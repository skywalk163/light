"""
正则表达式模块 - 匹配、捕获、替换

提供正则表达式处理功能，包括：
- 正则匹配与查找
- 分组捕获
- 替换与分割
- 常用模式验证
"""
import re
from typing import List, Tuple, Dict, Optional, Any


class 正则表达式:
    """正则表达式类"""
    
    def __init__(self, 模式: str, 标志: int = 0):
        self._模式 = 模式
        self._标志 = 标志
        self._编译后 = re.compile(模式, 标志)
    
    def 匹配(self, 文本: str) -> bool:
        """检查文本是否匹配正则表达式"""
        return bool(self._编译后.match(文本))
    
    def 完全匹配(self, 文本: str) -> bool:
        """检查文本是否完全匹配正则表达式"""
        return bool(self._编译后.fullmatch(文本))
    
    def 查找(self, 文本: str) -> Optional[str]:
        """查找第一个匹配项"""
        结果 = self._编译后.search(文本)
        return 结果.group() if 结果 else None
    
    def 查找所有(self, 文本: str) -> List[str]:
        """查找所有匹配项"""
        return self._编译后.findall(文本)
    
    def 查找迭代(self, 文本: str):
        """返回匹配迭代器"""
        return self._编译后.finditer(文本)
    
    def 替换(self, 文本: str, 替换文本: str, 最大替换次数: int = 0) -> str:
        """替换匹配项"""
        return self._编译后.sub(替换文本, 文本, 最大替换次数)
    
    def 替换函数(self, 文本: str, 替换函数: callable, 最大替换次数: int = 0) -> str:
        """使用函数替换匹配项"""
        return self._编译后.sub(替换函数, 文本, 最大替换次数)
    
    def 分割(self, 文本: str, 最大分割次数: int = 0) -> List[str]:
        """分割文本"""
        return self._编译后.split(文本, 最大分割次数)
    
    def 捕获分组(self, 文本: str) -> Optional[Tuple[str, ...]]:
        """捕获分组"""
        结果 = self._编译后.search(文本)
        return 结果.groups() if 结果 else None
    
    def 捕获命名分组(self, 文本: str) -> Optional[Dict[str, str]]:
        """捕获命名分组"""
        结果 = self._编译后.search(文本)
        return 结果.groupdict() if 结果 else None
    
    def 获取匹配对象(self, 文本: str) -> Optional[re.Match]:
        """获取匹配对象"""
        return self._编译后.search(文本)
    
    def 获取模式(self) -> str:
        """获取正则模式"""
        return self._模式


def 匹配(模式: str, 文本: str, 标志: int = 0) -> bool:
    """检查文本是否包含匹配项"""
    return bool(re.search(模式, 文本, 标志))


def 完全匹配(模式: str, 文本: str, 标志: int = 0) -> bool:
    """检查文本是否完全匹配正则表达式"""
    return bool(re.fullmatch(模式, 文本, 标志))


def 查找(模式: str, 文本: str, 标志: int = 0) -> Optional[str]:
    """查找第一个匹配项"""
    结果 = re.search(模式, 文本, 标志)
    return 结果.group() if 结果 else None


def 查找所有(模式: str, 文本: str, 标志: int = 0) -> List[str]:
    """查找所有匹配项"""
    return re.findall(模式, 文本, 标志)


def 全部匹配(模式: str, 文本: str, 标志: int = 0) -> List[str]:
    """全部匹配（别名，对应 STDLIB_VERB_ARITY 注册）"""
    return 查找所有(模式, 文本, 标志)


def 匹配迭代(模式: str, 文本: str, 标志: int = 0):
    """匹配迭代（别名，对应 STDLIB_VERB_ARITY 注册）"""
    return re.finditer(模式, 文本, 标志)


def 替换(模式: str, 文本: str, 替换文本: str, 最大替换次数: int = 0, 标志: int = 0) -> str:
    """替换匹配项"""
    return re.sub(模式, 替换文本, 文本, 最大替换次数, 标志)


def 分割(模式: str, 文本: str, 最大分割次数: int = 0, 标志: int = 0) -> List[str]:
    """分割文本"""
    return re.split(模式, 文本, 最大分割次数, 标志)


def 编译(模式: str, 标志: int = 0) -> 正则表达式:
    """编译正则表达式"""
    return 正则表达式(模式, 标志)


def 转义(文本: str) -> str:
    """转义特殊字符"""
    return re.escape(文本)


def 验证邮箱(邮箱: str) -> bool:
    """验证邮箱格式"""
    模式 = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return 完全匹配(模式, 邮箱)


def 验证手机号(手机号: str) -> bool:
    """验证手机号格式"""
    模式 = r'^1[3-9]\d{9}$'
    return 完全匹配(模式, 手机号)


def 验证身份证号(身份证号: str) -> bool:
    """验证身份证号格式"""
    模式 = r'^\d{17}[\dXx]$'
    return 完全匹配(模式, 身份证号)


def 验证URL(URL: str) -> bool:
    """验证URL格式"""
    模式 = r'^https?://[^\s/$.?#].[^\s]*$'
    return 完全匹配(模式, URL)


def 验证IP地址(IP地址: str) -> bool:
    """验证IPv4地址格式"""
    模式 = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return 完全匹配(模式, IP地址)


def 验证IPv6地址(IPv6地址: str) -> bool:
    """验证IPv6地址格式"""
    模式 = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    return 完全匹配(模式, IPv6地址)


def 验证日期(日期: str) -> bool:
    """验证日期格式 YYYY-MM-DD"""
    模式 = r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$'
    return 完全匹配(模式, 日期)


def 验证时间(时间: str) -> bool:
    """验证时间格式 HH:MM:SS"""
    模式 = r'^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$'
    return 完全匹配(模式, 时间)


def 验证日期时间(日期时间: str) -> bool:
    """验证日期时间格式 YYYY-MM-DD HH:MM:SS"""
    模式 = r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]) (?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$'
    return 完全匹配(模式, 日期时间)


def 验证中文字符(文本: str) -> bool:
    """验证是否为中文字符"""
    模式 = r'^[\u4e00-\u9fa5]+$'
    return 完全匹配(模式, 文本)


def 验证数字(文本: str) -> bool:
    """验证是否为数字"""
    模式 = r'^-?\d+$'
    return 完全匹配(模式, 文本)


def 验证浮点数(文本: str) -> bool:
    """验证是否为浮点数"""
    模式 = r'^-?\d+\.\d+$'
    return 完全匹配(模式, 文本)


def 验证十六进制(文本: str) -> bool:
    """验证是否为十六进制数"""
    模式 = r'^0x[0-9a-fA-F]+$'
    return 完全匹配(模式, 文本)


def 提取邮箱(文本: str) -> List[str]:
    """提取文本中的所有邮箱"""
    模式 = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return 查找所有(模式, 文本)


def 提取手机号(文本: str) -> List[str]:
    """提取文本中的所有手机号"""
    模式 = r'1[3-9]\d{9}'
    return 查找所有(模式, 文本)


def 提取URL(文本: str) -> List[str]:
    """提取文本中的所有URL"""
    模式 = r'https?://[^\s/$.?#].[^\s]*'
    return 查找所有(模式, 文本)


def 提取IP地址(文本: str) -> List[str]:
    """提取文本中的所有IP地址"""
    模式 = r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
    return 查找所有(模式, 文本)


def 提取HTML标签(文本: str) -> List[str]:
    """提取文本中的所有HTML标签"""
    模式 = r'<[^>]+>'
    return 查找所有(模式, 文本)


def 去除HTML标签(文本: str) -> str:
    """去除文本中的HTML标签"""
    模式 = r'<[^>]+>'
    return 替换(模式, 文本, '')


def 提取中文字符(文本: str) -> str:
    """提取文本中的所有中文字符"""
    模式 = r'[\u4e00-\u9fa5]+'
    return ''.join(查找所有(模式, 文本))


def 去除空白字符(文本: str) -> str:
    """去除文本中的空白字符"""
    模式 = r'\s+'
    return 替换(模式, 文本, '')


def 去除首尾空白(文本: str) -> str:
    """去除文本首尾的空白字符"""
    return 替换(r'^\s+|\s+$', 文本, '')


def 替换换行符(文本: str, 替换为: str = ' ') -> str:
    """替换换行符"""
    模式 = r'\r?\n'
    return 替换(模式, 文本, 替换为)


def 提取数字(文本: str) -> List[str]:
    """提取文本中的所有数字"""
    模式 = r'-?\d+\.?\d*'
    return 查找所有(模式, 文本)


def 提取单词(文本: str) -> List[str]:
    """提取文本中的所有单词"""
    模式 = r'[a-zA-Z]+'
    return 查找所有(模式, 文本)


def 提取中文词语(文本: str) -> List[str]:
    """提取文本中的所有中文词语"""
    模式 = r'[\u4e00-\u9fa5]{2,}'
    return 查找所有(模式, 文本)


def 验证密码强度(密码: str) -> str:
    """验证密码强度"""
    if len(密码) < 8:
        return '弱'
    
    强度 = 0
    if re.search(r'[a-z]', 密码):
        强度 += 1
    if re.search(r'[A-Z]', 密码):
        强度 += 1
    if re.search(r'[0-9]', 密码):
        强度 += 1
    if re.search(r'[^a-zA-Z0-9]', 密码):
        强度 += 1
    
    if 强度 <= 1:
        return '弱'
    elif 强度 <= 2:
        return '中等'
    elif 强度 <= 3:
        return '强'
    else:
        return '非常强'


def 匹配多行(模式: str, 文本: str) -> bool:
    """多行模式匹配"""
    return 匹配(模式, 文本, re.MULTILINE)


def 忽略大小写匹配(模式: str, 文本: str) -> bool:
    """忽略大小写匹配"""
    return 匹配(模式, 文本, re.IGNORECASE)


def 点号匹配换行(模式: str, 文本: str) -> bool:
    """点号匹配换行"""
    return 匹配(模式, 文本, re.DOTALL)


# =============================================================================
# 从正则.py合并的独有函数
# =============================================================================

def 搜索(模式: str, 字符串: str) -> Optional[str]:
    """
    在字符串中搜索正则模式的第一个匹配。
    
    返回: 第一个匹配的字符串，无匹配返回 None
    """
    m = re.search(模式, 字符串)
    return m.group(0) if m else None


def 匹配开头(模式: str, 字符串: str) -> Optional[str]:
    """
    检查字符串开头是否匹配正则模式。
    
    返回: 匹配到的字符串，无匹配返回 None
    """
    m = re.match(模式, 字符串)
    return m.group(0) if m else None


def 是否匹配(模式: str, 字符串: str) -> bool:
    """
    检查字符串是否完全匹配正则模式。
    
    返回: 是否匹配
    """
    return bool(re.fullmatch(模式, 字符串))


def 分组匹配(模式: str, 字符串: str) -> Optional[List[str]]:
    """
    获取正则匹配的分组。
    
    返回: 分组列表，无匹配返回 None
    
    示例:
        分组匹配('(\\d{4})-(\\d{2})-(\\d{2})', '2026-06-16')
        # ['2026', '06', '16']
    """
    m = re.match(模式, 字符串)
    if m:
        return list(m.groups())
    return None


__all__ = [
    # 类
    '正则表达式',
    # 基本操作
    '匹配', '完全匹配', '查找', '查找所有', '替换', '分割',
    '编译', '转义',
    # 合并自正则.py
    '搜索', '匹配开头', '是否匹配', '分组匹配',
    # 验证
    '验证邮箱', '验证手机号', '验证身份证号', '验证URL',
    '验证IP地址', '验证IPv6地址', '验证日期', '验证时间',
    '验证日期时间', '验证中文字符', '验证数字',
    # 高级
    '匹配多行', '忽略大小写匹配', '点号匹配换行',
]