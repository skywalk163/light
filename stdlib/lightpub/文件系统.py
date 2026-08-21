"""
文件系统 — lightpub 桥接模块

基于 Python os / shutil / pathlib 库封装，函数名对齐上游 duanpub（段言时期）packages/文件系统/源.duan。

上游 duanpub 原始包通过 C FFI 直接调用操作系统文件 API，
本桥接模块用 Python os/shutil/pathlib 模块替代，提供等价的文件系统操作功能。
"""

import os as _os
import shutil as _shutil
import tempfile as _tempfile
from pathlib import Path as _Path


# =============================================================================
# 数据结构
# =============================================================================

class 文件信息:
    """文件信息对象"""
    def __init__(self, 路径='', 大小=0, 是否目录=False, 是否文件=False,
                 修改时间=0, 创建时间=0, 访问时间=0):
        self.路径 = 路径
        self.大小 = 大小
        self.是否目录 = 是否目录
        self.是否文件 = 是否文件
        self.修改时间 = 修改时间
        self.创建时间 = 创建时间
        self.访问时间 = 访问时间


# =============================================================================
# 文件读写
# =============================================================================

def 读取文件(文件路径, 编码='utf-8'):
    """读取文件全部内容，返回字符串"""
    if not 文件路径:
        raise Exception("读取文件失败: 文件路径为空")
    try:
        with open(文件路径, 'r', encoding=编码) as f:
            return f.read()
    except FileNotFoundError:
        raise Exception("读取文件失败: 文件不存在 " + 文件路径)
    except (IOError, UnicodeDecodeError) as e:
        raise Exception("读取文件失败: " + str(e))


def 写入文件(文件路径, 内容, 编码='utf-8'):
    """写入文件（覆盖），返回 True/False"""
    if not 文件路径:
        raise Exception("写入文件失败: 文件路径为空")
    try:
        with open(文件路径, 'w', encoding=编码) as f:
            f.write(内容)
        return True
    except (IOError, OSError) as e:
        raise Exception("写入文件失败: " + str(e))


def 追加写入(文件路径, 内容, 编码='utf-8'):
    """追加写入文件，返回 True/False"""
    if not 文件路径:
        raise Exception("追加写入失败: 文件路径为空")
    try:
        with open(文件路径, 'a', encoding=编码) as f:
            f.write(内容)
        return True
    except (IOError, OSError) as e:
        raise Exception("追加写入失败: " + str(e))


def 按行读取(文件路径, 编码='utf-8'):
    """按行读取文件，返回字符串列表"""
    if not 文件路径:
        raise Exception("按行读取失败: 文件路径为空")
    try:
        with open(文件路径, 'r', encoding=编码) as f:
            return [line.rstrip('\n\r') for line in f]
    except FileNotFoundError:
        raise Exception("按行读取失败: 文件不存在 " + 文件路径)
    except (IOError, UnicodeDecodeError) as e:
        raise Exception("按行读取失败: " + str(e))


def 按字节读取(文件路径, 最大长度=-1):
    """按字节读取文件，返回 bytes"""
    if not 文件路径:
        raise Exception("按字节读取失败: 文件路径为空")
    try:
        with open(文件路径, 'rb') as f:
            return f.read(最大长度)
    except FileNotFoundError:
        raise Exception("按字节读取失败: 文件不存在 " + 文件路径)
    except IOError as e:
        raise Exception("按字节读取失败: " + str(e))


# =============================================================================
# 文件信息与存在性
# =============================================================================

def 文件是否存在(路径):
    """检查文件/目录是否存在"""
    return _os.path.exists(路径)


def 文件大小(文件路径):
    """获取文件大小（字节）"""
    if not _os.path.exists(文件路径):
        raise Exception("文件大小失败: 文件不存在 " + 文件路径)
    return _os.path.getsize(文件路径)


def 获取修改时间(文件路径):
    """获取文件最后修改时间（时间戳）"""
    if not _os.path.exists(文件路径):
        raise Exception("获取修改时间失败: 文件不存在 " + 文件路径)
    return _os.path.getmtime(文件路径)


def 获取文件信息(文件路径):
    """获取文件信息，返回 文件信息 对象"""
    if not _os.path.exists(文件路径):
        raise Exception("获取文件信息失败: 路径不存在 " + 文件路径)
    stat = _os.stat(文件路径)
    return 文件信息(
        路径=文件路径,
        大小=stat.st_size,
        是否目录=_os.path.isdir(文件路径),
        是否文件=_os.path.isfile(文件路径),
        修改时间=stat.st_mtime,
        创建时间=getattr(stat, 'st_ctime', 0),
        访问时间=stat.st_atime,
    )


# =============================================================================
# 文件操作
# =============================================================================

def 删除文件(文件路径):
    """删除文件"""
    if not 文件路径:
        raise Exception("删除文件失败: 文件路径为空")
    try:
        _os.remove(文件路径)
        return True
    except FileNotFoundError:
        raise Exception("删除文件失败: 文件不存在 " + 文件路径)
    except OSError as e:
        raise Exception("删除文件失败: " + str(e))


def 重命名文件(旧路径, 新路径):
    """重命名/移动文件"""
    if not 旧路径 or not 新路径:
        raise Exception("重命名文件失败: 路径为空")
    try:
        _os.rename(旧路径, 新路径)
        return True
    except OSError as e:
        raise Exception("重命名文件失败: " + str(e))


def 复制文件(源路径, 目标路径):
    """复制文件"""
    if not 源路径 or not 目标路径:
        raise Exception("复制文件失败: 路径为空")
    try:
        _shutil.copy2(源路径, 目标路径)
        return True
    except FileNotFoundError:
        raise Exception("复制文件失败: 源文件不存在 " + 源路径)
    except (IOError, OSError) as e:
        raise Exception("复制文件失败: " + str(e))


# =============================================================================
# 目录操作
# =============================================================================

def 列出目录(目录路径):
    """列出目录下的文件和子目录名，返回列表"""
    if not 目录路径:
        raise Exception("列出目录失败: 目录路径为空")
    if not _os.path.isdir(目录路径):
        raise Exception("列出目录失败: 不是目录 " + 目录路径)
    try:
        return _os.listdir(目录路径)
    except OSError as e:
        raise Exception("列出目录失败: " + str(e))


def 递归遍历(目录路径):
    """递归遍历目录，返回所有文件的完整路径列表"""
    if not 目录路径:
        raise Exception("递归遍历失败: 目录路径为空")
    if not _os.path.isdir(目录路径):
        raise Exception("递归遍历失败: 不是目录 " + 目录路径)
    结果 = []
    for 根目录, 子目录, 文件列表 in _os.walk(目录路径):
        for 文件名 in 文件列表:
            结果.append(_os.path.join(根目录, 文件名))
    return 结果


def 创建目录(目录路径):
    """创建目录（含父目录）"""
    if not 目录路径:
        raise Exception("创建目录失败: 目录路径为空")
    try:
        _os.makedirs(目录路径, exist_ok=True)
        return True
    except OSError as e:
        raise Exception("创建目录失败: " + str(e))


def 删除目录(目录路径):
    """删除目录及其所有内容"""
    if not 目录路径:
        raise Exception("删除目录失败: 目录路径为空")
    if not _os.path.isdir(目录路径):
        raise Exception("删除目录失败: 不是目录 " + 目录路径)
    try:
        _shutil.rmtree(目录路径)
        return True
    except OSError as e:
        raise Exception("删除目录失败: " + str(e))


# =============================================================================
# 权限检查
# =============================================================================

def 检查可读(文件路径):
    """检查文件是否可读"""
    return _os.access(文件路径, _os.R_OK)


def 检查可写(文件路径):
    """检查文件是否可写"""
    return _os.access(文件路径, _os.W_OK)


def 检查可执行(文件路径):
    """检查文件是否可执行"""
    return _os.access(文件路径, _os.X_OK)


def 获取权限(文件路径):
    """获取文件权限码"""
    if not _os.path.exists(文件路径):
        raise Exception("获取权限失败: 文件不存在 " + 文件路径)
    return _os.stat(文件路径).st_mode


def 设置权限(文件路径, 权限码):
    """设置文件权限"""
    if not _os.path.exists(文件路径):
        raise Exception("设置权限失败: 文件不存在 " + 文件路径)
    try:
        _os.chmod(文件路径, 权限码)
        return True
    except OSError as e:
        raise Exception("设置权限失败: " + str(e))


# =============================================================================
# 临时文件
# =============================================================================

def 创建临时文件(后缀='', 前缀='duan_'):
    """创建临时文件，返回文件路径"""
    try:
        fd, 路径 = _tempfile.mkstemp(suffix=后缀, prefix=前缀)
        _os.close(fd)
        return 路径
    except OSError as e:
        raise Exception("创建临时文件失败: " + str(e))


def 创建临时目录(前缀='duan_'):
    """创建临时目录，返回目录路径"""
    try:
        return _tempfile.mkdtemp(prefix=前缀)
    except OSError as e:
        raise Exception("创建临时目录失败: " + str(e))


# =============================================================================
# 文件变更监控（简化）
# =============================================================================

def 检查文件变更(文件路径, 上次修改时间):
    """检查文件是否在上次修改时间之后被修改"""
    if not _os.path.exists(文件路径):
        return False
    return _os.path.getmtime(文件路径) > 上次修改时间


def 等待文件变更(文件路径, 超时秒=60, 轮询间隔=1):
    """等待文件变更，返回 True/False（超时返回 False）"""
    import time as _time
    if not _os.path.exists(文件路径):
        return False
    上次时间 = _os.path.getmtime(文件路径)
    已等待 = 0
    while 已等待 < 超时秒:
        _time.sleep(轮询间隔)
        已等待 += 轮询间隔
        if _os.path.getmtime(文件路径) > 上次时间:
            return True
    return False
