# 编译器 API 参考

> 自动生成 - 请勿手动编辑

---

## 模块: arity_parser

**模块说明**: 光明（Light）编程语言 - 元数驱动解析器

实现决策28：元数驱动解析
- 动词声明参数数量，自动收集参数
- 支持无括号函数调用
- 阻断符机制

示例：
  打印甲。          → 打印(甲)
  加1乘2 3。        → 加(1, 乘(2, 3))
  列1 2 3 4 5。     → 列(1, 2, 3, 4, 5)

### 类 `ArityParser`

元数驱动解析器

### 函数 `parse_verb_call(self, verb: str)`

解析动词调用（元数驱动）
        
        Args:
            verb: 动词名称
            
        Returns:
            (AST节点, 消耗的token数)

### 函数 `apply_arity_parsing(module: Module)`

对模块应用元数驱动解析
    
    这是后处理步骤，识别并转换动词调用

---

## 模块: ast_nodes

**模块说明**: 光明（Light）编程语言 AST 节点定义

与 src/ast_nodes.py 保持兼容的 AST 节点结构
供 ANTLR 解析器生成 AST 使用

### 类 `ASTNode`

AST 节点基类

### 类 `NumberLiteral`

### 类 `StringLiteral`

### 类 `BooleanLiteral`

### 类 `NullLiteral`

### 类 `SelfReference`

### 类 `Identifier`

### 类 `SegmentName`

### 类 `ModuleName`

### 类 `BinaryOp`

### 类 `UnaryOp`

### 类 `FunctionCall`

### 类 `PipeExpression`

### 类 `PropertyAccess`

### 类 `IndexAccess`

### 类 `ListLiteral`

### 类 `DictEntry`

### 类 `DictLiteral`

### 类 `NewExpression`

### 类 `ConditionalExpression`

### 类 `StringInterpolation`

### 类 `ListComprehension`

### 类 `LambdaExpression`

### 类 `MatchStatement`

### 类 `MatchCase`

### 类 `MatchPattern`

### 类 `DictComprehension`

### 类 `DecoratorDefinition`

### 类 `DestructuringAssignment`

### 类 `WithStatement`

### 类 `VariableDeclaration`

### 类 `Assignment`

### 类 `CompoundAssignment`

### 类 `IfStatement`

### 类 `ForeachStatement`

### 类 `WhileStatement`

### 类 `BreakStatement`

### 类 `ContinueStatement`

### 类 `ReturnStatement`

### 类 `CatchClause`

### 类 `TryStatement`

### 类 `ThrowStatement`

### 类 `PrintStatement`

### 类 `ExpressionStatement`

### 类 `EmbedBlock`

### 类 `Parameter`

### 类 `AwaitExpression`

### 类 `DeferStatement`

### 类 `AsyncScope`

### 类 `SegmentDefinition`

### 类 `DataTypeField`

### 类 `AttributeDeclaration`

### 类 `DataTypeDefinition`

### 类 `ErrorTypeDefinition`

### 类 `MethodDefinition`

### 类 `ConstructorDefinition`

### 类 `ClassDefinition`

### 类 `InterfaceMethod`

### 类 `InterfaceProperty`

### 类 `InterfaceDefinition`

### 类 `GenericType`

### 类 `GenericParameterDecl`

### 类 `EnumVariant`

### 类 `EnumDefinition`

### 类 `TraitMethodSignature`

### 类 `TraitDefinition`

### 类 `TraitImplementation`

### 类 `UnwrapExpression`

### 类 `OptionalType`

### 类 `TypeAlias`

### 类 `ImportStatement`

### 类 `ExportStatement`

### 类 `FFILoadLibraryStatement`

### 类 `FFIFunctionDeclaration`

### 类 `FFIStructDefinition`

### 类 `FFICallbackDefinition`

### 类 `FFIPointerType`

### 类 `FFIArrayType`

### 类 `FFIAddressOf`

### 类 `FFIDereference`

### 类 `FFIPointerOffset`

### 类 `FFISetPointerValue`

### 类 `FFIAllocMemory`

### 类 `FFIFreeMemory`

### 类 `FFICreateArray`

### 类 `FFISetArrayElement`

### 类 `FFIGetLastError`

### 类 `FFIGetErrno`

### 类 `FFISetErrno`

### 类 `FFITryCatch`

### 类 `FFIEnumDef`

### 类 `FFIUnionDef`

### 类 `FFICreateCallback`

### 类 `FFIVarArgsDecl`

### 类 `FFIStructByValue`

### 类 `FFILibraryPath`

### 类 `FFITypedefDef`

### 类 `FFIBitfieldDef`

### 类 `FFIFuncPtrDef`

### 类 `FFIDebugConfig`

### 类 `FFIPreprocessorDef`

### 类 `Module`

### 函数 `ast_to_dict(node: ASTNode)`

将 AST 节点转换为字典（用于序列化）

---

## 模块: ast_nodes_v3

**模块说明**: 光明（Light）编程语言 - Python 后端 AST 节点定义

从 light_parser_v3.py 提取，作为独立模块供代码生成器/语义分析器使用。

### 类 `ASTNode`

AST 节点基类

### 类 `Module`

### 类 `ParameterList`

### 类 `VarDecl`

### 类 `IfStmt`

### 类 `ForeachStmt`

### 类 `WhileStmt`

### 类 `Paragraph`

### 类 `ReturnStmt`

### 类 `BinaryOp`

### 类 `UnaryOp`

### 类 `NumberLiteral`

### 类 `StringLiteral`

### 类 `Identifier`

### 类 `ParagraphCall`

### 类 `SliceExpr`

### 类 `IndexAccess`

### 类 `AssignmentExpression`

### 类 `BreakStmt`

### 类 `ContinueStmt`

### 类 `PassStmt`

### 类 `TypeCheckToggleStmt`

### 类 `TryStmt`

### 类 `CatchClause`

### 类 `ThrowStmt`

### 类 `Pipeline`

### 类 `ImportStmt`

### 类 `ExportStmt`

### 类 `Parameter`

### 类 `AttributeDeclaration`

### 类 `MethodDefinition`

### 类 `CompoundAssignment`

### 类 `IndexedAssignment`

### 类 `IndexedCompoundAssignment`

### 类 `Assignment`

### 类 `SelfAssignment`

### 类 `ClassDefinition`

### 类 `ClassInstantiation`

### 类 `ConditionalExpression`

### 类 `MemberAccess`

### 类 `ListLiteral`

### 类 `TupleLiteral`

### 类 `SetLiteral`

### 类 `StringInterpolation`

### 类 `ListComprehension`

### 类 `SetComprehension`

### 类 `LambdaExpression`

### 类 `MatchStmt`

### 类 `MatchCase`

### 类 `MatchPattern`

### 类 `DictComprehension`

### 类 `DecoratorDefinition`

### 类 `MethodSignature`

### 类 `InterfaceDefinition`

### 类 `DestructuringAssignment`

### 类 `WithStmt`

### 类 `DictLiteral`

### 类 `RangeExpr`

### 类 `AwaitExpr`

=============================================================================
异步/并发节点
=============================================================================

### 类 `AsyncScope`

### 类 `FFILoadLibrary`

=============================================================================
C FFI 节点（外部函数接口）
=============================================================================

### 类 `FFIFunctionDecl`

### 类 `FFIStructDef`

### 类 `FFICallbackDef`

### 类 `FFIPointerType`

=============================================================================
C FFI 指针/数组/错误处理节点（第二阶段）
=============================================================================

### 类 `FFIArrayType`

### 类 `FFIAddressOf`

### 类 `FFIDereference`

### 类 `FFIPointerOffset`

### 类 `FFISetPointerValue`

### 类 `FFIAllocMemory`

### 类 `FFIFreeMemory`

### 类 `FFICreateArray`

### 类 `FFISetArrayElement`

### 类 `FFIGetLastError`

### 类 `FFIGetErrno`

### 类 `FFISetErrno`

### 类 `FFITryCatch`

### 类 `FFIEnumDef`

=============================================================================
C FFI 第三阶段：回调/结构体传值/枚举/联合体/变长参数
=============================================================================

### 类 `FFIUnionDef`

### 类 `FFICreateCallback`

### 类 `FFIVarArgsDecl`

### 类 `FFIStructByValue`

### 类 `FFILibraryPath`

### 类 `FFITypedefDef`

=============================================================================
C FFI 第四阶段：typedef/位域/函数指针/回调生命周期/调试
=============================================================================

### 类 `FFIBitfieldDef`

### 类 `FFIFuncPtrDef`

### 类 `FFIDebugConfig`

### 类 `FFIPreprocessorDef`

### 类 `KeywordArg`

关键字参数：name=value（用于函数/方法调用中的关键字参数）

### 类 `EmbedBlock`

嵌入块语句：嵌入 Python/C: ... 结束嵌入
    
    将外部语言代码作为"外语引用"嵌入光明代码中，
    类似中文文本中嵌入数学公式或英文片段。

---

## 模块: ast_unified

**模块说明**: 光明（Light）编程语言 - 统一AST系统（用于机器码生成）

这是为原生编译器设计的统一AST，包含：
1. 完整的类型系统支持
2. 符号表和作用域信息
3. 代码生成所需的额外元数据
4. 跨平台代码生成支持

### 类 `Type`

类型基类

### 类 `PrimitiveType`

基本类型

### 类 `PointerType`

指针类型

### 类 `ArrayType`

数组类型

### 类 `StructType`

结构体类型

### 类 `FunctionType`

函数类型

### 类 `ASTNode`

AST节点基类

### 类 `NumberLiteral`

数字字面量

### 类 `StringLiteral`

字符串字面量

### 类 `BooleanLiteral`

布尔字面量

### 类 `CharLiteral`

字符字面量

### 类 `Identifier`

标识符

### 类 `Symbol`

符号表条目

### 类 `BinaryOp`

二元运算

### 类 `UnaryOp`

一元运算

### 类 `FunctionCall`

函数调用

### 类 `ArrayAccess`

数组访问

### 类 `StructAccess`

结构体成员访问

### 类 `CastExpression`

类型转换

### 类 `Block`

代码块

### 类 `VariableDeclaration`

变量声明

### 类 `Assignment`

赋值语句

### 类 `IfStatement`

条件语句

### 类 `WhileStatement`

while循环

### 类 `ForStatement`

for循环

### 类 `BreakStatement`

break语句

### 类 `ContinueStatement`

continue语句

### 类 `ReturnStatement`

return语句

### 类 `ExpressionStatement`

表达式语句

### 类 `PrintStatement`

打印语句

### 类 `Parameter`

函数参数

### 类 `FunctionDefinition`

函数定义

### 类 `StructDefinition`

结构体定义

### 类 `GlobalVariable`

全局变量

### 类 `Module`

模块（顶层节点）

### 函数 `add_scope(self)`

创建新作用域并返回ID

### 函数 `add_symbol(self, scope_id: int, name: str, symbol: Symbol)`

在指定作用域添加符号

### 函数 `lookup_symbol(self, scope_id: int, name: str)`

在作用域链中查找符号

### 类 `ASTVisitor`

AST访问者基类

### 函数 `visit(self, node: ASTNode)`

调度访问方法

### 函数 `visit_default(self, node: ASTNode)`

默认访问方法

### 函数 `visit_NumberLiteral(self, node: NumberLiteral)`

### 函数 `visit_StringLiteral(self, node: StringLiteral)`

### 函数 `visit_BooleanLiteral(self, node: BooleanLiteral)`

### 函数 `visit_CharLiteral(self, node: CharLiteral)`

### 函数 `visit_Identifier(self, node: Identifier)`

### 函数 `visit_BinaryOp(self, node: BinaryOp)`

### 函数 `visit_UnaryOp(self, node: UnaryOp)`

### 函数 `visit_FunctionCall(self, node: FunctionCall)`

### 函数 `visit_ArrayAccess(self, node: ArrayAccess)`

### 函数 `visit_StructAccess(self, node: StructAccess)`

### 函数 `visit_CastExpression(self, node: CastExpression)`

### 函数 `visit_Block(self, node: Block)`

### 函数 `visit_VariableDeclaration(self, node: VariableDeclaration)`

### 函数 `visit_Assignment(self, node: Assignment)`

### 函数 `visit_IfStatement(self, node: IfStatement)`

### 函数 `visit_WhileStatement(self, node: WhileStatement)`

### 函数 `visit_ForStatement(self, node: ForStatement)`

### 函数 `visit_BreakStatement(self, node: BreakStatement)`

### 函数 `visit_ContinueStatement(self, node: ContinueStatement)`

### 函数 `visit_ReturnStatement(self, node: ReturnStatement)`

### 函数 `visit_ExpressionStatement(self, node: ExpressionStatement)`

### 函数 `visit_PrintStatement(self, node: PrintStatement)`

### 函数 `visit_FunctionDefinition(self, node: FunctionDefinition)`

### 函数 `visit_StructDefinition(self, node: StructDefinition)`

### 函数 `visit_GlobalVariable(self, node: GlobalVariable)`

### 函数 `visit_Module(self, node: Module)`

---

## 模块: code_generator

**模块说明**: 光明（Light）编程语言 - Python代码生成器

将光明AST转换为Python代码

### 类 `CodeGenError`

代码生成错误

### 类 `PythonCodeGenerator`

光明到Python代码生成器

### 函数 `generate(self, module: Module)`

生成Python代码

---

## 模块: code_generator_unified

**模块说明**: 光明（Light）编程语言 - Python代码生成器（统一AST版本）

支持统一AST格式，兼容来自duan_ast和ast_unified的AST节点
集成类型推断系统，正确处理字符串连接和数字加法

### 函数 `is_instance(node, class_name)`

检查节点是否为指定类型（通过名称检查，支持多个模块）

### 函数 `get_attr(node, attr_name, default=None)`

安全获取节点属性

### 类 `UnifiedCodeGenerator`

光明到Python代码生成器（支持统一AST）

### 函数 `generate(self, module)`

生成Python代码

---

## 模块: codegen_x64

**模块说明**: 光明（Light）编程语言 - x86-64代码生成器

将三地址码IR转换为x86-64汇编代码。
支持Linux/macOS (System V AMD64 ABI) 和 Windows (x64 calling convention)。

### 类 `Register`

寄存器

### 类 `Assembler`

汇编器

### 函数 `emit(self, instruction: str, comment: str = "")`

添加汇编指令

### 函数 `emit_label(self, name: str)`

添加标签

### 函数 `emit_section(self, section: str)`

添加段声明

### 函数 `emit_global(self, name: str)`

添加全局符号声明

### 函数 `emit_string(self, label: str, content: str)`

添加字符串常量

### 函数 `emit_align(self, align: int)`

添加对齐指令

### 函数 `emit_int(self, value: int)`

添加整数常量

### 函数 `new_label(self)`

创建新标签

### 函数 `get_code(self)`

获取生成的汇编代码

### 类 `RegisterAllocator`

寄存器分配器

### 函数 `allocate(self, name: str)`

分配寄存器

### 函数 `free(self, name: str)`

释放寄存器

### 函数 `get_register(self, name: str)`

获取变量的寄存器分配

### 类 `X86CodeGenerator`

x86-64代码生成器

### 函数 `generate(self, module: ModuleIR)`

生成汇编代码

### 函数 `generate_function(self, func: FunctionIR)`

生成函数汇编

### 函数 `emit_prologue(self)`

函数序言

### 函数 `emit_epilogue(self)`

函数尾声

### 函数 `generate_block(self, block: BasicBlock)`

生成基本块

### 函数 `generate_instruction(self, instr: Instruction)`

生成单条指令

### 函数 `generate_add(self, instr: Instruction)`

生成加法指令

### 函数 `generate_sub(self, instr: Instruction)`

生成减法指令

### 函数 `generate_mul(self, instr: Instruction)`

生成乘法指令

### 函数 `generate_div(self, instr: Instruction)`

生成除法指令

### 函数 `generate_cmp(self, instr: Instruction, cond: str)`

生成比较指令

### 函数 `generate_store(self, instr: Instruction)`

生成存储指令

### 函数 `generate_load(self, instr: Instruction)`

生成加载指令

### 函数 `generate_load_const(self, instr: Instruction)`

生成加载常量指令

### 函数 `generate_jump(self, instr: Instruction)`

生成跳转指令

### 函数 `generate_jump_if_false(self, instr: Instruction)`

生成条件跳转指令

### 函数 `generate_call(self, instr: Instruction)`

生成函数调用指令

### 函数 `generate_return(self, instr: Instruction)`

生成返回指令

### 函数 `generate_param(self, instr: Instruction)`

生成参数传递指令

### 函数 `emit_move(self, value: IRValue, reg: Register)`

生成移动指令

### 函数 `emit_operand(self, value: IRValue, op: str, dest_reg: Register)`

生成操作数指令

### 函数 `emit_memory_store(self, mem: Memory, reg: Register)`

生成内存存储指令

### 函数 `emit_memory_load(self, mem: Memory, reg: Register)`

生成内存加载指令

### 函数 `allocate_result(self, dest: Optional[IRValue], reg: Register)`

分配结果到目标

### 函数 `get_var_offset(self, name: str)`

获取变量的栈偏移

### 函数 `get_temp_offset(self, name: str)`

获取临时变量的栈偏移

### 函数 `test_code_generator()`

测试代码生成器

---

## 模块: compiler

**模块说明**: 光明（Light）编程语言 - 统一编译器管道

完整链路：  源码 → 词法分析 → 语法解析 → AST 适配 → 类型检查
          (source)  (Lexer)   (LightParser)  (Adapter)  (TypeInferencer)

这是连接前端解析器与后端类型系统的桥梁。

### 类 `AstAdapter`

将 `ast_nodes_v3` 节点转换为 `ast_nodes.py` 节点

    现有 LightParser v3 输出 ast_nodes_v3 的节点，这些节点使用 __slots__
    的普通类设计。而我们的类型系统基于 ast_nodes.py（dataclass 设计）。
    本适配器在两者之间提供无损转换。

### 函数 `convert(self, node)`

将 v3 AST 节点转换为 ast_nodes 格式

### 函数 `convert_module(self, node)`

将 v3 Module 转换为我们的 Module 格式

### 类 `LightCompiler`

光明统一编译器

    使用示例：
        compiler = LightCompiler()
        # 完整流程
        result = compiler.compile('定义甲等于三。')
        # 分步：解析 → 检查
        module = compiler.parse('定义甲等于三。')
        typed = compiler.type_check(module)
        # 查看错误
        if compiler.errors:
            print(compiler.errors)

    跨模块项目级使用：
        compiler = LightCompiler(project_root='/path/to/project')
        result = compiler.compile_project('/path/to/project')

### 函数 `version(self)`

返回光明编译器版本号

### 函数 `preload_stdlib(self)`

预加载标准库模块，确保内置函数在编译时可用

### 函数 `compile(self, source: str, optimize: bool = True)`

完整编译流程。返回字典：

        {
            'source': 源代码,
            'tokens': Token 列表,
            'ast_raw': ast_nodes_v3.Module,
            'ast': ast_nodes.Module,
            'inferencer': TypeInferencer（含类型标注信息）,
            'errors': 错误列表,
        }

### 函数 `compile_project(self, project_root: Optional[str] = None, optimize: bool = True)`

编译整个光明项目（支持多模块。

        流程：
          1. 解析 package.toml，寻找入口模块
          2. 从入口模块出发递归解析所有依赖（ModuleDependencyResolver）
          3. 按拓扑顺序编译每个模块，合并导出符号到全局符号表
          4. 在类型检查阶段将导入模块的符号合并到当前作用域

### 函数 `tokenize(self, source: str)`

词法分析

### 函数 `parse_raw(self, source: str)`

语法解析（返回 v3 AST）

### 函数 `adapt(self, raw_ast)`

将 v3 AST 适配为我们的 ast_nodes.Module

### 函数 `optimize_ast(self, module: ast.Module)`

依次运行所有优化器，返回优化后的模块

### 函数 `type_check(self, module: ast.Module, source: str = '')`

对适配后的 AST 进行类型推断与检查。返回 inferencer 实例。

### 函数 `has_errors(self)`

### 函数 `describe(self, module: ast.Module, indent: int = 0)`

简单的 AST 描述（调试用）

### 函数 `generate_llvm_ir(self, module: ast.Module)`

生成 LLVM IR 代码
        
        使用 antlrparser/llvm_codegen.py 中的 LLVMCodeGen 生成 LLVM IR。
        需要确保 antlrparser 目录在 sys.path 中。

### 函数 `compile_file(file_path: str, use_cache: bool = True)`

编译文件并返回编译结果

    Args:
        file_path: 源文件路径
        use_cache: 是否使用编译缓存，默认为 True

    Returns:
        编译结果字典，与 LightCompiler.compile() 返回格式相同

### 函数 `compile_source(source: str)`

编译源码并返回已完成类型检查的编译器实例

### 函数 `parse_source(source: str)`

仅解析源码，返回适配后的 AST

### 函数 `tokenize_source(source: str)`

仅进行词法分析

### 类 `CompilerQuery`

便捷查询编译器结果的辅助类

### 函数 `infer_variable_type(self, var_name: str)`

查询变量类型

### 函数 `has_type_errors(self)`

---

## 模块: compiler_cache

**模块说明**: 光明编译缓存系统

支持：
- 文件哈希缓存（检测文件是否修改）
- 模块级缓存（缓存单个模块的编译结果）
- 依赖追踪（缓存依赖的模块）
- 缓存清理（TTL / 手动清理）

### 类 `CompilationCache`

编译缓存系统

    基于文件内容和元数据生成缓存键，支持缓存的新鲜度检查、
    过期清理和缓存统计。

    Attributes:
        cache_dir: 缓存目录路径
        _cache: 内存缓存 {cache_key: cached_data}
        _dirty: 脏标记，记录哪些文件的缓存已失效

### 函数 `get_cached(self, file_path: str)`

获取缓存编译结果

        Args:
            file_path: 源文件路径

        Returns:
            缓存的编译结果（IR 字符串），如果没有缓存或缓存已失效则返回 None

### 函数 `set_cached(self, file_path: str, result: str)`

设置缓存

        Args:
            file_path: 源文件路径
            result: 编译结果（IR 字符串）

### 函数 `invalidate(self, file_path: str)`

使缓存失效

        Args:
            file_path: 源文件路径

### 函数 `get_cache_key(self, file_path: str)`

生成缓存键（基于文件路径和内容）

        Args:
            file_path: 源文件路径

        Returns:
            缓存键字符串

### 函数 `is_fresh(self, file_path: str)`

检查缓存是否新鲜

        Args:
            file_path: 源文件路径

        Returns:
            True 表示缓存新鲜有效

### 函数 `clean(self, max_age_hours: int = 24)`

清理过期缓存

        Args:
            max_age_hours: 缓存最大存活时间（小时），默认 24 小时

### 函数 `clear(self)`

清空所有缓存

### 函数 `stats(self)`

获取缓存统计信息

        Returns:
            包含缓存统计信息的字典

---

## 模块: debug_engine

### 类 `StepMode`

单步执行模式

### 类 `Frame`

调用帧

### 类 `DebugEngine`

光明调试引擎
    
    支持：
    - 单步执行（step into/over/out）
    - 断点管理（设置/清除/列出）
    - 变量查看
    - 调用栈跟踪

### 函数 `set_breakpoint(self, file_path: str, line: int)`

设置断点
        
        Args:
            file_path: 文件路径
            line: 行号
            
        Returns:
            是否成功（True=新增, False=已存在）

### 函数 `clear_breakpoint(self, file_path: str, line: int)`

清除断点
        
        Args:
            file_path: 文件路径
            line: 行号
            
        Returns:
            是否成功（True=已清除, False=不存在）

### 函数 `clear_all_breakpoints(self)`

清除所有断点

### 函数 `list_breakpoints(self)`

列出所有断点
        
        Returns:
            断点列表，每个元素为 (文件路径, 行号)

### 函数 `step_into(self)`

单步进入
        
        设置单步模式为 INTO，下一次执行到任何行时暂停。
        
        Returns:
            是否成功

### 函数 `step_over(self)`

单步跳过
        
        设置单步模式为 OVER，在同一层级执行到下一行时暂停。
        
        Returns:
            是否成功

### 函数 `step_out(self)`

单步跳出
        
        设置单步模式为 OUT，执行到当前函数返回时暂停。
        
        Returns:
            是否成功

### 函数 `continue_execution(self)`

继续执行
        
        取消暂停状态，恢复正常执行。
        
        Returns:
            是否成功

### 函数 `pause(self)`

暂停执行
        
        Returns:
            是否成功

### 函数 `should_break(self, file_path: str, line: int)`

检查当前行是否应该暂停
        
        检查顺序：
        1. 是否有断点命中
        2. 单步模式是否匹配
        
        Args:
            file_path: 当前文件路径
            line: 当前行号
            
        Returns:
            是否应该暂停

### 函数 `get_variables(self)`

获取当前变量
        
        Returns:
            当前局部变量字典

### 函数 `get_watch_values(self)`

获取监视变量的值
        
        Returns:
            监视变量名 -> 值的字典

### 函数 `add_watch(self, var_name: str)`

添加监视变量
        
        Args:
            var_name: 变量名
            
        Returns:
            是否成功

### 函数 `remove_watch(self, var_name: str)`

移除监视变量
        
        Args:
            var_name: 变量名
            
        Returns:
            是否成功

### 函数 `get_call_stack(self)`

获取调用栈
        
        Returns:
            调用帧字典列表，每个元素包含 func_name, file_path, line, local_vars

### 函数 `push_frame()`

### 函数 `pop_frame(self)`

弹出调用帧
        
        Returns:
            被弹出的调用帧，如果调用栈为空则返回 None

### 函数 `update_local_vars(self, vars: Dict[str, Any])`

更新当前局部变量
        
        Args:
            vars: 新的局部变量字典

### 函数 `update_current_line(self, line: int)`

更新当前行号
        
        Args:
            line: 新的行号

### 函数 `on_breakpoint_hit(self, callback: Callable[[str, int], None])`

设置断点命中回调
        
        Args:
            callback: 回调函数，接收 (file_path, line)

### 函数 `on_step_hit(self, callback: Callable[[StepMode, str, int], None])`

设置单步命中回调
        
        Args:
            callback: 回调函数，接收 (step_mode, file_path, line)

### 函数 `get_status(self)`

获取调试引擎状态
        
        Returns:
            状态字典

### 函数 `reset(self)`

重置调试引擎

---

## 模块: doc_generator

### 类 `DocParser`

文档解析器

### 函数 `parse_file(self, filepath: str)`

解析单个文件

### 类 `DocGenerator`

文档生成器

### 函数 `generate_markdown(self, filepath: str)`

生成 Markdown 文档

### 函数 `generate_html(self, filepath: str)`

生成 HTML 文档

### 函数 `generate_project_docs(self, directory: str, format: str = 'markdown')`

生成项目文档

### 函数 `run_doc(target: str, output_format: str = 'markdown', output_file: str = None)`

运行文档生成器

---

## 模块: light_parser_v3

**模块说明**: 光明（Light）编程语言 - 完整语法解析器（v3.0）

组合模块：将核心基类、语句解析混入和表达式解析混入组合成完整解析器。

支持完整语法：
- 变量声明：定义甲等于三。
- 条件语句：如果...那么...否则...
- 循环语句：遍历...当...
- 段落定义：《段名》段(参数):
- 管道操作符：-> 和 ，

### 类 `LightParser`

光明完整语法解析器

---

## 模块: lightpkg

### 类 `SemVer`

语义化版本号

### 函数 `parse(cls, version_str: str)`

解析版本字符串，如 '1.2.3', '2.0.0-alpha', '1.0.0+build.123'
        
        Args:
            version_str: 版本字符串
        
        Returns:
            SemVer 实例
        
        Raises:
            ValueError: 版本格式无效

### 函数 `satisfied_by(constraint: str, version: str)`

检查版本是否满足约束，如 '>=1.0.0,<2.0.0'
        
        Args:
            constraint: 版本约束字符串，如 '>=1.0.0', '>=1.0.0,<2.0.0', '~1.2.3', '^1.2.3'
            version: 版本字符串
        
        Returns:
            是否满足约束

### 函数 `cmd_cache(args)`

缓存管理

### 函数 `cmd_init(args)`

初始化新包

### 函数 `cmd_install(args)`

安装包

### 函数 `cmd_publish(args)`

发布包到本地或远程注册表

### 函数 `cmd_search(args)`

搜索包

### 函数 `cmd_list(args)`

列出已安装包

### 函数 `cmd_info(args)`

查看包信息

### 函数 `cmd_remove(args)`

卸载包

### 类 `DependencyResolver`

依赖解析器，处理版本约束和依赖树

### 函数 `resolve(self, package_name: str, version_constraint: str = '')`

递归解析依赖
        
        Args:
            package_name: 包名
            version_constraint: 版本约束
        
        Returns:
            {包名: 版本号} 字典

### 函数 `check_conflict(self, deps: Dict)`

检查版本冲突
        
        Args:
            deps: {包名: 版本约束} 字典
        
        Returns:
            冲突描述列表

### 函数 `cmd_metadata(args)`

管理包元数据

### 函数 `cmd_versions(args)`

查看包版本列表

### 函数 `main()`

---

## 模块: enhanced_errors

### 类 `ErrorFormatter`

错误格式化器

### 函数 `format_error(self, source: str, error: Exception, line_num: int = None, col: int = None)`

格式化错误信息

        Args:
            source: 源代码
            error: 异常对象
            line_num: 错误行号（可选）
            col: 错误列号（可选）

        Returns:
            格式化后的错误信息

### 函数 `format_error(source: str, error: Exception, line_num: int = None, col: int = None)`

格式化错误信息（便捷函数）

### 函数 `install_error_handler()`

安装全局错误处理器

---

## 模块: error_formatter

### 类 `LightErrorFormatter`

光明错误信息格式化器

### 函数 `parse_line_mapping(self, python_code: str)`

从生成的 Python 代码中解析 LIGHT_SRC 行号映射表

        Returns:
            dict: {python_line: (light_line, code_snippet)}

### 函数 `build_full_mapping(self, python_code: str)`

构建完整的 Python 行号 -> 光明行号映射

        思路：
        1. 先找 LIGHT_SRC 注释对应的 Python 行号
        2. 假设两个相邻映射点之间是连续的（简单的近似）

### 函数 `format_exception(self, exc_type=None, exc_value=None, exc_tb=None)`

格式化异常为光明友好的错误信息

        Args:
            exc_type: 异常类型
            exc_value: 异常值
            exc_tb: traceback 对象

        Returns:
            格式化后的错误信息字符串

### 函数 `format_traceback_string(self, tb_text: str)`

格式化 traceback 字符串为光明友好版本

### 函数 `run_with_friendly_error(code: str, source: str = '', source_name: str = '<光明代码>')`

执行代码并以友好的方式报告错误

    Args:
        code: 要执行的 Python 代码
        source: 光明源代码（用于上下文显示）
        source_name: 源代码名称

    Returns:
        退出码 (0=正常, 1=错误)

### 函数 `format_runtime_error(source: str, exc_type=None, exc_value=None, exc_tb=None)`

便捷函数：格式化运行时错误

    Args:
        source: 光明源代码
        exc_type, exc_value, exc_tb: 异常信息，默认为 sys.exc_info()

---

## 模块: errors

### 函数 `format_exception(exc_type, exc_value, exc_tb, source_lines=None)`

格式化异常为美化的中文输出

### 函数 `install_excepthook()`

安装自定义的异常处理器

### 函数 `custom_excepthook(exc_type, exc_value, exc_tb)`

### 函数 `format_source_context(source, line, col=None, context_lines=3)`

格式化源代码上下文（增强版：显示行号、列号箭头、上下文行）

### 函数 `format_error_with_context()`

### 类 `LightError`

光明基础错误类

### 类 `LexerError`

词法分析错误

### 类 `SemanticError`

语义分析错误

### 类 `ParseError`

语法解析错误

### 类 `LightErrorFormatter`

统一错误格式化器

### 函数 `get_fix_suggestions(error_type: str, message: str)`

根据错误类型和消息自动匹配修复建议
        
        Args:
            error_type: 错误类型名称（如 'LexerError', 'SemanticError'）
            message: 错误消息文本
            
        Returns:
            匹配的修复建议列表，未匹配时返回空列表

### 函数 `format(error: Exception, source: str = None)`

统一格式化错误
        
        Args:
            error: 异常对象
            source: 可选的源代码
            
        Returns:
            格式化的错误信息

### 函数 `format_with_source(error: Exception, source: str, line: int, col: int)`

带源代码标注的格式化
        
        Args:
            error: 异常对象
            source: 源代码文本
            line: 错误行号
            col: 错误列号
            
        Returns:
            带源代码标注的完整错误信息

---

## 模块: file_watcher

### 类 `FileWatcher`

### 函数 `start(self)`

开始监视

### 函数 `stop(self)`

停止监视

### 函数 `run_with_watch(filepath, backend='src', interval=1.0)`

以监视模式运行光明文件

    Args:
        filepath: 源文件路径
        backend: 后端类型
        interval: 检查间隔（秒）

### 函数 `capture_print(*args, **kwargs)`

---

## 模块: formatter

### 函数 `format_code(source: str)`

格式化光明代码

### 函数 `check_format(source: str)`

检查格式问题

### 函数 `format_file(filepath: str, check_only: bool = False)`

格式化单个文件

### 函数 `format_directory(directory: str, check_only: bool = False)`

格式化目录

### 函数 `run_formatter(target: str, check_only: bool = False)`

---

## 模块: incremental_compiler

**模块说明**: 光明增量编译器

只重新编译修改过的模块，加速大型项目编译。
支持文件监听模式，自动检测并重新编译变化文件。

### 类 `IncrementalCompiler`

增量编译器

    只重新编译修改过的模块，加速大型项目编译。
    跟踪文件依赖关系，支持增量编译和全量编译。

    Attributes:
        cache: 编译缓存实例
        _dirty_files: 脏文件集合
        _compiled_modules: 已编译的模块记录
        _file_dependencies: 文件依赖关系

### 函数 `compile()`

### 函数 `compile_project()`

### 函数 `get_dirty_modules(self, project_root: str)`

获取需要重新编译的模块

        比较文件修改时间和缓存时间，找出已修改的文件。

        Args:
            project_root: 项目根目录路径

        Returns:
            需要重新编译的文件路径列表

### 函数 `watch()`

### 函数 `get_compile_stats(self)`

获取编译统计信息

        Returns:
            编译统计信息字典

---

## 模块: ir

**模块说明**: 光明（Light）编程语言 - 中间表示（IR）系统

使用三地址码（Three-Address Code）作为中间表示，便于后续优化和代码生成。

### 类 `OpCode`

操作码定义

### 类 `IRValue`

IR值基类

### 类 `Temp`

临时变量

### 类 `Label`

标签

### 类 `Const`

常量

### 类 `Variable`

变量引用

### 类 `Parameter`

函数参数

### 类 `Memory`

内存地址

### 类 `Instruction`

三地址码指令

### 类 `BasicBlock`

基本块

### 函数 `add_instruction(self, instr: Instruction)`

添加指令

### 类 `FunctionIR`

函数的IR表示

### 函数 `new_temp(self)`

创建新的临时变量

### 函数 `new_block(self, name: Optional[str] = None)`

创建新的基本块

### 函数 `add_block(self, block: BasicBlock)`

添加基本块

### 函数 `get_block(self, name: str)`

获取基本块

### 类 `ModuleIR`

模块的IR表示

### 函数 `add_function(self, func: FunctionIR)`

添加函数

### 函数 `get_function(self, name: str)`

获取函数

### 函数 `add_string_constant(self, string: str)`

添加字符串常量并返回偏移

### 类 `IRGenerator`

从AST生成三地址码IR

### 函数 `new_label(self)`

创建新标签

### 函数 `visit_Module(self, ast_module)`

访问AST模块

### 函数 `visit_FunctionDefinition(self, node)`

访问函数定义

### 函数 `visit_Block(self, node)`

访问代码块

### 函数 `visit_VariableDeclaration(self, node)`

访问变量声明

### 函数 `visit_Assignment(self, node)`

访问赋值语句

### 函数 `visit_Identifier(self, node)`

访问标识符

### 函数 `visit_NumberLiteral(self, node)`

访问数字字面量

### 函数 `visit_StringLiteral(self, node)`

访问字符串字面量

### 函数 `visit_BooleanLiteral(self, node)`

访问布尔字面量

### 函数 `visit_BinaryOp(self, node)`

访问二元运算

### 函数 `visit_UnaryOp(self, node)`

访问一元运算

### 函数 `visit_FunctionCall(self, node)`

访问函数调用

### 函数 `visit_IfStatement(self, node)`

访问条件语句

### 函数 `visit_WhileStatement(self, node)`

访问while循环

### 函数 `visit_ReturnStatement(self, node)`

访问返回语句

### 函数 `visit_PrintStatement(self, node)`

访问打印语句

### 函数 `visit(self, node)`

调度访问方法

### 函数 `generate(self, ast_module)`

生成IR

### 类 `IROptimizer`

IR优化器

### 函数 `optimize(module: ModuleIR)`

优化模块IR

### 函数 `optimize_function(func: FunctionIR)`

优化函数IR

### 函数 `constant_propagation(func: FunctionIR)`

常量传播优化

### 函数 `dead_code_elimination(func: FunctionIR)`

死代码消除

### 函数 `test_ir_generator()`

测试IR生成器

---

## 模块: keywords

**模块说明**: 光明（Light）编程语言关键字定义

核心设计（v4.0 分层语法）：
- L0 核心字表（30字冻结）：单字为主形式，双字/多字为向后兼容别名
  参考中文：3000常用字稳定不变，组合灵活
- 分层架构：L0(核心字) → L1(白话体/教学) → L2(文言体/工程)
            → L3(领域嵌入: SQL/正则/数学) → L4(外语引用: Python/C/Go)
- 动词声明参数数量（元数驱动解析，决策28）

### 函数 `is_keyword(word: str)`

判断是否为关键字

### 函数 `is_double_keyword(word: str)`

判断是否为双字关键字

### 函数 `get_arity(verb: str)`

获取动词的参数数量

### 函数 `get_verb_mode(verb: str)`

获取动词的修改模式

### 函数 `is_builtin_type(word: str)`

判断是否为内置类型

### 函数 `normalize_symbol(char: str)`

将中文符号转换为英文符号

---

## 模块: lexer

**模块说明**: 光明（Light）编程语言 - 词法分析器

实现决策29的三层分词机制：
1. 类型切换自动分词 - 甲加1 → [甲] [加] [1]
2. 双字关键词优先匹配 - 定义甲 → [定义] [甲]
3. 元数驱动参数收集 - 打印 甲 -（元数=1）→ [打印] [甲]

参考：newlisp/yan 的无空格分词实现

### 类 `LexerError`

词法分析错误

### 类 `Lexer`

光明词法分析器：无空格分词 + 三层机制

### 函数 `tokenize(self, source: str = None)`

将源码转为 Token 流
        
        支持两种调用方式：
        - lexer.tokenize()  # 使用构造时传入的 source
        - lexer.tokenize(source)  # 使用传入的 source
        
        Args:
            source: 要分析的源码字符串（可选，默认使用构造时传入的）

---

## 模块: linker

**模块说明**: 光明（Light）编程语言 - 链接器和可执行文件生成器

支持：
- Linux ELF格式
- Windows PE/COFF格式
- macOS Mach-O格式

### 类 `ExecutableFormat`

可执行文件格式抽象基类

### 函数 `add_section(self, name: str, data: bytes, flags: int = 0)`

添加段

### 函数 `add_symbol(self, name: str, offset: int, is_global: bool = False)`

添加符号

### 函数 `add_relocation(self, section_idx: int, offset: int, symbol_name: str, type: int)`

添加重定位

### 函数 `generate(self)`

生成可执行文件字节流

### 类 `Section`

段

### 类 `Symbol`

符号

### 类 `Relocation`

重定位

### 类 `ELFFormat`

ELF可执行文件格式

### 函数 `generate(self)`

生成ELF文件

### 类 `PEFormat`

PE/COFF可执行文件格式

### 函数 `generate(self)`

生成PE文件

### 类 `Linker`

链接器

### 函数 `add_object_file(self, obj_file)`

添加目标文件

### 函数 `set_runtime_code(self, code: bytes)`

设置运行时代码

### 函数 `add_string_constants(self, strings: bytes)`

添加字符串常量

### 函数 `link(self)`

链接并生成可执行文件

### 类 `ObjectFile`

目标文件抽象

### 类 `AssemblerWrapper`

汇编器封装

### 函数 `emit(self, instr: str)`

添加汇编指令

### 函数 `emit_label(self, name: str)`

添加标签

### 函数 `new_label(self)`

创建新标签

### 函数 `assemble(self)`

汇编为机器码（简化实现）

### 类 `LightCompiler`

光明编译器主类

### 函数 `compile(self, ast_module)`

编译AST为可执行文件

### 函数 `test_compiler()`

测试编译器

---

## 模块: linter

### 类 `Severity`

=============================================================================
规则定义
=============================================================================

### 类 `LintRule`

检查规则

### 类 `LintIssue`

检查结果

### 类 `LightLinter`

光明代码检查器

### 函数 `check(self, source: str, filepath: str = '')`

执行所有检查

### 函数 `auto_fix(source: str, issues: List[LintIssue])`

自动修复简单问题

### 函数 `format_issues_text(issues: List[LintIssue], filepath: str = '')`

格式化输出（文本格式）

### 函数 `format_issues_json(issues: List[LintIssue], filepath: str = '')`

格式化输出（JSON 格式）

### 函数 `lint_file()`

=============================================================================
入口函数
=============================================================================

### 函数 `lint_directory()`

### 函数 `run_linter()`

---

## 模块: module_resolver

**模块说明**: 光明（Light）编程语言 - 模块解析器

实现功能：
1. 模块查找（搜索.duan文件）
2. 依赖图构建
3. 循环依赖检测
4. 拓扑排序（确定编译顺序）

### 类 `ModuleError`

模块相关错误基类

### 类 `ModuleNotFoundError`

模块未找到

### 类 `CircularDependencyError`

循环依赖错误

### 类 `ModuleInfo`

模块信息

### 类 `DependencyGraph`

依赖图

### 函数 `add_module(self, module: ModuleInfo)`

添加模块节点

### 函数 `add_dependency(self, from_module: str, to_module: str)`

添加依赖关系

### 函数 `get_dependencies(self, module_name: str)`

获取模块的直接依赖

### 函数 `get_all_dependencies(self, module_name: str)`

获取模块的所有依赖（递归）

### 类 `ModuleResolver`

模块解析器

### 函数 `get_stdlib_module(self, module_name: str)`

获取标准库模块信息

### 函数 `get_stdlib_module_names(self)`

获取所有可用的标准库模块名

### 函数 `load_stdlib_module(self, module_name: str)`

加载标准库模块
        
        Args:
            module_name: 模块名
        
        Returns:
            模块信息，如果未找到则返回 None

### 函数 `preload_builtins(self)`

预加载内置模块（builtins）
        确保内置函数在编译时可用

### 函数 `find_module(self, module_name: str, from_dir: str = None)`

查找模块文件
        
        Args:
            module_name: 模块名
            from_dir: 从哪个目录开始查找（用于相对导入）
        
        Returns:
            模块文件路径
        
        Raises:
            ModuleNotFoundError: 模块未找到

### 函数 `parse_module(self, module_path: Path)`

解析模块文件
        
        Args:
            module_path: 模块文件路径
        
        Returns:
            模块信息

### 函数 `build_dependency_graph(self, main_module: str, from_dir: str = None)`

构建依赖图
        
        Args:
            main_module: 主模块名
            from_dir: 主模块所在目录
        
        Returns:
            依赖图

### 函数 `visit(module_name: str, module_dir: str = None)`

访问模块并构建依赖图

### 函数 `detect_circular_dependency(self, graph: DependencyGraph)`

检测循环依赖
        
        Args:
            graph: 依赖图
        
        Returns:
            循环依赖路径，如果没有则返回 None

### 函数 `dfs(node: str)`

深度优先搜索检测环

### 函数 `detect_all_cycles(self, graph: DependencyGraph)`

检测所有循环依赖，返回所有环的列表
        
        Args:
            graph: 依赖图
        
        Returns:
            所有循环依赖路径的列表，每个元素是一个环路径

### 函数 `dfs(node: str, path_stack: List[str])`

深度优先搜索检测所有环

### 函数 `topological_sort(self, graph: DependencyGraph)`

拓扑排序（确定编译顺序）
        
        Args:
            graph: 依赖图
        
        Returns:
            模块名列表（按编译顺序）

### 函数 `resolve(self, main_file: str)`

解析主文件及其所有依赖
        
        Args:
            main_file: 主文件路径
        
        Returns:
            (模块列表（按编译顺序），依赖图)
        
        Raises:
            ModuleNotFoundError: 模块未找到
            CircularDependencyError: 循环依赖

### 类 `ResolvedModule`

已解析模块（用于 compile_project 跨模块链接）

### 类 `CircularDependencyError`

循环依赖错误（与上方重名但可共存，此处保持清晰）

### 类 `ModuleDependencyResolver`

递归解析入口模块及所有 import 依赖，进行循环检测与拓扑排序。

    与模块中的 ImportStmt（`导入 模块`、`从 模块 导入 符号`）协同工作。

### 函数 `resolve_all()`

------------------------------------------------------------------
公共接口
------------------------------------------------------------------

### 函数 `topological_order(self)`

返回模块拓扑排序结果（被依赖的在前）。

### 函数 `visit(name: str)`

### 类 `ModuleLoader`

模块加载器

### 函数 `load(self, module_name: str, from_dir: str = None)`

加载模块
        
        Args:
            module_name: 模块名
            from_dir: 从哪个目录查找
        
        Returns:
            模块信息

### 函数 `load_project(self, main_file: str)`

加载整个项目
        
        Args:
            main_file: 主文件路径
        
        Returns:
            模块列表（按依赖顺序）

---

## 模块: package_installer

### 类 `PackageInfo`

段件信息

### 函数 `to_dict(self)`

### 类 `GitUrlInfo`

解析后的 Git 仓库 URL 信息

### 类 `GitUrlParser`

解析 Git 仓库 URL，生成平台对应的 ZIP 下载链接

### 函数 `parse(cls, git_url: str)`

解析 Git URL，返回 GitUrlInfo 或 None

### 类 `MirrorResult`

镜像测速结果

### 类 `MirrorSpeedTest`

并发测速：对多个镜像源发起 HEAD 请求，选最快的

    工作原理：
      1. 对每个镜像的 ZIP 下载链接发起 HEAD 请求
      2. 测量 TCP 连接 + HTTP 响应时间
      3. 并发执行，2 秒内返回最快的结果
      4. 全部不可达时返回 None

### 函数 `find_fastest(cls, mirror_urls: List[str])`

从镜像列表中找到最快的

        Args:
            mirror_urls: Git 仓库 URL 列表

        Returns:
            最快的 MirrorResult，全部不可达返回 None

### 类 `ZipDownloader`

从 GitCode / GitHub / Gitee 下载 ZIP 段件并解压

### 函数 `download_and_extract(cls, zip_url: str, dest_dir: Path, package_name: str)`

下载 ZIP 并解压到目标目录

        Args:
            zip_url: ZIP 下载链接
            dest_dir: 解压目标目录
            package_name: 包名（用于日志）

        Returns:
            是否成功

### 类 `PackageInstaller`

光明包安装器

    安装策略（按优先级）：
      1. GitCode/GitHub/Gitee 公开仓库 → ZIP 下载（无需 Git）
      2. GitCode/GitHub/Gitee 私有仓库 → Git Clone（需要 Git + 认证）
      3. 其他 Git 仓库                → Git Clone

    典型用法：
        installer = PackageInstaller()
        installer.install("标准数学扩展")        # 从注册中心安装
        installer.install_from_git("https://gitcode.com/user/repo.git")
        installer.install_from_path("./local-package")
        installer.list_installed()               # 列出已安装
        installer.search("网络")                  # 搜索

### 函数 `search(self, keyword: str)`

搜索段件

### 函数 `list_registry(self)`

列出注册表中所有段件

### 函数 `install(self, package_name: str, version: Optional[str] = None)`

从注册中心安装段件（自动测速选最快镜像）

### 函数 `install_from_git(self, git_url: str, package_name: Optional[str] = None)`

从 Git 仓库安装段件

### 函数 `install_from_path(self, local_path: str)`

从本地路径安装段件

### 函数 `list_installed(self)`

列出已安装的段件

### 函数 `uninstall(self, package_name: str)`

卸载段件

### 函数 `run_install(args)`

运行安装命令

### 函数 `run_publish(args)`

发布段件 — 生成段件库条目并显示 PR 提交指引

---

## 模块: package_manager

**模块说明**: 光明（Light）包管理器

负责：
1. package.toml 项目配置文件的解析
2. 项目目录初始化（package.toml + 主.light）
3. 入口模块发现与项目级编译入口

设计原则：
- 不依赖外部 toml 库，内置极简解析
- 所有文件操作均有异常安全保护
- 与 src/compiler.py、src/module_resolver.py 解耦

### 类 `PackageConfig`

从 package.toml 解析出的包配置

### 函数 `to_dict(self)`

### 类 `Package`

解析后的完整包信息（包含模块 AST 等）

### 类 `TomlParser`

极简 TOML 解析器（仅支持项目所需子集）

    支持语法：
      [section]
      key = "字符串"
      key = 123
      key = 1.5
      key = true / false / yes / no
      key = [ "a", "b" ]
      key = { sub = "value" }

    不支持：多行字符串、嵌套数组、[[arrays_of_tables]]。

### 函数 `parse(self, content: str)`

### 类 `PackageManager`

光明包管理器。

    典型用法：
        pm = PackageManager(project_root)
        pm.init_project("myproject")    # 新建项目
        config = pm.load_config()       # 读取 package.toml
        result = pm.build_project()     # 编译整个项目
        status = pm.run_project()       # 运行

### 函数 `init_project(self, name: Optional[str] = None)`

在 project_root 下创建 package.toml 与 主.light。

        如果目录不存在则自动创建；文件已存在时返回 True（视为幂等）。

### 函数 `load_config(self)`

加载 project_root/package.toml。

        返回 PackageConfig 或 None（文件不存在或解析失败）。

### 函数 `find_module(self, module_name: str)`

根据模块名找到对应的 .light 文件。

        支持格式：
          - 数学        ->  数学.light
          - 数学.工具   ->  数学/工具.light
          - 数学/工具   ->  数学/工具.light

### 函数 `build_project(self)`

编译整个项目：加载 package.toml，编译入口模块及依赖。

        返回字典：
            {
                'success': bool,
                'config': PackageConfig | None,
                'project_root': str,
                'entry': str,
                'modules': { module_name: {...} },
                'order': [module_name, ...],  # 拓扑排序
                'errors': [str, ...],
            }

### 函数 `run_project(self)`

先构建，再尝试翻译入口模块并在隔离命名空间内 exec。

        返回 0 表示成功，非 0 表示失败。

### 函数 `resolve_path_dependencies(self)`

解析 package.toml 中的 path 依赖。

        支持格式：
            [dependencies]
            utils = { path = "../utils" }
            mylib = { path = "./lib/mylib" }

        返回：依赖名 -> 路径 的字典

### 函数 `build_project_native(self, output_path: str = None, verbose: bool = False)`

使用 LLVM 后端编译项目为原生可执行文件。

        自动解析 path 依赖，收集所有模块源码，编译合并为单一可执行文件。

        Args:
            output_path: 输出路径
            verbose: 是否输出详细信息

        Returns:
            可执行文件路径

### 函数 `collect(src: str, mod_name: str)`

### 函数 `load_package(project_root: Optional[Path] = None)`

加载光明项目配置

### 函数 `init_package(project_root: Optional[Path] = None, name: Optional[str] = None)`

初始化光明项目

### 函数 `build_package(project_root: Optional[Path] = None)`

编译光明项目

### 函数 `run_package(project_root: Optional[Path] = None)`

编译并运行光明项目

---

## 模块: parser_core

**模块说明**: 光明（Light）编程语言 - 语法解析器核心框架

提供基础解析框架：
- 词法分析集成
- Token 流管理
- 辅助方法（_current, _consume, _match, _peek）
- 操作符映射表

### 类 `ParseError`

语法解析错误

### 类 `LightParserCore`

光明完整语法解析器核心基类

### 函数 `parse(self, source: str)`

解析光明代码

---

## 模块: parser_expr

**模块说明**: 光明（Light）编程语言 - 表达式解析混入类

提供所有表达式级别解析方法，包括：
- 算术表达式（加、减、乘、除）
- 比较表达式
- 逻辑表达式
- 基本表达式（数字、字符串、标识符、括号等）
- 后缀表达式（函数调用、成员访问、索引访问）
- 列表/字典字面量
- Lambda 表达式
- 字符串插值

### 类 `ParserExprMixin`

表达式解析混入类

---

## 模块: parser_stmt

**模块说明**: 光明（Light）编程语言 - 语句解析混入类

提供所有语句级别解析方法，包括：
- 模块解析
- 变量声明、赋值、条件、循环
- 导入/导出
- 段落定义
- 类/接口定义
- 模式匹配
- 异常处理

### 类 `CForStmt`

C风格for循环：循环(init;cond;incr){body}

### 类 `Block`

花括号代码块

### 类 `ParserStmtMixin`

语句解析混入类

---

## 模块: profiler

### 类 `LightProfiler`

光明性能分析器

### 函数 `profile(self, filepath: str, memory: bool = False, report: bool = False)`

分析光明程序的性能

        Args:
            filepath: 光明文件路径
            memory: 是否分析内存
            report: 是否生成详细报告

        Returns:
            性能分析结果

### 函数 `capture_print(*args, **kwargs)`

### 函数 `profile_with_cprofile(self, filepath: str)`

使用 cProfile 进行详细性能分析

        Args:
            filepath: 光明文件路径

        Returns:
            详细性能分析结果

### 函数 `format_profile_output(stats: dict, report: bool = False, cprofile: bool = False)`

格式化输出性能分析结果

### 函数 `run_profile(target: str, memory: bool = False, report: bool = False, cprofile: bool = False)`

运行性能分析

---

## 模块: registry_server

### 类 `PackageStorage`

包存储管理器

### 函数 `list_packages(self)`

列出所有包

### 函数 `get_package(self, name: str, version: str = None)`

获取包信息

### 函数 `publish_package()`

### 函数 `download_package(self, name: str, version: str = None)`

下载包

### 函数 `search_packages(self, query: str)`

搜索包

### 函数 `get_stats(self)`

获取统计信息

### 类 `RegistryHandler`

注册表 HTTP 处理器

### 函数 `log_message(self, format, *args)`

自定义日志

### 函数 `do_OPTIONS(self)`

处理 CORS 预检请求

### 函数 `do_GET(self)`

处理 GET 请求

### 函数 `do_POST(self)`

处理 POST 请求

### 函数 `main()`

=============================================================================
入口
=============================================================================

---

## 模块: semantic_analyzer

**模块说明**: 光明（Light）编程语言 - 语义分析器

负责：
1. 符号表构建和管理
2. 类型检查和推断
3. 作用域分析
4. 错误检测

### 类 `SemanticError`

语义错误异常

### 类 `SemanticAnalyzer`

语义分析器

### 函数 `add_error(self, message: str, node: ASTNode)`

添加错误

### 函数 `enter_scope(self)`

进入新作用域

### 函数 `exit_scope(self)`

退出当前作用域（简单实现）

### 函数 `declare_symbol(self, name: str, type: Type, node: ASTNode, is_mutable: bool = False, is_global: bool = False)`

声明符号

### 函数 `resolve_symbol(self, name: str, node: ASTNode)`

解析符号引用

### 函数 `check_types(self, expected: Type, actual: Type, node: ASTNode, context: str = "")`

检查类型兼容性（使用子类型关系，支持多态）

### 函数 `visit_Module(self, node: Module)`

访问模块

### 函数 `visit_StructDefinition(self, node: StructDefinition)`

访问结构体定义

### 函数 `get_type_size(self, type: Type)`

获取类型大小（字节）

### 函数 `visit_GlobalVariable(self, node: GlobalVariable)`

访问全局变量

### 函数 `visit_FunctionDefinition(self, node: FunctionDefinition)`

访问函数定义

### 函数 `visit_Block(self, node: Block)`

访问代码块

### 函数 `visit_VariableDeclaration(self, node: VariableDeclaration)`

访问变量声明

### 函数 `visit_Identifier(self, node: Identifier)`

访问标识符

### 函数 `visit_NumberLiteral(self, node: NumberLiteral)`

访问数字字面量

### 函数 `visit_StringLiteral(self, node: StringLiteral)`

访问字符串字面量

### 函数 `visit_BooleanLiteral(self, node: BooleanLiteral)`

访问布尔字面量

### 函数 `visit_BinaryOp(self, node: BinaryOp)`

访问二元运算

### 函数 `visit_UnaryOp(self, node: UnaryOp)`

访问一元运算

### 函数 `visit_FunctionCall(self, node: FunctionCall)`

访问函数调用

### 函数 `visit_Assignment(self, node: Assignment)`

访问赋值语句

### 函数 `visit_IfStatement(self, node: IfStatement)`

访问条件语句

### 函数 `visit_WhileStatement(self, node: WhileStatement)`

访问while循环

### 函数 `visit_ForStatement(self, node: ForStatement)`

访问for循环

### 函数 `visit_ReturnStatement(self, node: ReturnStatement)`

访问return语句

### 函数 `analyze(self)`

执行语义分析

---

## 模块: semantic_identifier

**模块说明**: 光明（Light）编程语言 - 语义识别器

实现决策34：主谓/谓宾语义识别

主谓结构：对象 操作 → 原地修改
  示例：列表排序 → 列表.sort()

谓宾结构：操作 对象 → 返回新对象
  示例：排序列表 → sorted(列表)

定语结构：包含"的" → 临时生成
  示例：排序后的列表 → sorted(列表)

### 类 `SemanticType`

语义类型

### 类 `SemanticIdentifier`

语义识别器 - 识别主谓/谓宾语义

### 函数 `identify(self, expr: ASTNode)`

识别表达式的语义类型
        
        Args:
            expr: AST节点
            
        Returns:
            (语义类型, 操作符/动词名称)

### 函数 `generate_python_code(semantic_type: str, verb: str, args: list, symbol_table: dict = None)`

根据语义类型生成Python代码
    
    Args:
        semantic_type: 语义类型
        verb: 动词名称
        args: 参数列表
        symbol_table: 符号表
        
    Returns:
        Python代码字符串

---

## 模块: templates

### 类 `ProjectTemplate`

项目模板基类

### 函数 `create(self, project_dir: Path)`

创建项目结构

### 类 `DefaultTemplate`

默认空项目模板

### 函数 `create(self, project_dir: Path)`

### 类 `CLITemplate`

命令行工具模板

### 函数 `create(self, project_dir: Path)`

### 类 `LibTemplate`

库/包模板

### 函数 `create(self, project_dir: Path)`

### 类 `WebTemplate`

Web 应用模板

### 函数 `create(self, project_dir: Path)`

### 函数 `get_template(name: str)`

获取模板

### 函数 `list_templates()`

列出所有模板

### 函数 `create_project(project_dir: Path, template_name: str = 'default')`

创建项目

---

## 模块: test_exception_output

### 函数 `测试基本异常()`

### 函数 `测试抛出异常()`

### 函数 `测试最终块()`

### 类 `异常`

### 函数 `主()`

---

## 模块: test_output

### 函数 `主()`

### 类 `狗`

### 函数 `说话(self)`

---

## 模块: test_runner

### 函数 `discover_test_files(directory: str, pattern: str = None)`

发现测试文件

    按以下规则查找：
    1. tests/ 目录下的所有 .light 文件（递归）
    2. 当前目录下匹配 *_test.light 或 test_*.light 的文件

    Args:
        directory: 项目根目录
        pattern: 过滤模式（可选）

    Returns:
        测试文件路径列表

### 函数 `run_test_file(filepath: str, verbose: bool = False)`

运行单个测试文件

    Args:
        filepath: .light 文件路径
        verbose: 是否详细输出

    Returns:
        {'name': str, 'passed': bool, 'time': float, 'output': str, 'error': str}

### 函数 `capture_print(*args, **kwargs)`

### 函数 `run_tests(directory: str, filter_pattern: str = None, verbose: bool = False)`

运行所有测试

    Args:
        directory: 项目根目录
        filter_pattern: 过滤模式
        verbose: 详细输出

    Returns:
        退出码（0=全部通过, 1=有失败）

### 函数 `run_single_file(filepath: str, verbose: bool = False)`

运行单个测试文件

    Args:
        filepath: .light 文件路径
        verbose: 详细输出

    Returns:
        退出码

---

## 模块: tokens

**模块说明**: 光明（Light）编程语言 - Token 定义

基于设计规范：
- 决策27：双字关键字
- 决策28：元数驱动解析
- 决策29：三层分词机制

### 类 `TokenType`

Token 类型

### 类 `Token`

Token 数据结构

---

## 模块: type_checker

### 类 `TypeErrorSeverity`

类型错误严重程度

### 类 `TypeCheckResult`

类型检查结果

### 函数 `is_error(self)`

### 类 `TypeCheckerConfig`

类型检查器配置：控制检查的粒度和严格程度

### 函数 `from_light_config(cls, dc: LightConfig)`

从 LightConfig 创建配置

### 函数 `apply_file_directives(self, source: str)`

从源文件注释中提取文件级类型检查指令并应用到配置

### 函数 `get_segment_check_level(self, modifiers: List[str])`

根据段落修饰符确定检查级别

### 类 `LightType`

光明类型基类

### 函数 `to_duan(self)`

### 函数 `to_python(self)`

### 函数 `is_compatible(self, other: 'LightType')`

检查类型兼容性

### 类 `PrimitiveType`

基本类型

### 函数 `to_duan(self)`

### 函数 `to_python(self)`

### 函数 `is_compatible(self, other: 'LightType')`

### 类 `ListType`

列表类型：列表<元素类型>

### 函数 `to_duan(self)`

### 函数 `to_python(self)`

### 函数 `is_compatible(self, other: 'LightType')`

### 类 `DictType`

字典类型：字典<键类型, 值类型>

### 函数 `to_duan(self)`

### 函数 `to_python(self)`

### 函数 `is_compatible(self, other: 'LightType')`

### 类 `UnionType`

联合类型：整数|浮点、字符串|空

### 函数 `to_duan(self)`

### 函数 `to_python(self)`

### 函数 `is_compatible(self, other: 'LightType')`

### 类 `OptionalType`

可选类型：可空整数

### 函数 `to_duan(self)`

### 函数 `to_python(self)`

### 函数 `is_compatible(self, other: 'LightType')`

### 类 `FunctionType`

函数类型：(参数类型) -> 返回类型

### 函数 `to_duan(self)`

### 函数 `to_python(self)`

### 函数 `is_compatible(self, other: 'LightType')`

### 类 `AnyType`

任意类型（未标注或无法推导）

### 函数 `to_duan(self)`

### 函数 `to_python(self)`

### 函数 `is_compatible(self, other: 'LightType')`

### 类 `TypeVarType`

泛型类型变量（如 T、K、V）
    
    用于表示泛型类型参数，如列表[T] 中的 T。

### 函数 `to_duan(self)`

### 函数 `to_python(self)`

### 函数 `is_compatible(self, other: 'LightType')`

### 类 `GenericTypeInstance`

泛型类型实例化（如 列表[T]、字典[K, V]）

### 函数 `to_duan(self)`

### 函数 `to_python(self)`

### 函数 `is_compatible(self, other: 'LightType')`

### 函数 `parse_type_annotation(annotation: str)`

解析类型标注字符串为类型对象

### 类 `TypeEnv`

类型环境：跟踪当前作用域中变量的类型

### 函数 `define(self, name: str, t: LightType)`

### 函数 `lookup(self, name: str)`

### 函数 `define_function(self, name: str, t: FunctionType)`

### 函数 `lookup_function(self, name: str)`

### 函数 `push_scope(self)`

### 函数 `pop_scope(self)`

### 函数 `infer_type_from_value(value_node)`

从 AST 值节点推导类型

### 类 `IssueLevel`

=============================================================================
独立类型检查器（CLI 用）
=============================================================================

### 类 `TypeIssue`

### 类 `TypeChecker`

光明独立类型检查器（CLI 使用）

### 函数 `check(self, module)`

检查整个模块的类型

### 类 `GradedTypeChecker`

分级类型检查器 —— 与编译器集成，支持三级检查

    根据 TypeCheckerConfig 的 check_level 执行不同粒度的检查：
      - SIGNATURE：仅检查段落参数和返回值类型标注
      - VARIABLE：签名级 + 变量声明类型检查
      - EXPRESSION：变量级 + 表达式运算类型检查

### 函数 `check(self, module, inferencer=None)`

执行分级类型检查

        当提供 inferencer（TypeInferencer 实例）时，变量级和表达式级检查会
        利用 inferencer 的类型缓存获得更准确的类型信息。

### 函数 `get_errors(self)`

### 函数 `get_warnings(self)`

### 函数 `has_errors(self)`

### 类 `LightTypeBridge`

类型系统桥接器：在 type_checker 的简单类型系统与 type_inferencer 的高级类型系统之间转换

    两个类型系统：
      - 简单系统（type_checker）：LightType 层次（PrimitiveType, ListType, DictType, ...）
      - 高级系统（type_system）：Type 层次（NumberType, StringType, BooleanType, ...）

    桥接器提供双向转换，使 GradedTypeChecker 能利用 TypeInferencer 的推断结果。

### 函数 `simple_to_advanced(simple_type: LightType)`

将简单 LightType 转换为高级 Type 对象

### 函数 `advanced_to_simple(adv_type: 'Any')`

将高级 Type 对象转换为简单 LightType

### 类 `CFGAnalyzer`

控制流分析器：用于分析段落的返回路径

    核心功能：
      - 检测所有路径是否都有返回值
      - 检测不可达代码
      - 检测遗漏的返回路径

### 函数 `all_paths_return(body: List[Any])`

检查代码块的所有执行路径是否都有 return 语句

### 函数 `check_missing_return(seg, declared_return_type: LightType)`

检查段落是否缺少返回语句，返回问题列表

### 函数 `find_unreachable_code(body: List[Any])`

查找不可达代码的行号列表

### 函数 `create_checker_from_source(source: str, dc: LightConfig)`

从源代码和 LightConfig 创建分级类型检查器

    从源文件头部的注释中提取类型检查指令并应用到配置。

### 函数 `create_checker_from_config(dc: LightConfig)`

从 LightConfig 创建分级类型检查器（无源代码指令）

### 函数 `check_module(module, strict: bool = False)`

检查模块的类型（独立检查器）

### 函数 `check_source(source: str, strict: bool = False)`

检查源代码的类型（独立检查器）

### 函数 `format_issues(issues: List[TypeIssue], source: str = '')`

格式化类型检查问题为可读文本

---

## 模块: type_inferencer

**模块说明**: 光明（Light）编程语言 - 增强类型推断器（Phase 1 版本）

特点：
- 完整的类型系统：基本类型、复合类型、泛型类型、类类型、接口类型
- 基于合一（unification）的类型变量解析
- 泛型段落（函数）的类型参数推断
- 泛型类实例化
- 局部变量类型推断
- 函数返回类型推断

### 类 `InferenceResult`

单个表达式的推断结果（类型 + 相关的替换）

### 类 `SegmentCacheEntry`

段推断缓存条目（增量推断用）

### 类 `TypeInferencer`

光明增强类型推断器（Phase 1 版本）

### 函数 `register_enum(self, enum_def: EnumDefinition)`

注册枚举类型

### 函数 `register_trait(self, trait_def: TraitDefinition)`

注册 trait 定义

### 函数 `register_interface(self, iface_def)`

注册接口定义（InterfaceDefinition 节点）

### 函数 `register_trait_impl(self, impl: TraitImplementation)`

注册 trait 实现并检查方法是否完整且签名匹配

### 函数 `infer(self, module: Module, incremental: bool = False)`

对整个模块进行类型推断（HM 风格两阶段：预扫描 + 推断 + 泛化）

        Args:
            module: 要推断的模块
            incremental: 是否启用增量推断缓存（IDE 场景下可大幅提速）

### 函数 `get_errors(self)`

---- 公共辅助 ----

### 函数 `get_typed_errors(self)`

获取结构化类型错误列表（携带位置信息）

### 函数 `get_type_cache(self)`

### 函数 `walk(node: Type)`

---

## 模块: type_system

**模块说明**: 光明（Light）编程语言 - 类型系统定义（Phase 1 增强版）

定义所有类型类、符号表、类型推断错误，以及：
- 基本类型（数、串、布尔、空、任意、未知）
- 复合类型（列表、字典、元组、集合）
- 泛型类型（类型变量、泛型实例、泛型定义）
- 函数类型
- 类类型（含泛型）
- 接口类型
- 代数数据类型（枚举）
- 类型替换与合一

### 类 `Type`

类型基类 —— 所有类型的公共接口

### 函数 `is_subtype_of(self, other: 'Type')`

检查当前类型是否为 other 的子类型

### 函数 `collect_type_vars(self)`

收集类型中出现的所有类型变量（返回 TypeVar 名称集合以保证 hashable）。

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

应用类型变量替换

### 函数 `resolve_type_vars(self)`

### 类 `_SingletonType`

只存在一个实例的类型基类 —— 基本类型都用此实现

### 类 `NumberType`

数字类型（数）

### 类 `StringType`

字符串类型（串）

### 类 `BooleanType`

布尔类型（布尔）

### 类 `NullType`

空值类型（空）

### 函数 `is_subtype_of(self, other: 'Type')`

空值可以赋值给可空类型或任意类型

### 类 `AnyType`

任意类型（任意）—— 未给出类型注解时使用

### 类 `UnknownType`

未知类型（未知）—— 无法静态推断的类型

### 函数 `is_subtype_of(self, other: 'Type')`

### 类 `OptionalTypeWrapper`

可空类型包装（对应 T|空）

### 函数 `is_subtype_of(self, other: 'Type')`

### 函数 `unwrap(self)`

解包装获取内部类型

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `ListType`

列表类型（带元素类型）

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `DictType`

字典类型（带键值类型）

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `TupleType`

元组类型（固定元素类型列表）

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `SetType`

集合类型（带元素类型）

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `FunctionType`

函数类型（参数类型列表 + 返回类型）

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `TypeVar`

泛型类型变量（如 T、U）

    支持可选的上界约束（constraint）。

### 函数 `is_subtype_of(self, other: 'Type')`

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `GenericTypeInstance`

泛型类型实例化（如 列表[数]、映射[T, U]）

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `GenericTypeDef`

泛型类型定义（如 列表<T>）

    仅用于符号表中记录泛型类/接口的定义。

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `ClassType`

类类型（支持泛型实例化 + 接口实现跟踪）

### 函数 `is_subtype_of(self, other: 'Type')`

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `InterfaceType`

接口类型（Phase 1 基础设施）

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `method_signature_matches(self, name: str, actual_ft: 'FunctionType')`

检查接口方法的签名是否与实现匹配。返回 None 表示匹配，返回字符串表示错误描述。

### 类 `EnumType`

枚举/代数数据类型

### 函数 `get_variant_types(self, variant_name: str)`

获取变体的字段类型

### 函数 `has_variant(self, variant_name: str)`

### 函数 `collect_type_vars(self)`

### 类 `FutureType`

Future/异步类型（对应 async 函数的返回值包装）

### 函数 `is_subtype_of(self, other: 'Type')`

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `UnionType`

联合类型：值可以是其中任意一种类型
    
    例如 整数|字符串|空 表示整数或字符串或空值。
    联合类型支持嵌套（自动扁平化）和类型变量替换。

### 函数 `is_subtype_of(self, other: 'Type')`

### 函数 `contains_type(self, t: Type)`

检查是否包含指定类型

### 函数 `collect_type_vars(self)`

### 函数 `apply_substitution(self, subs: 'TypeSubstitution')`

### 函数 `resolve_type_vars(self)`

### 类 `TypeSubstitution`

类型变量 → 类型 的替换映射（Copy-on-Write 优化）

    CoW 机制：clone() 创建子节点共享父节点的映射，O(1) 克隆。
    写入时只修改本地 _mapping，读取时沿 _parent 链向上查找。

### 函数 `get(self, name: str, default: Optional[Type] = None)`

### 函数 `bind(self, name: str, t: Type)`

添加一个绑定，返回自身以支持链式调用

### 函数 `compose(self, other: 'TypeSubstitution')`

组合两个替换：先应用 other，再应用 self。

### 函数 `items(self)`

返回所有条目（本地覆盖父级，父链去重）

### 函数 `clone(self)`

Copy-on-Write: O(1) 克隆，延迟复制映射

### 类 `UnificationError`

类型合一失败

### 函数 `unify(t1: Type, t2: Type, subs: Optional[TypeSubstitution] = None)`

类型合一：尝试找到使 t1 和 t2 等价的类型变量替换。
    使用 _type_id 快速分派替代 isinstance 链。

### 函数 `free_type_vars(t: Type)`

收集类型 t 中的自由类型变量（去重）

### 函数 `apply_substitution_to_type(t: Type, subs: TypeSubstitution)`

对类型应用替换（等价 t.apply_substitution(subs) 的公开入口）

### 类 `TypedSymbol`

带类型信息的符号

### 类 `TypeSymbolTable`

带类型信息的符号表（增强版）

    支持：
    - 作用域嵌套（enter_scope / exit_scope）
    - 泛型参数绑定（define_generic_param / resolve_type_param）
    - 按作用域查找（从内到外）
    - ⭐ 全局符号索引（_global_index）：O(1) 查找函数/类/枚举/trait

### 函数 `enter_scope(self)`

进入新作用域

### 函数 `exit_scope(self)`

退出作用域（同时清理该作用域在全局索引中的符号）

### 函数 `define()`

---- 符号定义 ----

### 函数 `lookup(self, name: str)`

查找符号（优先全局索引 O(1)，再回退到作用域栈遍历）

### 函数 `update_type(self, name: str, data_type: Type)`

更新符号类型

### 函数 `define_generic_param(self, name: str, constraint: Optional[Type] = None)`

定义泛型参数到当前作用域

### 函数 `resolve_type_param(self, name: str)`

解析类型参数

### 函数 `clear_generic_params(self)`

清除泛型参数（在退出泛型作用域时调用）

### 函数 `get_generic_param_names(self)`

获取当前所有泛型参数名称

### 函数 `snapshot(self)`

创建符号表的不可变快照（用于并行推断中的隔离副本）。

        快照包含：
        - 当前作用域栈的浅拷贝（全局作用域）
        - 全局符号索引的拷贝
        - 泛型参数的拷贝

        注意：快照中不包含局部作用域（当前函数体内），因为并行推断的段
        各自拥有独立的局部作用域。

### 函数 `merge_global(self, other: 'TypeSymbolTable')`

合并另一个符号表的全局符号到当前符号表。

        用于并行推断后，将各 worker 推断出的段类型合并回主符号表。
        只合并全局作用域（level 0）中的符号，不合并局部作用域。

### 类 `TypeErrorInference`

类型推断错误

### 类 `TypeParser`

从字符串解析光明类型表达式。

    支持的类型表达式示例：
        数
        串
        列表[数]
        字典[串: 数]
        T                   （类型变量）
        列表[T]             （泛型实例）
        (数, 串) -> 布尔     （函数类型）
        T|空                （可空类型）

### 函数 `parse(self, expr: str)`

解析类型表达式字符串为 Type 对象（带 LRU 缓存）。

---

## 模块: verb_info

**模块说明**: 光明（Light）编程语言 - 动词信息模块

定义动词的元数和修改模式（决策28、决策34）

决策28：元数驱动解析
- 动词声明参数数量，自动收集参数
- 支持无括号函数调用

决策34：主谓/谓宾语义
- mode='modify': 原地修改（列表排序 → 列表.sort()）
- mode='functional': 返回新对象（排序列表 → sorted(列表)）
- mode='both': 两种模式都支持

### 类 `VerbInfo`

动词信息

### 函数 `supports_modify(self)`

是否支持原地修改

### 函数 `supports_functional(self)`

是否支持函数式

### 函数 `get_verb_info(verb: str)`

获取动词信息

### 函数 `get_arity(verb: str)`

获取动词参数数量

### 函数 `get_mode(verb: str)`

获取动词修改模式

### 函数 `is_verb(word: str)`

判断是否为动词

### 函数 `supports_modify(verb: str)`

判断是否支持原地修改

### 函数 `supports_functional(verb: str)`

判断是否支持函数式

### 函数 `get_python_mapping(verb: str)`

获取动词到Python的映射

---

## 模块: wasm_target

### 函数 `compile_light_to_python(source: str)`

将光明代码编译为 Python 代码

### 函数 `compile_to_pyodide(source: str)`

编译光明代码为 Pyodide 可执行格式

    Returns:
        {
            'python_code': str,      # 编译后的 Python 代码
            'loader_js': str,         # Pyodide 加载器 JS 代码
            'error': str or None,     # 编译错误
        }

### 函数 `compile_to_standalone_html(source: str, title: str = "光明程序")`

编译光明代码为独立 HTML 页面（内嵌 Pyodide 运行时）

    Args:
        source: 光明源代码
        title: 页面标题

    Returns:
        完整的 HTML 字符串

### 函数 `compile_to_wasm_json(source: str)`

编译为 JSON 格式的 WASM 包（包含 Python 代码和元数据）

    Returns:
        JSON 字符串

### 类 `DuanWasmRuntime`

---
