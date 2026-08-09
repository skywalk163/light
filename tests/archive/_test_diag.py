"""诊断：检查ANTLR token类型映射"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'antlrparser'))

from LightLangLexer import LightLangLexer
from light_tokenizer import LightLangTokenizer, create_antlr_token_stream, LightLangTokenSource
from antlr4 import Token as AntlrToken

print("=== ANTLR Lexer Symbolic Names ===")
lexer = LightLangLexer()
for i, name in enumerate(lexer.symbolicNames):
    if name and name != '<INVALID>':
        print(f"  {i}: {name}")

print()

# Check if '为' is properly tokenized
tokenizer = LightLangTokenizer()
tokens = tokenizer.tokenize('设甲为10。')
print("=== Custom Tokenizer Output for '设甲为10。' ===")
for t in tokens:
    print(f"  {t.type_name} = '{t.text}' (line {t.line}, col {t.column})")

# Check mapping
print()
print("=== Token Type Mapping (first 50) ===")
ts = LightLangTokenSource(tokens, lexer)
for name in ['K_SET', 'K_AS', 'K_DEFINE', 'K_EQUAL', 'K_IF', 'K_THEN', 'K_ELSE_IF', 'K_ELSE', 'K_END', 'K_FOREACH', 'K_WHILE']:
    mapped_type = ts._token_type_map.get(name, 'NOT FOUND')
    print(f"  {name} -> {mapped_type}")

# Now let's see what the parser actually sees
print()
print("=== Parser Token Stream ===")
token_stream = create_antlr_token_stream('设甲为10。', lexer)
token_stream.fill()
for tok in token_stream.tokens:
    if tok.type != -1:  # not EOF
        name = lexer.symbolicNames[tok.type] if tok.type < len(lexer.symbolicNames) else 'UNKNOWN'
        print(f"  Token({tok.type}) {name} = '{tok.text}' (line {tok.line})")