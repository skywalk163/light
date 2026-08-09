#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明翻译器 — GPU LoRA 微调脚本

针对 GPU 环境优化，使用 transformers + peft 在 GPU 上对
Qwen2.5-0.5B-Instruct / Qwen3.5-2B-Instruct 等模型进行 LoRA 微调。

与 train_cpu_lora.py 的区别：
  - 使用 bf16 混合精度（GPU 原生支持，速度提升 2-3 倍）
  - 更大 batch_size（16 vs 1），充分利用 GPU 并行
  - 更大 max_len（8192 vs 256），覆盖系统提示+长代码样本
  - 更多 LoRA target modules（all-linear），效果更好
  - 支持 QLoRA 4bit 量化（显存不够时的降级方案，所有模型均可用）
  - 支持 gradient_checkpointing（省显存，适合大模型）
  - 支持模型预设（--preset），自动配置不同模型的训练参数

支持的模型预设：
  qwen2.5-0.5b  — Qwen2.5-0.5B-Instruct (0.5B, LoRA ~5GB, QLoRA ~3GB)
  qwen2.5-1.5b  — Qwen2.5-1.5B-Instruct (1.5B, LoRA ~10GB, QLoRA ~4GB)
  qwen3.5-2b    — Qwen3.5-2B (2B, 多模态架构, LoRA ~5GB, QLoRA ~3GB, 需 transformers>=5.0)

预计训练时间（978 条 × 3 epochs = 2934 样本）：
  Qwen2.5-0.5B / RTX 3060 (12GB):  ~9 分钟
  Qwen2.5-0.5B / RTX 4090 (24GB):  ~3 分钟
  Qwen3.5-2B   / RTX 3060 (12GB):  ~25 分钟
  Qwen3.5-2B   / RTX 4090 (24GB):  ~8 分钟

支持的平台/GPU：
  RTX 3060/4060/4070/4090 (12-24GB)  — 默认参数直接跑
  Kaggle 双 T4 (2x16GB)               — 自动检测双 GPU，启用 DDP 分布式训练
  Kaggle 单 T4 (16GB)                  — 默认参数直接跑（T4 不支持 bf16，自动切 fp16）
  Google Colab T4 (16GB)              — 同上
  8GB 显存 GPU (如 GTX 1070/2060)     — 用 --qlora + --max-len 1024 可跑

参数优先级：
  命令行参数 > --preset 预设值 > 内置默认值
  例如: --preset qwen3.5-2b --max-len 2048
        max_len 使用命令行的 2048，其余参数用预设值

显存需求（gradient_checkpointing=on）：
  标准模式 (HF + PEFT):
    T4 fp16 权重策略: fp16 模型 + fp32 LoRA 参数, 无 AMP
      Qwen2.5-0.5B LoRA  (max_len=8192): ~3 GB   ← T4 16GB 轻松跑
      Qwen2.5-1.5B LoRA  (max_len=4096): ~6 GB   ← T4 可跑
      Qwen3.5-2B   LoRA  (max_len=4096): ~5 GB   ← T4 可跑
    bf16 GPU 策略: fp32 模型 + bf16 AMP
      Qwen2.5-0.5B LoRA  (max_len=8192): ~5 GB
      Qwen2.5-1.5B LoRA  (max_len=8192): ~10 GB
      Qwen3.5-2B   LoRA  (max_len=8192): ~6 GB
    QLoRA 4bit (所有 GPU):
      Qwen2.5-0.5B QLoRA (max_len=8192): ~3 GB
      Qwen2.5-1.5B QLoRA (max_len=8192): ~4 GB
      Qwen3.5-2B   QLoRA (max_len=8192): ~3 GB

  Unsloth 模式 (--unsloth, 省 30-50% 显存 + 2x 加速):
    Qwen2.5-0.5B LoRA      (max_len=8192): ~3 GB   ← T4 16GB 轻松跑
    Qwen2.5-1.5B LoRA      (max_len=8192): ~5 GB
    Qwen3.5-2B   LoRA      (max_len=8192): ~3 GB   ← T4 16GB 可跑

T4 注意事项：
  - T4 是 Turing 架构（compute capability 7.5），不支持原生 bf16
  - 脚本自动检测 GPU 并切换为 fp16 模式
  - QLoRA 的 compute_dtype 也会自动适配为 fp16
  - T4 16GB 显存可跑所有预设的 LoRA 模式（0.5B/1.5B/3.5-2B）

Kaggle 双 T4 DDP 注意事项：
  - Kaggle 提供双 T4 环境，脚本自动检测多 GPU 并启用 DDP
  - DDP 模式下每个 GPU 各跑一份模型副本，数据并行
  - 等效 batch = per_device_batch_size × num_gpus × grad_accum
  - DDP 下不要手动 .to(device)，Trainer 自动处理设备分配
  - 如需禁用多 GPU，设置环境变量 CUDA_VISIBLE_DEVICES=0

用法：
    # 标准训练（默认 Qwen2.5-0.5B）
    python train_gpu_lora.py

    # 使用 Qwen3.5-2B 预设（自动配置参数）
    python train_gpu_lora.py --preset qwen3.5-2b

    # 快速验证（2步）
    python train_gpu_lora.py --max-steps 2

    # QLoRA 4bit 量化训练（显存不够时，所有模型均可用）
    python train_gpu_lora.py --qlora

    # Unsloth 优化后端（省 30-50% 显存 + 2x 加速，T4 推荐）
    python train_gpu_lora.py --unsloth

    # Unsloth + Qwen3.5-2B（T4 16GB 可跑 max_len=8192）
    python train_gpu_lora.py --preset qwen3.5-2b --unsloth

    # 8GB 显存推荐配置（如 GTX 1070/2060）
    python train_gpu_lora.py --qlora --max-len 1024 --batch-size 1

    # 使用更大模型
    python train_gpu_lora.py --model-path ./model_cache/qwen2.5-1.5b

    # 自定义参数
    python train_gpu_lora.py --epochs 5 --lora-rank 16 --batch-size 8

    # 训练后测试推理
    python train_gpu_lora.py --test-infer

前置条件：
    # GPU 版 PyTorch（根据 CUDA 版本选择）
    pip install torch --index-url https://download.pytorch.org/whl/cu121
    pip install transformers peft datasets accelerate

    # Qwen3.5 需要 transformers >= 5.0
    pip install transformers>=5.0

    # 如需 QLoRA 4bit 量化训练（显存不够时）
    pip install bitsandbytes

    # 如需 Qwen3.5-2B，还需确保 torchao >= 0.16.0
    pip install "torchao>=0.16.0"
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ── 路径常量 ─
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATASET_PATH = os.path.join(_SCRIPT_DIR, "sft_dataset.jsonl")
_DEFAULT_MODEL_PATH = os.path.join(_SCRIPT_DIR, "model_cache", "qwen2.5-0.5b")
_DEFAULT_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "output", "qwen2.5_0.5b_light_gpu")

# ── 模型预设 ─
# 不同模型自动配置不同的训练参数
MODEL_PRESETS = {
    "qwen2.5-0.5b": {
        "model_path": os.path.join(_SCRIPT_DIR, "model_cache", "qwen2.5-0.5b"),
        "output_dir": os.path.join(_SCRIPT_DIR, "output", "qwen2.5_0.5b_light_gpu"),
        "max_len": 8192,
        "batch_size": 2,
        "grad_accum": 8,
        "lora_rank": 16,
        "lora_alpha": 32,
        "lr": 2e-4,
        "allow_qlora": True,
        "desc": "Qwen2.5-0.5B-Instruct (0.5B, LoRA ~5GB / QLoRA ~3GB)",
    },
    "qwen2.5-1.5b": {
        "model_path": os.path.join(_SCRIPT_DIR, "model_cache", "qwen2.5-1.5b"),
        "output_dir": os.path.join(_SCRIPT_DIR, "output", "qwen2.5_1.5b_light_gpu"),
        "max_len": 8192,
        "batch_size": 1,
        "grad_accum": 4,
        "lora_rank": 16,
        "lora_alpha": 32,
        "lr": 2e-4,
        "allow_qlora": True,
        "desc": "Qwen2.5-1.5B-Instruct (1.5B, LoRA ~10GB / QLoRA ~4GB)",
    },
    "qwen3.5-2b": {
        "model_path": os.path.join(_SCRIPT_DIR, "model_cache", "qwen3.5-2b"),
        "output_dir": os.path.join(_SCRIPT_DIR, "output", "qwen3.5_2b_light_gpu"),
        "max_len": 8192,
        "batch_size": 1,
        "grad_accum": 4,
        "lora_rank": 32,
        "lora_alpha": 64,
        "lr": 1e-4,
        "allow_qlora": True,  # 允许 QLoRA（官方不建议但显存不足时可用）
        "desc": "Qwen3.5-2B (2B, 多模态架构, LoRA ~5GB / QLoRA ~3GB, 需 transformers>=5.0)",
    },
}

# ── 系统提示词（与 CPU 版一致）──
SYSTEM_PROMPT = (
    "你是光明（LightLang）编程语言 v3.2 的翻译专家。"
    "光明是一种中文编程语言，使用中文关键字。"
    "你的任务是将 Python 代码翻译为光明 v3.2 代码。\n"
    "关键规则：\n"
    "- 变量赋值: 设 x 为 10\n"
    "- 字符串赋值: 定义 s 等于 \"hello\"\n"
    "- 段落定义: 段落 名 接收 参数：\n"
    "- 条件: 如果 / 否则若 / 否则：\n"
    "- 循环: 遍历 i 于 0至N： / 当 条件：\n"
    "- 运算: 加上/减去/乘以/除以/取余/幂\n"
    "- 比较: 等于/不等于/大于/小于/大于等于/小于等于\n"
    "- 逻辑: 且/或/非\n"
    "- 布尔: 真/假/空\n"
    "- 跳转: 跳出(break)/跳过(continue)/返回(return)\n"
    "- 长度: 用 len() 而非 长度()\n"
    "- 列表索引赋值: lst[0] = 10\n"
    "- 打印: 打印(x)\n"
    "- f-string: 直接保留 f\"...{var}...\" 格式, f-string内的变量名保持原样不翻译\n"
    "- 变量赋值规则: 数字/布尔/None/列表/字典用 设 x 为 Y; 仅纯字符串赋值可用 定义 s 等于 \"hello\"\n"
    "- 列表推导: [expr 遍历 var 之 列表 若 条件]\n"
    "- 字典推导: {k: v 遍历 k, v 之 d.items() 若 条件}\n"
    "- 集合推导: {expr 遍历 var 之 列表 若 条件}\n"
    "- 类定义: 类 名：\n"
    "- 类属性: 属性 名\n"
    "- 类构造: 构造 接收 参数：\n"
    "- 类方法: 段落 名：\n"
    "- 类继承: 类 子类 继承 父类：\n"
    "- 父类调用: 父.方法名(参数)\n"
    "- self引用: 己.属性 / 己.方法()\n"
    "- 访问控制: 公有/私有/保护 属性\n"
    "- 静态方法: 静态 段落 名 接收 参数：\n"
    "- 类方法: 类方法 段落 名：\n"
    "- 特性: 特性 段落 名：\n"
    "- 异常处理: 尝试：/捕获 异常类型 [e]：/最终：\n"
    "- 抛出异常: 抛出 \"message\" / 抛出 新建 异常类型(\"msg\")\n"
    "- with语句: 使用 资源 为 变量：\n"
    "- lambda: 接收 参数：返回 表达式\n"
    "- 高阶函数: 筛选(谓词, 数据) / 映射(函数, 数据) / reduce(函数, 数据)\n"
    "- 排序: sorted(数据, key=接收 x：返回 x[0])\n"
    "- 文件读取: 读取文件(\"file.txt\")\n"
    "- 文件写入: 打开文件(\"file.txt\", \"w\")\n"
    "- 装饰器: @标注名 标注\n"
    "- 变量名保持: 变量名、函数名、类名、方法名保持英文原样，不翻译为中文\n"
    "- 复合赋值: x += y -> 设 x 为 x 加上 y; x -= y -> 设 x 为 x 减去 y; x *= y -> 设 x 为 x 乘以 y; x /= y -> 设 x 为 x 除以 y\n"
    "- 负数字面量: -1, -100 等负数保持原样，返回 -1 而非 返回 减 1\n"
    "- 整除运算: // 翻译为 整除; / 翻译为 除以\n"
    "- 取余运算: % 翻译为 取余\n"
    "- 幂运算: ** 翻译为 幂\n"
    "- 方法调用: 对象方法调用保持原样，如 s.upper(), lst.append(x), d.get(key) 不翻译方法名\n"
    "- break/continue: break -> 跳出; continue -> 跳过; 不可混用 返回 替代 break\n"
    "- 多返回值: return a, b 保持原样; x, y = func() 分别赋值\n"
    "- 异常类型: 捕获具体异常类型，如 捕获 ZeroDivisionError 为 e\n"
    "只输出光明代码，不要解释。"
)


# ═══════════════════════════════════════════════════════════════════
# GPU 能力检测
# ═══════════════════════════════════════════════════════════════════

def get_gpu_capability() -> tuple:
    """检测 GPU 的 compute capability 和是否支持 bf16。
    
    Returns:
        (major, minor) — compute capability, 如 (8, 6) 表示 SM 8.6
        如果无 GPU 返回 (0, 0)
    """
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_capability(0)
    except Exception:
        pass
    return (0, 0)


def supports_bf16() -> bool:
    """检测当前 GPU 是否支持原生 bf16（需要 Ampere+, SM >= 8.0）。"""
    major, _ = get_gpu_capability()
    return major >= 8


def get_train_dtype():
    """获取训练精度：bf16 优先，T4 等不支持时回退到 fp16。"""
    import torch
    if not torch.cuda.is_available():
        return torch.float32
    if supports_bf16():
        return torch.bfloat16
    print("  [INFO] GPU 不支持 bf16（Turing 架构如 T4），使用 fp16 替代")
    return torch.float16


def get_gpu_count():
    """检测可用 GPU 数量。"""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.device_count()
    except Exception:
        pass
    return 0


def detect_kaggle_multi_t4():
    """检测是否运行在 Kaggle 双 T4 环境中。

    Kaggle 提供的双 T4 环境特征:
    - 2 块 Tesla T4 GPU
    - 路径 /kaggle/working 或环境变量 KAGGLE_KERNEL_RUN_TYPE 存在
    """
    try:
        import torch
        if not torch.cuda.is_available():
            return False
        gpu_count = torch.cuda.device_count()
        if gpu_count < 2:
            return False
        # 检查是否所有 GPU 都是 T4
        all_t4 = all(
            "T4" in torch.cuda.get_device_name(i)
            for i in range(gpu_count)
        )
        # 检查 Kaggle 环境标志
        is_kaggle = (
            os.path.exists("/kaggle/working")
            or os.environ.get("KAGGLE_KERNEL_RUN_TYPE") is not None
        )
        return all_t4 and is_kaggle
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════
# 第 1 步：环境检查
# ═══════════════════════════════════════════════════════════════════

def check_environment(require_gpu: bool = True) -> bool:
    """检查 GPU 环境"""
    print("=" * 60)
    print("第 1 步：环境检查（GPU 模式）")
    print("=" * 60)

    ok = True

    # PyTorch + CUDA
    try:
        import torch
        print(f"  [OK] PyTorch {torch.__version__}")
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            major, minor = torch.cuda.get_device_capability(0)
            if gpu_count > 1:
                print(f"  [OK] 检测到 {gpu_count} 块 GPU:")
                for i in range(gpu_count):
                    name_i = torch.cuda.get_device_name(i)
                    mem_i = torch.cuda.get_device_properties(i).total_memory / 1e9
                    print(f"         GPU {i}: {name_i} ({mem_i:.1f} GB)")
                if detect_kaggle_multi_t4():
                    print(f"  [OK] Kaggle 双 T4 环境检测到，将启用 DDP 分布式训练")
            else:
                print(f"  [OK] GPU: {gpu_name} ({gpu_mem:.1f} GB, SM {major}.{minor})")
            if not supports_bf16():
                print(f"  [INFO] 此 GPU 不支持原生 bf16（需 SM >= 8.0），将自动使用 fp16")
        else:
            if require_gpu:
                print("  [FAIL] 未检测到 GPU，此脚本需要 GPU 环境")
                print("         如需 CPU 训练，请使用 train_cpu_lora.py")
                ok = False
            else:
                print("  [WARN] 未检测到 GPU，将回退到 CPU 模式（会很慢）")
    except ImportError:
        print("  [FAIL] PyTorch 未安装")
        print("         pip install torch --index-url https://download.pytorch.org/whl/cu121")
        ok = False

    # transformers
    try:
        import transformers
        print(f"  [OK] transformers {transformers.__version__}")
    except ImportError:
        print("  [FAIL] transformers 未安装")
        ok = False

    # peft
    try:
        import peft
        print(f"  [OK] peft {peft.__version__}")
    except ImportError:
        print("  [FAIL] peft 未安装")
        ok = False

    # bitsandbytes（QLoRA 需要）
    try:
        import bitsandbytes
        print(f"  [OK] bitsandbytes {bitsandbytes.__version__}")
    except ImportError:
        print("  [WARN] bitsandbytes 未安装（仅 QLoRA 模式需要，安装: pip install bitsandbytes）")

    # torchao（peft 依赖，版本不兼容会导致 LoRA 创建失败）
    try:
        import torchao
        version = getattr(torchao, "__version__", "unknown")
        print(f"  [OK] torchao {version}")
        # peft 要求 torchao >= 0.16.0，低版本会触发 ImportError
        if version != "unknown":
            try:
                major, minor = version.split(".")[:2]
                if int(major) == 0 and int(minor) < 16:
                    print(f"  [WARN] torchao 版本过低 ({version})，peft 需要 >= 0.16.0")
                    print(f"         升级: pip install \"torchao>=0.16.0\"")
            except (ValueError, IndexError):
                pass
    except ImportError:
        print("  [INFO] torchao 未安装（非必须，但 peft 可能需要）")

    # unsloth（可选，省显存 + 加速）
    # 注意：只用 find_spec 检测是否安装，不触发 import（避免初始化报错）
    try:
        import importlib.util
        if importlib.util.find_spec("unsloth"):
            print(f"  [OK] unsloth 已安装（可用 --unsloth 启用）")
        else:
            raise ImportError
    except ImportError:
        print("  [INFO] unsloth 未安装（可选，安装后可用 --unsloth 省显存加速）")
        print("         安装: pip install unsloth")

    # 数据集
    if os.path.exists(_DATASET_PATH):
        with open(_DATASET_PATH, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f)
        print(f"  [OK] 数据集: {_DATASET_PATH} ({count} 条)")
    else:
        print(f"  [FAIL] 数据集不存在: {_DATASET_PATH}")
        ok = False

    return ok


# ═══════════════════════════════════════════════════════════════════
# 第 2 步：数据集
# ═══════════════════════════════════════════════════════════════════

import torch
from torch.utils.data import Dataset


class LightSFTDataset(Dataset):
    """光明 SFT 数据集（与 CPU 版共用同一数据格式）"""

    def __init__(self, jsonl_path: str, tokenizer, max_len: int = 512):
        self.data = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                self.data.append(item)
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        instruction = item.get("instruction", "将Python代码转为光明代码：")
        code_input = item.get("input", "")
        output = item.get("output", "")

        # 构造 user 消息
        if code_input:
            user_msg = f"{instruction}\n\nPython 代码：\n{code_input}"
        else:
            user_msg = instruction

        # 构造 prompt 部分（system + user，不计算 loss）
        prompt_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        prompt_text = self.tokenizer.apply_chat_template(
            prompt_messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        # 构造完整文本（prompt + assistant 回复）
        full_messages = prompt_messages + [
            {"role": "assistant", "content": output},
        ]
        full_text = self.tokenizer.apply_chat_template(
            full_messages,
            tokenize=False,
            add_generation_prompt=False,
        )

        # tokenize
        prompt_ids = self.tokenizer(
            prompt_text, truncation=True, max_length=self.max_len,
            return_tensors=None,
        )["input_ids"]

        full_ids = self.tokenizer(
            full_text, truncation=True, max_length=self.max_len,
            return_tensors=None,
        )["input_ids"]

        # labels: prompt 部分设为 -100，只对 assistant 回复计算 loss
        labels = list(full_ids)
        prompt_len = len(prompt_ids)
        for i in range(min(prompt_len, len(labels))):
            labels[i] = -100

        # padding 到 max_len
        pad_id = self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
        attention_mask = [1] * len(full_ids)

        while len(full_ids) < self.max_len:
            full_ids.append(pad_id)
            attention_mask.append(0)
            labels.append(-100)

        # 截断到 max_len
        full_ids = full_ids[: self.max_len]
        attention_mask = attention_mask[: self.max_len]
        labels = labels[: self.max_len]

        return {
            "input_ids": torch.tensor(full_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


# ═══════════════════════════════════════════════════════════════════
# 第 3 步：训练
# ═══════════════════════════════════════════════════════════════════

def train(
    model_path: str,
    output_dir: str,
    epochs: int = 3,
    lora_rank: int = 16,
    lora_alpha: int = 32,
    lr: float = 2e-4,
    max_len: int = 8192,
    batch_size: int = 2,
    grad_accum: int = 8,
    warmup_ratio: float = 0.05,
    save_steps: int = 50,
    dataset_path: str = None,
    max_steps: int = -1,
    use_qlora: bool = False,
    gradient_checkpointing: bool = True,
    use_unsloth: bool = False,
):
    """执行 GPU LoRA 微调"""
    from transformers import (
        TrainingArguments,
        Trainer,
    )

    # 检测多 GPU 环境
    gpu_count = get_gpu_count()
    use_multi_gpu = gpu_count > 1
    is_kaggle_dual_t4 = detect_kaggle_multi_t4()

    print("\n" + "=" * 60)
    print("第 2 步：加载模型")
    print("=" * 60)
    print(f"  模型路径: {model_path}")
    print(f"  QLoRA 4bit: {'是' if use_qlora else '否'}")
    if use_multi_gpu:
        print(f"  [多GPU] 检测到 {gpu_count} 块 GPU，将启用 DDP 分布式训练")
        if is_kaggle_dual_t4:
            print(f"  [Kaggle] 双 T4 环境已确认")

    # 自动检测 GPU 精度能力（T4 不支持 bf16，自动切 fp16）
    train_dtype = get_train_dtype()
    use_fp16 = (train_dtype == torch.float16)
    if use_fp16:
        print("  [INFO] 使用 fp16 精度（GPU 不支持 bf16）")
    else:
        print("  [INFO] 使用 bf16 精度")

    # ── Qwen3.5 MoE 保护：fp16 直接加载会导致 grad_norm=nan ──
    # Qwen3.5 是 MoE 架构，gating 网络对精度极敏感：
    #   fp16 加载 → gate softmax 溢出 → NaN 传播 → loss=0
    #
    # 策略：
    #   多 GPU (双 T4):  fp32 加载 + DDP（每卡 ~12GB, 16GB 够用）
    #   单 GPU (T4):     QLoRA NF4（fp32 2B + 长序列可能 OOM）
    #   bf16 GPU:        fp32 加载 + bf16 AMP（原生支持）
    model_path_lower = model_path.lower().replace(os.sep, "/")
    is_qwen35 = "qwen3.5" in model_path_lower or "qwen3_5" in model_path_lower
    if is_qwen35 and use_fp16 and not use_qlora and not use_unsloth:
        if use_multi_gpu:
            # 多 GPU：fp32 加载保持 DDP，限制 max_len 适配显存
            print("  [AUTO] Qwen3.5 MoE + 多GPU + T4(fp16) → 使用 fp32 加载保持 DDP")
            print("         原因: MoE gating 对 fp16 敏感, fp32 加载可避免 NaN")
            print("         DDP 双卡并行 > QLoRA 单卡量化")
            use_fp16 = False  # 强制 fp32 加载
            if max_len > 2048:
                print(f"         max_len {max_len}→2048（fp32 模型显存适配）")
                max_len = 2048
        else:
            # 单 GPU：QLoRA 避免 fp32 OOM
            print("  [AUTO] Qwen3.5 MoE + 单GPU + T4(fp16) → 自动启用 QLoRA")
            print("         原因: MoE gating 网络对 fp16 精度敏感，直接 fp16 加载会导致 NaN")
            print("         QLoRA NF4 量化在 compute 阶段恢复 fp16，对 gate 更稳定")
            use_qlora = True

    # ════════════════════════════════════════════════════════════
    # 模型加载 — 两条路径：Unsloth（优化） / 标准 HF+PEFT
    # ════════════════════════════════════════════════════════════
    if use_unsloth:
        # ── Unsloth 路径：节省 30-50% 显存，速度提升 2x ──
        # Unsloth 必须在 transformers/peft 之前导入才能生效
        # Kaggle Python 3.12 可能不兼容，导入失败时自动降级到标准模式
        try:
            from unsloth import FastLanguageModel
        except (ImportError, NameError, Exception) as e:
            print(f"  [WARN] Unsloth 导入失败: {e}")
            print(f"  [WARN] 自动降级到标准 HF+PEFT 模式")
            print(f"         Unsloth 可能与当前 Python/transformers 版本不兼容")
            print(f"         可去掉 --unsloth 使用标准模式训练")
            use_unsloth = False

    if use_unsloth:
        # ── Unsloth 路径：节省 30-50% 显存，速度提升 2x ──
        print("  [Unsloth] 使用 Unsloth 优化后端（省显存 + 加速）")

        # Unsloth 自动处理：量化加载、设备分配、梯度检查点、混合精度
        # dtype=None 让 Unsloth 自动选择（T4→fp16, Ampere+→bf16）
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_path,
            max_seq_length=max_len,
            dtype=None,            # 自动选择精度
            load_in_4bit=use_qlora,  # QLoRA 时用 4bit
            trust_remote_code=True,
        )

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            tokenizer.pad_token_id = tokenizer.eos_token_id

        backend_name = "QLoRA 4bit" if use_qlora else "LoRA"
        print(f"  [Unsloth] 模型已 {backend_name} 加载")

        # Unsloth 的梯度检查点（比 HF 标准模式更省显存）
        if gradient_checkpointing:
            # Unsloth 在 get_peft_model 中处理 gradient checkpointing
            use_gc_unsloth = "unsloth"
        else:
            use_gc_unsloth = False

        # ── 配置 LoRA（Unsloth 版）──
        print("\n" + "=" * 60)
        print("第 3 步：配置 LoRA (Unsloth)")
        print("=" * 60)

        model = FastLanguageModel.get_peft_model(
            model,
            r=lora_rank,
            lora_alpha=lora_alpha,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            use_gradient_checkpointing=use_gc_unsloth,
            random_state=42,
        )
        model.print_trainable_parameters()

    else:
        # ── 标准 HF + PEFT 路径 ──
        # 屏蔽 unsloth_zoo 的 monkey-patch（避免 KeyError: 'input_embeds'）
        # unsloth_zoo 在 import 时会 patch transformers 的 Qwen3.5 attention 逻辑，
        # 导致标准 HF 路径传 input_ids 时因缺少 input_embeds key 而崩溃
        import importlib
        import importlib.util as _ilu
        if _ilu.find_spec("unsloth_zoo"):
            # 1) 清除已加载的 unsloth_zoo 相关模块
            for _mod in list(sys.modules.keys()):
                if "unsloth_zoo" in _mod:
                    del sys.modules[_mod]
            # 2) 阻止重新导入（设为 None 后 import 会报 ModuleNotFoundError）
            sys.modules["unsloth_zoo"] = None
            # 3) 重载 Qwen3.5 模型模块，恢复未被 patch 的原始函数
            _qwen35_mod = "transformers.models.qwen3_5.modeling_qwen3_5"
            if _qwen35_mod in sys.modules:
                importlib.reload(sys.modules[_qwen35_mod])
            # 4) 也重载 masking 相关模块（create_causal_mask 可能定义在此）
            for _mod_name in list(sys.modules.keys()):
                if "transformers" in _mod_name and "mask" in _mod_name:
                    try:
                        importlib.reload(sys.modules[_mod_name])
                    except Exception:
                        pass
            print("  [FIX] 已屏蔽 unsloth_zoo monkey-patch，恢复标准 HF 路径")

        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import LoraConfig, get_peft_model, TaskType

        tokenizer = AutoTokenizer.from_pretrained(
            model_path, trust_remote_code=True
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            tokenizer.pad_token_id = tokenizer.eos_token_id

        # 模型加载精度策略：
        #   bf16 GPU (Ampere+): fp32 加载 + bf16 AMP → 标准混合精度训练
        #   fp16 GPU (T4):      fp16 加载 + 关闭 AMP → LoRA 参数自带 fp32，无需 AMP
        #     （之前 fp16 权重 + fp16 AMP = 双重精度损失 → grad_norm=nan，
        #      关闭 AMP 后 LoRA 的 fp32 参数足够稳定）
        if use_qlora:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=train_dtype,
                bnb_4bit_use_double_quant=True,
            )
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                quantization_config=bnb_config,
                attn_implementation="sdpa",
                trust_remote_code=True,
            )
            print("  [QLoRA] 模型已 4bit 量化加载, SDPA attention")
            if use_multi_gpu:
                print(f"  [WARN] QLoRA + 多 GPU: bitsandbytes 量化模型仅在 GPU 0 上运行")
                print(f"         多 GPU 并行不生效，建议去掉 --qlora 以使用双 T4 DDP")
                use_multi_gpu = False
        else:
            # T4 用 fp16 加载（1GB），bf16 GPU 用 fp32 加载（2GB）+ AMP
            load_dtype = train_dtype if use_fp16 else torch.float32
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                dtype=load_dtype,
                attn_implementation="sdpa",
                trust_remote_code=True,
            )
            if use_fp16:
                print(f"  [LoRA] 模型已 fp16 加载 + SDPA attention（T4 模式: fp16 权重 + LoRA fp32 参数, 无 AMP）")
            elif supports_bf16():
                print(f"  [LoRA] 模型已 fp32 加载 + SDPA attention（bf16 GPU: fp32 权重 + bf16 AMP）")
            else:
                print(f"  [LoRA] 模型已 fp32 加载 + SDPA attention（T4 MoE 保护: fp32 权重, 无 AMP）")

        # 设备分配
        if use_multi_gpu:
            print(f"  设备: DDP 自动分配 ({gpu_count} GPUs)")
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(device)
            print(f"  设备: {device}")
        print(f"  模型参数量: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")

        # gradient checkpointing
        if gradient_checkpointing:
            model.gradient_checkpointing_enable()
            model.config.use_cache = False
            print("  [OK] gradient checkpointing 已启用")

        # ── 配置 LoRA（标准 PEFT）──
        print("\n" + "=" * 60)
        print("第 3 步：配置 LoRA")
        print("=" * 60)

        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=lora_rank,
            lora_alpha=lora_alpha,
            lora_dropout=0.05,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
            bias="none",
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

    # ── 加载数据集 ──
    print("\n" + "=" * 60)
    print("第 4 步：加载数据集")
    print("=" * 60)

    train_dataset = LightSFTDataset(dataset_path or _DATASET_PATH, tokenizer, max_len=max_len)
    print(f"  训练数据: {len(train_dataset)} 条")
    print(f"  max_len: {max_len}")

    # 统计类别分布
    categories = {}
    for item in train_dataset.data:
        cat = item.get("category", "未知")
        categories[cat] = categories.get(cat, 0) + 1
    print("  类别分布:")
    for cat, cnt in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {cnt}")

    # ── 训练参数 ──
    print("\n" + "=" * 60)
    print("第 5 步：训练（GPU）")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)
    checkpoint_dir = os.path.join(output_dir, "checkpoints")

    total_samples = len(train_dataset) * epochs
    total_steps = total_samples // (batch_size * grad_accum) + 1
    if use_multi_gpu:
        total_steps = total_steps // gpu_count  # DDP 每步处理 gpu_count 倍数据
    if max_steps > 0:
        total_steps = max_steps

    # GPU 速度估算
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        # 粗略估算：0.5B 模型 ~0.1秒/样本, 1.5B ~0.3秒/样本
        param_count = sum(p.numel() for p in model.parameters()) / 1e9
        sec_per_sample = max(0.05, param_count * 0.2)
        est_time = total_samples * sec_per_sample
        if use_multi_gpu:
            est_time = est_time / gpu_count  # 多 GPU 近似线性加速
            print(f"  GPU: {gpu_count}x {gpu_name} ({gpu_mem:.1f} GB each)")
            print(f"  [DDP] 数据并行，每 GPU 独立跑一份模型副本")
        else:
            print(f"  GPU: {gpu_name} ({gpu_mem:.1f} GB)")
        print(f"  预计总步数: ~{total_steps}")
        print(f"  预计时间: ~{est_time:.0f} 秒 ({est_time / 60:.1f} 分钟)")
    else:
        print(f"  预计总步数: ~{total_steps}")
        print(f"  [WARN] CPU 模式，预计 ~{total_samples * 7 / 3600:.1f} 小时")

    effective_batch = batch_size * grad_accum
    if use_multi_gpu:
        effective_batch *= gpu_count
        print(f"  batch_size: {batch_size} x grad_accum: {grad_accum} x GPUs: {gpu_count} = 等效 batch {effective_batch}")
    else:
        print(f"  batch_size: {batch_size} x grad_accum: {grad_accum} = 等效 batch {effective_batch}")
    print(f"  epochs: {epochs}, lr: {lr}, LoRA rank: {lora_rank}")
    # 显示精度模式
    if use_unsloth:
        print(f"  precision: unsloth-auto, QLoRA: {use_qlora}")
    elif use_fp16:
        print(f"  precision: fp16 权重 + fp32 LoRA (无 AMP), QLoRA: {use_qlora}")
    else:
        print(f"  precision: fp32 权重 + bf16 AMP, QLoRA: {use_qlora}")
    print()

    # 根据 GPU 能力选择训练策略：
    #   bf16 GPU (Ampere+): fp32 权重 + bf16 AMP → 标准混合精度
    #   fp16 GPU (T4):      fp16 权重 + 关闭 AMP → LoRA 参数 fp32, 不需 AMP
    #     （fp16 权重 + fp16 AMP = 双重精度损失 → grad_norm=nan）
    use_bf16 = torch.cuda.is_available() and supports_bf16()
    use_fp16_amp = False  # 默认关闭 AMP；T4 不用 AMP，bf16 GPU 用 bf16 AMP

    # ── 优化器选择 ──
    # 8-bit AdamW (bitsandbytes): 优化器状态用 8-bit 存储，省 ~75% 显存
    #   QLoRA / Unsloth / Qwen3.5 fp32 时启用（大模型省显存）
    #   小模型标准 LoRA 用 32-bit adamw_torch（精度优先）
    if use_qlora or use_unsloth or is_qwen35:
        optim_name = "adamw_8bit"
        print(f"  [OPTIM] adamw_8bit (8-bit AdamW, 省 ~75% 优化器显存)")
    else:
        optim_name = "adamw_torch"
        print(f"  [OPTIM] adamw_torch (32-bit AdamW)")

    training_args = TrainingArguments(
        output_dir=checkpoint_dir,
        num_train_epochs=epochs if max_steps <= 0 else 1,
        max_steps=max_steps if max_steps > 0 else -1,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        lr_scheduler_type="cosine",
        warmup_steps=max(1, int(total_steps * 0.05)),
        logging_steps=5,
        save_steps=save_steps,
        save_total_limit=3,
        bf16=use_bf16,          # Ampere+ 启用 bf16 AMP
        fp16=use_fp16_amp,      # T4 关闭 AMP（LoRA 参数已是 fp32）
        max_grad_norm=1.0,
        gradient_checkpointing=gradient_checkpointing,
        report_to="none",
        seed=42,
        dataloader_num_workers=0,
        remove_unused_columns=False,
        optim=optim_name,
        ddp_find_unused_parameters=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
    )

    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0

    print(f"\n训练完成！耗时 {elapsed:.0f} 秒 ({elapsed / 60:.1f} 分钟)")

    # ── 保存 ──
    final_dir = os.path.join(output_dir, "final")
    model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    print(f"\nLoRA 权重保存到: {final_dir}")

    # 保存训练信息
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    gpu_caps = get_gpu_capability()
    info = {
        "model_path": model_path,
        "dataset_path": _DATASET_PATH,
        "dataset_size": len(train_dataset),
        "epochs": epochs,
        "lora_rank": lora_rank,
        "lora_alpha": lora_alpha,
        "lr": lr,
        "max_len": max_len,
        "batch_size": batch_size,
        "grad_accum": grad_accum,
        "use_qlora": use_qlora,
        "use_unsloth": use_unsloth,
        "precision": "unsloth-auto" if use_unsloth else ("fp16-no-amp" if use_fp16 else "fp32-bf16-amp"),
        "gpu": gpu_name,
        "gpu_count": gpu_count,
        "ddp_enabled": use_multi_gpu,
        "kaggle_dual_t4": is_kaggle_dual_t4,
        "effective_batch_size": batch_size * grad_accum * (gpu_count if use_multi_gpu else 1),
        "gpu_compute_capability": f"{gpu_caps[0]}.{gpu_caps[1]}",
        "training_time_seconds": elapsed,
        "system_prompt": SYSTEM_PROMPT,
    }
    info_path = os.path.join(output_dir, "training_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f"训练信息保存到: {info_path}")

    return final_dir


# ═══════════════════════════════════════════════════════════════════
# 第 4 步：推理测试
# ═══════════════════════════════════════════════════════════════════

def test_inference(model_path: str, lora_path: str):
    """测试微调后的模型推理"""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    print("\n" + "=" * 60)
    print("推理测试")
    print("=" * 60)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # 推理精度也需适配 GPU 能力（T4 用 fp16，Ampere+ 用 bf16）
    if torch.cuda.is_available():
        dtype = torch.bfloat16 if supports_bf16() else torch.float16
    else:
        dtype = torch.float32

    tokenizer = AutoTokenizer.from_pretrained(
        model_path, trust_remote_code=True
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        model_path, dtype=dtype, trust_remote_code=True
    ).to(device)
    model = PeftModel.from_pretrained(base_model, lora_path).to(device)
    model.eval()

    test_cases = [
        ("def add(a, b):\n    return a + b", "加法段落"),
        ("for i in range(10):\n    print(i)", "循环打印"),
        ("def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)", "递归阶乘"),
        ("x = 10\ny = 20\nif x > y:\n    print('x大')\nelse:\n    print('y大')", "条件判断"),
        ("data = [3, 1, 4, 1, 5, 9, 2, 6]\ndata.sort()\nprint(data)", "列表排序"),
    ]

    for python_code, desc in test_cases:
        print(f"\n--- {desc} ---")
        print(f"Python: {python_code}")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"将以下 Python 代码翻译为光明 v3.2：\n\n{python_code}"},
        ]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(text, return_tensors="pt").to(device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.1,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
            )

        response = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )
        print(f"光明: {response}")


# ═══════════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="光明翻译器 — GPU LoRA 微调（需要 GPU 环境）"
    )
    parser.add_argument(
        "--preset",
        choices=list(MODEL_PRESETS.keys()),
        default=None,
        help="模型预设，自动配置训练参数（如 qwen3.5-2b）",
    )
    parser.add_argument(
        "--model-path", default=_DEFAULT_MODEL_PATH,
        help=f"预训练模型路径（默认 {_DEFAULT_MODEL_PATH}，--preset 会自动设置）",
    )
    parser.add_argument(
        "--output-dir", default=_DEFAULT_OUTPUT_DIR,
        help=f"输出目录（默认 {_DEFAULT_OUTPUT_DIR}，--preset 会自动设置）",
    )
    parser.add_argument("--epochs", type=int, default=3, help="训练轮数（默认 3）")
    parser.add_argument("--lora-rank", type=int, default=None, help="LoRA rank（默认 16，--preset 可覆盖）")
    parser.add_argument("--lora-alpha", type=int, default=None, help="LoRA alpha（默认 32，--preset 可覆盖）")
    parser.add_argument("--lr", type=float, default=None, help="学习率（默认 2e-4，--preset 可覆盖）")
    parser.add_argument("--max-len", type=int, default=None, help="最大序列长度（默认 8192，--preset 可覆盖；命令行优先）")
    parser.add_argument("--batch-size", type=int, default=None, help="batch size（默认 2，--preset 可覆盖；命令行优先）")
    parser.add_argument("--grad-accum", type=int, default=None, help="梯度累积步数（默认 8，--preset 可覆盖；命令行优先）")
    parser.add_argument("--save-steps", type=int, default=50, help="保存间隔（默认 50）")
    parser.add_argument(
        "--max-steps", type=int, default=-1,
        help="最大训练步数（-1 表示用 epochs，正数则覆盖 epochs）",
    )
    parser.add_argument(
        "--dataset", default=None,
        help="自定义数据集路径（默认 sft_dataset.jsonl）",
    )
    parser.add_argument("--qlora", action="store_true", help="使用 QLoRA 4bit 量化训练（省显存，所有模型可用）")
    parser.add_argument("--unsloth", action="store_true", help="使用 Unsloth 优化后端（省 30-50%% 显存 + 2x 加速，T4 推荐）")
    parser.add_argument("--no-gc", action="store_true", help="禁用 gradient checkpointing")
    parser.add_argument("--dry-run", action="store_true", help="只检查环境不训练")
    parser.add_argument("--test-infer", action="store_true", help="训练后测试推理")
    parser.add_argument("--no-gpu-required", action="store_true", help="允许在无 GPU 时回退到 CPU")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # ── 应用模型预设（命令行参数优先于预设值）──
    if args.preset:
        preset = MODEL_PRESETS[args.preset]
        print(f"[预设] {args.preset}: {preset['desc']}")

        # model_path / output_dir: 预设总是覆盖（用户极少手动指定）
        args.model_path = preset["model_path"]
        args.output_dir = preset["output_dir"]

        # 训练参数: 仅当用户未通过命令行显式指定时，才使用预设值
        # argparse default=None 表示用户未指定，非 None 表示用户显式传入了
        if args.max_len is None:
            args.max_len = preset["max_len"]
        if args.batch_size is None:
            args.batch_size = preset["batch_size"]
        if args.grad_accum is None:
            args.grad_accum = preset["grad_accum"]
        if args.lora_rank is None:
            args.lora_rank = preset["lora_rank"]
        if args.lora_alpha is None:
            args.lora_alpha = preset["lora_alpha"]
        if args.lr is None:
            args.lr = preset["lr"]

        print(f"  model_path={args.model_path}")
        print(f"  output_dir={args.output_dir}")
        print(f"  max_len={args.max_len}, batch_size={args.batch_size}, grad_accum={args.grad_accum}")
        print(f"  lora_rank={args.lora_rank}, lora_alpha={args.lora_alpha}, lr={args.lr}")
        print()

    # ── 无 preset 时回退到内置默认值 ──
    if args.max_len is None:
        args.max_len = 8192
    if args.batch_size is None:
        args.batch_size = 2
    if args.grad_accum is None:
        args.grad_accum = 8
    if args.lora_rank is None:
        args.lora_rank = 16
    if args.lora_alpha is None:
        args.lora_alpha = 32
    if args.lr is None:
        args.lr = 2e-4

    # ── T4 / 低显存 GPU 自动调参 ──
    # T4 (16GB) 策略：
    #   标准模式 (fp16 权重, 无 AMP): max_len=8192 ~3GB 权重 + 激活值, 可跑
    #   QLoRA 模式: max_len=8192 ~1GB 权重, 轻松跑
    #   Unsloth 模式: 自动优化, 不限制
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            major, minor = torch.cuda.get_device_capability(0)
            is_t4 = "T4" in gpu_name or "Tesla T4" in gpu_name

            if is_t4 or gpu_mem_gb < 10:
                # T4 或低显存 GPU：调整参数
                if not args.qlora and not args.unsloth:
                    # 标准模式: T4 用 fp16 权重（~1GB），max_len=8192 可跑
                    if is_t4:
                        t4_max_len_limit = 8192
                    else:
                        t4_max_len_limit = 1024  # 8GB 显卡保守
                    if args.max_len > t4_max_len_limit:
                        print(f"[自适应] GPU {'T4' if is_t4 else f'{gpu_mem_gb:.0f}GB'}, max_len {args.max_len}→{t4_max_len_limit}")
                        args.max_len = t4_max_len_limit
                    if not is_t4 and args.batch_size > 1:
                        print(f"[自适应] batch_size {args.batch_size}→1（低显存）")
                        args.batch_size = 1

                if is_t4:
                    print(f"[T4 检测] Tesla T4 ({gpu_mem_gb:.1f}GB, SM {major}.{minor})")
                    if args.unsloth:
                        print(f"  [Unsloth] 自动处理精度和显存优化")
                    else:
                        print(f"  fp16 权重 + fp32 LoRA 参数 (无 AMP, 避免 grad_norm=nan)")
                    print(f"  当前配置: max_len={args.max_len}, batch_size={args.batch_size}, QLoRA={args.qlora}")
    except ImportError:
        pass

    # ── QLoRA 检查与警告 ──
    if args.qlora:
        # 检测是否为 Qwen3.5（官方不建议 QLoRA，但显存不足时可用）
        model_path_lower = args.model_path.lower().replace(os.sep, "/")
        is_qwen35 = "qwen3.5" in model_path_lower or "qwen3_5" in model_path_lower
        if is_qwen35:
            print("[WARN] Qwen3.5 系列官方不建议使用 QLoRA（量化差异可能高于正常水平）")
            print("       但显存不足时仍可使用，如效果不佳请换用 bf16 LoRA 模式")
            print("       继续使用 QLoRA 训练...\n")

    # 环境检查
    if not check_environment(require_gpu=not args.no_gpu_required):
        print("\n环境检查未通过，请先安装缺失的依赖。")
        sys.exit(1)

    # 检查自定义数据集
    dataset_path = args.dataset
    if dataset_path:
        if not os.path.isabs(dataset_path):
            dataset_path = os.path.join(_SCRIPT_DIR, dataset_path)
        if not os.path.exists(dataset_path):
            print(f"\n[ERROR] 数据集不存在: {dataset_path}")
            sys.exit(1)
        print(f"\n使用自定义数据集: {dataset_path}")

    if args.dry_run:
        print("\n[Dry-run] 环境检查通过，未执行训练。")
        return

    # 检查模型路径
    if not os.path.exists(args.model_path):
        print(f"\n[ERROR] 模型路径不存在: {args.model_path}")
        print("请先运行: python download_model.py")
        sys.exit(1)

    # 训练
    final_dir = train(
        model_path=args.model_path,
        output_dir=args.output_dir,
        epochs=args.epochs,
        lora_rank=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lr=args.lr,
        max_len=args.max_len,
        batch_size=args.batch_size,
        grad_accum=args.grad_accum,
        save_steps=args.save_steps,
        dataset_path=args.dataset,
        max_steps=args.max_steps,
        use_qlora=args.qlora,
        gradient_checkpointing=not args.no_gc,
        use_unsloth=args.unsloth,
    )

    # 推理测试
    if args.test_infer:
        test_inference(args.model_path, final_dir)

    print("\n" + "=" * 60)
    print("全部完成！")
    print("=" * 60)
    print(f"\n下一步：")
    print(f"  1. 合并 LoRA:    python merge_and_convert.py --merge-only")
    print(f"  2. 转 GGUF:      python merge_and_convert.py --convert-gguf")
    print(f"  3. 本地推理:     python local_infer.py --fine-tuned")
    print(f"  4. 集成到 CLI:   light ai local \"写一个冒泡排序\"")


if __name__ == "__main__":
    main()
