# 光明 HM 全局类型推断系统

## 概述

光明采用 Hindley-Milner (HM) 风格的全局类型推断系统。HM 类型推断是一种基于合一（unification）的类型系统，能够自动推断出程序中几乎所有表达式的类型，而无需显式标注。

**核心特性**：
- 🎯 **两阶段推断**：预扫描注册 → 段体推断 + 泛化
- 🔄 **let-polymorphism**：自动识别泛型并实例化
- 🔗 **合一驱动**：TypeVar ~ 具体类型的双向推导
- 🚀 **全局推断**：跨段落、跨模块的类型传播
- 🧩 **泛型支持**：泛型段落、泛型类、泛型接口

## 架构设计

### 类型系统层次（src/type_system.py）

```
Type（基类）
├─ 基本类型（单例化）
│   ├─ NumberType        # 数
│   ├─ StringType        # 串
│   ├─ BooleanType       # 布尔
│   ├─ NullType          # 空
│   ├─ AnyType           # 任意
│   └─ UnknownType       # 未知
├─ 可空类型
│   └─ OptionalTypeWrapper  # 数|空
├─ 复合类型
│   ├─ ListType          # 列表[数]
│   ├─ DictType          # 字典[串: 数]
│   ├─ TupleType         # 元组[数, 串]
│   └─ SetType           # 集合[串]
├─ 函数类型
│   └─ FunctionType      # (参数类型列表) -> 返回类型
├─ 泛型
│   ├─ TypeVar           # 类型变量（T, U, V）
│   ├─ GenericTypeInstance  # 泛型实例：列表[数]
│   └─ GenericTypeDef    # 泛型定义：列表<T>
├─ 面向对象
│   ├─ ClassType         # 类类型
│   └─ InterfaceType     # 接口类型
├─ 枚举
│   └─ EnumType          # 代数数据类型
└─ 未来类型
    └─ FutureType        # 异步/协程包装
```

**类型 ID 机制**：每个类型都有唯一的 `_type_id` 整数，用于快速类型判断（替代 `isinstance` 链式检查）。

### 合一算法（unification）

合一是 HM 类型推断的核心。给定两个类型 t1 和 t2，合一尝试找到一个变量替换（substitution）使得两者等价。

```python
substitutions = unify(t1, t2)
```

**核心规则**：

| t1 | t2 | 结果 |
|---|---|---|
| `TypeVar('T')` | `NumberType` | `{'T': NumberType}` |
| `ListType(TypeVar('T'))` | `ListType(NumberType)` | `{'T': NumberType}` |
| `FunctionType([T, T], T)` | `FunctionType([数, 数], 数)` | `{'T': NumberType}` |
| `数` | `串` | **失败**（UnificationError） |
| `ClassType('向量')` | `InterfaceType('可比较')` | **失败**（除非实现） |

**发生检查（Occurs Check）**：防止无限类型。`T ~ list[T]` 会被拒绝，因为 `T` 出现在 `list[T]` 内部。

### 推断流程（两阶段架构）

**第一阶段：预扫描（`_pre_scan_definitions`）**

1. 遍历所有顶层段/类/方法定义
2. 解析显式类型标注（参数和返回类型）
3. 未标注的参数用 `TypeVar('T0'), TypeVar('T1'), ...` 占位
4. 未标注的返回值用 `TypeVar('R')` 占位
5. 将完整 `FunctionType` 注册到符号表

```
段 加(甲, 乙):
    返回 甲 加 乙。
结束。

↓ 预扫描

FunctionType(
    param_types=[TypeVar('T0'), TypeVar('T1')],
    return_type=TypeVar('R')
)
```

**第二阶段：段体推断（`_hm_infer_module`）**

1. 进入段体作用域
2. 推断每条语句中的表达式类型
3. 通过合一累积 `TypeSubstitution`
4. 将累积的替换应用到段签名
5. 识别自由类型变量（泛化），记录到 `generic_segment_defs`

```
段 加(甲, 乙):
    返回 甲 加 乙。   ← 甲=数, 乙=数, 推断返回=数
结束。

↓ 合一结果
FunctionType(param_types=[数, 数], return_type=数)
```

**第三阶段：泛化（Generalize）**

推断后，如果签名中仍有未绑定的 `TypeVar`，这些就是**泛型参数**。

```
段 恒等(值):
    返回 值。
结束。

↓ 推断
FunctionType(param_types=[TypeVar('T')], return_type=TypeVar('T'))
↳ 泛化结果: generic_segment_defs['恒等'] = ['T']
```

**第四阶段：实例化（Instantiate）**

调用泛型段落时，产生新鲜的 `TypeVar`，避免不同调用互相干扰。

```
恒等(五)    ← 实例化为 (T'0) -> T'0, 合一 T'0=数
恒等("你好") ← 实例化为 (T'1) -> T'1, 合一 T'1=串
                ↑ 两次调用互相独立
```

## 核心 API

### TypeInferencer（src/type_inferencer.py）

```python
from type_inferencer import TypeInferencer
from ast_nodes import Module

ti = TypeInferencer()
ti.infer(module)

# 访问推断结果
for name in ti.symbol_table.local_names():
    sym = ti.symbol_table.lookup(name)
    print(f"{name}: {sym.data_type}")

# 检查错误
for err in ti.errors:
    print(f"错误: {err}")
```

### 关键方法

| 方法 | 作用 |
|---|---|
| `infer(module)` | 完整推断入口（自动执行四阶段） |
| `_pre_scan_definitions(module)` | 第一阶段：扫描所有段签名 |
| `_hm_infer_module(module)` | 第二-四阶段：段体推断 + 泛化 |
| `_generalize(name, type)` | 将自由 TypeVar 标记为泛型参数 |
| `_instantiate(func_type)` | 产生新鲜 TypeVar 副本，供调用使用 |

### 类型合一（unify）

```python
from type_system import (
    TypeVar, NumberType, StringType, ListType,
    FunctionType, unify, TypeSubstitution
)

# 基本合一
T = TypeVar('T')
subs = unify(T, NumberType())
print(subs)  # {'T': NumberType}

# 列表合一
subs = unify(ListType(T), ListType(NumberType()))
print(subs)  # {'T': NumberType}

# 函数合一
ft1 = FunctionType([TypeVar('A'), TypeVar('B')], TypeVar('A'))
ft2 = FunctionType([NumberType, StringType], NumberType)
subs = unify(ft1, ft2)
# {'A': NumberType, 'B': StringType}
```

## 推断示例

### 示例 1：变量声明 → 基本类型推断

```光明
定义 年龄 等于 二十五。
定义 名字 等于 "张三"。

↓ 类型推断
年龄: 数
名字: 串
```

### 示例 2：段落调用 → 泛型推断

```光明
段落 加(甲, 乙):
    返回 甲 加 乙。
结束。

定义 结果 等于 加(三, 五)。

↓ 推断
加: (数, 数) -> 数
结果: 数
```

### 示例 3：泛型函数（多态）

```光明
段落 恒等(值):
    返回 值。
结束。

恒等(五)      ← 返回类型: 数
恒等("你好")  ← 返回类型: 串

↓ 实际签名
恒等: (T) -> T  (T 是泛型参数，实例化时根据参数确定)
```

### 示例 4：列表推断

```光明
定义 列表 等于 [一, 二, 三]。
↓
列表: 列表[数]
```

### 示例 5：返回类型推断

```光明
段落 乘积(甲, 乙):
    返回 甲 乘 乙。
结束。

↓ 推断（无需声明返回类型）
乘积: (数, 数) -> 数
```

### 示例 6：类与接口

```光明
接口 可比较:
    段落 比大小(其他):
    结束。
结束。

类 向量 实现 可比较:
    属性 x。
    属性 y。

    段落 比大小(其他):
        返回 x 大于 其他x。
    结束。
结束。

↓ 推断
向量: ClassType 实现了 InterfaceType('可比较')
向量.is_subtype_of(可比较) = True
```

## 错误检测

类型推断器在以下场景产生错误：

| 错误类型 | 示例 | 说明 |
|---|---|---|
| **类型不匹配** | `定义 x 等于 一加 "字符串"` | 数 与 串 合一失败 |
| **参数数量错误** | `加(一)` | `加` 需要 2 个参数 |
| **参数类型错误** | `加("一", 二)` | 形参是数，实参是串 |
| **接口未实现** | `类 甲 实现 可比较` | 需要实现 `比大小` |
| **循环依赖** | 段 A 调用 B，B 调用 A | 段体互相调用时自动识别 |
| **发生检查** | `段 坏(x): 返回 [x, 坏(x)]` | 防止无限类型 |

## 与可空类型系统的交互

HM 推断器支持可选类型（`OptionalTypeWrapper`）。当表达式可能返回 `空` 时，类型被标记为 `数|空`。使用 `!` 解包后，类型恢复为 `数`。

```光明
定义 值 等于 获取可能空的值()。
↓ 推断
值: 数|空

定义 非空 等于 值!。
↓ 推断
非空: 数
```

## 与模块系统的交互

- 模块内：完整的 HM 推断，符号表共享
- 跨模块：导入段的类型签名保留，可在当前模块继续推断
- 循环依赖：拓扑排序后逐个模块推断，跨模块类型传播

## 性能优化

### 1. 类型 ID 快速匹配

用整数 `_type_id` 替代 `isinstance` 链。合一判断从 O(n) 变为 O(1)。

```python
# 优化前
if isinstance(t1, NumberType) and isinstance(t2, NumberType): ...

# 优化后
if t1._type_id == TYPE_ID_NUMBER and t2._type_id == TYPE_ID_NUMBER: ...
```

### 2. 基本类型单例化

每个基本类型只有一个实例，避免重复创建。

```python
a = NumberType()
b = NumberType()
a is b  # True
```

### 3. 方法签名缓存

类方法第一次被解析后缓存，避免重复扫描。

```python
self._method_pre_scan_cache[(class_name, method_name)] = func_type
```

### 4. HM 两轮迭代

段调用段时，第一轮先解决被调用者的类型，第二轮再推断调用者，避免多次扫描。

## 限制与未来方向

### 当前限制

1. **高阶函数**：段可以被作为参数传递，但类型推断能力有限
2. **递归类型**：显式支持 `递归` 段落，但复杂递归类型的推断可能退化到 `任意`
3. **多方法重载**：目前不支持同一段名根据参数类型的重载

### 未来方向

1. **更高阶的 HM**：支持 rank-N 多态、类型类约束
2. **效果系统**：区分纯函数与副作用（标注 `异步`、`抛出`）
3. **增量推断**：只重新推断变更的段，加速 IDE 体验
4. **类型引导自动补全**：根据推断的类型提供智能补全建议

## 参考资料

- Hindley, R. (1969). "The principal type-scheme of an object in combinatory logic"
- Milner, R. (1978). "A theory of type polymorphism in programming"
- Pierce, B. C. (2002). "Types and Programming Languages"
