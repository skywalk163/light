import sys
import os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

parser = LightParser()

# 测试: 不带括号的 arity=0 函数
tests = [
    ("字典创建(无括号)", """段落 主():
    设 d 为 字典创建。
    字典设置(d, "key", "value")。
    打印输出(字典获取(d, "key"))。
结束。
"""),
    ("列表创建(无括号)", """段落 主():
    设 lst 为 列表创建。
    列表追加(lst, "a")。
    列表追加(lst, "b")。
    打印输出(列表长度(lst))。
结束。
"""),
    ("JSON 测试", """段落 主():
    设 数据 为 解析JSON("{\"name\": \"光明\"}")。
    打印输出(字典获取(数据, "name"))。
结束。
"""),
]

for name, source in tests:
    print(f"\n=== {name} ===")
    gen = PythonCodeGenerator()
    try:
        ast = parser.parse(source) if name.split('(')[0] != tests[-1][0].split('(')[0] else LightParser().parse(source)
        if name == "JSON 测试":
            ast = LightParser().parse(source)
        code = gen.generate(ast)
        code_to_run = code + "\n\n主()\n"
        result = __import__('subprocess').run(
            [sys.executable, '-c', code_to_run],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout:
            print("STDOUT:", result.stdout.strip())
        if result.stderr:
            print("STDERR:", result.stderr.strip())
        if not result.stdout and not result.stderr:
            print("(无输出)")
    except Exception as e:
        print(f"错误: {e}")
