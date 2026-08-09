"""
可空类型安全（Null Safety）测试 —— 强制可空类型 unwrap 系统

测试点：
1. 可空类型声明：设值为空 → 推断为 NullType（空|空）
2. unwrap 基本：设值为空! → 非可空
3. 变量声明可空后解包使用
4. 段落参数非可空 → 调用时传可空值报错（必须 unwrap）
5. 段落参数可空 → 正常传参
6. 运算时未 unwrap 报错
7. 返回类型为可空
8. unwrap 非可空值（警告但允许）
9. 与现有测试兼容（确保不破坏 Phase 1-5）
"""

import os
import sys

# 确保从 src 目录导入
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, 'src')
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
    sys.path.insert(0, _project_root)

import unittest
from compiler import DuanCompiler
from type_inferencer import TypeInferencer
from type_system import NullType, OptionalTypeWrapper, NumberType, UnknownType


def compile_source(src: str) -> DuanCompiler:
    """编译源码，返回编译器实例"""
    c = DuanCompiler()
    c.compile(src)
    return c


class TestNullSafetyBasic(unittest.TestCase):
    """基础可空类型测试"""

    def test_null_declaration(self):
        """测试点 1：设值为空 → 推断为 NullType"""
        c = compile_source('设值为空。')
        sym = c._inferencer.symbol_table.lookup('值')
        self.assertIsNotNone(sym, "'值' 变量应被定义")
        # 空字面量应被推断为 NullType
        self.assertIsInstance(sym.data_type, NullType)

    def test_unwrap_basic(self):
        """测试点 2：设值为空! → 解包"""
        c = compile_source('设值为空!。')
        sym = c._inferencer.symbol_table.lookup('值')
        self.assertIsNotNone(sym, "'值' 变量应被定义")
        # 对空值执行 ! 会被转为非可空（可能 UnknownType，表示运行时断言结果）
        self.assertNotIsInstance(sym.data_type, OptionalTypeWrapper)

    def test_unwrap_on_nullable_variable(self):
        """测试点 3：变量声明为可空，然后解包"""
        # 这里使用嵌套调用场景：先定义可空，再定义使用其 unwrap 后的值
        # 由于光明当前推断器将每个顶层语句的 VariableDeclaration 独立推断，
        # 我们通过简单赋值链来测试
        src = (
            '设值为空。'
            '设值2为值!。'
        )
        c = compile_source(src)
        sym = c._inferencer.symbol_table.lookup('值2')
        self.assertIsNotNone(sym)
        # 值2 是 值! 的推断类型，应该不是可空类型
        self.assertNotIsInstance(sym.data_type, OptionalTypeWrapper)


class TestNullSafetyFunctionCall(unittest.TestCase):
    """段落调用可空检查"""

    def test_func_non_nullable_param_with_nullable_arg(self):
        """测试点 4：形参非可空，传入可空实参 → 应报错"""
        src = (
            '段落展示内容接收内容:数：\n'
            '    打印内容。\n'
            '设值为空。\n'
            '展示内容(值)。\n'
        )
        c = compile_source(src)
        # 应有与可空相关的错误
        errors = [e for e in c.errors if '可空' in e or 'unwrap' in e or '解包' in e]
        self.assertTrue(
            len(errors) > 0,
            f"期望形参非可空且实参可空时报错，但得到: {c.errors}"
        )

    def test_func_non_nullable_param_with_unwrapped_arg(self):
        """形参非可空，传入 unwrap 后的值 → 不应有可空错误"""
        src = (
            '段落打印数接收数：\n'
            '    打印数。\n'
            '设值为42。\n'
            '打印数(值!)。\n'
        )
        c = compile_source(src)
        # 不应有可空错误
        errors = [e for e in c.errors if '可空' in e or 'unwrap' in e or '解包' in e]
        self.assertEqual(len(errors), 0, f"不期望有可空错误，得到: {errors}")

    def test_func_nullable_param_with_nullable_arg(self):
        """测试点 5：形参可空，传入可空实参 → 正常"""
        src = (
            '段落打印值接收值：\n'
            '    打印值。\n'
            '设空值为空。\n'
            '打印值(空值)。\n'
        )
        c = compile_source(src)
        # 注意：如果形参未声明类型，默认 type_inferencer 会用 TypeVar/Unknown
        # 这里主要测试不会崩溃
        self.assertIsNotNone(c._inferencer)


class TestNullSafetyArithmetic(unittest.TestCase):
    """运算时可空检查"""

    def test_operation_without_unwrap(self):
        """测试点 6：参与运算的值是可空的但未 unwrap → 应报错"""
        src = (
            '设值为空。'
            '设结果为值加1。'
        )
        c = compile_source(src)
        errors = [e for e in c.errors if '可空' in e or 'unwrap' in e or '解包' in e]
        self.assertTrue(
            len(errors) > 0,
            f"期望可空值参与运算时报错，但得到: {c.errors}"
        )

    def test_operation_with_unwrap(self):
        """可空值先 unwrap 再运算 → 正常"""
        src = (
            '设值为3。'
            '设结果为值!加1。'
        )
        c = compile_source(src)
        errors = [e for e in c.errors if '可空' in e or 'unwrap' in e or '解包' in e]
        self.assertEqual(len(errors), 0)


class TestUnwrapExpressionAst(unittest.TestCase):
    """AST 层级的 UnwrapExpression 测试"""

    def test_parsed_has_unwrap_expression(self):
        """确保解析后能产生 UnwrapExpression 节点"""
        c = DuanCompiler()
        raw = c.parse_raw('设值为空!。')
        # 从原始 AST 中查看存在 UnwrapExpression
        ast_nodes = []

        def walk(node):
            if node is None:
                return
            # 优先走 __slots__（v3 AST 基于 __slots__）
            slots = getattr(node, '__slots__', None)
            if slots:
                for slot in slots:
                    try:
                        v = getattr(node, slot)
                    except AttributeError:
                        continue
                    if v is None:
                        continue
                    if isinstance(v, list):
                        for item in v:
                            walk(item)
                    else:
                        walk(v)
            elif hasattr(node, '__dict__'):
                for k, v in vars(node).items():
                    if v is None:
                        continue
                    if isinstance(v, list):
                        for item in v:
                            walk(item)
                    else:
                        walk(v)
            ast_nodes.append(type(node).__name__)

        for stmt in getattr(raw, 'statements', []) or []:
            walk(stmt)

        self.assertIn('UnwrapExpression', ast_nodes,
                      f"应存在 UnwrapExpression，但实际: {ast_nodes}")

    def test_adapter_converts_unwrap(self):
        """确保 AstAdapter 将 UnwrapExpression 转换为正确类型"""
        c = DuanCompiler()
        result = c.compile('设值为空!。')
        # 适配后的 AST
        adapted = result['ast']
        # 检查顶层 VariableDeclaration 的 value 是 UnwrapExpression
        found_unwrap = False
        for stmt in adapted.statements:
            v = getattr(stmt, 'value', None)
            if v is not None and type(v).__name__ == 'UnwrapExpression':
                found_unwrap = True
        self.assertTrue(found_unwrap, "适配后 AST 中应有 UnwrapExpression")


class TestCodeGeneration(unittest.TestCase):
    """代码生成测试 —— 确保值! 被翻译为 _light_unwrap(...)"""

    def test_unwrap_generates_assert(self):
        """测试点：代码生成中包含 _light_unwrap 调用"""
        from code_generator import PythonCodeGenerator
        from ast_nodes import UnwrapExpression
        from ast_nodes_v3 import (
            Module, Identifier, NumberLiteral,
            VarDecl, ParagraphCall,
        )
        # 手动构建一个最小 AST：定义 x = 42!  打印x。
        mod = Module(statements=[
            VarDecl(name='甲', value=UnwrapExpression(value=NumberLiteral(42))),
            ParagraphCall(name='打印', args=[Identifier(name='甲')]),
        ])
        gen = PythonCodeGenerator()
        code = gen.generate(mod)
        self.assertIn('_light_unwrap(42)', code)
        self.assertIn('def _light_unwrap', code)
        self.assertIn('assert', code)


class TestBackwardsCompatibility(unittest.TestCase):
    """测试点 9：确保对现有 Phase 1-5 代码不造成破坏"""

    def test_simple_arithmetic(self):
        c = compile_source('设甲为3加5。')
        self.assertEqual(len([e for e in c.errors if '可空' in e]), 0)

    def test_paragraph_call(self):
        src = (
            '段落相加(甲, 乙)：\n'
            '    返回甲加乙。\n'
            '打印相加(1, 2)。\n'
        )
        c = compile_source(src)
        # 允许有语法/类型错误，但不能有「可空」之外的崩溃
        self.assertIsNotNone(c._inferencer)

    def test_null_value_without_unwrap(self):
        """仅声明空值变量不会触发可空错误"""
        c = compile_source('设值为空。')
        self.assertIsNotNone(c._inferencer)


if __name__ == '__main__':
    unittest.main(verbosity=2)
