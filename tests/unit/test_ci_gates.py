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


if __name__ == "__main__":
    unittest.main()
