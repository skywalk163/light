# -*- coding: utf-8 -*-
"""test_R142_L196_异步方法形参与协程.py —— R142-A（L-196）。

被测缺陷（R142-A 定位与修复）：
  L-196 原生腿「异步上下文里带参方法调用不执行 + 协程 await 触发 IR 支配域错误」。
  两层根因（R141 已实证，本轮在 src/compiler.py::AstAdapter 收口）：
    ① 形参丢失：类体内 `异步 段落 名(形参…)` 在 v3 AST 是 Paragraph 节点
       （形参在 params、修饰符在 modifiers），AstAdapter 只读 parameters → 形参整体
       丢失（v 走「未知标识符当字符串常量」兜底，实测写后为字符串 "v"）。
       修复：`_convert_method_definition` / 构造器 加 `parameters 取不到则取 params` 兼容
       （与转译腿 code_generator.py:3754-3757 同口径）。
    ② 协程识别：MethodDefinition 无 modifiers 槽，原生 codegen 读不到 `异步` → 异步类
       方法被当普通方法，协程内 `等待 方法()` 发射的指令与 Duff's device 状态机产生 SSA
       支配冲突（编译失败：Instruction does not dominate all uses）。
       修复：新增 `_ModifiersMethodDefinition` 子类透传 modifiers，使原生 codegen
       把异步类方法正确生成协程。

判实方式（全部真编译 + 真运行 + 两腿对拍，仿 test_R141_L195_方法形参.py）：
    原生腿输出 == Python 腿输出 == 显式期望值，三者缺一不可。

覆盖：
  A1  异步类方法带参（形参丢失修复）—— 写后应为 9，坏时为字符串 "v"。
  A2  协程内 await 带参异步方法（支配域修复）—— r=12，坏时编译失败。
  CTRL 异步类方法无参（modifiers 透传不得破坏无参异步方法）。

反跑（证明断言有牙，已在 0.82 实测）：
  把 src/compiler.py::AstAdapter._convert_method_definition 里
  `形参源 = getattr(node, 'parameters', None); if 形参源 is None: 形参源 = getattr(node, 'params', None)`
  改回只取 `parameters`，A1 用例立即由绿转红（写后="v"）；改回即绿。
  （反跑不写进自动化用例——它需要改 src/，属 CI 不该做的事。）

平台：本机 Windows 不实跑（项目铁律），全部在 192.168.0.82（FreeBSD 15.1）执行。
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _native_helpers import 仓库根, skip_without_clang  # type: ignore[import]

_SRC = os.path.join(仓库根, 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

子进程口径 = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')


def 写文件(目录, 文件名, 内容):
    """无 BOM 写 .light（BOM 会被词法层当字符卡住）"""
    路径 = os.path.join(目录, 文件名)
    with open(路径, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(内容)
    return 路径


def 原生腿跑(主文件, 目录):
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    exe = compile_light_typed(主文件, os.path.join(目录, '产物'), optimize_level=2)
    结果 = subprocess.run([exe], timeout=120, cwd=目录, **子进程口径)
    return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


def python腿跑(主文件, 目录):
    结果 = subprocess.run(
        [sys.executable, os.path.join(仓库根, 'cli', 'light.py'), 'run', 主文件],
        cwd=目录, timeout=180, **子进程口径)
    return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


def 双腿跑(tmp_path, 名, 源):
    """返回 (原生腿输出, Python腿输出)。两腿都真编译/真运行。"""
    目录 = str(tmp_path / 名)
    os.makedirs(目录, exist_ok=True)
    主文件 = 写文件(目录, 名 + '.light', 源)
    原_rc, 原_出 = 原生腿跑(主文件, 目录)
    py_rc, py_出 = python腿跑(主文件, 目录)
    assert 原_rc == 0, '原生腿 rc=%s' % 原_出
    assert py_rc == 0, 'Python 腿 rc=%s' % py_出
    return 原_出, py_出


# A1：异步类方法带参（形参丢失修复）—— 写后应为 9，坏时为字符串 "v"
A1 = """类 小:
  段落 初始化(自):
    设 己.值 为 0
  异步 段落 存值(自, v):
    设 己.值 为 v
  段落 读(自):
    返回 己.值

段落 主():
  设 对 为 新建 小()
  异步 运行 对.存值(9)
  输出("写后=" 加上 转字符串(对.读()))
"""

# A2：协程内 await 带参异步方法（支配域修复）—— r=12，坏时编译失败
A2 = """类 小:
  异步 段落 加异(自, a):
    返回 a 加上 1
  异步 段落 驱动(自):
    设 r 为 等待 自.加异(11)
    设 己.记 为 r

段落 主():
  设 对 为 新建 小()
  异步 运行 对.驱动()
  输出("r=" 加上 转字符串(对.记))
"""

# CTRL：异步类方法无参（modifiers 透传不得破坏无参异步方法）
CTRL = """类 小:
  异步 段落 给值(自):
    返回 7
  异步 段落 驱动(自):
    设 己.记 为 等待 自.给值()

段落 主():
  设 对 为 新建 小()
  异步 运行 对.驱动()
  输出("r=" 加上 转字符串(对.记))
"""


@skip_without_clang
def test_A1_异步方法带参_写后正确(tmp_path):
    """L-196 根因①：异步类方法形参不再丢失。

    修前 `异步 段落 存值(自, v)` 里 v 取不到形参 → 当字符串常量 "v"，写后="v"。
    """
    原, py = 双腿跑(tmp_path, 'A1', A1)
    assert 原 == ['写后=9'], '原生腿=%s' % 原
    assert py == ['写后=9'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_A2_协程内await带参异步方法(tmp_path):
    """L-196 根因②：协程内 `等待 带参异步方法` 编译通过且返回正确。

    修前编译失败：LLVM IR 验证失败: Instruction does not dominate all uses。
    """
    原, py = 双腿跑(tmp_path, 'A2', A2)
    assert 原 == ['r=12'], '原生腿=%s' % 原
    assert py == ['r=12'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_CTRL_异步方法无参_对照组(tmp_path):
    """对照组：异步类方法无参（modifiers 透传不得破坏无参异步方法）。"""
    原, py = 双腿跑(tmp_path, 'CTRL', CTRL)
    assert 原 == ['r=7'], '原生腿=%s' % 原
    assert py == ['r=7'], 'Python 腿=%s' % py
    assert 原 == py
