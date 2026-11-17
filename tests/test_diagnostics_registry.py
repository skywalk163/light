# -*- coding: utf-8 -*-
"""T-0316：结构化错误码框架 / 码表的验收测试。

判据（对应任务卡「完成标准」）：
* ≥14 条规则，每条至少一组正例（命中）与反例（不命中）；
* ``explain()`` 未命中返回 ``None``，不造兜底假码；
* ``to_dict`` / ``from_dict`` 往返相等；
* 同一错误码出现在两条规则里 → 测试失败（且有反向验证，判据不是弱断言）；
* ``to_legacy_entry`` 转换后 ``format()`` 与直接构造 ``ErrorEntry`` 逐字一致。

本文件自包含：显式把仓根加进 ``sys.path``，不依赖 conftest 的隐式行为。
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.diagnostics import (  # noqa: E402
    CODE_PATTERN,
    CODE_SEGMENTS,
    DIAGNOSTIC_FIELDS,
    MAX_FIXES,
    RULES,
    SEVERITIES,
    Diagnostic,
    Rule,
    all_codes,
    duplicate_codes,
    explain,
    get,
    to_legacy_entry,
)
from src.errors import ErrorEntry  # noqa: E402

# ---------------------------------------------------------------------------
# 每条规则一组 (code, 正例, 反例)。
# 正例尽量取自仓库里的真实报错模板；反例是「看起来相关但实际不该命中」的文本，
# 断言的是**全局** explain() 返回 None，比只断言不命中本码更有判别力。
# ---------------------------------------------------------------------------
CASES = [
    (
        "L1001",
        "未知的标记 'def'，函数请用「段落」定义",
        "段落 加法 接收 甲, 乙： 语法正确",
    ),
    (
        "L1002",
        "不支持的语句 'if x > 0:'，请改用「如果」",
        "如果 x > 0： 打印(x) 正常",
    ),
    (
        "L1003",
        "不支持的运算符 '&&'，光明用「且」",
        "如果 a > 0 且 b > 0 或 非 c： 正常",
    ),
    (
        "L1004",
        "不支持三元表达式 'a ? b : c'，请写「真值 如果 条件 否则 假值」",
        "设 结果 为 大值 如果 甲 > 乙 否则 小值 正常",
    ),
    (
        "L1005",
        "不支持单引号字符串 'hello'，请改用双引号",
        '设 s 为 "hello" 正常',
    ),
    (
        "L1006",
        "「空」是保留字（值类型），不可作标识符（变量名/下标名）。请改用其他名称。",
        "设 标志 为 真 正常",
    ),
    (
        "L1007",
        "单行段落体后顶层语句静默空跑、rc=0 零输出",
        "多行缩进体与顶层打印均正常",
    ),
    (
        "L2001",
        "参数数量错误: 段落「加法」期望 2 个参数，实际传入 3 个",
        "段落「加法」参数数量正确",
    ),
    (
        "L2002",
        "未定义的名称 'True'，布尔值请写真/假/空",
        "设 标志 为 真；设 值 为 空",
    ),
    (
        "L2003",
        "默认参数只支持标量字面量和「空」：段落 f(列表 = []) 会被拒绝",
        "段落 f(a, b = 0) 合法",
    ),
    (
        "L3001",
        "列表索引越界: 5, 长度: 3",
        "列表获取([10,20], 1) 正常",
    ),
    (
        "L3002",
        "字典下标赋值必须用「设 … 为 …」：己.表[k] = v 不生效",
        "设 列表[0] 为 9 合法",
    ),
    (
        "L3003",
        "设 字典[键] 为 空 不删键，之后 字典包含键(键) 仍为真",
        '字典删除(甲, "旧键") 正常',
    ),
    (
        "L3004",
        "闭包内对外层数值变量赋值不生效（L-098）",
        '设 全局状态 为 {"计数": 0} 与字典原地修改正常',
    ),
    (
        "L4001",
        "该函数来自『字符串处理』模块（不是未定义变量），"
        "请在文件顶部加一行：从 字符串处理 导入 子串位置",
        "未定义的名称: 甲，请先定义变量",
    ),
    (
        "L4002",
        "没有 math 模块，叫「数学」：从 math 导入 sqrt 失败",
        "从 数学 导入 平方根 正常",
    ),
    (
        "L5001",
        "原生后端暂不支持语句类型「YieldStmt」（源码行 12）："
        "原生后端暂不支持，请用转译后端（python -m cli.light_unified run）",
        "转译后端编译成功，rc=0",
    ),
    (
        "L5002",
        "类系统在 SRC 后端不可用，需切换 LLVM 后端",
        "类 动物： 段落 初始化 接收 名字： 正常",
    ),
    (
        "L5003",
        "原生腿列表/字典作为函数参数跨段变异不生效（值拷贝）",
        "转译腿是 Python 引用语义，追加后调用方可见",
    ),
]


# ---------------------------------------------------------------------------
# 码表结构与数量
# ---------------------------------------------------------------------------
def test_registry_has_at_least_14_rules():
    assert len(RULES) >= 14
    assert len(all_codes()) == len(RULES)


def test_cases_cover_every_rule_exactly_once():
    """CASES 与码表必须对拍：新增码忘了补测试 / 测试写了不存在的码，都会红。"""
    case_codes = [code for code, _, _ in CASES]
    assert len(case_codes) == len(set(case_codes)), "CASES 里有重复码"
    assert set(case_codes) == set(all_codes())
    assert len(CASES) == len(RULES)


def test_code_format_and_segment_consistency():
    for rule in RULES:
        assert CODE_PATTERN.fullmatch(rule.code), rule.code
        assert rule.code[:2] in CODE_SEGMENTS
        assert rule.stage
        assert rule.title
        assert rule.hint
        assert 0 < len(rule.fixes) <= MAX_FIXES
        assert rule.severity in SEVERITIES
        assert rule.pattern
    # 码段分布与 docs/错误码规范.md §1.1 的统计对拍
    dist = {seg: 0 for seg in CODE_SEGMENTS}
    for rule in RULES:
        dist[rule.code[:2]] += 1
    assert dist == {"L1": 7, "L2": 3, "L3": 4, "L4": 2, "L5": 3}


def test_every_rule_has_real_source():
    """禁止为凑数编造：每条都要有可复核的 docs/ 或 src/ 出处。"""
    for rule in RULES:
        assert rule.source, f"{rule.code} 缺 source"
        assert "docs/" in rule.source or "src/" in rule.source or "antlrparser/" in rule.source, rule.source


def test_get_and_all_codes():
    for code in all_codes():
        assert get(code) is not None
        assert get(code).code == code
    assert get("L9999") is None
    assert get("l2001") is None  # 大小写敏感


# ---------------------------------------------------------------------------
# 重复码判据：既要真实码表无重复，也要验证检测函数「有牙」
# ---------------------------------------------------------------------------
def test_no_duplicate_codes_in_registry():
    codes = [r.code for r in RULES]
    assert len(codes) == len(set(codes)), "同一错误码出现在两条规则里"
    assert duplicate_codes(RULES) == []


def test_duplicate_code_detection_has_teeth():
    """把一条规则的码改成另一条已用的码，检测器必须报出重复。

    没有这条反向验证，「无重复」就只是对当前数据的一次弱断言。
    """
    injected = (RULES[0], replace(RULES[1], code=RULES[0].code))
    assert duplicate_codes(injected) == [RULES[0].code]
    # 三条规则共用同一个码，也只报一次
    triple = (RULES[0], replace(RULES[1], code=RULES[0].code),
              replace(RULES[2], code=RULES[0].code))
    assert duplicate_codes(triple) == [RULES[0].code]


def test_rule_rejects_duplicate_grade_metadata():
    """Rule 自身的构造校验：非法码 / 无出处 / 过宽严重度都必须拒绝。"""
    base = RULES[0]
    with pytest.raises(ValueError):
        replace(base, code="L9001")
    with pytest.raises(ValueError):
        replace(base, code="L9999")
    with pytest.raises(ValueError):
        replace(base, source="")
    with pytest.raises(ValueError):
        replace(base, severity="fatal")
    with pytest.raises(ValueError):
        replace(base, pattern="(")
    with pytest.raises(ValueError):
        replace(base, fixes=("1", "2", "3", "4"))


# ---------------------------------------------------------------------------
# 每条规则：正例命中、反例不命中
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("code,positive,negative", CASES, ids=[c[0] for c in CASES])
def test_rule_positive_and_negative(code, positive, negative):
    rule = get(code)
    assert rule is not None

    diag = explain(positive)
    assert diag is not None, f"{code} 正例未命中：{positive}"
    assert diag.code == code, f"{code} 正例被别的规则抢先命中：{diag.code}"
    assert diag.severity == rule.severity
    assert diag.stage == rule.stage
    assert diag.message == positive  # 原始报错文本原样保留
    assert diag.hint == rule.hint
    assert list(diag.fixes) == list(rule.fixes)
    assert list(diag.candidates) == list(rule.candidates)

    # 带 stage 过滤同样能命中（stage 与规则一致时）
    assert explain(positive, stage=rule.stage).code == code

    # 反例：全局不命中，且不带 stage 过滤也不命中
    assert explain(negative) is None, f"{code} 反例被误命中：{negative}"
    assert explain(negative, stage=rule.stage) is None


def test_explain_miss_returns_none_without_fabricating_code():
    for message in (
        "完全无关的报错文本",
        "编译成功",
        "变量拼写可能有误",
        "",
    ):
        assert explain(message) is None
    assert explain(None) is None
    assert explain(123) is None
    assert explain([]) is None


def test_explain_stage_filter_is_a_real_filter():
    positive = dict((c, (p, n)) for c, p, n in CASES)["L2001"][0]
    assert explain(positive).code == "L2001"
    assert explain(positive, stage="类型").code == "L2001"
    assert explain(positive, stage="语法") is None  # 不允许跨阶段抢匹配
    assert explain(positive, stage="不存在的阶段") is None


def test_explain_does_not_fabricate_position_or_precision():
    diag = explain("参数数量错误: 段落「加法」期望 2 个参数，实际传入 3 个")
    assert diag.line == 0
    assert diag.column == 0
    assert diag.to_dict()["line"] == 0
    assert diag.provisional is True  # 文本推断态，不是精确归因


def test_not_equal_operator_is_not_reported_as_bang_misuse():
    """L1003 的 `!` 规则不能把合法的 `!=` / `>=` 误报成逻辑运算符误用。"""
    assert explain("设 不等 为 a != b") is None
    assert explain("如果 甲 >= 乙： 正常") is None
    assert explain("不支持的运算符 '!'，请用「非」").code == "L1003"


def test_warning_rules_are_not_upgraded_to_error():
    """禁止把 warning 升级成 error：文档里是提示/合法语法/静默差异的一律 warning。"""
    warning_codes = {
        "L1005", "L1007", "L3002", "L3003", "L3004", "L5002", "L5003",
    }
    for code, positive, _ in CASES:
        rule = get(code)
        diag = explain(positive)
        if code in warning_codes:
            assert rule.severity == "warning", code
            assert diag.severity == "warning", code
        else:
            assert rule.severity == "error", code
            assert diag.severity == "error", code


def test_real_error_messages_from_source_are_explained():
    """4 条仓库里的真实报错模板：命中码与 fixes 都要对得上（summary 引用）。"""
    expectations = [
        (
            "参数数量错误: 段落「加法」期望 2 个参数，实际传入 3 个",
            "L2001",
        ),
        (
            "该函数来自『字符串处理』模块（不是未定义变量），"
            "请在文件顶部加一行：从 字符串处理 导入 子串位置",
            "L4001",
        ),
        (
            "原生后端暂不支持语句类型「YieldStmt」（源码行 12）："
            "原生后端暂不支持，请用转译后端（python -m cli.light_unified run）",
            "L5001",
        ),
        (
            "「空」是保留字（值类型），不可作标识符（变量名/下标名）。"
            "请改用其他名称。常用保留字清单：真、假、空。",
            "L1006",
        ),
    ]
    for message, code in expectations:
        diag = explain(message)
        assert diag is not None and diag.code == code
        assert len(diag.fixes) >= 1 and all(isinstance(f, str) for f in diag.fixes)
        assert len(diag.fixes) <= MAX_FIXES
        assert diag.candidates


# ---------------------------------------------------------------------------
# Diagnostic 数据模型
# ---------------------------------------------------------------------------
def _full_diagnostic(**overrides):
    data = dict(
        code="L2001",
        severity="error",
        stage="类型",
        line=7,
        column=13,
        message="参数数量错误: 段落「加法」期望 2 个参数，实际传入 3 个",
        hint="调用段落时传入的实参个数必须和段落定义的参数个数一致。",
        fixes=["补齐参数", "检查逗号分隔"],
        candidates=["设 和 为 加法(1, 2)"],
        provisional=True,
        docs="docs/错误码规范.md",
    )
    data.update(overrides)
    return Diagnostic(**data)


def test_to_dict_field_order_is_stable():
    diag = _full_diagnostic()
    assert tuple(diag.to_dict()) == DIAGNOSTIC_FIELDS
    assert list(json.loads(diag.to_json())) == list(DIAGNOSTIC_FIELDS)
    # 两次序列化结果逐字相同，可直接 diff
    assert diag.to_json() == diag.to_json()


def test_to_dict_keeps_zero_line():
    diag = _full_diagnostic(line=0, column=0)
    payload = json.loads(diag.to_json(ensure_ascii=False))
    assert payload["line"] == 0
    assert payload["column"] == 0
    assert "1" != str(payload["line"])


def test_from_dict_roundtrip():
    diag = _full_diagnostic()
    assert Diagnostic.from_dict(diag.to_dict()) == diag
    # 经过 JSON 往返也一样
    assert Diagnostic.from_dict(json.loads(diag.to_json(ensure_ascii=False))) == diag


def test_from_dict_roundtrip_for_unknown_line():
    diag = _full_diagnostic(line=0, column=0, fixes=[], candidates=[], provisional=False)
    assert Diagnostic.from_dict(diag.to_dict()) == diag
    assert Diagnostic.from_dict(diag.to_dict()).line == 0


def test_from_dict_ignores_unknown_fields():
    payload = _full_diagnostic().to_dict()
    payload["future_field"] = "新版本才有"
    restored = Diagnostic.from_dict(payload)
    assert restored.code == "L2001"
    assert not hasattr(restored, "future_field")


def test_to_dict_returns_copies():
    diag = _full_diagnostic()
    payload = diag.to_dict()
    payload["fixes"].append("外部塞进来的")
    assert "外部塞进来的" not in diag.fixes


def test_diagnostic_validation():
    with pytest.raises(ValueError):
        _full_diagnostic(severity="fatal")
    with pytest.raises(ValueError):
        _full_diagnostic(fixes=["1", "2", "3", "4"])
    with pytest.raises(ValueError):
        _full_diagnostic(line=-1)
    with pytest.raises(ValueError):
        _full_diagnostic(column=-1)
    with pytest.raises(ValueError):
        _full_diagnostic(line=True)
    with pytest.raises(TypeError):
        _full_diagnostic(fixes=[1, 2])
    with pytest.raises(TypeError):
        Diagnostic.from_dict("not a dict")


# ---------------------------------------------------------------------------
# 兼容层：文本输出逐字不变
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "diag",
    [
        _full_diagnostic(),
        _full_diagnostic(line=0, column=0),
        _full_diagnostic(fixes=[], candidates=[]),
        _full_diagnostic(severity="warning", stage="词法", line=3, column=0),
    ],
    ids=["with-position", "unknown-position", "no-fixes", "warning"],
)
def test_to_legacy_entry_format_matches_direct_error_entry(diag):
    legacy = to_legacy_entry(diag)
    direct = ErrorEntry(
        stage=diag.stage,
        message=diag.message,
        line=diag.line,
        column=diag.column,
        fix_suggestions=list(diag.fixes),
    )
    assert isinstance(legacy, ErrorEntry)
    assert legacy.format() == direct.format()
    assert legacy.stage == diag.stage
    assert legacy.message == diag.message
    assert legacy.fix_suggestions == list(diag.fixes)
    assert legacy.source_line == ""


def test_to_legacy_entry_preserves_original_message_and_does_not_inject_code():
    """兼容层不许把错误码拼进 message，否则旧文本输出会变。"""
    diag = explain("参数数量错误: 段落「加法」期望 2 个参数，实际传入 3 个")
    text = to_legacy_entry(diag).format()
    assert diag.code not in text
    assert "│ 原因: " + diag.message in text
    assert "│ 位置:" not in text  # line=0 时不打印位置行


def test_to_legacy_entry_of_all_explain_results():
    """每条规则产出的诊断都能无损降级成旧 ErrorEntry。"""
    for code, positive, _ in CASES:
        diag = explain(positive)
        assert diag is not None
        legacy = to_legacy_entry(diag)
        direct = ErrorEntry(
            stage=diag.stage,
            message=diag.message,
            line=diag.line,
            column=diag.column,
            fix_suggestions=list(diag.fixes),
        )
        assert legacy.format() == direct.format(), code


# ===========================================================================
# T-0378（R222-B 线）：统一诊断码注册表
# ---------------------------------------------------------------------------
# 判据（对应任务卡「完成标准」）：
# * 码唯一、区间合法（L[1-5]NNN，无 L9xxx 之类未定区间）；
# * 每条码都有 message（中文一句话）与 hint（最小修复建议）；
# * format_diagnostic 输出可 json.dumps；
# * 未注册码抛 KeyError（diagnostic / format_diagnostic 双入口）。
# 口径（用户 2026-11-17 拍板）：T-0316 的 19 条码收编不重排（legacy=True）；
# lint 类新码从 L5004 起避让 L5001-L5003；get() 保持 docs 规范 v1 的
# 「未注册返回 None」语义，严格查询由 diagnostic() 承担。
# ===========================================================================
from src.diagnostics import (  # noqa: E402
    ANCHORS,
    DIAG_SEGMENTS,
    DIAGNOSTICS,
    DiagnosticSpec,
    LEGACY_CODE_COUNT,
    LINT_RULE_MAP,
    all_diagnostic_codes,
    diagnostic,
    format_diagnostic,
    lint_rule_to_code,
)
from src.linter.light_linter import RULES as LINTER_RULES  # noqa: E402

_EXPECTED_LINT_COUNT = len(LINTER_RULES)
_EXPECTED_TOTAL = LEGACY_CODE_COUNT + _EXPECTED_LINT_COUNT


def test_unified_registry_covers_legacy_and_lint():
    """统一码表 = T-0316 收编 19 条 + lint 桥接（linter 全部规则）。"""
    codes = all_diagnostic_codes()
    assert len(codes) == len(set(codes)), "统一码表出现重复码"
    assert len(codes) == _EXPECTED_TOTAL
    assert set(codes) == set(all_codes()) | set(LINT_RULE_MAP.values())
    assert DIAGNOSTICS == {code: diagnostic(code) for code in codes}


def test_legacy_specs_keep_original_values_and_severity():
    """收编不重排：码值 / severity / hint / message 与 RULES 逐条一致。"""
    for rule in RULES:
        spec = diagnostic(rule.code)
        assert spec.legacy is True
        assert spec.code == rule.code
        assert spec.severity == rule.severity
        assert spec.hint == rule.hint
        assert spec.message == rule.title
    assert len(RULES) == LEGACY_CODE_COUNT == 19


def test_lint_bridge_maps_all_linter_rules():
    """「旧码 → 新码」映射必须覆盖 linter 全部规则，且 severity 对拍不漂移。"""
    assert set(LINT_RULE_MAP) == set(LINTER_RULES), "linter 规则与映射表不对拍"
    for rule_id, code in LINT_RULE_MAP.items():
        spec = diagnostic(code)
        assert spec.legacy is False
        assert spec.anchor == "linter"
        assert spec.severity == LINTER_RULES[rule_id]["severity"], rule_id
    assert len(set(LINT_RULE_MAP.values())) == len(LINT_RULE_MAP), "新码值有撞号"


def test_lint_codes_avoid_legacy_range_and_start_at_l5004():
    """lint 码从 L5004 起、避让 L5001-L5003；区间连续无跳号。"""
    lint_codes = {code for code in all_diagnostic_codes() if not diagnostic(code).legacy}
    expected = {f"L{5004 + i}" for i in range(_EXPECTED_LINT_COUNT)}
    assert lint_codes == expected
    assert not (lint_codes & set(all_codes())), "lint 新码与 T-0316 收编码撞号"


def test_every_spec_has_message_hint_and_valid_anchor():
    """任务卡硬判据：每条码都有 message 与 hint；anchor/severity 合法。"""
    for code in all_diagnostic_codes():
        spec = diagnostic(code)
        assert isinstance(spec, DiagnosticSpec)
        assert spec.message.strip(), code
        assert spec.hint.strip(), code
        assert spec.severity in SEVERITIES, code
        assert spec.anchor in ANCHORS, code


def test_all_codes_in_defined_segments_no_undefined_range():
    """区间合法：L[1-5]NNN、段位在 DIAG_SEGMENTS 内，无 L6xx/L9xxx 未定区间。"""
    for code in all_diagnostic_codes():
        assert CODE_PATTERN.fullmatch(code), code
        assert code[:2] in DIAG_SEGMENTS, code
        assert code[:2] in {"L1", "L2", "L3", "L4", "L5"}, code


def test_diagnostic_strict_lookup_raises_key_error_for_unknown():
    """未注册的 code 必须抛 KeyError（避免下游写出假码）。"""
    for code in all_diagnostic_codes():
        spec = diagnostic(code)
        assert spec.code == code
    with pytest.raises(KeyError):
        diagnostic("L9999")
    with pytest.raises(KeyError):
        diagnostic("l2001")  # 大小写敏感
    with pytest.raises(KeyError):
        diagnostic(123)
    with pytest.raises(KeyError):
        diagnostic(None)


def test_lint_rule_to_code_roundtrip():
    """旧规则码 → 新码逐条可查；未登记旧码抛 KeyError。"""
    for rule_id, code in LINT_RULE_MAP.items():
        assert lint_rule_to_code(rule_id) == code
    with pytest.raises(KeyError):
        lint_rule_to_code("E999")


def test_format_diagnostic_output_shape_and_stable_order():
    payload = format_diagnostic("L1001", "demo.light", 3, 5)
    assert list(payload) == [
        "code", "severity", "message", "hint", "anchor", "file", "line", "column",
    ]
    assert payload["code"] == "L1001"
    assert payload["file"] == "demo.light"
    assert payload["line"] == 3
    assert payload["column"] == 5
    assert payload["anchor"] == "parser"
    # 幂等：同样入参两次格式化逐字相等，可直接 diff
    assert payload == format_diagnostic("L1001", "demo.light", 3, 5)


def test_format_diagnostic_is_json_serializable_for_all_codes():
    """任务卡硬判据：输出可 json.dumps。"""
    for code in all_diagnostic_codes():
        payload = format_diagnostic(code, "x.light", 1, 1)
        text = json.dumps(payload, ensure_ascii=False)
        restored = json.loads(text)
        assert restored == payload
    # extra 是 dict 时也必须可序列化
    payload = format_diagnostic("L2001", "x.light", 2, 7, extra={"实际传入": 3})
    assert json.loads(json.dumps(payload, ensure_ascii=False)) == payload


def test_format_diagnostic_extra_merges_without_overriding_core_keys():
    payload = format_diagnostic("L1001", "a.light", 1, 1, extra={"期望": "段落"})
    assert payload["期望"] == "段落"
    poisoned = format_diagnostic("L1001", "a.light", 1, 1, extra={"file": "别处.light"})
    assert poisoned["file"] == "a.light"  # 核心键不被 extra 覆盖
    assert "extra" not in format_diagnostic("L1001", "a.light", 1, 1)


def test_format_diagnostic_validates_arguments():
    with pytest.raises(ValueError):
        format_diagnostic("L1001", "", 1, 1)  # file 非空
    with pytest.raises(ValueError):
        format_diagnostic("L1001", "a.light", -1, 1)
    with pytest.raises(ValueError):
        format_diagnostic("L1001", "a.light", 1, -1)
    with pytest.raises(ValueError):
        format_diagnostic("L1001", "a.light", True, 1)  # bool 冒充 int
    with pytest.raises(ValueError):
        format_diagnostic("L1001", "a.light", 1.5, 1)
    with pytest.raises(TypeError):
        format_diagnostic("L1001", "a.light", 1, 1, extra="字符串")


def test_format_diagnostic_unknown_code_raises_key_error():
    with pytest.raises(KeyError):
        format_diagnostic("L9999", "a.light", 1, 1)
    with pytest.raises(KeyError):
        format_diagnostic("L9001", "a.light", 1, 1)
