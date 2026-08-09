#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明文件I/O测试

测试文件读写和文件系统操作
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'stdlib'))

# 导入光明标准库
try:
    from stdlib import builtins as _light_builtin
except ImportError:
    # 如果无法导入，使用当前模块
    import importlib.util
    spec = importlib.util.spec_from_file_location("light_builtins", 
        os.path.join(os.path.dirname(__file__), '..', 'src', 'stdlib', 'builtins.py'))
    _light_builtin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_light_builtin)


def test_read_write_file():
    """测试文件读写"""
    print("="*60)
    print("测试1: 文件读写")
    print("="*60)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        test_file = os.path.join(temp_dir, "test.txt")
        test_content = "Hello, 光明！\n测试文件读写功能。"
        
        # 写入文件
        _light_builtin.写入文件(test_file, test_content)
        print(f"  [OK] 写入文件: {test_file}")
        
        # 读取文件
        content = _light_builtin.读取文件(test_file)
        print(f"  [OK] 读取文件: {len(content)} 字符")
        
        # 验证
        assert content == test_content, "内容不匹配"
        print(f"  [OK] 内容验证通过")
        
        return True
        
    finally:
        # 清理
        shutil.rmtree(temp_dir)


def test_file_exists():
    """测试文件存在检查"""
    print("\n" + "="*60)
    print("测试2: 文件存在检查")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建测试文件
        test_file = os.path.join(temp_dir, "exists.txt")
        
        # 文件不存在
        assert not _light_builtin.文件存在(test_file)
        print(f"  [OK] 文件不存在检查通过")
        
        # 创建文件
        _light_builtin.写入文件(test_file, "test")
        
        # 文件存在
        assert _light_builtin.文件存在(test_file)
        print(f"  [OK] 文件存在检查通过")
        
        # 目录存在
        assert _light_builtin.目录存在(temp_dir)
        print(f"  [OK] 目录存在检查通过")
        
        return True
        
    finally:
        shutil.rmtree(temp_dir)


def test_directory_operations():
    """测试目录操作"""
    print("\n" + "="*60)
    print("测试3: 目录操作")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建子目录
        sub_dir = os.path.join(temp_dir, "subdir", "nested")
        _light_builtin.创建目录(sub_dir)
        
        assert _light_builtin.目录存在(sub_dir)
        print(f"  [OK] 创建目录: {sub_dir}")
        
        # 列出目录
        files = _light_builtin.列出目录(temp_dir)
        print(f"  [OK] 列出目录: {files}")
        assert "subdir" in files
        
        return True
        
    finally:
        shutil.rmtree(temp_dir)


def test_path_operations():
    """测试路径操作"""
    print("\n" + "="*60)
    print("测试4: 路径操作")
    print("="*60)
    
    # 绝对路径
    abs_path = _light_builtin.绝对路径(".")
    print(f"  [OK] 绝对路径: {abs_path}")
    
    # 连接路径
    joined = _light_builtin.连接路径("dir", "subdir", "file.txt")
    print(f"  [OK] 连接路径: {joined}")
    assert "dir" in joined and "file.txt" in joined
    
    # 目录名和文件名
    test_path = "/path/to/file.txt"
    dirname = _light_builtin.目录名(test_path)
    basename = _light_builtin.文件名(test_path)
    print(f"  [OK] 目录名: {dirname}, 文件名: {basename}")
    assert basename == "file.txt"
    
    # 扩展名
    ext = _light_builtin.扩展名(test_path)
    print(f"  [OK] 扩展名: {ext}")
    assert ext == ".txt"
    
    return True


def test_string_operations():
    """测试字符串操作"""
    print("\n" + "="*60)
    print("测试5: 字符串操作")
    print("="*60)
    
    # 转换
    assert _light_builtin.转整数("123") == 123
    print(f"  [OK] 转整数: '123' -> 123")
    
    assert _light_builtin.转浮点("3.14") == 3.14
    print(f"  [OK] 转浮点: '3.14' -> 3.14")
    
    # 字符串操作
    text = "  Hello 光明  "
    trimmed = _light_builtin.去除空白(text)
    print(f"  [OK] 去除空白: '{trimmed}'")
    assert trimmed == "Hello 光明"
    
    # 分割
    parts = _light_builtin.分割字符串("a,b,c", ",")
    print(f"  [OK] 分割字符串: {parts}")
    assert parts == ["a", "b", "c"]
    
    # 连接
    joined = _light_builtin.连接字符串(["x", "y", "z"], "-")
    print(f"  [OK] 连接字符串: '{joined}'")
    assert joined == "x-y-z"
    
    return True


def test_list_operations():
    """测试列表操作"""
    print("\n" + "="*60)
    print("测试6: 列表操作")
    print("="*60)
    
    # 创建列表
    lst = [3, 1, 4, 1, 5]
    
    # 长度
    length = _light_builtin.列表长度(lst)
    print(f"  [OK] 列表长度: {length}")
    assert length == 5
    
    # 排序
    lst_copy = lst.copy()
    _light_builtin.列表排序(lst_copy)
    print(f"  [OK] 排序后: {lst_copy}")
    assert lst_copy == [1, 1, 3, 4, 5]
    
    # 包含
    has_three = _light_builtin.列表包含(lst, 3)
    print(f"  [OK] 包含3: {has_three}")
    assert has_three
    
    return True


def test_compilation():
    """测试编译器集成"""
    print("\n" + "="*60)
    print("测试7: 编译器集成")
    print("="*60)
    
    from lexer import Lexer
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator
    
    # 光明代码
    light_code = '''
设路径为"test.txt"。
设内容为"Hello, 光明！\\n"。

写入文件参数路径，内容。

如果文件存在参数路径那么
  打印"文件创建成功"。
  设读取内容为读取文件参数路径。
  打印读取内容。
否则
  打印"文件创建失败"。
'''
    
    print("  光明代码:")
    print("  " + "\n  ".join(light_code.strip().split("\n")))
    
    # 编译
    parser = LightParser()
    generator = PythonCodeGenerator()
    
    try:
        module = parser.parse(light_code)
        python_code = generator.generate(module)
        
        print("\n  生成的Python代码:")
        print("  " + "\n  ".join(python_code.strip().split("\n")[:20]))
        
        print("\n  [OK] 编译成功")
        return True
        
    except Exception as e:
        print(f"\n  [FAIL] 编译失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("光明文件I/O测试套件")
    print("="*60)
    print()
    
    tests = [
        ("文件读写", test_read_write_file),
        ("文件存在检查", test_file_exists),
        ("目录操作", test_directory_operations),
        ("路径操作", test_path_operations),
        ("字符串操作", test_string_operations),
        ("列表操作", test_list_operations),
        ("编译器集成", test_compilation),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] 测试 {name} 异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n通过: {passed}/{total}")
    
    if passed == total:
        print("\n恭喜！所有测试通过！")
        return True
    else:
        print(f"\n有 {total - passed} 个测试失败")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
