# -*- coding: utf-8 -*-
r"""地板自举率门禁（第九轮 G9 建，M22 的新增子判据）。

## 为什么要有这条门禁

`stdlib/builtins.py`（1068 行 / 114 个顶层函数）由 `src/code_generator.py:735-741`
在每一份生成产物的序言里按路径加载进来，**每个光明程序都站在它上面**。连自称
「零导入零引 Python」的 `stdlib/文件流.light` 都在用它的 `读取文件/写入文件/追加文件`。

而它**没有同名 `.light`**，于是：

  - `bootstrap_rate.py` 的文件维度分母是「`stdlib/` 下的 `.light` 个数」→ 它不在分母里
  - `python_direct_calls.py` 只扫 `.light` 里的 `导入 os` → 它是 `.py`，也不在
  - `引 Python` 计数只认关键字 → 更看不见

**六轮来最大的度量盲区**：地板是 Python 写的，上面盖的楼算不算「纯光明」是个
相对概念。本脚本把这块地板变成一条独立指标。

## 口径

清单 `任务书/自举地板清单.json` 逐个登记 `builtins.py` 的顶层函数：

    地板自举率 = 纯光明实现数 / (总数 − native_required 数)

**分母扣掉真边界**（任务书 G9 §2.1）：文件 I/O、环境变量、进程、stdin/stdout、
时间戳、随机源这些必须落到系统调用的东西，用光明写不出来也不该假装写得出来。
不扣的话这条指标永远到不了 100%，就会变成没人看的摆设。

**分子只数「地板真的搬过去了」的条目**：`分类 == has_light_impl` 只表示光明替身
已就位；必须 `builtins.py` 里该函数体真的转发到那个光明模块才计入分子。
S1 合并点裁决（`任务书/地板清单裁决_S1.md` §4）：12 条替身是真的，但
`builtins.py:482 分割字符串` 还是 `return text.split(separator)`，运行期跑的仍是
Python —— 「隔壁有个同名光明文件」不算搬迁，否则这条指标就是自我表扬。

## 三条防造假（每条都能反跑，见 tests/unit/test_ci_gates_round9.py）

1. **名单双向咬合**：清单条目名集合必须**逐个等于** `builtins.py` 里 `ast` 解析出的
   顶层函数名集合。代码里加了新内置、清单没登记 → 红（防腐烂）；清单写了代码里
   不存在的名字 → 红（防吹牛）。这条让分母不可能被偷偷改小。

2. **证据必须指到真的 `段落` 定义行**：登记成 `light` 的条目，其 `证据` 形如
   `stdlib/内置核心.light:42`，判据是**行号 ±2 窗口内存在一行「既是定义行、又含该
   函数名」**。照 `tests/unit/test_native_leg_capability.py:186` 收紧后的口径来 ——
   B7 原稿只断「1 ≤ 行号 ≤ 总行数」，四千行文件里任何数字都过，那种上界断言等于
   判据不存在。±2 是给正常编辑漂移留的余量，不是给蒙数字留的。

3. **不认被遮蔽的落点**：证据所在 `.light` 如果有同名 `.py` 且首两行没有魔数
   「纯光明实现」，运行期真正被执行的是那个 `.py`（`stdlib/_light_import_hook.py`
   让 `.py` 绝对优先）。这种「写了但跑不到」的实现不计入分子，直接判红。

## 基线（棘轮，三个方向都锁）

- `rate` 只升不降 —— 主指标
- `native_required_count` **只降不升** —— 否则把做不动的函数挪进豁免就能凭空涨点
- `denominator` **只升不降** —— 同一件事的另一面，双向锁死
- `native_required` 名单：新增名字即红并逐个点名（要改豁免范围得先说服主线）

## 谁填哪个字段

清单结构以 C9 版为准（任务书 C9 §3 要求分五类：`native_required` / `movable` /
`has_light_impl` / `duplicate` / `unused`；布尔字段表达不了 duplicate 与 unused，
而这两类是 S3 删码的输入）。字段归属：

- **C9**：`当前实现语言` / `目标落点` / `证据行`（搬迁进度是它的活）
- **G9**：`分类`（分母口径归度量方，改它要走主线裁决，见 任务书/地板清单裁决_S1.md）
- `native_required` 必须在 `目标落点` 里写清为什么是真边界、原生腿哪个符号对应
  （这条同时是 B9 的输入），不许只打个标签就把分母改小。

用法：
  # 对比模式（CI 用）
  python3 tools/ci/floor_bootstrap.py --root .
  # 刷新基线（搬迁一批之后手工执行并提交，只在合并点做）
  python3 tools/ci/floor_bootstrap.py --root . \
      --write-baseline tools/ci/floor_bootstrap_baseline.json
  # 清单与 builtins.py 漂移了：把缺的条目补进清单（新条目 native_required 留 null，
  # 门禁会因「未分类」判红，逼人做裁决而不是默默放过）
  python3 tools/ci/floor_bootstrap.py --root . --sync-list
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import io
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_BASELINE = os.path.join(_HERE, "floor_bootstrap_baseline.json")
_DEFAULT_清单 = os.path.join("任务书", "自举地板清单.json")
_地板源 = os.path.join("stdlib", "builtins.py")

必填字段 = ("名字", "职责", "当前实现语言", "分类", "目标落点", "证据行")
分类值域 = ("native_required", "movable", "has_light_impl", "duplicate", "unused")

# 复用 bootstrap_rate 的两个既定口径：定义行判据（RE_DECL）与魔数判据（_是纯光明）。
# 再写第二份必然分叉——第二轮就是三个自举率口径互相打架。
_spec = importlib.util.spec_from_file_location(
    "_g9_bootstrap_rate", os.path.join(_HERE, "bootstrap_rate.py"))
_BR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_BR)

RE_DECL = _BR.RE_DECL
_是纯光明 = _BR._是纯光明

_RE_证据 = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+)$")

窗口 = 2      # 证据行号容许的漂移窗口（行）


def _posix(path):
    """键一律走 POSIX `/`：基线要跨平台可比，不许带 os.sep（gitea run 71 教训）。"""
    return path.replace("\\", "/")


def 读地板函数名(root, 源=None):
    """用 `ast` 解析 `stdlib/builtins.py`，返回顶层函数名的有序列表。

    为什么用 ast 而不是正则：正则会把 docstring / 字符串里的 `def x(` 一起抓进来，
    分母被污染的门禁比没有门禁更糟（它会给出一个看起来精确的错数字）。
    带下划线前缀的私有函数（`_读文件`）也算 —— 它同样被产物调用
    （`src/code_generator.py:748` 的兜底里就有它）。
    """
    path = 源 or os.path.join(root, _地板源)
    with io.open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    return [n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def 读地板函数节点(root, 源=None):
    """返回 {函数名: ast 函数节点}，用于判「是不是真转发到光明实现」。

    分子不能只看「有没有同名光明实现」：`stdlib/字符串工具轻量.light` 写好了，
    但 `builtins.py:482 分割字符串` 的函数体还是 `return text.split(separator)`，
    运行期每一份产物执行的仍然是 Python —— 那就不算地板搬迁（S1 合并点裁决，
    见 任务书/地板清单裁决_S1.md §4）。
    """
    path = 源 or os.path.join(root, _地板源)
    with io.open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    return {n.name: n for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def 是否转发(节点, 模块名):
    """函数体里是否真的引用了光明模块 `模块名`。

    **只认 ast 里的标识符与 import，不做文本包含判定**。文本判定连踩两次假绿：
      - 签名行 `def 解析JSON(...)` 自带 `JSON`；
      - 错误串 `raise RuntimeError(f"JSON 解析失败: {e}")` 也自带 `JSON`；
      - `美化JSON` 里调的是兄弟 Python 函数 `序列化JSON`，同样含 `JSON`。
    三条都会让「隔壁有个同名光明文件」冒充「地板已搬迁」。
    """
    if 节点 is None or not 模块名:
        return False
    for 子 in ast.walk(节点):
        if isinstance(子, ast.Import):
            for a in 子.names:
                if a.name.split(".")[0] == 模块名:
                    return True
        elif isinstance(子, ast.ImportFrom):
            if (子.module or "").split(".")[0] == 模块名:
                return True
        elif isinstance(子, ast.Name) and 子.id == 模块名:
            return True
        elif isinstance(子, ast.Attribute) and 子.attr == 模块名:
            return True
    return False


def 读清单(path):
    with io.open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    条目 = data.get("函数")
    if not isinstance(条目, list) or not 条目:
        raise ValueError("清单缺 `函数` 数组或为空")
    return data, 条目



def 校验证据(root, 证据, 名字):
    """证据必须指到真的 `段落/类/函数` 定义行。返回 (问题字符串或 None, 模块名或 None)。

    判据（都可反跑）：
      1. 形如 `path:line`；
      2. 文件存在；
      3. **行号 ±2 窗口内有一行「既是定义行、又含该函数名」** —— 只断
         「行号在文件范围内」是上界断言，等于没判；
      4. 该 `.light` 不被同名 `.py` 遮蔽（有 `.py` 就必须首两行挂魔数）。
    """
    m = _RE_证据.match(str(证据).strip())
    if not m:
        return "证据行 `%s` 不是 `文件:行号` 形态" % 证据, None
    rel = m.group("file").strip()
    行号 = int(m.group("line"))
    full = os.path.join(root, rel.replace("/", os.sep))
    if not os.path.isfile(full):
        return "证据文件不存在：%s" % rel, None
    if not rel.endswith(".light"):
        return ("证据行指向 %s 而不是 `.light`：这个字段要证明「光明实现存在」，"
                "指到 builtins.py 只能证明「Python 版存在」，自我否证" % rel), None
    with io.open(full, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    if not (1 <= 行号 <= len(lines)):
        return "证据 %s:%d 行号越界（文件共 %d 行）" % (rel, 行号, len(lines)), None
    起 = max(0, 行号 - 1 - 窗口)
    止 = min(len(lines), 行号 + 窗口)
    命中 = [i + 1 for i in range(起, 止)
            if RE_DECL.search(lines[i]) and 名字 in lines[i]]
    if not 命中:
        return ("证据 %s:%d 的 ±%d 行窗口里找不到「既是 段落/类/函数 定义行、"
                "又含 `%s`」的行（当前行：%s）"
                % (rel, 行号, 窗口, 名字, lines[行号 - 1].strip()[:60])), None
    影子 = full[:-len(".light")] + ".py"
    if os.path.isfile(影子) and not _是纯光明(full):
        return ("落点 %s 有同名 `.py` 且首两行无魔数「纯光明实现」→ 运行期真正被"
                "执行的是那个 `.py`，这份光明实现跑不到，不算搬迁" % rel), None
    模块名 = os.path.basename(rel)[:-len(".light")]
    return None, 模块名


def 校验(root, 条目, 真名单, 函数节点):
    """返回 (问题清单, 统计字典)。

    分子口径（S1 合并点裁决，任务书/地板清单裁决_S1.md §4）：
    `has_light_impl` 只表示「光明替身已就位」，**不等于地板已搬迁**。
    只有 `builtins.py` 里该函数体真的转发到那个光明模块（函数体内出现证据文件的
    模块名）才计入分子 —— 否则运行期跑的还是 Python，指标就成了「隔壁有个同名
    文件」的自我表扬。
    """
    问题 = []
    见过 = set()
    清单名 = []
    已转发 = 0
    待接线 = []
    边界数 = 0
    未分类 = []
    for i, 条 in enumerate(条目, 1):
        名字 = 条.get("名字", "第%d项(无名字)" % i)
        缺 = [f for f in 必填字段 if f not in 条]
        if 缺:
            问题.append("%s 缺字段：%s" % (名字, "、".join(缺)))
            continue
        if 名字 in 见过:
            问题.append("%s 条目重复" % 名字)
            continue
        见过.add(名字)
        清单名.append(名字)

        if not str(条["职责"]).strip():
            问题.append("%s 职责为空（登记不写职责，后面没人判得出该不该搬）" % 名字)

        分类 = 条["分类"]
        if 分类 is None or not str(分类).strip():
            未分类.append(名字)
            continue
        if 分类 not in 分类值域:
            问题.append("%s 分类 `%s` 不在值域 %s 内"
                        % (名字, 分类, "/".join(分类值域)))
            continue

        if 分类 == "native_required":
            边界数 += 1
            if not str(条["目标落点"]).strip():
                问题.append("%s 是 native_required 但目标落点为空 —— 豁免会缩小分母，"
                            "必须写清为什么是真边界、原生腿由哪个符号对应" % 名字)
            continue

        if 分类 == "has_light_impl":
            坏, 模块名 = 校验证据(root, 条["证据行"], 名字)
            if 坏:
                问题.append("%s 登记为 has_light_impl 但%s" % (名字, 坏))
                continue
            体 = 函数节点.get(名字)
            if 模块名 and 是否转发(体, 模块名):
                已转发 += 1
            else:
                待接线.append("%s→%s" % (名字, 模块名))

    if 未分类:
        问题.append("以下 %d 条 分类 为空（未分类）：%s。"
                    "新条目由 --sync-list 补进来时留空，必须做完裁决再进 CI ——"
                    "留空就等于分母口径没定"
                    % (len(未分类), "、".join(未分类[:20])))

    真集 = set(真名单)
    清单集 = set(清单名)
    漏登记 = sorted(真集 - 清单集)
    吹牛 = sorted(清单集 - 真集)
    if 漏登记:
        问题.append("builtins.py 里有、清单里没有的函数（防腐烂）：%s"
                    % "、".join(漏登记))
    if 吹牛:
        问题.append("清单里有、builtins.py 里没有的函数（防吹牛）：%s"
                    % "、".join(吹牛))

    分母 = len(清单名) - 边界数
    return 问题, {
        "total": len(清单名),
        "native_required_count": 边界数,
        "denominator": 分母,
        "light_count": 已转发,
        "pending_wiring": sorted(待接线),
        "rate": (已转发 / 分母) if 分母 else 0.0,
        "native_required": sorted(条["名字"] for 条 in 条目
                                  if 条.get("分类") == "native_required"),
    }



def sync_list(root, 清单路径, 真名单):
    """把 `builtins.py` 里新出现的函数补进清单（`native_required` 留 null）。

    **只增不改**：已有条目一个字段都不动 —— 这里要是覆盖了 C9 填的证据，
    一次误跑就把搬迁进度抹平了。清单里多出来的（代码已删）只报告，不代删：
    删条目是记账动作，得由人决定并写进交付报告。
    """
    data, 条目 = 读清单(清单路径)
    有 = {条.get("名字") for 条 in 条目}
    新增 = [名 for 名 in 真名单 if 名 not in 有]
    多余 = [名 for 名 in sorted(有 - set(真名单)) if 名]
    for 名 in 新增:
        条目.append({
            "名字": 名,
            "职责": "",
            "当前实现语言": "Python（builtins.py）",
            "分类": "",
            "目标落点": "",
            "证据行": "",
        })
    data["函数"] = 条目
    with io.open(清单路径, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("[地板门禁] 已补入 %d 条新条目（分类留空，待裁决）：%s"
          % (len(新增), "、".join(新增) or "（无）"))
    if 多余:
        print("[地板门禁] 清单里有 %d 条 builtins.py 已不存在：%s"
              "（**不代删**：删条目要写进交付报告）" % (len(多余), "、".join(多余)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    # 默认 `.` 与 CI 显式传的 `--root .` 一致：第七轮 E7 踩过默认值不一致造 424 条幻影。
    ap.add_argument("--root", default=".", help="仓库根目录，默认当前目录")
    ap.add_argument("--list", dest="清单", default=None,
                    help="清单路径，默认 <root>/任务书/自举地板清单.json")
    ap.add_argument("--builtins", default=None,
                    help="地板源路径，默认 <root>/stdlib/builtins.py")
    ap.add_argument("--baseline", default=_DEFAULT_BASELINE, help="基线快照路径")
    ap.add_argument("--write-baseline", metavar="PATH", help="把本次结果写成新基线并退出")
    ap.add_argument("--sync-list", action="store_true",
                    help="把 builtins.py 里新出现的函数补进清单后退出（只增不改）")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("[地板门禁] 仓库根不存在：%s" % args.root)
        return 2

    清单路径 = args.清单 or os.path.join(args.root, _DEFAULT_清单)
    try:
        真名单 = 读地板函数名(args.root, args.builtins)
        函数节点 = 读地板函数节点(args.root, args.builtins)
    except (OSError, SyntaxError, ValueError) as e:
        print("[地板门禁] 读不动地板源 %s：%s"
              % (args.builtins or _地板源, e))
        return 2
    try:
        data, 条目 = 读清单(清单路径)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print("[地板门禁] 读不动清单 %s：%s（首次接入见脚本 docstring）"
              % (清单路径, e))
        return 2

    if args.sync_list:
        return sync_list(args.root, 清单路径, 真名单)

    问题, 统计 = 校验(args.root, 条目, 真名单, 函数节点)

    print("[地板门禁] 地板源 %s：%d 个顶层函数；清单 %s：%d 条"
          % (_posix(_地板源), len(真名单), _posix(_DEFAULT_清单), 统计["total"]))
    print("[地板门禁] 地板自举率 = %d/%d = %.2f%%（分母已扣掉 %d 条 native_required 真边界）"
          % (统计["light_count"], 统计["denominator"], 统计["rate"] * 100,
             统计["native_required_count"]))
    if 统计["pending_wiring"]:
        print("[地板门禁] 光明替身已就位但 builtins.py 尚未转发的 %d 条（不计入分子）：%s"
              % (len(统计["pending_wiring"]), "、".join(统计["pending_wiring"])))

    if 问题:
        print("[地板门禁] 红：清单有 %d 处不合规：" % len(问题))
        for p in 问题:
            print("       ! %s" % p)
        return 1

    if args.write_baseline:
        out = {
            "version": 1,
            "note": ("地板自举率基线（第九轮 G9 建）。口径见 tools/ci/floor_bootstrap.py "
                     "docstring。rate 只升不降；native_required_count 只降不升；"
                     "denominator 只升不降；native_required 名单新增即红。"
                     "**只在合并点重建**（总纲 §5 红线 5）。"),
            "built_from_commit": _BR._当前提交(args.root),
            "list_path": _posix(_DEFAULT_清单),
            "builtins_path": _posix(_地板源),
            "total": 统计["total"],
            "native_required_count": 统计["native_required_count"],
            "denominator": 统计["denominator"],
            "light_count": 统计["light_count"],
            "rate": 统计["rate"],
            "native_required": 统计["native_required"],
        }
        with io.open(args.write_baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("[地板门禁] 已写入基线 %s（%.2f%% = %d/%d）"
              % (args.write_baseline, 统计["rate"] * 100,
                 统计["light_count"], 统计["denominator"]))
        return 0

    try:
        with io.open(args.baseline, encoding="utf-8") as fh:
            baseline = json.load(fh)
    except (FileNotFoundError, ValueError):
        print("[地板门禁] 找不到（或读不动）基线 %s。"
              "首次接入请先 --write-baseline 生成并提交。" % args.baseline)
        return 2

    red = False
    base_rate = baseline.get("rate", 0.0)
    base_边界 = baseline.get("native_required_count")
    base_分母 = baseline.get("denominator")
    base_名单 = set(baseline.get("native_required", []))

    if base_边界 is None or base_分母 is None:
        print("[地板门禁] 红：基线缺 native_required_count / denominator 字段，"
              "分母维度无法判定。重新 --write-baseline 生成。")
        return 1
    if base_分母 + base_边界 != baseline.get("total"):
        print("[地板门禁] 红：基线自相矛盾 —— denominator %s + native_required_count %s "
              "≠ total %s，基线被手改过。" % (base_分母, base_边界, baseline.get("total")))
        return 1

    新增豁免 = sorted(set(统计["native_required"]) - base_名单)
    if 新增豁免:
        print("[地板门禁] 红：native_required 名单新增 %d 条：%s"
              % (len(新增豁免), "、".join(新增豁免)))
        print("       为什么是红：豁免直接缩小分母，把做不动的函数挪进来就能凭空涨点。"
              "确实是真边界的，先在交付报告里给出理由并请主线裁决，再随基线一起改。")
        red = True

    if 统计["native_required_count"] > base_边界:
        print("[地板门禁] 红：native_required 条数 %d 高于基线 %d（只许降不许升）。"
              % (统计["native_required_count"], base_边界))
        red = True
    if 统计["denominator"] < base_分母:
        print("[地板门禁] 红：分母 %d 低于基线 %d（只许升不许降）。"
              % (统计["denominator"], base_分母))
        red = True

    if 统计["rate"] < base_rate - 1e-9:
        print("[地板门禁] 红：地板自举率 %.2f%% 低于基线 %.2f%%（只许升不许降）。"
              % (统计["rate"] * 100, base_rate * 100))
        red = True
    elif 统计["rate"] > base_rate + 1e-9:
        print("[地板门禁] 地板自举率提升 %.2f%% → %.2f%%"
              "（搬迁一批后在**合并点**用 --write-baseline 刷新基线）。"
              % (base_rate * 100, 统计["rate"] * 100))
    else:
        print("[地板门禁] 地板自举率持平基线 %.2f%%。" % (base_rate * 100))

    if red:
        return 1
    print("[地板门禁] 通过：名单与 builtins.py 双向咬合、证据可定位、"
          "豁免未扩张、分母未缩、自举率未降。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
