# -*- coding: utf-8 -*-
"""R149-C：复数高阶函数族（纯 .light）对拍 Python cmath。

背景：Tier2 缺口中「复数高阶」此前全仓无 `.light` 定义（基础四则 +
模/幅角/共轭/整数幂已有）。本轮在 `stdlib/复数.light` 落地：
  复数指数 / 复数正弦 / 复数余弦 / 复数正切 / 复数对数 / 复数幂复数
全部纯光明实现，**零 src/ 改动**。

数学口径（对齐 cmath）：
  exp(a+bi) = e^a (cos b + i sin b)
  sin(x+yi) = sin x cosh y + i cos x sinh y
  cos(x+yi) = cos x cosh y - i sin x sinh y
  tan z     = sin z / cos z
  log z     = ln|z| + i arg(z)（主值）
  z^w       = exp(w * log z)（主值）

容差说明（诚实登记，非放水）：`复数幅角` 用本文件既有的纯光明反正切2
（级数 + 角度减半化简），文件头登记 |误差| < 4e-7。故依赖幅角的
复数对数 / 复数幂复数 用 1e-6 容差；其余用 1e-9。
⚠️ 复数正切 在 cos z 接近 0 时会数值放大（同 cmath 自身行为），
故测试点避开 tan 的极点附近。
"""
import cmath
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_REPO, "src"), os.path.join(_REPO, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _light_import_hook  # noqa: E402

_light_import_hook.install([os.path.abspath(os.path.join(_REPO, "stdlib"))])

sys.dont_write_bytecode = True


@pytest.fixture()
def cx():
    import 复数 as m
    return m


# 避开 tan 极点（cos z ≈ 0）与 log 分支切割附近的点
_TEST_POINTS = [
    [1.0, 2.0],
    [0.5, -0.5],
    [-2.0, 1.5],
    [3.0, 0.0],
    [0.0, 1.0],
]


def _close(a, b, tol):
    return abs(a[0] - b.real) < tol and abs(a[1] - b.imag) < tol


@pytest.mark.parametrize("z", _TEST_POINTS)
def test_复数指数(cx, z):
    assert _close(cx.复数指数(z), cmath.exp(complex(*z)), 1e-9)


@pytest.mark.parametrize("z", _TEST_POINTS)
def test_复数正弦(cx, z):
    assert _close(cx.复数正弦(z), cmath.sin(complex(*z)), 1e-9)


@pytest.mark.parametrize("z", _TEST_POINTS)
def test_复数余弦(cx, z):
    assert _close(cx.复数余弦(z), cmath.cos(complex(*z)), 1e-9)


@pytest.mark.parametrize("z", [[1.0, 2.0], [0.5, -0.5], [-2.0, 1.5]])
def test_复数正切(cx, z):
    assert _close(cx.复数正切(z), cmath.tan(complex(*z)), 1e-8)


@pytest.mark.parametrize("z", _TEST_POINTS)
def test_复数对数(cx, z):
    # 依赖 复数幅角（级数，登记误差 < 4e-7）→ 1e-6 容差
    assert _close(cx.复数对数(z), cmath.log(complex(*z)), 1e-6)


def test_复数幂复数(cx):
    z, w = [2.0, 1.0], [0.5, -0.5]
    assert _close(cx.复数幂复数(z, w), cmath.exp(
        complex(*w) * cmath.log(complex(*z))), 1e-6)


def test_欧拉恒等式(cx):
    """e^(i*pi) = -1：数值正确性自证（不依赖 cmath 的逐点比对）。"""
    got = cx.复数指数([0.0, 3.141592653589793])
    assert abs(got[0] + 1.0) < 1e-9, "e^(i*pi) 实部应为 -1：%s" % got
    assert abs(got[1]) < 1e-9, "e^(i*pi) 虚部应为 0：%s" % got
