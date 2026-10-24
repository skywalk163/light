# -*- coding: utf-8 -*-
"""test_R143_L198_嵌套异步写实例.py —— R143-A（L-198）。

被测缺陷（缺陷账 L-198，约 711-750 行）：
  L-198 声称「原生腿嵌套异步方法实例实例的属性写不回写」——被 `等待` 的嵌套异步
  方法实例 self 的属性写操作不回写到真实实例。最小复现用单级嵌套（主 → 外 → 内），
  期望嵌套方法实例 `己` 的写能穿透回真实实例。

判实方式（全部真编译 + 真运行 + 两腿实例拍，仿 test_R142_L196_异步方法形参与协程.py）：
  原生腿输出 == Python 腿输出 == 显式期望值，三者缺一不可。

⚠️ 关键实证结论（R143-A 在 0.82 实测）：
  用**干净方法名**（如 存值/写值/取，避开内置名）时，单级乃至多级嵌套异步方法实例
  实例属性的写——无论写已有字段还是新字段、无论外层是否显式 返回、无论是否经
  `异步睡眠` 真正挂起——**都能正确回写真实实例**（下列 P1-P4 全部 =9）。原生 codegen
  实例方法入口做 `dv_obj_deepcopy_self`（R140-A 为修 L-182/L-191 UAF 引入），方法出口经
  `_emit_self_writeback` 把局部 `己` 槽写回 `%self`，深拷贝 + 写回模型可跨嵌套边界传播，
  故 L-198 文档化的「写只改副本、返回后丢弃」**在干净命名下并不复现**。

  缺陷账 L-198 的最小复现与 A3 探针（`等待 自.写(9)`）之所以读到 0，根因是方法名 `写`
  撞上文件内置 `写`/`write`（`dv_file_write`），`等待 自.写(9)` 被编译成文件写而非实例方法
  调用——这正是缺陷账 686-687 行 L-196 已点名的同名坑，与 L-198 的深拷贝写回无涉。
  故本测试以 `写` 名探针作为「反跑有牙」实例照（它确实读=0，但病因是命名碰撞而非写回模型），
  真正锁定 L-198 写回正确性的，是下面 P1-P4 干净命名探针。

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
    assert 原_rc == 0, '原生腿 rc=%s out=%s' % (原_rc, 原_出)
    assert py_rc == 0, 'Python 腿 rc=%s out=%s' % (py_rc, py_出)
    return 原_出, py_出


# P1：嵌套返回**值** + 外层把返回值写进属性（值型写回，跨一层嵌套）
P1 = """类 小:
  段落 初始化(自):
    设 己.值 为 0
  异步 段落 取(自):
    返回 9
  异步 段落 外(自):
    设 己.值 为 等待 自.取()
段落 主():
  设 实例 为 新建 小()
  异步 运行 实例.外()
  输出("读=" 加上 转字符串(实例.值))
"""

# P2：嵌套方法**写**属性（副作用，最深一层内层方法写已有字段）
P2 = """类 小:
  段落 初始化(自):
    设 己.值 为 0
  异步 段落 写值(自, x):
    设 己.值 为 x
  异步 段落 外(自):
    等待 自.写值(9)
段落 主():
  设 实例 为 新建 小()
  异步 运行 实例.外()
  输出("读=" 加上 转字符串(实例.值))
"""

# P3：嵌套方法写**新**属性（此前不存在的字段，深拷贝下应能新建并写回）
P3 = """类 小:
  段落 初始化(自):
    设 己.值 为 0
  异步 段落 写新(自, x):
    设 己.新 为 x
  异步 段落 外(自):
    等待 自.写新(9)
段落 主():
  设 实例 为 新建 小()
  异步 运行 实例.外()
  输出("读=" 加上 转字符串(实例.新))
"""

# P4：同一协程内写属性（无嵌套），实例照基线
P4 = """类 小:
  段落 初始化(自):
    设 己.值 为 0
  异步 段落 外(自):
    设 己.值 为 9
段落 主():
  设 实例 为 新建 小()
  异步 运行 实例.外()
  输出("读=" 加上 转字符串(实例.值))
"""


@skip_without_clang
def test_P1_嵌套返回写属性_读9(tmp_path):
    """L-198 P1：嵌套返回值 + 外层写属性，应读=9（读=0 才是坏）。"""
    原, py = 双腿跑(tmp_path, 'P1', P1)
    assert 原 == ['读=9'], '原生腿=%s' % 原
    assert py == ['读=9'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_P2_嵌套方法写属性_读9(tmp_path):
    """L-198 P2（死穴）：嵌套方法实例实例属性的副作用写，应穿透回真实实例读=9。"""
    原, py = 双腿跑(tmp_path, 'P2', P2)
    assert 原 == ['读=9'], '原生腿=%s' % 原
    assert py == ['读=9'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_P3_嵌套方法写新属性_读9(tmp_path):
    """L-198 P3（死穴）：嵌套方法写此前不存在的新属性，应读=9（读=空 才是坏）。"""
    原, py = 双腿跑(tmp_path, 'P3', P3)
    assert 原 == ['读=9'], '原生腿=%s' % 原
    assert py == ['读=9'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_P4_同协程写属性_读9(tmp_path):
    """L-198 P4：非嵌套（同一协程内）写属性，应读=9（实例照基线）。"""
    原, py = 双腿跑(tmp_path, 'P4', P4)
    assert 原 == ['读=9'], '原生腿=%s' % 原
    assert py == ['读=9'], 'Python 腿=%s' % py
    assert 原 == py


# R164-A（L-198 收口）：原生腿命名截胡已修——`自`/`己` 接收器 + 类同名方法优先于
# 一切内置分派（不再限 mutating_methods 名单），`等待 自.写(9)` 两腿都正确落到
# 实例方法、写回 值=9。本探针由「反跑有牙」翻面为「修复后双腿一致」正断言；
# 反跑改由交付报告手证（回退 codegen 三处改动 ⇒ 原生腿读=0）。
碰撞 = """类 小:
  段落 初始化(自):
    设 己.值 为 0
  异步 段落 写(自, x):
    设 己.值 为 x
  异步 段落 读异(自):
    等待 自.写(9)
段落 主():
  设 实例 为 新建 小()
  异步 运行 实例.读异()
  输出("读=" 加上 转字符串(实例.值))
"""


@skip_without_clang
def test_R164A_写名_双腿一致读9(tmp_path):
    """R164-A（L-198 收口）：方法名 `写` 撞文件写内置 `dv_file_write` 的截胡已修。

    修前（R143 反跑锚点）：仅原生腿被截胡读=0，Python 腿读=9。
    修后：原生腿类同名方法优先 ⇒ 两腿皆读=9，与 SRC 腿一致。"""
    原, py = 双腿跑(tmp_path, '碰撞', 碰撞)
    assert 原 == ['读=9'], '原生腿=%s' % 原
    assert py == ['读=9'], 'Python 腿=%s' % py
    assert 原 == py
