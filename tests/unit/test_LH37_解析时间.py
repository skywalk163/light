# -*- coding: utf-8 -*-
"""
LH-37 解析时间默认格式与失败路径（P0 [L-259]）

背景：
  `解析时间` 默认格式只吃空格分隔（%Y-%m-%d %H:%M:%S），遇到 ISO-8601 的 T
  分隔（如 lighthive 租约时间戳 2026-10-30T15:00:00）会静默返回 空；失败路径
  一律 return None，把「格式不对」伪装成「没有时间」，导致后续 时间加减(空, …)
  也得 空，全程无一行报错。

本用例覆盖（T-0211 验收）：
  1. 缺省解析 ISO（T 分隔）文本成功，且 格式化时间 能还原回同一时刻；
  2. 缺省解析空格分隔文本行为不变（存量）；
  3. 解析失败必须抛 ValueError，而不是返回 空；
  4. 试解析时间 失败返回 空 且不抛（显式试探版）；
  5. 反跑：时间加减(解析时间(ISO), 分钟=180) 结果非空（修前这条是 空）。
"""
import os
import sys
import time as _time

import pytest

# conftest 已把 stdlib/ 加进 sys.path；此处兜底保证直跑也可用
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_ROOT, 'stdlib'),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from 时间管理 import (  # noqa: E402
    解析时间,
    试解析时间,
    格式化时间,
    时刻转戳,
    时间加减,
)

_ISO = "%Y-%m-%dT%H:%M:%S"
_空格 = "%Y-%m-%d %H:%M:%S"


class Test缺省格式兼容:
    """验收 1、2：缺省格式同时吃 ISO（T）与空格，行为不回退"""

    def test_缺省解析ISO_T分隔(self):
        时刻 = 解析时间("2026-10-30T15:00:00")
        # 用模块自带的 格式化时间 往返：struct_time → 时间戳 → 字符串；
        # 下一行若 时刻 为空，时刻转戳/格式化时间 必然抛错 ⇒ 失败，信号不减。
        还原 = 格式化时间(_ISO, 时刻转戳(时刻))
        assert 还原 == "2026-10-30T15:00:00"

    def test_缺省解析空格分隔_存量不变(self):
        时刻 = 解析时间("2026-10-30 15:00:00")
        还原 = 格式化时间(_空格, 时刻转戳(时刻))
        assert 还原 == "2026-10-30 15:00:00"

    def test_显式格式仍生效(self):
        # 显式传格式时，只按该格式解析，不偷偷回退到别的格式
        时刻 = 解析时间("2026-10-30T15:00:00", _ISO)
        assert _time.strftime(_ISO, 时刻) == "2026-10-30T15:00:00"

    def test_显式格式_空格文本(self):
        时刻 = 解析时间("2026-10-30 15:00:00", _空格)
        assert _time.strftime(_空格, 时刻) == "2026-10-30 15:00:00"


class Test失败抛异常:
    """验收 3：解析失败抛 ValueError，不再静默返回 空"""

    def test_垃圾文本抛异常(self):
        with pytest.raises(ValueError):
            解析时间("不是时间")

    def test_坏日期抛异常(self):
        # 13 月 / 45 日：显式格式下也必须抛
        with pytest.raises(ValueError):
            解析时间("2026-13-45", "%Y-%m-%d")

    def test_异常信息可读(self):
        # 错误信息应写明原始文本与候选格式，便于排查
        with pytest.raises(ValueError, match="2026-13-45"):
            解析时间("2026-13-45", "%Y-%m-%d")


class Test试解析时间:
    """验收 4：试解析时间 失败返回 空，不抛"""

    def test_垃圾文本返回空(self):
        assert 试解析时间("不是时间") is None

    def test_坏日期返回空(self):
        assert 试解析时间("2026-13-45", "%Y-%m-%d") is None

    def test_有效文本正常返回(self):
        时刻 = 试解析时间("2026-10-30T15:00:00")
        assert _time.strftime(_ISO, 时刻) == "2026-10-30T15:00:00"

    def test_空格文本正常返回(self):
        时刻 = 试解析时间("2026-10-30 15:00:00")
        assert _time.strftime(_空格, 时刻) == "2026-10-30 15:00:00"


class Test静默反跑:
    """验收 5：时间加减(解析时间(ISO), 分钟=180) 结果非空（修前为 空）"""

    def test_ISO解析后加180分钟非空(self):
        时刻 = 解析时间("2026-10-30T15:00:00")
        结果 = 时间加减(时刻, 分钟=180)
        # 15:00 + 180 分钟 = 18:00；结果为空时下一行 strftime 必抛 ⇒ 失败
        assert _time.strftime(_ISO, 结果) == "2026-10-30T18:00:00"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
