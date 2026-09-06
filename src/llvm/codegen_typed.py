"""
LLVM 代码生成器 - 类型版 (v3)
使用 LightValue 结构体（{ i32, i64, double, ptr }），
算术运算在原生类型上直接操作，无需 atoi/itoa 转换。
"""

from typing import Optional, Tuple, List
import sys
import platform as _platform
import types
import ast_nodes as ast
try:
    from .codegen import LLVMCodeGen
except ImportError:
    from codegen import LLVMCodeGen


def _detect_target_arch_internal(target_arg: str = None) -> str:
    """内部目标架构检测函数（避免循环导入）"""
    if target_arg is None:
        machine = _platform.machine().lower()
        if machine in ('aarch64', 'arm64', 'armv8l', 'armv8b'):
            return 'aarch64'
        return 'x86_64'
    target_lower = target_arg.lower().replace('-', '_').replace(' ', '_')
    if any(t in target_lower for t in ('aarch64', 'arm64', 'armv8')):
        return 'aarch64'
    if any(t in target_lower for t in ('x86_64', 'x64', 'amd64', 'x86')):
        return 'x86_64'
    return 'x86_64'


# LLVM 结构体类型：与 C 端 LightValue 布局匹配
# C 结构: { int type, int64_t i64, double f64, char* str, int boolean,
#           int list_size, int list_capacity, struct LightValue** list_data }
# 注意：为了安全起见，使用足够大的结构体（与 C sizeof(LightValue) 匹配）
LIGHTVALUE_STRUCT = '{ i32, i64, double, ptr, i32, i32, i32, ptr }'


# DWARF 调试信息标记
_DEBUG_METADATA_KINDS = {
    'DW_TAG': {
        'compile_unit': 0x11,
        'subprogram': 0x2e,
        'variable': 0x34,
        'structure_type': 0x13,
    },
    'DW_ATE': {
        'signed': 0x05,
        'unsigned': 0x07,
        'boolean': 0x02,
        'float': 0x04,
    },
    'DW_LANG': {
        'C': 0x0002,
        'C_plus_plus': 0x0004,
        'Python': 0x1007,
    },
}


class TypedLLVMCodeGen(LLVMCodeGen):
    """类型版 LLVM 代码生成器"""

    def __init__(self, target_platform: str = None, target_arch: str = None, debug: bool = False):
        super().__init__()
        self._dv_struct_slots = {}  # 栈上分配的结构体槽位
        self._classes = {}  # 类定义收集：class_name -> ClassDefinition
        self._interfaces = {}  # 接口定义收集：interface_name -> InterfaceDefinition
        self._method_result_ptr = None  # 当前方法的 result 指针（None 表示不在方法中）
        self._seg_result_ptr = None  # 当前段落函数的 result 指针（None 表示不在段落函数中）
        # T7B / T5C-02·04：段落参数写回表 [(arg_index, param_slot)]，仅普通段落设置
        self._seg_param_writeback = []
        self._current_class = None  # 当前方法所属的类名（None 表示不在方法中）
        self._current_method_type = None  # 当前方法类型：'instance' / 'class' / 'static'
        self._var_types = {}  # 变量类型追踪：var_name -> type_str (INT/FLOAT/BOOL/STRING/LIST/None)
        self._enable_type_opt = True  # 启用类型优化
        # 模块系统支持（Level 9）
        self._imports = {}
        self._module_imports = {}   # R12C（R11A-05）：模块名 -> {导入名: (源模块, 源名)}
        self._r12c_need_lstrip = False   # R12C（R11A-08）：用到 .lstrip() 时发射 IR 辅助函数
        self._r12c_need_title = False    # R12C（R11A-08）：用到 .每个单词首字母大写() 时发射 IR 辅助函数
        self._r12c_need_split_ws = False # R12C（R11A-08）：.分割() 无参空白切分辅助  # 导入符号表：符号名 -> (模块名, 原始符号名)
        self._imported_modules = set()  # 已导入的模块名集合
        self._module_decls = []  # 待生成的外部段函数声明
        self._segment_modifiers = {}  # 段的修饰符（异步等）
        self._current_module = None  # T9A: 当前生成代码所属模块名（None=单模块/主模块上下文）
        # 协程支持（Level 10）
        self._in_coroutine = False  # 当前是否在生成协程函数
        self._coro_handle_ptr = None  # 协程句柄指针（LightCoroutine*）
        self._coro_resume_point = 0  # 下一个 await 点的编号
        # ---- 生成器状态机（R10-11b 第四批B）----
        # `_gen_entry_insert_idx` 非 None 即表示「正在生成生成器状态机函数」。
        # 它同时是「往 entry 块插指令」的下标：生成器每次恢复都是重新调用，
        # 跨 `生成` 存活的一切（变量槽、临时槽、循环计数器 alloca）都必须落在
        # entry 块，否则恢复块拿不到定义 → LLVM "does not dominate all uses"。
        self._gen_entry_insert_idx = None
        self._gen_slot_index = 0        # 已用生成器槽位数
        self._gen_slot_budget = 1024    # 单生成器槽位上限（超出即报错，不静默截断）
        self._gen_yield_index = 0       # 本函数已发射的 `生成` 点数
        self._gen_resume_labels = []    # 第 k 个生成点的恢复标签
        # entry 回插指令的符号名序号：回插行与正文行在生成时刻交错，数字
        # 寄存器会「后造的编号小、先造的编号大」，文本序 ≠ 编号序，LLVM
        # 文本解析直接报 "expected to be numbered '%N' or greater"。所以
        # 凡是要回插 entry 的指令一律用符号名（%gslot.N / %galloc.N），
        # 不参与自动编号，正文的数字寄存器仍然单调递增。
        self._gen_entry_name_seq = 0
        # 目标平台：win32 / linux / darwin，默认根据当前系统判断
        self.target_platform = target_platform or sys.platform
        # 目标架构：x86_64 / aarch64，默认根据参数或本地架构检测
        self.target_arch = _detect_target_arch_internal(target_arch) if target_arch else 'x86_64'
        # IR 优化：SSA 值到 slot 指针的缓存，避免冗余 load/store
        self._dv_ssa_to_slot = {}  # dv_ssa_reg -> slot_ptr
        # 调试信息生成（DWARF）
        self._debug = debug
        self._debug_meta_idx = 0  # 元数据索引计数器
        self._debug_types = {}  # 缓存的调试类型
        self._current_debug_loc = None  # 当前调试位置 (line, col)
        self._debug_file_id = None  # DIFile 元数据 ID
        self._debug_cu_id = None  # DICompileUnit 元数据 ID
        self._debug_scope_id = None  # 当前调试作用域 ID
        self._debug_func_id = None  # 当前函数 DISubprogram ID
        self._debug_dv_struct_id = None  # LightValue 结构体类型 ID
        # 调试元数据行：单独收集，在 finalize 时追加到 IR 末尾
        # 因为 LLVM 要求所有 !N = !DIxxx 必须出现在文件末尾，不能在函数体中间
        self._debug_metadata_lines = []
        # 临时槽位池：使用单个数组替代多个 alloca，避免循环中动态栈分配
        self._temp_slot_pool = None  # 池数组的指针
        self._temp_slot_index = 0    # 当前可用槽位索引
        # 池大小上限（每个函数最多这么多临时槽位；真实分配量按用量回填，见
        # _begin_temp_slot_pool / _emit_temp_slot_pool）
        self._temp_slot_pool_size = 2048
        # 占位 alloca 在 self._lines 里的下标；函数体发射完毕后回填真实槽位数
        self._temp_slot_pool_line = None

    # ── T9A: 段名模块隔离辅助方法 ──────────────────────────────
    def _seg_reg_key(self, raw_name, module_name=None):
        """段在注册表中的 key：多模块时为 (module_name, raw_name) 元组，
        单模块（module_name=None）时为 raw_name 字符串，保持向后兼容。"""
        return (module_name, raw_name) if module_name is not None else raw_name

    def _seg_raw_name(self, reg_key):
        """从注册表 key 提取裸段名。"""
        return reg_key[1] if isinstance(reg_key, tuple) else reg_key

    def _seg_module_name(self, reg_key):
        """从注册表 key 提取模块名（单模块时返回 None）。"""
        return reg_key[0] if isinstance(reg_key, tuple) else None

    def _local_seg_key(self, raw_name):
        """在当前模块上下文中解析段的注册表 key。"""
        return self._seg_reg_key(raw_name, self._current_module)

    @property
    def is_windows(self) -> bool:
        return self.target_platform.startswith('win')

    @property
    def is_linux(self) -> bool:
        return self.target_platform.startswith('linux')

    @property
    def is_macos(self) -> bool:
        return self.target_platform == 'darwin'

    def alloca_local(self, name):
        """为局部变量分配 LightValue 栈空间（重写父类）

        注意：typed codegen 不 flush _pending_allocas（该字段仅被 append 后又
        被重置，从未发射进函数体），故走 pending 的 alloca 永远生成未定义值。
        局部变量的真正分配由 _gen_normal_segment / _gen_async_segment 在 entry
        块通过 _collect_vars_from_stmts + 批量 alloca 完成（见 3777-3780 等）。
        本方法保留父类契约：仅当变量尚未分配时才记录一个 pending 槽位编号，
        绝大多数情况下变量已被 entry 块预分配，此处守卫会跳过，不会覆盖有效
        寄存器，也不会在嵌套块内就地发射导致支配关系错误。
        """
        if name not in self._local_vars or self._local_vars[name] is None:
            reg = self.new_register()
            line = f'{reg} = alloca {LIGHTVALUE_STRUCT}'
            self._pending_allocas.append(line)
            self._local_vars[name] = reg
        return self._local_vars[name]

    # ============================================================
    # 调试信息生成（DWARF）
    # ============================================================

    def _new_debug_id(self) -> int:
        """生成新的调试元数据 ID"""
        self._debug_meta_idx += 1
        return self._debug_meta_idx

    def _get_debug_location(self, node) -> Tuple[int, int]:
        """从 AST 节点获取调试位置（行号，列号）"""
        line = getattr(node, 'lineno', 0) if node else 0
        col = getattr(node, 'col_offset', 0) if node else 0
        return (line, col)

    def _set_debug_location(self, line: int, col: int = 0):
        """设置当前调试位置"""
        self._current_debug_loc = (line, col)

    def _emit_debug_loc(self) -> str:
        """生成 !dbg 调试位置元数据引用，返回后缀字符串

        若未启用调试或未设置位置，返回空字符串；
        否则生成 !DILocation 元数据并返回 ", !dbg !N" 后缀。
        """
        if not self._debug or self._current_debug_loc is None:
            return ""
        line, col = self._current_debug_loc
        dbg_id = self._new_debug_id()
        self._emit_debug_metadata(f"!{dbg_id} = !DILocation(line: {line}, column: {col}, scope: !{self._debug_scope_id})")
        return f", !dbg !{dbg_id}"

    def _emit_debug_var(self, name: str, slot: str, line: int) -> str:
        """为局部变量生成调试信息（!DILocalVariable）

        返回 ", !dbg !N" 后缀用于附加到 store 指令。
        """
        if not self._debug:
            return ""
        var_id = self._new_debug_id()
        self._emit_debug_metadata(f'!{var_id} = !DILocalVariable(name: "{name}", arg: 0, scope: !{self._debug_scope_id}, file: !{self._debug_file_id}, line: {line})')
        return f", !dbg !{var_id}"

    def _gen_debug_types(self):
        """生成调试类型元数据（LightValue 结构体及基础类型）"""
        if not self._debug:
            return
        # LightValue 结构体类型定义
        self._debug_dv_struct_id = self._new_debug_id()
        self._debug_types['LightValue'] = self._debug_dv_struct_id
        # 内部类型 - i64
        self._debug_type_i64 = self._new_debug_id()
        self._emit_debug_metadata(f"!{self._debug_type_i64} = !DIBasicType(name: \"i64\", size: 64, align: 64, encoding: DW_ATE_unsigned)")
        # 内部类型 - i32
        self._debug_type_i32 = self._new_debug_id()
        self._emit_debug_metadata(f"!{self._debug_type_i32} = !DIBasicType(name: \"i32\", size: 32, align: 32, encoding: DW_ATE_unsigned)")
        # 内部类型 - double
        self._debug_type_double = self._new_debug_id()
        self._emit_debug_metadata(f"!{self._debug_type_double} = !DIBasicType(name: \"double\", size: 64, align: 64, encoding: DW_ATE_float)")
        # 指针类型
        self._debug_type_ptr = self._new_debug_id()
        self._emit_debug_metadata(f"!{self._debug_type_ptr} = !DIBasicType(name: \"ptr\", size: 64, align: 64)")
        # 结构体成员列表（LightValue 包含 i32, i64, double, ptr, i32, i32, i32, ptr）
        elements_id = self._new_debug_id()
        self._emit_debug_metadata(f"!{elements_id} = !{{!{self._debug_type_i32}, !{self._debug_type_i64}, !{self._debug_type_double}, !{self._debug_type_ptr}, !{self._debug_type_i32}, !{self._debug_type_i32}, !{self._debug_type_i32}, !{self._debug_type_ptr}}}")
        # DICompositeType 用于 LightValue 结构体
        self._emit_debug_metadata(f"!{self._debug_dv_struct_id} = !DICompositeType(tag: DW_TAG_structure_type, name: \"LightValue\", size: 384, align: 64, elements: !{elements_id})")

    def _gen_debug_compile_unit(self, source_file: str = ""):
        """生成调试编译单元信息（DICompileUnit + DIFile）"""
        if not self._debug:
            return
        self._debug_file_id = self._new_debug_id()
        self._debug_cu_id = self._new_debug_id()
        file_name = source_file or "input.light"
        self._emit_debug_metadata(f'!{self._debug_file_id} = !DIFile(filename: "{file_name}", directory: ".")')
        self._emit_debug_metadata(f'!{self._debug_cu_id} = distinct !DICompileUnit(language: DW_LANG_Python, file: !{self._debug_file_id}, producer: "光明编译器 v3", isOptimized: true, flags: "", runtimeVersion: 0, splitDebugInlining: false, emissionKind: FullDebug)')
        self._debug_scope_id = self._debug_cu_id

    def _gen_debug_function(self, name: str, line: int, param_names: List[str] = None):
        """生成函数调试信息（DISubprogram）

        调用后会切换当前调试作用域到该函数。
        """
        if not self._debug:
            return
        self._debug_func_id = self._new_debug_id()
        # 函数类型元数据（DISubroutineType）
        func_type_id = self._new_debug_id()
        # 返回类型列表（简化：返回 LightValue）
        ret_types_id = self._new_debug_id()
        self._emit_debug_metadata(f"!{ret_types_id} = !{{!{self._debug_dv_struct_id}}}")
        self._emit_debug_metadata(f"!{func_type_id} = !DISubroutineType(types: !{ret_types_id})")
        # 简化处理：使用 LightValue 作为所有参数和返回类型
        self._emit_debug_metadata(f'!{self._debug_func_id} = distinct !DISubprogram(name: "{name}", scope: !{self._debug_file_id}, file: !{self._debug_file_id}, line: {line}, type: !{func_type_id}, scopeLine: {line}, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !{self._debug_cu_id})')
        self._debug_scope_id = self._debug_func_id

    def _end_debug_function(self):
        """结束当前函数的调试作用域，恢复到编译单元作用域"""
        if self._debug:
            self._debug_scope_id = self._debug_cu_id

    def _emit_debug_metadata(self, line: str):
        """将调试元数据行收集到单独列表，在 finalize 时追加到 IR 末尾"""
        self._debug_metadata_lines.append(line)

    def _emit_r12c_string_helpers(self):
        """R12C（R11A-08）：一次性发射 .lstrip() / .每个单词首字母大写() 的
        IR 辅助函数。单遍状态机 + alloca 计数器（无 phi），libc isspace/
        isalpha/toupper/tolower/strlen/malloc（runtime 已链接 libc）。"""
        lv = LIGHTVALUE_STRUCT
        if self._r12c_need_lstrip:
            already = {l for l in self._lines if l.startswith('declare')}
            if 'declare i64 @strlen(ptr)' not in already:
                self.emit('declare i64 @strlen(ptr)')
            self.emit('declare i32 @isspace(i32)')
            self.emit('define internal void @_r12c_lstrip(ptr %result, ptr %str_ptr) {')
            self.emit('entry:')
            self.emit(f'  %sv = load {lv}, ptr %str_ptr')
            self.emit(f'  %s = extractvalue {lv} %sv, 3')
            self.emit('  %isnull = icmp eq ptr %s, null')
            self.emit('  %len0 = call i64 @strlen(ptr %s)')
            self.emit('  %len = select i1 %isnull, i64 0, i64 %len0')
            self.emit('  %out = call ptr @malloc(i64 %len)')
            self.emit('  %i_ptr = alloca i64')
            self._lines.append('  %w_ptr = alloca i64')
            self._lines.append('  store i64 0, ptr %i_ptr')
            self._lines.append('  store i64 0, ptr %w_ptr')
            self._lines.append('  br label %loop')
            self._lines.append('loop:')
            self._lines.append('  %i = load i64, ptr %i_ptr')
            self._lines.append('  %cont = icmp slt i64 %i, %len')
            self._lines.append('  br i1 %cont, label %body, label %done')
            self._lines.append('body:')
            self._lines.append('  %cp = getelementptr inbounds i8, ptr %s, i64 %i')
            self._lines.append('  %c = load i8, ptr %cp')
            self._lines.append('  %c32 = zext i8 %c to i32')
            self._lines.append('  %ws = call i32 @isspace(i32 %c32)')
            self._lines.append('  %is_ws = icmp ne i32 %ws, 0')
            self._lines.append('  br i1 %is_ws, label %skip, label %keep')
            self._lines.append('skip:')
            self._lines.append('  %ni = add i64 %i, 1')
            self._lines.append('  store i64 %ni, ptr %i_ptr')
            self._lines.append('  br label %loop')
            self._lines.append('keep:')
            self._lines.append('  %w = load i64, ptr %w_ptr')
            self._lines.append('  %op = getelementptr inbounds i8, ptr %out, i64 %w')
            self._lines.append('  store i8 %c, ptr %op')
            self._lines.append('  %nw = add i64 %w, 1')
            self._lines.append('  store i64 %nw, ptr %w_ptr')
            self._lines.append('  %ni2 = add i64 %i, 1')
            self._lines.append('  store i64 %ni2, ptr %i_ptr')
            self._lines.append('  br label %loop')
            self._lines.append('done:')
            self._lines.append('  %wf = load i64, ptr %w_ptr')
            self._lines.append('  %zp = getelementptr inbounds i8, ptr %out, i64 %wf')
            self._lines.append('  store i8 0, ptr %zp')
            self._lines.append(f'  %t_p = getelementptr inbounds {lv}, ptr %result, i32 0, i32 0')
            self._lines.append('  store i32 3, ptr %t_p')
            self._lines.append(f'  %i_p = getelementptr inbounds {lv}, ptr %result, i32 0, i32 1')
            self._lines.append('  store i64 0, ptr %i_p')
            self._lines.append(f'  %f_p = getelementptr inbounds {lv}, ptr %result, i32 0, i32 2')
            self._lines.append('  store double 0.0, ptr %f_p')
            self._lines.append(f'  %s_p = getelementptr inbounds {lv}, ptr %result, i32 0, i32 3')
            self._lines.append('  store ptr %out, ptr %s_p')
            self._lines.append(f'  %b_p = getelementptr inbounds {lv}, ptr %result, i32 0, i32 4')
            self._lines.append('  store i32 0, ptr %b_p')
            self._lines.append('  ret void')
            self._lines.append('}')
        if self._r12c_need_title:
            already = {l for l in self._lines if l.startswith('declare')}
            if 'declare i64 @strlen(ptr)' not in already:
                self.emit('declare i64 @strlen(ptr)')
            self.emit('declare i32 @isalpha(i32)')
            self.emit('declare i32 @toupper(i32)')
            self.emit('declare i32 @tolower(i32)')
            self.emit('define internal void @_r12c_title(ptr %result, ptr %str_ptr) {')
            self.emit('entry:')
            self.emit(f'  %sv = load {lv}, ptr %str_ptr')
            self.emit(f'  %s = extractvalue {lv} %sv, 3')
            self.emit('  %isnull = icmp eq ptr %s, null')
            self.emit('  %len0 = call i64 @strlen(ptr %s)')
            self.emit('  %len = select i1 %isnull, i64 0, i64 %len0')
            self.emit('  %out = call ptr @malloc(i64 %len)')
            self.emit('  %i_ptr = alloca i64')
            self._lines.append('  %w_ptr = alloca i64')
            self._lines.append('  %pa_ptr = alloca i8')
            self._lines.append('  store i64 0, ptr %i_ptr')
            self._lines.append('  store i64 0, ptr %w_ptr')
            self._lines.append('  store i8 0, ptr %pa_ptr')
            self._lines.append('  br label %loop')
            self._lines.append('loop:')
            self._lines.append('  %i = load i64, ptr %i_ptr')
            self._lines.append('  %cont = icmp slt i64 %i, %len')
            self._lines.append('  br i1 %cont, label %body, label %done')
            self._lines.append('body:')
            self._lines.append('  %cp = getelementptr inbounds i8, ptr %s, i64 %i')
            self._lines.append('  %c = load i8, ptr %cp')
            self._lines.append('  %c32 = zext i8 %c to i32')
            self._lines.append('  %a = call i32 @isalpha(i32 %c32)')
            self._lines.append('  %is_a = icmp ne i32 %a, 0')
            self._lines.append('  br i1 %is_a, label %alpha, label %other')
            self._lines.append('alpha:')
            self._lines.append('  %w1 = load i64, ptr %w_ptr')
            self._lines.append('  %op1 = getelementptr inbounds i8, ptr %out, i64 %w1')
            self._lines.append('  %pa = load i8, ptr %pa_ptr')
            self._lines.append('  %first = icmp eq i8 %pa, 0')
            self._lines.append('  %up = call i32 @toupper(i32 %c32)')
            self._lines.append('  %lo = call i32 @tolower(i32 %c32)')
            self._lines.append('  %sel = select i1 %first, i32 %up, i32 %lo')
            self._lines.append('  %ob = trunc i32 %sel to i8')
            self._lines.append('  store i8 %ob, ptr %op1')
            self._lines.append('  %nw1 = add i64 %w1, 1')
            self._lines.append('  store i64 %nw1, ptr %w_ptr')
            self._lines.append('  store i8 1, ptr %pa_ptr')
            self._lines.append('  br label %next')
            self._lines.append('other:')
            self._lines.append('  %w2 = load i64, ptr %w_ptr')
            self._lines.append('  %op2 = getelementptr inbounds i8, ptr %out, i64 %w2')
            self._lines.append('  store i8 %c, ptr %op2')
            self._lines.append('  %nw2 = add i64 %w2, 1')
            self._lines.append('  store i64 %nw2, ptr %w_ptr')
            self._lines.append('  store i8 0, ptr %pa_ptr')
            self._lines.append('  br label %next')
            self._lines.append('next:')
            self._lines.append('  %ni = add i64 %i, 1')
            self._lines.append('  store i64 %ni, ptr %i_ptr')
            self._lines.append('  br label %loop')
            self._lines.append('done:')
            self._lines.append('  %wf = load i64, ptr %w_ptr')
            self._lines.append('  %zp = getelementptr inbounds i8, ptr %out, i64 %wf')
            self._lines.append('  store i8 0, ptr %zp')
            self._lines.append(f'  %t_p = getelementptr inbounds {lv}, ptr %result, i32 0, i32 0')
            self._lines.append('  store i32 3, ptr %t_p')
            self._lines.append(f'  %i_p = getelementptr inbounds {lv}, ptr %result, i32 0, i32 1')
            self._lines.append('  store i64 0, ptr %i_p')
            self._lines.append(f'  %f_p = getelementptr inbounds {lv}, ptr %result, i32 0, i32 2')
            self._lines.append('  store double 0.0, ptr %f_p')
            self._lines.append(f'  %s_p = getelementptr inbounds {lv}, ptr %result, i32 0, i32 3')
            self._lines.append('  store ptr %out, ptr %s_p')
            self._lines.append(f'  %b_p = getelementptr inbounds {lv}, ptr %result, i32 0, i32 4')
            self._lines.append('  store i32 0, ptr %b_p')
            self._lines.append('  ret void')
            self._lines.append('}')
        if self._r12c_need_split_ws:
            already = {l for l in self._lines if l.startswith('declare')}
            if 'declare i64 @strlen(ptr)' not in already:
                self.emit('declare i64 @strlen(ptr)')
            if 'declare void @llvm.memcpy.p0.p0.i64(ptr, ptr, i64, i1, i1)' not in already:
                self.emit('declare void @llvm.memcpy.p0.p0.i64(ptr, ptr, i64, i1, i1)')
            self.emit('declare i32 @isspace(i32)')
            self.emit('define internal void @_r12c_split_ws(ptr %result, ptr %str_ptr) {')
            self.emit('entry:')
            self.emit(f'  %sv = load {lv}, ptr %str_ptr')
            self.emit(f'  %s = extractvalue {lv} %sv, 3')
            self.emit('  %isnull = icmp eq ptr %s, null')
            self.emit('  %len0 = call i64 @strlen(ptr %s)')
            self.emit('  %len = select i1 %isnull, i64 0, i64 %len0')
            self.emit('  %list_slot = alloca ' + lv)
            self.emit('  %elem = alloca ' + lv)
            self.emit('  %res2 = alloca ' + lv)
            self.emit('  %i_ptr = alloca i64')
            self.emit('  %start_ptr = alloca i64')
            self.emit('  store i64 0, ptr %i_ptr')
            self.emit('  store i64 0, ptr %start_ptr')
            self.emit('  call void @dv_list_new(ptr %list_slot)')
            self.emit('  br label %loop')
            self.emit('loop:')
            self.emit('  %i = load i64, ptr %i_ptr')
            self.emit('  %cont = icmp slt i64 %i, %len')
            self.emit('  br i1 %cont, label %body, label %tail')
            self.emit('body:')
            self.emit('  %cp = getelementptr inbounds i8, ptr %s, i64 %i')
            self._lines.append('  %c = load i8, ptr %cp')
            self._lines.append('  %c32 = zext i8 %c to i32')
            self._lines.append('  %ws = call i32 @isspace(i32 %c32)')
            self._lines.append('  %is_ws = icmp ne i32 %ws, 0')
            self._lines.append('  br i1 %is_ws, label %flush_a, label %keep')
            self._lines.append('flush_a:')
            self._lines.append('  %start1 = load i64, ptr %start_ptr')
            self._lines.append('  %plen1 = sub i64 %i, %start1')
            self._lines.append('  %cap1 = add i64 %plen1, 1')
            self._lines.append('  %buf1 = call ptr @malloc(i64 %cap1)')
            self._lines.append('  %sp1 = getelementptr inbounds i8, ptr %s, i64 %start1')
            self._lines.append('  call void @llvm.memcpy.p0.p0.i64(ptr %buf1, ptr %sp1, i64 %plen1, i1 false, i1 false)')
            self._lines.append('  %zp1 = getelementptr inbounds i8, ptr %buf1, i64 %plen1')
            self._lines.append('  store i8 0, ptr %zp1')
            self._lines.append('  call void @dv_str(ptr %elem, ptr %buf1)')
            self._lines.append('  call void @free(ptr %buf1)')
            self._lines.append('  %cur1 = load ' + lv + ', ptr %list_slot')
            self._lines.append('  call void @dv_list_append(ptr %res2, ptr %list_slot, ptr %elem)')
            self._lines.append('  %res1 = load ' + lv + ', ptr %res2')
            self._lines.append('  store ' + lv + ' %res1, ptr %list_slot')
            self._lines.append('  %ni1 = add i64 %i, 1')
            self._lines.append('  store i64 %ni1, ptr %i_ptr')
            self._lines.append('  store i64 %ni1, ptr %start_ptr')
            self._lines.append('  br label %loop')
            self._lines.append('keep:')
            self._lines.append('  %ni2 = add i64 %i, 1')
            self._lines.append('  store i64 %ni2, ptr %i_ptr')
            self._lines.append('  br label %loop')
            self._lines.append('tail:')
            self._lines.append('  %start2 = load i64, ptr %start_ptr')
            self._lines.append('  %plen2 = sub i64 %len, %start2')
            self._lines.append('  %cap2 = add i64 %plen2, 1')
            self._lines.append('  %buf2 = call ptr @malloc(i64 %cap2)')
            self._lines.append('  %sp2 = getelementptr inbounds i8, ptr %s, i64 %start2')
            self._lines.append('  call void @llvm.memcpy.p0.p0.i64(ptr %buf2, ptr %sp2, i64 %plen2, i1 false, i1 false)')
            self._lines.append('  %zp2 = getelementptr inbounds i8, ptr %buf2, i64 %plen2')
            self._lines.append('  store i8 0, ptr %zp2')
            self._lines.append('  call void @dv_str(ptr %elem, ptr %buf2)')
            self._lines.append('  call void @free(ptr %buf2)')
            self._lines.append('  %cur2 = load ' + lv + ', ptr %list_slot')
            self._lines.append('  call void @dv_list_append(ptr %res2, ptr %list_slot, ptr %elem)')
            self._lines.append('  %res2v = load ' + lv + ', ptr %res2')
            self._lines.append('  store ' + lv + ' %res2v, ptr %list_slot')
            self._lines.append('  %final = load ' + lv + ', ptr %list_slot')
            self._lines.append('  store ' + lv + ' %final, ptr %result')
            self._lines.append('  ret void')
            self._lines.append('}')


    def finalize(self) -> str:
        """覆写父类方法：在生成 IR 时追加调试元数据"""
        # R12C（R11A-08）：先发射本批按需的字符串辅助函数
        self._emit_r12c_string_helpers()
        # 先把调试元数据追加到 _lines 末尾

        if self._debug and self._debug_metadata_lines:
            self._lines.append('')
            self._lines.extend(self._debug_metadata_lines)
        return super().finalize()

    # ============================================================
    # 类型控制
    # ============================================================

    def _declare_typed_runtime(self):
        """声明类型版的运行时函数（所有 LightValue 通过 ptr 传递）"""
        funcs = [
            f'declare void @dv_int(ptr, i64)',
            f'declare void @dv_float(ptr, double)',
            f'declare void @dv_str(ptr, ptr)',
            f'declare void @dv_bool(ptr, i32)',
            f'declare void @dv_null(ptr)',
            f'declare i32 @dv_is_null(ptr)',
            f'declare void @dv_null_coalesce(ptr, ptr, ptr)',
            f'declare void @dv_safe_get(ptr, ptr, ptr)',
            f'declare void @dv_add(ptr, ptr, ptr)',
            f'declare void @dv_sub(ptr, ptr, ptr)',
            f'declare void @dv_mul(ptr, ptr, ptr)',
            f'declare void @dv_div(ptr, ptr, ptr)',
            f'declare i32 @dv_eq(ptr, ptr)',
            f'declare i32 @dv_lt(ptr, ptr)',
            f'declare i32 @dv_gt(ptr, ptr)',
            f'declare i32 @dv_le(ptr, ptr)',
            f'declare i32 @dv_ge(ptr, ptr)',
            f'declare void @dv_println(ptr)',
            f'declare void @dv_print(ptr)',
            f'declare void @dv_input(ptr)',
            f'declare void @dv_concat(ptr, ptr, ptr)',
            f'declare i64 @dv_str_len(ptr)',
            f'declare void @dv_str_get(ptr, ptr, i64)',
            f'declare void @dv_deref_value(ptr, ptr)',
            f'declare void @dv_list_new(ptr)',
            f'declare i64 @dv_list_len(ptr)',
            f'declare i64 @dv_len(ptr)',
            f'declare void @dv_ord(ptr, ptr)',
            f'declare void @dv_chr(ptr, ptr)',
            f'declare void @dv_hex(ptr, ptr)',
            f'declare void @dv_list_get(ptr, ptr, i64)',
            f'declare void @dv_list_append(ptr, ptr, ptr)',
            # 元组操作（R10-11a）
            f'declare void @dv_tuple_new(ptr)',
            f'declare void @dv_tuple_append(ptr, ptr, ptr)',
            f'declare void @dv_tuple_get(ptr, ptr, i64)',
            f'declare i64 @dv_tuple_len(ptr)',
            f'declare void @dv_list_insert(ptr, ptr, i64, ptr)',
            f'declare void @dv_list_remove(ptr, ptr, i64)',
            f'declare void @dv_list_pop(ptr, ptr, i64)',
            f'declare void @dv_list_set(ptr, ptr, i64, ptr)',
            f'declare i64 @dv_list_index_of(ptr, ptr)',
            f'declare i64 @dv_list_contains(ptr, ptr)',
            f'declare void @dv_list_reverse(ptr, ptr)',
            f'declare void @dv_list_sort(ptr, ptr)',
            f'declare void @dv_list_clear(ptr, ptr)',
            f'declare void @dv_sin(ptr, ptr)',
            f'declare void @dv_cos(ptr, ptr)',
            f'declare void @dv_sqrt(ptr, ptr)',
            f'declare void @dv_abs(ptr, ptr)',
            f'declare void @dv_pow(ptr, ptr, ptr)',
            f'declare void @dv_floor(ptr, ptr)',
            f'declare void @dv_ceil(ptr, ptr)',
            f'declare void @dv_mod(ptr, ptr, ptr)',
            # 数学扩展（第三批）
            f'declare void @dv_tan(ptr, ptr)',
            f'declare void @dv_asin(ptr, ptr)',
            f'declare void @dv_acos(ptr, ptr)',
            f'declare void @dv_atan(ptr, ptr)',
            f'declare void @dv_atan2(ptr, ptr, ptr)',
            f'declare void @dv_log(ptr, ptr)',
            f'declare void @dv_log2(ptr, ptr)',
            f'declare double @dv_random()',
            f'declare void @dv_random_seed(i64)',
            f'declare i64 @dv_random_bits(i64)',
            f'declare void @dv_log10(ptr, ptr)',
            f'declare void @dv_exp(ptr, ptr)',
            f'declare void @dv_round(ptr, ptr)',
            f'declare void @dv_trunc(ptr, ptr)',
            f'declare void @dv_sign(ptr, ptr)',
            f'declare void @dv_hypot(ptr, ptr, ptr)',
            f'declare void @dv_degrees(ptr, ptr)',
            f'declare void @dv_radians(ptr, ptr)',
            f'declare void @dv_min(ptr, ptr, ptr)',
            f'declare void @dv_max(ptr, ptr, ptr)',
            f'declare void @dv_gcd(ptr, ptr, ptr)',
            f'declare void @dv_lcm(ptr, ptr, ptr)',
            f'declare void @dv_substr(ptr, ptr, i64, i64)',
            f'declare i64 @dv_str_find(ptr, ptr)',
            f'declare i64 @dv_str_rfind(ptr, ptr)',
            f'declare void @dv_str_rstrip(ptr, ptr, ptr)',
            f'declare void @dv_upper(ptr, ptr)',
            f'declare void @dv_lower(ptr, ptr)',
            f'declare void @dv_trim(ptr, ptr)',
            f'declare void @dv_str_replace(ptr, ptr, ptr, ptr)',
            # 字符串扩展（第三批）
            f'declare void @dv_str_repeat(ptr, ptr, ptr)',
            f'declare i32 @dv_str_contains(ptr, ptr)',
            f'declare i32 @dv_str_starts_with(ptr, ptr)',
            f'declare i32 @dv_str_ends_with(ptr, ptr)',
            f'declare i64 @dv_str_count(ptr, ptr)',
            f'declare void @dv_str_rjust(ptr, ptr, ptr, ptr)',
            f'declare void @dv_str_ljust(ptr, ptr, ptr, ptr)',
            f'declare void @dv_str_center(ptr, ptr, ptr, ptr)',
            f'declare void @dv_str_reverse(ptr, ptr)',
            f'declare void @dv_str_split(ptr, ptr, ptr)',
            f'declare void @dv_path_join(ptr, ptr, ptr)',
            f'declare void @dv_path_dirname(ptr, ptr)',
            f'declare void @dv_path_basename(ptr, ptr)',
            f'declare void @dv_abspath(ptr, ptr)',
            f'declare void @dv_to_int(ptr, ptr)',
            f'declare void @dv_to_float(ptr, ptr)',
            f'declare void @dv_to_bool_val(ptr, ptr)',
            f'declare i32 @dv_to_bool(ptr)',
            f'declare double @dv_timestamp()',
            f'declare ptr @dv_format_time(double, ptr)',
            f'declare void @dv_sleep(double)',
            f'declare double @dv_clock()',
            f'declare i32 @dv_file_exists(ptr)',
            f'declare ptr @dv_read_file(ptr)',
            f'declare void @dv_write_file(ptr, ptr)',
            f'declare void @dv_append_file(ptr, ptr)',
            f'declare void @dv_open_file(ptr, ptr, ptr, ptr)',
            f'declare void @dv_file_write(ptr, ptr, ptr)',
            f'declare void @dv_file_close(ptr, ptr)',
            f'declare void @dv_file_read(ptr, ptr)',
            f'declare i64 @dv_file_size(ptr)',
            f'declare i32 @dv_delete_file(ptr)',
            f'declare void @dv_list_dir(ptr, ptr)',
            f'declare void @dv_foreach_get(ptr, ptr, i64)',
            # T7D：原生 LightValue 列表 join（取代 legacy dv_str_join：其按旧解释器
            # "list:..." 序列化串解析，codegen 传原生列表指针恒返空，见 T6A-04）
            f'declare void @dv_list_join(ptr, ptr, ptr)',
            f'declare ptr @dv_getenv(ptr)',
            f'declare i32 @dv_setenv(ptr, ptr)',
            f'declare ptr @dv_getcwd()',
            f'declare i32 @dv_chdir(ptr)',
            f'declare i32 @dv_system(ptr)',
            f'declare void @dv_exit(i32)',
            f'declare void @dv_init_args(i32, ptr)',
            f'declare void @dv_get_args(ptr)',
            f'declare void @dv_try_enter(ptr, ptr)',
            f'declare void @dv_try_end()',
            f'declare ptr @dv_try_push()',
            f'declare void @dv_try_pop()',
            f'declare void @dv_throw(ptr)',
            f'declare ptr @dv_get_exception_str()',
            f'declare void @dv_clear_exception()',
            f'declare void @dv_throw_exception(ptr)',
            f'declare void @dv_get_current_exception(ptr)',
            f'declare i32 @dv_exception_match(ptr, ptr)',
            f'declare void @dv_clear_exception_obj()',
            # 类系统
            f'declare void @dv_class_new(ptr, i32)',
            f'declare void @dv_class_set_member(ptr, ptr, ptr)',
            f'declare void @dv_class_get_member(ptr, ptr, ptr)',
            f'declare i32 @dv_register_class(ptr, ptr)',
            f'declare i32 @dv_register_method(ptr, ptr, ptr)',
            f'declare i32 @dv_register_attr(ptr, ptr)',
            # 接口系统（Level 7）
            f'declare i32 @dv_register_interface(ptr)',
            f'declare i32 @dv_register_interface_method(ptr, ptr, ptr)',
            f'declare i32 @dv_register_class_implements(ptr, ptr)',
            f'declare i32 @dv_class_implements_interface(ptr, ptr)',
            f'declare ptr @dv_find_method(ptr, ptr)',
            f'declare void @dv_class_new_named(ptr, ptr)',
            f'declare void @dv_get_class_name(ptr, ptr, i32)',
            f'declare void @dv_value_to_string(ptr, ptr)',
            f'declare void @dv_call_method(ptr, ptr, ptr, ptr, i32)',
            f'declare void @dv_call_super_method(ptr, ptr, ptr, ptr, ptr, i32)',
            f'declare i32 @dv_isinstance(ptr, ptr)',
            f'declare void @dv_get_type_name(ptr, ptr, i32)',
            f'declare i32 @dv_register_class_method(ptr, ptr, ptr)',
            f'declare i32 @dv_register_static_method(ptr, ptr, ptr)',
            f'declare void @dv_call_class_method(ptr, ptr, ptr, ptr, i32)',
            f'declare void @dv_call_static_method(ptr, ptr, ptr, ptr, i32)',
            f'declare void @dv_obj_release_slot(ptr)',
            f'declare void @dv_obj_deepcopy_self(ptr)',
            f'declare void @dv_value_disown(ptr)',
            # 接口 vtable 分发
            f'declare i32 @dv_call_interface_method(ptr, ptr, ptr, ptr, ptr, i32)',
            # 异常栈追踪
            f'declare void @dv_stack_push(ptr, ptr, i32)',
            f'declare void @dv_stack_pop()',
            f'declare void @dv_create_exception_with_cause(ptr, ptr, ptr, ptr)',
            f'declare i64 @dv_exception_to_full_string(ptr, ptr, i32)',
            # 字典操作
            f'declare void @dv_dict_new(ptr)',
            f'declare void @dv_dict_set(ptr, ptr, ptr, ptr)',
            # T7B / T5C-05 变参收集
            f'declare void @dv_collect_varargs(ptr, ptr, i64, i64)',
            f'declare void @dv_collect_kwargs(ptr, ptr, i64, i64)',
            # T7B / T5C-03 索引赋值（按运行时类型分派 list/dict）
            f'declare void @dv_index_set(ptr, ptr, ptr, ptr)',
            f'declare void @dv_dict_get(ptr, ptr, ptr)',
            # T7D：3 参 字典获取（带默认值，键缺失返回默认）
            f'declare void @dv_dict_get_def(ptr, ptr, ptr, ptr)',
            f'declare void @dv_dict_has(ptr, ptr, ptr)',
            f'declare void @dv_dict_keys(ptr, ptr)',
            f'declare void @dv_dict_remove(ptr, ptr, ptr)',
            f'declare void @dv_dict_values(ptr, ptr)',
            # 文件系统扩展
            f'declare i32 @dv_mkdir(ptr)',
            f'declare i32 @dv_rmdir(ptr)',
            f'declare i32 @dv_makedirs(ptr)',
            f'declare i32 @dv_rename_file(ptr, ptr)',
            f'declare i32 @dv_copy_file(ptr, ptr)',
            f'declare i32 @dv_is_file(ptr)',
            f'declare i32 @dv_is_dir(ptr)',
            # 哈希/编码
            f'declare ptr @dv_md5(ptr, i32)',
            f'declare ptr @dv_sha1(ptr, i32)',
            f'declare ptr @dv_sha256(ptr, i32)',
            # T7D：SHA512（C 层 64 位字实现，光明缺位移/按位运算符无法可靠模拟）
            f'declare ptr @dv_sha512(ptr, i32)',
            # T7D：HMAC_SHA256（对齐 哈希.py 的 pbkdf2_hmac('sha256', text, key, 1)）
            f'declare ptr @dv_pbkdf2_hmac_sha256_1(ptr, ptr)',
            f'declare ptr @dv_base64_encode(ptr, i32)',
            f'declare ptr @dv_base64_decode(ptr, ptr)',
            # 协程/异步
            f'declare ptr @dv_coro_create(ptr, ptr, i32, i32)',
            f'declare void @dv_coro_await(ptr, ptr)',
            f'declare void @dv_scheduler_run()',
            f'declare void @dv_coro_run_to_completion(ptr)',
            f'declare ptr @dv_coro_get_result(ptr)',
            f'declare i32 @dv_coro_is_done(ptr)',
            f'declare ptr @dv_future_create()',
            f'declare void @dv_future_complete(ptr, ptr)',
            f'declare ptr @dv_future_from_value(ptr)',
            f'declare void @dv_coro_get_await_result(ptr, ptr)',
            f'declare void @dv_coro_set_result(ptr, ptr)',
            f'declare ptr @dv_coro_get_local(ptr, i32)',
            f'declare ptr @dv_coro_get_arg(ptr, i32)',
            # ---- 生成器 (R10-11b 第四批B) ----
            # 与协程分属两套状态机：协程是推送式（调度器跑到完），
            # 生成器是拉取式（挂起在 `生成` 处把值交回消费者）。
            f'declare ptr @dv_gen_create(ptr, i32)',
            f'declare void @dv_gen_free(ptr)',
            f'declare ptr @dv_gen_slot(ptr, i32)',
            f'declare i32 @dv_gen_state(ptr)',
            f'declare void @dv_gen_yield(ptr, ptr, i32)',
            f'declare void @dv_gen_finish(ptr)',
            f'declare void @dv_gen_make(ptr, ptr)',
            f'declare i32 @dv_is_generator(ptr)',
            f'declare i32 @dv_gen_resume(ptr)',
            f'declare void @dv_gen_value(ptr, ptr)',
            # 网络/Socket (Task B1)
            f'declare i32 @dv_socket_create(i32, i32)',
            f'declare i32 @dv_socket_connect(i32, ptr, i32)',
            f'declare i32 @dv_socket_bind(i32, ptr, i32)',
            f'declare i32 @dv_socket_listen(i32, i32)',
            f'declare i32 @dv_socket_accept(i32)',
            f'declare i32 @dv_socket_send(i32, ptr)',
            f'declare void @dv_socket_recv(ptr, i32, i32)',
            f'declare i32 @dv_socket_close(i32)',
            f'declare i32 @dv_socket_shutdown(i32, i32)',
            f'declare i32 @dv_socket_set_nonblocking(i32, i32)',
            f'declare ptr @dv_socket_last_error()',
            f'declare i32 @dv_socket_last_error_code()',
            f'declare ptr @dv_socket_get_peer_addr(i32)',
            # IO 多路复用 (Task B2)
            f'declare ptr @dv_poller_create()',
            f'declare i32 @dv_poller_register(ptr, i32, i32)',
            f'declare i32 @dv_poller_unregister(ptr, i32)',
            f'declare i32 @dv_poller_wait(ptr, i32, ptr, ptr)',
            f'declare void @dv_poller_destroy(ptr)',
            # 事件循环 (Task B3)
            f'declare void @dv_coro_await_io(ptr, i32, i32)',
            f'declare void @dv_coro_sleep(ptr, i32)',
            # ---- 原生 TLS (Task B2-4) ----
            f'declare ptr @dv_tls_wrap(i32, ptr)',
            f'declare i32 @dv_tls_handshake(ptr)',
            f'declare i32 @dv_tls_send(ptr, ptr)',
            f'declare i32 @dv_tls_send_n(ptr, ptr, i32)',
            f'declare void @dv_tls_recv(ptr, ptr, i32)',
            f'declare i32 @dv_tls_recv_status(ptr)',
            f'declare void @dv_tls_free(ptr)',
            f'declare i32 @dv_tls_set_verify(ptr, i32)',
            f'declare i32 @dv_tls_add_trusted_cert_file(ptr)',
            f'declare i32 @dv_tls_want_event(ptr)',
            f'declare i32 @dv_tls_is_ready(ptr)',
            f'declare i32 @dv_tls_flush_public(ptr)',
            f'declare ptr @dv_tls_last_error()',
            f'declare ptr @dv_poller_last_error()',
            f'declare ptr @dv_poller_backend()',
            f'declare i32 @dv_poller_count(ptr)',
            f'declare void @dv_scheduler_run_event_loop()',
            f'declare void @dv_platform_sleep(i32)',
        ]
        for f in funcs:
            self._func_decls.add(f)

        # setjmp 声明：平台相关
        if self.is_windows:
            # Windows x64: _setjmp 需两个参数（jmp_buf + frameaddress）
            self._func_decls.add(f'declare i32 @_setjmp(ptr, ptr)')
        else:
            # Linux / macOS: 标准 setjmp 只需一个参数（jmp_buf）
            self._func_decls.add(f'declare i32 @setjmp(ptr)')

    # ============================================================
    # LightValue 堆栈操作
    # ============================================================

    def _begin_temp_slot_pool(self):
        """在当前位置放下临时槽位池的**占位** alloca，并记住它的行号。

        为什么要延迟填数：`alloca {LIGHTVALUE_STRUCT}, i32 2048` 是发射时就写死的，
        LIGHTVALUE_STRUCT 对齐后 48 字节，48 x 2048 ≈ 96KB/帧——递归稍深就爆栈
        （Windows 默认 1MB 栈只够约 10 层）。而"这个函数到底用了几个临时槽位"要等
        函数体全部发射完才知道（就是 self._temp_slot_index 的终值）。
        所以先发一行占位、把 self._lines 的下标记进 self._temp_slot_pool_line，
        函数体收尾时由 self._emit_temp_slot_pool() 用真实用量回填。

        占位行本身写成合法的 `i32 1`：万一回填没跑到（异常等），产出的仍是合法 IR
        而不是语法垃圾。
        """
        self._temp_slot_pool = self.new_register()
        self._temp_slot_pool_line = len(self._lines)
        self.emit(f'{self._temp_slot_pool} = alloca {LIGHTVALUE_STRUCT}, i32 1'
                  f'  ; 占位：真实槽位数由 _emit_temp_slot_pool() 回填')

    def _emit_temp_slot_pool(self):
        """用本函数真实用到的槽位数回填临时槽位池的 alloca 行。

        必须在函数体（含所有 _new_dv_slot 调用）发射完毕、`}` 之前调用。
        """
        if self._temp_slot_pool_line is None or self._temp_slot_pool is None:
            return
        idx = self._temp_slot_pool_line
        self._temp_slot_pool_line = None
        if not (0 <= idx < len(self._lines)):
            return
        # 一个槽位都没用也要留 1 个：alloca 的元素个数为 0 虽然合法，但没必要
        # 让下游工具面对零长数组
        真实用量 = max(self._temp_slot_index, 1)
        self._lines[idx] = f'{self._temp_slot_pool} = alloca {LIGHTVALUE_STRUCT}, i32 {真实用量}'

    def _new_dv_slot(self) -> str:
        # R10-11b：生成器内改走堆槽数组（跨 `生成` 存活），槽指针落在 entry 块。
        if self._gen_entry_insert_idx is not None:
            return self._gen_new_slot()

        """从临时槽位池中分配一个新的 LightValue 槽位（避免动态 alloca 导致栈溢出）"""
        if self._temp_slot_pool is None:
            reg = self.new_register()
            self.emit(f'{reg} = alloca {LIGHTVALUE_STRUCT}')
            return reg
        
        if self._temp_slot_index >= self._temp_slot_pool_size:
            # R12C（R11C-1）：不再硬性拒绝。alloca 行由 _emit_temp_slot_pool
            # 按 _temp_slot_index 真实用量回填（占位行只是容器），大型列表
            # 字面量（如行政区划 3000+ 元素）初始化需要海量临时槽位，
            # 这里动态抬高水位即可。
            self._temp_slot_pool_size = self._temp_slot_index + 1024
        
        idx = self._temp_slot_index
        self._temp_slot_index += 1
        reg = self.new_register()
        self.emit(f'{reg} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {self._temp_slot_pool}, i64 {idx}')
        return reg

    def _set_type(self, slot: str, type_val: int):
        """设置 LightValue 槽位的 type 字段"""
        ptr = self.new_register()
        self.emit(f'{ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 0')
        self.emit(f'store i32 {type_val}, ptr {ptr}')

    def _set_i64(self, slot: str, i64_val: str):
        """设置 LightValue 槽位的 i64 字段"""
        ptr = self.new_register()
        self.emit(f'{ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 1')
        self.emit(f'store i64 {i64_val}, ptr {ptr}')

    def _set_f64(self, slot: str, f64_val: str):
        """设置 LightValue 槽位的 f64 字段"""
        ptr = self.new_register()
        self.emit(f'{ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 2')
        self.emit(f'store double {f64_val}, ptr {ptr}')

    def _set_str(self, slot: str, str_val: str):
        """设置 LightValue 槽位的 str 字段"""
        ptr = self.new_register()
        self.emit(f'{ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 3')
        self.emit(f'store ptr {str_val}, ptr {ptr}')

    def _load_dv(self, slot: str) -> str:
        """加载整个 LightValue 作为 SSA 值"""
        reg = self.new_register()
        self.emit(f'{reg} = load {LIGHTVALUE_STRUCT}, ptr {slot}')
        return reg

    def _self_lvalue_slot(self) -> str:
        """返回 己/self 的 LightValue 槽位指针（lvalue），绝不复制。

        字段写回（己.X 为 … / self.X 为 …）必须就地修改「接收者」自身的
        LightValue，而不是一份副本：原生对象的可变状态（obj->str 序列化缓冲）
        以指针形式内嵌在 LightValue 中，dv_class_set_member 会 free+realloc 该
        缓冲。若先 _store_dv(get_var('己')) 复制出一份共享同缓冲的 LightValue，
        对副本的 set_member 会释放掉原 self 参数仍指向的缓冲，造成
        use-after-free（P0-2 SSE 原生崩溃根因）。故此helper直接返回 己/self
        的真实槽位指针（参数槽或局部 alloca 槽），确保修改落在接收者本体上。
        """
        p = self._current_func_params.get('己') or self._current_func_params.get('self')
        if p is not None:
            return p
        slot = self._local_vars.get('己')
        if slot is not None:
            return slot
        # 兜底：尝试普通变量查找（参数情形 get_var 已返回槽位指针）
        return self.get_var('己')

    def _store_dv(self, dv_reg: str) -> str:
        """将 LightValue SSA 寄存器存入槽位，返回槽位指针"""
        if dv_reg in self._dv_ssa_to_slot:
            return self._dv_ssa_to_slot[dv_reg]
        slot = self._new_dv_slot()
        self.emit(f'store {LIGHTVALUE_STRUCT} {dv_reg}, ptr {slot}')
        self._dv_ssa_to_slot[dv_reg] = slot
        return slot

    def _create_int_dv(self, i64_str: str) -> str:
        """创建整数 LightValue 并返回 SSA 值"""
        slot = self._new_dv_slot()
        self.emit(f'call void @dv_int(ptr {slot}, i64 {i64_str})')
        return self._load_dv(slot)

    def _create_str_dv(self, ptr_val: str) -> str:
        """创建字符串 LightValue 并返回 SSA 值"""
        slot = self._new_dv_slot()
        self.emit(f'call void @dv_str(ptr {slot}, ptr {ptr_val})')
        return self._load_dv(slot)

    def _create_bool_dv(self, i1_val: str) -> str:
        """根据 i1 条件创建布尔 LightValue"""
        slot = self._new_dv_slot()
        ext = self.new_register()
        self.emit(f'{ext} = zext i1 {i1_val} to i32')
        self.emit(f'call void @dv_bool(ptr {slot}, i32 {ext})')
        return self._load_dv(slot)

    def _call_dv_func(self, func_name: str, *args: str) -> str:
        """调用通过 ptr 输出 LightValue 的运行时函数"""
        result_slot = self._new_dv_slot()
        # P0-2 内存安全修复：result_slot 来自复用型临时槽位池（_new_dv_slot 不零初始化），
        # 若直接传给会 dv_deref(result) 的运行时函数（如 dv_list_append），残留垃圾可能
        # 被误判为 type=8 REF 并跟随到坏指针 → ASan access-violation 0x3。新分配的槽位
        # 本就不可能是合法 REF，先零初始化为 NULL 才是正确默认值，不影响任何输出语义。
        self.emit(f'call void @dv_null(ptr {result_slot})')
        call_args = [f'ptr {result_slot}']
        for a in args:
            if ' ' in a:
                # 已有类型注释（如 'double %dbl', 'i64 %idx'），直接传递
                call_args.append(a)
            else:
                # LightValue SSA 寄存器 → 存入槽位后传 ptr
                # 优化：如果 SSA 值刚从 slot 加载，直接用原 slot
                slot = self._store_dv(a)
                call_args.append(f'ptr {slot}')
        self.emit(f'call void @{func_name}({", ".join(call_args)})')
        return self._load_dv(result_slot)

    # ============================================================
    # 类型推断与优化（Level 8）
    # ============================================================

    def _get_var_type(self, name: str) -> Optional[str]:
        """获取变量的已知类型（INT/FLOAT/BOOL/STRING/LIST/None）"""
        return self._var_types.get(name)

    def _set_var_type(self, name: str, type_: Optional[str]):
        """设置变量的类型"""
        self._var_types[name] = type_

    def _infer_expr_type(self, expr) -> Optional[str]:
        """推断表达式的类型（基于 AST 节点）"""
        if isinstance(expr, ast.NumberLiteral):
            val = str(expr.value)
            if '.' in val or 'e' in val.lower():
                return 'FLOAT'
            return 'INT'
        elif isinstance(expr, ast.StringLiteral):
            return 'STRING'
        elif isinstance(expr, ast.BooleanLiteral):
            return 'BOOL'
        elif isinstance(expr, ast.NullLiteral):
            return None
        elif isinstance(expr, ast.ListLiteral):
            return 'LIST'
        elif isinstance(expr, ast.Identifier):
            if expr.name in ('True', 'False'):
                return 'BOOL'
            if expr.name == 'None':
                return None
            return self._get_var_type(expr.name)
        elif isinstance(expr, ast.BinaryOp):
            left_type = self._infer_expr_type(expr.left)
            right_type = self._infer_expr_type(expr.right)
            op = expr.operator
            if op in ('+', '-', '*', '/', '%', '**', '加', '减', '乘', '除', '模', '幂'):
                # T5C 修复：任一侧静态类型未知（builtin 返回值、函数参数）时
                # 不得推断 FLOAT，否则快路径会误取浮点 DV 的 i64 字段（恒 0）。
                if (left_type in ('FLOAT', 'INT') and right_type in ('FLOAT', 'INT')):
                    if left_type == 'FLOAT' or right_type == 'FLOAT':
                        return 'FLOAT'
                    if op in ('/', '除'):
                        return 'FLOAT'
                    return 'INT'
                return None
            if op in ('==', '等于', '!=', '不等于', '<', '小于', '>', '大于',
                     '<=', '小于等于', '>=', '大于等于'):
                return 'BOOL'
            if op in ('and', 'or', '且', '与', '或'):
                return 'BOOL'
            return None
        return None

    def _extract_i64(self, dv_reg: str) -> str:
        """从 LightValue 中提取 i64 值"""
        reg = self.new_register()
        self.emit(f'{reg} = extractvalue {LIGHTVALUE_STRUCT} {dv_reg}, 1')
        return reg

    def _extract_f64(self, dv_reg: str) -> str:
        """从 LightValue 中提取 double 值"""
        reg = self.new_register()
        self.emit(f'{reg} = extractvalue {LIGHTVALUE_STRUCT} {dv_reg}, 2')
        return reg

    def _extract_bool(self, dv_reg: str) -> str:
        """从 LightValue 中提取 bool 值（返回 i1）"""
        i32_reg = self.new_register()
        self.emit(f'{i32_reg} = extractvalue {LIGHTVALUE_STRUCT} {dv_reg}, 4')
        i1_reg = self.new_register()
        self.emit(f'{i1_reg} = trunc i32 {i32_reg} to i1')
        return i1_reg

    def _create_int_dv_fast(self, i64_reg: str) -> str:
        """快速创建 INT 类型 LightValue（直接构造结构体）"""
        slot = self._new_dv_slot()
        type_ptr = self.new_register()
        self.emit(f'{type_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 0')
        self.emit(f'store i32 1, ptr {type_ptr}')
        i64_ptr = self.new_register()
        self.emit(f'{i64_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 1')
        self.emit(f'store i64 {i64_reg}, ptr {i64_ptr}')
        return self._load_dv(slot)

    def _create_float_dv_fast(self, f64_reg: str) -> str:
        """快速创建 FLOAT 类型 LightValue（直接构造结构体）"""
        slot = self._new_dv_slot()
        type_ptr = self.new_register()
        self.emit(f'{type_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 0')
        self.emit(f'store i32 2, ptr {type_ptr}')
        f64_ptr = self.new_register()
        self.emit(f'{f64_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 2')
        self.emit(f'store double {f64_reg}, ptr {f64_ptr}')
        return self._load_dv(slot)

    # ============================================================
    # 覆盖父类的表达式/语句生成
    # ============================================================

    def generate(self, module: ast.Module) -> str:
        self.declare_runtime()
        self._declare_typed_runtime()

        # 初始化调试信息（DWARF）
        if self._debug:
            self._gen_debug_compile_unit()
            self._gen_debug_types()

        # Level 9: 处理导入语句
        self._process_imports(module)

        for stmt in module.statements:
            if isinstance(stmt, ast.ImportStatement):
                continue
            self._collect_statement(stmt)
        if hasattr(module, 'classes'):
            for cls_def in module.classes:
                self._collect_class(cls_def)
        # 收集接口定义（Level 7）
        if hasattr(module, 'interfaces'):
            for iface_def in module.interfaces:
                self._collect_interface(iface_def)
        for seg in module.segments:
            self._collect_segment(seg)

        # 生成导入的外部段函数声明
        self._emit_module_decls()

        self._gen_global_init()
        for cls_name, cls_def in self._classes.items():
            self._gen_typed_class_methods(cls_name, cls_def)
        for reg_key in self._segment_order:
            seg_name = self._seg_raw_name(reg_key)
            mod_name = self._seg_module_name(reg_key)
            params = self._segments[reg_key]
            body = self._segment_bodies.get(reg_key, [])
            modifiers = self._segment_modifiers.get(reg_key, [])
            self._gen_typed_segment(seg_name, params, body, modifiers, mod_name)

        # Level 9: 为导出的段函数生成模块前缀别名
        self._gen_exported_aliases(module)

        self._gen_typed_main()
        ir = self.finalize()
        self._verify_ir(ir)
        return ir

    def _verify_ir(self, ir):
        """在 finalize 后验证生成的 IR 结构正确性"""
        errors = self._verify_module_ir(self._lines)
        if errors:
            error_msg = '\n'.join(f"  - {e}" for e in errors)
            raise RuntimeError(f"LLVM IR 验证失败，发现 {len(errors)} 个问题:\n{error_msg}")

    def _resolve_import_chain(self, module_name, orig_name, _seen=None):
        """R12C（R11A-05）：沿「导入→再导出」链解析段的最终定义模块。

        「导入即再导出」（B: 从 A 导入 f + 导出 f）的段定义注册在 A 名下，
        调用方按 B 的名义查找会落空。此函数跟随 B 的导入映射直到找到
        真正定义；找不到返回 None。_seen 防循环。
        """
        seen = _seen if _seen is not None else set()
        key = (module_name, orig_name)
        if key in seen:
            return None
        seen.add(key)
        if self._seg_reg_key(orig_name, module_name) in self._segments:
            return module_name, orig_name
        mod_imp = self._module_imports.get(module_name) or {}
        if orig_name in mod_imp:
            nxt_mod, nxt_name = mod_imp[orig_name]
            return self._resolve_import_chain(nxt_mod, nxt_name, seen)
        return None

    def _process_imports(self, module: ast.Module):
        """处理模块导入语句，记录导入的符号"""
        imports = getattr(module, 'imports', None) or []
        mod_name = getattr(module, 'name', None)
        for imp in imports:
            if isinstance(imp, ast.ImportStatement):
                module_name = imp.module
                self._imported_modules.add(module_name)
                if imp.names:
                    for name in imp.names:
                        self._imports[name] = (module_name, name)
                        # R12C（R11A-05）：按模块记录导入映射，供再导出链解析
                        if mod_name:
                            self._module_imports.setdefault(mod_name, {})[name] = (
                                module_name, name)
                        # 生成外部段函数声明
                        safe_name = self._safe_func_name(f'{module_name}_{name}')
                        if safe_name not in self._module_decls:
                            self._module_decls.append(safe_name)

    def _emit_module_decls(self):
        """生成导入的外部段函数声明"""
        for decl_name in self._module_decls:
            self.emit(f'declare void @_seg_{decl_name}(ptr, ptr, i32)')

    def _gen_exported_aliases(self, module: ast.Module):
        """为当前模块导出的段函数生成带模块前缀的别名"""
        module_name = getattr(module, 'name', None)
        if not module_name:
            return
        exports = getattr(module, 'exports', None) or []
        exported_names = set()
        for exp in exports:
            if isinstance(exp, ast.ExportStatement):
                # 优先使用 names 列表
                if exp.names:
                    exported_names.update(exp.names)
                elif exp.name:
                    exported_names.add(exp.name)
        # 如果没有显式导出，导出所有段函数
        if not exported_names:
            for reg_key in self._segment_order:
                # T9A：只导出本模块的段（reg_key 的模块名匹配当前模块）
                if self._seg_module_name(reg_key) == module_name:
                    exported_names.add(self._seg_raw_name(reg_key))
        for seg_name in exported_names:
            reg_key = self._seg_reg_key(seg_name, module_name)
            if reg_key in self._segments:
                # T9A：定义端 safe name 按模块隔离
                safe = self._safe_func_name(seg_name, module_name)
                alias_name = self._safe_func_name(f'{module_name}_{seg_name}')
                if alias_name != safe:
                    self.emit(f'@_seg_{alias_name} = alias void (ptr, ptr, i32), void (ptr, ptr, i32)* @_seg_{safe}')

    def _is_imported_symbol(self, name: str) -> bool:
        """检查符号是否来自导入的模块"""
        return name in self._imports

    # ============================================================
    # 重写表达式生成：使用 LightValue
    # ============================================================

    def _gen_expression(self, expr) -> Tuple[str, str]:
        """生成表达式，返回 (LightValue_SSA, 'dv')"""
        if expr is None:
            return self._create_int_dv('0'), 'dv'

        # C3-1：适配层把未知节点包成 ExpressionStatement(Identifier("<unknown:XXX>"))，
        # 不管它出现在语句位还是表达式位。语句位由 _gen_statement 拆，这里拆表达式位——
        # 先剥掉 ExpressionStatement 外壳，让下面的 Identifier 前缀检查接得住。
        if isinstance(expr, ast.ExpressionStatement):
            return self._gen_expression(expr.expression)

        if isinstance(expr, ast.NumberLiteral):
            val = expr.value
            if isinstance(val, int) or (isinstance(val, str) and val.isdigit()):
                return self._create_int_dv(str(val)), 'dv'
            return self._call_dv_func('dv_float', f'double {val}'), 'dv'

        if isinstance(expr, ast.StringLiteral):
            s_reg = self.gen_string_constant(expr.value)
            return self._create_str_dv(s_reg), 'dv'

        if isinstance(expr, ast.BooleanLiteral):
            val_i1 = '1' if expr.value else '0'
            return self._create_bool_dv(val_i1), 'dv'

        if isinstance(expr, ast.NullLiteral):
            return self._call_dv_func('dv_null'), 'dv'

        if isinstance(expr, ast.Identifier):
            # C3-1：适配层也会把未知表达式节点包成 Identifier("<unknown:XXX>")。
            # 必须先拆开报原 v3 类型名，否则会报成「未定义变量 <unknown:DictLiteral>」，
            # 把线索藏起来。
            if isinstance(expr.name, str) and expr.name.startswith(self._ADAPTER_UNKNOWN_PREFIX):
                inner = expr.name[len(self._ADAPTER_UNKNOWN_PREFIX):].rstrip('>')
                self._reject_unsupported_expr(inner, expr)
            return self._gen_typed_identifier(expr)

        if isinstance(expr, ast.BinaryOp):
            return self._gen_typed_binary_op(expr)

        if isinstance(expr, ast.UnaryOp):
            return self._gen_typed_unary_op(expr)

        if isinstance(expr, ast.FunctionCall):
            return self._gen_typed_function_call(expr)

        if hasattr(ast, 'ParagraphCall') and isinstance(expr, ast.ParagraphCall):
            args = [self._gen_expression(arg)[0] for arg in expr.args]
            builtin = self._gen_typed_builtin(expr.name, args)
            if builtin is not None:
                return builtin
            if self._local_seg_key(expr.name) in self._segments:
                # 名字已定义，却走不到正常返回——说明是类型推断问题，不是名字问题。
                try:
                    return self._gen_typed_segment_call(expr.name, args, expr.args)
                except NotImplementedError:
                    raise
                except Exception as e:
                    raise NotImplementedError(
                        f"段落「{expr.name}」的调用类型推断失败"
                        f"（源码行 {self._stmt_source_line(expr)}）：{e}。"
                        f"名字已定义，问题在类型上。{self._FALLBACK_HINT}"
                    ) from e
            # T9A 防御性补全：导入段查找（与 FunctionCall 路径对齐：本地段→导入段→builtin）
            if expr.name in self._imports:
                _imp_mod, _imp_orig = self._imports[expr.name]
                if (self._seg_reg_key(_imp_orig, _imp_mod) in self._segments
                        or self._resolve_import_chain(_imp_mod, _imp_orig)):
                    return self._gen_imported_segment_call(expr.name, args, expr.args)
            # C3-1：拼错名字的段落调用，报错并列出已定义候选。
            self._reject_unknown_call(expr.name, expr)

        if isinstance(expr, ast.IndexAccess):
            return self._gen_typed_index_access(expr)

        if isinstance(expr, ast.ListLiteral):
            return self._gen_typed_list_literal(expr)

        if isinstance(expr, ast.TupleLiteral):
            return self._gen_typed_tuple_literal(expr)

        if isinstance(expr, ast.DictLiteral):
            return self._gen_typed_dict_literal(expr)

        if isinstance(expr, ast.StringInterpolation):
            return self._gen_typed_string_interpolation(expr)

        if isinstance(expr, ast.ConditionalExpression):
            return self._gen_typed_conditional(expr)

        if isinstance(expr, ast.PropertyAccess):
            return self._gen_typed_property_access(expr)

        if hasattr(ast, 'ClassInstantiation') and isinstance(expr, ast.ClassInstantiation):
            return self._gen_typed_class_instantiation(expr)

        if hasattr(ast, 'NewExpression') and isinstance(expr, ast.NewExpression):
            return self._gen_typed_class_instantiation(expr)
        
        # 异步：等待表达式
        if hasattr(ast, 'AwaitExpression') and isinstance(expr, ast.AwaitExpression):
            return self._gen_await_expression(expr)

        # A9-S2：列表推导 [表达式 遍历 变量 之 列表 若 条件]
        if isinstance(expr, ast.ListComprehension):
            return self._gen_typed_list_comprehension(expr)

        # C3-1：表达式层链尾兜底。以前这里把一切未支持表达式静默编成整数 0——
        # 字典字面量 / Lambda / 推导式 / 切片 / UnwrapExpression / Pipeline 全是
        # 「编译成功、产物行为错误」。现在与语句层同一口径：响亮报错。
        self._reject_unsupported_expr(type(expr).__name__, expr)

    def _gen_typed_identifier(self, expr: ast.Identifier) -> Tuple[str, str]:
        name = expr.name
        var = self.get_var(name)
        if var is not None:
            return var, 'dv'

        # 解析器将 真/假/空 转为 Identifier('True'/'False'/'None')，需映射回布尔/空值
        if name == 'True':
            return self._create_bool_dv('1'), 'dv'
        if name == 'False':
            return self._create_bool_dv('0'), 'dv'
        if name == 'None':
            return self._call_dv_func('dv_null'), 'dv'

        # 方法内部：裸 self / 己 标识符 = 当前对象。
        # 解析器会把源码里的「己」转成 Identifier('self')，而方法内 self 槽位键是「己」，
        # 不做这层映射会一路落到「当作字符串常量」，dv_class_get_member/set_member 拿到
        # 一个字符串对象，属性读写直接崩。
        if self._method_result_ptr is not None:
            self_dv = self.get_var('己')
            if self_dv is not None and (name == 'self' or name == '己'):
                return self_dv, 'dv'

        # 方法内部：以"self."开头的标识符视为 self 的属性访问
        if self._method_result_ptr is not None and name.startswith('self.') and len(name) > 5:
            attr_name = name[5:]
            self_dv = self.get_var('己')
            if self_dv is not None:
                obj_slot = self._self_lvalue_slot()
                member_reg = self.gen_string_constant(attr_name)
                result_slot = self._new_dv_slot()
                self.emit(f'call void @dv_class_get_member(ptr {result_slot}, ptr {obj_slot}, ptr {member_reg})')
                return self._load_dv(result_slot), 'dv'
        
        # 方法内部：以"己"开头的标识符视为 self 的属性访问
        if self._method_result_ptr is not None and name.startswith('己') and len(name) > 1:
            attr_name = name[1:]
            self_dv = self.get_var('己')
            if self_dv is not None:
                obj_slot = self._self_lvalue_slot()
                member_reg = self.gen_string_constant(attr_name)
                result_slot = self._new_dv_slot()
                self.emit(f'call void @dv_class_get_member(ptr {result_slot}, ptr {obj_slot}, ptr {member_reg})')
                return self._load_dv(result_slot), 'dv'
        
        # 内置函数名当作字符串
        str_reg = self.gen_string_constant(name)
        return self._create_str_dv(str_reg), 'dv'

    def _gen_short_circuit_logic(self, expr: ast.BinaryOp, op: str) -> Tuple[str, str]:
        """R12A（R11A-07）：且/或 短路求值。

        结果用 i8 槽：默认存左值，右臂块内覆盖为右值。and → 左真才进右臂
        （结果=右真值，左假时结果=0=左）；or → 左假才进右臂（左真时结果=1=左）。
        右臂嵌套 且/或 时各自再建块，天然支持复合内联条件。
        """
        left_dv, _ = self._gen_expression(expr.left)
        left_i1 = self._gen_condition_i1(expr.left, left_dv)
        rhs_lab = self.new_label('sc_rhs')
        end_lab = self.new_label('sc_end')
        res_slot = self.new_register()
        self.emit(f'{res_slot} = alloca i8')
        lv = self.new_register()
        self.emit(f'{lv} = zext i1 {left_i1} to i8')
        self.emit(f'store i8 {lv}, ptr {res_slot}')
        if op in ('and', '且', '与'):
            self.emit(f'br i1 {left_i1}, label %{rhs_lab}, label %{end_lab}')
        else:
            self.emit(f'br i1 {left_i1}, label %{end_lab}, label %{rhs_lab}')
        self.emit(f'{rhs_lab}:')
        right_dv, _ = self._gen_expression(expr.right)
        right_i1 = self._gen_condition_i1(expr.right, right_dv)
        rv = self.new_register()
        self.emit(f'{rv} = zext i1 {right_i1} to i8')
        self.emit(f'store i8 {rv}, ptr {res_slot}')
        self.emit(f'br label %{end_lab}')
        self.emit(f'{end_lab}:')
        b8 = self.new_register()
        self.emit(f'{b8} = load i8, ptr {res_slot}')
        res_i1 = self.new_register()
        self.emit(f'{res_i1} = trunc i8 {b8} to i1')
        return self._create_bool_dv(res_i1), 'dv'

    def _gen_typed_binary_op(self, expr: ast.BinaryOp) -> Tuple[str, str]:
        op = expr.operator
        # R12A（R11A-07）：且/或 短路求值。必须在此提前分派——若先走下方
        # 双侧统一求值（left_dv/right_dv），右侧会在进入逻辑前被执行，
        # 「假 且 报错()」会求值报错()。短路专用路径：and 左假直接假、
        # or 左真直接真，右侧仅在 rhs 块内求值（Python and/or 同语义）。
        if op in ('and', 'or', '且', '与', '或'):
            return self._gen_short_circuit_logic(expr, op)
        left_dv, _ = self._gen_expression(expr.left)
        right_dv, _ = self._gen_expression(expr.right)

        left_type = self._infer_expr_type(expr.left)
        right_type = self._infer_expr_type(expr.right)

        arith_ops = {
            '+': ('add', 'fadd'), '-': ('sub', 'fsub'),
            '*': ('mul', 'fmul'), '/': ('sdiv', 'fdiv'),
            '%': ('srem', 'frem'),
            '加': ('add', 'fadd'), '减': ('sub', 'fsub'),
            '乘': ('mul', 'fmul'), '除': ('sdiv', 'fdiv'),
            '模': ('srem', 'frem'),
            # C3-1：`整除`（//）。parser 已把 `整除` 归一成 '//'，改动前它不是任何
            # 映射的键，一路静默走链尾 dv_add——`7 整除 2` 算出 9。双整数的类型
            # 优化路径用 sdiv（截断整除，与 runtime dv_div 双整数分支一致）；
            # 通用路径走 dv_div（双整数时也整除）。
            '//': ('sdiv', 'fdiv'),
        }

        if op in arith_ops:
            if self._enable_type_opt and left_type == 'INT' and right_type == 'INT':
                # T7A 修复：`/`（除）在 _infer_expr_type 中推断为 FLOAT，
                # 此处必须生成 FLOAT DV（fdiv + _create_float_dv_fast），
                # 否则 DV 类型标记为 INT 而推断为 FLOAT，后续算术走 FLOAT
                # 快路径从 INT DV 的 f64 字段读到垃圾值（恒 0 或未初始化）。
                # `//`（整除）在 _infer_expr_type 中不返回 FLOAT，仍走 sdiv + INT DV。
                if op in ('/', '除'):
                    left_f64 = self._i64_to_f64(self._extract_i64(left_dv))
                    right_f64 = self._i64_to_f64(self._extract_i64(right_dv))
                    result = self.new_register()
                    self.emit(f'{result} = fdiv double {left_f64}, {right_f64}')
                    return self._create_float_dv_fast(result), 'dv'
                left_i64 = self._extract_i64(left_dv)
                right_i64 = self._extract_i64(right_dv)
                int_op, _ = arith_ops[op]
                result = self.new_register()
                self.emit(f'{result} = {int_op} i64 {left_i64}, {right_i64}')
                return self._create_int_dv_fast(result), 'dv'
            if (self._enable_type_opt and
                    (left_type == 'FLOAT' or right_type == 'FLOAT') and
                    left_type in ('FLOAT', 'INT') and right_type in ('FLOAT', 'INT')):
                # T5C 修复：快路径仅当两侧静态类型已知（FLOAT/INT）才可直取字段；
                # 任一侧为未知类型（builtin 返回、函数参数等）时走下方通用 dv 路径，
                # 由运行时标签决定取 i64 还是 double——否则未知侧的 i64 字段被当
                # 数值（浮点 DV 的 i64 字段恒为 0），`时间戳() 乘 1.0` 得 0。
                left_f64 = self._extract_f64(left_dv) if left_type == 'FLOAT' else self._i64_to_f64(self._extract_i64(left_dv))
                right_f64 = self._extract_f64(right_dv) if right_type == 'FLOAT' else self._i64_to_f64(self._extract_i64(right_dv))
                _, float_op = arith_ops[op]
                result = self.new_register()
                self.emit(f'{result} = {float_op} double {left_f64}, {right_f64}')
                return self._create_float_dv_fast(result), 'dv'

            # String repetition: "str" * n  or  n * "str"
            if op in ('*', '乘') and left_type == 'STRING':
                return self._call_dv_func('dv_str_repeat', left_dv, right_dv), 'dv'
            if op in ('*', '乘') and right_type == 'STRING':
                return self._call_dv_func('dv_str_repeat', right_dv, left_dv), 'dv'

        cmp_ops = {
            '==': ('eq', 'oeq'), '等于': ('eq', 'oeq'),
            '!=': ('ne', 'une'), '不等于': ('ne', 'une'),
            '<': ('slt', 'olt'), '小于': ('slt', 'olt'),
            '>': ('sgt', 'ogt'), '大于': ('sgt', 'ogt'),
            '<=': ('sle', 'ole'), '小于等于': ('sle', 'ole'),
            '>=': ('sge', 'oge'), '大于等于': ('sge', 'oge'),
        }

        if op in cmp_ops:
            if self._enable_type_opt and left_type == 'INT' and right_type == 'INT':
                left_i64 = self._extract_i64(left_dv)
                right_i64 = self._extract_i64(right_dv)
                int_pred, _ = cmp_ops[op]
                cmp_reg = self.new_register()
                self.emit(f'{cmp_reg} = icmp {int_pred} i64 {left_i64}, {right_i64}')
                return self._create_bool_dv(cmp_reg), 'dv'
            if (self._enable_type_opt and
                    (left_type == 'FLOAT' or right_type == 'FLOAT') and
                    left_type in ('FLOAT', 'INT') and right_type in ('FLOAT', 'INT')):
                # T5C 修复：与算术路径同口径——未知静态类型侧回退通用 dv 比较
                left_f64 = self._extract_f64(left_dv) if left_type == 'FLOAT' else self._i64_to_f64(self._extract_i64(left_dv))
                right_f64 = self._extract_f64(right_dv) if right_type == 'FLOAT' else self._i64_to_f64(self._extract_i64(right_dv))
                _, float_pred = cmp_ops[op]
                cmp_reg = self.new_register()
                self.emit(f'{cmp_reg} = fcmp {float_pred} double {left_f64}, {right_f64}')
                return self._create_bool_dv(cmp_reg), 'dv'

        type_map = {
            '+': 'dv_add', '-': 'dv_sub', '*': 'dv_mul', '/': 'dv_div',
            '%': 'dv_mod', '**': 'dv_pow',
            '加': 'dv_add', '减': 'dv_sub', '乘': 'dv_mul', '除': 'dv_div',
            '模': 'dv_mod', '幂': 'dv_pow',
            '//': 'dv_div',  # C3-1：`整除`——通用路径 dv_div 双整数时即整除
        }
        if op in type_map:
            dv_func = type_map[op]
            # T7A 修复：`/`（除）是 true division，结果必须为 FLOAT。
            # 通用路径中两侧类型未知（函数参数等），dv_div 对双整数走整数除法
            # 返回 INT。先 dv_to_float 两侧，使 dv_div 必走 float 分支返回 FLOAT。
            # `//`（整除）仍直接调 dv_div（双整数即整除，行为正确）。
            if op in ('/', '除'):
                left_f = self._call_dv_func('dv_to_float', left_dv)
                right_f = self._call_dv_func('dv_to_float', right_dv)
                return self._call_dv_func(dv_func, left_f, right_f), 'dv'
            return self._call_dv_func(dv_func, left_dv, right_dv), 'dv'

        cmp_map = {
            '==': 'dv_eq', '等于': 'dv_eq',
            '!=': None, '不等于': None,
            '<': 'dv_lt', '小于': 'dv_lt',
            '>': 'dv_gt', '大于': 'dv_gt',
            '<=': 'dv_le', '小于等于': 'dv_le',
            '>=': 'dv_ge', '大于等于': 'dv_ge',
        }
        if op in cmp_map:
            cmp_name = cmp_map[op]
            if cmp_name is None:
                left_slot = self._store_dv(left_dv)
                right_slot = self._store_dv(right_dv)
                eq = self.new_register()
                self.emit(f'{eq} = call i32 @dv_eq(ptr {left_slot}, ptr {right_slot})')
                cmp = self.new_register()
                self.emit(f'{cmp} = icmp eq i32 {eq}, 0')
                return self._create_bool_dv(cmp), 'dv'
            left_slot = self._store_dv(left_dv)
            right_slot = self._store_dv(right_dv)
            cmp_reg = self.new_register()
            self.emit(f'{cmp_reg} = call i32 @{cmp_name}(ptr {left_slot}, ptr {right_slot})')
            final = self.new_register()
            self.emit(f'{final} = icmp ne i32 {cmp_reg}, 0')
            return self._create_bool_dv(final), 'dv'

        if op == '连接':
            return self._call_dv_func('dv_concat', left_dv, right_dv), 'dv'

        # 逻辑运算：且/与 (and), 或 (or)
        if op in ('and', 'or'):
            left_i1 = self._gen_condition_i1(expr.left, left_dv)
            right_i1 = self._gen_condition_i1(expr.right, right_dv)
            result_i1 = self.new_register()
            if op == 'and':
                self.emit(f'{result_i1} = and i1 {left_i1}, {right_i1}')
            else:
                self.emit(f'{result_i1} = or i1 {left_i1}, {right_i1}')
            return self._create_bool_dv(result_i1), 'dv'

        # C3-1：二元运算符链尾兜底。以前这里把一切不认识的运算符静默编成
        # `dv_add`——`X 管道 Y`（管道式写法本轮不做）会被编成 `X + Y`，
        # 编译成功、产物行为错误，与表达式层链尾是同一类静默降级。现在响亮报错，
        # 并给出已支持的运算符清单，把「哪个运算符能用」从猜变成查。
        raise NotImplementedError(
            f"原生后端暂不支持二元运算符「{op}」"
            f"（源码行 {self._stmt_source_line(expr)}）。"
            f"已支持：加/减/乘/除/模/幂/连接/比较/逻辑。{self._FALLBACK_HINT}"
        )

    def _i64_to_f64(self, i64_reg: str) -> str:
        """将 i64 转换为 double"""
        reg = self.new_register()
        self.emit(f'{reg} = sitofp i64 {i64_reg} to double')
        return reg

    def _gen_condition_i1(self, cond_expr, cond_dv: str) -> str:
        """根据条件表达式生成 i1 布尔值，尽可能使用类型优化"""
        cond_type = self._infer_expr_type(cond_expr) if self._enable_type_opt else None

        if cond_type == 'BOOL':
            return self._extract_bool(cond_dv)
        if cond_type == 'INT':
            i64_val = self._extract_i64(cond_dv)
            cmp_reg = self.new_register()
            self.emit(f'{cmp_reg} = icmp ne i64 {i64_val}, 0')
            return cmp_reg
        if cond_type == 'FLOAT':
            f64_val = self._extract_f64(cond_dv)
            cmp_reg = self.new_register()
            self.emit(f'{cmp_reg} = fcmp one double {f64_val}, 0.0')
            return cmp_reg

        # 兜底（类型未知 / 字符串 / 列表 / 字典 / 方法调用返回值等）：
        # 必须用运行时真值函数 dv_to_bool，不能写 dv_eq(cond, 0) != 0。
        # 原因：布尔(type 5)与整数(type 1)类型不同，dv_eq(bool假, int0) 会
        # 判为「不等」→ icmp eq 0,0 = true，导致假条件被误判为真；空字符串 /
        # 空列表同理会被误判为真。dv_to_bool 对所有类型给出正确真值。
        cond_slot = self._store_dv(cond_dv)
        truthy = self.new_register()
        self.emit(f'{truthy} = call i32 @dv_to_bool(ptr {cond_slot})')
        final = self.new_register()
        self.emit(f'{final} = icmp ne i32 {truthy}, 0')
        return final

    def _gen_typed_unary_op(self, expr: ast.UnaryOp) -> Tuple[str, str]:
        reg, _ = self._gen_expression(expr.operand)
        if expr.operator == '非':
            # R12A（R11A-01 / R11B-1）：原实现 dv_eq(operand, 整数0) 对布尔假
            # 判错——bool(type 5) 与 int(type 1) 类型不同，dv_eq 返回「不等」，
            # 「非 假」得假。同时函数调用返回值的取反也依赖类型无关真值。
            # 统一改为 dv_to_bool 取真值后取反：非 x ≡ (truthy(x) == 0)，
            # 对布尔/整数/字符串/列表/函数返回值全类型正确（与 _gen_condition_i1
            # 兜底同口径）。
            reg_slot = self._store_dv(reg)
            truthy = self.new_register()
            self.emit(f'{truthy} = call i32 @dv_to_bool(ptr {reg_slot})')
            final = self.new_register()
            self.emit(f'{final} = icmp eq i32 {truthy}, 0')
            return self._create_bool_dv(final), 'dv'
        # T6A-01（T7B）：一元负号此前被整段忽略——只处理了「非」，其余一元
        # 操作符直接返回操作数本身，于是负数字面量 `-1` 求值成 `1`
        # （模板.light 的 _找子 用 -1 当哨兵 → 判断永假 → 渲染死循环）。
        # 补 0 - operand（走既有 dv_sub，与二元减法同口径）。
        if expr.operator == '-':
            zero_dv = self._create_int_dv('0')
            zero_slot = self._store_dv(zero_dv)
            reg_slot = self._store_dv(reg)
            out_slot = self._new_dv_slot()
            self.emit(f'call void @dv_sub(ptr {out_slot}, ptr {zero_slot}, ptr {reg_slot})')
            return self._load_dv(out_slot), 'dv'
        return reg, 'dv'

    def _merge_kwargs(self, func_name, args, kw_values):
        """把关键字参数按目标函数参数名映射进位置参数列表。

        目标签名来源：内置函数用 _BUILTIN_KWARGS 表（名字 -> 位置）；光明段落
        用 _segments[name].parameters 的参数名顺序。位置参数占位在前，
        关键字参数按名填入对应槽位。"""
        sig = self._BUILTIN_KWARGS.get(func_name)
        if sig is None and self._local_seg_key(func_name) in self._segments:
            params = getattr(self._segments[self._local_seg_key(func_name)], 'parameters', None) or []
            sig = {getattr(p, 'name', None): i for i, p in enumerate(params)}
        if not sig:
            # 无签名信息：关键字参数顺序追加到末尾（保守，避免丢值）
            return args + [kw_values[n] for n in kw_values]
        out = list(args)
        for kw_name, kw_dv in kw_values.items():
            pos = sig.get(kw_name)
            if pos is None:
                out.append(kw_dv)
            else:
                while len(out) <= pos:
                    out.append(self._call_dv_func('dv_null'))
                out[pos] = kw_dv
        return out

    def _gen_typed_function_call(self, expr):
        # R11A-02 修复：局部变量遮蔽内建（Python 语义）。
        # 当调用名已被声明为局部变量时，即使源码写法像函数调用（如 `转文本(删除)`
        # 中括号内的内建名被解析为无参 FunctionCall 节点），也把它当变量引用返回——
        # light 没有「函数值可调用」语义，用户用内建名作变量即表示要遮蔽内建。
        # 仅当该名从未作为变量声明时才走内建调用（如真正的 `删除(表, 2)` list.remove）。
        _nm = expr.name
        if isinstance(_nm, ast.Identifier):
            _key = _nm.name
        elif isinstance(_nm, ast.SegmentName):
            _key = _nm.name
        elif isinstance(_nm, ast.PropertyAccess):
            _key = None
        elif isinstance(_nm, str):
            _key = _nm
        else:
            _key = str(_nm)
        if _key is not None and (_key in self._local_vars or _key in self._current_func_params):
            _v = self.get_var(_key)
            if _v is not None:
                return _v, 'dv'
        if isinstance(expr.name, ast.Identifier):
            func_name = expr.name.name
        elif isinstance(expr.name, ast.SegmentName):
            func_name = expr.name.name
        elif isinstance(expr.name, ast.PropertyAccess):
            return self._gen_typed_method_call(expr)
        elif isinstance(expr.name, str):
            func_name = expr.name
        else:
            func_name = str(expr.name)

        # 关键字参数支持：f(名=值)。位置参数照常；KeywordArg 按目标函数
        # 参数名映射到位置（stdlib 里 打开文件(..., encoding=)、sort(reverse=) 用）。
        args = []
        kw_values = {}
        plain_arg_asts = []
        for arg in expr.arguments:
            if isinstance(arg, ast.KeywordArg):
                kw_values[arg.name] = self._gen_expression(arg.value)[0]
            else:
                args.append(self._gen_expression(arg)[0])
                plain_arg_asts.append(arg)
        arg_asts = plain_arg_asts
        if kw_values:
            args = self._merge_kwargs(func_name, args, kw_values)
            # 位置参数已被重排，无法与实参 AST 一一对齐 → 放弃写回（保守）
            arg_asts = None

        # 方法内部：己.方法名(...) 被 parser 拍平成 SegmentName('self.方法名')。
        # 不拦下来会一路落到「未定义的段落：self.xxx」。这里对己对象做一次
        # dv_call_method，与方法调方法（_gen_typed_method_call）同语义。
        # 注：嵌套的 己.字段.方法 不会被拍平——它走 PropertyAccess →
        # _gen_typed_method_call，再由 _persist_to_receiver 写回字段。
        if self._method_result_ptr is not None:
            self_method_name = None
            if func_name.startswith('self.') and len(func_name) > 5:
                self_method_name = func_name[5:]
            elif func_name.startswith('己') and len(func_name) > 1 and not func_name.startswith('己.'):
                self_method_name = func_name[1:]
            if self_method_name:
                self_dv = self.get_var('己')
                if self_dv is not None:
                    return self._gen_self_method_call(self_method_name, args)

        # 当前模块的段函数：优先于同名 builtin（转译腿 Python 语义：用户定义段
        # 覆盖内置。stdlib JSON核心 定义 `段落 连接`，若先查 builtin 会被
        # builtin `连接`(dv_concat 字符串拼接) 劫持，`连接(部分, ", ")` 错乱）。
        if self._local_seg_key(func_name) in self._segments:
            return self._gen_typed_segment_call(func_name, args, arg_asts)

        # T9A：导入的外部段函数也优先于同名 builtin（模块隔离后导入段不再
        # 被本地检查命中，需在此处补位，否则 数学.对数 会被 builtin dv_log 劫持）。
        # 但仅当目标模块确实定义了该段时才走导入路径；若导入名实为 builtin
        # （如 随机位 被测试导入但无段定义），回退到 builtin 检查。
        if func_name in self._imports:
            _imp_mod, _imp_orig = self._imports[func_name]
            if (self._seg_reg_key(_imp_orig, _imp_mod) in self._segments
                    or self._resolve_import_chain(_imp_mod, _imp_orig)):
                return self._gen_imported_segment_call(func_name, args, arg_asts)

        # 内置函数（arg_asts：与 args 对齐的参数 AST，供类型推断快路径用；
        # kwargs 重排后为 None）
        builtin = self._gen_typed_builtin(func_name, args, arg_asts)
        if builtin is not None:
            # 函数式变异调用写回：`列表弹出(己.数据)` / `列表插入(己.数据, 0, x)` 这类
            # 独立语句调用 mutating builtin（返回新列表），须把新列表写回
            # 第一参数（实例字段或局部变量），否则跨调用累积丢失。
            if func_name in ('追加', 'append', '列表追加', '清空', 'clear', '设置', 'set',
                             '插入', 'insert', '列表插入', 'list_insert',
                             '删除', 'remove', 'list_remove',
                             '列表弹出', 'list_pop') and expr.arguments:
                self._persist_to_receiver(
                    types.SimpleNamespace(obj=expr.arguments[0]), builtin[0])
            return builtin

        # A9-S2：AstAdapter 把 v3 SliceExpr（`表[1:2]`）转成对 `slice` 的调用。
        # 切片作为索引操作已在 _gen_typed_index_access 中拦截实现。
        # 如果走到这里，说明 `slice` 被当作独立函数调用（非索引位），语义不对。
        if func_name == 'slice':
            raise NotImplementedError(
                f"slice 不能作为独立函数调用——请用索引语法 `表[起:止]`"
                f"（源码行 {self._stmt_source_line(expr)}）。"
            )

        # C3-1：拼错名字的函数/段落调用（AstAdapter 把 v3 ParagraphCall 转成
        # FunctionCall，所以「未知段落」真正落在这里）。以前静默编成整数 0，
        # 现在报错并列出本模块已定义候选。
        # 解析器歧义兜底：局部变量名与内置判型名重名时（如 stdlib 的
        # `设 是浮点 为 假` 后 `如果 是浮点 == 真`），v3 解析器把变量引用
        # 解析成无参 ParagraphCall，适配层转成 FunctionCall。此处若名字已是
        # 已收集局部变量且调用无参，降级为变量引用，与转译腿语义一致。
        if not args and func_name in self._local_vars:
            var_ref = self.get_var(func_name)
            if var_ref is not None:
                return var_ref, 'dv'

        self._reject_unknown_call(func_name, expr)

    def _emit_args_writeback(self, args_arr: str, arg_asts, num_args: int) -> None:
        """T7B / T5C-02·04 调用侧：段调用返回后，把 %args[i] 的值写回实参变量槽。

        被调方在出口把形参壳写回了 %args[i]（见 _emit_param_writeback）；这里再
        把它搬回调用方变量，写回链才闭合。必须在 llvm.stackrestore 之前执行——
        args_arr 是栈上 alloca，restore 之后就失效了。

        只对「实参是局部变量标识符」的位置写回：其余（字面量、索引、属性、
        临时槽）本就没有可写回的归属，Python 里也不可能观察到变化。
        """
        if not arg_asts:
            return
        for i, a in enumerate(arg_asts):
            if i >= num_args:
                break
            if not isinstance(a, ast.Identifier):
                continue
            slot = self._local_vars.get(a.name)
            if slot is None:
                continue
            elem_ptr = self.new_register()
            self.emit(f'{elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {args_arr}, i64 {i}')
            val = self.new_register()
            self.emit(f'{val} = load {LIGHTVALUE_STRUCT}, ptr {elem_ptr}')
            self.emit(f'store {LIGHTVALUE_STRUCT} {val}, ptr {slot}')

    def _gen_imported_segment_call(self, name: str, args: List[str], arg_asts=None) -> Tuple[str, str]:
        """调用从其他模块导入的段函数。

        T9A 修复：直接使用目标模块的定义 safe name（模块隔离），而非 alias 名。
        原因：未导出的段（如 随机.随机位）没有生成 alias，原 alias 路径会引用
        未定义函数。多模块联合编译时所有段定义都在同一 IR 中，可直接调用定义。
        """
        module_name, orig_name = self._imports[name]
        # R12C（R11A-05）：再导出链——B 从 A 导入 f 再导出，调用方按 B 名义
        # 查找；这里跟随链到真正定义模块，直接调用定义端 safe name。
        resolved = self._resolve_import_chain(module_name, orig_name)
        if resolved:
            module_name, orig_name = resolved
        safe = self._safe_func_name(orig_name, module_name)
        result_slot = self._new_dv_slot()
        # R10-11a 打回 A2：同 _gen_typed_segment_call，段函数返回时
        # dv_obj_release_slot(result_ptr) 会读取未初始化槽位 → O0 段错误。
        self.emit(f'call void @dv_null(ptr {result_slot})')
        num_args = len(args)
        if num_args == 0:
            args_arr_ptr = 'null'
            self.emit(f'call void @_seg_{safe}(ptr {result_slot}, ptr {args_arr_ptr}, i32 {num_args})')
        else:
            stack_save = self.new_register()
            self.emit(f'{stack_save} = call ptr @llvm.stacksave()')
            args_arr = self.new_register()
            self.emit(f'{args_arr} = alloca {LIGHTVALUE_STRUCT}, i32 {num_args}')
            for i, arg_dv in enumerate(args):
                elem_ptr = self.new_register()
                self.emit(f'{elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {args_arr}, i64 {i}')
                self.emit(f'store {LIGHTVALUE_STRUCT} {arg_dv}, ptr {elem_ptr}')
            self.emit(f'call void @_seg_{safe}(ptr {result_slot}, ptr {args_arr}, i32 {num_args})')
            # T7B / T5C-02·04：写回（跨模块调用同样适用，必须在 stackrestore 前）
            self._emit_args_writeback(args_arr, arg_asts, num_args)
            self.emit(f'call void @llvm.stackrestore(ptr {stack_save})')
        result = self.new_register()
        self.emit(f'{result} = load {LIGHTVALUE_STRUCT}, ptr {result_slot}')
        return result, 'dv'

    def _gen_typed_builtin(self, name: str, args: List[str], arg_asts=None) -> Optional[Tuple[str, str]]:
        # 异常类名直呼构造：stdlib 写 `抛出 运行时错误("...")`（裸类名调用，
        # 非 `新建`），与 `新建 异常(提示)` 走同一类实例化语义。中文名覆盖
        # stdlib 直呼的 Python 风格名，英文名对齐已注册的内置异常类。
        if name in ('异常', '运行时异常', '值异常', '索引异常', '类型异常', 'IO异常',
                    '内存异常', '算术异常', '运行时错误', '类型错误', '值错误', '索引错误',
                    '读取错误', '请求错误', 'Exception', 'RuntimeException', 'ValueError',
                    'TypeError', 'IndexError', 'IOException', 'MemoryError', 'ArithmeticError'):
            name_reg = self.gen_string_constant(name)
            exc_slot = self._new_dv_slot()
            self.emit(f'call void @dv_class_new_named(ptr {exc_slot}, ptr {name_reg})')
            return self._load_dv(exc_slot), 'dv'
        if name in ('输出', '打印'):
            if args:
                slot = self._store_dv(args[0])
                self.emit(f'call void @dv_println(ptr {slot})')
            else:
                null_slot = self._new_dv_slot()
                self.emit(f'call void @dv_null(ptr {null_slot})')
                self.emit(f'call void @dv_println(ptr {null_slot})')
            return self._create_int_dv('0'), 'dv'

        if name in ('输入', 'input'):
            slot = self._new_dv_slot()
            self.emit(f'call void @dv_input(ptr {slot})')
            reg = self._load_dv(slot)
            return reg, 'dv'

        if name in ('时间戳', '时间', '_dv_timestamp'):
            dbl = self.new_register()
            self.emit(f'{dbl} = call double @dv_timestamp()')
            return self._call_dv_func('dv_float', f'double {dbl}'), 'dv'

        # T5C：确定性随机数（MT19937，对齐 CPython random）
        if name in ('随机数', 'random', 'dv_random'):
            dbl = self.new_register()
            self.emit(f'{dbl} = call double @dv_random()')
            return self._call_dv_func('dv_float', f'double {dbl}'), 'dv'

        if name in ('播种随机种子', '设置随机种子', 'random_seed', 'dv_random_seed'):
            if args:
                seed_i64 = self.new_register()
                self.emit(f'{seed_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                self.emit(f'call void @dv_random_seed(i64 {seed_i64})')
            return self._create_int_dv('0'), 'dv'

        if name in ('随机位', 'random_bits', 'getrandbits', 'dv_random_bits'):
            if args:
                k_i64 = self.new_register()
                self.emit(f'{k_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                ret = self.new_register()
                self.emit(f'{ret} = call i64 @dv_random_bits(i64 {k_i64})')
                return self._create_int_dv(ret), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name == '格式化时间':
            if not args:
                return self._create_int_dv('0'), 'dv'
            dbl = self.new_register()
            self.emit(f'{dbl} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 2')
            fmt_reg = self.gen_string_constant("%Y-%m-%d %H:%M:%S")
            out = self.new_register()
            self.emit(f'{out} = call ptr @dv_format_time(double {dbl}, ptr {fmt_reg})')
            return self._create_str_dv(out), 'dv'

        # T6B：带格式的 strftime（dv_format_time 支持任意 strftime fmt）
        if name in ('时间格式化', 'strftime', 'format_time', '_strftime'):
            if not args:
                return self._create_str_dv(self.gen_string_constant("")), 'dv'
            dbl = self.new_register()
            self.emit(f'{dbl} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 2')
            if len(args) >= 2:
                fmt_ptr = self.new_register()
                self.emit(f'{fmt_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 3')
            else:
                fmt_ptr = self.gen_string_constant("%Y-%m-%d %H:%M:%S")
            out = self.new_register()
            self.emit(f'{out} = call ptr @dv_format_time(double {dbl}, ptr {fmt_ptr})')
            return self._create_str_dv(out), 'dv'

        # T6B：秒级睡眠 dv_sleep(double)；毫秒级用既有 睡眠（事件循环区）
        if name in ('睡眠秒', 'sleep_seconds', 'dv_sleep', '_sleep_sec'):
            if args:
                dbl = self.new_register()
                self.emit(f'{dbl} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 2')
                self.emit(f'call void @dv_sleep(double {dbl})')
            return self._create_int_dv('0'), 'dv'

        # T6B：单调高分辨率时钟 dv_clock() -> float 秒（perf_counter/monotonic 语义）
        if name in ('时钟', '性能计数器', '单调时钟', 'clock', 'perf_counter', 'monotonic', '_clock'):
            dbl = self.new_register()
            self.emit(f'{dbl} = call double @dv_clock()')
            return self._call_dv_func('dv_float', f'double {dbl}'), 'dv'


        if name in ('文件存在', 'file_exists', 'path_exists'):
            if args:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                file_reg = self.new_register()
                self.emit(f'{file_reg} = call i32 @dv_file_exists(ptr {path_ptr})')
                cmp = self.new_register()
                self.emit(f'{cmp} = icmp ne i32 {file_reg}, 0')
                return self._create_bool_dv(cmp), 'dv'
            return self._create_bool_dv('false'), 'dv'

        if name in ('目录存在', 'dir_exists', 'is_dir'):
            if args:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                file_reg = self.new_register()
                self.emit(f'{file_reg} = call i32 @dv_is_dir(ptr {path_ptr})')
                cmp = self.new_register()
                self.emit(f'{cmp} = icmp ne i32 {file_reg}, 0')
                return self._create_bool_dv(cmp), 'dv'
            return self._create_bool_dv('false'), 'dv'

        if name in ('读取文件', 'read_file', 'load_file', '_读文件'):
            if args:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                out = self.new_register()
                self.emit(f'{out} = call ptr @dv_read_file(ptr {path_ptr})')
                return self._create_str_dv(out), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('写入文件', 'write_file', 'save_file'):
            if len(args) >= 2:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                str_ptr = self.new_register()
                self.emit(f'{str_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 3')
                self.emit(f'call void @dv_write_file(ptr {path_ptr}, ptr {str_ptr})')
            return self._create_int_dv('0'), 'dv'

        if name in ('追加文件', 'append_file', 'write_append'):
            if len(args) >= 2:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                str_ptr = self.new_register()
                self.emit(f'{str_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 3')
                self.emit(f'call void @dv_append_file(ptr {path_ptr}, ptr {str_ptr})')
            return self._create_int_dv('0'), 'dv'

        if name in ('打开文件', 'open_file'):
            # 打开文件(路径, 模式[, encoding]) -> 文件句柄对象。
            # runtime 签名 dv_open_file(result, char* path, char* mode, char* encoding)；
            # encoding 参数 POSIX 下忽略（字节直写 UTF-8）。
            if len(args) >= 2:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                mode_ptr = self.new_register()
                self.emit(f'{mode_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 3')
                if len(args) >= 3:
                    enc_ptr = self.new_register()
                    self.emit(f'{enc_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[2]}, 3')
                    return self._call_dv_func('dv_open_file', f'ptr {path_ptr}', f'ptr {mode_ptr}', f'ptr {enc_ptr}'), 'dv'
                return self._call_dv_func('dv_open_file', f'ptr {path_ptr}', f'ptr {mode_ptr}', 'ptr null'), 'dv'
            return self._call_dv_func('dv_open_file', 'ptr null', 'ptr null', 'ptr null'), 'dv'

        if name in ('write', '写'):
            # 文件句柄方法：f.write(文本)
            if len(args) >= 2:
                return self._call_dv_func('dv_file_write', args[0], args[1]), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('close', '关闭'):
            # 文件句柄方法：f.close()
            if args:
                return self._call_dv_func('dv_file_close', args[0]), 'dv'
            return self._create_bool_dv('true'), 'dv'

        if name in ('read', '读取'):
            # 文件句柄方法：f.read()（从当前文件位置读到 EOF，返回字符串）
            if args:
                return self._call_dv_func('dv_file_read', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('文件大小', 'file_size'):
            if args:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                size = self.new_register()
                self.emit(f'{size} = call i64 @dv_file_size(ptr {path_ptr})')
                return self._create_int_dv(size), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('删除文件', 'delete_file', 'remove_file'):
            if args:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_delete_file(ptr {path_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('列出目录', 'list_dir', 'dir_list'):
            if args:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                return self._call_dv_func('dv_list_dir', f'ptr {path_ptr}'), 'dv'
            return self._call_dv_func('dv_list_new'), 'dv'

        if name in ('环境变量', 'getenv', 'get_env'):
            if args:
                name_ptr = self.new_register()
                self.emit(f'{name_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                out = self.new_register()
                self.emit(f'{out} = call ptr @dv_getenv(ptr {name_ptr})')
                return self._create_str_dv(out), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('设置环境变量', 'setenv', 'set_env'):
            if len(args) >= 2:
                name_ptr = self.new_register()
                self.emit(f'{name_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                val_ptr = self.new_register()
                self.emit(f'{val_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 3')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_setenv(ptr {name_ptr}, ptr {val_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('当前目录', 'getcwd', 'cwd'):
            out = self.new_register()
            self.emit(f'{out} = call ptr @dv_getcwd()')
            return self._create_str_dv(out), 'dv'

        if name in ('切换目录', 'chdir', 'cd'):
            if args:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_chdir(ptr {path_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('执行命令', 'system', 'exec'):
            if args:
                cmd_ptr = self.new_register()
                self.emit(f'{cmd_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_system(ptr {cmd_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('退出程序', '退出', 'exit'):
            if args:
                code_i64 = self.new_register()
                self.emit(f'{code_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                code_i32 = self.new_register()
                self.emit(f'{code_i32} = trunc i64 {code_i64} to i32')
                self.emit(f'call void @dv_exit(i32 {code_i32})')
            else:
                self.emit(f'call void @dv_exit(i32 0)')
            return self._create_int_dv('0'), 'dv'

        if name in ('参数列表', 'argv', 'args'):
            return self._call_dv_func('dv_get_args'), 'dv'

        if name in ('整数', 'int', '转整数', 'to_int'):
            if not args:
                return self._create_int_dv('0'), 'dv'
            # R12A（R11B-2）：runtime dv_to_int 对 bool（type 5）落默认分支
            # 返回 0，「整数(真)」得 0，与 Python int(True)=1 不符。参数 AST
            # 静态类型为 BOOL（真/假 字面量、比较、非 表达式等）时直接从
            # 布尔字段（field 4）零扩展成 i64。类型未知的操作数仍走
            # dv_to_int（bool→int 的运行时映射归 T7）。
            if (arg_asts and self._enable_type_opt
                    and self._infer_expr_type(arg_asts[0]) == 'BOOL'):
                b32 = self.new_register()
                self.emit(f'{b32} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 4')
                wide = self.new_register()
                self.emit(f'{wide} = zext i32 {b32} to i64')
                return self._create_int_dv_fast(wide), 'dv'
            return self._call_dv_func('dv_to_int', args[0]), 'dv'

        if name in ('浮点数', 'float', '转浮点', 'to_float'):
            if not args:
                return self._call_dv_func('dv_float', 'double 0.0'), 'dv'
            return self._call_dv_func('dv_to_float', args[0]), 'dv'

        if name in ('长度', '长', 'len', '列表长度', '字符串长度'):
            if not args:
                return self._create_int_dv('0'), 'dv'
            slot = self._store_dv(args[0])
            i64_val = self.new_register()
            self.emit(f'{i64_val} = call i64 @dv_len(ptr {slot})')
            return self._create_int_dv(i64_val), 'dv'

        if name in ('码位', 'ord'):
            # 取字符串首字符的码点（等价 Python ord）
            if not args:
                return self._create_int_dv('0'), 'dv'
            return self._call_dv_func('dv_ord', args[0]), 'dv'

        if name in ('字符自码位', 'chr'):
            # 码点 -> UTF-8 字符串（等价 Python chr）
            if not args:
                return self._create_str_dv(self.gen_string_constant("")), 'dv'
            return self._call_dv_func('dv_chr', args[0]), 'dv'

        if name in ('十六进制', 'hex'):
            # 码点 -> 大写十六进制字符串，无 0x 前缀（等价 format(n,'X')）
            if not args:
                return self._create_str_dv(self.gen_string_constant("")), 'dv'
            return self._call_dv_func('dv_hex', args[0]), 'dv'

        if name in ('新建', '新建列表', 'new_list', '列表创建'):
            return self._call_dv_func('dv_list_new'), 'dv'

        if name in ('列', 'list', '列表'):
            # C3-1：`列(1, 2, 3)` 构造带元素的列表（走漏到链尾兜底前就该支持的
            # 常规形态）。无参数时等价于空列表。
            return self._gen_typed_list_from_args(args), 'dv'

        if name in ('追加', 'append', '列表追加'):
            if len(args) >= 2:
                slot0 = self._store_dv(args[0])
                slot1 = self._store_dv(args[1])
                self.emit(f'call void @dv_list_append(ptr {slot0}, ptr {slot0}, ptr {slot1})')
                result = self._load_dv(slot0)
                return result, 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('包含', 'contains', '列表包含'):
            if len(args) >= 2:
                slot0 = self._store_dv(args[0])
                slot1 = self._store_dv(args[1])
                i64_val = self.new_register()
                self.emit(f'{i64_val} = call i64 @dv_list_contains(ptr {slot0}, ptr {slot1})')
                cmp = self.new_register()
                self.emit(f'{cmp} = icmp ne i64 {i64_val}, 0')
                return self._create_bool_dv(cmp), 'dv'
            return self._create_bool_dv('false'), 'dv'

        if name in ('插入', 'insert', 'list_insert', '列表插入'):
            if len(args) >= 3:
                idx_i64 = self.new_register()
                self.emit(f'{idx_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                return self._call_dv_func('dv_list_insert', args[0], f'i64 {idx_i64}', args[2]), 'dv'
            return self._call_dv_func('dv_list_new'), 'dv'

        if name in ('列表弹出', 'list_pop'):
            # 返回移除元素后的新列表（数据结构轻量用法：先取值、后弹、弃返回值）；
            # 调用点对接收者（字段/局部变量）做写回。无下标参数时弹末尾（i64 -1）。
            if len(args) >= 1:
                if len(args) >= 2:
                    idx_i64 = self.new_register()
                    self.emit(f'{idx_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                    return self._call_dv_func('dv_list_pop', args[0], f'i64 {idx_i64}'), 'dv'
                return self._call_dv_func('dv_list_pop', args[0], 'i64 -1'), 'dv'
            return self._call_dv_func('dv_list_new'), 'dv'

        if name in ('删除', 'remove', 'list_remove'):
            if len(args) >= 2:
                idx_i64 = self.new_register()
                self.emit(f'{idx_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                return self._call_dv_func('dv_list_remove', args[0], f'i64 {idx_i64}'), 'dv'
            return self._call_dv_func('dv_list_new'), 'dv'

        if name in ('设置', 'set', 'list_set'):
            if len(args) >= 3:
                idx_i64 = self.new_register()
                self.emit(f'{idx_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                return self._call_dv_func('dv_list_set', args[0], f'i64 {idx_i64}', args[2]), 'dv'
            return self._call_dv_func('dv_list_new'), 'dv'

        if name in ('索引查找', 'index_of', 'list_index'):
            if len(args) >= 2:
                slot0 = self._new_dv_slot()
                self.emit(f'store {LIGHTVALUE_STRUCT} {args[0]}, ptr {slot0}')
                slot1 = self._new_dv_slot()
                self.emit(f'store {LIGHTVALUE_STRUCT} {args[1]}, ptr {slot1}')
                idx = self.new_register()
                self.emit(f'{idx} = call i64 @dv_list_index_of(ptr {slot0}, ptr {slot1})')
                return self._create_int_dv(idx), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('包含', 'contains', 'list_contains'):
            if len(args) >= 2:
                slot0 = self._new_dv_slot()
                self.emit(f'store {LIGHTVALUE_STRUCT} {args[0]}, ptr {slot0}')
                slot1 = self._new_dv_slot()
                self.emit(f'store {LIGHTVALUE_STRUCT} {args[1]}, ptr {slot1}')
                val = self.new_register()
                self.emit(f'{val} = call i64 @dv_list_contains(ptr {slot0}, ptr {slot1})')
                cmp = self.new_register()
                self.emit(f'{cmp} = icmp ne i64 {val}, 0')
                return self._create_bool_dv(cmp), 'dv'
            return self._create_bool_dv('false'), 'dv'

        if name in ('反转', 'reverse', 'list_reverse'):
            if args:
                return self._call_dv_func('dv_list_reverse', args[0]), 'dv'
            return self._call_dv_func('dv_list_new'), 'dv'

        if name in ('排序', 'sort', 'list_sort', '列表排序'):
            if args:
                return self._call_dv_func('dv_list_sort', args[0]), 'dv'
            return self._call_dv_func('dv_list_new'), 'dv'

        if name in ('列表获取',):
            if len(args) >= 2:
                idx_i64 = self.new_register()
                self.emit(f'{idx_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                return self._call_dv_func('dv_list_get', args[0], f'i64 {idx_i64}'), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('字符串获取',):
            if len(args) >= 2:
                idx_i64 = self.new_register()
                self.emit(f'{idx_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                return self._call_dv_func('dv_str_get', args[0], f'i64 {idx_i64}'), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('获取', 'get'):
            # R12C（R11B-3）：方法形式 `表.获取(键, 默认)` 的接收者是字典
            # （type 7）时走字典路径（含默认值），否则回落字符串/列表索引
            # 路径。运行时类型分派，静态类型未知也不受影响。
            if args:
                obj_slot = self._store_dv(args[0])
                type_reg = self.new_register()
                self.emit(f'{type_reg} = load i32, ptr {obj_slot}')
                is_dict = self.new_register()
                self.emit(f'{is_dict} = icmp eq i32 {type_reg}, 7')
                dict_lab = self.new_label('get_dict')
                idx_lab = self.new_label('get_idx')
                end_lab = self.new_label('get_end')
                res_slot = self._new_dv_slot()
                self.emit(f'br i1 {is_dict}, label %{dict_lab}, label %{idx_lab}')
                self.emit(f'{dict_lab}:')
                if len(args) >= 3:
                    k_slot = self._store_dv(args[1])
                    d_slot = self._store_dv(args[2])
                    self.emit(f'call void @dv_dict_get_def(ptr {res_slot}, ptr {obj_slot}, ptr {k_slot}, ptr {d_slot})')
                elif len(args) == 2:
                    k_slot = self._store_dv(args[1])
                    self.emit(f'call void @dv_dict_get(ptr {res_slot}, ptr {obj_slot}, ptr {k_slot})')
                else:
                    self.emit(f'call void @dv_null(ptr {res_slot})')
                self.emit(f'br label %{end_lab}')
                self.emit(f'{idx_lab}:')
                if len(args) >= 2:
                    idx_i64 = self.new_register()
                    self.emit(f'{idx_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                    self.emit(f'call void @dv_str_get(ptr {res_slot}, ptr {obj_slot}, i64 {idx_i64})')
                else:
                    self.emit(f'call void @dv_null(ptr {res_slot})')
                self.emit(f'br label %{end_lab}')
                self.emit(f'{end_lab}:')
                result = self._load_dv(res_slot)
                return result, 'dv'
        if name in ('获取', 'get', '索引'):
            if len(args) >= 2:
                idx_i64 = self.new_register()
                self.emit(f'{idx_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                obj_slot = self._store_dv(args[0])
                type_reg = self.new_register()
                self.emit(f'{type_reg} = load i32, ptr {obj_slot}')
                is_str = self.new_register()
                self.emit(f'{is_str} = icmp eq i32 {type_reg}, 3')
                then_lab = self.new_label('get_str')
                else_lab = self.new_label('get_list')
                end_lab = self.new_label('get_end')
                result_slot = self._new_dv_slot()
                self.emit(f'br i1 {is_str}, label %{then_lab}, label %{else_lab}')
                self.emit(f'{then_lab}:')
                self.emit(f'call void @dv_str_get(ptr {result_slot}, ptr {obj_slot}, i64 {idx_i64})')
                self.emit(f'br label %{end_lab}')
                self.emit(f'{else_lab}:')
                self.emit(f'call void @dv_list_get(ptr {result_slot}, ptr {obj_slot}, i64 {idx_i64})')
                self.emit(f'br label %{end_lab}')
                self.emit(f'{end_lab}:')
                result = self._load_dv(result_slot)
                return result, 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('转文本', 'to_string', '转字符串', '转串', 'str'):
            if args:
                # R12C（R11A-09）：runtime dv_to_string 对列表（type 4）读 str
                # 字段恒得 "[]"。运行时按 DV 类型分派：列表 → dv_list_join
                # （逐元素 dv_to_string）后加方括号；其余走原 dv_value_to_string。
                # 嵌套容器的内层元素仍走 dv_to_string（嵌套序列化归 T7）。
                obj_slot = self._store_dv(args[0])
                type_reg = self.new_register()
                self.emit(f'{type_reg} = load i32, ptr {obj_slot}')
                is_list = self.new_register()
                self.emit(f'{is_list} = icmp eq i32 {type_reg}, 4')
                list_lab = self.new_label('tostr_list')
                def_lab = self.new_label('tostr_def')
                end_lab = self.new_label('tostr_end')
                res_slot = self._new_dv_slot()
                self.emit(f'br i1 {is_list}, label %{list_lab}, label %{def_lab}')
                self.emit(f'{list_lab}:')
                joined = self._call_dv_func(
                    'dv_list_join', args[0],
                    self._create_str_dv(self.gen_string_constant(", ")))
                open_br = self._create_str_dv(self.gen_string_constant("["))
                with_open = self._call_dv_func('dv_concat', open_br, joined)
                wo_slot = self._store_dv(with_open)
                close_br = self._create_str_dv(self.gen_string_constant("]"))
                cb_slot = self._store_dv(close_br)
                self.emit(f'call void @dv_concat(ptr {res_slot}, ptr {wo_slot}, ptr {cb_slot})')
                self.emit(f'br label %{end_lab}')
                self.emit(f'{def_lab}:')
                self.emit(f'call void @dv_value_to_string(ptr {res_slot}, ptr {obj_slot})')
                self.emit(f'br label %{end_lab}')
                self.emit(f'{end_lab}:')
                result = self._load_dv(res_slot)
                return result, 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name == '连接':
            a = args[0] if len(args) > 0 else self._create_int_dv('0')
            b = args[1] if len(args) > 1 else self._create_int_dv('0')
            return self._call_dv_func('dv_concat', a, b), 'dv'

        if name in ('正弦', 'sin'):
            if args:
                return self._call_dv_func('dv_sin', args[0]), 'dv'

        if name in ('对数', 'log', '自然对数'):
            if args:
                return self._call_dv_func('dv_log', args[0]), 'dv'
            return self._call_dv_func('dv_float', 'double 0.0'), 'dv'

        # T7A：解除内联 Taylor workaround，补齐常用对数/对数2/指数的 builtin 路由
        if name in ('常用对数', 'log10'):
            if args:
                return self._call_dv_func('dv_log10', args[0]), 'dv'
            return self._call_dv_func('dv_float', 'double 0.0'), 'dv'

        if name in ('对数2', 'log2'):
            if args:
                return self._call_dv_func('dv_log2', args[0]), 'dv'
            return self._call_dv_func('dv_float', 'double 0.0'), 'dv'

        if name in ('指数', 'exp'):
            if args:
                return self._call_dv_func('dv_exp', args[0]), 'dv'
            return self._call_dv_func('dv_float', 'double 1.0'), 'dv'

        if name in ('余弦', 'cos'):
            if args:
                return self._call_dv_func('dv_cos', args[0]), 'dv'
            return self._call_dv_func('dv_float', 'double 0.0'), 'dv'

        if name in ('平方根', 'sqrt'):
            if args:
                return self._call_dv_func('dv_sqrt', args[0]), 'dv'
            return self._call_dv_func('dv_float', 'double 0.0'), 'dv'

        if name in ('绝对值', 'abs'):
            if args:
                return self._call_dv_func('dv_abs', args[0]), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('幂', 'pow'):
            if len(args) >= 2:
                return self._call_dv_func('dv_pow', args[0], args[1]), 'dv'
            return self._call_dv_func('dv_float', 'double 0.0'), 'dv'

        if name in ('向下取整', 'floor'):
            if args:
                return self._call_dv_func('dv_floor', args[0]), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('向上取整', 'ceil'):
            if args:
                return self._call_dv_func('dv_ceil', args[0]), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('四舍五入', 'round'):
            if args:
                return self._call_dv_func('dv_round', args[0]), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('取模', 'mod'):
            if len(args) >= 2:
                return self._call_dv_func('dv_mod', args[0], args[1]), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('整除', 'div'):
            if len(args) >= 2:
                return self._call_dv_func('dv_div', args[0], args[1]), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('截取', 'substr', 'substring'):
            if len(args) >= 3:
                start_i64 = self.new_register()
                self.emit(f'{start_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                len_i64 = self.new_register()
                self.emit(f'{len_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[2]}, 1')
                return self._call_dv_func('dv_substr', args[0], f'i64 {start_i64}', f'i64 {len_i64}'), 'dv'
            if len(args) >= 2:
                start_i64 = self.new_register()
                self.emit(f'{start_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                return self._call_dv_func('dv_substr', args[0], f'i64 {start_i64}', f'i64 -1'), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('查找', 'find', 'str_find'):
            if len(args) >= 2:
                slot0 = self._store_dv(args[0])
                slot1 = self._store_dv(args[1])
                i64_val = self.new_register()
                self.emit(f'{i64_val} = call i64 @dv_str_find(ptr {slot0}, ptr {slot1})')
                return self._create_int_dv(i64_val), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('rfind', '右查找', 'str_rfind'):
            if len(args) >= 2:
                slot0 = self._store_dv(args[0])
                slot1 = self._store_dv(args[1])
                i64_val = self.new_register()
                self.emit(f'{i64_val} = call i64 @dv_str_rfind(ptr {slot0}, ptr {slot1})')
                return self._create_int_dv(i64_val), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('大写', 'upper', 'to_upper', '转大写'):
            if args:
                return self._call_dv_func('dv_upper', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('小写', 'lower', 'to_lower', '转小写'):
            if args:
                return self._call_dv_func('dv_lower', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        # ── T5B：编码 / 哈希 runtime 内置注册（仅接线既有 runtime，不新增 C 函数）──
        # 公开中文名 + 内部 ASCII 别名双注册；模块段落内调别名（如 _b64_encode）
        # 以避免「段落名 == builtin 名」的同名遮蔽（段 > builtin 派发顺序）。
        if name in ('Base64编码', 'base64_encode', 'b64encode', '_b64_encode'):
            if args:
                obj_slot = self._store_dv(args[0])
                data_ptr = self.new_register()
                self.emit(f'{data_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                len_i64 = self.new_register()
                # dv_str_len 入参是 LightValue*（需先 _store_dv 取指针）；编码函数仍用 data_ptr(char*)
                self.emit(f'{len_i64} = call i64 @dv_str_len(ptr {obj_slot})')
                len_i32 = self.new_register()
                self.emit(f'{len_i32} = trunc i64 {len_i64} to i32')
                out = self.new_register()
                self.emit(f'{out} = call ptr @dv_base64_encode(ptr {data_ptr}, i32 {len_i32})')
                return self._create_str_dv(out), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('Base64解码', 'base64_decode', 'b64decode', '_b64_decode'):
            if args:
                str_ptr = self.new_register()
                self.emit(f'{str_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                outlen_ptr = self.new_register()
                self.emit(f'{outlen_ptr} = alloca i32')
                out = self.new_register()
                self.emit(f'{out} = call ptr @dv_base64_decode(ptr {str_ptr}, ptr {outlen_ptr})')
                return self._create_str_dv(out), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('MD5', 'md5', '_md5'):
            if args:
                obj_slot = self._store_dv(args[0])
                data_ptr = self.new_register()
                self.emit(f'{data_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                len_i64 = self.new_register()
                # dv_str_len 入参是 LightValue*（需先 _store_dv 取指针）；编码函数仍用 data_ptr(char*)
                self.emit(f'{len_i64} = call i64 @dv_str_len(ptr {obj_slot})')
                len_i32 = self.new_register()
                self.emit(f'{len_i32} = trunc i64 {len_i64} to i32')
                out = self.new_register()
                self.emit(f'{out} = call ptr @dv_md5(ptr {data_ptr}, i32 {len_i32})')
                return self._create_str_dv(out), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('SHA1', 'sha1', '_sha1'):
            if args:
                obj_slot = self._store_dv(args[0])
                data_ptr = self.new_register()
                self.emit(f'{data_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                len_i64 = self.new_register()
                # dv_str_len 入参是 LightValue*（需先 _store_dv 取指针）；编码函数仍用 data_ptr(char*)
                self.emit(f'{len_i64} = call i64 @dv_str_len(ptr {obj_slot})')
                len_i32 = self.new_register()
                self.emit(f'{len_i32} = trunc i64 {len_i64} to i32')
                out = self.new_register()
                self.emit(f'{out} = call ptr @dv_sha1(ptr {data_ptr}, i32 {len_i32})')
                return self._create_str_dv(out), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('SHA256', 'sha256', '_sha256'):
            if args:
                obj_slot = self._store_dv(args[0])
                data_ptr = self.new_register()
                self.emit(f'{data_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                len_i64 = self.new_register()
                # dv_str_len 入参是 LightValue*（需先 _store_dv 取指针）；编码函数仍用 data_ptr(char*)
                self.emit(f'{len_i64} = call i64 @dv_str_len(ptr {obj_slot})')
                len_i32 = self.new_register()
                self.emit(f'{len_i32} = trunc i64 {len_i64} to i32')
                out = self.new_register()
                self.emit(f'{out} = call ptr @dv_sha256(ptr {data_ptr}, i32 {len_i32})')
                return self._create_str_dv(out), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        # T7D：SHA512 —— runtime C 层实现（光明缺位移/按位运算符无法在 i64 上
        # 可靠模拟 64 位逻辑右移）。输出 128 位小写十六进制，对拍 hashlib.sha512。
        if name in ('SHA512', 'sha512', '_sha512'):
            if args:
                obj_slot = self._store_dv(args[0])
                data_ptr = self.new_register()
                self.emit(f'{data_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                len_i64 = self.new_register()
                self.emit(f'{len_i64} = call i64 @dv_str_len(ptr {obj_slot})')
                len_i32 = self.new_register()
                self.emit(f'{len_i32} = trunc i64 {len_i64} to i32')
                out = self.new_register()
                self.emit(f'{out} = call ptr @dv_sha512(ptr {data_ptr}, i32 {len_i32})')
                return self._create_str_dv(out), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        # T7D：HMAC_SHA256（密钥, 文本）—— 对齐 哈希.py 语义
        # pbkdf2_hmac('sha256', password=文本, salt=密钥, iterations=1)。
        # runtime dv_pbkdf2_hmac_sha256_1(pw=文本, salt=密钥) 以显式长度
        # 二进制安全构造 HMAC（消息尾含 NUL，strlen 版 sha256 无法对拍）。
        if name in ('HMAC_SHA256', '_hmac_sha256'):
            if len(args) >= 2:
                pw_ptr = self.new_register()
                self.emit(f'{pw_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 3')
                salt_ptr = self.new_register()
                self.emit(f'{salt_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                out = self.new_register()
                self.emit(f'{out} = call ptr @dv_pbkdf2_hmac_sha256_1(ptr {pw_ptr}, ptr {salt_ptr})')
                return self._create_str_dv(out), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('四舍五入', 'round', '_round'):
            # dv_round(result, a)：a 已是整数则原样克隆，否则 f64 四舍五入取整。
            if args:
                res_slot = self._new_dv_slot()
                self.emit(f'call void @dv_null(ptr {res_slot})')
                # dv_round 两参均为 LightValue*；args[0] 是 struct 值，需先落槽取指针
                in_slot = self._store_dv(args[0])
                self.emit(f'call void @dv_round(ptr {res_slot}, ptr {in_slot})')
                res = self._load_dv(res_slot)
                return res, 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('去除空格', 'trim', 'strip', '去除空白', 'str_strip'):
            if args:
                return self._call_dv_func('dv_trim', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('lstrip', '左去除', 'str_lstrip'):
            # R12C（R11A-08）：runtime 无 dv_str_lstrip，reverse 组合链在对象
            # 缓冲机制下结果异常（归 T7）。改为一次性发射 IR 辅助函数
            # _r12c_lstrip（单遍状态机，libc isspace）。
            self._r12c_need_lstrip = True
            if args:
                obj_slot = self._store_dv(args[0])
                res_slot = self._new_dv_slot()
                self.emit(f'call void @_r12c_lstrip(ptr {res_slot}, ptr {obj_slot})')
                return self._load_dv(res_slot), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('每个单词首字母大写', 'title', '词首大写'):
            # R12C（R11A-08）：runtime 无 title/capitalize，发射 IR 辅助函数
            # _r12c_title（单遍状态机，libc isalpha/toupper/tolower），
            # 语义对齐 Python str.title()（非字母重置、字母序列首大余小）。
            self._r12c_need_title = True
            if args:
                obj_slot = self._store_dv(args[0])
                res_slot = self._new_dv_slot()
                self.emit(f'call void @_r12c_title(ptr {res_slot}, ptr {obj_slot})')
                return self._load_dv(res_slot), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('rstrip', '右去除', 'str_rstrip'):
            if len(args) >= 2:
                return self._call_dv_func('dv_str_rstrip', args[0], args[1]), 'dv'
            if args:
                return self._call_dv_func('dv_str_rstrip', args[0],
                                          self._create_str_dv(self.gen_string_constant(" \t\n\r\v\f"))), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('字符串重复', '重复', 'str_repeat', 'repeat'):
            if len(args) >= 2:
                return self._call_dv_func('dv_str_repeat', args[0], args[1]), 'dv'
            return self._create_str_dv(self.gen_string_constant('')), 'dv'

        if name in ('连接路径', 'join_path', 'path_join'):
            if len(args) >= 2:
                return self._call_dv_func('dv_path_join', args[0], args[1]), 'dv'
            return self._create_str_dv(self.gen_string_constant('')), 'dv'

        if name in ('目录名', 'dirname', 'path_dirname'):
            # POSIX dirname（对齐 转译腿 _light_builtin.目录名 = os.path.dirname）
            if args:
                return self._call_dv_func('dv_path_dirname', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant('')), 'dv'

        if name in ('文件名', 'basename', 'path_basename'):
            # POSIX basename（对齐 转译腿 _light_builtin.文件名 = os.path.basename）
            if args:
                return self._call_dv_func('dv_path_basename', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant('')), 'dv'

        if name in ('绝对路径', 'abspath', 'abs_path'):
            # os.path.abspath（相对路径基于 cwd 拼接 + 规范化）
            if args:
                return self._call_dv_func('dv_abspath', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant('')), 'dv'

        if name in ('创建目录', 'mkdir', 'make_dir', 'makedirs'):
            # os.makedirs(path, exist_ok=True)（逐级建父目录，已存在不算错）
            if args:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_makedirs(ptr {path_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('删除目录', 'rmdir', 'remove_dir'):
            # os.rmdir（删除空目录）
            if args:
                path_ptr = self.new_register()
                self.emit(f'{path_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_rmdir(ptr {path_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('字符串包含', 'str_contains', '包含字符串'):
            if len(args) >= 2:
                s0 = self._store_dv(args[0])
                s1 = self._store_dv(args[1])
                r = self.new_register()
                self.emit(f'{r} = call i32 @dv_str_contains(ptr {s0}, ptr {s1})')
                cmp = self.new_register()
                self.emit(f'{cmp} = icmp ne i32 {r}, 0')
                return self._create_bool_dv(cmp), 'dv'
            return self._create_bool_dv('false'), 'dv'

        if name in ('开头', '以开头', 'startswith', 'starts_with', '前缀是'):
            if len(args) >= 2:
                s0 = self._store_dv(args[0])
                s1 = self._store_dv(args[1])
                r = self.new_register()
                self.emit(f'{r} = call i32 @dv_str_starts_with(ptr {s0}, ptr {s1})')
                cmp = self.new_register()
                self.emit(f'{cmp} = icmp ne i32 {r}, 0')
                return self._create_bool_dv(cmp), 'dv'
            return self._create_bool_dv('false'), 'dv'

        if name in ('结尾', '以结尾', 'endswith', 'ends_with', '后缀是'):
            if len(args) >= 2:
                s0 = self._store_dv(args[0])
                s1 = self._store_dv(args[1])
                r = self.new_register()
                self.emit(f'{r} = call i32 @dv_str_ends_with(ptr {s0}, ptr {s1})')
                cmp = self.new_register()
                self.emit(f'{cmp} = icmp ne i32 {r}, 0')
                return self._create_bool_dv(cmp), 'dv'
            return self._create_bool_dv('false'), 'dv'

        if name in ('反向查找', 'rfind', 'str_rfind'):
            if len(args) >= 2:
                s0 = self._store_dv(args[0])
                s1 = self._store_dv(args[1])
                r = self.new_register()
                self.emit(f'{r} = call i64 @dv_str_rfind(ptr {s0}, ptr {s1})')
                return self._create_int_dv(r), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('计数', 'count', 'str_count'):
            if len(args) >= 2:
                s0 = self._store_dv(args[0])
                s1 = self._store_dv(args[1])
                r = self.new_register()
                self.emit(f'{r} = call i64 @dv_str_count(ptr {s0}, ptr {s1})')
                return self._create_int_dv(r), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('替换', 'replace', 'str_replace', '替换字符串'):
            if len(args) >= 3:
                return self._call_dv_func('dv_str_replace', args[0], args[1], args[2]), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('分割', 'split', 'str_split', '分割字符串'):
            if len(args) >= 2:
                return self._call_dv_func('dv_str_split', args[0], args[1]), 'dv'
            if args:
                # R12C（R11A-08）：方法形式 `s.分割()` 无参 → 按空白切分
                # （能力边界：连续空白会产生空段，与 Python str.split() 的
                # 折叠语义不同——运行时折叠归 T7）
                self._r12c_need_split_ws = True
                obj_slot = self._store_dv(args[0])
                res_slot = self._new_dv_slot()
                self.emit(f'call void @_r12c_split_ws(ptr {res_slot}, ptr {obj_slot})')
                return self._load_dv(res_slot), 'dv'
            return self._call_dv_func('dv_list_new'), 'dv'

        if name in ('连接字符串', 'join', 'str_join', 'implode'):
            # T7D：走 dv_list_join(原生 LightValue 列表, 分隔)。旧实现 extractvalue
            # …,3 取 str 字段（列表为 NULL）→ dv_str_join(legacy "list:" 解析器)
            # 恒返空串（T6A-04 根因）。1 参时分隔默认 ""。
            if args:
                if len(args) >= 2:
                    return self._call_dv_func('dv_list_join', args[0], args[1]), 'dv'
                empty_sep = self._create_str_dv(self.gen_string_constant(""))
                return self._call_dv_func('dv_list_join', args[0], empty_sep), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('转布尔', 'to_bool', 'bool'):
            if args:
                return self._call_dv_func('dv_to_bool_val', args[0]), 'dv'
            return self._create_bool_dv('false'), 'dv'

        if name in ('是实例', 'isinstance', '是否实例', '是类实例', 'instance_of'):
            if len(args) >= 2:
                obj_slot = self._store_dv(args[0])
                class_name_ptr = self.new_register()
                self.emit(f'{class_name_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 3')
                result = self.new_register()
                self.emit(f'{result} = call i32 @dv_isinstance(ptr {obj_slot}, ptr {class_name_ptr})')
                cmp = self.new_register()
                self.emit(f'{cmp} = icmp ne i32 {result}, 0')
                return self._create_bool_dv(cmp), 'dv'
            return self._create_bool_dv('false'), 'dv'

        if name in ('取类型', 'type', '获取类型', 'typeof', '类型名', 'type_name', '类型'):
            if args:
                obj_slot = self._store_dv(args[0])
                buf_size = 256
                buf_ptr = self.new_register()
                self.emit(f'{buf_ptr} = alloca [256 x i8]')
                buf_cast = self.new_register()
                self.emit(f'{buf_cast} = getelementptr inbounds [256 x i8], ptr {buf_ptr}, i32 0, i32 0')
                self.emit(f'call void @dv_get_type_name(ptr {obj_slot}, ptr {buf_cast}, i32 {buf_size})')
                return self._create_str_dv(buf_cast), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name == '范围':
            return self._gen_typed_range(args)

        if name in ('list', '列表', '创建列表'):
            return self._gen_typed_list_from_builtin_args(args)

        # 字典操作
        if name in ('dict', '字典', '新建字典', '创建字典', '字典创建'):
            dict_dv = self._call_dv_func('dv_dict_new')
            return dict_dv, 'dv'

        if name in ('字典设置', '字典添加'):
            if len(args) >= 3:
                slot0 = self._store_dv(args[0])
                slot1 = self._store_dv(args[1])
                slot2 = self._store_dv(args[2])
                self.emit(f'call void @dv_dict_set(ptr {slot0}, ptr {slot0}, ptr {slot1}, ptr {slot2})')
                result = self._load_dv(slot0)
                return result, 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('字典获取',):
            if len(args) >= 3:
                # T7D：3 参（带默认值）→ dv_dict_get_def；此前签名收窄只传 2 参、
                # 默认值被静默丢弃（T6A-05 根因）。
                return self._call_dv_func('dv_dict_get_def', args[0], args[1], args[2]), 'dv'
            if len(args) >= 2:
                return self._call_dv_func('dv_dict_get', args[0], args[1]), 'dv'
            return self._call_dv_func('dv_null'), 'dv'

        if name in ('字典包含键', '字典有键'):
            if len(args) >= 2:
                return self._call_dv_func('dv_dict_has', args[0], args[1]), 'dv'
            return self._create_bool_dv('false'), 'dv'

        # T7B：注册 字典删除（runtime dv_dict_remove 早已存在但未注册；供缓存家族
        # 字典化时删除键用，行为对齐 Python dict.pop(key) 的静默缺失语义）。
        if name in ('字典删除', '字典移除'):
            if len(args) >= 2:
                slot0 = self._store_dv(args[0])
                slot1 = self._store_dv(args[1])
                self.emit(f'call void @dv_dict_remove(ptr {slot0}, ptr {slot0}, ptr {slot1})')
                return self._load_dv(slot0), 'dv'
            return self._create_int_dv('0'), 'dv'

        if name in ('字典键列表', '字典键'):
            if args:
                return self._call_dv_func('dv_dict_keys', args[0]), 'dv'
            return self._call_dv_func('dv_list_new'), 'dv'

        # 可空类型操作
        if name in ('是空', 'is_null', 'null?'):
            if args:
                slot = self._store_dv(args[0])
                result = self.new_register()
                self.emit(f'{result} = call i32 @dv_is_null(ptr {slot})')
                return self._create_bool_dv(result), 'dv'
            return self._create_bool_dv('true'), 'dv'

        if name in ('空合并', 'null_coalesce', '??'):
            if len(args) >= 2:
                v_slot = self._store_dv(args[0])
                default_slot = self._store_dv(args[1])
                result_slot = self._new_dv_slot()
                self.emit(f'call void @dv_null_coalesce(ptr {result_slot}, ptr {v_slot}, ptr {default_slot})')
                return self._load_dv(result_slot), 'dv'
            return self._call_dv_func('dv_null'), 'dv'

        if name in ('安全获取', 'safe_get', '?.'):
            if len(args) >= 2:
                obj_slot = self._store_dv(args[0])
                attr_slot = self._store_dv(args[1])
                result_slot = self._new_dv_slot()
                self.emit(f'call void @dv_safe_get(ptr {result_slot}, ptr {obj_slot}, ptr {attr_slot})')
                return self._load_dv(result_slot), 'dv'
            return self._call_dv_func('dv_null'), 'dv'

        # ---- 网络/Socket 内置函数 (Task B1) ----
        if name in ('创建socket', 'socket_create'):
            if len(args) >= 2:
                d_i64 = self.new_register()
                self.emit(f'{d_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                d_i32 = self.new_register()
                self.emit(f'{d_i32} = trunc i64 {d_i64} to i32')
                t_i64 = self.new_register()
                self.emit(f'{t_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                t_i32 = self.new_register()
                self.emit(f'{t_i32} = trunc i64 {t_i64} to i32')
                fd = self.new_register()
                self.emit(f'{fd} = call i32 @dv_socket_create(i32 {d_i32}, i32 {t_i32})')
                fd_i64 = self.new_register()
                self.emit(f'{fd_i64} = sext i32 {fd} to i64')
                return self._create_int_dv(fd_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('连接socket', 'socket_connect'):
            if len(args) >= 3:
                fd_i64 = self.new_register()
                self.emit(f'{fd_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                fd_i32 = self.new_register()
                self.emit(f'{fd_i32} = trunc i64 {fd_i64} to i32')
                host_ptr = self._extract_ptr_from_dv(args[1])
                port_i64 = self.new_register()
                self.emit(f'{port_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[2]}, 1')
                port_i32 = self.new_register()
                self.emit(f'{port_i32} = trunc i64 {port_i64} to i32')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_socket_connect(i32 {fd_i32}, ptr {host_ptr}, i32 {port_i32})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('发送socket', 'socket_send'):
            if len(args) >= 2:
                fd_i64 = self.new_register()
                self.emit(f'{fd_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                fd_i32 = self.new_register()
                self.emit(f'{fd_i32} = trunc i64 {fd_i64} to i32')
                data_ptr = self._extract_ptr_from_dv(args[1])
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_socket_send(i32 {fd_i32}, ptr {data_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('接收socket', 'socket_recv'):
            if len(args) >= 2:
                fd_i64 = self.new_register()
                self.emit(f'{fd_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                fd_i32 = self.new_register()
                self.emit(f'{fd_i32} = trunc i64 {fd_i64} to i32')
                mb_i64 = self.new_register()
                self.emit(f'{mb_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                mb_i32 = self.new_register()
                self.emit(f'{mb_i32} = trunc i64 {mb_i64} to i32')
                result_slot = self._new_dv_slot()
                self.emit(f'call void @dv_socket_recv(ptr {result_slot}, i32 {fd_i32}, i32 {mb_i32})')
                return self._load_dv(result_slot), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('关闭socket', 'socket_close'):
            if args:
                fd_i64 = self.new_register()
                self.emit(f'{fd_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                fd_i32 = self.new_register()
                self.emit(f'{fd_i32} = trunc i64 {fd_i64} to i32')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_socket_close(i32 {fd_i32})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('socket错误', 'socket_last_error'):
            err_ptr = self.new_register()
            self.emit(f'{err_ptr} = call ptr @dv_socket_last_error()')
            return self._create_str_dv(err_ptr), 'dv'

        if name in ('socket错误码', 'socket_last_error_code'):
            ret = self.new_register()
            self.emit(f'{ret} = call i32 @dv_socket_last_error_code()')
            ret_i64 = self.new_register()
            self.emit(f'{ret_i64} = sext i32 {ret} to i64')
            return self._create_int_dv(ret_i64), 'dv'

        # ---- IO 多路复用内置函数 (Task B2) ----
        if name in ('创建poller', 'poller_create'):
            poller_ptr = self.new_register()
            self.emit(f'{poller_ptr} = call ptr @dv_poller_create()')
            # 用 type=8 REF 存储 poller 指针在 str 字段
            slot = self._new_dv_slot()
            # 直接构造: type=8, str=poller_ptr
            self.emit(f'call void @dv_int(ptr {slot}, i64 0)')  # 先初始化
            # 内联设置 type=8 和 str 字段
            t_ptr = self.new_register()
            self.emit(f'{t_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 0')
            self.emit(f'store i32 8, ptr {t_ptr}')
            s_ptr = self.new_register()
            self.emit(f'{s_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 3')
            self.emit(f'store ptr {poller_ptr}, ptr {s_ptr}')
            return self._load_dv(slot), 'dv'

        if name in ('销毁poller', 'poller_destroy'):
            if args:
                p_ptr = self._extract_ptr_from_dv(args[0])
                self.emit(f'call void @dv_poller_destroy(ptr {p_ptr})')
            return self._create_int_dv('0'), 'dv'

        if name in ('注册poller', 'poller_register'):
            if len(args) >= 3:
                p_ptr = self._extract_ptr_from_dv(args[0])
                fd_i64 = self.new_register()
                self.emit(f'{fd_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                fd_i32 = self.new_register()
                self.emit(f'{fd_i32} = trunc i64 {fd_i64} to i32')
                ev_i64 = self.new_register()
                self.emit(f'{ev_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[2]}, 1')
                ev_i32 = self.new_register()
                self.emit(f'{ev_i32} = trunc i64 {ev_i64} to i32')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_poller_register(ptr {p_ptr}, i32 {fd_i32}, i32 {ev_i32})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('poller_wait',):
            if len(args) >= 2:
                p_ptr = self._extract_ptr_from_dv(args[0])
                to_i64 = self.new_register()
                self.emit(f'{to_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                to_i32 = self.new_register()
                self.emit(f'{to_i32} = trunc i64 {to_i64} to i32')
                fds_arr = self.new_register()
                self.emit(f'{fds_arr} = alloca i32, i32 256')
                ev_arr = self.new_register()
                self.emit(f'{ev_arr} = alloca i32, i32 256')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_poller_wait(ptr {p_ptr}, i32 {to_i32}, ptr {fds_arr}, ptr {ev_arr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        # ---- 事件循环内置函数 (Task B3) ----
        if name in ('运行事件循环', 'run_event_loop'):
            self.emit(f'call void @dv_scheduler_run_event_loop()')
            return self._create_int_dv('0'), 'dv'

        if name in ('睡眠', 'sleep'):
            if args:
                ms_i64 = self.new_register()
                self.emit(f'{ms_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                ms_i32 = self.new_register()
                self.emit(f'{ms_i32} = trunc i64 {ms_i64} to i32')
                if self._in_coroutine:
                    point_num = self._coro_resume_point
                    self._coro_resume_point += 1
                    resume_label = self._coro_resume_labels.get(point_num + 1)
                    rp_ptr = self.new_register()
                    self.emit(f'{rp_ptr} = getelementptr inbounds i8, ptr %coro, i32 4')
                    self.emit(f'store i32 {point_num + 1}, ptr {rp_ptr}')
                    self.emit(f'call void @dv_coro_sleep(ptr %coro, i32 {ms_i32})')
                    self.emit(f'ret void')
                    if resume_label:
                        self.emit(f'{resume_label}:')
                    else:
                        fallback = self.new_label(f'sleep_resume_{point_num}')
                        self.emit(f'{fallback}:')
                else:
                    self.emit(f'call void @dv_platform_sleep(i32 {ms_i32})')
            return self._create_int_dv('0'), 'dv'

        if name in ('await_io',):
            if len(args) >= 2:
                fd_i64 = self.new_register()
                self.emit(f'{fd_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                fd_i32 = self.new_register()
                self.emit(f'{fd_i32} = trunc i64 {fd_i64} to i32')
                ev_i64 = self.new_register()
                self.emit(f'{ev_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                ev_i32 = self.new_register()
                self.emit(f'{ev_i32} = trunc i64 {ev_i64} to i32')
                if self._in_coroutine:
                    point_num = self._coro_resume_point
                    self._coro_resume_point += 1
                    resume_label = self._coro_resume_labels.get(point_num + 1)
                    rp_ptr = self.new_register()
                    self.emit(f'{rp_ptr} = getelementptr inbounds i8, ptr %coro, i32 4')
                    self.emit(f'store i32 {point_num + 1}, ptr {rp_ptr}')
                    self.emit(f'call void @dv_coro_await_io(ptr %coro, i32 {fd_i32}, i32 {ev_i32})')
                    self.emit(f'ret void')
                    if resume_label:
                        self.emit(f'{resume_label}:')
                    else:
                        fallback = self.new_label(f'io_resume_{point_num}')
                        self.emit(f'{fallback}:')
            return self._create_int_dv('0'), 'dv'

        # ---- 原生 TLS 内置函数 (Task B2-4) ----
        # 语义与 socket 家族对齐：句柄用 type=8 REF 装指针，返回码走 INT，
        # 收数据走 STR。握手返回 0=完成 / 1=WANT_READ / 2=WANT_WRITE / -1=错误，
        # 配合 `等待事件tls` + `await_io` 就能在事件循环里非阻塞握手。
        if name in ('包装tls', 'tls_wrap'):
            if len(args) >= 2:
                fd_i64 = self.new_register()
                self.emit(f'{fd_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 1')
                fd_i32 = self.new_register()
                self.emit(f'{fd_i32} = trunc i64 {fd_i64} to i32')
                host_ptr = self._extract_ptr_from_dv(args[1])
                tls_ptr = self.new_register()
                self.emit(f'{tls_ptr} = call ptr @dv_tls_wrap(i32 {fd_i32}, ptr {host_ptr})')
                slot = self._new_dv_slot()
                self.emit(f'call void @dv_int(ptr {slot}, i64 0)')
                t_ptr = self.new_register()
                self.emit(f'{t_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 0')
                self.emit(f'store i32 8, ptr {t_ptr}')
                s_ptr = self.new_register()
                self.emit(f'{s_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 3')
                self.emit(f'store ptr {tls_ptr}, ptr {s_ptr}')
                return self._load_dv(slot), 'dv'
            return self._create_int_dv('-1'), 'dv'

        _tls_int_unary = {
            ('握手tls', 'tls_handshake'): 'dv_tls_handshake',
            ('等待事件tls', 'tls_want_event'): 'dv_tls_want_event',
            ('就绪tls', 'tls_is_ready'): 'dv_tls_is_ready',
            ('冲刷tls', 'tls_flush'): 'dv_tls_flush_public',
        }
        for _names, _cfunc in _tls_int_unary.items():
            if name in _names:
                if args:
                    t_ptr = self._extract_ptr_from_dv(args[0])
                    ret = self.new_register()
                    self.emit(f'{ret} = call i32 @{_cfunc}(ptr {t_ptr})')
                    ret_i64 = self.new_register()
                    self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                    return self._create_int_dv(ret_i64), 'dv'
                return self._create_int_dv('-1'), 'dv'

        if name in ('发送tls', 'tls_send'):
            if len(args) >= 2:
                t_ptr = self._extract_ptr_from_dv(args[0])
                data_ptr = self._extract_ptr_from_dv(args[1])
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_tls_send(ptr {t_ptr}, ptr {data_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('发送tls长度', 'tls_send_n'):
            """带长度的 TLS 发送：可发含 NUL 字节的二进制数据"""
            if len(args) >= 3:
                t_ptr = self._extract_ptr_from_dv(args[0])
                data_ptr = self._extract_ptr_from_dv(args[1])
                len_i64 = self.new_register()
                self.emit(f'{len_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[2]}, 1')
                len_i32 = self.new_register()
                self.emit(f'{len_i32} = trunc i64 {len_i64} to i32')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_tls_send_n(ptr {t_ptr}, ptr {data_ptr}, i32 {len_i32})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('接收tls', 'tls_recv'):
            if len(args) >= 2:
                t_ptr = self._extract_ptr_from_dv(args[0])
                mb_i64 = self.new_register()
                self.emit(f'{mb_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                mb_i32 = self.new_register()
                self.emit(f'{mb_i32} = trunc i64 {mb_i64} to i32')
                result_slot = self._new_dv_slot()
                self.emit(f'call void @dv_tls_recv(ptr {result_slot}, ptr {t_ptr}, i32 {mb_i32})')
                return self._load_dv(result_slot), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('接收状态tls', 'tls_recv_status'):
            """查询最近一次 dv_tls_recv 的状态：0=有数据 / 1=WANT_READ / -1=ERROR / -2=CLOSED"""
            if args:
                t_ptr = self._extract_ptr_from_dv(args[0])
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_tls_recv_status(ptr {t_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('释放tls', 'tls_free'):
            if args:
                t_ptr = self._extract_ptr_from_dv(args[0])
                self.emit(f'call void @dv_tls_free(ptr {t_ptr})')
            return self._create_int_dv('0'), 'dv'

        if name in ('校验tls', 'tls_set_verify'):
            if len(args) >= 2:
                t_ptr = self._extract_ptr_from_dv(args[0])
                en_i64 = self.new_register()
                self.emit(f'{en_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                en_i32 = self.new_register()
                self.emit(f'{en_i32} = trunc i64 {en_i64} to i32')
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_tls_set_verify(ptr {t_ptr}, i32 {en_i32})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('信任证书tls', 'tls_add_trusted_cert'):
            if args:
                path_ptr = self._extract_ptr_from_dv(args[0])
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_tls_add_trusted_cert_file(ptr {path_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'

        if name in ('错误tls', 'tls_last_error'):
            err_ptr = self.new_register()
            self.emit(f'{err_ptr} = call ptr @dv_tls_last_error()')
            return self._create_str_dv(err_ptr), 'dv'

        if name in ('poller错误', 'poller_last_error'):
            err_ptr = self.new_register()
            self.emit(f'{err_ptr} = call ptr @dv_poller_last_error()')
            return self._create_str_dv(err_ptr), 'dv'

        if name in ('poller后端', 'poller_backend'):
            b_ptr = self.new_register()
            self.emit(f'{b_ptr} = call ptr @dv_poller_backend()')
            return self._create_str_dv(b_ptr), 'dv'

        if name in ('poller计数', 'poller_count'):
            if args:
                p_ptr = self._extract_ptr_from_dv(args[0])
                ret = self.new_register()
                self.emit(f'{ret} = call i32 @dv_poller_count(ptr {p_ptr})')
                ret_i64 = self.new_register()
                self.emit(f'{ret_i64} = sext i32 {ret} to i64')
                return self._create_int_dv(ret_i64), 'dv'
            return self._create_int_dv('-1'), 'dv'
        return None

    def _gen_typed_list_from_builtin_args(self, args: List[str]) -> Tuple[str, str]:
        """从内置函数调用参数创建列表"""
        list_dv = self._call_dv_func('dv_list_new')
        if not args:
            return list_dv, 'dv'
        
        list_slot = self._new_dv_slot()
        self.emit(f'store {LIGHTVALUE_STRUCT} {list_dv}, ptr {list_slot}')
        
        for arg in args:
            cur_list = self.new_register()
            self.emit(f'{cur_list} = load {LIGHTVALUE_STRUCT}, ptr {list_slot}')
            new_list = self._call_dv_func('dv_list_append', cur_list, arg)
            self.emit(f'store {LIGHTVALUE_STRUCT} {new_list}, ptr {list_slot}')
        
        result = self.new_register()
        self.emit(f'{result} = load {LIGHTVALUE_STRUCT}, ptr {list_slot}')
        return result, 'dv'

    def _gen_typed_range(self, args: List[str]) -> Tuple[str, str]:
        """生成范围列表"""
        start_dv = args[0] if args else self._create_int_dv('1')
        end_dv = args[1] if len(args) > 1 else self._create_int_dv('10')

        # 提取数值
        start_i64 = self.new_register()
        end_i64 = self.new_register()
        self.emit(f'{start_i64} = extractvalue {LIGHTVALUE_STRUCT} {start_dv}, 1')
        self.emit(f'{end_i64} = extractvalue {LIGHTVALUE_STRUCT} {end_dv}, 1')

        list_dv = self._call_dv_func('dv_list_new')
        # 使用 alloca 保存列表
        list_slot = self._new_dv_slot()
        self.emit(f'store {LIGHTVALUE_STRUCT} {list_dv}, ptr {list_slot}')

        idx_slot = self._gen_alloca('i64')
        self.emit(f'store i64 {start_i64}, ptr {idx_slot}')

        range_cond = self.new_label('range_cond')
        range_body = self.new_label('range_body')
        range_end = self.new_label('range_end')
        self.emit(f'br label %{range_cond}')

        self.emit(f'{range_cond}:')
        cur = self.new_register()
        self.emit(f'{cur} = load i64, ptr {idx_slot}')
        cmp = self.new_register()
        self.emit(f'{cmp} = icmp sle i64 {cur}, {end_i64}')
        self.emit(f'br i1 {cmp}, label %{range_body}, label %{range_end}')

        self.emit(f'{range_body}:')
        cur_val = self.new_register()
        self.emit(f'{cur_val} = load i64, ptr {idx_slot}')
        elem_dv = self._create_int_dv(cur_val)
        list_val_load = self.new_register()
        self.emit(f'{list_val_load} = load {LIGHTVALUE_STRUCT}, ptr {list_slot}')
        new_list_dv = self._call_dv_func('dv_list_append', list_val_load, elem_dv)
        self.emit(f'store {LIGHTVALUE_STRUCT} {new_list_dv}, ptr {list_slot}')
        next_i = self.new_register()
        self.emit(f'{next_i} = add i64 {cur_val}, 1')
        self.emit(f'store i64 {next_i}, ptr {idx_slot}')
        self.emit(f'br label %{range_cond}')

        self.emit(f'{range_end}:')
        final = self.new_register()
        self.emit(f'{final} = load {LIGHTVALUE_STRUCT}, ptr {list_slot}')
        return final, 'dv'

    def _gen_typed_property_access(self, expr) -> Tuple[str, str]:
        """处理 obj.成员 (属性访问表达式)"""
        obj_dv, _ = self._gen_expression(expr.obj)
        member = expr.property_name
        if member == '长度' or member == 'len' or member == '大小' or member == 'size':
            slot = self._store_dv(obj_dv)
            i64_val = self.new_register()
            self.emit(f'{i64_val} = call i64 @dv_len(ptr {slot})')
            return self._create_int_dv(i64_val), 'dv'
        obj_slot = self._store_dv(obj_dv)
        member_reg = self.gen_string_constant(member)
        result_slot = self._new_dv_slot()
        self.emit(f'call void @dv_class_get_member(ptr {result_slot}, ptr {obj_slot}, ptr {member_reg})')
        return self._load_dv(result_slot), 'dv'

    def _recv_is_field(self, prop) -> bool:
        """接收者是否是需要写回的实例字段。

        light parser 把属性链拍平：
        - `己.数据` 作为接收者 → Identifier('己.数据')（带点）
        - `己.数据` 作为单级 PropertyAccess → PropertyAccess(obj=Identifier('己'), '数据')
        两者都表示「实例字段」，需要把 realloc 后的对象写回字段。
        """
        recv = prop.obj
        if isinstance(recv, ast.Identifier):
            # 带点（己.数据）= 实例字段；无点（栈）= 局部变量参数。
            # 两者都是可写回接收者：_persist_to_receiver 的情况一/二分别处理，
            # 不写回则跨调用累积丢失（数据结构轻量 入栈/出栈 的 栈 参数根因）。
            return True
        if isinstance(recv, ast.PropertyAccess) and isinstance(recv.obj, ast.Identifier):
            return True
        return False

    def _persist_to_receiver(self, prop, value_reg: str) -> None:
        """方法调用后，把被重分配（realloc）的接收者写回到它的来源槽位。

        light 的 parser 把属性链拍平：
        - 单级变量（如 `局`）→ Identifier（无点）
        - 单级字段（如 `己.数据`）→ Identifier（带点，形如 `己.数据`）
        - 方法调用接收者 `己.方法()` → PropertyAccess(obj=Identifier('己'), property_name='方法')
        - 字段方法 `己.数据.追加()` → PropertyAccess(obj=Identifier('己.数据'), property_name='追加')

        本方法覆盖：
        - 单级变量：写回变量（set_var）。
        - 单级字段（带点 Identifier / 单级 PropertyAccess）：dv_class_set_member 写回
          字段并刷新属主（己/局），否则跨调用累积丢失（SSE 空行边界 0 事件根因）。
        其它形式（嵌套字段、表达式结果等）无法写回，跳过。

        prop 为 FunctionCall 的 name（PropertyAccess）；value_reg 为更新后的
        接收者 dv 寄存器（可能已被 realloc）。
        """
        recv = prop.obj

        # 情况一：单级变量（无点 Identifier），如 `局`
        if isinstance(recv, ast.Identifier) and '.' not in recv.name:
            obj_name = recv.name
            set_name = '己' if (self._method_result_ptr is not None and obj_name in ('self', '己')) else obj_name
            self.set_var(set_name, value_reg)
            return

        # 情况二：单级字段（parser 拍平为带点 Identifier，如 `己.数据`）
        if isinstance(recv, ast.Identifier) and '.' in recv.name:
            owner_name, field_name = recv.name.split('.', 1)
            if '.' in field_name:
                return  # 暂不支持更深嵌套（己.数据.子字段）
            set_owner_name = '己' if (self._method_result_ptr is not None and owner_name in ('self', '己')) else owner_name
            owner_dv = self.get_var(set_owner_name)
            if owner_dv is None:
                owner_dv, _ = self._gen_expression(ast.Identifier(name=owner_name))
            owner_slot = self._store_dv(owner_dv)
            member_reg = self.gen_string_constant(field_name)
            value_slot = self._store_dv(value_reg)
            self.emit(f'call void @dv_class_set_member(ptr {owner_slot}, ptr {member_reg}, ptr {value_slot})')
            updated_owner = self._load_dv(owner_slot)
            self.set_var(set_owner_name, updated_owner)
            return

        # 情况三：单级字段以 PropertyAccess 形式（如 `己.数据`）—— 备用分支
        if isinstance(recv, ast.PropertyAccess) and isinstance(recv.obj, ast.Identifier):
            owner_name = recv.obj.name
            field_name = recv.property_name
            set_owner_name = '己' if (self._method_result_ptr is not None and owner_name in ('self', '己')) else owner_name
            owner_dv = self.get_var(set_owner_name)
            if owner_dv is None:
                owner_dv, _ = self._gen_expression(recv.obj)
            owner_slot = self._store_dv(owner_dv)
            member_reg = self.gen_string_constant(field_name)
            value_slot = self._store_dv(value_reg)
            self.emit(f'call void @dv_class_set_member(ptr {owner_slot}, ptr {member_reg}, ptr {value_slot})')
            updated_owner = self._load_dv(owner_slot)
            self.set_var(set_owner_name, updated_owner)
            return

        # 其它来源（嵌套属性、函数调用结果等）无法写回，跳过
        return

    def _gen_typed_method_call(self, expr: ast.FunctionCall) -> Tuple[str, str]:
        """处理 obj.方法(args) - FunctionCall with PropertyAccess name"""
        prop = expr.name  # PropertyAccess
        method_name = prop.property_name

        # T6B：sys.stderr.write(文本) / sys.stderr.flush() 链级改写。
        # 事件总线（A3-7）在错误隔离路径写 `sys.stderr.write(...)。sys.stderr.flush()。`
        # —— Python 腿绑定真 sys（对象属性链天然成立）；原生腿的模块只有「段落」
        # 没有属性值，`sys.stderr` 无法表达。这里在**求值接收者之前**拦截这条链：
        #   write(文本) -> dv_println（原生无 stderr 通道，回落 stdout，边界见交付报告）
        #   flush()     -> no-op（dv_println 无缓冲）
        if (isinstance(prop.obj, ast.PropertyAccess)
                and isinstance(prop.obj.obj, ast.Identifier)
                and prop.obj.obj.name == 'sys'
                and prop.obj.property_name == 'stderr'
                and method_name in ('write', 'flush')):
            if method_name == 'write' and expr.arguments:
                arg_dv, _ = self._gen_expression(expr.arguments[0])
                slot = self._store_dv(arg_dv)
                self.emit(f'call void @dv_println(ptr {slot})')
            return self._create_int_dv('0'), 'dv'

        # 检测是否是 super 调用（父.方法() 或 super.方法()）
        is_super_call = False
        if isinstance(prop.obj, ast.Identifier):
            obj_name = prop.obj.name
            if obj_name in ('super()', '父', 'super'):
                is_super_call = True
        
        if is_super_call and self._current_class is not None:
            # super 调用：使用 dv_call_super_method
            self_dv = self.get_var('己')
            if self_dv is None:
                return self._create_int_dv('0'), 'dv'
            
            obj_slot = self._self_lvalue_slot()
            method_name_reg = self.gen_string_constant(method_name)
            class_name_reg = self.gen_string_constant(self._current_class)
            
            num_args = len(expr.arguments)
            result_slot = self._new_dv_slot()
            num_args_i32 = self.new_register()
            self.emit(f'{num_args_i32} = add i32 0, {num_args}')
            
            if num_args == 0:
                self.emit(f'call void @dv_call_super_method(ptr {result_slot}, ptr {obj_slot}, ptr {class_name_reg}, ptr {method_name_reg}, ptr null, i32 {num_args_i32})')
            else:
                stack_save = self.new_register()
                self.emit(f'{stack_save} = call ptr @llvm.stacksave()')
                args_array = self.new_register()
                self.emit(f'{args_array} = alloca {LIGHTVALUE_STRUCT}, i32 {num_args}')
                
                for i, arg in enumerate(expr.arguments):
                    arg_dv, _ = self._gen_expression(arg)
                    arg_elem_ptr = self.new_register()
                    self.emit(f'{arg_elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {args_array}, i32 {i}')
                    self.emit(f'store {LIGHTVALUE_STRUCT} {arg_dv}, ptr {arg_elem_ptr}')
                
                self.emit(f'call void @dv_call_super_method(ptr {result_slot}, ptr {obj_slot}, ptr {class_name_reg}, ptr {method_name_reg}, ptr {args_array}, i32 {num_args_i32})')
                self.emit(f'call void @llvm.stackrestore(ptr {stack_save})')
            
            # 更新己变量
            updated_obj = self._load_dv(obj_slot)
            self.set_var('己', updated_obj)
            
            return self._load_dv(result_slot), 'dv'
        
        # _light_builtin 模块点访问：`_light_builtin.删除文件(路径)` 按名转发内置
        # （对齐转译腿 `_light_builtin.删除文件` -> `删除文件` 语义）。不把
        # `_light_builtin` 当接收者传参——它在原生腿只是模块名，求值成字符串会让
        # 内置分支把第一个参数取错（试图删除名为 "_light_builtin" 的文件）。
        if isinstance(prop.obj, ast.Identifier) and prop.obj.name == '_light_builtin':
            args_dv = []
            kw_values = {}
            for arg in expr.arguments:
                if isinstance(arg, ast.KeywordArg):
                    kw_values[arg.name] = self._gen_expression(arg.value)[0]
                else:
                    args_dv.append(self._gen_expression(arg)[0])
            if kw_values:
                args_dv = self._merge_kwargs(method_name, args_dv, kw_values)
            builtin_result = self._gen_typed_builtin(method_name, args_dv)
            if builtin_result is not None:
                return builtin_result
            self._reject_unknown_call(method_name, expr, kind='模块点访问')

        obj_dv, _ = self._gen_expression(prop.obj)

        # 检查是否是 类名.方法名() 形式的调用（通过类名调用类方法/静态方法）
        if isinstance(prop.obj, ast.Identifier):
            obj_name = prop.obj.name
            if obj_name in self._classes:
                # 这是通过类名调用方法，先判断方法类型
                class_name = obj_name
                cls_def = self._classes[class_name]
                method_type = 'instance'
                # 在类的方法中查找
                for method in getattr(cls_def, 'methods', []) or []:
                    if method.name == method_name:
                        method_type = self._get_method_type(method)
                        break
                
                class_name_reg = self.gen_string_constant(class_name)
                method_name_reg = self.gen_string_constant(method_name)
                
                num_args = len(expr.arguments)
                result_slot = self._new_dv_slot()
                num_args_i32 = self.new_register()
                self.emit(f'{num_args_i32} = add i32 0, {num_args}')
                
                if num_args == 0:
                    if method_type == 'static':
                        self.emit(f'call void @dv_call_static_method(ptr {result_slot}, ptr {class_name_reg}, ptr {method_name_reg}, ptr null, i32 {num_args_i32})')
                    else:
                        self.emit(f'call void @dv_call_class_method(ptr {result_slot}, ptr {class_name_reg}, ptr {method_name_reg}, ptr null, i32 {num_args_i32})')
                else:
                    stack_save = self.new_register()
                    self.emit(f'{stack_save} = call ptr @llvm.stacksave()')
                    args_array = self.new_register()
                    self.emit(f'{args_array} = alloca {LIGHTVALUE_STRUCT}, i32 {num_args}')
                    
                    for i, arg in enumerate(expr.arguments):
                        arg_dv, _ = self._gen_expression(arg)
                        arg_elem_ptr = self.new_register()
                        self.emit(f'{arg_elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {args_array}, i32 {i}')
                        self.emit(f'store {LIGHTVALUE_STRUCT} {arg_dv}, ptr {arg_elem_ptr}')
                    
                    if method_type == 'static':
                        self.emit(f'call void @dv_call_static_method(ptr {result_slot}, ptr {class_name_reg}, ptr {method_name_reg}, ptr {args_array}, i32 {num_args_i32})')
                    else:
                        self.emit(f'call void @dv_call_class_method(ptr {result_slot}, ptr {class_name_reg}, ptr {method_name_reg}, ptr {args_array}, i32 {num_args_i32})')
                    
                    self.emit(f'call void @llvm.stackrestore(ptr {stack_save})')
                
                return self._load_dv(result_slot), 'dv'

        # 模块名.段落名(...) —— 模块级导入后通过模块名调用段函数。
        # 多模块编译时所有段都在同一个 codegen 中，直接分派到 _seg_f*，
        # 不走 dv_call_method（运行时无法解析段函数名，返回 null）。
        # (R10-11a 打回修复 f598a7b2，此处分派未合入 main，一并补回)
        if isinstance(prop.obj, ast.Identifier):
            obj_name = prop.obj.name
            # T9A：模块名.段落名 调用时，按 obj_name 作为模块名查找段定义
            if obj_name in self._imported_modules and self._seg_reg_key(method_name, obj_name) in self._segments:
                # 临时切换当前模块以解析到目标模块的段
                _prev = self._current_module
                self._current_module = obj_name
                try:
                    return self._gen_typed_segment_call(method_name, [
                        self._gen_expression(a)[0] for a in expr.arguments
                    ])
                finally:
                    self._current_module = _prev

        # 先检查是否是内置方法（列表、字符串等）
        # 内置方法调用：把对象作为第一个参数传给内置函数
        args_dv = [obj_dv]
        kw_values = {}
        for arg in expr.arguments:
            if isinstance(arg, ast.KeywordArg):
                kw_values[arg.name] = self._gen_expression(arg.value)[0]
            else:
                args_dv.append(self._gen_expression(arg)[0])
        if kw_values:
            args_dv = self._merge_kwargs(method_name, args_dv, kw_values)

        # 尝试使用内置函数处理
        builtin_result = self._gen_typed_builtin(method_name, args_dv)
        if builtin_result is not None:
            result_reg, _ = builtin_result
            # 内置 mutating 方法（追加/插入/删除/设置…）会把接收者 realloc 成新对象
            # 并以返回值给出。若接收者是实例字段（己.数据），必须把新对象写回字段，
            # 否则跨调用累积丢失（SSE 空行边界产出 0 事件的根因）。
            mutating_methods = {'追加', 'append', '清空', 'clear', '设置', 'set', '插入', 'insert', '删除', 'remove', '弹出', 'pop'}
            if method_name in mutating_methods and self._recv_is_field(prop):
                self._persist_to_receiver(prop, result_reg)
            return result_reg, 'dv'

        # 否则使用 dv_call_method 调用类方法
        # 己/self 方法调用：直接取接收者 lvalue 槽位，避免复制出共享缓冲的副本
        # 导致被调方法内 dv_class_set_member 释放后原 self 悬空（use-after-free）。
        if isinstance(prop.obj, ast.Identifier) and prop.obj.name in ('己', 'self'):
            obj_slot = self._self_lvalue_slot()
        else:
            obj_slot = self._store_dv(obj_dv)
        method_name_reg = self.gen_string_constant(method_name)
        
        num_args = len(expr.arguments)
        result_slot = self._new_dv_slot()
        num_args_i32 = self.new_register()
        self.emit(f'{num_args_i32} = add i32 0, {num_args}')
        
        if num_args == 0:
            self.emit(f'call void @dv_call_method(ptr {result_slot}, ptr {obj_slot}, ptr {method_name_reg}, ptr null, i32 {num_args_i32})')
        else:
            stack_save = self.new_register()
            self.emit(f'{stack_save} = call ptr @llvm.stacksave()')
            args_array = self.new_register()
            self.emit(f'{args_array} = alloca {LIGHTVALUE_STRUCT}, i32 {num_args}')
            
            for i, arg in enumerate(expr.arguments):
                arg_dv, _ = self._gen_expression(arg)
                arg_elem_ptr = self.new_register()
                self.emit(f'{arg_elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {args_array}, i32 {i}')
                self.emit(f'store {LIGHTVALUE_STRUCT} {arg_dv}, ptr {arg_elem_ptr}')
            
            self.emit(f'call void @dv_call_method(ptr {result_slot}, ptr {obj_slot}, ptr {method_name_reg}, ptr {args_array}, i32 {num_args_i32})')
            self.emit(f'call void @llvm.stackrestore(ptr {stack_save})')
        
        # dv_call_method 会就地重分配接收者缓冲，obj_slot 即更新后的接收者。
        # 把其写回到来源（局部变量 或 实例字段）；非 lvalue 来源则跳过。
        self._persist_to_receiver(prop, self._load_dv(obj_slot))

        return self._load_dv(result_slot), 'dv'

    def _gen_self_method_call(self, method_name: str, args: List[str]) -> Tuple[str, str]:
        """方法内部己.方法名(...) —— 对己对象调方法（dv_call_method）。

        与 _gen_typed_method_call 的通用分支共用同一套发射逻辑；调用方保证
        self._method_result_ptr 非空且 己 槽位存在。args 已经是求值后的 dv 寄存器。
        """
        self_dv = self.get_var('己')
        obj_slot = self._self_lvalue_slot()
        method_name_reg = self.gen_string_constant(method_name)

        num_args = len(args)
        result_slot = self._new_dv_slot()
        num_args_i32 = self.new_register()
        self.emit(f'{num_args_i32} = add i32 0, {num_args}')

        if num_args == 0:
            self.emit(f'call void @dv_call_method(ptr {result_slot}, ptr {obj_slot}, ptr {method_name_reg}, ptr null, i32 {num_args_i32})')
        else:
            stack_save = self.new_register()
            self.emit(f'{stack_save} = call ptr @llvm.stacksave()')
            args_array = self.new_register()
            self.emit(f'{args_array} = alloca {LIGHTVALUE_STRUCT}, i32 {num_args}')

            for i, arg_dv in enumerate(args):
                arg_elem_ptr = self.new_register()
                self.emit(f'{arg_elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {args_array}, i32 {i}')
                self.emit(f'store {LIGHTVALUE_STRUCT} {arg_dv}, ptr {arg_elem_ptr}')

            self.emit(f'call void @dv_call_method(ptr {result_slot}, ptr {obj_slot}, ptr {method_name_reg}, ptr {args_array}, i32 {num_args_i32})')
            self.emit(f'call void @llvm.stackrestore(ptr {stack_save})')

        # dv_call_method 会重分配对象缓冲，写回己槽位
        updated_obj = self._load_dv(obj_slot)
        self.set_var('己', updated_obj)

        return self._load_dv(result_slot), 'dv'

    def _gen_typed_class_instantiation(self, expr) -> Tuple[str, str]:
        """生成类实例化 new ClassName(args)"""
        class_name = expr.class_name if hasattr(expr, 'class_name') else str(getattr(expr, 'name', 'object'))
        if class_name == '列表' or class_name == 'list':
            return self._call_dv_func('dv_list_new'), 'dv'
        if class_name == '字典' or class_name == 'dict':
            return self._call_dv_func('dv_dict_new'), 'dv'
        
        name_reg = self.gen_string_constant(class_name)
        result_slot = self._new_dv_slot()
        self.emit(f'call void @dv_class_new_named(ptr {result_slot}, ptr {name_reg})')

        # 检测构造函数：原生 AST 的 cls_def.constructor 未被解析器填充，
        # 故回退到「构造函数命名约定」(构造/初始化/构) 扫描方法名——与 src 后端
        # _CTOR_NAMES 对齐。注意构造函数经方法循环已按其真实名（如「构造」）注册，
        # 这里必须用真实名发起调用；此前错用类名「盒」导致 dv_find_method 返回
        # NULL、构造静默不执行，对象字段停留在默认值（轻量 UTF8 解码器原生腿产空
        # 串的根因）。
        CTOR_NAMES = ('构造', '初始化', '构')
        has_ctor = False
        ctor_name = None
        if class_name in self._classes:
            cls_def = self._classes[class_name]
            constructor = getattr(cls_def, 'constructor', None)
            if constructor is not None:
                has_ctor = True
                # 构造函数经 _gen_global_init 注册时一律以「类名」为方法名
                # （见下方注册段 3778 行附近的 dv_register_method(cls_name)），
                # 与 constructor.name（可能被解析器规范化为 __init__）无关。
                # 此处必须用 class_name 发起调用，否则 dv_call_method 查不到
                # 该名、构造静默不执行，对象字段停留在默认值（原生腿类构造
                # 加属性用例产空串的根因）。
                ctor_name = class_name
            else:
                for m in (getattr(cls_def, 'methods', []) or []):
                    mn = getattr(m, 'name', None)
                    if mn in CTOR_NAMES:
                        has_ctor = True
                        ctor_name = mn
                        break

        if has_ctor:
            obj_dv = self._load_dv(result_slot)
            obj_slot = self._store_dv(obj_dv)
            ctor_name_reg = self.gen_string_constant(ctor_name if ctor_name else class_name)
            
            args = getattr(expr, 'arguments', []) or []
            num_args = len(args)
            ctor_result_slot = self._new_dv_slot()
            num_args_i32 = self.new_register()
            self.emit(f'{num_args_i32} = add i32 0, {num_args}')
            
            if num_args == 0:
                self.emit(f'call void @dv_call_method(ptr {ctor_result_slot}, ptr {obj_slot}, ptr {ctor_name_reg}, ptr null, i32 {num_args_i32})')
            else:
                stack_save = self.new_register()
                self.emit(f'{stack_save} = call ptr @llvm.stacksave()')
                args_array = self.new_register()
                self.emit(f'{args_array} = alloca {LIGHTVALUE_STRUCT}, i32 {num_args}')
                
                for i, arg in enumerate(args):
                    arg_dv, _ = self._gen_expression(arg)
                    arg_elem_ptr = self.new_register()
                    self.emit(f'{arg_elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {args_array}, i32 {i}')
                    self.emit(f'store {LIGHTVALUE_STRUCT} {arg_dv}, ptr {arg_elem_ptr}')
                
                self.emit(f'call void @dv_call_method(ptr {ctor_result_slot}, ptr {obj_slot}, ptr {ctor_name_reg}, ptr {args_array}, i32 {num_args_i32})')
                self.emit(f'call void @llvm.stackrestore(ptr {stack_save})')
            
            updated_obj = self._load_dv(obj_slot)
            self.emit(f'store {LIGHTVALUE_STRUCT} {updated_obj}, ptr {result_slot}')
        
        return self._load_dv(result_slot), 'dv'

    def _gen_typed_try(self, stmt):
        """生成 try-catch 语句 - 使用内联 setjmp 避免栈帧失效问题"""
        # 获取 catch 子句列表（优先使用 catch_clauses，向后兼容 catch_body）
        catch_clauses = []
        if hasattr(stmt, 'catch_clauses') and stmt.catch_clauses and len(stmt.catch_clauses) > 0:
            catch_clauses = stmt.catch_clauses
        elif stmt.catch_body and len(stmt.catch_body) > 0:
            # 向后兼容：旧的单 catch 形式
            from dataclasses import dataclass
            catch_clauses = [type('CatchClause', (), {
                'catch_type': stmt.catch_type or '',
                'catch_var': stmt.catch_var or '',
                'catch_body': stmt.catch_body
            })()]
        
        has_catch = len(catch_clauses) > 0
        has_finally = bool(stmt.finally_body and len(stmt.finally_body) > 0)

        # 既无 catch 也无 finally：直接执行 try 体（不需要 setjmp）
        if not has_catch and not has_finally:
            for s in stmt.try_body:
                self._gen_statement(s)
            return

        end_lab = self.new_label('try_end')
        try_lab = self.new_label('try_body')

        if has_catch:
            dispatch_catch_lab = self.new_label('catch_dispatch')
        else:
            dispatch_catch_lab = self.new_label('catch_dispatch')

        if has_finally:
            finally_lab = self.new_label('finally_body')
            finally_from_try_lab = self.new_label('finally_from_try')

        # 获取 jmp_buf 指针
        jmp_buf_ptr = self.new_register()
        self.emit(f'{jmp_buf_ptr} = call ptr @dv_try_push()')

        # 内联调用 setjmp（平台相关）
        if self.is_windows:
            frame_addr = self.new_register()
            setjmp_result = self.new_register()
            self.emit(f'{frame_addr} = call ptr @llvm.frameaddress.p0(i32 0)')
            self.emit(f'{setjmp_result} = call i32 @_setjmp(ptr {jmp_buf_ptr}, ptr {frame_addr})')
        else:
            setjmp_result = self.new_register()
            self.emit(f'{setjmp_result} = call i32 @setjmp(ptr {jmp_buf_ptr})')

        cmp = self.new_register()
        self.emit(f'{cmp} = icmp ne i32 {setjmp_result}, 0')
        self.emit(f'br i1 {cmp}, label %{dispatch_catch_lab}, label %{try_lab}')

        # ---- try 块 ----
        self.emit(f'{try_lab}:')
        for s in stmt.try_body:
            self._gen_statement(s)
        if not self._ends_with_terminator(stmt.try_body):
            self.emit(f'call void @dv_try_pop()')
            if has_finally:
                self.emit(f'br label %{finally_from_try_lab}')
            else:
                self.emit(f'br label %{end_lab}')

        # ---- catch 分发 ----
        if has_catch:
            self.emit(f'{dispatch_catch_lab}:')
            self.emit(f'call void @dv_try_pop()')
            
            # 获取当前异常对象
            exc_slot = self._new_dv_slot()
            self.emit(f'call void @dv_get_current_exception(ptr {exc_slot})')
            
            # 生成多个 catch 块的匹配逻辑
            catch_end_lab = self.new_label('catch_end')
            next_catch_labs = []
            
            for i, clause in enumerate(catch_clauses):
                catch_lab = self.new_label(f'catch_{i}')
                if i < len(catch_clauses) - 1:
                    next_catch_lab = self.new_label(f'catch_next_{i}')
                else:
                    next_catch_lab = catch_end_lab
                next_catch_labs.append(next_catch_lab)
                
                if clause.catch_type:
                    # 有类型过滤：检查异常类型是否匹配
                    type_reg = self.gen_string_constant(clause.catch_type)
                    match_result = self.new_register()
                    self.emit(f'{match_result} = call i32 @dv_exception_match(ptr {exc_slot}, ptr {type_reg})')
                    cmp_match = self.new_register()
                    self.emit(f'{cmp_match} = icmp ne i32 {match_result}, 0')
                    self.emit(f'br i1 {cmp_match}, label %{catch_lab}, label %{next_catch_lab}')
                else:
                    # 无类型过滤：直接匹配（捕获所有）
                    self.emit(f'br label %{catch_lab}')
                
                # catch 块体
                self.emit(f'{catch_lab}:')
                if clause.catch_var:
                    self.alloca_local(clause.catch_var)
                    exc_val = self._load_dv(exc_slot)
                    self.set_var(clause.catch_var, exc_val)
                for s in clause.catch_body:
                    self._gen_statement(s)
                if not self._ends_with_terminator(clause.catch_body):
                    if has_finally:
                        self.emit(f'br label %{finally_lab}')
                    else:
                        self.emit(f'br label %{end_lab}')
                
                # 下一个 catch 块的入口（如果不是最后一个）
                if i < len(catch_clauses) - 1:
                    self.emit(f'{next_catch_lab}:')
            
            # catch 全部不匹配：重新抛出异常
            self.emit(f'{catch_end_lab}:')
            if has_finally:
                self.emit(f'br label %{finally_lab}')
            else:
                # 没有 finally，重新抛出异常向外层传播
                self.emit(f'call void @dv_throw_exception(ptr {exc_slot})')
                self.emit(f'br label %{end_lab}')
        else:
            # 无 catch 但有 finally：异常先执行 finally，然后重新抛出
            self.emit(f'{dispatch_catch_lab}:')
            self.emit(f'call void @dv_try_pop()')
            self.emit(f'br label %{finally_lab}')

        # ---- finally 块 ----
        if has_finally:
            # 从 try 块正常进入 finally
            self.emit(f'{finally_from_try_lab}:')
            self.emit(f'br label %{finally_lab}')

            self.emit(f'{finally_lab}:')
            for s in stmt.finally_body:
                self._gen_statement(s)

            if not self._ends_with_terminator(stmt.finally_body):
                if has_catch:
                    # 有 catch 时，finally 后直接结束
                    self.emit(f'br label %{end_lab}')
                else:
                    # 无 catch 时，finally 执行完重新抛出异常（向外层传播）
                    exc_slot = self._new_dv_slot()
                    self.emit(f'call void @dv_get_current_exception(ptr {exc_slot})')
                    self.emit(f'call void @dv_throw_exception(ptr {exc_slot})')
                    self.emit(f'br label %{end_lab}')

        self.emit(f'{end_lab}:')

    def _gen_typed_throw(self, stmt):
        """生成抛出异常语句"""
        dv_val, _ = self._gen_expression(stmt.value)
        slot = self._store_dv(dv_val)
        self.emit(f'call void @dv_throw_exception(ptr {slot})')

    def _collect_segment(self, seg, module_name=None):
        """覆盖父类方法：在收集阶段预先注册所有段名。

        T9A 修复：module_name 不为 None 时使用 (module_name, raw_name) 作为
        注册表 key，使跨模块同名段不互相覆盖；_safe_func_name 同步传入 module_name
        以获得模块隔离的 fN 编号。
        """
        raw_name = seg.name.name if hasattr(seg.name, 'name') else str(seg.name)
        reg_key = self._seg_reg_key(raw_name, module_name)
        params = [(p.name, p.default_value) for p in seg.parameters]
        self._segments[reg_key] = params
        self._segment_order.append(reg_key)
        self._segment_bodies[reg_key] = seg.body
        # 保存 modifiers（用于异步段落识别）
        modifiers = getattr(seg, 'modifiers', None) or []
        self._segment_modifiers[reg_key] = list(modifiers)
        # 预先注册到 _func_name_map，确保 f# 编号稳定（模块隔离）
        self._safe_func_name(raw_name, module_name)

    def _collect_statement(self, stmt):
        """覆盖父类方法"""
        super()._collect_statement(stmt)

    def _collect_vars_from_stmts(self, stmts):
        """覆盖父类：补充收集 try/catch 中的捕获变量。

        根因：基类 _collect_vars_from_stmts 只处理 VariableDeclaration /
        If / Foreach / While，遗漏了 TryStatement 的 catch 捕获变量。原生腿在
        entry 块按收集到的变量名批量 alloca（见 _gen_normal_segment 3777-3780），
        catch 变量因未被收集而缺失，运行时落到 _gen_typed_try 的
        alloca_local(clause.catch_var)（2625）走永不 flush 的 _pending_allocas，
        产生未定义值 `%N`（`use of undefined value '%N'`），这是原生腿 try/catch
        编译失败的直接原因。此处补齐 catch 变量收集，使其与其他局部变量一样获得
        entry 块 alloca。
        """
        for stmt in stmts:
            if stmt is None:
                continue
            if isinstance(stmt, ast.TryStatement):
                # 向后兼容：单 catch 变量
                if getattr(stmt, 'catch_var', None):
                    self._local_vars.setdefault(stmt.catch_var, None)
                for clause in (getattr(stmt, 'catch_clauses', None) or []):
                    cv = getattr(clause, 'catch_var', None)
                    if cv:
                        self._local_vars.setdefault(cv, None)
                    body = getattr(clause, 'catch_body', None)
                    if body:
                        self._collect_vars_from_stmts(body)
                for sub in (getattr(stmt, 'try_body', None) or []):
                    self._collect_vars_from_stmts([sub])
                for sub in (getattr(stmt, 'finally_body', None) or []):
                    self._collect_vars_from_stmts([sub])
            else:
                # 其余类型交给基类递归处理（If/Foreach/While/VariableDeclaration）
                super()._collect_vars_from_stmts([stmt])

    def _collect_class(self, cls_def):
        """收集类定义"""
        self._classes[cls_def.name] = cls_def

    def _collect_interface(self, iface_def):
        """收集接口定义（Level 7）"""
        self._interfaces[iface_def.name] = iface_def

    def _get_method_type(self, method_def) -> str:
        """判断方法类型：'instance' | 'class' | 'static'
        
        通过方法名前缀识别：
        - 以 '类' 开头 → 类方法
        - 以 '静' 开头 → 静态方法
        - 否则 → 实例方法
        """
        name = method_def.name if hasattr(method_def, 'name') else str(method_def)
        if name.startswith('类'):
            return 'class'
        if name.startswith('静'):
            return 'static'
        if getattr(method_def, 'is_static', False):
            return 'static'
        return 'instance'

    def _gen_typed_segment_call(self, name: str, args: List[str], arg_asts=None) -> Tuple[str, str]:
        # T9A：段调用使用当前模块上下文，确保跨模块同名段调用到正确的定义
        safe = self._safe_func_name(name, self._current_module)
        result_slot = self._new_dv_slot()
        # R10-11a 打回 A2：段函数返回路径会 dv_obj_release_slot(result_ptr) 释放旧值。
        # _new_dv_slot 来自复用型临时槽位池（不零初始化），O0 下残留垃圾可能被
        # 误判为 REF 指针 → memcpy 非法地址 → 段错误(rc=3221225477)。
        # O1+ 优化消除未初始化读取故不崩。与 _call_dv_func(L690) 同模式补 dv_null。
        self.emit(f'call void @dv_null(ptr {result_slot})')
        num_args = len(args)
        if num_args == 0:
            self.emit(f'call void @_seg_{safe}(ptr {result_slot}, ptr null, i32 0)')
        else:
            stack_save = self.new_register()
            self.emit(f'{stack_save} = call ptr @llvm.stacksave()')
            args_arr = self.new_register()
            self.emit(f'{args_arr} = alloca {LIGHTVALUE_STRUCT}, i32 {num_args}')
            for i, arg_dv in enumerate(args):
                elem_ptr = self.new_register()
                self.emit(f'{elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {args_arr}, i64 {i}')
                self.emit(f'store {LIGHTVALUE_STRUCT} {arg_dv}, ptr {elem_ptr}')
            self.emit(f'call void @_seg_{safe}(ptr {result_slot}, ptr {args_arr}, i32 {num_args})')
            # T7B / T5C-02·04：写回（必须在 stackrestore 前）
            self._emit_args_writeback(args_arr, arg_asts, num_args)
            self.emit(f'call void @llvm.stackrestore(ptr {stack_save})')
        result = self.new_register()
        self.emit(f'{result} = load {LIGHTVALUE_STRUCT}, ptr {result_slot}')
        return result, 'dv'

    def _gen_typed_index_access(self, expr) -> Tuple[str, str]:
        # A9-S2：SliceExpr — 适配层把 obj[start:stop] 转成
        # IndexAccess(obj, FunctionCall('slice', start, stop))。在正常索引处理前拦截。
        if isinstance(expr.index, ast.FunctionCall) and \
                isinstance(expr.index.name, ast.Identifier) and \
                expr.index.name.name == 'slice':
            return self._gen_typed_slice(expr.obj, expr.index.arguments)
        obj_dv, _ = self._gen_expression(expr.obj)
        # 索引既要做成 i64（字符串/列表下标），也要保留 LightValue（字典键）。
        # 字符串用 i64；列表用 i64；字典（type=7）要传整个 LightValue 做键。
        if isinstance(expr.index, ast.NumberLiteral):
            idx_val = int(expr.index.value)
            i64_reg = f'{idx_val}'
            key_slot = self._new_dv_slot()
            self.emit(f'call void @dv_int(ptr {key_slot}, i64 {i64_reg})')
        else:
            idx_dv, _ = self._gen_expression(expr.index)
            i64_reg = self.new_register()
            self.emit(f'{i64_reg} = extractvalue {LIGHTVALUE_STRUCT} {idx_dv}, 1')
            key_slot = self._store_dv(idx_dv)
        obj_slot = self._store_dv(obj_dv)
        # 解引用 REF（dict 索引取值返回 REF，type=8）：否则字符串/列表索引的
        # type 判断误走 list 分支，dict 内字符串取字符读到垃圾（\u0000 等）。
        deref_slot = self._new_dv_slot()
        self.emit(f'call void @dv_deref_value(ptr {deref_slot}, ptr {obj_slot})')
        obj_slot = deref_slot
        type_reg = self.new_register()
        self.emit(f'{type_reg} = load i32, ptr {obj_slot}')
        is_str = self.new_register()
        self.emit(f'{is_str} = icmp eq i32 {type_reg}, 3')
        is_dict = self.new_register()
        self.emit(f'{is_dict} = icmp eq i32 {type_reg}, 7')
        is_tuple = self.new_register()
        self.emit(f'{is_tuple} = icmp eq i32 {type_reg}, 23')
        str_lab = self.new_label('idx_str')
        dict_lab = self.new_label('idx_dict')
        tuple_lab = self.new_label('idx_tuple')
        list_lab = self.new_label('idx_list')
        end_lab = self.new_label('idx_end')
        result_slot = self._new_dv_slot()
        not_str_lab = self.new_label('idx_not_str')
        self.emit(f'br i1 {is_str}, label %{str_lab}, label %{not_str_lab}')
        self.emit(f'{not_str_lab}:')
        not_dict_lab = self.new_label('idx_not_dict')
        self.emit(f'br i1 {is_dict}, label %{dict_lab}, label %{not_dict_lab}')
        self.emit(f'{not_dict_lab}:')
        self.emit(f'br i1 {is_tuple}, label %{tuple_lab}, label %{list_lab}')
        self.emit(f'{str_lab}:')
        self.emit(f'call void @dv_str_get(ptr {result_slot}, ptr {obj_slot}, i64 {i64_reg})')
        self.emit(f'br label %{end_lab}')
        self.emit(f'{dict_lab}:')
        self.emit(f'call void @dv_dict_get(ptr {result_slot}, ptr {obj_slot}, ptr {key_slot})')
        self.emit(f'br label %{end_lab}')
        self.emit(f'{tuple_lab}:')
        self.emit(f'call void @dv_tuple_get(ptr {result_slot}, ptr {obj_slot}, i64 {i64_reg})')
        self.emit(f'br label %{end_lab}')
        self.emit(f'{list_lab}:')
        self.emit(f'call void @dv_list_get(ptr {result_slot}, ptr {obj_slot}, i64 {i64_reg})')
        self.emit(f'br label %{end_lab}')
        self.emit(f'{end_lab}:')
        result = self._load_dv(result_slot)
        return result, 'dv'

    def _gen_typed_slice(self, obj_ast, args) -> Tuple[str, str]:
        """A9-S2: 切片 obj[start:stop] / obj[start:] / obj[:stop] / obj[:]

        适配层把 v3 SliceExpr 转成 FunctionCall('slice', start, stop, step)，
        包在 IndexAccess(obj, FunctionCall('slice',...)) 里。_gen_typed_index_access
        拦截后调到这里。推翻 C3-2「切片不做」决策——stdlib 用了 52 次，是最高频未支持节点。

        字符串用 dv_substr(result, str, start, len)；
        列表用 dv_list_new + 循环 dv_list_get + dv_list_append。
        step 参数暂不支持（stdlib 中 0 次使用）。
        """
        obj_dv, _ = self._gen_expression(obj_ast)
        obj_slot = self._store_dv(obj_dv)

        # 解析 start/stop（默认 start=0, stop=len）
        start_i64 = '0'
        stop_is_len = True
        stop_i64 = None

        if len(args) >= 1 and args[0] is not None:
            start_dv, _ = self._gen_expression(args[0])
            start_i64 = self.new_register()
            self.emit(f'{start_i64} = extractvalue {LIGHTVALUE_STRUCT} {start_dv}, 1')
        if len(args) >= 2 and args[1] is not None:
            stop_dv, _ = self._gen_expression(args[1])
            stop_i64 = self.new_register()
            self.emit(f'{stop_i64} = extractvalue {LIGHTVALUE_STRUCT} {stop_dv}, 1')
            stop_is_len = False
        if len(args) >= 3 and args[2] is not None:
            raise NotImplementedError(
                f"原生后端切片暂不支持 step 参数"
                f"（源码行 {self._stmt_source_line(obj_ast)}）。"
            )

        # 获取对象类型（3=字符串, 6=列表）
        type_reg = self.new_register()
        self.emit(f'{type_reg} = load i32, ptr {obj_slot}')
        is_str = self.new_register()
        self.emit(f'{is_str} = icmp eq i32 {type_reg}, 3')

        str_lab = self.new_label('slice_str')
        list_lab = self.new_label('slice_list')
        end_lab = self.new_label('slice_end')
        result_slot = self._new_dv_slot()

        not_str_lab = self.new_label('slice_not_str')
        self.emit(f'br i1 {is_str}, label %{str_lab}, label %{not_str_lab}')
        self.emit(f'{not_str_lab}:')
        self.emit(f'br label %{list_lab}')

        # ── 字符串切片：dv_substr(result, str, start, len) ──
        self.emit(f'{str_lab}:')
        if stop_is_len:
            str_len = self.new_register()
            self.emit(f'{str_len} = call i64 @dv_str_len(ptr {obj_slot})')
            slice_len = self.new_register()
            self.emit(f'{slice_len} = sub i64 {str_len}, {start_i64}')
        else:
            slice_len = self.new_register()
            self.emit(f'{slice_len} = sub i64 {stop_i64}, {start_i64}')
        # 处理负长度（start > stop → 空串）
        is_neg = self.new_register()
        self.emit(f'{is_neg} = icmp slt i64 {slice_len}, 0')
        safe_len = self.new_register()
        self.emit(f'{safe_len} = select i1 {is_neg}, i64 0, i64 {slice_len}')
        self.emit(f'call void @dv_substr(ptr {result_slot}, ptr {obj_slot}, i64 {start_i64}, i64 {safe_len})')
        self.emit(f'br label %{end_lab}')

        # ── 列表切片：创建新列表，循环复制 ──
        self.emit(f'{list_lab}:')
        new_list_dv = self._call_dv_func('dv_list_new')
        new_list_slot = self._new_dv_slot()
        self.emit(f'store {LIGHTVALUE_STRUCT} {new_list_dv}, ptr {new_list_slot}')

        list_len = self.new_register()
        self.emit(f'{list_len} = call i64 @dv_list_len(ptr {obj_slot})')

        if stop_is_len:
            stop_val = list_len
        else:
            stop_val = stop_i64

        # i = start
        i_slot = self._gen_alloca('i64')
        self.emit(f'store i64 {start_i64}, ptr {i_slot}')

        cond_lab = self.new_label('slice_cond')
        body_lab = self.new_label('slice_body')
        done_lab = self.new_label('slice_done')

        self.emit(f'br label %{cond_lab}')
        self.emit(f'{cond_lab}:')
        i_val = self.new_register()
        self.emit(f'{i_val} = load i64, ptr {i_slot}')
        cmp = self.new_register()
        self.emit(f'{cmp} = icmp slt i64 {i_val}, {stop_val}')
        self.emit(f'br i1 {cmp}, label %{body_lab}, label %{done_lab}')

        self.emit(f'{body_lab}:')
        elem_slot = self._new_dv_slot()
        self.emit(f'call void @dv_list_get(ptr {elem_slot}, ptr {obj_slot}, i64 {i_val})')
        # 用原地追加模式（result == list 同槽），避免 _call_dv_func 的
        # result_slot 未初始化导致 dv_list_append 跳过 dv_clone。
        cur_list = self.new_register()
        self.emit(f'{cur_list} = load {LIGHTVALUE_STRUCT}, ptr {new_list_slot}')
        list_arg_slot = self._store_dv(cur_list)
        elem_dv = self._load_dv(elem_slot)
        elem_arg_slot = self._store_dv(elem_dv)
        self.emit(f'call void @dv_list_append(ptr {list_arg_slot}, ptr {list_arg_slot}, ptr {elem_arg_slot})')
        new_list = self._load_dv(list_arg_slot)
        self.emit(f'store {LIGHTVALUE_STRUCT} {new_list}, ptr {new_list_slot}')
        next_i = self.new_register()
        self.emit(f'{next_i} = add i64 {i_val}, 1')
        self.emit(f'store i64 {next_i}, ptr {i_slot}')
        self.emit(f'br label %{cond_lab}')

        self.emit(f'{done_lab}:')
        final = self.new_register()
        self.emit(f'{final} = load {LIGHTVALUE_STRUCT}, ptr {new_list_slot}')
        self.emit(f'store {LIGHTVALUE_STRUCT} {final}, ptr {result_slot}')
        self.emit(f'br label %{end_lab}')

        self.emit(f'{end_lab}:')
        result = self._load_dv(result_slot)
        return result, 'dv'

    def _gen_typed_list_comprehension(self, expr) -> Tuple[str, str]:
        """A9-S2: 列表推导 [表达式 遍历 变量 之 列表 若 条件]

        适配层把 v3 ListComprehension 转成 v1 ListComprehension（保留
        expression/variable/iterable/condition 四字段）。这里生成循环：
        创建空列表 → 遍历 iterable → 设循环变量 → 检查 condition → 追加 expression。
        """
        # 生成可迭代对象
        iter_dv, _ = self._gen_expression(expr.iterable)
        iter_slot = self._store_dv(iter_dv)

        # 创建结果列表
        result_dv = self._call_dv_func('dv_list_new')
        result_slot = self._new_dv_slot()
        self.emit(f'store {LIGHTVALUE_STRUCT} {result_dv}, ptr {result_slot}')

        # 获取长度
        list_len = self.new_register()
        self.emit(f'{list_len} = call i64 @dv_list_len(ptr {iter_slot})')

        # 循环变量（用 slot pool 而非 alloca_local，因为 typed codegen
        # 不 flush _pending_allocas，alloca 指令会丢失导致未定义值）
        var_name = expr.variable
        var_slot = self._new_dv_slot()
        self._local_vars[var_name] = var_slot

        # i = 0
        i_slot = self._gen_alloca('i64')
        self.emit(f'store i64 0, ptr {i_slot}')

        cond_lab = self.new_label('lc_cond')
        body_lab = self.new_label('lc_body')
        filter_lab = self.new_label('lc_filter')
        append_lab = self.new_label('lc_append')
        next_lab = self.new_label('lc_next')
        done_lab = self.new_label('lc_done')

        self.emit(f'br label %{cond_lab}')
        self.emit(f'{cond_lab}:')
        i_val = self.new_register()
        self.emit(f'{i_val} = load i64, ptr {i_slot}')
        cmp = self.new_register()
        self.emit(f'{cmp} = icmp slt i64 {i_val}, {list_len}')
        self.emit(f'br i1 {cmp}, label %{body_lab}, label %{done_lab}')

        self.emit(f'{body_lab}:')
        # 取出元素
        elem_dv = self._call_dv_func('dv_list_get', iter_dv, f'i64 {i_val}')
        self.set_var(var_name, elem_dv)

        # 检查条件（如果有）
        if expr.condition is not None:
            cond_dv, _ = self._gen_expression(expr.condition)
            cond_i1 = self._gen_condition_i1(expr.condition, cond_dv)
            self.emit(f'br i1 {cond_i1}, label %{append_lab}, label %{next_lab}')
        else:
            self.emit(f'br label %{append_lab}')

        self.emit(f'{append_lab}:')
        # 计算输出表达式
        out_dv, _ = self._gen_expression(expr.expression)
        # 原地追加模式（result == list 同槽），避免未初始化 result_slot 问题
        cur_list = self.new_register()
        self.emit(f'{cur_list} = load {LIGHTVALUE_STRUCT}, ptr {result_slot}')
        list_arg_slot = self._store_dv(cur_list)
        elem_arg_slot = self._store_dv(out_dv)
        self.emit(f'call void @dv_list_append(ptr {list_arg_slot}, ptr {list_arg_slot}, ptr {elem_arg_slot})')
        new_list = self._load_dv(list_arg_slot)
        self.emit(f'store {LIGHTVALUE_STRUCT} {new_list}, ptr {result_slot}')
        self.emit(f'br label %{next_lab}')

        self.emit(f'{next_lab}:')
        next_i = self.new_register()
        self.emit(f'{next_i} = add i64 {i_val}, 1')
        self.emit(f'store i64 {next_i}, ptr {i_slot}')
        self.emit(f'br label %{cond_lab}')

        self.emit(f'{done_lab}:')
        final = self.new_register()
        self.emit(f'{final} = load {LIGHTVALUE_STRUCT}, ptr {result_slot}')
        return final, 'dv'

    # ============================================================
    # 生成器状态机底层支撑（R10-11b 第四批B）
    # ============================================================

    def _gen_entry_symbolic(self, prefix: str) -> str:
        """分配一个符号名寄存器（不参与 %N 自动编号），供回插 entry 的指令用。

        生成器正文里凡是**稍后文本上要插到 entry 块**的指令，必须用符号名：
        它们在生成时刻排在正文寄存器之后，数字寄存器名会破坏 LLVM 文本的
        单调编号约束；符号名没有这个约束，可被任意块引用。
        """
        self._gen_entry_name_seq += 1
        return f'%g{prefix}{self._gen_entry_name_seq}'

    def _gen_emit_entry_alloca(self, line: str):
        """生成器中发射 alloca：强制落进 entry 块。

        普通段里 `alloca` 就地发射没问题（每个块只进一次）；生成器的 `ret void`
        之后会从 entry 的 switch 直接跳进恢复块，就地 alloca 的块**不支配**恢复块，
        循环计数器（`遍历`/`范围`）就会变成 "instruction does not dominate all uses"。
        故生成器内所有 alloca 统一提到 entry。
        """
        if self._gen_entry_insert_idx is None:
            self.emit(line)
            return
        self._lines.insert(self._gen_entry_insert_idx, line)
        self._gen_entry_insert_idx += 1

    def _gen_alloca(self, ir_type: str) -> str:
        """发射一条 alloca，返回寄存器名（生成器内自动提到 entry 块）。"""
        if self._gen_entry_insert_idx is not None:
            reg = self._gen_entry_symbolic('a')
            self._lines.insert(
                self._gen_entry_insert_idx, f'{reg} = alloca {ir_type}')
            self._gen_entry_insert_idx += 1
            return reg
        reg = self.new_register()
        self.emit(f'{reg} = alloca {ir_type}')
        return reg

    def _gen_new_slot(self) -> str:
        """在生成器堆槽数组里取一个 LightValue 槽位。

        与普通段的 `_new_dv_slot`（栈上临时池）对应：生成器的槽必须活过
        `ret void`，所以放堆上；取槽指令一律插在 entry 块，保证支配所有恢复块。
        """
        if self._gen_slot_index >= self._gen_slot_budget:
            raise RuntimeError(
                f"生成器槽位溢出：段落「{self._current_func}」用掉 "
                f"{self._gen_slot_index} / {self._gen_slot_budget} 个槽位")
        idx = self._gen_slot_index
        self._gen_slot_index += 1
        reg = self._gen_entry_symbolic('s')
        self._lines.insert(
            self._gen_entry_insert_idx,
            f'{reg} = call ptr @dv_gen_slot(ptr %gen, i32 {idx})')
        self._gen_entry_insert_idx += 1
        return reg

    @staticmethod
    def _iter_ast_children(node):
        """遍历 AST 节点的子节点（dataclass 字段里的节点 / 节点列表）。

        slots dataclass 上 `vars()` 不可用，只能走 `dataclasses.fields`。
        `line`/`column` 等 int 字段天然被跳过（不是 dataclass）。
        """
        try:
            from dataclasses import fields, is_dataclass
        except ImportError:  # pragma: no cover
            return
        if not is_dataclass(node):
            return
        for f in fields(node):
            try:
                v = getattr(node, f.name)
            except Exception:
                continue
            if isinstance(v, list):
                for x in v:
                    if is_dataclass(x):
                        yield x
            elif is_dataclass(v):
                yield v

    def _段内生成点(self, body, 计数: bool) -> int:
        """统计段落体里的 `生成` 点数（不深入嵌套段落/类定义——它们各自成函数）。

        这是**发射前**的预扫：状态机 entry 块的 switch 需要先把全部恢复标签
        造出来，标签数取决于生成点数。
        """
        计数结果 = 0
        栈 = [s for s in (body or []) if s is not None]
        while 栈:
            node = 栈.pop()
            if isinstance(node, ast.YieldStatement):
                if not 计数:
                    return 1
                计数结果 += 1
                continue
            if isinstance(node, (ast.SegmentDefinition, ast.ClassDefinition)):
                continue
            for child in self._iter_ast_children(node):
                栈.append(child)
        return 计数结果

    def _段是生成器(self, body) -> bool:
        return self._段内生成点(body, 计数=False) > 0

    def _当前块已终止(self) -> bool:
        """最近一条实际发射的指令是不是终止指令（ret/br/switch/…）。

        生成器收尾要追加「finish + ret」，但正文可能已经以 `ret void`（生成点或
        `返回`）结尾——此时必须先起新块，否则同一块里出现两个终止指令。
        """
        for line in reversed(self._lines):
            s = line.strip()
            if not s or s.startswith(';'):
                continue
            if s.endswith(':'):
                # 最后一条是标签 —— 当前块是刚开的空块，还没写终止指令。
                # 这正是「正文以 `生成`/`返回` 收尾」和「循环正常结束」两种
                # 情形的共同形态，都必须补一条 br 到收尾块。
                return False
            return (s.startswith('ret ') or s.startswith('br ')
                    or s.startswith('switch ') or s.startswith('unreachable')
                    or s.startswith('indirectbr ') or s.startswith('resume '))
        return False

    def _gen_typed_list_from_args(self, args: List[str]) -> str:
        """C3-1：从一组已生成的 LightValue 构造列表（`列(1, 2, 3)`）。"""
        list_dv = self._call_dv_func('dv_list_new')
        list_slot = self._new_dv_slot()
        self.emit(f'store {LIGHTVALUE_STRUCT} {list_dv}, ptr {list_slot}')
        for elem_dv in args:
            cur = self.new_register()
            self.emit(f'{cur} = load {LIGHTVALUE_STRUCT}, ptr {list_slot}')
            new_list = self._call_dv_func('dv_list_append', cur, elem_dv)
            self.emit(f'store {LIGHTVALUE_STRUCT} {new_list}, ptr {list_slot}')
        final = self.new_register()
        self.emit(f'{final} = load {LIGHTVALUE_STRUCT}, ptr {list_slot}')
        return final

    def _gen_typed_dict_literal(self, expr) -> Tuple[str, str]:
        """C3-2：字典字面量 `[键: 值]`。runtime 侧 dv_dict_new/dv_dict_set 已有，
        缺的只是字面量构造——逐条目 dv_dict_set 进空字典。
        `**展开`（entries 里 key 为 None）本轮不做，显式报错。
        """
        dict_dv = self._call_dv_func('dv_dict_new')
        dict_slot = self._new_dv_slot()
        self.emit(f'store {LIGHTVALUE_STRUCT} {dict_dv}, ptr {dict_slot}')
        for entry in expr.entries:
            key, value = entry
            if key is None:
                self._reject_unsupported_expr('DictExpand', entry)
            key_dv, _ = self._gen_expression(key)
            value_dv, _ = self._gen_expression(value)
            cur = self.new_register()
            self.emit(f'{cur} = load {LIGHTVALUE_STRUCT}, ptr {dict_slot}')
            new_dict = self._call_dv_func('dv_dict_set', cur, key_dv, value_dv)
            self.emit(f'store {LIGHTVALUE_STRUCT} {new_dict}, ptr {dict_slot}')
        final = self.new_register()
        self.emit(f'{final} = load {LIGHTVALUE_STRUCT}, ptr {dict_slot}')
        return final, 'dv'

    def _gen_typed_string_interpolation(self, expr) -> Tuple[str, str]:
        """C3-2：字符串插值降级实现——拆成若干段 + 字符串拼接（dv_concat）。

        不真做 format 机制：每段先求值成字符串（字面段直接进字符串常量，
        表达式段求值后用 dv_concat 自动转字符串），逐段拼起来。
        """
        result_dv = self._create_str_dv(self.gen_string_constant(""))
        for part in expr.parts:
            if isinstance(part, str):
                part_dv = self._create_str_dv(self.gen_string_constant(part))
            else:
                part_dv, _ = self._gen_expression(part)
            result_dv = self._call_dv_func('dv_concat', result_dv, part_dv)
        return result_dv, 'dv'

    def _gen_typed_list_literal(self, expr) -> Tuple[str, str]:
        list_dv = self._call_dv_func('dv_list_new')
        list_slot = self._new_dv_slot()
        self.emit(f'store {LIGHTVALUE_STRUCT} {list_dv}, ptr {list_slot}')
        for elem in expr.elements:
            elem_dv, _ = self._gen_expression(elem)
            cur = self.new_register()
            self.emit(f'{cur} = load {LIGHTVALUE_STRUCT}, ptr {list_slot}')
            new_list = self._call_dv_func('dv_list_append', cur, elem_dv)
            self.emit(f'store {LIGHTVALUE_STRUCT} {new_list}, ptr {list_slot}')
        final = self.new_register()
        self.emit(f'{final} = load {LIGHTVALUE_STRUCT}, ptr {list_slot}')
        return final, 'dv'

    def _gen_typed_tuple_literal(self, expr) -> Tuple[str, str]:
        """R10-11a：元组字面量 (a, b) → dv_tuple_new + dv_tuple_append 逐元素构造"""
        tuple_dv = self._call_dv_func('dv_tuple_new')
        tuple_slot = self._new_dv_slot()
        self.emit(f'store {LIGHTVALUE_STRUCT} {tuple_dv}, ptr {tuple_slot}')
        for elem in expr.elements:
            elem_dv, _ = self._gen_expression(elem)
            cur = self.new_register()
            self.emit(f'{cur} = load {LIGHTVALUE_STRUCT}, ptr {tuple_slot}')
            new_tuple = self._call_dv_func('dv_tuple_append', cur, elem_dv)
            self.emit(f'store {LIGHTVALUE_STRUCT} {new_tuple}, ptr {tuple_slot}')
        final = self.new_register()
        self.emit(f'{final} = load {LIGHTVALUE_STRUCT}, ptr {tuple_slot}')
        return final, 'dv'

    def _gen_typed_conditional(self, expr) -> Tuple[str, str]:
        cond_dv, _ = self._gen_expression(expr.condition)
        zero_dv = self._create_int_dv('0')
        cond_slot = self._store_dv(cond_dv)
        zero_slot = self._store_dv(zero_dv)
        eq = self.new_register()
        self.emit(f'{eq} = call i32 @dv_eq(ptr {cond_slot}, ptr {zero_slot})')
        final = self.new_register()
        self.emit(f'{final} = icmp ne i32 {eq}, 0')

        then_lab = self.new_label('cond_then')
        else_lab = self.new_label('cond_else')
        end_lab = self.new_label('cond_end')
        result_slot = self._new_dv_slot()
        self.emit(f'br i1 {final}, label %{else_lab}, label %{then_lab}')

        self.emit(f'{then_lab}:')
        then_dv, _ = self._gen_expression(expr.then_expr)
        self.emit(f'store {LIGHTVALUE_STRUCT} {then_dv}, ptr {result_slot}')
        self.emit(f'br label %{end_lab}')

        self.emit(f'{else_lab}:')
        else_dv, _ = self._gen_expression(expr.else_expr)
        self.emit(f'store {LIGHTVALUE_STRUCT} {else_dv}, ptr {result_slot}')
        self.emit(f'br label %{end_lab}')

        self.emit(f'{end_lab}:')
        loaded = self.new_register()
        self.emit(f'{loaded} = load {LIGHTVALUE_STRUCT}, ptr {result_slot}')
        return loaded, 'dv'

    # ============================================================
    # 语句生成（重写，使用 LightValue）
    # ============================================================

    # A2-1：AstAdapter（src/compiler.py:305-307）对它不认识的 v3 节点不报错，
    # 而是包成 `ExpressionStatement(Identifier("<unknown:XXX>"))`。原生腿于是把
    # `全局 计数。`/`生成 X。` 编成一次标识符取值，既不实现也不提示——产物行为错误
    # 却编译成功。下面这个前缀就是那道伪装的唯一识别特征。
    _ADAPTER_UNKNOWN_PREFIX = '<unknown:'
    # 内置函数关键字参数签名：函数名 -> {关键字名: 位置索引}。
    # 打开文件(路径, 模式, encoding)；sort/排序(列表, reverse)。
    _BUILTIN_KWARGS = {
        '打开文件': {'encoding': 2},
        'sort': {'reverse': 1},
        'list_sort': {'reverse': 1},
        '排序': {'reverse': 1},
        '列表排序': {'reverse': 1},
    }

    # 转译后端的正确调用方式，所有拒绝文案共用一份，避免文案漂移
    _FALLBACK_HINT = '原生后端暂不支持，请用转译后端（python -m cli.light_unified run）'

    @staticmethod
    def _stmt_source_line(stmt) -> str:
        """取语句的源码行号；取不到就说明取不到，不许伪造一个 0 出来。"""
        line = getattr(stmt, 'lineno', None)
        if not line:
            # AstAdapter 造 ExpressionStatement 时不带行号，内层表达式也没有
            inner = getattr(stmt, 'expression', None)
            line = getattr(inner, 'lineno', None) if inner is not None else None
        return str(line) if line else '未知（适配层未保留行号）'

    def _reject_unsupported_stmt(self, type_name: str, stmt):
        """原生后端遇到未实现的语句类型：显式炸，不许静默丢弃。"""
        raise NotImplementedError(
            f"原生后端暂不支持语句类型「{type_name}」"
            f"（源码行 {self._stmt_source_line(stmt)}）：{self._FALLBACK_HINT}"
        )

    def _reject_unsupported_expr(self, type_name: str, expr):
        """C3-1：原生后端遇到未实现的表达式类型：显式炸，不许静默编成整数 0。

        与 `_reject_unsupported_stmt` 同一口径（复用行号获取逻辑），区别只在
        「表达式」三字——让用户知道自己写坏的是表达式不是语句。
        """
        raise NotImplementedError(
            f"原生后端暂不支持表达式「{type_name}」"
            f"（源码行 {self._stmt_source_line(expr)}）：{self._FALLBACK_HINT}"
        )

    def _reject_unknown_call(self, name: str, expr, kind: str = '段落'):
        """C3-1：调用了未定义的段落/函数：列出本模块已定义候选，不许静默编成 0。

        拼错名字的调用（`计算总和(表)` 写成 `计算总和`）是最坑的静默降级——
        旧行为编成 `结果 = 0` 且编译成功。现在报错并给出候选，省掉猜名字的时间。
        候选多于 10 个时截断到前 10 个 + 总数。
        """
        # T9A：从模块限定 key 中提取裸段名作为候选（去重）
        candidates = sorted(set(self._seg_raw_name(k) for k in self._segments.keys()))
        if len(candidates) > 10:
            cand_text = ', '.join(candidates[:10]) + f' 等共 {len(candidates)} 个'
        elif candidates:
            cand_text = ', '.join(candidates)
        else:
            cand_text = '（本模块未定义任何段落）'
        raise NotImplementedError(
            f"未定义的{kind}：{name}（源码行 {self._stmt_source_line(expr)}）。"
            f"本模块已定义：{cand_text}。{self._FALLBACK_HINT}"
        )

    def _gen_statement(self, stmt):
        if stmt is None:
            return
        # 设置调试位置（用于 !dbg 元数据）
        if self._debug:
            line = getattr(stmt, 'lineno', 0) if stmt else 0
            col = getattr(stmt, 'col_offset', 0) if stmt else 0
            self._set_debug_location(line, col)
        if isinstance(stmt, ast.VariableDeclaration):
            self._gen_typed_var_decl(stmt)
        elif isinstance(stmt, ast.Assignment):
            self._gen_typed_assignment(stmt)
        elif hasattr(ast, 'SelfAssignment') and isinstance(stmt, ast.SelfAssignment):
            self._gen_typed_self_assignment(stmt)
        elif isinstance(stmt, ast.CompoundAssignment):
            self._gen_typed_compound_assignment(stmt)
        elif isinstance(stmt, ast.IfStatement):
            self._gen_typed_if(stmt)
        elif isinstance(stmt, ast.ForeachStatement):
            self._gen_typed_foreach(stmt)
        elif isinstance(stmt, ast.WhileStatement):
            self._gen_typed_while(stmt)
        elif isinstance(stmt, ast.ReturnStatement):
            self._gen_typed_return(stmt)
        elif isinstance(stmt, ast.BreakStatement):
            super()._gen_break(stmt)
        elif isinstance(stmt, ast.ContinueStatement):
            super()._gen_continue(stmt)
        elif isinstance(stmt, ast.PrintStatement):
            self._gen_typed_print(stmt)
        elif isinstance(stmt, ast.TryStatement):
            self._gen_typed_try(stmt)
        elif isinstance(stmt, ast.ThrowStatement):
            self._gen_typed_throw(stmt)
        elif isinstance(stmt, ast.ExpressionStatement):
            expr = stmt.expression
            # A2-1：先拆掉适配层的伪装——`<unknown:XXX>` 不是标识符，是一条被
            # 悄悄降级的语句，必须报出它原来的 v3 类型名。
            if isinstance(expr, ast.Identifier) and isinstance(expr.name, str) \
                    and expr.name.startswith(self._ADAPTER_UNKNOWN_PREFIX):
                inner = expr.name[len(self._ADAPTER_UNKNOWN_PREFIX):].rstrip('>')
                # R10-11b 后：`生成` 由适配层转成一等 YieldStatement 节点并走
                # _gen_typed_yield 状态机（本文件生成器段）。若这里仍出现
                # <unknown:YieldStmt> 伪装标识符，说明适配层漏转，必须报错而
                # 不许静默跳过（防静默降级）。
                self._reject_unsupported_stmt(inner, stmt)
            if isinstance(expr, ast.FunctionCall) and isinstance(expr.name, ast.PropertyAccess):
                method_name = expr.name.property_name
                obj = expr.name.obj
                mutating_methods = {'追加', 'append', '清空', 'clear', '设置', 'set', '插入', 'insert', '删除', 'remove', '弹出', 'pop'}
                if method_name in mutating_methods:
                    # 情形一：裸局部变量 x.追加(...) —— 调用后把返回值写回 x 绑定
                    if isinstance(obj, ast.Identifier):
                        obj_name = obj.name
                        result_dv, _ = self._gen_expression(expr)
                        self.set_var(obj_name, result_dv)
                        return
            self._gen_expression(expr)
        elif isinstance(stmt, ast.ImportStatement):
            pass
        elif hasattr(ast, 'AsyncScope') and isinstance(stmt, ast.AsyncScope):
            self._gen_async_scope(stmt)
        elif isinstance(stmt, ast.YieldStatement):
            self._gen_typed_yield(stmt)
        else:
            # A2-1：链尾兜底。以前这里什么都没有，未知语句被静默吃掉。
            self._reject_unsupported_stmt(type(stmt).__name__, stmt)

    def _gen_typed_var_decl(self, stmt: ast.VariableDeclaration):
        name = stmt.name
        # 字段赋值形式：设 己.X 为 Y / 设 self.X 为 Y（在方法/构造内）。
        # 解析器会把「设 己.X」拍平成名为「己.X」的 VariableDeclaration，
        # 原生腿需在此显式降级为 dv_class_set_member（与 src 后端一致），
        # 否则会错误地建一个字面名为「己.X」的局部变量，导致字段写丢失（P0-2 双后端一致）。
        if (self._method_result_ptr is not None
                and (name.startswith('己.') or name.startswith('self.'))):
            attr_name = name.split('.', 1)[1] if '.' in name else name
            self_dv = self.get_var('己')
            if self_dv is not None:
                if stmt.value:
                    value_dv, _ = self._gen_expression(stmt.value)
                else:
                    value_dv = self._create_int_dv('0')
                obj_slot = self._self_lvalue_slot()
                member_reg = self.gen_string_constant(attr_name)
                value_slot = self._store_dv(value_dv)
                self.emit(f'call void @dv_class_set_member(ptr {obj_slot}, ptr {member_reg}, ptr {value_slot})')
                updated_dv = self._load_dv(obj_slot)
                self.set_var('己', updated_dv)
                return
        # 外部字段赋值形式：设 obj.field 为 Y（顶层/方法外，obj 为普通变量）。
        # 解析器把「设 d.错误」拍平成名为「d.错误」的 VariableDeclaration，
        # 原生腿需在此降级为 dv_class_set_member（与 src 后端一致）；否则会建一个
        # 字面名为「d.错误」的局部变量，字段写完全丢失——UTF8 解码器 strict 模式
        # 不抛错、原生 SSE 等依赖「实例字段外部改写」的模块 0 事件的根因。
        # 仅处理单级 owner.field；己/self 已由上方方法内分支覆盖。
        if ('.' in name
                and not name.startswith('己.')
                and not name.startswith('self.')):
            owner_name, attr_name = name.split('.', 1)
            if '.' not in attr_name:
                owner_dv = self.get_var(owner_name)
                if owner_dv is None:
                    owner_dv, _ = self._gen_expression(ast.Identifier(name=owner_name))
                if owner_dv is not None:
                    obj_slot = self._store_dv(owner_dv)
                    member_reg = self.gen_string_constant(attr_name)
                    if stmt.value:
                        value_dv, _ = self._gen_expression(stmt.value)
                    else:
                        value_dv = self._create_int_dv('0')
                    value_slot = self._store_dv(value_dv)
                    self.emit(f'call void @dv_class_set_member(ptr {obj_slot}, ptr {member_reg}, ptr {value_slot})')
                    # set_member 会重分配对象缓冲，把 owner 归位到新缓冲（消除悬空/泄漏）
                    updated_dv = self._load_dv(obj_slot)
                    self.set_var(owner_name, updated_dv)
                    return
        self.alloca_local(stmt.name)
        if stmt.value:
            dv_val, _ = self._gen_expression(stmt.value)
        else:
            dv_val = self._create_int_dv('0')
        self.set_var(stmt.name, dv_val)
        var_type = None
        if stmt.type_annotation:
            var_type = self._map_type_name(stmt.type_annotation)
        elif stmt.value:
            var_type = self._infer_expr_type(stmt.value)
        self._set_var_type(stmt.name, var_type)

    def _map_type_name(self, type_name: str) -> Optional[str]:
        """将类型注解名称映射为内部类型常量"""
        type_map = {
            '数': 'INT', '整数': 'INT', 'int': 'INT', 'Int': 'INT',
            '浮点数': 'FLOAT', '小数': 'FLOAT', 'float': 'FLOAT', 'Float': 'FLOAT', 'double': 'FLOAT',
            '布尔': 'BOOL', 'bool': 'BOOL', 'Bool': 'BOOL',
            '串': 'STRING', '字符串': 'STRING', 'str': 'STRING', 'String': 'STRING',
            '列表': 'LIST', '数组': 'LIST', 'list': 'LIST', 'List': 'LIST',
        }
        return type_map.get(type_name)

    def _emit_index_set(self, obj_dv: str, idx_dv: str, value_dv: str) -> str:
        """对容器 dv 做一次索引写入，返回**写入后的新容器** dv。
        dv_index_set 按 obj 真实类型分派（list → dv_list_set 复制出新列表 /
        dict → dv_dict_set 原地更新共享散列表），新容器经 slot0 就地写回。"""
        slot0 = self._store_dv(obj_dv)
        slot1 = self._store_dv(idx_dv)
        slot2 = self._store_dv(value_dv)
        self.emit(f'call void @dv_index_set(ptr {slot0}, ptr {slot0}, ptr {slot1}, ptr {slot2})')
        return self._load_dv(slot0)

    def _writeback_lvalue_root(self, root_ast, container_dv: str):
        """把更新后的最外层容器写回 lvalue 根（变量或 己/对象成员）。"""
        if isinstance(root_ast, ast.Identifier):
            self.set_var(root_ast.name, container_dv)
            return
        if isinstance(root_ast, ast.PropertyAccess):
            member = root_ast.property_name
            if isinstance(root_ast.obj, ast.Identifier) and root_ast.obj.name in ('己', 'self'):
                obj_slot = self._self_lvalue_slot()
            else:
                obj_dv, _ = self._gen_expression(root_ast.obj)
                obj_slot = self._store_dv(obj_dv)
            member_reg = self.gen_string_constant(member)
            value_slot = self._store_dv(container_dv)
            self.emit(f'call void @dv_class_set_member(ptr {obj_slot}, ptr {member_reg}, ptr {value_slot})')
            if isinstance(root_ast.obj, ast.Identifier):
                obj_name = root_ast.obj.name
                set_name = '己' if (self._method_result_ptr is not None and obj_name in ('self', '己')) else obj_name
                self.set_var(set_name, self._load_dv(obj_slot))

    def _gen_typed_index_assign(self, target: ast.IndexAccess, value_dv: str):
        """嵌套容器索引赋值的多层写回（R11A-10 / R11C-2 codegen 侧）。

        dv_index_set 的 list 分支是复制出新容器、dict 分支是原地更新（realloc
        可能换缓冲）——都要求**把新容器写回宿主位置**。对 `设 外[k][0] 为 v`：
          1) 取 外[k] 得到内层容器，写入 v → 新内层容器；
          2) 把新内层容器经 外[k] 写回外容器 → 新外容器；
          3) 递归到根变量 外，整体重绑定。
        旧实现只支持 obj 为 Identifier 的单层（写回根变量即可），嵌套链路的
        中间新容器被丢弃 → 写不进（读回仍是旧值）。本递归把每一层都写回去。"""
        obj_ast = target.obj
        if isinstance(obj_ast, ast.IndexAccess):
            # 更深一层：先写本层，得到新容器，再继续向 obj_ast 所在位置写回
            idx_dv, _ = self._gen_expression(target.index)
            obj_dv, _ = self._gen_expression(obj_ast)
            new_container = self._emit_index_set(obj_dv, idx_dv, value_dv)
            self._gen_typed_index_assign(obj_ast, new_container)
            return
        # 本层 obj 是根（变量 / 成员）
        idx_dv, _ = self._gen_expression(target.index)
        obj_dv, _ = self._gen_expression(obj_ast)
        new_container = self._emit_index_set(obj_dv, idx_dv, value_dv)
        self._writeback_lvalue_root(obj_ast, new_container)

    def _gen_typed_assignment(self, stmt: ast.Assignment):
        if isinstance(stmt.target, ast.PropertyAccess):
            member = stmt.target.property_name
            value_dv, _ = self._gen_expression(stmt.value)
            # 己/self 字段写回：直接取接收者 lvalue 槽位，避免复制出共享缓冲的副本
            # 导致 dv_class_set_member 释放后原 self 悬空（use-after-free，P0-2 SSE 原生崩溃）。
            if isinstance(stmt.target.obj, ast.Identifier) and stmt.target.obj.name in ('己', 'self'):
                obj_slot = self._self_lvalue_slot()
            else:
                obj_dv, _ = self._gen_expression(stmt.target.obj)
                obj_slot = self._store_dv(obj_dv)
            member_reg = self.gen_string_constant(member)
            value_slot = self._store_dv(value_dv)
            self.emit(f'call void @dv_class_set_member(ptr {obj_slot}, ptr {member_reg}, ptr {value_slot})')
            if isinstance(stmt.target.obj, ast.Identifier):
                obj_name = stmt.target.obj.name
                # dv_class_set_member 会重分配对象缓冲，写回时把 self/己 归位到「己」槽位
                set_name = '己' if (self._method_result_ptr is not None and obj_name in ('self', '己')) else obj_name
                updated_dv = self._load_dv(obj_slot)
                self.set_var(set_name, updated_dv)
        elif isinstance(stmt.target, ast.Identifier):
            name = stmt.target.name
            # 方法内部：self.xxx 赋值
            if self._method_result_ptr is not None and name.startswith('self.') and len(name) > 5:
                attr_name = name[5:]
                self_dv = self.get_var('己')
                if self_dv is not None:
                    value_dv, _ = self._gen_expression(stmt.value)
                    obj_slot = self._self_lvalue_slot()
                    member_reg = self.gen_string_constant(attr_name)
                    value_slot = self._store_dv(value_dv)
                    self.emit(f'call void @dv_class_set_member(ptr {obj_slot}, ptr {member_reg}, ptr {value_slot})')
                    updated_dv = self._load_dv(obj_slot)
                    self.set_var('己', updated_dv)
                    return
            # 方法内部：己xxx 赋值
            if self._method_result_ptr is not None and name.startswith('己') and len(name) > 1:
                attr_name = name[1:]
                self_dv = self.get_var('己')
                if self_dv is not None:
                    value_dv, _ = self._gen_expression(stmt.value)
                    obj_slot = self._self_lvalue_slot()
                    member_reg = self.gen_string_constant(attr_name)
                    value_slot = self._store_dv(value_dv)
                    self.emit(f'call void @dv_class_set_member(ptr {obj_slot}, ptr {member_reg}, ptr {value_slot})')
                    updated_dv = self._load_dv(obj_slot)
                    self.set_var('己', updated_dv)
                    return
            name = self._get_var_name(stmt.target)
            dv_val, _ = self._gen_expression(stmt.value)
            self.set_var(name, dv_val)
            if isinstance(stmt.target, ast.Identifier):
                new_type = self._infer_expr_type(stmt.value)
                if new_type is not None:
                    old_type = self._get_var_type(name)
                    if old_type is None or old_type == new_type:
                        self._set_var_type(name, new_type)
                    else:
                        self._set_var_type(name, None)
        elif isinstance(stmt.target, ast.IndexAccess):
            # 容器[键/下标] 为 值：按运行时类型分派（T7B / T5C-03）。
            # 原来无条件 dv_dict_set —— 对列表会把它整体改写成 dict（元素全丢）。
            # T7B 改用 dv_index_set 运行时分派（list → dv_list_set / dict → dv_dict_set）；
            # R12B 进一步支持**嵌套**索引赋值（`外[k][0] 为 v` / `外[0][1] 为 v`）：
            # dv_list_set/dv_dict_set 是「产出新容器」语义，中间层新容器若丢弃则
            # 写不进去——必须沿 lvalue 链逐层把新容器写回其宿主，直到根变量/成员
            # 整体重绑定（R11A-10 / R11C-2 codegen 侧修复）。
            value_dv, _ = self._gen_expression(stmt.value)
            self._gen_typed_index_assign(stmt.target, value_dv)
        else:
            name = self._get_var_name(stmt.target)
            dv_val, _ = self._gen_expression(stmt.value)
            self.set_var(name, dv_val)
            new_type = self._infer_expr_type(stmt.value)
            if new_type is not None:
                old_type = self._get_var_type(name)
                if old_type is None or old_type == new_type:
                    self._set_var_type(name, new_type)
                else:
                    self._set_var_type(name, None)

    def _gen_typed_self_assignment(self, stmt):
        """生成 SelfAssignment 语句（己.属性名 为 值）"""
        self_dv = self.get_var('己')
        if self_dv is None:
            return
        attr_name = stmt.attr_name if hasattr(stmt, 'attr_name') else ''
        value_dv, _ = self._gen_expression(stmt.value)
        obj_slot = self._self_lvalue_slot()
        member_reg = self.gen_string_constant(attr_name)
        value_slot = self._store_dv(value_dv)
        self.emit(f'call void @dv_class_set_member(ptr {obj_slot}, ptr {member_reg}, ptr {value_slot})')
        updated_dv = self._load_dv(obj_slot)
        self.set_var('己', updated_dv)

    def _gen_typed_compound_assignment(self, stmt: ast.CompoundAssignment):
        if isinstance(stmt.target, str):
            name = stmt.target
        else:
            name = self._get_var_name(stmt.target)
        cur = self.get_var(name)
        if cur is None:
            return
        val_dv, _ = self._gen_expression(stmt.value)
        op_map = {'加': 'dv_add', '减': 'dv_sub', '乘': 'dv_mul', '除': 'dv_div',
                  '模': 'dv_mod', '幂': 'dv_pow'}
        func = op_map.get(stmt.operator, 'dv_add')
        result = self._call_dv_func(func, cur, val_dv)
        self.set_var(name, result)

    def _gen_typed_if(self, stmt: ast.IfStatement):
        cond_dv, _ = self._gen_expression(stmt.condition)
        final = self._gen_condition_i1(stmt.condition, cond_dv)

        then_lab = self.new_label('then')
        end_lab = self.new_label('endif')
        else_lab = self.new_label('else') if stmt.else_body else end_lab

        elseif_labs = [self.new_label('elseif') for _ in stmt.elseif_conditions]

        next_lab = elseif_labs[0] if elseif_labs else else_lab
        self.emit(f'br i1 {final}, label %{then_lab}, label %{next_lab}')

        self.emit(f'{then_lab}:')
        for s in stmt.then_body:
            self._gen_statement(s)
        if not self._ends_with_terminator(stmt.then_body):
            self.emit(f'br label %{end_lab}')

        for idx, (eif_cond, eif_body) in enumerate(zip(stmt.elseif_conditions, stmt.elseif_bodies)):
            eif_lab = elseif_labs[idx]
            next_l = elseif_labs[idx + 1] if idx + 1 < len(elseif_labs) else else_lab
            self.emit(f'{eif_lab}:')
            c_dv, _ = self._gen_expression(eif_cond)
            f = self._gen_condition_i1(eif_cond, c_dv)
            e_then = self.new_label('eif_then')
            self.emit(f'br i1 {f}, label %{e_then}, label %{next_l}')
            self.emit(f'{e_then}:')
            for s in eif_body:
                self._gen_statement(s)
            if not self._ends_with_terminator(eif_body):
                self.emit(f'br label %{end_lab}')

        if stmt.else_body:
            self.emit(f'{else_lab}:')
            for s in stmt.else_body:
                self._gen_statement(s)
            if not self._ends_with_terminator(stmt.else_body):
                self.emit(f'br label %{end_lab}')

        # 检查所有分支是否都以终止指令结束
        all_term = self._ends_with_terminator(stmt.then_body)
        for eif_body in (stmt.elseif_bodies or []):
            all_term = all_term and self._ends_with_terminator(eif_body)
        if stmt.else_body:
            all_term = all_term and self._ends_with_terminator(stmt.else_body)
        else:
            all_term = False  # 没有 else 分支时 endif 可达

        if all_term:
            # 所有分支都终止，endif 块不可达，但仍需终止指令
            self.emit(f'{end_lab}:')
            self.emit('unreachable')
        else:
            self.emit(f'{end_lab}:')

    def _gen_typed_foreach(self, stmt: ast.ForeachStatement):
        var_name = stmt.variable if isinstance(stmt.variable, str) else str(stmt.variable)
        self.alloca_local(var_name)
        list_dv, _ = self._gen_expression(stmt.iterable)

        # R10-11b：迭代对象可能是生成器（type=24）。两条消费路径——
        #   生成器：dv_gen_resume 拉一次 → dv_gen_value 取值
        #   列表/字符串/字典：既有 dv_len + dv_foreach_get 索引
        # ——各自的取值块把值写进**同一个**循环变量槽（entry 块预分配，支配
        # 整个循环），再 br 到同一份 body。因此 `跳出`/`跳过` 落点唯一，
        # 循环体只发射一遍，既有列表路径的取值方式一字未改。
        slot = self._store_dv(list_dv)
        is_gen = self.new_register()
        self.emit(f'{is_gen} = call i32 @dv_is_generator(ptr {slot})')
        is_gen_i1 = self.new_register()
        self.emit(f'{is_gen_i1} = icmp ne i32 {is_gen}, 0')

        idx_slot = self._gen_alloca('i64')
        # len_val 不能用 SSA 值跨块传：list_loop 有一条回边来自 foreach_cont
        # （生成器路径也能绕到 cont，静态上 list_init 不支配 list_loop）。
        # 改走内存：entry 预分配两个 i64 槽，list_init 里 store，list_loop 里
        # load——load/store 不是 SSA 值，不适用支配规则。
        len_slot = self._gen_alloca('i64')

        gen_init_lab = self.new_label('foreach_gen_init')
        gen_loop_lab = self.new_label('foreach_gen_loop')
        gen_take_lab = self.new_label('foreach_gen_take')
        list_init_lab = self.new_label('foreach_list_init')
        list_loop_lab = self.new_label('foreach_loop')
        list_take_lab = self.new_label('foreach_list_take')
        body_lab = self.new_label('foreach_body')
        cont_lab = self.new_label('foreach_cont')
        end_lab = self.new_label('foreach_end')
        self._loop_break_labels.append(end_lab)
        self._loop_continue_labels.append(cont_lab)

        self.emit(f'br i1 {is_gen_i1}, label %{gen_init_lab}, label %{list_init_lab}')

        # ── 生成器路径 ──
        self.emit(f'{gen_init_lab}:')
        self.emit(f'br label %{gen_loop_lab}')
        self.emit(f'{gen_loop_lab}:')
        produced = self.new_register()
        self.emit(f'{produced} = call i32 @dv_gen_resume(ptr {slot})')
        produced_i1 = self.new_register()
        self.emit(f'{produced_i1} = icmp ne i32 {produced}, 0')
        self.emit(f'br i1 {produced_i1}, label %{gen_take_lab}, label %{end_lab}')
        self.emit(f'{gen_take_lab}:')
        elem_slot = self._new_dv_slot()
        self.emit(f'call void @dv_gen_value(ptr {elem_slot}, ptr {slot})')
        elem_dv = self.new_register()
        self.emit(f'{elem_dv} = load {LIGHTVALUE_STRUCT}, ptr {elem_slot}')
        self.set_var(var_name, elem_dv)
        self.emit(f'br label %{body_lab}')

        # ── 列表 / 字符串 / 字典路径 ──
        self.emit(f'{list_init_lab}:')
        self.emit(f'store i64 0, ptr {idx_slot}')
        len_val = self.new_register()
        # 用 dv_len（dict/list/str 统一取长）+ dv_foreach_get（list 取元素 / dict 取键）
        self.emit(f'{len_val} = call i64 @dv_len(ptr {slot})')
        self.emit(f'store i64 {len_val}, ptr {len_slot}')
        self.emit(f'br label %{list_loop_lab}')

        self.emit(f'{list_loop_lab}:')
        i = self.new_register()
        self.emit(f'{i} = load i64, ptr {idx_slot}')
        len_v = self.new_register()
        self.emit(f'{len_v} = load i64, ptr {len_slot}')
        cmp = self.new_register()
        self.emit(f'{cmp} = icmp slt i64 {i}, {len_v}')
        self.emit(f'br i1 {cmp}, label %{list_take_lab}, label %{end_lab}')

        self.emit(f'{list_take_lab}:')
        elem = self._call_dv_func('dv_foreach_get', list_dv, f'i64 {i}')
        self.set_var(var_name, elem)
        self.emit(f'br label %{body_lab}')

        # ── 共用循环体 ──
        self.emit(f'{body_lab}:')
        for s in stmt.body:
            self._gen_statement(s)
        if not self._ends_with_terminator(stmt.body):
            self.emit(f'br label %{cont_lab}')

        # ── 步进：列表路推进索引，生成器路的游标长在生成器自己身上 ──
        # 注意必须重新 load：%i 定义在 list_loop_lab，它不支配 cont_lab。
        self.emit(f'{cont_lab}:')
        cur_i = self.new_register()
        self.emit(f'{cur_i} = load i64, ptr {idx_slot}')
        next_i = self.new_register()
        self.emit(f'{next_i} = add i64 {cur_i}, 1')
        self.emit(f'store i64 {next_i}, ptr {idx_slot}')
        self.emit(f'br i1 {is_gen_i1}, label %{gen_loop_lab}, label %{list_loop_lab}')

        self.emit(f'{end_lab}:')
        self._loop_break_labels.pop()
        self._loop_continue_labels.pop()

    def _gen_typed_while(self, stmt: ast.WhileStatement):
        cond_lab = self.new_label('while_cond')
        body_lab = self.new_label('while_body')
        end_lab = self.new_label('while_end')
        self._loop_break_labels.append(end_lab)
        self._loop_continue_labels.append(cond_lab)
        self.emit(f'br label %{cond_lab}')

        self.emit(f'{cond_lab}:')
        cond_dv, _ = self._gen_expression(stmt.condition)
        final = self._gen_condition_i1(stmt.condition, cond_dv)
        self.emit(f'br i1 {final}, label %{body_lab}, label %{end_lab}')

        self.emit(f'{body_lab}:')
        for s in stmt.body:
            self._gen_statement(s)
        if not self._ends_with_terminator(stmt.body):
            self.emit(f'br label %{cond_lab}')

        self.emit(f'{end_lab}:')
        self._loop_break_labels.pop()
        self._loop_continue_labels.pop()

    # ============================================================
    # T7B / T5C-02·T5C-04：段落参数写回（REF 调用约定）
    # ============================================================
    # 背景：段落实参经 `%args` 数组按值浅拷贝进形参槽（`load %struct, store`），
    # 于是在被调方对列表/字典形参的原地修改（追加导致 realloc、字典新增键导致
    # realloc）只改到形参壳，调用方原变量仍持有旧的 list_data 指针 —— 这正是
    # 「追加 对函数参数无效」「字典新增键经参数写回丢失」的根因。
    #
    # 修复：调用约定补上「写回」这一半 ——
    #   被调侧：段落出口把形参槽的值写回 %args[i]；
    #   调用侧：调用返回后把 %args[i] 的值写回实参变量槽。
    # 与 Python 保持一致的一点：形参若在体内被**重新绑定**（`设 形参 为 ...`、
    # 复合赋值、作为遍历变量），则不写回——Python 里重新绑定不影响实参。

    def _collect_rebound_names(self, stmts):
        """收集函数体内被重新绑定的名字集合（用于排除参数写回）。

        T7B 实测修复：此前只查 target/variable 两个字段，漏了主力赋值形态
        VariableDeclaration（`设 x 为 ...` 的重绑目标在 str 字段 name，不是
        Identifier）——导致 rebind 恒为空集、全部形参被登记出口写回，深度递归
        （re.light 回溯 VM 的 跑）的中途回溯态被写回污染调用方。现补齐：
          - VariableDeclaration.name（str）与 destructure_names（列表[str]）
          - Assignment/CompoundAssignment.target（Identifier）
          - ForeachStatement/WithStatement.variable（Identifier）
        """
        names = set()

        def visit(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for n in node:
                    visit(n)
                return
            if isinstance(node, (ast.SegmentDefinition, ast.ClassDefinition)):
                return  # 嵌套段落/类各自成函数，其内重绑与当前函数形参无关
            if isinstance(node, ast.VariableDeclaration):
                if isinstance(node.name, str):
                    names.add(node.name)
                for dn in (node.destructure_names or []):
                    if isinstance(dn, str):
                        names.add(dn)
                for child in self._iter_ast_children(node):
                    visit(child)
                return
            tgt = getattr(node, 'target', None)
            if isinstance(tgt, ast.Identifier):
                names.add(tgt.name)
            var = getattr(node, 'variable', None)
            if isinstance(var, ast.Identifier):
                names.add(var.name)
            # 捕获变量（尝试/捕获 的 捕获变量）
            exc = getattr(node, 'exception_var', None)
            if isinstance(exc, ast.Identifier):
                names.add(exc.name)
            for child in self._iter_ast_children(node):
                visit(child)

        visit(stmts)
        return names

    @staticmethod
    def _split_param_name(pname):
        """拆分 parser 留在参数名里的 `*名字` / `**名字` 变参标记。

        parser（src/parser_stmt.py）把 `接收 *列表们` 产成
        Parameter(name='*列表们')，星号是名字的一部分。codegen 若照单全收，
        局部变量键就成了 '*列表们'，函数体里引用 `列表们` 时 get_var 落空 →
        一路掉进「未知标识符当字符串常量」兜底，于是变参被绑成字符串 "列表们"
        （T5C-05）。返回 (去星号名, 是否 *args, 是否 **kwargs)。
        """
        if isinstance(pname, str) and pname.startswith('**'):
            return pname[2:], False, True
        if isinstance(pname, str) and pname.startswith('*'):
            return pname[1:], True, False
        return pname, False, False

    def _emit_param_writeback(self) -> None:
        """段落返回出口：把「未被重新绑定」的形参槽写回 %args[i]。

        缺参保护是必需的：stdlib 大量用默认参调用（如 `X(a)` 调 `X(a, b=0)`），
        此时 args_arr 只有 num_args 个元素，对 i >= num_args 的形参位置做
        getelementptr + store 就是越界写 —— 实测直接 0xC0000005 段错误。
        """
        wb = getattr(self, '_seg_param_writeback', None)
        if not wb:
            return
        na = getattr(self, '_seg_num_args_reg', None)
        if na is None:
            return
        for i, slot in wb:
            cond = self.new_register()
            self.emit(f'{cond} = icmp slt i64 {i}, {na}')
            t_lab = self.new_label(f'wb_then{i}')
            e_lab = self.new_label(f'wb_end{i}')
            self.emit(f'br i1 {cond}, label %{t_lab}, label %{e_lab}')
            self.emit(f'{t_lab}:')
            elem_ptr = self.new_register()
            self.emit(f'{elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr %args, i64 {i}')
            val = self.new_register()
            self.emit(f'{val} = load {LIGHTVALUE_STRUCT}, ptr {slot}')
            self.emit(f'store {LIGHTVALUE_STRUCT} {val}, ptr {elem_ptr}')
            self.emit(f'br label %{e_lab}')
            self.emit(f'{e_lab}:')

    def _emit_self_writeback(self) -> None:
        """非静态方法的出口前，把局部 己 槽位（其对象缓冲可能已被 dv_class_set_member
        free+realloc）写回 %self，使调用方的对象槽位看到最新缓冲，避免悬空指针 / UAF。

        light 的方法 prologue 会把 %self 按值拷进局部 己 槽位；方法内对 己.字段 的写
        入会改掉 己.str 指向的堆缓冲（free 旧 + malloc 新）。只有把 己 整体写回 %self，
        调用方持有的对象引用才跟着指向新缓冲，否则调用方下次读 obj->str 即 use-after-free
        （SSE 原生崩溃根因）。本函数对实例/类方法且存在 己 槽位时生效；静态方法或普通
        函数为无操作。写回必须在 ret 之前发射，绝不能落在终止指令之后。
        """
        if self._current_method_type == 'static':
            return
        self_var_slot = self._local_vars.get('己')
        if self_var_slot is None:
            return
        self.emit(f'call void @dv_obj_release_slot(ptr %self)')
        self_dv = self.new_register()
        self.emit(f'{self_dv} = load {LIGHTVALUE_STRUCT}, ptr {self_var_slot}')
        self.emit(f'store {LIGHTVALUE_STRUCT} {self_dv}, ptr %self')
        # writeback 移动：%self 取得 己 的缓冲后，清空 己 的持有，使 己 槽位后续
        # 释放（方法出口/被覆盖）为无操作，避免与 %self 双重释放。
        self.emit(f'call void @dv_value_disown(ptr {self_var_slot})')

    def _gen_typed_return(self, stmt: ast.ReturnStatement):
        if self._gen_entry_insert_idx is not None:
            # R10-11b：生成器里的 `返回` 语义是「结束生成」（等价 StopIteration），
            # 不是往 %result 写值——生成器段没有 %result 这个形参，写到那儿
            # 就是 IR 未定义值。返回值本批丢弃（与 `生成` 序列不冲突）。
            self.emit('call void @dv_gen_finish(ptr %gen)')
            self.emit('ret void')
            return
        if self._in_coroutine:
            # 协程函数中的返回：存储结果到 coro->result，设置完成状态
            if stmt.value:
                dv_val, _ = self._gen_expression(stmt.value)
                # 存储到 coro->result
                # 假设 result 字段在 offset 16 (state 4 + resume_point 4 + padding 4 + func ptr 8 = 20? 不对)
                # 让我们用运行时函数更安全
                result_slot = self._store_dv(dv_val)
                self.emit(f'call void @dv_coro_set_result(ptr %coro, ptr {result_slot})')
            # 设置 state = DV_CORO_DONE (3)
            state_ptr = self.new_register()
            self.emit(f'{state_ptr} = getelementptr inbounds i8, ptr %coro, i32 0')
            self.emit(f'store i32 3, ptr {state_ptr}')
            self.emit(f'ret void')
        elif self._method_result_ptr is not None:
            self._emit_return_with_self_writeback(self._method_result_ptr, stmt.value)
        elif self._seg_result_ptr is not None:
            self._emit_return_with_self_writeback(self._seg_result_ptr, stmt.value)
        else:
            if stmt.value:
                # 关键顺序：先求值返回表达式（可能是 己.方法() 尾调用，会改写局部 己 槽位），
                # 再发射 self 写回，确保调用方对象槽位看到返回表达式产生的 己 最新状态。
                dv_val, _ = self._gen_expression(stmt.value)
                self._emit_self_writeback()
                self.emit('call void @dv_stack_pop()')
                self.emit(f'ret {LIGHTVALUE_STRUCT} {dv_val}')
            else:
                self._emit_self_writeback()
                null_dv = self._call_dv_func('dv_null')
                self.emit('call void @dv_stack_pop()')
                self.emit(f'ret {LIGHTVALUE_STRUCT} {null_dv}')

    def _emit_return_with_self_writeback(self, result_ptr: str, value) -> None:
        """方法/段落返回的通用出口：先求值返回表达式（其可能经 己.方法() 尾调用改写
        局部 己 槽位），再发射 self 写回，使 %self（调用方对象槽位）捕获返回表达式产生的
        己 最新状态。此顺序修复了「返回 己.方法()」类尾调用中 self 写回落在嵌套调用之前、
        导致嵌套方法对 己 的改写（如 当前字段 重置）被丢弃的 bug（SSE 原生 0 事件根因）。"""
        if value is not None:
            dv_val, _ = self._gen_expression(value)
            self._emit_self_writeback()
            self.emit(f'call void @dv_obj_release_slot(ptr {result_ptr})')
            self.emit(f'store {LIGHTVALUE_STRUCT} {dv_val}, ptr {result_ptr}')
            self.emit(f'call void @dv_obj_deepcopy_self(ptr {result_ptr})')
        else:
            self._emit_self_writeback()
            self.emit(f'call void @dv_obj_release_slot(ptr {result_ptr})')
            self.emit(f'call void @dv_null(ptr {result_ptr})')
        # T7B / T5C-02·04：显式返回出口也要把形参写回 %args
        self._emit_param_writeback()
        self.emit('call void @dv_stack_pop()')
        self.emit('ret void')

    def _gen_typed_print(self, stmt: ast.PrintStatement):
        if stmt.value:
            dv_val, _ = self._gen_expression(stmt.value)
            slot = self._store_dv(dv_val)
            self.emit(f'call void @dv_println(ptr {slot})')
        else:
            null_slot = self._new_dv_slot()
            self.emit(f'call void @dv_null(ptr {null_slot})')
            self.emit(f'call void @dv_println(ptr {null_slot})')

    # ============================================================
    # 全局初始化
    # ============================================================

    def _gen_builtin_exception_classes(self):
        """注册内置异常类"""
        builtin_exceptions = [
            ("异常", "", ["消息", "类型", "栈追踪", "原因"]),
            ("运行时异常", "异常", []),
            ("值异常", "异常", []),
            ("索引异常", "异常", []),
            ("类型异常", "异常", []),
            ("IO异常", "异常", []),
            ("内存异常", "异常", []),
            ("算术异常", "异常", []),
            # 中文 Python 风格异常名别名（stdlib 直呼 运行时错误/类型错误/值错误 等，
            # 与内置中文名 运行时异常/类型异常/值异常 对齐，继承关系同 Python）
            ("运行时错误", "运行时异常", []),
            ("类型错误", "类型异常", []),
            ("值错误", "值异常", []),
            ("索引错误", "索引异常", []),
            ("读取错误", "IO异常", []),
            ("请求错误", "IO异常", []),
            # "Exception"（英文）是 "异常"（中文）的别名基类：让二者在继承树中
            # 隶属同一根，否则用户代码 `继承 Exception` 抛出的异常无法被 `捕获 异常`
            # 接住（dv_isinstance 沿 super 链走到并列顶层 "Exception" 即失配重抛）。
            ("Exception", "异常", ["消息", "类型", "栈追踪", "原因"]),
            ("RuntimeException", "Exception", []),
            ("ValueError", "Exception", []),
            ("IndexError", "Exception", []),
            ("TypeError", "Exception", []),
            ("IOException", "Exception", []),
            ("MemoryError", "Exception", []),
            ("ArithmeticError", "Exception", []),
        ]
        
        for cls_name, super_name, attrs in builtin_exceptions:
            name_reg = self.gen_string_constant(cls_name)
            super_reg = self.gen_string_constant(super_name)
            _ = self.new_register()
            self.emit(f'{_} = call i32 @dv_register_class(ptr {name_reg}, ptr {super_reg})')
            
            for attr in attrs:
                attr_reg = self.gen_string_constant(attr)
                _ = self.new_register()
                self.emit(f'{_} = call i32 @dv_register_attr(ptr {name_reg}, ptr {attr_reg})')

    def _gen_global_init(self):
        self._current_func = '__init__'
        self._local_vars.clear()
        self._pending_allocas = []
        self._reg_counter = 0
        self._dv_ssa_to_slot.clear()
        self._temp_slot_index = 0
        self.emit(f'define void @__light_init() {{')
        self.emit('entry:')
        
        # 分配临时槽位池
        self._begin_temp_slot_pool()

        self._collect_vars_from_stmts(self._module_statements)
        for vname in self._local_vars.keys():
            reg = self.new_register()
            self.emit(f'{reg} = alloca {LIGHTVALUE_STRUCT}')
            self._local_vars[vname] = reg

        # 注册内置异常类
        self._gen_builtin_exception_classes()

        # 注册所有接口（Level 7）
        for iface_name, iface_def in self._interfaces.items():
            name_reg = self.gen_string_constant(iface_name)
            _ = self.new_register()
            self.emit(f'{_} = call i32 @dv_register_interface(ptr {name_reg})')

            for method in iface_def.methods:
                method_name_reg = self.gen_string_constant(method.name)
                param_count = len(method.parameters)
                sig_reg = self.gen_string_constant(f"{method.name}/{param_count}")
                _ = self.new_register()
                self.emit(f'{_} = call i32 @dv_register_interface_method(ptr {name_reg}, ptr {method_name_reg}, ptr {sig_reg})')

        # 注册所有类
        for cls_name, cls_def in self._classes.items():
            name_reg = self.gen_string_constant(cls_name)
            # 目前只支持单继承，取第一个父类
            super_name = cls_def.superclasses[0] if cls_def.superclasses else ""
            super_reg = self.gen_string_constant(super_name)
            _ = self.new_register()
            self.emit(f'{_} = call i32 @dv_register_class(ptr {name_reg}, ptr {super_reg})')
            
            # 注册属性
            for attr in cls_def.fields:
                attr_reg = self.gen_string_constant(attr.name)
                _ = self.new_register()
                self.emit(f'{_} = call i32 @dv_register_attr(ptr {name_reg}, ptr {attr_reg})')
            
            # 注册方法
            methods = getattr(cls_def, 'methods', []) or []
            for method in methods:
                method_name_reg = self.gen_string_constant(method.name)
                method_safe_name = f'_method_{self._safe_func_name(cls_name)}_{self._safe_func_name(method.name)}'
                method_type = self._get_method_type(method)
                _ = self.new_register()
                if method_type == 'class':
                    self.emit(f'{_} = call i32 @dv_register_class_method(ptr {name_reg}, ptr {method_name_reg}, ptr @{method_safe_name})')
                elif method_type == 'static':
                    self.emit(f'{_} = call i32 @dv_register_static_method(ptr {name_reg}, ptr {method_name_reg}, ptr @{method_safe_name})')
                else:
                    self.emit(f'{_} = call i32 @dv_register_method(ptr {name_reg}, ptr {method_name_reg}, ptr @{method_safe_name})')

            # 注册类实现的接口（Level 7）
            implements = getattr(cls_def, 'interfaces', []) or []
            for iface_name in implements:
                iface_reg = self.gen_string_constant(iface_name)
                _ = self.new_register()
                self.emit(f'{_} = call i32 @dv_register_class_implements(ptr {name_reg}, ptr {iface_reg})')

            # 注册构造函数（方法名与类名相同）
            constructor = getattr(cls_def, 'constructor', None)
            if constructor is not None:
                ctor_name_reg = self.gen_string_constant(cls_name)
                ctor_safe_name = f'_method_{self._safe_func_name(cls_name)}_{self._safe_func_name(cls_name)}'
                _ = self.new_register()
                self.emit(f'{_} = call i32 @dv_register_method(ptr {name_reg}, ptr {ctor_name_reg}, ptr @{ctor_safe_name})')

        for stmt in self._module_statements:
            self._gen_global_statement(stmt)

        self.emit('ret void')
        # 函数体发射完毕，用真实槽位用量回填池大小
        self._emit_temp_slot_pool()
        self.emit('}')
        self.emit_blank()

    def _gen_global_statement(self, stmt):
        if isinstance(stmt, ast.VariableDeclaration):
            name = stmt.name
            if name and name in self._globals:
                if stmt.value:
                    dv_val, _ = self._gen_expression(stmt.value)
                    safe = self._safe_var_name(name)
                    slot_alloc = self._new_dv_slot()
                    # For globals, store LightValue in a global struct
                    self.emit(f'store {LIGHTVALUE_STRUCT} {dv_val}, {LIGHTVALUE_STRUCT}* @__var_{safe}')
                return
        self._gen_statement(stmt)

    def gen_global_var(self, name, init_value=''):
        """覆盖：全局变量存 LightValue"""
        self._globals[name] = init_value

    # ============================================================
    # 段落函数生成
    # ============================================================

    def _gen_typed_segment(self, name, params, body, modifiers=None, module_name=None):
        modifiers = modifiers or []
        is_async = '异步' in modifiers or 'async' in [m.lower() for m in modifiers]
        
        if is_async:
            self._gen_async_segment(name, params, body, module_name)
        elif self._段是生成器(body):
            # R10-11b：段落体里出现了 `生成` → 编成生成器（状态机 + 包装段）
            self._gen_generator_segment(name, params, body, module_name)
        else:
            self._gen_normal_segment(name, params, body, module_name)
    
    def _gen_normal_segment(self, name, params, body, module_name=None):
        """生成普通（非异步）段落函数。

        T9A：module_name 用于 _safe_func_name 模块隔离 + 设置 _current_module
        使段内调用解析到本模块的同名段。
        """
        prev_module = self._current_module
        self._current_module = module_name
        self._current_func = name
        self._current_func_params = {}
        self._local_vars.clear()
        self._pending_allocas = []
        self._reg_counter = 0
        self._dv_ssa_to_slot.clear()
        self._temp_slot_index = 0
        self._seg_result_ptr = '%result'
        safe = self._safe_func_name(name, module_name)

        self.emit(f'define void @_seg_{safe}(ptr %result, ptr %args, i32 %num_args) {{')
        self.emit('entry:')
        
        # 分配临时槽位池（必须是 entry 块的第一个指令，避免动态 alloca）
        self._begin_temp_slot_pool()

        # 生成函数调试信息（DISubprogram）
        if self._debug:
            self._gen_debug_function(name, line=1, param_names=[p[0] for p in params])

        func_name_ptr = self.gen_string_constant(name)
        file_name_ptr = self.gen_string_constant("")
        self.emit(f'call void @dv_stack_push(ptr {func_name_ptr}, ptr {file_name_ptr}, i32 0)')

        self._collect_vars_from_stmts(body)
        # T7B / T5C-05：剥掉变参的 `*`/`**` 前缀后再登记局部变量
        cleaned_params = []
        vararg_kind = {}  # 形参下标 -> 'args' | 'kwargs'
        for idx, (pname, default_val) in enumerate(params):
            clean, is_va, is_kw = self._split_param_name(pname)
            cleaned_params.append((clean, default_val))
            if is_kw:
                vararg_kind[idx] = 'kwargs'
            elif is_va:
                vararg_kind[idx] = 'args'
        for clean, _ in cleaned_params:
            self._local_vars[clean] = None

        for vname in self._local_vars.keys():
            reg = self.new_register()
            self.emit(f'{reg} = alloca {LIGHTVALUE_STRUCT}')
            self._local_vars[vname] = reg

        if params:
            num_args_sext = self.new_register()
            self.emit(f'{num_args_sext} = sext i32 %num_args to i64')
            # T7B：供 _emit_param_writeback 做越界判断
            self._seg_num_args_reg = num_args_sext

        for i, (pname, default_val) in enumerate(cleaned_params):
            param_slot = self._local_vars.get(pname)
            if param_slot is not None:
                # T7B / T5C-05：变参——把第 i 个起的全部剩余实参打包成列表/字典
                if i in vararg_kind:
                    fn = ('dv_collect_kwargs' if vararg_kind[i] == 'kwargs'
                          else 'dv_collect_varargs')
                    self.emit(f'call void @{fn}(ptr {param_slot}, ptr %args, i64 {num_args_sext}, i64 {i})')
                    continue
                in_bounds = self.new_register()
                self.emit(f'{in_bounds} = icmp slt i64 {i}, {num_args_sext}')
                then_lab = self.new_label('param_valid')
                else_lab = self.new_label('param_invalid')
                end_lab = self.new_label('param_end')
                self.emit(f'br i1 {in_bounds}, label %{then_lab}, label %{else_lab}')
                self.emit(f'{then_lab}:')
                elem_ptr = self.new_register()
                self.emit(f'{elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr %args, i64 {i}')
                param_val = self.new_register()
                self.emit(f'{param_val} = load {LIGHTVALUE_STRUCT}, ptr {elem_ptr}')
                self.emit(f'store {LIGHTVALUE_STRUCT} {param_val}, ptr {param_slot}')
                self.emit(f'br label %{end_lab}')
                self.emit(f'{else_lab}:')
                # 缺参：应用默认值（stdlib 的 缩进 = 0 / 美化 = 假 等），无默认值才用 null
                if default_val is not None:
                    default_dv, _ = self._gen_expression(default_val)
                    self.emit(f'store {LIGHTVALUE_STRUCT} {default_dv}, ptr {param_slot}')
                else:
                    null_slot = self._new_dv_slot()
                    self.emit(f'call void @dv_null(ptr {null_slot})')
                    null_val = self.new_register()
                    self.emit(f'{null_val} = load {LIGHTVALUE_STRUCT}, ptr {null_slot}')
                    self.emit(f'store {LIGHTVALUE_STRUCT} {null_val}, ptr {param_slot}')
                self.emit(f'br label %{end_lab}')
                self.emit(f'{end_lab}:')

        # T7B / T5C-02·04：登记出口写回的形参。
        # 排除：①变参（是新建容器，与实参无共享关系）；②体内被重新绑定的形参
        # （Python 语义：重新绑定不影响实参，写回反而会污染调用方变量）。
        rebound = self._collect_rebound_names(body)
        self._seg_param_writeback = []
        for i, (pname, _) in enumerate(cleaned_params):
            if i in vararg_kind or pname in rebound:
                continue
            slot = self._local_vars.get(pname)
            if slot is not None:
                self._seg_param_writeback.append((i, slot))

        for stmt in body:
            self._gen_statement(stmt)

        if not self._ends_with_terminator(body):
            self._emit_param_writeback()
            self.emit(f'call void @dv_null(ptr %result)')
            self.emit('call void @dv_stack_pop()')
            self.emit('ret void')
        # 函数体发射完毕，用真实槽位用量回填池大小
        self._emit_temp_slot_pool()
        self.emit('}')
        self.emit_blank()
        self._seg_param_writeback = []
        self._seg_num_args_reg = None
        self._seg_result_ptr = None
        self._current_module = prev_module
        # 结束函数调试作用域
        self._end_debug_function()

    # ============================================================
    # 生成器段（R10-11b 第四批B）
    # ============================================================
    # 形态：一个生成器段编出一对函数
    #   1. @_genf_<名>(ptr %gen)                     状态机（可重复进入）
    #   2. @_seg_<名>(ptr %result, ptr %args, i32)    包装段（建生成器 + 抄实参）
    # 与既有协程（@_coro_*）不共用：协程是推送式（调度器一路跑到完，挂起点
    # 由 sleep/io 驱动），生成器是拉取式（挂起在 `生成` 处把值交回消费者，
    # 下次 resume 从挂起点继续）。两套编号语义正交，混用会把 await 点与
    # yield 点搅在一起，故独立实现。
    def _gen_generator_segment(self, name, params, body, module_name=None):
        prev_module = self._current_module
        self._current_module = module_name
        safe = self._safe_func_name(name, module_name)
        gen_func_name = f'_genf_{safe}'
        生成点数 = self._段内生成点(body, 计数=True)

        # ── 1. 状态机函数 ──────────────────────────────────────────
        self._current_func = name
        self._current_func_params = {}
        self._local_vars.clear()
        self._pending_allocas = []
        self._reg_counter = 0
        self._dv_ssa_to_slot.clear()
        self._temp_slot_index = 0
        # 生成器不用栈上临时池：跨 `生成` 存活的状态必须在 gen->slots（堆）上
        self._temp_slot_pool = None
        self._temp_slot_pool_line = None
        self._seg_result_ptr = None
        self._current_module = prev_module
        self._gen_yield_index = 0
        self._gen_slot_index = 0
        self._gen_entry_name_seq = 0

        self.emit(f'define void @{gen_func_name}(ptr %gen) {{')
        self.emit('entry:')
        state = self.new_register()
        self.emit(f'{state} = call i32 @dv_gen_state(ptr %gen)')
        # 恢复标签按预扫到的生成点数一次造齐——entry 的 switch 必须先知道全部落点
        self._gen_resume_labels = [self.new_label(f'gen_resume_{i + 1}')
                                   for i in range(生成点数)]
        init_lab = self.new_label('gen_init')
        # 插入点必须在 switch **之前**：之后所有槽位指针 / alloca 都插到这里，
        # 每插一条就把 switch 往下推一行，于是它们始终留在 entry 块内、
        # 终止指令之前，且支配 init 块与全部恢复块。
        self._gen_entry_insert_idx = len(self._lines)
        if 生成点数:
            cases = ' '.join(f'i32 {i + 1}, label %{lab}'
                             for i, lab in enumerate(self._gen_resume_labels))
            self.emit(f'switch i32 {state}, label %{init_lab} [ {cases} ]')
        else:
            self.emit(f'br label %{init_lab}')

        self._collect_vars_from_stmts(body)
        param_names = [p[0] for p in params]
        for pname in param_names:
            self._local_vars[pname] = None
        # 参数先发槽：包装段按 0..n-1 抄实参，顺序必须对得上
        for pname in param_names:
            self._local_vars[pname] = self._gen_new_slot()
        for vname in list(self._local_vars.keys()):
            if self._local_vars[vname] is None:
                self._local_vars[vname] = self._gen_new_slot()

        self.emit(f'{init_lab}:')
        for stmt in body:
            self._gen_statement(stmt)

        # 收尾：正文可能已经以 `ret void` 结束（最后一个 `生成`，或 `返回`），
        # 那就先起新块再发 finish，避免同一块里两条终止指令。
        done_lab = self.new_label('gen_done')
        if not self._当前块已终止():
            self.emit(f'br label %{done_lab}')
        self.emit(f'{done_lab}:')
        self.emit('call void @dv_gen_finish(ptr %gen)')
        self.emit('ret void')
        self.emit('}')
        self.emit_blank()

        槽位数 = max(self._gen_slot_index, 1)
        self._gen_entry_insert_idx = None
        self._gen_resume_labels = []
        self._gen_yield_index = 0

        # ── 2. 包装段函数 ──────────────────────────────────────────
        self._current_func = name
        self._current_func_params = {}
        self._local_vars.clear()
        self._pending_allocas = []
        self._reg_counter = 0
        self._dv_ssa_to_slot.clear()
        self._temp_slot_index = 0
        self._seg_result_ptr = '%result'

        self.emit(f'define void @_seg_{safe}(ptr %result, ptr %args, i32 %num_args) {{')
        self.emit('entry:')
        self._begin_temp_slot_pool()

        gen_ptr = self.new_register()
        self.emit(f'{gen_ptr} = call ptr @dv_gen_create(ptr @{gen_func_name}, i32 {槽位数})')

        if params:
            num_args_sext = self.new_register()
            self.emit(f'{num_args_sext} = sext i32 %num_args to i64')

        for i, (pname, default_val) in enumerate(params):
            in_bounds = self.new_register()
            self.emit(f'{in_bounds} = icmp slt i64 {i}, {num_args_sext}')
            then_lab = self.new_label('gen_arg_ok')
            else_lab = self.new_label('gen_arg_default')
            end_lab = self.new_label('gen_arg_end')
            self.emit(f'br i1 {in_bounds}, label %{then_lab}, label %{else_lab}')

            self.emit(f'{then_lab}:')
            src = self.new_register()
            self.emit(f'{src} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr %args, i64 {i}')
            val = self.new_register()
            self.emit(f'{val} = load {LIGHTVALUE_STRUCT}, ptr {src}')
            dst = self.new_register()
            self.emit(f'{dst} = call ptr @dv_gen_slot(ptr {gen_ptr}, i32 {i})')
            self.emit(f'store {LIGHTVALUE_STRUCT} {val}, ptr {dst}')
            self.emit(f'br label %{end_lab}')

            self.emit(f'{else_lab}:')
            dst2 = self.new_register()
            self.emit(f'{dst2} = call ptr @dv_gen_slot(ptr {gen_ptr}, i32 {i})')
            if default_val is not None:
                default_dv, _ = self._gen_expression(default_val)
                self.emit(f'store {LIGHTVALUE_STRUCT} {default_dv}, ptr {dst2}')
            else:
                self.emit(f'call void @dv_null(ptr {dst2})')
            self.emit(f'br label %{end_lab}')

            self.emit(f'{end_lab}:')

        # 包成 LightValue（type=24，str 存 LightGenerator*）返回
        self.emit(f'call void @dv_gen_make(ptr %result, ptr {gen_ptr})')
        self.emit('ret void')
        self._emit_temp_slot_pool()
        self.emit('}')
        self.emit_blank()
        self._seg_result_ptr = None

    def _gen_typed_yield(self, stmt: ast.YieldStatement):
        """`生成 表达式。` —— 生成器的挂起点。

        三件事：把值克隆进 ``gen->yielded``、写入「下一个恢复点」编号、然后
        ``ret void`` 把控制权交还消费者；恢复标签紧跟其后，下次 resume 时
        entry 的 switch 直接落到这里继续。

        编号靠 ``_gen_yield_index`` 按**发射顺序**递增，标签由预扫按**个数**
        造好，两者一一对应：漏行 / 乱序 / 复用同一恢复点都会让 IR 自相矛盾
        （switch 落点缺失或重复），编译期就炸，不会静默跑出漏行。
        """
        if self._gen_entry_insert_idx is None:
            raise NotImplementedError(
                f"原生后端暂不支持语句类型「YieldStmt」（源码行 "
                f"{self._stmt_source_line(stmt)}）：`生成` 只能用在段落体内，"
                f"该段落会被编译为生成器；此处没有消费者。"
                f"{self._FALLBACK_HINT}")
        if getattr(stmt, 'is_from', False):
            raise NotImplementedError(
                f"原生后端暂不支持语句类型「YieldFromStmt」（源码行 "
                f"{self._stmt_source_line(stmt)}）：`生成 全部 X`（生成器委托）"
                f"未实现，请改写为 `遍历 项 之 X：` + `生成 项。`。"
                f"{self._FALLBACK_HINT}")
        self._gen_yield_index += 1
        k = self._gen_yield_index
        if k > len(self._gen_resume_labels):
            raise RuntimeError(
                f"生成器「{self._current_func}」第 {k} 个 `生成` 超出预扫到的 "
                f"{len(self._gen_resume_labels)} 个恢复点——预扫与发射走了不同的"
                f"分支遍历，状态机编号已不可信")
        if stmt.value is not None:
            dv_val, _ = self._gen_expression(stmt.value)
            val_slot = self._store_dv(dv_val)
        else:
            val_slot = self._new_dv_slot()
            self.emit(f'call void @dv_null(ptr {val_slot})')
        self.emit(f'call void @dv_gen_yield(ptr %gen, ptr {val_slot}, i32 {k})')
        self.emit('ret void')
        self.emit(f'{self._gen_resume_labels[k - 1]}:')

    def _gen_async_segment(self, name, params, body, module_name=None):
        """生成异步段落：包括协程函数和包装段函数
        
        生成两个函数：
        1. _coro_xxx(ptr %coro) - 协程状态机函数（Duff's device 模式）
        2. _seg_xxx(ptr %result, ptr %args, i32 %num_args) - 包装函数，创建协程
        """
        prev_module = self._current_module
        self._current_module = module_name
        safe = self._safe_func_name(name, module_name)
        coro_func_name = f'_coro_{safe}'
        
        # 第一步：生成协程状态机函数
        self._gen_coroutine_function(name, params, body, coro_func_name)
        
        # 第二步：生成包装段函数（创建协程并返回）
        self._current_func = name
        self._current_func_params = {}
        self._local_vars.clear()
        self._pending_allocas = []
        self._reg_counter = 0
        self._seg_result_ptr = '%result'
        self._in_coroutine = False
        
        self.emit(f'define void @_seg_{safe}(ptr %result, ptr %args, i32 %num_args) {{')
        self.emit('entry:')
        
        func_name_ptr = self.gen_string_constant(name)
        file_name_ptr = self.gen_string_constant("")
        self.emit(f'call void @dv_stack_push(ptr {func_name_ptr}, ptr {file_name_ptr}, i32 0)')
        
        # 获取协程函数指针
        coro_func_ptr = self.new_register()
        self.emit(f'{coro_func_ptr} = ptrtoint ptr @{coro_func_name} to i64')
        
        # 计算局部变量数量
        self._collect_vars_from_stmts(body)
        num_locals = len(self._local_vars)
        num_params = len(params)
        
        # 调用 dv_coro_create 创建协程
        coro_handle = self.new_register()
        self.emit(f'{coro_handle} = call ptr @dv_coro_create(ptr @{coro_func_name}, ptr %args, i32 %num_args, i32 {num_locals + num_params})')
        
        # 将协程句柄存储到 result 中（作为指针值存储在 LightValue 中）
        # 我们用 LightValue 的 type=DV_COROUTINE, value.ptr_val = coro_handle
        self._store_coro_to_result(coro_handle, '%result')
        
        self.emit('call void @dv_stack_pop()')
        self.emit('ret void')
        self.emit('}')
        self.emit_blank()
        self._seg_result_ptr = None
    
    def _store_coro_to_result(self, coro_ptr, result_ptr):
        """将协程指针存储到 LightValue result 中"""
        # 设置 type = 100 (DV_TYPE_COROUTINE)
        type_ptr = self.new_register()
        self.emit(f'{type_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {result_ptr}, i32 0, i32 0')
        self.emit(f'store i32 100, ptr {type_ptr}')
        
        # 设置 ptr_val = coro_ptr
        ptr_val_ptr = self.new_register()
        self.emit(f'{ptr_val_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {result_ptr}, i32 0, i32 3')
        self.emit(f'store ptr {coro_ptr}, ptr {ptr_val_ptr}')
    
    def _gen_coroutine_function(self, name, params, body, coro_func_name):
        """生成协程状态机函数（Duff's device 模式）
        
        函数签名: void @_coro_xxx(ptr %coro)
        - %coro: 指向 LightCoroutine 结构体的指针
        
        使用两阶段法：
        1. 预扫描统计 await 点数量
        2. 生成带完整 switch 的函数
        """
        # 第一阶段：预扫描统计 await 点
        num_await = self._count_await_points(body)
        
        self._current_func = name + '$coro'
        self._current_func_params = {}
        self._local_vars.clear()
        self._pending_allocas = []
        self._reg_counter = 0
        self._in_coroutine = True
        self._coro_handle_ptr = '%coro'
        self._coro_resume_point = 0
        # 保存 await 点标签映射: point_num -> resume_label
        self._coro_resume_labels = {}
        # 初始化临时槽位池（否则会使用上一个函数残留的池指针）
        self._temp_slot_index = 0
        self._dv_ssa_to_slot = {}
        
        # 协程函数定义处。B7 曾在此挂 TODO(移交:A7)，说「O2 会打坏协程 yield
        # 基本块（Duff's device），也许得在这儿发 optnone/noinline」——
        # **A7 已实测证伪**：O0/O1/O2/O3 四档全绿（12 格矩阵，见
        # tests/test_native_cli.py），协程在任何优化档下都对。当时那批 O2 崩溃的
        # 真元凶是 startup_optimizer.py 把函数属性写在返回类型之后产出非法 IR
        # （每个程序都有 __light_init，所以 O3 对任何源码都炸），以及
        # optimizer_pipeline 用 `\{[^}]*\}` 匹配函数体、遇到 `alloca { i64, i8* }`
        # 就把函数腰斩。两处 A7 已修。结论：**这里不需要加属性**。
        self.emit(f'define void @{coro_func_name}(ptr %result, ptr %coro, ptr %args, i32 %num_args) {{')
        self.emit('entry:')
        
        # 分配临时槽位池
        self._begin_temp_slot_pool()
        
        # 收集变量
        self._collect_vars_from_stmts(body)
        for param_name, _ in params:
            self._local_vars[param_name] = None
        
        # 为协程局部变量分配索引（使用 coro->locals 数组，跨 await 持久化）
        var_names = list(self._local_vars.keys())
        self._coro_local_indices = {}  # var_name -> index
        for i, vname in enumerate(var_names):
            # 参数也放在 locals 中（索引 0..num_params-1）
            # 注意：dv_coro_create 的 num_locals 参数控制 locals 数组大小
            local_ptr = self.new_register()
            self.emit(f'{local_ptr} = call ptr @dv_coro_get_local(ptr %coro, i32 {i})')
            self._local_vars[vname] = local_ptr
            self._coro_local_indices[vname] = i
        
        # 将参数从 coro->args 复制到 coro->locals（每次调用都执行，确保参数可用）
        for i, (pname, _) in enumerate(params):
            local_ptr = self._local_vars.get(pname)
            if local_ptr is not None:
                arg_ptr = self.new_register()
                self.emit(f'{arg_ptr} = call ptr @dv_coro_get_arg(ptr %coro, i32 {i})')
                arg_val = self.new_register()
                self.emit(f'{arg_val} = load {LIGHTVALUE_STRUCT}, ptr {arg_ptr}')
                self.emit(f'store {LIGHTVALUE_STRUCT} {arg_val}, ptr {local_ptr}')
        
        # 加载 resume_point
        # resume_point 在 LightCoroutine 的 offset 4 (state 在 offset 0)
        rp_ptr = self.new_register()
        self.emit(f'{rp_ptr} = getelementptr inbounds i8, ptr %coro, i32 4')
        rp_val = self.new_register()
        self.emit(f'{rp_val} = load i32, ptr {rp_ptr}')
        
        # 预先生成所有 resume 标签名
        resume_labels = []
        for i in range(num_await + 1):
            resume_labels.append(self.new_label(f'resume_{i}'))
            self._coro_resume_labels[i] = resume_labels[i]
        
        # 生成 switch 语句（单行，避免验证器将 case 行误判为终止指令后的死代码）
        switch_end_label = self.new_label('coro_switch_end')
        cases = ' '.join(f'i32 {i}, label %{resume_labels[i]}' for i in range(num_await + 1))
        self.emit(f'switch i32 {rp_val}, label %{switch_end_label} [ {cases} ]')
        
        # 生成每个 resume 点和对应的代码
        # 注意：我们只有一个 resume_0 作为入口，然后在生成 body 时遇到 await 再插入 resume_N
        # 但 switch 已经引用了所有 resume_N 标签，所以它们必须存在
        # 策略：先生成 resume_0:，然后生成 body
        # 遇到 await 时，生成挂起代码 + ret void，然后生成下一个 resume_N:
        # 这样所有的 resume_N 标签都会被定义
        
        # resume_0: 开始执行
        self.emit(f'{resume_labels[0]}:')
        
        # 生成函数体语句
        for stmt in body:
            self._gen_statement(stmt)
        
        # 协程结束：设置 state = DONE
        if not self._ends_with_terminator(body):
            self._gen_coro_return()
        
        # switch_end: 无效 resume_point
        self.emit(f'{switch_end_label}:')
        self.emit(f'ret void')
        
        # 函数体发射完毕，用真实槽位用量回填池大小
        self._emit_temp_slot_pool()
        self.emit('}')
        self.emit_blank()
        
        self._in_coroutine = False
        self._current_module = prev_module
        self._coro_handle_ptr = None
        self._coro_resume_point = 0
        self._coro_resume_labels = None
    
    def _gen_coro_return(self):
        """生成协程返回（设置完成状态）"""
        # 设置 state = DV_CORO_DONE (3)
        state_ptr = self.new_register()
        self.emit(f'{state_ptr} = getelementptr inbounds i8, ptr %coro, i32 0')
        self.emit(f'store i32 3, ptr {state_ptr}')
        self.emit(f'ret void')
    
    def _count_await_points(self, stmts) -> int:
        """预扫描语句块，统计 await 点数量"""
        count = 0
        for stmt in stmts:
            count += self._count_await_in_node(stmt)
        return count
    
    def _count_await_in_node(self, node) -> int:
        """递归统计节点中的 await 点数量"""
        if node is None:
            return 0
        
        count = 0
        
        # AwaitExpression 本身是一个 await 点
        if hasattr(ast, 'AwaitExpression') and isinstance(node, ast.AwaitExpression):
            count += 1
            # 还要统计 expression 内部的 await（嵌套 await）
            count += self._count_await_in_node(node.expression)
            return count
        
        # 语句块 / 段落 / 循环：body 是 list
        if isinstance(node, (ast.SegmentDefinition, ast.ForeachStatement, ast.WhileStatement)) and hasattr(node, 'body') and isinstance(node.body, list):
            for s in node.body:
                count += self._count_await_in_node(s)
            # WhileStatement 还有 condition
            if isinstance(node, ast.WhileStatement):
                count += self._count_await_in_node(getattr(node, 'condition', None))
            # ForeachStatement 还有 iterable
            if isinstance(node, ast.ForeachStatement):
                count += self._count_await_in_node(getattr(node, 'iterable', None))
            return count
        
        # if 语句
        if isinstance(node, ast.IfStatement):
            count += self._count_await_in_node(getattr(node, 'condition', None))
            for s in (node.then_body or []):
                count += self._count_await_in_node(s)
            if node.else_body:
                for s in node.else_body:
                    count += self._count_await_in_node(s)
            for cond, body in zip(getattr(node, 'elseif_conditions', []) or [], getattr(node, 'elseif_bodies', []) or []):
                count += self._count_await_in_node(cond)
                for s in (body or []):
                    count += self._count_await_in_node(s)
            return count
        
        # 变量声明 / 赋值 / 返回语句：都有 value
        if isinstance(node, (ast.VariableDeclaration, ast.Assignment, ast.CompoundAssignment, ast.ReturnStatement)):
            count += self._count_await_in_node(getattr(node, 'value', None))
            if isinstance(node, ast.Assignment):
                count += self._count_await_in_node(getattr(node, 'target', None))
            return count
        
        # 表达式语句
        if isinstance(node, ast.ExpressionStatement):
            return self._count_await_in_node(node.expression)
        
        # 二元/一元运算
        if isinstance(node, ast.BinaryOp):
            count += self._count_await_in_node(node.left)
            count += self._count_await_in_node(node.right)
            return count
        if isinstance(node, ast.UnaryOp):
            return self._count_await_in_node(node.operand)
        
        # 函数调用
        if isinstance(node, ast.FunctionCall):
            # 睡眠/await_io 是 yield 点（在协程中产生 ret void + resume label）
            call_name = None
            if hasattr(node, 'name'):
                if hasattr(node.name, 'name'):
                    call_name = node.name.name
                elif isinstance(node.name, str):
                    call_name = node.name
            if call_name in ('睡眠', 'sleep', 'await_io'):
                count += 1
            for arg in (node.arguments or []):
                count += self._count_await_in_node(arg)
            return count
        
        return count
    
    def _gen_await_expression(self, expr) -> Tuple[str, str]:
        """生成 await 表达式代码
        
        在协程函数中：
        1. 计算子表达式得到 future/协程
        2. 设置 resume_point = 当前点编号 + 1
        3. 调用 dv_coro_await 挂起
        4. ret void
        5. 恢复标签已在 switch 中预定义，下次从这里继续
        6. 返回 future 的结果
        
        不在协程中：直接返回子表达式结果（退化情况）
        """
        if not self._in_coroutine:
            # 不在协程中，直接求值子表达式
            return self._gen_expression(expr.expression)
        
        # 在协程中，生成挂起/恢复代码
        # 第一步：计算子表达式（future/协程）
        future_dv, _ = self._gen_expression(expr.expression)
        
        # 获取当前 await 点编号
        point_num = self._coro_resume_point
        self._coro_resume_point += 1
        
        # 生成 await 前的标签（用于调试）
        await_label = self.new_label(f'await_{point_num}')
        # 恢复标签已经在 switch 中预生成了
        resume_label = self._coro_resume_labels.get(point_num + 1)
        
        # 跳转到 await 标签（前一个基本块需要 terminator）
        self.emit(f'br label %{await_label}')
        self.emit(f'{await_label}:')
        
        # 设置 resume_point = point_num + 1（下次恢复时跳到 resume_N）
        # resume_point 在 coro 结构体的 offset 4
        rp_ptr = self.new_register()
        self.emit(f'{rp_ptr} = getelementptr inbounds i8, ptr %coro, i32 4')
        self.emit(f'store i32 {point_num + 1}, ptr {rp_ptr}')
        
        # 从 future_dv 中提取 future 指针
        future_ptr = self._extract_ptr_from_dv(future_dv)
        
        # 调用 dv_coro_await(coro, future)
        self.emit(f'call void @dv_coro_await(ptr %coro, ptr {future_ptr})')
        
        # 挂起返回
        self.emit(f'ret void')
        
        # 恢复点标签（必须定义，switch 引用了它）
        if resume_label:
            self.emit(f'{resume_label}:')
        else:
            # 理论上不应该发生，预扫描应该算准了
            fallback_label = self.new_label(f'resume_fallback_{point_num}')
            self.emit(f'{fallback_label}:')
        
        # 从 future 中获取结果
        result_slot = self._new_dv_slot()
        self.emit(f'call void @dv_coro_get_await_result(ptr %coro, ptr {result_slot})')
        
        # 加载结果
        result_val = self._load_dv(result_slot)
        return result_val, 'dv'
    
    def _extract_ptr_from_dv(self, dv_val: str) -> str:
        """从 LightValue 中提取 ptr_val 字段"""
        # 需要先 store 到内存，然后用 GEP 取 ptr_val
        slot = self._store_dv(dv_val)
        ptr_val_ptr = self.new_register()
        self.emit(f'{ptr_val_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {slot}, i32 0, i32 3')
        ptr_val = self.new_register()
        self.emit(f'{ptr_val} = load ptr, ptr {ptr_val_ptr}')
        return ptr_val
    
    def _gen_async_scope(self, scope):
        """生成异步作用域（结构化并发）
        
        伪代码:
        1. 为每个任务创建协程
        2. 将所有协程加入调度器
        3. 运行调度器直到所有任务完成
        4. 收集结果（如果有 result_vars）
        """
        tasks = scope.tasks or []
        num_tasks = len(tasks)
        
        if num_tasks == 0:
            return
        
        # 存储所有协程句柄
        coro_handles = []
        
        for i, task in enumerate(tasks):
            # 任务是一个表达式（通常是异步函数调用）
            # 计算表达式得到协程句柄
            coro_dv, _ = self._gen_expression(task)
            coro_ptr = self._extract_ptr_from_dv(coro_dv)
            coro_handles.append(coro_ptr)
        
        # 将所有协程加入调度器队列并运行
        # 简化：逐个调用 dv_coro_run_to_completion
        # 注意：这不是真正的并发，只是串行执行
        # 真正的并发需要调度器队列
        for i, coro_ptr in enumerate(coro_handles):
            self.emit(f'call void @dv_coro_run_to_completion(ptr {coro_ptr})')
        
        # 如果有 result_vars，收集结果
        result_vars = getattr(scope, 'result_vars', None) or []
        for i, var_name in enumerate(result_vars):
            if i >= len(coro_handles):
                break
            result_slot = self._new_dv_slot()
            # 调用 dv_coro_get_result 获取结果指针
            result_ptr = self.new_register()
            self.emit(f'{result_ptr} = call ptr @dv_coro_get_result(ptr {coro_handles[i]})')
            # 复制结果
            result_val = self.new_register()
            self.emit(f'{result_val} = load {LIGHTVALUE_STRUCT}, ptr {result_ptr}')
            # 存储到变量
            self.alloca_local(var_name)
            var_slot = self._local_vars.get(var_name)
            if var_slot:
                self.emit(f'store {LIGHTVALUE_STRUCT} {result_val}, ptr {var_slot}')

    def _gen_module_alias(self, module_name: str, seg_name: str, safe_name: str):
        """为段函数生成模块前缀别名，使其他模块可通过 @_seg_{模块名}_{函数名} 引用"""
        alias_name = self._safe_func_name(f'{module_name}_{seg_name}')
        if alias_name != safe_name:
            self.emit(f'@_seg_{alias_name} = alias void (ptr, ptr, i32), void (ptr, ptr, i32)* @_seg_{safe_name}')

    def _gen_typed_class_methods(self, class_name, cls_def):
        """生成类的所有方法"""
        methods = getattr(cls_def, 'methods', []) or []
        for method in methods:
            self._gen_typed_method(class_name, method)
        constructor = getattr(cls_def, 'constructor', None)
        if constructor is not None:
            self._gen_typed_constructor(class_name, constructor)

    def _gen_typed_method(self, class_name, method_def):
        """生成单个方法函数
        
        根据方法类型生成不同签名：
        - 实例方法: void @_method_xxx(ptr result, ptr self, ptr args, i32 num_args)
        - 类方法: void @_method_xxx(ptr result, ptr cls_val, ptr args, i32 num_args)
        - 静态方法: void @_method_xxx(ptr result, ptr args, i32 num_args)
        """
        method_type = self._get_method_type(method_def)
        self._current_func = f'{class_name}.{method_def.name}'
        self._current_func_params = {}
        self._local_vars.clear()
        self._pending_allocas = []
        self._reg_counter = 0
        self._dv_ssa_to_slot.clear()
        self._temp_slot_index = 0
        self._temp_slot_pool = None
        self._temp_slot_pool_line = None
        self._method_result_ptr = '%result'
        self._current_class = class_name
        self._current_method_type = method_type

        method_safe_name = f'_method_{self._safe_func_name(class_name)}_{self._safe_func_name(method_def.name)}'

        if method_type == 'static':
            self.emit(f'define void @{method_safe_name}(ptr %result, ptr %args, i32 %num_args) {{')
        else:
            self.emit(f'define void @{method_safe_name}(ptr %result, ptr %self, ptr %args, i32 %num_args) {{')
        self.emit('entry:')

        # 分配临时槽位池（必须在 entry 块内、分支出现前，避免动态 alloca 爆栈）
        self._begin_temp_slot_pool()

        # 生成函数调试信息（DISubprogram）
        if self._debug:
            method_name_dbg = f'{class_name}.{method_def.name}'
            params_dbg = [p.name if hasattr(p, 'name') else str(p) for p in (getattr(method_def, 'parameters', []) or [])]
            if method_type != 'static':
                params_dbg = ['己'] + params_dbg
            self._gen_debug_function(method_name_dbg, line=getattr(method_def, 'lineno', 1), param_names=params_dbg)

        # 栈追踪：方法入口压栈
        method_name = f'{class_name}.{method_def.name}'
        func_name_ptr = self.gen_string_constant(method_name)
        file_name_ptr = self.gen_string_constant("")
        self.emit(f'call void @dv_stack_push(ptr {func_name_ptr}, ptr {file_name_ptr}, i32 0)')

        params = getattr(method_def, 'parameters', []) or []

        self._collect_vars_from_stmts(getattr(method_def, 'body', []) or [])
        
        # 添加己（self/cls）变量（仅实例方法和类方法有）
        if method_type != 'static':
            self._local_vars['己'] = None
        # 添加方法参数
        for param in params:
            pname = param.name if hasattr(param, 'name') else str(param)
            self._local_vars[pname] = None

        for vname in self._local_vars.keys():
            reg = self.new_register()
            self.emit(f'{reg} = alloca {LIGHTVALUE_STRUCT}')
            self._local_vars[vname] = reg

        # 加载 self/cls 变量（仅实例方法和类方法有）
        if method_type != 'static':
            self_var_slot = self._local_vars.get('己')
            if self_var_slot is not None:
                self_dv = self.new_register()
                self.emit(f'{self_dv} = load {LIGHTVALUE_STRUCT}, ptr %self')
                self.emit(f'store {LIGHTVALUE_STRUCT} {self_dv}, ptr {self_var_slot}')
                # prologue 深拷贝：己 拥有独立对象缓冲，使 dv_class_set_member 的
                # free+realloc 不再波及调用方 %self（修复 UAF），详见 runtime_typed.c。
                self.emit(f'call void @dv_obj_deepcopy_self(ptr {self_var_slot})')

        if params:
            num_args_sext = self.new_register()
            self.emit(f'{num_args_sext} = sext i32 %num_args to i64')

        for i, param in enumerate(params):
            pname = param.name if hasattr(param, 'name') else str(param)
            param_slot = self._local_vars.get(pname)
            if param_slot is not None:
                in_bounds = self.new_register()
                self.emit(f'{in_bounds} = icmp slt i64 {i}, {num_args_sext}')
                then_lab = self.new_label('param_valid')
                else_lab = self.new_label('param_invalid')
                end_lab = self.new_label('param_end')
                self.emit(f'br i1 {in_bounds}, label %{then_lab}, label %{else_lab}')
                self.emit(f'{then_lab}:')
                elem_ptr = self.new_register()
                self.emit(f'{elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr %args, i64 {i}')
                param_val = self.new_register()
                self.emit(f'{param_val} = load {LIGHTVALUE_STRUCT}, ptr {elem_ptr}')
                self.emit(f'store {LIGHTVALUE_STRUCT} {param_val}, ptr {param_slot}')
                self.emit(f'br label %{end_lab}')
                self.emit(f'{else_lab}:')
                null_slot = self._new_dv_slot()
                self.emit(f'call void @dv_null(ptr {null_slot})')
                null_val = self.new_register()
                self.emit(f'{null_val} = load {LIGHTVALUE_STRUCT}, ptr {null_slot}')
                self.emit(f'store {LIGHTVALUE_STRUCT} {null_val}, ptr {param_slot}')
                self.emit(f'br label %{end_lab}')
                self.emit(f'{end_lab}:')

        for stmt in (getattr(method_def, 'body', []) or []):
            self._gen_statement(stmt)

        # 出口兜底：方法体不以 返回/跳出 收尾时，把 己 写回 %self 并补一条空结果返回。
        # 显式 返回 已在 _gen_typed_return 的各分支各自写回 己→%self，此处仅在“体末尾
        # 没有终止指令”的兜底路径写回，绝不会产生「终止指令之后的多余指令」非法 IR。
        if not self._ends_with_terminator(getattr(method_def, 'body', []) or []):
            if method_type != 'static':
                self_var_slot = self._local_vars.get('己')
                if self_var_slot is not None:
                    self_dv = self.new_register()
                    self.emit(f'{self_dv} = load {LIGHTVALUE_STRUCT}, ptr {self_var_slot}')
                    self.emit(f'store {LIGHTVALUE_STRUCT} {self_dv}, ptr %self')
            self.emit(f'call void @dv_null(ptr %result)')
            self.emit('ret void')
        # 函数体发射完毕，用真实槽位用量回填池大小
        self._emit_temp_slot_pool()
        self.emit('}')
        self.emit_blank()
        self._method_result_ptr = None
        self._current_class = None
        self._current_method_type = None
        # 结束函数调试作用域
        self._end_debug_function()

    def _gen_typed_constructor(self, class_name, constructor_def):
        """生成构造函数
        构造函数名就是类名，方法名与类名相同
        """
        original_name = constructor_def.name
        constructor_def.name = class_name
        try:
            self._gen_typed_method(class_name, constructor_def)
        finally:
            constructor_def.name = original_name

    def _gen_typed_main(self):
        self._reg_counter = 0
        self._dv_ssa_to_slot.clear()
        self._temp_slot_index = 0
        self._local_vars.clear()
        self._pending_allocas = []
        self.emit(f'define i32 @main(i32 %argc, ptr %argv) {{')
        self.emit('entry:')

        # 生成 main 函数调试信息（DISubprogram）
        if self._debug:
            self._gen_debug_function('main', line=1, param_names=['argc', 'argv'])

        self._begin_temp_slot_pool()

        self.emit('call void @dv_init_args(i32 %argc, ptr %argv)')
        self.emit('call void @__light_init()')

        # P0-2：补齐原生腿入口约定，与 src 后端对齐——src 以 `段落 主:` 作为程序入口，
        # 原生腿此前只认 主程序/主入口/main，导致 src 写法的测试文件在原生腿无法直接运行。
        main_names = {'主程序', '主入口', 'main', '主'}
        main_called = False

        # 检查顶层是否已经调用了主程序
        for stmt in self._module_statements:
            if isinstance(stmt, ast.ExpressionStatement):
                expr = stmt.expression
                if isinstance(expr, ast.FunctionCall):
                    call_name = None
                    if hasattr(expr, 'name'):
                        if hasattr(expr.name, 'name'):
                            call_name = expr.name.name
                        elif isinstance(expr.name, str):
                            call_name = expr.name
                    if call_name and call_name in main_names:
                        main_called = True
                        break

        # 如果顶层没有调用主程序，但定义了主程序段落，则调用它
        if not main_called:
            for name in main_names:
                # T9A：主程序段在当前模块上下文中查找
                if self._local_seg_key(name) in self._segments:
                    params = self._segments[self._local_seg_key(name)]
                    safe = self._safe_func_name(name, self._current_module)
                    num_params = len(params)
                    result_slot = self._new_dv_slot()
                    if num_params == 0:
                        self.emit(f'call void @_seg_{safe}(ptr {result_slot}, ptr null, i32 0)')
                    else:
                        args_arr = self._new_dv_slot()
                        for i in range(num_params):
                            elem_ptr = self.new_register()
                            self.emit(f'{elem_ptr} = getelementptr inbounds {LIGHTVALUE_STRUCT}, ptr {args_arr}, i64 {i}')
                            arg_idx = self.new_register()
                            self.emit(f'{arg_idx} = add i32 1, {i}')
                            has_arg = self.new_register()
                            self.emit(f'{has_arg} = icmp slt i32 {arg_idx}, %argc')
                            arg_then = self.new_label('arg_then')
                            arg_else = self.new_label('arg_else')
                            arg_end = self.new_label('arg_end')
                            self.emit(f'br i1 {has_arg}, label %{arg_then}, label %{arg_else}')
                            self.emit(f'{arg_then}:')
                            argv_ptr = self.new_register()
                            self.emit(f'{argv_ptr} = getelementptr inbounds ptr, ptr %argv, i32 {arg_idx}')
                            arg_str = self.new_register()
                            self.emit(f'{arg_str} = load ptr, ptr {argv_ptr}')
                            arg_slot = self._new_dv_slot()
                            self.emit(f'call void @dv_str(ptr {arg_slot}, ptr {arg_str})')
                            arg_val = self.new_register()
                            self.emit(f'{arg_val} = load {LIGHTVALUE_STRUCT}, ptr {arg_slot}')
                            self.emit(f'store {LIGHTVALUE_STRUCT} {arg_val}, ptr {elem_ptr}')
                            self.emit(f'br label %{arg_end}')
                            self.emit(f'{arg_else}:')
                            null_slot = self._new_dv_slot()
                            self.emit(f'call void @dv_null(ptr {null_slot})')
                            null_val = self.new_register()
                            self.emit(f'{null_val} = load {LIGHTVALUE_STRUCT}, ptr {null_slot}')
                            self.emit(f'store {LIGHTVALUE_STRUCT} {null_val}, ptr {elem_ptr}')
                            self.emit(f'br label %{arg_end}')
                            self.emit(f'{arg_end}:')
                        self.emit(f'call void @_seg_{safe}(ptr {result_slot}, ptr {args_arr}, i32 {num_params})')
                    main_called = True
                    break

        self.emit('ret i32 0')
        # 函数体发射完毕，用真实槽位用量回填池大小
        self._emit_temp_slot_pool()
        self.emit('}')
        self.emit_blank()
        # 结束 main 函数调试作用域
        self._end_debug_function()

    # ============================================================
    # 变量管理（存储/加载 LightValue）
    # ============================================================

    def get_var(self, name):
        """获取 LightValue（覆写父类）"""
        if name in self._current_func_params:
            return self._current_func_params[name]
        if name in self._globals:
            safe = self._safe_var_name(name)
            reg = self.new_register()
            self.emit(f'{reg} = load {LIGHTVALUE_STRUCT}, {LIGHTVALUE_STRUCT}* @__var_{safe}')
            return reg
        if name in self._local_vars:
            slot = self._local_vars[name]
            reg = self.new_register()
            self.emit(f'{reg} = load {LIGHTVALUE_STRUCT}, ptr {slot}')
            self._dv_ssa_to_slot[reg] = slot
            return reg
        return None

    def set_var(self, name, value_reg):
        """设置变量（覆写父类）"""
        if name in self._globals:
            safe = self._safe_var_name(name)
            self.emit(f'store {LIGHTVALUE_STRUCT} {value_reg}, {LIGHTVALUE_STRUCT}* @__var_{safe}')
        elif name in self._local_vars:
            slot = self._local_vars[name]
            self.emit(f'store {LIGHTVALUE_STRUCT} {value_reg}, ptr {slot}')
        elif name in self._current_func_params:
            self._current_func_params[name] = value_reg

    # ============================================================
    # finalize - 生成全局声明（使用 LightValue 结构体）
    # ============================================================

    def finalize(self) -> str:
        """生成最终 IR（覆写父类）"""
        # R12C（R11A-08）：发射本批按需的字符串辅助函数（此 finalize 为
        # 类内后定义者，实际生效；422 行的同名方法被本方法覆盖）
        self._emit_r12c_string_helpers()
        lines = []
        for s in self._string_decls:
            lines.append(s)
        if self._string_decls:
            lines.append('')
        for f in sorted(self._func_decls):
            lines.append(f)
        lines.append('')
        for name in self._globals:
            safe = self._safe_var_name(name)
            lines.append(f'@__var_{safe} = global {LIGHTVALUE_STRUCT} zeroinitializer')
        if self._globals:
            lines.append('')
        lines.extend(self._lines)
        # 追加 DWARF 调试元数据（必须出现在 IR 末尾）
        if self._debug and self._debug_metadata_lines:
            lines.append('')
            lines.extend(self._debug_metadata_lines)
        return '\n'.join(lines)