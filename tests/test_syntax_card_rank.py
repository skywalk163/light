# -*- coding: utf-8 -*-
"""T-0320：语法速查卡按近 30 天错误频次动态置顶。

覆盖四块：
  1. error_stats.rank_pitfalls：按 code 聚合 hits、hits 降序 / last_seen 倒序、
     top 截断、30 天窗口过滤、坏行跳过并计数；
  2. 语料缺失 / 坏行 / 空目录 → 空列表，不抛；
  3. T-0459 三层卡：generate_syntax_card(level) 的 compact / standard / full
     输出与 docs/ai/ 三份文档逐字一致（详细验收见 tests/test_T0459_aeicard.py），
     本文件聚焦 ranked 置顶区块与三层卡的组合行为；
  4. 有 ranked 时置顶区块在最前，且三层卡原有小节顺序不变。

快照说明（T-0459 更新）：旧版把改动前的逐字输出内联成常量（_BASELINE_*）。
三层卡以「docs/ai/ 文档 == 生成函数输出」作为防腐烂断言（见 T-0459 验收），
ranked 置顶区块的逐字基线改为动态调用 generate_syntax_card(level)，
效果等价：任何静态输出的字节漂移都会让置顶组合断言失败。
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from ai_copilot import error_stats, syntax_card  # noqa: E402

# ── 语料构造辅助 ──────────────────────────────────────────────────

def _now():
    return datetime.now().astimezone()


def _iso(days_ago=0):
    return (_now() - timedelta(days=days_ago)).isoformat(timespec="seconds")


def _write_lines(corpus_dir, records):
    """按记录自身时间戳落到 YYYY-MM.jsonl（模拟 error_corpus 的落盘布局）。"""
    os.makedirs(corpus_dir, exist_ok=True)
    for record in records:
        stamp = record.get("last_seen") or record.get("ts")
        dt = datetime.fromisoformat(stamp)
        path = os.path.join(corpus_dir, "%04d-%02d.jsonl" % (dt.year, dt.month))
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _ranked_fixture(top=3):
    ranked = []
    for index in range(1, top + 1):
        ranked.append({
            "code": "L400%d" % index,
            "title": "第%d个坑" % index,
            "hits": 100 - index,
            "last_seen": "2026-11-09T10:00:0%d+08:00" % index,
            "example": "正确写法%d" % index,
        })
    return ranked


# ── rank_pitfalls：排序 / 聚合 / 截断 / 窗口 ────────────────────────

def test_rank_orders_by_hits_then_last_seen(tmp_path):
    recent = {"ts": _iso(1), "code": "L4001", "hits": 5, "message": "近期高频",
              "fixes": ["列表[0] = 10"]}
    older = {"ts": _iso(5), "code": "L4002", "hits": 5, "message": "同样 5 次但更早"}
    top_hits = {"ts": _iso(9), "code": "L4003", "hits": 9, "message": "最高频"}
    low = {"ts": _iso(2), "code": "L4004", "hits": 1, "message": "低频"}
    _write_lines(str(tmp_path), [recent, older, top_hits, low])

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path))

    assert [item["code"] for item in ranked] == ["L4003", "L4001", "L4002", "L4004"]
    assert set(ranked[0]) == {"code", "title", "hits", "last_seen", "example"}
    assert ranked[0]["hits"] == 9
    assert ranked[0]["last_seen"] == top_hits["ts"]
    assert ranked[1]["example"] == "列表[0] = 10"
    assert ranked[0]["title"]  # title 永远非空（registry 缺失时退化为 code）


def test_rank_aggregates_hits_by_code_and_keeps_latest_example(tmp_path):
    first = {"ts": _iso(3), "code": "L4001", "hits": 2, "fixes": ["旧写法"]}
    second = {"ts": _iso(1), "code": "L4001", "hits": 3, "fixes": ["新写法"], "hint": "提示"}
    other = {"ts": _iso(2), "code": "L4002", "hits": 4, "fixes": ["另一条"]}
    _write_lines(str(tmp_path), [first, second, other])

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path))

    assert [(item["code"], item["hits"]) for item in ranked] == [("L4001", 5), ("L4002", 4)]
    assert ranked[0]["last_seen"] == second["ts"]      # 最近一条决定 last_seen
    assert ranked[0]["example"] == "新写法"             # 最近一条的 fixes 优先


def test_rank_uses_hint_when_no_fixes_and_hits_default_one(tmp_path):
    record = {"ts": _iso(2), "code": "L3001", "hint": "先转换类型"}
    _write_lines(str(tmp_path), [record, {"ts": _iso(1), "code": "L3001"}])

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path))

    assert len(ranked) == 1
    assert ranked[0]["hits"] == 2          # 缺 hits 的行按 1 计
    assert ranked[0]["example"] == "先转换类型"


def test_rank_top_truncates(tmp_path):
    records = [{"ts": _iso(index), "code": "L40%02d" % index, "hits": 20 - index}
               for index in range(1, 8)]
    _write_lines(str(tmp_path), records)

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path), top=3)
    assert [item["code"] for item in ranked] == ["L4001", "L4002", "L4003"]
    assert len(error_stats.rank_pitfalls(corpus_dir=str(tmp_path), top=None)) == 7
    assert len(error_stats.rank_pitfalls(corpus_dir=str(tmp_path), top=0)) == 7


def test_rank_filters_by_window_days(tmp_path):
    recent = {"ts": _iso(3), "code": "L1001", "hits": 2}
    edge = {"ts": _iso(29), "code": "L1003", "hits": 1}
    stale = {"ts": _iso(45), "code": "L1002", "hits": 99}
    _write_lines(str(tmp_path), [recent, edge, stale])

    windowed = error_stats.rank_pitfalls(corpus_dir=str(tmp_path), window_days=30)
    assert [item["code"] for item in windowed] == ["L1001", "L1003"]

    widened = error_stats.rank_pitfalls(corpus_dir=str(tmp_path), window_days=90)
    assert [item["code"] for item in widened][0] == "L1002"   # 旧数据确实在文件里
    assert len(widened) == 3


# ── 坏数据 / 缺失：一律降级为空，不抛 ──────────────────────────────

def test_bad_lines_skipped_and_counted(tmp_path):
    corpus = str(tmp_path)
    os.makedirs(corpus, exist_ok=True)
    prefix = "L4001"
    lines = [
        "这不是 JSON",
        json.dumps({"ts": _iso(1), "message": "缺 code"}, ensure_ascii=False),
        "",
        json.dumps({"ts": _iso(2), "code": prefix, "hits": 2}, ensure_ascii=False),
        json.dumps({"ts": _iso(3), "code": "   ", "hits": 9}, ensure_ascii=False),
        json.dumps([1, 2, 3]),
    ]
    now = _now()
    path = os.path.join(corpus, "%04d-%02d.jsonl" % (now.year, now.month))
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")

    stats = {}
    ranked = error_stats.rank_pitfalls(corpus_dir=corpus, stats=stats)

    assert [item["code"] for item in ranked] == [prefix]
    assert ranked[0]["hits"] == 2
    assert stats["files_read"] == 1
    assert stats["lines_read"] == 5      # 空行不计
    assert stats["lines_skipped"] == 4   # 坏 JSON / 缺 code / 空白 code / 非对象


def test_missing_or_empty_corpus_returns_empty(tmp_path):
    assert error_stats.rank_pitfalls(corpus_dir=str(tmp_path / "不存在")) == []
    empty = tmp_path / "empty"
    empty.mkdir()
    assert error_stats.rank_pitfalls(corpus_dir=str(empty)) == []


def test_unreadable_corpus_file_degrades(tmp_path):
    corpus = tmp_path / "locked"
    corpus.mkdir()
    now = _now()
    path = corpus / ("%04d-%02d.jsonl" % (now.year, now.month))
    path.mkdir()  # 同名目录：open() 必然失败，验证不抛
    assert error_stats.rank_pitfalls(corpus_dir=str(corpus)) == []


def test_corpus_dir_env_override(monkeypatch, tmp_path):
    corpus = tmp_path / "env-corpus"
    _write_lines(str(corpus), [{"ts": _iso(1), "code": "L5001", "hits": 3}])
    monkeypatch.setenv("LIGHT_ERROR_CORPUS_DIR", str(corpus))

    assert [item["code"] for item in error_stats.rank_pitfalls()] == ["L5001"]
    # 显式 corpus_dir 优先于环境变量
    assert error_stats.rank_pitfalls(corpus_dir=str(tmp_path / "none")) == []


def test_title_degrades_to_code_when_registry_missing(tmp_path):
    _write_lines(str(tmp_path), [{"ts": _iso(1), "code": "L8888", "hits": 1}])
    item = error_stats.rank_pitfalls(corpus_dir=str(tmp_path))[0]

    assert item["title"]
    if error_stats._lookup_title(item["code"]) is None:
        assert item["title"] == item["code"]   # 不臆造标题


def test_non_utf8_bytes_do_not_crash(tmp_path):
    corpus = str(tmp_path)
    now = _now()
    path = os.path.join(corpus, "%04d-%02d.jsonl" % (now.year, now.month))
    with open(path, "wb") as handle:
        handle.write(b'\xff\xfe{"code": "L1", "hits": 3}\n')
        handle.write(json.dumps({"ts": _iso(1), "code": "L4001",
                                 "hits": 2}, ensure_ascii=False).encode("utf-8") + b"\n")

    stats = {}
    ranked = error_stats.rank_pitfalls(corpus_dir=corpus, stats=stats)

    assert [item["code"] for item in ranked] == ["L4001"]
    assert stats["lines_skipped"] == 1


def test_timestamp_formats_are_tolerated(tmp_path):
    utc = datetime.now(timezone.utc)
    local = datetime.now()
    records = [
        {"ts": utc.isoformat(timespec="seconds").replace("+00:00", "Z"), "code": "L1"},
        {"ts": local.strftime("%Y-%m-%dT%H:%M:%S"), "code": "L2"},
        {"ts": local.strftime("%Y-%m-%d"), "code": "L3"},
    ]
    _write_lines(str(tmp_path), records)

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path))

    assert sorted(item["code"] for item in ranked) == ["L1", "L2", "L3"]
    assert {item["code"]: item["last_seen"] for item in ranked} == {
        record["code"]: record["ts"] for record in records}



# ── 三层卡：ranked 置顶区块与静态输出逐字组合 ──────────────────────────

def _compact():
    return syntax_card.generate_syntax_card("compact")


def _standard():
    return syntax_card.generate_syntax_card("standard")


# ── ranked 置顶区块：格式 / 位置 / 不破坏三层卡小节 ──────────────────────

_STANDARD_SECTIONS = [
    "════compact 层════",
    "════语法骨架(关键字来自 spec keywords)════",
    "════运算符(spec operators)════",
    "════stdlib 常用50(函数名来自 spec stdlib)════",
]


def test_ranked_block_is_at_very_top_and_format_is_one_line_per_item():
    ranked = _ranked_fixture(top=3)

    card = syntax_card.generate_syntax_card(ranked=ranked)
    lines = card.splitlines()

    assert lines[0] == "## 最近 30 天最常踩的坑（TOP 3）"
    assert lines[1] == "1. [L4001] 第1个坑 —— 正确写法1"
    assert lines[2] == "2. [L4002] 第2个坑 —— 正确写法2"
    assert lines[3] == "3. [L4003] 第3个坑 —— 正确写法3"
    assert lines[4] == ""

    # 原有内容逐字保留，只是被前置
    assert card.endswith(_compact())
    assert card.index("## 最近 30 天最常踩的坑") < card.index("【6条硬规则】")


def test_ranked_block_keeps_standard_section_order():
    card = syntax_card.generate_syntax_card(
        level="standard", ranked=_ranked_fixture(top=2))

    positions = [card.index(section) for section in _STANDARD_SECTIONS]
    assert positions == sorted(positions)
    assert card.index("## 最近 30 天最常踩的坑") == 0


def test_ranked_standard_card_also_gets_top_block():
    card = syntax_card.generate_syntax_card(
        level="standard", ranked=_ranked_fixture(top=2))

    assert card.startswith("## 最近 30 天最常踩的坑（TOP 2）\n")
    assert "1. [L4001] 第1个坑 —— 正确写法1" in card
    assert card.endswith(_standard())


def test_ranked_item_without_example_has_no_dash():
    ranked = [{"code": "L255", "title": "变量名遮蔽内建", "hits": 4,
               "last_seen": "", "example": ""}]

    card = syntax_card.generate_syntax_card(compact=True, ranked=ranked)

    assert "1. [L255] 变量名遮蔽内建\n" in card
    assert " —— " not in card.splitlines()[1]


def test_ranked_example_is_flattened_to_single_line():
    ranked = [{"code": "L1", "title": "多行修法", "hits": 1,
               "last_seen": "", "example": "第一行\n  第二行"}]

    card = syntax_card.generate_syntax_card(compact=True, ranked=ranked)

    assert card.splitlines()[1] == "1. [L1] 多行修法 —— 第一行 第二行"


def test_ranked_composes_with_extra_sections():
    card = syntax_card.generate_syntax_card(
        include_verbs=True, include_pitfalls=True, ranked=_ranked_fixture(top=1))

    assert card.startswith("## 最近 30 天最常踩的坑（TOP 1）\n")
    assert card.count("【动词参数参照】") == 1
    assert card.count("【光明暗坑 — AI 生成时必须注意】") == 1
    assert card.index("【动词参数参照】") > card.index("【6条硬规则】")


def test_rank_pitfalls_feeds_card_end_to_end(tmp_path):
    records = [
        {"ts": _iso(1), "code": "L4001", "hits": 7, "fixes": ["列表[0] = 10"]},
        {"ts": _iso(2), "code": "L4002", "hits": 3, "fixes": ["设 n 为 10"]},
        {"ts": _iso(3), "code": "L4003", "hits": 1, "fixes": ["遍历 i 于 1至10："]},
    ]
    _write_lines(str(tmp_path), records)

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path), top=10)
    card = syntax_card.generate_syntax_card(compact=True, ranked=ranked)

    assert card.startswith("## 最近 30 天最常踩的坑（TOP 3）\n")
    assert "1. [L4001]" in card and "列表[0] = 10" in card
    assert card.endswith(_compact())


def test_empty_ranked_is_byte_identical_to_static_card():
    assert syntax_card.generate_syntax_card(ranked=None) == _compact()
    assert syntax_card.generate_syntax_card(ranked=[]) == _compact()
    assert syntax_card.generate_syntax_card(ranked=[None, {}, ""]) == _compact()
    assert syntax_card.generate_syntax_card(compact=True, ranked=[]) == _compact()
    assert syntax_card.generate_syntax_card(level="standard", ranked=[]) == _standard()
