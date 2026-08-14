# 文件批量重命名工具

使用段言编程语言实现的命令行文件批量重命名工具。支持添加前缀、添加后缀、替换文本等操作，适用于批量整理文件。

## 功能

- 添加前缀（如 `--prefix "备份_"`）
- 添加后缀（如 `--suffix "_v2"`）
- 替换文件名中的文本（如 `--replace "旧名" "新名"`）
- 按文件扩展名过滤（如 `--ext ".txt"`）
- 预览模式，不实际修改文件（`--dry-run`）
- 递归处理子目录（`--recursive`）
- 自动跳过无需修改的文件
- 显示操作统计报告

## 用法

```bash
# 预览模式 - 查看将要执行的操作
duan run examples/file_tools/batch_rename/主.duan ./图片 --prefix "旅行_" --ext ".jpg" --dry-run

# 为所有文件添加前缀
duan run examples/file_tools/batch_rename/主.duan ./文档 --prefix "2024_"

# 为所有文件添加后缀
duan run examples/file_tools/batch_rename/主.duan ./照片 --suffix "_已处理"

# 替换文件名中的文本
duan run examples/file_tools/batch_rename/主.duan ./报告 --replace "草稿" "正式版"

# 限定扩展名 + 添加前缀 + 递归子目录
duan run examples/file_tools/batch_rename/主.duan ./代码 --prefix "备份_" --ext ".py" --recursive

# 查看帮助
duan run examples/file_tools/batch_rename/主.duan --help
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `--prefix <文本>` | 在文件名前添加前缀 |
| `--suffix <文本>` | 在文件名后添加后缀（扩展名前） |
| `--replace <旧> <新>` | 替换文件名中的文本 |
| `--ext <扩展名>` | 限定处理的文件扩展名 |
| `--dry-run` | 预览模式，不实际修改文件 |
| `--recursive` | 递归处理子目录 |
| `--help` | 显示帮助信息 |

## 涉及的语言特性

- `段落` 函数定义与参数传递
- `设` 变量声明
- `如果`/`否则若`/`否则` 条件判断
- `遍历` 列表遍历循环
- `当` 条件循环
- `尝试`/`捕获` 异常处理
- `导入` 标准库模块（文件系统、路径处理）
- 字符串处理（分割、替换、拼接）
- 文件系统操作（列出目录、重命名、文件大小检测）
- 命令行参数解析