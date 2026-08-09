#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
光明编程语言 - ANTLR编译器功能验证测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'antlrparser'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from antlr4 import InputStream
from LightLangLexer import LightLangLexer
from LightLangParser import LightLangParser
from light_visitor import LightLangASTBuilder
from code_generator_unified import UnifiedCodeGenerator
from io import StringIO


def compile_and_run(code: str):
    """编译并运行光明代码"""
    # 词法分析
    input_stream = InputStream(code)
    lexer = LightLangLexer(input_stream)
    from antlr4 import CommonTokenStream
    tokens = CommonTokenStream(lexer)
    
    # 语法分析
    parser = LightLangParser(tokens)
    tree = parser.program()
    
    # AST构建
    builder = LightLangASTBuilder()
    module = builder.visitProgram(tree)
    
    if not module:
        return None, "AST构建失败"
    
    # 代码生成
    generator = UnifiedCodeGenerator()
    python_code = generator.generate(module)
    
    # 执行
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        exec(python_code, {})
        output = captured_output.getvalue()
    except Exception as e:
        output = f"执行错误: {e}"
    finally:
        sys.stdout = old_stdout
    
    return output, None


def test_variable_declaration():
    """测试变量声明"""
    code = """
设 甲 为 10。
设 乙 为 20。
设 结果 为 甲 加 乙。
打印 结果。
"""
    output, error = compile_and_run(code)
    assert error is None, f"编译失败: {error}"
    assert "30" in output, f"期望输出包含30，实际输出: {output}"
    return "变量声明测试通过"


def test_paragraph_definition():
    """测试函数定义"""
    code = """
段落 平方 接收 数值：
  返回 数值 乘 数值。
结束。

设 结果 为 平方(5)。
打印 结果。
"""
    output, error = compile_and_run(code)
    assert error is None, f"编译失败: {error}"
    assert "25" in output, f"期望输出包含25，实际输出: {output}"
    return "函数定义测试通过"


def test_paragraph_multiple_params():
    """测试多参数函数"""
    code = """
段落 求和 接收 甲, 乙：
  返回 甲 加 乙。
结束。

设 结果 为 求和(10, 20)。
打印 结果。
"""
    output, error = compile_and_run(code)
    assert error is None, f"编译失败: {error}"
    assert "30" in output, f"期望输出包含30，实际输出: {output}"
    return "多参数函数测试通过"


def test_conditional():
    """测试条件语句"""
    code = """
设 年龄 为 18。
如果 年龄 大于 18：
  打印 "成年"。
否则：
  打印 "未成年"。
结束。
"""
    output, error = compile_and_run(code)
    assert error is None, f"编译失败: {error}"
    assert "未成年" in output, f"期望输出包含'未成年'，实际输出: {output}"
    return "条件语句测试通过"


def test_while_loop():
    """测试while循环"""
    code = """
设 计数 为 0。
当 计数 小于 3：
  打印 计数。
  设 计数 为 计数 加 1。
结束。
"""
    output, error = compile_and_run(code)
    assert error is None, f"编译失败: {error}"
    assert "0" in output and "1" in output and "2" in output, f"期望输出包含0,1,2，实际输出: {output}"
    return "while循环测试通过"


def test_foreach_loop():
    """测试遍历循环"""
    code = """
设 水果 为 ["苹果", "香蕉"]。
遍历 水果项 之 水果：
  打印 水果项。
结束。
"""
    output, error = compile_and_run(code)
    assert error is None, f"编译失败: {error}"
    assert "苹果" in output and "香蕉" in output, f"期望输出包含苹果和香蕉，实际输出: {output}"
    return "遍历循环测试通过"


def test_recursive_function():
    """测试递归函数"""
    code = """
段落 阶乘 接收 数值：
  如果 数值 小于等于 1：
    返回 1。
  结束。
  返回 数值 乘 阶乘(数值 减 1)。
结束。

打印 阶乘(5)。
"""
    output, error = compile_and_run(code)
    assert error is None, f"编译失败: {error}"
    assert "120" in output, f"期望输出包含120，实际输出: {output}"
    return "递归函数测试通过"


def test_class_definition():
    """测试类定义"""
    code = """
类 动物：
  段落 叫声：
    打印 "动物叫声"。
  结束。
结束。

设 小动物 为 新建 动物。
小动物.叫声()。
"""
    output, error = compile_and_run(code)
    assert error is None, f"编译失败: {error}"
    assert "动物叫声" in output, f"期望输出包含'动物叫声'，实际输出: {output}"
    return "类定义测试通过"


def test_class_inheritance():
    """测试类继承"""
    code = """
类 动物：
  属性 名称。
  
  构造 接收 名称：
    己名称 为 名称。
  结束。
  
  段落 叫声：
    打印 "动物叫声"。
  结束。
结束。

类 狗 继承 动物：
  属性 品种。
  
  构造 接收 名称, 品种：
    己名称 为 名称。
    己品种 为 品种。
  结束。
  
  段落 叫声：
    打印 "汪汪汪"。
  结束。
  
  段落 介绍：
    打印 己名称。
    打印 己品种。
  结束。
结束。

设 小狗 为 新建 狗 "旺财", "金毛"。
小狗.叫声()。
小狗.介绍()。
"""
    output, error = compile_and_run(code)
    assert error is None, f"编译失败: {error}"
    assert "汪汪汪" in output and "旺财" in output and "金毛" in output, f"期望输出包含汪汪汪、旺财、金毛，实际输出: {output}"
    return "类继承测试通过"


def main():
    """运行所有测试"""
    tests = [
        test_variable_declaration,
        test_paragraph_definition,
        test_paragraph_multiple_params,
        test_conditional,
        test_while_loop,
        test_foreach_loop,
        test_recursive_function,
        test_class_definition,
        test_class_inheritance,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, "PASS", result))
        except AssertionError as e:
            results.append((test_func.__name__, "FAIL", str(e)))
        except Exception as e:
            results.append((test_func.__name__, "ERROR", str(e)))
    
    # 打印结果
    print("\n" + "=" * 70)
    print("光明编程语言 - ANTLR编译器功能验证测试报告")
    print("=" * 70)
    
    for name, status, message in results:
        status_icon = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[ERR!]"
        print(f"\n{status_icon} | {name:30} | {message}")
    
    # 统计
    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = sum(1 for _, status, _ in results if status == "FAIL")
    errors = sum(1 for _, status, _ in results if status == "ERROR")
    
    print("\n" + "=" * 70)
    print(f"总计: {len(results)}个测试")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  错误: {errors}")
    print("=" * 70 + "\n")
    
    return failed == 0 and errors == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
