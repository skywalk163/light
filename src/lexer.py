"""
光明（Light）编程语言 - 词法分析器

实现决策29的三层分词机制：
1. 类型切换自动分词 - 甲加1 → [甲] [加] [1]
2. 双字关键词优先匹配 - 定义甲 → [定义] [甲]
3. 元数驱动参数收集 - 打印 甲 -（元数=1）→ [打印] [甲]

参考：newlisp/yan 的无空格分词实现
"""

from dataclasses import dataclass
from typing import List, Set, Dict, Optional, Tuple
from enum import Enum

from tokens import Token, TokenType
from keywords import (
    ALL_KEYWORDS, KEYWORDS_DOUBLE, KEYWORDS_LOGIC, KEYWORDS_SPECIAL,
    VERB_ARITY, BUILTIN_TYPES, SYMBOL_MAP, BLOCKING_SYMBOLS
)

# 运算符动词集合（用于分词时识别运算符）
OPERATOR_VERBS = frozenset({
    '加', '减', '乘', '除', '加上', '减去', '乘以', '除以', 
    '大于', '小于', '等于', '不等于', '大于等于', '小于等于',
    '不小于', '不大于',
    '模', '幂'
})

# 标识符安全关键字：这些关键字常作为复合标识符的后缀（如"处理函数"、"输出格式"），
# 在分词时不应触发拆分。即：当这些关键字出现在标识符中间或末尾时，应作为标识符的一部分。
IDENTIFIER_SAFE_KEYWORDS = frozenset({
    '函数', '段落',  # 函数相关
    '输出', '返回',  # I/O 和返回
    '接口', '结构体',  # 类型相关
    '枚举', '联合体',  # FFI 类型
    '回调',  # FFI 回调（如"回调函数"、"回调结构体"）
    '匹配',  '配',  # 匹配/配（如"配置"、"完全匹配"应为复合标识符）
})

# 常见复合词保护列表（这些词包含运算符动词或中文数字，但应该作为整体识别）
COMMON_COMPOUND_WORDS = frozenset({
    '追加', '加入', '减少', '乘法', '除法', '模式', '幂次',
    '当前', '当然', '应当', '当选', '当家',
    '加入', '加快', '加强', '加减',
    '减少', '减弱', '减速',
    '乘法', '乘积', '乘客', '乘除',
    '除法', '除非', '去除',
    # 含中文数字字符但整体是标识符/函数名的词
    '四舍五入', '百分位', '千分位', '万分位',
    '二进制', '八进制', '十进制', '十六进制',
    '一次性', '二选一', '三合一',
    '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日',
    # C FFI 指针/数组/错误处理（第二阶段）
    '设置', '设置数组', '设指针', '设指针值', '设系统', '设系统错误码',
    '创建数组', '释放内存', '分配内存', '取地址', '解引用', '指针偏移',
    '外部错误', 'FFI错误', '系统错误码',
    # C FFI 第三阶段
    '创建回调', '枚举值', '联合体成员', '跨平台库', '库路径', '按值传递', '结构体值',
    # C FFI 第四阶段
    '开启调试', '记录调用', '记录类型', '追踪内存',
    '注册回调', '注销回调', '获取回调', 'FFI调试', 'FFI禁用调试', 'FFI获取日志',
    '位域设置', '位域获取', '创建函数指针', '创建类型别名', '定义宏', '获取宏',
    # 科学计算中"X函数"作为标识符（如"导函数"、"函数对象"）
    '导函数', '目标函数', '梯度函数', '海森函数', '函数对象',
    '伽马函数', '误差函数', '贝塔函数', '激活函数', '损失函数', '核函数',
})

# CJK 汉字范围
_HAN_START = 0x4E00
_HAN_END = 0x9FFF


def _is_han_fast(ch: str) -> bool:
    """判断是否为汉字（直接比较 codepoint，CJK 范围是连续的，无需缓存）"""
    cp = ord(ch)
    return _HAN_START <= cp <= _HAN_END


# ASCII 字符分类查表（0-127）
_ASCII_CLASS = bytearray(128)

# 字符分类位掩码
_CLASS_DIGIT = 0x01
_CLASS_ALPHA = 0x02
_CLASS_ALNUM = 0x04
_CLASS_SPACE = 0x08
_CLASS_WHITESPACE = 0x10

for _i in range(128):
    _ch = chr(_i)
    if _ch.isdigit():
        _ASCII_CLASS[_i] |= _CLASS_DIGIT
    if _ch.isalpha():
        _ASCII_CLASS[_i] |= _CLASS_ALPHA
    if _ch.isalnum():
        _ASCII_CLASS[_i] |= _CLASS_ALNUM
    if _ch == ' ' or _ch == '\t':
        _ASCII_CLASS[_i] |= _CLASS_SPACE
    if _ch in ' \t\r':
        _ASCII_CLASS[_i] |= _CLASS_WHITESPACE


def _is_ascii_digit(ch: str) -> bool:
    """判断 ASCII 字符是否为数字（查表法）"""
    cp = ord(ch)
    return cp < 128 and (_ASCII_CLASS[cp] & _CLASS_DIGIT) != 0


def _is_ascii_alpha(ch: str) -> bool:
    """判断 ASCII 字符是否为字母（查表法）"""
    cp = ord(ch)
    return cp < 128 and (_ASCII_CLASS[cp] & _CLASS_ALPHA) != 0


def _is_ascii_alnum(ch: str) -> bool:
    """判断 ASCII 字符是否为字母或数字（查表法）"""
    cp = ord(ch)
    return cp < 128 and (_ASCII_CLASS[cp] & _CLASS_ALNUM) != 0


def _is_ascii_space_tab(ch: str) -> bool:
    """判断 ASCII 字符是否为空格或制表符（查表法）"""
    cp = ord(ch)
    return cp < 128 and (_ASCII_CLASS[cp] & _CLASS_SPACE) != 0


def _is_ascii_whitespace(ch: str) -> bool:
    """判断 ASCII 字符是否为空白字符（空格、制表符、回车）（查表法）"""
    cp = ord(ch)
    return cp < 128 and (_ASCII_CLASS[cp] & _CLASS_WHITESPACE) != 0


# 模块级关键字预计算（只计算一次）
_ALL_KEYWORDS_WITH_VERBS = ALL_KEYWORDS | set(VERB_ARITY.keys())

# 按长度分组的关键字字典（模块级预计算）
_KEYWORDS_BY_LENGTH: Dict[int, frozenset] = {}
_ALL_KEYWORDS_BY_LENGTH: Dict[int, frozenset] = {}
_MAX_KEYWORD_LEN = 0
_ALL_MAX_KEYWORD_LEN = 0

for kw in ALL_KEYWORDS:
    length = len(kw)
    if length not in _KEYWORDS_BY_LENGTH:
        _KEYWORDS_BY_LENGTH[length] = frozenset()
    _KEYWORDS_BY_LENGTH[length] = _KEYWORDS_BY_LENGTH[length] | {kw}
    if length > _MAX_KEYWORD_LEN:
        _MAX_KEYWORD_LEN = length

for kw in _ALL_KEYWORDS_WITH_VERBS:
    length = len(kw)
    if length not in _ALL_KEYWORDS_BY_LENGTH:
        _ALL_KEYWORDS_BY_LENGTH[length] = frozenset()
    _ALL_KEYWORDS_BY_LENGTH[length] = _ALL_KEYWORDS_BY_LENGTH[length] | {kw}
    if length > _ALL_MAX_KEYWORD_LEN:
        _ALL_MAX_KEYWORD_LEN = length

# 中文数字集合（模块级）
_SIMPLE_CHINESE_NUMBERS = frozenset({
    '零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
})

_CHINESE_DIGITS = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '百': 100, '千': 1000, '万': 10000,
}

# 中文引号映射（模块级常量，避免重复创建）
_QUOTE_MAP = {
    '「': '"', '」': '"',
    '『': "'", '』': "'",
}

# 中文闭合引号映射（模块级常量）
_CLOSE_QUOTE_MAP = {
    '「': '」',
    '『': '』',
}

# 中文标点符号集合（模块级常量）
_CJK_PUNCTUATION = frozenset('。：；，（）【】')

# 复合词安全单字关键字（模块级 frozenset）
_COMPOUND_SAFE_SINGLE_KEYWORDS = frozenset({
    '数', '列', '串', '典', '集',
    '从',
    '段',
    '空', '真', '假',
    '父',
    '的',
    '若',
    '则',
    '对',
    '长',
    # L0 单字核心字（v4.1 补全 — 仅添加在复合词中常见的，避免误拆分）
    '过',   # 过滤/过程/通过
    '自',   # 自己/自动
    '是',   # 但是/还是
    '之',   # 属性提取符，常见于复合词
    '并',   # 并且
    '且',   # 并且
    '或',   # 或者
    '非',   # 非常
    '出',   # 弹出/输出/退出
    '引',   # 引号/引用/引导（L4引用关键字，但常见于复合词）
    # 算术运算符（v4.2 补全 — 常见于复合词）
    '加',   # 加法/增加
    '减',   # 减法/减少
    '乘',   # 乘法/乘坐
    '除',   # 除法/删除
    '步',   # 步骤/逐步
    '骤',   # 步骤
    '类',   # 类别/分类
    '模',   # 模拟/模块
    '接',   # 接口/连接/直接（L0核心字，但常见于复合词）
    '序',   # 序列/顺序/程序（常见于遍历循环变量）
    '试',   # 尝试/测试/重试（L0异常关键字，但常见于复合词）
    '否',   # 否则（L0条件关键字，但常见于"是否"等复合词）
    '跳',   # 跳出（L0循环控制关键字，但常见于"心跳"等复合词）
})

# 符号到 TokenType 的映射（模块级常量）
_SYMBOL_TOKEN_MAP = {
    '.': TokenType.DOT,
    ',': TokenType.COMMA,
    ';': TokenType.SEMICOLON,
    ':': TokenType.COLON,
    '(': TokenType.LPAREN,
    ')': TokenType.RPAREN,
    '[': TokenType.LBRACKET,
    ']': TokenType.RBRACKET,
    '{': TokenType.LBRACE,
    '}': TokenType.RBRACE,
    '\\': TokenType.COMMA,
    '=': TokenType.EQUALS,
    '@': TokenType.AT,
    '+': TokenType.PLUS,
    '-': TokenType.MINUS,
    '*': TokenType.STAR,
    '/': TokenType.SLASH,
    '%': TokenType.PERCENT,
    '<': TokenType.LESS,
    '>': TokenType.GREATER,
    '|': TokenType.PIPE,
    '!': TokenType.BANG,
    '\uff01': TokenType.BANG,
}


class LexerError(Exception):
    """词法分析错误"""
    def __init__(self, message: str, line: int, col: int, source_context: str = None):
        self.message = message
        self.line = line
        self.col = col
        self.source_context = source_context
        msg = f"词法错误 (行{line}, 列{col}): {message}"
        if source_context:
            msg += f"\n  附近代码: ...{source_context}..."
        super().__init__(msg)


class Lexer:
    """光明词法分析器：无空格分词 + 三层机制"""

    CHINESE_DIGITS = _CHINESE_DIGITS
    SIMPLE_CHINESE_NUMBERS = _SIMPLE_CHINESE_NUMBERS
    compound_safe_single_keywords = _COMPOUND_SAFE_SINGLE_KEYWORDS

    def __init__(self, source: str = None):
        """初始化词法分析器

        支持两种调用方式：
        - Lexer(source).tokenize()
        - Lexer().tokenize(source)

        Args:
            source: 可选的源码字符串
        """
        self._source = source
        self.keywords_by_length = _KEYWORDS_BY_LENGTH
        self.max_keyword_len = _MAX_KEYWORD_LEN
        self.all_keywords_with_verbs = _ALL_KEYWORDS_WITH_VERBS
        self.all_keywords_by_length = _ALL_KEYWORDS_BY_LENGTH
        self.all_max_keyword_len = _ALL_MAX_KEYWORD_LEN
        self._symbol_token_map = _SYMBOL_TOKEN_MAP
    
    def tokenize(self, source: str = None) -> List[Token]:
        """将源码转为 Token 流
        
        支持两种调用方式：
        - lexer.tokenize()  # 使用构造时传入的 source
        - lexer.tokenize(source)  # 使用传入的 source
        
        Args:
            source: 要分析的源码字符串（可选，默认使用构造时传入的）
        """
        if source is None:
            source = self._source
        if source is None:
            raise LexerError("没有提供源码", 0, 0)
        
        tokens = []
        i = 0
        line = 1
        col = 1
        n = len(source)

        # 预扫描：收集用户定义的标识符
        user_definitions = self._scan_user_definitions(source)

        # 处理缩进
        indent_stack = [0]

        # 安全计数器（防止意外死循环）
        _main_loop_safety = 0

        while i < n:
            # 安全计数器（防止意外死循环）
            _main_loop_safety += 1
            if _main_loop_safety > 1000000:
                raise RuntimeError(f"词法分析主循环超出安全上限 ({_main_loop_safety}次迭代), 位置: {i}, 字符: {repr(source[i:i+30])}")
            
            # 处理字符串（必须在换行处理之前，因为字符串可能包含换行符）
            if source[i] in '"\'「『':
                token, consumed = self._tokenize_string(source, i, line, col)
                tokens.append(token)
                col += consumed
                i += consumed
                continue
            
            # 处理换行
            if source[i] == '\n':
                tokens.append(Token(TokenType.NEWLINE, '\n', line, col))
                line += 1
                col = 1
                i += 1
                
                # 计算下一行的缩进
                indent = 0
                _is_space_tab = _is_ascii_space_tab
                while i < n and _is_space_tab(source[i]):
                    if source[i] == '\t':
                        indent += 4
                    else:
                        indent += 1
                    col += 1
                    i += 1
                
                # 跳过空行和注释行（缩进后立即是换行、EOF、# 或 //）
                if i >= n or source[i] == '\n':
                    continue
                if source[i] == '#':
                    # 跳过注释行
                    while i < n and source[i] != '\n':
                        i += 1
                    continue
                if i + 1 < n and source[i:i+2] == '//':
                    # 跳过注释行
                    while i < n and source[i] != '\n':
                        i += 1
                    continue
                
                # 处理缩进变化
                if indent > indent_stack[-1]:
                    tokens.append(Token(TokenType.INDENT, indent, line, 1))
                    indent_stack.append(indent)
                elif indent < indent_stack[-1]:
                    while indent_stack[-1] > indent:
                        indent_stack.pop()
                        tokens.append(Token(TokenType.DEDENT, indent_stack[-1], line, 1))
                continue
            
            # 跳过空白
            if _is_ascii_whitespace(source[i]):
                col += 1
                i += 1
                continue
            
            # 处理注释（# 开头）
            if source[i] == '#':
                while i < n and source[i] != '\n':
                    i += 1
                continue
            
            # 处理注释（// 开头）或整除运算符（// 在表达式中间）
            if i + 1 < n and source[i:i+2] == '//':
                # 判断是注释还是整除：检查前一个 token
                # 如果前一个 token 是数字、标识符、) 或 ]，则 // 是整除运算符
                if tokens and tokens[-1].type in (
                    TokenType.NUMBER, TokenType.IDENTIFIER, TokenType.RPAREN, TokenType.RBRACKET,
                    TokenType.STRING
                ):
                    # 整除运算符：发出两个 SLASH token
                    tokens.append(Token(TokenType.SLASH, '/', line, col))
                    tokens.append(Token(TokenType.SLASH, '/', line, col + 1))
                    i += 2
                    col += 2
                    continue
                else:
                    # 注释
                    while i < n and source[i] != '\n':
                        i += 1
                    continue
            
            # 处理以点号开头的浮点数（如 .5）
            if source[i] == '.' and i + 1 < n and _is_ascii_digit(source[i + 1]):
                token, consumed = self._tokenize_number(source, i, line, col)
                tokens.append(token)
                col += consumed
                i += consumed
                continue
            
            # 处理符号
            token, consumed = self._try_match_symbol(source, i, line, col)
            if token:
                # 特殊处理：书名号《》内的段落名
                if token.type == TokenType.LBOOK:
                    # 收集段落名
                    j = i + 1
                    name_chars = []
                    while j < n and source[j] != '》':
                        name_chars.append(source[j])
                        j += 1
                    
                    if j >= n:
                        raise LexerError(f"书名号《》未闭合: 段落名 '{''.join(name_chars)}' 缺少右书名号》", line, col)
                    
                    # 添加左书名号
                    tokens.append(token)
                    col += 1
                    i += 1
                    
                    # 添加段落名（作为标识符）
                    para_name = ''.join(name_chars)
                    tokens.append(Token(TokenType.IDENTIFIER, para_name, line, col))
                    col += len(name_chars)
                    i += len(name_chars)
                    
                    # 添加右书名号
                    tokens.append(Token(TokenType.RBOOK, '》', line, col))
                    col += 1
                    i += 1
                    continue
                else:
                    tokens.append(token)
                    col += consumed
                    i += consumed
                    continue
            
            # 处理数字
            if _is_ascii_digit(source[i]):
                token, consumed = self._tokenize_number(source, i, line, col)
                tokens.append(token)
                col += consumed
                i += consumed
                continue
            
            # 处理 f-string：f"..." 或 f'...'
            if source[i] == 'f' and i + 1 < n and source[i+1] in '"\'':
                token, consumed = self._tokenize_fstring(source, i, line, col)
                tokens.append(token)
                col += consumed
                i += consumed
                continue
            
            # 处理中文数字（不在此处拦截单个字符，而是交给 _tokenize_chinese_sequence 处理复合数字）
            # 注释：SIMPLE_CHINESE_NUMBERS 单个字符拦截会破坏复合数字（如"零点一"、"一百"）
            # 以及以数字开头的函数名（如"四舍五入"）的解析
            # 所有汉字统一由 _tokenize_identifier_or_keyword → _tokenize_chinese_sequence 处理
            
            # 处理嵌入块 / L4外语引用块：
            #   v3.3 兼容写法：嵌入 Python: ... 结束嵌入
            #   v4.0 推荐写法：引 Python:   ... 结束引
            # 需在标识符/关键字分词之前检测，避免嵌入代码被光明分词器破坏
            embed_prefix_len = 0
            if _is_han_fast(source[i]):
                if source[i:i+2] == '嵌入':
                    embed_prefix_len = 2  # 旧写法：嵌入
                elif source[i] == '引':
                    # 新写法：引 —— 仅当后面紧跟空格/冒号/换行时才触发
                    # 避免把"引号"、"引用"等复合词中的"引"误判为嵌入块前缀
                    if i + 1 < len(source) and source[i+1] in ' \t:\n':
                        embed_prefix_len = 1
                    # 否则作为普通标识符，不触发嵌入块
            if embed_prefix_len > 0:
                token, consumed = self._tokenize_embed_block(source, i, line, col, embed_prefix_len)
                if token:
                    tokens.append(token)
                    col += consumed
                    i += consumed
                    continue

            # 处理中文数字（注释：不在此处处理，而是在标识符处理中判断）
            # 因为 "甲加三" 中的 "三" 需要根据上下文判断
            
            # 处理标识符和关键字（核心：无空格分词）
            ch_i = source[i]
            if _is_han_fast(ch_i) or _is_ascii_alpha(ch_i) or ch_i == '_':
                new_tokens, consumed = self._tokenize_identifier_or_keyword(source, i, line, col, user_definitions)
                tokens.extend(new_tokens)
                col += consumed
                i += consumed
                continue
            
            # 未知字符
            raise LexerError(f"未知字符: '{source[i]}' (0x{ord(source[i]):04X})", line, col)
        
        # 文件结束，处理剩余的 DEDENT
        while len(indent_stack) > 1:
            indent_stack.pop()
            tokens.append(Token(TokenType.DEDENT, indent_stack[-1], line, col))
        
        tokens.append(Token(TokenType.EOF, None, line, col))
        return tokens
    
    def _is_han(self, ch: str) -> bool:
        """判断是否为汉字（直接委托给模块级快速函数）"""
        return _is_han_fast(ch)
    
    def _is_same_type(self, ch1: str, ch2: str) -> bool:
        """判断两个字符是否属于同一类型（用于分词边界检测）"""
        if not ch1 or not ch2:
            return False

        # 汉字只能和汉字连续
        if _is_han_fast(ch1):
            return _is_han_fast(ch2)

        # 字母、数字、下划线可以连续（但汉字应该分开）
        if _is_han_fast(ch2):
            return False

        if ch1 == '_' or _is_ascii_alnum(ch1):
            return ch2 == '_' or _is_ascii_alnum(ch2)

        return False
    
    def _try_parse_chinese_number(self, source: str, pos: int):
        """
        尝试从指定位置解析完整的中文数字
        返回 (数值, 消耗长度) 或 (None, 0)
        """
        n = len(source)
        start = pos
        
        # 收集连续的汉字
        chars = []
        while pos < n and self._is_han(source[pos]):
            ch = source[pos]
            # 只收集中文数字相关的字符
            if ch in self.CHINESE_DIGITS or ch == '点':
                chars.append(ch)
                pos += 1
            else:
                break
        
        if not chars:
            return None, 0
        
        text = ''.join(chars)
        
        # 尝试解析为中文数字
        value = self._convert_chinese_number(text)
        if value is not None:
            return value, len(text)
        
        return None, 0

    def _convert_chinese_number(self, text: str):
        """
        将中文数字字符串转换为数值
        
        支持格式：
        - 整数：一、十二、三百二十一、一千零一
        - 小数：三点一四一五九、零点一
        """
        if not text:
            return None
        
        digits = self.CHINESE_DIGITS
        
        # 处理小数：X点Y
        if '点' in text:
            parts = text.split('点', 1)
            if len(parts) != 2:
                return None
            # 整数部分
            int_part = self._convert_chinese_integer(parts[0])
            if int_part is None:
                return None
            # 小数部分
            frac = 0
            frac_len = 0
            for ch in parts[1]:
                if ch in digits and digits[ch] < 10:  # 只取0-9的数字
                    frac = frac * 10 + digits[ch]
                    frac_len += 1
                else:
                    return None
            if frac_len == 0:
                return float(int_part)
            return float(int_part) + frac / (10 ** frac_len)
        
        # 处理整数
        return self._convert_chinese_integer(text)

    def _convert_chinese_integer(self, text: str):
        """将中文整数转换为数值"""
        if not text:
            return None
        
        digits = self.CHINESE_DIGITS
        
        # 简单数字
        if text in digits:
            return digits[text]
        
        # 处理复合数字（如十六、一百零一、三百二十一）
        result = 0
        temp = 0
        for ch in text:
            if ch in digits:
                d = digits[ch]
                if d >= 10:  # 十、百、千、万是进位单位
                    if temp == 0:
                        temp = 1  # "十"在开头表示1*10
                    temp *= d
                    result += temp
                    temp = 0
                elif d == 0:  # 零表示空位
                    temp = 0
                else:  # 0-9的数字
                    if temp > 0:
                        temp = temp * 10 + d  # 连续数字组成多位数（如"八五"→85）
                    else:
                        temp = d
            else:
                return None
        
        result += temp
        return result
    
    def _match_keyword(self, text: str, pos: int) -> Tuple[Optional[str], int]:
        """
        最长匹配关键字
        
        注意：compound_safe_single 中的单字关键字（如"典"）不应在独立上下文中匹配，
        仅当它们是更长关键字的组成部分时才使用。
        递归调用 _skip_compound_safe_and_match 处理这种情况。
        
        Returns:
            (匹配到的关键字, 匹配长度) 或 (None, 0)
        """
        return self._skip_compound_safe_and_match(text, pos)
    
    def _skip_compound_safe_and_match(self, text: str, pos: int, text_len: int = None) -> Tuple[Optional[str], int]:
        """尝试匹配关键字，遇到 compound_safe 关键字时跳过并继续匹配后续内容"""
        # 局部变量缓存
        _kw_by_len = _ALL_KEYWORDS_BY_LENGTH
        _max_len = _ALL_MAX_KEYWORD_LEN
        _compound_safe = self.compound_safe_single_keywords
        
        # 缓存 text_len 避免重复计算
        if text_len is None:
            text_len = len(text)
        
        max_possible = min(_max_len, text_len - pos)
        
        # 从最长到最短尝试匹配
        for length in range(max_possible, 0, -1):
            candidates = _kw_by_len.get(length)
            if candidates:
                candidate = text[pos:pos+length]
                if candidate in candidates:
                    # 检查是否是 compound_safe_single 中的单字关键字
                    if (length == 1 and candidate in _compound_safe
                            and pos + length < text_len):
                        # 单字 compound_safe 关键字（如"典"），后面还有内容，
                        # 跳过它，尝试匹配后续内容
                        kw, l = self._skip_compound_safe_and_match(text, pos + 1, text_len)
                        if kw:
                            return kw, l
                        # 后续无法形成关键字，继续使用当前关键字
                    return candidate, length
        
        return None, 0
    
    def _try_match_symbol(self, source: str, i: int, line: int, col: int) -> Tuple[Optional[Token], int]:
        """尝试匹配符号"""
        ch = source[i]
        n = len(source)
        
        # 多字符运算符（必须在单字符之前检查）
        # 管道操作符 ->
        if ch == '-' and i + 1 < n and source[i+1] == '>':
            return Token(TokenType.ARROW, '->', line, col), 2
        
        # 海象运算符 := （不支持）
        if ch == ':' and i + 1 < n and source[i+1] == '=':
            return Token(TokenType.WALRUS, ':=', line, col), 2
        
        # 比较运算符（双字符）
        if ch == '=' and i + 1 < n and source[i+1] == '=':
            return Token(TokenType.EQ_EQ, '==', line, col), 2
        if ch == '!' and i + 1 < n and source[i+1] == '=':
            return Token(TokenType.NOT_EQ, '!=', line, col), 2
        if ch == '<' and i + 1 < n and source[i+1] == '=':
            return Token(TokenType.LESS_EQUAL, '<=', line, col), 2
        if ch == '>' and i + 1 < n and source[i+1] == '=':
            return Token(TokenType.GREATER_EQUAL, '>=', line, col), 2
        
        # 书名号（直接处理，避免与 < 和 > 比较运算符冲突）
        if ch == '《':
            return Token(TokenType.LBOOK, '《', line, col), 1
        if ch == '》':
            return Token(TokenType.RBOOK, '》', line, col), 1
        
        # 中文句号（直接映射到 PERIOD，不经过 SYMBOL_MAP 的 DOT 映射）
        if ch == '。':
            return Token(TokenType.PERIOD, ch, line, col), 1
        
        # 中文符号映射
        if ch in SYMBOL_MAP:
            mapped = SYMBOL_MAP[ch]
            token_type = self._symbol_token_map.get(mapped)
            if token_type:
                return Token(token_type, ch, line, col), 1
            # 其他符号
            return Token(TokenType.COMMA, ch, line, col), 1
        
        # 英文符号
        token_type = self._symbol_token_map.get(ch)
        if token_type:
            return Token(token_type, ch, line, col), 1
        
        return None, 0
    
    def _tokenize_string(self, source: str, i: int, line: int, col: int) -> Tuple[Token, int]:
        """处理字符串"""
        start_col = col
        quote_char = source[i]

        if quote_char in _QUOTE_MAP:
            # 中文引号
            close_quote = _CLOSE_QUOTE_MAP[quote_char]
            
            j = i + 1
            chars = []
            while j < len(source) and source[j] != close_quote:
                chars.append(source[j])
                j += 1
            
            if j >= len(source):
                raise LexerError(f"字符串未闭合: 以 '{quote_char}' 开头的字符串缺少匹配的 '{close_quote}'", line, start_col)
            
            value = ''.join(chars)
            return Token(TokenType.STRING, value, line, start_col), j - i + 1
        else:
            # 英文引号
            j = i + 1
            chars = []
            while j < len(source) and source[j] != quote_char:
                if source[j] == '\\' and j + 1 < len(source):
                    next_ch = source[j + 1]
                    if next_ch == 'n':
                        chars.append('\n')
                    elif next_ch == 't':
                        chars.append('\t')
                    elif next_ch == 'r':
                        chars.append('\r')
                    elif next_ch == '\\':
                        chars.append('\\')
                    elif next_ch == quote_char:
                        chars.append(quote_char)
                    elif next_ch == 'x' and j + 3 < len(source):
                        hex_str = source[j+2:j+4]
                        try:
                            chars.append(chr(int(hex_str, 16)))
                            j += 4
                            continue
                        except ValueError:
                            chars.append(next_ch)
                    elif next_ch == '0':
                        chars.append('\0')
                    else:
                        # 未识别的转义序列，保留反斜杠和后续字符
                        # 如 \d → \d（而非丢弃反斜杠只剩 d）
                        chars.append('\\')
                        chars.append(next_ch)
                    j += 2
                else:
                    chars.append(source[j])
                    j += 1
            
            if j >= len(source):
                raise LexerError(f"字符串未闭合: 以 '{quote_char}' 开头的字符串缺少匹配的引号", line, start_col)
            
            value = ''.join(chars)
            return Token(TokenType.STRING, value, line, start_col), j - i + 1
    
    def _tokenize_fstring(self, source: str, i: int, line: int, col: int) -> Tuple[Token, int]:
        """处理 f-string：f"..." 或 f'...'，支持嵌套 {expr} 和内部引号"""
        start_col = col
        # 跳过 f 前缀
        i += 1
        col += 1
        quote_char = source[i]
        
        j = i + 1
        chars = []
        brace_depth = 0
        # 追踪花括号内的引号状态
        inner_quote = None
        
        while j < len(source):
            ch = source[j]
            
            # 处理转义字符
            if ch == '\\' and j + 1 < len(source):
                chars.append(ch)
                chars.append(source[j + 1])
                j += 2
                continue
            
            # 处理花括号内的引号
            if brace_depth > 0:
                if inner_quote is not None:
                    # 在花括号内的字符串中
                    if ch == '\\' and j + 1 < len(source):
                        chars.append(ch)
                        chars.append(source[j + 1])
                        j += 2
                        continue
                    if ch == inner_quote:
                        inner_quote = None
                    chars.append(ch)
                    j += 1
                    continue
                elif ch in '"\'':
                    # 进入花括号内的字符串
                    inner_quote = ch
                    chars.append(ch)
                    j += 1
                    continue
            
            # 处理花括号
            if ch == '{':
                if j + 1 < len(source) and source[j + 1] == '{':
                    # 转义的花括号 {{
                    chars.append('{')
                    chars.append('{')
                    j += 2
                    continue
                brace_depth += 1
                chars.append(ch)
                j += 1
                continue
            elif ch == '}':
                if j + 1 < len(source) and source[j + 1] == '}':
                    # 转义的花括号 }}
                    chars.append('}')
                    chars.append('}')
                    j += 2
                    continue
                if brace_depth > 0:
                    brace_depth -= 1
                chars.append(ch)
                j += 1
                continue
            
            # 在花括号深度为0时，遇到匹配的引号则结束
            if brace_depth == 0 and ch == quote_char:
                j += 1  # 跳过闭合引号
                break
            
            # 处理换行（f-string 不支持裸换行，但数据集中可能有）
            chars.append(ch)
            j += 1
        
        if j >= len(source) and (brace_depth > 0 or source[j - 1] != quote_char):
            raise LexerError(f"f-string未闭合: 以 f'{quote_char}' 开头的f-string缺少匹配的引号", line, start_col)
        
        value = ''.join(chars)
        return Token(TokenType.FSTRING, value, line, start_col), j - i + 1
    
    def _tokenize_embed_block(self, source: str, i: int, line: int, col: int, prefix_len: int = 2) -> Tuple[Optional[Token], int]:
        """处理嵌入块 / L4 外语引用块

        语法格式（两种写法等价，任意组合都兼容）：
            嵌入 Python:   <原始代码>   结束嵌入   （v3.3 原写法，2字前缀）
            引   Python:   <原始代码>   结束引     （v4.0 推荐，1字前缀）
            引   Python:   <原始代码>   结束嵌入   （容错：混用也可以）
            嵌入 Python:   <原始代码>   结束引     （容错：混用也可以）

        将整个嵌入块作为一个 EMBED_BLOCK token 返回，
        token.value 为 (language, code) 元组。
        如果不是嵌入块（如"嵌入"作为普通标识符），返回 (None, 0)。
        """
        n = len(source)
        start_col = col
        j = i + prefix_len  # 跳过前缀（嵌入=2字，引=1字）
        col += prefix_len
        
        # 跳过空格
        while j < n and source[j] in ' \t':
            j += 1
            col += 1
        
        # 读取语言名称（ASCII 字母，直到冒号或换行）
        lang_chars = []
        while j < n and source[j] not in ':\n' and source[j] != '：':
            lang_chars.append(source[j])
            j += 1
            col += 1
        
        language = ''.join(lang_chars).strip()
        
        # 必须有冒号才视为嵌入块
        if j >= n or source[j] not in ':：':
            return None, 0
        j += 1  # 跳过冒号
        col += 1
        
        # 检查语言名称是否有效
        if not language:
            return None, 0
        
        # 跳过冒号后的同一行剩余内容（到换行）
        while j < n and source[j] != '\n':
            j += 1
        if j < n:
            j += 1  # 跳过换行
        
        # 收集嵌入代码，直到遇到 "结束嵌入" 或 "结束引"（两种都可，容错）
        code_lines = []
        end_markers = ('结束嵌入', '结束引')
        while j < n:
            # 检查当前行是否为结束标记
            # 跳过行首空白
            line_start = j
            k = j
            while k < n and source[k] in ' \t':
                k += 1
            # 检查是否匹配任一结束标记
            matched_end = None
            for em in end_markers:
                if source[k:k+len(em)] == em:
                    matched_end = em
                    break
            if matched_end:
                # 确认后面是换行或EOF
                after = k + len(matched_end)
                if after >= n or source[after] == '\n' or source[after] in ' \t。':
                    # 计算消耗的字符数
                    consumed = after - i if after < n else n - i
                    # 如果后面是句号，也消耗掉
                    if after < n and source[after] == '。':
                        consumed = after + 1 - i
                    code = '\n'.join(code_lines)
                    return Token(TokenType.EMBED_BLOCK, (language, code), line, start_col), consumed
            
            # 收集这一行
            line_end = j
            while line_end < n and source[line_end] != '\n':
                line_end += 1
            code_lines.append(source[line_start:line_end] if line_end < n else source[line_start:])
            j = line_end + 1 if line_end < n else n
        
        # 到达 EOF 仍未找到结束标记
        raise LexerError(
            f"L4引用/嵌入块未闭合：缺少「结束嵌入」或「结束引」标记",
            line, start_col
        )

    def _tokenize_number(self, source: str, i: int, line: int, col: int) -> Tuple[Token, int]:
        """处理数字"""
        start = i
        j = i
        n = len(source)
        _is_digit = _is_ascii_digit

        # 负号
        if source[j] == '-':
            j += 1

        # 整数部分
        while j < n and _is_digit(source[j]):
            j += 1

        # 小数部分
        if j < n and source[j] == '.':
            j += 1
            while j < n and _is_digit(source[j]):
                j += 1
        
        num_str = source[start:j]
        if '.' in num_str:
            value = float(num_str)
        else:
            value = int(num_str)
        
        return Token(TokenType.NUMBER, value, line, col), j - start
    
    def _tokenize_chinese_number(self, source: str, i: int, line: int, col: int) -> Tuple[Token, int]:
        """处理中文数字（简单版：只处理一到十）"""
        ch = source[i]
        value = self.CHINESE_DIGITS.get(ch)
        
        if value is None:
            raise LexerError(f"无效的中文数字: {ch}", line, col)
        
        return Token(TokenType.CHINESE_NUM, value, line, col), 1
    
    def _tokenize_identifier_or_keyword(self, source: str, i: int, line: int, col: int, user_definitions: Set[str] = None) -> Tuple[List[Token], int]:
        """
        处理标识符和关键字（核心：三层分词机制）

        决策29：
        1. 类型切换自动分词 - 甲加1 → [甲] [加] [1]
        2. 双字关键词优先匹配 - 定义甲 → [定义] [甲]
        3. 元数驱动参数收集 - 打印 甲 → [打印] [甲]
        """
        if user_definitions is None:
            user_definitions = set()

        tokens = []
        n = len(source)
        _is_han = _is_han_fast
        _is_ascii_alnum_f = _is_ascii_alnum
        _Token = Token
        _TokenType = TokenType

        # 收集连续的汉字（或英文标识符）
        if _is_han(source[i]):
            # 汉字处理：实现三层分词
            consumed = self._tokenize_chinese_sequence(source, i, line, col, tokens, user_definitions)

            # 处理汉字后紧跟ASCII字母/数字的情况（如"计算器1"）
            next_pos = i + consumed
            if next_pos < n:
                next_ch = source[next_pos]
                cp_next = ord(next_ch)
                if cp_next < 128 and (_is_ascii_alnum_f(next_ch) or next_ch == '_'):
                    j = next_pos
                    while j < n:
                        ch = source[j]
                        cp = ord(ch)
                        if cp < 128 and (_is_ascii_alnum_f(ch) or ch == '_'):
                            j += 1
                        else:
                            break
                    suffix = source[next_pos:j]
                    # 将后缀合并到最后一个token
                    if tokens:
                        last = tokens[-1]
                        if last.type == TokenType.IDENTIFIER:
                            tokens[-1] = _Token(_TokenType.IDENTIFIER, last.value + suffix, last.line, last.col)
                            consumed += len(suffix)
                        elif last.type == TokenType.KEYWORD:
                            # 关键字后紧跟ASCII字母（如"分割Pointer_内部"），合并为完整标识符
                            # 语法如"引 Python:"中间有空格，不会进入此分支
                            # 不合并数字后缀（如"至10"、"为123"），避免破坏范围表达式/赋值
                            if suffix[0].isalpha() or suffix[0] == '_':
                                tokens[-1] = _Token(_TokenType.IDENTIFIER, last.value + suffix, last.line, last.col)
                                consumed += len(suffix)

            return tokens, consumed
        else:
            # 英文标识符：收集连续的字母、数字、下划线
            j = i + 1
            while j < n and (_is_ascii_alnum_f(source[j]) or source[j] == '_'):
                j += 1

            # 检查是否紧跟汉字（如 evennum集），如果是则合并
            # 但只合并非关键字的汉字，避免破坏 left至right 这类范围表达式
            while j < n and _is_han(source[j]):
                # 检查从 j 开始的汉字序列是否是关键字
                k = j
                while k < n and _is_han(source[k]):
                    k += 1
                han_seq = source[j:k]
                # 如果汉字序列是关键字，则不合并
                if han_seq in ALL_KEYWORDS:
                    break
                j = k

            word = source[i:j]
            if word in ALL_KEYWORDS:
                tokens.append(_Token(_TokenType.KEYWORD, word, line, col))
            else:
                tokens.append(_Token(_TokenType.IDENTIFIER, word, line, col))

            return tokens, j - i
    
    def _tokenize_chinese_sequence(self, source: str, i: int, line: int, col: int, tokens: List[Token], user_definitions: Set[str] = None) -> int:
        """
        处理连续的汉字序列（实现三层分词）

        这是核心方法，实现决策29的三层机制
        """
        if user_definitions is None:
            user_definitions = set()

        # 局部变量缓存（减少属性查找和函数调用开销）
        _is_han = _is_han_fast
        _match_kw = self._match_keyword
        _try_parse_cn_num = self._try_parse_chinese_number
        _simple_nums = _SIMPLE_CHINESE_NUMBERS
        _cn_digits = _CHINESE_DIGITS
        _compound_safe = _COMPOUND_SAFE_SINGLE_KEYWORDS
        _symbol_map = SYMBOL_MAP
        _common_compounds = COMMON_COMPOUND_WORDS
        _punctuation = _CJK_PUNCTUATION
        _Token = Token
        _TokenType = TokenType
        _tokens_append = tokens.append

        n = len(source)
        consumed = 0
        current_col = col
        
        # 安全计数器，防止无限循环
        _loop_safety = 0

        while i + consumed < n:
            _loop_safety += 1
            if _loop_safety > 100:
                raise RuntimeError(f"词法分析内部错误: 汉字序列分词超出安全上限 ({_loop_safety}次迭代), 当前位置: {i + consumed}")

            pos = i + consumed
            ch = source[pos]

            # 遇到非汉字，结束
            if not _is_han(ch):
                break

            # 遇到符号，结束
            if ch in _symbol_map or ch in _punctuation:
                break

            # 检查是否是简单中文数字（一～十）
            if ch in _simple_nums:
                # 检查下一个位置是否是关键字或符号
                next_pos = pos + 1

                # 情况1：下一个字符不是汉字（如 "三。" 中的 "。"）
                # 情况2：下一个字符是关键字（如 "三加" 中的 "加"）
                # 情况3：下一个字符是符号
                # 在这些情况下，当前中文数字应该独立输出

                is_standalone_num = False

                if next_pos >= n:
                    # 到达字符串末尾
                    is_standalone_num = True
                elif not _is_han(source[next_pos]):
                    # 下一个字符不是汉字
                    is_standalone_num = True
                else:
                    # 检查下一个位置是否能匹配关键字
                    next_keyword, _ = _match_kw(source, next_pos)
                    if next_keyword:
                        # 下一个是关键字，当前数字独立
                        is_standalone_num = True
                    elif source[next_pos] in _symbol_map or source[next_pos] in _punctuation:
                        # 下一个是符号
                        is_standalone_num = True

                if is_standalone_num:
                    # 单独的中文数字，输出为数字
                    value = _cn_digits[ch]
                    _tokens_append(_Token(_TokenType.CHINESE_NUM, value, line, current_col))
                    consumed += 1
                    current_col += 1
                    continue

            # 先收集完整的汉字序列
            j = pos
            while j < n and _is_han(source[j]):
                # 遇到符号停止
                if source[j] in _symbol_map or source[j] in _punctuation:
                    break
                j += 1
            
            full_identifier = source[pos:j]
            
            # 检查完整标识符是否是常见复合词（优先级高于中文数字拆分）
            if full_identifier in _common_compounds:
                # 如果完整标识符同时也是关键字（如"创建回调"在VERB_ARITY中），作为关键字输出
                kw_check, _ = _match_kw(source, pos)
                if kw_check == full_identifier:
                    _tokens_append(_Token(_TokenType.KEYWORD, full_identifier, line, current_col))
                    consumed += len(full_identifier)
                    current_col += len(full_identifier)
                    continue
                # 常见复合词，作为整体标识符，不拆分
                _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))
                consumed += len(full_identifier)
                current_col += len(full_identifier)
                continue
            
            # 检查完整标识符是否在用户定义中（优先级高于中文数字拆分）
            if full_identifier in user_definitions:
                # 完整标识符在用户定义中，优先作为标识符，不拆分
                _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))
                consumed += len(full_identifier)
                current_col += len(full_identifier)
                continue
            
            # 检查是否是中文数字（如三点一四一五九、一百零一）
            if full_identifier:
                num_value, num_len = _try_parse_cn_num(source, pos)
                if num_value is not None and num_len == len(full_identifier):
                    # 整个标识符是中文数字
                    _tokens_append(_Token(_TokenType.CHINESE_NUM, num_value, line, current_col))
                    consumed += num_len
                    current_col += num_len
                    continue
                elif num_value is not None and num_len > 0:
                    # 前缀是中文数字（如"九十那么"中的"九十"）
                    # 输出CHINESE_NUM，剩余部分由后续循环处理
                    _tokens_append(_Token(_TokenType.CHINESE_NUM, num_value, line, current_col))
                    consumed += num_len
                    current_col += num_len
                    continue
            
            # 检查前缀是否在用户定义中（如"阶乘结果"在定义中，当前标识符为"阶乘结果等于"）
            # 但若完整标识符本身是关键字（如"列表弹出"在VERB_ARITY中），则优先识别为关键字
            if user_definitions:
                prefix_matched = None
                # 先检查完整标识符是否本身就是关键字（优先级高于用户定义前缀匹配）
                full_is_keyword = False
                kw_check, _ = _match_kw(source, pos)
                if kw_check == full_identifier:
                    full_is_keyword = True
                if not full_is_keyword:
                    for plen in range(len(full_identifier) - 1, 0, -1):
                        prefix = full_identifier[:plen]
                        if prefix in user_definitions:
                            prefix_matched = prefix
                            break
                if prefix_matched:
                    # 检查剩余部分是否为 compound_safe 单字关键字
                    # 如果是，则不拆分（保持完整标识符），避免：
                    # - "路径段"被拆为"路径"+"段"（段是compound_safe）
                    # - "甲序"被拆为"甲"+"序"（序是compound_safe）
                    remaining = full_identifier[len(prefix_matched):]
                    if len(remaining) == 1 and remaining in _compound_safe:
                        prefix_matched = None
                    else:
                        # 输出用户定义的前缀部分作为标识符，剩余部分由后续循环处理
                        _tokens_append(_Token(_TokenType.IDENTIFIER, prefix_matched, line, current_col))
                        consumed += len(prefix_matched)
                        current_col += len(prefix_matched)
                        continue
            
            # 第一层：尝试最长匹配关键字
            keyword, length = _match_kw(source, pos)
            
            # 再次检查单个关键字是否在用户定义中
            if keyword and keyword in user_definitions:
                # 用户定义的标识符，不作为关键字
                keyword = None

            if keyword:
                # 单字动词在词首且词长>1时不直接匹配，避免拆开复合词
                # 例如"列表"(len=2)不应拆为 列(动词)+表
                # 但独立出现的"加"(len=1)仍应匹配为关键字
                # 例外：后续字符是中文数字（如"加五"），应拆分为 加(动词)+五(数字)
                # 另外：只有当关键字在词首位置时才跳过，词中出现的运算符应正常识别
                skip_verb = False
                if length == 1 and keyword in _compound_safe and len(full_identifier) > 1:
                    # 检查是否在词首位置（相对于 full_identifier）
                    in_word_start = (pos == i + consumed)  # 当前位置是当前处理的起始位置
                    if in_word_start:
                        # 检查后续字符是否构成中文数字
                        remaining = full_identifier[1:]
                        is_chinese_num = False
                        if len(remaining) == 1 and remaining[0] in _simple_nums:
                            is_chinese_num = True
                        else:
                            num_val, num_len = _try_parse_cn_num(remaining, 0)
                            if num_val is not None and num_len >= len(remaining):
                                is_chinese_num = True
                        if not is_chinese_num:
                            skip_verb = True
                
                # 动词在词首且后面还有内容时跳过：动词作为复合标识符前缀时不应拆分
                # 例如"输出格式"不应拆为 输出(关键字)+格式，而应作为整体标识符
                # 注意：只对 VERB_ARITY 中的动词生效，不对"返回"等语句关键字生效
                if length > 1 and keyword in VERB_ARITY and len(full_identifier) > length:
                    skip_verb = True
                
                # 特殊处理："当"关键字只在后面跟着冒号或在标识符开头时才作为关键字
                # 否则作为复合词的一部分（如"当前时间戳"中的"当"）
                if length == 1 and keyword == '当':
                    # 检查整个汉字序列后面的字符
                    word_end_pos = i + consumed + len(full_identifier)
                    if word_end_pos < n:
                        word_next_char = source[word_end_pos]
                        # 如果整个汉字序列后面是冒号，"当"作为关键字
                        if word_next_char == ':':
                            # 作为关键字处理，不跳过
                            pass
                        else:
                            # 检查"当"后面是否紧跟非汉字字符（如空格、符号等）
                            next_pos = pos + length
                            if next_pos < n:
                                next_char = source[next_pos]
                                # 如果"当"后面是冒号或空格，作为关键字
                                if next_char == ':' or next_char.isspace():
                                    pass
                                else:
                                    # 否则作为复合词的一部分
                                    skip_verb = True
                
                if skip_verb:
                    # 单字动词在多字词词首，跳过主匹配，让嵌入式检测处理
                    keyword = None
                else:
                    # 匹配到关键字（非单字动词或不在词首）
                    _tokens_append(_Token(_TokenType.KEYWORD, keyword, line, current_col))
                    consumed += length
                    current_col += length
                    # 更新 full_identifier 为剩余部分
                    full_identifier = full_identifier[length:]
                    # 如果还有剩余内容，进入下一个循环迭代处理
                    if full_identifier:
                        continue
                    # 没有剩余内容，结束本次迭代
                    break
            
            if not keyword:
                # 未匹配到关键字（或单字动词被跳过），检查是否内嵌有关键字
                # 例如"初始值加数值"中的"加"应该被识别为关键字
                # 单字关键字和 OPERATOR_VERBS 中的多字关键字（如大于、小于、等于）都可能内嵌
                embedded_found = False
                scan_pos = 0
                while scan_pos < len(full_identifier):
                    sub_kw, sub_len = self._match_keyword(source, i + consumed + scan_pos)
                    if sub_kw and sub_kw not in user_definitions:
                        # 检查是否应该跳过这个关键字
                        skip_kw = False
                        if sub_len == 1 and sub_kw in OPERATOR_VERBS:
                            # 单字运算符动词：检查后面是否是括号（可能是函数名的一部分，如"阶乘"）
                            next_pos = i + consumed + scan_pos + sub_len
                            if next_pos < len(source):
                                next_char = source[next_pos]
                                if next_char == '(':
                                    # 后面跟着括号，作为复合词的一部分（如"阶乘"）
                                    skip_kw = True
                            # 否则作为运算符识别（不跳过）
                            # 例如：甲加乙 -> [甲] [加] [乙]
                        elif sub_len == 1 and sub_kw == '当':
                            # "当"关键字：检查后面是否是冒号或空格
                            next_pos = i + consumed + scan_pos + sub_len
                            if next_pos < len(source):
                                next_char = source[next_pos]
                                if next_char != ':' and not next_char.isspace():
                                    skip_kw = True
                        elif sub_len == 1 and sub_kw in self.compound_safe_single_keywords:
                            # 单字 compound_safe 关键字：直接跳过
                            skip_kw = True
                        elif sub_kw in IDENTIFIER_SAFE_KEYWORDS:
                            # 标识符安全关键字（如"函数"、"输出"）：是复合标识符的一部分，跳过
                            skip_kw = True
                        
                        if not skip_kw:
                            # 不是需要跳过的关键字，标记为内嵌关键字
                            embedded_found = True
                            break
                    scan_pos += 1
                
                if embedded_found:
                    # 有内嵌关键字，分段输出
                    scan_pos = 0
                    while scan_pos < len(full_identifier):
                        abs_pos = i + consumed + scan_pos
                        sub_kw, sub_len = self._match_keyword(source, abs_pos)
                        if sub_kw and sub_kw not in user_definitions:
                            # 跳过 compound_safe_single 的单字关键字（如"典"），继续扫描
                            # 这允许"字典创建"中的"典"被跳过，从而识别"创建"为关键字
                            # 对于运算符动词（加、减、乘、除、模、幂、大于、小于等）：
                            # - 如果后面跟着普通汉字，作为复合词的一部分，跳过
                            # - 如果后面跟着数字或符号，作为运算符识别
                            # 特殊处理："当"关键字只在后面跟着冒号时才作为关键字
                            if sub_len == 1 and sub_kw == '当':
                                # 检查后面是否是冒号
                                next_pos = abs_pos + sub_len
                                if next_pos < len(source):
                                    next_char = source[next_pos]
                                    # 只有当后面是冒号或空格时，才作为关键字
                                    if next_char != ':' and not next_char.isspace():
                                        scan_pos += sub_len
                                        continue
                            elif sub_len == 1 and sub_kw in self.compound_safe_single_keywords:
                                # 单字 compound_safe 关键字（非"当"）
                                if sub_kw in OPERATOR_VERBS:
                                    if scan_pos == 0:
                                        # 运算符在词首，作为复合词的一部分（如"加法"、"减法"）
                                        # 例如：加法(3, 5) → 加法 作为整体标识符
                                        scan_pos += sub_len
                                        continue
                                    # 运算符在词中，识别为关键字（不跳过）
                                    # 例如：甲加乙 -> [甲] [加] [乙]
                                    pass
                                else:
                                    # 只跳过不在词尾的关键字；在词尾时作为关键字输出
                                    if scan_pos + sub_len < len(full_identifier):
                                        scan_pos += sub_len
                                        continue
                            elif sub_len == 1 and sub_kw in OPERATOR_VERBS:
                                # 单字运算符动词（不在 compound_safe 中）
                                # 检查后面是否是括号（可能是函数名的一部分，如"阶乘"）
                                next_pos = abs_pos + sub_len
                                if next_pos < len(source):
                                    next_char = source[next_pos]
                                    if next_char == '(':
                                        # 后面跟着括号，作为复合词的一部分（如"阶乘"）
                                        scan_pos += sub_len
                                        continue
                                # 否则作为运算符识别（不跳过）
                                # 例如：甲加乙 -> [甲] [加] [乙]
                                pass
                            elif sub_len > 1 and sub_kw in OPERATOR_VERBS:
                                # 多字运算符动词（大于、小于、等于等）
                                # 检查前后是否都是普通汉字（组成复合词的情况）
                                prev_is_han = (scan_pos > 0 and self._is_han(full_identifier[scan_pos - 1]))
                                next_pos = abs_pos + sub_len
                                next_is_han = (next_pos < len(source) and self._is_han(source[next_pos])
                                              and source[next_pos] not in self.SIMPLE_CHINESE_NUMBERS)
                                # 如果前后都是普通汉字，可能是复合词的一部分，跳过
                                # 但常见比较运算符（大于、小于、等于）在表达式中很常见，应该优先识别为运算符
                                # 策略：多字比较运算符总是作为关键字识别
                                pass  # 不跳过，继续输出为关键字
                            elif sub_len > 1 and sub_kw in IDENTIFIER_SAFE_KEYWORDS:
                                # 标识符安全关键字（如"函数"、"输出"）：跳过，作为复合标识符的一部分
                                scan_pos += sub_len
                                continue
                            elif sub_len > 1:
                                # 其他多字关键字（如接收、段落等），直接输出
                                pass  # 不跳过，继续输出为关键字
                            # 输出关键字前的标识符部分
                            if scan_pos > 0:
                                id_part = full_identifier[:scan_pos]
                                num_value = self._convert_chinese_number(id_part)
                                if num_value is not None:
                                    tokens.append(Token(TokenType.CHINESE_NUM, num_value, line, current_col))
                                else:
                                    tokens.append(Token(TokenType.IDENTIFIER, id_part, line, current_col))
                                consumed += scan_pos
                                current_col += scan_pos
                                full_identifier = full_identifier[scan_pos:]
                                scan_pos = 0
                                abs_pos = i + consumed
                                sub_kw, sub_len = self._match_keyword(source, abs_pos)
                                if not (sub_kw and sub_kw not in user_definitions):
                                    break
                                # 重新匹配后，再次检查是否需要跳过
                                skip_after_rematch = False
                                if sub_len == 1 and sub_kw == '当':
                                    next_pos = abs_pos + sub_len
                                    if next_pos < len(source):
                                        next_char = source[next_pos]
                                        if next_char != ':' and not next_char.isspace():
                                            skip_after_rematch = True
                                elif sub_len == 1 and sub_kw in self.compound_safe_single_keywords:
                                    if sub_kw in OPERATOR_VERBS:
                                        # 运算符动词：不跳过，始终识别为关键字
                                        # 例如：甲加乙 → 加 作为关键字
                                        pass
                                    elif sub_len < len(full_identifier):
                                        # 只跳过不在词尾的关键字；在词尾时作为关键字输出
                                        skip_after_rematch = True
                                elif sub_len == 1 and sub_kw in OPERATOR_VERBS:
                                    # 单字运算符动词：检查后面是否是括号（可能是函数名的一部分，如"阶乘"）
                                    next_pos = abs_pos + sub_len
                                    if next_pos < len(source):
                                        next_char = source[next_pos]
                                        if next_char == '(':
                                            # 后面跟着括号，作为复合词的一部分（如"阶乘"）
                                            skip_after_rematch = True
                                elif sub_kw in IDENTIFIER_SAFE_KEYWORDS:
                                    # 标识符安全关键字（如"函数"、"输出"）：跳过，作为复合标识符的一部分
                                    skip_after_rematch = True
                                if skip_after_rematch:
                                    scan_pos += sub_len
                                    continue
                            # 输出关键字
                            tokens.append(Token(TokenType.KEYWORD, sub_kw, line, current_col))
                            consumed += sub_len
                            current_col += sub_len
                            full_identifier = full_identifier[sub_len:]
                            scan_pos = 0
                        else:
                            scan_pos += 1
                    # 输出剩余标识符部分
                    if full_identifier:
                        num_value, num_len = self._try_parse_chinese_number(source, i + consumed)
                        if num_value is not None and num_len == len(full_identifier):
                            tokens.append(Token(TokenType.CHINESE_NUM, num_value, line, current_col))
                            consumed += num_len
                            current_col += num_len
                        else:
                            tokens.append(Token(TokenType.IDENTIFIER, full_identifier, line, current_col))
                            consumed += len(full_identifier)
                            current_col += len(full_identifier)
                else:
                    # 无嵌入关键字，使用前面收集的完整标识符
                    if full_identifier:
                        # 尝试解析为中文数字（支持多位如"四十二"、"一百"）
                        num_value, num_len = self._try_parse_chinese_number(source, i + consumed)
                        if num_value is not None and num_len == len(full_identifier):
                            tokens.append(Token(TokenType.CHINESE_NUM, num_value, line, current_col))
                            consumed += num_len
                            current_col += num_len
                        else:
                            tokens.append(Token(TokenType.IDENTIFIER, full_identifier, line, current_col))
                            consumed += len(full_identifier)
                            current_col += len(full_identifier)
                    else:
                        # 单个非关键字汉字，检查是否为中文数字
                        if ch in self.SIMPLE_CHINESE_NUMBERS:
                            value = self.CHINESE_DIGITS[ch]
                            tokens.append(Token(TokenType.CHINESE_NUM, value, line, current_col))
                        else:
                            tokens.append(Token(TokenType.IDENTIFIER, ch, line, current_col))
                        consumed += 1
                        current_col += 1
        
        return consumed
    
    def _scan_user_definitions(self, source: str) -> Set[str]:
        """
        预扫描：收集用户定义的变量名和函数名

        用于避免将用户定义的标识符错误拆分为关键字
        """
        definitions = set()
        i = 0
        n = len(source)
        _is_han = _is_han_fast
        _is_space_tab = _is_ascii_space_tab

        # 安全计数器（防止意外死循环）
        _scan_safety = 0

        while i < n:
            _scan_safety += 1
            if _scan_safety > 1000000:
                raise RuntimeError(f"_scan_user_definitions 超出安全上限 ({_scan_safety}次迭代), i={i}, n={n}")

            # 查找段落定义：《段名》段 或 《类名》类 或 《方法名》方法(参数)
            if source[i] == '《':
                j = i + 1
                # 收集段名/类名/方法名
                k = j
                while k < n and source[k] != '》':
                    k += 1
                if k < n and k > j:
                    name = source[j:k]
                    # 《Name》段 或 《Name》类
                    next_start = k + 1
                    if next_start < n:
                        # 检查后跟"方法("：收集括号内的参数名，并注册方法名
                        if source[next_start:next_start+2] == '方法' and next_start+2 < n and source[next_start+2] == '(':
                            # 注册方法名（如"添加成绩"、"打印信息"）
                            if name not in ALL_KEYWORDS and name not in VERB_ARITY:
                                definitions.add(name)
                            # 收集括号内的参数
                            p = next_start + 3  # 跳过 方法(
                            while p < n and source[p] != ')':
                                # 跳过空白
                                if _is_space_tab(source[p]):
                                    p += 1
                                    continue
                                # 跳过逗号
                                if source[p] == ',' or source[p] == '，':
                                    p += 1
                                    continue
                                # 收集参数名
                                param_start = p
                                while p < n and _is_han(source[p]) and source[p] not in '，, )）':
                                    p += 1
                                if p > param_start:
                                    param_name = source[param_start:p]
                                    if param_name not in ALL_KEYWORDS:
                                        definitions.add(param_name)
                                else:
                                    # 非汉字的参数（如ASCII字符'x'），向前移动一位避免死循环
                                    p += 1
                        elif name not in ALL_KEYWORDS and name not in VERB_ARITY:
                            definitions.add(name)
                i = k + 1
                continue

            # 查找 "函数/段落 段名 参数 参数名" 格式
            if source[i:i+2] == '函数' or source[i:i+2] == '段落':
                j = i + 2
                # 跳过空白
                while j < n and _is_space_tab(source[j]):
                    j += 1
                # 收集段名（遇到段落语法关键字或冒号停止）
                k = j
                while k < n and _is_han(source[k]):
                    # 检查当前位置是否匹配段落语法关键字（接收、返回）
                    kw, kw_len = self._match_keyword(source, k)
                    if kw and kw_len > 0 and kw in ('接收', '返回'):
                        break
                    k += 1
                if k > j:
                    segment_name = source[j:k]
                    # 收集段落名（允许覆盖动词名称）
                    if segment_name not in ALL_KEYWORDS:
                        definitions.add(segment_name)

                # 检查是否有 "参数" 关键字
                j = k
                while j < n and _is_space_tab(source[j]):
                    j += 1
                if source[j:j+2] == '参数':
                    j += 2
                    # 跳过空白
                    while j < n and _is_space_tab(source[j]):
                        j += 1
                    # 收集参数名（可能多个参数）
                    while j < n:
                        k = j
                        while k < n and _is_han(source[k]) and source[k] not in '。：':
                            k += 1
                        if k > j:
                            param_name = source[j:k]
                            # 排除关键字和动词
                            if param_name not in ALL_KEYWORDS and param_name not in VERB_ARITY:
                                definitions.add(param_name)
                        j = k
                        # 跳过空白
                        while j < n and _is_space_tab(source[j]):
                            j += 1
                        # 检查是否结束（句号、冒号或换行）
                        if j >= n or source[j] in '。：\n':
                            break
                i = j
                continue

            # 查找 "段 函数名(参数)" 模式（新式函数定义语法）
            if source[i] == '段' and i + 1 < n and _is_space_tab(source[i + 1]):
                j = i + 1
                # 跳过空白
                while j < n and _is_space_tab(source[j]):
                    j += 1
                # 收集函数名
                k = j
                while k < n and _is_han(source[k]):
                    k += 1
                if k > j:
                    func_name = source[j:k]
                    # 跳过空白，检查是否紧跟 ( 或 （
                    m = k
                    while m < n and _is_space_tab(source[m]):
                        m += 1
                    if m < n and source[m] in '（(':
                        # 收集函数名
                        if func_name not in ALL_KEYWORDS and func_name not in VERB_ARITY:
                            definitions.add(func_name)
                        # 收集括号内的参数
                        p = m + 1
                        while p < n and source[p] not in ')）':
                            if _is_space_tab(source[p]) or source[p] in '，,':
                                p += 1
                                continue
                            # 收集参数名
                            param_start = p
                            while p < n and _is_han(source[p]) and source[p] not in '，, )）':
                                p += 1
                            if p > param_start:
                                param_name = source[param_start:p]
                                if param_name not in ALL_KEYWORDS:
                                    definitions.add(param_name)
                            else:
                                p += 1
                        # 跳过右括号
                        if p < n and source[p] in ')）':
                            p += 1
                        i = p
                    else:
                        # 没有括号，属于函数调用（如 段 函数名 参数 参数名），跳过函数名
                        i = k
                    continue
                i = k
                continue

            # 查找 "定义" 或 "设" 开头的定义语句
            if source[i:i+2] == '定义':
                j = i + 2
                # 跳过空白
                while j < n and _is_space_tab(source[j]):
                    j += 1
                # 收集标识符（收集到赋值关键字"等于"/"为"为止）
                k = j
                while k < n and _is_han(source[k]):
                    # 只把赋值关键字（等于、为）作为断点
                    # 其他关键字（如结束、返回、跳过等）都可以是变量名的一部分
                    next_kw, length = self._match_keyword(source, k)
                    if next_kw and next_kw in ('等于', '为'):
                        break
                    # 否则继续前进
                    if next_kw:
                        k += length
                    else:
                        k += 1
                if k > j:
                    name = source[j:k]
                    definitions.add(name)
                i = k
            elif source[i] == '设':
                j = i + 1
                # 跳过空白
                while j < n and _is_space_tab(source[j]):
                    j += 1
                # 收集标识符（设 甲 为/等于 值）
                k = j
                collected_something = False
                while k < n and _is_han(source[k]):
                    # 只检查是否遇到"为"或"等于"关键字（跳过空格），动词在开头时可跳过
                    lookahead = k
                    while lookahead < n and _is_space_tab(source[lookahead]):
                        lookahead += 1
                    if lookahead < n and source[lookahead] == '为':
                        break
                    # 检查"等于"关键字
                    next_kw_lookahead, _ = self._match_keyword(source, k)
                    if next_kw_lookahead == '等于':
                        break
                    # 在开头遇到动词（如"设阶乘结果为五"），跳过
                    next_kw, length = self._match_keyword(source, k)
                    if next_kw and next_kw in VERB_ARITY and not collected_something:
                        k += length
                        continue
                    k += 1
                    collected_something = True
                if k > j:
                    name = source[j:k]
                    # 只排除真正的关键字，动词可以作为变量名的一部分
                    if name not in ALL_KEYWORDS:
                        definitions.add(name)
                i = k
            else:
                i += 1

        return definitions
