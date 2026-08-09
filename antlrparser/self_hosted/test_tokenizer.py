"""
光明自举分词器 - 测试脚本

加载并执行 tokenizer.light，验证分词结果。
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from light_interpreter import run_source, Interpreter, LightValue, LightFunction
from light_ast import SegmentDefinition, FunctionCall, StringLiteral


def unwrap_token(t):
    """将 LightValue 封装的 Token 字典转换为纯 Python 字典"""
    d = t.value if isinstance(t, LightValue) else t
    result = {}
    for k, v in d.items():
        if isinstance(v, LightValue):
            result[k] = v.value
        else:
            result[k] = v
    return result


def get_tokenizer_interp():
    """加载并解释 tokenizer.light，返回解释器"""
    tokenizer_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tokenizer.light')
    with open(tokenizer_path, 'r', encoding='utf-8') as f:
        tokenizer_source = f.read()
    return run_source(tokenizer_source), tokenizer_source


def test_tokenizer_basic():
    """测试自举分词器能否正确分词"""
    print("=" * 60)
    print("测试：自举分词器基础功能")
    print("=" * 60)
    
    interp, _ = get_tokenizer_interp()
    tokenizer_func = interp.env.get('分词器').value
    
    # 测试简单代码
    test_source = '定义甲等于1。'
    result = interp._call_function(tokenizer_func, [LightValue(test_source, '串')])
    
    tokens = result.value
    print(f"  [+] 输入: '{test_source}'")
    print(f"  [+] 输出: {len(tokens)} 个 Token")
    for t in tokens:
        print(f"      {unwrap_token(t)}")
    
    # 验证关键 Token
    assert len(tokens) >= 4, f"应该至少4个 Token, 实际 {len(tokens)}"
    
    # 检查第一个 Token 是 K_DEFINE
    first = unwrap_token(tokens[0])
    assert first['type'] == 'K_DEFINE', f"第一个 Token 应为 K_DEFINE, 实际 {first}"
    print(f"  [+] 验证通过！")
    return True


def test_tokenizer_self_hosting():
    """用自举分词器分词自身源码 - 真正的自举验证"""
    print("=" * 60)
    print("测试：自举验证 - 分词自身源码")
    print("=" * 60)
    
    interp, tokenizer_source = get_tokenizer_interp()
    tokenizer_func = interp.env.get('分词器').value
    
    # 用自己分词自己！
    result = interp._call_function(tokenizer_func, [LightValue(tokenizer_source, '串')])
    
    tokens = result.value
    print(f"  [+] tokenizer.light 源码长度: {len(tokenizer_source)} 字符")
    print(f"  [+] 自举分词结果: {len(tokens)} 个 Token")
    
    # 统计不同类型 Token 数量
    type_counts = {}
    for t in tokens:
        uw = unwrap_token(t)
        tt = uw.get('type', '?')
        type_counts[tt] = type_counts.get(tt, 0) + 1
    
    print(f"  [+] Token 类型分布:")
    for tt, cnt in sorted(type_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"      {tt}: {cnt}")
    
    assert len(tokens) > 50, f"自举分词结果太少: {len(tokens)}"
    print(f"  [+] 自举验证通过！")
    return True


def test_tokenizer_advanced():
    """测试更复杂的代码片段"""
    print("=" * 60)
    print("测试：复杂代码分词")
    print("=" * 60)
    
    interp, _ = get_tokenizer_interp()
    tokenizer_func = interp.env.get('分词器').value
    
    test_cases = [
        ("if", '如果甲大于乙那么：打印甲。结束。'),
        ("func_def", '《斐波那契》段(n): 如果n小于2那么：返回n。结束。结束。'),
        ("string", '打印"你好，世界！"。'),
        ("list", '定义列表等于【1, 2, 3】。'),
        ("dict", '定义映射等于_典("a", 1, "b", 2)。'),
        ("comment", '# 这是一行注释\n定义x等于1。'),
        ("block_comment", '```\n块注释\n```\n定义x等于1。'),
    ]
    
    all_pass = True
    for name, code in test_cases:
        try:
            result = interp._call_function(tokenizer_func, [LightValue(code, '串')])
            tokens = result.value
            print(f"  [+] [{name}] {len(tokens)} Token: {code[:30]}...")
            for t in tokens[:5]:
                print(f"      {unwrap_token(t)}")
            if len(tokens) > 5:
                print(f"      ... 共 {len(tokens)} 个")
        except Exception as e:
            print(f"  [-] [{name}] 失败: {e}")
            all_pass = False
    
    return all_pass


def test_direct_parse():
    """直接解析 tokenizer.light 并检查报错"""
    print("=" * 60)
    print("测试：直接解析 tokenizer.light")
    print("=" * 60)
    
    from light_visitor import LightParser
    
    tokenizer_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tokenizer.light')
    with open(tokenizer_path, 'r', encoding='utf-8') as f:
        tokenizer_source = f.read()
    
    parser = LightParser()
    module = parser.parse(tokenizer_source)
    
    if module is None:
        print(f"  [-] 解析失败！{len(parser.errors)} 个错误:")
        for err in parser.errors[:10]:
            print(f"      {err}")
        return False
    
    print(f"  [+] 解析成功:")
    print(f"      段落定义: {len(module.segments)}")
    print(f"      顶层语句: {len(module.statements)}")
    for seg in module.segments:
        print(f"      - 《{seg.name}》({len(seg.parameters)} 参数)")
    return True


if __name__ == '__main__':
    test_direct_parse()
    print()
    test_tokenizer_basic()
    print()
    test_tokenizer_advanced()
    print()
    test_tokenizer_self_hosting()