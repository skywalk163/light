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
import glob
import os
import sys

import pytest

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


def test_datetime_still_resolves_to_py():
    """回归护栏：《日期时间》必须仍解析到能力更全的 stdlib/日期时间.py。

    C2 曾把一份 11 导出的纯光明实现写成 日期时间.light 并加魔数，于是它遮蔽了
    100+ 导出的 日期时间.py，tests/test_datetime.py 退化成 collection error 并
    中断整个非 e2e 全量。纯光明那份已改名《日期时间轻量》。
    """
    import importlib
    mod = importlib.import_module("日期时间")
    assert not hasattr(mod, "__light_source__")
    assert getattr(mod, "__file__", "").endswith(".py")
    # .py 独有的能力面（类 + 农历），.light 那 11 个导出里没有
    assert hasattr(mod, "日期时间") and hasattr(mod, "农历日期")

    轻量 = importlib.import_module("日期时间轻量")
    assert getattr(轻量, "__light_source__", "").endswith(".light")
    assert 轻量.两个数字(5) == "05"


# ── D3-5 首两行魔数守卫 ──────────────────────────────────────────────────────
# `_light_import_hook._is_pure_light()` 只读首两行（见 stdlib/_light_import_hook.py）。
# 凡 .light 内**任何位置**含「纯光明实现」但首两行没有的，一旦有人建了同名 .py，
# 这份 .light 会被静默遮蔽（行为倒退，且无任何报错）。
#
# 已知 5 个真实现魔数不在首两行，属 A3/B3 独占文件：
#   伪终端.light:11 / 事件总线.light:4 / 插件.light:5 / 进程树.light:12 / 路径护栏.light:5
# 本轮（D3）只加检查、不改文件；A3/B3 尚未合入 main，所以先按 **warn（xfail）**
# 处理，不阻断 CI。A3/B3 合入并把魔数提到首两行后，本 warn 自动消失；
# 若届时仍残留，应改为硬红并追问对应任务。
_KNOWN_MAGIC_NOT_FIRST2 = {
    "伪终端", "事件总线", "插件", "进程树", "路径护栏",
}
_MAGIC = "纯光明实现"


def test_magic_number_in_first_two_lines():
    """防定时炸弹：含「纯光明实现」但首两行没有的 .light 必须打红。

    已知 5 个（A3/B3 待修）→ 本次按 warn（xfail）；新出现的违反 → 硬红。
    """
    violations = []
    for full in glob.glob(os.path.join(_STDLIB, "*.light")):
        name = os.path.splitext(os.path.basename(full))[0]
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
                text = "".join(lines)
        except OSError:
            continue
        if _MAGIC not in text:
            continue
        if _MAGIC in "".join(lines[:2]):
            continue  # 魔数已在首两行，安全
        violations.append(name)

    # 新出现的违反（不在已知 5 个里）一律硬红——这是本门禁的价值所在。
    new = [v for v in violations if v not in _KNOWN_MAGIC_NOT_FIRST2]
    if new:
        pytest.fail(
            "以下 .light 含「纯光明实现」但不在首两行，会被同名 .py 静默遮蔽（新出现，须硬红）：%s"
            % new
        )

    # 已知 5 个仍违规 → warn（xfail），不阻断 CI，但在报告里点名催 A3/B3 修。
    # TODO(D3-5): A3 修 事件总线、B3 修其余 4 个，并把魔数提到首两行后，
    #             本 xfail 会自动消失；若 A3/B3 合入后仍残留，改为硬红。
    # 截止条件：A3/B3 合入 main 后的下一轮 D3 收口时移除本 warn。
    known_still = [v for v in violations if v in _KNOWN_MAGIC_NOT_FIRST2]
    if known_still:
        pytest.xfail(
            "已知 5 个真实现魔数不在首两行（A3/B3 待修，warn 不红）：%s" % known_still
        )


# ── 第九轮 S1 合并点：大小写不敏感文件系统导致的标准库劫持 ──────────────────────
# C9 给 stdlib/JSON.light 加了「纯光明实现」魔数后，钩子原来的 os.path.isfile
# 在 Windows / macOS 上把 `json` 也当成命中（json.light ≡ JSON.light），于是
# Python 标准库的 `import json` 被换成只有中文导出名的光明门面。任何第三方库里
# 的 `from json import loads`（pandas/core/generic.py 就有）当场 ImportError，
# 表现为 5 条 e2e 产物运行失败，且报错栈跟光明毫无字面关系。
def test_标准库json不被同名不同壳的light劫持():
    import importlib
    mod = importlib.import_module("json")
    assert not hasattr(mod, "__light_source__"), (
        "钩子劫持了标准库 json，实际来源：%s" % getattr(mod, "__file__", None)
    )
    # 只断言「不是 .light」不够——第三方库要的是 loads 这个名字真能取到。
    assert mod.loads("[]") == []


def test_大写JSON仍走纯光明门面():
    """反向护栏：修大小写命中不许把真·纯光明模块一起关掉。"""
    import importlib
    mod = importlib.import_module("JSON")
    assert getattr(mod, "__light_source__", "").endswith("JSON.light")
    assert mod.解析JSON("[]") == []


def test_任何light都不许应答仅大小写不同的标准库名():
    """通用判据：把 5 条 e2e 的具体症状升级成对全部 .light 的结构约束。"""
    finder = _light_import_hook._current_finder()
    assert isinstance(finder, _light_import_hook.LightFinder) and _STDLIB in finder.search_paths, \
        "钩子未挂在 stdlib 上，本判据不成立：%r" % (finder and finder.search_paths,)
    劫持 = []
    for full in glob.glob(os.path.join(_STDLIB, "*.light")):
        name = os.path.splitext(os.path.basename(full))[0]
        for 标准名 in sys.stdlib_module_names:
            if 标准名 == name or 标准名.lower() != name.lower():
                continue
            if finder.find_spec(标准名) is not None:
                劫持.append((name, 标准名))
    assert 劫持 == [], "以下 .light 会劫持仅大小写不同的标准库模块：%s" % 劫持
