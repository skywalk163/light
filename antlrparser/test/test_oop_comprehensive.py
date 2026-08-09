#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_interpreter import Interpreter
from light_visitor import parse_source

source_code = """
《人》类:
  定义 姓名 等于 ""。
  定义 年龄 等于 0。
  
  《初始化》方法(姓名参数, 年龄参数):
    姓名 等于 姓名参数。
    年龄 等于 年龄参数。
  结束。
  
  《说话》方法():
    打印(姓名 + "，年龄: " + _串化(年龄))。
  结束。
  
  《成长》方法(年数):
    年龄 等于 年龄 + 年数。
    打印(姓名 + "长大了" + _串化(年数) + "岁")。
  结束。
结束。

定义 张三 等于 新 人("张三", 25)。
张三之说话()。
张三之成长(3)。
张三之说话()。

定义 李四 等于 新 人("李四", 30)。
李四之说话()。
"""

print("=== 综合 OOP 测试 ===")
print("源代码:\n", source_code)

try:
    module = parse_source(source_code)
    interpreter = Interpreter()
    result = interpreter.interpret_module(module)
    print("\n=== 执行成功 ===")
except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()