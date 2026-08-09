"""
LLVM 代码生成器核心 - v2
基于字符串类型系统 (i8*)
"""
import re

from abc import ABC, abstractmethod


class LLVMCodeGenCore(ABC):
    """LLVM IR 生成器核心"""

    def __init__(self):
        self._lines = []
        self._strings = {}  # 字符串常量池
        self._str_counter = 0
        self._reg_counter = 0
        self._label_counter = 0
        self._globals = {}  # 全局变量名 → 初始值
        self._var_names = {}  # 原始变量名 → 安全 LLVM 名
        self._var_counter = 0
        self._func_name_map = {}  # 原始函数名 → 安全 LLVM 名
        self._func_counter = 0
        self._string_decls = []
        self._func_decls = set()  # 已声明的外部函数
        self._current_func = None
        self._current_func_params = {}  # 参数名 → 寄存器名
        self._local_vars = {}  # 局部变量名 → alloca 寄存器名
        self._pending_allocas = []  # 待分配的 alloca 列表（在函数开头分配）

    def new_register(self):
        self._reg_counter += 1
        return f'%{self._reg_counter}'

    def new_label(self, prefix='label'):
        self._label_counter += 1
        return f'{prefix}_{self._label_counter}'

    def _emit_string(self, s):
        """注册字符串常量，返回标签名"""
        if s not in self._strings:
            self._str_counter += 1
            name = f'@.str.{self._str_counter}'
            self._strings[s] = name
            # 转义特殊字符
            escaped = s.replace('\\', '\\5C').replace('"', '\\22').replace('\n', '\\0A').replace('\r', '\\0D').replace('\t', '\\09')
            self._string_decls.append(f'{name} = private unnamed_addr constant [{len(s.encode("utf-8")) + 1} x i8] c"{escaped}\\00"')
        return self._strings[s]

    def emit(self, line):
        self._lines.append(line)

    def emit_blank(self):
        self._lines.append('')

    def declare_runtime(self):
        """声明所有运行时函数"""
        funcs = [
            # 输入输出
            'declare i8* @light_input()',
            'declare void @light_print(i8*)',
            'declare void @light_println(i8*)',
            'declare void @light_print_int(i32)',
            # 字符串
            'declare i8* @light_concat(i8*, i8*)',
            'declare i8* @light_concat3(i8*, i8*, i8*)',
            'declare i32 @light_str_eq(i8*, i8*)',
            'declare i32 @light_str_len(i8*)',
            # 数字
            'declare i8* @light_itoa(i32)',
            'declare i32 @light_atoi(i8*)',
            'declare double @light_atof(i8*)',
            'declare i8* @light_ftoa(double)',
            # 列表
            'declare i8* @light_list_new()',
            'declare i32 @light_list_len(i8*)',
            'declare i8* @light_list_get(i8*, i32)',
            'declare i8* @light_list_append(i8*, i8*)',
            'declare i8* @light_list_clear(i8*)',
            # 时间
            'declare double @light_timestamp()',
            'declare i8* @light_format_time(double, i8*)',
            # 文件
            'declare i32 @light_file_exists(i8*)',
            'declare i8* @light_read_file(i8*)',
            'declare void @light_write_file(i8*, i8*)',
            # JSON
            'declare i8* @light_list_to_json(i8*, i32)',
            'declare i8* @light_json_parse(i8*)',
            # 内存
            'declare i8* @malloc(i64)',
            'declare void @free(i8*)',
            'declare i32 @printf(i8*, ...)',
        ]
        for f in funcs:
            self._func_decls.add(f)

    def _get_string_ptr(self, label):
        """获取字符串指针: getelementptr"""
        reg = self.new_register()
        self.emit(f'{reg} = getelementptr inbounds [{len(label)} x i8], [{len(label)} x i8]* {label}, i64 0, i64 0')
        return reg

    def _safe_var_name(self, name):
        """将中文变量名转换为安全的 ASCII LLVM 标识符"""
        if name not in self._var_names:
            self._var_counter += 1
            self._var_names[name] = f'v{self._var_counter}'
        return self._var_names[name]

    def _safe_func_name(self, name):
        """将中文段落名转换为安全的 ASCII LLVM 标识符"""
        if name not in self._func_name_map:
            self._func_counter += 1
            self._func_name_map[name] = f'f{self._func_counter}'
        return self._func_name_map[name]

    def get_var(self, name):
        """获取变量值 (i8*)"""
        if name in self._current_func_params:
            return self._current_func_params[name]
        if name in self._local_vars:
            alloca_reg = self._local_vars[name]
            reg = self.new_register()
            self.emit(f'{reg} = load i8*, i8** {alloca_reg}')
            return reg
        if name in self._globals:
            safe = self._safe_var_name(name)
            # 全局变量直接 emit load，不使用 pending 机制避免寄存器错乱
            reg = self.new_register()
            self.emit(f'{reg} = load i8*, i8** @__var_{safe}')
            return reg
        return None

    def get_var_i32(self, name):
        """获取变量值作为 i32"""
        var = self.get_var(name)
        if var is None:
            return None
        reg = self.new_register()
        self.emit(f'{reg} = call i32 @light_atoi(i8* {var})')
        return reg

    def alloca_local(self, name):
        """为局部变量分配栈空间
        如果变量已预分配，则直接返回；否则加入 pending allocas。
        """
        if name not in self._local_vars or self._local_vars[name] is None:
            reg = self.new_register()
            line = f'{reg} = alloca i8*'
            self._pending_allocas.append(line)
            self._local_vars[name] = reg

    def flush_allocas(self):
        """将延迟的 alloca 指令 emit 到当前位置"""
        for line in self._pending_allocas:
            self.emit(line)
        self._pending_allocas = []

    def flush_allocas_at(self, insert_idx):
        """将延迟的 alloca 指令插入到指定位置"""
        # 首先为 pending allocas 分配正确的寄存器号（基于当前 _reg_counter）
        for i, line in enumerate(self._pending_allocas):
            # 提取原始寄存器号
            import re
            match = re.search(r'%(\d+)', line)
            if match:
                old_num = int(match.group(1))
                new_num = self._reg_counter + i + 1
                new_reg = f'%{new_num}'
                # 替换行中的原始寄存器号
                self._pending_allocas[i] = line.replace(f'%{old_num}', new_reg, 1)
                # 更新 _local_vars 中的映射
                for name in list(self._local_vars.keys()):
                    if self._local_vars[name] == f'%{old_num}':
                        self._local_vars[name] = new_reg
        # 插入 allocas
        count = len(self._pending_allocas)
        for line in reversed(self._pending_allocas):
            self._lines.insert(insert_idx, line)
        self._pending_allocas = []
        # 更新 _reg_counter
        self._reg_counter += count

    def set_var(self, name, value_reg):
        """设置变量值"""
        if name in self._globals:
            safe = self._safe_var_name(name)
            self.emit(f'store i8* {value_reg}, i8** @__var_{safe}')
        elif name in self._local_vars:
            alloca_reg = self._local_vars[name]
            self.emit(f'store i8* {value_reg}, i8** {alloca_reg}')
        elif name in self._current_func_params:
            self._current_func_params[name] = value_reg

    def gen_binary_op(self, op, left_reg, right_reg):
        """生成二元运算，返回 (i8* 结果寄存器, 类型)"""
        l_i32 = self.new_register()
        r_i32 = self.new_register()
        result_i32 = self.new_register()
        result_str = self.new_register()
        self.emit(f'{l_i32} = call i32 @light_atoi(i8* {left_reg})')
        self.emit(f'{r_i32} = call i32 @light_atoi(i8* {right_reg})')
        if op == 'ADD':
            self.emit(f'{result_i32} = add i32 {l_i32}, {r_i32}')
        elif op == 'SUB':
            self.emit(f'{result_i32} = sub i32 {l_i32}, {r_i32}')
        elif op == 'MUL':
            self.emit(f'{result_i32} = mul i32 {l_i32}, {r_i32}')
        elif op == 'DIV':
            self.emit(f'{result_i32} = sdiv i32 {l_i32}, {r_i32}')
        else:
            self.emit(f'{result_i32} = add i32 {l_i32}, {r_i32}')
        self.emit(f'{result_str} = call i8* @light_itoa(i32 {result_i32})')
        return result_str, 'i8*'

    def gen_cmp(self, op, left_reg, right_reg):
        """生成比较，返回 i1"""
        eq_reg = self.new_register()
        self.emit(f'{eq_reg} = call i32 @light_str_eq(i8* {left_reg}, i8* {right_reg})')
        if op == 'EQ':
            cmp_reg = self.new_register()
            self.emit(f'{cmp_reg} = icmp ne i32 {eq_reg}, 0')
        elif op == 'NE':
            cmp_reg = self.new_register()
            self.emit(f'{cmp_reg} = icmp eq i32 {eq_reg}, 0')
        elif op in ('LT', 'GT', 'LE', 'GE'):
            l_i32 = self.new_register()
            r_i32 = self.new_register()
            self.emit(f'{l_i32} = call i32 @light_atoi(i8* {left_reg})')
            self.emit(f'{r_i32} = call i32 @light_atoi(i8* {right_reg})')
            cmp_reg = self.new_register()
            if op == 'LT':
                self.emit(f'{cmp_reg} = icmp slt i32 {l_i32}, {r_i32}')
            elif op == 'GT':
                self.emit(f'{cmp_reg} = icmp sgt i32 {l_i32}, {r_i32}')
            elif op == 'LE':
                self.emit(f'{cmp_reg} = icmp sle i32 {l_i32}, {r_i32}')
            elif op == 'GE':
                self.emit(f'{cmp_reg} = icmp sge i32 {l_i32}, {r_i32}')
        return cmp_reg

    def gen_string_constant(self, value):
        """生成字符串常量"""
        label = self._emit_string(value)
        return self._get_string_ptr(label)

    def gen_global_var(self, name, init_value=''):
        """声明全局变量"""
        self._globals[name] = init_value

    def finalize(self):
        """生成最终 IR"""
        lines = []
        # 字符串声明
        for s in self._string_decls:
            lines.append(s)
        if self._string_decls:
            lines.append('')
        # 外部函数声明
        for f in sorted(self._func_decls):
            lines.append(f)
        lines.append('')
        # 全局变量声明
        for name in self._globals:
            safe = self._safe_var_name(name)
            lines.append(f'@__var_{safe} = global i8* null')
        if self._globals:
            lines.append('')
        # 主体代码
        lines.extend(self._lines)
        return '\n'.join(lines)