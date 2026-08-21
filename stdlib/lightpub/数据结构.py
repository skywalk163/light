"""
数据结构 — lightpub 桥接模块

基于 Python collections 库封装，函数名对齐上游 duanpub（段言时期）packages/数据结构/源.duan。

上游 duanpub 原始包通过 C FFI 实现链表、栈、队列、堆、树、图等数据结构，
本桥接模块用 Python 标准库实现，提供等价的数据结构功能。
"""

import heapq as _heapq


# =============================================================================
# 链表
# =============================================================================

class 链表节点:
    """链表节点"""
    def __init__(self, 值):
        self.值 = 值
        self.下一个 = None


class 链表对象:
    """链表对象"""
    def __init__(self):
        self.头 = None
        self.长度 = 0


def 创建链表节点(值):
    """创建链表节点"""
    try:
        return 链表节点(值)
    except Exception as e:
        raise Exception("创建链表节点失败: " + str(e))


def 创建链表():
    """创建空链表"""
    try:
        return 链表对象()
    except Exception as e:
        raise Exception("创建链表失败: " + str(e))


def 链表追加(链表, 值):
    """向链表追加元素"""
    if not 链表:
        raise Exception("链表追加失败: 链表为空")
    try:
        new_node = 链表节点(值)
        if not 链表.头:
            链表.头 = new_node
        else:
            cur = 链表.头
            while cur.下一个:
                cur = cur.下一个
            cur.下一个 = new_node
        链表.长度 += 1
        return True
    except Exception as e:
        raise Exception("链表追加失败: " + str(e))


def 链表插入(链表, 索引, 值):
    """在链表指定位置插入元素"""
    if not 链表:
        raise Exception("链表插入失败: 链表为空")
    if 索引 < 0 or 索引 > 链表.长度:
        raise Exception("链表插入失败: 索引越界")
    try:
        new_node = 链表节点(值)
        if 索引 == 0:
            new_node.下一个 = 链表.头
            链表.头 = new_node
        else:
            cur = 链表.头
            for _ in range(索引 - 1):
                cur = cur.下一个
            new_node.下一个 = cur.下一个
            cur.下一个 = new_node
        链表.长度 += 1
        return True
    except Exception as e:
        raise Exception("链表插入失败: " + str(e))


def 链表删除(链表, 索引):
    """删除链表指定位置的元素"""
    if not 链表:
        raise Exception("链表删除失败: 链表为空")
    if 索引 < 0 or 索引 >= 链表.长度:
        raise Exception("链表删除失败: 索引越界")
    try:
        if 索引 == 0:
            链表.头 = 链表.头.下一个
        else:
            cur = 链表.头
            for _ in range(索引 - 1):
                cur = cur.下一个
            cur.下一个 = cur.下一个.下一个
        链表.长度 -= 1
        return True
    except Exception as e:
        raise Exception("链表删除失败: " + str(e))


def 链表获取(链表, 索引):
    """获取链表指定位置的元素值"""
    if not 链表:
        raise Exception("链表获取失败: 链表为空")
    if 索引 < 0 or 索引 >= 链表.长度:
        raise Exception("链表获取失败: 索引越界")
    try:
        cur = 链表.头
        for _ in range(索引):
            cur = cur.下一个
        return cur.值
    except Exception as e:
        raise Exception("链表获取失败: " + str(e))


def 链表长度获取(链表):
    """获取链表长度"""
    if not 链表:
        return 0
    return 链表.长度


def 链表转为列表(链表):
    """将链表转为Python列表"""
    if not 链表:
        return []
    try:
        result = []
        cur = 链表.头
        while cur:
            result.append(cur.值)
            cur = cur.下一个
        return result
    except Exception as e:
        raise Exception("链表转为列表失败: " + str(e))


# =============================================================================
# 栈
# =============================================================================

class 栈对象:
    """栈对象"""
    def __init__(self):
        self.栈 = []


def 创建栈():
    """创建空栈"""
    try:
        return 栈对象()
    except Exception as e:
        raise Exception("创建栈失败: " + str(e))


def 栈压入(栈, 值):
    """向栈中压入元素"""
    if not 栈:
        raise Exception("栈压入失败: 栈为空")
    try:
        栈.栈.append(值)
        return True
    except Exception as e:
        raise Exception("栈压入失败: " + str(e))


def 栈弹出(栈):
    """从栈中弹出元素"""
    if not 栈 or not 栈.栈:
        raise Exception("栈弹出失败: 栈为空")
    try:
        return 栈.栈.pop()
    except IndexError:
        raise Exception("栈弹出失败: 栈为空")
    except Exception as e:
        raise Exception("栈弹出失败: " + str(e))


def 栈窥视(栈):
    """查看栈顶元素但不弹出"""
    if not 栈 or not 栈.栈:
        raise Exception("栈窥视失败: 栈为空")
    try:
        return 栈.栈[-1]
    except IndexError:
        raise Exception("栈窥视失败: 栈为空")
    except Exception as e:
        raise Exception("栈窥视失败: " + str(e))


def 栈大小(栈):
    """获取栈的大小"""
    if not 栈:
        return 0
    return len(栈.栈)


def 栈是否为空(栈):
    """检查栈是否为空"""
    if not 栈:
        return True
    return len(栈.栈) == 0


# =============================================================================
# 队列
# =============================================================================

class 队列对象:
    """队列对象"""
    def __init__(self):
        from collections import deque as _deque
        self.队列 = _deque()


def 创建队列():
    """创建空队列"""
    try:
        return 队列对象()
    except Exception as e:
        raise Exception("创建队列失败: " + str(e))


def 队列入队(队列, 值):
    """向队列尾部入队"""
    if not 队列:
        raise Exception("队列入队失败: 队列为空")
    try:
        队列.队列.append(值)
        return True
    except Exception as e:
        raise Exception("队列入队失败: " + str(e))


def 队列出队(队列):
    """从队列头部出队"""
    if not 队列 or not 队列.队列:
        raise Exception("队列出队失败: 队列为空")
    try:
        return 队列.队列.popleft()
    except IndexError:
        raise Exception("队列出队失败: 队列为空")
    except Exception as e:
        raise Exception("队列出队失败: " + str(e))


def 队列窥视(队列):
    """查看队列头部元素但不移除"""
    if not 队列 or not 队列.队列:
        raise Exception("队列窥视失败: 队列为空")
    try:
        return 队列.队列[0]
    except IndexError:
        raise Exception("队列窥视失败: 队列为空")
    except Exception as e:
        raise Exception("队列窥视失败: " + str(e))


def 队列大小(队列):
    """获取队列的大小"""
    if not 队列:
        return 0
    return len(队列.队列)


def 队列是否为空(队列):
    """检查队列是否为空"""
    if not 队列:
        return True
    return len(队列.队列) == 0


# =============================================================================
# 堆
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


# =============================================================================
# 树
# =============================================================================

class 树节点:
    """树节点"""
    def __init__(self, 值):
        self.值 = 值
        self.左 = None
        self.右 = None


class 二叉树对象:
    """二叉树对象"""
    def __init__(self):
        self.根 = None


def 创建树节点(值):
    """创建树节点"""
    try:
        return 树节点(值)
    except Exception as e:
        raise Exception("创建树节点失败: " + str(e))


def 创建二叉树():
    """创建空二叉树"""
    try:
        return 二叉树对象()
    except Exception as e:
        raise Exception("创建二叉树失败: " + str(e))


def 二叉树插入(二叉树, 值):
    """向二叉搜索树中插入值"""
    if not 二叉树:
        raise Exception("二叉树插入失败: 二叉树为空")
    try:
        new_node = 树节点(值)
        if not 二叉树.根:
            二叉树.根 = new_node
            return True
        cur = 二叉树.根
        while True:
            if 值 < cur.值:
                if cur.左 is None:
                    cur.左 = new_node
                    return True
                cur = cur.左
            else:
                if cur.右 is None:
                    cur.右 = new_node
                    return True
                cur = cur.右
    except Exception as e:
        raise Exception("二叉树插入失败: " + str(e))


def 二叉树包含(二叉树, 值):
    """检查二叉树中是否包含指定值"""
    if not 二叉树 or not 二叉树.根:
        return False
    try:
        cur = 二叉树.根
        while cur:
            if 值 == cur.值:
                return True
            elif 值 < cur.值:
                cur = cur.左
            else:
                cur = cur.右
        return False
    except Exception as e:
        raise Exception("二叉树包含失败: " + str(e))


def 中序遍递归(节点):
    """中序遍历递归辅助函数，返回值列表"""
    if not 节点:
        return []
    try:
        return 中序遍递归(节点.左) + [节点.值] + 中序遍递归(节点.右)
    except Exception as e:
        raise Exception("中序遍递归失败: " + str(e))


def 二叉树中序遍(二叉树):
    """中序遍历二叉树，返回值列表"""
    if not 二叉树:
        return []
    return 中序遍递归(二叉树.根)


def 前序遍递归(节点):
    """前序遍历递归辅助函数，返回值列表"""
    if not 节点:
        return []
    try:
        return [节点.值] + 前序遍递归(节点.左) + 前序遍递归(节点.右)
    except Exception as e:
        raise Exception("前序遍递归失败: " + str(e))


def 二叉树前序遍(二叉树):
    """前序遍历二叉树，返回值列表"""
    if not 二叉树:
        return []
    return 前序遍递归(二叉树.根)


def 后序遍递归(节点):
    """后序遍历递归辅助函数，返回值列表"""
    if not 节点:
        return []
    try:
        return 后序遍递归(节点.左) + 后序遍递归(节点.右) + [节点.值]
    except Exception as e:
        raise Exception("后序遍递归失败: " + str(e))


def 二叉树后序遍(二叉树):
    """后序遍历二叉树，返回值列表"""
    if not 二叉树:
        return []
    return 后序遍递归(二叉树.根)


# =============================================================================
# 图
# =============================================================================

class 图对象:
    """图对象"""
    def __init__(self):
        self.邻接表 = {}  # {节点: {邻居节点: 权重}}
        self.节点数 = 0
        self.边数 = 0


def 创建图():
    """创建空图"""
    try:
        return 图对象()
    except Exception as e:
        raise Exception("创建图失败: " + str(e))


def 图添加节点(图, 节点):
    """向图中添加节点"""
    if not 图:
        raise Exception("图添加节点失败: 图为空")
    try:
        if 节点 not in 图.邻接表:
            图.邻接表[节点] = {}
            图.节点数 += 1
        return True
    except Exception as e:
        raise Exception("图添加节点失败: " + str(e))


def 图添加边(图, 节点1, 节点2, 权重=1):
    """向图中添加边（无向图）"""
    if not 图:
        raise Exception("图添加边失败: 图为空")
    try:
        if 节点1 not in 图.邻接表:
            图添加节点(图, 节点1)
        if 节点2 not in 图.邻接表:
            图添加节点(图, 节点2)
        图.邻接表[节点1][节点2] = 权重
        图.邻接表[节点2][节点1] = 权重
        图.边数 += 1
        return True
    except Exception as e:
        raise Exception("图添加边失败: " + str(e))


def 图邻居(图, 节点):
    """获取图中指定节点的邻居列表"""
    if not 图:
        raise Exception("图邻居失败: 图为空")
    if 节点 not in 图.邻接表:
        return []
    try:
        return list(图.邻接表[节点].keys())
    except Exception as e:
        raise Exception("图邻居失败: " + str(e))


def 图节点数(图):
    """获取图的节点数"""
    if not 图:
        return 0
    return 图.节点数


def 图边数(图):
    """获取图的边数"""
    if not 图:
        return 0
    return 图.边数


def 图包含边(图, 节点1, 节点2):
    """检查图中是否存在边"""
    if not 图:
        return False
    if 节点1 not in 图.邻接表:
        return False
    return 节点2 in 图.邻接表[节点1]


# =============================================================================
# 哈希表增强
# =============================================================================

class 哈希表对象:
    """哈希表增强对象"""
    def __init__(self):
        self.数据 = {}


def 创建哈希表增强():
    """创建增强哈希表"""
    try:
        return 哈希表对象()
    except Exception as e:
        raise Exception("创建哈希表增强失败: " + str(e))


def 哈希表设置(哈希表, 键, 值):
    """设置哈希表中的键值对"""
    if not 哈希表:
        raise Exception("哈希表设置失败: 哈希表为空")
    try:
        哈希表.数据[键] = 值
        return True
    except Exception as e:
        raise Exception("哈希表设置失败: " + str(e))


def 哈希表获取(哈希表, 键, 默认值=None):
    """获取哈希表中指定键的值"""
    if not 哈希表:
        raise Exception("哈希表获取失败: 哈希表为空")
    try:
        return 哈希表.数据.get(键, 默认值)
    except Exception as e:
        raise Exception("哈希表获取失败: " + str(e))


def 哈希表删除(哈希表, 键):
    """删除哈希表中指定键的键值对"""
    if not 哈希表:
        raise Exception("哈希表删除失败: 哈希表为空")
    try:
        if 键 in 哈希表.数据:
            del 哈希表.数据[键]
            return True
        return False
    except Exception as e:
        raise Exception("哈希表删除失败: " + str(e))


def 哈希表包含(哈希表, 键):
    """检查哈希表中是否包含指定键"""
    if not 哈希表:
        return False
    return 键 in 哈希表.数据


def 哈希表键列表(哈希表):
    """获取哈希表中所有键的列表"""
    if not 哈希表:
        return []
    try:
        return list(哈希表.数据.keys())
    except Exception as e:
        raise Exception("哈希表键列表失败: " + str(e))


def 哈希表值列表(哈希表):
    """获取哈希表中所有值的列表"""
    if not 哈希表:
        return []
    try:
        return list(哈希表.数据.values())
    except Exception as e:
        raise Exception("哈希表值列表失败: " + str(e))


def 哈希表条目列表(哈希表):
    """获取哈希表中所有条目的列表"""
    if not 哈希表:
        return []
    try:
        return list(哈希表.数据.items())
    except Exception as e:
        raise Exception("哈希表条目列表失败: " + str(e))