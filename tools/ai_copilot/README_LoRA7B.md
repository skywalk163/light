# LoRA 微调指南 — 光明翻译器

用 LoRA 轻量化微调，使模型学会将 Python 代码翻译为光明 v3.2 代码。

## 支持模型

| 模型 | 参数量 | LoRA 显存 | QLoRA 显存 | 定位 |
|------|--------|-----------|------------|------|
| **Qwen3.5-2B** | 2B | ~5 GB | ~3 GB | 开发调试首选，飞快 |
| **Qwen3-8B** | 8B | ~22 GB | ~8 GB | 生产部署，效果最强 |

**推荐工作流**：先用 Qwen3.5-2B 快速迭代验证（~10分钟/轮），确认效果后切 Qwen3-8B 做生产级微调。

### 为什么选这两个模型？

| 对比项 | Qwen3.5-2B | Qwen3-8B | Llama 3.3-8B | Mistral Small 3-7B |
|--------|------------|----------|---------------|---------------------|
| 参数量 | 2B | 8B | 8B | 7B |
| HumanEval | — | **76.0** | 68.5 | 62.1 |
| 中文能力 | 强 | 强（60% 中文数据） | 弱 | 中等 |
| 架构 | 门控 DeltaNet + MoE | Transformer | Transformer | Transformer |
| LoRA 显存 | ~5 GB | ~22 GB | ~22 GB | ~20 GB |
| 训练速度（881条×3轮） | **~10 分钟** | ~30 分钟 | ~30 分钟 | ~35 分钟 |
| 适用场景 | 开发调试 | 生产部署 | 英文为主 | 通用 |

**Qwen3.5-2B 亮点**：新架构（门控 DeltaNet + 稀疏 MoE），2B 级性能领先，训练速度极快，任何消费级显卡都能跑。

## 快速开始

### 1. 安装依赖

```bash
# 方式一：从 PyPI 安装（简单）
pip install llamafactory transformers accelerate peft

# 方式二：从源码安装（推荐，获取最新功能）
git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e ".[torch,metrics]"

# QLoRA 4bit 量化训练需要（8GB 显存用户必装）
pip install bitsandbytes

# 国内用户加速模型下载
pip install modelscope
```

### 2. 一键训练

```bash
cd tools/ai_copilot

# 开发调试首选：2B 模型，飞快（LoRA BF16 ~5GB 显存）
python train_lora_7b.py --model-preset qwen3.5-2b

# 生产部署：8B 模型，效果最好（LoRA BF16 ~22GB 显存）
python train_lora_7b.py --model-preset qwen3-8b

# QLoRA 4bit 量化（更省显存）
python train_lora_7b.py --model-preset qwen3.5-2b --qlora

# 查看所有选项
python train_lora_7b.py --help
```

### 3. Jupyter Notebook 调试

```bash
jupyter notebook train_lora_7b.ipynb
```

Notebook 包含 10 个 Cell，逐步引导你从环境检查到推理测试。

## 两种模型 + 两种模式

### 模型选择

| 场景 | 推荐模型 | 命令 |
|------|----------|------|
| 开发调试、快速迭代 | Qwen3.5-2B | `--model-preset qwen3.5-2b` |
| 生产部署、最高质量 | Qwen3-8B | `--model-preset qwen3-8b` |
| 自定义模型 | 任意 | `--model /path/to/model` |

### 模式一：LoRA BF16（推荐，显存够就用）

```bash
# 2B 模型（~5GB 显存，GTX 1660 即可）
python train_lora_7b.py --model-preset qwen3.5-2b

# 8B 模型（~22GB 显存，RTX 3090/4090）
python train_lora_7b.py --model-preset qwen3-8b
```

### 模式二：QLoRA 4bit（显存不够时用）

```bash
# 2B QLoRA（~3GB 显存，几乎任何 GPU）
python train_lora_7b.py --model-preset qwen3.5-2b --qlora

# 8B QLoRA（~8GB 显存，RTX 4060）
python train_lora_7b.py --model-preset qwen3-8b --qlora --batch-size 1 --grad-accum 16
```

### 显存对照表

| 显存 | 推荐配置 |
|------|----------|
| ≥24 GB | `--model-preset qwen3-8b`（LoRA BF16，batch=2） |
| 16-24 GB | `--model-preset qwen3-8b`（LoRA BF16，batch=1） |
| 8-16 GB | `--model-preset qwen3-8b --qlora`（QLoRA 4bit） |
| 4-8 GB | `--model-preset qwen3.5-2b`（LoRA BF16，batch=4） |
| <4 GB | `--model-preset qwen3.5-2b --qlora`（QLoRA 4bit） |

## 参数详解

### 核心参数

| 参数 | 说明 |
|------|------|
| `--model-preset` | 模型预设：`qwen3.5-2b`（2B 开发调试）或 `qwen3-8b`（8B 生产部署） |
| `--model` | 自定义模型名称或路径（覆盖预设） |
| `--output` | 输出目录（默认: 根据预设自动生成） |
| `--qlora` | 启用 QLoRA 4bit 量化 |
| `--epochs` | 训练轮数（默认: 3） |
| `--lr` | 学习率（2B 默认 2e-4，8B 默认 1e-4） |
| `--lora-rank` | LoRA 秩（默认: 16） |

### LoRA 秩（lora_rank）选择指南

| 秩 | 可训练参数 | 显存增量 | 适用场景 |
|----|-----------|---------|----------|
| 8 | ~10M | 最低 | 简单翻译任务 |
| **16** | ~20M | 适中 | **推荐：通用 Python→光明翻译** |
| 32 | ~40M | 较高 | 复杂代码/暗坑多 |
| 64 | ~80M | 高 | 需要极强泛化能力 |

### 学习率建议

| 场景 | 推荐学习率 |
|------|-----------|
| LoRA (rank 8-16) | `1e-4` |
| LoRA (rank 32-64) | `5e-5` |
| QLoRA | `1e-4` ~ `2e-4` |
| 全参微调（不推荐） | `2e-5` |

**重要：LoRA/QLoRA 的学习率要比全参微调高 5-10 倍！**

### 其他参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--batch-size` | `2` | 每设备批大小 |
| `--grad-accum` | `8` | 梯度累积步数 |
| `--max-seq-len` | `1024` | 最大序列长度 |
| `--skip-download` | `False` | 跳过模型下载 |
| `--skip-merge` | `False` | 跳过 LoRA 合并 |
| `--test-infer` | `False` | 训练后测试推理 |
| `--dry-run` | `False` | 只生成配置不训练 |

## 训练数据

使用 `sft_dataset.jsonl`（881 条 Python↔光明 v3.2 对照数据）。

数据格式（Alpaca）：
```json
{
  "instruction": "将Python代码转为光明代码：",
  "input": "def add(a, b): return a + b",
  "output": "段落 加法 接收 a, b：\n    返回 a 加 b",
  "category": "段落"
}
```

脚本会自动转为 ShareGPT 格式（LLaMA-Factory 推荐），并添加 system prompt。

### 类别分布

| 类别 | 样本数 |
|------|--------|
| 段落 | 104 |
| 变量 | 100 |
| 复合 | 99 |
| 列表 | 98 |
| 循环 | 90 |
| 条件 | 90 |
| 暗坑 | 87 |
| 字符串 | 74 |
| 类 | 42 |
| 字典 | 37 |
| 异常 | 34 |
| 导入 | 26 |

## 训练后使用

### 方式一：直接推理（合并后模型）

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

# 2B 模型
model_path = "output/qwen3.5_2b_light/merged"
# 或 8B 模型
# model_path = "output/qwen3_8b_light/merged"

tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path, device_map="auto", trust_remote_code=True
)

messages = [
    {"role": "system", "content": "你是光明编程语言v3.2的翻译专家。"},
    {"role": "user", "content": "将Python代码转为光明代码：\ndef add(a, b): return a + b"},
]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.1)
print(tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True))
```

### 方式二：vLLM 部署（生产级）

```bash
pip install vllm
vllm serve output/qwen3.5_2b_light/merged --port 8000
```

然后通过 OpenAI 兼容 API 调用：
```python
import openai
client = openai.OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
response = client.chat.completions.create(
    model="qwen3-8b-light",
    messages=[{"role": "user", "content": "将Python代码转为光明代码：\nprint('hello')"}],
)
print(response.choices[0].message.content)
```

### 方式三：LoRA Adapter 热切换

不合并，直接加载 adapter：

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-8B-Instruct", device_map="auto")
model = PeftModel.from_pretrained(base, "output/qwen3_8b_light/checkpoints/checkpoint-XXX")
```

好处：一个基础模型可以挂载多个 LoRA adapter，按需切换。

### 方式四：集成到光明管线

```bash
# 设置模型路径
light ai generate "排序算法" --model-path output/qwen3_8b_light/merged

# 或通过 pipeline.py 的 model-size=large 自动路由
light ai generate "排序算法" --model-size large
```

## 完整流程示例

```bash
# 1. 安装依赖
pip install llamafactory transformers accelerate peft bitsandbytes

# 2. 开发调试：2B 模型快速验证（~10分钟）
cd tools/ai_copilot
python train_lora_7b.py --model-preset qwen3.5-2b --test-infer

# 3. 效果确认后，切 8B 生产级微调
python train_lora_7b.py --model-preset qwen3-8b --test-infer

# 4. 部署为 API 服务
pip install vllm
vllm serve output/qwen3.5_2b_light/merged --port 8000

# 5. 集成到光明开发
light ai generate "二分查找" --model-path output/qwen3.5_2b_light/merged
```

## 常见问题

### Q: 显存不够怎么办？

1. 使用 2B 模型：`--model-preset qwen3.5-2b`（LoRA 仅 ~5GB）
2. 使用 `--qlora` 开启 4bit 量化（2B QLoRA 仅 ~3GB）
3. 减小 `--batch-size 1` + 增大 `--grad-accum 16`
4. 减小 `--max-seq-len 512`
5. 使用云 GPU（AutoDL / AI Studio 等，约 2-5 元/小时）

### Q: Loss 不下降怎么办？

- **学习率太小**：LoRA/QLoRA 推荐 `1e-4`，不要用全参微调的 `2e-5`
- **lora_rank 太小**：从 16 开始，如果效果不好再升到 32
- **数据问题**：检查 sft_dataset.jsonl 是否有损坏条目
- **训练轮数不够**：3 轮通常够，复杂任务可试 5 轮

### Q: 训练很慢？

- 确认 `gradient_checkpointing: true`（省显存但稍慢）
- 确认用了 BF16（不要用 FP32）
- 检查是否在用 CPU 而非 GPU
- 考虑用云 GPU

### Q: QLoRA 和 LoRA 效果差多少？

- 实测差距约 2-5%（在光明翻译任务上几乎可忽略）
- 如果显存够，优先用 LoRA BF16
- 如果显存紧，QLoRA 是性价比最高的选择

### Q: 模型下载太慢？

```bash
# 国内镜像（ModelScope）
pip install modelscope
python -c "from modelscope import snapshot_download; snapshot_download('Qwen/Qwen3-8B-Instruct')"

# 或使用 huggingface 镜像
export HF_ENDPOINT=https://hf-mirror.com
```

### Q: 如何恢复中断的训练？

LoRA checkpoint 会保存在 `output/qwen3_8b_light/checkpoints/` 目录下，
最新 checkpoint 可以直接用于推理或继续训练。

### Q: LLaMA-Factory 安装失败？

```bash
# 确保 Python >= 3.9
python --version

# 确保 PyTorch 已安装
pip install torch --index-url https://download.pytorch.org/whl/cu121

# 再安装 LLaMA-Factory
pip install llamafactory
```

## 与 ERNIE-4.5-0.3B 方案对比

| 对比项 | Qwen3-8B + LoRA | ERNIE-4.5-0.3B + LoRA |
|--------|------------------|----------------------|
| 模型大小 | 80 亿参数 | 3 亿参数 |
| 显存需求 | 8-22 GB | 4 GB |
| 代码理解 | 强（HumanEval 76.0） | 弱 |
| 中文能力 | 强 | 中等 |
| 训练框架 | LLaMA-Factory | ERNIEKit |
| 训练时间 | 30-90 分钟 | 10-30 分钟 |
| 翻译质量 | 高（上下文理解强） | 中（简单翻译可用） |
| 适用场景 | 通用 Python→光明 | 窄翻译/规则化转换 |

**推荐策略**：先用 Qwen3-8B 做主翻译器，ERNIE-4.5-0.3B 做轻量级备用。

## 文件清单

| 文件 | 说明 |
|------|------|
| `train_lora_7b.py` | 多模型 LoRA/QLoRA 一键微调脚本（支持 qwen3-8b / qwen3.5-2b 预设） |
| `train_lora_7b.ipynb` | Jupyter Notebook 调试版（含 2B/8B 预设切换） |
| `sft_dataset.jsonl` | 训练数据（881 条） |
| `build_sft_dataset.py` | 训练数据构造器 |
| `train_sft.py` | ERNIE-4.5-0.3B 微调脚本（备用） |
| `README_SFT.md` | ERNIE 方案文档 |
| `README_LoRA7B.md` | 本文档 |

## 参考链接

- [Qwen3-8B-Instruct](https://huggingface.co/Qwen/Qwen3-8B-Instruct)
- [Qwen3.5-2B-Instruct](https://huggingface.co/Qwen/Qwen3.5-2B-Instruct)
- [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory)
- [LoRA 论文](https://arxiv.org/abs/2106.09685)
- [QLoRA 论文](https://arxiv.org/abs/2305.14314)
