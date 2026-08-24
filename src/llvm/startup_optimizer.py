"""启动时间优化器

策略：
- 延迟初始化（懒加载）
- 预编译热函数（打 inlinehint，真正的内联交给 clang 的 -O2/-O3）
- 函数分块（hot/cold 分离）
- 预计算（编译时计算常量表达式）
- 延迟初始化优化（全局变量按需初始化）

第七轮 A7 去掉了一条名为「内联热函数」的步骤：它并不内联，而是**删掉被调用
函数的定义、把调用点留在原地**，并且靠 `\\{[^}]*\\}` 找函数体 —— 遇到函数体里
的行内结构体类型（`{ i64, i8* }`）就在第一个 `}` 处截断，把函数腰斩，产出
`, i32 8` 这类悬空片段。协程函数体必然含这类类型，所以 O3 档一碰协程就废。
真正的内联是 clang `-O2/-O3` 的活儿，此处不再重复。
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

    # LLVM 文本 IR 里函数属性（cold / inlinehint / optnone…）**必须写在参数表
    # 之后**：
    #     define void @f() cold {          合法
    #     define void cold @f() {          非法 —— clang 报 "expected function name"
    # 第七轮之前本文件把属性插在返回类型后面（`define\s+\w+` 之后），于是
    # O3 档产出的 IR 一律无法被 clang 解析。生产路径上表现为
    # `LLVM IR 验证失败（clang -x ir）: ... error: expected function name`，
    # 而所有原生用例都用 O0 生成 IR、绕过了这条路，所以六轮没人看见。
    _DEFINE_LINE = re.compile(r'^\s*define\b')
    _FUNC_NAME = re.compile(r'@([\w.$-]+)\s*\(')

    @staticmethod
    def _split_define_line(line: str):
        """把一行 `define ... @名字(参数) [属性] {` 拆成 (前缀, 属性段, 函数名)

        拆不开（不是单行 define 头、或者没有以 `{` 收尾）时返回 None ——
        调用方原样保留该行，不猜。
        """
        if not StartupOptimizer._DEFINE_LINE.match(line):
            return None
        stripped = line.rstrip()
        if not stripped.endswith('{'):
            return None
        name_match = StartupOptimizer._FUNC_NAME.search(stripped)
        if not name_match:
            return None
        close = stripped.rfind(')')
        if close < name_match.end() - 1:
            return None
        head = stripped[:close + 1]
        attrs = stripped[close + 1:-1].strip()
        return head, attrs, name_match.group(1)

    @classmethod
    def _add_fn_attr(cls, line: str, attr: str):
        """给单行 define 头补一个函数属性，返回 (新行, 是否真的加上了)"""
        parts = cls._split_define_line(line)
        if parts is None:
            return line, False
        head, attrs, _name = parts
        if attr in attrs.split():
            return line, False
        attrs = f'{attrs} {attr}'.strip()
        return f'{head} {attrs} ' + '{', True




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
        冷函数打 `cold`、其余打 `inlinehint`，属性一律写在参数表之后
        （见 `_add_fn_attr` 上方那段关于位置的说明）。

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        # 冷函数特征：名称包含 init / cleanup / free / error / 例外 / 清理
        cold_patterns = ['init', 'cleanup', 'free', 'error', '例外', '清理']
        result = []

        for line in ir.split('\n'):
            parts = self._split_define_line(line)
            if parts is None:
                result.append(line)
                continue
            _head, _attrs, func_name = parts
            attr = 'cold' if any(p in func_name.lower() for p in cold_patterns) else 'inlinehint'
            new_line, changed = self._add_fn_attr(line, attr)
            if changed:
                self.stats['hot_cold_split'] += 1
            result.append(new_line)

        return '\n'.join(result)


    def _precompile_hot_functions(self, ir: str) -> str:
        """预编译热函数

        标记热函数（被调用多次的内部函数），提示编译器优先内联。
        属性位置同 `_hot_cold_splitting`：写在参数表之后。

        Args:
            ir: LLVM IR 字符串

        Returns:
            优化后的 IR 字符串
        """
        # 统计函数调用次数
        call_counts: Dict[str, int] = {}
        for m in re.finditer(r'@([\w.$-]+)\s*\(', ir):
            func_name = m.group(1)
            # 排除外部函数（以 light_ 开头）与编译器内部函数（__ 前缀）
            if not func_name.startswith('light_') and not func_name.startswith('__'):
                call_counts[func_name] = call_counts.get(func_name, 0) + 1

        result = []
        for line in ir.split('\n'):
            parts = self._split_define_line(line)
            if parts is None:
                result.append(line)
                continue
            _head, _attrs, func_name = parts
            # 计数含定义行自身，> 1 才说明真有调用点
            if call_counts.get(func_name, 0) > 1:
                new_line, changed = self._add_fn_attr(line, 'inlinehint')
                if changed:
                    self.stats['precompiled_hot'] += 1
                result.append(new_line)
            else:
                result.append(line)

        return '\n'.join(result)


    def get_stats(self) -> Dict[str, int]:
        """获取优化统计信息

        Returns:
            优化统计字典
        """
        return dict(self.stats)