"""自举收敛性验证：三次自举一致性测试

验证方法：
1. 用 level6_generated.py 编译 bootstrap_level5.light → level6_self_compiled.py
2. 用 level6_self_compiled.py 编译 bootstrap_level5.light → level6_self_compiled2.py
3. 用 level6_self_compiled2.py 编译 bootstrap_level5.light → level6_self_compiled3.py
4. 验证 level6_self_compiled2.py 与 level6_self_compiled3.py 完全相同
"""
import sys
sys.path.insert(0, '.')
import traceback

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

# 读取源文件
with open('bootstrap/bootstrap_level5.light', 'r', encoding='utf-8') as f:
    light_code = f.read()

print(f"源码: bootstrap_level5.light ({len(light_code)} 字节)")
print()

# ===== 第1次：用 level6_generated.py 编译 =====
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
    compile(py_code1, '<string>', 'exec')
    print("✅ 语法正确")
    with open('bootstrap/level6_self_compiled.py', 'w', encoding='utf-8') as f:
        f.write(py_code1)
except Exception as e:
    print(f"❌ 编译失败: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

print()

# ===== 第2次：用 level6_self_compiled.py 编译 =====
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
    compile(py_code2, '<string>', 'exec')
    print("✅ 语法正确")
    with open('bootstrap/level6_self_compiled2.py', 'w', encoding='utf-8') as f:
        f.write(py_code2)
except Exception as e:
    print(f"❌ 编译失败: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

print()

# ===== 第3次：用 level6_self_compiled2.py 编译 =====
print("=" * 60)
print("第3次: level6_self_compiled2.py 编译 bootstrap_level5.light")
print("=" * 60)
with open('bootstrap/level6_self_compiled2.py', 'r', encoding='utf-8') as f:
    compiler3_code = f.read()
ns3 = dict(ns)
exec(compiler3_code, ns3)
编译3 = ns3['编译']

try:
    py_code3 = 编译3(light_code)
    print(f"✅ 编译成功! 生成代码: {len(py_code3)} 字节")
    compile(py_code3, '<string>', 'exec')
    print("✅ 语法正确")
    with open('bootstrap/level6_self_compiled3.py', 'w', encoding='utf-8') as f:
        f.write(py_code3)
except Exception as e:
    print(f"❌ 编译失败: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

print()

# ===== 收敛性验证：比较第2次和第3次输出 =====
print("=" * 60)
print("收敛性验证: 比较 level6_self_compiled2.py 和 level6_self_compiled3.py")
print("=" * 60)

def normalize(code):
    """去除头部注释行和空行，只比较实际代码"""
    lines = code.split('\n')
    # 跳过开头的注释/空行
    idx = 0
    while idx < len(lines) and (lines[idx].startswith('#') or lines[idx].strip() == ''):
        idx += 1
    return '\n'.join(lines[idx:])

norm2 = normalize(py_code2)
norm3 = normalize(py_code3)

if norm2 == norm3:
    print("✅ 收敛成功！第2次和第3次编译输出完全一致")
    print()
    print(f"第1次: {len(py_code1)} 字节, {len(py_code1.split(chr(10)))} 行")
    print(f"第2次: {len(py_code2)} 字节, {len(py_code2.split(chr(10)))} 行")
    print(f"第3次: {len(py_code3)} 字节, {len(py_code3.split(chr(10)))} 行")
    print()
    print("🎉 自举验证通过！")
else:
    print("❌ 收敛失败：第2次和第3次编译输出有差异")
    lines2 = norm2.split('\n')
    lines3 = norm3.split('\n')
    diff_count = 0
    for i, (l2, l3) in enumerate(zip(lines2, lines3)):
        if l2 != l3:
            diff_count += 1
            if diff_count <= 15:
                print(f"  差异 {diff_count} (行 {i+1}):")
                print(f"    第2次: {l2[:120]}")
                print(f"    第3次: {l3[:120]}")
    if len(lines2) != len(lines3):
        print(f"  行数不同: 第2次 {len(lines2)} 行, 第3次 {len(lines3)} 行")
    print(f"  总差异数: {diff_count}")
    sys.exit(1)