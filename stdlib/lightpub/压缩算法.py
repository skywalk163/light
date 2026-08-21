"""
压缩算法 — lightpub 桥接模块

基于 Python gzip / zlib 标准库封装，函数名对齐上游 duanpub（段言时期）packages/压缩算法/源.duan。

上游 duanpub 原始包通过 C FFI 调用 zlib/lz4/zstd 库，
本桥接模块用 Python 标准库替代：
  - gzip压缩/解压: Python gzip 模块
  - zlib压缩/解压: Python zlib 模块
  - lz4压缩/解压: 需要第三方 lz4 库 (skeleton)
  - zstd压缩/解压: 需要第三方 zstd 库 (skeleton)
"""

import gzip as _gzip
import zlib as _zlib
import io as _io


# =============================================================================
# gzip 压缩/解压
# =============================================================================

def gzip压缩(数据, 压缩级别=9):
    """gzip 压缩数据，返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        return _gzip.compress(数据, compresslevel=压缩级别)
    except Exception as e:
        raise Exception("gzip压缩失败: " + str(e))


def gzip解压(数据):
    """gzip 解压数据，返回字节"""
    try:
        return _gzip.decompress(数据)
    except Exception as e:
        raise Exception("gzip解压失败: " + str(e))


# =============================================================================
# zlib 压缩/解压
# =============================================================================

def zlib压缩(数据, 压缩级别=9):
    """zlib 压缩数据，返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        return _zlib.compress(数据, level=压缩级别)
    except Exception as e:
        raise Exception("zlib压缩失败: " + str(e))


def zlib解压(数据):
    """zlib 解压数据，返回字节"""
    try:
        return _zlib.decompress(数据)
    except Exception as e:
        raise Exception("zlib解压失败: " + str(e))


# =============================================================================
# lz4 压缩/解压 (skeleton - 需要第三方库)
# =============================================================================

def lz4压缩(数据):
    """
    lz4 压缩数据

    注意: 需要安装第三方 lz4 库 (pip install lz4)
    """
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        import lz4.frame as _lz4frame
        return _lz4frame.compress(数据)
    except ImportError:
        raise Exception("lz4压缩失败: 需要安装 lz4 库 (pip install lz4)")
    except Exception as e:
        raise Exception("lz4压缩失败: " + str(e))


def lz4解压(数据):
    """
    lz4 解压数据

    注意: 需要安装第三方 lz4 库 (pip install lz4)
    """
    try:
        import lz4.frame as _lz4frame
        return _lz4frame.decompress(数据)
    except ImportError:
        raise Exception("lz4解压失败: 需要安装 lz4 库 (pip install lz4)")
    except Exception as e:
        raise Exception("lz4解压失败: " + str(e))


# =============================================================================
# zstd 压缩/解压 (skeleton - 需要第三方库)
# =============================================================================

def zstd压缩(数据, 压缩级别=3):
    """
    zstd 压缩数据

    注意: 需要安装第三方 zstd 库 (pip install zstandard)
    """
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        import zstandard as _zstd
        compressor = _zstd.ZstdCompressor(level=压缩级别)
        return compressor.compress(数据)
    except ImportError:
        raise Exception("zstd压缩失败: 需要安装 zstandard 库 (pip install zstandard)")
    except Exception as e:
        raise Exception("zstd压缩失败: " + str(e))


def zstd解压(数据):
    """
    zstd 解压数据

    注意: 需要安装第三方 zstd 库 (pip install zstandard)
    """
    try:
        import zstandard as _zstd
        decompressor = _zstd.ZstdDecompressor()
        return decompressor.decompress(数据)
    except ImportError:
        raise Exception("zstd解压失败: 需要安装 zstandard 库 (pip install zstandard)")
    except Exception as e:
        raise Exception("zstd解压失败: " + str(e))