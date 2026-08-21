"""
文件上传 — lightpub 桥接模块

基于 Python cgi / os / uuid / hashlib / mimetypes 库封装，函数名对齐上游 duanpub（段言时期）packages/文件上传/源.duan。

上游 duanpub 原始包通过 C FFI 实现 HTTP 多部分表单解析，
本桥接模块用 Python 标准库替代，提供文件上传处理功能。
"""

import os as _os
import uuid as _uuid
import hashlib as _hashlib
import mimetypes as _mimetypes
import time as _time
import random as _random
import string as _string


# =============================================================================
# 内部工具函数
# =============================================================================

def 内部取时间戳():
    """获取当前时间戳"""
    return _time.time()


def 内部包含(字符串, 子串):
    """检查字符串是否包含子串"""
    return 子串 in 字符串


def 范围(开始, 结束, 步长=1):
    """生成范围列表"""
    return list(range(开始, 结束, 步长))


def 内部分割(字符串, 分隔符):
    """分割字符串"""
    return 字符串.split(分隔符)


def 内部转为小写(字符串):
    """转为小写"""
    return 字符串.lower()


def 内部整数转字符串(整数):
    """整数转字符串"""
    return str(整数)


def 内部字符串转整数(字符串):
    """字符串转整数"""
    return int(字符串)


def 内部下一个随机数():
    """生成下一个随机数"""
    return _random.random()


def 内部随机字符串(长度=8):
    """生成随机字符串"""
    return ''.join(_random.choices(_string.ascii_letters + _string.digits, k=长度))


# =============================================================================
# 上传配置
# =============================================================================

class 上传配置:
    """文件上传配置"""
    def __init__(self, 存储目录='./uploads', 最大文件大小=10*1024*1024,
                 允许类型=None, 覆盖已存在=False, 唯一文件名=True):
        self.存储目录 = 存储目录
        self.最大文件大小 = 最大文件大小
        self.允许类型 = 允许类型 or []
        self.覆盖已存在 = 覆盖已存在
        self.唯一文件名 = 唯一文件名


def 创建上传配置(存储目录='./uploads', 最大文件大小=10*1024*1024, 允许类型=None, 覆盖已存在=False, 唯一文件名=True):
    """创建上传配置对象"""
    return 上传配置(存储目录=存储目录, 最大文件大小=最大文件大小, 允许类型=允许类型, 覆盖已存在=覆盖已存在, 唯一文件名=唯一文件名)


# =============================================================================
# 内部解析函数
# =============================================================================

def 内部提取边界(content_type):
    """从 Content-Type 中提取 boundary"""
    if not content_type:
        return None
    parts = content_type.split(';')
    for part in parts:
        part = part.strip()
        if part.startswith('boundary='):
            return part[9:].strip('"')
    return None


def 内部解析内容部署(content_disposition):
    """解析 Content-Disposition 头"""
    result = {}
    if not content_disposition:
        return result
    parts = content_disposition.split(';')
    for part in parts:
        part = part.strip()
        if '=' in part:
            key, val = part.split('=', 1)
            result[key.strip().lower()] = val.strip().strip('"')
        else:
            result['type'] = part
    return result


def 内部解析多部分头(头文本):
    """解析多部分头部"""
    if not 头文本:
        return {}
    headers = {}
    for line in 头文本.strip().split('\n'):
        line = line.strip()
        if ':' in line:
            key, val = line.split(':', 1)
            headers[key.strip().lower()] = val.strip()
    return headers


def 内部魔术字节检测(文件路径):
    """检测文件魔术字节，返回文件类型签名"""
    if not 文件路径 or not _os.path.exists(文件路径):
        return b''
    try:
        with open(文件路径, 'rb') as f:
            return f.read(8)
    except Exception:
        return b''


def 内部生成唯一文件名(原始文件名):
    """生成唯一文件名"""
    if not 原始文件名:
        return str(_uuid.uuid4())
    ext = _os.path.splitext(原始文件名)[1]
    return str(_uuid.uuid4()) + ext


# =============================================================================
# 文件类型检测
# =============================================================================

_MAGIC_MAP = {
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'%PDF': 'application/pdf',
    b'PK\x03\x04': 'application/zip',
    b'RIFF': 'image/webp',
}


def 检测文件类型(文件路径):
    """检测文件类型"""
    if not 文件路径:
        raise Exception("检测文件类型失败: 文件路径为空")
    try:
        # 先通过扩展名检测
        mime_type, _ = _mimetypes.guess_type(文件路径)
        if mime_type:
            return mime_type

        # 通过魔术字节检测
        magic = 内部魔术字节检测(文件路径)
        for sig, mime in _MAGIC_MAP.items():
            if magic.startswith(sig):
                return mime
        return 'application/octet-stream'
    except Exception as e:
        raise Exception("检测文件类型失败: " + str(e))


def 检测文件类型从内容(内容):
    """从文件内容检测文件类型"""
    if not 内容:
        return 'application/octet-stream'
    try:
        if isinstance(内容, str):
            内容 = 内容.encode('utf-8')
        for sig, mime in _MAGIC_MAP.items():
            if 内容.startswith(sig):
                return mime
        return 'application/octet-stream'
    except Exception as e:
        raise Exception("检测文件类型从内容失败: " + str(e))


def 验证文件类型(文件路径, 允许类型列表):
    """验证文件类型是否在允许列表中"""
    if not 允许类型列表:
        return True
    try:
        文件类型 = 检测文件类型(文件路径)
        return 文件类型 in 允许类型列表
    except Exception:
        return False


def 验证文件大小(文件路径, 最大大小):
    """验证文件大小是否在限制内"""
    if not 文件路径:
        return False
    try:
        size = _os.path.getsize(文件路径)
        return size <= 最大大小
    except Exception:
        return False


def 生成存储路径(配置, 文件名):
    """生成存储路径"""
    if not 配置 or not 文件名:
        raise Exception("生成存储路径失败: 参数无效")
    try:
        if not _os.path.exists(配置.存储目录):
            _os.makedirs(配置.存储目录, exist_ok=True)
        if 配置.唯一文件名:
            文件名 = 内部生成唯一文件名(文件名)
        路径 = _os.path.join(配置.存储目录, 文件名)
        return 路径
    except Exception as e:
        raise Exception("生成存储路径失败: " + str(e))


# =============================================================================
# 多部分解析
# =============================================================================

class 文件部分:
    """多部分文件部分"""
    def __init__(self):
        self.字段名 = ''
        self.文件名 = ''
        self.内容类型 = ''
        self.内容 = b''
        self.头部 = {}


def 解析多部分(数据, 边界):
    """解析多部分表单数据"""
    if not 数据 or not 边界:
        raise Exception("解析多部分失败: 参数为空")
    try:
        if isinstance(数据, str):
            数据 = 数据.encode('utf-8')
        if isinstance(边界, str):
            边界 = 边界.encode('utf-8')

        parts = []
        delimiter = b'--' + 边界
        raw_parts = 数据.split(delimiter)

        for raw_part in raw_parts:
            # 跳过边界标记和尾部
            if not raw_part or raw_part == b'--\r\n' or raw_part == b'--\n':
                continue

            # 移除开头的 \r\n
            if raw_part.startswith(b'\r\n'):
                raw_part = raw_part[2:]
            # 移除尾部的 \r\n--
            if raw_part.endswith(b'--\r\n'):
                raw_part = raw_part[:-4]
            elif raw_part.endswith(b'--\n'):
                raw_part = raw_part[:-3]
            elif raw_part.endswith(b'\r\n'):
                raw_part = raw_part[:-2]

            if not raw_part:
                continue

            # 分割头部和内容
            header_end = raw_part.find(b'\r\n\r\n')
            if header_end == -1:
                continue

            header_bytes = raw_part[:header_end]
            body_bytes = raw_part[header_end + 4:]

            headers = {}
            for line in header_bytes.decode('utf-8', errors='replace').split('\r\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    headers[key.strip().lower()] = val.strip()

            # 解析 Content-Disposition
            part = 文件部分()
            part.头部 = headers
            part.内容 = body_bytes

            cd = headers.get('content-disposition', '')
            cd_info = 内部解析内容部署(cd)
            part.字段名 = cd_info.get('name', '')
            part.文件名 = cd_info.get('filename', '')
            part.内容类型 = headers.get('content-type', 'application/octet-stream')

            parts.append(part)

        return parts
    except Exception as e:
        raise Exception("解析多部分失败: " + str(e))


def 解析多部分流式(数据, 边界):
    """流式解析多部分表单数据"""
    return 解析多部分(数据, 边界)


# =============================================================================
# 文件保存
# =============================================================================

def 保存文件(部分, 存储路径):
    """保存文件部分到磁盘"""
    if not 部分 or not 部分.内容:
        raise Exception("保存文件失败: 内容为空")
    if not 存储路径:
        raise Exception("保存文件失败: 存储路径为空")
    try:
        目录 = _os.path.dirname(存储路径)
        if 目录 and not _os.path.exists(目录):
            _os.makedirs(目录, exist_ok=True)
        with open(存储路径, 'wb') as f:
            f.write(部分.内容)
        return 存储路径
    except OSError as e:
        raise Exception("保存文件失败: " + str(e))


def 保存所有文件(parts, 配置):
    """保存所有文件部分"""
    if not parts or not 配置:
        raise Exception("保存所有文件失败: 参数无效")
    try:
        if not _os.path.exists(配置.存储目录):
            _os.makedirs(配置.存储目录, exist_ok=True)

        saved = []
        for part in parts:
            if part.文件名:
                路径 = 生成存储路径(配置, part.文件名)
                保存文件(part, 路径)
                saved.append({
                    '字段名': part.字段名,
                    '文件名': part.文件名,
                    '存储路径': 路径,
                    '大小': len(part.内容),
                    '内容类型': part.内容类型,
                })
        return saved
    except Exception as e:
        raise Exception("保存所有文件失败: " + str(e))


# =============================================================================
# 存储驱动
# =============================================================================

class 本地存储驱动:
    """本地文件存储驱动"""
    def __init__(self, 根目录):
        self.根目录 = 根目录
        if not _os.path.exists(根目录):
            _os.makedirs(根目录, exist_ok=True)

    def 保存(self, 文件路径, 数据):
        full_path = _os.path.join(self.根目录, 文件路径)
        dir_name = _os.path.dirname(full_path)
        if dir_name and not _os.path.exists(dir_name):
            _os.makedirs(dir_name, exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(数据)
        return full_path

    def 读取(self, 文件路径):
        full_path = _os.path.join(self.根目录, 文件路径)
        with open(full_path, 'rb') as f:
            return f.read()

    def 删除(self, 文件路径):
        full_path = _os.path.join(self.根目录, 文件路径)
        if _os.path.exists(full_path):
            _os.remove(full_path)


class 内存存储驱动:
    """内存存储驱动"""
    def __init__(self):
        self._数据 = {}

    def 保存(self, 文件路径, 数据):
        self._数据[文件路径] = 数据
        return 文件路径

    def 读取(self, 文件路径):
        return self._数据.get(文件路径)

    def 删除(self, 文件路径):
        self._数据.pop(文件路径, None)


def 创建本地存储驱动(根目录):
    """创建本地存储驱动"""
    return 本地存储驱动(根目录)


def 创建内存存储驱动():
    """创建内存存储驱动"""
    return 内存存储驱动()


# =============================================================================
# 断点续传
# =============================================================================

class 断点续传:
    """断点续传管理器"""
    def __init__(self, 文件标识):
        self.文件标识 = 文件标识
        self._分块 = {}
        self._总大小 = 0
        self._已接收 = 0

    def 添加分块(self, 分块编号, 数据):
        self._分块[分块编号] = 数据
        self._已接收 += len(数据)

    def 获取缺失分块(self, 总块数):
        return [i for i in range(总块数) if i not in self._分块]

    def 是否完成(self, 总块数):
        return len(self._分块) >= 总块数

    def 合并分块(self, 总块数, 输出路径):
        if not self.是否完成(总块数):
            raise Exception("合并分块失败: 分块不完整")
        try:
            with open(输出路径, 'wb') as f:
                for i in range(总块数):
                    f.write(self._分块[i])
            return 输出路径
        except OSError as e:
            raise Exception("合并分块失败: " + str(e))

    def 获取进度(self, 总块数):
        return {
            '总块数': 总块数,
            '已接收块数': len(self._分块),
            '总大小': self._总大小,
            '已接收大小': self._已接收,
            '进度百分比': (len(self._分块) / 总块数 * 100) if 总块数 > 0 else 0,
        }


def 创建断点续传(文件标识):
    """创建断点续传管理器"""
    return 断点续传(文件标识)


def 断点续传添加分块(uploader, 分块编号, 数据):
    """添加分块数据"""
    if uploader:
        uploader.添加分块(分块编号, 数据)


def 断点续传获取缺失分块(uploader, 总块数):
    """获取缺失的分块编号列表"""
    if uploader:
        return uploader.获取缺失分块(总块数)
    return []


def 断点续传是否完成(uploader, 总块数):
    """检查上传是否完成"""
    if uploader:
        return uploader.是否完成(总块数)
    return False


def 断点续传合并分块(uploader, 总块数, 输出路径):
    """合并分块为完整文件"""
    if uploader:
        return uploader.合并分块(总块数, 输出路径)
    raise Exception("断点续传合并分块失败: uploader 为空")


def 断点续传获取进度(uploader, 总块数):
    """获取上传进度"""
    if uploader:
        return uploader.获取进度(总块数)
    return {}