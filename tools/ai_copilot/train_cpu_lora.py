#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明翻译器 — CPU LoRA 微调脚本（无GPU环境专用）

针对无GPU环境优化，使用 transformers + peft 在 CPU 上对
Qwen2.5-0.5B-Instruct 进行 LoRA 微调，使其学会将 Python 代码
翻译为光明 v3.2 代码。

完整流程：
  1. 环境检查（PyTorch CPU / transformers / peft）
  2. 加载预训练模型和 tokenizer
  3. 加载 SFT 数据集（881 条 Python→光明 对照）
  4. 配置 LoRA（rank=8, 只训练 q_proj/v_proj）
  5. CPU 训练（batch_size=1, gradient_accumulation=16, epochs=3）
  6. 保存 LoRA 权重
  7. （可选）测试推理效果

显存/内存需求：
  - 模型权重（float32）: ~2 GB
  - LoRA 参数: ~10 MB
  - 数据 + 优化器状态: ~1 GB
  - 总计: ~3-4 GB（11GB 内存绰绰有余）

预计训练时间：
  - 881 条 × 3 轮 = 2643 步
  - CPU ~3-5 秒/步
  - 总计: 2-4 小时（可过夜运行）

用法：
    # 标准训练（默认参数）
    python train_cpu_lora.py

    # 自定义参数
    python train_cpu_lora.py --epochs 5 --lora-rank 16 --lr 3e-4

    # 指定模型路径（如果不在默认位置）
    python train_cpu_lora.py --model-path ./model_cache/qwen2.5-0.5b

    # 只检查环境不训练
    python train_cpu_lora.py --dry-run

    # 训练完测试推理
    python train_cpu_lora.py --test-infer

前置条件：
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    pip install transformers peft datasets accelerate
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ── 路径常量 ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATASET_PATH = os.path.join(_SCRIPT_DIR, "sft_dataset.jsonl")
_DEFAULT_MODEL_PATH = os.path.join(_SCRIPT_DIR, "model_cache", "qwen2.5-0.5b")
_DEFAULT_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "output", "qwen2.5_0.5b_light_cpu")

# ── 系统提示词（微调后模型的 system prompt）──
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
# 第 1 步：环境检查
# ═══════════════════════════════════════════════════════════════════

def check_environment() -> bool:
    """检查运行环境"""
    print("=" * 60)
    print("第 1 步：环境检查")
    print("=" * 60)

    ok = True

    # PyTorch
    try:
        import torch
        print(f"  [OK] PyTorch {torch.__version__}")
        if torch.cuda.is_available():
            print(f"       GPU: {torch.cuda.get_device_name(0)}")
        else:
            print(f"       CPU 模式（无 GPU，训练会慢但可行）")
    except ImportError:
        print("  [FAIL] PyTorch 未安装")
        print("         pip install torch --index-url https://download.pytorch.org/whl/cpu")
        ok = False

    # transformers
    try:
        import transformers
        print(f"  [OK] transformers {transformers.__version__}")
    except ImportError:
        print("  [FAIL] transformers 未安装")
        print("         pip install transformers")
        ok = False

    # peft
    try:
        import peft
        print(f"  [OK] peft {peft.__version__}")
    except ImportError:
        print("  [FAIL] peft 未安装")
        print("         pip install peft")
        ok = False

    # accelerate
    try:
        import accelerate
        print(f"  [OK] accelerate {accelerate.__version__}")
    except ImportError:
        print("  [WARN] accelerate 未安装（可选但推荐）")
        print("         pip install accelerate")

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
    """光明 SFT 数据集

    将 JSONL 格式的 Python→光明 对照数据转换为模型可训练的格式。
    使用 chat template 构造完整的对话，然后对 assistant 回复部分
    计算 loss。
    """

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

        # 预计算 prompt 部分（不计算 loss 的部分）的长度
        # 方法：对每个样本分别构造 prompt 和 full text，
        # labels 中 prompt 部分设为 -100（ignore_index）

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
            add_generation_prompt=True,  # 加上 assistant 开头标记
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
    lora_rank: int = 8,
    lora_alpha: int = 16,
    lr: float = 2e-4,
    max_len: int = 512,
    batch_size: int = 1,
    grad_accum: int = 16,
    warmup_ratio: float = 0.05,
    save_steps: int = 100,
    dataset_path: str = None,
    max_steps: int = -1,
):
    """执行 LoRA 微调"""
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
    )
    from peft import LoraConfig, get_peft_model, TaskType

    print("\n" + "=" * 60)
    print("第 2 步：加载模型")
    print("=" * 60)
    print(f"  模型路径: {model_path}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_path, trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        dtype=torch.float32,  # CPU 必须用 float32
        trust_remote_code=True,
    )
    print(f"  模型参数量: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")

    # ── 配置 LoRA ──
    print("\n" + "=" * 60)
    print("第 3 步：配置 LoRA")
    print("=" * 60)

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],  # CPU 友好：只训练 q/v
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
    print("第 5 步：训练")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)
    checkpoint_dir = os.path.join(output_dir, "checkpoints")

    total_steps = (len(train_dataset) // (batch_size * grad_accum) + 1) * epochs
    print(f"  预计总步数: ~{total_steps}")
    print(f"  预计时间: ~{total_steps * 4:.0f} 秒 ({total_steps * 4 / 3600:.1f} 小时)")
    print(f"  batch_size: {batch_size} × grad_accum: {grad_accum} = 等效 batch {batch_size * grad_accum}")
    print(f"  epochs: {epochs}, lr: {lr}, LoRA rank: {lora_rank}")
    print()
    print("  [提示] 训练可过夜运行，日志每 10 步输出一次。")
    print("  按 Ctrl+C 可中断，checkpoint 会自动保存。")
    print()

    training_args = TrainingArguments(
        output_dir=checkpoint_dir,
        num_train_epochs=epochs,
        max_steps=max_steps,  # -1 表示不限制，正数则覆盖 epochs
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        lr_scheduler_type="cosine",
        warmup_steps=int(total_steps * warmup_ratio),
        logging_steps=1,  # 2步训练时每步都输出
        save_steps=save_steps,
        save_total_limit=2,
        bf16=False,  # CPU 不支持 bf16
        fp16=False,  # CPU 不支持 fp16
        gradient_checkpointing=False,
        report_to="none",
        seed=42,
        dataloader_num_workers=0,  # Windows 上用 0 最稳定
        remove_unused_columns=False,
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

    print(f"\n训练完成！耗时 {elapsed:.0f} 秒 ({elapsed / 3600:.1f} 小时)")

    # ── 保存 ──
    final_dir = os.path.join(output_dir, "final")
    model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    print(f"\nLoRA 权重保存到: {final_dir}")

    # 保存训练信息
    info = {
        "model_path": model_path,
        "dataset_path": _DATASET_PATH,
        "dataset_size": len(train_dataset),
        "epochs": epochs,
        "lora_rank": lora_rank,
        "lora_alpha": lora_alpha,
        "lr": lr,
        "max_len": max_len,
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

    tokenizer = AutoTokenizer.from_pretrained(
        model_path, trust_remote_code=True
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        model_path, dtype=torch.float32, trust_remote_code=True
    )
    model = PeftModel.from_pretrained(base_model, lora_path)
    model.eval()

    test_cases = [
        ("def add(a, b):\n    return a + b", "加法段落"),
        ("for i in range(10):\n    print(i)", "循环打印"),
        ("def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)", "递归阶乘"),
        ("x = 10\ny = 20\nif x > y:\n    print('x大')\nelse:\n    print('y大')", "条件判断"),
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
        inputs = tokenizer(text, return_tensors="pt")

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
        description="光明翻译器 — CPU LoRA 微调（无GPU环境专用）"
    )
    parser.add_argument(
        "--model-path", default=_DEFAULT_MODEL_PATH,
        help=f"预训练模型路径（默认 {_DEFAULT_MODEL_PATH}）",
    )
    parser.add_argument(
        "--output-dir", default=_DEFAULT_OUTPUT_DIR,
        help=f"输出目录（默认 {_DEFAULT_OUTPUT_DIR}）",
    )
    parser.add_argument("--epochs", type=int, default=3, help="训练轮数（默认 3）")
    parser.add_argument("--lora-rank", type=int, default=8, help="LoRA rank（默认 8）")
    parser.add_argument("--lora-alpha", type=int, default=16, help="LoRA alpha（默认 16）")
    parser.add_argument("--lr", type=float, default=2e-4, help="学习率（默认 2e-4）")
    parser.add_argument("--max-len", type=int, default=512, help="最大序列长度（默认 512）")
    parser.add_argument("--batch-size", type=int, default=1, help="batch size（默认 1）")
    parser.add_argument("--grad-accum", type=int, default=16, help="梯度累积步数（默认 16）")
    parser.add_argument("--save-steps", type=int, default=100, help="保存间隔（默认 100）")
    parser.add_argument(
        "--max-steps", type=int, default=-1,
        help="最大训练步数（-1 表示用 epochs，正数则覆盖 epochs，用于快速验证）",
    )
    parser.add_argument(
        "--dataset", default=None,
        help="自定义数据集路径（默认 sft_dataset.jsonl）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只检查环境不训练")
    parser.add_argument("--test-infer", action="store_true", help="训练后测试推理")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # 环境检查
    if not check_environment():
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
