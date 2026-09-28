# -*- coding: utf-8 -*-
"""LP-D-004 回归：保留字误用导致误导性诊断时，直指「保留字」（LP-D 批次 路1）。

缺陷回顾
--------
`尝试` 是 try 语句关键字。`尝试["次数"] 为 1`（语句头下标目标）被 try 语句
头劫持，报「期望 冒号「:」，但得到 左方括号」并建议"函数定义、条件、循环
后面都需要冒号"——把人往完全错误的方向带。

修复口径（任务书 路1 验收 2，按语料实况收窄）
--------------------------------------------
· 语句头 `<保留字>[...]`（try 头劫持形态）→ 直报
  「『尝试』是保留字（try 语句），不可作标识符」+ 常用保留字清单，不再误导冒号；
· `设 尝试 为 0`（标量计数器）是既有合法用法（examples/harness/编排.light、
  lightharness/src/客户端.light、目标折叠.light；stdlib/re.light 的 `设 类 为 节点[0]`），
  「关键字作名」兼容承重，保持不变——不拦，避免打红存量语料。

反跑判据
--------
· 撤掉 _parse_try_stmt 非 COLON 守卫 → 用例 1 变红（回到「期望冒号」误导）。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest

from parser_core import ParseError  # noqa: E402
from light_parser_v3 import LightParser  # noqa: E402
from keywords import RESERVED_NO_IDENTIFIER, reserved_word_identifier_error  # noqa: E402


def _parse(src: str):
    return LightParser().parse(src)


class Test语句头保留字下标:
    def test_尝试当下标目标_报保留字不误导冒号(self):
        src = (
            "段落 主:\n"
            "  设 尝试 为 [\"次数\": 0]\n"
            "  尝试[\"次数\"] 为 1\n"
        )
        with pytest.raises(ParseError) as ei:
            _parse(src)
        msg = str(ei.value)
        assert '保留字' in msg
        assert '不可作标识符' in msg
        assert '可能缺少冒号' not in msg
        assert '都需要冒号' not in msg

    def test_报错文案含常用保留字清单(self):
        src = "段落 主:\n  尝试[\"x\"] 为 1\n"
        with pytest.raises(ParseError) as ei:
            _parse(src)
        msg = str(ei.value)
        for w in ('捕获', '返回', '遍历', '类'):
            assert w in msg

    def test_正常尝试语句不受影响(self):
        """真 try 语句必须照常解析（不因守卫误伤）。"""
        src = (
            "段落 主:\n"
            "  尝试:\n"
            "    设 甲 为 1\n"
            "  捕获 值异常 e:\n"
            "    设 甲 为 2\n"
            "  返回 甲\n"
        )
        _parse(src)  # 不应抛


class Test既有合法用法不回退:
    def test_设保留字为标量_兼容用法保持(self):
        """`设 尝试 为 0` 是存量语料的重试计数器写法（编排.light 等），
        不得被本修拦下；`尝试 + 1` 表达式位同样照常。"""
        src = (
            "段落 主:\n"
            "  设 尝试 为 0\n"
            "  设 尝试 为 尝试 + 1\n"
            "  打印 字符串(尝试)\n"
            "\n"
            "主()\n"
        )
        LightParser().parse(src)  # 解析必须通过

    def test_设类为_兼容用法保持(self):
        """stdlib/re.light:472 `设 类 为 节点[0]` 是既有合法写法。"""
        src = (
            "段落 主:\n"
            "  设 节点 为 [1, 2]\n"
            "  设 类 为 节点[0]\n"
            "  打印 字符串(类)\n"
            "\n"
            "主()\n"
        )
        LightParser().parse(src)  # 解析必须通过


class Test诊断表:
    def test_清单覆盖任务书16词(self):
        必有 = {'尝试', '捕获', '如果', '段落', '返回', '设', '从', '导入',
                '全局', '导出', '类', '属性', '抛出', '跳出', '遍历', '当'}
        assert 必有 <= set(RESERVED_NO_IDENTIFIER)

    def test_非保留字返回空串(self):
        assert reserved_word_identifier_error('甲') == ''
        assert reserved_word_identifier_error('生成计数') == ''
