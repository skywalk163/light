# -*- coding: utf-8 -*-
"""光明积木工具代码 · 自动导入所有领域模块

自动生成于 2026-08-10
基于光明积木库 v0.2.0
共 26 个领域, 1037 块积木

用法:
  from 积木库.工具代码 import 数据, 数学, 文本
  数据.求和([1, 2, 3])
"""

from . import 中文
from . import 几何
from . import 函数
from . import 单位
from . import 密码
from . import 工具
from . import 数学
from . import 数据
from . import 数组
from . import 文件
from . import 文本
from . import 时间
from . import 格式
from . import 生成
from . import 类型
from . import 系统
from . import 统计
from . import 编码
from . import 网络
from . import 财务
from . import 迭代
from . import 逻辑
from . import 随机
from . import 集合
from . import 颜色
from . import 验证

__all__ = [
  "中文",
  "几何",
  "函数",
  "单位",
  "密码",
  "工具",
  "数学",
  "数据",
  "数组",
  "文件",
  "文本",
  "时间",
  "格式",
  "生成",
  "类型",
  "系统",
  "统计",
  "编码",
  "网络",
  "财务",
  "迭代",
  "逻辑",
  "随机",
  "集合",
  "颜色",
  "验证"
]


def 按名称查找(名称):
    """在已加载的领域模块中查找指定名称的积木函数"""
    import importlib
    for 领域 in __all__:
        模块 = importlib.import_module(f".{领域}", __package__)
        if hasattr(模块, 名称):
            return getattr(模块, 名称)
    return None
