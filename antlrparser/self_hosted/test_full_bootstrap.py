"""测试完整自举流程"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source, LightValue, LightFunction


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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


def test_interpreter_executes_code():
    """测试光明版解释器执行代码"""
    print("=" * 60)
    print("测试：光明版解释器执行代码")
    print("=" * 60)
    
    # 加载分词器
    tok_interp, tok_func = load_tokenizer()
    
    # 加载解析器
    parse_interp, parse_func = load_parser()
    
    # 加载解释器
    interp_code = open(os.path.join(BASE_DIR, 'interpreter.light'), encoding='utf-8').read()
    interp = run_source(interp_code)
    
    # 测试代码
    test_code = """
定义x等于10。
定义y等于20。
定义z等于x加y。
打印(z)。
"""
    
    print(f"  测试代码:\n{test_code}")
    
    # 分词
    tokens = get_tokens(test_code, tok_interp, tok_func)
    print(f"  分词完成: {len(unwrap_value(tokens))} 个Token")
    
    # 解析
    parse_result = parse_interp._call_function(parse_func, [tokens])
    parsed = unwrap_value(parse_result)
    
    if parsed.get('_type') == 'Error':
        print(f"  解析失败: {parsed.get('message')}")
        return False
    
    ast = parsed.get('result')
    print(f"  解析成功: {len(ast.get('statements', []))} 个语句")
    
    # 将AST包装为LightValue
    ast_value = LightValue(ast, '典')
    
    # 调用解释器执行
    run_func = interp.env.get('_run')
    if run_func is None:
        print("  未找到 _run 函数")
        return False
    
    try:
        interp._call_function(run_func.value, [ast_value])
        output = interp.get_output()
        print(f"  执行结果: {output.strip()}")
        if "30" in output:
            print("  ✓ 解释器执行成功！")
            return True
        else:
            print("  ✗ 执行结果不正确")
            return False
    except Exception as e:
        print(f"  执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llvm_codegen():
    """测试光明版LLVM代码生成器"""
    print("=" * 60)
    print("测试：光明版LLVM代码生成器")
    print("=" * 60)
    
    # 加载分词器
    tok_interp, tok_func = load_tokenizer()
    
    # 加载解析器
    parse_interp, parse_func = load_parser()
    
    # 加载LLVM代码生成器
    llvm_code = open(os.path.join(BASE_DIR, 'llvm_codegen.light'), encoding='utf-8').read()
    llvm_interp = run_source(llvm_code)
    
    # 测试代码
    test_code = """
定义a等于1。
定义b等于2。
定义c等于a加b。
打印(c)。
"""
    
    print(f"  测试代码:\n{test_code}")
    
    # 分词
    tokens = get_tokens(test_code, tok_interp, tok_func)
    print(f"  分词完成")
    
    # 解析
    parse_result = parse_interp._call_function(parse_func, [tokens])
    parsed = unwrap_value(parse_result)
    
    if parsed.get('_type') == 'Error':
        print(f"  解析失败: {parsed.get('message')}")
        return False
    
    ast = parsed.get('result')
    print(f"  解析成功")
    
    # 将AST包装为LightValue
    ast_value = LightValue(ast, '典')
    
    # 调用编译函数
    compile_func = llvm_interp.env.get('编译')
    if compile_func is None:
        print("  未找到 编译 函数")
        return False
    
    try:
        result = llvm_interp._call_function(compile_func.value, [ast_value])
        llvm_ir = result.value if hasattr(result, 'value') else str(result)
        print(f"  LLVM IR 生成成功！")
        print(f"  生成的IR长度: {len(llvm_ir)} 字符")
        
        # 保存到文件
        with open("test_output.ll", "w", encoding="utf-8") as f:
            f.write(llvm_ir)
        print("  LLVM IR已保存到 test_output.ll")
        
        return True
    except Exception as e:
        print(f"  生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_self_hosted_interpreter():
    """测试完全自举：用光明解释器解释光明解释器"""
    print("=" * 60)
    print("测试：完全自举 - 光明解释器解释自身")
    print("=" * 60)
    
    # 加载分词器
    tok_interp, tok_func = load_tokenizer()
    
    # 加载解析器
    parse_interp, parse_func = load_parser()
    
    # 加载解释器
    interp_code = open(os.path.join(BASE_DIR, 'interpreter.light'), encoding='utf-8').read()
    interp = run_source(interp_code)
    
    print(f"  解释器源码长度: {len(interp_code)} 字符")
    
    # 分词解释器源码
    tokens = get_tokens(interp_code, tok_interp, tok_func)
    print(f"  分词完成: {len(unwrap_value(tokens))} 个Token")
    
    # 解析解释器源码
    parse_result = parse_interp._call_function(parse_func, [tokens])
    parsed = unwrap_value(parse_result)
    
    if parsed.get('_type') == 'Error':
        print(f"  解析失败: {parsed.get('message')}")
        return False
    
    ast = parsed.get('result')
    print(f"  解析成功: {len(ast.get('segments', []))} 个段落定义")
    
    # 将AST包装为LightValue
    ast_value = LightValue(ast, '典')
    
    # 调用解释器的_run函数来解释自身
    run_func = interp.env.get('_run')
    if run_func is None:
        print("  未找到 _run 函数")
        return False
    
    try:
        interp._call_function(run_func.value, [ast_value])
        output = interp.get_output()
        print(f"  自解释完成！")
        print(f"  输出: {'有输出' if output else '无输出（正常）'}")
        return True
    except Exception as e:
        print(f"  自解释失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("开始测试光明自举系统...")
    print()
    
    results = []
    
    results.append(("解释器执行代码", test_interpreter_executes_code()))
    print()
    
    results.append(("LLVM代码生成", test_llvm_codegen()))
    print()
    
    results.append(("完全自举测试", test_self_hosted_interpreter()))
    print()
    
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(p for _, p in results)
    print()
    if all_passed:
        print("所有测试通过！")
        sys.exit(0)
    else:
        print("部分测试失败！")
        sys.exit(1)