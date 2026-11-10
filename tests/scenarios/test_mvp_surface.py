# -*- coding: utf-8 -*-
"""Light 生态最小可用面（MVP Surface）场景测试。

五个方向各一个完整示例，全部用 `python -m cli.light run` 真跑：
  01 文件读写 / 02 网络请求+JSON / 03 进程管理 / 04 测试框架 / 05 包与模块引用

网络示例只在测试内起 127.0.0.1 的 http.server（随机端口），不依赖外网。
不达标的示例必须用 pytest.xfail(strict=True) 并把原因指向 docs/MVP_SURFACE.md，
禁止静默 skip；当前五个方向均已达「稳定」，故没有 xfail 分支。
"""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXAMPLES = os.path.join(ROOT, "examples", "mvp")
MVP_DOC = os.path.join(ROOT, "docs", "MVP_SURFACE.md")
SCENARIOS_SCRIPT = os.path.join(ROOT, "scripts", "run_scenarios.py")

# (文件名, stdout 关键标记)
DIRECT_SCENARIOS = [
    ("01_file_io.light", "MVP_IO_OK"),
    ("03_process.light", "MVP_PROCESS_OK"),
    ("04_test_framework.light", "MVP_TEST_OK"),
    ("05_pkg_module.light", "MVP_MODULE_OK"),
]

ALL_EXAMPLE_FILES = [
    "01_file_io.light",
    "02_http_json.light",
    "03_process.light",
    "04_test_framework.light",
    "05_pkg_module.light",
]


def _env():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    路径 = [ROOT] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    env["PYTHONPATH"] = os.pathsep.join(路径)
    return env


def run_light(script, args=(), timeout=90):
    """在仓库根目录用 CLI 跑一个 .light 示例，返回 CompletedProcess。"""
    cmd = [sys.executable, "-m", "cli.light", "run", os.path.join(EXAMPLES, script)]
    if args:
        cmd += ["--"] + list(args)
    return subprocess.run(
        cmd,
        cwd=ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


class _JSONHandler(BaseHTTPRequestHandler):
    """只服务 /mvp：返回固定 JSON，供 02 示例解析。"""

    def do_GET(self):
        数据 = {
            "name": "light",
            "message": "你好，MVP",
            "items": [1, 2, 3, 4],
        }
        body = json.dumps(数据, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture()
def local_json_url():
    """在 127.0.0.1 的随机端口起本机 JSON 服务，测试结束关闭。"""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _JSONHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d/mvp" % server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("script,marker", DIRECT_SCENARIOS)
def test_direct_scenario(script, marker):
    """四个不依赖网络的示例：退出码 0 且输出关键标记。"""
    结果 = run_light(script)
    assert 结果.returncode == 0, (
        "%s 退出码 %d\nstdout:\n%s\nstderr:\n%s"
        % (script, 结果.returncode, 结果.stdout, 结果.stderr)
    )
    assert marker in 结果.stdout, "%s 输出缺少标记 %s\n%s" % (script, marker, 结果.stdout)


def test_http_json_scenario(local_json_url):
    """网络示例：请求测试内起的本机服务，解析 JSON 并取字段。"""
    结果 = run_light("02_http_json.light", [local_json_url])
    assert 结果.returncode == 0, (
        "02_http_json.light 退出码 %d\nstdout:\n%s\nstderr:\n%s"
        % (结果.returncode, 结果.stdout, 结果.stderr)
    )
    for 标记 in ("状态码=200", "服务名=light", "消息=你好，MVP", "MVP_HTTP_OK"):
        assert 标记 in 结果.stdout, "输出缺少 %s\n%s" % (标记, 结果.stdout)


def test_examples_are_single_screen():
    """五个示例存在且每个不超过 60 行（docs/MVP_SURFACE.md 的承诺）。"""
    for 文件名 in ALL_EXAMPLE_FILES:
        路径 = os.path.join(EXAMPLES, 文件名)
        assert os.path.isfile(路径), "缺少示例 %s" % 路径
        with open(路径, "r", encoding="utf-8") as f:
            行数 = len(f.readlines())
        assert 行数 <= 60, "%s 有 %d 行，超过单屏 60 行上限" % (文件名, 行数)


def test_mvp_surface_doc_covers_all_directions():
    """MVP Surface 文档必须覆盖五个方向，并指向对应示例。"""
    assert os.path.isfile(MVP_DOC), "缺少 docs/MVP_SURFACE.md"
    with open(MVP_DOC, "r", encoding="utf-8") as f:
        正文 = f.read()
    for 方向 in ("文件读写", "网络请求", "进程管理", "测试框架", "包与模块"):
        assert 方向 in 正文, "docs/MVP_SURFACE.md 缺少方向：%s" % 方向
    for 文件名 in ALL_EXAMPLE_FILES:
        assert 文件名 in 正文, "docs/MVP_SURFACE.md 未引用 %s" % 文件名


def test_run_scenarios_script():
    """一键脚本 --json 输出 5 个场景且全部通过。"""
    assert os.path.isfile(SCENARIOS_SCRIPT), "缺少 scripts/run_scenarios.py"
    结果 = subprocess.run(
        [sys.executable, SCENARIOS_SCRIPT, "--json"],
        cwd=ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert 结果.returncode == 0, "run_scenarios.py 退出码 %d\n%s\n%s" % (
        结果.returncode,
        结果.stdout,
        结果.stderr,
    )
    报告 = json.loads(结果.stdout)
    assert 报告["ok"] is True
    assert len(报告["scenarios"]) == 5
    assert all(项["result"] == "通过" for 项 in 报告["scenarios"])
