# -*- coding: utf-8 -*-
"""第九轮 G9 三道新门禁的双向反跑（地板 / 原生产品 / 分布式判据）。

## 为什么要有这个文件

棘轮型门禁有两个盲区，只做一半的门禁等于没有门禁：

1. 只验「加违规判红」，不验「删基线条目也判红」—— 基线是人手改的文本文件，
   删一条就消红的门禁拦不住任何人。
2. 只验「有判据」，不验「判据有分辨力」—— 第七轮 B7 原稿断的是
   「1 ≤ 行号 ≤ 文件总行数」，四千行文件里任何数字都过。**上界断言是假绿主形态。**

所以本文件每条断言都配一条「几乎一样但不该命中」的反例，钉住判据真正 key 在
哪个形状上：

- 地板：证据行号在 `±2` 窗口内该过、在窗口外（但仍在文件范围内）**不该过**
- 地板：落点带同名 `.py` 且无魔数不该算搬迁（运行期跑的是那个 `.py`）
- 地板：`native_required` 名单新增即红 —— 否则把做不动的函数挪进豁免就能凭空涨点
- 原生：源码 `--backend` 新增取值没登记该红；表里有源码已无的取值只该告警（摘除
  死腿是许可处置，不该被拦）
- 分布式：`反跑` 写「有」不算反跑，指向不存在的文件也不算

## 反面样例为什么塞在三引号块 / 模块级常量里

`tools/ci/assert_quality.py::_prose_lines()` 只豁免注释与**多行**字符串，单行字符串
字面量照扫。样例写成 `code = "assert x >= 0"` 会让本文件自己变成门禁违规。
同理所有 docstring 都写成多行 —— 单行 docstring 会被 `assert_quality` 点名。
"""

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

_CI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools", "ci",
)


def _load(name):
    """按路径加载闸门脚本。

    `tools/ci` 不是包，import 不到；与 `tests/unit/test_ci_gates.py` 同一套加载法。
    """
    path = os.path.join(_CI_DIR, name + ".py")
    spec = importlib.util.spec_from_file_location("_g9gate_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FB = _load("floor_bootstrap")
NP = _load("native_product")
DC = _load("dist_criteria")


def _跑(mod, *argv):
    """按 CLI 口径跑一遍门禁并拿 rc。

    单测「校验函数返回了几条问题」只能证明形态对，证不了整条门禁会不会红
    （第四轮踩过：形态在、门禁没拦）。所以一律过 `main()`。
    """
    旧 = sys.argv
    sys.argv = ["gate"] + list(argv)
    try:
        return mod.main()
    finally:
        sys.argv = 旧


def _写json(path, data):
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _读json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _写文本(path, 文本):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(文本)


# ── 地板自举率 ────────────────────────────────────────────────────────────

_假地板 = """# -*- coding: utf-8 -*-
def 甲():
    import 内置核心
    return 内置核心.甲()


def 乙():
    return 2
"""

# 落点样例：`段落 甲` 在第 4 行。第 20 行远在 ±2 窗口之外，但仍在文件范围内 ——
# 这正是「上界断言」会放过、真判据必须拦下的形状。
_落点 = """# 纯光明实现
# 头两行挂魔数才能取代同名 .py

段落 甲：
  返回 1

段落 乙：
  返回 2

# 下面是填充行，把文件撑长，好让「行号在文件范围内」这种弱判据露出破绽
# 3
# 4
# 5
# 6
# 7
# 8
# 9
# 10
# 11
# 12
# 13
"""


def _地板条(名, 分类="movable", 落点="", 证据行=""):
    """C9 版清单的条目形状（S1 合并点裁决：结构以清单所有权方 C9 为准）。"""
    return {
        "名字": 名,
        "职责": "样例职责",
        "当前实现语言": "Python（builtins.py）",
        "分类": 分类,
        "目标落点": 落点 or ("真边界：样例" if 分类 == "native_required" else ""),
        "证据行": 证据行,
    }


def _已搬迁条(名="甲"):
    """已就位且 builtins.py 真转发到 内置核心.light 的条目 → 计入分子。"""
    return _地板条(名, "has_light_impl", "stdlib/内置核心.light",
                   "stdlib/内置核心.light:4")


class Test地板自举率(unittest.TestCase):
    """地板自举率门禁：名单咬合 + 证据可定位 + 豁免不许扩张。
    """

    def _树(self, d, 条目, 落点文本=_落点, 带影子=False, 影子有魔数=True):
        os.makedirs(os.path.join(d, "stdlib"), exist_ok=True)
        os.makedirs(os.path.join(d, "任务书"), exist_ok=True)
        _写文本(os.path.join(d, "stdlib", "builtins.py"), _假地板)
        文本 = 落点文本
        if 带影子 and not 影子有魔数:
            文本 = 落点文本.replace("# 纯光明实现", "# 普通注释", 1)
        _写文本(os.path.join(d, "stdlib", "内置核心.light"), 文本)
        if 带影子:
            _写文本(os.path.join(d, "stdlib", "内置核心.py"), "# 影子\n")
        清单 = os.path.join(d, "任务书", "自举地板清单.json")
        _写json(清单, {"函数": 条目})
        return 清单

    def test_名单双向咬合(self):
        with tempfile.TemporaryDirectory() as d:
            缺基线 = os.path.join(d, "不存在的基线.json")
            # 方向一：builtins.py 有 乙、清单只登记 甲 → 红（防腐烂）
            清单 = self._树(d, [_地板条("甲")])
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--baseline", 缺基线), 1)
            # 方向二：清单多写一个代码里没有的 丙 → 红（防吹牛）
            _写json(清单, {"函数": [_地板条("甲"), _地板条("乙"), _地板条("丙")]})
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--baseline", 缺基线), 1)
            # 逐个相等 → 校验通过（此时只差基线，rc=2 而非 1）
            _写json(清单, {"函数": [_地板条("甲"), _地板条("乙")]})
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--baseline", 缺基线), 2)

    def test_证据必须落在定义行的窗口内(self):
        with tempfile.TemporaryDirectory() as d:
            条 = _已搬迁条("甲")
            清单 = self._树(d, [条, _地板条("乙")])
            基线 = os.path.join(d, "b.json")
            # 行号正指 `段落 甲` 那一行 → 过
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            self.assertEqual(_读json(基线)["light_count"], 1)
            # ±2 窗口内（第 6 行 vs 定义在第 4 行）→ 仍过，留给正常编辑漂移
            条["证据行"] = "stdlib/内置核心.light:6"
            _写json(清单, {"函数": [条, _地板条("乙")]})
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--baseline", 基线), 0)

    def test_行号在文件内但不在窗口内即红(self):
        """这条是「上界断言不算判据」的反跑。

        第 20 行确实满足 `1 <= 行号 <= 总行数`，B7 原稿那种弱判据会放过它；
        真判据必须红，因为那一行没有任何 `段落 甲`。
        """
        with tempfile.TemporaryDirectory() as d:
            条 = _已搬迁条("甲")
            条["证据行"] = "stdlib/内置核心.light:20"
            清单 = self._树(d, [条, _地板条("乙")])
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单), 1)

    def test_被同名py遮蔽的落点不算搬迁(self):
        with tempfile.TemporaryDirectory() as d:
            # 有同名 .py 但首两行挂了魔数 → 取代成立，算搬迁
            清单 = self._树(d, [_已搬迁条("甲"), _地板条("乙")],
                            带影子=True, 影子有魔数=True)
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--write-baseline", os.path.join(d, "b.json")), 0)
        with tempfile.TemporaryDirectory() as d:
            # 同样的实现，只是魔数没了 → 运行期跑的是 .py，判红
            清单 = self._树(d, [_已搬迁条("甲"), _地板条("乙")],
                            带影子=True, 影子有魔数=False)
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单), 1)

    def test_替身就位但builtins没转发_不计入分子(self):
        """S1 合并点裁决的核心反跑（任务书/地板清单裁决_S1.md §4）。

        `乙` 在 内置核心.light 里有真 `段落 乙`，但 builtins.py 的 乙 还是
        `return 2` —— 运行期跑的仍是 Python，所以不算搬迁，分子只有 甲。
        """
        with tempfile.TemporaryDirectory() as d:
            乙 = _地板条("乙", "has_light_impl", "stdlib/内置核心.light",
                        "stdlib/内置核心.light:7")
            清单 = self._树(d, [_已搬迁条("甲"), 乙])
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            b = _读json(基线)
            self.assertEqual((b["light_count"], b["denominator"]), (1, 2))

    def test_豁免新增即红且分母不许缩(self):
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d, [_已搬迁条("甲"), _地板条("乙")])
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            b = _读json(基线)
            self.assertEqual((b["denominator"], b["native_required_count"]), (2, 0))
            # 把 乙 挪进豁免：分母 2→1，比例 50%→100%，看着是进步，实为缩分母
            _写json(清单, {"函数": [_已搬迁条("甲"),
                                   _地板条("乙", "native_required")]})
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--baseline", 基线), 1)

    def test_自举率退回即红(self):
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d, [_已搬迁条("甲"), _地板条("乙")])
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            # 甲 退回 movable（等于把搬迁记账撤了）→ 分子 1→0
            _写json(清单, {"函数": [_地板条("甲"), _地板条("乙")]})
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单,
                                "--baseline", 基线), 1)

    def test_豁免必须写理由(self):
        with tempfile.TemporaryDirectory() as d:
            条 = _地板条("甲", "native_required")
            条["目标落点"] = "   "
            清单 = self._树(d, [条, _地板条("乙")])
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单), 1)

    def test_未分类的空判红(self):
        """`--sync-list` 补进来的新条目 `分类` 是空串。

        留空等于分母口径没定，必须逼人做裁决而不是默默放过。
        """
        with tempfile.TemporaryDirectory() as d:
            条 = _地板条("甲")
            条["分类"] = ""
            清单 = self._树(d, [条, _地板条("乙")])
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单), 1)

    def test_sync只增不改(self):
        """sync 覆盖已有条目就会抹平 C9 填的搬迁进度，所以必须只增不改。
        """
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d, [_已搬迁条("甲")])
            self.assertEqual(_跑(FB, "--root", d, "--list", 清单, "--sync-list"), 0)
            条目 = {c["名字"]: c for c in _读json(清单)["函数"]}
            # 中文名不按字面序断言（`乙` 的码位小于 `甲`），只断集合
            self.assertEqual(set(条目), {"甲", "乙"})
            self.assertEqual(条目["甲"]["证据行"], "stdlib/内置核心.light:4")
            self.assertEqual(条目["甲"]["分类"], "has_light_impl")
            self.assertEqual(条目["乙"]["分类"], "")


# ── 原生腿产品清单 ────────────────────────────────────────────────────────

_假CLI = """import argparse


def build():
    p = argparse.ArgumentParser()
    p.add_argument('--backend', choices=['src', 'llvm-typed'], default='src')
    return p
"""


def _模块条(名, 状态="未实测", 证据="", 阻断=""):
    return {"模块": 名, "状态": 状态, "阻断原因": 阻断, "证据": 证据, "备注": "样例"}


def _CLI条(路径, 取值, 状态, 证据="", 备注="样例"):
    return {"路径": 路径, "后端取值": 取值, "状态": 状态, "证据": 证据, "备注": 备注}


def _格(平台, 能力, 状态, 证据=""):
    return {"平台": 平台, "能力": 能力, "状态": 状态, "证据": 证据, "备注": "样例"}


class Test原生腿产品清单(unittest.TestCase):
    """三张表：模块咬合、后端取值覆盖、三条棘轮。
    """

    def _树(self, d, 模块表=None, CLI表=None, 矩阵=None, 模块文件=("甲", "乙")):
        os.makedirs(os.path.join(d, "stdlib"), exist_ok=True)
        os.makedirs(os.path.join(d, "任务书"), exist_ok=True)
        for 名 in 模块文件:
            _写文本(os.path.join(d, "stdlib", 名 + ".light"), "段落 主：\n  返回 1\n")
        _写文本(os.path.join(d, "cli", "light.py"), _假CLI)
        data = {
            "模块表": 模块表 if 模块表 is not None
                      else [_模块条(名) for 名 in 模块文件],
            "CLI路径表": CLI表 if CLI表 is not None else [
                _CLI条("light run --backend src", "src", "可用", "tests/x.py"),
                _CLI条("light run --backend llvm-typed", "llvm-typed", "未实测"),
            ],
            "平台矩阵": 矩阵 if 矩阵 is not None else [
                _格("Windows", "socket", "已实测通过", "tests/x.py"),
                _格("Linux", "socket", "未实测"),
            ],
        }
        清单 = os.path.join(d, "任务书", "原生腿产品清单.json")
        _写json(清单, data)
        return 清单

    def test_模块表双向咬合(self):
        with tempfile.TemporaryDirectory() as d:
            # 方向一：stdlib 有 乙.light、表里没登记 → 红
            清单 = self._树(d, 模块表=[_模块条("甲")])
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单), 1)
            # 方向二：表里写个 stdlib 里不存在的 丙 → 红
            _写json(清单, dict(_读json(清单),
                             模块表=[_模块条("甲"), _模块条("乙"), _模块条("丙")]))
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单), 1)

    def test_源码新增后端取值必须登记(self):
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d)
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            # B9 给 choices 加了 native 却没在表里记账 → 红
            _写文本(os.path.join(d, "cli", "light.py"),
                   _假CLI.replace("'src', 'llvm-typed'",
                                  "'src', 'llvm-typed', 'native'"))
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单,
                                "--baseline", 基线), 1)

    def test_源码摘除后端取值只告警不判红(self):
        """摘掉死腿是本轮许可的处置（总纲 S1「修或删，二选一」）。

        摘掉之后 `坏` 计数下降是真进步，不该被反向检查拦住。
        """
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d, CLI表=[
                _CLI条("light run --backend src", "src", "可用", "tests/x.py"),
                _CLI条("light run --backend llvm-typed", "llvm-typed", "未实测"),
                _CLI条("light run --backend llvm", "llvm", "坏", "src/x.py",
                       "引用不存在的 runtime.c"),
            ])
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            self.assertEqual(_读json(基线)["cli_broken"], 1)
            # 源码里本来就没有 llvm 这个取值（表里有、源码无）→ 告警，仍绿
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单,
                                "--baseline", 基线), 0)

    def test_坏路径数只降不升(self):
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d)
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            data = _读json(清单)
            data["CLI路径表"].append(
                _CLI条("light run --backend src -X", "src", "坏", "src/x.py", "新死腿"))
            _写json(清单, data)
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单,
                                "--baseline", 基线), 1)

    def test_平台矩阵未实测只降不升(self):
        """这条专治「只在 Windows 测过就声称跨平台」。
        """
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d)
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            data = _读json(清单)
            data["平台矩阵"].append(_格("macOS", "TLS", "未实测"))
            _写json(清单, data)
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单,
                                "--baseline", 基线), 1)

    def test_可编译比例退回即红(self):
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d, 模块表=[
                _模块条("甲", "可编译", "light compile --backend llvm-typed 甲.light"),
                _模块条("乙"),
            ])
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            _写json(清单, dict(_读json(清单),
                              模块表=[_模块条("甲"), _模块条("乙")]))
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单,
                                "--baseline", 基线), 1)

    def test_可编译必须带可复跑命令(self):
        with tempfile.TemporaryDirectory() as d:
            # 空证据 → 红
            清单 = self._树(d, 模块表=[_模块条("甲", "可编译"), _模块条("乙")])
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单), 1)
            # 有证据但不是可复跑的 light 命令 → 红
            _写json(清单, dict(_读json(清单),
                              模块表=[_模块条("甲", "可编译", "我试过了"),
                                    _模块条("乙")]))
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单), 1)

    def test_状态值域外即红(self):
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d, 模块表=[_模块条("甲", "基本可编译"), _模块条("乙")])
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单), 1)

    def test_不可编译必须写阻断原因(self):
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d, 模块表=[_模块条("甲", "不可编译"), _模块条("乙")])
            self.assertEqual(_跑(NP, "--root", d, "--list", 清单), 1)


# ── 分布式判据清单 ────────────────────────────────────────────────────────

_九条 = ("分发", "心跳", "重派", "幂等", "背压", "限流",
        "取消传播", "结果汇聚", "故障隔离")


def _判据条(能力, 状态="none", 判据="", 反跑="", 备注="样例记账"):
    return {
        "能力": 能力,
        "状态": 状态,
        "判据": 判据,
        "反跑": 反跑,
        "本阶段目标": "样例目标",
        "备注": 备注,
    }


class Test分布式判据(unittest.TestCase):
    """核心不是「有没有测试」，而是「有没有能立红的反跑」。
    """

    def _树(self, d, 条目=None):
        os.makedirs(os.path.join(d, "任务书"), exist_ok=True)
        _写文本(os.path.join(d, "tests", "test_分发.py"),
               "def test_分发():\n    pass\n")
        清单 = os.path.join(d, "任务书", "分布式判据清单.json")
        _写json(清单, {"条目": 条目 if 条目 is not None
                              else [_判据条(名) for 名 in _九条]})
        return 清单

    def _全绿条目(self):
        条目 = [_判据条(名) for 名 in _九条]
        条目[0] = _判据条("分发", "done", "tests/test_分发.py:1",
                        "把 tests/test_分发.py:2 的 assert 三个节点条数之和 改成 只断总数>0，"
                        "该用例立红")
        return 条目

    def test_done需要可定位判据与可复跑反跑(self):
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d, self._全绿条目())
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            self.assertEqual(_读json(基线)["done_count"], 1)

    def test_反跑为空即红(self):
        with tempfile.TemporaryDirectory() as d:
            条目 = self._全绿条目()
            条目[0]["反跑"] = ""
            清单 = self._树(d, 条目)
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单), 1)

    def test_反跑没有动作词即红(self):
        """「见测试里的说明」这种话不算反跑 —— 它没说改哪一行会让判据变红。

        动作词是粗判据：「注释」既可能是动作（注释掉那一行）也可能是名词
        （见注释），后者会漏判。宁可漏判也不误伤，真出现时在评审里点出来。
        """
        with tempfile.TemporaryDirectory() as d:
            条目 = self._全绿条目()
            条目[0]["反跑"] = "见 tests/test_分发.py 里的说明"
            清单 = self._树(d, 条目)
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单,
                                "--baseline", os.path.join(d, "无.json")), 1)

    def test_反跑指向不存在的文件即红(self):
        with tempfile.TemporaryDirectory() as d:
            条目 = self._全绿条目()
            条目[0]["反跑"] = "把 tests/不存在.py:3 的断言改成恒真"
            清单 = self._树(d, 条目)
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单), 1)

    def test_判据行号越界即红(self):
        with tempfile.TemporaryDirectory() as d:
            条目 = self._全绿条目()
            条目[0]["判据"] = "tests/test_分发.py:9999"
            清单 = self._树(d, 条目)
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单), 1)

    def test_none缺备注即红(self):
        with tempfile.TemporaryDirectory() as d:
            条目 = [_判据条(名) for 名 in _九条]
            条目[3]["备注"] = "  "
            清单 = self._树(d, 条目)
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单), 1)

    def test_状态值域外即红(self):
        with tempfile.TemporaryDirectory() as d:
            条目 = [_判据条(名) for 名 in _九条]
            条目[0]["状态"] = "基本可用"
            清单 = self._树(d, 条目)
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单), 1)

    def test_双向反跑_删能力与done退回都判红(self):
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d, self._全绿条目())
            基线 = os.path.join(d, "b.json")
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单,
                                "--write-baseline", 基线), 0)
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单,
                                "--baseline", 基线), 0)
            # 方向一：done 退回 partial → 红
            条目 = self._全绿条目()
            条目[0]["状态"] = "partial"
            _写json(清单, {"条目": 条目})
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单,
                                "--baseline", 基线), 1)
            # 方向二：把做不到的那条能力整条删掉想消红 → 照样红
            _写json(清单, {"条目": [c for c in self._全绿条目()
                                  if c["能力"] != "故障隔离"]})
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单,
                                "--baseline", 基线), 1)

    def test_巡检清单打印每条反跑(self):
        """S2/S3 合并点靠这份输出人工复跑，空了也要说清是真空还是漏了。
        """
        with tempfile.TemporaryDirectory() as d:
            清单 = self._树(d, self._全绿条目())
            self.assertEqual(_跑(DC, "--root", d, "--list", 清单,
                                "--print-inspection",
                                "--write-baseline", os.path.join(d, "b.json")), 0)


# ── 真仓库上的活体检查 ────────────────────────────────────────────────────

class Test真清单在册(unittest.TestCase):
    """三张新清单必须真在仓库里，且与当前源码咬合。

    这几条不吃临时目录：门禁在 CI 上跑的是真仓库，清单被删/被改歪要在这里就红，
    而不是等到 CI 的门禁段。
    """

    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def test_三张清单都在任务书目录下(self):
        for 名 in ("自举地板清单.json", "原生腿产品清单.json", "分布式判据清单.json"):
            p = os.path.join(self._ROOT, "任务书", 名)
            self.assertTrue(os.path.isfile(p), "清单不见了：任务书/%s" % 名)
            # 放 docs/ 会被 tests/unit/doc_block_scan.py 扫，这条边界要钉住
            self.assertFalse(os.path.isfile(os.path.join(self._ROOT, "docs", 名)),
                             "清单不许放 docs/：%s" % 名)

    def test_地板清单与builtins咬合(self):
        真 = set(FB.读地板函数名(self._ROOT))
        _data, 条目 = FB.读清单(os.path.join(self._ROOT, "任务书", "自举地板清单.json"))
        self.assertEqual({c["名字"] for c in 条目}, 真)

    def test_模块表与stdlib咬合(self):
        data = NP.读清单(os.path.join(self._ROOT, "任务书", "原生腿产品清单.json"))
        self.assertEqual({c["模块"] for c in data["模块表"]},
                         set(NP.实际模块名(self._ROOT)))

    def test_分布式九条能力齐(self):
        _data, 条目 = DC.读清单(
            os.path.join(self._ROOT, "任务书", "分布式判据清单.json"))
        self.assertEqual({c["能力"] for c in 条目}, set(_九条))

    def _真产品清单(self):
        return NP.读清单(os.path.join(self._ROOT, "任务书", "原生腿产品清单.json"))

    def test_CLI路径表与源码后端取值双向咬合(self):
        """门禁对「表里有、源码已无」只告警（裁决见
        `test_源码摘除后端取值只告警不判红`），于是清单腐烂在门禁输出里只是一行字：
        B9 把 `--backend llvm` 从 `cli/light.py` 的 choices 摘掉之后，清单里那条
        `坏` 记账在真仓库上留了整整一轮没人清。这条断言把那行告警在**真仓库**上
        钉成红，同时一个字不改门禁的 warn 语义（临时目录那几条反跑照旧）。
        """
        data = self._真产品清单()
        _问题, 统计 = NP.校验(self._ROOT, data)
        self.assertEqual(统计["backend_已摘除"], [],
                         "CLI路径表登记了 cli/light.py 里已无的后端取值："
                         "要么那条路径其实还活着（去修），要么整条挪进 已摘除CLI路径")
        表取值 = set()
        for 条 in data["CLI路径表"]:
            表取值.update(条["后端取值"])
        # 连等号一起断：只断一个方向的话，两个集合可以各自漂而门禁只喊其中一边
        self.assertEqual(表取值, set(NP.源码后端取值(self._ROOT)))

    def test_已摘除归档不许藏活着的后端(self):
        """`已摘除CLI路径` 是历史账归档区，不是豁免名单。

        把一条**仍在** `choices` 里的坏路径挪进归档，`cli_broken` 会凭空掉一格 ——
        那是白名单式消警。门禁的正向检查（源码有、表里无 → 红）拦的是「不登记」，
        这条拦的是「登记到归档里」。
        `llvm` 必须留在归档里：它的历史账不许被悄悄删掉。哪天真把 llvm 复活成可用
        后端，改的人得同时动这条断言 —— 那正是应该走一次的显式裁决。
        """
        data = self._真产品清单()
        choices = set(NP.源码后端取值(self._ROOT))
        归档 = set()
        for 条 in data.get("已摘除CLI路径") or []:
            for m in NP._RE_后端取值.finditer(str(条.get("命令", ""))):
                归档.update(t.strip() for t in m.group(1).split("/") if t.strip())
        self.assertIn("llvm", 归档)
        self.assertEqual(归档 & choices, set())


if __name__ == "__main__":
    unittest.main()
