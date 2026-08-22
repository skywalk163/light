"""
LLVM 代码生成器 - 类型版 (v3)
使用 LightValue 结构体（{ i32, i64, double, ptr }），
算术运算在原生类型上直接操作，无需 atoi/itoa 转换。
"""

from typing import Optional, Tuple, List
import sys
import platform as _platform
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
        self._current_class = None  # 当前方法所属的类名（None 表示不在方法中）
        self._current_method_type = None  # 当前方法类型：'instance' / 'class' / 'static'
        self._var_types = {}  # 变量类型追踪：var_name -> type_str (INT/FLOAT/BOOL/STRING/LIST/None)
        self._enable_type_opt = True  # 启用类型优化
        # 模块系统支持（Level 9）
        self._imports = {}  # 导入符号表：符号名 -> (模块名, 原始符号名)
        self._imported_modules = set()  # 已导入的模块名集合
        self._module_decls = []  # 待生成的外部段函数声明
        self._segment_modifiers = {}  # 段的修饰符（异步等）
        # 协程支持（Level 10）
        self._in_coroutine = False  # 当前是否在生成协程函数
        self._coro_handle_ptr = None  # 协程句柄指针（LightCoroutine*）
        self._coro_resume_point = 0  # 下一个 await 点的编号
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
        """为局部变量分配 LightValue 栈空间（重写父类）"""
        if name not in self._local_vars or self._local_vars[name] is None:
            reg = self.new_register()
            line = f'{reg} = alloca {LIGHTVALUE_STRUCT}'
            self._pending_allocas.append(line)
            self._local_vars[name] = reg

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

    def finalize(self) -> str:
        """覆写父类方法：在生成 IR 时追加调试元数据"""
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
            f'declare void @dv_list_new(ptr)',
            f'declare i64 @dv_list_len(ptr)',
            f'declare i64 @dv_len(ptr)',
            f'declare void @dv_list_get(ptr, ptr, i64)',
            f'declare void @dv_list_append(ptr, ptr, ptr)',
            f'declare void @dv_list_insert(ptr, ptr, i64, ptr)',
            f'declare void @dv_list_remove(ptr, ptr, i64)',
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
            f'declare void @dv_to_int(ptr, ptr)',
            f'declare void @dv_to_float(ptr, ptr)',
            f'declare void @dv_to_bool_val(ptr, ptr)',
            f'declare double @dv_timestamp()',
            f'declare ptr @dv_format_time(double, ptr)',
            f'declare i32 @dv_file_exists(ptr)',
            f'declare ptr @dv_read_file(ptr)',
            f'declare void @dv_write_file(ptr, ptr)',
            f'declare void @dv_append_file(ptr, ptr)',
            f'declare i64 @dv_file_size(ptr)',
            f'declare i32 @dv_delete_file(ptr)',
            f'declare void @dv_list_dir(ptr, ptr)',
            f'declare ptr @dv_str_join(ptr, ptr)',
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
            f'declare void @dv_dict_get(ptr, ptr, ptr)',
            f'declare void @dv_dict_has(ptr, ptr, ptr)',
            f'declare void @dv_dict_keys(ptr, ptr)',
            f'declare void @dv_dict_values(ptr, ptr)',
            # 文件系统扩展
            f'declare i32 @dv_mkdir(ptr)',
            f'declare i32 @dv_rmdir(ptr)',
            f'declare i32 @dv_rename_file(ptr, ptr)',
            f'declare i32 @dv_copy_file(ptr, ptr)',
            f'declare i32 @dv_is_file(ptr)',
            f'declare i32 @dv_is_dir(ptr)',
            # 哈希/编码
            f'declare ptr @dv_md5(ptr, i32)',
            f'declare ptr @dv_sha1(ptr, i32)',
            f'declare ptr @dv_sha256(ptr, i32)',
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

        """从临时槽位池中分配一个新的 LightValue 槽位（避免动态 alloca 导致栈溢出）"""
        if self._temp_slot_pool is None:
            reg = self.new_register()
            self.emit(f'{reg} = alloca {LIGHTVALUE_STRUCT}')
            return reg
        
        if self._temp_slot_index >= self._temp_slot_pool_size:
            raise RuntimeError(f"临时槽位池溢出！已使用 {self._temp_slot_index} / {self._temp_slot_pool_size}")
        
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
                if left_type == 'FLOAT' or right_type == 'FLOAT':
                    return 'FLOAT'
                if left_type == 'INT' and right_type == 'INT':
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
        for seg_name in self._segment_order:
            params = self._segments[seg_name]
            body = self._segment_bodies.get(seg_name, [])
            modifiers = self._segment_modifiers.get(seg_name, [])
            self._gen_typed_segment(seg_name, params, body, modifiers)

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

    def _process_imports(self, module: ast.Module):
        """处理模块导入语句，记录导入的符号"""
        imports = getattr(module, 'imports', None) or []
        for imp in imports:
            if isinstance(imp, ast.ImportStatement):
                module_name = imp.module
                self._imported_modules.add(module_name)
                if imp.names:
                    for name in imp.names:
                        self._imports[name] = (module_name, name)
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
            for seg_name in self._segment_order:
                exported_names.add(seg_name)
        for seg_name in exported_names:
            if seg_name in self._segments:
                safe = self._safe_func_name(seg_name)
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
            if expr.name in self._segments:
                return self._gen_typed_segment_call(expr.name, args)
            return self._create_int_dv('0'), 'dv'

        if isinstance(expr, ast.IndexAccess):
            return self._gen_typed_index_access(expr)

        if isinstance(expr, ast.ListLiteral):
            return self._gen_typed_list_literal(expr)

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

        return self._create_int_dv('0'), 'dv'

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

        # 方法内部：以"self."开头的标识符视为 self 的属性访问
        if self._method_result_ptr is not None and name.startswith('self.') and len(name) > 5:
            attr_name = name[5:]
            self_dv = self.get_var('己')
            if self_dv is not None:
                obj_slot = self._store_dv(self_dv)
                member_reg = self.gen_string_constant(attr_name)
                result_slot = self._new_dv_slot()
                self.emit(f'call void @dv_class_get_member(ptr {result_slot}, ptr {obj_slot}, ptr {member_reg})')
                return self._load_dv(result_slot), 'dv'
        
        # 方法内部：以"己"开头的标识符视为 self 的属性访问
        if self._method_result_ptr is not None and name.startswith('己') and len(name) > 1:
            attr_name = name[1:]
            self_dv = self.get_var('己')
            if self_dv is not None:
                obj_slot = self._store_dv(self_dv)
                member_reg = self.gen_string_constant(attr_name)
                result_slot = self._new_dv_slot()
                self.emit(f'call void @dv_class_get_member(ptr {result_slot}, ptr {obj_slot}, ptr {member_reg})')
                return self._load_dv(result_slot), 'dv'
        
        # 内置函数名当作字符串
        str_reg = self.gen_string_constant(name)
        return self._create_str_dv(str_reg), 'dv'

    def _gen_typed_binary_op(self, expr: ast.BinaryOp) -> Tuple[str, str]:
        left_dv, _ = self._gen_expression(expr.left)
        right_dv, _ = self._gen_expression(expr.right)
        op = expr.operator

        left_type = self._infer_expr_type(expr.left)
        right_type = self._infer_expr_type(expr.right)

        arith_ops = {
            '+': ('add', 'fadd'), '-': ('sub', 'fsub'),
            '*': ('mul', 'fmul'), '/': ('sdiv', 'fdiv'),
            '%': ('srem', 'frem'),
            '加': ('add', 'fadd'), '减': ('sub', 'fsub'),
            '乘': ('mul', 'fmul'), '除': ('sdiv', 'fdiv'),
            '模': ('srem', 'frem'),
        }

        if op in arith_ops:
            if self._enable_type_opt and left_type == 'INT' and right_type == 'INT':
                left_i64 = self._extract_i64(left_dv)
                right_i64 = self._extract_i64(right_dv)
                int_op, _ = arith_ops[op]
                result = self.new_register()
                self.emit(f'{result} = {int_op} i64 {left_i64}, {right_i64}')
                return self._create_int_dv_fast(result), 'dv'
            if self._enable_type_opt and (left_type == 'FLOAT' or right_type == 'FLOAT'):
                left_f64 = self._extract_f64(left_dv) if left_type == 'FLOAT' else self._i64_to_f64(self._extract_i64(left_dv))
                right_f64 = self._extract_f64(right_dv) if right_type == 'FLOAT' else self._i64_to_f64(self._extract_i64(right_dv))
                _, float_op = arith_ops[op]
                result = self.new_register()
                self.emit(f'{result} = {float_op} double {left_f64}, {right_f64}')
                return self._create_float_dv_fast(result), 'dv'

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
            if self._enable_type_opt and (left_type == 'FLOAT' or right_type == 'FLOAT'):
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
        }
        if op in type_map:
            dv_func = type_map[op]
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

        return self._call_dv_func('dv_add', left_dv, right_dv), 'dv'

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

        zero_dv = self._create_int_dv('0')
        cond_slot = self._store_dv(cond_dv)
        zero_slot = self._store_dv(zero_dv)
        eq = self.new_register()
        self.emit(f'{eq} = call i32 @dv_eq(ptr {cond_slot}, ptr {zero_slot})')
        final = self.new_register()
        self.emit(f'{final} = icmp eq i32 {eq}, 0')
        return final

    def _gen_typed_unary_op(self, expr: ast.UnaryOp) -> Tuple[str, str]:
        reg, _ = self._gen_expression(expr.operand)
        if expr.operator == '非':
            zero_dv = self._create_int_dv('0')
            reg_slot = self._store_dv(reg)
            zero_slot = self._store_dv(zero_dv)
            eq = self.new_register()
            self.emit(f'{eq} = call i32 @dv_eq(ptr {reg_slot}, ptr {zero_slot})')
            final = self.new_register()
            self.emit(f'{final} = icmp ne i32 {eq}, 0')
            return self._create_bool_dv(final), 'dv'
        return reg, 'dv'

    def _gen_typed_function_call(self, expr: ast.FunctionCall) -> Tuple[str, str]:
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

        args = [self._gen_expression(arg)[0] for arg in expr.arguments]

        # 内置函数
        builtin = self._gen_typed_builtin(func_name, args)
        if builtin is not None:
            return builtin

        # 当前模块的段函数
        if func_name in self._segments:
            return self._gen_typed_segment_call(func_name, args)

        # Level 9: 导入的外部段函数
        if func_name in self._imports:
            return self._gen_imported_segment_call(func_name, args)

        return self._create_int_dv('0'), 'dv'

    def _gen_imported_segment_call(self, name: str, args: List[str]) -> Tuple[str, str]:
        """调用从其他模块导入的段函数"""
        module_name, orig_name = self._imports[name]
        safe = self._safe_func_name(f'{module_name}_{orig_name}')
        result_slot = self._new_dv_slot()
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
            self.emit(f'call void @llvm.stackrestore(ptr {stack_save})')
        result = self.new_register()
        self.emit(f'{result} = load {LIGHTVALUE_STRUCT}, ptr {result_slot}')
        return result, 'dv'

    def _gen_typed_builtin(self, name: str, args: List[str]) -> Optional[Tuple[str, str]]:
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

        if name in ('时间戳', '时间'):
            dbl = self.new_register()
            self.emit(f'{dbl} = call double @dv_timestamp()')
            return self._call_dv_func('dv_float', f'double {dbl}'), 'dv'

        if name == '格式化时间':
            if not args:
                return self._create_int_dv('0'), 'dv'
            dbl = self.new_register()
            self.emit(f'{dbl} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 2')
            fmt_reg = self.gen_string_constant("%Y-%m-%d %H:%M:%S")
            out = self.new_register()
            self.emit(f'{out} = call ptr @dv_format_time(double {dbl}, ptr {fmt_reg})')
            return self._create_str_dv(out), 'dv'

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
            return self._call_dv_func('dv_to_int', args[0]), 'dv'

        if name in ('浮点数', 'float', '转浮点', 'to_float'):
            if not args:
                return self._call_dv_func('dv_float', 'double 0.0'), 'dv'
            return self._call_dv_func('dv_to_float', args[0]), 'dv'

        if name == '长度' or name == 'len' or name == '列表长度' or name == '字符串长度':
            if not args:
                return self._create_int_dv('0'), 'dv'
            slot = self._store_dv(args[0])
            i64_val = self.new_register()
            self.emit(f'{i64_val} = call i64 @dv_len(ptr {slot})')
            return self._create_int_dv(i64_val), 'dv'

        if name in ('新建', '新建列表', 'new_list', '列表创建'):
            return self._call_dv_func('dv_list_new'), 'dv'

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

        if name in ('插入', 'insert', 'list_insert'):
            if len(args) >= 3:
                idx_i64 = self.new_register()
                self.emit(f'{idx_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                return self._call_dv_func('dv_list_insert', args[0], f'i64 {idx_i64}', args[2]), 'dv'
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

        if name in ('排序', 'sort', 'list_sort'):
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

        if name in ('转文本', 'to_string', '转字符串', '转串'):
            if args:
                return self._call_dv_func('dv_value_to_string', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name == '连接':
            a = args[0] if len(args) > 0 else self._create_int_dv('0')
            b = args[1] if len(args) > 1 else self._create_int_dv('0')
            return self._call_dv_func('dv_concat', a, b), 'dv'

        if name in ('正弦', 'sin'):
            if args:
                return self._call_dv_func('dv_sin', args[0]), 'dv'
            return self._call_dv_func('dv_float', 'double 0.0'), 'dv'

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

        if name in ('取模', 'mod'):
            if len(args) >= 2:
                return self._call_dv_func('dv_mod', args[0], args[1]), 'dv'
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

        if name in ('大写', 'upper', 'to_upper'):
            if args:
                return self._call_dv_func('dv_upper', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('小写', 'lower', 'to_lower'):
            if args:
                return self._call_dv_func('dv_lower', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('去除空格', 'trim', 'strip'):
            if args:
                return self._call_dv_func('dv_trim', args[0]), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('替换', 'replace', 'str_replace'):
            if len(args) >= 3:
                return self._call_dv_func('dv_str_replace', args[0], args[1], args[2]), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'

        if name in ('分割', 'split', 'str_split'):
            if len(args) >= 2:
                return self._call_dv_func('dv_str_split', args[0], args[1]), 'dv'
            return self._call_dv_func('dv_list_new'), 'dv'

        if name in ('连接字符串', 'join', 'str_join', 'implode'):
            if len(args) >= 2:
                list_ptr = self.new_register()
                self.emit(f'{list_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[0]}, 3')
                sep_ptr = self.new_register()
                self.emit(f'{sep_ptr} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 3')
                out = self.new_register()
                self.emit(f'{out} = call ptr @dv_str_join(ptr {list_ptr}, ptr {sep_ptr})')
                return self._create_str_dv(out), 'dv'
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

        if name in ('取类型', 'type', '获取类型', 'typeof', '类型名', 'type_name'):
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
            if len(args) >= 2:
                return self._call_dv_func('dv_dict_get', args[0], args[1]), 'dv'
            return self._call_dv_func('dv_null'), 'dv'

        if name in ('字典包含键', '字典有键'):
            if len(args) >= 2:
                return self._call_dv_func('dv_dict_has', args[0], args[1]), 'dv'
            return self._create_bool_dv('false'), 'dv'

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

        idx_slot = self.new_register()
        self.emit(f'{idx_slot} = alloca i64')
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

    def _gen_typed_method_call(self, expr: ast.FunctionCall) -> Tuple[str, str]:
        """处理 obj.方法(args) - FunctionCall with PropertyAccess name"""
        prop = expr.name  # PropertyAccess
        method_name = prop.property_name
        
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
            
            obj_slot = self._store_dv(self_dv)
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

        # 先检查是否是内置方法（列表、字符串等）
        # 内置方法调用：把对象作为第一个参数传给内置函数
        args_dv = [obj_dv]
        for arg in expr.arguments:
            arg_dv, _ = self._gen_expression(arg)
            args_dv.append(arg_dv)

        # 尝试使用内置函数处理
        builtin_result = self._gen_typed_builtin(method_name, args_dv)
        if builtin_result is not None:
            return builtin_result

        # 否则使用 dv_call_method 调用类方法
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
        
        # 如果对象是一个变量，把更新后的对象写回变量
        if isinstance(prop.obj, ast.Identifier):
            obj_name = prop.obj.name
            updated_obj = self._load_dv(obj_slot)
            self.set_var(obj_name, updated_obj)
        
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
        
        has_ctor = False
        if class_name in self._classes:
            cls_def = self._classes[class_name]
            constructor = getattr(cls_def, 'constructor', None)
            if constructor is not None:
                has_ctor = True
        
        if has_ctor:
            obj_dv = self._load_dv(result_slot)
            obj_slot = self._store_dv(obj_dv)
            ctor_name_reg = self.gen_string_constant(class_name)
            
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

    def _collect_segment(self, seg):
        """覆盖父类方法：在收集阶段预先注册所有段名"""
        raw_name = seg.name.name if hasattr(seg.name, 'name') else str(seg.name)
        params = [(p.name, p.default_value) for p in seg.parameters]
        self._segments[raw_name] = params
        self._segment_order.append(raw_name)
        self._segment_bodies[raw_name] = seg.body
        # 保存 modifiers（用于异步段落识别）
        modifiers = getattr(seg, 'modifiers', None) or []
        self._segment_modifiers[raw_name] = list(modifiers)
        # 预先注册到 _func_name_map，确保 f# 编号稳定
        self._safe_func_name(raw_name)

    def _collect_statement(self, stmt):
        """覆盖父类方法"""
        super()._collect_statement(stmt)

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

    def _gen_typed_segment_call(self, name: str, args: List[str]) -> Tuple[str, str]:
        safe = self._safe_func_name(name)
        result_slot = self._new_dv_slot()
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
            self.emit(f'call void @llvm.stackrestore(ptr {stack_save})')
        result = self.new_register()
        self.emit(f'{result} = load {LIGHTVALUE_STRUCT}, ptr {result_slot}')
        return result, 'dv'

    def _gen_typed_index_access(self, expr) -> Tuple[str, str]:
        obj_dv, _ = self._gen_expression(expr.obj)
        if isinstance(expr.index, ast.NumberLiteral):
            idx_val = int(expr.index.value)
            i64_reg = f'{idx_val}'
        else:
            idx_dv, _ = self._gen_expression(expr.index)
            i64_reg = self.new_register()
            self.emit(f'{i64_reg} = extractvalue {LIGHTVALUE_STRUCT} {idx_dv}, 1')
        obj_slot = self._store_dv(obj_dv)
        type_reg = self.new_register()
        self.emit(f'{type_reg} = load i32, ptr {obj_slot}')
        is_str = self.new_register()
        self.emit(f'{is_str} = icmp eq i32 {type_reg}, 3')
        then_lab = self.new_label('idx_str')
        else_lab = self.new_label('idx_list')
        end_lab = self.new_label('idx_end')
        result_slot = self._new_dv_slot()
        self.emit(f'br i1 {is_str}, label %{then_lab}, label %{else_lab}')
        self.emit(f'{then_lab}:')
        self.emit(f'call void @dv_str_get(ptr {result_slot}, ptr {obj_slot}, i64 {i64_reg})')
        self.emit(f'br label %{end_lab}')
        self.emit(f'{else_lab}:')
        self.emit(f'call void @dv_list_get(ptr {result_slot}, ptr {obj_slot}, i64 {i64_reg})')
        self.emit(f'br label %{end_lab}')
        self.emit(f'{end_lab}:')
        result = self._load_dv(result_slot)
        return result, 'dv'

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
                self._reject_unsupported_stmt(inner, stmt)
            if isinstance(expr, ast.FunctionCall) and isinstance(expr.name, ast.PropertyAccess):
                method_name = expr.name.property_name
                obj = expr.name.obj
                if isinstance(obj, ast.Identifier):
                    obj_name = obj.name
                    mutating_methods = {'追加', 'append', '清空', 'clear', '设置', 'set', '插入', 'insert', '删除', 'remove', '弹出', 'pop'}
                    if method_name in mutating_methods:
                        result_dv, _ = self._gen_expression(expr)
                        self.set_var(obj_name, result_dv)
                        return
            self._gen_expression(expr)
        elif isinstance(stmt, ast.ImportStatement):
            pass
        elif hasattr(ast, 'AsyncScope') and isinstance(stmt, ast.AsyncScope):
            self._gen_async_scope(stmt)
        else:
            # A2-1：链尾兜底。以前这里什么都没有，未知语句被静默吃掉。
            self._reject_unsupported_stmt(type(stmt).__name__, stmt)

    def _gen_typed_var_decl(self, stmt: ast.VariableDeclaration):
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

    def _gen_typed_assignment(self, stmt: ast.Assignment):
        if isinstance(stmt.target, ast.PropertyAccess):
            obj_dv, _ = self._gen_expression(stmt.target.obj)
            member = stmt.target.property_name
            value_dv, _ = self._gen_expression(stmt.value)
            obj_slot = self._store_dv(obj_dv)
            member_reg = self.gen_string_constant(member)
            value_slot = self._store_dv(value_dv)
            self.emit(f'call void @dv_class_set_member(ptr {obj_slot}, ptr {member_reg}, ptr {value_slot})')
            if isinstance(stmt.target.obj, ast.Identifier):
                obj_name = stmt.target.obj.name
                updated_dv = self._load_dv(obj_slot)
                self.set_var(obj_name, updated_dv)
        elif isinstance(stmt.target, ast.Identifier):
            name = stmt.target.name
            # 方法内部：self.xxx 赋值
            if self._method_result_ptr is not None and name.startswith('self.') and len(name) > 5:
                attr_name = name[5:]
                self_dv = self.get_var('己')
                if self_dv is not None:
                    value_dv, _ = self._gen_expression(stmt.value)
                    obj_slot = self._store_dv(self_dv)
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
                    obj_slot = self._store_dv(self_dv)
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
        obj_slot = self._store_dv(self_dv)
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

        idx_slot = self.new_register()
        self.emit(f'{idx_slot} = alloca i64')
        self.emit(f'store i64 0, ptr {idx_slot}')

        slot = self._store_dv(list_dv)
        len_val = self.new_register()
        self.emit(f'{len_val} = call i64 @dv_list_len(ptr {slot})')

        loop_lab = self.new_label('foreach_loop')
        body_lab = self.new_label('foreach_body')
        end_lab = self.new_label('foreach_end')
        self._loop_break_labels.append(end_lab)
        self._loop_continue_labels.append(loop_lab)
        self.emit(f'br label %{loop_lab}')

        self.emit(f'{loop_lab}:')
        i = self.new_register()
        self.emit(f'{i} = load i64, ptr {idx_slot}')
        cmp = self.new_register()
        self.emit(f'{cmp} = icmp slt i64 {i}, {len_val}')
        self.emit(f'br i1 {cmp}, label %{body_lab}, label %{end_lab}')

        self.emit(f'{body_lab}:')
        elem = self._call_dv_func('dv_list_get', list_dv, f'i64 {i}')
        self.set_var(var_name, elem)
        for s in stmt.body:
            self._gen_statement(s)
        if not self._ends_with_terminator(stmt.body):
            next_i = self.new_register()
            self.emit(f'{next_i} = add i64 {i}, 1')
            self.emit(f'store i64 {next_i}, ptr {idx_slot}')
            self.emit(f'br label %{loop_lab}')

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

    def _gen_typed_return(self, stmt: ast.ReturnStatement):
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
            if self._current_method_type != 'static':
                self_var_slot = self._local_vars.get('己')
                if self_var_slot is not None:
                    self_dv = self.new_register()
                    self.emit(f'{self_dv} = load {LIGHTVALUE_STRUCT}, ptr {self_var_slot}')
                    self.emit(f'store {LIGHTVALUE_STRUCT} {self_dv}, ptr %self')
            if stmt.value:
                dv_val, _ = self._gen_expression(stmt.value)
                self.emit(f'store {LIGHTVALUE_STRUCT} {dv_val}, ptr {self._method_result_ptr}')
            else:
                self.emit(f'call void @dv_null(ptr {self._method_result_ptr})')
            self.emit('call void @dv_stack_pop()')
            self.emit('ret void')
        elif self._seg_result_ptr is not None:
            if stmt.value:
                dv_val, _ = self._gen_expression(stmt.value)
                self.emit(f'store {LIGHTVALUE_STRUCT} {dv_val}, ptr {self._seg_result_ptr}')
            else:
                self.emit(f'call void @dv_null(ptr {self._seg_result_ptr})')
            self.emit('call void @dv_stack_pop()')
            self.emit('ret void')
        else:
            if stmt.value:
                dv_val, _ = self._gen_expression(stmt.value)
                self.emit('call void @dv_stack_pop()')
                self.emit(f'ret {LIGHTVALUE_STRUCT} {dv_val}')
            else:
                null_dv = self._call_dv_func('dv_null')
                self.emit('call void @dv_stack_pop()')
                self.emit(f'ret {LIGHTVALUE_STRUCT} {null_dv}')

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
            ("Exception", "", ["消息", "类型", "栈追踪", "原因"]),
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

    def _gen_typed_segment(self, name, params, body, modifiers=None):
        modifiers = modifiers or []
        is_async = '异步' in modifiers or 'async' in [m.lower() for m in modifiers]
        
        if is_async:
            self._gen_async_segment(name, params, body)
        else:
            self._gen_normal_segment(name, params, body)
    
    def _gen_normal_segment(self, name, params, body):
        """生成普通（非异步）段落函数"""
        self._current_func = name
        self._current_func_params = {}
        self._local_vars.clear()
        self._pending_allocas = []
        self._reg_counter = 0
        self._dv_ssa_to_slot.clear()
        self._temp_slot_index = 0
        self._seg_result_ptr = '%result'
        safe = self._safe_func_name(name)

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
        for param_name, _ in params:
            self._local_vars[param_name] = None

        for vname in self._local_vars.keys():
            reg = self.new_register()
            self.emit(f'{reg} = alloca {LIGHTVALUE_STRUCT}')
            self._local_vars[vname] = reg

        if params:
            num_args_sext = self.new_register()
            self.emit(f'{num_args_sext} = sext i32 %num_args to i64')

        for i, (pname, _) in enumerate(params):
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

        for stmt in body:
            self._gen_statement(stmt)

        if not self._ends_with_terminator(body):
            self.emit(f'call void @dv_null(ptr %result)')
            self.emit('call void @dv_stack_pop()')
            self.emit('ret void')
        # 函数体发射完毕，用真实槽位用量回填池大小
        self._emit_temp_slot_pool()
        self.emit('}')
        self.emit_blank()
        self._seg_result_ptr = None
        # 结束函数调试作用域
        self._end_debug_function()

    def _gen_async_segment(self, name, params, body):
        """生成异步段落：包括协程函数和包装段函数
        
        生成两个函数：
        1. _coro_xxx(ptr %coro) - 协程状态机函数（Duff's device 模式）
        2. _seg_xxx(ptr %result, ptr %args, i32 %num_args) - 包装函数，创建协程
        """
        safe = self._safe_func_name(name)
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
        self._method_result_ptr = '%result'
        self._current_class = class_name
        self._current_method_type = method_type

        method_safe_name = f'_method_{self._safe_func_name(class_name)}_{self._safe_func_name(method_def.name)}'

        if method_type == 'static':
            self.emit(f'define void @{method_safe_name}(ptr %result, ptr %args, i32 %num_args) {{')
        else:
            self.emit(f'define void @{method_safe_name}(ptr %result, ptr %self, ptr %args, i32 %num_args) {{')
        self.emit('entry:')

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

        if not self._ends_with_terminator(getattr(method_def, 'body', []) or []):
            # 把己变量写回 self（仅实例方法和类方法有）
            if method_type != 'static':
                self_var_slot = self._local_vars.get('己')
                if self_var_slot is not None:
                    self_dv = self.new_register()
                    self.emit(f'{self_dv} = load {LIGHTVALUE_STRUCT}, ptr {self_var_slot}')
                    self.emit(f'store {LIGHTVALUE_STRUCT} {self_dv}, ptr %self')
            self.emit(f'call void @dv_null(ptr %result)')

        self.emit('ret void')
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

        main_names = {'主程序', '主入口', 'main'}
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
                if name in self._segments:
                    params = self._segments[name]
                    safe = self._safe_func_name(name)
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