"""
光明（Light）编程语言 - 中文分词器

【主解析器路线】此为当前主解析器路线：
  1. light_tokenizer.py  - 自定义中文分词器（无空格分词）
  2. LightLangParser.g4  - ANTLR 语法规则定义（生成 light_parser/）
  3. light_visitor.py    - 语法树访问器（转换为 AST）
  4. light_interpreter.py | light_compiler.py - 执行/编译

手写解析器（src/lexer.py, src/light_parser_v3.py）为参考实现，用于验证正确性。
历史实验文件已归档至 bootstrap/archive/。

实现决策29：无空格分词支持
- 双字关键词优先匹配
- 类型切换自动分词
- 元数驱动参数收集

使用 Python 实现自定义分词，然后将 tokens 喂给 ANTLR 解析器
"""

import re
from typing import List, Optional, Tuple
from antlr4 import *
from antlr4 import Token as AntlrToken
from antlr4.CommonTokenFactory import CommonTokenFactory
from antlr4.Lexer import TokenSource
from antlr4.Token import CommonToken


# =============================================================================
# 关键词表（按长度降序排列，优先匹配长关键词）
# =============================================================================

# 所有关键字（长关键字在前；v4.0 L0 30字单字为推荐主形式，全部兼容旧写法）
KEYWORDS = [
    # 条件判断（三字）
    '否则若', '大于等于', '小于等于',
    # 定义声明（二字）
    '数据类型', '错误', '定义', '等于', '导入', '导出', '常量', '类型', '继承', '使用', '方法', '自我', '段落', '实现', '构造', '属性',
    # 函数声明（二字）
    '接收',
    # 新语法别名（Phase 1）
    '函数',
    # 条件判断（二字）
    '如果', '那么', '否则', '结束',
    # 比较（二字）
    '大于', '小于', '不等于',
    # 循环控制（二字）
    '遍历', '跳出', '跳过',
    # 循环控制别名（Phase 3）
    '中的',   # 遍历变量中的列表 → K_FOREACH ID K_AT expr
    # 异常处理（二字）
    '尝试', '捕获', '抛出', '最终',
    # 返回（二字）
    '返回',
    # 数据操作（二字）
    '打印', '输出', '输入',
    # 复合赋值（二字，Phase 5）
    '加上', '减去', '乘以', '除以', '模以', '幂以',
    # 模式匹配（二字）
    '匹配', '情况',
    # 上下文管理器/装饰器（二字）
    '标注',
    # 嵌入块（v3.3 兼容别名）/ 外语引用块（v4.0 推荐）
    '结束嵌入', '结束引',
    '嵌入',
    # 单字（v4.0 L0 核心字推荐形式 + v3.3 兼容）
    '段', '从', '当', '父', '类', '接口', '新', '新建', '己', '设', '为', '于', '数',
    # v4.0 L0 新增单字别名（16字，兼容旧双字写法）
    '否',  # 否则
    '遍',  # 遍历
    '跳',  # 跳出
    '过',  # 跳过
    '返',  # 返回
    '承',  # 继承
    '接',  # 接口
    '配',  # 匹配
    '试',  # 尝试
    '捕',  # 捕获
    '抛',  # 抛出
    '终',  # 最终
    '自',  # 己/self
    '是',  # 判断/相等
    '导',  # 导入
    '出',  # 导出
    '引',  # 嵌入（v4.0 L4 推荐：引 Python:）
    # 逻辑（单字）
    '且', '或', '非',
    # 条件别名（单字）
    '若', '则',
    # 遍历别名（单字）
    '对',
    # 算术（单字）
    '加', '减', '乘', '除', '模', '幂',
    # 连接/属性（单字）
    '并', '之', '的',
    # 特殊值（单字）
    '真', '假', '空',
    # 内置类型（单字/二字）
    '整数', '浮数', '布尔', '任意',
    '列', '串', '典', '集',
]

# 关键词到其类型的映射
KEYWORD_TOKEN_MAP = {
    # 条件判断
    '否则若': 'K_ELSE_IF',
    '如果': 'K_IF',
    # 新语法别名：若 = 如果
    '若': 'K_IF',
    '那么': 'K_THEN',
    # 新语法别名：则 = 那么
    '则': 'K_THEN',
    '否则': 'K_ELSE',
    '结束': 'K_END',
    # 比较
    '大于等于': 'K_GE',
    '小于等于': 'K_LE',
    '不等于': 'K_NE',
    '大于': 'K_GT',
    '小于': 'K_LT',
    # 定义声明
    '定义': 'K_DEFINE',
    '等于': 'K_EQUAL',
    '段': 'K_SEGMENT',
    '段落': 'K_SEGMENT',
    # 新语法别名：函数 = 段落
    '函数': 'K_SEGMENT',
    '接收': 'K_RECEIVE',
    '类': 'K_CLASS',
    '接口': 'K_INTERFACE',
    '新': 'K_NEW',
    '新建': 'K_NEW',
    '数据类型': 'K_DATA_TYPE',
    '错误': 'K_ERROR_TYPE',
    '常量': 'K_CONST',
    '类型': 'K_TYPE',
    '导出': 'K_EXPORT',
    '导入': 'K_IMPORT',
    '从': 'K_FROM',
    '遍历': 'K_FOREACH',
    '当': 'K_WHILE',
    '跳出': 'K_BREAK',
    '跳过': 'K_CONTINUE',
    '尝试': 'K_TRY',
    '捕获': 'K_CATCH',
    '抛出': 'K_THROW',
    '返回': 'K_RETURN',
    '打印': 'K_PRINT',
    '输出': 'K_OUTPUT',
    '输入': 'K_INPUT',
    '继承': 'K_INHERIT',
    '实现': 'K_IMPLEMENTS',
    '使用': 'K_WITH',
    '父': 'K_PARENT',
    '己': 'K_SELF',
    '方法': 'K_METHOD',
    '属性': 'K_ATTRIBUTE',
    '构造': 'K_CONSTRUCTOR',
    '设': 'K_SET',
    '为': 'K_AS',
    '于': 'K_AT',
    '错误': 'K_ERROR_TYPE',
    '常量': 'K_CONST',
    '类型': 'K_TYPE',
    '导出': 'K_EXPORT',
    '导入': 'K_IMPORT',
    '从': 'K_FROM',
    # 循环控制
    '遍历': 'K_FOREACH',
    # 新语法别名：对 = 遍历
    '对': 'K_FOREACH',
    # 新语法别名：中的 = 于（遍历分隔符）
    '中的': 'K_AT',
    '当': 'K_WHILE',
    '跳出': 'K_BREAK',
    '跳过': 'K_CONTINUE',
    # 异常处理
    '尝试': 'K_TRY',
    '捕获': 'K_CATCH',
    '抛出': 'K_THROW',
    # 返回
    '返回': 'K_RETURN',
    # 数据操作
    '打印': 'K_PRINT',
    '输出': 'K_OUTPUT',
    '输入': 'K_INPUT',
    # 作用域
    '继承': 'K_INHERIT',
    '使用': 'K_WITH',
    '父': 'K_PARENT',
    '自我': 'K_SELF',
    '方法': 'K_METHOD',
    # 逻辑运算
    '且': 'K_AND',
    '与': 'K_AND',
    '或': 'K_OR',
    '非': 'K_NOT',
    # 算术运算
    '加': 'K_PLUS',
    '减': 'K_MINUS',
    '乘': 'K_MULTIPLY',
    '除': 'K_DIVIDE',
    '模': 'K_MOD',
    '幂': 'K_POW',
    # 复合赋值（Phase 5）
    '加上': 'K_PLUS_ASSIGN',
    '减去': 'K_MINUS_ASSIGN',
    '乘以': 'K_MULTIPLY_ASSIGN',
    '除以': 'K_DIVIDE_ASSIGN',
    '模以': 'K_MOD_ASSIGN',
    '幂以': 'K_POW_ASSIGN',
    # 连接符/属性
    '并': 'K_AND_WORD',
    '之': 'K_OF',
    '的': 'DOT',  # 「的」映射为点号，作为属性访问运算符
    # 特殊值
    '真': 'K_TRUE',
    '假': 'K_FALSE',
    '空': 'K_NULL',
    # 内置类型
    '数': 'T_NUMBER',
    '整数': 'T_INT',
    '浮数': 'T_FLOAT',
    '串': 'T_STRING',
    '列': 'T_LIST',
    '典': 'T_DICT',
    '集': 'T_SET',
    '布尔': 'T_BOOL',
    '任意': 'T_ANY',
    # 模式匹配
    '匹配': 'K_MATCH',
    '情况': 'K_CASE',
    # 上下文管理器
    '标注': 'K_DECORATE',
    # =========================================================================
    # v4.0 L0 核心字 单字别名（映射到现有token，保证零破坏）
    # =========================================================================
    # 控制流
    '否': 'K_ELSE',          # 否则
    '遍': 'K_FOREACH',       # 遍历
    '跳': 'K_BREAK',         # 跳出
    '过': 'K_CONTINUE',      # 跳过
    '返': 'K_RETURN',        # 返回
    # 定义与类型
    '承': 'K_INHERIT',       # 继承
    '接': 'K_INTERFACE',     # 接口
    '配': 'K_MATCH',         # 匹配
    # 异常（注：K_FINALLY token 在 ANTLR g4 中后续补齐，先用存在的兼容映射）
    '试': 'K_TRY',           # 尝试
    '捕': 'K_CATCH',         # 捕获
    '抛': 'K_THROW',         # 抛出
    '终': 'K_FINALLY',       # 最终 → 需在 LightLangLexer.g4 中补齐 K_FINALLY 规则
    # 自指与连接
    '自': 'K_SELF',          # 己/self（L0 推荐用字，旧 '己' 保留兼容）
    '是': 'K_EQUAL',         # 判断/相等（后续支持 isinstance 语义时再细分）
    # 组织
    '导': 'K_IMPORT',        # 导入
    '出': 'K_EXPORT',        # 导出
    # L4 外语引用（嵌入块，与 '嵌入' 等价。实际识别由 src/lexer.py 硬编码。）
    '引': 'K_EMBED',         # 引 Python:（占位 token，后续 g4 中补齐）
    '结束引': 'K_END_EMBED', # 对应 '结束嵌入'
    '嵌入': 'K_EMBED',
    '结束嵌入': 'K_END_EMBED',
    # 最终关键字（确保有 token 映射）
    '最终': 'K_FINALLY',
}

# 构建关键词集合（用于快速查找）
KEYWORD_SET = set(KEYWORDS)
KEYWORD_MAX_LEN = max(len(k) for k in KEYWORDS)

# 单字关键词集合（用于复合词冲突检测）
SINGLE_CHAR_KEYWORDS = {kw for kw in KEYWORDS if len(kw) == 1}

# 复合词安全关键词：这些单字关键词在复合词中很常见（如"列表"中的"列"），
# 后接CJK字符时应该跳过，允许收集为标识符
COMPOUND_SAFE_SINGLE_KEYWORDS = {
    '数', '列', '串', '典', '集',   # 类型
    '从',                             # 导入
    '段', '段落',                        # 段落（统一语法）
    '当',                             # 循环（常见复合词如 当前、当时）
    '空', '真', '假',                 # 特殊值（常见复合词如 空间、真实、假设）
    '父',                             # 作用域（常见复合词如 父类、父级）
    '的',                             # 助词（代码中请用空格分隔： 甲 的 属性）
    '加', '减', '乘', '除', '模', '幂',  # 算术运算符（常见复合词如 加法、减法、乘法）
    '若',                             # 条件（常见复合词如 若干、若非）
    '则',                             # 条件（常见复合词如 规则、法则）
    '对',                             # 遍历别名（常见复合词如 对象、对于、对比）
    # v4.0 L0 新增：常见复合词安全字
    '否',                             # 否则（常见：是否、否认、否则）
    '遍',                             # 遍历（常见：普遍、遍地）
    '过',                             # 跳过（常见：通过、过程、过去）
    '承',                             # 继承（常见：承担、承认、承接）
    '接',                             # 接口（常见：接受、接着、连接）
    '终',                             # 最终（常见：终结、始终、终点）
    '自',                             # self（常见：自己、自动、自然）
    '是',                             # 判断（常见：是否、就是、但是）
    '导',                             # 导入（常见：引导、导演、导航）
    '出',                             # 导出（常见：输出、出发、出色）
    '引',                             # 引用（常见：引用、引导、吸引）
    '试',                             # 尝试（常见：测试、试验、面试）
    '配',                             # 匹配（常见：配合、分配、配置）
}

# 复合词安全二字关键词：这些二字关键词在复合词中作为后缀很常见，
# 当标识符已收集字符时，应跳过允许继续收集
COMPOUND_SAFE_MULTI_KEYWORDS = {
    '整数', '浮数', '布尔', '任意',   # 类型名
    '函数',                           # 段别名（构造函数、成员函数等）
    '中的',                           # 遍历分隔符（常见于"其中的"、"心中的"等复合词中）
}

# 符号 Token 映射
SYMBOL_TOKEN_MAP = {
    '。': 'PERIOD', '.': 'DOT',
    '，': 'COMMA', ',': 'COMMA',
    '：': 'COLON', ':': 'COLON',
    '；': 'SEMICOLON', ';': 'SEMICOLON',
    '、': 'PAUSE',
    '（': 'LPAREN', '(': 'LPAREN',
    '）': 'RPAREN', ')': 'RPAREN',
    '【': 'LBRACKET', '[': 'LBRACKET',
    '】': 'RBRACKET', ']': 'RBRACKET',
    '{': 'LBRACE', '}': 'RBRACE',
    '＼': 'PATH_SEP', '/': 'PATH_SEP',
    '^': 'POW', '%': 'MODULO',
    '@': 'AT',
    '*': 'MULTIPLY', '×': 'MULTIPLY',
    '÷': 'DIVIDE',
    '+': 'PLUS',
    # '-' 作为连字符，需要特殊处理（-> 是 PIPE）
}

# 多字符符号
MULTI_CHAR_SYMBOLS = {
    '->': 'PIPE',
    '==': 'EQ',
    '!=': 'NE',
    '>=': 'GE',
    '<=': 'LE',
    '&&': 'AND',
    '||': 'OR',
}

# 单字符符号
SINGLE_CHAR_SYMBOLS = {
    '>': 'GT',
    '<': 'LT',
    '!': 'NOT',
    '-': 'MINUS',
    '=': 'EQ',  # 赋值/相等比较
}


# Unicode 范围
def is_cjk_char(ch: str) -> bool:
    """判断是否为中文字符"""
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF or
            0x3400 <= cp <= 0x4DBF or
            0xF900 <= cp <= 0xFAFF)


def is_letter(ch: str) -> bool:
    """判断是否为英文字母"""
    return 'a' <= ch <= 'z' or 'A' <= ch <= 'Z' or ch == '_'


def is_digit(ch: str) -> bool:
    """判断是否为数字"""
    return '0' <= ch <= '9'


def char_type(ch: str) -> str:
    """获取字符类型（用于类型切换分词）"""
    if is_cjk_char(ch):
        return 'CJK'
    elif is_letter(ch):
        return 'LETTER'
    elif is_digit(ch):
        return 'DIGIT'
    else:
        return 'SYMBOL'


# =============================================================================
# Token 数据类
# =============================================================================

class Token:
    """光明 Token"""

    def __init__(self, type_name: str, text: str, line: int, column: int):
        self.type_name = type_name
        self.text = text
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type_name}, '{self.text}', line={self.line}, col={self.column})"


# =============================================================================
# 中文分词器
# =============================================================================

class LightLangTokenizer:
    """光明中文分词器

    实现决策29的三层分词机制：
    第1层：类型切换自动分词
    第2层：双字关键词优先匹配
    第3层：元数驱动参数收集（可选，在 Visitor 中实现）
    """

    def __init__(self):
        self.errors = []

    def tokenize(self, source: str) -> List[Token]:
        """将光明源代码分词"""
        tokens = []
        line = 1
        col = 1
        i = 0
        source_len = len(source)

        def advance(n: int = 1):
            nonlocal i, line, col
            for _ in range(n):
                if i < source_len and source[i] == '\n':
                    line += 1
                    col = 1
                else:
                    col += 1
                i += 1

        def peek(n: int = 0) -> str:
            pos = i + n
            return source[pos] if pos < source_len else ''

        while i < source_len:
            ch = source[i]

            # ---------- 空白字符 ----------
            if ch in ' \t\r\n':
                advance()
                continue

            # ---------- 单行注释（#）----------
            if ch == '#':
                while i < source_len and source[i] != '\n':
                    advance()
                continue

            # ---------- 单行注释（//）----------
            if ch == '/' and i + 1 < source_len and source[i + 1] == '/':
                while i < source_len and source[i] != '\n':
                    advance()
                continue

            # ---------- 代码块注释 ```...``` ----------
            if ch == '`' and source[i:i+3] == '```':
                advance(3)  # 跳过开启的```
                # 跳过注释标签行（如 `注释` 或 `python`）
                while i < source_len and source[i] != '\n':
                    advance()
                if i < source_len:
                    advance()  # 跳过换行
                # 跳过注释内容直到关闭的```
                while i < source_len:
                    if source[i:i+3] == '```':
                        advance(3)
                        break
                    advance()
                continue

            # ---------- 多字符符号（如 ->, ==, != 等）----------
            for sym_len in [2, 3]:
                if i + sym_len <= source_len:
                    text = source[i:i+sym_len]
                    if text in MULTI_CHAR_SYMBOLS:
                        token_type = MULTI_CHAR_SYMBOLS[text]
                        tokens.append(Token(token_type, text, line, col))
                        advance(sym_len)
                        break
            else:
                # ---------- 单独下划线（模式匹配通配符）----------
                if ch == '_' and (i + 1 >= source_len or not (is_letter(source[i+1]) or is_digit(source[i+1]))):
                    tokens.append(Token('UNDERSCORE', '_', line, col))
                    advance()
                    continue
                
                # ---------- 单字符符号 ----------
                if ch in SINGLE_CHAR_SYMBOLS:
                    token_type = SINGLE_CHAR_SYMBOLS[ch]
                    tokens.append(Token(token_type, ch, line, col))
                    advance()
                    continue

                # ---------- 《》书名号（收集内部文本作为单个 ID）----------
                if ch == '《':
                    tokens.append(Token('BOOK_L', ch, line, col))
                    advance()  # 跳过《
                    id_text = ''
                    start_line, start_col = line, col
                    while i < source_len and source[i] != '》':
                        id_text += source[i]
                        advance()
                    if i < source_len and source[i] == '》':
                        tokens.append(Token('ID', id_text, start_line, start_col))
                        tokens.append(Token('BOOK_R', source[i], line, col))
                        advance()  # 跳过》
                    continue

                # ---------- 中英文标点 ----------
                if ch in SYMBOL_TOKEN_MAP:
                    if ch in SYMBOL_TOKEN_MAP:
                        token_type = SYMBOL_TOKEN_MAP[ch]
                        tokens.append(Token(token_type, ch, line, col))
                        advance()
                        continue

                # ---------- 字符串 ----------
                if ch in ('"', "'"):
                    quote = ch
                    start_line, start_col = line, col
                    advance()  # 跳过开引号
                    text = quote
                    while i < source_len and source[i] != quote:
                        if source[i] == '\\':
                            advance()
                            if i < source_len:
                                text += '\\' + source[i]
                                advance()
                        else:
                            text += source[i]
                            advance()
                    if i < source_len:
                        text += source[i]
                        advance()  # 跳过闭引号
                    else:
                        self.errors.append(f"行{start_line}: 字符串未闭合")
                    tokens.append(Token('STRING', text, start_line, start_col))
                    continue

                # ---------- 关键字/标识符（中文连续书写分词）----------
                if is_cjk_char(ch) or is_letter(ch):

                    # 尝试匹配最长关键词
                    if is_cjk_char(ch):
                        matched_keyword = None
                        for kw_len in range(KEYWORD_MAX_LEN, 0, -1):
                            if i + kw_len <= source_len:
                                text = source[i:i+kw_len]
                                if text in KEYWORD_SET:
                                    matched_keyword = text
                                    break

                        if matched_keyword:
                            # 复合词安全：部分单字关键词在后接CJK时跳过（避免"列表"被拆分为"列"+"表"）
                            if (len(matched_keyword) == 1
                                and matched_keyword in COMPOUND_SAFE_SINGLE_KEYWORDS
                                and i + 1 < source_len
                                and is_cjk_char(source[i+1])):
                                matched_keyword = None
                            else:
                                token_type = KEYWORD_TOKEN_MAP[matched_keyword]
                                tokens.append(Token(token_type, matched_keyword, line, col))
                                advance(len(matched_keyword))
                                continue

                    # 不是关键字，则收集连续字符作为标识符（支持CJK/字母/数字混合）
                    start_line, start_col = line, col
                    
                    # 先收集完整的汉字序列（直到非汉字字符）
                    cjk_run = ''
                    while i < source_len and is_cjk_char(source[i]):
                        cjk_run += source[i]
                        advance()
                    
                    if cjk_run:
                        # 在汉字序列中扫描嵌入式关键字（类似手写解析器的中文分词逻辑）
                        self._tokenize_cjk_with_embedded_keywords(cjk_run, start_line, start_col, tokens)
                        start_col = col  # update after CJK processing
                    
                    # 继续收集字母/数字序列
                    text = ''
                    has_alphanumeric = False
                    while i < source_len:
                        c = source[i]
                        if is_letter(c):
                            text += c
                            has_alphanumeric = True
                            advance()
                        elif is_digit(c):
                            text += c
                            has_alphanumeric = True
                            advance()
                        elif is_cjk_char(c):
                            # 遇到新的CJK字符，先输出当前文本，再处理CJK序列
                            break
                        else:
                            break
                    
                    if text:
                        # 纯数字序列输出为 NUMBER，否则输出为 ID
                        if text.isdigit():
                            tokens.append(Token('NUMBER', text, start_line, start_col))
                        else:
                            tokens.append(Token('ID', text, start_line, start_col))
                    
                    # 如果还有未处理的CJK字符，递归处理
                    if i < source_len and is_cjk_char(source[i]):
                        # 检查ASCII前缀后的CJK序列是否含有关键字
                        # 如果不含关键字，则应与前面的ASCII ID合并为一个标识符
                        # 例如 "__async_异步任务" 不应被拆分为两个token
                        cjk_rest = ''
                        lookahead = i
                        while lookahead < source_len and is_cjk_char(source[lookahead]):
                            cjk_rest += source[lookahead]
                            lookahead += 1
                        
                        if cjk_rest and text:
                            # 检查CJK部分是否含有关键字
                            has_keyword = False
                            for kw_len in range(KEYWORD_MAX_LEN, 0, -1):
                                for start_pos in range(len(cjk_rest) - kw_len + 1):
                                    if cjk_rest[start_pos:start_pos + kw_len] in KEYWORD_SET:
                                        has_keyword = True
                                        break
                                if has_keyword:
                                    break
                            
                            if not has_keyword:
                                # CJK部分不含关键字，合并为单一标识符
                                combined = text + cjk_rest
                                # 替换最后一个token
                                tokens[-1] = Token('ID', combined, start_line, start_col)
                                # 跳过CJK字符
                                for _ in range(len(cjk_rest)):
                                    advance()
                                continue
                        continue  # 回到主循环处理下一个CJK序列
                    continue

                # ---------- 数字 ----------
                if is_digit(ch):
                    start_line, start_col = line, col
                    text = ''
                    is_float = False
                    while i < source_len and is_digit(source[i]):
                        text += source[i]
                        advance()
                    if i < source_len and source[i] == '.':
                        # 检查是否是数字的一部分（后面还有数字）
                        if i + 1 < source_len and is_digit(source[i+1]):
                            is_float = True
                            text += '.'
                            advance()
                            while i < source_len and is_digit(source[i]):
                                text += source[i]
                                advance()
                    tokens.append(Token('NUMBER', text, start_line, start_col))
                    continue

                # ---------- 未知字符（错误捕获）----------
                self.errors.append(f"行{line}, 列{col}: 无法识别的字符 '{ch}'")
                advance()

        # 不再在这里添加 EOF，让 nextToken 方法处理
        return tokens

    def _tokenize_cjk_with_embedded_keywords(
        self, cjk_run: str, line: int, col: int, tokens: List[Token]
    ):
        """扫描汉字序列中的嵌入式关键字并分词

        类似手写解析器(src/lexer.py)的 _tokenize_chinese_sequence 方法逻辑：
        1. 从序列中按最长匹配查找关键字
        2. 将关键字前后的文本作为标识符输出
        3. 在序列起始位置处理复合词安全（避免拆分"列表"为"列"+"表"），
           但在序列中间位置不跳过关键字（确保"甲加乙"中的"加"被识别）

        Args:
            cjk_run: 纯汉字序列（不含非汉字字符）
            line: 起始行号
            col: 起始列号
            tokens: 输出 token 列表
        """
        pos = 0
        run_len = len(cjk_run)
        current_line = line
        current_col = col

        while pos < run_len:
            # ---------- 尝试匹配最长关键字 ----------
            matched_keyword = None
            for kw_len in range(KEYWORD_MAX_LEN, 0, -1):
                if pos + kw_len <= run_len:
                    text = cjk_run[pos:pos + kw_len]
                    if text in KEYWORD_SET:
                        matched_keyword = text
                        break

            if matched_keyword:
                # 复合词安全检查（仅限起始位置）：
                # 单字关键词在后接CJK字符时跳过，避免拆分复合词
                # 例如："列表"不应被拆分为"列"+"表"
                # 但对于"甲加乙"，中间的"加"仍然要识别为关键字
                if (pos == 0
                    and len(matched_keyword) == 1
                    and matched_keyword in COMPOUND_SAFE_SINGLE_KEYWORDS
                    and pos + 1 < run_len):
                    matched_keyword = None

            if matched_keyword:
                token_type = KEYWORD_TOKEN_MAP[matched_keyword]
                tokens.append(Token(token_type, matched_keyword, current_line, current_col))
                pos += len(matched_keyword)
                current_col += len(matched_keyword)
            else:
                # ---------- 无关键字匹配，收集连续字符作为标识符 ----------
                id_start = pos
                id_col = current_col
                while pos < run_len:
                    # 检查当前位置是否能匹配到关键字
                    found_kw = None
                    for kw_len in range(KEYWORD_MAX_LEN, 0, -1):
                        if pos + kw_len <= run_len:
                            text = cjk_run[pos:pos + kw_len]
                            if text in KEYWORD_SET:
                                found_kw = text
                                break

                    if found_kw:
                        # 复合词安全：单字类型关键词（数/列/串/典/集等）在复合词中出现时不拆分
                        # 例如"列表""整数""字符串""随机整数"中的"列""数""串"不应视为单独关键词
                        if (len(found_kw) == 1
                            and found_kw in COMPOUND_SAFE_SINGLE_KEYWORDS):
                            # 跳过这个单字，继续收集（避免拆分"列表""整数"等）
                            pos += 1
                            current_col += 1
                            continue
                        # 复合词安全：二字类型关键词（整数/浮数/布尔等）在复合词末尾不拆分
                        # 例如"随机整数""和数据"中的"整数""布尔"等
                        if (len(found_kw) > 1
                            and found_kw in COMPOUND_SAFE_MULTI_KEYWORDS
                            and pos > id_start):
                            # 跳过这个关键词，继续收集
                            pos += len(found_kw)
                            current_col += len(found_kw)
                            continue
                        # 遇到关键字，停止收集
                        break

                    pos += 1
                    current_col += 1

                if pos > id_start:
                    id_text = cjk_run[id_start:pos]
                    tokens.append(Token('ID', id_text, current_line, id_col))


# =============================================================================
# ANTLR 适配器：将光明 Token 转换为 ANTLR Token 流
# =============================================================================

class LightLangTokenSource(TokenSource):
    """将自定义 Token 转换为 ANTLR Token 流"""

    def __init__(self, tokens: List[Token], lexer):
        self.tokens = tokens
        self.lexer = lexer
        self.pos = 0
        self._token_type_map = self._build_token_type_map(lexer)
        self._factory = CommonTokenFactory.DEFAULT

    def _build_token_type_map(self, lexer) -> dict:
        """构建 Token 名称到 ANTLR Token 类型的映射（使用 symbolicNames）"""
        mapping = {}
        for i, name in enumerate(lexer.symbolicNames):
            if name and name != '<INVALID>':
                mapping[name] = i
        # 添加 EOF
        mapping['EOF'] = AntlrToken.EOF
        return mapping

    def nextToken(self):
        """获取下一个 Token"""
        if self.pos >= len(self.tokens):
            # 返回 EOF token
            ct = CommonToken(
                source=CommonToken.EMPTY_SOURCE,
                type=AntlrToken.EOF,
                channel=AntlrToken.DEFAULT_CHANNEL,
            )
            ct.line = 0
            ct.column = 0
            ct.text = ''
            return ct

        token = self.tokens[self.pos]
        self.pos += 1

        antlr_type = self._token_type_map.get(token.type_name, AntlrToken.INVALID_TYPE)

        ct = CommonToken(
            source=CommonToken.EMPTY_SOURCE,
            type=antlr_type,
            channel=AntlrToken.DEFAULT_CHANNEL,
            start=token.column - 1,
            stop=token.column - 1 + len(token.text) - 1,
        )
        ct.line = token.line
        ct.column = token.column - 1
        ct.text = token.text

        return ct

    def getSourceName(self):
        return "光明自定义分词器"


def create_antlr_token_stream(source: str, lexer) -> CommonTokenStream:
    """创建 ANTLR Token 流（使用自定义分词器）"""
    tokenizer = LightLangTokenizer()
    tokens = tokenizer.tokenize(source)
    token_source = LightLangTokenSource(tokens, lexer)
    return CommonTokenStream(token_source)