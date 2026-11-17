# -*- coding: utf-8 -*-
"""光明编译器结构化诊断包（T-0316 码表 + T-0378 统一注册表）。

纯标准库，两层分工：

T-0316（向下兼容承诺不变，docs/错误码规范.md v1）
    ``Diagnostic`` 数据模型 + 19 条高频错误码表（``Rule`` / ``RULES``）+
    ``explain()``（报错文本 → 码的正则归因）+ ``to_legacy_entry()`` 兼容层。

T-0378（R222-B 线）::
    from src.diagnostics import diagnostic, format_diagnostic

    spec = diagnostic("L1001")                 # 未注册抛 KeyError
    payload = format_diagnostic("L1001", "demo.light", 3, 5)
    print(json.dumps(payload, ensure_ascii=False))  # 错误码+位置+最小修复

    统一码表 ``DIAGNOSTICS`` = T-0316 收编 19 条（legacy=True，码值与语义
    不变）+ lint 桥接 33 条（``L5004``–``L5036``，见 ``lint_bridge``，
    E001/W001/E016/W016 等旧规则码的 L5xxx 身份）。

边界：本包不修改 ``cli/light.py``、``src/enhanced_errors.py``、
``src/errors.py``、``src/linter/``；错误码的 CLI 接线由 T-0382 承担。
"""

from .model import (
    ANCHORS,
    DIAGNOSTIC_FIELDS,
    MAX_FIXES,
    SEVERITIES,
    Diagnostic,
    DiagnosticSpec,
)
from .registry import (
    CODE_PATTERN,
    CODE_SEGMENTS,
    RULES,
    Rule,
    all_codes,
    all_diagnostic_codes,
    diagnostic,
    duplicate_codes,
    explain,
    format_diagnostic,
    get,
    to_legacy_entry,
    DIAGNOSTICS,
    DIAG_SEGMENTS,
    LEGACY_CODE_COUNT,
)
from .lint_bridge import LINT_RULE_MAP, lint_rule_to_code

__all__ = [
    # T-0316（原样保留）
    "Diagnostic",
    "DIAGNOSTIC_FIELDS",
    "SEVERITIES",
    "MAX_FIXES",
    "Rule",
    "RULES",
    "CODE_SEGMENTS",
    "CODE_PATTERN",
    "explain",
    "get",
    "all_codes",
    "duplicate_codes",
    "to_legacy_entry",
    # T-0378（R222-B 线统一注册表）
    "DiagnosticSpec",
    "ANCHORS",
    "DIAGNOSTICS",
    "DIAG_SEGMENTS",
    "LEGACY_CODE_COUNT",
    "diagnostic",
    "all_diagnostic_codes",
    "format_diagnostic",
    # lint 桥接
    "LINT_RULE_MAP",
    "lint_rule_to_code",
]
