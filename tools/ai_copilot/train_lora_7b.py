#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明翻译器 — 多模型 LoRA/QLoRA 一键微调脚本

使用 LLaMA-Factory 框架对多种模型进行 LoRA/QLoRA 微调，
使其学会将 Python 代码翻译为光明 v3.2 代码。

支持模型（通过 --model-preset 选择）：
  qwen3-8b   — Qwen3-8B-Instruct（7-8B 级中文代码最强，生产用）
  qwen3.5-2b — Qwen3.5-2B-Instruct（2B 级轻量模型，开发调试首选）

为什么有 Qwen3.5-2B？
  - 仅 20 亿参数，LoRA BF16 显存 ~5GB，QLoRA ~3GB
  - 任何消费级显卡都能跑，训练速度极快（~10 分钟）
  - 适合开发阶段快速迭代、验证 prompt/数据质量
  - 新架构（门控 DeltaNet + MoE），2B 级性能领先

完整流程：
  1. 环境检查（PyTorch / CUDA / LLaMA-Factory）
  2. 下载预训练模型
  3. 注册光明数据集到 LLaMA-Factory
  4. 自动生成 YAML 训练配置
  5. 执行 LoRA/QLoRA SFT 训练
  6. 合并 LoRA 权重并导出
  7. （可选）测试推理效果

显存需求：
  Qwen3-8B:
    - LoRA BF16:  ~22 GB（RTX 3090/4090/A100）
    - QLoRA 4bit: ~8 GB（RTX 4060）
  Qwen3.5-2B:
    - LoRA BF16:  ~5 GB（GTX 1660 即可）
    - QLoRA 4bit: ~3 GB（几乎任何 GPU）

用法：
    # 开发调试首选：2B 模型，飞快
    python train_lora_7b.py --model-preset qwen3.5-2b

    # 生产部署：8B 模型，效果最好
    python train_lora_7b.py --model-preset qwen3-8b

    # QLoRA 4bit 量化训练（显存更省）
    python train_lora_7b.py --model-preset qwen3.5-2b --qlora

    # 自定义参数
    python train_lora_7b.py --model-preset qwen3-8b --epochs 5 --lora-rank 32

    # 只生成配置文件不训练
    python train_lora_7b.py --model-preset qwen3.5-2b --dry-run

    # 训练完测试推理
    python train_lora_7b.py --model-preset qwen3.5-2b --test-infer

前置条件：
    # 1. 安装 LLaMA-Factory（推荐 conda 环境）
    git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
    cd LLaMA-Factory
    pip install -e ".[torch,metrics]"

    # 2. 或者直接 pip 安装
    pip install llamafactory

    # 3. 如需 QLoRA 量化训练
    pip install bitsandbytes auto-gptq optimum

文档：tools/ai_copilot/README_LoRA7B.md
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ── 路径常量 ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
_DATASET_PATH = os.path.join(_SCRIPT_DIR, 'sft_dataset.jsonl')

# LLaMA-Factory 数据集注册文件路径
_LF_DATASET_INFO = None  # 运行时检测

# ═══════════════════════════════════════════════════════════════════
# 模型预设
# ═══════════════════════════════════════════════════════════════════
# 每个预设包含：模型名称、默认输出目录、LLaMA-Factory template、
# LoRA target modules、推荐参数（batch_size / lora_rank / 显存估算）

MODEL_PRESETS = {
    'qwen3-8b': {
        'name': 'Qwen3-8B-Instruct',
        'model_id': 'Qwen/Qwen3-8B-Instruct',
        'output_dir': os.path.join(_SCRIPT_DIR, 'output', 'qwen3_8b_light'),
        'template': 'qwen3',
        'lora_target': 'q_proj,v_proj,k_proj,o_proj,gate_proj,up_proj,down_proj',
        'description': '7-8B 级中文代码生成最强模型（HumanEval 76.0），生产部署首选',
        'params_b': 8,
        'vram_lora': '~22 GB',
        'vram_qlora': '~8 GB',
        'default_batch_size': 2,
        'default_lora_rank': 16,
        'default_lr': 1e-4,
        'default_grad_accum': 8,
    },
    'qwen3.5-2b': {
        'name': 'Qwen3.5-2B-Instruct',
        'model_id': 'Qwen/Qwen3.5-2B-Instruct',
        'output_dir': os.path.join(_SCRIPT_DIR, 'output', 'qwen3.5_2b_light'),
        'template': 'qwen3',
        'lora_target': 'q_proj,v_proj,k_proj,o_proj,gate_proj,up_proj,down_proj',
        'description': '2B 级轻量模型（门控 DeltaNet + MoE），开发调试首选，飞快',
        'params_b': 2,
        'vram_lora': '~5 GB',
        'vram_qlora': '~3 GB',
        'default_batch_size': 4,
        'default_lora_rank': 16,
        'default_lr': 2e-4,
        'default_grad_accum': 4,
    },
}

_DEFAULT_PRESET = 'qwen3-8b'


# ═══════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════

def _run_cmd(cmd, **kwargs):
    """执行命令并实时输出"""
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kwargs)
    return result


def _find_llamafactory_dir():
    """查找 LLaMA-Factory 安装路径"""
    # 1. 环境变量
    lf_dir = os.environ.get('LLAMAFACTORY_HOME', '')
    if lf_dir and os.path.isdir(lf_dir):
        return lf_dir

    # 2. pip show
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', 'llamafactory'],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith('Location:'):
                    loc = line.split(':', 1)[1].strip()
                    candidate = os.path.join(loc, 'llamafactory')
                    if os.path.isdir(candidate):
                        return os.path.dirname(candidate)
    except Exception:
        pass

    # 3. 常见位置
    for base in [os.getcwd(), os.path.expanduser('~')]:
        candidate = os.path.join(base, 'LLaMA-Factory')
        if os.path.isdir(candidate):
            return candidate

    return None


def _convert_to_sharegpt(input_path: str, output_path: str) -> int:
    """将 Alpaca 格式 JSONL 转换为 ShareGPT 格式

    LLaMA-Factory 推荐使用 ShareGPT 格式（多轮对话）。

    Alpaca 格式: {"instruction": "...", "input": "...", "output": "...", "category": "..."}
    ShareGPT 格式: {"conversations": [{"from": "human", "value": "..."}, {"from": "gpt", "value": "..."}]}

    Returns:
        转换后的样本数
    """
    count = 0
    with open(input_path, 'r', encoding='utf-8') as fin, \
         open(output_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)

            # 构造 system + user + assistant 三轮对话
            system_msg = (
                "你是光明（LightLang）编程语言 v3.2 的翻译专家。"
                "光明是一种中文编程语言，使用中文关键字。"
                "你的任务是将 Python 代码翻译为光明 v3.2 代码。"
                "注意暗坑：长度()不可用用len()、列表索引赋值用方括号语法、变量名不能与内建函数同名、类系统需LLVM后端。"
            )
            instruction = item.get('instruction', '将Python代码转为光明代码：')
            code_input = item.get('input', '')
            output = item.get('output', '')

            user_msg = f"{instruction}\n\nPython代码：\n{code_input}" if code_input else instruction

            conv = {
                "conversations": [
                    {"from": "system", "value": system_msg},
                    {"from": "human", "value": user_msg},
                    {"from": "gpt", "value": output},
                ]
            }
            fout.write(json.dumps(conv, ensure_ascii=False) + '\n')
            count += 1

    return count


# ═══════════════════════════════════════════════════════════════════
# 第 1 步：环境检查
# ═══════════════════════════════════════════════════════════════════

def check_environment(qlora: bool = False) -> bool:
    """检查运行环境是否满足要求"""
    print("=" * 60)
    print("第 1 步：环境检查")
    print("=" * 60)

    ok = True

    # 检查 Python 版本
    py_ver = sys.version_info
    print(f"  Python: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < (3, 9):
        print("  ✗ Python 版本需 >= 3.9")
        ok = False
    else:
        print("  ✓ Python 版本满足")

    # 检查 PyTorch
    try:
        import torch
        print(f"  ✓ PyTorch {torch.__version__}")
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_mem / (1024**3)
            print(f"    GPU: {gpu_name} ({gpu_mem:.1f} GB)")
            if gpu_mem < 8:
                print("    ⚠ 显存 < 8GB，只能用 QLoRA 4bit + offload 模式")
            elif gpu_mem < 16:
                print("    ⚠ 显存 < 16GB，推荐使用 QLoRA 4bit 模式")
            elif gpu_mem < 24:
                print("    ⚠ 显存 < 24GB，LoRA BF16 可用但 batch_size 需调小")
            else:
                print("    ✓ 显存充足，LoRA BF16 可全速运行")
        else:
            print("    ⚠ CUDA 不可用（仅 CPU 模式，训练极慢）")
    except ImportError:
        print("  ✗ PyTorch 未安装")
        print("    安装命令: pip install torch --index-url https://download.pytorch.org/whl/cu121")
        ok = False

    # 检查 LLaMA-Factory
    try:
        import llamafactory
        print(f"  ✓ LLaMA-Factory 已安装")
    except ImportError:
        # 尝试 CLI
        try:
            result = subprocess.run(
                ['llamafactory-cli', 'version'],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                print(f"  ✓ LLaMA-Factory CLI 可用")
            else:
                raise FileNotFoundError
        except (FileNotFoundError, OSError):
            print("  ✗ LLaMA-Factory 未安装")
            print("    安装方式一（推荐）:")
            print("      git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git")
            print("      cd LLaMA-Factory && pip install -e '.[torch,metrics]'")
            print("    安装方式二:")
            print("      pip install llamafactory")
            ok = False

    # 检查 bitsandbytes（QLoRA 需要）
    if qlora:
        try:
            import bitsandbytes
            print(f"  ✓ bitsandbytes {bitsandbytes.__version__}（QLoRA 可用）")
        except ImportError:
            print("  ✗ bitsandbytes 未安装（QLoRA 4bit 量化需要）")
            print("    安装命令: pip install bitsandbytes")
            ok = False
    else:
        try:
            import bitsandbytes
            print(f"  ✓ bitsandbytes {bitsandbytes.__version__}（若需 QLoRA 可直接使用 --qlora）")
        except ImportError:
            print("  ℹ bitsandbytes 未安装（QLoRA 不可用，LoRA BF16 不受影响）")

    # 检查训练数据
    if os.path.isfile(_DATASET_PATH):
        with open(_DATASET_PATH, 'r', encoding='utf-8') as f:
            count = sum(1 for _ in f)
        print(f"  ✓ 训练数据: {_DATASET_PATH} ({count} 条)")
    else:
        print(f"  ✗ 训练数据不存在: {_DATASET_PATH}")
        print("    请先运行: python build_sft_dataset.py")
        ok = False

    # 显存估算
    print()
    print("  显存估算：")
    print("  ┌──────────────────────────────────┬───────────┐")
    print("  │ 模型 + 模式                       │ 显存需求  │")
    print("  ├──────────────────────────────────┼───────────┤")
    print("  │ Qwen3-8B  LoRA BF16              │ ~22 GB    │")
    print("  │ Qwen3-8B  QLoRA 4bit             │ ~8 GB     │")
    print("  │ Qwen3.5-2B LoRA BF16             │ ~5 GB     │")
    print("  │ Qwen3.5-2B QLoRA 4bit            │ ~3 GB     │")
    print("  └──────────────────────────────────┴───────────┘")

    print()
    return ok


# ═══════════════════════════════════════════════════════════════════
# 第 2 步：下载模型
# ═══════════════════════════════════════════════════════════════════

def download_model(model_name: str, save_dir: str) -> str:
    """下载预训练模型

    Args:
        model_name: 模型名称（如 Qwen/Qwen3-8B-Instruct）
        save_dir: 保存目录

    Returns:
        模型本地路径
    """
    model_path = os.path.join(save_dir, model_name.replace('/', '_'))

    # 检查模型是否已存在
    config_file = os.path.join(model_path, 'config.json')
    if os.path.isdir(model_path) and os.path.isfile(config_file):
        print(f"  模型已存在: {model_path}")
        return model_path

    print(f"  下载模型: {model_name}")
    print(f"  保存到: {model_path}")
    print("  （模型约 16GB，下载需要较长时间）")

    os.makedirs(model_path, exist_ok=True)

    # 方式1: huggingface_hub（推荐）
    try:
        from huggingface_hub import snapshot_download
        print("  使用 huggingface_hub 下载...")
        snapshot_download(
            repo_id=model_name,
            local_dir=model_path,
        )
        print("  ✓ 下载完成")
        return model_path
    except ImportError:
        print("  ⚠ huggingface_hub 未安装")
    except Exception as e:
        print(f"  ⚠ huggingface_hub 下载失败: {e}")

    # 方式2: modelscope（国内镜像）
    try:
        from modelscope import snapshot_download as ms_download
        print("  使用 ModelScope 下载（国内镜像）...")
        ms_download(
            model_id=model_name,
            cache_dir=model_path,
        )
        print("  ✓ 下载完成")
        return model_path
    except ImportError:
        print("  ⚠ modelscope 未安装")
    except Exception as e:
        print(f"  ⚠ ModelScope 下载失败: {e}")

    # 方式3: llamafactory-cli download
    try:
        result = subprocess.run(
            ['llamafactory-cli', 'download', model_name],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=3600,
        )
        if result.returncode == 0:
            print("  ✓ 通过 LLaMA-Factory CLI 下载完成")
            return model_path
    except (FileNotFoundError, OSError):
        pass
    except Exception:
        pass

    print()
    print("  自动下载失败，请手动下载：")
    print(f"    方式1: huggingface-cli download {model_name}")
    print(f"    方式2: 从 https://huggingface.co/{model_name} 下载")
    print(f"    方式3: 从 https://modelscope.cn/models/{model_name} 下载（国内快）")
    print(f"    解压到: {model_path}")
    return model_path


# ═══════════════════════════════════════════════════════════════════
# 第 3 步：准备数据集
# ═══════════════════════════════════════════════════════════════════

def prepare_dataset(dataset_path: str, output_dir: str) -> tuple:
    """准备训练数据集并注册到 LLaMA-Factory

    将 Alpaca 格式转为 ShareGPT 格式，并注册到 dataset_info.json。

    Args:
        dataset_path: 原始 JSONL 数据集路径
        output_dir: 输出目录

    Returns:
        (sharegpt_path, dataset_name) 元组
    """
    print("=" * 60)
    print("第 3 步：准备训练数据集")
    print("=" * 60)

    # 转换为 ShareGPT 格式
    sharegpt_path = os.path.join(output_dir, 'light_sft_sharegpt.jsonl')
    os.makedirs(output_dir, exist_ok=True)

    count = _convert_to_sharegpt(dataset_path, sharegpt_path)
    print(f"  转换为 ShareGPT 格式: {sharegpt_path} ({count} 条)")

    # 注册到 LLaMA-Factory
    dataset_name = 'light_v32_sft'
    lf_dir = _find_llamafactory_dir()

    if lf_dir:
        data_dir = os.path.join(lf_dir, 'data')
        dataset_info_path = os.path.join(data_dir, 'dataset_info.json')
        target_data_path = os.path.join(data_dir, 'light_sft_sharegpt.jsonl')

        # 复制数据文件到 LLaMA-Factory data 目录
        shutil.copy2(sharegpt_path, target_data_path)
        print(f"  复制到 LLaMA-Factory: {target_data_path}")

        # 更新 dataset_info.json
        info = {}
        if os.path.isfile(dataset_info_path):
            with open(dataset_info_path, 'r', encoding='utf-8') as f:
                info = json.load(f)

        info[dataset_name] = {
            "file_name": "light_sft_sharegpt.jsonl",
            "formatting": "sharegpt",
            "columns": {
                "messages": "conversations",
            },
        }

        with open(dataset_info_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)

        print(f"  ✓ 数据集已注册: {dataset_name}")
        print(f"    dataset_info.json: {dataset_info_path}")
    else:
        # 未找到 LLaMA-Factory 目录，使用绝对路径注册
        print("  ⚠ 未找到 LLaMA-Factory 安装目录")
        print("  将在训练配置中使用绝对路径")

    return sharegpt_path, dataset_name


# ═══════════════════════════════════════════════════════════════════
# 第 4 步：生成训练配置
# ═══════════════════════════════════════════════════════════════════

def generate_yaml_config(
    model_path: str,
    dataset_name: str,
    dataset_path: str,
    output_dir: str,
    epochs: int = 3,
    batch_size: int = 2,
    lr: float = 1e-4,
    lora_rank: int = 16,
    max_seq_len: int = 1024,
    qlora: bool = False,
    gradient_accumulation: int = 8,
    use_absolute_path: bool = False,
    template: str = 'qwen3',
    lora_target: str = 'q_proj,v_proj,k_proj,o_proj,gate_proj,up_proj,down_proj',
) -> str:
    """生成 LLaMA-Factory 训练 YAML 配置文件

    Args:
        model_path: 预训练模型路径
        dataset_name: 数据集名称（已注册到 dataset_info.json）
        dataset_path: 数据集绝对路径（未注册时使用）
        output_dir: 输出目录
        epochs: 训练轮数
        batch_size: 每设备批大小
        lr: 学习率
        lora_rank: LoRA 秩
        max_seq_len: 最大序列长度
        qlora: 是否使用 QLoRA 4bit 量化
        gradient_accumulation: 梯度累积步数
        use_absolute_path: 是否使用绝对路径（未注册数据集时）

    Returns:
        YAML 配置文件路径
    """
    yaml_path = os.path.join(output_dir, 'train_config.yaml')
    os.makedirs(output_dir, exist_ok=True)

    lora_alpha = lora_rank * 2
    lora_target = lora_target

    # 量化配置
    quant_bit = 4 if qlora else None
    quant_type = "nf4" if qlora else None

    # 数据集引用
    if use_absolute_path:
        dataset_ref = dataset_path
        dataset_format = "sharegpt"
    else:
        dataset_ref = dataset_name
        dataset_format = None  # 从 dataset_info.json 读取

    yaml_lines = [
        f"# 光明翻译器 — Qwen3-8B {'QLoRA 4bit' if qlora else 'LoRA BF16'} 微调配置",
        f"# 由 train_lora_7b.py 自动生成",
        f"# 模型: {model_path}",
        f"# 数据: {dataset_ref} ({'QLoRA' if qlora else 'LoRA'})",
        f"",
        f"### 模型配置",
        f"model_name_or_path: {model_path}",
        f"trust_remote_code: true",
        f"",
        f"### 微调方法",
        f"stage: sft",
        f"do_train: true",
        f"finetuning_type: lora",
        f"lora_rank: {lora_rank}",
        f"lora_alpha: {lora_alpha}",
        f"lora_target: {lora_target}",
        f"lora_dropout: 0.05",
    ]

    if qlora:
        yaml_lines.extend([
            f"quantization_bit: {quant_bit}",
            f"quantization_method: {quant_type}",
        ])

    yaml_lines.extend([
        f"",
        f"### 数据集",
        f"dataset: {dataset_ref}",
    ])

    if dataset_format:
        yaml_lines.extend([
            f"dataset_dir: {os.path.dirname(dataset_path)}",
            f"template: {template}",
            f"cutoff_len: {max_seq_len}",
            f"formatting: {dataset_format}",
        ])
    else:
        yaml_lines.extend([
            f"template: {template}",
            f"cutoff_len: {max_seq_len}",
        ])

    yaml_lines.extend([
        f"",
        f"### 训练参数",
        f"output_dir: {output_dir}/checkpoints",
        f"per_device_train_batch_size: {batch_size}",
        f"gradient_accumulation_steps: {gradient_accumulation}",
        f"num_train_epochs: {epochs}",
        f"learning_rate: {lr}",
        f"lr_scheduler_type: cosine",
        f"warmup_ratio: 0.05",
        f"logging_steps: 10",
        f"save_steps: 100",
        f"save_total_limit: 3",
        f"",
        f"### 精度与性能",
        f"bf16: true" if not qlora else f"bf16: false",
        f"fp16: false",
        f"gradient_checkpointing: true",
        f"",
        f"### 其他",
        f"overwrite_output_dir: false",
        f"report_to: none",
        f"seed: 42",
        f"ddp_timeout: 180000000",
    ])

    yaml_content = '\n'.join(yaml_lines)

    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    print(f"  配置文件: {yaml_path}")
    return yaml_path


# ═══════════════════════════════════════════════════════════════════
# 第 5 步：执行训练
# ═══════════════════════════════════════════════════════════════════

def run_training(yaml_path: str) -> bool:
    """执行 LLaMA-Factory 训练

    Args:
        yaml_path: 训练配置 YAML 路径

    Returns:
        是否训练成功
    """
    print()
    print("=" * 60)
    print("第 5 步：执行 LoRA SFT 训练")
    print("=" * 60)
    print("  训练开始，请耐心等待...")
    print("  881 条数据 × 3 epochs，预计 30-90 分钟（取决于硬件）")
    print()

    # 方式1: llamafactory-cli
    try:
        result = _run_cmd(
            [sys.executable, '-m', 'llamafactory.cli', 'train', yaml_path],
        )
        if result.returncode == 0:
            print("  ✓ 训练完成")
            return True
        else:
            print(f"  ⚠ llamafactory-cli 训练返回非零: {result.returncode}")
    except Exception as e:
        print(f"  ⚠ llamafactory-cli 执行异常: {e}")

    # 方式2: llamafactory-train
    try:
        result = _run_cmd(
            ['llamafactory-train', yaml_path],
        )
        if result.returncode == 0:
            print("  ✓ 训练完成")
            return True
    except (FileNotFoundError, OSError):
        pass
    except Exception as e:
        print(f"  ⚠ llamafactory-train 执行异常: {e}")

    # 方式3: Python API
    try:
        from llamafactory.train.tuner import run_exp
        print("  尝试通过 Python API 训练...")
        run_exp(yaml_path)
        print("  ✓ 训练完成")
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"  ⚠ Python API 训练异常: {e}")

    print()
    print("  ✗ 自动训练未成功。请手动执行：")
    print(f"    llamafactory-cli train {yaml_path}")
    return False


# ═══════════════════════════════════════════════════════════════════
# 第 6 步：合并 LoRA 权重
# ═══════════════════════════════════════════════════════════════════

def merge_lora(model_path: str, checkpoint_dir: str, output_dir: str,
               lora_rank: int = 16) -> bool:
    """合并 LoRA 权重到基础模型

    Args:
        model_path: 基础模型路径
        checkpoint_dir: LoRA checkpoint 路径
        output_dir: 合并后模型输出路径
        lora_rank: LoRA 秩

    Returns:
        是否合并成功
    """
    print()
    print("=" * 60)
    print("第 6 步：合并 LoRA 权重")
    print("=" * 60)

    merge_output = os.path.join(output_dir, 'merged')
    os.makedirs(merge_output, exist_ok=True)

    # 找到最新的 checkpoint
    if not os.path.isdir(checkpoint_dir):
        # 尝试查找 checkpoints 子目录
        alt = os.path.join(output_dir, 'checkpoints')
        if os.path.isdir(alt):
            checkpoint_dir = alt
        else:
            print(f"  ✗ Checkpoint 目录不存在: {checkpoint_dir}")
            print(f"    请手动指定合并路径")
            return False

    # 找到最新的 checkpoint 子目录
    ckpt_dirs = sorted([
        d for d in os.listdir(checkpoint_dir)
        if d.startswith('checkpoint-') and os.path.isdir(os.path.join(checkpoint_dir, d))
    ], key=lambda x: int(x.split('-')[-1]) if x.split('-')[-1].isdigit() else 0)

    if ckpt_dirs:
        latest_ckpt = os.path.join(checkpoint_dir, ckpt_dirs[-1])
        print(f"  使用最新 checkpoint: {latest_ckpt}")
    else:
        latest_ckpt = checkpoint_dir
        print(f"  使用 checkpoint 目录: {latest_ckpt}")

    # 生成合并配置
    merge_yaml = os.path.join(output_dir, 'merge_config.yaml')
    merge_content = f"""### 合并 LoRA 权重
model_name_or_path: {model_path}
adapter_name_or_path: {latest_ckpt}
template: qwen3
finetuning_type: lora
lora_rank: {lora_rank}
export_dir: {merge_output}
export_size: 2
export_device: cpu
export_legacy_format: false
"""
    with open(merge_yaml, 'w', encoding='utf-8') as f:
        f.write(merge_content)

    # 执行合并
    try:
        result = _run_cmd(
            [sys.executable, '-m', 'llamafactory.cli', 'export', merge_yaml],
        )
        if result.returncode == 0:
            print(f"  ✓ 合并完成: {merge_output}")
            return True
    except Exception as e:
        print(f"  ⚠ 合并异常: {e}")

    # 备选
    try:
        from llamafactory.train.tuner import run_exp
        run_exp(merge_yaml)
        print(f"  ✓ 合并完成: {merge_output}")
        return True
    except Exception:
        pass

    print()
    print("  合并命令（手动）：")
    print(f"    llamafactory-cli export {merge_yaml}")
    return False


# ═══════════════════════════════════════════════════════════════════
# 第 7 步：测试推理
# ═══════════════════════════════════════════════════════════════════

def test_inference(model_path: str, merged_path: str = None) -> bool:
    """测试微调后模型的推理效果

    Args:
        model_path: 模型路径（合并后的或 LoRA adapter）
        merged_path: 合并后模型路径（如果使用 adapter 推理）

    Returns:
        是否测试成功
    """
    print()
    print("=" * 60)
    print("第 7 步：测试推理效果")
    print("=" * 60)

    use_model = merged_path or model_path
    if not os.path.isdir(use_model):
        print(f"  ✗ 模型路径不存在: {use_model}")
        return False

    test_cases = [
        ("def add(a, b): return a + b", "段落 加法 接收 a, b：\n    返回 a 加 b"),
        ("x = 10\nprint(x)", "设 x 为 10\n打印(x)"),
        ("for i in range(5): print(i)", "遍历 i 于 0至4：\n    打印(i)"),
    ]

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print(f"  加载模型: {use_model}")
        tokenizer = AutoTokenizer.from_pretrained(use_model, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            use_model,
            device_map="auto",
            trust_remote_code=True,
        )
        model.eval()

        print()
        correct = 0
        for i, (python_code, expected_hint) in enumerate(test_cases, 1):
            prompt = (
                f"将Python代码转为光明代码：\n\nPython代码：\n{python_code}"
            )
            messages = [
                {"role": "system", "value": "你是光明编程语言v3.2的翻译专家。将Python代码翻译为光明v3.2代码。"},
                {"role": "user", "value": prompt},
            ]
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(text, return_tensors="pt").to(model.device)

            import torch
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.1,
                    do_sample=True,
                )

            response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
            print(f"  测试 {i}:")
            print(f"    输入: {python_code}")
            print(f"    期望: {expected_hint}")
            print(f"    输出: {response}")
            print()

        return True

    except ImportError:
        print("  ⚠ transformers 未安装，跳过推理测试")
        print("    安装: pip install transformers accelerate")
        return False
    except Exception as e:
        print(f"  ⚠ 推理测试异常: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════

def main():
    # ── 预设名称列表（用于帮助信息） ──
    preset_names = ', '.join(f'{k} ({v["name"]})' for k, v in MODEL_PRESETS.items())
    default_preset = MODEL_PRESETS[_DEFAULT_PRESET]

    parser = argparse.ArgumentParser(
        description='光明翻译器 — 多模型 LoRA/QLoRA 一键微调',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
支持的模型预设（--model-preset）：
  qwen3-8b   — Qwen3-8B-Instruct（8B，生产部署首选，LoRA ~22GB / QLoRA ~8GB）
  qwen3.5-2b — Qwen3.5-2B-Instruct（2B，开发调试首选，LoRA ~5GB / QLoRA ~3GB）

示例:
  python train_lora_7b.py --model-preset qwen3.5-2b          # 2B 快速调试
  python train_lora_7b.py --model-preset qwen3-8b            # 8B 生产训练
  python train_lora_7b.py --model-preset qwen3.5-2b --qlora  # QLoRA 更省显存
  python train_lora_7b.py --model-preset qwen3-8b --epochs 5 --lora-rank 32
  python train_lora_7b.py --model-preset qwen3.5-2b --dry-run
  python train_lora_7b.py --model-preset qwen3.5-2b --test-infer
  python train_lora_7b.py --model ./my_local_model            # 自定义模型路径

显存需求:
  Qwen3-8B:    LoRA BF16 ~22GB / QLoRA 4bit ~8GB
  Qwen3.5-2B:  LoRA BF16 ~5GB  / QLoRA 4bit ~3GB

完整文档: tools/ai_copilot/README_LoRA7B.md
        """
    )

    parser.add_argument('--model-preset', default=_DEFAULT_PRESET,
                        choices=list(MODEL_PRESETS.keys()),
                        help=f'模型预设名称（默认: {_DEFAULT_PRESET}）')
    parser.add_argument('--model', default=None,
                        help='自定义预训练模型名称或路径（覆盖预设）')
    parser.add_argument('--output', default=None,
                        help='输出目录（默认: 根据预设自动生成）')
    parser.add_argument('--dataset', default=_DATASET_PATH,
                        help='训练数据 JSONL 路径')
    parser.add_argument('--epochs', type=int, default=None,
                        help='训练轮数（默认: 根据预设）')
    parser.add_argument('--batch-size', type=int, default=None,
                        help='每设备批大小（默认: 根据预设）')
    parser.add_argument('--lr', type=float, default=None,
                        help='学习率（默认: 根据预设）')
    parser.add_argument('--lora-rank', type=int, default=None,
                        help='LoRA 秩（默认: 16）')
    parser.add_argument('--max-seq-len', type=int, default=1024,
                        help='最大序列长度（默认: 1024）')
    parser.add_argument('--grad-accum', type=int, default=None,
                        help='梯度累积步数（默认: 根据预设）')
    parser.add_argument('--qlora', action='store_true',
                        help='使用 QLoRA 4bit 量化训练')
    parser.add_argument('--dry-run', action='store_true',
                        help='只生成配置文件，不执行训练')
    parser.add_argument('--skip-download', action='store_true',
                        help='跳过模型下载（假设模型已存在本地）')
    parser.add_argument('--skip-check', action='store_true',
                        help='跳过环境检查')
    parser.add_argument('--skip-merge', action='store_true',
                        help='跳过 LoRA 合并步骤')
    parser.add_argument('--test-infer', action='store_true',
                        help='训练后测试推理效果')
    parser.add_argument('--only-infer', action='store_true',
                        help='只测试推理（不训练）')
    parser.add_argument('--only-merge', action='store_true',
                        help='只合并 LoRA 权重（不训练）')

    args = parser.parse_args()

    # ── 应用预设 ──
    preset = MODEL_PRESETS[args.model_preset]
    model_name = args.model or preset['model_id']
    output_dir = args.output or preset['output_dir']
    batch_size = args.batch_size or preset['default_batch_size']
    lr = args.lr or preset['default_lr']
    lora_rank = args.lora_rank or preset['default_lora_rank']
    grad_accum = args.grad_accum or preset['default_grad_accum']
    template = preset['template']
    lora_target = preset['lora_target']

    print()
    print("=" * 60)
    print(f"模型预设: {args.model_preset} — {preset['name']}")
    print(f"  {preset['description']}")
    print(f"  参数量: {preset['params_b']}B")
    print(f"  显存: LoRA {preset['vram_lora']} / QLoRA {preset['vram_qlora']}")
    print("=" * 60)

    # ── 仅推理模式 ──
    if args.only_infer:
        merged_path = os.path.join(output_dir, 'merged')
        test_inference(model_name, merged_path)
        return

    # ── 仅合并模式 ──
    if args.only_merge:
        checkpoint_dir = os.path.join(output_dir, 'checkpoints')
        merge_lora(model_name, checkpoint_dir, output_dir, lora_rank)
        return

    # ── 环境检查 ──
    if not args.skip_check:
        if not check_environment(qlora=args.qlora):
            print("环境检查未通过，请安装缺失的依赖后重试。")
            print("安装指南: tools/ai_copilot/README_LoRA7B.md")
            sys.exit(1)

    # ── 下载模型 ──
    print()
    print("=" * 60)
    print("第 2 步：下载预训练模型")
    print("=" * 60)

    if args.skip_download:
        model_path = model_name
        print(f"  跳过下载，使用路径: {model_path}")
    else:
        model_cache = os.path.join(_SCRIPT_DIR, 'model_cache')
        model_path = download_model(model_name, model_cache)

    # ── 准备数据集 ──
    sharegpt_path, dataset_name = prepare_dataset(args.dataset, output_dir)

    # 检查数据集是否成功注册到 LLaMA-Factory
    lf_dir = _find_llamafactory_dir()
    use_absolute_path = lf_dir is None

    # ── 生成训练配置 ──
    print()
    print("=" * 60)
    print("第 4 步：生成训练配置")
    print("=" * 60)

    mode_str = "QLoRA 4bit" if args.qlora else "LoRA BF16"
    print(f"  模型: {preset['name']} ({preset['params_b']}B)")
    print(f"  训练模式: {mode_str}")
    print(f"  LoRA 秩: {lora_rank}")
    print(f"  学习率: {lr}")
    print(f"  批大小: {batch_size} × {grad_accum} = {batch_size * grad_accum} (等效)")

    yaml_path = generate_yaml_config(
        model_path=model_path,
        dataset_name=dataset_name,
        dataset_path=sharegpt_path,
        output_dir=output_dir,
        epochs=args.epochs or 3,
        batch_size=batch_size,
        lr=lr,
        lora_rank=lora_rank,
        max_seq_len=args.max_seq_len,
        qlora=args.qlora,
        gradient_accumulation=grad_accum,
        use_absolute_path=use_absolute_path,
        template=template,
        lora_target=lora_target,
    )

    if args.dry_run:
        print()
        print("Dry run 模式，配置已生成，不执行训练。")
        print(f"手动训练命令: llamafactory-cli train {yaml_path}")
        return

    # ── 执行训练 ──
    success = run_training(yaml_path)

    if not success:
        print()
        print("自动训练未成功。请手动执行：")
        print(f"  llamafactory-cli train {yaml_path}")
        print()
        print("或查看文档: tools/ai_copilot/README_LoRA7B.md")
        sys.exit(1)

    # ── 合并 LoRA ──
    if not args.skip_merge:
        checkpoint_dir = os.path.join(output_dir, 'checkpoints')
        merge_lora(model_path, checkpoint_dir, output_dir, lora_rank)

    # ── 测试推理 ──
    if args.test_infer:
        merged_path = os.path.join(output_dir, 'merged')
        test_inference(model_path, merged_path)

    # ── 完成 ──
    merged_path = os.path.join(output_dir, 'merged')
    checkpoint_dir = os.path.join(output_dir, 'checkpoints')
    print()
    print("=" * 60)
    print("训练完成！")
    print("=" * 60)
    print(f"  模型: {preset['name']}")
    print(f"  LoRA checkpoints: {checkpoint_dir}")
    print(f"  合并后模型: {merged_path}")
    print()
    print("下一步：")
    print(f"  1. 测试推理: python train_lora_7b.py --model-preset {args.model_preset} --only-infer")
    print(f"  2. 合并权重: python train_lora_7b.py --model-preset {args.model_preset} --only-merge")
    print(f"  3. 集成到光明管线: 将微调后的模型嵌入 light ai generate 流程")
    print()
    print("部署方式：")
    print("  - vLLM:   vllm serve <merged_path> --port 8000")
    print("  - Ollama: 将 GGUF 导入 Ollama（需先转换格式）")
    print("  - API:    python -m llamafactory.cli api <merged_path>")


if __name__ == '__main__':
    main()
