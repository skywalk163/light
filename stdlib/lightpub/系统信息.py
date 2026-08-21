"""
系统信息 — lightpub 桥接模块

基于 Python platform / os / time 库封装，函数名对齐上游 duanpub（段言时期）packages/系统信息/源.duan。

上游 duanpub 原始包通过 C FFI 直接调用系统 API 获取系统信息，
本桥接模块用 Python platform/os 模块替代，提供等价的系统信息获取功能。
"""

import platform as _platform
import os as _os
import time as _time


# =============================================================================
# CPU 信息
# =============================================================================

def 获取CPU信息():
    """获取CPU信息字典"""
    try:
        return {
            '型号': _platform.processor(),
            '核心数': _os.cpu_count() or 0,
            '架构': _platform.machine(),
        }
    except Exception as e:
        raise Exception("获取CPU信息失败: " + str(e))


def 获取CPU核心数():
    """获取CPU核心数"""
    try:
        return _os.cpu_count() or 0
    except Exception:
        return 0


def 获取CPU使用率():
    """获取CPU使用率百分比（简化实现，依赖psutil）"""
    try:
        import psutil as _psutil
        return _psutil.cpu_percent(interval=0.1)
    except ImportError:
        return 0.0
    except Exception:
        return 0.0


def 获取CPU每核使用率():
    """获取每核CPU使用率列表（简化实现，依赖psutil）"""
    try:
        import psutil as _psutil
        return _psutil.cpu_percent(interval=0.1, percpu=True)
    except ImportError:
        return [0.0] * (_os.cpu_count() or 1)
    except Exception:
        return [0.0]


# =============================================================================
# 内存信息
# =============================================================================

def 获取内存信息():
    """获取内存信息字典（依赖psutil）"""
    try:
        import psutil as _psutil
        mem = _psutil.virtual_memory()
        return {
            '总量': mem.total,
            '可用': mem.available,
            '已用': mem.used,
            '使用率': mem.percent,
        }
    except ImportError:
        return {'总量': 0, '可用': 0, '已用': 0, '使用率': 0.0}
    except Exception as e:
        raise Exception("获取内存信息失败: " + str(e))


def 获取内存总量():
    """获取内存总量（字节）"""
    try:
        import psutil as _psutil
        return _psutil.virtual_memory().total
    except ImportError:
        return 0
    except Exception:
        return 0


def 获取内存可用():
    """获取可用内存（字节）"""
    try:
        import psutil as _psutil
        return _psutil.virtual_memory().available
    except ImportError:
        return 0
    except Exception:
        return 0


def 获取内存使用率():
    """获取内存使用率百分比"""
    try:
        import psutil as _psutil
        return _psutil.virtual_memory().percent
    except ImportError:
        return 0.0
    except Exception:
        return 0.0


# =============================================================================
# 磁盘信息
# =============================================================================

def 获取磁盘信息(路径):
    """获取指定路径的磁盘信息"""
    if not 路径:
        raise Exception("获取磁盘信息失败: 路径为空")
    try:
        import psutil as _psutil
        usage = _psutil.disk_usage(路径)
        return {
            '总量': usage.total,
            '已用': usage.used,
            '可用': usage.free,
            '使用率': usage.percent,
        }
    except ImportError:
        return {'总量': 0, '已用': 0, '可用': 0, '使用率': 0.0}
    except Exception as e:
        raise Exception("获取磁盘信息失败: " + str(e))


def 获取磁盘全部():
    """获取所有磁盘分区信息汇总"""
    try:
        import psutil as _psutil
        total = 0
        used = 0
        free = 0
        for part in _psutil.disk_partitions():
            try:
                usage = _psutil.disk_usage(part.mountpoint)
                total += usage.total
                used += usage.used
                free += usage.free
            except Exception:
                continue
        return {'总量': total, '已用': used, '可用': free}
    except ImportError:
        return {'总量': 0, '已用': 0, '可用': 0}
    except Exception as e:
        raise Exception("获取磁盘全部失败: " + str(e))


def 获取所有磁盘信息():
    """获取所有磁盘分区的信息列表"""
    try:
        import psutil as _psutil
        result = []
        for part in _psutil.disk_partitions():
            try:
                usage = _psutil.disk_usage(part.mountpoint)
                result.append({
                    '设备': part.device,
                    '挂载点': part.mountpoint,
                    '文件系统': part.fstype,
                    '总量': usage.total,
                    '已用': usage.used,
                    '可用': usage.free,
                    '使用率': usage.percent,
                })
            except Exception:
                continue
        return result
    except ImportError:
        return []
    except Exception as e:
        raise Exception("获取所有磁盘信息失败: " + str(e))


# =============================================================================
# 网络接口信息
# =============================================================================

def 获取网口全部():
    """获取所有网口名称列表"""
    try:
        import psutil as _psutil
        stats = _psutil.net_io_counters(pernic=True)
        return list(stats.keys())
    except ImportError:
        return []
    except Exception:
        return []


def 获取网络接口信息(接口名):
    """获取指定网络接口的详细信息"""
    if not 接口名:
        raise Exception("获取网络接口信息失败: 接口名为空")
    try:
        import psutil as _psutil
        import socket as _socket
        addrs = _psutil.net_if_addrs().get(接口名, [])
        stats = _psutil.net_if_stats().get(接口名)
        io = _psutil.net_io_counters(pernic=True).get(接口名)
        addr_list = []
        for addr in addrs:
            addr_list.append({
                '地址': addr.address,
                '掩码': addr.netmask,
                '广播': addr.broadcast,
                '类型': str(addr.family),
            })
        return {
            '地址列表': addr_list,
            '是否启动': stats.isup if stats else False,
            '速度': stats.speed if stats else 0,
            '发送字节': io.bytes_sent if io else 0,
            '接收字节': io.bytes_recv if io else 0,
        }
    except ImportError:
        return {'地址列表': [], '是否启动': False, '速度': 0, '发送字节': 0, '接收字节': 0}
    except Exception as e:
        raise Exception("获取网络接口信息失败: " + str(e))


def 获取所有网络接口信息():
    """获取所有网络接口的信息字典"""
    try:
        import psutil as _psutil
        result = {}
        for name in 获取网口全部():
            try:
                result[name] = 获取网络接口信息(name)
            except Exception:
                continue
        return result
    except Exception as e:
        raise Exception("获取所有网络接口信息失败: " + str(e))


# =============================================================================
# 系统概要
# =============================================================================

def 获取系统概览():
    """获取系统概要信息"""
    try:
        import psutil as _psutil
        boot_time = _psutil.boot_time()
        return {
            '主机名': _platform.node(),
            '操作系统': _platform.system(),
            '版本': _platform.version(),
            '架构': _platform.machine(),
            'CPU核心数': _os.cpu_count() or 0,
            'CPU型号': _platform.processor(),
            '内存总量': 获取内存总量(),
            '启动时间': boot_time,
            '运行时间': _time.time() - boot_time,
            '当前用户': 获取当前用户(),
        }
    except ImportError:
        return {
            '主机名': _platform.node(),
            '操作系统': _platform.system(),
            '版本': _platform.version(),
            '架构': _platform.machine(),
            'CPU核心数': _os.cpu_count() or 0,
            'CPU型号': _platform.processor(),
            '内存总量': 0,
            '启动时间': 0,
            '运行时间': 0,
            '当前用户': 获取当前用户(),
        }
    except Exception as e:
        raise Exception("获取系统概览失败: " + str(e))


def 获取主机名():
    """获取系统主机名"""
    try:
        return _platform.node()
    except Exception as e:
        raise Exception("获取主机名失败: " + str(e))


def 获取操作系统名称():
    """获取操作系统名称"""
    try:
        return _platform.system()
    except Exception as e:
        raise Exception("获取操作系统名称失败: " + str(e))


def 获取操作系统版本():
    """获取操作系统版本字符串"""
    try:
        return _platform.version()
    except Exception as e:
        raise Exception("获取操作系统版本失败: " + str(e))


def 获取系统架构():
    """获取系统架构类型"""
    try:
        return _platform.machine()
    except Exception as e:
        raise Exception("获取系统架构失败: " + str(e))


def 获取当前用户():
    """获取当前用户名"""
    try:
        import getpass as _getpass
        return _getpass.getuser()
    except Exception:
        try:
            return _os.environ.get('USERNAME', _os.environ.get('USER', 'unknown'))
        except Exception:
            return 'unknown'


def 获取启动时间():
    """获取系统启动时间戳（依赖psutil）"""
    try:
        import psutil as _psutil
        return _psutil.boot_time()
    except ImportError:
        return 0.0
    except Exception:
        return 0.0


def 获取运行时间():
    """获取系统已运行时间（秒）"""
    try:
        boot = 获取启动时间()
        if boot > 0:
            return _time.time() - boot
        return 0.0
    except Exception:
        return 0.0


# =============================================================================
# 格式化工具
# =============================================================================

def 格式化字节(字节数):
    """将字节数格式化为人类可读的字符串"""
    if 字节数 < 0:
        return '0 B'
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    size = float(字节数)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f'{size:.2f} {units[unit_index]}'


def 格式化运行时间(秒数):
    """将运行时间秒数格式化为人类可读的字符串"""
    if 秒数 < 0:
        秒数 = 0
    days = int(秒数 // 86400)
    hours = int((秒数 % 86400) // 3600)
    minutes = int((秒数 % 3600) // 60)
    seconds = int(秒数 % 60)

    parts = []
    if days > 0:
        parts.append(f'{days}天')
    if hours > 0:
        parts.append(f'{hours}小时')
    if minutes > 0:
        parts.append(f'{minutes}分')
    parts.append(f'{seconds}秒')
    return ''.join(parts)