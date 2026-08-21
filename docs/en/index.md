# Light (光明) Programming Language

> **Version:** v6.0
> **Last updated:** 2026-08-07

**Light** is a modern programming language with Chinese keywords, designed to make programming more intuitive and accessible for Chinese speakers.

## Overview

Light (光明, literally "Segment Language") is a Chinese natural language programming language. It uses Chinese keywords and syntax, allowing Chinese speakers to write code in their native language without translating their thoughts into English first.

## Key Features

- 🀄 **Chinese Syntax**: All keywords are in Chinese, making it accessible to Chinese speakers
- 🚀 **Self-hosting Compiler**: The compiler itself is written in Light (95 functions, ~62KB)
- ⚡ **LLVM Native Compilation**: Compile to native machine code (EXE) without Python runtime
- 📦 **Dual-backend Architecture**: Python interpreter execution + LLVM native compilation
- 🔧 **Rich Standard Library**: 60+ modules covering math, file I/O, JSON, HTTP, encryption, FFI, etc.
- 🔗 **C FFI Bindings**: Full C language interop via dynamic library loading
- 🧠 **HM Type Inference**: Hindley-Milner global type inference with generics support
- 🛡️ **Null Safety System**: `可空` (nullable) type annotations with safe `unwrap`
- 📦 **duanpub Package Manager**: Package indexing, installation, dependency management, publishing
- 🤖 **AI Toolchain 2.0**: AI Copilot for code generation, fine-tuned models, syntax cards
- 💻 **Full LSP Support**: Hover, completion, go-to-definition, diagnostics, refactoring, formatting
- 🐛 **DAP Debugger**: VS Code debug adapter for breakpoint debugging
- 📚 **Interactive Tutorial**: 10 complete lessons with REPL and step-by-step modes

## Installation

```bash
pip install light
```

Verify installation:

```bash
light --version
```

## Quick Start

Create `hello.light`:

```光明
打印 "Hello, Light!"
```

Run it:

```bash
light run hello.light
```

Output: `Hello, Light!`

## Basic Syntax

### Variables

```光明
设 姓名 为 "Alice"
设 年龄 为 25
设 分数 为 95.5
```

### Functions

```光明
段落 加法 接收 甲, 乙:
    返回 甲 + 乙

设 结果 为 加法(3, 5)
打印 结果  # Output: 8
```

### Conditionals

```光明
设 分数 为 85

如果 分数 >= 90：
    打印 "优秀"
否则如果 分数 >= 60：
    打印 "及格"
否则：
    打印 "不及格"
```

### Loops

```光明
# Range loop
遍历 i 在 1 到 5：
    打印 i

# List iteration
设 水果 为 ["苹果", "香蕉", "橘子"]
遍历 水果 为 果：
    打印 果

# While loop
设 计数 为 0
当 计数 < 5：
    打印 计数
    设 计数 为 计数 + 1
```

### Classes and Objects

```光明
类 动物：
    属性 名字

    构造 接收 名字：
        己.名字 为 名字

    段落 介绍 接收:
        打印(f"我叫{己.名字}")

设 小狗 为 动物("旺财")
小狗.介绍()
```

### Exception Handling

```光明
尝试：
    设 结果 为 10 / 0
捕获 Exception 为 错误：
    打印("出错：" + 转字符串(错误))
最终：
    打印("操作结束")
```

## CLI Commands

```bash
light run hello.light           # Run a program
light compile hello.light       # Compile to Python
light ast hello.light           # Show AST
light tokens hello.light        # Show token stream
light check hello.light         # Syntax check
light repl                     # Interactive REPL
light tutorial                 # Interactive tutorial
light pkg init myproject       # Initialize a project
light pkg -p myproject build   # Build project
light ai generate "排序算法"    # AI-assisted code generation
```

## Backend Options

| Backend | Command | Description | Dependencies |
|---------|---------|-------------|--------------|
| **SRC** (default) | `light run hello.light` | Hand-written parser, v3.2 syntax | **None** |
| ANTLR | `light run hello.light --backend antlr` | ANTLR parser, compatibility mode | `pip install antlr4-python3-runtime` |
| LLVM | `light compile hello.light --backend llvm-typed -o hello.exe` | Native compilation to EXE | LLVM/Clang |

## Documentation

- [Getting Started](getting-started.md) — Installation and basic usage
- [Syntax Reference](../syntax.md) — Complete language syntax
- [Standard Library](../stdlib.md) — Built-in modules reference
- [Toolchain](../tools.md) — CLI, debugger, LSP, AI Copilot
- [Package Manager Guide](../包管理器使用指南.md) — duanpub package management
- [Architecture](../architecture.md) — Compiler architecture
- [API Reference](../API_REFERENCE.md) — Complete API documentation
- [Roadmap](../ROADMAP.md) — Version planning and vision

## Project Status

Current version: **v6.0**

Light v6.0 introduces type annotations, nullable types, interfaces/protocols, enhanced pattern matching, async/await support, and comprehensive package management. The language is under active development with a focus on self-hosting compiler and native compilation via LLVM.

## Contributing

- 💬 **Discuss**: Start a [GitHub Discussion](https://github.com/skywalk163/light/discussions)
- 🐛 **Report Bug**: Submit a [Bug Report](https://github.com/skywalk163/light/issues/new?template=bug_report.md)
- 💡 **Feature Request**: Submit a [Feature Request](https://github.com/skywalk163/light/issues/new?template=feature_request.md)
- 🔧 **Contribute Code**: See [CONTRIBUTING.md](../../CONTRIBUTING.md)

## License

MIT License