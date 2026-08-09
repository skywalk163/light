"""
LLVM 代码生成器 - v2
基于字符串类型系统 (i8*)，直接编译为原生代码
支持两种 AST：antlrparser/light_ast.py 和 src/ast_nodes.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llvm_core import LLVMCodeGenCore

_AST_TYPES_LOADED = False
_Module = None
_SegmentDefinition = None
_FunctionCall = None
_Identifier = None
_StringLiteral = None
_NumberLiteral = None
_BooleanLiteral = None
_BinaryOp = None
_PropertyAccess = None
_IndexAccess = None
_PrintStatement = None
_VariableDeclaration = None
_Assignment = None
_IfStatement = None
_ForeachStatement = None
_WhileStatement = None
_ReturnStatement = None
_BreakStatement = None
_ContinueStatement = None
_ExpressionStatement = None
_ImportStatement = None
_ListLiteral = None
_SegmentName = None
_SelfReference = None
_UnaryOp = None
_ConditionalExpression = None
_CompoundAssignment = None
_Parameter = None
_NullLiteral = None
_DictLiteral = None
_DictEntry = None
_NewExpression = None
_StringInterpolation = None


def _load_ast_types(module):
    """根据传入的 module 对象动态加载对应的 AST 类型"""
    global _AST_TYPES_LOADED
    global _Module, _SegmentDefinition, _FunctionCall, _Identifier, _StringLiteral
    global _NumberLiteral, _BooleanLiteral, _BinaryOp, _PropertyAccess, _IndexAccess
    global _PrintStatement, _VariableDeclaration, _Assignment, _IfStatement
    global _ForeachStatement, _WhileStatement, _ReturnStatement, _BreakStatement
    global _ContinueStatement, _ExpressionStatement, _ImportStatement, _ListLiteral
    global _SegmentName, _SelfReference, _UnaryOp, _ConditionalExpression
    global _CompoundAssignment, _Parameter, _NullLiteral, _DictLiteral
    global _DictEntry, _NewExpression, _StringInterpolation

    if _AST_TYPES_LOADED:
        return

    import importlib

    node_module_name = type(module).__module__
    if node_module_name.startswith('ast_nodes'):
        ast_module = importlib.import_module('ast_nodes')
    elif node_module_name.startswith('light_ast'):
        ast_module = importlib.import_module('light_ast')
    else:
        try:
            ast_module = importlib.import_module('light_ast')
        except ImportError:
            src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            ast_module = importlib.import_module('ast_nodes')

    _Module = ast_module.Module
    _SegmentDefinition = ast_module.SegmentDefinition
    _FunctionCall = ast_module.FunctionCall
    _Identifier = ast_module.Identifier
    _StringLiteral = ast_module.StringLiteral
    _NumberLiteral = ast_module.NumberLiteral
    _BooleanLiteral = ast_module.BooleanLiteral
    _BinaryOp = ast_module.BinaryOp
    _PropertyAccess = getattr(ast_module, 'PropertyAccess', None) or getattr(ast_module, 'MemberAccess', None)
    _IndexAccess = ast_module.IndexAccess
    _PrintStatement = ast_module.PrintStatement
    _VariableDeclaration = ast_module.VariableDeclaration
    _Assignment = ast_module.Assignment
    _IfStatement = ast_module.IfStatement
    _ForeachStatement = ast_module.ForeachStatement
    _WhileStatement = ast_module.WhileStatement
    _ReturnStatement = ast_module.ReturnStatement
    _BreakStatement = ast_module.BreakStatement
    _ContinueStatement = ast_module.ContinueStatement
    _ExpressionStatement = ast_module.ExpressionStatement
    _ImportStatement = ast_module.ImportStatement
    _ListLiteral = ast_module.ListLiteral
    _SegmentName = getattr(ast_module, 'SegmentName', None)
    _SelfReference = getattr(ast_module, 'SelfReference', None)
    _UnaryOp = getattr(ast_module, 'UnaryOp', None)
    _ConditionalExpression = getattr(ast_module, 'ConditionalExpression', None)
    _CompoundAssignment = getattr(ast_module, 'CompoundAssignment', None)
    _Parameter = ast_module.Parameter
    _NullLiteral = getattr(ast_module, 'NullLiteral', None)
    _DictLiteral = getattr(ast_module, 'DictLiteral', None)
    _DictEntry = getattr(ast_module, 'DictEntry', None)
    _NewExpression = getattr(ast_module, 'NewExpression', None)
    _StringInterpolation = getattr(ast_module, 'StringInterpolation', None)

    _AST_TYPES_LOADED = True


class LLVMCodeGen(LLVMCodeGenCore):
    """光明 LLVM 代码生成器"""

    def __init__(self):
        super().__init__()
        self._segments = {}  # 段落名 → (参数列表, 是否已生成)
        self._segment_order = []  # 段落顺序
        self._segment_bodies = {}  # 段落名 → 语句列表
        self._module_statements = []  # 模块级语句（全局变量初始化等）
        self._loop_break_labels = []  # break 标签栈
        self._loop_continue_labels = []  # continue 标签栈
        self._declared_vars = set()  # 已声明的变量

    # ====================================
    # 公开接口
    # ====================================

    def generate(self, module) -> str:
        """生成 LLVM IR"""
        _load_ast_types(module)

        self.declare_runtime()

        # 第一遍：收集所有段落定义和全局变量
        for stmt in module.statements:
            if isinstance(stmt, _ImportStatement):
                continue
            self._collect_statement(stmt)
        for seg in module.segments:
            self._collect_segment(seg)

        # 生成全局变量初始化
        self._gen_global_init()

        # 生成所有段落函数
        for seg_name in self._segment_order:
            params = self._segments[seg_name]
            body = self._segment_bodies.get(seg_name, [])
            self._gen_segment_function(seg_name, params, body)

        # 生成 main 函数
        self._gen_main()

        return self.finalize()

    # ====================================
    # 收集阶段
    # ====================================

    def _collect_segment(self, seg: _SegmentDefinition):
        name = seg.name
        params = [(p.name, p.default_value) for p in seg.parameters]
        self._segments[name] = params
        self._segment_order.append(name)
        self._segment_bodies[name] = seg.body

    def _collect_statement(self, stmt):
        if isinstance(stmt, _VariableDeclaration):
            name = stmt.name
            if name:
                self.gen_global_var(name)
                self._declared_vars.add(name)
        elif isinstance(stmt, _Assignment):
            name = self._get_var_name(stmt.target)
            if name and name not in self._globals:
                self.gen_global_var(name)
                self._declared_vars.add(name)
        self._module_statements.append(stmt)

    def _get_var_name(self, expr):
        if isinstance(expr, _Identifier):
            return expr.name
        if isinstance(expr, _PropertyAccess):
            return self._get_var_name(expr.obj)
        return None

    # ====================================
    # 全局初始化
    # ====================================

    def _gen_global_init(self):
        self._current_func = '__init__'
        self._local_vars.clear()
        self._pending_allocas = []
        self.emit('define void @__light_init() {')
        self.emit('entry:')

        # 预收集所有局部变量并分配 alloca
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
        """处理全局变量声明/赋值 - 直接使用全局地址，不走 alloca"""
        if isinstance(stmt, _VariableDeclaration):
            name = stmt.name
            if name and name in self._globals:
                # 全局变量：直接发射 store 到全局地址
                if stmt.value:
                    reg, _ = self._gen_expression(stmt.value)
                    safe = self._safe_var_name(name)
                    self.emit(f'store i8* {reg}, i8** @__var_{safe}')
                return
        # 其他语句走正常流程
        self._gen_statement(stmt)

    # ====================================
    # main 函数
    # ====================================

    def _gen_main(self):
        self.emit('define i32 @main(i32 %argc, i8** %argv) {')
        self.emit('entry:')
        self.emit('call void @__light_init()')

        has_top_level_call = False
        main_names = {'主程序', '主入口', 'main'}
        for stmt in self._module_statements:
            if isinstance(stmt, _ExpressionStatement):
                expr = stmt.expression
                if isinstance(expr, _FunctionCall):
                    call_name = None
                    if isinstance(expr.name, _SegmentName):
                        call_name = expr.name.name
                    elif isinstance(expr.name, _Identifier):
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

    # ====================================
    # 段落函数生成
    # ====================================

    def _gen_segment_function(self, name, params, body):
        self._current_func = name
        self._current_func_params = {}
        self._local_vars.clear()
        self._pending_allocas = []
        safe = self._safe_func_name(name)

        # 参数
        param_strs = []
        for i, (pname, default) in enumerate(params):
            reg = f'%__param_{i}'
            self._current_func_params[pname] = reg
            param_strs.append(f'i8* {reg}')

        self.emit(f'define i8* @_seg_{safe}({", ".join(param_strs)}) {{')
        self.emit('entry:')

        # 预收集所有局部变量并分配 alloca
        self._collect_vars_from_stmts(body)
        for vname in self._local_vars.keys():
            reg = self.new_register()
            self.emit(f'{reg} = alloca i8*')
            self._local_vars[vname] = reg

        for stmt in body:
            self._gen_statement(stmt)

        self.emit('ret i8* null')
        self.emit('}')
        self.emit_blank()

    def _collect_vars_from_stmts(self, stmts):
        """递归收集语句中声明的所有局部变量名"""
        for stmt in stmts:
            if stmt is None:
                continue
            if isinstance(stmt, _VariableDeclaration):
                if stmt.name and stmt.name not in self._local_vars:
                    self._local_vars[stmt.name] = None
            elif isinstance(stmt, _IfStatement):
                self._collect_vars_from_stmts(stmt.then_body)
                if stmt.else_body:
                    self._collect_vars_from_stmts(stmt.else_body)
            elif isinstance(stmt, _ForeachStatement):
                var_name = getattr(stmt, 'variable', None) or getattr(stmt, 'var_name', None)
                if var_name and var_name not in self._local_vars:
                    self._local_vars[var_name] = None
                self._collect_vars_from_stmts(stmt.body)
            elif isinstance(stmt, _WhileStatement):
                self._collect_vars_from_stmts(stmt.body)
            elif isinstance(stmt, _CompoundAssignment):
                pass
            elif isinstance(stmt, _Assignment):
                pass

    # ====================================
    # 语句生成
    # ====================================

    def _ends_with_terminator(self, stmts):
        if not stmts:
            return False
        last = stmts[-1]
        if isinstance(last, _ReturnStatement):
            return True
        if isinstance(last, _BreakStatement):
            return True
        if isinstance(last, _ContinueStatement):
            return True
        if isinstance(last, _IfStatement):
            then_term = self._ends_with_terminator(last.then_body)
            else_term = self._ends_with_terminator(last.else_body) if last.else_body else False
            elseif_term = all(
                self._ends_with_terminator(body)
                for body in last.elseif_bodies
            ) if last.elseif_bodies else True
            return then_term and (else_term or not last.else_body) and elseif_term and bool(last.else_body or last.elseif_bodies)
        if isinstance(last, _WhileStatement):
            return False
        if isinstance(last, _ForeachStatement):
            return False
        return False

    def _gen_statement(self, stmt):
        if stmt is None:
            return
        if isinstance(stmt, _VariableDeclaration):
            self._gen_variable_declaration(stmt)
        elif isinstance(stmt, _Assignment):
            self._gen_assignment(stmt)
        elif isinstance(stmt, _CompoundAssignment):
            self._gen_compound_assignment(stmt)
        elif isinstance(stmt, _IfStatement):
            self._gen_if(stmt)
        elif isinstance(stmt, _ForeachStatement):
            self._gen_foreach(stmt)
        elif isinstance(stmt, _WhileStatement):
            self._gen_while(stmt)
        elif isinstance(stmt, _ReturnStatement):
            self._gen_return(stmt)
        elif isinstance(stmt, _BreakStatement):
            self._gen_break(stmt)
        elif isinstance(stmt, _ContinueStatement):
            self._gen_continue(stmt)
        elif isinstance(stmt, _PrintStatement):
            self._gen_print(stmt)
        elif isinstance(stmt, _ExpressionStatement):
            self._gen_expression(stmt.expression)
        elif isinstance(stmt, _ImportStatement):
            pass  # 运行时处理

    def _gen_variable_declaration(self, stmt: _VariableDeclaration):
        init_val = stmt.value
        self.alloca_local(stmt.name)
        if init_val:
            reg, rtype = self._gen_expression(init_val)
        else:
            reg = self.gen_string_constant("")
        self.set_var(stmt.name, reg)

    def _gen_assignment(self, stmt: _Assignment):
        name = self._get_var_name(stmt.target)
        reg, rtype = self._gen_expression(stmt.value)
        self.set_var(name, reg)

    def _gen_compound_assignment(self, stmt: _CompoundAssignment):
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

    def _gen_if(self, stmt: _IfStatement):
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

        # 收集所有 elseif 条件和对应的标签
        elseif_labels = []
        for _ in stmt.elseif_conditions:
            elseif_labels.append(self.new_label('elseif'))

        if stmt.else_body:
            else_label = self.new_label('else')
        else:
            else_label = end_label

        # 第一个条件分支
        next_label = elseif_labels[0] if elseif_labels else else_label
        self.emit(f'br i1 {final}, label %{next_label}, label %{then_label}')

        # then 分支
        self.emit(f'{then_label}:')
        for s in stmt.then_body:
            self._gen_statement(s)
        if not self._ends_with_terminator(stmt.then_body):
            self.emit(f'br label %{end_label}')

        # elseif 分支
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

        # else 分支
        if stmt.else_body:
            self.emit(f'{else_label}:')
            for s in stmt.else_body:
                self._gen_statement(s)
            if not self._ends_with_terminator(stmt.else_body):
                self.emit(f'br label %{end_label}')

        self.emit(f'{end_label}:')

    def _gen_foreach(self, stmt: _ForeachStatement):
        """遍历列表: 遍历 变量 于 列表 { ... }"""
        var_name = stmt.variable.name if isinstance(stmt.variable, _Identifier) else str(stmt.variable)
        # 先为循环变量分配栈空间
        self.alloca_local(var_name)
        list_reg, _ = self._gen_expression(stmt.iterable)

        # 初始化 - idx_reg 是临时寄存器，不需要延迟
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

    def _gen_while(self, stmt: _WhileStatement):
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
        self.emit(f'br label %{cond_label}')

        self.emit(f'{end_label}:')
        self._loop_break_labels.pop()
        self._loop_continue_labels.pop()

    def _gen_return(self, stmt: _ReturnStatement):
        if stmt.value:
            reg, _ = self._gen_expression(stmt.value)
            self.emit(f'ret i8* {reg}')
        else:
            self.emit('ret i8* null')

    def _gen_break(self, stmt: _BreakStatement):
        if self._loop_break_labels:
            self.emit(f'br label %{self._loop_break_labels[-1]}')

    def _gen_continue(self, stmt: _ContinueStatement):
        if self._loop_continue_labels:
            self.emit(f'br label %{self._loop_continue_labels[-1]}')

    def _gen_print(self, stmt: _PrintStatement):
        if stmt.value:
            reg, _ = self._gen_expression(stmt.value)
            self.emit(f'call void @light_println(i8* {reg})')
        else:
            self.emit('call void @light_println(i8* null)')

    # ====================================
    # 表达式生成 - 返回 (寄存器名, 类型)
    # ====================================

    def _gen_expression(self, expr):
        if expr is None:
            return self.gen_string_constant(""), 'i8*'

        if isinstance(expr, _StringLiteral):
            return self.gen_string_constant(expr.value), 'i8*'

        if isinstance(expr, _NumberLiteral):
            return self.gen_string_constant(str(expr.value)), 'i8*'

        if isinstance(expr, _BooleanLiteral):
            val = "真" if expr.value else "假"
            return self.gen_string_constant(val), 'i8*'

        if isinstance(expr, _NullLiteral):
            return self.gen_string_constant(""), 'i8*'

        if isinstance(expr, _Identifier):
            return self._gen_identifier(expr)

        if isinstance(expr, _BinaryOp):
            return self._gen_binary_op(expr)

        if isinstance(expr, _UnaryOp):
            return self._gen_unary_op(expr)

        if isinstance(expr, _FunctionCall):
            return self._gen_function_call(expr)

        if isinstance(expr, _PropertyAccess):
            return self._gen_property_access(expr)

        if isinstance(expr, _IndexAccess):
            return self._gen_index_access(expr)

        if isinstance(expr, _ListLiteral):
            return self._gen_list_literal(expr)

        if isinstance(expr, _ConditionalExpression):
            return self._gen_conditional(expr)

        # 默认返回空字符串
        return self.gen_string_constant(""), 'i8*'

    def _gen_identifier(self, expr: _Identifier):
        name = expr.name
        var = self.get_var(name)
        if var is not None:
            # get_var 已经处理了 load，现在 var 是 i8* 类型
            return var, 'i8*'
        # 可能是内置函数
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
        # 未定义的变量，返回空字符串
        return self.gen_string_constant(""), 'i8*'

    def _gen_binary_op(self, expr: _BinaryOp):
        left_reg, lt = self._gen_expression(expr.left)
        right_reg, rt = self._gen_expression(expr.right)
        op = expr.operator

        # 布尔运算
        if op == '且':
            op = 'AND'
        elif op == '或':
            op = 'OR'

        # 比较运算
        if op in ('==', 'EQ', '等于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('EQ', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'
        if op in ('!=', 'NE', '不等于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('NE', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'
        if op in ('<', 'LT', '小于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('LT', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'
        if op in ('>', 'GT', '大于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('GT', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'
        if op in ('<=', 'LE', '小于等于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('LE', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'
        if op in ('>=', 'GE', '大于等于'):
            true_str = self.gen_string_constant("真")
            false_str = self.gen_string_constant("假")
            cmp = self.gen_cmp('GE', left_reg, right_reg)
            str_reg = self.new_register()
            self.emit(f'{str_reg} = select i1 {cmp}, i8* {true_str}, i8* {false_str}')
            return str_reg, 'i8*'

        # 算术运算
        llvm_op = op
        if op == '+':
            llvm_op = 'ADD'
            # 字符串连接：如果左右操作数都是字符串，直接用 light_concat
            # 不需要先 atoi 再 itoa，这样更高效且正确
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_concat(i8* {left_reg}, i8* {right_reg})')
            return reg, 'i8*'

        # 算术运算（减、乘、除）
        if op == '-':
            llvm_op = 'SUB'
        elif op == '*':
            llvm_op = 'MUL'
        elif op == '/':
            llvm_op = 'DIV'
        elif op == '连接':
            # 字符串连接
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_concat(i8* {left_reg}, i8* {right_reg})')
            return reg, 'i8*'
        elif op in ('加', '减', '乘', '除'):
            # 中文算术关键字
            op_map = {'加': 'ADD', '减': 'SUB', '乘': 'MUL', '除': 'DIV'}
            llvm_op = op_map.get(op, 'ADD')
        else:
            llvm_op = 'ADD'

        return self.gen_binary_op(llvm_op, left_reg, right_reg)

    def _gen_unary_op(self, expr: _UnaryOp):
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

    def _gen_function_call(self, expr: _FunctionCall):
        # 获取函数名
        if isinstance(expr.name, _Identifier):
            func_name = expr.name.name
        elif isinstance(expr.name, _SegmentName):
            func_name = expr.name.name
        elif isinstance(expr.name, _PropertyAccess):
            return self._gen_method_call(expr)
        elif isinstance(expr.name, str):
            func_name = expr.name
        else:
            func_name = str(expr.name)

        # 生成参数
        args = []
        for arg in expr.arguments:
            reg, _ = self._gen_expression(arg)
            args.append(reg)

        # 内置函数
        builtin = self._gen_builtin_call(func_name, args)
        if builtin is not None:
            return builtin

        # 段落调用
        if func_name in self._segments:
            return self._gen_segment_call(func_name, args)

        # 未知函数，返回空字符串
        return self.gen_string_constant(""), 'i8*'

    def _gen_method_call(self, expr: _FunctionCall):
        """处理 obj.方法(args) 形式的调用"""
        prop = expr.name
        if not isinstance(prop, _PropertyAccess):
            return self.gen_string_constant(""), 'i8*'

        obj_name = prop.obj.name if isinstance(prop.obj, _Identifier) else str(prop.obj)
        method = prop.property_name if hasattr(prop, 'property_name') else prop.member

        # 生成对象和参数
        obj_reg, _ = self._gen_expression(prop.obj)
        args = []
        for arg in expr.arguments:
            reg, _ = self._gen_expression(arg)
            args.append(reg)

        # JSON 模块方法
        if obj_name == 'JSON' or obj_name == 'json':
            if method in ('序列化', '序列化JSON', 'dumps'):
                indent_reg = self.gen_string_constant("2") if len(args) < 2 else args[1]
                i32 = self.new_register()
                self.emit(f'{i32} = call i32 @light_atoi(i8* {indent_reg})')
                reg = self.new_register()
                self.emit(f'{reg} = call i8* @light_list_to_json(i8* {args[0]}, i32 {i32})')
                return reg, 'i8*'
            if method in ('解析', '解析JSON', 'loads'):
                reg = self.new_register()
                self.emit(f'{reg} = call i8* @light_json_parse(i8* {args[0]})')
                return reg, 'i8*'

        # 列表方法
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

        # 字符串方法
        if method == '长度' or method == 'len':
            reg = self.new_register()
            self.emit(f'{reg} = call i32 @light_str_len(i8* {obj_reg})')
            str_reg = self.new_register()
            self.emit(f'{str_reg} = call i8* @light_itoa(i32 {reg})')
            return str_reg, 'i8*'

        return self.gen_string_constant(""), 'i8*'

    def _gen_builtin_call(self, name, args):
        """生成内置函数调用，返回 (reg, type) 或 None"""
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
                # len() 用于列表时应该用 light_list_len
                # 注意：当前实现无法区分列表和字符串，统一用 light_list_len
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
        """调用用户定义的段落"""
        safe = self._safe_func_name(name)
        arg_strs = []
        for arg in args:
            arg_strs.append(f'i8* {arg}')
        reg = self.new_register()
        self.emit(f'{reg} = call i8* @_seg_{safe}({", ".join(arg_strs)})')
        return reg, 'i8*'

    def _gen_property_access(self, expr: _PropertyAccess):
        """属性访问: obj.属性"""
        obj_name = expr.obj.name if isinstance(expr.obj, _Identifier) else str(expr.obj)
        prop = expr.property_name if hasattr(expr, 'property_name') else getattr(expr, 'member', '')

        # 己属性 → self
        if obj_name == '己' or obj_name == 'self':
            return self.gen_string_constant(""), 'i8*'

        return self.gen_string_constant(""), 'i8*'

    def _gen_index_access(self, expr: _IndexAccess):
        """索引访问: obj[index]"""
        obj_reg, _ = self._gen_expression(expr.obj)
        
        # 如果索引是数字字面量，直接使用数字值，避免 atoi 转换开销
        if isinstance(expr.index, _NumberLiteral):
            idx_val = int(expr.index.value)
            reg = self.new_register()
            self.emit(f'{reg} = call i8* @light_list_get(i8* {obj_reg}, i32 {idx_val})')
            return reg, 'i8*'
        
        # 动态索引：需要计算
        idx_reg, _ = self._gen_expression(expr.index)
        i32 = self.new_register()
        self.emit(f'{i32} = call i32 @light_atoi(i8* {idx_reg})')
        reg = self.new_register()
        self.emit(f'{reg} = call i8* @light_list_get(i8* {obj_reg}, i32 {i32})')
        return reg, 'i8*'

    def _gen_list_literal(self, expr: _ListLiteral):
        """列表字面量"""
        reg = self.new_register()
        self.emit(f'{reg} = call i8* @light_list_new()')
        for elem in expr.elements:
            elem_reg, _ = self._gen_expression(elem)
            new_reg = self.new_register()
            self.emit(f'{new_reg} = call i8* @light_list_append(i8* {reg}, i8* {elem_reg})')
            reg = new_reg
        return reg, 'i8*'

    def _gen_conditional(self, expr: _ConditionalExpression):
        """三元条件表达式"""
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