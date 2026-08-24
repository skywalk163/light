# -*- coding: utf-8 -*-
r"""分布式判据清单门禁（第九轮 G9 建，M24 的判据锚点）。

## 为什么要有这条门禁

分布式在本轮开工时是**零，不是弱**：无 gRPC、无 MQ 客户端、无 RPC、无服务发现、
无心跳、无选主；`contrib/分布式锁.py:49` 的「内存分布式锁」是进程内
`threading.Lock`；`docs/lightpub/RPC框架.md` 是文档先行、代码不存在。

从零起步的东西最容易攒出「只有壳」的判据：一条 `assert 节点数 >= 1` 就能让
「分发」看起来有判据。第七轮已经吃过这个亏 —— **上界断言（单边 `<=`/`>=`）是假绿
主形态**，`tests/unit/test_native_leg_capability.py` 原稿断的是「1 ≤ 行号 ≤ 总行数」，
四千行文件里任何数字都过。

所以本门禁的核心不是「有没有测试」，而是 **「有没有反跑」**：

    没有反跑就不算判据（总纲 §5 红线 3）

反跑 = 一句可执行的话，说明**改哪一行会让这条判据立刻变红**。写不出反跑的判据，
通常意味着它根本没在验证它声称验证的东西。

## 判据（每条都能反跑，见 tests/unit/test_ci_gates_round9.py）

1. 九条能力（分发 / 心跳 / 重派 / 幂等 / 背压 / 限流 / 取消传播 / 结果汇聚 /
   故障隔离）**可增不可删** —— 删掉做不到的那条等于把指标改成自己能过的样子。
2. 状态三值 `done / partial / none`，写别的字即红（防「基本可用」这类模糊态）。
3. `done` 必须**同时**满足：
   - `判据` 形如 `tests/xxx.py:123`，文件真存在、行号在文件范围内；
   - `反跑` 非空，**含一个真存在的文件路径**，且含一个动作词
     （改 / 删 / 取反 / 注释 / 换 / 调 / 去掉）—— 「反跑：有」这种话不算反跑。
4. `partial` / `none` 必须有 `备注` 写明差什么、本阶段做不做。
   `none` 不是耻辱，没记账才是。
5. `done` 条数只升不降（棘轮），且基线里已是 `done` 的能力不许退回。
6. `--print-inspection` 打印**反跑巡检清单**：S2 / S3 两个合并点各人工复跑一遍，
   结果写进阶段合并报告（任务书 G9 §2.3）。

用法：
  # 对比模式（CI 用）
  python3 tools/ci/dist_criteria.py --root .
  # 反跑巡检清单（合并点人工复跑）
  python3 tools/ci/dist_criteria.py --root . --print-inspection
  # 刷新基线（**只在合并点**）
  python3 tools/ci/dist_criteria.py --root . \
      --write-baseline tools/ci/dist_criteria_baseline.json
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_BASELINE = os.path.join(_HERE, "dist_criteria_baseline.json")
_DEFAULT_清单 = os.path.join("任务书", "分布式判据清单.json")

状态值域 = ("done", "partial", "none")
必填字段 = ("能力", "状态", "判据", "反跑", "本阶段目标", "备注")

# 反跑必须是个动作。这批词是「改哪一行会让它立红」的常见说法；
# 不在这批词里的写法（例如「反跑：有」「见测试」）一律判红。
动作词 = ("改", "删", "取反", "注释", "换", "调", "去掉", "改成", "去除")

_RE_位置 = re.compile(r"(?P<file>[\w./\u4e00-\u9fff-]+\.(?:py|light|c|json|md))"
                     r"(?::(?P<line>\d+))?")

_spec = importlib.util.spec_from_file_location(
    "_g9_dc_bootstrap_rate", os.path.join(_HERE, "bootstrap_rate.py"))
_BR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_BR)


def _posix(path):
    return path.replace("\\", "/")


def 读清单(path):
    with io.open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    条目 = data.get("条目")
    if not isinstance(条目, list) or not 条目:
        raise ValueError("清单缺 `条目` 数组或为空")
    return data, 条目


def _查文件行(root, 文本):
    """从一段文字里抽出第一个 `文件[:行号]`，返回 (相对路径, 行号或 None, 问题)。"""
    m = _RE_位置.search(str(文本))
    if not m:
        return None, None, "找不到 `文件:行号` 形态的位置"
    rel = m.group("file")
    full = os.path.join(root, rel.replace("/", os.sep))
    if not os.path.isfile(full):
        return rel, None, "文件不存在：%s" % rel
    行号 = int(m.group("line")) if m.group("line") else None
    if 行号 is not None:
        with io.open(full, encoding="utf-8", errors="replace") as fh:
            总行 = sum(1 for _ in fh)
        if not (1 <= 行号 <= 总行):
            return rel, 行号, "%s:%d 行号越界（文件共 %d 行）" % (rel, 行号, 总行)
    return rel, 行号, None


def 校验(root, 条目):
    问题 = []
    分布 = {s: 0 for s in 状态值域}
    done能力 = set()
    见过 = set()
    巡检 = []
    for i, 条 in enumerate(条目, 1):
        能力 = 条.get("能力", "第%d项(无能力名)" % i)
        缺 = [f for f in 必填字段 if f not in 条]
        if 缺:
            问题.append("%s 缺字段：%s" % (能力, "、".join(缺)))
            continue
        if 能力 in 见过:
            问题.append("%s 条目重复" % 能力)
            continue
        见过.add(能力)

        状态 = 条["状态"]
        if 状态 not in 状态值域:
            问题.append("%s 状态 `%s` 不在值域 %s 内（状态词不能当解释用）"
                        % (能力, 状态, "/".join(状态值域)))
            continue
        分布[状态] += 1

        if not str(条["本阶段目标"]).strip():
            问题.append("%s 本阶段目标为空" % 能力)

        if 状态 == "done":
            判据 = str(条["判据"]).strip()
            反跑 = str(条["反跑"]).strip()
            if not 判据:
                问题.append("%s 是 done 但判据为空 —— 「做完了」必须指得出在哪" % 能力)
                continue
            _rel, _行, 坏 = _查文件行(root, 判据)
            if 坏:
                问题.append("%s 的判据 %s" % (能力, 坏))
                continue
            if not 反跑:
                问题.append("%s 是 done 但反跑为空 —— 没有反跑就不算判据"
                            "（总纲 §5 红线 3）" % 能力)
                continue
            if not any(w in 反跑 for w in 动作词):
                问题.append("%s 的反跑 `%s` 里没有动作词（%s）—— 反跑要说清"
                            "「改哪一行会让它立红」，不是写一句「有」"
                            % (能力, 反跑[:40], "/".join(动作词[:5])))
                continue
            _rel2, _行2, 坏2 = _查文件行(root, 反跑)
            if 坏2:
                问题.append("%s 的反跑 %s（反跑必须指到一个真存在的文件，"
                            "否则合并点没法复跑）" % (能力, 坏2))
                continue
            done能力.add(能力)
            巡检.append((能力, 判据, 反跑))
        else:
            if not str(条["备注"]).strip():
                问题.append("%s 状态是 %s 但备注为空 —— 差什么、本阶段做不做要写明；"
                            "none 不是耻辱，没记账才是" % (能力, 状态))
    return 问题, 分布, done能力, 巡检


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="仓库根目录，默认当前目录")
    ap.add_argument("--list", dest="清单", default=None,
                    help="清单路径，默认 <root>/任务书/分布式判据清单.json")
    ap.add_argument("--baseline", default=_DEFAULT_BASELINE, help="基线快照路径")
    ap.add_argument("--write-baseline", metavar="PATH", help="把本次结果写成新基线并退出")
    ap.add_argument("--print-inspection", action="store_true",
                    help="打印反跑巡检清单（合并点人工复跑，结果写进阶段合并报告）")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("[分布式判据门禁] 仓库根不存在：%s" % args.root)
        return 2

    清单路径 = args.清单 or os.path.join(args.root, _DEFAULT_清单)
    try:
        data, 条目 = 读清单(清单路径)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print("[分布式判据门禁] 读不动清单 %s：%s" % (清单路径, e))
        return 2

    问题, 分布, done能力, 巡检 = 校验(args.root, 条目)
    print("[分布式判据门禁] 清单 %s：共 %d 条能力，done %d / partial %d / none %d"
          % (_posix(os.path.relpath(清单路径, args.root)), len(条目),
             分布["done"], 分布["partial"], 分布["none"]))

    if args.print_inspection:
        print("[分布式判据门禁] 反跑巡检清单（%d 条，S2/S3 合并点各人工复跑一遍）：" % len(巡检))
        for 能力, 判据, 反跑 in 巡检:
            print("       [%s]" % 能力)
            print("         判据：%s" % 判据)
            print("         反跑：%s" % 反跑)
            print("         期望：反跑后该判据**立红**；若仍绿，这条判据无效，"
                  "状态退回 partial 并留档")
        if not 巡检:
            print("       （当前没有 done 条目，巡检清单为空 —— 这是真实状态，不是遗漏）")

    if 问题:
        print("[分布式判据门禁] 红：清单有 %d 处不合规：" % len(问题))
        for p in 问题:
            print("       ! %s" % p)
        return 1

    if args.write_baseline:
        out = {
            "version": 1,
            "note": ("分布式判据清单基线（第九轮 G9 建）。口径见 "
                     "tools/ci/dist_criteria.py docstring。done 只升不降、已 done 不许"
                     "退回、能力可增不可删；done 必须同时有可定位的判据与含动作词的反跑。"
                     "**只在合并点重建**（总纲 §5 红线 5）。"),
            "built_from_commit": _BR._当前提交(args.root),
            "list_path": _posix(_DEFAULT_清单),
            "total": len(条目),
            "done_count": 分布["done"],
            "done_能力": sorted(done能力),
            "能力": sorted(条.get("能力") for 条 in 条目),
            "distribution": 分布,
        }
        with io.open(args.write_baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("[分布式判据门禁] 已写入基线 %s（done %d / %d）"
              % (args.write_baseline, 分布["done"], len(条目)))
        return 0

    try:
        with io.open(args.baseline, encoding="utf-8") as fh:
            baseline = json.load(fh)
    except (FileNotFoundError, ValueError):
        print("[分布式判据门禁] 找不到（或读不动）基线 %s。"
              "首次接入请先 --write-baseline 生成并提交。" % args.baseline)
        return 2

    red = False
    base_能力 = set(baseline.get("能力", []))
    当前能力 = {条.get("能力") for 条 in 条目}
    丢失 = sorted(base_能力 - 当前能力)
    if 丢失:
        print("[分布式判据门禁] 红：基线里的能力在清单里消失了：%s"
              "（做不到的能力要留在清单里记 none + 备注，不是删掉）" % "、".join(丢失))
        red = True

    base_done = set(baseline.get("done_能力", []))
    退回 = sorted(base_done - done能力 - set(丢失))
    if 退回:
        当前态 = {条.get("能力"): 条.get("状态") for 条 in 条目}
        print("[分布式判据门禁] 红：基线里已是 done 的能力退回了：")
        for 名 in 退回:
            print("       ! %s：done → %s" % (名, 当前态.get(名)))
        print("       只卡 done 总数会留一个洞：拆一条补一条总数不变，"
              "被拆掉的那条从此无人记账。")
        red = True

    base_count = baseline.get("done_count", 0)
    if 分布["done"] < base_count:
        print("[分布式判据门禁] 红：done 条数 %d 低于基线 %d（只升不降）。"
              % (分布["done"], base_count))
        red = True
    elif 分布["done"] > base_count:
        print("[分布式判据门禁] 完成度提升 %d → %d（在合并点刷新基线，"
              "并在交付报告第 5 项写明「哪几条从什么变成什么」）。"
              % (base_count, 分布["done"]))
    else:
        print("[分布式判据门禁] 完成度持平基线 %d。" % base_count)

    if red:
        return 1
    print("[分布式判据门禁] 通过：能力未消失、无 done 退回、完成度未降、"
          "每条 done 都有可定位判据与可复跑反跑。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
