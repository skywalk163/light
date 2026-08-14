# CLI 文件整理器示例

演示如何使用段言标准库构建一个功能完整的命令行工具——按文件类型自动分类整理文件。

## 功能

- **目录扫描** — 递归扫描指定目录，列出所有文件
- **智能分类** — 按扩展名自动归类到 Images、Documents、Archives 等类别
- **预览模式** (`--dry-run`) — 模拟执行，不实际移动文件，安全可靠
- **自定义规则** (`--config`) — 支持 JSON 配置文件自定义分类规则
- **进度显示** — 实时显示处理进度条和百分比
- **汇总报告** — 完成后显示详细的统计信息
- **自动跳过** — 忽略隐藏文件和系统文件，避免误操作
- **错误处理** — 完善的异常捕获和错误提示

## 用法

```bash
# 整理当前目录
duan run examples/cli_tool/file_organizer.duan

# 预览模式 - 查看整理结果但不实际移动文件
duan run examples/cli_tool/file_organizer.duan ./下载 --dry-run

# 使用自定义规则
duan run examples/cli_tool/file_organizer.duan ./桌面 -c 我的规则.json

# 指定输出目录
duan run examples/cli_tool/file_organizer.duan ./文档 -o ./整理后

# 查看帮助
duan run examples/cli_tool/file_organizer.duan --help
```

## 参数说明

| 参数 | 简写 | 说明 |
|------|------|------|
| `目录` | - | 要整理的目录路径（默认: 当前目录） |
| `--dry-run` | `-n` | 预览模式，不实际移动文件 |
| `--config <文件>` | `-c` | 指定自定义规则配置文件（JSON 格式） |
| `--output <目录>` | `-o` | 指定输出目录（默认: 源目录） |
| `--help` | `-h` | 显示帮助信息 |

## 默认分类

| 类别 | 文件夹 | 文件类型 |
|------|--------|----------|
| 图片 | Images/ | .jpg .jpeg .png .gif .bmp .svg .webp .ico 等 |
| 文档 | Documents/ | .pdf .doc .docx .xls .xlsx .txt .md .csv .json 等 |
| 压缩包 | Archives/ | .zip .rar .tar .gz .7z .bz2 .xz 等 |
| 音频 | Audio/ | .mp3 .wav .flac .aac .ogg .wma .m4a 等 |
| 视频 | Video/ | .mp4 .avi .mkv .mov .wmv .flv .webm 等 |
| 代码 | Code/ | .py .js .ts .java .c .cpp .go .rs .duan 等 |
| 可执行文件 | Executables/ | .exe .msi .bat .sh .app .dll 等 |
| 其他 | Other/ | 未匹配到上述分类的文件 |

## 自定义规则

首次运行会自动生成 `organizer_config.json` 配置文件，编辑即可自定义规则：

```json
{
  "MyCategory": {
    "extensions": [".xxx", ".yyy"],
    "description": "我的自定义分类"
  }
}
```

## 涉及的语言特性

- `段落` 函数定义与多参数传递
- `设` 变量声明
- `如果`/`否则若`/`否则` 条件判断
- `遍历` 列表和字典遍历
- `当` 条件循环（`跳过`/`跳出`）
- `尝试`/`捕获` 异常处理
- `导入` 标准库模块（文件系统、JSON）
- 字典和列表的增删改查操作
- 字符串处理（分割、替换、大小写转换）
- 文件系统操作（扫描、判断、创建、移动）
- 命令行参数解析
- JSON 序列化与反序列化
- `转字符串`/`转整数` 类型转换
- `真`/`假`/`空` 布尔值和空值处理