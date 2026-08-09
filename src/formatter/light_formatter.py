# -*- coding: utf-8 -*-
"""
光明代码格式化器

提供完整的光明代码格式化功能，支持多种格式化规则。

用法:
    from formatter import LightFormatter
    formatter = LightFormatter(indent_size=4, max_line_length=80)
    formatted = formatter.format(source)
"""

import re
import os
from typing import List, Dict, Optional


# 块关键字（需要增加缩进）
BLOCK_KEYWORDS = {
    '如果', '否则如果', '否则若', '遍历', '当',
    '尝试', '捕获', '匹配', '情况',
    '函数', '段落', '段', '类', '接口',
    '构造', '异步',
    '若', '遍', '试', '捕', '配',
}

# 需要冒号的关键字
NEEDS_COLON = BLOCK_KEYWORDS | {'否则', '接收', '否', '返', '跳', '过', '抛', '终', '最终'}


class LightFormatter:
    """光明代码格式化器"""

    def __init__(self, indent_size: int = 4, max_line_length: int = 80):
        self.indent_size = indent_size
        self.max_line_length = max_line_length

    def format(self, source: str) -> str:
        """格式化代码"""
        source = self._format_trailing_whitespace(source)
        source = self._format_line_breaks(source)
        source = self._format_brackets(source)
        source = self._format_spacing(source)
        source = self._format_indentation(source)
        source = self._format_function_signature(source)
        source = self._format_blank_lines(source)
        source = self._format_imports(source)
        source = self._format_comment_spacing(source)
        source = self._format_trailing_commas(source)
        source = self._format_multi_line_statements(source)
        # 确保末尾有换行
        if not source.endswith('\n'):
            source += '\n'
        return source

    def format_file(self, file_path: str) -> str:
        """格式化文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        formatted = self.format(source)
        if formatted != source:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted)
        return formatted

    def format_token(self, tokens) -> str:
        """基于 token 序列格式化"""
        # 简化实现：将 token 序列转为字符串后用 format 处理
        if isinstance(tokens, list):
            source = ' '.join(str(t) for t in tokens)
        else:
            source = str(tokens)
        return self.format(source)

    def _format_indentation(self, source: str) -> str:
        """统一缩进为 4 空格"""
        lines = source.split('\n')
        result = []
        indent = 0
        prev_non_blank_indent = 0

        # 预扫描，找出所有函数定义行（用于重置缩进）
        func_def_lines = set()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                kw = self._get_keyword(stripped, BLOCK_KEYWORDS)
                if kw in ('段', '函', '函数', '段落', '类', '接口'):
                    func_def_lines.add(i)

        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if not stripped:
                result.append('')
                continue

            content = stripped.strip()
            keyword = self._get_keyword(content, NEEDS_COLON)

            # 如果当前行是一个函数/类定义，且在空行之后，重置缩进
            if i in func_def_lines and i > 0 and lines[i-1].strip() == '':
                indent = 0

            # 处理"否则"、"捕获"等：它们应与对应的块同级
            if keyword in ('否则', '否则如果', '否则若', '捕获', '捕', '否'):
                actual_indent = max(0, indent - 1)
            else:
                actual_indent = indent

            # 格式化行内容：添加冒号
            if not content.startswith('#'):
                if keyword in NEEDS_COLON:
                    if not content.rstrip().endswith('：') and not content.rstrip().endswith(':'):
                        content = content + '：'

            result.append(' ' * (self.indent_size * actual_indent) + content)

            # 更新下一行的缩进
            if keyword in BLOCK_KEYWORDS:
                indent = actual_indent + 1
            elif keyword in ('否则', '否则如果', '否则若', '捕获', '捕', '否'):
                indent = actual_indent + 1
            else:
                indent = actual_indent

        # 移除末尾空行
        while result and result[-1] == '':
            result.pop()

        return '\n'.join(result)

    def _format_spacing(self, source: str) -> str:
        """运算符/逗号/冒号前后空格格式化"""
        # 处理中文标点前后空格
        # 逗号后加空格
        source = re.sub(r'，(\S)', r'， \1', source)
        # 确保冒号前无空格，后加空格（中文冒号）
        source = re.sub(r'\s+：', '：', source)
        source = re.sub(r'：(\S)', r'： \1', source)
        # 英文冒号后加空格
        source = re.sub(r':(\S)', r': \1', source)
        # 运算符前后空格（避免干扰中文注释）
        # 简单处理：在行的非注释部分添加运算符空格
        lines = source.split('\n')
        result = []
        for line in lines:
            if '#' in line:
                # 分离注释
                code_part, _, comment_part = line.partition('#')
                code_part = self._add_operator_spacing(code_part)
                result.append(code_part + '#' + comment_part)
            else:
                result.append(self._add_operator_spacing(line))
        return '\n'.join(result)

    @staticmethod
    def _add_operator_spacing(line: str) -> str:
        """在运算符前后添加空格"""
        # 处理中文标点（避免破坏中文）
        # 等号（非 == != 等比较符）
        line = re.sub(r'(?<![=!<>])=(?!=)', ' = ', line)
        # 比较运算符
        line = re.sub(r'==', ' == ', line)
        line = re.sub(r'!=', ' != ', line)
        line = re.sub(r'<=', ' <= ', line)
        line = re.sub(r'>=', ' >= ', line)
        line = re.sub(r'(?<![<>])>(?!=)', ' > ', line)
        line = re.sub(r'(?<![<>])<(?!=)', ' < ', line)
        # 算术运算符（允许数字前后的运算符）
        line = re.sub(r'(?<![+\-*/%])\+(?=[^+\d\s]|\d)', ' + ', line)
        line = re.sub(r'(?<![+\-*/%])-(?=[^>\d\s]|\d)', ' - ', line)
        line = re.sub(r'(?<![*/])[*](?![*/])', ' * ', line)
        line = re.sub(r'(?<![*/])/(?![/*])', ' / ', line)
        # 清理多余空格
        line = re.sub(r' {2,}', ' ', line)
        # 去除行首尾空格（保持缩进）
        line = line.rstrip()
        return line

    def _format_line_breaks(self, source: str) -> str:
        """统一换行风格"""
        # 统一为 \n
        source = source.replace('\r\n', '\n').replace('\r', '\n')
        return source

    def _format_blank_lines(self, source: str) -> str:
        """控制空行数量：最多保留 2 个连续空行"""
        lines = source.split('\n')
        result = []
        blank_count = 0

        for line in lines:
            stripped = line.strip()

            if stripped == '':
                blank_count += 1
                continue

            # 最多保留 2 个连续空行
            if blank_count >= 2:
                result.extend([''] * 2)
            elif blank_count == 1:
                result.append('')
            blank_count = 0
            result.append(line)

        # 移除末尾空行
        while result and result[-1] == '':
            result.pop()

        return '\n'.join(result)

    def _format_trailing_whitespace(self, source: str) -> str:
        """去除行尾空格"""
        lines = source.split('\n')
        result = [line.rstrip() for line in lines]
        return '\n'.join(result)

    def _format_imports(self, source: str) -> str:
        """排序导入语句，按类型分组（标准库、第三方、本地）"""
        lines = source.split('\n')
        import_lines = []
        non_import_lines = []
        in_import_block = False
        import_block = []

        # 标准库导入前缀（光明内置模块）
        STDLIB_PREFIXES = ('时间', '文件', '系统', '数学', '网络', '正则', 'JSON', 'json',
                           'os', 'sys', 're', 'math', 'time', 'json', 'pathlib')

        for line in lines:
            stripped = line.strip()
            # 检测导入语句
            if stripped.startswith('导入') or stripped.startswith('引') or stripped.startswith('from 导入'):
                import_block.append(line)
                in_import_block = True
            elif in_import_block and stripped == '':
                # 空行结束导入块
                import_lines.extend(import_block)
                import_block = []
                in_import_block = False
                non_import_lines.append('')
            elif in_import_block:
                # 导入块结束
                import_lines.extend(import_block)
                import_block = []
                in_import_block = False
                non_import_lines.append(line)
            else:
                non_import_lines.append(line)

        # 处理最后的导入块
        if import_block:
            import_lines.extend(import_block)

        if import_lines:
            # 按类型分组
            stdlib_imports = []
            third_party_imports = []
            local_imports = []

            for imp in import_lines:
                stripped = imp.strip()
                # 判断是否是标准库导入
                is_stdlib = False
                for prefix in STDLIB_PREFIXES:
                    if stripped.startswith('导入 ' + prefix) or stripped.startswith('引 ' + prefix):
                        is_stdlib = True
                        break
                # 判断是否是本地导入（包含 . 或 /）
                if is_stdlib:
                    stdlib_imports.append(imp)
                elif '.' in stripped or '/' in stripped:
                    local_imports.append(imp)
                else:
                    third_party_imports.append(imp)

            # 每组内排序
            stdlib_imports.sort(key=lambda x: x.strip())
            third_party_imports.sort(key=lambda x: x.strip())
            local_imports.sort(key=lambda x: x.strip())

            # 组合结果
            grouped = []
            if stdlib_imports:
                grouped.extend(stdlib_imports)
                grouped.append('')
            if third_party_imports:
                grouped.extend(third_party_imports)
                grouped.append('')
            if local_imports:
                grouped.extend(local_imports)
                grouped.append('')
            # 移除末尾多余空行
            while grouped and grouped[-1] == '':
                grouped.pop()

            result = grouped + [''] + non_import_lines
        else:
            result = non_import_lines

        return '\n'.join(result)

    def _format_comment_spacing(self, source: str) -> str:
        """注释格式化：确保 # 前有 2 个空格"""
        lines = source.split('\n')
        result = []
        for line in lines:
            if '#' in line:
                code_part, _, comment_part = line.partition('#')
                if code_part.strip() and not code_part.endswith(' '):
                    code_part = code_part.rstrip() + '  '
                result.append(code_part + '#' + comment_part)
            else:
                result.append(line)
        return '\n'.join(result)

    @staticmethod
    def _get_keyword(content: str, keywords: set) -> str:
        """获取内容开头的关键字"""
        content = content.strip()
        for kw in sorted(keywords, key=len, reverse=True):
            if content == kw:
                return kw
            if content.startswith(kw):
                rest = content[len(kw):]
                if not rest or rest[0] in ' ：:（(' or '\u4e00' <= rest[0] <= '\u9fff' or rest[0].isalpha():
                    return kw
        return ''

    def _format_brackets(self, source: str) -> str:
        """括号内空格格式化：去除括号内多余空格"""
        # 去除左括号后的空格
        source = re.sub(r'([（(])\s+', r'\1', source)
        # 去除右括号前的空格
        source = re.sub(r'\s+([）)])', r'\1', source)
        # 确保函数调用括号前无空格
        source = re.sub(r'\s+([（(])', r'\1', source)
        return source

    def _format_function_signature(self, source: str) -> str:
        """格式化函数签名：长参数列表自动换行"""
        lines = source.split('\n')
        result = []

        for line in lines:
            stripped = line.rstrip()
            if not stripped:
                result.append('')
                continue

            # 检查函数定义行是否过长
            if len(stripped) > self.max_line_length:
                func_match = re.match(r'(\s*)(?:段|函|函数|段落)\s+(\S+)\s*\(([^)]*)\)\s*[：:]?', stripped)
                if func_match:
                    indent = func_match.group(1)
                    fname = func_match.group(2)
                    params_str = func_match.group(3).strip()

                    if params_str and len(params_str) > 30:
                        # 拆分为多行参数
                        params = re.split(r'[,，]\s*', params_str)
                        new_line = f'{indent}段 {fname}('
                        result.append(new_line)
                        inner_indent = indent + ' ' * self.indent_size
                        for i, param in enumerate(params):
                            comma = ',' if i < len(params) - 1 else ''
                            result.append(f'{inner_indent}{param}{comma}')
                        result.append(f'{indent})：')
                        continue

            result.append(stripped)

        return '\n'.join(result)

    def _format_trailing_commas(self, source: str) -> str:
        """去除函数调用/定义中多余的尾随逗号"""
        lines = source.split('\n')
        result = []
        for line in lines:
            stripped = line.rstrip()
            # 去除括号/方括号内最后一个逗号（保持元组语义）
            # 去除 ,) → ), ,] → ], ,】 → 】, ,）→ ）
            stripped = re.sub(r',\s*([)\]）】])', r'\1', stripped)
            result.append(stripped)
        return '\n'.join(result)

    def _format_multi_line_statements(self, source: str) -> str:
        """处理多行语句：确保续行有正确缩进"""
        lines = source.split('\n')
        result = []
        in_continuation = False
        continuation_indent = 0

        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if not stripped:
                result.append('')
                in_continuation = False
                continue

            if in_continuation:
                # 续行，保持缩进
                content = stripped.strip()
                result.append(' ' * continuation_indent + content)
                # 检查是否续行结束
                if content.endswith(')') or content.endswith('）') or content.endswith(';'):
                    in_continuation = False
            else:
                indent = len(line) - len(line.lstrip())
                content = stripped.strip()

                # 检测续行：以运算符结尾或括号未闭合
                if (content.endswith(',') or content.endswith('\\') or
                    content.rstrip().endswith(('+', '-', '*', '/', '|', '&', '，'))):
                    in_continuation = True
                    continuation_indent = indent + self.indent_size
                elif content.count('(') > content.count(')') or content.count('（') > content.count('）'):
                    in_continuation = True
                    continuation_indent = indent + self.indent_size

                result.append(stripped)

        return '\n'.join(result)

    def check(self, source: str) -> List[Dict]:
        """检查格式问题，返回差异列表"""
        formatted = self.format(source)
        if formatted == source:
            return []

        orig_lines = source.split('\n')
        fmt_lines = formatted.split('\n')
        issues = []
        max_len = max(len(orig_lines), len(fmt_lines))
        for i in range(max_len):
            o = orig_lines[i].rstrip() if i < len(orig_lines) else ''
            f = fmt_lines[i].rstrip() if i < len(fmt_lines) else ''
            if o != f:
                issues.append({'line': i + 1, 'original': o, 'formatted': f})
        return issues


def format_code(source: str, indent_size: int = 4, max_line_length: int = 80) -> str:
    """便捷函数：格式化光明代码"""
    formatter = LightFormatter(indent_size, max_line_length)
    return formatter.format(source)


def check_format(source: str, indent_size: int = 4, max_line_length: int = 80) -> List[Dict]:
    """便捷函数：检查格式问题"""
    formatter = LightFormatter(indent_size, max_line_length)
    return formatter.check(source)