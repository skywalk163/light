"""
集合扩展 — lightpub 桥接模块

基于 Python itertools / collections 库封装，函数名对齐上游 duanpub（段言时期）packages/集合扩展/源.duan。

上游 duanpub 原始包通过 C FFI 实现集合操作，
本桥接模块用 Python 内置函数和标准库替代，提供等价的列表、字典、集合扩展操作功能。
"""


# =============================================================================
# 列表操作
# =============================================================================

def 列表_排序(列表, 反转=False, 键=None):
    """排序列表，返回新列表"""
    if not 列表:
        return []
    try:
        return sorted(列表, reverse=反转, key=键)
    except Exception as e:
        raise Exception("列表排序失败: " + str(e))


def 列表_过滤(列表, 条件函数=None):
    """过滤列表，返回满足条件的元素新列表"""
    if not 列表:
        return []
    try:
        if 条件函数:
            return [item for item in 列表 if 条件函数(item)]
        return [item for item in 列表 if item]
    except Exception as e:
        raise Exception("列表过滤失败: " + str(e))


def 列表_映射(列表, 转换函数):
    """对列表每个元素应用转换函数，返回新列表"""
    if not 列表:
        return []
    if not 转换函数:
        raise Exception("列表映射失败: 转换函数为空")
    try:
        return [转换函数(item) for item in 列表]
    except Exception as e:
        raise Exception("列表映射失败: " + str(e))


def 列表_去重(列表, 键=None):
    """列表去重，保持顺序，返回新列表"""
    if not 列表:
        return []
    try:
        seen = set()
        result = []
        for item in 列表:
            k = 键(item) if 键 else item
            if k not in seen:
                seen.add(k)
                result.append(item)
        return result
    except Exception as e:
        raise Exception("列表去重失败: " + str(e))


def 列表_分组(列表, 键函数):
    """按指定键函数对列表分组，返回{键: [元素列表]}"""
    if not 列表:
        return {}
    if not 键函数:
        raise Exception("列表分组失败: 键函数为空")
    try:
        result = {}
        for item in 列表:
            key = 键函数(item)
            if key not in result:
                result[key] = []
            result[key].append(item)
        return result
    except Exception as e:
        raise Exception("列表分组失败: " + str(e))


def 列表_分块(列表, 块大小):
    """将列表分块为指定大小的子列表"""
    if not 列表:
        return []
    if 块大小 <= 0:
        raise Exception("列表分块失败: 块大小必须大于0")
    try:
        return [列表[i:i + 块大小] for i in range(0, len(列表), 块大小)]
    except Exception as e:
        raise Exception("列表分块失败: " + str(e))


def 列表_扁平化(嵌套列表):
    """将嵌套列表扁平化为一层"""
    if not 嵌套列表:
        return []
    try:
        result = []
        for item in 嵌套列表:
            if isinstance(item, list):
                result.extend(列表_扁平化(item))
            else:
                result.append(item)
        return result
    except Exception as e:
        raise Exception("列表扁平化失败: " + str(e))


def 列表_复制(列表):
    """复制列表（浅拷贝）"""
    if not 列表:
        return []
    try:
        return list(列表)
    except Exception as e:
        raise Exception("列表复制失败: " + str(e))


# =============================================================================
# 字典操作
# =============================================================================

def 字典_合并(*字典列表):
    """合并多个字典，返回新字典（后面的覆盖前面的）"""
    if not 字典列表:
        return {}
    try:
        result = {}
        for d in 字典列表:
            if d:
                result.update(d)
        return result
    except Exception as e:
        raise Exception("字典合并失败: " + str(e))


def 字典_获取键组(字典, 键列表):
    """从字典中获取指定键的键值对，返回新字典"""
    if not 字典:
        return {}
    if not 键列表:
        return {}
    try:
        return {k: 字典[k] for k in 键列表 if k in 字典}
    except Exception as e:
        raise Exception("字典获取键组失败: " + str(e))


def 字典_获取值组(字典, 键列表, 默认值=None):
    """从字典中获取指定键的值列表"""
    if not 字典:
        return []
    if not 键列表:
        return []
    try:
        return [字典.get(k, 默认值) for k in 键列表]
    except Exception as e:
        raise Exception("字典获取值组失败: " + str(e))


def 字典_过滤(字典, 条件函数):
    """过滤字典中满足条件的键值对，返回新字典"""
    if not 字典:
        return {}
    if not 条件函数:
        return dict(字典)
    try:
        return {k: v for k, v in 字典.items() if 条件函数(k, v)}
    except Exception as e:
        raise Exception("字典过滤失败: " + str(e))


# =============================================================================
# 集合操作
# =============================================================================

def 集合_交集(集合1, 集合2):
    """返回两个集合的交集"""
    if not 集合1 or not 集合2:
        return set()
    try:
        return set(集合1) & set(集合2)
    except Exception as e:
        raise Exception("集合交集失败: " + str(e))


def 集合_并集(集合1, 集合2):
    """返回两个集合的并集"""
    if not 集合1 and not 集合2:
        return set()
    try:
        result = set(集合1) if 集合1 else set()
        result.update(集合2 or [])
        return result
    except Exception as e:
        raise Exception("集合并集失败: " + str(e))


def 集合_差集(集合1, 集合2):
    """返回两个集合的差集（在集合1中但不在集合2中）"""
    if not 集合1:
        return set()
    if not 集合2:
        return set(集合1)
    try:
        return set(集合1) - set(集合2)
    except Exception as e:
        raise Exception("集合差集失败: " + str(e))