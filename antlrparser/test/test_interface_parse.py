#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_visitor import parse_source

def test_interface_parse():
    source = """【测试模块】
《可飞行》接口:
  《飞》方法() -> 空。
结束。

《人》类 使用 可飞行:
  定义 姓名 等于 ""。
  《飞》方法():
    打印(姓名 + "正在飞")。
  结束。
结束。
"""
    
    try:
        module = parse_source(source)
        print("解析成功!")
        
        print(f'模块名: {module.name}')
        print(f'类数量: {len(module.classes)}')
        print(f'接口数量: {len(module.interfaces)}')
        
        if module.interfaces:
            iface = module.interfaces[0]
            print(f'接口名: {iface.name}')
            print(f'父接口: {iface.superinterfaces}')
            print(f'方法签名: {[m.name for m in iface.methods]}')
        
        if module.classes:
            cls = module.classes[0]
            print(f'类名: {cls.name}')
            print(f'父类: {cls.superclasses}')
            print(f'实现接口: {cls.interfaces}')
            print(f'字段: {[f.name for f in cls.fields]}')
            print(f'方法: {[m.name for m in cls.methods]}')
            
    except Exception as e:
        print(f'解析失败: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_interface_parse()