"""
光明标准库 - 美化输出模块

封装 pprint 模块，提供美观的数据结构输出功能。
"""

import pprint
import json
from typing import Any, Optional


def 美化输出(对象: Any, 缩进: int = 2, 宽度: int = 80, 深度: int = None, 紧凑: bool = False) -> str:
    """
    返回对象的美化字符串表示
    
    参数:
        对象: 要美化的对象
        缩进: 缩进空格数
        宽度: 最大宽度
        深度: 最大嵌套深度
        紧凑: 是否紧凑模式
    
    返回:
        美化后的字符串
    """
    printer = pprint.PrettyPrinter(
        indent=缩进,
        width=宽度,
        depth=深度,
        compact=紧凑,
    )
    return printer.pformat(对象)


def 打印(对象: Any, 缩进: int = 2, 宽度: int = 80, 深度: int = None, 紧凑: bool = False) -> None:
    """
    美化打印对象
    
    参数:
        对象: 要打印的对象
        缩进: 缩进空格数
        宽度: 最大宽度
        深度: 最大嵌套深度
        紧凑: 是否紧凑模式
    """
    printer = pprint.PrettyPrinter(
        indent=缩进,
        width=宽度,
        depth=深度,
        compact=紧凑,
    )
    printer.pprint(对象)


def 美化JSON(对象: Any, 缩进: int = 2, 确保ASCII: bool = False) -> str:
    """
    返回JSON格式的美化字符串
    
    参数:
        对象: 要美化的对象（需可JSON序列化）
        缩进: 缩进空格数
        确保ASCII: 是否确保ASCII
    
    返回:
        美化后的JSON字符串
    """
    return json.dumps(对象, indent=缩进, ensure_ascii=确保ASCII)


def 打印JSON(对象: Any, 缩进: int = 2, 确保ASCII: bool = False) -> None:
    """
    以JSON格式美化打印对象
    
    参数:
        对象: 要打印的对象
        缩进: 缩进空格数
        确保ASCII: 是否确保ASCII
    """
    print(美化JSON(对象, 缩进, 确保ASCII))


def 格式化表格(数据: list, 列标题: list = None) -> str:
    """
    将数据格式化为表格字符串
    
    参数:
        数据: 二维列表数据
        列标题: 列标题列表
    
    返回:
        表格字符串
    """
    if not 数据:
        return "(空表)"
    
    所有行 = list(数据)
    if 列标题:
        所有行 = [列标题] + 所有行
    
    # 计算每列最大宽度
    列数 = max(len(行) for 行 in 所有行)
    列宽 = [0] * 列数
    
    for 行 in 所有行:
        for i in range(列数):
            if i < len(行):
                宽度 = len(str(行[i]))
                if 宽度 > 列宽[i]:
                    列宽[i] = 宽度
    
    def 格式化行(行):
        单元格 = []
        for i in range(列数):
            值 = str(行[i]) if i < len(行) else ""
            单元格.append(值.ljust(列宽[i]))
        return " | ".join(单元格)
    
    行列表 = []
    if 列标题:
        行列表.append(格式化行(所有行[0]))
        分隔线 = "-+-".join("-" * w for w in 列宽)
        行列表.append(分隔线)
        for 行 in 所有行[1:]:
            行列表.append(格式化行(行))
    else:
        for 行 in 所有行:
            行列表.append(格式化行(行))
    
    return "\n".join(行列表)


def 打印表格(数据: list, 列标题: list = None) -> None:
    """打印表格"""
    print(格式化表格(数据, 列标题))


def 美化XML(xml字符串: str, 缩进: int = 2) -> str:
    """
    美化XML字符串
    
    参数:
        xml字符串: XML字符串
        缩进: 缩进空格数
    
    返回:
        美化后的XML字符串
    """
    try:
        import xml.dom.minidom
        dom = xml.dom.minidom.parseString(xml字符串)
        return dom.toprettyxml(indent=" " * 缩进)
    except:
        return xml字符串


__all__ = [
    '美化输出',
    '打印',
    '美化JSON',
    '打印JSON',
    '格式化表格',
    '打印表格',
    '美化XML',
]
