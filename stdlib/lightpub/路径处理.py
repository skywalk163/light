"""
路径处理 — lightpub 桥接模块

基于 Python os.path / pathlib / glob 库封装，函数名对齐上游 duanpub（段言时期）packages/路径处理/源.duan。

上游 duanpub 原始包通过 C FFI 直接调用操作系统路径处理 API，
本桥接模块用 Python os.path/pathlib/glob 模块替代，提供等价的路径操作功能。
"""

import os as _os
import os.path as _path
from pathlib import Path as _Path
import glob as _glob


# =============================================================================
# 路径解析与转换
# =============================================================================

def 绝对路径(路径):
    """返回路径的绝对路径"""
    if not 路径:
        raise Exception("绝对路径失败: 路径为空")
    try:
        return _path.abspath(路径)
    except Exception as e:
        raise Exception("绝对路径失败: " + str(e))


def 相对路径(路径, 起始=None):
    """返回相对于起始路径的相对路径"""
    if not 路径:
        raise Exception("相对路径失败: 路径为空")
    try:
        if 起始:
            return _path.relpath(路径, 起始)
        return _path.relpath(路径)
    except Exception as e:
        raise Exception("相对路径失败: " + str(e))


def 拼接路径(路径片段1, 路径片段2):
    """拼接两个路径"""
    if not 路径片段1:
        raise Exception("拼接路径失败: 路径片段1为空")
    try:
        return _path.join(路径片段1, 路径片段2) if 路径片段2 else 路径片段1
    except Exception as e:
        raise Exception("拼接路径失败: " + str(e))


def 拼接路径2(*路径片段):
    """拼接多个路径片段"""
    if not 路径片段:
        raise Exception("拼接路径2失败: 路径片段为空")
    try:
        return _path.join(*路径片段)
    except Exception as e:
        raise Exception("拼接路径2失败: " + str(e))


def 获取文件名(路径):
    """获取路径中的文件名部分"""
    if not 路径:
        raise Exception("获取文件名失败: 路径为空")
    return _path.basename(路径)


def 获取目录名(路径):
    """获取路径中的目录名部分"""
    if not 路径:
        raise Exception("获取目录名失败: 路径为空")
    return _path.dirname(路径)


def 获取扩展名(路径):
    """获取路径中的文件扩展名（含点号）"""
    if not 路径:
        raise Exception("获取扩展名失败: 路径为空")
    return _path.splitext(路径)[1]


def 获取基础名(路径):
    """获取路径中的文件名（不含扩展名）"""
    if not 路径:
        raise Exception("获取基础名失败: 路径为空")
    basename = _path.basename(路径)
    return _path.splitext(basename)[0]


def 获取父目录(路径):
    """获取路径的父目录路径"""
    if not 路径:
        raise Exception("获取父目录失败: 路径为空")
    return _path.dirname(路径)


def 分割路径(路径):
    """将路径分割为(目录, 文件名)"""
    if not 路径:
        raise Exception("分割路径失败: 路径为空")
    return _path.split(路径)


def 分割扩展名(路径):
    """将路径分割为(主路径, 扩展名)"""
    if not 路径:
        raise Exception("分割扩展名失败: 路径为空")
    return _path.splitext(路径)


def 分割全部(路径):
    """将路径分割为所有组成部分的列表"""
    if not 路径:
        raise Exception("分割全部失败: 路径为空")
    parts = []
    while True:
        路径, part = _path.split(路径)
        if part:
            parts.append(part)
        else:
            if 路径:
                parts.append(路径)
            break
    parts.reverse()
    return parts


def 规范化路径(路径):
    """规范化路径格式"""
    if not 路径:
        raise Exception("规范化路径失败: 路径为空")
    try:
        return _path.normpath(路径)
    except Exception as e:
        raise Exception("规范化路径失败: " + str(e))


def 获取相对路径(目标路径, 起始路径):
    """获取从起始路径到目标路径的相对路径"""
    if not 目标路径 or not 起始路径:
        raise Exception("获取相对路径失败: 路径为空")
    try:
        return _path.relpath(目标路径, 起始路径)
    except Exception as e:
        raise Exception("获取相对路径失败: " + str(e))


def globMatch(模式, 路径):
    """检查路径是否匹配glob模式"""
    if not 模式:
        return False
    try:
        return _glob.fnmatch.fnmatch(路径, 模式)
    except Exception:
        return False


def 路径是否相等(路径1, 路径2):
    """比较两个路径是否相等（规范化后比较）"""
    if not 路径1 or not 路径2:
        return False
    try:
        return _path.normpath(路径1) == _path.normpath(路径2)
    except Exception:
        return False


def 更改扩展名(路径, 新扩展名):
    """更改文件扩展名"""
    if not 路径:
        raise Exception("更改扩展名失败: 路径为空")
    if not 新扩展名.startswith('.'):
        新扩展名 = '.' + 新扩展名
    base, _ = _path.splitext(路径)
    return base + 新扩展名


def 主目录():
    """获取当前用户的主目录路径"""
    try:
        return str(_Path.home())
    except Exception as e:
        raise Exception("主目录失败: " + str(e))


def 当前目录():
    """获取当前工作目录路径"""
    try:
        return _os.getcwd()
    except Exception as e:
        raise Exception("当前目录失败: " + str(e))


def 临时目录():
    """获取系统临时目录路径"""
    import tempfile as _tempfile
    try:
        return _tempfile.gettempdir()
    except Exception as e:
        raise Exception("临时目录失败: " + str(e))