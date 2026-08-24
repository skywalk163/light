# -*- coding: utf-8 -*-
r"""原生腿产品清单门禁（第九轮 G9 建，M23 的判据锚点）。

## 为什么要有这条门禁

既有的 `docs/原生腿能力清单.json`（第七轮 B7 建，由
`tests/unit/test_native_leg_capability.py` 守）度量的是**语言节点与运行时符号**级：
`ForeachStatement` 分派了没有、`dv_socket_connect` 声明了没有。那一层现在是绿的。

但「能编译一个节点」和「是个能交付的产品」之间还差三件事，而这三件事没有任何
机读判据：

1. **模块级**：`stdlib/` 下 76 个 `.light`，哪些真能被原生腿编译？
   `ImportStatement` 在 `src/llvm/codegen_typed.py:2799-2800` 是 `pass`（no-op），
   单文件原生编译**根本看不见 stdlib**。这条是 M23 的头号阻断，却不在任何指标里。
2. **CLI 路径级**：`--backend llvm`（非 typed）引用不存在的 `src/llvm/runtime.c`
   （`compiler.py:486`），**100% 不可用、零测试**，但它在 `cli/light.py` 的
   `choices` 里是合法取值。用户按帮助文本敲一条命令，撞上一条死腿。
3. **平台级**：POSIX TLS 是 `dv_tls_unsupported` 桩，而「跨平台」这个词在文档里
   照用。**只在 Windows 测过就声称跨平台**是本轮要专治的一类假话。

## 三张表与三条指标

清单 `任务书/原生腿产品清单.json`（B9 填内容，G9 守门禁）：

- `模块表`：逐个 `stdlib/*.light` 标 `可编译 / 不可编译 / 未实测` + 阻断原因
  → **原生可编译比例只升不降**，**`未实测` 数只降不升**
- `CLI路径表`：逐条命令路径标 `可用 / 坏 / 未实现 / 未实测` + 证据
  → **`坏` 的条数只降不升**
- `平台矩阵`：平台 × 能力，标 `已实测通过 / 已实测失败 / 未实测`
  → **`未实测` 格子数只降不升**，`已实测通过` 数只升不降

## 防造假（每条都能反跑，见 tests/unit/test_ci_gates_round9.py）

1. **模块表双向咬合**：表里的模块名集合必须**逐个等于** `stdlib/` 下 `.light` 的
   实际集合。新写一个 `.light` 不登记 → 红（防腐烂）；表里写个不存在的模块 → 红
   （防吹牛）。这条让分母不可能被挑着填。
2. **后端取值正向覆盖**：从 `cli/light.py` 源码里抓出所有 `--backend` 的 `choices`
   取值，每一个都必须在 `CLI路径表` 的 `后端取值` 里出现过。
   B9 若给 `run` 加上 `native` 取值而不登记 → 红；若想靠**删掉表里那条**来消掉
   `坏` 计数，正向检查会立刻红。反向（表里有、源码已无）只**告警**不判红：
   把死腿从 `choices` 里摘掉是本轮许可的处置方式（总纲 S1 「修或删，二选一」），
   摘掉后 `坏` 计数下降是真进步，不该被拦。
3. **`可编译` 必须有判定命令**：条目的 `证据` 必须非空且含 `light`
   （即一条可复跑的 CLI），空口宣称可编译不算。B9 → 全体的那份「原生可编译判定
   命令」契约（总纲 §6）就落在这个字段上。
4. **`不可编译` / `已实测失败` 必须写原因**：状态词不能当解释用。

用法：
  # 对比模式（CI 用）
  python3 tools/ci/native_product.py --root .
  # 刷新基线（**只在合并点**）
  python3 tools/ci/native_product.py --root . \
      --write-baseline tools/ci/native_product_baseline.json
  # stdlib 新增/删除了 .light：把模块表补齐（只增不改，删的只报告不代删）
  python3 tools/ci/native_product.py --root . --sync-list
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
_DEFAULT_BASELINE = os.path.join(_HERE, "native_product_baseline.json")
_DEFAULT_清单 = os.path.join("任务书", "原生腿产品清单.json")
_CLI源 = os.path.join("cli", "light.py")

模块状态值域 = ("可编译", "不可编译", "未实测")
CLI状态值域 = ("可用", "坏", "未实现", "未实测")
矩阵状态值域 = ("已实测通过", "已实测失败", "桩", "未实测")

模块必填 = ("模块", "状态", "阻断原因", "证据", "备注")
CLI必填 = ("路径", "后端取值", "状态", "证据", "备注")
矩阵必填 = ("平台", "能力", "状态", "证据", "备注")

_RE_后端取值 = re.compile(r"--backend\s+([\w\-/ ]+)")

# B9 版清单里用了值域外的状态词。这里做同义词归一而不是去改 B9 的清单：
# 清单所有权在 B9（任务书 G9 §2.2），门禁只负责判。语义对齐理由写在值里。
CLI状态同义 = {
    "未打通": "未实现",      # 「原生腿能 import stdlib」这条路径尚未实现，不是坏掉
}



_spec = importlib.util.spec_from_file_location(
    "_g9_np_bootstrap_rate", os.path.join(_HERE, "bootstrap_rate.py"))
_BR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_BR)

# `add_argument('--backend', choices=['antlr', 'src', ...])`：跨行也要抓得到，
# 所以按 re.S 从 `--backend` 一路吃到第一个 `]`。
_RE_BACKEND = re.compile(r"--backend['\"].{0,200}?choices\s*=\s*\[([^\]]*)\]", re.S)
_RE_取值 = re.compile(r"['\"]([^'\"]+)['\"]")


def _posix(path):
    """键一律走 POSIX `/`：跨平台可比，不许带 os.sep（gitea run 71 教训）。"""
    return path.replace("\\", "/")


def 规范化(data):
    """把 B9 版清单的形状归一成门禁判的三张平表。

    B9 是清单所有权方（任务书 G9 §2.2「清单由 B9 产出」），所以**清单不动、门禁适配**：

      - `stdlib原生可编译矩阵`：dict{模块: {状态, 阻断}} → 平表 `模块表`
      - `CLI路径状态表`：{命令, 前端, 后端, 状态, 说明} → 平表 `CLI路径表`
        （`后端取值` 从 `命令` 串里的 `--backend X / Y` 抽出来，不再要求 B9 手填）
      - `平台矩阵`：宽表（每行一个平台、每列一个能力）→ 长表（一格一条）
        状态词映射：`真实测*`→已实测通过，`桩*`→桩，`未实测*`→未实测

    已经是门禁形状（G9 骨架那种）的清单原样返回，两种都能读。
    """
    if all(isinstance(data.get(k), list) for k in ("模块表", "CLI路径表", "平台矩阵")):
        return data

    依据 = str(data.get("依据", "")).strip()
    出 = dict(data)

    模块表 = []
    for 模块, v in (data.get("stdlib原生可编译矩阵") or {}).items():
        v = v if isinstance(v, dict) else {}
        状态 = v.get("状态", "未实测")
        阻断 = str(v.get("阻断", "")).strip()
        模块表.append({
            "模块": 模块,
            "状态": 状态,
            "阻断原因": "" if 状态 == "可编译" else 阻断,
            # 可编译必须有一条含 light 的可复跑命令：B9 的 依据 字段就是那条判定命令
            "证据": (v.get("证据") or 依据) if 状态 == "可编译" else "",
            "备注": 阻断 if 状态 == "可编译" else "",
        })
    出["模块表"] = 模块表

    CLI表 = []
    for 条 in (data.get("CLI路径状态表") or []):
        命令 = str(条.get("命令", "")).strip()
        取值 = []
        for m in _RE_后端取值.finditer(命令):
            取值 += [t.strip() for t in m.group(1).split("/") if t.strip()]
        原状态 = 条.get("状态", "未实测")
        CLI表.append({
            "路径": 命令,
            "后端取值": 取值,
            "状态": CLI状态同义.get(原状态, 原状态),
            "证据": str(条.get("后端", "")).strip(),
            "备注": str(条.get("说明", "")).strip(),
        })
    出["CLI路径表"] = CLI表

    宽 = data.get("平台矩阵") or []
    if 宽 and isinstance(宽[0], dict) and "能力" not in 宽[0]:
        长 = []
        for 行 in 宽:
            平台 = 行.get("平台", "?")
            for 能力, 值 in 行.items():
                if 能力 == "平台":
                    continue
                原 = str(值).strip()
                if 原.startswith("真实测"):
                    状态 = "已实测通过"
                elif 原.startswith("桩"):
                    状态 = "桩"
                elif 原.startswith("未实测"):
                    状态 = "未实测"
                else:
                    状态 = "已实测失败"
                长.append({
                    "平台": 平台,
                    "能力": 能力,
                    "状态": 状态,
                    "证据": 原 if 状态 == "已实测通过" else "",
                    "备注": 原,
                })
        出["平台矩阵"] = 长
    return 出


def 读清单(path):
    with io.open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    data = 规范化(data)
    for 表 in ("模块表", "CLI路径表", "平台矩阵"):
        if not isinstance(data.get(表), list) or not data[表]:
            raise ValueError("清单缺 `%s` 数组或为空" % 表)
    return data



def 实际模块名(root):
    """`stdlib/` 下所有 `.light` 的模块名（含子目录），排序返回。

    与 `bootstrap_rate.scan_stdlib` 同一套枚举（`iter_light_files`），
    免得两条指标的分母来自两份口径。
    """
    stdlib_dir = os.path.join(root, "stdlib")
    if not os.path.isdir(stdlib_dir):
        return []
    名 = [os.path.basename(f)[:-len(".light")]
          for f in _BR.iter_light_files(stdlib_dir)]
    return sorted(名)


def 源码后端取值(root, cli源=None):
    """从 `cli/light.py` 里抓出所有 `--backend` 的 choices 取值（去重排序）。

    **不记行号**：门禁基线的键带行号会造幻影红（第七轮 A7 已踩）。这里只要
    「源码承诺了哪些取值」这个集合，行号无关。
    """
    path = cli源 or os.path.join(root, _CLI源)
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    出 = set()
    for m in _RE_BACKEND.finditer(src):
        出.update(_RE_取值.findall(m.group(1)))
    return sorted(出)


def _校验表(条目, 必填, 值域, 键名, 标签):
    """三张表的公共校验：字段齐、键不重、状态在值域内。返回 (问题, 状态计数)。"""
    问题 = []
    计数 = {s: 0 for s in 值域}
    见过 = set()
    for i, 条 in enumerate(条目, 1):
        键 = " / ".join(str(条.get(k, "")) for k in 键名) or "第%d项" % i
        缺 = [f for f in 必填 if f not in 条]
        if 缺:
            问题.append("%s %s 缺字段：%s" % (标签, 键, "、".join(缺)))
            continue
        if 键 in 见过:
            问题.append("%s %s 条目重复" % (标签, 键))
            continue
        见过.add(键)
        状态 = 条["状态"]
        if 状态 not in 值域:
            问题.append("%s %s 状态 `%s` 不在值域 %s 内"
                        % (标签, 键, 状态, "/".join(值域)))
            continue
        计数[状态] += 1
    return 问题, 计数


def 校验(root, data):
    问题 = []

    # —— 表一：模块表 ——
    模块问题, 模块计数 = _校验表(data["模块表"], 模块必填, 模块状态值域,
                                ("模块",), "模块表")
    问题 += 模块问题
    for 条 in data["模块表"]:
        if 条.get("状态") == "不可编译" and not str(条.get("阻断原因", "")).strip():
            问题.append("模块表 %s 状态是不可编译但阻断原因为空 —— 状态词不能当解释用"
                        % 条.get("模块"))
        if 条.get("状态") == "可编译":
            证据 = str(条.get("证据", "")).strip()
            if not 证据:
                问题.append("模块表 %s 声称可编译但没有证据（要一条可复跑的判定命令）"
                            % 条.get("模块"))
            elif "light" not in 证据:
                问题.append("模块表 %s 的证据 `%s` 里没有可复跑的 light 命令"
                            % (条.get("模块"), 证据[:60]))
    真模块 = 实际模块名(root)
    表模块 = {条.get("模块") for 条 in data["模块表"]}
    漏 = sorted(set(真模块) - 表模块)
    吹 = sorted(表模块 - set(真模块))
    if 漏:
        问题.append("stdlib 里有、模块表没登记的 .light（防腐烂）：%s" % "、".join(漏))
    if 吹:
        问题.append("模块表里有、stdlib 里不存在的模块（防吹牛）：%s" % "、".join(吹))

    # —— 表二：CLI 路径表 ——
    cli问题, cli计数 = _校验表(data["CLI路径表"], CLI必填, CLI状态值域,
                              ("路径",), "CLI路径表")
    问题 += cli问题
    for 条 in data["CLI路径表"]:
        if 条.get("状态") == "坏" and not str(条.get("备注", "")).strip():
            问题.append("CLI路径表 %s 标成坏但备注为空（坏在哪、怎么处置要写明）"
                        % 条.get("路径"))
    try:
        真取值 = 源码后端取值(root)
    except OSError as e:
        问题.append("读不动 %s：%s" % (_posix(_CLI源), e))
        真取值 = []
    表取值 = set()
    for 条 in data["CLI路径表"]:
        v = 条.get("后端取值")
        if isinstance(v, list):
            表取值.update(v)
        elif v:
            表取值.add(v)
    未登记 = sorted(set(真取值) - 表取值)
    if 未登记:
        问题.append("cli/light.py 的 --backend choices 里有、CLI路径表没登记的取值："
                    "%s（新加一条后端就得给它记账，包括「它到底能不能用」）"
                    % "、".join(未登记))
    已摘除 = sorted(表取值 - set(真取值))

    # —— 表三：平台矩阵 ——
    矩阵问题, 矩阵计数 = _校验表(data["平台矩阵"], 矩阵必填, 矩阵状态值域,
                                ("平台", "能力"), "平台矩阵")
    问题 += 矩阵问题
    for 条 in data["平台矩阵"]:
        if 条.get("状态") == "已实测失败" and not str(条.get("备注", "")).strip():
            问题.append("平台矩阵 %s/%s 标成已实测失败但备注为空"
                        % (条.get("平台"), 条.get("能力")))
        if 条.get("状态") == "已实测通过" and not str(条.get("证据", "")).strip():
            问题.append("平台矩阵 %s/%s 声称已实测通过但没有证据"
                        "（哪台机器、哪条命令、哪个测试）"
                        % (条.get("平台"), 条.get("能力")))

    模块总 = len(data["模块表"])
    统计 = {
        "module_total": 模块总,
        "module_compilable": 模块计数["可编译"],
        "module_untested": 模块计数["未实测"],
        "module_rate": (模块计数["可编译"] / 模块总) if 模块总 else 0.0,
        "cli_broken": cli计数["坏"],
        "cli_total": len(data["CLI路径表"]),
        "matrix_untested": 矩阵计数["未实测"],
        "matrix_passed": 矩阵计数["已实测通过"],
        "matrix_stub": 矩阵计数["桩"],
        "matrix_total": len(data["平台矩阵"]),
        "backend_choices": 真取值,
        "backend_已摘除": 已摘除,
    }
    return 问题, 统计


def sync_list(root, 清单路径):
    """把 `stdlib/` 下新增的 `.light` 补进模块表（状态 `未实测`）。只增不改。

    **按清单原始形状回写**：B9 版的模块表是 `stdlib原生可编译矩阵`（dict），
    要是把门禁内部归一后的平表 dump 回去，等于用适配层覆盖了所有权方的清单。
    """
    with io.open(清单路径, encoding="utf-8") as fh:
        raw = json.load(fh)
    真 = 实际模块名(root)
    if isinstance(raw.get("stdlib原生可编译矩阵"), dict):
        矩阵 = raw["stdlib原生可编译矩阵"]
        新增 = [名 for 名 in 真 if 名 not in 矩阵]
        多余 = sorted(set(矩阵) - set(真))
        for 名 in 新增:
            矩阵[名] = {"状态": "未实测", "阻断": ""}
    else:
        有 = {条.get("模块") for 条 in raw.get("模块表", [])}
        新增 = [名 for 名 in 真 if 名 not in 有]
        多余 = sorted(有 - set(真))
        raw.setdefault("模块表", [])
        for 名 in 新增:
            raw["模块表"].append({
                "模块": 名, "状态": "未实测", "阻断原因": "", "证据": "", "备注": "",
            })
    with io.open(清单路径, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(raw, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("[原生产品门禁] 已补入 %d 条模块（状态 未实测）：%s"
          % (len(新增), "、".join(新增) or "（无）"))
    if 多余:
        print("[原生产品门禁] 模块表里有 %d 条 stdlib 已不存在：%s（**不代删**）"
              % (len(多余), "、".join(多余)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="仓库根目录，默认当前目录")
    ap.add_argument("--list", dest="清单", default=None,
                    help="清单路径，默认 <root>/任务书/原生腿产品清单.json")
    ap.add_argument("--baseline", default=_DEFAULT_BASELINE, help="基线快照路径")
    ap.add_argument("--write-baseline", metavar="PATH", help="把本次结果写成新基线并退出")
    ap.add_argument("--sync-list", action="store_true",
                    help="把 stdlib 新增的 .light 补进模块表后退出（只增不改）")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("[原生产品门禁] 仓库根不存在：%s" % args.root)
        return 2

    清单路径 = args.清单 or os.path.join(args.root, _DEFAULT_清单)
    try:
        data = 读清单(清单路径)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print("[原生产品门禁] 读不动清单 %s：%s" % (清单路径, e))
        return 2

    if args.sync_list:
        return sync_list(args.root, 清单路径)

    问题, 统计 = 校验(args.root, data)

    print("[原生产品门禁] 模块表：可编译 %d / %d = %.2f%%（未实测 %d）"
          % (统计["module_compilable"], 统计["module_total"],
             统计["module_rate"] * 100, 统计["module_untested"]))
    print("[原生产品门禁] CLI 路径表：共 %d 条，其中坏 %d 条；"
          "源码 --backend choices = %s"
          % (统计["cli_total"], 统计["cli_broken"],
             "/".join(统计["backend_choices"]) or "（空）"))
    if 统计["backend_已摘除"]:
        print("[原生产品门禁] 告警（不判红）：CLI路径表登记了源码里已无的后端取值：%s"
              "（摘除死腿是许可处置，记得同步把表里那条改成 未实现 或删除）"
              % "、".join(统计["backend_已摘除"]))
    print("[原生产品门禁] 平台矩阵：%d 格，已实测通过 %d / 桩 %d / 未实测 %d"
          % (统计["matrix_total"], 统计["matrix_passed"],
             统计["matrix_stub"], 统计["matrix_untested"]))

    if 问题:
        print("[原生产品门禁] 红：清单有 %d 处不合规：" % len(问题))
        for p in 问题:
            print("       ! %s" % p)
        return 1

    if args.write_baseline:
        out = {
            "version": 1,
            "note": ("原生腿产品清单基线（第九轮 G9 建）。口径见 "
                     "tools/ci/native_product.py docstring。"
                     "module_rate 只升不降；module_untested 只降不升；"
                     "cli_broken 只降不升；matrix_untested 只降不升；"
                     "matrix_passed 只升不降。**只在合并点重建**（总纲 §5 红线 5）。"),
            "built_from_commit": _BR._当前提交(args.root),
            "list_path": _posix(_DEFAULT_清单),
        }
        for k in ("module_total", "module_compilable", "module_untested",
                  "module_rate", "cli_broken", "cli_total",
                  "matrix_untested", "matrix_passed", "matrix_stub",
                  "matrix_total"):
            out[k] = 统计[k]
        with io.open(args.write_baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("[原生产品门禁] 已写入基线 %s" % args.write_baseline)
        return 0

    try:
        with io.open(args.baseline, encoding="utf-8") as fh:
            baseline = json.load(fh)
    except (FileNotFoundError, ValueError):
        print("[原生产品门禁] 找不到（或读不动）基线 %s。"
              "首次接入请先 --write-baseline 生成并提交。" % args.baseline)
        return 2

    red = False

    def 只升(键, 名, 单位=""):
        """当前值不许低于基线。"""
        base = baseline.get(键)
        if base is None:
            print("[原生产品门禁] 红：基线缺 %s 字段，该维度无法判定。重建基线。" % 键)
            return True
        cur = 统计[键]
        if cur < base - 1e-9:
            print("[原生产品门禁] 红：%s %s%s 低于基线 %s%s（只许升不许降）。"
                  % (名, _数(cur), 单位, _数(base), 单位))
            return True
        if cur > base + 1e-9:
            print("[原生产品门禁] %s 提升 %s%s → %s%s（在合并点刷新基线）。"
                  % (名, _数(base), 单位, _数(cur), 单位))
        return False

    def 只降(键, 名, 理由=""):
        """当前值不许高于基线。"""
        base = baseline.get(键)
        if base is None:
            print("[原生产品门禁] 红：基线缺 %s 字段，该维度无法判定。重建基线。" % 键)
            return True
        cur = 统计[键]
        if cur > base:
            print("[原生产品门禁] 红：%s %d 高于基线 %d（只许降不许升）。%s"
                  % (名, cur, base, 理由))
            return True
        if cur < base:
            print("[原生产品门禁] %s 下降 %d → %d（在合并点刷新基线）。" % (名, base, cur))
        return False

    red = 只升("module_rate", "原生可编译比例") or red
    red = 只降("module_untested", "模块表未实测数",
               "「没测过」不算进步，只能越来越少。") or red
    red = 只降("cli_broken", "CLI 坏路径数",
               "坏路径要么修好要么摘掉，不许新增一条死腿。") or red
    red = 只降("matrix_untested", "平台矩阵未实测格数",
               "这条专治「只在 Windows 测过就声称跨平台」。") or red
    red = 只升("matrix_passed", "平台矩阵已实测通过格数") or red
    red = 只降("matrix_stub", "平台矩阵桩格数",
               "桩不是实现：POSIX TLS 的 dv_tls_unsupported 这类格子只能越来越少。") or red

    base_总 = baseline.get("module_total")
    if base_总 is not None and 统计["module_total"] < base_总:
        print("[原生产品门禁] 红：模块表总数 %d 低于基线 %d —— 分母缩小会让比例虚涨；"
              "确实删了 stdlib 模块的，在交付报告里写明并在合并点重建基线。"
              % (统计["module_total"], base_总))
        red = True

    if red:
        return 1
    print("[原生产品门禁] 通过：三张表合规、模块表与 stdlib 双向咬合、"
          "后端取值全登记、可编译比例未降、未实测与坏路径未增。")
    return 0


def _数(v):
    return ("%.2f%%" % (v * 100)) if isinstance(v, float) else str(v)


if __name__ == "__main__":
    sys.exit(main())
