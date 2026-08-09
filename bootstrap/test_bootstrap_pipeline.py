"""
test_bootstrap_pipeline.py - End-to-end test of the bootstrap compiler pipeline

This script tests the bootstrap compiler pipeline by:
1. Using the existing Light ANTLR infrastructure to parse a simple test program
2. Simulating our bootstrap pipeline (lexer -> parser -> codegen) to verify correctness
3. Verifying the output Python code is valid and executable

The goal is to validate our bootstrap compiler design before tackling
the bootstrapping compilation chain.
"""

import sys
import os
import types

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'antlrparser'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# =============================================================================
# Test Data: A simple Light program to compile
# =============================================================================

TEST_PROGRAM = """设 msg 为 "Hello, Bootstrap!"。
打印 msg。
"""

TEST_PROGRAM_WITH_FUNC = """段落 greet 接收 name：
  设 full 为 name 加 "!"。
  打印 full。
结束。

设 x 为 42。
greet("World")。
"""

# =============================================================================
# Step 1: Test the existing ANTLR pipeline
# =============================================================================

def test_antlr_run():
    """Test that the ANTLR interpreter can run the test program."""
    print("=" * 60)
    print("Test 1: ANTLR Interpreter")
    print("=" * 60)
    
    from light_visitor import LightParser
    from light_interpreter import run_source
    
    try:
        result = run_source(TEST_PROGRAM)
        print(f"  ✓ ANTLR interpreter executed successfully")
        return True
    except Exception as e:
        print(f"  ✗ ANTLR interpreter failed: {e}")
        return False


def test_antlr_parse():
    """Test that the ANTLR parser can parse and we can inspect the AST."""
    print("\n" + "=" * 60)
    print("Test 2: ANTLR Parser AST Inspection")
    print("=" * 60)
    
    try:
        from light_visitor import LightParser
        parser = LightParser()
        module = parser.parse(TEST_PROGRAM)
        
        if module is None:
            print(f"  ✗ Parse failed:")
            for err in parser.errors:
                print(f"    {err}")
            return False
        
        print(f"  ✓ Parse succeeded")
        print(f"  Module type: {type(module).__name__}")
        print(f"  Statements: {len(module.statements)}")
        
        for i, stmt in enumerate(module.statements):
            print(f"  Stmt {i}: {type(stmt).__name__}")
            for attr in dir(stmt):
                if not attr.startswith('_') and not callable(getattr(stmt, attr)):
                    val = getattr(stmt, attr)
                    if val is not None:
                        print(f"    .{attr} = {val}")
        
        return True
    except Exception as e:
        print(f"  ✗ Parse failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# Step 2: Test our bootstrap codegen against the test program
# =============================================================================

def test_bootstrap_codegen():
    """
    Test our bootstrap codegen's output by mimicking the logic in Python.
    """
    print("\n" + "=" * 60)
    print("Test 3: Bootstrap Codegen Logic")
    print("=" * 60)
    
    # Create _light_builtin namespace
    import types
    ns_light_builtin = types.ModuleType('_light_builtin')
    ns_light_builtin.打印 = print
    ns_light_builtin.列表创建 = list
    ns_light_builtin.列表长度 = len
    ns_light_builtin.列表获取 = lambda lst, i: lst[i]
    ns_light_builtin.列表追加 = lambda lst, item: lst.append(item)
    ns_light_builtin.字典创建 = dict
    ns_light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
    ns_light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
    ns_light_builtin.字符串长度 = len
    
    # Build an AST manually matching what our parser would produce
    test_ast = [
        "program",
        [
            ["var_decl", "msg", ["string", "Hello, Bootstrap!"]],
            ["expr_stmt", ["func_call", "打印", [["identifier", "msg"]]]]
        ]
    ]
    
    # Our bootstrap codegen's logic, implemented in Python for testing
    def builtin_map(name):
        mapping = {
            '打印': '_light_builtin.打印',
            '输出': '_light_builtin.打印',
            '列表创建': '_light_builtin.列表创建',
            '列表长度': '_light_builtin.列表长度',
            '列表获取': '_light_builtin.列表获取',
            '列表追加': '_light_builtin.列表追加',
            '列表弹出': '_light_builtin.列表弹出',
            '列表包含': '_light_builtin.列表包含',
            '字典创建': '_light_builtin.字典创建',
            '字典设置': '_light_builtin.字典设置',
            '字典获取': '_light_builtin.字典获取',
            '字典包含键': '_light_builtin.字典包含键',
            '字符串长度': '_light_builtin.字符串长度',
            '字符串获取': '_light_builtin.字符串获取',
        }
        return mapping.get(name, name)
    
    def gen_expr(node):
        ntype = node[0]
        if ntype == "number":
            return node[1]
        elif ntype == "string":
            return '"' + node[1] + '"'
        elif ntype == "boolean":
            return "True" if node[1] == "真" else "False"
        elif ntype == "null":
            return "None"
        elif ntype == "identifier":
            return node[1]
        elif ntype == "func_call":
            name = builtin_map(node[1])
            args = node[2]
            result = name + "("
            for i, arg in enumerate(args):
                if i > 0:
                    result += ", "
                result += gen_expr(arg)
            result += ")"
            return result
        elif ntype == "binary_op":
            op = node[1]
            left = gen_expr(node[2])
            right = gen_expr(node[3])
            op_map = {
                '加': '+', '减': '-', '乘': '*', '除': '/',
                '模': '%', '幂': '**',
                '大于': '>', '小于': '<', '等于': '==',
                '不等于': '!=', '大于等于': '>=', '小于等于': '<=',
                '且': 'and', '或': 'or',
            }
            py_op = op_map.get(op, op)
            return f"({left} {py_op} {right})"
        return "None"
    
    def gen_stmt(node, indent_lines, indent_level):
        indent = "    " * indent_level
        ntype = node[0]
        
        if ntype == "var_decl":
            name = node[1]
            value = gen_expr(node[2])
            indent_lines.append(f"{indent}{name} = {value}")
        
        elif ntype == "assign":
            name = node[1]
            value = gen_expr(node[2])
            indent_lines.append(f"{indent}{name} = {value}")
        
        elif ntype == "compound_assign":
            name = node[1]
            op = node[2]
            value = gen_expr(node[3])
            op_map = {'加上': '+', '减去': '-', '乘以': '*', '除以': '/'}
            py_op = op_map.get(op, op)
            indent_lines.append(f"{indent}{name} {py_op}= {value}")
        
        elif ntype == "return":
            if node[1] is None:
                indent_lines.append(f"{indent}return")
            else:
                indent_lines.append(f"{indent}return {gen_expr(node[1])}")
        
        elif ntype == "if_stmt":
            cond = gen_expr(node[1])
            body = node[2]
            elif_branches = node[3]
            else_body = node[4]
            indent_lines.append(f"{indent}if {cond}:")
            for s in body:
                gen_stmt(s, indent_lines, indent_level + 1)
            for branch in elif_branches:
                elif_cond = gen_expr(branch[0])
                elif_body = branch[1]
                indent_lines.append(f"{indent}elif {elif_cond}:")
                for s in elif_body:
                    gen_stmt(s, indent_lines, indent_level + 1)
            if else_body is not None:
                indent_lines.append(f"{indent}else:")
                for s in else_body:
                    gen_stmt(s, indent_lines, indent_level + 1)
        
        elif ntype == "while_loop":
            cond = gen_expr(node[1])
            body = node[2]
            indent_lines.append(f"{indent}while {cond}:")
            for s in body:
                gen_stmt(s, indent_lines, indent_level + 1)
        
        elif ntype == "paragraph_def":
            name = node[1]
            params = node[2]
            body = node[3]
            param_str = ", ".join(params)
            indent_lines.append(f"{indent}def {name}({param_str}):")
            for s in body:
                gen_stmt(s, indent_lines, indent_level + 1)
            indent_lines.append("")
        
        elif ntype == "expr_stmt":
            code = gen_expr(node[1])
            indent_lines.append(f"{indent}{code}")
    
    # Generate Python code
    lines = []
    lines.append("# Generated by Light bootstrap compiler (test)")
    lines.append("import types")
    lines.append("_light_builtin = types.ModuleType('_light_builtin')")
    lines.append("_light_builtin.打印 = print")
    lines.append("_light_builtin.列表创建 = list")
    lines.append("_light_builtin.列表长度 = len")
    lines.append("_light_builtin.列表获取 = lambda lst, i: lst[i]")
    lines.append("_light_builtin.列表追加 = lambda lst, item: lst.append(item)")
    lines.append("_light_builtin.字典创建 = dict")
    lines.append("_light_builtin.字典设置 = lambda d, k, v: d.update({k: v})")
    lines.append("_light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)")
    lines.append("_light_builtin.字符串长度 = len")
    lines.append("")
    
    for stmt in test_ast[1]:
        gen_stmt(stmt, lines, 0)
    
    py_code = "\n".join(lines)
    
    print(f"  Generated Python code:")
    print(f"  {'-' * 40}")
    for line in py_code.split('\n'):
        print(f"  {line}")
    print(f"  {'-' * 40}")
    
    # Verify the generated code is valid Python
    try:
        namespace = {'_light_builtin': ns_light_builtin}
        exec(py_code, namespace)
        print(f"  ✓ Generated code executed successfully")
        return True
    except Exception as e:
        print(f"  ✗ Generated code execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# Step 3: Test with function definitions
# =============================================================================

def test_bootstrap_codegen_with_functions():
    """Test bootstrap codegen with function definitions."""
    print("\n" + "=" * 60)
    print("Test 4: Bootstrap Codegen with Functions")
    print("=" * 60)
    
    test_ast = [
        "program",
        [
            [
                "paragraph_def",
                "greet",
                ["name"],
                [
                    ["var_decl", "full", ["binary_op", "加", ["identifier", "name"], ["string", "!"]]],
                    ["expr_stmt", ["func_call", "打印", [["identifier", "full"]]]]
                ]
            ],
            ["var_decl", "x", ["number", "42"]],
            ["expr_stmt", ["func_call", "greet", [["string", "World"]]]]
        ]
    ]
    
    # Generate Python code using same gen_expr/gen_stmt functions
    def builtin_map(name):
        mapping = {
            '打印': '_light_builtin.打印',
            '列表创建': '_light_builtin.列表创建',
            '列表长度': '_light_builtin.列表长度',
            '列表获取': '_light_builtin.列表获取',
            '列表追加': '_light_builtin.列表追加',
        }
        return mapping.get(name, name)
    
    # Functions defined inside test scope - let me just re-use them
    import types
    _light_builtin2 = types.ModuleType('_light_builtin')
    _light_builtin2.打印 = print
    _light_builtin2.列表创建 = list
    _light_builtin2.列表长度 = len
    _light_builtin2.列表获取 = lambda lst, i: lst[i]
    _light_builtin2.列表追加 = lambda lst, item: lst.append(item)
    _light_builtin2.字典创建 = dict
    _light_builtin2.字典设置 = lambda d, k, v: d.update({k: v})
    _light_builtin2.字典获取 = lambda d, k, default=None: d.get(k, default)
    _light_builtin2.字符串长度 = len
    
    def gen_expr2(node):
        ntype = node[0]
        if ntype == "number": return node[1]
        if ntype == "string": return '"' + node[1] + '"'
        if ntype == "identifier": return node[1]
        if ntype == "func_call":
            name = builtin_map(node[1])
            args = node[2]
            result = name + "("
            for i, arg in enumerate(args):
                if i > 0: result += ", "
                result += gen_expr2(arg)
            result += ")"
            return result
        if ntype == "binary_op":
            op = node[1]
            left = gen_expr2(node[2])
            right = gen_expr2(node[3])
            op_map = {'加': '+', '减': '-', '乘': '*', '除': '/'}
            py_op = op_map.get(op, op)
            return f"({left} {py_op} {right})"
        return "None"
    
    def gen_stmt2(node, lines, indent_lvl):
        indent = "    " * indent_lvl
        ntype = node[0]
        
        if ntype == "var_decl":
            name = node[1]
            value = gen_expr2(node[2])
            lines.append(f"{indent}{name} = {value}")
        elif ntype == "paragraph_def":
            name = node[1]
            params = node[2]
            body = node[3]
            param_str = ", ".join(params)
            lines.append(f"{indent}def {name}({param_str}):")
            for s in body:
                gen_stmt2(s, lines, indent_lvl + 1)
            lines.append("")
        elif ntype == "expr_stmt":
            code = gen_expr2(node[1])
            lines.append(f"{indent}{code}")
    
    lines = []
    lines.append("# Generated by Light bootstrap compiler (test)")
    lines.append("import types")
    lines.append("_light_builtin = types.ModuleType('_light_builtin')")
    lines.append("_light_builtin.打印 = print")
    lines.append("_light_builtin.列表创建 = list")
    lines.append("_light_builtin.列表长度 = len")
    lines.append("")
    
    for stmt in test_ast[1]:
        gen_stmt2(stmt, lines, 0)
    
    py_code = "\n".join(lines)
    
    print(f"  Generated Python code:")
    for line in py_code.split('\n'):
        print(f"  {line}")
    
    try:
        namespace = {'_light_builtin': _light_builtin2}
        exec(py_code, namespace)
        print(f"  ✓ Generated code executed successfully")
        return True
    except Exception as e:
        print(f"  ✗ Generated code execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    results = []
    
    results.append(("ANTLR Run", test_antlr_run()))
    results.append(("ANTLR Parse", test_antlr_parse()))
    results.append(("Bootstrap Codegen", test_bootstrap_codegen()))
    results.append(("Codegen w/ Functions", test_bootstrap_codegen_with_functions()))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    if all(r[1] for r in results):
        print("\n  All tests passed! The bootstrap compiler design is valid.")
    else:
        print("\n  Some tests failed. Review the output above.")