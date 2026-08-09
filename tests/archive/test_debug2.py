import sys
sys.path.insert(0, r'G:\dumategithub\light\src')
sys.path.insert(0, r'G:\dumategithub\light')

from lexer import Lexer

lexer = Lexer()

tests = [
    # Test A: Method line only
    ('《加》方法(x):', 'Test A: method header only'),
    # Test B: Just 方法
    ('方法', 'Test B: 方法 only'),
    # Test C: Assign with 结果
    ('结果 等于 结果 加 x。', 'Test C: assign result'),
    # Test D: Method header with newlines and body
    ('《加》方法(x):\n    结果 等于 结果 加 x。\n结束。', 'Test D: full method'),
    # Test E: What about after the { handling?
    ('《加》', 'Test E: just book title'),
    # Test F: method after book
    ('》方法', 'Test F: 方法 after 》'),
]

for i, (src, desc) in enumerate(tests):
    print(f"\n=== {desc} ===")
    print(f"Source: {repr(src)}")
    try:
        tokens = lexer.tokenize(src)
        for t in tokens:
            print(f"  {t}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()