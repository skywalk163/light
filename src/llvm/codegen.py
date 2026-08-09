"""
LLVM 代码生成器 - 基础版 (string 模式)
基于字符串类型系统 (i8*)，作为 TypedLLVMCodeGen 的父类。
适配 src/ast_nodes.py 的 AST 节点。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from .core import LLVMCodeGenCore
except ImportError:
    from core import LLVMCodeGenCore
import ast_nodes as ast


class LLVMCodeGen(LLVMCodeGenCore):
    """光明 LLVM 代码生成器（string 模式，基础版）"""

    def __init__(self):
        super().__init__()
        self._segments = {}
        self._segment_order = []
        self._segment_bodies = {}
        self._module_statements = []
        self._loop_break_labels = []
        self._loop_continue_labels = []
        self._declared_vars = set()
        self._ffi_libraries = {}
        self._ffi_functions = {}

    def generate(self, module) -> str:
        self.declare_runtime()

        for stmt in module.statements:
            if isinstance(stmt, ast.ImportStatement):
                continue
            self._collect_statement(stmt)
        for seg in module.segments:
            self._collect_segment(seg)

        self._gen_global_init()

        for seg_name in self._segment_order:
            params = self._segments[seg_name]
            body = self._segment_bodies.get(seg_name, [])
            self._gen_segment_function(seg_name, params, body)

        self._gen_main()

        return self.finalize()

    def _collect_segment(self, seg):
        name = seg.name
        params = [(p.name, p.default_value) for p in seg.parameters]
        self._segments[name] = params
        self._segment_order.append(name)
        self._segment_bodies[name] = seg.body

    def _collect_statement(self, stmt):
        if isinstance(stmt, ast.VariableDeclaration):
            name = stmt.name
            if name:
                self.gen_global_var(name)
                self._declared_vars.add(name)
        elif isinstance(stmt, ast.Assignment):
            name = self._get_var_name(stmt.target)
            if name and name not in self._globals:
                self.gen_global_var(name)
                self._declared_vars.add(name)
        elif isinstance(stmt, ast.FFILoadLibraryStatement):
            # FFI 加载库：记录到模块中
            self._ffi_libraries[stmt.alias] = stmt.library_path
        elif isinstance(stmt, ast.FFIFunctionDeclaration):
            # FFI 函数声明：记录到模块中
            self._ffi_functions[stmt.name] = stmt
        elif isinstance(stmt, ast.FFICreateArray):
            # FFI 创建数组：暂存
            pass
        elif isinstance(stmt, ast.FFISetArrayElement):
            # FFI 设置数组：暂存
            pass
        elif isinstance(stmt, ast.FFIAllocMemory):
            # FFI 分配内存：暂存
            pass
        elif isinstance(stmt, ast.FFIFreeMemory):
            # FFI 释放内存：暂存
            pass
        elif isinstance(stmt, ast.FFISetPointerValue):
            # FFI 设指针值：暂存
            pass
        elif isinstance(stmt, ast.FFISetErrno):
            # FFI 设系统错误码：暂存
            pass
        elif isinstance(stmt, ast.FFITryCatch):
            # FFI 错误捕获：暂存
            pass
        elif isinstance(stmt, (ast.FFIEnumDef, ast.FFIUnionDef,
                                ast.FFICreateCallback, ast.FFIVarArgsDecl,
                                ast.FFIStructByValue, ast.FFILibraryPath)):
            # FFI 第三阶段：暂存
            pass
        elif isinstance(stmt, (ast.FFITypedefDef, ast.FFIBitfieldDef,
                                ast.FFIFuncPtrDef, ast.FFIDebugConfig,
                                ast.FFIPreprocessorDef)):
            # FFI 第四阶段：暂存
            pass
        self._module_statements.append(stmt)

    def _get_var_name(self, expr):
        if isinstance(expr, ast.Identifier):
            return expr.name
        if isinstance(expr, ast.PropertyAccess):
            return self._get_var_name(expr.obj)
        return None

    def _gen_global_init(self):
        self._current_func = '__init__'
        self._local_vars.clear()
        self._pending_allocas = []
        self.emit('define void @__light_init() {')
        self.emit('entry:')

        self._collect_vars_from_stmts(self._module_statements)
        for vname in self._local_vars.keys():
            reg = self.new_register()
            self.emit(f'{reg} = alloca i8*')
            self._local_vars[vname] = reg

        for stmt in self._module_statements:
            self._gen_global_statement(stmt)

        self.emit('ret void')
        self.emit('}')
        self.emit_blank()

    def _gen_global_statement(self, stmt):
        if isinstance(stmt, ast.VariableDeclaration):
            name = stmt.name
            if name and name in self._globals:
                if stmt.value:
                    reg, _ = self._gen_expression(stmt.value)
                    safe = self._safe_var_name(name)
                    self.emit(f'store i8* {reg}, i8** @__var_{safe}')
                return
        if isinstance(stmt, ast.FFILoadLibraryStatement):
            # FFI 加载库：记录元数据，不生成 LLVM 声明
            return
        if isinstance(stmt, ast.FFIFunctionDeclaration):
            # FFI 函数声明：生成 LLVM declare
            self._gen_ffi_declare(stmt)
            return
        if isinstance(stmt, (ast.FFICreateArray, ast.FFISetArrayElement,
                              ast.FFIAllocMemory, ast.FFIFreeMemory,
                              ast.FFISetPointerValue, ast.FFISetErrno,
                              ast.FFITryCatch)):
            # FFI 第二阶段：暂不生成 LLVM
            return
        if isinstance(stmt, (ast.FFIEnumDef, ast.FFIUnionDef,
                              ast.FFICreateCallback, ast.FFIVarArgsDecl,
                              ast.FFIStructByValue, ast.FFILibraryPath)):
            # FFI 第三阶段：暂不生成 LLVM
            return
        if isinstance(stmt, (ast.FFITypedefDef, ast.FFIBitfieldDef,
                              ast.FFIFuncPtrDef, ast.FFIDebugConfig,
                              ast.FFIPreprocessorDef)):
            # FFI 第四阶段：暂不生成 LLVM
            return
        self._gen_statement(stmt)

    def _gen_main(self):
        self.emit('define i32 @main(i32 %argc, i8** %argv) {')
        self.emit('entry:')
        self.emit('call void @__light_init()')

        has_top_level_call = False
        main_names = {'主程序', '主入口', 'main'}
        for stmt in self._module_statements:
            if isinstance(stmt, ast.ExpressionStatement):
                expr = stmt.expression
                if isinstance(expr, ast.FunctionCall):
                    call_name = None
                    if isinstance(expr.name, ast.SegmentName):
                        call_name = expr.name.name
                    elif isinstance(expr.name, ast.Identifier):
                        call_name = expr.name.name
                    if call_name in main_names:
                        has_top_level_call = True
                        break

        if not has_top_level_call:
            for name in main_names:
                if name in self._segments:
                    safe = self._safe_func_name(name)
                    params = self._segments[name]
                    reg = self.new_register()
                    if params:
                        self.emit(f'{reg} = call i8* @_seg_{safe}(i8* null)')
                    else:
                        self.emit(f'{reg} = call i8* @_seg_{safe}()')
                    break

        self.emit('ret i32 0')
        self.emit('}')
        self.emit_blank()

    def _gen_segment_function(self, name, params, body):
        self._current_func = name
        self._current_func_params = {}
        self._local_vars.clear()
        self._pending_allocas = []
        safe = self._safe_func_name(name)

        param_strs = []
        for i, (pname, default) in enumerate(params):
            reg = f'%__param_{i}'
            self._current_func_params[pname] = reg
            param_strs.append(f'i8* {reg}')

        self.emit(f'define i8* @_seg_{safe}({", ".join(param_strs)}) {{')
        self.emit('entry:')

        self._collect_vars_from_stmts(body)
        for vname in self._local_vars.keys():
            reg = self.new_register()
            self.emit(f'{reg} = alloca i8*')
            self._local_vars[vname] = reg

        for stmt in body:
            self._gen_statement(stmt)

        if not self._ends_with_terminator(body):
            self.emit('ret i8* null')
        self.emit('}')
        self.emit_blank()

    def _collect_vars_from_stmts(self, stmts):
        for stmt in stmts:
            if stmt is None:
                continue
            if isinstance(stmt, ast.VariableDeclaration):
                if stmt.name and stmt.name not in self._local_vars:
                    self._local_vars[stmt.name] = None
            elif isinstance(stmt, ast.IfStatement):
                self._collect_vars_from_stmts(stmt.then_body)
                if stmt.elseif_bodies:
                    for body in stmt.elseif_bodies:
                        self._collect_vars_from_stmts(body)
                if stmt.else_body:
                    self._collect_vars_from_stmts(stmt.else_body)
            elif isinstance(stmt, ast.ForeachStatement):
                var_name = getattr(stmt, 'variable', None) or getattr(stmt, 'var_name', None)
                if var_name and var_name not in self._local_vars:
                    self._local_vars[var_name] = None
                self._collect_vars_from_stmts(stmt.body)
            elif isinstance(stmt, ast.WhileStatement):
                self._collect_vars_from_stmts(stmt.body)

    def _ends_with_terminator(self, stmts):
        if not stmts:
            return False
        last = stmts[-1]
        if isinstance(last, ast.ReturnStatement):
            return True
        if isinstance(last, ast.BreakStatement):
            return True
        if isinstance(last, ast.ContinueStatement):
            return True
        if isinstance(last, ast.IfStatement):
            then_term = self._ends_with_terminator(last.then_body)
            else_term = self._ends_with_terminator(last.else_body) if last.else_body else False
            elseif_term = all(
                self._ends_with_terminator(body)
                for body in last.elseif_bodies
            ) if last.elseif_bodies else True
            return then_term and (else_term or not last.else_body) and elseif_term and bool(last.else_body or last.elseif_bodies)
        if isinstance(last, ast.WhileStatement):
            return False
        if isinstance(last, ast.ForeachStatement):
            return False
        return False

    def _gen_statement(self, stmt):
        if stmt is None:
            return
        if isinstance(stmt, ast.VariableDeclaration):
            self._gen_variable_declaration(stmt)
        elif isinstance(stmt, ast.Assignment):
            self._gen_assignment(stmt)
        elif isinstance(stmt, ast.CompoundAssignment):
            self._gen_compound_assignment(stmt)
        elif isinstance(stmt, ast.IfStatement):
            self._gen_if(stmt)
        elif isinstance(stmt, ast.ForeachStatement):
            self._gen_foreach(stmt)
        elif isinstance(stmt, ast.WhileStatement):
            self._gen_while(stmt)
        elif isinstance(stmt, ast.ReturnStatement):
            self._gen_return(stmt)
        elif isinstance(stmt, ast.BreakStatement):
            self._gen_break(stmt)
        elif isinstance(stmt, ast.ContinueStatement):
            self._gen_continue(stmt)
        elif isinstance(stmt, ast.PrintStatement):
            self._gen_print(stmt)
        elif isinstance(stmt, ast.ExpressionStatement):
            self._gen_expression(stmt.expression)
        elif isinstance(stmt, ast.ImportStatement):
            pass

    def _gen_variable_declaration(self, stmt):
        init_val = stmt.value
        self.alloca_local(stmt.name)
        if init_val:
            reg, rtype = self._gen_expression(init_val)
        else:
            reg = self.gen_string_constant("")
        self.set_var(stmt.name, reg)

    def _gen_assignment(self, stmt):
        name = self._get_var_name(stmt.target)
        reg, rtype = self._gen_expression(stmt.value)
        self.set_var(name, reg)

    def _gen_compound_assignment(self, stmt):
        name = stmt.target if isinstance(stmt.target, str) else self._get_var_name(stmt.target)
        cur = self.get_var(name)
        if cur is None:
            return
        op_map = {'加': 'ADD', '减': 'SUB', '乘': 'MUL', '除': 'DIV',
                  '模': 'MOD', '幂': 'MUL'}
        op = op_map.get(stmt.operator, 'ADD')
        val_reg, _ = self._gen_expression(stmt.value)
        result, _ = self.gen_binary_op(op, cur, val_reg)
        self.set_var(name, result)

    def _gen_if(self, stmt):
        cond_reg, _ = self._gen_expression(stmt.condition)
        zero = self.gen_string_constant("")
        false_str = self.gen_string_constant("假")
        cmp = self.new_register()
        self.emit(f'{cmp} = call i32 @light_str_eq(i8* {cond_reg}, i8* {zero})')
        false_cmp = self.new_register()
        self.emit(f'{false_cmp} = call i32 @light_str_eq(i8* {cond_reg}, i8* {false_str})')
        combined = self.new_register()
        self.emit(f'{combined} = or i32 {cmp}, {false_cmp}')
        final = self.new_register()
        self.emit(f'{final} = icmp ne i32 {combined}, 0')

        then_label = self.new_label('then')
        end_label = self.new_label('endif')

        elseif_labels = []
        for _ in stmt.elseif_conditions:
            elseif_labels.append(self.new_label('elseif'))

        if stmt.else_body:
            else_label = self.new_label('else')
        else:
            else_label = end_label

        next_label = elseif_labels[0] if elseif_labels else else_label
        self.emit(f'br i1 {final}, label %{next_label}, label %{then_label}')

        self.emit(f'{then_label}:')
        for s in stmt.then_body:
            self._gen_statement(s)
        if not self._ends_with_terminator(stmt.then_body):
            self.emit(f'br label %{end_label}')

        for idx, (eif_cond, eif_body) in enumerate(zip(stmt.elseif_conditions, stmt.elseif_bodies)):
            eif_label = elseif_labels[idx]
            next_label = elseif_labels[idx + 1] if idx + 1 < len(elseif_labels) else else_label

            self.emit(f'{eif_label}:')
            cond_reg, _ = self._gen_expression(eif_cond)
            cmp = self.new_register()
            self.emit(f'{cmp} = call i32 @light_str_eq(i8* {cond_reg}, i8* {zero})')
            false_cmp = self.new_register()
            self.emit(f'{false_cmp} = call i32 @light_str_eq(i8* {cond_reg}, i8* {false_str})')
            combined = self.new_register()
            self.emit(f'{combined} = or i32 {cmp}, {false_cmp}')
            final = self.new_register()
            self.emit(f'{final} = icmp ne i32 {combined}, 0')

            eif_then = self.new_label('eif_then')
            self.emit(f'br i1 {final}, label %{next_label}, label %{eif_then}')

            self.emit(f'{eif_then}:')
            for s in eif_body:
                self._gen_statement(s)
            if not self._ends_with_terminator(eif_body):
                self.emit(f'br label %{end_label}')

        if stmt.else_body:
            self.emit(f'{else_label}:')
            for s in stmt.else_body:
                self._gen_statement(s)
            if not self._ends_with_terminator(stmt.else_body):
                self.emit(f'br label %{end_label}')

        self.emit(f'{end_label}:')

    def _gen_foreach(self, stmt):
        var_name = stmt.variable.name if isinstance(stmt.variable, ast.Identifier) else str(stmt.variable)
        self.alloca_local(var_name)
        list_reg, _ = self._gen_expression(stmt.iterable)

        idx_reg = self.new_register()
        self.emit(f'{idx_reg} = alloca i32')
        self.emit(f'store i32 0, i32* {idx_reg}')

        len_reg = self.new_register()
        self.emit(f'{len_reg} = call i32 @light_list_len(i8* {list_reg})')

        loop_label = self.new_label('foreach_loop')
        body_label = self.new_label('foreach_body')
        end_label = self.new_label('foreach_end')

        self._loop_break_labels.append(end_label)
        self._loop_continue_labels.append(loop_label)

        self.emit(f'br label %{loop_label}')

        self.emit(f'{loop_label}:')
        i = self.new_register()
        self.emit(f'{i} = load i32, i32* {idx_reg}')
        cmp = self.new_register()
        self.emit(f'{cmp} = icmp slt i32 {i}, {len_reg}')
        self.emit(f'br i1 {cmp}, label %{body_label}, label %{end_label}')

        self.emit(f'{body_label}:')
        elem = self.new_register()
        self.emit(f'{elem} = call i8* @light_list_get(i8* {list_reg}, i32 {i})')
        self.set_var(var_name, elem)

        for s in stmt.body:
            self._gen_statement(s)

        if not self._ends_with_terminator(stmt.body):
            next_i = self.new_register()
            self.emit(f'{next_i} = add i32 {i}, 1')
            self.emit(f'store i32 {next_i}, i32* {idx_reg}')
            self.emit(f'br label %{loop_label}')

        self.emit(f'{end_label}:')
        self._loop_break_labels.pop()
        self._loop_continue_labels.pop()

    def _gen_while(self, stmt):
        cond_label = self.new_label('while_cond')
        body_label = self.new_label('while_body')
        end_label = self.new_label('while_end')

        self._loop_break_labels.append(end_label)
        self._loop_continue_labels.append(cond_label)

        self.emit(f'br label %{cond_label}')

        self.emit(f'{cond_label}:')
        cond_reg, _ = self._gen_expression(stmt.condition)
        zero = self.gen_string_constant("")
        false_str = self.gen_string_constant("假")
        cmp1 = self.new_register()
        self.emit(f'{cmp1} = call i32 @light_str_eq(i8* {cond_reg}, i8* {zero})')
        cmp2 = self.new_register()
        self.emit(f'{cmp2} = call i32 @light_str_eq(i8* {cond_reg}, i8* {false_str})')
        combined = self.new_register()
        self.emit(f'{combined} = or i32 {cmp1}, {cmp2}')
        final = self.new_register()
        self.emit(f'{final} = icmp ne i32 {combined}, 0')
        self.emit(f'br i1 {final}, label %{end_label}, label %{body_label}')

        self.emit(f'{body_label}:')
        for s in stmt.body:
            self._gen_statement(s)
        if not self._ends_with_terminator(stmt.body):
            self.emit(f'br label %{cond_label}')

        self.emit(f'{end_label}:')
        self._loop_break_labels.pop()
        self._loop_continue_labels.pop()

    def _gen_return(self, stmt):
        if stmt.value:
            reg, _ = self._gen_expression(stmt.value)
            self.emit(f'ret i8* {reg}')
        else:
            self.emit('ret i8* null')

    def _gen_break(self, stmt):
        if self._loop_break_labels:
            self.emit(f'br label %{self._loop_break_labels[-1]}')

    def _gen_continue(self, stmt):
        if self._loop_continue_labels:
            self.emit(f'br label %{self._loop_continue_labels[-1]}')

    def _gen_print(self, stmt):
        if stmt.value:
            reg, _ = self._gen_expression(stmt.value)
            self.emit(f'call void @light_println(i8* {reg})')
        else:
            self.emit('call void @light_println(i8* null)')

    def _gen_expression(self, expr):
        if expr is None:
            return self.gen_string_constant(""), 'i8*'

        if isinstance(expr, ast.StringLiteral):
            return self.gen_string_constant(expr.value), 'i8*'

        if isinstance(expr, ast.NumberLiteral):
            return self.gen_string_constant(str(expr.value)), 'i8*'

        if isinstance(expr, ast.BooleanLiteral):
            val = "真" if expr.value else "假"
            return self.gen_string_constant(val), 'i8*'

        if isinstance(expr, ast.NullLiteral):
            return self.gen_string_constant(""), 'i8*'

        if isinstance(expr, ast.Identifier):
            return self._gen_identifier(expr)

        if isinstance(expr, ast.BinaryOp):
            return self._gen_binary_op(expr)

        if isinstance(expr, ast.UnaryOp):
            return self._gen_unary_op(expr)

        if isinstance(expr, ast.FunctionCall):
            return self._gen_function_call(expr)

        if isinstance(expr, ast.PropertyAccess):
            return self._gen_property_access(expr)

        if isinstance(expr, ast.IndexAccess):
            return self._gen_index_access(expr)

        if isinstance(expr, ast.ListLiteral):
            return self._gen_list_literal(expr)

        if isinstance(expr, ast.ConditionalExpression):
            return self._gen_conditional(expr)

        return self.gen_string_constant(""), 'i8*'

    def _gen_identifier(self, expr):
        name = expr.name
        var = self.get_var(name)
        if var is not None:
            return var, 'i8*'
        if name in ('时间戳', '时间'):
            reg = self.new_register()
            self.emit(f'{reg} = call double @light_timestamp()')
            str_reg = self.new_register()
            self.emit(f'{str_reg} = call i8* @light_ftoa(double {reg})')
            return str_reg, 'i8*'
        if name == '输入' or name == 'input':
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_input()')
            return reg, 'i8*'
        return self.gen_string_constant(""), 'i8*'

    def _gen_binary_op(self, expr):
        left_reg, lt = self._gen_expression(expr.left)
        right_reg, rt = self._gen_expression(expr.right)
        op = expr.operator

        if op in ('==', '等于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('EQ', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'
        if op in ('!=', '不等于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('NE', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'
        if op in ('<', '小于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('LT', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'
        if op in ('>', '大于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('GT', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'
        if op in ('<=', '小于等于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('LE', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'
        if op in ('>=', '大于等于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('GE', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'

        if op == '+':
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_concat(i8* {left_reg}, i8* {right_reg})')
            return reg, 'i8*'

        if op == '连接':
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_concat(i8* {left_reg}, i8* {right_reg})')
            return reg, 'i8*'

        llvm_op = 'ADD'
        if op == '-':
            llvm_op = 'SUB'
        elif op == '*':
            llvm_op = 'MUL'
        elif op == '/':
            llvm_op = 'DIV'
        elif op in ('加', '减', '乘', '除'):
            op_map = {'加': 'ADD', '减': 'SUB', '乘': 'MUL', '除': 'DIV'}
            llvm_op = op_map.get(op, 'ADD')

        return self.gen_binary_op(llvm_op, left_reg, right_reg)

    def _gen_unary_op(self, expr):
        reg, rtype = self._gen_expression(expr.operand)
        if expr.operator == '非':
            zero = self.gen_string_constant("")
            false_str = self.gen_string_constant("假")
            cmp1 = self.new_register()
            self.emit(f'{cmp1} = call i32 @light_str_eq(i8* {reg}, i8* {zero})')
            cmp2 = self.new_register()
            self.emit(f'{cmp2} = call i32 @light_str_eq(i8* {reg}, i8* {false_str})')
            combined = self.new_register()
            self.emit(f'{combined} = or i32 {cmp1}, {cmp2}')
            true_str = self.gen_string_constant("真")
            false_str2 = self.gen_string_constant("假")
            result = self.new_register()
            self.emit(f'{result} = select i1 {combined}, i8* {true_str}, i8* {false_str2}')
            return result, 'i8*'
        if expr.operator == '-':
            neg = self.new_register()
            self.emit(f'{neg} = call i32 @light_atoi(i8* {reg})')
            neg_val = self.new_register()
            self.emit(f'{neg_val} = sub i32 0, {neg}')
            result = self.new_register()
            self.emit(f'{result} = call i8* @light_itoa(i32 {neg_val})')
            return result, 'i8*'
        return reg, rtype

    def _gen_function_call(self, expr):
        if isinstance(expr.name, ast.Identifier):
            func_name = expr.name.name
        elif isinstance(expr.name, ast.SegmentName):
            func_name = expr.name.name
        elif isinstance(expr.name, ast.PropertyAccess):
            return self._gen_method_call(expr)
        elif isinstance(expr.name, str):
            func_name = expr.name
        else:
            func_name = str(expr.name)

        args = []
        for arg in expr.arguments:
            reg, _ = self._gen_expression(arg)
            args.append(reg)

        builtin = self._gen_builtin_call(func_name, args)
        if builtin is not None:
            return builtin

        if func_name in self._segments:
            return self._gen_segment_call(func_name, args)

        # FFI 函数调用
        if func_name in self._ffi_functions:
            return self._gen_ffi_call(func_name, args)

        return self.gen_string_constant(""), 'i8*'

    def _gen_method_call(self, expr):
        prop = expr.name
        if not isinstance(prop, ast.PropertyAccess):
            return self.gen_string_constant(""), 'i8*'

        obj_name = prop.obj.name if isinstance(prop.obj, ast.Identifier) else str(prop.obj)
        method = prop.property_name if hasattr(prop, 'property_name') else prop.member

        obj_reg, _ = self._gen_expression(prop.obj)
        args = []
        for arg in expr.arguments:
            reg, _ = self._gen_expression(arg)
            args.append(reg)

        if method == '长度' or method == 'length' or method == 'len':
            reg = self.new_register()
            self.emit(f'{reg} = call i32 @light_list_len(i8* {obj_reg})')
            str_reg = self.new_register()
            self.emit(f'{str_reg} = call i8* @light_itoa(i32 {reg})')
            return str_reg, 'i8*'

        if method == '追加' or method == 'append' or method == 'push':
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_list_append(i8* {obj_reg}, i8* {args[0] if args else self.gen_string_constant("")})')
            self.set_var(obj_name, reg)
            return reg, 'i8*'

        if method == '清空' or method == 'clear':
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_list_clear(i8* {obj_reg})')
            self.set_var(obj_name, reg)
            return reg, 'i8*'

        return self.gen_string_constant(""), 'i8*'

    def _gen_builtin_call(self, name, args):
        if name == '输出' or name == '打印':
            if args:
                self.emit(f'call void @light_println(i8* {args[0]})')
            else:
                self.emit('call void @light_println(i8* null)')
            return self.gen_string_constant(""), 'i8*'

        if name == '输入' or name == 'input':
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_input()')
            return reg, 'i8*'

        if name == '时间戳' or name == '时间':
            reg = self.new_register()
            self.emit(f'{reg} = call double @light_timestamp()')
            str_reg = self.new_register()
            self.emit(f'{str_reg} = call i8* @light_ftoa(double {reg})')
            return str_reg, 'i8*'

        if name == '格式化时间':
            ts_reg = args[0] if args else self.gen_string_constant("0")
            fmt_reg = args[1] if len(args) > 1 else self.gen_string_constant("%Y-%m-%d %H:%M:%S")
            dbl = self.new_register()
            self.emit(f'{dbl} = call double @light_atof(i8* {ts_reg})')
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_format_time(double {dbl}, i8* {fmt_reg})')
            return reg, 'i8*'

        if name == '文件存在':
            empty_str = args[0] if args else self.gen_string_constant("")
            reg = self.new_register()
            self.emit(f'{reg} = call i32 @light_file_exists(i8* {empty_str})')
            cmp_reg = self.new_register()
            self.emit(f'{cmp_reg} = icmp ne i32 {reg}, 0')
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp_reg}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'

        if name == '读取文件':
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_read_file(i8* {args[0] if args else self.gen_string_constant("")})')
            return reg, 'i8*'

        if name == '写入文件':
            self.emit(f'call void @light_write_file(i8* {args[0] if args else self.gen_string_constant("")}, i8* {args[1] if len(args) > 1 else self.gen_string_constant("")})')
            return self.gen_string_constant(""), 'i8*'

        if name == 'float' or name == '浮点数':
            if args:
                reg = self.new_register()
                self.emit(f'{reg} = call double @light_atof(i8* {args[0]})')
                str_reg = self.new_register()
                self.emit(f'{str_reg} = call i8* @light_ftoa(double {reg})')
                return str_reg, 'i8*'
            return self.gen_string_constant("0"), 'i8*'

        if name == 'int' or name == '整数':
            if args:
                reg = self.new_register()
                self.emit(f'{reg} = call i32 @light_atoi(i8* {args[0]})')
                str_reg = self.new_register()
                self.emit(f'{str_reg} = call i8* @light_itoa(i32 {reg})')
                return str_reg, 'i8*'
            return self.gen_string_constant("0"), 'i8*'

        if name == 'str' or name == '字符串':
            return args[0], 'i8*' if args else (self.gen_string_constant(""), 'i8*')

        if name == 'len' or name == '长度':
            if args:
                reg = self.new_register()
                self.emit(f'{reg} = call i32 @light_list_len(i8* {args[0]})')
                str_reg = self.new_register()
                self.emit(f'{str_reg} = call i8* @light_itoa(i32 {reg})')
                return str_reg, 'i8*'
            return self.gen_string_constant("0"), 'i8*'

        if name == '连接':
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_concat(i8* {args[0] if len(args) > 0 else self.gen_string_constant("")}, i8* {args[1] if len(args) > 1 else self.gen_string_constant("")})')
            return reg, 'i8*'

        return None

    def _gen_segment_call(self, name, args):
        safe = self._safe_func_name(name)
        arg_strs = []
        for arg in args:
            arg_strs.append(f'i8* {arg}')
        reg = self.new_register()
        self.emit(f'{reg} = call i8* @_seg_{safe}({", ".join(arg_strs)})')
        return reg, 'i8*'

    def _gen_property_access(self, expr):
        obj_name = expr.obj.name if isinstance(expr.obj, ast.Identifier) else str(expr.obj)
        prop = expr.property_name if hasattr(expr, 'property_name') else getattr(expr, 'member', '')

        if obj_name == '己' or obj_name == 'self':
            return self.gen_string_constant(""), 'i8*'

        return self.gen_string_constant(""), 'i8*'

    def _gen_index_access(self, expr):
        obj_reg, _ = self._gen_expression(expr.obj)

        if isinstance(expr.index, ast.NumberLiteral):
            idx_val = int(expr.index.value)
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_list_get(i8* {obj_reg}, i32 {idx_val})')
            return reg, 'i8*'

        idx_reg, _ = self._gen_expression(expr.index)
        i32 = self.new_register()
        self.emit(f'{i32} = call i32 @light_atoi(i8* {idx_reg})')
        reg = self.new_register()
        self.emit(f'{reg} = call i8* @light_list_get(i8* {obj_reg}, i32 {i32})')
        return reg, 'i8*'

    def _gen_list_literal(self, expr):
        reg = self.new_register()
        self.emit(f'{reg} = call i8* @light_list_new()')
        for elem in expr.elements:
            elem_reg, _ = self._gen_expression(elem)
            new_reg = self.new_register()
            self.emit(f'{new_reg} = call i8* @light_list_append(i8* {reg}, i8* {elem_reg})')
            reg = new_reg
        return reg, 'i8*'

    def _gen_conditional(self, expr):
        cond_reg, _ = self._gen_expression(expr.condition)
        zero = self.gen_string_constant("")
        false_str = self.gen_string_constant("假")
        cmp1 = self.new_register()
        self.emit(f'{cmp1} = call i32 @light_str_eq(i8* {cond_reg}, i8* {zero})')
        cmp2 = self.new_register()
        self.emit(f'{cmp2} = call i32 @light_str_eq(i8* {cond_reg}, i8* {false_str})')
        combined = self.new_register()
        self.emit(f'{combined} = or i32 {cmp1}, {cmp2}')
        final = self.new_register()
        self.emit(f'{final} = icmp ne i32 {combined}, 0')

        then_label = self.new_label('cond_then')
        else_label = self.new_label('cond_else')
        end_label = self.new_label('cond_end')

        result_reg = self.new_register()
        self.emit(f'{result_reg} = alloca i8*')
        self.emit(f'br i1 {final}, label %{else_label}, label %{then_label}')

        self.emit(f'{then_label}:')
        then_reg, _ = self._gen_expression(expr.then_expr)
        self.emit(f'store i8* {then_reg}, i8** {result_reg}')
        self.emit(f'br label %{end_label}')

        self.emit(f'{else_label}:')
        else_reg, _ = self._gen_expression(expr.else_expr)
        self.emit(f'store i8* {else_reg}, i8** {result_reg}')
        self.emit(f'br label %{end_label}')

        self.emit(f'{end_label}:')
        loaded = self.new_register()
        self.emit(f'{loaded} = load i8*, i8** {result_reg}')
        return loaded, 'i8*'

    # =========================================================================
    # C FFI 方法（LLVM 后端）
    # =========================================================================

    # FFI 光明类型 → LLVM 类型映射
    _ffi_type_llvm_map = {
        '整数': 'i32',
        '小数': 'double',
        '浮数': 'double',
        '文本': 'i8*',
        '串': 'i8*',
        '布尔': 'i1',
        '空': 'i8*',
        '数': 'double',
        '无': 'void',
    }

    def _gen_ffi_declare(self, stmt):
        """生成 LLVM declare 外部函数声明"""
        c_name = stmt.c_name or stmt.name
        ret_type = 'void'
        if stmt.return_type:
            ret_type = self._ffi_type_llvm_map.get(stmt.return_type, 'i8*')
        arg_types = []
        for p in stmt.params:
            light_type = p.get('type', '整数')
            llvm_type = self._ffi_type_llvm_map.get(light_type, 'i32')
            arg_types.append(llvm_type)
        arg_str = ', '.join(arg_types)
        self.emit(f'declare {ret_type} @{c_name}({arg_str})')
        self.emit_blank()

    def _gen_ffi_call(self, func_name, args):
        """生成 LLVM FFI 函数调用"""
        stmt = self._ffi_functions.get(func_name)
        if not stmt:
            return self.gen_string_constant(""), 'i8*'
        c_name = stmt.c_name or func_name
        ret_type = stmt.return_type
        ret_llvm = 'void'
        if ret_type:
            ret_llvm = self._ffi_type_llvm_map.get(ret_type, 'i8*')
        arg_strs = []
        for i, p in enumerate(stmt.params):
            light_type = p.get('type', '整数')
            llvm_type = self._ffi_type_llvm_map.get(light_type, 'i32')
            if i < len(args):
                if light_type in ('整数',):
                    conv_reg = self.new_register()
                    self.emit(f'{conv_reg} = call i32 @light_atoi(i8* {args[i]})')
                    arg_strs.append(f'i32 {conv_reg}')
                elif light_type in ('小数', '浮数', '数'):
                    conv_reg = self.new_register()
                    self.emit(f'{conv_reg} = call double @light_atof(i8* {args[i]})')
                    arg_strs.append(f'double {conv_reg}')
                elif light_type in ('布尔',):
                    conv_reg = self.new_register()
                    self.emit(f'{conv_reg} = call i32 @light_str_eq(i8* {args[i]}, i8* {self.gen_string_constant("真")})')
                    arg_strs.append(f'i1 {conv_reg}')
                else:
                    arg_strs.append(f'{llvm_type} {args[i]}')
            else:
                arg_strs.append(f'{llvm_type} null')
        reg = self.new_register()
        resolved_args = ', '.join(arg_strs)
        self.emit(f'{reg} = call {ret_llvm} @{c_name}({resolved_args})')
        if ret_type in ('整数',):
            str_reg = self.new_register()
            self.emit(f'{str_reg} = call i8* @light_itoa(i32 {reg})')
            return str_reg, 'i8*'
        elif ret_type in ('小数', '浮数', '数'):
            str_reg = self.new_register()
            self.emit(f'{str_reg} = call i8* @light_ftoa(double {reg})')
            return str_reg, 'i8*'
        elif ret_llvm == 'void':
            return self.gen_string_constant(""), 'i8*'
        return reg, ret_llvm
