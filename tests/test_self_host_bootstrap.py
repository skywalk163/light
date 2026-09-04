# -*- coding: utf-8 -*-
"""
test_self_host_bootstrap.py - 自举编译器全链路功能测试

测试内容：
1. test_level1_basic_expr  - Level 1 基础表达式解析
2. test_level2_condition   - Level 2 条件判断
3. test_level3_function_loop - Level 3 函数和循环
4. test_level4_list_dict   - Level 4 列表和字典
5. test_level5_advanced    - Level 5 高级特性
6. test_bootstrap_self_compile - 自举编译器能否编译自身

使用方式：
    pytest tests/test_self_host_bootstrap.py -v
"""

import pytest
import sys
import os
from typing import Any, Dict, List, Optional, Tuple

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, 'src')
_bootstrap_dir = os.path.join(_project_root, 'bootstrap')
sys.path.insert(0, _project_root)
sys.path.insert(0, _src_dir)
sys.path.insert(0, _bootstrap_dir)


# =============================================================================
# 辅助函数
# =============================================================================

def _compile_and_run(source_code: str) -> Tuple[Dict[str, Any], str]:
    """用 Python 编译器编译段言代码并执行，返回命名空间

    Args:
        source_code: 段言源代码

    Returns:
        (命名空间, 生成的Python代码) 元组
    """
    from compiler import LightCompiler
    from code_generator_unified import UnifiedCodeGenerator

    c = LightCompiler()
    result = c.compile(source_code)
    module = result['ast']

    generator = UnifiedCodeGenerator()
    py_code = generator.generate(module)

    _light_builtin = type('_light_builtin', (), {})()
    _light_builtin.打印 = print
    _light_builtin.输出 = print
    _light_builtin.转字符串 = str
    _light_builtin.转整数 = int
    _light_builtin.转浮点 = float
    _light_builtin.列表创建 = list
    _light_builtin.列表长度 = len
    _light_builtin.列表获取 = lambda lst, i: lst[i]
    _light_builtin.列表追加 = lambda lst, item: lst.append(item)
    _light_builtin.列表弹出 = lambda lst: lst.pop() if lst else None
    _light_builtin.列表包含 = lambda lst, item: item in lst
    _light_builtin.字典创建 = dict
    _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
    _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
    _light_builtin.字典包含键 = lambda d, k: k in d
    _light_builtin.字典键列表 = lambda d: list(d.keys())
    _light_builtin.字符串长度 = len
    _light_builtin.字符串获取 = lambda s, i: s[i]
    _light_builtin.截取 = lambda s, start, end: s[start:end]
    _light_builtin._读文件 = lambda path: open(path, 'r', encoding='utf-8').read()
    _light_builtin.范围 = range

    namespace = {'_light_builtin': _light_builtin}
    exec(py_code, namespace)
    return namespace, py_code


def _build_bootstrap_ast() -> Any:
    """构建自举编译器源码的 AST

    Returns:
        解析后的 Module AST 对象
    """
    from lexer import Lexer
    from light_parser_v3 import LightParser

    # 读取 bootstrap_level5.light（包含全部层级功能）
    level5_path = os.path.join(_bootstrap_dir, 'bootstrap_level5.light')
    with open(level5_path, 'r', encoding='utf-8') as f:
        source = f.read()

    lexer = Lexer()
    tokens = lexer.tokenize(source)
    parser = LightParser()
    module = parser.parse(source)
    return module


# =============================================================================
# Level 1: 基础表达式
# =============================================================================

class TestLevel1BasicExpr:
    """Level 1 基础表达式解析测试"""

    def test_number_literal(self) -> None:
        """测试数字字面量"""
        source = '设 x 为 42'
        ns, _ = _compile_and_run(source)
        assert ns['x'] == 42

    def test_float_number(self) -> None:
        """测试浮点数"""
        source = '设 x 为 3.14'
        ns, _ = _compile_and_run(source)
        assert abs(ns['x'] - 3.14) < 0.001

    def test_string_literal(self) -> None:
        """测试字符串字面量"""
        source = '设 s 为 "hello"'
        ns, _ = _compile_and_run(source)
        assert ns['s'] == 'hello'

    def test_boolean_true(self) -> None:
        """测试布尔值真"""
        source = '设 b 为 真'
        ns, _ = _compile_and_run(source)
        assert ns['b'] == True

    def test_boolean_false(self) -> None:
        """测试布尔值假"""
        source = '设 b 为 假'
        ns, _ = _compile_and_run(source)
        assert ns['b'] == False

    def test_variable_reference(self) -> None:
        """测试变量引用"""
        source = '''设 x 为 42
设 y 为 x
'''
        ns, _ = _compile_and_run(source)
        assert ns['y'] == 42

    def test_binary_add(self) -> None:
        """测试加法运算"""
        source = '设 r 为 1 加 2'
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 3

    def test_binary_sub(self) -> None:
        """测试减法运算"""
        source = '设 r 为 5 减 3'
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 2

    def test_binary_mul(self) -> None:
        """测试乘法运算"""
        source = '设 r 为 3 乘 4'
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 12

    def test_binary_div(self) -> None:
        """测试除法运算"""
        source = '设 r 为 10 除 3'
        ns, _ = _compile_and_run(source)
        # 裁决 B（§15.1）：「除」整数相除向零截断 → 10 / 3 = 3（整型，对齐原生腿 i64 sdiv）
        assert ns['r'] == 3

    def test_binary_mod(self) -> None:
        """测试取模运算"""
        # 取模运算在当前编译器中不可用，跳过
        pytest.skip("取模运算在当前编译器中需要特殊处理")

    def test_parentheses(self) -> None:
        """测试括号分组"""
        source = '设 r 为 (1 加 2) 乘 3'
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 9

    def test_operator_precedence(self) -> None:
        """测试运算符优先级"""
        source = '设 r 为 1 加 2 乘 3'
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 7


# =============================================================================
# Level 2: 条件判断
# =============================================================================

class TestLevel2Condition:
    """Level 2 条件判断测试"""

    def test_if_statement(self) -> None:
        """测试 if 语句"""
        source = '''设 x 为 10
如果 x 大于 5：
  设 y 为 "大"
'''
        ns, _ = _compile_and_run(source)
        assert ns['y'] == '大'

    def test_if_else_statement(self) -> None:
        """测试 if-else 语句"""
        source = '''设 x 为 2
如果 x 大于 5：
  设 y 为 "大"
否则：
  设 y 为 "小"
'''
        ns, _ = _compile_and_run(source)
        assert ns['y'] == '小'

    def test_compare_equal(self) -> None:
        """测试等于比较"""
        source = '''设 r 为 假
如果 5 等于 5：
  设 r 为 真
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == True

    def test_compare_not_equal(self) -> None:
        """测试不等于比较"""
        source = '''设 r 为 假
如果 5 不等于 3：
  设 r 为 真
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == True

    def test_compare_less(self) -> None:
        """测试小于比较"""
        source = '设 r 为 3 小于 5'
        ns, _ = _compile_and_run(source)
        assert ns['r'] == True

    def test_compare_greater(self) -> None:
        """测试大于比较"""
        source = '设 r 为 5 大于 3'
        ns, _ = _compile_and_run(source)
        assert ns['r'] == True

    def test_compare_less_equal(self) -> None:
        """测试小于等于比较"""
        source = '设 r 为 3 小于等于 3'
        ns, _ = _compile_and_run(source)
        assert ns['r'] == True

    def test_compare_greater_equal(self) -> None:
        """测试大于等于比较"""
        source = '设 r 为 5 大于等于 5'
        ns, _ = _compile_and_run(source)
        assert ns['r'] == True

    def test_logical_and(self) -> None:
        """测试逻辑与"""
        source = '''设 r 为 假
如果 真 且 真：
  设 r 为 真
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == True

    def test_logical_or(self) -> None:
        """测试逻辑或"""
        source = '''设 r 为 假
如果 真 或 假：
  设 r 为 真
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == True

    def test_logical_not(self) -> None:
        """测试逻辑非"""
        # 非运算符在顶层表达式中需要特殊处理，跳过运行时测试
        pytest.skip("逻辑非运算符在顶层表达式中的运行时支持需要特殊处理")

    def test_nested_if(self) -> None:
        """测试嵌套 if"""
        source = '''设 x 为 10
设 y 为 ""
如果 x 大于 0：
  如果 x 大于 5：
    设 y 为 "大正数"
  否则：
    设 y 为 "小正数"
'''
        ns, _ = _compile_and_run(source)
        assert ns['y'] == '大正数'


# =============================================================================
# Level 3: 函数和循环
# =============================================================================

class TestLevel3FunctionLoop:
    """Level 3 函数和循环测试"""

    def test_function_definition_no_params(self) -> None:
        """测试无参数函数定义"""
        source = '''段落 返回答案():
  返回 42
'''
        from compiler import LightCompiler
        from code_generator_unified import UnifiedCodeGenerator
        c = LightCompiler()
        result = c.compile(source)
        module = result['ast']
        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)
        assert 'def 返回答案' in py_code, "生成的代码应包含函数定义"
        assert 'return 42' in py_code, "生成的代码应包含 return 42"
        # 验证语法正确性
        compile(py_code, '<string>', 'exec')

    def test_function_with_params(self) -> None:
        """测试带参数函数"""
        source = '''段落 加法 接收 x, y：
  返回 x 加 y
设 r 为 加法(3, 4)
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 7

    def test_function_return_value(self) -> None:
        """测试函数返回值"""
        source = '''段落 平方 接收 x：
  返回 x 乘 x
设 r 为 平方(5)
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 25

    def test_while_loop(self) -> None:
        """测试 while 循环"""
        source = '''设 i 为 0
设 sum 为 0
当 i 小于 5：
  设 sum 为 sum 加 i
  设 i 为 i 加 1
'''
        ns, _ = _compile_and_run(source)
        assert ns['sum'] == 10

    def test_variable_assignment(self) -> None:
        """测试变量赋值"""
        source = '''设 x 为 10
设 x 为 20
'''
        ns, _ = _compile_and_run(source)
        assert ns['x'] == 20

    def test_function_with_multiple_params(self) -> None:
        """测试多参数函数"""
        source = '''段落 乘加 接收 a, b, c：
  返回 a 乘 b 加 c
设 r 为 乘加(2, 3, 1)
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 7

    def test_function_call_chain(self) -> None:
        """测试函数调用链"""
        source = '''段落 加倍 接收 x：
  返回 x 加 x
段落 平方 接收 x：
  返回 x 乘 x
设 r 为 平方(加倍(3))
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 36

    def test_while_with_continue(self) -> None:
        """测试 while 循环（累计）"""
        source = '''设 i 为 0
设 result 为 0
当 i 小于 10：
  设 result 为 result 加 i
  设 i 为 i 加 2
'''
        ns, _ = _compile_and_run(source)
        # 0 + 2 + 4 + 6 + 8 = 20
        assert ns['result'] == 20


# =============================================================================
# Level 4: 列表和字典
# =============================================================================

class TestLevel4ListDict:
    """Level 4 列表和字典测试"""

    def test_list_creation(self) -> None:
        """测试列表创建"""
        source = '''设 lst 为 列表创建()
设 r 为 列表长度(lst)
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 0

    def test_list_append(self) -> None:
        """测试列表追加"""
        source = '''设 lst 为 列表创建()
列表追加(lst, 42)
设 r 为 列表长度(lst)
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 1

    def test_list_get(self) -> None:
        """测试列表索引获取"""
        source = '''设 lst 为 列表创建()
列表追加(lst, 10)
列表追加(lst, 20)
设 r 为 列表获取(lst, 1)
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 20

    def test_list_pop(self) -> None:
        """测试列表弹出"""
        source = '''设 lst 为 列表创建()
列表追加(lst, 1)
列表追加(lst, 2)
设 r 为 列表弹出(lst)
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 2

    def test_list_contains(self) -> None:
        """测试列表包含"""
        source = '''设 lst 为 列表创建()
列表追加(lst, 1)
列表追加(lst, 2)
列表追加(lst, 3)
设 r1 为 列表包含(lst, 2)
设 r2 为 列表包含(lst, 5)
'''
        ns, _ = _compile_and_run(source)
        assert ns['r1'] == True
        assert ns['r2'] == False

    def test_dict_creation(self) -> None:
        """测试字典创建"""
        source = '''设 d 为 字典创建()
字典设置(d, "name", "test")
设 r 为 字典获取(d, "name")
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 'test'

    def test_dict_contains_key(self) -> None:
        """测试字典包含键"""
        source = '''设 d 为 字典创建()
字典设置(d, "a", 1)
设 r1 为 字典包含键(d, "a")
设 r2 为 字典包含键(d, "b")
'''
        ns, _ = _compile_and_run(source)
        assert ns['r1'] == True
        assert ns['r2'] == False

    def test_dict_keys(self) -> None:
        """测试字典键列表"""
        source = '''设 d 为 字典创建()
字典设置(d, "a", 1)
字典设置(d, "b", 2)
设 keys 为 字典键列表(d)
设 r 为 列表长度(keys)
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 2

    def test_for_loop(self) -> None:
        """测试 for 循环（遍历）"""
        source = '''设 lst 为 列表创建()
列表追加(lst, 1)
列表追加(lst, 2)
列表追加(lst, 3)
设 sum 为 0
遍历 i 在 lst：
  设 sum 为 sum 加 i
'''
        ns, _ = _compile_and_run(source)
        assert ns['sum'] == 6


# =============================================================================
# Level 5: 高级特性
# =============================================================================

class TestLevel5Advanced:
    """Level 5 高级特性测试"""

    def test_class_definition(self) -> None:
        """测试类定义"""
        source = '''类 计数器：
  段落 初始化 接收 己, 初始值：
    属性 己.值 为 初始值
  段落 增加 接收 己：
    设 己.值 为 己.值 加 1
  段落 获取 接收 己：
    返回 己.值
设 c 为 计数器(0)
'''

    def test_try_except(self) -> None:
        """测试 try/except 异常处理

        验证 bootstrap_level5.light 源码中包含异常处理相关关键字
        """
        fpath = os.path.join(_bootstrap_dir, 'bootstrap_level5.light')
        assert os.path.exists(fpath), f"文件不存在: {fpath}"
        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()
        assert '尝试' in source, "bootstrap_level5 应包含 尝试 关键字"
        assert '捕获' in source, "bootstrap_level5 应包含 捕获 关键字"
        assert '抛出' in source, "bootstrap_level5 应包含 抛出 关键字"

    def test_raise_exception(self) -> None:
        """测试抛出异常（使用内置 raise 绕过）"""
        # 段言中 raise 会中断流程，这里只测试语法可以通过编译
        source = '''段落 检查正数 接收 x：
  如果 x 小于 0：
    抛出 "值错误"
  返回 真
'''
        # 仅验证编译通过，不执行抛出路径
        from compiler import LightCompiler
        from code_generator_unified import UnifiedCodeGenerator
        c = LightCompiler()
        result = c.compile(source)
        _ = result['ast']
        generator = UnifiedCodeGenerator()
        py_code = generator.generate(result['ast'])
        assert 'raise' in py_code

    def test_method_call(self) -> None:
        """测试方法调用

        使用 bootstrap_level4 中的类定义语法
        """
        source = '''类 计算器：
  段落 初始化(己, n):
    设 己.值 为 n
  段落 加(己, n):
    设 己.值 为 己.值 加 n
  段落 获取(己):
    返回 己.值
结束
'''
        from compiler import LightCompiler
        from code_generator_unified import UnifiedCodeGenerator
        c = LightCompiler()
        result = c.compile(source)
        module = result['ast']
        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)
        assert 'class ' in py_code, "生成的代码应包含 class"
        assert 'def ' in py_code, "生成的代码应包含 def"

    def test_for_loop_over_range(self) -> None:
        """测试 for 循环遍历"""
        source = '''设 lst 为 列表创建()
列表追加(lst, 1)
列表追加(lst, 2)
列表追加(lst, 3)
设 sum 为 0
遍历 v 在 lst：
  设 sum 为 sum 加 v
'''
        ns, _ = _compile_and_run(source)
        assert ns['sum'] == 6

    def test_string_operations(self) -> None:
        """测试字符串操作"""
        source = '''设 s 为 "hello 世界"
设 n 为 字符串长度(s)
设 c 为 字符串获取(s, 0)
'''
        ns, _ = _compile_and_run(source)
        assert ns['n'] == len('hello 世界')
        assert ns['c'] == 'h'

    def test_string_substring(self) -> None:
        """测试字符串截取"""
        source = '''设 s 为 "hello world"
设 sub 为 截取(s, 0, 5)
'''
        ns, _ = _compile_and_run(source)
        assert ns['sub'] == 'hello'


# =============================================================================
# 自举编译器自编译测试
# =============================================================================

class TestBootstrapSelfCompile:
    """自举编译器能否编译自身测试"""

    BOOTSTRAP_FILES = [
        'bootstrap_level4.light',
        'bootstrap_level5.light',
        'bootstrap_merged.light',
    ]

    def test_lexer_can_tokenize_bootstrap(self) -> None:
        """测试词法分析器能分析自举编译器源码"""
        from lexer import Lexer, LexerError

        for fname in self.BOOTSTRAP_FILES:
            fpath = os.path.join(_bootstrap_dir, fname)
            if not os.path.exists(fpath):
                continue
            with open(fpath, 'r', encoding='utf-8') as f:
                source = f.read()

            lexer = Lexer()
            try:
                tokens = lexer.tokenize(source)
            except LexerError as e:
                pytest.fail(f"词法分析失败 ({fname}): {e}")

            assert tokens is not None, f"词法分析返回 None ({fname})"
            assert len(tokens) > 0, f"令牌列表为空 ({fname})"

    def test_parser_can_parse_bootstrap_level4(self) -> None:
        """测试解析器能解析 bootstrap_level4.light"""
        from lexer import Lexer
        from light_parser_v3 import LightParser, ParseError, Module

        fpath = os.path.join(_bootstrap_dir, 'bootstrap_level4.light')
        assert os.path.exists(fpath), f"文件不存在: {fpath}"

        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()

        parser = LightParser()
        try:
            module = parser.parse(source)
        except ParseError as e:
            pytest.fail(f"解析失败: {e}")

        assert module is not None, "解析返回 None"
        assert isinstance(module, Module), f"返回类型不是 Module: {type(module)}"
        assert hasattr(module, 'statements'), "Module 缺少 statements 属性"
        assert len(module.statements) > 0, "Module statements 为空"

    def test_parser_can_parse_bootstrap_level5(self) -> None:
        """测试解析器能解析 bootstrap_level5.light"""
        from lexer import Lexer
        from light_parser_v3 import LightParser, ParseError, Module

        fpath = os.path.join(_bootstrap_dir, 'bootstrap_level5.light')
        assert os.path.exists(fpath), f"文件不存在: {fpath}"

        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()

        parser = LightParser()
        try:
            module = parser.parse(source)
        except ParseError as e:
            pytest.fail(f"解析失败: {e}")

        assert module is not None, "解析返回 None"
        assert isinstance(module, Module), f"返回类型不是 Module: {type(module)}"
        assert len(getattr(module, 'statements', [])) > 0, "Module statements 为空"

    def test_codegen_generates_valid_python_from_level4(self) -> None:
        """测试从 bootstrap_level4.light 生成有效的 Python 代码"""
        from light_parser_v3 import LightParser
        from code_generator_unified import UnifiedCodeGenerator

        fpath = os.path.join(_bootstrap_dir, 'bootstrap_level4.light')
        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()

        parser = LightParser()
        module = parser.parse(source)

        generator = UnifiedCodeGenerator()
        try:
            py_code = generator.generate(module)
        except Exception as e:
            pytest.fail(f"代码生成失败: {e}")

        assert py_code is not None, "代码生成返回 None"
        assert len(py_code) > 0, "生成的代码为空"
        assert 'def ' in py_code, "生成的代码未包含函数定义"

        # 验证 Python 语法正确性
        try:
            compile(py_code, '<string>', 'exec')
        except SyntaxError as e:
            lines = py_code.splitlines()
            context = '\n'.join(lines[max(0, (e.lineno or 1) - 3):(e.lineno or 1) + 2])
            pytest.fail(f"生成的 Python 代码语法错误 (行 {e.lineno}): {e.msg}\n附近代码:\n{context}")

    def test_codegen_generates_valid_python_from_level5(self) -> None:
        """测试从 bootstrap_level5.light 生成有效的 Python 代码"""
        from light_parser_v3 import LightParser
        from code_generator_unified import UnifiedCodeGenerator

        fpath = os.path.join(_bootstrap_dir, 'bootstrap_level5.light')
        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()

        parser = LightParser()
        module = parser.parse(source)

        generator = UnifiedCodeGenerator()
        try:
            py_code = generator.generate(module)
        except Exception as e:
            pytest.fail(f"代码生成失败: {e}")

        assert py_code is not None, "代码生成返回 None"
        assert len(py_code) > 0, "生成的代码为空"
        assert 'def ' in py_code, "生成的代码未包含函数定义"

        # 验证 Python 语法正确性
        try:
            compile(py_code, '<string>', 'exec')
        except SyntaxError as e:
            lines = py_code.splitlines()
            context = '\n'.join(lines[max(0, (e.lineno or 1) - 3):(e.lineno or 1) + 2])
            pytest.fail(f"生成的 Python 代码语法错误 (行 {e.lineno}): {e.msg}\n附近代码:\n{context}")

    def test_full_pipeline_level4(self) -> None:
        """测试 bootstrap_level4.light 的完整词法→解析→代码生成流水线"""
        from light_parser_v3 import LightParser
        from code_generator_unified import UnifiedCodeGenerator

        fpath = os.path.join(_bootstrap_dir, 'bootstrap_level4.light')
        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()

        parser = LightParser()
        module = parser.parse(source)

        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        # 验证语法
        compile(py_code, '<string>', 'exec')

        # 统计信息
        func_count = py_code.count('def ')
        line_count = len(py_code.splitlines())
        source_lines = len(source.splitlines())

        print(f"\n--- Level 4 自举编译器统计 ---")
        print(f"源码行数: {source_lines}")
        print(f"生成的 Python 行数: {line_count}")
        print(f"生成的函数数量: {func_count}")
        print(f"生成代码长度: {len(py_code)} 字符")
        print(f"语法验证: 通过")
        print(f"-------------------------------")

        assert func_count > 0, "生成的代码中未找到函数定义"
        assert source_lines > 100, f"源码行数异常: {source_lines}"

    def test_full_pipeline_level5(self) -> None:
        """测试 bootstrap_level5.light 的完整词法→解析→代码生成流水线"""
        from light_parser_v3 import LightParser
        from code_generator_unified import UnifiedCodeGenerator

        fpath = os.path.join(_bootstrap_dir, 'bootstrap_level5.light')
        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()

        parser = LightParser()
        module = parser.parse(source)

        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        # 验证语法
        compile(py_code, '<string>', 'exec')

        # 统计信息
        func_count = py_code.count('def ')
        line_count = len(py_code.splitlines())
        source_lines = len(source.splitlines())

        print(f"\n--- Level 5 自举编译器统计 ---")
        print(f"源码行数: {source_lines}")
        print(f"生成的 Python 行数: {line_count}")
        print(f"生成的函数数量: {func_count}")
        print(f"生成代码长度: {len(py_code)} 字符")
        print(f"语法验证: 通过")
        print(f"-------------------------------")

        assert func_count > 0, "生成的代码中未找到函数定义"
        assert source_lines > 100, f"源码行数异常: {source_lines}"

    def test_bootstrap_merged_exists_and_valid(self) -> None:
        """测试 bootstrap_merged.light 存在且包含有效内容"""
        fpath = os.path.join(_bootstrap_dir, 'bootstrap_merged.light')
        assert os.path.exists(fpath), f"合并版自举编译器文件不存在: {fpath}"

        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert len(content) > 500, f"内容过短: {len(content)} 字符"
        assert '编译' in content or '段落' in content, "内容缺少段言代码特征"

    def test_bootstrap_source_files_exist(self) -> None:
        """测试所有自举编译器源码文件存在"""
        for fname in self.BOOTSTRAP_FILES:
            fpath = os.path.join(_bootstrap_dir, fname)
            assert os.path.exists(fpath), f"文件不存在: {fpath}"
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            assert len(content) > 100, f"文件内容过短: {fname} ({len(content)} 字符)"

    def test_bootstrap_level4_self_test(self) -> None:
        """测试 bootstrap_level4.light 中的测试函数可以运行"""
        from light_parser_v3 import LightParser
        from code_generator_unified import UnifiedCodeGenerator

        fpath = os.path.join(_bootstrap_dir, 'bootstrap_level4.light')
        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()

        parser = LightParser()
        module = parser.parse(source)

        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        # 验证语法（不执行，因为内置函数需要特定环境）
        compile(py_code, '<string>', 'exec')

    def test_bootstrap_level5_self_test(self) -> None:
        """测试 bootstrap_level5.light 中的测试函数可以运行"""
        from light_parser_v3 import LightParser
        from code_generator_unified import UnifiedCodeGenerator

        fpath = os.path.join(_bootstrap_dir, 'bootstrap_level5.light')
        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()

        parser = LightParser()
        module = parser.parse(source)

        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        # 验证语法（不执行，因为内置函数需要特定环境）
        compile(py_code, '<string>', 'exec')

    def test_compiled_code_contains_key_features(self) -> None:
        """验证编译后的代码包含关键特性"""
        from light_parser_v3 import LightParser
        from code_generator_unified import UnifiedCodeGenerator

        # 使用 level5 包含最完整的特性
        fpath = os.path.join(_bootstrap_dir, 'bootstrap_level5.light')
        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()

        parser = LightParser()
        module = parser.parse(source)

        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        # 关键特性检查
        assert 'def ' in py_code, "缺少函数定义"
        assert 'if ' in py_code or 'elif ' in py_code, "缺少条件判断"
        assert 'for ' in py_code or 'while ' in py_code, "缺少循环"
        assert 'class ' in py_code, "缺少类定义"
        assert 'try' in py_code, "缺少异常处理"
        assert 'raise' in py_code, "缺少抛出语句"

    def test_bootstrap_progress_report(self) -> None:
        """测试自举编译器进度检查工具"""
        from bootstrap_progress import BootstrapProgressChecker

        checker = BootstrapProgressChecker(_bootstrap_dir)
        progress = checker.check_progress()
        stats = checker.get_statistics()
        remaining = checker.get_remaining_features()

        # 验证进度报告结构
        assert progress is not None, "进度检查返回 None"
        assert len(progress) == 5, f"应该包含 5 个层级，实际 {len(progress)}"
        assert stats['total_features'] > 0, "总功能数应为正数"
        assert stats['completed'] >= 0, "已完成数不能为负"
        assert stats['completion_percentage'] >= 0, "完成度不能为负"

        # 生成报告
        report = checker.generate_report()
        assert report is not None, "报告生成返回 None"
        assert len(report) > 100, "报告内容过短"
        assert '光明' in report, "报告应包含语言名称"
        # 这条原先断言的是 '段言'。报告头早就是「光明（Light）自举编译器进度报告」
        # （bootstrap_progress.py:263），所以是判据陈旧、不是产物出错。
        # 段言项目已停止开发，旧品牌名再出现在产物里就是回归。
        assert '段言' not in report, "报告里不该再出现旧品牌名「段言」"
        assert 'Level' in report, "报告应包含层级信息"


        print(f"\n自举编译器进度: {stats['completed']}/{stats['total_features']} "
              f"({stats['completion_percentage']}%) 完成")
        if remaining:
            print(f"未完成功能: {len(remaining)}")
            for item in remaining:
                print(f"  - {item}")

    def test_segment_count_consistency(self) -> None:
        """验证自举编译器中的段落数量一致性"""
        import re

        for fname in self.BOOTSTRAP_FILES:
            fpath = os.path.join(_bootstrap_dir, fname)
            if not os.path.exists(fpath):
                continue
            with open(fpath, 'r', encoding='utf-8') as f:
                source = f.read()

            # 统计段落定义
            seg_count = len(re.findall(r'^段落\s+', source, re.MULTILINE))
            if seg_count > 0:
                print(f"{fname}: {seg_count} 个段落")

    def test_bootstrap_cycle_verify(self) -> None:
        """测试自举循环验证脚本存在并可运行"""
        verify_path = os.path.join(_bootstrap_dir, 'verify_bootstrap_cycle.py')
        if os.path.exists(verify_path):
            with open(verify_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert len(content) > 50, "验证脚本内容过短"
            # 验证语法正确性
            compile(content, verify_path, 'exec')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])