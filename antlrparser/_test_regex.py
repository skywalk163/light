"""检查正则表达式"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from light_visitor import LightParser

p = LightParser()
src = "异步段落 异步任务 接收:\n  打印(\"异步执行中\")。\n结束。\n\n异步任务()。"
print("源:", repr(src))
result = p._preprocess_async(src)
print("结果:", repr(result))

# 也测试有空格的情况
src2 = "异步 段落 普通任务 接收:\n  打印(\"普通\")。\n结束。"
print("\n源2:", repr(src2))
result2 = p._preprocess_async(src2)
print("结果2:", repr(result2))