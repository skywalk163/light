# -*- coding: utf-8 -*-
"""T1 固化打包脚本：生成 0.88 验证机用 light_verify.tar.gz。

固化项（见 0.88失败修复_任务分解.md / 并行任务 路1）：
  必须包含 任务书/ docs/ vscode-extension/ —— 曾因 tar 排除列表漏掉导致
  0.88 上清单类门禁 10 红 + vscode/native_leg 假红。
用法：python scripts/pack_verify_tar.py
"""
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(r"C:\Users\skywalk\AppData\Local\Temp\light_verify.tar.gz")

# 允许打包的目录/文件白名单：0.88 验证机所需的最小集
INCLUDE_DIRS = ["src", "stdlib", "stdlib_v3", "tests", "docs", "vscode-extension", "任务书",
                "cli", "scripts", "tools", "examples", "contrib", "templates", "bootstrap"]
INCLUDE_FILES = ["pyproject.toml", "README.md", "conftest.py"]
# conftest.py 若在 tests/ 下自动包含

EXCLUDE_PARTS = {".git", "__pycache__", ".venv", ".pytest_cache", "node_modules",
                 "build", "dist", "light.egg-info", ".ccls-cache"}

def main():
    assert (ROOT / "任务书").is_dir(), "任务书/ 缺失，禁止打包"
    assert (ROOT / "docs").is_dir(), "docs/ 缺失，禁止打包"
    assert (ROOT / "vscode-extension").is_dir(), "vscode-extension/ 缺失，禁止打包"
    n = 0
    with tarfile.open(OUT, "w:gz") as tf:
        for d in INCLUDE_DIRS:
            p = ROOT / d
            if not p.is_dir():
                continue
            for f in p.rglob("*"):
                if f.is_file() and not (EXCLUDE_PARTS & set(f.parts)):
                    tf.add(f, arcname=str(f.relative_to(ROOT)))
                    n += 1
        for fname in INCLUDE_FILES:
            f = ROOT / fname
            if f.is_file():
                tf.add(f, arcname=fname)
                n += 1
    print(f"packed {n} files -> {OUT}")
    # 自检：三个关键目录的样本文件必须在 tar 内
    with tarfile.open(OUT, "r:gz") as tf:
        names = set(tf.getnames())
    for probe in ["任务书/原生腿产品清单.json", "任务书/分布式判据清单.json",
                  "任务书/自举地板清单.json", "任务书/缺失内置清单.json",
                  "vscode-extension/extension.js"]:
        print(("OK  " if probe in names else "MISS") + " " + probe)
        assert probe in names, f"关键文件缺失: {probe}"
    print("VERIFY OK")

if __name__ == "__main__":
    main()
