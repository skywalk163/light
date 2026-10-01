# -*- coding: utf-8 -*-
"""自举地板清单·内部自洽断言门禁的回归用例（R108 任务线 I · 落地 R107 顺延项，卡 #307）。

## 为什么要有这个文件

`tools/ci/assert_floor_manifest.py` 守的是「`分类统计` 与 `函数[]` 两处手写口径是否
仍自洽」——这条线此前没有任何门禁（R106 §九 实测「似乎不漂」只是碰巧，一旦有人改了
一处漏了另一处就静默放行）。门禁本身必须可被反跑证明**真的会红**：把 `分类统计` 里的
`native_required` 从 62 改成 61（差 1 条），门禁必须判红并打印差异明细。

## 反跑的两种方向（与 test_ci_gates.py 同思路）

- 方向一（加漂移）：`分类统计.native_required` 62 → 61 → 红。
- 方向二（未知分类）：某条 `函数[].分类` 写成合法集合外的值 → 红。
- 方向三（基线脱节）：把 `floor_bootstrap_baseline.json` 的 `native_required_count`
  改成与清单不符 → 红。
- 方向四（三方总量）：`总数` 与 `len(函数)` 不符 → 红。

所有反跑都只在临时副本上做，**绝不改写源清单**（任务书线 G 硬约束：只读）。
"""

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MANIFEST = os.path.join(_ROOT, "任务书", "自举地板清单.json")
_BASELINE = os.path.join(_ROOT, "tools", "ci", "floor_bootstrap_baseline.json")
_CI = os.path.join(_ROOT, "tools", "ci")


def _load(name):
    """按路径加载门禁脚本：tools/ci 不是包，import 不到。"""
    path = os.path.join(_CI, name + ".py")
    spec = importlib.util.spec_from_file_location("_gate_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = _load("assert_floor_manifest")


def _跑(*argv):
    """按 CLI 口径跑一遍门禁并拿 rc。"""
    旧 = sys.argv
    sys.argv = ["gate"] + list(argv)
    try:
        return G.main()
    finally:
        sys.argv = 旧


def _读():
    with io.open(_MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


def _写临时(修改):
    """深拷贝真实清单、施加修改、落临时文件，返回路径。源清单不动。"""
    data = _读()
    修改(data)
    d = tempfile.mkdtemp()
    p = os.path.join(d, "自举地板清单副本.json")
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    return p


class Test正向通过(unittest.TestCase):
    """真实清单当前不漂 → 绿。"""

    def test_真实清单通过(self):
        self.assertEqual(_跑("--root", _ROOT), 0)

    def test_逐类计数真一致(self):
        data, 条目 = G.读清单(_MANIFEST)
        问题, 统计 = G.校验(data, 条目, json.load(io.open(_BASELINE, encoding="utf-8")))
        self.assertEqual(问题, [])
        # 分类统计 每个键都 == 实计数
        for k, v in 统计["分类统计"].items():
            self.assertEqual(v, 统计["实计数"].get(k, 0))


class Test反跑_分类统计漂移(unittest.TestCase):
    """方向一：native_required 62 → 61（差 1 条）→ 红，且打印可操作差异。"""

    def test_改61即红(self):
        副本 = _写临时(lambda d: d["分类统计"].__setitem__("native_required", 61))
        rc = _跑("--manifest", 副本, "--baseline", _BASELINE)
        self.assertEqual(rc, 1)

    def test_红时打印差异明细(self):
        副本 = _写临时(lambda d: d["分类统计"].__setitem__("native_required", 61))
        import subprocess
        r = subprocess.run(
            [sys.executable, os.path.join(_CI, "assert_floor_manifest.py"),
             "--manifest", 副本, "--baseline", _BASELINE],
            capture_output=True, text=True, encoding="utf-8")
        self.assertIn("差 +1 条", r.stdout)
        self.assertIn("分类统计登记 61 条", r.stdout)
        self.assertIn("函数[]实计 62 条", r.stdout)

    def test_还原后复跑绿(self):
        # 源清单从没被改，直接复跑真实清单必须绿（反跑只在临时副本上做）
        self.assertEqual(_跑("--root", _ROOT), 0)

    def test_多类同时漂移仍红(self):
        副本 = _写临时(lambda d: d["分类统计"].update(
            {"native_required": 60, "movable": 17, "has_light_impl": 66}))
        self.assertEqual(_跑("--manifest", 副本, "--baseline", _BASELINE), 1)


class Test反跑_未知分类(unittest.TestCase):
    """方向二：函数[].分类 出现合法集合外的值 → 红。"""

    def test_未知分类值即红(self):
        def 改(d):
            d["函数"][0]["分类"] = "尚未裁决"
        副本 = _写临时(改)
        self.assertEqual(_跑("--manifest", 副本, "--baseline", _BASELINE), 1)

    def test_空分类即红(self):
        def 改(d):
            d["函数"][0]["分类"] = ""
        副本 = _写临时(改)
        self.assertEqual(_跑("--manifest", 副本, "--baseline", _BASELINE), 1)


class Test反跑_基线脱节(unittest.TestCase):
    """方向三：CI 基线的 native_required_count / light_count 与清单不符 → 红。"""

    def test_基线native_required脱节即红(self):
        d = tempfile.mkdtemp()
        b = os.path.join(d, "b.json")
        基线 = json.load(io.open(_BASELINE, encoding="utf-8"))
        基线["native_required_count"] = 99
        with io.open(b, "w", encoding="utf-8") as fh:
            json.dump(基线, fh, ensure_ascii=False)
        # 清单真实不变 → 仍应与真实基线一致；与篡改基线比应对不上
        self.assertEqual(_跑("--root", _ROOT, "--baseline", b), 1)

    def test_基线light_count脱节即红(self):
        d = tempfile.mkdtemp()
        b = os.path.join(d, "b.json")
        基线 = json.load(io.open(_BASELINE, encoding="utf-8"))
        基线["light_count"] = 70
        with io.open(b, "w", encoding="utf-8") as fh:
            json.dump(基线, fh, ensure_ascii=False)
        self.assertEqual(_跑("--root", _ROOT, "--baseline", b), 1)


class Test反跑_三方总量(unittest.TestCase):
    """方向四：总数 / len(函数) / 分类统计求和 三者不一致 → 红。"""

    def test_总数不符即红(self):
        def 改(d):
            d["总数"] = 159
        副本 = _写临时(改)
        self.assertEqual(_跑("--manifest", 副本, "--baseline", _BASELINE), 1)

    def test_分类统计求和不符即红(self):
        # 偷偷加一条 分类 但不补进 函数[]：分类统计求和会超出 函数[] 条数
        def 改(d):
            d["分类统计"]["unused"] = 2
        副本 = _写临时(改)
        self.assertEqual(_跑("--manifest", 副本, "--baseline", _BASELINE), 1)


if __name__ == "__main__":
    unittest.main()
