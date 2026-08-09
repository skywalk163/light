#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from antlr4 import *
from LightLangLexer import LightLangLexer
from LightLangParser import LightLangParser
from antlr4.error.ErrorListener import ErrorListener

class VerboseErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        print(f"\n[语法错误] 行{line}, 列{column}: {msg}")
        print(f"  期望的 token: {recognizer.getExpectedTokens().toString(recognizer.literalNames, recognizer.symbolicNames)}")
        if offendingSymbol:
            print(f"  实际的 token: {offendingSymbol.text} (类型: {recognizer.symbolicNames[offendingSymbol.type]})")

def test_parser(source):
    input_stream = InputStream(source)
    lexer = LightLangLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = LightLangParser(token_stream)
    
    # 添加详细错误监听
    parser.removeErrorListeners()
    parser.addErrorListener(VerboseErrorListener())
    
    print("解析源代码:")
    print(source)
    print("-" * 60)
    
    tree = parser.program()
    print("\n解析完成!")
    print(f"语法错误数: {parser.getNumberOfSyntaxErrors()}")

# 测试简单的类定义
source = """【测试】
《人》类:
  定义 姓名 等于 ""。
结束。
"""

test_parser(source)