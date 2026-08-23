# -*- coding: utf-8 -*-
"""
test_metrics_light.py —— 打分指标原语行为判据（C5，M13）

覆盖：
- `精确匹配`：字符串逐字相等
- `集合匹配`：多答案——期望列表每一项都被实际覆盖
- `子串匹配`：期望片段是实际的子串
- `正则匹配`：期望模式可被 re.search 命中
- `打分`：按方式分派，未知方式抛异常
- `批量汇总`：pass-rate / 平均耗时与逐条手算一致；空输入不炸

每条都用「与手算一致的数字 / 明确的真假」判定，反跑改坏点贴在对应用例 docstring。
"""
import os
import sys

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 度量 import 精确匹配, 集合匹配, 子串匹配, 正则匹配, 打分, 批量汇总
from 测试 import 断言命中


class Test断言命中:
    # 测试框架强化（M13）：光明里写出的断言要「断言失败真红、通过真绿」。
    # 反跑改坏点：把 断言命中 改成只返回不抛（吞失败）→ 未命中那三条不抛 → 红。
    def test_hit_returns_true(self):
        assert 断言命中("净利润5.20%", "净利润5.20%", "精确") is True
        assert 断言命中(["A", "B"], ["B"], "集合") is True
        assert 断言命中("增长率5.20%", "5.20", "子串") is True
        assert 断言命中("PE 12.30 倍", r"\d+\.\d+", "正则") is True

    def test_miss_raises_assertion_error(self):
        import pytest as _pytest
        # 未命中必须真红，绝不吃掉失败变假绿
        with _pytest.raises(AssertionError):
            断言命中("净利润6.6%", "5.20", "子串")
        with _pytest.raises(AssertionError):
            断言命中(["A"], ["A", "B"], "集合")
        with _pytest.raises(AssertionError):
            断言命中("PE 9.99 倍", r"\d+\.\d{2}\.", "正则")

    def test_unknown_mode_raises_value_error(self):
        import pytest as _pytest
        with _pytest.raises(ValueError):
            断言命中("x", "x", "不存在的判定")


class TestExactMatch:
    def test_exact_hit_and_miss(self):
        assert 精确匹配("沪深300昨日收涨", "沪深300昨日收涨") is True
        assert 精确匹配("沪深300昨日收涨", "科创50昨日收涨") is False


class TestSetMatch:
    def test_expected_all_covered(self):
        actual = ["基本面", "技术面", "资金面"]
        assert 集合匹配(actual, ["基本面", "资金面"]) is True

    def test_missing_one_expected_fails(self):
        actual = ["基本面"]
        assert 集合匹配(actual, ["基本面", "资金面"]) is False


class TestSubstringMatch:
    def test_fragment_present(self):
        assert 子串匹配("净利润同比增长5.20%", "5.20") is True

    def test_fragment_absent(self):
        assert 子串匹配("净利润同比增长5.20%", "9.99") is False


class TestRegexMatch:
    def test_pattern_searchable(self):
        assert 正则匹配("PE 为 12.30 倍", r"\d+\.\d+") is True

    def test_pattern_absent(self):
        assert 正则匹配("PE 为 12.30 倍", r"9\.\d\d.") is False


class Test打分Dispatch:
    def test_dispatch_by_mode(self):
        # 反跑改坏点：把某方式的结果取反 → 对应子断言红
        assert 打分("x", "x", "精确") is True
        assert 打分(["a", "b"], ["a"], "集合") is True
        assert 打分("你好世界", "好世", "子串") is True
        assert 打分("温度 25.5C", r"25\.5", "正则") is True

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            打分("a", "a", "不存在的判定")


class Test批量汇总:
    def test_pass_rate_and_avg_manual(self):
        入 = [{"通过": 1, "耗时": 0.1}, {"通过": 0, "耗时": 0.2}, {"通过": 1, "耗时": 0.3}]
        出 = 批量汇总(入)
        # 与逐条手算一致
        assert 出["总数"] == 3
        assert 出["通过数"] == 2
        assert abs(出["通过率"] - 2 / 3) < 1e-9
        assert abs(出["总耗时"] - 0.6) < 1e-9
        assert abs(出["平均耗时"] - 0.2) < 1e-9

    def test_all_pass_rate_is_one(self):
        出 = 批量汇总([{"通过": 1, "耗时": 0.1}, {"通过": 1, "耗时": 0.2}])
        assert 出["通过率"] == 1

    def test_empty_input_no_divzero(self):
        出 = 批量汇总([])
        assert 出["总数"] == 0
        assert 出["通过数"] == 0
        assert 出["通过率"] == 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))