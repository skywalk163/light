# 段言开源贡献快速参考指南

> **最后更新：** 2026-08-07
> **适用版本：** v6.2.1

本文档是段言开源贡献的**快速参考指南**（简洁版），与完整的 [CONTRIBUTING.md](../../CONTRIBUTING.md) 互补。适合已经熟悉 GitHub 协作流程的开发者快速查阅。

---

## 目录

1. [如何提 Issue](#1-如何提-issue)
2. [如何提 PR](#2-如何提-pr)
3. [代码规范速查](#3-代码规范速查)
4. [测试要求](#4-测试要求)
5. [沟通渠道](#5-沟通渠道)

---

## 1. 如何提 Issue

### Bug 报告

在 [Issues 页面](https://github.com/skywalk163/duan/issues) 点击 **New Issue**，选择 Bug 报告模板。

**必填信息：**

```
## 描述
[一句话描述问题]

## 复现步骤
1. 执行命令：`duan run xxx.duan`
2. 输入：...
3. 看到错误：...

## 环境信息
- 操作系统：Windows 11 / macOS 14 / Ubuntu 22.04
- Python 版本：3.12
- 段言版本：v6.2.1

## 错误输出
[完整的错误信息，不要截取片段]
```

### 功能建议

选择功能请求模板，**必填内容**：

- **问题背景**：当前遇到了什么不便或限制
- **建议方案**：期望的功能如何工作
- **使用示例**：展示该功能在代码中的用法
- **适用场景**：该功能在什么场景下最有用

### 标签说明

| 标签 | 含义 | 谁可以添加 |
|------|------|------------|
| `bug` | 确认的 Bug | 维护者 |
| `enhancement` | 功能增强 | 维护者 |
| `good first issue` | 适合新手 | 维护者 |
| `help wanted` | 寻求帮助 | 维护者 |
| `documentation` | 文档相关 | 任何人 |
| `question` | 疑问 | 任何人 |

---

## 2. 如何提 PR

### 提交流程

```bash
# 1. Fork 并克隆
git clone https://github.com/你的用户名/duan.git
cd duan
git remote add upstream https://github.com/skywalk163/duan.git

# 2. 同步最新代码
git checkout main
git pull upstream main

# 3. 创建功能分支
git checkout -b feat/你的功能名称   # 新功能
git checkout -b fix/修复内容        # Bug 修复
git checkout -b docs/更新内容       # 文档更新

# 4. 编写代码并测试
# ... 修改代码 ...
python -m pytest tests/ -v

# 5. 提交并推送
git add .
git commit -m "feat: 简洁说明变更内容"
git push origin feat/你的功能名称
```

### PR 提交规范

**标题格式：**

```
<类型>: <简短描述>
```

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加 JSON 流式解析支持` |
| `fix` | Bug 修复 | `fix: 修复中文注释解析错误` |
| `docs` | 文档更新 | `docs: 更新入门教程示例` |
| `refactor` | 重构 | `refactor: 重构词法分析器` |
| `test` | 测试 | `test: 添加类型检查测试用例` |
| `perf` | 性能优化 | `perf: 优化列表遍历性能` |

**PR 描述应包含：**

- **变更内容**：做了什么修改
- **变更原因**：为什么需要这个修改
- **测试方法**：如何验证修改的正确性
- **关联 Issue**：`Closes #123`

### PR 审查清单

提交前请自查：

- [ ] 代码遵循段言/项目代码规范
- [ ] 已添加或更新测试用例
- [ ] 所有测试通过
- [ ] 文档已更新（如有需要）
- [ ] 无未处理的控制台输出或调试代码
- [ ] 分支已同步最新的 main 分支

---

## 3. 代码规范速查

### 段言代码规范

| 项目 | 规范 |
|------|------|
| 变量声明 | `设 变量名 为 值` |
| 函数定义 | `段落 函数名 接收 参数1, 参数2:` |
| 条件判断 | `如果` / `否则若` / `否则` |
| 循环 | `遍历 项 于 列表:` 或 `当 条件:` |
| 缩进 | 4 个空格（不要用 Tab） |
| 语句结尾 | 建议使用 `。`（中文句号）结尾 |
| 冒号 | 使用 `：`（中文冒号）结束语句块头部 |

### 命名规范

| 类型 | 推荐方式 | 示例 |
|------|----------|------|
| 变量名 | 中文或英文，小写开头 | `姓名`, `user_name` |
| 函数名 | 中文或英文，动词开头 | `获取用户`, `calculateSum` |
| 常量 | 全大写 | `MAX_COUNT`, `PI` |
| 文件名 | 中文或英文，小写 | `主.duan`, `main.duan` |

### 注释规范

- 使用 `#` 开头写注释
- 重要逻辑步骤前加注释说明
- 尽量用中文写注释
- 不要写显而易见的注释

### Python 代码规范（编译器/标准库）

- 遵循 [PEP 8](https://pep8.org/) 编码规范
- 使用 4 空格缩进
- 行长度不超过 100 字符
- 使用类型注解（Python 3.10+）
- 文件名使用蛇形命名（snake_case）

---

## 4. 测试要求

### 运行测试

```bash
# 运行全部测试
python -m pytest tests/

# 运行指定测试文件
python -m pytest tests/unit/test_lexer.py -v

# 运行测试并生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html
```

### 测试编写规范

| 场景 | 测试要求 |
|------|----------|
| 新功能 | 必须包含单元测试，覆盖正常路径和边界情况 |
| Bug 修复 | 必须包含回归测试，确保 Bug 不会再次出现 |
| 重构 | 必须确保现有测试全部通过 |
| 文档 | 无需测试，但需确保示例代码可运行 |

### 测试文件命名

```
tests/
├── unit/
│   ├── test_lexer.py          # 词法分析器测试
│   ├── test_parser.py         # 语法分析器测试
│   ├── test_compiler.py       # 编译器测试
│   └── test_stdlib.py         # 标准库测试
├── integration/
│   └── test_duan_programs.py  # 段言程序集成测试
└── e2e/
    └── test_cli.py            # CLI 端到端测试
```

---

## 5. 沟通渠道

| 渠道 | 地址 | 说明 |
|------|------|------|
| **GitHub Issues** | [https://github.com/skywalk163/duan/issues](https://github.com/skywalk163/duan/issues) | Bug 报告和功能请求 |
| **GitHub Discussions** | [https://github.com/skywalk163/duan/discussions](https://github.com/skywalk163/duan/discussions) | 技术讨论和问题求助 |
| **文档站** | [https://skywalk163.github.io/duan/](https://skywalk163.github.io/duan/) | 文档和教程 |
| **微信群** | 关注项目 README 中的二维码 | 实时交流 |
| **QQ 群** | 关注项目 README 中的群号 | 实时交流 |

### 提问建议

1. **先搜索**：提问前先在 Issues 和 Discussions 中搜索
2. **提供完整信息**：包括操作系统、Python 版本、段言版本、错误信息
3. **提供可复现代码**：附上最小可复现示例
4. **友善礼貌**：保持友善和尊重的沟通方式

---

> 完整版贡献指南请参考 [CONTRIBUTING.md](../../CONTRIBUTING.md)
> 开发环境搭建请参考 [开发指南](../DEVELOPMENT_GUIDE.md)
> 段言项目地址：[https://github.com/skywalk163/duan](https://github.com/skywalk163/duan)
> 许可证：MIT