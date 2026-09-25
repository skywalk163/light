# -*- coding: utf-8 -*-
"""
test_进程树_创建时间闸门.py —— R95-B2 创建时间闸门单测

验证 `_R92补杀迟建后代`（仅 Windows 生效的兜底补杀）在「按 PID 判定是否为本树
迟建后代」时，额外比对进程创建时间：

  - 真后代（创建时间晚于本树起点）→ 仍被补杀；
  - 老进程 PID 被 OS 复用（创建时间远早于本树起点）→ 绝不误杀；
  - 创建时间取不到（返回 空）→ 宁可漏杀也不误伤。

机理见 stdlib/进程树.light 的 [R95-B2] 注释。本测试在非 win32 平台整体 skip：
创建时间闸门只在 Windows 生效，且 0.82（FreeBSD）上 _创建时间秒 恒返回 空，
闸门为 no-op，保持原有行为（那一侧本就无 PID 复用误杀问题）。
"""
import os
import sys
import time
import subprocess
import unittest.mock as mock

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 进程树 import 进程树


@pytest.mark.skipif(sys.platform != "win32", reason="创建时间闸门仅 Windows 生效")
class Test创建时间闸门:
    def test_真后代被补杀_老pid复用不误杀_取不到创建时间也跳过(self):
        # 构造本树：根=1000，记录的早代后代=1001（都在 已杀键 内）。
        # 三个候选：8888（本树迟建后代，创建时间新）/ 9999（无关老进程 PID 复用，创建时间老）
        #          / 7777（创建时间取不到，返回 空）。
        # 三者 PPID 链都回溯到 1001→1000（命中已杀集合），但只有 8888 应通过闸门被杀。
        树 = 进程树(["echo", "hi"], {})
        树.开始时刻 = (time.time() - 2) * 1000  # 本树 2s 前启动（ms）

        alive = {8888: True}  # 只有 8888 视为仍存活

        def fake_关系表():
            # [(pid, ppid)]；9999/8888/7777 父都是 1001，1001 父=1000（根）
            return [
                (1000, 1), (1001, 1000),
                (9999, 1001), (8888, 1001), (7777, 1001),
                (5555, 1),  # 无关进程，PPID 链断在本树之外
            ]

        def fake_能打开(pid):
            return alive.get(pid, False)

        def fake_创时(pid):
            now = time.time()
            if pid == 9999:
                return now - 3600      # 一小时前创建 → 老 PID 复用
            if pid == 8888:
                return now - 1          # 1s 前创建 → 本树迟建后代
            if pid == 7777:
                return None             # 取不到
            return now - 10

        树.进程关系表 = fake_关系表
        树.能打开 = fake_能打开
        树._创建时间秒 = fake_创时

        killed = []

        def fake_call(args, *rest):
            # 进程树.light 调用形：subprocess.call(["taskkill","/F","/PID",str(p)], -1, 空, 空, DEVNULL, DEVNULL)
            if len(args) >= 4 and args[0] == "taskkill" and args[1] == "/F" and args[2] == "/PID":
                pid = int(args[3])
                killed.append(pid)
                alive[pid] = False
            return 0

        with mock.patch("subprocess.call", fake_call):
            树._R92补杀迟建后代(1000, [1001])

        assert 8888 in killed, "本树迟建后代（创建时间新）应被补杀"
        assert 9999 not in killed, "老 PID 复用（创建时间远早于本树起点）被误杀！闸门失效"
        assert 7777 not in killed, "创建时间取不到时不应误杀（取不到也走跳过分支）"
        # 无关进程 5555 链不到本树，本来就不该进 killed
        assert 5555 not in killed
