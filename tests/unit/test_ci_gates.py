# -*- coding: utf-8 -*-
"""闸门脚本自身的回归用例（第四轮非阻塞项-3）。

## 为什么要有这个文件

`tools/ci/assert_quality.py` 里有两个形态是**预防性**的——全仓零命中：

- `trivial-ge0`   `assert len(x) >= 0`（长度恒非负，恒真断言）
- `returncode-in` `assert returncode in [...]`（成败都算通过）

零命中本身没问题（`docs/known_issues.md` 14.5 已声明「预防性、未拦任何存量」，
报文里也单列，不算假绿）。问题在于：**零命中 = 零证据**。谁也没验证过这两条
正则真的能拦住它要拦的东西——万一写错了，它们从「防新增」退化成一行装饰，
而退化的那天不会有任何红灯提示，因为它们本来就不亮。

同理 `tools/ci/bootstrap_rate.py::查自导入`：这是自举率的**防造假**检查
（`.light` 里转手 `导入` 同名 `.py`，等于没自举），全仓当前也是零命中。

本文件把这三处从「零命中、未验证」变成「零命中、已验证可用」。

第七轮 E7 追加两道新门禁的**双向反跑**（这两条不是零命中，但棘轮型门禁有另一个
盲区：只验「加违规判红」，不验「删基线条目也判红」——而基线是人手改的文本文件，
删一条就消红的门禁等于没有门禁）：

- `tools/ci/python_direct_calls.py`：`.light` 里 `导入 os` 后直调 `os.xxx` 的行数。
  连带钉住三条误伤边界（注释 / 多行串 / 单行串里的 `os.path.join` 都不算，
  光明模块不算，模块名被 `设 … 为` 重新绑定后不算）。
- `tools/ci/spec_coverage.py`：功能对标清单完成度（done 只升不降 + 逐条不许退回
  + 条目不许消失 + 证据文件必须存在但**行号不校验**）。
- `tools/ci/bootstrap_rate.py::scan_critical_path`：关键路径自举率子指标，
  遮蔽判定钉在「首**两行**魔数」这个边界上，与 `stdlib/_light_import_hook.py`
  的 `_is_pure_light` 同源（写死「首行」或「前十行」都会与运行期脱节，
  而那种脱节不会有任何红灯提示）。


## 判据必须是有分辨力的

每条断言都配一条「几乎一样但不该命中」的反例，钉住正则真正 key 在哪个形状上：

- `>= 0` 该拦、`>= 1` 不该拦（后者是真下界，归 `lower-bound`）
- `returncode in [...]` 该拦、`returncode == 0` 不该拦
- `X.light` 里 `导入 X` 该判造假、`导入 别的模块` 不该判、`导入 Python: X` 不该判

## 反面样例为什么放在三引号块里

`assert_quality.py::_prose_lines()` 只豁免注释与**多行**字符串；单行字符串字面量
照扫。所以样例断言写成 `code = "assert len(xs) >= 0"` 会让本文件自己变成一条
门禁违规，逼人把它写进基线。统一塞进下面这个三引号块，从块里取。
"""

import importlib.util
import os
import sys
import tempfile
import unittest

_CI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools", "ci",
)


def _load(name):
    """按路径加载闸门脚本：tools/ci 不是包，import 不到。"""
    path = os.path.join(_CI_DIR, name + ".py")
    spec = importlib.util.spec_from_file_location("_gate_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AQ = _load("assert_quality")
BR = _load("bootstrap_rate")
PD = _load("python_direct_calls")
SC = _load("spec_coverage")


def _跑(mod, *argv):
    """按 CLI 口径跑一遍门禁并拿 rc：门禁的判绿语义只有 main() 说得准。

    单测正则「拦不拦」只能证明形态对，证不了「整条门禁会不会红」——
    第四轮踩过的就是这个（形态在、门禁没拦）。所以这里直接过 main()。
    """
    旧 = sys.argv
    sys.argv = ["gate"] + list(argv)
    try:
        return mod.main()
    finally:
        sys.argv = 旧

# label|code —— 见模块 docstring 末段：必须留在三引号块内。
_SAMPLES = """
ge0|    assert len(xs) >= 0
ge1|    assert len(xs) >= 1
gt0|    assert len(xs) > 0
rc_in|    assert returncode in [0, 1]
rc_eq|    assert returncode == 0
"""

S = dict(line.split("|", 1) for line in _SAMPLES.strip().splitlines())


class TestTrivialGe0(unittest.TestCase):
    """恒真断言式：`assert len(x) >= 0`。

    （这段写成多行不是排版洁癖：`_prose_lines()` 只豁免多行字符串，
    单行 docstring 里出现这个写法会让本文件自己被门禁点名。）
    """


    def test_命中(self):
        self.assertTrue(AQ.RE_TRIVIAL_GE.search(S["ge0"]))
        # 合并正则也必须收——scan_tree 先过 RE_MASTER，漏在这里等于整条形态失效
        self.assertTrue(AQ.RE_MASTER.search(S["ge0"]))

    def test_不误伤真下界(self):
        # `>= 1` / `> 0` 是真下界，归 lower-bound；被 trivial-ge0 吃掉会让报文分类失真
        self.assertIsNone(AQ.RE_TRIVIAL_GE.search(S["ge1"]))
        self.assertIsNone(AQ.RE_TRIVIAL_GE.search(S["gt0"]))
        self.assertTrue(AQ.RE_LOWER_BOUND.search(S["ge1"]))
        self.assertTrue(AQ.RE_LOWER_BOUND.search(S["gt0"]))


class TestReturncodeIn(unittest.TestCase):
    """成败都算通过：`assert returncode in [...]`。

    同上，多行是必须的（单行 docstring 不在 `_prose_lines()` 的豁免范围里）。
    """


    def test_命中(self):
        self.assertTrue(AQ.RE_RETURNCODE_IN.search(S["rc_in"]))
        self.assertTrue(AQ.RE_MASTER.search(S["rc_in"]))

    def test_不误伤确定值断言(self):
        # `== 0` 断的是确定结果，有真信号，不该进基线
        self.assertIsNone(AQ.RE_RETURNCODE_IN.search(S["rc_eq"]))
        self.assertIsNone(AQ.RE_MASTER.search(S["rc_eq"]))


class TestScanTreeEndToEnd(unittest.TestCase):
    """整条 scan_tree 打通：不只是正则对，分类落到哪个桶也要对。"""

    def _扫(self, 文本):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "probe_case.py"), "w", encoding="utf-8") as fh:
                fh.write(文本)
            found = AQ.scan_tree(d)
        return {cat: len(v) for cat, v in found.items() if v}

    def test_两个预防性形态各归各桶(self):
        文本 = "def f(xs, returncode):\n" + S["ge0"] + "\n" + S["rc_in"] + "\n"
        self.assertEqual(self._扫(文本), {"trivial-ge0": 1, "returncode-in": 1})

    def test_反例不产生任何命中(self):
        文本 = "def f(returncode):\n" + S["rc_eq"] + "\n"
        self.assertEqual(self._扫(文本), {})

    def test_预防性形态仍在名录里(self):
        # 报文单列靠这个元组；被人顺手删掉的话两条形态会混进存量统计
        self.assertEqual(AQ.PREVENTIVE, ("trivial-ge0", "returncode-in"))

    def test_编译器生成的py整份豁免(self):
        """首行 `# 由光明编译器生成` 的文件不扫（第六轮口径裁决）。

        这些文件的内容由 src/code_generator.py 决定，作者是编译器不是人；
        当成人写的测试来判假测试，只会让「测试里编译一份真文件」变成
        必须记得写临时目录的地雷。
        """
        文本 = ("# " + AQ.GENERATED_MARK + "\n"
                "def f(xs, returncode):\n" + S["ge0"] + "\n" + S["rc_in"] + "\n")
        self.assertEqual(self._扫(文本), {})

    def test_标记不在首行则照扫(self):
        """反向守护：豁免只认首行，不许拿这句注释当免死金牌插在文件中间。"""
        文本 = ("def f(xs, returncode):\n"
                "# " + AQ.GENERATED_MARK + "\n" + S["ge0"] + "\n" + S["rc_in"] + "\n")
        self.assertEqual(self._扫(文本), {"trivial-ge0": 1, "returncode-in": 1})



class Test查自导入(unittest.TestCase):
    """自举率防造假：`.light` 里转手导入同名 `.py`。"""

    def _建(self, 目录, 文件名, 文本):
        p = os.path.join(目录, 文件名)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(文本)
        return p

    def test_自导入命中(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = self._建(d, "甲.light", "导入 甲。\n段落 主：\n")
            命中 = BR.查自导入(p, "甲")
        self.assertEqual([行号 for 行号, _ in 命中], [1])

    def test_导入别的模块不算造假(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = self._建(d, "甲.light", "导入 乙。\n段落 主：\n")
            self.assertEqual(BR.查自导入(p, "甲"), [])

    def test_引外语库不算造假(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            # `导入 Python: 甲` 是引外语库，不是段言模块自导入
            p = self._建(d, "甲.light", "导入 Python: 甲\n段落 主：\n")
            self.assertEqual(BR.查自导入(p, "甲"), [])

    def test_读不到文件抬错而不是当没造假(self):
        # 第四轮回补点：原实现 `except OSError: pass`，读失败静默算「干净」，
        # 方向偏向放行。防造假检查失效必须判红。
        with self.assertRaises(OSError):
            BR.查自导入(os.path.join(_CI_DIR, "不存在的文件.light"), "甲")

    def test_造假文件不计入自举(self):
        # 整条 scan_stdlib 打通：命中造假的文件即便有 decl 也不算「有实现」
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            stdlib = os.path.join(d, "stdlib")
            os.makedirs(stdlib)
            self._建(stdlib, "甲.light", "导入 甲。\n段落 主：\n")
            self._建(stdlib, "乙.light", "段落 主：\n")
            r = BR.scan_stdlib(d)
        self.assertEqual(r["stdlib_light_total"], 2)
        self.assertEqual(r["stdlib_light_has_impl"], 1)      # 只有 乙
        self.assertEqual([h["file"] for h in r["fake_hits"]], ["stdlib/甲.light"])


# ── 第七轮 E7：两道新门禁的双向反跑 ─────────────────────────────────────────
#
# 「加违规判红」是一半，「删基线条目也判红」是另一半。只做前一半的门禁有个
# 现成的绕过路径：把基线里那条删掉，红就没了——而基线是人手改的文本文件。
#
# .light 样例同样必须留在三引号块里（`_prose_lines()` 不豁免单行字符串）。
_LIGHT样例 = {
    "直调": """导入 os
段落 主：
  设 路径 为 os.path.join("甲", "乙")
  返回 路径
""",
    "注释与串里不算": """导入 os
# os.path.join("这是注释，不该判红")
段落 主：
  设 说明 为 \"\"\"多行串里写 os.path.join(a, b) 当反面教材
  第二行也提一次 os.makedirs(d)，照样不该判红\"\"\"
  设 单行 为 "os.listdir(d) 在单行串里也不算"
  返回 说明
""",
    "光明模块不算": """从 JSON 导入 解析JSON
导入 JSON
段落 主：
  返回 JSON.解析JSON("[]")
""",
    "重绑定不算": """导入 os
段落 主：
  设 os 为 ["path": 1]
  返回 os.path
""",
}


class TestPython直调计数(unittest.TestCase):
    """`导入 os` 后直调 `os.xxx` 的行数——六轮来没有任何门禁数过这条通道。"""

    def _树(self, d, **文件):
        os.makedirs(os.path.join(d, "stdlib"), exist_ok=True)
        for 名, 文本 in 文件.items():
            with open(os.path.join(d, 名 + ".light"), "w", encoding="utf-8") as fh:
                fh.write(文本)

    def test_真直调计一行(self):
        with tempfile.TemporaryDirectory() as d:
            self._树(d, 甲=_LIGHT样例["直调"])
            per_file, details, _排除, _模块 = PD.scan_tree(d)
        self.assertEqual(per_file, {"甲.light": 1})
        self.assertEqual([(行, 名) for 行, 名, _t in details["甲.light"]], [(3, "os")])

    def test_注释与多行串里不判红(self):
        with tempfile.TemporaryDirectory() as d:
            self._树(d, 甲=_LIGHT样例["注释与串里不算"])
            per_file, _详, _排除, _模块 = PD.scan_tree(d)
        # 反面教材写在注释/字符串里是正当的，纯正则会误伤成违规
        self.assertEqual(per_file, {})

    def test_光明模块不算逃逸(self):
        with tempfile.TemporaryDirectory() as d:
            self._树(d, 甲=_LIGHT样例["光明模块不算"])
            with open(os.path.join(d, "stdlib", "JSON.light"), "w",
                      encoding="utf-8") as fh:
                fh.write("段落 解析JSON 接收 文本：\n  返回 []\n")
            per_file, _详, 排除, _模块 = PD.scan_tree(d)
        self.assertEqual(per_file, {})
        self.assertEqual([名 for 名, _因 in 排除["甲.light"]], ["JSON"])

    def test_模块名被重新绑定后不算(self):
        with tempfile.TemporaryDirectory() as d:
            self._树(d, 甲=_LIGHT样例["重绑定不算"])
            per_file, _详, 排除, _模块 = PD.scan_tree(d)
        self.assertEqual(per_file, {})
        self.assertEqual([名 for 名, _因 in 排除["甲.light"]], ["os"])

    def test_双向反跑(self):
        with tempfile.TemporaryDirectory() as d:
            self._树(d, 甲=_LIGHT样例["直调"])
            基线 = os.path.join(d, "python_direct_baseline.json")
            self.assertEqual(_跑(PD, "--root", d, "--write-baseline", 基线), 0)
            # 基线内、无改动 → 绿
            self.assertEqual(_跑(PD, "--root", d, "--baseline", 基线), 0)
            # 方向一：加一行 os.path.join → 红
            with open(os.path.join(d, "甲.light"), "a", encoding="utf-8") as fh:
                fh.write("段落 又一处：\n  返回 os.path.join(\"丙\", \"丁\")\n")
            self.assertEqual(_跑(PD, "--root", d, "--baseline", 基线), 1)
            # 方向二：把基线条目删掉想消红 → 照样红（棘轮不认手改）
            import json as _json
            with open(基线, encoding="utf-8") as fh:
                data = _json.load(fh)
            data["files"] = {}
            data["total"] = 0
            with open(基线, "w", encoding="utf-8") as fh:
                _json.dump(data, fh, ensure_ascii=False)
            self.assertEqual(_跑(PD, "--root", d, "--baseline", 基线), 1)

    def test_基线自相矛盾即红(self):
        # 防手改：total 与 files 之和不符，说明有人只改了总数
        with tempfile.TemporaryDirectory() as d:
            self._树(d, 甲=_LIGHT样例["直调"])
            基线 = os.path.join(d, "b.json")
            import json as _json
            with open(基线, "w", encoding="utf-8") as fh:
                _json.dump({"total": 99, "files": {"甲.light": 1}}, fh,
                           ensure_ascii=False)
            self.assertEqual(_跑(PD, "--root", d, "--baseline", 基线), 1)


class Test关键路径自举率(unittest.TestCase):
    """遮蔽判定必须按当前机制：首**两行**含魔数才取代同名 `.py`。"""

    def _建(self, stdlib, 名, 文本, 带py=False):
        with open(os.path.join(stdlib, 名 + ".light"), "w", encoding="utf-8") as fh:
            fh.write(文本)
        if 带py:
            with open(os.path.join(stdlib, 名 + ".py"), "w", encoding="utf-8") as fh:
                fh.write("# 影子\n")

    def test_四种形态各归其位(self):
        with tempfile.TemporaryDirectory() as d:
            stdlib = os.path.join(d, "stdlib")
            os.makedirs(stdlib)
            self._建(stdlib, "甲", "段落 主：\n  返回 1\n")                       # 计入
            self._建(stdlib, "乙", "段落 主：\n  返回 1\n", 带py=True)            # 被遮蔽
            self._建(stdlib, "丙", "# 纯光明实现\n段落 主：\n  返回 1\n", 带py=True)  # 取代
            self._建(stdlib, "丁", "导出 甲。\n")                                # decl 0
            # 魔数在第 3 行 → 钩子看不见（它只读两行），不算取代
            self._建(stdlib, "戊", "# 一\n# 二\n# 纯光明实现\n段落 主：\n  返回 1\n",
                     带py=True)
            r = BR.scan_critical_path(d, ["甲", "乙", "丙", "丁", "戊", "缺失"])
        计入 = {x["模块"]: x["计入"] for x in r["critical_path_detail"]}
        self.assertEqual(计入, {"甲": True, "乙": False, "丙": True,
                               "丁": False, "戊": False, "缺失": False})
        self.assertEqual((r["critical_path_has_impl"], r["critical_path_total"]),
                         (2, 6))

    def test_清单删条目判红(self):
        # 清单可增不可删：删掉做不到的那条 = 把指标改成自己能过的样子
        with tempfile.TemporaryDirectory() as d:
            stdlib = os.path.join(d, "stdlib")
            os.makedirs(stdlib)
            self._建(stdlib, "甲", "段落 主：\n  返回 1\n")
            import json as _json
            清单 = os.path.join(d, "modules.json")
            基线 = os.path.join(d, "bootstrap_rate_baseline.json")
            with open(清单, "w", encoding="utf-8") as fh:
                _json.dump({"模块": ["甲", "乙"]}, fh, ensure_ascii=False)
            旧清单 = BR._关键路径清单
            try:
                BR._关键路径清单 = 清单
                self.assertEqual(_跑(BR, "--root", d, "--write-baseline", 基线), 0)
                self.assertEqual(_跑(BR, "--root", d, "--baseline", 基线), 0)
                with open(清单, "w", encoding="utf-8") as fh:
                    _json.dump({"模块": ["甲"]}, fh, ensure_ascii=False)  # 删掉 乙
                self.assertEqual(_跑(BR, "--root", d, "--baseline", 基线), 1)
            finally:
                BR._关键路径清单 = 旧清单

    def test_魔数口径与钩子同源(self):
        """`_是纯光明` 读的行数必须与 stdlib/_light_import_hook.py 一致。

        钩子读的是 `fh.readline() + fh.readline()`（两行）。这里钉住边界：
        第 2 行算、第 3 行不算——写死「首行」或「前十行」都会让子指标与运行期
        真实行为脱节，那种脱节不会有任何红灯提示。
        """
        with tempfile.TemporaryDirectory() as d:
            p2 = os.path.join(d, "二.light")
            p3 = os.path.join(d, "三.light")
            with open(p2, "w", encoding="utf-8") as fh:
                fh.write("# 头\n# 纯光明实现\n段落 主：\n")
            with open(p3, "w", encoding="utf-8") as fh:
                fh.write("# 头\n# 中\n# 纯光明实现\n段落 主：\n")
            self.assertTrue(BR._是纯光明(p2))
            self.assertFalse(BR._是纯光明(p3))


_清单样例 = {
    "编号": 1,
    "功能": "样例功能",
    "状态": "done",
    "证据": ["证据.light:1-2"],
    "本轮目标": "保持",
    "备注": "",
}


class Test功能对标清单(unittest.TestCase):
    """完成度门禁：done 只升不降、逐条不许退回、证据文件必须存在。"""

    def _写(self, d, 条目):
        import json as _json
        os.makedirs(os.path.join(d, "任务书"), exist_ok=True)
        p = os.path.join(d, "任务书", "功能对标清单_harness.json")
        with open(p, "w", encoding="utf-8") as fh:
            _json.dump({"条目": 条目}, fh, ensure_ascii=False)
        return p

    def _备(self, d):
        with open(os.path.join(d, "证据.light"), "w", encoding="utf-8") as fh:
            fh.write("段落 主：\n  返回 1\n")

    def test_双向反跑(self):
        with tempfile.TemporaryDirectory() as d:
            self._备(d)
            清单 = self._写(d, [dict(_清单样例)])
            基线 = os.path.join(d, "spec_coverage_baseline.json")
            self.assertEqual(_跑(SC, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            self.assertEqual(_跑(SC, "--root", d, "--list", 清单,
                                "--baseline", 基线), 0)
            # 方向一：done 退成 none（带备注，schema 合规）→ 完成度掉了，红
            退 = dict(_清单样例)
            退["状态"] = "none"
            退["备注"] = "本轮不做"
            self._写(d, [退])
            self.assertEqual(_跑(SC, "--root", d, "--list", 清单,
                                "--baseline", 基线), 1)
            # 方向二：条目整条删掉想消红 → 照样红（基线编号必须还在）
            留 = dict(_清单样例)
            留["编号"] = 2
            self._写(d, [留])
            self.assertEqual(_跑(SC, "--root", d, "--list", 清单,
                                "--baseline", 基线), 1)

    def test_done没证据即红(self):
        with tempfile.TemporaryDirectory() as d:
            无证 = dict(_清单样例)
            无证["证据"] = []
            清单 = self._写(d, [无证])
            self.assertEqual(_跑(SC, "--root", d, "--list", 清单), 1)

    def test_证据文件不存在即红(self):
        with tempfile.TemporaryDirectory() as d:
            清单 = self._写(d, [dict(_清单样例)])   # 没建 证据.light
            self.assertEqual(_跑(SC, "--root", d, "--list", 清单), 1)

    def test_none缺备注即红(self):
        with tempfile.TemporaryDirectory() as d:
            self._备(d)
            无备 = dict(_清单样例)
            无备["状态"] = "none"
            无备["备注"] = "   "
            清单 = self._写(d, [无备])
            self.assertEqual(_跑(SC, "--root", d, "--list", 清单), 1)

    def test_状态值域外即红(self):
        with tempfile.TemporaryDirectory() as d:
            self._备(d)
            怪 = dict(_清单样例)
            怪["状态"] = "基本完成"
            清单 = self._写(d, [怪])
            self.assertEqual(_跑(SC, "--root", d, "--list", 清单), 1)

    def test_行号漂移不判红(self):
        """证据只校验文件存在，不校验行号——行号会随任何编辑漂移。"""
        with tempfile.TemporaryDirectory() as d:
            self._备(d)
            漂 = dict(_清单样例)
            漂["证据"] = ["证据.light:99999"]      # 文件只有两行
            清单 = self._写(d, [漂])
            self.assertEqual(_跑(SC, "--root", d, "--list", 清单,
                                "--write-baseline",
                                os.path.join(d, "b.json")), 0)


if __name__ == "__main__":
    unittest.main()
