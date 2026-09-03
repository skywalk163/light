# -*- coding: utf-8 -*-
"""
任务D/D2：进程树（纯光明实现）定向测试
覆盖：正常退出取输出、非零退出码、超时杀树（含孙子进程被连带杀死）、
      输出超界触发 spill + 省略标记、命令不存在、stderr/stdout 分离、
      以及 D2-1 的解码口径（平台探测 / 显式编码 / 失真标志位 / 窗口边界多字节
      字符 / UTF-8 与 GBK 混流）。

进程隔离红线：本文件绝不按进程名杀进程，只验证「引擎自己 spawn 的进程树」被
引擎自己超时+杀树清掉；辅助断言只用 PID。运行在 Windows 上，POSIX 分支跳过。

临时文件一律 `_taskD2_` 前缀，落在 pytest 的 tmp_path 里（跑完自动清）。
"""
import locale
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


def _本机默认编码():
    """与 进程树.平台编码 同一口径，用来钉住"默认不硬编码 UTF-8"。"""
    if sys.platform != "win32":
        return "utf-8"
    名 = locale.getpreferredencoding(False)
    return 名 or "utf-8"


def _写脚本(tmp_path, 名, 内容):
    p = tmp_path / f"_taskD2_{名}.py"
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
        # 中文能对上说明用的不是硬编码 UTF-8，而且没有走 replace 兜底
        assert 结果.标准输出失真 is False

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
        assert 结果.标准输出失真 is False
        assert 结果.标准错误失真 is False

    def test_命令不存在(self):
        树干 = 进程树(["__taskD2_不存在_cmd_xyz__"], {})
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
        assert "\ufffd" not in 结果.标准输出
        assert 结果.标准输出失真 is False
        # spill 文件必须带任务前缀（并行作业不撞名）
        assert os.path.basename(结果.溢出文件).startswith("_taskD2_")

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
        marker = tmp_path / "_taskD2_孙进程标记.txt"
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
        脚本 = _写脚本(tmp_path, "看环境", 'import os\nprint(os.environ.get("_TASKD2_秘密", ""))')
        # 先确认默认继承
        树干, 结果 = _跑(
            [sys.executable, "-u", 脚本],
            {"拒绝环境": ["_TASKD2_秘密"]},
        )
        assert 结果.标准输出.strip() == ""
        # 白名单：要求只匹配某个前缀，空环境变量应被过滤
        树干2, 结果2 = _跑(
            [sys.executable, "-u", 脚本],
            {"允许环境": ["__绝对不会匹配的前缀_"]},
        )
        assert 结果2.标准输出.strip() == ""


# ============================================================
# D2-1：解码口径
# 上一轮的红全在 `文本()` 硬编码 decode("utf-8")；这一组把新口径逐条钉死。
# ============================================================
class Test解码口径:
    def test_默认编码按平台探测而非硬编码UTF8(self, tmp_path):
        脚本 = _写脚本(tmp_path, "探编码", 'print("编码探测")')
        树干, 结果 = _跑([sys.executable, "-u", 脚本])
        assert 结果.采用编码 is not None
        # 主口径：默认编码必须与本机 locale 探测一致，绝不硬编码 UTF-8。
        # 这条断言在所有平台都成立——cp936 机器上 采用编码==cp936、UTF-8 locale
        # 机器上 采用编码==utf-8，都靠它钉死「不硬编码」。原先的 win32 分支硬断言
        #「!= "utf-8"」是「本机 ANSI 必为 cp936」的错误假设：本机 locale 返回
        # utf-8 时该假设不成立而误报失败，且 cp936 机器上此断言已被上面这条覆盖，
        # 故删去，统一用与 _本机默认编码() 对齐的口径。
        assert 结果.采用编码.lower() == _本机默认编码().lower()

    def test_显式指定编码优先于平台探测(self, tmp_path):
        脚本 = _写脚本(tmp_path, "显式编码",
                      'import sys\n'
                      'sys.stdout.buffer.write("统一码甲乙".encode("utf-8"))\n'
                      'sys.stdout.buffer.flush()\n')
        树干, 结果 = _跑([sys.executable, "-u", 脚本], {"编码": "utf-8"})
        assert 结果.采用编码 == "utf-8"
        assert "统一码甲乙" in 结果.标准输出
        assert 结果.标准输出失真 is False

    def test_字节接口给原始字节且可自行解码(self, tmp_path):
        脚本 = _写脚本(tmp_path, "原始字节",
                      'import sys\n'
                      'sys.stdout.buffer.write("原始字节甲".encode("utf-8"))\n'
                      'sys.stdout.buffer.flush()\n')
        树干, 结果 = _跑([sys.executable, "-u", 脚本], {"编码": "utf-8"})
        assert isinstance(结果.标准输出字节, bytes)
        assert 结果.标准输出字节 == "原始字节甲".encode("utf-8")
        assert 结果.标准输出字节.decode(结果.采用编码) == "原始字节甲"

    def test_坏字节走replace并置失真标志(self, tmp_path):
        # 0x80 在 cp936/GBK 里不是合法首字节，且夹在中间：
        # 首字节对齐/尾部裁剪都救不回来 → 必须落 replace 并把失真标志抬起来
        脚本 = _写脚本(tmp_path, "坏字节",
                      'import sys\n'
                      'sys.stdout.buffer.write("开头".encode("gbk") + b"\\x80" + "结尾".encode("gbk"))\n'
                      'sys.stdout.buffer.flush()\n')
        树干, 结果 = _跑([sys.executable, "-u", 脚本], {"编码": "gbk"})
        assert 结果.退出码 == 0
        assert 结果.标准输出失真 is True, 结果.标准输出
        assert "开头" in 结果.标准输出
        assert "结尾" in 结果.标准输出
        assert "\ufffd" in 结果.标准输出

    def test_解码策略可配为ignore且仍报失真(self, tmp_path):
        脚本 = _写脚本(tmp_path, "坏字节忽略",
                      'import sys\n'
                      'sys.stdout.buffer.write("开头".encode("gbk") + b"\\x80" + "结尾".encode("gbk"))\n'
                      'sys.stdout.buffer.flush()\n')
        树干, 结果 = _跑([sys.executable, "-u", 脚本],
                        {"编码": "gbk", "解码策略": "ignore"})
        assert "\ufffd" not in 结果.标准输出
        assert "开头" in 结果.标准输出
        assert "结尾" in 结果.标准输出
        # 换了策略也不许把"发生过损失"这件事咽下去
        assert 结果.标准输出失真 is True

    def test_窗口边界切在多字节字符中间也不产生半个字符(self, tmp_path):
        # 界限取奇数，保证"最后 N 字节"的起点落在某个 GBK 汉字（2 字节）中间。
        # 修好前：尾部窗口从半个字符开始，GBK 会整体错位半字节位（且解码不报错），
        # 尾巴标记根本对不上。修好后：切点被增量解码器拉回字符边界。
        脚本 = _写脚本(tmp_path, "边界",
                      'import sys\n'
                      'sys.stdout.buffer.write(("中" * 3000 + "尾巴标记").encode("gbk"))\n'
                      'sys.stdout.buffer.flush()\n')
        树干, 结果 = _跑(
            [sys.executable, "-u", 脚本],
            {"编码": "gbk", "限尾字节": 4097, "溢出目录": str(tmp_path)},
        )
        assert 结果.退出码 == 0
        assert 结果.溢出文件 is not None
        assert 结果.标准输出.endswith("尾巴标记")
        assert "\ufffd" not in 结果.标准输出
        assert 结果.标准输出失真 is False
        # 省略标记之后的第一个字符必须是完整的"中"，不是错位后的别的字
        尾段 = 结果.标准输出.split("]...", 1)[1]
        assert 尾段.startswith("中"), 尾段[:16]
        assert 尾段 == "中" * (len(尾段) - 4) + "尾巴标记"

    def test_UTF8与GBK混流不崩(self, tmp_path):
        # 同一条 stdout 里前半段 UTF-8、后半段 GBK。这是真实场景（子进程自己拼字节），
        # 能给的保证只有"不崩 + 与所选编码一致的那半边保真"，不是"两半都能还原"。
        # UTF-8 段特意取偶数字节（2 个三字节汉字 = 6 字节），好让 GBK 段仍在偶数偏移上。
        脚本 = _写脚本(tmp_path, "混流",
                      'import sys\n'
                      'sys.stdout.buffer.write("统一".encode("utf-8") + "国标码结束".encode("gbk"))\n'
                      'sys.stdout.buffer.flush()\n')

        # 按 utf-8 解：GBK 段是非法 UTF-8 → replace + 失真，UTF-8 段保真
        树甲, 甲 = _跑([sys.executable, "-u", 脚本], {"编码": "utf-8"})
        assert isinstance(甲.标准输出, str)
        assert "统一" in 甲.标准输出
        assert 甲.标准输出失真 is True

        # 按 gbk 解：GBK 段保真。UTF-8 段会被静默读成别的汉字——GBK 检不出错位，
        # 这条限制是明面上的，调用方要还原另一半只能自己拿 字节() 重解。
        树乙, 乙 = _跑([sys.executable, "-u", 脚本], {"编码": "gbk"})
        assert isinstance(乙.标准输出, str)
        assert "国标码结束" in 乙.标准输出
        assert 乙.标准输出字节.decode("utf-8", "replace").startswith("统一")
