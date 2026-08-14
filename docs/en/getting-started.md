# Getting Started with Duan

> **Version:** v6.0
> **Last updated:** 2026-08-07

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

### Install from PyPI (Recommended)

```bash
pip install duan
```

After installation, verify the CLI tool:

```bash
duan --version
duan --help
```

### Install from Source

```bash
git clone https://github.com/skywalk163/duan.git
cd duan
pip install -e .
```

## Hello World

Create a file named `hello.duan`:

```段言
打印 "Hello, World!"
```

Run it:

```bash
duan run hello.duan
```

Output:

```
Hello, World!
```

Congratulations! You've just run your first Duan program.

## Basic Syntax Tour

### Comments

```段言
# This is a single-line comment
```

### Variables

Duan uses `设` (set) to declare variables:

```段言
设 姓名 为 "Alice"         # String
设 年龄 为 25              # Integer
设 分数 为 95.5            # Float
设 是否 为 真              # Boolean (真/假)
设 列表 为 [1, 2, 3]       # List
设 字典 为 {"键": "值"}    # Dictionary
```

### Arithmetic Operators

Duan supports both symbolic and Chinese operators:

```段言
设 甲 为 10
设 乙 为 3

打印 甲 + 乙    # 13 (also: 甲 加 乙)
打印 甲 - 乙    # 7  (also: 甲 减 乙)
打印 甲 * 乙    # 30 (also: 甲 乘 乙)
打印 甲 / 乙    # 3.333... (also: 甲 除 乙)
打印 甲 % 乙    # 1  (also: 甲 取余 乙)
打印 甲 ** 乙   # 1000 (also: 甲 幂 乙)
```

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

Duan supports three types of loops:

**For-range loop:**

```段言
遍历 i 在 1 到 5：
    打印 i
```

**For-each loop:**

```段言
设 水果 为 ["苹果", "香蕉", "橘子"]
遍历 水果 为 果：
    打印 果
```

**While loop:**

```段言
设 计数 为 0
当 计数 < 5：
    打印 计数
    设 计数 为 计数 + 1
```

**Loop control:**

```段言
遍历 i 在 1 到 10：
    如果 i % 2 == 0：
        跳过   # continue
    如果 i > 5：
        跳出   # break
    打印 i
```

### Functions (段落)

Duan uses `段落` (paragraph) to define functions:

```段言
段落 加法 接收 甲, 乙:
    返回 甲 + 乙

设 结果 为 加法(3, 5)
打印 结果  # Output: 8
```

Functions with default parameters:

```段言
段落 问候 接收 名字 = "世界":
    打印 "你好，" + 名字 + "！"

问候()        # Output: 你好，世界！
问候("段言")  # Output: 你好，段言！
```

### Classes and Objects

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

### Lists and Dictionaries

```段言
# Lists
设 数字 为 [1, 2, 3, 4, 5]
数字.追加(6)
打印 数字[0]    # Access first element: 1
打印 长度(数字)  # Length: 6

# Dictionary
设 学生 为 {"名字": "张三", "年龄": 25}
打印 学生["名字"]  # Output: 张三
学生["成绩"] = 95
```

### String Interpolation

```段言
设 名字 为 "段言"
设 版本 为 6.0
打印(f"语言：{名字}，版本：{版本}")
```

### Pattern Matching

```段言
匹配 值：
    情况 1：
        打印("一")
    情况 2, 3：
        打印("二或三")
    默认：
        打印("其他")
```

### Async/Await

```段言
异步 段落 获取数据 接收 url：
    返回 等待 请求(url)

异步 范围：
    任务 数据 为 获取数据("https://api.example.com")
    任务 更多 为 获取数据("https://api.example.com/more")
    等待 全部(数据, 更多)
```

### Context Managers

```段言
使用 打开文件("test.txt") 为 文件：
    设 内容 为 文件.读取()
    打印 内容
```

### Lambda Expressions

```段言
设 加倍 为 参数 x => x * 2
打印 加倍(5)  # Output: 10

# With list operations
设 数字 为 [1, 2, 3, 4, 5]
设 加倍后 为 映射(数字, 参数 x => x * 2)
```

### List Comprehensions

```段言
# Basic list comprehension
设 平方数 为 [x * x 遍历 x 之 范围(1, 6)]
打印 平方数  # [1, 4, 9, 16, 25]

# With condition
设 偶数 为 [x 遍历 x 之 范围(1, 11) 若 x % 2 == 0]
打印 偶数  # [2, 4, 6, 8, 10]
```

### Pipeline Operator

```段言
设 结果 为 数据 |> 过滤 |> 映射 |> 归约
```

### Type Annotations (v6.0)

```段言
段落 加法 接收 a:整数, b:整数 返回 整数：
    返回 a + b
```

### Nullable Types (v6.0)

```段言
设 可能为空 为 可空("hello")
如果 可能为空 不是 空：
    打印 安全展开(可能为空)
```

### Interfaces & Protocols (v6.0)

```段言
协议 可打印：
    段落 打印 接收：

类 文档 实现 可打印：
    段落 打印 接收：
        打印("文档内容")
```

### Exception Handling

```段言
尝试：
    设 结果 为 10 / 0
捕获 Exception 为 错误：
    打印("出错了：" + 转字符串(错误))
最终：
    打印("操作结束")
```

### Modules

```段言
# Import entire module
导入 数学

设 结果 为 数学.平方根(16)
打印 结果  # Output: 4.0

# Import specific functions
从 数学 导入 阶乘
打印 阶乘(5)  # Output: 120
```

## Running Programs

### Basic Commands

```bash
# Run a Duan program
duan run hello.duan

# Compile to Python
duan compile hello.duan -o hello.py

# Check syntax only
duan check hello.duan

# Show AST (Abstract Syntax Tree)
duan ast hello.duan

# Show token stream
duan tokens hello.duan
```

### Interactive REPL

```bash
duan repl
```

### Interactive Tutorial

```bash
duan tutorial
```

### Package Management

```bash
duan pkg init myproject     # Initialize a new project
duan pkg -p myproject build # Build the project
duan pkg -p myproject run   # Run the project
```

### AI-Assisted Development

```bash
duan ai generate "binary search function"  # Generate code with AI
duan ai card                               # Show syntax reference card
duan ai check hello.duan                   # Backend compatibility check
```

## Example Programs

The project includes several example programs:

```bash
duan run examples/hello.duan
duan run examples/basic.duan
duan run examples/class_example.duan
duan run examples/hanoi.duan
duan run examples/calculator.duan
```

## What's Next?

- 📖 [Full Tutorial (Chinese)](../30分钟入门段言.md) — Comprehensive 30-minute tutorial
- 📚 [Syntax Reference](../syntax.md) — Complete language syntax
- 🛠️ [Toolchain](../tools.md) — CLI, LSP, debugger, AI Copilot
- 📦 [Package Manager Guide](../包管理器使用指南.md) — duanpub package management
- 🌐 [API Reference](../api/index.md) — Standard library documentation
- 📋 [Roadmap](../ROADMAP.md) — Version planning and vision
- 📝 [Blog: Introduction to Duan](../blog/段言入门指南.md) — Detailed introduction

---

> Project Repository: [github.com/skywalk163/duan](https://github.com/skywalk163/duan)
> License: MIT