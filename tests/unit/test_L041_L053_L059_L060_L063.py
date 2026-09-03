# -*- coding: utf-8 -*-
"""
L-041 / L-053 / L-059 / L-060 / L-063 标识符/关键字/命名缺陷回归测试

- L-041：`字典`/`映射` 等内建前缀名作变量/参数名——已被 lexer 复合词保护
  与关键字降级间接修复，现可正常使用（字典包含键(字典, 键) 等）。
- L-053：`己` 作普通变量名——_map_self_prefix 加 _in_class_method 门禁，
  类外 `设 己 为 …` 正常；类方法内 `己.attr` self 语义保持。
- L-059：`空` = None 是文档化设计决策，非缺陷（测试确认语义稳定）。
- L-060：`函数`/`终` 作变量/参数名——parser_expr 无段名时回退普通标识符；
  函数定义 / 闭包 / 尝试…最终 语义不变。
- L-063：字典字面量裸键自动转字符串键（JS 风格）；引号键 / 推导式 /
  ** 展开不受影响。

运行方式：pytest tests/unit/test_L041_L053_L059_L060_L063.py -v
"""

import io
import os
import sys
import json

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _compile(code: str) -> str:
    """编译光明源码为 Python 代码"""
    parser = LightParser()
    ast = parser.parse(code)
    if ast is None:
        raise RuntimeError('解析失败: %s' % '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(ast)


def _run(code: str) -> str:
    """编译并运行光明源码，返回标准输出"""
    py_code = _compile(code)
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(compile(py_code, '<light>', 'exec'), {'__name__': '__main__'})
        return sys.stdout.getvalue().replace('\r\n', '\n')
    finally:
        sys.stdout = old_stdout


# ===========================================================================
# L-041：字典/映射 作参数名（已被间接修复）
# ===========================================================================
class TestL041DictMappingAsParam:
    def test_dict_param_with_builtin_call(self):
        """`字典` 作参数名 + 字典包含键(字典, 键) 内建调用正常"""
        code = ('从 内置核心字典 导入 字典创建 字典设置 字典包含键\n'
                '段落 主 接收 字典, 键:\n'
                '  字典设置(字典, 键, 1)\n'
                '  写 转字符串(字典包含键(字典, 键))\n'
                '主({}, "a")\n')
        out = _run(code)
        assert out.strip() == 'True'

    def test_mapping_param_index(self):
        """`映射` 作参数名 + 下标访问正常"""
        code = ('段落 主 接收 映射, 键:\n'
                '  写 转字符串(映射[键])\n'
                '主({"a": 1}, "a")\n')
        out = _run(code)
        assert out.strip() == '1'

    def test_dict_param_getitem(self):
        """`字典` 作参数名 + 下标访问正常"""
        code = ('段落 主 接收 字典, 键:\n'
                '  写 转字符串(字典[键])\n'
                '主({"a": 1}, "a")\n')
        out = _run(code)
        assert out.strip() == '1'


# ===========================================================================
# L-053：己 作普通变量名（类外），类内 self 语义保持
# ===========================================================================
class TestL053JiAsNormalVar:
    def test_ji_module_level(self):
        """模块级 `设 己 为 …` → 普通变量"""
        out = _run('设 己 为 42\n写 转字符串(己)\n')
        assert out.strip() == '42'

    def test_ji_in_function(self):
        """函数内 `设 己 为 …` → 普通变量（天干名）"""
        code = ('段落 主:\n'
                '  设 己 为 7\n'
                '  写 转字符串(己)\n'
                '主()\n')
        out = _run(code)
        assert out.strip() == '7'

    def test_ji_as_param(self):
        """`己` 作参数名正常"""
        code = ('段落 主 接收 己:\n'
                '  写 转字符串(己)\n'
                '主(99)\n')
        out = _run(code)
        assert out.strip() == '99'

    def test_ji_class_method_self_semantics(self):
        """类方法内 `己.attr` 仍映射 self（L-053 不回退）"""
        code = ('类 人：\n'
                '  属性 名字。\n'
                '  构造 接收 名字：\n'
                '    己.名字 为 名字。\n'
                '  段落 取名字：\n'
                '    返回 己.名字。\n'
                '段落 主：\n'
                '  设 甲 为 新建 人("小明")。\n'
                '  写 转字符串(甲.取名字())。\n'
                '主()。\n')
        out = _run(code)
        assert out.strip() == '小明'


# ===========================================================================
# L-059：空 = None（文档化设计决策，非缺陷）
# ===========================================================================
class TestL059KongIsNone:
    def test_kong_equals_none(self):
        """`空 == 空` 为真（None 语义）"""
        code = ('设 a 为 空\n设 b 为 空\n写 转字符串(a 等于 b)\n')
        out = _run(code)
        assert out.strip() == 'True'

    def test_kong_not_equal_empty_string(self):
        """`空 == ""` 为假——空串判空须显式 == ""（文档化语义）"""
        code = ('设 a 为 空\n写 转字符串(a 等于 "")\n')
        out = _run(code)
        assert out.strip() == 'False'

    def test_kong_str_is_none(self):
        """`转字符串(空)` → 'None'（Python None 语义）"""
        out = _run('写 转字符串(空)\n')
        assert out.strip() == 'None'


# ===========================================================================
# L-060：终/函数 作变量/参数名（上下文关键字化）
# ===========================================================================
class TestL060ZhongFunctionAsVar:
    def test_zhong_as_var(self):
        """`设 终 为 …` + 读取正常"""
        code = ('段落 主:\n'
                '  设 终 为 5\n'
                '  写 转字符串(终)\n'
                '主()\n')
        out = _run(code)
        assert out.strip() == '5'

    def test_function_as_var(self):
        """`设 函数 为 …` + 读取正常（此前报「函数/段落调用后应跟段名」）"""
        code = ('段落 主:\n'
                '  设 函数 为 3\n'
                '  写 转字符串(函数)\n'
                '主()\n')
        out = _run(code)
        assert out.strip() == '3'

    def test_function_var_in_expr(self):
        """`函数` 作变量参与运算"""
        code = ('段落 主:\n'
                '  设 函数 为 8\n'
                '  写 转字符串(函数 + 2)\n'
                '主()\n')
        out = _run(code)
        assert out.strip() == '10'

    def test_function_as_param(self):
        """`函数` 作参数名正常"""
        code = ('段落 取和 接收 函数, 值:\n'
                '  返回 值\n'
                '段落 主:\n'
                '  写 转字符串(取和(10, 20))\n'
                '主()\n')
        out = _run(code)
        assert out.strip() == '20'

    def test_function_def_unchanged(self):
        """`函数 名(参数):` 函数定义语义不变"""
        code = ('函数 加 接收 a, b:\n'
                '  返回 a + b\n'
                '段落 主:\n'
                '  写 转字符串(加(1, 2))\n'
                '主()\n')
        out = _run(code)
        assert out.strip() == '3'

    def test_closure_unchanged(self):
        """`段落 接收 x:` 匿名闭包语义不变"""
        code = ('段落 主:\n'
                '  设 f 为 段落 接收 x: 返回 x + 1\n'
                '  写 转字符串(f(5))\n'
                '主()\n')
        out = _run(code)
        assert out.strip() == '6'

    def test_try_finally_unchanged(self):
        """`尝试 … 最终:` 异常块语义不变"""
        code = ('段落 主:\n'
                '  尝试:\n'
                '    写 "a"\n'
                '  最终:\n'
                '    写 "b"\n'
                '主()\n')
        out = _run(code)
        assert out.strip() == 'ab'


# ===========================================================================
# L-063：字典字面量裸键自动转字符串键
# ===========================================================================
class TestL063NakedDictKey:
    def test_naked_key_to_string(self):
        """`{追加: [], 落盘: []}` → 键自动转字符串（JS 风格）"""
        code = ('设 录 为 {追加: [], 落盘: []}\n写 序列化JSON(录)\n')
        out = _run(code)
        assert json.loads(out) == {"追加": [], "落盘": []}

    def test_naked_key_no_nameerror(self):
        """裸键不再触发 `name '追加' is not defined`"""
        code = ('段落 主:\n'
                '  设 录 为 {追加: [], 落盘: []}\n'
                '  写 序列化JSON(录)\n'
                '主()\n')
        out = _run(code)
        assert json.loads(out) == {"追加": [], "落盘": []}

    def test_quoted_key_unchanged(self):
        """带引号键不受影响"""
        code = ('设 录 为 {"键": 1, "名": 2}\n写 序列化JSON(录)\n')
        out = _run(code)
        assert json.loads(out) == {"键": 1, "名": 2}

    def test_dict_comprehension_key_unchanged(self):
        """字典推导式键保持变量语义（不受裸键转换影响）"""
        code = ('设 表 为 [1, 2, 3]\n'
                '设 录 为 {x: x * 2 遍历 x 之 表}\n'
                '写 序列化JSON(录)\n')
        out = _run(code)
        # JSON 键恒为字符串；值应为 2/4/6
        assert sorted(json.loads(out).values()) == [2, 4, 6]

    def test_mixed_keys(self):
        """裸键 + 引号键混用"""
        code = ('设 录 为 {追加: [], "已有": 5, 落盘: []}\n写 序列化JSON(录)\n')
        out = _run(code)
        assert json.loads(out) == {"追加": [], "已有": 5, "落盘": []}
