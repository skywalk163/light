#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lightpub 包「可导入性」判定 —— 单一事实来源。

为什么要有这个模块：
    docs/lightpub/*.md 是 tools/gen_lightpub_docs.py 生成的，每篇都有两个
    「导入方式」代码块（`导入 X` 和 `导入 标准X`）。这些块过去无条件用光明
    语言围栏标注，等于向读者承诺「这样写就能用」。实测 218 个块里只有一小部分
    真能跑通，其余全是谎话——文档示例扫描面只验证「能否编译」，编译得过、
    运行才炸的块它一个都抓不到。

单点原则：
    判据**不复刻**代码生成器的映射规则，而是直接调用真正的代码生成器编译
    `导入 X`，把它实际吐出的 `import ...` 行抠出来，再看那个 Python 模块
    在不在。复刻一份 P0/P1/P2 分支逻辑迟早会和 src/code_generator.py 漂移；
    这里让漂移在物理上不可能发生。

用法：
    from lightpub_importability import 判定
    v = 判定('导入 YAML')
    v.可用      # True/False
    v.原因      # 'OK' / 'LEX' / 'NO_MODULE' / 'IMPORT_ERR' / 'COMPILE_ERR'
    v.模块名    # 生成器实际写出的 Python 模块名，失败时可能为 None
    v.说明      # 面向读者的一句话，直接写进文档
"""

import os
import io
import sys
import importlib
import importlib.util

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_THIS_DIR)

for _p in (os.path.join(_PROJECT_DIR, 'src'),
           os.path.join(_PROJECT_DIR, 'stdlib'),
           _PROJECT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


class 判定结果:
    __slots__ = ('语句', '可用', '原因', '模块名', '说明')

    def __init__(self, 语句, 可用, 原因, 模块名, 说明):
        self.语句 = 语句
        self.可用 = 可用
        self.原因 = 原因
        self.模块名 = 模块名
        self.说明 = 说明

    def __repr__(self):
        return '判定结果(%r, 可用=%r, 原因=%r, 模块名=%r)' % (
            self.语句, self.可用, self.原因, self.模块名)


_基线行 = None
_生成器类 = None
_解析器类 = None


def _准备():
    global _基线行, _生成器类, _解析器类
    if _基线行 is not None:
        return
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator
    _解析器类 = LightParser
    _生成器类 = PythonCodeGenerator
    # 空程序也会带一堆前言 import（ctypes / typing / math / random …）。
    # 用「有导入语句」减「空程序」的行集合差，精确抠出导入语句自己那一行，
    # 不靠「取最后一个 import」这种会随前言变动而失效的启发式。
    _基线行 = frozenset(_生成代码('\n').splitlines())


def _生成代码(源码):
    _静默 = io.StringIO()
    _o, _e = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _静默, _静默
    try:
        return _生成器类().generate(_解析器类().parse(源码))
    finally:
        sys.stdout, sys.stderr = _o, _e


def 抠出导入行(语句):
    """编译一条光明导入语句，返回生成器实际写出的 Python 模块名。

    Returns: (模块名 or None, 错误信息 or None)
    """
    _准备()
    try:
        代码 = _生成代码(语句 + '\n')
    except BaseException as e:      # 词法/语法错误都在这里
        return None, '%s: %s' % (type(e).__name__, e)

    新增 = [l for l in 代码.splitlines() if l not in _基线行]
    for l in 新增:
        s = l.strip()
        if not s.startswith('import ') and not s.startswith('from '):
            continue
        s = s[len('import '):] if s.startswith('import ') else s[len('from '):]
        # `import A.B as C` / `from A import x` → 取模块名部分
        模块名 = s.split(' as ')[0].split(' import ')[0].strip()
        if 模块名:
            return 模块名, None
    return None, '生成的代码里找不到 import 行：%r' % 新增


def _压成一行(文本, 上限=160):
    """把编译器的多行报错（带 ┌│└ 画框）压成一行，好写进 Markdown 表述里。"""
    净 = []
    for ch in str(文本):
        if ch in '\r\n\t':
            净.append(' ')
        elif ch in '┌│└├─┐┘':
            净.append(' ')
        else:
            净.append(ch)
    s = ' '.join(''.join(净).split())
    return s if len(s) <= 上限 else s[:上限 - 1] + '…'


def 判定(语句, 真导入=True):
    """判定一条光明导入语句在本仓库里到底能不能用。

    真导入=True  时会真的 import 一遍（能抓到「文件在但一 import 就炸」）。
    真导入=False 时只查模块是否存在（快，但抓不到 import 期异常）。
    """
    模块名, 错误 = 抠出导入行(语句)
    if 模块名 is None:
        return 判定结果(语句, False, 'COMPILE_ERR', None,
                        '本仓库编译不过：%s' % _压成一行(错误))

    try:
        规格 = importlib.util.find_spec(模块名)
    except (ImportError, ValueError, AttributeError, TypeError) as e:
        return 判定结果(语句, False, 'NO_MODULE', 模块名,
                        '本仓库未提供实现（查 %s 时出错：%s）' % (模块名, e))
    if 规格 is None:
        return 判定结果(语句, False, 'NO_MODULE', 模块名,
                        '本仓库未提供实现（缺 %s）' % 模块名)

    if not 真导入:
        return 判定结果(语句, True, 'OK', 模块名, '')

    try:
        importlib.import_module(模块名)
    except BaseException as e:
        return 判定结果(语句, False, 'IMPORT_ERR', 模块名,
                        '实现存在但导入即报错：%s: %s' % (type(e).__name__, e))
    return 判定结果(语句, True, 'OK', 模块名, '')


def 判定包(包名, 真导入=True):
    """返回 (裸名判定, 标准名判定)，对应文档里那两个导入块。"""
    return 判定('导入 %s' % 包名, 真导入), 判定('导入 标准%s' % 包名, 真导入)
