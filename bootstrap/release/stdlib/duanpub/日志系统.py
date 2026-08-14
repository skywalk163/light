"""
日志系统 — duanpub 桥接模块

基于 Python logging 库封装，函数名对齐 duanpub/packages/日志系统/源.duan。

duanpub 原始包通过 C FFI 调用系统日志接口，
本桥接模块用 Python logging 模块替代，提供等价的日志功能。
"""

import logging as _logging
import threading as _threading


# =============================================================================
# 日志级别常量
# =============================================================================

DEBUG = _logging.DEBUG
INFO = _logging.INFO
WARNING = _logging.WARNING
ERROR = _logging.ERROR
CRITICAL = _logging.CRITICAL


# =============================================================================
# 内部存储
# =============================================================================

_loggers = {}


# =============================================================================
# 日志器管理
# =============================================================================

def 创建日志器(名称, 级别=None, 格式=None, 输出文件=None):
    """创建或获取指定名称的日志器"""
    if not 名称:
        raise Exception("创建日志器失败: 名称为空")
    try:
        logger = _logging.getLogger(名称)
        logger.setLevel(级别 if 级别 is not None else _logging.DEBUG)

        # 清空已有处理器
        logger.handlers.clear()

        # 创建格式化器
        fmt = _logging.Formatter(格式 or '%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        if 输出文件:
            handler = _logging.FileHandler(输出文件, encoding='utf-8')
        else:
            handler = _logging.StreamHandler()

        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.propagate = False

        _loggers[名称] = logger
        return logger
    except Exception as e:
        raise Exception("创建日志器失败: " + str(e))


def 日志器记录(logger, 级别, 消息, *参数):
    """日志器记录指定级别的日志"""
    if not logger:
        raise Exception("日志器记录失败: 无效的日志器")
    try:
        if 参数:
            logger.log(级别, 消息, *参数)
        else:
            logger.log(级别, 消息)
    except Exception as e:
        raise Exception("日志器记录失败: " + str(e))


def 日志器调试(logger, 消息, *参数):
    """日志器记录 DEBUG 级别日志"""
    if not logger:
        raise Exception("日志器调试失败: 无效的日志器")
    try:
        if 参数:
            logger.debug(消息, *参数)
        else:
            logger.debug(消息)
    except Exception as e:
        raise Exception("日志器调试失败: " + str(e))


def 日志器信息(logger, 消息, *参数):
    """日志器记录 INFO 级别日志"""
    if not logger:
        raise Exception("日志器信息失败: 无效的日志器")
    try:
        if 参数:
            logger.info(消息, *参数)
        else:
            logger.info(消息)
    except Exception as e:
        raise Exception("日志器信息失败: " + str(e))


def 日志器警告(logger, 消息, *参数):
    """日志器记录 WARNING 级别日志"""
    if not logger:
        raise Exception("日志器警告失败: 无效的日志器")
    try:
        if 参数:
            logger.warning(消息, *参数)
        else:
            logger.warning(消息)
    except Exception as e:
        raise Exception("日志器警告失败: " + str(e))


def 日志器错误(logger, 消息, *参数):
    """日志器记录 ERROR 级别日志"""
    if not logger:
        raise Exception("日志器错误失败: 无效的日志器")
    try:
        if 参数:
            logger.error(消息, *参数)
        else:
            logger.error(消息)
    except Exception as e:
        raise Exception("日志器错误失败: " + str(e))


def 日志器设置级别(logger, 级别):
    """设置日志器级别"""
    if not logger:
        raise Exception("日志器设置级别失败: 无效的日志器")
    try:
        logger.setLevel(级别)
    except Exception as e:
        raise Exception("日志器设置级别失败: " + str(e))


def 日志器关闭(logger):
    """关闭日志器并释放资源"""
    if not logger:
        return
    try:
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
    except Exception:
        pass