# 欢迎为段言做贡献！🎉

你好！感谢你对段言（Duan）编程语言的关注。无论你是经验丰富的开发者，还是刚刚开始学习编程的新手，我们都热忱欢迎你为段言贡献力量。

段言是一门**中文编程语言**，我们的社区也秉承中文友善的理念。这份指南完全用中文编写，希望能帮助每一位中文开发者轻松上手，参与到开源贡献中来。

## 你可以贡献什么？

- 🐛 **报告 Bug** — 发现编译器或工具的问题，告诉我们
- 💡 **提出建议** — 你有好的想法？我们洗耳恭听
- 📖 **改进文档** — 修正错别字、补充说明、写教程
- 💻 **提交代码** — 修复 Bug、新增功能、优化性能
- 📦 **贡献标准库** — 给段言添加更多实用的功能模块
- ✍️ **写博客** — 分享你使用段言的经验和心得
- 🗣 **参与讨论** — 帮助其他新手解答问题

---

## 快速开始

### 第一步：Fork 项目

访问段言仓库：https://github.com/skywalk163/duan

点击页面右上角的 **Fork** 按钮，把项目复制一份到你的 GitHub 账号下。

### 第二步：克隆到本地

打开终端，运行以下命令：

```bash
# 把你 fork 的仓库克隆到本地
git clone https://github.com/你的用户名/duan.git
cd duan

# 添加上游仓库（原项目），方便同步最新代码
git remote add upstream https://github.com/skywalk163/duan.git
```

> 💡 把 `你的用户名` 替换成你的 GitHub 用户名。

---

## 开发环境配置

段言的编译器是用 Python 写的，所以配置起来很简单。

### 你需要准备

| 工具 | 版本要求 | 说明 |
|------|----------|------|
| **Python** | 3.10 或更高（推荐 3.12） | 段言编译器运行的基础 |
| **Git** | 2.30 以上 | 版本管理 |
| **VS Code**（可选） | 最新版 | 推荐安装段言扩展，获得语法高亮和代码提示 |
| **LLVM/Clang**（可选） | 14+ | 如果你要用 LLVM 后端编译 |

### 安装步骤

```bash
# 1. 进入项目目录
cd duan

# 2. 创建虚拟环境（推荐）
python -m venv venv

# 3. 激活虚拟环境
# Windows 系统：
venv\Scripts\activate
# macOS / Linux 系统：
# source venv/bin/activate

# 4. 安装项目依赖
pip install -e .
pip install antlr4-tools antlr4-python3-runtime

# 5. 安装测试工具（可选，开发时推荐）
pip install pytest pytest-cov
```

### 验证安装成功

```bash
# 查看版本号
python -m cli.duan --version

# 运行一个简单的段言程序
python -m cli.duan run examples/hello.duan

# 输出应该是：你好，世界！
```

如果看到输出了"你好，世界！"，恭喜你，开发环境配置成功！🎉

---

## 项目结构

了解项目结构，能帮你快速找到需要修改的代码。

```
duan/
├── src/                  # 核心编译器源码
│   ├── lexer.py          # 词法分析器（把代码拆成单词）
│   ├── parser_core.py    # 语法分析器核心（把单词拼成语法树）
│   ├── parser_expr.py    # 表达式解析
│   ├── parser_stmt.py    # 语句解析
│   ├── compiler.py       # 编译器主入口
│   ├── code_generator.py # 代码生成器
│   ├── type_checker.py   # 类型检查器
│   ├── type_system.py    # 类型系统定义
│   ├── ast_nodes.py      # 抽象语法树节点定义
│   ├── tokens.py         # 词法单元定义
│   ├── keywords.py       # 关键字定义
│   ├── formatter.py      # 代码格式化工具
│   ├── module_resolver.py # 模块解析器
│   └── ...
│
├── cli/                  # 命令行工具
│   ├── duan.py           # 主命令行入口
│   ├── duan_unified.py   # 统一命令行接口
│   └── tutorial.py       # 交互式教程
│
├── stdlib/               # 标准库（Python 实现）
│   ├── 文件系统.py       # 文件操作
│   ├── JSON.py           # JSON 解析
│   ├── 正则表达式.py     # 正则匹配
│   ├── 日期时间.py       # 日期时间处理
│   ├── 数学.py           # 数学计算
│   ├── ...               # 更多标准库模块
│   └── duanpub/          # duanpub 桥接模块
│
├── tests/                # 测试目录
│   ├── unit/             # 单元测试
│   ├── integration/      # 集成测试
│   ├── e2e/              # 端到端测试
│   ├── run_tests.py      # 测试运行脚本
│   └── ...
│
├── docs/                 # 文档
│   ├── api/              # API 参考文档
│   ├── blog/             # 技术博客
│   ├── tutorials/        # 教程
│   └── ...
│
├── examples/             # 示例代码
│   ├── hello.duan        # Hello World
│   ├── basic.duan        # 基础语法示例
│   ├── web_crawler/      # 网页爬虫示例
│   ├── games/            # 游戏示例
│   └── ...
│
├── bootstrap/            # 自举编译器（用段言写的编译器）
│   ├── lexer.duan        # 词法分析器（段言版）
│   ├── parser.duan       # 语法分析器（段言版）
│   ├── compiler.duan     # 编译器（段言版）
│   └── ...
│
├── antlrparser/          # ANTLR 解析器（另一种解析方式）
│   ├── DuanLangLexer.g4  # ANTLR 词法规则
│   ├── DuanLangParser.g4 # ANTLR 语法规则
│   ├── duan_interpreter.py # 解释器
│   └── ...
│
├── contrib/              # 社区贡献模块
│   ├── HTTP服务端.duan   # HTTP 服务端
│   ├── HTTP客户端.duan   # HTTP 客户端
│   └── ...
│
├── tools/                # 开发工具
│   ├── repl.py           # 交互式 REPL
│   ├── doc_site.py       # 文档站点构建
│   └── ...
│
├── pyproject.toml        # Python 项目配置
└── README.md             # 项目介绍
```

### 各目录简要说明

| 目录 | 作用 | 适合谁修改 |
|------|------|------------|
| `src/` | 核心编译器，包含词法、语法、语义分析、代码生成 | 有编译器开发经验 |
| `cli/` | 命令行工具，用户和编译器交互的窗口 | 有 Python 命令行经验 |
| `stdlib/` | 标准库，段言内置功能的 Python 实现 | 有 Python 开发经验 |
| `tests/` | 测试用例，保证代码质量的重要防线 | 任何水平的开发者 |
| `docs/` | 文档和教程，帮助用户学习段言 | 喜欢写作的开发者 |
| `examples/` | 示例代码，展示段言的实际应用 | 想分享段言使用技巧 |
| `bootstrap/` | 自举编译器，用段言本身编写的编译器 | 熟悉段言语法的开发者 |
| `contrib/` | 社区贡献的实用模块 | 想贡献新功能的开发者 |

---

## 详细开发环境配置

### Python 环境要求

段言编译器使用 Python 编写，以下是推荐的开发环境配置：

| 工具 | 版本要求 | 用途 |
|------|----------|------|
| **Python** | 3.10 ~ 3.13 | 编译器运行环境 |
| **Git** | 2.30+ | 版本控制 |
| **VS Code** | 最新版 | 推荐 IDE（含段言扩展） |
| **pytest** | 7.0+ | 测试框架 |
| **ANTLR** (可选) | 4.13+ | 备选解析后端 |

### 完整安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/skywalk163/duan.git
cd duan

# 2. 创建并激活虚拟环境
# Windows:
python -m venv venv
venv\Scripts\activate

# macOS/Linux:
# python3 -m venv venv
# source venv/bin/activate

# 3. 安装项目依赖（开发模式）
pip install -e .

# 4. 安装开发工具
pip install -e ".[dev]"

# 5. 安装 ANTLR 支持（可选）
pip install -e ".[antlr]"

# 6. 验证安装
python -m cli.duan_unified --version
python -m cli.duan_unified run examples/hello.duan
```

### 验证开发环境

运行以下命令确认环境配置正确：

```bash
# 查看版本号
python -m cli.duan_unified --version

# 运行 Hello World
python -m cli.duan_unified run examples/hello.duan

# 运行测试套件
python -m pytest tests/ -q --tb=short
```

---

## 如何运行测试

### 测试目录结构

```
tests/
├── unit/           # 单元测试（词法分析、语法解析、代码生成等）
├── integration/    # 集成测试（模块间交互）
├── e2e/            # 端到端测试（完整链路，覆盖示例程序）
└── test_e2e_full_coverage.py  # 全链路覆盖测试
```

### 运行全部测试

```bash
# 运行所有测试（推荐）
python -m pytest tests/

# 仅显示失败和跳过的测试
python -m pytest tests/ -q --tb=short

# 显示详细输出
python -m pytest tests/ -v
```

### 运行特定测试

```bash
# 运行单个测试文件
python -m pytest tests/unit/test_lexer.py -v

# 运行单个测试用例
python -m pytest tests/unit/test_lexer.py::test_xxx -v

# 按关键词筛选
python -m pytest tests/ -k "lexer or parser"

# 运行 E2E 测试
python -m pytest tests/e2e/ -v
```

### 运行测试并生成覆盖率报告

```bash
# 安装覆盖率工具
pip install pytest-cov

# 运行测试并生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=term-missing

# 生成 HTML 覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html
```

### 测试注意事项

- 提交 PR 前确保所有测试通过：`python -m pytest tests/ -q --tb=short`
- 新增功能必须包含对应的测试用例
- E2E 测试覆盖示例程序，修改示例时需同步更新测试
- 测试文件命名规范：`test_模块名_功能.py`

---

## Pull Request 检查清单

提交 PR 前，请逐项确认：

### 代码质量
- [ ] 代码遵循项目代码规范（参见「代码规范」章节）
- [ ] 所有测试通过（`python -m pytest tests/ -q --tb=short`）
- [ ] 新增功能包含充分的测试用例
- [ ] Bug 修复包含回归测试
- [ ] 代码无明显的性能问题

### 文档与注释
- [ ] 关键逻辑有中文注释说明
- [ ] 新增的公开 API 有文档字符串
- [ ] 如果修改了用户可见行为，更新了相关文档
- [ ] 示例代码使用最新语法

### 提交规范
- [ ] 分支命名符合规范（`feature/xxx`、`fix/xxx`、`docs/xxx`）
- [ ] Commit 信息简洁明了，说明变更原因
- [ ] 一个分支只解决一个问题
- [ ] 没有包含调试代码或临时文件

### 兼容性
- [ ] 没有破坏现有功能
- [ ] 兼容 Python 3.10 ~ 3.13
- [ ] 跨平台测试（Windows/macOS/Linux）通过

---

## 代码审查指南

### 审查原则

1. **尊重与建设性**：以帮助作者改进为目的，而非挑剔
2. **关注关键问题**：优先审查逻辑正确性、安全性、性能
3. **代码风格次之**：风格问题可标注，但不应阻塞合入
4. **及时响应**：争取在 48 小时内完成审查

### 审查清单

#### 功能正确性
- 代码是否实现了预期的功能？
- 边界情况是否处理妥当？（空值、零值、超大输入等）
- 是否有潜在的并发问题？

#### 代码质量
- 是否有重复代码可以抽取复用？
- 函数/段落是否职责单一？
- 错误处理是否恰当？
- 是否有过度设计（不必要的抽象）？

#### 安全性
- 用户输入是否经过验证？
- 文件路径操作是否安全？（防止路径遍历）
- 是否存在命令注入风险？
- 敏感信息（密钥、密码）是否泄露？

#### 测试覆盖
- 新增代码是否有对应的测试？
- 测试是否覆盖了正常路径和异常路径？
- 测试是否真实有效（不是虚假测试）？

### 审查流程

1. **阅读 PR 描述**：了解变更目的和范围
2. **查看关键文件**：优先审查核心逻辑文件
3. **运行测试**：确保所有测试通过
4. **留下评论**：使用 GitHub 的 Review 功能
5. **批准或请求修改**：确认无误后批准合入

### 常用审查标签

| 标签 | 含义 | 操作 |
|------|------|------|
| `nit` | 小问题（拼写、格式） | 可选修改 |
| `suggestion` | 改进建议 | 可考虑采纳 |
| `blocking` | 必须修改的问题 | 需修改后才能合入 |
| `question` | 疑问 | 需要作者澄清 |

---

## 如何贡献翻译

段言项目支持多语言文档，欢迎贡献翻译！

### 翻译范围

- **文档翻译**：`docs/` 目录下的文档翻译为其他语言
- **错误信息翻译**：编译器和运行时错误信息的多语言支持
- **示例注释翻译**：示例代码中的注释翻译
- **VS Code 扩展**：扩展界面文本的本地化

### 翻译流程

1. **确认需求**：在 GitHub Issues 中搜索 `translation` 标签，或新建 Issue 说明你想翻译的语言
2. **创建分支**：`git checkout -b translation/目标语言-文档名`
3. **翻译文档**：在 `docs/` 下创建对应语言的子目录（如 `docs/en/`、`docs/ja/`）
4. **保持同步**：翻译应跟随中文原版的最新版本
5. **提交 PR**：在 PR 描述中标注 `translation` 标签

### 翻译规范

- **保持术语一致**：使用统一的术语翻译表
- **保留代码示例**：代码示例不需要翻译，只需翻译注释和说明文字
- **保留链接**：内部链接保持相对路径，外部链接保持原样
- **注明译者**：在文档末尾添加 `> 翻译：@你的GitHub用户名`

### 中文术语对照表（英→中）

| 英文 | 中文 |
|------|------|
| compiler | 编译器 |
| lexer | 词法分析器 |
| parser | 语法分析器 |
| code generator | 代码生成器 |
| abstract syntax tree | 抽象语法树 |
| type system | 类型系统 |
| standard library | 标准库 |
| bootstrap | 自举 |
| module | 模块 |
| package | 包 |

---

## 如何贡献代码

### 第一步：选择一个任务

如果你是第一次贡献，可以看看有没有这些标签的任务：

- **`good first issue`**（适合新手的任务）— 最适合你的起点
- **`help wanted`**（寻求帮助）— 项目需要帮助的任务
- **`documentation`**（文档相关）— 从文档开始最轻松
- **`bug`**（Bug 修复）— 修复问题

在对应的 Issue 下留言说"我想认领这个任务"，就可以开始动手了。

### 第二步：创建分支

```bash
# 先同步最新的代码
git checkout main
git pull upstream main

# 创建你的功能分支
git checkout -b feature/你的功能名称
# 或
git checkout -b fix/你要修复的问题
# 或
git checkout -b docs/你要更新的文档
```

### 第三步：编写代码

写代码的时候，请记住下面几点：

- **保持改动范围集中** — 一个分支只解决一个问题
- **遵循代码规范**（见下文）
- **如果是修复 Bug**，先写一个能复现 Bug 的测试用例
- **多写注释**，用中文注释说明你的思路

### 第四步：运行测试

```bash
# 运行所有测试，确保没有破坏现有的功能
python -m pytest tests/

# 只运行你修改相关的测试
python -m pytest tests/unit/test_lexer.py -v

# 运行测试时显示详细输出
python -m pytest tests/ -v
```

确保所有测试都通过了再提交。

### 第五步：提交 Pull Request

```bash
# 提交你的代码
git add 你修改的文件
git commit -m "feat: 简单说明你做了什么"

# 推送到你的 GitHub 仓库
git push origin feature/你的功能名称
```

然后去 GitHub 上你的仓库页面，点击 **Compare & pull request** 按钮，填写 PR 信息：

- **标题**：简洁说明你的变更
- **内容**：描述你做了什么、为什么这么做、如何测试的
- **关联 Issue**：在描述中写上 `Closes #123`（123 是 Issue 编号）

之后就等着维护者审查你的代码吧！如果审查者有修改建议，在你的本地修改后推送即可，PR 会自动更新。

---

## 代码规范

### 段言代码规范

段言代码使用 v6.0 语法，请遵循以下规范：

| 项目 | 规范 |
|------|------|
| 变量声明 | 使用 `设 变量名 为 值` |
| 函数定义 | 使用 `段落 函数名 接收 参数1, 参数2:` |
| 条件判断 | 使用 `如果` / `否则若` / `否则` |
| 循环 | 使用 `遍历 项 于 列表:` 或 `当 条件:` |
| 缩进 | 4 个空格（不要用 Tab） |
| 语句结尾 | 建议使用 `。`（中文句号）结尾 |
| 冒号 | 使用 `：`（中文冒号）结束语句块头部 |

示例：

```段言
# 推荐的段言代码风格
设 姓名 为 "段言"

段落 问候 接收 名字:
  打印("你好，" + 名字 + "！")

遍历 数字 于 1 到 5:
  如果 数字 % 2 等于 0:
    打印(数字 + "是偶数")
  否则:
    打印(数字 + "是奇数")
```

### 命名规范

| 类型 | 推荐方式 | 示例 |
|------|----------|------|
| 变量名 | 中文或英文，小写开头 | `姓名`, `user_name` |
| 函数名 | 中文或英文，动词开头 | `获取用户`, `calculateSum` |
| 常量 | 全大写 | `MAX_COUNT`, `π` |
| 文件名 | 中文或英文，小写 | `主.duan`, `main.duan` |

### 注释规范

- 使用 `#` 开头写注释
- 重要逻辑步骤前加注释说明
- 尽量用中文写注释，方便其他中文开发者理解
- 不要写显而易见的注释，比如 `# 加1` 这种

### 测试规范

- 所有新功能必须包含测试用例
- Bug 修复必须包含回归测试（确保 Bug 不会再次出现）
- 测试文件放在 `tests/` 目录下
- 测试命名：`test_模块名_功能.py`

---

## 如何报告问题

发现了 Bug？或者有什么建议？请提交 Issue。

### 提交 Issue 的模板

在 [Issues 页面](https://github.com/skywalk163/duan/issues) 点击 **New Issue**，请尽量包含以下信息：

**Bug 报告模板：**

```
## 描述问题
请清晰简洁地描述这个 Bug 是什么。

## 复现步骤
1. 执行命令：`duan run xxx.duan`
2. 输入：...
3. 看到错误：...

## 期望行为
你期望看到什么结果？

## 实际行为
实际发生了什么？（请附上错误信息截图）

## 环境信息
- 操作系统：Windows 10 / macOS 14 / Ubuntu 22.04
- Python 版本：3.12
- 段言版本：v6.2.0

## 补充信息
其他你觉得有用的信息。
```

**功能建议模板：**

```
## 建议内容
清晰描述你希望添加的功能。

## 使用场景
这个功能在什么场景下有用？请举例说明。

## 实现思路（可选）
如果你有实现思路，可以写在这里。
```

---

## 如何贡献文档

文档是项目的重要组成部分，好的文档能帮助更多人学习和使用段言。

你可以这样贡献文档：

1. **修正错误** — 发现文档中有错别字、语法错误或过时的内容，直接修改
2. **补充说明** — 某个功能说明不够详细？补充更多例子和解释
3. **写教程** — 分享你使用段言的经验，教别人做有趣的事情
4. **翻译文档** — 帮助把中文文档翻译成英文，或把英文文档翻译成中文

文档目录在 `docs/` 下，使用 Markdown 格式编写。

本地预览文档：

```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

然后在浏览器打开 http://127.0.0.1:8000 即可预览。

---

## 如何贡献示例

想展示段言的某个好用功能？欢迎贡献示例代码！

示例放在 `examples/` 目录下，请遵循以下规则：

1. 每个示例放在独立的子目录中
2. 主文件命名为 `主.duan`
3. 附带 `README.md` 说明文档
4. 代码要有中文注释
5. README 要包含：
   - 功能介绍
   - 使用方法（运行命令）
   - 涉及的语言特性

可以参考已有的示例，比如 `examples/web_crawler/` 或 `examples/data_pipeline/`。

---

## 社区交流渠道

遇到问题想找人聊聊？这里有一些渠道：

| 渠道 | 地址 | 说明 |
|------|------|------|
| **GitHub Issues** | https://github.com/skywalk163/duan/issues | 报告 Bug 和提功能建议 |
| **GitHub Discussions** | https://github.com/skywalk163/duan/discussions | 一般讨论、提问、分享 |
| **文档站** | https://skywalk163.github.io/duan/ | 查看完整的文档和教程 |
| **微信群** | 请关注项目 README 中的二维码 | 实时交流，快速响应 |

### 交流建议

- 提问前先搜索一下，看是否已经有答案
- 描述问题时尽量详细，附上代码和错误信息
- 保持友善和尊重的态度，我们欢迎所有水平的开发者
- 如果发现别人问的问题你会回答，伸出援手吧！

---

## 写在最后

每一份贡献都让段言变得更好，无论你贡献的是代码、文档、测试还是社区讨论，我们都衷心感谢你！

还记得吗？段言是一门**中文编程语言**，我们的社区也应该是中文开发者最温暖的家。不要因为自己"不够厉害"就不敢参与，每个专家都曾经是新手。勇敢地迈出第一步吧！

让我们一起，用中文编程，让编程变得更简单、更有趣！🚀

---

> **段言项目地址**：https://github.com/skywalk163/duan
> **文档站**：https://skywalk163.github.io/duan/
> **许可证**：MIT