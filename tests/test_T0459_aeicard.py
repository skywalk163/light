# -*- coding: utf-8 -*-
"""T-0459：语法卡三层重写（compact/standard/full）验收。

卡面判据：
  1. compact ≤300 字符、standard ≤3000 字符（按 len() 计）；
  2. 三个 level 都不含 v3.2；standard 含当前版本号（真源 src/version.py，
     断言相等而不是写死版本号）；
  3. standard 含 读取文件、段落、若、引 SQL；
  4. docs/ai/*.md 与生成函数输出逐字一致（防腐烂）。

派生健全性（防"复制第二份关键字表"）：
  5. stdlib 节函数名 ⊆ spec/light.spec.json 的 stdlib 导出全集；
  6. 暗坑条目与 spec diagnostics 逐条对得上（code + title）；
  7. L0 分组章节与 spec l0_core 一致；
  8. compact 顶部有 6 条硬规则，含两条实测坑（读取(x)→input(x)、print→打印）。

另覆盖：full 索引层、旧签名兼容（compact=True / compact=False / ranked 置顶）。
"""

import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from ai_copilot import syntax_card  # noqa: E402

_SPEC_PATH = os.path.join(_ROOT, "spec", "light.spec.json")
_VERSION_PATH = os.path.join(_ROOT, "src", "version.py")
_AI_DOCS = {
    "compact.md": syntax_card.generate_compact_card,
    "standard.md": syntax_card.generate_standard_card,
    "README.md": syntax_card.generate_full_card,
}


def _load_spec():
    with open(_SPEC_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def _version_from_source() -> str:
    """独立从 src/version.py 解析版本号，不经过被测模块。"""
    with open(_VERSION_PATH, encoding="utf-8") as handle:
        text = handle.read()
    match = re.search(r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']', text)
    assert match, "src/version.py 应包含 __version__ 字面量"
    return match.group(1)


# ── 长度判据（卡面硬指标，按 len() 计）──────────────────────────────────

def test_compact_within_300_chars():
    card = syntax_card.generate_syntax_card("compact")
    assert len(card) <= 300, f"compact 卡 {len(card)} 字符，超出 300 上限"


def test_standard_within_3000_chars():
    card = syntax_card.generate_syntax_card("standard")
    assert len(card) <= 3000, f"standard 卡 {len(card)} 字符，超出 3000 上限"


# ── 版本：真源 src/version.py，三个 level 都不许再出现 v3.2 ──────────────

def test_no_v32_in_any_level():
    for level in ("compact", "standard", "full"):
        card = syntax_card.generate_syntax_card(level)
        assert "v3.2" not in card, f"{level} 层不得再出现 v3.2"


def test_standard_contains_current_version():
    version = _version_from_source()
    card = syntax_card.generate_syntax_card("standard")
    assert version and version in card
    assert f"光明v{version}语法卡" in card


def test_compact_and_full_also_carry_version():
    version = _version_from_source()
    assert version in syntax_card.generate_syntax_card("compact")
    assert version in syntax_card.generate_syntax_card("full")


# ── standard 必含词（卡面完成标准）─────────────────────────────────────

def test_standard_contains_required_terms():
    card = syntax_card.generate_syntax_card("standard")
    for term in ("读取文件", "段落", "若", "引 SQL"):
        assert term in card, f"standard 卡缺少必含词：{term}"


def test_compact_has_six_rules_with_real_pitfalls():
    card = syntax_card.generate_syntax_card("compact")
    assert "6条硬规则" in card
    # 实测坑 1：读取(x) 编译成 input(x)（等 stdin），读文件要用 读取文件
    assert "读取(x)" in card and "input(x)" in card and "读取文件" in card
    # 实测坑 2：print → 打印；冒号必选、块靠缩进
    assert "print" in card and "打印" in card
    assert "冒号必选" in card and "缩进" in card
    # 最小可跑例子
    assert "设甲为1" in card and "如果甲大于0" in card and "打印" in card


# ── 派生健全性：不复制第二份关键字表，事实必须来自 spec ──────────────────

def test_stdlib_names_all_from_spec():
    spec = _load_spec()
    exports = set()
    for module in spec.get("stdlib", {}).get("模块", []):
        for entry in module.get("导出", []):
            exports.add(entry.get("名字"))
    card = syntax_card.generate_syntax_card("standard")
    # 正向断言：卡里列出的每个 stdlib 函数名都在 spec 导出全集里
    for name in sorted(syntax_card._stdlib_top_names()):
        assert name in exports, f"stdlib 节出现 spec 之外的函数名：{name}"
        assert name in card, f"stdlib 节漏列 spec 导出：{name}"


def test_pitfalls_match_spec_diagnostics():
    spec = _load_spec()
    diagnostics = spec.get("diagnostics", [])
    card = syntax_card.generate_syntax_card("standard")
    section = card.split("暗坑", 1)[1]
    assert f"共{len(diagnostics)}条" in card
    for item in diagnostics:
        line = f"{item['code']} {item['title']}"
        assert line in section, f"暗坑节缺少 spec diagnostics 条目：{line}"


def test_l0_groups_match_spec():
    spec = _load_spec()
    chapters = spec.get("l0_core", {}).get("章节", [])
    compact = syntax_card.generate_syntax_card("compact")
    for chapter in chapters:
        piece = f"{chapter['章节']}{chapter['字数']}"
        assert piece in compact, f"L0 分组缺少 spec 章节：{piece}"


def test_skeleton_covers_spec_categories():
    spec = _load_spec()
    sections = {"条件判断", "循环控制", "函数定义", "类与对象", "异常处理",
                "嵌入块", "模块系统", "逻辑运算", "特殊值"}
    standard = syntax_card.generate_syntax_card("standard")
    for item in spec.get("keywords", []):
        categories = {part.strip() for part in str(item.get("类别") or "").split("、")}
        if categories & sections:
            assert item["字"] in standard, \
                f"骨架缺 spec 关键字：{item['字']}（{item['类别']}）"


def test_stdlib_top_is_exactly_50_names():
    names = syntax_card._stdlib_top_names()
    assert len(names) == 50
    plan_modules = {module for module, _ in syntax_card._STDLIB_TOP_PLAN}
    exports = syntax_card._stdlib_exports()
    assert plan_modules <= set(exports), "白名单模块必须存在于 spec stdlib"


# ── docs/ai/ 三份文档与生成输出逐字一致（防腐烂）────────────────────────

def test_docs_ai_files_match_generated_output():
    # 换行归一化对比：入库内容恒为 LF，但 Windows checkout（core.autocrlf=true）
    # 会把工作区转成 CRLF；逐字一致按归一化后断言，防内容腐烂跨平台误报。
    for name, generate in _AI_DOCS.items():
        path = os.path.join(_ROOT, "docs", "ai", name)
        with open(path, encoding="utf-8", newline="") as handle:
            on_disk = handle.read()
        assert on_disk.replace("\r\n", "\n") == generate(), \
            f"docs/ai/{name} 与生成函数输出不一致，请重跑 write_ai_docs()"


def test_write_ai_docs_roundtrip(tmp_path):
    written = syntax_card.write_ai_docs(str(tmp_path))
    assert sorted(written) == ["README.md", "compact.md", "standard.md"]
    for name, generate in _AI_DOCS.items():
        path = tmp_path / name
        with open(path, encoding="utf-8", newline="") as handle:
            assert handle.read() == generate()


# ── full 层：索引页，不给正文 ──────────────────────────────────────────

def test_full_card_is_index():
    card = syntax_card.generate_syntax_card("full")
    for link in ("docs/ai/compact.md", "docs/ai/standard.md", "docs/ai/README.md"):
        assert link in card, f"full 索引缺少文档链接：{link}"
    assert "ai snippets" in card
    assert len(card) < 600, "full 是索引页，不应塞正文"


# ── 统一入口与旧签名兼容（T-0464 接 --level 之前 cli 仍走旧参数）─────────

def test_default_level_is_compact():
    assert syntax_card.generate_syntax_card() == syntax_card.generate_syntax_card("compact")


def test_legacy_compact_flag_maps_to_levels():
    assert syntax_card.generate_syntax_card(compact=True) == syntax_card.generate_syntax_card("compact")
    assert syntax_card.generate_syntax_card(compact=False) == syntax_card.generate_syntax_card("standard")


def test_unknown_level_raises():
    try:
        syntax_card.generate_syntax_card("巨大")
    except ValueError as error:
        assert "compact/standard/full" in str(error)
    else:
        raise AssertionError("未知 level 应抛 ValueError")


def test_ranked_block_composes_with_compact():
    ranked = [{"code": "L4001", "title": "缺导入", "hits": 5, "last_seen": "",
               "example": "导入 标准库"}]
    card = syntax_card.generate_syntax_card(ranked=ranked)
    assert card.startswith("## 最近 30 天最常踩的坑（TOP 1）\n")
    assert "1. [L4001] 缺导入 —— 导入 标准库" in card
    assert card.endswith(syntax_card.generate_syntax_card("compact"))


def test_ranked_block_is_ignored_on_full_level():
    ranked = [{"code": "L4001", "title": "缺导入", "hits": 5, "last_seen": "", "example": ""}]
    card = syntax_card.generate_syntax_card("full", ranked=ranked)
    assert card == syntax_card.generate_syntax_card("full")


def test_cli_compat_include_verbs_and_pitfalls():
    card = syntax_card.generate_syntax_card(compact=True, include_verbs=True, include_pitfalls=True)
    assert "【动词参数参照】" in card
    assert "【光明暗坑 — AI 生成时必须注意】" in card
    assert card.startswith(syntax_card.generate_syntax_card("compact"))


def test_status_banner_reads_version_source():
    banner = syntax_card.status_banner()
    version = _version_from_source()
    assert f"v{version}" in banner
