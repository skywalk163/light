"""
统计分析 — lightpub 桥接模块

基于 Python statistics / math / scipy.stats 库封装，函数名对齐上游 duanpub（段言时期）packages/统计分析/源.duan。

上游 duanpub 原始包通过 C FFI 调用数值计算库，
本桥接模块用 Python 标准库 statistics 和 math 模块替代，提供等价的统计分析功能。
"""

import math as _math
import statistics as _stats
import itertools as _itertools
import random as _random
from collections import Counter as _Counter


# =============================================================================
# 基础统计量
# =============================================================================

def 求平均值(数据):
    """求算术平均值"""
    if not 数据:
        raise Exception("求平均值失败: 数据为空")
    try:
        return _stats.mean(数据)
    except Exception as e:
        raise Exception("求平均值失败: " + str(e))


def 求中位数(数据):
    """求中位数"""
    if not 数据:
        raise Exception("求中位数失败: 数据为空")
    try:
        return _stats.median(数据)
    except Exception as e:
        raise Exception("求中位数失败: " + str(e))


def 求众数(数据):
    """求众数（返回出现次数最多的值）"""
    if not 数据:
        raise Exception("求众数失败: 数据为空")
    try:
        return _stats.mode(数据)
    except _stats.StatisticsError:
        # 多个众数时返回第一个
        counter = _Counter(数据)
        max_count = max(counter.values())
        for val, cnt in counter.items():
            if cnt == max_count:
                return val
        raise Exception("求众数失败: 无法计算众数")


def 求标准差(数据, 样本=True):
    """求标准差（样本=True 使用样本标准差，否则总体标准差）"""
    if not 数据:
        raise Exception("求标准差失败: 数据为空")
    if 样本 and len(数据) < 2:
        raise Exception("求标准差失败: 样本至少需要2个元素")
    try:
        return _stats.stdev(数据) if 样本 else _stats.pstdev(数据)
    except Exception as e:
        raise Exception("求标准差失败: " + str(e))


def 求方差(数据, 样本=True):
    """求方差（样本=True 使用样本方差，否则总体方差）"""
    if not 数据:
        raise Exception("求方差失败: 数据为空")
    if 样本 and len(数据) < 2:
        raise Exception("求方差失败: 样本至少需要2个元素")
    try:
        return _stats.variance(数据) if 样本 else _stats.pvariance(数据)
    except Exception as e:
        raise Exception("求方差失败: " + str(e))


def 求偏度(数据):
    """计算偏度（衡量分布不对称性）"""
    if not 数据:
        raise Exception("求偏度失败: 数据为空")
    n = len(数据)
    if n < 3:
        raise Exception("求偏度失败: 至少需要3个数据点")
    try:
        均值 = _stats.mean(数据)
        标准差 = _stats.pstdev(数据)
        if 标准差 == 0:
            return 0.0
        偏度 = sum((x - 均值) ** 3 for x in 数据) / (n * 标准差 ** 3)
        return 偏度
    except Exception as e:
        raise Exception("求偏度失败: " + str(e))


def 求峰度(数据):
    """计算峰度（衡量分布尾部厚度，正态分布峰度为0）"""
    if not 数据:
        raise Exception("求峰度失败: 数据为空")
    n = len(数据)
    if n < 4:
        raise Exception("求峰度失败: 至少需要4个数据点")
    try:
        均值 = _stats.mean(数据)
        标准差 = _stats.pstdev(数据)
        if 标准差 == 0:
            return 0.0
        峰度 = sum((x - 均值) ** 4 for x in 数据) / (n * 标准差 ** 4) - 3
        return 峰度
    except Exception as e:
        raise Exception("求峰度失败: " + str(e))


def 求分位数(数据, 分位):
    """求分位数（0~1 之间的分位值）"""
    if not 数据:
        raise Exception("求分位数失败: 数据为空")
    if not (0 <= 分位 <= 1):
        raise Exception("求分位数失败: 分位必须在0到1之间")
    try:
        排序数据 = sorted(数据)
        n = len(排序数据)
        idx = 分位 * (n - 1)
        lo = int(_math.floor(idx))
        hi = int(_math.ceil(idx))
        if lo == hi:
            return 排序数据[lo]
        return 排序数据[lo] * (hi - idx) + 排序数据[hi] * (idx - lo)
    except Exception as e:
        raise Exception("求分位数失败: " + str(e))


def 求比例分位数(数据, 比例):
    """求比例分位数（同分位数）"""
    return 求分位数(数据, 比例)


def 求极差(数据):
    """求极差（最大值减最小值）"""
    if not 数据:
        raise Exception("求极差失败: 数据为空")
    try:
        return max(数据) - min(数据)
    except Exception as e:
        raise Exception("求极差失败: " + str(e))


def 求四分位距(数据):
    """求四分位距（Q3 - Q1）"""
    if not 数据:
        raise Exception("求四分位距失败: 数据为空")
    if len(数据) < 4:
        raise Exception("求四分位距失败: 至少需要4个数据点")
    try:
        q1 = 求分位数(数据, 0.25)
        q3 = 求分位数(数据, 0.75)
        return q3 - q1
    except Exception as e:
        raise Exception("求四分位距失败: " + str(e))


def 求协方差(数据1, 数据2):
    """计算样本协方差"""
    if len(数据1) != len(数据2):
        raise Exception("求协方差失败: 数据长度不一致")
    if len(数据1) < 2:
        raise Exception("求协方差失败: 至少需要2个数据点")
    try:
        return _stats.covariance(数据1, 数据2)
    except AttributeError:
        # Python < 3.10 回退
        均值1 = _stats.mean(数据1)
        均值2 = _stats.mean(数据2)
        n = len(数据1)
        return sum((x - 均值1) * (y - 均值2) for x, y in zip(数据1, 数据2)) / (n - 1)
    except Exception as e:
        raise Exception("求协方差失败: " + str(e))


def 求相关系数(数据1, 数据2):
    """计算皮尔逊相关系数"""
    if len(数据1) != len(数据2):
        raise Exception("求相关系数失败: 数据长度不一致")
    if len(数据1) < 2:
        raise Exception("求相关系数失败: 至少需要2个数据点")
    try:
        return _stats.correlation(数据1, 数据2)
    except AttributeError:
        # Python < 3.10 回退
        协方差 = 求协方差(数据1, 数据2)
        标准差1 = 求标准差(数据1, 样本=True)
        标准差2 = 求标准差(数据2, 样本=True)
        if 标准差1 == 0 or 标准差2 == 0:
            return 0.0
        return 协方差 / (标准差1 * 标准差2)
    except Exception as e:
        raise Exception("求相关系数失败: " + str(e))


# =============================================================================
# 特殊函数
# =============================================================================

def 阶乘(n):
    """阶乘（n!）"""
    if n < 0:
        raise Exception("阶乘失败: 参数不能为负")
    return _math.factorial(int(n))


def 伽马函数(x):
    """伽马函数"""
    if x <= 0 and x == int(x):
        raise Exception("伽马函数失败: 非正整数无定义")
    return _math.gamma(x)


def 贝塔函数(a, b):
    """贝塔函数 B(a, b)"""
    try:
        return _math.gamma(a) * _math.gamma(b) / _math.gamma(a + b)
    except Exception as e:
        raise Exception("贝塔函数失败: " + str(e))


def 误差函数(x):
    """误差函数"""
    return _math.erf(x)


def 标准正态CDF(x):
    """标准正态分布累积分布函数"""
    return (1.0 + _math.erf(x / _math.sqrt(2.0))) / 2.0


def 标准正态分位数(p):
    """标准正态分布分位数（逆CDF）"""
    if not (0 < p < 1):
        raise Exception("标准正态分位数失败: p 必须在 0 到 1 之间")
    # 使用有理近似（Abramowitz and Stegun 算法）
    if p < 0.5:
        return -_norm_ppf_inner(1 - p)
    return _norm_ppf_inner(p)


def _norm_ppf_inner(p):
    """标准正态分位数内部计算"""
    a1 = -3.969683028665376e+01
    a2 = 2.209460984245205e+02
    a3 = -2.759285104469687e+02
    a4 = 1.383577518672690e+02
    a5 = -3.066479806614716e+01
    a6 = 2.506628277459239e+00

    b1 = -5.447609879822406e+01
    b2 = 1.615858368580409e+02
    b3 = -1.556989798598866e+02
    b4 = 6.680131188771972e+01
    b5 = -1.328068155288572e+01

    c1 = -7.784894002430293e-03
    c2 = -3.223964580411365e-01
    c3 = -2.400758277161838e+00
    c4 = -2.549732539343734e+00
    c5 = 4.374664141464968e+00
    c6 = 2.938163982698783e+00

    d1 = 7.784695709041462e-03
    d2 = 3.224671290700398e-01
    d3 = 2.445134137142996e+00
    d4 = 3.754408661907416e+00

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = _math.sqrt(-2.0 * _math.log(p))
        return (((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + c6) / \
               ((((d1 * q + d2) * q + d3) * q + d4) * q + 1.0)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a1 * r + a2) * r + a3) * r + a4) * r + a5) * r + a6) * q / \
               (((((b1 * r + b2) * r + b3) * r + b4) * r + b5) * r + 1.0)
    else:
        q = _math.sqrt(-2.0 * _math.log(1.0 - p))
        return -(((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + c6) / \
                ((((d1 * q + d2) * q + d3) * q + d4) * q + 1.0)


def 指数(x):
    """指数函数 e^x"""
    try:
        return _math.exp(x)
    except OverflowError:
        raise Exception("指数失败: 溢出")


def tDistCDF(t, df):
    """t分布累积分布函数"""
    if df <= 0:
        raise Exception("tDistCDF失败: 自由度必须大于0")
    x = df / (t * t + df)
    return 1.0 - 0.5 * _math.beta(x, df / 2.0, 0.5) if t >= 0 else 0.5 * _math.beta(x, df / 2.0, 0.5)


def _math_beta_inc(x, a, b):
    """不完全贝塔函数（简化实现）"""
    if x < 0 or x > 1:
        raise Exception("不完全贝塔函数参数越界")
    if x == 0 or x == 1:
        return x
    # 使用连分式法
    return _betainc(x, a, b)


def _betainc(x, a, b):
    """不完全贝塔函数连分式实现"""
    if x == 0.0 or x == 1.0:
        return x
    # 使用正则化不完全贝塔函数的连分式近似
    lbeta = _math.lgamma(a) + _math.lgamma(b) - _math.lgamma(a + b)
    front = _math.exp(_math.log(x) * a + _math.log(1.0 - x) * b - lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(x, a, b) / a
    return 1.0 - front * _betacf(1.0 - x, b, a) / b


def _betacf(x, a, b):
    """不完全贝塔函数的连分式求值"""
    MAX_ITER = 200
    EPS = 3.0e-12
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, MAX_ITER + 1):
        m2 = 2 * m
        # 偶数步
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        # 奇数步
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def 卡方CDF(x, df):
    """卡方分布累积分布函数"""
    if df <= 0:
        raise Exception("卡方CDF失败: 自由度必须大于0")
    if x <= 0:
        return 0.0
    return _math.gamma(df / 2.0) * _betainc(x / 2.0, df / 2.0, 1.0) / _math.gamma(df / 2.0)
    # 简化实现
    return _betainc(x / 2.0, df / 2.0, 1.0)


# =============================================================================
# 矩阵运算
# =============================================================================

def 矩阵转置(矩阵):
    """矩阵转置"""
    if not 矩阵 or not 矩阵[0]:
        raise Exception("矩阵转置失败: 矩阵为空")
    try:
        return [list(row) for row in zip(*矩阵)]
    except Exception as e:
        raise Exception("矩阵转置失败: " + str(e))


def 矩阵乘法(矩阵A, 矩阵B):
    """矩阵乘法"""
    if not 矩阵A or not 矩阵B:
        raise Exception("矩阵乘法失败: 矩阵为空")
    try:
        m, n = len(矩阵A), len(矩阵A[0])
        p = len(矩阵B[0])
        if n != len(矩阵B):
            raise Exception("矩阵乘法失败: 维度不匹配")
        结果 = [[0.0] * p for _ in range(m)]
        for i in range(m):
            for k in range(n):
                aik = 矩阵A[i][k]
                if aik != 0:
                    for j in range(p):
                        结果[i][j] += aik * 矩阵B[k][j]
        return 结果
    except Exception as e:
        raise Exception("矩阵乘法失败: " + str(e))


def 矩阵求逆(矩阵):
    """矩阵求逆（高斯消元法）"""
    if not 矩阵:
        raise Exception("矩阵求逆失败: 矩阵为空")
    n = len(矩阵)
    if n != len(矩阵[0]):
        raise Exception("矩阵求逆失败: 矩阵必须是方阵")
    try:
        aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(矩阵)]
        for i in range(n):
            # 选主元
            pivot = i
            for k in range(i + 1, n):
                if abs(aug[k][i]) > abs(aug[pivot][i]):
                    pivot = k
            if abs(aug[pivot][i]) < 1e-12:
                raise Exception("矩阵求逆失败: 矩阵是奇异的")
            aug[i], aug[pivot] = aug[pivot], aug[i]
            pivot_val = aug[i][i]
            for j in range(2 * n):
                aug[i][j] /= pivot_val
            for k in range(n):
                if k != i:
                    factor = aug[k][i]
                    for j in range(2 * n):
                        aug[k][j] -= factor * aug[i][j]
        return [row[n:] for row in aug]
    except Exception as e:
        raise Exception("矩阵求逆失败: " + str(e))


def 求解线性方程组(A, b):
    """求解线性方程组 Ax = b"""
    if not A or not b:
        raise Exception("求解线性方程组失败: 输入为空")
    try:
        invA = 矩阵求逆(A)
        b_col = [[val] for val in b]
        result = 矩阵乘法(invA, b_col)
        return [row[0] for row in result]
    except Exception as e:
        raise Exception("求解线性方程组失败: " + str(e))


# =============================================================================
# 列表运算
# =============================================================================

def 列表排序(数据, 降序=False):
    """列表排序"""
    try:
        return sorted(数据, reverse=降序)
    except Exception as e:
        raise Exception("列表排序失败: " + str(e))


def 列表和(数据):
    """列表求和"""
    try:
        return sum(数据)
    except Exception as e:
        raise Exception("列表和失败: " + str(e))


def 列表平方和(数据):
    """列表平方和"""
    try:
        return sum(x * x for x in 数据)
    except Exception as e:
        raise Exception("列表平方和失败: " + str(e))


def 平方根(x):
    """平方根"""
    if x < 0:
        raise Exception("平方根失败: 不能对负数求平方根")
    return _math.sqrt(x)


def 描述统计(数据):
    """计算描述统计量，返回包含各项统计值的字典"""
    if not 数据:
        raise Exception("描述统计失败: 数据为空")
    try:
        n = len(数据)
        均值 = _stats.mean(数据)
        方差 = _stats.pvariance(数据) if n > 0 else 0.0
        标准差 = _math.sqrt(方差) if 方差 >= 0 else 0.0
        return {
            'n': n,
            '均值': 均值,
            '中位数': _stats.median(数据),
            '标准差': 标准差,
            '方差': 方差,
            '最小值': min(数据),
            '最大值': max(数据),
            '极差': max(数据) - min(数据),
            '总和': sum(数据),
        }
    except Exception as e:
        raise Exception("描述统计失败: " + str(e))


def 列表去重计数(数据):
    """列表去重计数，返回字典 {值: 次数}"""
    try:
        return dict(_Counter(数据))
    except Exception as e:
        raise Exception("列表去重计数失败: " + str(e))


def 描述统计多列(数据列表, 列名列表=None):
    """对多列数据分别计算描述统计"""
    if not 数据列表:
        raise Exception("描述统计多列失败: 数据为空")
    try:
        结果 = []
        for i, 列 in enumerate(数据列表):
            列名 = 列名列表[i] if 列名列表 and i < len(列名列表) else f'列{i}'
            统计 = 描述统计(列)
            统计['列名'] = 列名
            结果.append(统计)
        return 结果
    except Exception as e:
        raise Exception("描述统计多列失败: " + str(e))


def 频率分布(数据, 组数=None):
    """计算频率分布"""
    if not 数据:
        raise Exception("频率分布失败: 数据为空")
    try:
        n = len(数据)
        min_val = min(数据)
        max_val = max(数据)
        组数 = 组数 or min(int(_math.ceil(_math.sqrt(n))), 50)
        if 组数 <= 0:
            组数 = 1
        组距 = (max_val - min_val) / 组数 if 组数 > 1 and max_val > min_val else 1.0
        bins = []
        for i in range(组数):
            lo = min_val + i * 组距
            hi = lo + 组距
            计数 = sum(1 for x in 数据 if lo <= x < hi or (i == 组数 - 1 and x == max_val))
            bins.append({
                '起始': lo,
                '结束': hi,
                '计数': 计数,
                '频率': 计数 / n,
            })
        return bins
    except Exception as e:
        raise Exception("频率分布失败: " + str(e))


def 交叉表(行数据, 列数据):
    """计算交叉表（列联表）"""
    if len(行数据) != len(列数据):
        raise Exception("交叉表失败: 数据长度不一致")
    try:
        行标签 = sorted(set(行数据))
        列标签 = sorted(set(列数据))
        table = {r: {c: 0 for c in 列标签} for r in 行标签}
        for r, c in zip(行数据, 列数据):
            table[r][c] += 1
        return table
    except Exception as e:
        raise Exception("交叉表失败: " + str(e))


def 计算协方差(数据1, 数据2):
    """计算协方差（同求协方差）"""
    return 求协方差(数据1, 数据2)


def 计算相关系数(数据1, 数据2):
    """计算相关系数（同求相关系数）"""
    return 求相关系数(数据1, 数据2)


def 计算斯皮尔曼相关系数(数据1, 数据2):
    """计算斯皮尔曼等级相关系数"""
    if len(数据1) != len(数据2):
        raise Exception("计算斯皮尔曼相关系数失败: 数据长度不一致")
    if len(数据1) < 3:
        raise Exception("计算斯皮尔曼相关系数失败: 至少需要3个数据点")
    try:
        n = len(数据1)
        def 排名(seq):
            sorted_pairs = sorted(enumerate(seq), key=lambda x: x[1])
            rank = [0] * n
            for i, (idx, _) in enumerate(sorted_pairs):
                rank[idx] = i + 1
            # 处理并列排名
            i = 0
            while i < n:
                j = i
                while j < n and sorted_pairs[j][1] == sorted_pairs[i][1]:
                    j += 1
                if j > i + 1:
                    avg_rank = sum(range(i + 1, j + 1)) / (j - i)
                    for k in range(i, j):
                        rank[sorted_pairs[k][0]] = avg_rank
                i = j
            return rank
        r1 = 排名(数据1)
        r2 = 排名(数据2)
        d_sum = sum((r1[i] - r2[i]) ** 2 for i in range(n))
        return 1 - 6 * d_sum / (n * (n * n - 1))
    except Exception as e:
        raise Exception("计算斯皮尔曼相关系数失败: " + str(e))


def 计算肯德尔相关系数(数据1, 数据2):
    """计算肯德尔秩相关系数"""
    if len(数据1) != len(数据2):
        raise Exception("计算肯德尔相关系数失败: 数据长度不一致")
    if len(数据1) < 2:
        raise Exception("计算肯德尔相关系数失败: 至少需要2个数据点")
    try:
        n = len(数据1)
        一致 = 0
        不一致 = 0
        for i in range(n):
            for j in range(i + 1, n):
                dx = 数据1[i] - 数据1[j]
                dy = 数据2[i] - 数据2[j]
                if dx * dy > 0:
                    一致 += 1
                elif dx * dy < 0:
                    不一致 += 1
        total = 一致 + 不一致
        if total == 0:
            return 0.0
        return (一致 - 不一致) / total
    except Exception as e:
        raise Exception("计算肯德尔相关系数失败: " + str(e))


def 相关矩阵(数据矩阵):
    """计算相关矩阵"""
    if not 数据矩阵 or not 数据矩阵[0]:
        raise Exception("相关矩阵失败: 数据为空")
    try:
        n_cols = len(数据矩阵[0])
        cols = [[row[i] for row in 数据矩阵] for i in range(n_cols)]
        corr = [[0.0] * n_cols for _ in range(n_cols)]
        for i in range(n_cols):
            for j in range(i, n_cols):
                r = 求相关系数(cols[i], cols[j])
                corr[i][j] = r
                corr[j][i] = r
        return corr
    except Exception as e:
        raise Exception("相关矩阵失败: " + str(e))


def 协方差矩阵(数据矩阵):
    """计算协方差矩阵"""
    if not 数据矩阵 or not 数据矩阵[0]:
        raise Exception("协方差矩阵失败: 数据为空")
    try:
        n_cols = len(数据矩阵[0])
        cols = [[row[i] for row in 数据矩阵] for i in range(n_cols)]
        cov = [[0.0] * n_cols for _ in range(n_cols)]
        for i in range(n_cols):
            for j in range(i, n_cols):
                c = 求协方差(cols[i], cols[j])
                cov[i][j] = c
                cov[j][i] = c
        return cov
    except Exception as e:
        raise Exception("协方差矩阵失败: " + str(e))


# =============================================================================
# 概率分布函数
# =============================================================================

def 正态PDF(x, 均值=0, 标准差=1):
    """正态分布概率密度函数"""
    if 标准差 <= 0:
        raise Exception("正态PDF失败: 标准差必须大于0")
    return (1.0 / (_math.sqrt(2 * _math.pi) * 标准差)) * _math.exp(-0.5 * ((x - 均值) / 标准差) ** 2)


def 正态CDF(x, 均值=0, 标准差=1):
    """正态分布累积分布函数"""
    if 标准差 <= 0:
        raise Exception("正态CDF失败: 标准差必须大于0")
    return 标准正态CDF((x - 均值) / 标准差)


def 正态PPF(p, 均值=0, 标准差=1):
    """正态分布分位数函数"""
    if 标准差 <= 0:
        raise Exception("正态PPF失败: 标准差必须大于0")
    return 均值 + 标准差 * 标准正态分位数(p)


def 正态分布(均值=0, 标准差=1, 大小=1):
    """生成正态分布随机数"""
    if 标准差 <= 0:
        raise Exception("正态分布失败: 标准差必须大于0")
    try:
        return [_random.gauss(均值, 标准差) for _ in range(大小)]
    except Exception as e:
        raise Exception("正态分布失败: " + str(e))


def 标准正态分布(大小=1):
    """生成标准正态分布随机数"""
    return 正态分布(0, 1, 大小)


def 均匀分布(下限=0, 上限=1, 大小=1):
    """生成均匀分布随机数"""
    try:
        return [_random.uniform(下限, 上限) for _ in range(大小)]
    except Exception as e:
        raise Exception("均匀分布失败: " + str(e))


def 均匀分布PDF(x, 下限=0, 上限=1):
    """均匀分布概率密度函数"""
    if 下限 >= 上限:
        raise Exception("均匀分布PDF失败: 下限必须小于上限")
    if 下限 <= x <= 上限:
        return 1.0 / (上限 - 下限)
    return 0.0


def 均匀分布CDF(x, 下限=0, 上限=1):
    """均匀分布累积分布函数"""
    if 下限 >= 上限:
        raise Exception("均匀分布CDF失败: 下限必须小于上限")
    if x < 下限:
        return 0.0
    if x > 上限:
        return 1.0
    return (x - 下限) / (上限 - 下限)


def 指数分布(速率=1, 大小=1):
    """生成指数分布随机数"""
    if 速率 <= 0:
        raise Exception("指数分布失败: 速率必须大于0")
    try:
        return [_random.expovariate(速率) for _ in range(大小)]
    except Exception as e:
        raise Exception("指数分布失败: " + str(e))


def 指数分布PDF(x, 速率=1):
    """指数分布概率密度函数"""
    if 速率 <= 0:
        raise Exception("指数分布PDF失败: 速率必须大于0")
    if x < 0:
        return 0.0
    return 速率 * _math.exp(-速率 * x)


def 指数分布CDF(x, 速率=1):
    """指数分布累积分布函数"""
    if 速率 <= 0:
        raise Exception("指数分布CDF失败: 速率必须大于0")
    if x < 0:
        return 0.0
    return 1.0 - _math.exp(-速率 * x)


def 二项分布(n, p, 大小=1):
    """生成二项分布随机数"""
    if n < 0 or not (0 <= p <= 1):
        raise Exception("二项分布失败: 参数无效")
    try:
        return [sum(1 for _ in range(n) if _random.random() < p) for _ in range(大小)]
    except Exception as e:
        raise Exception("二项分布失败: " + str(e))


def 对数(x):
    """自然对数"""
    if x <= 0:
        raise Exception("对数失败: 参数必须大于零")
    return _math.log(x)


def 泊松分布(lam, 大小=1):
    """生成泊松分布随机数"""
    if lam <= 0:
        raise Exception("泊松分布失败: lambda 必须大于0")
    try:
        result = []
        for _ in range(大小):
            L = _math.exp(-lam)
            k = 0
            p = 1.0
            while p > L:
                k += 1
                p *= _random.random()
            result.append(k - 1)
        return result
    except Exception as e:
        raise Exception("泊松分布失败: " + str(e))


def tDist(df, 大小=1):
    """生成t分布随机数"""
    if df <= 0:
        raise Exception("tDist失败: 自由度必须大于0")
    try:
        result = []
        for _ in range(大小):
            z = _random.gauss(0, 1)
            chi2 = sum(_random.gauss(0, 1) ** 2 for _ in range(int(df)))
            result.append(z / _math.sqrt(chi2 / df))
        return result
    except Exception as e:
        raise Exception("tDist失败: " + str(e))


def fDist(df1, df2, 大小=1):
    """生成F分布随机数"""
    if df1 <= 0 or df2 <= 0:
        raise Exception("fDist失败: 自由度必须大于0")
    try:
        result = []
        for _ in range(大小):
            chi2_1 = sum(_random.gauss(0, 1) ** 2 for _ in range(int(df1)))
            chi2_2 = sum(_random.gauss(0, 1) ** 2 for _ in range(int(df2)))
            result.append((chi2_1 / df1) / (chi2_2 / df2))
        return result
    except Exception as e:
        raise Exception("fDist失败: " + str(e))


def 卡方分布(df, 大小=1):
    """生成卡方分布随机数"""
    if df <= 0:
        raise Exception("卡方分布失败: 自由度必须大于0")
    try:
        return [sum(_random.gauss(0, 1) ** 2 for _ in range(int(df))) for _ in range(大小)]
    except Exception as e:
        raise Exception("卡方分布失败: " + str(e))


def 概率分布PDF(分布类型, x, *参数):
    """通用概率分布概率密度函数"""
    if 分布类型 == '正态':
        return 正态PDF(x, *参数)
    elif 分布类型 == '均匀':
        return 均匀分布PDF(x, *参数)
    elif 分布类型 == '指数':
        return 指数分布PDF(x, *参数)
    else:
        raise Exception("概率分布PDF失败: 不支持的分布类型 " + 分布类型)


def 概率分布CDF(分布类型, x, *参数):
    """通用概率分布累积分布函数"""
    if 分布类型 == '正态':
        return 正态CDF(x, *参数)
    elif 分布类型 == '均匀':
        return 均匀分布CDF(x, *参数)
    elif 分布类型 == '指数':
        return 指数分布CDF(x, *参数)
    else:
        raise Exception("概率分布CDF失败: 不支持的分布类型 " + 分布类型)


def 概率分布分位数(分布类型, p, *参数):
    """通用概率分布分位数函数"""
    if 分布类型 == '正态':
        return 正态PPF(p, *参数)
    else:
        raise Exception("概率分布分位数失败: 不支持的分布类型 " + 分布类型)


def 概率分布随机抽样(分布类型, 大小, *参数):
    """通用概率分布随机抽样"""
    if 分布类型 == '正态':
        return 正态分布(*参数, 大小=大小)
    elif 分布类型 == '均匀':
        return 均匀分布(*参数, 大小=大小)
    elif 分布类型 == '指数':
        return 指数分布(*参数, 大小=大小)
    elif 分布类型 == '二项':
        return 二项分布(*参数, 大小=大小)
    elif 分布类型 == '泊松':
        return 泊松分布(*参数, 大小=大小)
    else:
        raise Exception("概率分布随机抽样失败: 不支持的分布类型 " + 分布类型)


# =============================================================================
# 效应量与统计检验
# =============================================================================

def 计算效应量(均值1, 均值2, 标准差1, 标准差2, n1, n2):
    """计算 Cohen's d 效应量"""
    if 标准差1 < 0 or 标准差2 < 0:
        raise Exception("计算效应量失败: 标准差不能为负")
    if n1 < 1 or n2 < 1:
        raise Exception("计算效应量失败: 样本量必须大于0")
    try:
        pooled_std = _math.sqrt(((n1 - 1) * 标准差1 ** 2 + (n2 - 1) * 标准差2 ** 2) / (n1 + n2 - 2))
        if pooled_std == 0:
            return 0.0
        return (均值1 - 均值2) / pooled_std
    except Exception as e:
        raise Exception("计算效应量失败: " + str(e))


def tTestOneSample(数据, mu=0):
    """单样本t检验"""
    if not 数据 or len(数据) < 2:
        raise Exception("tTestOneSample失败: 至少需要2个数据点")
    try:
        n = len(数据)
        均值 = _stats.mean(数据)
        标准差 = _stats.stdev(数据)
        se = 标准差 / _math.sqrt(n)
        t = (均值 - mu) / se if se != 0 else 0.0
        df = n - 1
        # 双尾p值（简化计算）
        p = 2.0 * (1.0 - _t_cdf(abs(t), df))
        return {'t统计量': t, '自由度': df, 'p值': p, '均值': 均值, '标准误': se}
    except Exception as e:
        raise Exception("tTestOneSample失败: " + str(e))


def _t_cdf(t, df):
    """t分布累积分布函数（简化实现）"""
    x = df / (t * t + df)
    return 1.0 - 0.5 * _betainc(x, df / 2.0, 0.5)


def tTestTwoSample(数据1, 数据2):
    """独立双样本t检验"""
    if len(数据1) < 2 or len(数据2) < 2:
        raise Exception("tTestTwoSample失败: 每组至少需要2个数据点")
    try:
        n1, n2 = len(数据1), len(数据2)
        均值1, 均值2 = _stats.mean(数据1), _stats.mean(数据2)
        方差1, 方差2 = _stats.variance(数据1), _stats.variance(数据2)
        # 合并标准误
        sp = _math.sqrt(((n1 - 1) * 方差1 + (n2 - 1) * 方差2) / (n1 + n2 - 2))
        se = sp * _math.sqrt(1.0 / n1 + 1.0 / n2)
        t = (均值1 - 均值2) / se if se != 0 else 0.0
        df = n1 + n2 - 2
        p = 2.0 * (1.0 - _t_cdf(abs(t), df))
        return {'t统计量': t, '自由度': df, 'p值': p, '均值差': 均值1 - 均值2, '标准误': se}
    except Exception as e:
        raise Exception("tTestTwoSample失败: " + str(e))


def tTestPaired(数据1, 数据2):
    """配对t检验"""
    if len(数据1) != len(数据2):
        raise Exception("tTestPaired失败: 数据长度不一致")
    if len(数据1) < 2:
        raise Exception("tTestPaired失败: 至少需要2对数据")
    try:
        差值 = [数据1[i] - 数据2[i] for i in range(len(数据1))]
        return tTestOneSample(差值, 0)
    except Exception as e:
        raise Exception("tTestPaired失败: " + str(e))


def 卡方检验(观测频数, 期望频数=None):
    """卡方检验"""
    if not 观测频数:
        raise Exception("卡方检验失败: 观测频数为空")
    try:
        n = len(观测频数)
        期望 = 期望频数 or [sum(观测频数) / n] * n
        chi2 = sum((o - e) ** 2 / e for o, e in zip(观测频数, 期望) if e > 0)
        df = n - 1
        p = 1.0 - _betainc(chi2 / 2.0, df / 2.0, 1.0) if chi2 > 0 else 1.0
        return {'卡方统计量': chi2, '自由度': df, 'p值': p}
    except Exception as e:
        raise Exception("卡方检验失败: " + str(e))


def 卡方独立性检验(列联表):
    """卡方独立性检验"""
    if not 列联表 or not 列联表[0]:
        raise Exception("卡方独立性检验失败: 列联表为空")
    try:
        rows, cols = len(列联表), len(列联表[0])
        total = sum(sum(row) for row in 列联表)
        行和 = [sum(row) for row in 列联表]
        列和 = [sum(列联表[i][j] for i in range(rows)) for j in range(cols)]
        期望表 = [[行和[i] * 列和[j] / total for j in range(cols)] for i in range(rows)]
        chi2 = 0.0
        for i in range(rows):
            for j in range(cols):
                if 期望表[i][j] > 0:
                    chi2 += (列联表[i][j] - 期望表[i][j]) ** 2 / 期望表[i][j]
        df = (rows - 1) * (cols - 1)
        p = 1.0 - _betainc(chi2 / 2.0, df / 2.0, 1.0) if chi2 > 0 else 1.0
        return {'卡方统计量': chi2, '自由度': df, 'p值': p}
    except Exception as e:
        raise Exception("卡方独立性检验失败: " + str(e))


def fTest(数据1, 数据2):
    """F检验（方差齐性检验）"""
    if len(数据1) < 2 or len(数据2) < 2:
        raise Exception("fTest失败: 每组至少需要2个数据点")
    try:
        方差1, 方差2 = _stats.variance(数据1), _stats.variance(数据2)
        if 方差1 > 方差2:
            f = 方差1 / 方差2
            df1, df2 = len(数据1) - 1, len(数据2) - 1
        else:
            f = 方差2 / 方差1
            df1, df2 = len(数据2) - 1, len(数据1) - 1
        # F分布p值简化
        p = 2.0 * (1.0 - _betainc(df1 * f / (df1 * f + df2), df1 / 2.0, df2 / 2.0))
        return {'F统计量': f, '自由度1': df1, '自由度2': df2, 'p值': p}
    except Exception as e:
        raise Exception("fTest失败: " + str(e))


def 曼惠特尼U检验(数据1, 数据2):
    """曼惠特尼U检验（非参数检验）"""
    if not 数据1 or not 数据2:
        raise Exception("曼惠特尼U检验失败: 数据为空")
    try:
        n1, n2 = len(数据1), len(数据2)
        合并 = sorted([(val, 0) for val in 数据1] + [(val, 1) for val in 数据2])
        r1 = sum(i + 1 for i, (_, g) in enumerate(合并) if g == 0)
        u1 = r1 - n1 * (n1 + 1) / 2
        u2 = n1 * n2 - u1
        u = min(u1, u2)
        mu = n1 * n2 / 2.0
        sigma = _math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
        z = (u - mu) / sigma if sigma > 0 else 0
        p = 2.0 * (1.0 - 标准正态CDF(abs(z)))
        return {'U统计量': u, 'z值': z, 'p值': p}
    except Exception as e:
        raise Exception("曼惠特尼U检验失败: " + str(e))


def 威尔科克森检验(数据1, 数据2=None):
    """威尔科克森符号秩检验"""
    if 数据2 is not None:
        if len(数据1) != len(数据2):
            raise Exception("威尔科克森检验失败: 数据长度不一致")
        差值 = [数据1[i] - 数据2[i] for i in range(len(数据1))]
    else:
        差值 = 数据1
    try:
        nonzero = [d for d in 差值 if d != 0]
        if len(nonzero) < 1:
            raise Exception("威尔科克森检验失败: 无有效数据")
        n = len(nonzero)
        绝对值排名 = sorted([(abs(d), d) for d in nonzero], key=lambda x: x[0])
        ranks = {}
        i = 0
        while i < n:
            j = i
            while j < n and 绝对值排名[j][0] == 绝对值排名[i][0]:
                j += 1
            avg_rank = (i + 1 + j) / 2.0
            for k in range(i, j):
                ranks[绝对值排名[k][1]] = avg_rank
            i = j
        w_plus = sum(rank for d, rank in ranks.items() if d > 0)
        w = min(w_plus, n * (n + 1) / 2 - w_plus)
        mu = n * (n + 1) / 4.0
        sigma = _math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
        z = (w - mu) / sigma if sigma > 0 else 0
        p = 2.0 * (1.0 - 标准正态CDF(abs(z)))
        return {'W统计量': w, 'z值': z, 'p值': p, '有效样本量': n}
    except Exception as e:
        raise Exception("威尔科克森检验失败: " + str(e))


def 柯尔莫哥洛夫检验(数据, 分布='正态', *参数):
    """柯尔莫哥洛夫-斯米尔诺夫检验"""
    if not 数据:
        raise Exception("柯尔莫哥洛夫检验失败: 数据为空")
    try:
        n = len(数据)
        排序数据 = sorted(数据)
        if 分布 == '正态':
            均值 = 参数[0] if len(参数) > 0 else _stats.mean(数据)
            标准差 = 参数[1] if len(参数) > 1 else _stats.stdev(数据) if n > 1 else 1.0
            def 理论CDF(x):
                return 正态CDF(x, 均值, 标准差)
        elif 分布 == '均匀':
            下限 = 参数[0] if len(参数) > 0 else min(数据)
            上限 = 参数[1] if len(参数) > 1 else max(数据)
            def 理论CDF(x):
                return 均匀分布CDF(x, 下限, 上限)
        else:
            raise Exception("柯尔莫哥洛夫检验失败: 不支持的分布 " + 分布)
        d = 0.0
        for i, x in enumerate(排序数据):
            ecdf = (i + 1) / n
            cdf_val = 理论CDF(x)
            d = max(d, abs(ecdf - cdf_val), abs(i / n - cdf_val))
        # KS统计量近似p值
        se = _math.sqrt(n) + 0.12 + 0.11 / _math.sqrt(n)
        p = 2.0 * _math.exp(-se * d * d)
        return {'D统计量': d, 'p值': min(p, 1.0), '样本量': n}
    except Exception as e:
        raise Exception("柯尔莫哥洛夫检验失败: " + str(e))


def 正态性检验(数据):
    """正态性检验（Shapiro-Wilk 简化版）"""
    if not 数据 or len(数据) < 3:
        raise Exception("正态性检验失败: 至少需要3个数据点")
    try:
        # 使用 D'Agostino-Pearson 检验
        n = len(数据)
        偏度 = 求偏度(数据)
        峰度 = 求峰度(数据)
        z_skew = 偏度 / _math.sqrt(6.0 / n)
        z_kurt = 峰度 / _math.sqrt(24.0 / n)
        chi2 = z_skew ** 2 + z_kurt ** 2
        p = 1.0 - _betainc(chi2 / 2.0, 1.0, 1.0) if chi2 > 0 else 1.0
        return {'统计量': chi2, 'p值': p, '偏度': 偏度, '峰度': 峰度}
    except Exception as e:
        raise Exception("正态性检验失败: " + str(e))


def 二项检验(成功数, 试验数, p=0.5):
    """二项检验"""
    if 试验数 <= 0:
        raise Exception("二项检验失败: 试验数必须大于0")
    if not (0 <= p <= 1):
        raise Exception("二项检验失败: p 必须在0到1之间")
    try:
        p_obs = 成功数 / 试验数
        # 正态近似
        se = _math.sqrt(p * (1 - p) / 试验数)
        z = (p_obs - p) / se if se > 0 else 0.0
        p_val = 2.0 * (1.0 - 标准正态CDF(abs(z)))
        return {'观测比例': p_obs, 'z值': z, 'p值': p_val}
    except Exception as e:
        raise Exception("二项检验失败: " + str(e))


# =============================================================================
# 回归分析
# =============================================================================

def 线性回归(x, y):
    """一元线性回归"""
    if len(x) != len(y):
        raise Exception("线性回归失败: 数据长度不一致")
    if len(x) < 3:
        raise Exception("线性回归失败: 至少需要3个数据点")
    try:
        n = len(x)
        x_mean = _stats.mean(x)
        y_mean = _stats.mean(y)
        xy_cov = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        x_var = sum((xi - x_mean) ** 2 for xi in x)
        if x_var == 0:
            raise Exception("线性回归失败: x 无变化")
        斜率 = xy_cov / x_var
        截距 = y_mean - 斜率 * x_mean
        y_pred = [斜率 * xi + 截距 for xi in x]
        残差 = [y[i] - y_pred[i] for i in range(n)]
        rss = sum(r ** 2 for r in 残差)
        mse = rss / (n - 2)
        斜率se = _math.sqrt(mse / x_var) if x_var > 0 else 0
        截距se = _math.sqrt(mse * (1.0 / n + x_mean ** 2 / x_var))
        t_slope = 斜率 / 斜率se if 斜率se > 0 else 0
        t_intercept = 截距 / 截距se if 截距se > 0 else 0
        r2 = 1 - rss / sum((y[i] - y_mean) ** 2 for i in range(n))
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - 2)
        return {
            '斜率': 斜率, '截距': 截距,
            '斜率标准误': 斜率se, '截距标准误': 截距se,
            't值(斜率)': t_slope, 't值(截距)': t_intercept,
            'R方': r2, '调整R方': adj_r2,
            '残差平方和': rss, '均方误差': mse,
            '样本量': n,
        }
    except Exception as e:
        raise Exception("线性回归失败: " + str(e))


def 多元线性回归(X, y):
    """多元线性回归"""
    if not X or not y:
        raise Exception("多元线性回归失败: 数据为空")
    if len(X) != len(y):
        raise Exception("多元线性回归失败: 数据长度不一致")
    try:
        n = len(X)
        k = len(X[0]) if X else 0
        # 添加常数项列
        X_design = [[1.0] + row for row in X]
        # 正规方程: beta = (X'X)^-1 X'y
        Xt = 矩阵转置(X_design)
        XtX = 矩阵乘法(Xt, X_design)
        Xty = 矩阵乘法(Xt, [[yi] for yi in y])
        beta = 矩阵乘法(矩阵求逆(XtX), Xty)
        系数 = [row[0] for row in beta]
        y_pred = [sum(系数[j] * X_design[i][j] for j in range(k + 1)) for i in range(n)]
        残差 = [y[i] - y_pred[i] for i in range(n)]
        rss = sum(r ** 2 for r in 残差)
        mse = rss / (n - k - 1) if n > k + 1 else 0
        y_mean = _stats.mean(y)
        tss = sum((y[i] - y_mean) ** 2 for i in range(n))
        r2 = 1 - rss / tss if tss > 0 else 0
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1) if n > k + 1 else r2
        return {
            '系数': 系数,
            '残差': 残差,
            'R方': r2, '调整R方': adj_r2,
            '残差平方和': rss, '均方误差': mse,
            '样本量': n, '特征数': k,
        }
    except Exception as e:
        raise Exception("多元线性回归失败: " + str(e))


def 多项式回归(x, y, 阶数=2):
    """多项式回归"""
    if len(x) != len(y):
        raise Exception("多项式回归失败: 数据长度不一致")
    if len(x) < 阶数 + 1:
        raise Exception("多项式回归失败: 数据点不足")
    try:
        X = [[xi ** (d + 1) for d in range(阶数)] for xi in x]
        return 多元线性回归(X, y)
    except Exception as e:
        raise Exception("多项式回归失败: " + str(e))


def 逻辑回归(X, y):
    """逻辑回归（简化实现）"""
    if not X or not y:
        raise Exception("逻辑回归失败: 数据为空")
    if len(X) != len(y):
        raise Exception("逻辑回归失败: 数据长度不一致")
    try:
        n = len(X)
        k = len(X[0]) if X else 0
        # 使用牛顿-拉夫森迭代
        X_design = [[1.0] + row for row in X]
        系数 = [0.0] * (k + 1)
        for _ in range(100):
            # 预测概率
            z = [sum(系数[j] * X_design[i][j] for j in range(k + 1)) for i in range(n)]
            p = [1.0 / (1.0 + _math.exp(-max(min(z[i], 100), -100))) for i in range(n)]
            # 梯度
            grad = [sum(X_design[i][j] * (y[i] - p[i]) for i in range(n)) for j in range(k + 1)]
            # Hessian
            W = [[p[i] * (1 - p[i]) if i == j else 0.0 for j in range(n)] for i in range(n)]
            XtW = 矩阵乘法(矩阵转置(X_design), W)
            H = 矩阵乘法(XtW, X_design)
            try:
                H_inv = 矩阵求逆(H)
            except Exception:
                break
            delta = 矩阵乘法(H_inv, [[g] for g in grad])
            delta_flat = [row[0] for row in delta]
            系数 = [系数[j] + delta_flat[j] for j in range(k + 1)]
            if all(abs(d) < 1e-8 for d in delta_flat):
                break
        return {
            '系数': 系数,
            '迭代次数': _ + 1,
        }
    except Exception as e:
        raise Exception("逻辑回归失败: " + str(e))


def 回归结果预测(回归结果, 新数据):
    """使用回归结果对新数据进行预测"""
    if '系数' not in 回归结果:
        raise Exception("回归结果预测失败: 无效的回归结果")
    try:
        系数 = 回归结果['系数']
        if isinstance(新数据[0], (list, tuple)):
            return [sum(系数[0] + 系数[j + 1] * row[j] for j in range(len(row))) for row in 新数据]
        else:
            return 系数[0] + sum(系数[j + 1] * 新数据[j] for j in range(len(新数据)))
    except Exception as e:
        raise Exception("回归结果预测失败: " + str(e))


def 回归结果预测区间(回归结果, 新数据, 置信水平=0.95):
    """回归结果预测区间"""
    if '均方误差' not in 回归结果:
        raise Exception("回归结果预测区间失败: 无效的回归结果")
    try:
        y_pred = 回归结果预测(回归结果, 新数据)
        mse = 回归结果['均方误差']
        z = 标准正态分位数((1 + 置信水平) / 2)
        margin = z * _math.sqrt(mse)
        if isinstance(y_pred, list):
            return [(y - margin, y + margin) for y in y_pred]
        return (y_pred - margin, y_pred + margin)
    except Exception as e:
        raise Exception("回归结果预测区间失败: " + str(e))


def 回归结果残差(回归结果):
    """获取回归结果残差"""
    if '残差' not in 回归结果:
        raise Exception("回归结果残差失败: 无效的回归结果")
    return 回归结果['残差']


def 回归结果残差图数据(回归结果):
    """获取回归结果残差图数据"""
    if '残差' not in 回归结果:
        raise Exception("回归结果残差图数据失败: 无效的回归结果")
    return [{'索引': i, '残差': r} for i, r in enumerate(回归结果['残差'])]


def 回归结果摘要(回归结果):
    """生成回归结果摘要字符串"""
    if not 回归结果:
        raise Exception("回归结果摘要失败: 无效的回归结果")
    lines = []
    lines.append("回归分析结果")
    lines.append("=" * 40)
    for key, value in 回归结果.items():
        if isinstance(value, float):
            lines.append(f"{key}: {value:.6f}")
        elif isinstance(value, list):
            lines.append(f"{key}: {[round(v, 6) if isinstance(v, float) else v for v in value]}")
        else:
            lines.append(f"{key}: {value}")
    return '\n'.join(lines)


# =============================================================================
# 方差分析
# =============================================================================

def 单因素方差分析(组数据):
    """单因素方差分析"""
    if not 组数据 or len(组数据) < 2:
        raise Exception("单因素方差分析失败: 至少需要2组")
    try:
        k = len(组数据)
        n_total = sum(len(g) for g in 组数据)
        all_data = [val for g in 组数据 for val in g]
        grand_mean = _stats.mean(all_data)
        ss_between = sum(len(g) * (_stats.mean(g) - grand_mean) ** 2 for g in 组数据)
        ss_within = sum(sum((val - _stats.mean(g)) ** 2 for val in g) for g in 组数据)
        df_between = k - 1
        df_within = n_total - k
        ms_between = ss_between / df_between if df_between > 0 else 0
        ms_within = ss_within / df_within if df_within > 0 else 0
        f = ms_between / ms_within if ms_within > 0 else 0
        p = 1.0 - _betainc(df_within * f / (df_within * f + df_between), df_within / 2.0, df_between / 2.0) if f > 0 else 1.0
        return {
            'F统计量': f, 'p值': p,
            '组间平方和': ss_between, '组内平方和': ss_within,
            '组间自由度': df_between, '组内自由度': df_within,
            '组间均方': ms_between, '组内均方': ms_within,
            '组数': k, '总样本量': n_total,
        }
    except Exception as e:
        raise Exception("单因素方差分析失败: " + str(e))


def 双因素方差分析(数据, 行因子, 列因子):
    """双因素方差分析"""
    if len(数据) != len(行因子) or len(数据) != len(列因子):
        raise Exception("双因素方差分析失败: 数据长度不一致")
    try:
        grand_mean = _stats.mean(数据)
        行标签 = sorted(set(行因子))
        列标签 = sorted(set(列因子))
        n = len(数据)
        # 计算各类均值
        ss_total = sum((数据[i] - grand_mean) ** 2 for i in range(n))
        ss_row = 0
        for r in 行标签:
            idx = [i for i in range(n) if 行因子[i] == r]
            if idx:
                ss_row += len(idx) * (_stats.mean([数据[i] for i in idx]) - grand_mean) ** 2
        ss_col = 0
        for c in 列标签:
            idx = [i for i in range(n) if 列因子[i] == c]
            if idx:
                ss_col += len(idx) * (_stats.mean([数据[i] for i in idx]) - grand_mean) ** 2
        ss_within = 0
        for r in 行标签:
            for c in 列标签:
                idx = [i for i in range(n) if 行因子[i] == r and 列因子[i] == c]
                if len(idx) > 1:
                    ss_within += sum((数据[i] - _stats.mean([数据[j] for j in idx])) ** 2 for i in idx)
        df_row = len(行标签) - 1
        df_col = len(列标签) - 1
        df_within = n - len(行标签) * len(列标签)
        ms_row = ss_row / df_row if df_row > 0 else 0
        ms_col = ss_col / df_col if df_col > 0 else 0
        ms_within = ss_within / df_within if df_within > 0 else 0
        f_row = ms_row / ms_within if ms_within > 0 else 0
        f_col = ms_col / ms_within if ms_within > 0 else 0
        p_row = 1.0 - _betainc(df_within * f_row / (df_within * f_row + df_row), df_within / 2.0, df_row / 2.0) if f_row > 0 else 1.0
        p_col = 1.0 - _betainc(df_within * f_col / (df_within * f_col + df_col), df_within / 2.0, df_col / 2.0) if f_col > 0 else 1.0
        return {
            '行F统计量': f_row, '行p值': p_row, '行自由度': df_row,
            '列F统计量': f_col, '列p值': p_col, '列自由度': df_col,
            '组内自由度': df_within, '组内均方': ms_within,
        }
    except Exception as e:
        raise Exception("双因素方差分析失败: " + str(e))


def 重复测量方差分析(数据):
    """重复测量方差分析（单因素重复测量）"""
    if not 数据 or len(数据) < 2:
        raise Exception("重复测量方差分析失败: 至少需要2组")
    try:
        k = len(数据)
        n = len(数据[0])
        for g in 数据:
            if len(g) != n:
                raise Exception("重复测量方差分析失败: 各组数据长度不一致")
        grand_mean = _stats.mean([val for g in 数据 for val in g])
        subject_means = [_stats.mean([数据[g][i] for g in range(k)]) for i in range(n)]
        ss_total = sum((数据[g][i] - grand_mean) ** 2 for g in range(k) for i in range(n))
        ss_treatment = sum(n * (_stats.mean(g) - grand_mean) ** 2 for g in 数据)
        ss_subject = sum(k * (subject_means[i] - grand_mean) ** 2 for i in range(n))
        ss_error = ss_total - ss_treatment - ss_subject
        df_treatment = k - 1
        df_error = (k - 1) * (n - 1)
        ms_treatment = ss_treatment / df_treatment if df_treatment > 0 else 0
        ms_error = ss_error / df_error if df_error > 0 else 0
        f = ms_treatment / ms_error if ms_error > 0 else 0
        p = 1.0 - _betainc(df_error * f / (df_error * f + df_treatment), df_error / 2.0, df_treatment / 2.0) if f > 0 else 1.0
        return {
            'F统计量': f, 'p值': p,
            '处理自由度': df_treatment, '误差自由度': df_error,
        }
    except Exception as e:
        raise Exception("重复测量方差分析失败: " + str(e))


def 方差分析事后检验(组数据):
    """方差分析事后检验（Tukey HSD）"""
    if not 组数据 or len(组数据) < 2:
        raise Exception("方差分析事后检验失败: 至少需要2组")
    try:
        from itertools import combinations as _combinations
        k = len(组数据)
        n = sum(len(g) for g in 组数据)
        mse = 0
        for g in 组数据:
            mse += sum((val - _stats.mean(g)) ** 2 for val in g)
        mse /= (n - k)
        results = []
        for (i, g1), (j, g2) in _combinations(enumerate(组数据), 2):
            均值差 = _stats.mean(g1) - _stats.mean(g2)
            se = _math.sqrt(mse * (1.0 / len(g1) + 1.0 / len(g2)))
            q = 均值差 / se if se > 0 else 0
            # Tukey p值近似
            p = 2.0 * (1.0 - _t_cdf(abs(q), n - k))
            results.append({
                '组1': i, '组2': j,
                '均值差': 均值差, '标准误': se,
                'q统计量': q, 'p值': p,
            })
        return results
    except Exception as e:
        raise Exception("方差分析事后检验失败: " + str(e))


# =============================================================================
# 置信区间与统计力
# =============================================================================

def 计算置信区间(数据, 置信水平=0.95):
    """计算均值的置信区间"""
    if not 数据 or len(数据) < 2:
        raise Exception("计算置信区间失败: 至少需要2个数据点")
    try:
        n = len(数据)
        均值 = _stats.mean(数据)
        se = _stats.stdev(数据) / _math.sqrt(n)
        z = 标准正态分位数((1 + 置信水平) / 2)
        margin = z * se
        return (均值 - margin, 均值 + margin)
    except Exception as e:
        raise Exception("计算置信区间失败: " + str(e))


def 计算统计检验力(均值差, 标准差, 样本量, 显著性水平=0.05):
    """计算统计检验力（双样本t检验）"""
    if 标准差 <= 0 or 样本量 <= 1:
        raise Exception("计算统计检验力失败: 参数无效")
    try:
        se = 标准差 * _math.sqrt(2.0 / 样本量)
        t_crit = 标准正态分位数(1 - 显著性水平 / 2)
        delta = 均值差 / se
        power = 1.0 - 标准正态CDF(t_crit - abs(delta))
        return power
    except Exception as e:
        raise Exception("计算统计检验力失败: " + str(e))


def 计算样本量(效应量, 统计检验力=0.8, 显著性水平=0.05):
    """计算所需样本量（双样本t检验）"""
    if 效应量 <= 0:
        raise Exception("计算样本量失败: 效应量必须大于0")
    if not (0 < 统计检验力 < 1) or not (0 < 显著性水平 < 1):
        raise Exception("计算样本量失败: 概率参数必须在0到1之间")
    try:
        z_alpha = 标准正态分位数(1 - 显著性水平 / 2)
        z_beta = 标准正态分位数(统计检验力)
        n = int(_math.ceil(2 * ((z_alpha + z_beta) / 效应量) ** 2))
        return max(n, 2)
    except Exception as e:
        raise Exception("计算样本量失败: " + str(e))


# =============================================================================
# 数据标准化
# =============================================================================

def 标准化数据(数据, 方法='zscore'):
    """标准化数据（zscore 或 minmax）"""
    if not 数据:
        raise Exception("标准化数据失败: 数据为空")
    try:
        if 方法 == 'zscore':
            均值 = _stats.mean(数据)
            标准差 = _stats.stdev(数据) if len(数据) > 1 else 1.0
            if 标准差 == 0:
                return [0.0] * len(数据)
            return [(x - 均值) / 标准差 for x in 数据]
        elif 方法 == 'minmax':
            min_val = min(数据)
            max_val = max(数据)
            if max_val == min_val:
                return [0.5] * len(数据)
            return [(x - min_val) / (max_val - min_val) for x in 数据]
        else:
            raise Exception("标准化数据失败: 不支持的方法 " + 方法)
    except Exception as e:
        raise Exception("标准化数据失败: " + str(e))


def 最小最大标准化(数据):
    """最小最大标准化（归一到0~1）"""
    return 标准化数据(数据, 方法='minmax')