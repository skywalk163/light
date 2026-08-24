# -*- coding: utf-8 -*-
r"""Python 直调计数门禁（第七轮 E7 建，M20 主判据）。

## 为什么要有这条门禁

`bootstrap_rate.py` 那条「引 Python 逃逸」只数 `引 Python：` 这一个关键字，
六轮来一直是 0——因为逃逸根本不走那条通道。真正的逃逸走 `导入`：

    导入 os
    导入 sys
    ...
    如果 os.path.isabs(路径):        ← 这是 Python 标准库调用，门禁看不见
    os.makedirs(目录)
    sys.stdout.write(文本)

于是「逃逸 0」这句话一直是真的、也一直没意义。本脚本把这类行数变成一条
有基线、只降不升的指标。

## 口径（第七轮总纲 §4.5 E7 条，开工首日裁决，取默认口径）

一行计一次「Python 直调」，当且仅当：

  1. 该行在 `.light` 文件里，且**不是注释、不在字符串字面量内**
     （单行串与多行串都剥掉，见 `剥注释与字符串()`）；
  2. 行内出现 `<模块名>.<属性>`，`<模块名>` 前面不是标识符字符或点
     （排除 `x.os.path` 这种属性链）；
  3. `<模块名>` 来自**本文件**的导入语句（`导入 X` / `从 X 导入 …` /
     `导入 Python: X` 等，形态解析复用 `bootstrap_rate.取模块名位置`）；
  4. `<模块名>` **不是光明模块**——即它既不是 `stdlib/` 下任何 `.light`/`.py`
     的模块名，也不是本文件同目录下的兄弟模块，且是纯 ASCII 标识符
     （含中文的名字一律判为光明模块，Python 标准库没有中文模块名）。

**一行只计一次**，哪怕一行里有三处 `os.xxx`。基线按**文件维度**记数，
不记行号——行号会随任何编辑漂移，键里带行号就会造幻影红
（第七轮 A7 已经在门禁基线上踩过这个坑）。

### 刻意不算进来的东西（写在明处，免得被当成漏洞）

- **`.encode("utf-8")` / `.strip()` 这类方法调用不计。** 静态看不出接收者是
  Python 对象还是光明对象，硬算会把 `坏行表.append(...)`（光明列表的方法）
  一起算进来。总纲 §0 把 `.encode("utf-8")` 列为逃逸样本是对的，但它需要
  类型推断才能判准，本门禁不做类型推断，宁可少算也不造假红。
- **`引 Python：` 内联块里的行不计。** 那是另一条门禁
  （`bootstrap_rate.py` 的 stdlib 破零判据）的地盘，重复计会让两条指标互相污染。
- **模块名被本文件重新绑定的不计**：`设 os 为 ...` / `接收 os` 之后，
  `os.foo` 已经不是 Python 调用了。这类排除会打印在「误伤排除」清单里。

## 基线口径：只降不升，且**不要求降到 0**

要求一次性降到 0 只会逼出「换个写法绕过正则」的假降（例如把
`os.path.join(a, b)` 改写成 `路径拼接(a, b)` 再在别处 `引 Python：` 兜底）。
所以基线只做棘轮：**每个文件的计数不许升、总数不许升**，降了就提示刷新基线。

## 防篡改

- 基线里 `total` 必须等于 `files` 各项之和，不等即红（防手改总数放宽）。
- 从基线里删掉一条仍然存在的违规 → 该文件当前计数 > 基线（缺项按 0 算）→ 红。
  这就是「偷偷删基线条目消红」这条路被堵死的机制。

用法：
  # 对比模式（CI 用）
  python3 tools/ci/python_direct_calls.py --root .
  # 刷新基线（真降下来之后手工执行并提交）
  python3 tools/ci/python_direct_calls.py --root . \
      --write-baseline tools/ci/python_direct_baseline.json
  # 只看排行（施工地图）
  python3 tools/ci/python_direct_calls.py --root . --top 10
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_BASELINE = os.path.join(_HERE, "python_direct_baseline.json")

# 与 bootstrap_rate.py 共用同一套「导入语句形态」解析：那边覆盖了 parser 的 10 种
# 形态（裸写 / 《》/ 为 别名 / 逗号多模块 / 倒装 / `导` 简写），再写第二份解析器
# 就是双实现，口径迟早分叉。tools/ci 不是包，按路径加载。
_spec = importlib.util.spec_from_file_location(
    "_e7_bootstrap_rate", os.path.join(_HERE, "bootstrap_rate.py"))
_BR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_BR)

取模块名位置 = _BR.取模块名位置
iter_light_files = _BR.iter_light_files

# `导入 Python: os, sys` / `导 Python：json`：`取模块名位置` 刻意返回 []
# （它判的是「段言模块自导入」），但对本门禁来说这批模块正是 Python 模块。
_RE_导入PY = re.compile(r"^\s*导入?\s*Python\s*[：:]\s*(.+)$")
# `引 Python：` 内联块起始行。块体归另一条门禁管，这里整块跳过。
_RE_引PY = re.compile(r"引\s*Python\s*[：:]")
# 模块名被本文件重新绑定：`设 X 为 …`（光明的赋值）/ `接收 … X …`（形参）
_RE_设 = re.compile(r"(?:^|\s)设\s+([A-Za-z_][A-Za-z0-9_]*)\s+为(?![A-Za-z0-9_])")
_RE_接收 = re.compile(r"接收\s+(.+)$")

_ASCII_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# 扫描时跳过的目录：与 bootstrap_rate/assert_quality 同一套，口径不许各自一份
_SKIP_DIRS = _BR._SKIP_DIRS


def _posix(path):
    """路径分隔符归一成 `/`：基线键跨平台可比，绝不许带 `os.sep`。

    gitea run 71 就是因为基线键在 Windows 上生成成 `a\\b.light`、
    在 FreeBSD runner 上算出 `a/b.light`，键对不上导致门禁无条件长红。
    """
    return path.replace("\\", "/")


def 剥注释与字符串(文本):
    """把 `.light` 源码里的注释与字符串字面量替换成空白，返回逐行列表。

    保留行结构（行号不变），只把「不该当代码看」的字符抹成空格：
      - `#` 到行尾（不在字符串内时）
      - `"..."` / `'...'` 单行串
      - `\"\"\"...\"\"\"` / `'''...'''` **多行**串（光明支持三引号文档串，
        `contrib/统计函数增强.light:31` 之类）
      - 全角引号 `“…”`
    抹成空格而不是删掉：列位置不变，报文里贴原行时对得上。
    """
    out = []
    i = 0
    n = len(文本)
    buf = []
    三引号 = None      # 当前所在的三引号串定界符，None = 不在串内
    单引号 = None      # 当前所在的单行串定界符
    while i < n:
        ch = 文本[i]
        if 三引号:
            if 文本.startswith(三引号, i):
                buf.append(" " * len(三引号))
                i += len(三引号)
                三引号 = None
            else:
                buf.append("\n" if ch == "\n" else " ")
                i += 1
            continue
        if 单引号:
            if ch == "\n":              # 单行串不跨行：行尾自动闭合，容错
                buf.append("\n")
                单引号 = None
                i += 1
                continue
            if ch == "\\" and i + 1 < n:   # 转义：整对抹掉
                buf.append("  ")
                i += 2
                continue
            if ch == 单引号:
                单引号 = None
            buf.append(" ")
            i += 1
            continue
        if 文本.startswith('"""', i) or 文本.startswith("'''", i):
            三引号 = 文本[i:i + 3]
            buf.append("   ")
            i += 3
            continue
        if ch in ('"', "'", "\u201c"):
            单引号 = "\u201d" if ch == "\u201c" else ch
            buf.append(" ")
            i += 1
            continue
        if ch == "#":
            j = 文本.find("\n", i)
            if j < 0:
                j = n
            buf.append(" " * (j - i))
            i = j
            continue
        buf.append(ch)
        i += 1
    out = "".join(buf).split("\n")
    return out


def 光明模块名集合(root):
    """`stdlib/` 下所有 `.light` / `.py` 的模块名——这些一律不算 Python 模块。

    `.py` 也收：`stdlib/文件系统.py` 是光明标准库用 Python 写的实现，
    `从 文件系统 导入 …` 是光明模块导入，不是 Python 逃逸
    （它自举率为 0 是另一条指标的事，不是这条）。
    """
    名字 = set()
    stdlib_dir = os.path.join(root, "stdlib")
    for dirpath, dirnames, filenames in os.walk(stdlib_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".light"):
                名字.add(fn[:-len(".light")])
            elif fn.endswith(".py"):
                名字.add(fn[:-len(".py")])
    return 名字


def _兄弟模块名(full):
    """同目录下的 `.light` / `.py`：本地模块，`导入 编排` 这种。"""
    名字 = set()
    d = os.path.dirname(full)
    try:
        for fn in os.listdir(d):
            if fn.endswith(".light"):
                名字.add(fn[:-len(".light")])
            elif fn.endswith(".py"):
                名字.add(fn[:-len(".py")])
    except OSError:
        pass
    return 名字


def 扫一个文件(full, 光明模块):
    """返回 (命中清单, 排除清单)。

    命中清单 = [(行号, 模块名, 原行文本), ...]，**一行只出现一次**。
    排除清单 = [(模块名, 原因), ...]，用于报文里的「误伤排除」样本。
    """
    try:
        with open(full, encoding="utf-8", errors="replace") as fh:
            原文 = fh.read()
    except OSError:
        return [], []

    原行 = 原文.split("\n")

    # —— 第一遍（廉价）：只在**原始行**上收「本文件导入了哪些 ASCII 模块名」——
    # 这一遍刻意不做逐字符的注释/字符串剥离：全仓上千个 `.light` 里绝大多数只导入
    # 中文模块，逐字符扫全部文件要 40 秒以上（实测），而门禁承诺秒级。
    # 先用整行注释 + 行内注释的廉价切法定出候选，没有 ASCII 候选就直接返回，
    # 剥离只留给真正可能命中的那几十个文件。
    候选 = set()
    重绑定 = set()
    for 行 in 原行:
        if not 行.strip() or 行.lstrip().startswith("#"):
            continue
        码 = 行.split("#", 1)[0]
        if "导" in 码 or "从" in 码:
            m = _RE_导入PY.match(码)
            if m:
                for 条 in re.split(r"[，,]", m.group(1)):
                    名 = 条.strip().rstrip("。").split(".")[0].strip()
                    if _ASCII_IDENT.match(名):
                        候选.add(名)
                continue
            for 名 in 取模块名位置(码.strip()):
                名 = 名.split(".")[0].strip()
                if _ASCII_IDENT.match(名):
                    候选.add(名)
        if "设" in 码:
            m2 = _RE_设.search(码)
            if m2:
                重绑定.add(m2.group(1))
        if "接收" in 码:
            m3 = _RE_接收.search(码)
            if m3:
                for 条 in re.split(r"[，,]", m3.group(1)):
                    名 = 条.strip().split(":")[0].strip().rstrip("：:")
                    if _ASCII_IDENT.match(名):
                        重绑定.add(名)

    排除 = []
    py模块 = set()
    for 名 in sorted(候选):
        if 名 in 光明模块:
            排除.append((名, "光明模块（stdlib/ 或同目录同名文件）"))
            continue
        if 名 in 重绑定:
            排除.append((名, "本文件重新绑定过这个名字（设/接收），已不是模块引用"))
            continue
        py模块.add(名)

    if not py模块:
        return [], 排除

    # —— 第二遍（精确）：只有确实导入了 Python 模块的文件才付逐字符剥离的代价 ——
    码行 = 剥注释与字符串(原文)
    引块行 = set()
    引块缩进 = None
    for idx, 行 in enumerate(码行):
        裸 = 行.strip()
        if 引块缩进 is not None:
            if not 裸:
                引块行.add(idx)
                continue
            if len(行) - len(行.lstrip()) > 引块缩进:
                引块行.add(idx)
                continue
            引块缩进 = None
        if _RE_引PY.search(行):
            引块行.add(idx)
            引块缩进 = len(行) - len(行.lstrip())


    # —— 第二遍：逐行找 `<模块名>.<属性>` ——
    # 前置 lookbehind 排掉属性链（`x.os.path`）与同名后缀（`myos.path`）。
    # 按名字排序建表：一行只计一次、归给「第一个命中的模块」，若按 set 的迭代序
    # 来定这个「第一个」，同一份源码在两次进程里会把 `os.path.join(sys.argv[1])`
    # 归给不同模块（PYTHONHASHSEED 随机化），总数不变但模块排行会抖。
    # 报告要能逐字复现，这里固定成字典序。
    正则 = [(名, re.compile(r"(?<![\w\u4e00-\u9fff.])%s\s*\.\s*[A-Za-z_\u4e00-\u9fff]"
                            % re.escape(名)))
            for 名 in sorted(py模块)]
    命中 = []
    for idx, 行 in enumerate(码行):
        if idx in 引块行 or not 行.strip():
            continue
        # 导入行本身不算调用（`导入 Python: os.path` 这种）
        if 取模块名位置(行.strip()) or _RE_导入PY.match(行):
            continue
        for 名, rx in 正则:
            if rx.search(行):
                原 = 原行[idx].strip() if idx < len(原行) else ""
                命中.append((idx + 1, 名, 原))
                break      # 一行只计一次
    return 命中, 排除


def scan_tree(root):
    """扫全仓 `.light`，返回 (per_file, details, excludes, 模块计数)。"""
    光明模块 = 光明模块名集合(root)
    per_file = {}
    details = {}
    excludes = {}
    模块计数 = {}
    兄弟缓存 = {}          # 目录 → 兄弟模块名集合（同目录几十个文件不必各自 listdir）
    for full in iter_light_files(root):
        d = os.path.dirname(full)
        if d not in 兄弟缓存:
            兄弟缓存[d] = _兄弟模块名(full)
        命中, 排除 = 扫一个文件(full, 光明模块 | 兄弟缓存[d])
        rel = _posix(os.path.relpath(full, root))
        if 排除:
            excludes[rel] = 排除
        if not 命中:
            continue
        per_file[rel] = len(命中)
        details[rel] = 命中
        for _, 名, _t in 命中:
            模块计数[名] = 模块计数.get(名, 0) + 1
    return per_file, details, excludes, 模块计数


def _当前提交(root):
    """基线是从哪个提交生成的。实现与 bootstrap_rate 同源，直接复用。"""
    return _BR._当前提交(root)


def _打印排行(per_file, 模块计数, top):
    排行 = sorted(per_file.items(), key=lambda kv: (-kv[1], kv[0]))
    print("[Python直调门禁] top %d 文件排行（后续轮次的施工地图）：" % top)
    for rel, n in 排行[:top]:
        print("       %4d 行  %s" % (n, rel))
    if 模块计数:
        热 = sorted(模块计数.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        print("[Python直调门禁] 被直调最多的模块：%s"
              % "、".join("%s(%d)" % (k, v) for k, v in 热))


def main():
    ap = argparse.ArgumentParser()
    # 默认 `.` 与 CI 显式传的 `--root .` 一致：assert_quality 那边默认 `tests`
    # 与 CI 不一致，忘传参就造出几百条幻影新增（第七轮 E7 §3.3 已修）。
    ap.add_argument("--root", default=".", help="仓库根目录，默认当前目录")
    ap.add_argument("--baseline", default=_DEFAULT_BASELINE, help="基线快照路径")
    ap.add_argument("--write-baseline", metavar="PATH", help="把本次结果写成新基线并退出")
    ap.add_argument("--top", type=int, default=10, help="排行榜条数，默认 10")
    ap.add_argument("--show-hits", type=int, default=0,
                    help="额外打印前 N 条命中行（排查用，不影响判定）")
    ap.add_argument("--show-excludes", type=int, default=0,
                    help="额外打印前 N 条「误伤排除」样本（排查用，不影响判定）")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("[Python直调门禁] 仓库根不存在：%s" % args.root)
        return 2

    per_file, details, excludes, 模块计数 = scan_tree(args.root)
    total = sum(per_file.values())
    print("[Python直调门禁] 扫描 %s：%d 个 .light 文件里共 %d 行 Python 直调"
          % (args.root, len(per_file), total))
    _打印排行(per_file, 模块计数, args.top)

    if args.show_hits:
        剩 = args.show_hits
        for rel in sorted(details):
            for 行号, 名, 文本 in details[rel]:
                if 剩 <= 0:
                    break
                print("       - %s:%d  [%s] %s" % (rel, 行号, 名, 文本[:100]))
                剩 -= 1

    # 误伤排除：被口径主动放掉的导入名。数量与样本都要能看见——
    # 「排除了什么」和「计了什么」同样是口径的一部分，只贴计数会让口径不可复核。
    原因计数 = {}
    for rel in excludes:
        for _名, 原因 in excludes[rel]:
            原因计数[原因] = 原因计数.get(原因, 0) + 1
    if 原因计数:
        print("[Python直调门禁] 误伤排除（不计入指标）：%s"
              % "；".join("%s %d 处" % (k, v) for k, v in sorted(原因计数.items())))
    if args.show_excludes:
        剩 = args.show_excludes
        for rel in sorted(excludes):
            for 名, 原因 in excludes[rel]:
                if 剩 <= 0:
                    break
                print("       ~ %s：`%s` → %s" % (rel, 名, 原因))
                剩 -= 1


    if args.write_baseline:
        data = {
            "version": 1,
            "note": ("Python 直调计数基线（第七轮 E7 建）。口径见 "
                     "tools/ci/python_direct_calls.py docstring。"
                     "每文件计数与总数都只许降不许升；降了要重新生成本文件。"
                     "刻意不要求降到 0——那会逼出「换写法绕正则」的假降。"
                     "total 必须等于 files 各项之和，不等即红（防手改总数放宽）。"
                     "键不带行号：行号会随任何编辑漂移，带行号的键只会造幻影红。"),
            "built_from_commit": _当前提交(args.root),
            "scanned_root": args.root,
            "total": total,
            "files": {k: per_file[k] for k in sorted(per_file)},
        }
        with open(args.write_baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("[Python直调门禁] 已写入基线 %s（%d 文件 / %d 行）"
              % (args.write_baseline, len(per_file), total))
        return 0

    try:
        with open(args.baseline, encoding="utf-8") as fh:
            baseline = json.load(fh)
    except (FileNotFoundError, ValueError):
        print("[Python直调门禁] 找不到（或读不动）基线 %s。"
              "首次接入请先 --write-baseline 生成并提交。" % args.baseline)
        return 2

    base_files = {_posix(k): v for k, v in baseline.get("files", {}).items()}
    base_total = baseline.get("total")
    red = False

    # 防篡改：基线自身必须自洽
    if base_total is None or base_total != sum(base_files.values()):
        print("[Python直调门禁] 红：基线自相矛盾——total=%s 与 files 之和 %d 不符，"
              "基线被手改过。重新用 --write-baseline 生成。"
              % (base_total, sum(base_files.values())))
        return 1

    上升 = [(k, base_files.get(k, 0), v) for k, v in sorted(per_file.items())
            if v > base_files.get(k, 0)]
    if 上升:
        print("[Python直调门禁] 红：%d 个文件的 Python 直调行数高于基线（只许降不许升）："
              % len(上升))
        for rel, b, c in 上升:
            print("       ! %s：基线 %d → 当前 %d" % (rel, b, c))
            for 行号, 名, 文本 in details.get(rel, [])[:5]:
                print("           %s:%d  [%s] %s" % (rel, 行号, 名, 文本[:90]))
        print("       为什么是红：`导入 <Python 模块>` 后直调 Python API，"
              "等于这段逻辑并没有用光明写；这条通道以前不被任何门禁计数。")
        red = True

    下降 = [(k, v, per_file.get(k, 0)) for k, v in sorted(base_files.items())
            if per_file.get(k, 0) < v]
    if 下降:
        print("[Python直调门禁] %d 个文件下降（真降下来后请 --write-baseline 刷新基线）："
              % len(下降))
        for rel, b, c in 下降[:20]:
            print("       - %s：基线 %d → 当前 %d" % (rel, b, c))

    if total > base_total:
        print("[Python直调门禁] 红：总行数 %d 高于基线 %d。" % (total, base_total))
        red = True

    if red:
        return 1
    print("[Python直调门禁] 通过：总数 %d ≤ 基线 %d，无文件上升。" % (total, base_total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
