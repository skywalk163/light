# -*- coding: utf-8 -*-
"""
任务D：插件系统（纯光明实现）定向测试
覆盖：加载/启动/停止/卸载生命周期、依赖拓扑序（启动正序/停止逆序）、
      卸载后总线订阅被清理（无幽灵监听者）、循环依赖被拒绝、能力声明被
      拒绝、插件初始化抛异常时的回滚、扩展点注册与触发。
"""
import os
import sys

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, os.path.join(_PROJECT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT, 'stdlib'))

import _light_import_hook
_light_import_hook.install([os.path.join(_PROJECT, 'stdlib'), _PROJECT])

import pytest

from 事件总线 import 事件总线
from 插件 import 插件, 插件管理器


def _管理器():
    return 插件管理器(事件总线())


class Test基本生命周期:
    def test_加载启动停止卸载(self):
        m = _管理器()
        记录 = []

        class 甲(插件):
            名称 = "甲"
            依赖 = []
            能力 = []

            def 启动(self):
                记录.append("启动")

            def 停止(self):
                记录.append("停止")

        m.注册插件("甲", 甲)
        assert m.加载插件("甲") is True
        assert m.已加载("甲")
        assert 记录 == ["启动"]
        m.卸载插件("甲")
        assert not m.已加载("甲")
        assert 记录 == ["启动", "停止"]

    def test_加载已存在幂等返回路径不重复启动(self):
        m = _管理器()
        记录 = []

        class 甲(插件):
            名称 = "甲"
            依赖 = []
            能力 = []

            def 启动(self):
                记录.append("启动")

        m.注册插件("甲", 甲)
        m.加载插件("甲")
        m.加载插件("甲")  # 已是实例表 → 跳过，不二次启动
        assert 记录 == ["启动"]


class Test依赖拓扑序:
    def test_启动正序停止逆序(self):
        m = _管理器()
        记录 = []

        class 甲(插件):
            名称 = "甲"
            依赖 = []
            能力 = []

            def 启动(self):
                记录.append("启动甲")

            def 停止(self):
                记录.append("停止甲")

        class 乙(插件):
            名称 = "乙"
            依赖 = ["甲"]
            能力 = []

            def 启动(self):
                记录.append("启动乙")

            def 停止(self):
                记录.append("停止乙")

        class 丙(插件):
            名称 = "丙"
            依赖 = ["乙"]
            能力 = []

            def 启动(self):
                记录.append("启动丙")

            def 停止(self):
                记录.append("停止丙")

        for 名, 类 in [("甲", 甲), ("乙", 乙), ("丙", 丙)]:
            m.注册插件(名, 类)
        # 只加载丙，应连带启动其全部依赖，且按拓扑序
        m.加载插件("丙")
        assert 记录 == ["启动甲", "启动乙", "启动丙"]
        assert m.已加载("甲") and m.已加载("乙") and m.已加载("丙")
        # 逆序停止
        记录.clear()
        m.停止多个(["甲", "乙"])
        assert 记录 == ["停止乙", "停止甲"]
        assert not m.已加载("甲") and not m.已加载("乙")
        # 丙不受影响
        assert m.已加载("丙")


class Test卸载清理订阅:
    def test_卸载后订阅被清理无幽灵监听者(self):
        m = _管理器()
        命中 = []

        class 甲(插件):
            名称 = "甲"
            依赖 = []
            能力 = []

            def 启动(self):
                # 订阅一个事件
                己句柄 = m.订阅("甲", "事件X", lambda e, p: 命中.append(p))

        m.注册插件("甲", 甲)
        m.加载插件("甲")
        # 发布触发一次
        m.发布("事件X", 1)
        assert 命中 == [1]
        # 卸载插件 → 其订阅应被自动取消
        m.卸载插件("甲")
        m.发布("事件X", 2)
        assert 命中 == [1]


class Test错误与拒绝:
    def test_循环依赖被拒绝(self):
        m = _管理器()

        class 甲(插件):
            名称 = "甲"
            依赖 = ["乙"]
            能力 = []

        class 乙(插件):
            名称 = "乙"
            依赖 = ["甲"]
            能力 = []

        m.注册插件("甲", 甲)
        m.注册插件("乙", 乙)
        with pytest.raises(RuntimeError):
            m.加载多个(["甲"])
        # 不应留下任何半加载的实例
        assert not m.已加载("甲") and not m.已加载("乙")

    def test_能力声明被拒绝(self):
        m = _管理器()
        # 白表只允许 网络/文件
        m.设置能力许可(["网络", "文件"])

        class 越界(插件):
            名称 = "越界"
            依赖 = []
            能力 = ["进程"]

        m.注册插件("越界", 越界)
        with pytest.raises(RuntimeError):
            m.加载插件("越界")
        assert not m.已加载("越界")

    def test_未登记的依赖被拒绝(self):
        m = _管理器()

        class 甲(插件):
            名称 = "甲"
            依赖 = ["不存在插件"]
            能力 = []

        m.注册插件("甲", 甲)
        with pytest.raises(RuntimeError):
            m.加载插件("甲")
        assert not m.已加载("甲")


class Test初始化异常回滚:
    def test_启动顺序中第三个崩则前两个被回滚(self):
        m = _管理器()
        记录 = []

        class 甲(插件):
            名称 = "甲"
            依赖 = []
            能力 = []

            def 启动(self):
                记录.append("启动甲")

            def 停止(self):
                记录.append("停止甲")

        class 乙(插件):
            名称 = "乙"
            依赖 = []
            能力 = []

            def 启动(self):
                记录.append("启动乙")

            def 停止(self):
                记录.append("停止乙")

        class 崩(插件):
            名称 = "崩"
            依赖 = []
            能力 = []

            def __init__(self):
                raise RuntimeError("崩在初始化")

            def 启动(self):
                记录.append("启动崩")

        for 名, 类 in [("甲", 甲), ("乙", 乙), ("崩", 崩)]:
            m.注册插件(名, 类)
        with pytest.raises(RuntimeError):
            m.加载多个(["甲", "乙", "崩"])
        # 甲、乙 已启动，崩 失败 → 前两者被回滚停止并移除
        assert 记录 == ["启动甲", "启动乙", "停止乙", "停止甲"]
        assert not m.已加载("甲") and not m.已加载("乙") and not m.已加载("崩")


class Test扩展点:
    def test_注册与触发返回结果并按序(self):
        m = _管理器()
        m.注册扩展点("重镜像", lambda p: p * 2)
        m.注册扩展点("重镜像", lambda p: p + 1)
        结果 = m.触发扩展点("重镜像", 5)
        assert 结果 == [10, 6]

    def test_未注册的扩展点返回空表(self):
        m = _管理器()
        assert m.触发扩展点("看不懂", 1) == []

    def test_单个扩展点抛异常不影响其它(self):
        m = _管理器()

        def 崩(p):
            raise ValueError("崩")

        m.注册扩展点("混合", 崩)
        m.注册扩展点("混合", lambda p: p + 1)
        assert m.触发扩展点("混合", 1) == [2]