"""
统计函数增强模块 - 对 contrib/统计函数.light 的补充
新增能力：
1. 百分位数（别名，和分位数语义等价，百分位 0-100）
2. Z分数标准化（对每个数据点算 (x-均值)/标准差）
3. 简单线性回归（最小二乘，返回 {斜率/截距/预测函数/R²/SST/SSE}，以及预测值）
4. T分数（Z*10+50，教育/心理测量常用）
5. 四分位异常值检测（1.5 IQR 法则返回 {异常值索引, 下界, 上界}）
"""
from __future__ import annotations
import math
from typing import List, Dict, Any, Tuple, Callable


def _ensure_non_empty(数据: List[float]) -> None:
    if not 数据:
        raise ValueError("数据不能为空")


# 复用 contrib.统计函数.light 里的 Python 版本（独立运行 fallback 内嵌）
def _fallback_mean(数据: List[float]) -> float:
    return sum(数据) / len(数据)


def _fallback_var(数据: List[float], 总体: bool = True) -> float:
    n = len(数据)
    if n <= 1:
        return 0.0
    m = _fallback_mean(数据)
    s2 = sum((x - m) ** 2 for x in 数据)
    return s2 / n if 总体 else s2 / (n - 1)


def _fallback_std(数据: List[float], 总体: bool = True) -> float:
    return math.sqrt(_fallback_var(数据, 总体))


def _fallback_q(数据: List[float], 分位: float) -> float:
    """分位数：0 <= 分位 <= 1"""
    xs = sorted(数据)
    n = len(xs)
    if n == 0:
        raise ValueError("数据不能为空")
    if 分位 < 0 or 分位 > 1:
        raise ValueError("分位必须在 0~1 之间，百分位请用百分位数(p)")
    pos = (n - 1) * 分位
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


# ==========================================================
# 1. 百分位数（和分位数等价，输入 0~100）
# ==========================================================

def 百分位数(数据: List[float], p: float) -> float:
    """p 取值 0 ~ 100。百分位 50 = 分位 0.5 = 中位数"""
    if p < 0 or p > 100:
        raise ValueError("百分位必须在 0~100 之间")
    return _fallback_q(数据, p / 100.0)


def 百分等级(数据: List[float], 数值: float) -> float:
    """返回小于等于「数值」的元素占比 ×100，取值 0~100"""
    _ensure_non_empty(数据)
    le = sum(1 for x in 数据 if x <= 数值)
    return 100.0 * le / len(数据)


# ==========================================================
# 2. Z 分数标准化 / T 分数
# ==========================================================

def Z分数(数据: List[float], 总体: bool = False) -> List[float]:
    """对每个数据点 Z_i = (x_i - 均值) / 标准差。默认用样本标准差（总体=False）"""
    _ensure_non_empty(数据)
    m = _fallback_mean(数据)
    s = _fallback_std(数据, 总体)
    if s == 0:
        return [0.0] * len(数据)
    return [(x - m) / s for x in 数据]


def T分数(数据: List[float], 总体: bool = False) -> List[float]:
    """T = Z * 10 + 50，常用于考试/心理测量标准化"""
    zs = Z分数(数据, 总体)
    return [z * 10 + 50 for z in zs]


# ==========================================================
# 3. 简单线性回归（最小二乘，y = 斜率 * x + 截距）
# ==========================================================

def 线性回归(X: List[float], Y: List[float]) -> Dict[str, Any]:
    """返回 dict：斜率, 截距, R², SST(总平方和), SSE(残差平方和), 预测函数(Callable[[float],float]), 相关系数r"""
    if len(X) != len(Y):
        raise ValueError("X 和 Y 长度必须相等")
    _ensure_non_empty(X)
    n = len(X)
    mx = _fallback_mean(X)
    my = _fallback_mean(Y)
    sxx = sum((x - mx) ** 2 for x in X)
    syy = sum((y - my) ** 2 for y in Y)
    sxy = sum((X[i] - mx) * (Y[i] - my) for i in range(n))
    if sxx == 0:
        return {
            '斜率': 0.0, '截距': my, 'R²': 1.0 if syy == 0 else 0.0,
            'SST': syy, 'SSE': syy,
            '相关系数r': 0.0,
            '预测': (lambda x0: my)
        }
    a = sxy / sxx  # 斜率
    b = my - a * mx  # 截距
    sse = sum((Y[i] - (a * X[i] + b)) ** 2 for i in range(n))
    sst = syy
    r2 = 1 - sse / sst if sst != 0 else 1.0
    r = sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else 0.0

    def _predict(x0: float) -> float:
        return a * x0 + b

    return {
        '斜率': a, '截距': b, 'R²': r2,
        'SST': sst, 'SSE': sse,
        '相关系数r': r,
        '预测': _predict,
    }


def 线性预测(回归结果: Dict[str, Any], x0: float) -> float:
    """更方便的语法糖：预测(x) = 回归结果['预测'](x)"""
    fn: Callable[[float], float] = 回归结果['预测']
    return fn(x0)


# ==========================================================
# 4. 四分位异常值检测（1.5 × IQR 法则）
# ==========================================================

def 异常值检测(数据: List[float], 阈值倍IQR: float = 1.5) -> Dict[str, Any]:
    """返回：{下界,上界,异常值索引[],异常值[],正常值[]}"""
    _ensure_non_empty(数据)
    q1 = _fallback_q(数据, 0.25)
    q3 = _fallback_q(数据, 0.75)
    iqr = q3 - q1
    lo = q1 - 阈值倍IQR * iqr
    hi = q3 + 阈值倍IQR * iqr
    idx: List[int] = []
    bad: List[float] = []
    good: List[float] = []
    for i, x in enumerate(数据):
        if x < lo or x > hi:
            idx.append(i)
            bad.append(x)
        else:
            good.append(x)
    return {'下界': lo, '上界': hi, 'IQR': iqr, 'Q1': q1, 'Q3': q3,
            '异常值索引': idx, '异常值': bad, '正常值': good}
