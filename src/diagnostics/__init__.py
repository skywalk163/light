# -*- coding: utf-8 -*-
"""光明编译器结构化诊断包（T-0316）。

纯标准库：``Diagnostic`` 数据模型 + 高频错误码表 + ``explain()`` + 兼容层。

典型用法::

    from src.diagnostics import explain, get, to_legacy_entry

    diag = explain("参数数量错误: 段落「加法」期望 2 个参数，实际传入 3 个")
    if diag is not None:
        print(diag.code, diag.fixes)          # L2001 [...]
        print(diag.to_json())                 # 字段顺序稳定，可直接 diff
        print(to_legacy_entry(diag).format()) # 与旧 ErrorEntry 文本逐字一致

边界：本包不修改 ``cli/light.py``、``src/enhanced_errors.py``、
``src/errors.py``；错误码的渲染与 JSON 输出由 T-0317 / T-0318 接入。
"""

from .model import DIAGNOSTIC_FIELDS, MAX_FIXES, SEVERITIES, Diagnostic
from .registry import (
    CODE_PATTERN,
    CODE_SEGMENTS,
    RULES,
    Rule,
    all_codes,
    duplicate_codes,
    explain,
    get,
    to_legacy_entry,
)

__all__ = [
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
]
