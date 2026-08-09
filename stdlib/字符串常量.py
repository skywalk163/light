"""
光明标准库 - 字符串常量模块

提供常用字符串常量和字符分类功能。
"""

import string
from typing import List


小写字母 = string.ascii_lowercase
大写字母 = string.ascii_uppercase
字母 = string.ascii_letters
数字 = string.digits
十六进制数字 = string.hexdigits
八进制数字 = string.octdigits
标点符号 = string.punctuation
可打印字符 = string.printable
空白字符 = string.whitespace
换行符 = '\n'
制表符 = '\t'
回车符 = '\r'
空字符串 = ''


def 是字母(字符: str) -> bool:
    """检查字符是否为字母"""
    return 字符.isalpha() if len(字符) == 1 else False


def 是数字(字符: str) -> bool:
    """检查字符是否为数字"""
    return 字符.isdigit() if len(字符) == 1 else False


def 是字母数字(字符: str) -> bool:
    """检查字符是否为字母或数字"""
    return 字符.isalnum() if len(字符) == 1 else False


def 是小写(字符: str) -> bool:
    """检查字符是否为小写字母"""
    return 字符.islower() if len(字符) == 1 else False


def 是大写(字符: str) -> bool:
    """检查字符是否为大写字母"""
    return 字符.isupper() if len(字符) == 1 else False


def 是空白(字符: str) -> bool:
    """检查字符是否为空白字符"""
    return 字符.isspace() if len(字符) == 1 else False


def 是可打印(字符: str) -> bool:
    """检查字符是否为可打印字符"""
    return 字符.isprintable() if len(字符) == 1 else False


def 是标点(字符: str) -> bool:
    """检查字符是否为标点符号"""
    return 字符 in 标点符号 if len(字符) == 1 else False


def 是十六进制(字符: str) -> bool:
    """检查字符是否为十六进制数字"""
    return 字符 in 十六进制数字 if len(字符) == 1 else False


def 是八进制(字符: str) -> bool:
    """检查字符是否为八进制数字"""
    return 字符 in 八进制数字 if len(字符) == 1 else False


def 字符列表全部是(文本: str, 检测函数) -> bool:
    """检查字符串中所有字符是否都满足条件"""
    return all(检测函数(c) for c in 文本) if 文本 else True


def 字符列表有一个是(文本: str, 检测函数) -> bool:
    """检查字符串中是否至少有一个字符满足条件"""
    return any(检测函数(c) for c in 文本) if 文本 else False


def 首字母大写(文本: str) -> str:
    """首字母大写"""
    return 文本.capitalize() if 文本 else 文本


def 标题大小写(文本: str) -> str:
    """标题大小写（每个单词首字母大写）"""
    return 文本.title()


def 全大写(文本: str) -> str:
    """转换为全大写"""
    return 文本.upper()


def 全小写(文本: str) -> str:
    """转换为全小写"""
    return 文本.lower()


def 交换大小写(文本: str) -> str:
    """交换大小写"""
    return 文本.swapcase()


def 去除两端空白(文本: str, 字符: str = None) -> str:
    """去除两端空白或指定字符"""
    if 字符 is None:
        return 文本.strip()
    return 文本.strip(字符)


def 去除左端空白(文本: str, 字符: str = None) -> str:
    """去除左端空白或指定字符"""
    if 字符 is None:
        return 文本.lstrip()
    return 文本.lstrip(字符)


def 去除右端空白(文本: str, 字符: str = None) -> str:
    """去除右端空白或指定字符"""
    if 字符 is None:
        return 文本.rstrip()
    return 文本.rstrip(字符)


def 居中填充(文本: str, 宽度: int, 填充字符: str = ' ') -> str:
    """居中填充"""
    return 文本.center(宽度, 填充字符)


def 左对齐(文本: str, 宽度: int, 填充字符: str = ' ') -> str:
    """左对齐填充"""
    return 文本.ljust(宽度, 填充字符)


def 右对齐(文本: str, 宽度: int, 填充字符: str = ' ') -> str:
    """右对齐填充"""
    return 文本.rjust(宽度, 填充字符)


def 补零(文本: str, 宽度: int) -> str:
    """左侧补零"""
    return 文本.zfill(宽度)


def 连接(分隔符: str, 字符串列表: List[str]) -> str:
    """用分隔符连接字符串列表"""
    return 分隔符.join(字符串列表)


def 分割(文本: str, 分隔符: str = None, 最大分割次数: int = -1) -> List[str]:
    """分割字符串"""
    if 分隔符 is None:
        return 文本.split(maxsplit=最大分割次数)
    return 文本.split(分隔符, 最大分割次数)


def 右分割(文本: str, 分隔符: str, 最大分割次数: int = -1) -> List[str]:
    """从右侧分割字符串"""
    return 文本.rsplit(分隔符, 最大分割次数)


def 按行分割(文本: str, 保留换行符: bool = False) -> List[str]:
    """按行分割"""
    return 文本.splitlines(保留换行符)


def 替换(文本: str, 旧子串: str, 新子串: str, 替换次数: int = -1) -> str:
    """替换子串"""
    return 文本.replace(旧子串, 新子串, 替换次数)


def 包含(文本: str, 子串: str) -> bool:
    """检查是否包含子串"""
    return 子串 in 文本


def 以开头(文本: str, 前缀: str) -> bool:
    """检查是否以前缀开头"""
    return 文本.startswith(前缀)


def 以结尾(文本: str, 后缀: str) -> bool:
    """检查是否以后缀结尾"""
    return 文本.endswith(后缀)


def 查找(文本: str, 子串: str, 起始: int = 0, 结束: int = -1) -> int:
    """查找子串位置，未找到返回-1"""
    if 结束 == -1:
        return 文本.find(子串, 起始)
    return 文本.find(子串, 起始, 结束)


def 反向查找(文本: str, 子串: str, 起始: int = 0, 结束: int = -1) -> int:
    """从右侧查找子串位置"""
    if 结束 == -1:
        return 文本.rfind(子串, 起始)
    return 文本.rfind(子串, 起始, 结束)


def 计数(文本: str, 子串: str, 起始: int = 0, 结束: int = -1) -> int:
    """统计子串出现次数"""
    if 结束 == -1:
        return 文本.count(子串, 起始)
    return 文本.count(子串, 起始, 结束)


__all__ = [
    '小写字母', '大写字母', '字母', '数字', '十六进制数字', '八进制数字',
    '标点符号', '可打印字符', '空白字符', '换行符', '制表符', '回车符', '空字符串',
    '是字母', '是数字', '是字母数字', '是小写', '是大写', '是空白',
    '是可打印', '是标点', '是十六进制', '是八进制',
    '字符列表全部是', '字符列表有一个是',
    '首字母大写', '标题大小写', '全大写', '全小写', '交换大小写',
    '去除两端空白', '去除左端空白', '去除右端空白',
    '居中填充', '左对齐', '右对齐', '补零',
    '连接', '分割', '右分割', '按行分割',
    '替换', '包含', '以开头', '以结尾',
    '查找', '反向查找', '计数',
]
