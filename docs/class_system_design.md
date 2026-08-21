# 光明 (Light) 语言类系统设计文档

> v1.9.x 核心功能 - 完整的面向对象编程支持

## 概述

本文档描述光明 (Light) 语言的完整类系统实现，基于 LLVM 后端构建。类系统采用序列化字符串存储对象，通过运行时全局表维护类元信息，支持继承、方法、属性、运算符重载等现代 OOP 特性。

## 对象模型

### 存储格式

对象在运行时以**序列化字符串**格式存储，便于调试和跨语言调用：

```
obj:__class__\x1f类名\x1f属性1\x1f值1\x1f属性2\x1F值2...
```

- `\x1f` (Unit Separator) 作为字段分隔符
- `__class__` 字段记录类名，用于类型判断和反射
- 属性按定义顺序存储，支持动态增删

### LightValue 结构

```c
typedef struct {
    int type;          // 0=NULL, 1=INT, 2=FLOAT, 3=STR, 4=LIST, 5=BOOL, 6=OBJ
    int64_t i64;       // INT
    double f64;        // FLOAT
    char* str;         // STR / OBJ (序列化)
    int boolean;       // BOOL
} LightValue;
```

## 类元信息系统

### LightClassInfo 结构体

```c
#define MAX_CLASSES 128
#define MAX_METHODS_PER_CLASS 64
#define MAX_ATTRS_PER_CLASS 128
#define MAX_INHERIT_DEPTH 32

typedef struct {
    char name[MAX_CLASS_NAME_LEN];
    char super_name[MAX_CLASS_NAME_LEN];
    int num_methods;
    char method_names[MAX_METHODS_PER_CLASS][MAX_CLASS_NAME_LEN];
    void* method_ptrs[MAX_METHODS_PER_CLASS];
    int method_flags[MAX_METHODS_PER_CLASS];  // 0=实例方法, 1=类方法, 2=静态方法
    int num_attrs;
    char attr_names[MAX_ATTRS_PER_CLASS][MAX_CLASS_NAME_LEN];
} LightClassInfo;

static LightClassInfo __dv_classes[MAX_CLASSES];
static int __dv_num_classes = 0;
```

### 注册流程

1. **类注册**：`dv_register_class(name, super_name)` 将类加入全局表
2. **属性注册**：`dv_register_attr(class_name, attr_name)` 登记类属性
3. **方法注册**：`dv_register_method/class/static` 登记方法函数指针

### 查找机制

- **方法查找**：`dv_find_method(class_name, method_name)` 递归向上查找父类
- **属性收集**：`collect_all_attrs(class_name, attrs, count)` 递归收集继承属性
- **深度限制**：最大继承深度 32 层，防止循环继承导致栈溢出

## 方法系统

### 方法签名

```c
typedef void (*LightMethodFunc)(LightValue* result, LightValue* self, LightValue* args, int num_args);
```

- `result`: 返回值指针
- `self`: 方法所属对象（实例方法）或类（类方法）
- `args`: 参数数组
- `num_args`: 参数个数

### 方法类型

| 类型 | 标识 | self 参数 | 调用方式 |
|------|------|-----------|----------|
| 实例方法 | 无前缀 | 对象本身 | obj.method() |
| 类方法 | `类` 前缀 | 类对象 | Class.method() |
| 静态方法 | `静` 前缀 | 无 | Class.static_method() |

### 方法调用链

```
调用 obj.method(args)
    ↓
生成 dv_call_method(obj, "method", args, n)
    ↓
获取 obj 的类名 → __class__
    ↓
dv_find_method(class_name, "method")
    ↓
找到方法指针 → 调用 LightMethodFunc
```

## 继承与 super

### 继承实现

1. **父类记录**：`LightClassInfo.super_name` 存储父类名
2. **属性继承**：`dv_class_new_named` 创建对象时，递归收集所有父类属性
3. **方法覆盖**：子类方法同名覆盖，查找时优先返回子类实现

### super 调用

```c
void dv_call_super_method(LightValue* result, LightValue* obj,
                          const char* class_name, const char* method_name,
                          LightValue* args, int num_args);
```

从指定类的**父类**开始查找方法，跳过当前类实现。

## 类型判断

### isinstance 实现

```c
int dv_isinstance(LightValue* obj, const char* class_name) {
    char actual_class[MAX_CLASS_NAME_LEN];
    dv_get_class_name(obj, actual_class, sizeof(actual_class));

    // 递归向上查找父类链
    while (strcmp(actual_class, class_name) != 0) {
        LightClassInfo* cls = dv_find_class(actual_class);
        if (!cls || !cls->super_name[0]) return 0;
        strcpy(actual_class, cls->super_name);
    }
    return 1;
}
```

### 类型名称获取

```c
void dv_get_type_name(LightValue* obj, char* buf, int buf_size);
```

返回对象类型名称（类名）或基础类型名称（整数、浮点数、文本、列表、布尔）。

## 运算符重载

### 重载方法名

| 运算符 | 中文方法名 | 英文方法名 |
|--------|-----------|-----------|
| + | 加 | __add__ |
| - | 减 | __sub__ |
| * | 乘 | __mul__ |
| / | 除 | __div__ |

### 实现机制

算术运算函数（如 `dv_add`）在执行前检查左操作数是否为对象：

```c
void dv_add(LightValue* result, LightValue* a, LightValue* b) {
    if (dv_is_object(a)) {
        // 查找并调用重载方法
        dv_try_operator_overload(result, a, "加", b, 1);
        return;
    }
    // 默认实现...
}
```

## 异常处理增强 (B 方案)

### 内置异常类

```
异常 (Exception)
├── 运行时异常 (RuntimeException)
├── 值异常 (ValueError)
├── 索引异常 (IndexError)
├── 类型异常 (TypeError)
├── IO异常 (IOError)
├── 内存异常 (MemoryError)
└── 算术异常 (ArithmeticError)
```

### 异常对象结构

异常是类实例，包含以下属性：
- `消息` (message): 错误描述
- `类型` (type): 异常类型名
- `栈追踪` (stack_trace): 调用栈信息
- `原因` (cause): 原始异常（用于异常链）

### 多重捕获

```光明
尝试：
    抛出 新建 值异常("错误")
捕获 值异常 e：
    打印 "值错误"
捕获 异常 e：
    打印 "其他错误"
最终：
    打印 "清理"
结束
```

捕获块按顺序匹配，支持继承匹配（子类异常可被父类捕获）。

## 编译流程

### LLVM IR 生成

```
.light 源码
    ↓
解析器 → AST (ast_nodes)
    ↓
TypedLLVMCodeGen.generate()
    ├─ 声明运行时函数 (_declare_typed_runtime)
    ├─ 收集类定义 (_collect_class)
    ├─ 生成全局初始化 (__light_init)
    │   ├─ 注册类 (dv_register_class)
    │   ├─ 注册属性 (dv_register_attr)
    │   ├─ 注册方法 (dv_register_method/class/static)
    │   └─ 注册内置异常
    ├─ 生成段落函数 (_gen_typed_segment)
    ├─ 生成主函数 (_gen_typed_main)
    └─ 输出 LLVM IR
        ↓
    clang 编译 → 可执行文件
```

### 代码生成关键点

1. **寄存器管理**：每个函数开始时重置 `_reg_counter = 0`
2. **非 void 调用**：有返回值的函数调用必须显式赋值给寄存器
3. **对象状态同步**：属性赋值后必须存回原变量

## 文件清单

### 核心文件

| 文件 | 描述 |
|------|------|
| `src/llvm/runtime_typed.c` | 运行时库：对象操作、方法调用、异常处理 |
| `src/llvm/codegen_typed.py` | LLVM 代码生成器 |
| `src/llvm/compiler.py` | 编译管道入口 |
| `src/ast_nodes.py` | AST 节点定义 |
| `src/compiler.py` | AST 适配器 |

### 测试文件

| 文件 | 覆盖内容 |
|------|----------|
| `test_class_stage1.light` | 类基础：定义、实例化、属性 |
| `test_class_stage2.light` | 方法与构造函数 |
| `test_class_stage3.light` | 继承、方法重写、super |
| `test_class_stage4.light` | 类型判断 (isinstance) |
| `test_class_stage5.light` | 运算符重载 |
| `test_class_stage6.light` | 类方法、静态方法 |
| `test_exception_class.light` | 类式异常处理 |

## 版本历史

- **v1.9.0**: 完整类系统实现，包含阶段 1-7 全部功能
- **v1.8.0**: LLVM 后端基础，异常处理初步实现
- **v1.7.0**: 统一编译管道，内置函数扩充
