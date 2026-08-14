"""
段言迭代器协议测试

测试内容：
1. 自定义迭代器：__迭代__ / __下一项__ 魔术方法
2. 遍历 循环使用自定义迭代器
"""

import sys
import os
import io
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def run_light(code: str) -> str:
    """使用 src 后端解析并执行段言代码，返回输出"""
    parser = LightParser()
    module = parser.parse(code)
    generator = PythonCodeGenerator()
    py_code = generator.generate(module)
    
    # 执行生成的 Python 代码，捕获输出
    output = io.StringIO()
    local_vars = {}
    try:
        with redirect_stdout(output):
            exec(py_code, {}, local_vars)
    except SystemExit:
        pass
    result = output.getvalue().strip()
    return result


def _compile(duan_code: str) -> str:
    """编译段言代码，返回Python源码"""
    parser = LightParser()
    module = parser.parse(duan_code)
    generator = PythonCodeGenerator()
    return generator.generate(module)


def test_iterator_protocol_method_names():
    """__迭代__ 映射到 __iter__，__下一项__ 映射到 __next__"""
    code = """
类 计数器：
  构造(上限)：
    设 己.上限 为 上限。
    设 己.当前 为 0。
  结束。

  段落 __迭代__()：
    返回 己。
  结束。

  段落 __下一项__()：
    设 己.当前 为 己.当前 加上 1。
    如果 己.当前 大于 己.上限：
      抛出 迭代停止。
    结束。
    返回 己.当前。
  结束。
结束。
"""
    py_code = _compile(code)
    assert 'def __iter__(self):' in py_code, f"__iter__ not found in:\n{py_code}"
    assert 'def __next__(self):' in py_code, f"__next__ not found in:\n{py_code}"
    assert 'StopIteration' in py_code or '迭代停止' in py_code


def test_custom_iterator_for_loop():
    """自定义迭代器可用于遍历循环"""
    result = run_light('''
类 计数器：
  构造(上限)：
    设 己.上限 为 上限。
    设 己.当前 为 0。
  结束。

  段落 __迭代__()：
    返回 己。
  结束。

  段落 __下一项__()：
    设 己.当前 为 己.当前 加上 1。
    如果 己.当前 大于 己.上限：
      抛出 迭代停止。
    结束。
    返回 己.当前。
  结束。
结束。

设 计 为 新建 计数器(3)。
遍历 数 之 计：
  打印 转字符串(数)。
结束。
''')
    assert "1" in result, f"Expected '1' in result, got '{result}'"
    assert "2" in result, f"Expected '2' in result, got '{result}'"
    assert "3" in result, f"Expected '3' in result, got '{result}'"


def test_iterator_with_range():
    """使用范围迭代器"""
    result = run_light('''
遍历 数 于 1 至 3：
  打印 转字符串(数)。
结束。
''')
    lines = result.strip().split('\n')
    assert len(lines) >= 3, f"Expected 3 lines, got {lines}"
    assert "1" in lines[0] if lines else True
    assert "2" in lines[1] if len(lines) > 1 else True
    assert "3" in lines[2] if len(lines) > 2 else True


def test_iterator_with_list():
    """遍历列表"""
    result = run_light('''
设 列表 为 [1, 2, 3]。
设 结果 为 ""。
遍历 数 之 列表：
  设 结果 为 结果 加上 转字符串(数)。
结束。
打印 结果。
''')
    assert result == "123", f"Expected '123', got '{result}'"


def test_iterator_stop_iteration():
    """迭代停止异常映射"""
    code = """
类 我的迭代器：
  段落 __迭代__()：
    返回 己。
  结束。
  段落 __下一项__()：
    抛出 迭代停止。
  结束。
结束。
"""
    py_code = _compile(code)
    assert 'raise StopIteration' in py_code or 'StopIteration' in py_code


if __name__ == '__main__':
    tests = [
        ("迭代器协议方法名", test_iterator_protocol_method_names),
        ("自定义迭代器遍历", test_custom_iterator_for_loop),
        ("范围迭代器", test_iterator_with_range),
        ("列表遍历", test_iterator_with_list),
        ("迭代停止异常", test_iterator_stop_iteration),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  [OK] {name}")
            passed += 1
        except Exception as e:
            import traceback
            print(f"  [失败] {name}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n总计: {len(tests)}  |  通过: {passed}  |  失败: {failed}")
    sys.exit(0 if failed == 0 else 1)