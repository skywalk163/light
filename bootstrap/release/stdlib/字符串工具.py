"""
字符串工具模块 - 分词、大小写、填充等

提供丰富的字符串处理功能，包括：
- 大小写转换
- 填充与对齐
- 分词与拼接
- 编码处理
- 字符串验证
- 文本处理
"""
import re
import unicodedata
from typing import List, Tuple, Optional


def 转大写(文本: str) -> str:
    """转大写"""
    return 文本.upper()


def 转小写(文本: str) -> str:
    """转小写"""
    return 文本.lower()


def 首字母大写(文本: str) -> str:
    """首字母大写"""
    return 文本.capitalize()


def 每个单词首字母大写(文本: str) -> str:
    """每个单词首字母大写"""
    return 文本.title()


def 反转字符串(文本: str) -> str:
    """反转字符串"""
    return 文本[::-1]


def 截取字符串(文本: str, 起始: int = 0, 结束: int = None) -> str:
    """截取字符串"""
    return 文本[起始:结束]


def 分割字符串(文本: str, 分隔符: str = None, 最大分割次数: int = -1) -> List[str]:
    """分割字符串"""
    return 文本.split(分隔符, 最大分割次数)


def 连接字符串(列表: List[str], 连接符: str = '') -> str:
    """连接字符串列表"""
    return 连接符.join(列表)


def 替换字符串(文本: str, 旧字符串: str, 新字符串: str, 替换次数: int = -1) -> str:
    """替换字符串"""
    return 文本.replace(旧字符串, 新字符串, 替换次数)


def 去除首尾空白(文本: str) -> str:
    """去除首尾空白"""
    return 文本.strip()


def 去除左侧空白(文本: str) -> str:
    """去除左侧空白"""
    return 文本.lstrip()


def 去除右侧空白(文本: str) -> str:
    """去除右侧空白"""
    return 文本.rstrip()


def 去除所有空白(文本: str) -> str:
    """去除所有空白"""
    return ''.join(文本.split())


def 左填充(文本: str, 宽度: int, 填充字符: str = ' ') -> str:
    """左填充"""
    return 文本.rjust(宽度, 填充字符)


def 右填充(文本: str, 宽度: int, 填充字符: str = ' ') -> str:
    """右填充"""
    return 文本.ljust(宽度, 填充字符)


def 居中填充(文本: str, 宽度: int, 填充字符: str = ' ') -> str:
    """居中填充"""
    return 文本.center(宽度, 填充字符)


def 零填充(文本: str, 宽度: int) -> str:
    """零填充"""
    return 文本.zfill(宽度)


def 重复字符串(文本: str, 次数: int) -> str:
    """重复字符串"""
    return 文本 * 次数


def 字符串长度(文本: str) -> int:
    """获取字符串长度"""
    return len(文本)


def 字符计数(文本: str, 字符: str) -> int:
    """计数字符出现次数"""
    return 文本.count(字符)


def 子串查找(文本: str, 子串: str, 起始位置: int = 0, 结束位置: int = None) -> int:
    """查找子串位置"""
    return 文本.find(子串, 起始位置, 结束位置)


def 子串查找最后(文本: str, 子串: str, 起始位置: int = 0, 结束位置: int = None) -> int:
    """从末尾查找子串位置"""
    return 文本.rfind(子串, 起始位置, 结束位置)


def 包含子串(文本: str, 子串: str) -> bool:
    """检查是否包含子串"""
    return 子串 in 文本


def 以子串开头(文本: str, 前缀: str) -> bool:
    """检查是否以前缀开头"""
    return 文本.startswith(前缀)


def 以子串结尾(文本: str, 后缀: str) -> bool:
    """检查是否以后缀结尾"""
    return 文本.endswith(后缀)


def 字符串对齐(文本: str, 宽度: int, 对齐方式: str = 'left') -> str:
    """字符串对齐"""
    if 对齐方式 == 'left':
        return 文本.ljust(宽度)
    elif 对齐方式 == 'right':
        return 文本.rjust(宽度)
    elif 对齐方式 == 'center':
        return 文本.center(宽度)
    else:
        return 文本


def 分词(文本: str, 分隔符: str = None) -> List[str]:
    """分词"""
    return 文本.split(分隔符)


def 中文分词(文本: str) -> List[str]:
    """简单中文分词（按字分词）"""
    return list(文本)


def 英文分词(文本: str) -> List[str]:
    """英文分词（按空格分词）"""
    return re.findall(r'\b\w+\b', 文本)


def 按长度分词(文本: str, 长度: int) -> List[str]:
    """按固定长度分词"""
    return [文本[i:i + 长度] for i in range(0, len(文本), 长度)]


def 字符转码(文本: str, 源编码: str = 'utf-8', 目标编码: str = 'gbk') -> bytes:
    """字符转码"""
    return 文本.encode(源编码).decode(目标编码).encode(目标编码)


def UTF8转GBK(文本: str) -> bytes:
    """UTF-8转GBK"""
    return 文本.encode('utf-8').decode('gbk').encode('gbk')


def GBK转UTF8(字节: bytes) -> str:
    """GBK转UTF-8"""
    return 字节.decode('gbk').encode('utf-8').decode('utf-8')


def ASCII转Unicode(文本: str) -> str:
    """ASCII转Unicode"""
    return ''.join(chr(ord(c)) for c in 文本)


def Unicode转ASCII(文本: str) -> str:
    """Unicode转ASCII（非ASCII字符转义）"""
    return ''.join(c if ord(c) < 128 else f'\\u{ord(c):04x}' for c in 文本)


def Base64编码(文本: str) -> str:
    """Base64编码"""
    import base64
    return base64.b64encode(文本.encode('utf-8')).decode('utf-8')


def Base64解码(文本: str) -> str:
    """Base64解码"""
    import base64
    return base64.b64decode(文本).decode('utf-8')


def URL编码(文本: str) -> str:
    """URL编码"""
    import urllib.parse
    return urllib.parse.quote(文本)


def URL解码(文本: str) -> str:
    """URL解码"""
    import urllib.parse
    return urllib.parse.unquote(文本)


def HTML编码(文本: str) -> str:
    """HTML编码"""
    映射 = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    }
    return ''.join(映射.get(c, c) for c in 文本)


def HTML解码(文本: str) -> str:
    """HTML解码"""
    映射 = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
    }
    for 编码, 原始 in 映射.items():
        文本 = 文本.replace(编码, 原始)
    return 文本


def 十六进制转字符串(十六进制: str) -> str:
    """十六进制转字符串"""
    return bytes.fromhex(十六进制).decode('utf-8')


def 字符串转十六进制(文本: str) -> str:
    """字符串转十六进制"""
    return 文本.encode('utf-8').hex()


def 二进制转字符串(二进制: str) -> str:
    """二进制转字符串"""
    return ''.join(chr(int(二进制[i:i + 8], 2)) for i in range(0, len(二进制), 8))


def 字符串转二进制(文本: str) -> str:
    """字符串转二进制"""
    return ''.join(format(ord(c), '08b') for c in 文本)


def MD5哈希(文本: str) -> str:
    """MD5哈希"""
    import hashlib
    return hashlib.md5(文本.encode('utf-8')).hexdigest()


def SHA256哈希(文本: str) -> str:
    """SHA256哈希"""
    import hashlib
    return hashlib.sha256(文本.encode('utf-8')).hexdigest()


def 生成随机字符串(长度: int = 10, 字符集: str = 'abcdefghijklmnopqrstuvwxyz0123456789') -> str:
    """生成随机字符串"""
    import random
    return ''.join(random.choice(字符集) for _ in range(长度))


def 生成UUID() -> str:
    """生成UUID"""
    import uuid
    return str(uuid.uuid4())


def 验证邮箱(邮箱: str) -> bool:
    """验证邮箱格式"""
    模式 = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(模式, 邮箱))


def 验证手机号(手机号: str) -> bool:
    """验证手机号格式"""
    模式 = r'^1[3-9]\d{9}$'
    return bool(re.match(模式, 手机号))


def 验证身份证号(身份证号: str) -> bool:
    """验证身份证号格式"""
    模式 = r'^\d{17}[\dXx]$'
    return bool(re.match(模式, 身份证号))


def 验证URL(URL: str) -> bool:
    """验证URL格式"""
    模式 = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(模式, URL))


def 验证IP地址(IP地址: str) -> bool:
    """验证IPv4地址格式"""
    模式 = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return bool(re.match(模式, IP地址))


def 验证日期(日期: str) -> bool:
    """验证日期格式 YYYY-MM-DD"""
    模式 = r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$'
    return bool(re.match(模式, 日期))


def 验证数字(文本: str) -> bool:
    """验证是否为数字"""
    return 文本.isdigit()


def 验证字母(文本: str) -> bool:
    """验证是否为字母"""
    return 文本.isalpha()


def 验证字母数字(文本: str) -> bool:
    """验证是否为字母数字"""
    return 文本.isalnum()


def 验证空白(文本: str) -> bool:
    """验证是否为空白字符"""
    return 文本.isspace()


def 验证标题(文本: str) -> bool:
    """验证是否为标题格式"""
    return 文本.istitle()


def 验证小写(文本: str) -> bool:
    """验证是否为小写"""
    return 文本.islower()


def 验证大写(文本: str) -> bool:
    """验证是否为大写"""
    return 文本.isupper()


def 去除HTML标签(文本: str) -> str:
    """去除HTML标签"""
    return re.sub(r'<[^>]+>', '', 文本)


def 提取HTML标签(文本: str) -> List[str]:
    """提取HTML标签"""
    return re.findall(r'<[^>]+>', 文本)


def 提取文本中的数字(文本: str) -> List[str]:
    """提取文本中的数字"""
    return re.findall(r'-?\d+\.?\d*', 文本)


def 提取文本中的邮箱(文本: str) -> List[str]:
    """提取文本中的邮箱"""
    return re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', 文本)


def 提取文本中的手机号(文本: str) -> List[str]:
    """提取文本中的手机号"""
    return re.findall(r'1[3-9]\d{9}', 文本)


def 提取文本中的URL(文本: str) -> List[str]:
    """提取文本中的URL"""
    return re.findall(r'https?://[^\s/$.?#].[^\s]*', 文本)


def 去除标点符号(文本: str) -> str:
    """去除标点符号"""
    return re.sub(r'[^\w\s]', '', 文本)


def 去除特殊字符(文本: str) -> str:
    """去除特殊字符"""
    return re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5\s]', '', 文本)


def 替换换行符(文本: str, 替换为: str = ' ') -> str:
    """替换换行符"""
    return re.sub(r'\r?\n', 替换为, 文本)


def 替换多个空白(文本: str, 替换为: str = ' ') -> str:
    """替换多个空白为单个空格"""
    return re.sub(r'\s+', 替换为, 文本)


def 文本清洗(文本: str) -> str:
    """文本清洗（去除多余空白、特殊字符等）"""
    文本 = 去除首尾空白(文本)
    文本 = 替换多个空白(文本)
    文本 = 去除特殊字符(文本)
    return 文本


def 生成哈希值(文本: str, 算法: str = 'md5') -> str:
    """生成哈希值"""
    import hashlib
    if 算法 == 'md5':
        return hashlib.md5(文本.encode('utf-8')).hexdigest()
    elif 算法 == 'sha1':
        return hashlib.sha1(文本.encode('utf-8')).hexdigest()
    elif 算法 == 'sha256':
        return hashlib.sha256(文本.encode('utf-8')).hexdigest()
    elif 算法 == 'sha512':
        return hashlib.sha512(文本.encode('utf-8')).hexdigest()
    else:
        raise ValueError(f'未知算法: {算法}')


def 字符串比较(文本1: str, 文本2: str, 忽略大小写: bool = False) -> bool:
    """字符串比较"""
    if 忽略大小写:
        return 文本1.lower() == 文本2.lower()
    return 文本1 == 文本2


def 字符串相似度(文本1: str, 文本2: str) -> float:
    """计算字符串相似度（Levenshtein距离）"""
    矩阵 = [[0] * (len(文本2) + 1) for _ in range(len(文本1) + 1)]
    
    for i in range(len(文本1) + 1):
        矩阵[i][0] = i
    for j in range(len(文本2) + 1):
        矩阵[0][j] = j
    
    for i in range(1, len(文本1) + 1):
        for j in range(1, len(文本2) + 1):
            if 文本1[i - 1] == 文本2[j - 1]:
                成本 = 0
            else:
                成本 = 1
            矩阵[i][j] = min(矩阵[i - 1][j] + 1, 矩阵[i][j - 1] + 1, 矩阵[i - 1][j - 1] + 成本)
    
    最大长度 = max(len(文本1), len(文本2))
    return 1 - 矩阵[len(文本1)][len(文本2)] / 最大长度


def 查找所有出现位置(文本: str, 子串: str) -> List[int]:
    """查找所有出现位置"""
    位置 = []
    起始 = 0
    while True:
        idx = 文本.find(子串, 起始)
        if idx == -1:
            break
        位置.append(idx)
        起始 = idx + 1
    return 位置


def 安全字符串(文本: str, 最大长度: int = 1000) -> str:
    """安全字符串（截断并去除特殊字符）"""
    文本 = str(文本)[:最大长度]
    return re.sub(r'[<>"\']', '', 文本)


def 格式化数字(数字: float, 小数位数: int = 2) -> str:
    """格式化数字"""
    return f'{数字:.{小数位数}f}'


def 格式化金额(金额: float) -> str:
    """格式化金额"""
    return f'{金额:,.2f}'


def 格式化百分比(数值: float) -> str:
    """格式化百分比"""
    return f'{数值 * 100:.2f}%'