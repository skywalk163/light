"""最终测试套件 - 边界情况、自举测试和性能测试"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source, LightValue

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("光明解释器最终测试套件")
    print("=" * 70)
    
    all_passed = True
    
    # ========== 边界情况测试 ==========
    print("\n【第一部分：边界情况测试】")
    print("-" * 70)
    
    # 数学函数边界测试
    math_cases = [
        ('abs(0)', 0), ('abs(-0)', 0), ('sqrt(0)', 0), ('sqrt(1)', 1),
        ('pow(0, 0)', 1), ('pow(0, 1)', 0), ('pow(1, 0)', 1), ('pow(1, 100)', 1),
        ('round(0.5)', 0), ('round(1.5)', 2), ('max(-1, -2, -3)', -1), ('min(-1, -2, -3)', -3),
    ]
    
    print("测试：数学函数边界")
    for expr, expected in math_cases:
        try:
            interp = run_source(f'打印({expr})。')
            output = interp.get_output().strip()
            actual = float(output) if '.' in output else int(output)
            if actual == expected:
                print(f"  ✓ {expr} = {actual}")
            else:
                print(f"  ✗ {expr} = {actual}, 期望: {expected}")
                all_passed = False
        except Exception as e:
            print(f"  ✗ {expr} 异常: {e}")
            all_passed = False
    
    # 字符串函数边界测试
    print("\n测试：字符串函数边界")
    str_cases = [
        ('len("")', 0), ('len(" ")', 1), ('len("测试")', 2),
        ('trim("")', ""), ('trim("   ")', ""), ('trim("abc")', "abc"),
        ('substring("abc", 0, 0)', ""), ('substring("abc", 3, 5)', ""),
    ]
    
    for expr, expected in str_cases:
        try:
            interp = run_source(f'打印({expr})。')
            output = interp.get_output().strip()
            if output == str(expected):
                print(f"  ✓ {expr} = '{output}'")
            else:
                print(f"  ✗ {expr} = '{output}', 期望: '{expected}'")
                all_passed = False
        except Exception as e:
            print(f"  ✗ {expr} 异常: {e}")
            all_passed = False
    
    # 错误处理测试
    print("\n测试：错误处理边界")
    error_cases = [
        ('定义x等于未定义变量。', '未定义'),
        ('定义a等于10除0。', '除以零'),
        ('未知函数(1, 2, 3)。', '未定义'),
    ]
    
    for code, expected_error in error_cases:
        try:
            run_source(code)
            print(f"  ✗ 未捕获预期错误: {code}")
            all_passed = False
        except Exception as e:
            if expected_error in str(e):
                print(f"  ✓ 正确捕获错误: {expected_error}")
            else:
                print(f"  ✗ 错误类型不匹配: {e}")
                all_passed = False
    
    # ========== 自举测试 ==========
    print("\n【第二部分：自举测试】")
    print("-" * 70)
    
    print("测试：光明分词器解析光明代码")
    try:
        # 加载分词器
        tokenizer_path = os.path.join(BASE_DIR, 'tokenizer.light')
        with open(tokenizer_path, 'r', encoding='utf-8') as f:
            tokenizer_code = f.read()
        tok_interp = run_source(tokenizer_code)
        tok_func = tok_interp.env.get('分词器').value
        
        # 测试代码
        test_code = '定义x等于10加20。'
        tokens = tok_interp._call_function(tok_func, [LightValue(test_code, '串')])
        raw_tokens = []
        
        def unwrap(v):
            if isinstance(v, LightValue):
                return unwrap(v.value)
            if isinstance(v, dict):
                return {k: unwrap(v) for k, v in v.items()}
            if isinstance(v, list):
                return [unwrap(x) for x in v]
            return v
        
        token_list = unwrap(tokens)
        print(f"  ✓ 分词完成，共 {len(token_list)} 个Token")
        
        # 检查关键字识别
        token_types = [t['type'] for t in token_list]
        if 'K_DEFINE' in token_types and 'ID' in token_types and 'NUMBER' in token_types:
            print("  ✓ 正确识别关键字、标识符和数字")
        else:
            print("  ✗ Token类型识别不完全")
            all_passed = False
            
    except Exception as e:
        print(f"  ✗ 分词器测试失败: {e}")
        all_passed = False
    
    print("\n测试：光明解析器解析光明代码")
    try:
        # 加载解析器
        combined = ''
        for name in ['ast.light', 'parser.light']:
            path = os.path.join(BASE_DIR, name)
            with open(path, 'r', encoding='utf-8') as f:
                combined += f.read() + '\n'
        parse_interp = run_source(combined)
        parse_func = parse_interp.env.get('解析').value
        
        print("  ✓ 解析器加载完成")
        
        # 使用分词器获取tokens
        tokenizer_path = os.path.join(BASE_DIR, 'tokenizer.light')
        with open(tokenizer_path, 'r', encoding='utf-8') as f:
            tokenizer_code = f.read()
        tok_interp = run_source(tokenizer_code)
        tok_func = tok_interp.env.get('分词器').value
        
        test_code = '定义x等于1加2。打印(x)。'
        raw_tokens = tok_interp._call_function(tok_func, [LightValue(test_code, '串')])
        
        # 包装tokens
        token_list = unwrap(raw_tokens)
        wrapped = []
        for t in token_list:
            wrapped.append(LightValue({
                'type': LightValue(t['type'], '串'),
                'text': LightValue(t['text'], '串'),
                'line': LightValue(t['line'], '数'),
                'col': LightValue(t['col'], '数'),
            }, '典'))
        tokens_value = LightValue(wrapped, '列')
        
        # 解析
        parse_result = parse_interp._call_function(parse_func, [tokens_value])
        parsed = unwrap(parse_result)
        
        if parsed.get('_type') == 'Error':
            print(f"  ✗ 解析失败: {parsed.get('message')}")
            all_passed = False
        else:
            ast = parsed.get('result')
            stmt_count = len(ast.get('statements', []))
            print(f"  ✓ 解析成功，共 {stmt_count} 个语句")
            
    except Exception as e:
        print(f"  ✗ 解析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    # ========== 性能测试 ==========
    print("\n【第三部分：性能测试】")
    print("-" * 70)
    
    # 数学运算性能
    print("\n测试：数学运算性能")
    iterations = 10000
    code = f'''
定义sum等于0。
定义i等于0。
当i小于{iterations}：
  sum等于sum加i。
  i等于i加1。
结束。
打印(sum)。
'''
    start = time.time()
    interp = run_source(code)
    elapsed = time.time() - start
    ops_per_sec = iterations / elapsed
    print(f"  ✓ 循环 {iterations} 次完成")
    print(f"  耗时: {elapsed:.3f} 秒")
    print(f"  速度: {ops_per_sec:.1f} 次/秒")
    
    # 列表操作性能
    print("\n测试：列表操作性能")
    iterations = 5000
    code = f'''
定义arr等于【】。
定义i等于0。
当i小于{iterations}：
  listAppend(arr, i)。
  i等于i加1。
结束。
打印(listLen(arr))。
'''
    start = time.time()
    interp = run_source(code)
    elapsed = time.time() - start
    ops_per_sec = iterations / elapsed
    print(f"  ✓ 列表追加 {iterations} 次完成")
    print(f"  耗时: {elapsed:.3f} 秒")
    print(f"  速度: {ops_per_sec:.1f} 次/秒")
    
    # 标准库函数性能
    print("\n测试：标准库函数性能")
    iterations = 1000
    code = f'''
定义sum等于0。
定义i等于1。
当i小于{iterations}：
  sum等于sum加sqrt(i)。
  i等于i加1。
结束。
打印("完成")。
'''
    start = time.time()
    interp = run_source(code)
    elapsed = time.time() - start
    ops_per_sec = iterations / elapsed
    print(f"  ✓ sqrt调用 {iterations} 次完成")
    print(f"  耗时: {elapsed:.3f} 秒")
    print(f"  速度: {ops_per_sec:.1f} 次/秒")
    
    # Python对比
    print("\n测试：Python vs 光明性能对比")
    iterations = 100000
    
    py_start = time.time()
    py_sum = sum(i for i in range(iterations))
    py_elapsed = time.time() - py_start
    py_ops = iterations / py_elapsed
    
    code = f'''
定义sum等于0。
定义i等于0。
当i小于{iterations}：
  sum等于sum加i。
  i等于i加1。
结束。
打印(sum)。
'''
    light_start = time.time()
    interp = run_source(code)
    light_elapsed = time.time() - light_start
    light_ops = iterations / light_elapsed
    
    slowdown = py_ops / light_ops
    print(f"  Python: {py_ops:.0f} 次/秒")
    print(f"  光明: {light_ops:.0f} 次/秒")
    print(f"  光明比Python慢 {slowdown:.1f} 倍")
    
    # ========== 总结 ==========
    print("\n" + "=" * 70)
    print("测试结果总结")
    print("=" * 70)
    
    if all_passed:
        print("✓ 所有测试通过！")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1


def unwrap(v):
    """递归解包 LightValue"""
    if isinstance(v, LightValue):
        return unwrap(v.value)
    if isinstance(v, dict):
        return {k: unwrap(v) for k, v in v.items()}
    if isinstance(v, list):
        return [unwrap(x) for x in v]
    return v


if __name__ == '__main__':
    sys.exit(run_all_tests())