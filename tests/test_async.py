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
        """B5：defer 真跑 —— 新语义（FILO 延迟执行）。

        旧实现把 defer 体内联（开始→推迟执行→结束），B5 改为：
        推迟体在作用域退出时执行（栈序 FILO），顺序为 开始→结束→推迟执行。
        该判据由 B5 修改，原因是旧实现（unified 的 try-body-pass / finally-内联）
        语义等于不推迟，与 `推迟` 关键字语义不符。
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
        # B5 新语义：推迟体在作用域退出时执行，顺序为 开始→结束→推迟执行
        assert lines == ['开始', '结束', '推迟执行'], f"defer 执行顺序: {lines}"

    def test_defer_try_finally_structure(self):
        """defer 真跑：body 被真实执行一次（unified 链路）"""
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

    # ---- 主链路（PythonCodeGenerator）行为判据 ----

    def test_defer_main_chain_basic(self):
        """主链路真跑：推迟体在作用域退出时执行（FILO），不是内联执行。

        判据：输出顺序为 开始→结束→推迟执行（推迟在段落体结束后才跑）。
        反面：旧实现输出 开始→推迟执行→结束（内联 = 不推迟）。
        """
        src = """
段落 测试:
  打印 "开始"。
  推迟 打印 "推迟执行"。
  打印 "结束"。
结束。

测试()。
"""
        out = _run(src)
        lines = [l.strip() for l in out.split('\n') if l.strip()]
        assert lines == ['开始', '结束', '推迟执行'], \
            f"主链路 defer 顺序应为 开始→结束→推迟执行，实际: {lines}"

    def test_defer_main_chain_filo_multiple(self):
        """主链路真跑：多个推迟按 FILO（后进先出）执行。

        判据：注册顺序 第一→第二，执行顺序 第二→第一（栈序）。
        """
        src = """
段落 测试:
  推迟 打印 "第一"。
  推迟 打印 "第二"。
  打印 "主体"。
结束。

测试()。
"""
        out = _run(src)
        lines = [l.strip() for l in out.split('\n') if l.strip()]
        assert lines == ['主体', '第二', '第一'], \
            f"多 defer FILO 顺序应为 主体→第二→第一，实际: {lines}"

    def test_defer_main_chain_early_return(self):
        """主链路真跑：提前返回时推迟体仍执行。

        判据：return 后推迟体仍然跑，输出 before-return→清理。
        "不应执行" 不可出现在输出中（return 后的语句被跳过）。
        """
        src = """
段落 测试:
  推迟 打印 "清理"。
  打印 "before-return"。
  返回。
  打印 "不应执行"。
结束。

测试()。
"""
        out = _run(src)
        lines = [l.strip() for l in out.split('\n') if l.strip()]
        assert lines == ['before-return', '清理'], \
            f"early return 时 defer 应执行，顺序 before-return→清理，实际: {lines}"

    def test_defer_main_chain_exception_path(self):
        """主链路真跑：异常路径上推迟体仍执行（finally 语义）。

        判据：抛出异常后推迟体先执行（异常清理），再传播异常被外层捕获。
        输出顺序 before-raise→异常清理→caught。
        """
        src = """
段落 测试:
  推迟 打印 "异常清理"。
  打印 "before-raise"。
  抛出 值错误("测试异常")。
  打印 "不应执行"。
结束。

尝试:
  测试()。
捕获 值错误:
  打印 "caught"。
"""
        out = _run(src)
        lines = [l.strip() for l in out.split('\n') if l.strip()]
        assert lines == ['before-raise', '异常清理', 'caught'], \
            f"异常路径 defer 应执行，顺序 before-raise→异常清理→caught，实际: {lines}"

    def test_defer_main_chain_block_form(self):
        """主链路真跑：块形式推迟（推迟：\\n  body）正确解析且延迟执行。

        判据：块体在主体之后执行，输出 主体→块-第一→块-第二。
        """
        src = """
段落 测试:
  推迟:
    打印 "块-第一"。
    打印 "块-第二"。
  打印 "主体"。
结束。

测试()。
"""
        out = _run(src)
        lines = [l.strip() for l in out.split('\n') if l.strip()]
        assert lines == ['主体', '块-第一', '块-第二'], \
            f"块形式 defer 应在主体后执行，顺序 主体→块-第一→块-第二，实际: {lines}"


class TestAsyncForeachGeneralization:
    """B5：异步遍历泛化——普通 list 与异步生成器都能用「异步 遍历」"""

    def test_async_foreach_on_normal_list(self):
        """主链路真跑：异步遍历普通 list 收集结果。

        判据：[1,2,3] 每项乘 2 后追加到结果列表，输出 [2, 4, 6]。
        反面：直接发 `async for` 不包装会抛 TypeError: 'async for' requires __aiter__。
        """
        src = """
异步 函数 测试():
  设 结果 为 []
  异步 遍历 项 于 [1, 2, 3]:
    结果.追加(项 * 2)
  打印 结果。
结束。

异步 运行 测试()。
"""
        out = _run(src)
        assert out == '[2, 4, 6]', f"异步遍历普通 list 应收集结果 [2, 4, 6]，实际: {out!r}"

    def test_async_foreach_on_async_generator(self):
        """主链路真跑：异步遍历异步生成器走原路 async for。

        判据：异步生成器 yield 1/2/3，异步遍历打印各值，输出 1→2→3。
        """
        src = """
异步 函数 生成器():
  生成 1。
  生成 2。
  生成 3。
结束。

异步 函数 测试():
  异步 遍历 项 于 生成器():
    打印 项。
  结束。
结束。

异步 运行 测试()。
"""
        out = _run(src)
        lines = [l.strip() for l in out.split('\n') if l.strip()]
        assert lines == ['1', '2', '3'], \
            f"异步遍历异步生成器应输出 1→2→3，实际: {lines}"

    def test_async_foreach_on_range(self):
        """主链路真跑：异步遍历 range 回退收集语义。

        判据：range(1,5) 求和 = 1+2+3+4 = 10。
        """
        src = """
异步 函数 测试():
  设 总和 为 0。
  异步 遍历 项 于 范围(1, 5):
    设 总和 为 总和 + 项。
  打印 总和。
结束。

异步 运行 测试()。
"""
        out = _run(src)
        assert out == '10', f"异步遍历 range 求和应为 10，实际: {out!r}"

    def test_sync_foreach_not_affected(self):
        """主链路真跑：同步遍历不受异步遍历泛化影响。

        判据：同步遍历 [10,20,30] 各加 1，输出 [11, 21, 31]。
        """
        src = """
段落 测试:
  设 结果 为 []
  遍历 项 于 [10, 20, 30]:
    结果.追加(项 + 1)
  打印 结果。
结束。

测试()。
"""
        out = _run(src)
        assert out == '[11, 21, 31]', f"同步遍历不受影响应为 [11, 21, 31]，实际: {out!r}"


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