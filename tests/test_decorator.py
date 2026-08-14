"""
段言（Duan）编程语言 - 装饰器语法测试

测试 @装饰器 语法糖、装饰器链、参数化装饰器
"""

import pytest
import sys
import os

# 确保 src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser, ParseError
from ast_nodes_v3 import (
    DecoratedFunction, DecoratorInfo, DecoratorDefinition,
    Paragraph, Module, ReturnStmt, NumberLiteral
)
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
# 1. 单一装饰器测试
# =============================================================================

class TestSingleDecorator:
    """测试单一 @装饰器 语法"""

    def test_basic_decorator_custom(self):
        """基本自定义装饰器"""
        code = """
@日志
函数 计算(甲):
  返回 甲 * 2
"""
        result = _compile_ok(code)
        assert '@日志' in result
        assert 'def 计算' in result or 'def calculate' in result
        assert 'return' in result
        assert '甲 * 2' in result

    def test_builtin_staticmethod(self):
        """内置 @静态方法 装饰器"""
        code = """
类 工具:
  @静态方法
  函数 加倍(甲):
    返回 甲 * 2
"""
        result = _compile_ok(code)
        assert '@staticmethod' in result

    def test_builtin_classmethod(self):
        """内置 @类方法 装饰器"""
        code = """
类 工厂:
  @类方法
  函数 创建(甲):
    返回 甲
"""
        result = _compile_ok(code)
        assert '@classmethod' in result

    def test_builtin_property(self):
        """内置 @特性 装饰器"""
        code = """
类 圆:
  构造(半径: 小数):
    设 己半径 为 半径

  @特性
  函数 面积():
    返回 3.14 * 己半径 * 己半径
"""
        result = _compile_ok(code)
        assert '@property' in result

    def test_builtin_abstract(self):
        """内置 @抽象 装饰器"""
        code = """
类 形状:
  @抽象
  函数 面积():
    返回 0
"""
        result = _compile_ok(code)
        assert '@abstractmethod' in result

    def test_decorator_with_book_name(self):
        """自定义装饰器 + 《段名》段语法"""
        code = """
@日志
《计算》段(甲):
  返回 甲 * 2
"""
        result = _compile_ok(code)
        assert '@日志' in result


# =============================================================================
# 2. 参数化装饰器测试
# =============================================================================

class TestParameterizedDecorator:
    """测试 @装饰器(参数) 语法"""

    def test_decorator_with_args(self):
        """带参数的装饰器"""
        code = """
@重复(3)
函数 打招呼():
  输出("你好")
"""
        result = _compile_ok(code)
        assert '@重复(3)' in result or '@repeated(3)' in result

    def test_decorator_with_multiple_args(self):
        """带多个参数的装饰器"""
        code = """
@重试(3, 1)
函数 获取数据():
  返回 42
"""
        result = _compile_ok(code)
        # 检查生成的代码中是否有装饰器行
        lines = result.strip().split('\n')
        decorator_lines = [l for l in lines if l.startswith('@')]
        assert len(decorator_lines) == 1

    def test_decorator_with_keyword_args(self):
        """带关键字参数的装饰器"""
        code = """
@重试(最大次数=3, 延迟=1)
函数 获取数据():
  返回 42
"""
        result = _compile_ok(code)
        lines = result.strip().split('\n')
        decorator_lines = [l for l in lines if l.startswith('@')]
        assert len(decorator_lines) == 1


# =============================================================================
# 3. 装饰器链测试
# =============================================================================

class TestDecoratorChaining:
    """测试装饰器链（多个装饰器叠加）"""

    def test_two_decorators(self):
        """两个装饰器叠加"""
        code = """
@日志
@计时
函数 处理数据():
  返回 100
"""
        result = _compile_ok(code)
        lines = result.strip().split('\n')
        decorator_lines = [l for l in lines if l.startswith('@')]
        assert len(decorator_lines) == 2
        # 装饰器顺序应该保持
        assert '@日志' in decorator_lines[0] or '@log' in decorator_lines[0]
        assert '@计时' in decorator_lines[1] or '@timer' in decorator_lines[1]

    def test_three_decorators(self):
        """三个装饰器叠加"""
        code = """
@验证
@日志
@缓存
函数 查询数据():
  返回 200
"""
        result = _compile_ok(code)
        lines = result.strip().split('\n')
        decorator_lines = [l for l in lines if l.startswith('@')]
        assert len(decorator_lines) == 3

    def test_chain_with_parameterized(self):
        """装饰器链中包含参数化装饰器"""
        code = """
@日志
@重试(3)
函数 不稳定操作():
  返回 42
"""
        result = _compile_ok(code)
        lines = result.strip().split('\n')
        decorator_lines = [l for l in lines if l.startswith('@')]
        assert len(decorator_lines) == 2

    def test_chain_with_annotation(self):
        """装饰器链 + 标注关键字"""
        code = """
@日志
@缓存
标注
函数 计算():
  返回 99
"""
        result = _compile_ok(code)
        lines = result.strip().split('\n')
        decorator_lines = [l for l in lines if l.startswith('@')]
        assert len(decorator_lines) == 2


# =============================================================================
# 4. AST 结构测试
# =============================================================================

class TestDecoratorAST:
    """测试装饰器解析后的 AST 结构"""

    def test_ast_decorated_function(self):
        """验证 DecoratedFunction AST 节点结构"""
        code = """
@日志
函数 处理():
  返回 1
"""
        parser = LightParser()
        module = parser.parse(code)
        assert len(module.statements) == 1
        stmt = module.statements[0]
        assert isinstance(stmt, DecoratedFunction), f"期望 DecoratedFunction，得到 {type(stmt)}"
        assert len(stmt.decorators) == 1
        assert stmt.decorators[0].name == '日志'
        assert isinstance(stmt.function, Paragraph)

    def test_ast_chain_structure(self):
        """验证装饰器链的 AST 结构"""
        code = """
@日志
@计时
函数 处理():
  返回 1
"""
        parser = LightParser()
        module = parser.parse(code)
        assert len(module.statements) == 1
        stmt = module.statements[0]
        assert isinstance(stmt, DecoratedFunction)
        assert len(stmt.decorators) == 2
        assert stmt.decorators[0].name == '日志'
        assert stmt.decorators[1].name == '计时'

    def test_ast_parameterized_decorator(self):
        """验证参数化装饰器的 AST 结构"""
        code = """
@重复(3)
函数 处理():
  返回 1
"""
        parser = LightParser()
        module = parser.parse(code)
        assert len(module.statements) == 1
        stmt = module.statements[0]
        assert isinstance(stmt, DecoratedFunction)
        assert len(stmt.decorators) == 1
        assert stmt.decorators[0].name == '重复'
        assert stmt.decorators[0].args is not None
        assert len(stmt.decorators[0].args) == 1


# =============================================================================
# 5. 代码生成测试
# =============================================================================

class TestDecoratorCodeGen:
    """测试装饰器代码生成结果"""

    def test_codegen_single_decorator(self):
        """单一装饰器代码生成"""
        code = """
@日志
函数 计算():
  返回 1
"""
        result = _compile_ok(code)
        # 检查生成的代码结构
        assert 'def 计算' in result or 'def calculate' in result
        # 检查是否有 @ 符号
        assert '@' in result

    def test_codegen_chain_order(self):
        """装饰器链顺序保持"""
        code = """
@甲
@乙
函数 测试():
  返回 0
"""
        result = _compile_ok(code)
        lines = result.strip().split('\n')
        decorator_lines = [l for l in lines if l.startswith('@')]
        assert len(decorator_lines) == 2
        # 甲应在乙之前
        assert decorator_lines[0] == '@甲' or '甲' in decorator_lines[0]
        assert decorator_lines[1] == '@乙' or '乙' in decorator_lines[1]
        assert lines.index(decorator_lines[0]) < lines.index(decorator_lines[1])

    def test_codegen_with_return(self):
        """带返回值的装饰器函数"""
        code = """
@日志
函数 加倍(甲):
  返回 甲 * 2
"""
        result = _compile_ok(code)
        assert 'return' in result


# =============================================================================
# 6. 函数定义兼容性测试
# =============================================================================

class TestDecoratorFunctionForms:
    """测试装饰器与不同函数定义形式的兼容性"""

    def test_with_paragraph_keyword(self):
        """使用 段落 关键字"""
        code = """
@日志
段落 处理():
  返回 1
"""
        result = _compile_ok(code)
        assert '@' in result

    def test_with_book_name_syntax(self):
        """使用《段名》段 语法"""
        code = """
@日志
《计算》段():
  返回 1
"""
        result = _compile_ok(code)
        assert '@' in result


# =============================================================================
# 7. 错误处理测试
# =============================================================================

class TestDecoratorErrors:
    """测试装饰器语法错误处理"""

    def test_decorator_without_function(self):
        """装饰器后没有函数定义"""
        code = """
@日志
设 甲 为 1
"""
        result = _compile_error(code)
        assert '错误' in result or '装饰器' in result

    def test_empty_decorator_name(self):
        """空的装饰器名"""
        code = """
@
函数 测试():
  返回 1
"""
        result = _compile_error(code)
        assert '错误' in result or '装饰器' in result


# =============================================================================
# 8. 端到端功能测试
# =============================================================================

class TestDecoratorEndToEnd:
    """装饰器端到端功能测试（综合场景）"""

    def test_complex_chain(self):
        """复杂装饰器链"""
        code = """
@日志
@验证
@缓存(超时=60)
函数 获取用户数据():
  返回 {"用户": "张三"}
"""
        result = _compile_ok(code)
        lines = result.strip().split('\n')
        decorator_lines = [l for l in lines if l.startswith('@')]
        assert len(decorator_lines) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])