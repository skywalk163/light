# -*- coding: utf-8 -*-
"""
test_进程树_jobobject.py —— R95-B1 Job Object 杀树根治验证（仅 Windows）

R95 承接 R94 的 KI-R94-01：Windows 高负载下 xdist worker 被杀的根因战场。
进程树.light 已在 [R91-D] / [R92-A-LEAK] 落地 Windows Job Object（KILL_ON_JOB_CLOSE）
+ 创建时间闸门（[R95-B2]，见 test_进程树_创建时间闸门.py）双重保险。本文件验证：

  1. test_绑定任务对象_产生有效句柄：启动即把根进程挂入 Job Object，任务句柄非零
     （证明 Job Object 根治路径在运行时确实生效，不是死代码）。
  2. test_杀树_整树被回收且无关进程存活：构造「根→子→孙」三层进程树，杀树后整树
     回收（root + 所有枚举到的后代全部 gone），且一个与本树无关的存活进程毫发无伤
     （证明不存在 PID 复用误杀 / 漏杀）。

非 win32（含 0.82 FreeBSD）整体 skip：Job Object 是 Windows 专属机制，那一侧本就
无 KI-R94-01 的误杀面。
"""
import os
import sys
import time
import subprocess
import tempfile

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 进程树 import 进程树


@pytest.mark.skipif(sys.platform != "win32", reason="Job Object 仅 Windows 生效")
class TestJobObject杀树:
    def test_绑定任务对象_产生有效句柄(self):
        树 = 进程树([sys.executable, "-c", "import time; time.sleep(20)"], {})
        assert 树.启动() is True
        try:
            # 任务句柄 为 0 表示 Job Object 绑定失败降级（走 taskkill 路径）；
            # 非 0 才是真正的 Job Object 根治路径生效。
            assert 树.任务句柄 != 0, "Job Object 未绑定（任务句柄应为非零有效句柄）"
        finally:
            树.杀树(3000)

    def test_杀树_整树被回收且无关进程存活(self):
        # 一个与本树完全无关的存活进程（父是本测试进程，不在 root 之下）
        幸存 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])

        # 子脚本：spawn 一个孙进程（睡眠 30s）后自己也睡 30s → 形成 根→子→孙 三层。
        child_src = (
            "import subprocess, sys, time\n"
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
            "time.sleep(30)\n"
        )
        child_path = os.path.join(tempfile.gettempdir(), "_r95_jo_child.py")
        with open(child_path, "w", encoding="utf-8") as fh:
            fh.write(child_src)

        树 = 进程树([sys.executable, child_path], {})
        assert 树.启动() is True
        root = 树.进程对象.pid
        # 杀前枚举后代（root 仍存活期，BFS 能拿到完整链）
        后代 = 树.枚举后代(root)
        try:
            树.杀树(5000)
        finally:
            pass

        def 全gone(pids, 上限=10.0):
            t0 = time.time()
            while time.time() - t0 < 上限:
                if all(not 树.能打开(p) for p in pids):
                    return True
                time.sleep(0.1)
            return all(not 树.能打开(p) for p in pids)

        assert 全gone([root] + 后代), (
            f"杀树后整树未回收：仍存活 {[p for p in [root] + 后代 if 树.能打开(p)]}"
        )
        # 关键断言：无关进程绝不能被误杀
        assert 树.能打开(幸存.pid), "无关进程被误杀！Job Object / 创建时间闸门失效"
        幸存.kill()
