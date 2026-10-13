# -*- coding: utf-8 -*-
"""test_R146_L204_嵌套dict深拷贝.py —— R146-A（L-204 修复）。

被测缺陷（R145-B 发现，R146-A 定位与修复，符号级）：
  L-204 原生腿「类字段存嵌套 dict 读回内层键错乱」。
  `设 己.回 为 {"错误":{"码":-1,"消息":"连接失败"},"结果":空}` 读回 `对.回` →
  `{'错误': {'': -1, 空: '结果'}, '结果': 空}`（内层键 `码`/`消息` 变空；顶层键完好）。

根因：`src/llvm/runtime_typed.c` 的 `dv_clone` DICT（type 7）分支是**浅拷贝**——
  只共享 `list_data` 指针。`dv_dict_set` 把内层 dict 值 `dv_clone` 进外层后，
  内层临时 dict 被 `dv_free` **深释放**（连 list_data 与每个 key/val 一起 free），
  外层 dict 的 `list_data` 随即悬空 → 键/值读回错乱。
  W4（类字段路径）触发；W3（顶层变量路径）因 LLVM 生命周期恰好不触发 dv_free 而正常。

修复：`dv_clone` DICT 分支由浅拷贝改为**深拷贝**——独立分配 `list_data`，
  并对每个 key/val 递归 `dv_clone`（与既有 LIST 分支同口径）。
  与 `dv_dict_get` 返回 REF 的原地修改路径不冲突：REF 指向 `dv_dict_set` 内堆分配的
  new_val 本体，深拷贝的是**插入时**的值，互不影响。

判实方式（真编译 + 真运行 + 两腿对拍）：
  原生腿输出 == Python 腿输出 == 显式期望值。
  ⚠️ 断言口径：两腿的 dict **字符串化格式**本就不同（native 单引号 / src 双引号，
  属既有跨腿差异，与 L-204 无关），故本用例断言的是**内层键的读回值**
  （双腿一致），而非整串序列化结果。

覆盖：
  W4  类字段存嵌套 dict → 读回内层 `码` / `消息`（修前内层键变空 → 读回空）。
  W3  顶层变量存嵌套 dict（对照组，修前即正常，护栏不回退）。
  W5  嵌套 dict 再套一层（三级），验证深拷贝递归正确。

反跑（证明断言有牙；已在 Windows 本机实测，不写进自动化用例——它需改 src/）：
  把 `dv_clone` DICT 分支改回浅拷贝 → W4/W5 立即由绿转红（原生腿读回空）；
  恢复深拷贝 → 全绿。W3 在反跑中仍通过（顶层变量路径不触发 dv_free）——
  正是 L-204 必须用**类字段**路径才能证明的原因。
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
    结果 = subprocess.run([exe], timeout=180, cwd=目录, **子进程口径)
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
    assert 原_rc == 0, '原生腿 rc=%s 输出=%s' % (原_rc, 原_出)
    assert py_rc == 0, 'Python 腿 rc=%s 输出=%s' % (py_rc, py_出)
    return 原_出, py_出


# W4：类字段存嵌套 dict → 读回内层键（L-204 主证据）
W4 = """类 仓库:
  段落 设置回():
    设 己.回 为 {"错误":{"码":-1,"消息":"连接失败"},"结果":"ok"}
    返回 空

段落 主():
  设 a 为 新建 仓库()
  a.设置回()
  输出("码=" 加上 转字符串(a.回["错误"]["码"]) 加上 " 消息=" 加上 转字符串(a.回["错误"]["消息"]))
"""

# W3：顶层变量存嵌套 dict（对照组，修前即正常，护栏不回退）
W3 = """段落 主():
  设 d 为 {"错误":{"码":-1,"消息":"连接失败"},"结果":"ok"}
  输出("码=" 加上 转字符串(d["错误"]["码"]) 加上 " 消息=" 加上 转字符串(d["错误"]["消息"]))
"""

# W5：三级嵌套 —— 验证深拷贝递归正确（不只修了一层）
W5 = """类 仓库:
  段落 设置回():
    设 己.回 为 {"外层":{"中层":{"码":-1,"消息":"连接失败"}},"结果":"ok"}
    返回 空

段落 主():
  设 a 为 新建 仓库()
  a.设置回()
  输出("码=" 加上 转字符串(a.回["外层"]["中层"]["码"]) 加上 " 消息=" 加上 转字符串(a.回["外层"]["中层"]["消息"]))
"""


@skip_without_clang
def test_W4_类字段嵌套dict_内层键读回(tmp_path):
    """L-204 主证据：类字段存嵌套 dict，内层键 `码`/`消息` 不得错乱为空。

    修前 native 内层键变空 → 读回空；修后 `码=-1 消息=连接失败`。
    """
    原, py = 双腿跑(tmp_path, 'W4', W4)
    assert 原 == ['码=-1 消息=连接失败'], '原生腿=%s' % 原
    assert py == ['码=-1 消息=连接失败'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_W3_顶层变量嵌套dict_对照组(tmp_path):
    """对照组：顶层变量路径（W3）修前即正常，用于护栏不回退。"""
    原, py = 双腿跑(tmp_path, 'W3', W3)
    assert 原 == ['码=-1 消息=连接失败'], '原生腿=%s' % 原
    assert py == ['码=-1 消息=连接失败'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_W5_三级嵌套dict_深拷贝递归(tmp_path):
    """深拷贝递归验证：三层嵌套时最内层键仍应完整读回。"""
    原, py = 双腿跑(tmp_path, 'W5', W5)
    assert 原 == ['码=-1 消息=连接失败'], '原生腿=%s' % 原
    assert py == ['码=-1 消息=连接失败'], 'Python 腿=%s' % py
    assert 原 == py
