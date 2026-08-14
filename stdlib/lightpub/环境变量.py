"""
环境变量 — duanpub 桥接模块

基于 Python os.environ / os.path 库封装，函数名对齐 duanpub/packages/环境变量/源.duan。

duanpub 原始包通过 C FFI 直接调用操作系统环境变量 API，
本桥接模块用 Python os 模块替代，提供等价的系统环境变量操作功能。
"""

import os as _os
import re as _re


# =============================================================================
# 核心环境变量操作
# =============================================================================

def 获取环境变量(键, 默认值=None):
    """获取环境变量值，不存在返回默认值"""
    try:
        return _os.environ.get(键, 默认值)
    except Exception as e:
        raise Exception("获取环境变量失败: " + str(e))


def 设置环境变量(键, 值):
    """设置环境变量"""
    if not 键:
        raise Exception("设置环境变量失败: 键为空")
    try:
        _os.environ[键] = 值
        return True
    except Exception as e:
        raise Exception("设置环境变量失败: " + str(e))


def 删除环境变量(键):
    """删除环境变量"""
    if not 键:
        raise Exception("删除环境变量失败: 键为空")
    try:
        if 键 in _os.environ:
            del _os.environ[键]
        return True
    except Exception as e:
        raise Exception("删除环境变量失败: " + str(e))


def 环境变量是否存在(键):
    """检查环境变量是否存在"""
    return 键 in _os.environ


def 列出全部环境变量():
    """列出所有环境变量的键值对列表，返回[(键, 值), ...]"""
    try:
        return list(_os.environ.items())
    except Exception as e:
        raise Exception("列出全部环境变量失败: " + str(e))


def 获取环境变量或抛出(键):
    """获取环境变量值，不存在则抛出异常"""
    if not 键:
        raise Exception("获取环境变量或抛出失败: 键为空")
    try:
        return _os.environ[键]
    except KeyError:
        raise Exception("环境变量不存在: " + 键)
    except Exception as e:
        raise Exception("获取环境变量失败: " + str(e))


def 展开环境变量(文本):
    """展开文本中的环境变量引用，如 $VAR 或 %VAR%"""
    if not 文本:
        return ''
    try:
        return _os.path.expandvars(文本)
    except Exception as e:
        raise Exception("展开环境变量失败: " + str(e))


# =============================================================================
# .env 文件解析
# =============================================================================

def 解析env文本(文本):
    """解析环境变量文本，返回{键: 值}字典"""
    if not 文本:
        return {}
    result = {}
    for line in 文本.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()
        # 去除引号
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def 解析env文件(文件路径):
    """从文件解析环境变量，返回{键: 值}字典"""
    if not 文件路径:
        raise Exception("解析env文件失败: 文件路径为空")
    try:
        with open(文件路径, 'r', encoding='utf-8') as f:
            return 解析env文本(f.read())
    except FileNotFoundError:
        raise Exception("解析env文件失败: 文件不存在 " + 文件路径)
    except Exception as e:
        raise Exception("解析env文件失败: " + str(e))


def 加载env文件(文件路径):
    """加载env文件到当前环境变量"""
    if not 文件路径:
        raise Exception("加载env文件失败: 文件路径为空")
    try:
        env_dict = 解析env文件(文件路径)
        for key, value in env_dict.items():
            _os.environ[key] = value
        return True
    except Exception as e:
        raise Exception("加载env文件失败: " + str(e))


# =============================================================================
# 类型转换获取
# =============================================================================

def 获取环境变量整数(键, 默认值=0):
    """获取环境变量值并转为整数"""
    val = 获取环境变量(键)
    if val is None:
        return 默认值
    try:
        return int(val)
    except ValueError:
        return 默认值


def 获取环境变量布尔(键, 默认值=False):
    """获取环境变量值并转为布尔"""
    val = 获取环境变量(键)
    if val is None:
        return 默认值
    return val.lower() in ('true', '1', 'yes', 'on')


def 获取环境变量列表(键, 分隔符=',', 默认值=None):
    """获取环境变量值并分割为列表"""
    if 默认值 is None:
        默认值 = []
    val = 获取环境变量(键)
    if val is None:
        return 默认值
    return [item.strip() for item in val.split(分隔符) if item.strip()]


def 环境变量到字符串():
    """将所有环境变量转为字符串"""
    try:
        return '\n'.join(f'{k}={v}' for k, v in _os.environ.items())
    except Exception as e:
        raise Exception("环境变量到字符串失败: " + str(e))


# =============================================================================
# 工具函数
# =============================================================================

def 范围(开始, 结束):
    """返回指定范围的整数列表"""
    return list(range(开始, 结束))