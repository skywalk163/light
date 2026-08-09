#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_visitor import parse_source
from light_interpreter import Interpreter

source = """
《人》类:
  定义 姓名 等于 ""。
结束。

定义 某人 等于 新 人()。
"""

module = parse_source(source)

# 添加调试
interpreter = Interpreter()
print("=== 执行前 ===")
print(f"环境中 '人' 的类型: {interpreter.env.get('人').type_name if interpreter.env.has('人') else '不存在'}")

# 执行第一个语句（类定义已在模块解释时注册）
interpreter._interpret_module(module)

print("\n=== 执行后 ===")
print(f"环境中 '人' 的类型: {interpreter.env.get('人').type_name}")
print(f"环境中 '某人' 的类型: {interpreter.env.get('某人').type_name}")
print(f"某人的值: {interpreter.env.get('某人').value}")