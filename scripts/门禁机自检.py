#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门禁机自检.py —— 把 `docs/门禁机初始化清单_0.88.md` 的三步做成**可执行自检**。

为什么要有这个脚本
------------------
那三步（git 树 / lightharness 副本 / venv 依赖）此前全靠人肉手敲。后果是**同一
commit 本机绿、0.82 红**反复重演：R161-E 实测 `test_builtins_drift` 的 26 项
「缺口」其实是 `/home/ai/lightharness` 拷贝陈旧，与仓库代码无关；`cryptography`
缺失也是纯环境问题。手敲清单不会自己报错，脚本会。

三步自检
--------
① **git 树**：HEAD 短号、`git status --porcelain` 必须为空、不得是 shallow 克隆
   （可选 `--expect-head` 比对本轮基线）。
② **lightharness 副本**：与主真源 `stdlib/builtins.py` 比对 —— 名字差集必须
   等于 `LH_ONLY`、公共函数体哈希逐项一致、`内置核心判型.light` 四个判型段落齐。
   **口径不另写**：直接复用 `scripts/sync_builtins.py` 的 `parse_functions` /
   `block_hash` / `LH_ONLY` / `LH_LIGHT_SYNC`（两处口径迟早分叉，故不复制）。
③ **venv 依赖**：`scripts/ensure_venv.py` 的 `LOCKED` 逐项版本核对（唯一权威）。
④ **baseline 收集数**：`tests/ci_baseline_failures.txt` 快照 collected 与
   `pytest --collect-only` 实际门收集数偏差 ≤ ±10%（R165 补；防基线虚高、分辨力归零）。

用法
----
    python scripts/门禁机自检.py --check                      # 默认 venv = <仓库根>/.venv
    python scripts/门禁机自检.py --check --venv /home/ai/lm082_venv
    python scripts/门禁机自检.py --check --expect-head 8ae1bdf80
    python scripts/门禁机自检.py --check --allow-dirty         # 只核②③固化项，跳过①工作树干净

`--allow-dirty`（R164-D）：只跳过「①git 工作树干净」这一条断言，②LH 副本 / ③LOCKED
依赖仍照核。用于 **pre-push 场景**——推送时工作树常含未提交 / 未跟踪物（scratch、
本轮并行改动），那不是「同 commit 判绿」要守的东西；但闸门只该看固化项。默认（不带
本开关）仍是初始化 / 收口时的严格口径。

退出码：**0 = 全 PASS；1 = 有 FAIL**。`--check` 是只读模式（不装包、不改任何文件），
修环境请用 `scripts/ensure_venv.py --venv ...`（幂等安装）。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# 口径复用：不另写一份副本比对逻辑
import sync_builtins as _sb  # noqa: E402
import ensure_venv as _ev  # noqa: E402

_判型段落 = ("段落 是布尔", "段落 是函数", "段落 是数值", "段落 字符串全数字")


class _结果:
    def __init__(self):
        self.行 = []

    def add(self, ok: bool, 项: str, 说明: str = ""):
        self.行.append((bool(ok), 项, 说明))

    def info(self, 项: str, 说明: str = ""):
        self.行.append((None, 项, 说明))

    @property
    def 全过(self) -> bool:
        return all(ok is not False for ok, _, _ in self.行)


def _跑(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(cwd) if cwd else None)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


# ── ① git 树 ────────────────────────────────────────────────────────────────
def 检git树(res: _结果, 期望head: str | None, 树: Path, allow_dirty: bool = False):
    if not (树 / ".git").exists():
        res.add(False, "①git 树存在", f"{树} 不是 git 工作树")
        return
    rc, head, err = _跑(["git", "rev-parse", "--short", "HEAD"], cwd=树)
    if rc != 0:
        res.add(False, "①git HEAD 可读", err[:200])
        return
    res.info("①git HEAD", head)
    if 期望head:
        res.add(head.startswith(期望head) or 期望head.startswith(head),
                "①git HEAD == 期望", f"期望 {期望head}，实得 {head}")

    rc2, 干净, _ = _跑(["git", "status", "--porcelain"], cwd=树)
    if allow_dirty:
        # R164-D：pre-push 场景跳过「工作树干净」硬判——推送时工作树常含未提交/未跟踪物
        # （scratch、本轮并行改动），那不是「同 commit 判绿」要守的东西。降级为 INFO 留痕。
        res.info("①git 工作树（--allow-dirty 跳过干净校验）",
                 "干净" if 干净 == "" else "未跟踪/改动：" + 干净.replace("\n", " | ")[:300])
    else:
        res.add(rc2 == 0 and 干净 == "", "①git 工作树干净",
                "" if 干净 == "" else "未跟踪/改动：" + 干净.replace("\n", " | ")[:300])

    rc3, shallow, _ = _跑(["git", "rev-parse", "--is-shallow-repository"], cwd=树)
    res.add(rc3 == 0 and shallow == "false", "①git 非 shallow 克隆",
            f"实得 {shallow or 'unknown'}（shallow 会让基线比对失真）")


# ── ② lightharness 副本 ────────────────────────────────────────────────────
def 检lh副本(res: _结果, lh: Path | None):
    lh_path = Path(lh) if lh else Path(_sb.LH_PATH)
    main_path = Path(_sb.MAIN_PATH)
    if not main_path.exists():
        res.add(False, "②真源 builtins.py", f"不存在：{main_path}")
        return
    if not lh_path.exists():
        res.add(False, "②LH 副本 builtins.py",
                f"不存在：{lh_path}（/home/ai/lightharness 非 git 仓，需 sync_builtins.py 刷新）")
        return
    res.info("②LH 副本路径", str(lh_path))

    主文 = _sb.read(str(main_path))
    主函数, 主序 = _sb.parse_functions(主文)
    lh文 = _sb.read(str(lh_path))
    lh函数, _ = _sb.parse_functions(lh文)

    独有 = set(lh函数) - set(主函数)
    res.add(独有 == set(_sb.LH_ONLY), "②LH 独有函数 == LH_ONLY",
            f"期望 {sorted(_sb.LH_ONLY)}，实得 {sorted(独有)}")
    缺失 = set(主函数) - set(lh函数)
    res.add(not 缺失, "②LH 不缺真源函数",
            "" if not 缺失 else f"缺 {len(缺失)} 项：{sorted(缺失)[:12]}")

    漂移 = [n for n in 主序
            if n not in _sb.LH_ONLY and n in lh函数
            and _sb.block_hash(lh函数[n]) != _sb.block_hash(主函数[n])]
    res.add(not 漂移, "②LH 公共函数体哈希一致",
            "" if not 漂移 else f"{len(漂移)} 项漂移：{漂移[:12]}")

    lh_stdlib = lh_path.parent
    for name in _sb.LH_LIGHT_SYNC:
        p = lh_stdlib / name
        if not p.exists():
            res.add(False, f"②LH {name}", f"不存在：{p}")
            continue
        t = _sb.read(str(p))
        缺 = [s for s in _判型段落 if s not in t]
        res.add(not 缺, f"②LH {name} 判型段落齐", "" if not 缺 else f"缺 {缺}")


# ── ③ venv 依赖 ────────────────────────────────────────────────────────────
def 检venv(res: _结果, venv: Path):
    venv = Path(venv)
    if not venv.exists():
        res.add(False, "③venv 存在", f"不存在：{venv}")
        return
    try:
        py = _ev.venv_python(venv)
    except SystemExit as e:
        res.add(False, "③venv 解释器", str(e))
        return
    if not py.exists():
        res.add(False, "③venv 解释器", f"不存在：{py}")
        return
    res.info("③venv 解释器", str(py))
    for pkg, 期望 in _ev.LOCKED.items():
        实得 = _ev.installed_version(py, pkg)
        res.add(实得 == 期望, f"③LOCKED {pkg}=={期望}",
                "" if 实得 == 期望 else f"实得 {实得!r}（未装或版本漂移）")
    for pkg in _ev.WATCH:
        实得 = _ev.installed_version(py, pkg)
        res.info(f"③WATCH {pkg}", 实得 or "未装（仅 WARN，不影响退出码）")


# ── ④ baseline 收集数偏差 ──────────────────────────────────────────────────
def 检baseline偏差(res: _结果, 树: Path, py: Path, 容差: float = 0.10):
    """核对 `tests/ci_baseline_failures.txt` 登记的 collected 与实际门收集数。

    R165 取证：旧基线 collected=1203 而实际全量门收集 9399 例，基线虚高（实为虚低）
    后分辨力归零——「基线外新增打红」根本拦不住。这里用 `pytest --collect-only`
    只读重收（不执行，秒级），与基线快照 collected 比对，偏差 > ±10% 即 FAIL，
    防基线再次与真实门脱节。collect-only 不跑用例，无副作用。
    """
    base_file = 树 / "tests" / "ci_baseline_failures.txt"
    if not base_file.exists():
        res.add(False, "④baseline 文件存在", f"不存在：{base_file}")
        return
    m = re.search(r"collected\s*=\s*(\d+)", base_file.read_text(encoding="utf-8"))
    if not m:
        res.add(False, "④baseline 含 collected 快照", "未找到 collected=<N> 行")
        return
    基线数 = int(m.group(1))
    res.info("④baseline 登记 collected", str(基线数))

    # collect-only 即使有零星收集错误也会打印已收集数，故不依赖退出码
    rc, out, err = _跑([str(py), "-m", "pytest", "--collect-only", "-q",
                        "-p", "no:cacheprovider", "tests"], cwd=树)
    实际数 = None
    for line in reversed(out.splitlines()):
        mm = re.search(r"(\d+)\s+tests?\s+collected", line)
        if mm:
            实际数 = int(mm.group(1))
            break
    if 实际数 is None:
        # 兜底：数含 "::" 的用例行（旧版 pytest 无末行汇总时）
        实际数 = sum(1 for ln in out.splitlines() if "::" in ln)
    if not 实际数:
        res.add(False, "④实际门收集数可读",
                f"pytest --collect-only 未产出用例（rc={rc}）：{(err or out)[-200:]}")
        return
    res.info("④实际门 collected", str(实际数))
    偏差 = abs(实际数 - 基线数) / float(基线数)
    res.add(偏差 <= 容差, f"④baseline collected 偏差 ≤ ±{int(容差 * 100)}%",
            f"基线 {基线数} vs 实际 {实际数}，偏差 {偏差 * 100:.1f}%")


def main() -> int:
    ap = argparse.ArgumentParser(description="门禁机三步自检（只读）")
    ap.add_argument("--check", action="store_true",
                    help="只读自检模式（默认即只读；本脚本不会修改任何文件）")
    ap.add_argument("--venv", default=str(_ev.DEFAULT_VENV), help="待检 venv 路径")
    ap.add_argument("--lh", default=None, help="lightharness 副本 builtins.py 路径（默认取 sync_builtins.LH_PATH）")
    ap.add_argument("--tree", default=str(ROOT), help="待检 git 工作树（默认 = 本仓库根）")
    ap.add_argument("--expect-head", default=None, help="期望 HEAD（短号或全号），不符即 FAIL")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="只跳过「①git 工作树干净」断言（②LH 副本/③LOCKED 仍硬判）；pre-push 场景用")
    args = ap.parse_args()

    res = _结果()
    print("=" * 72)
    print("门禁机自检（只读）  树 =", args.tree)
    print("=" * 72)
    检git树(res, args.expect_head, Path(args.tree), args.allow_dirty)
    检lh副本(res, Path(args.lh) if args.lh else None)
    检venv(res, Path(args.venv))
    try:
        _py = _ev.venv_python(Path(args.venv))
        检baseline偏差(res, Path(args.tree), _py)
    except SystemExit as _e:
        res.add(False, "④baseline 偏差（venv 解释器不可用）", str(_e))
    print("-" * 72)

    失败数 = 0
    for ok, 项, 说明 in res.行:
        if ok is None:
            print(f"  INFO  {项}" + (("：" + 说明) if 说明 else ""))
        elif ok:
            print(f"  PASS  {项}")
        else:
            失败数 += 1
            print(f"  FAIL  {项}" + (("：" + 说明) if 说明 else ""))
    print("-" * 72)
    print(f"结果：{'全 PASS' if 失败数 == 0 else str(失败数) + ' 项 FAIL'}")
    print("修法：git 树/副本问题见 docs/门禁机初始化清单_0.88.md；依赖用 "
          "scripts/ensure_venv.py --venv <venv>（幂等安装）")
    return 0 if 失败数 == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
