"""全面测试套件 - 边界情况、自举测试和性能测试"""
import sys
import os
import time
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source, LightValue

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ==================== 边界情况测试 ====================

def test_math_edge_cases():
    """测试数学函数边界情况"""
    print("=" * 70)
    print("测试：数学函数边界情况")
    print("=" * 70)
    
    test_cases = [
        # 边界值测试
        ('abs(0)', 0),
        ('abs(-0)', 0),
        ('sqrt(0)', 0),
        ('sqrt(1)', 1),
        ('pow(0, 0)', 1),
        ('pow(0, 1)', 0),
        ('pow(1, 0)', 1),
        ('pow(1, 100)', 1),
        ('pow(2, 0)', 1),
        ('round(0.5)', 0),
        ('round(1.5)', 2),
        ('round(-0.5)', 0),
        ('round(-1.5)', -2),
        ('max(1, 1, 1)', 1),
        ('min(1, 1, 1)', 1),
        ('max(-1, -2, -3)', -1),
        ('min(-1, -2, -3)', -3),
    ]
    
    passed = 0
    failed = 0
    
    for expr, expected in test_cases:
        try:
            code = f'打印({expr})。'
            interp = run_source(code)
            output = interp.get_output().strip()
            actual = float(output) if '.' in output else int(output)
            if actual == expected:
                passed += 1
                print(f"  ✓ {expr} = {actual}")
            else:
                failed += 1
                print(f"  ✗ {expr} = {actual}, 期望: {expected}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {expr} 异常: {e}")
    
    print(f"\n  结果: {passed}/{len(test_cases)} 通过")
    return failed == 0


def test_string_edge_cases():
    """测试字符串函数边界情况"""
    print("\n" + "=" * 70)
    print("测试：字符串函数边界情况")
    print("=" * 70)
    
    test_cases = [
        ('len("")', 0),
        ('len(" ")', 1),
        ('len("测试")', 2),
        ('trim("")', ""),
        ('trim("   ")', ""),
        ('trim("  abc  ")', "abc"),
        ('trim("abc")', "abc"),
        ('substring("abc", 0, 0)', ""),
        ('substring("abc", 0, 1)', "a"),
        ('substring("abc", 1, 3)', "bc"),
        ('substring("abc", 3, 3)', ""),
        ('substring("abc", 3, 5)', ""),
    ]
    
    passed = 0
    failed = 0
    
    for expr, expected in test_cases:
        try:
            code = f'打印({expr})。'
            interp = run_source(code)
            output = interp.get_output().strip()
            if output == str(expected):
                passed += 1
                print(f"  ✓ {expr} = '{output}'")
            else:
                failed += 1
                print(f"  ✗ {expr} = '{output}', 期望: '{expected}'")
        except Exception as e:
            failed += 1
            print(f"  ✗ {expr} 异常: {e}")
    
    print(f"\n  结果: {passed}/{len(test_cases)} 通过")
    return failed == 0


def test_list_edge_cases():
    """测试列表函数边界情况"""
    print("\n" + "=" * 70)
    print("测试：列表函数边界情况")
    print("=" * 70)
    
    test_code = '''
打印("=== 空列表测试 ===")。
定义empty等于【】。
打印("空列表长度: "加listLen(empty))。

打印("\\n=== 单元素列表 ===")。
定义single等于【42】。
打印("单元素长度: "加listLen(single))。
listReverse(single)。
打印("反转后: "加single[0])。

打印("\\n=== 重复元素 ===")。
定义dup等于【1, 2, 2, 3, 2】。
打印("indexOf(dup, 2) = "加listIndexOf(dup, 2))。
打印("listContains(dup, 2) = "加listContains(dup, 2))。
打印("listContains(dup, 4) = "加listContains(dup, 4))。

打印("\\n=== 边界索引 ===")。
定义arr等于【10, 20, 30, 40, 50】。
定义slice1等于listSlice(arr, 0, 5)。
打印("slice(0,5)长度: "加listLen(slice1))。
定义slice2等于listSlice(arr, 2, 2)。
打印("slice(2,2)长度: "加listLen(slice2))。
定义slice3等于listSlice(arr, 1, 4)。
打印("slice(1,4)[0] = "加slice3[0])。

打印("\\n=== 列表拼接 ===")。
定义a等于【1,2,3】。
定义b等于【4,5,6】。
定义c等于listConcat(a, b)。
打印("concat长度: "加listLen(c))。
打印("concat[3] = "加c[3])。
'''
    
    try:
        with open(os.path.join(BASE_DIR, 'stdlib.light'), 'r', encoding='utf-8') as f:
            stdlib_code = f.read()
        
        full_code = stdlib_code + '\n\n' + test_code
        interp = run_source(full_code)
        output = interp.get_output()
        print(output)
        
        # 验证关键结果
        expected_outputs = [
            '空列表长度: 0',
            '单元素长度: 1',
            '反转后: 42',
            'indexOf(dup, 2) = 1',
            'listContains(dup, 2) = 真',
            'listContains(dup, 4) = 假',
            'slice(0,5)长度: 5',
            'slice(2,2)长度: 0',
            'slice(1,4)[0] = 20',
            'concat长度: 6',
            'concat[3] = 4',
        ]
        
        all_passed = all(expected in output for expected in expected_outputs)
        if all_passed:
            print("  ✓ 所有边界情况测试通过")
            return True
        else:
            print("  ✗ 部分测试失败")
            return False
    except Exception as e:
        print(f"  ✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling_cases():
    """测试错误处理边界情况"""
    print("\n" + "=" * 70)
    print("测试：错误处理边界情况")
    print("=" * 70)
    
    test_cases = [
        # (代码, 预期错误关键词)
        ('定义x等于未定义变量。', '未定义'),
        ('定义a等于10除0。', '除以零'),
        ('未知函数(1, 2, 3)。', '未定义'),
    ]
    
    passed = 0
    failed = 0
    
    for code, expected_error in test_cases:
        try:
            run_source(code)
            failed += 1
            print(f"  ✗ 未捕获预期错误: {code}")
        except Exception as e:
            error_str = str(e)
            if expected_error in error_str:
                passed += 1
                print(f"  ✓ 正确捕获错误: {expected_error}")
            else:
                failed += 1
                print(f"  ✗ 错误类型不匹配: 得到 '{error_str}', 期望 '{expected_error}'")
    
    print(f"\n  结果: {passed}/{len(test_cases)} 通过")
    return failed == 0


# ==================== 完整自举测试 ====================

def unwrap_value(v):
    """递归解包 LightValue"""
    if isinstance(v, LightValue):
        return unwrap_value(v.value)
    if isinstance(v, dict):
        return {k: unwrap_value(v) for k, v in v.items()}
    if isinstance(v, list):
        return [unwrap_value(x) for x in v]
    return v


def load_tokenizer():
    """加载自举分词器"""
    tokenizer_path = os.path.join(BASE_DIR, 'tokenizer.light')
    with open(tokenizer_path, 'r', encoding='utf-8') as f:
        source = f.read()
    interp = run_source(source)
    func = interp.env.get('分词器').value
    return interp, func


def get_tokens(code, tokenizer_interp, tokenizer_func):
    """用自举分词器获取Token列表"""
    result = tokenizer_interp._call_function(
        tokenizer_func, [LightValue(code, '串')]
    )
    raw_tokens = unwrap_value(result)
    wrapped = []
    for t in raw_tokens:
        wrapped.append(LightValue({
            'type': LightValue(t['type'], '串'),
            'text': LightValue(t['text'], '串'),
            'line': LightValue(t['line'], '数'),
            'col': LightValue(t['col'], '数'),
        }, '典'))
    return LightValue(wrapped, '列')


def load_parser():
    """加载 ast.light + parser.light"""
    combined = ''
    for name in ['ast.light', 'parser.light']:
        path = os.path.join(BASE_DIR, name)
        with open(path, 'r', encoding='utf-8') as f:
            combined += f.read() + '\n'
    interp = run_source(combined)
    parse_func = interp.env.get('解析').value
    return interp, parse_func


def test_full_bootstrap():
    """测试完全自举：用光明解释器解释光明代码"""
    print("\n" + "=" * 70)
    print("测试：完整自举 - 光明解释器解释光明代码")
    print("=" * 70)
    
    try:
        # 加载分词器
        print("  1. 加载分词器...")
        tok_interp, tok_func = load_tokenizer()
        print("     ✓ 分词器加载完成")
        
        # 加载解析器
        print("  2. 加载解析器...")
        parse_interp, parse_func = load_parser()
        print("     ✓ 解析器加载完成")
        
        # 加载解释器
        print("  3. 加载解释器...")
        interp_code = open(os.path.join(BASE_DIR, 'interpreter.light'), encoding='utf-8').read()
        interp = run_source(interp_code)
        print(f"     ✓ 解释器加载完成 ({len(interp_code)} 字符)")
        
        # 加载标准库
        print("  4. 加载标准库...")
        stdlib_code = open(os.path.join(BASE_DIR, 'stdlib.light'), encoding='utf-8').read()
        # 先运行标准库初始化
        stdlib_interp = run_source(stdlib_code)
        print(f"     ✓ 标准库加载完成 ({len(stdlib_code)} 字符)")
        
        # 综合测试代码 - 测试所有增强功能
        test_code = """
打印("=== 自举测试：综合功能 ===")。

打印("\\n1. 数学函数测试")。
定义pi等于3.14159。
打印("abs(-100) = "加abs(0减100))。
打印("sqrt(25) = "加sqrt(25))。
打印("pow(2, 8) = "加pow(2, 8))。
打印("round(pi) = "加round(pi))。

打印("\\n2. 字符串函数测试")。
定义s等于"  Hello World  "。
打印("len(s) = "加len(s))。
打印("trim(s) = '"加trim(s)加"'")。
打印("substring(s, 2, 7) = '"加substring(s, 2, 7)加"'")。

打印("\\n3. 列表函数测试")。
定义arr等于【10, 20, 30, 40, 50】。
打印("列表长度: "加listLen(arr))。
listAppend(arr, 60)。
printDebug("append后", listLen(arr))。

打印("\\n4. 错误处理测试")。
assert(listLen(arr)等于6, "列表长度应为6")。
printDebug("断言通过", 真)。

打印("\\n=== 自举测试完成！ ===")。
"""
        
        print("  5. 执行自举测试代码...")
        
        # 分词
        tokens = get_tokens(test_code, tok_interp, tok_func)
        print(f"     ✓ 分词完成 ({len(unwrap_value(tokens))} 个Token)")
        
        # 解析
        parse_result = parse_interp._call_function(parse_func, [tokens])
        parsed = unwrap_value(parse_result)
        
        if parsed.get('_type') == 'Error':
            print(f"     ✗ 解析失败: {parsed.get('message')}")
            return False
        
        ast = parsed.get('result')
        print(f"     ✓ 解析成功 ({len(ast.get('statements', []))} 个语句)")
        
        # 将AST包装为LightValue
        ast_value = LightValue(ast, '典')
        
        # 调用解释器执行
        run_func = interp.env.get('_run')
        if run_func is None:
            print("     ✗ 未找到 _run 函数")
            return False
        
        interp._call_function(run_func.value, [ast_value])
        output = interp.get_output()
        print(f"     ✓ 执行完成")
        
        # 验证结果
        expected_checks = [
            'abs(-100) = 100',
            'sqrt(25) = 5',
            'pow(2, 8) = 256',
            'len(s) = 15',
            'trim(s) = \'Hello World\'',
            'substring(s, 2, 7) = \'Hello\'',
            '列表长度: 5',
            'DEBUG: append后 = 6',
            'DEBUG: 断言通过 = True',
            '自举测试完成',
        ]
        
        all_passed = True
        for check in expected_checks:
            if check not in output:
                print(f"     ✗ 缺失预期输出: {check}")
                all_passed = False
        
        if all_passed:
            print("\n     ✓ 所有自举测试通过！")
            print(f"     输出:\n{output}")
        
        return all_passed
        
    except Exception as e:
        print(f"  ✗ 自举测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== 性能测试 ====================

def test_performance_math():
    """测试数学运算性能"""
    print("\n" + "=" * 70)
    print("测试：数学运算性能")
    print("=" * 70)
    
    iterations = 10000
    
    test_code = f'''
定义sum等于0。
定义i等于0。
当i小于{iterations}：
  sum等于sum加i。
  i等于i加1。
结束。
打印("循环完成，sum = "加sum)。
'''
    
    start_time = time.time()
    interp = run_source(test_code)
    elapsed = time.time() - start_time
    
    output = interp.get_output()
    expected_sum = iterations * (iterations - 1) // 2
    
    if f"sum = {expected_sum}" in output:
        ops_per_sec = iterations / elapsed
        print(f"  ✓ 循环 {iterations} 次完成")
        print(f"  耗时: {elapsed:.3f} 秒")
        print(f"  运算速度: {ops_per_sec:.1f} 次/秒")
        return True, elapsed, ops_per_sec
    else:
        print(f"  ✗ 结果错误")
        return False, elapsed, 0


def test_performance_list():
    """测试列表操作性能"""
    print("\n" + "=" * 70)
    print("测试：列表操作性能")
    print("=" * 70)
    
    iterations = 5000
    
    test_code = f'''
定义arr等于【】。
定义i等于0。
当i小于{iterations}：
  listAppend(arr, i)。
  i等于i加1。
结束。
打印("列表长度 = "加listLen(arr))。
'''
    
    start_time = time.time()
    interp = run_source(test_code)
    elapsed = time.time() - start_time
    
    output = interp.get_output()
    
    if f"列表长度 = {iterations}" in output:
        ops_per_sec = iterations / elapsed
        print(f"  ✓ 列表追加 {iterations} 次完成")
        print(f"  耗时: {elapsed:.3f} 秒")
        print(f"  操作速度: {ops_per_sec:.1f} 次/秒")
        return True, elapsed, ops_per_sec
    else:
        print(f"  ✗ 结果错误")
        return False, elapsed, 0


def test_performance_stdlib():
    """测试标准库函数性能"""
    print("\n" + "=" * 70)
    print("测试：标准库函数性能")
    print("=" * 70)
    
    iterations = 1000
    
    test_code = f'''
定义sum等于0。
定义i等于1。
当i小于{iterations}：
  sum等于sum加sqrt(i)。
  i等于i加1。
结束。
打印("sqrt累加完成")。
'''
    
    start_time = time.time()
    interp = run_source(test_code)
    elapsed = time.time() - start_time
    
    output = interp.get_output()
    
    if "sqrt累加完成" in output:
        ops_per_sec = iterations / elapsed
        print(f"  ✓ sqrt 调用 {iterations} 次完成")
        print(f"  耗时: {elapsed:.3f} 秒")
        print(f"  调用速度: {ops_per_sec:.1f} 次/秒")
        return True, elapsed, ops_per_sec
    else:
        print(f"  ✗ 执行失败")
        return False, elapsed, 0


def test_performance_comparison():
    """性能对比测试"""
    print("\n" + "=" * 70)
    print("测试：Python vs 光明解释器性能对比")
    print("=" * 70)
    
    iterations = 100000
    
    # Python原生性能
    print("  1. Python原生循环:")
    py_start = time.time()
    py_sum = sum(i for i in range(iterations))
    py_elapsed = time.time() - py_start
    py_ops = iterations / py_elapsed
    print(f"     结果: {py_sum}")
    print(f"     耗时: {py_elapsed:.3f} 秒")
    print(f"     速度: {py_ops:.1f} 次/秒")
    
    # 光明解释器性能
    print("\n  2. 光明解释器循环:")
    test_code = f'''
定义sum等于0。
定义i等于0。
当i小于{iterations}：
  sum等于sum加i。
  i等于i加1。
结束。
打印(sum)。
'''
    light_start = time.time()
    interp = run_source(test_code)
    light_elapsed = time.time() - light_start
    light_ops = iterations / light_elapsed
    output = interp.get_output().strip()
    print(f"     结果: {output}")
    print(f"     耗时: {light_elapsed:.3f} 秒")
    print(f"     速度: {light_ops:.1f} 次/秒")
    
    # 计算慢多少倍
    slowdown = py_ops / light_ops
    print(f"\n  3. 性能对比:")
    print(f"     光明解释器比Python原生慢 {slowdown:.1f} 倍")
    
    return True


# ==================== 主测试函数 ====================

def main():
    """运行所有测试"""
    print("=" * 70)
    print("光明解释器综合测试套件")
    print("=" * 70)
    
    all_passed = True
    
    # 边界情况测试
    print("\n" + "=" * 70)
    print("【第一部分：边界情况测试】")
    print("=" * 70)
    
    tests = [
        ("数学函数边界", test_math_edge_cases),
        ("字符串函数边界", test_string_edge_cases),
        ("列表函数边界", test_list_edge_cases),
        ("错误处理边界", test_error_handling_cases),
    ]
    
    for name, test_func in tests:
        if not test_func():
            all_passed = False
    
    # 完整自举测试
    print("\n" + "=" * 70)
    print("【第二部分：完整自举测试】")
    print("=" * 70)
    
    if not test_full_bootstrap():
        all_passed = False
    
    # 性能测试
    print("\n" + "=" * 70)
    print("【第三部分：性能测试】")
    print("=" * 70)
    
    perf_results = []
    perf_results.append(("数学运算", test_performance_math()))
    perf_results.append(("列表操作", test_performance_list()))
    perf_results.append(("标准库函数", test_performance_stdlib()))
    
    for name, (passed, elapsed, ops) in perf_results:
        if not passed:
            all_passed = False
    
    # 性能对比
    test_performance_comparison()
    
    # 总结
    print("\n" + "=" * 70)
    print("测试结果总结")
    print("=" * 70)
    
    if all_passed:
        print("✓ 所有测试通过！")
        return 0
    else:
        print("✗ 部分测试失败！")
        return 1


if __name__ == '__main__':
    sys.exit(main())