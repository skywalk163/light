# 光明（Light）开发指南

## 项目概述

光明（Light）是一款以中文为基础的编程语言，旨在为中文用户提供更自然、更直观的编程体验。

## 目录结构

```
light/
├── antlrparser/          # ANTLR4 解析器实现
│   ├── light_parser/      # 生成的解析器代码
│   ├── runtime/          # C 语言运行时库
│   ├── scripts/          # 构建脚本
│   ├── test/             # 测试用例
│   ├── web_playground/   # Web 在线编辑器
│   └── self_hosted/      # 自举测试代码
├── bootstrap/            # 自举相关代码
├── docs/                 # 文档
│   ├── specs/            # 规格说明文档
│   └── superpowers/      # 进阶功能设计文档
├── examples/             # 示例代码
│   ├── modules/          # 模块示例
│   └── bootstrap_*.light  # 自举示例
├── src/                  # 核心源代码
│   ├── llvm/             # LLVM 后端
│   ├── optimizer/        # 优化器
│   └── stdlib/           # 标准库
└── tests/                # 测试套件
```

## 开发环境设置

### 1. 安装 Python

确保安装 Python 3.10 或更高版本：

```bash
python --version
```

### 2. 创建虚拟环境

```bash
cd light
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements-dev.txt
```

### 4. 安装 LLVM（编译支持）

下载并安装 LLVM 16.0+：
- Windows: https://github.com/llvm/llvm-project/releases
- macOS: `brew install llvm`
- Linux: `sudo apt install llvm`

设置环境变量（Windows）：
```bash
set LLVM_BIN=E:\Program Files\LLVM\bin
```

## 生成解析器

修改语法文件 `antlrparser/LightLang.g4` 后，运行生成脚本：

```bash
cd antlrparser
.\scripts\generate.ps1
```

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_parser.py -v

# 运行性能测试
python tests/performance_benchmark.py
```

## 使用命令行工具

```bash
# 解析并显示 AST
python antlrparser/light_cli.py parse test.light

# 解释执行
python antlrparser/light_cli.py run test.light

# 编译为可执行文件
python antlrparser/light_cli.py compile test.light -o output
```

## 代码规范

### Python 代码规范

- 使用 `black` 进行代码格式化
- 使用 `flake8` 进行代码检查
- 使用 `isort` 进行导入排序

```bash
black antlrparser/
flake8 antlrparser/
isort antlrparser/
```

### 命名规范

- Python 文件：小写加下划线，如 `light_ast.py`
- 类名：大驼峰，如 `DuanVisitor`
- 函数/方法：小写加下划线，如 `visit_class_def`
- 变量：小写加下划线，如 `segment_name`

## 调试技巧

### 1. 调试解析器

```python
from antlrparser.light_visitor import parse_source

source = """
定义 x 等于 10。
打印(x)。
"""

module = parse_source(source)
print(module)
```

### 2. 调试解释器

```python
from antlrparser.light_interpreter import run_source

result = run_source("定义 x 等于 5 加 3。打印(x)。")
print(result.get_output())
```

### 3. 调试编译器

```python
import sys
sys.path.insert(0, 'src')
from llvm.compiler import compile_source_typed

# 编译光明源码为 LLVM IR
ir = compile_source_typed('打印("hello")', verbose=True)
print(ir)
```

更多示例参见 `tests/test_level8_llvm.light`。

## 开发流程

1. **修改语法** → 更新 `src/light_parser_v3.py`
2. **更新 AST** → 修改 `src/ast_nodes.py`
3. **更新适配器** → 修改 `src/compiler.py`（AstAdapter）
4. **更新解释器** → 修改 `src/code_generator.py`
5. **更新 LLVM 后端** → 修改 `src/llvm/codegen_typed.py`（TypedLLVMCodeGen）
6. **编写测试** → 在 `tests/` 添加测试
7. **运行测试** → `pytest`

## 发布流程

```bash
# 构建包
python -m build

# 发布到 PyPI
twine upload dist/*
```

## 常见问题

### Q: 解析器生成失败

**A:** 确保已安装 `antlr4-tools`：
```bash
pip install antlr4-tools
```

### Q: 编译失败

**A:** 检查 LLVM 路径是否正确配置，确保 `clang.exe` 可访问。

### Q: 中文显示乱码

**A:** 确保终端编码为 UTF-8：
```bash
chcp 65001  # Windows
export LC_ALL=en_US.UTF-8  # Linux/macOS
```

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

### 1. Fork 仓库

首先 Fork 光明仓库到您的 GitHub 账户。

### 2. 创建特性分支

```bash
git checkout -b feature/xxx   # 特性开发
git checkout -b fix/xxx       # Bug 修复
git checkout -b docs/xxx      # 文档更新
```

### 3. 提交更改

请遵循 Conventional Commits 规范：

```bash
# 特性开发
git commit -m 'feat: 添加类型注解支持'

# Bug 修复
git commit -m 'fix: 修复变量声明解析错误'

# 文档更新
git commit -m 'docs: 更新开发指南'

# 代码重构
git commit -m 'refactor: 优化代码生成器'

# 测试更新
git commit -m 'test: 添加类型注解测试用例'
```

### 4. 推送到分支

```bash
git push origin feature/xxx
```

### 5. 创建 Pull Request

在 GitHub 上创建 Pull Request，并描述您的更改内容。

### 贡献类型

| 类型 | 说明 |
|------|------|
| **特性开发** | 添加新功能，如类型系统、新语法等 |
| **Bug 修复** | 修复已知问题 |
| **文档更新** | 更新文档、添加示例 |
| **代码重构** | 优化代码结构，不改变功能 |
| **性能优化** | 提升编译器/解释器性能 |
| **标准库扩展** | 添加新的标准库模块 |

### PR 检查清单

- [ ] 代码遵循项目代码规范
- [ ] 添加了相应的测试用例
- [ ] 所有测试通过 (`pytest`)
- [ ] 文档已更新（如需要）
- [ ] 提交信息符合规范

## 标准库模块添加流程

### 1. 创建模块文件

在 `src/stdlib/` 目录下创建新的模块文件：

```bash
touch src/stdlib/my_module.py
```

### 2. 实现模块功能

模块文件应导出一个 `light_module` 字典，包含模块名称和导出的函数/类：

```python
# src/stdlib/my_module.py

def 我的函数(参数):
    """函数说明"""
    return 参数

light_module = {
    'name': '我的模块',
    'exports': {
        '我的函数': 我的函数,
    }
}
```

### 3. 注册模块

在 `src/stdlib/__init__.py` 中注册新模块：

```python
# src/stdlib/__init__.py

MODULES = {
    # ... 现有模块 ...
    '我的模块': 'my_module',
}
```

### 4. 添加测试

在 `tests/` 目录下创建对应的测试文件：

```python
# tests/test_my_module.py

def test_my_function():
    from stdlib.my_module import 我的函数
    assert 我的函数(10) == 10
```

### 5. 运行测试

```bash
pytest tests/test_my_module.py -v
```

### 标准库模块规范

- 模块名使用中文
- 函数/类名使用中文
- 提供详细的文档字符串
- 遵循光明命名规范
- 确保跨平台兼容性

## 代码审查流程

1. PR 创建后，自动运行 CI 测试
2. 核心开发人员进行代码审查
3. 根据反馈进行修改
4. 审查通过后合并到主分支

## 问题反馈

如果遇到问题或有建议，请在 GitHub Issues 中提交：

- **Bug 报告**: 描述问题、复现步骤、期望结果
- **功能请求**: 描述期望的功能
- **文档问题**: 描述文档中的问题

## 许可证

MIT License - 详见 LICENSE 文件