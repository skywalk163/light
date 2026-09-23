# -*- coding: utf-8 -*-
"""固化本机 light-merge 虚拟环境（.venv）依赖，保证「删 venv 重建」不丢关键包。

R89-B：R88-C 在 light-merge/.venv 手工补装了 lunardate==0.3.0 与 requests==2.34.2，
消除 14 条缺库红（test_datetime 农历 8 条 + test_lightpub_bridge 6 条），但未固化——
重建 venv 会丢。本脚本把该补装动作固化成幂等步骤。

设计口径（对齐 lightharness/scripts/同步0.86.py 的 ensure_venv）：
  * 只锁 **R88-C 实测确认** 的两个包版本，其余依赖按 .venv 现状核对，**不擅自新增**；
  * 幂等：已装且版本匹配 → 跳过；已装但版本不符 → 升级到锁版本；未装 → 安装锁版本；
  * 另有 WATCH 清单（门禁/运行时相关），缺失只 WARN 提示、不自动装（避免擅自改环境）；
  * 独立运行退出码 0；`--check` 只体检不写环境。

用法：
    python scripts/ensure_venv.py            # 确保依赖就位（幂等）
    python scripts/ensure_venv.py --check    # 只体检，不改环境
    python scripts/ensure_venv.py --venv D:/path/to/.venv   # 指定其它 venv

对应测试文件（锁版本依据）：
  * lunardate==0.3.0  → tests/test_datetime.py（农历 8 条）、stdlib/历法、stdlib/日期时间
  * requests==2.34.2  → tests/test_lightpub_bridge.py（6 条）、stdlib/lightpub HTTP 客户端
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# 脚本位于 <light-merge>/scripts/ 下 → 仓库根 = parents[1]
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VENV = ROOT / ".venv"

# ── 固化项：R88-C 实测版本，必须锁 ────────────────────────────────────────────
# 键 = pip 包名（import 名可能不同），值 = 锁定版本
LOCKED: dict[str, str] = {
    "lunardate": "0.3.0",
    "requests": "2.34.2",
}

# ── 观察项：只核对存在性，缺失 WARN、不自动安装（避免擅自扩环境）─────────────
WATCH: tuple[str, ...] = (
    "pytest",                  # 门禁运行器
    "pytest-xdist",            # 全量 -n auto 并行
    "pytest-timeout",          # 用例超时保护
    "antlr4-python3-runtime",  # 光明生成解析器运行时契约（应为 4.13.2）
    "psutil",                  # 进程树/子进程类用例（0.86 侧必备，本机视用例需要）
)


def venv_python(venv: Path) -> Path:
    """返回 venv 的 python 可执行文件（跨平台）。"""
    win = venv / "Scripts" / "python.exe"
    if win.exists():
        return win
    posix = venv / "bin" / "python"
    if posix.exists():
        return posix
    raise SystemExit(f"[ensure_venv] 找不到 venv 解释器：{venv}/Scripts/python.exe 或 {venv}/bin/python")


def installed_version(py: Path, pkg: str) -> str | None:
    """`pip show` 取已装版本；未装返回 None。"""
    r = subprocess.run([str(py), "-m", "pip", "show", pkg],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        return None
    for line in r.stdout.splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
    return ""


def pip_install(py: Path, spec: str) -> int:
    print(f"[ensure_venv] 安装 {spec} …")
    r = subprocess.run([str(py), "-m", "pip", "install", spec],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        print(f"[ensure_venv] ❌ 安装失败 {spec}（rc={r.returncode}）")
        print((r.stdout or "")[-800:] + (r.stderr or "")[-800:])
    else:
        print(f"[ensure_venv] ✅ 已安装 {spec}")
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="固化 light-merge/.venv 依赖（幂等）")
    ap.add_argument("--venv", default=str(DEFAULT_VENV), help="venv 目录，默认同仓 .venv")
    ap.add_argument("--check", action="store_true", help="只体检，不安装/升级")
    args = ap.parse_args()

    venv = Path(args.venv)
    if not venv.exists():
        print(f"[ensure_venv] ⚠️ venv 不存在：{venv}（跳过，不阻断）")
        return 0
    py = venv_python(venv)
    print(f"[ensure_venv] venv = {venv}")
    print(f"[ensure_venv] python = {py}")

    rc_all = 0
    # 1) 固化项
    for pkg, ver in LOCKED.items():
        cur = installed_version(py, pkg)
        if cur == ver:
            print(f"[ensure_venv] ✓ {pkg}=={ver} 已就位，跳过")
            continue
        if cur is None:
            print(f"[ensure_venv] · {pkg} 未安装（期望 {ver}）")
        else:
            print(f"[ensure_venv] · {pkg} 版本 {cur} != 期望 {ver}")
        if args.check:
            rc_all = 1
            continue
        rc_all |= pip_install(py, f"{pkg}=={ver}")

    # 2) 观察项（缺失只 WARN）
    for pkg in WATCH:
        cur = installed_version(py, pkg)
        if cur is None:
            print(f"[ensure_venv] ⚠️ 观察项缺失：{pkg}（不自动安装；若对应用例报缺库请人工补或登记）")
        else:
            print(f"[ensure_venv] ✓ 观察项 {pkg}=={cur}")

    if args.check and rc_all:
        print("[ensure_venv] --check 结论：存在未就位的固化项")
    else:
        print("[ensure_venv] 完成")
    # 门禁集成点要求「失败不阻断」，故恒 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
