# -*- coding: utf-8 -*-
"""LP-D-005 回归：列表/字典可调用方法面（LP-D 批次 路5）。

缺陷回顾
--------
写纯逻辑插件需要三件基础操作——判断值在列表中、两列表去重并集、字典删条目。
仓内 12 插件实测：方法面未文档化，只有一部分方法有可参照用法，另一部分不知道
有没有。于是手写 含于/并入去重，删除退化成「置空软删除」。

· 实测可用但未文档化：`列表.包含(值)`（发射 `值 in 列表`）、
  `字典.弹出(键)`（发射 `键.pop(键)`，真删除）；
· `字典.删除(键)` / `字典.移除(键)` 映射到 list.remove，对 dict 报属性错误
  ——「删除」是列表按值删，字典删键必须用 `.弹出(键)`；
· ⚠️ 软删除陷阱：`字典[键] 为 空` 只是把值置空，**键仍在**，
  `.包含(键)` 依然为真——只判 `.包含` 会把已注销条目当有效，静默错。

路5 修复 = 文档化方法面（docs/LANGUAGE_EXTENSIONS.md §4.5 +
stdlib/内置核心列表.light、内置核心字典.light 头注释）+ 行为测试固化，
**不碰 lexer/parser/codegen**（方法映射本就在 code_generator.py method_name_map）。

反跑判据
--------
· 把 code_generator.py method_name_map 的 `删除` 从 'remove' 改回未映射 →
  用例 4（列表.删除 按值删）变红；
· 文档 §4.5 撤掉「软删除陷阱」警示 → 用例 3 仍然绿（行为由运行时决定），
  故行为侧以用例 1/2/4 为准，陷阱用用例 3 固化现状供文档引用。
"""
import contextlib
import io
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402
from compiler import LightCompiler  # noqa: E402
from code_generator_unified import UnifiedCodeGenerator  # noqa: E402


def _run(src: str, backend: str):
    """用指定后端编译并执行光明源码，返回 (stdout, py_code)。"""
    if backend == 'legacy':
        module = LightParser().parse(src)
        py_code = PythonCodeGenerator().generate(module, is_main=False)
    else:
        result = LightCompiler().compile(src)
        py_code = UnifiedCodeGenerator().generate(result['ast'])
    builtin = types.ModuleType('_light_builtin')
    builtin.打印 = print
    builtin.字符串 = str
    namespace = {'_light_builtin': builtin, '__name__': '_lpd005_test_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lpd005>', 'exec'), namespace)
    return buf.getvalue(), py_code


BACKENDS = ['legacy', 'unified']

# 列表.包含：值在/不在
_列表包含 = (
    "段落 主:\n"
    "  设 名单 为 [\"甲\", \"乙\", \"丙\"]\n"
    "  打印 字符串(名单.包含(\"乙\"))\n"
    "  打印 字符串(名单.包含(\"丁\"))\n"
    "\n"
    "主()\n"
)

# 字典.弹出：真删除（删键）
_字典弹出 = (
    "段落 主:\n"
    "  设 表 为 [\"名字\": \"张三\", \"年龄\": 30]\n"
    "  设 旧值 为 表.弹出(\"年龄\")\n"
    "  打印 字符串(旧值)\n"
    "  打印 字符串(表.包含(\"年龄\"))\n"
    "\n"
    "主()\n"
)

# 软删除陷阱：置空后 .包含 仍为真
_软删除陷阱 = (
    "段落 主:\n"
    "  设 表 为 [\"名字\": \"李四\"]\n"
    "  表[\"名字\"] 为 空\n"
    "  打印 字符串(表.包含(\"名字\"))\n"
    "  打印 字符串(表[\"名字\"] == 空)\n"
    "\n"
    "主()\n"
)

# 列表.删除：按值删（remove），与 .移除 同义
_列表删除 = (
    "段落 主:\n"
    "  设 名单 为 [\"甲\", \"乙\", \"丙\", \"乙\"]\n"
    "  名单.删除(\"乙\")\n"
    "  打印 字符串(长(名单))\n"
    "  打印 字符串(名单.包含(\"丙\"))\n"
    "\n"
    "主()\n"
)


class Test列表包含方法:
    @pytest.mark.parametrize('backend', BACKENDS)
    def test_包含_值在与不在(self, backend):
        out, py = _run(_列表包含, backend)
        lines = out.strip().splitlines()
        assert lines[0].strip() == 'True', py
        assert lines[1].strip() == 'False', py

    @pytest.mark.parametrize('backend', BACKENDS)
    def test_产物发射成员运算而非方法调用(self, backend):
        out, py = _run(_列表包含, backend)
        # `名单.包含("乙")` 应发射为 `("乙" in 名单)` 或 `名单.__contains__(...)`
        assert 'in' in py, py


class Test字典弹出真删除:
    @pytest.mark.parametrize('backend', BACKENDS)
    def test_弹出删键返回旧值(self, backend):
        out, py = _run(_字典弹出, backend)
        lines = out.strip().splitlines()
        assert lines[0].strip() == '30', py
        assert lines[1].strip() == 'False', py

    @pytest.mark.parametrize('backend', BACKENDS)
    def test_弹出后取键不应存在(self, backend):
        out, py = _run(_字典弹出 + "  表.弹出(\"年龄\")\n" * 0, backend)
        assert out.splitlines()[1].strip() == 'False'


class Test软删除陷阱:
    @pytest.mark.parametrize('backend', BACKENDS)
    def test_置空后包含仍为真(self, backend):
        out, py = _run(_软删除陷阱, backend)
        lines = out.strip().splitlines()
        assert lines[0].strip() == 'True', py   # 键还在 → 包含仍真
        assert lines[1].strip() == 'True', py   # 取值 == 空


class Test列表删除方法:
    @pytest.mark.parametrize('backend', BACKENDS)
    def test_删除按值移除首个匹配(self, backend):
        out, py = _run(_列表删除, backend)
        lines = out.strip().splitlines()
        assert lines[0].strip() == '3', py      # 乙 被删一个，剩 3 个
        assert lines[1].strip() == 'True', py


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))