"""
正则表达式 — duanpub 桥接模块

基于 Python re 库封装，函数名对齐 duanpub/packages/正则表达式/源.duan。

duanpub 原始包通过 C FFI 调用 PCRE2 库，
本桥接模块用 Python re 模块替代，提供等价的正则匹配、替换、捕获组功能。
"""

import re as _re


# =============================================================================
# 数据结构（对齐 duanpub 源.duan 的结构体定义）
# =============================================================================

class MatchResult:
    """匹配结果"""
    def __init__(self, 匹配成功=False, 整体匹配='', 起始位置=0, 结束位置=0, 捕获组=None):
        self.匹配成功 = 匹配成功
        self.整体匹配 = 整体匹配
        self.起始位置 = 起始位置
        self.结束位置 = 结束位置
        self.捕获组 = 捕获组 or []


class RegexObj:
    """正则对象，封装编译后的正则表达式"""
    def __init__(self, 模式='', 标志=0):
        self.模式 = 模式
        self.标志 = 标志
        self._regex = None

    def _compile(self):
        if self._regex is None:
            try:
                self._regex = _re.compile(self.模式, self.标志)
            except _re.error as e:
                raise Exception("编译正则失败: " + str(e))
        return self._regex


# =============================================================================
# 标志常量
# =============================================================================

忽略大小写 = _re.IGNORECASE
多行模式 = _re.MULTILINE
点号匹配换行 = _re.DOTALL
Unicode匹配 = _re.UNICODE
ASCII匹配 = _re.ASCII
VERBOSE = _re.VERBOSE


# =============================================================================
# 正则对象操作（对齐 duanpub 源.duan）
# =============================================================================

def RegexObjNew(模式, 标志=0):
    """创建正则对象"""
    obj = RegexObj(模式=模式, 标志=标志)
    obj._compile()
    return obj


def RegexObjIsMatch(regex, 文本):
    """判断是否匹配"""
    if not regex or not regex._regex:
        raise Exception("RegexObjIsMatch失败: 无效的正则对象")
    return bool(regex._regex.search(文本))


def RegexObjSearch(regex, 文本):
    """搜索第一个匹配，返回 MatchResult"""
    if not regex or not regex._regex:
        raise Exception("RegexObjSearch失败: 无效的正则对象")
    m = regex._regex.search(文本)
    if m is None:
        return MatchResult(匹配成功=False)
    捕获组 = list(m.groups())
    return MatchResult(
        匹配成功=True,
        整体匹配=m.group(0),
        起始位置=m.start(),
        结束位置=m.end(),
        捕获组=捕获组,
    )


def RegexObjSearchAll(regex, 文本):
    """搜索所有匹配，返回 MatchResult 列表"""
    if not regex or not regex._regex:
        raise Exception("RegexObjSearchAll失败: 无效的正则对象")
    结果 = []
    for m in regex._regex.finditer(文本):
        捕获组 = list(m.groups())
        结果.append(MatchResult(
            匹配成功=True,
            整体匹配=m.group(0),
            起始位置=m.start(),
            结束位置=m.end(),
            捕获组=捕获组,
        ))
    return 结果


def RegexObjReplace(regex, 文本, 替换内容, 次数=0):
    """替换匹配内容"""
    if not regex or not regex._regex:
        raise Exception("RegexObjReplace失败: 无效的正则对象")
    return regex._regex.sub(替换内容, 文本, count=次数)


def RegexObjSplit(regex, 文本, 最大分割=0):
    """按正则分割字符串"""
    if not regex or not regex._regex:
        raise Exception("RegexObjSplit失败: 无效的正则对象")
    return regex._regex.split(文本, maxsplit=最大分割)


def RegexObjFree(regex):
    """释放正则对象"""
    if regex:
        regex._regex = None


def MatchResultGroup(match, 组号=0):
    """获取匹配结果的捕获组"""
    if not match or not match.匹配成功:
        return None
    if 组号 == 0:
        return match.整体匹配
    if 组号 < 1 or 组号 > len(match.捕获组):
        return None
    return match.捕获组[组号 - 1]


# =============================================================================
# 便捷函数（中文名）
# =============================================================================

def 创建正则(模式, 忽略大小写_=False, 多行=False, 点匹配换行=False):
    """创建编译后的正则对象"""
    标志 = 0
    if 忽略大小写_:
        标志 |= _re.IGNORECASE
    if 多行:
        标志 |= _re.MULTILINE
    if 点匹配换行:
        标志 |= _re.DOTALL
    try:
        return RegexObjNew(模式, 标志)
    except Exception:
        raise


def 是否匹配(模式, 文本, 标志=0):
    """判断文本是否匹配正则模式"""
    try:
        return bool(_re.search(模式, 文本, 标志))
    except _re.error as e:
        raise Exception("是否匹配失败: " + str(e))


def 搜索(模式, 文本, 标志=0):
    """搜索第一个匹配，返回 MatchResult"""
    try:
        m = _re.search(模式, 文本, 标志)
    except _re.error as e:
        raise Exception("搜索失败: " + str(e))
    if m is None:
        return MatchResult(匹配成功=False)
    return MatchResult(
        匹配成功=True,
        整体匹配=m.group(0),
        起始位置=m.start(),
        结束位置=m.end(),
        捕获组=list(m.groups()),
    )


def 全部搜索(模式, 文本, 标志=0):
    """搜索所有匹配，返回 MatchResult 列表"""
    try:
        结果 = []
        for m in _re.finditer(模式, 文本, 标志):
            结果.append(MatchResult(
                匹配成功=True,
                整体匹配=m.group(0),
                起始位置=m.start(),
                结束位置=m.end(),
                捕获组=list(m.groups()),
            ))
        return 结果
    except _re.error as e:
        raise Exception("全部搜索失败: " + str(e))


def 替换(模式, 文本, 替换内容, 次数=0, 标志=0):
    """替换所有匹配内容"""
    try:
        return _re.sub(模式, 替换内容, 文本, count=次数, flags=标志)
    except _re.error as e:
        raise Exception("替换失败: " + str(e))


def 分割(模式, 文本, 最大分割=0, 标志=0):
    """按正则分割字符串"""
    try:
        return _re.split(模式, 文本, maxsplit=最大分割, flags=标志)
    except _re.error as e:
        raise Exception("分割失败: " + str(e))


def 提取所有(模式, 文本, 标志=0):
    """提取所有匹配的字符串列表"""
    try:
        return _re.findall(模式, 文本, 标志)
    except _re.error as e:
        raise Exception("提取所有失败: " + str(e))


def 转义特殊字符(文本):
    """转义正则表达式中的特殊字符"""
    return _re.escape(文本)
