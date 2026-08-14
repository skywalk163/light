"""
错误处理 — duanpub 桥接模块

基于 Python 异常机制封装，函数名对齐 duanpub/packages/错误处理/源.duan。

duanpub 原始包通过 C FFI 实现错误链和 Result 类型，
本桥接模块用 Python 类模拟，提供等价的错误处理功能。
"""

import traceback as _traceback
import sys as _sys


# =============================================================================
# 数据结构
# =============================================================================

class _Result:
    """Result 类型：成功或失败"""
    def __init__(self, success, value=None, error=None):
        self._success = success
        self._value = value
        self._error = error

    def is_success(self):
        return self._success

    def is_failure(self):
        return not self._success

    def get_value(self):
        return self._value

    def get_error(self):
        return self._error


class _Error:
    """错误对象，支持错误链"""
    def __init__(self, message, cause=None):
        self.message = message
        self.cause = cause

    def __str__(self):
        if self.cause:
            return f"{self.message}: {self.cause}"
        return self.message


# =============================================================================
# Panic 钩子
# =============================================================================

_panic_hook = None


# =============================================================================
# 错误创建与包装
# =============================================================================

def 创建错误(消息):
    """创建一个错误对象"""
    return _Error(消息)


def 包装错误(错误, 上下文):
    """包装错误，添加上下文信息"""
    if isinstance(错误, _Error):
        return _Error(f"{上下文}: {错误.message}", 错误.cause)
    return _Error(f"{上下文}: {str(错误)}", 错误)


def 错误链_获取(错误):
    """获取错误链，返回错误消息列表"""
    result = []
    current = 错误
    while isinstance(current, _Error):
        result.append(current.message)
        current = current.cause
    return result


# =============================================================================
# Result 类型
# =============================================================================

def 结果成功(值):
    """创建一个成功的 Result"""
    return _Result(True, value=值)


def 结果失败(错误):
    """创建一个失败的 Result"""
    if isinstance(错误, str):
        错误 = _Error(错误)
    return _Result(False, error=错误)


def 是成功_检查(result):
    """检查 Result 是否成功"""
    if not isinstance(result, _Result):
        raise Exception("是成功_检查失败: 输入不是 Result 类型")
    return result.is_success()


def 是失败_检查(result):
    """检查 Result 是否失败"""
    if not isinstance(result, _Result):
        raise Exception("是失败_检查失败: 输入不是 Result 类型")
    return result.is_failure()


def 取值_获取(result):
    """获取 Result 的值，失败时抛出异常"""
    if not isinstance(result, _Result):
        raise Exception("取值_获取失败: 输入不是 Result 类型")
    if result.is_failure():
        raise Exception("取值_获取失败: Result 是失败状态: " + str(result.get_error()))
    return result.get_value()


def 或默认_获取(result, 默认值):
    """获取 Result 的值，失败时返回默认值"""
    if not isinstance(result, _Result):
        return 默认值
    if result.is_failure():
        return 默认值
    return result.get_value()


def 错误消息_获取(result):
    """获取 Result 的错误消息"""
    if not isinstance(result, _Result):
        raise Exception("错误消息_获取失败: 输入不是 Result 类型")
    if result.is_success():
        return ''
    error = result.get_error()
    if isinstance(error, _Error):
        return error.message
    return str(error)


def 然后_链式(result, 函数):
    """链式调用：如果 Result 成功则应用函数，否则返回原失败"""
    if not isinstance(result, _Result):
        raise Exception("然后_链式失败: 输入不是 Result 类型")
    if result.is_success():
        try:
            return 函数(result.get_value())
        except Exception as e:
            return 结果失败(str(e))
    return result


# =============================================================================
# Panic 相关
# =============================================================================

def 设置Panic钩子(钩子函数):
    """设置 Panic 钩子函数"""
    global _panic_hook
    _panic_hook = 钩子函数


def 触发Panic(消息):
    """触发 Panic，调用钩子函数"""
    global _panic_hook
    if _panic_hook:
        _panic_hook(消息)
    else:
        raise Exception("Panic: " + 消息)


def 恢复Panic钩子():
    """恢复 Panic 钩子为默认值"""
    global _panic_hook
    _panic_hook = None