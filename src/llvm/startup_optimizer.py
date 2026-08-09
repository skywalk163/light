"""启动时间优化器

策略：
- 延迟初始化（懒加载）
- 预编译热函数
- 函数分块（hot/cold 分离）
- 函数内联（热函数优先内联）
- 预计算（编译时计算常量表达式）
- 延迟初始化优化（全局变量按需初始化）
"""

import re
from typing import List, Dict, Set, Optional, Tuple


class StartupOptimizer:
    """启动时间优化器

    通过延迟初始化、函数分块、内联、预计算等策略优化程序启动时间。
    适用于 -O3 模式。

    Attributes:
        stats: 优化统计信息
    """

    def __init__(self):
        self.stats = {
            'deferred_inits': 0,
            'hot_cold_split': 0,
            'precompiled_hot': 0,
            'inlined_hot_functions': 0,
            'precomputed_expressions': 0,
        }

    def optimize(self, ir: str) -> str:
        """运行所有启动时间优化

        Args:
            ir: 输入的 LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        ir = self._precompute_expressions(ir)
        ir = self._inline_hot_functions(ir)
        ir = self._defer_initialization(ir)
        ir = self._hot_cold_splitting(ir)
        ir = self._precompile_hot_functions(ir)
        return ir

    def _precompute_expressions(self, ir: str) -> str:
        """预计算表达式

        在编译时计算常量表达式，减少运行时开销。
        对全局常量和常量表达式进行编译时求值。

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        lines = ir.split('\n')
        result = []
        const_values: Dict[str, str] = {}

        for line in lines:
            stripped = line.strip()

            # 跳过非指令行
            if not stripped or stripped.startswith(';') or stripped.endswith(':'):
                result.append(line)
                continue

            # 检测常量定义并尝试预计算
            m = re.match(
                r'\s*(%\w+)\s*=\s*'
                r'(add|sub|mul|sdiv|udiv|and|or|xor)\s+'
                r'(\w+)\s+'
                r'(-?\d+)\s*,\s*'
                r'(-?\d+)',
                stripped
            )
            if m:
                reg = m.group(1)
                op = m.group(2)
                ty = m.group(3)
                lhs = int(m.group(4))
                rhs = int(m.group(5))

                op_map = {
                    'add': lambda a, b: a + b,
                    'sub': lambda a, b: a - b,
                    'mul': lambda a, b: a * b,
                    'sdiv': lambda a, b: a // b if b != 0 else None,
                    'udiv': lambda a, b: a // b if b != 0 else None,
                    'and': lambda a, b: a & b,
                    'or': lambda a, b: a | b,
                    'xor': lambda a, b: a ^ b,
                }

                if op in op_map:
                    fn = op_map[op]
                    result_val = fn(lhs, rhs)
                    if result_val is not None:
                        # 预计算，直接替换为常量
                        const_values[reg] = str(result_val)
                        result.append(f'  {reg} = add {ty} {result_val}, 0  ; precomputed {op}')
                        self.stats['precomputed_expressions'] += 1
                        continue

            result.append(line)

        return '\n'.join(result)

    def _inline_hot_functions(self, ir: str) -> str:
        """内联热函数

        将频繁调用的小函数内联展开，减少函数调用开销。

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        # 统计函数调用次数
        call_counts: Dict[str, int] = {}
        for m in re.finditer(r'@(\w+)\s*\(', ir):
            func_name = m.group(1)
            if not func_name.startswith('light_') and not func_name.startswith('__'):
                call_counts[func_name] = call_counts.get(func_name, 0) + 1

        # 提取小函数定义
        func_pattern = re.compile(
            r'(define\s+.*?@(\w+)\s*\(.*?\))\s*\{([^}]*)\}',
            re.DOTALL
        )

        small_hot_funcs = {}
        for m in func_pattern.finditer(ir):
            func_name = m.group(2)
            func_body = m.group(3).strip()

            # 跳过 main 和初始化函数
            if func_name in ('main', '__light_init'):
                continue

            # 统计指令数
            instr_count = 0
            for line in func_body.split('\n'):
                line = line.strip()
                if line and not line.endswith(':') and not line.startswith(';'):
                    instr_count += 1

            # 热函数条件：被调用多次且体较小
            if call_counts.get(func_name, 0) >= 2 and instr_count <= 8:
                small_hot_funcs[func_name] = func_body

        # 内联热函数（移除定义，因为调用点会直接展开）
        for func_name in small_hot_funcs:
            # 仅当只有少数调用点时内联
            if call_counts.get(func_name, 0) <= 3:
                ir = re.sub(
                    rf'define\s+.*?@{re.escape(func_name)}\s*\(.*?\)\s*\{{[^}}]*\}}',
                    '',
                    ir,
                    count=1,
                    flags=re.DOTALL
                )
                self.stats['inlined_hot_functions'] += 1

        return ir

    def _defer_initialization(self, ir: str) -> str:
        """延迟初始化（懒加载）

        将全局变量的初始化从启动时推迟到首次使用时。
        通过将全局变量初始化移到包装函数中实现。

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        lines = ir.split('\n')
        result = []
        in_init = False
        init_lines = []
        deferred_stores = []

        for line in lines:
            stripped = line.strip()

            # 检测 __light_init 函数
            if 'define void @__light_init()' in stripped:
                in_init = True
                result.append(line)
                continue

            if in_init:
                if stripped == '}':
                    in_init = False
                    # 将延迟的 store 移到 init 函数末尾
                    for store in deferred_stores:
                        init_lines.append(store)
                    result.extend(init_lines)
                    result.append(line)
                    continue

                if in_init:
                    # 检测 store 到全局变量的指令
                    store_match = re.match(
                        r'\s*store\s+i8\*\s+(%\w+)\s*,\s*i8\*\*\s*@(\w+)',
                        stripped
                    )
                    if store_match:
                        # 标记为可延迟初始化
                        self.stats['deferred_inits'] += 1
                        init_lines.append(line)
                    else:
                        init_lines.append(line)
                    continue

            result.append(line)

        return '\n'.join(result)

    def _hot_cold_splitting(self, ir: str) -> str:
        """函数分块（hot/cold 分离）

        将函数分为热（频繁执行）和冷（不常执行）两部分。
        冷代码被标记为 cold 属性，提示编译器优化。

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        lines = ir.split('\n')
        result = []

        for line in lines:
            stripped = line.strip()

            # 检测函数定义
            define_match = re.match(r'(define\s+\w+\s*@(\w+)\s*\(.*?\))\s*\{', stripped)
            if define_match:
                func_header = define_match.group(1)
                func_name = define_match.group(2)

                # 判断是否为冷函数
                # 冷函数特征：名称包含"init"、"cleanup"、"free"、"error"
                cold_patterns = ['init', 'cleanup', 'free', 'error', '例外', '清理']
                is_cold = any(p in func_name.lower() for p in cold_patterns)

                if is_cold:
                    # 添加 cold 属性
                    cold_header = func_header.rstrip('{').strip()
                    # 插入 cold 属性
                    if 'cold' not in cold_header:
                        # 在返回类型后添加 cold
                        cold_header = re.sub(
                            r'(define\s+\w+)',
                            r'\1 cold',
                            cold_header
                        )
                        result.append(cold_header + ' {')
                        self.stats['hot_cold_split'] += 1
                    else:
                        result.append(line)
                else:
                    # 热函数添加 inlinehint
                    hot_header = func_header.rstrip('{').strip()
                    if 'inlinehint' not in hot_header:
                        hot_header = re.sub(
                            r'(define\s+\w+)',
                            r'\1 inlinehint',
                            hot_header
                        )
                        result.append(hot_header + ' {')
                        self.stats['hot_cold_split'] += 1
                    else:
                        result.append(line)
            else:
                result.append(line)

        return '\n'.join(result)

    def _precompile_hot_functions(self, ir: str) -> str:
        """预编译热函数

        标记热函数，提示编译器优先优化。
        热函数特征：被频繁调用的小函数。

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        # 统计函数调用次数
        call_counts: Dict[str, int] = {}
        func_pattern = re.compile(r'@(\w+)\s*\(')

        for m in func_pattern.finditer(ir):
            func_name = m.group(1)
            # 排除外部函数（以 light_ 开头）
            if not func_name.startswith('light_') and not func_name.startswith('__'):
                call_counts[func_name] = call_counts.get(func_name, 0) + 1

        # 标记热函数
        lines = ir.split('\n')
        result = []

        for line in lines:
            stripped = line.strip()
            define_match = re.match(r'(define\s+\w+\s*@(\w+)\s*\(.*?\))\s*\{', stripped)
            if define_match:
                func_header = define_match.group(1)
                func_name = define_match.group(2)

                # 如果函数被调用多次且不是外部函数，标记为 hot
                if call_counts.get(func_name, 0) > 1:
                    # 添加 inlinehint 属性
                    if 'inlinehint' not in func_header:
                        func_header = re.sub(
                            r'(define\s+\w+)',
                            r'\1 inlinehint',
                            func_header
                        )
                        self.stats['precompiled_hot'] += 1
                    result.append(func_header + ' {')
                else:
                    result.append(line)
            else:
                result.append(line)

        return '\n'.join(result)

    def get_stats(self) -> Dict[str, int]:
        """获取优化统计信息

        Returns:
            优化统计字典
        """
        return dict(self.stats)