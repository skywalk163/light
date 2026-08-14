"""
段言标准库 - 排版模块

提供中英文混排空格、全半角转换、标点规范、引号规范、排版检查等功能。
参考《中文文案排版指北》。
"""

import re
import unicodedata


# =============================================================================
# 中英文混排
# =============================================================================

# CJK 字符正则
_CJK_PATTERN = re.compile(
    r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff'
    r'\U00020000-\U0002a6df\U0002a700-\U0002b73f'
    r'\u3040-\u30ff\uac00-\ud7af'  # 日文假名、韩文
    r']'
)

# 中文字符与英文/数字之间插入空格
_SPACE_PATTERN_1 = re.compile(r'([\u4e00-\u9fff\u3400-\u4dbf])([a-zA-Z0-9])')
_SPACE_PATTERN_2 = re.compile(r'([a-zA-Z0-9])([\u4e00-\u9fff\u3400-\u4dbf])')


def 插入中英文空格(文本):
    """
    在中文字符和英文/数字之间插入空格。
    
    示例: "你好world" -> "你好 world"
    
    参数:
        文本: 待处理的文本
    
    返回: 处理后的文本
    """
    result = _SPACE_PATTERN_2.sub(r'\1 \2', 文本)
    result = _SPACE_PATTERN_1.sub(r'\1 \2', result)
    return result


# =============================================================================
# 全半角转换
# =============================================================================

# 半角 -> 全角 映射
_HALF_TO_FULL = {}
for i in range(0x21, 0x7F):
    _HALF_TO_FULL[chr(i)] = chr(i + 0xFEE0)
_HALF_TO_FULL[' '] = '\u3000'  # 空格特殊处理

# 全角 -> 半角 映射
_FULL_TO_HALF = {v: k for k, v in _HALF_TO_FULL.items()}


def 转全角(文本):
    """
    将文本中的半角字符转为全角字符。
    
    参数:
        文本: 待转换的文本
    
    返回: 全角文本
    """
    result = []
    for char in 文本:
        if char in _HALF_TO_FULL:
            result.append(_HALF_TO_FULL[char])
        else:
            result.append(char)
    return ''.join(result)


def 转半角(文本):
    """
    将文本中的全角字符转为半角字符。
    
    参数:
        文本: 待转换的文本
    
    返回: 半角文本
    """
    result = []
    for char in 文本:
        if char in _FULL_TO_HALF:
            result.append(_FULL_TO_HALF[char])
        else:
            result.append(char)
    return ''.join(result)


# =============================================================================
# 标点规范
# =============================================================================

# 英文标点 -> 中文标点（在中文上下文中）
_EN_TO_ZH_PUNCT = {
    ',': '\uff0c',  # ，
    '.': '\u3002',  # 。
    '!': '\uff01',  # ！
    '?': '\uff1f',  # ？
    ';': '\uff1b',  # ；
    ':': '\uff1a',  # ：
    '(': '\uff08',  # （
    ')': '\uff09',  # ）
    '[': '\u3010',  # 【
    ']': '\u3011',  # 】
    '<': '\u300a',  # 《
    '>': '\u300b',  # 》
}


def _is_cjk_context(文本, 位置, 方向='both'):
    """判断某个位置附近是否有中文字符"""
    length = len(文本)
    
    if direction_check := 'both':
        check_before = 位置 > 0
        check_after = 位置 < length - 1
    elif direction_check := 'before':
        check_before = 位置 > 0
        check_after = False
    else:
        check_before = False
        check_after = 位置 < length - 1
    
    if check_before:
        prev_char = 文本[位置 - 1]
        if _CJK_PATTERN.match(prev_char):
            return True
    
    if check_after:
        next_char = 文本[位置 + 1]
        if _CJK_PATTERN.match(next_char):
            return True
    
    return False


def 规范化标点(文本):
    """
    在中文上下文中，将英文标点替换为中文标点。
    
    仅在标点前后有中文字符时替换，避免误改英文句子中的标点。
    
    参数:
        文本: 待处理的文本
    
    返回: 处理后的文本
    """
    result = []
    for i, char in enumerate(文本):
        if char in _EN_TO_ZH_PUNCT:
            # 检查前后是否有中文字符
            if _is_cjk_context(文本, i):
                result.append(_EN_TO_ZH_PUNCT[char])
            else:
                result.append(char)
        else:
            result.append(char)
    return ''.join(result)


# =============================================================================
# 引号规范
# =============================================================================

def 规范化引号(文本):
    """
    将英文直引号转为中文弯引号。
    
    "..." -> "..."
    '...' -> '...'
    
    参数:
        文本: 待处理的文本
    
    返回: 处理后的文本
    """
    result = []
    in_double = False
    in_single = False
    
    for char in 文本:
        if char == '"':
            if in_double:
                result.append('\u201d')  # 右双引号
                in_double = False
            else:
                result.append('\u201c')  # 左双引号
                in_double = True
        elif char == "'":
            if in_single:
                result.append('\u2019')  # 右单引号
                in_single = False
            else:
                result.append('\u2018')  # 左单引号
                in_single = True
        else:
            result.append(char)
    
    return ''.join(result)


# =============================================================================
# 排版检查
# =============================================================================

def 检查排版(文本):
    """
    检查文本中的排版问题。
    
    返回: 问题列表，每个元素是 {类型, 位置, 描述, 建议}
    """
    issues = []
    
    # 1. 检查中英文之间缺少空格
    for match in _SPACE_PATTERN_1.finditer(文本):
        issues.append({
            '类型': '缺少空格',
            '位置': match.start(),
            '描述': f"中文'{match.group(1)}'与英文'{match.group(2)}'之间缺少空格",
            '建议': '在中英文之间插入空格',
        })
    
    for match in _SPACE_PATTERN_2.finditer(文本):
        issues.append({
            '类型': '缺少空格',
            '位置': match.start(),
            '描述': f"英文'{match.group(1)}'与中文'{match.group(2)}'之间缺少空格",
            '建议': '在中英文之间插入空格',
        })
    
    # 2. 检查全角英文
    full_width_pattern = re.compile(r'[\uff01-\uff5e]')
    for match in full_width_pattern.finditer(文本):
        char = match.group()
        half = _FULL_TO_HALF.get(char, '?')
        issues.append({
            '类型': '全角英数字',
            '位置': match.start(),
            '描述': f"使用了全角字符'{char}'",
            '建议': f"替换为半角'{half}'",
        })
    
    # 3. 检查重复标点
    repeat_pattern = re.compile(r'([。！？，；：])\1{1,}')
    for match in repeat_pattern.finditer(文本):
        issues.append({
            '类型': '重复标点',
            '位置': match.start(),
            '描述': f"重复使用了'{match.group(1)}'",
            '建议': '标点符号不应重复',
        })
    
    # 4. 检查中文文本中使用英文标点
    for i, char in enumerate(文本):
        if char in _EN_TO_ZH_PUNCT:
            if _is_cjk_context(文本, i):
                issues.append({
                    '类型': '标点不一致',
                    '位置': i,
                    '描述': f"中文上下文中使用了英文标点'{char}'",
                    '建议': f"替换为中文标点'{_EN_TO_ZH_PUNCT[char]}'",
                })
    
    # 5. 检查直引号
    if '"' in 文本 or "'" in 文本:
        issues.append({
            '类型': '引号不规范',
            '位置': 文本.find('"') if '"' in 文本 else 文本.find("'"),
            '描述': '使用了英文直引号',
            '建议': '替换为中文弯引号',
        })
    
    # 6. 检查连续空格
    multi_space_pattern = re.compile(r' {2,}')
    for match in multi_space_pattern.finditer(文本):
        issues.append({
            '类型': '连续空格',
            '位置': match.start(),
            '描述': f"连续{len(match.group())}个空格",
            '建议': '使用单个空格',
        })
    
    return issues


def 自动排版(文本):
    """
    一键执行全部排版优化：
    1. 插入中英文空格
    2. 全角英数字转半角
    3. 规范化标点
    4. 规范化引号
    
    参数:
        文本: 待处理的文本
    
    返回: 排版后的文本
    """
    # 先转半角英数字
    result = 转半角(文本)
    # 再插入中英文空格
    result = 插入中英文空格(result)
    # 规范化标点
    result = 规范化标点(result)
    # 规范化引号
    result = 规范化引号(result)
    return result


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    '插入中英文空格',
    '转全角', '转半角',
    '规范化标点',
    '规范化引号',
    '检查排版',
    '自动排版',
]
