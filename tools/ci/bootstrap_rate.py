# -*- coding: utf-8 -*-
r"""语言自举率 + 引 Python 逃逸计数门禁（第三轮 D3-4）。

把「自举率」「引 Python 逃逸」两个核心度量从人工统计变成可复现脚本，
统一到 `第三轮总纲.md` §2.3 的**唯一口径**，杜绝第二轮文档里
0/134、8/63、16/68 三个口径互相打架的问题。

唯一口径（§2.3）：
  - code    = 非空且不以 `#` 开头的行
  - decl    = 含 `段落` / `类` / `函数` 定义的行
  - 有真实现 ⇔ decl ≥ 1
  - **主报文件维度**（当前 16/68 ≈ 23.5%）；行维度虚高（85.8%），脚本里明确标注不许引用。
  - 引 Python 计数：`引\s*Python[：:]`（覆盖全角/半角冒号），排除
    `.git` / `__pycache__` / `.light_cache` / `docs-site` / `.ml_cache`。
    当前真值：stdlib/ 下 0 处；全仓 .light 源码 19 处（15 个文件，全在
    examples/ 的 L3/L4 分层教学示例，属教学用途，不算违规）。

门禁判据：
  - stdlib/ 下「引 Python」计数 > 0 即红（守住破零成果）。
  - 自举率只许升不许降（基线写进 bootstrap_rate_baseline.json）。
  - stdlib/lightpub/ 下 .light 数量当前 0、.py 56 —— 记入报告，不设门禁。

用法：
  # 对比模式（CI 用）
  python3 tools/ci/bootstrap_rate.py --root .
  # 刷新基线（自举率提升后手工执行并提交）
  python3 tools/ci/bootstrap_rate.py --root . --write-baseline tools/ci/bootstrap_rate_baseline.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# 引 Python 逃逸：覆盖全角/半角冒号
RE_PYTHON_ESCAPE = re.compile(r"引\s*Python[：:]")
# 定义行判定（§2.3：decl = 含「段落/类/函数 定义」的行）。
# 必须是定义行（关键字在行首缩进之后），不能只是「调用 函数甲()」里出现关键字，
# 否则会把纯调用行误算成实现。严格口径得到的文件维度自举率 = 16/68 ≈ 23.5%，
# 与第三轮总纲 §2.3 给出的当前真值一致。
RE_DECL = re.compile(r"^\s*(段落|类|函数)\b")

# 扫描时跳过的目录
_SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules",
              ".light_cache", ".ml_cache", "docs-site"}

_DEFAULT_BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "bootstrap_rate_baseline.json")


def iter_light_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".light"):
                yield os.path.join(dirpath, fn)


def count_code_decl(lines):
    """返回 (code 行数, decl 行数)。code=非空且非 `#` 开头；decl=行首定义行。"""
    code = 0
    decl = 0
    for raw in lines:
        s = raw.rstrip("\n")
        if not s.strip():
            continue
        if s.lstrip().startswith("#"):
            continue
        code += 1
        if RE_DECL.search(s):
            decl += 1
    return code, decl


def scan_stdlib(root):
    """扫描 stdlib/ 下所有 .light，按 §2.3 口径算文件维度自举率。"""
    stdlib_dir = os.path.join(root, "stdlib")
    files = []
    if os.path.isdir(stdlib_dir):
        files = list(iter_light_files(stdlib_dir))
    total = 0
    has_impl = 0
    for full in files:
        total += 1
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                _, decl = count_code_decl(fh)
        except OSError:
            continue
        if decl >= 1:
            has_impl += 1
    rate = (has_impl / total) if total else 0.0
    return {
        "stdlib_light_total": total,
        "stdlib_light_has_impl": has_impl,
        "file_dim_rate": rate,
    }


def count_python_escape(root):
    """全仓扫 .light 里的「引 Python」：返回 (stdlib 计数, 全仓计数, 全仓文件数, 命中清单)。"""
    stdlib_hits = 0
    repo_hits = 0
    repo_files = 0
    repo_detail = []
    stdlib_prefix = os.path.join(root, "stdlib")
    for full in iter_light_files(root):
        # 文件级命中（去重到文件，便于数「文件数」）
        file_has = False
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    if RE_PYTHON_ESCAPE.search(line):
                        repo_hits += 1
                        if not file_has:
                            file_has = True
                            repo_files += 1
                            rel = os.path.relpath(full, root)
                            repo_detail.append("%s:%d" % (rel, i))
                        if full.startswith(stdlib_prefix + os.sep) or full == stdlib_prefix:
                            stdlib_hits += 1
        except OSError:
            continue
    return stdlib_hits, repo_hits, repo_files, repo_detail


def count_lightpub(root):
    lightpub = os.path.join(root, "stdlib", "lightpub")
    n_light = 0
    n_py = 0
    if os.path.isdir(lightpub):
        for fn in os.listdir(lightpub):
            if fn.endswith(".light"):
                n_light += 1
            elif fn.endswith(".py"):
                n_py += 1
    return {"lightpub_light": n_light, "lightpub_py": n_py}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".",
                    help="仓库根目录，默认当前目录（相对或绝对路径）")
    ap.add_argument("--baseline", default=_DEFAULT_BASELINE,
                    help="自举率基线快照路径（对比模式）")
    ap.add_argument("--write-baseline", metavar="PATH",
                    help="把本次自重举率写成新基线并退出")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("[自举率门禁] 仓库根不存在：%s" % args.root)
        return 2

    stdlib = scan_stdlib(args.root)
    stdlib_esc, repo_esc, repo_files, repo_detail = count_python_escape(args.root)
    lightpub = count_lightpub(args.root)

    # —— 行维度口径（明确标注：虚高、不许引用）——
    # 这里只做统计展示，不在门禁里使用。
    line_code = line_decl = line_has_impl_files = 0
    sd = os.path.join(args.root, "stdlib")
    if os.path.isdir(sd):
        for full in iter_light_files(sd):
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    c, d = count_code_decl(fh)
                line_code += c
                line_decl += d
            except OSError:
                continue
    line_dim_rate = (line_decl / line_code) if line_code else 0.0

    print("[自举率门禁] stdlib 文件维度自举率：%d/%d = %.2f%%"
          % (stdlib["stdlib_light_has_impl"], stdlib["stdlib_light_total"],
             stdlib["file_dim_rate"] * 100))
    print("[自举率门禁] （仅供参考、不许引用）行维度 decl/code = %d/%d = %.2f%%"
          % (line_decl, line_code, line_dim_rate * 100))
    print("[自举率门禁] stdlib 「引 Python」逃逸：%d 处" % stdlib_esc)
    print("[自举率门禁] 全仓 .light 「引 Python」：%d 处 / %d 文件（教学示例不算违规）"
          % (repo_esc, repo_files))
    if repo_detail:
        for d in repo_detail[:30]:
            print("       - %s" % d)
    print("[自举率门禁] stdlib/lightpub：.light=%d  .py=%d（仅记录，不设门禁）"
          % (lightpub["lightpub_light"], lightpub["lightpub_py"]))

    if args.write_baseline:
        data = {
            "version": 1,
            "note": "自举率基线快照：文件维度自举率只许升不许降。行维度虚高，不许引用。",
            "file_dim_rate": stdlib["file_dim_rate"],
            "stdlib_light_total": stdlib["stdlib_light_total"],
            "stdlib_light_has_impl": stdlib["stdlib_light_has_impl"],
        }
        with open(args.write_baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("[自举率门禁] 已写入基线 %s（文件维度 %.2f%%）"
              % (args.write_baseline, stdlib["file_dim_rate"] * 100))
        return 0

    baseline = None
    try:
        with open(args.baseline, encoding="utf-8") as fh:
            baseline = json.load(fh)
    except (FileNotFoundError, ValueError):
        baseline = None

    if baseline is None:
        print("[自举率门禁] 找不到基线 %s。首次接入请先 --write-baseline 生成并提交。" % args.baseline)
        return 2

    base_rate = baseline.get("file_dim_rate", 0.0)
    red = False

    if stdlib_esc > 0:
        print("[自举率门禁] 红：stdlib/ 下出现「引 Python」逃逸 %d 处（破零成果被破坏）。" % stdlib_esc)
        red = True
    else:
        print("[自举率门禁] stdlib/ 引 Python 逃逸 = 0，破零成果守住。")

    if stdlib["file_dim_rate"] < base_rate - 1e-9:
        print("[自举率门禁] 红：文件维度自举率 %.2f%% 低于基线 %.2f%%（自举率只许升不许降）。"
              % (stdlib["file_dim_rate"] * 100, base_rate * 100))
        red = True
    elif stdlib["file_dim_rate"] > base_rate + 1e-9:
        print("[自举率门禁] 自举率提升 %.2f%% → %.2f%%（修好一批后请用 --write-baseline 更新基线）。"
              % (base_rate * 100, stdlib["file_dim_rate"] * 100))
    else:
        print("[自举率门禁] 自举率持平基线 %.2f%%。" % (base_rate * 100))

    if red:
        return 1
    print("[自举率门禁] 通过：破零守住、自举率未降。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
