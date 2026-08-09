import sys
import os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

parser = LightParser()
gen = PythonCodeGenerator()

# 测试1: 基本当循环
source1 = """段落 主():
    设 计数 为 0。
    当 计数 小于 3:
        打印输出(计数)。
        设 计数 为 计数 加 1。
    结束。
结束。
"""

print("=== 测试1: 当循环 ===")
try:
    ast = parser.parse(source1)
    code = gen.generate(ast)
    print("✓ 编译成功")
    code_to_run = code + "\n\n主()\n"
    result = __import__('subprocess').run(
        [sys.executable, '-c', code_to_run],
        capture_output=True, text=True, timeout=10
    )
    print("STDOUT:", result.stdout.strip())
    if result.stderr:
        print("STDERR:", result.stderr.strip())
except Exception as e:
    print(f"错误: {e}")

# 测试2: 条件判断
source2 = """段落 主():
    设 名称 为 "Content-Length: 123"。
    如果 名称 等于 "Content-Length: 123" 那么:
        打印输出("完全匹配")。
    结束。
    设 前缀 为 名称的前15个字符。
    如果 前缀 等于 "Content-Length:" 那么:
        打印输出("前缀匹配")。
    结束。
结束。
"""

print("\n=== 测试2: 条件判断 ===")
try:
    gen2 = PythonCodeGenerator()
    ast = parser.parse(source2)
    code = gen2.generate(ast)
    print("✓ 编译成功")
    code_to_run = code + "\n\n主()\n"
    result = __import__('subprocess').run(
        [sys.executable, '-c', code_to_run],
        capture_output=True, text=True, timeout=10
    )
    print("STDOUT:", result.stdout.strip())
    if result.stderr:
        print("STDERR:", result.stderr.strip())
except Exception as e:
    print(f"错误: {e}")

# 测试3: 子串提取
source3 = """段落 主():
    设 文本 为 "Content-Length: 123"。
    设 值 为 文本的从第16个字符到最后。
    打印输出(值)。
结束。
"""

print("\n=== 测试3: 子串提取 ===")
try:
    gen3 = PythonCodeGenerator()
    ast = parser.parse(source3)
    code = gen3.generate(ast)
    # 打印生成的代码看看
    print("生成的代码（最后部分）:")
    lines = code.split('\n')
    for l in lines[-15:]:
        print(f"  {l}")
    code_to_run = code + "\n\n主()\n"
    result = __import__('subprocess').run(
        [sys.executable, '-c', code_to_run],
        capture_output=True, text=True, timeout=10
    )
    print("STDOUT:", repr(result.stdout))
    if result.stderr:
        print("STDERR:", result.stderr.strip())
except Exception as e:
    print(f"错误: {e}")
