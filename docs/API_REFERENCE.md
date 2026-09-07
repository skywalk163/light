# 光明（Light）API 参考 v7.0+

> **⚠️ 文档定位**：本文档是**编译器内部 Python API**（compiler/parser/type_system/code_generator 等模块的 Python 接口），面向需要嵌入光明编译器到 Python 程序的开发者。
> - **写光明代码的 API（标准库）**：请看 [stdlib.md](stdlib.md) 的 109 模块速查表，或 [AI编程指南.md](AI编程指南.md) 的「30 个最常用标准库模块」
> - **运行时原生腿能力（711 项）**：请看 [原生腿能力清单.json](原生腿能力清单.json)，或本文档下方「运行时原生腿 API」章节
> - **版本**：正文 v4.2（编译器内部 API），2026-09-07 头部更新；当前实现 v7.0+

## 目录

1. [快速开始](#快速开始)
2. [编译器 API](#编译器-api)
3. [解析器 API](#解析器-api)
4. [类型系统 API](#类型系统-api)
5. [类型推断 API](#类型推断-api)
6. [代码生成 API](#代码生成-api)
7. [模块解析 API](#模块解析-api)
8. [包管理 API](#包管理-api)
9. [标准库](#标准库光明语言-api)
10. [运行时原生腿 API](#运行时原生腿-api711-项能力)
11. [AST 节点](#ast-节点)

---

## 快速开始

### 编译并运行光明代码

```python
import sys
sys.path.insert(0, 'src')

from compiler import LightCompiler

compiler = LightCompiler()
result = compiler.compile("""
    设 消息 为 "你好，光明！"
    打印 消息
""")

if result.success:
    print("生成的 Python 代码:")
    print(result.python_code)
else:
    print("编译错误:", result.errors)
```

### 使用解析器

```python
from light_parser_v3 import LightParser

parser = LightParser()
module = parser.parse("设 x 为 10")
print("AST 节点数:", len(module.statements))
```

---

## 编译器 API

### 模块: `compiler`

#### `LightCompiler` 类

光明主编译器，提供完整的编译流水线。

**方法:**

- `__init__(config: Optional[Dict[str, Any]] = None)`: 初始化编译器
- `compile(source: str, filepath: Optional[str] = None) -> CompileResult`: 编译源代码
- `compile_file(filepath: str) -> CompileResult`: 从文件编译
- `compile_project(project_root: str, entry: str = None) -> CompileResult`: 编译项目

**属性:**

- `parser`: LightParser 实例
- `semantic_analyzer`: SemanticAnalyzer 实例
- `type_inferencer`: TypeInferencer 实例
- `code_generator`: PythonCodeGenerator 实例

---

#### `CompileResult` (dataclass)

编译结果对象。

**属性:**

- `success: bool`: 是否编译成功
- `python_code: str`: 生成的 Python 代码
- `errors: List[str]`: 错误列表
- `warnings: List[str]`: 警告列表
- `ast_raw`: 原始 AST (ast_nodes_v3.Module)
- `ast`: 转换后的 AST (ast_nodes.Module)
- `type_env: Optional[Dict[str, Type]]`: 类型推断结果
- `metadata: Dict[str, Any]`: 附加信息

---

## 解析器 API

### 模块: `light_parser_v3`

#### `LightParser` 类

光明手写解析器，基于 Pratt 风格的表达式解析 + 递归下降语句解析。

**方法:**

- `__init__()`: 创建解析器实例
- `parse(source: str) -> ast_nodes_v3.Module`: 解析完整源代码

**示例:**

```python
from light_parser_v3 import LightParser

parser = LightParser()
module = parser.parse("""
    设 x 为 10
    设 y 为 20
    如果 x < y：
        打印 "x 较小"
""")

for stmt in module.statements:
    print(type(stmt).__name__)
```

### 模块: `lexer`

#### `Lexer` 类

词法分析器，将光明源代码转换为 token 流。

**方法:**

- `__init__(source: str)`
- `tokenize() -> List[Token]`: 返回 token 列表

### 模块: `tokens`

#### `TokenType` 枚举

token 类型：`NUMBER`, `STRING`, `KEYWORD`, `IDENTIFIER`, `OPERATOR`, `DOT`, `COLON`, `COMMA`, `LPAREN`, `RPAREN`, `INDENT`, `DEDENT`, `NEWLINE`, `EOF`

---

## 类型系统 API

### 模块: `type_system`

#### 类型层次

```
Type (基类, 带类型 ID)
├── AnyType
├── UnknownType
├── NullType
├── NumberType
├── StringType
├── BooleanType
├── ListType (包含 element_type)
├── DictType (包含 key_type, value_type)
├── FunctionType (包含 param_types, return_type)
├── ClassType (包含 class_name, methods, fields)
└── TypeVar (泛型变量)
```

#### 可空类型检查

```python
from type_system import NullType, NumberType, TypeUnion, is_nullable_type

num_type = NumberType()
nullable = TypeUnion(NumberType(), NullType())

# 是否可空类型
print(is_nullable_type(nullable))  # True
print(is_nullable_type(num_type))  # False
```

#### 类型合一 (Unification)

```python
from type_system import TypeVar, NumberType, unify

a = TypeVar('a')
result = unify(a, NumberType())
print(result)  # a 被合一为 NumberType
```

---

## 类型推断 API

### 模块: `type_inferencer`

#### `TypeInferencer` 类

基于 Hindley-Milner 的全局类型推断器。

**方法:**

- `__init__()`
- `infer_module(module: Module) -> Dict[str, Type]`: 推断整个模块的类型
- `infer_segment(segment: Paragraph) -> Type`: 推断段落类型
- `get_type(expr) -> Type`: 获取表达式类型

**两阶段推断:**
1. 预扫描：收集所有段落签名
2. 推断：基于 HM 算法推断每个表达式类型

---

## 代码生成 API

### 模块: `code_generator`

#### `PythonCodeGenerator` 类

将光明 AST 编译为 Python 代码。

**方法:**

- `__init__()`
- `generate(module) -> str`: 生成 Python 代码字符串

**示例:**

```python
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

parser = LightParser()
generator = PythonCodeGenerator()

ast = parser.parse("设 消息 为 '你好'")
code = generator.generate(ast)

# 执行生成的代码
exec(code)
```

---

## 模块解析 API

### 模块: `module_resolver`

#### `ModuleResolver` 类

负责解析模块依赖、检测循环依赖，并以拓扑顺序编译。

**方法:**

- `__init__(search_paths: List[str])`
- `resolve_module(module_name: str) -> ResolvedModule`: 查找并编译模块
- `detect_circular_dependency(dep_graph: Dict) -> bool`: 检测循环依赖
- `topological_sort(dep_graph: Dict) -> List[str]`: 模块拓扑排序

**示例:**

```python
from module_resolver import ModuleResolver

resolver = ModuleResolver(search_paths=["./modules", "./stdlib"])
resolved = resolver.resolve_module("我的模块")
```

---

## 包管理 API

### 模块: `package_manager`

#### `PackageManager` 类

基于 TOML 配置的项目级包管理器。

**方法:**

- `__init__(project_root: str)`
- `load_config() -> PackageConfig`: 加载 package.toml
- `init_project(name: str) -> bool`: 在当前目录初始化新项目
- `build_project(entry: str = None) -> BuildResult`: 构建整个项目
- `get_search_paths() -> List[str]`: 获取模块搜索路径

#### `PackageConfig` (dataclass)

项目配置对象。

**字段:**

- `name: str`: 项目名称
- `version: str`: 版本号
- `description: str`: 项目描述
- `authors: List[str]`: 作者列表
- `entry_point: str`: 入口文件
- `dependencies: List[str]`: 依赖列表
- `source_dirs: List[str]`: 源文件目录
- `test_dirs: List[str]`: 测试目录

---

## 标准库（光明语言 API）

光明标准库位于 `stdlib/` 目录，当前包含 **109 个 .light 模块**（每个模块通常有对应的 .py Python 腿实现）。

> **完整模块列表**：请看 [stdlib.md](stdlib.md) 的「模块速查表（109 个 .light 模块，按类别）」，按 15 个类别组织，每模块一句话核心功能。
> **AI 快速参考**：请看 [AI编程指南.md](AI编程指南.md) 的「30 个最常用标准库模块」。

### 最常用模块（10 个）

| 模块 | 核心功能 | 导入示例 |
|------|----------|----------|
| `数学` | 数学运算（平方根/幂/三角/pi/floor/ceil） | `从 数学 导入 平方根, 幂` |
| `统计` | 平均数/中位数/标准差/方差/分位数 | `从 统计 导入 平均数, 标准差` |
| `时间` | 当前时间/时间戳/格式化/睡眠 | `从 时间 导入 当前时间, 睡眠` |
| `文件系统` | 读写/追加/存在/创建目录/列出目录 | `从 文件系统 导入 读取, 写入` |
| `JSON` | JSON 解析/序列化/美化 | `从 JSON 导入 解析, 序列化` |
| `字符串处理` | 分割/替换/查找/截取/去空白 | `从 字符串处理 导入 分割, 替换` |
| `哈希` | MD5/SHA1/SHA256/SHA512/HMAC（runtime C） | `从 哈希 导入 sha256, hmac` |
| `网络请求` | HTTP客户端（HTTPS/POST/重定向/超时） | `从 网络请求 导入 获取, POST` |
| `参数解析` | 命令行参数解析 | `从 参数解析 导入 解析器, 添加参数` |
| `日志` | 日志记录/级别/格式化 | `从 日志 导入 记录, 信息, 错误` |

### 使用示例

```光明
从 数学 导入 平方根
从 文件系统 导入 写入
从 JSON 导入 序列化

设 值 为 平方根(16)
设 数据 为 {"结果": 值}
写入("output.json", 序列化(数据))
```

---

## 运行时原生腿 API（711 项能力）

光明的 LLVM 原生编译路径有一个 C 语言 runtime（`src/llvm/runtime_typed.c`），提供 **711 项原生腿能力**：
- **builtin 411 项**：编译器内建函数（算术/字符串/容器/类型转换等）
- **runtime 262 项**：C 运行时库函数（TLS/哈希/编码/序列化/对象池等）

### runtime C 层关键能力

| 类别 | 能力 | 说明 |
|------|------|------|
| **TLS/网络** | Schannel (Windows) / mbedTLS (POSIX) | HTTPS 握手/证书校验/读写，API 跨平台对齐 |
| **哈希** | MD5 / SHA1 / SHA256 / SHA512 / HMAC / PBKDF2 | runtime C 实现，非 LLVM 路径也可用 |
| **编码** | Base64 / URL编码 / 十六进制 | 编解码 |
| **序列化** | 嵌套容器序列化（深度上限）/ 反序列化 | 列表/字典/字符串嵌套 |
| **对象池** | 槽位池 / 复用 / 放入获取 | 性能优化 |
| **UUID** | v1 / v3 / v4 / v5 | v3/v5 与 CPython 逐字符一致 |
| **字符串** | 拼接/分割/替换/查找/格式化 | 中文安全 |
| **容器** | 列表/字典/集合 创建与操作 | dv_* 系列函数 |
| **类型转换** | 转字符串/转整数/转浮点/转布尔 | 多态 |

### 能力清单查询

完整 711 项能力清单（JSON 格式）：`docs/原生腿能力清单.json`

重建能力清单：
```bash
python scripts/gen_native_capability_json.py
```

校验能力清单：
```bash
python -m pytest tests/unit/test_native_leg_capability.py -q
```

> **注意**：runtime C 层 API 是内部实现细节，光明代码通过标准库模块（`哈希`/`网络请求`/`Base64` 等）间接调用，不需要直接调用 C 函数。

---

## AST 节点

### 模块: `ast_nodes_v3`

#### 语句节点

- `Module`: 模块根节点，包含多个语句
- `VarDecl`: 变量声明（定义/设）
- `Paragraph`: 段落定义（函数）
- `IfStmt`: 条件语句（如果/若）
- `ForEachStmt`: 遍历语句
- `WhileStmt`: 当循环
- `ReturnStmt`: 返回语句
- `BreakStmt`: 跳出循环
- `ContinueStmt`: 跳过当前迭代
- `PrintStmt`: 显示/打印语句
- `ImportStmt`: 导入语句
- `ClassInstantiation`: 类实例化

#### 表达式节点

- `NumberLiteral`: 数字字面量
- `StringLiteral`: 字符串字面量
- `BooleanLiteral`: 布尔字面量
- `NullLiteral`: 空字面量
- `Variable`: 变量引用
- `BinaryOperation`: 二元运算（加/减/乘/除/等于/小于...）
- `FunctionCall`: 段落/函数调用
- `ListLiteral`: 列表字面量 `[...]`
- `IndexAccess`: 下标访问 `列表[索引]`
- `MemberAccess`: 成员访问 `对象.属性`
- `UnwrapExpression`: 可空解包 `值!`
- `StringInterpolation`: 字符串插值
- `LambdaExpression`: Lambda 表达式
- `ListComprehension`: 列表推导式
- `DictComprehension`: 字典推导式

#### 面向对象节点

- `ClassDefinition`: 类定义
- `InterfaceDefinition`: 接口定义
- `MethodSignature`: 方法签名

---

## CLI 命令行工具

### `light` 命令 (REPL/运行)

```bash
# 交互式 REPL
python -m cli.light

# 运行单个文件
python -m cli.light examples/hello.light

# 执行代码片段
python -m cli.light -c '打印 "你好"'
```

### `lightc` 命令 (编译器)

```bash
# 编译文件为 Python
python -m cli.lightc examples/hello.light

# 编译并运行
python -m cli.lightc examples/hello.light --run

# 指定输出文件
python -m cli.lightc examples/hello.light -o hello.py
```

### 项目管理

```bash
# 初始化新项目
python -m cli.lightc init my_project

# 构建项目
python -m cli.lightc build

# 运行项目
python -m cli.lightc run
```

---

## package.toml 配置

```toml
name = "我的项目"
version = "4.2.0"
description = "光明示例项目"
authors = ["作者名"]

[compiler]
entry_point = "main.light"
source_dirs = ["src", "modules"]
test_dirs = ["tests"]
target = "python"

[dependencies]
# 其他光明包
```

---

## 版本信息

当前版本可通过以下方式查询:

```python
from compiler import LightCompiler

c = LightCompiler()
print(c.version())  # 4.2.0
```

---

*本文件随光明 v4.2 同步更新*
