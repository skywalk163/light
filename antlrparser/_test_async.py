"""测试 ANTLR 后端异步功能"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from light_visitor import LightParser
from light_interpreter import Interpreter, run_source
from light_ast import *

# 测试1：AsyncScope 解释执行
print("=== 测试1: AsyncScope ===")
interp = Interpreter()
scope = AsyncScope(
    line=1, column=1,
    tasks=[
        PrintStatement(value=StringLiteral(value="任务1")),
        PrintStatement(value=StringLiteral(value="任务2")),
    ]
)
interp._execute(scope)
print("输出:", interp.get_output())

# 测试2：DeferStatement 推迟栈
print("\n=== 测试2: DeferStatement ===")
interp2 = Interpreter()
defer_stmt = DeferStatement(
    line=1, column=1,
    body=[
        PrintStatement(value=StringLiteral(value="推迟执行")),
    ]
)
interp2._execute(defer_stmt)
interp2._run_defer_stack()
print("输出:", interp2.get_output())

# 测试3：AwaitExpression
print("\n=== 测试3: AwaitExpression ===")
interp3 = Interpreter()
await_expr = AwaitExpression(
    line=1, column=1,
    expression=NumberLiteral(value=42)
)
result = interp3._eval(await_expr)
print("等待结果:", result)

# 测试4：同步段内的推迟
print("\n=== 测试4: 推迟语句 ===")
source = """段落 测试推迟 接收:
  打印("开始")。
  推迟：打印("清理")。
  打印("结束")。
结束。

测试推迟()。
"""
try:
    interp4 = run_source(source)
    print("执行成功")
    print("输出:", interp4.get_output())
except Exception as e:
    print(f"执行失败: {e}")

# 测试5：异步段定义
print("\n=== 测试5: 异步段定义 ===")
source2 = """段落 读文件 接收 路径:
  返回 路径。
结束。

打印(读文件("test.txt"))。
"""
try:
    interp5 = run_source(source2)
    print("执行成功")
    print("输出:", interp5.get_output())
except Exception as e:
    print(f"执行失败: {e}")

# 测试6：异步段（带修饰符）
print("\n=== 测试6: 异步段（修饰符） ===")
source3 = """异步段落 异步任务 接收:
  打印("异步执行中")。
结束。

异步任务()。
"""
try:
    interp6 = run_source(source3)
    print("执行成功")
    print("输出:", interp6.get_output())
except Exception as e:
    print(f"执行失败: {e}")

# 测试7：等待表达式
print("\n=== 测试7: 等待表达式 ===")
source4 = """段落 取值 接收:
  返回 42。
结束。

设 结果 为 等待(取值())。
打印(结果)。
"""
try:
    interp7 = run_source(source4)
    print("执行成功")
    print("输出:", interp7.get_output())
except Exception as e:
    print(f"执行失败: {e}")

# 测试8：预处理验证
print("\n=== 测试8: 预处理验证 ===")
p = LightParser()
tests = [
    ("异步段定义", "异步段落 读文件 接收 路径:\n  返回 路径。\n结束。"),
    ("等待调用", "等待(读文件(\"test.txt\"))"),
    ("推迟语句", "推迟：打印(\"清理\")。"),
]

for name, src in tests:
    pre = p._preprocess_async(src)
    print(f"  {name}: {repr(pre)}")

print("\n=== 全部完成 ===")