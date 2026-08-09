"""
光明标准库 - 数据结构模块

提供常用数据结构实现，包括：
- 栈（Stack）
- 队列（Queue）
- 优先队列（Priority Queue）
- 链表（Linked List）
- 二叉树（Binary Tree）
"""

from collections import deque
from typing import List, Any, Optional


class 栈:
    """栈数据结构（后进先出）"""
    
    def __init__(self, 初始元素=None):
        self._数据 = list(初始元素) if 初始元素 else []
    
    def 压入(self, 元素: Any):
        """压入元素"""
        self._数据.append(元素)
    
    def 弹出(self) -> Any:
        """弹出元素"""
        if self.空():
            raise RuntimeError("栈为空")
        return self._数据.pop()
    
    def 顶部(self) -> Any:
        """获取顶部元素"""
        if self.空():
            raise RuntimeError("栈为空")
        return self._数据[-1]
    
    def 空(self) -> bool:
        """判断是否为空"""
        return len(self._数据) == 0
    
    def 大小(self) -> int:
        """获取大小"""
        return len(self._数据)
    
    def 清空(self):
        """清空栈"""
        self._数据.clear()
    
    def 转为列表(self) -> List[Any]:
        """转换为列表"""
        return list(self._数据)
    
    def __len__(self):
        return self.大小()
    
    def __bool__(self):
        return not self.空()


class 队列:
    """队列数据结构（先进先出）"""
    
    def __init__(self, 初始元素=None):
        self._数据 = list(初始元素) if 初始元素 else []
    
    def 入队(self, 元素: Any):
        """入队"""
        self._数据.append(元素)
    
    def 出队(self) -> Any:
        """出队"""
        if self.空():
            raise RuntimeError("队列为空")
        return self._数据.pop(0)
    
    def 队首(self) -> Any:
        """获取队首元素"""
        if self.空():
            raise RuntimeError("队列为空")
        return self._数据[0]
    
    def 队尾(self) -> Any:
        """获取队尾元素"""
        if self.空():
            raise RuntimeError("队列为空")
        return self._数据[-1]
    
    def 空(self) -> bool:
        """判断是否为空"""
        return len(self._数据) == 0
    
    def 大小(self) -> int:
        """获取大小"""
        return len(self._数据)
    
    def 清空(self):
        """清空队列"""
        self._数据.clear()
    
    def 转为列表(self) -> List[Any]:
        """转换为列表"""
        return list(self._数据)
    
    def __len__(self):
        return self.大小()
    
    def __bool__(self):
        return not self.空()


class 双端队列:
    """双端队列数据结构"""
    
    def __init__(self, 初始元素=None):
        self._数据 = list(初始元素) if 初始元素 else []
    
    def 左入队(self, 元素: Any):
        """从左侧入队"""
        self._数据.insert(0, 元素)
    
    def 右入队(self, 元素: Any):
        """从右侧入队"""
        self._数据.append(元素)
    
    def 左出队(self) -> Any:
        """从左侧出队"""
        if self.空():
            raise RuntimeError("队列为空")
        return self._数据.pop(0)
    
    def 右出队(self) -> Any:
        """从右侧出队"""
        if self.空():
            raise RuntimeError("队列为空")
        return self._数据.pop()
    
    def 队首(self) -> Any:
        """获取队首元素"""
        if self.空():
            raise RuntimeError("队列为空")
        return self._数据[0]
    
    def 队尾(self) -> Any:
        """获取队尾元素"""
        if self.空():
            raise RuntimeError("队列为空")
        return self._数据[-1]
    
    def 空(self) -> bool:
        """判断是否为空"""
        return len(self._数据) == 0
    
    def 大小(self) -> int:
        """获取大小"""
        return len(self._数据)
    
    def 清空(self):
        """清空队列"""
        self._数据.clear()
    
    def 转为列表(self) -> List[Any]:
        """转换为列表"""
        return list(self._数据)


class 优先队列:
    """优先队列数据结构"""
    
    def __init__(self):
        import heapq
        self._heap = []
        self._heapq = heapq
    
    def 入队(self, 优先级: int, 元素: Any):
        """入队（优先级越小越优先）"""
        self._heapq.heappush(self._heap, (优先级, 元素))
    
    def 出队(self) -> Any:
        """出队"""
        if self.空():
            raise RuntimeError("队列为空")
        return self._heapq.heappop(self._heap)[1]
    
    def 队首(self) -> Any:
        """获取队首元素"""
        if self.空():
            raise RuntimeError("队列为空")
        return self._heap[0][1]
    
    def 队首优先级(self) -> int:
        """获取队首优先级"""
        if self.空():
            raise RuntimeError("队列为空")
        return self._heap[0][0]
    
    def 空(self) -> bool:
        """判断是否为空"""
        return len(self._heap) == 0
    
    def 大小(self) -> int:
        """获取大小"""
        return len(self._heap)
    
    def 清空(self):
        """清空队列"""
        self._heap.clear()
    
    def __len__(self):
        return self.大小()
    
    def __bool__(self):
        return not self.空()


class 链表节点:
    """链表节点"""
    
    def __init__(self, 值: Any):
        self.值 = 值
        self.下一个 = None


class 单链表:
    """单链表数据结构"""
    
    def __init__(self):
        self._头节点 = None
        self._大小 = 0
    
    def 头部插入(self, 值: Any):
        """头部插入"""
        新节点 = 链表节点(值)
        新节点.下一个 = self._头节点
        self._头节点 = 新节点
        self._大小 += 1
    
    def 尾部插入(self, 值: Any):
        """尾部插入"""
        新节点 = 链表节点(值)
        if self._头节点 is None:
            self._头节点 = 新节点
        else:
            当前 = self._头节点
            while 当前.下一个 is not None:
                当前 = 当前.下一个
            当前.下一个 = 新节点
        self._大小 += 1
    
    def 指定位置插入(self, 索引: int, 值: Any):
        """指定位置插入"""
        if 索引 < 0 or 索引 > self._大小:
            raise RuntimeError("索引越界")
        if 索引 == 0:
            self.头部插入(值)
            return
        新节点 = 链表节点(值)
        当前 = self._头节点
        for _ in range(索引 - 1):
            当前 = 当前.下一个
        新节点.下一个 = 当前.下一个
        当前.下一个 = 新节点
        self._大小 += 1
    
    def 删除头部(self) -> Any:
        """删除头部"""
        if self._头节点 is None:
            raise RuntimeError("链表为空")
        值 = self._头节点.值
        self._头节点 = self._头节点.下一个
        self._大小 -= 1
        return 值
    
    def 删除尾部(self) -> Any:
        """删除尾部"""
        if self._头节点 is None:
            raise RuntimeError("链表为空")
        if self._头节点.下一个 is None:
            值 = self._头节点.值
            self._头节点 = None
            self._大小 -= 1
            return 值
        当前 = self._头节点
        while 当前.下一个.下一个 is not None:
            当前 = 当前.下一个
        值 = 当前.下一个.值
        当前.下一个 = None
        self._大小 -= 1
        return 值
    
    def 删除指定值(self, 值: Any) -> bool:
        """删除指定值"""
        if self._头节点 is None:
            return False
        if self._头节点.值 == 值:
            self._头节点 = self._头节点.下一个
            self._大小 -= 1
            return True
        当前 = self._头节点
        while 当前.下一个 is not None:
            if 当前.下一个.值 == 值:
                当前.下一个 = 当前.下一个.下一个
                self._大小 -= 1
                return True
            当前 = 当前.下一个
        return False
    
    def 查找(self, 值: Any) -> int:
        """查找值的索引"""
        当前 = self._头节点
        索引 = 0
        while 当前 is not None:
            if 当前.值 == 值:
                return 索引
            当前 = 当前.下一个
            索引 += 1
        return -1
    
    def 获取(self, 索引: int) -> Any:
        """获取指定索引的值"""
        if 索引 < 0 or 索引 >= self._大小:
            raise RuntimeError("索引越界")
        当前 = self._头节点
        for _ in range(索引):
            当前 = 当前.下一个
        return 当前.值
    
    def 修改(self, 索引: int, 值: Any):
        """修改指定索引的值"""
        if 索引 < 0 or 索引 >= self._大小:
            raise RuntimeError("索引越界")
        当前 = self._头节点
        for _ in range(索引):
            当前 = 当前.下一个
        当前.值 = 值
    
    def 空(self) -> bool:
        """判断是否为空"""
        return self._头节点 is None
    
    def 大小(self) -> int:
        """获取大小"""
        return self._大小
    
    def 清空(self):
        """清空链表"""
        self._头节点 = None
        self._大小 = 0
    
    def 转为列表(self) -> List[Any]:
        """转换为列表"""
        结果 = []
        当前 = self._头节点
        while 当前 is not None:
            结果.append(当前.值)
            当前 = 当前.下一个
        return 结果


class 二叉树节点:
    """二叉树节点"""
    
    def __init__(self, 值: Any):
        self.值 = 值
        self.左子树 = None
        self.右子树 = None


class 二叉搜索树:
    """二叉搜索树"""
    
    def __init__(self):
        self._根节点 = None
    
    def 插入(self, 值: Any):
        """插入值"""
        if self._根节点 is None:
            self._根节点 = 二叉树节点(值)
            return
        self._插入递归(self._根节点, 值)
    
    def _插入递归(self, 节点: 二叉树节点, 值: Any):
        if 值 < 节点.值:
            if 节点.左子树 is None:
                节点.左子树 = 二叉树节点(值)
            else:
                self._插入递归(节点.左子树, 值)
        else:
            if 节点.右子树 is None:
                节点.右子树 = 二叉树节点(值)
            else:
                self._插入递归(节点.右子树, 值)
    
    def 查找(self, 值: Any) -> bool:
        """查找值"""
        return self._查找递归(self._根节点, 值)
    
    def _查找递归(self, 节点: 二叉树节点, 值: Any) -> bool:
        if 节点 is None:
            return False
        if 值 == 节点.值:
            return True
        elif 值 < 节点.值:
            return self._查找递归(节点.左子树, 值)
        else:
            return self._查找递归(节点.右子树, 值)
    
    def 删除(self, 值: Any):
        """删除值"""
        self._根节点 = self._删除递归(self._根节点, 值)
    
    def _删除递归(self, 节点: 二叉树节点, 值: Any) -> Optional[二叉树节点]:
        if 节点 is None:
            return None
        if 值 < 节点.值:
            节点.左子树 = self._删除递归(节点.左子树, 值)
        elif 值 > 节点.值:
            节点.右子树 = self._删除递归(节点.右子树, 值)
        else:
            if 节点.左子树 is None:
                return 节点.右子树
            if 节点.右子树 is None:
                return 节点.左子树
            最小节点 = self._查找最小(节点.右子树)
            节点.值 = 最小节点.值
            节点.右子树 = self._删除递归(节点.右子树, 最小节点.值)
        return 节点
    
    def _查找最小(self, 节点: 二叉树节点) -> 二叉树节点:
        while 节点.左子树 is not None:
            节点 = 节点.左子树
        return 节点
    
    def 中序遍历(self) -> List[Any]:
        """中序遍历（左-根-右）"""
        结果 = []
        self._中序递归(self._根节点, 结果)
        return 结果
    
    def _中序递归(self, 节点: 二叉树节点, 结果: List[Any]):
        if 节点 is not None:
            self._中序递归(节点.左子树, 结果)
            结果.append(节点.值)
            self._中序递归(节点.右子树, 结果)
    
    def 前序遍历(self) -> List[Any]:
        """前序遍历（根-左-右）"""
        结果 = []
        self._前序递归(self._根节点, 结果)
        return 结果
    
    def _前序递归(self, 节点: 二叉树节点, 结果: List[Any]):
        if 节点 is not None:
            结果.append(节点.值)
            self._前序递归(节点.左子树, 结果)
            self._前序递归(节点.右子树, 结果)
    
    def 后序遍历(self) -> List[Any]:
        """后序遍历（左-右-根）"""
        结果 = []
        self._后序递归(self._根节点, 结果)
        return 结果
    
    def _后序递归(self, 节点: 二叉树节点, 结果: List[Any]):
        if 节点 is not None:
            self._后序递归(节点.左子树, 结果)
            self._后序递归(节点.右子树, 结果)
            结果.append(节点.值)
    
    def 层序遍历(self) -> List[Any]:
        """层序遍历"""
        if self._根节点 is None:
            return []
        结果 = []
        队列 = [self._根节点]
        while 队列:
            节点 = 队列.pop(0)
            结果.append(节点.值)
            if 节点.左子树:
                队列.append(节点.左子树)
            if 节点.右子树:
                队列.append(节点.右子树)
        return 结果
    
    def 高度(self) -> int:
        """获取树高度"""
        return self._高度递归(self._根节点)
    
    def _高度递归(self, 节点: 二叉树节点) -> int:
        if 节点 is None:
            return 0
        return 1 + max(self._高度递归(节点.左子树), self._高度递归(节点.右子树))
    
    def 大小(self) -> int:
        """获取节点数量"""
        return self._大小递归(self._根节点)
    
    def _大小递归(self, 节点: 二叉树节点) -> int:
        if 节点 is None:
            return 0
        return 1 + self._大小递归(节点.左子树) + self._大小递归(节点.右子树)
    
    def 空(self) -> bool:
        """判断是否为空"""
        return self._根节点 is None
    
    def 清空(self):
        """清空树"""
        self._根节点 = None


# =============================================================================
# 合并自队列栈.py的独有函数
# =============================================================================

# -----------------------------------------------------------------------------
# 栈操作（函数式）
# -----------------------------------------------------------------------------

def 创建栈() -> list:
    """创建空栈"""
    return []


def 入栈(栈: list, 值: Any) -> None:
    """
    将值压入栈顶

    参数:
        栈: 栈列表
        值: 要压入的值
    """
    栈.append(值)


def 出栈(栈: list) -> Any:
    """
    弹出栈顶元素

    参数:
        栈: 栈列表

    返回:
        栈顶元素

    异常:
        RuntimeError: 栈为空时
    """
    if not 栈:
        raise RuntimeError("栈为空，无法出栈")
    return 栈.pop()


def 查看栈顶(栈: list) -> Any:
    """
    查看栈顶元素（不弹出）

    参数:
        栈: 栈列表

    返回:
        栈顶元素

    异常:
        RuntimeError: 栈为空时
    """
    if not 栈:
        raise RuntimeError("栈为空，无法查看栈顶")
    return 栈[-1]


def 栈是否为空(栈: list) -> bool:
    """
    判断栈是否为空

    参数:
        栈: 栈列表

    返回:
        True 如果栈为空
    """
    return len(栈) == 0


def 栈大小(栈: list) -> int:
    """
    获取栈中元素数量

    参数:
        栈: 栈列表

    返回:
        栈中元素数量
    """
    return len(栈)


# -----------------------------------------------------------------------------
# 队列操作（函数式，基于 deque）
# -----------------------------------------------------------------------------

def 创建队列() -> deque:
    """创建空队列"""
    return deque()


def 入队(队列: deque, 值: Any) -> None:
    """
    将值加入队尾

    参数:
        队列: 队列
        值: 要加入的值
    """
    队列.append(值)


def 出队(队列: deque) -> Any:
    """
    从队首取出元素

    参数:
        队列: 队列

    返回:
        队首元素

    异常:
        RuntimeError: 队列为空时
    """
    if not 队列:
        raise RuntimeError("队列为空，无法出队")
    return 队列.popleft()


def 查看队首(队列: deque) -> Any:
    """
    查看队首元素（不取出）

    参数:
        队列: 队列

    返回:
        队首元素

    异常:
        RuntimeError: 队列为空时
    """
    if not 队列:
        raise RuntimeError("队列为空，无法查看队首")
    return 队列[0]


def 队列是否为空(队列: deque) -> bool:
    """
    判断队列是否为空

    参数:
        队列: 队列

    返回:
        True 如果队列为空
    """
    return len(队列) == 0


def 队列大小(队列: deque) -> int:
    """
    获取队列中元素数量

    参数:
        队列: 队列

    返回:
        队列中元素数量
    """
    return len(队列)


# -----------------------------------------------------------------------------
# 双端队列操作（函数式，基于 deque）
# -----------------------------------------------------------------------------

def 创建双端队列() -> deque:
    """创建空双端队列"""
    return deque()


def 左入(双端队列: deque, 值: Any) -> None:
    """
    从左端插入值

    参数:
        双端队列: 双端队列
        值: 要插入的值
    """
    双端队列.appendleft(值)


def 右入(双端队列: deque, 值: Any) -> None:
    """
    从右端插入值

    参数:
        双端队列: 双端队列
        值: 要插入的值
    """
    双端队列.append(值)


def 左出(双端队列: deque) -> Any:
    """
    从左端取出元素

    参数:
        双端队列: 双端队列

    返回:
        左端元素

    异常:
        RuntimeError: 双端队列为空时
    """
    if not 双端队列:
        raise RuntimeError("双端队列为空，无法左出")
    return 双端队列.popleft()


def 右出(双端队列: deque) -> Any:
    """
    从右端取出元素

    参数:
        双端队列: 双端队列

    返回:
        右端元素

    异常:
        RuntimeError: 双端队列为空时
    """
    if not 双端队列:
        raise RuntimeError("双端队列为空，无法右出")
    return 双端队列.pop()


def 查看左端(双端队列: deque) -> Any:
    """
    查看左端元素（不取出）

    参数:
        双端队列: 双端队列

    返回:
        左端元素

    异常:
        RuntimeError: 双端队列为空时
    """
    if not 双端队列:
        raise RuntimeError("双端队列为空，无法查看左端")
    return 双端队列[0]


def 查看右端(双端队列: deque) -> Any:
    """
    查看右端元素（不取出）

    参数:
        双端队列: 双端队列

    返回:
        右端元素

    异常:
        RuntimeError: 双端队列为空时
    """
    if not 双端队列:
        raise RuntimeError("双端队列为空，无法查看右端")
    return 双端队列[-1]


def 双端队列是否为空(双端队列: deque) -> bool:
    """
    判断双端队列是否为空

    参数:
        双端队列: 双端队列

    返回:
        True 如果双端队列为空
    """
    return len(双端队列) == 0


def 双端队列大小(双端队列: deque) -> int:
    """
    获取双端队列中元素数量

    参数:
        双端队列: 双端队列

    返回:
        双端队列中元素数量
    """
    return len(双端队列)


__all__ = [
    '栈', '队列', '双端队列', '优先队列',
    '链表节点', '单链表',
    '二叉树节点', '二叉搜索树',
    # 栈操作（函数式）
    '创建栈', '入栈', '出栈', '查看栈顶', '栈是否为空', '栈大小',
    # 队列操作（函数式）
    '创建队列', '入队', '出队', '查看队首', '队列是否为空', '队列大小',
    # 双端队列操作（函数式）
    '创建双端队列', '左入', '右入', '左出', '右出',
    '查看左端', '查看右端', '双端队列是否为空', '双端队列大小',
]