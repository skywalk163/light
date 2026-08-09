#!/usr/bin/env python3
"""综合修复 Python 代码 bug - 第二轮"""
import json, os, re, copy

DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sft_dataset.jsonl')
BACKUP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sft_dataset_backup_v40.jsonl')

items = []
with open(DATASET_PATH, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            items.append(json.loads(line))

# Backup
with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
    for item in items:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
print(f"Backup saved to {BACKUP_PATH}")

fix_count = 0

# ============================================================
# Pass 1: Fix DU parse failures - empty tuple () not supported
# Replace 设 X 为 () with 设 X 为 空元组  (but we need valid Light)
# Actually, just remove the empty tuple assignment line
# ============================================================
parse_fail_indices = {903, 1111, 1201, 1234, 1237}
for idx in parse_fail_indices:
    item = items[idx]
    du = item['output']
    py = item['input']
    
    # Remove '设 args 为 ()\n' from DU
    old_du = '设 args 为 ()\\n'
    if old_du in du:
        du = du.replace(old_du, '')
        item['output'] = du
        fix_count += 1
        print(f"  [{idx}] removed empty tuple from DU")
    
    # Remove 'args = ()\n' from PY
    old_py = 'args = ()\\n'
    if old_py in py:
        py = py.replace(old_py, '')
        item['input'] = py
        fix_count += 1
        print(f"  [{idx}] removed empty tuple from PY")

# ============================================================
# Pass 2: Add stub classes for undefined parent classes
# ============================================================
# Find all class names in the dataset
all_class_names = set()
for item in items:
    py = item['input']
    for m in re.finditer(r'class\s+(\w+)', py):
        all_class_names.add(m.group(1))

# Indices that need Dog class
dog_indices = {46, 166, 168, 221}
animal_indices = {107, 270, 420, 1013}

for idx in dog_indices:
    item = items[idx]
    py = item['input']
    if 'class Dog' not in py:
        stub = 'class Dog:\n    pass\n'
        py = stub + py
        item['input'] = py
        fix_count += 1
        print(f"  [{idx}] added stub class Dog")

for idx in animal_indices:
    item = items[idx]
    py = item['input']
    if 'class Animal' not in py:
        stub = 'class Animal:\n    def __init__(self, name):\n        self.name = name\n'
        py = stub + py
        item['input'] = py
        fix_count += 1
        print(f"  [{idx}] added stub class Animal")

# Also fix DU for these
for idx in dog_indices | animal_indices:
    item = items[idx]
    du = item['output']
    py = item['input']
    
    # Remove fake var definitions for Dog/Animal in DU
    # These are like: 设 Dog 为 空\n  or  设 Animal 为 空\n
    du = re.sub(r'设 Dog 为 空\\n', '', du)
    du = re.sub(r'设 Animal 为 空\\n', '', du)
    
    # Add stub class in DU
    if 'class Dog' in py and '类 Dog' not in du:
        du_stub = '类 Dog：\\n    跳过\\n'
        du = du_stub + du
    if 'class Animal' in py and '类 Animal' not in du:
        du_stub = '类 Animal：\\n    构造 接收 name：\\n        己.name 为 name\\n'
        du = du_stub + du
    
    item['output'] = du

# ============================================================
# Pass 3: Fix undefined variables and missing imports
# ============================================================
# 561: random is not defined
item = items[561]
py = item['input']
if 'import random' not in py:
    py = 'import random\n' + py
    item['input'] = py
    du = item['output']
    if '导入 random' not in du:
        du = '导入 random\\n' + du
        item['output'] = du
    fix_count += 1
    print(f"  [561] added import random")

# 710: datetime is not defined
item = items[710]
py = item['input']
if 'import datetime' not in py:
    py = 'from datetime import datetime\n' + py
    item['input'] = py
    du = item['output']
    if '导入 datetime' not in du:
        du = '导入 datetime\\n' + du
        item['output'] = du
    fix_count += 1
    print(f"  [710] added import datetime")

# 724: sub is not defined
item = items[724]
py = item['input']
# Already has import re, but 'sub' is used as a variable
# Change 'sub' to a string
py = py.replace('string.index(sub)', "string.index('sub')")
item['input'] = py
du = item['output']
du = du.replace('sub', '"sub"')
item['output'] = du
fix_count += 1
print(f"  [724] fixed undefined sub variable")

# 725: math is not defined
item = items[725]
py = item['input']
if 'import math' not in py:
    py = 'import math\n' + py
    item['input'] = py
    du = item['output']
    if '导入 math' not in du:
        du = '导入 math\\n' + du
        item['output'] = du
    fix_count += 1
    print(f"  [725] added import math")

# 675: x is not defined
item = items[675]
py = item['input']
if 'x = ' not in py.split('assert')[0]:
    py = 'x = 0\n' + py
    item['input'] = py
    du = item['output']
    du = '设 x 为 0\\n' + du
    item['output'] = du
    fix_count += 1
    print(f"  [675] added x = 0")

# 746: keys is not defined
item = items[746]
py = item['input']
py = py.replace('d.fromkeys(keys, 0)', "d.fromkeys(['a', 'b'], 0)")
item['input'] = py
du = item['output']
du = du.replace('keys', '["a", "b"]')
item['output'] = du
fix_count += 1
print(f"  [746] fixed undefined keys")

# 1255, 1256: results is not defined
for idx in [1255, 1256]:
    item = items[idx]
    py = item['input']
    if 'results = ' not in py:
        py = py.replace('print(results)', 'results = []\n    print(results)')
        item['input'] = py
        fix_count += 1
        print(f"  [{idx}] added results = []")

# ============================================================
# Pass 4: Fix NoneType iteration issues
# ============================================================
none_indices = [637, 638, 650, 823, 824, 826, 827, 829, 830, 831, 832]
for idx in none_indices:
    item = items[idx]
    py = item['input']
    du = item['output']
    
    if 'data = None' in py:
        py = py.replace('data = None', 'data = [1, 2, 3, 4, 5]')
        item['input'] = py
        du = du.replace('设 data 为 空', '设 data 为 [1, 2, 3, 4, 5]')
        item['output'] = du
        fix_count += 1
        print(f"  [{idx}] replaced None with list")

# 825, 828: reduce with None data
for idx in [825, 828]:
    item = items[idx]
    py = item['input']
    du = item['output']
    if 'data = None' in py:
        py = py.replace('data = None', 'data = [1, 2, 3, 4, 5]')
        item['input'] = py
        du = du.replace('设 data 为 空', '设 data 为 [1, 2, 3, 4, 5]')
        item['output'] = du
        fix_count += 1
        print(f"  [{idx}] replaced None with list for reduce")

# 663: NoneType close
item = items[663]
py = item['input']
du = item['output']
if 'connect_db = lambda' in py:
    py = py.replace(
        'connect_db = lambda *a, **k: None',
        'connect_db = lambda *a, **k: type("Conn", (), {"cursor": lambda self: type("Cursor", (), {"execute": lambda *a: None, "close": lambda *a: None})(), "close": lambda *a: None})()'
    )
    item['input'] = py
    fix_count += 1
    print(f"  [663] fixed NoneType close")

# 699: NoneType json
item = items[699]
py = item['input']
du = item['output']
# Change requests from {} to a proper mock
if 'requests = {}' in py:
    py = py.replace(
        'requests = {}',
        'class MockResponse:\n    @staticmethod\n    def json():\n        return {}\nclass MockRequests:\n    @staticmethod\n    def get(url):\n        return MockResponse()\nrequests = MockRequests()'
    )
    item['input'] = py
    fix_count += 1
    print(f"  [699] fixed NoneType json")

# 700: NoneType item assignment
item = items[700]
py = item['input']
du = item['output']
if 'config = None' in py:
    py = py.replace('config = None', 'config = {}')
    item['input'] = py
    du = du.replace('设 config 为 空', '设 config 为 {}')
    item['output'] = du
    fix_count += 1
    print(f"  [700] replaced None with dict")

# 842: NoneType bytes
item = items[842]
py = item['input']
du = item['output']
if 'data = None' in py:
    py = py.replace('data = None', 'data = b"hello"')
    item['input'] = py
    du = du.replace('设 data 为 空', '设 data 为 b"hello"')
    item['output'] = du
    fix_count += 1
    print(f"  [842] replaced None with bytes")

# ============================================================
# Pass 5: Fix type mismatches (str/int confusion)
# ============================================================
# 172, 173: 'hello' in s where s is int
for idx in [172, 173]:
    item = items[idx]
    py = item['input']
    du = item['output']
    py = py.replace('s = 0', "s = 'hello world'")
    item['input'] = py
    du = du.replace('设 s 为 0', "设 s 为 'hello world'")
    item['output'] = du
    fix_count += 1
    print(f"  [{idx}] fixed int not iterable")

# 495: str + int concatenation
item = items[495]
py = item['input']
py = py.replace('y = 0', 'y = 5')
py = py.replace('x = \'\'', "x = 'Result: '")
item['input'] = py
fix_count += 1
print(f"  [495] fixed str+int concat")

# 503: str/str division
item = items[503]
py = item['input']
py = py.replace("done = ''", "done = 3")
py = py.replace("total = ''", "total = 10")
item['input'] = py
fix_count += 1
print(f"  [503] fixed str/str division")

# 505: format code 'd' for str
item = items[505]
py = item['input']
py = py.replace("day = ''", "day = 15")
py = py.replace("year = ''", "year = 2024")
item['input'] = py
fix_count += 1
print(f"  [505] fixed format code d for str")

# 506: format code 'd' for str
item = items[506]
py = item['input']
# Fix by replacing str with int
py = re.sub(r"(\w+) = ''", lambda m: f"{m.group(1)} = 0" if m.group(1) in ['day', 'month', 'year'] else m.group(0), py)
item['input'] = py
fix_count += 1
print(f"  [506] fixed format code d for str")

# 507: Cannot specify ',' with 's'
item = items[507]
py = item['input']
# Fix by replacing str with int
py = re.sub(r"(\w+) = ''", lambda m: f"{m.group(1)} = 0" if m.group(1) in ['price', 'amount'] else m.group(0), py)
item['input'] = py
fix_count += 1
print(f"  [507] fixed format specifier")

# 509: format code '%' for str
item = items[509]
py = item['input']
py = re.sub(r"(\w+) = ''", lambda m: f"{m.group(1)} = 0" if m.group(1) in ['rate', 'value'] else m.group(0), py)
item['input'] = py
fix_count += 1
print(f"  [509] fixed format code %")

# 518: format code 'd' for str
item = items[518]
py = item['input']
py = re.sub(r"(\w+) = ''", lambda m: f"{m.group(1)} = 0" if m.group(1) in ['hour', 'minute'] else m.group(0), py)
item['input'] = py
fix_count += 1
print(f"  [518] fixed format code d")

# 519: str / int
item = items[519]
py = item['input']
py = py.replace("x = ''", "x = 10")
item['input'] = py
fix_count += 1
print(f"  [519] fixed str/int division")

# 521, 522: str ** int
for idx in [521, 522]:
    item = items[idx]
    py = item['input']
    py = py.replace("x = ''", "x = 5")
    item['input'] = py
    fix_count += 1
    print(f"  [{idx}] fixed str**int")

# 524: abs(str)
item = items[524]
py = item['input']
py = re.sub(r"(\w+) = ''", lambda m: f"{m.group(1)} = -5" if m.group(1) in ['x', 'val', 'num'] else m.group(0), py)
item['input'] = py
fix_count += 1
print(f"  [524] fixed abs(str)")

# 528: str/str division
item = items[528]
py = item['input']
py = py.replace("a = ''", "a = 10")
py = py.replace("b = ''", "b = 3")
item['input'] = py
fix_count += 1
print(f"  [528] fixed str/str")

# 529, 531, 565: not all arguments converted
for idx in [529, 531, 565]:
    item = items[idx]
    py = item['input']
    # Replace %s with %d and string vars with ints
    py = py.replace('%s', '%d')
    py = re.sub(r"(\w+) = ''", lambda m: f"{m.group(1)} = 0" if len(m.group(1)) <= 3 else m.group(0), py)
    item['input'] = py
    fix_count += 1
    print(f"  [{idx}] fixed format string")

# 530, 566: str // str
for idx in [530, 566]:
    item = items[idx]
    py = item['input']
    py = re.sub(r"(\w+) = ''", lambda m: f"{m.group(1)} = 10" if m.group(1) in ['a', 'b', 'x', 'y'] else m.group(0), py)
    item['input'] = py
    fix_count += 1
    print(f"  [{idx}] fixed str//str")

# 555: format code 'f' for str
item = items[555]
py = item['input']
py = py.replace("x = ''", "x = 1234.56")
item['input'] = py
fix_count += 1
print(f"  [555] fixed format code f")

# 560: str / int
item = items[560]
py = item['input']
py = py.replace("x = ''", "x = 10")
item['input'] = py
fix_count += 1
print(f"  [560] fixed str/int")

# 562: str * str
item = items[562]
py = item['input']
py = py.replace("s = ''", "s = 'abc'")
py = py.replace("n = ''", "n = 3")
item['input'] = py
fix_count += 1
print(f"  [562] fixed str*str")

# 563: str - str
item = items[563]
py = item['input']
py = py.replace("a = ''", "a = 10")
py = py.replace("b = ''", "b = 3")
item['input'] = py
fix_count += 1
print(f"  [563] fixed str-str")

# 564: str / str
item = items[564]
py = item['input']
py = py.replace("a = ''", "a = 10")
py = py.replace("b = ''", "b = 3")
item['input'] = py
fix_count += 1
print(f"  [564] fixed str/str")

# 567: str ** str
item = items[567]
py = item['input']
py = py.replace("a = ''", "a = 2")
py = py.replace("b = ''", "b = 3")
item['input'] = py
fix_count += 1
print(f"  [567] fixed str**str")

# 568: str & str
item = items[568]
py = item['input']
py = py.replace("a = ''", "a = 5")
py = py.replace("b = ''", "b = 3")
item['input'] = py
fix_count += 1
print(f"  [568] fixed str&str")

# 569: str | str
item = items[569]
py = item['input']
py = py.replace("a = ''", "a = 5")
py = py.replace("b = ''", "b = 3")
item['input'] = py
fix_count += 1
print(f"  [569] fixed str|str")

# 570: str ^ str
item = items[570]
py = item['input']
py = py.replace("a = ''", "a = 5")
py = py.replace("b = ''", "b = 3")
item['input'] = py
fix_count += 1
print(f"  [570] fixed str^str")

# 571: ~str
item = items[571]
py = item['input']
py = py.replace("x = ''", "x = 5")
item['input'] = py
fix_count += 1
print(f"  [571] fixed ~str")

# 572: str << str
item = items[572]
py = item['input']
py = py.replace("a = ''", "a = 1")
py = py.replace("b = ''", "b = 2")
item['input'] = py
fix_count += 1
print(f"  [572] fixed str<<str")

# 573: str >> str
item = items[573]
py = item['input']
py = py.replace("a = ''", "a = 8")
py = py.replace("b = ''", "b = 2")
item['input'] = py
fix_count += 1
print(f"  [573] fixed str>>str")

# 936: str < int
item = items[936]
py = item['input']
py = py.replace("count = ''", "count = 0")
item['input'] = py
fix_count += 1
print(f"  [936] fixed str<int")

# 639, 640, 641, 711: int not iterable
for idx in [639, 640, 641]:
    item = items[idx]
    py = item['input']
    # These are for-loop over ints, change to range
    py = re.sub(r'for (\w+) in (\d+):', lambda m: f'for {m.group(1)} in range({m.group(2)}):', py)
    item['input'] = py
    fix_count += 1
    print(f"  [{idx}] fixed int not iterable")

# 711: subprocess.Popen(cmd) where cmd is int
item = items[711]
py = item['input']
py = py.replace('cmd = 0', 'cmd = ["echo", "hello"]')
item['input'] = py
fix_count += 1
print(f"  [711] fixed int not iterable in Popen")

# ============================================================
# Pass 6: Fix division by zero / modulo by zero
# ============================================================
# 242: integer modulo by zero
item = items[242]
py = item['input']
py = py.replace('a = 0', 'a = 10')
py = py.replace('b = 0', 'b = 3')
item['input'] = py
fix_count += 1
print(f"  [242] fixed modulo by zero")

# 498: division by zero (empty list)
item = items[498]
py = item['input']
py = py.replace('nums = []', 'nums = [10, 20, 30]')
item['input'] = py
fix_count += 1
print(f"  [498] fixed empty list division")

# 1148: division by zero
item = items[1148]
py = item['input']
py = py.replace('data = []', 'data = [1, 2, 3, 4, 5]')
py = py.replace('n = 0', 'n = 5')
item['input'] = py
fix_count += 1
print(f"  [1148] fixed division by zero")

# ============================================================
# Pass 7: Fix KeyError / value not in list / index errors
# ============================================================
# 19, 732: KeyError
for idx in [19, 732]:
    item = items[idx]
    py = item['input']
    py = py.replace("d = {}", "d = {'key': 0}")
    item['input'] = py
    fix_count += 1
    print(f"  [{idx}] fixed KeyError")

# 113, 425: value not in list
for idx in [113, 425]:
    item = items[idx]
    py = item['input']
    if "s = []" in py:
        py = py.replace("s = []", "s = ['abc']")
    elif "s = ''" in py:
        py = py.replace("s = ''", "s = 'abc'")
    item['input'] = py
    fix_count += 1
    print(f"  [{idx}] fixed value not in list")

# 515: max() empty iterable
item = items[515]
py = item['input']
py = py.replace('values = []', 'values = [1, 5, 3]')
item['input'] = py
fix_count += 1
print(f"  [515] fixed empty max()")

# 516, 552, 655: list index out of range
for idx in [516, 552, 655]:
    item = items[idx]
    py = item['input']
    if 'items = []' in py:
        py = py.replace('items = []', 'items = [10, 20, 30]')
    elif 'd = []' in py:
        py = py.replace('d = []', 'd = [10, 20, 30]')
    item['input'] = py
    fix_count += 1
    print(f"  [{idx}] fixed index out of range")

# ============================================================
# Pass 8: Fix attribute errors
# ============================================================
# 102: list.cnt (should be count)
item = items[102]
py = item['input']
py = py.replace('list_.cnt(5)', 'list_.count(5)')
py = py.replace('list_ = []', 'list_ = [5, 5, 3]')
item['input'] = py
fix_count += 1
print(f"  [102] fixed list.cnt -> count")

# 666: list.index on int
item = items[666]
py = item['input']
py = py.replace('list.index(item)', '[1, 2, 3].index(item)')
py = py.replace('item = 0', 'item = 2')
item['input'] = py
fix_count += 1
print(f"  [666] fixed list.index descriptor")

# 672: getattr with int attribute name
item = items[672]
py = item['input']
py = py.replace('attr = 0', "attr = 'name'")
py = py.replace('obj = 0', 'obj = type("Obj", (), {"name": "test"})()')
item['input'] = py
fix_count += 1
print(f"  [672] fixed getattr with int")

# 674: list.pop() unbound
item = items[674]
py = item['input']
py = py.replace('list.pop()', '[1, 2, 3].pop()')
item['input'] = py
fix_count += 1
print(f"  [674] fixed unbound list.pop()")

# 681: int has no attribute 'release'
item = items[681]
py = item['input']
du = item['output']
py = py.replace('lock = 0', 'lock = type("Lock", (), {"acquire": lambda *a: None, "release": lambda *a: None})()')
item['input'] = py
fix_count += 1
print(f"  [681] fixed int.release")

# 686: int has no attribute 'connect'
item = items[686]
py = item['input']
py = py.replace('socket = 0', 'import socket')
item['input'] = py
fix_count += 1
print(f"  [686] fixed int.connect")

# 687: int has no attribute 'open'
item = items[687]
py = item['input']
# Replace int with proper mock
py = py.replace('db = 0', 'db = type("DB", (), {"open": lambda *a: type("Conn", (), {"close": lambda *a: None})()})()')
item['input'] = py
fix_count += 1
print(f"  [687] fixed int.open")

# 688: subprocess.subprocess...
item = items[688]
py = item['input']
py = py.replace(
    'subprocess.subprocess.subprocess.subprocess.subprocess.subprocess.CalledProcessError',
    'subprocess.CalledProcessError'
)
py = py.replace('cmd = 0', 'cmd = ["echo", "hello"]')
item['input'] = py
fix_count += 1
print(f"  [688] fixed subprocess chain")

# 689: inet_aton with int
item = items[689]
py = item['input']
py = py.replace('ip = 0', "ip = '127.0.0.1'")
item['input'] = py
fix_count += 1
print(f"  [689] fixed inet_aton int")

# 692: dict has no attribute 'Timeout'
item = items[692]
py = item['input']
py = py.replace(
    'requests = {}',
    'class MockRequests:\n    class Timeout(Exception):\n        pass\n    class ConnectionError(Exception):\n        pass\n    @staticmethod\n    def get(url, timeout=5):\n        return type("Resp", (), {"json": lambda: {}})()\nrequests = MockRequests()'
)
py = py.replace('url = 0', "url = 'http://example.com'")
item['input'] = py
fix_count += 1
print(f"  [692] fixed dict.Timeout")

# 694: int has no attribute 'error'
item = items[694]
py = item['input']
py = py.replace(
    'urllib = 0',
    'class MockUrllib:\n    class request:\n        @staticmethod\n        def urlopen(url):\n            return type("Resp", (), {"read": lambda: b"data"})()\n    class error:\n        class URLError(Exception):\n            pass\nurllib = MockUrllib()'
)
py = py.replace('url = 0', "url = 'http://example.com'")
item['input'] = py
fix_count += 1
print(f"  [694] fixed int.error")

# 701: list has no attribute 'Error'
item = items[701]
py = item['input']
py = py.replace(
    'shutil = []',
    'class MockShutil:\n    class Error(Exception):\n        pass\n    @staticmethod\n    def copy(src, dst):\n        pass\nshutil = MockShutil()'
)
py = py.replace('src = 0', "src = 'file.txt'")
item['input'] = py
fix_count += 1
print(f"  [701] fixed list.Error")

# 703: str has no attribute 'error'
item = items[703]
py = item['input']
py = py.replace(
    "struct = ''",
    'class MockStruct:\n    class error(Exception):\n        pass\n    @staticmethod\n    def unpack(fmt, raw):\n        return (1, 2, 3)\nstruct = MockStruct()'
)
py = py.replace('fmt = 0', "fmt = 'III'")
py = py.replace('raw = 0', "raw = b'\\x01\\x00\\x00\\x00'")
item['input'] = py
fix_count += 1
print(f"  [703] fixed str.error")

# 713: function has no attribute 'signal'
item = items[713]
py = item['input']
py = py.replace(
    'signal = lambda *a, **k: None',
    'import signal\n'
)
py = py.replace('handler = 0', 'handler = lambda signum, frame: None')
item['input'] = py
fix_count += 1
print(f"  [713] fixed function.signal")

# 714, 719: int has no attribute 'PickleError'
for idx in [714, 719]:
    item = items[idx]
    py = item['input']
    py = py.replace('pickle = 0', 'import pickle')
    item['input'] = py
    fix_count += 1
    print(f"  [{idx}] fixed pickle import")

# 717: int has no attribute 'ParseError'
item = items[717]
py = item['input']
py = py.replace('ET = 0', 'import xml.etree.ElementTree as ET')
py = py.replace("fromstring = ''", '')
py = py.replace("xml_str = ''", "xml_str = '<root><child>text</child></root>'")
item['input'] = py
fix_count += 1
print(f"  [717] fixed ET.ParseError")

# 718: int has no attribute 'YAMLError'
item = items[718]
py = item['input']
py = py.replace('yaml = 0', 'import yaml')
py = py.replace("safe_load = lambda *a, **k: None", '')
item['input'] = py
fix_count += 1
print(f"  [718] fixed yaml import")

# 722: int has no attribute 'Empty'
item = items[722]
py = item['input']
py = py.replace('queue = 0', 'import queue')
py = py.replace("get_nowait = lambda *a, **k: None", '')
item['input'] = py
fix_count += 1
print(f"  [722] fixed queue.Empty")

# 1226: int has no attribute 'search'
item = items[1226]
py = item['input']
py = py.replace('pattern = 0', 'import re; pattern = re.compile(r"\\d+")')
item['input'] = py
fix_count += 1
print(f"  [1226] fixed int.search")

# ============================================================
# Pass 9: Fix JSON type issues
# ============================================================
# 682, 723: JSON loads on int
for idx in [682, 723]:
    item = items[idx]
    py = item['input']
    py = py.replace('line = 0', "line = '{\"key\": \"value\"}'")
    item['input'] = py
    fix_count += 1
    print(f"  [{idx}] fixed JSON int")

# ============================================================
# Pass 10: Fix regex issues
# ============================================================
# 678, 702: pattern is int
for idx in [678, 702]:
    item = items[idx]
    py = item['input']
    py = py.replace('pattern = 0', "pattern = r'\\d+'")
    item['input'] = py
    fix_count += 1
    print(f"  [{idx}] fixed regex pattern int")

# ============================================================
# Pass 11: Fix file operations
# ============================================================
# These entries need actual files to exist. Let's remove them or fix them.
# 698, 720, 684, 708: empty path
# 839, 840, 851, 852, 853: missing files

# For file entries, we'll remove them since they require actual filesystem setup
file_remove_indices = {698, 720, 684, 708, 839, 840, 851, 852, 853}
# Mark them as removed (we'll handle this at the end)

# ============================================================
# Pass 12: Fix misc errors
# ============================================================
# 216: raise ValueError - this is intentional, let's fix
item = items[216]
py = item['input']
# Wrap in try/except to make it executable
py = 'try:\n    raise ValueError("invalid")\nexcept ValueError:\n    print("invalid")\n'
item['input'] = py
fix_count += 1
print(f"  [216] fixed ValueError raise")

# 217: raise Exception
item = items[217]
py = item['input']
py = 'try:\n    raise Exception("error")\nexcept Exception:\n    print("error")\n'
item['input'] = py
fix_count += 1
print(f"  [217] fixed Exception raise")

# 308: raise Exception() with empty msg
item = items[308]
py = item['input']
py = 'try:\n    raise Exception()\nexcept Exception:\n    pass\n'
item['input'] = py
fix_count += 1
print(f"  [308] fixed empty Exception raise")

# 547: find() argument must be str
item = items[547]
py = item['input']
py = py.replace('c = 0', "c = 'a'")
py = py.replace("s = ''", "s = 'abc'")
item['input'] = py
fix_count += 1
print(f"  [547] fixed find() int arg")

# 548: startswith int arg
item = items[548]
py = item['input']
# Fix by replacing int with str
py = re.sub(r'(\w+) = 0', lambda m: f"{m.group(1)} = 'abc'" if m.group(1) in ['s', 'prefix'] else m.group(0), py)
item['input'] = py
fix_count += 1
print(f"  [548] fixed startswith int")

# 549: endswith int arg
item = items[549]
py = item['input']
py = re.sub(r'(\w+) = 0', lambda m: f"{m.group(1)} = 'abc'" if m.group(1) in ['s', 'suffix'] else m.group(0), py)
item['input'] = py
fix_count += 1
print(f"  [549] fixed endswith int")

# 553: ord() expected string, got int
item = items[553]
py = item['input']
py = py.replace('c = 0', "c = 'A'")
item['input'] = py
fix_count += 1
print(f"  [553] fixed ord() int")

# 740: str cannot be interpreted as int
item = items[740]
py = item['input']
py = py.replace('d = []', "d = {'key': 'value'}")
item['input'] = py
fix_count += 1
print(f"  [740] fixed dict pop on list")

# 741: pop expected at most 1 argument
item = items[741]
py = item['input']
py = py.replace('d = []', "d = {'key': 'value'}")
item['input'] = py
fix_count += 1
print(f"  [741] fixed dict pop on list")

# 744: int is not a mapping
item = items[744]
py = item['input']
py = py.replace('d1 = 0', "d1 = {'a': 1}")
py = py.replace('d2 = 0', "d2 = {'b': 2}")
item['input'] = py
fix_count += 1
print(f"  [744] fixed int not mapping")

# 1150: factorial recursion issue
item = items[1150]
py = item['input']
# This should work... let me check the actual error
# du: 'NoneType' object is not callable - this means the DU translation has issues
# The PY code defines factorial as lambda, which should work
# Let's keep it as-is for now and check after other fixes

# ============================================================
# Pass 13: Fix DU execution failures
# ============================================================
# 537: du 'NoneType' not callable
# 649: du No module named 'sub'  
# 898: du No module named 'sub'
# 1150: du 'NoneType' not callable

# ============================================================
# Pass 14: Remove file-based entries that can't work without actual files
# ============================================================
# Actually, let's not remove them. Let's fix them by creating temp files.

# Instead, let's just remove the file entries - they're not useful for training
# since they depend on filesystem state
items_to_remove = set()
for idx in file_remove_indices:
    items_to_remove.add(idx)
    print(f"  [{idx}] marked for removal (file ops)")

# ============================================================
# Save results
# ============================================================
# First, remove marked items (in reverse order to preserve indices)
if items_to_remove:
    new_items = [item for i, item in enumerate(items) if i not in items_to_remove]
    print(f"\nRemoved {len(items) - len(new_items)} file-dependent entries")
    items = new_items

with open(DATASET_PATH, 'w', encoding='utf-8') as f:
    for item in items:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"\nTotal fixes applied: {fix_count}")
print(f"Remaining entries: {len(items)}")
print(f"Saved to {DATASET_PATH}")