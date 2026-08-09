# CLI 使用指南

## 基本用法

```bash
light [选项] <文件>
```

## 选项

| 选项 | 说明 |
|------|------|
| `--version` | 显示版本信息 |
| `--help` | 显示帮助信息 |
| `--ast` | 输出 AST 解析树 |
| `--tokens` | 输出词法分析结果 |
| `--compile` | 编译为 Python 代码 |
| `--llvm` | 编译为 LLVM IR |
| `--check` | 仅检查语法，不执行 |
| `--format` | 格式化代码 |
| `--watch` | 监视文件变化并自动重跑 |

## 示例

```bash
# 运行文件
light hello.light

# 查看 AST
light hello.light --ast

# 编译为 Python
light hello.light --compile

# 语法检查
light hello.light --check
```

## REPL

```bash
light
```

进入交互式 REPL 环境，支持：
- 逐行执行光明代码
- 自动补全
- 语法高亮
- 历史记录