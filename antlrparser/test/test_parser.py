"""
光明 ANTLR 解析器测试

测试 ANTLR 生成的词法分析器和语法解析器
使用自定义中文分词器进行词法分析
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 尝试导入生成的解析器
try:
    from light_parser.LightLangLexer import LightLangLexer
    from light_parser.LightLangParser import LightLangParser
    HAS_GENERATED_PARSER = True
except ImportError:
    HAS_GENERATED_PARSER = False

from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener

# 导入自定义分词器
from light_tokenizer import LightLangTokenizer, create_antlr_token_stream


class TestErrorListener(ErrorListener):
    """测试用错误监听器"""
    def __init__(self):
        super().__init__()
        self.errors = []
    
    def syntaxError(self, recognizer, offending_symbol, line, column, msg, e):
        self.errors.append(f"行{line}, 列{column}: {msg}")
    
    def has_errors(self):
        return len(self.errors) > 0


def tokenize_with_custom(source: str):
    """使用自定义分词器进行词法分析"""
    tokenizer = LightLangTokenizer()
    return tokenizer.tokenize(source)


def test_lexer_basic():
    """测试基本词法分析"""
    if not HAS_GENERATED_PARSER:
        print("  ⚠ 解析器未生成，跳过测试")
        assert True
        return
    
    source = "定义甲等于10。"
    tokens = tokenize_with_custom(source)
    token_names = [t.type_name for t in tokens if t.type_name != 'EOF']
    
    print(f"  Token序列: {' '.join(token_names)}")
    print(f"  共 {len(token_names)} 个 Token")
    assert len(token_names) > 0


def _test_parsing_sample(filepath: str):
    """测试解析样本文件（使用自定义分词器 + ANTLR 解析器）"""
    if not HAS_GENERATED_PARSER:
        print("  ⚠ 解析器未生成，跳过测试")
        return True
    
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    # 使用自定义分词器 + ANTLR 解析器
    input_stream = InputStream(source)
    antlr_lexer = LightLangLexer(input_stream)
    error_listener = TestErrorListener()
    
    token_stream = create_antlr_token_stream(source, antlr_lexer)
    
    parser = LightLangParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)
    
    tree = parser.program()
    
    if error_listener.has_errors():
        print(f"  ✗ 解析错误: {error_listener.errors}")
        return False
    
    print(f"  ✓ 解析成功")
    return True


def test_keyword_tokenization():
    """测试中文关键字分词（使用自定义分词器）"""
    if not HAS_GENERATED_PARSER:
        print("  ⚠ 解析器未生成，跳过测试")
        assert True
        return
    
    test_cases = [
        ("定义甲等于三", ["K_DEFINE", "ID", "K_EQUAL", "ID"]),
        ("如果甲大于十那么", ["K_IF", "ID", "K_GT", "ID", "K_THEN"]),
        ("返回甲加乙", ["K_RETURN", "ID", "K_PLUS", "ID"]),
        ("遍历列表", ["K_FOREACH", "ID"]),
        ("结束", ["K_END"]),
    ]
    
    for source, expected_types in test_cases:
        tokens = tokenize_with_custom(source)
        actual_types = [t.type_name for t in tokens if t.type_name != 'EOF']
        
        assert actual_types == expected_types, f"'{source}' 期望 {expected_types}, 实际 {actual_types}"
        print(f"  ✓ '{source}' -> {actual_types}")


def test_punctuation_dual_mode():
    """测试中英文标点双模式（使用自定义分词器）"""
    if not HAS_GENERATED_PARSER:
        print("  ⚠ 解析器未生成，跳过测试")
        assert True
        return
    
    cn_source = "定义甲等于三。"
    en_source = "定义甲等于三."
    
    cn_tokens = tokenize_with_custom(cn_source)
    en_tokens = tokenize_with_custom(en_source)
    
    cn_types = [t.type_name for t in cn_tokens if t.type_name != 'EOF']
    en_types = [t.type_name for t in en_tokens if t.type_name != 'EOF']
    
    assert cn_types == en_types, f"中英文标点不一致: 中文 {cn_types}, 英文 {en_types}"
    print(f"  ✓ 中英文标点双模式一致")


if __name__ == '__main__':
    print("=== 光明 ANTLR 解析器测试 ===\n")
    
    if not HAS_GENERATED_PARSER:
        print("[提示] 请先运行以下命令生成解析器:")
        print("  cd antlrparser && .venv\\Scripts\\activate && antlr4 -Dlanguage=Python3 LightLangLexer.g4 -o light_parser -no-listener -visitor")
        print("  antlr4 -Dlanguage=Python3 LightLangParser.g4 -o light_parser -no-listener -visitor\n")
    
    # 运行测试
    tests = [
        ("关键字分词测试", test_keyword_tokenization),
        ("标点双模式测试", test_punctuation_dual_mode),
        ("基本词法分析", test_lexer_basic),
    ]
    
    all_passed = True
    for name, test_fn in tests:
        print(f"[{name}]")
        try:
            test_fn()
            print(f"  ✓ 通过")
        except Exception as e:
            print(f"  ✗ 异常: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
        print()
    
    # 测试样本文件解析
    sample_dir = os.path.dirname(os.path.abspath(__file__))
    for fname in sorted(os.listdir(sample_dir)):
        if fname.endswith('.light'):
            filepath = os.path.join(sample_dir, fname)
            print(f"[解析样本: {fname}]")
            try:
                result = _test_parsing_sample(filepath)
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"  ✗ 异常: {e}")
                import traceback
                traceback.print_exc()
                all_passed = False
            print()
    
    if all_passed:
        print("=== 全部测试通过 ✅ ===")
    else:
        print("=== 部分测试失败 ❌ ===")
    
    sys.exit(0 if all_passed else 1)