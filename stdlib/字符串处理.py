"""
光明标准库 - 字符串处理模块

提供字符串操作函数：长度、拼接、分割、替换、查找、大小写转换等
"""

from typing import List, Optional, Dict, Any
import re
import base64


def 长度(s: str) -> int:
    """返回字符串长度"""
    return len(s)


def 拼接(*args: str) -> str:
    """拼接多个字符串"""
    return ''.join(args)


def 分割(s: str, sep: str = '') -> List[str]:
    """分割字符串，默认按空格分割"""
    if not sep:
        return s.split()
    return s.split(sep)


def 替换(s: str, old: str, new: str, 次数: int = -1) -> str:
    """替换字符串中的子串"""
    if 次数 < 0:
        return s.replace(old, new)
    return s.replace(old, new, 次数)


def 查找(s: str, sub: str) -> int:
    """查找子串位置，未找到返回 -1"""
    return s.find(sub)


def 大写(s: str) -> str:
    """转换为大写"""
    return s.upper()


def 小写(s: str) -> str:
    """转换为小写"""
    return s.lower()


def 去除空格(s: str) -> str:
    """去除两端空格"""
    return s.strip()


def 去空格(s: str) -> str:
    """去除两端空格（别名）"""
    return s.strip()


def 判断开头(s: str, prefix: str) -> bool:
    """判断字符串是否以指定前缀开头"""
    return s.startswith(prefix)


def 判断结尾(s: str, suffix: str) -> bool:
    """判断字符串是否以指定后缀结尾"""
    return s.endswith(suffix)


def 格式化(template: str, *args) -> str:
    """格式化字符串"""
    return template.format(*args)


def 截取(s: str, start: int, end: Optional[int] = None) -> str:
    """截取子串"""
    if end is None:
        return s[start:]
    return s[start:end]


def 字符串截取(s: str, start: int, end: Optional[int] = None) -> str:
    """字符串截取（别名，对应 STDLIB_VERB_ARITY 注册）"""
    return 截取(s, start, end)


def 是数字符(s: str) -> bool:
    """判断字符串是否全为数字字符"""
    return s.isdigit()


def 重复(s: str, n: int) -> str:
    """重复字符串 n 次"""
    return s * n


def 计数(s: str, sub: str) -> int:
    """统计子串出现次数"""
    return s.count(sub)


def 反转(s: str) -> str:
    """反转字符串"""
    return s[::-1]


def 标题(s: str) -> str:
    """转换为标题格式（首字母大写）"""
    return s.title()


def 大小写互换(s: str) -> str:
    """大小写互换"""
    return s.swapcase()


def 首字母大写(s: str) -> str:
    """首字母大写，其余小写"""
    return s.capitalize()


def 左对齐(s: str, width: int, 填充字符: str = ' ') -> str:
    """左对齐字符串"""
    return s.ljust(width, 填充字符)


def 右对齐(s: str, width: int, 填充字符: str = ' ') -> str:
    """右对齐字符串"""
    return s.rjust(width, 填充字符)


def 居中(s: str, width: int, 填充字符: str = ' ') -> str:
    """居中对齐字符串"""
    return s.center(width, 填充字符)


def 去除左侧空格(s: str) -> str:
    """去除左侧空格"""
    return s.lstrip()


def 去除右侧空格(s: str) -> str:
    """去除右侧空格"""
    return s.rstrip()


def 去除指定字符(s: str, 字符集: str = None) -> str:
    """去除两端指定字符"""
    if 字符集 is None:
        return s.strip()
    return s.strip(字符集)


def 去除左侧指定字符(s: str, 字符集: str = None) -> str:
    """去除左侧指定字符"""
    if 字符集 is None:
        return s.lstrip()
    return s.lstrip(字符集)


def 去除右侧指定字符(s: str, 字符集: str = None) -> str:
    """去除右侧指定字符"""
    if 字符集 is None:
        return s.rstrip()
    return s.rstrip(字符集)


def 查找从右(s: str, sub: str) -> int:
    """从右侧查找子串位置，未找到返回 -1"""
    return s.rfind(sub)


def 查找所有(s: str, sub: str) -> List[int]:
    """查找所有子串位置"""
    result = []
    start = 0
    while True:
        pos = s.find(sub, start)
        if pos == -1:
            break
        result.append(pos)
        start = pos + 1
    return result


def 替换正则(s: str, 模式: str, 替换: str) -> str:
    """使用正则表达式替换"""
    return re.sub(模式, 替换, s)


def 匹配正则(s: str, 模式: str) -> bool:
    """检查字符串是否匹配正则表达式"""
    return bool(re.match(模式, s))


def 搜索正则(s: str, 模式: str) -> Optional[re.Match]:
    """搜索正则表达式"""
    match = re.search(模式, s)
    return match


def 分割正则(s: str, 模式: str) -> List[str]:
    """使用正则表达式分割字符串"""
    return re.split(模式, s)


def 查找所有匹配(s: str, 模式: str) -> List[str]:
    """查找所有匹配正则表达式的子串"""
    return re.findall(模式, s)


def Base64编码(s: str) -> str:
    """Base64编码"""
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')


def Base64解码(s: str) -> str:
    """Base64解码"""
    return base64.b64decode(s).decode('utf-8')


def Base32编码(s: str) -> str:
    """Base32编码"""
    return base64.b32encode(s.encode('utf-8')).decode('utf-8')


def Base32解码(s: str) -> str:
    """Base32解码"""
    return base64.b32decode(s).decode('utf-8')


def 十六进制编码(s: str) -> str:
    """十六进制编码"""
    return s.encode('utf-8').hex()


def 十六进制解码(s: str) -> str:
    """十六进制解码"""
    return bytes.fromhex(s).decode('utf-8')


def URL编码(s: str) -> str:
    """URL编码"""
    import urllib.parse
    return urllib.parse.quote(s)


def URL解码(s: str) -> str:
    """URL解码"""
    import urllib.parse
    return urllib.parse.unquote(s)


def HTML编码(s: str) -> str:
    """HTML编码"""
    import html
    return html.escape(s)


def HTML解码(s: str) -> str:
    """HTML解码"""
    import html
    return html.unescape(s)


def 编码(s: str, 编码格式: str = 'utf-8') -> bytes:
    """字符串转字节"""
    return s.encode(编码格式)


def 解码(b: bytes, 编码格式: str = 'utf-8') -> str:
    """字节转字符串"""
    return b.decode(编码格式)


def 格式化字典(template: str, **kwargs) -> str:
    """使用字典格式化字符串"""
    return template.format(**kwargs)


def 格式化f字符串(template: str, **kwargs) -> str:
    """使用f字符串方式格式化（模拟）"""
    return template.format(**kwargs)


def 字符串切片(s: str, start: int, end: int = None, step: int = 1) -> str:
    """字符串切片"""
    if end is None:
        return s[start::step]
    return s[start:end:step]


def 填充前导(s: str, width: int, 填充字符: str = '0') -> str:
    """前导填充"""
    return s.zfill(width)


def 转义(s: str) -> str:
    """转义特殊字符"""
    return repr(s)[1:-1]


def 转义正则(s: str) -> str:
    """转义正则表达式特殊字符"""
    return re.escape(s)


def 是否全大写(s: str) -> bool:
    """检查是否全大写"""
    return s.isupper()


def 是否全小写(s: str) -> bool:
    """检查是否全小写"""
    return s.islower()


def 是否标题格式(s: str) -> bool:
    """检查是否标题格式"""
    return s.istitle()


def 是否字母(s: str) -> bool:
    """检查是否全字母"""
    return s.isalpha()


def 是否数字(s: str) -> bool:
    """检查是否全数字"""
    return s.isdigit()


def 是否字母数字(s: str) -> bool:
    """检查是否字母数字"""
    return s.isalnum()


def 是否空白(s: str) -> bool:
    """检查是否全空白"""
    return s.isspace()


def 是否可打印(s: str) -> bool:
    """检查是否可打印字符"""
    return s.isprintable()


def 是否十进制(s: str) -> bool:
    """检查是否十进制数字"""
    return s.isdecimal()


def 是否数字字符(s: str) -> bool:
    """检查是否数字字符（包括Unicode数字）"""
    return s.isnumeric()


def 比较(s: str, other: str) -> int:
    """字符串比较"""
    if s < other:
        return -1
    elif s > other:
        return 1
    return 0


def 比较忽略大小写(s: str, other: str) -> int:
    """忽略大小写比较"""
    return 比较(s.lower(), other.lower())


def 包含(s: str, sub: str) -> bool:
    """检查是否包含子串"""
    return sub in s


def 包含忽略大小写(s: str, sub: str) -> bool:
    """忽略大小写检查是否包含子串"""
    return sub.lower() in s.lower()


def 以开头(s: str, prefix: str) -> bool:
    """判断是否以指定前缀开头（别名）"""
    return s.startswith(prefix)


def 以结尾(s: str, suffix: str) -> bool:
    """判断是否以指定后缀结尾（别名）"""
    return s.endswith(suffix)


def 插入(s: str, pos: int, 插入字符串: str) -> str:
    """在指定位置插入字符串"""
    return s[:pos] + 插入字符串 + s[pos:]


def 删除(s: str, start: int, end: int) -> str:
    """删除指定范围的字符"""
    return s[:start] + s[end:]


def 替换多次(s: str, 旧字符串: str, 新字符串: str, 次数: int) -> str:
    """替换指定次数"""
    return s.replace(旧字符串, 新字符串, 次数)


def 去除重复空格(s: str) -> str:
    """去除重复空格"""
    return ' '.join(s.split())


def 去除换行(s: str) -> str:
    """去除换行符"""
    return s.replace('\n', '').replace('\r', '')


def 标准化空格(s: str) -> str:
    """标准化空格（统一为单个空格）"""
    return ' '.join(s.split())


def 字符串到列表(s: str) -> List[str]:
    """字符串转字符列表"""
    return list(s)


def 列表到字符串(列表: List[str], 分隔符: str = '') -> str:
    """字符列表转字符串"""
    return 分隔符.join(列表)


def 字符转ASCII(c: str) -> int:
    """字符转ASCII码"""
    return ord(c)


def ASCII转字符(n: int) -> str:
    """ASCII码转字符"""
    return chr(n)


def 获取字符(s: str, index: int) -> str:
    """获取指定位置的字符"""
    return s[index]


def 设置字符(s: str, index: int, 新字符: str) -> str:
    """设置指定位置的字符"""
    return s[:index] + 新字符 + s[index + 1:]


def 子串次数(s: str, sub: str) -> int:
    """统计子串出现次数（别名）"""
    return s.count(sub)


def 子串位置(s: str, sub: str) -> int:
    """查找子串位置（别名）"""
    return s.find(sub)


def 分割成行(s: str) -> List[str]:
    """按行分割"""
    return s.splitlines()


def 合并成行(列表: List[str], 换行符: str = '\n') -> str:
    """合并成行"""
    return 换行符.join(列表)


def 移除前缀(s: str, 前缀: str) -> str:
    """移除前缀"""
    return s[len(前缀):] if s.startswith(前缀) else s


def 移除后缀(s: str, 后缀: str) -> str:
    """移除后缀"""
    return s[:-len(后缀)] if s.endswith(后缀) else s


def 交换前缀后缀(s: str, 前缀: str, 后缀: str) -> str:
    """交换前缀和后缀"""
    return 后缀 + s[len(前缀):-len(后缀)] + 前缀 if s.startswith(前缀) and s.endswith(后缀) else s


def 字符串转数字(s: str) -> float:
    """字符串转数字"""
    try:
        return int(s)
    except ValueError:
        return float(s)


def 数字转字符串(n: float) -> str:
    """数字转字符串"""
    return str(n)


def 格式化为整数(s: str) -> int:
    """格式化为整数"""
    return int(s)


def 格式化为浮点数(s: str) -> float:
    """格式化为浮点数"""
    return float(s)


def 格式化为科学计数法(n: float, 精度: int = 6) -> str:
    """格式化为科学计数法"""
    return f"{n:.{精度}e}"


def 格式化为百分比(n: float, 小数位数: int = 2) -> str:
    """格式化为百分比"""
    return f"{n * 100:.{小数位数}f}%"


def 格式化数字(n: float, 小数位数: int = 2) -> str:
    """格式化数字"""
    return f"{n:.{小数位数}f}"


def 格式化整数(n: int, 位数: int = 0) -> str:
    """格式化整数，不足位数前导补零"""
    if 位数 <= 0:
        return str(n)
    return f"{n:0{位数}d}"


def 字符串哈希(s: str) -> int:
    """字符串哈希值"""
    return hash(s)


def 字符串相等(s1: str, s2: str) -> bool:
    """字符串相等"""
    return s1 == s2


def 字符串不等(s1: str, s2: str) -> bool:
    """字符串不等"""
    return s1 != s2


def 字符串小于(s1: str, s2: str) -> bool:
    """字符串小于"""
    return s1 < s2


def 字符串大于(s1: str, s2: str) -> bool:
    """字符串大于"""
    return s1 > s2


def 字符串小于等于(s1: str, s2: str) -> bool:
    """字符串小于等于"""
    return s1 <= s2


def 字符串大于等于(s1: str, s2: str) -> bool:
    """字符串大于等于"""
    return s1 >= s2