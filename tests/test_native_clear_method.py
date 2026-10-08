# -*- coding: utf-8 -*-
"""test_native_clear_method.py —— R124-C3：obj.清空() 原生腿侧反跑用例

背景：`src/llvm/codegen_typed.py` 的 `mutating_methods` 在**原生腿侧**仍含
「清空」。于是 `c.清空()`（c 是**自定义类实例**）被 codegen 截胡成容器清空
（list.clear / dict.clear 那类内建分派），而不是走类里定义的 `清空` 段。
R123-A2 已确认**转译腿**侧自洽，但原生腿侧这条反跑此前零覆盖。

R123 实测（_r123_scratch/probe_清空反跑.light，双腿对拍）：
  - 转译腿：`c.n after c.清空() = 0`  —— 走类方法，正确。
  - 原生腿：`c.n after c.清空() = `（空）—— 被截胡，c.n 没有归零。

R124 只登记不修（落 xfail）。R125-A2 真修：
  codegen_typed.py 增加类实例静态跟踪（`设 c 为 新建 X()` 记 c->X），
  接收者是已跟踪类实例且方法名在该类继承链上有定义时，优先走
  dv_call_method（类方法），不再被内置 mutating 分派截胡；容器字段
  （己.数据 等）不在跟踪名单，SSE 字段写回语义原样保留。
  按本文件预留的转正路径：R125 摘掉 @xfail 标记，反跑转真绿。
"""
import importlib
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _native_helpers import 仓库根, skip_without_clang  # type: ignore[import]

if os.path.join(仓库根, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(仓库根, 'src'))

# 自包含探针：自定义类带 清空 段，新建后置 c.n=5，调 c.清空() 后应归零。
# 顶层 打印 一行 `RESULT=<值>` 供两腿分别解析。
_灯源码 = '''类 计数器:
 段 初始化():
    己.n 为 0
 段 清空():
    己.n 为 0

设 c 为 新建 计数器()
c.n 为 5
c.清空()
打印("RESULT=" + 转字符串(c.n))
'''


def _写临时灯(目录):
    """无 BOM 写入 .light（与 tests/_native_helpers 同款口径）。"""
    路径 = os.path.join(目录, '清空反跑.light')
    with open(路径, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(_灯源码)
    return 路径


def _解析结果(输出文本):
    for 行 in (输出文本 or '').splitlines():
        if 行.strip().startswith('RESULT='):
            return 行.strip()[len('RESULT='):].strip()
    return None


@pytest.fixture()
def 临时灯(tmp_path):
    """把探针 .light 落到临时目录，返回 (目录, 主文件路径)。"""
    目录 = str(tmp_path)
    return 目录, _写临时灯(目录)


# ── 转译腿对照：真绿（不 xfail）────────────────────────────────────────────
def test_转译腿_清空走类方法(临时灯, capsys):
    """转译腿：c.清空() 必须走类里的 清空 段 ⇒ c.n 归零为 0。

    这是对照基线：证明「转译腿自洽」，原生腿的红是原生腿 codegen 截胡所致，
    不是这份 .light 本身写错。
    """
    目录, 主文件 = 临时灯
    import _light_import_hook  # type: ignore[import]
    _light_import_hook.install([目录])
    sys.modules.pop('清空反跑', None)
    try:
        importlib.import_module('清空反跑')
    finally:
        sys.modules.pop('清空反跑', None)
        try:
            _light_import_hook.uninstall()
        except Exception:
            pass
    值 = _解析结果(capsys.readouterr().out)
    assert 值 == '0', "转译腿：c.清空() 应走类方法使 c.n==0，stdout=%r" % (值,)


# ── 原生腿：R125-A2 真修后转正（原 R124 xfail 已摘除）──────────────────────
@skip_without_clang
def test_原生腿_清空应走类方法(临时灯):
    """原生腿反跑：自定义类的 清空() 段应被真调用，c.n 归零为 0。

    R123 实测修复前输出 `RESULT=`（空）—— 截胡实锤。
    R125-A2 修复（类实例跟踪 + mutating 撞名让位类方法）后 RESULT=0。
    """
    from llvm.compiler import compile_light_typed  # type: ignore[import]

    目录, 主文件 = 临时灯
    exe = compile_light_typed(主文件, os.path.join(目录, '产物'), optimize_level=2)
    结果 = subprocess.run([exe], capture_output=True, timeout=60,
                          text=True, encoding='utf-8', errors='replace')
    assert 结果.returncode == 0, "原生腿跑产物 rc=%d，stderr=%s" % (
        结果.returncode, 结果.stderr)
    值 = _解析结果(结果.stdout)
    assert 值 == '0', "原生腿：c.清空() 应走类方法使 c.n==0，实得 RESULT=%r" % (值,)
