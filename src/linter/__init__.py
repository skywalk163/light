# -*- coding: utf-8 -*-
"""
光明代码检查器 (Light Linter)

提供光明代码的静态分析功能，包括语法检查、风格检查、废弃模式检测等。
"""

from .light_linter import LightLinter, LintResult, LintRule, Severity, RULES

__version__ = '1.1.0'