# -*- coding: utf-8 -*-
"""R158-B 回归门：地板自举检测器「语法级定位」的漂移容忍 + 反跑三组。

## 为什么要有这个文件

R157-E9：`tools/ci/floor_bootstrap.py` 的证据判定原本是「行号 ±2 文本窗口内存在一行
『既是定义行、又含该函数名』」。`stdlib/内置核心判型.light` 自 R153 起往每个 `段落`
上方增厚「对齐 stdlib/builtins.py:xxxx」注释，把 9 条判型内置的定义行推出了 ±2 窗口 ——
地板自举率被误算成 59/96（真值 68/96）。**代码定义完好、L1 判型类模块实测可编**，
是尺子（检测器口径）漂了，不是功能回退。

R157 只把 9 条证据行手工对准当前定义行（停血）。durable 教训：**改 `.light` 源文件
会顶行号** —— 任何在 `段落 X(` 上方增删行的改动都会让清单证据行再次失准，下轮跑
floor 门禁必红。R158-B 把判据换成**按声明名的语法级定位**（`声明行表` / `定位定义行`
/ `段落块`），本文件把这次根治钉成回归门。

## 判据

- **正向**：真仓库跑 floor 门禁 RC=0；地板自举率 == 68/96（70.83%）；9 条判型内置
  全部登记 `has_light_impl`，且证据经语法级定位校验通过。
- **反跑①**（顶得住 R153 那类注释增厚）：在 `段落 是字母(` 上方插 3 行注释后，
  整条 floor 门禁仍 RC=0 且 `light_count` 仍 68；**同一份漂移文件**用旧 ±2 窗口复算
  会红。若有人把 `floor_bootstrap.py` 改回 ±2 文本窗口，本类立即转红。
- **反跑②**（整树端到端）：`--root` 指向漂移树，门禁对真基线 RC=0、`light_count` 68。
- **反跑③**（防假绿，两形）：(a) 把一条 `movable` 真·空壳改成 `has_light_impl` 并把
  证据指向一个**没有该声明**的文件 → RC=1；(b) 证据行指向**有该声明但相距超过一个
  段落块长**的远处行 → RC=1（这条同时是「上界断言不算判据」的反跑）。

所有反跑都在临时目录里做，**绝不改写仓库里的清单与 `.light` 源**（任务书线 G 硬约束）。
"""

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CI_DIR = os.path.join(_ROOT, "tools", "ci")
_MANIFEST = os.path.join(_ROOT, "任务书", "自举地板清单.json")
_BUILTINS = os.path.join(_ROOT, "stdlib", "builtins.py")

# 判型内置：R157-E9 的 9 条现场（也是 R153 注释增厚的重灾区）。
_判型九条 = ("是字母", "是数字", "是空", "是空白", "是布尔",
            "是函数", "是数值", "字符串全数字", "是负零")
# 反跑用的样本：`段落 是字母(` 的定义行上方插行，最直接地复现 R153 场景。
_样本名 = "是字母"
_判型文件 = "stdlib/内置核心判型.light"
# 真仓库里 `是字母` 的定义行（R157 手工对准的值）。用它当「漂移前」的锚点。
_是字母定义行_R157 = 61

_旧窗口 = 2   # R158 之前的漂移窗口（行）


def _load(name):
    """按路径加载门禁脚本：`tools/ci` 不是包，import 不到。"""
    path = os.path.join(_CI_DIR, name + ".py")
    spec = importlib.util.spec_from_file_location("_r158bgate_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FB = _load("floor_bootstrap")


def _跑(*argv):
    """按 CLI 口径跑一遍门禁并拿 rc。

    单测「校验函数返回了几条问题」只证明形态对，证不了整条门禁会不会红 ——
    一律过 `main()`（与 test_ci_gates_round9.py 同口径）。
    """
    旧 = sys.argv
    sys.argv = ["gate"] + list(argv)
    try:
        return FB.main()
    finally:
        sys.argv = 旧


def _读json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _写json(path, data):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _读行(path):
    with io.open(path, encoding="utf-8", newline="") as fh:
        return fh.read().split("\n")


def _写行(path, 行, 换行):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(换行.join(行))


def _引用的落点文件(条目):
    """`has_light_impl` 条目证据引用的 `.light` 文件（POSIX 相对路径，去重排序）。

    门禁只对 `has_light_impl` 校验证据，所以最小树只需搬这些落点 —— 不必拷整个 stdlib。
    """
    落点 = set()
    for 条 in 条目:
        if 条.get("分类") != "has_light_impl":
            continue
        证据 = str(条.get("证据行", "")).strip()
        if ":" in 证据:
            落点.add(证据.split(":", 1)[0])
    return sorted(落点)


def _在样本段前插三行(行, 换行):
    """在 `段落 是字母(` 的定义行**正上方**插 3 行注释，返回 (新行, 新定义行, 旧定义行)。

    插行位置由 `FB.声明行表` 现算（不写死行号）——写死就又把「猜行号」请回来了。
    """
    纯行 = [s.rstrip("\r") for s in 行]
    定义行, _缩 = FB.定位定义行(FB.声明行表(纯行), _样本名, 1)
    if 定义行 is None:
        raise AssertionError("样本 `%s` 在判型文件里找不到 —— 测试自身失效" % _样本名)
    新 = list(行)
    新[定义行 - 1:定义行 - 1] = ["# R158-B 反跑：人为增厚注释 1",
                              "# R158-B 反跑：人为增厚注释 2",
                              "# R158-B 反跑：人为增厚注释 3"]
    return 新, 定义行 + 3, 定义行


def _旧窗口命中(行列表, 行号, 名字, 窗口=_旧窗口):
    """R158 之前的判据复刻：±2 行窗口内找「既是定义行、又含该函数名」的行。

    复刻它不是为了让它继续生效，而是把「旧口径会红」钉成可执行的证据 ——
    反跑①要的「改回 ±2 立即转红」，红的就是这条。
    """
    起 = max(0, 行号 - 1 - 窗口)
    止 = min(len(行列表), 行号 + 窗口)
    return [i + 1 for i in range(起, 止)
            if FB.RE_DECL.search(行列表[i]) and 名字 in 行列表[i]]


def _最小树(d, 漂移判型=False, 清单数据=None):
    """搭一棵「够 floor 门禁跑完整一轮」的最小仓库树，返回清单路径。

    组成：`stdlib/builtins.py` + 各 `has_light_impl` 落点 `.light`（连同名 `.py` 影子）
    + `任务书/自举地板清单.json`。`漂移判型=True` 时判型文件走「样本段上方插 3 行」。
    """
    os.makedirs(os.path.join(d, "stdlib"), exist_ok=True)
    os.makedirs(os.path.join(d, "任务书"), exist_ok=True)
    shutil.copy(_BUILTINS, os.path.join(d, "stdlib", "builtins.py"))
    清单 = 清单数据 if 清单数据 is not None else _读json(_MANIFEST)
    清单路径 = os.path.join(d, "任务书", "自举地板清单.json")
    _写json(清单路径, 清单)
    for rel in _引用的落点文件(清单["函数"]):
        src = os.path.join(_ROOT, *rel.split("/"))
        dst = os.path.join(d, *rel.split("/"))
        if rel == _判型文件 and 漂移判型:
            行 = _读行(src)
            换行 = "\r\n" if any(s.endswith("\r") for s in 行) else "\n"
            行 = [s.rstrip("\r") for s in 行]
            行, _新, _旧 = _在样本段前插三行(行, 换行)
            _写行(dst, 行, 换行)
        else:
            d2 = os.path.dirname(dst)
            if d2 and not os.path.isdir(d2):
                os.makedirs(d2)
            shutil.copy(src, dst)
        影子 = src[:-len(".light")] + ".py"
        if os.path.isfile(影子):
            shutil.copy(影子, dst[:-len(".light")] + ".py")
    return 清单路径


class Test正向_真仓库不漂(unittest.TestCase):
    """真清单 + 真 `.light` + 真基线 → 绿，且自举率仍是 68/96。"""

    def test_门禁在真仓库上通过(self):
        self.assertEqual(_跑("--root", _ROOT), 0)

    def test_地板自举率等于68比96(self):
        真名单 = FB.读地板函数名(_ROOT)
        函数节点 = FB.读地板函数节点(_ROOT)
        _data, 条目 = FB.读清单(_MANIFEST)
        问题, 统计 = FB.校验(_ROOT, 条目, 真名单, 函数节点)
        self.assertEqual(问题, [])
        self.assertEqual((统计["light_count"], 统计["denominator"]), (68, 96))
        self.assertAlmostEqual(统计["rate"], 68 / 96, places=12)

    def test_九条判型内置全部语法级可定位(self):
        _data, 条目 = FB.读清单(_MANIFEST)
        表 = {条["名字"]: 条 for 条 in 条目}
        for 名 in _判型九条:
            self.assertIn(名, 表, "判型内置 %s 不在清单里" % 名)
            self.assertEqual(表[名]["分类"], "has_light_impl",
                             "%s 的分类不是 has_light_impl" % 名)
            坏, 模块名 = FB.校验证据(_ROOT, 表[名]["证据行"], 名)
            self.assertIsNone(坏, "%s 的证据行语法级定位失败：%s" % (名, 坏))
            self.assertEqual(模块名, "内置核心判型")


class Test反跑一_旧窗口会红新定位不红(unittest.TestCase):
    """R153 场景：`段落 是字母(` 上方插 3 行注释。

    - 旧 ±2 文本窗口：证据行 61 落在注释里，±2 内无定义行 → **红**；
    - 新语法级定位：按声明名找到定义行（61 → 64），距离 3 ≤ 段落块长 → **绿**。
    """

    def _漂移文件(self, d):
        行 = _读行(os.path.join(_ROOT, *_判型文件.split("/")))
        换行 = "\r\n" if any(s.endswith("\r") for s in 行) else "\n"
        纯 = [s.rstrip("\r") for s in 行]
        新, 新定义行, 旧定义行 = _在样本段前插三行(纯, 换行)
        目标 = os.path.join(d, *_判型文件.split("/"))
        _写行(目标, 新, 换行)
        return 新, 新定义行, 旧定义行

    def test_旧窗口在漂移后失配(self):
        with tempfile.TemporaryDirectory() as d:
            新行, 新定义行, 旧定义行 = self._漂移文件(d)
            self.assertEqual(旧定义行, _是字母定义行_R157,
                             "真仓库里 `段落 是字母` 的定义行已不是 R157 对准的 %d —— "
                             "要么 `.light` 被改过，要么证据行该刷新" % _是字母定义行_R157)
            self.assertEqual(新定义行, 旧定义行 + 3, "插 3 行后定义行应下移 3")
            # 证据行仍指着 R157 那行（= 现在的注释行），旧 ±2 窗口找不到定义行
            self.assertEqual(_旧窗口命中(新行, _是字母定义行_R157, _样本名), [])

    def test_新定位在漂移后仍绿(self):
        with tempfile.TemporaryDirectory() as d:
            self._漂移文件(d)
            坏, 模块名 = FB.校验证据(d, "%s:%d" % (_判型文件, _是字母定义行_R157), _样本名)
            self.assertIsNone(坏, "新定位在 R153 场景下仍判红：%s" % 坏)
            self.assertEqual(模块名, "内置核心判型")

    def test_插行后整条门禁仍绿(self):
        """反跑①+②的核心：改回 ±2 文本窗口，这一条立刻转红。"""
        with tempfile.TemporaryDirectory() as d:
            清单 = _最小树(d, 漂移判型=True)
            # 对真基线跑棘轮判定 → 绿（不是 write-baseline 自证）
            self.assertEqual(_跑("--root", d, "--list", 清单), 0)
            # 分子不许因漂移缩水
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑("--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            self.assertEqual(_读json(基线)["light_count"], 68)

    def test_删除上方三行后仍绿(self):
        """反向漂移（删行）同样被「一个段落块长」的容差吸收。"""
        with tempfile.TemporaryDirectory() as d:
            行 = _读行(os.path.join(_ROOT, *_判型文件.split("/")))
            换行 = "\r\n" if any(s.endswith("\r") for s in 行) else "\n"
            纯 = [s.rstrip("\r") for s in 行]
            # 在文件更上方删 3 行（整段上移）—— 不是删样本段自己的注释
            新 = 纯[:20] + 纯[23:]
            目标 = os.path.join(d, *_判型文件.split("/"))
            _写行(目标, 新, 换行)
            坏, _模块名 = FB.校验证据(d, "%s:%d" % (_判型文件, _是字母定义行_R157), _样本名)
            self.assertIsNone(坏, "删行后新定位误判红：%s" % 坏)


class Test反跑三_假绿必须红(unittest.TestCase):
    """空壳冒充 `has_light_impl` / 证据指错地方 → 必须红。"""

    def _改清单(self, 改):
        数据 = _读json(_MANIFEST)
        改(数据)
        return 数据

    def test_空壳误标has_light_impl即红(self):
        """拿一条真·空壳（`movable`，没有光明实现）冒充已搬迁 → 红。"""
        def 改(数据):
            for 条 in 数据["函数"]:
                if 条["名字"] == "格式化时间":
                    条["分类"] = "has_light_impl"
                    条["证据行"] = "%s:1" % _判型文件   # 该文件里没有 `格式化时间` 的声明
                    return
            raise AssertionError("清单里找不到 `格式化时间` —— 测试自身失效")
        with tempfile.TemporaryDirectory() as d:
            清单 = _最小树(d, 清单数据=self._改清单(改))
            self.assertEqual(_跑("--root", d, "--list", 清单), 1)

    def test_证据指向远处行即红(self):
        """证据行在文件范围内、但离语法级定义行超过一个段落块长 → 红。

        这条同时是「上界断言不算判据」的反跑：只断 `1 <= 行号 <= 总行数` 会放过它。
        """
        def 改(数据):
            for 条 in 数据["函数"]:
                if 条["名字"] == _样本名:
                    条["证据行"] = "%s:1" % _判型文件     # 第 1 行是文件头注释
                    return
            raise AssertionError("清单里找不到 `%s`" % _样本名)
        with tempfile.TemporaryDirectory() as d:
            清单 = _最小树(d, 清单数据=self._改清单(改))
            self.assertEqual(_跑("--root", d, "--list", 清单), 1)

    def test_前缀同名不许互相冒充(self):
        """`段落 是空白(字符)` 不许冒充 `是空` —— 声明名必须精确相等。

        子串匹配（旧判据用的 `名字 in 行`）会让 `是空` 命中 `段落 是空白(字符)`；
        新判据抓「声明名」并做精确比较，第 73 行离 `是空` 的定义行 55 有 18 行，
        超过一个段落块长 → 红。
        """
        坏, _模块名 = FB.校验证据(_ROOT, "%s:73" % _判型文件, "是空")
        self.assertIsNotNone(坏, "`是空白` 的定义行被 `是空` 蒙过去了")


if __name__ == "__main__":
    unittest.main()
