# -*- coding: utf-8 -*-
"""光明程序标准输入/输出冒烟（R152-C3 改造：真 test_* 函数）。

沿革
----
本文件原先是**手动冒烟脚本**：副作用写在 `_main()` 里、由 `if __name__ == '__main__'`
守卫保护。作为 pytest 目标它只会被 import（`rc=5 无测试项`），真实断言从未进过门禁。

R152-C3 二选一裁定：**选 (a) 改造成真 `test_*` 函数**，理由是这段断言（「生成的
Python 会调用入口 `主()`」+「`读取行()` 真能读到喂进去的 stdin」）是**入口自动调用**
与**标准 IO** 两条核心链路的唯一现存覆盖，判红和 `collect_ignore` 排除都会让它永久
退出门禁；改成真测试后它随每次全量门一起跑。

纪律：不再 `os.chdir`（会污染其它测试的当前目录），改为显式插 `sys.path`。
"""
import os
import subprocess
import sys

import pytest

_仓库根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_仓库根, 'src'))

_源码 = """段落 主():
    设 消息 为 "光明IO测试-开始"。
    打印输出(消息)。
    打印输出("等待输入...")。
    设 用户行 为 读取行()。
    打印输出(用户行)。
    """


def _生成的Python代码():
    from code_generator import PythonCodeGenerator
    from light_parser_v3 import LightParser

    return PythonCodeGenerator().generate(LightParser().parse(_源码))


def test_生成代码自动调用入口主():
    """入口自动调用：生成的 Python 必须自己发起 `主()`，否则 `light run` 静默无输出。"""
    assert "主()" in _生成的Python代码()


def test_标准输入输出往返():
    """`打印输出` 走 stdout、`读取行()` 读到喂进去的 stdin——端到端往返一次。"""
    代码 = _生成的Python代码() + "\n\n主()\n"
    r = subprocess.run(
        [sys.executable, '-c', 代码],
        input='你好光明\n',
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, "rc=%d stderr=%s" % (r.returncode, r.stderr[:800])
    assert '光明IO测试-开始' in r.stdout
    assert '等待输入...' in r.stdout
    assert '你好光明' in r.stdout
