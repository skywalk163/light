# 光明 LoRA 微调运行指南

本指南说明如何在本地使用小模型 LoRA 微调，让模型学会将 Python 代码翻译为光明 v3.2 代码。

> **不想自己训练？** 训练好的模型已上线 Ollama，可直接拉取使用：
> ```bash
> ollama pull airoot/light-translator
> ```
> 模型主页：[https://ollama.com/airoot/light-translator](https://ollama.com/airoot/light-translator)

## 快速总结

- **支持模型**：
  - Qwen2.5-0.5B-Instruct（0.5B 参数，CPU 也能跑）
  - Qwen2.5-1.5B-Instruct（1.5B 参数，需 GPU）
  - Qwen3.5-2B（2B 多模态架构，需 GPU + transformers>=5.0）
- **训练方法**：LoRA 微调（只训练 q/v/k/o_proj 等投影层，参数量 ~0.1%）
- **数据集**：978 条 Python→光明 对照（`sft_dataset.jsonl`）
- **数据集 v2 扩充**：新增 494 条覆盖类/OOP、f-string、列表推导、异常处理、lambda、with、复合算法
- **数据集 v3 扩充**：新增 32 条长代码样本（Python 49-99 行），覆盖多类协作、设计模式、数据管线、算法实现、游戏逻辑、Web 后端、数学计算
- **max_len**：8192（v3 提升，覆盖系统提示+长代码样本，v2 为 1024）
- **2步验证训练**：28 秒完成，LoRA 权重 2.1MB
- **全量训练 CPU 估算**：~5.5 小时（不推荐）
- **全量训练 GPU 估算**：~9 分钟（0.5B / RTX 3060） / ~3 分钟（0.5B / RTX 4090） / ~25 分钟（3.5-2B / RTX 3060）

### 模型预设对照

| 预设名 | 模型 | 参数量 | 显存需求 (LoRA bf16) | QLoRA | 备注 |
|--------|------|--------|----------------------|-------|------|
| `qwen2.5-0.5b` | Qwen2.5-0.5B-Instruct | 0.5B | ~5 GB | 支持 | 默认，CPU 可跑 |
| `qwen2.5-1.5b` | Qwen2.5-1.5B-Instruct | 1.5B | ~10 GB | 支持 | 需 GPU |
| `qwen3.5-2b` | Qwen3.5-2B | 2B | ~5 GB | ~3 GB | 需 transformers>=5.0 |

> **Qwen3.5-2B 注意事项**：
> - 需安装 `transformers>=5.0`：`pip install "transformers>=5.0"`
> - QLoRA 模式可用但官方不建议（量化差异可能偏高），显存不足时可使用 `--qlora`
> - Dense 架构，显存效率优于同参数量的 MoE 模型
> - LoRA rank=32 / alpha=64 / lr=1e-4（比 0.5B 的默认值更大，适配 2B 模型）

## 文件结构

```
tools/ai_copilot/
├── sft_dataset.jsonl           # 训练数据（978 条 Python→光明 对照，v3 扩充后）
├── sft_dataset_new.jsonl       # v2 新增样本（494 条，已合并到 sft_dataset.jsonl）
├── sft_dataset_long.jsonl      # v3 长样本（32 条，Python 49-99 行，已合并到 sft_dataset.jsonl）
├── augment_dataset.py           # 数据集增强脚本 v2
├── augment_long_samples.py      # 长样本增强脚本 v3
├── train_cpu_lora.py           # CPU 训练脚本（已验证可用）
├── train_gpu_lora.py           # GPU 训练脚本（推荐，速度提升 30 倍，支持多模型预设）
├── download_model.py           # 模型下载脚本（支持 qwen2.5-0.5b / 1.5b / qwen3.5-2b）
├── local_infer.py              # 推理脚本（支持 ollama / transformers 后端，自动检测模型）
├── merge_and_convert.py        # LoRA 合并 & GGUF 转换（支持 --preset 多模型）
├── auto_finish.py              # 训练自动完成脚本（自动检测多模型路径）
├── fix_gguf_rope.py            # GGUF 修复脚本（修复 rope.freq_base=0.0）
├── create_ollama_model.sh      # 一键创建 ollama 模型（修复 + 量化）
├── model_cache/
│   ├── qwen2.5-0.5b/           # 基础模型（~1GB）
│   ├── qwen2.5-1.5b/           # 基础模型（~3GB）
│   └── qwen3.5-2b/             # 基础模型（~4.5GB）
└── output/
    ├── smoke_test/             # 2步验证训练产物
    ├── qwen2.5_0.5b_light_gpu/  # 0.5B GPU 全量训练产物
    ├── qwen2.5_1.5b_light_gpu/  # 1.5B GPU 全量训练产物
    ├── qwen3.5_2b_light_gpu/    # 3.5-2B GPU 全量训练产物
    ├── light_translator_merged_0.5b/   # 0.5B 合并后模型 + GGUF
    ├── light_translator_merged_1.5b/   # 1.5B 合并后模型 + GGUF
    └── light_translator_merged_3.5_2b/ # 3.5-2B 合并后模型 + GGUF
```

## 环境准备

### CPU 环境（开发验证用）

```bash
# 安装 PyTorch CPU 版
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 安装其余依赖
pip install transformers peft datasets accelerate

# Windows 还需要 VC++ Redistributable
# 下载: https://aka.ms/vs/17/release/vc_redist.x64.exe
```

### GPU 环境（全量训练用）

```bash
# 安装 GPU 版 PyTorch（根据 CUDA 版本）
pip install torch --index-url https://download.pytorch.org/whl/cu121

# 安装全部 GPU 训练依赖（包含 bitsandbytes, torchao）
pip install -r requirements-gpu.txt

# 或手动安装核心依赖
pip install transformers peft datasets accelerate
pip install bitsandbytes       # QLoRA 4bit 量化训练需要
pip install "torchao>=0.16.0"  # peft 依赖，版本过低会导致 LoRA 创建失败

# Qwen3.5-2B 额外要求
pip install --upgrade "transformers>=5.0"
```

> **Kaggle / Colab 用户注意**：平台预装的 transformers 可能较旧，
> 下载 Qwen3.5-2B 前必须先升级：
> ```bash
> pip install --upgrade "transformers>=5.0"
> ```

## 下载模型

```bash
cd tools/ai_copilot

# 下载 Qwen2.5-0.5B（默认，~1GB）
HF_ENDPOINT=https://hf-mirror.com python download_model.py --model qwen2.5-0.5b

# 下载 Qwen2.5-1.5B（~3GB）
HF_ENDPOINT=https://hf-mirror.com python download_model.py --model qwen2.5-1.5b

# 下载 Qwen3.5-2B（~4.5GB）
HF_ENDPOINT=https://hf-mirror.com python download_model.py --model qwen3.5-2b
```

如果下载超时，可以手动用 curl 下载：

```bash
curl -L -o model_cache/qwen2.5-0.5b/model.safetensors \
  "https://hf-mirror.com/Qwen/Qwen2.5-0.5B-Instruct/resolve/main/model.safetensors"
```

## 训练

### 2步验证训练（CPU，30 秒内）

验证全流程是否跑通：

```bash
python train_cpu_lora.py --max-steps 2 --batch-size 2 --grad-accum 1 --max-len 256 \
  --output-dir output/smoke_test
```

验证内容：
- 模型能加载 ✓
- LoRA 配置正确 ✓
- 数据集能读取 ✓
- 训练能跑 ✓
- 权重能保存 ✓

### 全量训练（GPU 推荐）

```bash
# 标准 GPU 训练（默认 Qwen2.5-0.5B，~8 分钟 RTX 3060）
python train_gpu_lora.py

# 使用 Qwen3.5-2B 预设（自动配置参数，~25 分钟 RTX 3060）
python train_gpu_lora.py --preset qwen3.5-2b

# 使用 Qwen2.5-1.5B 预设
python train_gpu_lora.py --preset qwen2.5-1.5b

# 快速验证（GPU 上 2 步）
python train_gpu_lora.py --max-steps 2
python train_gpu_lora.py --preset qwen3.5-2b --max-steps 2

# QLoRA 4bit 量化（显存 < 4GB 时，所有模型均可用）
python train_gpu_lora.py --qlora

# Qwen3.5-2B + QLoRA（显存不足时，会有警告但可继续）
python train_gpu_lora.py --preset qwen3.5-2b --qlora

# 自定义参数
python train_gpu_lora.py --epochs 5 --lora-rank 32 --batch-size 16
```

### 全量训练（CPU，不推荐，~5 小时）

```bash
# 过夜运行
python train_cpu_lora.py --epochs 3
```

## 推理验证

### 方法 1：直接 Python 脚本

```bash
# 训练后测试推理
python train_gpu_lora.py --test-infer
python train_gpu_lora.py --preset qwen3.5-2b --test-infer

# 或单独推理（自动检测模型）
python local_infer.py --fine-tuned "写一个冒泡排序"

# 指定模型预设
python local_infer.py --fine-tuned --preset qwen3.5-2b "写一个冒泡排序"
python local_infer.py --fine-tuned --preset qwen2.5-0.5b "写一个冒泡排序"
```

### 方法 2：自定义推理脚本

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

model_path = "tools/ai_copilot/model_cache/qwen2.5-0.5b"
lora_path = "tools/ai_copilot/output/qwen2.5_0.5b_light_gpu/final"

tokenizer = AutoTokenizer.from_pretrained(model_path)
base = AutoModelForCausalLM.from_pretrained(model_path, dtype=torch.float32)
model = PeftModel.from_pretrained(base, lora_path)

messages = [
    {"role": "system", "content": "你是光明翻译专家..."},
    {"role": "user", "content": "将以下 Python 翻译为光明：\ndef add(a,b): return a+b"},
]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=128)
print(tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True))
```

## 训练参数说明

| 参数 | CPU 默认 | GPU 默认 | 说明 |
|------|----------|----------|------|
| `--preset` | N/A | N/A | 模型预设（qwen2.5-0.5b / qwen2.5-1.5b / qwen3.5-2b），自动配置所有参数 |
| `--epochs` | 3 | 3 | 训练轮数 |
| `--lora-rank` | 8 | 16 | LoRA 秩，越大效果越好但越慢（qwen3.5-2b 预设为 32） |
| `--lora-alpha` | 16 | 32 | LoRA alpha，通常 = rank × 2（qwen3.5-2b 预设为 64） |
| `--lr` | 2e-4 | 2e-4 | 学习率（qwen3.5-2b 预设为 1e-4） |
| `--max-len` | 512 | 8192 | 最大序列长度 |
| `--batch-size` | 1 | 2 | 批大小（qwen3.5-2b 预设为 1） |
| `--grad-accum` | 16 | 8 | 梯度累积步数（qwen3.5-2b 预设为 16） |
| `--max-steps` | -1 | -1 | 最大步数（正数覆盖 epochs） |
| `--qlora` | N/A | False | 4bit 量化训练（所有模型可用，Qwen3.5 会警告） |

## 预期效果

训练 3 epochs 后，模型应能正确翻译：

| Python | 光明 |
|--------|------|
| `x = 10` | `设 x 为 10` |
| `def add(a, b): return a + b` | `段落 加法 接收 a, b：\n    返回 a 加 b` |
| `for i in range(10): print(i)` | `遍历 i 于 0至10：\n    打印(i)` |
| `if x > 5: print("大")` | `如果 x 大于 5：\n    打印("大")` |

## 后续步骤

1. **合并 LoRA**：`python merge_and_convert.py --merge-only`
   - 指定模型：`python merge_and_convert.py --preset qwen3.5-2b --merge-only`
2. **转 GGUF**：`python merge_and_convert.py --convert-gguf`
   - 指定模型：`python merge_and_convert.py --preset qwen3.5-2b --convert-gguf`
3. **集成到 CLI**：`light ai local "写一个冒泡排序"`
4. **部署到 ollama**：详见下方 [ollama 部署指南](#ollama-部署指南)

---

## ollama 部署指南

本节详细说明如何将微调后的光明翻译模型部署到 ollama，实现快速本地推理。

### 整体流程

```
LoRA 训练产物
  │
  ▼
merge_and_convert.py --merge-only    →  合并后的 safetensors 模型 (~1.9GB)
  │
  ▼
llama.cpp convert_hf_to_gguf.py      →  GGUF F16 模型 (~994MB)
  │
  ▼
fix_gguf_rope.py                      →  修复 GGUF 中 rope.freq_base=0.0 问题
  │
  ▼
ollama create -q q4_K_M               →  量化导入 ollama (~398MB)
  │
  ▼
ollama run light-translator            →  推理使用
```

### 第 0 步：准备文件

你需要准备以下文件（拷到目标机器）：

| 文件 | 说明 | 获取方式 |
|------|------|----------|
| `light_translator.gguf` | F16 格式 GGUF 模型 (~994MB) | `merge_and_convert.py --convert-gguf` 或 Kaggle 训练后转换 |
| `fix_gguf_rope.py` | GGUF 修复脚本 (4KB) | 仓库 `tools/ai_copilot/fix_gguf_rope.py` |
| `create_ollama_model.sh` | 一键创建脚本 (3KB) | 仓库 `tools/ai_copilot/create_ollama_model.sh` |

如果你已经有了量化后的 `light_translator_fixed.gguf`（修复 + 量化的最终文件），可以直接跳到第 3 步。

### 第 1 步：安装 ollama

**Windows**（推荐从 ModelScope 下载，国内速度快）：

1. 下载 `OllamaSetup.exe`：https://www.modelscope.cn/models/Liangdi/ollama-windows-release
2. 双击安装，默认路径 `C:\Users\<用户名>\AppData\Local\Programs\Ollama\`
3. 安装完成后 ollama 服务自动启动，托盘图标显示运行状态

验证安装：

```bash
ollama --version
# 应输出: ollama version is 0.13.x
```

**Linux**：

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 第 2 步：修复 GGUF 文件（rope.freq_base 问题）

**问题说明**：safetensors → GGUF 转换时，`qwen2.rope.freq_base` 会丢失为 `0.0`（应为 `1000000.0`），导致 ollama 推理时触发 `llama-sampling.cpp:662` 断言崩溃，返回 500 错误。

**修复方法**：

```bash
# 检查当前值
python fix_gguf_rope.py light_translator.gguf
# 输出: 当前 rope.freq_base = 0.0

# 修复（输出到新文件，原文件不变）
python fix_gguf_rope.py light_translator.gguf light_translator_fixed.gguf
# 输出:
#   当前 rope.freq_base = 0.0
#   修复完成: light_translator_fixed.gguf
#   验证 rope.freq_base = 1000000.0

# 也可以就地修改（自动创建 .bak 备份）
python fix_gguf_rope.py light_translator.gguf
```

**原理**：脚本解析 GGUF 二进制头部，定位 `qwen2.rope.freq_base` 的 float32 字节偏移（通常在偏移量 467），将其从 `0x00000000` 改为 `1000000.0` 对应的字节 `0x00247449`。

### 第 3 步：创建 Modelfile

在与 `light_translator_fixed.gguf` 同一目录下创建 `Modelfile`：

```bash
cat > Modelfile << 'EOF'
# 光明翻译器 — ollama Modelfile
FROM ./light_translator_fixed.gguf

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
"""

SYSTEM """你是光明（LightLang）编程语言 v3.2 的翻译专家。你的任务是将 Python 代码翻译为光明 v3.2 代码。只输出光明代码，不要解释。"""

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER stop "<|im_end|>"
EOF
```

**Modelfile 参数说明**：

| 参数 | 值 | 说明 |
|------|-----|------|
| `FROM` | `./light_translator_fixed.gguf` | 指向修复后的 GGUF 文件 |
| `TEMPLATE` | ChatML 格式 | Qwen2.5 的对话模板，`<\|im_start\|>` / `<\|im_end\|>` |
| `temperature` | 0.1 | 低温度保证翻译稳定性 |
| `num_ctx` | 4096 | 上下文窗口，长代码翻译需要更大窗口（v3 训练 max_len=8192，推理 4096 够用） |
| `stop` | `<\|im_end\|>` | 生成终止符 |

> **注意**：TEMPLATE 中不要有多余的 `{{ end }}`。Qwen2.5 的 ChatML 模板在 assistant 标签后直接结束，不需要 `{{ end }}` 闭合。多余的 `{{ end }}` 会导致 `template error: unexpected {{end}}`。

### 第 4 步：创建 ollama 模型

**方式 A：一键脚本（推荐）**

```bash
# 确保 light_translator_fixed.gguf 和 Modelfile 在同一目录
# 脚本会自动检测、修复、创建、验证
bash create_ollama_model.sh
```

**方式 B：手动命令**

```bash
# 创建量化模型（q4_K_M，994MB → 398MB）
ollama create light-translator -f Modelfile -q q4_K_M

# 查看模型列表
ollama list
# 应出现: light-translator:latest  398 MB
```

**量化级别选择**：

| 量化级别 | 大小 | 精度损失 | 速度 | 命令 |
|----------|------|----------|------|------|
| F16（不量化） | 994 MB | 无 | 最慢 | `-q f16` 或不指定 `-q` |
| Q8_0 | 528 MB | 极小 | 慢 | `-q q8_0` |
| Q5_K_M | 470 MB | 小 | 中 | `-q q5_k_m` |
| **Q4_K_M（推荐）** | **398 MB** | 小 | **快** | `-q q4_K_M` |
| Q4_K_S | 374 MB | 中 | 快 | `-q q4_k_s` |

对于 0.5B 参数的小模型，Q4_K_M 是精度和速度的最佳平衡点。

### 第 5 步：测试推理

```bash
# 基本测试 — 翻译加法函数
ollama run light-translator "def add(a, b): return a + b"
# 预期输出: 段落 加法 接收 a, b：
#               返回 a 加 b

# 翻译循环
ollama run light-translator "for i in range(10): print(i)"
# 预期输出: 遍历 i 于 0至10：
#               打印(i)

# 翻译条件
ollama run light-translator "if x > 5: print('big')"
# 预期输出: 如果 x 大于 5：
#               打印("big")
```

### 第 6 步：在项目中调用

通过 `local_infer.py` 使用 ollama 后端：

```bash
# 翻译 Python 代码
python local_infer.py --fine-tuned --backend ollama --mode translate "def add(a, b): return a + b"

# 交互模式
python local_infer.py --fine-tuned --backend ollama --interactive

# 生成光明代码（自然语言描述需求）
python local_infer.py --fine-tuned "写一个冒泡排序"
```

`local_infer.py` 内部通过 HTTP API 调用 ollama（`localhost:11434/api/generate`），无需额外安装 Python 依赖。

### 性能参考

| 环境 | 模型 | 量化 | 速度 | 单次翻译耗时 |
|------|------|------|------|-------------|
| CPU (i5-8250U, 24GB RAM) | Qwen2.5-0.5B | Q4_K_M | 0.01 tok/s | ~6 分钟（不可用） |
| GPU (RTX 3060 12GB) | Qwen2.5-0.5B | Q4_K_M | 预估 50+ tok/s | ~2 秒 |
| GPU (RTX 4090 24GB) | Qwen2.5-0.5B | Q4_K_M | 预估 100+ tok/s | ~1 秒 |
| GPU (RTX 3060 12GB) | Qwen3.5-2B | Q8_0 | 预估 40+ tok/s | ~2 秒 |
| GPU (RTX 4090 24GB) | Qwen3.5-2B | Q8_0 | 预估 80+ tok/s | ~1 秒 |

> 0.5B 模型在任意 GPU 上都极快。如果 CPU 推理太慢，务必使用 GPU 环境。
> Qwen3.5-2B 效果优于 0.5B（更强的代码理解能力），推荐在有 GPU 的环境下使用。

### 迁移到另一台机器

如果训练在本机完成，推理在另一台（更快的）机器上运行：

1. **拷贝 GGUF 文件**：将 `light_translator_fixed.gguf`（398MB 或 994MB F16）拷到目标机器
2. **拷贝脚本**：`fix_gguf_rope.py`、`create_ollama_model.sh`（或手动创建 Modelfile）
3. 在目标机器上安装 ollama
4. 如果 GGUF 未修复，先运行 `python fix_gguf_rope.py`
5. 创建 Modelfile 并 `ollama create light-translator -f Modelfile -q q4_K_M`
6. 测试：`ollama run light-translator "def add(a, b): return a + b"`

> **注意**：如果目标机器有 GPU，ollama 会自动检测并使用 GPU 推理，无需额外配置。可通过 `ollama ps` 查看模型运行在 CPU 还是 GPU 上。

### 故障排除

**问题：`ollama create` 超时或卡住**

ollama 需要读取 GGUF 文件并量化，994MB 文件可能需要几分钟。确保 `ollama create` 命令有足够超时时间（至少 5 分钟）。

**问题：推理返回 500 错误**

检查 ollama 日志（Windows: `%LOCALAPPDATA%\Ollama\server.log`）：
- 如果看到 `Assertion failed: found, file llama-sampling.cpp, line 662`，说明 `rope.freq_base` 未修复，回到第 2 步修复 GGUF
- 如果日志中 `freq_base = 0.0`，同样需要修复
- 修复后日志应显示 `freq_base = 1000000.0`

**问题：`template error: unexpected {{end}}`**

Modelfile 的 TEMPLATE 中有多余的 `{{ end }}`。正确的 ChatML 模板在 `<|im_start|>assistant\n` 后直接结束，不加 `{{ end }}`。

**问题：模型输出乱码或不相关**

1. 确认使用的是**微调后**的模型，而非基础模型
2. 检查 SYSTEM prompt 是否正确设置
3. 尝试降低 `temperature` 到 0
4. 确认 GGUF 是从**合并后**的 safetensors 转换的，而非基础模型

## 故障排除

### torch 导入失败（Windows）

```
OSError: [WinError 126] 找不到指定的模块
```

**解决**：安装 [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### 模型下载超时

**解决**：使用 HF 镜像 `HF_ENDPOINT=https://hf-mirror.com`，或用 `curl -C -` 断点续传

### 显存不足

**解决**：使用 QLoRA 4bit 量化 `--qlora`（所有模型均可用），或减小 `--batch-size` 和 `--max-len`

### torchao 版本不兼容

**报错**：`ImportError: Found an incompatible version of torchao. Found version 0.10.0, but only versions above 0.16.0 are supported`

**原因**：peft 依赖 torchao，低版本会触发 `is_torchao_available()` 中的版本检查异常。

**解决**：

```bash
pip install "torchao>=0.16.0"
```

或使用 `requirements-gpu.txt` 一键安装全部依赖：

```bash
pip install -r requirements-gpu.txt
```

### bitsandbytes 未安装

**报错**：`[WARN] bitsandbytes 未安装（仅 QLoRA 模式需要）`

**说明**：这只是一个警告，不影响 bf16 LoRA 训练。仅当使用 `--qlora` 时才需要安装。

**解决**（如需 QLoRA）：

```bash
pip install bitsandbytes
```

### Qwen3.5-2B 特有问题

**问题：`KeyError: 'qwen3'` 或模型加载失败**

确保已安装 `transformers>=5.0`：

```bash
pip install "transformers>=5.0"
```

**问题：Qwen3.5-2B + QLoRA 效果不佳**

Qwen3.5 官方不建议 QLoRA（量化差异可能偏高）。脚本会输出警告但允许继续训练。如效果不佳，请换用 bf16 LoRA 模式（去掉 `--qlora`），或减小 `--batch-size` 和 `--max-len`。

**问题：Qwen3.5 GGUF 转换失败**

Qwen3.5 模型架构较新，需要较新版本的 llama.cpp。请确保 `llama.cpp` 已更新到最新版本：

```bash
cd llama.cpp && git pull && pip install -r requirements.txt
```

## Kaggle 双 T4 + Swift 训练指南

如果你没有本地 GPU，可以使用 **Kaggle 免费双 T4 GPU** 进行训练。相比本地 LoRA 脚本，使用 **ms-swift** 框架在双 T4 上训练效率更高（batch_size=4, max_length=4096 不爆显存）。

> 详细博文：[Kaggle 双 T4 训练 Qwen2.5-0.5B 的正确打开方式](https://blog.csdn.net/skywalk8163/article/details/163384636)

### 为什么用 Swift？

| 对比项 | 本地 LoRA 脚本 | Kaggle + Swift |
|--------|---------------|----------------|
| 硬件 | 需自备 GPU | 免费双 T4 (15GB x2) |
| 框架 | peft + transformers | ms-swift |
| 分布式 | 单卡 | 双卡 (torchrun) |
| max_length | 1024~2048 | 4096 |
| batch_size | 1~2 | 4 |
| 训练速度 | ~9 分钟 (RTX 3060) | ~15 分钟 (3 epochs) |

### 完整流程

#### 1. 在 Kaggle 上创建 Notebook

访问 [Kaggle](https://www.kaggle.com/)，创建新 Notebook，选择 **双 T4 GPU** 加速器。

#### 2. 安装依赖

```bash
!pip install ms-swift[llm] -U -q
!pip install torchao -U -q
```

#### 3. 下载模型

用 transformers 下载（比 swift 自动下载更快）：

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen2.5-0.5B-Instruct"
save_dir = "./qwen2.5-0.5b-instruct"

tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.save_pretrained(save_dir)

model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
model.save_pretrained(save_dir)

print(f"下载完成，保存在 {save_dir}")
```

#### 4. 获取训练数据集

```bash
!git clone https://gitcode.com/skywalk163/light/
```

数据集路径：`/kaggle/working/light/tools/ai_copilot/sft_dataset.jsonl`

#### 5. 开始训练

使用 `torchrun` 启动双卡分布式训练：

```bash
!torchrun --nproc_per_node=2 \
    -m swift.cli.sft \
    --model "./qwen2.5-0.5b-instruct" \
    --dataset /kaggle/working/light/tools/ai_copilot/sft_dataset.jsonl \
    --max_length 4096 \
    --num_train_epochs 12 \
    --per_device_train_batch_size 4 \
    --learning_rate 5e-5 \
    --output_dir ./output_v2 \
    --logging_steps 5 \
    --save_steps 500 \
    --eval_steps 500 \
    --split_dataset_ratio 0.1 \
    --bf16 true
```

**关键参数说明：**

| 参数 | 说明 | 调优建议 |
|------|------|----------|
| `--num_train_epochs` | 训练轮数 | 12 epochs 效果最佳，3 epochs 快速验证 |
| `--per_device_train_batch_size` | 每卡 batch size | 双 T4 设为 4，爆显存则减为 2 |
| `--max_length` | 最大序列长度 | 4096 覆盖长代码样本 |
| `--learning_rate` | 学习率 | 5e-5 经验值 |
| `--save_steps` | 保存间隔步数 | 500 步保存一次 checkpoint |

**训练时间参考（双 T4）：**

| epochs | 步数 | 耗时 | eval_token_acc |
|--------|------|------|----------------|
| 3 | 201 | ~15 分钟 | 93.91% |
| 6 | 402 | ~30 分钟 | — |
| 12 | 804 | ~47 分钟 | 95.20% |

> 最终测试显示 **checkpoint-500**（12 epochs 中第 500 步）效果最好，18/18 测试全部通过。

#### 6. 合并 LoRA 模型

```bash
!swift merge-lora \
    --adapters /kaggle/working/output_v2/v7-20260801-042924/checkpoint-500
```

#### 7. 转换为 GGUF 并部署

合并后的模型需转换为 GGUF 格式才能用 ollama 加载。建议在本地机器上转换（Kaggle 上编译 llama.cpp 耗时较长）：

```bash
# 本地执行（需安装 llama.cpp）
python convert_hf_to_gguf.py merged_model/ --outfile light_translator.gguf --outtype f16
ollama create light-translator -f Modelfile
ollama run light-translator "def add(a, b): return a + b"
```

> 完整部署流程见上方「迁移到另一台机器」章节。

### 训练成果

最终训练得到的 v7 模型（checkpoint-500）已上线 Ollama：

```bash
ollama pull airoot/light-translator
```

模型主页：[https://ollama.com/airoot/light-translator](https://ollama.com/airoot/light-translator)
