# 从段言到 LLVM —— 段言编译原理与原生编译指南

> **版本：** v6.2  
> **更新日期：** 2026-08-07  
> **文档状态：** 定稿  
> **适用对象：** 对编译器原理感兴趣的有经验开发者

---

## 目录

1. [段言的编译管线](#1-段言的编译管线)
2. [从段言到 Python 字节码（SRC 后端）](#2-从段言到-python-字节码src-后端)
3. [从段言到 LLVM IR（Typed 后端）](#3-从段言到-llvm-irtyped-后端)
4. [段言代码的 LLVM IR 对照速查](#4-段言代码的-llvm-ir-对照速查)
5. [运行时库与运行时机制](#5-运行时库与运行时机制)
6. [性能优化策略](#6-性能优化策略)
7. [实战：编译一个段言程序为独立 EXE](#7-实战编译一个段言程序为独立-exe)
8. [常见问题](#8-常见问题)

---

## 1. 段言的编译管线

段言采用**双后端架构**：开发阶段使用 SRC 后端（编译为 Python 字节码）以获得快速迭代，生产阶段使用 LLVM 后端（编译为原生机器码）以获得极致性能。

### 1.1 完整编译流程

```
.duan 源文件
    │
    ▼
┌──────────────────┐
│    词法分析      │  Lexer (lexer.py)
│  Token 化        │  → Token 流: [关键字, 标识符, 字面量, ...]
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    语法分析      │  DuanParser v3 (duan_parser_v3)
│  AST 构建        │  → v3 AST (抽象语法树)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  AST 适配        │  AstAdapter (compiler.py)
│  统一 AST        │  → 统一 AST (后端无关中间表示)
└────────┬─────────┘
         │
         ├───────────────────────┬──────────────────────┐
         │                       │                      │
         ▼                       ▼                      ▼
┌──────────────────┐  ┌──────────────────────┐  ┌──────────────────┐
│  SRC 后端        │  │  TypedLLVMCodeGen    │  │  StringCodeGen   │
│  → Python 字节码  │  │  → LLVM IR (.ll)    │  │  → LLVM IR (.ll) │
│  → CPython 执行   │  │  → clang 优化/编译   │  │  → clang 编译    │
│  (开发模式)       │  │  → 机器码 (.exe/.o)  │  │  (旧版, 不推荐)   │
└──────────────────┘  └────────┬─────────────┘  └──────────────────┘
                               │
                               ▼
                      ┌──────────────────┐
                      │  clang 链接       │
                      │  + 运行时库       │
                      │  → 原生可执行文件  │
                      └──────────────────┘
```

### 1.2 双后端决策树

```
源代码 → 是否生产部署？
         ├── 否 → SRC 后端（Python 字节码，秒级启动）
         └── 是 → 是否需要极致性能？
                  ├── 是 → LLVM Typed 后端（原生机器码，10-50x 加速）
                  └── 否 → SRC 后端（开发/调试更方便）
```

### 1.3 关键组件一览

| 组件 | 文件 | 职责 |
|------|------|------|
| Lexer | `lexer.py` | 词法分析，将源码切分为 Token 流 |
| DuanParser v3 | `duan_parser_v3` | 语法分析，构建 v3 AST |
| AstAdapter | `compiler.py` | 将 v3 AST 适配为统一 AST |
| SrcCodeGen | `codegen.py` | 生成 Python 字节码（SRC 后端） |
| TypedLLVMCodeGen | `codegen_typed.py` | 生成 LLVM IR（Typed 后端） |
| StringCodeGen | `codegen_string.py` | 生成 LLVM IR（String 后端，旧版） |
| Compiler | `compiler.py` | 编译入口，协调整个流水线 |
| Runtime | `runtime_typed.c` | C 实现的运行时库 |

---

## 2. 从段言到 Python 字节码（SRC 后端）

### 2.1 工作原理

SRC 后端将段言源码编译为 Python 字节码（`.pyc`），由 CPython 虚拟机执行。这是段言的默认开发模式。

### 2.2 编译流程

```
段言源码 → 词法分析 → 语法分析 → AST → SrcCodeGen → Python AST → compile() → .pyc → CPython 执行
```

### 2.3 关键特性

- **启动速度**：秒级，无需等待 clang 编译
- **调试体验**：完整的 Python 回溯栈，可直接使用 Python 调试器
- **生态桥接**：段言代码可以直接调用 Python 库（numpy、pandas、requests 等）
- **性能特征**：受限于 CPython 解释执行，适合开发阶段和性能不敏感的场景

### 2.4 代码示例

```段言
# hello.duan
打印 "你好，世界！"

设 名字 为 输入("请输入你的名字：")
打印 "你好，" + 名字
```

SRC 后端将其编译为等价于以下 Python 字节码：

```python
print("你好，世界！")
name = input("请输入你的名字：")
print("你好，" + name)
```

### 2.5 使用方式

```bash
# 默认使用 SRC 后端
duan run hello.duan

# 显式指定 SRC 后端
duan run hello.duan --backend src

# 编译为 Python 字节码文件
duan build hello.duan -o hello.pyc --backend src
```

---

## 3. 从段言到 LLVM IR（Typed 后端）

### 3.1 工作原理

Typed 后端是段言 LLVM 编译的主力模式。它将段言源码编译为 LLVM IR，然后通过 clang 编译为目标平台的原生机器码。

### 3.2 核心设计

#### 3.2.1 DuanValue 类型系统

所有段言值在 LLVM IR 中统一表示为 `DuanValue` 结构体，通过指针传递：

```llvm
; LLVM IR 定义（与 C 端布局完全匹配）
%struct.DuanValue = type {
    i32,        ; type: 0=NULL 1=INT 2=FLOAT 3=STR 4=LIST 5=BOOL
    i64,        ; i64_val: 整数
    double,     ; f64_val: 浮点数
    ptr,        ; str_val: 字符串指针
    i32,        ; bool_val: 布尔值
    i32,        ; list_size: 列表元素数
    i32,        ; list_capacity: 列表容量
    ptr         ; list_data: 列表数据指针
}
```

#### 3.2.2 指针传递调用约定

所有段言函数（段落）和类方法统一使用指针传递：

```llvm
; 段落函数签名
define void @_seg_函数名(ptr %result, ptr %args, i32 %num_args)

; 类方法签名（实例方法）
define void @_method_类名_方法名(ptr %result, ptr %self, ptr %args, i32 %num_args)
```

#### 3.2.3 代码生成核心

- **寄存器分配**：简单的递增计数器，生成 `%1`, `%2`, `%3`, ... 形式的虚拟寄存器
- **标签管理**：`prefix_N` 格式，如 `entry_1`, `if_then_2`, `loop_body_3`
- **Alloca 延迟生成**：在函数入口块统一生成 alloca 指令，满足 LLVM 的 SSA 要求

### 3.3 Typed 模式 vs String 模式

| 维度 | String 模式（旧版） | Typed 模式（推荐） |
|------|-------------------|-------------------|
| 类型存储 | 所有值存为 i8* 字符串 | DuanValue 结构体（原生类型） |
| 算术运算 | atoi → 运算 → itoa | 直接 i64/double 指令 |
| 性能 | 较差 | 优异（接近 C） |
| 传递方式 | 值传递 | 指针传递（避免 ABI 不兼容） |
| 状态 | 已废弃，仅用于兼容 | 当前主要开发方向 |

### 3.4 编译入口

```python
from llvm.compiler import compile_duan_typed

# 编译单文件
exe_path = compile_duan_typed('hello.duan', verbose=True)
print(f'编译成功: {exe_path}')

# 指定输出路径
compile_duan_typed('hello.duan', output_path='dist/hello.exe')

# 设置优化级别
compile_duan_typed('hello.duan', opt_level='-O2')
```

---

## 4. 段言代码的 LLVM IR 对照速查

本章提供 12 个段言代码片段及其对应的 LLVM IR，帮助理解段言到 LLVM 的编译映射。

### 4.1 变量赋值

**段言代码：**
```段言
设 x 为 10
```

**LLVM IR：**
```llvm
; 分配栈空间
%x_slot = alloca %struct.DuanValue

; 构造 DuanValue（INT 类型）
%type_ptr = getelementptr %struct.DuanValue, ptr %x_slot, i32 0, i32 0
store i32 1, ptr %type_ptr          ; type = INT (1)
%i64_ptr = getelementptr %struct.DuanValue, ptr %x_slot, i32 0, i32 1
store i64 10, ptr %i64_ptr          ; i64_val = 10
```

**类型优化后的 LLVM IR（当编译器知道 x 为 INT 时）：**
```llvm
%x_slot = alloca %struct.DuanValue
%type_ptr = getelementptr %struct.DuanValue, ptr %x_slot, i32 0, i32 0
store i32 1, ptr %type_ptr
%i64_ptr = getelementptr %struct.DuanValue, ptr %x_slot, i32 0, i32 1
store i64 10, ptr %i64_ptr
; 省去了对 dv_int() 运行时函数的调用
```

### 4.2 算术运算

**段言代码：**
```段言
设 结果 为 x 加 y
```

**LLVM IR（未优化，调用运行时函数）：**
```llvm
; 调用运行时 dv_add
call void @dv_add(ptr %result_slot, ptr %x_slot, ptr %y_slot)
```

**LLVM IR（类型优化，已知均为 INT）：**
```llvm
; 提取 x 的 i64 值
%x_i64 = extractvalue %struct.DuanValue %x_dv, 1
; 提取 y 的 i64 值
%y_i64 = extractvalue %struct.DuanValue %y_dv, 1
; 原生 add 指令
%sum = add i64 %x_i64, %y_i64
; 快速构造 DuanValue 结果
%type_ptr = getelementptr %struct.DuanValue, ptr %result_slot, i32 0, i32 0
store i32 1, ptr %type_ptr
%i64_ptr = getelementptr %struct.DuanValue, ptr %result_slot, i32 0, i32 1
store i64 %sum, ptr %i64_ptr
```

**LLVM IR（类型优化，已知均为 FLOAT）：**
```llvm
%x_f64 = extractvalue %struct.DuanValue %x_dv, 2
%y_f64 = extractvalue %struct.DuanValue %y_dv, 2
%sum = fadd double %x_f64, %y_f64
```

### 4.3 条件判断

**段言代码：**
```段言
如果 x 大于 0：
    打印 "正数"
```

**LLVM IR（类型优化，已知 x 为 INT）：**
```llvm
; 提取 x 的 i64 值
%x_i64 = extractvalue %struct.DuanValue %x_dv, 1
; 与 0 比较
%cmp = icmp sgt i64 %x_i64, 0
br i1 %cmp, label %if_then_1, label %if_end_2

if_then_1:
  ; 构造 "正数" 字符串
  call void @dv_println(ptr @str_正数)
  br label %if_end_2

if_end_2:
  ; 继续执行
```

**未优化时（调用运行时比较函数）：**
```llvm
%cmp_dv = alloca %struct.DuanValue
call void @dv_gt(ptr %cmp_dv, ptr %x_slot, ptr %zero_slot)
; 提取布尔字段
%bool_val = extractvalue %struct.DuanValue %cmp_dv, 4
%i1_val = trunc i32 %bool_val to i1
br i1 %i1_val, label %if_then_1, label %if_end_2
```

### 4.4 函数调用

**段言代码：**
```段言
打印 "你好，世界！"
```

**LLVM IR：**
```llvm
; 声明运行时函数
declare void @dv_println(ptr)

; 调用
call void @dv_println(ptr @str_你好世界)
```

### 4.5 自定义函数（段落）

**段言代码：**
```段言
段落 加法 接收 a, b：
    返回 a 加 b
```

**LLVM IR：**
```llvm
define void @_seg_加法(ptr %result, ptr %args, i32 %num_args) {
entry:
  ; 获取参数
  %a_ptr = getelementptr %struct.DuanValue, ptr %args, i32 0
  %b_ptr = getelementptr %struct.DuanValue, ptr %args, i32 1
  
  ; 调用 dv_add
  call void @dv_add(ptr %result, ptr %a_ptr, ptr %b_ptr)
  ret void
}
```

**调用方：**
```llvm
; 在栈上分配参数数组
%args = alloca [2 x %struct.DuanValue]
; 填充参数
; ...
; 调用段落
%result = alloca %struct.DuanValue
call void @_seg_加法(ptr %result, ptr %args, i32 2)
```

### 4.6 循环（遍历）

**段言代码：**
```段言
遍历 i 从 1 到 10：
    打印 i
```

**LLVM IR：**
```llvm
; 初始化
%i_slot = alloca %struct.DuanValue
%i_i64 = alloca i64
store i64 1, ptr %i_i64
br label %loop_cond_1

loop_cond_1:
  %i_val = load i64, ptr %i_i64
  %done = icmp sgt i64 %i_val, 10
  br i1 %done, label %loop_end_3, label %loop_body_2

loop_body_2:
  ; 构造 DuanValue 用于打印
  %type_ptr = getelementptr %struct.DuanValue, ptr %i_slot, i32 0, i32 0
  store i32 1, ptr %type_ptr
  %i64_ptr = getelementptr %struct.DuanValue, ptr %i_slot, i32 0, i32 1
  store i64 %i_val, ptr %i64_ptr
  call void @dv_println(ptr %i_slot)
  ; i++
  %next = add i64 %i_val, 1
  store i64 %next, ptr %i_i64
  br label %loop_cond_1

loop_end_3:
  ; 继续执行
```

### 4.7 循环（当）

**段言代码：**
```段言
当 条件：
    执行操作
```

**LLVM IR：**
```llvm
br label %while_cond_1

while_cond_1:
  ; 评估条件表达式 -> %cond_i1
  %cond_val = extractvalue %struct.DuanValue %cond_dv, 4
  %cond_i1 = trunc i32 %cond_val to i1
  br i1 %cond_i1, label %while_body_2, label %while_end_3

while_body_2:
  ; 执行循环体
  call void @_seg_执行操作(ptr %result, ptr %args, i32 %num_args)
  br label %while_cond_1

while_end_3:
  ; 继续执行
```

### 4.8 类与方法

**段言代码：**
```段言
类 动物：
    构造 接收 名字：
        设 己.名字 为 名字
    
    段落 叫 接收 次数：
        遍历 i 从 1 到 次数：
            打印 己.名字
```

**LLVM IR（vtable dispatch）：**
```llvm
; 构造方法
define void @_method_动物_构造(ptr %result, ptr %self, ptr %args, i32 %num_args) {
  %name_ptr = getelementptr %struct.DuanValue, ptr %args, i32 0
  call void @dv_class_set_member(ptr %self, ptr @str_名字, ptr %name_ptr)
  ret void
}

; 实例方法
define void @_method_动物_叫(ptr %result, ptr %self, ptr %args, i32 %num_args) {
  ; 获取 self.名字 并打印
  %name_val = alloca %struct.DuanValue
  call void @dv_class_get_member(ptr %name_val, ptr %self, ptr @str_名字)
  call void @dv_println(ptr %name_val)
  ret void
}

; 方法表（vtable）
@_vtable_动物 = constant [2 x ptr] [
  ptr @_method_动物_构造,
  ptr @_method_动物_叫
]
```

### 4.9 异常处理

**段言代码：**
```段言
尝试：
    设 结果 为 10 除以 0
捕获 e：
    打印 "出错了：" + e
最终：
    打印 "清理资源"
结束。
```

**LLVM IR（setjmp/longjmp 模式）：**
```llvm
; Windows x64 路径
%jmp_buf = alloca [32 x i8]           ; jmp_buf 大小
%frame_addr = call ptr @llvm.frameaddress.p0(i32 0)
%setjmp_result = call i32 @_setjmp(ptr %jmp_buf, ptr %frame_addr)
%is_exception = icmp ne i32 %setjmp_result, 0
br i1 %is_exception, label %catch_dispatch_1, label %try_body_1

try_body_1:
  ; 尝试块：执行 10 除以 0
  call void @dv_div(ptr %result, ptr %ten, ptr %zero)
  ; 成功，跳过 catch
  call void @dv_try_pop()
  br label %finally_1

catch_dispatch_1:
  ; 获取异常消息
  %exc_str = call ptr @dv_get_exception_str()
  ; 构造 DuanValue 赋值给 e
  ; ...
  call void @dv_try_pop()
  br label %catch_body_1

catch_body_1:
  call void @dv_println(ptr %e_dv)
  br label %finally_1

finally_1:
  call void @dv_println(ptr @str_清理资源)
  ; 继续执行
```

### 4.10 列表操作

**段言代码：**
```段言
设 列表 为 [1, 2, 3]
列表追加(列表, 4)
```

**LLVM IR：**
```llvm
; 创建列表
%list = call ptr @dv_list_new()
; 追加元素
call void @dv_list_append(ptr %list, ptr %elem_1_ptr)
call void @dv_list_append(ptr %list, ptr %elem_2_ptr)
call void @dv_list_append(ptr %list, ptr %elem_3_ptr)
; 再追加一个
call void @dv_list_append(ptr %list, ptr %elem_4_ptr)

; 包装为 DuanValue
store i32 4, ptr %list_type_ptr    ; type = LIST
store ptr %list, ptr %list_data_ptr ; list_data
```

### 4.11 异步/协程

**段言代码：**
```段言
异步 段落 获取数据 接收 URL：
    设 响应 为 等待 请求(URL)
    返回 响应.正文
```

**LLVM IR（两阶段状态机模式）：**
```llvm
; 协程函数
define void @_coro_获取数据(ptr %result, ptr %coro, ptr %args, i32 %num_args) {
entry:
  ; 加载恢复点
  %rp_ptr = getelementptr %struct.DuanCoroutine, ptr %coro, i32 0, i32 1
  %rp = load i32, ptr %rp_ptr
  ; Duff's device 状态机
  switch i32 %rp, label %coro_end [
    i32 0, label %resume_0
    i32 1, label %resume_1
  ]

resume_0:
  ; 调用异步请求
  %coro2 = call ptr @_seg_请求(ptr %args, i32 1)
  ; 设置恢复点 = 1
  store i32 1, ptr %rp_ptr
  ; 挂起协程
  call void @dv_coro_await(ptr %coro, ptr %coro2)
  ret void

resume_1:
  ; 获取 await 结果
  call void @dv_coro_get_await_result(ptr %result, ptr %coro)
  ret void

coro_end:
  ret void
}

; 包装函数（异步段落）
define void @_seg_获取数据(ptr %result, ptr %args, i32 %num_args) {
  %coro = call ptr @dv_coro_create(ptr @_coro_获取数据, ptr %args, i32 %num_args, i32 %num_locals)
  ; 将协程指针存储为 DuanValue
  store ptr %coro, ptr %result_str_ptr
  ret void
}
```

### 4.12 模块导入与导出

**段言代码：**
```段言
# 导出
导出 阶乘

段落 阶乘 接收 n：
    如果 n 小于等于 1：
        返回 1
    返回 n 乘 阶乘(n 减 1)
```

**LLVM IR：**
```llvm
; 定义函数
define void @_seg_阶乘(ptr %result, ptr %args, i32 %num_args) {
  ; ... 函数体 ...
}

; 导出别名
@_seg__数学工具_阶乘 = alias void (ptr, ptr, i32), void (ptr, ptr, i32)* @_seg_阶乘
```

**调用方（另一个模块）：**
```llvm
; 外部声明
declare void @_seg__数学工具_阶乘(ptr, ptr, i32)

; 调用
call void @_seg__数学工具_阶乘(ptr %result, ptr %args, i32 1)
```

### 4.13 布尔运算

**段言代码：**
```段言
如果 x 大于 0 且 x 小于 100：
    打印 "范围内"
```

**LLVM IR：**
```llvm
%x_i64 = extractvalue %struct.DuanValue %x_dv, 1
%gt0 = icmp sgt i64 %x_i64, 0
%lt100 = icmp slt i64 %x_i64, 100
%and = and i1 %gt0, %lt100
br i1 %and, label %if_then_1, label %if_end_2
```

### 4.14 对照表汇总

| 段言语法 | LLVM IR 模式 | 说明 |
|---------|-------------|------|
| `设 x 为 10` | `alloca` + `store` | 栈上分配 + 构造 DuanValue |
| `x 加 y` | `add` / `fadd` 或 `call @dv_add` | 类型已知时用原生指令 |
| `x 大于 y` | `icmp` / `fcmp` 或 `call @dv_gt` | 类型已知时用原生比较 |
| `如果 ...：` | `br i1 %cond` | 条件分支 |
| `段落 名(...)` | `define void @_seg_名(ptr, ptr, i32)` | 指针传递调用约定 |
| `遍历 i 从 1 到 10` | `phi` + `br` 循环 | 计数器 + 条件分支 |
| `当 条件：` | `br` → `br i1` 循环 | 条件分支循环 |
| `类 名：` | `vtable` + 方法表 | 虚函数表 + dispatch |
| `尝试：` | `setjmp`/`longjmp` | 非局部跳转异常处理 |
| `等待 协程` | `switch` 状态机 | Duff's device 协程 |
| `列表追加` | `call @dv_list_append` | 动态数组操作 |
| `导出 名` | `alias` | 符号导出别名 |

---

## 5. 运行时库与运行时机制

### 5.1 运行时库文件结构

| 文件 | 说明 | 用途 |
|------|------|------|
| `runtime_typed.c` | 类型化运行时库（C 实现） | Typed 后端 |
| `runtime.c` | String 模式运行时库 | 旧版 String 后端 |

### 5.2 DuanValue 结构体

```c
typedef struct DuanValue {
    int type;              /* 0=NULL 1=INT 2=FLOAT 3=STR 4=LIST 5=BOOL 6=CLASS */
    int64_t i64;           /* INT 类型的值 */
    double f64;            /* FLOAT 类型的值 */
    char* str;             /* STR 类型的字符串 / 对象的序列化表示 */
    int boolean;           /* BOOL 类型 */
    /* LIST 类型专用字段 */
    int list_size;         /* 当前元素数量 */
    int list_capacity;     /* 分配的数组容量 */
    struct DuanValue** list_data; /* 元素指针数组 */
} DuanValue;
```

**类型标记对照：**

| 值 | 常量 | 段言类型 | 有效字段 |
|----|------|---------|---------|
| 0 | DV_NULL | 空 | — |
| 1 | DV_INT | 数/整数 | `i64` |
| 2 | DV_FLOAT | 浮点数/小数 | `f64` |
| 3 | DV_STR | 串/字符串 | `str` |
| 4 | DV_LIST | 列表/数组 | `list_size`, `list_capacity`, `list_data` |
| 5 | DV_BOOL | 布尔 | `boolean` |
| 6 | DV_CLASS | 类/对象 | `str`（序列化表示） |

### 5.3 运行时函数分类

#### 值构造器

| 函数 | 签名 | 说明 |
|------|------|------|
| `dv_null` | `void dv_null(DuanValue* result)` | 构造空值 |
| `dv_int` | `void dv_int(DuanValue* result, int64_t v)` | 构造整数 |
| `dv_float` | `void dv_float(DuanValue* result, double v)` | 构造浮点数 |
| `dv_str` | `void dv_str(DuanValue* result, const char* v)` | 构造字符串 |
| `dv_bool` | `void dv_bool(DuanValue* result, int v)` | 构造布尔值 |

#### 算术运算

| 函数 | 签名 | 说明 |
|------|------|------|
| `dv_add` | `void dv_add(DuanValue* r, DuanValue* a, DuanValue* b)` | 加法 |
| `dv_sub` | `void dv_sub(DuanValue* r, DuanValue* a, DuanValue* b)` | 减法 |
| `dv_mul` | `void dv_mul(DuanValue* r, DuanValue* a, DuanValue* b)` | 乘法 |
| `dv_div` | `void dv_div(DuanValue* r, DuanValue* a, DuanValue* b)` | 除法 |

#### 比较运算

| 函数 | 签名 | 说明 |
|------|------|------|
| `dv_eq` | `void dv_eq(DuanValue* r, DuanValue* a, DuanValue* b)` | 等于 |
| `dv_lt` | `void dv_lt(DuanValue* r, DuanValue* a, DuanValue* b)` | 小于 |
| `dv_gt` | `void dv_gt(DuanValue* r, DuanValue* a, DuanValue* b)` | 大于 |
| `dv_le` | `void dv_le(DuanValue* r, DuanValue* a, DuanValue* b)` | 小于等于 |
| `dv_ge` | `void dv_ge(DuanValue* r, DuanValue* a, DuanValue* b)` | 大于等于 |

#### I/O 操作

| 函数 | 签名 | 说明 |
|------|------|------|
| `dv_print` | `void dv_print(DuanValue* v)` | 打印（不换行） |
| `dv_println` | `void dv_println(DuanValue* v)` | 打印（换行） |
| `dv_input` | `void dv_input(DuanValue* r, DuanValue* prompt)` | 读取输入 |

#### 字符串操作

| 函数 | 说明 |
|------|------|
| `dv_concat` | 字符串拼接 |
| `dv_str_len` | 获取字符串长度 |
| `dv_substr` | 取子串 |
| `dv_str_find` | 查找子串 |
| `dv_str_replace` | 替换子串 |
| `dv_str_split` | 分割字符串 |
| `dv_str_upper` / `dv_str_lower` | 大小写转换 |
| `dv_str_trim` | 去除空白 |

#### 列表操作

| 函数 | 说明 |
|------|------|
| `dv_list_new` | 创建空列表（初始容量 4） |
| `dv_list_len` | 返回列表长度（O(1)） |
| `dv_list_get` | 按索引访问元素（O(1)） |
| `dv_list_append` | 追加元素（自动扩容） |
| `dv_list_insert` | 插入元素 |
| `dv_list_remove` | 删除元素 |
| `dv_list_reverse` | 反转列表 |
| `dv_list_sort` | 排序 |
| `dv_list_clear` | 清空列表 |

#### 异常处理

| 函数 | 说明 |
|------|------|
| `dv_try_push` | 推入 try 层级，返回 jmp_buf 指针 |
| `dv_try_pop` | 弹出 try 层级 |
| `dv_throw` | 抛出异常（longjmp） |
| `dv_get_exception_str` | 获取异常消息 |
| `dv_clear_exception` | 清除异常状态 |

#### 协程调度

| 函数 | 说明 |
|------|------|
| `dv_coro_create` | 创建协程 |
| `dv_coro_resume` | 恢复执行 |
| `dv_coro_await` | 挂起等待 |
| `dv_coro_run_to_completion` | 运行到完成 |
| `dv_coro_set_result` | 设置结果并完成 Future |
| `dv_coro_get_await_result` | 获取 await 结果 |
| `dv_coro_get_local` | 获取局部变量指针 |
| `dv_coro_get_arg` | 获取参数指针 |
| `dv_future_create` | 创建 Future |
| `dv_future_complete` | 完成 Future，唤醒等待者 |
| `dv_scheduler_run` | 运行调度器 |

### 5.4 内存管理机制

段言的运行时库使用 `malloc`/`free` 手动管理内存，没有自动垃圾回收。

**内存分配策略：**

- **DuanValue 结构体**：通常在 LLVM IR 中通过 `alloca` 在栈上分配
- **字符串数据**：堆分配，通过 `dv_str` 构造时复制
- **列表数据**：动态数组，自动扩容（初始容量 4，每次扩容翻倍）
- **协程局部变量**：堆分配，跨 await 点持久化

**内存生命周期：**

```
alloca（栈上分配，函数返回自动释放）
    ├── 基本类型（INT/FLOAT/BOOL）：值直接存储在结构体字段中
    ├── 字符串（STR）：str 指向堆内存，需要在适当时机 free
    └── 列表（LIST）：list_data 指向堆内存数组，需要逐元素 free
```

> **注意**：当前没有自动垃圾回收机制，字符串和列表的堆内存需要手动管理。未来计划引入引用计数 GC。

### 5.5 异常传播机制

段言的异常处理基于 C 标准库的 `setjmp`/`longjmp` 实现非局部跳转。

**跨平台适配：**

| 平台 | 函数签名 | 说明 |
|------|---------|------|
| Windows x64 | `int _setjmp(jmp_buf buf, void* frame_addr)` | 需要帧地址参数 |
| Linux/macOS | `int setjmp(jmp_buf buf)` | 标准 C 签名 |

**嵌套 try 层级管理：**

```c
#define MAX_TRY_DEPTH 16
static jmp_buf __dv_jmp_bufs[MAX_TRY_DEPTH];
static int __dv_try_level = -1;
static char __dv_exception_str[1024];
```

**控制流：**

```
入口 → dv_try_push() → setjmp()
  ├── 返回 0 → 执行 try 块
  │   ├── 正常完成 → dv_try_pop() → finally（如有）→ 结束
  │   └── 抛出异常 → longjmp() → setjmp 返回非零
  └── 返回非零 → catch 分派
      ├── 有 catch → 执行 catch 块 → finally → 结束
      └── 无 catch → finally → 重新抛出
```

### 5.6 协程调度机制

段言的协程采用 **Duff's device** 模式，通过在生成的 LLVM IR 中嵌入 `switch(resume_point)` 状态机实现协程的挂起与恢复。

**DuanCoroutine 结构体：**

```c
typedef struct DuanCoroutine {
    int state;              // DV_CORO_READY/SUSPENDED/DONE/ERROR
    int resume_point;       // 恢复点（Duff's device 的 case 标签）
    DuanCoroFunc func;      // 协程函数指针
    DuanValue result;       // 返回值
    DuanValue* args;        // 参数数组（堆分配）
    int num_args;           // 参数数量
    DuanValue* locals;      // 局部变量数组（堆分配，跨 await 持久化）
    int num_locals;         // 局部变量数量
    struct DuanFuture* waiting_for;   // 等待的 Future
    struct DuanFuture* future;         // 关联的 Future
    struct DuanCoroutine* next;        // 调度器链表指针
} DuanCoroutine;
```

**调度器模型：**

```
可运行队列（单链表）
    ↓
调度循环：从队列头部取出协程 → dv_coro_resume() 执行一步
    ↓
协程遇到 await → 挂起到 Future 的 waiters 链表
    ↓
Future 完成 → 批量唤醒所有等待协程 → 放回可运行队列
    ↓
队列为空 → 调度结束
```

---

## 6. 性能优化策略

### 6.1 编译器优化级别

段言 LLVM 后端支持多级优化，通过 clang 编译时传递优化标志：

| 级别 | 标志 | 说明 | 适用场景 |
|------|------|------|---------|
| O0 | `-O0` | 无优化，编译最快 | 调试、开发 |
| O1 | `-O1` | 基本优化，平衡编译时间和代码质量 | 日常构建 |
| O2 | `-O2` | 标准优化（默认），性能好 | 发布构建 |
| O3 | `-O3` | 激进优化，可能增加代码体积 | 性能关键场景 |

**典型用法：**

```bash
# 默认使用 -O2
duan build hello.duan -o hello.exe

# 指定优化级别
duan build hello.duan -o hello.exe --opt -O3

# 调试模式，无优化
duan build hello.duan -o hello_debug.exe --opt -O0
```

### 6.2 类型信息优化（Level 8）

这是段言编译器中最重要的优化手段。当编译器能确定操作数的类型时，直接使用 LLVM 原生指令替代运行时函数调用，消除函数调用开销和类型分派开销。

**优化效果对比：**

| 操作 | 未优化 | 类型优化后 |
|------|--------|-----------|
| `x 加 y`（INT） | `call @dv_add` → 类型检查 → 提取值 → 运算 → 包装结果 | `add i64` → 直接构造 DuanValue |
| `x 大于 0`（INT） | `call @dv_gt` → 类型分派 → 比较 | `icmp sgt i64` |
| `如果 x：`（BOOL） | `call @dv_eq` → 判断是否为空 | `extractvalue → trunc to i1` |

**类型追踪系统：**

```python
# 代码生成器维护变量类型映射表
self._var_types: Dict[str, int] = {
    '甲': DV_INT,      # 设 甲 为 10 → 推断为 INT
    '乙': DV_FLOAT,    # 设 乙 为 3.14 → 推断为 FLOAT
    '丙': DV_STR,      # 设 丙 为 "你好" → 推断为 STR
    '丁': DV_BOOL,     # 设 丁 为 真 → 推断为 BOOL
}
```

**类型推断规则：**

| 表达式 | 推断类型 |
|--------|---------|
| 数字字面量（含小数点） | FLOAT |
| 数字字面量（无小数点） | INT |
| 字符串字面量 | STRING |
| 布尔字面量 | BOOL |
| 标识符 | 查询变量类型表 |
| 算术运算（INT ⊕ INT） | INT（除法除外） |
| 算术运算（含 FLOAT） | FLOAT |
| 比较运算 | BOOL |

### 6.3 增量编译

段言支持增量编译，缓存已编译的模块，避免重复编译：

```
编译 hello.duan（依赖 math.duan、io.duan）
    │
    ├── math.duan → 编译为 math.ll → 缓存
    ├── io.duan   → 编译为 io.ll   → 缓存
    └── hello.duan → 编译为 hello.ll
        │
        如果 math.duan 未修改 → 直接使用缓存的 math.ll
        如果 math.duan 已修改 → 重新编译并更新缓存
```

### 6.4 缓存系统

**缓存策略：**

- **缓存键**：源文件内容哈希（SHA256）
- **缓存内容**：编译生成的 LLVM IR（`.ll` 文件）
- **缓存位置**：`.duan_cache/` 目录
- **失效条件**：源文件内容变化、依赖模块变化

### 6.5 链接时优化（LTO）

LTO 允许 LLVM 在链接阶段对整个程序进行跨模块优化：

```bash
# 启用 LTO
duan build hello.duan -o hello.exe --opt -flto

# LTO 的优势：
# - 跨模块函数内联
# - 死代码消除（删除未使用的导出函数）
# - 常量传播跨模块边界
# - 减少代码体积
```

### 6.6 交叉编译

段言支持为目标平台编译原生可执行文件：

```bash
# 为 Linux x64 编译（在 Windows 上）
duan build hello.duan -o hello_linux --target linux

# 为 macOS x64 编译
duan build hello.duan -o hello_macos --target darwin

# 指定目标架构
duan build hello.duan -o hello_arm64 --target linux --arch arm64
```

**交叉编译原理：**

```
段言源码 → LLVM IR（平台无关）
    → 使用目标平台的 clang 交叉编译器
    → 链接目标平台的运行时库
    → 生成目标平台的可执行文件
```

### 6.7 优化建议速查

| 场景 | 建议 |
|------|------|
| 开发调试 | `-O0`，使用 SRC 后端 |
| 日常构建 | `-O2`，默认配置 |
| 性能关键 | `-O3` + 类型注解 |
| 最小体积 | `-O2` + `-flto` + `-Os` |
| 跨平台 | 指定 `--target` 和 `--arch` |
| 大型项目 | 启用增量编译 + 缓存 |
| 数学密集 | 使用类型注解（`数`/`浮点数`）触发类型优化 |
| 字符串密集 | 使用运行时函数，类型优化收益有限 |

---

## 7. 实战：编译一个段言程序为独立 EXE

### 7.1 最简单的示例

**创建源码：**
```段言
# hello.duan
打印 "你好，世界！"
```

**编译为独立 EXE：**
```bash
# 使用默认配置（LLVM 后端）
duan build hello.duan -o hello.exe

# 或显式指定 LLVM 后端
duan build hello.duan -o hello --backend llvm

# 运行
./hello.exe
# 输出：你好，世界！
```

### 7.2 完整项目示例

**项目结构：**
```
my_project/
├── main.duan
├── math_tools.duan
├── io_utils.duan
└── package.toml
```

**main.duan：**
```段言
从 math_tools 导入 阶乘
从 io_utils 导入 提示输入

段落 主程序：
    设 输入值 为 提示输入("请输入一个数字：")
    设 数字 为 转整数(输入值)
    设 结果 为 阶乘(数字)
    打印 "阶乘结果是：" + 转字符串(结果)

主程序()
```

**math_tools.duan：**
```段言
导出 阶乘

段落 阶乘 接收 n：
    如果 n 小于等于 1：
        返回 1
    返回 n 乘 阶乘(n 减 1)
```

**io_utils.duan：**
```段言
导出 提示输入

段落 提示输入 接收 提示文本：
    打印 提示文本
    返回 输入("")
```

**编译步骤：**
```bash
# 方式一：直接编译主文件（自动解析依赖）
duan build main.duan -o my_app.exe

# 方式二：使用包管理器编译
duan build --package my_project -o my_app.exe

# 方式三：分步编译（用于调试）
duan build main.duan -o main.ll --backend llvm --emit-ir
clang -O2 main.ll runtime_typed.c -o my_app.exe
```

### 7.3 完整编译流水线

```
1. 源码准备阶段
   ├── 编写 .duan 源文件
   ├── 配置 package.toml（可选）
   └── 确保运行时库在搜索路径中

2. 编译阶段
   ├── 词法分析：源码 → Token 流
   ├── 语法分析：Token 流 → v3 AST
   ├── AST 适配：v3 AST → 统一 AST
   └── 代码生成：统一 AST → LLVM IR

3. 链接阶段
   ├── 合并所有模块的 LLVM IR
   ├── 链接运行时库（runtime_typed.c）
   ├── clang 优化（-O2）
   └── 输出可执行文件

4. 部署阶段
   ├── EXE 是独立可执行文件
   ├── 无需携带运行时解释器
   └── 可直接分发给最终用户
```

### 7.4 查看生成的 LLVM IR

```bash
# 只生成 LLVM IR，不编译为可执行文件
duan build hello.duan -o hello.ll --backend llvm --emit-ir

# 查看生成的 IR
cat hello.ll
```

### 7.5 调试编译过程

```bash
# 输出详细编译日志
duan build hello.duan -o hello.exe --verbose

# 保留中间文件
duan build hello.duan -o hello.exe --keep-temps

# 生成的中间文件：
#   hello.ll    - LLVM IR
#   hello.o     - 目标文件
#   hello.exe   - 最终可执行文件
```

### 7.6 打包为发布版

```bash
# 最终发布命令
duan build hello.duan -o dist/hello.exe ^
    --backend llvm ^
    --opt -O2 ^
    --verbose

# 分发时只需 hello.exe 文件
# 目标机器无需安装段言或 Python
```

---

## 8. 常见问题

### 8.1 编译错误

**Q: `clang: command not found`**

确保 clang 已安装并在 PATH 中：
- Windows：通过 Visual Studio Installer 安装 LLVM/Clang 工具链
- Linux：`apt install clang llvm` 或 `yum install clang llvm`
- macOS：`xcode-select --install` 或 `brew install llvm`

**Q: 编译时提示 `runtime_typed.c` 找不到**

设置运行时库路径：
```bash
# 设置环境变量
set DUAN_RUNTIME_DIR=C:\path\to\duan\runtime
# 或在编译时指定
duan build hello.duan -o hello.exe --runtime-dir ./runtime
```

### 8.2 运行时错误

**Q: 运行时 Segmentation Fault**

可能原因：
1. DuanValue 结构体布局不匹配（LLVM IR 端与 C 端的定义不一致）
2. 指针传递时使用了已释放的栈地址
3. 列表操作越界

**排查方法：**
```bash
# 使用 AddressSanitizer 编译
duan build hello.duan -o hello.exe --opt -fsanitize=address

# 运行时会显示内存错误位置
```

**Q: 异常处理不生效**

确认：
1. 使用了 `_setjmp`（Windows）还是 `setjmp`（Linux/macOS）
2. Windows 平台必须传递帧地址参数
3. try 嵌套深度未超过 16 层

### 8.3 性能问题

**Q: 编译后的 EXE 为什么比预期慢？**

1. **未启用类型优化**：检查代码中是否使用了类型注解（`数`、`浮点数`、`布尔`）
2. **未启用优化级别**：确认使用 `-O2` 或 `-O3`
3. **字符串操作密集**：字符串操作通过运行时函数实现，优化空间有限
4. **大量函数调用**：段落函数调用有指针传递开销，内联小函数可提升性能

**Q: LLVM 后端比 Python 后端还慢？**

可能原因：
1. 代码规模太小，LLVM 编译开销超过了运行时长
2. 大量使用 `打印` 等 I/O 操作（I/O 是瓶颈，与后端无关）
3. 未启用类型优化，频繁调用运行时函数

### 8.4 跨平台问题

**Q: 在 Windows 上编译的 EXE 能在 Linux 上运行吗？**

不能直接运行。需要：
- 使用交叉编译：`duan build hello.duan --target linux`
- 或在目标平台重新编译

**Q: macOS 支持情况**

macOS 支持正在开发中。当前已知问题：
- `setjmp` 函数签名与 Linux 一致（单参数）
- 可执行文件格式为 Mach-O（无需 `.exe` 后缀）
- ARM64（Apple Silicon）支持尚未完成

### 8.5 调试与诊断

**Q: 如何查看编译生成的 LLVM IR？**

```bash
duan build hello.duan -o hello.ll --backend llvm --emit-ir
```

**Q: 如何调试段言程序？**

```bash
# 开发阶段使用 SRC 后端（可获取 Python 回溯）
duan run hello.duan --backend src

# 生产阶段使用 LLVM 后端 + 调试信息
duan build hello.duan -o hello.exe --opt -g
# 然后使用 gdb/lldb 调试
gdb hello.exe
```

**Q: 如何获取编译器内部日志？**

```bash
# 设置日志级别
set DUAN_LOG_LEVEL=DEBUG
duan build hello.duan -o hello.exe --verbose
```

---

## 附录：参考资源

### 关键文件路径

| 文件 | 说明 |
|------|------|
| `src/llvm/codegen_typed.py` | Typed 后端代码生成器 |
| `src/llvm/compiler.py` | 编译入口 |
| `src/llvm/lexer.py` | 词法分析器 |
| `src/llvm/duan_parser_v3.py` | 语法分析器 |
| `runtime/runtime_typed.c` | 类型化运行时库 |
| `src/llvm/llvm_backend_design.md` | LLVM 后端设计文档 |

### 推荐阅读

- [LLVM Language Reference](https://llvm.org/docs/LangRef.html) — LLVM IR 语言参考
- [LLVM Programmer's Manual](https://llvm.org/docs/ProgrammersManual.html) — LLVM 编程手册
- [段言设计哲学与定位](设计哲学与定位.md) — 段言整体架构设计
- [LLVM 后端设计文档](llvm_backend_design.md) — 段言 LLVM 后端详细设计

---

> **项目地址：** [https://github.com/skywalk163/duan](https://github.com/skywalk163/duan)  
> **文档索引：** [index.md](index.md)  
> **许可证：** MIT