"""
段言标准库 - 中文数字转换模块

提供中文数字与阿拉伯数字的互转功能，包括整数、浮点数和大写金额转换。

类：
    ChineseNumberConverter: 中文数字转换器

用法:
    converter = ChineseNumberConverter()
    num = converter.chinese_to_arabic("一百二十三")
    cn = converter.arabic_to_chinese(123)
    f = converter.chinese_to_arabic_float("三点一四")
    currency = converter.arabic_to_chinese_currency(123.45)
"""

import re
from typing import List


# =============================================================================
# 中文数字常量
# =============================================================================

# 中文数字到阿拉伯数字的映射
_CHINESE_DIGITS = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '两': 2,
}

# 阿拉伯数字到中文数字的映射
_ARABIC_TO_CHINESE = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']

# 中文单位
_CHINESE_UNITS = {
    '十': 10,
    '百': 100,
    '千': 1000,
    '万': 10000,
}

# 中文大写金额数字
_CHINESE_UPPER_DIGITS = {
    '零': 0, '壹': 1, '贰': 2, '叁': 3, '肆': 4,
    '伍': 5, '陆': 6, '柒': 7, '捌': 8, '玖': 9,
}

# 阿拉伯数字到中文大写金额数字的映射
_ARABIC_TO_UPPER = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']

# 中文大写金额单位
_CHINESE_UPPER_UNITS = ['拾', '佰', '仟', '万', '亿']

# 金额单位
_CURRENCY_UNITS = ['圆', '角', '分', '整']

# 中文数字正则（用于检测）
_CHINESE_NUM_PATTERN = re.compile(r'^[零一二三四五六七八九十百千万两]+$')
_CHINESE_FLOAT_PATTERN = re.compile(r'^[零一二三四五六七八九十百千万两]+点[零一二三四五六七八九]+$')


class ChineseNumberConverter:
    """中文数字转换器

    支持中文数字与阿拉伯数字的互转，包括：
    - 整数转换（0-9999 万以内）
    - 浮点数转换
    - 中文大写金额转换

    用法:
        converter = ChineseNumberConverter()
        num = converter.chinese_to_arabic("一百二十三")
        cn = converter.arabic_to_chinese(123)
        f = converter.chinese_to_arabic_float("三点一四")
        currency = converter.arabic_to_chinese_currency(123.45)
    """

    def chinese_to_arabic(self, chinese_num: str) -> int:
        """中文数字转阿拉伯数字

        支持 0-9999 万以内的中文数字转换。
        如 "一百二十三" → 123

        Args:
            chinese_num: 中文数字字符串

        Returns:
            转换后的阿拉伯数字

        Raises:
            ValueError: 输入格式无效时抛出
        """
        if not chinese_num:
            raise ValueError("输入不能为空")

        chinese_num = chinese_num.strip()

        # 处理单个数字
        if chinese_num in _CHINESE_DIGITS:
            return _CHINESE_DIGITS[chinese_num]

        # 处理"零"开头的情况
        if chinese_num.startswith('零'):
            chinese_num = chinese_num[1:]

        result = 0
        current = 0
        last_unit = 1

        # 处理"十"开头的特殊情况（如"十二"表示12）
        if chinese_num.startswith('十'):
            result = 10
            chinese_num = chinese_num[1:]
            if not chinese_num:
                return result

        for i, char in enumerate(chinese_num):
            if char in _CHINESE_DIGITS:
                current = _CHINESE_DIGITS[char]
            elif char in _CHINESE_UNITS:
                unit = _CHINESE_UNITS[char]
                if current == 0:
                    current = 1
                if unit >= 10000:
                    # 万（及以上）进位
                    result = (result + current) * unit
                    current = 0
                else:
                    if unit > last_unit:
                        # 遇到更大的单位，把之前的加起来
                        result = (result + current) * unit
                        current = 0
                    else:
                        result += current * unit
                        current = 0
                    last_unit = unit
            else:
                raise ValueError(f"无效的中文数字字符: '{char}'")

        result += current
        return result

    def arabic_to_chinese(self, num: int) -> str:
        """阿拉伯数字转中文数字

        支持 0-9999 万以内的数字转换。
        如 123 → "一百二十三"

        Args:
            num: 阿拉伯数字

        Returns:
            中文数字字符串

        Raises:
            ValueError: 数字超出支持范围时抛出
        """
        if not isinstance(num, int):
            raise ValueError("输入必须是整数")

        if num < 0:
            raise ValueError(f"不支持负数转换: {num}")
        if num > 99999999:
            raise ValueError(f"数字超出支持范围（最大 99999999）: {num}")

        if num == 0:
            return "零"

        # 按万、千、百、十、个位转换
        units = ['', '十', '百', '千']
        big_units = ['', '万']

        result_parts: List[str] = []
        is_zero = False

        # 处理万以上部分
        wan_part = num // 10000
        if wan_part > 0:
            result_parts.append(self._convert_under_10000(wan_part))
            result_parts.append('万')
            num = num % 10000
            if num < 1000 and num > 0:
                result_parts.append('零')

        # 处理万以下部分
        if num > 0:
            result_parts.append(self._convert_under_10000(num))
        elif wan_part > 0:
            pass  # 整万数

        return ''.join(result_parts)

    def _convert_under_10000(self, num: int) -> str:
        """转换 0-9999 的数字为中文数字

        Args:
            num: 0-9999 的整数

        Returns:
            中文数字字符串
        """
        if num == 0:
            return "零"
        if num < 10:
            return _ARABIC_TO_CHINESE[num]

        units = ['', '十', '百', '千']
        digits = []
        i = 0
        has_zero = False

        while num > 0:
            digit = num % 10
            if digit == 0:
                if not has_zero and i > 0:
                    digits.insert(0, '零')
                    has_zero = True
            else:
                has_zero = False
                part = _ARABIC_TO_CHINESE[digit]
                if i > 0:
                    part += units[i]
                digits.insert(0, part)
            num //= 10
            i += 1

        return ''.join(digits)

    def chinese_to_arabic_float(self, chinese_num: str) -> float:
        """中文数字转浮点数

        支持带小数点的中文数字转换。
        如 "三点一四" → 3.14

        Args:
            chinese_num: 中文数字字符串（含"点"）

        Returns:
            转换后的浮点数

        Raises:
            ValueError: 输入格式无效时抛出
        """
        if not chinese_num:
            raise ValueError("输入不能为空")

        chinese_num = chinese_num.strip()

        if '点' not in chinese_num:
            # 没有小数点，当作整数处理
            return float(self.chinese_to_arabic(chinese_num))

        parts = chinese_num.split('点')
        if len(parts) != 2:
            raise ValueError(f"无效的中文数字格式: {chinese_num}")

        integer_part_str, decimal_part_str = parts

        # 转换整数部分
        if integer_part_str:
            integer_part = self.chinese_to_arabic(integer_part_str)
        else:
            integer_part = 0

        # 转换小数部分
        decimal_part = 0.0
        for i, char in enumerate(decimal_part_str):
            if char in _CHINESE_DIGITS:
                decimal_part += _CHINESE_DIGITS[char] * (10 ** -(i + 1))
            else:
                raise ValueError(f"无效的中文数字字符: '{char}'")

        return integer_part + decimal_part

    def arabic_to_chinese_currency(self, num: float) -> str:
        """数字转中文大写金额

        支持最大 9999 万以内的金额转换。
        如 123.45 → "壹佰贰拾叁圆肆角伍分"

        Args:
            num: 金额数字

        Returns:
            中文大写金额字符串

        Raises:
            ValueError: 数字超出支持范围时抛出
        """
        if num < 0:
            raise ValueError(f"不支持负数金额: {num}")
        if num > 99999999.99:
            raise ValueError(f"金额超出支持范围（最大 99999999.99）: {num}")

        # 四舍五入到分
        num = round(num, 2)

        # 分离整数部分和小数部分
        integer_part = int(num)
        decimal_part = round(num - integer_part, 2)

        if integer_part == 0 and decimal_part == 0:
            return "零圆整"

        result_parts: List[str] = []

        # 转换整数部分
        if integer_part > 0:
            chinese_int = self.arabic_to_chinese(integer_part)
            # 把中文数字转为大写
            for char in chinese_int:
                if char in _ARABIC_TO_CHINESE:
                    idx = _ARABIC_TO_CHINESE.index(char)
                    result_parts.append(_ARABIC_TO_UPPER[idx])
                elif char == '十':
                    result_parts.append('拾')
                elif char == '百':
                    result_parts.append('佰')
                elif char == '千':
                    result_parts.append('仟')
                elif char == '万':
                    result_parts.append('万')
                elif char == '零':
                    result_parts.append('零')
                else:
                    result_parts.append(char)
            result_parts.append('圆')
        else:
            result_parts.append('零圆')

        # 转换小数部分
        if decimal_part == 0:
            result_parts.append('整')
        else:
            jiao = int(decimal_part * 10) % 10
            fen = int(round(decimal_part * 100)) % 10

            if jiao > 0:
                result_parts.append(_ARABIC_TO_UPPER[jiao])
                result_parts.append('角')
            elif integer_part > 0:
                result_parts.append('零')

            if fen > 0:
                result_parts.append(_ARABIC_TO_UPPER[fen])
                result_parts.append('分')

        return ''.join(result_parts)


# =============================================================================
# 便捷函数
# =============================================================================

_default_converter = ChineseNumberConverter()


def 中文转阿拉伯数字(chinese_num: str) -> int:
    """中文数字转阿拉伯数字

    Args:
        chinese_num: 中文数字字符串

    Returns:
        阿拉伯数字
    """
    return _default_converter.chinese_to_arabic(chinese_num)


def 阿拉伯数字转中文(num: int) -> str:
    """阿拉伯数字转中文数字

    Args:
        num: 阿拉伯数字

    Returns:
        中文数字字符串
    """
    return _default_converter.arabic_to_chinese(num)


def 中文转浮点数(chinese_num: str) -> float:
    """中文数字转浮点数

    Args:
        chinese_num: 中文数字字符串（含"点"）

    Returns:
        浮点数
    """
    return _default_converter.chinese_to_arabic_float(chinese_num)


def 数字转大写金额(num: float) -> str:
    """数字转中文大写金额

    Args:
        num: 金额数字

    Returns:
        中文大写金额字符串
    """
    return _default_converter.arabic_to_chinese_currency(num)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'ChineseNumberConverter',
    '中文转阿拉伯数字',
    '阿拉伯数字转中文',
    '中文转浮点数',
    '数字转大写金额',
]