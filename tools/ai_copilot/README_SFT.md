# 光明 AI Copilot — 微调训练指南

将 **ERNIE-4.5-0.3B** 微调为 Python → 光明 v3.2 代码翻译器。

即使你从未微调过大模型，按照本指南也能一步步完成。

---

## 这是什么？

一个 3 亿参数的小模型，经过微调后能将 Python 代码**自动翻译**为光明代码。

它不是万能的——不能从需求描述直接创作光明代码。但它擅长一件事：**看到 Python 代码，输出等价的光明代码**。

配合光明 AI 管线，工作流是：

```
用户需求 → 大模型生成 Python → 微调后的 0.3B 翻译为光明 → light ai check 验证
```

---

## 快速开始（3 步完成训练）

### 第 1 步：安装环境

```bash
# GPU 版本（推荐，训练约 1-2 小时）
pip install paddlepaddle-gpu
pip install --upgrade --pre paddlenlp
pip install --upgrade aistudio-sdk

# CPU 版本（也能跑，但训练需要 6-10 小时）
pip install paddlepaddle
pip install --upgrade --pre paddlenlp
pip install --upgrade aistudio-sdk
```

验证安装：

```bash
python -c "import paddle; print(paddle.__version__); print('GPU:', paddle.is_compiled_with_cuda())"
python -c "import paddlenlp; print(paddlenlp.__version__)"
```

### 第 2 步：生成训练数据

```bash
cd tools/ai_copilot
python build_sft_dataset.py
```

这会生成 `sft_dataset.jsonl`，包含 **881 条** Python↔光明对照数据。

### 第 3 步：一键训练

```bash
python train_sft.py
```

脚本会自动完成：环境检查 → 下载模型 → 生成配置 → 训练 → 合并权重。

---

## 两种训练方式

### 方式 A：一键脚本（推荐新手）

```bash
# 默认参数训练
python train_sft.py

# 自定义参数
python train_sft.py --epochs 5 --lora-rank 32 --lr 2e-4

# 只生成配置文件（不训练，检查参数是否正确）
python train_sft.py --dry-run

# 跳过模型下载（如果已经下载过）
python train_sft.py --skip-download
```

### 方式 B：Jupyter Notebook（推荐调试）

```bash
jupyter notebook train_sft.ipynb
```

每个步骤独立一个 Cell，可以逐个运行、调试、观察中间结果。

---

## 训练参数详解

| 参数 | 默认值 | 说明 | 调参建议 |
|------|--------|------|---------|
| `--epochs` | 3 | 训练轮数 | 3-5 轮通常足够，过多会过拟合 |
| `--lora-rank` | 16 | LoRA 秩 | 16 够用，32 效果稍好但显存翻倍 |
| `--lr` | 1e-4 | 学习率 | 1e-4 ~ 2e-4，太大会训练不稳定 |
| `--batch-size` | 4 | 批大小 | 4GB 显存用 2-4，8GB 可用 8 |
| `--max-seq-len` | 1024 | 最大序列长度 | 1024 够用，代码不会很长 |

**显存需求参考：**

| 显存 | batch_size | lora_rank | 预估训练时间 |
|------|-----------|-----------|-------------|
| 4 GB | 2 | 16 | ~3 小时 |
| 8 GB | 4 | 16 | ~1.5 小时 |
| 16 GB | 8 | 32 | ~40 分钟 |

---

## 训练数据说明

### 数据格式

每条数据是 JSONL 格式的一行：

```json
{
  "instruction": "将以下Python代码翻译为光明v3.2代码。",
  "input": "def add(a, b):\n    return a + b",
  "output": "段落 加法 接收 a, b：\n    返回 a 加 b",
  "category": "段落"
}
```

- `instruction`：任务指令（10 种变体随机选择）
- `input`：Python 代码
- `output`：对应的光明代码
- `category`：语法类别（用于统计）

### 数据类别分布

| 类别 | 条数 | 示例 |
|------|------|------|
| 段落 | 104 | 函数定义、递归 |
| 变量 | 100 | 声明、赋值、复合运算 |
| 复合 | 99 | 完整函数（排序/搜索/加密） |
| 列表 | 98 | 索引、追加、排序 |
| 循环 | 90 | 当、遍历、嵌套 |
| 条件 | 90 | 如果、否则、多分支 |
| 暗坑 | 87 | 运算符映射、关键字翻译 |
| 字符串 | 74 | 拼接、f-string、分割 |
| 类 | 42 | 定义、继承、构造 |
| 字典 | 37 | 创建、访问、遍历 |
| 异常 | 34 | try/catch/raise |
| 导入 | 26 | import/from-import |

### 添加自定义数据

编辑 `build_sft_dataset.py`，在 `_HANDCRAFTED` 列表中添加新条目：

```python
("类别", "Python 代码", "光明代码"),
```

然后重新运行：

```bash
python build_sft_dataset.py
```

---

## 训练后使用

### 方式 1：ERNIEKit 推理

```bash
# 启动推理服务
erniekit server output/light_translator/run_chat.yaml

# 或 CLI 对话
erniekit chat output/light_translator/run_chat.yaml
```

### 方式 2：PaddleNLP Python 推理

```python
from paddlenlp.transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("output/light_translator/merged")
model = AutoModelForCausalLM.from_pretrained("output/light_translator/merged", dtype="bfloat16")

prompt = "将以下Python代码翻译为光明v3.2代码。\n\ndef factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)"
inputs = tokenizer(prompt, return_tensors="pd")
outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.1)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

### 方式 3：GGUF 格式 + llama.cpp / Ollama

```bash
# 转换为 GGUF（需要自定义写入器，参考下方链接）
python train_sft.py --convert-gguf

# 用 llama.cpp 推理
llama-cli -m light_translator.gguf -p "def add(a, b): return a + b"

# 或用 Ollama
ollama create light-translator -f Modelfile
ollama run light-translator "def factorial(n): ..."
```

GGUF 转换详细教程：https://aistudio.baidu.com/projectdetail/9749867

### 方式 4：集成到光明 AI 管线

```
light ai generate "写一个冒泡排序" --model-size medium
→ 大模型输出 Python 代码

→ 喂给微调后的 0.3B 做翻译
→ 输出光明代码

→ light ai check output.light --run
→ 验证通过
```

---

## 常见问题

### Q：训练时报 CUDA out of memory

降低 batch_size 或 lora_rank：

```bash
python train_sft.py --batch-size 2 --lora-rank 8
```

### Q：CPU 能训练吗？

可以，但很慢（6-10 小时）。需要修改配置：
- 训练配置中 `dtype` 改为 `"float32"`
- `bf16` 改为 `false`

### Q：训练数据太少怎么办？

在 `build_sft_dataset.py` 的 `_HANDCRAFTED` 中添加更多对照对，然后重新运行。

建议：
- 每个语法类别至少 20 条
- 优先补充"复合"类（完整函数），这是最有价值的
- 暗坑类数据帮助模型避开常见错误

### Q：训练后效果不好？

可能原因和对策：

| 症状 | 原因 | 对策 |
|------|------|------|
| 输出乱码 | epochs 太多过拟合 | 减少到 2-3 轮 |
| 不遵循指令 | 学习率太大 | 降到 5e-5 |
| 语法错误 | 暗坑数据不够 | 补充更多暗坑对照对 |
| 只会翻译短代码 | 长代码数据不够 | 补充更多"复合"类数据 |

### Q：ERNIEKit 命令找不到？

确保 PaddleNLP 版本正确：

```bash
pip install --upgrade --pre paddlenlp
erniekit --help  # 验证 CLI 可用
```

### Q：模型下载失败？

手动下载：

```bash
# 方式 1：aistudio-sdk
aistudio download --model paddlepaddle/ernie-4.5-0.3b

# 方式 2：HuggingFace
git lfs install
git clone https://huggingface.co/baidu/ERNIE-4.5-0.3B

# 方式 3：浏览器下载
# 访问 https://huggingface.co/baidu/ERNIE-4.5-0.3B
```

---

## 文件清单

```
tools/ai_copilot/
├── README_SFT.md          ← 本文档
├── build_sft_dataset.py   ← 训练数据构造脚本
├── sft_dataset.jsonl      ← 生成的训练数据（881条）
├── train_sft.py           ← 一键训练脚本
├── train_sft.ipynb        ← Jupyter Notebook 版本
├── pipeline.py            ← 一揽子管线（generate/fix）
├── syntax_card.py         ← 语法速查卡生成器
├── snippets.py            ← 代码片段库
└── prompt_generator.py    ← Prompt 生成器
```

---

## 参考链接

- ERNIE-4.5 开源模型：https://huggingface.co/baidu
- ERNIEKit 文档：https://github.com/PaddlePaddle/ERNIE
- GGUF 转换教程：https://aistudio.baidu.com/projectdetail/9749867
- 光明项目：`c:\traework\light`
