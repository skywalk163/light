"""
光明（Light）编程语言 - 词法分析器

实现决策29的三层分词机制：
1. 类型切换自动分词 - 甲加1 → [甲] [加] [1]
2. 双字关键词优先匹配 - 定义甲 → [定义] [甲]
3. 元数驱动参数收集 - 打印 甲 -（元数=1）→ [打印] [甲]

参考：newlisp/yan 的无空格分词实现
"""

import re
from dataclasses import dataclass
from typing import List, Set, Dict, Optional, Tuple
from enum import Enum

from tokens import Token, TokenType
from keywords import (
    ALL_KEYWORDS, KEYWORDS_DOUBLE, KEYWORDS_LOGIC, KEYWORDS_SPECIAL,
    VERB_ARITY, STDLIB_VERB_ARITY, ALL_VERB_ARITY, BUILTIN_TYPES, SYMBOL_MAP, BLOCKING_SYMBOLS
)

# 运算符动词集合（用于分词时识别运算符）
OPERATOR_VERBS = frozenset({
    '加', '减', '乘', '除', '加上', '减去', '乘以', '除以', 
    '大于', '小于', '等于', '不等于', '大于等于', '小于等于',
    '不小于', '不大于',
    '包含',  # 包含关系运算符
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
    '外部',  # 外部（如"外部命令"整体作标识符；FFI 外部 函数 带空格不受影响）
    '排序',  # 排序（如"排序完成"、"排序分数"应为复合标识符）
    '匹配',  '配',  # 匹配/配（如"配置"、"完全匹配"应为复合标识符）
    '包含',  # 包含（如"字典包含键"、"列表包含项"应为复合标识符）
    # v7 新单 B：模块 / 标准库 / 打印 也常作复合标识符的词中、词尾成分
    # （学生模块 / 可打印 / 我的标准库），词中词尾不应触发拆分。
    # 见下面 IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS：这三个只享受「词中/词尾」豁免，
    # 词首仍必须作关键字（打印 是 print，词首豁免会把 print 语句吞成标识符）。
    '模块', '标准库', '打印',
})

# IDENTIFIER_SAFE_KEYWORDS 的子集：**只在词中/词尾**享受不拆分豁免。
#
# 背景（v7 新单 B）：IDENTIFIER_SAFE_KEYWORDS 在 _tokenize_chinese_sequence 的
# 嵌入关键字扫描里有两处判据，口径并不一致——
#   * 输出循环：带 `scan_pos > 0` 门（词首仍作关键字）；
#   * 探测循环：无条件跳过（词首也被并入标识符）。
# 既有成员按后者落地：`输出甲` → IDENTIFIER('输出甲')、`输出格式` → IDENTIFIER
# （探测循环那行注释明确要这个行为，不能动）。
# 但 `打印` 是 print，且在 VERB_ARITY 中（keywords.py:253），词首遇到更长的汉字
# 序列时会被第一层的「多字动词作复合词前缀」判据跳过、落到探测循环。若沿用既有
# 成员的无条件跳过，`打印甲` / `打印结果` / `打印日志` 会从
# KEYWORD(打印)+IDENTIFIER 退化成单个 IDENTIFIER —— 无空格写法是本语言的一等
# 写法（见本文件顶部 docstring 第 3 条「元数驱动参数收集 - 打印 甲」），
# 那等于把 print 语句静默改写成一个自由标识符。
# 因此这三个新成员在探测循环里补 `scan_pos > 0` 门，与输出循环对齐。
IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS = frozenset({
    '模块', '标准库', '打印',
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
    # 数学函数名（含关键字"余"等，需保护不被拆分）
    '余弦', '余切', '反正弦', '反余弦', '反正切', '反正切2',
    '向下取整', '向上取整', '平方根', '最大公约数', '最小公倍数',
    '四舍五入', '随机整数', '随机浮点', '随机选择',
    # 医学领域复合词（含关键字"除"、"末"、"收"等）
    '清除率', '清除', '清除速率',
    '舒张末期容积', '舒张末期', '舒张',
    '收缩末期容积', '收缩末期', '收缩',
    '分布容积', '容积',
    '生物利用度', '利用度',
    '达峰时间', '峰时间',
    # 工程领域复合词（含关键字"模"、"承"等）
    '弹性模量', '弹性模',
    '承载力', '承载能力', '承载力',
    '桩基承载力', '桩基承载',
    '端承', '端承力',
    '侧摩', '侧摩阻力',
    '惯性矩', '惯性',
    '对流传热系数', '传热系数',
    '凝固点降低常数', '凝固点',
    '热对流', '对流',
    # 农业领域复合词
    '料肉比', '灌水定额', '计划层', '田间持水', '当前含水', '当前含',
    # 体育领域复合词
    '球员效率',
    # 医学领域新增复合词
    '新生儿体质量', '体质量', '生长Z评分', 'GOS',
    # 文本领域复合词
    '文本去重行', '去重行',
    '文本最长公共', '最长公共子串', '最长公共子序列',
    # 地理领域复合词
    '方位角',
    # 工具领域复合词
    '年龄分类',
    # 心理领域复合词
    '标准化分数',
    # 搜索领域复合词
    'Q学习搜索', '协同搜索', '差分进化搜索',
    # 教育领域复合词
    'Cronbachα', 'GlassΔ', 'KR20', '年级当量', '教育年龄', '等值分数',
    '方差和', '总方差',
    # 数学领域复合词
    '数学二分法',
    # 数据领域复合词（含百分号和数字）
    '减百分比', '减10百分比', '减20百分比', '减50百分比',
    '加百分比', '加10百分比', '加20百分比', '加50百分比',
    '各乘', '各乘数据', '各减', '各减数据', '各加', '各加数据', '各除', '各除数据',
    '平滑滤波', '平滑滤波3',
    'Z检测', '数据Z检测', '数据异常值', '数据相关系数', '数据聚合函数',
    # 数据滚动函数复合词
    '滚动均值', '滚动中位', '滚动乘积', '滚动加权', '滚动变化',
    '滚动差值', '滚动方差', '滚动最大', '滚动最小', '滚动标准差', '滚动求和', '滚动范围',
    # 数据过滤复合词
    '过滤模', '过滤模零', '过滤模非零', '过滤模二零', '过滤模二非零', '过滤模十零',
    # 格式领域复合词
    '保留位', '保留0位', '保留2位',
    '百分比格式', '货币格式', '十六进制',
    # 概率领域复合词
    '交叉熵', '伽马分布', '信息熵', '贝塔分布',
    # 法律领域复合词
    '土地增值税', '地方教育附加', '年终奖个税', '教育费附加',
    # 环境领域复合词
    'PM2.5等级', '水体富营养化',
    # 类型领域复合词
    '二转整数',
    # 系统领域复合词
    '负载1分', '负载5分', '负载15分',
    # 系统原语自举内置（D9 S2 / task-BI2）：含关键字子串（关闭/常量/枚举），
    # 保护不被切成 低级+关闭、常量+时间比较 等（见 外发任务_内置与直调S2.md §4）
    '低级打开', '低级读', '低级写', '低级关闭',
    '常量时间比较', '环境枚举',
    # 经济领域复合词
    'CVaR', 'VaR', '产出缺口', '四因子', '夏普率', '收益率', '斯特林率',
    '泰勒规则', '社会福利', '索提诺率',
    # 财务领域复合词
    'CAGR', '总资产增长', '财务VaR', '财务公司FCF', '财务利率互换',
    '财务套保比率', '财务安全库存', '财务更新决策', '财务股票分割', '财务配股价格',
    # 迭代领域复合词
    '三连组', '范围三元组', '范围四元组', '跳过迭代',
    # 随机领域复合词
    '随机Jack', '随机MCVaR', '随机矩阵正态',
    # 集合领域复合词
    '倍数', '过滤模零集合',
    # 验证领域复合词
    '数字验证', '非负验证',
    # 网络领域复合词
    '网络TCP连接', '网络ACL', '网络BGP', '网络流量控制', '状态码错误',
    # 数学/物理领域复合词（含科学计数法）
    '终点', '初值',
    '函数', '目标函数', '梯度函数', '损失函数', '激活函数', '核函数', '似然函数',
    '常数', '速率常数', '凝固点降低常数',
    '标准差', '均值',
    '总人数', '总次数', '总学分', '总绩点',
    'p_类型', 'p_均值', 'p_方差', 'p_标准差', 'p_输入', 'p_输出',
    'p_梯度', 'p_动量', 'p_衰减', 'p_学习率',
    # 工程领域复合词（含关键字"承"、"模"等）
    '极限承载能力', '承载能力', '桩基承载力', '弹性模量',
    'p_步长', 'p_维度', 'p_参数', 'p_权重',
    'p_温度', 'p_阈值', 'p_精度', 'p_比例',
    'p_分布', 'p_噪声', 'p_速度', 'p_扩散',
    'p_更新', 'p_投影', 'p_缩放', 'p_移位',
    'p_协方差', 'p_相关性', 'p_共轭方向', 'p_特征值',
    'p_量化步长', 'p_置信度', 'p_显著性', 'p_效应量',
    # === 新增复合词（修复NameError）===
    # 数据领域
    '协方差', '协', '方差',
    # 格式领域
    '格式模式',
    # 工程领域
    '压缩模量', '压缩模',
    # 经济/财务领域
    'std偏差', 'std',
    '终期折现因子', '折现因子和',
    '资产末期值', '期初资产',
    '期值', '期折现因子',
    # 迭代领域
    '循环迭代',
    # 文本领域
    '文本左填充', '文本Base64编码', '文本Base64解码',
    '文本URL编码', '文本URL解码', '文本前缀', '文本后缀',
    # 类型领域
    '是空', '分数文本转小数', '文本转小数', '整数转小数',
    '文本转模', '文本转ASCII', '文本转字节', '文本转码点',
    '码点转文本',
    # 计算机领域
    '位与', '位取反', '位异或', '位或', '右移', '左移',
    '位非',  # B5：位非(~)是一元位运算符，含 KEYWORD_LOGIC 成员 '非'，需复合词保护
    '位非输入', '输入右移', '输入左移',
    '甲位与乙', '甲位异或乙', '甲位或乙',
    # B5：推迟（defer）—— 复合词保护，`推`/`迟` 虽非单字关键字，
    # 但作为新增关键字登记以防未来切词变化。
    '推迟',
    # 集合领域
    '3倍数', '5倍数', 'p_mod值',
    # 数据过滤领域
    'p_cmp值',
    # 数学领域
    '数学二分法', 'p_分法',
    # 中文异常类型名
    '迭代停止', '停止迭代',
    '值错误', '类型错误', '索引错误', '键错误', '属性错误',
    '导入错误', '零除错误', '文件错误', '运行时错误',
    '溢出错误', '递归错误', '内存错误', '系统错误', '断言错误',
    '外部错误', 'FFI错误', '系统错误码',
    # 正则表达式函数名（含"匹配"关键字，需保护）
    '正则匹配', '编译正则表达式',
    # 异步 / 并发原语的复合名。
    #
    # 这张表只保证「这几个汉字不被切开」，**不提供任何实现**。第二轮总纲 §5 把
    # 「词法白名单式假实现」列为禁止形态——所以**新进表**必须同时有 codegen 映射。
    #
    # A2-3 删掉的死名字（原表 12 个里的 9 个）：`异步读取二进制`/`异步写入二进制`/
    # `异步HTTP获取`/`创建事件循环`/`事件循环运行`/`事件循环停止`/`事件循环创建任务`/
    # `异步任务等待`/`异步任务取消`。删除依据：全仓 37261 个 `.light` 里 0 处使用，
    # `src/code_generator.py` 与 `stdlib/builtins.py` 各 0 处定义；删除前后做过
    # 全仓 token A/B 扫描，token 流 0 处差异。
    #
    # `异步读取文件`/`异步写入文件`/`异步追加文件` **保留原状**（本轮不动）：
    # 它们同样没有实现（真实现只在 `stdlib/lightpub/异步运行时.py`，而那份实现第一行
    # 就是**裸的** `import aiofiles`，`except ImportError` 兜底是死代码），但
    # `异步` 是关键字——名字一旦从表里拿掉就会被切成 KEYWORD `异步` +
    # IDENTIFIER `读取文件`，`设 内容 为 等待 异步读取文件("a")。` 实测编成
    #     内容 = await 异步
    #     读取文件('a')          ← 结果被丢弃
    # 即把「运行期 NameError（吵）」换成「静默错编（哑）」，与本任务口径正好相反。
    # 所以留着比删掉安全。补零依赖实现要动 `stdlib/`（A2 明令不许碰），已记入
    # 移交清单，由 stdlib 归属方接。当前状态：写了会**报 NameError，不会静默错**。
    #
    # 下面五个是本轮真映射的（`src/code_generator.py` builtin_map → `asyncio.*`）：
    # `并发等待` 不进表会被切成 `并发` + KEYWORD `等待`（`等待` 就是 await），
    # `限时`/`创建任务`/`首个完成` 与它同一口径登记，避免随语料里的定义名漂移。
    '异步睡眠', '并发等待', '限时', '创建任务', '首个完成',
    '异步读取文件', '异步写入文件', '异步追加文件',


    # 文件路径/配置相关标识符
    '配置文件路径',
    # 通用复合标识符（防止被 pre-scan 前缀匹配误拆分）
    '环节序', '记录列表', '行列表', '环节列表', '环节数据',
    '当前环节数', '总环节数', '问题文本', '输入文本',
    '上边框', '生成分析阶段', '系统提示词', '下边框', '最终答案', '历史记录', '次序值', '新环节',
    '数字列表', '名称列表', '值列表', '键列表', '元素列表', '参数列表', '项目列表', '文件列表',
    '生成问候语', '生成分析',
    # 测试函数名（含ASCII下划线 + 含关键字的函数名）
    '测试_生成问候语', '测试_计算平均数',
    '当前环节', '环节1', '环节2', '环节3', '环节4', '环节数据',
})

# CJK 汉字范围
_HAN_START = 0x4E00
_HAN_END = 0x9FFF


def _is_han_fast(ch: str) -> bool:
    """判断是否为汉字（直接比较 codepoint，CJK 范围是连续的，无需缓存）"""
    cp = ord(ch)
    return _HAN_START <= cp <= _HAN_END


# 非 ASCII、非汉字的「字母类」字符缓存（希腊字母 π/α/θ、西里尔字母、假名等）
_EXTRA_LETTER_CACHE = {}


def _is_extra_letter(ch: str) -> bool:
    """判断是否为可用于标识符的其他 Unicode 字母。

    数学库里 `弧度π`、`角度θ` 这类命名很自然，但这些字符既不是 ASCII 字母
    也不在 CJK 区间，早期实现会直接抛「未知字符」，导致 stdlib/数学 里
    含 π 的导出名在段言侧完全不可用。这里放行 Unicode 字母类字符；
    标点、符号、emoji 仍然会被拒绝。
    """
    cp = ord(ch)
    if cp < 128 or _HAN_START <= cp <= _HAN_END:
        return False
    cached = _EXTRA_LETTER_CACHE.get(ch)
    if cached is None:
        cached = ch.isalpha()
        _EXTRA_LETTER_CACHE[ch] = cached
    return cached


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

# 关键字起始字符集合（用于快速跳过不匹配的位置）
_KEYWORD_START_CHARS: frozenset = frozenset()

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

# 构建关键字起始字符集合（用于快速跳过不匹配的位置）
_KEYWORD_START_CHARS = frozenset({kw[0] for kw in _ALL_KEYWORDS_WITH_VERBS if kw})

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
    # '之'  已移除 — 之 是成员访问符，应始终拆分，不应作为复合词安全字
    '并',   # 并且
    '且',   # 并且
    '或',   # 或者
    '非',   # 非常
    '出',   # 弹出/输出/退出
    '导',   # 导出/导入/引导（常见于"电导率"等复合词）
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
    # v7 单 F 补全 — 同族遗漏的复合安全单字（判据同上：既是关键字、又是高频构词字，
    # 且非语义分隔符）。前三个是 VERB_ARITY 单字动词，兄弟 长/列 早已在表；
    # `配` 是 KEYWORDS_MATCH，lexer.py:41 的 IDENTIFIER_SAFE_KEYWORDS 已声明
    # 「配置应为复合标识符」，但那只在嵌入扫描生效，词首漏了这一处。
    '首',   # 首字母/首项/首行 —— 兄弟 长/列 已在表；旧行为 去除首尾→去/首/首/尾（字面失真）
    '末',   # 月末/周末/期末 —— 遍历/日期库导出名 月末,周末 被切碎
    '余',   # 余额/剩余/冗余 —— 己余额、剩余时间 被切开
    '配',   # 配置/配对/配位 —— 词首 配置→配+置，与 IDENTIFIER_SAFE 已声明的意图对齐
    # `幂` 有意不加：`10的幂` 的错根在「的」递归吞掉分隔符（另一支缺陷），加 `幂`
    # 只把 幂+幂 改成 幂+ID(幂)，`的` 字面仍丢，不能真修；且 `幂` 是算术运算符
    # （OPERATOR_VERBS），进表风险大。留待「的 递归」单独处置。
    # v7 单 27 补全 —— `匹`/`例` 本单起成为关键字（KEYWORDS_MATCH），必须同时进本表：
    '匹',   # 匹配/匹配结果/匹配项 —— 全仓 89 处词首 `匹X`，不保护会被切成 匹+配
    '例',   # 例如/例1 —— 词首仅 3 处，仍一并保护（示例/比例/案例 里 `例` 不在词首，不受影响）
    # v7 单 31-A 补全 —— `断`/`跃` 本单起成为关键字（KEYWORDS_LOOP），必须同时进本表：
    '断',   # 断言*/判断*/中断/断裂韧性 —— 全仓 174 处词首、635 处词内，且此前**无任何
            #   关键字含 `断`**（零最长匹配保护）。最密集处是 stdlib/断言工具.light:238-243
            #   的 `导出 断言失败异常 断言 断言为真 …`（106 处），不保护会整族切成 断+言*。
    '跃',   # 跃迁能量/跳跃/阶跃函数/活跃线程数 —— 词首仅 4 处，仍一并保护
    # v7 单 31-B 补全 —— `现` 本单起成为关键字（KEYWORDS_CLASS），必须同时进本表：
    '现',   # 现在/出现/表现/实现/发现/体现 —— 高频构词字。注意 `实现`(len2) 由结构性
            #   最长匹配优先命中，不受影响；本表保护的是词首以 `现` 打头的复合词。
    # 同族的 `约` **不在本表**，但已在 31-F 落地——走的是范式 A：parser 判裸
    # IDENTIFIER（`parser_stmt.py:_is_interface_char_header`），词法层零改动。
    # 31-B 当年不加的理由（进表会踩本函数「回报内层结果」的返回值失配、把
    # `合约乘数` 编成 `合 * 乘数`）已由 **31-D 正面修掉**；31-F 之所以仍不进表，
    # 是因为 `约` 全仓代码侧词内 198 处，动最长匹配的风险大于收益。
    # **要找 `约` 的实现请看 parser_stmt.py，不要往这里加。**

    # v7 单 31-C 补全 —— `等` 本单起成为关键字（KEYWORDS_ASYNC = await），必须同时进本表：
    '等',   # 等级/等价/等额本息/等压过程/等容过程 —— 全仓词首 7680 处，其中 `等于`(7204)
            #   与 `等待`(41) 由 len-2 结构性最长匹配自保，其余复合词只能靠本表兜。
            #   已过全仓 token A/B（37255 文件）：0 漂移、0 吞字。

    # v7 单 31-G 补全 —— `异` 本单起成为关键字（KEYWORDS_ASYNC = async），必须同时进本表：
    '异',   # 异常/异或/位异或/变异系数/异常值检测 —— 全仓代码侧词内 595 处（272 文件）。
            #   `异步`(len-2) 由结构性最长匹配自保，其余复合词靠本表兜。
            #   已过全仓 token A/B（37255 文件）：REGRESS=0、SPLIT=2，两例都是
            #   bootstrap/release/stdlib 里 `def异常`/`def异常处理` 的已损坏生成产物。
            #   **不要顺手把 `异常` 也加进关键字表**：31-E 曾按 `等于` 护 `等` 的类比推演
            #   要加，31-G 实测证伪——加了 SPLIT 反从 2 涨到 7（`异常` 自己变成新切割点，
            #   撕开 `异常信息`/`断言失败异常`/`异常列表`/`异常值检测`）。详见工单 31-G。

    # v7 单 33 补全 —— `常` 本单起成为关键字（KEYWORDS_DEFINE = 常量修饰符），必须同时进本表：
    '常',   # 异常/常数/常表/自然常数/常量 —— 全仓代码侧词内 444 处（208 文件）。
            #   `常量`(len-2) 由结构性最长匹配自保，其余复合词靠本表兜。
            #   已过全仓 token A/B（37255 文件，探针 .scratch/ab_chang.py，收尾已删）：
            #   REGRESS=0、SPLIT=4，4 例全是 `异常` 被切开，均在
            #   bootstrap/release/stdlib 的已损坏生成产物里（`除异常`/`def异常*`），
            #   不在任何测试断言路径上。
    #   **同 31-G 的告诫：不要把 `异常` 加进关键字表**——那不是给 `常` 加保护，
    #   而是让 `异常` 自成切割点、把 SPLIT 放大。

    # 包⑤ L-038 补全 —— `到` 是 KEYWORDS_RESERVED 的范围表达式结束符（1到10），
    # 但常见于复合标识符：截取到末尾/添加到队列/追加到列表/插入到头部。
    # 不保护则 `截取到末尾` 被切为 截取+到+末尾，运行报 name '末尾' is not defined。
    # 范围表达式 `1到10` 不受影响：到 处于 NUMBER→KEYWORD→NUMBER 的类型边界，
    # 不在汉字序列内部，不走 _tokenize_chinese_sequence 路径。
    '到',
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


# ---------------------------------------------------------------------------
# L4 外语引用块的导出函数名提取（v7 单 20）
#
# 背景：`引 C:` / `引 Go:` 块里定义的函数，会在产物运行期被绑进模块 globals()，
# 因此在光明侧就是「用户显式声明的名字」。但这些名字若含内置动词（如 J1 的
# `快速求和` 尾部含 `求和`、J2 直接导出 `求和`），词法层的最长前缀匹配会把它
# 切碎（快速求和 -> IDENTIFIER 快速 + KEYWORD 求和），生成层的 builtin_map 还会
# 把它顶替成 sum / math.factorial，最终产物根本调不到外语函数。
#
# 这两条正则必须与 src/code_generator.py 里运行期实际绑定用的正则**逐字同源**：
#   C  : src/code_generator.py:3443
#   Go : src/code_generator.py:3494
# 若白名单登记的名字集合与 globals() 实际绑定的集合不相等，就会把「名字被拆碎」
# 换成「名字未绑定」，同样是 NameError，只是换了个位置。
_L4_C_DECL_RE = re.compile(r'(?:int|float|double|void|long|char\s*\*)\s+(\w+)\s*\(')
_L4_GO_EXPORT_RE = re.compile(r'//export\s+(\w+)')


def extract_embed_export_names(language: str, code: str) -> Set[str]:
    """从 L4 嵌入源码里提取「会被绑进光明命名空间的导出函数名」。

    只有 C 与 Go 两种语言在运行期往 globals() 写名字；MoonBit
    （src/code_generator.py:3510-3560）与 Python 沙箱分支都不写，
    因此这里对它们必须返回空集 —— 否则白名单有名、运行期无绑定，
    反而制造新的 NameError（J3_MoonBit_快速排序 就靠这条保持现状）。
    """
    tokens = (language or '').strip().split()
    lang = tokens[0].lower() if tokens else ''
    if lang == 'c':
        return set(_L4_C_DECL_RE.findall(code))
    if lang in ('go', 'golang'):
        return set(_L4_GO_EXPORT_RE.findall(code))
    return set()


# ── L-051：多行字典/列表字面量 —— 括号类型判定 ──────────────────
#
# `{` 在光明里是双义符号：既可以是字典/集合字面量（`设 映射 为 {`），
# 也可以是 C 风格语句块（`循环(...){...}` / `如果(...){...}` / `否则{...}` /
# 裸块 `{ stmts }`）。语句块的 body 由 `_parse_brace_body` 依赖花括号内部的
# NEWLINE/INDENT/DEDENT 定界，因此换行抑制**只能作用于字面量括号**，
# 绝不能作用于语句块花括号，否则 C 风格控制流全部解析失败。
#
# 判定：看 `{` 之前最近的实义 token——若它处于「必须接表达式」的位置
# （赋值 `为`、返回、`(`/`[`/`{` 之内、逗号、冒号、等号、运算符），
# 则 `{` 是字面量；否则（语句开头、`)` 之后、标识符/字面量之后）视为语句块。

# 「必须接表达式」的前置关键字（其后 `{` 判为字面量）
_LITERAL_BRACE_PREV_KEYWORDS = frozenset({
    '为', '返回', '等于', '之', '加', '减', '乘', '除',
    '加上', '减去', '乘以', '除以',
})

# 「必须接表达式」的前置标点 token（其后 `{` 判为字面量）
_LITERAL_BRACE_PREV_TYPES = frozenset({
    TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE,
    TokenType.COMMA, TokenType.COLON, TokenType.EQUALS,
})

# 值本身即字面量/名字、不可能引出字面量 `{` 的 token 类型
_LITERAL_BRACE_STOP_TYPES = frozenset({
    TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.STRING,
})

_BRACE_SKIP_TYPES = frozenset({
    TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT,
})


def _is_literal_lbrace(tokens) -> bool:
    """L-051：判断当前 `{` 是「字典/集合字面量」还是「C 风格语句块」。

    返回 True 表示字面量（其内换行应被抑制），False 表示语句块（保持原行为）。
    """
    prev = None
    for tok in reversed(tokens):
        if tok.type in _BRACE_SKIP_TYPES:
            continue
        prev = tok
        break
    if prev is None:
        return False
    if prev.type == TokenType.KEYWORD:
        return prev.value in _LITERAL_BRACE_PREV_KEYWORDS
    if prev.type in _LITERAL_BRACE_STOP_TYPES:
        return False
    return prev.type in _LITERAL_BRACE_PREV_TYPES


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

    def __init__(self, source: str = None, deterministic: bool = True):
        """初始化词法分析器

        支持两种调用方式：
        - Lexer(source).tokenize()
        - Lexer().tokenize(source)

        Args:
            source: 可选的源码字符串
            deterministic: P0-A 词法确定性切词开关。True 时标识符内部不拆分
                （仅词首做关键字判定），消除对逐词白名单（COMMON_COMPOUND_WORDS /
                IDENTIFIER_SAFE_KEYWORDS 中段扫描）的依赖。
                **默认 True**（P0-A 收口后成为正式行为）。全仓 A/B 实测：432 个
                .light、278971 个 token 零词法错误，仅 2 个文件 token 流变化，
                且两处都是修 bug（列表设置(...) 函数调用、类 伪终端会话: 类名，
                原被内部关键字劈开）。传 deterministic=False 可回到旧行为。
        """
        self._source = source
        self._deterministic = deterministic
        self.keywords_by_length = _KEYWORDS_BY_LENGTH
        self.max_keyword_len = _MAX_KEYWORD_LEN
        self.all_keywords_with_verbs = _ALL_KEYWORDS_WITH_VERBS
        self.all_keywords_by_length = _ALL_KEYWORDS_BY_LENGTH
        self.all_max_keyword_len = _ALL_MAX_KEYWORD_LEN
        self._symbol_token_map = _SYMBOL_TOKEN_MAP
    
    def tokenize(self, source: str = None, extra_definitions: set = None) -> List[Token]:
        """将源码转为 Token 流
        
        支持两种调用方式：
        - lexer.tokenize()  # 使用构造时传入的 source
        - lexer.tokenize(source)  # 使用传入的 source
        
        Args:
            source: 要分析的源码字符串（可选，默认使用构造时传入的）
            extra_definitions: 跨模块的用户定义标识符集合（如已注册模块的导出函数名）
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

        # 预扫描：收集用户定义的标识符（段落名 / 方法名 / 变量名等）
        user_definitions = self._scan_user_definitions(source)
        if extra_definitions:
            user_definitions = user_definitions | extra_definitions
        # 暴露给解析器：parser_expr 需要区分「含运算符动词的函数名」（如 添加任务，
        # 用户确实定义了该段落）与「紧凑二元表达式」（如 n乘阶乘 中 乘 是运算符，
        # n乘 并不是用户定义）。因此把预扫描结果通过 self.user_definitions 属性
        # 共享给 parser_expr 的 _parse_primary / _collect_primary_arg / _collect_single_arg，
        # 供它们在合并"动词函数名"前做合法性校验（见 parser_expr.py 对应注释）。
        self.user_definitions = user_definitions

        # 处理缩进
        indent_stack = [0]
        # L-051：括号深度计数。{ [ ( 及其闭包内的换行属于表达式内部空白，
        # 不应发射 NEWLINE/INDENT/DEDENT，否则多行字典/列表字面量会破坏后续块缩进。
        # 注意：仅「字面量括号」抑制换行；C 风格语句块花括号（`循环(...){...}` 等）
        # 的 body 由 NEWLINE/INDENT/DEDENT 定界，必须保持原样发射。
        # 每个未闭合括号一个元素：True = 语句块花括号（不抑制换行），False = 字面量括号（抑制）。
        # 判据取「最内层」——块花括号内嵌的字面量（`循环(...){ 设 x 为 [\n…\n] }`）
        # 仍应抑制，只有最内层是语句块花括号时才放行 NEWLINE/INDENT/DEDENT。
        bracket_stack = []

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
                # L-051：括号内换行属于表达式内部空白，不发射 NEWLINE/INDENT/DEDENT，
                # 否则多行字典/列表字面量会向 token 流注入 phantom 缩进，破坏后续块缩进。
                # 语句块花括号（block_brace_depth > 0）内不抑制——body 需要这些 token 定界。
                if bracket_stack and not bracket_stack[-1]:
                    line += 1
                    col = 1
                    i += 1
                    continue
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
                    # L-051：跟踪括号栈（True = 语句块花括号，False = 字面量括号）。
                    # 注意：`{` 的双义判定必须在把 `{` 自身追加进 tokens **之前**做——
                    # 否则辅助函数会把 `{` 自己当成「前一个实义 token」，而 LBRACE 属于
                    # 字面量前置集合，会导致所有 `{` 恒被判为字面量，C 风格语句块全崩。
                    is_block_brace = (token.type == TokenType.LBRACE
                                      and not _is_literal_lbrace(tokens))
                    tokens.append(token)
                    col += consumed
                    i += consumed
                    if token.type in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE):
                        bracket_stack.append(is_block_brace)
                    elif token.type in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
                        if bracket_stack:
                            bracket_stack.pop()
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
            
            # 处理原始字符串：r"..." / R"..."（v7 新单 C）
            #
            # 原来没有这条判据，`r` 在下面的 ASCII 标识符分派处被整体吞成
            # IDENTIFIER('r')，紧跟的字符串再独立成 STRING，于是
            #   设 甲 = r"\d{4}"   ->  甲 = r("\d{4}")
            # parse OK、compile 无 error，运行期才炸 NameError: name 'r' is
            # not defined。属静默错译（demo2_regex 4 处全中）。
            #
            # 判据与上面 f 前缀同源：字母**紧贴**引号才算前缀。
            #   r"x"  -> 前缀
            #   r "x" -> 标识符 r + 字符串（有空格，不受影响）
            #   设 r 为 1 / 打印 r -> r 不贴引号，不受影响
            # 全仓 37255 个 .light 扫过：非注释非嵌入块的「字母紧贴引号」现场
            # 里没有一处是「变量 r 恰好后跟字符串」，判据零误伤。
            #
            # raw=True 不能省：_tokenize_string 会翻译 \n \t \r \\ \x.. \0
            # （仅「未识别转义」如 \d 才原样保留）。只改调用形状而不施加 raw
            # 语义，等于把「调用错译」换成「转义错译」——
            # bootstrap/release/stdlib/正则表达式.light:174 的 r'\r?\n' 就会被改坏。
            #
            # 前缀集合本轮只做 r/R（产品裁定）：
            #   - docs/L2_文言体语法规范_v4.0.md:93-96 是唯一把字符串前缀写进
            #     规范的地方，且只列了 r
            #   - f 不动：裸串 "用户{姓名}" 已由 codegen 自动变成 f-string，
            #     中文侧插值不依赖前缀，另加 f 语义是冗余
            #   - b 另立单：bytes 要语义正确需 codegen 配合（bytes vs str），
            #     范围大于本单（contrib/HTTP客户端.light 的 b'' 归那张单）
            #   - u 不做：Python 3 里是空操作
            if (source[i] in 'rR' and i + 1 < n and source[i+1] in '"\''
                    and not (i > 0 and (source[i-1].isalnum() or source[i-1] == '_'))):
                token, consumed = self._tokenize_string(source, i + 1, line, col + 1, raw=True)
                tokens.append(token)
                consumed += 1  # 计入 r 前缀本身
                col += consumed
                i += consumed
                continue
            
            # 处理字节串：b"..." / B"..."（v7 新单 H，单 C 里明确挂账的那条）
            #
            # 判据与上面的 r / f 前缀同源：字母**紧贴**引号才算前缀。
            #   b''  -> 前缀            b "x" -> 标识符 b + 字符串（有空格）
            #   设 b 为 1 / 打印 b     -> b 不贴引号，不受影响
            # 不做的：`rb''`/`br''` 组合前缀。`rb'` 在 r 分支上 source[i+1]=='b'
            # 不匹配，会整体落到标识符路径 —— 全仓零处使用，本轮不扩判据。
            #
            # 为什么必须新开 BYTES token 而不是复用 STRING：
            # bytes 与 str 在 Python 里是不同类型，这个信息要一路带到 codegen。
            # r 前缀不需要新 token，因为「原样保留反斜杠」只是**值**的变换；
            # bytes 是**类型**的变换，值一模一样的 '' 和 b'' 产物必须不同。
            #
            # 修的是静默错译：原先 b'abc' 被切成 IDENTIFIER('b') + STRING('abc')，
            # 发出 b("abc")，编译无错、运行期 NameError: name 'b' is not defined。
            # 空的 b'' 更糟，在默认参数位置直接 ParseError。
            if (source[i] in 'bB' and i + 1 < n and source[i+1] in '"\''
                    and not (i > 0 and (source[i-1].isalnum() or source[i-1] == '_'))):
                token, consumed = self._tokenize_string(source, i + 1, line, col + 1)
                token.type = TokenType.BYTES
                tokens.append(token)
                consumed += 1  # 计入 b 前缀本身
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
                    # 嵌入块整块吞掉（含块体里的所有换行）。此前这里只推进 col/i、
                    # 从不推进 line，于是块之后所有 token 的行号都停在块起始行，
                    # 报错定位整体偏移「块体行数」（实测 all_in_one_L3_demo 偏 33 行、
                    # E4_L4_沙箱隔离验证 偏 27 行），任何报错都没法按行号回源码。
                    # 这里只修 token 的 line/col 元数据，不动 token 的类型、数量、顺序，
                    # 也不动 _tokenize_embed_block 的三条闭合路径（结束引 / 缩进回归 / EOF）。
                    swallowed = source[i:i + consumed]
                    newline_count = swallowed.count('\n')
                    if newline_count:
                        line += newline_count
                        # 块尾那一行的真实列：最后一个换行之后的字符数 + 1
                        col = consumed - swallowed.rfind('\n')
                    else:
                        col += consumed
                    i += consumed
                    continue

            # 处理中文数字（注释：不在此处处理，而是在标识符处理中判断）
            # 因为 "甲加三" 中的 "三" 需要根据上下文判断
            
            # 处理标识符和关键字（核心：无空格分词）
            ch_i = source[i]
            if _is_han_fast(ch_i) or _is_ascii_alpha(ch_i) or ch_i == '_' or _is_extra_letter(ch_i):
                new_tokens, consumed = self._tokenize_identifier_or_keyword(source, i, line, col, user_definitions)
                tokens.extend(new_tokens)
                col += consumed
                i += consumed
                continue
            
            # 未知字符
            # A2-7：`?` 单独给一条指路文案。决策是**不支持 `?` 可空后缀**（理由记在
            # 移交清单与 docs/ 语法文档：`?` 会与三元表达式、字典可选键等未来语法
            # 抢词法位，而 `可空 X` 已经走得通、且是中文前缀式，与 `列表 整数`
            # 这类既有写法同构）。既然不支持，报错就必须指向正确写法，而不是
            # 让人看着 `未知字符: '?' (0x003F)` 猜自己哪里写错了。
            if source[i] == '?':
                raise LexerError(
                    "光明不支持 `?` 可空后缀（`?` 不是词法原子）。"
                    "可空类型请写成中文前缀式：`设 甲: 可空 整数 为 无。`"
                    "（同义前缀 `可选`；这是既定口径，`?` 永不支持）",
                    line, col)
            raise LexerError(f"未知字符: '{source[i]}' (0x{ord(source[i]):04X})", line, col)
        
        # 文件结束，处理剩余的 DEDENT
        while len(indent_stack) > 1:
            indent_stack.pop()
            tokens.append(Token(TokenType.DEDENT, indent_stack[-1], line, col))
        
        tokens.append(Token(TokenType.EOF, None, line, col))
        
        # 包⑤ L-039：别名重映射 —— `退出循环` → `跳出`
        # parser 硬编码 ('跳出','跳','断')，无法在 parser 层加别名（硬边界禁改 parser）。
        # 在 lexer 返回前把 KEYWORD(退出循环) 的 value 替换为 '跳出'，使 parser 透明接收。
        _BREAK_ALIAS = {'退出循环': '跳出'}
        for _tok in tokens:
            if _tok.type == TokenType.KEYWORD and _tok.value in _BREAK_ALIAS:
                _tok.value = _BREAK_ALIAS[_tok.value]
        
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

        注意：compound_safe_single 中的单字关键字（如"自"、"过"）**是否**应该在
        当前位置成词，由调用方按上下文判定（词首/词中/词尾、后随字符等），
        判据集中在 _tokenize_chinese_sequence 的三处：第一层的「单字动词在词首
        且词长>1 时跳过」、嵌入扫描探测循环、嵌入扫描输出循环。
        本函数只负责「从 pos 起最长能匹配到哪个关键字」。


        Returns:
            (匹配到的关键字, 匹配长度) 或 (None, 0)
            匹配长度恒等于 len(匹配到的关键字)，且关键字恒等于 text[pos:pos+长度]。
        """
        return self._skip_compound_safe_and_match(text, pos)
    
    def _skip_compound_safe_and_match(self, text: str, pos: int, text_len: int = None) -> Tuple[Optional[str], int]:
        """从 pos 起做关键字匹配；遇到 compound-safe 单字关键字时尝试递归看后续。

        v7 新单 B 修复的是**返回值失配**，不是递归本身。原实现在命中
        _COMPOUND_SAFE_SINGLE_KEYWORDS 的单字（且后面还有内容）时递归到 pos+1，
        然后把**内层的 value 和内层的 length 原样返回**——既没折算偏移，也没退回
        外层候选：

            _match_keyword('自之姓名', 0) -> ('之', 1)   # 应为 ('自', 1)

        调用方消费 1 个字符（`自`）却记成 `之`，`自之姓名` 被切成
        KEYWORD(之) KEYWORD(之) IDENTIFIER(姓名)，self 语义静默丢失。

        为什么**不**直接删掉递归、退化成纯最长匹配：
          递归的返回值有一个被下游长期依赖的**副作用语义**——「一串 compound-safe
          单字后面若没有真正的关键字，就回报最内层那颗 compound-safe 单字（会被
          调用方 skip 掉）」。例如 `除空格` 里 `除`(compound-safe 运算符) 后跟
          `空`(compound-safe)，旧实现回报 ('空',1)，被 :2001/:2046 当作 compound-safe
          跳过，于是 `去除空格` 整体保留为一个标识符（stdlib 函数名）。若改成纯最长
          匹配，`除` 会作为运算符浮现、把 `去除空格` 切成 去+除+空格（实测 37255 文件
          A/B 比对抓到这类回归 100+ 处：10的幂/索引/种类/阶乘 …）。这些串大多是没进
          user_definitions 的自由名，切开即 NameError——正是本票严禁的静默错译。

        因此只做**最小对齐修复**，且只认成员访问符 `之`：
          * 递归找到的 kw 是 `之`（唯一被移出 compound-safe 表的分隔符，见 :388
            「之 是成员访问符，应始终拆分」）→ pos 处这颗 compound-safe 单字才是
            该成的词，返回与 pos 对齐的 (candidate, length)；
          * 其余一切情况（后续是别的普通关键字、或又是 compound-safe 单字、或没
            找到）→ 原样返回内层结果，历史行为一字不改。
        为什么不放宽成「任意非 compound-safe 关键字」：那会连 `对于`(对+于)、
        `10的幂`(…+幂)、`是否为空`(是+否+为) 这类既有切法一起改掉——实测全仓
        A/B 因此多出 100+ 处漂移、42 个文件受影响；收窄到 `之` 后只剩 16 处
        `KEYWORD(之)+KEYWORD(之) → KEYWORD(自)+KEYWORD(之)`，全部是本票要修的形状。
        判据即：`自之X` 修好；`去除空格`、`对于`、`是否`、`10的幂` 一个都不动。
        """

        # 局部变量缓存
        _kw_by_len = _ALL_KEYWORDS_BY_LENGTH
        _max_len = _ALL_MAX_KEYWORD_LEN
        _compound_safe = self.compound_safe_single_keywords
        _start_chars = _KEYWORD_START_CHARS
        
        # 缓存 text_len 避免重复计算
        if text_len is None:
            text_len = len(text)
        
        # 快速路径：如果当前字符不能起始任何关键字，直接返回
        if pos < text_len and text[pos] not in _start_chars:
            return None, 0
        
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
                        # 单字 compound_safe 关键字（如"自"、"除"），后面还有内容，
                        # 递归看紧跟的位置能否成词。
                        kw, l = self._skip_compound_safe_and_match(text, pos + 1, text_len)
                        if kw:
                            if kw == '之':
                                # 后续是成员访问符 `之`（唯一被移出 compound-safe 的
                                # 分隔符，见 :388「之 始终拆分」）：pos 处这颗
                                # compound-safe 单字才是最长匹配，返回与 pos 对齐的
                                # (candidate, length)。`自之X` 由此修成 KEYWORD(自)…。
                                #
                                # 只认 `之`、不认「任意非 compound-safe 关键字」：后者会
                                # 把 `对于`(对+于)、`10的幂`(…幂+幂) 之类 compound-safe
                                # 单字紧跟普通关键字的既有切法一并改掉——实测 A/B 多出
                                # 100+ 处 `对于/幂/是否` 漂移。历史上这些串靠「回报内层
                                # 关键字」被下游 skip/整体保留，必须原样保留。
                                return candidate, length
                            # v7 单 31-D：其余情况**不再回报内层结果**。
                            #
                            # 旧行为 `return kw, l` 是返回值失配的本体：kw 取自
                            # text[pos+k : pos+k+l]，l 也以 pos+k 为基准，而调用方
                            # （:2040/:2244/:2365 等六处）按 **pos** 消费 l 个字符、
                            # 同时把 kw 的字面 emit 出去——于是 pos 处那个字被丢掉、
                            # 内层关键字被吐两次（下列均为全仓 A/B 实测的真实形态）：
                            #     等于空那么 → 等于那么么   （`空`丢、`么`凭空出现）
                            #     种类等于   → 种等于于     （`类`丢、`于`吐两次）
                            #     10的幂     → 幂幂         （`的`丢、`幂`吐两次）
                            #     除类型错误 → 类型型错误   （`除`丢、`型`吐两次）
                            # 实测现行 src 上这类契约违约有 6874 处 / 2192 文件（**函数
                            # 契约层**违约数，多数被调用方的 compound-safe 跳过救回，
                            # 真正写坏 token 流的是其中 31 文件，见单 31-D 工单）。
                            #
                            # 单 B 曾试过 `return candidate, length`（即断言 pos 处
                            # 这颗 compound-safe 单字就是词），那会让 `除`/`幂`/`于`
                            # 作为运算符浮现，把 `去除空格`/`对于`/`10的幂` 切碎——
                            # 全仓 A/B 实测 100+ 处漂移、42 文件，故当年收窄到只认 `之`。
                            #
                            # 本单取第三种语义：**pos 处不做关键字承诺**。
                            # 语义上这正是 compound-safe 这套启发式本来要表达的
                            # 「这颗单字后面还接着关键字料，别让它在这里成词」；
                            # 契约（:1023「关键字恒等于 text[pos:pos+长度]」）由
                            # kw is None 平凡满足。下游行为不变的原因是：调用方拿到
                            # None 后把 pos 处的字当标识符料继续扫，扫到内层那个位置
                            # 时会**在正确的 pos 上**重新问一次，得到诚实的结果，再由
                            # 既有的 compound-safe 跳过逻辑决定整词保留还是切开。
                            return None, 0
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
    
    def _tokenize_string(self, source: str, i: int, line: int, col: int,
                         raw: bool = False) -> Tuple[Token, int]:
        """处理字符串

        raw=True 时施加原始字符串语义：不翻译任何转义序列，反斜杠逐字保留。
        由 v7 新单 C 的 `r"…"` 前缀路径传入，见 tokenize() 主循环里的前缀特判。
        """

        start_col = col
        quote_char = source[i]

        # 三引号字符串（docstring）："""...""" 或 '''...'''
        # Bug 根因：原实现只按成对引号处理，"""...""" 会被拆成三个 STRING token
        # （"" + "内容" + ""），作为独立语句时首 token 为空字符串，解析器报
        # "无法识别的语法元素：''"（bootstrap_eval/lexer.duan 的 docstring 失败）。
        # 修复方案：检测连续三个相同引号，把整个三引号块作为单个 STRING token 消费，
        # 内容为三引号之间的原文（支持跨行），供裸字符串语句（docstring）解析使用。
        if i + 2 < len(source) and source[i] == source[i + 1] == source[i + 2]:
            triple = quote_char * 3
            close_idx = source.find(triple, i + 3)
            if close_idx == -1:
                raise LexerError(
                    f"字符串未闭合: 三引号 '{triple}' 缺少匹配的结束符", line, start_col)
            value = source[i + 3:close_idx]
            return Token(TokenType.STRING, value, line, start_col), close_idx + 3 - i

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
                if raw and source[j] == '\\' and j + 1 < len(source):
                    # 原始字符串：反斜杠不翻译，但仍参与「下一个字符不作为闭合引号」
                    # 的扫描（与 Python 一致：r"a\"b" 的值是 a\"b，字符串不在中间截断）。
                    chars.append(source[j])
                    chars.append(source[j + 1])
                    j += 2
                    continue
                if not raw and source[j] == '\\' and j + 1 < len(source):
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
                    elif next_ch == 'u' and j + 5 < len(source):
                        # L-033: 识别 \uXXXX 转义并解码为 Unicode 码点
                        hex_str = source[j+2:j+6]
                        try:
                            code_point = int(hex_str, 16)
                            chars.append(chr(code_point))
                            j += 6
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
        
        # 计算「开启行」的缩进宽度（v7 单 15）
        #
        # 本方法是字符级扫描器，不经过 token 流，拿不到 INDENT/DEDENT。要支持
        # 「缩进回归自动闭合」就必须自己算出 引/嵌入 所在行的缩进。
        # 不能用入参 col - 1 代替：主循环换行段（:540-546）对 \t 做 indent += 4
        # 而 col 只 += 1，制表符缩进会失真。这里按与 :540-546 完全相同的口径重算。
        _line_head = i
        while _line_head > 0 and source[_line_head - 1] != '\n':
            _line_head -= 1
        open_indent = 0
        for _c in source[_line_head:i]:
            if _c == '\t':
                open_indent += 4
            elif _c == ' ':
                open_indent += 1
            else:
                # 开启行在 引/嵌入 之前还有非空白内容（如行内块），缩进无意义
                open_indent = -1
                break

        # 收集嵌入代码，直到遇到 "结束嵌入" 或 "结束引"（两种都可，容错），
        # 或者发生缩进回归（v7 单 15）
        code_lines = []
        end_markers = ('结束嵌入', '结束引')
        body_indent = None
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

            # 缩进回归闭合（v7 单 15）
            #
            # 口径依据：docs/分层语法设计_v4.0.md:748 明列「缩进回归」为合法闭合方式；
            # docs/知识库/语言规范.md:170-173 的官方 L4 示例本身就省略 结束引 ——
            #     引 Python:
            #         def hello():
            #             return "Hello from Python"
            #     出 hello          ← 回到开启行缩进，块在此闭合
            # 因此「块体缩进 > 开启行缩进」时，首个缩进 ≤ 开启行的非空行即闭合点。
            #
            # 只对「缩进式块体」生效（body_indent > open_indent）。零缩进块体
            # （块体与 引 同列）在词法层无法与普通 light 语句区分，不做启发式，
            # 仍走下面的未闭合报错。
            _blank = k >= n or source[k] == '\n'
            if not _blank and open_indent >= 0:
                _cur_indent = 0
                for _c in source[line_start:k]:
                    _cur_indent += 4 if _c == '\t' else 1
                if body_indent is None:
                    body_indent = _cur_indent
                elif body_indent > open_indent and _cur_indent <= open_indent:
                    # 缩进回归：在本行之前闭合，本行不消耗，交回主循环当普通 light 语句
                    code = '\n'.join(code_lines)
                    return Token(TokenType.EMBED_BLOCK, (language, code), line, start_col), line_start - i

            # 收集这一行
            line_end = j
            while line_end < n and source[line_end] != '\n':
                line_end += 1
            code_lines.append(source[line_start:line_end] if line_end < n else source[line_start:])
            j = line_end + 1 if line_end < n else n

        # 到达 EOF：缩进式块体按缩进回归的极限情形正常闭合
        # （文件以缩进块体结尾、没写 结束引，仍是合法的「缩进回归」）
        if body_indent is not None and open_indent >= 0 and body_indent > open_indent:
            code = '\n'.join(code_lines)
            return Token(TokenType.EMBED_BLOCK, (language, code), line, start_col), n - i

        # 零缩进块体且无显式结束标记 —— 无法无歧义闭合，保持报错
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
        
        # 科学计数法：e/E 后跟可选 +/- 及数字
        # 如 6.67e-11, 3e8, 1.05e-34, 5.67e-8
        if j < n and (source[j] == 'e' or source[j] == 'E'):
            e_pos = j
            j += 1
            # 可选正负号
            if j < n and (source[j] == '+' or source[j] == '-'):
                j += 1
            # 指数部分数字
            while j < n and _is_digit(source[j]):
                j += 1
            # 如果 e 后面没有数字，回退到 e 之前（不当作科学计数法）
            if j == e_pos + 1 or (j == e_pos + 2 and (source[e_pos+1] == '+' or source[e_pos+1] == '-')):
                # e 后面没有数字，回退
                j = e_pos
        
        num_str = source[start:j]
        # 科学计数法或无小数点浮点数（如 1e6, 3e8）也需用 float()
        if '.' in num_str or 'e' in num_str.lower():
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

        # 白名单优先（仅限「汉字 + 数字/英文」混排的名字）
        #
        # 预扫描已把 导出/导入 列表、函数名等收进 user_definitions，但纯汉字路径
        # 只在 _tokenize_chinese_sequence 里查白名单，遇到 `随机0到1` 这种带数字的
        # 名字会先切出 `随机0`，再把 `到` 当成关键字，名字被拦腰截断。
        # 这里只处理「含混排后缀」的情形，纯汉字标识符的既有行为完全不变。
        if user_definitions:
            mixed = self._match_mixed_user_definition(source, i, user_definitions)
            if mixed:
                tokens.append(_Token(_TokenType.IDENTIFIER, mixed, line, col))
                return tokens, len(mixed)

        # 成员访问上下文：紧跟 '.' 之后的连续标识符作为单一标识符
        # L-004/L-010/L-011/L-012：'.' 之后按语言规范只可能是属性/方法名，
        # 不可能是语句关键字，因此不再按关键字边界拆分。
        # （如 对象.导出事件表 不再拆成 对象.导出+事件表）
        # 注意：不能只收「连续汉字」——汉字+ASCII 混合的成员名（如 导出JSON、
        # 导出HTML、段言到Python）会被切成 导出+JSON 两个标识符，编译产物变成
        # l3_chart.导出(JSON()) 语义错误。须按标识符字符集（汉字/ASCII 字母数字/
        # 下划线/Unicode 字母，与 :1824 混排规则一致）整段收集。
        if _is_han(source[i]) and i > 0 and source[i - 1] == '.':
            j = i
            while j < n and (_is_han(source[j]) or _is_ascii_alnum_f(source[j])
                             or source[j] == '_' or _is_extra_letter(source[j])):
                j += 1
            _member_name = source[i:j]
            if _member_name:
                tokens.append(_Token(_TokenType.IDENTIFIER, _member_name, line, col))
                return tokens, j - i

        # 收集连续的汉字（或英文标识符）
        if _is_han(source[i]):
            # 汉字处理：实现三层分词
            if self._deterministic:
                consumed = self._tokenize_chinese_sequence_det(source, i, line, col, tokens, user_definitions)
            else:
                consumed = self._tokenize_chinese_sequence(source, i, line, col, tokens, user_definitions)

            # 处理汉字后紧跟ASCII字母/数字的情况（如"计算器1"）
            next_pos = i + consumed
            if next_pos < n:
                next_ch = source[next_pos]
                cp_next = ord(next_ch)
                if (cp_next < 128 and (_is_ascii_alnum_f(next_ch) or next_ch == '_')) \
                        or _is_extra_letter(next_ch):
                    j = next_pos
                    while j < n:
                        ch = source[j]
                        cp = ord(ch)
                        if (cp < 128 and (_is_ascii_alnum_f(ch) or ch == '_')) \
                                or _is_extra_letter(ch):
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
                            # 关键字后紧跟ASCII字母时的合并——**必须凭已知名字放行**（v7 单 02）
                            #
                            # 缺陷史：本分支原先只判 `suffix[0].isalpha() or == '_'` 就无条件合并，
                            # 并把 token 类型从 KEYWORD 降级成 IDENTIFIER。_tokenize_chinese_sequence
                            # 已经按最长前缀匹配正确切出了 KEYWORD 设/如果/打印/遍历/自，这里又粘回去，
                            # 于是 `设x为10` → IDENTIFIER '设x'、`打印x` → '打印x'、`left自right` →
                            # 'left' + '自right'，把 Level 6「语句内无空格」整个特性推翻了一半。
                            #
                            # 规范依据（light 自己的规格，非 duan）：
                            #   docs/superpowers/specs/2026-07-01-level6-type-annotation-design.md:16
                            #     「无空格分词：语句内关键字与标识符紧密相连，词法分析通过最长前缀匹配自动拆分」
                            #   同文件 :31-38  2.1 节给出最长前缀匹配四步算法
                            #   同文件 :41-48  2.2 节把 设/为/段/类/己 等约 45 个关键字列为支持无空格分词
                            #   同文件 :332    「有空格的写法（设 x 为 10）和无空格的写法（设x为10）都支持」
                            # 断言依据：tests/test_level6_lexer.py:41-53 / :56-67 / :95-109
                            #
                            # 放行条件（三档，缺一不可）：
                            # 1) 成员名上下文：紧邻的前一个源字符是 `.`。`.` 之后按定义是属性/方法名，
                            #    不可能是语句关键字。若不放行会打穿
                            #    examples/L3_domain/demo4_echarts.light:64 `l3_chart.导出JSON()`、
                            #    :69 `l3_chart.导出HTML(...)`、examples/chat_bot/主.light:42 `.段言到Python(...)`
                            #    注意这里必须看源码字符而不是 tokens[-2]——本方法的 `tokens`
                            #    是 :1262 新建的局部列表，看不到外层已发射的 DOT。
                            # 2) 合并结果（含紧随的汉字后缀）是内置复合动词名：如 读取N字节
                            #    （src/keywords.py:283 在 ALL_VERB_ARITY 中）
                            # 3) 合并结果在 user_definitions 里：即 :500-508 预扫描认定的用户自定义名
                            #    （如 lsp/lsp_protocol.light:22 `段落 读取LSP消息()`）
                            # 其余情况一律不合并，KEYWORD 保持独立，ASCII 后缀交回主循环单独分词。
                            #
                            # 注意：IDENTIFIER 分支（上面 1306-1308）**不受本次收窄影响**——
                            # tests/test_level6_lexer.py:70-92 明确期望 `循环i从1到10` 里 `循环i`
                            # 是单个 IDENTIFIER（`循环` 不是关键字，走的就是 IDENTIFIER 分支）。
                            if suffix[0].isalpha() or suffix[0] == '_':
                                _han_end = j
                                while _han_end < n and _is_han(source[_han_end]):
                                    _han_end += 1
                                _cand_ascii = last.value + suffix
                                _cand_full = _cand_ascii + source[j:_han_end]
                                _after_dot = i > 0 and source[i - 1] == '.'
                                if (_after_dot
                                        or _cand_full in ALL_VERB_ARITY or _cand_ascii in ALL_VERB_ARITY
                                        or _cand_full in user_definitions or _cand_ascii in user_definitions):
                                    tokens[-1] = _Token(_TokenType.IDENTIFIER, last.value + suffix, last.line, last.col)
                                    consumed += len(suffix)

                        # 继续收集ASCII后缀后的汉字（如"阶段1标题" → 完整标识符）
                        # 注意：只有当后继汉字不是关键字时才合并，避免误合并"循环i从1"
                        after_ascii = i + consumed
                        while after_ascii < n and _is_han(source[after_ascii]):
                            # 先收集完整的汉字后缀
                            k = after_ascii
                            while k < n and _is_han(source[k]):
                                k += 1
                            han_suffix = source[after_ascii:k]
                            
                            # 检查整个标识符是否在常见复合词中（如"测试_生成问候语"）
                            full_combined = tokens[-1].value + han_suffix
                            if full_combined in COMMON_COMPOUND_WORDS:
                                tokens[-1] = _Token(_TokenType.IDENTIFIER, full_combined, tokens[-1].line, tokens[-1].col)
                                consumed += len(han_suffix)
                                after_ascii = i + consumed
                                continue
                            
                            # 检查后继汉字是否是关键字（包括动词运算符和语句关键字）
                            han_kw, kw_len = self._match_keyword(source, after_ascii)
                            if han_kw and han_kw in _ALL_KEYWORDS_WITH_VERBS:
                                break  # 是关键字，不合并，交给后续分词处理
                            # 收集连续的汉字作为标识符后缀
                            tokens[-1] = _Token(_TokenType.IDENTIFIER, tokens[-1].value + han_suffix, tokens[-1].line, tokens[-1].col)
                            consumed += len(han_suffix)
                            after_ascii = i + consumed

                    elif tokens and tokens[-1].type == TokenType.KEYWORD:
                        # 检查关键字+ASCII后缀+后续汉字是否构成复合关键字或用户定义标识符
                        # 例如"读取N字节"中"读取"是关键字、后面是ASCII"N"和汉字"字节"，
                        # 但"读取N字节"整体在 ALL_VERB_ARITY 中，应作为单个关键字输出。
                        # 又如"读取LSP消息"是用户定义的函数名，应作为单个标识符输出。
                        after_ascii = j
                        while after_ascii < n and _is_han(source[after_ascii]):
                            after_ascii += 1
                        han_suffix = source[j:after_ascii]
                        combined = tokens[-1].value + suffix + han_suffix
                        if combined in ALL_VERB_ARITY:
                            tokens[-1] = _Token(_TokenType.KEYWORD, combined, tokens[-1].line, tokens[-1].col)
                            consumed += len(suffix) + len(han_suffix)
                        elif user_definitions and combined in user_definitions:
                            tokens[-1] = _Token(_TokenType.IDENTIFIER, combined, tokens[-1].line, tokens[-1].col)
                            consumed += len(suffix) + len(han_suffix)

            return tokens, consumed
        else:
            # 英文标识符：收集连续的字母、数字、下划线（含 π/α 等 Unicode 字母）
            j = i + 1
            while j < n and (_is_ascii_alnum_f(source[j]) or source[j] == '_'
                             or _is_extra_letter(source[j])):
                j += 1

            # 检查是否紧跟汉字（如 evennum集），如果是则合并
            # 但只合并非关键字的汉字，避免破坏 left至right 这类范围表达式
            # 同时检查汉字序列中是否包含成员访问符（之、的），遇到则停止合并
            #
            # Bug 根因：原实现只判断汉字序列开头是否命中 ALL_KEYWORDS，但运算符动词
            # （减/乘/除/至/等于 等）存放在 VERB_ARITY 而【不在】ALL_KEYWORDS，导致
            # "n减1" 中 "减" 未被识别为关键字，汉字序列被整体并入标识符，
            # "n减1" 被切成单个标识符 "n减"，运行时产生 NameError。
            #
            # 修复方案：从汉字起点 j 处用 _match_keyword 做最长关键字匹配（该函数同时
            # 覆盖 VERB_ARITY 中的运算符动词，是 ALL_KEYWORDS 的超集），一旦命中关键字
            # 立即停止合并，从而把 "n减1" 正确切分为 标识符 n + 关键字 减 + 数字 1；
            # 未命中关键字的纯后缀汉字（如 evennum 后的 集）仍按原逻辑合并。
            member_access_kw = {'之', '的'}

            # snake_case 名字中的汉字段：`_` 后紧跟汉字时，这颗汉字必然是名字的一部分，
            # 不可能是运算符或语句关键字 —— 光明不会写 `foo_减1` 来表示减法。
            # L3 领域层生成的函数名正是这个形状（把块标签拼进名字）：
            #   l3_math_solve_例1_2 / l3_math_int_例1_x_8 / l3_sql_成绩_q2
            # （examples/E阶段_L3L4原生语法/E3_L3_公式数学原生.light:33,46 等）。
            # 若照下面的通用规则在关键字处断开，名字会碎成
            #   IDENTIFIER(l3_math_solve_) KEYWORD(例) NUMBER(1) IDENTIFIER(_2)
            # 编译期报「例 是保留关键字，不能直接作为语句开头」。
            # 因此此处整段吞掉「汉字/字母/数字/下划线」混排，直到真正的分隔符。
            # `n减1`、`left至right` 的汉字前面不是 `_`，走原路，一字不改。
            if j < n and _is_han(source[j]) and source[j - 1] == '_':
                while j < n and (_is_han(source[j]) or _is_ascii_alnum_f(source[j])
                                 or source[j] == '_' or _is_extra_letter(source[j])):
                    if source[j] in member_access_kw:
                        break
                    j += 1
                tokens.append(_Token(_TokenType.IDENTIFIER, source[i:j], line, col))
                return tokens, j - i

            while j < n and _is_han(source[j]):
                # 从 j 处做最长关键字匹配（_match_keyword 覆盖 VERB_ARITY 中的动词）
                han_kw, _ = self._match_keyword(source, j)
                if han_kw:
                    break
                k = j
                while k < n and _is_han(source[k]):
                    if source[k] in member_access_kw:
                        break
                    k += 1
                if k < n and source[k] in member_access_kw:
                    # 遇到成员访问符，将汉字合并到成员访问符前，后续由中文序列分词处理
                    j = k
                    break
                j = k

            # 收集尾随的下划线（如 __迭代__ 末尾的 _）
            while j < n and source[j] == '_':
                j += 1

            word = source[i:j]
            if word in ALL_KEYWORDS:
                tokens.append(_Token(_TokenType.KEYWORD, word, line, col))
            else:
                tokens.append(_Token(_TokenType.IDENTIFIER, word, line, col))

            return tokens, j - i
    
    def _match_mixed_user_definition(self, source: str, i: int, user_definitions: Set[str]):
        """在位置 i 处对「含数字/英文的用户定义名」做最长匹配。

        只有当名字在纯汉字前缀之后还有 ASCII/其他字母后缀时才生效，
        避免干扰既有的纯汉字分词逻辑（那条路径自己会查白名单）。

        例：`导出 随机0到1。` 预扫描已把 `随机0到1` 加入白名单，
        这里整体返回，防止被切成 `随机0` + 关键字`到` + `1`。
        """
        n = len(source)
        han_end = i
        while han_end < n and _is_han_fast(source[han_end]):
            han_end += 1

        j = han_end
        while j < n:
            ch = source[j]
            if _is_ascii_alnum(ch) or ch == '_' or _is_han_fast(ch) or _is_extra_letter(ch):
                j += 1
            else:
                break

        if j <= han_end:
            return None  # 没有混排后缀，交给原有逻辑

        while j > han_end:
            candidate = source[i:j]
            if candidate in user_definitions and candidate not in ALL_KEYWORDS:
                # 不能在标识符「中间」停下：若 candidate 之后仍是合法的标识符续接字符
                # （ASCII 字母/数字/下划线/其他 Unicode 字母/汉字），说明这只是一个更长名字
                # 的前缀，应当继续缩短，否则会把 `ai_api_helper`（白名单里只有被误拆的 `ai`）
                # 错切成 `ai` + `_api_helper`，运行期报 No module named 'ai'。
                after = source[j] if j < n else ''
                if after and (after == '_' or _is_ascii_alnum(after)
                              or _is_han_fast(after) or _is_extra_letter(after)):
                    j -= 1
                    continue
                return candidate
            j -= 1
        return None

    def _await_in_name(self, full_identifier: str, source: str, abs_pos: int) -> bool:
        """L-056：判断 full_identifier 是否因内嵌 await 关键字（等待 / 等）而必须整体成标识符。

        光明语言的 await 规范写法恒带空格（等待 目标() / 等 目标()）。若 等待 / 等
        出现在汉字序列内部、且其「后一个字符」是标识符续接字符（汉字 / ASCII 字母数字
        / 下划线，即无空格紧邻），说明它是某个标识符的一部分（等待器 / 团队错等待中止 /
        等他 …），不能当关键字切出，整串应作为单个标识符。
        反例：带空格的 await（等待 目标）会被空格切成独立汉字段，full_identifier 仅为
        「等待」、其后为空格 → 不触发本规则，仍是 KEYWORD（await）。
        """
        n = len(source)
        j = 0
        while j < len(full_identifier):
            kw, klen = self._match_keyword(source, abs_pos + j)
            if kw in ('等待', '等'):
                after_idx = abs_pos + j + klen
                after = source[after_idx] if after_idx < n else ''
                if after and (_is_han_fast(after) or after == '_' or _is_ascii_alnum(after)):
                    return True
            j += 1
        return False

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

            # 先检查完整汉字序列是否在常见复合词中（优先级高于中文数字拆分）
            # 例如"零除错误"不应被拆分为 零(数字)+除错误
            _full_seq_collected = None
            if ch in _simple_nums or ch in _cn_digits:
                _j = pos
                while _j < n and _is_han(source[_j]):
                    if source[_j] in _symbol_map or source[_j] in _punctuation:
                        break
                    _j += 1
                _full_seq = source[pos:_j]
                if _full_seq in _common_compounds or _full_seq in user_definitions:
                    _full_seq_collected = _full_seq

            if _full_seq_collected:
                # 完整标识符在常见复合词或用户定义中，整体输出，不拆分
                kw_check, _ = _match_kw(source, pos)
                if kw_check == _full_seq_collected:
                    _tokens_append(_Token(_TokenType.KEYWORD, _full_seq_collected, line, current_col))
                else:
                    _tokens_append(_Token(_TokenType.IDENTIFIER, _full_seq_collected, line, current_col))
                consumed += len(_full_seq_collected)
                current_col += len(_full_seq_collected)
                continue

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

            # L-056：等待 / 等 是 await 关键字，但规范用法恒带空格（等待 目标()）。
            # 若它出现在汉字序列内部、且其后紧跟标识符续接字符（无空格），说明它是某个
            # 标识符的一部分（等待器 / 团队错等待中止 / 等他），不能当关键字切出。
            # 整串作为单个标识符整体输出，避免把标识符中间的关键字错误拆出。
            # 带空格的 await 会被空格切成独立汉字段（full_identifier 仅为「等待」、其后为
            # 空格），不会触发本规则，仍是 KEYWORD。
            if self._await_in_name(full_identifier, source, pos):
                _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))
                consumed += len(full_identifier)
                current_col += len(full_identifier)
                continue

            # P0-A 确定性合并（有界「精确整串」集合 _P0A_MERGE_WHOLE，非逐词白名单
            # COMMON_COMPOUND_WORDS / IDENTIFIER_SAFE_KEYWORDS）：整串恰好等于 §8.4 点名的
            # 历史雷区（导出事件表/整理模型消息/退出码/接收参数/非空块）+ FFI/排序/输出
            # 同构词（外部命令/排序依据/输出块表）+ 返回码 时，整体成标识符。
            # 此检查独立于「词首是否命中关键字」——即便 整理/列表 等本身不是关键字（走
            # 嵌入扫描会误拆 模/设），也能整体成词；而 接收参数 合并、接收数/段落阶乘接收数
            # 不合并（接收数 不在集合，落回 OLD 词首切分）。「整串精确匹配」保证 返回 永不词首
            # 吞并（L-027：返回 斐波那契 仍拆为 返回/斐波那契）。仅确定性模式生效。
            if self._deterministic and full_identifier in self._P0A_MERGE_WHOLE:
                _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))
                consumed += len(full_identifier)
                current_col += len(full_identifier)
                continue

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
                    #
                    # v7 新单 A：原判据是「只要有数字前缀就切」，于是把
                    # `百分位数` 切成 CHINESE_NUM(100) + IDENTIFIER(分位数)、
                    # `万能钥匙` 切成 CHINESE_NUM(10000) + IDENTIFIER(能钥匙)。
                    # 更糟的是 `设 甲 为 百分位数` 这种切错的流仍能**解析通过**
                    # （数字后跟标识符被当成别的形状消费掉），属静默错译：
                    # 不报错，但产物语义与源码不符。
                    #
                    # 慢速回退路径（本文件 :2105-2127 / :2117-2127）的口径与此
                    # 矛盾——那里只认 `num_len == len(full_identifier)`，else 直接
                    # 整体输出标识符，**根本没有前缀切分**。两条扫描路径对同一串
                    # 汉字给出不同 token 流，说明前缀切分是快速路径独有的越界行为。
                    #
                    # 收窄为：**仅当数字前缀之后紧跟关键字时才切**。
                    #   九十那么大 → 余部 `那么大` 以关键字 `那么` 开头 → 照切（保住原用例）
                    #   百分位数   → 余部 `分位数` 不以关键字开头 → 整体标识符（修掉 bug）
                    #   万能钥匙   → 余部 `能钥匙` 不以关键字开头 → 整体标识符
                    #   一百零一 / 三点一四 → 走上面 :1721「整串都是数字」分支，零影响
                    # 这是**单向收窄**：原本会切的，改后要么仍切、要么不再切；
                    # 不存在「原本不切、改后反而切了」的方向，故不会新造切分。
                    #
                    # 注意：不切的那一侧**只能落空、不能自行输出标识符**。
                    # 全仓 A/B token 流比对（37255 个 .light）抓到过这个错法：
                    # 一旦在此直接 emit(full_identifier) 并 continue，就绕过了下面
                    # :1762 起的用户定义前缀匹配、:1810 的 stdlib 名判定、:1817 起的
                    # 嵌入关键字扫描。`二元运算符表等于_元` 因此被整块吞成一个标识符，
                    # 中间的 `等于` 关键字消失（antlrparser/self_hosted/parser.light）。
                    # 正确做法是让它继续往下走常规标识符流程，由既有逻辑决定怎么切。
                    rest_kw, _rest_len = _match_kw(source, pos + num_len)
                    if rest_kw:
                        # 输出CHINESE_NUM，剩余部分由后续循环处理
                        _tokens_append(_Token(_TokenType.CHINESE_NUM, num_value, line, current_col))
                        consumed += num_len
                        current_col += num_len
                        continue
                    # 余部不是关键字：不在此处切分，落空交给下面的常规标识符流程
            
            # 检查前缀是否在用户定义中（如"阶乘结果"在定义中，当前标识符为"阶乘结果等于"）
            # 但若完整标识符本身是关键字（如"列表弹出"在VERB_ARITY中），则优先识别为关键字
            if user_definitions:
                prefix_matched = None
                # 先检查完整标识符是否本身就是关键字（优先级高于用户定义前缀匹配）
                full_is_keyword = False
                kw_check, _ = _match_kw(source, pos)
                if kw_check == full_identifier:
                    full_is_keyword = True
                # Bug 根因（合并回归）：关键字表拆分为 VERB_ARITY(核心动词) +
                # STDLIB_VERB_ARITY(标准库函数名) 之后，_match_kw 背后的
                # _ALL_KEYWORDS_WITH_VERBS 只并入了 VERB_ARITY，标准库复合动词
                # （列表包含 / 列表长度 / 解析JSON …）对上面这个 kw_check 判断
                # 完全不可见。于是当用户变量名恰好是标准库函数名的前缀时
                # （如 设 列表 为 [...] 之后调用 列表包含(列表, 2)），下面的
                # 用户定义前缀匹配会把 列表包含 撕成 列表 + 包含，而 包含 是
                # 运算符关键字，最终被解析成二元 contains 表达式而非函数调用。
                # 修复：标准库函数名与关键字同等对待，不参与前缀拆分。
                if not full_is_keyword and full_identifier in STDLIB_VERB_ARITY:
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
                    elif remaining and remaining[0] in OPERATOR_VERBS:
                        # 剩余部分以运算符动词开头（如"甲加乙"拆出"甲"后剩"加乙"）
                        # 不拆分，让整个标识符走正常流程，嵌入扫描会正确识别运算符
                        prefix_matched = None
                    elif remaining and not _match_kw(remaining, 0)[0]:
                        # L-010：余部是不含任何关键字的纯标识符续接（程序/命令/结果…）。
                        # 已声明短名（如 从 主程序 导入 主。 里被预扫描收进 user_definitions
                        # 的「主」）绝不应从更长复合词里劈出，否则 主程序→主+程序，
                        # parser 只读第一个 token 当模块名头、语法直接打断。
                        # 仅当余部以关键字开头时才断开（下面 else 兜底，保留既有行为，
                        # 例如 阶乘结果等于 仍拆为 阶乘结果+等于）。
                        prefix_matched = None
                    else:
                        # 输出用户定义的前缀部分作为标识符，剩余部分由后续循环处理
                        _tokens_append(_Token(_TokenType.IDENTIFIER, prefix_matched, line, current_col))
                        consumed += len(prefix_matched)
                        current_col += len(prefix_matched)
                        continue
            
            # 检查完整标识符是否是 stdlib 函数名（在 STDLIB_VERB_ARITY 中但不在 VERB_ARITY 中）
            # 如果是，直接作为 IDENTIFIER 输出，不拆分（防止"字典设置"被拆为 字典+设+置）
            # 注意：VERB_ARITY 中的核心动词仍需作为 KEYWORD 处理
            if full_identifier in STDLIB_VERB_ARITY and full_identifier not in VERB_ARITY:
                _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))
                consumed += len(full_identifier)
                current_col += len(full_identifier)
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
                        # 例外（v7 新单 B）：紧跟成员访问符 `之` 时，该单字不可能是
                        # 复合词前缀——`之` 已被排除出 compound-safe（见 :388 注释
                        # 「之 是成员访问符，应始终拆分」），词边界就在下一个字符处。
                        # `自之姓名` 等价于 `自.姓名`，首 token 必须是 KEYWORD(自)
                        # 才能拿到 self 语义；跳过后会落到嵌入扫描，被当成标识符前缀
                        # 吐成 IDENTIFIER(自)，`自` 退化为一个未定义的自由变量。
                        # 对照：`自加乙`（后随运算符）、`自动化`/`自蛙`（后随普通汉字）
                        # 都不满足本例外，仍按复合词前缀跳过，行为不变。
                        _member_access_follows = remaining.startswith('之')
                        if not is_chinese_num and not _member_access_follows:
                            skip_verb = True

                
                # 动词在词首且后面还有内容时跳过：动词作为复合标识符前缀时不应拆分
                # 例如"输出格式"不应拆为 输出(关键字)+格式，而应作为整体标识符
                # 注意：只对 VERB_ARITY 中的动词生效，不对"返回"等语句关键字生效
                if length > 1 and keyword in VERB_ARITY and len(full_identifier) > length:
                    skip_verb = True

                # L-010（最终收窄版）：仅对 `外部` 这一个「FFI 关键字且永远带空格」的
                # 词首做严格前缀合并，且要求余部不是关键字（否则保持旧拆分）。
                # - `外部命令`→合并（FFI 写法恒为 `外部 函数/段落/…` 带空格，连续 `外部X`
                #   必是标识符，合并安全）；`外部 函数` 带空格不受影响。
                # - 严禁对 `返回` 做词首合并：`返回` 在词首歧义极大——既是"返回语句关键字"
                #   （`返回 斐波那契(...)`），又可能是标识符前缀（`返回码`）。`advanced.light`
                #   实测 `返回 斐波那契(...)` 被合并成 `返回斐波那契` 单标识符 → NameError；
                #   docs/api/stdlib.md 的 `返回类型` 也靠 `返回` 单独成 token。故 `返回` 保持
                #   旧拆分（parser 期望的行为）。`返回码` 成员访问属更难的 parser 级问题，
                #   不在本次词法器修复范围（见升级计划 L27 备注）。
                # - 严禁对 `函数`/`段落`/`类型`/`接口`/`结构体`/`枚举`/`联合体`/`回调`/
                #   `输出`/`模块`/`标准库`/`打印`/`匹配`/`配`/`包含`/`排序` 等复合名成分
                #   做词首合并——它们本就是合法复合名成分（如 `函数名`、`参数类型列表`），
                #   旧拆分是 parser 期望的行为（全量 A/B 测试已抓出"期望类型别名名称"回归）。
                if (length > 1 and keyword == '外部'
                        and len(full_identifier) > length
                        and full_identifier[len(keyword):] not in ALL_KEYWORDS):
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
                #
                # v7 单 02 第二缺口：「运算符在词尾 → 不拆分」这条保护（下面 :1795-1798 与
                # :1879-1885）原先只看纯汉字序列 full_identifier 的右边界，没看**汉字序列
                # 之后紧邻的源字符**。于是 `甲加1。` 里的汉字序列是 `甲加`（停在数字 1），
                # `加` 被判成词尾而不拆，`甲加` 整体成 IDENTIFIER，返回后再被
                # :1306-1308 把 `1` 粘上 → 最终只剩 IDENTIFIER '甲加1' + PERIOD 两个 token，
                # 期望的 4 个（甲 / 加 / 1 / 。）拿不到，BinaryOp 也就无从生成。
                # 判据：若汉字序列之后紧跟 ASCII 数字，说明这是「左操作数 运算符 数字」的
                # 表达式而不是复合词收尾，运算符不该按词尾豁免。
                # 只放行 ASCII 数字、不放行 ASCII 字母，是刻意收窄——`体重增加`（尾部无字符）
                # 与 `数乘阶乘(` （尾部是括号）都不受影响。
                #
                # 已知边界（实测确认）：**已声明的名字不受影响**——`设 衰减1 为 0.9`、
                # `导出 衰减1`、`段落 优化 接收 衰减1：` 三种声明都会让 `衰减1` 进
                # user_definitions，从而在 :1275-1279 的 _match_mixed_user_definition
                # 整体返回，根本走不到这里。只有**未声明的自由名字**（如
                # 积木库/blocks/函数/函数Adam.light:5 里既没声明也没导出的 衰减1）会被拆开，
                # 而那种名字本来就是 NameError，拆不拆都跑不了。
                _seq_tail = i + consumed + len(full_identifier)
                _tail_is_digit_operand = _seq_tail < n and _is_ascii_digit(source[_seq_tail])
                # v7 单 02 收尾：汉字序列后紧跟 **ASCII 字母** 时的同族缺口。
                #
                # 上面那条只放行 ASCII 数字，于是 `甲加1` 拆得对、`和加i` 拆不对：
                # examples/hello.light:18 `设和为和加i` 里 `加` 被判词尾豁免，
                # `和加` 整体成 IDENTIFIER、再把 `i` 粘上 → 产物 `和 = 和加i` → NameError。
                #
                # 但**不能**照搬数字那条放宽成「任意 ASCII 字母」——实测会把
                # `增加count` 拆成 增+加+count、`取模_链式2` 拆成 取+模+_链式+2，
                # 这类复合词/积木名一拆即字面失真（全仓这种形状 64 处、31 个文件，
                # 其中真运算符只有 `和加i` 一处）。字母尾与数字尾的本质差别：
                # `增加count` 这种「复合动词 + ASCII 后缀」的命名完全合法，
                # 而 `甲加1` 不可能是复合词收尾。
                #
                # 判据（比数字那条多一道门）：运算符左边那段必须是**本文件已声明的名字**
                # （在 user_definitions 里）。`设 和 为 0` 让 `和` 进 user_definitions，
                # 于是 `和加i` 判成「左操作数 运算符 右操作数」；而 `增`/`取`/`删`
                # 都不是声明过的名字，`增加count`/`取模_链式2`/`删除x` 一个都不动。
                #
                # 下面两处词尾豁免（探测循环 / 输出循环）必须用同一套判据，否则探测说
                # 「有内嵌关键字」而输出循环又跳过，会走进不一致的分支。
                _tail_is_alpha_operand = _seq_tail < n and _is_ascii_alpha(source[_seq_tail])

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
                            # 检查运算符是否在标识符词尾（如"体重增加"中的"加"）
                            # 在词尾时，作为复合词的一部分，不拆分
                            # 例外（v7 单 02）：汉字序列后紧跟 ASCII 数字时不算词尾，
                            # 见上面 _tail_is_digit_operand 的说明（`甲加1`、`值加1`）；
                            # 紧跟 ASCII 字母时还要求运算符左边是已声明的名字（`和加i`）
                            if (scan_pos + sub_len >= len(full_identifier)
                                    and not _tail_is_digit_operand
                                    and not (_tail_is_alpha_operand
                                             and full_identifier[:scan_pos] in user_definitions)):


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
                            # 标识符安全关键字（如"函数"、"输出"）：是复合标识符的一部分，跳过。
                            # 注：此处不检查 scan_pos——词首的 VERB_ARITY 动词（如"输出格式"中的
                            # "输出"）已在第一层 1264 行判定为复合词前缀，应整体并入标识符
                            #
                            # 例外（v7 新单 B）：IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS
                            # （模块/标准库/打印）只在词中、词尾豁免，词首仍作关键字。
                            # 否则 `打印甲` 会被整体并成 IDENTIFIER('打印甲')，
                            # 把 print 语句静默改写成一个自由标识符。判据与输出循环
                            # 的 `scan_pos > 0` 门一致（见下面 IDENTIFIER_SAFE 分支）。
                            if scan_pos > 0 or sub_kw not in IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS:
                                skip_kw = True
                        elif sub_len == 1 and self._deterministic and sub_kw not in self._P0A_OP:
                            # P0-A：探测循环必须与下面输出循环判据【严格一致】——内部单字
                            # 关键字不标记内嵌。否则探测说「有内嵌关键字」而输出循环又跳过，
                            # 会走进不一致的分支（上面 v7 单 02 已踩过这个坑）。
                            if scan_pos > 0 and scan_pos + sub_len < len(full_identifier):
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
                        # 当前剩余串整体是 stdlib 函数名（如"阶乘"）时，作为整体标识符输出，
                        # 防止"数乘阶乘"被误拆为 数 乘 阶 乘（D08：嵌入式拆分不破坏已知函数名）
                        if full_identifier in STDLIB_VERB_ARITY and full_identifier not in VERB_ARITY:
                            tokens.append(Token(TokenType.IDENTIFIER, full_identifier, line, current_col))
                            consumed += len(full_identifier)
                            current_col += len(full_identifier)
                            full_identifier = ''
                            break
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
                                        # 运算符在词首，通常是复合词的一部分（如"加法"、"减法"）
                                        # 例如：加法(3, 5) → 加法 作为整体标识符
                                        #
                                        # 例外（v7 单 02）：若「运算符之后的剩余部分」本身就是一个
                                        # 已知名字，则该运算符是真运算符而不是复合词前缀。
                                        # 典型：`n乘阶乘(n减1)` 中英文分支已正确切出 IDENTIFIER 'n'，
                                        # 随后的汉字序列是 `乘阶乘`；无此例外时会被切成
                                        # IDENTIFIER '乘阶' + KEYWORD '乘'，再被
                                        # parser_expr 的相邻 IDENTIFIER 合并粘成 'n乘阶'
                                        # （tests/unit/test_parser.py:65 报 `'n乘阶' != 'n'`）。
                                        # `阶乘` 在 src/keywords.py 的 STDLIB_VERB_ARITY 中，
                                        # 据此判定 `乘` 是运算符，正确切成 乘(KW) + 阶乘(ID)。
                                        # 反例保护：`加法` 的剩余部分 `法` 不是已知名字，仍按复合词整体保留。
                                        _rest = full_identifier[sub_len:]
                                        if not (_rest in STDLIB_VERB_ARITY
                                                or _rest in ALL_VERB_ARITY
                                                or _rest in user_definitions):
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
                                # 检查运算符是否在词尾（如"体重增加"中的"加"）
                                # 在词尾时，作为复合词的一部分，不拆分
                                # 例如：体重增加 → 体重增加 作为整体标识符
                                # 注意：在词中时（如"甲加乙"），运算符应作为关键字分隔符
                                # 例外（v7 单 02）：汉字序列后紧跟 ASCII 数字时不算词尾，
                                # 与上面探测循环的判据保持一致，否则探测说「有内嵌关键字」
                                # 而输出循环又跳过，会走进不一致的分支
                                if (scan_pos + sub_len >= len(full_identifier)
                                        and not _tail_is_digit_operand
                                        and not (_tail_is_alpha_operand
                                                 and full_identifier[:scan_pos] in user_definitions)):


                                    # 运算符在词尾，作为复合词的一部分
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
                                # IDENTIFIER_SAFE_KEYWORDS（函数/段落/输出/返回 等）常作
                                # 复合标识符的后缀部分（如 处理函数 / 输出列表），
                                # 因此默认跳过、并入标识符。
                                #
                                # Bug 根因：原实现【无条件】跳过这些关键字，导致紧随其
                                # 他关键字之后、位于剩余标识符开头的安全关键字也被吞掉，
                                # 例如 "那么返回一" 中的 "返回"（紧跟 那么）被并入，
                                # "返回一" 被并成单个标识符，丢失关键字语义。
                                #
                                # 修复方案：仅当 scan_pos > 0（即该关键字位于复合词
                                # 【后缀】位置，如 处理返回 中的 返回）时才跳过；
                                # 位于词首（scan_pos == 0）时按普通关键字输出，
                                # "那么返回一" 正确切分为 那么 + 返回 + 一。
                                if scan_pos > 0:
                                    scan_pos += sub_len
                                    continue
                                # 词首（scan_pos == 0）：默认作关键字输出（如 那么返回一 的 返回）。
                                # 但若整词（含本关键字后续成分）在 user_definitions / COMMON_COMPOUND_WORDS，
                                # 说明它是用户定义的复合名（如 接收参数 / 返回结果 作函数名词首），
                                # 应整体并入标识符，而非把其中「接收/返回」切出。
                                # 独立参数关键字（段落 名 接收 参数）中的「接收」不在白名单，仍作 KEYWORD。
                                if full_identifier in user_definitions or full_identifier in _common_compounds:
                                    scan_pos += sub_len
                                    continue
                            elif sub_len == 1 and self._deterministic and sub_kw not in self._P0A_OP:
                                # P0-A 确定性切词：单字【非运算符】关键字位于标识符【内部】
                                # （既非词首 scan_pos>0、也非词尾 scan_pos+sub_len<len）时并入
                                # 标识符、不拆分——即 §8.4「标识符内部不做拆分，仅词首/词尾做
                                # 关键字判定」。典型：`列表设置` 的 `设`（前有 列表、后有 置）
                                # 不再被劈成 列表/设/置；`甲并` 的 `并` 同理。
                                # 运算符与成员/关系分隔符（_P0A_OP：之/在/于/为/与/加/减…）
                                # 由上面分支处理，故 甲加乙/自之姓名/不在/对于/甲属于乙/
                                # 如果为真 均不受影响。词首（己姓名 的 己）与词尾仍照旧输出关键字。
                                if scan_pos > 0 and scan_pos + sub_len < len(full_identifier):
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

    # ------------------------------------------------------------------
    # P0-A 确定性切词（独立实现，不改动上面的 _tokenize_chinese_sequence）
    # 设计见 复刻harness驱动_light升级计划.md §8.4-P0-A：
    #   「标识符内部不做拆分（仅词首/词尾做关键字判定）」+「不依赖逐词白名单」。
    # 本实现把「是否切分」从「逐词白名单成员判定」改为「关键字类别判定」：
    #   - 运算符/动词/成员访问/逻辑运算符 出现即切（保留无空格表达式：甲加乙、数减一、
    #     n乘阶乘、不在、人之构造）；
    #   - 语句/类型关键字（输出/返回/包含/匹配/排序/模块/接口/结构体/枚举/联合体/
    #     回调/设/为…）无论词首词中词尾一律并入标识符（修复 L-004 家族复合词被切：
    #     对于/排序依据/列表设置/输出格式/某函数）；
    #   - 整串恰为关键字→KEYWORD；恰为用户定义/标准库函数名→整体 IDENTIFIER；
    #     恰为中文数字→CHINESE_NUM。
    # 不再依赖 COMMON_COMPOUND_WORDS / IDENTIFIER_SAFE_KEYWORDS 的逐词登记。
    # ------------------------------------------------------------------
    # P0-A 确定性切词：三类固定「类别集合」（非逐词白名单，全部来自既有关键字类别）。
    #
    # 1) _P0A_OP —— 始终切分（任何位置）：真正的二元运算符 + 成员访问/关系分隔符。
    #    从 OPERATOR_VERBS 剔除 `模`（语料实证其从不作取模运算符，0 处 `X模Y`，
    #    反是 模型/模块/模式/模拟 2900+ 处高频成分，必须并入标识符）；剔除 `步/至/到`
    #    （它们是「运算对象之间的」范围分隔符，仅在 1至10 / 1到10步2 这类被数字包围时
    #    才成词——那种情形范围符本就是独立汉字段，由「整串即关键字」兜底，无需在此随时切）。
    # 2) _P0A_MERGE —— 任何位置并入标识符（复合名/边界连接词）：既有 IDENTIFIER_SAFE_KEYWORDS
    #    （函数/段落/输出/返回/接口/结构体/枚举/联合体/回调/外部/排序/匹配/配/包含/模块/
    #    标准库/打印）+ 本次升级明确要整体成词的复合词头（导出/整理/接收/列表/字典）+ 逻辑
    #    连接词（且/或/非/是/否/并/的，父 作命名红线改名项一并并入）。这些词头后随汉字时
    #    整体并入标识符，使 导出事件表/整理模型消息/接收参数/列表设置/非空 等复合词整体成词。
    # 3) 其余关键字（结构/语句关键字：如果/返回/设/段落/类/己/自/属性/捕获/等待/否则/当/函数/类型…）
    #    仅在「词首」切分——本语言大量使用无空格写法（如果数小于等于二那么返回一 / 返回数乘数 /
    #    段落阶乘接收n：/ 己姓名），词首切分才能正确解析这些构造；词中/词尾则并入标识符。
    # P0-A 确定性切词：有界、类别化、不依赖逐词复合词白名单。
    #
    # 三类固定集合（全部来自既有关键字类别，绝非逐词生长的复合词表）：
    #   _P0A_OP          —— 始终切分（任何位置）：二元/关系/成员运算符与分隔符。
    #                       从 OPERATOR_VERBS 剔除 `模`（语料实证其从不作取模，仅作 模型/模块/
    #                       模式/模拟 2900+ 高频成分，必须并入标识符）；补 之/在/于/为/与 作成员/
    #                       关系分隔符。
    #   _P0A_MERGE_WHOLE —— 有界「精确整串」合并集合（升级计划 §8.4 点名的 6 个历史雷区之
    #                       完整词形 + FFI/排序/输出 同构词形 + 返回码）。仅当整个汉字段 恰好 等于
    #                       集合中的某一整串时才并入标识符，使 导出事件表/整理模型消息/退出码/
    #                       接收参数/非空块/外部命令/排序依据/输出块表/返回码 整体成词；其余关键字
    #                       一律走 OLD 的「词首切分」口径，保证全量语料零回归。这是有界固定集合
    #                       （非逐词生长的 COMMON_COMPOUND_WORDS），从根本上消除 L-004 家族「打地鼠」。
    #                       因是「精确整串匹配」而非「词头+余部合并」，返回 永不词首吞并（L-027）。
    #   _P0A_NEVER_SPLIT —— 永不切分的关键字：`模`（理由同上）。
    _P0A_OP = frozenset(
        (OPERATOR_VERBS - {'模', '步', '至', '到'})
        | {'之', '在', '于', '为', '与'}
    )
    #   _P0A_MERGE_WHOLE —— 有界「精确整串」合并集合（升级计划 §8.4 点名的 6 个历史雷区之
    #                       完整词形 + FFI/排序/输出 同构词形 + 返回码）。仅当整个汉字段 恰好 等于
    #                       集合中的某一整串时才并入标识符；其余关键字一律走 OLD 的「词首切分」口径，
    #                       保证全量语料零回归。这是有界固定集合（非逐词生长的 COMMON_COMPOUND_WORDS）。
    #                       **注意**：集合存的是「整串」（如 导出事件表），不是「词头」（如 导出）。
    #                       故 返回 永不词首吞并——`返回 斐波那契(...)` 中 返回 仍是 KEYWORD（L-027：
    #                       并成单标识符会 NameError）；`返回码` 作为整串在集合中，单独成标识符安全；
    #                       真实语料里 `结果.返回码` 由 1698 行成员访问规则整体成词，二者一致。
    _P0A_MERGE_WHOLE = frozenset({
        '导出事件表', '整理模型消息', '退出码', '接收参数', '非空块',
        '外部命令', '排序依据', '输出块表', '返回码',
    })
    # 永不切分：模（仅作 模型/模块/模式/模拟 2900+ 成分）；步/至/到 仅在数字范围
    # （1至10 / 1到10步2）以「独立汉字段」出现，由「整串即关键字」兜底为 KEYWORD，
    # 故词内切分亦须剔除（异步睡眠/至于 等保持整体）。
    _P0A_NEVER_SPLIT = frozenset({'模', '步', '至', '到'})
    # 单字复合安全字（沿用 OLD _COMPOUND_SAFE_SINGLE_KEYWORDS + 当）：词首且后随非成员访问符
    # 之 时并入标识符、不切分（对/列/当/数/自…），覆盖 对象/列表/当前值/自加乙 等。
    _P0A_COMPOUND_SAFE = _COMPOUND_SAFE_SINGLE_KEYWORDS | {'当'}
    # 硬语句关键字（多字）：词首必须切分（支撑无空格写法 如果数…/段落阶乘…/否则如果…）。
    # 单字硬语句（类/设/己）不在此列 —— 它们不在 _P0A_COMPOUND_SAFE 中，走通用词首切分。
    _P0A_HARD_STMT = frozenset({'如果', '那么', '否则', '否则如果', '段落', '函数', '类型', '捕获', '等待'})
    _P0A_OP_SINGLE = frozenset(k for k in _P0A_OP if len(k) == 1)
    _P0A_CN_SINGLE = _SIMPLE_CHINESE_NUMBERS | frozenset(_CHINESE_DIGITS)

    def _p0a_contains_op(self, source: str, start: int, length: int) -> bool:
        """扫描 [start, start+length) 是否含任一始终切分运算符关键字。"""
        end = start + length
        p = start
        while p < end:
            kw, _ = self._match_keyword(source, p)
            if kw and kw in self._P0A_OP:
                return True
            p += 1
        return False

    def _tokenize_chinese_sequence_det(self, source: str, i: int, line: int, col: int, tokens: List[Token], user_definitions: Set[str] = None) -> int:
        """P0-A 确定性切词入口。

        直接复用 OLD 经过全仓验证的 _tokenize_chinese_sequence 三层切词主流程
        （含 COMMON_COMPOUND_WORDS 冻结安全网、user_definitions 前缀合并、嵌入
        关键字扫描），仅在「复合名头在词首的整体成词」这一确定性规则上做了增强——
        该增强位于 _tokenize_chinese_sequence 内部、由 self._deterministic 门控：
        导出/整理/退出/接收/非空/外部/排序/输出 在词首且余部纯汉字无运算符时整体成
        标识符（导出事件表/整理模型消息/退出码/接收参数/非空块/外部命令/排序依据/
        输出块表），属有界类别规则、不依赖逐词白名单。

        这样：确定性模式 = OLD 全量行为 + 6 个历史雷区确定性收口，零回归；
        非确定性模式 = OLD 原行为，可随时回退比对。
        """
        return self._tokenize_chinese_sequence(source, i, line, col, tokens, user_definitions)
    @staticmethod
    def _emit_p0a_buf(buf: str, line: int, col: int, tokens_append, try_cn) -> None:
        """把标识符缓冲落盘：若整体是纯中文数字则发 CHINESE_NUM，否则 IDENTIFIER。"""
        cn_val, cn_len = try_cn(buf, 0)
        if cn_val is not None and cn_len == len(buf):
            tokens_append(Token(TokenType.CHINESE_NUM, cn_val, line, col))
        else:
            tokens_append(Token(TokenType.IDENTIFIER, buf, line, col))

    def _scan_user_definitions(self, source: str) -> Set[str]:
        """
        预扫描：收集用户定义的变量名和函数名

        用于避免将用户定义的标识符错误拆分为关键字
        """
        definitions = set()
        n = len(source)
        _is_han = _is_han_fast
        _is_space_tab = _is_ascii_space_tab

        # ---- v7 单 20：先把 L4 引 C/Go 块的导出函数名登记进白名单 ----
        #
        # 为什么必须在词法预扫描阶段做：Lexer.tokenize 第一件事就是调用本方法拿
        # user_definitions，随后传给 _tokenize_identifier_or_keyword。等 parser 拿到
        # token 时，J1 的 `快速求和` 已经是 IDENTIFIER 快速 + KEYWORD 求和 两颗，
        # 信息已丢，任何后置补救都来不及。
        #
        # 为什么单开一遍扫描而不塞进下面的主循环：主循环的 search_targets 跳跃与
        # 各分支的 i 推进耦合很紧，插一个分支进去容易悄悄改变既有登记行为。这里
        # 纯加性 —— 只往 definitions 里加名字，主循环一个字节都不动。
        #
        # 前缀门槛与真实分词器保持一致（见主循环的嵌入块检测段）：'嵌入' 两字；
        # '引' 必须紧跟空格/制表/冒号/换行，避免把 引号/引用 这类复合词误判。
        # 额外加「行首门槛」：块前缀之前只能是空白。本方法是裸文本预扫描、不认
        # 字符串字面量，而仓内确实有字符串里写着 引 Python: 的例子
        # （examples/L4_python/all_in_one_demo.light:90、demo4_requests_http.light:30），
        # 行首门槛正好把它们挡在外面 —— 真实分词器不会踩这个坑，因为字符串在
        # 更早的分支就被整体吞掉了。
        _probe = 0
        while _probe < n:
            _p1 = source.find('引', _probe)
            _p2 = source.find('嵌入', _probe)
            if _p1 == -1 and _p2 == -1:
                break
            if _p1 == -1 or (_p2 != -1 and _p2 < _p1):
                _hit, _prefix = _p2, 2
            else:
                _hit, _prefix = _p1, 1
                if not (_hit + 1 < n and source[_hit + 1] in ' \t:\n'):
                    _probe = _hit + 1
                    continue
            _line_start = source.rfind('\n', 0, _hit) + 1
            if source[_line_start:_hit].strip():
                _probe = _hit + 1
                continue
            # 复用分词器自己的块定界（含单 15 的缩进回归/EOF 闭合），保证
            # 「预扫描认定的块体」与「分词认定的块体」同源，不会错位。
            try:
                _tok, _ = self._tokenize_embed_block(source, _hit, 1, 1, _prefix)
            except LexerError:
                # 零缩进块体且无显式结束标记 —— 分词阶段会照样报错，
                # 预扫描不越权代替它报，跳过即可。
                _tok = None
            if _tok is not None and isinstance(_tok.value, tuple) and len(_tok.value) == 2:
                definitions |= extract_embed_export_names(_tok.value[0], _tok.value[1])
            # 只前进一个字符、不跳过块体：今天的主循环本来就会扫进块体并从中
            # 登记 设/段/导 之类的名字，跳过块体会减少既有白名单、可能打红既有绿。
            _probe = _hit + 1


        # 使用 str.find() 跳跃到关键位置，避免逐字符扫描
        # 搜索目标：'《' (段落/类/方法定义), '设' (变量定义), '定义' (变量定义), '函数', '段落' (函数定义), '导' (导出/导入 列表)
        search_targets = ('《', '设', '定', '函', '段', '导', '从')
        i = 0

        # 安全计数器（防止意外死循环）
        _scan_safety = 0

        while i < n:
            _scan_safety += 1
            if _scan_safety > 100000:
                raise RuntimeError(f"_scan_user_definitions 超出安全上限 ({_scan_safety}次迭代), i={i}, n={n}")

            # 找到下一个目标字符的最近位置
            next_pos = n
            for target in search_targets:
                p = source.find(target, i)
                if p != -1 and p < next_pos:
                    next_pos = p
            if next_pos >= n:
                break
            i = next_pos

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
                            if name not in ALL_KEYWORDS and name not in ALL_VERB_ARITY:
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
                        elif name not in ALL_KEYWORDS and name not in ALL_VERB_ARITY:
                            definitions.add(name)
                i = k + 1
                continue

            # 查找 "从 模块名 导入 ..." —— 收集模块名
            # L-015：模块名若含关键字根（如 异步样例、终端），会被按关键字边界拆成
            # 关键字+标识符，导致「从 异步样例 导入」解析失败。
            # 与导入名一样，模块名是用户显式书写的名字，须整段进白名单。
            if source[i] == '从':
                j = i + 1
                # 跳过名称前的所有空白（含换行、全角空格）
                while j < n and source[j] in ' \t\n\r\f\v\u3000':
                    j += 1
                # 相对导入前缀：从 .模块 / 从 ..模块
                while j < n and source[j] == '.':
                    j += 1
                # 收集模块名（汉字/ASCII/下划线/点号，支持 a.b.c 路径）
                k = j
                while k < n and (_is_han(source[k]) or _is_ascii_alnum(source[k])
                                 or source[k] == '_' or source[k] == '.'):
                    k += 1
                if k > j:
                    name = source[j:k]
                    if name not in ALL_KEYWORDS:
                        definitions.add(name)
                    j = k
                i = j
                continue

            # 查找 "导出 名称1 名称2 ..." 或 "从 模块 导入 名称1 名称2 ..."
            # 将导出/导入列表中的名字也加入白名单，避免带关键字前缀的名字被拆分成 关键字 + 标识符
            # 例如 "导出 生成AI阶段提示。" -> "生成" 是关键字，若不加入白名单会被拆成 KEYWORD(生成) + IDENTIFIER(AI阶段提示)
            if source[i:i+2] in ('导出', '导入'):
                j = i + 2
                # 跳过名称列表前的所有空白（含换行、全角空格）
                while j < n and source[j] in ' \t\n\r\f\v　':
                    j += 1
                # 逐段收集名字（名字以空白分隔，遇到句号或换行结束）
                while j < n and source[j] not in '。\n':
                    # 跳过名字之间的空白
                    while j < n and source[j] in ' \t\n\r\f\v　':
                        j += 1
                    if j >= n or source[j] in '。\n':
                        break
                    # 收集一个标识符：汉字 或 ASCII 字母/数字/下划线/点（支持中英混合、
                    # 含下划线的 Python 模块名，如 生成AI阶段提示、ai_api_helper、a.b.c）
                    k = j
                    while k < n and (_is_han(source[k]) or _is_ascii_alnum(source[k])
                                     or source[k] == '_' or source[k] == '.') and source[k] not in ' \t\n\r\f\v　。':
                        k += 1
                    if k > j:
                        name = source[j:k]
                        if name not in ALL_KEYWORDS:
                            definitions.add(name)
                        j = k
                    else:
                        # 遇到非标识符、非空白字符（如冒号、标点）时跳过一个字符，
                        # 避免死循环。例如 "导入 Python: ai_api_helper。" 中的 ":"
                        j += 1
                i = j
                continue

            # 查找 "函数/段落 段名 参数 参数名" 格式
            if source[i:i+2] == '函数' or source[i:i+2] == '段落':
                j = i + 2
                # 跳过空白
                while j < n and _is_space_tab(source[j]):
                    j += 1
                # 收集段名（遇到段落语法关键字或冒号停止）
                # 支持汉字和ASCII字母数字的标识符
                k = j
                # 计算本定义头部结束位置（遇到冒号/换行即止），用于判定「最后一个」接收/返回 即参数分隔符
                _header_end = k
                while _header_end < n and source[_header_end] not in '：:\n':
                    _header_end += 1
                # 预定位分隔符：头部内「最后一个」接收/返回。
                # - 若它后接空白/冒号/标点（清晰分隔符），直接采用；
                # - 否则（老式无空格写法，如 加法接收甲 的 接收 后接 甲）取头部内最后一个 接收/返回。
                # 这样：名字内部的 接收（接收参数、测直接收集、消息接收器、接收消息）后面还有
                # 更靠后的分隔符 接收，不会在此截断，段名完整（如 接收参数）；
                # 真正的分隔符 接收（加法接收甲 中唯一/最后的那个）才会截断段名 → 段名=加法。
                # 修复 L-020 伴生回归：旧逻辑遇「接收后接汉字」不截断，把 加法 吞进 加法接收甲，
                # 使 加法 未注册、接收 分隔符被合并，basic.light 等示例编译报「期望冒号但得到逗号」。
                _sep_pos = -1
                _s = j
                while _s < _header_end:
                    _kw, _kl = self._match_keyword(source, _s)
                    if _kw and _kl > 0 and _kw in ('接收', '返回'):
                        _a = _s + _kl
                        if _a >= _header_end or source[_a] in ' \t\n\r\f\v　：:。、，,；;':
                            _sep_pos = _s
                            break
                    _s += 1
                if _sep_pos == -1:
                    _s = j
                    while _s < _header_end:
                        _kw, _kl = self._match_keyword(source, _s)
                        if _kw and _kl > 0 and _kw in ('接收', '返回'):
                            _sep_pos = _s
                        _s += 1
                # 段名收集循环：遇到非名字字符或定位到的分隔符即停
                while k < n and (_is_han(source[k]) or _is_ascii_alnum(source[k])
                                 or source[k] == '_'):
                    if _sep_pos != -1 and k >= _sep_pos:
                        break
                    k += 1
                if k > j:
                    segment_name = source[j:k]
                    # 收集段落名（允许覆盖动词名称）
                    if segment_name not in ALL_KEYWORDS:
                        definitions.add(segment_name)
                # 让后续「接收/参数 参数名」收集逻辑从分隔符位置继续
                if _sep_pos != -1:
                    k = _sep_pos

                # 检查是否有 "接收" 或 "参数" 关键字（旧式 接收 / 新式 参数）
                # 旧式「段落 名 接收 参数：」的参数名必须整体注册进白名单，
                # 否则含已注册子名的复合参数名（如 年月）会被最长匹配切碎成 年/月
                j = k
                while j < n and _is_space_tab(source[j]):
                    j += 1
                if source[j:j+2] in ('接收', '参数'):
                    j += 2
                    # 跳过空白
                    while j < n and _is_space_tab(source[j]):
                        j += 1
                    # 收集参数名（可能多个参数，空格或中英文逗号分隔，遇冒号/句号/换行结束）
                    # 支持汉字和 ASCII 字母数字的标识符
                    while j < n:
                        prev_j = j
                        k = j
                        while k < n and (_is_han(source[k]) or _is_ascii_alnum(source[k])
                                         or source[k] == '_') and source[k] not in '。：，, 、；;':
                            k += 1
                        if k > j:
                            param_name = source[j:k]
                            # 排除关键字和动词
                            if param_name not in ALL_KEYWORDS and param_name not in ALL_VERB_ARITY:
                                definitions.add(param_name)
                        j = k
                        # 跳过空白与参数分隔符（中英文逗号/顿号/分号）
                        while j < n and (_is_space_tab(source[j]) or source[j] in '，,、；;'):
                            j += 1
                        if j >= n or source[j] in '。：\n':
                            break
                        # 兜底：本回合无任何前进则跳过一个字符，避免遇到非常规分隔符时死循环
                        if j == prev_j:
                            j += 1
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
                # 支持汉字和ASCII字母数字组成的标识符（如"变量1"、"数据2"）
                k = j
                while k < n and (_is_han(source[k]) or _is_ascii_alnum(source[k])
                                 or source[k] == '_'):
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
                    # 只排除真正的关键字 —— 与 :2664（段 的形参分支）、:2735（设 分支）
                    # 同口径。本分支此前漏了这道闸门，导致注释里的「自定义段。」被当成
                    # 用户定义名 `段`（预扫描是裸文本扫描，不跳注释也不跳字符串），
                    # 随后 `段 主():` 的 `段` 被降级成 IDENTIFIER，整个文件解析崩掉
                    # （examples/E阶段_L3L4原生语法/E4_L4_沙箱隔离验证.light:70 的注释）。
                    # 关键字本就不能当用户变量名，不该出现在 user_definitions 里。
                    if name not in ALL_KEYWORDS:
                        definitions.add(name)
                i = k
            elif source[i] == '设':
                j = i + 1
                # 跳过空白
                while j < n and _is_space_tab(source[j]):
                    j += 1
                # 收集标识符（设 甲 为/等于 值）
                # 支持汉字和ASCII字母数字组成的标识符（如"环节1"、"数据2"）
                k = j
                collected_something = False
                while k < n and (_is_han(source[k]) or _is_ascii_alnum(source[k])
                                 or source[k] == '_'):
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
