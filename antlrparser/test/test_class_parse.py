#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_visitor import parse_source

def test_class_parse():
    source = """
【测试模块】
《人》类:
  定义 姓名 等于 ""。
  《说话》方法():
    打印(姓名)。
  结束。
结束。
"""
    
    try:
        module = parse_source(source)
        print("解析成功!")
        
        print(f'模块名: {module.name}')
        print(f'类数量: {len(module.classes)}')
        print(f'接口数量: {len(module.interfaces)}')
        
        if module.classes:
            cls = module.classes[0]
            print(f'类名: {cls.name}')
            print(f'字段: {[f.name for f in cls.fields]}')
            print(f'方法: {[m.name for m in cls.methods]}')
            
    except Exception as e:
        print(f'解析失败: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_class_parse()