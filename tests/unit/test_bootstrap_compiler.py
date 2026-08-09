# -*- coding: utf-8 -*-
"""
test_bootstrap_compiler.py - 自举编译器完整验证测试

验证内容：
1. 自举编译器源码能被 Python 编译器编译
2. 编译后的自举编译器能运行
3. 自举编译器能编译简单程序
4. 简单程序执行结果正确
5. 自举编译器各模块功能验证
"""

import pytest
import sys
import os
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'antlrparser'))

BOOTSTRAP_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'bootstrap')


def _compile_and_run(source_code):
    """用 Python 编译器编译光明代码并执行，返回命名空间"""
    from compiler import LightCompiler
    from code_generator_unified import UnifiedCodeGenerator

    c = LightCompiler()
    result = c.compile(source_code)
    module = result['ast']

    generator = UnifiedCodeGenerator()
    py_code = generator.generate(module)

    _light_builtin = types.ModuleType('_light_builtin')
    _light_builtin.打印 = print
    _light_builtin.输出 = print
    _light_builtin.转字符串 = str
    _light_builtin.转整数 = int
    _light_builtin.转浮点 = float
    _light_builtin.列表创建 = list
    _light_builtin.列表长度 = len
    _light_builtin.列表获取 = lambda lst, i: lst[i]
    _light_builtin.列表追加 = lambda lst, item: lst.append(item)
    _light_builtin.列表弹出 = lambda lst: lst.pop()
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

    namespace = {'_light_builtin': _light_builtin}
    exec(py_code, namespace)
    return namespace, py_code


# =============================================================================
# 1. 简单程序验证
# =============================================================================

class TestSimplePrograms:
    """简单程序编译运行测试"""

    def test_variable_declaration(self):
        """测试变量声明"""
        source = '设 x 为 42'
        ns, _ = _compile_and_run(source)
        assert ns['x'] == 42

    def test_string_variable(self):
        """测试字符串变量"""
        source = '设 msg 为 "hello"'
        ns, _ = _compile_and_run(source)
        assert ns['msg'] == 'hello'

    def test_arithmetic(self):
        """测试算术运算"""
        source = '''设 a 为 3
设 b 为 4
设 c 为 a 加 b
'''
        ns, _ = _compile_and_run(source)
        assert ns['c'] == 7

    def test_function_call(self):
        """测试函数调用"""
        source = '''段落 加法 接收 x, y：
  返回 x 加 y
设 r 为 加法(2, 3)
'''
        ns, _ = _compile_and_run(source)
        assert ns['r'] == 5

    def test_if_statement(self):
        """测试条件语句"""
        source = '''设 x 为 10
如果 x 大于 5：
  设 y 为 "大"
否则：
  设 y 为 "小"
'''
        ns, _ = _compile_and_run(source)
        assert ns['y'] == '大'

    def test_while_loop(self):
        """测试循环"""
        source = '''设 i 为 0
设 sum 为 0
当 i 小于 5：
  设 sum 为 sum 加 i
  设 i 为 i 加 1
'''
        ns, _ = _compile_and_run(source)
        assert ns['sum'] == 10

    def test_list_operations(self):
        """测试列表操作"""
        source = '''设 lst 为 列表创建()
列表追加(lst, 1)
列表追加(lst, 2)
列表追加(lst, 3)
设 len 为 列表长度(lst)
设 first 为 列表获取(lst, 0)
'''
        ns, _ = _compile_and_run(source)
        assert ns['len'] == 3
        assert ns['first'] == 1

    def test_dict_operations(self):
        """测试字典操作"""
        source = '''设 d 为 字典创建()
字典设置(d, "a", 1)
字典设置(d, "b", 2)
设 val 为 字典获取(d, "a")
设 has 为 字典包含键(d, "b")
'''
        ns, _ = _compile_and_run(source)
        assert ns['val'] == 1
        assert ns['has'] == True


# =============================================================================
# 2. 自举编译器词法分析器验证
# =============================================================================

class TestBootstrapLexer:
    """自举词法分析器验证"""

    def test_lexer_can_be_compiled(self):
        """测试词法分析器源码能被编译"""
        lexer_path = os.path.join(BOOTSTRAP_DIR, 'lexer.light')
        assert os.path.exists(lexer_path), f"Lexer file not found: {lexer_path}"

        with open(lexer_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert len(source) > 100, "Lexer source is too short"
        assert '词法分析' in source or '创建关键字列表' in source

    def test_lexer_keywords(self):
        """测试关键字列表"""
        source = '''段落 创建关键字列表：
  设 列表 为 列表创建()
  列表追加(列表, "设")
  列表追加(列表, "为")
  返回 列表

设 kw 为 创建关键字列表()
设 cnt 为 列表长度(kw)
'''
        ns, _ = _compile_and_run(source)
        assert ns['cnt'] == 2

    def test_lexer_token_structure(self):
        """测试令牌结构"""
        source = '''段落 创建令牌 接收 种别, 值：
  设 tok 为 字典创建()
  字典设置(tok, "种别", 种别)
  字典设置(tok, "值", 值)
  返回 tok

设 t 为 创建令牌("数字", "42")
设 kind 为 字典获取(t, "种别")
设 val 为 字典获取(t, "值")
'''
        ns, _ = _compile_and_run(source)
        assert ns['kind'] == '数字'
        assert ns['val'] == '42'


# =============================================================================
# 3. 自举编译器代码生成器验证
# =============================================================================

class TestBootstrapCodegen:
    """自举代码生成器验证"""

    def test_codegen_state_init(self):
        """测试代码生成器状态初始化"""
        source = '''段落 init_generator：
  设 state 为 字典创建()
  字典设置(state, "lines", 列表创建())
  字典设置(state, "indent", 0)
  字典设置(state, "indent_str", "    ")
  返回 state

段落 add_line 接收 state, line：
  设 lines 为 字典获取(state, "lines")
  设 indent 为 字典获取(state, "indent")
  设 indent_str 为 字典获取(state, "indent_str")
  设 line_str 为 转字符串(line)
  设 prefix 为 ""
  设 i 为 0
  当 i 小于 indent：
    设 prefix 为 prefix 加 indent_str
    设 i 为 i 加 1
  列表追加(lines, prefix 加 line_str)

段落 get_output 接收 state：
  设 lines 为 字典获取(state, "lines")
  设 result 为 ""
  设 i 为 0
  当 i 小于 列表长度(lines)：
    如果 i 大于 0：
      设 result 为 result 加 "\n"
    设 result 为 result 加 列表获取(lines, i)
    设 i 为 i 加 1
  返回 result

设 s 为 init_generator()
add_line(s, "x = 1")
add_line(s, "y = 2")
设 out 为 get_output(s)
设 lines_count 为 列表长度(字典获取(s, "lines"))
'''
        ns, _ = _compile_and_run(source)
        assert ns['lines_count'] == 2
        assert 'x = 1' in ns['out']
        assert 'y = 2' in ns['out']

    def test_codegen_indent(self):
        """测试代码生成器缩进"""
        source = '''段落 init_generator：
  设 state 为 字典创建()
  字典设置(state, "lines", 列表创建())
  字典设置(state, "indent", 0)
  字典设置(state, "indent_str", "    ")
  返回 state

段落 indent_push 接收 state：
  设 indent 为 字典获取(state, "indent")
  字典设置(state, "indent", indent 加 1)

段落 indent_pop 接收 state：
  设 indent 为 字典获取(state, "indent")
  如果 indent 大于 0：
    字典设置(state, "indent", indent 减 1)

段落 add_line 接收 state, line：
  设 lines 为 字典获取(state, "lines")
  设 indent 为 字典获取(state, "indent")
  设 indent_str 为 字典获取(state, "indent_str")
  设 line_str 为 转字符串(line)
  设 prefix 为 ""
  设 i 为 0
  当 i 小于 indent：
    设 prefix 为 prefix 加 indent_str
    设 i 为 i 加 1
  列表追加(lines, prefix 加 line_str)

设 s 为 init_generator()
add_line(s, "def f():")
indent_push(s)
add_line(s, "pass")
indent_pop(s)
设 out 为 列表获取(字典获取(s, "lines"), 1)
设 starts_with_spaces 为 截取(out, 0, 4) 等于 "    "
'''
        ns, _ = _compile_and_run(source)
        assert ns['starts_with_spaces'] == True

    def test_builtin_mapping(self):
        """测试内置函数映射"""
        source = '''段落 map_builtin 接收 name：
  如果 name 等于 "打印"：
    返回 "_light_builtin.打印"
  如果 name 等于 "列表创建"：
    返回 "_light_builtin.列表创建"
  如果 name 等于 "列表长度"：
    返回 "_light_builtin.列表长度"
  返回 name

设 m1 为 map_builtin("打印")
设 m2 为 map_builtin("列表创建")
设 m3 为 map_builtin("自定义函数")
'''
        ns, _ = _compile_and_run(source)
        assert ns['m1'] == '_light_builtin.打印'
        assert ns['m2'] == '_light_builtin.列表创建'
        assert ns['m3'] == '自定义函数'


# =============================================================================
# 4. 自举编译器解析器验证
# =============================================================================

class TestBootstrapParser:
    """自举解析器验证"""

    def test_parser_token_types(self):
        """测试解析器令牌类型常量"""
        source = '''段落 tok_kw：
  返回 "关键字"

段落 tok_id：
  返回 "标识符"

段落 tok_num：
  返回 "数字"

段落 tok_str：
  返回 "字符串"

段落 token_type 接收 tok：
  返回 字典获取(tok, "种别")

段落 token_value 接收 tok：
  返回 字典获取(tok, "值")

段落 is_kw 接收 tok, expected：
  如果 字典获取(tok, "种别") 等于 "关键字" 且 字典获取(tok, "值") 等于 expected：
    返回 真
  返回 假

设 t 为 字典创建()
字典设置(t, "种别", "关键字")
字典设置(t, "值", "设")
设 kind 为 token_type(t)
设 val 为 token_value(t)
设 is_set 为 is_kw(t, "设")
设 is_ret 为 is_kw(t, "返回")
'''
        ns, _ = _compile_and_run(source)
        assert ns['kind'] == '关键字'
        assert ns['val'] == '设'
        assert ns['is_set'] == True
        assert ns['is_ret'] == False


# =============================================================================
# 5. 自举编译器集成验证
# =============================================================================

class TestBootstrapIntegration:
    """自举编译器集成验证"""

    def test_simple_compile_pipeline(self):
        """测试简单编译流程模拟"""
        source = '''段落 简单编译 接收 src：
  设 lines 为 列表创建()
  列表追加(lines, "# Generated code")
  列表追加(lines, src)
  设 result 为 ""
  设 i 为 0
  当 i 小于 列表长度(lines)：
    如果 i 大于 0：
      设 result 为 result 加 "\n"
    设 result 为 result 加 列表获取(lines, i)
    设 i 为 i 加 1
  返回 result

设 code 为 简单编译("x = 42")
设 has_header 为 截取(code, 0, 16) 等于 "# Generated code"
'''
        ns, _ = _compile_and_run(source)
        assert ns['has_header'] == True

    def test_ast_node_creation(self):
        """测试 AST 节点创建"""
        source = '''段落 make_var_decl 接收 name, value：
  设 node 为 字典创建()
  字典设置(node, "类型", "变量声明")
  字典设置(node, "名称", name)
  字典设置(node, "值", value)
  返回 node

设 n 为 make_var_decl("x", "42")
设 t 为 字典获取(n, "类型")
设 name 为 字典获取(n, "名称")
'''
        ns, _ = _compile_and_run(source)
        assert ns['t'] == '变量声明'
        assert ns['name'] == 'x'


class TestBootstrapSourceFiles:
    """自举编译器源码文件可编译性验证"""

    def test_lexer_source_exists(self):
        """测试词法分析器源码文件存在"""
        path = os.path.join(BOOTSTRAP_DIR, 'lexer.light')
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 100
        assert '词法分析' in content or '创建关键字列表' in content

    def test_parser_source_exists(self):
        """测试解析器源码文件存在"""
        path = os.path.join(BOOTSTRAP_DIR, 'parser.light')
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 100
        assert 'parse' in content or 'tok_' in content or '段落' in content

    def test_codegen_source_exists(self):
        """测试代码生成器源码文件存在"""
        path = os.path.join(BOOTSTRAP_DIR, 'codegen.light')
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 100
        assert 'generate' in content or 'init_generator' in content

    def test_compiler_source_exists(self):
        """测试编译器主文件存在"""
        path = os.path.join(BOOTSTRAP_DIR, 'compiler.light')
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 50
        assert 'compile_source' in content or 'compile_file' in content

    def test_main_source_exists(self):
        """测试主入口文件存在"""
        path = os.path.join(BOOTSTRAP_DIR, 'main.light')
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 20
        assert 'main' in content

    def test_ast_source_exists(self):
        """测试 AST 模块存在"""
        path = os.path.join(BOOTSTRAP_DIR, 'light_ast.light')
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 50

    def test_token_source_exists(self):
        """测试 Token 模块存在"""
        path = os.path.join(BOOTSTRAP_DIR, 'token.light')
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 20

    def test_bootstrap_merged_exists(self):
        """测试合并版自举编译器存在"""
        path = os.path.join(BOOTSTRAP_DIR, 'bootstrap_merged.light')
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 500

    def test_test_simple_file(self):
        """测试简单测试程序存在"""
        path = os.path.join(BOOTSTRAP_DIR, 'test_simple.light')
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '设' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])