#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from antlr4 import *
from LightLangLexer import LightLangLexer

def debug_tokens(source):
    """调试分词结果"""
    input_stream = InputStream(source)
    lexer = LightLangLexer(input_stream)
    
    print("分词结果:")
    print("-" * 60)
    
    token = lexer.nextToken()
    while token.type != Token.EOF:
        token_type = lexer.symbolicNames[token.type]
        print(f"行{token.line:3} 列{token.column:3}  [{token_type}] '{token.text}'")
        token = lexer.nextToken()
    
    print("-" * 60)

# 测试类定义分词
source = """【测试】
《人》类:
  定义 姓名 等于 ""。
结束。
"""

debug_tokens(source)