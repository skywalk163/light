"""
协程 — duanpub 桥接模块

基于 Python asyncio 库封装，函数名对齐 duanpub/packages/协程/源.duan。

duanpub 原始包通过 C FFI 实现协程调度、通道通信、生成器、选择器，
本桥接模块用 Python asyncio 模块替代，提供等价的协程功能。
"""

import asyncio as _asyncio
import inspect as _inspect
from collections import deque as _deque


# =============================================================================
# 调度器
# =============================================================================

class _Scheduler:
    """协程调度器"""
    def __init__(self):
        self._coros = {}
        self._running = False
        self._loop = None
        self._counter = 0

    def _next_id(self):
        self._counter += 1
        return f"coro_{self._counter}"


def createScheduler():
    """创建协程调度器"""
    try:
        return _Scheduler()
    except Exception as e:
        raise Exception("createScheduler失败: " + str(e))


def schedulerCreateCoro(scheduler, coro_func, *args):
    """在调度器中创建协程"""
    if not scheduler:
        raise Exception("schedulerCreateCoro失败: scheduler为空")
    try:
        coro_id = scheduler._next_id()
        scheduler._coros[coro_id] = {
            'id': coro_id,
            'func': coro_func,
            'args': args,
            'coro': None,
            'status': 'created',
            'result': None,
            'error': None,
        }
        return coro_id
    except Exception as e:
        raise Exception("schedulerCreateCoro失败: " + str(e))


def schedulerStartCoro(scheduler, coro_id):
    """启动协程"""
    if not scheduler:
        raise Exception("schedulerStartCoro失败: scheduler为空")
    if coro_id not in scheduler._coros:
        raise Exception("schedulerStartCoro失败: 协程不存在 " + str(coro_id))
    try:
        info = scheduler._coros[coro_id]
        if info['status'] != 'created':
            raise Exception("schedulerStartCoro失败: 协程状态不是created")
        coro = info['func'](*info['args'])
        if _inspect.iscoroutine(coro):
            info['coro'] = coro
            info['status'] = 'running'
            if scheduler._loop and scheduler._loop.is_running():
                task = scheduler._loop.create_task(coro)
                info['task'] = task
        else:
            info['result'] = coro
            info['status'] = 'completed'
        return True
    except Exception as e:
        raise Exception("schedulerStartCoro失败: " + str(e))


def schedulerSuspendCoro(scheduler, coro_id):
    """挂起协程"""
    if not scheduler:
        raise Exception("schedulerSuspendCoro失败: scheduler为空")
    if coro_id not in scheduler._coros:
        raise Exception("schedulerSuspendCoro失败: 协程不存在")
    try:
        info = scheduler._coros[coro_id]
        if info['status'] == 'running':
            info['status'] = 'suspended'
            return True
        raise Exception("schedulerSuspendCoro失败: 协程未运行")
    except Exception as e:
        raise Exception("schedulerSuspendCoro失败: " + str(e))


def schedulerResumeCoro(scheduler, coro_id):
    """恢复协程"""
    if not scheduler:
        raise Exception("schedulerResumeCoro失败: scheduler为空")
    if coro_id not in scheduler._coros:
        raise Exception("schedulerResumeCoro失败: 协程不存在")
    try:
        info = scheduler._coros[coro_id]
        if info['status'] == 'suspended':
            info['status'] = 'running'
            return True
        raise Exception("schedulerResumeCoro失败: 协程未挂起")
    except Exception as e:
        raise Exception("schedulerResumeCoro失败: " + str(e))


def schedulerCancelCoro(scheduler, coro_id):
    """取消协程"""
    if not scheduler:
        raise Exception("schedulerCancelCoro失败: scheduler为空")
    if coro_id not in scheduler._coros:
        raise Exception("schedulerCancelCoro失败: 协程不存在")
    try:
        info = scheduler._coros[coro_id]
        if 'task' in info:
            info['task'].cancel()
        info['status'] = 'cancelled'
        return True
    except Exception as e:
        raise Exception("schedulerCancelCoro失败: " + str(e))


def schedulerRunStep(scheduler):
    """运行协程调度器一步"""
    if not scheduler:
        raise Exception("schedulerRunStep失败: scheduler为空")
    try:
        for coro_id, info in scheduler._coros.items():
            if info['status'] == 'running' and 'task' in info:
                if info['task'].done():
                    try:
                        info['result'] = info['task'].result()
                        info['status'] = 'completed'
                    except Exception as e:
                        info['error'] = str(e)
                        info['status'] = 'failed'
                    return True
        return False
    except Exception as e:
        raise Exception("schedulerRunStep失败: " + str(e))


def schedulerRunAll(scheduler):
    """运行所有协程直到完成"""
    if not scheduler:
        raise Exception("schedulerRunAll失败: scheduler为空")
    try:
        scheduler._loop = _asyncio.new_event_loop()
        tasks = []
        for coro_id, info in scheduler._coros.items():
            if info['status'] == 'running' and info['coro']:
                tasks.append(info['coro'])
        if tasks:
            scheduler._loop.run_until_complete(_asyncio.gather(*tasks, return_exceptions=True))
        for coro_id, info in scheduler._coros.items():
            if info['status'] == 'running':
                info['status'] = 'completed'
        return True
    except Exception as e:
        raise Exception("schedulerRunAll失败: " + str(e))
    finally:
        if scheduler._loop:
            scheduler._loop.close()
            scheduler._loop = None


def schedulerRun(scheduler):
    """运行调度器"""
    return schedulerRunAll(scheduler)


def schedulerStop(scheduler):
    """停止调度器"""
    if not scheduler:
        raise Exception("schedulerStop失败: scheduler为空")
    try:
        for coro_id, info in scheduler._coros.items():
            if info['status'] in ('running', 'suspended'):
                if 'task' in info:
                    info['task'].cancel()
                info['status'] = 'cancelled'
        if scheduler._loop and scheduler._loop.is_running():
            scheduler._loop.stop()
        return True
    except Exception as e:
        raise Exception("schedulerStop失败: " + str(e))


def schedulerGetCoro(scheduler, coro_id):
    """获取协程信息"""
    if not scheduler:
        raise Exception("schedulerGetCoro失败: scheduler为空")
    if coro_id not in scheduler._coros:
        raise Exception("schedulerGetCoro失败: 协程不存在")
    return scheduler._coros[coro_id]


def schedulerGetAllCoros(scheduler):
    """获取所有协程"""
    if not scheduler:
        raise Exception("schedulerGetAllCoros失败: scheduler为空")
    return list(scheduler._coros.values())


def schedulerGetStats(scheduler):
    """获取调度器统计"""
    if not scheduler:
        raise Exception("schedulerGetStats失败: scheduler为空")
    statuses = {}
    for info in scheduler._coros.values():
        s = info['status']
        statuses[s] = statuses.get(s, 0) + 1
    return {
        'total': len(scheduler._coros),
        'statuses': statuses,
    }


def schedulerWaitCoro(scheduler, coro_id):
    """等待单个协程完成"""
    if not scheduler:
        raise Exception("schedulerWaitCoro失败: scheduler为空")
    if coro_id not in scheduler._coros:
        raise Exception("schedulerWaitCoro失败: 协程不存在")
    try:
        info = scheduler._coros[coro_id]
        if 'task' in info:
            scheduler._loop = scheduler._loop or _asyncio.new_event_loop()
            scheduler._loop.run_until_complete(info['task'])
        info['status'] = 'completed'
        return info['result']
    except Exception as e:
        raise Exception("schedulerWaitCoro失败: " + str(e))


def schedulerWaitAll(scheduler):
    """等待所有协程完成"""
    if not scheduler:
        raise Exception("schedulerWaitAll失败: scheduler为空")
    return schedulerRunAll(scheduler)


def schedulerWaitAny(scheduler):
    """等待任意协程完成"""
    if not scheduler:
        raise Exception("schedulerWaitAny失败: scheduler为空")
    try:
        for coro_id, info in scheduler._coros.items():
            if info['status'] == 'completed':
                return coro_id
            if 'task' in info and info['task'].done():
                info['status'] = 'completed'
                return coro_id
        return None
    except Exception as e:
        raise Exception("schedulerWaitAny失败: " + str(e))


def schedulerYield(scheduler):
    """让出协程执行权"""
    if not scheduler:
        raise Exception("schedulerYield失败: scheduler为空")
    try:
        scheduler._loop = scheduler._loop or _asyncio.get_event_loop()
        if scheduler._loop and scheduler._loop.is_running():
            return True
        return False
    except Exception:
        return False


# =============================================================================
# 通道 (Channel)
# =============================================================================

class _Channel:
    """协程通道"""
    def __init__(self, capacity=0):
        self._queue = _asyncio.Queue(capacity) if capacity > 0 else _asyncio.Queue()
        self._closed = False
        self._capacity = capacity


def createChannel():
    """创建无缓冲通道"""
    try:
        return _Channel(capacity=0)
    except Exception as e:
        raise Exception("createChannel失败: " + str(e))


def createBufferedChannel(capacity):
    """创建有缓冲通道"""
    if capacity < 0:
        raise Exception("createBufferedChannel失败: 容量不能为负数")
    try:
        return _Channel(capacity=capacity)
    except Exception as e:
        raise Exception("createBufferedChannel失败: " + str(e))


def channelSend(ch, value):
    """向通道发送数据"""
    if not ch:
        raise Exception("channelSend失败: 通道为空")
    if ch._closed:
        raise Exception("channelSend失败: 通道已关闭")
    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            loop.run_until_complete(ch._queue.put(value))
        else:
            ch._queue.put_nowait(value)
        return True
    except _asyncio.QueueFull:
        raise Exception("channelSend失败: 通道已满")
    except Exception as e:
        raise Exception("channelSend失败: " + str(e))


def channelRecv(ch):
    """从通道接收数据"""
    if not ch:
        raise Exception("channelRecv失败: 通道为空")
    if ch._closed and ch._queue.empty():
        raise Exception("channelRecv失败: 通道已关闭且为空")
    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(ch._queue.get())
        return ch._queue.get_nowait()
    except _asyncio.QueueEmpty:
        raise Exception("channelRecv失败: 通道为空")
    except Exception as e:
        raise Exception("channelRecv失败: " + str(e))


def channelTrySend(ch, value):
    """尝试向通道发送数据（非阻塞）"""
    if not ch:
        raise Exception("channelTrySend失败: 通道为空")
    if ch._closed:
        return False
    try:
        ch._queue.put_nowait(value)
        return True
    except (_asyncio.QueueFull, Exception):
        return False


def channelTryRecv(ch):
    """尝试从通道接收数据（非阻塞）"""
    if not ch:
        raise Exception("channelTryRecv失败: 通道为空")
    try:
        return ch._queue.get_nowait()
    except (_asyncio.QueueEmpty, Exception):
        return None


def channelClose(ch):
    """关闭通道"""
    if not ch:
        raise Exception("channelClose失败: 通道为空")
    ch._closed = True
    return True


def channelIsClosed(ch):
    """检查通道是否已关闭"""
    if not ch:
        raise Exception("channelIsClosed失败: 通道为空")
    return ch._closed


def channelLen(ch):
    """获取通道当前长度"""
    if not ch:
        raise Exception("channelLen失败: 通道为空")
    return ch._queue.qsize()


def channelCap(ch):
    """获取通道容量"""
    if not ch:
        raise Exception("channelCap失败: 通道为空")
    return ch._capacity


def channelClear(ch):
    """清空通道"""
    if not ch:
        raise Exception("channelClear失败: 通道为空")
    try:
        while not ch._queue.empty():
            ch._queue.get_nowait()
        return True
    except Exception as e:
        raise Exception("channelClear失败: " + str(e))


# =============================================================================
# 选择器 (Selector)
# =============================================================================

class _Selector:
    """通道选择器"""
    def __init__(self):
        self._send_cases = []
        self._recv_cases = []
        self._default = None


def createSelector():
    """创建选择器"""
    try:
        return _Selector()
    except Exception as e:
        raise Exception("createSelector失败: " + str(e))


def selectorAddSend(sel, ch, value):
    """添加发送选择分支"""
    if not sel:
        raise Exception("selectorAddSend失败: selector为空")
    if not ch:
        raise Exception("selectorAddSend失败: 通道为空")
    sel._send_cases.append((ch, value))
    return True


def selectorAddRecv(sel, ch):
    """添加接收选择分支"""
    if not sel:
        raise Exception("selectorAddRecv失败: selector为空")
    if not ch:
        raise Exception("selectorAddRecv失败: 通道为空")
    sel._recv_cases.append(ch)
    return True


def selectorSetDefault(sel, callback):
    """设置默认选择分支"""
    if not sel:
        raise Exception("selectorSetDefault失败: selector为空")
    sel._default = callback
    return True


def selectorSelect(sel):
    """执行选择，返回第一个就绪的通道操作结果"""
    if not sel:
        raise Exception("selectorSelect失败: selector为空")
    try:
        for ch, value in sel._send_cases:
            if not ch._closed and ch._queue.qsize() < (ch._capacity if ch._capacity > 0 else 1):
                ch._queue.put_nowait(value)
                return ('send', ch, value)
        for ch in sel._recv_cases:
            if not ch._queue.empty():
                val = ch._queue.get_nowait()
                return ('recv', ch, val)
        if sel._default:
            sel._default()
            return ('default', None, None)
        return None
    except Exception as e:
        raise Exception("selectorSelect失败: " + str(e))


# =============================================================================
# 生成器 (Generator)
# =============================================================================

class _Generator:
    """协程生成器"""
    def __init__(self, gen_func, *args):
        self._gen = gen_func(*args) if args else gen_func()
        self._exhausted = False

    def next(self):
        return generatorNext(self)


def createGenerator(gen_func, *args):
    """创建生成器"""
    if not gen_func:
        raise Exception("createGenerator失败: 生成器函数为空")
    try:
        return _Generator(gen_func, *args)
    except Exception as e:
        raise Exception("createGenerator失败: " + str(e))


def generatorNext(gen):
    """获取生成器下一个值"""
    if not gen:
        raise Exception("generatorNext失败: generator为空")
    if gen._exhausted:
        raise Exception("generatorNext失败: 生成器已耗尽")
    try:
        value = next(gen._gen)
        return value
    except StopIteration:
        gen._exhausted = True
        raise Exception("generatorNext失败: 生成器已耗尽")
    except Exception as e:
        gen._exhausted = True
        raise Exception("generatorNext失败: " + str(e))


def generatorCollect(gen):
    """收集生成器所有值"""
    if not gen:
        raise Exception("generatorCollect失败: generator为空")
    try:
        results = list(gen._gen)
        gen._exhausted = True
        return results
    except Exception as e:
        raise Exception("generatorCollect失败: " + str(e))


def generatorReset(gen):
    """重置生成器"""
    if not gen:
        raise Exception("generatorReset失败: generator为空")
    gen._exhausted = False
    return True