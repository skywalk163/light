# Syntax Reference

> **Version:** v6.0
> **Last updated:** 2026-08-07

---

## Basics

### Comments

```段言
# This is a single-line comment
```

### Variable Declaration

```段言
设 年龄 为 25                # 设 ... 为 declares a variable
设 姓名 为 "Alice"
设 价格 为 3.14
设 是否完成 为 真              # Boolean: 真 (true) / 假 (false)
设 空值 为 空                 # Null: 空
```

### Data Types

| Type | Examples | Description |
|------|----------|-------------|
| Number | `42`, `3.14`, `-5` | Integer and floating-point |
| String | `"Hello"`, `'World'` | Text strings |
| Boolean | `真`, `假` | Boolean values (true/false) |
| List | `[1, 2, 3]` | Ordered collection |
| Dict | `{"key": "value"}` | Key-value map |
| Null | `空` | Null value |

### Operators

#### Arithmetic Operators

```段言
# Symbolic operators (Chinese equivalents also work)
设 结果 为 10 + 5    # Addition (also: 10 加 5)
设 结果 为 10 - 5    # Subtraction (also: 10 减 5)
设 结果 为 10 * 5    # Multiplication (also: 10 乘 5)
设 结果 为 10 / 5    # Division (also: 10 除 5)
设 结果 为 10 % 3    # Modulo (also: 10 取余 3)
设 结果 为 2 ** 3   # Exponentiation (also: 2 幂 3)
设 结果 为 10 // 3   # Floor division (also: 10 整除 3)
```

#### Comparison Operators

```段言
甲 > 乙             # Greater than (also: 甲 大于 乙)
甲 < 乙             # Less than (also: 甲 小于 乙)
甲 == 乙            # Equal to (also: 甲 等于 乙)
甲 != 乙            # Not equal (also: 甲 不等于 乙)
甲 >= 乙            # Greater or equal (also: 甲 大于等于 乙)
甲 <= 乙            # Less or equal (also: 甲 小于等于 乙)
```

#### Logical Operators

```段言
甲 且 乙            # Logical AND
甲 或 乙            # Logical OR
非 甲               # Logical NOT
```

## Control Flow

### Conditional Statements

```段言
设 分数 为 85

如果 分数 >= 90：
    打印 "优秀"        # Excellent
否则如果 分数 >= 60：
    打印 "及格"        # Pass
否则：
    打印 "不及格"      # Fail
```

### Loops

#### For-Range Loop

```段言
遍历 i 在 1 到 5：
    打印 i
```

#### For-Each Loop

```段言
设 水果 为 ["苹果", "香蕉", "橘子"]
遍历 水果 为 果：
    打印 果
```

#### While Loop

```段言
设 计数 为 0
当 计数 < 5：
    打印 计数
    设 计数 为 计数 + 1
```

#### Loop Control

```段言
遍历 i 在 1 到 10：
    如果 i % 2 == 0：
        跳过   # continue — skip to next iteration
    如果 i > 5：
        跳出   # break — exit loop
    打印 i
```

## Functions (段落)

Duan uses `段落` (paragraph) to define functions:

```段言
段落 加法 接收 甲, 乙：
    返回 甲 + 乙

设 结果 为 加法(3, 5)
打印 结果  # Output: 8
```

### Default Parameters

```段言
段落 问候 接收 名字 = "世界"：
    打印 "你好，" + 名字 + "！"

问候()        # Output: 你好，世界！
问候("段言")  # Output: 你好，段言！
```

### Return Values

```段言
段落 计算 接收 甲, 乙：
    返回 甲 + 乙, 甲 - 乙  # Multiple return values

设 和, 差 为 计算(10, 3)
打印 和  # Output: 13
打印 差  # Output: 7
```

## Classes and Objects

```段言
类 动物：
    属性 名字

    构造 接收 名字：
        己.名字 为 名字

    段落 介绍 接收:
        打印(f"我叫{己.名字}")

设 小狗 为 动物("旺财")
小狗.介绍()
```

### Class Inheritance

```段言
类 狗 继承 动物：
    属性 品种

    构造 接收 名字, 品种：
        父.构造(名字)
        己.品种 为 品种

    段落 叫 接收:
        打印("汪汪！")
```

## Lists and Dictionaries

### List Operations

```段言
设 数字 为 [1, 2, 3, 4, 5]
数字.追加(6)          # Append
打印 数字[0]          # Access: 1
打印 长度(数字)        # Length: 6
数字.弹出()            # Pop last element
数字.插入(0, 0)       # Insert at index
```

### Dictionary Operations

```段言
设 学生 为 {"名字": "张三", "年龄": 25}
打印 学生["名字"]     # Access: 张三
学生["成绩"] = 95     # Set value
学生.删除("年龄")     # Delete key
打印 长度(学生)        # Size: 2
```

## String Interpolation

```段言
设 名字 为 "段言"
设 版本 为 5.5
打印(f"语言：{名字}，版本：{版本}")
```

## Exception Handling

```段言
尝试：
    设 结果 为 10 / 0
捕获 Exception 为 错误：
    打印("出错了：" + 转字符串(错误))
最终：
    打印("操作结束")
```

## Modules

### Import

```段言
# Import entire module
导入 数学

设 结果 为 数学.平方根(16)
打印 结果  # Output: 4.0

# Import specific functions
从 数学 导入 阶乘
打印 阶乘(5)  # Output: 120

# Import with alias
导入 数学 为 数
打印 数.π  # Output: 3.14159...
```

### Export

```段言
导出 我的函数, 我的类
```

## Generics

### Generic Functions

```段言
段落 恒等[T] 接收 x：
    返回 x

设 结果1 为 恒等(42)       # x inferred as Number
设 结果2 为 恒等("你好")   # x inferred as String
```

### Generic Classes

```段言
类 栈[T]：
    属性 数据

    构造：
        己.数据 = []

    段落 入栈 接收 值：
        己.数据.追加(值)

    段落 出栈 接收:
        返回 己.数据.弹出()
```

## Lambda Expressions

```段言
设 加倍 为 参数 x => x * 2
打印 加倍(5)  # Output: 10

# Using lambda with list operations
设 数字 为 [1, 2, 3, 4, 5]
设 加倍后 为 映射(数字, 参数 x => x * 2)
```

## Pattern Matching

```段言
匹配 值：
    情况 1：
        打印("一")
    情况 2, 3：
        打印("二或三")
    默认：
        打印("其他")
```

## Pipeline Operator

```段言
设 结果 为 数据 |> 过滤 |> 映射 |> 归约
```

## Async/Await

```段言
异步 段落 获取数据 接收 url：
    返回 等待 请求(url)

异步 范围：
    任务 数据 = 获取数据("https://api.example.com")
    任务 更多 = 获取数据("https://api.example.com/more")
    等待 全部(数据, 更多)
```

## Full Example

```段言
# 学生管理系统示例
类 学生：
    属性 名字, 年龄, 成绩

    构造 接收 名字, 年龄, 成绩：
        己.名字 为 名字
        己.年龄 为 年龄
        己.成绩 为 成绩

    段落 介绍 接收:
        打印(f"我叫{己.名字}，{己.年龄}岁，成绩{己.成绩}分")

段落 主 接收：
    设 学生列表 为 [
        学生("张三", 20, 95),
        学生("李四", 21, 88),
        学生("王五", 19, 92),
    ]

    遍历 学生列表 为 学生：
        学生.介绍()

    设 总成绩 为 0
    遍历 学生列表 为 学生：
        总成绩 为 总成绩 + 学生.成绩

    打印(f"平均成绩：{总成绩 / 长度(学生列表)}")

主()
```

## v6.0 New Features

### Type Annotations

```段言
段落 加法 接收 a:整数, b:整数 返回 整数：
    返回 a + b
```

### Nullable Types

```段言
设 可能为空 为 可空("hello")
如果 可能为空 不是 空：
    打印 安全展开(可能为空)
```

### Interfaces & Protocols

```段言
协议 可打印：
    段落 打印 接收：

类 文档 实现 可打印：
    段落 打印 接收：
        打印("文档内容")
```

## Next Steps

- 📖 [Getting Started](getting-started.md) — Installation and basics
- 📚 [Standard Library](stdlib.md) — Built-in modules reference
- 📦 [Package Manager](package-manager.md) — duanpub package management
- 🛠️ [Toolchain](../tools.md) — CLI, LSP, debugger, AI Copilot