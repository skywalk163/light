# -*- coding: utf-8 -*-
"""
Light 语言类型推断模块性能分析脚本

使用 cProfile 分析 TypeInferencer.infer() 调用性能
"""
import sys
import os
import cProfile
import pstats
import io

# ============================================================
# 1. 设置 sys.path
# ============================================================
_project_root = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)

# ============================================================
# 2. 导入所需模块
# ============================================================
from type_inferencer import TypeInferencer
from ast_nodes import (
    Module, SegmentDefinition, ClassDefinition, MethodDefinition,
    ConstructorDefinition, Parameter, VariableDeclaration, Assignment,
    IfStatement, WhileStatement, ForeachStatement, ReturnStatement,
    PrintStatement, ExpressionStatement, BinaryOp, UnaryOp,
    FunctionCall, Identifier, NumberLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, ListLiteral, DictLiteral, DictEntry,
    NewExpression, PropertyAccess, IndexAccess, SelfReference,
    LambdaExpression, ConditionalExpression, ListComprehension,
    EnumDefinition, EnumVariant, DataTypeField,
    TraitDefinition, TraitMethodSignature, TraitImplementation,
)


def make_identifier(name):
    return Identifier(name=name)


def make_number(value):
    return NumberLiteral(value=value)


def make_string(value):
    return StringLiteral(value=value)


def make_bool(value):
    return BooleanLiteral(value=value)


def make_call(name, *args):
    return FunctionCall(name=make_identifier(name), arguments=list(args))


def make_binary(left, op, right):
    return BinaryOp(left=left, operator=op, right=right)


def make_return(value=None):
    return ReturnStatement(value=value)


def make_var(name, value, type_annotation=None):
    return VariableDeclaration(name=name, value=value, type_annotation=type_annotation)


def make_param(name, type_annotation=None):
    return Parameter(name=name, type_annotation=type_annotation)


# ============================================================
# 3. 构建真实的测试模块 (~50 段, ~200 语句)
# ============================================================

def create_realistic_module():
    """创建一个包含多种语言特性的测试模块"""
    segments = []
    classes = []
    enums = []
    trait_defs = []
    trait_impls = []
    statements = []

    # ---- 枚举定义 ----
    enums.append(EnumDefinition(
        name="颜色",
        variants=[
            EnumVariant(name="红", fields=[]),
            EnumVariant(name="绿", fields=[]),
            EnumVariant(name="蓝", fields=[]),
        ]
    ))

    enums.append(EnumDefinition(
        name="结果",
        variants=[
            EnumVariant(name="成功", fields=[DataTypeField(name="值", type_annotation="串")]),
            EnumVariant(name="失败", fields=[DataTypeField(name="错误", type_annotation="串")]),
        ]
    ))

    # ---- Trait 定义 ----
    trait_defs.append(TraitDefinition(
        name="可比较",
        methods=[
            TraitMethodSignature(name="比较", parameters=[make_param("其他", "可比较")], return_type="布尔"),
        ]
    ))

    # ---- 类定义 ----
    # 简单类
    simple_class = ClassDefinition(
        name="点",
        constructor=ConstructorDefinition(
            name="新建",
            parameters=[make_param("x", "数"), make_param("y", "数")],
            body=[
                Assignment(target=make_identifier("x"), value=make_identifier("x")),
                Assignment(target=make_identifier("y"), value=make_identifier("y")),
            ]
        ),
        methods=[
            MethodDefinition(
                name="距离",
                parameters=[make_param("其他", "点")],
                return_type="数",
                body=[
                    make_return(make_binary(
                        make_binary(make_identifier("x"), "-", make_identifier("其他.x")),
                        "*",
                        make_binary(make_identifier("y"), "-", make_identifier("其他.y")),
                    ))
                ]
            ),
            MethodDefinition(
                name="平移",
                parameters=[make_param("dx", "数"), make_param("dy", "数")],
                body=[
                    ExpressionStatement(make_call("点.平移内部", make_identifier("dx"), make_identifier("dy"))),
                ]
            ),
        ]
    )
    classes.append(simple_class)

    # 泛型类
    generic_class = ClassDefinition(
        name="容器",
        generic_params=["T"],
        constructor=ConstructorDefinition(
            name="新建",
            parameters=[make_param("值", "T")],
            body=[
                Assignment(target=make_identifier("值"), value=make_identifier("值")),
            ]
        ),
        methods=[
            MethodDefinition(
                name="获取",
                parameters=[],
                return_type="T",
                body=[make_return(make_identifier("值"))],
            ),
            MethodDefinition(
                name="设置",
                parameters=[make_param("新值", "T")],
                body=[
                    Assignment(target=make_identifier("值"), value=make_identifier("新值")),
                ]
            ),
        ]
    )
    classes.append(generic_class)

    # 带接口实现的类
    interface_class = ClassDefinition(
        name="整数",
        interfaces=["可比较"],
        constructor=ConstructorDefinition(
            name="新建",
            parameters=[make_param("值", "数")],
            body=[
                Assignment(target=make_identifier("值"), value=make_identifier("值")),
            ]
        ),
        methods=[
            MethodDefinition(
                name="比较",
                parameters=[make_param("其他", "整数")],
                return_type="布尔",
                body=[
                    make_return(make_binary(make_identifier("值"), ">", make_identifier("其他.值"))),
                ]
            ),
        ]
    )
    classes.append(interface_class)

    # Trait 实现
    trait_impls.append(TraitImplementation(
        trait_name="可比较",
        type_name="整数",
        methods=[
            MethodDefinition(
                name="比较",
                parameters=[make_param("其他", "整数")],
                return_type="布尔",
                body=[make_return(make_bool(True))],
            )
        ]
    ))

    # ---- 段落定义 (约 45 个段) ----
    # 简单计算函数
    segments.append(SegmentDefinition(
        name="加法",
        parameters=[make_param("甲", "数"), make_param("乙", "数")],
        return_type="数",
        body=[make_return(make_binary(make_identifier("甲"), "+", make_identifier("乙")))],
    ))

    segments.append(SegmentDefinition(
        name="减法",
        parameters=[make_param("甲", "数"), make_param("乙", "数")],
        return_type="数",
        body=[make_return(make_binary(make_identifier("甲"), "-", make_identifier("乙")))],
    ))

    segments.append(SegmentDefinition(
        name="乘法",
        parameters=[make_param("甲", "数"), make_param("乙", "数")],
        return_type="数",
        body=[make_return(make_binary(make_identifier("甲"), "*", make_identifier("乙")))],
    ))

    segments.append(SegmentDefinition(
        name="除法",
        parameters=[make_param("甲", "数"), make_param("乙", "数")],
        return_type="数",
        body=[make_return(make_binary(make_identifier("甲"), "/", make_identifier("乙")))],
    ))

    # 字符串操作
    segments.append(SegmentDefinition(
        name="拼接",
        parameters=[make_param("甲", "串"), make_param("乙", "串")],
        return_type="串",
        body=[make_return(make_binary(make_identifier("甲"), "+", make_identifier("乙")))],
    ))

    segments.append(SegmentDefinition(
        name="问候",
        parameters=[make_param("名字", "串")],
        return_type="串",
        body=[
            make_var("前缀", make_string("你好，")),
            make_var("后缀", make_string("！")),
            make_return(make_binary(
                make_binary(make_identifier("前缀"), "+", make_identifier("名字")),
                "+",
                make_identifier("后缀"),
            )),
        ],
    ))

    # 条件逻辑
    segments.append(SegmentDefinition(
        name="最大值",
        parameters=[make_param("甲", "数"), make_param("乙", "数")],
        return_type="数",
        body=[
            make_var("结果", make_number(0)),
            IfStatement(
                condition=make_binary(make_identifier("甲"), ">", make_identifier("乙")),
                then_body=[
                    Assignment(target=make_identifier("结果"), value=make_identifier("甲")),
                ],
                else_body=[
                    Assignment(target=make_identifier("结果"), value=make_identifier("乙")),
                ],
            ),
            make_return(make_identifier("结果")),
        ],
    ))

    segments.append(SegmentDefinition(
        name="绝对值",
        parameters=[make_param("值", "数")],
        return_type="数",
        body=[
            IfStatement(
                condition=make_binary(make_identifier("值"), "<", make_number(0)),
                then_body=[
                    make_return(make_binary(make_number(0), "-", make_identifier("值"))),
                ],
                else_body=[
                    make_return(make_identifier("值")),
                ],
            ),
        ],
    ))

    segments.append(SegmentDefinition(
        name="判断正负",
        parameters=[make_param("值", "数")],
        return_type="串",
        body=[
            make_var("结果", make_string("")),
            IfStatement(
                condition=make_binary(make_identifier("值"), ">", make_number(0)),
                then_body=[
                    Assignment(target=make_identifier("结果"), value=make_string("正数")),
                ],
                else_body=[
                    IfStatement(
                        condition=make_binary(make_identifier("值"), "<", make_number(0)),
                        then_body=[
                            Assignment(target=make_identifier("结果"), value=make_string("负数")),
                        ],
                        else_body=[
                            Assignment(target=make_identifier("结果"), value=make_string("零")),
                        ],
                    ),
                ],
            ),
            make_return(make_identifier("结果")),
        ],
    ))

    # 循环
    segments.append(SegmentDefinition(
        name="累加求和",
        parameters=[make_param("上限", "数")],
        return_type="数",
        body=[
            make_var("总和", make_number(0)),
            make_var("索引", make_number(0)),
            WhileStatement(
                condition=make_binary(make_identifier("索引"), "<", make_identifier("上限")),
                body=[
                    Assignment(
                        target=make_identifier("总和"),
                        value=make_binary(make_identifier("总和"), "+", make_identifier("索引")),
                    ),
                    Assignment(
                        target=make_identifier("索引"),
                        value=make_binary(make_identifier("索引"), "+", make_number(1)),
                    ),
                ],
            ),
            make_return(make_identifier("总和")),
        ],
    ))

    segments.append(SegmentDefinition(
        name="列表求和",
        parameters=[make_param("列表", "列表[数]")],
        return_type="数",
        body=[
            make_var("总和", make_number(0)),
            ForeachStatement(
                variable="元素",
                iterable=make_identifier("列表"),
                body=[
                    Assignment(
                        target=make_identifier("总和"),
                        value=make_binary(make_identifier("总和"), "+", make_identifier("元素")),
                    ),
                ],
            ),
            make_return(make_identifier("总和")),
        ],
    ))

    segments.append(SegmentDefinition(
        name="列表映射",
        parameters=[make_param("列表", "列表[数]"), make_param("倍数", "数")],
        return_type="列表[数]",
        body=[
            make_var("结果", ListLiteral(elements=[])),
            ForeachStatement(
                variable="元素",
                iterable=make_identifier("列表"),
                body=[
                    ExpressionStatement(make_call("列表追加", make_identifier("结果"),
                                          make_binary(make_identifier("元素"), "*", make_identifier("倍数")))),
                ],
            ),
            make_return(make_identifier("结果")),
        ],
    ))

    segments.append(SegmentDefinition(
        name="斐波那契",
        parameters=[make_param("n", "数")],
        return_type="数",
        body=[
            IfStatement(
                condition=make_binary(make_identifier("n"), "<=", make_number(1)),
                then_body=[make_return(make_identifier("n"))],
                else_body=[
                    make_return(make_binary(
                        make_call("斐波那契", make_binary(make_identifier("n"), "-", make_number(1))),
                        "+",
                        make_call("斐波那契", make_binary(make_identifier("n"), "-", make_number(2))),
                    )),
                ],
            ),
        ],
    ))

    # 列表与字典操作
    segments.append(SegmentDefinition(
        name="创建列表",
        parameters=[],
        return_type="列表[数]",
        body=[
            make_return(ListLiteral(elements=[make_number(1), make_number(2), make_number(3), make_number(4), make_number(5)])),
        ],
    ))

    segments.append(SegmentDefinition(
        name="创建字典",
        parameters=[],
        return_type="字典[串: 数]",
        body=[
            make_return(DictLiteral(entries=[
                DictEntry(key=make_string("甲"), value=make_number(1)),
                DictEntry(key=make_string("乙"), value=make_number(2)),
                DictEntry(key=make_string("丙"), value=make_number(3)),
            ])),
        ],
    ))

    segments.append(SegmentDefinition(
        name="字典查找",
        parameters=[make_param("字典", "字典[串: 数]"), make_param("键", "串")],
        return_type="数",
        body=[
            make_return(IndexAccess(obj=make_identifier("字典"), index=make_identifier("键"))),
        ],
    ))

    segments.append(SegmentDefinition(
        name="列表推导测试",
        parameters=[],
        return_type="列表[数]",
        body=[
            make_return(ListComprehension(
                expression=make_binary(make_identifier("x"), "*", make_number(2)),
                variable="x",
                iterable=make_call("创建列表"),
            )),
        ],
    ))

    # 泛型函数
    segments.append(SegmentDefinition(
        name="恒等",
        generic_params=["T"],
        parameters=[make_param("值", "T")],
        return_type="T",
        body=[make_return(make_identifier("值"))],
    ))

    segments.append(SegmentDefinition(
        name="交换",
        generic_params=["T"],
        parameters=[make_param("甲", "T"), make_param("乙", "T")],
        return_type="元组[T, T]",
        body=[
            make_return(ListLiteral(elements=[make_identifier("乙"), make_identifier("甲")])),
        ],
    ))

    segments.append(SegmentDefinition(
        name="数组长度",
        generic_params=["T"],
        parameters=[make_param("数组", "列表[T]")],
        return_type="数",
        body=[make_return(make_call("长度", make_identifier("数组")))],
    ))

    segments.append(SegmentDefinition(
        name="获取首元素",
        generic_params=["T"],
        parameters=[make_param("列表", "列表[T]")],
        return_type="T",
        body=[
            make_return(IndexAccess(obj=make_identifier("列表"), index=make_number(0))),
        ],
    ))

    segments.append(SegmentDefinition(
        name="映射泛型",
        generic_params=["T", "U"],
        parameters=[make_param("列表", "列表[T]"), make_param("函数", "T -> U")],
        return_type="列表[U]",
        body=[
            make_var("结果", ListLiteral(elements=[])),
            ForeachStatement(
                variable="元素",
                iterable=make_identifier("列表"),
                body=[
                    ExpressionStatement(make_call("列表追加", make_identifier("结果"),
                                          make_call("函数", make_identifier("元素")))),
                ],
            ),
            make_return(make_identifier("结果")),
        ],
    ))

    # 类实例化
    segments.append(SegmentDefinition(
        name="创建点",
        parameters=[],
        return_type="点",
        body=[
            make_return(NewExpression(class_name="点", arguments=[make_number(0), make_number(0)])),
        ],
    ))

    segments.append(SegmentDefinition(
        name="使用容器",
        parameters=[],
        return_type="容器[数]",
        body=[
            make_var("c", NewExpression(class_name="容器", arguments=[make_number(42)], type_args=["数"])),
            make_return(make_identifier("c")),
        ],
    ))

    segments.append(SegmentDefinition(
        name="点距离计算",
        parameters=[make_param("p1", "点"), make_param("p2", "点")],
        return_type="数",
        body=[
            make_return(PropertyAccess(obj=make_identifier("p1"), property_name="距离")),
        ],
    ))

    # Lambda 表达式
    segments.append(SegmentDefinition(
        name="使用Lambda",
        parameters=[make_param("列表", "列表[数]")],
        return_type="列表[数]",
        body=[
            make_var("加倍", LambdaExpression(
                parameters=[make_param("x")],
                body=make_binary(make_identifier("x"), "*", make_number(2)),
            )),
            make_return(make_call("映射", make_identifier("列表"), make_identifier("加倍"))),
        ],
    ))

    segments.append(SegmentDefinition(
        name="Lambda排序",
        parameters=[make_param("列表", "列表[数]")],
        return_type="列表[数]",
        body=[
            make_var("排序后", make_call("排序", make_identifier("列表"))),
            make_return(make_identifier("排序后")),
        ],
    ))

    # 条件表达式（三元）
    segments.append(SegmentDefinition(
        name="三元测试",
        parameters=[make_param("条件", "布尔"), make_param("甲", "数"), make_param("乙", "数")],
        return_type="数",
        body=[
            make_return(ConditionalExpression(
                condition=make_identifier("条件"),
                then_expr=make_identifier("甲"),
                else_expr=make_identifier("乙"),
            )),
        ],
    ))

    # 复杂嵌套函数调用
    segments.append(SegmentDefinition(
        name="复合计算",
        parameters=[make_param("a", "数"), make_param("b", "数"), make_param("c", "数")],
        return_type="数",
        body=[
            make_var("结果1", make_call("加法", make_identifier("a"), make_identifier("b"))),
            make_var("结果2", make_call("乘法", make_identifier("结果1"), make_identifier("c"))),
            make_var("结果3", make_call("减法", make_identifier("结果2"), make_identifier("a"))),
            make_return(make_call("绝对值", make_identifier("结果3"))),
        ],
    ))

    segments.append(SegmentDefinition(
        name="链式调用",
        parameters=[make_param("x", "数")],
        return_type="数",
        body=[
            make_return(make_call("加法",
                make_call("乘法", make_identifier("x"), make_number(2)),
                make_call("绝对值", make_identifier("x")),
            )),
        ],
    ))

    segments.append(SegmentDefinition(
        name="多层嵌套条件",
        parameters=[make_param("分数", "数")],
        return_type="串",
        body=[
            make_var("等级", make_string("")),
            IfStatement(
                condition=make_binary(make_identifier("分数"), ">=", make_number(90)),
                then_body=[Assignment(target=make_identifier("等级"), value=make_string("甲"))],
                else_body=[
                    IfStatement(
                        condition=make_binary(make_identifier("分数"), ">=", make_number(80)),
                        then_body=[Assignment(target=make_identifier("等级"), value=make_string("乙"))],
                        else_body=[
                            IfStatement(
                                condition=make_binary(make_identifier("分数"), ">=", make_number(70)),
                                then_body=[Assignment(target=make_identifier("等级"), value=make_string("丙"))],
                                else_body=[
                                    IfStatement(
                                        condition=make_binary(make_identifier("分数"), ">=", make_number(60)),
                                        then_body=[Assignment(target=make_identifier("等级"), value=make_string("丁"))],
                                        else_body=[Assignment(target=make_identifier("等级"), value=make_string("戊"))],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            make_return(make_identifier("等级")),
        ],
    ))

    # 更多带有类型标注的段
    segments.append(SegmentDefinition(
        name="计算面积",
        parameters=[make_param("宽", "数"), make_param("高", "数")],
        return_type="数",
        body=[make_return(make_binary(make_identifier("宽"), "*", make_identifier("高")))],
    ))

    segments.append(SegmentDefinition(
        name="计算周长",
        parameters=[make_param("宽", "数"), make_param("高", "数")],
        return_type="数",
        body=[
            make_return(make_binary(
                make_binary(make_identifier("宽"), "+", make_identifier("高")),
                "*",
                make_number(2),
            )),
        ],
    ))

    segments.append(SegmentDefinition(
        name="阶乘",
        parameters=[make_param("n", "数")],
        return_type="数",
        body=[
            IfStatement(
                condition=make_binary(make_identifier("n"), "<=", make_number(1)),
                then_body=[make_return(make_number(1))],
                else_body=[
                    make_return(make_binary(
                        make_identifier("n"),
                        "*",
                        make_call("阶乘", make_binary(make_identifier("n"), "-", make_number(1))),
                    )),
                ],
            ),
        ],
    ))

    # 无类型标注的段（用于推断测试）
    segments.append(SegmentDefinition(
        name="推断加法",
        parameters=[make_param("甲"), make_param("乙")],
        body=[
            make_return(make_binary(make_identifier("甲"), "+", make_identifier("乙"))),
        ],
    ))

    segments.append(SegmentDefinition(
        name="推断拼接",
        parameters=[make_param("甲"), make_param("乙")],
        body=[
            make_return(make_binary(make_identifier("甲"), "+", make_identifier("乙"))),
        ],
    ))

    segments.append(SegmentDefinition(
        name="推断比较",
        parameters=[make_param("甲"), make_param("乙")],
        body=[
            make_var("结果", make_binary(make_identifier("甲"), ">", make_identifier("乙"))),
            make_return(make_identifier("结果")),
        ],
    ))

    segments.append(SegmentDefinition(
        name="推断返回",
        parameters=[make_param("值")],
        body=[make_return(make_identifier("值"))],
    ))

    # 属性访问
    segments.append(SegmentDefinition(
        name="属性访问测试",
        parameters=[make_param("对象", "点")],
        return_type="数",
        body=[
            make_return(PropertyAccess(obj=make_identifier("对象"), property_name="x")),
        ],
    ))

    # 一元运算
    segments.append(SegmentDefinition(
        name="取反",
        parameters=[make_param("值", "布尔")],
        return_type="布尔",
        body=[make_return(UnaryOp(operator="非", operand=make_identifier("值")))],
    ))

    segments.append(SegmentDefinition(
        name="负数",
        parameters=[make_param("值", "数")],
        return_type="数",
        body=[make_return(UnaryOp(operator="-", operand=make_identifier("值")))],
    ))

    # 打印语句
    segments.append(SegmentDefinition(
        name="打印测试",
        parameters=[make_param("消息", "串")],
        body=[
            PrintStatement(value=make_identifier("消息")),
            make_return(make_identifier("消息")),
        ],
    ))

    # 更多实用函数
    for i in range(1, 11):
        segments.append(SegmentDefinition(
            name=f"计算{i}",
            parameters=[make_param("x", "数")],
            return_type="数",
            body=[
                make_var("结果", make_binary(
                    make_binary(make_identifier("x"), "*", make_number(i)),
                    "+",
                    make_number(i * 10),
                )),
                make_return(make_identifier("结果")),
            ],
        ))

    # ---- 顶层语句 ----
    statements.append(make_var("全局常量", make_number(100), type_annotation="数"))
    statements.append(make_var("全局名称", make_string("光明"), type_annotation="串"))
    statements.append(make_var("全局标志", make_bool(True), type_annotation="布尔"))
    statements.append(PrintStatement(value=make_identifier("全局名称")))
    statements.append(ExpressionStatement(make_call("计算1", make_number(5))))

    # ---- 组装模块 ----
    module = Module(
        name="性能测试模块",
        segments=segments,
        classes=classes,
        enums=enums,
        trait_defs=trait_defs,
        trait_impls=trait_impls,
        statements=statements,
    )

    return module


# ============================================================
# 4. 执行 cProfile 分析
# ============================================================

def main():
    print("=" * 70)
    print("  光明 (Light) 类型推断器 cProfile 性能分析")
    print("=" * 70)

    # 构建测试模块
    print("\n[1] 构建测试模块...")
    test_module = create_realistic_module()
    seg_count = len(test_module.segments)
    stmt_count = len(test_module.statements)
    # 统计总语句数
    total_stmts = len(test_module.statements)
    for seg in test_module.segments:
        total_stmts += len(seg.body)
    for cls in test_module.classes:
        for m in cls.methods:
            total_stmts += len(m.body)
        if cls.constructor:
            total_stmts += len(cls.constructor.body)
    print(f"     段(函数)数量: {seg_count}")
    print(f"     类定义数量:   {len(test_module.classes)}")
    print(f"     枚举数量:     {len(test_module.enums)}")
    print(f"     Trait数量:    {len(test_module.trait_defs)}")
    print(f"     顶层语句:     {len(test_module.statements)}")
    print(f"     总语句数:     ~{total_stmts}")

    # 运行 cProfile
    print("\n[2] 运行 cProfile 分析...")
    profiler = cProfile.Profile()
    profiler.enable()

    inferencer = TypeInferencer()
    type_cache = inferencer.infer(test_module)

    profiler.disable()

    print(f"     推断完成: 共推断 {len(type_cache)} 个节点类型")
    print(f"     类型错误: {len(inferencer.errors)} 个")

    # 输出统计数据
    print("\n[3] 按累积时间排序 (Top 20):")
    print("-" * 70)
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
    print(stream.getvalue())

    # 按调用次数排序
    print("\n[4] 按调用次数排序 (Top 20):")
    print("-" * 70)
    stream2 = io.StringIO()
    stats2 = pstats.Stats(profiler, stream=stream2)
    stats2.sort_stats('calls')
    stats2.print_stats(20)
    print(stream2.getvalue())

    # 保存到文件
    print("\n[5] 保存完整分析结果到 profile_type_infer.out...")
    stats.dump_stats("profile_type_infer.out")
    print("     已保存到 profile_type_infer.out")

    print("\n" + "=" * 70)
    print("  分析完成！")
    print("=" * 70)


if __name__ == '__main__':
    main()