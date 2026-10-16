# -*- coding: utf-8 -*-
"""R154-B：L-214 双轨 `是空` 根治 —— 业主裁定方案 (b)“改名 皆空”。

背景
----
宽口径 `是空`（null/`""`/`[]`/`{}`/`()`/`set()` 全算空）只存在于 `.py`
影子腿（`stdlib/lightpub/类型工具.py` 与 release 存根同名文件），而权威
`.light` 腿没有该函数、地板内置 `是空` 的权威口径仅为“null 或空字符串”。
于是同一份 `.light` 程序，加不加 `从 类型工具 导入 是空` 这一行，
`是空([])` / `是空({})` 就会从假变真——静默换口径，零提示。R153 登记为 L-214。

根治（R154，2026-10-16）
-----------------------
宽口径能力保留，原名 `是空` 彻底改名 `皆空`，彻底分名：
  * 主模块、release 存根：`def 是空` → `def 皆空`（docstring 注明口径差异）；
  * 两处 `stdlib/lightpub/__index__.py` 导出清单：`'是空'` → `'皆空'`（函数数仍 24）；
  * 两份文档（docs/api、docs/lightpub）同步改名，分歧对照表改写为“已根治记录”。
  * `.light` 腿（`stdlib_v3/类型工具.light`）经评估**不补对应段**：该文件是
    独立的 v3 模块（仅 8 个函数，与本桥接模块不同名族），补一个孤立的
    `皆空` 会混淆模块身份；改名后已不存在“同名撞口径”，评估理由见
    `_R154_B线交付报告.md`。

断言族
------
1. 源码级守：两个 .py 无宽口径 `是空` 定义、有 `皆空`；两个 index 清单同步；
   两份文档同步；.light 腿维持两无。
2. 行为探针（src 腿子进程）：`从 类型工具 导入 皆空` 拿宽口径且地板
   `是空([])` 仍为假；`从 类型工具 导入 是空` 响亮报 ImportError（不静默换口径）。
   注：原生腿不做模块解析（导模块即“未定义”），本测试只覆盖 src 腿钩子，
   与任务书 B 线要求一致。
3. release 存根与主模块函数清单/皆空函数体逐字节同步。
4. 守卫正则有牙（合成宽口径定义必被抓）。

反跑（人工，2026-10-16 已实测）
-----------------------------
把宽口径 `def 是空(值)` 加回任一 .py 文件 → 本测试源码级守由绿转红。
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_MAIN_PY = os.path.join(_ROOT, "stdlib", "lightpub", "类型工具.py")
_REL_PY = os.path.join(_ROOT, "bootstrap", "release", "stdlib",
                       "lightpub", "类型工具.py")
_MAIN_INDEX = os.path.join(_ROOT, "stdlib", "lightpub", "__index__.py")
_REL_INDEX = os.path.join(_ROOT, "bootstrap", "release", "stdlib",
                         "lightpub", "__index__.py")
_API_DOC = os.path.join(_ROOT, "docs", "api", "类型工具.md")
_LP_DOC = os.path.join(_ROOT, "docs", "lightpub", "类型工具.md")
_LIGHT_LEG = os.path.join(_ROOT, "stdlib_v3", "类型工具.light")

# 宽口径旧名定义（def 是空(）；改名后两处源码均不得命中
_WIDE_DEF = re.compile(r"^def\s+是空\s*\(", re.M)
# 新名定义
_NEW_DEF = re.compile(r"^def\s+皆空\s*\(", re.M)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _func_names(src):
    return re.findall(r"^def\s+(\w+)\s*\(", src, re.M)


def _func_body(src, name):
    m = re.search(r"^(def\s+%s\b.*?)(?=^def\s|\Z)" % re.escape(name),
                  src, re.M | re.S)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# 1. 源码级守
# ---------------------------------------------------------------------------
class R154L214_源码级守(unittest.TestCase):

    def test_两个py无宽口径旧名定义(self):
        for p in (_MAIN_PY, _REL_PY):
            s = _read(p)
            self.assertIsNone(
                _WIDE_DEF.search(s),
                "%s 仍有宽口径 `def 是空` 定义（L-214 未根治/复发）"
                % os.path.relpath(p, _ROOT))

    def test_两个py有新名皆空定义(self):
        for p in (_MAIN_PY, _REL_PY):
            s = _read(p)
            self.assertIsNotNone(
                _NEW_DEF.search(s),
                "%s 缺 `def 皆空` 定义" % os.path.relpath(p, _ROOT))

    def test_皆空实现保持宽口径能力(self):
        """改名不允许顺手改语义：宽口径类型分支（tuple/set）与 len 判定必须保留。"""
        body = _func_body(_read(_MAIN_PY), "皆空")
        self.assertIsNotNone(body)
        self.assertIn("tuple", body)
        self.assertIn("set", body)
        self.assertIn("len(值) == 0", body)

    def test_两个index导出清单已分名(self):
        for p in (_MAIN_INDEX, _REL_INDEX):
            s = _read(p)
            self.assertIn("'皆空'", s,
                          "%s 导出清单缺 '皆空'" % os.path.relpath(p, _ROOT))
            self.assertNotIn("'是空'", s,
                             "%s 导出清单仍登记 '是空'（L-214 未根治/复发）"
                             % os.path.relpath(p, _ROOT))

    def test_api文档已根治且保留历史(self):
        s = _read(_API_DOC)
        self.assertIn("皆空", s)
        self.assertIn("L-214 已根治", s)
        # 历史对照表与反跑判据不得悄悄删除
        self.assertIn("双轨", s)
        self.assertIn("反跑判据", s)
        self.assertNotIn("### `是空(值)`", s)
        self.assertNotIn("| `是空(值)`", s)

    def test_lightpub文档已改名(self):
        s = _read(_LP_DOC)
        self.assertIn("### 皆空", s)
        self.assertNotIn("### 是空", s)

    def test_light腿维持两无(self):
        """评估结论：v3 独立模块不补 皆空；也不得出现旧名。"""
        s = _read(_LIGHT_LEG)
        self.assertNotIn("是空", s)
        self.assertNotIn("皆空", s)

    def test_守卫正则有牙(self):
        """合成宽口径定义必须被守卫正则抓到——证明反跑时本文件真能变红。"""
        sample = "def 是空(值):\n    return True\n"
        self.assertIsNotNone(_WIDE_DEF.search(sample))


# ---------------------------------------------------------------------------
# 2. 行为探针（src 腿，子进程）
# ---------------------------------------------------------------------------
_PROG_NEW = (
    "从 类型工具 导入 皆空\n"
    "\n"
    "打印(皆空(空))\n"
    "打印(皆空(\"\"))\n"
    "打印(皆空([]))\n"
    "打印(皆空({}))\n"
    "打印(皆空(\"x\"))\n"
    "打印(是空([]))\n"
)

_PROG_OLD = (
    "从 类型工具 导入 是空\n"
    "\n"
    "打印(是空([]))\n"
)


def _run_src(src_text, timeout=600):
    with tempfile.TemporaryDirectory(prefix="_r154b_") as d:
        src = os.path.join(d, "main.light")
        with open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(src_text)
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, os.path.join("cli", "light.py"), "run", src],
            capture_output=True, timeout=timeout, env=env, cwd=_ROOT,
        )
    return proc


class R154L214_行为探针(unittest.TestCase):
    """src 腿真实运行，不依赖任何 scratch 探针（D 线会清理）。"""

    def test_导入皆空拿宽口径_地板是空不翻转(self):
        proc = _run_src(_PROG_NEW)
        self.assertEqual(
            proc.returncode, 0,
            "src 腿运行失败 rc=%d\nSTDERR:\n%s"
            % (proc.returncode,
               proc.stderr.decode("utf-8", "replace")[:2000]))
        lines = [ln.strip() for ln in
                 proc.stdout.decode("utf-8", "replace").splitlines()
                 if ln.strip()]
        # 皆空：null/""/[]/{} 全为真，非空字符串为假；地板内置 是空([]) 仍为假
        self.assertEqual(
            lines, ["True", "True", "True", "True", "False", "False"],
            "口径与预期不符：%r" % lines)

    def test_导入旧名响亮报错(self):
        proc = _run_src(_PROG_OLD)
        # 预期：响亮失败（运行期 ImportError），而不是静默跑通换口径
        self.assertNotEqual(
            proc.returncode, 0,
            "旧名导入竟静默跑通，可能重新落回宽口径（L-214 复发）：\n%s"
            % proc.stdout.decode("utf-8", "replace"))
        err = proc.stderr.decode("utf-8", "replace")
        self.assertIn("cannot import name '是空'", err)
        # 若万一 rc==0，下面的口径守卫必须成立（窄口径 True/False 判定）
        if proc.returncode == 0:
            out = proc.stdout.decode("utf-8", "replace").strip()
            self.assertEqual(out, "False",
                             "旧名静默落回宽口径（L-214 复发）：%r" % out)


# ---------------------------------------------------------------------------
# 3. release 存根同步
# ---------------------------------------------------------------------------
class R154L214_release存根同步(unittest.TestCase):

    def test_函数清单一致(self):
        main_names = _func_names(_read(_MAIN_PY))
        rel_names = _func_names(_read(_REL_PY))
        self.assertEqual(main_names, rel_names)
        self.assertIn("皆空", main_names)
        self.assertNotIn("是空", main_names)

    def test_皆空函数体一致(self):
        main_body = _func_body(_read(_MAIN_PY), "皆空")
        rel_body = _func_body(_read(_REL_PY), "皆空")
        self.assertIsNotNone(main_body)
        self.assertIsNotNone(rel_body)
        self.assertEqual(main_body, rel_body)


if __name__ == "__main__":
    unittest.main()
