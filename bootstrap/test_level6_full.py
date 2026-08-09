"""
Level 6 全面测试套件
测试无空格分词 + 纯缩进语法
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
    try:
        py_code = 编译(light_code)
    except Exception as e:
        return "", type(e).__name__ + ": " + str(e)
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
            if err is None or expected_err not in err:
                print(f"  FAIL {name}: 应包含错误 '{expected_err}', 实际: {err}, 输出: {out}")
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
print("Level 6 全面测试套件")
print("无空格分词 + 纯缩进语法")
print("=" * 60)

# ═══════════════════════════════════════════════════════════
# 类别 1: 无空格分词
# ═══════════════════════════════════════════════════════════
print()
print("[类别 1] 无空格分词")

t("无空格函数定义",
   """
段foo接收a
    输出(a)
段主函数
    foo("hello")
""",
   "hello")

t("无空格变量声明",
   """
段主函数
    设x为42
    输出(x)
""",
   "42")

t("无空格返回语句",
   """
段add接收a,b
    返回a加b
段主函数
    输出(add(3,4))
""",
   "7")

t("无空格if语句",
   """
段主函数
    设x为10
    如果x大于5
        输出("big")
""",
   "big")

t("无空格混合分隔符",
   """
段主函数
    输出("hello,world")
""",
   "hello,world")

# ═══════════════════════════════════════════════════════════
# 类别 2: 纯缩进语法 - 基本控制流
# ═══════════════════════════════════════════════════════════
print()
print("[类别 2] 纯缩进 - 基本控制流")

t("if-else缩进",
   """
段主函数
    设x为5
    如果x大于10
        输出("big")
    否则
        输出("small")
""",
   "small")

t("while循环缩进",
   """
段主函数
    设i为0
    当i小于3
        输出(i)
        设i为i加1
""",
   "0\n1\n2")

t("for循环缩进",
   """
段主函数
    设s为0
    遍历i在列表创建(1,2,3)
        设s为s加i
    输出(s)
""",
   "6")

t("嵌套if缩进",
   """
段主函数
    设x为5
    如果x大于0
        如果x大于3
            输出("gt3")
        否则
            输出("le3")
    否则
        输出("neg")
""",
   "gt3")

t("嵌套while缩进",
   """
段主函数
    设i为0
    设s为0
    当i小于3
        设j为0
        当j小于3
            设s为s加1
            设j为j加1
        设i为i加1
    输出(s)
""",
   "9")

# ═══════════════════════════════════════════════════════════
# 类别 3: 纯缩进 - 函数定义
# ═══════════════════════════════════════════════════════════
print()
print("[类别 3] 纯缩进 - 函数定义")

t("简单函数纯缩进",
   """
段greet接收name
    输出(name)
段主函数
    greet("world")
""",
   "world")

t("多函数纯缩进",
   """
段add接收a,b
    返回a加b
段mul接收a,b
    返回a乘b
段主函数
    输出(add(3,mul(2,4)))
""",
   "11")

t("递归函数纯缩进",
   """
段fact接收n
    如果n小于等于1
        返回1
    返回n乘fact(n减1)
段主函数
    输出(fact(5))
""",
   "120")

t("函数嵌套调用纯缩进",
   """
段add接收a,b
    返回a加b
段calc接收x
    返回add(x,10)
段主函数
    输出(calc(5))
""",
   "15")

# ═══════════════════════════════════════════════════════════
# 类别 4: 纯缩进 - 异常处理
# ═══════════════════════════════════════════════════════════
print()
print("[类别 4] 纯缩进 - 异常处理")

t("try-catch纯缩进",
   """
段主函数
    尝试
        输出("try")
        抛出"test"
        输出("skip")
    捕获
        输出("catch")
""",
   "try\ncatch")

t("try-catch-finally纯缩进",
   """
段主函数
    尝试
        输出("try")
        抛出"err"
    捕获
        输出("catch")
    最终
        输出("finally")
""",
   "try\ncatch\nfinally")

t("try-finally无异常纯缩进",
   """
段主函数
    尝试
        输出("try")
    最终
        输出("finally")
""",
   "try\nfinally")

t("抛出变量纯缩进",
   """
段主函数
    设msg为"错误"
    尝试
        抛出msg
    捕获
        输出("catch")
""",
   "catch")

t("捕获值错误as变量",
   """
段主函数
    尝试
        抛出 ValueError("值错误")
    捕获 值错误 as e
        输出(e)
""",
   "值错误")

t("捕获异常as变量并输出e",
   """
段主函数
    尝试
        抛出"错误信息"
    捕获 异常 as e
        输出(e)
""",
   "错误信息")

t("捕获类型无变量",
   """
段主函数
    尝试
        抛出 ValueError("值错误")
    捕获 值错误
        输出("caught")
""",
   "caught")

t("多捕获类型第一匹配",
   """
段主函数
    尝试
        抛出 ValueError("值错误")
    捕获 值错误 as e
        输出("val")
    捕获 异常 as e
        输出("exc")
""",
   "val")

t("多捕获类型第二匹配",
   """
段主函数
    尝试
        抛出"test"
    捕获 值错误 as e
        输出("val")
    捕获 异常 as e
        输出(e)
""",
   "test")

# ═══════════════════════════════════════════════════════════
# 类别 5: 纯缩进 - 类定义
# ═══════════════════════════════════════════════════════════
print()
print("[类别 5] 纯缩进 - 类定义")

t("简单类纯缩进",
   """
段主函数
    类Point
        段落__init__接收己,x,y
            设己.x为x
            设己.y为y
        段落show接收己
            输出(己.x)
    设p为Point(3,4)
    p.show()
""",
   "3")

t("类继承纯缩进",
   """
段主函数
    类Base
        段落val接收己
            返回1
    类Derived(Base)
        段落val接收己
            返回父.val()加2
    输出(Derived().val())
""",
   "3")

# ═══════════════════════════════════════════════════════════
# 类别 6: 表达式和运算
# ═══════════════════════════════════════════════════════════
print()
print("[类别 6] 表达式和运算")

t("算术运算优先级",
   """
段主函数
    输出(1加2乘3减4除2)
""",
   "5")

t("比较运算",
   """
段主函数
    如果5大于3且2小于1或10等于10
        输出("true")
""",
   "true")

t("非运算",
   """
段主函数
    如果非假
        输出("yes")
""",
   "yes")

t("字符串拼接",
   """
段主函数
    输出("hello"加"world")
""",
   "helloworld")

t("运算符符号_加",
   """
段主函数
    输出(1+2)
""",
   "3")

t("运算符符号_减",
   """
段主函数
    输出(5-3)
""",
   "2")

t("运算符符号_乘",
   """
段主函数
    输出(3*4)
""",
   "12")

t("运算符符号_除",
   """
段主函数
    输出(7/2)
""",
   "3")

t("运算符符号_取模",
   """
段主函数
    输出(10%3)
""",
   "1")

t("运算符符号_等于",
   """
段主函数
    如果3==3
        输出("ok")
""",
   "ok")

t("运算符符号_不等于",
   """
段主函数
    如果3!=4
        输出("ok")
""",
   "ok")

t("运算符符号_小于",
   """
段主函数
    如果2<3
        输出("ok")
""",
   "ok")

t("运算符符号_大于",
   """
段主函数
    如果3>2
        输出("ok")
""",
   "ok")

t("运算符符号_小于等于",
   """
段主函数
    如果2<=3
        输出("ok")
""",
   "ok")

t("运算符符号_大于等于",
   """
段主函数
    如果3>=3
        输出("ok")
""",
   "ok")

t("运算符符号混合运算",
   """
段主函数
    输出(1+2*3-4/2)
""",
   "5")

t("运算符符号比较链",
   """
段主函数
    如果1<2且2<=3且3==3且3!=4
        输出("all_true")
""",
   "all_true")

t("反引号转义标识符变量",
   """
段主函数
    设`真`为10
    输出(`真`)
""",
   "10")

t("反引号转义关键字作为变量名",
   """
段主函数
    设`类`为"test"
    输出(`类`)
""",
   "test")

t("反引号转义标识符赋值",
   """
段主函数
    `如果`设为5
    输出(`如果`)
""",
   "5")

t("反引号未闭合错误",
   """
段主函数
    设x为`abc
    输出(x)
""",
   expected_err="未闭合的反引号标识符")

# ═══════════════════════════════════════════════════════════
# 类别 7: 混合场景
# ═══════════════════════════════════════════════════════════
print()
print("[类别 7] 混合场景")

t("复杂嵌套",
   """
段fact接收n
    如果n小于等于1
        返回1
    返回n乘fact(n减1)
段主函数
    设i为0
    当i小于5
        输出(fact(i))
        设i为i加1
""",
   "1\n1\n2\n6\n24")

t("异常+循环混合",
   """
段主函数
    设i为0
    当i小于3
        尝试
            输出(i)
            如果i等于1
                抛出"skip"
        捕获
            输出("caught")
        最终
            输出("done")
        设i为i加1
""",
   "0\ndone\n1\ncaught\ndone\n2\ndone")

# ═══════════════════════════════════════════════════════════
# 类别 8: 健壮性测试 - 错误检测
# ═══════════════════════════════════════════════════════════
print()
print("[类别 8] 健壮性测试 - 错误检测")

t("制表符缩进错误",
   """
段主函数
\t输出("tab")
""",
   expected_err="缩进中不能使用制表符(Tab)")

t("制表符代码中错误",
   """
段主函数
    输出("a")\t输出("b")
""",
   expected_err="代码中不能包含制表符(Tab)")

t("无法识别的字符",
   """
段主函数
    输出@("test")
""",
   expected_err="无法识别的字符")

t("正常代码无错误",
   """
段主函数
    输出("hello")
""",
   expected_out="hello")

# ═══════════════════════════════════════════════════════════
# 类别 9: 调试日志功能
# ═══════════════════════════════════════════════════════════
print()
print("[类别 9] 调试日志功能")

# 测试 调试模式设为文件
def test_debug_log_file():
    """测试调试日志输出到文件"""
    import os, tempfile
    tmp = tempfile.mktemp(suffix=".log")
    try:
        ns['调试模式设为文件'](tmp)
        # 编译一个简单程序触发日志输出
        编译("段主函数\n    输出(1)")
        # 关闭文件
        if ns['调试日志文件'] is not None:
            ns['调试日志文件'].close()
            ns['调试日志文件'] = None
            ns['调试模式'] = False
        with open(tmp, 'r', encoding='utf-8') as f:
            content = f.read()
        if "=== 调试日志开始 ===" in content:
            print("  OK  调试日志输出到文件")
        else:
            print("  FAIL 调试日志输出到文件: 文件内容不含预期内容")
    except Exception as e:
        import traceback
        print("  FAIL 调试日志输出到文件:", e)
        traceback.print_exc()
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

test_debug_log_file()

# 测试 调试模式=真（stdout）
def test_debug_log_stdout():
    """测试调试日志输出到stdout"""
    old_mode = ns['调试模式']
    try:
        # 先重置为假
        ns['调试模式'] = False
        if ns['调试日志文件'] is not None:
            ns['调试日志文件'].close()
            ns['调试日志文件'] = None
        # 编译简单程序，不触发日志输出（调试模式为假）
        编译("段主函数\n    输出(1)")
        print("  OK  调试模式关闭无日志输出（默认行为）")
        # 开启调试模式
        ns['调试模式'] = True
        编译("段主函数\n    输出(1)")
        print("  OK  调试模式开启无异常（stdout输出）")
    except Exception as e:
        import traceback
        print("  FAIL 调试日志stdout:", e)
        traceback.print_exc()
    finally:
        ns['调试模式'] = old_mode

test_debug_log_stdout()

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