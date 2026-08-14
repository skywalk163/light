"""
光明转译器 v3.5 验证脚本
测试 T2: match-case / async-await / 函数默认参数
测试 T3: 装饰器转译增强
测试 T5: 链式调用 a.b.c()
测试 T6: 转译器语义校验与报告
"""
import sys
import os
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from py2light_transpiler import Py2LightTranspiler, TranspileError

# 导入光明解析器验证转译结果
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.light_parser_v3 import LightParser

transpiler = Py2LightTranspiler()

PASS = 0
FAIL = 0


def t(name, py_code, expected):
    """测试用例：转译 Python 代码并比对期望输出"""
    global PASS, FAIL
    try:
        result = transpiler.transpile(py_code.strip())
        expected = expected.strip()
        if result == expected:
            PASS += 1
            print(f"  [PASS] {name}")
        else:
            FAIL += 1
            print(f"  [FAIL] {name}")
            print(f"    期望:\n{expected}")
            print(f"    实际:\n{result}")
    except TranspileError as e:
        FAIL += 1
        print(f"  [FAIL] {name} — 转译错误: {e}")


def verify_parse(name, light_code):
    """验证光明代码能被 LightParser 正确解析"""
    global PASS, FAIL
    try:
        parser = LightParser()
        parser.parse(light_code)
        PASS += 1
        print(f"  [PASS] {name} (解析成功)")
    except Exception as e:
        FAIL += 1
        print(f"  [FAIL] {name} — 解析失败: {e}")


print("=" * 60)
print("T2: match-case 转译")
print("=" * 60)

# === 2.1 match-case ===
t("match-case 基本",
  """match status:
    case 200:
        print("OK")
    case 404:
        print("Not Found")
    case _:
        print("Unknown")""",
  """匹配 status：
    情况 200：
        打印("OK")
    情况 404：
        打印("Not Found")
    情况 _：
        打印("Unknown")""")

t("match-case 带守卫",
  """match x:
    case n if n > 0:
        print("positive")""",
  """匹配 x：
    情况 n 若 n 大于 0：
        打印("positive")""")

t("match-case 序列模式",
  """match point:
    case [0, 0]:
        print("origin")
    case [x, y]:
        print(f"point at {x},{y}")""",
  """匹配 point：
    情况 [0, 0]：
        打印("origin")
    情况 [x, y]：
        打印(f"point at {x},{y}")""")

t("match-case 映射模式",
  """match config:
    case {"debug": True}:
        print("debug mode")
    case _:
        print("normal")""",
  """匹配 config：
    情况 {"debug": 真}：
        打印("debug mode")
    情况 _：
        打印("normal")""")

t("match-case 类模式",
  """match cmd:
    case Command("quit"):
        print("bye")
    case _:
        print("unknown")""",
  """匹配 cmd：
    情况 Command("quit")：
        打印("bye")
    情况 _：
        打印("unknown")""")

t("match-case 默认值",
  """match status:
    case 200:
        print("OK")
    case 404:
        print("Not Found")
    case _:
        print("Unknown")""",
  """匹配 status：
    情况 200：
        打印("OK")
    情况 404：
        打印("Not Found")
    情况 _：
        打印("Unknown")""")


print()
print("=" * 60)
print("T2: async/await 转译")
print("=" * 60)

# === 2.2 async/await ===
t("async def",
  """async def fetch_data(url):
    response = await get(url)
    return response""",
  """异步 段落 fetch_data 接收 url：
    设 response 为 等待 get(url)
    返回 response""")

t("async def 无参",
  """async def tick():
    await asyncio.sleep(1)
    return "done\"""",
  """异步 段落 tick：
    等待 asyncio.sleep(1)
    返回 "done\"""")

t("async for",
  """async for item in async_iter:
    print(item)""",
  """异步 遍历 item 于 async_iter：
    打印(item)""")

t("async with",
  """async with session.get(url) as resp:
    data = await resp.json()""",
  """异步 使用 获取(session, url) 为 resp：
    设 data 为 等待 resp.json()""")


print()
print("=" * 60)
print("T2: 函数默认参数")
print("=" * 60)

# === 2.3 函数默认参数 ===
t("函数默认参数",
  """def greet(name, greeting="Hello", times=1):
    for i in range(times):
        print(f"{greeting}, {name}!")""",
  """段落 greet 接收 name, greeting 等于 "Hello", times 等于 1：
    遍历 i 于 0至times-1：
        打印(f"{greeting}, {name}!")""")

t("函数默认参数-数字",
  """def multiply(a, b=2):
    return a * b""",
  """段落 multiply 接收 a, b 等于 2：
    返回 a 乘以 b""")

t("函数默认参数-布尔",
  """def is_positive(n, debug=False):
    if debug:
        print(f"checking {n}")
    return n > 0""",
  """段落 is_positive 接收 n, debug 等于 假：
    如果 debug：
        打印(f"checking {n}")
    返回 n 大于 0""")


print()
print("=" * 60)
print("T3: 装饰器转译增强")
print("=" * 60)

# === T3: 装饰器 ===
t("@staticmethod",
  """class MyClass:
    @staticmethod
    def helper():
        return 42""",
  """类 MyClass：
    静态 段落 helper：
        返回 42""")

t("@property",
  """class MyClass:
    @property
    def count(self):
        return len(self.items)""",
  """类 MyClass：
    特性 段落 count：
        返回 len(己.items)""")

t("@classmethod",
  """class MyClass:
    @classmethod
    def create(cls, val):
        return cls(val)""",
  """类 MyClass：
    类方法 段落 create 接收 val：
        返回 cls(val)""")

t("@自定义装饰器",
  """class MyClass:
    @my_decorator
    def process(self):
        pass""",
  """类 MyClass：
    标注 my_decorator
    段落 process：""")

t("@装饰器带参数",
  """class MyClass:
    @decorator(param=10)
    def method(self):
        return 1""",
  """类 MyClass：
    标注 decorator(param=10)
    段落 method：
        返回 1""")

t("@装饰器链",
  """class MyClass:
    @staticmethod
    @my_decorator
    def process():
        pass""",
  """类 MyClass：
    静态 标注 my_decorator
    段落 process：""")

t("@classmethod 链",
  """class MyClass:
    @classmethod
    @validate
    def create(cls, val):
        return cls(val)""",
  """类 MyClass：
    类方法 标注 validate
    段落 create 接收 val：
        返回 cls(val)""")


print()
print("=" * 60)
print("T5: 链式调用转译")
print("=" * 60)

# === T5: 链式调用 ===
t("链式调用 a.b.c()",
  "result = obj.method().chain()",
  "设 result 为 obj.method().chain()")

t("链式调用+属性",
  "result = obj.method().value",
  "设 result 为 obj.method().value")

t("深层属性 self.a.b.c",
  "result = self.data.items",
  "设 result 为 己.data.items")

t("混合调用 obj.method().attr",
  "result = obj.method().chain().value",
  "设 result 为 obj.method().chain().value")

t("append 链式",
  "self.data.items.append(10)",
  "追加(己.data.items, 10)")

t("多层方法链式",
  "result = a.b().c().d()",
  "设 result 为 a.b().c().d()")

t("属性+方法混合",
  "result = obj.attr.method().prop",
  "设 result 为 obj.attr.method().prop")

t("链式调用作为参数",
  "print(obj.method().chain())",
  "打印(obj.method().chain())")

t("双重链式赋值",
  "x = obj.a.b.c.d",
  "设 x 为 obj.a.b.c.d")

t("self 链式",
  "self.a.b.c()",
  "己.a.b.c()")

t("链式调用带参数",
  "result = a.b(c).d(e)",
  "设 result 为 a.b(c).d(e)")

t("链式调用带下标",
  "result = a.b[c].d()",
  "设 result 为 a.b[c].d()")

t("嵌套链式作为参数",
  "result = a(b().c())",
  "设 result 为 a(b().c())")

t("链式与二元运算",
  "result = a.b().c + d.e().f",
  "设 result 为 a.b().c 加上 d.e().f")

t("方法链+属性",
  "result = obj.get_data().process().result",
  "设 result 为 obj.get_data().process().result")

t("链式在if条件中",
  "if obj.is_valid() and obj.check(): pass",
  "如果 obj.is_valid() 且 obj.check()：")

t("链式调用带关键字参数",
  "result = obj.method(a=1, b=2).chain()",
  "设 result 为 obj.method(a=1, b=2).chain()")

t("链式返回值+方法",
  "obj.get_config().save()",
  "obj.get_config().save()")

t("链式在返回语句中",
  "def get(): return self.data.items",
  "段落 get：\n    返回 己.data.items")

t("列表推导式中链式",
  "result = [x.method() for x in items]",
  "设 result 为 [x.method() 遍历 x 于 items]")

t("方法调用中的链式",
  "print(self.data.strip().upper())",
  "打印(字符串转大写(字符串去空白(己.data)))")

t("复杂链式+赋值",
  "self.cache.get(key).update(value)",
  "获取(己.cache, key).update(value)")

t("三元表达式中的链式",
  "result = a if obj.is_valid() else b",
  "设 result 为 如果 obj.is_valid() 则 a 否则 b")


print()
print("=" * 60)
print("T6: 语义校验验证")
print("=" * 60)

# 验证 _validate_light 能正确检测有效/无效代码
try:
    from pyproject2light import ProjectTranspiler

    # 创建临时目录测试
    tmpdir = tempfile.mkdtemp(prefix="light_test_t6_")
    os.makedirs(os.path.join(tmpdir, "test_project"), exist_ok=True)

    # 创建测试用的 Python 文件
    valid_py = os.path.join(tmpdir, "test_project", "valid.py")
    with open(valid_py, "w", encoding="utf-8") as f:
        f.write("x = 1\nprint(x)\n")

    # 运行 ProjectTranspiler
    t6 = ProjectTranspiler(
        src_dir=os.path.join(tmpdir, "test_project"),
        out_dir=os.path.join(tmpdir, "out"),
        dry_run=False,
        verbose=False,
    )
    t6.run()

    # 检查报告是否包含必要信息
    report_path = os.path.join(tmpdir, "out", "CONVERSION_REPORT.md")
    with open(report_path, "r", encoding="utf-8") as f:
        report = f.read()

    checks = [
        ("统计摘要", "统计摘要" in report),
        ("文件转译详情", "文件转译详情" in report),
        ("使用说明", "使用说明" in report),
        ("Python 特性", "特性" in report or "Python" in report),
        ("转译成功率", "转译成功率" in report),
    ]

    for name, ok in checks:
        if ok:
            PASS += 1
            print(f"  [PASS] T6 报告包含 {name}")
        else:
            FAIL += 1
            print(f"  [FAIL] T6 报告缺少 {name}")

    # 验证 duan.json 包含必要信息
    json_path = os.path.join(tmpdir, "out", "duan.json")
    with open(json_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    json_checks = [
        ("stats", "stats" in manifest),
        ("duan_files", "duan_files" in manifest),
        ("imports", "imports" in manifest),
        ("local_modules", "local_modules" in manifest),
    ]

    for name, ok in json_checks:
        if ok:
            PASS += 1
            print(f"  [PASS] T6 duan.json 包含 {name}")
        else:
            FAIL += 1
            print(f"  [FAIL] T6 duan.json 缺少 {name}")

    # 清理
    shutil.rmtree(tmpdir)

except ImportError as e:
    FAIL += 1
    print(f"  [FAIL] T6 导入失败: {e}")
    print(f"  [INFO] T6 验证跳过 (可能缺少依赖)")
except Exception as e:
    FAIL += 1
    print(f"  [FAIL] T6 运行失败: {e}")


print()
print("=" * 60)
print("光明解析验证: 验证转译结果能被 LightParser 解析")
print("=" * 60)

# 验证转译后的光明代码能被解析
verify_tests = [
    ("match-case 解析", """匹配 status：
    情况 200：
        打印("OK")
    情况 404：
        打印("Not Found")
    情况 _：
        打印("Unknown")"""),
    ("async 解析", """异步 段落 fetch_data 接收 url：
    设 response 为 等待 get(url)
    返回 response"""),
    ("函数默认参数 解析", """段落 greet 接收 name, greeting 等于 "Hello", times 等于 1：
    遍历 i 于 0至times-1：
        打印(f"{greeting}, {name}!")"""),
    ("链式调用 解析", """设 result 为 obj.method().chain()"""),
    ("链式+属性 解析", """设 result 为 obj.method().value"""),
    ("深层属性 解析", """设 result 为 己.data.items"""),
    ("混合调用 解析", """设 result 为 obj.method().chain().value"""),
    ("append 解析", """追加(己.data.items, 10)"""),
    ("多层方法链式 解析", """设 result 为 a.b().c().d()"""),
    ("属性+方法混合 解析", """设 result 为 obj.attr.method().prop"""),
    ("self 链式 解析", """己.a.b.c()"""),
    ("链式调用带参数 解析", """设 result 为 a.b(c).d(e)"""),
    ("链式调用带下标 解析", """设 result 为 a.b[c].d()"""),
    ("嵌套链式作为参数 解析", """设 result 为 a(b().c())"""),
    ("链式与二元运算 解析", """设 result 为 a.b().c 加上 d.e().f"""),
    ("方法链+属性 解析", """设 result 为 obj.get_data().process().result"""),
    ("链式在if条件中 解析", """如果 obj.is_valid() 且 obj.check()："""),
    ("链式调用带关键字参数 解析", """设 result 为 obj.method(a=1, b=2).chain()"""),
    ("链式返回值+方法 解析", """obj.get_config().save()"""),
    ("链式在返回语句中 解析", """段落 get：\n    返回 己.data.items"""),
    ("列表推导式中链式 解析", """设 result 为 [x.method() 遍历 x 于 items]"""),
    ("方法调用中的链式 解析", """打印(字符串转大写(字符串去空白(己.data)))"""),
    ("复杂链式+赋值 解析", """获取(己.cache, key).update(value)"""),
    ("三元表达式中的链式 解析", """设 result 为 如果 obj.is_valid() 则 a 否则 b"""),
]

for name, light_code in verify_tests:
    verify_parse(name, light_code)


# === 结果汇总 ===
print()
print("=" * 60)
total = PASS + FAIL
print(f"结果: {PASS}/{total} 通过", end="")
if FAIL > 0:
    print(f", {FAIL} 失败")
else:
    print(" 全部通过!")
print("=" * 60)

sys.exit(0 if FAIL == 0 else 1)