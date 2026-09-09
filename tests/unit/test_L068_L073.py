# -*- coding: utf-8 -*-
"""
外发任务 D1 — L-068（类方法边界）与 L-073（运行期错误翻译）单元测试。

覆盖：
  * L-073：AttributeError / KeyError / IndexError / TypeError 译文（含「文件:行号」定位，
           以及无 file_path 时回落「第N行」）。
  * L-068：类结束标记（类结束 / 结束类）被解析器消费、其后的段落归为模块级函数；
           模块级函数与某类成员同名 → 编译警告；正常模块级函数不误报。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from enhanced_errors import ErrorFormatter
from light_parser_v3 import LightParser


class TestL073RuntimeTranslation:
    """L-073：运行期 Python 原生异常 → 光明层可读提示"""

    def _fmt(self, err_type, err_msg, line_num=None, file_path=None):
        # 用真实异常对象驱动 _translate_runtime_message，确保 err_type/err_msg 一致。
        fake = type(err_type, (Exception,), {})(err_msg)
        f = ErrorFormatter()
        return f._translate_runtime_message(err_type, err_msg, line_num, file_path)

    def test_attribute_error_with_file_loc(self):
        out = self._fmt('AttributeError',
                        "'测试类' object has no attribute '不存在的方法'",
                        line_num=13, file_path='examples/test_L073.light')
        assert out == "类 测试类 缺少方法/属性 不存在的方法（examples/test_L073.light:13）"

    def test_key_error_with_file_loc(self):
        out = self._fmt('KeyError', "'b'", line_num=15, file_path='examples/test_L073.light')
        assert out == "字典缺少键 'b'（examples/test_L073.light:15）"

    def test_index_error_with_file_loc(self):
        out = self._fmt('IndexError', 'list index out of range',
                        line_num=9, file_path='examples/test_L073.light')
        assert out == "列表索引越界（examples/test_L073.light:9）"

    def test_type_error_unsupported_operand(self):
        out = self._fmt('TypeError',
                        "unsupported operand type(s) for +: 'NoneType' and 'str'",
                        line_num=7, file_path='examples/test_L073.light')
        assert out == "类型错误：不能对 空值 与 字符串 做 加 运算（examples/test_L073.light:7）"

    def test_no_file_path_falls_back_to_line(self):
        # 无 file_path 时回落「第N行」，仍给出可读译文。
        out = self._fmt('AttributeError',
                        "'Web服务端' object has no attribute '处理获取配置'",
                        line_num=42)
        assert out == "类 Web服务端 缺少方法/属性 处理获取配置（第42行）"

    def test_untranslated_type_passthrough(self):
        # 不在 L-073 四类之内的异常，原样返回（不带 loc），绝不改变既有行为。
        out = self._fmt('ValueError', 'invalid literal for int()', line_num=3)
        assert out == "invalid literal for int()"


class TestL068ClassBoundary:
    """L-068：类结束标记 + 模块级函数与类成员同名编译警告"""

    def _parse(self, src):
        p = LightParser()
        mod = p.parse(src, filename='<test_L068>')
        return p, mod

    def test_class_end_marker_consumed(self):
        # 类结束标记应被消费，其后的「段落 主」正确归为模块级函数，不报错。
        src = (
            "类 工具：\n"
            "  属性 名称。\n"
            "  段落 运行 接收：\n"
            "    返回 己名称\n"
            "类结束\n"
            "\n"
            "段落 主 接收：\n"
            "  返回 0\n"
        )
        p, mod = self._parse(src)
        # 解析成功（不抛异常即达标）；且不应产生 L-068 同名碰撞警告。
        assert not any('L-068' in w for w in p.warnings)
        # 顶层应有模块级函数「主」（类已用 类结束 显式闭合）。
        names = [getattr(s, 'name', None) for s in mod.statements]
        assert '主' in names

    def test_alt_end_class_marker(self):
        # 「结束类」双字写法同样应被消费。
        src = (
            "类 工具：\n"
            "  段落 运行 接收：\n"
            "    返回 1\n"
            "结束类\n"
            "\n"
            "段落 主 接收：\n"
            "  返回 0\n"
        )
        p, mod = self._parse(src)
        assert not any('L-068' in w for w in p.warnings)
        names = [getattr(s, 'name', None) for s in mod.statements]
        assert '主' in names

    def test_module_func_vs_class_member_warns(self):
        # 模块级「段落 计算」与类 计算器 的方法「计算」同名 → 编译警告。
        src = (
            "类 计算器：\n"
            "  段落 计算 接收：\n"
            "    返回 42\n"
            "段落 计算 接收：\n"
            "  返回 0\n"
        )
        p, mod = self._parse(src)
        assert any('L-068' in w and '计算' in w for w in p.warnings)

    def test_no_false_positive_for_unrelated_module_func(self):
        # 正常模块级函数（与任何类成员不同名）不应触发警告。
        src = (
            "类 猫：\n"
            "  段落 喵 接收：\n"
            "    返回 \"喵\"\n"
            "段落 狗叫 接收：\n"
            "  返回 \"汪\"\n"
        )
        p, mod = self._parse(src)
        assert not any('L-068' in w for w in p.warnings)


if __name__ == '__main__':
    import pytest
    raise SystemExit(pytest.main([__file__, '-q']))
