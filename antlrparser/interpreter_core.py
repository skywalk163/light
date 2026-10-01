"""
光明（Light）编程语言 解释执行器 - 核心模块

将 AST 节点解释执行为实际的运行结果。
支持：变量环境、表达式求值、语句执行、段落调用。
"""

import sys
import os
from typing import List, Optional, Union, Any, Dict, Tuple, Set
from dataclasses import dataclass, field

# 导入 AST 节点
from light_ast import (
    ASTNode, Module, NumberLiteral, StringLiteral, BooleanLiteral,
    NullLiteral, ListLiteral, DictLiteral, DictEntry,
    Identifier, SegmentName, ModuleName,
    BinaryOp, UnaryOp, FunctionCall, PipeExpression,
    PropertyAccess, IndexAccess, NewExpression,
    VariableDeclaration, Assignment, CompoundAssignment, IfStatement, ForeachStatement,
    WhileStatement, BreakStatement, ContinueStatement, ReturnStatement,
    TryStatement, ThrowStatement, PrintStatement, ExpressionStatement,
    Parameter, SegmentDefinition, DataTypeDefinition, ErrorTypeDefinition,
    ImportStatement, ExportStatement,
    ClassDefinition, InterfaceDefinition, MethodDefinition, ConstructorDefinition,
    InterfaceMethod, InterfaceProperty, SelfReference,
    AwaitExpression, DeferStatement, AsyncScope,
    StringInterpolation,
)

# 导入模块解析器
from light_module import ModuleResolver, ModuleError

# =============================================================================
# 运行时值类型
# =============================================================================

class LightValue:
    """光明运行时值的包装"""
    
    def __init__(self, value: Any, type_name: str = None):
        self.value = value
        self.type_name = type_name or self._infer_type(value)
    
    def _infer_type(self, value: Any) -> str:
        if value is None:
            return '空'
        if isinstance(value, bool):
            return '布尔'
        if isinstance(value, (int, float)):
            return '数'
        if isinstance(value, str):
            return '串'
        if isinstance(value, list):
            return '列'
        if isinstance(value, dict):
            return '典'
        if isinstance(value, LightFunction):
            return '段'
        return type(value).__name__
    
    def is_truthy(self) -> bool:
        """判断是否为真值"""
        if self.value is None:
            return False
        if isinstance(self.value, bool):
            return self.value
        if isinstance(self.value, (int, float)):
            return self.value != 0
        if isinstance(self.value, str):
            return len(self.value) > 0
        if isinstance(self.value, list):
            return len(self.value) > 0
        if isinstance(self.value, dict):
            return len(self.value) > 0
        return True
    
    def __repr__(self):
        return f"{self.type_name}({repr(self.value)})"
    
    def __str__(self):
        if self.value is None:
            return '空'
        if isinstance(self.value, bool):
            return 'True' if self.value else 'False'
        if isinstance(self.value, dict):
            items = ', '.join(f'{k}: {v}' for k, v in self.value.items())
            return f'【{items}】'
        return str(self.value)


class LightFunction:
    """光明段落（函数）的运行时表示"""
    
    def __init__(self, definition: SegmentDefinition, closure: 'Environment'):
        self.definition = definition
        self.name = definition.name
        self.closure = closure  # 定义时的环境（闭包）
    
    def __repr__(self):
        return f"段({self.name})"


class LightBuiltinFunction:
    """内置函数的运行时表示"""
    
    def __init__(self, name: str, func: callable, min_args: int = 0, max_args: int = None):
        self.name = name
        self.func = func
        self.min_args = min_args
        self.max_args = max_args
    
    def __repr__(self):
        return f"内置({self.name})"


class LightClass:
    """光明类的运行时表示"""
    
    def __init__(self, definition, closure):
        self.definition = definition
        self.name = definition.name
        self.superclasses = definition.superclasses
        self.interfaces = definition.interfaces
        self.closure = closure
        self.methods = {}
        for method in definition.methods:
            self.methods[method.name] = method
        self.constructor = definition.constructor
    
    def new_instance(self, args=None):
        return LightInstance(self, args or [])
    
    def __repr__(self):
        return f"类({self.name})"


class LightInterface:
    """光明接口的运行时表示"""
    
    def __init__(self, definition):
        self.definition = definition
        self.name = definition.name
        self.superinterfaces = definition.superinterfaces
        self.method_signatures = {}
        for method in definition.methods:
            self.method_signatures[method.name] = method
        self.properties = {}
        for prop in definition.properties:
            self.properties[prop.name] = prop
    
    def __repr__(self):
        return f"接口({self.name})"


class LightInstance:
    """光明类实例的运行时表示"""
    
    def __init__(self, cls, args):
        self.cls = cls
        self.fields = {}
        
        for field in cls.definition.fields:
            if isinstance(field, VariableDeclaration):
                self.fields[field.name] = LightValue(None, '空')
        
        # 调用构造函数
        if cls.constructor:
            self._call_constructor(args)
    
    def _call_constructor(self, args):
        """调用构造函数"""
        constructor = self.cls.constructor
        if constructor is None:
            return
        
        # 创建构造函数执行环境
        call_env = self.cls.closure.create_child(f"构造({self.cls.name})")
        
        # 绑定参数
        param_names = [p.name for p in constructor.parameters]
        for i, name in enumerate(param_names):
            if i < len(args):
                call_env.define(name, args[i])
            else:
                call_env.define(name, LightValue(None, '空'))
        
        # 设置 self 引用
        call_env.define('自我', LightValue(self, '实例'))
        
        # 将实例字段添加到调用环境中
        for field_name, field_value in self.fields.items():
            call_env.define(field_name, field_value)
        
        # 执行构造函数体
        from light_interpreter import Interpreter
        interpreter = Interpreter()
        interpreter.env = call_env
        
        try:
            for stmt in constructor.body:
                interpreter._execute(stmt)
        finally:
            # 更新实例字段（构造函数中可能修改了字段值）
            for field_name in self.fields.keys():
                if call_env.has(field_name):
                    self.fields[field_name] = call_env.get(field_name)
    
    def get_field(self, name):
        if name in self.fields:
            return self.fields[name]
        raise RuntimeError(f"实例没有字段 '{name}'")
    
    def set_field(self, name, value):
        self.fields[name] = value
    
    def get_method(self, name):
        if name in self.cls.methods:
            return self.cls.methods[name]
        return None
    
    def __repr__(self):
        return f"实例({self.cls.name})"


class LightBoundMethod:
    """绑定到实例的方法"""
    
    def __init__(self, instance, method):
        self.instance = instance
        self.method = method
    
    def __repr__(self):
        return f"方法({self.method.name})"


# =============================================================================
# 环境管理
# =============================================================================

class Signal(BaseException):
    """控制流信号的基类"""
    pass


class ReturnSignal(Signal):
    """返回信号"""
    def __init__(self, value: LightValue = None):
        self.value = value or LightValue(None)


class BreakSignal(Signal):
    """跳出信号"""
    pass


class ContinueSignal(Signal):
    """跳过信号"""
    pass


class LightError(Signal):
    """光明运行时错误（对应 抛出/捕获）"""
    def __init__(self, message: str, value: LightValue = None):
        self.message = message
        self.value = value or LightValue(message, '串')


class Environment:
    """变量环境（作用域链）"""
    
    def __init__(self, parent: Optional['Environment'] = None, name: str = "全局"):
        self.variables: Dict[str, LightValue] = {}
        self.parent = parent
        self.name = name
        # 优化：缓存变量查找结果
        self._cache: Dict[str, LightValue] = {}
    
    def define(self, name: str, value: LightValue):
        """定义新变量（当前作用域）"""
        self.variables[name] = value
        # 更新缓存
        self._cache[name] = value
    
    def get(self, name: str) -> LightValue:
        """获取变量值（沿作用域链查找）- 优化版"""
        # 优化：先检查缓存
        cache = self._cache
        if name in cache:
            return cache[name]
        
        # 优化：使用局部变量减少属性查找
        vars = self.variables
        if name in vars:
            val = vars[name]
            cache[name] = val
            return val
        
        parent = self.parent
        if parent is not None:
            val = parent.get(name)
            cache[name] = val
            return val
        
        raise NameError(f"未定义的变量: '{name}'")
    
    def set(self, name: str, value: LightValue):
        """设置变量值（沿作用域链查找并修改）- 优化版"""
        if name in self.variables:
            self.variables[name] = value
            # 更新缓存
            self._cache[name] = value
            return
        if self.parent is not None:
            self.parent.set(name, value)
            # 更新缓存
            self._cache[name] = value
            return
        raise NameError(f"未定义的变量: '{name}'")
    
    def has(self, name: str) -> bool:
        """检查变量是否存在 - 优化版"""
        # 优化：先检查缓存
        if name in self._cache:
            return True
        if name in self.variables:
            return True
        if self.parent is not None:
            return self.parent.has(name)
        return False
    
    def create_child(self, name: str = "局部") -> 'Environment':
        """创建子作用域"""
        return Environment(parent=self, name=name)
    
    def __repr__(self):
        return f"环境({self.name}, vars={len(self.variables)})"


# =============================================================================
# 解释器核心基类
# =============================================================================

class InterpreterCore:
    """光明解释器核心 - 将 AST 解释执行为结果"""

    # 预编译运算符映射表（类级别常量，避免重复创建）
    _OP_PLUS = ('加', 'PLUS', '+')
    _OP_MINUS = ('减', 'MINUS', '-', 'K_MINUS')
    _OP_MULT = ('乘', 'MULTIPLY', '*')
    _OP_DIV = ('除', 'DIVIDE', '/')
    _OP_MOD = ('模', 'MOD', '%')
    _OP_POW = ('幂', 'POW', '^')
    _OP_GT = ('大于', 'GT', '>')
    _OP_LT = ('小于', 'LT', '<')
    _OP_EQ = ('等于', 'EQ', '==')
    _OP_NE = ('不等于', 'NE', '!=')
    _OP_GE = ('大于等于', 'GE', '>=')
    _OP_LE = ('小于等于', 'LE', '<=')
    _OP_AND = ('且', 'and', 'AND', '&&')
    _OP_OR = ('或', 'or', 'OR', '||')
    _OP_NOT = ('非', 'NOT', '!')

    def __init__(self, search_paths: List[str] = None):
        self.global_env = Environment(name="全局")
        self.env = self.global_env
        self.output_lines: List[str] = []  # 打印/输出捕获
        self._break_encountered = False  # 标记是否遇到跳出
        self._register_builtins()
        # 模块系统
        self.module_resolver = ModuleResolver(search_paths=search_paths or ['.'])
        self.current_filepath: Optional[str] = None  # 当前执行的文件路径
        self._imported_modules: Set[str] = set()  # 已完全处理的模块（防循环）
        
        # 性能优化：缓存内置函数查找
        self._builtin_cache: Dict[str, Optional[LightValue]] = {}
        self._fill_builtin_cache()

    def _fill_builtin_cache(self):
        """预填充内置函数缓存"""
        for name in ['abs', 'max', 'min', 'sqrt', 'pow', 'round', 'len', 'trim',
                     'substring', 'listLen', 'listAppend', 'listReverse',
                     'listIndexOf', 'listContains', 'listSlice', 'listConcat',
                     'printDebug', 'assert', '_典', '_串化', '_数化']:
            try:
                val = self.global_env.get(name)
                self._builtin_cache[name] = val
            except NameError:
                self._builtin_cache[name] = None

    # ----- 顶层接口 -----
    
    def interpret(self, node: ASTNode) -> Optional[LightValue]:
        """解释执行任意 AST 节点"""
        if isinstance(node, Module):
            return self._interpret_module(node)
        return self._execute(node)
    
    def interpret_module(self, module: Module, module_name: str = None) -> Optional[LightValue]:
        """解释执行模块"""
        return self._interpret_module(module, module_name=module_name)
    
    def _interpret_module(self, module: Module, module_name: str = None) -> Optional[LightValue]:
        # 记录本模块为已处理（防止循环导入时重复执行）
        if module_name:
            self._imported_modules.add(module_name)

        # 先处理导入（导入的段落优先注册到环境）
        for imp in module.imports:
            self._exec_import(imp)

        # 再注册当前模块的所有段落定义
        for seg in module.segments:
            func = LightFunction(seg, self.env)
            self.env.define(seg.name, LightValue(func, '段'))

        # 注册类定义
        for cls in module.classes:
            class_obj = LightClass(cls, self.env)
            self.env.define(cls.name, LightValue(class_obj, '类'))

        # 注册接口定义
        for iface in module.interfaces:
            interface_obj = LightInterface(iface)
            self.env.define(iface.name, LightValue(interface_obj, '接口'))

        # 然后顺序执行顶层语句
        result = None
        for stmt in module.statements:
            try:
                result = self._execute(stmt)
            except ReturnSignal as rs:
                result = rs.value
                break
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result
    
    def reset(self):
        """重置解释器状态"""
        self.global_env = Environment(name="全局")
        self.env = self.global_env
        self.output_lines = []
        self._break_encountered = False
        self._register_builtins()
        self.module_resolver.clear_cache()
        self.current_filepath = None
        self._imported_modules.clear()
    
    def get_output(self) -> str:
        """获取所有输出"""
        return '\n'.join(self.output_lines)
    
    # ----- 表达式求值 -----
    
    # 性能优化：使用类级别的方法映射表
    _EVAL_METHODS = {
        NumberLiteral: '_eval_number',
        StringLiteral: '_eval_string',
        BooleanLiteral: '_eval_boolean',
        NullLiteral: '_eval_null',
        Identifier: '_eval_identifier',
        BinaryOp: '_eval_binary_op',
        UnaryOp: '_eval_unary_op',
        ListLiteral: '_eval_list_literal',
        DictLiteral: '_eval_dict_literal',
        IndexAccess: '_eval_index_access',
        PropertyAccess: '_eval_property_access',
        FunctionCall: '_eval_function_call',
        PipeExpression: '_eval_pipe',
        NewExpression: '_eval_new_expression',
        SelfReference: '_eval_self_reference',
        AwaitExpression: '_eval_await',
    }

    def _eval(self, node: ASTNode) -> LightValue:
        """求值表达式 - 优化版使用字典分发"""
        node_type = type(node)
        method_name = self._EVAL_METHODS.get(node_type)
        if method_name:
            return getattr(self, method_name)(node)
        
        # 兜底处理（使用 isinstance 作为备用）
        if isinstance(node, NumberLiteral):
            return LightValue(node.value, '数')
        if isinstance(node, StringLiteral):
            return LightValue(node.value, '串')
        if isinstance(node, BooleanLiteral):
            return LightValue(node.value, '布尔')
        if isinstance(node, NullLiteral):
            return LightValue(None, '空')
        if isinstance(node, Identifier):
            return self.env.get(node.name)
        if isinstance(node, StringInterpolation):
            parts = []
            for part in node.parts:
                if isinstance(part, str):
                    parts.append(part)
                else:
                    val = self._eval(part)
                    parts.append(str(val.value))
            return LightValue(''.join(parts), '串')
        
        raise RuntimeError(f"不支持的表达式类型: {type(node).__name__}")
    
    # 优化：独立的字面量求值方法（减少分支判断）
    def _eval_number(self, node: NumberLiteral) -> LightValue:
        return LightValue(node.value, '数')
    
    def _eval_string(self, node: StringLiteral) -> LightValue:
        return LightValue(node.value, '串')
    
    def _eval_boolean(self, node: BooleanLiteral) -> LightValue:
        return LightValue(node.value, '布尔')
    
    def _eval_null(self, node: NullLiteral) -> LightValue:
        return LightValue(None, '空')
    
    def _eval_identifier(self, node: Identifier) -> LightValue:
        return self.env.get(node.name)
    
    def _eval_list_literal(self, node: ListLiteral) -> LightValue:
        """求值列表字面量"""
        elements = [self._eval(e) for e in node.elements]
        return LightValue(elements, '列')
    
    def _eval_dict_literal(self, node: DictLiteral) -> LightValue:
        """求值典字面量"""
        result = {}
        for entry in node.entries:
            key_val = self._eval(entry.key)
            val_val = self._eval(entry.value)
            # 键必须是可哈希的：串、数、布尔
            if key_val.type_name in ('串', '数', '布尔'):
                result[key_val.value] = val_val
            else:
                raise RuntimeError(f"典键不支持类型: '{key_val.type_name}'")
        return LightValue(result, '典')
    
    def _eval_index_access(self, node: IndexAccess) -> LightValue:
        """求值索引访问：对象[索引]"""
        obj = self._eval(node.obj)
        idx = self._eval(node.index)
        
        if obj.type_name == '典':
            key = idx.value
            if key not in obj.value:
                raise RuntimeError(f"典中不存在键: '{key}'")
            return obj.value[key]
        
        if obj.type_name == '串':
            # 字符串索引
            s = obj.value
            i = self._to_number(idx)
            if not isinstance(i, int):
                i = int(i)
            if i < 0 or i >= len(s):
                raise RuntimeError(f"字符串索引越界: {i}, 长度: {len(s)}")
            return LightValue(s[i], '串')
        
        if obj.type_name == '列':
            lst = obj.value
            i = self._to_number(idx)
            if not isinstance(i, int):
                i = int(i)
            if i < 0 or i >= len(lst):
                raise RuntimeError(f"列表索引越界: {i}, 长度: {len(lst)}")
            return lst[i]
        
        raise RuntimeError(f"不支持索引访问的类型: '{obj.type_name}'")
    
    def _eval_property_access(self, node: PropertyAccess) -> LightValue:
        """求值属性访问：对象之属性"""
        obj = self._eval(node.obj)
        prop = node.property_name
        
        if obj.type_name == '典':
            if prop == '长度':
                return LightValue(len(obj.value), '数')
            if prop == '键列':
                return LightValue([LightValue(k, '串') if isinstance(k, str) else LightValue(k) for k in obj.value.keys()], '列')
            if prop == '值列':
                return LightValue(list(obj.value.values()), '列')
        
        if obj.type_name == '列':
            if prop == '长度':
                return LightValue(len(obj.value), '数')
        
        if obj.type_name == '串':
            if prop == '长度':
                return LightValue(len(obj.value), '数')
        
        # 对象实例的属性访问
        if obj.type_name == '实例':
            instance = obj.value
            if isinstance(instance, LightInstance):
                # 先检查字段
                try:
                    return instance.get_field(prop)
                except RuntimeError:
                    pass
                # 再检查方法
                method = instance.get_method(prop)
                if method is not None:
                    # 返回一个包装的方法对象，供后续调用
                    return LightValue(LightBoundMethod(instance, method), '方法')
        
        # 字典/数据类型的属性访问
        if isinstance(obj.value, dict):
            if prop in obj.value:
                return obj.value[prop]
        
        raise RuntimeError(f"'{obj.type_name}' 没有属性 '{prop}'")
    
    def _eval_function_call(self, node: FunctionCall) -> LightValue:
        """求值函数/段落调用 - 优化版"""
        # 获取函数名
        if isinstance(node.name, PropertyAccess):
            # 方法调用：对象之方法()
            # 先求值属性访问得到方法对象
            func_val = self._eval_property_access(node.name)
            args = [self._eval(a) for a in node.arguments]
            
            # 如果是绑定方法，直接调用
            if func_val.type_name == '方法':
                bound_method = func_val.value
                if isinstance(bound_method, LightBoundMethod):
                    return self._call_method(bound_method, args)
            
            # 否则当作普通函数调用
            if isinstance(func_val.value, LightFunction):
                return self._call_function(func_val.value, args)
            
            raise RuntimeError(f"'{func_val.type_name}' 不是可调用的")
        
        if isinstance(node.name, Identifier):
            func_name = node.name.name
        elif isinstance(node.name, SegmentName):
            func_name = node.name.name
        else:
            raise RuntimeError(f"不支持的函数名类型: {type(node.name).__name__}")
        
        # 求值参数
        args = [self._eval(a) for a in node.arguments]
        
        # 优化：首先检查内置函数缓存
        cached = self._builtin_cache.get(func_name)
        if cached is not None:
            func_val = cached
            if isinstance(func_val.value, LightBuiltinFunction):
                builtin = func_val.value
                if len(args) < builtin.min_args:
                    raise RuntimeError(f"内置函数 '{func_name}' 需要至少 {builtin.min_args} 个参数")
                if builtin.max_args is not None and len(args) > builtin.max_args:
                    raise RuntimeError(f"内置函数 '{func_name}' 最多接受 {builtin.max_args} 个参数")
                return builtin.func(args)
        
        # 在环境中查找函数
        func_val = self.env.get(func_name)
        
        # 内置函数
        if isinstance(func_val.value, LightBuiltinFunction):
            builtin = func_val.value
            if len(args) < builtin.min_args:
                raise RuntimeError(f"内置函数 '{func_name}' 需要至少 {builtin.min_args} 个参数")
            if builtin.max_args is not None and len(args) > builtin.max_args:
                raise RuntimeError(f"内置函数 '{func_name}' 最多接受 {builtin.max_args} 个参数")
            return builtin.func(args)
        
        # 绑定方法调用
        if func_val.type_name == '方法':
            bound_method = func_val.value
            if isinstance(bound_method, LightBoundMethod):
                return self._call_method(bound_method, args)
        
        if func_val.type_name != '段':
            raise RuntimeError(f"'{func_name}' 不是段落 (类型: {func_val.type_name})")
        
        func = func_val.value
        if not isinstance(func, LightFunction):
            raise RuntimeError(f"'{func_name}' 不是可调用的段落")
        
        return self._call_function(func, args)
    
    def _eval_new_expression(self, node: NewExpression) -> LightValue:
        """求值类实例化表达式（新类名()）"""
        class_name = node.class_name
        
        # 在环境中查找类
        class_val = self.env.get(class_name)
        if class_val.type_name != '类':
            raise RuntimeError(f"'{class_name}' 不是类（类型: {class_val.type_name}）")
        
        cls = class_val.value
        if not isinstance(cls, LightClass):
            raise RuntimeError(f"'{class_name}' 不是有效的类定义")
        
        # 求值构造函数参数
        args = [self._eval(a) for a in node.arguments]
        
        # 创建实例
        instance = cls.new_instance(args)
        return LightValue(instance, '实例')

    def _eval_self_reference(self, node: SelfReference) -> LightValue:
        """求值 self 引用（己）"""
        return self.env.get('自我')

    def _eval_await(self, node: AwaitExpression) -> LightValue:
        """求值等待表达式

        在同步解释器中，直接求值内部表达式。
        如果表达式返回协程/coroutine，则运行它直到完成。
        """
        result = self._eval(node.expression)
        # 如果结果是协程（异步函数调用返回），执行它
        if hasattr(result.value, '__await__') or hasattr(result.value, '__aenter__'):
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    result = LightValue(loop.run_until_complete(result.value), '数')
                finally:
                    loop.close()
            except (ImportError, RuntimeError, TypeError):
                pass  # 同步模式下直接返回
        return result

    def _call_method(self, bound_method: LightBoundMethod, args: List[LightValue]) -> LightValue:
        """调用绑定到实例的方法"""
        method = bound_method.method
        instance = bound_method.instance
        
        # 创建方法执行环境
        call_env = instance.cls.closure.create_child(f"方法({method.name})")
        
        # 绑定参数
        param_names = [p.name for p in method.parameters]
        for i, name in enumerate(param_names):
            if i < len(args):
                call_env.define(name, args[i])
            else:
                call_env.define(name, LightValue(None, '空'))
        
        # 设置 self 引用
        call_env.define('自我', LightValue(instance, '实例'))
        
        # 将实例字段添加到调用环境中
        for field_name, field_value in instance.fields.items():
            call_env.define(field_name, field_value)
        
        # 执行方法体
        old_env = self.env
        self.env = call_env
        try:
            result = LightValue(None, '空')
            for stmt in method.body:
                try:
                    self._execute(stmt)
                except ReturnSignal as rs:
                    result = rs.value
                    break
            return result
        finally:
            # 更新实例字段（方法中可能修改了字段值）
            for field_name in instance.fields.keys():
                if call_env.has(field_name):
                    instance.fields[field_name] = call_env.get(field_name)
            # 执行推迟栈
            self._run_defer_stack()
            self.env = old_env
    
    def _call_function(self, func: LightFunction, args: List[LightValue]) -> LightValue:
        """调用段落函数 - 优化版"""
        seg = func.definition
        
        # 创建新的作用域（闭包）
        call_env = func.closure.create_child(f"段({seg.name})")
        
        # 优化：使用局部变量减少属性查找
        param_names = [p.name for p in seg.parameters]
        seg_body = seg.body
        
        # 绑定参数
        args_len = len(args)
        for i, name in enumerate(param_names):
            if i < args_len:
                call_env.define(name, args[i])
            else:
                # 使用默认值
                param = seg.parameters[i]
                if param.default_value is not None:
                    # 默认值需要在定义时的环境中求值
                    old_env = self.env
                    self.env = func.closure
                    try:
                        default_val = self._eval(param.default_value)
                        call_env.define(name, default_val)
                    finally:
                        self.env = old_env
                else:
                    call_env.define(name, LightValue(None, '空'))
        
        # 执行段落体 - 优化：减少 try-finally 开销
        old_env = self.env
        self.env = call_env
        try:
            result = LightValue(None, '空')
            for stmt in seg_body:
                try:
                    self._execute(stmt)
                except ReturnSignal as rs:
                    result = rs.value or LightValue(None, '空')
                    break
            return result
        finally:
            # 执行推迟栈（后进先出）
            self._run_defer_stack()
            self.env = old_env

    def call_function(self, func_val: LightValue, args: List[LightValue]) -> Optional[LightValue]:
        """公共接口：调用函数值 - 用于自举测试"""
        if isinstance(func_val.value, LightFunction):
            return self._call_function(func_val.value, args)
        elif isinstance(func_val.value, LightBuiltinFunction):
            return func_val.value.func(args)
        else:
            raise RuntimeError(f"无法调用非函数类型: {func_val.type_name}")
    
    def _eval_pipe(self, node: PipeExpression) -> LightValue:
        """求值管道表达式"""
        current = self._eval(node.expressions[0])
        for i in range(1, len(node.expressions)):
            current = self._eval(node.expressions[i])
        return current
    
    # ----- 语句执行 -----
    
    def _execute(self, node: ASTNode):
        """执行语句"""
        if isinstance(node, VariableDeclaration):
            return self._exec_var_decl(node)
        if isinstance(node, Assignment):
            return self._exec_assignment(node)
        if isinstance(node, CompoundAssignment):
            return self._exec_compound_assignment(node)
        if isinstance(node, IfStatement):
            return self._exec_if(node)
        if isinstance(node, WhileStatement):
            return self._exec_while(node)
        if isinstance(node, ForeachStatement):
            return self._exec_foreach(node)
        if isinstance(node, PrintStatement):
            return self._exec_print(node)
        if isinstance(node, BreakStatement):
            raise BreakSignal()
        if isinstance(node, ContinueStatement):
            raise ContinueSignal()
        if isinstance(node, ReturnStatement):
            val = self._eval(node.value) if node.value else LightValue(None, '空')
            raise ReturnSignal(val)
        if isinstance(node, ExpressionStatement):
            return self._eval(node.expression)
        if isinstance(node, TryStatement):
            return self._exec_try(node)
        if isinstance(node, ThrowStatement):
            val = self._eval(node.value)
            raise LightError(str(val), val)
        if isinstance(node, ImportStatement):
            return self._exec_import(node)
        if isinstance(node, ExportStatement):
            # 导出语句在模块加载时已被处理，此处忽略
            return None
        # 异步/并发语句
        if isinstance(node, DeferStatement):
            return self._exec_defer(node)
        if isinstance(node, AsyncScope):
            return self._exec_async_scope(node)
        # 跳过类型定义等
        return None
    
    def _exec_var_decl(self, node: VariableDeclaration):
        """执行变量声明"""
        value = LightValue(None, '空')
        if node.value is not None:
            value = self._eval(node.value)
        self.env.define(node.name, value)
    
    def _exec_assignment(self, node: Assignment):
        """执行赋值"""
        target = node.target
        value = self._eval(node.value)
        
        if isinstance(target, Identifier):
            self.env.set(target.name, value)
        elif isinstance(target, PropertyAccess):
            # 属性赋值
            obj = self._eval(target.obj)
            if obj.type_name == '列' or obj.type_name == '串':
                raise RuntimeError(f"不能给 '{obj.type_name}' 类型赋值属性")
            
            # 对象实例的字段赋值
            if obj.type_name == '实例':
                instance = obj.value
                if isinstance(instance, LightInstance):
                    instance.set_field(target.property_name, value)
                    return
            
            if isinstance(obj.value, dict):
                obj.value[target.property_name] = value
            else:
                raise RuntimeError(f"不支持属性赋值的类型: '{obj.type_name}'")
        elif isinstance(target, IndexAccess):
            # 索引赋值
            obj = self._eval(target.obj)
            idx = self._eval(target.index)
            if obj.type_name == '典':
                obj.value[idx.value] = value
            elif obj.type_name == '列':
                i = self._to_number(idx)
                if not isinstance(i, int):
                    i = int(i)
                if i < 0 or i >= len(obj.value):
                    raise RuntimeError(f"列表索引越界: {i}")
                obj.value[i] = value
            else:
                raise RuntimeError(f"不支持索引赋值的类型: '{obj.type_name}'")
        else:
            raise RuntimeError(f"不支持的赋值目标: {type(target).__name__}")
    
    def _exec_compound_assignment(self, node: CompoundAssignment):
        """执行复合赋值：甲 加上 1 → 甲 += 1"""
        # 获取当前变量值
        current = self.env.get(node.target)
        if current is None:
            raise RuntimeError(f"变量 '{node.target}' 未定义，无法进行复合赋值")
        
        # 获取右值
        new_val = self._eval(node.value)
        
        # 运算符映射
        import operator as py_op
        op_map = {
            '加': py_op.add,
            '减': py_op.sub,
            '乘': py_op.mul,
            '除': py_op.truediv,
            '模': py_op.mod,
            '幂': py_op.pow,
        }
        
        op_func = op_map.get(node.operator)
        if op_func is None:
            raise RuntimeError(f"不支持的复合赋值运算符: '{node.operator}'")
        
        # 计算结果
        py_value = current.value
        py_new = new_val.value
        result = op_func(py_value, py_new)
        
        # 推断结果类型
        if isinstance(result, bool):
            result_type = '布尔'
        elif isinstance(result, int):
            result_type = '整数'
        elif isinstance(result, float):
            result_type = '浮数'
        else:
            result_type = new_val.type_name
        
        self.env.set(node.target, LightValue(result, result_type))
    
    def _exec_if(self, node: IfStatement):
        """执行条件语句"""
        # 判断条件
        cond = self._eval(node.condition)
        
        if cond.is_truthy():
            self._execute_block(node.then_body)
            return
        
        # 检查 elseif
        for i, elseif_cond in enumerate(node.elseif_conditions):
            if self._eval(elseif_cond).is_truthy():
                self._execute_block(node.elseif_bodies[i])
                return
        
        # else 分支
        if node.else_body is not None:
            self._execute_block(node.else_body)
    
    def _exec_while(self, node: WhileStatement):
        """执行当循环"""
        while self._eval(node.condition).is_truthy():
            try:
                self._execute_block(node.body)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
    
    def _exec_foreach(self, node: ForeachStatement):
        """执行遍历循环"""
        iterable = self._eval(node.iterable)
        
        items = None
        if iterable.type_name == '列':
            items = iterable.value
        elif iterable.type_name == '典':
            items = [LightValue(k, '串') if isinstance(k, str) else LightValue(k) for k in iterable.value.keys()]
        else:
            raise RuntimeError(f"遍历目标必须是列表或典，实际类型: '{iterable.type_name}'")
        for item in items:
            self.env.define(node.variable, item)
            try:
                self._execute_block(node.body)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
    
    def _exec_print(self, node: PrintStatement):
        """执行打印语句"""
        value = self._eval(node.value)
        text = str(value)
        self.output_lines.append(text)
        # 同时输出到控制台
        print(text)
    
    def _exec_try(self, node: TryStatement):
        """执行异常捕获"""
        try:
            self._execute_block(node.try_body)
        except LightError as e:
            catch_var = node.catch_var
            self.env.define(catch_var, e.value)
            self._execute_block(node.catch_body)

    def _exec_defer(self, node: DeferStatement):
        """执行推迟语句

        将推迟的语句保存到当前环境的延迟执行栈中，
        在作用域/段落退出时执行。
        """
        if not hasattr(self.env, '_defer_stack'):
            self.env._defer_stack = []
        # 将推迟语句体压栈（后进先出）
        self.env._defer_stack.append(node.body)

    def _run_defer_stack(self):
        """运行当前环境的推迟栈（后进先出）"""
        if hasattr(self.env, '_defer_stack') and self.env._defer_stack:
            while self.env._defer_stack:
                deferred_body = self.env._defer_stack.pop()
                try:
                    self._execute_block(deferred_body)
                except Exception as e:
                    # 推迟语句执行出错，打印错误但继续执行其余推迟
                    print(f"[推迟执行错误] {e}", file=sys.stderr)

    def _exec_async_scope(self, node: AsyncScope):
        """执行并行作用域（结构化并发）

        在同步解释器中，顺序执行所有任务。
        如果启用了 asyncio，使用 asyncio.gather 并发执行。
        """
        tasks = node.tasks
        if not tasks:
            return LightValue(None, '空')

        try:
            import asyncio

            async def run_task(task_stmt):
                """执行单个异步任务"""
                if isinstance(task_stmt, ExpressionStatement) and isinstance(task_stmt.expression, AwaitExpression):
                    val = self._eval(task_stmt.expression)
                    return val
                return self._execute(task_stmt)

            async def run_all():
                results = await asyncio.gather(*[run_task(t) for t in tasks])
                return results

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(run_all())
            finally:
                loop.close()
        except (ImportError, RuntimeError, TypeError):
            # 没有 asyncio 时顺序执行
            for task_stmt in tasks:
                self._execute(task_stmt)

        return LightValue(None, '空')

    def _exec_import(self, node: ImportStatement):
        """执行导入语句"""
        # ----- 直接导入（无模块名）：在当前环境中查找已注册的符号 -----
        if not node.module:
            for name in node.names:
                if not self.env.has(name):
                    raise RuntimeError(
                        f"直接导入失败: 未找到符号 '{name}'"
                    )
            return

        # ----- 从模块导入 -----
        # 已处理过的模块直接跳过
        if node.module in self._imported_modules:
            return

        # 计算 from_dir
        from_dir = None
        if self.current_filepath:
            from_dir = os.path.dirname(os.path.abspath(self.current_filepath))

        # 加载模块 AST
        try:
            module_ast, filepath = self.module_resolver.load_module(node.module, from_dir)
        except ModuleError as e:
            raise RuntimeError(f"导入失败: {e}")

        # ----- 递归处理被导入模块自身的依赖 -----
        self._imported_modules.add(node.module)

        old_filepath = self.current_filepath
        self.current_filepath = filepath
        try:
            for sub_import in module_ast.imports:
                self._exec_import(sub_import)

            # 将被导入模块的所有段落和类注册到全局环境（确保内部交叉调用可用）
            for seg in module_ast.segments:
                if not self.env.has(seg.name):
                    func = LightFunction(seg, self.global_env)
                    self.env.define(seg.name, LightValue(func, '段'))
            
            # 注册类定义
            for cls in module_ast.classes:
                if not self.env.has(cls.name):
                    class_obj = LightClass(cls, self.global_env)
                    self.env.define(cls.name, LightValue(class_obj, '类'))

            # 执行被导入模块的顶层语句
            old_env = self.env
            self.env = self.global_env
            try:
                for stmt in module_ast.statements:
                    try:
                        self._execute(stmt)
                    except (ReturnSignal, BreakSignal, ContinueSignal):
                        pass
            finally:
                self.env = old_env
        finally:
            self.current_filepath = old_filepath

        # ----- 验证并注册请求的导出符号 -----
        export_names = {exp.name for exp in module_ast.exports}
        # 构建符号映射（包括段落和类）
        symbols_map = {}
        for seg in module_ast.segments:
            symbols_map[seg.name] = ('segment', seg)
        for cls in module_ast.classes:
            symbols_map[cls.name] = ('class', cls)

        # 如果指定了要导入的名称，验证其可导出性
        if node.names:
            for name in node.names:
                if name not in symbols_map:
                    raise RuntimeError(
                        f"模块 '{node.module}' 中未找到导出符号 '{name}'"
                    )
                if export_names and name not in export_names:
                    raise RuntimeError(
                        f"符号 '{name}' 未在模块 '{node.module}' 中导出"
                    )
                if not self.env.has(name):
                    symbol_type, symbol_def = symbols_map[name]
                    if symbol_type == 'segment':
                        func = LightFunction(symbol_def, self.global_env)
                        self.env.define(name, LightValue(func, '段'))
                    elif symbol_type == 'class':
                        class_obj = LightClass(symbol_def, self.global_env)
                        self.env.define(name, LightValue(class_obj, '类'))

    def _execute_block(self, statements: List[ASTNode]):
        """执行语句块"""
        for stmt in statements:
            self._execute(stmt)
    
    # ----- 辅助方法 -----
    
    def _to_number(self, val: LightValue) -> Union[int, float]:
        """转换为数字 - 优化版"""
        # 优化：直接访问 value 属性减少开销
        v = val.value
        type_name = val.type_name
        
        if type_name == '数':
            return v
        if v is None:
            return 0
        if isinstance(v, bool):
            return 1 if v else 0
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            try:
                if '.' in v:
                    return float(v)
                return int(v)
            except (ValueError, TypeError):
                raise RuntimeError(f"无法转换为数字: '{v}'")
        raise RuntimeError(f"无法转换为数字: 类型 '{type_name}'")
    
    def _equals(self, a: LightValue, b: LightValue) -> bool:
        """比较两个值是否相等 - 优化版"""
        # 优化：直接访问 type_name 减少属性查找
        a_type = a.type_name
        b_type = b.type_name
        
        if a_type != b_type:
            return False
        if a_type == '空':
            return True
        return a.value == b.value