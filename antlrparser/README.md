# 光明 (Light) 语言解释器 — ANTLR 实现

光明是一门中文编程语言，使用 ANTLR4 生成的解析器实现语法分析和解释执行。

## 目录结构

```
antlrparser/
├── light_parser/          # ANTLR 生成的解析器 (v1)
├── light_parser2/         # ANTLR 生成的解析器 (v2)
├── self_hosted/          # 自举解析器（光明自身编写的解析器）
│   ├── tokenizer.light    # 自举分词器
│   ├── parser.light       # 自举解析器
│   └── ast.light          # AST 数据结构
├── test/                 # 测试用例
│   ├── test_interpreter.py   # 解释器核心测试
│   ├── test_module.py        # 模块系统测试
│   ├── test_parser.py        # 解析器测试
│   ├── test_controlflow.py   # 控制流测试
│   ├── test_types.py         # 类型系统测试
│   ├── test_dict.py          # 字典测试
│   ├── sample_*.light         # 示例源码
│   └── mod_*.light            # 模块测试文件
├── web_playground/       # Web 在线演示环境
│   ├── server.py         # Flask 后端
│   ├── test_api.py       # API 测试
│   └── static/           # 前端文件
├── cli.py                # 命令行工具
├── light_interpreter.py   # 解释器核心
├── light_module.py        # 模块解析器
├── light_ast.py           # AST 节点定义
├── light_visitor.py       # ANTLR AST 访问器
├── light_tokenizer.py     # 分词器辅助
├── main.py               # 旧版入口
├── pyproject.toml         # 项目打包配置
└── requirements.txt       # Python 依赖
```

## 快速开始

### 安装依赖

```bash
pip install antlr4-python3-runtime
```

### 运行光明文件

```bash
python cli.py run test/sample_basic.light
```

### 启动 REPL

```bash
python cli.py repl
```

### 启动 Web Playground

```bash
cd web_playground
python server.py
# 访问 http://localhost:5000
```

### 运行测试

```bash
pytest test/ -v
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `light run <file>` | 运行光明文件 |
| `light exec '<code>'` | 直接执行代码字符串 |
| `light repl` | 启动交互式 REPL 环境 |
| `light parse <file>` | 解析并显示 AST 结构 |
| `light tokenize <file>` | 词法分析并显示 Token |

### REPL 命令

在 REPL 环境中支持以下命令：

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/exit` | 退出 REPL |
| `/clear` | 清屏 |
| `/env` | 显示当前环境变量 |

### 示例

```bash
# 运行文件
python cli.py run test/sample_basic.light

# 直接执行
python cli.py exec '打印("你好，世界！")。'

# 启动 REPL
python cli.py repl
光明> 定义甲等于42。
光明> 打印(甲)。
42
光明> /exit
```

## 模块系统

光明支持跨文件模块导入：

```light
从 mod_math 导入《平方》，《阶乘》。

打印("5 的平方："加《平方》(5))。
打印("6 的阶乘："加《阶乘》(6))。
```

特性：
- 递归依赖解析
- 路径继承（从导入文件所在目录查找）
- 缓存机制，防止重复加载
- 循环导入保护

## 语法要点

光明使用中文关键字和标点：

- `定义` — 变量定义：`定义甲等于10。`
- `如果/否则若/否则` — 条件判断
- `遍历` — 列表/字典遍历
- `当` — 条件循环
- `《》段()` — 段落（函数）定义
- `打印` — 输出
- `返回` — 返回值
- `结束` — 块语句结束
- `【】` — 列表字面量
- `之` — 属性访问

## Web Playground

Web 版本提供图形化界面，支持：

- 代码编辑器（Monaco Editor，中文高亮）
- 一键运行、查看 AST/Token 分析
- 内置示例库（9 个示例）
- 一键分享代码

```bash
cd web_playground
python server.py
# 浏览器打开 http://localhost:5000
```

## 自举解析器

`self_hosted/` 目录包含用光明自身编写的解析器，包括：

- `tokenizer.light` — 自举分词器
- `parser.light` — 自举解析器
- `ast.light` — AST 数据结构

配套的 Python 调试脚本可用于验证自举解析器的正确性。

## 语言文档

完整的语言文档和教程请参阅项目根目录下的 [光明语言文档与教程.md](../光明语言文档与教程.md)。

## 许可证

MIT