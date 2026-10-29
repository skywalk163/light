# -*- coding: utf-8 -*-
"""LH-20：管道式交互子进程（进程会话）回归测试。

验证 stdlib/进程.py 新增的 进程会话启动 / 进程会话 提供真正的
stdin/stdout 长连接能力——MCP stdio / LSP / JSON-RPC over pipe /
交互式 CLI 驱动（ssh/gdb/psql/fdisk）的地基。

验收五条（对应 LH-20 验收）：
  1. 请求-响应循环：连发 5 轮，读回与发出一一对应（幂等、无串包）
  2. 超时：子进程故意不回 → 读一行(超时=1) 约 1 秒返回空，不挂死
  3. stderr 大流量：子进程往 stderr 写 1MB 再回一行 → 仍能正常读回
     （证明 stderr 没被接 PIPE 又不读、没把子进程写死）
  4. 收尾：终止() 后进程确实退出（是否存活() 为假），无僵尸
  5. （加分）MCP initialize 握手：断言拿到 serverInfo
"""
import json
import os
import sys
import time
import unittest

# 经 tests/conftest.py 的 stdlib sys.path 落位，取 stdlib/进程.py 真身
from 进程 import 进程会话启动


def _回显脚本():
    """读一行、回一行的 echo 服务源码（LF 逐行、立即 flush）。"""
    return (
        "import sys\n"
        "for line in sys.stdin:\n"
        "    sys.stdout.write(line)\n"
        "    sys.stdout.flush()\n"
    )


class TestLH20管道交互(unittest.TestCase):
    """LH-20 管道式交互子进程测试。"""

    def setUp(self):
        self._会话们 = []

    def tearDown(self):
        # 无论成败都必须回收自 spawn 的子进程，否则孤儿进程占着管道/句柄
        for 会 in self._会话们:
            try:
                会.终止()
            except Exception:
                pass

    def _启动(self, 脚本):
        会 = 进程会话启动([sys.executable, "-u", "-c", 脚本])
        self._会话们.append(会)
        return 会

    def test_01_请求响应循环(self):
        """连发 5 轮，每轮读回与发出一一对应（幂等、无串包）。"""
        会 = self._启动(_回显脚本())
        for i in range(5):
            消息 = f"轮次{i}-消息"
            会.写一行(消息)
            读回 = 会.读一行(超时=3)
            self.assertIsNotNone(读回, f"第{i}轮未读到响应（子进程未回或读超时）")
            self.assertEqual(读回, 消息, f"第{i}轮读回与发出不一致")

    def test_02_超时返回空(self):
        """子进程故意不回 → 读一行(超时=1) 约 1 秒返回空，不挂死。"""
        脚本 = (
            "import sys, time\n"
            "line = sys.stdin.readline()\n"   # 读走我们写的那行，但故意不回
            "time.sleep(30)\n"
        )
        会 = self._启动(脚本)
        会.写一行("ping")
        开始 = time.monotonic()
        读回 = 会.读一行(超时=1)
        耗时 = time.monotonic() - 开始
        self.assertIsNone(读回,
                          "子进程不回时应返回空，而不是阻塞或返回内容")
        self.assertGreaterEqual(耗时, 0.9,
                                f"超时应在约 1 秒返回，实际 {耗时:.2f}s")
        self.assertLess(耗时, 5, "超时不应挂死")

    def test_03_stderr大流量(self):
        """子进程往 stderr 写 1MB 再回一行 → 仍能正常读回。"""
        脚本 = (
            "import sys\n"
            "sys.stderr.write('x' * (1024 * 1024))\n"   # 1MB 到 stderr
            "sys.stderr.flush()\n"
            "line = sys.stdin.readline()\n"
            "sys.stdout.write(line)\n"
            "sys.stdout.flush()\n"
        )
        会 = self._启动(脚本)
        会.写一行("ping")
        读回 = 会.读一行(超时=5)
        self.assertIsNotNone(读回, "stderr 大流量不应把子进程堵死")
        self.assertEqual(读回, "ping")

    def test_04_终止后进程退出无僵尸(self):
        """终止() 后进程确实退出（是否存活() 为假），无僵尸。"""
        会 = self._启动("import time; time.sleep(60)\n")
        self.assertTrue(会.是否存活(), "刚启动应存活")
        会.终止()
        self.assertFalse(会.是否存活(), "终止后应已退出")
        # 无僵尸：wait() 已收割，再 waitpid(WNOHANG) 应无子可等（ECHILD）
        if sys.platform != "win32":
            try:
                os.waitpid(会.进程PID(), os.WNOHANG)
                self.fail("进程未被收割（仍是僵尸）")
            except ChildProcessError:
                pass  # 已收割，正常
        self.assertIsNotNone(会.返回码(), "终止后返回码应已设置（已收割）")

    def test_05_MCP初始化握手(self):
        """（加分）真协议佐证：跑一次 MCP initialize 握手，断言拿到 serverInfo。"""
        脚本 = (
            "import sys, json\n"
            "for line in sys.stdin:\n"
            "    line = line.strip()\n"
            "    if not line:\n"
            "        continue\n"
            "    msg = json.loads(line)\n"
            "    if msg.get('method') == 'initialize':\n"
            "        resp = {'jsonrpc':'2.0','id':msg.get('id'),"
            "'result':{'protocolVersion':'2024-11-05','capabilities':{},"
            "'serverInfo':{'name':'echo-mcp','version':'1.0'}}}\n"
            "        sys.stdout.write(json.dumps(resp) + '\\n')\n"
            "        sys.stdout.flush()\n"
        )
        会 = self._启动(脚本)
        请求 = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        }
        会.写一行(json.dumps(请求))
        响应行 = 会.读一行(超时=5)
        self.assertIsNotNone(响应行, "MCP initialize 应得到响应")
        响应 = json.loads(响应行)
        self.assertEqual(响应.get("jsonrpc"), "2.0")
        self.assertEqual(响应.get("id"), 1)
        self.assertEqual(响应["result"]["serverInfo"]["name"], "echo-mcp")
        self.assertEqual(响应["result"]["protocolVersion"], "2024-11-05")


if __name__ == "__main__":
    unittest.main()
