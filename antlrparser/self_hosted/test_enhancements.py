"""测试光明解释器增强功能"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source


def test_stdlib_math():
    """测试数学函数"""
    print("=" * 70)
    print("测试：数学函数增强")
    print("=" * 70)
    
    test_code = '''
# 测试基础数学函数
打印("=== 基础数学 ===")。
打印("abs(-42) = "加abs(0减42))。
打印("floor(3.7) = "加floor(3.7))。
打印("ceil(3.2) = "加ceil(3.2))。
打印("round(3.5) = "加round(3.5))。
打印("mod(7, 3) = "加mod(7, 3))。
打印()。

# 测试幂运算
打印("=== 幂运算 ===")。
打印("sqrt(16) = "加sqrt(16))。
打印("cbrt(8) = "加cbrt(8))。
打印("pow(2, 10) = "加pow(2, 10))。
打印()。

# 测试三角函数（简单测试）
打印("=== 三角函数 ===")。
打印("sin(0) = "加sin(0))。
打印("cos(0) = "加cos(0))。
打印()。

# 测试指数对数
打印("=== 指数对数 ===")。
打印("exp(1) ≈ "加exp(1))。
打印("log(exp(1)) = "加round(log(exp(1))))。
打印("log10(100) = "加round(log10(100)))。
打印()。

打印("数学函数测试完成！")。
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
        import traceback
        traceback.print_exc()
        return False


def test_stdlib_string():
    """测试字符串函数"""
    print("\n" + "=" * 70)
    print("测试：字符串函数增强")
    print("=" * 70)
    
    test_code = '''
# 测试字符串函数
打印("=== 字符串函数 ===")。
定义s等于"  Hello World!  "。
打印("原始字符串: '"加s加"'")。
打印("len(s) = "加len(s))。
打印("trim(s) = '"加trim(s)加"'")。
打印()。

打印("=== 替换和查找 ===")。
打印("replace(Hello, l, x) = "加replace("Hello", "l", "x"))。
打印("indexOf(Hello, l) = "加indexOf("Hello", "l"))。
打印("startsWith(Hello, He) = "加startsWith("Hello", "He"))。
打印("endsWith(Hello, lo) = "加endsWith("Hello", "lo"))。
打印()。

打印("=== 大小写转换 ===")。
打印("toLowerCase(Hello) = "加toLowerCase("Hello"))。
打印("toUpperCase(Hello) = "加toUpperCase("Hello"))。
打印()。

打印("=== 重复和填充 ===")。
打印("repeat(ab, 3) = "加repeat("ab", 3))。
打印("padStart(123, 6, 0) = "加padStart("123", 6, "0"))。
打印("padEnd(abc, 6, x) = "加padEnd("abc", 6, "x"))。
打印()。

打印("字符串函数测试完成！")。
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
        import traceback
        traceback.print_exc()
        return False


def test_stdlib_list():
    """测试列表函数"""
    print("\n" + "=" * 70)
    print("测试：列表函数增强")
    print("=" * 70)
    
    test_code = '''
# 测试列表函数
打印("=== 列表基础操作 ===")。
定义arr等于【1,2,3,4,5】。
打印("原始列表长度: "加listLen(arr))。

listAppend(arr, 6)。
打印("append后长度: "加listLen(arr))。

listInsert(arr, 2, 99)。
打印("insert后第3个元素: "加arr[2])。

定义removed等于listRemove(arr, 2)。
打印("remove后被移除的元素: "加removed)。
打印("remove后长度: "加listLen(arr))。
打印()。

打印("=== 列表切片 ===")。
定义slice等于listSlice(arr, 1, 4)。
打印("slice(1,4) 长度: "加listLen(slice))。
打印()。

打印("=== 列表排序 ===")。
定义unsorted等于【5,2,8,1,9】。
listSort(unsorted)。
打印("排序后第一个: "加unsorted[0])。
打印("排序后最后一个: "加unsorted[4])。
打印()。

打印("=== 列表反转 ===")。
listReverse(arr)。
打印("反转后第一个: "加arr[0])。
打印()。

打印("=== 列表包含 ===")。
打印("listContains(arr, 3) = "加listContains(arr, 3))。
打印("listContains(arr, 99) = "加listContains(arr, 99))。
打印()。

打印("列表函数测试完成！")。
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
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 70)
    print("测试：错误处理增强")
    print("=" * 70)
    
    test_code = '''
# 测试错误处理
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
        print("检测到错误: " + ("是" if "错误" in output else "否"))
        return "除零错误" in output
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llvm_codegen():
    """测试LLVM代码生成器增强"""
    print("\n" + "=" * 70)
    print("测试：LLVM代码生成器增强")
    print("=" * 70)
    
    from light_llvm import compile_light
    
    test_code = '''
定义pi等于3.14159。
定义r等于10。
定义面积等于pi乘r乘r。
打印(面积)。

定义消息等于"Hello LLVM"。
打印(len(消息))。
'''
    
    try:
        success = compile_light(test_code, "test_enhanced.exe")
        if success:
            print("LLVM编译成功！")
            # 运行生成的程序
            result = os.popen("test_enhanced.exe").read()
            print("程序输出:")
            print(result)
            # 清理
            os.remove("test_enhanced.exe")
            os.remove("test_enhanced.ll")
            return True
        else:
            print("LLVM编译失败")
            return False
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 70)
    print("光明解释器增强功能测试")
    print("=" * 70)
    
    tests = [
        ("数学函数", test_stdlib_math),
        ("字符串函数", test_stdlib_string),
        ("列表函数", test_stdlib_list),
        ("错误处理", test_error_handling),
        ("LLVM代码生成", test_llvm_codegen),
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