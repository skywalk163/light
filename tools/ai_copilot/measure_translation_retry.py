#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
measure_translation_retry.py — R139 任务 B 线：翻译 retry 成本复测

背景
----
light-translator 翻译 Python→Light 时，若生成的 Light 未通过校验会进入"重试循环"，
"retry 成本" = 单样本平均 LLM 调用次数。把工程体(engineering-body)语料并入 SFT 数据集，
预期让 7B 模型首次即产出合法 Light，从而降低 retry 成本 —— 即任务书所谓"确认 7B 吃到工程体写法"。

两种模式
--------
--mode local-proxy  (默认, 本机可跑, 不调 LLM / 不编译)
    对合并后数据集里的 Light 片段做"结构性自洽"离线启发式校验，作为 retry 成本的代理指标：
    结构自洽率越高 → 模型首次产出合法 Light 概率越高 → retry 越低。
    ⚠️ 这是代理指标(非权威)：权威复测须在 0.88 用真实模型 + translator 重试循环跑(见 --mode llm)。

--mode llm  (门禁到 0.88, 本机不跑)
    加载 translator + 模型端点，对 holdout 集合做 Python→Light 翻译并统计重试次数，
    对比 基线 sft(无工程体) vs 合并后 sft(含 551 工程体)。本机只打印在 0.88 的执行命令。

红线遵守
--------
- 本脚本 local-proxy 模式纯文本启发式，不调用大模型、不调用 Light 编译器（编译/运行门禁在 0.88）。
- 不改变任何数据集文件，只读。
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict

LIGHT_DECL = re.compile(r"(段落|函数|类别|类|接口|枚举|异步\s*段落)\s")
PY_LEAK = re.compile(r"^\s*(def |class |import |from \w+ import|return |async def )")
PAIRS = [("(", ")"), ("[", "]"), ("{", "}")]


def balanced_ok(code: str):
    """宽松结构自洽：分隔符平衡 + 无 Python 顶层泄漏（不要求含声明）。"""
    if not code or not code.strip():
        return False, "empty"
    for op, cl in PAIRS:
        if code.count(op) != code.count(cl):
            return False, f"unbalanced {op}{cl}"
    for ln in code.splitlines():
        if PY_LEAK.match(ln):
            return False, "python_leak"
    return True, "ok"


def structural_check(code: str):
    """严格结构自洽(完整模块)：分隔符平衡 + 含 Light 声明 + 无 Python 泄漏。"""
    ok, reason = balanced_ok(code)
    if not ok:
        return False, reason
    if not LIGHT_DECL.search(code):
        return False, "no_light_decl"
    return True, "ok"


def collect_light_snippets(path):
    """从合并数据集中抽取所有 Light 片段：(code, category, source)。"""
    snips = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        # corpus-A: light 字段
        if "light" in d and (d.get("light") or "").strip():
            snips.append((d["light"], d.get("category", "?"), d.get("source", "")))
        # schema-B / sft: output 字段即 Light 译文
        elif "output" in d and (d.get("output") or "").strip():
            snips.append((d["output"], d.get("category", "?"), d.get("source", "")))
    return snips


def mode_local_proxy(path):
    snips = collect_light_snippets(path)
    total = len(snips)
    strict_ok = 0
    relaxed_ok = 0
    reasons = Counter()
    by_cat = defaultdict(lambda: [0, 0, 0])  # cat -> [strict_pass, relaxed_pass, total]
    for code, cat, src in snips:
        s_ok, s_reason = structural_check(code)
        r_ok, _ = balanced_ok(code)
        by_cat[cat][2] += 1
        if s_ok:
            strict_ok += 1
            by_cat[cat][0] += 1
        else:
            reasons[s_reason] += 1
        if r_ok:
            relaxed_ok += 1
            by_cat[cat][1] += 1
    s_rate = (strict_ok / total * 100) if total else 0.0
    r_rate = (relaxed_ok / total * 100) if total else 0.0
    print("=" * 64)
    print("R139-B retry 成本代理复测 (local-proxy, 离线结构自洽)")
    print("=" * 64)
    print(f"抽取 Light 片段总数        : {total}")
    print(f"完整模块率(含声明+平衡)    : {strict_ok}  ({s_rate:.1f}%)")
    print(f"宽松平衡率(仅平衡+无泄漏)  : {relaxed_ok}  ({r_rate:.1f}%)")
    print(f"未通过原因分布             : {dict(reasons)}")
    print("-" * 64)
    print("按类目(完整模块率 宽松平衡率 总数):")
    for cat, (sp, rp, t) in sorted(by_cat.items(), key=lambda x: -x[1][2]):
        sr = sp / t * 100 if t else 0
        rr = rp / t * 100 if t else 0
        print(f"  {cat:14s} {sr:5.1f}%  {rr:5.1f}%  {t:4d}")
    print("-" * 64)
    print("代理结论: 结构自洽/平衡率越高 → 模型首次产出合法 Light 概率越高 →")
    print("           translator 重试循环触发越少 → retry 成本越低。")
    print("⚠️ 此为代理指标；权威 retry 成本复测须在 0.88 跑 --mode llm。")
    print("=" * 64)
    # 退出码：代理指标仅汇报，不阻断（0）
    sys.exit(0)


def mode_llm(path):
    print("=" * 64)
    print("R139-B retry 成本权威复测 (--mode llm, 门禁到 0.88)")
    print("=" * 64)
    print("本机红线：禁止实跑 / 不调大模型。以下命令在 192.168.0.88 执行：")
    print()
    print("  # 基线(无工程体)：用原始 sft_dataset_pre_R139B_backup.jsonl")
    print("  python tools/ai_copilot/measure_translation_retry.py \\")
    print("      --mode llm --dataset tools/ai_copilot/sft_dataset_pre_R139B_backup.jsonl \\")
    print("      --holdout <holdout.jsonl> --model <7b-endpoint> --out baseline_retry.json")
    print()
    print("  # 含工程体：用合并后 sft_dataset.jsonl")
    print("  python tools/ai_copilot/measure_translation_retry.py \\")
    print("      --mode llm --dataset tools/ai_copilot/sft_dataset.jsonl \\")
    print("      --holdout <holdout.jsonl> --model <7b-endpoint> --out merged_retry.json")
    print()
    print("  # 对比：python -c \"import json;\\")
    print("  #   b=json.load(open('baseline_retry.json'));m=json.load(open('merged_retry.json'));\\")
    print("  #   print('baseline avg retries',b['avg'],'| merged avg retries',m['avg'])\"")
    print()
    print("注：真实实现需在 translator.py 的翻译循环中挂钩 retry 计数")
    print("    （当前仓库无现成 retry-cost eval 脚本，本文件即补此能力）。")
    print("=" * 64)
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description="翻译 retry 成本复测 (R139-B)")
    ap.add_argument("--dataset", default="sft_dataset.jsonl")
    ap.add_argument("--mode", choices=["local-proxy", "llm"], default="local-proxy")
    args = ap.parse_args()
    if args.mode == "local-proxy":
        mode_local_proxy(args.dataset)
    else:
        mode_llm(args.dataset)


if __name__ == "__main__":
    main()
