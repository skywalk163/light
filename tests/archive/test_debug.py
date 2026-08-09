import sys
sys.path.insert(0, r'G:\dumategithub\light\src')
sys.path.insert(0, r'G:\dumategithub\light')

from lexer import Lexer

lexer = Lexer()

# Test various code snippets
tests = [
    # Test 1: Simple class
    '《计算器》类:\n    设 结果 为 0。\n结束。',
    # Test 2: Class with method
    '《计算器》类:\n    设 结果 为 0。\n    《加》方法(x):\n        结果 等于 结果 加 x。\n    结束。\n结束。',
    # Test 3: Just the method line
    '《加》方法(x):\n    结果 等于 结果 加 x。\n结束。',
    # Test 4: Method without class
    '《计算器》类:\n    设 结果 为 0。',
]

for i, test in enumerate(tests):
    print(f"\n=== Test {i+1} ===")
    print(f"Source: {repr(test[:50])}...")
    try:
        tokens = lexer.tokenize(test)
        for t in tokens:
            print(f"  {t}")
    except Exception as e:
        print(f"  ERROR: {e}")