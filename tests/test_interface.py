"""
光明接口与抽象类功能测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _compile(light_code: str) -> str:
    """编译光明代码，返回Python源码"""
    parser = LightParser()
    module = parser.parse(light_code)
    generator = PythonCodeGenerator()
    return generator.generate(module)


def test_interface_definition():
    """接口定义"""
    code = """
接口 可打印：
  段落 输出 返回 串。
结束。
"""
    py_code = _compile(code)
    assert 'from abc import ABC, abstractmethod' in py_code
    assert 'class 可打印(ABC):' in py_code
    assert '@abstractmethod' in py_code
    assert 'def 输出(self) -> str:' in py_code or 'def 输出(self) -> 串:' in py_code


def test_interface_inheritance():
    """接口继承"""
    code = """
接口 可保存 继承 可打印：
  段落 保存(路径)。
结束。
"""
    py_code = _compile(code)
    assert 'class 可保存(ABC, 可打印):' in py_code or 'class 可保存(可打印):' in py_code


def test_class_implements():
    """类实现接口"""
    code = """
接口 可打印：
  段落 输出 返回 串。
结束。

类 文档 实现 可打印：
  段落 输出 返回 串：
    返回 "文档内容"。
  结束。
结束。
"""
    py_code = _compile(code)
    assert 'class 文档(可打印):' in py_code


def test_abstract_decorator():
    """@抽象 装饰器"""
    code = """
类 形状：
  @抽象
  段落 面积 返回 数：
    结束。
结束。
"""
    py_code = _compile(code)
    assert '@abstractmethod' in py_code


if __name__ == '__main__':
    tests = [
        ("接口定义", test_interface_definition),
        ("接口继承", test_interface_inheritance),
        ("类实现接口", test_class_implements),
        ("@抽象装饰器", test_abstract_decorator),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  [OK] {name}")
            passed += 1
        except Exception as e:
            print(f"  [失败] {name}: {e}")
            failed += 1
    print(f"\n总计: {len(tests)}  |  通过: {passed}  |  失败: {failed}")
    sys.exit(0 if failed == 0 else 1)