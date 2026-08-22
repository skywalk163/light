# -*- coding: utf-8 -*-
"""假测试门禁：只拦「新增」的假绿断言，不要求存量清零。

背景（第三轮 D3-2）：
  三轮下来最大的一类发现是「某个东西看着做了，其实没验证」。第二轮写了三条禁令
  （`第二轮总纲` §5），但禁令只是文档里一句话，没兜住——`tests/test_agent_loop_light.py`
  的 `TestMaxRounds` 用 `assert len(events) <= 3` 空转通过就是活案例。
  本脚本把禁令变成能自动拦住的门禁。

设计原则（与 `check_regression.py` 同源思路，但这是**静态扫描**、零运行时依赖）：
  - 纯正则扫 `tests/` 文本，**不起子进程、不 import 被测代码**，必须 < 5s 跑完。
  - 现有违规写进基线快照 `assert_quality_baseline.json`；**新增即红，减少要求更新基线**。
  - 一次性清零不现实（全仓量大），但必须「止血」：存量允许存在、只许减不许增。
  - 违规报告给 `file:line` + 违规类型 + 一句「为什么这是假绿」。

扫描的三类模式（与 `第三轮留档/假测试普查清单.md` 口径一致）：
  1) 字符串断言式：`assert '<x>' in py_code|ir|c_code|source|产物`
     —— 测的是编译器/产物输出的字面量，不是行为。
  2) 上界断言式：`assert len(...) <= N`（集合为空时恒真，最隐蔽）
     以及 `assert len(...) >= 0`（长度恒非负，恒真）。
  3) 成败都算通过：`assert returncode in [0, 1]` 这类。

用法：
  # 对比模式（CI 用，新增即红）
  python3 tools/ci/assert_quality.py --root tests
  # 生成/刷新基线（修好一批后手工执行并提交）
  python3 tools/ci/assert_quality.py --root tests --write-baseline tools/ci/assert_quality_baseline.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tokenize


# ── 三类模式的静态判定 ────────────────────────────────────────────────────────
# 1) 字符串断言式：只拦「产物字面量」目标，避免把正常的 `in code` 也误伤成海量基线。
_STR_TARGETS = r"(?:py_code|pycode|ir|c_code|source|产物)"
RE_STRING_ASSERT = re.compile(
    r"assert\s+['\"][^'\"]*['\"]\s+in\s+" + _STR_TARGETS + r"\b"
)
# 2a) 上界断言式：len(...) <= N（集合空时恒真）
RE_UPPER_BOUND = re.compile(r"assert\s+len\([^()]*\)\s*<=\s*\d+")
# 2b) 恒真断言式：len(...) >= 0（长度恒非负）
RE_TRIVIAL_GE = re.compile(r"assert\s+len\([^()]*\)\s*>=\s*0\b")
# 3) 成败都算通过：returncode in [...]
RE_RETURNCODE_IN = re.compile(r"assert\s+returncode\s+in\s*\[")

CATEGORIES = {
    "string-assert": ("字符串断言式", RE_STRING_ASSERT,
        "测的是编译器/产物输出的字面量，不是行为；产物变了才发现的洞永远发现不了。"),
    "upper-bound": ("上界断言式", RE_UPPER_BOUND,
        "len(...) <= N：集合为空时恒真，是最隐蔽的假绿（事件总线案例即此形态）。"),
    "trivial-ge0": ("恒真断言式", RE_TRIVIAL_GE,
        "len(...) >= 0：长度恒非负，这条断言永远为真，零信号。"),
    "returncode-in": ("成败都算通过", RE_RETURNCODE_IN,
        "returncode in [0,1]：成功失败都算通过，等于没测。"),
}

# 单条合并正则：每行只做一次 .search，命中后再细分到具体类别（匹配极少，代价可忽略）。
RE_MASTER = re.compile(
    r"assert\s+(?:"
    r"['\"][^'\"]*['\"]\s+in\s+" + _STR_TARGETS + r"\b"
    r"|len\([^()]*\)\s*<=\s*\d+"
    r"|len\([^()]*\)\s*>=\s*0\b"
    r")"
    r"|assert\s+returncode\s+in\s*\["
)

_DEFAULT_BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "assert_quality_baseline.json")


def _prose_lines(full):
    """返回「不该被当代码看」的行号集合：注释行 + 多行字符串（含 docstring）内部的行。

    为什么需要：正文里引用一条假绿写法当反面教材是完全正当的——
    tests/test_generics_c3.py 的模块 docstring 里写着「不做 `assert 'T' in py_code`
    那种字符串断言式假测试」，纯正则会把这句**说明文字**当成违规命中，逼着人把一条
    并不存在的违规写进基线。用 tokenize 把注释与多行字符串的行捞出来跳过。
    单行字符串不跳（那种把假绿写法当数据放在一行里的情况极少，且真要出现也该看一眼）。
    """
    prose = set()
    try:
        with open(full, "rb") as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type == tokenize.COMMENT:
                    prose.add(tok.start[0])
                elif tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                    for ln in range(tok.start[0], tok.end[0] + 1):
                        prose.add(ln)
    except (OSError, tokenize.TokenError, SyntaxError, IndentationError,
            UnicodeDecodeError):
        # 词法都过不去的文件不做豁免：宁可多报一条，也不因为解析失败静默放过。
        return set()
    return prose


def scan_tree(root):
    """返回 {category: [ {file, line, text}, ... ]} 与总数。"""
    found = {cat: [] for cat in CATEGORIES}
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过的目录：缓存、虚拟环境、被排除的基线/文档
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", ".venv", "node_modules",
                                    ".light_cache", ".ml_cache", "docs-site")]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            if fn == "assert_quality.py":
                continue  # 不扫自己
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            prose = None
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        # 廉价预筛：绝大多数行不含 'assert'/'returncode'，直接跳过正则。
                        if "assert" not in line and "returncode" not in line:
                            continue
                        stripped = line.rstrip("\n")
                        m = RE_MASTER.search(stripped)
                        if not m:
                            continue
                        # 命中了才付 tokenize 的代价，且每个文件只付一次
                        if prose is None:
                            prose = _prose_lines(full)
                        if i in prose:
                            continue
                        # 命中后细分到具体类别（在短字符串上做，代价极小）
                        for cat, (_, rx, _) in CATEGORIES.items():
                            if rx.search(stripped):
                                found[cat].append({"file": rel, "line": i, "text": stripped.strip()})
                                break
            except OSError:
                continue
    return found



def load_baseline(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, ValueError):
        return None
    return data


def violation_key(v):
    return "%s:%d:%s" % (v["file"], v["line"], v["cat"] if "cat" in v else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="tests",
                    help="要扫描的根目录，默认 tests（相对仓库根或绝对路径）")
    ap.add_argument("--baseline", default=_DEFAULT_BASELINE,
                    help="基线快照路径（对比模式）")
    ap.add_argument("--write-baseline", metavar="PATH",
                    help="把本次结果写成新基线并退出")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("[假测试门禁] 扫描根不存在：%s" % args.root)
        return 2

    found = scan_tree(args.root)
    # 给每条打上分类标签，便于聚合
    tagged = []
    for cat, items in found.items():
        for it in items:
            it = dict(it)
            it["cat"] = cat
            tagged.append(it)

    total = len(tagged)
    print("[假测试门禁] 扫描 %s：命中 %d 条违规" % (args.root, total))
    for cat, (label, _, _) in CATEGORIES.items():
        n = len(found[cat])
        if n:
            print("       %-14s %3d 条" % (label, n))

    if args.write_baseline:
        data = {
            "version": 1,
            "note": "假测试门禁基线快照：本仓库当前的既有违规。新增即红；修好一批后重新生成并提交本文件。",
            "scanned_root": args.root,
            "categories": {c: CATEGORIES[c][0] for c in CATEGORIES},
            "violations": [
                {"file": v["file"], "line": v["line"], "cat": v["cat"], "text": v["text"]}
                for v in sorted(tagged, key=lambda x: (x["file"], x["line"]))
            ],
        }
        with open(args.write_baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("[假测试门禁] 已写入基线 %s（%d 条）" % (args.write_baseline, total))
        return 0

    baseline = load_baseline(args.baseline)
    if baseline is None:
        print("[假测试门禁] 找不到基线 %s。首次接入请先 --write-baseline 生成并提交。" % args.baseline)
        return 2

    base_keys = {violation_key(v) for v in baseline.get("violations", [])}
    cur_keys = {violation_key(v) for v in tagged}
    new_violations = [v for v in tagged if violation_key(v) not in base_keys]

    # 逐条打印存量（简略）与新违规（详细）
    if new_violations:
        print("[假测试门禁] 新增违规 %d 条（视为回归，闸门拦下）：" % len(new_violations))
        for v in sorted(new_violations, key=lambda x: (x["file"], x["line"])):
            label, _, why = CATEGORIES[v["cat"]]
            print("       ! %s:%d  [%s] %s" % (v["file"], v["line"], label, v["text"][:80]))
            print("           为什么是假绿：%s" % why)
    else:
        print("[假测试门禁] 无新增违规。")

    removed = len(base_keys - cur_keys)
    if removed:
        print("[假测试门禁] 相比基线已减少 %d 条（修好了就更新基线：--write-baseline）：" % removed)

    if new_violations:
        print("[假测试门禁] 红：出现了基线条目之外的新增假绿断言。")
        return 1
    if total > len(base_keys):
        print("[假测试门禁] 红：违规总数 %d 超过基线 %d（可能基线被改动绕过）。" % (total, len(base_keys)))
        return 1

    print("[假测试门禁] 通过：存量冻结、无新增。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
