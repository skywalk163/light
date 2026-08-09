# -*- coding: utf-8 -*-
"""
光明标准库 - 单元测试框架模块

提供类似 Python unittest 的单元测试功能。
"""

import sys
import traceback
import time
from typing import Callable, List, Dict, Any, Optional


class 测试用例:
    """测试用例基类"""

    def __init__(self, 名称: str = ''):
        self._名称 = 名称 or self.__class__.__name__
        self._结果 = []
        self._通过 = 0
        self._失败 = 0
        self._错误 = 0

    def 设置(self):
        """每个测试方法执行前的准备工作（可重写）"""
        pass

    def 清理(self):
        """每个测试方法执行后的清理工作（可重写）"""
        pass

    def 类设置(self):
        """所有测试方法执行前的类级别准备工作（可重写）"""
        pass

    def 类清理(self):
        """所有测试方法执行后的类级别清理工作（可重写）"""
        pass

    def 断言相等(self, 预期, 实际, 消息: str = ''):
        """断言两个值相等"""
        if 预期 != 实际:
            失败消息 = f"期望 {预期!r}，但得到 {实际!r}"
            if 消息:
                失败消息 += f"：{消息}"
            raise AssertionError(失败消息)

    def 断言不相等(self, 预期, 实际, 消息: str = ''):
        """断言两个值不相等"""
        if 预期 == 实际:
            失败消息 = f"期望不等于 {预期!r}"
            if 消息:
                失败消息 += f"：{消息}"
            raise AssertionError(失败消息)

    def 断言真(self, 表达式, 消息: str = ''):
        """断言表达式为真"""
        if not 表达式:
            失败消息 = "表达式为假"
            if 消息:
                失败消息 += f"：{消息}"
            raise AssertionError(失败消息)

    def 断言假(self, 表达式, 消息: str = ''):
        """断言表达式为假"""
        if 表达式:
            失败消息 = "表达式为真"
            if 消息:
                失败消息 += f"：{消息}"
            raise AssertionError(失败消息)

    def 断言为空(self, 值, 消息: str = ''):
        """断言值为空"""
        if 值 is not None and 值 != '' and 值 != [] and 值 != {}:
            失败消息 = f"值非空: {值!r}"
            if 消息:
                失败消息 += f"：{消息}"
            raise AssertionError(失败消息)

    def 断言非空(self, 值, 消息: str = ''):
        """断言值非空"""
        if 值 is None or 值 == '' or 值 == [] or 值 == {}:
            失败消息 = "值为空"
            if 消息:
                失败消息 += f"：{消息}"
            raise AssertionError(失败消息)

    def 断言包含(self, 容器, 元素, 消息: str = ''):
        """断言容器包含元素"""
        if 元素 not in 容器:
            失败消息 = f"{容器!r} 不包含 {元素!r}"
            if 消息:
                失败消息 += f"：{消息}"
            raise AssertionError(失败消息)

    def 断言不包含(self, 容器, 元素, 消息: str = ''):
        """断言容器不包含元素"""
        if 元素 in 容器:
            失败消息 = f"{容器!r} 包含 {元素!r}"
            if 消息:
                失败消息 += f"：{消息}"
            raise AssertionError(失败消息)

    def 断言异常(self, 异常类型, 可调用对象, *参数, **关键字参数):
        """
        断言可调用对象抛出指定异常

        返回:
            捕获的异常对象
        """
        try:
            可调用对象(*参数, **关键字参数)
        except 异常类型 as e:
            return e
        except Exception as e:
            raise AssertionError(f"期望异常 {异常类型.__name__}，但得到了 {type(e).__name__}")
        raise AssertionError(f"期望异常 {异常类型.__name__}，但未抛出任何异常")

    def 断言近似(self, 预期, 实际, 精度: int = 7, 消息: str = ''):
        """断言两个浮点数近似相等"""
        if round(预期, 精度) != round(实际, 精度):
            失败消息 = f"期望 {预期}，但得到 {实际}（精度: {精度}位小数）"
            if 消息:
                失败消息 += f"：{消息}"
            raise AssertionError(失败消息)


class 测试运行器:
    """测试运行器"""

    def __init__(self, 详细: bool = True):
        self._详细 = 详细
        self._结果 = {'通过': 0, '失败': 0, '错误': 0, '总计': 0}

    def 运行(self, 测试用例类: type) -> Dict[str, int]:
        """
        运行测试用例类中的所有测试方法

        参数:
            测试用例类: 继承自 测试用例 的类

        返回:
            测试结果字典
        """
        实例 = 测试用例类()
        测试方法列表 = self._获取测试方法(测试用例类)

        if self._详细:
            print(f"\n运行 {测试用例类.__name__} ({len(测试方法列表)} 个测试)...")

        # 类级别设置
        try:
            实例.类设置()
        except Exception as e:
            print(f"  类设置失败: {e}")
            for 方法名 in 测试方法列表:
                self._结果['错误'] += 1
                self._结果['总计'] += 1
            return self._结果

        for 方法名 in 测试方法列表:
            self._结果['总计'] += 1
            方法 = getattr(实例, 方法名)

            try:
                实例.设置()
                try:
                    方法()
                    self._结果['通过'] += 1
                    if self._详细:
                        print(f"  ✓ {方法名}")
                except AssertionError as e:
                    self._结果['失败'] += 1
                    print(f"  ✗ {方法名}: {e}")
                except Exception as e:
                    self._结果['错误'] += 1
                    print(f"  ✗ {方法名}: 未预期错误 - {e}")
                    traceback.print_exc()
                finally:
                    实例.清理()
            except Exception as e:
                self._结果['错误'] += 1
                print(f"  ✗ {方法名}: 设置/清理失败 - {e}")

        # 类级别清理
        try:
            实例.类清理()
        except Exception as e:
            print(f"  类清理失败: {e}")

        # 打印摘要
        if self._详细:
            self._打印摘要()

        return self._结果

    def 运行多个(self, *测试用例类列表: type) -> Dict[str, int]:
        """运行多个测试用例类"""
        总结果 = {'通过': 0, '失败': 0, '错误': 0, '总计': 0}

        for 类 in 测试用例类列表:
            结果 = self.运行(类)
            for key in 总结果:
                总结果[key] += 结果[key]

        print(f"\n{'='*50}")
        print(f"总计: {总结果['总计']} 个测试")
        print(f"通过: {总结果['通过']}")
        print(f"失败: {总结果['失败']}")
        print(f"错误: {总结果['错误']}")
        if 总结果['失败'] == 0 and 总结果['错误'] == 0:
            print("全部通过 ✓")
        else:
            print("存在失败测试 ✗")
        print(f"{'='*50}")

        return 总结果

    def _获取测试方法(self, 测试用例类: type) -> List[str]:
        """获取所有测试方法"""
        方法列表 = []
        for 名称 in dir(测试用例类):
            if 名称.startswith('测试'):
                方法 = getattr(测试用例类, 名称)
                if callable(方法):
                    方法列表.append(名称)
        return sorted(方法列表)

    def _打印摘要(self):
        print(f"  ---")
        print(f"  通过: {self._结果['通过']}, 失败: {self._结果['失败']}, 错误: {self._结果['错误']}")


def 运行测试(测试用例类: type, 详细: bool = True) -> Dict[str, int]:
    """
    运行测试用例类

    参数:
        测试用例类: 继承自 测试用例 的类
        详细: 是否显示详细信息

    返回:
        测试结果字典
    """
    运行器 = 测试运行器(详细=详细)
    return 运行器.运行(测试用例类)


def 运行多个测试(*测试用例类列表: type, 详细: bool = True) -> Dict[str, int]:
    """
    运行多个测试用例类

    参数:
        测试用例类列表: 多个测试用例类
        详细: 是否显示详细信息

    返回:
        测试结果字典
    """
    运行器 = 测试运行器(详细=详细)
    return 运行器.运行多个(*测试用例类列表)


def 断言相等(预期, 实际, 消息: str = ''):
    """断言两个值相等"""
    if 预期 != 实际:
        raise AssertionError(f"期望 {预期!r}，但得到 {实际!r}" + (f"：{消息}" if 消息 else ''))


def 断言真(表达式, 消息: str = ''):
    """断言表达式为真"""
    if not 表达式:
        raise AssertionError(f"表达式为假" + (f"：{消息}" if 消息 else ''))


def 断言异常(异常类型, 可调用对象, *参数, **关键字参数):
    """断言可调用对象抛出指定异常"""
    try:
        可调用对象(*参数, **关键字参数)
    except 异常类型 as e:
        return e
    except Exception as e:
        raise AssertionError(f"期望异常 {异常类型.__name__}，但得到了 {type(e).__name__}")
    raise AssertionError(f"期望异常 {异常类型.__name__}，但未抛出任何异常")


__all__ = [
    '测试用例', '测试运行器',
    '运行测试', '运行多个测试',
    '断言相等', '断言真', '断言异常',
]