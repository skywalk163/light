"""
任务队列 — duanpub 桥接模块

基于 Python queue / threading / time 库封装，
函数名对齐 duanpub/packages/任务队列/源.duan。

duanpub 原始包通过 C FFI 实现任务队列系统，
本桥接模块用 Python 标准库替代，提供等价的异步/延迟/定时任务功能。
"""

import time as _time
import threading as _threading
import uuid as _uuid
from collections import deque as _deque


# =============================================================================
# 时间工具
# =============================================================================

def 取时间戳():
    """获取当前时间戳（秒）"""
    return _time.time()


# =============================================================================
# 数据结构
# =============================================================================

class _Task:
    """任务对象"""
    def __init__(self, id, 任务函数, 参数=None, 延迟=0, 定时时间=None, 优先级=0, 重试次数=0):
        self.id = id
        self.任务函数 = 任务函数
        self.参数 = 参数 or []
        self.延迟 = 延迟
        self.定时时间 = 定时时间
        self.优先级 = 优先级
        self.重试次数 = 重试次数
        self.剩余重试次数 = 重试次数
        self.状态 = 'pending'  # pending, running, completed, failed
        self.创建时间 = _time.time()
        self.错误信息 = None


class _TaskQueue:
    """任务队列"""
    def __init__(self):
        self.队列 = _deque()
        self.延迟队列 = []
        self.定时任务列表 = []
        self.已完成列表 = []
        self.失败列表 = []
        self.暂停 = False
        self.停止 = False
        self.事件监听器 = {}
        self.锁 = _threading.Lock()
        self.处理计数 = 0
        self.成功计数 = 0
        self.失败计数 = 0


# =============================================================================
# 创建任务队列
# =============================================================================

def 创建任务队列():
    """创建一个新的任务队列"""
    return _TaskQueue()


def 创建任务(任务函数, 参数=None, 优先级=0, 重试次数=0):
    """创建一个任务对象"""
    return _Task(
        id=str(_uuid.uuid4()),
        任务函数=任务函数,
        参数=参数 or [],
        优先级=优先级,
        重试次数=重试次数
    )


# =============================================================================
# 添加任务
# =============================================================================

def 任务队列添加任务(队列, 任务):
    """向队列添加一个任务"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列添加任务失败: 队列无效")
    with 队列.锁:
        队列.队列.append(任务)
    return True


def 任务队列添加任务简便(队列, 任务函数, 参数=None):
    """简便方式添加任务"""
    任务 = 创建任务(任务函数, 参数)
    return 任务队列添加任务(队列, 任务)


def 任务队列添加延迟任务(队列, 任务函数, 延迟秒数, 参数=None):
    """添加延迟任务"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列添加延迟任务失败: 队列无效")
    任务 = 创建任务(任务函数, 参数)
    任务.延迟 = 延迟秒数
    任务.创建时间 = _time.time()
    with 队列.锁:
        队列.延迟队列.append(任务)
    return True


def 任务队列添加定时任务(队列, 任务函数, 定时时间, 参数=None):
    """添加定时任务（定时时间为时间戳）"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列添加定时任务失败: 队列无效")
    任务 = 创建任务(任务函数, 参数)
    任务.定时时间 = 定时时间
    with 队列.锁:
        队列.定时任务列表.append(任务)
    return True


# =============================================================================
# 事件
# =============================================================================

def 队列触发事件(队列, 事件名, *args, **kwargs):
    """触发队列事件"""
    if not isinstance(队列, _TaskQueue):
        return
    with 队列.锁:
        监听器列表 = 队列.事件监听器.get(事件名, [])
    for 监听器 in 监听器列表:
        try:
            监听器(*args, **kwargs)
        except Exception:
            pass


def 任务队列注册事件监听器(队列, 事件名, 回调函数):
    """注册事件监听器"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列注册事件监听器失败: 队列无效")
    with 队列.锁:
        if 事件名 not in 队列.事件监听器:
            队列.事件监听器[事件名] = []
        队列.事件监听器[事件名].append(回调函数)


# =============================================================================
# 处理任务
# =============================================================================

def 任务队列处理下一个(队列):
    """处理队列中的下一个任务，返回是否成功"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列处理下一个失败: 队列无效")
    if 队列.暂停 or 队列.停止:
        return False

    # 先检查延迟任务
    now = _time.time()
    with 队列.锁:
        ready_delayed = [t for t in 队列.延迟队列 if now - t.创建时间 >= t.延迟]
        for t in ready_delayed:
            队列.延迟队列.remove(t)
            队列.队列.append(t)

        # 检查定时任务
        ready_timed = [t for t in 队列.定时任务列表 if t.定时时间 and now >= t.定时时间]
        for t in ready_timed:
            队列.定时任务列表.remove(t)
            队列.队列.append(t)

        if not 队列.队列:
            return False
        任务 = 队列.队列.popleft()

    # 执行任务
    任务.状态 = 'running'
    try:
        if 任务.参数:
            任务.任务函数(*任务.参数)
        else:
            任务.任务函数()
        任务.状态 = 'completed'
        with 队列.锁:
            队列.已完成列表.append(任务)
            队列.成功计数 += 1
            队列.处理计数 += 1
        队列触发事件(队列, 'task_completed', 任务)
        return True
    except Exception as e:
        任务.状态 = 'failed'
        任务.错误信息 = str(e)
        with 队列.锁:
            队列.失败列表.append(任务)
            队列.失败计数 += 1
            队列.处理计数 += 1
        队列触发事件(队列, 'task_failed', 任务, e)
        return False


def 任务队列处理所有(队列):
    """处理队列中所有任务"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列处理所有失败: 队列无效")
    count = 0
    while 任务队列处理下一个(队列):
        count += 1
    return count


def 任务队列处理所有异步(队列):
    """异步处理所有任务（在新线程中）"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列处理所有异步失败: 队列无效")

    def _run():
        任务队列处理所有(队列)

    t = _threading.Thread(target=_run)
    t.daemon = True
    t.start()
    return t


# =============================================================================
# 队列控制
# =============================================================================

def 任务队列暂停(队列):
    """暂停队列处理"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列暂停失败: 队列无效")
    队列.暂停 = True


def 任务队列恢复(队列):
    """恢复队列处理"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列恢复失败: 队列无效")
    队列.暂停 = False


def 任务队列停止(队列):
    """停止队列处理"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列停止失败: 队列无效")
    队列.停止 = True


# =============================================================================
# 统计与查询
# =============================================================================

def 任务队列获取统计(队列):
    """获取队列统计信息"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列获取统计失败: 队列无效")
    with 队列.锁:
        return {
            '待处理': len(队列.队列),
            '延迟任务': len(队列.延迟队列),
            '定时任务': len(队列.定时任务列表),
            '已完成': len(队列.已完成列表),
            '失败': len(队列.失败列表),
            '处理总数': 队列.处理计数,
            '成功数': 队列.成功计数,
            '失败数': 队列.失败计数,
            '暂停中': 队列.暂停,
            '已停止': 队列.停止,
        }


def 任务队列获取任务(队列, 任务id):
    """根据任务ID获取任务"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列获取任务失败: 队列无效")
    with 队列.锁:
        for 列表 in [队列.队列, 队列.延迟队列, 队列.定时任务列表, 队列.已完成列表, 队列.失败列表]:
            for t in 列表:
                if t.id == 任务id:
                    return t
    return None


def 任务队列重试失败任务(队列):
    """重试所有失败任务"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列重试失败任务失败: 队列无效")
    with 队列.锁:
        failed = list(队列.失败列表)
        队列.失败列表.clear()
        for t in failed:
            t.状态 = 'pending'
            t.错误信息 = None
            队列.队列.append(t)
    return len(failed)


def 任务队列清理已完成(队列):
    """清理已完成的任务"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列清理已完成失败: 队列无效")
    with 队列.锁:
        count = len(队列.已完成列表)
        队列.已完成列表.clear()
    return count


# =============================================================================
# 定时任务处理
# =============================================================================

def 任务队列处理定时任务(队列):
    """处理到期的定时任务，将其加入主队列"""
    if not isinstance(队列, _TaskQueue):
        raise Exception("任务队列处理定时任务失败: 队列无效")
    now = _time.time()
    count = 0
    with 队列.锁:
        ready = [t for t in 队列.定时任务列表 if t.定时时间 and now >= t.定时时间]
        for t in ready:
            队列.定时任务列表.remove(t)
            队列.队列.append(t)
            count += 1
    return count


def 检查定时(队列):
    """检查定时任务状态，返回已到期数量"""
    return 任务队列处理定时任务(队列)