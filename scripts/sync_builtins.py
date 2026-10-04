#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_builtins.py — R114 S1：stdlib/builtins.py 三副本收敛同步脚本。

唯一真源：light-merge/stdlib/builtins.py（158 函数）。
目标副本：
  1. light-merge/bootstrap/release/stdlib/builtins.py（自举编译器打包用）
  2. lightharness/stdlib/builtins.py（LH 运行时用）

设计要点（合并算法写死，禁止"公共函数以真源为准"式模糊操作）：

* BOOT_JSON_EXEMPT：boot 侧三函数（解析JSON/序列化JSON/美化JSON）永远保留
  boot 直用 Python json 的实现——真源对应函数是惰性 `import JSON`，依赖
  JSON.light → JSON核心.light，而 release/stdlib 下没有 JSON核心.light；
  且 boot 顶层必须保留 `import json as _duan_json_module`（BOOT_KEEP_HEADER），
  否则留存的三个 boot JSON 函数体引用 _duan_json_module 会 NameError。

* BOOT_PORTED：boot 发布环境实测无光导入钩子（duan-compiler.py 只把 release/stdlib
  加进 sys.path 后 importlib 加载本文件），内置核心*.light 全部不存在（实测
  `import 内置核心判型` → ModuleNotFoundError）。真源里 ~66 个公共函数体是
  "地板转发"（惰性 import 内置核心*），盲同步进 boot 会运行期炸。因此下列
  11 个"真源有而 boot 缺"的转发式函数，以**自包含移植体**写入 boot，语义已逐条
  对齐 stdlib/内置核心判型.light / 内置核心字符串.light / 内置核心系统.light。
  boot 现有 109 个自包含公共函数体保持原样不动（additive 收敛，不重构已运行语义）。

* LH_ONLY：lightharness 副本独有 `整数`，原样保留；其余公共函数体以真源逐字同步
  （LH 运行时环境具备光导入钩子与全部 内置核心*.light，实测可托管转发体）。

幂等：重复跑不产生 diff（第二次跑从同一真源重生成同一产物）。
内置反例自检：任一不成立 →  exit 非 0。
"""

import os
import re
import sys
import hashlib

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))          # light-merge/scripts
LM = os.path.normpath(os.path.join(HERE, ".."))            # light-merge
LH_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "lightharness"))

MAIN_PATH = os.path.join(LM, "stdlib", "builtins.py")
BOOT_PATH = os.path.join(LM, "bootstrap", "release", "stdlib", "builtins.py")
LH_PATH = os.path.join(LH_ROOT, "stdlib", "builtins.py")

# ---------------------------------------------------------------------------
# 唯一豁免权威（tests/unit/test_builtins_drift.py import 同一份，防两处漂移）
# ---------------------------------------------------------------------------
BOOT_JSON_EXEMPT = {"解析JSON", "序列化JSON", "美化JSON"}   # boot 直用 json 的实现
LH_ONLY = {"整数"}                                         # LH 副本独有
BOOT_KEEP_HEADER = "import json as _duan_json_module"      # boot 顶层必须保留的行

# boot 自包含移植体（真源为转发式，release 环境无法托管；语义对齐 .light 真身）
#
# LH 侧 .light 依赖同步（R114 实测发现）：LH 的 builtins.py 公共函数体逐字取真源后，
# 是布尔/是函数/是数值/字符串全数字 转发到 LH stdlib 的 内置核心判型.light——但该
# .light 是旧拷贝（缺这 4 个段落，实测 AttributeError）。按同一真源原则逐字同步。
LH_LIGHT_SYNC = ("内置核心判型.light",)
BOOT_PORTED = {
    "最后索引": '''def 最后索引(text: str, substring: str) -> int:
    """查找子串最后出现位置，未找到返回 -1（R114-S1 boot 自包含移植：对齐 内置核心字符串.最后索引）"""
    return str.rfind(text, substring)''',

    "副本": '''def 副本(原):
    """浅拷贝：字典浅拷贝键值对、列表浅拷贝元素、其他类型原样返回（R114-S1 boot 自包含移植：对齐 内置核心列表.副本）"""
    import copy as _拷贝模块
    return _拷贝模块.copy(原)''',

    "浅拷贝": '''def 浅拷贝(原):
    """浅拷贝（R114-S1 boot 自包含移植：对齐 内置核心列表.浅拷贝）"""
    import copy as _拷贝模块
    return _拷贝模块.copy(原)''',

    "是字节": '''def 是字节(值) -> bool:
    """检查是否为字节串（bytes）。R114-S1 boot 自包含移植：对齐 内置核心判型.是字节。"""
    return isinstance(值, bytes)''',

    "是布尔": '''def 是布尔(值) -> bool:
    """检查是否为布尔值。R114-S1 boot 自包含移植：对齐 内置核心判型.是布尔。"""
    return isinstance(值, bool)''',

    "是函数": '''def 是函数(值) -> bool:
    """检查是否为可调用对象（函数/方法/lambda）。R114-S1 boot 自包含移植：对齐 内置核心判型.是函数。"""
    return callable(值)''',

    "是数值": '''def 是数值(值) -> bool:
    """检查是否为数值类型（int/float，排除 bool）。R114-S1 boot 自包含移植：对齐 内置核心判型.是数值。"""
    if isinstance(值, bool):
        return False
    return isinstance(值, (int, float))''',

    "字符串全数字": '''def 字符串全数字(串) -> bool:
    """检查整个字符串是否全由数字字符组成（空串/非 str 判假）。R114-S1 boot 自包含移植：对齐 内置核心判型.字符串全数字。"""
    if not isinstance(串, str):
        return False
    if len(串) == 0:
        return False
    return 串.isdigit()''',

    "是负零": '''def 是负零(值) -> bool:
    """检查 IEEE 754 负零（-0.0）；正零/整数 0/非零数均判假。R114-S1 boot 自包含移植：对齐 内置核心判型.是负零。"""
    if not isinstance(值, float):
        return False
    if 值 != 0.0:
        return False
    return str(值).startswith("-")''',

    "主目录": '''def 主目录() -> str:
    """获取当前用户主目录。R114-S1 boot 自包含移植：对齐 内置核心系统.主目录。"""
    return os.path.expanduser("~")''',

    "随机UUID": '''def 随机UUID() -> str:
    """生成随机 UUID v4 字符串。R114-S1 boot 自包含移植：对齐 内置核心系统.随机UUID。"""
    import uuid
    return str(uuid.uuid4())''',
}

# 自动生成段标记（boot 侧；幂等锚点）
MARK_BEGIN = "# ===== R114-S1 sync_builtins.py 自动生成段（勿手改；由 scripts/sync_builtins.py 重生成）====="
MARK_END = "# ===== R114-S1 sync_builtins.py 自动生成段结束 ====="

FUNC_RE = re.compile(r"^def ([^\(]+)\(")
# 顶层语句行（用于函数块结束判定：def 之间出现的模块级赋值等）
TOPLEVEL_RE = re.compile(r"^[A-Za-z_一-鿿][\w一-鿿]*\s*=")


# ---------------------------------------------------------------------------
# 解析工具
# ---------------------------------------------------------------------------
def parse_functions(text):
    """从 builtins 文本抽出 {函数名: 精确块文本}（块含尾部空行），保持源码顺序。"""
    lines = text.split("\n")
    funcs = {}
    order = []
    i, n = 0, len(lines)
    while i < n:
        m = FUNC_RE.match(lines[i])
        if m:
            name = m.group(1).strip()
            start = i
            i += 1
            while i < n:
                if FUNC_RE.match(lines[i]) or TOPLEVEL_RE.match(lines[i]):
                    break
                i += 1
            funcs[name] = "\n".join(lines[start:i])
            order.append(name)
        else:
            i += 1
    return funcs, order


def norm_block(block):
    """规范化函数体：去行尾空白、丢空行与列 0 注释行（drift 哈希用，不引第三方依赖）。

    列 0 注释行是分节横幅（不属于任何函数体），块解析时会被吸进相邻函数块尾部，
    不剔除会造成"注释位置不同"的假漂移。缩进的 docstring 行不受影响（非列 0）。
    """
    lines = []
    for l in block.split("\n"):
        t = l.strip()
        if not t or t.startswith("#"):
            continue
        lines.append(l.rstrip())
    return "\n".join(lines)


def block_hash(block):
    return hashlib.md5(norm_block(block).encode("utf-8")).hexdigest()


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# boot 同步
# ---------------------------------------------------------------------------
def sync_boot(main_text, main_funcs, main_order):
    boot_text = read(BOOT_PATH)

    # 1. 切出"原始前缀"（此前已运行过则从生成段标记切；首次运行从 __all__ 导出横幅切）
    idx = boot_text.find(MARK_BEGIN)
    if idx != -1:
        prefix = boot_text[:idx].rstrip() + "\n"
    else:
        banner = boot_text.find("# 导出所有函数")
        if banner == -1:
            raise SystemExit("boot 副本找不到 '导出所有函数' 横幅，无法定位同步锚点")
        start = boot_text.rfind("# ===", 0, banner)
        prefix = boot_text[:start].rstrip() + "\n"

    prefix_funcs, _ = parse_functions(prefix)
    already = set(prefix_funcs.keys())

    # 2. 真源有而 boot 缺的函数：38 个逐字取自真源 + 11 个走 BOOT_PORTED
    missing = [n for n in main_order if n not in already]
    verbatim = [n for n in missing if n not in BOOT_PORTED]
    ported = [n for n in missing if n in BOOT_PORTED]

    blocks = []
    blocks.append(MARK_BEGIN)
    blocks.append("")
    blocks.append("# --- 下列函数由 scripts/sync_builtins.py 从真源 stdlib/builtins.py 逐字补齐 ---")
    for n in verbatim:
        blocks.append(main_funcs[n].rstrip())
        blocks.append("")
    if ported:
        blocks.append("# --- 下列为 boot 自包含移植体（真源为地板转发式，release 环境无光导入钩子，语义对齐 内置核心*.light 真身）---")
        for n in ported:
            blocks.append(BOOT_PORTED[n])
            blocks.append("")
    blocks.append(MARK_END)
    blocks.append("")
    blocks.append(gen_all(main_order))

    new_text = prefix.rstrip() + "\n\n\n" + "\n".join(blocks) + "\n"
    write(BOOT_PATH, new_text)
    return set(verbatim), ported


def gen_all(names):
    lines = ["__all__ = ["]
    for n in names:
        lines.append(f"    '{n}',")
    lines.append("]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LH 同步
# ---------------------------------------------------------------------------
def sync_lh(main_text):
    lh_text = read(LH_PATH)

    # LH 头原样保留（含光导入钩子安装）：切到第一个 def 之前
    anchor = lh_text.find("def 读取文件")
    if anchor == -1:
        raise SystemExit("LH 副本找不到 'def 读取文件'，无法定位 LH 头边界")
    preamble = lh_text[:anchor].rstrip() + "\n"

    lh_funcs, _ = parse_functions(lh_text)
    if "整数" not in lh_funcs:
        raise SystemExit("LH 副本找不到 LH_ONLY 函数 '整数'，无法保留")
    zhengshu_block = lh_funcs["整数"].rstrip()

    # 真源主体（def 读取文件 到 EOF）逐字接管
    main_body = main_text[main_text.find("def 读取文件"):]

    # 在真源 转整数 块之后插入 LH 独有 整数
    m2 = re.search(r"^def 转整数\(", main_body, re.M)
    if not m2:
        raise SystemExit("真源主体找不到 'def 转整数'")
    pos = m2.start()
    # 找 转整数 块结束（下一个顶层 def / 赋值）
    rest = main_body[pos:]
    lines = rest.split("\n")
    end = 1
    while end < len(lines):
        if FUNC_RE.match(lines[end]) or TOPLEVEL_RE.match(lines[end]):
            break
        end += 1
    insert_at = pos + sum(len(l) + 1 for l in lines[:end])
    new_body = (main_body[:insert_at].rstrip() + "\n\n\n"
                + zhengshu_block + "\n\n\n"
                + main_body[insert_at:].lstrip("\n"))

    new_text = preamble.rstrip() + "\n\n\n" + new_body.lstrip("\n")
    write(LH_PATH, new_text)

    # LH .light 依赖逐字同步（见 LH_LIGHT_SYNC；idempotent：内容一致时无 diff）
    main_stdlib = os.path.dirname(MAIN_PATH)
    lh_stdlib = os.path.dirname(LH_PATH)
    for name in LH_LIGHT_SYNC:
        src = os.path.join(main_stdlib, name)
        dst = os.path.join(lh_stdlib, name)
        with open(src, encoding="utf-8") as f:
            src_text = f.read()
        old_text = None
        if os.path.exists(dst):
            with open(dst, encoding="utf-8") as f:
                old_text = f.read()
        if old_text != src_text:
            write(dst, src_text)
            print(f"  LH .light 同步: {name}")


# ---------------------------------------------------------------------------
# 内置反例自检
# ---------------------------------------------------------------------------
def self_checks(main_funcs, main_order, boot_verbatim):
    errors = []

    boot_text = read(BOOT_PATH)
    lh_text = read(LH_PATH)
    boot_funcs, _ = parse_functions(boot_text)
    lh_funcs, _ = parse_functions(lh_text)

    # 语法可编译
    for label, path, text in (("boot", BOOT_PATH, boot_text), ("lh", LH_PATH, lh_text)):
        try:
            compile(text, path, "exec")
        except SyntaxError as e:
            errors.append(f"{label} 副本语法错误: {e}")

    # boot 名字集合 == 真源
    if set(boot_funcs.keys()) != set(main_funcs.keys()):
        miss = set(main_funcs) - set(boot_funcs)
        extra = set(boot_funcs) - set(main_funcs)
        errors.append(f"boot 函数集合与真源不一致: 缺 {sorted(miss)} 多出 {sorted(extra)}")

    # LH 名字集合 diff == LH_ONLY
    lh_diff_extra = set(lh_funcs) - set(main_funcs)
    lh_diff_miss = set(main_funcs) - set(lh_funcs)
    if lh_diff_extra != LH_ONLY:
        errors.append(f"LH 独有函数集合应为 {sorted(LH_ONLY)}，实为 {sorted(lh_diff_extra)}")
    if lh_diff_miss:
        errors.append(f"LH 缺真源函数: {sorted(lh_diff_miss)}")

    # BOOT_KEEP_HEADER 必须存在（模块级行）
    header_lines = [l.strip() for l in boot_text.split("\n") if l and not l.startswith("#")]
    if BOOT_KEEP_HEADER not in header_lines:
        errors.append(f"boot 缺少顶层保留行: {BOOT_KEEP_HEADER}")

    # JSON 三豁免：取 boot 版。解析JSON/序列化JSON 必须直用 _duan_json_module 且
    # 不得含真源的惰性 import JSON；美化JSON 委托 序列化JSON（本就不直引模块），
    # 只需断言它没误入惰性 import JSON 版。
    for n in sorted(BOOT_JSON_EXEMPT):
        b = boot_funcs.get(n, "")
        if re.search(r"^\s*import\s+JSON\s*$", b, re.M):
            errors.append(f"boot 豁免函数 {n} 误入了真源的惰性 import JSON 版")
        if n == "美化JSON":
            if "序列化JSON" not in b:
                errors.append(f"boot 豁免函数 {n} 未委托 序列化JSON")
        elif "_duan_json_module" not in b:
            errors.append(f"boot 豁免函数 {n} 丢失 _duan_json_module 引用")

    # boot 不得混入 LH_ONLY
    if LH_ONLY & set(boot_funcs):
        errors.append(f"boot 不应含 LH 独有函数: {sorted(LH_ONLY & set(boot_funcs))}")

    # LH 公共函数体哈希与真源一致（排除 LH_ONLY）
    for n in main_order:
        if n in LH_ONLY:
            continue
        if block_hash(lh_funcs[n]) != block_hash(main_funcs[n]):
            errors.append(f"LH 公共函数体与真源漂移: {n}")

    # boot 逐字补齐的公共函数体哈希与真源一致（只覆盖本次从真源逐字写入的集合；
    # boot 现有 109 个自包含公共函数为保留体，不在本断言范围——见模块 docstring）
    for n in sorted(boot_verbatim):
        if block_hash(boot_funcs[n]) != block_hash(main_funcs[n]):
            errors.append(f"boot 逐字同步函数与真源漂移: {n}")

    # LH .light 依赖已同步（内置核心判型.light 必须含 4 个新判型段落）
    for name in LH_LIGHT_SYNC:
        p = os.path.join(os.path.dirname(LH_PATH), name)
        t = read(p)
        for para in ("段落 是布尔", "段落 是函数", "段落 是数值", "段落 字符串全数字"):
            if para not in t:
                errors.append(f"LH .light {name} 缺段落: {para}")

    if errors:
        for e in errors:
            print("  [自检失败] " + e)
        return 1
    print("  [自检] 全部通过")
    return 0


# ---------------------------------------------------------------------------
def main():
    main_text = read(MAIN_PATH)
    main_funcs, main_order = parse_functions(main_text)
    print(f"真源 {MAIN_PATH}")
    print(f"  函数数: {len(main_funcs)}")

    print("\n[boot] 同步 bootstrap/release/stdlib/builtins.py ...")
    boot_verbatim, ported = sync_boot(main_text, main_funcs, main_order)
    print(f"  补齐 {len(boot_verbatim) + len(ported)} 个: 逐字取自真源 {len(boot_verbatim)} 个, 自包含移植 {len(ported)} 个")
    print(f"  豁免命中: BOOT_JSON_EXEMPT={sorted(BOOT_JSON_EXEMPT)} 保持 boot 实现")

    print("\n[LH] 同步 lightharness/stdlib/builtins.py ...")
    sync_lh(main_text)
    print(f"  公共函数体逐字取真源; LH_ONLY={sorted(LH_ONLY)} 原样保留")

    print("\n[自检] ...")
    rc = self_checks(main_funcs, main_order, boot_verbatim)
    if rc != 0:
        sys.exit(rc)
    print("\n同步完成，exit 0")


if __name__ == "__main__":
    main()
