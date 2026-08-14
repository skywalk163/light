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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])