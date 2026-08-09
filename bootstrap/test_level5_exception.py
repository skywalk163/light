import sys
import io
import contextlib

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

with open('bootstrap/level5_generated.py', 'r', encoding='utf-8') as f:
    code = f.read()
exec(code, ns)
编译 = ns['编译']

def compile_and_run(light_code):
    py_code = 编译(light_code)
    ns2 = dict(ns)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        try:
            exec(py_code, ns2)
            return output.getvalue(), None
        except Exception as e:
            return output.getvalue(), type(e).__name__

def test_basic_try_catch():
    code = """尝试：
    输出("try块")
    抛出 "测试异常"
    输出("不会执行")
捕获：
    输出("捕获异常")
结束。
"""
    out, err = compile_and_run(code)
    assert "try块" in out, f"应执行try块: {out}"
    assert "捕获异常" in out, f"应捕获异常: {out}"
    assert "不会执行" not in out, f"不应执行抛出后代码: {out}"
    print("✅ 基础尝试-捕获测试通过")

def test_throw_string():
    code = """尝试：
    抛出 "错误"
捕获：
    输出("已捕获")
结束。
"""
    out, err = compile_and_run(code)
    assert "已捕获" in out, f"应捕获异常: {out}"
    print("✅ 抛出字符串测试通过")

def test_finally_block():
    code = """尝试：
    输出("try")
    抛出 "错"
捕获：
    输出("catch")
最终：
    输出("finally")
结束。
"""
    out, err = compile_and_run(code)
    assert "try" in out, f"应执行try: {out}"
    assert "catch" in out, f"应执行catch: {out}"
    assert "finally" in out, f"应执行finally: {out}"
    print("✅ 最终块测试通过")

def test_throw_variable():
    code = """设 msg 为 "动态错误"
尝试：
    抛出 msg
捕获：
    输出("已捕获")
结束。
"""
    out, err = compile_and_run(code)
    assert "已捕获" in out, f"应捕获变量抛出: {out}"
    print("✅ 抛出变量测试通过")

if __name__ == '__main__':
    print("Level 5 异常处理测试")
    print("=" * 50)
    test_basic_try_catch()
    test_throw_string()
    test_finally_block()
    test_throw_variable()
    print("=" * 50)
    print("🎉 所有异常处理测试通过!")