"""
线程 — lightpub 桥接模块

基于 Python threading 库封装，函数名对齐上游 duanpub（段言时期）packages/线程/源.duan。

上游 duanpub 原始包通过 C FFI 直接调用操作系统线程 API，
本桥接模块用 Python threading 模块替代，提供等价的线程与同步原语功能。
"""

import threading as _threading
import time as _time


# =============================================================================
# 线程管理
# =============================================================================

class 线程对象:
    """线程对象包装"""
    def __init__(self, 线程):
        self.线程 = 线程


def 创建线程(目标函数, 参数=None, 名称=''):
    """创建并启动一个新线程，返回线程对象"""
    if 参数 is None:
        参数 = ()
    try:
        线程 = _threading.Thread(target=目标函数, args=参数, name=名称)
        线程.daemon = False
        线程.start()
        return 线程对象(线程)
    except Exception as e:
        raise Exception("创建线程失败: " + str(e))


def 等待线程(线程):
    """等待线程结束"""
    if not 线程 or not 线程.线程:
        raise Exception("等待线程失败: 线程为空")
    try:
        线程.线程.join()
    except Exception as e:
        raise Exception("等待线程失败: " + str(e))


def 分离线程(线程):
    """分离线程，使其独立运行"""
    if not 线程 or not 线程.线程:
        raise Exception("分离线程失败: 线程为空")
    try:
        线程.线程.daemon = True
    except Exception as e:
        raise Exception("分离线程失败: " + str(e))


def 获取线程号(线程):
    """获取线程的标识号"""
    if not 线程 or not 线程.线程:
        raise Exception("获取线程号失败: 线程为空")
    return 线程.线程.ident or 0


def 当前线程号():
    """获取当前线程的标识号"""
    return _threading.current_thread().ident or 0


def 线程休眠(秒数):
    """当前线程休眠指定秒数"""
    _time.sleep(秒数)


def 线程让出():
    """让出当前线程的CPU时间片"""
    _time.sleep(0)


# =============================================================================
# 互斥锁
# =============================================================================

class 互斥锁对象:
    """互斥锁对象"""
    def __init__(self):
        self.锁 = _threading.Lock()


def 创建互斥锁():
    """创建互斥锁，返回互斥锁对象"""
    try:
        return 互斥锁对象()
    except Exception as e:
        raise Exception("创建互斥锁失败: " + str(e))


def 互斥锁锁定(互斥锁):
    """锁定互斥锁"""
    if not 互斥锁 or not 互斥锁.锁:
        raise Exception("互斥锁锁定失败: 互斥锁为空")
    try:
        互斥锁.锁.acquire()
        return True
    except Exception as e:
        raise Exception("互斥锁锁定失败: " + str(e))


def 互斥锁尝试锁定(互斥锁):
    """尝试锁定互斥锁，立即返回True/False"""
    if not 互斥锁 or not 互斥锁.锁:
        raise Exception("互斥锁尝试锁定失败: 互斥锁为空")
    try:
        return 互斥锁.锁.acquire(blocking=False)
    except Exception as e:
        return False


def 互斥锁解锁(互斥锁):
    """解锁互斥锁"""
    if not 互斥锁 or not 互斥锁.锁:
        raise Exception("互斥锁解锁失败: 互斥锁为空")
    try:
        互斥锁.锁.release()
        return True
    except Exception as e:
        raise Exception("互斥锁解锁失败: " + str(e))


def 互斥锁销毁(互斥锁):
    """销毁互斥锁"""
    if not 互斥锁:
        return
    互斥锁.锁 = None


# =============================================================================
# 信号量
# =============================================================================

class 信号量对象:
    """信号量对象"""
    def __init__(self, 初始值=1):
        self.信号量 = _threading.Semaphore(初始值)


def 创建信号量(初始值=1):
    """创建信号量，返回信号量对象"""
    try:
        return 信号量对象(初始值)
    except Exception as e:
        raise Exception("创建信号量失败: " + str(e))


def 信号量阻塞(信号量):
    """阻塞直到信号量可用"""
    if not 信号量 or not 信号量.信号量:
        raise Exception("信号量阻塞失败: 信号量为空")
    try:
        信号量.信号量.acquire()
        return True
    except Exception as e:
        raise Exception("信号量阻塞失败: " + str(e))


def 信号量发布(信号量):
    """发布信号量，增加一个可用计数"""
    if not 信号量 or not 信号量.信号量:
        raise Exception("信号量发布失败: 信号量为空")
    try:
        信号量.信号量.release()
        return True
    except Exception as e:
        raise Exception("信号量发布失败: " + str(e))


def 信号量销毁(信号量):
    """销毁信号量"""
    if not 信号量:
        return
    信号量.信号量 = None


# =============================================================================
# 条件变量
# =============================================================================

class 条件变量对象:
    """条件变量对象"""
    def __init__(self):
        self.条件变量 = _threading.Condition()


def 创建条件变量():
    """创建条件变量，返回条件变量对象"""
    try:
        return 条件变量对象()
    except Exception as e:
        raise Exception("创建条件变量失败: " + str(e))


def 条件变量阻塞(条件变量):
    """阻塞等待条件变量通知"""
    if not 条件变量 or not 条件变量.条件变量:
        raise Exception("条件变量阻塞失败: 条件变量为空")
    try:
        条件变量.条件变量.acquire()
        条件变量.条件变量.wait()
        条件变量.条件变量.release()
        return True
    except Exception as e:
        raise Exception("条件变量阻塞失败: " + str(e))


def 条件变量通知(条件变量):
    """通知一个等待的条件变量"""
    if not 条件变量 or not 条件变量.条件变量:
        raise Exception("条件变量通知失败: 条件变量为空")
    try:
        条件变量.条件变量.acquire()
        条件变量.条件变量.notify()
        条件变量.条件变量.release()
        return True
    except Exception as e:
        raise Exception("条件变量通知失败: " + str(e))


def 条件变量通知全部(条件变量):
    """通知所有等待的条件变量"""
    if not 条件变量 or not 条件变量.条件变量:
        raise Exception("条件变量通知全部失败: 条件变量为空")
    try:
        条件变量.条件变量.acquire()
        条件变量.条件变量.notify_all()
        条件变量.条件变量.release()
        return True
    except Exception as e:
        raise Exception("条件变量通知全部失败: " + str(e))


def 条件变量销毁(条件变量):
    """销毁条件变量"""
    if not 条件变量:
        return
    条件变量.条件变量 = None


# =============================================================================
# 原子操作（基于 threading 模拟）
# =============================================================================

class _原子值:
    """原子值包装"""
    def __init__(self, 初始值=0):
        self.锁 = _threading.Lock()
        self.值 = 初始值


_原子存储 = {}


def 原子加法(指针, 增量):
    """原子加法，返回新值"""
    if 指针 not in _原子存储:
        _原子存储[指针] = _原子值(0)
    a = _原子存储[指针]
    with a.锁:
        a.值 += 增量
        return a.值


def 原子减法(指针, 减量):
    """原子减法，返回新值"""
    return 原子加法(指针, -减量)


def 原子存储(指针, 值):
    """原子存储值"""
    if 指针 not in _原子存储:
        _原子存储[指针] = _原子值(0)
    a = _原子存储[指针]
    with a.锁:
        a.值 = 值


def 原子加载(指针):
    """原子加载值"""
    if 指针 not in _原子存储:
        return 0
    a = _原子存储[指针]
    with a.锁:
        return a.值


def 原子比较交换(指针, 预期值, 新值):
    """原子比较交换，成功返回True，失败返回False"""
    if 指针 not in _原子存储:
        _原子存储[指针] = _原子值(预期值)
    a = _原子存储[指针]
    with a.锁:
        if a.值 == 预期值:
            a.值 = 新值
            return True
        return False


# =============================================================================
# 线程池
# =============================================================================

class 线程池对象:
    """线程池对象"""
    def __init__(self, 最大线程数):
        from concurrent.futures import ThreadPoolExecutor as _Executor
        self.池 = _Executor(max_workers=最大线程数)
        self.最大线程数 = 最大线程数


def 线程池工作线程(线程池):
    """获取线程池的工作线程数"""
    if not 线程池:
        raise Exception("线程池工作线程失败: 线程池为空")
    return 线程池.最大线程数


def 创建线程池(最大线程数):
    """创建线程池，返回线程池对象"""
    try:
        return 线程池对象(最大线程数)
    except Exception as e:
        raise Exception("创建线程池失败: " + str(e))


def 线程池提交任务(线程池, 任务函数, *参数):
    """提交任务到线程池，返回Future对象"""
    if not 线程池 or not 线程池.池:
        raise Exception("线程池提交任务失败: 线程池为空")
    try:
        return 线程池.池.submit(任务函数, *参数)
    except Exception as e:
        raise Exception("线程池提交任务失败: " + str(e))


def 线程池等待全部(线程池):
    """等待线程池中所有任务完成"""
    if not 线程池 or not 线程池.池:
        raise Exception("线程池等待全部失败: 线程池为空")
    try:
        线程池.池.shutdown(wait=True)
        # 重新创建线程池
        线程池.池 = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor(max_workers=线程池.最大线程数)
    except Exception as e:
        raise Exception("线程池等待全部失败: " + str(e))


def 线程池关停(线程池):
    """关停线程池"""
    if not 线程池 or not 线程池.池:
        return
    try:
        线程池.池.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass