#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_visitor import parse_source
from light_interpreter import Interpreter

# 简单测试：类定义和实例化
source = """
《人》类:
  定义 姓名 等于 ""。
  《说话》方法():
    打印(姓名)。
  结束。
结束。

定义 某人 等于 新 人()。
某人之姓名 等于 "张三"。
某人之说话()。
"""

print("源代码:")
print(source)
print("-" * 40)

# 解析
module = parse_source(source)
print(f"类数量: {len(module.classes)}")
print(f"语句数量: {len(module.statements)}")

# 创建解释器并执行
interpreter = Interpreter()
interpreter.interpret_module(module)
print(f"\n输出:\n{interpreter.get_output()}")