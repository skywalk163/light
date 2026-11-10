#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键跑完 Light 生态最小可用面（MVP Surface）的 5 个场景。

用法：
    python scripts/run_scenarios.py
    python scripts/run_scenarios.py --json

默认输出「场景 | 结果 | 耗时(ms)」表格；任一场景失败退出码 1。
--json 输出结构化结果（含 stdout/stderr 尾部），便于 CI 消费。
只用标准库；网络场景在脚本内起 127.0.0.1 随机端口服务，不访问外网。
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "examples", "mvp")

场景列表 = [
    {"名称": "文件读写", "文件": "01_file_io.light", "标记": "MVP_IO_OK"},
    {"名称": "网络请求+JSON", "文件": "02_http_json.light", "标记": "MVP_HTTP_OK"},
    {"名称": "进程管理", "文件": "03_process.light", "标记": "MVP_PROCESS_OK"},
    {"名称": "测试框架", "文件": "04_test_framework.light", "标记": "MVP_TEST_OK"},
    {"名称": "包与模块引用", "文件": "05_pkg_module.light", "标记": "MVP_MODULE_OK"},
]


def _环境():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    路径 = [ROOT] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    env["PYTHONPATH"] = os.pathsep.join(路径)
    return env


class _JSONHandler(BaseHTTPRequestHandler):
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


def _起本机服务():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _JSONHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, "http://127.0.0.1:%d/mvp" % server.server_address[1]


def _跑场景(场景, 地址):
    命令 = [
        sys.executable,
        "-m",
        "cli.light",
        "run",
        os.path.join(EXAMPLES, 场景["文件"]),
    ]
    if 地址:
        命令 += ["--", 地址]
    开始 = time.perf_counter()
    try:
        进程 = subprocess.run(
            命令,
            cwd=ROOT,
            env=_环境(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        耗时 = (time.perf_counter() - 开始) * 1000
        通过 = 进程.returncode == 0 and 场景["标记"] in 进程.stdout
        return {
            "scenario": 场景["名称"],
            "file": 场景["文件"],
            "result": "通过" if 通过 else "失败",
            "elapsed_ms": round(耗时, 1),
            "returncode": 进程.returncode,
            "stdout_tail": "\n".join(进程.stdout.strip().splitlines()[-8:]),
            "stderr_tail": "\n".join(进程.stderr.strip().splitlines()[-8:]),
        }
    except subprocess.TimeoutExpired:
        耗时 = (time.perf_counter() - 开始) * 1000
        return {
            "scenario": 场景["名称"],
            "file": 场景["文件"],
            "result": "失败",
            "elapsed_ms": round(耗时, 1),
            "returncode": None,
            "stdout_tail": "",
            "stderr_tail": "超时（>90s）",
        }


def _打印表格(结果列表):
    print("| 场景 | 结果 | 耗时(ms) |")
    print("| --- | --- | ---: |")
    for 项 in 结果列表:
        print("| %s | %s | %.1f |" % (项["scenario"], 项["result"], 项["elapsed_ms"]))
    失败 = [项 for 项 in 结果列表 if 项["result"] != "通过"]
    if 失败:
        print("")
        for 项 in 失败:
            print("失败：%s（%s）" % (项["scenario"], 项["file"]))
            if 项["stdout_tail"]:
                print("  stdout 尾部：\n" + 项["stdout_tail"])
            if 项["stderr_tail"]:
                print("  stderr 尾部：\n" + 项["stderr_tail"])


def main(argv=None):
    解析器 = argparse.ArgumentParser(description="跑 Light MVP Surface 的 5 个场景")
    解析器.add_argument("--json", action="store_true", help="输出结构化 JSON")
    参数 = 解析器.parse_args(argv)

    服务, 线程, 地址 = _起本机服务()
    try:
        结果列表 = [
            _跑场景(场景, 地址 if 场景["文件"] == "02_http_json.light" else None)
            for 场景 in 场景列表
        ]
    finally:
        服务.shutdown()
        服务.server_close()
        线程.join(timeout=5)

    全部通过 = all(项["result"] == "通过" for 项 in 结果列表)
    if 参数.json:
        print(json.dumps(
            {"ok": 全部通过, "scenarios": 结果列表},
            ensure_ascii=False,
            indent=2,
        ))
    else:
        _打印表格(结果列表)
    return 0 if 全部通过 else 1


if __name__ == "__main__":
    sys.exit(main())
