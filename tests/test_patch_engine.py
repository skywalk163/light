# -*- coding: utf-8 -*-
"""T-0379（R222-C 线）：``patch_engine`` 的契约测试。

覆盖：
- ``ast_to_json``：可 JSON 序列化、span 有序、叶子数 > 0、真实基准文件全量可跑；
- ``symbols_json``：定义 / 导入 / 导出 / 作用域 / 被引用次数、真实 .light 文件、
  canonical（NFKC）口径；
- ``patch``：单点 / 多点 / 相邻 / 插入 / CRLF，以及交叠、越界、不闭合、
  字段缺失、同位置插入等拒绝路径（必须抛 ``PatchError`` 且带中文原因）；
- ``diff_summary``：相同、字面量修改、改名、插入/删除、语法非法降级。

运行：
    PYTHONPATH=src python3 -m pytest -q -o addopts= tests/test_patch_engine.py
"""

import glob
import json
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_BENCHMARKS = os.path.join(_ROOT, "benchmarks", "programs")

import patch_engine as pe  # noqa: E402


# =============================================================================
# 测试助手
# =============================================================================

def _nodes(node):
    """深度优先遍历 AST JSON 里的所有节点。"""
    yield node
    for child in node.get("children", ()):
        yield from _nodes(child)


def _span(source, line_no, needle, occurrence=0):
    """按「第 line_no 行第 occurrence 次出现的 needle」算一个半开 span。

    列号 1 起，end 指向 needle 最后一个字符的下一位，与 patch_engine 口径一致。
    """
    line = source.split("\n")[line_no - 1]
    start = -1
    cursor = 0
    for _ in range(occurrence + 1):
        start = line.index(needle, cursor)
        cursor = start + 1
    start_col = start + 1
    return {
        "start_line": line_no,
        "start_col": start_col,
        "end_line": line_no,
        "end_col": start_col + len(needle),
    }


def _edit(span, text):
    return {"span": span, "text": text}


def _benchmark_files():
    return sorted(glob.glob(os.path.join(_BENCHMARKS, "*.light")))


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _definition(symbols, name, scope=None, kind=None):
    for item in symbols["definitions"]:
        if item["name"] != name:
            continue
        if scope is not None and item["scope"] != scope:
            continue
        if kind is not None and item["kind"] != kind:
            continue
        return item
    return None


def _assert_span_ordered(span):
    assert set(span) == {"start_line", "start_col", "end_line", "end_col"}
    for key in span:
        assert isinstance(span[key], int) and not isinstance(span[key], bool)
    assert span["start_line"] >= 0
    assert span["start_col"] >= 0
    if span["start_line"] > 0:
        assert (span["start_line"], span["start_col"]) <= (
            span["end_line"], span["end_col"]
        )


# =============================================================================
# ast_to_json
# =============================================================================

def test_ast_to_json_json_serializable_and_leaf_count():
    source = "设 甲 为 3\n打印 甲\n"
    ast = pe.ast_to_json(source, "示例.light")

    assert ast["file"] == "示例.light"
    assert ast["language"] == "light"
    assert ast["root"]["kind"] == "Module"

    dumped = json.dumps(ast, ensure_ascii=False)
    assert "Module" in dumped

    assert ast["source"]["node_count"] > 1
    assert ast["source"]["leaf_count"] > 0
    assert ast["source"]["max_depth"] >= 1
    assert len(list(_nodes(ast["root"]))) == ast["source"]["node_count"]


def test_ast_to_json_nodes_have_required_keys_and_ordered_spans():
    source = "段落 斐波那契(n):\n  如果 n 小于 2 那么：\n    返回 n\n  否则：\n    返回 n\n设 结果 为 斐波那契(20)\n"
    ast = pe.ast_to_json(source, "fib.light")
    nodes = list(_nodes(ast["root"]))

    for node in nodes:
        assert set(node) == {"kind", "span", "value", "fields", "children"}
        assert isinstance(node["kind"], str) and node["kind"]
        _assert_span_ordered(node["span"])

    # 父节点的起点不晚于子节点、终点不早于子节点（只比较有位置信息的子节点）。
    def check_parent_child(node):
        parent = node["span"]
        for child in node["children"]:
            child_span = child["span"]
            if child_span["start_line"] > 0:
                assert (child_span["start_line"], child_span["start_col"]) >= (
                    parent["start_line"], parent["start_col"]
                )
                assert (child_span["end_line"], child_span["end_col"]) <= (
                    parent["end_line"], parent["end_col"]
                )
            check_parent_child(child)

    check_parent_child(ast["root"])

    paragraphs = [node for node in nodes if node["kind"] == "Paragraph"]
    assert paragraphs, "应至少有一个段落定义"
    assert paragraphs[0]["span"]["start_line"] == 1
    assert paragraphs[0]["span"]["end_line"] >= 5


def test_ast_to_json_literal_value_and_fields():
    source = "设 甲 为 42\n打印 甲\n打印 \"你好\"\n"
    nodes = list(_nodes(pe.ast_to_json(source)["root"]))

    numbers = [node for node in nodes if node["kind"] == "NumberLiteral"]
    assert any(node["value"] == 42 for node in numbers)

    strings = [node for node in nodes if node["kind"] == "StringLiteral"]
    assert any(node["value"] == "你好" for node in strings)

    identifiers = [node for node in nodes if node["kind"] == "Identifier"]
    assert any(node["fields"].get("name") == "甲" for node in identifiers)

    variables = [node for node in nodes if node["kind"] == "VarDecl"]
    assert variables[0]["fields"]["name"] == "甲"


def test_ast_to_json_is_deterministic():
    source = _read(os.path.join(_BENCHMARKS, "fibonacci.light"))
    first = json.dumps(pe.ast_to_json(source), ensure_ascii=False, sort_keys=True)
    second = json.dumps(pe.ast_to_json(source), ensure_ascii=False, sort_keys=True)
    assert first == second


def test_ast_to_json_accepts_empty_source():
    ast = pe.ast_to_json("")
    assert ast["root"]["kind"] == "Module"
    assert ast["root"]["children"] == []
    assert ast["source"]["node_count"] == 1
    assert ast["source"]["leaf_count"] == 1


@pytest.mark.parametrize("path", _benchmark_files(), ids=lambda p: os.path.basename(p))
def test_ast_to_json_on_real_benchmark_programs(path):
    ast = pe.ast_to_json(_read(path), os.path.basename(path))
    json.dumps(ast, ensure_ascii=False)
    assert ast["root"]["kind"] == "Module"
    assert ast["source"]["leaf_count"] > 0
    for node in _nodes(ast["root"]):
        _assert_span_ordered(node["span"])


# =============================================================================
# symbols_json
# =============================================================================

@pytest.mark.parametrize("path", _benchmark_files(), ids=lambda p: os.path.basename(p))
def test_symbols_json_on_real_benchmark_programs(path):
    label = os.path.basename(path)
    symbols = pe.symbols_json(_read(path), label)

    assert symbols["file"] == label
    assert symbols["definitions"], f"{label} 应至少有一个定义"
    assert symbols["stats"]["definition_count"] == len(symbols["definitions"])
    assert symbols["stats"]["scope_count"] == len(symbols["scopes"])
    json.dumps(symbols, ensure_ascii=False)

    for definition in symbols["definitions"]:
        assert definition["name"]
        assert definition["canonical"] == definition["canonical"].strip()
        assert definition["kind"]
        assert definition["scope"]
        assert isinstance(definition["references"], int)
        assert definition["references"] >= 0
        _assert_span_ordered(definition["span"])

    scopes = {scope["path"]: scope for scope in symbols["scopes"]}
    assert "module" in scopes
    assert scopes["module"]["parent"] is None


def test_symbols_json_fibonacci_definitions_and_references():
    source = _read(os.path.join(_BENCHMARKS, "fibonacci.light"))
    symbols = pe.symbols_json(source, "fibonacci.light")

    function = _definition(symbols, "斐波那契", scope="module", kind="function")
    assert function is not None
    assert function["references"] == 3  # 函数体内两次递归 + 顶层一次调用
    assert function["span"]["start_line"] == 2

    parameter = _definition(symbols, "n", scope="module.斐波那契", kind="parameter")
    assert parameter is not None
    assert parameter["references"] == 4  # 条件 1 次 + 返回 1 次 + 两次递归实参

    variable = _definition(symbols, "结果", scope="module", kind="variable")
    assert variable is not None
    assert variable["references"] == 1

    assert "module.斐波那契" in {scope["path"] for scope in symbols["scopes"]}
    assert "打印" in symbols["unresolved"]  # 内建/外部名不落到本文件定义


def test_symbols_json_class_scopes_and_members():
    source = _read(os.path.join(_BENCHMARKS, "class_system.light"))
    symbols = pe.symbols_json(source, "class_system.light")

    assert _definition(symbols, "形状", scope="module", kind="class") is not None
    assert _definition(symbols, "名称", scope="module.形状", kind="attribute") is not None
    assert _definition(symbols, "面积", scope="module.形状", kind="method") is not None
    assert _definition(symbols, "矩形", scope="module", kind="class") is not None

    # 继承关系是一次真实的符号引用
    shape = _definition(symbols, "形状", scope="module", kind="class")
    assert shape["references"] >= 3  # 矩形/圆形/Triangle 三个子类

    scopes = {scope["path"] for scope in symbols["scopes"]}
    assert {"module.形状", "module.矩形", "module.形状.面积"} <= scopes


def test_symbols_json_self_member_resolves_to_class_attribute():
    source = (
        "类 盒子：\n"
        "  属性 值\n"
        "  构造(值)：\n"
        "    己.值 为 值\n"
        "  段落 取()：\n"
        "    返回 己.值\n"
    )
    symbols = pe.symbols_json(source, "box.light")

    attribute = _definition(symbols, "值", scope="module.盒子", kind="attribute")
    parameter = _definition(symbols, "值", scope="module.盒子.__init__", kind="parameter")
    assert attribute is not None and parameter is not None
    # `己.值`（成员）算属性引用，裸 `值` 才算形参引用，两者不能串。
    assert attribute["references"] == 2
    assert parameter["references"] == 1
    # `己`/`self` 是接收者关键字，不应作为符号引用出现在结果里。
    assert "self" not in symbols["unresolved"]
    assert "己" not in symbols["unresolved"]


def test_symbols_json_imports_exports_and_function_scope():
    source = (
        "导入 数学\n"
        "从 字符串 导入 格式化, 连接\n"
        "段落 计算(甲, 乙):\n"
        "  设 和 为 甲 加 乙\n"
        "  返回 和\n"
        "设 结果 为 计算(1, 2)\n"
        "导出 计算, 结果\n"
    )
    symbols = pe.symbols_json(source, "io.light")

    imports = {item["module"]: item for item in symbols["imports"]}
    assert imports["数学"]["names"] == []
    assert imports["字符串"]["names"] == ["格式化", "连接"]
    assert imports["字符串"]["scope"] == "module"

    assert symbols["exports"][0]["names"] == ["计算", "结果"]
    assert symbols["exports"][0]["canonical_names"] == ["计算", "结果"]

    assert _definition(symbols, "格式化", scope="module", kind="import") is not None
    assert _definition(symbols, "连接", scope="module", kind="import") is not None
    assert _definition(symbols, "计算", scope="module", kind="function")["references"] == 1
    assert _definition(symbols, "和", scope="module.计算", kind="variable")["references"] == 1
    assert _definition(symbols, "结果", scope="module", kind="variable")["references"] == 0


def test_symbols_json_canonical_is_nfkc():
    # 全角 Ａ 与半角 A 在 Python 标识符归一后是同一个名字（D 线 --canonical 口径）。
    symbols = pe.symbols_json("设 Ａ 为 1\n打印 A\n", "canonical.light")
    definition = _definition(symbols, "Ａ", scope="module", kind="variable")
    assert definition is not None
    assert definition["canonical"] == "A"
    assert definition["references"] == 1
    resolved = [item for item in symbols["references"] if item["canonical"] == "A"]
    assert resolved and resolved[0]["resolved"] is True


# =============================================================================
# patch
# =============================================================================

def test_patch_single_replacement():
    source = "设 甲 为 3\n打印 甲\n"
    span = _span(source, 1, "3")
    assert span == {"start_line": 1, "start_col": 7, "end_line": 1, "end_col": 8}
    assert pe.patch(source, [_edit(span, "42")]) == "设 甲 为 42\n打印 甲\n"


def test_patch_multi_non_overlapping_and_unsorted():
    source = "设 甲 为 3\n打印 甲\n"
    edits = [
        _edit(_span(source, 2, "甲"), "乙"),
        _edit(_span(source, 1, "3"), "42"),
        _edit(_span(source, 1, "甲"), "丙"),
    ]
    assert pe.patch(source, edits) == "设 丙 为 42\n打印 乙\n"


def test_patch_adjacent_edits_are_allowed():
    source = "abcdef\n"
    edits = [
        _edit({"start_line": 1, "start_col": 1, "end_line": 1, "end_col": 2}, "A"),
        _edit({"start_line": 1, "start_col": 2, "end_line": 1, "end_col": 4}, "B"),
    ]
    assert pe.patch(source, edits) == "ABdef\n"


def test_patch_insertion_and_deletion():
    source = "设 甲 为 3\n"
    insertion = _edit({"start_line": 1, "start_col": 8, "end_line": 1, "end_col": 8}, "\n打印 甲")
    assert pe.patch(source, [insertion]) == "设 甲 为 3\n打印 甲\n"

    deletion = _edit(_span(source, 1, " 为 3"), "")
    assert pe.patch(source, [deletion]) == "设 甲\n"


def test_patch_empty_edits_returns_source_unchanged():
    source = "设 甲 为 3\n"
    assert pe.patch(source, []) == source


def test_patch_preserves_crlf_line_endings():
    source = "设 甲 为 3\r\n打印 甲\r\n"
    span = {"start_line": 1, "start_col": 7, "end_line": 1, "end_col": 8}
    assert pe.patch(source, [_edit(span, "42")]) == "设 甲 为 42\r\n打印 甲\r\n"


def test_patch_rejects_overlapping_edits():
    source = "abcdef\n"
    edits = [
        _edit({"start_line": 1, "start_col": 1, "end_line": 1, "end_col": 3}, "X"),
        _edit({"start_line": 1, "start_col": 2, "end_line": 1, "end_col": 4}, "Y"),
    ]
    with pytest.raises(pe.PatchError) as excinfo:
        pe.patch(source, edits)
    assert "交叠" in str(excinfo.value)


@pytest.mark.parametrize(
    "span",
    [
        {"start_line": 99, "start_col": 1, "end_line": 99, "end_col": 1},
        {"start_line": 0, "start_col": 1, "end_line": 1, "end_col": 1},
        {"start_line": 1, "start_col": 99, "end_line": 1, "end_col": 99},
        {"start_line": 1, "start_col": 1, "end_line": 9, "end_col": 1},
    ],
)
def test_patch_rejects_out_of_bounds(span):
    with pytest.raises(pe.PatchError) as excinfo:
        pe.patch("abc\n", [_edit(span, "x")])
    assert "越界" in str(excinfo.value)


def test_patch_rejects_unclosed_span():
    span = {"start_line": 1, "start_col": 4, "end_line": 1, "end_col": 2}
    with pytest.raises(pe.PatchError) as excinfo:
        pe.patch("abcdef\n", [_edit(span, "x")])
    assert "不闭合" in str(excinfo.value)


def test_patch_rejects_same_position_inserts():
    position = {"start_line": 1, "start_col": 1, "end_line": 1, "end_col": 1}
    with pytest.raises(pe.PatchError) as excinfo:
        pe.patch("abc\n", [_edit(position, "X"), _edit(position, "Y")])
    assert "同一位置插入" in str(excinfo.value)


@pytest.mark.parametrize(
    "edits,expected",
    [
        ([{"text": "x"}], "缺少 span"),
        ([{"span": {"start_line": 1, "start_col": 1, "end_line": 1, "end_col": 1}}], "缺少 text"),
        ([{"span": {"start_line": 1}, "text": "x"}], "缺少字段"),
        (
            [_edit({"start_line": "1", "start_col": 1, "end_line": 1, "end_col": 1}, "x")],
            "必须是整数",
        ),
        (
            [_edit({"start_line": 1, "start_col": 1, "end_line": 1, "end_col": 1}, 42)],
            "text 必须是字符串",
        ),
        ("not-a-list", "必须是列表"),
        ([["not-a-dict"]], "必须是字典"),
    ],
)
def test_patch_rejects_malformed_edits(edits, expected):
    with pytest.raises(pe.PatchError) as excinfo:
        pe.patch("abc\n", edits)
    assert expected in str(excinfo.value)


# =============================================================================
# diff_summary
# =============================================================================

def test_diff_summary_identical():
    source = "设 甲 为 1\n打印 甲\n"
    summary = pe.diff_summary(source, source)
    assert summary["identical"] is True
    assert summary["blocks"] == []
    assert summary["changed_lines"] == {"old": [], "new": []}
    assert summary["symbols"]["available"] is True
    assert summary["symbols"]["added"] == []
    assert summary["symbols"]["removed"] == []


def test_diff_summary_literal_change_reports_affected_symbol():
    old = "段落 计算(甲):\n  返回 甲 加 1\n设 结果 为 计算(2)\n"
    new = "段落 计算(甲):\n  返回 甲 加 2\n设 结果 为 计算(2)\n"
    summary = pe.diff_summary(old, new)

    assert summary["identical"] is False
    assert summary["changed_lines"] == {"old": [2], "new": [2]}
    assert summary["blocks"][0]["kind"] == "replace"
    assert summary["blocks"][0]["old_text"] == "  返回 甲 加 1"

    affected = {item["name"] for item in summary["symbols"]["affected"]}
    assert "计算" in affected
    assert summary["symbols"]["added"] == []
    assert summary["symbols"]["removed"] == []


def test_diff_summary_rename_detects_added_and_removed_symbols():
    old = "段落 旧名():\n  返回 1\n设 值 为 旧名()\n"
    new = "段落 新名():\n  返回 1\n设 值 为 新名()\n"
    summary = pe.diff_summary(old, new)

    added = {item["name"] for item in summary["symbols"]["added"]}
    removed = {item["name"] for item in summary["symbols"]["removed"]}
    referenced = set(summary["symbols"]["referenced"])
    assert "新名" in added
    assert "旧名" in removed
    assert {"旧名", "新名"} <= referenced


def test_diff_summary_insert_and_delete_blocks():
    base = "设 甲 为 1\n设 乙 为 2\n"
    with_insert = "设 甲 为 1\n设 丙 为 3\n设 乙 为 2\n"
    inserted = pe.diff_summary(base, with_insert)
    assert any(block["kind"] == "insert" for block in inserted["blocks"])
    assert 2 in inserted["changed_lines"]["new"]

    deleted = pe.diff_summary(with_insert, base)
    assert any(block["kind"] == "delete" for block in deleted["blocks"])
    assert 2 in deleted["changed_lines"]["old"]


def test_diff_summary_degrades_gracefully_on_parse_error():
    summary = pe.diff_summary("设 甲 为 1\n", "这不是合法的光明代码 @@@\n")
    assert summary["identical"] is False
    assert summary["blocks"], "行级 diff 仍应返回"
    assert summary["symbols"]["available"] is False
    assert summary["symbols"]["error"]


# =============================================================================
# 模块边界
# =============================================================================

def test_patch_engine_does_not_import_cli():
    with open(pe.__file__, encoding="utf-8") as handle:
        module_source = handle.read()
    assert "import cli" not in module_source
    assert "from cli" not in module_source
    assert "from light_parser_v3 import LightParser" in module_source
