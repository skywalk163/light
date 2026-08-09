"""
光明标准库 - 表格输出模块

提供表格输出功能：打印表格、格式化行、设置表格样式等
"""

from typing import List

# 全局表格样式
_table_style = '简单'


def 设置表格样式(样式: str) -> None:
    """设置表格样式（'简单'、'网格'、'分隔线'）"""
    global _table_style
    if 样式 in ('简单', '网格', '分隔线'):
        _table_style = 样式


def 对齐方式(文本: str, 宽度: int, 方式: str) -> str:
    """对齐文本：左对齐、右对齐、居中对齐"""
    text = str(文本)
    length = len(text)
    if length >= 宽度:
        return text[:宽度]
    spaces = 宽度 - length
    if 方式 == '右':
        return ' ' * spaces + text
    elif 方式 == '中':
        left = spaces // 2
        right = spaces - left
        return ' ' * left + text + ' ' * right
    else:  # 默认左对齐
        return text + ' ' * spaces


def 格式化行(单元格列表: List[str], 宽度: List[int], 对齐: str = '左') -> str:
    """格式化一行"""
    cells = []
    for i, cell in enumerate(单元格列表):
        w = 宽度[i] if i < len(宽度) else len(cell)
        cells.append(对齐方式(cell, w, 对齐))
    return '│ ' + ' │ '.join(cells) + ' │'


def _计算列宽(表头: List[str], 行数据: List[List[str]]) -> List[int]:
    """自动计算列宽"""
    if not 表头:
        return []
    col_count = len(表头)
    widths = [len(str(h)) for h in 表头]
    for row in 行数据:
        for i, cell in enumerate(row):
            if i < col_count:
                widths[i] = max(widths[i], len(str(cell)))
    return widths


def _打印分隔线(宽度: List[int], 样式: str) -> None:
    """打印分隔线"""
    if 样式 == '简单':
        pass
    elif 样式 == '网格':
        corners = ['┌', '┬', '┐']
        h_lines = ['─' * (w + 2) for w in 宽度]
        print(' ' + corners[0] + h_lines[0] + ''.join(corners[1] + h for h in h_lines[1:]) + corners[2])
    else:  # 分隔线
        print('─' * (sum(宽度) + len(宽度) * 3 + 1))


def _打印表头(表头: List[str], 宽度: List[int]) -> None:
    """打印表头"""
    cells = []
    for i, h in enumerate(表头):
        cells.append(对齐方式(h, 宽度[i], '中'))
    print('│ ' + ' │ '.join(cells) + ' │')


def _打印数据行(行数据: List[List[str]], 宽度: List[int], 对齐: str) -> None:
    """打印数据行"""
    for row in 行数据:
        cells = [str(c) for c in row]
        print(格式化行(cells, 宽度, 对齐))


def 打印表格(表头: List[str], 行数据: List[List[str]], 对齐: str = '左') -> None:
    """打印表格"""
    if not 表头:
        return

    样式 = _table_style
    宽度 = _计算列宽(表头, 行数据)

    if 样式 == '网格':
        _打印分隔线(宽度, 样式)
    elif 样式 == '分隔线':
        _打印分隔线(宽度, 样式)

    _打印表头(表头, 宽度)

    if 样式 == '网格':
        _打印分隔线(宽度, 样式)
    elif 样式 == '分隔线':
        print('├' + '┼'.join('─' * (w + 2) for w in 宽度) + '┤')

    _打印数据行(行数据, 宽度, 对齐)

    if 样式 == '网格':
        _打印分隔线(宽度, 样式)
    elif 样式 == '分隔线':
        _打印分隔线(宽度, 样式)
