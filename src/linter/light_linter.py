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
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


# 本模块既可能被 `import linter.light_linter`（src/ 在 sys.path 上，测试/conftest 这样引）
# 也可能被 `import src.linter.light_linter`（项目根在 sys.path 上，`python -m src.linter.cli`
# 这样引）。后一种情况下 `from code_generator import ...` 这类**绝对导入会静默失败**，
# 导致内置名登记少 200+ 条、E016 全哑。这里把 src/ 无条件放进 sys.path，让两种引法行为一致。
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


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
    'W014': {'name': '字典操作不规范', 'severity': 'warning', 'description': '建议用 .包含() 方法替代 字典包含键() 函数形式'},
    'W015': {'name': '文体风格不一致', 'severity': 'warning', 'description': '代码关键字文体与项目配置不一致（试/尝试、捕/捕获）'},
    # LH-21：静态名检查（AST 级，区分 内置名/导入名/模块级/局部 四类来源）
    'E016': {'name': '未定义的名字', 'severity': 'error',
             'description': '引用了一个未定义的名字：既非内置名、非导入名、非模块级段落/变量、也非局部变量（LH-21）'},
    # LH-09：L-166 影子变量告警的覆盖面扩展到「从 X 导入」进来的名字
    'W016': {'name': '导入名被局部遮蔽', 'severity': 'warning',
             'description': '段落体内给一个本模块「从 X 导入」进来的名字赋值，导入名被局部变量遮蔽（LH-09）'},
}


# =============================================================================
# 检查器
# =============================================================================

class LightLinter:
    """光明代码检查器"""

    def __init__(self, rules: Optional[List[str]] = None, style: Optional[str] = None):
        """
        初始化检查器

        Args:
            rules: 启用的规则 ID 列表，None 表示全部启用
            style: 目标文体风格（"工程体" / "教学体"），None 表示不检查文体
        """
        self.enabled_rules = set(rules) if rules is not None else None
        self.results: List[LintResult] = []
        self._source_lines: List[str] = []
        self._source: str = ''
        self.style = style  # "工程体" | "教学体" | None

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
        if self._is_enabled('W014'):
            self._check_dict_ops()
        if self._is_enabled('W015') and self.style is not None:
            self._check_style_consistency()

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
    # LH-21 / LH-09：AST 级静态名检查（E016 未定义的名字 / W016 导入名被局部遮蔽）
    # ------------------------------------------------------------------

    def lint_names(self, source: str, filename: str = ''):
        """执行 AST 级静态名检查，把结果并入 self.results。

        与 E002（正则、噪声大、易误报）互不干扰：这里是**按作用域查名字来源**，
        只有确认该名字既非内置名、非导入名、非模块级段落/变量、也非局部变量时才报。
        宁可漏报也不误报（误报会让全仓 .light 都跑不过 check）。

        :param source: 光明源码
        :param filename: 源文件名（仅用于定位提示）
        """
        self._source = source
        self._source_lines = source.split('\n')

        if self._is_enabled('E016'):
            for issue in check_undefined_names(source, filename=filename):
                if not self._is_enabled(issue.rule_id):
                    continue
                src = ''
                if 0 < issue.line <= len(self._source_lines):
                    src = self._source_lines[issue.line - 1].strip()
                self._add_result(issue.severity, issue.message, issue.line, issue.col,
                                 issue.rule_id, source=src)

        if self._is_enabled('W016'):
            for w in check_import_shadow(source, filename=filename):
                line = _extract_line_no(w)
                src = ''
                if 0 < line <= len(self._source_lines):
                    src = self._source_lines[line - 1].strip()
                self._add_result('warning', w, line, 0, 'W016', source=src)

        return self.results

    def lint_names_file(self, file_path: str):
        """读取文件并执行静态名检查。"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception as e:
            self._add_result('error', f'无法读取文件: {e}', 0, 0, 'E000')
            return self.results
        return self.lint_names(source, file_path)

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
    # 规则 W014: 字典操作不规范（M4 字典三轨收敛）
    # ------------------------------------------------------------------

    def _check_dict_ops(self):
        """检测 字典包含键() 函数形式调用，提示改用 .包含() 方法形式"""
        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#') or not stripped:
                continue
            # 匹配 字典包含键(字典, 键) 形式
            match = re.search(r'字典包含键\s*\(', stripped)
            if match:
                self._add_result(
                    'warning',
                    "建议用 .包含() 方法形式替代 字典包含键() 函数形式（如 d.包含(k)）",
                    i, match.start() + 1, 'W014',
                    source=stripped
                )

    # ------------------------------------------------------------------
    # 规则 W015: 文体风格不一致（M5 教学体/工程体收敛）
    # ------------------------------------------------------------------

    def _check_style_consistency(self):
        """根据 style 配置检测文体关键字不一致"""
        # 文体映射：目标风格 -> 不应出现的关键字模式及提示
        if self.style == '工程体':
            # 工程体目标：发现教学体关键字 → 提示改工程体
            patterns = [
                (r'^\s*试\s*[：:]', "教学体关键字「试:」建议改为工程体「尝试:」"),
                (r'^\s*捕\s+', "教学体关键字「捕」建议改为工程体「捕获」"),
            ]
        elif self.style == '教学体':
            # 教学体目标：发现工程体关键字 → 提示改教学体
            patterns = [
                (r'^\s*尝试\s*[：:]', "工程体关键字「尝试:」建议改为教学体「试:」"),
                (r'^\s*捕获\s+', "工程体关键字「捕获」建议改为教学体「捕」"),
            ]
        else:
            return

        for i, line in enumerate(self._source_lines, 1):
            stripped = line.strip()
            if stripped.startswith('#') or not stripped:
                continue
            for pattern, message in patterns:
                match = re.search(pattern, line)
                if match:
                    self._add_result(
                        'warning', message,
                        i, match.start() + 1, 'W015',
                        source=stripped
                    )

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


# =============================================================================
# LH-21 / LH-09：AST 级静态名检查（主战场）
# =============================================================================
#
# LH-21 症状：某个中文短语名字既不是地板内置名、也不是本模块导入名/模块级段落/局部变量，
# 编译期全安静，运行期才炸 `name 'xxx' is not defined`。
# 根因：光明内置函数名是中文短语、命名空间大且没有补全，极易「造词」
#       （`去除空白` 对 vs `去空白` 错；`最后索引` 对 vs `最后出现位置` 错）。
#
# ⚠️ 实测校准（重要）：任务书示例里的 `临时目录()` **是真实地板内置函数**
#   （`stdlib/系统接口.py:326`、`stdlib/环境.py:164`，且登记在
#   `stdlib/lightpub/__index__.py`），**不应报未定义**。所以本检查按
#   「宁可漏报也不能误报」硬约束放行它——见 tests/unit/test_LH21_未定义名.py
#   的「临时目录 是真实内置名 → 零告警」反例。E016 的正例改用 `去空白`
#   （真实内置名是 `去除空白`，`去空白` 确实不存在）。
#
# 设计原则（任务卡硬约束）：
#   1) 按作用域查名字来源（内置名 / 从 X 导入 的名字 / 模块级段落 / 局部变量）；
#   2) **宁可漏报也不能误报**——`从 X 导入` 的模块可能延迟解析、builtin_map 是调用点
#      重定向、段落可以当值传参；误报会让全仓 .light 都跑不过 check。
#   3) 只做静态判定，不改任何编译语义。
#
# LH-09：L-166 影子变量告警原本只覆盖「模块级变量被局部遮蔽」，不覆盖
#       「`从 X 导入` 进来的段落被局部遮蔽」→ 这里补齐（检测成本极低，导入表已存在）。
#
# 说明：`cli/light.py` 的 `check` 子命令由另一张卡在改，本卡用 `src/linter/cli.py`
#       （`python -m src.linter.cli --check-names file.light`）作为检查入口，
#       并用 `tools/内置名清单.py` 暴露机器可读内置名清单。


@dataclass
class NameIssue:
    """一条静态名检查结论。"""
    name: str
    line: int
    col: int
    category: str       # 期望的来源类别（内置名 / 导入名 / 模块级 / 局部变量）
    message: str
    severity: str       # 'error' | 'warning'
    rule_id: str


#: 进入这些节点意味着进入**新的作用域**，不再算作外层作用域的一部分。
_SCOPE_BOUNDARY_NAMES = frozenset({
    'Paragraph', 'MethodDefinition', 'ClassDefinition', 'InterfaceDefinition',
    'EnumDefinition', 'RecordDefinition', 'LambdaExpression',
})

#: 这些节点类型本身就是「名字绑定/声明」语句（名字不是引用）。
_DECLARED_NAME_TYPES = frozenset({
    'Paragraph', 'MethodDefinition', 'ClassDefinition', 'InterfaceDefinition',
    'EnumDefinition', 'RecordDefinition',
})

#: 内置名缓存（进程内只算一次；两腿 builtin_map 实例化约 0.4s，不能每次都算）。
_BUILTIN_NAMES_CACHE: Optional[frozenset] = None
_BUILTIN_SOURCES_CACHE: Optional[Dict[str, Dict[str, List[str]]]] = None
_KNOWN_WORDS_CACHE: Optional[frozenset] = None


def _slots_of(node: Any) -> List[str]:
    """取节点（含基类）声明的全部 __slots__ 字段名。"""
    names: List[str] = []
    for cls in type(node).__mro__:
        s = getattr(cls, '__slots__', ())
        if isinstance(s, str):
            s = (s,)
        names.extend(s)
    return names


def _children(node: Any) -> List[Any]:
    """取节点的直接 AST 子节点（只走 __slots__，避免扫到 line/col 等标量）。"""
    try:
        from ast_nodes_v3 import ASTNode
    except Exception:  # noqa: BLE001
        ASTNode = None  # 拿不到节点类则不再做 ASTNode 判定
    out: List[Any] = []
    for name in _slots_of(node):
        try:
            val = getattr(node, name, None)
        except Exception:  # noqa: BLE001 —— 槽位未初始化时跳过
            continue
        if ASTNode is None:
            continue
        if isinstance(val, ASTNode):
            out.append(val)
        elif isinstance(val, (list, tuple)):
            out.extend(x for x in val if isinstance(x, ASTNode))
    return out


_LIGHTPUB_FUNCS_CACHE: Optional[frozenset] = None


def _lightpub_function_names() -> frozenset:
    """收集 `stdlib/lightpub/__index__.py`（含 bootstrap 副本）里各模块登记的 functions。

    这是全库**最全**的地板内置函数登记（约 2600 条），`builtin_map` 只覆盖了
    compiler 调用点重定向的那一小部分，很多真实内置名（取最小值/斐波那契/转浮点数…）
    只在 lightpub 登记里出现。
    """
    global _LIGHTPUB_FUNCS_CACHE
    if _LIGHTPUB_FUNCS_CACHE is not None:
        return _LIGHTPUB_FUNCS_CACHE
    import ast as _pyast
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    names: Set[str] = set()
    for rel in ('stdlib/lightpub/__index__.py',
                'bootstrap/release/stdlib/lightpub/__index__.py'):
        path = os.path.join(_root, rel)
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                tree = _pyast.parse(f.read())
        except Exception:  # noqa: BLE001
            continue

        def _walk(node):
            if isinstance(node, _pyast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, _pyast.Constant) and k.value == 'functions' \
                            and isinstance(v, _pyast.List):
                        for e in v.elts:
                            if isinstance(e, _pyast.Constant) and isinstance(e.value, str) \
                                    and e.value and not e.value.startswith('_'):
                                names.add(e.value)
            for c in _pyast.iter_child_nodes(node):
                _walk(c)

        _walk(tree)
    _LIGHTPUB_FUNCS_CACHE = frozenset(names)
    return _LIGHTPUB_FUNCS_CACHE


def _load_builtin_registry() -> Tuple[Set[str], Dict[str, Dict[str, Set[str]]]]:
    """收集地板内置名集合与来源登记。

    来源（三处权威登记）：
      * `src/code_generator.py::PythonCodeGenerator.builtin_map` —— Python 腿调用点重定向表
      * `src/code_generator_unified.py::UnifiedCodeGenerator.builtin_map` —— unified 腿
      * `src/keywords.py::BUILTIN_TYPES` —— 内置类型名
      * `真`/`假`/`空` —— 值字面量（不是函数，但同样是「无需导入即可用」的名字）
      外加 `exception_name_map` 的内置异常名（`抛出 Xxx错误()` 场景）。
    """
    names: Set[str] = set()
    sources: Dict[str, Dict[str, Set[str]]] = {}

    def _add(name: Any, category: str, source: str):
        if not isinstance(name, str) or not name:
            return
        names.add(name)
        rec = sources.setdefault(name, {'类别': set(), '来源': set()})
        rec['类别'].add(category)
        rec['来源'].add(source)

    try:
        from code_generator import PythonCodeGenerator
        gen = PythonCodeGenerator()
        for n in gen.builtin_map:
            _add(n, '内置函数', 'src/code_generator.py:builtin_map')
        for n in getattr(gen, 'exception_name_map', {}) or {}:
            _add(n, '内置异常', 'src/code_generator.py:exception_name_map')
    except Exception:  # noqa: BLE001 —— 登记绝不能阻断检查
        pass
    try:
        from code_generator_unified import UnifiedCodeGenerator
        gen = UnifiedCodeGenerator()
        for n in getattr(gen, 'builtin_map', {}) or {}:
            _add(n, '内置函数', 'src/code_generator_unified.py:builtin_map')
    except Exception:  # noqa: BLE001
        pass
    try:
        from keywords import BUILTIN_TYPES
        for n in BUILTIN_TYPES:
            _add(n, '内置类型', 'src/keywords.py:BUILTIN_TYPES')
    except Exception:  # noqa: BLE001
        pass
    # 权威清单：`stdlib/builtins.py` 的 `__all__`（运行时真正导出的地板内置函数，129 条）
    try:
        import importlib.util
        _stdlib_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'stdlib', 'builtins.py',
        )
        _spec = importlib.util.spec_from_file_location('_light_stdlib_builtins', _stdlib_path)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        for n in getattr(_mod, '__all__', []) or []:
            if isinstance(n, str) and n and not n.startswith('_'):
                _add(n, '内置函数', 'stdlib/builtins.py:__all__')
    except Exception:  # noqa: BLE001
        pass
    for n in ('真', '假', '空'):
        _add(n, '字面量', '语言规范')
    # 权威清单③：`stdlib/lightpub/__index__.py`（2591 条）—— 各 lightpub 模块的
    # `functions` 登记，是**最全**的地板内置函数清单（取最小值/斐波那契/转浮点数 都在这）。
    for n in _lightpub_function_names():
        _add(n, '内置函数', 'stdlib/lightpub/__index__.py:functions')
    return names, sources


def builtin_names() -> frozenset:
    """全部地板内置名（可直接用、无需导入）。机器可读，供 AI 生成前先校验。"""
    global _BUILTIN_NAMES_CACHE
    if _BUILTIN_NAMES_CACHE is None:
        names, _ = _load_builtin_registry()
        _BUILTIN_NAMES_CACHE = frozenset(names)
    return _BUILTIN_NAMES_CACHE


def builtin_name_sources() -> Dict[str, Dict[str, List[str]]]:
    """内置名 → {类别: [...], 来源: [...]} 的来源登记（供 `tools/内置名清单.py` 输出）。"""
    global _BUILTIN_SOURCES_CACHE
    if _BUILTIN_SOURCES_CACHE is None:
        _, sources = _load_builtin_registry()
        _BUILTIN_SOURCES_CACHE = {
            n: {'类别': sorted(v['类别']), '来源': sorted(v['来源'])}
            for n, v in sources.items()
        }
    return _BUILTIN_SOURCES_CACHE


def _known_word_set() -> frozenset:
    """「永远不会是未定义引用」的词：关键字 + 动词（含 stdlib 动词）+ 自指词。

    光明大量「动词式调用」（`求 列表 最大值`、`追加 项 到 列表`）在 AST 里会以
    ParagraphCall 的 name 出现；它们不是未定义名字，必须整批排除，否则满屏误报。
    """
    global _KNOWN_WORDS_CACHE
    if _KNOWN_WORDS_CACHE is not None:
        return _KNOWN_WORDS_CACHE
    words: Set[str] = set()
    try:
        from keywords import (
            ALL_KEYWORDS, KEYWORDS_DOUBLE, KEYWORDS_SPECIAL,
            ALL_VERB_ARITY, BUILTIN_TYPES,
        )
        for seq in (ALL_KEYWORDS, KEYWORDS_DOUBLE):
            words.update(x for x in seq if isinstance(x, str))
        words.update(k for k in KEYWORDS_SPECIAL if isinstance(k, str))
        words.update(k for k in ALL_VERB_ARITY if isinstance(k, str))
        words.update(BUILTIN_TYPES)
    except Exception:  # noqa: BLE001
        pass
    # 自指 / 常用占位：绝不该被当「未定义」
    words.update({'己', '自身', '本', 'self', 'cls', 'it', '它'})
    _KNOWN_WORDS_CACHE = frozenset(words)
    return _KNOWN_WORDS_CACHE


def _parse_module(source: str):
    """用 src 腿解析器解析源码；解析失败返回 None（语法错误由别处负责，不重复报）。"""
    try:
        from light_parser_v3 import LightParser, Module
    except Exception:  # noqa: BLE001
        return None
    try:
        parser = LightParser()
        module = parser.parse(source)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(module, Module) or not getattr(module, 'statements', None):
        return None
    return module


#: 这些节点类型声明**模块级名字**（`.name` 槽是定义，不是引用）。
_DECLARES_NAME_TYPES: frozenset = frozenset({
    'Paragraph', 'MethodDefinition', 'ClassDefinition', 'InterfaceDefinition',
    'EnumDefinition', 'RecordDefinition',
    # FFI / 外部声明
    'FFIFunctionDecl', 'FFIStructDef', 'FFICallbackDef', 'FFIConstant', 'FFIGlobal',
    'FFITypedefDef', 'FFIConstantDef', 'FFIExternalDecl', 'FFIDecl',
    'ExportStmt',
})


def _declared_name(stmt: Any) -> Optional[str]:
    """定义类语句声明的模块级名字（段落/类/接口/枚举/方法/FFI 外部声明）。"""
    if type(stmt).__name__ in _DECLARES_NAME_TYPES:
        return getattr(stmt, 'name', None)
    return None


def _collect_python_block_defs(code: str, into: Dict[str, int]):
    """从 `引 Python:` 内联块里收集顶层 Python 定义名（def/class/赋值目标）。

    `.light` 常把函数直接写在 `引 Python` 里再在光明侧调用（如 `l4_numpy_mean`），
    这些名字对光明侧完全可见，必须算作模块级定义，否则会误报。
    """
    try:
        import ast as _pyast
        import textwrap
        # `引 Python:` 块整体缩进，直接 parse 会 IndentationError → 先统一去缩进
        tree = _pyast.parse(textwrap.dedent(code))
    except Exception:  # noqa: BLE001 —— Python 语法不合法就算了（编译器自会报）
        return
    for node in getattr(tree, 'body', []) or []:
        if isinstance(node, (_pyast.FunctionDef, _pyast.AsyncFunctionDef, _pyast.ClassDef)):
            if node.name:
                into.setdefault(node.name, 0)
        elif isinstance(node, _pyast.Assign):
            for t in node.targets:
                for sub in getattr(t, 'elts', [t]):
                    if isinstance(sub, _pyast.Name) and isinstance(sub.id, str):
                        into.setdefault(sub.id, 0)
        elif isinstance(node, _pyast.ImportFrom):
            for a in node.names:
                if a.name and a.name != '*':
                    into.setdefault(a.asname or a.name, 0)
        elif isinstance(node, _pyast.Import):
            for a in node.names:
                into.setdefault(a.asname or a.name.split('.')[0], 0)


def _collect_all_declared_names(stmt: Any, into: Dict[str, int]):
    """递归收集整棵 AST 里**声明的名字**，全部并入模块级「已知名」池。

    不限于模块顶层：内联 `引 Python:` 块（常藏在段落/类里）、FFI 外部声明、
    嵌套类方法都会登记。宁可漏报也不误报——与其因为名字藏在内联块或外部声明里
    而误报，不如一律放行。
    """
    if stmt is None:
        return
    cls = type(stmt).__name__
    if cls == 'EmbedBlock':
        _collect_python_block_defs(getattr(stmt, 'code', '') or '', into)
    elif cls == 'ImportStmt':
        symbols = getattr(stmt, 'symbols', None)
        if symbols:
            for s in symbols:
                if isinstance(s, str) and s:
                    into.setdefault(s, 0)
        else:
            mod = getattr(stmt, 'module_name', None)
            if isinstance(mod, str) and mod:
                into.setdefault(mod, 0)
        for extra in getattr(stmt, 'extra_modules', None) or []:
            nm = extra[0] if isinstance(extra, (list, tuple)) and extra else None
            if isinstance(nm, str) and nm:
                into.setdefault(nm, 0)
    else:
        nm = _declared_name(stmt) or _binding_name(stmt)
        if nm:
            into.setdefault(nm, 0)
    for ch in _children(stmt):
        _collect_all_declared_names(ch, into)


def _binding_name(stmt: Any) -> Optional[str]:
    """语句绑定的名字（`设 X 为 …`/`X = …`/循环变量/解构目标）。"""
    cls = type(stmt).__name__
    if cls == 'VarDecl':
        return getattr(stmt, 'name', None)
    if cls in ('Assignment', 'CompoundAssignment'):
        target = getattr(stmt, 'target', None)
        if isinstance(target, str):
            return target
        if target is not None and type(target).__name__ == 'Identifier':
            return getattr(target, 'name', None)
        return None
    if cls == 'DestructuringAssignment':
        return None  # 多个名字，交由 _collect_defs 逐项收集
    if cls == 'ForeachStmt':
        return getattr(stmt, 'variable', None)
    return None


def _param_names(func: Any) -> Set[str]:
    """段落/方法形参名集合。

    两种存放形态都要兼容：`Paragraph.params` 是 dict 列表（新解析器），
    `MethodDefinition.parameters` 是 `Parameter` 节点列表或 `ParameterList` 节点。
    """
    names: Set[str] = set()
    raw = getattr(func, 'parameters', None)
    if raw is None:
        raw = getattr(func, 'params', None)
    if raw is None:
        return names
    if type(raw).__name__ == 'ParameterList':
        items = getattr(raw, 'params', None) or getattr(raw, 'parameters', None) or []
    elif isinstance(raw, (list, tuple)):
        items = raw
    else:
        items = [raw]
    for p in items:
        if isinstance(p, str):
            n = p
        elif isinstance(p, dict):
            n = p.get('name') or p.get('名称')
        else:
            n = getattr(p, 'name', None)
        if n:
            # 变参 `*集合们` 解析器把星号并进名字里，函数体里引用的是不带星的 `集合们`
            names.add(n[1:] if n.startswith('*') else n)
    return names


def _add_binding(into: Dict[str, int], name: Any, line: int):
    """把一个绑定的名字登记进 into（名字为空则忽略）。"""
    if isinstance(name, str) and name:
        into.setdefault(name, line or 0)


def _collect_defs(stmts, into: Optional[Dict[str, int]] = None) -> Dict[str, int]:
    """收集一个语句块里「被赋名」的名字 → 首次出现的行号。

    光明里 `设 X 为 …` 是**函数级**作用域，所以把嵌套块里的赋值一并算进来是安全的
    （不构成误报）；`令 X 为 …`（块级）同样整体算入——宁可漏报也不误报。
    除赋值外还覆盖：循环变量、异常绑定（`捕获 e:`）、`与 … 为 变量`、推导式变量、
    模式匹配绑定。不进入嵌套段落/类/方法体（它们是独立作用域）。
    """
    if into is None:
        into = {}

    def _scan(seq):
        for st in seq:
            cls = type(st).__name__
            if cls in _SCOPE_BOUNDARY_NAMES:
                continue
            line = getattr(st, 'line', 0) or 0
            if cls == 'DestructuringAssignment':
                for v in getattr(st, 'variables', None) or []:
                    nm = v if isinstance(v, str) else getattr(v, 'name', None)
                    _add_binding(into, nm, line)
            elif cls == 'TryStmt':
                _add_binding(into, getattr(st, 'catch_var', None), line)
                for cc in getattr(st, 'catch_clauses', None) or []:
                    _add_binding(into, getattr(cc, 'catch_var', None), line)
            elif cls in ('ListComprehension', 'SetComprehension', 'DictComprehension'):
                _add_binding(into, getattr(st, 'variable', None), line)
                for g in getattr(st, 'generators', None) or []:
                    if isinstance(g, (list, tuple)) and g:
                        _add_binding(into, g[0], line)
            elif cls == 'WithStmt':
                _add_binding(into, getattr(st, 'variable', None), line)
                for item in getattr(st, 'items', None) or []:
                    if isinstance(item, (list, tuple)) and len(item) > 1:
                        _add_binding(into, item[1], line)
            else:
                nm = _binding_name(st)
                _add_binding(into, nm, line)
            # 模式匹配分支的绑定名（`情况 甲:`）
            if cls == 'MatchCase':
                _pattern_bindings(getattr(st, 'pattern', None), into, line)
            for ch in _children(st):
                if type(ch).__name__ in _SCOPE_BOUNDARY_NAMES:
                    continue
                _scan([ch])

    _scan(list(stmts) if isinstance(stmts, (list, tuple)) else [stmts])
    return into


def _pattern_bindings(pattern: Any, into: Dict[str, int], line: int):
    """把模式匹配分支里的绑定名登记进 into。"""
    if pattern is None:
        return
    if type(pattern).__name__ == 'MatchPattern':
        _add_binding(into, getattr(pattern, 'binding', None), line)
        for el in getattr(pattern, 'elements', None) or []:
            _pattern_bindings(el, into, line)
    else:
        for ch in _children(pattern):
            _pattern_bindings(ch, into, line)


def _iter_refs(node: Any) -> List[Tuple[str, int, int]]:
    """产出节点内所有「作为值/被调用」的名字引用 (name, line, col)。

    结构位（定义名/成员名/形参名/导入符号/键名）一律不产出；
    不进入嵌套作用域（嵌套段落/类/方法/λ），它们由调用方各自建作用域判定。
    """
    cls = type(node).__name__
    if cls in _SCOPE_BOUNDARY_NAMES:
        return []

    def _ln(x) -> int:
        return getattr(x, 'line', 0) or 0

    def _col(x) -> int:
        return getattr(x, 'col', 0) or 0

    out: List[Tuple[str, int, int]] = []

    if cls == 'Identifier':
        nm = getattr(node, 'name', None)
        if isinstance(nm, str) and nm:
            out.append((nm, _ln(node), _col(node)))

    elif cls == 'ParagraphCall':
        nm = getattr(node, 'name', None)
        if isinstance(nm, str) and nm:
            out.append((nm, _ln(node), _col(node)))
        # `X 的 Y` 被解析成 ParagraphCall(name='X的', args=[Y])——这里的实参是
        # **属性/成员名**（`水果的 弹出` 的 `弹出`），不是名字引用，不进作用域判定。
        if nm and nm.endswith('的'):
            return out
        for a in getattr(node, 'args', None) or []:
            out.extend(_iter_refs(a))

    elif cls == 'FunctionCallExpr':
        callee = getattr(node, 'callee', None)
        if callee is not None:
            out.extend(_iter_refs(callee))
        for a in getattr(node, 'args', None) or []:
            out.extend(_iter_refs(a))

    elif cls == 'MemberAccess':
        obj = getattr(node, 'obj', None)
        if obj is not None:
            out.extend(_iter_refs(obj))
        for a in getattr(node, 'args', None) or []:
            out.extend(_iter_refs(a))

    elif cls == 'ClassInstantiation':
        cn = getattr(node, 'class_name', None)
        if isinstance(cn, str) and cn:
            out.append((cn, _ln(node), _col(node)))
        for a in getattr(node, 'args', None) or []:
            out.extend(_iter_refs(a))

    elif cls == 'Assignment':
        target = getattr(node, 'target', None)
        if target is not None and type(target).__name__ != 'Identifier':
            out.extend(_iter_refs(target))
        value = getattr(node, 'value', None)
        if value is not None:
            out.extend(_iter_refs(value))

    elif cls == 'CompoundAssignment':
        target = getattr(node, 'target', None)
        if isinstance(target, str):
            out.append((target, _ln(node), _col(node)))
        elif target is not None:
            out.extend(_iter_refs(target))
        value = getattr(node, 'value', None)
        if value is not None:
            out.extend(_iter_refs(value))

    else:
        for ch in _children(node):
            out.extend(_iter_refs(ch))

    return out


def _iter_refs_body(body) -> List[Tuple[str, int, int]]:
    """收集函数体/类体里所有名字引用（不跨嵌套作用域）。"""
    stmts = list(body) if isinstance(body, (list, tuple)) else ([body] if body is not None else [])
    refs: List[Tuple[str, int, int]] = []
    for st in stmts:
        if type(st).__name__ in _SCOPE_BOUNDARY_NAMES:
            continue
        refs.extend(_iter_refs(st))
    return refs


def _collect_module_imports(module) -> Optional[Dict[str, str]]:
    """收集模块级导入名 → 来源模块名。

    `从 X 导入 A` 的 A、`导入 X` 的 X、多模块导入的每个模块名都会登记。
    **遇到通配导入（`从 X 导入 全部` 的 `*` 形态）返回 None**，调用方须放弃名检查
    ——通配导入的名字无法静态判定（宁可漏报）。
    """
    imports: Dict[str, str] = {}
    for st in getattr(module, 'statements', None) or []:
        if type(st).__name__ != 'ImportStmt':
            continue
        symbols = getattr(st, 'symbols', None)
        if symbols == '*':
            return None
        mod = getattr(st, 'module_name', None)
        mod = mod if isinstance(mod, str) else ''
        if symbols:
            for s in symbols:
                if isinstance(s, str) and s:
                    imports.setdefault(s, mod)
        elif mod:
            imports.setdefault(mod, mod)
        for extra in getattr(st, 'extra_modules', None) or []:
            nm = extra[0] if isinstance(extra, (list, tuple)) and extra else None
            if isinstance(nm, str) and nm:
                imports.setdefault(nm, nm)
    return imports


#: Python 内建名字。光明 stdlib 的 `.light` 常直接透出这些（Python 互操作/FFI 段），
#: 它们不是「光明内置名」，但也不该被当成未定义名字报错。
_PYTHON_BUILTIN_NAMES: frozenset = frozenset({
    'True', 'False', 'None', 'type', 'dict', 'str', 'int', 'float', 'bool', 'list',
    'tuple', 'set', 'frozenset', 'bytes', 'bytearray', 'complex', 'memoryview',
    'ord', 'chr', 'isinstance', 'issubclass', 'open', 'len', 'range', 'repr', 'slice',
    'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed', 'sum', 'min', 'max',
    'abs', 'round', 'pow', 'divmod', 'all', 'any', 'input', 'print', 'super', 'object',
    'classmethod', 'staticmethod', 'property', 'getattr', 'setattr', 'hasattr',
    'iter', 'next', 'id', 'hash', 'format', 'vars', 'dir', 'globals', 'locals',
    'eval', 'exec', 'compile', 'callable', 'help', 'breakpoint', 'exit', 'quit',
    'Exception', 'BaseException', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
})


def _is_non_reference_name(name: str) -> bool:
    """该名字**不是**可判定的「未定义引用」——直接跳过，宁可漏报。

    排除的形态（都对应光明里合法且常见的写法，误报代价远高于漏报）：
      * 含 `.` —— 模块限定访问 / 成员访问（`模块.函数`、`己.属性` 折成整体名）
      * 含 `的` —— `X 的 Y` 属性访问（解析器常把整串折成一个名字）
      * 含 `(` / `)` —— 调用被折成名字（如 `super()`）
      * 以 `己` / `self` 开头 —— 自指属性访问（`己名称` = `己.名称`）
      * 以 `_` 开头 —— 内部实现名（`_light_builtin`、`_sleep_sec` 等生成器暴露的内部符号）
      * Python 内建名 —— `.light` 里 Python 互操作/FFI 段常用
      * **含 ASCII 字母** —— Python/C 互操作名（`socket_create`、`urllib`、`UUID5`）。
        光明内置函数名都是纯中文短语，未定义名问题的重灾区也是「中文造词」；
        含 ASCII 的名字几乎必然是 FFI / 内联 Python / 隐式 C 原语，静态无法判定，
        按「宁可漏报」放行。
    """
    if '.' in name or '的' in name:
        return True
    if '(' in name or ')' in name:
        return True
    if name.startswith('己') or name.startswith('self') or name.startswith('_'):
        return True
    if any(c.isascii() and c.isalpha() for c in name):
        return True
    if name in _PYTHON_BUILTIN_NAMES:
        return True
    return False


def _undefined_message(name: str) -> str:
    return (
        f"使用了未定义的名字「{name}」：它既不是内置名（未知内置），也不是本模块的"
        f"导入名、模块级段落/变量或局部变量。光明内置函数名是中文短语、易「造词」——"
        f"请先用 `python tools/内置名清单.py` 对拍是否拼错内置名（如 `去除空白` 而非 `去空白`）；"
        f"若该名字来自模块，请用「从 模块 导入 {name}」引入。"
    )


def check_undefined_names(source: str, filename: str = '') -> List[NameIssue]:
    """静态名检查：报出所有「引用了未定义名字」的位置（LH-21）。

    纯函数，不改动 AST。**宁可漏报也不误报**：任何异常或无法判定的写法都静默跳过
    （返回空列表），绝不让检查器因一个陌生写法而报错或崩溃。
    """
    try:
        issues = _check_undefined_names_impl(source, filename)
    except Exception:  # noqa: BLE001 —— 检查器绝不能抛异常（宁可漏报）
        return []
    # Identifier AST 节点不携带行号（line=0），这里按源码回填：取该名字第一次出现的位置。
    if issues:
        _lines = source.split('\n')
        for it in issues:
            if it.line and it.line > 0:
                continue
            name = it.name or ''
            for idx, ln in enumerate(_lines, 1):
                pos = ln.find(name)
                if pos >= 0:
                    it.line, it.col = idx, pos + 1
                    break
    return issues


def _check_undefined_names_impl(source: str, filename: str = '') -> List[NameIssue]:
    """静态名检查实现（LH-21）。"""
    module = _parse_module(source)
    if module is None:
        return []

    imports = _collect_module_imports(module)
    if imports is None:
        return []  # 通配导入 → 放弃（无法判定）

    builtins = builtin_names()
    known = _known_word_set()

    module_defs: Dict[str, int] = {}
    for st in getattr(module, 'statements', None) or []:
        _collect_all_declared_names(st, module_defs)

    # 收集 (name, line, col, local_defs, params) —— 每条引用连同其所在作用域
    candidates: List[Tuple[str, int, int, Dict[str, int], Set[str]]] = []

    for st in getattr(module, 'statements', None) or []:
        cls = type(st).__name__
        if cls == 'ImportStmt':
            continue
        if cls in ('Paragraph', 'MethodDefinition'):
            local = _collect_defs(getattr(st, 'body', None) or [])
            params = _param_names(st)
            for nm, ln, col in _iter_refs_body(getattr(st, 'body', None) or []):
                candidates.append((nm, ln, col, local, params))
        elif cls in ('ClassDefinition', 'InterfaceDefinition', 'EnumDefinition',
                     'RecordDefinition'):
            # 类体：每个方法各自一个作用域；属性默认值里的引用按模块级判定
            for m in getattr(st, 'methods', None) or []:
                local = _collect_defs(getattr(m, 'body', None) or [])
                params = _param_names(m)
                for nm, ln, col in _iter_refs_body(getattr(m, 'body', None) or []):
                    candidates.append((nm, ln, col, local, params))
            for attr in getattr(st, 'attributes', None) or []:
                dv = getattr(attr, 'default_value', None)
                if dv is not None:
                    for nm, ln, col in _iter_refs(dv):
                        candidates.append((nm, ln, col, {}, set()))
        else:
            for nm, ln, col in _iter_refs(st):
                candidates.append((nm, ln, col, {}, set()))

    issues: List[NameIssue] = []
    seen: Set[Tuple[str, int]] = set()
    for nm, ln, col, local, params in candidates:
        if not isinstance(nm, str) or not nm:
            continue
        if _is_non_reference_name(nm):
            continue
        if nm in builtins or nm in known or nm in params or nm in local:
            continue
        if nm in module_defs or nm in imports:
            continue
        key = (nm, ln)
        if key in seen:
            continue
        seen.add(key)
        issues.append(NameIssue(
            name=nm, line=ln, col=col,
            category='未定义（非内置名 / 非导入名 / 非模块级 / 非局部）',
            message=_undefined_message(nm),
            severity='error', rule_id='E016',
        ))
    return issues


def check_import_shadow(source: str, filename: str = '') -> List[str]:
    """L-166 影子变量告警的覆盖面扩展：`从 X 导入` 进来的名字被局部赋值遮蔽（LH-09）。

    与 `src/scope_shadow_check.py::check_global_shadow`（模块级变量被局部遮蔽）互补：
    这里是「导入名被局部遮蔽」——段落体内出现 `设 <名> 为 …`，而 `<名>` 是本模块
    `从 X 导入` 进来的名字 → 导入的段落名被局部变量顶掉，运行期 UnboundLocalError。

    纯函数，**宁可漏报也不误报**：异常或无法判定的写法静默跳过。
    """
    try:
        return _check_import_shadow_impl(source, filename)
    except Exception:  # noqa: BLE001 —— 告警绝不能阻断检查
        return []


def _check_import_shadow_impl(source: str, filename: str = '') -> List[str]:
    """L-166 导入名被局部遮蔽告警实现（LH-09）。"""
    module = _parse_module(source)
    if module is None:
        return []

    imports = _collect_module_imports(module)
    if not imports:
        return []

    warnings: List[str] = []
    for st in getattr(module, 'statements', None) or []:
        cls = type(st).__name__
        if cls not in ('Paragraph', 'MethodDefinition'):
            continue
        local = _collect_defs(getattr(st, 'body', None) or [])
        params = _param_names(st)
        for name, line in sorted(local.items()):
            if name not in imports:
                continue
            if name in params:
                continue
            where = f'{filename}:{line}' if filename else f'第{line}行'
            warnings.append(
                f"⚠ 编译警告（L-166 影子变量）：{where} 段落『{st.name}』内给『{name}』赋值，"
                f"但『{name}』是本模块「从 {imports[name]} 导入」进来的**导入名**，被局部变量遮蔽"
                f"（LH-09：导入名被局部遮蔽）。按作用域语义这里会新建**局部**变量，"
                f"原来的『{name}』（导入的段落）在本段落内不可用，运行期会 UnboundLocalError。"
                f"请给局部变量换个名字，或在段落内用『全局 {name}。』显式声明后再赋值。"
            )
    return warnings


def _extract_line_no(message: str) -> int:
    """从 L-166 告警文案里抽行号（形如 `文件.light:24` 或 `第24行`）。"""
    m = re.search(r':(\d+)\b', message)
    if m:
        return int(m.group(1))
    m = re.search(r'第(\d+)行', message)
    if m:
        return int(m.group(1))
    return 0