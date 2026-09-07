# -*- coding: utf-8 -*-
"""R13A 定向反跑测试：runtime 残余缺陷修复（嵌套序列化/链式缓冲/dv_to_int bool）。

覆盖缺陷（R12 批标注归 T7 的 runtime 残余）：
  R12C-L2243 转文本 嵌套容器内层序列化走旧路径 → [[1,2],[3,4]] 打印错
  R12C-L2239 reverse/rstrip 组合链对象缓冲异常（链式调用中间结果损坏）
  R12A-L2001 dv_to_int 对 bool dv 转换（类型未知操作数路径，如 整数(f())）

判据：修复前红、修复后绿；每用例独立编译运行（T5A 范式），
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
    with _tempfile.TemporaryDirectory(prefix='_taskR13A_') as d:
        src = os.path.join(d, '主.light')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, '产物'),
                                  optimize_level=optimize_level)
        r = _subproc.run([exe], capture_output=True, timeout=60)
        out = r.stdout.decode('utf-8', errors='replace').rstrip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        return r.returncode, out, err


def _行(out: str):
    return [h for h in out.replace('\r', '').split('\n') if h != '']


def _对拍(out: str, 期望):
    实际 = _行(out)
    assert 实际 == [str(e) for e in 期望], f"实际={实际} 期望={期望}"


# ── R12C-L2243：嵌套容器序列化 ────────────────────────────────────────

def test_转文本_嵌套列表():
    """转文本(列表(列表(1,2), 列表(3,4))) → [[1, 2], [3, 4]]。"""
    code = (
        '段落 主:\n'
        '  输出(转文本(列表(列表(1, 2), 列表(3, 4))))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, ['[[1, 2], [3, 4]]'])


def test_转文本_嵌套混合元素():
    """顶层与内层混合：[1, [2, 3]] → "[1, [2, 3]]"。"""
    code = (
        '段落 主:\n'
        '  输出(转文本([1, 列表(2, 3)]))\n'
        '  输出(转文本(列表(列表(列表(1)))))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, ['[1, [2, 3]]', '[[[1]]]'])


def test_转文本_字典序列化():
    """转文本(字典) → Python str(dict) 形态 {'a': '1'}。"""
    code = (
        '段落 主:\n'
        '  输出(转文本({"a": "1", "b": "2"}))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, ["{'a': '1', 'b': '2'}"])


# ── R12A-L2001：dv_to_int 对 bool 的运行时转换 ────────────────────────

def test_整数_布尔运行时路径():
    """整数(布尔函数返回值)——类型未知操作数走 dv_to_int：真→1、假→0。"""
    code = (
        '从 字符串工具 导入 是数字字符\n'
        '段落 主:\n'
        '  输出(整数(是数字字符("7")))\n'
        '  输出(整数(是数字字符("x")))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, [1, 0])


# ── R12C-L2239：链式字符串方法缓冲 ────────────────────────────────────

def test_链式字符串方法():
    """反转+右去除 链式调用：中间结果不被覆盖。"""
    code = (
        '段落 主:\n'
        '  输出("  abc  ".反转().右去除())\n'
        '  输出("y  ".右去除().反转())\n'
        '  输出("  a  ".去除空白().反转().右去除().反转())\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    # "  abc  " 反转 → "  cba  "，右去除 → "  cba"
    # "y  " 右去除 → "y"，反转 → "y"
    # "  a  " 去空白 → "a"，反转 → "a"，右去除 → "a"，反转 → "a"
    _对拍(out, ['  cba', 'y', 'a'])
