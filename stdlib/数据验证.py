# -*- coding: utf-8 -*-
"""
光明标准库 - 数据验证模块

提供数据验证、类型检查、格式校验等功能。
"""

import re
import json
from typing import Any, Dict, List, Optional, Callable, Tuple


class 验证错误(Exception):
    """验证错误"""
    pass


class 验证结果:
    """验证结果"""

    def __init__(self):
        self._错误列表: List[str] = []
        self._警告列表: List[str] = []

    def 添加错误(self, 消息: str):
        """添加错误"""
        self._错误列表.append(消息)

    def 添加警告(self, 消息: str):
        """添加警告"""
        self._警告列表.append(消息)

    def 是否有效(self) -> bool:
        """是否验证通过"""
        return len(self._错误列表) == 0

    def 获取错误(self) -> List[str]:
        """获取所有错误"""
        return self._错误列表

    def 获取警告(self) -> List[str]:
        """获取所有警告"""
        return self._警告列表

    def 抛出异常(self):
        """如果验证失败则抛出异常"""
        if not self.是否有效():
            raise 验证错误('\n'.join(self._错误列表))


def 验证必填(值: Any, 字段名: str = '') -> 验证结果:
    """验证必填字段"""
    结果 = 验证结果()
    if 值 is None or (isinstance(值, str) and 值.strip() == ''):
        结果.添加错误(f"{字段名 or '字段'} 为必填项")
    return 结果


def 验证类型(值: Any, 期望类型: type, 字段名: str = '') -> 验证结果:
    """验证类型"""
    结果 = 验证结果()
    if not isinstance(值, 期望类型):
        结果.添加错误(f"{字段名 or '字段'} 期望类型 {期望类型.__name__}，但得到 {type(值).__name__}")
    return 结果


def 验证长度(值: str, 最小: int = 0, 最大: int = -1, 字段名: str = '') -> 验证结果:
    """验证字符串长度"""
    结果 = 验证结果()
    if not isinstance(值, str):
        结果.添加错误(f"{字段名 or '字段'} 不是字符串")
        return 结果
    长度 = len(值)
    if 长度 < 最小:
        结果.添加错误(f"{字段名 or '字段'} 长度 {长度} 小于最小值 {最小}")
    if 最大 > 0 and 长度 > 最大:
        结果.添加错误(f"{字段名 or '字段'} 长度 {长度} 大于最大值 {最大}")
    return 结果


def 验证范围(值: float, 最小: float = None, 最大: float = None, 字段名: str = '') -> 验证结果:
    """验证数值范围"""
    结果 = 验证结果()
    if 最小 is not None and 值 < 最小:
        结果.添加错误(f"{字段名 or '字段'} {值} 小于最小值 {最小}")
    if 最大 is not None and 值 > 最大:
        结果.添加错误(f"{字段名 or '字段'} {值} 大于最大值 {最大}")
    return 结果


def 验证邮箱(邮箱: str) -> 验证结果:
    """验证邮箱格式"""
    结果 = 验证结果()
    模式 = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(模式, 邮箱):
        结果.添加错误(f"邮箱格式无效: {邮箱}")
    return 结果


def 验证手机号(手机号: str) -> 验证结果:
    """验证中国大陆手机号格式"""
    结果 = 验证结果()
    模式 = r'^1[3-9]\d{9}$'
    if not re.match(模式, 手机号):
        结果.添加错误(f"手机号格式无效: {手机号}")
    return 结果


def 验证URL(网址: str) -> 验证结果:
    """验证 URL 格式"""
    结果 = 验证结果()
    模式 = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(模式, 网址):
        结果.添加错误(f"URL 格式无效: {网址}")
    return 结果


def 验证IP地址(ip: str) -> 验证结果:
    """验证 IP 地址格式"""
    结果 = 验证结果()
    import ipaddress
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        结果.添加错误(f"IP 地址格式无效: {ip}")
    return 结果


def 验证正则表达式(值: str, 模式: str, 字段名: str = '') -> 验证结果:
    """使用正则表达式验证"""
    结果 = 验证结果()
    if not re.match(模式, 值):
        结果.添加错误(f"{字段名 or '字段'} 不匹配模式: {模式}")
    return 结果


def 验证JSON(字符串: str) -> 验证结果:
    """验证 JSON 字符串"""
    结果 = 验证结果()
    try:
        json.loads(字符串)
    except json.JSONDecodeError as e:
        结果.添加错误(f"JSON 格式无效: {e}")
    return 结果


def 验证枚举(值: Any, 可选值: list, 字段名: str = '') -> 验证结果:
    """验证值是否在枚举列表中"""
    结果 = 验证结果()
    if 值 not in 可选值:
        结果.添加错误(f"{字段名 or '字段'} {值!r} 不在可选值 {可选值} 中")
    return 结果


def 验证集合(验证规则: Dict[str, list], 数据: Dict[str, Any]) -> 验证结果:
    """
    批量验证数据

    验证规则格式:
        {
            '字段名': [('必填',), ('类型', str), ('长度', 1, 100), ...],
        }

    参数:
        验证规则: 字段验证规则字典
        数据: 要验证的数据

    返回:
        验证结果
    """
    结果 = 验证结果()

    for 字段名, 规则列表 in 验证规则.items():
        值 = 数据.get(字段名)

        for 规则 in 规则列表:
            规则名 = 规则[0]

            if 规则名 == '必填':
                子结果 = 验证必填(值, 字段名)
            elif 规则名 == '类型':
                子结果 = 验证类型(值, 规则[1], 字段名)
            elif 规则名 == '长度':
                子结果 = 验证长度(值, 规则[1], 规则[2] if len(规则) > 2 else -1, 字段名)
            elif 规则名 == '范围':
                子结果 = 验证范围(值, 规则[1] if len(规则) > 1 else None,
                                    规则[2] if len(规则) > 2 else None, 字段名)
            elif 规则名 == '邮箱':
                子结果 = 验证邮箱(值)
            elif 规则名 == '手机号':
                子结果 = 验证手机号(值)
            elif 规则名 == 'URL':
                子结果 = 验证URL(值)
            elif 规则名 == 'IP':
                子结果 = 验证IP地址(值)
            elif 规则名 == '正则':
                子结果 = 验证正则表达式(值, 规则[1], 字段名)
            elif 规则名 == '枚举':
                子结果 = 验证枚举(值, 规则[1], 字段名)
            else:
                continue

            for 错误 in 子结果.获取错误():
                结果.添加错误(错误)

    return 结果


class 数据模式:
    """
    数据模式定义

    用法:
        模式 = 数据模式({
            '姓名': {'类型': str, '必填': True, '长度最小': 2, '长度最大': 50},
            '年龄': {'类型': int, '范围最小': 0, '范围最大': 150},
            '邮箱': {'类型': str, '邮箱': True},
        })
        结果 = 模式.验证({'姓名': '张三', '年龄': 25, '邮箱': 'test@example.com'})
        结果.是否有效()  # True
    """

    def __init__(self, 字段定义: Dict[str, Dict[str, Any]]):
        self._字段定义 = 字段定义

    def 验证(self, 数据: Dict[str, Any]) -> 验证结果:
        """验证数据"""
        结果 = 验证结果()

        for 字段名, 定义 in self._字段定义.items():
            值 = 数据.get(字段名)

            if 定义.get('必填', False):
                if 值 is None or (isinstance(值, str) and 值.strip() == ''):
                    结果.添加错误(f"{字段名} 为必填项")
                    continue

            if 值 is None:
                continue

            期望类型 = 定义.get('类型')
            if 期望类型 and not isinstance(值, 期望类型):
                结果.添加错误(f"{字段名} 期望类型 {期望类型.__name__}，但得到 {type(值).__name__}")
                continue

            if isinstance(值, str):
                长度最小 = 定义.get('长度最小', 0)
                长度最大 = 定义.get('长度最大', -1)
                if len(值) < 长度最小:
                    结果.添加错误(f"{字段名} 长度 {len(值)} 小于最小值 {长度最小}")
                if 长度最大 > 0 and len(值) > 长度最大:
                    结果.添加错误(f"{字段名} 长度 {len(值)} 大于最大值 {长度最大}")

                if 定义.get('邮箱'):
                    子结果 = 验证邮箱(值)
                    结果._错误列表.extend(子结果.获取错误())
                if 定义.get('手机号'):
                    子结果 = 验证手机号(值)
                    结果._错误列表.extend(子结果.获取错误())
                if 定义.get('URL'):
                    子结果 = 验证URL(值)
                    结果._错误列表.extend(子结果.获取错误())

            if isinstance(值, (int, float)):
                范围最小 = 定义.get('范围最小')
                范围最大 = 定义.get('范围最大')
                子结果 = 验证范围(值, 范围最小, 范围最大, 字段名)
                结果._错误列表.extend(子结果.获取错误())

        return 结果


def 创建数据模式(字段定义: Dict[str, Dict[str, Any]]) -> 数据模式:
    """创建数据模式"""
    return 数据模式(字段定义)