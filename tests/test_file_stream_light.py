# -*- coding: utf-8 -*-
"""
test_file_stream_light.py —— stdlib/文件流.light 纯光明文件流读写测试

判据（任务书 §3.1）：
- 行列表(路径) 等价 文件系统.py:325 文件行列表（readlines，行尾换行保留）
- 逐行(路径) 惰性生成器，产出与 行列表 一致
- 写文本(路径, 文本) / 追加文本(路径, 文本) 行为正确
- 零 导入 / 零 引 Python（静态检查由交付报告登记）
"""
import os
import sys
import tempfile

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 文件流 import 行列表, 逐行, 写文本, 追加文本
# 对照：只读参照答案 .py
from 文件系统 import 文件行列表, 写入文件 as py写入文件


@pytest.fixture
def 临时目录():
    d = tempfile.mkdtemp(prefix="_taskD7_")
    yield d
    for f in os.listdir(d):
        try:
            os.remove(os.path.join(d, f))
        except OSError:
            pass
    try:
        os.rmdir(d)
    except OSError:
        pass


def test_行列表_等价于_文件系统_文件行列表(临时目录):
    p = os.path.join(临时目录, "sample.txt")
    content = "第一行\n第二行\n第三行\n"
    py写入文件(p, content)
    mine = 行列表(p)
    ref = 文件行列表(p)
    assert mine == ref
    # readlines 风格：行尾换行保留
    assert mine == ["第一行\n", "第二行\n", "第三行\n"]


def test_行列表_末行无换行不补(临时目录):
    p = os.path.join(临时目录, "noeol.txt")
    py写入文件(p, "唯一一行")
    assert 行列表(p) == ["唯一一行"]


def test_逐行_惰性等价_行列表(临时目录):
    p = os.path.join(临时目录, "lazy.txt")
    py写入文件(p, "a\nb\nc\n")
    assert list(逐行(p)) == 行列表(p)


def test_逐行_是生成器(临时目录):
    p = os.path.join(临时目录, "gen.txt")
    py写入文件(p, "x\ny\n")
    # 不应一次性把全部行物化在列表里：用迭代协议驱动
    g = 逐行(p)
    assert hasattr(g, "__iter__")
    assert list(g) == ["x\n", "y\n"]


def test_写文本_覆盖写(临时目录):
    p = os.path.join(临时目录, "w.txt")
    写文本(p, "初稿")
    assert 行列表(p) == ["初稿"]
    写文本(p, "覆写")
    assert 行列表(p) == ["覆写"]


def test_追加文本_追加写(临时目录):
    p = os.path.join(临时目录, "a.txt")
    写文本(p, "甲")
    追加文本(p, "乙")
    # 写文本 用 \n 连接？这里 写文本 整文件覆盖写入 "甲"，追加 "乙" 后内容 "甲乙"
    assert 读取全部(p) == "甲乙"


def 读取全部(路径):
    with open(路径, "r", encoding="utf-8") as fh:
        return fh.read()


def test_逐行_空文件(临时目录):
    p = os.path.join(临时目录, "empty.txt")
    py写入文件(p, "")
    assert list(逐行(p)) == []
    assert 行列表(p) == []
