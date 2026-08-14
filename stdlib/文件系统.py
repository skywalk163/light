"""
光明标准库 - 文件系统模块

提供文件 I/O 和路径操作函数
"""

import os
import shutil
import tempfile
import time
from typing import List, Optional, Union, Dict, Any


def 读取文件(path: str, encoding: str = 'utf-8') -> str:
    """读取文件内容"""
    with open(path, 'r', encoding=encoding) as f:
        return f.read()


def 写入文件(path: str, content: str, encoding: str = 'utf-8') -> None:
    """写入文件"""
    with open(path, 'w', encoding=encoding) as f:
        f.write(content)


def 追加文件(path: str, content: str, encoding: str = 'utf-8') -> None:
    """追加内容到文件"""
    with open(path, 'a', encoding=encoding) as f:
        f.write(content)


def 文件存在(path: str) -> bool:
    """检查文件是否存在"""
    return os.path.isfile(path)


def 删除文件(path: str) -> None:
    """删除文件"""
    os.remove(path)


def 复制文件(src: str, dst: str) -> None:
    """复制文件"""
    shutil.copy2(src, dst)


def 移动文件(src: str, dst: str) -> None:
    """移动文件"""
    shutil.move(src, dst)


def 创建目录(path: str) -> None:
    """创建目录（包括父目录）"""
    os.makedirs(path, exist_ok=True)


def 删除目录(path: str) -> None:
    """删除目录"""
    shutil.rmtree(path)


def 目录存在(path: str) -> bool:
    """检查目录是否存在"""
    return os.path.isdir(path)


def 获取文件名(path: str) -> str:
    """获取文件名（含扩展名）"""
    return os.path.basename(path)


def 获取扩展名(path: str) -> str:
    """获取文件扩展名"""
    _, ext = os.path.splitext(path)
    return ext


def 获取目录名(path: str) -> str:
    """获取目录路径"""
    return os.path.dirname(path)


def 文件大小(path: str) -> int:
    """获取文件大小（字节）"""
    return os.path.getsize(path)


def 文件列表(dir_path: str) -> List[str]:
    """列出目录中的文件名"""
    return os.listdir(dir_path)


def 路径连接(*parts: str) -> str:
    """连接路径组件"""
    return os.path.join(*parts)


def 绝对路径(path: str) -> str:
    """获取绝对路径"""
    return os.path.abspath(path)


def 规范化路径(path: str) -> str:
    """规范化路径（去除多余分隔符和引用）"""
    return os.path.normpath(path)


def 真实路径(path: str) -> str:
    """获取真实路径（解析符号链接）"""
    return os.path.realpath(path)


def 路径分割(path: str) -> tuple:
    """分割路径为(目录, 文件名)"""
    return os.path.split(path)


def 扩展名分割(path: str) -> tuple:
    """分割路径为(主名, 扩展名)"""
    return os.path.splitext(path)


def 获取文件名不含扩展名(path: str) -> str:
    """获取文件名（不含扩展名）"""
    name, _ = os.path.splitext(os.path.basename(path))
    return name


def 路径存在(path: str) -> bool:
    """检查路径是否存在（文件或目录）"""
    return os.path.exists(path)


def 是否符号链接(path: str) -> bool:
    """检查是否为符号链接"""
    return os.path.islink(path)


def 是否可执行(path: str) -> bool:
    """检查是否可执行"""
    return os.access(path, os.X_OK)


def 是否可读(path: str) -> bool:
    """检查是否可读"""
    return os.access(path, os.R_OK)


def 是否可写(path: str) -> bool:
    """检查是否可写"""
    return os.access(path, os.W_OK)


def 文件修改时间(path: str) -> float:
    """获取文件修改时间（时间戳）"""
    return os.path.getmtime(path)


def 文件访问时间(path: str) -> float:
    """获取文件访问时间（时间戳）"""
    return os.path.getatime(path)


def 文件创建时间(path: str) -> float:
    """获取文件创建时间（时间戳）"""
    return os.path.getctime(path)


def 文件修改时间字符串(path: str, 格式: str = '%Y-%m-%d %H:%M:%S') -> str:
    """获取文件修改时间（格式化字符串）"""
    return time.strftime(格式, time.localtime(os.path.getmtime(path)))


def 文件访问时间字符串(path: str, 格式: str = '%Y-%m-%d %H:%M:%S') -> str:
    """获取文件访问时间（格式化字符串）"""
    return time.strftime(格式, time.localtime(os.path.getatime(path)))


def 文件创建时间字符串(path: str, 格式: str = '%Y-%m-%d %H:%M:%S') -> str:
    """获取文件创建时间（格式化字符串）"""
    return time.strftime(格式, time.localtime(os.path.getctime(path)))


def 文件属性(path: str) -> Dict[str, Any]:
    """获取文件属性"""
    stat = os.stat(path)
    return {
        '大小': stat.st_size,
        '修改时间': stat.st_mtime,
        '访问时间': stat.st_atime,
        '创建时间': stat.st_ctime,
        '权限': oct(stat.st_mode)[-4:],
        'inode': stat.st_ino,
        '链接数': stat.st_nlink,
        '用户ID': stat.st_uid,
        '组ID': stat.st_gid,
    }


def 遍历目录(dir_path: str, 递归: bool = False) -> List[str]:
    """遍历目录，返回文件路径列表"""
    result = []
    if 递归:
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                result.append(os.path.join(root, file))
    else:
        for item in os.listdir(dir_path):
            full_path = os.path.join(dir_path, item)
            if os.path.isfile(full_path):
                result.append(full_path)
    return result


def 遍历目录树(dir_path: str) -> List[str]:
    """遍历目录树（递归，包含所有文件）"""
    return 遍历目录(dir_path, 递归=True)


def 目录列表(dir_path: str) -> List[str]:
    """列出目录中的所有项（文件和目录）"""
    return os.listdir(dir_path)


def 子目录列表(dir_path: str) -> List[str]:
    """列出目录中的子目录"""
    result = []
    for item in os.listdir(dir_path):
        full_path = os.path.join(dir_path, item)
        if os.path.isdir(full_path):
            result.append(full_path)
    return result


def 文件列表(dir_path: str) -> List[str]:
    """列出目录中的文件（完整路径）"""
    result = []
    for item in os.listdir(dir_path):
        full_path = os.path.join(dir_path, item)
        if os.path.isfile(full_path):
            result.append(full_path)
    return result


def 按扩展名筛选(dir_path: str, 扩展名: str) -> List[str]:
    """按扩展名筛选文件"""
    result = []
    for item in os.listdir(dir_path):
        full_path = os.path.join(dir_path, item)
        if os.path.isfile(full_path) and item.endswith(扩展名):
            result.append(full_path)
    return result


def 复制目录(src: str, dst: str) -> None:
    """复制目录"""
    shutil.copytree(src, dst)


def 重命名(src: str, dst: str) -> None:
    """重命名文件或目录"""
    os.rename(src, dst)


def 删除空目录(path: str) -> None:
    """删除空目录"""
    os.rmdir(path)


def 移动目录(src: str, dst: str) -> None:
    """移动目录"""
    shutil.move(src, dst)


def 创建符号链接(target: str, link_path: str) -> None:
    """创建符号链接"""
    os.symlink(target, link_path)


def 读取符号链接(link_path: str) -> str:
    """读取符号链接目标"""
    return os.readlink(link_path)


def 创建临时文件(suffix: str = '', prefix: str = 'tmp', dir: str = None) -> str:
    """创建临时文件，返回文件名"""
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    os.close(fd)
    return path


def 创建临时目录(suffix: str = '', prefix: str = 'tmp', dir: str = None) -> str:
    """创建临时目录，返回目录名"""
    return tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dir)


def 删除临时文件(path: str) -> None:
    """删除临时文件"""
    os.remove(path)


def 删除临时目录(path: str) -> None:
    """删除临时目录"""
    shutil.rmtree(path)


def 读取二进制文件(path: str) -> bytes:
    """读取二进制文件"""
    with open(path, 'rb') as f:
        return f.read()


def 写入二进制文件(path: str, content: bytes) -> None:
    """写入二进制文件"""
    with open(path, 'wb') as f:
        f.write(content)


def 追加二进制文件(path: str, content: bytes) -> None:
    """追加二进制内容到文件"""
    with open(path, 'ab') as f:
        f.write(content)


def 文件行列表(path: str, encoding: str = 'utf-8') -> List[str]:
    """读取文件为行列表"""
    with open(path, 'r', encoding=encoding) as f:
        return f.readlines()


def 写入行列表(path: str, 行列表: List[str], encoding: str = 'utf-8') -> None:
    """写入行列表到文件"""
    with open(path, 'w', encoding=encoding) as f:
        f.writelines(行列表)


def 读取文件块(path: str, 块大小: int = 4096, encoding: str = 'utf-8') -> List[str]:
    """按块读取文件"""
    blocks = []
    with open(path, 'r', encoding=encoding) as f:
        while True:
            block = f.read(块大小)
            if not block:
                break
            blocks.append(block)
    return blocks


def 当前工作目录() -> str:
    """获取当前工作目录"""
    return os.getcwd()


def 切换工作目录(path: str) -> None:
    """切换工作目录"""
    os.chdir(path)


def 获取环境变量(name: str, 默认值: str = None) -> Optional[str]:
    """获取环境变量"""
    return os.environ.get(name, 默认值)


def 设置环境变量(name: str, value: str) -> None:
    """设置环境变量"""
    os.environ[name] = value


def 目录大小(path: str) -> int:
    """计算目录大小（字节）"""
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total += os.path.getsize(filepath)
    return total


def 文件扩展名匹配(path: str, 扩展名: str) -> bool:
    """检查文件扩展名是否匹配"""
    return os.path.splitext(path)[1] == 扩展名


def 路径比较(path1: str, path2: str) -> bool:
    """比较两个路径是否相同"""
    return os.path.samefile(path1, path2)


def 获取磁盘使用情况(path: str = '/') -> Dict[str, Any]:
    """获取磁盘使用情况"""
    usage = shutil.disk_usage(path)
    return {
        '总空间': usage.total,
        '已用空间': usage.used,
        '可用空间': usage.free,
        '使用率': usage.used / usage.total * 100,
    }


def 创建文件(path: str) -> None:
    """创建空文件"""
    with open(path, 'w') as f:
        pass


def 触摸文件(path: str) -> None:
    """更新文件时间戳（不存在则创建）"""
    if os.path.exists(path):
        os.utime(path)
    else:
        创建文件(path)


def 批量重命名(dir_path: str, 前缀: str, 起始编号: int = 1, 扩展名: str = '') -> None:
    """批量重命名文件"""
    files = 文件列表(dir_path)
    for i, filepath in enumerate(files, 起始编号):
        _, ext = os.path.splitext(filepath)
        new_name = f"{前缀}{i}{ext}" if not 扩展名 else f"{前缀}{i}{扩展名}"
        os.rename(filepath, os.path.join(dir_path, new_name))


def 文件编码检测(path: str) -> str:
    """检测文件编码（简化版）"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read()
        return 'utf-8'
    except UnicodeDecodeError:
        try:
            with open(path, 'r', encoding='gbk') as f:
                f.read()
            return 'gbk'
        except UnicodeDecodeError:
            return '未知'


# 合并自高级文件.py的独有函数

def 移动(源路径: str, 目标路径: str) -> str:
    """
    移动文件或目录
    
    参数:
        源路径: 源路径
        目标路径: 目标路径
    
    返回:
        目标路径
    """
    return shutil.move(源路径, 目标路径)


def 磁盘使用情况(路径: str = ".") -> dict:
    """
    获取磁盘使用情况
    
    参数:
        路径: 路径
    
    返回:
        {'总空间': 字节数, '已用空间': 字节数, '可用空间': 字节数}
    """
    用法 = shutil.disk_usage(路径)
    return {
        '总空间': 用法.total,
        '已用空间': 用法.used,
        '可用空间': 用法.free,
    }


def 磁盘总空间(路径: str = ".") -> int:
    """获取磁盘总空间（字节）"""
    return shutil.disk_usage(路径).total


def 磁盘可用空间(路径: str = ".") -> int:
    """获取磁盘可用空间（字节）"""
    return shutil.disk_usage(路径).free


def 磁盘已用空间(路径: str = ".") -> int:
    """获取磁盘已用空间（字节）"""
    return shutil.disk_usage(路径).used


def 查找命令(命令名: str) -> Optional[str]:
    """
    查找可执行文件路径
    
    参数:
        命令名: 命令名称
    
    返回:
        可执行文件路径，未找到返回None
    """
    return shutil.which(命令名)


def 命令存在(命令名: str) -> bool:
    """检查命令是否存在"""
    return shutil.which(命令名) is not None


def 归档(源路径: str, 目标路径: str = None, 格式: str = "zip") -> str:
    """
    创建归档文件
    
    参数:
        源路径: 要归档的源路径
        目标路径: 目标归档文件路径（不含扩展名）
        格式: 归档格式（zip, tar, gztar, bztar, xztar）
    
    返回:
        归档文件路径
    """
    return shutil.make_archive(目标路径 or 源路径, 格式, 源路径)


def 解压(归档路径: str, 目标目录: str = None, 格式: str = None) -> None:
    """
    解压归档文件
    
    参数:
        归档路径: 归档文件路径
        目标目录: 目标目录，默认当前目录
        格式: 归档格式，None自动检测
    """
    shutil.unpack_archive(归档路径, 目标目录, 格式)


def 支持的归档格式() -> List[str]:
    """获取支持的归档格式列表"""
    return [f[0] for f in shutil.get_archive_formats()]


def 支持的解压格式() -> List[str]:
    """获取支持的解压格式列表"""
    return [f[0] for f in shutil.get_unpack_formats()]


# =============================================================================
# 随机文件访问
# =============================================================================

def 文件定位(文件对象, 偏移量: int,  whence: int = 0) -> int:
    """
    移动文件指针到指定位置

    参数:
        文件对象: 已打开的文件对象
        偏移量: 偏移量（字节）
        whence: 0=文件开头, 1=当前位置, 2=文件末尾

    返回:
        移动后的文件指针位置
    """
    return 文件对象.seek(偏移量, whence)


def 读取文件位置(path: str, 偏移量: int, 大小: int, encoding: str = 'utf-8') -> str:
    """
    从文件指定位置读取内容（文本模式）

    参数:
        path: 文件路径
        偏移量: 读取起始位置（字节偏移）
        大小: 读取的字符数
        encoding: 文件编码

    返回:
        读取的字符串
    """
    with open(path, 'r', encoding=encoding) as f:
        f.seek(偏移量)
        return f.read(大小)


def 读取二进制文件位置(path: str, 偏移量: int, 大小: int) -> bytes:
    """
    从文件指定位置读取二进制内容

    参数:
        path: 文件路径
        偏移量: 读取起始位置（字节偏移）
        大小: 读取的字节数

    返回:
        读取的字节数据
    """
    with open(path, 'rb') as f:
        f.seek(偏移量)
        return f.read(大小)


def 写入文件位置(path: str, 偏移量: int, 内容: str, encoding: str = 'utf-8') -> None:
    """
    在文件指定位置写入内容（文本模式）

    参数:
        path: 文件路径
        偏移量: 写入起始位置
        内容: 要写入的字符串
        encoding: 文件编码
    """
    with open(path, 'r+', encoding=encoding) as f:
        f.seek(偏移量)
        f.write(内容)


def 文件当前位置(文件对象) -> int:
    """获取文件当前指针位置"""
    return 文件对象.tell()


# =============================================================================
# 文件锁定（跨平台实现）
# =============================================================================

_文件锁注册表 = {}  # 跟踪已锁定的文件


def 文件锁定(path: str, 共享: bool = False) -> bool:
    """
    锁定文件（防止其他进程修改）

    参数:
        path: 文件路径
        共享: True=共享锁（读锁）, False=排他锁（写锁）

    返回:
        是否成功锁定
    """
    import platform as _平台
    try:
        if _平台.system() == 'Windows':
            import msvcrt as _msvcrt
            fd = os.open(path, os.O_RDWR | os.O_CREAT)
            flags = _msvcrt.LK_NBLCK if not 共享 else _msvcrt.LK_NBRLCK
            _msvcrt.locking(fd, flags, 1)
            _文件锁注册表[path] = fd
        else:
            import fcntl as _fcntl
            fd = os.open(path, os.O_RDWR | os.O_CREAT)
            flags = _fcntl.LOCK_EX | _fcntl.LOCK_NB if not 共享 else _fcntl.LOCK_SH | _fcntl.LOCK_NB
            _fcntl.flock(fd, flags)
            _文件锁注册表[path] = fd
        return True
    except (IOError, OSError):
        return False


def 文件解锁(path: str) -> bool:
    """
    解锁文件

    参数:
        path: 文件路径

    返回:
        是否成功解锁
    """
    import platform as _平台
    if path not in _文件锁注册表:
        return False
    try:
        fd = _文件锁注册表.pop(path)
        if _平台.system() == 'Windows':
            import msvcrt as _msvcrt
            _msvcrt.locking(fd, _msvcrt.LK_UNLCK, 1)
        else:
            import fcntl as _fcntl
            _fcntl.flock(fd, _fcntl.LOCK_UN)
        os.close(fd)
        return True
    except (IOError, OSError):
        return False


# =============================================================================
# 文件权限与所有权
# =============================================================================

def 设置权限(path: str, 权限码: int) -> None:
    """
    设置文件权限（chmod）

    参数:
        path: 文件路径
        权限码: 权限数字（如 0o644, 0o755）
    """
    os.chmod(path, 权限码)


def 获取权限(path: str) -> int:
    """
    获取文件权限码

    参数:
        path: 文件路径

    返回:
        权限数字（如 0o644）
    """
    return os.stat(path).st_mode


def 设置文件所有者(path: str, uid: int, gid: int) -> None:
    """
    设置文件所有者和组（chown）

    参数:
        path: 文件路径
        uid: 用户ID（-1 表示不修改）
        gid: 组ID（-1 表示不修改）
    """
    import platform as _平台
    if _平台.system() == 'Windows':
        raise NotImplementedError("Windows 不支持 chown 操作")
    os.chown(path, uid, gid)


def 获取文件所有者(path: str) -> Dict[str, Any]:
    """
    获取文件所有者和组信息

    参数:
        path: 文件路径

    返回:
        {'uid': 用户ID, 'gid': 组ID, '用户': 用户名, '组': 组名}
    """
    import platform as _平台
    stat = os.stat(path)
    结果 = {'uid': stat.st_uid, 'gid': stat.st_gid, '用户': str(stat.st_uid), '组': str(stat.st_gid)}
    if _平台.system() != 'Windows':
        try:
            import pwd as _pwd
            结果['用户'] = _pwd.getpwuid(stat.st_uid).pw_name
        except (ImportError, KeyError):
            pass
        try:
            import grp as _grp
            结果['组'] = _grp.getgrgid(stat.st_gid).gr_name
        except (ImportError, KeyError):
            pass
    return 结果


# =============================================================================
# 目录筛选与高级列表
# =============================================================================

def 筛选目录列表(dir_path: str, 模式: str = '*', 递归: bool = False) -> List[str]:
    """
    按模式筛选目录内容

    参数:
        dir_path: 目录路径
        模式: 匹配模式（支持 fnmatch 模式，如 *.txt, data_?.csv）
        递归: 是否递归搜索子目录

    返回:
        匹配的文件完整路径列表
    """
    import fnmatch as _fnmatch
    结果 = []
    if 递归:
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if _fnmatch.fnmatch(file, 模式):
                    结果.append(os.path.join(root, file))
    else:
        for item in os.listdir(dir_path):
            if _fnmatch.fnmatch(item, 模式):
                结果.append(os.path.join(dir_path, item))
    return 结果


def 按大小筛选目录(dir_path: str, 最小字节: int = 0, 最大字节: int = None, 递归: bool = False) -> List[str]:
    """
    按文件大小筛选目录内容

    参数:
        dir_path: 目录路径
        最小字节: 最小文件大小（字节）
        最大字节: 最大文件大小（字节，None 表示不限制）
        递归: 是否递归搜索

    返回:
        符合条件的文件完整路径列表
    """
    结果 = []
    文件路径列表 = 遍历目录(dir_path, 递归=递归)
    for fp in 文件路径列表:
        try:
            size = os.path.getsize(fp)
            if size >= 最小字节:
                if 最大字节 is None or size <= 最大字节:
                    结果.append(fp)
        except OSError:
            pass
    return 结果


def 按时间筛选目录(dir_path: str, 属性: str = '修改', 起始时间: float = 0, 结束时间: float = None, 递归: bool = False) -> List[str]:
    """
    按时间属性筛选目录内容

    参数:
        dir_path: 目录路径
        属性: 时间属性（'修改', '访问', '创建'）
        起始时间: 起始时间戳
        结束时间: 结束时间戳（None 表示不限制）
        递归: 是否递归搜索

    返回:
        符合条件的文件完整路径列表
    """
    时间函数 = {'修改': os.path.getmtime, '访问': os.path.getatime, '创建': os.path.getctime}
    获取时间 = 时间函数.get(属性, os.path.getmtime)
    结果 = []
    文件路径列表 = 遍历目录(dir_path, 递归=递归)
    for fp in 文件路径列表:
        try:
            t = 获取时间(fp)
            if t >= 起始时间:
                if 结束时间 is None or t <= 结束时间:
                    结果.append(fp)
        except OSError:
            pass
    return 结果


# =============================================================================
# 路径验证与高级操作
# =============================================================================

def 路径验证(path: str) -> Dict[str, Any]:
    """
    验证路径并返回详细信息

    参数:
        path: 要验证的路径

    返回:
        包含路径验证详情的字典
    """
    return {
        '路径': path,
        '绝对路径': os.path.abspath(path),
        '规范化路径': os.path.normpath(path),
        '存在': os.path.exists(path),
        '是文件': os.path.isfile(path),
        '是目录': os.path.isdir(path),
        '是符号链接': os.path.islink(path),
        '是绝对路径': os.path.isabs(path),
        '是挂载点': os.path.ismount(path),
        '可读': os.access(path, os.R_OK) if os.path.exists(path) else False,
        '可写': os.access(path, os.W_OK) if os.path.exists(path) else False,
        '可执行': os.access(path, os.X_OK) if os.path.exists(path) else False,
    }


def 展开用户目录(path: str) -> str:
    """
    展开路径中的 ~ 和 ~user 为完整用户目录路径

    参数:
        path: 包含 ~ 的路径

    返回:
        展开后的完整路径
    """
    return os.path.expanduser(path)


def 展开环境变量(path: str) -> str:
    """
    展开路径中的环境变量（如 $HOME, %APPDATA%）

    参数:
        path: 包含环境变量的路径

    返回:
        展开后的路径
    """
    return os.path.expandvars(path)


def 是否为有效路径名(path: str) -> bool:
    """
    检查路径名是否有效（不含非法字符）

    参数:
        path: 路径名

    返回:
        是否有效
    """
    import platform as _平台
    if not path or not path.strip():
        return False
    if _平台.system() == 'Windows':
        非法字符 = set('<>:"|?*')
        for part in path.split('\\'):
            if any(c in 非法字符 for c in part):
                return False
            if part.endswith(' ') or part.endswith('.'):
                return False
    else:
        if '\0' in path:
            return False
    return True


def 文件树(路径: str, 前缀: str = "", 显示大小: bool = True) -> str:
    """
    生成目录树状结构字符串
    
    参数:
        路径: 目录路径
        前缀: 行前缀
        显示大小: 是否显示文件大小
    
    返回:
        树状结构字符串
    """
    行列表 = []
    行列表.append(f"{前缀}{os.path.basename(路径) or 路径}/")
    
    try:
        项目列表 = sorted(os.listdir(路径))
    except PermissionError:
        行列表.append(f"{前缀}  [权限不足]")
        return "\n".join(行列表)
    
    文件列表 = [f for f in 项目列表 if os.path.isfile(os.path.join(路径, f))]
    目录列表 = [d for d in 项目列表 if os.path.isdir(os.path.join(路径, d))]
    
    # 显示目录
    for i, 目录 in enumerate(目录列表):
        是最后 = i == len(目录列表) - 1 and len(文件列表) == 0
        连接器 = "└── " if 是最后 else "├── "
        子前缀 = 前缀 + ("    " if 是最后 else "│   ")
        子路径 = os.path.join(路径, 目录)
        行列表.append(f"{前缀}{连接器}{目录}/")
        
        # 递归（限制深度，避免无限递归）
        子树 = 文件树(子路径, 子前缀, 显示大小)
        子行 = 子树.split("\n")
        行列表.extend(子行[1:])  # 跳过第一行（已由父级显示）
    
    # 显示文件
    for i, 文件 in enumerate(文件列表):
        是最后 = i == len(文件列表) - 1
        连接器 = "└── " if 是最后 else "├── "
        if 显示大小:
            try:
                大小 = os.path.getsize(os.path.join(路径, 文件))
                大小文本 = f" ({大小}字节)"
            except:
                大小文本 = ""
            行列表.append(f"{前缀}{连接器}{文件}{大小文本}")
        else:
            行列表.append(f"{前缀}{连接器}{文件}")

    return "\n".join(行列表)


# =============================================================================
# 文件类型与 MIME 检测
# =============================================================================

_魔术字节映射 = {
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'%PDF': 'application/pdf',
    b'PK\x03\x04': 'application/zip',
    b'RIFF': 'image/webp',
    b'\x1f\x8b': 'application/gzip',
    b'BZh': 'application/bzip2',
    b'\xfd7zXZ\x00': 'application/x-xz',
    b'\x00\x00\x00\x18ftyp': 'video/mp4',
    b'\x00\x00\x00\x1cftyp': 'video/mp4',
    b'\x1a\x45\xdf\xa3': 'video/webm',
    b'\x00\x00\x00\x0cftyp': 'image/heic',
}


def 文件类型检测(path: str) -> str:
    """
    检测文件类型（基于幻数/魔术字节）

    参数:
        path: 文件路径

    返回:
        文件类型描述（如 'PNG 图像', 'JPEG 图像', 'PDF 文档' 等）
    """
    类型映射 = {
        'image/png': 'PNG 图像',
        'image/jpeg': 'JPEG 图像',
        'image/gif': 'GIF 图像',
        'image/webp': 'WebP 图像',
        'image/heic': 'HEIC 图像',
        'application/pdf': 'PDF 文档',
        'application/zip': 'ZIP 压缩包',
        'application/gzip': 'GZIP 压缩包',
        'application/bzip2': 'BZIP2 压缩包',
        'application/x-xz': 'XZ 压缩包',
        'video/mp4': 'MP4 视频',
        'video/webm': 'WebM 视频',
    }
    try:
        mime = MIME类型检测(path)
        return 类型映射.get(mime, f'未知类型 ({mime})')
    except Exception:
        return '未知类型'


def MIME类型检测(path: str) -> str:
    """
    检测文件的 MIME 类型

    参数:
        path: 文件路径

    返回:
        MIME 类型字符串（如 'image/png', 'text/plain'）
    """
    import mimetypes as _mimetypes
    if not os.path.isfile(path):
        raise ValueError(f"文件不存在: {path}")

    # 先通过扩展名检测
    mime, _ = _mimetypes.guess_type(path)
    if mime:
        return mime

    # 通过魔术字节检测
    try:
        with open(path, 'rb') as f:
            magic = f.read(8)

        for sig, mime_type in _魔术字节映射.items():
            if magic.startswith(sig):
                return mime_type

        # 尝试检测文本文件
        try:
            with open(path, 'r', encoding='utf-8') as f:
                f.read(1024)
            return 'text/plain'
        except UnicodeDecodeError:
            return 'application/octet-stream'
    except OSError:
        return 'application/octet-stream'


# =============================================================================
# 文件哈希计算
# =============================================================================

def 计算文件MD5(path: str) -> str:
    """
    计算文件的 MD5 哈希值

    参数:
        path: 文件路径

    返回:
        32 位小写十六进制哈希字符串
    """
    import hashlib as _hashlib
    h = _hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def 计算文件SHA1(path: str) -> str:
    """
    计算文件的 SHA-1 哈希值

    参数:
        path: 文件路径

    返回:
        40 位小写十六进制哈希字符串
    """
    import hashlib as _hashlib
    h = _hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def 计算文件SHA256(path: str) -> str:
    """
    计算文件的 SHA-256 哈希值

    参数:
        path: 文件路径

    返回:
        64 位小写十六进制哈希字符串
    """
    import hashlib as _hashlib
    h = _hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def 计算文件哈希(path: str, 算法: str = 'sha256') -> str:
    """
    计算文件的哈希值（支持多种算法）

    参数:
        path: 文件路径
        算法: 哈希算法（'md5', 'sha1', 'sha256', 'sha512'）

    返回:
        十六进制哈希字符串
    """
    import hashlib as _hashlib
    算法映射 = {
        'md5': _hashlib.md5,
        'sha1': _hashlib.sha1,
        'sha256': _hashlib.sha256,
        'sha512': _hashlib.sha512,
    }
    if 算法 not in 算法映射:
        raise ValueError(f"不支持的哈希算法: {算法}，可选: {list(算法映射.keys())}")
    h = 算法映射[算法]()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


# =============================================================================
# 批量文件操作
# =============================================================================

def 批量复制文件(源目录: str, 目标目录: str, 模式: str = '*', 递归: bool = False) -> List[str]:
    """
    批量复制匹配模式的文件

    参数:
        源目录: 源目录路径
        目标目录: 目标目录路径
        模式: 匹配模式（如 *.txt, data_*.csv）
        递归: 是否递归搜索子目录

    返回:
        复制成功的文件路径列表
    """
    创建目录(目标目录)
    匹配文件列表 = 筛选目录列表(源目录, 模式, 递归=递归)
    复制成功列表 = []
    for fp in 匹配文件列表:
        rel = os.path.relpath(fp, 源目录)
        dst = os.path.join(目标目录, rel)
        创建目录(os.path.dirname(dst))
        try:
            shutil.copy2(fp, dst)
            复制成功列表.append(dst)
        except (IOError, OSError):
            pass
    return 复制成功列表


def 批量移动文件(源目录: str, 目标目录: str, 模式: str = '*', 递归: bool = False) -> List[str]:
    """
    批量移动匹配模式的文件

    参数:
        源目录: 源目录路径
        目标目录: 目标目录路径
        模式: 匹配模式（如 *.txt, data_*.csv）
        递归: 是否递归搜索子目录

    返回:
        移动成功的文件路径列表
    """
    创建目录(目标目录)
    匹配文件列表 = 筛选目录列表(源目录, 模式, 递归=递归)
    移动成功列表 = []
    for fp in 匹配文件列表:
        rel = os.path.relpath(fp, 源目录)
        dst = os.path.join(目标目录, rel)
        创建目录(os.path.dirname(dst))
        try:
            shutil.move(fp, dst)
            移动成功列表.append(dst)
        except (IOError, OSError):
            pass
    return 移动成功列表


def 批量删除文件(目录路径: str, 模式: str = '*', 递归: bool = False) -> int:
    """
    批量删除匹配模式的文件

    参数:
        目录路径: 目录路径
        模式: 匹配模式（如 *.tmp, *.log）
        递归: 是否递归搜索子目录

    返回:
        删除的文件数量
    """
    匹配文件列表 = 筛选目录列表(目录路径, 模式, 递归=递归)
    删除计数 = 0
    for fp in 匹配文件列表:
        try:
            os.remove(fp)
            删除计数 += 1
        except (IOError, OSError):
            pass
    return 删除计数


# =============================================================================
# 安全文件操作
# =============================================================================

def 安全写入文件(path: str, content: str, encoding: str = 'utf-8', 备份: bool = True) -> str:
    """
    安全写入文件（先备份再覆写）

    参数:
        path: 文件路径
        content: 要写入的内容
        encoding: 文件编码
        备份: 是否在覆写前备份原文件

    返回:
        备份文件路径（如果进行了备份），否则返回空字符串
    """
    备份路径 = ''
    if 备份 and os.path.isfile(path):
        备份路径 = path + '.bak'
        shutil.copy2(path, 备份路径)
    写入文件(path, content, encoding)
    return 备份路径


def 备份文件(path: str, 备份目录: str = None) -> str:
    """
    创建文件备份

    参数:
        path: 要备份的文件路径
        备份目录: 备份存放目录（None 表示与源文件同目录）

    返回:
        备份文件路径
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"文件不存在: {path}")
    if 备份目录:
        创建目录(备份目录)
        base = os.path.basename(path)
        备份路径 = os.path.join(备份目录, base + '.bak')
    else:
        备份路径 = path + '.bak'
    shutil.copy2(path, 备份路径)
    return 备份路径


def 安全删除文件(path: str, 移动到回收站: bool = False) -> bool:
    """
    安全删除文件（可选择移动到回收站或先备份再删除）

    参数:
        path: 要删除的文件路径
        移动到回收站: 是否尝试移动到回收站（需安装 send2trash）

    返回:
        是否成功
    """
    if not os.path.isfile(path):
        return False
    try:
        if 移动到回收站:
            try:
                import send2trash as _send2trash
                _send2trash.send2trash(path)
                return True
            except ImportError:
                # 备用：原地重命名再删除
                pass
        os.remove(path)
        return True
    except OSError:
        return False


# =============================================================================
# 文件比较
# =============================================================================

def 比较文件内容(path1: str, path2: str) -> bool:
    """
    比较两个文件内容是否完全相同

    参数:
        path1: 第一个文件路径
        path2: 第二个文件路径

    返回:
        内容是否相同
    """
    if not os.path.isfile(path1) or not os.path.isfile(path2):
        return False
    if os.path.getsize(path1) != os.path.getsize(path2):
        return False
    # 逐块比较
    with open(path1, 'rb') as f1, open(path2, 'rb') as f2:
        while True:
            chunk1 = f1.read(65536)
            chunk2 = f2.read(65536)
            if chunk1 != chunk2:
                return False
            if not chunk1:
                return True


def 比较文件信息(path1: str, path2: str) -> Dict[str, Any]:
    """
    比较两个文件的元信息（大小、时间、权限）

    参数:
        path1: 第一个文件路径
        path2: 第二个文件路径

    返回:
        包含比较结果的字典
    """
    info1 = os.stat(path1) if os.path.exists(path1) else None
    info2 = os.stat(path2) if os.path.exists(path2) else None
    return {
        '存在': os.path.exists(path1) and os.path.exists(path2),
        '大小相同': (info1 and info2) and info1.st_size == info2.st_size,
        '修改时间相同': (info1 and info2) and info1.st_mtime == info2.st_mtime,
        '权限相同': (info1 and info2) and info1.st_mode == info2.st_mode,
        '大小差异': (info1.st_size - info2.st_size) if info1 and info2 else None,
        '时间差异': (info1.st_mtime - info2.st_mtime) if info1 and info2 else None,
    }


def 查找重复文件(目录路径: str, 递归: bool = True) -> List[List[str]]:
    """
    查找目录中的重复文件（基于内容比较）

    参数:
        目录路径: 要搜索的目录
        递归: 是否递归搜索子目录

    返回:
        重复文件分组列表，每组包含路径相同的文件
    """
    文件大小映射 = {}
    文件列表 = 遍历目录(目录路径, 递归=递归)
    for fp in 文件列表:
        try:
            size = os.path.getsize(fp)
            文件大小映射.setdefault(size, []).append(fp)
        except OSError:
            pass

    # 只考虑大小相同的文件组
    重复分组 = []
    for size, paths in 文件大小映射.items():
        if len(paths) < 2:
            continue
        已比较 = set()
        for i in range(len(paths)):
            if i in 已比较:
                continue
            当前组 = [paths[i]]
            for j in range(i + 1, len(paths)):
                if j in 已比较:
                    continue
                try:
                    if 比较文件内容(paths[i], paths[j]):
                        当前组.append(paths[j])
                        已比较.add(j)
                except OSError:
                    pass
            if len(当前组) > 1:
                重复分组.append(当前组)
                已比较.add(i)
    return 重复分组


# =============================================================================
# 文件变更监控（轮询模式）
# =============================================================================

import threading as _threading
import time as _time


class _目录监控器:
    """目录变更监控器（内部类）"""

    def __init__(self, 目录路径: str, 回调函数, 模式: str = '*', 轮询间隔: float = 1.0):
        self.目录路径 = 目录路径
        self.回调函数 = 回调函数
        self.模式 = 模式
        self.轮询间隔 = 轮询间隔
        self._运行中 = False
        self._线程 = None
        self._已知状态 = {}

    def _获取快照(self) -> Dict[str, float]:
        """获取当前目录快照 {文件路径: 修改时间}"""
        快照 = {}
        for fp in 筛选目录列表(self.目录路径, self.模式, 递归=True):
            try:
                快照[fp] = os.path.getmtime(fp)
            except OSError:
                pass
        return 快照

    def _轮询循环(self):
        """轮询循环"""
        self._已知状态 = self._获取快照()
        while self._运行中:
            _time.sleep(self.轮询间隔)
            try:
                当前状态 = self._获取快照()
                # 检测新增文件
                for fp in 当前状态:
                    if fp not in self._已知状态:
                        self.回调函数('创建', fp)
                # 检测修改和删除的文件
                for fp in self._已知状态:
                    if fp not in 当前状态:
                        self.回调函数('删除', fp)
                    elif 当前状态[fp] != self._已知状态[fp]:
                        self.回调函数('修改', fp)
                self._已知状态 = 当前状态
            except Exception:
                pass

    def 启动(self):
        """启动监控"""
        if self._运行中:
            return
        self._运行中 = True
        self._线程 = _threading.Thread(target=self._轮询循环, daemon=True)
        self._线程.start()

    def 停止(self):
        """停止监控"""
        self._运行中 = False
        if self._线程:
            self._线程.join(timeout=5)
            self._线程 = None


_监控器注册表 = {}  # type: Dict[str, _目录监控器]


def 目录监控(目录路径: str, 回调函数, 模式: str = '*', 轮询间隔: float = 1.0) -> str:
    """
    监控目录文件变更

    参数:
        目录路径: 要监控的目录路径
        回调函数: 变更回调函数，签名 callback(事件类型, 文件路径)
                  事件类型: '创建', '修改', '删除'
        模式: 文件匹配模式（如 *.txt, *.py）
        轮询间隔: 轮询间隔（秒），最小 0.1

    返回:
        监控器 ID（可用于停止监控）
    """
    实例 = _目录监控器(目录路径, 回调函数, 模式, max(轮询间隔, 0.1))
    监控器ID = f"watch_{id(实例)}"
    _监控器注册表[监控器ID] = 实例
    实例.启动()
    return 监控器ID


def 停止目录监控(监控器ID: str) -> bool:
    """
    停止目录监控

    参数:
        监控器ID: 目录监控返回的监控器 ID

    返回:
        是否成功停止
    """
    if 监控器ID not in _监控器注册表:
        return False
    _监控器注册表[监控器ID].停止()
    del _监控器注册表[监控器ID]
    return True


def 停止所有监控() -> int:
    """停止所有目录监控，返回停止的数量"""
    计数 = 0
    for 监控器ID in list(_监控器注册表.keys()):
        try:
            停止目录监控(监控器ID)
            计数 += 1
        except Exception:
            pass
    return 计数