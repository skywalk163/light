# -*- coding: utf-8 -*-
r"""功能对标清单门禁（第七轮 E7 建，M20 的第二条判据）。

## 为什么要有这条门禁

前六轮的验收判据是「特性点齐了没」，所以永远回答不了一个最该回答的问题：
**离「能开发 deepseek-harness 类项目」还差多少。** 第五轮 M14 写着「最终判据」，
落地判据却是「跑 mock 即算达成」——判据与目标不在同一层。

第七轮把口径换成「对着原版 harness 的功能清单勾完成度」，清单落在
`任务书/功能对标清单_harness.json`（数据初值见总纲 §4.1），本脚本把它变成门禁。

## 判据

1. **`done` 条数只升不降**（棘轮）。
2. **逐条棘轮**：基线里已经是 `done` 的编号，现在不许退成 `partial`/`none`。
   只卡总数会留一个洞——把一条 `done` 改成 `none`、再把另一条 `none` 改成 `done`，
   总数不变而实际是拆东墙补西墙，且被拆掉的那条从此无人记账。
3. **条目不许消失**：基线里的编号必须还在（防「删掉做不到的那条」）。
4. `done` / `partial` **必须有至少一条证据**，且证据里的**文件必须存在**。
   **不校验行号内容**——行号随任何编辑漂移，校验它会造长红。
5. `none` 允许存在，但**必须有 `备注`** 说明本轮做不做。这条是刻意的：
   `none` 不是耻辱，没记账才是。
6. 状态值域只有 `done` / `partial` / `none`，写别的字即红（防「基本完成」这类模糊态）。

## 为什么清单放 `任务书/` 而不是 `docs/`

`docs/` 下的文件会被文档示例门禁扫（`tests/unit/doc_block_scan.py` 只扫 `docs/`），
而任务书目录本来就是这批文档的家（第五轮 `2595a6d0` 的既有裁决）。

用法：
  # 对比模式（CI 用）
  python3 tools/ci/spec_coverage.py --root .
  # 刷新基线（勾掉一条之后手工执行并提交）
  python3 tools/ci/spec_coverage.py --root . \
      --write-baseline tools/ci/spec_coverage_baseline.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_BASELINE = os.path.join(_HERE, "spec_coverage_baseline.json")
_DEFAULT_清单 = os.path.join("任务书", "功能对标清单_harness.json")

状态值域 = ("done", "partial", "none")
必填字段 = ("编号", "功能", "状态", "证据", "本轮目标", "备注")


def _posix(path):
    """键一律走 POSIX `/`：基线要跨平台可比，不许带 os.sep（gitea run 71 教训）。"""
    return path.replace("\\", "/")


def 读清单(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    条目 = data.get("条目")
    if not isinstance(条目, list) or not 条目:
        raise ValueError("清单缺 `条目` 数组或为空")
    return data, 条目


def 校验(条目, root):
    """返回 (问题清单, 状态分布, done 编号集合)。"""
    问题 = []
    分布 = {s: 0 for s in 状态值域}
    done_ids = set()
    见过 = set()
    for i, 条 in enumerate(条目, 1):
        编号 = 条.get("编号", "第%d项(无编号)" % i)
        缺 = [f for f in 必填字段 if f not in 条]
        if 缺:
            问题.append("#%s 缺字段：%s" % (编号, "、".join(缺)))
            continue
        if 编号 in 见过:
            问题.append("#%s 编号重复" % 编号)
        见过.add(编号)

        状态 = 条["状态"]
        if 状态 not in 状态值域:
            问题.append("#%s 状态 `%s` 不在值域 %s 内" % (编号, 状态, "/".join(状态值域)))
            continue
        分布[状态] += 1

        证据 = 条["证据"]
        if not isinstance(证据, list):
            问题.append("#%s 证据必须是数组" % 编号)
            证据 = []
        if 状态 in ("done", "partial") and not 证据:
            问题.append("#%s 状态是 %s 但没有任何证据——「做完了」必须指得出在哪"
                        % (编号, 状态))
        for 项 in 证据:
            # 证据形如 `path/to/file.light:12-34`；只取文件名部分，行号只作人读线索。
            文件 = str(项).split(":")[0].strip()
            if not 文件:
                问题.append("#%s 证据 `%s` 解不出文件名" % (编号, 项))
                continue
            if not os.path.isfile(os.path.join(root, 文件.replace("/", os.sep))):
                问题.append("#%s 证据文件不存在：%s（行号不校验，但文件必须在）"
                            % (编号, 文件))
        if 状态 == "none" and not str(条["备注"]).strip():
            问题.append("#%s 状态是 none 但备注为空——none 不是耻辱，没记账才是；"
                        "必须写明本轮做不做" % 编号)
        if not str(条["本轮目标"]).strip():
            问题.append("#%s 本轮目标为空" % 编号)
        if 状态 == "done":
            done_ids.add(编号)
    return 问题, 分布, done_ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="仓库根目录，默认当前目录")
    ap.add_argument("--list", dest="清单", default=None,
                    help="清单路径，默认 <root>/任务书/功能对标清单_harness.json")
    ap.add_argument("--baseline", default=_DEFAULT_BASELINE, help="基线快照路径")
    ap.add_argument("--write-baseline", metavar="PATH", help="把本次状态写成新基线并退出")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("[对标清单门禁] 仓库根不存在：%s" % args.root)
        return 2

    清单路径 = args.清单 or os.path.join(args.root, _DEFAULT_清单)
    try:
        data, 条目 = 读清单(清单路径)
    except (FileNotFoundError, ValueError, UnicodeDecodeError) as e:
        print("[对标清单门禁] 读不动清单 %s：%s" % (清单路径, e))
        return 2

    问题, 分布, done_ids = 校验(条目, args.root)
    print("[对标清单门禁] 清单 %s：共 %d 条，done %d / partial %d / none %d"
          % (_posix(os.path.relpath(清单路径, args.root)), len(条目),
             分布["done"], 分布["partial"], 分布["none"]))

    if 问题:
        print("[对标清单门禁] 红：清单本身有 %d 处不合规：" % len(问题))
        for p in 问题:
            print("       ! %s" % p)
        return 1

    if args.write_baseline:
        out = {
            "version": 1,
            "note": ("功能对标清单基线（第七轮 E7 建）。done 条数只升不降；"
                     "基线里已是 done 的编号不许退回；条目编号不许消失。"
                     "口径见 tools/ci/spec_coverage.py docstring。"
                     "勾掉一条之后重新生成本文件，并在交付报告第 7 项写明"
                     "「哪几条从什么变成什么」。"),
            "built_from_commit": _当前提交(args.root),
            "list_path": _posix(_DEFAULT_清单),
            "total": len(条目),
            "done_count": 分布["done"],
            "done_ids": sorted(done_ids),
            "ids": sorted(条.get("编号") for 条 in 条目),
            "distribution": 分布,
        }
        with open(args.write_baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("[对标清单门禁] 已写入基线 %s（done %d / %d 条）"
              % (args.write_baseline, 分布["done"], len(条目)))
        return 0

    try:
        with open(args.baseline, encoding="utf-8") as fh:
            baseline = json.load(fh)
    except (FileNotFoundError, ValueError):
        print("[对标清单门禁] 找不到（或读不动）基线 %s。"
              "首次接入请先 --write-baseline 生成并提交。" % args.baseline)
        return 2

    red = False
    base_done = baseline.get("done_count", 0)
    base_done_ids = set(baseline.get("done_ids", []))
    base_ids = set(baseline.get("ids", []))
    cur_ids = {条.get("编号") for 条 in 条目}

    丢失 = sorted(base_ids - cur_ids)
    if 丢失:
        print("[对标清单门禁] 红：基线里的条目在清单里消失了：%s"
              "（做不到的功能要留在清单里记 none + 备注，不是删掉）"
              % "、".join("#%s" % i for i in 丢失))
        red = True

    退回 = sorted(base_done_ids - done_ids - set(丢失))
    if 退回:
        当前态 = {条.get("编号"): 条.get("状态") for 条 in 条目}
        print("[对标清单门禁] 红：基线里已是 done 的条目退回了：")
        for i in 退回:
            print("       ! #%s：done → %s" % (i, 当前态.get(i)))
        print("       为什么是红：只卡 done 总数会留一个洞——拆一条补一条总数不变，"
              "而被拆掉的那条从此无人记账。")
        red = True

    if 分布["done"] < base_done:
        print("[对标清单门禁] 红：done 条数 %d 低于基线 %d（完成度只升不降）。"
              % (分布["done"], base_done))
        red = True
    elif 分布["done"] > base_done:
        print("[对标清单门禁] 完成度提升 %d → %d（勾掉之后请 --write-baseline 刷新基线，"
              "并在交付报告第 7 项写明变更）。" % (base_done, 分布["done"]))
    else:
        print("[对标清单门禁] 完成度持平基线 %d。" % base_done)

    if red:
        return 1
    print("[对标清单门禁] 通过：清单合规、完成度未降、无条目消失、无 done 退回。")
    return 0


def _当前提交(root):
    """基线是从哪个提交生成的。与 bootstrap_rate 同实现，按路径复用免得写第三份。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_e7_br_for_spec", os.path.join(_HERE, "bootstrap_rate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._当前提交(root)


if __name__ == "__main__":
    sys.exit(main())
