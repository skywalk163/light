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
import re
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STDLIB = os.path.join(_ROOT, "stdlib")
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


# ── 第九轮 S1 合并点：门面导出面必须盖住全部消费方（不只 examples/tests）──────────
# 症状：C9 把 文件系统.py 换成 文件系统.light 门面时按「examples/tests 用到的名」数导出，
# 漏了 积木库/工具/列目录文件.light 要的 文件列表 → CI 的积木库闸门红（可运行率
# 0.9945 < 1.0、问题块数 1），而本机七道门禁与全部 pytest 全绿，红只在 CI 才出现。
# 本判据把「积木库消费的名字」纳入本机可跑范围：凡 stdlib 有纯光明门面的模块，
# 积木库里 `从《模块》导入《名》` 的名字必须真在门面的 导出 行里。
_BLOCKS = os.path.join(_ROOT, "积木库")
_IMPORT_RE = re.compile(r"从《([^》]+)》导入《([^》]+)》")


def test_积木库导入的名字必须在纯光明门面的导出面内():
    门面 = {}
    for full in glob.glob(os.path.join(_STDLIB, "*.light")):
        text = open(full, encoding="utf-8").read()
        if _MAGIC not in "".join(text.splitlines(keepends=True)[:2]):
            continue  # 不是门面（没被钩子接管），仍走同名 .py，不受本判据约束
        导出名 = set()
        for line in text.splitlines():
            if line.startswith("导出 "):
                导出名 |= set(line[3:].rstrip("。").split())
        门面[os.path.splitext(os.path.basename(full))[0]] = 导出名
    assert 门面, "stdlib 里一个纯光明门面都没找到，判据不成立"

    缺口 = []
    for full in glob.glob(os.path.join(_BLOCKS, "**", "*.light"), recursive=True):
        for 模块, 名 in _IMPORT_RE.findall(open(full, encoding="utf-8").read()):
            if 模块 in 门面 and 名 not in 门面[模块]:
                缺口.append((os.path.relpath(full, _ROOT), 模块, 名))
    assert 缺口 == [], "积木库要的名字不在门面导出面里（CI 积木库闸门会红）：%s" % 缺口


# ── 第九轮 S2：地板转发 —— 运行期必须真的取光明的返回值 ──────────────────────────
# tools/ci/floor_bootstrap.py 只能静态看到 builtins.py 的函数体里出现了那个光明模块名。
# 它抓得到「改回 text.upper() 且删了 import」，抓不到「留一句 import 装样子、实际仍走
# Python 老路」—— 那正是最容易发生的退化形态。所以这里用替身法给出运行期判据：
# 把光明模块里的那个段落换成返回哨兵的替身，再调 builtins 的同名函数；拿不到哨兵，
# 就说明返回值不是从光明来的。
_已转发 = {
    "转大写": ("字符串工具轻量", ("abc",), "ABC"),
    "转小写": ("字符串工具轻量", ("ABC",), "abc"),
    "字符串长度": ("字符串工具轻量", ("中文Ab",), 4),
    "去除左侧空白": ("字符串工具轻量", ("  x  ",), "x  "),
    "去除右侧空白": ("字符串工具轻量", ("  x  ",), "  x"),
    "替换字符串": ("字符串工具轻量", ("aaa", "a", "b"), "bbb"),
    "分割字符串": ("字符串工具轻量", ("a,b,c", ","), ["a", "b", "c"]),
    # ── S2 新接 47 条（五个 内置核心*.light 模块）────────────────────────────
    # 返回 None 的原地段落（列表追加/插入/排序/反转、字典设置/删除）期望值就是 None：
    # 转发写成 `return 内置核心X.名字(...)`，换上替身后拿到的是哨兵而不是 None，
    # 所以这条判据对它们同样有效（判的是「值从哪来」，不是「值是什么」）。
    "字符串获取": ("内置核心字符串", ("abc", 1), "b"),
    "截取": ("内置核心字符串", ("abcdef", 1, 3), "bc"),
    "去除空白": ("内置核心字符串", ("  x  ",), "x"),
    "字符串包含": ("内置核心字符串", ("abc", "b"), True),
    "开头": ("内置核心字符串", ("abc", "a"), True),
    "结尾": ("内置核心字符串", ("abc", "c"), True),
    "查找子串": ("内置核心字符串", ("abcabc", "c"), 2),
    "最后索引": ("内置核心字符串", ("abcabc", "c"), 5),
    "替换字符串次数": ("内置核心字符串", ("aaa", "a", "b", 2), "bba"),
    "截取到末尾": ("内置核心字符串", ("abcd", 2), "cd"),
    "字符串计数": ("内置核心字符串", ("aaa", "a"), 3),
    "字符串重复": ("内置核心字符串", ("ab", 3), "ababab"),
    "字符串反转": ("内置核心字符串", ("abcd",), "dcba"),
    "转标题": ("内置核心字符串", ("hello world",), "Hello World"),
    "字符串对齐居中": ("内置核心字符串", ("ab", 6, "-"), "--ab--"),
    "字符串对齐左": ("内置核心字符串", ("ab", 4, "."), "ab.."),
    "字符串对齐右": ("内置核心字符串", ("ab", 4, "."), "..ab"),
    "是整数": ("内置核心判型", (1,), True),
    "是浮点": ("内置核心判型", (1.5,), True),
    "是字符串": ("内置核心判型", ("a",), True),
    "是列表": ("内置核心判型", ([],), True),
    "是字典": ("内置核心判型", ({},), True),
    "是空": ("内置核心判型", (None,), True),
    "是字母": ("内置核心判型", ("a",), True),
    "是数字": ("内置核心判型", ("1",), True),
    "是空白": ("内置核心判型", (" ",), True),
    "列": ("内置核心列表", (1, 2), [1, 2]),
    "列表创建": ("内置核心列表", (), []),
    "列表长度": ("内置核心列表", ([1, 2, 3],), 3),
    "列表获取": ("内置核心列表", ([1, 2, 3], 1), 2),
    "列表追加": ("内置核心列表", ([], "x"), None),
    "列表弹出": ("内置核心列表", ([1, 2], 0), 1),
    "列表插入": ("内置核心列表", ([], 0, "x"), None),
    "列表排序": ("内置核心列表", ([2, 1], False), None),
    "列表反转": ("内置核心列表", ([1, 2],), None),
    "列表包含": ("内置核心列表", ([1, 2], 2), True),
    "字典创建": ("内置核心字典", (), {}),
    "字典设置": ("内置核心字典", ({}, "k", 1), None),
    "字典删除": ("内置核心字典", ({"k": 1}, "k"), None),
    "字典键列表": ("内置核心字典", ({"k": 1},), ["k"]),
    "字典值列表": ("内置核心字典", ({"a": 9},), [9]),
    "字典项列表": ("内置核心字典", ({"a": 9},), [("a", 9)]),
    "字典包含键": ("内置核心字典", ({"a": 1}, "a"), True),
    "字典获取": ("内置核心字典", ({"a": 1}, "b", 7), 7),
    "转整数": ("内置核心转换", ("42",), 42),
    "转浮点": ("内置核心转换", ("1.5",), 1.5),
    "转字符串": ("内置核心转换", (1,), "1"),
    "解析JSON": ("JSON", ('{"a": 1}',), {"a": 1}),
    "序列化JSON": ("JSON", ({"a": 1},), '{"a": 1}'),
    "美化JSON": ("JSON", ({"a": 1},), '{\n  "a": 1\n}'),
    # 求和 的哨兵入参必须能同时穿过整数快路径与补偿路径：全 int 列表在光明侧
    # 走的是「首段不切出、直接返回整值」那条，若只测 [1,2] 则朴素累加也会绿。
    "求和": ("列表工具", ([1e16, 1.0, -1e16],), 1.0),
    # 连接字符串 的入参必须是「全 str」：非 str 元素现在会抛 TypeError（已收严到
    # str.join 口径），哨兵替身那一跳也就没法走完。
    "连接字符串": ("字符串工具轻量", (["a", "b"], "-"), "a-b"),
    # 路径 6 条**刻意不在本表里**：替身 stdlib/内置核心路径.light 已写好，且与
    # posixpath 逐条等价（tests/unit/test_地板搬迁_路径_S2.py，466 条），但
    # builtins.py 没有转发 —— stdlib/操作系统.light:26-31 `本机平台` 把
    # 「`连接路径("甲","乙")` 里有没有反斜杠」当作平台判定的**唯一探针**，
    # 换成只认 `/` 的 POSIX 语义会让 Windows 上 `本机平台()` 返回 "posix"，
    # 路径护栏 / 代理工具集 / 路径运算 / harness 沙箱连带 46 条测试转红（实测）。
    # 它们仍算「替身已就位但未转发」，收进本表就是假绿。
}



_哨兵 = "＿这是替身的返回值＿"


def _新装地板():
    """把 stdlib/builtins.py 当独立模块重新载入一份，避免污染其他测试的模块表。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_地板副本", os.path.join(_STDLIB, "builtins.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("名字", sorted(_已转发))
def test_地板转发的函数在运行期真的取光明的返回值(名字):
    import importlib
    模块名, 入参, 期望 = _已转发[名字]
    地板 = _新装地板()

    结果 = getattr(地板, 名字)(*入参)
    assert 结果 == 期望, "%s%r 应得 %r，实得 %r" % (名字, 入参, 期望, 结果)

    光明 = importlib.import_module(模块名)
    assert getattr(光明, "__light_source__", "").endswith(".light"), (
        "%s 不是由 .light 加载的（__light_source__=%r）"
        % (模块名, getattr(光明, "__light_source__", None)))

    原段落 = getattr(光明, 名字)
    try:
        setattr(光明, 名字, lambda *a, **k: _哨兵)
        经替身 = getattr(地板, 名字)(*入参)
    finally:
        setattr(光明, 名字, 原段落)
    assert 经替身 == _哨兵, (
        "把 %s.%s 换成替身后，builtins.%s 仍返回 %r —— 说明它没真的转发，"
        "运行期跑的还是 Python（门禁只看静态 import，抓不到这种退化）"
        % (模块名, 名字, 名字, 经替身))


def test_分割字符串的三条口径不许被搬迁顺手改掉():
    """光明版用 "" 表示「按空白切」，Python 版用 None；且 "" 在 Python 语义里是错误用法。

    搬迁时最容易顺手把 `separator=""` 也当成「按空白切」放过去 —— 那是把
    `"a".split("")` 的 ValueError 悄悄吞掉，属于放宽错误检查。
    """
    地板 = _新装地板()
    assert 地板.分割字符串("  a  b ") == ["a", "b"]           # None → 按空白
    assert 地板.分割字符串("a,,b", ",") == ["a", "", "b"]     # 显式分隔符，空段要保留
    with pytest.raises(ValueError):
        地板.分割字符串("a", "")                              # 空分隔符仍是错误用法
