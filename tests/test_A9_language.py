"""
A9 语言层测试
S1.1: 类体接受 异步 段落（async def 方法）
S1.2: 真 最终(finally) 语义 + 捕获折叠 bug 修复
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


def _run(src: str) -> str:
    """编译并执行光明源码，返回 stdout（strip 后）。失败返回 ERR:类型:信息。"""
    parser = LightParser()
    module = parser.parse(src)
    gen = PythonCodeGenerator()
    code = gen.generate(module)
    local_ns = {}
    global_ns = {}
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            exec(code, global_ns, local_ns)
    except Exception as e:
        return f"ERR:{type(e).__name__}:{e}"
    return stdout.getvalue().strip()


def _gen(src: str) -> str:
    """仅生成 Python 代码，不执行。"""
    parser = LightParser()
    module = parser.parse(src)
    gen = PythonCodeGenerator()
    return gen.generate(module)


# ──────────────────────────────────────────────────────────────────────
# S1.1: 类体异步段落
# ──────────────────────────────────────────────────────────────────────

class TestS11AsyncMethodInClass:
    """类体内 `异步 段落 名字():` 应转译为 `async def 名字(self):`。"""

    def test_async_method_generates_async_def(self):
        """生成的 Python 代码中方法以 async def 开头。"""
        src = '''
类 读取器:
    异步 段落 读取(路径):
        返回 "data"
'''
        code = _gen(src)
        assert "async def 读取" in code, f"期望 async def，实际:\n{code[-200:]}"

    def test_sync_method_still_def(self):
        """同步方法不受影响，仍生成 def。"""
        src = '''
类 读取器:
    段落 同步读取(路径):
        返回 "data"
'''
        code = _gen(src)
        assert "def 同步读取" in code
        # 确保不是 async def
        assert "async def 同步读取" not in code

    def test_async_method_executable(self):
        """async 方法可以被 asyncio.run 调用。"""
        src = '''
类 读取器:
    异步 段落 读取():
        返回 "hello-async"
'''
        code = _gen(src)
        # 通过 exec 执行，然后在命名空间中取类和方法
        global_ns = {}
        exec(code, global_ns)
        ReaderClass = global_ns['读取器']
        instance = ReaderClass()
        result = asyncio.run(instance.读取())
        assert result == "hello-async"

    def test_async_method_with_await(self):
        """async 方法内部可以使用 await。"""
        src = '''
异步 段落 获取值():
    返回 42

类 工人:
    异步 段落 执行():
        设 结果 为 等待 获取值()
        返回 结果
'''
        code = _gen(src)
        global_ns = {}
        exec(code, global_ns)
        WorkerClass = global_ns['工人']
        instance = WorkerClass()
        result = asyncio.run(instance.执行())
        assert result == 42

    def test_async_method_alongside_sync(self):
        """类中同时有 async 和 sync 方法。"""
        src = '''
类 混合:
    异步 段落 异步方法():
        返回 "async"
    段落 同步方法():
        返回 "sync"
'''
        code = _gen(src)
        assert "async def 异步方法" in code
        assert "def 同步方法" in code
        assert "async def 同步方法" not in code

    def test_异_alias_for_async(self):
        """单字 `异` 也应作为异步关键字的别名。"""
        src = '''
类 读取器:
    异 段落 读取():
        返回 "aliased"
'''
        code = _gen(src)
        assert "async def 读取" in code


# ──────────────────────────────────────────────────────────────────────
# S1.2: 捕获折叠 bug 修复
# ──────────────────────────────────────────────────────────────────────

class TestS12CatchFoldingFix:
    """catch 块后同级语句不应被吞入 except 块。"""

    def test_catch_no_folding_normal_path(self):
        """try 无异常时，catch 后的语句正常执行。"""
        src = '''
尝试:
    输出("try")
捕获 e:
    输出("catch")
输出("after")
'''
        result = _run(src)
        assert "try" in result
        assert "catch" not in result
        assert "after" in result
        # 顺序：try → after
        lines = result.split('\n')
        assert lines[0] == "try"
        assert lines[1] == "after"

    def test_catch_no_folding_exception_path(self):
        """try 有异常时，catch 执行，after 也执行。"""
        src = '''
尝试:
    输出("try")
    抛出 值错误("boom")
捕获 e:
    输出("catch")
输出("after")
'''
        result = _run(src)
        assert "try" in result
        assert "catch" in result
        assert "after" in result
        lines = result.split('\n')
        assert lines[0] == "try"
        assert lines[1] == "catch"
        assert lines[2] == "after"

    def test_catch_not_swallowing_sibling_in_codegen(self):
        """直接检查生成的 Python 代码：print("after") 不在 except 块内。"""
        src = '''
尝试:
    输出("try")
捕获 e:
    输出("catch")
输出("after")
'''
        code = _gen(src)
        lines = code.split('\n')
        # 找到 try/except/after 三行的缩进。用 dict 收集而不是三个 None 变量：
        # `assert x is not None` 是零信号断言（假测试门禁 [非空断言式]），
        # 「三个标记都找到了」这件事要用一条有判别力的等式来断。
        缩进 = {}
        for line in lines:
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if stripped.startswith('try:'):
                缩进['try'] = indent
            elif stripped.startswith('except'):
                缩进['except'] = indent
            elif 'after' in stripped and 'print' in stripped:
                缩进['after'] = indent
        assert set(缩进) == {'try', 'except', 'after'}, \
            "生成代码里缺关键标记，实际找到：%s\n%s" % (sorted(缩进), code)
        try_indent = 缩进['try']
        except_indent = 缩进['except']
        after_indent = 缩进['after']
        # after 应与 try 同级（不在 except 块内）
        assert after_indent == try_indent, \
            f"after 的缩进({after_indent})应等于 try({try_indent})，" \
            f"但 except 是 {except_indent}"


# ──────────────────────────────────────────────────────────────────────
# S1.2: try/catch/finally 完整三段语义
# ──────────────────────────────────────────────────────────────────────

class TestS12TryCatchFinally:
    """try/catch/finally 三段完整 + 正确缩进。"""

    def test_finally_normal_path(self):
        """无异常时：try → finally → after。"""
        src = '''
尝试:
    输出("try")
捕获 e:
    输出("catch")
最终:
    输出("finally")
输出("after")
'''
        result = _run(src)
        lines = result.split('\n')
        assert lines == ["try", "finally", "after"]

    def test_finally_exception_path(self):
        """有异常时：try → catch → finally → after。"""
        src = '''
尝试:
    输出("try")
    抛出 值错误("boom")
捕获 e:
    输出("catch")
最终:
    输出("finally")
输出("after")
'''
        result = _run(src)
        lines = result.split('\n')
        assert lines == ["try", "catch", "finally", "after"]

    def test_finally_with_return(self):
        """return 时 finally 仍执行。"""
        src = '''
段落 测试():
    尝试:
        输出("try")
        返回 "result"
    捕获 e:
        输出("catch")
    最终:
        输出("finally")
    输出("unreachable")

结果 为 测试()
输出(结果)
'''
        result = _run(src)
        lines = result.split('\n')
        assert "try" in lines
        assert "finally" in lines
        assert "result" in lines
        # "unreachable" 不应出现（return 跳过了它）
        assert "unreachable" not in lines
        # finally 在 return 之前执行
        assert lines.index("finally") < lines.index("result")

    def test_finally_codegen_structure(self):
        """生成的 Python 代码结构正确：try/except/finally 三块缩进一致。"""
        src = '''
尝试:
    输出("try")
捕获 e:
    输出("catch")
最终:
    输出("finally")
输出("after")
'''
        code = _gen(src)
        lines = code.split('\n')
        try_indent = except_indent = finally_indent = after_indent = None
        for line in lines:
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if stripped == 'try:':
                try_indent = indent
            elif stripped.startswith('except'):
                except_indent = indent
            elif stripped == 'finally:':
                finally_indent = indent
            elif 'after' in stripped and 'print' in stripped:
                after_indent = indent
        assert try_indent == except_indent == finally_indent == after_indent, \
            f"缩进不一致: try={try_indent} except={except_indent} " \
            f"finally={finally_indent} after={after_indent}"

    def test_multiple_catches(self):
        """多个 catch 块都能正确解析和执行。"""
        src = '''
尝试:
    输出("try")
    抛出 值错误("err")
捕获 值错误 e:
    输出("value-error")
捕获 e:
    输出("generic-error")
最终:
    输出("finally")
输出("after")
'''
        result = _run(src)
        lines = result.split('\n')
        assert lines == ["try", "value-error", "finally", "after"]

    def test_try_finally_no_catch(self):
        """try/finally 无 catch 块。"""
        src = '''
尝试:
    输出("try")
最终:
    输出("finally")
输出("after")
'''
        result = _run(src)
        lines = result.split('\n')
        assert lines == ["try", "finally", "after"]

    def test_nested_try_catch_finally(self):
        """嵌套 try/catch/finally。"""
        src = '''
尝试:
    输出("outer-try")
    尝试:
        输出("inner-try")
        抛出 值错误("inner")
    捕获 e:
        输出("inner-catch")
    最终:
        输出("inner-finally")
捕获 e:
    输出("outer-catch")
最终:
    输出("outer-finally")
输出("after")
'''
        result = _run(src)
        lines = result.split('\n')
        assert lines == [
            "outer-try", "inner-try", "inner-catch", "inner-finally",
            "outer-finally", "after"
        ]
