# -*- coding: utf-8 -*-
"""
test_metrics_light.py —— 打分指标原语行为判据（任务 D7 §3.3/§3.4）

覆盖：
- `精确匹配`：字符串逐字相等
- `集合匹配`：多答案——期望列表每一项都被实际覆盖
- `包含`（原 `子串匹配`，§3.4 语义收敛改名）：期望片段是实际的子串
- `正则匹配`：期望模式可被 re.search 命中
- `打分`：按方式分派，未知方式抛异常
- `分位`：与 统计.py:197-213 百分位数 逐百分位相等；反跑插值取整必红
- `批量汇总`：pass-rate / 平均耗时与逐条手算一致；空输入不炸；
  新增 p50/p95/总输入词元/总输出词元/成本估算/失败分类计数；未配置单价时成本留空。

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

from 度量 import 精确匹配, 集合匹配, 包含, 正则匹配, 打分, 批量汇总, 分位
from 测试 import 断言命中
from 统计 import 百分位数


class Test断言命中:
    # 测试框架强化：光明里写出的断言要「断言失败真红、通过真绿」。
    # 反跑改坏点：把 断言命中 改成只返回不抛（吞失败）→ 未命中那三条不抛 → 红。
    def test_hit_returns_true(self):
        assert 断言命中("净利润5.20%", "净利润5.20%", "精确") is True
        assert 断言命中(["A", "B"], ["B"], "集合") is True
        # 注意：框架侧 断言命中 当前仍用「子串」名（§3.4 的 harness 侧改名归 C7），故此处用「子串」。
        assert 断言命中("增长率5.20%", "5.20", "子串") is True
        assert 断言命中("PE 12.30 倍", r"\d+\.\d+", "正则") is True

    def test_miss_raises_assertion_error(self):
        with pytest.raises(AssertionError):
            断言命中("净利润6.6%", "5.20", "子串")
        with pytest.raises(AssertionError):
            断言命中(["A"], ["A", "B"], "集合")
        with pytest.raises(AssertionError):
            断言命中("PE 9.99 倍", r"\d+\.\d{2}\.", "正则")

    def test_unknown_mode_raises_value_error(self):
        with pytest.raises(ValueError):
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


class Test包含SubstringMatch:
    """§3.4 语义收敛：原「子串匹配」改名为「包含」，语义不变（期望片段是实际子串）。"""
    def test_fragment_present(self):
        assert 包含("净利润同比增长5.20%", "5.20") is True

    def test_fragment_absent(self):
        assert 包含("净利润同比增长5.20%", "9.99") is False

    def test_分词点_旧别名_子串_仍可用(self):
        # 打分 的「子串」历史别名保留，收敛后规范名是「包含」；两者都指向 包含。
        assert 打分("净利润同比增长5.20%", "5.20", "子串") is True
        assert 打分("净利润同比增长5.20%", "5.20", "包含") is True


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
        assert 打分("你好世界", "好世", "包含") is True
        assert 打分("温度 25.5C", r"25\.5", "正则") is True

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            打分("a", "a", "不存在的判定")


class Test分位:
    # 与 统计.py:197-213 百分位数 逐百分位相等（3/5/7/100 样本 + 1 样本边界）
    @pytest.mark.parametrize("数据,百分位", [
        ([7.0], 50), ([7.0], 100),
        ([1.0, 2.0, 3.0], 3), ([1.0, 2.0, 3.0], 50), ([1.0, 2.0, 3.0], 95), ([1.0, 2.0, 3.0], 100),
        ([10.0, 20.0, 30.0, 40.0, 50.0], 5), ([10.0, 20.0, 30.0, 40.0, 50.0], 50), ([10.0, 20.0, 30.0, 40.0, 50.0], 95),
        ([3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0], 7), ([3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0], 50), ([3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0], 90),
        (list(range(1, 101)), 3), (list(range(1, 101)), 50), (list(range(1, 101)), 95), (list(range(1, 101)), 99),
    ])
    def test_与_统计py_逐百分位相等(self, 数据, 百分位):
        mine = 分位(数据, 百分位)
        ref = 百分位数(数据, 百分位)
        assert abs(mine - ref) < 1e-9, "分位不一致: 数据=%r 百分位=%d mine=%r ref=%r" % (数据, 百分位, mine, ref)

    def test_反跑_线性插值非取整(self):
        # 95th of [0.1,0.2,0.3]：k=1.9 → 0.2*0.1 + 0.3*0.9 = 0.29；
        # 若插值被改成「取整」（直接取 data[floor(k)]=0.2），此处必红。
        assert abs(分位([0.1, 0.2, 0.3], 95) - 0.29) < 1e-9

    def test_空列表返回0_但不抛(self):
        assert 分位([], 50) == 0


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
        # 新增字段在空输入下也不炸
        assert 出["p50耗时"] == 0
        assert 出["p95耗时"] == 0
        assert 出["总输入词元"] == 0
        assert 出["总输出词元"] == 0
        assert 出["失败分类计数"] == {}

    def test_新增字段_与_token_成本(self):
        入 = [
            {"通过": 1, "耗时": 0.1, "输入词元": 100, "输出词元": 50, "失败分类": ""},
            {"通过": 0, "耗时": 0.2, "输入词元": 200, "输出词元": 80, "失败分类": "超时"},
            {"通过": 1, "耗时": 0.3, "输入词元": 150, "输出词元": 60, "失败分类": ""},
        ]
        # 单价：每千词元（输入 0.01，输出 0.02）
        出 = 批量汇总(入, {"输入": 0.01, "输出": 0.02})
        assert 出["总输入词元"] == 450
        assert 出["总输出词元"] == 190
        # 成本 = 450/1000*0.01 + 190/1000*0.02 = 0.0045 + 0.0038 = 0.0083
        assert abs(出["成本估算"] - 0.0083) < 1e-9
        assert 出["成本说明"] == "已按每千词元单价估算"
        # 失败分类计数：1 个「超时」
        assert 出["失败分类计数"] == {"超时": 1}
        # p50 / p95（耗时 [0.1,0.2,0.3]）
        assert abs(出["p50耗时"] - 0.2) < 1e-9
        assert abs(出["p95耗时"] - 0.29) < 1e-9
        # 既有五字段冻结不变
        assert 出["总数"] == 3
        assert 出["通过数"] == 2
        assert abs(出["通过率"] - 2 / 3) < 1e-9

    def test_未配置单价_成本留空(self):
        出 = 批量汇总([{"通过": 1, "耗时": 0.1}])
        assert 出["成本估算"] == ""
        assert 出["成本说明"] == "未配置单价"
        assert 出["总输入词元"] == 0
        assert 出["失败分类计数"] == {}

    def test_失败分类_缺失归未分类(self):
        入 = [
            {"通过": 0, "耗时": 0.1, "失败分类": "幻觉"},
            {"通过": 0, "耗时": 0.2},  # 无 失败分类 → 未分类
        ]
        出 = 批量汇总(入)
        assert 出["失败分类计数"] == {"幻觉": 1, "未分类": 1}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
