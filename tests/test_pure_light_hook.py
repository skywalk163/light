# -*- coding: utf-8 -*-
"""
test_pure_light_hook.py —— 验证 stdlib/_light_import_hook.py 的「纯光明实现」声明机制

背景：钩子原先"同名 .py 存在则 .light 绝对跳过"，导致 列表工具.light 永不执行
（自举率上不去的结构性原因）。C2-2 引入显式声明：.light 首行含魔数「纯光明实现」
即优先加载 .light、无视同名 .py。

本测试：
- 正例：列表工具.light（已声明纯光明）确实被加载 .light 版本（有 __light_source__、
  __file__ 以 .light 结尾），且功能可用。
- 默认路径不变：未声明纯光明的模块（如 格式化，有同名 .py）仍走 .py 兜底。
"""
import os
import sys

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])


def test_list_tools_loads_light_version():
    from 列表工具 import 求和, 最大值, 反转列表
    mod = sys.modules.get("列表工具")
    # LightLoader 设置的特征属性，.py 模块不会有
    assert getattr(mod, "__light_source__", "").endswith(".light")
    assert getattr(mod, "__file__", "").endswith(".light")
    # 行为也可用
    assert 求和([1, 2, 3, 4]) == 10
    assert 最大值([3, 7, 2]) == 7
    assert 反转列表([1, 2, 3]) == [3, 2, 1]


def test_default_path_still_routes_to_py():
    # 格式化 有同名 .py 且 .light 未声明纯光明 → 应加载 .py 兜底
    import importlib
    mod = importlib.import_module("格式化")
    assert not hasattr(mod, "__light_source__")
    assert getattr(mod, "__file__", "").endswith(".py")


def test_is_pure_light_helper():
    # 直接验证魔数探测逻辑
    light_path = os.path.join(_STDLIB, "列表工具.light")
    assert _light_import_hook._is_pure_light(light_path) is True
    other = os.path.join(_STDLIB, "格式化.light")
    assert _light_import_hook._is_pure_light(other) is False