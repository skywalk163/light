# 光明（Light）开发指南

> **最后更新：** 2026-08-07
> **适用版本：** v6.1.0

欢迎阅读光明开发指南！本文档面向所有希望参与光明开发的贡献者，从环境搭建到代码提交流程，从编码规范到测试要求，提供全面的指导。

---

## 目录

1. [项目概述](#1-项目概述)
2. [开发环境设置](#2-开发环境设置)
3. [目录结构](#3-目录结构)
4. [开发工作流程](#4-开发工作流程)
5. [代码风格指南](#5-代码风格指南)
6. [PR 审查流程](#6-pr-审查流程)
7. [测试要求](#7-测试要求)
8. [文档要求](#8-文档要求)
9. [提交信息规范](#9-提交信息规范)
10. [Good First Issue 推荐](#10-good-first-issue-推荐)
11. [调试技巧](#11-调试技巧)
12. [常见问题](#12-常见问题)

---

## 1. 项目概述

光明（Light）是一款以中文为基础的编程语言，旨在为中文用户提供更自然、更直观的编程体验。

### 技术栈

| 组件 | 技术 |
|------|------|
| 编译器实现 | Python 3.10+ |
| 语法解析 | ANTLR4 + 手写解析器（双后端） |
| 类型系统 | HM 类型推断 + 三级类型检查 |
| 代码生成 | Python 代码生成 + LLVM 原生编译 |
| 包管理 | lightpub 注册中心 |
| 工具链 | LSP、DAP 调试器、AI Copilot |

### 核心原则

1. **中文优先**：关键字使用中文，同时兼容英文写法
2. **工程化优先**：完整的工具链和包管理生态
3. **AI 原生集成**：AI Copilot 作为编译器的一部分
4. **开源治理**：MIT 许可证，开放透明的社区

---

## 2. 开发环境设置

### 2.1 基础环境要求

| 依赖 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Python | 3.10 | 3.12 |
| pip | 21.0 | 24.0+ |
| Git | 2.30 | 2.40+ |

### 2.2 克隆仓库

```bash
git clone https://github.com/skywalk163/light.git
cd light
```

### 2.3 创建虚拟环境

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 2.4 安装依赖

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 或使用可选依赖组
pip install -e ".[dev,antlr,repl]"
```

### 2.5 安装 LLVM（编译支持，可选）

下载并安装 LLVM 16.0+：
- **Windows**：https://github.com/llvm/llvm-project/releases
- **macOS**：`brew install llvm`
- **Linux**：`sudo apt install llvm`

设置环境变量：

```bash
# Windows
set LLVM_BIN=E:\Program Files\LLVM\bin

# macOS/Linux
export LLVM_CONFIG=/usr/local/opt/llvm/bin/llvm-config
```

### 2.6 验证安装

```bash
python -m cli.light --version
# 应输出：光明 v6.2.0

python -m cli.light run examples/hello.light
# 应输出：你好，光明！
```

---

## 3. 目录结构

```
light/
├── antlrparser/              # ANTLR4 解析器实现
│   ├── light_parser/          # 生成的解析器代码
│   ├── runtime/              # C 语言运行时库
│   ├── scripts/              # 构建脚本
│   ├── test/                 # 测试用例
│   ├── web_playground/       # Web 在线编辑器
│   └── self_hosted/          # 自举测试代码
├── bootstrap/                # 自举相关代码
├── cli/                      # 命令行工具
│   ├── light.py               # 主 CLI 入口
│   ├── light_unified.py       # 统一编译器 CLI
│   └── lightc.py              # 编译运行工具
├── docs/                     # 文档
│   ├── blog/                 # 技术博客
│   ├── community/            # 社区文档
│   ├── specs/                # 规格说明文档
│   └── superpowers/          # 进阶功能设计文档
├── examples/                 # 示例代码
│   ├── modules/              # 模块示例
│   └── bootstrap_*.light      # 自举示例
├── src/                      # 核心源代码
│   ├── llvm/                 # LLVM 后端
│   ├── optimizer/            # 优化器
│   └── stdlib/               # 标准库
├── tests/                    # 测试套件
└── tools/                    # 工具链
    ├── ai_copilot/           # AI Copilot
    ├── lsp/                  # 语言服务器
    └── repl/                 # 交互式 REPL
```

---

## 4. 开发工作流程

### 4.1 标准开发流程

光明采用 **基于分支的开发流程**，每个功能或修复在独立分支上开发，经审查后合并到主分支。

```
1. 选择 Issue → 2. 创建分支 → 3. 开发 → 4. 编写测试 → 5. 本地测试
    → 6. 提交代码 → 7. 推送分支 → 8. 创建 PR → 9. 代码审查
    → 10. 合并到主分支
```

### 4.2 分支命名规范

| 分支类型 | 命名格式 | 示例 |
|----------|----------|------|
| 特性开发 | `feature/xxx` | `feature/json-stream-parser` |
| Bug 修复 | `fix/xxx` | `fix/lexer-unicode-bug` |
| 文档更新 | `docs/xxx` | `docs/update-api-reference` |
| 代码重构 | `refactor/xxx` | `refactor/optimizer-arch` |
| 性能优化 | `perf/xxx` | `perf/llvm-inline-pass` |
| 测试更新 | `test/xxx` | `test/add-type-check-cases` |

### 4.3 从 Issue 开始

1. 在 [GitHub Issues](https://github.com/skywalk163/light/issues) 中找到你想解决的问题
2. 如果没有相关 Issue，先创建一个（建议先讨论再动手）
3. 在 Issue 下留言说明你想参与，等待维护者确认
4. 确认后开始开发

### 4.4 创建分支

```bash
# 确保主分支是最新的
git checkout main
git pull upstream main

# 创建特性分支
git checkout -b feature/xxx
```

### 4.5 开发与测试

```bash
# 修改代码后运行测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_parser.py -v

# 运行特定测试用例
pytest tests/test_parser.py::test_parse_variable -v
```

### 4.6 提交与推送

```bash
# 查看变更
git status
git diff

# 暂存修改
git add src/compiler.py tests/test_compiler.py

# 提交（遵循提交信息规范）
git commit -m "feat: 添加 JSON 流式解析支持"

# 推送到远程
git push origin feature/xxx
```

### 4.7 创建 Pull Request

在 GitHub 上创建 PR 时，请确保：

1. PR 标题清晰描述变更内容
2. PR 描述包含变更动机和实现方式
3. 关联相关的 Issue 编号
4. 勾选 PR 检查清单中的所有项目
5. 添加适当的标签（如 `feature`、`bug`、`docs`）

---

## 5. 代码风格指南

### 5.1 Python 代码风格

光明项目使用以下工具保证代码风格一致性：

```bash
# 代码格式化
black src/ tests/

# 导入排序
isort src/ tests/

# 代码检查
flake8 src/ tests/

# 类型检查
mypy src/
```

#### 配置说明

| 工具 | 配置 | 说明 |
|------|------|------|
| **black** | 行宽 120，Python 3.10+ | 自动格式化，无商量余地 |
| **isort** | 使用 black 兼容模式 | 自动排序导入语句 |
| **flake8** | 行宽 120，忽略 E203/E501 | 代码质量检查 |
| **mypy** | Python 3.10，忽略缺失导入 | 可选的类型检查 |

### 5.2 Python 命名规范

| 类别 | 规范 | 示例 |
|------|------|------|
| 文件名 | 小写加下划线 | `light_ast.py`、`code_generator.py` |
| 类名 | 大驼峰（PascalCase） | `LightVisitor`、`AstAdapter`、`LLVMCodeGen` |
| 函数/方法 | 小写加下划线（snake_case） | `visit_class_def`、`parse_source` |
| 变量 | 小写加下划线（snake_case） | `segment_name`、`token_list` |
| 常量 | 全大写加下划线 | `MAX_CACHE_SIZE`、`DEFAULT_OPT_LEVEL` |
| 私有成员 | 前导下划线 | `_convert_module`、`_token_cache` |
| 特殊方法 | 双下划线包围 | `__init__`、`__str__`、`__repr__` |

### 5.3 Python 代码示例

```python
# ✅ 好的代码风格
class Tokenizer:
    """光明词法分析器"""

    def __init__(self, max_length: int = 100):
        self._max_length = max_length
        self._tokens: List[Token] = []
        self._position = 0

    def tokenize(self, source: str) -> List[Token]:
        """将源代码解析为 Token 列表"""
        if not source:
            return []

        for line_num, line in enumerate(source.split('\n'), 1):
            tokens = self._tokenize_line(line, line_num)
            self._tokens.extend(tokens)

        return self._tokens

    def _tokenize_line(self, line: str, line_num: int) -> List[Token]:
        """处理单行代码"""
        tokens = []
        for char in line:
            if char.isspace():
                continue
            tokens.append(Token(char, line_num))
        return tokens
```

```python
# ❌ 不好的代码风格
class tokenizer:  # 类名应使用大驼峰
    def __init__(s, ml=100):  # 参数名应清晰
        s.ml = ml
        s.t = []  # 变量名应有意义
        s.p = 0

    def Parse(self, src):  # 函数名应使用小写加下划线
        # 缺少文档字符串
        for i, l in enumerate(src.split('\n'), 1):
            for c in l:
                if c.isspace():
                    continue
                s.t.append(Token(c, i))  # 使用 self 而非 s
```

### 5.4 光明代码风格

光明代码本身也应遵循一致的风格：

```光明
# ✅ 好的光明代码风格
段落 计算平均值 接收 数字列表:
    """计算数字列表的平均值"""
    如果 数字列表 为空:
        返回 0

    设 总和 为 0
    遍历 数字 于 数字列表:
        总和 为 总和 + 数字

    返回 总和 / 数字列表.长度

# 使用清晰的变量名
设 用户列表 为 ["张三", "李四", "王五"]
遍历 用户 于 用户列表:
    打印("你好, ", 用户)
```

```光明
# ❌ 不好的光明代码风格
段落 a 接收 x:  # 名称应有意义
    设 s 为 0  # 变量名应清晰
    遍历 y 于 x:
        s 为 s + y
    返回 s
```

### 5.5 导入顺序

导入语句应遵循以下顺序（每组之间空一行）：

1. **标准库**：`os`、`sys`、`json`、`pathlib` 等
2. **第三方库**：外部依赖
3. **本地模块**：项目内部模块

```python
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pytest  # 第三方库

from lexer import Lexer, LexerError  # 本地模块
from tokens import Token, TokenType
```

---

## 6. PR 审查流程

### 6.1 审查流程概述

```
PR 提交 → CI 自动检查 → 至少 1 位维护者审查 → 修改反馈 → 批准 → 合并
```

### 6.2 PR 检查清单

提交 PR 前，请逐项确认：

- [ ] 代码遵循项目代码规范（通过 `black`、`flake8`、`isort` 检查）
- [ ] 添加了相应的测试用例
- [ ] 所有测试通过（`pytest tests/ -v`）
- [ ] 新功能已更新文档
- [ ] 提交信息符合规范
- [ ] PR 描述清晰，包含变更动机和实现方式
- [ ] 关联了相关 Issue 编号
- [ ] 没有引入新的依赖（除非必要）
- [ ] 兼容所有支持的操作系统（Windows/macOS/Linux）

### 6.3 审查者注意事项

审查 PR 时，请关注以下方面：

| 审查维度 | 关注点 |
|----------|--------|
| **正确性** | 代码逻辑是否正确？边界情况是否处理？ |
| **性能** | 是否有性能问题？是否需要优化？ |
| **安全性** | 是否有安全漏洞？输入是否经过验证？ |
| **可维护性** | 代码是否易于理解和维护？ |
| **测试覆盖** | 测试是否充分？是否覆盖关键路径？ |
| **文档** | 是否需要更新文档？代码注释是否清晰？ |
| **兼容性** | 是否向后兼容？是否有破坏性变更？ |

### 6.4 审查流程时间

| PR 类型 | 预期响应时间 | 预期合并时间 |
|---------|-------------|-------------|
| 紧急 Bug 修复 | 24 小时内 | 1-3 天 |
| 普通 Bug 修复 | 3 天内 | 3-7 天 |
| 新功能 | 1 周内 | 1-2 周 |
| 文档更新 | 3 天内 | 3-5 天 |
| 大型重构 | 2 周内 | 2-4 周 |

### 6.5 合并策略

- **小型修复**：使用 Squash Merge，保持历史简洁
- **功能开发**：使用 Rebase Merge，保持提交历史清晰
- **大型功能**：使用 Merge Commit，保留功能分支历史

---

## 7. 测试要求

### 7.1 测试类型

光明项目包含以下测试类型：

| 测试类型 | 位置 | 说明 |
|----------|------|------|
| 单元测试 | `tests/` | 测试单个模块或函数 |
| 集成测试 | `tests/` | 测试多个模块的协作 |
| 端到端测试 | `tests/` | 测试完整编译链路 |
| 性能测试 | `tests/` | 基准测试和性能分析 |
| 回归测试 | `tests/` | 防止已修复的 Bug 再次出现 |

### 7.2 测试工具

```bash
# 运行所有测试
pytest tests/ -v

# 运行带覆盖率报告
pytest tests/ --cov=src --cov-report=term-missing

# 运行特定测试文件
pytest tests/test_parser.py -v

# 运行特定测试用例
pytest tests/test_parser.py::test_parse_variable -v

# 运行性能测试
python tests/performance_benchmark.py
```

### 7.3 测试编写规范

#### 单元测试示例

```python
# tests/test_lexer.py
import pytest
from lexer import Lexer


class TestLexer:
    """词法分析器测试"""

    def setup_method(self):
        self.lexer = Lexer()

    def test_tokenize_simple_variable(self):
        """测试变量声明词法分析"""
        tokens = self.lexer.tokenize("设 甲 为 42。")
        assert len(tokens) > 0
        assert tokens[0].value == "设"

    @pytest.mark.parametrize("source,expected", [
        ("设 甲 为 10。", "设"),
        ("打印 结果", "打印"),
        ("如果 甲 大于 5：", "如果"),
    ])
    def test_keyword_tokens(self, source, expected):
        """测试关键字词法分析（参数化）"""
        tokens = self.lexer.tokenize(source)
        assert tokens[0].value == expected

    def test_empty_source(self):
        """测试空源码"""
        tokens = self.lexer.tokenize("")
        assert tokens == []

    def test_unicode_support(self):
        """测试中文 Unicode 支持"""
        source = "打印('你好，世界！')"
        tokens = self.lexer.tokenize(source)
        assert len(tokens) > 0
```

#### 测试编写原则

1. **每个测试只测一个功能点**：一个测试用例只验证一个行为
2. **使用有意义的测试名称**：`test_xxx` 格式，清晰描述测试场景
3. **覆盖边界情况**：空输入、极限值、异常情况
4. **测试文档字符串**：说明测试的目的和预期行为
5. **参数化测试**：使用 `@pytest.mark.parametrize` 减少重复代码

### 7.4 测试覆盖率要求

| 模块 | 最低覆盖率要求 | 目标覆盖率 |
|------|---------------|-----------|
| 词法分析器 | 90% | 95% |
| 语法解析器 | 85% | 90% |
| 类型检查器 | 80% | 85% |
| 代码生成器 | 75% | 85% |
| 标准库 | 70% | 80% |
| LLVM 后端 | 60% | 75% |

---

## 8. 文档要求

### 8.1 文档类型

| 文档类型 | 位置 | 说明 |
|----------|------|------|
| API 文档 | `docs/api/` | 标准库 API 参考 |
| 用户文档 | `docs/` | 用户手册、教程、指南 |
| 技术博客 | `docs/blog/` | 版本发布、技术分享 |
| 社区文档 | `docs/community/` | 社区运营、贡献指南 |
| 代码注释 | 源代码中 | 模块、类、函数的文档字符串 |

### 8.2 Python 文档字符串规范

光明项目使用 Google 风格的文档字符串：

```python
def parse_source(source: str, strict: bool = True) -> ast.Module:
    """解析光明源代码为 AST 模块

    支持完整的光明语法的解析，包括异常处理、模式匹配等特性。

    Args:
        source: 光明源代码字符串
        strict: 是否启用严格模式（默认开启）。
                严格模式下会抛出所有解析错误。

    Returns:
        解析后的 AST 模块对象

    Raises:
        ParseError: 解析失败时抛出
        LexerError: 词法分析失败时抛出

    Examples:
        >>> module = parse_source("设 甲 为 42。")
        >>> print(module.segments[0].name)
        甲
    """
```

### 8.3 文档编写原则

1. **中文优先**：用户文档使用中文编写
2. **示例驱动**：每个功能点都附带代码示例
3. **保持更新**：代码变更时同步更新文档
4. **新手友好**：避免假设读者有专业背景
5. **可搜索性**：使用有意义的标题和关键词

### 8.4 文档更新流程

```
代码变更 → 检查是否需要更新文档 → 更新文档 → 在 PR 中说明文档变更
```

---

## 9. 提交信息规范

### 9.1 提交信息格式

光明项目遵循 **Conventional Commits** 规范：

```
<类型>: <简短描述>

<详细描述（可选）>

<关联 Issue（可选）>
```

### 9.2 提交类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加 JSON 流式解析支持` |
| `fix` | Bug 修复 | `fix: 修复变量声明解析错误` |
| `docs` | 文档更新 | `docs: 更新 API 参考文档` |
| `refactor` | 代码重构 | `refactor: 优化代码生成器结构` |
| `perf` | 性能优化 | `perf: 优化词法分析器缓存` |
| `test` | 测试更新 | `test: 添加类型注解测试用例` |
| `style` | 代码风格 | `style: 修复 flake8 警告` |
| `chore` | 构建/工具 | `chore: 更新项目依赖版本` |
| `ci` | CI 配置 | `ci: 添加 GitHub Actions 工作流` |

### 9.3 提交信息示例

```
feat: 添加 JSON 流式解析支持

为 JSON 模块添加流式解析能力，支持逐行解析大型 JSON 文件。
内存占用降低 60%，适用于大数据处理场景。

Closes #123
```

```
fix: 修复变量声明解析错误

修复了当变量名包含数字时解析器报错的问题。
现在变量名可以包含数字，如「变量1」「数据2」等。

Fixes #456
```

```
docs: 更新开发指南

添加了测试编写规范和文档编写规范章节，
让贡献者更容易了解项目标准。
```

### 9.4 提交信息规范检查

```bash
# 使用 commitlint 检查提交信息
npx commitlint --edit
```

---

## 10. Good First Issue 推荐

### 10.1 适合新贡献者的任务类型

如果你是第一次参与光明开发，以下任务类型是不错的起点：

| 任务类型 | 难度 | 所需技能 | 预计时间 |
|----------|------|----------|----------|
| 文档改进 | ⭐ | Markdown 写作 | 1-2 小时 |
| Bug 报告 | ⭐ | 使用光明的经验 | 30 分钟 |
| 测试用例编写 | ⭐⭐ | Python 基础 | 2-4 小时 |
| 简单 Bug 修复 | ⭐⭐ | Python + 简单编译器知识 | 4-8 小时 |
| 示例代码 | ⭐⭐ | 光明编程 | 2-4 小时 |
| 标准库函数 | ⭐⭐⭐ | Python 编程 | 4-8 小时 |

### 10.2 推荐的 Good First Issue

#### 文档类

1. **改进文档示例代码**：检查文档中的代码示例是否可运行，修正错误
2. **补充 API 文档**：为标准库模块添加缺失的 API 文档
3. **翻译文档**：帮助将中文文档翻译为英文
4. **修正错别字**：扫描文档中的错别字和语法错误

#### 测试类

1. **添加边界测试**：为现有模块添加边界情况测试用例
2. **参数化测试**：将重复的测试用例重构为参数化测试
3. **测试覆盖率提升**：为低覆盖率的模块添加测试

#### 代码类

1. **改进错误信息**：将英文错误信息改为中文
2. **添加简单标准库函数**：如字符串处理、数学计算等
3. **代码清理**：移除废弃代码、修复 lint 警告
4. **示例项目**：用光明编写有趣的示例程序

### 10.3 新手入门步骤

1. **设置开发环境**：按照[环境设置](#2-开发环境设置)完成配置
2. **运行测试**：确保所有测试通过
3. **选择一个 Good First Issue**：在 Issues 中查找 `good first issue` 标签
4. **在 Issue 下留言**：说明你想参与
5. **开始开发**：按照[开发工作流程](#4-开发工作流程)进行
6. **寻求帮助**：遇到问题在 Discussions 中提问

### 10.4 新手常见问题

**Q: 我不熟悉编译器开发，能参与吗？**
A: 当然可以！光明项目有很多非编译器核心的贡献机会，如文档、测试、示例、工具链等。

**Q: 我需要很强的 Python 技能吗？**
A: 基础的 Python 技能就可以参与文档、测试和简单修复。随着参与深入，你会逐渐学习更多。

**Q: 如何获得帮助？**
A: 在 GitHub Discussions 的「问题求助」分类提问，或直接 @ 维护者。

---

## 11. 调试技巧

### 11.1 调试解析器

```python
from antlrparser.light_visitor import parse_source

source = """
定义 x 等于 10。
打印(x)。
"""

module = parse_source(source)
print(module)
```

### 11.2 调试解释器

```python
from antlrparser.light_interpreter import run_source

result = run_source("定义 x 等于 5 加 3。打印(x)。")
print(result.get_output())
```

### 11.3 调试编译器

```python
import sys
sys.path.insert(0, 'src')
from compiler import LightCompiler

# 创建编译器实例
compiler = LightCompiler()

# 完整编译流程
result = compiler.compile('设 甲 为 42。打印(甲)。')

# 查看 Token 流
print("Tokens:", result['tokens'])

# 查看 AST
print("AST:")
print(compiler.describe(result['ast']))

# 查看错误
if compiler.errors:
    print("Errors:", compiler.errors)
```

### 11.4 调试 LLVM 后端

```python
import sys
sys.path.insert(0, 'src')
from llvm.compiler import compile_source_typed

# 编译光明源码为 LLVM IR
ir = compile_source_typed('打印("hello")', verbose=True)
print(ir)
```

### 11.5 使用日志调试

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 在代码中插入日志
logger = logging.getLogger(__name__)
logger.debug("正在解析变量声明: %s", var_name)
```

---

## 12. 常见问题

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

### Q: 测试失败

**A:** 检查是否安装了所有开发依赖：
```bash
pip install -r requirements-dev.txt
```

### Q: 如何添加新的标准库模块？

请参考[标准库模块添加流程](#标准库模块添加流程)章节。

### Q: 如何报告问题？

在 GitHub Issues 中提交，使用对应的 Issue 模板。

---

## 附录：标准库模块添加流程

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
- 所有函数应有类型注解
- 提供完整的单元测试

---

## 附录：发布流程

```bash
# 构建包
python -m build

# 发布到 PyPI
twine upload dist/*

# 创建 Git 标签
git tag -a v6.2.0 -m "v6.2.0"
git push origin v6.2.0

# 发布 Release Notes
# 在 GitHub 上创建 Release，附上 CHANGELOG 内容
```

---

> 光明项目地址：[https://github.com/skywalk163/light](https://github.com/skywalk163/light)
> 文档站：[https://skywalk163.github.io/light/](https://skywalk163.github.io/light/)
> 许可证：MIT