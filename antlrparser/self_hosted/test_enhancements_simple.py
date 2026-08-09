"""简化测试光明解释器增强功能"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source


def test_math_basic():
    """测试基础数学函数"""
    print("=" * 70)
    print("测试：基础数学函数")
    print("=" * 70)
    
    test_code = '''
打印("=== 基础数学 ===")。
打印("abs(-42) = "加abs(0减42))。
打印("max(10, 20) = "加max(10, 20))。
打印("min(10, 20) = "加min(10, 20))。
打印("sqrt(16) = "加sqrt(16))。
打印("pow(2, 10) = "加pow(2, 10))。
打印("数学测试完成")。
'''
    
    try:
        with open(os.path.join(os.path.dirname(__file__), 'stdlib.light'), 'r', encoding='utf-8') as f:
            stdlib_code = f.read()
        
        full_code = stdlib_code + '\n\n' + test_code
        interp = run_source(full_code)
        output = interp.get_output()
        print(output)
        return True
    except Exception as e:
        print(f"测试失败: {e}")
        return False


def test_string_basic():
    """测试基础字符串函数"""
    print("\n" + "=" * 70)
    print("测试：字符串函数")
    print("=" * 70)
    
    test_code = '''
打印("=== 字符串函数 ===")。
打印("len(Hello) = "加len("Hello"))。
打印("trim(  abc  ) = "加trim("  abc  "))。
打印("substring(HelloWorld, 5, 10) = "加substring("HelloWorld", 5, 10))。
打印("字符串测试完成")。
'''
    
    try:
        with open(os.path.join(os.path.dirname(__file__), 'stdlib.light'), 'r', encoding='utf-8') as f:
            stdlib_code = f.read()
        
        full_code = stdlib_code + '\n\n' + test_code
        interp = run_source(full_code)
        output = interp.get_output()
        print(output)
        return True
    except Exception as e:
        print(f"测试失败: {e}")
        return False


def test_list_basic():
    """测试基础列表函数"""
    print("\n" + "=" * 70)
    print("测试：列表函数")
    print("=" * 70)
    
    test_code = '''
打印("=== 列表函数 ===")。
定义arr等于【1,2,3,4,5】。
打印("长度 = "加listLen(arr))。
listAppend(arr, 6)。
打印("append后长度 = "加listLen(arr))。
listReverse(arr)。
打印("reverse后第一个 = "加arr[0])。
打印("列表测试完成")。
'''
    
    try:
        with open(os.path.join(os.path.dirname(__file__), 'stdlib.light'), 'r', encoding='utf-8') as f:
            stdlib_code = f.read()
        
        full_code = stdlib_code + '\n\n' + test_code
        interp = run_source(full_code)
        output = interp.get_output()
        print(output)
        return True
    except Exception as e:
        print(f"测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 70)
    print("测试：错误处理")
    print("=" * 70)
    
    test_code = '''
打印("=== 测试除零错误 ===")。
定义a等于10。
定义b等于0。
定义c等于a除b。
打印("这条不应该执行")。
'''
    
    try:
        with open(os.path.join(os.path.dirname(__file__), 'stdlib.light'), 'r', encoding='utf-8') as f:
            stdlib_code = f.read()
        
        full_code = stdlib_code + '\n\n' + test_code
        interp = run_source(full_code)
        output = interp.get_output()
        print(output)
        return "错误" in output or "除以零" in str(sys.exc_info()[0])
    except Exception as e:
        print(f"捕获到预期错误: {e}")
        return True


def main():
    """运行所有测试"""
    print("=" * 70)
    print("光明解释器增强功能测试")
    print("=" * 70)
    
    tests = [
        ("数学函数", test_math_basic),
        ("字符串函数", test_string_basic),
        ("列表函数", test_list_basic),
        ("错误处理", test_error_handling),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n--- 运行测试: {name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✓ {name} 测试通过")
            else:
                failed += 1
                print(f"✗ {name} 测试失败")
        except Exception as e:
            failed += 1
            print(f"✗ {name} 测试异常: {e}")
    
    print("\n" + "=" * 70)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 70)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())