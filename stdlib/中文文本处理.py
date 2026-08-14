"""
段言标准库 - 中文文本处理增强模块

提供增强的中文文本处理功能，包括字符统计、提取、标点清理、
简繁占位转换、分句分段、词频统计等。

类：
    ChineseTextProcessor: 中文文本处理器

用法:
    processor = ChineseTextProcessor()
    count = processor.count_chinese_chars("Hello 你好世界！")
    chinese = processor.extract_chinese("Hello 你好世界！")
    pure = processor.remove_punctuation("你好，世界！")
    is_all = processor.is_all_chinese("你好世界")
    has = processor.contains_chinese("Hello 你好")
    simplified = processor.to_simplified("繁體字")
    traditional = processor.to_traditional("简体字")
    sentences = processor.split_sentences("你好。世界！")
    paras = processor.split_paragraphs("你好。\\n\\n世界。")
    freq = processor.count_words("你好世界你好")
"""

import re
from typing import Dict, List, Optional


# =============================================================================
# 中文 Unicode 范围
# =============================================================================

# 常用中文字符（CJK 统一表意文字）
_CJK_UNIFIED_IDEOGRAPHS = range(0x4E00, 0x9FFF + 1)
_CJK_EXTENSION_A = range(0x3400, 0x4DBF + 1)
_CJK_EXTENSION_B = range(0x20000, 0x2A6DF + 1)
_CJK_COMPATIBILITY = range(0xF900, 0xFAFF + 1)

# 中文标点符号
_CHINESE_PUNCTUATION = set(
    "，。、；：？！…—·～〃「」『』【】《》（）〔〕"
    "﹁﹂﹃﹄﹝﹞＂＇｀｜＠＃＄％＾＆＊＋＝｛｝［］＼｜；：＂＇"
    "，。、；：？！…—·～〃"
)

# 中文分句正则
_SENTENCE_SPLIT_PATTERN = re.compile(r'[。！？\n]+')

# 中文分段正则
_PARAGRAPH_SPLIT_PATTERN = re.compile(r'\n\s*\n')


class ChineseTextProcessor:
    """中文文本处理器

    提供中文字符的统计、提取、清理、简繁转换（占位）、分句、
    分段、词频统计等增强功能。

    用法:
        processor = ChineseTextProcessor()
        count = processor.count_chinese_chars("Hello 你好世界！")
        chinese = processor.extract_chinese("Hello 你好世界！")
        freq = processor.count_words("你好世界你好")
    """

    @staticmethod
    def _is_chinese_char(char: str) -> bool:
        """判断单个字符是否为中文字符

        Args:
            char: 单个字符

        Returns:
            True 如果该字符是中文字符
        """
        if len(char) != 1:
            return False
        code = ord(char)
        return (
            code in _CJK_UNIFIED_IDEOGRAPHS
            or code in _CJK_EXTENSION_A
            or code in _CJK_EXTENSION_B
            or code in _CJK_COMPATIBILITY
        )

    def count_chinese_chars(self, text: str) -> int:
        """统计文本中的中文字符数

        遍历文本，统计属于 CJK 统一表意文字范围的中文字符数量。

        Args:
            text: 输入文本

        Returns:
            中文字符的数量
        """
        if not text:
            return 0
        return sum(1 for char in text if self._is_chinese_char(char))

    def extract_chinese(self, text: str) -> str:
        """提取文本中的中文字符

        过滤掉所有非中文字符（保留英文、数字、标点等），
        只返回中文字符序列。

        Args:
            text: 输入文本

        Returns:
            仅包含中文字符的字符串
        """
        if not text:
            return ""
        return "".join(char for char in text if self._is_chinese_char(char))

    def remove_punctuation(self, text: str) -> str:
        """去除文本中的中文标点符号

        移除所有中文标点符号（如，。、；：？！等），
        保留中文字符、英文、数字和其他字符。

        Args:
            text: 输入文本

        Returns:
            去除中文标点后的文本
        """
        if not text:
            return ""
        return "".join(
            char for char in text
            if char not in _CHINESE_PUNCTUATION
        )

    def is_all_chinese(self, text: str) -> bool:
        """判断文本是否全部为中文字符

        Args:
            text: 输入文本

        Returns:
            True 如果文本全部由中文字符组成
        """
        if not text:
            return False
        return all(self._is_chinese_char(char) for char in text)

    def contains_chinese(self, text: str) -> bool:
        """判断文本是否包含中文字符

        Args:
            text: 输入文本

        Returns:
            True 如果文本中包含至少一个中文字符
        """
        if not text:
            return False
        return any(self._is_chinese_char(char) for char in text)

    def to_simplified(self, text: str) -> str:
        """简体转换（占位实现）

        当前返回原文本。后续可接入 OpenCC 等繁简转换库。

        Args:
            text: 输入文本

        Returns:
            原文本（占位）
        """
        return text

    def to_traditional(self, text: str) -> str:
        """繁体转换（占位实现）

        当前返回原文本。后续可接入 OpenCC 等繁简转换库。

        Args:
            text: 输入文本

        Returns:
            原文本（占位）
        """
        return text

    def split_sentences(self, text: str) -> List[str]:
        """中文分句

        根据中文句号、感叹号、问号、换行符等句子结束符进行分句。
        会过滤掉空字符串。

        Args:
            text: 输入文本

        Returns:
            句子列表
        """
        if not text:
            return []
        sentences = _SENTENCE_SPLIT_PATTERN.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def split_paragraphs(self, text: str) -> List[str]:
        """中文分段

        根据连续换行符（至少两个换行）进行段落分割。
        会过滤掉空字符串。

        Args:
            text: 输入文本

        Returns:
            段落列表
        """
        if not text:
            return []
        paragraphs = _PARAGRAPH_SPLIT_PATTERN.split(text)
        return [p.strip() for p in paragraphs if p.strip()]

    def count_words(self, text: str) -> Dict[str, int]:
        """中文词频统计

        以单字为单位统计中文字符的出现频率。
        注意：此方法按单字统计，如需分词统计请使用中文分词模块。

        Args:
            text: 输入文本

        Returns:
            词频字典 {字符: 出现次数}
        """
        if not text:
            return {}
        freq: Dict[str, int] = {}
        for char in text:
            if self._is_chinese_char(char):
                freq[char] = freq.get(char, 0) + 1
        # 按频率降序排列
        return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))


# =============================================================================
# 便捷函数
# =============================================================================

_default_processor = ChineseTextProcessor()


def 统计中文字符(text: str) -> int:
    """统计中文字符数

    Args:
        text: 输入文本

    Returns:
        中文字符数量
    """
    return _default_processor.count_chinese_chars(text)


def 提取中文(text: str) -> str:
    """提取文本中的中文字符

    Args:
        text: 输入文本

    Returns:
        中文字符序列
    """
    return _default_processor.extract_chinese(text)


def 去除标点(text: str) -> str:
    """去除中文标点符号

    Args:
        text: 输入文本

    Returns:
        去除标点后的文本
    """
    return _default_processor.remove_punctuation(text)


def 判断全中文(text: str) -> bool:
    """判断是否全为中文

    Args:
        text: 输入文本

    Returns:
        True 如果全为中文
    """
    return _default_processor.is_all_chinese(text)


def 判断含中文(text: str) -> bool:
    """判断是否包含中文

    Args:
        text: 输入文本

    Returns:
        True 如果包含中文
    """
    return _default_processor.contains_chinese(text)


def 中文分句(text: str) -> List[str]:
    """中文分句

    Args:
        text: 输入文本

    Returns:
        句子列表
    """
    return _default_processor.split_sentences(text)


def 中文分段(text: str) -> List[str]:
    """中文分段

    Args:
        text: 输入文本

    Returns:
        段落列表
    """
    return _default_processor.split_paragraphs(text)


def 中文词频(text: str) -> Dict[str, int]:
    """中文词频统计

    Args:
        text: 输入文本

    Returns:
        词频字典
    """
    return _default_processor.count_words(text)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'ChineseTextProcessor',
    '统计中文字符',
    '提取中文',
    '去除标点',
    '判断全中文',
    '判断含中文',
    '中文分句',
    '中文分段',
    '中文词频',
]