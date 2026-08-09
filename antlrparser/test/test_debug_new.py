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
print(f"语句数量: {len(module.statements)}")
for i, stmt in enumerate(module.statements):
    print(f"语句 {i}: {type(stmt).__name__}")
    if hasattr(stmt, 'expression'):
        print(f"  表达式: {type(stmt.expression).__name__}")
        if hasattr(stmt.expression, 'class_name'):
            print(f"    类名: {stmt.expression.class_name}")