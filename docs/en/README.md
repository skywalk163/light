# LightLang (光明) Programming Language

**LightLang** is a Chinese-first programming language built on Chinese keywords and a **layered syntax architecture (L0–L7)**. It borrows the idea that "3000 common Chinese characters cover every discipline": **30 L0 core keywords** form a stable kernel; L1 (Baihua / vernacular style) lets teenagers get started quickly; L2 (Wenyan / literary style) supports large commercial projects; L3 embeds SQL / regex / math DSLs; L4 references existing ecosystems such as Python / C / Go / MoonBit; L5 provides exception handling and a module system; L6 offers space-free tokenization and pure-indentation syntax; L7 is a type-annotation system.

> **Terminology clarification (2026-08-29)**: L0–L7 are **syntax levels (registers / dialects)**,
> **not** internal compiler layers (lexical / syntactic / code generation). For the compiler
> layering see [docs/architecture.md](docs/architecture.md): 5 frontend stages + code generation +
> three backends. The "v4.0 five-layer syntax architecture" below covers the L0–L4 teaching and
> engineering tiers; L5–L7 were added later (specs: `docs/level5_spec.md`,
> `docs/Level6_已知限制与待办事项.md`, `docs/level7_spec.md`). The authoritative list is
> `SUPPORTED_LEVELS` in `src/version.py`.

## ✨ Core Features

- 🀄 **Chinese syntax**: full Chinese keywords that match Chinese thinking habits
- 🚀 **Self-hosted compiler**: the compiler itself is written in LightLang (`bootstrap_v3.light`, 95 paragraphs) and can bootstrap-compile
- ⚡ **LLVM native compilation**: compile to native machine code (EXE) with no Python runtime required. The runtime C layer ships 262 runtime symbols including TLS (Windows Schannel + POSIX mbedTLS) / SHA512 / HMAC / PBKDF2 / uuid v3&v5 / Base64 / hashing / nested-container serialization / object-pool caching
- 📦 **Three-backend architecture**: `src` (built-in parser, default) · `antlr` (legacy-syntax compatible) · `native`/`llvm-typed` (LLVM native compilation), switch flexibly with `--backend`
- 🔧 **Rich standard library**: **109 `.light` modules** covering math / statistics / strings / lists / sets / data structures / filesystem / datetime / Chinese lunar calendar / encoding (Base64/JSON/XML/CSV) / hashing (MD5/SHA1–512/HMAC) / crypto / networking (HTTPS / HTTP server / DNS / SSE) / LLM client / Agent loop / system / process / threads / concurrency / event bus / testing / assertions / caching / progress bar / logging / config / argument parsing / templating / Chinese text processing (tokenization / pinyin / number conversion / NLP) / ID-card & phone validation / uuid / regex / FFI / image processing. Native-leg capability totals **711 items** (411 builtin + 262 runtime); see the module quick-reference in [docs/stdlib.md](docs/stdlib.md)
- 🔗 **C FFI binding**: call C dynamic libraries, with enums / unions / variadic args / callbacks / bitfields / function pointers
- 🏗️ **v4.0 five-layer syntax**: the 30 L0 core keywords stay frozen; L1 vernacular (teenagers) + L2 literary (commercial) dual track; L3 domain embedding (SQL / regex / math); L4 foreign-language references (Python/C/Go/MoonBit); zero-breaking compatibility with v3.3
- 📊 **Current status (2026-09-07)**: after the v7.0 two-track merge, continuous iteration; R10–R13 four batches of native-leg coverage plus codegen defect root-cause fixes are complete; both CI red-light groups (ci_eval smoke 6 blocks + pytest 16 failed) are fully fixed. See [CHANGELOG.md](CHANGELOG.md)

---

## v4.0 Five-Layer Syntax Architecture

> Design doc: [分层语法设计_v4.0.md](docs/分层语法设计_v4.0.md) · Migration guide: [v3.3_to_v4.0迁移指南.md](docs/v3.3_to_v4.0迁移指南.md)

```
┌──────────────────────────────────────────────────────────┐
│  L4  Foreign-reference layer (引 C: / 引 Go: / 引 MoonBit: / 引 Python:) │ ← reuse the global ecosystem, sandboxed
├──────────────────────────────────────────────────────────┤
│  L3  Domain-embedding layer (SQL / regex / math formulas)                  │ ← native parameterization, injection-safe, write DSL directly
├──────────────────────────────────────────────────────────┤
│  L2  Literary style (commercial)   30 L0 words + English punctuation + explicit types │ ← maintainable big projects, strong typing
├──────────────────────────────────────────────────────────┤
│  L1  Vernacular style (teenager intro)  19 L0 words + Chinese punctuation + omitted types │ ← low threshold, code like speaking
├──────────────────────────────────────────────────────────┤
│  L0  Core keyword table (30)   若否当遍跳过返｜设段类承接配｜试捕抛终   │ ← permanently stable, never changed
│                        自之并从是｜且或非真假空｜导出               │
└──────────────────────────────────────────────────────────┘
```

### L0: Core Keyword Table (permanently frozen, 30 words)

| Group | Words |
|-------|-------|
| Control flow (7) | 若 否 当 遍 跳 过 返 |
| Definition / type (6) | 设 段 类 承 接 配 |
| Exception (4) | 试 捕 抛 终 |
| Self-reference / connection (5) | 自 之 并 从 是 |
| Logical values (6) | 且 或 非 真 假 空 |
| Organization (2) | 导 出 |

> All higher-level syntax is composed from L0; single-character-primary form, with v3.3 two-character words kept permanently as aliases (no deprecation planned).

### L1 vs L2 Dual-Track Quick Reference

| Dimension | L1 Vernacular (teen / teaching) | L2 Literary (commercial / big project) |
|-----------|--------------------------------|---------------------------------------|
| Core words | 19-word L0 subset | all 30 L0 words |
| Punctuation | Chinese punctuation（，。：（）） | English punctuation（, . : ()） |
| Types | omitted, auto-inferred | explicit type annotation `: 整` |
| Keyword form | mostly two-character (如果、遍历) | mostly single-character (若、遍) |
| Use case | intro teaching, scripts, contests | production code, libraries, teamwork |

Detailed specs:
- [L1_白话体语法规范_v4.0.md](docs/L1_白话体语法规范_v4.0.md)
- [L2_文言体语法规范_v4.0.md](docs/L2_文言体语法规范_v4.0.md)
- [L1 vs L2 comparison README](examples/L1_vs_L2_README.md)

### E-stage: L3 native syntax + L4 sandbox isolation (done)

**L3 domain embedding**: write `引 SQL:` / `引 正则:` / `引 数学:` blocks directly; the LightLang compiler auto-parameterizes / wraps them.

Example (SQL):
```light
引 SQL:
    CREATE TABLE 用户( id INTEGER PRIMARY KEY, 姓名 TEXT, 分数 INTEGER );
    INSERT INTO 用户 VALUES (1, '张三', 95), (2, '李四', 87);
    SELECT 姓名, 分数 FROM 用户 WHERE 分数 > 90;
```
→ LightLang auto-generates `l3_sql_*` functions, SQL-injection-safe, returning `list[dict]`.

Example (regex named capture):
```light
引 正则 手机号:
    (?<区号>\d{3,4})-(?<号码>\d{7,8})
打印 手机号.匹配("010-12345678").区号    # 010
```

Example (math formula):
```light
引 数学 二次求根:
    x = (-b ± √(b²-4ac)) / 2a
打印 二次求根(a=1, b=-5, c=6)   # [3.0, 2.0]
```

**L4 foreign reference**: `引 Python:` / `引 C:` / `引 Go:` / `引 MoonBit:` → independent namespace sandbox, explicit `出` keyword to export, never pollutes the LightLang main scope.

```light
引 Python:
    import numpy as np
    数据 = [1,2,3,4,5]
    均值 = float(np.mean(数据))
    出 均值
打印 均值    # 3.0
```

Full examples: [examples/E阶段_L3L4原生语法/](examples/E阶段_L3L4原生语法/README.md), [examples/L3_domain/](examples/L3_domain/README.md), [examples/L4_python/](examples/L4_python/README.md).

### F-stage: Chinese standard-library enhancements (done)

Three enhancement modules added under `contrib/`, with **42 unit tests** (`contrib/test_F3_三个增强模块.py`):

| Module | File | Capability |
|--------|------|-----------|
| 🕒 DateTime enhancement | [contrib/日期时间增强.py](contrib/日期时间增强.py) | natural-language relative time ("3 days ago", "next Monday", "the 15th of this month"), start/end time, date ranges, solar-term / lunar helpers |
| 📊 Statistics enhancement | [contrib/统计函数增强.py](contrib/统计函数增强.py) | percentile, Z-score, T-score, linear regression, R², outlier detection (IQR / Z-score) |
| 🔍 Regex tools enhancement | [contrib/正则工具增强.py](contrib/正则工具增强.py) | ID-card GB11643 validation, license-plate validation, bank-card Luhn, batch extraction of phone / email / URL |

LightLang-side usage:
```light
从 日期时间增强 导入 解析相对时间, 日期区间
打印 解析相对时间("3天后")
打印 日期区间("2026-01-01", "2026-01-07")
```

LightLang-side examples: [examples/F阶段_标准库增强/](examples/F阶段_标准库增强/).

### G-stage: CI + Playground automation (in progress)

- ✅ **CI workflow**: [.github/workflows/ci.yml](.github/workflows/ci.yml) supports the `4.0dev` branch, installs L3/L4 dependencies (numpy/pandas/matplotlib/requests/sklearn), full pytest + 8 smoke demos
- ✅ **Playground Web API**: [playground/server.py](playground/server.py) adds `/api/demos/list` (20+ demo list), `/api/demos/run?id=xxx` (run demo), `/api/demos/<id>` (single demo detail), one-click run of all A→G stage examples
- 🟡 **Homepage docs**: the current page ←

## Milestones

| Milestone | Status | Notes |
|-----------|--------|-------|
| v3.2 syntax | ✅ | mature, stable Chinese programming language |
| Self-hosted compiler | ✅ | LightLang compiler written in LightLang (62KB / 95 paragraphs) |
| LLVM backend | ⚠️ partial | can compile to native EXE (clang zero-error), but **does not support projects depending on the Python ecosystem** (`导入 asyncio` etc. report module-not-found). Capability boundary: [docs/原生腿能力边界.md](docs/原生腿能力边界.md) |
| Bootstrap compilation | ✅ | self-hosted compiler compiles via LLVM to native EXE (525KB) |
| AI Copilot | ✅ | LightLang code generation toolchain for low-compute scenarios + LoRA fine-tuning |
| C FFI binding | ✅ | four-stage implementation + @C syntax marker: basic FFI → pointer/array → enum/union/variadic → typedef/bitfield/debug |

## Quick Start (3 steps)

### Step 1: Install Python

LightLang needs **Python 3.10+**. Check your version:

```bash
python --version
# output should be Python 3.10.x or higher
```

> No Python? Download from [python.org](https://www.python.org/downloads/).
> Windows users: please tick **Add Python to PATH** during install.

### Step 2: Install LightLang

**Method A: install from source (recommended for developers)**

```bash
git clone https://gitcode.com/skywalk163/light.git
cd light
pip install -e .
```

**Method B: install from PyPI (use only)**

```bash
pip install light
```

Verify after install:

```bash
light --version
# output: 光明编译器 v7.0.0
```

### Step 3: Run your first program

Create a file `hello.light` with this content:

```light
打印 "你好，世界！"
```

Run it:

```bash
light run hello.light
# output: 你好，世界！
```

That's it! No extra dependencies needed.

---

## Syntax Basics

### Variables

```light
设 姓名 为 "张三"
设 年龄 为 25
打印 姓名
打印 年龄
```

### Functions (段落)

```light
段落 加法 接收 a, b：
    返回 a 加上 b

打印 加法(3, 5)    # output: 8
```

### Conditionals

```light
设 分数 为 85

如果 分数 大于等于 90：
    打印 "优秀"
否则如果 分数 大于等于 60：
    打印 "及格"
否则：
    打印 "不及格"
```

### Loops

```light
# while loop
设 计数 为 0
当 计数 小于 5：
    打印 计数
    设 计数 为 计数 加上 1

# for loop
遍历 项 于 1至5：
    打印 项
```

### Strings

```light
设 名字 为 "光明"
打印 "你好，" 加上 名字 加上 "！"
```

## Command-Line Tools

```bash
# run a LightLang program (default SRC backend, no extra deps)
light run hello.light

# compile to a Python file
light compile hello.light -o hello.py

# syntax check
light check hello.light

# type check (three levels: signature / variable / expression)
light check hello.light --type-check 表达式

# standalone type check
light type-check hello.light --level 变量

# view the token stream
light tokens hello.light

# view the AST
light ast hello.light

# initialize a new project
light init myproject
```

### Package Management

```bash
# initialize a new package (creates package.toml and 主.light)
light pkg init myproject

# build the project
light pkg -p myproject build

# run the project
light pkg -p myproject run

# LLVM native compilation
light pkg -p myproject native -o output.exe
```

### Backend Selection

LightLang supports multiple compilation backends:

| Backend | Command | Notes | Extra deps |
|---------|---------|-------|-----------|
| **SRC** (default) | `light run hello.light` | hand-written parser, v3.2 syntax, Python interpretation | **none** |
| ANTLR | `light run hello.light --backend antlr` | ANTLR parser, compatibility mode | `pip install antlr4-python3-runtime` |
| LLVM | `light compile hello.light --backend llvm-typed -o hello.exe` | native compile to EXE | install LLVM/Clang |

**Beginner advice**: just use the default SRC backend; no extra install needed.

### Compile to EXE

To compile a Windows executable:

```bash
# Method 1: PyInstaller (simple, but larger file)
pip install pyinstaller
light compile hello.light -o hello.exe

# Method 2: LLVM native compile (needs LLVM installed)
light compile hello.light --backend llvm-typed -o hello.exe
```

## Standard Library

LightLang ships a rich Chinese standard library under `stdlib/`, organized into **14 stages** and **60+ modules**:

```light
从 数学工具 导入 阶乘
打印 阶乘(10)
```

Highlights by stage:

- **Stage 1 — Core basics**: builtins, math, string processing, filesystem, logging, JSON
- **Stage 2 — Data structures & tools**: datetime, random, sets, itertools, data structures (stack/queue/BST)
- **Stage 3 — System & network**: HTTP requests, process, threads, time management
- **Stage 4 — Encoding & security**: base64/URL codec, symmetric/asymmetric crypto, MD5/SHA hashing
- **Stage 5 — Advanced**: 11 decorators, 13 context managers
- **Stage 6 — Data science**: statistics, matrix ops, linear algebra
- **Stage 7 — Text & parsing**: regex, template engine, CSV, JSON parser
- **Stage 8 — Web & protocols**: HTTP client/server, WebSocket, SMTP, URL tools
- **Stage 9 — Testing & debugging**: unit-test framework, mocks, benchmarks, assertions
- **Stage 10 — Metaprogramming**: AST ops, type-system enhancement, object pool, plugin system, DSL
- **Stage 11 — Security & permissions**: OAuth/JWT, RBAC/ACL, crypto protocols, input sanitization, audit log
- **Stage 12 — Concurrency & distributed**: Actor model, distributed locks, message queue, task scheduler, workflow engine
- **Stage 13 — System utilities**: system interface, external commands, arg parsing, temp files, pretty output, copy, glob, serialization, enum, diff, compression, advanced files, string constants, functools, collections tools
- **Stage 14 — C FFI**: call C dynamic libraries (`.so`/`.dll`) across four evolving stages

> Full module quick-reference: [docs/stdlib.md](docs/stdlib.md)

### C FFI Example

```light
加载库 "libm.so" 为 math。
外部 段落 平方根 接收 输入: 小数 返回 小数 在 math。
外部 结构体 点 { x: 小数, y: 小数 }。
外部 枚举 颜色 { 红 = 0, 绿 = 1, 蓝 = 2 }。

设 结果 为 平方根(16.0)   # calls C's sqrt function
打印 结果                  # output: 4.0

# or use the @C syntax marker (more concise)
@C 段落 绝对值 接收 甲: 小数 返回 小数 在 math。
```

> Docs: [C FFI binding guide](docs/ffi.md)

## Syntax Reference (v3.2)

| Syntax | Meaning | Example |
|--------|---------|---------|
| `设 X 为 Y` | variable declare / assign | `设 年龄 为 25` |
| `段落 名 接收 参数：` | function definition | `段落 加法 接收 a, b：` |
| `如果 条件：` | conditional | `如果 年龄 大于 18：` |
| `否则如果 条件：` | else-if | `否则如果 年龄 大于 12：` |
| `否则：` | else | `否则：` |
| `当 条件：` | while loop | `当 计数 小于 10：` |
| `遍历 变量 于 列表：` | for loop | `遍历 i 于 1至10：` |
| `遍历 变量 在 列表：` | for loop | `遍历 项 在 列表：` |
| `返回 X` | return | `返回 a 加 b` |
| `打印 X` | print | `打印 "你好"` |
| `从 模块 导入 符号` | import from module | `从 数学工具 导入 阶乘` |
| `导入 模块` | import whole module | `导入 数学工具` |
| `导出 符号列表` | export symbols | `导出 加法, 减法` |
| `跳出` | break | `跳出` |
| `跳过` | continue | `跳过` |

### Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `加上` | add | `a 加上 b` |
| `减去` | subtract | `a 减去 b` |
| `乘以` | multiply | `a 乘以 b` |
| `除以` | divide | `a 除以 b` |
| `取余` | modulo | `a 取余 b` |
| `幂` | power | `a 幂 b` |
| `整除` | floor divide | `a 整除 b` |
| `等于` | equal | `a 等于 b` |
| `不等于` | not equal | `a 不等于 b` |
| `大于` / `小于` | greater / less | `a 大于 b` |
| `大于等于` / `小于等于` | ≥ / ≤ | `a 大于等于 b` |
| `且` / `或` / `非` | and / or / not | `a 且 b` |

### Classes & OOP

```light
类 动物：
    属性 名字
    构造 接收 名字：
        己.名字 为 名字
    段落 介绍 接收：
        打印 "我叫" 加上 己.名字

类 狗 继承 动物：
    段落 叫声 接收：
        打印 "汪汪汪"

设 小狗 为 狗("旺财")
小狗.介绍()
小狗.叫声()
```

### Type Annotation & Checking

LightLang supports three-level type checking (signature / variable / expression):

```text
段落 加法 接收 甲:数, 乙:数 -> 数：
    返回 甲 加 乙

严格 段落 计算接收 输入:字符串 -> 字典：
    ...
```

```bash
light check hello.light --type-check 签名
light type-check hello.light --level 表达式
```

## Project Structure

```
light/
├── src/                 # core compiler (actively maintained)
│   ├── lexer.py         # lexical analyzer
│   ├── parser_core.py   # parser core
│   ├── parser_stmt.py   # statement parser
│   ├── parser_expr.py   # expression parser
│   ├── ast_nodes_v3.py  # AST node definitions
│   ├── code_generator.py     # Python code generation
│   ├── code_generator_unified.py  # unified code generation
│   ├── compiler.py      # compiler main
│   ├── type_checker.py  # three-level type checker
│   ├── type_inferencer.py   # HM type inference
│   ├── package_manager.py   # package manager
│   ├── module_resolver.py   # module resolver
│   ├── llvm/            # LLVM backend
│   │   ├── codegen_typed.py  # LLVM codegen (typed mode)
│   │   └── compiler.py       # LLVM compile entry
│   └── optimizer/       # code optimizer
├── cli/                 # command-line tools
│   └── light.py          # main entry (light command, with pkg subcommand)
├── stdlib/              # standard library (60+ modules)
│   ├── FFI.py          # C FFI runtime module (~500 lines)
│   ├── FFI.light        # C FFI LightLang implementation
├── lsp/                 # LSP language server
├── debug-adapter/       # DAP debug adapter
├── tools/               # debuggers and other tools
│   └── ai_copilot/      # AI assistance toolchain
├── demos/               # demo projects
├── examples/            # example programs
├── tests/               # tests
└── docs/                # documentation
```

## Development

### Environment Setup

```bash
# clone
git clone https://gitcode.com/skywalk163/light.git
cd light

# install (development mode)
pip install -e .

# install dev tools (optional)
pip install -e ".[dev]"
```

### Run Tests

```bash
# run core tests
python -m pytest tests/test_parser.py tests/test_lexer.py tests/test_async.py -v

# run unit tests
python -m pytest tests/unit/ -v

# run all tests
python -m pytest tests/ -v
```

Project uses UTF-8 encoding and Chinese comments.

## FAQ

### Q: Runtime reports `No module named 'antlr4'`

**A:** This is an ANTLR backend dependency. Two solutions:

1. **Use the default SRC backend** (recommended, no extra install):
   ```bash
   light run hello.light
   ```
2. **Install the ANTLR runtime** (if you need `--backend antlr`):
   ```bash
   pip install antlr4-python3-runtime
   ```

### Q: `pip install antlr4` fails

**A:** The correct package name is `antlr4-python3-runtime`, not `antlr4`:
```bash
pip install antlr4-python3-runtime
```

### Q: Compiling to EXE fails

**A:** Two ways:

1. **PyInstaller** (simple):
   ```bash
   pip install pyinstaller
   light compile hello.light -o hello.exe
   ```
2. **LLVM** (native compile, needs LLVM installed):
   ```bash
   light compile hello.light --backend llvm-typed -o hello.exe
   ```

### Q: Python version requirement

**A:** LightLang needs Python 3.10 or higher. Check:
```bash
python --version
```

## Documentation

- [Syntax spec v3.2](docs/统一语法规范_v3.2.md)
- [Getting Started](docs/getting-started.md)
- [Architecture](docs/architecture.md)
- [Development Guide](docs/DEVELOPMENT_GUIDE.md)
- [User Manual](docs/USER_MANUAL.md)
- [Toolchain](docs/tools.md) (CLI, debugger, LSP, AI Copilot)
- [AI Copilot LoRA fine-tuning guide](tools/ai_copilot/README_LoRA7B.md)
- [AI Copilot ERNIE fine-tuning guide](tools/ai_copilot/README_SFT.md)

## License

This project is licensed under the MIT License.
