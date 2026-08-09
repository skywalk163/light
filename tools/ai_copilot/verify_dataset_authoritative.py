#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明数据集 v6 权威验证 — 基于 src/keywords.py 的完整关键字表

关键修正：
- 加/减/乘/除/模/幂 是合法运算符（单字形式）
- 加上/减去/乘以/除以/模以/幂以 是合法复合运算符（双字形式）
- 之/的/并/至/到/步/己/父 是合法保留字
- 首/末/余/长/列/排序/反转/求和/去重/筛选/映射 是合法动词
- 整除/次方/范围/步长/全局/非局部 不是光明关键字（之前修复脚本错误添加）
"""
import json
import re
import os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(SCRIPT_DIR, "sft_dataset.jsonl")

# ====== 从 src/keywords.py 导入完整关键字表 ======

# 双字关键字
KEYWORDS_DOUBLE = {
    '定义', '常量', '类型', '导入', '导出', '从', '为', '设', '开启', '关闭',
    '如果', '那么', '否则', '否则若', '若', '则',
    '遍历', '当', '跳出', '跳过', '在', '对', '中的', '于',
    '段落', '接收', '返回',
    '严格', '松散',
    '尝试', '捕获', '抛出', '最终',
    '类', '继承', '属性', '构造', '新建', '接口', '实现',
    '私属性', '私段落', '私有', '公有', '保护',
    '静态', '静态方法', '类方法', '特性',
    '模块', '标准库',
    '异步', '等待', '作用域',
    '匹配', '情况',
    '使用', '标注',
    '外部', '加载库', '结构体', '回调', '外部错误', '枚举', '联合体',
    '变长参数', '类型别名', '位域', '函数指针', '宏', '调试',
    '抽象',
}

# 单字保留字
KEYWORDS_RESERVED = {
    '且', '或', '非', '与',  # 逻辑运算
    '真', '假', '空',  # 特殊值
    '并', '之', '的', '己', '父', '至', '到', '步',  # 保留字
}

# 动词（VERB_ARITY 的所有 key）
VERBS = {
    '加', '减', '乘', '除', '取余', '模', '幂',
    '乘以', '除以', '加上', '减去', '模以', '幂以',
    '等于', '大于', '小于', '不等于', '大于等于', '小于等于',
    '首', '末', '余', '长', '列',
    '打印', '读取', '输出',
    '排序', '反转', '求和', '求最大', '求最小', '去重', '筛选', '映射',
    '新建',
    '匹配', '搜索', '全部匹配', '替换', '分割', '匹配迭代', '是否匹配', '转义',
    '添加', '删除',
    '读取文件', '写入文件', '追加文件', '文件存在', '目录存在', '路径存在',
    '创建目录', '删除文件', '删除目录', '列出目录',
    '绝对路径', '连接路径', '目录名', '文件名', '分割扩展名',
    '环境变量', '设置环境变量', '参数列表', '退出程序', '当前目录', '切换目录', '执行命令',
    '转整数', '转浮点', '转字符串', '字符串长度', '分割字符串', '连接字符串',
    '替换字符串', '去除空白', '字符串截取',
    '列表长度', '列表追加', '列表获取', '列表弹出', '列表排序', '列表反转',
    '列表包含', '列表创建',
    '字典创建', '字典设置', '字典删除', '字典获取', '字典键列表', '字典值列表', '字典项列表',
    '随机整数', '随机浮点', '随机选择', '圆周率', '自然常数',
    '角度转弧度', '弧度转角度',
    '是整数', '是浮点', '是字符串', '是列表', '是字典', '是空',
    '是字母', '是数字符', '是空白',
    '打印输出', '写入输出', '读取行', '读取N字节', '刷新输出', '打印错误', '写入错误',
    '解析JSON', '序列化JSON', '美化JSON',
    # stdlib 中广泛使用的复合词（not in / open / file ops）
    '不在', '打开', '打开文件', '读取文件',
    # 标准库中的常用动词/名词
    '包含', '断言包含', '断言相等', '断言不相等',
    '开头是', '结尾是', '去空格', '计数', '重复',
    '反转字符串', '连接', '查找索引',
    '最大值', '最小值', '平均值', '范围',
    '求最大', '求最小',
    '字典包含键', '枚举', '整数枚举',
    '从值获取', '包含值',
    # 异常相关
    '抛出断言失败异常',
    # 常用标准库名
    '打开数据库',
}

# 内置类型
BUILTIN_TYPES = {
    '数', '整数', '浮数', '小数', '串', '文本', '列', '列表',
    '典', '字典', '集', '集合', '布尔', '空', '任意',
}

# 所有合法光明关键字/动词/类型
ALL_LIGHT_WORDS = KEYWORDS_DOUBLE | KEYWORDS_RESERVED | VERBS | BUILTIN_TYPES

# Python内置函数/模块名（应保持英文）
PYTHON_BUILTINS = {
    'print', 'len', 'range', 'int', 'float', 'str', 'list', 'dict', 'set',
    'tuple', 'bool', 'abs', 'min', 'max', 'sum', 'sorted', 'reversed',
    'enumerate', 'zip', 'map', 'filter', 'open', 'input', 'type', 'isinstance',
    'append', 'extend', 'insert', 'remove', 'pop', 'index', 'count',
    'sort', 'reverse', 'copy', 'clear', 'keys', 'values', 'items',
    'get', 'update', 'split', 'join', 'replace', 'strip', 'upper', 'lower',
    'find', 'startswith', 'endswith', 'format', 'encode', 'decode',
    'isdigit', 'isalpha', 'isalnum', 'isspace',
    'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
    'ZeroDivisionError', 'AttributeError', 'StopIteration',
    'ArithmeticError', 'RuntimeError', 'ImportError', 'FileNotFoundError',
    'NotImplementedError', 'OverflowError', 'NameError', 'OSError',
    'super', 'self', 'cls', 'property', 'staticmethod', 'classmethod',
    'None', 'True', 'False',
    'os', 'sys', 'math', 'random', 'json', 're', 'time',
    'datetime', 'collections', 'itertools', 'functools',
    'Counter', 'deque', 'defaultdict', 'OrderedDict',
    'namedtuple', 'ChainMap',
    'reduce', 'partial', 'wraps', 'lru_cache',
    'ceil', 'floor', 'sqrt', 'pow', 'log', 'sin', 'cos', 'tan',
    'pi', 'e', 'inf', 'nan',
    'randint', 'choice', 'shuffle', 'sample',
    'loads', 'dumps', 'load', 'dump',
    'path', 'exists', 'mkdir', 'makedirs', 'listdir',
    'walk', 'getcwd', 'basename', 'dirname',
    'sleep', 'now', 'strftime', 'strptime',
    'match', 'search', 'findall', 'sub', 'compile',
    'round', 'divmod', 'frozenset', 'bin', 'hex', 'oct', 'chr', 'ord',
    'any', 'all', 'next', 'iter', 'slice',
    'deepcopy', 'copy',
    'pass', 'lambda', 'with', 'as', 'try', 'except', 'finally', 'raise',
    'for', 'while', 'break', 'continue', 'return', 'yield',
    'global', 'nonlocal', 'del', 'assert', 'import', 'from',
    'class', 'def', 'if', 'elif', 'else',
}


def find_non_light_chinese(text):
    """找到输出中所有非光明关键字的中文词组"""
    chinese_seqs = re.findall(r'[\u4e00-\u9fff]+', text)
    non_light = [seq for seq in chinese_seqs if seq not in ALL_LIGHT_WORDS]
    return non_light


def verify_dataset():
    data = []
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    
    print(f"[读取] {len(data)} 条样本")
    print(f"光明关键字/动词/类型总数: {len(ALL_LIGHT_WORDS)} 个\n")
    
    all_chinese = defaultdict(list)
    issue_counts = defaultdict(int)
    
    for i, item in enumerate(data):
        output = item.get('output', '')
        py_code = item.get('input', '')
        
        # 找非光明中文
        non_light = find_non_light_chinese(output)
        for ch in non_light:
            all_chinese[ch].append(i)
        
        # 检查具体问题
        if 'self_' in output:
            issue_counts['self_prefix'] += 1
        # range() 是 Python 内置函数，光明保留 — 不再视为问题
        # ** 只在算术运算上下文中是问题（排除 **kwargs 字典解包）
        if '**' in output:
            lines_with_power = []
            for l in output.split('\n'):
                if '**' in l and 'f"' not in l and "f'" not in l:
                    # 排除 **kwargs, **dict 等字典解包模式
                    # 排除 **kwargs, **dict 等字典解包模式
                    if not re.search(r'\*\*[\w]+(?=[\s,)\]}：])', l):
                        # 排除字符串字面量中的 **, 如 '**'
                        if not re.search(r"['\"]\*\*['\"]", l):
                            lines_with_power.append(l)
            if lines_with_power:
                issue_counts['power_kept'] += 1
        # range() 是 Python 内置函数，光明保留 — 不再视为问题
        # 检查是否有错误的"关键字"（整除/次方/范围/步长/全局/非局部）
        for wrong_kw in ['整除', '次方', '范围', '步长', '全局', '非局部']:
            if wrong_kw in output:
                issue_counts[f'wrong_kw_{wrong_kw}'] += 1
    
    samples_with_chinese = set()
    for ch, indices in all_chinese.items():
        for idx in indices:
            samples_with_chinese.add(idx)
    
    print(f"{'='*60}")
    print(f"权威验证报告 (基于 src/keywords.py)")
    print(f"{'='*60}")
    print(f"总样本数: {len(data)}")
    print(f"\n具体问题:")
    for k, v in sorted(issue_counts.items()):
        print(f"  {k}: {v}")
    
    print(f"\n输出中非光明中文: {len(all_chinese)} 个不同词")
    print(f"含非光明中文的样本: {len(samples_with_chinese)} 条")
    print(f"干净样本: {len(data) - len(samples_with_chinese)} 条")
    print(f"干净率: {(len(data) - len(samples_with_chinese)) / len(data) * 100:.1f}%")
    
    sorted_chinese = sorted(all_chinese.items(), key=lambda x: -len(x[1]))
    print(f"\n前30个高频非光明中文:")
    for ch, indices in sorted_chinese[:30]:
        print(f"  '{ch}': {len(indices)} 条")
    
    # 显示有问题的样本
    if samples_with_chinese:
        print(f"\n--- 仍有问题的样本示例 ---")
        shown = 0
        for ch, indices in sorted_chinese:
            if shown >= 10:
                break
            idx = indices[0]
            print(f"\n[{idx}] 非光明中文: '{ch}'")
            print(f"  Python: {data[idx]['input'][:120]}")
            print(f"  输出: {data[idx]['output'][:200]}")
            shown += 1
    
    # 检查错误关键字
    print(f"\n--- 错误关键字检查 ---")
    wrong_keywords = ['整除', '次方', '范围', '步长', '全局', '非局部']
    for wk in wrong_keywords:
        count = sum(1 for item in data if wk in item.get('output', ''))
        if count > 0:
            print(f"  '{wk}' 出现在 {count} 条样本中 (需要修复)")
        else:
            print(f"  '{wk}': 0 ✅")


if __name__ == '__main__':
    verify_dataset()
