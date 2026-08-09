# LLVM 后端设计文档

## 概述

光明 LLVM 后端将光明源代码编译为原生可执行文件，提供远高于 Python 解释执行的运行性能。后端基于 LLVM IR 中间表示，通过 clang 编译链接为目标平台的原生机器码。

## 编译流程

```
.light 源文件
    │
    ▼
┌─────────────────┐
│   Lexer         │  词法分析
│   lexer.py      │  → Token 流
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LightParser v3  │  语法分析
│  light_parser_v3 │  → v3 AST
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AstAdapter    │  AST 适配
│  compiler.py    │  → 统一 AST
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TypedLLVMCodeGen│  代码生成
│ codegen_typed.py│  → LLVM IR (.ll)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      clang      │  编译优化
│                 │  → 目标文件 (.o)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      clang      │  链接
│  + runtime_typed│  → 可执行文件 (.exe)
└─────────────────┘
```

## 两种模式对比

### String 模式（旧版）
- 类型系统基于 i8* 字符串
- 所有值都以字符串形式存储
- 算术运算需要 atoi/itoa 转换
- 实现简单，但性能较差

### Typed 模式（推荐）
- 类型系统基于 LightValue 结构体
- 算术运算直接在原生类型（i64/double）上操作
- 通过指针传递，避免 C/LLVM ABI 不兼容
- 性能优异，是当前主要开发方向

## LightValue 类型系统

### 结构体定义

**LLVM IR 定义**（与 C 端布局完全匹配）：
```llvm
{ i32 type, i64 i64_val, double f64_val, ptr str_val, i32 bool_val, i32 list_size, i32 list_capacity, ptr list_data }
```

**C 定义**：
```c
typedef struct {
    int type;          /* 0=NULL 1=INT 2=FLOAT 3=STR 4=LIST 5=BOOL */
    int64_t i64;       /* INT */
    double f64;        /* FLOAT */
    char* str;         /* STR / LIST (序列化，仅用于 type=3) */
    int boolean;       /* BOOL */
    /* LIST 类型专用字段 (type=4) */
    int list_size;     /* 当前元素数量 */
    int list_capacity; /* 分配的数组容量 */
    struct LightValue** list_data; /* 元素数组指针 */
} LightValue;
```

> **重要**：LLVM IR 端的结构体定义必须与 C 端完全匹配，包括 list 相关字段。否则运行时函数在操作 LIST 类型时会写入越界内存。

### 类型标记

| 值 | 类型 | 存储位置 |
|----|------|----------|
| 0 | NULL（空） | - |
| 1 | INT（64位整数） | i64 |
| 2 | FLOAT（64位浮点数） | f64 |
| 3 | STRING（字符串） | str |
| 4 | LIST（列表） | str（序列化字符串） |
| 5 | BOOL（布尔值） | boolean |

### 指针传递策略

**问题**：C 和 LLVM 对结构体的内存布局、对齐方式可能存在差异（ABI 不兼容），直接传递结构体可能导致崩溃。

**解决方案**：所有 LightValue 通过指针传递，运行时函数接收 `LightValue*` 参数，结果写入 `result` 指针。

```llvm
; 函数签名示例
declare void @dv_add(ptr result, ptr a, ptr b)
declare void @dv_println(ptr value)
```

### 段落函数调用约定

段落函数（用户自定义函数）和类方法统一使用指针传递调用约定：

```llvm
; 段落函数签名
define void @_seg_函数名(ptr %result, ptr %args, i32 %num_args) {
    ...
}

; 类方法签名（实例方法）
define void @_method_类名_方法名(ptr %result, ptr %self, ptr %args, i32 %num_args) {
    ...
}
```

**参数传递流程**：
1. 调用方在栈上分配 `LightValue` 数组存放参数
2. 通过 `getelementptr` 计算每个参数的地址并写入
3. 传递数组指针和参数数量给被调函数
4. 被调函数从数组中按索引提取参数
5. 结果写入 `%result` 指针，调用方从中读取返回值

**参数越界保护**：被调函数检查 `i < num_args`，未提供的参数设为 null。

## 代码生成核心

### 寄存器分配

使用简单的递增计数器分配虚拟寄存器：

```python
def new_register(self) -> str:
    self._reg_counter += 1
    return f'%{self._reg_counter}'
```

### 标签管理

标签用于控制流（分支、循环、函数等）：

```python
def new_label(self, prefix: str) -> str:
    self._label_counter += 1
    return f'{prefix}_{self._label_counter}'
```

### Alloca 延迟生成

LLVM 要求 alloca 指令必须在函数入口块（entry block）中。通过 `_pending_allocas` 列表延迟生成：

```python
# 收集阶段
self._pending_allocas.append(f'{reg} = alloca {DUANVALUE_STRUCT}')

# 函数入口统一生成
for alloca in self._pending_allocas:
    self.emit(alloca)
```

## 模块系统支持（Level 9）

Level 9 实现了 LLVM 后端的模块系统，支持跨文件编译和符号导入导出。

### 导入处理流程

1. **解析导入语句**：`_process_imports()` 遍历 `module.imports`，记录符号映射表 `_imports`
   - 键：本地符号名
   - 值：(模块名, 原始符号名)
2. **生成外部声明**：`_emit_module_decls()` 为每个导入的段函数生成 `declare` 声明
3. **调用外部函数**：`_gen_imported_segment_call()` 通过模块前缀别名调用

### 导出别名机制

为使其他模块能引用当前模块的段函数，为导出的函数生成 LLVM alias：

```llvm
; 模块 "数学工具" 导出函数 "阶乘"
@_seg__数学工具_阶乘 = alias void (ptr, ptr, i32), void (ptr, ptr, i32)* @_seg__阶乘
```

调用方通过 `@_seg_{模块名}_{函数名}` 引用，实现跨模块调用。

### 多模块编译流水线

```
compile_light_project(主文件路径)
    ↓
递归收集依赖模块（通过 ModuleResolver）
    ↓
compile_modules_typed(模块名→源码字典)
    ↓
逐模块编译为 IR（主模块生成 main 函数，依赖模块只生成段函数）
    ↓
合并 IR（依赖模块在前，主模块在后）
    ↓
clang 编译 → 链接 → 原生可执行文件
```

### 包管理器集成

`PackageManager` 新增两个方法支持 LLVM 原生编译：

- `resolve_path_dependencies()`：解析 `package.toml` 中的 path 依赖
- `build_project_native()`：完整流水线，从 `package.toml` 到原生可执行文件

## 类型信息优化（Level 8）

Level 8 引入了基于类型注解和类型推断的代码生成优化。当编译器能确定操作数的类型时，直接使用原生 LLVM 指令替代运行时函数调用。

### 类型追踪系统

代码生成器维护变量类型映射表 `_var_types`，在以下时机记录变量类型：

1. **显式类型注解**：`变量 甲：数 = 10` → 记录甲为 INT
2. **初始化表达式推断**：`变量 x = 3.14` → 推断 x 为 FLOAT
3. **赋值表达式推断**：`x = y + 1` → 根据y的类型推断x的类型

类型映射支持中英文类型名：

| 光明类型名 | 英文名 | 内部常量 |
|-----------|--------|---------|
| 数、整数 | int | INT |
| 浮点数、小数 | float | FLOAT |
| 布尔 | bool | BOOL |
| 串、字符串 | str | STRING |
| 列表、数组 | list | LIST |

### 表达式类型推断

`_infer_expr_type` 方法根据 AST 节点推断表达式类型：

- **NumberLiteral**：含小数点 → FLOAT，否则 → INT
- **StringLiteral** → STRING
- **BooleanLiteral** → BOOL
- **Identifier** → 查询变量类型表
- **BinaryOp**：根据操作符和操作数类型推断
  - 算术运算：INT ⊕ INT → INT（除法除外），含 FLOAT → FLOAT
  - 比较运算 → BOOL

### 算术运算优化

当操作数类型已知时，直接使用 LLVM 原生算术指令：

```llvm
; INT + INT 优化（无需调用 dv_add）
%left_i64 = extractvalue { i32, i64, ... } %left_dv, 1
%right_i64 = extractvalue { i32, i64, ... } %right_dv, 1
%result = add i64 %left_i64, %right_i64
; 直接构造 LightValue（无需调用 dv_int）
store i32 1, ptr %type_ptr    ; type = INT
store i64 %result, ptr %i64_ptr
```

| 操作符 | INT 指令 | FLOAT 指令 |
|-------|---------|-----------|
| + / 加 | `add` | `fadd` |
| - / 减 | `sub` | `fsub` |
| * / 乘 | `mul` | `fmul` |
| / / 除 | `sdiv` | `fdiv` |

当类型未知时，回退到运行时函数调用（`dv_add` 等）。

### 比较运算优化

```llvm
; INT < INT 优化（无需调用 dv_lt）
%cmp = icmp slt i64 %left, %right
; 直接构造 BOOL LightValue
```

| 操作符 | INT 谓词 | FLOAT 谓词 |
|-------|---------|-----------|
| == / 等于 | `eq` | `oeq` |
| != / 不等于 | `ne` | `une` |
| < / 小于 | `slt` | `olt` |
| > / 大于 | `sgt` | `ogt` |
| <= / 小于等于 | `sle` | `ole` |
| >= / 大于等于 | `sge` | `oge` |

### 条件判断优化

`_gen_condition_i1` 方法根据条件类型选择最优判断策略：

| 条件类型 | 判断方式 | 生成的指令 |
|---------|---------|-----------|
| BOOL | 直接提取布尔字段 | `extractvalue ... 4` → `trunc to i1` |
| INT | 与0比较 | `extractvalue ... 1` → `icmp ne i64, 0` |
| FLOAT | 与0.0比较 | `extractvalue ... 2` → `fcmp one double, 0.0` |
| 未知 | 运行时比较 | `call @dv_eq` → `icmp ne` |

此优化应用于 `如果`、`否则如果`、`当` 等控制流语句的条件判断。

### 快速 LightValue 构造

`_create_int_dv_fast` 和 `_create_float_dv_fast` 方法直接通过 `getelementptr` + `store` 构造结构体，避免调用运行时构造函数 `dv_int` / `dv_float` 的开销：

```llvm
; 快速构造 INT（直接操作结构体字段）
%type_ptr = getelementptr ... { ... }, ptr %slot, i32 0, i32 0
store i32 1, ptr %type_ptr          ; type = INT
%i64_ptr = getelementptr ... { ... }, ptr %slot, i32 0, i32 1
store i64 %result, ptr %i64_ptr     ; i64 值
```

## 异常处理实现

### 语法

```光明
尝试：
    可能抛出异常的代码
捕获 异常变量：
    异常处理代码
最终：
    无论是否异常都执行的代码
结束。
```

### 实现机制

基于 C 标准库的 `setjmp`/`longjmp` 实现非局部跳转：

- `setjmp(buf)`：保存当前执行环境，返回 0
- `longjmp(buf, val)`：跳转到 `setjmp` 位置，`setjmp` 返回 `val`

### 跨平台 setjmp 适配

不同平台的 `setjmp` 函数签名存在差异，代码生成器根据目标平台动态生成对应的调用：

#### Windows x64

**问题**：Windows x64 的 `_setjmp` 需要两个参数：
1. jmp_buf 指针
2. 帧地址（用于栈展开）

如果在 C 函数中调用 `setjmp`，当 C 函数返回后，栈帧失效，`longjmp` 会崩溃。

**解决方案**：
- 在 LLVM IR 中直接调用 `_setjmp`
- 使用 `llvm.frameaddress.p0(i32 0)` 获取当前帧地址
- setjmp 的帧地址指向当前 LLVM 函数的栈帧，长期有效

```llvm
%frame_addr = call ptr @llvm.frameaddress.p0(i32 0)
%setjmp_result = call i32 @_setjmp(ptr %jmp_buf_ptr, ptr %frame_addr)
```

#### Linux / macOS

Linux 和 macOS 使用标准 C 库的 `setjmp`，只需一个参数（jmp_buf 指针）：

```llvm
%setjmp_result = call i32 @setjmp(ptr %jmp_buf_ptr)
```

#### 平台检测机制

代码生成器在初始化时检测目标平台：
- `is_windows`：Windows 平台（win32/cygwin）
- `is_linux`：Linux 平台
- `is_macos`：macOS 平台（darwin）

支持通过 `target_platform` 参数显式指定目标平台，便于交叉编译场景。

### Try 层级管理

使用全局数组和计数器管理嵌套 try-catch：

```c
#define MAX_TRY_DEPTH 16
static jmp_buf __dv_jmp_bufs[MAX_TRY_DEPTH];
static int __dv_try_level = -1;

void* dv_try_push(void) {
    __dv_try_level++;
    if (__dv_try_level >= MAX_TRY_DEPTH) {
        __dv_try_level--;
        return NULL;
    }
    return (void*)__dv_jmp_bufs[__dv_try_level];
}

void dv_try_pop(void) {
    if (__dv_try_level >= 0) {
        __dv_try_level--;
    }
}

void dv_throw(LightValue* exc) {
    if (__dv_try_level < 0) return;
    // 保存异常消息
    char* s = dv_to_string(exc);
    strncpy(__dv_exception_str, s, 1023);
    free(s);
    // 跳转到当前 try 层级
    int level = __dv_try_level;
    longjmp(__dv_jmp_bufs[level], 1);
}
```

### 控制流设计

```
入口:
  jmp_buf_ptr = dv_try_push()
  frame_addr = llvm.frameaddress(0)
  setjmp_result = _setjmp(jmp_buf_ptr, frame_addr)
  if setjmp_result != 0 → catch 分派
  else → try 块

try 块:
  执行 try 体
  dv_try_pop()
  有 finally → finally_from_try → finally 块
  无 finally → end

catch 分派:
  有 catch → catch 块
  无 catch 但有 finally → finally 块（之后重新抛出）

catch 块:
  dv_try_pop()
  获取异常消息
  执行 catch 体
  有 finally → finally 块
  无 finally → end

finally 块:
  执行 finally 体
  有 catch → end
  无 catch → 重新抛出异常（向外层传播）
```

### 特殊情况处理

1. **既无 catch 也无 finally**：直接执行 try 体，不设置 setjmp
2. **无 catch 但有 finally**：finally 执行完后重新抛出异常
3. **异常信息存储**：全局缓冲区 `__dv_exception_str[1024]`

## 列表实现

列表内部使用动态数组存储，LightValue 结构体中的 `list_size`、`list_capacity`、`list_data` 字段专门用于 LIST 类型：

```c
typedef struct {
    int type;          /* 4 = LIST */
    ...
    int list_size;     /* 当前元素数量 */
    int list_capacity; /* 分配的数组容量 */
    struct LightValue** list_data; /* 元素指针数组 */
} LightValue;
```

### 列表操作

- **创建**：`dv_list_new` 分配初始容量为 4 的数组
- **追加**：`dv_list_append` 复制原列表并追加元素，容量不足时自动扩容
- **访问**：`dv_list_get` 通过索引直接访问 `list_data[index]`，O(1) 复杂度
- **长度**：`dv_list_len` 直接返回 `list_size` 字段

## 类与对象实现

对象内部也使用序列化字符串存储，格式为：

```
obj:字段数:字段名1\x1f值1\x1f字段名2\x1f值2\x1f...
```

使用 `\x1f` 分隔字段名和值。

## 运行时库

### 文件结构

| 文件 | 说明 |
|------|------|
| `runtime_typed.c` | 类型化运行时库（C 实现） |
| `runtime.c` | string 模式运行时库 |

### 运行时函数分类

**值构造器**：`dv_null`, `dv_int`, `dv_float`, `dv_str`, `dv_bool`

**算术运算**：`dv_add`, `dv_sub`, `dv_mul`, `dv_div`

**比较运算**：`dv_eq`, `dv_lt`, `dv_gt`, `dv_le`, `dv_ge`

**I/O**：`dv_print`, `dv_println`, `dv_input`

**字符串操作**：`dv_concat`, `dv_str_len`

**列表操作**：`dv_list_new`, `dv_list_len`, `dv_list_get`, `dv_list_append`, `dv_list_clear`

**时间**：`dv_timestamp`, `dv_format_time`

**文件**：`dv_file_exists`, `dv_read_file`, `dv_write_file`

**异常处理**：`dv_try_push`, `dv_try_pop`, `dv_throw`, `dv_get_exception_str`, `dv_clear_exception`

**类操作**：`dv_class_new`, `dv_class_set_member`, `dv_class_get_member`

## 编译入口

`src/llvm/compiler.py` 提供完整的编译流程：

### 主要函数

- `compile_source(source)`：编译源码为 LLVM IR 字符串
- `compile_source_typed(source)`：编译源码为 LLVM IR（typed 模式）
- `compile_light(source_path, output_path)`：编译 .light 文件为可执行文件
- `compile_light_typed(source_path, output_path)`：typed 模式编译
- `find_clang()`：查找 clang 编译器

### 使用示例

```python
from llvm.compiler import compile_light_typed

exe_path = compile_light_typed('hello.light', verbose=True)
print(f'编译成功: {exe_path}')
```

## 异步并发支持（Level 10）

### 设计思想

采用 **Duff's device 协程** 模式，通过在生成的 LLVM IR 中嵌入 `switch(resume_point)` 状态机实现协程的挂起与恢复。每个 `await` 点对应一个 `case` 标签，挂起时记录 `resume_point` 并返回，恢复时从对应 `case` 继续执行。

### 核心数据结构

**LightCoroutine 结构体**（`runtime_typed.c`）：
```c
typedef struct LightCoroutine {
    int state;             // 协程状态：DV_CORO_READY/SUSPENDED/DONE/ERROR
    int resume_point;      // 恢复点（Duff's device 的 case 标签）
    DuanCoroFunc func;     // 协程函数指针
    LightValue result;      // 返回值
    LightValue* args;       // 参数数组（堆分配）
    int num_args;          // 参数数量
    LightValue* locals;     // 局部变量数组（堆分配，跨 await 持久化）
    int num_locals;        // 局部变量数量
    struct LightFuture* waiting_for;  // 等待的 Future
    struct LightFuture* future;        // 关联的 Future（完成时自动触发）
    struct LightCoroutine* next;       // 调度器链表指针
} LightCoroutine;
```

**LightFuture 结构体**：
```c
typedef struct LightFuture {
    int ready;             // 是否已完成
    LightValue result;      // 结果值
    int has_error;         // 是否有错误
    char error_msg[256];   // 错误消息
    LightCoroutine* waiters; // 等待这个 future 的协程链表
} LightFuture;
```

**协程函数签名**：
```llvm
define void @_coro_xxx(ptr %result, ptr %coro, ptr %args, i32 %num_args)
```
与运行时 `DuanCoroFunc` typedef 匹配。

### 代码生成策略

**两阶段法生成协程状态机**：

```
阶段1：预扫描 body，统计 await 点数量
阶段2：生成完整函数
  ├── entry: 分配局部变量（coro->locals）
  ├── 加载 resume_point
  ├── switch i32 %rp, label %end [
  │     i32 0, label %resume_0
  │     i32 1, label %resume_1
  │     ...
  │   ]
  ├── resume_0: 执行前半段代码...
  ├── await 点（设置 resume_point=1, 调用 dv_coro_await, ret void）
  ├── resume_1: 继续执行...
  ├── ...
  └── coro_switch_end: ret void
```

**局部变量持久化**：
- 不使用 `alloca`（栈上分配，跨调用不保持）
- 使用 `coro->locals` 堆数组存储，通过 `dv_coro_get_local(coro, index)` 访问
- 参数在入口处从 `coro->args` 复制到 `coro->locals`

### 异步段落

**包装函数模式**：每个异步段落生成两个函数：
1. `_seg_xxx`（包装函数）：创建协程，返回协程句柄（LightValue 指针值）
2. `_coro_xxx`（协程函数）：实际的协程状态机

**示例 IR**：
```llvm
define void @_seg_xxx(ptr %result, ptr %args, i32 %num_args) {
  %coro = call ptr @dv_coro_create(ptr @_coro_xxx, ptr %args, i32 %num_args, i32 N)
  ; 存储协程指针到 LightValue result
  ret void
}
```

### async/await 实现

**await 表达式代码生成**：
1. 计算子表达式得到协程 LightValue
2. 提取 ptr_val 得到协程指针
3. 设置 `resume_point = 当前点 + 1`
4. 调用 `dv_coro_await(%coro, %target_coro)` 挂起
5. `ret void` 返回到调度器
6. 恢复标签：从 `dv_coro_get_await_result` 获取结果

### 异步作用域（结构化并发）

```光明
异步作用域
    任务1()
    任务2()
结束
```

**代码生成**：
1. 为每个任务创建协程（调用异步段落函数）
2. 逐个调用 `dv_coro_run_to_completion(coro_ptr)` 执行
3. 当前是串行执行，未来可升级为并发调度

### 调度器

- **可运行队列**：`run_queue` 单链表
- **调度循环**：从队列头部取出协程 → `dv_coro_resume` 执行一步 → 重复
- **等待唤醒**：协程 await 时挂起到 future 的 waiters 链表，future 完成时批量唤醒

### 运行时函数清单

| 函数 | 说明 |
|------|------|
| `dv_coro_create(func, args, num_args, num_locals)` | 创建协程 |
| `dv_coro_resume(coro)` | 恢复执行一步 |
| `dv_coro_await(coro, target_coro)` | 挂起等待另一个协程 |
| `dv_coro_run_to_completion(coro)` | 运行到完成（阻塞式） |
| `dv_coro_set_result(coro, val)` | 设置结果并完成 future |
| `dv_coro_get_await_result(coro, out)` | 获取 await 结果 |
| `dv_coro_get_local(coro, index)` | 获取局部变量指针 |
| `dv_coro_get_arg(coro, index)` | 获取参数指针 |
| `dv_future_create()` | 创建 Future |
| `dv_future_complete(f, result)` | 完成 Future，唤醒等待者 |
| `dv_scheduler_run()` | 运行调度器到队列为空 |

## 已知限制

### 类型系统
- **字符串编码**：当前使用 UTF-8 字符串，未完全支持 Unicode 字符串操作（如按字符索引、子串等）
- **垃圾回收**：使用 malloc/free 手动管理内存，没有自动垃圾回收
- ~~**列表存储**：列表使用序列化字符串存储，访问元素需要解析，性能较低~~ ✅ 已改为动态数组存储，O(1) 随机访问
- **对象存储**：对象使用序列化字符串存储，字段访问需要线性查找

### 异常处理
- **异常类型**：目前只支持字符串异常消息，不支持自定义异常类型和类型匹配
- **线程安全**：全局变量（try 层级、异常消息）非线程安全
- **最大 try 深度**：最多 16 层嵌套 try-catch

### 标准库
- **覆盖度低**：仅实现了 48 个运行时函数，Python 后端有 23 个标准库模块
- **缺少数学库**：sin/cos/sqrt 等数学函数尚未实现
- **缺少字符串操作**：分割、替换、查找等字符串操作有限

### 平台支持
- **已支持平台**：Windows x64、Linux x64
- **setjmp 适配**：已实现 Windows `_setjmp` 与 Linux/macOS 标准 `setjmp` 的条件生成
- **可执行文件后缀**：Windows 生成 `.exe`，Linux/macOS 生成无后缀可执行文件
- **待支持**：macOS、ARM64、WebAssembly

### 优化程度
- **类型信息优化**：✅ Level 8 实现了基于类型注解和推断的直接原生类型运算
- **LLVM 优化 Pass**：未启用 LLVM 的 O1/O2/O3 优化 Pass（但 clang 编译时使用 -O2）
- **SSA 优化**：代码生成已使用 SSA 形式，但未利用 LLVM 的深度优化

## 未来规划

### 短期目标（v1.9.x）— 功能补全与稳定性提升

#### 1. 内置函数扩充
- [x] **数学函数**：`sin`、`cos`、`sqrt`、`pow`、`abs`、`floor`、`ceil`、`取模` 等 ✅
- [x] **字符串操作**：`分割`、`替换`、`查找`、`子串`、`转大写`、`转小写`、`去除空白` 等 ✅
- [x] **列表操作**：`插入`、`删除`、`反转`、`排序`、`查找元素索引`、`包含`、`设置元素`、`列表字面量` 等 ✅
- [x] **文件操作**：`追加文件`、`列出目录`、`删除文件`、`文件大小`、`读取文件`、`写入文件`、`文件存在` 等 ✅
- [x] **系统操作**：`环境变量`、`设置环境变量`、`参数列表`、`退出程序`、`当前目录`、`切换目录`、`执行命令` 等 ✅
- [x] **类型转换函数**：`转整数`、`转浮点`、`转字符串`、`转布尔` 等显式转换 ✅
- [x] **字符串连接列表**：`join`/`连接字符串` ✅

#### 2. 异常处理增强
- [ ] **自定义异常类型**：支持定义异常类，按类型捕获异常
- [ ] **异常栈追踪**：抛出异常时记录调用栈，便于调试
- [ ] **多重捕获**：支持多个捕获块按类型匹配
- [ ] **异常链式传递**：支持异常 cause，保留原始异常信息

#### 3. 类型系统改进
- [ ] **字典/映射类型**：新增 `dict` 类型，支持键值对存储（替代当前对象序列化方案）
- [ ] **列表优化**：改用动态数组存储列表元素，提升随机访问性能
- [x] **类型转换函数**：`转整数`、`转浮点`、`转字符串`、`转布尔` 等显式转换 ✅
- [ ] **可空类型**：与语言层面的可空类型对接，支持 null 安全检查

#### 4. 稳定性与测试
- [ ] **完善测试覆盖**：将 LLVM 后端纳入 CI，运行完整测试套件
- [ ] **内存泄漏检测**：使用 valgrind/AddressSanitizer 检测内存泄漏
- [ ] **边界情况处理**：除零、空指针、索引越界等边界错误的优雅处理
- [ ] **错误信息改进**：编译错误包含行号、列号和源代码上下文

### 中期目标（v2.0）— 性能优化与生态完善

#### 1. 内存管理
- [ ] **引用计数 GC**：实现基于引用计数的自动垃圾回收
- [ ] **循环引用处理**：使用弱引用或周期回收处理循环引用
- [ ] **内存池**：小对象内存池分配，减少 malloc 开销
- [ ] **字符串池**：字符串常量池，避免重复分配

#### 2. 性能优化
- [ ] **LLVM 优化 Pass**：启用 O1/O2 优化，集成 InstCombine、GVN、DCE 等
- [ ] **函数内联**：小函数自动内联，减少调用开销
- [ ] **循环优化**：循环不变量外提、循环展开、循环向量化
- [ ] **常量传播**：跨函数常量传播与折叠
- [ ] **逃逸分析**：栈上分配未逃逸对象，减少 GC 压力
- [ ] **内联缓存**：方法调用的内联缓存（Inline Cache）优化

#### 3. 标准库移植
- [ ] **数学模块**：完整移植数学模块（三角函数、对数、随机数等）
- [ ] **字符串处理模块**：移植字符串处理模块（正则、编码转换等）
- [ ] **JSON 模块**：移植 JSON 解析与序列化
- [ ] **时间/日期模块**：移植时间与日期处理
- [ ] **文件系统模块**：移植文件系统操作
- [ ] **哈希模块**：MD5、SHA1、SHA256 等哈希算法
- [ ] **正则模块**：正则表达式支持（集成 PCRE 或 re2）

#### 4. 模块系统支持
- [x] **导入/导出**：支持模块导入导出语法 ✅ Level 9 已实现
- [x] **模块解析**：实现模块路径解析与缓存 ✅ Level 9 已实现
- [x] **跨模块调用**：支持调用其他模块的函数和类 ✅ Level 9 已实现
- [ ] **标准库加载**：内置标准库模块的自动加载机制

#### 5. 开发工具
- [ ] **调试信息**：生成 DWARF 调试信息，支持 gdb/lldb 调试
- [ ] **性能分析**：支持生成性能分析所需的符号表
- [ ] **编译缓存**：增量编译，缓存已编译的模块

### 长期目标（v2.x+）— 高级特性与平台扩展

#### 1. 高级类型系统
- [ ] **泛型特化**：泛型函数/类的单态化（monomorphization），生成特化代码
- [ ] **接口/协议**：接口定义与动态派发
- [ ] **枚举类型**：带关联值的代数数据类型（ADT）
- [ ] **模式匹配**：match 表达式与解构赋值
- [ ] **类型推断集成**：将 HM 类型推断结果用于代码生成优化

#### 2. JIT 编译
- [ ] **LLVM ORC JIT**：集成 LLVM ORC JIT 引擎，支持即时编译
- [ ] **REPL 支持**：LLVM 后端的 REPL 交互式环境
- [ ] **动态加载**：运行时动态编译和加载代码
- [ ] **分层编译**：解释执行 → 快速 JIT → 优化 JIT 的分层编译策略

#### 3. 并发与并行
- [x] **协程**：支持 async/await 异步编程 ✅ Level 10 已实现
- [ ] **多线程**：线程安全的运行时，支持多线程并行
- [ ] **通道/消息传递**：CSP 风格的并发模型
- [ ] **并行循环**：自动并行化的遍历循环

#### 4. 跨平台支持
- [x] **Linux 支持**：适配 Linux x64 平台 ✅
- [ ] **macOS 支持**：适配 macOS x64/ARM64 平台
- [ ] **ARM64 支持**：支持 ARM64 架构（树莓派、移动设备等）
- [ ] **WebAssembly**：编译为 WASM，支持浏览器运行
- [ ] **跨平台 CI**：多平台持续集成测试

#### 5. 高级优化
- [ ] **逃逸分析与栈分配**：基于逃逸分析的对象栈分配
- [ ] **向量化**：SIMD 向量化优化
- [ ] **PGO（Profile-Guided Optimization）**：基于运行时 profile 的优化
- [ ] **LTO（Link-Time Optimization）**：链接时优化
- [ ] **GC 优化**：分代垃圾回收、增量 GC、并发 GC

#### 6. 自举与元循环
- [x] **光明自举**：用光明重写编译器核心部分（bootstrap_v3.light，95 个段落）
- [x] **LLVM 自举编译**：自举编译器可通过 LLVM 后端编译为原生 EXE（525KB）
- [ ] **元循环解释器**：在光明中实现光明解释器
- [ ] **编译器即库**：编译器作为库嵌入到光明程序中
- [ ] **编译期计算**：支持编译期函数执行（const eval）

### 优先级路线图

```
v1.9.x (短期)                    v2.0 (中期)                      v2.x+ (长期)
┌───────────────────┐        ┌───────────────────┐        ┌───────────────────┐
│ 内置函数扩充       │        │ 引用计数 GC       │        │ 泛型特化           │
│ 异常处理增强       │──────▶│ LLVM 优化 Pass    │──────▶│ JIT 编译           │
│ 字典/列表优化      │        │ 标准库移植        │        │ 协程/多线程        │
│ 稳定性与测试       │        │ 模块系统支持      │        │ 跨平台（Linux/macOS）│
│                   │        │ 调试信息生成      │        │ 自举与元循环        │
└───────────────────┘        └───────────────────┘        └───────────────────┘
```

### 当前进度追踪

| 类别 | 已实现 | 计划中 | 完成度 |
|------|--------|--------|--------|
| 基础类型（int/float/bool/str） | ✅ | - | 100% |
| 列表类型 | ✅（动态数组） | - | 100% |
| 类与对象 | ✅（序列化字符串） | 字典优化 | 50% |
| 算术运算 | ✅（含类型优化） | - | 100% |
| 比较运算 | ✅（含类型优化） | - | 100% |
| 逻辑运算 | ✅ | - | 100% |
| 条件分支（如果/否则） | ✅（含类型优化） | - | 100% |
| 循环（遍历/当） | ✅（含类型优化） | - | 100% |
| 函数（段落） | ✅（指针传递） | - | 100% |
| 类与继承 | ✅ | - | 100% |
| 异常处理（尝试/捕获/抛出/最终） | ✅（含自定义异常类型） | - | 100% |
| 类型注解集成 | ✅ | - | 100% |
| 类型推断优化 | ✅ | - | 100% |
| 模块系统（导入/导出） | ✅（多模块编译） | - | 100% |
| 打印/输入 | ✅ | - | 100% |
| 字符串操作 | ✅ | 更多字符串操作 | 80% |
| 文件读写 | ✅ | 更多文件操作 | 60% |
| 时间函数 | ✅ | 日期时间模块 | 30% |
| 垃圾回收 | ❌ | 引用计数 GC | 0% |
| 模块系统 | ✅（导入/导出/多模块编译） | Git/注册表依赖 | 60% |
| LLVM 优化 | ❌ | O1/O2 优化 | 0% |
| 调试信息 | ❌ | DWARF 支持 | 0% |
| JIT 编译 | ❌ | ORC JIT | 0% |

### 已知问题

1. ~~**比较运算符在顶级条件分支中无效**~~ ✅ 已修复（Level 8 类型优化）
2. ~~**布尔条件判断问题**~~ ✅ 已修复（BooleanLiteral 现正确生成 BOOL 类型）
3. ~~**段落函数直接传递结构体导致 ABI 问题**~~ ✅ 已修复（改用指针传递）
4. ~~**LightValue 结构体布局不匹配**~~ ✅ 已修复（LLVM IR 与 C 端布局完全匹配）
5. ~~**_extract_f64 / _set_f64 类型错误**~~ ✅ 已修复（double 字段不再当作指针处理）

### Level 8 已完成功能

- [x] BooleanLiteral 生成正确的 BOOL 类型（type=5）
- [x] LightValue 结构体与 C 端布局完全匹配
- [x] 段落函数统一使用指针传递（`ptr %result, ptr %args, i32 %num_args`）
- [x] 集成 Level 6 类型注解到代码生成
- [x] 类型追踪系统（变量类型映射表）
- [x] 表达式类型推断
- [x] 算术运算类型优化（直接 i64/double 运算）
- [x] 比较运算类型优化（直接 icmp/fcmp）
- [x] 条件判断类型优化（直接布尔/整数/浮点判断）
- [x] 快速 LightValue 构造（直接结构体字段操作）
- [x] `转串` 内置函数别名支持

### Level 9 已完成功能

- [x] LLVM 后端导入解析（`_process_imports`、`_imports` 符号映射表）
- [x] 外部段函数声明生成（`_emit_module_decls`）
- [x] 导入函数调用（`_gen_imported_segment_call`，通过模块前缀别名）
- [x] 导出别名生成（`_gen_exported_aliases`，`@_seg_{模块名}_{函数名}`）
- [x] 多模块编译流水线（`compile_modules_typed`、`compile_light_project`）
- [x] 包管理器 path 依赖解析（`resolve_path_dependencies`）
- [x] 包管理器原生编译（`build_project_native`）
- [x] `ExportStatement` 多符号导出支持（`names: List[str]`）
- [x] `_convert_module` 正确收集 imports/exports
- [x] AST 节点命名兼容别名（`ImportStmt`/`ExportStmt`）
- [x] 核心标准库纯光明实现（数学工具、字符串工具、列表工具、类型工具）

### 待修复

（Level 8 已修复之前所有已知问题，当前无待修复项）
