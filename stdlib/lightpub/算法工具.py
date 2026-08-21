"""
算法工具 — lightpub 桥接模块

基于 Python bisect / heapq 库封装，函数名对齐上游 duanpub（段言时期）packages/算法工具/源.duan。

上游 duanpub 原始包通过 C FFI 实现常用算法和数据结构，
本桥接模块用 Python 标准库替代，提供优先级队列、并查集、动态规划等算法功能。
"""

import heapq as _heapq
import bisect as _bisect
import itertools as _itertools
import math as _math


# =============================================================================
# 优先队列
# =============================================================================

class 优先队列:
    """优先队列（最小堆实现）"""
    def __init__(self):
        self._数据 = []
        self._索引 = 0

    def 上浮(self, 项):
        if 项 in self._数据:
            idx = self._数据.index(项)
            _heapq._siftdown(self._数据, 0, idx)

    def 下沉(self, 项):
        if 项 in self._数据:
            idx = self._数据.index(项)
            _heapq._siftup(self._数据, idx)

    def 插入(self, 优先级, 值):
        """插入元素，优先级越小越靠前"""
        _heapq.heappush(self._数据, (优先级, self._索引, 值))
        self._索引 += 1

    def 弹出(self):
        """弹出优先级最高的元素"""
        if not self._数据:
            raise Exception("优先队列弹出失败: 队列为空")
        优先级, _, 值 = _heapq.heappop(self._数据)
        return (优先级, 值)

    def 是否为空(self):
        """检查队列是否为空"""
        return len(self._数据) == 0


def 创建优先队列():
    """创建优先队列"""
    return 优先队列()


def 优先队列上浮(queue, 项):
    """优先队列上浮操作"""
    if queue:
        queue.上浮(项)


def 优先队列下沉(queue, 项):
    """优先队列下沉操作"""
    if queue:
        queue.下沉(项)


def 优先队列插入(queue, 优先级, 值):
    """向优先队列插入元素"""
    if queue:
        queue.插入(优先级, 值)


def 优先队列弹出(queue):
    """从优先队列弹出元素"""
    if queue:
        return queue.弹出()
    raise Exception("优先队列弹出失败: 队列为空")


def 优先队列是否为空(queue):
    """检查优先队列是否为空"""
    if queue:
        return queue.是否为空()
    return True


# =============================================================================
# 并查集
# =============================================================================

class 并查集:
    """并查集（Union-Find）"""
    def __init__(self):
        self._父节点 = {}
        self._秩 = {}

    def 查找(self, x):
        """查找元素所属集合（带路径压缩）"""
        if x not in self._父节点:
            self._父节点[x] = x
            self._秩[x] = 0
            return x
        if self._父节点[x] != x:
            self._父节点[x] = self.查找(self._父节点[x])
        return self._父节点[x]

    def 合并(self, x, y):
        """合并两个集合"""
        root_x = self.查找(x)
        root_y = self.查找(y)
        if root_x == root_y:
            return
        if self._秩[root_x] < self._秩[root_y]:
            self._父节点[root_x] = root_y
        elif self._秩[root_x] > self._秩[root_y]:
            self._父节点[root_y] = root_x
        else:
            self._父节点[root_y] = root_x
            self._秩[root_x] += 1


def 并查集查找(uf, x):
    """并查集查找操作"""
    if uf:
        return uf.查找(x)
    return x


def 并查集合并(uf, x, y):
    """并查集合并操作"""
    if uf:
        uf.合并(x, y)


# =============================================================================
# 背包问题
# =============================================================================

def 背包问题(重量列表, 价值列表, 容量):
    """0-1 背包问题，返回最大价值"""
    if not 重量列表 or not 价值列表:
        return 0
    if len(重量列表) != len(价值列表):
        raise Exception("背包问题失败: 重量和价值列表长度不一致")
    try:
        n = len(重量列表)
        dp = [0] * (容量 + 1)
        for i in range(n):
            for w in range(容量, 重量列表[i] - 1, -1):
                dp[w] = max(dp[w], dp[w - 重量列表[i]] + 价值列表[i])
        return dp[容量]
    except Exception as e:
        raise Exception("背包问题失败: " + str(e))


# =============================================================================
# 最长公共子序列
# =============================================================================

def 最长公共子序列(序列1, 序列2):
    """计算最长公共子序列（LCS）长度"""
    if not 序列1 or not 序列2:
        return 0
    try:
        m, n = len(序列1), len(序列2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if 序列1[i - 1] == 序列2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp[m][n]
    except Exception as e:
        raise Exception("最长公共子序列失败: " + str(e))


# =============================================================================
# 全排列
# =============================================================================

def 全排列(数据):
    """生成所有排列"""
    try:
        return list(_itertools.permutations(数据))
    except Exception as e:
        raise Exception("全排列失败: " + str(e))


def 全排列回溯(数据):
    """使用回溯法生成所有排列"""
    try:
        result = []
        used = [False] * len(数据)
        def backtrack(path):
            if len(path) == len(数据):
                result.append(tuple(path))
                return
            for i, val in enumerate(数据):
                if not used[i]:
                    used[i] = True
                    path.append(val)
                    backtrack(path)
                    path.pop()
                    used[i] = False
        backtrack([])
        return result
    except Exception as e:
        raise Exception("全排列回溯失败: " + str(e))


# =============================================================================
# 子集
# =============================================================================

def 子集(数据):
    """生成所有子集"""
    try:
        result = []
        for r in range(len(数据) + 1):
            for combo in _itertools.combinations(数据, r):
                result.append(list(combo))
        return result
    except Exception as e:
        raise Exception("子集失败: " + str(e))


def 子集回溯(数据):
    """使用回溯法生成所有子集"""
    try:
        result = []
        def backtrack(start, path):
            result.append(list(path))
            for i in range(start, len(数据)):
                path.append(数据[i])
                backtrack(i + 1, path)
                path.pop()
        backtrack(0, [])
        return result
    except Exception as e:
        raise Exception("子集回溯失败: " + str(e))


# =============================================================================
# 图算法
# =============================================================================

def Dijkstra(图, 起点):
    """Dijkstra 最短路径算法"""
    if not 图 or 起点 not in 图:
        raise Exception("Dijkstra失败: 图或起点无效")
    try:
        distances = {节点: float('inf') for 节点 in 图}
        distances[起点] = 0
        pq = [(0, 起点)]
        visited = set()

        while pq:
            current_dist, current = _heapq.heappop(pq)
            if current in visited:
                continue
            visited.add(current)
            for neighbor, weight in 图[current].items():
                if neighbor in visited:
                    continue
                distance = current_dist + weight
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    _heapq.heappush(pq, (distance, neighbor))
        return distances
    except Exception as e:
        raise Exception("Dijkstra失败: " + str(e))


def 最小生成树(图):
    """Prim 最小生成树算法"""
    if not 图:
        raise Exception("最小生成树失败: 图为空")
    try:
        start = next(iter(图))
        visited = {start}
        edges = []
        total_weight = 0

        # 初始化边集
        edge_heap = []
        for neighbor, weight in 图[start].items():
            _heapq.heappush(edge_heap, (weight, start, neighbor))

        while edge_heap and len(visited) < len(图):
            weight, u, v = _heapq.heappop(edge_heap)
            if v in visited:
                continue
            visited.add(v)
            edges.append((u, v, weight))
            total_weight += weight
            for neighbor, w in 图[v].items():
                if neighbor not in visited:
                    _heapq.heappush(edge_heap, (w, v, neighbor))

        return {
            '边': edges,
            '总权重': total_weight,
        }
    except Exception as e:
        raise Exception("最小生成树失败: " + str(e))


# =============================================================================
# 排序
# =============================================================================

def 按权重排(数据, 权重函数):
    """按权重函数排序"""
    if not 数据:
        return []
    try:
        return sorted(数据, key=权重函数)
    except Exception as e:
        raise Exception("按权重排失败: " + str(e))


def 贪心找零(面额列表, 金额):
    """贪心算法找零，返回面额列表"""
    if not 面额列表 or 金额 < 0:
        raise Exception("贪心找零失败: 参数无效")
    try:
        面额列表 = sorted(面额列表, reverse=True)
        result = []
        remaining = 金额
        for 面额 in 面额列表:
            while remaining >= 面额:
                result.append(面额)
                remaining -= 面额
        return result
    except Exception as e:
        raise Exception("贪心找零失败: " + str(e))


def 降序排(数据):
    """降序排序"""
    if not 数据:
        return []
    try:
        return sorted(数据, reverse=True)
    except Exception as e:
        raise Exception("降序排失败: " + str(e))