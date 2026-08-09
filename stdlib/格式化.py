# -*- coding: utf-8 -*-
"""
光明标准库 - 文本格式化模块

提供文本对齐、填充、缩进等格式化功能。
"""

from typing import List, Optional, Union


def 文本居中(文本: str, 宽度: int, 填充字符: str = ' ') -> str:
    """
    文本居中对齐

    参数:
        文本: 要居中的文本
        宽度: 目标宽度
        填充字符: 填充字符（默认空格）

    返回:
        居中对齐后的文本

    示例:
        文本居中('hello', 11)  # '   hello   '
    """
    if 宽度 <= len(文本):
        return 文本
    left_pad = (宽度 - len(文本)) // 2
    right_pad = 宽度 - len(文本) - left_pad
    return 填充字符 * left_pad + 文本 + 填充字符 * right_pad


def 文本左对齐(文本: str, 宽度: int, 填充字符: str = ' ') -> str:
    """
    文本左对齐

    参数:
        文本: 要左对齐的文本
        宽度: 目标宽度
        填充字符: 填充字符（默认空格）

    返回:
        左对齐后的文本
    """
    if 宽度 <= len(文本):
        return 文本
    return 文本 + 填充字符 * (宽度 - len(文本))


def 文本右对齐(文本: str, 宽度: int, 填充字符: str = ' ') -> str:
    """
    文本右对齐

    参数:
        文本: 要右对齐的文本
        宽度: 目标宽度
        填充字符: 填充字符（默认空格）

    返回:
        右对齐后的文本
    """
    if 宽度 <= len(文本):
        return 文本
    return 填充字符 * (宽度 - len(文本)) + 文本


def 文本填充(文本: str, 宽度: int, 填充字符: str = ' ', 对齐方式: str = '左') -> str:
    """
    文本填充到指定宽度

    参数:
        文本: 要填充的文本
        宽度: 目标宽度
        填充字符: 填充字符（默认空格）
        对齐方式: '左', '右', '居中'

    返回:
        填充后的文本
    """
    if 对齐方式 == '左':
        return 文本左对齐(文本, 宽度, 填充字符)
    elif 对齐方式 == '右':
        return 文本右对齐(文本, 宽度, 填充字符)
    elif 对齐方式 == '居中':
        return 文本居中(文本, 宽度, 填充字符)
    else:
        raise ValueError(f"不支持的对齐方式: '{对齐方式}'")


def 文本缩进(文本: str, 缩进空格数: int = 4, 缩进字符: str = ' ') -> str:
    """
    为文本添加缩进

    参数:
        文本: 要缩进的文本
        缩进空格数: 缩进空格数（默认4）
        缩进字符: 缩进字符（默认空格）

    返回:
        缩进后的文本

    示例:
        文本缩进('hello', 4)  # '    hello'
    """
    缩进前缀 = 缩进字符 * 缩进空格数
    return '\n'.join(缩进前缀 + 行 for 行 in 文本.split('\n'))


def 文本去除缩进(文本: str) -> str:
    """
    去除文本的公共缩进（类似 Python 的 textwrap.dedent）

    参数:
        文本: 要去除缩进的文本

    返回:
        去除公共缩进后的文本
    """
    import textwrap
    return textwrap.dedent(文本)


def 文本换行(文本: str, 宽度: int = 80) -> List[str]:
    """
    将文本按指定宽度换行

    参数:
        文本: 要换行的文本
        宽度: 每行最大宽度（默认80）

    返回:
        换行后的行列表

    示例:
        文本换行('hello world', 5)  # ['hello', 'world']
    """
    import textwrap
    return textwrap.wrap(文本, width=宽度)


def 文本填充段落(文本: str, 宽度: int = 80) -> str:
    """
    将文本填充为指定宽度的段落

    参数:
        文本: 要填充的文本
        宽度: 每行最大宽度（默认80）

    返回:
        填充后的文本
    """
    import textwrap
    return textwrap.fill(文本, width=宽度)


def 文本截断(文本: str, 最大长度: int, 省略号: str = '...') -> str:
    """
    截断文本到指定长度

    参数:
        文本: 要截断的文本
        最大长度: 最大长度（包含省略号）
        省略号: 省略号字符（默认 '...'）

    返回:
        截断后的文本

    示例:
        文本截断('hello world', 8)  # 'hello...'
    """
    if len(文本) <= 最大长度:
        return 文本
    return 文本[:最大长度 - len(省略号)] + 省略号


def 文本去除空白(文本: str) -> str:
    """
    去除文本中多余的空白字符

    参数:
        文本: 要处理的文本

    返回:
        处理后的文本
    """
    import re
    return re.sub(r'\s+', ' ', 文本).strip()


def 文本填充零(数字: Union[int, str], 总长度: int) -> str:
    """
    用零填充数字

    参数:
        数字: 要填充的数字
        总长度: 填充后的总长度

    返回:
        补零后的字符串

    示例:
        文本填充零(42, 5)  # '00042'
    """
    return str(数字).zfill(总长度)


def 文本分隔线(字符: str = '-', 长度: int = 50) -> str:
    """
    创建分隔线

    参数:
        字符: 分隔线字符（默认 '-')
        长度: 分隔线长度（默认50）

    返回:
        分隔线字符串
    """
    return 字符 * 长度


def 文本表格(数据: List[List[str]], 表头: List[str] = None, 分隔符: str = ' | ') -> str:
    """
    创建简单的文本表格

    参数:
        数据: 表格数据（二维列表）
        表头: 表头列表
        分隔符: 列分隔符（默认 ' | '）

    返回:
        表格字符串
    """
    if not 数据:
        return ''

    # 计算每列宽度
    if 表头:
        列宽 = [len(h) for h in 表头]
    else:
        列宽 = [0] * len(数据[0])

    for 行 in 数据:
        for i, 单元格 in enumerate(行):
            if i < len(列宽):
                列宽[i] = max(列宽[i], len(str(单元格)))

    行列表 = []
    if 表头:
        表头行 = 分隔符.join(文本左对齐(str(h), 列宽[i]) for i, h in enumerate(表头))
        行列表.append(表头行)
        行列表.append(分隔符.join('-' * 列宽[i] for i in range(len(列宽))))

    for 行 in 数据:
        行列表.append(分隔符.join(
            文本左对齐(str(行[i]), 列宽[i]) if i < len(列宽) else str(行[i])
            for i in range(len(行))
        ))

    return '\n'.join(行列表)


__all__ = [
    '文本居中', '文本左对齐', '文本右对齐', '文本填充',
    '文本缩进', '文本去除缩进',
    '文本换行', '文本填充段落', '文本截断',
    '文本去除空白', '文本填充零',
    '文本分隔线', '文本表格',
]