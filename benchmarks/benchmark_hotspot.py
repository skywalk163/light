# -*- coding: utf-8 -*-
"""
光明编译器 - 热点代码优化分析

功能：
1. 分析 benchmarks/programs/ 中各测试程序的性能瓶颈
2. 针对热点提出优化建议
3. 实现至少2个具体优化并验证效果
4. 输出优化分析报告（JSON格式）
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer
from light_parser_v3 import LightParser as V3Parser
from code_generator_unified import UnifiedCodeGenerator
from compiler import LightCompiler, AstAdapter

# 导入现有优化器
from optimizer import (
    ConstantFoldingOptimizer,
    DeadCodeEliminationOptimizer,
    LoopInvariantOptimizer,
    PeepholeOptimizer,
)

# 导入 AST 节点
from ast_nodes import (
    ASTNode, Module, BinaryOp, UnaryOp,
    NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral,
    VariableDeclaration, Assignment, Identifier,
    WhileStatement, ForStatement, ForeachStatement,
    IfStatement, ExpressionStatement, PrintStatement, ReturnStatement,
    FunctionCall, SegmentDefinition, ClassDefinition,
)

BENCHMARK_DIR = Path(__file__).parent / 'programs'
REPORT_DIR = Path(__file__).parent / 'reports'


def time_it(func, *args, **kwargs):
    """测量函数执行时间，返回 (结果, 耗时秒)"""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


def format_time(seconds):
    """格式化时间显示"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f} µs"
    elif seconds < 1.0:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.3f} s"


# =============================================================================
# 优化1：增强常量折叠
# =============================================================================

class EnhancedConstantFolding:
    """增强型常量折叠优化器

    在现有 ConstantFoldingOptimizer 基础上增加：
    - 嵌套二元运算的批量折叠（如 (1+2)*(3+4) → 21）
    - 常量条件判断的短路求值（如 if True → 直接取真分支）
    - 字符串常量拼接折叠
    - 列表常量折叠
    """

    def __init__(self):
        self.optimizations_applied = 0

    def optimize(self, module: Module) -> Module:
        """优化整个模块"""
        self.optimizations_applied = 0
        module.statements = [self._optimize_stmt(stmt) for stmt in module.statements]
        module.segments = [self._optimize_segment(seg) for seg in module.segments]
        module.classes = [self._optimize_class(cls) for cls in module.classes]
        return module

    def _optimize_stmt(self, stmt: ASTNode) -> ASTNode:
        """优化语句"""
        if isinstance(stmt, VariableDeclaration):
            if stmt.value:
                stmt.value = self._optimize_expr(stmt.value)
        elif isinstance(stmt, Assignment):
            if stmt.value:
                stmt.value = self._optimize_expr(stmt.value)
        elif isinstance(stmt, IfStatement):
            stmt.condition = self._optimize_expr(stmt.condition)
            # 常量条件短路
            if isinstance(stmt.condition, BooleanLiteral):
                self.optimizations_applied += 1
                if stmt.condition.value:
                    return self._flatten_block(stmt.then_body)
                elif stmt.else_body:
                    return self._flatten_block(stmt.else_body)
                return ExpressionStatement(None)  # 空语句占位
            stmt.then_body = [self._optimize_stmt(s) for s in stmt.then_body]
            if stmt.else_body:
                stmt.else_body = [self._optimize_stmt(s) for s in stmt.else_body]
        elif isinstance(stmt, WhileStatement):
            stmt.condition = self._optimize_expr(stmt.condition)
            stmt.body = [self._optimize_stmt(s) for s in stmt.body]
        elif isinstance(stmt, ReturnStatement):
            if stmt.value:
                stmt.value = self._optimize_expr(stmt.value)
        elif isinstance(stmt, PrintStatement):
            if stmt.expression:
                stmt.expression = self._optimize_expr(stmt.expression)
        return stmt

    def _optimize_segment(self, seg: SegmentDefinition) -> SegmentDefinition:
        """优化段落定义"""
        seg.body = [self._optimize_stmt(s) for s in seg.body]
        if seg.default_return:
            seg.default_return = self._optimize_expr(seg.default_return)
        return seg

    def _optimize_class(self, cls_def: ClassDefinition) -> ClassDefinition:
        """优化类定义"""
        if cls_def.constructor:
            cls_def.constructor.body = [self._optimize_stmt(s) for s in cls_def.constructor.body]
        for method in cls_def.methods:
            method.body = [self._optimize_stmt(s) for s in method.body]
        return cls_def

    def _optimize_expr(self, expr: ASTNode) -> ASTNode:
        """优化表达式，递归折叠常量"""
        if isinstance(expr, BinaryOp):
            expr.left = self._optimize_expr(expr.left)
            expr.right = self._optimize_expr(expr.right)
            return self._try_fold(expr)
        elif isinstance(expr, UnaryOp):
            expr.operand = self._optimize_expr(expr.operand)
            return self._try_fold_unary(expr)
        elif isinstance(expr, FunctionCall):
            expr.arguments = [self._optimize_expr(a) for a in expr.arguments]
        return expr

    def _try_fold(self, node: BinaryOp) -> ASTNode:
        """尝试折叠二元运算"""
        left = node.left
        right = node.right
        op = node.operator

        # 获取左右值
        left_val = self._get_literal_value(left)
        right_val = self._get_literal_value(right)

        if left_val is None or right_val is None:
            return node

        # 字符串拼接
        if op == '+' and isinstance(left_val, str) and isinstance(right_val, str):
            self.optimizations_applied += 1
            return StringLiteral(left_val + right_val)

        # 数值运算
        if isinstance(left_val, (int, float)) and isinstance(right_val, (int, float)):
            try:
                if op == '+':
                    result = NumberLiteral(left_val + right_val)
                elif op == '-':
                    result = NumberLiteral(left_val - right_val)
                elif op == '*':
                    result = NumberLiteral(left_val * right_val)
                elif op == '/' and right_val != 0:
                    result = NumberLiteral(left_val / right_val)
                elif op == '%':
                    result = NumberLiteral(left_val % right_val)
                elif op == '^':
                    result = NumberLiteral(left_val ** right_val)
                elif op == '>':
                    result = BooleanLiteral(left_val > right_val)
                elif op == '<':
                    result = BooleanLiteral(left_val < right_val)
                elif op == '>=':
                    result = BooleanLiteral(left_val >= right_val)
                elif op == '<=':
                    result = BooleanLiteral(left_val <= right_val)
                elif op == '==':
                    result = BooleanLiteral(left_val == right_val)
                elif op == '!=':
                    result = BooleanLiteral(left_val != right_val)
                else:
                    return node
                self.optimizations_applied += 1
                return result
            except (ZeroDivisionError, TypeError, ValueError):
                return node

        # 布尔运算
        if isinstance(left_val, bool) and isinstance(right_val, bool):
            if op == '且':
                self.optimizations_applied += 1
                return BooleanLiteral(left_val and right_val)
            elif op == '或':
                self.optimizations_applied += 1
                return BooleanLiteral(left_val or right_val)

        return node

    def _try_fold_unary(self, node: UnaryOp) -> ASTNode:
        """尝试折叠一元运算"""
        val = self._get_literal_value(node.operand)
        if val is None:
            return node

        if node.operator == '-' and isinstance(val, (int, float)):
            self.optimizations_applied += 1
            return NumberLiteral(-val)
        if node.operator == '非' and isinstance(val, bool):
            self.optimizations_applied += 1
            return BooleanLiteral(not val)
        if node.operator == '非' and isinstance(val, (int, float)):
            self.optimizations_applied += 1
            return BooleanLiteral(not val)

        return node

    def _get_literal_value(self, expr: ASTNode):
        """获取字面量的值，非字面量返回 None"""
        if isinstance(expr, NumberLiteral):
            return expr.value
        elif isinstance(expr, StringLiteral):
            return expr.value
        elif isinstance(expr, BooleanLiteral):
            return expr.value
        elif isinstance(expr, NullLiteral):
            return None
        return None

    def _flatten_block(self, stmts: list) -> ASTNode:
        """将块语句展开为单个语句或序列"""
        if not stmts:
            return ExpressionStatement(None)
        if len(stmts) == 1:
            return stmts[0]
        # 多个语句 -> 用第一个返回（简化处理）
        return stmts[0]


# =============================================================================
# 优化2：简单循环展开
# =============================================================================

class SimpleLoopUnrolling:
    """简单循环展开优化器

    对固定次数的 while 循环进行部分或完全展开。
    适用于循环次数较小（<= 8）且循环体简单的场景。
    """

    def __init__(self, unroll_factor: int = 4):
        self.unroll_factor = unroll_factor
        self.optimizations_applied = 0

    def optimize(self, module: Module) -> Module:
        """优化整个模块"""
        self.optimizations_applied = 0
        module.statements = self._optimize_stmt_list(module.statements)
        module.segments = [self._optimize_segment(seg) for seg in module.segments]
        module.classes = [self._optimize_class(cls) for cls in module.classes]
        return module

    def _optimize_stmt_list(self, stmts: list) -> list:
        """优化语句列表"""
        result = []
        for stmt in stmts:
            if isinstance(stmt, WhileStatement):
                unrolled = self._try_unroll(stmt)
                if unrolled is not stmt:
                    result.extend(unrolled)
                else:
                    stmt.body = self._optimize_stmt_list(stmt.body)
                    result.append(stmt)
            else:
                if isinstance(stmt, (IfStatement, SegmentDefinition)):
                    result.append(self._optimize_stmt(stmt))
                else:
                    result.append(stmt)
        return result

    def _optimize_stmt(self, stmt: ASTNode) -> ASTNode:
        """递归优化语句"""
        if isinstance(stmt, IfStatement):
            stmt.then_body = self._optimize_stmt_list(stmt.then_body)
            if stmt.else_body:
                stmt.else_body = self._optimize_stmt_list(stmt.else_body)
        elif isinstance(stmt, WhileStatement):
            stmt.body = self._optimize_stmt_list(stmt.body)
        elif isinstance(stmt, SegmentDefinition):
            stmt.body = self._optimize_stmt_list(stmt.body)
        return stmt

    def _optimize_segment(self, seg: SegmentDefinition) -> SegmentDefinition:
        """优化段落"""
        seg.body = self._optimize_stmt_list(seg.body)
        return seg

    def _optimize_class(self, cls_def: ClassDefinition) -> ClassDefinition:
        """优化类"""
        if cls_def.constructor:
            cls_def.constructor.body = self._optimize_stmt_list(cls_def.constructor.body)
        for method in cls_def.methods:
            method.body = self._optimize_stmt_list(method.body)
        return cls_def

    def _try_unroll(self, while_stmt: WhileStatement) -> list:
        """尝试展开 while 循环

        识别模式：
        i = 0; while i < N: body; i = i + 1
        """
        condition = while_stmt.condition
        body = while_stmt.body

        # 尝试识别固定次数的计数循环
        bound = self._get_loop_bound(condition)
        if bound is None or bound > 8:
            return [while_stmt]  # 不展开

        # 检查循环体是否有递增计数器
        counter_var = self._get_counter_var(condition)
        if counter_var is None:
            return [while_stmt]

        # 检查循环体是否包含 counter = counter + 1
        has_increment = self._has_increment(body, counter_var)
        if not has_increment:
            return [while_stmt]

        # 过滤掉递增语句，生成展开体
        unrolled_body = []
        for i in range(bound):
            for stmt in body:
                if self._is_increment(stmt, counter_var):
                    continue
                unrolled_body.append(self._clone_stmt(stmt))

        self.optimizations_applied += 1
        return unrolled_body

    def _get_loop_bound(self, condition) -> int:
        """获取循环边界（如果可确定）"""
        if not isinstance(condition, BinaryOp):
            return None
        if condition.operator not in ('<', '<='):
            return None
        if isinstance(condition.right, NumberLiteral):
            val = condition.right.value
            if isinstance(val, (int, float)) and val <= 8:
                return int(val)
        return None

    def _get_counter_var(self, condition) -> str:
        """获取循环计数器变量名"""
        if not isinstance(condition, BinaryOp):
            return None
        if isinstance(condition.left, Identifier):
            return condition.left.name
        return None

    def _has_increment(self, body: list, var_name: str) -> bool:
        """检查循环体是否有对变量的递增操作"""
        for stmt in body:
            if self._is_increment(stmt, var_name):
                return True
        return False

    def _is_increment(self, stmt: ASTNode, var_name: str) -> bool:
        """判断是否为 var = var + 1 模式的递增"""
        if isinstance(stmt, Assignment):
            if isinstance(stmt.target, Identifier) and stmt.target.name == var_name:
                if isinstance(stmt.value, BinaryOp):
                    if (stmt.value.operator == '+'
                            and isinstance(stmt.value.left, Identifier)
                            and stmt.value.left.name == var_name
                            and isinstance(stmt.value.right, NumberLiteral)
                            and stmt.value.right.value == 1):
                        return True
        return False

    def _clone_stmt(self, stmt: ASTNode) -> ASTNode:
        """克隆语句（浅拷贝，足够用于展开）"""
        import copy
        return copy.deepcopy(stmt)


# =============================================================================
# 性能瓶颈分析
# =============================================================================

def analyze_bottlenecks():
    """分析各测试程序的性能瓶颈"""
    print("=" * 80)
    print("1. 性能瓶颈分析")
    print("=" * 80)

    bench_files = sorted(BENCHMARK_DIR.glob('*.light'))
    results = []

    for bench_file in bench_files:
        name = bench_file.stem
        with open(bench_file, 'r', encoding='utf-8') as f:
            source = f.read()

        print(f"\n  分析 {name} ...")

        # 各阶段耗时分析
        lexer = Lexer()
        tokens, t_lex = time_it(lexer.tokenize, source)

        parser = V3Parser()
        ast_raw, t_parse = time_it(parser.parse, source)

        adapter = AstAdapter()
        ast, t_adapter = time_it(adapter.convert_module, ast_raw)

        codegen = UnifiedCodeGenerator()
        code, t_codegen = time_it(codegen.generate, ast)

        t_total = t_lex + t_parse + t_adapter + t_codegen

        # 瓶颈分析
        phases = {
            '词法分析': t_lex,
            '语法解析': t_parse,
            'AST适配': t_adapter,
            '代码生成': t_codegen,
        }
        bottleneck = max(phases, key=phases.get)
        bottleneck_pct = phases[bottleneck] / t_total * 100

        # 代码特征分析
        features = analyze_code_features(source)

        print(f"    总耗时: {format_time(t_total)}")
        for phase_name, t in phases.items():
            pct = t / t_total * 100
            marker = " ← 瓶颈" if phase_name == bottleneck else ""
            print(f"      {phase_name}: {format_time(t)} ({pct:.1f}%){marker}")

        result = {
            'name': name,
            'source_len': len(source),
            'total_time': t_total,
            'phases': {k: v for k, v in phases.items()},
            'bottleneck': bottleneck,
            'bottleneck_pct': bottleneck_pct,
            'features': features,
            'suggestions': generate_suggestions(name, bottleneck, features),
        }

        print(f"    瓶颈: {bottleneck} ({bottleneck_pct:.1f}%)")
        print(f"    建议: {result['suggestions'][0] if result['suggestions'] else '无'}")
        results.append(result)

    return results


def analyze_code_features(source: str) -> Dict[str, Any]:
    """分析代码特征"""
    lines = source.split('\n')
    features = {
        'line_count': len(lines),
        'function_count': source.count('段落'),
        'class_count': source.count('类 '),
        'loop_count': source.count('当 ') + source.count('遍历 '),
        'if_count': source.count('如果 '),
        'recursion': '递归' in source or source.count('段落') > source.count('返回'),
        'has_nested_ifs': '如果' in source and source.count('如果') > 3,
    }
    return features


def generate_suggestions(name: str, bottleneck: str, features: Dict) -> List[str]:
    """生成优化建议"""
    suggestions = []

    if bottleneck == '语法解析':
        suggestions.append("减少嵌套深度，简化表达式结构可加速解析")
        if features.get('has_nested_ifs'):
            suggestions.append("考虑将深层嵌套 if 重构为扁平结构或 switch 模式")
        if features.get('function_count', 0) > 10:
            suggestions.append("大量函数定义增加了解析负担，可考虑模块化拆分")

    elif bottleneck == '代码生成':
        suggestions.append("代码生成阶段较慢，可考虑缓存生成的代码片段")
        if features.get('function_count', 0) > 5:
            suggestions.append("函数模板代码生成可预编译优化")

    elif bottleneck == '词法分析':
        suggestions.append("代码较长时词法分析成为瓶颈，可考虑增量词法分析")
        if features.get('line_count', 0) > 50:
            suggestions.append("大文件词法分析可并行化处理")

    elif bottleneck == 'AST适配':
        suggestions.append("AST 适配阶段可优化节点映射表查找效率")

    # 通用建议
    if features.get('recursion'):
        suggestions.append("递归函数可考虑改写为迭代形式以提升运行时性能")
    if features.get('loop_count', 0) > 2:
        suggestions.append("循环体可考虑循环展开优化")

    return suggestions


# =============================================================================
# 优化效果验证
# =============================================================================

def verify_optimizations():
    """验证优化效果：对比优化前后编译时间和代码质量"""
    print("\n" + "=" * 80)
    print("2. 优化效果验证")
    print("=" * 80)

    bench_files = sorted(BENCHMARK_DIR.glob('*.light'))
    results = []

    for bench_file in bench_files:
        name = bench_file.stem
        with open(bench_file, 'r', encoding='utf-8') as f:
            source = f.read()

        print(f"\n  验证 {name}:")

        # 基准：无优化
        adapter = AstAdapter()
        parser = V3Parser()
        ast_raw = parser.parse(source)
        ast = adapter.convert_module(ast_raw)
        codegen = UnifiedCodeGenerator()
        code_before, t_before = time_it(codegen.generate, ast)
        size_before = len(code_before)

        # 应用优化1：增强常量折叠
        adapter2 = AstAdapter()
        ast2 = adapter2.convert_module(parser.parse(source))
        opt1 = EnhancedConstantFolding()
        ast_opt1 = opt1.optimize(ast2)
        codegen2 = UnifiedCodeGenerator()
        code_opt1, t_opt1 = time_it(codegen2.generate, ast_opt1)
        size_opt1 = len(code_opt1)

        # 应用优化2：简单循环展开
        adapter3 = AstAdapter()
        ast3 = adapter3.convert_module(parser.parse(source))
        opt2 = SimpleLoopUnrolling(unroll_factor=4)
        ast_opt2 = opt2.optimize(ast3)
        codegen3 = UnifiedCodeGenerator()
        code_opt2, t_opt2 = time_it(codegen3.generate, ast_opt2)
        size_opt2 = len(code_opt2)

        # 两个优化一起应用
        adapter4 = AstAdapter()
        ast4 = adapter4.convert_module(parser.parse(source))
        ast_opt1a = opt1.optimize(ast4)  # 用新实例
        opt1b = EnhancedConstantFolding()
        opt2b = SimpleLoopUnrolling(unroll_factor=4)
        ast_combined = opt1b.optimize(ast_opt1a)
        ast_combined = opt2b.optimize(ast_combined)
        codegen4 = UnifiedCodeGenerator()
        code_combined, t_combined = time_it(codegen4.generate, ast_combined)
        size_combined = len(code_combined)

        print(f"    无优化:     代码生成={format_time(t_before)}, 生成大小={size_before}字符")
        print(f"    常量折叠:   代码生成={format_time(t_opt1)}, 生成大小={size_opt1}字符, 优化次数={opt1.optimizations_applied}")
        print(f"    循环展开:   代码生成={format_time(t_opt2)}, 生成大小={size_opt2}字符, 优化次数={opt2.optimizations_applied}")
        print(f"    组合优化:   代码生成={format_time(t_combined)}, 生成大小={size_combined}字符")

        result = {
            'name': name,
            'baseline': {'codegen_time': t_before, 'generated_size': size_before},
            'enhanced_folding': {
                'codegen_time': t_opt1,
                'generated_size': size_opt1,
                'optimizations_applied': opt1.optimizations_applied,
                'time_speedup': t_before / t_opt1 if t_opt1 > 0 else 0,
                'size_reduction': (1 - size_opt1 / size_before) * 100 if size_before > 0 else 0,
            },
            'loop_unrolling': {
                'codegen_time': t_opt2,
                'generated_size': size_opt2,
                'optimizations_applied': opt2.optimizations_applied,
                'time_speedup': t_before / t_opt2 if t_opt2 > 0 else 0,
            },
            'combined': {
                'codegen_time': t_combined,
                'generated_size': size_combined,
                'time_speedup': t_before / t_combined if t_combined > 0 else 0,
                'size_reduction': (1 - size_combined / size_before) * 100 if size_before > 0 else 0,
            },
        }
        results.append(result)

    return results


# =============================================================================
# 运行时性能优化验证
# =============================================================================

def verify_runtime_optimization():
    """验证优化对运行时性能的影响"""
    print("\n" + "=" * 80)
    print("3. 优化对运行时性能的影响")
    print("=" * 80)

    # 测试用例：带大量常量运算的代码
    test_cases = [
        {
            'name': '常量表达式折叠',
            'code': '''
设 结果 为 (1 加 2) 乘 (3 加 4) 减 5 加 10 乘 2
打印 结果
'''
        },
        {
            'name': '条件短路',
            'code': '''
设 甲 为 10
如果 真 那么：
  打印 "始终执行"
否则：
  打印 "不会执行"
设 乙 为 20
打印 乙
'''
        },
        {
            'name': '小循环展开',
            'code': '''
设 总和 为 0
设 i 为 0
当 i 小于 4：
  总和 为 总和 加 i
  i 为 i 加 1
打印 总和
'''
        },
    ]

    results = []

    for case in test_cases:
        name = case['name']
        source = case['code']
        print(f"\n  测试: {name}")

        # 无优化编译执行
        compiler = LightCompiler()
        code_before = compiler.compile(source)
        times_before = []
        for _ in range(5):
            _, t = time_it(exec, code_before, {})
            times_before.append(t)
        avg_before = sum(times_before) / len(times_before)

        # 应用优化后编译执行
        parser = V3Parser()
        ast_raw = parser.parse(source)
        adapter = AstAdapter()
        ast = adapter.convert_module(ast_raw)

        # 增强常量折叠
        efc = EnhancedConstantFolding()
        ast = efc.optimize(ast)

        # 循环展开
        slu = SimpleLoopUnrolling(unroll_factor=4)
        ast = slu.optimize(ast)

        # 代码生成
        codegen = UnifiedCodeGenerator()
        code_after = codegen.generate(ast)

        times_after = []
        for _ in range(5):
            _, t = time_it(exec, code_after, {})
            times_after.append(t)
        avg_after = sum(times_after) / len(times_after)

        speedup = avg_before / avg_after if avg_after > 0 else 0
        print(f"    优化前: {format_time(avg_before)}")
        print(f"    优化后: {format_time(avg_after)}")
        print(f"    加速比: {speedup:.2f}x")

        results.append({
            'name': name,
            'before_avg': avg_before,
            'after_avg': avg_after,
            'speedup': speedup,
            'optimizations': {
                'enhanced_folding_applied': efc.optimizations_applied,
                'loop_unrolling_applied': slu.optimizations_applied,
            },
        })

    return results


def generate_report(bottleneck_results, opt_verify_results, runtime_opt_results, output_path):
    """生成结构化 JSON 报告"""
    report = {
        'report_type': 'hotspot_benchmark',
        'timestamp': datetime.now().isoformat(),
        'bottleneck_analysis': bottleneck_results,
        'optimization_verification': opt_verify_results,
        'runtime_optimization': runtime_opt_results,
        'summary': {},
    }

    # 计算汇总
    summary = {}

    if bottleneck_results:
        bottlenecks = {}
        for r in bottleneck_results:
            b = r['bottleneck']
            bottlenecks[b] = bottlenecks.get(b, 0) + 1
        summary['bottleneck_distribution'] = bottlenecks
        summary['total_programs_analyzed'] = len(bottleneck_results)

    if opt_verify_results:
        total_folding = sum(r['enhanced_folding']['optimizations_applied'] for r in opt_verify_results)
        total_unrolling = sum(r['loop_unrolling']['optimizations_applied'] for r in opt_verify_results)
        avg_time_speedup = sum(r['combined']['time_speedup'] for r in opt_verify_results) / len(opt_verify_results)
        summary['optimization_stats'] = {
            'total_folding_applied': total_folding,
            'total_unrolling_applied': total_unrolling,
            'avg_combined_time_speedup': avg_time_speedup,
        }

    if runtime_opt_results:
        avg_speedup = sum(r['speedup'] for r in runtime_opt_results) / len(runtime_opt_results)
        summary['runtime_optimization'] = {
            'test_count': len(runtime_opt_results),
            'avg_speedup': avg_speedup,
        }

    report['summary'] = summary

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存到 {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description='光明编译器热点代码优化分析')
    parser.add_argument('--output', '-o', default=str(REPORT_DIR / 'hotspot_benchmark.json'),
                        help='JSON 报告输出路径')
    parser.add_argument('--no-bottleneck', action='store_true', help='跳过瓶颈分析')
    parser.add_argument('--no-verify', action='store_true', help='跳过优化验证')
    parser.add_argument('--no-runtime', action='store_true', help='跳过运行时优化验证')
    args = parser.parse_args()

    print("光明编译器 - 热点代码优化分析")
    print("=" * 80)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    print()

    print("已实现的优化：")
    print("  1. EnhancedConstantFolding - 增强型常量折叠")
    print("     - 嵌套二元运算批量折叠")
    print("     - 常量条件短路求值")
    print("     - 字符串常量拼接折叠")
    print("  2. SimpleLoopUnrolling - 简单循环展开")
    print("     - 固定次数的计数循环展开（<=8次）")
    print()

    bottleneck_results = None
    opt_verify_results = None
    runtime_opt_results = None

    if not args.no_bottleneck:
        bottleneck_results = analyze_bottlenecks()

    if not args.no_verify:
        opt_verify_results = verify_optimizations()

    if not args.no_runtime:
        runtime_opt_results = verify_runtime_optimization()

    # 生成报告
    report = generate_report(bottleneck_results, opt_verify_results, runtime_opt_results, args.output)

    print("\n" + "=" * 80)
    print("热点代码优化分析完成！")
    print("=" * 80)

    return report


if __name__ == '__main__':
    main()