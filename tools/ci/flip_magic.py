# -*- coding: utf-8 -*-
"""零风险翻「纯光明实现」魔数（R122 C1 首建）。

把 R121 当时手搓的临时翻面脚本规范化入库。翻魔数 = 给一个 `.light` 的**首行前**
插一行含「纯光明实现」的注释（钩子 `_is_pure_light` 读首两行，命中即视为纯光明）。

三道前置闸门，任一不过就**拒绝翻**（rc=1），守住就绪度单调性：

  1. 影子闸门（HAS-PY 默认拒绝）：若该 `.light` 旁边存在**同名 `.py`**，补魔数会让
     Python 腿改吃 `.light`、改变现有行为——这正是 R119/R120 `对象池缓存` 翻车处。
     默认拒绝；确需翻必须显式 `--allow-shadow` 并打印红字警告（翻后必须自跑 082 门）。
     无同名 `.py`（NO-PY）的模块，钩子本就加载 `.light`，补魔数对 Python 腿零影响。
  2. 幂等闸门：首两行已含魔数 → 报告「已翻」，不动字节，rc=0。
  3. 可编闸门（单调性）：先跑 `probe_light_compile.probe_one` 真过原生腿编译。
     **不可编一律不翻**——翻不可编模块会让分母涨、分子不涨，就绪度反而下降。

写完按 bytes 落盘（不经过文本转写），保持原文件 CRLF，并当场自检 `bareLF=0`、
自检魔数已生效。本工具**零 src/ 改动、零 stdlib 语义改动**（只加一行注释头）。

用法（在本仓 venv python 下）：
  .venv/Scripts/python.exe tools/ci/flip_magic.py 字节缓冲
      探查 + 前置可编校验 + 翻魔数（无同名 .py 才放行）。
  .venv/Scripts/python.exe tools/ci/flip_magic.py 字节缓冲 --dry-run
      只跑前置校验、打印将插入的行，不动字节。
  .venv/Scripts/python.exe tools/ci/flip_magic.py 某模块 --allow-shadow --note "R123 语义已对齐"
      有同名 .py 时显式放行（高危，翻后必过 082 门），并自定义声明语。

退出码：0=翻好/本就已翻；1=任一前置闸门拒绝；2=用法错误（目标找不到/命中多个）。
"""

from __future__ import annotations

import argparse
import os
import sys

_CI_DIR = os.path.dirname(os.path.abspath(__file__))
if _CI_DIR not in sys.path:
    sys.path.insert(0, _CI_DIR)
from bootstrap_rate import _是纯光明  # noqa: E402
from probe_light_compile import probe_one, 遍历_light  # noqa: E402

_DEFAULT_ROOT = os.path.dirname(os.path.dirname(_CI_DIR))
_魔数 = "纯光明实现"


def _has_exact_shadow_py(light_path):
    """是否存在**同名同大小写**的 .py（与导入钩子 _exists_exact 同口径）。

    不能只 os.path.isfile：Windows FS 大小写不敏感，会把 JSON.light 误判命中 json.py。
    """
    py_path = light_path[:-len(".light")] + ".py"
    if not os.path.isfile(py_path):
        return False
    base = os.path.dirname(light_path)
    return os.path.basename(py_path) in os.listdir(base)


def _bare_lf_count(data):
    """bytes 里「裸 LF」个数：\\n 前面不是 \\r 就算一个。CRLF 文件必须为 0。"""
    n = 0
    for i, b in enumerate(data):
        if b == 0x0A and (i == 0 or data[i - 1] != 0x0D):
            n += 1
    return n


def _resolve(root, target):
    """模块名/路径 -> .light 绝对路径；找不到或命中多个返回 None。"""
    if target.endswith(".light") and os.path.isfile(target):
        return os.path.abspath(target)
    by_basename = {}
    for 名, 路径 in 遍历_light(root):
        by_basename.setdefault(名, []).append(路径)
    base = os.path.basename(target)[:-len(".light")] if target.endswith(".light") else target
    hits = by_basename.get(base, [])
    if not hits:
        print("找不到 .light：%s" % target)
        return None
    if len(hits) > 1:
        print("模块名「%s」命中多个 .light，请改用具体路径：" % target)
        for p in hits:
            print("  - %s" % os.path.relpath(p, root).replace("\\", "/"))
        return None
    return hits[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description="零风险翻「纯光明实现」魔数（内置可编前置校验 + CRLF 自检）")
    ap.add_argument("target", help="模块名或 .light 路径")
    ap.add_argument("--root", default=_DEFAULT_ROOT, help="仓库根（默认本脚本上两级）")
    ap.add_argument("--timeout", type=float, default=300, help="前置可编校验超时秒数（默认 300）")
    ap.add_argument("--allow-shadow", action="store_true",
                    help="显式放行有同名 .py 的高危模块（HAS-PY），并打印警告")
    ap.add_argument("--note", default="", help="自定义声明语（追加在插入行括号内）")
    ap.add_argument("--dry-run", action="store_true", help="只跑前置校验、打印将插入的行，不动字节")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)

    light = _resolve(root, args.target)
    if light is None:
        return 2
    名 = os.path.basename(light)[:-len(".light")]
    rel = os.path.relpath(light, root).replace("\\", "/")

    # —— 闸门 1：影子（HAS-PY）——
    has_shadow = _has_exact_shadow_py(light)
    if has_shadow and not args.allow_shadow:
        print("⛔ 拒绝翻：%s 存在同名 .py（HAS-PY）。" % rel)
        print("   补魔数会让 Python 腿改吃 .light、改变现有行为（R119/R120 对象池缓存即此翻车）。")
        print("   若已逐模块证明 .light 与 .py 语义等价并准备自跑 082 全量门，请加 --allow-shadow 显式放行。")
        return 1

    # —— 闸门 2：幂等 ——
    if _是纯光明(light):
        print("✅ %s 首两行已含魔数，无需再翻（幂等跳过）。" % rel)
        return 0

    # —— 闸门 3：前置可编校验（单调性：不可编不翻）——
    print("前置校验：原生腿 compile_light_typed 编译 %s …" % rel)
    r = probe_one(root, light, args.timeout)
    if r["bucket"] != "可编":
        print("⛔ 拒绝翻：%s 原生腿不可编（桶=%s，缺口=%s）。" % (rel, r["bucket"], r.get("gap") or "-"))
        print("   首个错误：%s" % (r.get("detail") or "（无）"))
        print("   翻不可编模块会分母涨分子不涨、拉低就绪度——故不翻，先补原生腿能力或登记终局。")
        return 1
    print("   可编 ✅（IR 长度 %s）。" % r.get("ir_len"))

    # —— 构造插入行（CRLF，UTF-8 无 BOM）——
    note = args.note or ("本模块无同名 .py，本就是纯光明唯一实现，补魔数以计入原生腿就绪度分母（对 Python 腿零影响）"
                         if not has_shadow else "HAS-PY 显式放行（--allow-shadow），翻后必须自跑 082 全量门")
    header = "# %s —— %s（flip_magic 自动补声明：%s）" % (_魔数, 名, note)
    if has_shadow:
        print("⚠️  高危放行：%s 有同名 .py。插入行将是：" % rel)
    print("将插入首行：%s" % header)
    if args.dry_run:
        print("--dry-run：未改动任何字节。")
        return 0

    # —— bytes 落盘：前插一行 + CRLF，不动其余字节 ——
    with open(light, "rb") as fh:
        original = fh.read()
    new_bytes = header.encode("utf-8") + b"\r\n" + original
    with open(light, "wb") as fh:
        fh.write(new_bytes)

    # —— 自检：CRLF(bareLF=0) + 魔数已生效 ——
    with open(light, "rb") as fh:
        after = fh.read()
    bare_lf = _bare_lf_count(after)
    ok_magic = _是纯光明(light)
    print("")
    print("已翻：%s" % rel)
    print("  bareLF = %d（必须 0，CRLF 保持）%s" % (bare_lf, " ✅" if bare_lf == 0 else " ❌"))
    print("  魔数生效（首两行含「%s」）：%s" % (_魔数, "✅" if ok_magic else "❌"))
    if bare_lf != 0 or not ok_magic:
        print("⛔ 自检失败，请人工核查 %s" % rel)
        return 1
    print("✅ 完成。该模块现计入就绪度分母；因前置校验已过，分子同步 +1，就绪度单调上升。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
