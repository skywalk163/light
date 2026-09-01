# -*- coding: utf-8 -*-
"""假测试门禁：只拦「新增」的假绿断言，不要求存量清零。

背景（第三轮 D3-2）：
  三轮下来最大的一类发现是「某个东西看着做了，其实没验证」。第二轮写了三条禁令
  （`第二轮总纲` §5），但禁令只是文档里一句话，没兜住——`tests/test_agent_loop_light.py`
  的 `TestMaxRounds` 用 `assert len(events) <= 3` 空转通过就是活案例。
  本脚本把禁令变成能自动拦住的门禁。

设计原则（与 `check_regression.py` 同源思路，但这是**静态扫描**、零运行时依赖）：
  - 纯正则扫 `tests/` 文本，**不起子进程、不 import 被测代码**，必须 < 5s 跑完。
  - 现有违规写进基线快照 `assert_quality_baseline.json`；**新增即红，减少要求更新基线**。
  - 一次性清零不现实（全仓量大），但必须「止血」：存量允许存在、只许减不许增。
  - 违规报告给 `file:line` + 违规类型 + 一句「为什么这是假绿」。

扫描的形态（与 `第三轮留档/假测试普查清单.md` 口径一致，第四轮 D4-1 扩了三类）：
  1) 字符串断言式：`assert '<x>' in py_code|ir|c_code|source|产物`
     —— 测的是编译器/产物输出的字面量，不是行为。
  2) 上界断言式：`assert len(...) <= N`（集合为空时恒真，最隐蔽）
     以及 `assert len(...) >= 0`（长度恒非负，恒真）。
  3) 成败都算通过：`assert returncode in [0, 1]` 这类。

第四轮 D4-1 新增三类（总纲 §2.2 实测所得，已裁决取**保守口径**）：
  4) unittest 写法的字符串断言：`self.assertIn('<x>', <产物变量>)`
     —— 与形态 1 完全同源，只是换了 unittest API 就绕过了整道门禁。
     实测 113 处 > 形态 1 的 65 处，**它放过的比它拦住的还多**。
  5) 下界断言式：`assert len(...) >= N`（N>0）与等价拼法 `assert len(...) > N`
     —— 只断「至少有几个」，多出来的、错位的、重复的一概不管；集合非空即恒真。
     合并期回补：原实现只收 `>=`，实测拦住 26 处、放过 67 处 `> `，
     「换个符号就绕过门禁」本身就是门禁最该堵的洞。
  6) 非空断言式：`assert <名字或属性> is not None` —— 只断「不是 None」，零信号。

  形态 4/5/6 一律取**保守口径**（第四轮总纲已裁决）：
  - 形态 4 沿用形态 1 的 `_STR_TARGETS` 产物变量白名单，**不扫任意字符串字面量**。
    放宽到「第一参数是字符串字面量」的全部 `assertIn` 是 636 处（52 文件），
    `self.assertIn(` 总调用 718 处（57 文件）——那个口径会把大量正当断言拖进基线。
  - 形态 6 只收「裸名字 / 点属性」这一种目标，**不收下标与函数调用**：
    `assert d['k'] is not None` 至少断了键存在（否则 KeyError），
    `assert f() is not None` 至少真调了一次 f——都还剩一点信号，保守起见不算违规。
    宽口径（任意表达式）实测 176 处，保守口径 152 处。

关于两个「零命中」形态（`trivial-ge0` / `returncode-in`）：
  这两类**当前全仓零命中**，是预防性形态而非正在生效的拦截。为免有人误以为
  它俩在拦什么，报文里单列一节「预防性形态（当前零命中）」显式点名，
  不混在命中统计里。保留而不删的理由：`len(...) >= 0` 不被形态 5 覆盖
  （形态 5 只收 N>0），删掉就真没人拦了。

用法：
  # 对比模式（CI 用，新增即红）。扫描根 = 全仓：2026-08-23 用户裁决，
  # 原来只扫 tests/，同形态违规在 tests/ 之外还有 50 条，门禁覆盖面窄于
  # 它自己声明的形态覆盖面。全仓实测 1.7s，仍在 <5s 承诺内。
  python3 tools/ci/assert_quality.py --root .
  # 第七轮 E7：`--root` 的默认值已从 `tests` 改成 `.`，与 CI 一致——
  # 忘了传参不再造出「几百条新增」的幻影（实测无参时是 424 条 + rc=1）。
  # 生成/刷新基线（修好一批后手工执行并提交）
  python3 tools/ci/assert_quality.py --root . --write-baseline tools/ci/assert_quality_baseline.json

  注意：换 --root 会让基线里所有 key 一起变（key 是相对 --root 的路径），
  必须整份重生成，不能只补差量；换根造成的「全量新增」不是回归。

关于基线的 key（2026-09-01 改）：
  原 key 是 `file:line:cat`——**带行号**。行号是这份清单里最易变、却最没有
  语义的字段：往一个测试文件中间插一段测试，其后所有断言整体下移，门禁就会
  把「同一条断言换了个行号」判成「1 条新增违规 + 1 条基线失效」，CI 直接红。
  本仓库已经这样红了三次（e7c5ccd1 / a1ed9163 / 本次），每次都要手工
  --write-baseline 重建，纯属噪声——它拦下的从来不是坏断言，只是编辑行为。

  现改为按 **(file, cat, 断言原文) 的**多重集**比对：
    - 去掉行号 → 免疫插入/删除造成的整体位移；
    - 用多重集而非集合 → 同一文件里 2 条一模一样的坏断言仍算 2 条
      （实测 468 条存量里有 48 个重复键，用集合会让「再写一条同样的」
       被第 1 条的额度吃掉，等于给复制粘贴的假绿留后门）。
  基线文件格式不变（依旧逐条带 file/line/cat/text），行号退化为给人看的
  位置提示、不参与比对，因此 v2 基线无需迁移即可直接被新逻辑消费。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tokenize
from collections import Counter


# ── 各形态的静态判定 ──────────────────────────────────────────────────────────
# 1) 字符串断言式：只拦「产物字面量」目标，避免把正常的 `in code` 也误伤成海量基线。
_STR_TARGETS = r"(?:py_code|pycode|ir|c_code|source|产物)"
RE_STRING_ASSERT = re.compile(
    r"assert\s+['\"][^'\"]*['\"]\s+in\s+" + _STR_TARGETS + r"\b"
)
# 2a) 上界断言式：len(...) <= N（集合空时恒真）
RE_UPPER_BOUND = re.compile(r"assert\s+len\([^()]*\)\s*<=\s*\d+")
# 2b) 恒真断言式：len(...) >= 0（长度恒非负）
RE_TRIVIAL_GE = re.compile(r"assert\s+len\([^()]*\)\s*>=\s*0\b")
# 3) 成败都算通过：returncode in [...]
RE_RETURNCODE_IN = re.compile(r"assert\s+returncode\s+in\s*\[")

# 4) unittest 写法的字符串断言：assertIn('<x>', <产物变量>)。
#    不写死 `self.`：辅助函数里 `tc.assertIn(...)` / 直接 `assertIn(...)` 同样该拦。
#    `\b` 前缀防止把 `assertNotIn` 误当 `assertIn`（NotIn 断的是「不包含」，
#    那是有方向的断言，不属于本形态）。
RE_ASSERTIN_STR = re.compile(
    r"\bassertIn\(\s*['\"][^'\"]*['\"]\s*,\s*" + _STR_TARGETS + r"\b"
)
# 5) 下界断言式：len(...) >= N，N>0。N=0 归 trivial-ge0，不在这里重复计。
#    合并期回补（D4-1 漏形态）：必须同时收 `> N` 这种等价拼法。
#    `len(x) > 0` 与 `len(x) >= 1` 是同一个断言，只是写法不同；原正则只收 `>=`，
#    结果全仓 26 处 `>=` 被拦、67 处 `> ` 溜过去——放过的比拦住的多 2.6 倍，
#    等于给这一形态留了个「换个符号就绕过门禁」的门。
#    `>=` 分支放在前面：交替按序尝试，`>\s*\d+` 不会误吃 `>=`（`>` 后面是 `=` 不是数字）。
#    `> N` 里 N 允许为 0（`> 0` 就是 `>= 1`，是真正的下界，不属于恒真形态）。
RE_LOWER_BOUND = re.compile(
    r"assert\s+len\([^()]*\)\s*(?:>=\s*[1-9]\d*|>\s*\d+)"
)
# 6) 非空断言式：assert <裸名字或点属性> is not None。
#    目标只收标识符与点属性（含中文标识符），**不收下标 `d['k']` 与调用 `f()`**——
#    保守口径，理由见模块 docstring。尾部锚点收 `,`（带断言消息）、`#`（行尾注释）
#    与行尾三种，避免把 `assert x is not None and len(x) == 3` 这类复合断言算进来
#    （那种有真信号）。
RE_NOT_NONE = re.compile(
    r"assert\s+[A-Za-z_\u4e00-\u9fff][\w.\u4e00-\u9fff]*\s+is\s+not\s+None\s*(?:,|#|$)"
)

CATEGORIES = {
    "string-assert": ("字符串断言式", RE_STRING_ASSERT,
        "测的是编译器/产物输出的字面量，不是行为；产物变了才发现的洞永远发现不了。"),
    "assertin-string": ("unittest字符串断言", RE_ASSERTIN_STR,
        "assertIn('x', py_code) 与 assert 'x' in py_code 完全同源，"
        "换个 unittest API 就绕过门禁——这类实测比 assert 写法还多。"),
    "upper-bound": ("上界断言式", RE_UPPER_BOUND,
        "len(...) <= N：集合为空时恒真，是最隐蔽的假绿（事件总线案例即此形态）。"),
    "lower-bound": ("下界断言式", RE_LOWER_BOUND,
        "len(...) >= N / > N：只断「至少有几个」，多出来的/错位的/重复的一概不管，集合非空即恒真。"),
    "not-none": ("非空断言式", RE_NOT_NONE,
        "x is not None：只断「不是 None」，对值、类型、结构零约束，是零信号断言。"),
    "trivial-ge0": ("恒真断言式", RE_TRIVIAL_GE,
        "len(...) >= 0：长度恒非负，这条断言永远为真，零信号。"),
    "returncode-in": ("成败都算通过", RE_RETURNCODE_IN,
        "returncode in [0,1]：成功失败都算通过，等于没测。"),
}

# 预防性形态：当前全仓零命中，保留是为了防新增，不是正在拦什么。
# 报文里单列，不让人误以为它俩在生效（第四轮 D4-1 要求）。
PREVENTIVE = ("trivial-ge0", "returncode-in")

# 单条合并正则：每行只做一次 .search，命中后再细分到具体类别（匹配极少，代价可忽略）。
RE_MASTER = re.compile(
    r"assert\s+(?:"
    r"['\"][^'\"]*['\"]\s+in\s+" + _STR_TARGETS + r"\b"
    r"|len\([^()]*\)\s*<=\s*\d+"
    r"|len\([^()]*\)\s*>=\s*\d+"
    r"|len\([^()]*\)\s*>\s*\d+"
    r"|[A-Za-z_\u4e00-\u9fff][\w.\u4e00-\u9fff]*\s+is\s+not\s+None\s*(?:,|#|$)"
    r")"
    r"|assert\s+returncode\s+in\s*\["
    r"|\bassertIn\(\s*['\"][^'\"]*['\"]\s*,\s*" + _STR_TARGETS + r"\b"
)

_DEFAULT_BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "assert_quality_baseline.json")

# 编译器生成的 .py 首行标记，见 src/code_generator.py 的 `# 由光明编译器生成`。
GENERATED_MARK = "由光明编译器生成"



def _posix(path):
    """把路径分隔符归一成 `/`：基线要跨平台可比，键里不能带 `os.sep`。"""
    return path.replace("\\", "/")


def _当前提交():
    """基线是从哪个提交生成的——写进基线文件，便于判断它是否已过期。

    不起 git 子进程（本脚本承诺零子进程、< 5s），直接读 .git 里的 ref。
    读不到就返回 "unknown"，不影响门禁判定。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    gitpath = os.path.join(root, ".git")
    try:
        if os.path.isfile(gitpath):  # worktree：.git 是指向真实 gitdir 的文件
            with open(gitpath, encoding="utf-8") as fh:
                gitpath = fh.read().strip().split("gitdir:", 1)[1].strip()
        head = os.path.join(gitpath, "HEAD")
        with open(head, encoding="utf-8") as fh:
            ref = fh.read().strip()
        if ref.startswith("ref:"):
            name = ref.split(None, 1)[1]
            # worktree 的分支 ref 可能在 commondir 里，两处都试
            for base in (gitpath, os.path.join(gitpath, "..", "..")):
                p = os.path.join(base, name.replace("/", os.sep))
                if os.path.isfile(p):
                    with open(p, encoding="utf-8") as fh:
                        return fh.read().strip()[:12]
            return "unknown"
        return ref[:12]
    except (OSError, IndexError, UnicodeDecodeError):
        return "unknown"


def _prose_lines(full):
    """返回「不该被当代码看」的行号集合：注释行 + 多行字符串（含 docstring）内部的行。

    为什么需要：正文里引用一条假绿写法当反面教材是完全正当的——
    tests/test_generics_c3.py 的模块 docstring 里写着「不做 `assert 'T' in py_code`
    那种字符串断言式假测试」，纯正则会把这句**说明文字**当成违规命中，逼着人把一条
    并不存在的违规写进基线。用 tokenize 把注释与多行字符串的行捞出来跳过。
    单行字符串不跳（那种把假绿写法当数据放在一行里的情况极少，且真要出现也该看一眼）。
    """
    prose = set()
    try:
        with open(full, "rb") as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type == tokenize.COMMENT:
                    prose.add(tok.start[0])
                elif tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                    for ln in range(tok.start[0], tok.end[0] + 1):
                        prose.add(ln)
    except (OSError, tokenize.TokenError, SyntaxError, IndentationError,
            UnicodeDecodeError):
        # 词法都过不去的文件不做豁免：宁可多报一条，也不因为解析失败静默放过。
        return set()
    return prose


def scan_tree(root):
    """返回 {category: [ {file, line, text}, ... ]} 与总数。"""
    found = {cat: [] for cat in CATEGORIES}
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过的目录：缓存、虚拟环境、被排除的基线/文档
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", ".venv", "node_modules",
                                    ".light_cache", ".ml_cache", "docs-site")]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            if fn == "assert_quality.py":
                continue  # 不扫自己
            full = os.path.join(dirpath, fn)
            # 一律用 POSIX 分隔符做 key。基线在 Windows 上生成时 relpath 给的是
            # `unit\test_self_host.py`，同一条违规在 FreeBSD runner 上是
            # `unit/test_self_host.py`，键对不上就被判成「6 条新增 + 6 条减少」，
            # 门禁在 CI 上无条件长红。2026-08-23 gitea run 71 就是这么红的。
            rel = _posix(os.path.relpath(full, root))
            prose = None
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        # 编译器生成的 .py 一律豁免（第六轮口径裁决）。
                        # 这些文件的内容由 src/code_generator.py 决定，作者是编译器
                        # 而不是人；把它们当「人写的测试」来判假测试，只会让「测试
                        # 里编译一份真文件」这件事变成必须记得写临时目录的地雷
                        # （产物一旦落在树里，CI 的门禁步骤就无条件红）。
                        # 代价记在明处：这类文件里的真问题门禁看不见——要防的是
                        # 生成器本身生成弱断言，那是 code_generator 的测试该管的事。
                        if i == 1 and GENERATED_MARK in line:
                            break
                        # 廉价预筛：绝大多数行不含 'assert'/'returncode'，直接跳过正则。

                        if "assert" not in line and "returncode" not in line:
                            continue
                        stripped = line.rstrip("\n")
                        m = RE_MASTER.search(stripped)
                        if not m:
                            continue
                        # 命中了才付 tokenize 的代价，且每个文件只付一次
                        if prose is None:
                            prose = _prose_lines(full)
                        if i in prose:
                            continue
                        # 命中后细分到具体类别（在短字符串上做，代价极小）
                        for cat, (_, rx, _) in CATEGORIES.items():
                            if rx.search(stripped):
                                found[cat].append({"file": rel, "line": i, "text": stripped.strip()})
                                break
            except OSError:
                continue
    return found



def load_baseline(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, ValueError):
        return None
    return data


def violation_key(v):
    # 2026-09-01 改：去掉行号，按 (file, cat, 断言原文) 三重集比对，
    # 免疫插入/删除造成的行号漂移（详见模块 docstring「关于基线的 key」一节）。
    # file 仍做 POSIX 归一（存量基线可能带 Windows 分隔符）；line 退化为人看字段，不参与 key。
    return "%s:%s:%s" % (_posix(v["file"]), v["cat"] if "cat" in v else "",
                         v.get("text", ""))


def main():
    ap = argparse.ArgumentParser()
    # 默认值必须与 CI 传的一致。原默认是 `tests`，而两侧 CI 都显式传 `--root .`
    # （`.gitea/workflows/ci.yml` 断言质量门禁步、`.github/workflows/ci.yml` 同名步）。
    # 基线键是**相对扫描根**的，所以谁忘了传参，扫出来的键全对不上基线，
    # 424 条存量会被逐条报成「新增违规」并 rc=1——一次实测就是这个数
    # （第七轮 E7 §3.3 实地复现）。默认值与 CI 对齐后，无参调用与 `--root .` 等价。
    ap.add_argument("--root", default=".",
                    help="要扫描的根目录，默认 `.`（与 CI 一致；相对仓库根或绝对路径）")
    ap.add_argument("--baseline", default=_DEFAULT_BASELINE,
                    help="基线快照路径（对比模式）")
    ap.add_argument("--write-baseline", metavar="PATH",
                    help="把本次结果写成新基线并退出")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("[假测试门禁] 扫描根不存在：%s" % args.root)
        return 2

    found = scan_tree(args.root)
    # 给每条打上分类标签，便于聚合
    tagged = []
    for cat, items in found.items():
        for it in items:
            it = dict(it)
            it["cat"] = cat
            tagged.append(it)

    total = len(tagged)
    print("[假测试门禁] 扫描 %s：命中 %d 条违规" % (args.root, total))
    for cat, (label, _, _) in CATEGORIES.items():
        n = len(found[cat])
        if n:
            print("       %-18s %3d 条  (%s)" % (label, n, cat))
    # 零命中的预防性形态单列，别让人以为它在拦什么（第四轮 D4-1）。
    空跑 = [c for c in PREVENTIVE if not found[c]]
    if 空跑:
        print("       预防性形态（当前零命中，只防新增，未在拦任何存量）：%s"
              % "、".join("%s/%s" % (CATEGORIES[c][0], c) for c in 空跑))
    非空预防 = [c for c in PREVENTIVE if found[c]]
    if 非空预防:
        print("       注意：以下预防性形态**已不再是零命中**，请更新脚本注释：%s"
              % "、".join(非空预防))

    if args.write_baseline:
        data = {
            "version": 2,
            "note": ("假测试门禁基线快照：本仓库当前的既有违规。新增即红；修好一批后重新生成并提交本文件。"
                     "built_from_commit 是**生成基线时的 HEAD**，也就是携带本基线那个提交的父提交；"
                     "若它在当前分支上不可达，说明基线是从被改写/丢弃的提交上生成的，必须重新生成。"),
            "built_from_commit": _当前提交(),
            "scanned_root": args.root,
            "categories": {c: CATEGORIES[c][0] for c in CATEGORIES},
            "violations": [
                {"file": v["file"], "line": v["line"], "cat": v["cat"], "text": v["text"]}
                for v in sorted(tagged, key=lambda x: (x["file"], x["line"]))
            ],
        }
        with open(args.write_baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("[假测试门禁] 已写入基线 %s（%d 条）" % (args.write_baseline, total))
        return 0

    baseline = load_baseline(args.baseline)
    if baseline is None:
        print("[假测试门禁] 找不到基线 %s。首次接入请先 --write-baseline 生成并提交。" % args.baseline)
        return 2

    # 双重集比对（2026-09-01 改）：base_c / cur_c 是 key→出现次数的计数，
    # 不再用 set——否则同一文件里两条一模一样的坏断言会被第 1 条额度吃掉，
    # 给复制粘贴的假绿留后门（实测 468 条存量里有 48 个重复键）。
    base_c = Counter(violation_key(v) for v in baseline.get("violations", []))
    cur_c = Counter(violation_key(v) for v in tagged)
    # 当前条目逐条比对：基线里同 key 还有余额就「核销」，余额耗尽的部分算新增。
    base_seen = Counter()
    new_violations = []
    for v in tagged:
        k = violation_key(v)
        base_seen[k] += 1
        if base_seen[k] <= base_c.get(k, 0):
            continue
        new_violations.append(v)

    # 逐条打印存量（简略）与新违规（详细）
    if new_violations:
        print("[假测试门禁] 新增违规 %d 条（视为回归，闸门拦下）：" % len(new_violations))
        for v in sorted(new_violations, key=lambda x: (x["file"], x["line"])):
            label, _, why = CATEGORIES[v["cat"]]
            print("       ! %s:%d  [%s] %s" % (v["file"], v["line"], label, v["text"][:80]))
            print("           为什么是假绿：%s" % why)
    else:
        print("[假测试门禁] 无新增违规。")

    # 存量条目已消失 = 有人修好了，或有人把那批代码删/挪了。
    # 原实现只打了一个数字后跟冒号却什么都不列，等于让人自己去猜是哪几条——
    # 而这正是合并点最需要的信息：D4 的基线在前三路合入前生成，C4 改完
    # tests/test_async.py 之后会有一批条目失效，必须被点名提示重建，
    # 否则失效条目会给「同文件同行号的新违规」留一张永久赦免票。
    # 基线里某项 key 的计数超过当前计数，超出的部分即「已修复/已挪走」的存量。
    stale = []
    for k, bc in base_c.items():
        for _ in range(max(0, bc - cur_c.get(k, 0))):
            stale.append(k)
    stale.sort()
    if stale:
        print("[假测试门禁] 相比基线已减少 %d 条。这些基线条目在当前代码里已不存在，"
              "请用 --write-baseline 重建基线（失效条目会给同位置的新违规留赦免票）：" % len(stale))
        for k in stale[:40]:
            print("       - %s" % k)
        if len(stale) > 40:
            print("       …… 另有 %d 条，完整清单用 --write-baseline 重建后对比" % (len(stale) - 40))

    if new_violations:
        print("[假测试门禁] 红：出现了基线条目之外的新增假绿断言。")
        return 1
    base_total = sum(base_c.values())
    if total > base_total:
        print("[假测试门禁] 红：违规总数 %d 超过基线 %d（可能基线被改动绕过）。" % (total, base_total))
        return 1

    print("[假测试门禁] 通过：存量冻结、无新增。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
