# -*- coding: utf-8 -*-
"""
段言 - 中文错误系统测试

测试 D05（全量中文错误名称映射）和 D06（中文错误附带修改指引）。
"""

import sys
import os
import pytest

# 确保 src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from errors import (
    CHINESE_ERROR_NAMES,
    CHINESE_ERROR_HINTS,
    CHINESE_DUAN_ERROR_HINTS,
    get_chinese_error_name,
    get_chinese_error_hint,
    get_duan_error_hint,
    LightError,
    LexerError,
    SemanticError,
    format_exception,
)


# =============================================================================
# D05: 测试全量中文错误名称映射
# =============================================================================

class TestChineseErrorNames:
    """测试 D05: 中文错误名称映射表"""

    def test_all_20_entries_present(self):
        """验证 20 种标准异常类型全部存在"""
        required_names = {
            'SyntaxError': '语法解析错误',
            'TypeError': '类型错误',
            'ValueError': '值错误',
            'NameError': '名称错误',
            'IndexError': '索引错误',
            'KeyError': '键错误',
            'AttributeError': '属性错误',
            'ImportError': '导入错误',
            'RuntimeError': '运行时错误',
            'ZeroDivisionError': '除零错误',
            'FileNotFoundError': '文件未找到',
            'IOError': '输入输出错误',
            'MemoryError': '内存错误',
            'RecursionError': '递归错误',
            'StopIteration': '迭代停止',
            'AssertionError': '断言错误',
            'NotImplementedError': '未实现错误',
            'OverflowError': '溢出错误',
            'ArithmeticError': '算术错误',
            'LookupError': '查找错误',
        }
        for en, cn in required_names.items():
            assert en in CHINESE_ERROR_NAMES, f"缺少 {en} 的映射"
            assert CHINESE_ERROR_NAMES[en] == cn, \
                f"{en} 的映射应为 '{cn}'，实际为 '{CHINESE_ERROR_NAMES[en]}'"

    def test_get_chinese_error_name(self):
        """测试获取中文错误名称"""
        assert get_chinese_error_name('SyntaxError') == '语法解析错误'
        assert get_chinese_error_name('NameError') == '名称错误'
        assert get_chinese_error_name('TypeError') == '类型错误'
        assert get_chinese_error_name('UnknownError') == 'UnknownError'

    def test_get_chinese_error_name_all(self):
        """测试所有映射条目都能通过 getter 获取"""
        for en, cn in CHINESE_ERROR_NAMES.items():
            assert get_chinese_error_name(en) == cn, f"{en} → {cn} 失败"


# =============================================================================
# D06: 测试中文错误附带修改指引
# =============================================================================

class TestChineseErrorHints:
    """测试 D06: 中文错误修改指引"""

    def test_all_20_hints_present(self):
        """验证 20 种标准异常类型的中文修改指引全部存在"""
        required_hints = {
            'SyntaxError', 'TypeError', 'ValueError', 'NameError',
            'IndexError', 'KeyError', 'AttributeError', 'ImportError',
            'RuntimeError', 'ZeroDivisionError', 'FileNotFoundError',
            'IOError', 'MemoryError', 'RecursionError', 'StopIteration',
            'AssertionError', 'NotImplementedError', 'OverflowError',
            'ArithmeticError', 'LookupError',
        }
        for exc_type in required_hints:
            assert exc_type in CHINESE_ERROR_HINTS, f"缺少 {exc_type} 的修改指引"
            hint = CHINESE_ERROR_HINTS[exc_type]
            assert len(hint) > 0, f"{exc_type} 的修改指引为空"
            assert '请' in hint or '检查' in hint, f"{exc_type} 的修改指引缺少行动指示"

    def test_get_chinese_error_hint(self):
        """测试获取中文错误修改指引"""
        hint = get_chinese_error_hint('SyntaxError')
        assert '💡' in hint
        assert '修改建议' in hint

        hint = get_chinese_error_hint('UnknownError')
        assert hint == ''

    def test_duan_error_hints(self):
        """测试段言特有错误修改指引"""
        # 测试关键字匹配
        assert '设' in CHINESE_DUAN_ERROR_HINTS
        assert '接收' in CHINESE_DUAN_ERROR_HINTS
        assert '如果' in CHINESE_DUAN_ERROR_HINTS

        # 测试 get_duan_error_hint
        hint = get_duan_error_hint('第 3 行的"设"关键字后缺少变量名')
        assert '💡' in hint
        assert '修改建议' in hint
        assert '设' in hint

        hint = get_duan_error_hint('没有匹配关键字的错误消息')
        assert hint == ''


# =============================================================================
# D06: 测试 LightError 自动添加修改指引
# =============================================================================

class TestLightErrorWithHints:
    """测试 LightError 自动集成修改指引"""

    def test_duan_error_with_hint_keyword(self):
        """测试 LightError 自动匹配段言错误提示"""
        # 包含"设"的消息应自动匹配到"设"的指引
        error = LightError('第 3 行的"设"关键字后缺少要定义的变量名', line=3)
        assert '💡' in str(error) or '提示' in str(error)

    def test_duan_error_without_hint(self):
        """测试 LightError 在没有匹配关键字时不添加指引"""
        error = LightError('常规错误', line=1)
        # 不应包含"设"的指引
        assert '设' not in str(error) or '缺少' not in str(error)

    def test_duan_error_with_explicit_hint(self):
        """测试 LightError 显式传入的 hint 不被覆盖"""
        error = LightError('第 5 行的"设"关键字后缺少变量名', line=5, hint='自定义提示')
        assert '自定义提示' in str(error)

    def test_lexer_error_inherits_hints(self):
        """测试 LexerError 继承 LightError 的修改指引功能"""
        error = LexerError('第 1 行的"如果"条件表达式缺少冒号', line=1)
        assert '如果' in str(error) or '冒号' in str(error)

    def test_semantic_error_inherits_hints(self):
        """测试 SemanticError 继承 LightError 的修改指引功能"""
        error = SemanticError('第 10 行使用了未定义的变量"甲"', line=10)
        assert '定义' in str(error) or '变量' in str(error)


# =============================================================================
# D06: 测试 format_exception 集成中文信息
# =============================================================================

class TestFormatExceptionChinese:
    """测试 format_exception 集成中文错误名称和修改指引"""

    def test_format_syntax_error(self):
        """测试 SyntaxError 的格式化输出包含中文名称和指引"""
        try:
            raise SyntaxError("invalid syntax (第 3 行)")
        except SyntaxError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            output = format_exception(exc_type, exc_value, exc_tb)
            assert '语法解析错误' in output
            assert '修改建议' in output

    def test_format_name_error(self):
        """测试 NameError 的格式化输出包含中文名称和指引"""
        try:
            raise NameError("name '甲' is not defined")
        except NameError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            output = format_exception(exc_type, exc_value, exc_tb)
            assert '名称错误' in output
            assert '修改建议' in output

    def test_format_type_error(self):
        """测试 TypeError 的格式化输出包含中文名称和指引"""
        try:
            raise TypeError("类型不匹配: 期望 整数，实际为 文本")
        except TypeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            output = format_exception(exc_type, exc_value, exc_tb)
            assert '类型错误' in output
            assert '修改建议' in output

    def test_format_zero_division_error(self):
        """测试 ZeroDivisionError 的格式化输出包含中文名称和指引"""
        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            output = format_exception(exc_type, exc_value, exc_tb)
            assert '除零错误' in output
            assert '修改建议' in output

    def test_format_file_not_found_error(self):
        """测试 FileNotFoundError 的格式化输出包含中文名称和指引"""
        try:
            raise FileNotFoundError("文件不存在: test.txt")
        except FileNotFoundError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            output = format_exception(exc_type, exc_value, exc_tb)
            assert '文件未找到' in output
            assert '修改建议' in output


# =============================================================================
# D06: 测试中文错误指引的实用性
# =============================================================================

class TestChineseErrorHintQuality:
    """测试中文错误修改指引的实用性和可读性"""

    def test_hints_are_actionable(self):
        """验证所有修改指引都是可操作的"""
        for exc_type, hint in CHINESE_ERROR_HINTS.items():
            # 指引应包含"请"、"检查"等行动指示词
            has_action_word = any(word in hint for word in ['请', '检查', '确认', '确保', '尝试'])
            assert has_action_word, f"{exc_type} 的指引缺乏行动指示词: {hint[:20]}..."

    def test_duan_hints_include_examples(self):
        """验证段言特有指引包含示例或具体说明"""
        for keyword, hint in CHINESE_DUAN_ERROR_HINTS.items():
            has_example_or_detail = any(word in hint for word in ['例如', '必须', '格式', '使用'])
            assert has_example_or_detail, f"{keyword} 的指引缺少示例或具体说明: {hint[:30]}..."

    def test_hint_length_reasonable(self):
        """验证指引长度合理（不太短也不太啰嗦）"""
        for exc_type, hint in CHINESE_ERROR_HINTS.items():
            assert 10 <= len(hint) <= 100, \
                f"{exc_type} 的指引长度 {len(hint)} 不合理: {hint[:30]}..."

    def test_duan_hint_length_reasonable(self):
        """验证段言指引长度合理"""
        for keyword, hint in CHINESE_DUAN_ERROR_HINTS.items():
            assert 10 <= len(hint) <= 80, \
                f"{keyword} 的指引长度 {len(hint)} 不合理: {hint[:30]}..."