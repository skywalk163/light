"""
LLVM 代码生成器核心 - v2
基于字符串类型系统 (i8*)
"""

import re


class LLVMCodeGenCore:
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
        """注册字符串常量，返回 (标签名, 字节长度)"""
        if s not in self._strings:
            self._str_counter += 1
            name = f'@.str.{self._str_counter}'
            utf8_bytes = s.encode('utf-8')
            byte_len = len(utf8_bytes) + 1
            self._strings[s] = (name, byte_len)
            # 转义每个字节为 LLVM IR 格式
            parts = []
            for b in utf8_bytes:
                if b == 0x5C:  # backslash
                    parts.append('\\5C')
                elif b == 0x22:  # double quote
                    parts.append('\\22')
                elif 0x20 <= b <= 0x7E:  # printable ASCII
                    parts.append(chr(b))
                else:
                    parts.append(f'\\{b:02X}')
            escaped = ''.join(parts)
            self._string_decls.append(f'{name} = private unnamed_addr constant [{byte_len} x i8] c"{escaped}\\00"')
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
        if name in self._globals:
            safe = self._safe_var_name(name)
            reg = self.new_register()
            self.emit(f'{reg} = load i8*, i8** @__var_{safe}')
            return reg
        if name in self._local_vars:
            alloca_reg = self._local_vars[name]
            reg = self.new_register()
            self.emit(f'{reg} = load i8*, i8** {alloca_reg}')
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
        """为局部变量分配栈空间"""
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
        for i, line in enumerate(self._pending_allocas):
            match = re.search(r'%(\d+)', line)
            if match:
                old_num = int(match.group(1))
                new_num = self._reg_counter + i + 1
                new_reg = f'%{new_num}'
                self._pending_allocas[i] = line.replace(f'%{old_num}', new_reg, 1)
                for name in list(self._local_vars.keys()):
                    if self._local_vars[name] == f'%{old_num}':
                        self._local_vars[name] = new_reg
        count = len(self._pending_allocas)
        for line in reversed(self._pending_allocas):
            self._lines.insert(insert_idx, line)
        self._pending_allocas = []
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
        """生成字符串常量，返回寄存器名 (i8*)"""
        name, byte_len = self._emit_string(value)
        reg = self.new_register()
        self.emit(f'{reg} = getelementptr inbounds [{byte_len} x i8], [{byte_len} x i8]* {name}, i64 0, i64 0')
        return reg

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

    # ============================================================
    # IR 验证工具
    # ============================================================

    def _verify_function(self, func_lines, func_name):
        """验证单个函数的 IR 结构正确性

        检查：
        1. 每个基本块以终止指令结尾（ret/br/unreachable/switch/indirectbr）
        2. 基本块标签不重复
        3. ret 之后没有死代码
        4. 寄存器定义不重复

        Args:
            func_lines: 该函数的 IR 行列表
            func_name: 函数名（用于错误信息）

        Returns:
            list: 错误信息列表，空列表表示通过
        """
        errors = []
        terminators = ('ret ', 'ret\t', 'br ', 'br\t', 'unreachable', 'switch ', 'indirectbr ')
        labels_seen = set()
        current_block = None
        block_start_idx = 0
        block_has_terminator = False

        i = 0
        while i < len(func_lines):
            line = func_lines[i].strip()

            # 跳过空行和注释
            if not line or line.startswith(';'):
                i += 1
                continue

            # 检查是否是基本块标签（格式：label: 或 label: ）
            if line.endswith(':') and not line.startswith('%') and not line.startswith('define') and not line.startswith('}'):
                # 先检查前一个块是否以终止指令结尾
                if current_block is not None and not block_has_terminator:
                    errors.append(f"函数 {func_name}: 基本块 '{current_block}' 缺少终止指令")

                label_name = line[:-1].strip()
                if label_name in labels_seen:
                    errors.append(f"函数 {func_name}: 重复的基本块标签 '{label_name}'")
                labels_seen.add(label_name)

                current_block = label_name
                block_start_idx = i
                block_has_terminator = False
                i += 1
                continue

            # 检查函数定义结束
            if line == '}':
                if current_block is not None and not block_has_terminator:
                    errors.append(f"函数 {func_name}: 基本块 '{current_block}' 缺少终止指令")
                break

            # 检查终止指令
            if any(line.startswith(t) for t in terminators):
                if block_has_terminator:
                    errors.append(f"函数 {func_name}: 基本块 '{current_block}' 在终止指令之后存在多余指令")
                block_has_terminator = True
                # 多行终止指令（典型是 switch）：
                #   switch i32 %r, label %end [
                #     i32 0, label %resume_0
                #   ]
                # 后续 case 行与 `]` 是同一条指令的一部分，不是「终止指令之后的多余
                # 指令」。逐行扫描器此前把它们各记一条误报（每个 switch 恰好 2 条）。
                # 按方括号配平把整条指令一次吃掉：同行内配平的 `[4 x i32]` 之类
                # 深度为 0，不受影响。
                depth = line.count('[') - line.count(']')
                while depth > 0 and i + 1 < len(func_lines):
                    i += 1
                    depth += func_lines[i].count('[') - func_lines[i].count(']')
            elif block_has_terminator:

                # 终止指令之后存在非终止指令（死代码）
                errors.append(f"函数 {func_name}: 基本块 '{current_block}' 在终止指令之后存在多余指令")

            i += 1

        return errors

    def _verify_module_ir(self, ir_lines):
        """验证整个模块的 IR 结构

        解析 _lines 中的所有函数，对每个函数调用 _verify_function

        Args:
            ir_lines: IR 行列表（通常是 self._lines）

        Returns:
            list: 错误信息列表，空列表表示通过
        """
        all_errors = []
        in_function = False
        current_func_name = None
        current_func_lines = []

        for line in ir_lines:
            stripped = line.strip()

            # 检测函数定义开始
            if stripped.startswith('define ') and '{' in stripped:
                in_function = True
                # 提取函数名
                parts = stripped.split('@')
                if len(parts) >= 2:
                    func_name = parts[1].split('(')[0].split('{')[0].strip()
                else:
                    func_name = 'unknown'
                current_func_name = func_name
                current_func_lines = [line]
                continue

            if in_function:
                current_func_lines.append(line)
                if stripped == '}':
                    errors = self._verify_function(current_func_lines, current_func_name)
                    all_errors.extend(errors)
                    in_function = False
                    current_func_name = None
                    current_func_lines = []

        return all_errors