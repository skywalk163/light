"""
段言标准库 - 数学模块

提供数学运算函数：pow, sqrt, sin, cos, tan, random, floor, ceil, round, pi
"""

import math
import cmath
import random as _random
import statistics as _stats
from typing import Union, List, Optional

Number = Union[int, float]


def 绝对值(x: Number) -> Number:
    """绝对值"""
    return abs(x)


def 最大值(甲: Number, 乙: Number) -> Number:
    """最大值"""
    return max(甲, 乙)


def 最小值(甲: Number, 乙: Number) -> Number:
    """最小值"""
    return min(甲, 乙)


def 幂(底数: Number, 指数: Number) -> float:
    """幂运算：底数 ^ 指数"""
    return pow(底数, 指数)


def 平方根(x: Number) -> float:
    """平方根"""
    if x < 0:
        raise RuntimeError(f"不能对负数求平方根: {x}")
    return math.sqrt(x)


def 正弦(x: Number) -> float:
    """正弦（弧度）"""
    return math.sin(x)


def 余弦(x: Number) -> float:
    """余弦（弧度）"""
    return math.cos(x)


def 正切(x: Number) -> float:
    """正切（弧度）"""
    return math.tan(x)


def 弧度转角度(弧度: Number) -> float:
    """弧度转角度"""
    return math.degrees(弧度)


def 角度转弧度(角度: Number) -> float:
    """角度转弧度"""
    return math.radians(角度)


def 向上取整(x: Number) -> int:
    """向上取整"""
    return math.ceil(x)


def 向下取整(x: Number) -> int:
    """向下取整"""
    return math.floor(x)


def 四舍五入(x: Number, 小数位数: int = 0) -> float:
    """四舍五入"""
    return round(x, 小数位数)


def 随机整数(最小值: int, 最大值: int) -> int:
    """随机整数 [最小值, 最大值]"""
    return _random.randint(最小值, 最大值)


def 随机浮点() -> float:
    """随机浮点数 [0.0, 1.0)"""
    return _random.random()


def 随机选择(列表: List) -> object:
    """从列表中随机选择一个元素"""
    return _random.choice(列表)


def 圆周率() -> float:
    """圆周率 π"""
    return math.pi


def 自然常数() -> float:
    """自然常数 e"""
    return math.e


def 阶乘(n: int) -> int:
    """阶乘 n!"""
    if n < 0:
        raise RuntimeError(f"不能对负数求阶乘: {n}")
    return math.factorial(n)


def 对数(x: Number, 底数: Number = math.e) -> float:
    """对数：log_底数(x)"""
    return math.log(x, 底数)


def 自然对数(x: Number) -> float:
    """自然对数 ln(x)"""
    if x <= 0:
        raise RuntimeError(f"不能对非正数求自然对数: {x}")
    return math.log(x)


def 常用对数(x: Number) -> float:
    """常用对数 log10(x)"""
    if x <= 0:
        raise RuntimeError(f"不能对非正数求常用对数: {x}")
    return math.log10(x)


def 对数2(x: Number) -> float:
    """以2为底的对数 log2(x)"""
    if x <= 0:
        raise RuntimeError(f"不能对非正数求对数: {x}")
    return math.log2(x)


def 立方根(x: Number) -> float:
    """立方根"""
    return math.cbrt(x)


def 指数(x: Number) -> float:
    """指数函数 e^x"""
    return math.exp(x)


def 双曲正弦(x: Number) -> float:
    """双曲正弦 sinh(x)"""
    return math.sinh(x)


def 双曲余弦(x: Number) -> float:
    """双曲余弦 cosh(x)"""
    return math.cosh(x)


def 双曲正切(x: Number) -> float:
    """双曲正切 tanh(x)"""
    return math.tanh(x)


def 反双曲正弦(x: Number) -> float:
    """反双曲正弦 asinh(x)"""
    return math.asinh(x)


def 反双曲余弦(x: Number) -> float:
    """反双曲余弦 acosh(x)"""
    return math.acosh(x)


def 反双曲正切(x: Number) -> float:
    """反双曲正切 atanh(x)"""
    return math.atanh(x)


def 反正弦(x: Number) -> float:
    """反正弦 arcsin(x)（弧度）"""
    return math.asin(x)


def 反余弦(x: Number) -> float:
    """反余弦 arccos(x)（弧度）"""
    return math.acos(x)


def 反正切(x: Number) -> float:
    """反正切 arctan(x)（弧度）"""
    return math.atan(x)


def 反正切2(y: Number, x: Number) -> float:
    """反正切2 atan2(y, x)（弧度）"""
    return math.atan2(y, x)


def 余切(x: Number) -> float:
    """余切 cot(x)"""
    return 1.0 / math.tan(x)


def 正割(x: Number) -> float:
    """正割 sec(x)"""
    return 1.0 / math.cos(x)


def 余割(x: Number) -> float:
    """余割 csc(x)"""
    return 1.0 / math.sin(x)


def 双曲余切(x: Number) -> float:
    """双曲余切 coth(x)"""
    return 1.0 / math.tanh(x)


def 双曲正割(x: Number) -> float:
    """双曲正割 sech(x)"""
    return 1.0 / math.cosh(x)


def 双曲余割(x: Number) -> float:
    """双曲余割 csch(x)"""
    return 1.0 / math.sinh(x)


def 弧度(x: Number) -> float:
    """角度转弧度（别名）"""
    return math.radians(x)


def 角度(x: Number) -> float:
    """弧度转角度（别名）"""
    return math.degrees(x)


def 双阶乘(n: int) -> int:
    """双阶乘 n!!"""
    if n < 0:
        raise RuntimeError(f"不能对负数求双阶乘: {n}")
    result = 1
    i = n
    while i > 0:
        result *= i
        i -= 2
    return result


def 排列(n: int, k: int) -> int:
    """排列数 P(n, k)"""
    if n < 0 or k < 0 or k > n:
        raise RuntimeError(f"无效的排列参数: n={n}, k={k}")
    result = 1
    for i in range(k):
        result *= (n - i)
    return result


def 组合(n: int, k: int) -> int:
    """组合数 C(n, k)"""
    if n < 0 or k < 0 or k > n:
        raise RuntimeError(f"无效的组合参数: n={n}, k={k}")
    if k > n - k:
        k = n - k
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result


def 二项式系数(n: int, k: int) -> int:
    """二项式系数（组合数别名）"""
    return 组合(n, k)


def 欧拉常数() -> float:
    """欧拉常数 γ ≈ 0.5772"""
    return math.gamma(1)


def 黄金比例() -> float:
    """黄金比例 φ ≈ 1.618"""
    return (1 + math.sqrt(5)) / 2


def 弧度π() -> float:
    """π 弧度（180度）"""
    return math.pi


def 弧度π2() -> float:
    """π/2 弧度（90度）"""
    return math.pi / 2


def 弧度π4() -> float:
    """π/4 弧度（45度）"""
    return math.pi / 4


def 弧度2π() -> float:
    """2π 弧度（360度）"""
    return math.pi * 2


def 度分秒转弧度(度: int, 分: int = 0, 秒: float = 0) -> float:
    """度分秒转弧度"""
    return math.radians(度 + 分 / 60 + 秒 / 3600)


def 弧度转度分秒(弧度: float) -> tuple:
    """弧度转度分秒"""
    度 = math.degrees(弧度)
    整数度 = int(度)
    分 = (度 - 整数度) * 60
    整数分 = int(分)
    秒 = (分 - 整数分) * 60
    return (整数度, 整数分, 秒)


def 复数实部(z: complex) -> float:
    """复数实部"""
    return z.real


def 复数虚部(z: complex) -> float:
    """复数虚部"""
    return z.imag


def 复数模(z: complex) -> float:
    """复数模（绝对值）"""
    return abs(z)


def 复数辐角(z: complex) -> float:
    """复数辐角（弧度）"""
    return math.atan2(z.imag, z.real)


def 复数共轭(z: complex) -> complex:
    """复数共轭"""
    return complex(z.real, -z.imag)


def 复数极坐标转直角(模: float, 辐角: float) -> complex:
    """极坐标转直角坐标"""
    return complex(模 * math.cos(辐角), 模 * math.sin(辐角))


def 复数直角转极坐标(z: complex) -> tuple:
    """直角坐标转极坐标 (模, 辐角)"""
    return (abs(z), math.atan2(z.imag, z.real))


def 复数指数(z: complex) -> complex:
    """复数指数函数 e^z"""
    return cmath.exp(z)


def 复数对数(z: complex) -> complex:
    """复数对数"""
    return cmath.log(z)


def 复数平方根(z: complex) -> complex:
    """复数平方根"""
    return cmath.sqrt(z)


def 复数正弦(z: complex) -> complex:
    """复数正弦"""
    return cmath.sin(z)


def 复数余弦(z: complex) -> complex:
    """复数余弦"""
    return cmath.cos(z)


def 复数正切(z: complex) -> complex:
    """复数正切"""
    return cmath.tan(z)


def 双曲正弦h(x: Number) -> float:
    """双曲正弦（简写）"""
    return math.sinh(x)


def 双曲余弦h(x: Number) -> float:
    """双曲余弦（简写）"""
    return math.cosh(x)


def 双曲正切h(x: Number) -> float:
    """双曲正切（简写）"""
    return math.tanh(x)


def 随机范围(最小值: float, 最大值: float) -> float:
    """生成指定范围内的随机浮点数"""
    return _random.uniform(最小值, 最大值)


def 随机打乱(列表: List) -> None:
    """随机打乱列表（原地修改）"""
    _random.shuffle(列表)


def 随机样本(列表: List, k: int) -> List:
    """从列表中随机抽取k个不重复元素"""
    return _random.sample(列表, k)


def 设置随机种子(种子: int = None) -> None:
    """设置随机数种子"""
    _random.seed(种子)


def 正态随机(均值: float = 0.0, 标准差: float = 1.0) -> float:
    """生成正态分布随机数"""
    return _random.normalvariate(均值, 标准差)


def 泊松随机(均值: float) -> int:
    """生成泊松分布随机数"""
    return _random.poissonvariate(均值)


def 指数随机(均值: float) -> float:
    """生成指数分布随机数"""
    return _random.expovariate(均值)


# =============================================================================
# 统计函数
# =============================================================================

def 平均数(数据: List[Number]) -> float:
    """
    算术平均数

    参数:
        数据: 数字列表

    返回:
        平均数
    """
    return _stats.mean(数据)


def 中位数(数据: List[Number]) -> float:
    """
    中位数

    参数:
        数据: 数字列表

    返回:
        中位数
    """
    return _stats.median(数据)


def 众数(数据: List[Number]) -> Number:
    """
    众数（出现最多的值）

    参数:
        数据: 数字列表

    返回:
        众数
    """
    try:
        return _stats.mode(数据)
    except _stats.StatisticsError:
        raise RuntimeError("众数不存在：所有值出现次数相同")


def 标准差(数据: List[Number]) -> float:
    """
    总体标准差

    参数:
        数据: 数字列表

    返回:
        标准差
    """
    return _stats.pstdev(数据)


def 样本标准差(数据: List[Number]) -> float:
    """
    样本标准差（自由度 n-1）

    参数:
        数据: 样本数据列表

    返回:
        样本标准差
    """
    if len(数据) < 2:
        raise RuntimeError("样本数量不足，至少需要 2 个数据")
    return _stats.stdev(数据)


def 方差(数据: List[Number]) -> float:
    """
    总体方差

    参数:
        数据: 数字列表

    返回:
        方差
    """
    return _stats.pvariance(数据)


def 样本方差(数据: List[Number]) -> float:
    """
    样本方差（自由度 n-1）

    参数:
        数据: 样本数据列表

    返回:
        样本方差
    """
    if len(数据) < 2:
        raise RuntimeError("样本数量不足，至少需要 2 个数据")
    return _stats.variance(数据)


def 范围(数据: List[Number]) -> float:
    """
    范围（最大值 - 最小值）

    参数:
        数据: 数字列表

    返回:
        范围值
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    return max(数据) - min(数据)


def 求和(数据: List[Number]) -> Number:
    """
    求和

    参数:
        数据: 数字列表

    返回:
        总和
    """
    return sum(数据)


def 累积和(数据: List[Number]) -> List[Number]:
    """
    累积和

    参数:
        数据: 数字列表

    返回:
        累积和列表（每个元素为到该位置为止的和）
    """
    result = []
    total = 0
    for v in 数据:
        total += v
        result.append(total)
    return result


def 线性回归(x数据: List[Number], y数据: List[Number]) -> dict:
    """
    线性回归（斜率、截距、相关系数）

    参数:
        x数据: X 轴数据列表
        y数据: Y 轴数据列表

    返回:
        {'斜率': slope, '截距': intercept, '相关系数': r}
    """
    if len(x数据) != len(y数据):
        raise RuntimeError("X 和 Y 数据长度不匹配")
    if len(x数据) < 2:
        raise RuntimeError("数据点不足，至少需要 2 个点")
    try:
        slope, intercept = _stats.linear_regression(x数据, y数据)
    except _stats.StatisticsError as e:
        raise RuntimeError(f"线性回归失败: {e}")

    # 计算相关系数
    n = len(x数据)
    mx, my = _stats.mean(x数据), _stats.mean(y数据)
    sx, sy = _stats.pstdev(x数据), _stats.pstdev(y数据)
    if sx == 0 or sy == 0:
        r = 1.0
    else:
        r = sum((x数据[i] - mx) * (y数据[i] - my) for i in range(n)) / (n * sx * sy)

    return {
        '斜率': slope,
        '截距': intercept,
        '相关系数': r,
    }


__all__ = [
    '绝对值', '最大值', '最小值',
    '幂', '平方根', '立方根',
    '正弦', '余弦', '正切',
    '余切', '正割', '余割',
    '反正弦', '反余弦', '反正切', '反正切2',
    '弧度转角度', '角度转弧度', '弧度', '角度',
    '向上取整', '向下取整', '四舍五入',
    '随机整数', '随机浮点', '随机选择',
    '随机范围', '随机打乱', '随机样本',
    '设置随机种子', '正态随机', '泊松随机', '指数随机',
    '圆周率', '自然常数', '欧拉常数', '黄金比例',
    '弧度π', '弧度π2', '弧度π4', '弧度2π',
    '阶乘', '双阶乘', '对数', '自然对数',
    '常用对数', '对数2', '指数',
    '双曲正弦', '双曲余弦', '双曲正切',
    '双曲余切', '双曲正割', '双曲余割',
    '反双曲正弦', '反双曲余弦', '反双曲正切',
    '双曲正弦h', '双曲余弦h', '双曲正切h',
    '排列', '组合', '二项式系数',
    '度分秒转弧度', '弧度转度分秒',

    # 复数运算
    '复数实部', '复数虚部', '复数模',
    '复数辐角', '复数共轭',
    '复数极坐标转直角', '复数直角转极坐标',
    '复数指数', '复数对数', '复数平方根',
    '复数正弦', '复数余弦', '复数正切',

    # 统计函数
    '平均数', '中位数', '众数',
    '标准差', '样本标准差', '方差', '样本方差',
    '范围', '求和', '累积和',
    '线性回归',

    # 合并自数学工具
    '平方', '是奇数', '是偶数', '是素数',
    '最大公约数', '最小公倍数', '累加',
]


# =============================================================================
# 合并自数学工具.duan的独有函数
# =============================================================================

def 平方(x: Number) -> Number:
    """计算平方"""
    return x * x


def 是奇数(n: int) -> bool:
    """判断是否为奇数"""
    return n % 2 == 1


def 是偶数(n: int) -> bool:
    """判断是否为偶数"""
    return n % 2 == 0


def 是素数(n: int) -> bool:
    """判断是否为素数"""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def 最大公约数(甲: int, 乙: int) -> int:
    """计算最大公约数"""
    甲, 乙 = abs(甲), abs(乙)
    while 乙:
        甲, 乙 = 乙, 甲 % 乙
    return 甲


def 最小公倍数(甲: int, 乙: int) -> int:
    """计算最小公倍数"""
    if 甲 == 0 or 乙 == 0:
        return 0
    return abs(甲 * 乙) // 最大公约数(甲, 乙)


def 累加(n: int) -> int:
    """计算1到n的累加和"""
    return n * (n + 1) // 2