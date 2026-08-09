#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_visitor import parse_source

source = """
《人》类:
  定义 姓名 等于 ""。
结束。

定义 某人 等于 新 人()。
"""

module = parse_source(source)

# 检查变量声明的表达式
stmt = module.statements[0]
print(f"语句类型: {type(stmt).__name__}")
print(f"变量名: {stmt.name}")
print(f"表达式类型: {type(stmt.value).__name__}")

# 检查表达式详情
if hasattr(stmt.value, 'class_name'):
    print(f"类名: {stmt.value.class_name}")
else:
    print("表达式没有 class_name 属性")
    # 打印表达式的所有属性
    print(f"表达式属性: {dir(stmt.value)}")