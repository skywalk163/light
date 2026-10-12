# -*- coding: utf-8 -*-
"""test_R141_L195_方法形参.py —— R141-A2：原生腿「类方法形参绑定错位一位」

被测缺陷（R141-A 定位，本轮修复）：

  **L-195** 原生腿类方法的形参绑定**整体错位一位**。
  实例/类方法的第一个形参 `自` 是**接收者占位符**，它不占用 `%args` 槽位——
  调用方只把显式实参装进 args，接收者由 `%self` 单独传
  （`void @_method_xxx(ptr %result, ptr %self, ptr %args, i32 %num_args)`）。
  修前 `_gen_typed_method` 把 `自` 当成 args[0] 绑定，于是用户形参整体后移一位：

      段落 加(自, a, b, c):  …
      对.加(3, 4, 5)          → 修前 a=4 / b=5 / c=空      ← 错位
                              → 修后 a=3 / b=4 / c=5       ← 对齐 Python 腿

  影响面：**所有带参类方法**。这是一个静默的语义错误——不崩、不报错，只是算错，
  因此比 L-194（内存暴涨）更危险。L-194 正是它的下游后果（见 `_R141_A线定位报告.md`）。

判实方式（全部**真编译 + 真运行**，且**两腿对拍**）：

  只断言「原生腿等于某个期望值」是不够的——那正是缺陷藏身的方式（错位后每个
  位置仍是一个「合理的值」）。每条用例都要求：
      原生腿输出 == Python 腿输出 == 显式期望值
  三者缺一不可。

反跑（证明断言有牙，已在 0.82 实测）：
  把 `_gen_typed_method` 里接收者占位符的判定名元组改成永不匹配的值后，
  本文件 3 条用例立即由绿转红（`4/5/空`、`空`），改回即绿。
  未把反跑写进自动化用例，因为它需要改 `src/`，属 CI 不该做的事。

平台：本机 Windows **不实跑**（项目铁律），全部在 192.168.0.82（FreeBSD 15.1）执行。
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
    # 两腿都必须真的跑起来，否则下面的对拍就是在比较两次「没跑起来」
    assert 原_rc == 0, '原生腿 rc=%s stderr=%s' % (原_rc, 原_出)
    assert py_rc == 0, 'Python 腿 rc=%s stderr=%s' % (py_rc, py_出)
    return 原_出, py_出


# ---------------------------------------------------------------- 用例

三参源 = """类 小:
  段落 初始化(自):
    设 己.值 为 0
  段落 加(自, a, b, c):
    返回 转字符串(a) 加上 "/" 加上 转字符串(b) 加上 "/" 加上 转字符串(c)

段落 主():
  设 对 为 新建 小()
  输出("三参=" 加上 对.加(3, 4, 5))
"""

单参源 = """类 小:
  段落 初始化(自):
    设 己.值 为 0
  段落 回参(自, v):
    返回 v

段落 主():
  设 对 为 新建 小()
  输出("单参=" 加上 转字符串(对.回参(42)))
"""

两参源 = """类 小:
  段落 初始化(自):
    设 己.值 为 0
  段落 加(自, a, b):
    返回 转字符串(a) 加上 "/" 加上 转字符串(b)

段落 主():
  设 对 为 新建 小()
  输出("两参=" 加上 对.加(3, 4))
"""

顶层源 = """段落 加(a, b):
  返回 转字符串(a) 加上 "/" 加上 转字符串(b)

段落 主():
  输出("顶层=" 加上 加(3, 4))
"""


@skip_without_clang
def test_三参方法_三个位置全部对齐(tmp_path):
    """L-195 主判据：a/b/c 三个位置都要对，不能只验一个位置。

    只验「a 有值」会漏——错位后 a 照样有值（拿到的是第二个实参）。
    """
    原, py = 双腿跑(tmp_path, '三参', 三参源)
    assert 原 == ['三参=3/4/5'], '原生腿=%s' % 原
    assert py == ['三参=3/4/5'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_单参方法_形参不再为空(tmp_path):
    """修前 `回参(自, v)` 里 v 取 args[1] 越界 → 空。"""
    原, py = 双腿跑(tmp_path, '单参', 单参源)
    assert 原 == ['单参=42'], '原生腿=%s' % 原
    assert py == ['单参=42'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_两参方法_末位不再为空(tmp_path):
    """修前 `加(自, a, b)` 调 (3,4) → a=4 / b=空；末位是空最容易被测漏。"""
    原, py = 双腿跑(tmp_path, '两参', 两参源)
    assert 原 == ['两参=3/4'], '原生腿=%s' % 原
    assert py == ['两参=3/4'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_顶层段落不受影响_对照组(tmp_path):
    """对照组：顶层 `段落`（无 `自`）的形参本来就正常，本次修复不许把它改坏。"""
    原, py = 双腿跑(tmp_path, '顶层', 顶层源)
    assert 原 == ['顶层=3/4'], '原生腿=%s' % 原
    assert py == ['顶层=3/4'], 'Python 腿=%s' % py
    assert 原 == py
