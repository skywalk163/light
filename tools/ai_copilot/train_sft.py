#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明翻译器 — ERNIE-4.5-0.3B 一键 LoRA 微调脚本

将 sft_dataset.jsonl 中的 Python→光明 对照数据用于微调
ERNIE-4.5-0.3B，使其学会将 Python 代码翻译为光明 v3.2 代码。

完整流程：
  1. 环境检查（PaddlePaddle / PaddleNLP / ERNIEKit）
  2. 下载预训练模型（从 AI Studio）
  3. 自动生成 YAML 训练配置
  4. 执行 LoRA SFT 训练
  5. 合并 LoRA 权重并导出
  6. （可选）转换为 GGUF 格式用于 llama.cpp 部署

用法：
    # 最简单：一键训练（使用默认参数）
    python train_sft.py

    # 自定义参数
    python train_sft.py --epochs 5 --lora-rank 32 --lr 2e-4

    # 只生成配置文件不训练
    python train_sft.py --dry-run

    # 转换已有模型为 GGUF
    python train_sft.py --convert-gguf --model-path ./output/light_translator

前置条件：
    pip install --upgrade --pre paddlenlp
    pip install --upgrade aistudio-sdk
    # GPU 版本需安装 paddlepaddle-gpu，CPU 版本用 paddlepaddle

文档：tools/ai_copilot/README_SFT.md
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# ── 路径常量 ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
_DATASET_PATH = os.path.join(_SCRIPT_DIR, 'sft_dataset.jsonl')
_DEFAULT_MODEL = 'paddlepaddle/ernie-4.5-0.3b'
_DEFAULT_OUTPUT = os.path.join(_SCRIPT_DIR, 'output', 'light_translator')


# ═══════════════════════════════════════════════════════════════════
# 第 1 步：环境检查
# ═══════════════════════════════════════════════════════════════════

def check_environment() -> bool:
    """检查运行环境是否满足要求"""
    print("=" * 60)
    print("第 1 步：环境检查")
    print("=" * 60)

    ok = True

    # 检查 PaddlePaddle
    try:
        import paddle
        print(f"  ✓ PaddlePaddle {paddle.__version__}")
        if paddle.is_compiled_with_cuda():
            print(f"    GPU 可用: {paddle.device.get_device()}")
        else:
            print("    ⚠ 仅 CPU 模式（训练会很慢，建议用 GPU）")
    except ImportError:
        print("  ✗ PaddlePaddle 未安装")
        print("    安装命令: pip install paddlepaddle-gpu  (GPU)")
        print("    或:       pip install paddlepaddle       (CPU)")
        ok = False

    # 检查 PaddleNLP / ERNIEKit
    try:
        import paddlenlp
        print(f"  ✓ PaddleNLP {paddlenlp.__version__}")
    except ImportError:
        print("  ✗ PaddleNLP 未安装")
        print("    安装命令: pip install --upgrade --pre paddlenlp")
        ok = False

    # 检查 aistudio-sdk（模型下载用）
    try:
        import aistudio_sdk
        print(f"  ✓ aistudio-sdk 已安装")
    except ImportError:
        print("  ⚠ aistudio-sdk 未安装（模型下载需要）")
        print("    安装命令: pip install --upgrade aistudio-sdk")

    # 检查训练数据
    if os.path.isfile(_DATASET_PATH):
        with open(_DATASET_PATH, 'r', encoding='utf-8') as f:
            count = sum(1 for _ in f)
        print(f"  ✓ 训练数据: {_DATASET_PATH} ({count} 条)")
    else:
        print(f"  ✗ 训练数据不存在: {_DATASET_PATH}")
        print("    请先运行: python build_sft_dataset.py")
        ok = False

    print()
    return ok


# ═══════════════════════════════════════════════════════════════════
# 第 2 步：下载模型
# ═══════════════════════════════════════════════════════════════════

def download_model(model_name: str, save_dir: str) -> str:
    """下载预训练模型

    Args:
        model_name: 模型名称（如 paddlepaddle/ernie-4.5-0.3b）
        save_dir: 保存目录

    Returns:
        模型本地路径
    """
    model_path = os.path.join(save_dir, model_name.replace('/', '_'))

    if os.path.isdir(model_path) and os.path.isfile(os.path.join(model_path, 'config.json')):
        print(f"  模型已存在: {model_path}")
        return model_path

    print(f"  下载模型: {model_name}")
    print(f"  保存到: {model_path}")

    os.makedirs(model_path, exist_ok=True)

    # 尝试用 aistudio-sdk 下载
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'aistudio_sdk', 'download',
             '--model', model_name, '--target', model_path],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=600,
        )
        if result.returncode == 0:
            print("  ✓ 下载完成")
            return model_path
        else:
            print(f"  ⚠ aistudio-sdk 下载失败: {result.stderr[:200]}")
    except Exception as e:
        print(f"  ⚠ aistudio-sdk 下载异常: {e}")

    # 备选：用 huggingface_hub 下载
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=f"baidu/{model_name.split('/')[-1]}",
            local_dir=model_path,
        )
        print("  ✓ 通过 HuggingFace 下载完成")
        return model_path
    except ImportError:
        pass
    except Exception as e:
        print(f"  ⚠ HuggingFace 下载失败: {e}")

    print("  手动下载方式：")
    print(f"    aistudio download --model {model_name}")
    print(f"    或从 https://huggingface.co/baidu 下载")
    print(f"    解压到: {model_path}")
    return model_path


# ═══════════════════════════════════════════════════════════════════
# 第 3 步：生成训练配置
# ═══════════════════════════════════════════════════════════════════

def generate_yaml_config(
    model_path: str,
    dataset_path: str,
    output_dir: str,
    epochs: int = 3,
    batch_size: int = 4,
    lr: float = 1e-4,
    lora_rank: int = 16,
    max_seq_len: int = 1024,
) -> str:
    """生成 ERNIEKit 训练 YAML 配置文件

    Args:
        model_path: 预训练模型本地路径
        dataset_path: 训练数据 JSONL 路径
        output_dir: 输出目录
        epochs: 训练轮数
        batch_size: 批大小
        lr: 学习率
        lora_rank: LoRA 秩
        max_seq_len: 最大序列长度

    Returns:
        YAML 配置文件路径
    """
    yaml_path = os.path.join(output_dir, 'train_config.yaml')
    os.makedirs(output_dir, exist_ok=True)

    yaml_content = f"""# 光明翻译器 — ERNIE-4.5-0.3B LoRA SFT 训练配置
# 由 train_sft.py 自动生成

model:
  model_name_or_path: "{model_path}"
  dtype: "bfloat16"  # CPU 环境请改为 "float32"

method:
  name: "lora"
  lora_rank: {lora_rank}
  lora_alpha: {lora_rank * 2}
  lora_dropout: 0.05
  target_modules: ["q_proj", "v_proj", "k_proj", "o_proj"]

data:
  train_datasets:
    - name: "light_sft"
      data_source: "{dataset_path}"
      format: "jsonl"
      columns:
        prompt: "instruction"
        query: "input"
        response: "output"

training:
  output_dir: "{output_dir}/checkpoints"
  per_device_train_batch_size: {batch_size}
  gradient_accumulation_steps: 4
  num_train_epochs: {epochs}
  learning_rate: {lr}
  warmup_ratio: 0.05
  logging_steps: 10
  save_steps: 100
  save_total_limit: 3
  max_seq_length: {max_seq_len}
  bf16: true  # CPU 环境请改为 false
  fp16: false
  gradient_checkpointing: true
  seed: 42

eval:
  eval_strategy: "no"
"""

    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    print(f"  配置文件: {yaml_path}")
    return yaml_path


# ═══════════════════════════════════════════════════════════════════
# 第 4 步：执行训练
# ═══════════════════════════════════════════════════════════════════

def run_training(yaml_path: str) -> bool:
    """执行 ERNIEKit 训练

    Args:
        yaml_path: 训练配置 YAML 路径

    Returns:
        是否训练成功
    """
    print()
    print("=" * 60)
    print("第 4 步：执行 LoRA SFT 训练")
    print("=" * 60)

    # 尝试 erniekit CLI
    try:
        result = subprocess.run(
            ['erniekit', 'train', yaml_path],
            cwd=_SCRIPT_DIR,
        )
        if result.returncode == 0:
            print("  ✓ 训练完成")
            return True
    except FileNotFoundError:
        pass

    # 备选：python -m paddlenlp
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'paddlenlp.cli', 'train', yaml_path],
            cwd=_SCRIPT_DIR,
        )
        if result.returncode == 0:
            print("  ✓ 训练完成")
            return True
    except Exception:
        pass

    # 备选：直接 Python 调用
    print("  尝试直接调用 PaddleNLP 训练 API...")
    try:
        from paddlenlp.trainer import PdArgumentParser, TrainingArguments
        print("  ⚠ 自动训练未成功，请手动执行：")
        print(f"    erniekit train {yaml_path}")
        return False
    except ImportError:
        print("  ✗ PaddleNLP 未安装或版本不支持")
        return False


# ═══════════════════════════════════════════════════════════════════
# 第 5 步：合并 LoRA 权重
# ═══════════════════════════════════════════════════════════════════

def merge_lora(model_path: str, checkpoint_dir: str, output_dir: str) -> bool:
    """合并 LoRA 权重到基础模型

    Args:
        model_path: 基础模型路径
        checkpoint_dir: LoRA checkpoint 路径
        output_dir: 合并后模型输出路径

    Returns:
        是否合并成功
    """
    print()
    print("=" * 60)
    print("第 5 步：合并 LoRA 权重")
    print("=" * 60)

    merge_output = os.path.join(output_dir, 'merged')

    try:
        result = subprocess.run(
            ['erniekit', 'merge', '--model', model_path,
             '--lora', checkpoint_dir, '--output', merge_output],
        )
        if result.returncode == 0:
            print(f"  ✓ 合并完成: {merge_output}")
            return True
    except FileNotFoundError:
        pass

    # 备选：Python API
    print("  合并命令：")
    print(f"    erniekit merge --model {model_path} --lora {checkpoint_dir} --output {merge_output}")
    return False


# ═══════════════════════════════════════════════════════════════════
# 第 6 步：GGUF 转换（可选）
# ═══════════════════════════════════════════════════════════════════

def convert_to_gguf(model_path: str, output_dir: str) -> bool:
    """将合并后的模型转换为 GGUF 格式

    ERNIE-4.5-0.3B 格式特殊，需要自定义写入器。
    参考: https://aistudio.baidu.com/projectdetail/9749867

    Args:
        model_path: 合并后的模型路径
        output_dir: GGUF 输出目录

    Returns:
        是否转换成功
    """
    print()
    print("=" * 60)
    print("第 6 步：GGUF 格式转换（用于 llama.cpp 部署）")
    print("=" * 60)

    gguf_output = os.path.join(output_dir, 'light_translator.gguf')

    # 检查是否安装了转换工具
    try:
        from llama_cpp import Llama
        print("  ⚠ ERNIE-4.5-0.3B 的 GGUF 转换需要自定义写入器")
        print("  请参考: https://aistudio.baidu.com/projectdetail/9749867")
    except ImportError:
        pass

    print()
    print("  GGUF 转换步骤（手动）：")
    print("  1. 安装 llama.cpp: pip install llama-cpp-python")
    print("  2. 参考 AI Studio 教程中的自定义 GGUF 写入器")
    print(f"  3. 将 {model_path} 转换为 {gguf_output}")
    print("  4. 验证: llama-cli -m light_translator.gguf -p 'def add(a,b): return a+b'")
    return False


# ═══════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='光明翻译器 — ERNIE-4.5-0.3B 一键 LoRA 微调',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python train_sft.py                           # 一键训练（默认参数）
  python train_sft.py --epochs 5 --lora-rank 32 # 更多轮次 + 更高秩
  python train_sft.py --dry-run                 # 只生成配置不训练
  python train_sft.py --skip-download            # 跳过模型下载
  python train_sft.py --convert-gguf             # 只做 GGUF 转换

完整文档: tools/ai_copilot/README_SFT.md
        """
    )

    parser.add_argument('--model', default=_DEFAULT_MODEL,
                        help='预训练模型名称（默认: paddlepaddle/ernie-4.5-0.3b）')
    parser.add_argument('--output', default=_DEFAULT_OUTPUT,
                        help='输出目录（默认: tools/ai_copilot/output/light_translator）')
    parser.add_argument('--dataset', default=_DATASET_PATH,
                        help='训练数据 JSONL 路径（默认: tools/ai_copilot/sft_dataset.jsonl）')
    parser.add_argument('--epochs', type=int, default=3,
                        help='训练轮数（默认: 3）')
    parser.add_argument('--batch-size', type=int, default=4,
                        help='批大小（默认: 4）')
    parser.add_argument('--lr', type=float, default=1e-4,
                        help='学习率（默认: 1e-4）')
    parser.add_argument('--lora-rank', type=int, default=16,
                        help='LoRA 秩（默认: 16，越大效果越好但显存占用更多）')
    parser.add_argument('--max-seq-len', type=int, default=1024,
                        help='最大序列长度（默认: 1024）')
    parser.add_argument('--dry-run', action='store_true',
                        help='只生成配置文件，不执行训练')
    parser.add_argument('--skip-download', action='store_true',
                        help='跳过模型下载（假设模型已存在）')
    parser.add_argument('--convert-gguf', action='store_true',
                        help='只执行 GGUF 转换')
    parser.add_argument('--skip-check', action='store_true',
                        help='跳过环境检查')

    args = parser.parse_args()

    # ── GGUF 转换模式 ──
    if args.convert_gguf:
        convert_to_gguf(args.output, args.output)
        return

    # ── 环境检查 ──
    if not args.skip_check:
        if not check_environment():
            print("环境检查未通过，请安装缺失的依赖后重试。")
            print("安装指南: tools/ai_copilot/README_SFT.md")
            sys.exit(1)

    # ── 下载模型 ──
    print("=" * 60)
    print("第 2 步：下载预训练模型")
    print("=" * 60)

    if args.skip_download:
        model_path = args.model
        print(f"  跳过下载，使用路径: {model_path}")
    else:
        model_cache = os.path.join(_SCRIPT_DIR, 'model_cache')
        model_path = download_model(args.model, model_cache)

    # ── 生成训练配置 ──
    print()
    print("=" * 60)
    print("第 3 步：生成训练配置")
    print("=" * 60)

    yaml_path = generate_yaml_config(
        model_path=model_path,
        dataset_path=args.dataset,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        lora_rank=args.lora_rank,
        max_seq_len=args.max_seq_len,
    )

    if args.dry_run:
        print()
        print("Dry run 模式，配置已生成，不执行训练。")
        print(f"手动训练命令: erniekit train {yaml_path}")
        return

    # ── 执行训练 ──
    success = run_training(yaml_path)

    if not success:
        print()
        print("自动训练未成功。请手动执行：")
        print(f"  erniekit train {yaml_path}")
        print()
        print("或查看文档: tools/ai_copilot/README_SFT.md")
        sys.exit(1)

    # ── 合并 LoRA ──
    checkpoint_dir = os.path.join(args.output, 'checkpoints')
    merge_lora(model_path, checkpoint_dir, args.output)

    # ── GGUF 转换提示 ──
    merged_path = os.path.join(args.output, 'merged')
    print()
    print("=" * 60)
    print("训练完成！")
    print("=" * 60)
    print(f"  LoRA checkpoints: {checkpoint_dir}")
    print(f"  合并后模型: {merged_path}")
    print()
    print("下一步：")
    print(f"  1. 测试推理: erniekit server {args.output}/run_chat.yaml")
    print(f"  2. 转换 GGUF: python train_sft.py --convert-gguf --model-path {merged_path}")
    print(f"  3. 集成到光明管线: 将微调后的模型嵌入 light ai generate 流程")


if __name__ == '__main__':
    main()
