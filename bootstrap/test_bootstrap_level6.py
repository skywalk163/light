"""测试 bootstrap_level6.light 能否被 level6_generated.py 编译"""
import sys, io, contextlib

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

# 加载 Level 6 编译器
with open('bootstrap/level6_generated.py', 'r', encoding='utf-8') as f:
    compiler_code = f.read()
exec(compiler_code, ns)
编译 = ns['编译']

# 读取 bootstrap_level6.light
with open('bootstrap/bootstrap_level6.light', 'r', encoding='utf-8') as f:
    light_code = f.read()

print("正在编译 bootstrap_level6.light ...")
print(f"源码大小: {len(light_code)} 字节")
print()

try:
    py_code = 编译(light_code)
    print(f"编译成功!")
    print(f"生成代码大小: {len(py_code)} 字节")
    print(f"生成代码行数: {len(py_code.split(chr(10)))} 行")
    print()
    
    # 验证生成的 Python 代码语法正确
    try:
        compile(py_code, '<string>', 'exec')
        print("✅ 生成的 Python 代码语法正确")
    except SyntaxError as e:
        print(f"❌ 生成的 Python 代码语法错误: {e}")
        # 打印错误位置附近的代码
        lines = py_code.split(chr(10))
        lineno = e.lineno or 0
        for i in range(max(0, lineno-3), min(len(lines), lineno+2)):
            print(f"  {i+1}: {lines[i]}")
    
    # 保存生成的文件
    with open('bootstrap/level6_self_compiled.py', 'w', encoding='utf-8') as f:
        f.write(py_code)
    print(f"✅ 已保存到 bootstrap/level6_self_compiled.py")
    
except Exception as e:
    print(f"❌ 编译失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()