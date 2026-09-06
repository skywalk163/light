# -*- coding: utf-8 -*-
"""R12C 定向反跑测试：方法分派/语法解析/控制流族 codegen 根因修复。

覆盖缺陷（R11 批 workaround 绕过、本批根因修复）：
  R11A-05 跨模块「导入即再导出」→ 调用点「未定义的段落」
  R11A-06 默认参数禁负数字面量（`接收 甲 = -1` 报意外的标记）
  R11A-08 字符串内置方法返空（.去除空白/.lstrip/.rstrip/.每个单词首字母大写/.分割）
  R11A-09 转文本(列表) 打印为 []（序列化读错字段）
  R11B-3  字典 .获取 默认参数失效
  R11C-1  O0 临时槽位池 2048 上限（大字面量溢出）
  R11C-3  try/catch 块内 跳过(continue) → IR 验证失败

判据：修复前红、修复后绿；每用例独立编译运行（T5A 范式），
optimize_level=0 强 O0。只跑本文件，禁止全量。
"""
import os
import sys
import subprocess as _subproc
import tempfile as _tempfile

import pytest


def _编译并运行(code: str, optimize_level: int = 0, 额外模块: dict = None) -> tuple:
    """用原生腿 compile_light_typed 编译并运行，返回 (rc, stdout, stderr)。

    额外模块：模块名 -> 源码，写入入口同目录供跨模块导入解析。
    """
    from llvm.compiler import compile_light_typed
    with _tempfile.TemporaryDirectory(prefix='_taskR12C_') as d:
        src = os.path.join(d, '主.light')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        for mod_name, mod_src in (额外模块 or {}).items():
            with open(os.path.join(d, f'{mod_name}.light'), 'w',
                      encoding='utf-8', newline='\n') as f:
                f.write(mod_src)
        exe = compile_light_typed(src, os.path.join(d, '产物'),
                                  optimize_level=optimize_level)
        r = _subproc.run([exe], capture_output=True, timeout=120)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        return r.returncode, out, err


def _行(out: str):
    return [h for h in out.replace('\r', '').split('\n') if h != '']


def _对拍(out: str, 期望):
    实际 = _行(out)
    assert 实际 == [str(e) for e in 期望], f"实际={实际} 期望={期望}"


# ── R11A-05：跨模块导入即再导出 ────────────────────────────────────────

def test_再导出_跨模块链式调用():
    """A 定义 f；B `从 A 导入 f` + `导出 f`；主模块 `从 B 导入 f` 调用。"""
    code = (
        '从 模块乙 导入 加倍\n'
        '段落 主:\n'
        '  输出(加倍(21))\n'
    )
    模块甲 = (
        '段落 加倍 接收 n:\n'
        '  返回 n 乘以 2\n'
        '\n'
        '导出 加倍。\n'
    )
    模块乙 = (
        '从 模块甲 导入 加倍\n'
        '\n'
        '导出 加倍。\n'
    )
    rc, out, err = _编译并运行(code, 额外模块={'模块甲': 模块甲, '模块乙': 模块乙})
    assert rc == 0, err
    _对拍(out, [42])


# ── R11A-06：默认参数负数字面量 ────────────────────────────────────────

def test_默认参数_负数字面量():
    """`接收 甲 = -1` 不报错；无参调用得 -1，传参得传值。"""
    code = (
        '段落 步进 接收 甲 = -1:\n'
        '  返回 甲\n'
        '\n'
        '段落 主:\n'
        '  输出(步进())\n'
        '  输出(步进(7))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, [-1, 7])


# ── R11A-08：字符串内置方法 ────────────────────────────────────────────

def test_字符串方法_去除空白族():
    """.去除空白()/.lstrip()/.rstrip() 返回正确字符串。"""
    code = (
        '段落 主:\n'
        '  输出("  a b  ".去除空白())\n'
        '  输出("  x".lstrip())\n'
        '  输出("y  ".rstrip())\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, ['a b', 'x', 'y'])


def test_字符串方法_首字母大写_分割():
    """.每个单词首字母大写() 与 .分割() 无参空白切分（单空格输入）。"""
    code = (
        '段落 主:\n'
        '  输出("hello world".每个单词首字母大写())\n'
        '  设 词们 为 "a b c".分割()\n'
        '  输出(长(词们))\n'
        '  输出(词们[2])\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, ['Hello World', 3, 'c'])


# ── R11A-09：转文本(列表) 序列化 ───────────────────────────────────────

def test_转文本_列表序列化():
    """转文本(列表(1,2,3)) → "[1, 2, 3]"（修复前恒 "[]"）。"""
    code = (
        '段落 主:\n'
        '  输出(转文本(列表(1, 2, 3)))\n'
        '  输出(转文本([4, 5]))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, ['[1, 2, 3]', '[4, 5]'])


# ── R11B-3：字典 .获取 默认参数 ────────────────────────────────────────

def test_字典获取方法_默认参数():
    """表.获取("缺", "默认") → 默认；表.获取("a", "默认") → 1。"""
    code = (
        '段落 主:\n'
        '  设 表 为 {"a": "1"}\n'
        '  输出(表.获取("a", "默认"))\n'
        '  输出(表.获取("缺", "默认"))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, ['1', '默认'])


# ── R11C-1：大字面量槽位池 ─────────────────────────────────────────────

def test_大列表字面量_不溢出():
    """3000 元素列表字面量（>2048 槽位池上限）编译运行不溢出。"""
    元素 = ', '.join(str(i) for i in range(1, 3001))
    code = (
        f'段落 主:\n'
        f'  设 大表 为 [{元素}]\n'
        f'  输出(长(大表))\n'
        f'  输出(大表[0])\n'
        f'  输出(大表[2999])\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    _对拍(out, [3000, 1, 3000])


# ── R11C-3：try/catch 内 跳过 ──────────────────────────────────────────

def test_trycatch内_跳过():
    """try/catch 块内 跳过(continue)：IR 验证通过、循环正常。"""
    code = (
        '段落 主:\n'
        '  设 i 为 0\n'
        '  设 命中 为 0\n'
        '  当 i < 4:\n'
        '    尝试:\n'
        '      设 i 为 i + 1\n'
        '      如果 i == 2:\n'
        '        跳过\n'
        '      设 命中 为 命中 + 1\n'
        '    捕获:\n'
        '      设 命中 为 命中 + 100\n'
        '  输出(i)\n'
        '  输出(命中)\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    # i=1..4；i==2 时跳过不计数 → 命中 3
    _对拍(out, [4, 3])
