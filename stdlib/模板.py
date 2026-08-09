# -*- coding: utf-8 -*-
"""
光明标准库 - 模板引擎模块

提供简单的字符串替换模板引擎功能。
"""

import re
from typing import Dict, Any, Optional


class 模板:
    """简单模板引擎类"""

    def __init__(self, 模板字符串: str):
        """
        创建模板

        参数:
            模板字符串: 包含占位符的模板字符串

        占位符格式:
            {{变量名}} - 简单变量替换
            {{变量名|默认值}} - 带默认值的变量
        """
        self._模板 = 模板字符串

    def 渲染(self, 数据: Dict[str, Any]) -> str:
        """
        渲染模板

        参数:
            数据: 变量值字典

        返回:
            渲染后的字符串

        示例:
            t = 模板('Hello, {{name}}!')
            t.渲染({'name': '光明'})  # 'Hello, 光明!'
        """
        def _替换(match):
            变量名 = match.group(1)
            if '|' in 变量名:
                变量名, 默认值 = 变量名.split('|', 1)
                return str(数据.get(变量名.strip(), 默认值.strip()))
            return str(数据.get(变量名, ''))

        return re.sub(r'\{\{(.+?)\}\}', _替换, self._模板)

    def 渲染文件(self, 模板文件: str, 数据: Dict[str, Any]) -> str:
        """
        从文件读取模板并渲染

        参数:
            模板文件: 模板文件路径
            数据: 变量值字典

        返回:
            渲染后的字符串
        """
        with open(模板文件, 'r', encoding='utf-8') as f:
            self._模板 = f.read()
        return self.渲染(数据)


def 渲染模板(模板字符串: str, 数据: Dict[str, Any]) -> str:
    """
    渲染模板字符串

    参数:
        模板字符串: 包含占位符的模板字符串
        数据: 变量值字典

    返回:
        渲染后的字符串

    示例:
        渲染模板('Hello, {{name}}!', {'name': '光明'})  # 'Hello, 光明!'
    """
    return 模板(模板字符串).渲染(数据)


def 渲染模板文件(模板文件: str, 数据: Dict[str, Any]) -> str:
    """
    从文件读取模板并渲染

    参数:
        模板文件: 模板文件路径
        数据: 变量值字典

    返回:
        渲染后的字符串
    """
    with open(模板文件, 'r', encoding='utf-8') as f:
        模板字符串 = f.read()
    return 渲染模板(模板字符串, 数据)


def 模板变量替换(文本: str, 变量: Dict[str, str]) -> str:
    """
    简单的变量替换（支持 {{变量名}} 和 ${变量名} 格式）

    参数:
        文本: 包含占位符的文本
        变量: 变量值字典

    返回:
        替换后的文本
    """
    结果 = 文本
    for 键, 值 in 变量.items():
        结果 = 结果.replace('{{' + 键 + '}}', str(值))
        结果 = 结果.replace('${' + 键 + '}', str(值))
    return 结果


def 模板循环(模板字符串: str, 数据列表: list, 循环变量: str = 'item') -> str:
    """
    循环渲染模板

    参数:
        模板字符串: 包含循环变量的模板
        数据列表: 数据列表，每个元素是字典
        循环变量: 循环变量名（默认 'item'）

    返回:
        渲染后的字符串（所有循环结果拼接）

    示例:
        模板循环('{{item.name}}: {{item.age}}\n',
                   [{'name': '甲', 'age': 20}, {'name': '乙', 'age': 30}])
    """
    结果列表 = []
    for 数据 in 数据列表:
        if isinstance(数据, dict):
            包装数据 = {f'{循环变量}.{k}': v for k, v in 数据.items()}
            结果列表.append(模板变量替换(模板字符串, 包装数据))
        else:
            结果列表.append(模板变量替换(模板字符串, {循环变量: str(数据)}))
    return ''.join(结果列表)


def 模板条件(模板字符串: str, 条件: bool, 真值数据: dict, 假值数据: dict = None) -> str:
    """
    条件渲染模板

    参数:
        模板字符串: 模板字符串
        条件: 条件值
        真值数据: 条件为真时的数据
        假值数据: 条件为假时的数据

    返回:
        渲染后的字符串
    """
    if 条件:
        return 渲染模板(模板字符串, 真值数据)
    return 渲染模板(模板字符串, 假值数据 or {})


__all__ = [
    '模板', '渲染模板', '渲染模板文件',
    '模板变量替换', '模板循环', '模板条件',
]