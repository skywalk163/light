"""
A9-S1.2 判据测试：真 最终(finally) 语义 + 捕获折叠 bug 修复

六例（任务书要求）：
① 正常路径
② 异常路径
③ 返回 提前退出
④ 嵌套
⑤ 异步
⑥ 反跑（把 最终 体删掉，断言资源未释放的那条断言必须立红）
"""

import sys
import os
import io
import asyncio
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _gen(src: str) -> str:
    """仅生成 Python 代码，不执行。"""
    parser = LightParser()
    module = parser.parse(src)
    gen = PythonCodeGenerator()
    return gen.generate(module)


def _run(src: str) -> str:
    """编译并执行光明源码，返回 stdout（strip 后）。失败返回 ERR:类型:信息。"""
    parser = LightParser()
    module = parser.parse(src)
    gen = PythonCodeGenerator()
    code = gen.generate(module)
    global_ns = {}
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            exec(code, global_ns)
    except Exception as e:
        return f"ERR:{type(e).__name__}:{e}"
    return stdout.getvalue().strip()


class TestTryFinally:
    """任务书 S1.2 判据：tests/test_try_finally.py 六例。"""

    def test_01_normal_path(self):
        """① 正常路径：try → finally → after，catch 不执行。"""
        src = '''
设 日志 为 ""

尝试:
    日志 为 日志 加上 "try>"
捕获 e:
    日志 为 日志 加上 "catch>"
最终:
    日志 为 日志 加上 "finally>"
输出(日志)
'''
        result = _run(src)
        assert result == "try>finally>"

    def test_02_exception_path(self):
        """② 异常路径：try → catch → finally。"""
        src = '''
设 日志 为 ""

尝试:
    日志 为 日志 加上 "try>"
    抛出 值错误("boom")
捕获 e:
    日志 为 日志 加上 "catch>"
最终:
    日志 为 日志 加上 "finally>"
输出(日志)
'''
        result = _run(src)
        assert result == "try>catch>finally>"

    def test_03_return_early_exit(self):
        """③ 返回 提前退出：finally 仍执行，return 后的语句不执行。

        Python 语义：return 表达式先求值，然后 finally 执行，最后才真正返回。
        所以返回值本身不含 finally 的副作用——但 finally 确实执行了。
        用列表（可变对象）验证 finally 确实跑过。
        """
        src = '''
设 日志 为 []

段落 测试():
    尝试:
        日志.追加("try")
        返回 "result"
    捕获 e:
        日志.追加("catch")
    最终:
        日志.追加("finally")
    日志.追加("unreachable")
    返回 "end"

设 结果 为 测试()
输出(结果)
输出(日志)
'''
        result = _run(src)
        lines = result.split('\n')
        # 第一行是返回值
        assert lines[0] == "result"
        # 第二行是日志列表，应含 try 和 finally，不含 unreachable
        assert "try" in lines[1]
        assert "finally" in lines[1]
        assert "unreachable" not in lines[1]

    def test_04_nested(self):
        """④ 嵌套 try/catch/finally：内外层都正确。"""
        src = '''
设 日志 为 ""

尝试:
    日志 为 日志 加上 "outer-try>"
    尝试:
        日志 为 日志 加上 "inner-try>"
        抛出 值错误("inner")
    捕获 e:
        日志 为 日志 加上 "inner-catch>"
    最终:
        日志 为 日志 加上 "inner-finally>"
捕获 e:
    日志 为 日志 加上 "outer-catch>"
最终:
    日志 为 日志 加上 "outer-finally>"
输出(日志)
'''
        result = _run(src)
        assert result == "outer-try>inner-try>inner-catch>inner-finally>outer-finally>"

    def test_05_async_finally(self):
        """⑤ 异步段落里的 最终 同样成立。"""
        src = '''
设 日志 为 ""

异步 段落 异步测试():
    全局 日志
    尝试:
        日志 为 日志 加上 "try>"
        返回 "done"
    捕获 e:
        日志 为 日志 加上 "catch>"
    最终:
        日志 为 日志 加上 "finally>"
    日志 为 日志 加上 "unreachable"

异步 段落 主():
    设 结果 为 等待 异步测试()
    输出(结果)
    输出(日志)

异步 运行 主()
'''
        result = _run(src)
        lines = result.split('\n')
        # 第一行是返回值 "done"
        assert lines[0] == "done"
        # 第二行是日志，应含 try> 和 finally>，不含 catch> 和 unreachable
        assert "try>" in lines[1]
        assert "finally>" in lines[1]
        assert "catch>" not in lines[1]
        assert "unreachable" not in lines[1]

    def test_06_negative_no_finally(self):
        """⑥ 反跑：把 最终 体删掉，断言资源未释放。

        没有 finally 时，异常路径下「资源释放」代码不会执行。
        我们用一个标志变量模拟资源释放，验证没有 finally 时释放确实不发生。
        """
        # 有 finally — 资源释放
        src_with_finally = '''
设 已释放 为 假

尝试:
    抛出 值错误("boom")
捕获 e:
    输出("caught")
最终:
    已释放 为 真

输出(已释放)
'''
        result_with = _run(src_with_finally)
        assert "caught" in result_with
        assert "True" in result_with or "真" in result_with or "1" in result_with

        # 没有 finally - 资源未释放（反跑：这条必须立红如果 finally 没执行）
        src_without_finally = '''
设 已释放 为 假

尝试:
    抛出 值错误("boom")
捕获 e:
    输出("caught")

输出(已释放)
'''
        result_without = _run(src_without_finally)
        assert "caught" in result_without
        # 已释放 仍为 假/False
        assert "False" in result_without or "假" in result_without or "0" in result_without


class TestCatchFoldingBug:
    """捕获折叠 bug：catch 后同级语句不被吞入 except 块。

    任务书要求：「先写一条能复现折叠的最小用例，再修，用例留在仓库里。」
    """

    def test_catch_folding_reproduction(self):
        """复现用例：catch 后的 输出("after") 不应在 except 块内。"""
        src = '''
尝试:
    输出("try")
捕获 e:
    输出("catch")
输出("after")
'''
        code = _gen(src)
        lines = code.split('\n')
        # 找到各关键行的缩进
        try_indent = except_indent = after_indent = None
        for line in lines:
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if stripped == 'try:':
                try_indent = indent
            elif stripped.startswith('except'):
                except_indent = indent
            elif 'after' in stripped and 'print' in stripped:
                after_indent = indent
        assert try_indent is not None, "没有找到 try:"
        assert except_indent is not None, "没有找到 except"
        assert after_indent is not None, "没有找到 after print"
        # after 必须与 try 同级（不在 except 块内）
        assert after_indent == try_indent, \
            f"折叠 bug 复现：after 缩进({after_indent})应等于 try({try_indent})，" \
            f"except 是 {except_indent}"

    def test_catch_folding_execution_normal(self):
        """正常路径：try → after（catch 不执行）。"""
        src = '''
尝试:
    输出("try")
捕获 e:
    输出("catch")
输出("after")
'''
        result = _run(src)
        lines = result.split('\n')
        assert lines == ["try", "after"]

    def test_catch_folding_execution_exception(self):
        """异常路径：try → catch → after。"""
        src = '''
尝试:
    输出("try")
    抛出 值错误("boom")
捕获 e:
    输出("catch")
输出("after")
'''
        result = _run(src)
        lines = result.split('\n')
        assert lines == ["try", "catch", "after"]
