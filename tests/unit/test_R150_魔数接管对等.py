# -*- coding: utf-8 -*-
"""L-212 护栏：带魔数的 `stdlib/X.light` 必须与同名 `X.py` **函数级对等**。

## 这个缺陷长什么样（为什么需要这个门）

`_light_import_hook` 的规则是：`stdlib/X.light` **首两行**含魔数「纯光明实现」→ 运行期
用它接管同名 `X.py`。若 `.light` 的定义集合**小于** `.py`，被接管后那部分函数就
**凭空消失**——不报 ImportError，只在真正调用时才 AttributeError，是**静默降级**。

R149 补跑 0.82 权威门时实证：

    >>> import stdlib; __import__('stdlib.文件系统', fromlist=['x']).__file__
    '...\\stdlib\\文件系统.light'                 # ← 拿到的不是 .py
    >>> hasattr(fs, '文件锁定'), hasattr(fs, '文件状态')
    (False, False)

全仓共 **3 个模块 109 个函数**在运行期不可达（`数学` 56 / `JSON` 45 / `文件系统` 8）。
R150-A 修掉 `文件锁定`/`文件解锁` 2 个 → 当前余 **107**（R151 各线补齐后 `扫描缺口` 复测现状=0，`已知缺口` 已清空，门进入「退役警戒」态）。

⛔ 为什么之前没人发现：本机判绿口径是 `tests/unit/`，顶层 `tests/` 自 R125 起没 gate 过。

## 这个门怎么工作

登记 `已知缺口`（本文件常量），然后两条断言：

1. **现状缺口 ⊆ 已知缺口** → 出现清单外的新增缺口即红（**这是防复发点**）；
2. **已知缺口里不许残留已补齐项** → 补齐之后必须把这行删掉，
   否则清单会变成永久白洗条。清单长度就是剩余债，肉眼可见地在缩短。

反跑自证见 `Test反跑_门有牙`：造一棵临时 stdlib 树，验证
(a) 多一个缺口会被报出来；(b) 无魔数的 `.light` 不被误判。
"""
import ast
import io
import os
import re
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STDLIB = os.path.join(_ROOT, "stdlib")

_RE_段落 = re.compile(r"^段落\s+([^\s(（:：]+)")

# ---------------------------------------------------------------------------
# 已知缺口（唯一维护点：补齐一个就从这里删一个）
# ---------------------------------------------------------------------------
# L-212 收口（R151）：数学 56 + JSON 45 + 文件系统 6 = 107 个运行期不可达函数，
# 经 A/B/C/D 各线补齐后，`扫描缺口` 已确认 现状=0（见本文件 test_现状缺口不得超出登记 /
# test_登记里不许残留已补齐项）。本账本已退役：清单长度=剩余债，债归零即清空。
# ⚠️ 若日后某 stdlib/X.light 又出现「带魔数接管但缺函数」的静默降级，
#    重新在此登记对应模块与函数名，门即恢复牙口。
已知缺口 = {}


def 是纯光明(path):
    """魔数判据：首两行含「纯光明实现」（与 bootstrap_rate.py 同口径）。"""
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        head = "".join(fh.readlines()[:2])
    return "纯光明实现" in head


def py顶层函数(py_path):
    with io.open(py_path, encoding="utf-8", errors="replace") as fh:
        try:
            tree = ast.parse(fh.read())
        except SyntaxError:
            return set()
    return {n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def light顶层段落(lt_path):
    out = set()
    with io.open(lt_path, encoding="utf-8", errors="replace") as fh:
        for ln in fh.read().splitlines():
            m = _RE_段落.match(ln)
            if m:
                out.add(m.group(1))
    return out


def 扫描缺口(stdlib_dir):
    """返回 {模块名: set(运行期不可达的函数名)}。

    只查「含魔数 + 有同名 .py」的组合——那才是会被静默接管、且接管不全的场景。
    """
    缺口 = {}
    for fn in sorted(os.listdir(stdlib_dir)):
        if not fn.endswith(".light"):
            continue
        lt = os.path.join(stdlib_dir, fn)
        py = os.path.join(stdlib_dir, fn[:-len(".light")] + ".py")
        if not os.path.isfile(py) or not 是纯光明(lt):
            continue
        缺 = py顶层函数(py) - light顶层段落(lt)
        if 缺:
            缺口[fn[:-len(".light")]] = 缺
    return 缺口


class TestL212护栏(unittest.TestCase):

    def test_现状缺口不得超出登记(self):
        """清单外的新增缺口即红 —— 这条是整个 L-212 的防复发点。"""
        现状 = 扫描缺口(_STDLIB)
        越界 = {}
        for 模块, 缺 in sorted(现状.items()):
            登记 = 已知缺口.get(模块, set())
            多 = sorted(缺 - 登记)
            if 多:
                越界[模块] = 多
        self.assertEqual(越界, {},
                         "运行期被魔数 .light 接管后消失的函数里，有未登记的：%s\n"
                         "要么补进 stdlib/%s.light，要么写理由补进 `已知缺口` 并登记任务。"
                         % (越界, "<模块>"))

    def test_登记里不许残留已补齐项(self):
        """补齐之后必须删账 —— 防「登记清单」退化成永久白洗条。"""
        现状 = 扫描缺口(_STDLIB)
        已补齐 = {}
        for 模块, 登记 in sorted(已知缺口.items()):
            现存 = 现状.get(模块, set())
            残留 = sorted(登记 - 现存)
            if 残留:
                已补齐[模块] = 残留
        self.assertEqual(已补齐, {},
                         "这些登记项其实已经补齐了，请把它们从 `已知缺口` 里删掉"
                         "（清单长度 = 剩余债，必须随补齐而缩短）：%s" % 已补齐)

    def test_扫描与登记总数一致(self):
        """收口态（R151）：L-212 债已归零，`已知缺口` 已清空。

        旧版要求 `assertTrue(现状)`（上界断言：扫描必须看见真实债，否则门恒绿）。
        那条断言的失败信息自己写着「L-212 已修完？那就该删掉这个门了」——
        债归零正是它要我们做的：退役该上界断言。

        保留「扫描缺口总数 == 已知缺口登记总数」这一不变量，确保扫描口径没坏、
        且门不会因债归零而悄悄恒绿。真正的防复发点改由
        `test_现状缺口不得超出登记` 承担：现状 ⊆ 空登记 ⇒ 任何清单外新增缺口立刻红。
        """
        现状 = 扫描缺口(_STDLIB)
        扫描数 = sum(len(v) for v in 现状.values())
        登记数 = sum(len(v) for v in 已知缺口.values())
        self.assertEqual(扫描数, 登记数,
                         "扫描到的缺口总数与登记不一致：\n扫描=%s\n登记=%s"
                         % ({k: len(v) for k, v in sorted(现状.items())},
                            {k: len(v) for k, v in sorted(已知缺口.items())}))


class Test反跑_门有牙(unittest.TestCase):
    """反跑：证明这个门真的会红，而不是恒真的装饰品。"""

    def _造树(self, 魔数=True, 段落名=None):
        d = tempfile.mkdtemp(prefix="_r150_l212_")
        sd = os.path.join(d, "stdlib")
        os.makedirs(sd)
        名字 = "某测试模块"
        head = "# 纯光明实现 —— 测试用\n#\n" if 魔数 else "# 普通光明模块\n#\n"
        with io.open(os.path.join(sd, 名字 + ".light"), "w", encoding="utf-8") as f:
            f.write(head + (("段落 %s():\n  返回 1\n" % 段落名) if 段落名 else "段落 甲():\n  返回 1\n"))
        with io.open(os.path.join(sd, 名字 + ".py"), "w", encoding="utf-8") as f:
            f.write("def 甲():\n    return 1\n\n\ndef 乙():\n    return 2\n")
        return d, sd, 名字

    def test_多一个缺口会被报出来(self):
        d, sd, 名字 = self._造树(魔数=True)
        try:
            缺口 = 扫描缺口(sd)
            self.assertIn(名字, 缺口, "带魔数且缺 乙 —— 门必须报出来")
            self.assertEqual(缺口[名字], {"乙"})
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_无魔数的light不算接管(self):
        """反向：没有魔数 → 钩子不接管 → 不构成 L-212 风险，不该被扫出来。"""
        d, sd, _ = self._造树(魔数=False)
        try:
            self.assertEqual(扫描缺口(sd), {},
                             "无魔数的 .light 不应被计入（它不会接管同名 .py）")
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_补齐后即从扫描结果消失(self):
        d, sd, 名字 = self._造树(魔数=True, 段落名="甲")
        try:
            with io.open(os.path.join(sd, 名字 + ".light"), "w", encoding="utf-8") as f:
                f.write("# 纯光明实现 —— 测试用\n#\n"
                        "段落 甲():\n  返回 1\n段落 乙():\n  返回 2\n")
            self.assertNotIn(名字, 扫描缺口(sd),
                             "补齐 乙 之后这个模块就不该再出现在缺口里")
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
