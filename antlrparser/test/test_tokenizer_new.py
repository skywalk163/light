#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_tokenizer import LightLangTokenizer

source = "新 人()"
tokenizer = LightLangTokenizer()
tokens = tokenizer.tokenize(source)

print("分词结果:")
for token in tokens:
    print(f"  [{token.type_name}] '{token.text}'")