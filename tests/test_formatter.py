# -*- coding: utf-8 -*-
"""
测试光明代码格式化器

测试覆盖：
- 缩进格式化
- 间距格式化（运算符前后空格）
- 空行控制
- 导入排序
- 注释间距
- 括号间距
- 尾随逗号
- 多行语句
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from formatter.light_formatter import LightFormatter, format_code, check_format


class TestLightFormatter:
    """测试 LightFormatter 类"""

    def setup_method(self):
        self.formatter = LightFormatter(indent_size=4, max_line_length=80)

    # ------------------------------------------------------------------
    # 缩进格式化
    # ------------------------------------------------------------------

    def test_indent_basic(self):
        """测试基本缩进"""
        source = """段 测试():
印("hello")
"""
        expected = """段 测试():
    印("hello")
"""
        result = self.formatter.format(source)
        assert result == expected, f"缩进格式化失败\n期望:\n{expected}\n实际:\n{result}"

    def test_indent_nested(self):
        """测试嵌套缩进"""
        source = """段 测试():
若 真:
印("true")
否:
印("false")
"""
        expected = """段 测试():
    若 真:
        印("true")
    否:
        印("false")
"""
        result = self.formatter.format(source)
        assert result == expected, f"嵌套缩进格式化失败\n期望:\n{expected}\n实际:\n{result}"

    def test_indent_deep_nesting(self):
        """测试深层嵌套缩进"""
        source = """段 测试():
若 真:
若 真:
印("deep")
"""
        expected = """段 测试():
    若 真:
        若 真:
            印("deep")
"""
        result = self.formatter.format(source)
        assert result == expected, f"深层嵌套格式化失败\n期望:\n{expected}\n实际:\n{result}"

    def test_indent_else_keyword(self):
        """测试否则关键字缩进与同级"""
        source = """段 测试():
若 真:
印("true")
否则:
印("false")
"""
        expected = """段 测试():
    若 真:
        印("true")
    否则:
        印("false")
"""
        result = self.formatter.format(source)
        assert result == expected, f"否则缩进格式化失败\n期望:\n{expected}\n实际:\n{result}"

    def test_indent_for_loop(self):
        """测试遍历循环缩进"""
        source = """段 测试():
遍历 i 在 范围(5):
印(i)
"""
        expected = """段 测试():
    遍历 i 在 范围(5):
        印(i)
"""
        result = self.formatter.format(source)
        assert result == expected, f"遍历循环缩进格式化失败\n期望:\n{expected}\n实际:\n{result}"

    # ------------------------------------------------------------------
    # 间距格式化
    # ------------------------------------------------------------------

    def test_operator_spacing(self):
        """测试运算符前后空格"""
        source = """设 x=1+2
设 y =3*4
设 z=5/6
"""
        expected = """设 x = 1 + 2
设 y = 3 * 4
设 z = 5 / 6
"""
        result = self.formatter.format(source)
        assert result == expected, f"运算符间距格式化失败\n期望:\n{expected}\n实际:\n{result}"

    def test_comparison_spacing(self):
        """测试比较运算符前后空格"""
        source = """若 x>5:
若 y<=10:
若 z!=3:
"""
        expected = """若 x > 5:
    若 y <= 10:
        若 z != 3:
"""
        result = self.formatter.format(source)
        assert result == expected, f"比较运算符间距格式化失败\n期望:\n{expected}\n实际:\n{result}"

    # ------------------------------------------------------------------
    # 空行控制
    # ------------------------------------------------------------------

    def test_blank_lines(self):
        """测试空行控制（最多2个连续空行）"""
        source = """段 函1():
    印(1)


段 函2():
    印(2)




段 函3():
    印(3)
"""
        expected = """段 函1():
    印(1)


段 函2():
    印(2)


段 函3():
    印(3)
"""
        result = self.formatter.format(source)
        assert result == expected, f"空行控制失败\n期望:\n{expected}\n实际:\n{result}"

    # ------------------------------------------------------------------
    # 导入排序
    # ------------------------------------------------------------------

    def test_import_block(self):
        """测试导入块识别"""
        source = """引 模块丙
引 模块乙
引 模块甲

段 主():
    印("hello")
"""
        expected = """引 模块丙
引 模块乙
引 模块甲

段 主():
    印("hello")
"""
        result = self.formatter.format(source)
        # 验证导入块被识别（不会和函数体混在一起）
        assert "引 模块" in result
        assert "段 主()" in result

    # ------------------------------------------------------------------
    # 注释间距
    # ------------------------------------------------------------------

    def test_comment_spacing(self):
        """测试注释前空格"""
        source = """设 x = 1#这是注释
段 主():
    印(1)#打印
"""
        expected = """设 x = 1  #这是注释
段 主():
    印(1)  #打印
"""
        result = self.formatter.format(source)
        assert result == expected, f"注释间距格式化失败\n期望:\n{expected}\n实际:\n{result}"

    # ------------------------------------------------------------------
    # 行尾空白
    # ------------------------------------------------------------------

    def test_trailing_whitespace(self):
        """测试行尾空白去除"""
        source = """段 测试():   
    印("hello")   
"""
        expected = """段 测试():
    印("hello")
"""
        result = self.formatter.format(source)
        assert result == expected, f"行尾空白去除失败\n期望:\n{expected}\n实际:\n{result}"

    # ------------------------------------------------------------------
    # 括号间距
    # ------------------------------------------------------------------

    def test_bracket_spacing(self):
        """测试括号内空格去除"""
        source = """段 测试( 参数 ):
    印( "hello" )
"""
        expected = """段 测试(参数):
    印("hello")
"""
        result = self.formatter.format(source)
        assert result == expected, f"括号间距格式化失败\n期望:\n{expected}\n实际:\n{result}"

    # ------------------------------------------------------------------
    # 便捷函数
    # ------------------------------------------------------------------

    def test_format_code_function(self):
        """测试便利函数 format_code"""
        source = "段 测试():\n印(1)\n"
        result = format_code(source)
        assert "段 测试()" in result

    def test_check_format_function(self):
        """测试便利函数 check_format"""
        source = "段 测试():\n    印(1)\n"
        issues = check_format(source)
        assert isinstance(issues, list)

    # ------------------------------------------------------------------
    # 完整格式化流程
    # ------------------------------------------------------------------

    def test_complete_format(self):
        """测试完整格式化流程"""
        source = """段 测试():
    若 真:
        印("hello")
        印("world")
    否:
        印("false")
"""
        result = self.formatter.format(source)
        # 格式化后应保持不变（已经是正确格式）
        assert result == source, f"完整格式化失败\n期望:\n{source}\n实际:\n{result}"

    def test_format_with_trailing_commas(self):
        """测试尾随逗号去除"""
        source = """段 测试():
    设 列表 = [1, 2, 3,]
    印(列表)
"""
        expected = """段 测试():
    设 列表 = [1, 2, 3]
    印(列表)
"""
        result = self.formatter.format(source)
        assert result == expected, f"尾随逗号格式化失败\n期望:\n{expected}\n实际:\n{result}"

    def test_format_long_function_signature(self):
        """测试长函数签名格式化"""
        long_params = ", ".join([f"参数{i}" for i in range(20)])
        source = f"段 测试({long_params}):\n    印(1)\n"
        result = self.formatter.format(source)
        assert "段 测试" in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])