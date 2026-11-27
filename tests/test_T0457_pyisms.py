# -*- coding: utf-8 -*-
"""T-0457 验收：AI 惯性诊断（D1xx）+ 消灭 ``L0000`` 占位码。

这张卡的现场是：``light ai check --json`` 对着一个 Python 写法的文件只吐出

    {"code": "L0000", "message": "无法识别的语法元素：':'。", "provisional": true}

——真错的是 ``def``，报错却指向冒号，``fixes`` 还是把 ``hint`` 抄了一遍。
本文件的判据按「agent 拿到的东西到底能不能照着修」来写：

* :func:`src.ai_pyisms.scan` 覆盖 ``docs/AI编程指南.md`` §六 全部 14 条，
  每条断言 ``code`` / ``line:column`` / ``replacement``；
* ``def`` 这一条额外断言 replacement **不含 def 且含「段落」**，并且
  ``message`` 明确说「别去修冒号」；
* :func:`src.diagnostics.explain` 对 ``def`` / ``if`` / ``&&`` / ``True``
  返回 ``code`` 以 ``D1`` 开头的诊断，且 ``provisional=False``；
* 同时踩 5 种惯性的样本 → 正好 5 条发现，没有一条是 ``L0000``；
* 把 ``replacement`` 逐行贴回去再扫，必须**一条都不剩**（自愈闭环）。

本文件自包含：显式把仓根加进 ``sys.path``，不依赖 conftest 的隐式行为。
"""

from __future__ import annotations

import sys
from dataclasses import fields
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai_pyisms import (  # noqa: E402
    PYISM_CODES,
    PYISM_CODE_PATTERN,
    Finding,
    all_codes,
    code_info,
    scan,
)
from src.diagnostics import (  # noqa: E402
    all_diagnostic_codes,
    all_pyism_codes,
    diagnostic,
    explain,
    explain_pyisms,
    format_diagnostic,
)

#: 卡里引用的现场：那份「只报了冒号」的文件。
BUG_SOURCE = 'def 问候():\n    print("hi")\n'
BUG_MESSAGE = "无法识别的语法元素：':'。"


def _findings(source: str):
    return scan(source)


def _one(source: str, code: str) -> Finding:
    """取该行该码的唯一一条发现；数量不对直接红。"""
    hits = [f for f in scan(source) if f.code == code]
    assert len(hits) == 1, f"{code} 命中 {len(hits)} 条：{[f.code for f in scan(source)]}"
    return hits[0]


# ---------------------------------------------------------------------------
# 14 条 + 细项：一条一行，断言 code / line:column / replacement
# ---------------------------------------------------------------------------
#: (code, 源码, 期望的 1-based 行, 期望的 1-based 列, 期望的整行 replacement)
CASES = [
    # 错误 1：def / function
    ("D101", "def 加法(甲, 乙):", 1, 1, "段落 加法 接收 甲, 乙："),
    ("D101", "def 问候():", 1, 1, "段落 问候："),
    ("D101", "    def 内层(x):", 1, 5, "    段落 内层 接收 x："),
    # 错误 2：if / for / while（含 elif / else 细项）
    ("D102", "if x > 0:", 1, 1, "如果 x > 0："),
    ("D103", "elif x == 0:", 1, 1, "否则如果 x == 0："),
    ("D104", "else:", 1, 1, "否则："),
    ("D105", "for 项 in 列表:", 1, 1, "遍历 项 于 列表："),
    ("D106", "while 计数 < 3:", 1, 1, "当 计数 < 3："),
    ("D107", "return 甲 + 乙", 1, 1, "返回 甲 + 乙"),
    # 错误 3：True / False / None
    ("D108", "设 标志 为 True", 1, 8, "设 标志 为 真"),
    ("D108", "设 值 为 None", 1, 7, "设 值 为 空"),
    ("D108", "设 名 为 False", 1, 7, "设 名 为 假"),
    # 错误 4：&& / || / ! 与 and / or / not
    ("D109", "如果 a > 0 && b > 0：", 1, 10, "如果 a > 0 且 b > 0："),
    ("D109", "如果 a || b：", 1, 6, "如果 a 或 b："),
    ("D109", "如果 !标志：", 1, 4, "如果 非 标志："),
    ("D110", "设 结论 为 a and b", 1, 10, "设 结论 为 a 且 b"),
    ("D110", "设 结论 为 a or b", 1, 10, "设 结论 为 a 或 b"),
    ("D110", "设 结论 为 not a", 1, 8, "设 结论 为 非 a"),
    # 错误 5：空容器
    ("D111", "设 列表 为 新建列表()", 1, 8, "设 列表 为 列表创建()"),
    ("D112", "设 字典 为 dict()", 1, 8, "设 字典 为 字典创建()"),
    # 错误 6：追加
    ("D113", "追加(列表, 项)", 1, 1, "列表.追加(项)"),
    ("D113", "    追加(缓冲, 行)", 1, 5, "    缓冲.追加(行)"),
    # 错误 7：遍历介词
    ("D114", "遍历 项 之 列表：", 1, 6, "遍历 项 于 列表："),
    # 错误 8：单引号
    ("D115", "设 s 为 'hello'", 1, 7, '设 s 为 "hello"'),
    # 错误 9：构造函数名
    ("D116", "类 动物：\n    段落 __init__ 接收 名字：\n        设 己.名字 为 名字",
     2, 8, "    段落 初始化 接收 名字："),
    # 错误 10：实例属性
    ("D117", "类 动物：\n    段落 初始化 接收 名字：\n        设 名字 为 名字",
     3, 11, "        设 己.名字 为 名字"),
    # 错误 11：英文模块名
    ("D118", "从 math 导入 sqrt", 1, 3, "从 数学 导入 sqrt"),
    # 错误 12：print
    ("D119", 'print("hi")', 1, 1, '打印("hi")'),
    ("D119", "    打印(1)\nprint(2)", 2, 1, "打印(2)"),
    # 错误 13 / 14：无安全整行替换 → replacement 为空串
    ("D120", "设 翻倍 为 lambda x: x * 2", 1, 8, ""),
    ("D121", 'with open("f.txt") as fh:', 1, 1, ""),
]


@pytest.mark.parametrize("code, source, line, column, replacement", CASES)
def test_case(code, source, line, column, replacement):
    """每条用例断言 code / line:column / replacement 三项。"""
    finding = _one(source, code)
    assert finding.line == line
    assert finding.column == column
    assert finding.replacement == replacement
    assert finding.message.strip()
    assert finding.end_column == finding.column + len(finding.wrong)


def test_14_guide_items_all_covered():
    """指南 §六 的 14 条必须条条有码，不许漏项。"""
    covered = {code for code, *_ in CASES}
    for must in (
        "D101",  # 1 def
        "D102", "D105", "D106",  # 2 if/for/while
        "D108",  # 3 True/False/None
        "D109",  # 4 && || !
        "D111", "D112",  # 5 空容器
        "D113",  # 6 追加
        "D114",  # 7 遍历介词
        "D115",  # 8 单引号
        "D116",  # 9 __init__
        "D117",  # 10 己.
        "D118",  # 11 英文模块名
        "D119",  # 12 print
        "D120",  # 13 lambda
        "D121",  # 14 with
    ):
        assert must in covered, f"{must} 没有用例"


def test_every_registered_code_has_a_case():
    """反向对拍：码表里新增了码却忘了补用例 → 红。"""
    assert set(all_codes()) <= {code for code, *_ in CASES}


def test_code_format_and_uniqueness():
    codes = [info.code for info in PYISM_CODES]
    assert len(codes) == len(set(codes))
    for info in PYISM_CODES:
        assert PYISM_CODE_PATTERN.fullmatch(info.code), info.code
        assert info.name.startswith("PY_"), info.name
        assert info.title and info.hint and info.docs
        assert info.severity in ("error", "warning", "info")


def test_severity_never_silently_upgraded():
    """指南写「部分版本不支持 / 静默不生效」的坑必须保持 warning。"""
    for code in ("D108", "D111", "D113", "D114", "D115", "D116", "D117"):
        assert code_info(code).severity == "warning", code
    # 真编译不过的必须是 error，不能被降成 warning 糊过去
    for code in ("D101", "D102", "D105", "D106", "D109", "D119"):
        assert code_info(code).severity == "error", code


# ---------------------------------------------------------------------------
# 卡的原始现场：def 这条
# ---------------------------------------------------------------------------
def test_def_case_points_at_def_not_colon():
    findings = scan(BUG_SOURCE)
    defs = [f for f in findings if f.code == "D101"]
    assert len(defs) == 1
    finding = defs[0]
    assert "def" not in finding.replacement
    assert "段落" in finding.replacement
    assert "冒号" in finding.message, "必须明确告诉 agent 别去修冒号"
    assert finding.wrong == "def"
    assert finding.column == 1


def test_bug_source_has_no_placeholder_code():
    """同一个文件里不能再出现 L0000 这种占位码。"""
    findings = scan(BUG_SOURCE)
    assert findings, "现场文件必须扫得出东西"
    assert len(findings) == 2  # D101 + D119
    assert all(f.code.startswith("D1") for f in findings)
    assert all(f.code != "L0000" for f in findings)


# ---------------------------------------------------------------------------
# explain() 归因：D1xx 真码、provisional=False
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "source, code",
    [
        ("def 加法(甲, 乙):\n    return 甲 + 乙\n", "D101"),
        ("if x > 0:\n    打印(x)\n", "D102"),
        ("如果 a > 0 && b > 0：", "D109"),
        ("设 标志 为 True", "D108"),
    ],
)
def test_explain_returns_d_code(source, code):
    diag = explain(BUG_MESSAGE, source=source)
    assert diag is not None
    assert diag.code.startswith("D1")
    assert diag.code == code
    assert diag.provisional is False
    assert diag.line >= 1 and diag.column >= 1
    assert diag.severity in ("error", "warning")


def test_explain_pyisms_direct_entry():
    """CLI 侧可以不用 explain()，直接吃 explain_pyisms()。"""
    diag = explain_pyisms(BUG_SOURCE)
    assert diag is not None and diag.code == "D101"
    assert diag.candidates and "段落" in diag.candidates[0]
    assert explain_pyisms("") is None
    assert explain_pyisms("设 甲 为 1") is None  # 正常光明代码不该报
    assert explain_pyisms(BUG_SOURCE, stage="类型") is None  # 类型阶段不归它管


def test_explain_without_source_keeps_legacy_attribution():
    """不给源码时行为不变：仍按报错文本正则归因，绝不把报错文本当源码扫。

    报错文本引用出错 token 时也用单引号，当源码扫会把每条语法错误都误判成
    「字符串用了单引号」——这条用例就是钉死这个回归点。
    """
    diag = explain(BUG_MESSAGE)
    assert diag is None  # 旧行为：归不上就是 None，不造假码
    legacy = explain("未知的标记 'def'，函数请用「段落」定义")
    assert legacy is not None and legacy.code == "L1001"
    assert legacy.provisional is True


def test_explain_still_refuses_to_invent_codes():
    assert explain("这个报错文本和任何码都对不上") is None
    assert explain("") is None
    assert explain(None) is None


# ---------------------------------------------------------------------------
# 同时踩 5 种惯性：5 条发现、一条 L0000 都没有，且照 replacement 能自愈
# ---------------------------------------------------------------------------
FIVE_WAYS = (
    "def 打招呼():\n"
    "    print(1)\n"
    "if 真:\n"
    "for 项 in [1, 2]:\n"
    "while 真:\n"
)


def test_five_pyisms_five_findings():
    findings = scan(FIVE_WAYS)
    assert len(findings) == 5, [(f.code, f.line) for f in findings]
    assert [f.code for f in findings] == ["D101", "D119", "D102", "D105", "D106"]
    assert all(f.code != "L0000" for f in findings)
    assert [f.line for f in findings] == [1, 2, 3, 4, 5]


def test_replacement_roundtrip_cleans_the_file():
    """把每行的 replacement 贴回去，再扫必须一条都不剩（自愈闭环）。"""
    lines = FIVE_WAYS.splitlines()
    by_line = {f.line: f for f in scan(FIVE_WAYS)}
    healed = [by_line[i].replacement if i in by_line else text
              for i, text in enumerate(lines, 1)]
    assert scan("\n".join(healed)) == []


# ---------------------------------------------------------------------------
# 不许和字符串 / 注释打架（这是「不用正则扫全文」的验收点）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "source",
    [
        '打印("if x > 0 && True")',
        '# def 问候(): print("hi")',
        '设 提示 为 "for 项 in 列表:"  # while True',
        '"""\ndef 旧的():\n    print(1)\n"""',
        "设 甲 为 1\n设 乙 为 甲 且 甲\n打印(乙)",
        "",
        "   \n\n",
    ],
)
def test_string_and_comment_are_invisible(source):
    """字符串体里的 Python 关键字 / 注释里的整行代码都不算惯性。"""
    assert scan(source) == []


@pytest.mark.parametrize(
    "source, only_code",
    [
        ("设 提示 为 'def 问候():'", "D115"),
        ("设 提示 为 'if x > 0:'", "D115"),
        ("设 提示 为 'True'", "D115"),
        ("设 提示 为 '&&'", "D115"),
    ],
)
def test_python_words_inside_strings_are_not_keyword_findings(source, only_code):
    """单引号串里的 def / if / True / && 只该报「单引号」一条，不该报关键字码。"""
    codes = [f.code for f in scan(source)]
    assert codes == [only_code], codes


def test_embed_block_is_skipped():
    """``引 C:`` / ``引 Python:`` 块里本来就是外语代码，整块不许报。

    反例（真实语料）：``examples/J阶段_L4_C_Go_MoonBit/J1_C_快速求和.light``
    的 ``for (int i = 0; ...)`` 会被 D105 误判，必须跳过。
    """
    source = "\n".join([
        "引 C:",
        "    double 求和(double* arr, int n) {",
        "        for (int i = 0; i < n; i++) s += arr[i];",
        "        if (n <= 1) return 1;",
        "    }",
        "    结束引",
        '打印("done")',
    ])
    assert scan(source) == []


def test_embed_block_without_end_marker_swallows_rest():
    """没有 ``结束引`` 时块吃到文件末尾——与词法器切块口径一致。"""
    source = "\n".join(["引 Python:", "print(1)", "def f():", "    return True"])
    assert scan(source) == []


def test_code_after_closed_embed_block_is_still_scanned():
    source = "\n".join(["引 Python:", "print(1)", "结束引", "print(9)"])
    assert [(f.code, f.line) for f in scan(source)] == [("D119", 4)]


@pytest.mark.parametrize(
    "source",
    [
        "从 JSONL 导入 逐行读JSONL",  # stdlib/JSONL.light 真实存在
        "从 os 导入 路径连接",
        "从 CSV 导入 CSV读取",
    ],
)
def test_real_ascii_modules_are_not_flagged(source):
    """真模块名（哪怕全是英文）不许判死：``从 JSONL 导入`` 是合法写法。"""
    assert scan(source) == []


def test_unknown_ascii_module_keeps_replacement_empty():
    """认不出的英文模块名：报出来但不编中文名（replacement 必须是空串）。"""
    findings = scan("从 numpy 导入 array")
    assert [f.code for f in findings] == ["D118"]
    assert findings[0].replacement == ""
    assert "docs/STDLIB_REFERENCE.md" in findings[0].message


def test_line_and_column_are_character_based():
    """中文按 1 个字符算列：第 2 行的 print 在第 9 列（缩进 8 + 1）。"""
    source = "段落 外层：\n        设 值 为 print(1)\n"
    finding = _one(source, "D119")
    assert (finding.line, finding.column) == (2, 15)
    assert finding.end_column == 20


# ---------------------------------------------------------------------------
# 数据模型与码表收编
# ---------------------------------------------------------------------------
def test_finding_has_exactly_eight_fields():
    assert [f.name for f in fields(Finding)] == [
        "line", "column", "end_column", "code", "wrong", "right", "message", "replacement",
    ]


def test_pyism_codes_registered_but_not_mixed_into_l_codes():
    """D 码进 PYISM_DIAGNOSTICS，但**不**污染 L 码全集（T-0378 条数被锁死）。"""
    assert set(all_pyism_codes()) == set(all_codes())
    assert not any(code.startswith("D") for code in all_diagnostic_codes())
    spec = diagnostic("D101")
    assert spec.severity == "error" and spec.anchor == "parser"
    with pytest.raises(KeyError):
        diagnostic("D198")  # 未登记就是未登记，不返回空


def test_format_diagnostic_accepts_d_codes():
    payload = format_diagnostic("D101", "demo.light", 1, 1)
    assert payload["code"] == "D101"
    assert payload["line"] == 1 and payload["column"] == 1
    assert payload["message"] and payload["hint"]
    assert payload["anchor"] == "parser"


def test_scan_rejects_non_string():
    with pytest.raises(TypeError):
        scan(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        scan(b"def f():")  # type: ignore[arg-type]


def test_no_duplicate_finding_on_one_line():
    """同一行重复踩同一个坑只报一次（避免刷屏）。"""
    findings = scan("设 标志 为 True 且 另一个 为 True")
    assert len(findings) == 1
    assert findings[0].code == "D108"
