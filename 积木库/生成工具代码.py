# -*- coding: utf-8 -*-
"""
光明积木 · 自动化工具代码生成器 v0.2
======================================
读取积木库导出 JSON 和 .light 源码，为每个积木生成等价的 Python 函数。
输出按领域分组的 Python 模块，可直接 import 使用。

用法:
  python 积木库/生成工具代码.py                              # 生成所有积木
  python 积木库/生成工具代码.py --limit 100                  # 只生成前 100 块
  python 积木库/生成工具代码.py --domain 数学,文本           # 只生成指定领域
  python 积木库/生成工具代码.py --verify                     # 生成后验证语法
"""

import json, os, re, sys, argparse, ast
from collections import defaultdict

_HERE = os.path.abspath(os.path.dirname(__file__))
_输出目录 = os.path.join(_HERE, '工具代码')


# ══════════════════════════════════════════════════════
# 光明语言 → Python 翻译引擎
# ══════════════════════════════════════════════════════

# 关键词翻译（控制流）
_关键词 = {
    '当': 'while',
    '如果': 'if',
    '否则如果': 'elif',
    '否则': 'else',
    '返回': 'return',
    '设': 'let',    # 特殊处理
    '为': '=',
    '接收': 'def',  # 特殊处理
    '段落': 'def',  # 特殊处理
    '导出': 'export',  # 特殊处理
}

# 运算符（按长度降序，避免短词误匹配）
_运算符表 = [
    ('小于等于', '<='),
    ('大于等于', '>='),
    ('不等于', '!='),
    ('等于', '=='),
    ('小于', '<'),
    ('大于', '>'),
    ('且', 'and'),
    ('或', 'or'),
    ('非', 'not'),
    ('整除', '//'),
    ('除以', '/'),
    ('加', '+'),
    ('减', '-'),
    ('乘乘', '**'),   # 乘 乘 → **（幂运算）
    ('乘方', '**'),
    ('乘', '*'),
    ('异或', '^'),
    ('除', '/'),
    ('取模', '%'),
    ('模', '%'),
    ('幂', '**'),
    ('取余', '%'),
]

# 内置函数映射
_内置函数表 = {
    '长度': 'len',
    '转字符串': 'str',
    '转整数': 'int',
    '转小数': 'float',
    '转浮点': 'float',
    '转逻辑': 'bool',
    '转列表': 'list',
    '整数': 'int',
    '绝对值': 'abs',
    '最大值': 'max',
    '最小值': 'min',
    '求和': 'sum',
    '类型': 'type',
    '打印': 'print',
    '范围': 'range',
    '排序': 'sorted',
    '枚举': 'enumerate',
    '反转': 'reversed',
    '取长度': 'len',
    '取整': 'int',
    '取绝对值': 'abs',
    '取最大值': 'max',
    '取最小值': 'min',
    '取类型': 'type',
    '取范围': 'range',
    '转文本': 'str',
    '转数': 'float',
    '取小数': 'float',
    '取整数': 'int',
    '取平方根': 'math.sqrt',
    '取对数': 'math.log',
    '取指数': 'math.exp',
    '取正弦': 'math.sin',
    '取余弦': 'math.cos',
    '取正切': 'math.tan',
    '取随机': 'random.random',
    '随机': 'random.random',
    '取随机整数': 'random.randint',
    '取随机范围': 'random.randrange',
    '开平方': 'math.sqrt',
    '开立方': 'math.cbrt',
    '取余': 'math.fmod',
    '取模': 'math.fmod',
    '取随机数': 'random.random',
    '取随机元素': 'random.choice',
    '取随机样本': 'random.sample',
    '乱序': 'random.shuffle',
    '取当前时间': 'time.time',
    '取当前日期': 'time.strftime',
    '格式化时间': 'time.strftime',
    '解析时间': 'time.strptime',
    '取时间戳': 'time.time',
    '睡眠': 'time.sleep',
}

# 方法调用映射（.光明(x) → .py(x)）
_方法表 = {
    '追加': 'append',
    '分割': 'split',
    '替换': 'replace',
    '查找': 'find',
    '编码': 'encode',
    '解码': 'decode',
    '去除空白': 'strip',
    '去空格': 'strip',
    '转大写': 'upper',
    '转小写': 'lower',
    '排序': 'sort',
    '反转': 'reverse',
    '弹出': 'pop',
    '清空': 'clear',
    '复制': 'copy',
    '计数': 'count',
    '包含': '__contains__',  # 特殊处理：x.包含(y) → y in x
    '开始': 'startswith',
    '结束': 'endswith',
    '是否以': 'startswith',
    '加入': 'join',
    '映射': 'map',
    '过滤': 'filter',
    '减少': 'reduce',
    '查找所有': 'findall',
    '匹配': 'match',
    '搜索': 'search',
    '截取': '__slice__',  # 特殊处理
    '去除前缀': 'removeprefix',
    '去除后缀': 'removesuffix',
    '居中': 'center',
    '左对齐': 'ljust',
    '右对齐': 'rjust',
    '补零': 'zfill',
    '填充': 'zfill',
    '补空格': 'ljust',
    '检测': 'startswith',  # 启发式
    '修剪': 'strip',
    '大写': 'upper',
    '小写': 'lower',
    '切分': 'split',
    '拼接': 'join',
}

# 哈希函数映射（X 的 MD5 → hashlib.md5(X.encode()).hexdigest()）
_哈希函数表 = {
    'MD5': 'md5',
    'SHA1': 'sha1',
    'SHA256': 'sha256',
    'SHA512': 'sha512',
    'SHA384': 'sha384',
    'SHA224': 'sha224',
    'RIPEMD160': 'ripemd160',
    'BLAKE2': 'blake2b',
    'CRC32': 'crc32',
    'CRC64': 'crc64',
    'HMAC_MD5': 'hmac_md5',
    'HMAC_SHA1': 'hmac_sha1',
    'HMAC_SHA256': 'hmac_sha256',
    '校验和': 'checksum',
}

# 特殊后缀表达式：X 的 Y → python 表达式
# 优先级从长到短
_后缀表达式表 = [
    ('平方根', 'math.sqrt(V)'),
    ('立方根', 'math.cbrt(V)'),
    ('立方', 'V**3'),
    ('平方', 'V**2'),
    ('绝对值', 'abs(V)'),
    ('相反数', '-V'),
    ('倒数', '1/V'),
]


def _翻译_三元表达式(expr):
    """递归翻译光明语言的三元表达式：如果 A 则 B 否则 C → B if A else C

    支持嵌套（从最外层逐层向内翻译）。
    """
    while '如果' in expr:
        def _替换(m):
            return f'{_翻译_表达式(m.group(2).strip())} if {_翻译_表达式(m.group(1).strip())} else {_翻译_表达式(m.group(3).strip())}'
        new_expr = re.sub(r'如果\s+(.+?)\s+则\s+(.+?)\s+否则\s+(.+)', _替换, expr, count=1)
        if new_expr == expr:
            break
        expr = new_expr
    return expr


def _翻译_截取调用(expr):
    """将截取(对象, 起始, 结束) 翻译为 对象[起始:结束]

    支持嵌套括号（如截取(结果, 1, 长度(结果))）。
    """
    m = re.search(r'截取\s*\(', expr)
    if not m:
        return expr
    start = m.start()
    # 找到匹配的右括号
    depth = 0
    i = m.end() - 1  # '(' 的位置
    while i < len(expr):
        if expr[i] == '(':
            depth += 1
        elif expr[i] == ')':
            depth -= 1
            if depth == 0:
                inner = expr[m.end():i]
                parts = [p.strip() for p in inner.split(',')]
                if len(parts) == 3:
                    replacement = f'{parts[0]}[{parts[1]}:{parts[2]}]'
                    return expr[:start] + replacement + expr[i+1:]
                break
        i += 1
    return expr


def _翻译_运算符(expr):
    """将光明语言的中缀运算符翻译为 Python 运算符"""
    # 先合并空格分割的复合运算符：大于 等于 → 大于等于
    expr = _预翻译_空格运算符(expr)
    for 光明, py in _运算符表:
        if 光明 in expr:
            # 使用单词边界，避免"除"误匹配"除数"中的"除"
            # 排除函数调用：乘方(...) 是函数名不是运算符
            expr = re.sub(r'(?<!\w)' + re.escape(光明) + r'(?!\w|\()', py, expr)
    return expr


def _预翻译_空格运算符(expr):
    """合并空格分割的复合运算符：大于 等于 → 大于等于"""
    expr = re.sub(r'大于\s+等于', '大于等于', expr)
    expr = re.sub(r'小于\s+等于', '小于等于', expr)
    expr = re.sub(r'不\s+等于', '不等于', expr)
    # 乘 乘 → 乘乘（幂运算）
    expr = re.sub(r'乘\s+乘', '乘乘', expr)
    return expr


def _翻译_内置函数(expr):
    """将光明语言的内置函数调用翻译为 Python 内置函数"""
    # 按长度降序排列，避免短名误匹配
    for 光明 in sorted(_内置函数表, key=len, reverse=True):
        py = _内置函数表[光明]
        # 匹配 光明(...) 模式
        expr = re.sub(r'\b' + re.escape(光明) + r'\s*\(', py + '(', expr)
    return expr


def _翻译_方法调用(expr):
    """将光明语言的方法调用翻译为 Python 方法调用"""
    # 特殊处理 .len() → len(...)（从右向左匹配，避免引号干扰）
    expr = _翻译_点长度(expr, 'len')
    # 特殊处理 .长度() → len(...)（从右向左匹配，避免引号干扰）
    expr = _翻译_点长度(expr, '长度')

    # 先处理 .截取() 和 .包含() 等特殊方法
    # .截取(i, j) → [i:j]（支持嵌套括号）
    expr = _翻译_截取方法(expr)
    # .包含(y) → y in x
    expr = _翻译_包含方法(expr)

    for 光明, py in _方法表.items():
        if py in ('__slice__', '__contains__'):
            continue  # 已在上面处理
        else:
            expr = re.sub(
                r'\.' + re.escape(光明) + r'\s*\(',
                '.' + py + '(', expr
            )
    return expr


def _翻译_截取方法(expr):
    """处理 .截取(i, j) → [i:j]，支持嵌套括号"""
    # 从右向左处理，避免嵌套冲突
    while True:
        m = re.search(r'(\S+?)\.' + re.escape('截取') + r'\s*\(', expr)
        if not m:
            break
        obj = m.group(1)
        start_pos = m.start()
        # 找到匹配的右括号
        depth = 0
        i = m.end() - 1  # '(' 的位置
        while i < len(expr):
            if expr[i] == '(':
                depth += 1
            elif expr[i] == ')':
                depth -= 1
                if depth == 0:
                    inner = expr[m.end():i]
                    # 按逗号分割参数（注意不在括号内的逗号）
                    parts = _分割_参数(inner)
                    if len(parts) == 2:
                        replacement = f'{obj}[{parts[0]}:{parts[1]}]'
                        expr = expr[:start_pos] + replacement + expr[i+1:]
                    break
            i += 1
        else:
            break  # 没找到匹配的括号
    return expr


def _翻译_点长度(expr, 方法名):
    """处理 .长度() → len(...)，从右向左匹配避免引号干扰"""
    while True:
        # 从右向左找最后一个 .方法名()
        idx = expr.rfind(f'.{方法名}()')
        if idx < 0:
            break
        # 找到方法名前面的表达式边界
        prefix = expr[:idx]
        # 从 idx-1 向左找，找到匹配的表达式起点
        # 跳过括号匹配，找到最左边的表达式起点
        depth = 0
        start = idx - 1
        while start >= 0:
            ch = prefix[start]
            if ch == ')':
                depth += 1
            elif ch == '(':
                depth -= 1
                if depth < 0:
                    start += 1
                    break
            elif ch in (' ', '\t', '=', ',', ':', ';', '（', '，'):
                if depth == 0:
                    start += 1
                    break
            start -= 1
        if start < 0:
            start = 0
        expr = expr[:start] + f'len({prefix[start:]})' + expr[idx + len(f'.{方法名}()'):]
    return expr


def _翻译_包含方法(expr):
    """处理 .包含(y) → y in x"""
    while True:
        m = re.search(r'(\S+?)\.' + re.escape('包含') + r'\s*\(', expr)
        if not m:
            break
        obj = m.group(1)
        start_pos = m.start()
        depth = 0
        i = m.end() - 1
        while i < len(expr):
            if expr[i] == '(':
                depth += 1
            elif expr[i] == ')':
                depth -= 1
                if depth == 0:
                    arg = expr[m.end():i].strip()
                    replacement = f'{arg} in {obj}'
                    expr = expr[:start_pos] + replacement + expr[i+1:]
                    break
            i += 1
        else:
            break
    return expr


def _分割_参数(inner):
    """按逗号分割函数参数，跳过括号内的逗号"""
    parts = []
    depth = 0
    current = ''
    for ch in inner:
        if ch == '(':
            depth += 1
            current += ch
        elif ch == ')':
            depth -= 1
            current += ch
        elif ch == ',' and depth == 0:
            parts.append(current.strip())
            current = ''
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


def _翻译_表达式(expr):
    """完整翻译一个光明表达式为 Python 表达式"""
    expr = expr.strip()
    # 清理全角符号
    expr = expr.replace('：', ':').replace('，', ',').replace('（', '(').replace('）', ')')
    expr = expr.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    # 先处理三元表达式
    expr = _翻译_三元表达式(expr)
    # 再处理 X 的 Y 后缀表达式（平方根、哈希等）
    expr = _翻译_的表达式(expr)
    # 再处理方法调用
    expr = _翻译_方法调用(expr)
    # 处理 截取(a, i, j) → a[i:j] 函数调用（支持嵌套括号）
    expr = _翻译_截取调用(expr)
    # 再处理内置函数
    expr = _翻译_内置函数(expr)
    # 最后处理运算符
    expr = _翻译_运算符(expr)
    return expr


def _翻译_的表达式(expr):
    """处理 X 的 Y 模式：平方根、立方根、哈希等

    X 的 平方根 → math.sqrt(X)
    X 的 立方根 → math.cbrt(X)
    X 的 立方 → X**3
    X 的 MD5 → hashlib.md5(str(X).encode()).hexdigest()
    """
    # 处理哈希函数（X 的 MD5 → hashlib.md5(str(X).encode()).hexdigest()）
    for 哈希名 in sorted(_哈希函数表, key=len, reverse=True):
        py名 = _哈希函数表[哈希名]
        while True:
            m = re.search(r'(\S+?)\s+的\s+' + re.escape(哈希名), expr)
            if not m:
                break
            var = m.group(1).strip()
            if py名 == 'crc32':
                replacement = f'zlib.crc32(str({var}).encode())'
            else:
                replacement = f'hashlib.{py名}(str({var}).encode()).hexdigest()'
            expr = expr[:m.start()] + replacement + expr[m.end():]
        # 也处理 对 X 做 哈希名 的模式
        while True:
            m = re.search(r'对\s+(\S+?)\s+做\s+' + re.escape(哈希名), expr)
            if not m:
                break
            var = m.group(1).strip()
            if py名 == 'crc32':
                replacement = f'zlib.crc32(str({var}).encode())'
            else:
                replacement = f'hashlib.{py名}(str({var}).encode()).hexdigest()'
            expr = expr[:m.start()] + replacement + expr[m.end():]

    # 处理后缀表达式（X 的 平方根 → math.sqrt(X)）
    for 后缀, template in _后缀表达式表:
        while True:
            m = re.search(r'(\S+?)\s+的\s+' + re.escape(后缀), expr)
            if not m:
                break
            var = m.group(1).strip()
            # 如果 var 是运算符结尾，说明匹配错误（如"乘 乘 的 平方根"）
            if var in ('乘', '加', '减', '除', '模'):
                break
            replacement = template.replace('V', var)
            expr = expr[:m.start()] + replacement + expr[m.end():]

    return expr


def _计算_缩进深度(行):
    """计算光明代码的缩进深度（以 4 空格为单位）"""
    s = 行.rstrip('\n')
    缩进 = len(s) - len(s.lstrip())
    return 缩进 // 4


def _翻译_行(行):
    """翻译单行光明代码为 Python 代码

    返回:
        (原始缩进深度, Python 代码行) 或 None
    """
    s = 行.rstrip('\n')
    if not s.strip():
        return None

    裸 = s.strip()
    # 计算原始缩进深度（用于 Python 缩进）
    原始缩进 = _计算_缩进深度(s)

    # 注释直接保留
    if 裸.startswith('#'):
        return (原始缩进, 裸)

    # 去掉末尾的句号
    if 裸.endswith('。'):
        裸 = 裸[:-1]
    elif 裸.endswith('：'):
        裸 = 裸[:-1] + ':'

    # ── 段落 X 接收 a, b: → def X(a, b): ──
    m = re.match(r'段落\s+(\w+)\s+接收\s*(.*)', 裸)
    if m:
        函数名 = m.group(1)
        参数 = m.group(2).strip().rstrip('：').rstrip(':')
        return (0, f'def {函数名}({参数}):')

    # ── 导出 X → 忽略 ──
    if 裸.startswith('导出'):
        return None

    # ── 设 x 为 y → x = y ──
    m = re.match(r'设\s+(\w+)\s+为\s+(.*)', 裸)
    if m:
        变量 = m.group(1)
        值 = _翻译_表达式(m.group(2))
        return (原始缩进, f'{变量} = {值}')

    # ── 否则如果 cond → elif cond: ──
    m = re.match(r'否则如果\s+(.*)[：:]', 裸)
    if m:
        return (原始缩进, f'elif {_翻译_表达式(m.group(1))}:')

    # ── 否则 → else: ──
    if 裸.replace('：', ':').replace(':', '') == '否则':
        return (原始缩进, 'else:')

    # ── 当 cond → while cond: ──
    m = re.match(r'当\s+(.*)[：:]', 裸)
    if m:
        return (原始缩进, f'while {_翻译_表达式(m.group(1))}:')

    # ── 如果 cond → if cond: ──
    m = re.match(r'如果\s+(.*)[：:]', 裸)
    if m:
        return (原始缩进, f'if {_翻译_表达式(m.group(1))}:')

    # ── 返回 x → return x ──
    m = re.match(r'返回\s+(.*)', 裸)
    if m:
        return (原始缩进, f'return {_翻译_表达式(m.group(1))}')

    # ── 普通表达式 ──
    return (原始缩进, _翻译_表达式(裸))


def _翻译_积木源码(源码路径, 导出名, 输入参数):
    """读取 .light 文件，翻译为 Python 函数源码

    使用原始 .light 的缩进结构来确定 Python 的缩进层次。
    """
    if not os.path.isfile(源码路径):
        return None

    with open(源码路径, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 第一遍：收集所有非空有效行的缩进深度
    processed = []
    for ln in lines:
        r = _翻译_行(ln)
        if r is not None:
            processed.append(r)

    if not processed:
        return None

    # 检查是否包含段落定义
    has_def = any('def ' in l for _, l in processed)

    if not has_def:
        # 没有段落定义，用导出名创建函数头
        参数串 = ', '.join(输入参数) if 输入参数 else ''
        # 将所有行缩进一级
        result = [f'def {导出名}({参数串}):']
        for depth, line in processed:
            # 确保至少 4 空格缩进
            py_indent = 1  # 函数体内至少 1 级
            result.append('    ' * py_indent + line)
        if len(result) == 1:
            result.append('    pass')
        return '\n'.join(result)

    # 已有段落定义：用原始缩进映射到 Python 缩进
    # 找到段落定义的缩进基准
    py_lines = []
    base_indent = None

    for depth, line in processed:
        if line.startswith('def '):
            py_lines.append(line)
            base_indent = depth
        elif line.startswith('#'):
            # 注释保持位置
            if base_indent is not None:
                py_lines.append('    ' + line)
            else:
                py_lines.append(line)
        else:
            if base_indent is not None:
                # depth 1 = 缩进 4, depth 2 = 缩进 8, 等等
                py_indent = depth  # 原始缩进深度直接映射到 Python 缩进层级
                py_lines.append('    ' * py_indent + line)
            else:
                # 还没遇到 def，保留原样
                py_lines.append(line)

    if len(py_lines) == 1:
        py_lines.append('    pass')

    return '\n'.join(py_lines)


# ══════════════════════════════════════════════════════
# 辅助：获取块参数名列表
# ══════════════════════════════════════════════════════
def _获取参数名(块):
    输入 = 块.get('输入', [])
    return [p.get('名', f'参{i}') for i, p in enumerate(输入)]


# ══════════════════════════════════════════════════════
# 主生成函数
# ══════════════════════════════════════════════════════
def 生成_工具代码(导出路径=None, 限制=None, 目标领域=None, 验证语法=False):
    """生成所有积木的 Python 工具代码

    参数:
        导出路径: 导出的 JSON 路径
        限制: 最多生成的积木数
        目标领域: 限定生成的领域列表
        验证语法: 是否验证生成的 Python 语法

    返回:
        {领域: (成功数, 失败数)}
    """
    if 导出路径 is None:
        导出路径, _ = os.path.splitext(os.path.join(_HERE, '积木库_导出.json'))
        导出路径 += '.json'

    if not os.path.isfile(导出路径):
        print(f"错误: 找不到导出文件 {导出路径}")
        print("请先运行 export_blocks.py 生成导出文件")
        return {}

    # 加载导出数据
    with open(导出路径, 'r', encoding='utf-8') as f:
        数据 = json.load(f)

    块列表 = 数据['块']
    print(f"加载积木库: {数据['统计']['总块数']} 块, {数据['统计']['领域数']} 个领域")

    # 按领域分组
    领域分组 = defaultdict(list)
    for 块 in 块列表:
        领域 = 块.get('领域', '其他')
        领域分组[领域].append(块)

    if 目标领域:
        目标集 = set(目标领域)
        领域分组 = {k: v for k, v in 领域分组.items() if k in 目标集}

    # 创建输出目录
    os.makedirs(_输出目录, exist_ok=True)

    # 保留领域顺序
    领域顺序 = [d for d in 数据.get('统计', {}).get('领域列表', []) if d in 领域分组]

    # 统计
    总生成 = 0
    总翻译成功 = 0
    总翻译失败 = 0
    总语法错误 = 0
    各领域统计 = {}

    # 处理每个领域
    for 领域 in 领域顺序:
        块们 = 领域分组[领域]
        if 限制 and 总生成 >= 限制:
            break
        if 限制:
            剩余 = 限制 - 总生成
            块们 = 块们[:剩余]

        py_lines = [
            '# -*- coding: utf-8 -*-',
            f'"""光明积木 · {领域}领域工具代码',
            '',
            f'自动生成于 {数据.get("导出时间", "?")}',
            f'基于光明积木库 v{数据.get("版本", "?")}',
            f'"""',
            '',
            'import math, time, random, hashlib, zlib',
            '',
        ]

        领域成功 = 0
        领域失败 = 0
        领域语法错 = 0

        for 块 in 块们:
            名称 = 块['名称']
            导出名 = 块.get('导出名', 名称)
            路径 = 块.get('路径', '')
            描述 = 块.get('描述', '')
            输入 = 块.get('输入', [])
            输出 = 块.get('输出', {})

            输出类型 = 输出.get('类型', '?') if isinstance(输出, dict) else '?'
            源码路径 = os.path.join(_HERE, 路径) if 路径 else ''
            参数名 = _获取参数名(块)

            # 生成 Python 函数
            py_code = _翻译_积木源码(源码路径, 导出名, 参数名)

            if py_code:
                输入类型 = [p.get('类型', '?') for p in 输入]
                类型签名 = f"# 输入: {输入类型} → 输出: {输出类型}"

                # 语法验证
                if 验证语法:
                    try:
                        ast.parse(py_code)
                    except SyntaxError as e:
                        # 出错时用桩代码
                        py_code = None
                        领域语法错 += 1
                        总语法错误 += 1
                        print(f"  ⚠ {名称}: 语法错误 ({e.msg})")

            if py_code:
                py_lines.append(f'# ── {名称} ──')
                py_lines.append(类型签名)
                py_lines.append(py_code)
                py_lines.append('')
                领域成功 += 1
                总翻译成功 += 1
            else:
                # 无源码或语法错误，生成桩代码
                输入类型 = [p.get('类型', '?') for p in 输入]
                参数串 = ', '.join(参数名)

                py_lines.append(f'# ── {名称}（桩代码）──')
                py_lines.append(f'# 输入: {输入类型} → 输出: {输出类型}')
                py_lines.append(f'def {导出名}({参数串}):')
                py_lines.append(f'    """{描述}"""')
                py_lines.append(f'    raise NotImplementedError("积木 {名称} 源码未找到: {路径}")')
                py_lines.append('')
                领域失败 += 1
                总翻译失败 += 1

            总生成 += 1

        # 写入领域文件
        领域文件名 = f'{领域}.py'
        领域路径 = os.path.join(_输出目录, 领域文件名)
        with open(领域路径, 'w', encoding='utf-8') as f:
            f.write('\n'.join(py_lines))

        各领域统计[领域] = (领域成功, 领域失败, 领域语法错)
        status = f"{领域成功}/{领域失败}/{领域语法错}"
        print(f"  [{领域}] {status} -> {领域文件名}")

    # 生成 __init__.py
    _生成_init(领域顺序, 数据)

    # 报告
    print(f"\n{'='*50}")
    print(f"生成完成!")
    print(f"  总积木: {总生成}")
    print(f"  翻译成功: {总翻译成功}")
    print(f"  翻译失败: {总翻译失败}")
    if 验证语法:
        print(f"  语法错误: {总语法错误}")
    print(f"  输出目录: {_输出目录}")
    print(f"  领域文件: {len(领域顺序)} 个")

    return 各领域统计


def _生成_init(领域顺序, 数据):
    """生成 __init__.py 导入所有领域模块"""
    统计 = 数据.get('统计', {})
    lines = [
        '# -*- coding: utf-8 -*-',
        f'"""光明积木工具代码 · 自动导入所有领域模块',
        '',
        f'自动生成于 {数据.get("导出时间", "?")}',
        f'基于光明积木库 v{数据.get("版本", "?")}',
        f'共 {统计.get("领域数", 0)} 个领域, {统计.get("总块数", 0)} 块积木',
        '',
        '用法:',
        '  from 积木库.工具代码 import 数据, 数学, 文本',
        '  数据.求和([1, 2, 3])',
        '"""',
        '',
    ]

    for 领域 in 领域顺序:
        lines.append(f'from . import {领域}')

    lines.extend([
        '',
        f'__all__ = {json.dumps(领域顺序, ensure_ascii=False, indent=2)}',
        '',
        '',
        'def 按名称查找(名称):',
        '    """在已加载的领域模块中查找指定名称的积木函数"""',
        '    import importlib',
        '    for 领域 in __all__:',
        '        模块 = importlib.import_module(f".{领域}", __package__)',
        '        if hasattr(模块, 名称):',
        '            return getattr(模块, 名称)',
        '    return None',
    ])

    init_path = os.path.join(_输出目录, '__init__.py')
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


# ══════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description='光明积木工具代码生成器')
    parser.add_argument('--limit', type=int, default=None,
                        help='最多生成的积木数（默认全部）')
    parser.add_argument('--domain', type=str, default=None,
                        help='限定生成的领域，用逗号分隔')
    parser.add_argument('--output', type=str, default=None,
                        help='积木库导出 JSON 路径')
    parser.add_argument('--verify', action='store_true',
                        help='生成后验证 Python 语法')
    args = parser.parse_args()

    目标领域 = args.domain.split(',') if args.domain else None
    生成_工具代码(
        导出路径=args.output,
        限制=args.limit,
        目标领域=目标领域,
        验证语法=args.verify,
    )


if __name__ == '__main__':
    main()