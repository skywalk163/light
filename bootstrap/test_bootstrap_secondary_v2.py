"""二次自举编译 v2：用 level6_self_compiled.py 编译 bootstrap_level5.light (Level 4 语法)

验证自举收敛性：比较第一次和第二次编译输出的差异
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

# 加载 level6_self_compiled.py (Level 4 编译器，从 Level 6 语法源码编译而来)
print("=" * 60)
print("加载 level6_self_compiled.py (自举编译器)")
print("=" * 60)
with open('bootstrap/level6_self_compiled.py', 'r', encoding='utf-8') as f:
    compiler_code = f.read()
exec(compiler_code, ns)
编译 = ns['编译']

# 读取 bootstrap_level5.light (Level 4 语法源码)
with open('bootstrap/bootstrap_level5.light', 'r', encoding='utf-8') as f:
    light_code = f.read()

print(f"源码大小: {len(light_code)} 字节")
print()

# 编译
print("正在编译 bootstrap_level5.light (Level 4 语法)...")
try:
    py_code = 编译(light_code)
    print(f"编译成功!")
    print(f"生成代码大小: {len(py_code)} 字节")
    print(f"生成代码行数: {len(py_code.split(chr(10)))} 行")
    print()
    
    # 验证语法
    try:
        compile(py_code, '<string>', 'exec')
        print("✅ 生成的 Python 代码语法正确")
    except SyntaxError as e:
        print(f"❌ 语法错误: {e}")
        lines = py_code.split(chr(10))
        lineno = e.lineno or 0
        for i in range(max(0, lineno-3), min(len(lines), lineno+2)):
            print(f"  {i+1}: {lines[i]}")
    
    # 保存
    with open('bootstrap/level6_self_compiled2.py', 'w', encoding='utf-8') as f:
        f.write(py_code)
    print("✅ 已保存到 bootstrap/level6_self_compiled2.py")
    
except Exception as e:
    print(f"❌ 编译失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("收敛性验证: 比较两次编译输出")
print("=" * 60)

# 读取第一次编译的结果 (level6_generated.py 编译 bootstrap_level6.light)
with open('bootstrap/level6_self_compiled.py', 'r', encoding='utf-8') as f:
    first_pass = f.read()

# 读取第二次编译的结果 (level6_self_compiled.py 编译 bootstrap_level5.light)
with open('bootstrap/level6_self_compiled2.py', 'r', encoding='utf-8') as f:
    second_pass = f.read()

# 归一化比较（忽略头部注释差异）
def normalize(code):
    lines = code.split('\n')
    idx = 0
    while idx < len(lines) and (lines[idx].startswith('#') or lines[idx].strip() == ''):
        idx += 1
    return '\n'.join(lines[idx:])

norm1 = normalize(first_pass)
norm2 = normalize(second_pass)

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
            if diff_count <= 5:
                print(f"  差异 {i+1} (行 {i+1}):")
                print(f"    第一次: {l1[:100]}")
                print(f"    第二次: {l2[:100]}")
    if len(lines1) != len(lines2):
        print(f"  行数不同: 第一次 {len(lines1)} 行, 第二次 {len(lines2)} 行")
    print(f"  总差异数: {diff_count}")

print()
print(f"第一次编译大小: {len(first_pass)} 字节")
print(f"第二次编译大小: {len(second_pass)} 字节")