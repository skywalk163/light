"""代码体积优化器

策略：
- 去重同类函数
- 合并字符串常量
- 函数内联（小函数）
- 移除未使用的全局变量
- 合并基本块
- 死代码消除
- 常量折叠
- 指令合并
"""

import re
from typing import List, Set, Dict, Tuple, Optional


class SizeOptimizer:
    """代码体积优化器

    通过多种策略减小生成的 LLVM IR 体积，
    适用于 -Os（体积优化）和 -Oz（激进体积优化）模式。

    Attributes:
        stats: 优化统计信息
    """

    def __init__(self):
        self.stats = {
            'deduplicated_functions': 0,
            'merged_constants': 0,
            'inlined_functions': 0,
            'removed_globals': 0,
            'merged_blocks': 0,
            'dead_code_eliminated': 0,
            'constants_folded': 0,
            'instructions_combined': 0,
        }

    def optimize(self, ir: str) -> str:
        """运行所有体积优化

        Args:
            ir: 输入的 LLVM IR 字符串

        Returns:
            优化后的 LLVM IR 字符串
        """
        ir = self._dead_code_elimination(ir)
        ir = self._constant_folding(ir)
        ir = self._instruction_combining(ir)
        ir = self._deduplicate_functions(ir)
        ir = self._merge_constants(ir)
        ir = self._inline_small_functions(ir, max_size=10)
        ir = self._remove_unused_globals(ir)
        ir = self._merge_blocks(ir)
        return ir

    def _dead_code_elimination(self, ir: str) -> str:
        """死代码消除

        移除以下死代码：
        1. 定义后从未被使用的寄存器（非全局）
        2. 永远不会被执行的代码块（在无条件 ret 之后的代码）

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        lines = ir.split('\n')
        result = []
        in_function = False
        after_ret = False
        defined_regs: Set[str] = set()
        used_regs: Set[str] = set()

        # 第一遍：收集所有寄存器定义和使用
        for line in lines:
            stripped = line.strip()
            # 检测函数开始
            if stripped.startswith('define ') and '{' in stripped:
                in_function = True
                after_ret = False
                defined_regs.clear()
                used_regs.clear()
                continue

            if not in_function:
                continue

            # 检测函数结束
            if stripped == '}':
                # 在函数内部进行死代码消除
                in_function = False
                continue

            # 收集寄存器定义：%X = ...
            def_match = re.match(r'\s*(%\w+)\s*=\s*', stripped)
            if def_match:
                defined_regs.add(def_match.group(1))

            # 收集寄存器使用
            for m in re.finditer(r'(%\w+)', stripped):
                reg = m.group(1)
                if reg in defined_regs:
                    used_regs.add(reg)

        # 第二遍：移除死代码（函数内未使用的寄存器赋值）
        in_function = False
        unreachable_after_ret = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith('define ') and '{' in stripped:
                in_function = True
                unreachable_after_ret = False
                result.append(line)
                continue

            if not in_function:
                result.append(line)
                continue

            if stripped == '}':
                in_function = False
                result.append(line)
                continue

            # 检测 ret 指令（之后的代码不可达）
            if stripped.startswith('ret '):
                unreachable_after_ret = True
                result.append(line)
                continue

            # 如果已经在 ret 之后，跳过所有非标签代码
            if unreachable_after_ret:
                if stripped.endswith(':'):
                    unreachable_after_ret = False
                    result.append(line)
                else:
                    self.stats['dead_code_eliminated'] += 1
                    continue
                continue

            # 检查寄存器定义是否被使用
            def_match = re.match(r'\s*(%\w+)\s*=\s*', stripped)
            if def_match:
                reg = def_match.group(1)
                if reg not in used_regs:
                    # 但保留有副作用的指令（call、store 等）
                    if not any(kw in stripped for kw in ['call ', 'store ', 'br ', 'ret ']):
                        self.stats['dead_code_eliminated'] += 1
                        continue

            result.append(line)

        return '\n'.join(result)

    def _constant_folding(self, ir: str) -> str:
        """常量折叠

        在编译时计算常量表达式，如：
        - 算术运算：add/sub/mul/sdiv 等
        - 逻辑运算：and/or/xor 等

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        lines = ir.split('\n')
        result = []
        const_values: Dict[str, str] = {}  # 寄存器 -> 常量值

        for line in lines:
            stripped = line.strip()

            # 跳过非指令行
            if not stripped or stripped.startswith(';') or stripped.endswith(':'):
                result.append(line)
                continue

            # 尝试折叠算术指令
            folded = self._try_fold_arith(stripped, const_values)
            if folded:
                # 如果折叠成功，记录常量值
                def_match = re.match(r'\s*(%\w+)\s*=\s*', folded)
                val_match = re.search(r'add\s+\w+\s+(-?\d+)\s*,\s*0', folded)
                if def_match and val_match:
                    const_values[def_match.group(1)] = val_match.group(1)
                result.append(folded)
                self.stats['constants_folded'] += 1
                continue

            result.append(line)

        return '\n'.join(result)

    @staticmethod
    def _try_fold_arith(line: str, const_values: Dict[str, str]) -> Optional[str]:
        """尝试折叠算术运算

        Args:
            line: IR 指令行
            const_values: 已知的常量映射

        Returns:
            折叠后的指令行，如果不能折叠返回 None
        """
        # 匹配: %r = add i32 %const, %const
        m = re.match(
            r'\s*(%\w+)\s*=\s*'
            r'(add|sub|mul|sdiv|udiv|and|or|xor|shl|lshr|ashr)\s+'
            r'(\w+)\s+'
            r'(\S+)\s*,\s*'
            r'(\S+)',
            line
        )
        if not m:
            return None

        reg = m.group(1)
        op = m.group(2)
        ty = m.group(3)
        lhs_str = m.group(4)
        rhs_str = m.group(5)

        # 尝试将操作数解析为常量（直接数字或常量寄存器）
        lhs_val = None
        rhs_val = None

        try:
            if lhs_str.lstrip('-').isdigit():
                lhs_val = int(lhs_str)
            elif lhs_str in const_values:
                lhs_val = int(const_values[lhs_str])

            if rhs_str.lstrip('-').isdigit():
                rhs_val = int(rhs_str)
            elif rhs_str in const_values:
                rhs_val = int(const_values[rhs_str])
        except ValueError:
            return None

        # 两个操作数都是常量时才折叠
        if lhs_val is None or rhs_val is None:
            return None

        op_map = {
            'add': lambda a, b: a + b,
            'sub': lambda a, b: a - b,
            'mul': lambda a, b: a * b,
            'sdiv': lambda a, b: a // b if b != 0 else None,
            'udiv': lambda a, b: a // b if b != 0 else None,
            'and': lambda a, b: a & b,
            'or': lambda a, b: a | b,
            'xor': lambda a, b: a ^ b,
            'shl': lambda a, b: a << b,
            'lshr': lambda a, b: a >> b,
            'ashr': lambda a, b: a >> b,
        }

        if op in op_map:
            fn = op_map[op]
            result_val = fn(lhs_val, rhs_val)
            if result_val is not None:
                return f'  {reg} = add {ty} {result_val}, 0  ; folded {op} {lhs_val}, {rhs_val} -> {result_val}'

        return None

    def _instruction_combining(self, ir: str) -> str:
        """指令合并

        合并相邻的同类指令：
        1. 连续的 getelementptr 合并
        2. 冗余的 bitcast 消除
        3. 连续的 load 消除

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        lines = ir.split('\n')
        result = []
        skip_next = False

        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            stripped = line.strip()

            # 消除冗余的 bitcast（相同类型之间）
            if re.match(r'\s*%\w+\s*=\s*bitcast\s+(\S+)\s+(\S+)\s+%\w+\s+to\s+\1\s*$', stripped):
                # bitcast 到相同类型，可以移除
                self.stats['instructions_combined'] += 1
                continue

            # 合并连续的 add 0
            if re.match(r'\s*%\w+\s*=\s*add\s+\w+\s+\S+\s*,\s*0\s', stripped):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'\s*%\w+\s*=\s*add\s+\w+\s+\S+\s*,\s*0\s', next_line):
                        result.append(line)
                        skip_next = True
                        self.stats['instructions_combined'] += 1
                        continue

            result.append(line)

        return '\n'.join(result)

    def _deduplicate_functions(self, ir: str) -> str:
        """去重同类函数

        检测函数体完全相同的函数，合并为一个。

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        # 提取所有函数定义
        func_pattern = re.compile(
            r'(define\s+.*?@(\w+)\s*\(.*?\))\s*\{'
            r'([^}]*)\}',
            re.DOTALL
        )

        # 按函数体内容分组
        body_to_funcs: Dict[str, List[str]] = {}
        func_to_body: Dict[str, str] = {}

        for m in func_pattern.finditer(ir):
            func_header = m.group(1)
            func_name = m.group(2)
            func_body = m.group(3).strip()

            # 跳过外部声明
            if 'declare' in func_header:
                continue

            func_to_body[func_name] = func_body
            if func_body not in body_to_funcs:
                body_to_funcs[func_body] = []
            body_to_funcs[func_body].append(func_name)

        # 替换重复函数调用为第一个函数
        result = ir
        for body, names in body_to_funcs.items():
            if len(names) > 1:
                # 保留第一个函数，删除其他
                keep_name = names[0]
                for dup_name in names[1:]:
                    # 替换所有调用
                    result = re.sub(
                        rf'@\b{re.escape(dup_name)}\b(?=\s*\()',
                        f'@{keep_name}',
                        result
                    )
                    # 删除函数定义
                    result = re.sub(
                        rf'define\s+.*?@{re.escape(dup_name)}\s*\(.*?\)\s*\{{[^}}]*\}}',
                        '',
                        result,
                        count=1,
                        flags=re.DOTALL
                    )
                    self.stats['deduplicated_functions'] += 1

        return result

    def _merge_constants(self, ir: str) -> str:
        """合并字符串常量

        检测内容相同的字符串常量，合并为一个。

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        # 匹配字符串常量定义
        const_pattern = re.compile(
            r'(@[\w.]+)\s*=\s*private\s+unnamed_addr\s+constant\s+'
            r'\[(\d+)\s*x\s*i8\]\s*c"([^"]*)"'
        )

        # 按内容分组
        content_to_consts: Dict[str, List[Tuple[str, str]]] = {}
        for m in const_pattern.finditer(ir):
            name = m.group(1)
            size = m.group(2)
            content = m.group(3)
            if content not in content_to_consts:
                content_to_consts[content] = []
            content_to_consts[content].append((name, size))

        # 合并重复常量
        result = ir
        for content, consts in content_to_consts.items():
            if len(consts) > 1:
                keep_name = consts[0][0]
                for dup_name, _ in consts[1:]:
                    # 替换引用
                    result = result.replace(dup_name, keep_name)
                    # 移除重复定义
                    result = re.sub(
                        rf'{re.escape(dup_name)}\s*=\s*private\s+unnamed_addr\s+constant\s+'
                        rf'\[\d+\s*x\s*i8\]\s*c"[^"]*"',
                        '',
                        result
                    )
                    self.stats['merged_constants'] += 1

        return result

    # 函数名字符集：LLVM 裸标识符允许字母数字与 [-$._]
    _LABEL_CHARS = r'[\w.$-]+'

    def _function_spans(self, lines: List[str]) -> List[Tuple[int, int, str]]:
        """返回 [(define 行号, 收尾 `}` 行号, 函数名)]，找不到名字的跳过。

        按行扫到单独一行的 `}`，不用会被行内结构体类型截断的 `\\{[^}]*\\}`；
        与 optimizer_pipeline._function_spans 同源。
        """
        spans: List[Tuple[int, int, str]] = []
        n = len(lines)
        i = 0
        while i < n:
            if re.match(r'\s*define\b', lines[i]):
                name_match = re.search(rf'@({self._LABEL_CHARS})\s*\(', lines[i])
                j = i
                while j < n and not re.match(r'\s*\}\s*$', lines[j]):
                    j += 1
                end = min(j, n - 1)
                if name_match:
                    spans.append((i, end, name_match.group(1)))
                i = end + 1
            else:
                i += 1
        return spans

    def _inline_small_functions(self, ir: str, max_size: int = 10) -> str:
        """内联小函数（实际是清理零引用的小函数定义）

        删除前统计**全部**引用形式，只要存在任一引用就不删：
          - 直接调用：`call i32 @name(...)`
          - 地址取用：`@name` 出现在全局初始值 / ptrtoint / bitcast / 函数指针
            槽位等**值**位置
          - 间接调用：经函数指针的调用，其地址取用同样以 `@name` 文本出现
          - 其它引用：定义行以外任何 `@name` 出现都算引用（含跨函数/外部可见）
        定义行自身不算引用；`main` / `__light_init` 一律不删。

        Args:
            ir: LLVM IR 字符串
            max_size: 最大函数体大小（指令数），默认 10

        Returns:
            优化后的 IR 字符串
        """
        lines = ir.split('\n')
        spans = self._function_spans(lines)

        # 候选小函数：指令数 <= max_size 且非 main / __light_init
        candidates: List[Tuple[int, int, str]] = []
        for start, end, name in spans:
            if name in ('main', '__light_init'):
                continue
            body = lines[start + 1:end]
            instrs = [l.strip() for l in body
                      if l.strip() and not l.strip().endswith(':')
                      and not l.strip().startswith(';')]
            if len(instrs) <= max_size:
                candidates.append((start, end, name))

        # 引用检查：定义行之外任何 `@name` 出现即视为被引用，保留定义
        drop: Set[int] = set()
        for start, end, name in candidates:
            token = f'@{name}'
            referenced = False
            for idx, line in enumerate(lines):
                if idx == start:
                    continue  # 定义行自身不算引用
                if re.search(rf'{re.escape(token)}\b', line):
                    referenced = True
                    break
            if not referenced:
                drop.update(range(start, end + 1))
                self.stats['inlined_functions'] += 1

        if not drop:
            return ir
        return '\n'.join(l for i, l in enumerate(lines) if i not in drop)

    def _remove_unused_globals(self, ir: str) -> str:
        """移除未使用的全局变量

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        # 匹配所有全局变量定义
        global_pattern = re.compile(r'@([\w.]+)\s*=\s*(global|constant)\s+.*')

        # 收集所有全局变量
        globals_def = {}
        for m in global_pattern.finditer(ir):
            name = m.group(1)
            globals_def[name] = m.group(0)

        # 统计引用
        used_globals = set()
        for line in ir.split('\n'):
            for name in globals_def:
                if f'@{name}' in line:
                    # 排除定义行本身
                    if not line.strip().startswith(f'@{name} ='):
                        used_globals.add(name)

        # 移除未使用的
        result = ir
        for name, def_line in globals_def.items():
            if name not in used_globals:
                # 移除定义行
                result = result.replace(def_line + '\n', '')
                result = result.replace(def_line, '')
                self.stats['removed_globals'] += 1

        return result

    def _merge_blocks(self, ir: str) -> str:
        """合并基本块

        合并只有一条无条件跳转的连续基本块。

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        lines = ir.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # 检测模式: "br label %labelX" 后面紧跟 "labelX:"
            br_match = re.match(r'br label %(\w+)', line)
            if br_match and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                next_label_match = re.match(r'(\w+):', next_line)
                if next_label_match and br_match.group(1) == next_label_match.group(1):
                    # 跳过 br 指令，合并到下一个块
                    self.stats['merged_blocks'] += 1
                    i += 1
                    continue

            result.append(lines[i])
            i += 1

        return '\n'.join(result)

    def get_stats(self) -> Dict[str, int]:
        """获取优化统计信息

        Returns:
            优化统计字典
        """
        return dict(self.stats)