# -*- coding: utf-8 -*-
"""
L-055 / L-061 / L-062 修复回归测试

- L-055：`写 f(x)` 裸函数调用实参被丢弃；`写` 要求值必须是字符串——
  扩展 `_try_merge_output_concat` 覆盖单一函数调用实参形态，非字符串值自动 str()。
- L-061：运行时顶层异常 message 与抛出点错配、行号错位——
  修复 enhanced_errors 异常归因，使 message 与行号正确对应抛出位置。
- L-062：`副本` 只接受字典——扩展为支持字典/列表浅拷贝。

运行方式：pytest tests/unit/test_L055_L061_L062.py -v
"""

import io
import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator
from enhanced_errors import format_error


def _compile(code: str) -> str:
    """编译光明源码为 Python 代码"""
    parser = LightParser()
    ast = parser.parse(code)
    if ast is None:
        raise RuntimeError('解析失败: %s' % '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(ast)


def _run(code: str) -> str:
    """编译并运行光明源码，返回标准输出（不含换行归一化前 CR）"""
    py_code = _compile(code)
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(compile(py_code, '<light>', 'exec'), {'__name__': '__main__'})
        return sys.stdout.getvalue().replace('\r\n', '\n')
    finally:
        sys.stdout = old_stdout


def _run_exc(code: str):
    """编译并运行光明源码；抛异常时返回 (异常, py_code)，否则 (None, py_code)"""
    py_code = _compile(code)
    try:
        exec(compile(py_code, '<light>', 'exec'), {'__name__': '__main__'})
        return None, py_code
    except Exception as e:
        return e, py_code


# ===========================================================================
# L-055：写 f(x) 裸函数调用实参被丢弃 / 非字符串值自动 str()
# ===========================================================================
class TestL055WriteFunctionCall:
    def test_write_int_variable_auto_str(self):
        """形态③：写 x（x 为 int）→ 输出 str(x)"""
        out = _run('设 x 为 3\n写 x\n')
        assert out.strip() == '3'

    def test_write_function_call(self):
        """形态②：写 转字符串(3) → 输出 3"""
        out = _run('写 转字符串(3)\n')
        assert out.strip() == '3'

    def test_write_int_concat(self):
        """形态①：写 1 + 2 → 输出 3（不再 TypeError）"""
        out = _run('写 1 + 2\n')
        assert out.strip() == '3'

    def test_write_str_concat_with_var(self):
        """L-045 既有形态不回退：写 "x=" + 标签 → 输出拼接结果"""
        out = _run('设 标签 为 "abc"\n写 "x=" + 标签\n')
        assert out.strip() == 'x=abc'

    def test_write_user_function(self):
        """形态②：写 f(x)（用户函数）→ 输出 str(f(x))"""
        code = ('段落 加倍 接收 n:\n'
                '  返回 n * 2\n\n'
                '写 加倍(21)\n')
        out = _run(code)
        assert out.strip() == '42'


# ===========================================================================
# L-061：顶层异常 message 与抛出点行号归因
# ===========================================================================
class TestL061TopExceptionAttribution:
    _code = ('段落 函数A 接收 x:\n'
             '  设 y 为 x + 1\n'
             '  返回 y\n'
             '\n'
             '段落 主:\n'
             '  设 a 为 函数A(1)\n'
             '  抛出 新建 错误("boom")\n'
             '  设 b 为 2\n'
             '\n'
             '主()\n')

    def test_message_matches_throw_site(self):
        """message 与抛出点对应：输出包含抛出语句文本，而非首行陈旧内容"""
        e, py_code = _run_exc(self._code)
        assert e is not None
        out = format_error(self._code, e, py_code=py_code)
        assert 'boom' in out
        # 抛出点（光明第 7 行）必须出现在归因上下文里
        assert '7   抛出 新建 错误' in out
        # 不得再错位指向首行函数定义
        assert '1 段落 函数A' not in out

    def test_line_number_points_to_throw_statement(self):
        """行号指向抛出语句（第 7 行）而不是后续语句"""
        e, py_code = _run_exc(self._code)
        assert e is not None
        out = format_error(self._code, e, py_code=py_code)
        # 抛出语句行文本在代码片段中
        assert '抛出 新建 错误("boom")' in out
        # 抛出点之后的行（设 b）不应出现在片段内（end 边界除外），这里直接校验
        # 归因行号已映射到抛出语句（第 7 行），而非映射到函数定义（第 5 行）
        # 或后续语句（第 8 行）：片段必须包含第 7 行文本。
        assert '7   抛出' in out


# ===========================================================================
# L-062：副本 支持字典/列表浅拷贝
# ===========================================================================
class TestL062CopyShallow:
    def test_copy_dict(self):
        """副本(字典)：浅拷贝，改副本不影响原字典"""
        code = ('设 原 为 {"a": 1, "b": 2}\n'
                '设 复 为 副本(原)\n'
                '复["a"] 为 9\n'
                '如果 (原["a"] != 1): 抛出 新建 错误("影响原字典")\n'
                '如果 (复["a"] != 9): 抛出 新建 错误("副本未独立")\n'
                '写 "dict-ok"\n')
        out = _run(code)
        assert out.strip() == 'dict-ok'

    def test_copy_list(self):
        """副本(列表)：浅拷贝，改副本不影响原列表（L-062 核心）"""
        code = ('设 原 为 [1, 2, 3]\n'
                '设 复 为 副本(原)\n'
                '复[0] 为 9\n'
                '如果 (原[0] != 1): 抛出 新建 错误("影响原列表")\n'
                '如果 (复[0] != 9): 抛出 新建 错误("副本未独立")\n'
                '如果 (长(复) != 3): 抛出 新建 错误("长度不一致")\n'
                '写 "list-ok"\n')
        out = _run(code)
        assert out.strip() == 'list-ok'

    def test_copy_preserves_length_and_elems(self):
        """副本(列表) 长度与元素保持一致"""
        code = ('设 原 为 [10, 20, 30]\n'
                '设 复 为 副本(原)\n'
                '如果 (长(复) != 3): 抛出 新建 错误("长度错误")\n'
                '如果 (复[1] != 20): 抛出 新建 错误("元素错误")\n'
                '写 "len-ok"\n')
        out = _run(code)
        assert out.strip() == 'len-ok'
