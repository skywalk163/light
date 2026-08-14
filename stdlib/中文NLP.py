"""
段言标准库 - 中文 NLP 工具模块

提供综合的中文自然语言处理功能：
- 分词（基于 jieba/内置词典）
- 拼音转换（基于 pypinyin/内置映射）
- 简繁转换（基于 opencc/内置映射）
- 文本统计
- 数字与金额转换
- 文本处理工具

依赖（可选）:
  pip install jieba          # 分词、关键词提取
  pip install pypinyin       # 拼音转换
  pip install opencc-python-reimplemented  # 简繁转换
"""

import re
import math
from collections import Counter
from typing import List, Optional, Tuple, Dict, Set, Union

# =============================================================================
# 可选依赖检测
# =============================================================================

try:
    import jieba as _jieba
    import jieba.posseg as _posseg
    import jieba.analyse as _analyse
    _HAS_JIEBA = True
except ImportError:
    _HAS_JIEBA = False

try:
    from pypinyin import pinyin as _pypinyin, Style as _PinyinStyle, lazy_pinyin as _lazy_pinyin
    _HAS_PYPINYIN = True
except ImportError:
    _HAS_PYPINYIN = False

try:
    from opencc import OpenCC as _OpenCC
    _HAS_OPENCC = True
except ImportError:
    _HAS_OPENCC = False


# =============================================================================
# CJK 字符范围
# =============================================================================

_CJK_RANGES = [
    (0x4E00, 0x9FFF),    # CJK 统一表意文字
    (0x3400, 0x4DBF),    # CJK 扩展A
    (0x20000, 0x2A6DF),  # CJK 扩展B
    (0x2A700, 0x2B73F),  # CJK 扩展C
    (0x2B740, 0x2B81F),  # CJK 扩展D
    (0x2B820, 0x2CEAF),  # CJK 扩展E
    (0x2CEB0, 0x2EBEF),  # CJK 扩展F
    (0x30000, 0x3134F),  # CJK 扩展G
    (0x31350, 0x323AF),  # CJK 扩展H
]

# 中文标点 Unicode 范围
_CJK_PUNCT_RANGES = [
    (0x3000, 0x303F),   # CJK 符号和标点
    (0xFE30, 0xFE4F),   # CJK 兼容形式
    (0xFF00, 0xFFEF),   # 全角 ASCII / 全角标点
    (0x2000, 0x206F),   # 通用标点
]


def _is_cjk(char: str) -> bool:
    """判断字符是否为 CJK 汉字"""
    cp = ord(char)
    for start, end in _CJK_RANGES:
        if start <= cp <= end:
            return True
    return False


def _is_cjk_punct(char: str) -> bool:
    """判断字符是否为中文标点"""
    cp = ord(char)
    for start, end in _CJK_PUNCT_RANGES:
        if start <= cp <= end:
            return True
    # 额外常见中文标点
    return char in '，。、！？：；""''（）【】《》—…·～「」『』〔〕〈〉'


# =============================================================================
# 1. 分词 (Tokenization)
# =============================================================================

def 分词精确模式(文本: str) -> List[str]:
    """
    使用精确模式分词（jieba精确模式），力求最精确地切分句子。

    参数:
        文本: 待分词文本

    返回: 词语列表

    依赖: jieba（无依赖时按字符切分）
    """
    if not 文本:
        return []
    if _HAS_JIEBA:
        return list(_jieba.cut(文本, cut_all=False))
    # 回退：按 CJK 字符块和非 CJK 字符块切分
    return _fallback_segment(文本)


def 分词全模式(文本: str) -> List[str]:
    """
    使用全模式分词，把句子中所有可能的词语都扫描出来，速度很快，但会有冗余。

    参数:
        文本: 待分词文本

    返回: 词语列表

    依赖: jieba（无依赖时按字符切分）
    """
    if not 文本:
        return []
    if _HAS_JIEBA:
        return list(_jieba.cut(文本, cut_all=True))
    return _fallback_segment(文本)


def 分词搜索引擎模式(文本: str) -> List[str]:
    """
    使用搜索引擎模式分词，在精确模式基础上对长词再次切分。

    参数:
        文本: 待分词文本

    返回: 词语列表

    依赖: jieba（无依赖时按字符切分）
    """
    if not 文本:
        return []
    if _HAS_JIEBA:
        return list(_jieba.cut_for_search(文本))
    return _fallback_segment(文本)


def _fallback_segment(文本: str) -> List[str]:
    """回退分词：按 CJK 字符块和空白分隔"""
    tokens = []
    buf = ""
    for ch in 文本:
        if _is_cjk(ch):
            buf += ch
        else:
            if buf:
                tokens.append(buf)
                buf = ""
            if ch.strip():
                tokens.append(ch)
    if buf:
        tokens.append(buf)
    return tokens


def 添加自定义词典(词典路径: str) -> None:
    """
    添加自定义词典文件。

    参数:
        词典路径: 词典文件路径（每行一个词，可包含词频和词性）

    依赖: jieba（无依赖时静默忽略）
    """
    if _HAS_JIEBA:
        _jieba.load_userdict(词典路径)


def 添加自定义词语(词: str, 词频: int = 0, 词性: str = None) -> None:
    """
    动态添加自定义词语。

    参数:
        词: 词语
        词频: 词频（可选）
        词性: 词性标注（可选）

    依赖: jieba（无依赖时静默忽略）
    """
    if _HAS_JIEBA:
        if 词性:
            _jieba.add_word(词, freq=词频, tag=词性)
        else:
            _jieba.add_word(词, freq=词频)


def 删除自定义词语(词: str) -> None:
    """
    删除自定义词语。

    参数:
        词: 要删除的词语

    依赖: jieba（无依赖时静默忽略）
    """
    if _HAS_JIEBA:
        _jieba.del_word(词)


def 词性标注(文本: str) -> List[Tuple[str, str]]:
    """
    词性标注：返回 (词语, 词性) 列表。

    参数:
        文本: 待标注文本

    返回: [(词语, 词性), ...] 列表

    依赖: jieba（无依赖时返回 (词语, 'x') 占位）
    """
    if not 文本:
        return []
    if _HAS_JIEBA:
        return [(w, t) for w, t in _posseg.cut(文本)]
    return [(w, 'x') for w in _fallback_segment(文本)]


def 提取关键词TFIDF(文本: str, 数量: int = 10) -> List[Tuple[str, float]]:
    """
    基于 TF-IDF 提取关键词。

    参数:
        文本: 待提取文本
        数量: 返回关键词数量

    返回: [(关键词, 权重), ...] 列表

    依赖: jieba（无依赖时使用词频统计）
    """
    if not 文本:
        return []
    if _HAS_JIEBA:
        return _analyse.extract_tags(文本, topK=数量, withWeight=True)
    # 回退：使用词频统计
    words = _fallback_segment(文本)
    total = len(words)
    counter = Counter(words)
    result = []
    for w, cnt in counter.most_common(数量):
        result.append((w, cnt / total if total > 0 else 0.0))
    return result


def 提取关键词TextRank(文本: str, 数量: int = 10) -> List[Tuple[str, float]]:
    """
    基于 TextRank 提取关键词。

    参数:
        文本: 待提取文本
        数量: 返回关键词数量

    返回: [(关键词, 权重), ...] 列表

    依赖: jieba（无依赖时使用词频统计）
    """
    if not 文本:
        return []
    if _HAS_JIEBA:
        return _analyse.textrank(文本, topK=数量, withWeight=True)
    return 提取关键词TFIDF(文本, 数量)


def 分词带位置(文本: str) -> List[Tuple[str, int, int]]:
    """
    分词并返回每个词在文本中的起始和结束位置。

    参数:
        文本: 待分词文本

    返回: [(词语, 起始位置, 结束位置), ...]

    依赖: jieba（无依赖时按字符块切分）
    """
    if not 文本:
        return []
    if _HAS_JIEBA:
        result = []
        for w, start, end in _jieba.tokenize(文本):
            result.append((w, start, end))
        return result
    # 回退实现
    result = []
    pos = 0
    for w in _fallback_segment(文本):
        start = 文本.find(w, pos)
        if start == -1:
            start = pos
        end = start + len(w)
        result.append((w, start, end))
        pos = end
    return result


# =============================================================================
# 2. 拼音转换 (Pinyin)
# =============================================================================

# 基础汉字到拼音映射（常用字）
_BASIC_PINYIN_MAP = {
    '我': 'wo', '你': 'ni', '他': 'ta', '她': 'ta', '它': 'ta',
    '们': 'men', '的': 'de', '了': 'le', '是': 'shi', '不': 'bu',
    '在': 'zai', '有': 'you', '人': 'ren', '这': 'zhe', '那': 'na',
    '和': 'he', '就': 'jiu', '也': 'ye', '要': 'yao', '会': 'hui',
    '一': 'yi', '二': 'er', '三': 'san', '四': 'si', '五': 'wu',
    '六': 'liu', '七': 'qi', '八': 'ba', '九': 'jiu', '十': 'shi',
    '上': 'shang', '下': 'xia', '大': 'da', '小': 'xiao', '中': 'zhong',
    '国': 'guo', '北': 'bei', '京': 'jing', '天': 'tian', '地': 'di',
    '日': 'ri', '月': 'yue', '水': 'shui', '火': 'huo', '山': 'shan',
    '石': 'shi', '木': 'mu', '金': 'jin', '土': 'tu', '风': 'feng',
    '云': 'yun', '雨': 'yu', '雪': 'xue', '花': 'hua', '草': 'cao',
    '树': 'shu', '鸟': 'niao', '鱼': 'yu', '马': 'ma', '牛': 'niu',
    '羊': 'yang', '虫': 'chong', '龙': 'long', '来': 'lai', '去': 'qu',
    '说': 'shuo', '话': 'hua', '写': 'xie', '读': 'du', '看': 'kan',
    '听': 'ting', '想': 'xiang', '知': 'zhi', '道': 'dao', '好': 'hao',
    '坏': 'huai', '多': 'duo', '少': 'shao', '长': 'chang', '短': 'duan',
    '高': 'gao', '低': 'di', '新': 'xin', '旧': 'jiu', '美': 'mei',
    '丽': 'li', '白': 'bai', '黑': 'hei', '红': 'hong', '绿': 'lv',
    '蓝': 'lan', '黄': 'huang', '青': 'qing', '紫': 'zi', '灰': 'hui',
    '开': 'kai', '关': 'guan', '门': 'men', '窗': 'chuang', '桌': 'zhuo',
    '椅': 'yi', '床': 'chuang', '房': 'fang', '家': 'jia', '城': 'cheng',
    '市': 'shi', '村': 'cun', '前': 'qian', '后': 'hou', '左': 'zuo',
    '右': 'you', '里': 'li', '外': 'wai', '东': 'dong', '南': 'nan',
    '西': 'xi', '春': 'chun', '夏': 'xia', '秋': 'qiu', '冬': 'dong',
    '年': 'nian', '月': 'yue', '日': 'ri', '时': 'shi', '分': 'fen',
    '秒': 'miao', '今': 'jin', '明': 'ming', '昨': 'zuo', '早': 'zao',
    '晚': 'wan', '午': 'wu', '夜': 'ye', '饭': 'fan', '菜': 'cai',
    '汤': 'tang', '茶': 'cha', '酒': 'jiu', '水': 'shui', '果': 'guo',
    '姓': 'xing', '名': 'ming', '字': 'zi', '文': 'wen',
    '中': 'zhong', '华': 'hua', '人': 'ren', '民': 'min', '共': 'gong',
    '产': 'chan', '党': 'dang', '军': 'jun', '政': 'zheng', '法': 'fa',
    '学': 'xue', '校': 'xiao', '生': 'sheng', '工': 'gong', '作': 'zuo',
    '用': 'yong', '能': 'neng', '力': 'li', '机': 'ji', '电': 'dian',
    '信': 'xin', '息': 'xi', '网': 'wang', '络': 'luo', '数': 'shu',
    '据': 'ju', '算': 'suan', '编': 'bian', '程': 'cheng', '序': 'xu',
    '世': 'shi', '界': 'jie', '全': 'quan', '部': 'bu', '种': 'zhong',
    '类': 'lei', '型': 'xing', '式': 'shi', '方': 'fang', '向': 'xiang',
    '量': 'liang', '度': 'du', '间': 'jian', '空': 'kong', '时': 'shi',
    '问': 'wen', '题': 'ti', '答': 'da', '案': 'an', '需': 'xu',
    '求': 'qiu', '解': 'jie', '决': 'jue', '定': 'ding', '义': 'yi',
}

# 带声调拼音映射
_BASIC_PINYIN_TONE_MAP = {
    '我': 'wǒ', '你': 'nǐ', '他': 'tā', '她': 'tā', '它': 'tā',
    '们': 'men', '的': 'de', '了': 'le', '是': 'shì', '不': 'bù',
    '在': 'zài', '有': 'yǒu', '人': 'rén', '这': 'zhè', '那': 'nà',
    '和': 'hé', '就': 'jiù', '也': 'yě', '要': 'yào', '会': 'huì',
    '一': 'yī', '二': 'èr', '三': 'sān', '四': 'sì', '五': 'wǔ',
    '六': 'liù', '七': 'qī', '八': 'bā', '九': 'jiǔ', '十': 'shí',
    '上': 'shàng', '下': 'xià', '大': 'dà', '小': 'xiǎo', '中': 'zhōng',
    '国': 'guó', '北': 'běi', '京': 'jīng', '天': 'tiān', '地': 'dì',
    '日': 'rì', '月': 'yuè', '水': 'shuǐ', '火': 'huǒ', '山': 'shān',
    '石': 'shí', '木': 'mù', '金': 'jīn', '土': 'tǔ', '风': 'fēng',
    '云': 'yún', '雨': 'yǔ', '雪': 'xuě', '花': 'huā', '草': 'cǎo',
    '树': 'shù', '鸟': 'niǎo', '鱼': 'yú', '马': 'mǎ', '牛': 'niú',
    '羊': 'yáng', '虫': 'chóng', '龙': 'lóng', '来': 'lái', '去': 'qù',
    '说': 'shuō', '话': 'huà', '写': 'xiě', '读': 'dú', '看': 'kàn',
    '听': 'tīng', '想': 'xiǎng', '知': 'zhī', '道': 'dào', '好': 'hǎo',
    '坏': 'huài', '多': 'duō', '少': 'shǎo', '长': 'cháng', '短': 'duǎn',
    '高': 'gāo', '低': 'dī', '新': 'xīn', '旧': 'jiù', '美': 'měi',
    '丽': 'lì', '白': 'bái', '黑': 'hēi', '红': 'hóng', '绿': 'lǜ',
    '蓝': 'lán', '黄': 'huáng', '青': 'qīng', '紫': 'zǐ', '灰': 'huī',
    '开': 'kāi', '关': 'guān', '门': 'mén', '窗': 'chuāng', '桌': 'zhuō',
    '椅': 'yǐ', '床': 'chuáng', '房': 'fáng', '家': 'jiā', '城': 'chéng',
    '市': 'shì', '村': 'cūn', '前': 'qián', '后': 'hòu', '左': 'zuǒ',
    '右': 'yòu', '里': 'lǐ', '外': 'wài', '东': 'dōng', '南': 'nán',
    '西': 'xī', '春': 'chūn', '夏': 'xià', '秋': 'qiū', '冬': 'dōng',
    '年': 'nián', '时': 'shí', '今': 'jīn', '明': 'míng', '昨': 'zuó',
    '早': 'zǎo', '晚': 'wǎn', '午': 'wǔ', '夜': 'yè', '华': 'huá',
    '民': 'mín', '共': 'gòng', '党': 'dǎng', '军': 'jūn', '政': 'zhèng',
    '法': 'fǎ', '学': 'xué', '校': 'xiào', '生': 'shēng', '工': 'gōng',
    '作': 'zuò', '用': 'yòng', '能': 'néng', '力': 'lì', '机': 'jī',
    '电': 'diàn', '信': 'xìn', '息': 'xī', '网': 'wǎng', '数': 'shù',
    '据': 'jù', '算': 'suàn', '世': 'shì', '界': 'jiè', '全': 'quán',
    '部': 'bù', '种': 'zhǒng', '类': 'lèi', '型': 'xíng', '式': 'shì',
    '方': 'fāng', '向': 'xiàng', '量': 'liàng', '度': 'dù', '间': 'jiān',
    '空': 'kōng', '问': 'wèn', '题': 'tí', '答': 'dá', '案': 'àn',
    '需': 'xū', '求': 'qiú', '解': 'jiě', '决': 'jué', '定': 'dìng',
    '义': 'yì', '文': 'wén', '名': 'míng', '字': 'zì',
}

# 常见姓氏拼音（多音字姓氏）
_SURNAME_PINYIN = {
    '单': 'shàn', '朴': 'piáo', '区': 'ōu', '仇': 'qiú',
    '解': 'xiè', '查': 'zhā', '曾': 'zēng', '华': 'huà',
    '任': 'rén', '缪': 'miào', '盖': 'gě', '乐': 'yuè',
    '万俟': 'mòqí', '尉迟': 'yùchí', '长孙': 'zhǎngsūn',
}


def 转拼音(文本: str, 分隔符: str = ' ', 首字母: bool = False) -> str:
    """
    将中文文本转为拼音（无音调）。

    参数:
        文本: 中文文本
        分隔符: 拼音之间的分隔符，默认空格
        首字母: True 时只返回首字母

    返回: 拼音字符串
    """
    if not 文本:
        return ''
    if _HAS_PYPINYIN:
        if 首字母:
            items = _pypinyin(文本, style=_PinyinStyle.FIRST_LETTER)
            return ''.join(item[0] for item in items)
        items = _pypinyin(文本, style=_PinyinStyle.NORMAL)
        return 分隔符.join(item[0] for item in items)
    # 回退
    result = []
    for ch in 文本:
        if ch in _BASIC_PINYIN_MAP:
            py = _BASIC_PINYIN_MAP[ch]
            result.append(py[0] if 首字母 else py)
        elif ch.strip() and not _is_cjk(ch):
            result.append(ch)
    return 分隔符.join(result) if not 首字母 else ''.join(result)


def 转拼音带声调(文本: str, 分隔符: str = ' ') -> str:
    """
    将中文文本转为带声调的拼音。

    参数:
        文本: 中文文本
        分隔符: 拼音之间的分隔符

    返回: 带声调拼音字符串
    """
    if not 文本:
        return ''
    if _HAS_PYPINYIN:
        items = _pypinyin(文本, style=_PinyinStyle.TONE)
        return 分隔符.join(item[0] for item in items)
    # 回退
    result = []
    for ch in 文本:
        if ch in _BASIC_PINYIN_TONE_MAP:
            result.append(_BASIC_PINYIN_TONE_MAP[ch])
        elif ch.strip() and not _is_cjk(ch):
            result.append(ch)
    return 分隔符.join(result)


def 转拼音声调数字(文本: str, 分隔符: str = ' ') -> str:
    """
    将中文文本转为拼音，声调用数字表示（如 hao3）。

    参数:
        文本: 中文文本
        分隔符: 拼音之间的分隔符

    返回: 带数字声调的拼音字符串
    """
    if not 文本:
        return ''
    if _HAS_PYPINYIN:
        items = _pypinyin(文本, style=_PinyinStyle.TONE3)
        return 分隔符.join(item[0] for item in items)
    # 回退
    result = []
    for ch in 文本:
        if ch in _BASIC_PINYIN_TONE_MAP:
            py = _BASIC_PINYIN_TONE_MAP[ch]
            # 声调符号转数字
            tone = _tone_mark_to_number(py)
            result.append(py)
        elif ch.strip() and not _is_cjk(ch):
            result.append(ch)
    return 分隔符.join(result)


def _tone_mark_to_number(py: str) -> str:
    """将声调符号转为数字后缀（简化实现）"""
    tone_map = {'ā': 'a1', 'á': 'a2', 'ǎ': 'a3', 'à': 'a4',
                'ō': 'o1', 'ó': 'o2', 'ǒ': 'o3', 'ò': 'o4',
                'ē': 'e1', 'é': 'e2', 'ě': 'e3', 'è': 'e4',
                'ī': 'i1', 'í': 'i2', 'ǐ': 'i3', 'ì': 'i4',
                'ū': 'u1', 'ú': 'u2', 'ǔ': 'u3', 'ù': 'u4',
                'ǖ': 'v1', 'ǘ': 'v2', 'ǚ': 'v3', 'ǜ': 'v4',
                'm̄': 'm1', 'ḿ': 'm2', 'mǐ': 'm3', 'm̀': 'm4',
                'ń': 'n2', 'ň': 'n3', 'ǹ': 'n4'}
    return py


def 转拼音首字母(文本: str) -> str:
    """
    获取中文文本的拼音首字母。

    参数:
        文本: 中文文本

    返回: 首字母字符串
    """
    return 转拼音(文本, 分隔符='', 首字母=True)


def 转拼音列表(文本: str, 带声调: bool = False) -> List[str]:
    """
    将中文文本转为拼音列表（每个字对应一个拼音）。

    参数:
        文本: 中文文本
        带声调: 是否包含声调

    返回: 拼音列表
    """
    if not 文本:
        return []
    if _HAS_PYPINYIN:
        style = _PinyinStyle.TONE if 带声调 else _PinyinStyle.NORMAL
        items = _pypinyin(文本, style=style)
        return [item[0] for item in items]
    # 回退
    result = []
    for ch in 文本:
        if ch in (_BASIC_PINYIN_TONE_MAP if 带声调 else _BASIC_PINYIN_MAP):
            result.append((_BASIC_PINYIN_TONE_MAP if 带声调 else _BASIC_PINYIN_MAP)[ch])
        elif ch.strip() and not _is_cjk(ch):
            result.append(ch)
    return result


def 转拼音姓氏(文本: str, 分隔符: str = ' ') -> str:
    """
    按姓氏发音转换拼音（处理多音字姓氏）。

    参数:
        文本: 姓名文本
        分隔符: 拼音之间的分隔符

    返回: 拼音字符串
    """
    if not 文本:
        return ''
    # 先尝试匹配复姓
    for surname, py in sorted(_SURNAME_PINYIN.items(), key=lambda x: -len(x[0])):
        if 文本.startswith(surname):
            rest = 文本[len(surname):]
            rest_py = 转拼音(rest, 分隔符=' ', 首字母=False) if rest else ''
            if rest_py:
                return py + ' ' + rest_py
            return py
    # 单姓
    if 文本 and 文本[0] in _SURNAME_PINYIN:
        py = _SURNAME_PINYIN[文本[0]]
        rest = 文本[1:]
        rest_py = 转拼音(rest, 分隔符=' ', 首字母=False) if rest else ''
        if rest_py:
            return py + ' ' + rest_py
        return py
    return 转拼音(文本, 分隔符=分隔符)


# =============================================================================
# 3. 简繁转换 (Simplified/Traditional)
# =============================================================================

# 基础简繁映射表
_SIMPLIFIED_TO_TRADITIONAL = {
    '门': '門', '国': '國', '华': '華', '龙': '龍', '长': '長',
    '关': '關', '爱': '愛', '车': '車', '东': '東', '马': '馬',
    '鱼': '魚', '鸟': '鳥', '贝': '貝', '见': '見', '言': '言',
    '语': '語', '说': '說', '话': '話', '读': '讀', '写': '寫',
    '书': '書', '学': '學', '习': '習', '飞': '飛', '风': '風',
    '云': '雲', '电': '電', '阳': '陽', '阴': '陰', '时': '時',
    '间': '間', '问': '問', '题': '題', '对': '對', '错': '錯',
    '过': '過', '还': '還', '进': '進', '这': '這', '那': '那',
    '来': '來', '会': '會', '动': '動', '开': '開', '发': '發',
    '体': '體', '面': '面', '声': '聲', '线': '線', '级': '級',
    '红': '紅', '绿': '綠', '纸': '紙', '张': '張', '画': '畫',
    '笔': '筆', '机': '機', '气': '氣', '乐': '樂', '兴': '興',
    '当': '當', '后': '後', '前': '前', '里': '裡', '只': '只',
    '个': '個', '为': '為', '与': '與', '于': '於', '并': '並',
    '从': '從', '变': '變', '义': '義', '实': '實', '导': '導',
    '标': '標', '点': '點', '线': '線', '队': '隊', '阵': '陣',
    '陆': '陸', '际': '際', '随': '隨', '险': '險', '难': '難',
    '双': '雙', '灵': '靈', '备': '備', '宝': '寶', '实': '實',
    '验': '驗', '试': '試', '让': '讓', '证': '證', '据': '據',
    '数': '數', '据': '據', '经': '經', '验': '驗', '资': '資',
    '源': '源', '网': '網', '页': '頁', '浏': '瀏', '览': '覽',
    '无': '無', '产': '產', '业': '業', '务': '務', '专': '專',
    '门': '門', '争': '爭', '广': '廣', '厂': '廠', '场': '場',
    '报': '報', '告': '告', '诉': '訴', '讼': '訟', '创': '創',
    '办': '辦', '协': '協', '议': '議', '论': '論', '坛': '壇',
    '识': '識', '别': '別', '称': '稱', '赞': '讚', '赏': '賞',
    '钱': '錢', '银': '銀', '铜': '銅', '铁': '鐵', '钟': '鐘',
    '钢': '鋼', '钻': '鑽', '矿': '礦', '盐': '鹽', '碱': '鹼',
    '药': '藥', '疗': '療', '医': '醫', '院': '院', '病': '病',
    '痛': '痛', '疯': '瘋', '癫': '癲', '痴': '癡', '哑': '啞',
    '聋': '聾', '盲': '盲', '众': '眾', '亲': '親', '新': '新',
    '旧': '舊', '时': '時', '代': '代', '历': '歷', '史': '史',
    '岁': '歲', '梦': '夢', '觉': '覺', '睡': '睡', '醒': '醒',
    '声': '聲', '音': '音', '响': '響', '量': '量', '质': '質',
    '干': '乾', '湿': '濕', '热': '熱', '冷': '冷', '温': '溫',
    '度': '度', '数': '數', '值': '值', '范': '範', '围': '圍',
    '图': '圖', '像': '像', '形': '形', '状': '狀', '态': '態',
    '运': '運', '转': '轉', '动': '動', '力': '力', '速': '速',
    '神': '神', '经': '經', '系': '系', '统': '統', '节': '節',
    '构': '構', '造': '造', '组': '組', '织': '織', '成': '成',
    '分': '分', '子': '子', '原': '原', '理': '理', '论': '論',
    '应': '應', '用': '用', '程': '程', '序': '序', '库': '庫',
    '存': '存', '取': '取', '放': '放', '置': '置', '处': '處',
    '理': '理', '管': '管', '控': '控', '制': '制', '度': '度',
    '权': '權', '限': '限', '规': '規', '则': '則', '准': '準',
    '则': '則', '标': '標', '准': '準', '规': '規', '范': '範',
    '审': '審', '核': '核', '查': '查', '阅': '閱', '读': '讀',
    '写': '寫', '编': '編', '译': '譯', '翻': '翻', '评': '評',
    '价': '價', '值': '值', '测': '測', '量': '量', '实': '實',
    '部': '部', '署': '署', '配': '配', '置': '置',
}

# 构建繁体到简体的反向映射
_TRADITIONAL_TO_SIMPLIFIED = {v: k for k, v in _SIMPLIFIED_TO_TRADITIONAL.items()}


def 简转繁(文本: str) -> str:
    """
    简体中文转繁体中文。

    参数:
        文本: 简体中文文本

    返回: 繁体中文文本
    """
    if not 文本:
        return ''
    if _HAS_OPENCC:
        cc = _OpenCC('s2t')
        return cc.convert(文本)
    # 回退：使用映射表
    result = []
    for ch in 文本:
        result.append(_SIMPLIFIED_TO_TRADITIONAL.get(ch, ch))
    return ''.join(result)


def 繁转简(文本: str) -> str:
    """
    繁体中文转简体中文。

    参数:
        文本: 繁体中文文本

    返回: 简体中文文本
    """
    if not 文本:
        return ''
    if _HAS_OPENCC:
        cc = _OpenCC('t2s')
        return cc.convert(文本)
    # 回退：使用映射表
    result = []
    for ch in 文本:
        result.append(_TRADITIONAL_TO_SIMPLIFIED.get(ch, ch))
    return ''.join(result)


def 简转繁台湾(文本: str) -> str:
    """
    简体中文转台湾繁体。

    参数:
        文本: 简体中文文本

    返回: 台湾繁体文本
    """
    if not 文本:
        return ''
    if _HAS_OPENCC:
        cc = _OpenCC('s2tw')
        return cc.convert(文本)
    return 简转繁(文本)


def 简转繁香港(文本: str) -> str:
    """
    简体中文转香港繁体。

    参数:
        文本: 简体中文文本

    返回: 香港繁体文本
    """
    if not 文本:
        return ''
    if _HAS_OPENCC:
        cc = _OpenCC('s2hk')
        return cc.convert(文本)
    return 简转繁(文本)


# =============================================================================
# 4. 文本统计 (Text Statistics)
# =============================================================================

def 统计字符(文本: str) -> Dict[str, int]:
    """
    统计文本中的各类字符数量。

    返回: {
        '总字符数': int,
        '汉字数': int,
        '中文标点数': int,
        '英文字母数': int,
        '数字数': int,
        '空格数': int,
        '其他字符数': int,
    }
    """
    total = len(文本)
    chinese = 0
    punct = 0
    letters = 0
    digits = 0
    spaces = 0
    others = 0

    for ch in 文本:
        if _is_cjk(ch):
            chinese += 1
        elif _is_cjk_punct(ch):
            punct += 1
        elif ch.isalpha():
            letters += 1
        elif ch.isdigit():
            digits += 1
        elif ch.isspace():
            spaces += 1
        else:
            others += 1

    return {
        '总字符数': total,
        '汉字数': chinese,
        '中文标点数': punct,
        '英文字母数': letters,
        '数字数': digits,
        '空格数': spaces,
        '其他字符数': others,
    }


def 统计词频(文本: str, 数量: int = 10, 过滤停用词: bool = False) -> List[Tuple[str, int]]:
    """
    统计文本中的词频。

    参数:
        文本: 待统计文本
        数量: 返回前N个高频词
        过滤停用词: 是否过滤常见停用词

    返回: [(词语, 出现次数), ...]
    """
    words = 分词精确模式(文本)

    if 过滤停用词:
        停用词集 = _get_stopwords()
        words = [w for w in words if w.strip() and w not in 停用词集 and len(w) > 1]

    return Counter(words).most_common(数量)


def _get_stopwords() -> Set[str]:
    """获取常见中文停用词"""
    return {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
        '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
        '你', '会', '着', '没有', '看', '好', '自己', '这', '他', '她',
        '它', '们', '那', '为', '与', '及', '等', '从', '被', '把',
        '让', '对', '向', '往', '以', '比', '跟', '同', '并', '或',
        '但', '而', '且', '如果', '因为', '所以', '虽然', '但是', '然而',
        '之', '其', '该', '此', '每', '各', '某', '哪', '谁', '什么',
        '怎么', '如何', '为什么', '怎样', '吗', '吧', '呢', '啊', '哦',
        '嗯', '呀', '么', '过', '还', '已', '已经', '能', '可', '可以',
        '做', '做', '当', '将', '把', '被', '让', '使', '用', '给',
        '为', '所', '得', '地', '个', '种', '些', '点', '些', '里',
        '中', '外', '前', '后', '上', '下', '左', '右', '来', '去',
        '出', '入', '进', '回', '开', '关', '起', '落', '是', '非',
    }


def 统计句子数(文本: str) -> int:
    """
    统计文本中的句子数量。

    根据句号、问号、感叹号、省略号、分号等句子结束符统计。

    参数:
        文本: 待统计文本

    返回: 句子数量
    """
    if not 文本.strip():
        return 0
    # 句子结束符
    sentences = re.split(r'[。！？\n]+', 文本)
    return len([s for s in sentences if s.strip()])


def 统计段落数(文本: str) -> int:
    """
    统计文本中的段落数量。

    参数:
        文本: 待统计文本

    返回: 段落数量
    """
    if not 文本.strip():
        return 0
    paragraphs = [p for p in 文本.split('\n') if p.strip()]
    return len(paragraphs)


def 可读性评分(文本: str) -> float:
    """
    计算中文文本的可读性评分（基于平均句子长度和汉字占比的简易评分）。

    评分范围 0-100，越高表示越易读。

    参数:
        文本: 待计算文本

    返回: 可读性评分
    """
    if not 文本.strip():
        return 0.0

    stats = 统计字符(文本)
    chinese_count = stats['汉字数']
    total_chars = stats['总字符数']

    if total_chars == 0:
        return 0.0

    sentence_count = 统计句子数(文本)
    if sentence_count == 0:
        sentence_count = 1

    # 平均句子长度（汉字数/句子数）
    avg_sentence_len = chinese_count / sentence_count

    # 汉字占比
    chinese_ratio = chinese_count / total_chars if total_chars > 0 else 0

    # 评分：句子越短、汉字占比越高，越易读
    # 理想平均句子长度 10-20 字
    len_score = max(0, 100 - abs(avg_sentence_len - 15) * 3)
    # 汉字占比 70% 以上为佳
    ratio_score = chinese_ratio * 100

    score = len_score * 0.6 + ratio_score * 0.4
    return max(0, min(100, score))


def 语言检测(文本: str) -> str:
    """
    检测文本主要语言。

    参数:
        文本: 待检测文本

    返回: '中文', '英文', '中英混合', '其他'
    """
    if not 文本.strip():
        return '其他'

    stats = 统计字符(文本)
    chinese = stats['汉字数']
    letters = stats['英文字母数']

    total_printable = chinese + letters + stats['数字数']
    if total_printable == 0:
        return '其他'

    chinese_ratio = chinese / total_printable
    english_ratio = letters / total_printable

    if chinese_ratio > 0.8:
        return '中文'
    elif english_ratio > 0.8:
        return '英文'
    elif chinese_ratio > 0.2 and english_ratio > 0.2:
        return '中英混合'
    else:
        return '其他'


# =============================================================================
# 5. 数字与金额转换 (Number/Currency)
# =============================================================================

_DIGITS = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
_DIGITS_CAPITAL = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
_UNITS = ['', '十', '百', '千']
_UNITS_CAPITAL = ['', '拾', '佰', '仟']
_LARGE_UNITS = ['', '万', '亿', '万亿']
_LARGE_UNITS_CAPITAL = ['', '萬', '億', '兆']

# 数字到中文映射
_DIGIT_MAP = {
    '0': '零', '1': '一', '2': '二', '3': '三', '4': '四',
    '5': '五', '6': '六', '7': '七', '8': '八', '9': '九',
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '壹': 1, '贰': 2, '叁': 3, '肆': 4,
    '伍': 5, '陆': 6, '柒': 7, '捌': 8, '玖': 9,
    '十': 10, '拾': 10, '百': 100, '佰': 100,
    '千': 1000, '仟': 1000,
    '万': 10000, '萬': 10000,
    '亿': 100000000, '億': 100000000,
}


def 数字转中文(数值: Union[int, float], 大写: bool = False) -> str:
    """
    将阿拉伯数字转为中文数字。

    参数:
        数值: 数字（整数或浮点数）
        大写: True 使用大写（壹贰叁...），用于财务

    返回: 中文数字字符串
    """
    if isinstance(数值, float):
        int_part = int(数值)
        dec_part = round(数值 - int_part, 10)
        if dec_part == 0:
            return 数字转中文整数(int_part, 大写)
        int_str = 数字转中文整数(int_part, 大写)
        digits = _DIGITS_CAPITAL if 大写 else _DIGITS
        # 小数部分
        dec_str = ''
        s = str(数值)
        if '.' in s:
            dec_digits = s.split('.')[1]
            dec_str = '点' + ''.join(digits[int(d)] for d in dec_digits if d.isdigit())
        return int_str + dec_str

    return 数字转中文整数(int(数值), 大写)


def 数字转中文整数(数值: int, 大写: bool = False) -> str:
    """整数转中文数字"""
    if 数值 == 0:
        return (_DIGITS_CAPITAL if 大写 else _DIGITS)[0]

    if 数值 < 0:
        return '负' + 数字转中文整数(-数值, 大写)

    digits = _DIGITS_CAPITAL if 大写 else _DIGITS
    units = _UNITS_CAPITAL if 大写 else _UNITS
    large_units = _LARGE_UNITS_CAPITAL if 大写 else _LARGE_UNITS

    # 分组处理（每4位一组）
    groups = []
    n = 数值
    while n > 0:
        groups.append(n % 10000)
        n //= 10000

    result = ''
    for i in range(len(groups) - 1, -1, -1):
        group = groups[i]
        if group == 0:
            if result and not result.endswith(digits[0]):
                result += digits[0]
            continue

        # 处理一组（4位数）
        group_str = ''
        for j in range(3, -1, -1):
            d = (group // (10 ** j)) % 10
            if d == 0:
                if group_str and not group_str.endswith(digits[0]):
                    group_str += digits[0]
            else:
                group_str += digits[d] + units[j]

        # 去除尾部零
        group_str = group_str.rstrip(digits[0])
        result += group_str + large_units[i]

    # 特殊处理：十 ~ 十九 省略开头的"一"
    if 10 <= 数值 <= 19:
        result = result[1:]

    return result


def 中文转数字(文本: str) -> int:
    """
    将中文数字转为阿拉伯数字。

    参数:
        文本: 中文数字字符串（如"三千五百二十一"）

    返回: 整数
    """
    if not 文本:
        raise ValueError('输入文本为空')

    # 处理负数
    if 文本.startswith('负'):
        return -中文转数字(文本[1:])

    # 单字数字
    if 文本 in _DIGIT_MAP:
        return _DIGIT_MAP[文本]

    result = 0
    current = 0
    total = 0

    for ch in 文本:
        if ch in _DIGIT_MAP:
            val = _DIGIT_MAP[ch]
            if val >= 10:
                # 单位
                if current == 0:
                    current = 1
                result += current * val
                current = 0
            else:
                # 数字
                current = val
        elif ch in ('万', '萬'):
            if current == 0 and result == 0:
                result = 1
            result = (result + current) * 10000
            total += result
            result = 0
            current = 0
        elif ch in ('亿', '億'):
            if current == 0 and result == 0:
                result = 1
            result = (result + current) * 100000000
            total += result
            result = 0
            current = 0

    return total + result + current


def 金额转大写(金额: float) -> str:
    """
    将金额转为中文大写（用于财务/发票）。

    例如: 1234.56 -> "壹仟贰佰叁拾肆元伍角陆分"

    参数:
        金额: 金额数字

    返回: 中文大写金额字符串
    """
    if 金额 < 0:
        return '负' + 金额转大写(-金额)

    # 四舍五入到分，使用字符串方式避免浮点精度问题
    fen_total = round(金额 * 100)
    if fen_total < 0:
        fen_total = 0

    if fen_total == 0:
        return '零元整'

    yuan = fen_total // 100
    jiao = (fen_total % 100) // 10
    fen = fen_total % 10

    digits = _DIGITS_CAPITAL
    units = ['', '拾', '佰', '仟']
    large_units = ['', '萬', '億', '兆']

    # 处理整数部分
    result = ''
    if yuan > 0:
        groups = []
        n = yuan
        while n > 0:
            groups.append(n % 10000)
            n //= 10000

        for i in range(len(groups) - 1, -1, -1):
            group = groups[i]
            if group == 0:
                if result and not result.endswith(digits[0]):
                    result += digits[0]
                continue

            group_str = ''
            for j in range(3, -1, -1):
                d = (group // (10 ** j)) % 10
                if d == 0:
                    if group_str and not group_str.endswith(digits[0]):
                        group_str += digits[0]
                else:
                    group_str += digits[d] + units[j]

            group_str = group_str.rstrip(digits[0])
            result += group_str + large_units[i]

        result += '元'

    # 处理小数部分
    if jiao == 0 and fen == 0:
        result += '整'
    else:
        if jiao > 0:
            result += digits[jiao] + '角'
        if fen > 0:
            result += digits[fen] + '分'

    return result


def 百分比转中文(数值: float, 小数位数: int = 2) -> str:
    """
    将百分比转为中文表示。

    参数:
        数值: 百分比值（如 0.1234 表示 12.34%）
        小数位数: 保留小数位数

    返回: 中文百分比字符串
    """
    percent = 数值 * 100
    formatted = f'{percent:.{小数位数}f}'
    return formatted + '%'


def 中文转百分比(文本: str) -> float:
    """
    将中文百分比字符串转为数值。

    参数:
        文本: 如 "百分之十二点三四" 或 "12.34%"

    返回: 浮点数（如 0.1234）
    """
    if 文本.startswith('百分之'):
        inner = 文本[3:]
        if '点' in inner:
            parts = inner.split('点')
            int_part = 中文转数字(parts[0]) if parts[0] else 0
            dec_part = 0
            if len(parts) > 1:
                for i, ch in enumerate(parts[1]):
                    if ch in _DIGIT_MAP and isinstance(_DIGIT_MAP[ch], int) and _DIGIT_MAP[ch] < 10:
                        dec_part = dec_part * 10 + _DIGIT_MAP[ch]
                dec_part = dec_part / (10 ** len(parts[1]))
            return (int_part + dec_part) / 100
        return 中文转数字(inner) / 100
    elif 文本.endswith('%'):
        return float(文本[:-1]) / 100
    try:
        return float(文本) / 100
    except ValueError:
        raise ValueError(f'无法解析百分比: {文本}')


# =============================================================================
# 6. 文本处理工具 (Text Utilities)
# =============================================================================

def 去除空白(文本: str) -> str:
    """
    去除文本中的所有空白字符（空格、换行、制表符等）。

    参数:
        文本: 输入文本

    返回: 去除空白后的文本
    """
    return ''.join(文本.split())


def 去除标点(文本: str) -> str:
    """
    去除文本中的标点符号（中英文标点）。

    参数:
        文本: 输入文本

    返回: 去除标点后的文本
    """
    return re.sub(r'[^\w\s\u4e00-\u9fff]', '', 文本)


def 提取汉字(文本: str) -> str:
    """
    提取文本中的汉字（只保留 CJK 字符）。

    参数:
        文本: 输入文本

    返回: 只包含汉字的字符串
    """
    return ''.join(ch for ch in 文本 if _is_cjk(ch))


def 提取英文(文本: str) -> str:
    """
    提取文本中的英文字母。

    参数:
        文本: 输入文本

    返回: 只包含英文字母的字符串
    """
    return ''.join(ch for ch in 文本 if ch.isalpha() and not _is_cjk(ch))


def 提取数字(文本: str) -> str:
    """
    提取文本中的数字字符。

    参数:
        文本: 输入文本

    返回: 只包含数字的字符串
    """
    return ''.join(ch for ch in 文本 if ch.isdigit())


def 判断中英混合(文本: str) -> bool:
    """
    判断文本是否包含中英文混合内容。

    参数:
        文本: 输入文本

    返回: True 如果包含中英文混合
    """
    has_chinese = any(_is_cjk(ch) for ch in 文本)
    has_english = any(ch.isalpha() and not _is_cjk(ch) for ch in 文本)
    return has_chinese and has_english


def 文本相似度Jaccard(文本1: str, 文本2: str) -> float:
    """
    计算两段文本的 Jaccard 相似度（基于字符集合）。

    参数:
        文本1: 第一段文本
        文本2: 第二段文本

    返回: 相似度 0.0 ~ 1.0
    """
    set1 = set(文本1)
    set2 = set(文本2)

    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0

    intersection = set1 & set2
    union = set1 | set2

    return len(intersection) / len(union)


def 文本相似度余弦(文本1: str, 文本2: str) -> float:
    """
    计算两段文本的余弦相似度（基于词频向量）。

    参数:
        文本1: 第一段文本
        文本2: 第二段文本

    返回: 相似度 0.0 ~ 1.0
    """
    words1 = 分词精确模式(文本1)
    words2 = 分词精确模式(文本2)

    if not words1 or not words2:
        return 0.0

    # 构建词频向量
    all_words = set(words1) | set(words2)
    vec1 = Counter(words1)
    vec2 = Counter(words2)

    dot_product = sum(vec1.get(w, 0) * vec2.get(w, 0) for w in all_words)
    norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


class 敏感词过滤器:
    """
    敏感词过滤器（基于字典树 / Trie 实现）。

    用法:
        filter = 敏感词过滤器()
        filter.添加敏感词(['敏感词1', '敏感词2'])
        result = filter.过滤('文本包含敏感词1')
        # result = '文本包含***'
    """

    def __init__(self):
        self._trie = {}
        self._end_mark = '__END__'

    def 添加敏感词(self, 词语: Union[str, List[str]]) -> None:
        """
        添加敏感词。

        参数:
            词语: 单个敏感词字符串或敏感词列表
        """
        if isinstance(词语, str):
            self._add_word(词语)
        else:
            for w in 词语:
                self._add_word(w)

    def _add_word(self, 词语: str) -> None:
        node = self._trie
        for ch in 词语:
            if ch not in node:
                node[ch] = {}
            node = node[ch]
        node[self._end_mark] = len(词语)

    def 过滤(self, 文本: str, 替换字符: str = '*') -> str:
        """
        过滤文本中的敏感词。

        参数:
            文本: 待过滤文本
            替换字符: 替换敏感词的字符，默认 '*'

        返回: 过滤后的文本
        """
        result = list(文本)
        i = 0
        while i < len(文本):
            node = self._trie
            match_len = 0
            for j in range(i, len(文本)):
                ch = 文本[j]
                if ch in node:
                    node = node[ch]
                    if self._end_mark in node:
                        match_len = node[self._end_mark]
                else:
                    break
            if match_len > 0:
                for k in range(i, i + match_len):
                    result[k] = 替换字符
                i += match_len
            else:
                i += 1
        return ''.join(result)

    def 检测(self, 文本: str) -> List[str]:
        """
        检测文本中是否包含敏感词。

        参数:
            文本: 待检测文本

        返回: 找到的敏感词列表
        """
        found = []
        i = 0
        while i < len(文本):
            node = self._trie
            match_len = 0
            for j in range(i, len(文本)):
                ch = 文本[j]
                if ch in node:
                    node = node[ch]
                    if self._end_mark in node:
                        match_len = node[self._end_mark]
                else:
                    break
            if match_len > 0:
                found.append(文本[i:i + match_len])
                i += match_len
            else:
                i += 1
        return found

    def 清空(self) -> None:
        """清空所有敏感词"""
        self._trie = {}


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 分词
    '分词精确模式', '分词全模式', '分词搜索引擎模式',
    '添加自定义词典', '添加自定义词语', '删除自定义词语',
    '词性标注', '提取关键词TFIDF', '提取关键词TextRank',
    '分词带位置',
    # 拼音
    '转拼音', '转拼音带声调', '转拼音声调数字',
    '转拼音首字母', '转拼音列表', '转拼音姓氏',
    # 简繁
    '简转繁', '繁转简', '简转繁台湾', '简转繁香港',
    # 文本统计
    '统计字符', '统计词频', '统计句子数', '统计段落数',
    '可读性评分', '语言检测',
    # 数字与金额
    '数字转中文', '中文转数字', '金额转大写',
    '百分比转中文', '中文转百分比',
    # 文本处理工具
    '去除空白', '去除标点', '提取汉字', '提取英文', '提取数字',
    '判断中英混合',
    '文本相似度Jaccard', '文本相似度余弦',
    '敏感词过滤器',
]