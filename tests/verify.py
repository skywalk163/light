# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 简单验证测试
"""

import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print("=" * 60)
print("光明编译器验证测试")
print("=" * 60)

# 测试1：词法分析器
print("\n[1/8] 词法分析器...")
try:
    from lexer import Lexer
    lexer = Lexer()
    tokens = lexer.tokenize('设甲为三。')
    print(f"  OK - 生成 {len(tokens)} 个token")
except Exception as e:
    print(f"  FAIL - {e}")

# 测试2：语法解析器
print("\n[2/8] 语法解析器...")
try:
    from light_parser_v3 import LightParser
    parser = LightParser()
    module = parser.parse('设甲为123。')
    print(f"  OK - 解析 {len(module.statements)} 条语句")
except Exception as e:
    print(f"  FAIL - {e}")

# 测试3：语义分析器
print("\n[3/8] 语义分析器...")
try:
    from semantic_analyzer import SemanticAnalyzer
    analyzer = SemanticAnalyzer()
    print("  OK - 初始化成功")
except Exception as e:
    print(f"  FAIL - {e}")

# 测试4：代码生成器
print("\n[4/8] 代码生成器...")
try:
    from code_generator import PythonCodeGenerator
    generator = PythonCodeGenerator()
    print("  OK - 初始化成功")
except Exception as e:
    print(f"  FAIL - {e}")

# 测试5：动词信息
print("\n[5/8] 动词信息模块...")
try:
    from verb_info import get_verb_info
    info = get_verb_info('加')
    print(f"  OK - '加' 元数={info.arity}, 模式={info.mode}")
except Exception as e:
    print(f"  FAIL - {e}")

# 测试6：语义识别器
print("\n[6/8] 语义识别器...")
try:
    from semantic_identifier import SemanticIdentifier
    identifier = SemanticIdentifier({})
    print("  OK - 初始化成功")
except Exception as e:
    print(f"  FAIL - {e}")

# 测试7：完整编译
print("\n[7/8] 完整编译流程...")
try:
    from light_parser_v3 import LightParser
    from semantic_analyzer import SemanticAnalyzer
    from code_generator import PythonCodeGenerator
    
    parser = LightParser()
    analyzer = SemanticAnalyzer()
    generator = PythonCodeGenerator()
    
    code = '设甲为三加五。'
    module = parser.parse(code)
    analyzer.analyze(module)
    python_code = generator.generate(module)
    
    print(f"  OK - Python: {python_code.strip()[:50]}...")
except Exception as e:
    print(f"  FAIL - {e}")

# 测试8：函数编译
print("\n[8/8] 函数编译...")
try:
    from light_parser_v3 import LightParser
    from semantic_analyzer import SemanticAnalyzer
    from code_generator import PythonCodeGenerator
    
    parser = LightParser()
    analyzer = SemanticAnalyzer()
    generator = PythonCodeGenerator()
    
    code = '《加法》段(甲, 乙)：返回甲加乙。'
    module = parser.parse(code)
    analyzer.analyze(module)
    python_code = generator.generate(module)
    
    has_def = 'def' in python_code
    has_return = 'return' in python_code
    
    print(f"  OK - def:{has_def}, return:{has_return}")
except Exception as e:
    print(f"  FAIL - {e}")

print()
print("=" * 60)
print("验证完成")
print("=" * 60)