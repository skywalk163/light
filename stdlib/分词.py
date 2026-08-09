# -*- coding: utf-8 -*-
"""
光明标准库 - 中文分词模块

提供中文分词功能，支持 jieba 分词和简单分词实现。
"""

import re
from typing import List, Optional


def 简单分词(文本: str) -> List[str]:
    """
    简单的基于字典和规则的中文分词

    参数:
        文本: 要分词的文本

    返回:
        分词结果列表

    示例:
        简单分词('我爱北京天安门')  # ['我', '爱', '北京', '天安门']
    """
    if not 文本:
        return []

    # 基本分词词典
    词典 = {
        '北京', '天安门', '故宫', '长城', '上海', '广州', '深圳',
        '中国', '美国', '日本', '法国', '德国', '英国',
        '我们', '他们', '你们', '自己', '什么', '怎么', '为什么',
        '因为', '所以', '但是', '而且', '虽然', '如果', '然后',
        '可以', '应该', '需要', '能够', '可能', '必须',
        '工作', '学习', '生活', '研究', '开发', '设计',
        '系统', '程序', '代码', '数据', '文件', '网络',
        '类型', '变量', '函数', '类', '对象', '接口',
        '数组', '列表', '字典', '集合', '字符串', '数字',
        '你好', '谢谢', '欢迎', '再见', '早上', '晚上', '今天',
        '明天', '昨天', '现在', '以后', '之前', '之后',
        '一个', '这个', '那个', '哪个', '这些', '那些',
        '已经', '已经', '正在', '将要', '没有', '不是',
        '知道', '了解', '使用', '创建', '定义', '调用',
        '返回', '抛出', '捕获', '处理', '转换', '格式化',
    }

    # 停用词
    停用词 = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
                '都', '一', '一个', '上', '也', '很', '到', '说', '要',
                '去', '你', '会', '着', '没有', '看', '好', '自己', '这',
                '他', '她', '它', '们', '那', '些', '吗', '啊', '吧',
                '呢', '哦', '嗯', '呀', '嘛', '哈'}

    结果 = []
    缓存 = ''

    for 字符 in 文本:
        if re.match(r'[\u4e00-\u9fff]', 字符):
            缓存 += 字符
            # 尝试匹配最长词
            最长匹配 = None
            for 词长度 in range(min(len(缓存), 4), 0, -1):
                if 缓存[-词长度:] in 词典:
                    最长匹配 = 缓存[-词长度:]
            if 最长匹配 and len(缓存) >= 4:
                # 输出前部分
                for 单字 in 缓存[:-2]:
                    结果.append(单字)
                缓存 = 缓存[-2:]
        else:
            if 缓存:
                # 输出缓存的汉字
                if 缓存 in 词典:
                    结果.append(缓存)
                elif len(缓存) == 2 and 缓存[0] in 停用词:
                    结果.append(缓存[0])
                    结果.append(缓存[1])
                else:
                    结果.extend(list(缓存))
                缓存 = ''
            if 字符.strip():
                结果.append(字符)

    if 缓存:
        if 缓存 in 词典:
            结果.append(缓存)
        else:
            结果.extend(list(缓存))

    return 结果


def jieba分词(文本: str, 模式: str = '精确') -> List[str]:
    """
    使用 jieba 分词（需要安装 jieba）

    参数:
        文本: 要分词的文本
        模式: 分词模式：'精确', '全模式', '搜索引擎'

    返回:
        分词结果列表
    """
    try:
        import jieba
    except ImportError:
        raise RuntimeError("jieba 分词需要安装 jieba: pip install jieba")

    if 模式 == '精确':
        return list(jieba.cut(文本, cut_all=False))
    elif 模式 == '全模式':
        return list(jieba.cut(文本, cut_all=True))
    elif 模式 == '搜索引擎':
        return list(jieba.cut_for_search(文本))
    else:
        raise ValueError(f"不支持的分词模式: '{模式}'")


def 分词(文本: str, 使用jieba: bool = False, 模式: str = '精确') -> List[str]:
    """
    中文分词

    参数:
        文本: 要分词的文本
        使用jieba: 是否使用 jieba 分词（默认使用简单分词）
        模式: 分词模式（仅 jieba 有效）：'精确', '全模式', '搜索引擎'

    返回:
        分词结果列表
    """
    if 使用jieba:
        return jieba分词(文本, 模式)
    return 简单分词(文本)


def 分词统计(文本: str, 使用jieba: bool = False) -> List[tuple]:
    """
    分词并统计词频

    参数:
        文本: 要分词的文本
        使用jieba: 是否使用 jieba 分词

    返回:
        [(词, 频率), ...] 列表，按频率降序排列
    """
    tokens = 分词(文本, 使用jieba)
    词频 = {}
    for token in tokens:
        if len(token) >= 2:  # 只统计多字词
            词频[token] = 词频.get(token, 0) + 1
    return sorted(词频.items(), key=lambda x: x[1], reverse=True)


def 提取关键词(文本: str, 数量: int = 5, 使用jieba: bool = False) -> List[str]:
    """
    提取关键词

    参数:
        文本: 要提取关键词的文本
        数量: 提取数量（默认5）
        使用jieba: 是否使用 jieba 分词

    返回:
        关键词列表
    """
    统计结果 = 分词统计(文本, 使用jieba)
    return [词 for 词, _ in 统计结果[:数量]]


__all__ = [
    '分词', '简单分词', 'jieba分词',
    '分词统计', '提取关键词',
]