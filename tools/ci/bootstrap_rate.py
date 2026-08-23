# -*- coding: utf-8 -*-
r"""语言自举率 + 引 Python 逃逸计数门禁（第三轮 D3-4 建，第四轮 D4-2 加防造假）。

把「自举率」「引 Python 逃逸」两个核心度量从人工统计变成可复现脚本，
统一到 `第三轮总纲.md` §2.3 的**唯一口径**，杜绝第二轮文档里
0/134、8/63、16/68 三个口径互相打架的问题。

唯一口径（§2.3）：
  - code    = 非空且不以 `#` 开头的行
  - decl    = 含 `段落` / `类` / `函数` 定义的行
  - 有真实现 ⇔ decl ≥ 1 **且**没有转手调用同名 `.py`（见下「防造假」）
  - **主报文件维度**（本次实测 17/69 = 24.64%）；行维度虚高，脚本里明确标注不许引用
    ——按本脚本自己的口径实算是 decl 364 / code 4034 = 9.02%（第三轮文档串里
    写的「16/68 ≈ 23.5%」与「行维度 85.8%」两个数都与真值不符，第四轮 D4-2 已订正）。
  - 引 Python 计数：`引\s*Python[：:]`（覆盖全角/半角冒号），排除
    `.git` / `__pycache__` / `.light_cache` / `docs-site` / `.ml_cache`。
    当前真值：stdlib/ 下 0 处；全仓 .light 源码 19 处（15 个文件，全在
    examples/ 的 L3/L4 分层教学示例，属教学用途，不算违规）。

第四轮 D4-2 追加两个维度（总纲 §2.3「把同名 .py 原样包一层不算自举」）：

  1. **影子数**：`stdlib/` 下有同名 `.py` 的 `.light` 个数。本次实测 53。
     结构性事实：52 个未算实现的文件 100% 是「纯 `导出` 声明 + 同名 `.py` 影子」，
     一个例外都没有；17 个有实现的里只有 `列表工具` 有 `.py` 影子。也就是说
     「有影子」与「无实现」几乎是同一件事，而老门禁完全没度量这个维度。
     判据：影子数**只许降不许升**——新写的模块不该再造影子。

  2. **防造假（自导入）**：某个 `.light` 若转手调用同名 `.py`，不许记为「有实现」。
     判据见 `取模块名位置()`：先认出导入行，再只取**模块名位置**的名字与自身模块名比。
     覆盖 parser 的全部形态（`src/parser_stmt.py:1494-1507`）——裸写 / `《》` 包裹 /
     `为 别名` / 逗号多模块 / 倒装 `导入 <符号> 从 <模块名>` / `导` 简写，并排除
     `导入 Python:`、`导入 C:` 两种引外语库前缀。缩进行（段落体内的延迟自导入）也算。
     命中即：① 该文件不计入 has_impl；② 门禁直接红并点名行号。
     本次实测全 `stdlib/` **零命中**，故 17/69 这个数字不因口径变更而变动
     （`列表工具.light` 有 `.py` 影子但实现体是可见算法，不是转手调用，保留在分子里，
     不做虚降；它只会进「有实现且有影子」的人工核验警告清单）。

     **为什么只看模块名位置**：`从 tokenizer 导入《分词器》` 这种「从别的模块导入一个
     恰与自己同名的符号」是合法且真实存在的写法（`antlrparser/self_hosted/` 下就有），
     若连符号名位置一起比就会误判。

     **误判/漏判边界**（粗判据的已知盲区，写清楚免得当成万能）：
       - 漏判 1：改名转手。`导入 列表工具实现` 再原样再导出，模块名不同名，抓不到。
       - 漏判 2：`引 Python:` 内联调用同名 `.py`。这条由本脚本另一道
         「stdlib 引 Python 计数 > 0 即红」的门禁兜住，不重复判。
       - 漏判 3：`段落` 体只有一行 `返回 某影子函数(...)`，没有 `导入` 关键字
         （靠运行期解析器隐式找同名 `.py`）。粗判据抓不到，靠「有实现且有影子」
         警告清单人工核验——本轮该清单只有 1 条（`列表工具`），已核为真实现。
       - 漏判 4：点号路径。`导入 列表工具.内部` 抽出的是整串 `列表工具.内部`，
         与模块名 `列表工具` 不等，抓不到；stdlib 现状无此写法。
       - 误判：整行注释与行内注释都已切掉，但**字符串字面量**里的
         `导入 <自身模块名>` 仍会误判（本脚本不做词法分析）。stdlib 现状零命中，
         未出现该误判；真出现时把那行改写即可。

门禁判据：
  - stdlib/ 下「引 Python」计数 > 0 即红（守住破零成果）。
  - 自举率只许升不许降（基线写进 bootstrap_rate_baseline.json）。
  - **影子数只许降不许升**（D4-2 新增，基线同文件 `shadow_count` 字段）。
  - **自导入命中 > 0 即红**（D4-2 新增，防造假）。
  - stdlib/lightpub/ 下 .light 数量当前 0、.py 56 —— 记入报告，不设门禁。

用法：
  # 对比模式（CI 用）
  python3 tools/ci/bootstrap_rate.py --root .
  # 刷新基线（自举率提升后手工执行并提交）
  python3 tools/ci/bootstrap_rate.py --root . --write-baseline tools/ci/bootstrap_rate_baseline.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# 引 Python 逃逸：覆盖全角/半角冒号
RE_PYTHON_ESCAPE = re.compile(r"引\s*Python[：:]")
# 定义行判定（§2.3：decl = 含「段落/类/函数 定义」的行）。
# 必须是定义行（关键字在行首缩进之后），不能只是「调用 函数甲()」里出现关键字，
# 否则会把纯调用行误算成实现。严格口径得到的文件维度自举率 = 17/69 = 24.64%，
# 与第四轮总纲 §2.3 给出的当前真值一致。
RE_DECL = re.compile(r"^\s*(段落|类|函数)\b")

# —— D4-2 防造假：转手调用同名 .py 的「自导入」判据 ——
#
# parser 支持 10 种导入形态（`src/parser_stmt.py:1494-1507` 的 docstring + `:1541-1554`
# 的实现）：模块名可裸写、可 `《》` 包裹、可带 `为 别名`、可逗号多模块、可 `导入 Python:`
# / `导入 C:` 语言前缀、可倒装 `导入 <符号> 从 <模块名>`，`导入` 还有 `导` 简写。
# stdlib 现状 53 行导入全是裸写形态，但书名号形态是合法语法——而且语言自己的文本兜底
# `src/module_resolver.py:504` 反过来**只认**书名号形态。两条口径互不相认，所以这里
# 两种都收，免得留下绕过通道。
#
# 关键取舍：**只看「模块名位置」的名字，不看「符号名位置」的名字**。否则
# `从 tokenizer 导入《分词器》`（导入别的模块里恰与自己同名的符号）会被误判成自导入，
# 而该模式在 `antlrparser/self_hosted/` 下真实存在。
#
# 中文标识符不能用 `\b`（`\w` 已含中文，`\b` 在中英边界上乱跳），一律显式 lookaround。
_IDENT_CH = r"\w\u4e00-\u9fff"
_名字 = r"[^\s《》，,。：:（()]+"
_RE_行内注释 = re.compile(r"#.*$")
_RE_导入 = re.compile(r"(?<![%s])导入(?![%s])" % (_IDENT_CH, _IDENT_CH))
_RE_从 = re.compile(r"(?<![%s])从(?![%s])" % (_IDENT_CH, _IDENT_CH))
_RE_语言前缀 = re.compile(r"^(Python|C)\s*[：:]")


def 取模块名位置(s):
    """从一行导入语句里抽出**模块名位置**上的名字；不是导入行则返回 []。

    覆盖形态（与 parser 对齐）：
      从属  `从 X 导入 ...`      `从《X》导入《符号》`
      直接  `导入 X。`           `导入《X》`   `导入 X 为 别名`   `导入 X一，X二`
      倒装  `导入 <符号> 从 X`
      简写  行首 `导 X`
    排除：`导入 Python: sys` / `导入 C: m` 是引外语库，不是段言模块自导入。
    """
    s = _RE_行内注释.sub("", s).strip()
    if not s:
        return []

    # 形态：从属 / 书名号从属——模块名夹在 `从` 与 `导入` 之间，取第一个名字
    if s.startswith("从"):
        m = re.match(r"从\s*《?\s*(%s)" % _名字, s)
        return [m.group(1)] if m else []

    m = _RE_导入.search(s)
    if m:
        tail = s[m.end():]
    elif re.match(r"^导(?![%s])" % _IDENT_CH, s):   # `导` 简写
        tail = s[1:]
    else:
        return []
    tail = tail.strip()

    if _RE_语言前缀.match(tail):
        return []

    # 形态：倒装 `导入 <符号> 从 <模块名>`——模块名在 `从` 之后
    m2 = _RE_从.search(tail)
    if m2:
        m3 = re.match(r"\s*《?\s*(%s)" % _名字, tail[m2.end():])
        return [m3.group(1)] if m3 else []

    # 形态：直接导入，逗号分隔多模块，每条取第一个名字（丢掉 `为 别名`）
    出 = []
    for 条目 in re.split(r"[，,]", tail):
        条目 = 条目.strip().rstrip("。")
        m4 = re.match(r"《?\s*(%s)" % _名字, 条目)
        if m4:
            出.append(m4.group(1))
    return 出


def 查自导入(full, 模块名):
    """返回该 .light 里「转手调用同名 .py」的命中清单 [(行号, 行文本), ...]。

    整行注释（`#` 开头）与行内注释已排除；字符串字面量里的同形文本会误判，
    见模块 docstring 的「误判/漏判边界」。
    """
    命中 = []
    try:
        with open(full, encoding="utf-8", errors="replace") as fh:
            for i, raw in enumerate(fh, 1):
                s = raw.strip()
                if not s or s.startswith("#") or 模块名 not in s:
                    continue
                if 模块名 in 取模块名位置(s):
                    命中.append((i, s))
    except OSError:
        pass
    return 命中

# 扫描时跳过的目录
_SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules",
              ".light_cache", ".ml_cache", "docs-site"}

_DEFAULT_BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "bootstrap_rate_baseline.json")


def _当前提交(root):
    """基线是从哪个提交生成的——写进基线文件，便于判断它是否已过期。

    不起 git 子进程，直接读 `.git` 里的 ref；读不到返回 "unknown"，不影响门禁判定。
    与 `assert_quality.py:_当前提交` 同实现，区别是这里按 `--root` 定位而非 `__file__`
    （本脚本允许扫任意仓库根）。
    """
    gitpath = os.path.join(os.path.abspath(root), ".git")
    try:
        if os.path.isfile(gitpath):  # worktree：.git 是指向真实 gitdir 的文件
            with open(gitpath, encoding="utf-8") as fh:
                gitpath = fh.read().strip().split("gitdir:", 1)[1].strip()
        with open(os.path.join(gitpath, "HEAD"), encoding="utf-8") as fh:
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


def iter_light_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".light"):
                yield os.path.join(dirpath, fn)


def count_code_decl(lines):
    """返回 (code 行数, decl 行数)。code=非空且非 `#` 开头；decl=行首定义行。"""
    code = 0
    decl = 0
    for raw in lines:
        s = raw.rstrip("\n")
        if not s.strip():
            continue
        if s.lstrip().startswith("#"):
            continue
        code += 1
        if RE_DECL.search(s):
            decl += 1
    return code, decl


def scan_stdlib(root):
    """扫描 stdlib/ 下所有 .light，按 §2.3 口径算文件维度自举率 + D4-2 两个新维度。

    返回字典额外含：
      - shadow_count      有同名 .py 影子的 .light 个数（只许降不许升）
      - fake_hits         自导入命中清单（转手调用同名 .py，即红）
      - impl_with_shadow  「有实现且有影子」的文件（人工核验警告，不设门禁）
    """
    stdlib_dir = os.path.join(root, "stdlib")
    files = []
    if os.path.isdir(stdlib_dir):
        files = sorted(iter_light_files(stdlib_dir))
    total = 0
    has_impl = 0
    shadow_count = 0
    fake_hits = []
    impl_with_shadow = []
    for full in files:
        total += 1
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                _, decl = count_code_decl(fh)
        except OSError:
            continue

        模块名 = os.path.basename(full)[:-len(".light")]
        有影子 = os.path.isfile(full[:-len(".light")] + ".py")
        if 有影子:
            shadow_count += 1

        # 键一律走 POSIX `/`，不许带 os.sep（跨平台一致，第三轮 run 71 教训）
        rel = os.path.relpath(full, root).replace(os.sep, "/")

        命中 = 查自导入(full, 模块名)
        if 命中:
            # 防造假：转手调用同名 .py，不计入 has_impl，且门禁点名
            for 行号, 行文本 in 命中:
                fake_hits.append({"file": rel, "line": 行号, "text": 行文本})
            continue

        if decl >= 1:
            has_impl += 1
            if 有影子:
                impl_with_shadow.append(rel)
    rate = (has_impl / total) if total else 0.0
    return {
        "stdlib_light_total": total,
        "stdlib_light_has_impl": has_impl,
        "file_dim_rate": rate,
        "shadow_count": shadow_count,
        "fake_hits": fake_hits,
        "impl_with_shadow": impl_with_shadow,
    }


def count_python_escape(root):
    """全仓扫 .light 里的「引 Python」：返回 (stdlib 计数, 全仓计数, 全仓文件数, 命中清单)。"""
    stdlib_hits = 0
    repo_hits = 0
    repo_files = 0
    repo_detail = []
    stdlib_prefix = os.path.join(root, "stdlib")
    for full in iter_light_files(root):
        # 文件级命中（去重到文件，便于数「文件数」）
        file_has = False
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    if RE_PYTHON_ESCAPE.search(line):
                        repo_hits += 1
                        if not file_has:
                            file_has = True
                            repo_files += 1
                            # 打印路径一律 POSIX `/`，本机与 CI（Linux）输出可逐字对比
                            rel = os.path.relpath(full, root).replace(os.sep, "/")
                            repo_detail.append("%s:%d" % (rel, i))
                        if full.startswith(stdlib_prefix + os.sep) or full == stdlib_prefix:
                            stdlib_hits += 1
        except OSError:
            continue
    return stdlib_hits, repo_hits, repo_files, repo_detail


def count_lightpub(root):
    lightpub = os.path.join(root, "stdlib", "lightpub")
    n_light = 0
    n_py = 0
    if os.path.isdir(lightpub):
        for fn in os.listdir(lightpub):
            if fn.endswith(".light"):
                n_light += 1
            elif fn.endswith(".py"):
                n_py += 1
    return {"lightpub_light": n_light, "lightpub_py": n_py}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".",
                    help="仓库根目录，默认当前目录（相对或绝对路径）")
    ap.add_argument("--baseline", default=_DEFAULT_BASELINE,
                    help="自举率基线快照路径（对比模式）")
    ap.add_argument("--write-baseline", metavar="PATH",
                    help="把本次自重举率写成新基线并退出")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("[自举率门禁] 仓库根不存在：%s" % args.root)
        return 2

    stdlib = scan_stdlib(args.root)
    stdlib_esc, repo_esc, repo_files, repo_detail = count_python_escape(args.root)
    lightpub = count_lightpub(args.root)

    # —— 行维度口径（明确标注：虚高、不许引用）——
    # 这里只做统计展示，不在门禁里使用。
    line_code = line_decl = line_has_impl_files = 0
    sd = os.path.join(args.root, "stdlib")
    if os.path.isdir(sd):
        for full in iter_light_files(sd):
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    c, d = count_code_decl(fh)
                line_code += c
                line_decl += d
            except OSError:
                continue
    line_dim_rate = (line_decl / line_code) if line_code else 0.0

    print("[自举率门禁] stdlib 文件维度自举率：%d/%d = %.2f%%"
          % (stdlib["stdlib_light_has_impl"], stdlib["stdlib_light_total"],
             stdlib["file_dim_rate"] * 100))
    print("[自举率门禁] （仅供参考、不许引用）行维度 decl/code = %d/%d = %.2f%%"
          % (line_decl, line_code, line_dim_rate * 100))
    print("[自举率门禁] stdlib 同名 .py 影子数：%d/%d（只许降不许升，新模块不该再造影子）"
          % (stdlib["shadow_count"], stdlib["stdlib_light_total"]))
    print("[自举率门禁] 防造假（转手调用同名 .py / 自导入）：命中 %d 处"
          % len(stdlib["fake_hits"]))
    for h in stdlib["fake_hits"][:30]:
        print("       - %s:%d: %s" % (h["file"], h["line"], h["text"]))
    if stdlib["impl_with_shadow"]:
        print("[自举率门禁] 提示：%d 个文件「有实现且有影子」，"
              "算法可见性需人工核验（不设门禁，粗判据的已知盲区）："
              % len(stdlib["impl_with_shadow"]))
        for f in stdlib["impl_with_shadow"][:30]:
            print("       - %s" % f)
    print("[自举率门禁] stdlib 「引 Python」逃逸：%d 处" % stdlib_esc)
    print("[自举率门禁] 全仓 .light 「引 Python」：%d 处 / %d 文件（教学示例不算违规）"
          % (repo_esc, repo_files))
    if repo_detail:
        for d in repo_detail[:30]:
            print("       - %s" % d)
    print("[自举率门禁] stdlib/lightpub：.light=%d  .py=%d（仅记录，不设门禁）"
          % (lightpub["lightpub_light"], lightpub["lightpub_py"]))

    if args.write_baseline:
        if stdlib["fake_hits"]:
            print("[自举率门禁] 拒绝写基线：存在 %d 处自导入（转手调用同名 .py），"
                  "先把造假清掉再刷基线。" % len(stdlib["fake_hits"]))
            return 1
        data = {
            "version": 2,
            "note": ("自举率基线快照：文件维度自举率只许升不许降；影子数只许降不许升。"
                     "行维度虚高，不许引用。口径见 tools/ci/bootstrap_rate.py docstring。"),
            "file_dim_rate": stdlib["file_dim_rate"],
            "stdlib_light_total": stdlib["stdlib_light_total"],
            "stdlib_light_has_impl": stdlib["stdlib_light_has_impl"],
            "shadow_count": stdlib["shadow_count"],
            "built_from_commit": _当前提交(args.root),
        }
        with open(args.write_baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("[自举率门禁] 已写入基线 %s（文件维度 %.2f%%，影子数 %d）"
              % (args.write_baseline, stdlib["file_dim_rate"] * 100,
                 stdlib["shadow_count"]))
        return 0

    baseline = None
    try:
        with open(args.baseline, encoding="utf-8") as fh:
            baseline = json.load(fh)
    except (FileNotFoundError, ValueError):
        baseline = None

    if baseline is None:
        print("[自举率门禁] 找不到基线 %s。首次接入请先 --write-baseline 生成并提交。" % args.baseline)
        return 2

    base_rate = baseline.get("file_dim_rate", 0.0)
    red = False

    # —— D4-2 新增判据 1：防造假（自导入）命中即红 ——
    if stdlib["fake_hits"]:
        print("[自举率门禁] 红：%d 处「转手调用同名 .py」（自导入），"
              "按总纲 §2.3 不算自举，已从分子剔除并判红。"
              % len(stdlib["fake_hits"]))
        red = True

    # —— D4-2 新增判据 2：影子数只许降不许升 ——
    base_shadow = baseline.get("shadow_count")
    影子已判定 = base_shadow is not None
    if base_shadow is None:
        print("[自举率门禁] 警告：基线 %s 缺 shadow_count 字段（version < 2），"
              "本次**未判定**影子数维度。请用 --write-baseline 刷新基线。"
              % args.baseline)
    elif stdlib["shadow_count"] > base_shadow:
        print("[自举率门禁] 红：影子数 %d 高于基线 %d（新增了同名 .py 影子，"
              "新模块不该再造影子）。"
              % (stdlib["shadow_count"], base_shadow))
        red = True
    elif stdlib["shadow_count"] < base_shadow:
        print("[自举率门禁] 影子数下降 %d → %d（清掉影子后请用 --write-baseline 更新基线）。"
              % (base_shadow, stdlib["shadow_count"]))
    else:
        print("[自举率门禁] 影子数持平基线 %d。" % base_shadow)

    if stdlib_esc > 0:
        print("[自举率门禁] 红：stdlib/ 下出现「引 Python」逃逸 %d 处（破零成果被破坏）。" % stdlib_esc)
        red = True
    else:
        print("[自举率门禁] stdlib/ 引 Python 逃逸 = 0，破零成果守住。")

    if stdlib["file_dim_rate"] < base_rate - 1e-9:
        print("[自举率门禁] 红：文件维度自举率 %.2f%% 低于基线 %.2f%%（自举率只许升不许降）。"
              % (stdlib["file_dim_rate"] * 100, base_rate * 100))
        red = True
    elif stdlib["file_dim_rate"] > base_rate + 1e-9:
        print("[自举率门禁] 自举率提升 %.2f%% → %.2f%%（修好一批后请用 --write-baseline 更新基线）。"
              % (base_rate * 100, stdlib["file_dim_rate"] * 100))
    else:
        print("[自举率门禁] 自举率持平基线 %.2f%%。" % (base_rate * 100))

    if red:
        return 1
    if 影子已判定:
        print("[自举率门禁] 通过：破零守住、自举率未降、影子数未升、无转手造假。")
    else:
        print("[自举率门禁] 通过：破零守住、自举率未降、无转手造假"
              "（影子数维度**未判定**，基线待刷新）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
