#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明 v3.x → v4.0dev 语法转换器

将 v3.x 语法的 .light 文件自动转换为 4.0dev 格式。

用法:
    python tools/v3_to_v4.py 文件.light              # 转换单个文件
    python tools/v3_to_v4.py 文件.light -o 输出.light  # 指定输出文件
    python tools/v3_to_v4.py 目录/                   # 递归转换目录下所有 .light 文件
    python tools/v3_to_v4.py 目录/ --in-place        # 原地替换

v3.x → 4.0dev 主要映射:
    函数 → 段
    如果 → 若
    否则如果 → 否则若
    否则 → 否
    返回 → 返
    令 → 设
    设 变量 为 值 → 设 变量 = 值
    加/减/乘/除/取模 → + - * / %
    等于/不等于/大于/小于/大于等于/小于等于 → == != > < >= <=
    列表长度 → 长度
    【】 → []
    ， → ,
    ： → :
    // 注释 → # 注释
    外部 段落 ... 。 → 外部 段落 ...
"""

import re
import os
import sys


# ============================================================
# 替换规则表
# ============================================================

# 简单关键字替换（整词替换，不涉及上下文）
_KEYWORD_REPLACEMENTS = [
    # 注意：多字词要排在单字词前面，避免部分匹配
    ('否则如果', '否则若'),
    ('大于等于', '>='),
    ('小于等于', '<='),
    ('不等于', '!='),
    ('列表长度', '长度'),
    ('函数', '段'),
    ('如果', '若'),
    ('否则', '否'),
    ('返回', '返'),
    ('令', '设'),
    ('取模', '%'),
    ('大于', '>'),
    ('小于', '<'),
    ('等于', '=='),
]

# 对 v3.x 的 `加`/`减`/`乘`/`除` 运算符的替换
# 注意：这些单字可能出现在复合词中，需通过上下文判断
# 策略：仅在前后有空格/标点/边界时替换
_ARITH_OPERATORS = {
    '加': '+',
    '减': '-',
    '乘': '*',
    '除': '/',
}

# 已知包含"加/减/乘/除"的复合词（不应被替换为运算符）
_ARITH_COMPOUND_BIGRAMS = frozenset({
    '添加', '追加', '更加', '加载', '加密', '加速', '加锁', '加害',
    '增加', '参加', '附加', '加上', '加粗', '加长',
    '减少', '减弱', '减速', '减量', '减震', '减轻', '减去',
    '乘法', '乘数', '乘方', '乘客', '乘以', '乘除',
    '除法', '除数', '除外', '除以', '删除', '去除',
    '加法', '减法', '乘法', '除法算式', '数乘', '点乘', '二乘', '阶乘',
    '加减', '乘除', '加减乘除',
})

# v3.x 逻辑运算符（v3.x 使用 Python 风格 and/or/not，4.0dev 使用 L0 核心字 且/或/非）
_LOGIC_OPERATORS = {
    'and': '且',
    'or': '或',
    'not': '非',
}


def _is_han(ch: str) -> bool:
    """判断是否为汉字"""
    return '\u4e00' <= ch <= '\u9fff' or '\u3400' <= ch <= '\u4dbf'


def _is_boundary_char(ch: str) -> bool:
    """判断是否为分词边界字符（非汉字、非字母数字）"""
    if not ch:
        return True
    return not (_is_han(ch) or ch.isalnum() or ch == '_')


def _replace_arithmetic_operators(text: str) -> str:
    """替换算术运算符：加/减/乘/除 → + - * /
    
    策略：
    - 运算符前是强边界（)]}'\" 数字）→ 总是替换（如"]减求和" → "] - 求和"）
    - 运算符前是普通边界（空格、行首）且 后字符不是汉字 → 替换（如"值 加 1"）
    - 运算符前是普通边界（空格）且 后字符是汉字 → 复合词开头（如"除数"）→ 不替换
    - 运算符前是汉字，后字符不是汉字 → 替换（如"限加i"、"果加2"、"长除3"）
    - 运算符前后都是汉字，且不是已知复合词 → 替换（如"结果乘步长"）
    """
    result = list(text)
    i = 0
    while i < len(result):
        ch = result[i]
        if ch in _ARITH_OPERATORS and i + 1 < len(result) and result[i + 1] in _ARITH_OPERATORS:
            i += 1
            continue
        if ch in _ARITH_OPERATORS:
            prev_char = result[i - 1] if i > 0 else ''
            next_char = result[i + 1] if i + 1 < len(result) else ''
            prev_is_boundary = _is_boundary_char(prev_char)
            next_is_han = bool(next_char) and _is_han(next_char)
            prev_is_han = bool(prev_char) and _is_han(prev_char)
            # 前是数字 → 总是替换（如"6乘步长"、"2乘k2"、"3加5"）
            if prev_char.isdigit():
                result[i] = _ARITH_OPERATORS[ch]
            # 强边界（括号、方括号、引号等明确表达式结束符）→ 总是替换
            elif prev_char in ')]}"\'':
                result[i] = _ARITH_OPERATORS[ch]
            # 前是边界（空格、行首）且 后不是汉字 → 替换（如"值 加 1"）
            elif prev_is_boundary and not next_is_han:
                result[i] = _ARITH_OPERATORS[ch]
            # 前是数字或字母（非汉字），后不是汉字 → 替换（如"x加y"）
            elif prev_char and not _is_han(prev_char) and prev_char.isalnum() and not next_is_han:
                result[i] = _ARITH_OPERATORS[ch]
            # 前是汉字，后不是汉字 → 替换（如"限加i"、"果加2"、"结果加(...)"）
            # 但如果是已知复合词的一部分（如"数乘("、"阶乘("），不替换
            elif prev_is_han and next_char and not next_is_han:
                bigram = prev_char + ch
                if bigram not in _ARITH_COMPOUND_BIGRAMS:
                    result[i] = _ARITH_OPERATORS[ch]
            # 前后都是汉字 → 检查是否为已知复合词
            elif prev_is_han and next_is_han:
                trigram = prev_char + ch + next_char
                # 检查 trigram 是否包含已知复合词
                if (prev_char + ch) not in _ARITH_COMPOUND_BIGRAMS and \
                   (ch + next_char) not in _ARITH_COMPOUND_BIGRAMS:
                    result[i] = _ARITH_OPERATORS[ch]
        i += 1
    return ''.join(result)


def _convert_string_plus_call(text: str) -> str:
    """转换 "字符串"加函数名(...) → "字符串" + 函数名(...)
    
    在v3中，加/减/乘/除作为运算符时通常前后有空格，
    但某些情况下（如字符串拼接后直接跟函数调用）可能没有空格。
    此函数专门处理这种无空格但运算符明确的情况。
    """
    for op in ['加', '减', '乘', '除']:
        target = '+' if op == '加' else ('-' if op == '减' else ('*' if op == '乘' else '/'))
        # 在引号后的运算符，后面跟标识符（可能含中文）
        text = re.sub(
            r'(["\'])' + re.escape(op) + r'([\w\u4e00-\u9fff]+)',
            lambda m: m.group(1) + ' ' + target + ' ' + m.group(2),
            text
        )
        # 在数字后的运算符（如 3加5 → 3 + 5）
        text = re.sub(
            r'(\d)' + re.escape(op) + r'(\d)',
            lambda m: m.group(1) + ' ' + target + ' ' + m.group(2),
            text
        )
    return text


def _replace_logic_operators(text: str) -> str:
    """替换逻辑运算符：and/or/not → 且/或/非"""
    # 按关键字长度降序排序，避免部分匹配
    operators = sorted(_LOGIC_OPERATORS.keys(), key=len, reverse=True)
    result = []
    i = 0
    while i < len(text):
        matched = False
        for op in operators:
            if text[i:i+len(op)] == op:
                # 检查前后边界
                prev_ok = (i == 0) or _is_boundary_char(text[i-1])
                next_pos = i + len(op)
                next_ok = (next_pos >= len(text)) or _is_boundary_char(text[next_pos])
                if prev_ok and next_ok:
                    result.append(_LOGIC_OPERATORS[op])
                    i += len(op)
                    matched = True
                    break
        if not matched:
            result.append(text[i])
            i += 1
    return ''.join(result)


def _replace_keywords(text: str) -> str:
    """替换关键字（整词匹配，不破坏复合词）"""
    for old, new in _KEYWORD_REPLACEMENTS:
        if all(ord(c) < 128 for c in old):
            # ASCII 关键字：使用标准正则
            text = re.sub(r'\b' + re.escape(old) + r'\b', new, text)
        else:
            # 中文关键字：手写替换，检查前后边界
            result = []
            i = 0
            while i < len(text):
                if text[i:i+len(old)] == old:
                    # 检查前边界
                    prev_ok = (i == 0) or _is_boundary_char(text[i-1])
                    # 检查后边界（数字也算边界，如"小于0"中的"0"）
                    next_pos = i + len(old)
                    next_char = text[next_pos] if next_pos < len(text) else ''
                    next_ok = (next_pos >= len(text)) or _is_boundary_char(next_char) or next_char == '_' or next_char.isdigit()
                    if prev_ok and next_ok:
                        result.append(new)
                        i += len(old)
                        continue
                result.append(text[i])
                i += 1
            text = ''.join(result)
    return text


def _replace_assignment(text: str) -> str:
    """替换 设 变量 为 值 → 设 变量 = 值
    
    只在"设"语句中替换"为"为"="。
    """
    result = []
    i = 0
    while i < len(text):
        # 检测 "设 " 开头
        if text[i:i+2] == '设 ' or text[i:i+2] == '设\t':
            # 找到 "设" 后面的第一个空白开始的变量名
            j = i + 1
            # 跳过空白
            while j < len(text) and text[j] in ' \t':
                j += 1
            # 收集变量名（非空白字符）
            while j < len(text) and text[j] not in ' \t\n':
                j += 1
            # 跳过空白，查找 "为" 或 "等于"
            k = j
            while k < len(text) and text[k] in ' \t':
                k += 1
            if text[k:k+1] == '为' and (k+1 >= len(text) or text[k+1] in ' \t\n'):
                # 替换 "为" 为 " ="
                result.append(text[i:k].rstrip(' \t'))
                result.append(' = ')
                i = k + 1
                continue
            elif text[k:k+2] == '等于' and (k+2 >= len(text) or text[k+2] in ' \t\n'):
                # 替换 "等于" 为 " ="
                result.append(text[i:k].rstrip(' \t'))
                result.append(' = ')
                i = k + 2
                continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def _replace_wei_as_assign(text: str) -> str:
    """将非设语句中的 为 → =（赋值运算符）
    
    例如：byte1 为 128 → byte1 = 128
    注意：不转换从...为...导入中的"为"。
    """
    result = []
    i = 0
    n = len(text)
    while i < n:
        # 检测从...为...导入模式，跳过其中的"为"
        if i + 1 < n and text[i] == '从' and _is_boundary_char(text[i-1]) if i > 0 else True:
            j = i + 1
            while j < n and text[j] not in '\n':
                if text[j:j+1] == '为' and _is_boundary_char(text[j-1]) and (j+1 >= n or _is_boundary_char(text[j+1])):
                    # 这是从...为...中的"为"，跳过整行
                    result.append(text[i:j+1])
                    i = j + 1
                    break
                j += 1
            else:
                # 没找到"为"，回退到正常处理
                result.append(text[i])
                i += 1
            continue
        
        if text[i] == '为':
            prev_ok = (i == 0) or _is_boundary_char(text[i-1])
            next_ok = (i + 1 >= n) or _is_boundary_char(text[i+1])
            if prev_ok and next_ok:
                result.append('=')
                i += 1
                continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def _replace_external_declaration(text: str) -> str:
    """替换外部声明：移除末尾的句号"""
    # 外部 段落/结构体 ... 。
    text = re.sub(
        r'(外部\s+(?:段落|结构体|函数|变量)\s+[^。\n]+)。',
        r'\1',
        text
    )
    return text


def _convert_comments(text: str) -> str:
    """转换注释：// → # （注意跳过字符串中的 //）"""
    result = []
    in_string = False
    string_char = None
    i = 0
    while i < len(text):
        ch = text[i]
        
        # 处理字符串
        if not in_string and ch in '"\'':
            # 检查是否是 f-string
            if i > 0 and text[i-1] == 'f':
                pass  # f-string 的开始
            in_string = True
            string_char = ch
            result.append(ch)
            i += 1
            continue
        elif in_string and ch == '\\':
            result.append(ch)
            i += 1
            if i < len(text):
                result.append(text[i])
                i += 1
            continue
        elif in_string and ch == string_char:
            in_string = False
            string_char = None
            result.append(ch)
            i += 1
            continue
        
        if not in_string:
            # 处理 // 注释
            if i + 1 < len(text) and text[i:i+2] == '//':
                result.append('#')
                i += 2
                # 复制注释剩余内容
                while i < len(text) and text[i] != '\n':
                    result.append(text[i])
                    i += 1
                continue
        
        result.append(ch)
        i += 1
    
    return ''.join(result)


def _convert_chinese_punctuation(text: str) -> str:
    """转换中文标点（注意不在字符串内转换）"""
    result = []
    in_string = False
    string_char = None
    i = 0
    while i < len(text):
        ch = text[i]
        
        # 处理字符串
        if not in_string and ch in '"\'':
            in_string = True
            string_char = ch
            result.append(ch)
            i += 1
            continue
        elif in_string and ch == '\\':
            result.append(ch)
            i += 1
            if i < len(text):
                result.append(text[i])
                i += 1
            continue
        elif in_string and ch == string_char:
            in_string = False
            string_char = None
            result.append(ch)
            i += 1
            continue
        
        if not in_string:
            if ch == '【':
                result.append('[')
            elif ch == '】':
                result.append(']')
            elif ch == '，':
                result.append(',')
            elif ch == '：':
                result.append(':')
            elif ch == '；':
                result.append(';')
            elif ch == '（':
                result.append('(')
            elif ch == '）':
                result.append(')')
            elif ch == '「':
                result.append('"')
            elif ch == '」':
                result.append('"')
            else:
                result.append(ch)
        else:
            result.append(ch)
        i += 1
    
    return ''.join(result)


def _convert_ffi_struct(text: str) -> str:
    """转换外部结构体声明：去除字段类型中的冒号"""
    # 外部 结构体 Name { 年: 任意, 月: 任意 } → 外部 结构体 Name { 年 任意, 月 任意 }
    text = re.sub(
        r'(外部\s+结构体\s+\w+\s*\{)([^}]+)(\})',
        lambda m: m.group(1) + re.sub(r'(\w+)\s*:\s*(\w+)', r'\1 \2', m.group(2)) + m.group(3),
        text
    )
    return text


def _convert_while_loop(text: str) -> str:
    """转换 while 循环中的中文冒号"""
    # 当 条件 且 条件： → 当 条件 and 条件:
    # 这主要是替换中文冒号，前面已经处理了
    return text


def _convert_remove_dict_key(text: str) -> str:
    """转换 删除字典键 dict key → 字典删除(dict, key)
    
    删除字典键 是 v3.x 的内置函数，4.0dev 使用 字典删除(dict, key)。
    """
    text = re.sub(
        r'删除字典键\s+(\S+)\s+(\S+)',
        r'字典删除(\1, \2)',
        text
    )
    return text


def _convert_percent_call(text: str) -> str:
    """转换 %(a, b) → a % b（函数调用式取模转为中缀运算符）
    
    支持嵌套括号：%(长度(排序列表),2) → 长度(排序列表) % 2
    """
    result = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '%' and i + 1 < n and text[i + 1] == '(':
            # 找到匹配的右括号
            depth = 1
            j = i + 2
            while j < n and depth > 0:
                if text[j] == '(':
                    depth += 1
                elif text[j] == ')':
                    depth -= 1
                j += 1
            # j 指向匹配的 ')' 之后
            inner = text[i+2:j-1]
            # 在顶层逗号处分割（不分割嵌套括号内的逗号）
            parts = []
            part_start = 0
            part_depth = 0
            for k, ch in enumerate(inner):
                if ch == '(':
                    part_depth += 1
                elif ch == ')':
                    part_depth -= 1
                elif ch == ',' and part_depth == 0:
                    parts.append(inner[part_start:k].strip())
                    part_start = k + 1
            parts.append(inner[part_start:].strip())
            if len(parts) == 2:
                result.append(f"{parts[0]} % {parts[1]}")
                i = j
                continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def _convert_is_keyword(text: str) -> str:
    """转换 是 → ==（当 是 作为类型判断运算符使用时）
    
    例如：若 值 是 整数: → 若 值 == 整数:
    注意：但凡是复合词中的 是（如"但是"、"还是"）不受影响。
    """
    result = []
    i = 0
    while i < len(text):
        if text[i] == '是':
            # 检查前后是否都是边界字符（空格、标点等）
            prev_ok = (i == 0) or _is_boundary_char(text[i-1])
            next_ok = (i + 1 >= len(text)) or _is_boundary_char(text[i+1])
            if prev_ok and next_ok:
                result.append('==')
                i += 1
                continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def _remove_struct_commas(text: str) -> str:
    """移除结构体定义中的逗号
    
    外部 结构体 Name { 字段1 类型, 字段2 类型 } → 外部 结构体 Name { 字段1 类型 字段2 类型 }
    """
    def _replace_commas(m):
        prefix = m.group(1)
        body = m.group(2)
        # 移除逗号（保留空格）
        body = re.sub(r'\s*,\s*', ' ', body)
        return prefix + body + '}'
    text = re.sub(r'(外部\s+结构体\s+\w+\s*\{)([^}]+)(\})', _replace_commas, text)
    return text


def convert_v3_to_v4(source: str) -> str:
    """将 v3.x 源码转换为 4.0dev 格式"""
    # 1. 先转换注释（避免后续处理破坏注释中的内容）
    source = _convert_comments(source)
    
    # 2. 转换中文标点
    source = _convert_chinese_punctuation(source)
    
    # 3. 替换关键字（整词匹配）——大于_等标识符也会正确处理
    source = _replace_keywords(source)
    
    # 3b. 预转换字符串拼接中的运算符（如"xxx"加函数名 → "xxx" + 函数名）
    source = _convert_string_plus_call(source)
    
    # 4. 替换算术运算符
    source = _replace_arithmetic_operators(source)
    
    # 5. 替换逻辑运算符
    source = _replace_logic_operators(source)
    
    # 6. 替换赋值语句
    source = _replace_assignment(source)
    
    # 6b. 替换非设语句中的 为 → =
    source = _replace_wei_as_assign(source)
    
    # 7. 转换 是 → ==（类型判断运算符）
    source = _convert_is_keyword(source)
    
    # 8. 转换 %(a, b) → a % b
    source = _convert_percent_call(source)
    
    # 8b. 转换 删除字典键 dict key → 字典删除(dict, key)
    source = _convert_remove_dict_key(source)
    
    # 9. 移除结构体定义中的逗号
    source = _remove_struct_commas(source)
    
    # 10. 转换外部声明
    source = _replace_external_declaration(source)
    
    # 11. 转换外部结构体
    source = _convert_ffi_struct(source)
    
    # 12. 清理多余的空行
    source = re.sub(r'\n{3,}', '\n\n', source)
    
    return source


def convert_file(input_path: str, output_path: str = None, in_place: bool = False):
    """转换单个文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    converted = convert_v3_to_v4(source)
    
    if in_place:
        output_path = input_path
    elif output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = base + '.v4' + ext
    
    with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(converted)
    
    print(f"  ✓ {input_path} → {output_path}")


def convert_directory(dir_path: str, in_place: bool = False, overwrite_v4: bool = False):
    """递归转换目录下所有 .light 文件
    
    Args:
        dir_path: 目录路径
        in_place: 原地替换原文件
        overwrite_v4: 覆盖已存在的 .v4.light 输出文件
    """
    for root, dirs, files in os.walk(dir_path):
        for f in sorted(files):
            if not f.endswith('.light'):
                continue
            # 跳过 _cstyle 文件（不同的语法变体，使用 @C 进行外部声明）
            if f.endswith('_cstyle.light'):
                continue
            # 跳过已转换的 .v4.light 文件（只处理原始 .light 文件）
            if f.endswith('.v4.light'):
                continue
            input_path = os.path.join(root, f)
            if in_place:
                convert_file(input_path, in_place=True)
            else:
                output_path = os.path.join(root, f.replace('.light', '.v4.light'))
                # 如果输出文件已存在且不覆盖，则跳过
                if not overwrite_v4 and os.path.exists(output_path):
                    continue
                convert_file(input_path, output_path=output_path)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    target = sys.argv[1]
    in_place = '--in-place' in sys.argv or '-i' in sys.argv
    overwrite = '--overwrite' in sys.argv or '-w' in sys.argv
    
    # 检查是否有 -o 指定输出文件
    output_path = None
    if '-o' in sys.argv:
        idx = sys.argv.index('-o')
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]
    
    if os.path.isdir(target):
        print(f"转换目录: {target}")
        convert_directory(target, in_place, overwrite_v4=overwrite)
    elif os.path.isfile(target):
        print(f"转换文件: {target}")
        convert_file(target, output_path, in_place)
    else:
        print(f"错误: 找不到路径: {target}")
        sys.exit(1)
    
    print("完成!")


if __name__ == '__main__':
    main()