# -*- coding: utf-8 -*-
"""R12A 定向反跑测试：一元运算符/布尔逻辑/类型转换族 codegen 根因修复。

覆盖缺陷（R11 批 workaround 绕过、本批 codegen 根因修复）：
  R11B-1  非 假 → 应为 真（dv_eq(operand,0) 跨类型比较判错）
  R11A-01 非 函数调用 → 应取真值再取反（函数调用返回值布尔取反失效）
  R11B-2  整数(真) → 应为 1（dv_to_int 对 bool 落默认分支返回 0）
  R11A-07 且/或 应短路（假 且 报错() 不得求值右侧）

判据：修复前各用例红、修复后全绿；每用例独立编译运行（T5A 范式），
optimize_level=0 强 O0。只跑本文件，禁止全量。
"""
import os
import sys
import subprocess as _subproc
import tempfile as _tempfile

import pytest


def _编译并运行(code: str, optimize_level: int = 0) -> tuple:
    """用原生腿 compile_light_typed 编译并运行，返回 (rc, stdout, stderr)。"""
    from llvm.compiler import compile_light_typed
    with _tempfile.TemporaryDirectory(prefix='_taskR12A_') as d:
        src = os.path.join(d, '主.light')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, '产物'),
                                  optimize_level=optimize_level)
        r = _subproc.run([exe], capture_output=True, timeout=60)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        return r.returncode, out, err


def _行(out: str):
    return [h for h in out.replace('\r', '').split('\n') if h != '']


def _对拍(out: str, 期望):
    实际 = _行(out)
    assert 实际 == [str(e) for e in 期望], f"实际={实际} 期望={期望}"


def _b1头():
    """输出 1/0 的布尔打印辅助段落。"""
    return (
        '段落 b1 接收 b:\n'
        '  如果 b:\n'
        '    输出(1)\n'
        '  否则:\n'
        '    输出(0)\n'
    )


# ── R11B-1：非 对布尔真值 ──────────────────────────────────────────────

def test_非_布尔字面量():
    """非 假 → 真；非 真 → 假。修复前 非假 判成假。"""
    code = (
        _b1头() +
        '段落 主:\n'
        '  b1(非 假)\n'
        '  b1(非 真)\n'
        '  设 甲 为 假\n'
        '  b1(非 甲)\n'
        '  设 乙 为 真\n'
        '  b1(非 乙)\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, [1, 0, 1, 0])


def test_非_整数与表达式():
    """非 0 → 真；非 5 → 假；括号表达式取反（回归保护）。"""
    code = (
        _b1头() +
        '段落 主:\n'
        '  b1(非 0)\n'
        '  b1(非 5)\n'
        '  b1(非 (3 == 3))\n'
        '  b1(非 (3 == 4))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, [1, 0, 0, 1])


# ── R11A-01：非 作用于函数调用 ─────────────────────────────────────────

def test_非_函数调用():
    """非 是数字字符("a") → 真；非 是数字字符("!") → 真（!非数字→非假=真）。"""
    code = (
        '从 字符串工具 导入 是数字字符\n'
        + _b1头() +
        '段落 主:\n'
        '  b1(非 是数字字符("a"))\n'
        '  b1(非 是数字字符("!"))\n'
        '  b1(是数字字符("7"))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, [1, 1, 1])


# ── R11B-2：整数(布尔) ────────────────────────────────────────────────

def test_整数_布尔转换():
    """整数(真) → 1；整数(假) → 0；布尔累加计数。修复前 真 转 0。"""
    code = (
        '段落 主:\n'
        '  输出(整数(真))\n'
        '  输出(整数(假))\n'
        '  设 计数 为 0\n'
        '  设 计数 为 计数 + 整数(真)\n'
        '  设 计数 为 计数 + 整数(真)\n'
        '  设 计数 为 计数 + 整数(假)\n'
        '  输出(计数)\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, [1, 0, 2])


# ── R11A-07：且/或 短路 ───────────────────────────────────────────────

def test_且_或_真值表():
    """且/或 全组合真值表（经 b1 打印）。"""
    code = (
        _b1头() +
        '段落 主:\n'
        '  b1(真 且 真)\n'
        '  b1(真 且 假)\n'
        '  b1(假 且 真)\n'
        '  b1(假 且 假)\n'
        '  b1(真 或 真)\n'
        '  b1(真 或 假)\n'
        '  b1(假 或 真)\n'
        '  b1(假 或 假)\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, [1, 0, 0, 0, 1, 1, 1, 0])


def test_且_或_短路不崩():
    """假 且 报错() → 不求值右侧；真 或 报错() → 不求值右侧。"""
    code = (
        _b1头() +
        '段落 报错 接收:\n'
        '  输出("副作用")\n'
        '  返回 真\n'
        '段落 主:\n'
        '  设 甲 为 假\n'
        '  b1(甲 且 报错())\n'
        '  设 乙 为 真\n'
        '  b1(乙 或 报错())\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    # 短路：右侧「副作用」不打印；两条结果 0、1
    _对拍(out, [0, 1])


def test_如果_内联复合条件():
    """如果 a 且 b 且 非 c: 复杂内联条件（解析失败回归）。"""
    code = (
        _b1头() +
        '段落 主:\n'
        '  设 甲 为 真\n'
        '  设 乙 为 5\n'
        '  设 丙 为 假\n'
        '  如果 甲 且 乙 > 3 且 非 丙:\n'
        '    输出("命中")\n'
        '  如果 甲 且 乙 < 3 或 丙:\n'
        '    输出("误判")\n'
        '  否则:\n'
        '    输出("正确分支")\n'
        '  b1(非 丙 且 乙 == 5)\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, ['命中', '正确分支', 1])


def test_短路_嵌套调用返回值():
    """短路右臂为函数调用：真 且 是数字字符("x") → 假（右侧求值）。"""
    code = (
        '从 字符串工具 导入 是数字字符\n'
        + _b1头() +
        '段落 主:\n'
        '  b1(真 且 是数字字符("x"))\n'
        '  b1(假 或 是数字字符("5"))\n'
        '  b1(真 或 是数字字符("x"))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, [0, 1, 1])
