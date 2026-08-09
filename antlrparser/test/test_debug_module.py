#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_visitor import parse_source

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

module = parse_source(source)
print(f"类数量: {len(module.classes)}")
print(f"段落数量: {len(module.segments)}")
print(f"接口数量: {len(module.interfaces)}")
print(f"语句数量: {len(module.statements)}")

print("\n语句详情:")
for i, stmt in enumerate(module.statements):
    print(f"语句 {i}: {type(stmt).__name__}")
    if hasattr(stmt, 'name'):
        print(f"  名称: {stmt.name}")
    if hasattr(stmt, 'expression'):
        expr = stmt.expression
        print(f"  表达式类型: {type(expr).__name__}")
        if hasattr(expr, 'class_name'):
            print(f"    类名: {expr.class_name}")
    if hasattr(stmt, 'target'):
        print(f"  目标: {type(stmt.target).__name__}")