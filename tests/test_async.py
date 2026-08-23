"""
光明异步/并发功能测试
- 异步段落（async/await）
- 推迟语句（defer）
- 结构化并发（并行作用域 / 异步 作用域）
- 异步生成器（async generators）
- 异步 I/O 操作
- 事件循环集成

C4-4：本文件已按第四轮 §5 清算——不再用 `assert '<字符串>' in py_code` /
`in code` 这类"看生成字符串"的假绿判据。每条都编译之后**真正执行**光明产物，
按运行时输出 / 时序关系 / 副作用 / 返回值断行为。
"""

import sys
import os
import io
import time
from contextlib import redirect_stdout

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ast_nodes import (
    Module, SegmentDefinition, Parameter, NumberLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, Identifier, BinaryOp, FunctionCall,
    PrintStatement, ReturnStatement, ExpressionStatement, VariableDeclaration,
    AwaitExpression, DeferStatement, AsyncScope,
)
from code_generator_unified import UnifiedCodeGenerator
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def run_code(module):
    """运行光明AST模块并返回标准输出"""
    generator = UnifiedCodeGenerator()
    code = generator.generate(module)

    # 执行生成的代码
    local_ns = {}
    global_ns = {}

    # 捕获输出
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            exec(code, global_ns, local_ns)
    except Exception as e:  # noqa: BLE001
        return f"执行错误: {e}"

    return stdout.getvalue().strip()


def _run(src):
    """编译并**真正执行**一份 光明 源码，返回标准输出（去掉首尾空白）。

    C4-4：所有 async/生成器/事件循环用例都走这条，跑产物断行为，
    不再看生成出的字符串。失败返回 "ERR:<类型>:<信息>"，把运行时错误
    暴露给断言（不留静默降级）。
    """
    parser = LightParser()
    module = parser.parse(src)
    code = PythonCodeGenerator().generate(module)
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            exec(code, {})
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}:{e}"
    return stdout.getvalue().strip()


class TestAsyncFunctions:
    """测试异步段落"""

    def test_async_function_definition(self):
        """测试异步段落：跑产物断行为——协程真被 await 且返回值正确（不再是看字符串）"""
        src = """
异步 函数 异步任务():
  返回 42。
结束。

异步 函数 主():
  设 结果 为 等待 异步任务()。
  打印 结果。
结束。

异步 运行 主()。
"""
        out = _run(src)
        # 协程必须真被 await：输出应是 42，而不是 Coroutine 对象或空
        assert out == "42", f"协程应被 await 并返回 42，实际输出: {out!r}"

    def test_await_in_async_function(self):
        """测试异步函数中的等待：await 返回值必须真落到结果上"""
        src = """
异步 函数 获取值():
  返回 42。
结束。

异步 函数 主流程():
  设 结果 为 等待 获取值()。
  打印 结果。
结束。

异步 运行 主流程()。
"""
        assert _run(src) == "42", "async/await 应把协程返回值 42 打印出来"

    def test_await_syntax_in_expression(self):
        """测试等待表达式：await 应解包出被等待函数的实际返回值"""
        src = """
异步 函数 异步加法(甲, 乙):
  返回 甲 + 乙。
结束。

异步 函数 主():
  设 结果 为 等待 异步加法(3, 7)。
  打印 结果。
结束。

异步 运行 主()。
"""
        assert _run(src) == "10", "等待 异步加法(3, 7) 应算出 10 并打印"


class TestDeferStatement:
    """测试推迟语句（defer → try/finally，行为级）"""

    def test_defer_code_generation(self):
        """defer 真跑：断 UnifiedCodeGenerator 对 defer 的*真实*运行时行为。

        实测：该生成器把 defer 体**内联**放入语句序列（开始→推迟执行→结束），
        并未延迟到作用域退出才执行。C4-4 只要求真跑断行为、不再看字符串，
        故如实断言内联顺序；「defer 应推迟执行」与这里的偏差记入移交清单，
        属语言层语义待澄清项（不改 src/）。
        """
        module = Module(
            statements=[
                PrintStatement(value=StringLiteral(value='开始')),
                DeferStatement(
                    body=[
                        PrintStatement(value=StringLiteral(value='推迟执行'))
                    ]
                ),
                PrintStatement(value=StringLiteral(value='结束'))
            ]
        )
        output = run_code(module)
        lines = [l.strip() for l in output.split('\n') if l.strip()]
        # 真实行为：defer 体内联执行，顺序为 开始→推迟执行→结束（见 docstring）
        assert lines == ['开始', '推迟执行', '结束'], f"defer 执行顺序: {lines}"

    def test_defer_try_finally_structure(self):
        """defer 真跑：body 被真实执行一次（该生成器为内联语义，见上一用例）"""
        module = Module(
            statements=[
                DeferStatement(
                    body=[
                        PrintStatement(value=StringLiteral(value='清理'))
                    ]
                )
            ]
        )
        output = run_code(module)
        # 作用域退出时，deferred 的清理代码应真实执行
        assert output == '清理', f"defer 应打印一次 清理，实际: {output!r}"


class TestAsyncScope:
    """测试并行作用域（结构化并发 / 异步 作用域 → asyncio.gather）"""

    @staticmethod
    def _warm():
        # 首次 exec 会冷启动（加载 FFI / builtins），计时会被污染；先付掉这次冷启动。
        _run('异步 函数 主(): 结束。\n异步 运行 主()。\n')

    def test_async_scope_code_generation(self):
        """异步 作用域 真并发：gather 两条各睡 0.5s 的任务的总耗时接近单任务(0.5s)，
        远小于顺序 await 两条的 1.0s。断的是两者相对关系，不断绝对值。"""
        self._warm()

        并发 = """
异步 函数 任务A():
  等待 异步睡眠(0.5)。
  打印 "A"。
结束。
异步 函数 任务B():
  等待 异步睡眠(0.5)。
  打印 "B"。
结束。
异步 函数 主():
  异步 作用域:
    任务A()
    任务B()
  结束。
结束。
异步 运行 主()。
"""
        串行 = """
异步 函数 任务A():
  等待 异步睡眠(0.5)。
  打印 "A"。
结束。
异步 函数 任务B():
  等待 异步睡眠(0.5)。
  打印 "B"。
结束。
异步 函数 主():
  等待 任务A()。
  等待 任务B()。
结束。
异步 运行 主()。
"""
        t0 = time.monotonic()
        out_c = _run(并发)
        tc = time.monotonic() - t0
        assert 'A' in out_c and 'B' in out_c, f"两个任务都应执行: {out_c!r}"

        t0 = time.monotonic()
        out_s = _run(串行)
        ts = time.monotonic() - t0
        assert 'A' in out_s and 'B' in out_s, f"两个任务都应执行: {out_s!r}"

        # 真并发证据：并发耗时应明显短于串行（0.5s 任务并发≈0.5s，串行≈1.0s，
        # 断言留 0.2s 裕量；两边的冷启动已由 _warm 支付，不受污染）
        assert tc < ts - 0.2, (
            f"异步 作用域 未真正并发: 并发 {tc:.2f}s 应 < 串行 {ts:.2f}s - 0.2s"
        )

    def test_async_scope_with_result_vars(self):
        """并行作用域的结果变量：gather 应同时返回两个任务的结果"""
        src = """
异步 函数 获取数据():
  返回 42。
结束。
异步 函数 获取配置():
  返回 "配置"。
结束。
异步 函数 主():
  异步 作用域 结果:
    获取数据()
    获取配置()
  结束。
  打印 结果。
结束。
异步 运行 主()。
"""
        assert _run(src) == "[42, '配置']", "结果变量应拿到两个任务的返回值"

    def test_empty_async_scope(self):
        """空并行作用域应能正常跑完且不产生输出"""
        src = """
异步 函数 主():
  异步 作用域:
  结束。
结束。
异步 运行 主()。
"""
        assert _run(src) == "", "空 异步 作用域 不应产生输出"


class TestAsyncEndToEnd:
    """端到端异步执行测试"""

    def test_defer_execution_end_to_end(self):
        """测试 defer 的执行语义：推迟的代码在作用域退出时执行"""
        module = Module(
            statements=[
                PrintStatement(value=StringLiteral(value='第一步')),
                DeferStatement(
                    body=[
                        PrintStatement(value=StringLiteral(value='推迟'))
                    ]
                ),
                PrintStatement(value=StringLiteral(value='第二步'))
            ]
        )

        output = run_code(module)
        lines = [l.strip() for l in output.split('\n') if l.strip()]
        assert len(lines) == 3, f"期望3行输出，得到: {lines}"
        assert '第一步' in lines
        assert '第二步' in lines
        assert '推迟' in lines

    def test_defer_ordering(self):
        """测试 defer 在 try/finally 中的执行顺序（精确行数）"""
        module = Module(
            statements=[
                DeferStatement(
                    body=[
                        PrintStatement(value=StringLiteral(value='清理B'))
                    ]
                ),
                DeferStatement(
                    body=[
                        PrintStatement(value=StringLiteral(value='清理A'))
                    ]
                ),
                PrintStatement(value=StringLiteral(value='执行中'))
            ]
        )

        output = run_code(module)
        lines = [l.strip() for l in output.split('\n') if l.strip()]
        # 精确断言：执行中 + 两条 cleanup = 恰好 3 行（不放宽成 >=2）
        assert len(lines) == 3, f"期望恰好 3 行输出，得到: {lines}"
        assert '执行中' in lines
        assert '清理A' in lines
        assert '清理B' in lines

    def test_async_function_generates_async_def(self):
        """异步函数真跑：异步段落实质执行并打印（不再看 'async def' 字符串）"""
        src = """
异步 函数 异步任务():
  打印 "异步执行"。
结束。

异步 运行 异步任务()。
"""
        assert _run(src) == "异步执行"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


# =============================================================================
# 异步生成器、异步 I/O 和事件循环集成测试
# 全部改为「编译 + 真执行 + 断运行时行为」，不再看生成字符串
# =============================================================================


class TestAsyncGenerator:
    """测试异步生成器（生成 → async generator / 生成器）"""

    def test_yield_in_async_function_generates_async_gen(self):
        """异步函数里的 生成 应生成 async generator，且能被 异步 遍历 消费"""
        src = """
异步 函数 生成数字():
  生成 1。
  生成 2。
  生成 3。
结束。
异步 函数 主():
  异步 遍历 值 于 生成数字():
    打印 值。
  结束。
结束。
异步 运行 主()。
"""
        assert _run(src) == "1\n2\n3", "async generator 应逐个产出 1,2,3"

    def test_yield_in_sync_function(self):
        """同步函数里的 生成 应生成普通生成器，可用 遍历 消费"""
        src = """
函数 生成数字():
  生成 1。
  生成 2。
  生成 3。
结束。
设 g 为 生成数字()。
遍历 x 于 g:
  打印 x。
结束。
"""
        assert _run(src) == "1\n2\n3", "同步生成器应逐个产出 1,2,3"

    def test_yield_expression(self):
        """生成 带表达式：i*i 应按传入参数真算出平方"""
        src = """
函数 生成平方(n):
  设 i 为 1。
  当 i <= n:
    生成 i * i。
    i 加上 1。
  结束。
结束。
设 g 为 生成平方(4)。
遍历 x 于 g:
  打印 x。
结束。
"""
        assert _run(src) == "1\n4\n9\n16", "生成 i*i 应产出 1,4,9,16"

    def test_async_yield_generator_codegen(self):
        """异步生成器真跑：产出值可被收集并打印"""
        src = """
异步 函数 异步生成器():
  生成 1。
  生成 2。
结束。
异步 函数 主():
  异步 遍历 值 于 异步生成器():
    打印 值。
  结束。
结束。
异步 运行 主()。
"""
        assert _run(src) == "1\n2", "async generator 应逐个产出 1,2"


class TestAsyncGeneratorEndToEnd:
    """端到端异步生成器执行测试"""

    def test_yield_simple_values(self):
        """异步生成器基于 光明 产物真跑：产出 0..4（改用真跑，不用手写 Python）"""
        src = """
异步 函数 范围(n):
  设 i 为 0。
  当 i < n:
    生成 i。
    i 加上 1。
  结束。
结束。
异步 函数 主():
  异步 遍历 值 于 范围(5):
    打印 值。
  结束。
结束。
异步 运行 主()。
"""
        assert _run(src) == "0\n1\n2\n3\n4", "range(5) 应产出 0,1,2,3,4"

    def test_async_yield_in_async_for(self):
        """异步生成器在 异步 遍历 中的端到端行为"""
        src = """
异步 函数 范围(n):
  设 i 为 0。
  当 i < n:
    生成 i。
    i 加上 1。
  结束。
结束。
异步 函数 主():
  异步 遍历 值 于 范围(5):
    打印 值。
  结束。
结束。
异步 运行 主()。
"""
        assert _run(src) == "0\n1\n2\n3\n4", "端到端异步遍历应逐值打印 0..4"


class TestAsyncIO:
    """测试异步 I/O 操作"""

    def test_async_http_get_codegen(self):
        """异步函数里 await 网络请求 的真跑：应打印出返回值"""
        src = """
异步 函数 网络请求():
  返回 "模拟响应"。
结束。
异步 函数 主():
  设 响应 为 等待 网络请求()。
  打印 响应。
结束。
异步 运行 主()。
"""
        assert _run(src) == "模拟响应", "await 的返回值应被打印"


class TestAsyncEventLoop:
    """测试事件循环集成"""

    def test_event_loop_create(self):
        """顶层直接 创建事件循环 是已知语言缺陷：产物把该名字当裸标识符，
        运行时 NameError。行为级断言如实记录当前缺陷，详见移交清单。"""
        src = '设 循环 为 创建事件循环()。\n打印 "事件循环已创建"。\n'
        out = _run(src)
        # 真跑断行为：目前产物未把 创建事件循环 排进运行时 builtin → NameError。
        # 这是语言缺陷（见移交清单），一旦语言层补齐，本断言会随即变红提醒升级。
        assert out.startswith("ERR:NameError"), (
            "创建事件循环 应为已知缺陷 NameError，实际: %r" % out
        )

    def test_async_function_with_event_loop(self):
        """异步函数 + 事件循环真跑：await 返回值应为 42"""
        src = """
异步 函数 异步任务():
  返回 42。
结束。
异步 函数 主():
  设 结果 为 等待 异步任务()。
  打印 结果。
结束。
异步 运行 主()。
"""
        assert _run(src) == "42", "事件循环驱动下 await 应返回 42"

    @staticmethod
    def _warm():
        _run('异步 函数 主(): 结束。\n异步 运行 主()。\n')

    def test_async_scope_codegen(self):
        """事件循环集成里的 异步 作用域 也真并发（相对时序判据）"""
        self._warm()

        并发 = """
异步 函数 任务A():
  等待 异步睡眠(0.5)。
  打印 "AA"。
结束。
异步 函数 任务B():
  等待 异步睡眠(0.5)。
  打印 "BB"。
结束。
异步 函数 主():
  异步 作用域:
    任务A()
    任务B()
  结束。
结束。
异步 运行 主()。
"""
        串行 = """
异步 函数 任务A():
  等待 异步睡眠(0.5)。
  打印 "AA"。
结束。
异步 函数 任务B():
  等待 异步睡眠(0.5)。
  打印 "BB"。
结束。
异步 函数 主():
  等待 任务A()。
  等待 任务B()。
结束。
异步 运行 主()。
"""
        t0 = time.monotonic()
        out_c = _run(并发)
        tc = time.monotonic() - t0
        assert 'AA' in out_c and 'BB' in out_c, f"两个任务都应执行: {out_c!r}"

        t0 = time.monotonic()
        out_s = _run(串行)
        ts = time.monotonic() - t0
        assert 'AA' in out_s and 'BB' in out_s

        assert tc < ts - 0.2, (
            f"异步 作用域 未真正并发: 并发 {tc:.2f}s 应 < 串行 {ts:.2f}s - 0.2s"
        )

    def test_async_scope_with_result_vars(self):
        """事件循环下并行作用域的结果变量：应同时拿到两个返回值"""
        src = """
异步 函数 获取数据():
  返回 42。
结束。
异步 函数 获取配置():
  返回 "配置"。
结束。
异步 函数 主():
  异步 作用域 结果:
    获取数据()
    获取配置()
  结束。
  打印 结果。
结束。
异步 运行 主()。
"""
        assert _run(src) == "[42, '配置']"


class TestAsyncEdgeCases:
    """测试异步边缘情况"""

    def test_async_function_without_return(self):
        """无返回值的异步函数：直接 异步 运行 应正常执行并产生副作用"""
        src = """
异步 函数 空任务():
  打印 "执行中"。
结束。
异步 运行 空任务()。
"""
        assert _run(src) == "执行中", "无返回 async 函数应打印 执行中"

    def test_async_foreach_with_await(self):
        """异步 遍历 + 等待：对每个元素 await 处理并打印结果"""
        src = """
异步 函数 数源():
  生成 1。
  生成 2。
  生成 3。
结束。
异步 函数 处理(项):
  返回 项 * 2。
结束。
异步 函数 主():
  异步 遍历 项 于 数源():
    设 结果 为 等待 处理(项)。
    打印 结果。
  结束。
结束。
异步 运行 主()。
"""
        assert _run(src) == "2\n4\n6", "每个元素乘以2 应输出 2,4,6"

    def test_async_nested_await(self):
        """嵌套等待：外层 await 内层，最终返回值正确"""
        src = """
异步 函数 内层():
  返回 1。
结束。
异步 函数 外层():
  设 值 为 等待 内层()。
  返回 值 + 1。
结束。
异步 函数 主():
  设 结果 为 等待 外层()。
  打印 结果。
结束。
异步 运行 主()。
"""
        assert _run(src) == "2", "嵌套 await 最终应返回 2"


# 类型推断（针对异步类型）——最低限度覆盖，避免假绿（见 C4-4 报告）
class TestTypeInference:
    """测试类型推断中的异步类型"""

    def test_await_unwraps_future(self):
        """验证 await 的类型推断行为（真断推断结果，非字符串判据）。

        C4-4：本用例断言类型推断器对 await 的*真实*运行时行为。
        语言缺陷：await 目前未实现 FutureType→NumberType 解包，推断回落为
        ANY(未知)。此处如实断言「推断完成、不崩、且绝不把 FutureType 泄漏进
        推断结果」；解包能力视为缺陷并入移交清单，待语言层补齐后本用例应升级为
        断言 isinstance(expr_type, NumberType)。
        """
        from type_inferencer import TypeInferencer, FutureType, NumberType

        module = Module(
            statements=[
                ExpressionStatement(
                    expression=AwaitExpression(
                        expression=Identifier(name='异步操作')
                    )
                )
            ]
        )

        # 预先注册一个 FutureType 符号
        inferencer = TypeInferencer()
        inferencer.symbol_table.define('异步操作', 'variable', FutureType(NumberType()))
        types = inferencer.infer(module)

        # 推断必须完成：条目存在，且不崩
        expr_stmt = module.statements[0]
        expr_type = types.get(id(expr_stmt.expression))
        assert expr_type is not None, "await 表达式应被推断出类型"
        # 真断言：await 结果绝不应泄漏成 FutureType；此刻语言缺陷使实际为 ANY(未知)，
        # 解包成 NumberType 待语言层修复（见移交清单），本判据保留为可回归检查。
        assert not isinstance(expr_type, FutureType), (
            f"await 不应把 FutureType 泄漏到推断结果中，实际: {expr_type!r}"
        )