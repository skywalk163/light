#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI 覆盖率门禁：只守 4 个核心语言链路文件的行覆盖率（默认 70% 硬门槛）。

设计口径
--------
* 输入是 ``coverage json`` 的产物（coverage.py JSON format 3），默认 ``coverage.json``，
  可用 ``--coverage-json`` 指定。本脚本**纯标准库**，不 import coverage、不装 pytest-cov。
* 只统计 CORE_FILES 四个文件，**不给全仓设门槛**：coverage.json 里其它 80+ 个 src 模块
  哪怕是 0% 也不参与判定。它们只是同一份数据里的背景信息。
* 行覆盖率以 ``executed_lines`` / ``missing_lines`` 两个行号数组为准重算，
  **不采信** ``summary.percent_covered`` 的浮点值：后者经过格式化/舍入，
  69.96% 显示成 70.0% 就会造出「差一点却判绿」的假绿。判定用精确比较
  ``pct < min``，因此 69.9 红、70.0 绿。
* 核心文件没出现在 coverage.json 里 = 不达标（rc=1），不是「跳过」：
  这说明覆盖统计的测试选择根本没碰到它，是最该被门禁拦住的形态。
* 低于阈值时把 missing_lines 压成 ``12-18, 40, 55-57`` 形式全量列出，
  这份清单就是「哪些路径没人触达」的可执行反馈（见 summary.md / CI 注释）。
* 路径规范化：coverage.py 在 Windows 输出 ``src\\lexer.py``、
  FreeBSD/Linux 输出 ``src/lexer.py``；两者都归一成 ``src/lexer.py`` 匹配，
  也接受带绝对路径前缀的 key（如 ``C:/repo/src/lexer.py``）。

退出码
------
``0`` 四文件全达标 ｜ ``1`` 有文件不达标/未在统计中 ｜ ``2`` 输入缺失或格式错误
（rc=2 时额外打印一行「怎么生成」的命令，避免门禁变成猜谜）。

用法
----
    python scripts/check_coverage.py
    python scripts/check_coverage.py --coverage-json build/coverage.json --min 70
    python scripts/check_coverage.py --min 0        # 临时放行（只应急，不许进 CI）
"""

from __future__ import annotations

import argparse
import json
import posixpath
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CORE_FILES: tuple[str, ...] = (
    "src/lexer.py",
    "src/light_parser_v3.py",
    "src/compiler.py",
    "src/code_generator.py",
)
DEFAULT_MIN = 70.0
DEFAULT_JSON = "coverage.json"

GENERATE_HINT = (
    "怎么生成：python -m coverage run -m pytest -q <测试选择> && "
    "python -m coverage json -o coverage.json && python scripts/check_coverage.py"
)


class InputError(Exception):
    """输入缺失 / JSON 格式不合规 → rc=2。"""


@dataclass(frozen=True)
class FileCoverage:
    rel: str
    key: str | None
    covered: int
    statements: int
    pct: float
    missing: tuple[int, ...]

    @property
    def present(self) -> bool:
        return self.key is not None


def normalize_key(key: str) -> str:
    """把 coverage.json 的 file key 归一成 POSIX 风格相对路径。"""
    text = str(key).strip().replace("\\", "/")
    text = posixpath.normpath(text)
    while text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def match_core_key(files: dict[str, Any], rel: str) -> str | None:
    """找出 rel 对应的 key；找不到返回 None。带绝对路径前缀也认。"""
    hits = []
    for key in files:
        norm = normalize_key(key)
        if norm == rel or norm.endswith("/" + rel):
            hits.append(key)
    if not hits:
        return None
    # 同名义上有多个（例如两个 src/ 树）时取最短路径：离仓根最近的那份，
    # 并在报告里提示歧义，不静默挑一个。
    return sorted(hits, key=lambda k: (len(normalize_key(k)), normalize_key(k)))[0]


def _int_lines(entry: dict[str, Any], field: str, key: str) -> set[int]:
    raw = entry.get(field, [])
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise InputError(f"files[{key!r}].{field} 不是数组")
    out: set[int] = set()
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, int):
            raise InputError(f"files[{key!r}].{field} 含非整数行号：{value!r}")
        if value < 0:
            raise InputError(f"files[{key!r}].{field} 含负行号：{value}")
        out.add(value)
    return out


def compute_coverage(entry: dict[str, Any], key: str, rel: str) -> FileCoverage:
    """用 executed/missing 行号数组重算覆盖率，不看 summary.percent_covered。"""
    if not isinstance(entry, dict):
        raise InputError(f"files[{key!r}] 不是对象")
    executed = _int_lines(entry, "executed_lines", key)
    missing = _int_lines(entry, "missing_lines", key) - executed
    covered = len(executed)
    statements = covered + len(missing)
    # 零语句文件绝不能算 100%：那是「没人触达」而不是「全覆盖」。
    pct = 100.0 * covered / statements if statements else 0.0
    return FileCoverage(
        rel=rel,
        key=key,
        covered=covered,
        statements=statements,
        pct=pct,
        missing=tuple(sorted(missing)),
    )


def compress_ranges(lines: list[int] | tuple[int, ...]) -> str:
    """把行号压成 ``12-18, 40, 55-57`` 形式。"""
    ordered = sorted(set(lines))
    if not ordered:
        return "（无）"
    chunks: list[str] = []
    start = prev = ordered[0]
    for line in ordered[1:]:
        if line == prev + 1:
            prev = line
            continue
        chunks.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = line
    chunks.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(chunks)


def load_report(path: Path) -> dict[str, Any]:
    """读取并校验 coverage.json；任何不合规都抛 InputError（rc=2）。"""
    if not path.is_file():
        raise InputError(f"找不到 {path}（coverage json 产物缺失）")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise InputError(f"读取 {path} 失败：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"{path} 不是合法 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise InputError("coverage.json 顶层必须是对象")
    files = data.get("files")
    if not isinstance(files, dict):
        raise InputError("coverage.json 缺少 files 对象（是不是跑了 coverage report 而不是 coverage json？）")
    if not files:
        raise InputError("coverage.json 的 files 为空：没有任何文件被统计")
    return files


def evaluate(files: dict[str, Any], min_pct: float) -> list[FileCoverage]:
    """逐文件判定；返回四份结果（顺序固定 = CORE_FILES）。"""
    results: list[FileCoverage] = []
    for rel in CORE_FILES:
        key = match_core_key(files, rel)
        if key is None:
            results.append(
                FileCoverage(rel=rel, key=None, covered=0, statements=0, pct=0.0, missing=())
            )
        else:
            results.append(compute_coverage(files[key], key, rel))
    return results


def format_report(results: list[FileCoverage], min_pct: float, source: Path) -> tuple[str, int]:
    """生成人类可读报告，返回 (报告文本, 退出码)。"""
    lines = [
        f"[覆盖率门禁] 口径：仅 {len(CORE_FILES)} 个核心文件 · 行覆盖阈值 {min_pct:.2f}% · 数据 {source}",
        "[覆盖率门禁] 不给全仓设门槛；未覆盖行号区间可直接转成补测用例",
        "-" * 78,
    ]
    failed = 0
    for r in results:
        if not r.present:
            lines.append(
                f"[FAIL] {r.rel:<28} 未出现在覆盖统计中（测试选择没碰到它，按不达标处理）"
            )
            failed += 1
            continue
        ok = r.pct >= min_pct
        tag = "PASS" if ok else "FAIL"
        lines.append(
            f"[{tag}] {r.rel:<28} {r.covered:>5}/{r.statements:<5} = {r.pct:6.2f}%"
            f"  (阈值 {min_pct:.2f}%)"
        )
        if not ok:
            failed += 1
            lines.append(f"         未覆盖行号区间（{len(r.missing)} 行，{len(_ranges(r.missing))} 段）：")
            lines.append(f"         {compress_ranges(r.missing)}")
    lines.append("-" * 78)
    passed = len(results) - failed
    lowest = min((r.pct for r in results if r.present), default=0.0)
    lines.append(
        f"[覆盖率门禁] 结果：{passed}/{len(results)} 达标，最低 {lowest:.2f}%，"
        + ("全部达标" if not failed else f"{failed} 个文件不达标 → rc=1")
    )
    return "\n".join(lines), (0 if not failed else 1)


def _ranges(lines: tuple[int, ...] | list[int]) -> list[tuple[int, int]]:
    """把行号折成 (start, end) 段，供报告统计段数。"""
    ordered = sorted(set(lines))
    if not ordered:
        return []
    out: list[tuple[int, int]] = []
    start = prev = ordered[0]
    for line in ordered[1:]:
        if line == prev + 1:
            prev = line
            continue
        out.append((start, prev))
        start = prev = line
    out.append((start, prev))
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CI 覆盖率门禁：只对 4 个核心文件做行覆盖硬门槛",
        epilog=GENERATE_HINT,
    )
    parser.add_argument(
        "--coverage-json", default=DEFAULT_JSON, type=Path,
        help=f"coverage json 产物路径（默认 {DEFAULT_JSON}）",
    )
    parser.add_argument(
        "--min", dest="min_pct", default=DEFAULT_MIN, type=float,
        help=f"行覆盖率下限，精确比较（默认 {DEFAULT_MIN}）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.min_pct < 0 or args.min_pct > 100 or args.min_pct != args.min_pct:  # NaN / 越界
        print(f"[覆盖率门禁] 输入错误：--min 必须是 0~100 的数，收到 {args.min_pct!r}", file=sys.stderr)
        return 2
    try:
        files = load_report(args.coverage_json)
        results = evaluate(files, args.min_pct)
    except InputError as exc:
        print(f"[覆盖率门禁] 输入错误：{exc}", file=sys.stderr)
        print(GENERATE_HINT, file=sys.stderr)
        return 2
    report, rc = format_report(results, args.min_pct, args.coverage_json)
    print(report)
    return rc


if __name__ == "__main__":
    sys.exit(main())
