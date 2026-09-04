#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cli/lightc.py 真跑门禁测试

背景：commit 74df4169 后 lightc.py 对任意输入必崩——SemanticAnalyzer()
无参构造与 __init__(self, module) 签名不兼容，TypeError。本测试确保
lightc.py 对合法 .light 文件返回 rc=0 且输出正确。

反跑判据：若 lightc.py LightCompiler.compile() 改回无参 SemanticAnalyzer()
或重新引入语义分析步骤（与 ast_nodes_v3.Module 不兼容），本测试立即 rc!=0。
"""

import os
import subprocess
import sys
import tempfile
import textwrap
import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIGHTC = os.path.join(_PROJECT_ROOT, 'cli', 'lightc.py')


def _run_lightc(source: str, *extra_args):
    """在临时目录写一个 .light 文件，运行 lightc.py，返回 (rc, stdout, stderr)。"""
    with tempfile.TemporaryDirectory(prefix='_taskT2_lightc_') as td:
        src = os.path.join(td, 'test.light')
        with open(src, 'w', encoding='utf-8') as f:
            f.write(source)
        cmd = [sys.executable, _LIGHTC, src] + list(extra_args)
        p = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=30,
            cwd=_PROJECT_ROOT,
        )
        return p.returncode, p.stdout, p.stderr


# ── 合法光明源码（当前规范语法）──
_HELLO = textwrap.dedent("""\
    段 主函数():
        输出("hello")
    主函数()
""")

_CALC = textwrap.dedent("""\
    段 主函数():
        设 a 为 10
        设 b 为 20
        输出(a 加 b)
    主函数()
""")


class TestLightcCli:
    """lightc.py 命令行门禁。"""

    def test_编译hello返回rc0(self):
        """合法 .light 文件编译成功，rc=0，输出含「编译成功」。"""
        rc, out, err = _run_lightc(_HELLO)
        assert rc == 0, f"rc={rc}\nstdout={out}\nstderr={err}"
        assert '编译成功' in out, f"输出缺少「编译成功」: {out}"

    def test_编译calc返回rc0(self):
        """含变量声明与算术的 .light 文件编译成功。"""
        rc, out, err = _run_lightc(_CALC)
        assert rc == 0, f"rc={rc}\nstdout={out}\nstderr={err}"
        assert '编译成功' in out, f"输出缺少「编译成功」: {out}"

    def test_编译并运行输出正确(self):
        """--run 模式编译并执行，stdout 应含程序输出。"""
        rc, out, err = _run_lightc(_HELLO, '--run')
        assert rc == 0, f"rc={rc}\nstdout={out}\nstderr={err}"
        assert 'hello' in out, f"stdout 缺少 hello: {out}"

    def test_编译calc运行输出30(self):
        """--run 模式执行算术程序，stdout 应含 30。"""
        rc, out, err = _run_lightc(_CALC, '--run')
        assert rc == 0, f"rc={rc}\nstdout={out}\nstderr={err}"
        assert '30' in out, f"stdout 缺少 30: {out}"

    def test_无参构造反跑判据(self):
        """反跑：若 compile() 重新引入 SemanticAnalyzer 无参构造或语义分析步骤，
        上述用例会因 TypeError 返回 rc!=0。本测试验证当前代码不含无参构造。"""
        with open(_LIGHTC, 'r', encoding='utf-8') as f:
            src = f.read()
        # 确保不存在无参 SemanticAnalyzer() 调用
        assert 'SemanticAnalyzer()' not in src, \
            "lightc.py 仍含无参 SemanticAnalyzer() 构造，反跑判据失败"
