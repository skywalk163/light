# -*- coding: utf-8 -*-
"""R99 路 A · 原生 try/catch 语法验收（LP-D-011）

任务书口径（R99_并发开发任务分发书 · 路 A）
------------------------------------------
1. try 块正常返回；
2. 抛错被捕获，错误变量可访问；
3. 未捕获错误向上抛；
4. `尝试` 作变量名（LP-D-004 存量兼容，`设 尝试 为 0` 必须保留）；
5. 嵌套 try/catch。

红线：不放宽现有用例；`尝试` 作 `设` 目标的存量合法写法必须保留。

断言口径：段落内 `设` 出来的是函数局部变量，不会出现在模块命名空间，
所以一律断 `主()` 的返回值（demo 里同时有 打印 佐证副作用路径）。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


def _compile(light_code: str):
    """编译光明代码，返回（全局命名空间，主段落引用）。"""
    module = LightParser().parse(light_code)
    py_code = PythonCodeGenerator().generate(module)
    ns = {}
    exec(py_code, ns)
    return ns, ns["主"]


class Test路A_验收五用例:
    def test_1_try块正常返回(self):
        """try 块无异常时正常走完并返回。"""
        src = (
            "段落 主():\n"
            "  尝试:\n"
            "    设 结果 为 \"正常路径\"\n"
            "    返回 结果\n"
            "  捕获 错误 e:\n"
            "    返回 \"不该进来\"\n"
        )
        _, 主 = _compile(src)
        assert 主() == "正常路径"

    def test_2_抛错被捕获_错误变量可访问(self):
        """抛出 新建 错误 后被捕获，绑定变量 e 拿得到异常消息。"""
        src = (
            "段落 会炸(任务):\n"
            "  抛出 新建 错误(\"炸:\" + 任务)\n"
            "  返回 0\n"
            "\n"
            "段落 主():\n"
            "  尝试:\n"
            "    设 结果 为 会炸(\"批\")\n"
            "  捕获 错误 e:\n"
            "    返回 \"兜住: \" + 字符串(e)\n"
            "  返回 \"没兜住\"\n"
        )
        _, 主 = _compile(src)
        assert 主() == "兜住: 炸:批"

    def test_3_未捕获错误向上抛(self):
        """try/catch 之外的抛错必须向上传播，不能被静默吞掉。"""
        src = (
            "段落 会炸():\n"
            "  抛出 新建 错误(\"无人接\")\n"
            "  返回 0\n"
            "\n"
            "段落 主():\n"
            "  设 无关 为 1\n"
            "  设 结果 为 会炸()\n"
            "  返回 结果\n"
        )
        _, 主 = _compile(src)
        with pytest.raises(Exception) as ei:
            主()
        assert "无人接" in str(ei.value)

    def test_4_尝试作变量名_存量兼容(self):
        """LP-D-004：`设 尝试 为 0` 重试计数器写法必须原样保留。

        兼容口径按 LP-D-004 修复说明收窄：`设 尝试 为 ...`（设 目标）与
        表达式位 `尝试 + 1`、`字符串(尝试)` 是存量语料（编排.light 等）
        的承重写法；`返回 尝试` 等其他语句头的保留字形态不在承诺面内，
        本用例不越界扩权（那是独立的语言决策）。
        """
        src = (
            "段落 主():\n"
            "  设 尝试 为 0\n"
            "  设 尝试 为 尝试 + 1\n"
            "  设 尝试 为 尝试 + 1\n"
            "  设 报告 为 字符串(尝试)\n"
            "  返回 报告\n"
        )
        _, 主 = _compile(src)
        assert 主() == "2"

    def test_5_嵌套try_catch(self):
        """内层捕获后外层走正常路径。"""
        src = (
            "段落 主():\n"
            "  设 记录 为 \"\"\n"
            "  尝试:\n"
            "    尝试:\n"
            "      抛出 新建 错误(\"内层炸\")\n"
            "    捕获 错误 e:\n"
            "      设 记录 为 记录 + \"内层兜:\" + 字符串(e)\n"
            "    设 记录 为 记录 + \";外层续\"\n"
            "  捕获 错误 e:\n"
            "    设 记录 为 记录 + \";外层兜:\" + 字符串(e)\n"
            "  返回 记录\n"
        )
        _, 主 = _compile(src)
        assert 主() == "内层兜:内层炸;外层续"


class Test路A_回归红线:
    def test_真try语句解析不受守卫误伤(self):
        """LP-D-004 守卫只拦「尝试 后无冒号」，真 try 语句照常。"""
        src = (
            "段落 主:\n"
            "  尝试:\n"
            "    设 甲 为 1\n"
            "  捕获 值异常 e:\n"
            "    设 甲 为 2\n"
            "  返回 甲\n"
        )
        LightParser().parse(src)  # 不应抛

    def test_try_catch_finally组合(self):
        """最终 块无论是否抛错都执行。"""
        src = (
            "段落 主():\n"
            "  设 走过 为 \"\"\n"
            "  尝试:\n"
            "    抛出 新建 错误(\"x\")\n"
            "  捕获 错误 e:\n"
            "    设 走过 为 走过 + \"捕\"\n"
            "  最终:\n"
            "    设 走过 为 走过 + \"终\"\n"
            "  返回 走过\n"
        )
        _, 主 = _compile(src)
        assert 主() == "捕终"
