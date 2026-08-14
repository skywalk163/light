"""
段言标准库 - 编码解码模块

提供编码解码功能，包括：
- Base64/Base32/Base16编码解码
- URL编码解码
- 字符集转换
- 十六进制编码解码
"""

import base64
import urllib.parse
import codecs


def Base64编码(数据: str, 编码: str = 'utf-8') -> str:
    """Base64编码（字符串输入）"""
    return base64.b64encode(数据.encode(编码)).decode('ascii')


def Base64解码(数据: str, 编码: str = 'utf-8') -> str:
    """Base64解码（返回字符串）"""
    return base64.b64decode(数据).decode(编码)


def Base64编码二进制(数据: bytes) -> bytes:
    """Base64编码（二进制输入）"""
    return base64.b64encode(数据)


def Base64解码二进制(数据: bytes) -> bytes:
    """Base64解码（二进制输入输出）"""
    return base64.b64decode(数据)


def Base64URL编码(数据: str, 编码: str = 'utf-8') -> str:
    """URL安全的Base64编码"""
    return base64.urlsafe_b64encode(数据.encode(编码)).decode('ascii')


def Base64URL解码(数据: str, 编码: str = 'utf-8') -> str:
    """URL安全的Base64解码"""
    return base64.urlsafe_b64decode(数据).decode(编码)


def Base32编码(数据: str, 编码: str = 'utf-8') -> str:
    """Base32编码"""
    return base64.b32encode(数据.encode(编码)).decode('ascii')


def Base32解码(数据: str, 编码: str = 'utf-8') -> str:
    """Base32解码"""
    return base64.b32decode(数据).decode(编码)


def Base16编码(数据: str, 编码: str = 'utf-8') -> str:
    """Base16编码（十六进制）"""
    return base64.b16encode(数据.encode(编码)).decode('ascii')


def Base16解码(数据: str, 编码: str = 'utf-8') -> str:
    """Base16解码（十六进制）"""
    return base64.b16decode(数据).decode(编码)


def 十六进制编码(数据: str, 编码: str = 'utf-8') -> str:
    """十六进制编码（小写）"""
    return 数据.encode(编码).hex()


def 十六进制解码(数据: str, 编码: str = 'utf-8') -> str:
    """十六进制解码"""
    return bytes.fromhex(数据).decode(编码)


def 十六进制编码大写(数据: str, 编码: str = 'utf-8') -> str:
    """十六进制编码（大写）"""
    return 数据.encode(编码).hex().upper()


def 二进制转十六进制(数据: bytes) -> str:
    """二进制转十六进制"""
    return 数据.hex()


def 十六进制转二进制(数据: str) -> bytes:
    """十六进制转二进制"""
    return bytes.fromhex(数据)


def URL编码(文本: str, 编码: str = 'utf-8') -> str:
    """URL编码"""
    return urllib.parse.quote(文本, encoding=编码)


def URL解码(文本: str, 编码: str = 'utf-8') -> str:
    """URL解码"""
    return urllib.parse.unquote(文本, encoding=编码)


def URL编码全字符(文本: str, 编码: str = 'utf-8') -> str:
    """URL编码（包括安全字符）"""
    return urllib.parse.quote(文本, '', encoding=编码)


def URL查询串编码(参数: dict, 编码: str = 'utf-8') -> str:
    """编码URL查询字符串"""
    return urllib.parse.urlencode(参数, encoding=编码)


def URL查询串解码(查询串: str, 编码: str = 'utf-8') -> dict:
    """解码URL查询字符串"""
    结果 = urllib.parse.parse_qs(查询串, encoding=编码)
    return {k: v[0] if len(v) == 1 else v for k, v in 结果.items()}


def Unicode转ASCII(文本: str) -> str:
    """Unicode转ASCII（转义）"""
    return text.encode('ascii', errors='backslashreplace').decode('ascii')


def ASCII转Unicode(文本: str) -> str:
    """ASCII转Unicode（还原转义）"""
    return text.encode('ascii').decode('unicode_escape')


def GBK转UTF8(数据: bytes) -> str:
    """GBK转UTF-8"""
    return 数据.decode('gbk').encode('utf-8').decode('utf-8')


def UTF8转GBK(数据: str) -> bytes:
    """UTF-8转GBK"""
    return 数据.encode('utf-8').decode('utf-8').encode('gbk')


def GB2312转UTF8(数据: bytes) -> str:
    """GB2312转UTF-8"""
    return 数据.decode('gb2312').encode('utf-8').decode('utf-8')


def UTF8转GB2312(数据: str) -> bytes:
    """UTF-8转GB2312"""
    return 数据.encode('utf-8').decode('utf-8').encode('gb2312')


def GB18030转UTF8(数据: bytes) -> str:
    """GB18030转UTF-8"""
    return 数据.decode('gb18030').encode('utf-8').decode('utf-8')


def UTF8转GB18030(数据: str) -> bytes:
    """UTF-8转GB18030"""
    return 数据.encode('utf-8').decode('utf-8').encode('gb18030')


def BIG5转UTF8(数据: bytes) -> str:
    """BIG5转UTF-8"""
    return 数据.decode('big5').encode('utf-8').decode('utf-8')


def UTF8转BIG5(数据: str) -> bytes:
    """UTF-8转BIG5"""
    return 数据.encode('utf-8').decode('utf-8').encode('big5')


def ISO8859_1转UTF8(数据: bytes) -> str:
    """ISO-8859-1转UTF-8"""
    return 数据.decode('iso-8859-1').encode('utf-8').decode('utf-8')


def UTF8转ISO8859_1(数据: str) -> bytes:
    """UTF-8转ISO-8859-1"""
    return 数据.encode('utf-8').decode('utf-8').encode('iso-8859-1')


def 字符集转换(数据: bytes, 源编码: str, 目标编码: str) -> bytes:
    """通用字符集转换"""
    return 数据.decode(源编码).encode(目标编码)


def 字符集转换为字符串(数据: bytes, 源编码: str, 目标编码: str) -> str:
    """字符集转换为字符串"""
    return 数据.decode(源编码).encode(目标编码).decode(目标编码)


def 检测编码(数据: bytes, 候选编码: list = None) -> str:
    """检测文本编码"""
    if 候选编码 is None:
        候选编码 = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'iso-8859-1']
    
    for 编码 in 候选编码:
        try:
            数据.decode(编码)
            return 编码
        except:
            continue
    
    return 'utf-8'


def HTML实体编码(文本: str) -> str:
    """HTML实体编码"""
    映射 = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }
    for 原始, 替换 in 映射.items():
        文本 = 文本.replace(原始, 替换)
    return 文本


def HTML实体解码(文本: str) -> str:
    """HTML实体解码"""
    映射 = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&nbsp;': ' '
    }
    for 原始, 替换 in 映射.items():
        文本 = 文本.replace(原始, 替换)
    return 文本


def Unicode转中文(文本: str) -> str:
    """Unicode转义转中文"""
    return 文本.encode('utf-8').decode('unicode_escape')


def 中文转Unicode(文本: str) -> str:
    """中文转Unicode转义"""
    return 文本.encode('unicode_escape').decode('utf-8')


def 字节转字符串(数据: bytes, 编码: str = 'utf-8') -> str:
    """字节转字符串"""
    return 数据.decode(编码)


def 字符串转字节(数据: str, 编码: str = 'utf-8') -> bytes:
    """字符串转字节"""
    return 数据.encode(编码)


def 文本转十六进制(文本: str, 编码: str = 'utf-8') -> str:
    """文本转十六进制"""
    return 文本.encode(编码).hex()


def 十六进制转文本(数据: str, 编码: str = 'utf-8') -> str:
    """十六进制转文本"""
    return bytes.fromhex(数据).decode(编码)


def 二进制转字符串(数据: bytes, 编码: str = 'utf-8') -> str:
    """二进制转字符串"""
    return 数据.decode(编码)


def 字符串转二进制(数据: str, 编码: str = 'utf-8') -> bytes:
    """字符串转二进制"""
    return 数据.encode(编码)


__all__ = [
    'Base64编码', 'Base64解码', 'Base64编码二进制', 'Base64解码二进制',
    'Base64URL编码', 'Base64URL解码',
    'Base32编码', 'Base32解码',
    'Base16编码', 'Base16解码',
    '十六进制编码', '十六进制解码', '十六进制编码大写',
    '二进制转十六进制', '十六进制转二进制',
    'URL编码', 'URL解码', 'URL编码全字符',
    'URL查询串编码', 'URL查询串解码',
    'Unicode转ASCII', 'ASCII转Unicode',
    'GBK转UTF8', 'UTF8转GBK',
    'GB2312转UTF8', 'UTF8转GB2312',
    'GB18030转UTF8', 'UTF8转GB18030',
    'BIG5转UTF8', 'UTF8转BIG5',
    'ISO8859_1转UTF8', 'UTF8转ISO8859_1',
    '字符集转换', '字符集转换为字符串', '检测编码',
    'HTML实体编码', 'HTML实体解码',
    'Unicode转中文', '中文转Unicode',
    '字节转字符串', '字符串转字节',
    '文本转十六进制', '十六进制转文本',
    '二进制转字符串', '字符串转二进制'
]