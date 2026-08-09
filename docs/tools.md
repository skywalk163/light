# 工具链

## CLI 工具

### light 命令

```bash
# 编译运行
light run <file.light>

# 编译为可执行文件
light build <file.light> -o output.exe

# 版本信息
light --version

# 帮助
light --help
```

### light debug 调试模式

```bash
# 调试文件
light debug <file.light>

# 启动调试 REPL
light debug
```

**调试命令：**

| 命令 | 说明 |
|------|------|
| `b <行号>` | 设置断点 |
| `d <行号>` | 删除断点 |
| `c` | 继续执行 |
| `n` | 单步跳过 |
| `s` | 单步进入 |
| `r` | 单步返回 |
| `p <变量>` | 打印变量 |
| `w` | 显示调用栈 |
| `l` | 显示源代码 |
| `vars` | 显示所有变量 |
| `q` | 退出调试 |

## VS Code 插件

安装 `vscode-extension/` 目录下的插件可以获得：

- **语法高亮**：光明关键字、动词、字符串等
- **代码补全**：内置函数、关键字等
- **悬停提示**：函数签名、文档
- **调试支持**：断点、单步调试

## LSP 语言服务器

光明提供 Language Server Protocol 支持：

```bash
# 启动 LSP 服务器
python -m lsp.light_lsp

# 或通过 stdio
python -m lsp.light_lsp --stdio
```

### 支持的功能

- ✅ 悬停提示 (Hover)
- ✅ 代码补全 (Completion)
- ✅ 跳转到定义 (Go to Definition)
- ✅ 诊断信息 (Diagnostics)
- ✅ 符号搜索 (Document Symbols)

## AI Copilot（算力不足时让 AI 写光明代码）

光明提供完整的 AI 辅助工具链，位于 `tools/ai_copilot/`。

### 核心思路

算力有限时，直接让 AI 写光明代码容易出错。光明的方案是：

```
用户需求 → AI 生成 Python → 微调模型翻译为光明 → light ai check 验证
```

1. 大模型擅长生成 Python 代码
2. 微调后的小模型专精 Python→光明翻译
3. `light ai check` 检测暗坑和后端兼容性

### light ai 命令

```bash
# 一键生成光明代码（自动组装速查卡 + 片段 + 暗坑提示）
light ai generate "写一个二分查找函数"

# 指定模型大小
light ai generate "排序算法" --model-size small   # ≤7B，精简提示
light ai generate "排序算法" --model-size medium  # 7-14B
light ai generate "文件读写" --model-size large   # ≥14B，完整提示

# 修复出错的光明代码
light ai fix hello.light "第3行语法错误"

# 查看语法速查卡（复制给 AI 当参考）
light ai card
light ai card --full    # 完整版（含所有内建函数）

# 查看代码片段模板
light ai snippets
light ai snippets --detail  # 含暗坑说明

# 后端感知检测（类关键字→提示切换 LLVM 后端）
light ai check hello.light

# 查看 Python↔光明 对照示例
light ai examples
```

### 速查卡 + 片段模板

AI 写光明代码容易出错的根因：它不知道光明语法的精确边界。

- **速查卡**（`light ai card`）：从 keywords.py 和 builtins.py 自动生成，精简版约 200 字，可直接粘贴到 prompt
- **片段模板**（`light ai snippets`）：20 个常见代码模式，5 个带暗坑字段

### 暗坑提醒

光明 v3.2 SRC 后端有以下已知暗坑，微调数据和速查卡均已标注：

| 暗坑 | 错误写法 | 正确写法 |
|------|----------|----------|
| `长度()` 不可用 | `设 n 为 长度(列表)` | `设 n 为 len(列表)` |
| 列表索引赋值 | `设 列表[i] 为 值` | `列表[i] = 值` |
| 变量名与内建函数冲突 | `设 打印 为 1` | 避免使用内建函数名 |
| 类系统 | SRC 后端 | 需切换 LLVM 后端 |

### LoRA 微调训练

提供三套微调方案，将模型训练为 Python→光明翻译专家：

| 方案 | 模型 | 显存需求 | 训练时间 | 定位 |
|------|------|----------|----------|------|
| ERNIE-4.5-0.3B | 0.3B | ~4 GB | 10-30 分钟 | 轻量级窄翻译 |
| **Qwen3.5-2B** | 2B | ~5 GB | ~10 分钟 | **开发调试首选** |
| **Qwen3-8B** | 8B | ~22 GB | ~30 分钟 | **生产部署，效果最强** |

```bash
cd tools/ai_copilot

# 1. 开发调试：2B 模型快速验证
python train_lora_7b.py --model-preset qwen3.5-2b

# 2. 生产部署：8B 模型最高质量
python train_lora_7b.py --model-preset qwen3-8b

# 3. 显存不够：QLoRA 4bit 量化（2B 仅 ~3GB，8B 仅 ~8GB）
python train_lora_7b.py --model-preset qwen3.5-2b --qlora

# 4. ERNIE 轻量方案
python train_sft.py

# 5. Jupyter Notebook 调试
jupyter notebook train_lora_7b.ipynb
```

训练数据：`sft_dataset.jsonl`（881 条 Python↔光明 v3.2 对照数据，12 个语法类别）

推荐工作流：先用 Qwen3.5-2B 快速迭代验证数据质量（~10分钟/轮），确认效果后切 Qwen3-8B 做生产级微调。

详细文档：
- [LoRA 微调指南（Qwen3-8B / Qwen3.5-2B）](../tools/ai_copilot/README_LoRA7B.md)
- [ERNIE 微调指南（0.3B）](../tools/ai_copilot/README_SFT.md)

### 文件清单

| 文件 | 说明 |
|------|------|
| `syntax_card.py` | 语法速查卡生成（自动提取 85 个内建函数 + 7 条暗坑） |
| `snippets.py` | 20 个代码片段模板（5 个带暗坑字段） |
| `prompt_generator.py` | 三种 prompt 模式（translate/create/paragraph） |
| `pipeline.py` | 一揽子管线（generate/fix + 模型分级 + 片段自动匹配） |
| `build_sft_dataset.py` | SFT 训练集构造器 |
| `sft_dataset.jsonl` | 训练数据（881 条） |
| `train_lora_7b.py` | Qwen3-8B/3.5-2B LoRA/QLoRA 一键微调 |
| `train_lora_7b.ipynb` | Jupyter Notebook 调试版 |
| `train_sft.py` | ERNIE-4.5-0.3B 微调脚本 |
| `train_sft.ipynb` | ERNIE Notebook 调试版 |
| `README_LoRA7B.md` | LoRA 微调文档 |
| `README_SFT.md` | ERNIE 微调文档 |
