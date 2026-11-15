#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明源码静态分析：L0 核心字密度与辅助量。

口径严格对应 03-judge/rubric.md §4：
  l0_density = L0核心字出现次数 / 标识符出现次数

排除规则：
- 注释（# 到行尾）、字符串字面量（"..." / '...'）不参与分子分母；
- `引 Python: / 引 C: / 引 Go: / 引 MoonBit:` 外语块内部的代码全部排除
  （块引导行本身保留，供 D5 观察）；
- 双字 L1/L2 别名（如果/遍历/否则/返回/...）不计入分子，另记 alias_count。

用法：
  python3 l0_density.py minilog.light
  python3 l0_density.py --json out.json file1.light file2.light
"""
import argparse
import json
import re
import sys

L0 = set("若否当遍跳过返设段类承接配试捕抛终自之并从是且或非真假空导出")
# 常见 L1/L2 双字别名（用于 alias_count 观测，不算 L0）
ALIASES = ("如果", "否则", "或若", "遍历", "返回", "打印", "导入", "段落",
           "接收", "结束", "在", "为", "等于", "不等于", "小于", "大于",
           "令", "定义", "输出", "输入", "整数", "文本", "小数", "列表",
           "字典", "无", "属性", "继承", "父", "己")
ALIAS_SET = set(a for a in ALIASES if len(a) >= 2)
# 真实语法：L4/L3 块以「引 Python:/引 C:/引 SQL:」开始，以「结束引」结束。
# 「出 result」是导出单个变量的语句，不是块尾，不能作为结束标记。
FOREGIN_BLOCK = re.compile(r"^\s*引\s+.{0,20}?[:：]\s*$")
BLOCK_END = re.compile(r"^\s*结束引\s*$")

# 标识符：中文串 或 [A-Za-z_][A-Za-z0-9_]*
IDENT = re.compile(r"[一-鿿]+|[A-Za-z_][A-Za-z0-9_]*")
# 字符串/注释剥离
STRING = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')


def strip_noise(line):
    """去注释与字符串，返回 (有效片段, 是否在串内出现中文)。"""
    # 去注释（简化：# 之后全丢；串内 # 不做复杂处理，对本用途影响极小）
    hash_pos = line.find("#")
    if hash_pos >= 0:
        line = line[:hash_pos]
    return STRING.sub(" ", line)


def analyze(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    l0_count = 0
    ident_count = 0
    alias_count = 0
    alias_detail = {}
    l0_detail = {}
    loc = 0
    max_nesting = 0
    in_foreign = False
    foreign_lines = 0
    gaming_hits = []

    for lineno, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # 外语块边界
        if in_foreign:
            foreign_lines += 1
            if BLOCK_END.match(raw):
                in_foreign = False
                continue
            # 兜底：若无「结束引」，遇到顶格且以光明 L0 关键字开头的行视为块结束
            elif re.match(r"^(段|设|印|遍|当|若|导|类)\b", raw):
                in_foreign = False
                # 该行按光明代码重新处理（落到下方逻辑）
            else:
                continue
        if FOREGIN_BLOCK.match(raw):
            in_foreign = True
            foreign_lines += 1   # 定界符只计入外语块观测，不进分子分母
            continue

        loc += 1
        if re.search(r"提高\s*L0|L0\s*密度|凑\s*密度|gaming", raw):
            gaming_hits.append(lineno)

        code = strip_noise(raw)
        # 缩进层级（按 2 空格或 4 空格估算，中文源码常见 2/4 空格）
        leading = len(raw) - len(raw.lstrip(" \t"))
        if leading:
            nest = leading // 2 + 1
            max_nesting = max(max_nesting, nest)

        for tok in IDENT.findall(code):
            # 中文串可能被切成一整块，需按字拆开判断 L0
            if re.match(r"^[一-鿿]+$", tok):
                # 先尝试双字别名（贪心，长的优先）
                consumed = [False] * len(tok)
                for a in sorted(ALIAS_SET, key=len, reverse=True):
                    start = 0
                    while True:
                        i = tok.find(a, start)
                        if i < 0:
                            break
                        if not any(consumed[i:i + len(a)]):
                            for k in range(i, i + len(a)):
                                consumed[k] = True
                            alias_count += 1
                            alias_detail[a] = alias_detail.get(a, 0) + 1
                        start = i + len(a)
                # 剩余未消费的汉字：单字 L0 或普通标识符字符
                ident_count += 1
                for k, ch in enumerate(tok):
                    if not consumed[k] and ch in L0:
                        l0_count += 1
                        l0_detail[ch] = l0_detail.get(ch, 0) + 1
            else:
                ident_count += 1
                if tok in ALIAS_SET:
                    alias_count += 1
                    alias_detail[tok] = alias_detail.get(tok, 0) + 1

    density = (l0_count / ident_count) if (ident_count and loc > 0) else 0.0
    flags = []
    if loc == 0:
        flags.append("no_light_code")           # 光明侧无可执行语句
    if foreign_lines > max(loc, 1) * 0.5:
        flags.append("python_in_light_suspect") # 外语块占比过半
    if gaming_hits:
        flags.append("gaming_marker")
    return {
        "file": path,
        "loc": loc,
        "l0_token_count": l0_count,
        "identifier_count": ident_count,
        "l0_density": round(density, 4),
        "alias_count": alias_count,
        "alias_detail": dict(sorted(alias_detail.items(),
                                    key=lambda kv: -kv[1])[:12]),
        "l0_detail": dict(sorted(l0_detail.items(), key=lambda kv: -kv[1])),
        "max_nesting": max_nesting,
        "foreign_lines": foreign_lines,
        "gaming_hits": gaming_hits,
        "flags": flags,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", dest="json_out", default=None)
    a = ap.parse_args()
    results = [analyze(p) for p in a.files]
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            f.write("\n")
    for r in results:
        print("%s: loc=%d  l0=%d  ident=%d  density=%.4f  alias=%d  nest=%d  foreign=%d  flags=%s" %
              (r["file"], r["loc"], r["l0_token_count"], r["identifier_count"],
               r["l0_density"], r["alias_count"], r["max_nesting"],
               r["foreign_lines"], ",".join(r["flags"]) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
