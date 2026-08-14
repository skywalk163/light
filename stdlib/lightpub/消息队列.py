"""
消息队列 — duanpub 桥接模块

基于 Python queue 库封装，函数名对齐 duanpub/packages/消息队列/源.duan。

duanpub 原始包通过 C FFI 实现发布/订阅、消息代理、队列系统，
本桥接模块用 Python queue 模块替代，提供等价的消消息队列功能。
"""

import queue as _queue
import threading as _threading


# =============================================================================
# 消息队列
# =============================================================================

class _MessageQueue:
    """消息队列"""
    def __init__(self):
        self._queue = _queue.Queue()
        self._subscribers = {}
        self._lock = _threading.Lock()
        self._closed = False

    def publish(self, topic, message):
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            for cb in self._subscribers[topic]:
                try:
                    cb(topic, message)
                except Exception:
                    pass
            self._queue.put((topic, message))


def 创建消息队列():
    """创建消息队列"""
    try:
        return _MessageQueue()
    except Exception as e:
        raise Exception("创建消息队列失败: " + str(e))


def 消息队列发布(mq, topic, message):
    """发布消息到指定主题"""
    if not mq:
        raise Exception("消息队列发布失败: 消息队列为空")
    if not topic:
        raise Exception("消息队列发布失败: 主题为空")
    try:
        mq.publish(topic, message)
        return True
    except Exception as e:
        raise Exception("消息队列发布失败: " + str(e))


def 消息队列订阅(mq, topic, callback):
    """订阅指定主题的消息"""
    if not mq:
        raise Exception("消息队列订阅失败: 消息队列为空")
    if not topic:
        raise Exception("消息队列订阅失败: 主题为空")
    if not callable(callback):
        raise Exception("消息队列订阅失败: 回调不是可调用对象")
    try:
        with mq._lock:
            if topic not in mq._subscribers:
                mq._subscribers[topic] = []
            mq._subscribers[topic].append(callback)
        return True
    except Exception as e:
        raise Exception("消息队列订阅失败: " + str(e))


def 消息队列取消订阅(mq, topic, callback):
    """取消订阅指定主题"""
    if not mq:
        raise Exception("消息队列取消订阅失败: 消息队列为空")
    if not topic:
        raise Exception("消息队列取消订阅失败: 主题为空")
    try:
        with mq._lock:
            if topic in mq._subscribers and callback in mq._subscribers[topic]:
                mq._subscribers[topic].remove(callback)
                return True
        return False
    except Exception as e:
        raise Exception("消息队列取消订阅失败: " + str(e))


def 消息队列接收消息(mq, timeout=None):
    """接收消息，返回 (topic, message) 元组"""
    if not mq:
        raise Exception("消息队列接收消息失败: 消息队列为空")
    try:
        return mq._queue.get(timeout=timeout)
    except _queue.Empty:
        return None
    except Exception as e:
        raise Exception("消息队列接收消息失败: " + str(e))


def 消息队列确认消息(mq, topic, message):
    """确认消息处理完成"""
    if not mq:
        raise Exception("消息队列确认消息失败: 消息队列为空")
    try:
        mq._queue.task_done()
        return True
    except Exception as e:
        raise Exception("消息队列确认消息失败: " + str(e))


def 消息队列获取长度(mq):
    """获取消息队列长度"""
    if not mq:
        raise Exception("消息队列获取长度失败: 消息队列为空")
    try:
        return mq._queue.qsize()
    except Exception as e:
        raise Exception("消息队列获取长度失败: " + str(e))


def 消息队列清空(mq):
    """清空消息队列"""
    if not mq:
        raise Exception("消息队列清空失败: 消息队列为空")
    try:
        with mq._lock:
            while not mq._queue.empty():
                try:
                    mq._queue.get_nowait()
                    mq._queue.task_done()
                except _queue.Empty:
                    break
        return True
    except Exception as e:
        raise Exception("消息队列清空失败: " + str(e))


def 消息队列关闭(mq):
    """关闭消息队列"""
    if not mq:
        raise Exception("消息队列关闭失败: 消息队列为空")
    try:
        mq._closed = True
        return True
    except Exception as e:
        raise Exception("消息队列关闭失败: " + str(e))