# -*- coding: utf-8 -*-
"""stdlib 原生腿就绪度指标单元测试（下界式判据，多模块编译口径）。

判据纪律（总纲反复强调）：不许只断言「比例 >= 某个易达数字」——那样把模块换成
空壳也照样绿。这里三层钉死：
  1. 基线文件不变式：三桶合计 == 魔数模块总数；rate == 可编/总数；
     魔数模块总数有下界（缩水即红，空壳化先掉总数）。
  2. 名单下界：_下界可编模块 里的真实模块（R117 多模块口径基线实测可编）
     必须在基线「可编」桶里——这些模块任何一个掉出可编桶，闸门即红。
  3. 真编译下界：对 _下界可编模块 逐个真跑 --sample（子进程 + 超时），
     当场必须编过——不依赖基线是否被人改坏。

跑法（本仓 venv python）：
  .venv/Scripts/python.exe -m pytest tests/unit/test_llvm_stdlib_readiness.py -o addopts="" -q
"""

import json
import os
import subprocess
import sys
import unittest

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_TOOL = os.path.join(_ROOT, "tools", "ci", "llvm_stdlib_readiness.py")
_BASELINE = os.path.join(_ROOT, "tools", "ci", "llvm_stdlib_readiness_baseline.json")

# 下界钉死：真实模块名，R117 多模块口径基线实测在「可编」桶。
# 前五个是 R115 首跑就编过的稳定核心 + 大模块（拼音转换 2800+ 条字典设置）；
# 后四个是 R117 修口径后由「明确拒绝」翻正的真模块（原卡在跨模块导入的「未定义的段落」上）。
_下界可编模块 = ["Base64", "哈希", "列表工具", "拼音转换", "JSON核心",
                "JSON", "数学", "文件系统", "正则表达式"]
_魔数模块总数下界 = 70  # 2026-10-05 实测 73；只许增不许减，缩水即红


def _load_baseline():
    with open(_BASELINE, encoding="utf-8") as fh:
        return json.load(fh)


def _sample(name):
    """真跑工具 --sample，返回 (rc, stdout)。子进程 + 超时，防大模块拖死 pytest。"""
    proc = subprocess.run(
        [sys.executable, _TOOL, "--sample", name, "--timeout", "300"],
        capture_output=True, timeout=660, cwd=_ROOT,
    )
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


class TestBaseline不变式(unittest.TestCase):
    """基线文件结构 + 不变式（快，无编译）。"""

    def test_基线文件存在且结构完整(self):
        self.assertTrue(os.path.isfile(_BASELINE), "基线文件缺失：%s" % _BASELINE)
        b = _load_baseline()
        for key in ("compile_entry", "total", "ready", "rejected", "other", "rate", "buckets"):
            self.assertIn(key, b, "基线缺字段 %s" % key)
        self.assertEqual(b["compile_entry"], "compile_light_typed(多模块)")
        for bucket in ("可编", "明确拒绝", "其它错误"):
            self.assertIn(bucket, b["buckets"], "基线三桶缺 %s" % bucket)

    def test_三桶合计等于魔数模块总数(self):
        b = _load_baseline()
        total_buckets = sum(len(v) for v in b["buckets"].values())
        self.assertEqual(total_buckets, b["total"],
                         "三桶合计 %d != 魔数模块总数 %d" % (total_buckets, b["total"]))

    def test_就绪度数值自洽(self):
        b = _load_baseline()
        self.assertAlmostEqual(b["rate"], b["ready"] / b["total"], places=9,
                               msg="rate 与 可编/总数 不一致")

    def test_魔数模块总数下界(self):
        b = _load_baseline()
        self.assertGreaterEqual(b["total"], _魔数模块总数下界,
                                "魔数模块总数 %d 低于下界 %d——模块被删/空壳化先掉总数"
                                % (b["total"], _魔数模块总数下界))

    def test_下界模块必须在可编桶里(self):
        b = _load_baseline()
        ready = set(b["buckets"]["可编"])
        for name in _下界可编模块:
            self.assertIn(name, ready,
                          "模块「%s」掉出可编桶——就绪度回退，先查该模块是否被改坏" % name)


class Test真编译下界(unittest.TestCase):
    """真跑 --sample 当场编译（每个模块一个子进程 + 超时，不依赖基线）。"""

    @pytest.mark.timeout(900)  # R117 改多模块编译口径：9 个下界模块真编译合计远超全局 60s，放宽到 900s
    def test_下界模块当场编过(self):
        for name in _下界可编模块:
            with self.subTest(模块=name):
                rc, out = _sample(name)
                self.assertEqual(rc, 0, "工具 --sample %s 退出码 %d" % (name, rc))
                self.assertIn("桶：可编", out,
                              "模块「%s」当场编译未进可编桶，输出：\n%s" % (name, out))

    def test_sample找无魔数模块返回2(self):
        rc, out = _sample("不存在的模块xyz")
        self.assertEqual(rc, 2, "--sample 找不到模块应返回 2，实测 %d" % rc)
        self.assertIn("找不到魔数模块", out)


if __name__ == "__main__":
    unittest.main()
