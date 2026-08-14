"""
段言端侧离线模型打包工具

将 Ollama 上的 duan-translator 模型打包进安装包，
实现完全离线的 AI 代码生成能力。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "ollama_model"
OUTPUT_DIR = PROJECT_ROOT / "output" / "offline_model"
INSTALLER_MODEL_DIR = PROJECT_ROOT / "tools" / "installer" / "offline_model"


class OfflineModelPackager:
    """端侧离线模型打包工具"""

    def __init__(self):
        """初始化打包器"""
        self.model_name = "duan-translator"
        self.ollama_available = self._check_ollama()

    def _check_ollama(self) -> bool:
        """检查 ollama 是否可用"""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def check_model_status(self) -> dict:
        """检查模型状态

        Returns:
            包含模型状态信息的字典:
            - ollama_available: bool, Ollama 是否可用
            - model_installed: bool, 模型是否已安装
            - model_size: int, 模型文件大小（字节）
            - model_path: str, 本地模型目录路径
        """
        status = {
            "ollama_available": self.ollama_available,
            "model_installed": False,
            "model_size": 0,
            "model_path": str(MODEL_DIR),
        }
        if not self.ollama_available:
            return status

        # 检查模型是否已安装
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        if self.model_name in result.stdout:
            status["model_installed"] = True

        # 检查本地模型文件
        gguf_files = list(MODEL_DIR.glob("*.gguf"))
        if gguf_files:
            status["model_size"] = max(f.stat().st_size for f in gguf_files)

        return status

    def export_model(self) -> Tuple[bool, str]:
        """从 ollama 导出模型为 GGUF

        Returns:
            (成功标志, 消息字符串)
        """
        if not self.ollama_available:
            return False, "ollama 不可用，请先安装 ollama"

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # 使用 ollama export 命令导出模型
        try:
            result = subprocess.run(
                ["ollama", "export", self.model_name, str(OUTPUT_DIR / f"{self.model_name}.gguf")],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                return True, f"模型已导出到 {OUTPUT_DIR}"
            else:
                return False, f"导出失败: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "导出超时"

    def package_for_installer(self) -> Tuple[bool, str]:
        """将模型文件打包到安装包目录

        Returns:
            (成功标志, 消息字符串)
        """
        INSTALLER_MODEL_DIR.mkdir(parents=True, exist_ok=True)

        # 查找 GGUF 模型文件
        gguf_files = list(OUTPUT_DIR.glob("*.gguf"))
        if not gguf_files:
            gguf_files = list(MODEL_DIR.glob("*.gguf"))

        if not gguf_files:
            return False, "未找到 GGUF 模型文件，请先运行 --export"

        # 复制到安装包目录
        for f in gguf_files:
            shutil.copy2(f, INSTALLER_MODEL_DIR / f.name)

        # 创建模型清单
        manifest = {
            "model_name": self.model_name,
            "version": "1.0.0",
            "files": [f.name for f in gguf_files],
            "description": "段言翻译器端侧模型，用于离线 AI 代码生成",
            "requirements": {
                "ram_min_mb": 1024,
                "disk_mb": sum(f.stat().st_size for f in gguf_files) // (1024 * 1024),
            }
        }
        with open(INSTALLER_MODEL_DIR / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        return True, f"模型已打包到 {INSTALLER_MODEL_DIR}"

    def print_status(self):
        """打印模型状态报告"""
        status = self.check_model_status()
        print("=" * 50)
        print("  段言端侧离线模型状态")
        print("=" * 50)
        print(f"  Ollama 可用:    {'是' if status['ollama_available'] else '否'}")
        if status['ollama_available']:
            print(f"  模型已安装:     {'是' if status['model_installed'] else '否'}")
        print(f"  本地模型目录:   {status['model_path']}")
        if status['model_size'] > 0:
            print(f"  模型文件大小:   {status['model_size'] / 1024 / 1024:.1f} MB")
        print("=" * 50)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="段言端侧离线模型打包工具")
    parser.add_argument("--check", action="store_true", help="检查模型状态")
    parser.add_argument("--export", action="store_true", help="从 ollama 导出模型")
    parser.add_argument("--package", action="store_true", help="打包到安装包目录")
    args = parser.parse_args()

    packager = OfflineModelPackager()

    if args.check:
        packager.print_status()
    elif args.export:
        success, msg = packager.export_model()
        print(msg)
    elif args.package:
        success, msg = packager.package_for_installer()
        print(msg)
    else:
        packager.print_status()
        print("\n用法: python tools/package_offline_model.py --check|--export|--package")


if __name__ == "__main__":
    main()