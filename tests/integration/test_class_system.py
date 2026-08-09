# -*- coding: utf-8 -*-
"""
光明编译器 - 类系统集成测试

测试类定义、继承、构造函数、方法调用、方法重写等核心功能。
"""

import sys
import os
import io
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from compiler import LightCompiler
from code_generator_unified import UnifiedCodeGenerator


def compile_and_run(source):
    """编译并运行光明代码，返回输出结果"""
    compiler = LightCompiler()
    result = compiler.compile(source)
    ast = result['ast']

    codegen = UnifiedCodeGenerator()
    python_code = codegen.generate(ast)

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(python_code, {})
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    return output


class TestClassBasic:
    """基本类定义测试"""

    def test_simple_class_definition(self):
        """测试简单类定义"""
        source = '''类 动物：
  段落 叫声：
    打印 "动物叫声"

设 一只动物 为 新建 动物()
一只动物.叫声()
'''
        output = compile_and_run(source)
        assert '动物叫声' in output

    def test_class_with_attributes(self):
        """测试带属性的类"""
        source = '''类 人：
  属性 姓名
  属性 年龄
  构造 接收 姓名, 年龄：
    己姓名 为 姓名
    己年龄 为 年龄
  段落 介绍：
    打印 己姓名
    打印 己年龄

设 张三 为 新建 人("张三", 25)
张三.介绍()
'''
        output = compile_and_run(source)
        assert '张三' in output
        assert '25' in output


class TestClassInheritance:
    """类继承测试"""

    def test_basic_inheritance(self):
        """测试基本继承"""
        source = '''类 动物：
  段落 叫声：
    打印 "动物叫声"

类 狗 继承 动物：
  段落 叫声：
    打印 "汪汪汪"

设 小狗 为 新建 狗()
小狗.叫声()
'''
        output = compile_and_run(source)
        assert '汪汪汪' in output

    def test_inherited_method(self):
        """测试继承父类方法"""
        source = '''类 动物：
  段落 呼吸：
    打印 "呼吸中"

类 狗 继承 动物：
  段落 叫声：
    打印 "汪汪汪"

设 小狗 为 新建 狗()
小狗.呼吸()
小狗.叫声()
'''
        output = compile_and_run(source)
        assert '呼吸中' in output
        assert '汪汪汪' in output

    def test_constructor_with_inheritance(self):
        """测试带继承的构造函数"""
        source = '''类 动物：
  属性 品种
  构造 接收 品种：
    己品种 为 品种

类 狗 继承 动物：
  属性 名字
  构造 接收 名字：
    己名字 为 名字
    己品种 为 "金毛"
  段落 介绍：
    打印 己名字
    打印 己品种

设 旺财 为 新建 狗("旺财")
旺财.介绍()
'''
        output = compile_and_run(source)
        assert '旺财' in output
        assert '金毛' in output


class TestMethodOverride:
    """方法重写测试"""

    def test_method_override(self):
        """测试方法重写"""
        source = '''类 形状：
  段落 面积：
    打印 0

类 圆形 继承 形状：
  属性 半径
  构造 接收 半径：
    己半径 为 半径
  段落 面积：
    打印 己半径 乘 己半径 乘 3.14

设 圆 为 新建 圆形(5)
圆.面积()
'''
        output = compile_and_run(source)
        assert '78.5' in output

    def test_multiple_subclasses(self):
        """测试多个子类"""
        source = '''类 动物：
  段落 叫声：
    打印 "..."

类 狗 继承 动物：
  段落 叫声：
    打印 "汪汪汪"

类 猫 继承 动物：
  段落 叫声：
    打印 "喵喵喵"

设 小狗 为 新建 狗()
设 小猫 为 新建 猫()
小狗.叫声()
小猫.叫声()
'''
        output = compile_and_run(source)
        assert '汪汪汪' in output
        assert '喵喵喵' in output


class TestMultipleClasses:
    """多类定义测试"""

    def test_multiple_classes_in_one_file(self):
        """测试同一文件中定义多个类"""
        source = '''类 汽车：
  属性 品牌
  构造 接收 品牌：
    己品牌 为 品牌
  段落 启动：
    打印 己品牌 加 "启动了"

类 自行车：
  属性 颜色
  构造 接收 颜色：
    己颜色 为 颜色
  段落 骑行：
    打印 己颜色 加 "自行车在骑行"

设 小车 为 新建 汽车("丰田")
设 单车 为 新建 自行车("红色")
小车.启动()
单车.骑行()
'''
        output = compile_and_run(source)
        assert '丰田启动了' in output
        assert '红色自行车在骑行' in output


class TestClassAdvanced:
    """高级类功能测试"""

    def test_method_with_parameters(self):
        """测试带参数的方法"""
        source = '''类 计算器：
  段落 相加 接收 a, b：
    打印 a 加 b
  段落 相乘 接收 a, b：
    打印 a 乘 b

设  calc 为 新建 计算器()
calc.相加(3, 5)
calc.相乘(4, 6)
'''
        output = compile_and_run(source)
        assert '8' in output
        assert '24' in output

    def test_self_method_call(self):
        """测试类内部属性访问"""
        source = '''类 计数器：
  属性 值
  构造：
    己值 为 0
  段落 增加：
    己值 为 己值 加 1
  段落 获取值：
    打印 己值

设 计数 为 新建 计数器()
计数.增加()
计数.增加()
计数.增加()
计数.获取值()
'''
        output = compile_and_run(source)
        assert '3' in output
