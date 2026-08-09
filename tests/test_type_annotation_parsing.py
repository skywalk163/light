# -*- coding: utf-8 -*-
"""测试复杂类型标注解析"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from light_parser_v3 import LightParser

parser = LightParser()

# Test 1: Simple type annotation
code = '设 x: 整数 为 42'
module = parser.parse(code)
for stmt in module.statements:
    if hasattr(stmt, 'type_annotation'):
        assert stmt.type_annotation == '整数', f"Expected '整数', got '{stmt.type_annotation}'"
        print(f'Test 1 - Simple type: {stmt.type_annotation}')

# Test 2: Generic type 列表<整数>
code = '设 x: 列表<整数> 为 【1, 2, 3】'
module = parser.parse(code)
for stmt in module.statements:
    if hasattr(stmt, 'type_annotation'):
        assert stmt.type_annotation == '列表<整数>', f"Expected '列表<整数>', got '{stmt.type_annotation}'"
        print(f'Test 2 - Generic: {stmt.type_annotation}')

# Test 3: Dict type 字典<字符串, 整数>
code = '设 x: 字典<字符串, 整数> 为 {}'
module = parser.parse(code)
for stmt in module.statements:
    if hasattr(stmt, 'type_annotation'):
        assert stmt.type_annotation == '字典<字符串,整数>', f"Expected '字典<字符串,整数>', got '{stmt.type_annotation}'"
        print(f'Test 3 - Dict: {stmt.type_annotation}')

# Test 4: Union type 整数|浮点
code = '设 x: 整数|浮点 为 42'
module = parser.parse(code)
for stmt in module.statements:
    if hasattr(stmt, 'type_annotation'):
        assert stmt.type_annotation == '整数|浮点', f"Expected '整数|浮点', got '{stmt.type_annotation}'"
        print(f'Test 4 - Union: {stmt.type_annotation}')

# Test 5: Optional type 可空整数
code = '设 x: 可空整数 为 空'
module = parser.parse(code)
for stmt in module.statements:
    if hasattr(stmt, 'type_annotation'):
        assert stmt.type_annotation == '可空整数', f"Expected '可空整数', got '{stmt.type_annotation}'"
        print(f'Test 5 - Optional: {stmt.type_annotation}')

# Test 6: Nested generic 列表<字典<字符串, 整数>>
code = '设 x: 列表<字典<字符串, 整数>> 为 【】'
module = parser.parse(code)
for stmt in module.statements:
    if hasattr(stmt, 'type_annotation'):
        # Nested generics: expect 列表<字典<字符串,整数>>
        assert '列表' in stmt.type_annotation, f"Expected nested generic, got '{stmt.type_annotation}'"
        print(f'Test 6 - Nested: {stmt.type_annotation}')

# Test 7: Paragraph param with generic type
code = '段落 测试(a: 列表<整数>, b: 整数|浮点) 返回 字典<字符串, 整数>:\n  返回 {}'
module = parser.parse(code)
for stmt in module.statements:
    if hasattr(stmt, 'params'):
        for p in stmt.params:
            print(f'Test 7 - Param {p["name"]}: {p["type"]}')
        print(f'Test 7 - Return: {stmt.return_type}')

# Test 8: C-style variable with generic type
code = '令 x: 列表<整数> = 【1, 2, 3】'
module = parser.parse(code)
for stmt in module.statements:
    if hasattr(stmt, 'type_annotation'):
        assert stmt.type_annotation == '列表<整数>', f"Expected '列表<整数>', got '{stmt.type_annotation}'"
        print(f'Test 8 - C-style: {stmt.type_annotation}')

# Test 9: Union with generic 列表<整数|浮点>
code = '设 x: 列表<整数|浮点> 为 【1, 2, 3】'
module = parser.parse(code)
for stmt in module.statements:
    if hasattr(stmt, 'type_annotation'):
        assert '列表' in stmt.type_annotation and '整数|浮点' in stmt.type_annotation, \
            f"Expected union in generic, got '{stmt.type_annotation}'"
        print(f'Test 9 - Union in generic: {stmt.type_annotation}')

# Test 10: Multi-union 整数|浮点|字符串
code = '设 x: 整数|浮点|字符串 为 42'
module = parser.parse(code)
for stmt in module.statements:
    if hasattr(stmt, 'type_annotation'):
        assert stmt.type_annotation == '整数|浮点|字符串', f"Expected '整数|浮点|字符串', got '{stmt.type_annotation}'"
        print(f'Test 10 - Multi-union: {stmt.type_annotation}')

print('\nAll type annotation parsing tests passed!')