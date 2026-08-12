"""编译并运行数据处理.light"""
import sys
sys.path.insert(0, 'd:\\traework\\light\\src')

from compiler import LightCompiler
from code_generator_unified import UnifiedCodeGenerator

# 读取源码
with open('数据处理.light', 'r', encoding='utf-8') as f:
    source = f.read()

print("=== 编译 ===")
compiler = LightCompiler()
result = compiler.compile(source)
if result['errors']:
    print("编译失败:")
    for e in result['errors']:
        print(f"  - {e}")
    sys.exit(1)
print("编译成功！")

# 生成代码
print("\n=== 生成代码 ===")
gen = UnifiedCodeGenerator()
code = gen.generate(result['ast'])

# 写入文件
with open('数据处理.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("已写入 数据处理.py")

# 运行
print("\n=== 运行结果 ===")
exec(code)