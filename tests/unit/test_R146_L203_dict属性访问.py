# -*- coding: utf-8 -*-
"""test_R146_L203_dict属性访问.py —— R146-A（L-203 修复）。

被测缺陷（R145-B 发现，R146-A 定位与修复，符号级）：
  L-203 原生腿 dict `.键` 属性访问恒空。
  `src/llvm/codegen_typed.py::_gen_typed_property_access` 对属性访问**无条件**
  走 `dv_class_get_member`，dict（type 7）走这条路找不到成员 → 恒空；
  Python(src) 腿 `d.键` 正常返回 `-1`。

修复：
  - `src/llvm/runtime_typed.c` 新增 `dv_property_get(result, obj, field_name)`：
    obj 为 dict（type 7）→ 走 `dv_dict_get`（与下标访问同语义）；
    其余（类实例等）→ 走 `dv_class_get_member`。
  - `src/llvm/codegen_typed.py::_gen_typed_property_access` 由
    `dv_class_get_member` 改为 `dv_property_get`（运行时分派，兼容动态类型）。

判实方式（真编译 + 真运行 + 两腿对拍，仿 test_R145_R119B_嵌套对象字段写回.py）：
  原生腿输出 == Python 腿输出 == 显式期望值，三者缺一不可。

覆盖：
  P1  dict `.键` 取整数（修前 native 恒空，修后 -1）。
  P2  dict `.键` 取字符串（修前 native 恒空，修后 ok）。
  G1  **回归护栏**：类实例 `.字段` 属性访问仍必须走 dv_class_get_member——
      本修复改动的是属性访问的**总分派入口**，必须证明类成员访问未被带偏。
  G2  **回归护栏**：dict 下标访问 `d["键"]` 语义不变（未被本次改动影响）。

反跑（证明断言有牙；已在 Windows 本机实测，不写进自动化用例——它需改 src/，属 CI 不该做的事）：
  把 `_gen_typed_property_access` 的 `dv_property_get` 改回 `dv_class_get_member`
  → P1/P2 立即由绿转红（原生腿输出空）；恢复修复 → 全绿。
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


# P1：dict `.键` 取整数 —— 修前 native 输出空，修后 -1
P1 = """段落 主():
  设 d 为 {"码":-1}
  输出("码=" 加上 转字符串(d.码))
"""

# P2：dict `.键` 取字符串 —— 修前 native 输出空，修后 ok
P2 = """段落 主():
  设 d 为 {"名":"ok"}
  输出("名=" 加上 转字符串(d.名))
"""

# G1：回归护栏 —— 类实例 `.字段` 属性访问必须仍走 dv_class_get_member
G1 = """类 应答:
  段落 初始化(自, 码, 消息):
    设 己.码 为 码
    设 己.消息 为 消息

段落 主():
  设 a 为 新建 应答(-1, "连接失败")
  输出("码=" 加上 转字符串(a.码) 加上 " 消息=" 加上 转字符串(a.消息))
"""

# G2：回归护栏 —— dict 下标访问语义不变
G2 = """段落 主():
  设 d 为 {"码":-1}
  输出("码=" 加上 转字符串(d["码"]))
"""


@skip_without_clang
def test_P1_dict属性访问取整数(tmp_path):
    """L-203 最小复现：native 修前恒空、修后 -1；src 腿全程 -1。"""
    原, py = 双腿跑(tmp_path, 'P1', P1)
    assert 原 == ['码=-1'], '原生腿=%s' % 原
    assert py == ['码=-1'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_P2_dict属性访问取字符串(tmp_path):
    """dict 字符串值的 `.键` 访问（REF 解引用路径）同样修好。"""
    原, py = 双腿跑(tmp_path, 'P2', P2)
    assert 原 == ['名=ok'], '原生腿=%s' % 原
    assert py == ['名=ok'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_G1_回归护栏_类实例属性访问未受影响(tmp_path):
    """护栏：属性访问改走 dv_property_get 后，类实例成员访问仍正确。

    若 dv_property_get 的 dict/非 dict 分支判定写反，本例会红。
    """
    原, py = 双腿跑(tmp_path, 'G1', G1)
    assert 原 == ['码=-1 消息=连接失败'], '原生腿=%s' % 原
    assert py == ['码=-1 消息=连接失败'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_G2_回归护栏_dict下标访问未受影响(tmp_path):
    """护栏：dict 下标访问 `d["键"]` 不因本次改动而变化。"""
    原, py = 双腿跑(tmp_path, 'G2', G2)
    assert 原 == ['码=-1'], '原生腿=%s' % 原
    assert py == ['码=-1'], 'Python 腿=%s' % py
    assert 原 == py
