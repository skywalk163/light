#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lightharness 工程体 .light → Python↔光明 few-shot 语料抽取（R138-A 流 Y）。

输入：
    lightharness/src/*.light        （240 个工程体，主源）
    lightharness/examples/*.light   （排除 test_ 前缀，44 个，次源）
    light-merge/tools/ai_copilot/sft_dataset.jsonl
    light-merge/docs/lh_corpus_l4.jsonl

输出：
    light-merge/tools/ai_copilot/corpus_harness.jsonl   （≥300 行，幂等覆盖写）

设计要点：
    * 纯标准库（os/re/json/sys/argparse），不调大模型。
    * 抽取对象：顶层/类内「段落」签名 + 完整段落体（最多 MAX_BODY_LINES 行）。
    * Python 配对：从 sft_dataset / lh_corpus_l4 的光明侧 output 里
      用 regex 反查「段落 名」，命中则用其 input 做对照；否则产出 note 结构。
    * 严禁伪造 Python 侧。
    * 排除名单硬编码（与流 Z 协调）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
LIGHT_MERGE_ROOT = os.path.abspath(os.path.join(HERE, ".."))
LIGHTHARNESS_ROOT = os.path.abspath(os.path.join(LIGHT_MERGE_ROOT, "..", "lightharness"))

SRC_DIR = os.path.join(LIGHTHARNESS_ROOT, "src")
EX_DIR = os.path.join(LIGHTHARNESS_ROOT, "examples")

OUT_PATH = os.path.join(LIGHT_MERGE_ROOT, "tools", "ai_copilot", "corpus_harness.jsonl")

SFT_PATH = os.path.join(LIGHT_MERGE_ROOT, "tools", "ai_copilot", "sft_dataset.jsonl")
LH4_PATH = os.path.join(LIGHT_MERGE_ROOT, "docs", "lh_corpus_l4.jsonl")

# 与流 Z 协调：test_ 前缀已统一排除，这里再硬编码兜底
EXCLUDE_EXACT = {
    "test_e2b.light",
    "test_mcp.light",
    "test_mcp_http.light",
    "test_mcp接线.light",
    "test_代码运行时.light",
}

# 惯用法关键字（按优先级排序）
USAGE_KEYWORDS = (
    "尝试", "捕获",
    "读取文件", "写入文件",
    "序列化JSON", "解析JSON",
    "创建目录",
)

# 每条段落体最多保留行数
MAX_BODY_LINES = 30

# 每文件最多产出条数（防止爆量）
MAX_PER_FILE = 2

# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

# 段落签名：行首可有缩进，形式 `段落 名(参数):` 或 `段落 名:`
RE_PARA = re.compile(r"^(?P<indent>[ \t]*)段落\s+(?P<name>[^\s(:]+)\s*(?P<params>\([^)]*\))?\s*:\s*(?P<tail>.*)$")

# 类签名
RE_CLASS = re.compile(r"^[ \t]*类\s+(?P<name>[^\s:]+)\s*:")

# 导出行：`导出 名`
RE_EXPORT = re.compile(r"^[ \t]*导出\s+(?P<name>\S.*?)\s*$")

# 从既有语料 output（光明侧）里反查段落名
RE_OUTPUT_PARA = re.compile(r"段落\s+([^\s(:]+)\s*\(")

# 敏感信息
RE_SENSITIVE = re.compile(
    r"(sk-[A-Za-z0-9]{16,}"
    r"|ghp_[A-Za-z0-9]{16,}"
    r"|AKIA[A-Z0-9]{12,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|Bearer\s+[A-Za-z0-9._-]{20,}"
    r"|(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3})"
)

# ---------------------------------------------------------------------------
# Python 侧配对索引
# ---------------------------------------------------------------------------


def build_python_index() -> "OrderedDict[str, dict]":
    """扫描 sft_dataset.jsonl / lh_corpus_l4.jsonl，
    返回 {段落名: {"python": input, "category": category, "source": 来源}}。

    同名段落多次出现时取第一条（教学体稳定优先）。
    """
    index: "OrderedDict[str, dict]" = OrderedDict()
    for path, tag in ((SFT_PATH, "sft_dataset"), (LH4_PATH, "lh_corpus_l4")):
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                out_text = obj.get("output") or ""
                m = RE_OUTPUT_PARA.search(out_text)
                if not m:
                    continue
                name = m.group(1)
                if name in index:
                    continue
                index[name] = {
                    "python": obj.get("input", ""),
                    "category": obj.get("category", ""),
                    "source": tag,
                    "instruction": obj.get("instruction", ""),
                }
    return index


# ---------------------------------------------------------------------------
# .light 文件解析
# ---------------------------------------------------------------------------


def read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read().splitlines()


def paragraph_spans(lines: List[str]) -> List[Tuple[int, int, str, str, str]]:
    """返回 [(start_idx, end_idx_exclusive, name, params, indent_str), ...]。

    end_idx 为段落体结束后第一个非缩进行的下标（即段落体 [start_idx+1, end_idx)）。
    段落体 = 签名行之后、缩进严格大于签名行缩进的连续行。
    """
    def indent_width_of(s: str) -> int:
        """前导空格宽度（tab 按 4 展开）。"""
        expanded = s.expandtabs(4)
        return len(expanded) - len(expanded.lstrip())

    spans: List[Tuple[int, int, str, str, str]] = []
    for i, raw in enumerate(lines):
        m = RE_PARA.match(raw)
        if not m:
            continue
        indent = m.group("indent")
        indent_width = len(indent.expandtabs(4))
        name = m.group("name")
        params = m.group("params") or ""
        # 找段落体结束
        j = i + 1
        while j < len(lines):
            ln = lines[j]
            if ln.strip() == "":
                j += 1
                continue
            cur_indent = indent_width_of(ln)
            if cur_indent <= indent_width:
                break
            j += 1
        spans.append((i, j, name, params, indent))
    return spans


def preceding_comments(lines: List[str], idx: int) -> List[str]:
    """返回 idx 行上方紧邻的连续注释块。

    规则：
      * 遇到 `#` 注释行 → 纳入；
      * 遇到空行 → 最多跳过 1 个，再往上若仍是注释则继续；
      * 遇到任何代码行（非注释、非空）→ 立即停（防止把前一个段落的代码体吞进来）。
    """
    out: List[str] = []
    k = idx - 1
    skipped_blank = False
    while k >= 0:
        s = lines[k].strip()
        if s.startswith("#"):
            out.append(lines[k])
            k -= 1
            skipped_blank = False
        elif s == "":
            if skipped_blank:
                break
            skipped_blank = True
            k -= 1
        else:
            # 遇到代码行（可能是上一个段落体/上一个段落签名/赋值/导入），立即停
            break
    out.reverse()
    return out


# 块开头关键字：这些行以 `:` 结尾时，代表后续有缩进体，不能作为截断的最后一行
BLOCK_OPENERS = (
    "如果", "否则", "当", "遍历", "尝试", "捕获", "对于",
    "段落", "类", "从", "导入", "全局",
)


def trim_body_safely(body_lines: List[str], max_lines: int) -> Tuple[List[str], bool]:
    """把段体截到 max_lines 行内；若末行是块开头则回退，避免未闭合语法。

    返回 (新段体, 是否发生了截断)。
    """
    if len(body_lines) <= max_lines:
        return body_lines, False
    trimmed = body_lines[:max_lines]
    # 回退：从末尾往前删，直到最后一行不是块开头
    while trimmed:
        last = trimmed[-1].strip()
        if not last:
            trimmed.pop()
            continue
        # 块开头判定：以 `:` 结尾，且以块关键字起头
        if last.endswith(":") and any(last.startswith(k) for k in BLOCK_OPENERS):
            trimmed.pop()
            continue
        break
    return trimmed, True


def collect_exports(lines: List[str]) -> List[str]:
    out = []
    for ln in lines:
        m = RE_EXPORT.match(ln)
        if m:
            out.append(m.group("name"))
    return out


def has_usage_keyword(body: str) -> bool:
    return any(k in body for k in USAGE_KEYWORDS)


def infer_category(body: str, exports: List[str]) -> str:
    if "尝试" in body or "捕获" in body:
        return "异常映射"
    if "读取文件" in body or "写入文件" in body or "创建目录" in body or "文件存在" in body:
        return "工程-文件"
    if "序列化JSON" in body or "解析JSON" in body:
        return "工程-JSON"
    if "异步" in body or "并发" in body or "任务" in body or "协程" in body:
        return "工程-并发"
    if any(k in body for k in ("HTTP", "http", "URL", "请求", "客户端", "网页", "服务器", "API")):
        return "网络请求"
    if exports:
        return "工程-模块导出"
    return "工程-其他"


# ---------------------------------------------------------------------------
# 抽取逻辑
# ---------------------------------------------------------------------------


def relative_source(abs_path: str) -> str:
    """输出相对路径，形如 lightharness/src/e2b客户端.light。"""
    abs_path = os.path.normpath(abs_path)
    lh = os.path.normpath(LIGHTHARNESS_ROOT)
    if abs_path.startswith(lh + os.sep):
        return "lightharness/" + os.path.relpath(abs_path, LIGHTHARNESS_ROOT).replace("\\", "/")
    return os.path.basename(abs_path)


def safe_for_output(text: str) -> bool:
    """敏感信息过滤。"""
    return not RE_SENSITIVE.search(text)


def build_note_light(name: str, params: str, comments: List[str], body: List[str]) -> Tuple[str, bool]:
    """构造光明侧片段：注释块 + 签名行 + 段体（截到 MAX_BODY_LINES，安全回退）。

    返回 (light_text, 是否被截断)。
    """
    head = []
    if comments:
        head.extend(comments)
    sig = f"段落 {name}{params}:"
    head.append(sig)
    body_lines, truncated = trim_body_safely(body, MAX_BODY_LINES)
    head.extend(body_lines)
    return "\n".join(head).rstrip(), truncated


def extract_from_file(path: str, py_index: "OrderedDict[str, dict]") -> List[dict]:
    """对单个 .light 文件抽取 0..MAX_PER_FILE 条。"""
    lines = read_lines(path)
    spans = paragraph_spans(lines)
    exports = collect_exports(lines)
    src_tag = relative_source(path)

    rows: List[dict] = []

    # 按优先级选段落：含惯用法关键字 > 顶层 > 类内
    def body_of(span) -> List[str]:
        s, e, name, params, indent = span
        # 从 s 到 e 的所有原始行（不含签名行本身，后面 build_note_light 自己加）
        return lines[s + 1 : e]

    def body_text(span) -> str:
        return "\n".join(body_of(span))

    # 候选列表：带评分
    scored: List[Tuple[int, Tuple[int, int, str, str, str]]] = []
    for sp in spans:
        s, e, name, params, indent = sp
        score = 0
        # 含惯用法关键字优先
        bt = body_text(sp)
        if has_usage_keyword(bt):
            score += 100
        # 顶层（无缩进）优先
        if indent == "":
            score += 20
        # 类内方法（2 空格缩进）次优先
        elif len(indent.expandtabs(4)) == 2:
            score += 10
        # 段体非空、不太短
        body_len = e - s - 1
        if 3 <= body_len <= 25:
            score += 5
        scored.append((score, sp))

    scored.sort(key=lambda x: -x[0])

    picked_names = set()
    for score, sp in scored:
        if len(rows) >= MAX_PER_FILE:
            break
        s, e, name, params, indent = sp
        if name in picked_names:
            continue
        comments = preceding_comments(lines, s)
        body = body_of(sp)
        light_text, truncated = build_note_light(name, params, comments, body)

        if not safe_for_output(light_text):
            continue

        category = infer_category(light_text, exports)

        # Python 配对？
        py_hit = py_index.get(name)
        if py_hit and py_hit.get("python"):
            row = OrderedDict()
            row["instruction"] = py_hit.get("instruction") or "将以下Python代码翻译为段言v3.2代码。"
            row["input"] = py_hit["python"]
            row["output"] = light_text
            row["category"] = category or py_hit.get("category", "")
            row["source"] = src_tag
            row["_paired_from"] = py_hit.get("source", "")
        else:
            # note 结构
            # 从注释块构造中文 note
            note_bits = []
            if comments:
                # 去掉注释符
                cleaned = [c.lstrip("# ").strip() for c in comments if c.strip()]
                cleaned = [c for c in cleaned if c]
                if cleaned:
                    note_bits.append("；".join(cleaned[:3]))
            note_bits.append(f"lightharness 工程体段落「{name}{params}」签名/实现")
            if truncated:
                note_bits.append("（段体较长，仅保留前若干行；完整实现见源文件）")
            if exports:
                note_bits.append(f"该文件对外导出：{', '.join(exports[:6])}")
            row = OrderedDict()
            row["light"] = light_text
            row["note"] = "。".join(note_bits)
            row["source"] = src_tag
            row["category"] = category
        rows.append(row)
        picked_names.add(name)

    # 若还没凑到条数，且文件有 exports，补一条导出清单
    if len(rows) < MAX_PER_FILE and exports:
        export_text = "\n".join(f"导出 {n}" for n in exports[:12])
        if safe_for_output(export_text):
            row = OrderedDict()
            row["light"] = export_text
            row["note"] = (
                f"{src_tag} 模块对外导出清单（共 {len(exports)} 个），"
                "供小模型认识 lightharness 模块的公共 API 命名习惯。"
            )
            row["source"] = src_tag
            row["category"] = "工程-模块导出"
            rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# 迭代输入文件
# ---------------------------------------------------------------------------


def iter_light_files(d: str):
    if not os.path.isdir(d):
        return
    for base in sorted(os.listdir(d)):
        if not base.endswith(".light"):
            continue
        if base in EXCLUDE_EXACT:
            continue
        if base.startswith("test_"):
            continue
        yield os.path.join(d, base), base


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="只打印统计，不写文件")
    ap.add_argument("--limit", type=int, default=0, help="调试用：最多处理 N 个文件")
    ap.add_argument("--out", default=OUT_PATH, help="输出 JSONL 路径")
    args = ap.parse_args(argv)

    print(f"[i] 建立 Python 配对索引: {SFT_PATH} / {LH4_PATH}")
    py_index = build_python_index()
    print(f"[i] 索引段落数: {len(py_index)}")

    all_rows: List[dict] = []
    file_count = 0
    paired = 0
    noted = 0

    for base_dir in (SRC_DIR, EX_DIR):
        tag = "src" if base_dir == SRC_DIR else "examples"
        for path, base in iter_light_files(base_dir):
            if args.limit and file_count >= args.limit:
                break
            rows = extract_from_file(path, py_index)
            for r in rows:
                if "output" in r and "input" in r:
                    paired += 1
                else:
                    noted += 1
                all_rows.append(r)
            file_count += 1
        if args.limit and file_count >= args.limit:
            break

    print(f"[i] 处理文件数: {file_count}")
    print(f"[i] 对照结构(有Python侧): {paired}")
    print(f"[i] note结构(无Python侧): {noted}")
    print(f"[i] 总条数: {len(all_rows)}")

    if args.dry_run:
        print("[dry-run] 未写入文件")
        return 0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[ok] 写入 {len(all_rows)} 条 → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
