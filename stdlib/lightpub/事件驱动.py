"""
事件驱动 — duanpub 桥接模块

基于 Python asyncio 库封装，函数名对齐 duanpub/packages/事件驱动/源.duan。

duanpub 原始包通过 C FFI 实现事件驱动编程模型，
本桥接模块用 Python asyncio 模块替代，提供等价的 EventEmitter 功能。
"""

import asyncio as _asyncio


# =============================================================================
# 事件循环管理
# =============================================================================

_事件循环 = None


def 创建事件循环():
    """创建新的事件循环，返回事件循环对象"""
    global _事件循环
    try:
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        _事件循环 = loop
        return loop
    except Exception as e:
        raise Exception("创建事件循环失败: " + str(e))


def 事件循环添加事件(loop, event_name, callback):
    """向事件循环添加事件监听器"""
    if not loop:
        raise Exception("事件循环添加事件失败: 事件循环为空")
    if not event_name:
        raise Exception("事件循环添加事件失败: 事件名称为空")
    try:
        if not hasattr(loop, '_events'):
            loop._events = {}
        if event_name not in loop._events:
            loop._events[event_name] = []
        loop._events[event_name].append(callback)
        return True
    except Exception as e:
        raise Exception("事件循环添加事件失败: " + str(e))


def 事件循环运行(loop):
    """运行事件循环"""
    if not loop:
        raise Exception("事件循环运行失败: 事件循环为空")
    try:
        loop.run_forever()
    except Exception as e:
        raise Exception("事件循环运行失败: " + str(e))


def 事件循环停止(loop):
    """停止事件循环"""
    if not loop:
        raise Exception("事件循环停止失败: 事件循环为空")
    try:
        loop.stop()
        return True
    except Exception as e:
        raise Exception("事件循环停止失败: " + str(e))


# =============================================================================
# 事件管理
# =============================================================================

def 创建事件(event_name, data=None):
    """创建事件对象"""
    if not event_name:
        raise Exception("创建事件失败: 事件名称为空")
    return {
        '名称': event_name,
        '数据': data,
        '已处理': False,
        '时间戳': _asyncio.get_event_loop().time() if _asyncio.get_event_loop().is_running() else 0,
    }


def 触发事件(loop, event_name, data=None):
    """触发事件，调用所有注册的监听器"""
    if not loop:
        raise Exception("触发事件失败: 事件循环为空")
    if not event_name:
        raise Exception("触发事件失败: 事件名称为空")
    try:
        event = 创建事件(event_name, data)
        events = getattr(loop, '_events', {})
        callbacks = events.get(event_name, [])
        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                pass
        event['已处理'] = True
        return True
    except Exception as e:
        raise Exception("触发事件失败: " + str(e))