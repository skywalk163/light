"""
数值计算 — duanpub 桥接模块

基于 Python math 库封装，函数名对齐 duanpub/packages/数值计算/源.duan。

duanpub 原始包通过 C FFI 调用底层数学库，
本桥接模块用 Python math 模块替代，提供等价的数值计算功能。
"""

import math as _math


# =============================================================================
# 基本数值运算
# =============================================================================

def 内部平方根(x):
    """计算平方根（内部函数，直接返回 math.sqrt）"""
    if x < 0:
        raise Exception("内部平方根失败: 不能对负数求平方根")
    return _math.sqrt(x)


# =============================================================================
# 向量运算
# =============================================================================

def 向量点积(向量A, 向量B):
    """计算两个向量的点积"""
    if len(向量A) != len(向量B):
        raise Exception("向量点积失败: 向量维度不匹配")
    try:
        return sum(a * b for a, b in zip(向量A, 向量B))
    except Exception as e:
        raise Exception("向量点积失败: " + str(e))


def 向量加法(向量A, 向量B):
    """向量加法"""
    if len(向量A) != len(向量B):
        raise Exception("向量加法失败: 向量维度不匹配")
    try:
        return [a + b for a, b in zip(向量A, 向量B)]
    except Exception as e:
        raise Exception("向量加法失败: " + str(e))


def 向量减法(向量A, 向量B):
    """向量减法"""
    if len(向量A) != len(向量B):
        raise Exception("向量减法失败: 向量维度不匹配")
    try:
        return [a - b for a, b in zip(向量A, 向量B)]
    except Exception as e:
        raise Exception("向量减法失败: " + str(e))


def 向量模值(向量):
    """计算向量的模（长度）"""
    if not 向量:
        raise Exception("向量模值失败: 向量为空")
    try:
        return _math.sqrt(sum(x * x for x in 向量))
    except Exception as e:
        raise Exception("向量模值失败: " + str(e))


def 向量归一化(向量):
    """向量归一化（单位向量）"""
    if not 向量:
        raise Exception("向量归一化失败: 向量为空")
    try:
        mod = 向量模值(向量)
        if mod == 0:
            raise Exception("向量归一化失败: 零向量无法归一化")
        return [x / mod for x in 向量]
    except Exception as e:
        raise Exception("向量归一化失败: " + str(e))


# =============================================================================
# 矩阵运算
# =============================================================================

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


def 矩阵转置(矩阵):
    """矩阵转置"""
    if not 矩阵 or not 矩阵[0]:
        raise Exception("矩阵转置失败: 矩阵为空")
    try:
        return [list(row) for row in zip(*矩阵)]
    except Exception as e:
        raise Exception("矩阵转置失败: " + str(e))


def 行列式(矩阵):
    """计算方阵的行列式"""
    if not 矩阵:
        raise Exception("行列式失败: 矩阵为空")
    n = len(矩阵)
    if n != len(矩阵[0]):
        raise Exception("行列式失败: 矩阵必须是方阵")
    try:
        # 深拷贝
        a = [row[:] for row in 矩阵]
        det = 1.0
        for i in range(n):
            # 选主元
            pivot = i
            for k in range(i + 1, n):
                if abs(a[k][i]) > abs(a[pivot][i]):
                    pivot = k
            if abs(a[pivot][i]) < 1e-12:
                return 0.0
            if pivot != i:
                a[i], a[pivot] = a[pivot], a[i]
                det = -det
            pivot_val = a[i][i]
            det *= pivot_val
            for k in range(i + 1, n):
                factor = a[k][i] / pivot_val
                for j in range(i, n):
                    a[k][j] -= factor * a[i][j]
        return det
    except Exception as e:
        raise Exception("行列式失败: " + str(e))


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


# =============================================================================
# 插值与数值积分
# =============================================================================

def 线性插值(x0, y0, x1, y1, x):
    """线性插值：在点 (x0,y0) 和 (x1,y1) 之间对 x 进行插值"""
    if x1 == x0:
        raise Exception("线性插值失败: x0 和 x1 不能相同")
    try:
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    except Exception as e:
        raise Exception("线性插值失败: " + str(e))


def 梯形积分(函数, a, b, n=100):
    """梯形法数值积分"""
    if n <= 0:
        raise Exception("梯形积分失败: 分割数必须大于0")
    if a >= b:
        raise Exception("梯形积分失败: a 必须小于 b")
    try:
        h = (b - a) / n
        s = 0.5 * (函数(a) + 函数(b))
        for i in range(1, n):
            s += 函数(a + i * h)
        return s * h
    except Exception as e:
        raise Exception("梯形积分失败: " + str(e))


def 辛普森积分(函数, a, b, n=100):
    """辛普森法数值积分（n 必须为偶数）"""
    if n <= 0:
        raise Exception("辛普森积分失败: 分割数必须大于0")
    if a >= b:
        raise Exception("辛普森积分失败: a 必须小于 b")
    if n % 2 != 0:
        n += 1  # 确保为偶数
    try:
        h = (b - a) / n
        s = 函数(a) + 函数(b)
        for i in range(1, n, 2):
            s += 4 * 函数(a + i * h)
        for i in range(2, n - 1, 2):
            s += 2 * 函数(a + i * h)
        return s * h / 3.0
    except Exception as e:
        raise Exception("辛普森积分失败: " + str(e))