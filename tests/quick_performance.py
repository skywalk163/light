# -*- coding: utf-8 -*-
"""
光明编译器 - 快速性能测试
"""

import sys
import os
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer
from light_parser_v3 import LightParser

print("=" * 60)
print("光明编译器快速性能测试")
print("=" * 60)

# 测试1：词法分析器
print("\n[测试1] 词法分析器 - 简单变量")
lexer = Lexer()
code = '设甲为123。'

start = time.time()
for _ in range(1000):
    tokens = lexer.tokenize(code)
end = time.time()

print(f"  代码: {code}")
print(f"  迭代次数: 1000")
print(f"  总时间: {(end - start) * 1000:.2f} ms")
print(f"  平均时间: {(end - start) * 1000 / 1000:.3f} ms/次")
print(f"  Token数量: {len(tokens)}")

# 测试2：语法解析器
print("\n[测试2] 语法解析器 - 简单变量")
parser = LightParser()

start = time.time()
for _ in range(100):
    module = parser.parse(code)
end = time.time()

print(f"  代码: {code}")
print(f"  迭代次数: 100")
print(f"  总时间: {(end - start) * 1000:.2f} ms")
print(f"  平均时间: {(end - start) * 1000 / 100:.3f} ms/次")
print(f"  语句数量: {len(module.statements)}")

# 测试3：完整编译（单次）
print("\n[测试3] 完整编译 - 单次执行")
from semantic_analyzer import SemanticAnalyzer
from code_generator import PythonCodeGenerator

analyzer = SemanticAnalyzer()
generator = PythonCodeGenerator()

start = time.time()
tokens = lexer.tokenize(code)
end1 = time.time()
module = parser.parse(code)
end2 = time.time()
analyzer.analyze(module)
end3 = time.time()
python_code = generator.generate(module)
end4 = time.time()

print(f"  词法分析: {(end1 - start) * 1000:.3f} ms")
print(f"  语法解析: {(end2 - end1) * 1000:.3f} ms")
print(f"  语义分析: {(end3 - end2) * 1000:.3f} ms")
print(f"  代码生成: {(end4 - end3) * 1000:.3f} ms")
print(f"  总时间: {(end4 - start) * 1000:.3f} ms")
print(f"  输出长度: {len(python_code)} 字符")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
