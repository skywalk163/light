import sys
import os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

parser = LightParser()

# 测试: 字符串操作 - 各种方式
tests = [
    ("分割字符串", """段落 主():
    设 行 为 "Content-Length: 123"。
    设 部分 为 分割字符串(行, ":")。
    打印输出(部分)。
结束。
"""),
    ("字符串长度", """段落 主():
    设 名称 为 "Content-Length: 123"。
    打印输出(字符串长度(名称))。
结束。
"""),
    ("字典操作", """段落 主():
    设 字典 为 字典创建()。
    字典设置(字典, "key", "value")。
    打印输出(字典获取(字典, "key"))。
    打印输出(字典包含键(字典, "key"))。
结束。
"""),
    ("列表操作", """段落 主():
    设 列表 为 列表创建()。
    列表追加(列表, "a")。
    列表追加(列表, "b")。
    打印输出(列表获取(列表, 0))。
    打印输出(列表长度(列表))。
结束。
"""),
]

for name, source in tests:
    print(f"\n=== {name} ===")
    gen = PythonCodeGenerator()
    try:
        ast = parser.parse(source)
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
