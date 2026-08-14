"""
段言标准库 - 中文编码转换工具模块

提供中文编码的检测、转换功能，支持 GBK、UTF-8、Unicode 转义等。

类：
    ChineseEncoding: 中文编码转换工具

用法:
    encoder = ChineseEncoding()
    encoding = encoder.detect_encoding(data)
    result = encoder.convert_encoding(data, "gbk", "utf-8")
    is_gbk = encoder.is_gbk(data)
    is_utf8 = encoder.is_utf8(data)
    utf8_text = encoder.gbk_to_utf8(data)
    gbk_data = encoder.utf8_to_gbk("你好")
    escaped = encoder.unicode_escape("你好")
    unescaped = encoder.unicode_unescape("\\u4f60\\u597d")
"""

import re
from typing import Optional


# =============================================================================
# 编码检测常量
# =============================================================================

# UTF-8 编码的字节模式
_UTF8_BYTE_PATTERNS = [
    # 单字节（0xxxxxxx）
    re.compile(r'^[\x00-\x7F]+$'),
    # 双字节（110xxxxx 10xxxxxx）
    re.compile(r'^[\xC0-\xDF][\x80-\xBF]+$'),
    # 三字节（1110xxxx 10xxxxxx 10xxxxxx）
    re.compile(r'^[\xE0-\xEF][\x80-\xBF]{2,}$'),
    # 四字节（11110xxx 10xxxxxx 10xxxxxx 10xxxxxx）
    re.compile(r'^[\xF0-\xF7][\x80-\xBF]{3,}$'),
]

# Unicode 转义序列正则
_UNICODE_ESCAPE_PATTERN = re.compile(r'\\u([0-9a-fA-F]{4})')

# 常见编码名称
_ENCODING_NAMES = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'ascii']


class ChineseEncoding:
    """中文编码转换工具

    提供 GBK、UTF-8、Unicode 等编码的检测、转换功能。
    支持编码自动检测、编码互转、Unicode 转义与反转义。

    用法:
        encoder = ChineseEncoding()
        encoding = encoder.detect_encoding(b"\\xe4\\xbd\\xa0\\xe5\\xa5\\xbd")
        utf8_text = encoder.gbk_to_utf8(gbk_data)
        escaped = encoder.unicode_escape("你好")
    """

    def detect_encoding(self, data: bytes) -> str:
        """检测字节数据的编码

        通过尝试解码来判断编码类型，依次尝试 UTF-8、GBK、GB2312、
        GB18030、Big5 等常见编码。

        Args:
            data: 待检测的字节数据

        Returns:
            编码名称（如 "utf-8"、"gbk"），无法识别返回 "unknown"
        """
        if not data:
            return "unknown"

        # 先尝试 UTF-8
        try:
            data.decode('utf-8')
            return 'utf-8'
        except (UnicodeDecodeError, LookupError):
            pass

        # 尝试 GBK
        try:
            data.decode('gbk')
            return 'gbk'
        except (UnicodeDecodeError, LookupError):
            pass

        # 尝试 GB2312
        try:
            data.decode('gb2312')
            return 'gb2312'
        except (UnicodeDecodeError, LookupError):
            pass

        # 尝试 GB18030
        try:
            data.decode('gb18030')
            return 'gb18030'
        except (UnicodeDecodeError, LookupError):
            pass

        # 尝试 Big5
        try:
            data.decode('big5')
            return 'big5'
        except (UnicodeDecodeError, LookupError):
            pass

        # 尝试 ASCII
        try:
            data.decode('ascii')
            return 'ascii'
        except (UnicodeDecodeError, LookupError):
            pass

        return "unknown"

    def convert_encoding(self, data: bytes, from_enc: str, to_enc: str) -> bytes:
        """编码转换

        将字节数据从源编码转换为目标编码。

        Args:
            data: 待转换的字节数据
            from_enc: 源编码名称
            to_enc: 目标编码名称

        Returns:
            转换后的字节数据

        Raises:
            ValueError: 编码转换失败时抛出
            UnicodeDecodeError: 源编码解码失败时抛出
            UnicodeEncodeError: 目标编码编码失败时抛出
        """
        if not data:
            return b""

        if from_enc.lower() == to_enc.lower():
            return data

        # 先解码为 Unicode 字符串
        text = data.decode(from_enc)

        # 再编码为目标编码
        return text.encode(to_enc)

    def is_gbk(self, data: bytes) -> bool:
        """判断字节数据是否为 GBK 编码

        Args:
            data: 待检测的字节数据

        Returns:
            True 如果数据是有效的 GBK 编码
        """
        if not data:
            return False

        try:
            data.decode('gbk')
            # 确保不是 UTF-8（GBK 通常能解码 UTF-8 数据，但反过来不成立）
            try:
                data.decode('utf-8')
                return False
            except UnicodeDecodeError:
                return True
        except (UnicodeDecodeError, LookupError):
            return False

    def is_utf8(self, data: bytes) -> bool:
        """判断字节数据是否为 UTF-8 编码

        Args:
            data: 待检测的字节数据

        Returns:
            True 如果数据是有效的 UTF-8 编码
        """
        if not data:
            return False

        try:
            data.decode('utf-8')
            return True
        except (UnicodeDecodeError, LookupError):
            return False

    def gbk_to_utf8(self, data: bytes) -> str:
        """GBK 编码转 UTF-8 字符串

        Args:
            data: GBK 编码的字节数据

        Returns:
            UTF-8 编码的字符串

        Raises:
            ValueError: 数据不是有效的 GBK 编码时抛出
        """
        if not data:
            return ""

        try:
            return data.decode('gbk')
        except UnicodeDecodeError as e:
            raise ValueError(f"GBK 解码失败: {e}")

    def utf8_to_gbk(self, text: str) -> bytes:
        """UTF-8 字符串转 GBK 编码

        Args:
            text: UTF-8 字符串

        Returns:
            GBK 编码的字节数据

        Raises:
            ValueError: 字符串包含 GBK 无法编码的字符时抛出
        """
        if not text:
            return b""

        try:
            return text.encode('gbk')
        except UnicodeEncodeError as e:
            raise ValueError(f"GBK 编码失败: {e}")

    def unicode_escape(self, text: str) -> str:
        """Unicode 转义

        将字符串中的非 ASCII 字符转义为 \\uXXXX 格式。

        Args:
            text: 输入字符串

        Returns:
            转义后的字符串
        """
        if not text:
            return ""

        result = []
        for char in text:
            code = ord(char)
            if code > 0x7F:
                result.append(f'\\u{code:04X}')
            else:
                result.append(char)

        return ''.join(result)

    def unicode_unescape(self, text: str) -> str:
        """Unicode 反转义

        将 \\uXXXX 格式的转义序列还原为原始字符。

        Args:
            text: 包含 Unicode 转义序列的字符串

        Returns:
            还原后的字符串
        """
        if not text:
            return ""

        def _replace_match(match: re.Match) -> str:
            """替换匹配的 Unicode 转义序列"""
            hex_str = match.group(1)
            code_point = int(hex_str, 16)
            return chr(code_point)

        return _UNICODE_ESCAPE_PATTERN.sub(_replace_match, text)


# =============================================================================
# 便捷函数
# =============================================================================

_default_encoder = ChineseEncoding()


def 检测编码(data: bytes) -> str:
    """检测字节数据的编码

    Args:
        data: 字节数据

    Returns:
        编码名称
    """
    return _default_encoder.detect_encoding(data)


def 编码转换(data: bytes, from_enc: str, to_enc: str) -> bytes:
    """编码转换

    Args:
        data: 字节数据
        from_enc: 源编码
        to_enc: 目标编码

    Returns:
        转换后的字节数据
    """
    return _default_encoder.convert_encoding(data, from_enc, to_enc)


def 判断GBK(data: bytes) -> bool:
    """判断是否为 GBK 编码

    Args:
        data: 字节数据

    Returns:
        True 如果是 GBK 编码
    """
    return _default_encoder.is_gbk(data)


def 判断UTF8(data: bytes) -> bool:
    """判断是否为 UTF-8 编码

    Args:
        data: 字节数据

    Returns:
        True 如果是 UTF-8 编码
    """
    return _default_encoder.is_utf8(data)


def GBK转UTF8(data: bytes) -> str:
    """GBK 转 UTF-8

    Args:
        data: GBK 编码的字节数据

    Returns:
        UTF-8 字符串
    """
    return _default_encoder.gbk_to_utf8(data)


def UTF8转GBK(text: str) -> bytes:
    """UTF-8 转 GBK

    Args:
        text: UTF-8 字符串

    Returns:
        GBK 编码的字节数据
    """
    return _default_encoder.utf8_to_gbk(text)


def Unicode转义(text: str) -> str:
    """Unicode 转义

    Args:
        text: 输入字符串

    Returns:
        转义后的字符串
    """
    return _default_encoder.unicode_escape(text)


def Unicode反转义(text: str) -> str:
    """Unicode 反转义

    Args:
        text: 包含转义序列的字符串

    Returns:
        还原后的字符串
    """
    return _default_encoder.unicode_unescape(text)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'ChineseEncoding',
    '检测编码',
    '编码转换',
    '判断GBK',
    '判断UTF8',
    'GBK转UTF8',
    'UTF8转GBK',
    'Unicode转义',
    'Unicode反转义',
]