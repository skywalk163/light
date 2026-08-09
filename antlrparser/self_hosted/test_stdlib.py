"""测试光明标准库功能"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source


def test_stdlib():
    """测试标准库函数"""
    print("=" * 70)
    print("测试：光明标准库功能")
    print("=" * 70)
    print()
    
    # 测试代码
    test_code = '''
# 测试数学函数
打印("=== 数学函数 ===")。
打印("abs(-42) = "加abs(0减42))。
打印("sqrt(16) = "加sqrt(16))。
打印("pow(2, 10) = "加pow(2, 10))。
打印("max(10, 20) = "加max(10, 20))。
打印("min(10, 20) = "加min(10, 20))。
打印()。

# 测试字符串函数
打印("=== 字符串函数 ===")。
打印("len(Hello) = "加len("Hello"))。
打印("substring(HelloWorld, 5, 10) = "加substring("HelloWorld", 5, 10))。
打印()。

# 测试列表函数
打印("=== 列表函数 ===")。
定义arr等于【1,2,3,4,5】。
打印("listLen(arr) = "加listLen(arr))。
listAppend(arr, 6)。
打印("listAppend后长度 = "加listLen(arr))。
listReverse(arr)。
打印("listReverse后第一个 = "加arr[0])。
打印()。

# 测试调试函数
打印("=== 调试函数 ===")。
printDebug("测试变量", 123)。
assert(真, "这应该通过")。
打印("断言通过！")。
打印()。

打印("所有标准库测试完成！")。
'''
    
    try:
        # 合并标准库和测试代码
        with open(os.path.join(os.path.dirname(__file__), 'stdlib.light'), 'r', encoding='utf-8') as f:
            stdlib_code = f.read()
        
        full_code = stdlib_code + '\n\n' + test_code
        
        interp = run_source(full_code)
        output = interp.get_output()
        print(output)
        print("=" * 70)
        print("标准库测试完成！")
        return 0
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(test_stdlib())