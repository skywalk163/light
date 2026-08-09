"""
Level 7 类型注解测试 — 任务 1：变量类型注解
测试设x为整数=10 形式的变量类型注解
"""
import sys, io, contextlib

sys.path.insert(0, '.')

def 列表创建(*args): return list(args)
def 列表追加(lst, item): lst.append(item)
def 列表获取(lst, i): return lst[i]
def 列表长度(lst): return len(lst)
def 字符串长度(s): return len(s)
def 字符串获取(s, i): return s[i]
def 截取(s, a, b): return s[a:b]
def 打印(*args): print(*args)
def 建(t, v): return [t, v]

ns = {
    '列表创建': 列表创建, '列表追加': 列表追加, '列表获取': 列表获取,
    '列表长度': 列表长度, '字符串长度': 字符串长度, '字符串获取': 字符串获取,
    '截取': 截取, '打印': 打印, '输出': 打印, '真': True, '假': False, '建': 建,
}

with open('bootstrap/level6_generated.py', 'r', encoding='utf-8') as f:
    code = f.read()
exec(code, ns)
编译 = ns['编译']

def compile_and_run(light_code):
    """编译并运行光明代码，返回输出和错误"""
    py_code = 编译(light_code)
    ns2 = dict(ns)
    ns2['主函数'] = None
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        try:
            exec(py_code, ns2)
            if '主函数' in ns2 and ns2['主函数'] is not None:
                ns2['主函数']()
            return output.getvalue(), None
        except Exception as e:
            return output.getvalue(), type(e).__name__

passed = 0
failed = 0
failed_tests = []

def t(name, src, expected_out=None, expected_err=None):
    """测试用例：编译运行并检查输出"""
    global passed, failed, failed_tests
    try:
        out, err = compile_and_run(src)
        ok = True
        if expected_out is not None:
            if expected_out not in out:
                print(f"  FAIL {name}: 输出中应包含 '{expected_out}', 实际: {out}")
                ok = False
        if expected_err is not None:
            if err != expected_err:
                print(f"  FAIL {name}: 应出错 {expected_err}, 实际: {err}, 输出: {out}")
                ok = False
        if expected_err is None and err is not None:
            print(f"  FAIL {name}: 不应出错, 实际: {err}, 输出: {out}")
            ok = False
        if ok:
            print(f"  OK  {name}")
            passed += 1
        else:
            failed += 1
            failed_tests.append(name)
    except Exception as e:
        print(f"  FAIL {name}: {type(e).__name__}: {e}")
        failed += 1
        failed_tests.append(name)

print("=" * 60)
print("Level 7 类型注解测试 — 任务 1：变量类型注解")
print("=" * 60)

# ═══════════════════════════════════════════════════════════
# 测试组 1: 变量类型注解（有初始值）
# ═══════════════════════════════════════════════════════════
print()
print("[测试组 1] 变量类型注解（有初始值）")

t("变量整数类型注解",
   """
段主函数
    设x为整数=10
    输出(x)
""",
   "10")

t("变量文本类型注解",
   """
段主函数
    设name为文本="hello"
    输出(name)
""",
   "hello")

t("变量小数类型注解",
   """
段主函数
    设pi为小数=3.14
    输出(pi)
""",
   "3.14")

t("变量布尔类型注解",
   """
段主函数
    设flag为布尔=真
    如果flag
        输出("true")
""",
   "true")

# ═══════════════════════════════════════════════════════════
# 测试组 2: 变量类型注解（无初始值）
# ═══════════════════════════════════════════════════════════
print()
print("[测试组 2] 变量类型注解（无初始值）")

t("变量类型注解无初始值",
   """
段主函数
    设x为整数
    输出("ok")
""",
   "ok")

# ═══════════════════════════════════════════════════════════
# 测试组 3: 向后兼容（无类型注解）
# ═══════════════════════════════════════════════════════════
print()
print("[测试组 3] 向后兼容")

t("向后兼容无类型注解",
   """
段主函数
    设x为10
    输出(x)
""",
   "10")

t("向后兼容文本",
   """
段主函数
    设name为"world"
    输出(name)
""",
   "world")

t("向后兼容表达式",
   """
段主函数
    设x为1加2乘3
    输出(x)
""",
   "7")

# ═══════════════════════════════════════════════════════════
# 测试组 4: 己属性赋值（不受影响）
# ═══════════════════════════════════════════════════════════
print()
print("[测试组 4] 己属性赋值（不受影响）")

t("己属性赋值保持不变",
   """
段主函数
    类Counter
        段落__init__接收己
            设己.count为0
        段落get接收己
            返回己.count
    设c为Counter()
    输出(c.get())
""",
   "0")

# ═══════════════════════════════════════════════════════════
# 测试组 5: 函数参数和返回类型注解
# ═══════════════════════════════════════════════════════════
print()
print("[测试组 5] 函数参数和返回类型注解")

t("函数参数和返回类型注解",
   """
段add接收a 整数,b 整数返回整数
    返回a加b
段主函数
    输出(add(3,4))
""",
   "7")

t("函数参数类型注解无返回",
   """
段greet接收name 文本
    输出(name)
段主函数
    greet("hello")
""",
   "hello")

t("向后兼容无类型注解函数",
   """
段add接收a,b
    返回a加b
段主函数
    输出(add(3,4))
""",
   "7")

t("混合参数类型注解",
   """
段mul接收a 整数,b 小数
    返回a乘b
段主函数
    输出(mul(3,2.5))
""",
   "7.5")

# ═══════════════════════════════════════════════════════════
# 测试组 6: 复合类型注解
# ═══════════════════════════════════════════════════════════
print()
print("[测试组 6] 复合类型注解")

t("列表复合类型变量",
   """
段主函数
    设arr为列表[整数]=[1,2,3]
    输出(列表长度(arr))
""",
   "3")

t("字典复合类型变量",
   """
段主函数
    设map为字典[文本,整数]={"a":1}
    输出(列表长度(map))
""",
   "1")

t("复合类型函数参数",
   """
段process接收items 列表[整数]
    输出(列表长度(items))
段主函数
    process([1,2,3,4])
""",
   "4")

t("复合类型函数返回",
   """
段identity接收x 整数返回列表[整数]
    返回[x]
段主函数
    输出(identity(5))
""",
   "[5]")

# ═══════════════════════════════════════════════════════════
# 测试组 7: 运行时类型检查
# ═══════════════════════════════════════════════════════════
print()
print("[测试组 7] 运行时类型检查")

t("类型检查通过",
   """
段主函数
    开启类型检查
    设x为整数=10
    输出(x)
    关闭类型检查
""",
   "10")

t("类型检查失败",
   """
段主函数
    开启类型检查
    设x为整数="hello"
    输出("should_not_reach")
    关闭类型检查
""",
   None,
   "TypeError")

t("类型检查默认关闭",
   """
段主函数
    设x为整数="hello"
    输出("ok")
""",
   "ok")

# ═══════════════════════════════════════════════════════════
# 总结
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("总结")
print("=" * 60)
print(f"  总计: {passed}/{passed+failed} 通过")
if failed_tests:
    print(f"  失败: {failed_tests}")
else:
    print("  所有测试通过！")