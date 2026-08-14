"""
光明异常处理功能测试

测试内容：
1. 基本 try/catch
2. 按类型捕获异常
3. try/catch/finally 完整组合
4. 抛出异常（含异常链）
5. 多个捕获块
6. 异常类型层级（中文异常名）
7. 嵌套异常处理
8. 裸抛出（重新抛出）
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


def test_throw_chaining_from():
    """异常链：抛出 新异常 from 原异常"""
    code = """
尝试：
  尝试：
    设 甲 为 1 除 0。
  捕获 原错误：
    抛出 运行时错误("除零错误") from 原错误。
  结束。
捕获 错误：
  设 信息 为 错误。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('信息') is not None, "异常对象不应为空"
    assert '除零错误' in str(ns.get('信息'))


def test_throw_chaining_cong():
    """异常链：抛出 新异常 从 原异常（中文关键字）"""
    code = """
尝试：
  尝试：
    设 甲 为 1 除 0。
  捕获 原错误：
    抛出 运行时错误("除零错误") 从 原错误。
  结束。
捕获 错误：
  设 信息 为 错误。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('信息') is not None, "异常对象不应为空"
    assert '除零错误' in str(ns.get('信息'))


def test_multiple_catch_clauses():
    """多个捕获块：不同类型走不同分支"""
    code = """
设 结果 为 空。
尝试：
  设 甲 为 1 除 0。
捕获 ZeroDivisionError 错误：
  设 结果 为 "除零捕获"。
捕获 ValueError 错误：
  设 结果 为 "值错误捕获"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('结果') == "除零捕获", f"期望'除零捕获'，得到 {ns.get('结果')}"


def test_multiple_catch_clauses_order():
    """多个捕获块：第二个类型匹配"""
    code = """
设 结果 为 空。
尝试：
  设 列表 为 [1, 2, 3]。
  设 甲 为 列表[10]。
捕获 ValueError 错误：
  设 结果 为 "值错误捕获"。
捕获 IndexError 错误：
  设 结果 为 "索引错误捕获"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('结果') == "索引错误捕获", f"期望'索引错误捕获'，得到 {ns.get('结果')}"


def test_bare_raise():
    """裸抛出（重新抛出当前异常）"""
    code = """
设 结果 为 空。
尝试：
  尝试：
    设 甲 为 1 除 0。
  捕获 错误：
    设 结果 为 "内部捕获"。
    抛出。
  结束。
捕获 错误：
  设 结果 为 结果 + "->外部捕获"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('结果') == "内部捕获->外部捕获", f"期望'内部捕获->外部捕获'，得到 {ns.get('结果')}"


def test_chinese_exception_type_name():
    """中文异常类型名：零除错误"""
    code = """
设 结果 为 空。
尝试：
  设 甲 为 1 除 0。
捕获 零除错误 错误：
  设 结果 为 "零除错误捕获"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('结果') == "零除错误捕获", f"期望'零除错误捕获'，得到 {ns.get('结果')}"


def test_chinese_exception_type_name_value_error():
    """中文异常类型名：值错误"""
    code = """
设 结果 为 空。
尝试：
  抛出 值错误("测试值错误")。
捕获 值错误 错误：
  设 结果 为 "值错误捕获"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('结果') == "值错误捕获", f"期望'值错误捕获'，得到 {ns.get('结果')}"


def test_try_finally_no_catch():
    """只有 try/finally 无 catch"""
    code = """
设 结果 为 空。
尝试：
  设 结果 为 "尝试执行"。
最终：
  设 结果 为 结果 + "->最终执行"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('结果') == "尝试执行->最终执行", f"期望'尝试执行->最终执行'，得到 {ns.get('结果')}"


def test_nested_try_catch():
    """嵌套 try/catch"""
    code = """
设 结果 为 空。
尝试：
  尝试：
    设 甲 为 1 除 0。
  捕获 错误：
    设 结果 为 "内层捕获"。
  结束。
捕获 错误：
  设 结果 为 结果 + "->外层不会执行"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('结果') == "内层捕获", f"期望'内层捕获'，得到 {ns.get('结果')}"


def test_exception_in_finally():
    """finally 块中抛出异常"""
    code = """
设 结果 为 空。
尝试：
  设 结果 为 "尝试块"。
最终：
  抛出 "最终异常"。
结束。
"""
    try:
        ns = _compile_and_exec(code)
        assert False, "应抛出异常但未抛出"
    except Exception as e:
        assert '最终异常' in str(e), f"期望'最终异常'，得到 {e}"


def test_throw_chinese_exception_name():
    """抛出中文异常名"""
    code = """
尝试：
  抛出 值错误。
捕获 值错误 错误：
  设 结果 为 "值错误抛出"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('结果') == "值错误抛出", f"期望'值错误抛出'，得到 {ns.get('结果')}"


def test_throw_chinese_exception_name_with_message():
    """抛出中文异常名带消息"""
    code = """
尝试：
  抛出 运行时错误("自定义消息")。
捕获 运行时错误 错误：
  设 结果 为 字符串(错误)。
结束。
"""
    ns = _compile_and_exec(code)
    assert '自定义消息' in str(ns.get('结果')), f"期望含'自定义消息'，得到 {ns.get('结果')}"


def test_catch_any_exception_with_var():
    """捕获任意异常带变量"""
    code = """
设 结果 为 空。
尝试：
  设 甲 为 1 除 0。
捕获 错误：
  设 结果 为 字符串(错误)。
结束。
"""
    ns = _compile_and_exec(code)
    assert 'division by zero' in str(ns.get('结果')), f"期望含'division by zero'，得到 {ns.get('结果')}"


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
        ("异常链 from", test_throw_chaining_from),
        ("异常链 从", test_throw_chaining_cong),
        ("多个捕获块", test_multiple_catch_clauses),
        ("多个捕获块顺序", test_multiple_catch_clauses_order),
        ("裸抛出", test_bare_raise),
        ("中文异常类型名 零除错误", test_chinese_exception_type_name),
        ("中文异常类型名 值错误", test_chinese_exception_type_name_value_error),
        ("try/finally 无 catch", test_try_finally_no_catch),
        ("嵌套 try/catch", test_nested_try_catch),
        ("finally 中抛出异常", test_exception_in_finally),
        ("抛出中文异常名", test_throw_chinese_exception_name),
        ("抛出中文异常名带消息", test_throw_chinese_exception_name_with_message),
        ("捕获异常带类型信息", test_catch_any_exception_with_var),
    ]
    
    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [OK] {name}")
            passed += 1
        except Exception as e:
            import traceback
            print(f"  [失败] {name}: {e}")
            traceback.print_exc()
            failed += 1
    
    print(f"\n总计: {len(tests)}  |  通过: {passed}  |  失败: {failed}")
    sys.exit(0 if failed == 0 else 1)