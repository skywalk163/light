"""
光明标准库 - 集合模块

提供集合运算功能，包括：
- 并集、交集、差集、对称差
- 子集、超集判断
- 集合转换和操作
"""

from typing import List, Any, Set


def 创建集合(可迭代对象=None):
    """创建集合"""
    if 可迭代对象 is None:
        return set()
    return set(可迭代对象)


def 集合转列表(集合: Set[Any]):
    """集合转列表"""
    return list(集合)


def 列表转集合(列表: List[Any]):
    """列表转集合"""
    return set(列表)


def 集合转元组(集合: Set[Any]):
    """集合转元组"""
    return tuple(集合)


def 集合转字符串(集合: Set[Any], 分隔符: str = ','):
    """集合转字符串"""
    return 分隔符.join(str(item) for item in 集合)


def 并集(集合1: Set[Any], 集合2: Set[Any]):
    """计算两个集合的并集"""
    return 集合1 | 集合2


def 交集(集合1: Set[Any], 集合2: Set[Any]):
    """计算两个集合的交集"""
    return 集合1 & 集合2


def 差集(集合1: Set[Any], 集合2: Set[Any]):
    """计算集合1相对于集合2的差集"""
    return 集合1 - 集合2


def 对称差(集合1: Set[Any], 集合2: Set[Any]):
    """计算两个集合的对称差"""
    return 集合1 ^ 集合2


def 多个并集(*集合列表):
    """计算多个集合的并集"""
    if not 集合列表:
        return set()
    结果 = set(集合列表[0])
    for s in 集合列表[1:]:
        结果 |= s
    return 结果


def 多个交集(*集合列表):
    """计算多个集合的交集"""
    if not 集合列表:
        return set()
    结果 = set(集合列表[0])
    for s in 集合列表[1:]:
        结果 &= s
    return 结果


def 是否子集(集合1: Set[Any], 集合2: Set[Any]):
    """判断集合1是否是集合2的子集"""
    return 集合1 <= 集合2


def 是否真子集(集合1: Set[Any], 集合2: Set[Any]):
    """判断集合1是否是集合2的真子集"""
    return 集合1 < 集合2


def 是否超集(集合1: Set[Any], 集合2: Set[Any]):
    """判断集合1是否是集合2的超集"""
    return 集合1 >= 集合2


def 是否真超集(集合1: Set[Any], 集合2: Set[Any]):
    """判断集合1是否是集合2的真超集"""
    return 集合1 > 集合2


def 是否不相交(集合1: Set[Any], 集合2: Set[Any]):
    """判断两个集合是否不相交"""
    return 集合1.isdisjoint(集合2)


def 添加元素(集合: Set[Any], 元素: Any):
    """向集合添加元素"""
    集合.add(元素)
    return 集合


def 移除元素(集合: Set[Any], 元素: Any):
    """从集合移除元素（不存在时报错）"""
    集合.remove(元素)
    return 集合


def 丢弃元素(集合: Set[Any], 元素: Any):
    """从集合丢弃元素（不存在时不报错）"""
    集合.discard(元素)
    return 集合


def 弹出元素(集合: Set[Any]):
    """从集合弹出一个元素"""
    return 集合.pop()


def 清空集合(集合: Set[Any]):
    """清空集合"""
    集合.clear()
    return 集合


def 集合长度(集合: Set[Any]):
    """获取集合长度"""
    return len(集合)


def 集合包含(集合: Set[Any], 元素: Any):
    """判断集合是否包含元素"""
    return 元素 in 集合


def 集合相等(集合1: Set[Any], 集合2: Set[Any]):
    """判断两个集合是否相等"""
    return 集合1 == 集合2


def 集合不等(集合1: Set[Any], 集合2: Set[Any]):
    """判断两个集合是否不等"""
    return 集合1 != 集合2


def 复制集合(集合: Set[Any]):
    """复制集合"""
    return 集合.copy()


def 冻结集合(可迭代对象=None):
    """创建冻结集合"""
    return frozenset(可迭代对象)


def 集合的幂集(集合: Set[Any]):
    """计算集合的幂集"""
    元素列表 = list(集合)
    幂集 = [set()]
    for 元素 in 元素列表:
        幂集 += [子集 | {元素} for 子集 in 幂集]
    return 幂集


def 集合的笛卡尔积(集合1: Set[Any], 集合2: Set[Any]):
    """计算两个集合的笛卡尔积"""
    return {(a, b) for a in 集合1 for b in 集合2}


def 集合的补集(集合: Set[Any], 全集: Set[Any]):
    """计算集合相对于全集的补集"""
    return 全集 - 集合


def 集合差集的大小(集合1: Set[Any], 集合2: Set[Any]):
    """计算差集的大小"""
    return len(集合1 - 集合2)


def 集合交集的大小(集合1: Set[Any], 集合2: Set[Any]):
    """计算交集的大小"""
    return len(集合1 & 集合2)


def 集合并集的大小(集合1: Set[Any], 集合2: Set[Any]):
    """计算并集的大小"""
    return len(集合1 | 集合2)


def 杰卡德相似度(集合1: Set[Any], 集合2: Set[Any]):
    """计算两个集合的杰卡德相似度"""
    交集大小 = len(集合1 & 集合2)
    并集大小 = len(集合1 | 集合2)
    if 并集大小 == 0:
        return 0.0
    return 交集大小 / 并集大小


def 集合的唯一元素(列表: List[Any]):
    """从列表中获取唯一元素集合"""
    return set(列表)


def 集合的重复元素(列表: List[Any]):
    """从列表中获取重复元素集合"""
    出现次数 = {}
    for 元素 in 列表:
        出现次数[元素] = 出现次数.get(元素, 0) + 1
    return {元素 for 元素, 次数 in 出现次数.items() if 次数 > 1}


__all__ = [
    '创建集合', '集合转列表', '列表转集合', '集合转元组', '集合转字符串',
    '并集', '交集', '差集', '对称差', '多个并集', '多个交集',
    '是否子集', '是否真子集', '是否超集', '是否真超集', '是否不相交',
    '添加元素', '移除元素', '丢弃元素', '弹出元素', '清空集合',
    '集合长度', '集合包含', '集合相等', '集合不等', '复制集合',
    '冻结集合', '集合的幂集', '集合的笛卡尔积', '集合的补集',
    '集合差集的大小', '集合交集的大小', '集合并集的大小',
    '杰卡德相似度', '集合的唯一元素', '集合的重复元素'
]