import sys
import threading
sys.path.insert(0, r'G:\dumategithub\light\src')
sys.path.insert(0, r'G:\dumategithub\light')

print("Testing import only...")
sys.stdout.flush()

result = []
def do_import():
    from lexer import Lexer
    result.append(Lexer)

t = threading.Thread(target=do_import)
t.start()
t.join(timeout=3)

if t.is_alive():
    print("IMPORT HUNG!")
    sys.stdout.flush()
else:
    print("Import OK, testing simple tokenize...")
    sys.stdout.flush()
    
    lexer = result[0]()
    test = '加五'
    print(f"Tokenizing: {repr(test)}")
    sys.stdout.flush()
    
    try:
        tokens = lexer.tokenize(test)
        for tok in tokens:
            print(f"  {tok}")
        sys.stdout.flush()
    except Exception as e:
        print(f"Error: {e}")
        sys.stdout.flush()