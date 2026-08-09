"""二次自举编译 v3：正确收敛性验证

两次编译都用同一源文件 bootstrap_level5.light：
1. level6_generated.py 编译 bootstrap_level5.light → out1
2. level6_self_compiled.py 编译 bootstrap_level5.light → out2
3. 比较 out1 和 out2 是否一致
"""
import sys
sys.path.insert(0, '.')

def 列表创建(*args): return list(args)
def 列表追加(lst, item): lst.append(item)
def 列表插入(lst, item): lst.append(item)
def 列表获取(lst, i): return lst[i]
def 列表长度(lst): return len(lst)
def 列表弹栈(lst):
    if len(lst) > 0: lst.pop()
def 字符串长度(s): return len(s)
def 字符串获取(s, i): return s[i]
def 截取(s, a, b): return s[a:b]
def 打印(*args): print(*args)
def 建(t, v): return [t, v]

ns = {
    '列表创建': 列表创建, '列表追加': 列表追加, '列表插入': 列表插入, '列表获取': 列表获取,
    '列表长度': 列表长度, '列表弹栈': 列表弹栈,
    '字符串长度': 字符串长度, '字符串获取': 字符串获取,
    '截取': 截取, '打印': 打印, '输出': 打印, '真': True, '假': False, '建': 建,
}

# 读取源文件 (两个编译器都用同一源)
with open('bootstrap/bootstrap_level5.light', 'r', encoding='utf-8') as f:
    light_code = f.read()

print(f"源码: bootstrap_level5.light ({len(light_code)} 字节)")
print()

# ===== 第一次编译：用 level6_generated.py =====
print("=" * 60)
print("第1次: level6_generated.py 编译 bootstrap_level5.light")
print("=" * 60)
with open('bootstrap/level6_generated.py', 'r', encoding='utf-8') as f:
    compiler1_code = f.read()
ns1 = dict(ns)
exec(compiler1_code, ns1)
编译1 = ns1['编译']

try:
    py_code1 = 编译1(light_code)
    print(f"✅ 编译成功! 生成代码: {len(py_code1)} 字节")
    try:
        compile(py_code1, '<string>', 'exec')
        print("✅ 语法正确")
    except SyntaxError as e:
        print(f"❌ 语法错误: {e}")
except Exception as e:
    print(f"❌ 编译失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ===== 第二次编译：用 level6_self_compiled.py =====
print("=" * 60)
print("第2次: level6_self_compiled.py 编译 bootstrap_level5.light")
print("=" * 60)
with open('bootstrap/level6_self_compiled.py', 'r', encoding='utf-8') as f:
    compiler2_code = f.read()
ns2 = dict(ns)
exec(compiler2_code, ns2)
编译2 = ns2['编译']

try:
    py_code2 = 编译2(light_code)
    print(f"✅ 编译成功! 生成代码: {len(py_code2)} 字节")
    try:
        compile(py_code2, '<string>', 'exec')
        print("✅ 语法正确")
    except SyntaxError as e:
        print(f"❌ 语法错误: {e}")
except Exception as e:
    print(f"❌ 编译失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ===== 收敛性验证 =====
print("=" * 60)
print("收敛性验证: 比较两次编译输出")
print("=" * 60)

def normalize(code):
    lines = code.split('\n')
    idx = 0
    while idx < len(lines) and (lines[idx].startswith('#') or lines[idx].strip() == ''):
        idx += 1
    return '\n'.join(lines[idx:])

norm1 = normalize(py_code1)
norm2 = normalize(py_code2)

if norm1 == norm2:
    print("✅ 收敛成功！两次编译输出完全一致")
else:
    print("❌ 收敛失败：两次编译输出有差异")
    lines1 = norm1.split('\n')
    lines2 = norm2.split('\n')
    diff_count = 0
    for i, (l1, l2) in enumerate(zip(lines1, lines2)):
        if l1 != l2:
            diff_count += 1
            if diff_count <= 10:
                print(f"  差异 {diff_count} (行 {i+1}):")
                print(f"    第1次: {l1[:120]}")
                print(f"    第2次: {l2[:120]}")
    if len(lines1) != len(lines2):
        print(f"  行数不同: 第1次 {len(lines1)} 行, 第2次 {len(lines2)} 行")
    print(f"  总差异数: {diff_count}")

print()
print(f"第1次编译: {len(py_code1)} 字节, {len(py_code1.split(chr(10)))} 行")
print(f"第2次编译: {len(py_code2)} 字节, {len(py_code2.split(chr(10)))} 行")

# 保存
with open('bootstrap/level6_out1.py', 'w', encoding='utf-8') as f:
    f.write(py_code1)
with open('bootstrap/level6_out2.py', 'w', encoding='utf-8') as f:
    f.write(py_code2)
print("✅ 已保存到 bootstrap/level6_out1.py 和 level6_out2.py")