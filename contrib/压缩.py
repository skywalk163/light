"""
光明标准库 - 压缩模块

封装 gzip、zipfile、tarfile 等模块，提供文件压缩解压功能。
"""

import gzip
import zipfile
import tarfile
import os
import zlib
from typing import List, Optional


# ========== ZIP ==========

def 创建ZIP(源路径: str, 压缩文件路径: str, 包含目录名: bool = True) -> None:
    """
    创建ZIP压缩文件
    
    参数:
        源路径: 要压缩的文件或目录路径
        压缩文件路径: 输出的ZIP文件路径
        包含目录名: 目录压缩时是否包含目录名
    """
    with zipfile.ZipFile(压缩文件路径, 'w', zipfile.ZIP_DEFLATED) as zf:
        if os.path.isfile(源路径):
            zf.write(源路径, os.path.basename(源路径))
        elif os.path.isdir(源路径):
            基目录 = os.path.dirname(源路径) if 包含目录名 else 源路径
            前缀 = os.path.basename(源路径) if 包含目录名 else ""
            for 目录路径, 子目录, 文件列表 in os.walk(源路径):
                for 文件 in 文件列表:
                    完整路径 = os.path.join(目录路径, 文件)
                    相对路径 = os.path.relpath(完整路径, 基目录)
                    zf.write(完整路径, 相对路径)


def 解压ZIP(压缩文件路径: str, 目标目录: str = ".") -> None:
    """
    解压ZIP文件
    
    参数:
        压缩文件路径: ZIP文件路径
        目标目录: 目标目录
    """
    with zipfile.ZipFile(压缩文件路径, 'r') as zf:
        zf.extractall(目标目录)


def 列出ZIP内容(压缩文件路径: str) -> List[dict]:
    """
    列出ZIP文件内容
    
    参数:
        压缩文件路径: ZIP文件路径
    
    返回:
        文件信息字典列表
    """
    with zipfile.ZipFile(压缩文件路径, 'r') as zf:
        结果 = []
        for 信息 in zf.infolist():
            结果.append({
                '文件名': 信息.filename,
                '原始大小': 信息.file_size,
                '压缩后大小': 信息.compress_size,
                '是否目录': 信息.is_dir(),
            })
        return 结果


def ZIP文件存在(压缩文件路径: str, 文件名: str) -> bool:
    """检查ZIP文件中是否存在指定文件"""
    with zipfile.ZipFile(压缩文件路径, 'r') as zf:
        return 文件名 in zf.namelist()


def 读取ZIP文件(压缩文件路径: str, 文件名: str) -> bytes:
    """从ZIP中读取单个文件内容"""
    with zipfile.ZipFile(压缩文件路径, 'r') as zf:
        return zf.read(文件名)


def 添加到ZIP(压缩文件路径: str, 文件路径: str, 归档名: str = None) -> None:
    """向现有ZIP文件添加文件"""
    with zipfile.ZipFile(压缩文件路径, 'a', zipfile.ZIP_DEFLATED) as zf:
        名称 = 归档名 or os.path.basename(文件路径)
        zf.write(文件路径, 名称)


def 是ZIP文件(路径: str) -> bool:
    """检查是否为ZIP文件"""
    return zipfile.is_zipfile(路径)


# ========== GZIP ==========

def GZIP压缩(源文件路径: str, 压缩文件路径: str = None) -> str:
    """
    GZIP压缩单个文件
    
    参数:
        源文件路径: 源文件路径
        压缩文件路径: 输出路径，默认源文件+'.gz'
    
    返回:
        压缩文件路径
    """
    输出 = 压缩文件路径 or (源文件路径 + '.gz')
    with open(源文件路径, 'rb') as f_in:
        with gzip.open(输出, 'wb') as f_out:
            f_out.write(f_in.read())
    return 输出


def GZIP解压(压缩文件路径: str, 输出路径: str = None) -> str:
    """
    GZIP解压文件
    
    参数:
        压缩文件路径: GZIP文件路径
        输出路径: 输出路径，默认去掉.gz
    
    返回:
        解压后的文件路径
    """
    输出 = 输出路径
    if not 输出:
        if 压缩文件.endswith('.gz'):
            输出 = 压缩文件路径[:-3]
        else:
            输出 = 压缩文件路径 + '.out'
    
    with gzip.open(压缩文件路径, 'rb') as f_in:
        with open(输出, 'wb') as f_out:
            f_out.write(f_in.read())
    return 输出


def GZIP压缩字符串(数据: str, 编码: str = 'utf-8') -> bytes:
    """GZIP压缩字符串"""
    return gzip.compress(数据.encode(编码))


def GZIP解压字符串(数据: bytes, 编码: str = 'utf-8') -> str:
    """GZIP解压为字符串"""
    return gzip.decompress(数据).decode(编码)


def 是GZIP文件(路径: str) -> bool:
    """检查是否为GZIP文件"""
    try:
        with gzip.open(路径, 'rb') as f:
            f.read(1)
        return True
    except:
        return False


# ========== TAR ==========

def 创建TAR(源路径: str, 压缩文件路径: str, 压缩: str = None) -> None:
    """
    创建TAR归档
    
    参数:
        源路径: 源文件或目录
        压缩文件路径: 输出文件路径
        压缩: 压缩方式（None, 'gz', 'bz2', 'xz'）
    """
    模式 = 'w' if 压缩 is None else f'w:{压缩}'
    with tarfile.open(压缩文件路径, 模式) as tf:
        tf.add(源路径, arcname=os.path.basename(源路径))


def 解压TAR(压缩文件路径: str, 目标目录: str = ".") -> None:
    """解压TAR归档"""
    with tarfile.open(压缩文件路径, 'r:*') as tf:
        tf.extractall(目标目录)


def 列出TAR内容(压缩文件路径: str) -> List[str]:
    """列出TAR文件内容"""
    with tarfile.open(压缩文件路径, 'r:*') as tf:
        return tf.getnames()


def 是TAR文件(路径: str) -> bool:
    """检查是否为TAR文件"""
    return tarfile.is_tarfile(路径)


# ========== ZLIB 内存压缩 ==========

def 内存压缩(数据: bytes, 级别: int = 6) -> bytes:
    """
    内存中压缩数据
    
    参数:
        数据: 原始字节数据
        级别: 压缩级别（0-9）
    
    返回:
        压缩后的数据
    """
    return zlib.compress(数据, 级别)


def 内存解压(数据: bytes) -> bytes:
    """内存中解压数据"""
    return zlib.decompress(数据)


def 压缩字符串(文本: str, 编码: str = 'utf-8') -> bytes:
    """压缩字符串为字节"""
    return zlib.compress(文本.encode(编码))


def 解压字符串(数据: bytes, 编码: str = 'utf-8') -> str:
    """解压字节为字符串"""
    return zlib.decompress(数据).decode(编码)


def CRC32(数据: bytes) -> int:
    """计算CRC32校验值"""
    return zlib.crc32(数据) & 0xffffffff


def Adler32(数据: bytes) -> int:
    """计算Adler-32校验值"""
    return zlib.adler32(数据) & 0xffffffff


__all__ = [
    # ZIP
    '创建ZIP', '解压ZIP', '列出ZIP内容', 'ZIP文件存在',
    '读取ZIP文件', '添加到ZIP', '是ZIP文件',
    # GZIP
    'GZIP压缩', 'GZIP解压', 'GZIP压缩字符串', 'GZIP解压字符串', '是GZIP文件',
    # TAR
    '创建TAR', '解压TAR', '列出TAR内容', '是TAR文件',
    # 内存压缩
    '内存压缩', '内存解压', '压缩字符串', '解压字符串',
    'CRC32', 'Adler32',
]
