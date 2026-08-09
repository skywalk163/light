# -*- coding: utf-8 -*-
"""
光明运行时错误信息友好化测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from error_formatter import (
    LightErrorFormatter,
    format_runtime_error,
    run_with_friendly_error,
    LIGHT_EXCEPTION_MAP,
)


class TestExceptionTypeMapping:
    """测试异常类型映射"""

    def test_all_common_exceptions_mapped(self):
        """测试常见异常都被映射"""
        common = ['NameError', 'TypeError', 'ValueError', 'IndexError',
                  'KeyError', 'AttributeError', 'ZeroDivisionError']
        for exc_name in common:
            assert exc_name in LIGHT_EXCEPTION_MAP


class TestFormatter:
    """测试格式化器"""

    def test_chinese_exc_name(self):
        """测试英文异常名转中文"""
        f = LightErrorFormatter()
        assert f._chinese_exc_name('NameError') == '变量未定义'
        assert f._chinese_exc_name('ZeroDivisionError') == '除零错误'
        assert f._chinese_exc_name('UnknownError') == 'UnknownError'

    def test_zero_division_error(self):
        """测试除零错误"""
        source = '设 x 为 1 / 0'
        try:
            eval("1 / 0")
        except ZeroDivisionError:
            result = format_runtime_error(source)
            assert '除零错误' in result
            assert 'ZeroDivisionError' in result
            assert '除数是否为零' in result

    def test_name_error(self):
        """测试未定义变量错误"""
        source = '设 x 为 未定义变量'
        try:
            eval("undefined_var_xyz")
        except NameError as e:
            result = format_runtime_error(source, type(e), e, e.__traceback__)
            assert '变量未定义' in result
            assert '拼写' in result

    def test_type_error(self):
        """测试类型错误"""
        source = '"hello" + 1'
        try:
            eval("'hello' + 1")
        except TypeError as e:
            result = format_runtime_error(source, type(e), e, e.__traceback__)
            assert '类型错误' in result

    def test_index_error(self):
        """测试索引越界"""
        source = 'lst[10]'
        try:
            eval("[1,2,3][10]")
        except IndexError as e:
            result = format_runtime_error(source, type(e), e, e.__traceback__)
            assert '索引越界' in result
            assert '长度' in result

    def test_attribute_error(self):
        """测试属性不存在错误"""
        source = 'p.未知属性'
        try:
            eval("None.nonexistent_attr_xyz")
        except AttributeError as e:
            result = format_runtime_error(source, type(e), e, e.__traceback__)
            assert '属性不存在' in result

    def test_recursion_error(self):
        """测试递归过深"""
        source = '无限递归()'
        try:
            f = lambda: f()
            f()
        except RecursionError as e:
            result = format_runtime_error(source, type(e), e, e.__traceback__)
            assert '递归过深' in result
            assert '递归' in result

    def test_indentation_error(self):
        """测试缩进错误"""
        source = '错误的缩进'
        try:
            compile("def f():\nprint(1)", '<test>', 'exec')
            exec("def f():\nprint(1)")
        except IndentationError as e:
            result = format_runtime_error(source, type(e), e, e.__traceback__)
            assert '缩进错误' in result


class TestRunWithFriendlyError:
    """测试带友好错误的执行"""

    def test_normal_execution(self):
        """测试正常执行"""
        code = "print('hello')"
        exit_code = run_with_friendly_error(code, source=code)
        assert exit_code == 0

    def test_error_execution(self):
        """测试错误执行"""
        code = "1 / 0"
        exit_code = run_with_friendly_error(code, source=code)
        assert exit_code == 1

    def test_filenotfound_error(self):
        """测试文件未找到错误"""
        code = "open('不存在的文件.xyz', 'r')"
        try:
            exec(code)
        except FileNotFoundError:
            pass

        source = "读取文件('不存在的文件.xyz')"
        try:
            eval("open('nonexistent_xyz_abc', 'r')")
        except FileNotFoundError as e:
            result = format_runtime_error(source, type(e), e, e.__traceback__)
            assert '文件未找到' in result
            assert '路径' in result


class TestSourceContext:
    """测试源码上下文显示"""

    def test_source_lines_split(self):
        """测试源码行分割"""
        source = "第1行\n第2行\n第3行"
        f = LightErrorFormatter(source)
        assert f.source_lines == ['第1行', '第2行', '第3行']

    def test_empty_source(self):
        """测试空源码"""
        f = LightErrorFormatter('')
        assert f.source_lines == []


class TestLineMapping:
    """测试行号映射"""

    def test_parse_simple_mapping(self):
        """测试解析简单映射"""
        code = """# LIGHT_SRC:1:第一行
print('hello')
# LIGHT_SRC:5:第五行
print('world')
"""
        f = LightErrorFormatter()
        anchors = f.parse_line_mapping(code)
        assert len(anchors) == 2
        assert anchors['# LIGHT_SRC:1:第一行'] == (1, '第一行')

    def test_full_mapping(self):
        """测试完整映射构建"""
        code = """# LIGHT_SRC:1:第一行
print('a')
print('b')
# LIGHT_SRC:5:第五行
print('c')
"""
        f = LightErrorFormatter()
        mapping = f.build_full_mapping(code)
        # 第一个 anchor 后面到第二个 anchor 都是 1
        # 第二个 anchor 后面到结尾都是 5
        assert 0 in mapping  # anchor 行
        assert 1 in mapping
        assert 2 in mapping  # 第二个 anchor 之后是 5

    def test_empty_mapping(self):
        """测试无映射"""
        f = LightErrorFormatter()
        mapping = f.build_full_mapping("无映射的代码\n第二行")
        assert mapping == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
