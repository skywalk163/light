"""测试光明自举解释器 - 简化版"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source
from light_visitor import parse_source

# 1. 加载解释器源码
print("=" * 60)
print("1. 加载自举解释器源码")
print("=" * 60)

interpreter_code = open("interpreter.light", encoding="utf-8").read()
print(f"解释器源码长度: {len(interpreter_code)} 字符")
print(f"行数: {interpreter_code.count('\\n') + 1}")

# 2. 解析解释器源码
print()
print("=" * 60)
print("2. 解析自举解释器源码")
print("=" * 60)

try:
    ast = parse_source(interpreter_code)
    if ast is None:
        print("解析失败: AST 为 None")
        sys.exit(1)
    print(f"解析成功！模块包含:")
    print(f"  - {len(ast.segments)} 个段落定义")
    print(f"  - {len(ast.statements)} 个顶层语句")
    print(f"  - {len(ast.imports)} 个导入语句")
except Exception as e:
    print(f"解析失败: {e}")
    sys.exit(1)

# 3. 执行解释器源码
print()
print("=" * 60)
print("3. 执行自举解释器")
print("=" * 60)

try:
    interp = run_source(interpreter_code)
    output = interp.get_output()
    print(f"执行成功！")
    if output:
        print(f"输出: {output[:500]}")
    else:
        print("无输出（正常）")
except Exception as e:
    print(f"执行失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("测试完成")
print("=" * 60)