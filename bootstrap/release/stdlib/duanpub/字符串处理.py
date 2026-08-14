"""
字符串处理 — duanpub 桥接模块

基于 Python unicodedata / difflib / re 等库封装，
函数名对齐 duanpub/packages/字符串处理/源.duan。

duanpub 原始包通过 C FFI 实现 Unicode 处理和字符串操作，
本桥接模块用 Python 标准库替代，提供等价的字符串处理功能。
"""

import unicodedata as _unicodedata
import difflib as _difflib
import re as _re


# =============================================================================
# Unicode 规范化
# =============================================================================

def normalizeNFC(文本):
    """将字符串规范化为 NFC 格式"""
    try:
        return _unicodedata.normalize('NFC', 文本)
    except Exception as e:
        raise Exception("normalizeNFC失败: " + str(e))


def normalizeNFD(文本):
    """将字符串规范化为 NFD 格式"""
    try:
        return _unicodedata.normalize('NFD', 文本)
    except Exception as e:
        raise Exception("normalizeNFD失败: " + str(e))


def isCombiningChar(字符):
    """判断字符是否为组合字符"""
    if len(字符) != 1:
        return False
    try:
        return _unicodedata.combining(字符) != 0
    except Exception:
        return False


# =============================================================================
# UTF-8 编码转换
# =============================================================================

def toUTF8(文本):
    """将字符串转为 UTF-8 字节"""
    try:
        return 文本.encode('utf-8')
    except Exception as e:
        raise Exception("toUTF8失败: " + str(e))


def fromUTF8(数据):
    """将 UTF-8 字节转为字符串"""
    if isinstance(数据, str):
        return 数据
    try:
        return 数据.decode('utf-8')
    except Exception as e:
        raise Exception("fromUTF8失败: " + str(e))


# =============================================================================
# 模板插值
# =============================================================================

def templateInterpolate(模板, 变量):
    """模板插值，将 {key} 替换为变量中的值"""
    try:
        result = 模板
        for key, value in 变量.items():
            result = result.replace('{' + key + '}', str(value))
        return result
    except Exception as e:
        raise Exception("templateInterpolate失败: " + str(e))


# =============================================================================
# 模糊匹配
# =============================================================================

def editDistance(s1, s2):
    """计算两个字符串的编辑距离（Levenshtein）"""
    if not isinstance(s1, str) or not isinstance(s2, str):
        raise Exception("editDistance失败: 输入必须是字符串")
    # 使用动态规划计算编辑距离
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1
    return dp[m][n]


def fuzzyMatch(查询, 文本):
    """模糊匹配：检查文本是否包含查询（不区分大小写）"""
    if not isinstance(查询, str) or not isinstance(文本, str):
        return False
    return 查询.lower() in 文本.lower()


def fuzzyMatchSimilarity(查询, 文本):
    """模糊匹配相似度，返回 0.0-1.0 的值"""
    if not isinstance(查询, str) or not isinstance(文本, str):
        return 0.0
    # 使用 difflib 的相似度
    return _difflib.SequenceMatcher(None, 查询.lower(), 文本.lower()).ratio()


# =============================================================================
# 字符串操作
# =============================================================================

def strReverse(文本):
    """反转字符串"""
    try:
        return 文本[::-1]
    except Exception as e:
        raise Exception("strReverse失败: " + str(e))


def strRepeat(文本, 次数):
    """重复字符串"""
    if not isinstance(次数, int) or 次数 < 0:
        raise Exception("strRepeat失败: 次数必须是非负整数")
    try:
        return 文本 * 次数
    except Exception as e:
        raise Exception("strRepeat失败: " + str(e))


def strTruncate(文本, 最大长度, 后缀='...'):
    """截断字符串到指定长度，超出部分加后缀"""
    if not isinstance(最大长度, int) or 最大长度 < 0:
        raise Exception("strTruncate失败: 最大长度必须是正整数")
    try:
        if len(文本) <= 最大长度:
            return 文本
        if 最大长度 <= len(后缀):
            return 文本[:最大长度]
        return 文本[:最大长度 - len(后缀)] + 后缀
    except Exception as e:
        raise Exception("strTruncate失败: " + str(e))


def toCamelCase(文本):
    """转为驼峰命名（小驼峰）"""
    try:
        # 先按分隔符分割
        words = _re.split(r'[-_\s]+', 文本)
        if not words:
            return ''
        result = words[0].lower()
        for w in words[1:]:
            if w:
                result += w[0].upper() + w[1:].lower()
        return result
    except Exception as e:
        raise Exception("toCamelCase失败: " + str(e))


def toSnakeCase(文本):
    """转为蛇形命名"""
    try:
        # 在大写字母前插入下划线，转为小写
        s1 = _re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', 文本)
        s2 = _re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower().replace('-', '_').replace(' ', '_')
    except Exception as e:
        raise Exception("toSnakeCase失败: " + str(e))


def toKebabCase(文本):
    """转为短横线命名"""
    try:
        s = toSnakeCase(文本)
        return s.replace('_', '-')
    except Exception as e:
        raise Exception("toKebabCase失败: " + str(e))


def capitalizeFirst(文本):
    """首字母大写"""
    if not 文本:
        return 文本
    try:
        return 文本[0].upper() + 文本[1:]
    except Exception as e:
        raise Exception("capitalizeFirst失败: " + str(e))


def capitalizeWords(文本):
    """每个单词首字母大写"""
    try:
        return 文本.title()
    except Exception as e:
        raise Exception("capitalizeWords失败: " + str(e))


def trimWhitespace(文本):
    """去除首尾空白"""
    try:
        return 文本.strip()
    except Exception as e:
        raise Exception("trimWhitespace失败: " + str(e))


def trimPrefix(文本, 前缀):
    """去除前缀"""
    try:
        if 文本.startswith(前缀):
            return 文本[len(前缀):]
        return 文本
    except Exception as e:
        raise Exception("trimPrefix失败: " + str(e))


def trimSuffix(文本, 后缀):
    """去除后缀"""
    try:
        if 文本.endswith(后缀):
            return 文本[:-len(后缀)]
        return 文本
    except Exception as e:
        raise Exception("trimSuffix失败: " + str(e))


def countChars(文本):
    """统计字符数"""
    try:
        return len(文本)
    except Exception as e:
        raise Exception("countChars失败: " + str(e))


def countLines(文本):
    """统计行数"""
    if not 文本:
        return 0
    try:
        return len(文本.splitlines())
    except Exception as e:
        raise Exception("countLines失败: " + str(e))


def getSubstring(文本, 起始, 结束=None):
    """获取子字符串"""
    try:
        if 结束 is None:
            return 文本[起始:]
        return 文本[起始:结束]
    except Exception as e:
        raise Exception("getSubstring失败: " + str(e))