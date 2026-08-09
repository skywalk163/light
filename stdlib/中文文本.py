"""
光明标准库 - 中文文本模块

提供中文分词、拼音转换、简繁转换、标点处理、笔画部首、中文数字等功能。

依赖: pypinyin, opencc-python-reimplemented
"""

import re
import unicodedata

try:
    from pypinyin import pinyin as _pinyin, Style as _PinyinStyle
    _HAS_PINYIN = True
except ImportError:
    _HAS_PINYIN = False

try:
    from opencc import OpenCC as _OpenCC
    _HAS_OPENCC = True
except ImportError:
    _HAS_OPENCC = False


# =============================================================================
# 中文分词
# =============================================================================

# CJK Unicode 范围
_CJK_RANGES = [
    (0x4E00, 0x9FFF),    # CJK 统一表意文字
    (0x3400, 0x4DBF),    # CJK 统一表意文字扩展A
    (0x20000, 0x2A6DF),  # CJK 统一表意文字扩展B
    (0x2A700, 0x2B73F),  # CJK 统一表意文字扩展C
    (0x2B740, 0x2B81F),  # CJK 统一表意文字扩展D
]

def _is_cjk(char):
    """判断字符是否为 CJK 汉字"""
    cp = ord(char)
    for start, end in _CJK_RANGES:
        if start <= cp <= end:
            return True
    return False


def 中文分词(文本):
    """
    简易中文分词：按非中文字符（空格、标点、英文）切分中文文本。
    
    返回: 列表，每个元素是一个词或字符块
    """
    tokens = []
    buffer = ""
    for char in 文本:
        if _is_cjk(char):
            buffer += char
        else:
            if buffer:
                tokens.append(buffer)
                buffer = ""
            tokens.append(char)
    if buffer:
        tokens.append(buffer)
    # 过滤空白
    return [t for t in tokens if t.strip()]


def 中文逐字(文本):
    """将中文文本拆分为单个汉字列表"""
    return [char for char in 文本 if _is_cjk(char)]


def 汉字数量(文本):
    """统计文本中的汉字数量"""
    return sum(1 for char in 文本 if _is_cjk(char))


# =============================================================================
# 拼音转换
# =============================================================================

def 转拼音(文本, 首字母模式=False):
    """
    将中文文本转为拼音。
    
    参数:
        文本: 中文文本
        首字母模式: True 时只返回首字母
    
    返回: 拼音字符串（多字之间用空格分隔）
    """
    if not _HAS_PINYIN:
        raise RuntimeError("拼音转换需要 pypinyin 库，请执行: pip install pypinyin")
    
    if 首字母模式:
        result = _pinyin(文本, style=_PinyinStyle.FIRST_LETTER)
        return "".join([item[0] for item in result])
    else:
        result = _pinyin(文本, style=_PinyinStyle.NORMAL)
        return " ".join([item[0] for item in result])


def 转拼音列表(文本):
    """
    将中文文本转为拼音列表（每个字一个拼音）。
    
    返回: 拼音列表
    """
    if not _HAS_PINYIN:
        raise RuntimeError("拼音转换需要 pypinyin 库，请执行: pip install pypinyin")
    
    result = _pinyin(文本, style=_PinyinStyle.NORMAL)
    return [item[0] for item in result]


def 转带声调拼音(文本):
    """
    将中文文本转为带声调的拼音。
    
    返回: 带声调拼音字符串
    """
    if not _HAS_PINYIN:
        raise RuntimeError("拼音转换需要 pypinyin 库，请执行: pip install pypinyin")
    
    result = _pinyin(文本, style=_PinyinStyle.TONE)
    return " ".join([item[0] for item in result])


# =============================================================================
# 简繁转换
# =============================================================================

def 简转繁(文本):
    """简体中文转繁体中文"""
    if not _HAS_OPENCC:
        raise RuntimeError("简繁转换需要 opencc-python-reimplemented 库，请执行: pip install opencc-python-reimplemented")
    
    cc = _OpenCC('s2t')
    return cc.convert(文本)


def 繁转简(文本):
    """繁体中文转简体中文"""
    if not _HAS_OPENCC:
        raise RuntimeError("简繁转换需要 opencc-python-reimplemented 库，请执行: pip install opencc-python-reimplemented")
    
    cc = _OpenCC('t2s')
    return cc.convert(文本)


# =============================================================================
# 标点处理
# =============================================================================

# 中文标点 -> 英文标点
_ZH_PUNCT_MAP = {
    '，': ',', '。': '.', '！': '!', '？': '?',
    '；': ';', '：': ':', '、': ',',
    '（': '(', '）': ')', '【': '[', '】': ']',
    '《': '<', '》': '>', '「': '"', '」': '"',
    '『': "'", '』': "'", '〔': '(', '〕': ')',
    '〈': '<', '〉': '>',
    '～': '~', '…': '...',
    '—': '-', '–': '-',
}

# 英文标点 -> 中文标点（独立定义，确保一一对应）
_EN_PUNCT_MAP = {
    ',': '，', '.': '。', '!': '！', '?': '？',
    ';': '；', ':': '：',
    '(': '（', ')': '）', '[': '【', ']': '】',
    '<': '《', '>': '》',
    '~': '～',
}


def 中文标点转英文(文本):
    """将文本中的中文标点替换为英文标点"""
    result = 文本
    for zh, en in _ZH_PUNCT_MAP.items():
        result = result.replace(zh, en)
    return result


def 英文标点转中文(文本):
    """将文本中的英文标点替换为中文标点"""
    result = 文本
    for en, zh in _EN_PUNCT_MAP.items():
        result = result.replace(en, zh)
    return result


# =============================================================================
# 笔画 / 部首
# =============================================================================

# 常见汉字笔画数（覆盖常用3500字的部分采样）
_STROKE_DATA = {
    '一': 1, '丨': 1, '丶': 1, '丿': 1, '乙': 1, '亅': 1,
    '二': 2, '十': 2, '丁': 2, '厂': 2, '七': 2, '人': 2,
    '入': 2, '八': 2, '九': 2, '几': 2, '儿': 2, '了': 2,
    '力': 2, '乃': 2, '刀': 2, '又': 2,
    '三': 3, '干': 3, '于': 3, '亏': 3, '士': 3, '工': 3,
    '土': 3, '才': 3, '寸': 3, '下': 3, '大': 3, '丈': 3,
    '与': 3, '万': 3, '上': 3, '小': 3, '口': 3, '囗': 3,
    '山': 3, '千': 3, '乞': 3, '川': 3, '亿': 3, '个': 3,
    '勺': 3, '久': 3, '凡': 3, '及': 3, '夕': 3, '丸': 3,
    '么': 3, '广': 3, '亡': 3, '门': 3, '义': 3, '之': 3,
    '尸': 3, '弓': 3, '己': 3, '已': 3, '子': 3, '卫': 3,
    '也': 3, '女': 3, '飞': 3, '习': 3, '马': 3, '乡': 3,
    '四': 5, '五': 4, '六': 4, '七': 2, '八': 2, '九': 2,
    '十': 2, '百': 6, '千': 3, '万': 3,
    '中': 4, '国': 8, '人': 2, '天': 4, '地': 6,
    '日': 4, '月': 4, '星': 9, '水': 4, '火': 4,
    '山': 3, '河': 8, '海': 10, '风': 4, '雨': 8,
    '春': 9, '夏': 10, '秋': 9, '冬': 5,
    '东': 5, '南': 9, '西': 6, '北': 5,
    '上': 3, '下': 3, '左': 5, '右': 5,
    '前': 9, '后': 6, '内': 4, '外': 5,
    '好': 6, '你': 7, '我': 7, '他': 5, '她': 6,
    '们': 5, '的': 8, '是': 9, '在': 6, '有': 6,
    '不': 4, '了': 2, '为': 4, '会': 6, '说': 9,
    '看': 9, '想': 13, '做': 11, '走': 7, '来': 7,
    '去': 5, '回': 6, '出': 5, '入': 2,
    '爱': 10, '情': 11, '心': 4, '生': 5, '死': 6,
    '多': 6, '少': 4, '大': 3, '小': 3, '高': 10,
    '低': 7, '长': 4, '短': 12, '新': 13, '旧': 5,
    '美': 9, '丽': 7, '花': 7, '草': 9, '树': 9,
    '林': 8, '森': 12, '金': 8, '银': 11, '铜': 11,
    '铁': 10, '玉': 5, '石': 5, '土': 3, '木': 4,
}


def 笔画数(字符):
    """
    获取单个汉字的笔画数。
    
    返回: 笔画数（整数），如果无法识别返回 -1
    """
    if not 字符 or len(字符) != 1:
        raise ValueError("笔画数函数需要单个汉字")
    
    if not _is_cjk(字符):
        raise ValueError(f"'{字符}' 不是汉字")
    
    # 先查本地数据
    if 字符 in _STROKE_DATA:
        return _STROKE_DATA[字符]
    
    # 尝试使用 unicodedata
    try:
        # CJK 统一表意文字的笔画数可通过 Unicode 名推断部分
        # 但 unicodedata 不直接提供笔画数
        pass
    except Exception:
        pass
    
    return -1


# 常见部首映射
_RADICAL_DATA = {
    '一': '一', '二': '一', '三': '一', '十': '十', '丁': '一',
    '人': '人', '入': '入', '八': '八', '大': '大', '小': '小',
    '口': '口', '囗': '囗', '土': '土', '士': '士', '工': '工',
    '山': '山', '日': '日', '月': '月', '木': '木', '水': '水',
    '火': '火', '石': '石', '金': '金', '女': '女', '子': '子',
    '心': '心', '手': '手', '目': '目', '田': '田', '力': '力',
    '刀': '刀', '弓': '弓', '车': '车', '马': '马', '犬': '犬',
    '鸟': '鸟', '鱼': '鱼', '虫': '虫', '龙': '龙',
    '你': '人', '他': '人', '好': '女', '她': '女',
    '的': '白', '是': '日', '在': '土', '有': '月',
    '来': '木', '回': '囗', '问': '口', '听': '口',
    '想': '心', '情': '心', '爱': '心', '恨': '心',
    '说': '言', '读': '言', '写': '宀', '字': '子',
    '花': '艹', '草': '艹', '树': '木', '林': '木',
    '河': '水', '海': '水', '江': '水', '湖': '水',
}


def 部首(字符):
    """
    获取单个汉字的部首。
    
    返回: 部首字符串，如果无法识别返回空字符串
    """
    if not 字符 or len(字符) != 1:
        raise ValueError("部首函数需要单个汉字")
    
    if not _is_cjk(字符):
        raise ValueError(f"'{字符}' 不是汉字")
    
    return _RADICAL_DATA.get(字符, "")


# =============================================================================
# 中文数字
# =============================================================================

_DIGITS = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
_DIGITS_CAPITAL = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
_UNITS = ['', '十', '百', '千']
_UNITS_CAPITAL = ['', '拾', '佰', '仟']
_LARGE_UNITS = ['', '万', '亿', '万亿']


def 数字转中文(数值, 大写=False):
    """
    将数字转为中文表示。
    
    参数:
        数值: 整数
        大写: True 使用大写数字（壹贰叁...），用于财务
    
    返回: 中文数字字符串
    """
    if not isinstance(数值, int):
        try:
            数值 = int(数值)
        except (ValueError, TypeError):
            raise ValueError("数字转中文需要整数")
    
    if 数值 == 0:
        return _DIGITS_CAPITAL[0] if 大写 else _DIGITS[0]
    
    digits = _DIGITS_CAPITAL if 大写 else _DIGITS
    units = _UNITS_CAPITAL if 大写 else _UNITS
    
    if 数值 < 0:
        return "负" + 数字转中文(-数值, 大写)
    
    # 处理小数部分
    result = ""
    
    # 分组处理（每4位一组）
    groups = []
    n = 数值
    while n > 0:
        groups.append(n % 10000)
        n = n // 10000
    
    for i in range(len(groups) - 1, -1, -1):
        group = groups[i]
        if group == 0:
            continue
        
        # 处理一组（4位数）
        group_str = ""
        for j in range(3, -1, -1):
            d = (group // (10 ** j)) % 10
            if d == 0:
                if group_str and not group_str.endswith(digits[0]):
                    group_str += digits[0]
            else:
                group_str += digits[d] + units[j]
        
        # 去除尾部零
        group_str = group_str.rstrip(digits[0])
        
        result += group_str + _LARGE_UNITS[i]
    
    # 特殊处理：十一 ~ 十九 省略开头的"一"
    if 10 <= 数值 <= 19:
        result = result[1:]  # 去掉开头的"一"
    
    return result


def 中文转数字(文本):
    """
    将中文数字转为阿拉伯数字。
    
    参数:
        文本: 中文数字字符串（如"三千五百二十一"）
    
    返回: 整数
    """
    digit_map = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '壹': 1, '贰': 2, '叁': 3, '肆': 4,
        '伍': 5, '陆': 6, '柒': 7, '捌': 8, '玖': 9,
        '十': 10, '拾': 10, '百': 100, '佰': 100,
        '千': 1000, '仟': 1000,
    }
    large_map = {
        '万': 10000, '萬': 10000,
        '亿': 100000000, '億': 100000000,
    }
    
    # 合并两种 map
    all_map = {**digit_map, **large_map}
    
    if 文本 in all_map:
        return all_map[文本]
    
    result = 0
    current = 0
    total = 0
    
    for char in 文本:
        if char in digit_map:
            val = digit_map[char]
            if val >= 10:
                if current == 0:
                    current = 1
                result += current * val
                current = 0
            else:
                current = val
        elif char in large_map:
            if current == 0 and result == 0:
                result = 1
            result = (result + current) * large_map[char]
            total += result
            result = 0
            current = 0
    
    return total + result + current


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 分词
    '中文分词', '中文逐字', '汉字数量',
    # 拼音
    '转拼音', '转拼音列表', '转带声调拼音',
    # 简繁
    '简转繁', '繁转简',
    # 标点
    '中文标点转英文', '英文标点转中文',
    # 笔画部首
    '笔画数', '部首',
    # 中文数字
    '数字转中文', '中文转数字',
]
