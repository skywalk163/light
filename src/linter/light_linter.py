# -*- coding: utf-8 -*-
"""
光明代码检查器（linter）

提供丰富的代码检查规则，包括：
- 未使用变量检测
- 未定义变量检测
- 类型不匹配检测
- 函数参数数量不匹配检测
- 命名规范检查
- 函数过长检查
- 嵌套过深检查
- 缺少类型注解检查
- 未使用导入检查
- 废弃语法检查
- 代码重复检查
- 导入顺序检查
- 空行检查
- 缩进一致性检查
"""

import os
import re
import sys
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# 结果类型
# =============================================================================

class Severity(Enum):
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    HINT = 'hint'


@dataclass
class LintRule:
    """检查规则定义"""
    id: str
    name: str
    severity: str
    description: str = ''


@dataclass
class LintResult:
    """检查结果"""
    severity: str  # 'error', 'warning', 'info'
    message: str
    line: int
    col: int
    rule_id: str
    source: str = ''

    def to_dict(self) -> Dict:
        return {
            'severity': self.severity,
            'message': self.message,
            'line': self.line,
            'col': self.col,
            'rule_id': self.rule_id,
            'source': self.source,
        }


# =============================================================================
# 规则定义
# =============================================================================

RULES = {
    'E001': {'name': '未使用的变量', 'severity': 'error', 'description': '定义的变量从未被使用'},
    'E002': {'name': '未定义的变量', 'severity': 'error', 'description': '使用了未定义的变量'},
    'E003': {'name': '类型不匹配', 'severity': 'error', 'description': '变量类型与预期不符'},
    'E004': {'name': '函数参数数量不匹配', 'severity': 'error', 'description': '函数调用参数数量与定义不匹配'},
    'S001': {'name': '语法错误', 'severity': 'error', 'description': '代码存在语法错误'},
    'S002': {'name': '缺少结束符', 'severity': 'error', 'description': '代码块缺少结束符'},
    'L001': {'name': '布局不规范', 'severity': 'info', 'description': '代码布局不符合规范'},
    'D001': {'name': '废弃 API 使用', 'severity': 'warning', 'description': '使用了已废弃的 API'},
    'Q001': {'name': '代码质量问题', 'severity': 'warning', 'description': '检测到潜在的代码质量问题'},
    'W001': {'name': '变量名不符合命名规范', 'severity': 'warning', 'description': '变量名应使用有意义的名称'},
    'W002': {'name': '函数过长', 'severity': 'warning', 'description': '函数体超过 50 行'},
    'W003': {'name': '嵌套过深', 'severity': 'warning', 'description': '嵌套层级超过 4 层'},
    'W004': {'name': '缺少类型注解', 'severity': 'warning', 'description': '函数参数缺少类型注解'},
    'W005': {'name': '未使用的导入', 'severity': 'warning', 'description': '导入的模块从未被使用'},
    'W006': {'name': '使用已废弃的 v3.3 语法', 'severity': 'warning', 'description': '使用了 v3.3 废弃语法'},
    'W007': {'name': '代码重复', 'severity': 'warning', 'description': '检测到重复代码块'},
    'W008': {'name': '魔法数字', 'severity': 'warning', 'description': '代码中使用了未经解释的魔法数字'},
    'W009': {'name': '待办事项标记', 'severity': 'warning', 'description': '代码中包含 TODO/FIXME/XXX 标记'},
    'I001': {'name': '导入顺序不规范', 'severity': 'info', 'description': '导入语句应按字母顺序排列'},
    'I002': {'name': '缺少空行', 'severity': 'info', 'description': '函数定义之间应使用空行分隔'},
    'I003': {'name': '缩进不一致', 'severity': 'info', 'description': '缩进风格不一致'},
    'I004': {'name': '行过长', 'severity': 'info', 'description': '单行代码超过 100 个字符'},
    'I005': {'name': '行尾空白', 'severity': 'info', 'description': '行尾不应包含多余空格'},
    'W010': {'name': '空函数体', 'severity': 'warning', 'description': '函数体为空，应包含占位或实现'},
    'W011': {'name': '不可达代码', 'severity': 'warning', 'description': 'return/返 后的代码不会被执行'},
    'W012': {'name': '变量名遮蔽', 'severity': 'warning', 'description': '局部变量遮蔽了外层变量名'},
    'W013': {'name': '缺少返回类型注解', 'severity': 'warning', 'description': '函数缺少返回类型注解'},
    'I006': {'name': '多余括号', 'severity': 'info', 'description': '表达式中包含多余的括号'},
    'I007': {'name': '字符串引号不一致', 'severity': 'info', 'description': '字符串引号风格不一致（混用单双引号）'},
}


# =============================================================================
# 检查器
# =============================================================================

class LightLinter:
    """光明代码检查器"""

    def __init__(self, rules: Optional[List[str]] = None):
        """
        初始化检查器

        Args:
            rules: 启用的规则 ID 列表，None 表示全部启用
        """
        self.enabled_rules = set(rules) if rules is not None else None
        self.results: List[LintResult] = []
        self._source_lines: List[str] = []
        self._source: str = ''

    def _is_enabled(self, rule_id: str) -> bool:
        """检查规则是否启用"""
        if self.enabled_rules is None:
            return True
        return rule_id in self.enabled_rules

    def _add_result(self, severity: str, message: str, line: int, col: int,
                    rule_id: str, source: str = ''):
        """添加检查结果"""
        if not self._is_enabled(rule_id):
            return
        self.results.append(LintResult(
            severity=severity,
            message=message,
            line=line,
            col=col,
            rule_id=rule_id,
            source=source,
        ))

    def lint(self, source: str, filename: str = '') -> List[LintResult]:
        """执行所有检查"""
        self.results = []
        self._source = source
        self._source_lines = source.split('\n')

        if self._is_enabled('E001'):
            self._check_unused_variable()
        if self._is_enabled('E002'):
            self._check_undefined_variable()
        if self._is_enabled('E003'):
            self._check_type_mismatch()
        if self._is_enabled('E004'):
            self._check_argument_count()
        if self._is_enabled('W001'):
            self._check_naming_convention()
        if self._is_enabled('W002'):
            self._check_function_length()
        if self._is_enabled('W003'):
            self._check_nesting_depth()
        if self._is_enabled('W004'):
            self._check_type_annotation()
        if self._is_enabled('W005'):
            self._check_unused_import()
        if self._is_enabled('W006'):
            self._check_deprecated_syntax()
        if self._is_enabled('W007'):
            self._check_duplicate_code()
        if self._is_enabled('W008'):
            self._check_magic_number()
        if self._is_enabled('W009'):
            self._check_todo_comment()
        if self._is_enabled('I001'):
            self._check_import_order()
        if self._is_enabled('I002'):
            self._check_blank_lines()
        if self._is_enabled('I003'):
            self._check_indentation()
        if self._is_enabled('I004'):
            self._check_line_length()
        if self._is_enabled('I005'):
            self._check_trailing_whitespace()
        if self._is_enabled('W010'):
            self._check_empty_function()
        if self._is_enabled('W011'):
            self._check_unreachable_code()
        if self._is_enabled('W012'):
            self._check_shadowed_variable()
        if self._is_enabled('W013'):
            self._check_return_type()
        if self._is_enabled('I006'):
            self._check_redundant_parentheses()
        if self._is_enabled('I007'):
            self._check_string_quotes()

        return self.results

    def check(self, source: str, filename: str = '') -> List[LintResult]:
        """执行所有检查（lint 的别名，兼容外部调用）

        Args:
            source: 源代码字符串
            filename: 源文件名（可选）

        Returns:
            检查结果列表
        """
        return self.lint(source, filename)

    def lint_file(self, file_path: str) -> List[LintResult]:
        """检查文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception as e:
            self._add_result('error', f'无法读取文件: {e}', 0, 0, 'E000')
            return self.results
        return self.lint(source, file_path)

    # ------------------------------------------------------------------
    # 规则 E001: 未使用的变量
    # ------------------------------------------------------------------

    def _check_unused_variable(self):
        """检查未使用的变量"""
        defined_vars: Dict[str, int] = {}  # name -> line
        used_vars: Set[str] = set()

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 变量定义: 设 x 为 ... 或 定义 x 为 ...
            var_match = re.match(r'(?:设|定义)\s+(\S+)\s+', stripped)
            if var_match:
                var_name = var_match.group(1)
                defined_vars[var_name] = i

            # 变量使用
            for var_name in list(defined_vars.keys()):
                if var_name in stripped:
                    # 排除定义行本身
                    if not re.match(r'(?:设|定义)\s+' + re.escape(var_name), stripped):
                        used_vars.add(var_name)

        for var_name, line_no in defined_vars.items():
            if var_name not in used_vars:
                self._add_result(
                    'error', f"变量「{var_name}」定义但从未使用",
                    line_no, 0, 'E001',
                    source=self._source_lines[line_no - 1].strip()
                )

    # ------------------------------------------------------------------
    # 规则 E002: 未定义的变量
    # ------------------------------------------------------------------

    def _check_undefined_variable(self):
        """检查未定义的变量"""
        defined_vars: Set[str] = set()
        builtins = {'真', '假', '空', '打印', '印', '输入', '读', 'len', 'str', 'int', 'list', 'dict'}

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 变量定义
            var_match = re.match(r'(?:设|定义)\s+(\S+)', stripped)
            if var_match:
                defined_vars.add(var_match.group(1))

            # 函数定义（只在函数定义行提取参数）
            func_match = re.match(r'(?:段落|段|函数|函)\s+(\S+)', stripped)
            if func_match:
                defined_vars.add(func_match.group(1))
                # 提取函数参数
                param_match = re.search(r'\(([^)]*)\)', stripped)
                if param_match:
                    params = param_match.group(1).split(',')
                    for p in params:
                        p = p.strip()
                        if p and not p.startswith('#'):
                            # 只取参数名（去掉类型注解）
                            param_name = p.split(':')[0].split('：')[0].strip()
                            if param_name:
                                defined_vars.add(param_name)
                continue  # 跳过函数定义行的变量使用检查

            # 检查变量使用（简化：检查中文标识符）
            # 匹配中文标识符
            identifiers = re.findall(r'[\u4e00-\u9fff_a-zA-Z][\u4e00-\u9fff_a-zA-Z0-9]*', stripped)
            for ident in identifiers:
                if ident in builtins:
                    continue
                if ident in ('设', '定义', '段落', '段', '函数', '函', '导入', '引', '如果', '若', '当', '遍历', '遍',
                             '否则', '否', '返回', '返', '打印', '印', '类', '接口', '尝试', '试', '捕获', '捕',
                             '抛出', '抛', '掷', '最终', '终', '匹配', '配', '情况', '真', '假', '空', '是', '且', '或', '非'):
                    continue
                # 如果它是定义行的一部分，跳过
                if re.match(r'(?:设|定义|段落|段|函数|函)\s+', stripped):
                    continue
                if ident not in defined_vars and not ident[0].isascii():
                    # 检查是否是已知的标识符模式
                    if len(ident) > 1:  # 忽略单字符
                        self._add_result(
                            'error', f"使用了未定义的变量「{ident}」",
                            i, line.find(ident) + 1, 'E002',
                            source=stripped
                        )

    # ------------------------------------------------------------------
    # 规则 E004: 函数参数数量不匹配
    # ------------------------------------------------------------------

    def _check_argument_count(self):
        """检查函数参数数量不匹配（简化实现）"""
        func_defs: Dict[str, int] = {}  # name -> param_count
        func_calls: Dict[str, List[Tuple[int, int]]] = {}  # name -> [(line, arg_count)]

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 函数定义
            func_match = re.match(r'(?:段落|段|函数|函)\s+(\S+)\s*\(([^)]*)\)', stripped)
            if func_match:
                name = func_match.group(1)
                params = [p.strip() for p in func_match.group(2).split(',') if p.strip()]
                func_defs[name] = len(params)

            # 函数调用（简化检测）
            call_match = re.findall(r'(\w[\w\u4e00-\u9fff]*)\s*\(([^)]*)\)', stripped)
            for name, args_str in call_match:
                args = [a.strip() for a in args_str.split(',') if a.strip()]
                if name not in func_defs:
                    continue
                if name not in func_calls:
                    func_calls[name] = []
                func_calls[name].append((i, len(args)))

        for name, calls in func_calls.items():
            expected = func_defs.get(name, 0)
            for line_no, actual in calls:
                if actual != expected:
                    self._add_result(
                        'error', f"函数「{name}」调用参数数量 {actual} 与定义 {expected} 不匹配",
                        line_no, 0, 'E004',
                        source=self._source_lines[line_no - 1].strip()
                    )

    # ------------------------------------------------------------------
    # 规则 W001: 变量名不符合命名规范
    # ------------------------------------------------------------------

    def _check_naming_convention(self):
        """检查变量名命名规范"""
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 检查变量定义
            var_match = re.match(r'(?:设|定义)\s+(\S+)', stripped)
            if var_match:
                var_name = var_match.group(1)
                # 检查是否以字母或中文开头
                if not var_name[0].isalpha() and not '\u4e00' <= var_name[0] <= '\u9fff':
                    self._add_result(
                        'warning', f"变量名「{var_name}」不符合命名规范（应以字母或中文开头）",
                        i, stripped.find(var_name) + 1, 'W001',
                        source=stripped
                    )
                # 检查是否包含非法字符
                if not re.match(r'^[\u4e00-\u9fff_a-zA-Z][\u4e00-\u9fff_a-zA-Z0-9]*$', var_name):
                    self._add_result(
                        'warning', f"变量名「{var_name}」包含非法字符",
                        i, stripped.find(var_name) + 1, 'W001',
                        source=stripped
                    )

    # ------------------------------------------------------------------
    # 规则 W002: 函数过长
    # ------------------------------------------------------------------

    def _check_function_length(self):
        """检查函数是否过长"""
        func_start = None
        func_name = ''
        func_indent = 0

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 检测函数定义
            func_match = re.match(r'(?:段落|段|函数|函)\s+(\S+)', stripped)
            if func_match:
                # 计算前一个函数长度
                if func_start is not None:
                    length = i - func_start
                    if length > 50:
                        self._add_result(
                            'warning', f"函数「{func_name}」过长 ({length} 行，建议 ≤50 行)",
                            func_start, 0, 'W002',
                            source=self._source_lines[func_start - 1].strip()
                        )
                func_name = func_match.group(1)
                func_start = i
                # 计算缩进级别
                func_indent = len(line) - len(line.lstrip())

        # 检查最后一个函数
        if func_start is not None:
            length = len(self._source_lines) - func_start + 1
            if length > 50:
                self._add_result(
                    'warning', f"函数「{func_name}」过长 ({length} 行，建议 ≤50 行)",
                    func_start, 0, 'W002',
                    source=self._source_lines[func_start - 1].strip()
                )

    # ------------------------------------------------------------------
    # 规则 W003: 嵌套过深
    # ------------------------------------------------------------------

    def _check_nesting_depth(self):
        """检查嵌套深度"""
        nesting_keywords = {'如果', '若', '否则', '否则如果', '否则若', '否',
                            '遍历', '遍', '当',
                            '尝试', '试', '捕获', '捕'}

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 计算缩进级别
            indent = len(line) - len(line.lstrip())
            indent_level = indent // 4

            if indent_level > 4:
                self._add_result(
                    'warning', f"嵌套过深（缩进级别 {indent_level}，建议 ≤4 级）",
                    i, indent, 'W003',
                    source=stripped
                )

    # ------------------------------------------------------------------
    # 规则 W004: 缺少类型注解
    # ------------------------------------------------------------------

    def _check_type_annotation(self):
        """检查函数参数是否缺少类型注解"""
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 检测函数定义
            func_match = re.match(r'(?:段落|段|函数|函)\s+(\S+)\s*\(([^)]*)\)', stripped)
            if func_match:
                name = func_match.group(1)
                params_str = func_match.group(2)
                if params_str.strip():
                    params = [p.strip() for p in params_str.split(',') if p.strip()]
                    for param in params:
                        # 检查是否有类型注解（包含 :）
                        if ':' not in param and '为' not in param:
                            self._add_result(
                                'warning', f"参数「{param}」缺少类型注解（建议: 参数名: 类型）",
                                i, line.find(param) + 1 if param in line else 0, 'W004',
                                source=stripped
                            )

    # ------------------------------------------------------------------
    # 规则 W005: 未使用的导入
    # ------------------------------------------------------------------

    def _check_unused_import(self):
        """检查未使用的导入"""
        imports: Dict[str, int] = {}  # module -> line
        used_imports: Set[str] = set()

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 检测导入语句
            import_match = re.match(r'(?:导入|引)\s+(\S+)', stripped)
            if import_match:
                mod_name = import_match.group(1)
                imports[mod_name] = i

            # 检测导入使用
            for mod in imports:
                if mod in stripped and not re.match(r'(?:导入|引)\s+' + re.escape(mod), stripped):
                    used_imports.add(mod)

        for mod, line_no in imports.items():
            if mod not in used_imports:
                self._add_result(
                    'warning', f"模块「{mod}」导入但从未使用",
                    line_no, 0, 'W005',
                    source=self._source_lines[line_no - 1].strip()
                )

    # ------------------------------------------------------------------
    # 规则 W006: 使用已废弃的 v3.3 语法
    # ------------------------------------------------------------------

    def _check_deprecated_syntax(self):
        """检查已废弃的 v3.3 语法"""
        deprecated_patterns = [
            (r'接收', '「接收」关键字已废弃，请使用括号参数语法'),
            (r'\b嵌入\b', '「嵌入」关键字已废弃，请使用「引」'),
            (r'定义\s+\S+\s+等于', '「定义 x 等于 y」语法已废弃，请使用「设 x 为 y」'),
        ]

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            for pattern, message in deprecated_patterns:
                match = re.search(pattern, stripped)
                if match:
                    self._add_result(
                        'warning', message,
                        i, match.start() + 1, 'W006',
                        source=stripped
                    )

    # ------------------------------------------------------------------
    # 规则 W007: 代码重复
    # ------------------------------------------------------------------

    def _check_duplicate_code(self):
        """检查重复代码块（简化实现：检查连续 3 行完全相同的代码）"""
        line_count = len(self._source_lines)
        if line_count < 3:
            return

        # 构建行签名（忽略空行和注释）
        signatures: Dict[str, List[int]] = {}
        for i, line in enumerate(self._source_lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                if stripped in signatures:
                    signatures[stripped].append(i + 1)
                else:
                    signatures[stripped] = [i + 1]

        # 检查重复行（同一行出现 3 次以上）
        for line_content, lines in signatures.items():
            if len(lines) >= 3:
                # 检查是否是连续重复
                consecutive = []
                for j in range(1, len(lines)):
                    if lines[j] - lines[j-1] == 1:
                        consecutive.append(lines[j-1])
                if consecutive:
                    self._add_result(
                        'warning', f"检测到重复代码行: 「{line_content[:40]}」",
                        consecutive[0], 0, 'W007',
                        source=line_content
                    )

    # ------------------------------------------------------------------
    # 规则 E003: 类型不匹配
    # ------------------------------------------------------------------

    def _check_type_mismatch(self):
        """检查类型不匹配（简化实现：检测基本类型赋值冲突）"""
        var_types: Dict[str, str] = {}  # var_name -> type_hint

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 检测类型注解的变量定义: 设 x: 数值 = 10
            type_match = re.match(r'设\s+(\S+)\s*[:：]\s*(\S+)', stripped)
            if type_match:
                var_name = type_match.group(1)
                type_hint = type_match.group(2)
                var_types[var_name] = type_hint

            # 检测赋值: 设 x 为 ... 后面的值推测类型
            assign_match = re.match(r'设\s+(\S+)\s+为\s+(.+)', stripped)
            if assign_match:
                var_name = assign_match.group(1)
                value = assign_match.group(2).strip()
                if var_name in var_types:
                    expected_type = var_types[var_name]
                    # 从值推测实际类型
                    actual_type = self._guess_type(value)
                    if actual_type and actual_type != expected_type:
                        self._add_result(
                            'error', f"类型不匹配: 变量「{var_name}」期望类型 {expected_type}，但赋值为 {actual_type}",
                            i, 0, 'E003',
                            source=stripped
                        )

    @staticmethod
    def _guess_type(value: str) -> Optional[str]:
        """推测值的类型"""
        value = value.strip()
        if value in ('真', '假'):
            return '逻辑'
        if value == '空':
            return '空'
        if re.match(r'^-?\d+$', value):
            return '整数'
        if re.match(r'^-?\d+\.\d+$', value):
            return '小数'
        if value.startswith('"') and value.endswith('"'):
            return '文本'
        if value.startswith("'") and value.endswith("'"):
            return '文本'
        if value.startswith('[') or value.startswith('['):
            return '列表'
        if value.startswith('{') and ':' in value:
            return '映射'
        return None

    # ------------------------------------------------------------------
    # 规则 W008: 魔法数字
    # ------------------------------------------------------------------

    def _check_magic_number(self):
        """检查魔法数字（硬编码的数字常量）"""
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            # 跳过注释、字符串中的数字
            # 检查行中的数字（排除赋值、定义、比较等常见模式）
            numbers = re.findall(r'(?<![.\w])[1-9]\d{1,}(?![.\w])', stripped)
            for num in numbers:
                # 排除常见模式：配置值、日期等
                if int(num) in (0, 1, -1):
                    continue
                # 检查是否是魔法数字（不是赋值的目标或已知模式）
                if not re.match(r'.*[设为等于=]\s*' + re.escape(num), stripped):
                    # 在表达式中出现
                    if re.search(r'[+\-*/%<>]', stripped):
                        self._add_result(
                            'warning', f"魔法数字「{num}」建议定义为命名常量",
                            i, line.find(num) + 1, 'W008',
                            source=stripped
                        )

    # ------------------------------------------------------------------
    # 规则 W009: 待办事项标记
    # ------------------------------------------------------------------

    def _check_todo_comment(self):
        """检查代码中的 TODO/FIXME/XXX 标记"""
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if not stripped:
                continue

            # 在注释中查找待办标记
            comment_match = re.search(r'#.*\b(TODO|FIXME|XXX|HACK|BUG|WORKAROUND)\b', stripped)
            if comment_match:
                tag = comment_match.group(1)
                self._add_result(
                    'warning', f"包含待办标记「{tag}」: {stripped.strip()[:60]}",
                    i, comment_match.start() + 1, 'W009',
                    source=stripped
                )

    # ------------------------------------------------------------------
    # 规则 I004: 行过长
    # ------------------------------------------------------------------

    def _check_line_length(self, max_length: int = 100):
        """检查单行代码是否过长"""
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.rstrip()
            if len(stripped) > max_length:
                # 跳过纯注释行
                if stripped.strip().startswith('#'):
                    continue
                self._add_result(
                    'info', f"行过长 ({len(stripped)} 字符，建议 ≤{max_length})",
                    i, max_length, 'I004',
                    source=stripped[:80]
                )

    # ------------------------------------------------------------------
    # 规则 I005: 行尾空白
    # ------------------------------------------------------------------

    def _check_trailing_whitespace(self):
        """检查行尾多余空白"""
        for i, line in enumerate(self._source_lines, 1):
            if line != line.rstrip():
                stripped = line.rstrip()
                self._add_result(
                    'info', "行尾包含多余空白字符",
                    i, len(stripped) + 1, 'I005',
                    source=stripped[:60]
                )

    # ------------------------------------------------------------------
    # 规则 W010: 空函数体
    # ------------------------------------------------------------------

    def _check_empty_function(self):
        """检查空函数体"""
        func_start = None
        func_name = ''
        func_indent = -1
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            func_match = re.match(r'(?:段落|段|函数|函)\s+(\S+)', stripped)
            if func_match:
                # 检查前一个函数是否为空
                if func_start is not None:
                    self._check_function_body_empty(func_name, func_start, i, func_indent)
                func_name = func_match.group(1)
                func_start = i
                func_indent = len(line) - len(line.lstrip())
        # 检查最后一个函数
        if func_start is not None:
            self._check_function_body_empty(func_name, func_start, len(self._source_lines) + 1, func_indent)

    def _check_function_body_empty(self, name: str, start: int, end: int, indent: int):
        """检查单个函数体是否为空"""
        # 查找函数定义的后续行，检查是否有非空非注释行
        for j in range(start, min(end, len(self._source_lines) + 1)):
            if j < len(self._source_lines):
                line = self._source_lines[j]
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                line_indent = len(line) - len(line.lstrip())
                if line_indent > indent:
                    # 有缩进内容，函数体非空
                    return
        # 没有找到缩进内容，函数体为空
        self._add_result(
            'warning', f"函数「{name}」体为空，请添加实现或占位符",
            start, 0, 'W010',
            source=self._source_lines[start - 1].strip() if start <= len(self._source_lines) else ''
        )

    # ------------------------------------------------------------------
    # 规则 W011: 不可达代码
    # ------------------------------------------------------------------

    def _check_unreachable_code(self):
        """检查 return 后的不可达代码"""
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            # 检测返回语句
            if re.match(r'(?:返回|返)\s+', stripped):
                # 检查后续行是否在当前缩进层级内
                indent = len(line) - len(line.lstrip())
                for j in range(i, len(self._source_lines)):
                    next_line = self._source_lines[j]
                    next_stripped = next_line.strip()
                    if not next_stripped or next_stripped.startswith('#'):
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= indent:
                        break  # 函数结束或遇到同级代码
                    # 在 return 后有缩进代码，但缩进 > indent，说明是函数体后的代码
                    # 只有在同一缩进级的代码后面才会不可达
                # 检查同一缩进级的后续代码
                same_level_found = False
                for j in range(i, len(self._source_lines)):
                    next_line = self._source_lines[j]
                    next_stripped = next_line.strip()
                    if not next_stripped or next_stripped.startswith('#'):
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent == indent and not re.match(r'(?:返回|返|否则|否|捕获|捕)\s+', next_stripped):
                        # 同一缩进级且不是 else/catch
                        if not re.match(r'(?:段落|段|函数|函)\s+', next_stripped):
                            same_level_found = True
                            self._add_result(
                                'warning', f"不可达代码：L{i} 的返回语句后的代码不会被执行",
                                j + 1, 0, 'W011',
                                source=next_stripped
                            )
                            break

    # ------------------------------------------------------------------
    # 规则 W012: 变量名遮蔽
    # ------------------------------------------------------------------

    def _check_shadowed_variable(self):
        """检查变量名遮蔽外部变量"""
        outer_vars: Dict[str, int] = {}  # 外部变量名 -> 定义行
        func_vars: Dict[str, Dict[str, int]] = {}  # 函数名 -> {变量名: 定义行}
        current_func = ''

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # 检测函数定义
            func_match = re.match(r'(?:段落|段|函数|函)\s+(\S+)', stripped)
            if func_match:
                current_func = func_match.group(1)
                if current_func not in func_vars:
                    func_vars[current_func] = {}
                continue

            # 检测变量定义
            var_match = re.match(r'(?:设|定义)\s+(\S+)', stripped)
            if var_match:
                var_name = var_match.group(1)
                if current_func:
                    # 检查是否遮蔽了外部变量
                    if var_name in outer_vars and var_name not in func_vars.get(current_func, {}):
                        self._add_result(
                            'warning', f"变量「{var_name}」遮蔽了外层变量（定义于 L{outer_vars[var_name]}）",
                            i, 0, 'W012',
                            source=stripped
                        )
                    func_vars.setdefault(current_func, {})[var_name] = i
                else:
                    outer_vars[var_name] = i

    # ------------------------------------------------------------------
    # 规则 W013: 缺少返回类型注解
    # ------------------------------------------------------------------

    def _check_return_type(self):
        """检查函数缺少返回类型注解"""
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            func_match = re.match(r'(?:段落|段|函数|函)\s+(\S+)\s*\(([^)]*)\)\s*[：:]?\s*$', stripped)
            if func_match:
                name = func_match.group(1)
                # 检查是否有返回类型注解（-> 类型）
                if '->' not in stripped and '→' not in stripped:
                    # 检查函数体是否有返回语句
                    has_return = False
                    func_indent = len(line) - len(line.lstrip())
                    for j in range(i + 1, min(i + 50, len(self._source_lines) + 1)):
                        if j < len(self._source_lines):
                            next_line = self._source_lines[j]
                            next_stripped = next_line.strip()
                            if not next_stripped or next_stripped.startswith('#'):
                                continue
                            next_indent = len(next_line) - len(next_line.lstrip())
                            if next_indent <= func_indent:
                                break
                            if re.match(r'(?:返回|返)\s+', next_stripped):
                                has_return = True
                                break
                    if has_return:
                        self._add_result(
                            'warning', f"函数「{name}」包含返回语句但缺少返回类型注解（建议: -> 类型）",
                            i, 0, 'W013',
                            source=stripped
                        )

    # ------------------------------------------------------------------
    # 规则 I006: 多余括号
    # ------------------------------------------------------------------

    def _check_redundant_parentheses(self):
        """检查表达式中多余的括号"""
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#') or not stripped:
                continue
            # 检查 if / 如果 条件中的多余括号
            # 匹配: 如果 (x) 或 如果((x))
            if_match = re.match(r'(?:如果|若)\s+\(\((.+)\)\)\s*[：:]?', stripped)
            if if_match:
                self._add_result(
                    'info', f"条件表达式外层有多余括号：{if_match.group(1)[:40]}",
                    i, 0, 'I006',
                    source=stripped
                )
            # 检查返回语句中的多余括号: 返 (x) → 返 x
            ret_match = re.match(r'(?:返回|返)\s+\(([^()]+)\)\s*$', stripped)
            if ret_match:
                inner = ret_match.group(1)
                # 排除函数调用和复杂表达式
                if not re.match(r'[\w\u4e00-\u9fff.]+\(', inner) and '+' not in inner and '-' not in inner:
                    self._add_result(
                        'info', f"返回语句中的括号可省略：{inner[:40]}",
                        i, 0, 'I006',
                        source=stripped
                    )

    # ------------------------------------------------------------------
    # 规则 I007: 字符串引号不一致
    # ------------------------------------------------------------------

    def _check_string_quotes(self):
        """检查字符串引号风格是否一致"""
        double_quotes = 0
        single_quotes = 0
        double_lines = []
        single_lines = []

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            # 统计双引号字符串
            dq = re.findall(r'"[^"]*"', stripped)
            # 统计单引号字符串
            sq = re.findall(r"'[^']*'", stripped)
            # 排除注释中的引号
            if '#' in stripped:
                code_part = stripped.split('#')[0]
                dq = re.findall(r'"[^"]*"', code_part)
                sq = re.findall(r"'[^']*'", code_part)

            if dq:
                double_quotes += len(dq)
                double_lines.append(i)
            if sq:
                single_quotes += len(sq)
                single_lines.append(i)

        # 如果两种引号都有使用，给出提示
        if double_quotes > 0 and single_quotes > 0:
            # 找出行数较少的那个风格的行
            if double_quotes < single_quotes:
                target_lines = double_lines
                target_style = '双引号(")'
                other_style = '单引号(\')'
            else:
                target_lines = single_lines
                target_style = '单引号(\')'
                other_style = '双引号(")'

            for line_no in target_lines[:3]:  # 只显示前 3 处
                self._add_result(
                    'info', f"字符串引号风格不一致，建议统一使用{other_style}而非{target_style}",
                    line_no, 0, 'I007',
                    source=self._source_lines[line_no - 1].strip()[:60]
                )

    # ------------------------------------------------------------------
    # 规则 I001: 导入顺序不规范
    # ------------------------------------------------------------------

    def _check_import_order(self):
        """检查导入语句顺序"""
        import_lines = []
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if re.match(r'(?:导入|引)\s+', stripped):
                import_lines.append((i, stripped))

        # 检查是否按字母顺序排列
        for j in range(1, len(import_lines)):
            prev_line = import_lines[j - 1][1]
            curr_line = import_lines[j][1]
            if curr_line < prev_line:
                self._add_result(
                    'info', f"导入语句顺序不规范: 「{import_lines[j-1][1]}」应在「{import_lines[j][1]}」之前",
                    import_lines[j][0], 0, 'I001',
                    source=curr_line
                )

    # ------------------------------------------------------------------
    # 规则 I002: 缺少空行
    # ------------------------------------------------------------------

    def _check_blank_lines(self):
        """检查函数定义之间是否缺少空行"""
        func_lines = []
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if re.match(r'(?:段落|段|函数|函)\s+', stripped):
                func_lines.append(i)

        for j in range(1, len(func_lines)):
            # 检查前一个函数结束到当前函数之间是否有空行
            prev_end = func_lines[j - 1]
            curr_start = func_lines[j]
            if curr_start - prev_end <= 1:
                # 检查上一行是否为空行（函数定义紧挨着）
                pass  # 简化处理，不检查函数体结束位置
            elif curr_start - prev_end == 2:
                # 中间有一行，检查是否是空行
                mid_line = self._source_lines[prev_end]  # 函数定义行后的第一行
                if mid_line.strip():
                    self._add_result(
                        'info', f"函数定义之间缺少空行（L{prev_end} 和 L{curr_start}）",
                        curr_start, 0, 'I002',
                        source=self._source_lines[curr_start - 1].strip()
                    )

    # ------------------------------------------------------------------
    # 规则 I003: 缩进不一致
    # ------------------------------------------------------------------

    def _check_indentation(self):
        """检查缩进风格是否一致"""
        indent_sizes: Set[int] = set()

        for line in self._source_lines:
            stripped = line.rstrip()
            if not stripped or stripped.startswith('#'):
                continue
            indent = len(line) - len(line.lstrip())
            if indent > 0:
                indent_sizes.add(indent)

        # 如果有多种缩进大小，且不是 4 的倍数，提醒
        if len(indent_sizes) > 1:
            non_standard = [s for s in indent_sizes if s % 4 != 0]
            if non_standard:
                for i, line in enumerate(self._source_lines, 1):
                    stripped = line.rstrip()
                    if not stripped:
                        continue
                    indent = len(line) - len(line.lstrip())
                    if indent > 0 and indent % 4 != 0:
                        self._add_result(
                            'info', f"缩进不一致：发现 {indent} 空格缩进（建议使用 4 的倍数）",
                            i, 0, 'I003',
                            source=stripped
                        )
                        break

    # ------------------------------------------------------------------
    # 检查结果输出
    # ------------------------------------------------------------------

    def format_results(self, filename: str = '') -> str:
        """格式化输出结果"""
        if not self.results:
            return ''

        lines = []
        if filename:
            lines.append(f"\n{filename}")

        severity_counts = {'error': 0, 'warning': 0, 'info': 0, 'hint': 0}

        for result in self.results:
            severity_counts[result.severity] = severity_counts.get(result.severity, 0) + 1
            prefix = f"{filename}:" if filename else ""
            lines.append(
                f"  {prefix}{result.line}:{result.col}  "
                f"{result.severity.upper():7s}  "
                f"[{result.rule_id}] {result.message}"
            )
            if result.source:
                lines.append(f"    | {result.source[:80]}")

        summary_parts = []
        for sev in ['error', 'warning', 'info']:
            if severity_counts.get(sev, 0) > 0:
                summary_parts.append(f"{severity_counts[sev]} {sev}s")

        lines.append(f"  {'=' * 50}")
        lines.append(f"  Found: {', '.join(summary_parts)}")
        lines.append('')

        return '\n'.join(lines)

    def format_json(self, filename: str = '') -> str:
        """输出 JSON 格式结果"""
        import json
        results = []
        for r in self.results:
            d = r.to_dict()
            if filename:
                d['file'] = filename
            results.append(d)
        return json.dumps(results, ensure_ascii=False, indent=2)


def lint_file(filepath: str, linter: LightLinter) -> int:
    """检查单个文件"""
    results = linter.lint_file(filepath)
    output = linter.format_results(filepath)
    if output:
        print(output)
    return sum(1 for r in results if r.severity == 'error')


def lint_directory(directory: str, linter: LightLinter) -> int:
    """检查目录"""
    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}")
        return 1

    light_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for f in files:
            if f.endswith('.light'):
                light_files.append(os.path.join(root, f))

    if not light_files:
        print("未找到 .light 文件")
        return 0

    total_errors = 0
    for fp in sorted(light_files):
        total_errors += lint_file(fp, linter)

    print(f"\n总计: {len(light_files)} 个文件, {total_errors} 个错误")
    return 1 if total_errors > 0 else 0