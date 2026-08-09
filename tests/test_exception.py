"""
光明异常处理功能测试
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _compile_and_exec(light_code: str) -> dict:
    """编译并执行光明代码，返回执行后的全局变量"""
    parser = LightParser()
    module = parser.parse(light_code)
    
    generator = PythonCodeGenerator()
    py_code = generator.generate(module)
    
    # 执行生成的 Python 代码
    namespace = {}
    exec(py_code, namespace)
    return namespace


def test_try_catch_basic():
    """基本 try/catch"""
    code = """
设 结果 为 空。
尝试：
  设 结果 为 "尝试执行"。
捕获 错误：
  设 结果 为 "捕获到异常"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('结果') == "尝试执行", f"期望'尝试执行'，得到 {ns.get('结果')}"


def test_try_catch_exception_raised():
    """try/catch 捕获真实异常"""
    code = """
尝试：
  设 甲 为 1 除 0。
捕获 错误：
  设 甲 为 "除零错误"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('甲') == "除零错误", f"期望'除零错误'，得到 {ns.get('甲')}"


def test_try_catch_with_type():
    """按类型捕获异常（匹配时捕获）"""
    code = """
尝试：
  设 甲 为 1 除 0。
捕获 ZeroDivisionError：
  设 甲 为 "捕获除零"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('甲') == "捕获除零", f"期望'捕获除零'，得到 {ns.get('甲')}"


def test_try_catch_with_type_and_var():
    """按类型+变量捕获异常"""
    code = """
设 信息 为 空。
尝试：
  设 甲 为 1 除 0。
捕获 ZeroDivisionError 错误：
  设 信息 为 错误。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('信息') is not None, "异常对象不应为空"
    assert 'division by zero' in str(ns.get('信息')), f"期望包含'division by zero'，得到 {ns.get('信息')}"


def test_try_catch_wrong_type():
    """按类型捕获但异常类型不匹配（传播）"""
    code = """
尝试：
  设 甲 为 1 除 0。
捕获 ValueError：
  设 甲 为 "不会执行"。
结束。
"""
    try:
        ns = _compile_and_exec(code)
        assert False, "应抛出 ZeroDivisionError 但未抛出"
    except ZeroDivisionError:
        pass  # 预期行为：类型不匹配，异常向上传播


def test_try_catch_finally():
    """try/catch/finally 完整组合"""
    code = """
设 最终结果 为 空。
尝试：
  设 甲 为 1 除 0。
捕获 错误：
  设 甲 为 "错误信息"。
最终：
  设 最终结果 为 "执行完成"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('最终结果') == "执行完成", f"期望'执行完成'，得到 {ns.get('最终结果')}"
    assert ns.get('甲') == "错误信息", f"期望'错误信息'，得到 {ns.get('甲')}"


def test_throw_exception():
    """抛出异常"""
    code = """
尝试：
  抛出 "自定义错误"。
捕获 错误：
  设 甲 为 错误。
结束。
"""
    ns = _compile_and_exec(code)
    assert str(ns.get('甲')) == "自定义错误"


def test_throw_inside_function():
    """在函数内抛出异常"""
    code = """
段落 除 接收 甲, 乙：
  如果 乙 等于 0：
    抛出 "除数不能为零"。
  结束。
  返回 甲 除 乙。
结束。

设 结果 为 空。
尝试：
  设 结果 为 除(10, 0)。
捕获 错误：
  设 结果 为 错误。
结束。
"""
    ns = _compile_and_exec(code)
    assert str(ns.get('结果')) == "除数不能为零"


if __name__ == '__main__':
    tests = [
        ("基本 try/catch", test_try_catch_basic),
        ("捕获真实异常", test_try_catch_exception_raised),
        ("按类型捕获", test_try_catch_with_type),
        ("类型+变量", test_try_catch_with_type_and_var),
        ("类型不匹配传播", test_try_catch_wrong_type),
        ("try/catch/finally", test_try_catch_finally),
        ("抛出异常", test_throw_exception),
        ("函数内抛出", test_throw_inside_function),
    ]
    
    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [OK] {name}")
            passed += 1
        except Exception as e:
            print(f"  [失败] {name}: {e}")
            failed += 1
    
    print(f"\n总计: {len(tests)}  |  通过: {passed}  |  失败: {failed}")
    sys.exit(0 if failed == 0 else 1)