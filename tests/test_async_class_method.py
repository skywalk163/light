"""
A9-S1.1 判据测试：类体异步段落

四例（任务书要求）：
① 类内异步方法 + 等待 真跑
② 类内异步方法调另一个类内异步方法
③ 类内异步方法读写 己. 属性
④ 反跑：把 异步 去掉后 等待 应报「不在异步上下文」
"""

import sys
import os
import io
import asyncio
import pytest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator, CodeGenError


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


class TestAsyncClassMethod:
    """任务书 S1.1 判据：tests/test_async_class_method.py 至少四例。"""

    def test_01_async_method_with_await(self):
        """① 类内异步方法 + 等待 真跑。"""
        src = '''
异步 段落 获取值():
    返回 42

类 工人:
    异步 段落 执行():
        设 结果 为 等待 获取值()
        输出(结果)
'''
        # 用 asyncio.run 驱动
        code = _gen(src)
        global_ns = {}
        exec(code, global_ns)
        WorkerCls = global_ns['工人']
        instance = WorkerCls()
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            asyncio.run(instance.执行())
        assert stdout.getvalue().strip() == "42"

    def test_02_async_calls_async_in_class(self):
        """② 类内异步方法调另一个类内异步方法。"""
        src = '''
类 计算器:
    异步 段落 基础值():
        返回 10

    异步 段落 总和():
        设 x 为 等待 基础值()
        返回 x 加上 5
'''
        code = _gen(src)
        # 验证生成的是 async def 且内部有 await self.基础值()
        assert "async def 基础值" in code
        assert "async def 总和" in code
        assert "await self.基础值()" in code

        global_ns = {}
        exec(code, global_ns)
        CalcCls = global_ns['计算器']
        instance = CalcCls()
        result = asyncio.run(instance.总和())
        assert result == 15

    def test_03_async_method读写己属性(self):
        """③ 类内异步方法读写 己. 属性。"""
        src = '''
类 计数器:
    设 值 为 0

    异步 段落 增加():
        己.值 为 己.值 加上 1
        返回 己.值

    异步 段落 取值():
        返回 己.值
'''
        code = _gen(src)
        # 验证 self.属性 读写（L-096 helper 形态，R59 更新：写入发射
        # _light_attr_set(self, '值', (self.值 + 1))，类实例走 setattr，与旧直发等价）
        assert "_light_attr_set(self, '值', (self.值 + 1))" in code
        assert "return self.值" in code

        global_ns = {}
        exec(code, global_ns)
        CounterCls = global_ns['计数器']
        c = CounterCls()
        r1 = asyncio.run(c.增加())
        assert r1 == 1
        r2 = asyncio.run(c.增加())
        assert r2 == 2
        r3 = asyncio.run(c.取值())
        assert r3 == 2

    def test_04_negative_await_in_sync_method(self):
        """④ 反跑：同步段落里写 等待，编译器应在代码生成阶段提前报中文错。

        R70-B 收紧 _require_async_context 后，「等待」只能出现在异步段落里；
        同步段落中的 等待 会在 _gen() 阶段直接抛 CodeGenError（比旧行为
        「生成含裸 await 的普通 def → Python compile 才 SyntaxError」更早、
        错误信息更友好）。本用例断言这一改进后的行为。
        """
        src = '''
段落 非异步():
    设 x 为 等待 某函数()
    返回 x
'''
        with pytest.raises(CodeGenError) as exc_info:
            _gen(src)
        msg = str(exc_info.value)
        assert '等待' in msg, f"错误信息应提及「等待」，实际: {msg}"
        assert '异步' in msg, f"错误信息应提及「异步」，实际: {msg}"
        assert '同步' in msg, f"错误信息应说明当前在同步段落，实际: {msg}"
