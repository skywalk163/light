# -*- coding: utf-8 -*-
"""
Light 语言类型推断器基准测试

测量：
1. 不同规模模块（小/中/大）的推断时间
2. 不同数量类型变量的推断时间
3. 内存使用估算
"""
import sys
import os
import time
import gc
import tracemalloc

# ============================================================
# 设置 sys.path
# ============================================================
_project_root = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)

from type_inferencer import TypeInferencer
from ast_nodes import (
    Module, SegmentDefinition, ClassDefinition, MethodDefinition,
    ConstructorDefinition, Parameter, VariableDeclaration, Assignment,
    IfStatement, WhileStatement, ForeachStatement, ReturnStatement,
    PrintStatement, ExpressionStatement, BinaryOp, UnaryOp,
    FunctionCall, Identifier, NumberLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, ListLiteral, DictLiteral, DictEntry,
    NewExpression, PropertyAccess, IndexAccess, LambdaExpression,
    ConditionalExpression, ListComprehension,
    EnumDefinition, EnumVariant, DataTypeField,
    TraitDefinition, TraitMethodSignature, TraitImplementation,
)


# ============================================================
# 辅助函数
# ============================================================
def idn(name):
    return Identifier(name=name)


def num(val):
    return NumberLiteral(value=val)


def s(val):
    return StringLiteral(value=val)


def bo(val):
    return BooleanLiteral(value=val)


def call(name, *args):
    return FunctionCall(name=idn(name), arguments=list(args))


def binop(left, op, right):
    return BinaryOp(left=left, operator=op, right=right)


def ret(val=None):
    return ReturnStatement(value=val)


def var(name, val, ta=None):
    return VariableDeclaration(name=name, value=val, type_annotation=ta)


def param(name, ta=None):
    return Parameter(name=name, type_annotation=ta)


def seg(name, params, body, ret_type=None, generic_params=None):
    return SegmentDefinition(
        name=name, parameters=params, body=body,
        return_type=ret_type,
        generic_params=generic_params or [],
    )


def make_module(num_segments, complexity=1):
    """生成指定段数量和复杂度的测试模块"""
    segments = []

    for i in range(num_segments):
        # 根据复杂度决定函数体语句数
        n_stmts = max(1, complexity)
        body = []

        for j in range(n_stmts):
            body.append(var(f"v{i}_{j}", binop(num(i * 10 + j), "+", num(j * 5))))

        # 最后一条返回语句
        body.append(ret(idn(f"v{i}_{n_stmts - 1}")))

        segments.append(seg(
            f"函数{i}",
            [param(f"x{i}", "数"), param(f"y{i}", "数")],
            body,
            ret_type="数",
        ))

    return Module(name="基准测试", segments=segments)


def make_module_with_type_vars(num_type_vars):
    """生成包含指定数量类型变量的模块"""
    segments = []

    # 为每个类型变量创建泛型函数
    for i in range(num_type_vars):
        segments.append(seg(
            f"泛型函数{i}",
            [param("值", f"T{i}")],
            [ret(idn("值"))],
            ret_type=f"T{i}",
            generic_params=[f"T{i}"],
        ))

    # 创建使用这些泛型函数的普通函数
    segments.append(seg(
        "使用泛型",
        [param("x", "数"), param("y", "串")],
        [
            var("a", call("泛型函数0", idn("x"))),
            var("b", call("泛型函数1", idn("y"))),
            ret(idn("a")),
        ],
    ))

    return Module(name="类型变量测试", segments=segments)


def make_module_with_nested_calls(num_segments):
    """生成带有嵌套函数调用的模块"""
    segments = []

    # 基础函数
    segments.append(seg("基础", [param("a", "数"), param("b", "数")],
                        [ret(binop(idn("a"), "+", idn("b")))], ret_type="数"))

    # 嵌套调用链
    for i in range(num_segments - 1):
        body = [ret(call("基础",
                         call(f"嵌套{i}", idn("x"), idn("y")) if i > 0 else idn("x"),
                         idn("y")))]
        segments.append(seg(f"嵌套{i + 1}", [param("x", "数"), param("y", "数")],
                            body, ret_type="数"))

    return Module(name="嵌套调用测试", segments=segments)


def make_module_rich(features_count=10):
    """生成包含丰富特性的模块（类、泛型、枚举、trait等）"""
    segments = []
    classes = []
    enums = []
    trait_defs = []
    trait_impls = []

    # 枚举
    enums.append(EnumDefinition(
        name="选项",
        variants=[
            EnumVariant(name="A", fields=[]),
            EnumVariant(name="B", fields=[DataTypeField(name="val", type_annotation="数")]),
        ]
    ))

    # Trait
    trait_defs.append(TraitDefinition(
        name="可展示",
        methods=[TraitMethodSignature(name="展示", parameters=[], return_type="串")]
    ))

    # 类
    for i in range(min(features_count, 5)):
        c = ClassDefinition(
            name=f"类{i}",
            constructor=ConstructorDefinition(
                name="新建",
                parameters=[param("x", "数")],
                body=[Assignment(target=idn("x"), value=idn("x"))],
            ),
            methods=[
                MethodDefinition(
                    name="获取",
                    parameters=[],
                    return_type="数",
                    body=[ret(idn("x"))],
                ),
                MethodDefinition(
                    name="计算",
                    parameters=[param("y", "数")],
                    return_type="数",
                    body=[ret(binop(idn("x"), "+", idn("y")))],
                ),
            ]
        )
        classes.append(c)

    # 段
    for i in range(features_count):
        segments.append(seg(
            f"处理{i}",
            [param("data", "数")],
            [
                var("obj", NewExpression(class_name=f"类{i % min(features_count, 5)}",
                                         arguments=[idn("data")])),
                var("result", call("获取", idn("obj"))),
                ret(idn("result")),
            ],
            ret_type="数",
        ))

    return Module(
        name="丰富特性测试",
        segments=segments,
        classes=classes,
        enums=enums,
        trait_defs=trait_defs,
        trait_impls=trait_impls,
    )


def bench_infer(module, name, warmup=1, runs=5):
    """运行基准测试"""
    times = []

    # 预热
    for _ in range(warmup):
        inf = TypeInferencer()
        inf.infer(module)
        del inf

    gc.collect()

    for _ in range(runs):
        inf = TypeInferencer()
        t0 = time.perf_counter()
        inf.infer(module)
        t1 = time.perf_counter()
        times.append(t1 - t0)
        del inf

    avg = sum(times) / len(times)
    min_t = min(times)
    max_t = max(times)
    return avg, min_t, max_t, times


def format_time(seconds):
    """格式化时间"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    else:
        return f"{seconds:.3f} s"


def main():
    print("=" * 70)
    print("  光明 (Light) 类型推断器基准测试")
    print("=" * 70)

    # ================================================================
    # 1. 小/中/大规模模块推断时间
    # ================================================================
    print("\n" + "─" * 60)
    print("  1. 不同规模模块推断时间")
    print("─" * 60)

    sizes = [
        ("小 (10 segments)", 10, 1),
        ("中 (50 segments)", 50, 1),
        ("大 (100 segments)", 100, 1),
    ]

    results = []
    for label, n_segs, comp in sizes:
        print(f"\n  [{label}] 构建模块...")
        module = make_module(n_segs, comp)
        print(f"  运行基准测试 (预热1次 + 运行5次)...")
        avg, min_t, max_t, times = bench_infer(module, label)
        results.append((label, avg, min_t, max_t, n_segs))
        print(f"    平均: {format_time(avg)}  |  最小: {format_time(min_t)}  |  最大: {format_time(max_t)}")
        print(f"    每次用时: {[format_time(t) for t in times]}")

    # ================================================================
    # 2. 类型变量数量 vs 时间
    # ================================================================
    print("\n" + "─" * 60)
    print("  2. 类型变量数量 vs 推断时间")
    print("─" * 60)

    tv_counts = [0, 2, 5, 10, 20, 50]
    for n_tv in tv_counts:
        print(f"\n  [{n_tv} 个类型变量] ...")
        module = make_module_with_type_vars(n_tv)
        avg, min_t, max_t, _ = bench_infer(module, f"TypeVars={n_tv}", warmup=1, runs=3)
        print(f"    平均: {format_time(avg)}  |  最小: {format_time(min_t)}  |  最大: {format_time(max_t)}")

    # ================================================================
    # 3. 嵌套调用深度测试
    # ================================================================
    print("\n" + "─" * 60)
    print("  3. 嵌套调用深度 vs 推断时间")
    print("─" * 60)

    for depth in [5, 10, 20, 30]:
        print(f"\n  [深度 {depth}] ...")
        module = make_module_with_nested_calls(depth)
        avg, min_t, max_t, _ = bench_infer(module, f"Nested={depth}", warmup=1, runs=3)
        print(f"    平均: {format_time(avg)}  |  最小: {format_time(min_t)}  |  最大: {format_time(max_t)}")

    # ================================================================
    # 4. 复杂特性模块测试
    # ================================================================
    print("\n" + "─" * 60)
    print("  4. 复杂特性模块（类 + 泛型 + 枚举 + Trait）")
    print("─" * 60)

    for fc in [3, 5, 10]:
        print(f"\n  [特性数 {fc}] ...")
        module = make_module_rich(fc)
        avg, min_t, max_t, _ = bench_infer(module, f"Rich={fc}", warmup=1, runs=3)
        print(f"    平均: {format_time(avg)}  |  最小: {format_time(min_t)}  |  最大: {format_time(max_t)}")

    # ================================================================
    # 5. 内存使用估算
    # ================================================================
    print("\n" + "─" * 60)
    print("  5. 内存使用估算")
    print("─" * 60)

    # 使用 tracemalloc 跟踪内存
    tracemalloc.start()

    print("\n  [小模块 10 segments] ...")
    gc.collect()
    s1 = tracemalloc.take_snapshot()
    module_small = make_module(10, 1)
    inf_small = TypeInferencer()
    inf_small.infer(module_small)
    s2 = tracemalloc.take_snapshot()
    stats_small = s2.compare_to(s1, 'lineno')
    small_total = sum(stat.size_diff for stat in stats_small if stat.size_diff > 0)
    print(f"    推断期间内存增长: {small_total / 1024:.1f} KB")
    del inf_small, module_small

    print("\n  [中模块 50 segments] ...")
    gc.collect()
    s3 = tracemalloc.take_snapshot()
    module_med = make_module(50, 1)
    inf_med = TypeInferencer()
    inf_med.infer(module_med)
    s4 = tracemalloc.take_snapshot()
    stats_med = s4.compare_to(s3, 'lineno')
    med_total = sum(stat.size_diff for stat in stats_med if stat.size_diff > 0)
    print(f"    推断期间内存增长: {med_total / 1024:.1f} KB")
    del inf_med, module_med

    print("\n  [大模块 100 segments] ...")
    gc.collect()
    s5 = tracemalloc.take_snapshot()
    module_large = make_module(100, 1)
    inf_large = TypeInferencer()
    inf_large.infer(module_large)
    s6 = tracemalloc.take_snapshot()
    stats_large = s6.compare_to(s5, 'lineno')
    large_total = sum(stat.size_diff for stat in stats_large if stat.size_diff > 0)
    print(f"    推断期间内存增长: {large_total / 1024:.1f} KB")
    del inf_large, module_large

    tracemalloc.stop()

    # ================================================================
    # 6. 汇总
    # ================================================================
    print("\n" + "=" * 70)
    print("  基准测试汇总")
    print("=" * 70)

    print(f"\n  {'模块规模':<25} {'平均时间':>15} {'最小时间':>15} {'最大时间':>15}")
    print(f"  {'-'*25} {'-'*15} {'-'*15} {'-'*15}")
    for label, avg, min_t, max_t, _ in results:
        print(f"  {label:<25} {format_time(avg):>15} {format_time(min_t):>15} {format_time(max_t):>15}")

    print(f"\n  {'内存使用':<25} {'增长量':>15}")
    print(f"  {'-'*25} {'-'*15}")
    print(f"  {'小模块 (10 segments)':<25} {small_total / 1024:>14.1f} KB")
    print(f"  {'中模块 (50 segments)':<25} {med_total / 1024:>14.1f} KB")
    print(f"  {'大模块 (100 segments)':<25} {large_total / 1024:>14.1f} KB")

    print("\n  基准测试完成！")
    print("=" * 70)


if __name__ == '__main__':
    main()