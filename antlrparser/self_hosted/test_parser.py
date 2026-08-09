"""
光明自举解析器 - 测试脚本

加载并执行 parser.light + ast.light，使用自举分词器进行完全自举验证。
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from light_interpreter import run_source, Interpreter, LightValue, LightFunction


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
    """加载自举分词器，返回 (解释器, 分词器函数)"""
    tokenizer_path = os.path.join(BASE_DIR, 'tokenizer.light')
    with open(tokenizer_path, 'r', encoding='utf-8') as f:
        source = f.read()
    interp = run_source(source)
    func = interp.env.get('分词器').value
    return interp, func


def get_tokens(code, tokenizer_interp, tokenizer_func):
    """用自举分词器获取代码的 Token 列表，返回 LightValue 包装的列"""
    result = tokenizer_interp._call_function(
        tokenizer_func, [LightValue(code, '串')]
    )
    raw_tokens = unwrap_value(result)  # plain Python list of dicts
    
    # 重新包装为 parser 需要的格式（LightValue 包装的字典）
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
    """加载 ast.light + parser.light，返回 (解释器, 解析函数)"""
    # 读取并合并 ast.light + parser.light
    combined = ''
    for name in ['ast.light', 'parser.light']:
        path = os.path.join(BASE_DIR, name)
        with open(path, 'r', encoding='utf-8') as f:
            combined += f.read() + '\n'
    
    # ANTLR 验证
    from light_visitor import LightParser
    antlr_parser = LightParser()
    module = antlr_parser.parse(combined)
    if module is None:
        print("合并源码 ANTLR 解析失败：")
        for err in antlr_parser.errors:
            print(f"  {err}")
        return None, None
    
    print(f"合并源码 ANTLR 解析成功！（{len(module.segments)} 个段落定义）")
    
    # 执行
    interp = run_source(combined)
    parse_func = interp.env.get('解析').value
    return interp, parse_func


def test_parse_simple_expression(tokenizer_interp, tokenizer_func):
    """测试解析简单的表达式：定义甲等于1加2。"""
    print("=" * 60)
    print("测试：解析简单表达式")
    print("=" * 60)
    
    interp, parse_func = load_parser()
    if parse_func is None:
        return False
    
    test_code = '定义甲等于1加2。'
    tokens_value = get_tokens(test_code, tokenizer_interp, tokenizer_func)
    
    print(f"  输入代码: '{test_code}'")
    
    try:
        result = interp._call_function(parse_func, [tokens_value])
        parsed = unwrap_value(result)
        
        if isinstance(parsed, dict):
            if parsed.get('_type') == 'Error':
                print(f"  解析出错: {parsed.get('message')}")
                return False
            if parsed.get('_type') == 'Result':
                inner = parsed.get('result', {})
                if isinstance(inner, dict):
                    stmts = inner.get('statements', [])
                    print(f"  AST 为 Module，包含 {len(stmts)} 个语句")
                    print(f"  解析成功！")
                    return True
        print(f"  未知结果格式: {type(parsed)}")
        return False
    except Exception as e:
        print(f"  解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    return False


def test_parse_function_def(tokenizer_interp, tokenizer_func):
    """测试解析函数定义：《加一》段(n): 返回n加1。结束。"""
    print("=" * 60)
    print("测试：解析函数定义")
    print("=" * 60)
    
    interp, parse_func = load_parser()
    if parse_func is None:
        return False
    
    test_code = '《加一》段(n): 返回n加1。结束。'
    tokens_value = get_tokens(test_code, tokenizer_interp, tokenizer_func)
    
    print(f"  输入代码: '{test_code}'")
    
    try:
        result = interp._call_function(parse_func, [tokens_value])
        parsed = unwrap_value(result)
        
        if isinstance(parsed, dict):
            if parsed.get('_type') == 'Error':
                print(f"  解析出错: {parsed.get('message')}")
                return False
            if parsed.get('_type') == 'Result':
                inner = parsed.get('result', {})
                segs = inner.get('segments', []) if isinstance(inner, dict) else []
                print(f"  AST 包含 {len(segs)} 个段落定义")
                if segs:
                    first_seg = segs[0]
                    print(f"    段落名: {first_seg.get('name', '?')}")
                print(f"  解析成功！")
                return True
        print(f"  未知结果格式: {type(parsed)}")
        return False
    except Exception as e:
        print(f"  解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    return False


def test_parse_if_statement(tokenizer_interp, tokenizer_func):
    """测试解析 If 语句"""
    print("=" * 60)
    print("测试：解析 If 语句")
    print("=" * 60)
    
    interp, parse_func = load_parser()
    if parse_func is None:
        return False
    
    test_code = '如果甲大于乙那么：打印甲。否则：打印乙。结束。'
    tokens_value = get_tokens(test_code, tokenizer_interp, tokenizer_func)
    
    print(f"  输入代码: '{test_code}'")
    
    try:
        result = interp._call_function(parse_func, [tokens_value])
        parsed = unwrap_value(result)
        
        if isinstance(parsed, dict):
            if parsed.get('_type') == 'Error':
                print(f"  解析出错: {parsed.get('message')}")
                return False
            if parsed.get('_type') == 'Result':
                print(f"  解析成功！")
                return True
        print(f"  未知结果格式: {type(parsed)}")
        return False
    except Exception as e:
        print(f"  解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    return False


def test_parse_while_loop(tokenizer_interp, tokenizer_func):
    """测试解析当循环"""
    print("=" * 60)
    print("测试：解析当循环")
    print("=" * 60)
    
    interp, parse_func = load_parser()
    if parse_func is None:
        return False
    
    test_code = '定义i等于0。当i小于10：打印i。i等于i加1。结束。'
    tokens_value = get_tokens(test_code, tokenizer_interp, tokenizer_func)
    
    print(f"  输入代码: '{test_code}'")
    
    try:
        result = interp._call_function(parse_func, [tokens_value])
        parsed = unwrap_value(result)
        
        if isinstance(parsed, dict):
            if parsed.get('_type') == 'Error':
                print(f"  解析出错: {parsed.get('message')}")
                return False
            if parsed.get('_type') == 'Result':
                print(f"  解析成功！")
                return True
        print(f"  未知结果格式: {type(parsed)}")
        return False
    except Exception as e:
        print(f"  解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    return False


def test_parse_self_hosting(tokenizer_interp, tokenizer_func):
    """完全自举验证：用自举解析器解析自身源码"""
    print("=" * 60)
    print("测试：完全自举 - 自举解析器解析自身源码")
    print("=" * 60)
    
    interp, parse_func = load_parser()
    if parse_func is None:
        return False
    
    # 用自举分词器分词 parser.light
    parser_path = os.path.join(BASE_DIR, 'parser.light')
    with open(parser_path, 'r', encoding='utf-8') as f:
        parser_source = f.read()
    
    print(f"  parser.light 长度: {len(parser_source)} 字符")
    
    tokens_value = get_tokens(parser_source, tokenizer_interp, tokenizer_func)
    print(f"  自举分词完成！")
    
    try:
        result = interp._call_function(parse_func, [tokens_value])
        parsed = unwrap_value(result)
        
        if isinstance(parsed, dict):
            if parsed.get('_type') == 'Error':
                print(f"  解析出错: {parsed.get('message')}")
                return False
            if parsed.get('_type') == 'Result':
                inner = parsed.get('result', {})
                if isinstance(inner, dict):
                    segs = inner.get('segments', [])
                    print(f"  解析出 {len(segs)} 个段落定义！")
                print(f"  完全自举验证通过！")
                return True
        print(f"  未知结果格式: {type(parsed)}")
        return False
    except Exception as e:
        print(f"  解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    return False


if __name__ == '__main__':
    # 只加载一次分词器
    print("正在加载自举分词器...")
    tok_interp, tok_func = load_tokenizer()
    print(f"  分词器加载完成！")
    print()
    
    test_parse_simple_expression(tok_interp, tok_func)
    print()
    test_parse_function_def(tok_interp, tok_func)
    print()
    test_parse_if_statement(tok_interp, tok_func)
    print()
    test_parse_while_loop(tok_interp, tok_func)
    print()
    test_parse_self_hosting(tok_interp, tok_func)
    print()
    print("所有测试完成！")