"""
段言标准库 - 文件匹配模块

封装 glob 和 fnmatch 模块，提供文件路径模式匹配功能。
"""

import glob
import fnmatch
import os
from typing import List, Pattern, Iterator


def 匹配文件(模式: str, 递归: bool = True, 目录: str = None) -> List[str]:
    """
    按模式匹配文件
    
    参数:
        模式: 匹配模式（支持 * ? [abc] 等）
        递归: 是否递归搜索子目录
        目录: 搜索根目录，None为当前目录
    
    返回:
        匹配的文件路径列表
    """
    原始目录 = os.getcwd()
    if 目录:
        os.chdir(目录)
    
    try:
        if 递归:
            结果 = glob.glob(模式, recursive=True)
        else:
            结果 = glob.glob(模式)
        return 结果
    finally:
        if 目录:
            os.chdir(原始目录)


def 迭代匹配(模式: str, 递归: bool = True, 目录: str = None) -> Iterator[str]:
    """
    迭代器方式匹配文件（适合大量文件）
    
    参数:
        模式: 匹配模式
        递归: 是否递归
        目录: 根目录
    
    返回:
        文件路径迭代器
    """
    原始目录 = os.getcwd()
    if 目录:
        os.chdir(目录)
    
    try:
        if 递归:
            for 路径 in glob.iglob(模式, recursive=True):
                yield 路径
        else:
            for 路径 in glob.iglob(模式):
                yield 路径
    finally:
        if 目录:
            os.chdir(原始目录)


def 名称匹配(文件名: str, 模式: str) -> bool:
    """
    检查文件名是否匹配模式（fnmatch）
    
    参数:
        文件名: 文件名
        模式: 匹配模式
    
    返回:
        是否匹配
    """
    return fnmatch.fnmatch(文件名, 模式)


def 名称匹配忽略大小写(文件名: str, 模式: str) -> bool:
    """忽略大小写的文件名匹配"""
    return fnmatch.fnmatchcase(文件名.lower(), 模式.lower())


def 过滤列表(文件列表: List[str], 模式: str) -> List[str]:
    """
    从文件列表中过滤出匹配模式的文件
    
    参数:
        文件列表: 文件名列表
        模式: 匹配模式
    
    返回:
        匹配的文件名列表
    """
    return fnmatch.filter(文件列表, 模式)


def 转义元字符(字符串: str) -> str:
    """
    转义特殊字符（* ? [），使其作为普通字符匹配
    
    参数:
        字符串: 原始字符串
    
    返回:
        转义后的字符串
    """
    return fnmatch.translate(字符串)


def 查找所有Python文件(目录: str = ".", 递归: bool = True) -> List[str]:
    """查找所有Python文件（便捷函数）"""
    return 匹配文件("**/*.py" if 递归 else "*.py", 递归=递归, 目录=目录)


def 查找所有文本文件(目录: str = ".", 递归: bool = True) -> List[str]:
    """查找所有文本文件（便捷函数）"""
    return 匹配文件("**/*.txt" if 递归 else "*.txt", 递归=递归, 目录=目录)


def 查找所有JSON文件(目录: str = ".", 递归: bool = True) -> List[str]:
    """查找所有JSON文件（便捷函数）"""
    return 匹配文件("**/*.json" if 递归 else "*.json", 递归=递归, 目录=目录)


__all__ = [
    '匹配文件',
    '迭代匹配',
    '名称匹配',
    '名称匹配忽略大小写',
    '过滤列表',
    '转义元字符',
    '查找所有Python文件',
    '查找所有文本文件',
    '查找所有JSON文件',
]
