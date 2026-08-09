# -*- coding: utf-8 -*-
"""
光明标准库 - 进度条模块

提供命令行进度条显示功能，支持自定义样式、嵌套进度条等。
"""

import sys
import time
import math
from typing import Optional, TextIO


class 进度条:
    """
    命令行进度条

    用法:
        with 进度条(总数=100, 描述='处理中') as pb:
            for i in range(100):
                # 执行任务
                pb.更新(1)
    """

    def __init__(self, 总数: int = 100, 描述: str = '',
                 宽度: int = 30, 填充字符: str = '█',
                 空白字符: str = '░', 前缀: str = '',
                 后缀: str = '', 输出流: TextIO = sys.stderr):
        self._总数 = 总数
        self._描述 = 描述
        self._宽度 = 宽度
        self._填充字符 = 填充字符
        self._空白字符 = 空白字符
        self._前缀 = 前缀
        self._后缀 = 后缀
        self._输出流 = 输出流
        self._当前 = 0
        self._开始时间 = time.time()
        self._最后打印长度 = 0

    def 更新(self, 增量: int = 1):
        """更新进度"""
        self._当前 += 增量
        self._显示()

    def 设置当前(self, 值: int):
        """直接设置当前进度值"""
        self._当前 = min(值, self._总数)
        self._显示()

    def _显示(self):
        """显示进度条"""
        百分比 = self._当前 / self._总数 if self._总数 > 0 else 0
        填充长度 = int(self._宽度 * 百分比)
        空白长度 = self._宽度 - 填充长度

        进度条字符串 = self._填充字符 * 填充长度 + self._空白字符 * 空白长度

        已用时间 = time.time() - self._开始时间
        每秒速率 = self._当前 / 已用时间 if 已用时间 > 0 else 0
        剩余时间 = (self._总数 - self._当前) / 每秒速率 if 每秒速率 > 0 else 0

        行 = f"\r{self._前缀}{self._描述} |{进度条字符串}| {百分比:.0%} "
        行 += f"[{self._当前}/{self._总数}] "
        行 += f"({已用时间:.1f}s/{剩余时间:.1f}s){self._后缀}"

        if 百分比 >= 1:
            行 += '\n'

        self._输出流.write(行)
        self._输出流.flush()
        self._最后打印长度 = len(行)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.设置当前(self._总数)


def 创建进度条(总数: int = 100, 描述: str = '') -> 进度条:
    """创建进度条"""
    return 进度条(总数=总数, 描述=描述)


def 迭代进度条(可迭代对象, 描述: str = '', 总数: Optional[int] = None):
    """
    迭代并显示进度条

    用法:
        for item in 迭代进度条(列表, 描述='处理'):
            # 处理 item
    """
    可迭代列表 = list(可迭代对象)
    总数 = 总数 or len(可迭代列表)
    with 进度条(总数=总数, 描述=描述) as pb:
        for item in 可迭代列表:
            yield item
            pb.更新(1)


class 多阶段进度条:
    """多阶段进度条，支持多步任务"""

    def __init__(self, 阶段列表: list, 描述: str = '') -> None:
        """
        初始化多阶段进度条

        参数:
            阶段列表: 每个元素为 (阶段名称, 阶段总数)
            描述: 总体描述
        """
        self._阶段列表 = 阶段列表
        self._描述 = 描述
        self._当前阶段 = 0
        self._总进度 = 0
        self._总步数 = sum(步骤数 for _, 步骤数 in 阶段列表)
        self._当前阶段进度条 = 进度条(总数=阶段列表[0][1], 描述=阶段列表[0][0])
        self._开始时间 = time.time()

    def 更新(self, 增量: int = 1):
        """更新当前阶段进度"""
        self._当前阶段进度条.更新(增量)
        self._总进度 += 增量

    def 进入下一阶段(self):
        """进入下一阶段"""
        self._当前阶段 += 1
        if self._当前阶段 < len(self._阶段列表):
            阶段名称, 阶段总数 = self._阶段列表[self._当前阶段]
            self._当前阶段进度条 = 进度条(总数=阶段总数, 描述=阶段名称)

    def 完成(self):
        """完成进度"""
        总时间 = time.time() - self._开始时间
        print(f"\n{self._描述} 完成，耗时 {总时间:.1f}s")


def 显示旋转指示器(描述: str = '处理中', 停止条件: Optional[callable] = None,
                   间隔: float = 0.1, 超时: float = 10):
    """
    显示旋转指示器，直到满足停止条件或超时

    参数:
        描述: 显示文本
        停止条件: 返回 True 时停止
        间隔: 旋转更新间隔（秒）
        超时: 超时时间（秒）
    """
    符号 = '|/-\\'
    开始时间 = time.time()
    i = 0
    while True:
        if 停止条件 and 停止条件():
            break
        if time.time() - 开始时间 > 超时:
            break
        sys.stderr.write(f"\r{描述} {符号[i % 4]}")
        sys.stderr.flush()
        i += 1
        time.sleep(间隔)
    sys.stderr.write(f"\r{描述} 完成\n")
    sys.stderr.flush()