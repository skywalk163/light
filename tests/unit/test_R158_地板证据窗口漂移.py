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

- **正向**：真仓库跑 floor 门禁 RC=0；地板自举率等于基线快照（`light_count` /
  `denominator` 从 `tools/ci/floor_bootstrap_baseline.json` 读，**不写死数字** ——
  R158 上线后清单补条目、基线在合并点正常上棘轮，写死快照的门禁自己先红，教训见
  T-0214）；9 条判型内置全部登记 `has_light_impl`，且证据经语法级定位校验通过。
- **反跑①**（顶得住 R153 那类注释增厚）：在 `段落 是字母(` 上方插 3 行注释后，
  整条 floor 门禁仍 RC=0 且 `light_count` 仍等于基线；**同一份漂移文件**用旧 ±2
  窗口复算会红。若有人把 `floor_bootstrap.py` 改回 ±2 文本窗口，本类立即转红。
- **反跑②**（整树端到端）：`--root` 指向漂移树，门禁对真基线 RC=0、`light_count`
  等于基线。
- **反跑③**（防假绿，两形）：(a) 把一条 `movable` 真·空壳改成 `has_light_impl` 并把
  证据指向一个**没有该声明**的文件 → RC=1；(b) 证据行指向**有该声明但相距超过一个
  段落块长**的远处行 → RC=1（这条同时是「上界断言不算判据」的反跑）。

所有反跑都在临时目录里做，**绝不改写仓库里的清单与 `.light` 源**（任务书线 G 硬约束）。

## T-0280 补强（只加断言，不刷新任何数字）

R158/T-0214 已把写死的 `68/96` 换成从 `floor_bootstrap_baseline.json` 动态取数，
把 `段落 是字母` 的写死行号（R157 手工对准时 61、后来漂到 73）换成
`FB.定位定义行` 按声明名现算 —— 所以本文件在未改动 HEAD 上已是 0 红（10 passed），
卡面描述的「4 条红」在当前仓库已不存在，**不需要、也没有去刷新任何数字**。
本轮补的是卡面目标 2/3 里此前仍未落地、且不削弱任何既有断言的三件事，
见 `Test分母来源与同步守卫`：

- 分母**来源**：用 `ast` 独立再数一遍 `stdlib/builtins.py` 顶层函数数（门禁
  `FB.读地板函数名` 也用 ast；两边独立解析，防止门禁与基线被同时手改却互相印证）。
- 分母**计算方式**：钉 `denominator = total − native_required_count` 与
  `rate = light_count / denominator` 的口径，而不是钉某个数字。
- **分母变化必须同步更新**的反向哨兵：临时副本加一个顶层 `def` → 实统计 +1 →
  分母必变 → 基线没动就会被 `test_地板自举率等于基线快照` 判红，不许拿新数字自证。
  刷新办法：只在合并点 `python tools/ci/floor_bootstrap.py --write-baseline ...`
  重建基线（总纲 §5 红线 5），禁止手改数字。
- 行号**来源**：钉成「按声明名现算」而非快照；不同声明名必须定位到不同行。

与 T-0278 的约定：它补内置实现走 `_t5b_runtime.py` 通道、**不加顶层 def**，
故这里的 `total` 在并行期间不应变化；若它最终加了顶层 def，来源守卫会红 ——
按卡面第 4 条点名冲突，不靠互相迁就着改数字消红。
"""

import ast
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
_BASELINE = os.path.join(_ROOT, "tools", "ci", "floor_bootstrap_baseline.json")
_BUILTINS = os.path.join(_ROOT, "stdlib", "builtins.py")

# 判型内置：R157-E9 的 9 条现场（也是 R153 注释增厚的重灾区）。
_判型九条 = ("是字母", "是数字", "是空", "是空白", "是布尔",
            "是函数", "是数值", "字符串全数字", "是负零")
# 反跑用的样本：`段落 是字母(` 的定义行上方插行，最直接地复现 R153 场景。
_样本名 = "是字母"
_判型文件 = "stdlib/内置核心判型.light"
# T-0214 教训：定义行锚点（原 `_是字母定义行_R157 = 61`）写死会随 `.light` 演进漂移
# （R158 上线后不久就漂到 73，4 条红全是它引起的）。一律用语法级定位现算。
# 旧漂移窗口（行）——R158 之前的判据，复刻它只为证明「改回去就会红」。
_旧窗口 = 2


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


def _现算定义行(名字):
    """真仓库判型文件里 `名字` 的定义行 —— 语法级定位现算，不写死快照值。"""
    行 = [s.rstrip("\r") for s in _读行(os.path.join(_ROOT, *_判型文件.split("/")))]
    定义行, _缩 = FB.定位定义行(FB.声明行表(行), 名字, 1)
    if 定义行 is None:
        raise AssertionError("声明 `%s` 在 %s 里找不到 —— 测试自身失效" % (名字, _判型文件))
    return 定义行


# 「漂移前」的锚点：现算值（R157 手工对准时是 61，后来漂到 73 —— 写死就红）。
_是字母定义行 = _现算定义行(_样本名)
# 反跑三「前缀同名」的证据行：`是空白` 的定义行含 `是空` 子串但声明名精确不等。
_是空白定义行 = _现算定义行("是空白")


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
    """真清单 + 真 `.light` + 真基线 → 绿，且自举率与基线快照一致。"""

    def test_门禁在真仓库上通过(self):
        self.assertEqual(_跑("--root", _ROOT), 0)

    def test_地板自举率等于基线快照(self):
        """比率判据从基线 JSON 读，不写死：基线在合并点上棘轮，门禁跟着走。"""
        基线 = _读json(_BASELINE)
        真名单 = FB.读地板函数名(_ROOT)
        函数节点 = FB.读地板函数节点(_ROOT)
        _data, 条目 = FB.读清单(_MANIFEST)
        问题, 统计 = FB.校验(_ROOT, 条目, 真名单, 函数节点)
        self.assertEqual(问题, [])
        self.assertEqual((统计["light_count"], 统计["denominator"]),
                         (基线["light_count"], 基线["denominator"]))
        self.assertAlmostEqual(统计["rate"],
                               基线["light_count"] / 基线["denominator"], places=12)

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

    - 旧 ±2 文本窗口：证据行（漂移前的定义行）落进注释里，±2 内无定义行 → **红**；
    - 新语法级定位：按声明名找到定义行（下移 3 行），距离 3 ≤ 段落块长 → **绿**。
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
            self.assertEqual(旧定义行, _是字母定义行,
                             "插行前现算定义行与模块级锚点不一致 —— 测试自身失效")
            self.assertEqual(新定义行, 旧定义行 + 3, "插 3 行后定义行应下移 3")
            # 证据行仍指着漂移前那行（= 现在的注释行），旧 ±2 窗口找不到定义行
            self.assertEqual(_旧窗口命中(新行, _是字母定义行, _样本名), [])

    def test_新定位在漂移后仍绿(self):
        with tempfile.TemporaryDirectory() as d:
            self._漂移文件(d)
            坏, 模块名 = FB.校验证据(d, "%s:%d" % (_判型文件, _是字母定义行), _样本名)
            self.assertIsNone(坏, "新定位在 R153 场景下仍判红：%s" % 坏)
            self.assertEqual(模块名, "内置核心判型")

    def test_插行后整条门禁仍绿(self):
        """反跑①+②的核心：改回 ±2 文本窗口，这一条立刻转红。"""
        with tempfile.TemporaryDirectory() as d:
            清单 = _最小树(d, 漂移判型=True)
            # 对真基线跑棘轮判定 → 绿（不是 write-baseline 自证）
            self.assertEqual(_跑("--root", d, "--list", 清单), 0)
            # 分子不许因漂移缩水：仍等于真基线的 light_count
            基线路径 = os.path.join(d, "b.json")
            self.assertEqual(_跑("--root", d, "--list", 清单,
                                "--write-baseline", 基线路径), 0)
            self.assertEqual(_读json(基线路径)["light_count"],
                             _读json(_BASELINE)["light_count"])

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
            坏, _模块名 = FB.校验证据(d, "%s:%d" % (_判型文件, _是字母定义行), _样本名)
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
        新判据抓「声明名」并做精确比较，`是空白` 的定义行（现算，不写死）离
        `是空` 的定义行超过一个段落块长 → 红。
        """
        坏, _模块名 = FB.校验证据(_ROOT, "%s:%d" % (_判型文件, _是空白定义行), "是空")
        self.assertIsNotNone(坏, "`是空白` 的定义行被 `是空` 蒙过去了")


class Test分母来源与同步守卫(unittest.TestCase):
    """T-0280 补强：把「分母从哪来、怎么算、变了要同步」钉成可执行判据。

    本类**只增加断言**，不删除/削弱任何既有判据、不 skip、不写死任何快照数字，
    也不改被测源码。卡面目标 2/3 里「来源 + 计算方式 + 分母变化同步守卫 +
    按名字定位」此前只在 docstring 里说明，没有可执行判据；这里补齐。
    """

    @staticmethod
    def _独立顶层函数数(源=None):
        """不经门禁、独立用 ast 数 `stdlib/builtins.py` 顶层函数数。

        与 `FB.读地板函数名` 分两次解析：门禁与基线被同时手改时，单靠门禁
        自己的读数会互相印证成假绿，独立解析才是分母来源的硬证据。
        """
        with io.open(源 or _BUILTINS, encoding="utf-8") as fh:
            树 = ast.parse(fh.read())
        return sum(1 for 节点 in 树.body
                   if isinstance(节点, (ast.FunctionDef, ast.AsyncFunctionDef)))

    def test_分母来源是builtins顶层函数数(self):
        基线 = _读json(_BASELINE)
        独立数 = self._独立顶层函数数()
        门禁名单 = FB.读地板函数名(_ROOT)
        _数据, 条目 = FB.读清单(_MANIFEST)
        问题, 统计 = FB.校验(_ROOT, 条目, 门禁名单, FB.读地板函数节点(_ROOT))
        self.assertEqual(问题, [])
        self.assertEqual(独立数, len(门禁名单),
                         "独立 ast 与门禁 ast 数不一致 —— 分母来源被污染")
        self.assertEqual(统计["total"], 独立数,
                         "清单条目数与源码顶层函数数不一致")
        self.assertEqual(基线["total"], 独立数,
                         "基线 total 与 stdlib/builtins.py 顶层函数数不一致：分母来源变了，"
                         "必须只在合并点用 --write-baseline 重建基线，不许手改数字")
        # 钉计算方式，不钉数字：分母 = 总数 − native_required 真边界数
        self.assertEqual(基线["denominator"],
                         基线["total"] - 基线["native_required_count"],
                         "基线分母不是 total − native_required_count —— 口径被改或基线自相矛盾")

    def test_自举率按分子除以分母计算(self):
        基线 = _读json(_BASELINE)
        _数据, 条目 = FB.读清单(_MANIFEST)
        门禁名单 = FB.读地板函数名(_ROOT)
        问题, 统计 = FB.校验(_ROOT, 条目, 门禁名单, FB.读地板函数节点(_ROOT))
        self.assertEqual(问题, [])
        self.assertEqual(统计["denominator"],
                         统计["total"] - 统计["native_required_count"])
        self.assertAlmostEqual(统计["rate"],
                               统计["light_count"] / 统计["denominator"], places=12)
        self.assertAlmostEqual(基线["rate"],
                               基线["light_count"] / 基线["denominator"], places=12)
        self.assertGreater(统计["denominator"], 0, "分母为零则比率判据失去意义")

    def test_分母变化必须同步更新_反向哨兵(self):
        """A/B 实证：源码加一个顶层 def → 分母来源 +1，基线没动就会对不上（守卫会红）。

        同时验证「清单没同步时门禁必须报漏登记」，不许静默把新分母吞掉自证过关。
        副本只落在临时目录，绝不改写仓库里的清单 / builtins.py / `.light`。
        """
        基线 = _读json(_BASELINE)
        原数 = self._独立顶层函数数()
        with tempfile.TemporaryDirectory() as d:
            副本 = os.path.join(d, "builtins.py")
            shutil.copy(_BUILTINS, 副本)
            with io.open(副本, "a", encoding="utf-8", newline="\n") as fh:
                fh.write("\ndef T0280_分母哨兵_临时函数():\n    return 1\n")
            新数 = self._独立顶层函数数(副本)
            self.assertEqual(新数, 原数 + 1, "哨兵没被数进去 —— 反跑自身失效")
            self.assertEqual(基线["total"], 原数)
            self.assertNotEqual(基线["total"], 新数,
                                "源码加了顶层 def 后基线 total 竟仍匹配 —— "
                                "「分母变化必须同步更新」守卫失去判别力")
            # 门禁自己的 ast 口径也必须跟着 +1（不是只有独立解析看得见）
            副本名单 = FB.读地板函数名(_ROOT, 源=副本)
            self.assertEqual(len(副本名单), 新数)
            # 清单没同步 → 校验必须报「漏登记/防腐烂」，不许静默通过
            _数据, 条目 = FB.读清单(_MANIFEST)
            问题, _统计 = FB.校验(_ROOT, 条目, 副本名单,
                              FB.读地板函数节点(_ROOT, 源=副本))
            self.assertTrue(any("防腐烂" in q or "清单里没有" in q for q in 问题),
                            "源码多一个顶层 def、清单没补，门禁却没报漏登记：%s" % 问题)

    def test_定义行按声明名现算而非写死(self):
        """行号来源：锚点必须是「按声明名」现算，不是 61/73 之类快照。"""
        行 = [s.rstrip("\r") for s in _读行(os.path.join(_ROOT, *_判型文件.split("/")))]
        表 = FB.声明行表(行)
        现算, _ = FB.定位定义行(表, _样本名, 1)
        self.assertIsNotNone(现算, "真仓库里按名字定位不到样本声明 —— 测试自身失效")
        self.assertEqual(_是字母定义行, 现算,
                         "模块级锚点不是按声明名现算的 —— 又被写死成快照了")
        self.assertNotEqual(_是字母定义行, _是空白定义行,
                            "不同声明名定位到同一行 —— 定位没按名字区分")
        # 反跑①：把声明改名，按原名字必须找不到（精确匹配，不靠行号/子串）
        改名 = [s.replace("段落 是字母(", "段落 是字母已改名(") for s in 行]
        self.assertIsNone(FB.定位定义行(FB.声明行表(改名), _样本名, 1)[0],
                          "声明已改名仍按旧名定位成功 —— 定位不是按声明名精确匹配")
        # 反跑②：插 3 行后现算值必须下移 3（写死快照做不到）
        新行, _新定义行, _旧定义行 = _在样本段前插三行(行, "\n")
        现算2, _ = FB.定位定义行(FB.声明行表([s.rstrip("\r") for s in 新行]),
                              _样本名, 1)
        self.assertEqual(现算2, 现算 + 3,
                         "插 3 行后定义行没下移 3 —— 现算被写死了")


if __name__ == "__main__":
    unittest.main()
