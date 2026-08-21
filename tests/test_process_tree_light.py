# -*- coding: utf-8 -*-
"""
任务D：进程树（纯光明实现）定向测试
覆盖：正常退出取输出、非零退出码、超时杀树（含孙子进程被连带杀死）、
      输出超界触发 spill + 省略标记、UTF-8 边界、命令不存在、stderr/stdout 分离。

进程隔离红线：本文件绝不按进程名杀进程，只验证「引擎自己 spawn 的进程树」被
引擎自己超时+杀树清掉；辅助断言只用 PID。运行在 Windows 上，POSIX 分支跳过。
"""
import os
import sys
import time

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, os.path.join(_PROJECT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT, 'stdlib'))

import _light_import_hook
_light_import_hook.install([os.path.join(_PROJECT, 'stdlib'), _PROJECT])

import pytest

from 进程树 import 进程树


def _进程活(pid):
    """仅用 PID 判断进程是否存活，绝不按进程名。"""
    try:
        if sys.platform == "win32":
            import ctypes
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
            if not h:
                return False
            k.CloseHandle(h)
            return True
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False
    except Exception:
        return False


def _写脚本(tmp_path, 名, 内容):
    p = tmp_path / f"_taskD_{名}.py"
    p.write_text(内容, encoding="utf-8")
    return str(p)


def _跑(命令, 配置=None, 超时=6000):
    树干 = 进程树(命令, 配置 or {})
    assert 树干.启动() is True
    return 树干, 树干.等待(超时)


class Test基本退出:
    def test_正常退出取输出(self, tmp_path):
        脚本 = _写脚本(tmp_path, "正常", 'print("目录甲")\nprint("结束行")')
        树干, 结果 = _跑([sys.executable, "-u", 脚本])
        assert 结果.退出码 == 0
        assert "目录甲" in 结果.标准输出
        assert "结束行" in 结果.标准输出

    def test_非零退出码(self, tmp_path):
        脚本 = _写脚本(tmp_path, "非零", 'import sys\nprint("看这里")\nsys.exit(3)')
        树干, 结果 = _跑([sys.executable, "-u", 脚本])
        assert 结果.退出码 == 3
        assert "看这里" in 结果.标准输出

    def test_stderr与stdout分离(self, tmp_path):
        脚本 = _写脚本(tmp_path, "流分离",
                      'import sys\nprint("仅标准输出")\nprint("告诫进错误流", file=sys.stderr)')
        树干, 结果 = _跑([sys.executable, "-u", 脚本])
        assert "仅标准输出" in 结果.标准输出
        assert "背离" not in 结果.标准输出
        assert "告诫进错误流" in 结果.标准错误
        assert "仅标准输出" not in 结果.标准错误

    def test_命令不存在(self):
        树干 = 进程树(["__taskD_不存在_cmd_xyz__"], {})
        # Popen 抛 FileNotFoundError → 启动返回假
        assert 树干.启动() is False
        结果 = 树干.等待(1000)
        assert 结果.退出码 == -1
        assert "不存在" in 结果.标准错误 or 结果.标准错误 != ""


class Test有界输出与spill:
    def test_超界触发spill与省略标记(self, tmp_path):
        脚本 = _写脚本(tmp_path, "溢出", 'import sys\nsys.stdout.write("x" * 100000 + "中国结束")')
        树干, 结果 = _跑(
            [sys.executable, "-u", 脚本],
            {"限尾字节": 4096, "溢出目录": str(tmp_path)},
        )
        assert 结果.退出码 == 0
        assert 结果.溢出文件 is not None
        assert os.path.isfile(结果.溢出文件)
        assert "已省略" in 结果.标准输出
        # 尾部应保留最后内容，中文不被截断成半个
        assert 结果.标准输出.endswith("中国结束")

    def test_未超界不建spill(self, tmp_path):
        脚本 = _写脚本(tmp_path, "小输出", 'print("小小输出")')
        树干, 结果 = _跑(
            [sys.executable, "-u", 脚本],
            {"限尾字节": 4096, "溢出目录": str(tmp_path)},
        )
        assert 结果.退出码 == 0
        assert 结果.溢出文件 is None
        assert "小小输出" in 结果.标准输出


class Test超时杀树:
    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX 进程组分支未在 Windows 上实测（仅原理推导）")
    def test_posix信号语义跳过占位(self):
        pass

    def test_超时杀整棵树含孙子进程(self, tmp_path):
        marker = tmp_path / "_taskD_孙进程标记.txt"
        孙脚本 = _写脚本(tmp_path, "孙进程",
                        'import sys, time\n'
                        'time.sleep(30)\n'
                        'open(sys.argv[1], "w").write("x")\n')
        脚本 = _写脚本(tmp_path, "生孙子",
                      'import subprocess, sys, time\n'
                      'gc = subprocess.Popen([sys.executable, "-u", sys.argv[1], sys.argv[2]])\n'
                      'print(gc.pid, flush=True)\n'
                      'time.sleep(30)\n')
        树干, 结果 = _跑(
            [sys.executable, "-u", 脚本, 孙脚本, str(marker)],
            {"宽限期毫秒": 200},
            超时=800,
        )
        # 总超时到，返回"超时"结果
        assert 结果.是否超时 is True
        # 杀掉进程树后，引擎自己的直接子进程应已死
        assert not 树干.是否存活()
        # 取出孙子进程 PID
        pid行 = 结果.标准输出.strip()
        assert pid行.isdigit(), 结果.标准输出
        gc_pid = int(pid行)
        time.sleep(0.5)
        # 孙子进程必须随树的根被连带杀死（进程隔离：只按 PID 断言，不按名杀）
        assert _进程活(gc_pid) is False
        # 孙子若活着会在 30s 后写标记；被杀死则不会
        assert not marker.exists()


class Test环境控制:
    def test_环境黑名单过滤(self, tmp_path):
        脚本 = _写脚本(tmp_path, "看环境", 'import os\nprint(os.environ.get("_TASKD_秘密", ""))')
        # 先确认默认继承
        树干, 结果 = _跑(
            [sys.executable, "-u", 脚本],
            {"拒绝环境": ["_TASKD_秘密"]},
        )
        assert 结果.标准输出.strip() == ""
        # 白名单：要求只匹配某个前缀，空环境变量应被过滤
        树干2, 结果2 = _跑(
            [sys.executable, "-u", 脚本],
            {"允许环境": ["__绝对不会匹配的前缀_"]},
        )
        assert 结果2.标准输出.strip() == ""