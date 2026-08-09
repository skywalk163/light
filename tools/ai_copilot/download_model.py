#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明翻译器 — 模型下载脚本

下载 Qwen2.5-0.5B-Instruct 到本地缓存目录。
这个模型只有 5 亿参数，BF16 约 1GB，CPU 完全可跑。

用法：
    python download_model.py
    python download_model.py --model qwen2.5-0.5b
    python download_model.py --model qwen3.5-2b     # Qwen3.5-2B（多模态，需 transformers>=5.0）
    python download_model.py --model qwen2.5-1.5b   # 更大但更强
"""

import argparse
import os
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

MODELS = {
    "qwen2.5-0.5b": {
        "hf_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "size_gb": 1.0,
        "min_transformers": "4.44.0",
        "desc": "0.5B 参数，CPU 训练/推理最快，适合 11GB 内存环境",
    },
    "qwen2.5-1.5b": {
        "hf_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "size_gb": 3.0,
        "min_transformers": "4.44.0",
        "desc": "1.5B 参数，效果更好但训练慢约 3 倍",
    },
    "qwen2.5-coder-1.5b": {
        "hf_id": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        "size_gb": 3.0,
        "min_transformers": "4.44.0",
        "desc": "1.5B 代码专用模型，代码生成能力强",
    },
    "qwen3.5-2b": {
        "hf_id": "Qwen/Qwen3.5-2B",
        "size_gb": 4.5,
        "min_transformers": "5.0.0",
        "desc": "2B 参数，多模态架构（Gated DeltaNet + MoE），需 transformers>=5.0，GPU LoRA ~5GB 显存",
    },
}


def download_model(model_key: str, cache_dir: str = None):
    """下载模型到本地"""
    if model_key not in MODELS:
        print(f"未知模型: {model_key}")
        print(f"可选: {', '.join(MODELS.keys())}")
        sys.exit(1)

    info = MODELS[model_key]
    hf_id = info["hf_id"]

    if cache_dir is None:
        cache_dir = os.path.join(_SCRIPT_DIR, "model_cache", model_key)

    print("=" * 60)
    print(f"下载模型: {hf_id}")
    print(f"  参数量: {model_key}")
    print(f"  大小:   ~{info['size_gb']} GB")
    print(f"  说明:   {info['desc']}")
    min_ver = info.get("min_transformers", "4.0.0")
    if min_ver != "4.0.0":
        print(f"  要求:   transformers >= {min_ver}")
    print(f"  目标:   {cache_dir}")
    print("=" * 60)

    # 检查是否已安装 huggingface_hub
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("\n[ERROR] huggingface_hub 未安装")
        print("  请先运行: pip install huggingface_hub")
        sys.exit(1)

    # 检查目录是否已有模型
    if os.path.exists(cache_dir) and os.path.exists(os.path.join(cache_dir, "config.json")):
        print(f"\n模型已存在于 {cache_dir}")
        print("如需重新下载，请先删除该目录。")
        return cache_dir

    os.makedirs(cache_dir, exist_ok=True)

    print(f"\n开始下载（从 HuggingFace Hub）...")
    print("如果国内网络不通，可设置镜像:")
    print("  set HF_ENDPOINT=https://hf-mirror.com")
    print()

    t0 = time.time()

    # 用 snapshot_download 直接下载原始文件，绕过 torch/torchvision 导入链
    # 避免 Kaggle 环境 torchvision 与 torch 版本不兼容导致 from_pretrained 崩溃
    try:
        print("[1/1] 下载模型文件（snapshot_download）...")
        snapshot_download(
            repo_id=hf_id,
            local_dir=cache_dir,
            local_dir_use_symlinks=False,
        )
        print(f"  ✓ 模型文件保存完成")

    except Exception as e:
        print(f"\n[ERROR] 下载失败: {e}")
        print("\n尝试使用 HuggingFace 镜像:")
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

        print("[1/1] 下载模型文件（镜像）...")
        snapshot_download(
            repo_id=hf_id,
            local_dir=cache_dir,
            local_dir_use_symlinks=False,
        )
        print(f"  ✓ 模型文件保存完成")

    elapsed = time.time() - t0
    print(f"\n下载完成！耗时 {elapsed:.0f} 秒")
    print(f"模型路径: {cache_dir}")
    return cache_dir


def main():
    parser = argparse.ArgumentParser(description="下载预训练模型")
    parser.add_argument(
        "--model",
        default="qwen2.5-0.5b",
        choices=list(MODELS.keys()),
        help="模型选择（默认 qwen2.5-0.5b）",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="自定义缓存目录（默认 model_cache/<model>）",
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    download_model(args.model, args.cache_dir)


if __name__ == "__main__":
    main()
