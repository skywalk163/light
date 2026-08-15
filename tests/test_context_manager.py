"""
段言（Duan）编程语言 - 上下文管理器测试

测试 使用 关键字资源管理，包括同步/异步上下文管理器、多个上下文管理器
"""

import pytest
import sys
import os

# 确保 src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser, ParseError
from ast_nodes_v3 import WithStmt, Module, ReturnStmt, NumberLiteral
from code_generator import PythonCodeGenerator as CodeGenerator


# =============================================================================
# 编译辅助函数
# =============================================================================

def _compile_ok(code: str) -> str:
    """编译代码，成功返回生成的Python代码，失败抛出异常"""
    parser = LightParser()
    module = parser.parse(code)
    gen = CodeGenerator()
    result = gen.generate(module)
    return result


def _compile_error(code: str) -> str:
    """编译代码，期望失败返回错误信息"""
    parser = LightParser()
    try:
        module = parser.parse(code)
        gen = CodeGenerator()
        result = gen.generate(module)
        return f"期望错误但编译成功: {result}"
    except (ParseError, Exception) as e:
        return str(e)


# =============================================================================
# 1. 基本上下文管理器测试
# =============================================================================

class TestBasicWith:
    """测试基本使用 关键字上下文管理器"""

    def test_with_simple_expr(self):
        """基本使用表达式"""
        code = """
使用 打开("test.txt") 为 f:
  输出(f)
"""
        result = _compile_ok(code)
        assert 'with open(' in result or 'with 打开(' in result
        assert 'as f' in result

    def test_with_variable(self):
        """使用变量作为上下文管理器"""
        code = """
设 资源 为 创建资源()
使用 资源:
  输出("使用资源")
"""
        result = _compile_ok(code)
        assert 'with ' in result

    def test_with_body(self):
        """上下文管理器体"""
        code = """
使用 打开("a.txt") 为 f:
  设 内容 为 f.读取()
  输出(内容)
"""
        result = _compile_ok(code)
        assert 'with ' in result
        assert 'f.读取' in result or 'f.read' in result

    def test_without_variable(self):
        """不使用 as 变量"""
        code = """
使用 锁:
  输出("临界区")
"""
        result = _compile_ok(code)
        assert 'with 锁:' in result or 'with lock:' in result


# =============================================================================
# 2. 异步上下文管理器测试
# =============================================================================

class TestAsyncWith:
    """测试使用 异步 上下文管理器"""

    def test_async_with_basic(self):
        """基本异步上下文管理器"""
        code = """
使用 异步 打开文件("test.txt") 为 f:
  等待 f.读取()
"""
        result = _compile_ok(code)
        assert 'async with ' in result

    def test_async_with_await(self):
        """异步上下文管理器 + 等待"""
        code = """
使用 异步 连接数据库() 为 db:
  设 结果 为 等待 db.查询("SELECT 1")
  输出(结果)
"""
        result = _compile_ok(code)
        assert 'async with ' in result

    def test_async_without_variable(self):
        """异步上下文管理器不带变量"""
        code = """
使用 异步 资源锁:
  输出("异步临界区")
"""
        result = _compile_ok(code)
        assert 'async with ' in result

    def test_async_with_return(self):
        """异步上下文管理器 + 返回值"""
        code = """
函数 处理数据():
  使用 异步 打开文件("data.txt") 为 f:
    返回 等待 f.读取()
"""
        result = _compile_ok(code)
        assert 'async with ' in result


# =============================================================================
# 3. AST 结构测试
# =============================================================================

class TestWithAST:
    """测试上下文管理器 AST 结构"""

    def test_ast_with_stmt(self):
        """验证 WithStmt AST 节点"""
        code = """
使用 打开("test.txt") 为 f:
  输出(f)
"""
        parser = LightParser()
        module = parser.parse(code)
        assert len(module.statements) >= 1
        # 找到 WithStmt
        with_stmt = None
        for stmt in module.statements:
            if isinstance(stmt, WithStmt):
                with_stmt = stmt
                break
        assert with_stmt is not None, "未找到 WithStmt 节点"
        assert with_stmt.variable == 'f'

    def test_ast_async_with(self):
        """验证异步上下文管理器 AST 节点"""
        code = """
使用 异步 打开文件("test.txt") 为 f:
  等待 f.读取()
"""
        parser = LightParser()
        module = parser.parse(code)
        with_stmt = None
        for stmt in module.statements:
            if isinstance(stmt, WithStmt):
                with_stmt = stmt
                break
        assert with_stmt is not None
        assert with_stmt.is_async == True

    def test_ast_multiple_items(self):
        """验证多个上下文管理器 AST 节点"""
        code = """
使用 打开("a.txt") 为 f1, 打开("b.txt") 为 f2:
  输出(f1)
"""
        parser = LightParser()
        module = parser.parse(code)
        with_stmt = None
        for stmt in module.statements:
            if isinstance(stmt, WithStmt):
                with_stmt = stmt
                break
        assert with_stmt is not None
        assert with_stmt.items is not None
        assert len(with_stmt.items) == 2


# =============================================================================
# 5. 代码生成测试
# =============================================================================

class TestWithCodeGen:
    """测试上下文管理器代码生成"""

    def test_codegen_sync_with(self):
        """同步上下文管理器代码生成"""
        code = """
使用 打开("test.txt") 为 f:
  输出(f)
"""
        result = _compile_ok(code)
        assert 'with ' in result
        assert 'as f:' in result

    def test_codegen_async_with(self):
        """异步上下文管理器代码生成"""
        code = """
使用 异步 打开文件("test.txt") 为 f:
  等待 f.读取()
"""
        result = _compile_ok(code)
        assert 'async with ' in result


# =============================================================================
# 6. 端到端功能测试
# =============================================================================

class TestWithEndToEnd:
    """上下文管理器端到端测试"""

    def test_with_file_read(self):
        """使用文件读取"""
        code = """
使用 打开("data.txt") 为 f:
  设 内容 为 f.读取()
  输出(内容)
"""
        result = _compile_ok(code)
        assert 'with ' in result
        assert 'f.读取' in result or 'f.read' in result

    def test_async_with_file(self):
        """异步文件读取"""
        code = """
使用 异步 打开文件("data.txt") 为 f:
  设 内容 为 等待 f.读取()
  输出(内容)
"""
        result = _compile_ok(code)
        assert 'async with ' in result


# =============================================================================
# 7. 等待(await) 与复合标识符的消歧边界（v7 单 07 回归）
# =============================================================================

class TestAwaitMemberAccess:
    """`等待 对象.成员` 必须解析成 await 表达式，而 `等待X` 仍是复合标识符

    v7 单 07：`src/parser_expr.py` 的 `等待` 分支原先只把「等待 标识符(」当 await，
    peek2 是 DOT 时误走复合标识符分支，只吃掉 `等待`+`f` 返回 Identifier('等待f')，
    `.读取()` 被丢在 token 流里没人消费 → ParseError「无法识别的语法元素：'.'」。
    修复把 DOT 一并归入 await 一侧。这里两头都测，防止修复方向倒过来打穿复合标识符。
    """

    def test_await_member_call(self):
        """等待 + 内置名成员：不应报错，且成员名不被内置映射改写"""
        result = _compile_ok('等待 f.读取()\n')
        assert 'await f.读取()' in result
        # 单 03 的成员访问护栏仍在：不能退化成 await input(f)
        assert 'input(f)' not in result

    def test_await_member_call_non_builtin(self):
        """等待 + 非内置名成员"""
        result = _compile_ok('等待 f.抓取()\n')
        assert 'await f.抓取()' in result

    def test_await_chained_member(self):
        """等待 + 链式成员访问"""
        result = _compile_ok('等待 甲.乙.丙()\n')
        assert 'await 甲.乙.丙()' in result

    def test_await_plain_call_unchanged(self):
        """等待 + 普通调用：原有行为不变"""
        result = _compile_ok('等待 读取(f)\n')
        assert 'await ' in result

    def test_compound_identifier_before_rparen(self):
        """等待价值 在右括号前仍是复合标识符，不是 await"""
        result = _compile_ok('打印(等待价值)\n')
        assert 'print(等待价值)' in result
        assert 'await' not in result

    def test_compound_identifier_before_newline(self):
        """等待价值 在行尾仍是复合标识符"""
        result = _compile_ok('设 甲 为 等待价值\n')
        assert '甲 = 等待价值' in result
        assert 'await' not in result

    def test_compound_identifier_before_operator(self):
        """等待结果 后跟运算符时仍是复合标识符"""
        result = _compile_ok('设 甲 为 等待结果 加 1\n')
        assert '等待结果' in result
        assert 'await' not in result


class TestBracketCallArity:
    """v7 单 04：括号式调用不再被内置动词的 arity 截断

    `求和` 在 VERB_ARITY 里 arity=1，用户却可以定义 `段 求和(a, b)`。
    原实现用 arity 给括号式收参循环封顶，把 `求和(10, 20)` 编成 `求和(10)`，
    编译期不报错、运行期才炸，属静默错译。括号与逗号已界定边界，不该再套 arity。
    """

    def test_two_args_not_truncated(self):
        result = _compile_ok('段 求和(a, b)：\n  返回 a + b\n打印(求和(10, 20))\n')
        assert '求和(10, 20)' in result

    def test_three_args_not_truncated(self):
        """不是「只丢最后一个」：原实现会丢掉 arity 之后的全部"""
        result = _compile_ok('段 求和(a, b, c)：\n  返回 a + b + c\n打印(求和(1, 2, 3))\n')
        assert '求和(1, 2, 3)' in result

    def test_nested_call_not_truncated(self):
        result = _compile_ok('段 求和(a, b)：\n  返回 a + b\n打印(求和(求和(1, 2), 3))\n')
        assert '求和(求和(1, 2), 3)' in result

    def test_non_verb_name_unchanged(self):
        """名字不撞内置动词时走标识符路径，行为不变"""
        result = _compile_ok('段 加法(a, b)：\n  返回 a + b\n打印(加法(10, 20))\n')
        assert '加法(10, 20)' in result

    def test_args_fewer_than_arity_unchanged(self):
        """实参数 ≤ arity 的旧输入产物不变（收满即遇 RPAREN 停）"""
        result = _compile_ok('打印(长度([1, 2, 3]))\n')
        assert 'len([1, 2, 3])' in result


class TestContainsOperator:
    """v7 单 08：`包含` 的内部占位符 @@contains@@ 不再泄漏，且操作数方向正确

    `A 包含 B` 语义是「A 含有 B」→ Python `B in A`，操作数必须交换。
    只把占位符替换成 `in` 而不交换，会得到语法通过、语义相反的静默错译，
    比原来的 SyntaxError 更坏。
    """

    _SRC = ('段落 查找 接收 文件名, 关键词:\n'
            '  如果 文件名 包含 关键词:\n'
            '    打印("命中")。\n')

    def test_placeholder_not_leaked(self):
        assert '@@' not in _compile_ok(self._SRC)

    def test_operand_order_swapped(self):
        """容器在左、被找的东西在右 → 产物必须是 关键词 in 文件名"""
        result = _compile_ok(self._SRC)
        assert '(关键词 in 文件名)' in result
        assert '(文件名 in 关键词)' not in result

    def test_compound_or_expression(self):
        """工单原形：或复合条件里也不泄漏、方向不变"""
        result = _compile_ok('段落 查找 接收 文件名, 关键词:\n'
                             '  如果 关键词 等于 "" 或 文件名 包含 关键词:\n'
                             '    打印("命中")。\n')
        assert '@@' not in result
        assert '(关键词 in 文件名)' in result

    def test_parens_kept_to_avoid_chained_comparison(self):
        """括号必须留：in 是比较运算符，裸发射会与外层比较串成链式比较

        `x in y == False` 会被 Python 解释成 `(x in y) and (y == False)`，恒假。
        """
        result = _compile_ok('段落 查找 接收 文件名, 关键词:\n'
                             '  如果 (文件名 包含 关键词) 等于 假:\n'
                             '    打印("未命中")。\n')
        assert '(关键词 in 文件名)' in result

    def test_other_operators_unchanged(self):
        """不含 包含 的运算符不受影响"""
        result = _compile_ok('设 甲 为 1 加 2\n')
        assert '@@' not in result
        assert '(1 + 2)' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])