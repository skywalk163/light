# -*- coding: utf-8 -*-
"""
光明标准库 - CSV 读写模块

基于现有 CSV读写器 扩展，添加流式读写功能。
提供 CSV 文件的读取、写入、转换和流式处理。
"""

import csv
import io
import os
from typing import List, Dict, Any, Optional, Iterator


def CSV读取(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> List[Dict[str, Any]]:
    """
    读取 CSV 文件为字典列表

    参数:
        文件路径: CSV 文件路径
        编码: 文件编码（默认 utf-8）
        分隔符: 列分隔符（默认 ,）

    返回:
        字典列表
    """
    with open(文件路径, 'r', encoding=编码, newline='') as f:
        reader = csv.DictReader(f, delimiter=分隔符)
        return list(reader)


def CSV读取列表(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> List[List[str]]:
    """
    读取 CSV 文件为列表列表

    参数:
        文件路径: CSV 文件路径
        编码: 文件编码（默认 utf-8）
        分隔符: 列分隔符（默认 ,）

    返回:
        列表列表
    """
    with open(文件路径, 'r', encoding=编码, newline='') as f:
        reader = csv.reader(f, delimiter=分隔符)
        return list(reader)


def CSV写入(文件路径: str, 数据: List[Dict[str, Any]], 编码: str = 'utf-8', 分隔符: str = ','):
    """
    写入 CSV 文件（字典列表）

    参数:
        文件路径: 输出文件路径
        数据: 字典列表
        编码: 文件编码（默认 utf-8）
        分隔符: 列分隔符（默认 ,）
    """
    if not 数据:
        return
    with open(文件路径, 'w', encoding=编码, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(数据[0].keys()), delimiter=分隔符)
        writer.writeheader()
        writer.writerows(数据)


def CSV写入列表(文件路径: str, 数据: List[List[str]], 编码: str = 'utf-8', 分隔符: str = ','):
    """
    写入 CSV 文件（列表列表）

    参数:
        文件路径: 输出文件路径
        数据: 列表列表
        编码: 文件编码（默认 utf-8）
        分隔符: 列分隔符（默认 ,）
    """
    with open(文件路径, 'w', encoding=编码, newline='') as f:
        writer = csv.writer(f, delimiter=分隔符)
        writer.writerows(数据)


def CSV流式读取(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> Iterator[Dict[str, Any]]:
    """
    流式读取 CSV 文件（逐行读取，节省内存）

    参数:
        文件路径: CSV 文件路径
        编码: 文件编码（默认 utf-8）
        分隔符: 列分隔符（默认 ,）

    返回:
        字典迭代器

    示例:
        for 行 in CSV流式读取('large.csv'):
            处理(行)
    """
    with open(文件路径, 'r', encoding=编码, newline='') as f:
        reader = csv.DictReader(f, delimiter=分隔符)
        for row in reader:
            yield row


def CSV流式写入(文件路径: str, 表头: List[str], 编码: str = 'utf-8', 分隔符: str = ','):
    """
    创建 CSV 流式写入器

    参数:
        文件路径: 输出文件路径
        表头: 列名列表
        编码: 文件编码（默认 utf-8）
        分隔符: 列分隔符（默认 ,）

    返回:
        CSV 写入器对象，可用 writerow() 逐行写入

    示例:
        writer = CSV流式写入('output.csv', ['name', 'age'])
        writer.writerow({'name': '张三', 'age': '25'})
        writer.close()
    """
    f = open(文件路径, 'w', encoding=编码, newline='')
    writer = csv.DictWriter(f, fieldnames=表头, delimiter=分隔符)
    writer.writeheader()
    return _CSVWriter(f, writer)


class _CSVWriter:
    """CSV 流式写入器内部类"""

    def __init__(self, file, writer):
        self._file = file
        self._writer = writer

    def 写入行(self, 行: Dict[str, Any]):
        """写入一行数据"""
        self._writer.writerow(行)

    def 写入多行(self, 行列表: List[Dict[str, Any]]):
        """写入多行数据"""
        self._writer.writerows(行列表)

    def 关闭(self):
        """关闭写入器"""
        self._file.close()


def CSV转字符串(数据: List[Dict[str, Any]], 分隔符: str = ',') -> str:
    """
    将字典列表转换为 CSV 格式字符串

    参数:
        数据: 字典列表
        分隔符: 列分隔符（默认 ,）

    返回:
        CSV 格式字符串
    """
    if not 数据:
        return ''
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(数据[0].keys()), delimiter=分隔符)
    writer.writeheader()
    writer.writerows(数据)
    return output.getvalue()


def 字符串转CSV(文本: str, 分隔符: str = ',') -> List[Dict[str, Any]]:
    """
    将 CSV 格式字符串转换为字典列表

    参数:
        文本: CSV 格式字符串
        分隔符: 列分隔符（默认 ,）

    返回:
        字典列表
    """
    reader = csv.DictReader(io.StringIO(文本), delimiter=分隔符)
    return list(reader)


def CSV获取表头(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> List[str]:
    """获取 CSV 文件表头"""
    with open(文件路径, 'r', encoding=编码, newline='') as f:
        reader = csv.reader(f, delimiter=分隔符)
        return next(reader)


def CSV行数(文件路径: str, 编码: str = 'utf-8') -> int:
    """获取 CSV 文件行数（不含表头）"""
    with open(文件路径, 'r', encoding=编码, newline='') as f:
        return sum(1 for _ in f) - 1


def CSV列数(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> int:
    """获取 CSV 文件列数"""
    return len(CSV获取表头(文件路径, 编码, 分隔符))


def CSV添加行(文件路径: str, 行: Dict[str, Any], 编码: str = 'utf-8', 分隔符: str = ','):
    """向 CSV 文件追加一行"""
    表头 = CSV获取表头(文件路径, 编码, 分隔符)
    with open(文件路径, 'a', encoding=编码, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=表头, delimiter=分隔符)
        writer.writerow(行)


def CSV合并(*文件路径列表: str, 输出文件: str = None, 编码: str = 'utf-8', 分隔符: str = ',') -> str:
    """合并多个 CSV 文件"""
    合并数据 = []
    for 路径 in 文件路径列表:
        合并数据.extend(CSV读取(路径, 编码, 分隔符))
    if 输出文件:
        CSV写入(输出文件, 合并数据, 编码, 分隔符)
    return CSV转字符串(合并数据, 分隔符)


def CSV筛选(文件路径: str, 条件函数, 编码: str = 'utf-8', 分隔符: str = ',') -> List[Dict[str, Any]]:
    """筛选 CSV 数据"""
    数据 = CSV读取(文件路径, 编码, 分隔符)
    return [行 for 行 in 数据 if 条件函数(行)]


def CSV排序(文件路径: str, 键: str, 升序: bool = True, 编码: str = 'utf-8', 分隔符: str = ',') -> List[Dict[str, Any]]:
    """排序 CSV 数据"""
    数据 = CSV读取(文件路径, 编码, 分隔符)
    return sorted(数据, key=lambda x: x.get(键, ''), reverse=not 升序)


def CSV验证(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> bool:
    """验证 CSV 文件格式"""
    try:
        CSV读取(文件路径, 编码, 分隔符)
        return True
    except Exception:
        return False


__all__ = [
    'CSV读取', 'CSV读取列表', 'CSV写入', 'CSV写入列表',
    'CSV流式读取', 'CSV流式写入',
    'CSV转字符串', '字符串转CSV',
    'CSV获取表头', 'CSV行数', 'CSV列数',
    'CSV添加行', 'CSV合并', 'CSV筛选', 'CSV排序', 'CSV验证',
]