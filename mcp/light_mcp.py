#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""light-mcp —— 光明（Light）的 MCP stdio 服务端。

纯标准库、零依赖、只走 stdio（不实现 HTTP/SSE）。把光明的三个 AI 入口
（``light ai check --json`` / ``light run`` / ``light patch``）包装成 agent
可直接调用的结构化工具，省掉「拼 shell、解析 stdout、处理编码」这三步：

======================  ==========================================
工具                    底层命令
======================  ==========================================
``light_check``         ``light ai check --json <path> [--run]``
``light_run``           ``light run <path> [-- <args...>]``
``light_patch``         复用 ``src/patch_engine.patch``（等价 ``light patch``）
======================  ==========================================

设计红线（与任务卡一致）：

* **永不抛未捕获异常**：工具内部的失败都变成 ``isError: true`` 的
  ``{"content": [{"type": "text", "text": "<JSON>"}]}``，进程继续服务；
* 返回一律是**结构化 JSON 字符串**，字段名与 ``light ai check --json``
  同一口径（``ok`` / ``diagnostics`` / ``stage`` / ``duration_ms`` …），
  agent 可以跨两个入口复用同一套解析逻辑；
* **不在 MCP 层做业务判断**：修不修、算不算失败，全由调用方看字段决定，
  这里只搬运结构化结果；
* **不写盘**：``light_patch`` 只把新文本返回给调用方；
* 中文路径 / Windows 代码页：子进程统一 ``PYTHONIOENCODING=utf-8`` +
  ``encoding="utf-8", errors="replace"``。

启动方式（宿主配置里用绝对路径）::

    python -X utf8 /abs/path/to/light/mcp/light_mcp.py

可选参数：``--root /abs/path/to/light``（默认按本文件位置推导，也可用
环境变量 ``LIGHT_ROOT`` 覆盖）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

SERVER_NAME = "light-mcp"
SERVER_VERSION = "0.1.0"

#: 认得的协议版本；客户端报别的版本时回落到 DEFAULT_PROTOCOL_VERSION。
PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")
DEFAULT_PROTOCOL_VERSION = "2024-11-05"

#: ``light ai check --json`` 单次上限（秒）。--run 时底层还有自己的 30s 运行超时。
CHECK_TIMEOUT_S = 240.0
#: ``light run`` 默认 / 上限（秒），可由入参 timeout_s 覆盖。
RUN_TIMEOUT_DEFAULT_S = 30
RUN_TIMEOUT_MAX_S = 600


# --------------------------------------------------------------------------- #
# 工具定义（tools/list 的返回）
# --------------------------------------------------------------------------- #

TOOLS = [
    {
        "name": "light_check",
        "title": "光明代码检查",
        "description": (
            "对 .light 文件跑 `light ai check --json`，原样返回机器可读诊断 JSON"
            "（ok / diagnostics / stage / fix_suggestions …），并附 exit_code。"
            "ok=false 表示有 error 级诊断，具体改哪儿看 diagnostics 的 "
            "line/column/message/fixes。传 run=true 会额外执行一遍文件（运行期错误"
            "记在 stage=\"运行\"）。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "光明源文件路径（相对路径按宿主进程的当前目录解析）",
                },
                "strict": {
                    "type": "boolean",
                    "description": (
                        "严格解析 stdout：要求整段 stdout 恰好是一个 JSON 对象。"
                        "默认 false（容错：夹带日志时仍尝试抽出 JSON）。"
                        "只影响解析方式，不影响 ok 判定。"
                    ),
                    "default": False,
                },
                "run": {
                    "type": "boolean",
                    "description": "同时执行文件，把运行期错误也记成诊断（stage=\"运行\"）",
                    "default": False,
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "light_run",
        "title": "光明代码执行",
        "description": (
            "执行一个 .light 文件，返回 {rc, stdout, stderr, duration_ms}。"
            "脚本实参用 args 传（服务端自动补 `--` 分隔符，交给 `用户参数()`）。"
            "超时不抛错：返回 rc=null + timed_out=true。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "光明源文件路径（相对路径按宿主进程的当前目录解析）",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "传给脚本的实参（经 `--` 分隔，不会和 CLI 开关冲突）",
                },
                "timeout_s": {
                    "type": "integer",
                    "description": "执行超时秒数，默认 30，上限 600",
                    "default": RUN_TIMEOUT_DEFAULT_S,
                    "minimum": 1,
                    "maximum": RUN_TIMEOUT_MAX_S,
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "light_patch",
        "title": "光明局部补丁（不写盘）",
        "description": (
            "按 span 做确定性局部替换，返回 {ok, file, span, changed, new_text}。"
            "span 语义与 `light patch` 完全一致：行/列 1 起，end_column 不含"
            "（半开区间）。**只返回新文本，不写盘**——要落盘由调用方自己决定。"
            "复用 src/patch_engine，越界/交叠/不闭合会被拒绝并给出中文原因。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "光明源文件路径（只读；相对路径按宿主进程的当前目录解析）",
                },
                "span": {
                    "type": "object",
                    "description": "单行 span：{line, column, end_column}，1 起，端列不含",
                    "properties": {
                        "line": {"type": "integer", "minimum": 1},
                        "column": {"type": "integer", "minimum": 1},
                        "end_column": {"type": "integer", "minimum": 1},
                    },
                    "required": ["line", "column", "end_column"],
                },
                "replacement": {
                    "type": "string",
                    "description": "替换进去的新文本；删除传空串",
                },
            },
            "required": ["path", "span", "replacement"],
        },
    },
]


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #

def light_root(explicit: str | None = None) -> Path:
    """定位光明仓根：显式参数 → 环境变量 LIGHT_ROOT → 本文件上级目录。"""
    candidate = explicit or os.environ.get("LIGHT_ROOT")
    if candidate:
        return Path(candidate).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def _abs_path(value: str) -> str:
    """相对路径按当前工作目录补成绝对路径。

    服务端起子进程时 cwd 固定为仓根，如果不先绝对化，调用方给的
    ``./示例.light`` 会被解析成「仓根/示例.light」而不是「它的当前目录」。
    """
    p = Path(os.path.expanduser(value))
    if not p.is_absolute():
        p = Path(os.getcwd()) / p
    return str(p)


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _env_for_child() -> dict:
    env = os.environ.copy()
    # 子进程的 stdout/stderr 一律 UTF-8：避免 Windows 下 cp936 把中文编成乱码。
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _error_payload(message: str, code: str = "L_MCP_ERROR", **extra) -> dict:
    payload = {"ok": False, "code": code, "error": message}
    payload.update(extra)
    return payload


def _ok(payload: dict, is_error: bool = False) -> dict:
    """包成 MCP tools/call 的返回结构（text 里是结构化 JSON 字符串）。"""
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
        "isError": bool(is_error),
    }


def _fail(payload: dict) -> dict:
    return _ok(payload, is_error=True)


# --------------------------------------------------------------------------- #
# 工具实现
# --------------------------------------------------------------------------- #

def tool_light_check(root: Path, arguments: dict) -> dict:
    path = arguments.get("path")
    if not isinstance(path, str) or not path.strip():
        return _fail(_error_payload("参数 path 必填：光明源文件路径", "L_MCP_ARGS"))
    run = bool(arguments.get("run"))
    strict = bool(arguments.get("strict"))

    target = _abs_path(path)
    if not os.path.isfile(target):
        # CLI 对不存在的文件走 exit_code=2（「用法或文件错误」）；工具面按同一个
        # 语义提前拦下，省得把一次必然失败的子进程跑出来。
        return _fail(_error_payload(f"文件不存在: {target}", "L_MCP_NOT_FOUND",
                                    file=target))
    cmd = [sys.executable, "-X", "utf8", "-m", "cli.light",
           "ai", "check", "--json", target]
    if run:
        cmd.append("--run")

    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, cwd=str(root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=_env_for_child(),
            timeout=CHECK_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        return _fail(_error_payload(
            f"light ai check 超时（>{int(CHECK_TIMEOUT_S)}s）", "L_MCP_TIMEOUT",
            file=target, duration_ms=int((time.monotonic() - started) * 1000),
            stderr_tail=_as_text(getattr(exc, "stderr", ""))[-2000:]))
    except OSError as exc:
        return _fail(_error_payload(
            f"起不了 light 子进程：{type(exc).__name__}: {exc}", "L_MCP_SPAWN",
            file=target))
    except Exception as exc:  # noqa: BLE001 —— 工具层兜底，绝不把异常漏给宿主
        return _fail(_error_payload(
            f"{type(exc).__name__}: {exc}", "L_MCP_ERROR", file=target))

    payload, parse_error = _parse_check_stdout(proc.stdout or "", strict)
    if payload is None:
        return _fail(_error_payload(
            f"light ai check 的 stdout 不是可解析的 JSON：{parse_error}",
            "L_MCP_BAD_JSON", file=target, exit_code=proc.returncode,
            stdout_tail=(proc.stdout or "")[-2000:],
            stderr_tail=(proc.stderr or "")[-2000:]))

    payload.setdefault("ok", proc.returncode == 0)
    # 「原样 JSON + ok」：CLI 的字段一个不改，只补一个 exit_code 方便 agent 判退出码。
    payload["exit_code"] = proc.returncode
    return _ok(payload)


def _parse_check_stdout(stdout: str, strict: bool):
    """把 CLI 的 stdout 解析成一个 JSON 对象；失败返回 ``(None, 原因)``。"""
    text = (stdout or "").strip()
    if not text:
        return None, "stdout 为空"
    try:
        value = json.loads(text)
        if not isinstance(value, dict):
            return None, f"顶层不是对象（{type(value).__name__}）"
        return value, None
    except json.JSONDecodeError as exc:
        if strict:
            return None, str(exc)
    # 容错路径：从最后一行往前找第一个能解析的对象（进度日志通常在前面）。
    for line in reversed(text.splitlines()):
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value, None
    return None, "stdout 里没有 JSON 对象"


def tool_light_run(root: Path, arguments: dict) -> dict:
    path = arguments.get("path")
    if not isinstance(path, str) or not path.strip():
        return _fail(_error_payload("参数 path 必填：光明源文件路径", "L_MCP_ARGS"))

    script_args = arguments.get("args")
    if script_args is None:
        script_args = []
    if not isinstance(script_args, list) or any(not isinstance(a, str) for a in script_args):
        return _fail(_error_payload(
            "参数 args 必须是字符串数组", "L_MCP_ARGS",
            received=json.dumps(script_args, ensure_ascii=False)[:200]))

    timeout_s = arguments.get("timeout_s")
    if timeout_s is None:
        timeout_s = RUN_TIMEOUT_DEFAULT_S
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, int):
        return _fail(_error_payload("参数 timeout_s 必须是整数秒", "L_MCP_ARGS"))
    timeout_s = max(1, min(RUN_TIMEOUT_MAX_S, timeout_s))

    target = _abs_path(path)
    if not os.path.isfile(target):
        return _fail(_error_payload(f"文件不存在: {target}", "L_MCP_NOT_FOUND",
                                    file=target))
    cmd = [sys.executable, "-X", "utf8", "-m", "cli.light", "run", target]
    if script_args:
        cmd.append("--")
        cmd.extend(script_args)

    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, cwd=str(root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=_env_for_child(),
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return _fail({
            "ok": False,
            "file": target,
            "rc": None,
            "timed_out": True,
            "timeout_s": timeout_s,
            "stdout": _as_text(getattr(exc, "stdout", "")) or "",
            "stderr": _as_text(getattr(exc, "stderr", "")) or "",
            "duration_ms": int((time.monotonic() - started) * 1000),
        })
    except OSError as exc:
        return _fail(_error_payload(
            f"起不了 light 子进程：{type(exc).__name__}: {exc}", "L_MCP_SPAWN",
            file=target))
    except Exception as exc:  # noqa: BLE001
        return _fail(_error_payload(
            f"{type(exc).__name__}: {exc}", "L_MCP_ERROR", file=target))

    return _ok({
        "ok": proc.returncode == 0,
        "file": target,
        "rc": proc.returncode,
        "timed_out": False,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "duration_ms": int((time.monotonic() - started) * 1000),
    })


def _patch_engine(root: Path):
    """延迟导入 src/patch_engine（口径与 `light patch` 完全同源）。"""
    for extra in (str(root / "src"), str(root)):
        if extra not in sys.path:
            sys.path.insert(0, extra)
    import patch_engine  # noqa: F401 —— 故意延迟导入，坏环境不拖垮服务启动
    return patch_engine


def tool_light_patch(root: Path, arguments: dict) -> dict:
    path = arguments.get("path")
    if not isinstance(path, str) or not path.strip():
        return _fail(_error_payload("参数 path 必填：光明源文件路径", "L_MCP_ARGS"))
    span = arguments.get("span")
    if not isinstance(span, dict):
        return _fail(_error_payload(
            "参数 span 必填：{line, column, end_column}", "L_MCP_ARGS"))
    missing = [k for k in ("line", "column", "end_column") if k not in span]
    if missing:
        return _fail(_error_payload(
            "span 缺少字段：" + " / ".join(missing), "L_MCP_ARGS"))
    for key in ("line", "column", "end_column"):
        value = span[key]
        if isinstance(value, bool) or not isinstance(value, int):
            return _fail(_error_payload(
                f"span.{key} 必须是整数，实际是 {type(value).__name__}: {value!r}",
                "L_MCP_ARGS"))
    replacement = arguments.get("replacement")
    if not isinstance(replacement, str):
        return _fail(_error_payload("参数 replacement 必须是字符串", "L_MCP_ARGS"))

    target = _abs_path(path)
    try:
        source = Path(target).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return _fail(_error_payload(f"文件不存在: {target}", "L_MCP_NOT_FOUND"))
    except OSError as exc:
        return _fail(_error_payload(f"文件读取失败: {exc}", "L_MCP_READ"))

    try:
        engine = _patch_engine(root)
    except Exception as exc:  # noqa: BLE001
        return _fail(_error_payload(
            f"补丁引擎不可用（src/patch_engine.py 未合入或导入失败）："
            f"{type(exc).__name__}: {exc}", "L_MCP_ENGINE"))

    edit = {
        "span": {
            "start_line": span["line"],
            "start_col": span["column"],
            "end_line": span["line"],
            "end_col": span["end_column"],
        },
        "text": replacement,
    }
    try:
        new_text = engine.patch(source, [edit])
    except Exception as exc:  # PatchError 及其它：都按 CLI 口径回「补丁被拒」
        return _fail(_error_payload(f"补丁被拒: {exc}", "L_MCP_PATCH_REJECTED",
                                    file=target))

    return _ok({
        "ok": True,
        "file": target,
        "span": {"line": span["line"], "column": span["column"],
                 "end_column": span["end_column"]},
        "changed": new_text != source,
        "new_text": new_text,
    })


HANDLERS = {
    "light_check": tool_light_check,
    "light_run": tool_light_run,
    "light_patch": tool_light_patch,
}


# --------------------------------------------------------------------------- #
# JSON-RPC / stdio 传输
# --------------------------------------------------------------------------- #

class Server:
    def __init__(self, root: Path):
        self.root = root

    # -- 报文 ---------------------------------------------------------------- #
    @staticmethod
    def result(msg_id, payload: dict) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "result": payload}

    @staticmethod
    def error(msg_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id,
                "error": {"code": code, "message": message}}

    def handle(self, msg: dict):
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params") or {}
        if not isinstance(params, dict):
            params = {}

        if method == "initialize":
            requested = params.get("protocolVersion")
            version = (requested if requested in PROTOCOL_VERSIONS
                       else DEFAULT_PROTOCOL_VERSION)
            return self.result(msg_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "光明（Light）语言工具面。改代码的标准闭环："
                    "light_check 看诊断 → 按 diagnostics 的 line/column/fixes 改 "
                    "→ light_patch 拿新文本（不写盘）→ 再 light_check 复验。"
                    "需要看运行期行为时 light_check(run=true) 或 light_run。"
                ),
            })
        if method in ("notifications/initialized", "initialized"):
            return None
        if method == "ping":
            return self.result(msg_id, {})
        if method == "tools/list":
            return self.result(msg_id, {"tools": TOOLS})
        if method in ("resources/list", "prompts/list"):
            return self.result(msg_id, {method.split("/")[0]: []})
        if method == "tools/call":
            return self._call_tool(msg_id, params)
        if msg_id is None:
            return None
        return self.error(msg_id, -32601, f"不支持的方法：{method}")

    def _call_tool(self, msg_id, params: dict) -> dict:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return self.result(msg_id, _fail(_error_payload(
                "arguments 必须是对象", "L_MCP_ARGS")))
        handler = HANDLERS.get(name)
        if handler is None:
            return self.result(msg_id, _fail(_error_payload(
                f"没有工具 {name}", "L_MCP_UNKNOWN_TOOL")))
        try:
            # stdout 被协议独占：工具内部万一有 stray print，一律赶到 stderr。
            with _redirect_stdout(sys.stderr):
                envelope = handler(self.root, arguments)
        except Exception as exc:  # noqa: BLE001 —— 最后一道保险，进程不能退出
            envelope = _fail(_error_payload(
                f"{type(exc).__name__}: {exc}", "L_MCP_INTERNAL"))
        return self.result(msg_id, envelope)


class _redirect_stdout:
    """把 handler 期间写往 stdout 的内容重定向到 stderr（stdout 只留协议报文）。"""

    def __init__(self, target):
        self.target = target
        self.saved = None

    def __enter__(self):
        self.saved = sys.stdout
        sys.stdout = self.target
        return self

    def __exit__(self, *exc_info):
        sys.stdout = self.saved
        return False


def _read_message(stream):
    """读一条 JSON-RPC 报文，返回 ``(msg, framed)``；EOF 返回 ``(None, None)``。

    两种分帧都支持：

    * LSP/MCP 规范的 ``Content-Length: N`` 头 + 空行 + 定长 JSON；
    * 项目内 mcp_server 骨架用的「一行一个 JSON」。

    哪种由客户端第一条报文决定，之后服务端按同一种回去。
    """
    while True:
        line = stream.readline()
        if not line:
            return None, None
        if line.strip():
            break

    stripped = line.strip()
    if stripped.lower().startswith(b"content-length:"):
        try:
            length = int(stripped.split(b":", 1)[1].strip())
        except (IndexError, ValueError) as exc:
            raise ValueError(f"Content-Length 头无法解析：{stripped!r}（{exc}）")
        while True:  # 吃掉其余头 + 空行
            header = stream.readline()
            if not header or not header.strip():
                break
        body = stream.read(length)
        if len(body) < length:
            raise ValueError(f"报文被截断：期望 {length} 字节，实际 {len(body)}")
        return json.loads(body.decode("utf-8")), True

    return json.loads(line.decode("utf-8")), False


def _send(stream, message: dict, framed: bool) -> None:
    data = json.dumps(message, ensure_ascii=False).encode("utf-8")
    if framed:
        stream.write(b"Content-Length: " + str(len(data)).encode("ascii") + b"\r\n\r\n")
        stream.write(data)
    else:
        stream.write(data + b"\n")
    stream.flush()


def serve(root: Path) -> int:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    server = Server(root)
    framed = False
    while True:
        try:
            msg, framed_now = _read_message(stdin)
        except ValueError as exc:
            _send(stdout, Server.error(None, -32700, f"JSON 解析失败：{exc}"), framed)
            continue
        except Exception as exc:  # noqa: BLE001 —— 坏报文不该把服务打死
            _send(stdout, Server.error(None, -32700, f"报文读取失败：{exc}"), framed)
            continue
        if msg is None:
            return 0
        if framed_now:
            framed = True
        if not isinstance(msg, dict):
            _send(stdout, Server.error(None, -32600, "请求必须是 JSON 对象"), framed)
            continue
        response = server.handle(msg)
        if response is not None:
            _send(stdout, response, framed)


def main(argv: list | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    explicit_root = None
    rest = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--root" and index + 1 < len(argv):
            explicit_root = argv[index + 1]
            index += 2
            continue
        if arg.startswith("--root="):
            explicit_root = arg.split("=", 1)[1]
            index += 1
            continue
        rest.append(arg)
        index += 1
    if rest:
        print(f"忽略未知参数：{' '.join(rest)}", file=sys.stderr)

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    root = light_root(explicit_root)
    if not (root / "cli" / "light.py").is_file():
        print(f"找不到光明仓根（{root} 下没有 cli/light.py）；"
              f"用 --root 或环境变量 LIGHT_ROOT 指定", file=sys.stderr)
        return 2
    return serve(root)


if __name__ == "__main__":
    sys.exit(main())
