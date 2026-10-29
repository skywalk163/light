# -*- coding: utf-8 -*-
"""
LH-01 时间算术用例：时间加减 / 时间差秒 / 时刻转戳 / 戳转时刻（P1 stdlib 缺口）

背景（lighthive LH-01，2026-10-29 于 light HEAD 5e8d3ecb 复测）：
  `解析时间` 已有，但缺「加减」与「相差」，导致租约到期（到期 = 现在 + 180 分钟）
  和耗时统计（两个时刻差几秒）都得自己 FFI 直连 datetime。

本用例覆盖：
  1. 时间差秒：甲晚于乙为正（180.0），反向为负（-180.0）
  2. 时间加减：分钟参数跨时刻（15:00 + 180 分钟 = 18:00）
  3. 跨月：2026-01-31 + 1 天 = 2026-02-01
  4. 闰日：2028-02-28 + 1 天 = 2028-02-29（闰年）；2026-02-28 + 1 天 = 2026-03-01（平年）
  5. 多参数相加：秒/分钟/小时同时给时相加而不是覆盖
  6. 解析时间解析失败返回 空（None），不抛异常
  7. 时刻转戳 / 戳转时刻 往返一致
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
    时间加减,
    时间差秒,
    时刻转戳,
    戳转时刻,
)

_ISO = "%Y-%m-%dT%H:%M:%S"
_日期 = "%Y-%m-%d"


def _fmt(时刻, 格式=_ISO):
    """struct_time -> 格式串（方便断言）"""
    return _time.strftime(格式, 时刻)


class Test时间差秒:
    """时间差秒：甲晚于乙为正，反向为负"""

    def test_相差180秒(self):
        甲 = 解析时间("2026-10-28T15:03:00", _ISO)
        乙 = 解析时间("2026-10-28T15:00:00", _ISO)
        assert 时间差秒(甲, 乙) == pytest.approx(180.0, abs=1e-6)

    def test_反向为负180(self):
        甲 = 解析时间("2026-10-28T15:03:00", _ISO)
        乙 = 解析时间("2026-10-28T15:00:00", _ISO)
        assert 时间差秒(乙, 甲) == pytest.approx(-180.0, abs=1e-6)

    def test_同一时刻为零(self):
        甲 = 解析时间("2026-10-28T15:00:00", _ISO)
        assert 时间差秒(甲, 甲) == 0.0

    def test_时间戳输入(self):
        # 直接传时间戳（数字）也可
        assert 时间差秒(100.0, 100.0) == 0.0
        assert 时间差秒(120.0, 100.0) == 20.0

    def test_无效输入返回空(self):
        assert 时间差秒("不是时间", 100.0) is None


class Test时间加减:
    """时间加减：对时刻增加/减少指定时间"""

    def test_加180分钟(self):
        结果 = 时间加减(解析时间("2026-10-28T15:00:00", _ISO), 分钟=180)
        assert _fmt(结果) == "2026-10-28T18:00:00"

    def test_跨月(self):
        结果 = 时间加减(解析时间("2026-01-31", _日期), 天=1)
        assert _fmt(结果, _日期) == "2026-02-01"

    def test_闰年闰日(self):
        结果 = 时间加减(解析时间("2028-02-28", _日期), 天=1)
        assert _fmt(结果, _日期) == "2028-02-29"

    def test_平年跨日(self):
        结果 = 时间加减(解析时间("2026-02-28", _日期), 天=1)
        assert _fmt(结果, _日期) == "2026-03-01"

    def test_跨年(self):
        结果 = 时间加减(解析时间("2026-12-31", _日期), 天=1)
        assert _fmt(结果, _日期) == "2027-01-01"

    def test_多参数相加而非覆盖(self):
        结果 = 时间加减(
            解析时间("2026-10-28T15:00:00", _ISO),
            秒=30, 分钟=1, 小时=2,
        )
        # 15:00:00 + 30s + 1min + 2h = 17:01:30
        assert _fmt(结果) == "2026-10-28T17:01:30"

    def test_秒参数(self):
        结果 = 时间加减(解析时间("2026-10-28T15:00:00", _ISO), 秒=45)
        assert _fmt(结果) == "2026-10-28T15:00:45"

    def test_时间戳输入同型返回(self):
        结果 = 时间加减(1000.0, 秒=10)
        assert 结果 == 1010.0

    def test_减天(self):
        结果 = 时间加减(解析时间("2026-03-01", _日期), 天=-1)
        assert _fmt(结果, _日期) == "2026-02-28"

    def test_无效输入返回空(self):
        assert 时间加减("不是时间", 秒=1) is None


class Test时刻转换:
    """时刻转戳 / 戳转时刻 往返"""

    def test_时刻转戳_与戳转时刻往返(self):
        时刻 = 解析时间("2026-10-28T15:00:00", _ISO)
        戳 = 时刻转戳(时刻)
        assert isinstance(戳, float)
        恢复 = 戳转时刻(戳)
        assert isinstance(恢复, _time.struct_time)
        assert _fmt(恢复) == "2026-10-28T15:00:00"

    def test_时间戳直接通过(self):
        assert 时刻转戳(123.45) == 123.45

    def test_无效输入返回空(self):
        assert 时刻转戳("不是时间") is None


class Test解析时间容错:
    """解析时间解析失败返回空，不抛异常（试探型转换约定）"""

    def test_无效字符串返回空(self):
        assert 解析时间("不是时间") is None

    def test_无效字符串指定格式返回空(self):
        assert 解析时间("2026-13-45", "%Y-%m-%d") is None

    def test_有效字符串正常返回(self):
        结果 = 解析时间("2026-10-28T15:00:00", _ISO)
        assert 结果 is not None
        assert _fmt(结果) == "2026-10-28T15:00:00"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
