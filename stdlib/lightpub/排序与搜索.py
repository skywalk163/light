"""
排序与搜索 — lightpub 桥接模块

基于 Python bisect / heapq 库封装，函数名对齐上游 duanpub（段言时期）packages/排序与搜索/源.duan。

上游 duanpub 原始包通过 C FFI 实现排序与搜索算法，
本桥接模块用 Python bisect/heapq 模块替代，提供等价的排序与搜索功能。
"""

import bisect as _bisect
import heapq as _heapq
import math as _math


# =============================================================================
# 排序算法
# =============================================================================

def 选取中值(列表):
    """选取列表的中位数"""
    if not 列表:
        raise Exception("选取中值失败: 列表为空")
    try:
        sorted_list = sorted(列表)
        n = len(sorted_list)
        if n % 2 == 1:
            return sorted_list[n // 2]
        return (sorted_list[n // 2 - 1] + sorted_list[n // 2]) / 2
    except Exception as e:
        raise Exception("选取中值失败: " + str(e))


def 快排(列表):
    """快速排序，返回新列表"""
    if not 列表:
        return []
    try:
        if len(列表) <= 1:
            return list(列表)
        pivot = 列表[0]
        left = [x for x in 列表[1:] if x <= pivot]
        right = [x for x in 列表[1:] if x > pivot]
        return 快排(left) + [pivot] + 快排(right)
    except Exception as e:
        raise Exception("快排失败: " + str(e))


def 归并排(列表):
    """归并排序，返回新列表"""
    if not 列表:
        return []
    try:
        if len(列表) <= 1:
            return list(列表)
        mid = len(列表) // 2
        left = 归并排(列表[:mid])
        right = 归并排(列表[mid:])
        return 归并合并(left, right)
    except Exception as e:
        raise Exception("归并排失败: " + str(e))


def 归并合并(左列表, 右列表):
    """合并两个已排序的列表"""
    if not 左列表 and not 右列表:
        return []
    if not 左列表:
        return list(右列表)
    if not 右列表:
        return list(左列表)
    try:
        result = []
        i = j = 0
        while i < len(左列表) and j < len(右列表):
            if 左列表[i] <= 右列表[j]:
                result.append(左列表[i])
                i += 1
            else:
                result.append(右列表[j])
                j += 1
        result.extend(左列表[i:])
        result.extend(右列表[j:])
        return result
    except Exception as e:
        raise Exception("归并合并失败: " + str(e))


def 插入排(列表):
    """插入排序，返回新列表"""
    if not 列表:
        return []
    try:
        result = list(列表)
        for i in range(1, len(result)):
            key = result[i]
            j = i - 1
            while j >= 0 and result[j] > key:
                result[j + 1] = result[j]
                j -= 1
            result[j + 1] = key
        return result
    except Exception as e:
        raise Exception("插入排失败: " + str(e))


# =============================================================================
# 搜索算法
# =============================================================================

def 二分查(有序列表, 目标值):
    """在有序列表中二分查找目标值，返回索引，未找到返回-1"""
    if not 有序列表:
        return -1
    try:
        idx = _bisect.bisect_left(有序列表, 目标值)
        if idx < len(有序列表) and 有序列表[idx] == 目标值:
            return idx
        return -1
    except Exception as e:
        raise Exception("二分查失败: " + str(e))


def 模糊查(列表, 目标值, 容差=0.1):
    """在列表中模糊查找目标值（允许误差），返回索引，未找到返回-1"""
    if not 列表:
        return -1
    try:
        for i, val in enumerate(列表):
            if isinstance(val, (int, float)) and isinstance(目标值, (int, float)):
                if abs(val - 目标值) <= 容差:
                    return i
            elif val == 目标值:
                return i
        return -1
    except Exception as e:
        raise Exception("模糊查失败: " + str(e))


def 查找子串(文本, 子串):
    """在文本中查找子串，返回起始索引，未找到返回-1"""
    if not 文本 or not 子串:
        return -1
    try:
        return 文本.find(子串)
    except Exception as e:
        raise Exception("查找子串失败: " + str(e))


def 按位置排(列表, 位置列表):
    """按指定位置列表重新排列列表元素"""
    if not 列表 or not 位置列表:
        raise Exception("按位置排失败: 列表或位置列表为空")
    if len(列表) != len(位置列表):
        raise Exception("按位置排失败: 列表长度不匹配")
    try:
        result = [None] * len(列表)
        for i, pos in enumerate(位置列表):
            result[pos] = 列表[i]
        return result
    except Exception as e:
        raise Exception("按位置排失败: " + str(e))


def TopK(列表, K, 反转=False):
    """返回列表中前K个最大或最小的元素"""
    if not 列表:
        return []
    if K <= 0:
        return []
    if K > len(列表):
        K = len(列表)
    try:
        if 反转:
            return _heapq.nlargest(K, 列表)
        return _heapq.nsmallest(K, 列表)
    except Exception as e:
        raise Exception("TopK失败: " + str(e))


# =============================================================================
# 堆操作
# =============================================================================

class 最小堆对象:
    """最小堆对象"""
    def __init__(self):
        self.堆 = []


def 创建最小堆():
    """创建最小堆，返回堆对象"""
    try:
        return 最小堆对象()
    except Exception as e:
        raise Exception("创建最小堆失败: " + str(e))


def 堆上浮(堆, 索引):
    """对堆中指定索引的元素执行上浮操作"""
    if not 堆 or not 堆.堆:
        return
    if 索引 < 0 or 索引 >= len(堆.堆):
        return
    try:
        _heapq._siftup(堆.堆, 索引)
    except Exception:
        # 简化：重新堆化
        _heapq.heapify(堆.堆)


def 堆下沉(堆, 索引):
    """对堆中指定索引的元素执行下沉操作"""
    if not 堆 or not 堆.堆:
        return
    if 索引 < 0 or 索引 >= len(堆.堆):
        return
    try:
        _heapq._siftdown(堆.堆, 0, 索引)
    except Exception:
        _heapq.heapify(堆.堆)


def 堆插入(堆, 值):
    """向堆中插入一个值"""
    if not 堆:
        raise Exception("堆插入失败: 堆为空")
    try:
        _heapq.heappush(堆.堆, 值)
        return True
    except Exception as e:
        raise Exception("堆插入失败: " + str(e))


def 堆弹出(堆):
    """从堆中弹出最小值"""
    if not 堆 or not 堆.堆:
        raise Exception("堆弹出失败: 堆为空")
    try:
        return _heapq.heappop(堆.堆)
    except IndexError:
        raise Exception("堆弹出失败: 堆为空")
    except Exception as e:
        raise Exception("堆弹出失败: " + str(e))


def 堆窥视(堆):
    """查看堆顶元素但不弹出"""
    if not 堆 or not 堆.堆:
        raise Exception("堆窥视失败: 堆为空")
    try:
        return 堆.堆[0]
    except IndexError:
        raise Exception("堆窥视失败: 堆为空")
    except Exception as e:
        raise Exception("堆窥视失败: " + str(e))


def 堆是否为空(堆):
    """检查堆是否为空"""
    if not 堆:
        return True
    return len(堆.堆) == 0


def 反转列表(列表):
    """反转列表，返回新列表"""
    if not 列表:
        return []
    try:
        return list(reversed(列表))
    except Exception as e:
        raise Exception("反转列表失败: " + str(e))