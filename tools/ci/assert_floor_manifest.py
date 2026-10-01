# -*- coding: utf-8 -*-
r"""自举地板清单·内部自洽断言门禁（R108 任务线 I · 落地 R107 顺延项，卡 #307）。

## 为什么要有这条门禁

`任务书/自举地板清单.json` 里 `分类统计` 与 `函数[]` 是两处**独立手写**的口径：
`分类统计` 是汇总，`函数[].分类` 是逐条明细。两者只靠人的记性保持一致——
历史上（R106 §九）就出现过「`分类统计` 声称 62/15/68/13/0，逐条重算也 62/15/68/13/0，
看似不漂」的假象：一旦有人改了**某一条** `函数[].分类` 却忘了同步 `分类统计`，或反向，
没有任何红灯会发现。

`tools/ci/floor_bootstrap.py`（G9）守的是「清单 vs builtins.py」的咬合与自举率棘轮，
**不守清单内部**是否自洽。本脚本补上这一条：让「改一处、漏一处」立刻变红，并打印
差异明细（哪一类、期望多少、实际多少、差多少），而不是只 `assert False`。

## 四条判据（每条都能反跑，见 tests/unit/test_floor_manifest_gate.py）

1. **逐类计数咬合**：`分类统计` 每个键 == `函数[].分类` 实计数；任一不等 → 红，
   打印 `分类 X：分类统计登记 E 条 / 函数[]实计 A 条 / 差 D 条`。
2. **三方总量一致**：`sum(分类统计)` == `len(函数)` == `总数`；任一不等 → 红。
3. **分类值域合法**：`分类统计` 的每个键、`函数[].分类` 的每个值都必须落在
   `native_required/movable/has_light_impl/duplicate/unused` 之内；
   出现未知分类 → 红（防止拼写错把一条真边界吞成 0）。
4. **CI 基线交叉校验**：与 `tools/ci/floor_bootstrap_baseline.json` 对齐 ——
   `baseline.total` == `总数` == `len(函数)`、`baseline.light_count` ==
   `分类统计.has_light_impl`、`baseline.native_required_count` == `分类统计.native_required`。

## ⚠ 只读依赖

本脚本**只读** `任务书/自举地板清单.json` 与 `floor_bootstrap_baseline.json`，
**绝不改写**清单内容（任务书线 G 硬约束）。反跑靠临时副本，不动源文件。

用法：
  python tools/ci/assert_floor_manifest.py --root .
  # 反跑：把 分类统计.native_required 改成 61 → 红并打印差异
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_清单 = os.path.join("任务书", "自举地板清单.json")
_DEFAULT_BASELINE = os.path.join(_HERE, "floor_bootstrap_baseline.json")

# 与 floor_bootstrap.py 的 分类值域 同源（避免写第二份分叉）。
合法分类 = ("native_required", "movable", "has_light_impl", "duplicate", "unused")
合法集合 = set(合法分类)


def 读清单(path):
    with io.open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    条目 = data.get("函数")
    if not isinstance(条目, list) or not 条目:
        raise ValueError("清单缺 `函数` 数组或为空")
    return data, 条目


def 实计数(条目):
    """逐条统计 `函数[].分类` 的出现次数（缺失值按空串计，归到未知口径里再判）。"""
    c = Counter()
    for 条 in 条目:
        v = 条.get("分类")
        c["" if v is None else v] += 1
    return c


def 校验(清单数据, 条目, 基线):
    """返回 (问题字符串列表, 统计字典)。失败信息必须可操作。"""
    问题 = []
    分类统计 = 清单数据.get("分类统计")
    总数 = 清单数据.get("总数")
    实际 = 实计数(条目)
    条数 = len(条目)

    if not isinstance(分类统计, dict) or not 分类统计:
        问题.append("清单 `分类统计` 缺失或非字典")
        分类统计 = {}

    # ── 判据 1：逐类计数咬合（双向，覆盖 分类统计 有而函数无 / 函数有而分类统计无）──
    全部键 = sorted(set(分类统计) | set(实际))
    for 键 in 全部键:
        期望 = 分类统计.get(键, 0)
        实际值 = 实际.get(键, 0)
        if 期望 != 实际值:
            差 = 实际值 - 期望
            问题.append("分类 `%s`：分类统计登记 %d 条 / 函数[]实计 %d 条 / 差 %+d 条"
                        % (键, 期望, 实际值, 差))

    # ── 判据 3a：分类统计 里的键都合法 ──
    for 键 in 分类统计:
        if 键 not in 合法集合:
            问题.append("分类统计 含未知分类 `%s`（合法集合：%s）"
                        % (键, "/".join(合法分类)))

    # ── 判据 3b：函数[].分类 的每个值都合法（空串也算非法：未分类）──
    未知 = sorted(值 for 值 in 实际 if 值 and 值 not in 合法集合)
    if 未知:
        问题.append("函数[] 含未知分类值：%s（合法集合：%s）"
                    % ("、".join(未知), "/".join(合法分类)))
    if 实际.get("", 0):
        问题.append("函数[] 有 %d 条 分类 为空（未分类，必须做完裁决再进 CI）"
                    % 实际[""])

    # ── 判据 2：三方总量一致 ──
    求和 = sum(v for k, v in 分类统计.items() if k in 合法集合)
    if 求和 != 条数:
        问题.append("分类统计 合法键求和 %d ≠ 函数[]条数 %d（漏算或多算）" % (求和, 条数))
    if 条数 != 总数:
        问题.append("函数[] 条数 %d ≠ 总数 %d" % (条数, 总数))
    if isinstance(总数, int) and 求和 != 总数:
        问题.append("分类统计 合法键求和 %d ≠ 总数 %d" % (求和, 总数))

    # ── 判据 4：CI 基线交叉校验 ──
    if 基线 is not None:
        bt = 基线.get("total")
        if bt is not None and bt != 条数:
            问题.append("基线 total %s ≠ 函数[]条数 %d（与 floor_bootstrap_baseline.json 脱节）"
                        % (bt, 条数))
        if bt is not None and isinstance(总数, int) and bt != 总数:
            问题.append("基线 total %s ≠ 总数 %d" % (bt, 总数))
        bl = 基线.get("light_count")
        if bl is not None and bl != 分类统计.get("has_light_impl"):
            问题.append("基线 light_count %s ≠ 分类统计.has_light_impl %s"
                        % (bl, 分类统计.get("has_light_impl")))
        bn = 基线.get("native_required_count")
        if bn is not None and bn != 分类统计.get("native_required"):
            问题.append("基线 native_required_count %s ≠ 分类统计.native_required %s"
                        % (bn, 分类统计.get("native_required")))

    统计 = {
        "总数": 条数,
        "分类统计": dict(分类统计),
        "实计数": {k: v for k, v in 实际.items()},
    }
    return 问题, 统计


def main():
    ap = argparse.ArgumentParser(description="自举地板清单内部自洽断言门禁")
    ap.add_argument("--root", default=".", help="仓库根目录，默认当前目录")
    ap.add_argument("--manifest", default=None,
                    help="清单路径，默认 <root>/任务书/自举地板清单.json")
    ap.add_argument("--baseline", default=None,
                    help="CI 基线路径，默认 tools/ci/floor_bootstrap_baseline.json")
    args = ap.parse_args()

    清单路径 = args.manifest or os.path.join(args.root, _DEFAULT_清单)
    基线路径 = args.baseline or _DEFAULT_BASELINE

    try:
        清单数据, 条目 = 读清单(清单路径)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print("[清单门禁] 读不动清单 %s：%s" % (清单路径, e))
        return 2

    try:
        with io.open(基线路径, encoding="utf-8") as fh:
            基线 = json.load(fh)
    except (FileNotFoundError, ValueError):
        基线 = None
        print("[清单门禁] 警告：读不动基线 %s，跳过基线交叉校验。" % 基线路径)

    问题, 统计 = 校验(清单数据, 条目, 基线)

    print("[清单门禁] 清单 %s：函数[] %d 条；分类统计 = %s"
          % (清单路径, 统计["总数"], 统计["分类统计"]))

    if 问题:
        print("[清单门禁] 红：清单内部自洽失守，共 %d 处：" % len(问题))
        for p in 问题:
            print("       ! %s" % p)
        return 1

    print("[清单门禁] 通过：逐类计数咬合、三方总量一致、分类值域合法、与 CI 基线交叉校验一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
