# 光明编译器架构设计

## 概述

光明编译器采用经典的编译器架构，包含词法分析、语法分析、语义分析、中间表示生成、代码优化和目标代码生成等阶段。

```
┌─────────────┐
│  源程序(.light)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  词法分析器   │  Lexer
│  lexer.py    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Token流    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  语法分析器   │  Parser
│  parser_stmt.py │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   AST抽象语法树 │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  语义分析器   │  Semantic Analyzer
│  semantic_analyzer.py │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  验证后的AST  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  IR生成器    │  IR Generator
│  ir.py      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  三地址码IR  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  IR优化器    │  IR Optimizer
│  ir.py      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  代码生成器   │  Code Generator
│  codegen_x64.py │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  汇编代码    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  链接器      │  Linker
│  linker.py   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  可执行文件   │
└─────────────┘
```

## 各阶段详细说明

### 1. 词法分析（Lexical Analysis）

**文件**: `src/lexer.py`

词法分析器将源代码文本转换为Token流。

**Token类型**:
- `KEYWORD`: 关键字（遍历、如果、那么等）
- `IDENTIFIER`: 标识符（变量名、函数名）
- `NUMBER`: 数字（整数和小数）
- `STRING`: 字符串
- `OPERATOR`: 运算符
- `PUNCTUATION`: 标点符号（括号、冒号等）
- `NEWLINE`: 换行符
- `INDENT`: 缩进增加
- `DEDENT`: 缩进减少
- `EOF`: 文件结束

### 2. 语法分析（Syntax Analysis）

**文件**: `src/parser_stmt.py`

语法分析器使用递归下降解析器，将Token流转换为抽象语法树（AST）。

**支持的语法结构**:
- 变量声明
- 函数/段落定义
- 赋值语句
- 条件语句（如果/否则）
- 循环（遍历/当）
- 函数调用
- 表达式

### 3. 语义分析（Semantic Analysis）

**文件**: `src/semantic_analyzer.py`

语义分析器进行类型检查和符号表管理。

**职责**:
- 符号表构建和管理
- 类型检查和推断
- 作用域分析
- 错误检测（未定义变量、类型不匹配等）

### 4. 中间表示（Intermediate Representation）

**文件**: `src/ir.py`

使用三地址码（TAC）作为中间表示。

**特点**:
- 简单易优化
- 平台无关
- 便于多种代码生成

**IR结构**:
```
function add_one(n)
entry:
  t0 = 42
  store x = t0
  t1 = load x
  t2 = t1 + 1
  store x = t2
  t3 = load x
  return t3
```

### 5. 代码优化（Optimization）

**文件**: `src/ir.py` (IROptimizer类)

实现多种优化Pass：
- 常量折叠
- 常量传播
- 死代码消除
- 代数简化

### 6. 目标代码生成（Code Generation）

**文件**: `src/codegen_x64.py`

生成x86-64汇编代码。

**支持**:
- 算术指令（ADD、SUB、MUL、DIV）
- 比较指令（CMP）
- 跳转指令（JMP、JE、JNE等）
- 函数调用约定（System V AMD64 ABI）
- 栈帧管理

### 7. 链接（Linking）

**文件**: `src/linker.py`

将目标文件和运行时库链接成可执行文件。

**支持格式**:
- Linux: ELF格式
- Windows: PE/COFF格式
- macOS: Mach-O格式

## 核心数据结构

### AST节点

```python
# src/ast_unified.py
@dataclass
class FunctionDefinition(ASTNode):
    name: str
    parameters: List[Parameter]
    return_type: Type
    body: Block
```

### 类型系统

```python
# src/ast_unified.py
class PrimitiveType(Type):
    kind: str  # 'int', 'float', 'bool', 'string'

class PointerType(Type):
    pointee: Type

class FunctionType(Type):
    return_type: Type
    param_types: List[Type]
```

### 符号表

```python
@dataclass
class Symbol:
    name: str
    type: Type
    scope_id: int
    is_mutable: bool
    offset: Optional[int]  # 栈偏移
```

## 编译流程示例

### 输入
```light
《加一》段(数):
    返回 数 加 1
。

打印(加一(5))
```

### Token流
```
KEYWORD(《) IDENTIFIER(加一) KEYWORD(段) ( 
IDENTIFIER(数) ) : NEWLINE INDENT
KEYWORD(返回) IDENTIFIER(数) OPERATOR(+) NUMBER(1)
NEWLINE DEDENT
...
```

### AST
```
Module:
  FunctionDefinition:
    name: "加一"
    parameters: [Parameter(name: "数")]
    body: [ReturnStatement(value: BinaryOp(Identifier("数"), "+", NumberLiteral(1)))]
  ExpressionStatement:
    expression: FunctionCall(
      callee: Identifier("加一"),
      arguments: [NumberLiteral(5)]
    )
```

### IR
```
function 加一
entry:
  %t0 = add param_0, 1
  return %t0

function main
entry:
  %t1 = call 加一(5)
  call print(%t1)
```

### 汇编代码
```asm
.global 加一
加一:
    push rbp
    mov rbp, rsp
    mov rax, rdi      ; 参数1在rdi
    add rax, 1
    pop rbp
    ret

.global main
main:
    push rbp
    mov rbp, rsp
    mov rdi, 5        ; 参数
    call 加一
    mov rdi, rax
    call print
    xor eax, eax
    pop rbp
    ret
```

## 扩展计划

### 近期
- [ ] 完善标准库实现
- [ ] 添加更多优化Pass
- [ ] 支持ARM64架构
- [ ] 改进错误信息

### 远期
- [ ] IDE支持
- [ ] 调试器
- [ ] 性能分析工具
- [ ] 光明自举（元循环）

## 参考资料

- ["编译原理》](https://en.wikipedia.org/wiki/Compilers:_Principles,_Techniques,_and_Tools) - 龙书
- [LLVM文档](https://llvm.org/docs/)
- [System V AMD64 ABI](https://gitlab.com/x86-psABIs/x86-64-ABI)
