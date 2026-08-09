import sys
sys.path.insert(0, r'G:\dumategithub\light\src')
sys.path.insert(0, r'G:\dumategithub\light')

# Force reload
import importlib
import lexer as lexer_module
importlib.reload(lexer_module)
from lexer import Lexer

test_src = '《加》方法(x):\n    结果 等于 结果 加 x。\n结束。'
print(f"Testing: {repr(test_src)}")
print(f"Length: {len(test_src)}")
sys.stdout.flush()

try:
    lexer = Lexer()
    tokens = lexer.tokenize(test_src)
    print(f"SUCCESS! Got {len(tokens)} tokens")
    for t in tokens:
        print(f"  {t}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
sys.stdout.flush()