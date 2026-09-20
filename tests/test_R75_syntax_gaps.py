# -*- coding: utf-8 -*-
"""
R75 任务B —— G-06 推导式 / G-10 数据类 / G-15 with 三项语法补缺的双后端 parity 与回归测试。

覆盖：
- G-06：列表/字典推导式（已支持，正向 + 字典键括号修复回归）
- G-10：记录类型（R73-C 已支持，正向 + 可哈希验证）
- G-15：with 上下文管理器（R75-B 修复缩进 bug，正向 + 块后语句不被吞）

运行：
    pytest tests/test_R75_syntax_gaps.py -v
"""
import os
import sys

import pytest

# 把 src 加入路径
_SRC = os.path.join(os.path.dirname(__file__), '..', 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _parse(code):
    from light_parser_v3 import LightParser
    return LightParser().parse(code)


def _gen_src(ast):
    from code_generator import PythonCodeGenerator
    return PythonCodeGenerator().generate(ast)


def _gen_unified(ast):
    from code_generator_unified import UnifiedCodeGenerator
    return UnifiedCodeGenerator().generate(ast)


def _run_python(code):
    """编译生成的 Python 代码并执行，返回 stdout。"""
    import io
    import contextlib
    buf = io.StringIO()
    ns = {'__name__': '__main__'}
    with contextlib.redirect_stdout(buf):
        exec(compile(code, '<test>', 'exec'), ns)
    return buf.getvalue()


# ============================================================================
# G-06 推导式
# ============================================================================

class TestG06Comprehension:
    def test_list_comprehension_parity(self):
        """列表推导式两后端产物语义等价。"""
        code = '设 平方 = [x * x 遍历 x 之 范围(1, 4)]\n打印(平方)\n'
        ast = _parse(code)
        src_out = _gen_src(ast)
        uni_out = _gen_unified(ast)
        assert _run_python(src_out).strip() == '[1, 4, 9]'
        assert _run_python(uni_out).strip() == '[1, 4, 9]'

    def test_dict_comprehension_parity(self):
        """字典推导式两后端产物语义等价。"""
        code = '设 表 = {x: x * 2 遍历 x 之 范围(1, 4)}\n打印(表)\n'
        ast = _parse(code)
        src_out = _gen_src(ast)
        uni_out = _gen_unified(ast)
        assert _run_python(src_out).strip() == '{1: 2, 2: 4, 3: 6}'
        assert _run_python(uni_out).strip() == '{1: 2, 2: 4, 3: 6}'

    def test_conditional_comprehension(self):
        """带条件的列表推导式。"""
        code = '设 偶 = [x 遍历 x 之 范围(1, 7) 若 x % 2 == 0]\n打印(偶)\n'
        ast = _parse(code)
        assert _run_python(_gen_src(ast)).strip() == '[2, 4, 6]'

    def test_parenthesized_dict_key_is_expression(self):
        """R75-B 回归：{(变量): 值} 的键必须是变量表达式，不是字符串键。

        L-063 让裸标识符键转字符串（JS 风格），但承诺括号键可用变量作键。
        修复前括号被 parser 丢弃，{(p): 1} 仍生成 {'p': 1}。
        """
        code = ('设 p = "动态键"\n'
                '设 d = {(p): 42}\n'
                '打印(d["动态键"])\n')
        ast = _parse(code)
        src_out = _gen_src(ast)
        uni_out = _gen_unified(ast)
        # 产物中不应出现字符串 'p' 作为键（应是变量 p）
        assert "'p':" not in src_out, 'src 后端：括号键不应转字符串'
        assert "'p':" not in uni_out, 'unified 后端：括号键不应转字符串'
        assert _run_python(src_out).strip() == '42'
        assert _run_python(uni_out).strip() == '42'

    def test_naked_dict_key_still_string(self):
        """L-063 不回归：裸标识符键仍转字符串（JS 风格）。"""
        code = '设 d = {名字: "张三"}\n打印(d["名字"])\n'
        ast = _parse(code)
        src_out = _gen_src(ast)
        assert "'名字':" in src_out, '裸键应转字符串'
        assert _run_python(src_out).strip() == '张三'


# ============================================================================
# G-10 数据类 / 记录类型
# ============================================================================

class TestG10RecordType:
    def test_record_definition_parity(self):
        """记录类型两后端都生成 @dataclass 装饰的类。"""
        code = '记录 点: x, y\n设 p = 点(3, 4)\n打印(p.x, p.y)\n'
        ast = _parse(code)
        src_out = _gen_src(ast)
        uni_out = _gen_unified(ast)
        assert 'dataclass' in src_out, 'src 后端应生成 dataclass'
        assert 'dataclass' in uni_out, 'unified 后端应生成 dataclass'
        assert _run_python(src_out).strip() == '3 4'
        assert _run_python(uni_out).strip() == '3 4'

    def test_record_equality(self):
        """同值记录相等。"""
        code = ('记录 点: x, y\n'
                '设 p1 = 点(1, 2)\n'
                '设 p2 = 点(1, 2)\n'
                '打印(p1 == p2)\n')
        ast = _parse(code)
        assert _run_python(_gen_src(ast)).strip() == 'True'

    def test_record_hashable_in_set(self):
        """记录可哈希，同值在集合中去重。"""
        code = ('记录 点: x, y\n'
                '设 s = {点(1, 2), 点(1, 2), 点(3, 4)}\n'
                '打印(len(s))\n')
        ast = _parse(code)
        assert _run_python(_gen_src(ast)).strip() == '2'

    def test_empty_record_error(self):
        """反向哨兵：空记录必须报中文解析错误。"""
        from errors import ParseError
        with pytest.raises(Exception) as exc_info:
            _parse('记录 空记录:\n')
        # 错误信息应包含中文
        msg = str(exc_info.value)
        assert any('\u4e00' <= c <= '\u9fff' for c in msg), '错误信息应为中文'


# ============================================================================
# G-15 with 上下文管理器
# ============================================================================

class TestG15WithContext:
    def test_with_basic_parity(self):
        """with 基础用法两后端产物语义等价。"""
        code = ('类 追踪:\n'
                '  段落 构造:\n'
                '    己.entered = False\n'
                '    己.exited = False\n'
                '  段落 __enter__:\n'
                '    己.entered = True\n'
                '    返回 己\n'
                '  段落 __exit__ 接收 a, b, c:\n'
                '    己.exited = True\n'
                '    返回 假\n'
                '设 m = 追踪()\n'
                '使用 m 为 实例:\n'
                '  打印(实例.entered)\n'
                '打印(m.exited)\n')
        ast = _parse(code)
        src_out = _gen_src(ast)
        uni_out = _gen_unified(ast)
        assert _run_python(src_out).strip().split() == ['True', 'True']
        assert _run_python(uni_out).strip().split() == ['True', 'True']

    def test_with_body_does_not_swallow_following(self):
        """R75-B 回归：with 块后的语句不应被吞入 with 块。

        修复前 parser 未消耗 INDENT/DEDENT，_parse_body 把后续语句
        错误纳入 with 体，导致 m.exited 在块内检查（恒为 False）。
        """
        code = ('类 追踪:\n'
                '  段落 构造:\n'
                '    己.exited = False\n'
                '  段落 __enter__:\n'
                '    返回 己\n'
                '  段落 __exit__ 接收 a, b, c:\n'
                '    己.exited = True\n'
                '    返回 假\n'
                '设 m = 追踪()\n'
                '使用 m:\n'
                '  打印("in")\n'
                '打印(m.exited)\n')
        ast = _parse(code)
        src_out = _gen_src(ast)
        # 核心验证：如果 with 块吞掉了后续语句，打印(m.exited) 会在块内
        # 执行（此时 exited 仍为 False），输出 "in False"；正确行为是 "in True"。
        result = _run_python(src_out).strip().split()
        assert result == ['in', 'True'], (
            'with 块后语句被吞入块内：输出 %s（期望 ["in", "True"]）' % result)

    def test_without_variable(self):
        """不绑定变量的 with。"""
        code = ('类 追踪:\n'
                '  段落 构造:\n'
                '    己.exited = False\n'
                '  段落 __enter__:\n'
                '    返回 己\n'
                '  段落 __exit__ 接收 a, b, c:\n'
                '    己.exited = True\n'
                '    返回 假\n'
                '设 m = 追踪()\n'
                '使用 m:\n'
                '  打印("x")\n'
                '打印(m.exited)\n')
        ast = _parse(code)
        assert _run_python(_gen_src(ast)).strip().split() == ['x', 'True']

    def test_with_missing_expr_error(self):
        """反向哨兵：`使用:` 缺少表达式必须报中文解析错误。"""
        with pytest.raises(Exception) as exc_info:
            _parse('使用:\n  打印(1)\n')
        msg = str(exc_info.value)
        assert any('\u4e00' <= c <= '\u9fff' for c in msg), '错误信息应为中文'
