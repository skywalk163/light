"""
段言协议（trait）系统测试

测试协议定义、实现、继承、多态等核心功能。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _compile(duan_code: str) -> str:
    """编译段言代码，返回Python源码"""
    parser = LightParser()
    module = parser.parse(duan_code)
    generator = PythonCodeGenerator()
    return generator.generate(module)


def _exec(py_code: str) -> dict:
    """执行生成的 Python 代码，返回全局变量字典"""
    globals_dict = {}
    exec(py_code, globals_dict)
    return globals_dict


def test_trait_definition():
    """协议定义"""
    code = """
协议 可序列化：
  段落 转JSON() 返回 串。
  段落 从JSON(数据)。
结束。
"""
    py_code = _compile(code)
    assert 'from abc import ABC, abstractmethod' in py_code
    assert 'class 可序列化(ABC):' in py_code
    assert '@abstractmethod' in py_code
    assert 'def 转JSON(self)' in py_code
    assert 'def 从JSON(self, 数据)' in py_code


def test_trait_inheritance():
    """协议继承"""
    code = """
协议 可打印：
  段落 输出() 返回 串。
结束。

协议 可保存 继承 可打印：
  段落 保存(路径)。
结束。
"""
    py_code = _compile(code)
    assert 'class 可打印(ABC):' in py_code
    assert 'class 可保存(ABC, 可打印):' in py_code or 'class 可保存(可打印):' in py_code


def test_class_implements_trait():
    """类实现协议"""
    code = """
协议 可打印：
  段落 输出() 返回 串。
结束。

类 文档 实现 可打印：
  段落 输出() 返回 串：
    返回 "文档内容"。
  结束。
结束。
"""
    py_code = _compile(code)
    assert 'class 文档(可打印):' in py_code
    # 执行验证（需要定义 串 作为 exec 的全局变量）
    globals_dict = {'串': str}
    exec(py_code, globals_dict)
    doc = globals_dict['文档']()
    result = doc.输出()
    assert result == '文档内容'


def test_class_implements_multiple_traits():
    """类实现多个协议"""
    code = """
协议 可打印：
  段落 输出() 返回 串。
结束。

协议 可保存：
  段落 保存(路径)。
结束。

类 文档 实现 可打印, 可保存：
  段落 输出() 返回 串：
    返回 "文档内容"。
  结束。

  段落 保存(路径)：
    打印("保存到：" + 路径)。
  结束。
结束。
"""
    py_code = _compile(code)
    assert 'class 文档(可打印, 可保存):' in py_code
    # 执行验证
    from io import StringIO
    import contextlib
    globals_dict = {'串': str}
    exec(py_code, globals_dict)
    doc = globals_dict['文档']()
    result = doc.输出()
    assert result == '文档内容'


def test_trait_polymorphism():
    """协议多态：不同类实现同一协议"""
    code = """
协议 可打印：
  段落 输出() 返回 串。
结束。

类 文档 实现 可打印：
  段落 输出() 返回 串：
    返回 "文档内容"。
  结束。
结束。

类 图片 实现 可打印：
  段落 输出() 返回 串：
    返回 "图片内容"。
  结束。
结束。
"""
    py_code = _compile(code)
    assert 'class 文档(可打印):' in py_code
    assert 'class 图片(可打印):' in py_code
    # 执行验证多态
    globals_dict = {'串': str}
    exec(py_code, globals_dict)
    doc = globals_dict['文档']()
    img = globals_dict['图片']()
    assert doc.输出() == '文档内容'
    assert img.输出() == '图片内容'


def test_trait_as_interface_alias():
    """协议和接口等价"""
    code1 = """
接口 可打印：
  段落 输出() 返回 串。
结束。
"""
    code2 = """
协议 可打印：
  段落 输出() 返回 串。
结束。
"""
    py1 = _compile(code1)
    py2 = _compile(code2)
    # 两者生成相同的结构
    assert 'class 可打印(ABC):' in py1
    assert 'class 可打印(ABC):' in py2


def test_abstract_decorator_in_class():
    """类中的 @抽象 装饰器"""
    code = """
类 形状：
  @抽象
  段落 面积() 返回 数：
    结束。
结束。
"""
    py_code = _compile(code)
    assert '@abstractmethod' in py_code
    assert 'class 形状(ABC):' in py_code or 'ABC' in py_code


def test_trait_interface_mixed_implement():
    """类同时实现协议和接口"""
    code = """
接口 可打印：
  段落 输出() 返回 串。
结束。

协议 可保存：
  段落 保存(路径)。
结束。

类 文档 实现 可打印, 可保存：
  段落 输出() 返回 串：
    返回 "文档内容"。
  结束。

  段落 保存(路径)：
    打印("保存到：" + 路径)。
  结束。
结束。
"""
    py_code = _compile(code)
    assert 'class 文档(可打印, 可保存):' in py_code


if __name__ == '__main__':
    tests = [
        ("协议定义", test_trait_definition),
        ("协议继承", test_trait_inheritance),
        ("类实现协议", test_class_implements_trait),
        ("类实现多个协议", test_class_implements_multiple_traits),
        ("协议多态", test_trait_polymorphism),
        ("协议接口等价", test_trait_as_interface_alias),
        ("@抽象装饰器", test_abstract_decorator_in_class),
        ("协议接口混合实现", test_trait_interface_mixed_implement),
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