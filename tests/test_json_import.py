import sys
import os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

# 测试: 显式从《JSON》导入
source = """从《JSON》导入《解析JSON》，《序列化JSON》。

段落 主():
    设 数据 为 解析JSON("{\"name\": \"光明\"}")。
    打印输出(序列化JSON(数据))。
结束。
"""

print("=== 测试: 显式导入 JSON ===")
parser = LightParser()
gen = PythonCodeGenerator()
try:
    ast = parser.parse(source)
    code = gen.generate(ast)
    # 打印生成的代码（最后部分）
    print("生成的Python代码（最后20行）:")
    for line in code.split('\n')[-20:]:
        print(f"  {line}")
    code_to_run = code + "\n\n主()\n"
    result = __import__('subprocess').run(
        [sys.executable, '-c', code_to_run],
        capture_output=True, text=True, timeout=10
    )
    if result.stdout:
        print("STDOUT:", result.stdout.strip())
    if result.stderr:
        print("STDERR:", result.stderr.strip())
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
