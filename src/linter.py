# -*- coding: utf-8 -*-
"""
光明（Light）代码检查工具（Linter）

功能：
  - 语法错误检查（基于解析器）
  - 代码风格检查（L0/L1/L2 风格一致性）
  - 未使用变量检查
  - v3.3 废弃模式警告
  - 支持规则配置（--enable/--disable）
  - 支持 JSON 输出

用法：
  light lint file.light           # 检查单个文件
  light lint .                   # 检查当前目录
  light lint --json file.light    # JSON 输出
  light lint --fix file.light     # 自动修复简单问题
"""

import os
import sys
import json
import re
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# 规则定义
# =============================================================================

class Severity(Enum):
    ERROR = 1
    WARNING = 2
    INFO = 3
    HINT = 4


@dataclass
class LintRule:
    """检查规则"""
    code: str           # 规则代码，如 'L001'
    name: str           # 规则名称
    description: str    # 规则描述
    severity: Severity  # 默认严重级别
    auto_fix: bool = False  # 是否支持自动修复


# 所有检查规则
RULES = {
    # 语法类 (S)
    'S001': LintRule('S001', '语法错误', '代码存在语法错误，无法通过解析器', Severity.ERROR),
    'S002': LintRule('S002', '缺少冒号', '块关键字后缺少冒号（：或:）', Severity.ERROR),
    'S003': LintRule('S003', '缺少句号', '语句结尾缺少句号（。）', Severity.WARNING),

    # 风格类 (L - Layer)
    'L001': LintRule('L001', '混合风格', '同一文件中混用 L0 单字和 L1 双字关键字', Severity.WARNING),
    'L002': LintRule('L002', 'L1 风格推荐', '在 L1（白话体）文件中使用了 L0 单字关键字', Severity.INFO),
    'L003': LintRule('L003', 'L0 风格推荐', '在 L2（文言体）文件中推荐使用 L0 单字关键字', Severity.INFO),

    # 废弃类 (D)
    'D001': LintRule('D001', '废弃接收语法', '「接收」关键字已废弃，请使用括号参数语法', Severity.WARNING),
    'D002': LintRule('D002', '废弃嵌入关键字', '「嵌入」关键字已废弃，请使用「引」', Severity.WARNING),
    'D003': LintRule('D003', '废弃句号', '使用中文句号（。）作为语句分隔符，建议使用英文句号（.）', Severity.INFO),

    # 代码质量类 (Q)
    'Q001': LintRule('Q001', '未使用变量', '定义的变量从未被使用', Severity.WARNING),
    'Q002': LintRule('Q002', '未使用导入', '导入的模块从未被使用', Severity.WARNING),
    'Q003': LintRule('Q003', '空段落', '段落（函数）体为空', Severity.WARNING),
    'Q004': LintRule('Q004', '过长行', '行长度超过 120 字符', Severity.INFO),
    'Q005': LintRule('Q005', '尾随空白', '行尾存在空白字符', Severity.INFO, auto_fix=True),
    'Q006': LintRule('Q006', '多余空行', '连续空行超过 2 行', Severity.INFO),
    'Q007': LintRule('Q007', '文件末尾缺少换行', '文件末尾缺少换行符', Severity.INFO, auto_fix=True),
}


@dataclass
class LintIssue:
    """检查结果"""
    rule: LintRule
    line: int
    col: int
    message: str
    severity: Severity
    source: str = ''


# =============================================================================
# L0/L1/L2 关键字映射
# =============================================================================

# L0 单字关键字（主形式）
L0_KEYWORDS = frozenset({
    '若', '否', '当', '遍', '跳', '过', '返',
    '设', '段', '类', '承', '接', '配',
    '试', '捕', '抛', '终',
    '自', '之', '并', '从', '是',
    '且', '或', '非', '真', '假', '空',
    '导', '出',
})

# L1 双字关键字（白话体别名）
L1_KEYWORDS = frozenset({
    '如果', '否则', '否则若', '遍历', '返回', '跳出', '跳过',
    '定义', '段落', '继承', '接口', '实现',
    '尝试', '捕获', '抛出', '最终',
    '导入', '导出', '匹配',
})

# L0 ↔ L1 映射
L0_TO_L1 = {
    '若': '如果', '否': '否则', '遍': '遍历', '跳': '跳出', '过': '跳过',
    '返': '返回', '设': '定义', '段': '段落', '承': '继承', '接': '接口',
    '试': '尝试', '捕': '捕获', '抛': '抛出', '终': '最终',
    '配': '匹配', '导': '导入', '出': '导出',
}

L1_TO_L0 = {v: k for k, v in L0_TO_L1.items()}


# =============================================================================
# 检查器
# =============================================================================

class LightLinter:
    """光明代码检查器"""

    def __init__(self, rules: Optional[Set[str]] = None, disabled_rules: Optional[Set[str]] = None):
        """
        初始化检查器

        Args:
            rules: 启用的规则代码集合（None 表示全部启用）
            disabled_rules: 禁用的规则代码集合
        """
        self.enabled_rules = rules  # None = all enabled
        self.disabled_rules = disabled_rules or set()
        self.issues: List[LintIssue] = []
        self._source_lines: List[str] = []
        self._source: str = ''

    def _is_enabled(self, rule_code: str) -> bool:
        """检查规则是否启用"""
        if rule_code in self.disabled_rules:
            return False
        if self.enabled_rules is not None:
            return rule_code in self.enabled_rules
        return True

    def _add_issue(self, rule_code: str, line: int, col: int, message: str, source: str = ''):
        """添加检查结果"""
        if not self._is_enabled(rule_code):
            return
        rule = RULES.get(rule_code)
        if rule is None:
            return
        self.issues.append(LintIssue(
            rule=rule,
            line=line,
            col=col,
            message=message,
            severity=rule.severity,
            source=source
        ))

    def check(self, source: str, filepath: str = '') -> List[LintIssue]:
        """执行所有检查"""
        self.issues = []
        self._source = source
        self._source_lines = source.split('\n')

        self._check_syntax(source)
        self._check_style()
        self._check_deprecated()
        self._check_quality()

        return self.issues

    def _check_syntax(self, source: str):
        """检查语法错误"""
        try:
            from light_parser_v3 import LightParser
            parser = LightParser()
            parser.parse(source)
        except Exception as e:
            line = getattr(e, 'line', 1)
            col = getattr(e, 'col', 0)
            msg = getattr(e, 'message', str(e))
            self._add_issue('S001', line, col, msg)

        # 检查块关键字后是否有冒号
        block_keywords = {'如果', '若', '遍历', '遍', '当', '段落', '段', '类', '接口', '接',
                         '尝试', '试', '捕获', '捕', '匹配', '配', '否则', '否', '否则若', '否若', '最终', '终'}
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            for kw in sorted(block_keywords, key=len, reverse=True):
                if stripped.startswith(kw):
                    # 检查关键字后是否有冒号
                    after_kw = stripped[len(kw):].strip()
                    # 如果后面没有内容，或者有内容但不以冒号开始，且不是注释
                    if after_kw and not after_kw.startswith('：') and not after_kw.startswith(':'):
                        # 检查是否在行尾有冒号
                        if not stripped.rstrip().endswith('：') and not stripped.rstrip().endswith(':'):
                            self._add_issue('S002', i, len(kw) + 1, f"关键字「{kw}」后缺少冒号", source=stripped)
                    break

    def _check_style(self):
        """检查代码风格"""
        has_l0 = False
        has_l1 = False

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            # 检测 L0 关键字使用
            for kw in L0_KEYWORDS:
                if _is_keyword_usage(stripped, kw):
                    has_l0 = True
                    break

            # 检测 L1 关键字使用
            for kw in L1_KEYWORDS:
                if _is_keyword_usage(stripped, kw):
                    has_l1 = True
                    break

        # 混合风格检查
        if has_l0 and has_l1:
            self._add_issue('L001', 1, 0,
                          '文件中同时使用了 L0 单字关键字和 L1 双字关键字，建议统一风格',
                          source='mixed')

        # L1 风格推荐：如果文件以 L1 为主，检查 L0 单字使用
        if has_l1:
            for i, line in enumerate(self._source_lines, 1):
                for kw in L0_KEYWORDS:
                    if kw in L0_TO_L1 and _is_keyword_usage(line, kw):
                        self._add_issue('L002', i, line.find(kw) + 1,
                                      f'L1 风格中使用了 L0 单字「{kw}」，建议使用「{L0_TO_L1[kw]}」',
                                      source=line.strip())

        # L0 风格推荐：如果文件以 L0 为主，检查 L1 双字使用
        if has_l0 and not has_l1:
            for i, line in enumerate(self._source_lines, 1):
                for kw in L1_KEYWORDS:
                    if kw in L1_TO_L0 and _is_keyword_usage(line, kw):
                        self._add_issue('L003', i, line.find(kw) + 1,
                                      f'L0 风格中使用了 L1 双字「{kw}」，建议使用 L0 单字「{L1_TO_L0[kw]}」',
                                      source=line.strip())

    def _check_deprecated(self):
        """检查废弃模式"""
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 检查「接收」废弃语法
            if '接收' in stripped:
                self._add_issue('D001', i, stripped.find('接收') + 1,
                              '「接收」关键字已废弃，请使用括号参数语法，如「段 函数名(参数)：」',
                              source=stripped)

            # 检查「嵌入」废弃关键字
            if re.search(r'\b嵌入\b', stripped) and '嵌入' not in [kw for kw in
                    ('嵌入', '嵌入块') if kw in stripped] or '嵌入' in stripped:
                # 确保不是「嵌入块」的一部分
                if '嵌入' in stripped and '结束嵌入' not in stripped:
                    pos = stripped.find('嵌入')
                    # 检查是否作为独立关键字
                    if pos == 0 or stripped[pos-1] in ' \t' or not stripped[pos-1].isalnum():
                        self._add_issue('D002', i, pos + 1,
                                      '「嵌入」关键字已废弃，请使用「引」',
                                      source=stripped)

            # 检查中文句号
            if '。' in stripped and not stripped.rstrip().endswith('。'):
                self._add_issue('D003', i, stripped.find('。') + 1,
                              '使用了中文句号（。），建议使用英文句号（.）',
                              source=stripped)

    def _check_quality(self):
        """检查代码质量"""
        # 收集变量定义和使用
        defined_vars: Set[str] = set()
        used_vars: Set[str] = set()
        imported_modules: Dict[str, int] = {}  # module -> line
        used_imports: Set[str] = set()

        # 段落（函数）列表
        paragraphs: List[Tuple[int, str, int, int]] = []  # (line, name, body_start, body_end)

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 检查变量定义
            var_match = re.match(r'(?:设|定义)\s+(\S+)', stripped)
            if var_match:
                var_name = var_match.group(1)
                defined_vars.add(var_name)

            # 检查变量使用
            for var in defined_vars:
                if var in stripped:
                    # 排除定义行本身
                    if not re.match(r'(?:设|定义)\s+' + re.escape(var), stripped):
                        used_vars.add(var)

            # 检查导入
            import_match = re.match(r'(?:导入|导)\s+(\S+)', stripped)
            if import_match:
                mod_name = import_match.group(1)
                imported_modules[mod_name] = i

            # 检查导入使用
            for mod in imported_modules:
                if mod in stripped and not re.match(r'(?:导入|导)\s+' + re.escape(mod), stripped):
                    used_imports.add(mod)

            # 检查段落定义
            func_match = re.match(r'(?:段落|段)\s+(\S+)\s*(?:\(|：|:)', stripped)
            if func_match:
                para_name = func_match.group(1)
                paragraphs.append((i, para_name, i + 1, len(self._source_lines)))

            # 检查行长度
            if len(line.rstrip()) > 120:
                self._add_issue('Q004', i, 120, f'行长度 {len(line.rstrip())} 超过 120 字符限制',
                              source=line.rstrip()[:60] + '...')

            # 检查尾随空白
            if line.rstrip() != line.rstrip('\n').rstrip():
                self._add_issue('Q005', i, len(line.rstrip()), '行尾存在空白字符',
                              source=line.rstrip()[:60])

        # 未使用变量
        for var in sorted(defined_vars - used_vars):
            for i, line in enumerate(self._source_lines, 1):
                if re.match(r'(?:设|定义)\s+' + re.escape(var), line.strip()):
                    self._add_issue('Q001', i, line.find(var) + 1, f'变量「{var}」定义但从未使用',
                                  source=line.strip())
                    break

        # 未使用导入
        for mod in sorted(set(imported_modules.keys()) - used_imports):
            self._add_issue('Q002', imported_modules[mod], 0, f'模块「{mod}」导入但从未使用')

        # 检查空段落
        for line_no, name, start, end in paragraphs:
            body_lines = [l for l in self._source_lines[start:end]
                         if l.strip() and not l.strip().startswith('#')]
            if len(body_lines) <= 1:
                self._add_issue('Q003', line_no, 0, f'段落「{name}」体为空')

        # 检查多余空行
        blank_count = 0
        for i, line in enumerate(self._source_lines, 1):
            if line.strip() == '':
                blank_count += 1
            else:
                if blank_count > 2:
                    self._add_issue('Q006', i - blank_count, 0, f'连续 {blank_count} 行空行')
                blank_count = 0

        # 检查文件末尾换行
        if self._source and not self._source.endswith('\n'):
            self._add_issue('Q007', len(self._source_lines), 0, '文件末尾缺少换行符')


def _is_keyword_usage(line: str, keyword: str) -> bool:
    """检查关键字是否在行中作为独立关键字使用"""
    stripped = line.strip()
    # 关键字位于行首
    if stripped.startswith(keyword):
        rest = stripped[len(keyword):]
        if not rest or rest[0] in ' \t：:（(' or not rest[0].isalnum():
            return True
    # 关键字在行中作为独立词
    idx = stripped.find(keyword)
    if idx > 0:
        before = stripped[idx - 1]
        after = stripped[idx + len(keyword):idx + len(keyword) + 1] if idx + len(keyword) < len(stripped) else ''
        if before in ' \t' and (not after or after in ' \t：:。.'):
            return True
    return False


# =============================================================================
# 自动修复
# =============================================================================

def auto_fix(source: str, issues: List[LintIssue]) -> str:
    """自动修复简单问题"""
    lines = source.split('\n')

    # 按行号从后往前排序，避免行号偏移
    fixable = [i for i in issues if i.rule.auto_fix]
    fixable.sort(key=lambda x: (x.line, x.col), reverse=True)

    for issue in fixable:
        if issue.rule.code == 'Q005':
            # 尾随空白
            idx = issue.line - 1
            if 0 <= idx < len(lines):
                lines[idx] = lines[idx].rstrip()

        elif issue.rule.code == 'Q007':
            # 文件末尾缺少换行
            pass  # 在最后处理

    result = '\n'.join(lines)

    # 添加末尾换行
    if any(i.rule.code == 'Q007' for i in fixable):
        if not result.endswith('\n'):
            result += '\n'

    return result


# =============================================================================
# 输出格式化
# =============================================================================

def format_issues_text(issues: List[LintIssue], filepath: str = '') -> str:
    """格式化输出（文本格式）"""
    if not issues:
        return ''

    severity_colors = {
        Severity.ERROR: 'ERROR',
        Severity.WARNING: 'WARNING',
        Severity.INFO: 'INFO',
        Severity.HINT: 'HINT',
    }

    lines = []
    if filepath:
        lines.append(f"\n{filepath}")

    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    infos = sum(1 for i in issues if i.severity == Severity.INFO)

    for issue in issues:
        sev = severity_colors.get(issue.severity, '?')
        prefix = f"{filepath}:" if filepath else ""
        lines.append(f"  {prefix}{issue.line}:{issue.col}  {sev:7s}  [{issue.rule.code}] {issue.message}")
        if issue.source:
            lines.append(f"    | {issue.source[:80]}")

    summary_parts = []
    if errors:
        summary_parts.append(f"{errors} errors")
    if warnings:
        summary_parts.append(f"{warnings} warnings")
    if infos:
        summary_parts.append(f"{infos} infos")

    lines.append(f"  {'='*50}")
    lines.append(f"  Found: {', '.join(summary_parts)}")
    lines.append('')

    return '\n'.join(lines)


def format_issues_json(issues: List[LintIssue], filepath: str = '') -> str:
    """格式化输出（JSON 格式）"""
    result = []
    for issue in issues:
        result.append({
            'file': filepath,
            'line': issue.line,
            'col': issue.col,
            'severity': issue.severity.name,
            'rule': issue.rule.code,
            'rule_name': issue.rule.name,
            'message': issue.message,
            'source': issue.source,
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


# =============================================================================
# 入口函数
# =============================================================================

def lint_file(filepath: str, linter: LightLinter, json_output: bool = False,
              auto_fix_enabled: bool = False) -> int:
    """检查单个文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return 1

    issues = linter.check(source, filepath)

    if auto_fix_enabled and issues:
        fixed = auto_fix(source, issues)
        if fixed != source:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed)
            print(f"  Fixed {filepath}")

    if json_output:
        print(format_issues_json(issues, filepath))
    else:
        output = format_issues_text(issues, filepath)
        if output:
            print(output)

    # 返回错误数（仅 ERROR 级别）
    return sum(1 for i in issues if i.severity == Severity.ERROR)


def lint_directory(directory: str, linter: DuanLinter, json_output: bool = False,
                   auto_fix_enabled: bool = False) -> int:
    """检查目录"""
    if not os.path.isdir(directory):
        print(f"Error: directory not found: {directory}", file=sys.stderr)
        return 1

    light_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for f in files:
            if f.endswith('.light'):
                light_files.append(os.path.join(root, f))

    if not light_files:
        print("No .light files found")
        return 0

    total_errors = 0
    for fp in sorted(light_files):
        total_errors += lint_file(fp, linter, json_output, auto_fix_enabled)

    if not json_output:
        print(f"\nTotal: {len(light_files)} files, {total_errors} errors")
    return 1 if total_errors > 0 else 0


def run_linter(target: str, enabled_rules: Optional[Set[str]] = None,
               disabled_rules: Optional[Set[str]] = None,
               json_output: bool = False, auto_fix: bool = False) -> int:
    """运行检查器"""
    linter = LightLinter(rules=enabled_rules, disabled_rules=disabled_rules)

    if os.path.isdir(target):
        return lint_directory(target, linter, json_output, auto_fix)
    elif os.path.isfile(target):
        return lint_file(target, linter, json_output, auto_fix)
    else:
        print(f"Error: path not found: {target}", file=sys.stderr)
        return 1