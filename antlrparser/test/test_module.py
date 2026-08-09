"""
光明 - 模块系统测试

测试：
1. 从模块导入指定符号
2. 导入后调用导入的函数
3. 无导出声明时的导入（导入全部段落）
4. 模块缓存（多次导入同一模块）
5. 文件级模块导入（run_file）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source, run_file, LightValue


# =============================================================================
# 测试用例
# =============================================================================

def test_import_basic():
    """测试基本导入：从模块导入指定符号"""
    print("\n" + "=" * 60)
    print("测试: 基本导入")
    print("=" * 60)

    code = """
从 mod_math 导入《平方》，《立方》。

定义甲等于《平方》(5)。
定义乙等于《立方》(3)。
"""
    interp = run_source(code, search_paths=['test', '.'])

    val_a = interp.env.get('甲')
    val_b = interp.env.get('乙')
    assert val_a.value == 25, f"平方(5) 应为 25, 实际 {val_a.value}"
    assert val_b.value == 27, f"立方(3) 应为 27, 实际 {val_b.value}"
    print("  [+] 平方(5) = 25")
    print("  [+] 立方(3) = 27")
    return True


def test_import_factorial():
    """测试导入带复杂逻辑的函数（阶乘）"""
    print("\n" + "=" * 60)
    print("测试: 导入阶乘函数")
    print("=" * 60)

    code = """
从 mod_math 导入《阶乘》。

定义甲等于《阶乘》(5)。
定义乙等于《阶乘》(0)。
定义丙等于《阶乘》(3)。
"""
    interp = run_source(code, search_paths=['test', '.'])

    assert interp.env.get('甲').value == 120, "阶乘(5) 应为 120"
    assert interp.env.get('乙').value == 1, "阶乘(0) 应为 1"
    assert interp.env.get('丙').value == 6, "阶乘(3) 应为 6"
    print("  [+] 阶乘(5) = 120")
    print("  [+] 阶乘(0) = 1")
    print("  [+] 阶乘(3) = 6")
    return True


def test_import_no_export():
    """测试无导出声明时的导入"""
    print("\n" + "=" * 60)
    print("测试: 无导出声明的模块导入")
    print("=" * 60)

    code = """
从 mod_greet 导入《欢迎》，《再见》。

定义甲等于《欢迎》('张三')。
定义乙等于《再见》('李四')。
"""
    interp = run_source(code, search_paths=['test', '.'])

    val1 = interp.env.get('甲')
    val2 = interp.env.get('乙')
    assert val1.value == '欢迎，张三！', f"应为 '欢迎，张三！', 实际 {val1.value}"
    assert val2.value == '再见，李四。', f"应为 '再见，李四。', 实际 {val2.value}"
    print("  [+] 欢迎('张三') = '欢迎，张三！'")
    print("  [+] 再见('李四') = '再见，李四。'")
    return True


def test_import_export_check():
    """测试导出检查：未导出的符号不能被导入"""
    print("\n" + "=" * 60)
    print("测试: 导出检查 - 未导出符号不可导入")
    print("=" * 60)

    # mod_math 只导出了 平方/立方/阶乘，没有导出其他符号
    code = """
从 mod_math 导入《平方》，《立方》，《不存在的符号》。
"""
    try:
        interp = run_source(code, search_paths=['test', '.'])
        print("  [-] 应该抛出错误但未抛出")
        return False
    except RuntimeError as e:
        if '未找到导出符号' in str(e):
            print(f"  [+] 正确拦截未导出符号: {e}")
            return True
        print(f"  [-] 错误类型不对: {e}")
        return False


def test_import_cache():
    """测试模块缓存：多次导入同一模块应重用"""
    print("\n" + "=" * 60)
    print("测试: 模块缓存")
    print("=" * 60)

    code = """
从 mod_math 导入《平方》。
从 mod_math 导入《立方》。

定义甲等于《平方》(4)。
定义乙等于《立方》(2)。
"""
    interp = run_source(code, search_paths=['test', '.'])

    assert interp.env.get('甲').value == 16
    assert interp.env.get('乙').value == 8
    print("  [+] 多次导入同一模块正常")
    return True


def test_import_via_file():
    """测试通过文件路径导入模块"""
    print("\n" + "=" * 60)
    print("测试: 文件导入")
    print("=" * 60)

    # 创建一个使用模块的主文件
    main_path = os.path.join(os.path.dirname(__file__), 'test_main.light')
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write("""
从 mod_math 导入《平方》，《阶乘》。

定义结果1等于《平方》(6)。
定义结果2等于《阶乘》(4)。
""")

    try:
        interp = run_file(main_path)
        val1 = interp.env.get('结果1')
        val2 = interp.env.get('结果2')
        assert val1.value == 36, f"平方(6) 应为 36, 实际 {val1.value}"
        assert val2.value == 24, f"阶乘(4) 应为 24, 实际 {val2.value}"
        print("  [+] 文件导入正常")
        print(f"  [+] 平方(6) = {val1.value}")
        print(f"  [+] 阶乘(4) = {val2.value}")
        return True
    finally:
        if os.path.exists(main_path):
            os.remove(main_path)


def test_import_nested():
    """测试嵌套导入：A 导入 B，B 导入 C（递归依赖）"""
    print("\n" + "=" * 60)
    print("测试: 嵌套导入（递归依赖）")
    print("=" * 60)

    code = """
从 mod_advanced 导入《计算表达式》，《拼接字符串》。

定义结果1等于《计算表达式》(5)。
定义结果2等于《拼接字符串》("Hello", ", ", "World")。
"""
    interp = run_source(code, search_paths=['test', '.'])

    val1 = interp.env.get('结果1')
    val2 = interp.env.get('结果2')
    assert val1.value == 15, f"计算表达式(5) 应为 15 (5*2+5), 实际 {val1.value}"
    assert val2.value == "Hello, World", f"拼接字符串 应为 'Hello, World', 实际 {val2.value}"
    print("  [+] 计算表达式(5) = 5*2+5 = 15")
    print("  [+] 拼接字符串('Hello', ', ', 'World') = 'Hello, World'")
    return True


def test_import_with_nested_calls():
    """测试嵌套导入后，导入的函数内部调用其他导入的函数"""
    print("\n" + "=" * 60)
    print("测试: 嵌套导入 - 被导入函数内部调用了其他导入函数")
    print("=" * 60)

    code = """
从 mod_advanced 导入《计算表达式》。

定义结果等于《计算表达式》(3)。
"""
    interp = run_source(code, search_paths=['test', '.'])

    val = interp.env.get('结果')
    assert val.value == 9, f"计算表达式(3) 应为 9, 实际 {val.value}"
    print("  [+] 计算表达式(3) = 3*2+3 = 9")
    return True


def test_import_nested_string_concat():
    """测试嵌套导入的字符串拼接功能"""
    print("\n" + "=" * 60)
    print("测试: 嵌套导入 - 字符串拼接")
    print("=" * 60)

    code = """
从 mod_advanced 导入《拼接字符串》。

定义结果等于《拼接字符串》("A", "B", "C")。
"""
    interp = run_source(code, search_paths=['test', '.'])

    val = interp.env.get('结果')
    assert val.value == "ABC", f"拼接字符串 应为 'ABC', 实际 {val.value}"
    print("  [+] 拼接字符串('A', 'B', 'C') = 'ABC'")
    return True


def test_import_nested_all_exports():
    """测试嵌套导入：全部导出"""
    print("\n" + "=" * 60)
    print("测试: 嵌套导入 - 全部导出")
    print("=" * 60)

    code = """
从 mod_advanced 导入《计算表达式》。

定义结果等于《计算表达式》(10)。
"""
    interp = run_source(code, search_paths=['test', '.'])

    val = interp.env.get('结果')
    assert val.value == 30, f"计算表达式(10) 应为 30, 实际 {val.value}"
    print("  [+] 计算表达式(10) = 10*2+10 = 30")
    return True


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == '__main__':
    tests = [
        test_import_basic,
        test_import_factorial,
        test_import_no_export,
        test_import_export_check,
        test_import_cache,
        test_import_via_file,
        test_import_nested,
        test_import_with_nested_calls,
        test_import_nested_string_concat,
        test_import_nested_all_exports,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n  [-] {test.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"模块系统测试: {passed} 通过, {failed} 失败")
    print("=" * 60)
    sys.exit(1 if failed > 0 else 0)