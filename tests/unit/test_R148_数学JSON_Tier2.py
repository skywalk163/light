# -*- coding: utf-8 -*-
"""R148-C：Tier2 纯 .light 统计函数族 + JSON 高级工具 三腿对拍。

口径：经 _light_import_hook 加载 stdlib/统计.light（纯光明）、stdlib/JSON核心.light（纯光明），
与 stdlib/数学.py（参考实现，薄包装 statistics 模块）及 Python 内联参考实现语义对拍。

三腿说明：本文件覆盖 src 腿（hook 解释执行 .light）对拍 Python 参考；native 腿由
bootstrap / native readiness 门禁统一覆盖。

本轮三腿对拍发现并修复：统计.light 众数/多众数 用 `字典获取(频次, v) + 1`（缺省值 None）
导致首次出现的值 `None + 1` 崩溃 —— 已改为 `字典获取(频次, v, 0)`。
"""
import importlib.util
import math
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_REPO, "src"), os.path.join(_REPO, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _light_import_hook  # noqa: E402

_STDLIB = os.path.join(_REPO, "stdlib")
_light_import_hook.install([os.path.abspath(_STDLIB)])

sys.dont_write_bytecode = True


def _load_py(name):
    """按绝对路径加载 .py 参考实现（避开 hook 对同名模块的接管）。"""
    spec = importlib.util.spec_from_file_location(
        name + "_py_ref", os.path.join(_STDLIB, name + ".py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def stat():
    import 统计 as m
    return m


@pytest.fixture()
def math_ref():
    return _load_py("数学")


# ---------- 统计函数族（统计.light vs 数学.py） ----------

_DATASETS = [
    [1, 2, 3, 4],
    [2, 4, 4, 4, 5, 5, 7, 9],
    [0.5, 1.5, 2.5, 3.5],
    [10],
    [3, 1, 4, 1, 5, 9, 2, 6],
]


@pytest.mark.parametrize("data", _DATASETS)
def test_均值(stat, math_ref, data):
    assert stat.均值(data) == pytest.approx(math_ref.平均数(data))


@pytest.mark.parametrize("data", _DATASETS)
def test_中位数(stat, math_ref, data):
    assert stat.中位数(data) == pytest.approx(math_ref.中位数(data))


@pytest.mark.parametrize("data", _DATASETS)
def test_方差(stat, math_ref, data):
    assert stat.方差(data) == pytest.approx(math_ref.方差(data))


# 样本方差/样本标准差：n=1 时 Python statistics 抛 StatisticsError，而 light 口径返回 0.0
# （已知边界分歧，见下 test_样本方差_单元素边界）。对拍仅覆盖 n>=2 的数据集。
_DATASETS_SAMPLE = [d for d in _DATASETS if len(d) >= 2]


@pytest.mark.parametrize("data", _DATASETS_SAMPLE)
def test_样本方差(stat, math_ref, data):
    assert stat.样本方差(data) == pytest.approx(math_ref.样本方差(data))


@pytest.mark.parametrize("data", _DATASETS)
def test_标准差(stat, math_ref, data):
    assert stat.标准差(data) == pytest.approx(math_ref.标准差(data))


@pytest.mark.parametrize("data", _DATASETS_SAMPLE)
def test_样本标准差(stat, math_ref, data):
    assert stat.样本标准差(data) == pytest.approx(math_ref.样本标准差(data))


def test_样本方差_单元素边界(stat, math_ref):
    """已知边界分歧：n=1 时 .py 参考抛 RuntimeError(样本数量不足)，light 口径返回 0.0。"""
    assert stat.样本方差([10]) == 0.0
    with pytest.raises(RuntimeError):
        math_ref.样本方差([10])


@pytest.mark.parametrize("data", _DATASETS)
def test_求和(stat, math_ref, data):
    assert stat.求和(data) == math_ref.求和(data)


def test_众数(stat, math_ref):
    data = [1, 2, 2, 3, 3, 3, 4]
    assert stat.众数(data) == math_ref.众数(data)


def test_累积和(stat, math_ref):
    assert stat.累积和([1, 2, 3, 4]) == math_ref.累积和([1, 2, 3, 4])


def _ref_pct(已排序, 百分比):
    n = len(已排序)
    k = (n - 1) * 百分比 / 100.0
    下 = math.floor(k)
    上 = math.ceil(k)
    if 下 == 上:
        return 已排序[下]
    return 已排序[下] + (已排序[上] - 已排序[下]) * (k - 下)


def test_四分位数(stat):
    d = [1, 2, 3, 4, 5, 6, 7, 8]
    q = stat.四分位数(d)
    assert len(q) == 3
    assert q[0] == pytest.approx(_ref_pct(d, 25))
    assert q[1] == pytest.approx(_ref_pct(d, 50))
    assert q[2] == pytest.approx(_ref_pct(d, 75))


# ---------- JSON 高级工具（JSON核心.light vs Python 参考） ----------

@pytest.fixture()
def jc():
    import JSON核心 as m
    return m


def _ref_flatten(o, sep="."):
    out = {}

    def rec(cur, prefix):
        if isinstance(cur, dict):
            for k, v in cur.items():
                rec(v, k if prefix == "" else prefix + sep + str(k))
        elif isinstance(cur, list):
            for i, v in enumerate(cur):
                rec(v, prefix + sep + str(i))
        else:
            out[prefix] = cur

    rec(o, "")
    return out


def test_扁平化(jc):
    d = {"a": {"b": 1, "c": [2, 3]}, "d": 4, "e": {"f": {"g": 5}}}
    got = jc.扁平化(d)
    assert got == _ref_flatten(d)
    assert got["a.b"] == 1
    assert got["a.c.0"] == 2
    assert got["e.f.g"] == 5


def test_过滤字典(jc):
    d = {"a": 1, "b": 2, "c": 3, "d": 4}
    got = jc.过滤字典(d, ["a", "c"])
    assert got == {"a": 1, "c": 3}
    assert "b" not in got and "d" not in got


def test_分组(jc):
    rows = [
        {"k": "x", "v": 1},
        {"k": "x", "v": 2},
        {"k": "y", "v": 3},
        {"k": "y", "v": 4},
    ]
    got = jc.分组(rows, "k")
    assert set(got.keys()) == {"x", "y"}
    assert len(got["x"]) == 2 and len(got["y"]) == 2
    assert got["x"][0]["v"] == 1
