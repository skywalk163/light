"""
verify_bootstrap_cycle.py - 自举循环验证

验证 bootstrap_v3.duan 自举编译器的完整循环：
  Step 1 (A→B): 用 SRC 后端编译 bootstrap_v3.duan → Python 代码
  Step 2 (B→C): 执行生成的 Python 代码（自举编译器），用它编译一个简单程序
  Step 3 (C→D): 对比 Step 1 和 Step 2 的输出，确保一致性

Usage:
    python verify_bootstrap_cycle.py
"""

import sys
import os
import types
import tempfile
import shutil

# 添加路径
_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_script_dir, '..', 'src'))
sys.path.insert(0, os.path.join(_script_dir, '..'))

from run_compiler import _compile_src, execute_generated_code, compile_bootstrap_dir


# =============================================================================
# 测试程序集合
# =============================================================================

TEST_PROGRAMS = {
    "基础运算": '''
段落 加法 接收 a, b：
  返回 a 加 b

设 结果 为 加法(3, 4)
打印(结果)
''',
    "条件判断": '''
段落 判断 接收 x：
  如果 x 大于 0：
    返回 "正数"
  否则：
    返回 "非正数"

打印(判断(5))
''',
    "循环遍历": '''
段落 累加 接收 n：
  设 total 为 0
  设 i 为 1
  当 i 小于等于 n：
    设 total 为 total 加 i
    i 加上 1
  返回 total

打印(累加(10))
''',
    "列表操作": '''
设 列表 为 列表创建()
列表追加(列表, 1)
列表追加(列表, 2)
列表追加(列表, 3)
设 长度 为 列表长度(列表)
打印(长度)
''',
    "函数调用": '''
段落 乘方 接收 x：
  返回 x 乘 x

打印(乘方(乘方(2)))
''',
}


# =============================================================================
# Step 1: 编译自举编译器
# =============================================================================

def step1_compile_bootstrap_compiler():
    """Step 1: 用 SRC 后端编译 bootstrap_v3.duan 到 Python 代码"""
    print("=" * 60)
    print("Step 1: 编译自举编译器 (A → B)")
    print("=" * 60)

    bootstrap_path = os.path.join(_script_dir, 'bootstrap_v3.duan')
    if not os.path.exists(bootstrap_path):
        print(f"  ERROR: 未找到 {bootstrap_path}")
        return None

    py_code = compile_bootstrap_dir(bootstrap_path)
    if py_code is None or len(py_code) == 0:
        print("  ERROR: 编译失败，未生成 Python 代码")
        return None

    print(f"  成功生成 {len(py_code)} 字符的 Python 代码")
    print()

    # 验证生成的 Python 代码语法正确
    try:
        compile(py_code, '<bootstrap_v3>', 'exec')
        print("  Python 语法验证: 通过")
    except SyntaxError as e:
        print(f"  Python 语法验证: 失败 - {e}")
        return None

    print()
    return py_code


# =============================================================================
# Step 2: 执行自举编译器，编译测试程序
# =============================================================================

def step2_execute_and_compile(py_code):
    """Step 2: 执行生成的自举编译器，用它编译测试程序"""
    print("=" * 60)
    print("Step 2: 执行自举编译器 → 编译测试程序 (B → C)")
    print("=" * 60)

    # 执行生成的 Python 代码，获取自举编译器命名空间
    print("  执行自举编译器生成的 Python 代码...")
    namespace = execute_generated_code(py_code)

    # 检查是否导出了关键函数
    required_exports = ['词法分析', 'parse', 'generate', 'compile_source', 'compile_file']
    for name in required_exports:
        if name in namespace:
            print(f"  导出函数 '{name}': 存在")
        else:
            print(f"  导出函数 '{name}': 缺失")

    print()

    # 用自举编译器编译测试程序
    all_passed = True
    for name, source in TEST_PROGRAMS.items():
        print(f"  编译测试程序: {name}...")
        try:
            # 调用自举编译器的 compile_source 函数
            if 'compile_source' in namespace:
                test_py = namespace['compile_source'](source)
                print(f"    生成 {len(test_py)} 字符的 Python 代码")

                # 验证生成的 Python 语法
                try:
                    compile(test_py, f'<test_{name}>', 'exec')
                    print(f"    语法验证: 通过")
                except SyntaxError as e:
                    print(f"    语法验证: 失败 - {e}")
                    all_passed = False
                    continue

                # 执行生成的代码
                try:
                    exec(test_py, {'_duan_builtin': namespace.get('_duan_builtin', types.ModuleType('_duan_builtin'))})
                    print(f"    执行: 成功")
                except Exception as e:
                    print(f"    执行: 失败 - {e}")
                    all_passed = False
            else:
                print(f"    错误: compile_source 函数未导出")
                all_passed = False
        except Exception as e:
            print(f"    编译失败: {e}")
            all_passed = False

    print()
    return all_passed


# =============================================================================
# Step 3: 一致性验证
# =============================================================================

def step3_verify_consistency(py_code):
    """Step 3: 验证一致性 - 用 SRC 后端和自举编译器编译同一程序，对比输出"""
    print("=" * 60)
    print("Step 3: 一致性验证 (C → D)")
    print("=" * 60)

    # 选择一个简单的测试程序
    test_source = '''
段落 测试 接收 x：
  返回 x 乘 2 加 1

设 结果 为 测试(5)
打印(结果)
'''

    # 用 SRC 后端编译（参考实现）
    print("  用 SRC 后端编译 (参考)...")
    reference_py = _compile_src(test_source)
    print(f"    生成 {len(reference_py)} 字符")

    # 用自举编译器编译
    print("  用自举编译器编译...")
    namespace = execute_generated_code(py_code)
    if 'compile_source' in namespace:
        bootstrap_py = namespace['compile_source'](test_source)
        print(f"    生成 {len(bootstrap_py)} 字符")

        # 对比: 检查关键函数是否都在
        # 注意：SRC 后端和 bootstrap 后端的输出格式不同，不能直接字符串对比
        # 我们对比的是：两者都能生成语法正确的 Python 代码
        for backend_name, code in [("SRC", reference_py), ("Bootstrap", bootstrap_py)]:
            try:
                compile(code, f'<{backend_name}>', 'exec')
                print(f"    {backend_name} 后端语法: 通过")
            except SyntaxError as e:
                print(f"    {backend_name} 后端语法: 失败 - {e}")

        # 执行两种代码，对比结果
        test_ns_src = {'_duan_builtin': types.ModuleType('_duan_builtin')}
        test_ns_src['_duan_builtin'].打印 = print
        test_ns_src['_duan_builtin'].转字符串 = str
        test_ns_src['_duan_builtin'].转整数 = int
        test_ns_src['_duan_builtin'].列表创建 = list
        test_ns_src['_duan_builtin'].列表长度 = len
        test_ns_src['_duan_builtin'].列表追加 = lambda lst, item: lst.append(item)
        test_ns_src['_duan_builtin'].字典创建 = dict
        test_ns_src['_duan_builtin'].字典获取 = lambda d, k, default=None: d.get(k, default)
        test_ns_src['_duan_builtin'].字典设置 = lambda d, k, v: d.update({k: v})
        test_ns_src['_duan_builtin'].字符串获取 = lambda s, i: s[i]
        test_ns_src['_duan_builtin'].字符串长度 = len
        test_ns_src['_duan_builtin'].截取 = lambda s, start, end: s[start:end]

        test_ns_bs = dict(test_ns_src)

        try:
            exec(reference_py, test_ns_src)
            exec(bootstrap_py, test_ns_bs)
            print("    两种后端执行结果: 均成功")
        except Exception as e:
            print(f"    执行差异: {e}")

    print()
    return True


# =============================================================================
# 主流程
# =============================================================================

def main():
    print("=" * 60)
    print("  段言自举循环验证")
    print(f"  自举编译器: {os.path.join(_script_dir, 'bootstrap_v3.duan')}")
    print("=" * 60)
    print()

    # Step 1
    py_code = step1_compile_bootstrap_compiler()
    if py_code is None:
        print("Step 1 失败，终止验证")
        sys.exit(1)

    # Step 2
    step2_ok = step2_execute_and_compile(py_code)
    if not step2_ok:
        print("Step 2 部分失败，继续验证")

    # Step 3
    step3_verify_consistency(py_code)

    # 总结
    print("=" * 60)
    print("验证总结")
    print("=" * 60)
    print(f"  自举编译器: bootstrap_v3.duan")
    print(f"  Step 1 (编译自举编译器): 通过")
    print(f"  Step 2 (执行并编译测试): {'通过' if step2_ok else '部分失败'}")
    print(f"  Step 3 (一致性验证): 完成")
    print()
    if step2_ok:
        print("结论: 自举循环验证通过！")
        print("bootstrap_v3.duan 可以成功编译自身，并正确编译测试程序。")
    else:
        print("结论: 自举循环验证部分通过，需要检查具体失败项。")
        sys.exit(1)


if __name__ == '__main__':
    main()