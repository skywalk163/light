#!/usr/bin/env python3
import sys
sys.path.insert(0, 'antlrparser')

from light_visitor import parse_source

code = """
设 甲 为 10。
打印 甲。
"""

module = parse_source(code)
if module:
    print(f"解析成功，语句数: {len(module.statements)}")
    for i, stmt in enumerate(module.statements):
        print(f"  语句{i}: {type(stmt).__name__}")
else:
    print("解析失败")
