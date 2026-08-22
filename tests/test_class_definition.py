# -*- coding: utf-8 -*-
"""
光明编译器 - 类定义功能测试

测试类定义的解析和代码生成
"""

import sys
import os
import io

# 设置UTF-8编码输出（使用reconfigure避免关闭底层buffer）
# errors='replace' 不是可选项：pytest 下 sys.stdout 是**全场共用**的捕获流，
# 这里一旦把它收成 strict UTF-8，后面任何用例的孙进程往同一个 fd 写 GBK/ANSI
# 字节，就会在 teardown 抛 UnicodeDecodeError，并且从那条用例起整场
# setup/teardown 连锁报错（实测约 3565 errors、约 1780 条用例根本没真跑）。
# PYTHONUTF8=1 挡不住——reconfigure 的 strict errors 覆盖了它。
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import (
    ClassDefinition, AttributeDeclaration, MethodDefinition,
    Parameter, Module, Identifier
)
from code_generator import PythonCodeGenerator


def test_class_definition_generation():
    """测试类定义代码生成"""
    print("=" * 60)
    print("光明编译器 - 类定义功能测试")
    print("=" * 60)
    
    # 创建一个简单的学生类AST
    student_class = ClassDefinition(
        name='学生',
        base_classes=None,
        attributes=[
            AttributeDeclaration(
                name='姓名',
                type_annotation='str',
                default_value=None
            ),
            AttributeDeclaration(
                name='年龄',
                type_annotation='int',
                default_value=None
            ),
        ],
        methods=[
            MethodDefinition(
                name='构造',
                parameters=[
                    Parameter(name='姓名'),
                    Parameter(name='年龄'),
                ],
                body=[
                    ('var', 'self.姓名', Identifier('姓名')),
                    ('var', 'self.年龄', Identifier('年龄')),
                ],
                is_constructor=True
            ),
            MethodDefinition(
                name='介绍',
                parameters=[],
                body=[
                    ('return', None),
                ],
                is_constructor=False
            ),
        ]
    )
    
    # 创建模块
    module = Module(
        statements=[student_class]
    )
    
    # 生成Python代码
    generator = PythonCodeGenerator()
    python_code = generator.generate(module)
    
    print("\n生成的Python代码：")
    print("-" * 60)
    print(python_code)
    print("-" * 60)
    
    # 验证生成的代码
    assert 'class 学生:' in python_code, "应该包含类定义"
    assert 'def __init__(self, 姓名, 年龄):' in python_code, "应该包含构造函数"
    assert 'def 介绍(self):' in python_code, "应该包含方法定义"
    
    print("\n✅ 测试通过！")
    
    # 尝试执行生成的代码
    print("\n尝试执行生成的代码：")
    print("-" * 60)
    try:
        exec_globals = {}
        exec(python_code, exec_globals)
        print("✅ 代码执行成功！")
        
        # 创建实例
        if '学生' in exec_globals:
            student = exec_globals['学生']('张三', 20)
            print(f"✅ 成功创建实例：{student}")
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_class_definition_generation()
