import sys
import threading
sys.path.insert(0, r'G:\dumategithub\light\src')
sys.path.insert(0, r'G:\dumategithub\light')

from lexer import Lexer

# Test just the method definition (no class)
test_src = '《加》方法(x):\n    结果 等于 结果 加 x。\n结束。'

print(f"Testing: {repr(test_src)}")
sys.stdout.flush()

result = []
error = []

def run_test():
    try:
        lexer = Lexer()
        tokens = lexer.tokenize(test_src)
        result.append(tokens)
    except Exception as e:
        error.append(str(e))

t = threading.Thread(target=run_test)
t.start()
t.join(timeout=5)

if t.is_alive():
    print("TIMEOUT - lexer hung!")
    sys.stdout.flush()
elif error:
    print(f"ERROR: {error[0]}")
    sys.stdout.flush()
else:
    print("SUCCESS!")
    for tok in result[0]:
        print(f"  {tok}")
    sys.stdout.flush()