#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_tokenizer import LightLangTokenizer

def test_custom_tokenizer(source):
    """测试自定义分词器"""
    tokenizer = LightLangTokenizer()
    tokens = tokenizer.tokenize(source)
    
    print("自定义分词器结果:")
    print("-" * 60)
    
    for token in tokens:
        print(f"行{token.line:3} 列{token.column:3}  [{token.type_name}] '{token.text}'")
    
    print("-" * 60)

# 测试类定义分词
source = """【测试】
《人》类:
  定义 姓名 等于 ""。
结束。
"""

test_custom_tokenizer(source)