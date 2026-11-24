# -*- coding: utf-8 -*-
"""T-0461：light-mcp 的「宿主视角」验收。

只从外面看协议行为：起子进程、按 JSON-RPC 说话、断言工具能力与返回形状。
内部实现细节（函数名/类结构）一律不碰——换实现时这份测试仍然成立。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp" / "light_mcp.py"
EXAMPLE = ROOT / "mcp.example.json"
TOOL_NAMES = {"light_check", "light_run", "light_patch"}


def _child_env() -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


class LightMcp:
    """换行分帧的 MCP 客户端（项目内 mcp_server 骨架用的就是这种）。"""

    def __init__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-X", "utf8", str(SERVER)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(ROOT), env=_child_env(),
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        self._next_id = 0

    # -- 协议 -------------------------------------------------------------- #
    def request(self, method, params=None):
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            message["params"] = params
        return self._roundtrip(message)

    def notify(self, method, params=None):
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def _roundtrip(self, message):
        self.proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise AssertionError("服务端没有响应（进程可能已退出）：stderr=%r"
                                 % self._stderr())
        return json.loads(line)

    def tool(self, name, arguments):
        """调一个工具，返回 ``(解析后的 payload, isError)``。"""
        response = self.request("tools/call",
                                {"name": name, "arguments": arguments})
        result = response["result"]
        assert result["content"][0]["type"] == "text"
        return json.loads(result["content"][0]["text"]), bool(result.get("isError"))

    def _stderr(self):
        if self.proc.poll() is None:
            return "<still running>"
        return self.proc.stderr.read()

    def close(self):
        try:
            if self.proc.stdin and not self.proc.stdin.closed:
                self.proc.stdin.close()
        finally:
            if self.proc.poll() is None:
                self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()


@pytest.fixture()
def mcp():
    client = LightMcp()
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest"},
        })
        client.notify("notifications/initialized")
        yield client
    finally:
        client.close()


# --------------------------------------------------------------------------- #
# 1. 握手 + 工具清单
# --------------------------------------------------------------------------- #

def test_initialize_and_tools_list(mcp):
    response = mcp.request("ping")
    assert response["result"] == {}

    listed = mcp.request("tools/list")
    tools = {tool["name"]: tool for tool in listed["result"]["tools"]}
    assert set(tools) == TOOL_NAMES

    for name, tool in tools.items():
        schema = tool["inputSchema"]
        assert schema["type"] == "object", name
        assert "path" in schema["properties"], name
        assert schema["properties"]["path"]["type"] == "string", name
        assert "path" in schema["required"], name

    check_schema = tools["light_check"]["inputSchema"]["properties"]
    assert check_schema["run"]["type"] == "boolean"
    assert check_schema["strict"]["type"] == "boolean"

    patch_schema = tools["light_patch"]["inputSchema"]
    assert set(patch_schema["required"]) == {"path", "span", "replacement"}
    span_schema = patch_schema["properties"]["span"]
    assert set(span_schema["required"]) == {"line", "column", "end_column"}
    assert span_schema["properties"]["line"]["type"] == "integer"

    run_schema = tools["light_run"]["inputSchema"]["properties"]
    assert run_schema["args"]["type"] == "array"
    assert run_schema["args"]["items"]["type"] == "string"
    assert run_schema["timeout_s"]["type"] == "integer"


# --------------------------------------------------------------------------- #
# 2. light_check：坏文件有诊断、好文件 ok
# --------------------------------------------------------------------------- #

def test_light_check_reports_diagnostics_for_broken_file(mcp, tmp_path):
    source = tmp_path / "坏代码.light"          # 中文路径顺带验编码
    source.write_text('如果 1 大于 0\n    输出("正数")\n', encoding="utf-8")

    payload, is_error = mcp.tool("light_check", {"path": str(source)})

    # 源码有错是「业务结果」，不是工具故障：isError 必须是 False。
    assert is_error is False
    assert payload["ok"] is False
    assert payload["diagnostics"], "坏文件必须给出非空 diagnostics"
    assert payload["diagnostics"][0]["severity"] == "error"
    assert payload["diagnostics"][0]["line"] >= 1
    assert payload["exit_code"] == 1
    # 字段口径与 `light ai check --json` 一致，跨入口能复用解析逻辑。
    for key in ("schema_version", "file", "backend_hints", "stage",
                "fix_suggestions", "duration_ms"):
        assert key in payload


def test_light_check_passes_good_file(mcp, tmp_path):
    source = tmp_path / "你好.light"
    source.write_text('输出("你好，光明")\n', encoding="utf-8")

    payload, is_error = mcp.tool("light_check", {"path": str(source)})

    assert is_error is False
    assert payload["ok"] is True
    assert payload["diagnostics"] == []
    assert payload["exit_code"] == 0


# --------------------------------------------------------------------------- #
# 3. light_patch：与 `light patch` 命令行逐字一致，且不写盘
# --------------------------------------------------------------------------- #

def test_light_patch_matches_light_patch_cli(mcp, tmp_path):
    source = tmp_path / "补丁.light"
    original = '输出("你好，光明")\n'
    source.write_text(original, encoding="utf-8")

    span = {"line": 1, "column": 5, "end_column": 7}   # 「你好」两字，端列不含
    payload, is_error = mcp.tool("light_patch", {
        "path": str(source), "span": span, "replacement": "世界",
    })
    assert is_error is False
    assert payload["ok"] is True
    assert payload["changed"] is True

    edits = [{
        "span": {"start_line": 1, "start_col": 5, "end_line": 1, "end_col": 7},
        "text": "世界",
    }]
    cli = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "cli.light", "patch", "--json",
         str(source), "--edits", json.dumps(edits, ensure_ascii=False)],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=_child_env(),
    )
    cli_payload = json.loads(cli.stdout)
    assert cli_payload["ok"] is True
    assert payload["new_text"] == cli_payload["patched_source"]
    assert payload["new_text"] == '输出("世界，光明")\n'

    # 只返回、不写盘：源文件必须原样。
    assert source.read_text(encoding="utf-8") == original


def test_light_patch_rejects_out_of_range_span(mcp, tmp_path):
    source = tmp_path / "越界.light"
    source.write_text('输出("你好")\n', encoding="utf-8")

    payload, is_error = mcp.tool("light_patch", {
        "path": str(source),
        "span": {"line": 1, "column": 99, "end_column": 100},
        "replacement": "x",
    })
    assert is_error is True
    assert payload["ok"] is False
    assert "越界" in payload["error"]


# --------------------------------------------------------------------------- #
# 4. light_run：结构化结果，rc/stdout/stderr 一个不少
# --------------------------------------------------------------------------- #

def test_light_run_returns_structured_result(mcp, tmp_path):
    source = tmp_path / "运行.light"
    source.write_text('输出("你好，光明")\n', encoding="utf-8")

    payload, is_error = mcp.tool("light_run", {"path": str(source)})

    assert is_error is False
    assert payload["rc"] == 0
    assert "你好，光明" in payload["stdout"]
    assert isinstance(payload["stderr"], str)
    assert isinstance(payload["duration_ms"], int)
    assert payload["timed_out"] is False


def test_light_run_reports_nonzero_rc(mcp, tmp_path):
    source = tmp_path / "报错.light"
    source.write_text('输出(没有这个名字)\n', encoding="utf-8")

    payload, is_error = mcp.tool("light_run", {"path": str(source)})

    assert payload["rc"] != 0, "运行期错误必须体现在 rc 上"
    assert payload["stderr"].strip()


# --------------------------------------------------------------------------- #
# 5. 错误路径：isError 且进程不退出
# --------------------------------------------------------------------------- #

def test_missing_path_is_error_and_server_survives(mcp):
    payload, is_error = mcp.tool("light_check", {"path": "这个文件不存在.light"})

    assert is_error is True
    assert payload["ok"] is False
    assert "不存在" in payload["error"]

    # 关键：进程还活着，后续请求照常响应。
    listed = mcp.request("tools/list")
    assert {tool["name"] for tool in listed["result"]["tools"]} == TOOL_NAMES


def test_bad_arguments_never_kill_the_process(mcp):
    payload, is_error = mcp.tool("light_patch", {"path": "只有路径.light"})
    assert is_error is True
    assert "span" in payload["error"]

    payload, is_error = mcp.tool("light_run", {"path": "x.light", "args": "不是数组"})
    assert is_error is True

    unknown, is_error = mcp.tool("没有这个工具", {})
    assert is_error is True
    assert "没有工具" in unknown["error"]

    assert mcp.request("tools/list")["result"]["tools"]


# --------------------------------------------------------------------------- #
# 6. 传输层：规范要求的 Content-Length 分帧也得能跑
# --------------------------------------------------------------------------- #

def test_content_length_framing():
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=str(ROOT), env=_child_env(),
    )

    def send(message):
        body = json.dumps(message, ensure_ascii=False).encode("utf-8")
        proc.stdin.write(b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n")
        proc.stdin.write(body)
        proc.stdin.flush()

    def recv():
        header = proc.stdout.readline()
        assert header.startswith(b"Content-Length:"), header
        length = int(header.split(b":", 1)[1].strip())
        assert proc.stdout.readline().strip() == b"", "头与正文之间必须有空行"
        return json.loads(proc.stdout.read(length).decode("utf-8"))

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-03-26", "capabilities": {}}})
        response = recv()
        assert response["result"]["protocolVersion"] == "2025-03-26"
        assert response["result"]["serverInfo"]["name"] == "light-mcp"

        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        listed = recv()
        assert {tool["name"] for tool in listed["result"]["tools"]} == TOOL_NAMES
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


# --------------------------------------------------------------------------- #
# 7. 仓库根的 mcp.example.json 必须是可解析的真实配置
# --------------------------------------------------------------------------- #

def test_mcp_example_json_is_a_usable_config():
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    servers = data["mcpServers"]
    assert len(servers) == 1, "示例文件应当只放一个 server 条目"

    entry = servers["light"]
    assert entry["command"]
    assert entry["args"]
    assert any(str(arg).endswith("light_mcp.py") for arg in entry["args"])
    # 配置里指向的脚本必须真的存在（路径换成绝对路径后就能直接用）。
    script_arg = [arg for arg in entry["args"] if str(arg).endswith("light_mcp.py")][0]
    assert Path(script_arg).name == SERVER.name
    assert SERVER.is_file()
