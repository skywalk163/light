"""LLVM IR 优化 Pass 管线

支持多级优化 (-O0, -O1, -O2, -O3, -Os, -Oz)，
包含自定义优化 Pass 以及与 clang 集成的优化流程。
"""

import re
import time
from typing import List, Optional, Dict, Callable

from .opt_passes import (
    TailCallOptimizationPass,
    ConstantPropagationPass,
    StrengthReductionPass,
    IfConversionPass,
    LoopUnrollPass,
    GlobalOptimizationPass,
)


class PassStats:
    """单个 Pass 的统计信息"""

    def __init__(self, name: str):
        self.name = name
        self.start_time = 0.0
        self.end_time = 0.0
        self.input_size = 0
        self.output_size = 0
        self.status = 'pending'  # pending | running | done | skipped

    @property
    def elapsed(self) -> float:
        if self.end_time > 0:
            return self.end_time - self.start_time
        return 0.0

    @property
    def reduction(self) -> float:
        if self.input_size > 0:
            return (1 - self.output_size / self.input_size) * 100
        return 0.0

    def __repr__(self) -> str:
        return (f"  {self.name}: {self.elapsed:.3f}s, "
                f"{self.input_size} -> {self.output_size} 字"
                f" ({self.reduction:+.1f}%) [{self.status}]")


class OptimizationPipeline:
    """优化 Pass 管线管理器

    支持多级优化 (-O0, -O1, -O2, -O3, -Os, -Oz)，
    每级包含不同的 Pass 组合。

    Attributes:
        opt_level: 优化级别字符串 ('O0'-'O3', 'Os', 'Oz')
        passes: 当前管线的 Pass 列表
        stats: 各 Pass 统计信息
        verbose: 是否输出详细信息
    """

    def __init__(self, opt_level: str = 'O2', verbose: bool = False):
        self.opt_level = opt_level
        self.passes: List[Callable[[str], str]] = []
        self.stats: List[PassStats] = []
        self.verbose = verbose
        self.build_pipeline()
        # 全局 Pass 统计（累计所有管线运行）
        self._global_stats: Dict[str, Dict] = {}

    def build_pipeline(self) -> List[Callable[[str], str]]:
        """根据优化级别构建 Pass 管线"""
        level = self.opt_level.upper()
        if level.startswith('O'):
            level = level[1:]  # 去掉 'O' 前缀

        pipeline_map = {
            '0': self._get_0_passes,
            '1': self._get_1_passes,
            '2': self._get_2_passes,
            '3': self._get_3_passes,
            'S': self._get_s_passes,
            's': self._get_s_passes,
            'Z': self._get_z_passes,
            'z': self._get_z_passes,
        }

        builder = pipeline_map.get(level, self._get_2_passes)
        self.passes = builder()
        return self.passes

    def run(self, ir: str) -> str:
        """运行整个优化管线

        Args:
            ir: 输入的 LLVM IR 字符串

        Returns:
            优化后的 LLVM IR 字符串
        """
        if self.opt_level in ('O0', 'o0', '0'):
            if self.verbose:
                print(f"[优化管线] 优化级别 {self.opt_level}，跳过优化")
            return ir

        if self.verbose:
            print(f"[优化管线] 优化级别 {self.opt_level}，{len(self.passes)} 个 Pass")
            print(f"  输入 IR 大小: {len(ir)} 字符")

        result = ir
        self.stats = []

        for i, pass_fn in enumerate(self.passes):
            pass_name = getattr(pass_fn, '__name__', str(pass_fn))
            stat = PassStats(pass_name)
            stat.input_size = len(result)
            stat.start_time = time.time()
            stat.status = 'running'
            self.stats.append(stat)

            try:
                result = pass_fn(result)
                stat.end_time = time.time()
                stat.output_size = len(result)
                stat.status = 'done'

                if self.verbose:
                    print(f"  [{i+1}/{len(self.passes)}] {stat}")
            except Exception as e:
                stat.end_time = time.time()
                stat.output_size = len(result)
                stat.status = 'skipped'
                if self.verbose:
                    print(f"  [{i+1}/{len(self.passes)}] {pass_name}: 跳过 ({e})")

        if self.verbose:
            total_time = sum(s.elapsed for s in self.stats)
            total_reduction = (1 - len(result) / len(ir)) * 100 if len(ir) > 0 else 0
            print(f"  [总计] {total_time:.3f}s, {len(ir)} -> {len(result)} 字"
                  f" ({total_reduction:+.1f}%)")

        return result

    def get_0_passes(self) -> List[Callable[[str], str]]:
        """-O0: 无优化"""
        return []

    def get_1_passes(self) -> List[Callable[[str], str]]:
        """-O1: 基本优化"""
        return self._get_1_passes()

    def get_2_passes(self) -> List[Callable[[str], str]]:
        """-O2: 标准优化"""
        return self._get_2_passes()

    def get_3_passes(self) -> List[Callable[[str], str]]:
        """-O3: 激进优化"""
        return self._get_3_passes()

    def get_s_passes(self) -> List[Callable[[str], str]]:
        """-Os: 体积优化"""
        return self._get_s_passes()

    def get_z_passes(self) -> List[Callable[[str], str]]:
        """-Oz: 激进体积优化"""
        return self._get_z_passes()

    # ------------------------------------------------------------------
    # Pass 级别定义
    # ------------------------------------------------------------------

    def _get_0_passes(self) -> List[Callable[[str], str]]:
        return []

    def _get_1_passes(self) -> List[Callable[[str], str]]:
        """-O1: 基本优化

        包含常量传播、强度削弱、条件转换、窥孔优化。
        """
        cp = ConstantPropagationPass()
        sr = StrengthReductionPass()
        ic = IfConversionPass()
        return [
            cp.run,
            sr.run,
            ic.run,
            self._peephole_pass,
        ]

    def _get_2_passes(self) -> List[Callable[[str], str]]:
        """-O2: 标准优化

        包含 O1 所有 Pass + 尾调用优化、函数内联优化、循环不变代码外提、
        全局优化、基本块合并。
        """
        cp = ConstantPropagationPass()
        sr = StrengthReductionPass()
        ic = IfConversionPass()
        tc = TailCallOptimizationPass()
        go = GlobalOptimizationPass()
        return [
            cp.run,
            sr.run,
            ic.run,
            tc.run,
            self._peephole_pass,
            self._inline_small_functions_pass,
            self._loop_invariant_code_motion_pass,
            go.run,
            self._merge_blocks_pass,
        ]

    def _get_3_passes(self) -> List[Callable[[str], str]]:
        """-O3: 激进优化

        包含 O2 所有 Pass + 循环展开（更大因子）、向量化提示、
        更激进的内联、全局优化。
        """
        cp = ConstantPropagationPass()
        sr = StrengthReductionPass()
        ic = IfConversionPass()
        tc = TailCallOptimizationPass()
        lu = LoopUnrollPass(factor=8)
        go = GlobalOptimizationPass()
        return [
            cp.run,
            sr.run,
            ic.run,
            tc.run,
            self._peephole_pass,
            self._inline_small_functions_pass,
            self._loop_invariant_code_motion_pass,
            self._vectorization_hint_pass,
            lu.run,
            self._merge_blocks_pass,
            go.run,
        ]

    def _get_s_passes(self) -> List[Callable[[str], str]]:
        """-Os: 体积优化

        侧重减小代码体积，包含：
        - 常量合并
        - 死代码消除（移除未使用的函数和全局变量）
        - 小函数内联（仅单次调用者）
        - 基本块合并
        - 指令合并
        """
        cp = ConstantPropagationPass()
        sr = StrengthReductionPass()
        ic = IfConversionPass()
        return [
            cp.run,
            sr.run,
            ic.run,
            self._remove_unused_globals_pass,
            self._remove_unused_functions_pass,
            self._inline_single_call_functions_pass,
            self._merge_blocks_pass,
            self._instruction_combining_pass,
        ]

    def _get_z_passes(self) -> List[Callable[[str], str]]:
        """-Oz: 激进体积优化

        包含 Os 所有优化 + 更激进的大小缩减。
        """
        cp = ConstantPropagationPass()
        sr = StrengthReductionPass()
        ic = IfConversionPass()
        return [
            cp.run,
            sr.run,
            ic.run,
            self._remove_unused_globals_pass,
            self._remove_unused_functions_pass,
            self._inline_single_call_functions_pass,
            self._merge_blocks_pass,
            self._instruction_combining_pass,
            self._aggressive_size_reduce_pass,
        ]

    # ------------------------------------------------------------------
    # 内建 Pass（基于文本替换的简单 IR 优化）
    # ------------------------------------------------------------------

    @staticmethod
    def _peephole_pass(ir: str) -> str:
        """窥孔优化 Pass：局部 IR 模式替换"""
        # 消除冗余的 load/store 对
        ir = re.sub(
            r'%(\d+) = load i8\*, i8\*\* %(\d+)\s*\n\s*store i8\* %\1, i8\*\* %\2',
            '', ir
        )
        # 注意：这里原本有一条「消除连续的 br 跳转」规则：
        #     re.sub(r'br label %(\w+)\s*\n\s*\1:', r'\1:', ir)
        # 它把无条件跳转删掉、只留目标标签，于是前驱基本块失去终结指令，
        # 产出的 IR 非法（clang 在标签行报 "expected instruction opcode"）。
        # 而且窥孔层面拿不到前驱个数，无法判断这条 br 是否是目标块的唯一入口，
        # 单前驱才可以删。删块合并的活儿交给 _merge_blocks_pass（那里做引用
        # 计数），此处不再做这个替换。
        # 消除冗余的 alloca（分配后立即 store 再 load）
        ir = re.sub(
            r'%(\d+) = alloca i8\*\s*\n\s*store i8\* (%\w+), i8\*\* %\1\s*\n\s*%(\d+) = load i8\*, i8\*\* %\1',
            r'  %\3 = add i8* \2, 0',
            ir
        )
        return ir

    @staticmethod
    def _remove_unused_globals_pass(ir: str) -> str:
        """移除未使用的全局变量"""
        # 查找所有 private 全局变量
        global_vars = re.findall(r'@([\w.]+)\s*=\s*private\s+.*', ir)
        for var_name in global_vars:
            # 检查是否在 IR 中被引用（除了定义行）
            pattern = re.escape(f'@{var_name}')
            matches = re.findall(pattern, ir)
            if len(matches) <= 1:
                # 未被引用，移除定义
                ir = re.sub(
                    rf'@{re.escape(var_name)}\s*=\s*private\s+[^\n]*\n',
                    '',
                    ir
                )
        return ir

    @staticmethod
    def _remove_unused_functions_pass(ir: str) -> str:
        """移除未使用的函数定义（除 main / __light_init 外）

        判据：函数名除了自己的 `define` 行以外，全模块再无任何出现。
        """
        return OptimizationPipeline._drop_unreferenced_functions(ir)

    # ------------------------------------------------------------------
    # 函数体定位：**按行扫**，不用 `\{[^}]*\}` 这类正则
    # ------------------------------------------------------------------
    # 历史缺陷（第七轮 A7 修）：本文件与 startup_optimizer.py 都用
    #   rf'define\s+.*?@{name}\s*\(.*?\)\s*\{{[^}}]*\}}'
    # 找函数体。`[^}]*` 在遇到函数体里的行内结构体类型（`{ i64, i8* }`、
    # `%结构 = type { i32, i8* }`）时会在第一个 `}` 处停住，于是删掉的是
    # 「函数头 + 半个函数体」，剩下的后半截变成悬空文本（`, i32 8`），
    # 产出的 IR 连 clang 的 parser 都过不了。协程函数体必然含这类类型。
    #
    # 本仓 codegen 的函数体收尾恒为**单独一行的 `}`**（结构体类型写在行内），
    # 所以按行扫是可靠的，且与 `_label_ref_counts_by_line` 的既有口径同源。

    @staticmethod
    def _function_spans(lines: List[str]) -> List[tuple]:
        """返回 [(define 行号, 收尾 `}` 行号, 函数名)]，找不到名字的跳过"""
        chars = OptimizationPipeline._LABEL_CHARS
        spans = []
        n = len(lines)
        i = 0
        while i < n:
            if re.match(r'\s*define\b', lines[i]):
                name_match = re.search(rf'@({chars})\s*\(', lines[i])
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

    @staticmethod
    def _drop_unreferenced_functions(ir: str, max_instrs: int = None) -> str:
        """删掉「除定义行外全模块零引用」的内部函数定义

        Args:
            ir: LLVM IR 字符串
            max_instrs: 只删指令数不超过该值的函数；None 表示不限
        """
        lines = ir.split('\n')
        spans = OptimizationPipeline._function_spans(lines)
        drop = set()
        for start, end, name in spans:
            if name in ('main', '__light_init'):
                continue
            body = lines[start + 1:end]
            if max_instrs is not None:
                instrs = [l.strip() for l in body
                          if l.strip() and not l.strip().endswith(':')
                          and not l.strip().startswith(';')]
                if len(instrs) > max_instrs:
                    continue
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
        if not drop:
            return ir
        return '\n'.join(l for i, l in enumerate(lines) if i not in drop)


    # 标签名字符集：LLVM 的裸标识符允许字母数字与 [-$._]
    _LABEL_CHARS = r'[\w.$-]+'

    @staticmethod
    def _count_label_refs(text: str) -> Dict[str, int]:
        """统计文本里每个基本块标签被引用（即被当作前驱目标）的次数。

        必须覆盖本仓真实发射/消费的**全部**引用形式，漏一种就会把多前驱
        误判成单前驱、进而删掉不该删的 br：

        1. `br label %X`                       —— 无条件跳转（本文件 _merge_blocks_pass）
        2. `br i1 %c, label %X, label %Y`      —— 条件跳转（opt_passes.py:349 消费此形态）
        3. `switch i32 %r, label %D [ i32 0, label %X ... ]`
           —— codegen_typed.py:3276 把 switch 发射成**单行**（case 之间以空格分隔），
              但 src/llvm/core.py 的验证器（commit e27277c2）已按方括号配平支持多行
              形态，所以这里对单行/多行都必须成立。做法是不去解析 switch 的结构，
              直接统计所有 `label %X`，default 与每个 case 各记一次。
        4. `%r = phi i32 [ %v, %X ], [ 3, %Y ]`
           —— phi 的来源块也是前驱（opt_passes.py:365/475、本文件 _loop_invariant_
              code_motion_pass:486 都按这个形态匹配）。

        第 1~3 类统一由 `label %X` 覆盖（invoke 的 to/unwind 目标同理）；第 4 类
        单独扫方括号里 `, %X ]` 的形状——`[4 x i32]` 这类类型写法逗号后面不是 `%`，
        不会误计。
        """
        counts: Dict[str, int] = {}
        chars = OptimizationPipeline._LABEL_CHARS
        for name in re.findall(rf'\blabel\s+%({chars})', text):
            counts[name] = counts.get(name, 0) + 1
        for name in re.findall(rf'\[[^\[\]]*?,\s*%({chars})\s*\]', text):
            counts[name] = counts.get(name, 0) + 1
        return counts

    @staticmethod
    def _label_ref_counts_by_line(lines: List[str]) -> List[Dict[str, int]]:
        """给每一行配一张「其所属函数内」的标签引用计数表。

        标签是函数作用域的：`entry` / `endif_2` 这类名字会在多个函数里重复出现，
        跨函数合并统计会把单前驱错算成多前驱（偏保守、不产生非法 IR，但会白白
        放过可合并的块）。函数外的行（全局声明等）退回整模块计数兜底。
        """
        module_table = OptimizationPipeline._count_label_refs('\n'.join(lines))
        tables: List[Dict[str, int]] = [module_table] * len(lines)
        n = len(lines)
        i = 0
        while i < n:
            if re.match(r'\s*define\b', lines[i]):
                j = i
                # 函数体的收尾是单独一行的 `}`（结构体类型 `{ i32, ... }` 写在行内，
                # 不会被误当成函数结尾）
                while j < n and not re.match(r'\s*\}\s*$', lines[j]):
                    j += 1
                end = min(j, n - 1)
                table = OptimizationPipeline._count_label_refs('\n'.join(lines[i:end + 1]))
                for k in range(i, end + 1):
                    tables[k] = table
                i = end + 1
            else:
                i += 1
        return tables

    @staticmethod
    def _merge_blocks_pass(ir: str) -> str:
        """合并连续的基本块

        只在「本行是 `br label %X`、下一行就是 `X:`、且 X 在本函数内**只被引用
        一次**」时才合并。此时那唯一一次引用就是这条 br，删掉 br 之后标签变成
        死标签，连标签行一起删掉才是真正的块合并——只删 br 留标签的话，前驱块
        失去终结指令、后面又跟着一个标签行，产出的 IR 非法（clang 在标签行报
        "expected instruction opcode"）。

        目标标签被引用多次（别的 br / switch case / phi 还指着它）时，那条 br
        是必需的终结指令，一律保留。
        """
        lines = ir.split('\n')
        ref_tables = OptimizationPipeline._label_ref_counts_by_line(lines)
        chars = OptimizationPipeline._LABEL_CHARS
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            next_line = lines[i + 1] if i + 1 < len(lines) else ''
            br_match = re.match(rf'\s*br label %({chars})\s*$', line)
            next_label_match = re.match(rf'\s*({chars}):\s*$', next_line) if next_line else None
            if br_match and next_label_match and br_match.group(1) == next_label_match.group(1):
                if ref_tables[i].get(br_match.group(1), 0) <= 1:
                    # 单前驱：br 与标签行一起删掉，两块真正并成一块
                    i += 2
                    continue
                # 多前驱：保留 br（否则当前块没有终结指令）
            result.append(line)
            i += 1
        return '\n'.join(result)

    @staticmethod
    def _aggressive_size_reduce_pass(ir: str) -> str:
        """激进体积缩减 Pass"""
        # 1. 移除所有注释
        ir = re.sub(r';[^\n]*', '', ir)
        # 2. 合并空行
        ir = re.sub(r'\n\s*\n\s*\n', '\n\n', ir)
        # 3. 移除 debug 相关的 metadata（非 -g 模式下）
        ir = re.sub(r'!dbg\s*!\d+', '', ir)
        ir = re.sub(r'!\d+\s*=\s*!DI[^\n]*', '', ir)
        # 4. 移除尾部空格
        lines = [l.rstrip() for l in ir.split('\n')]
        return '\n'.join(lines)

    @staticmethod
    def _inline_small_functions_pass(ir: str) -> str:
        """小函数清理 Pass

        名字沿用历史（`inline_small_functions`），实际行为是**删掉体积很小
        （<= 5 条指令）且全模块无调用点的函数定义** —— 它从来没有真的内联过
        任何东西，真正的内联是 clang `-O2/-O3` 的活儿。函数体定位见
        `_function_spans`：按行扫到单独一行的 `}`，不用会被行内结构体类型
        截断的 `\\{[^}]*\\}`。
        """
        return OptimizationPipeline._drop_unreferenced_functions(ir, max_instrs=5)



    @staticmethod
    def _inline_single_call_functions_pass(ir: str) -> str:
        """无调用点函数清理 Pass（体积优化用）

        与 `_inline_small_functions_pass` 同源，只是不限函数体大小。
        """
        return OptimizationPipeline._drop_unreferenced_functions(ir)


    @staticmethod
    def _loop_invariant_code_motion_pass(ir: str) -> str:
        """循环不变代码外提（LICM）Pass

        将循环中不变的指令（如常量加载）外提到循环前。
        """
        # 检测简单循环模式并尝试外提不变量
        lines = ir.split('\n')
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # 检测循环头部（phi 节点）
            phi_match = re.match(
                r'\s*(%\w+)\s*=\s*phi\s+(\w+)\s*\[(\d+),\s*%(\w+)\]\s*,\s*\[(%\w+),\s*%(\w+)\]',
                line
            )
            if phi_match:
                # 找到循环体
                loop_body_lines = []
                j = i + 1
                while j < len(lines):
                    l = lines[j]
                    loop_body_lines.append(l)
                    if re.match(r'\s*br\s+', l):
                        j += 1
                        break
                    j += 1

                # 检测循环体中的不变指令（getelementptr 和常量加载）
                entry_block = phi_match.group(4)
                invariant_lines = []
                remaining_lines = []
                for l in loop_body_lines:
                    stripped = l.strip()
                    # 如果指令的操作数不依赖于循环变量，视为不变
                    if re.match(r'\s*%\w+\s*=\s*(getelementptr|load)\s+', stripped):
                        # 简单启发：不引用 phi 寄存器的指令视为不变
                        phi_reg = phi_match.group(1)
                        if phi_reg not in stripped:
                            invariant_lines.append(l)
                            continue
                    remaining_lines.append(l)

                # 将不变指令外提到循环前（在 entry 块中）
                if invariant_lines:
                    result.append(line)
                    # 将不变指令插入到循环前（替换原 br 跳转目标）
                    result.extend(remaining_lines)
                    i = j
                    continue

            result.append(line)
            i += 1

        return '\n'.join(result)

    @staticmethod
    def _vectorization_hint_pass(ir: str) -> str:
        """向量化提示 Pass

        为循环添加向量化 metadata，提示后端进行向量化优化。
        """
        # 在循环的 br 指令前添加 llvm.loop 向量化 metadata
        lines = ir.split('\n')
        result = []
        loop_depth = 0

        for line in lines:
            stripped = line.strip()
            # 检测 phi 节点（循环头部）
            if re.match(r'\s*%\w+\s*=\s*phi\s+', stripped):
                loop_depth += 1
            # 在 br 指令前添加向量化提示
            if re.match(r'\s*br\s+i1\s+', stripped) and loop_depth > 0:
                result.append(line)
                # 添加 llvm.loop 向量化 metadata
                md_id = len([l for l in result if l.startswith('!')]) + 1
                result.append(f'  !{md_id} = !{{!{md_id + 1}}}')
                result.append(f'  !{md_id + 1} = !{{!"llvm.loop.vectorize.enable", i1 true}}')
                loop_depth -= 1
            else:
                result.append(line)

        return '\n'.join(result)

    @staticmethod
    def _instruction_combining_pass(ir: str) -> str:
        """指令合并 Pass

        合并连续的相同类型操作，简化 IR。
        - 连续的 add 0 指令合并
        - 连续的 getelementptr 合并
        """
        lines = ir.split('\n')
        result = []
        skip_next = False

        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            stripped = line.strip()
            # 检测连续的 add 0（常量传播后的残留）
            if re.match(r'\s*%\w+\s*=\s*add\s+\w+\s+\S+\s*,\s*0\s', stripped):
                # 检查下一行是否也是 add 0
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'\s*%\w+\s*=\s*add\s+\w+\s+\S+\s*,\s*0\s', next_line):
                        # 合并：跳过下一行，将当前行的结果直接传递给下一行的使用
                        # 简化：只保留第一个 add 0
                        result.append(line)
                        skip_next = True
                        continue

            result.append(line)

        return '\n'.join(result)

    def get_summary(self) -> Dict:
        """获取优化管线运行摘要"""
        total_time = sum(s.elapsed for s in self.stats)
        total_input = self.stats[0].input_size if self.stats else 0
        total_output = self.stats[-1].output_size if self.stats else 0
        return {
            'opt_level': self.opt_level,
            'num_passes': len(self.passes),
            'total_time': total_time,
            'input_size': total_input,
            'output_size': total_output,
            'reduction_pct': (1 - total_output / total_input) * 100 if total_input > 0 else 0,
            'passes': [{
                'name': s.name,
                'time': s.elapsed,
                'input': s.input_size,
                'output': s.output_size,
                'status': s.status,
            } for s in self.stats],
        }