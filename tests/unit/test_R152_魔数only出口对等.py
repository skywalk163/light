# -*- coding: utf-8 -*-
"""R152-E1 护栏：补上「**带魔数 + 无同名 `.py`**」模块的扫描盲区。

## 这个盲区长什么样（为什么需要这个门）

R150 的 `test_R150_魔数接管对等.py` 只查「**含魔数 + 有同名 `.py`**」的组合——
因为它防的是「`.light` 接管 `.py` 后函数凭空消失」。

但还有一整类模块是 `.light` 带魔数、**同名 `.py` 已被删除**（纯光明模块的终态）。
这类模块：

* 没有 `.py` 可以对照 ⇒ R150 的门**永远扫不到它**；
* 语义缺一大截也**不会有任何门报警**——这正是 `集合工具.light` 的
  `测试集合工具模块` 8 条里 5 条能一路红到 R152 的原因（`集合工具.py` 已删，
  护栏扫描面里根本没有它）。

全仓这类模块共 ~80 个（含 `集合工具` / `统计` / `数学统计` / `数据结构` …）。

## 三层设计

1. **静态层（全自动、零登记）**：扫 `tests/**/test_*.py` 的 `from <魔数only模块> import <名>`，
   断言 `<名>` 在该模块的「可导入名集合」（`导出` 清单 ∪ 顶层 `段落` ∪ 顶层 `类`）里。
   抓的是「整函数/整类消失」——这种缺口不需要人工登记，扫到即红。
2. **行为层**：把 `tests/test_stdlib_phase13.py::测试集合工具模块` 的关键断言以单元
   形式搬进 `tests/unit/`。R150 教训：顶层 `tests/` 长期不在本机判绿口径里，
   结构性缺陷会一路漏到 0.82 才爆——行为层就是把它拉回本机门。
3. **登记层**：D 线裁定为「能力边界」的语义降级项进 `已知边界`，每条带**理由**与
   **复验探针**。清单长度 = 剩余边界债；探针一旦显示能力已具备（边界不再成立），
   门立刻红，逼你把那一条删掉——防清单退化成永久白洗条（R150 同款纪律）。

反跑自证见 `Test反跑_门有牙`：造临时 stdlib/测试树，证明静态层真的会红。
"""
import ast
import io
import os
import re
import shutil
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STDLIB = os.path.join(_ROOT, "stdlib")
_TESTS = os.path.join(_ROOT, "tests")

sys.path.insert(0, _STDLIB)
sys.path.insert(0, os.path.join(_ROOT, "src"))

_RE_导出 = re.compile(r"^导出\s+(.+?)。\s*$")
# `异步 段落 X(...)` 与 `段落 X(...)` 同属顶层可导入段（并发.light 的 任务池/超时运行
# 全是异步段，漏掉 `异步 ` 前缀会把它们整批误报成缺口）。
_RE_段落 = re.compile(r"^(?:异步\s+)?段落\s+([^\s(（:：]+)")
_RE_类 = re.compile(r"^类\s+([^\s(:：]+)")
# 顶层 `设 X 为 …` 是模块级变量，同样可被 `from 模块 import X` 取出
# （事件总线.light 的 `中止符号` 就是这么定义的）。
_RE_变量 = re.compile(r"^设\s+([^\s=]+)\s+为")
# `从 别的模块 导入 a b c。` 会把 a/b/c 绑进本模块命名空间 ⇒ 对外也可导入
# （数据验证.light 从 字符串工具 转出 验证IP地址/验证邮箱/…）。
_RE_导入 = re.compile(r"^从\s+\S+\s+导入\s+(.+?)(?:。\s*)?$")

# Python 标准库名即便有 .light 影子也不接管（_light_import_hook 的 _STDLIB_MODULES
# 保护），它们不是「纯光明模块」，不进本门的扫描面。
_标准库名 = frozenset(getattr(sys, "stdlib_module_names", ()))


# ---------------------------------------------------------------------------
# 扫描原语
# ---------------------------------------------------------------------------
def 是纯光明(path):
    """魔数判据：首两行含「纯光明实现」（与 R150 护栏 / bootstrap_rate.py 同口径）。"""
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        head = "".join(fh.readlines()[:2])
    return "纯光明实现" in head


def 魔数only模块(stdlib_dir):
    """带魔数 + 无同名 `.py`（R150 门的盲区集合）。"""
    out = {}
    for fn in sorted(os.listdir(stdlib_dir)):
        if not fn.endswith(".light"):
            continue
        名 = fn[: -len(".light")]
        if 名 in _标准库名:
            continue
        lt = os.path.join(stdlib_dir, fn)
        py = os.path.join(stdlib_dir, 名 + ".py")
        if os.path.isfile(py) or not 是纯光明(lt):
            continue
        out[名] = lt
    return out


def 可导入名(lt_path):
    """`.light` 对外可导入的名字。

    = `导出` 清单 ∪ 顶层段落（含 `异步 段落`）∪ 顶层类 ∪ 顶层变量（`设 X 为`）
      ∪ 顶层转出（`从 Y 导入 a b c`）。

    （类方法/嵌套段不算——外部 `from X import 方法名` 拿不到，出现即属异常用法。）
    """
    names = set()
    with io.open(lt_path, encoding="utf-8", errors="replace") as fh:
        for ln in fh.read().splitlines():
            m = _RE_导出.match(ln)
            if m:
                names.update(t for t in m.group(1).split() if t)
                continue
            m = _RE_段落.match(ln)
            if m:
                names.add(m.group(1))
                continue
            m = _RE_类.match(ln)
            if m:
                names.add(m.group(1))
                continue
            m = _RE_变量.match(ln)
            if m:
                names.add(m.group(1))
                continue
            m = _RE_导入.match(ln)
            if m:
                names.update(t for t in m.group(1).replace("。", " ").split() if t)
    return names


def 扫描导出缺口(stdlib_dir=_STDLIB, tests_dir=_TESTS):
    """返回 {测试文件: {模块: [缺失的导入名, ...]}}。

    只查「魔数 only」模块：它们没有 `.py` 兜底，导出面缺失 = 运行期直接
    ImportError / AttributeError，且 R150 的门看不见。
    """
    模块表 = 魔数only模块(stdlib_dir)
    导出面 = {名: 可导入名(p) for 名, p in 模块表.items()}
    缺口 = {}
    for 目录, _, 文件们 in os.walk(tests_dir):
        for fn in sorted(文件们):
            if not (fn.startswith("test_") and fn.endswith(".py")):
                continue
            path = os.path.join(目录, fn)
            with io.open(path, encoding="utf-8", errors="replace") as fh:
                try:
                    tree = ast.parse(fh.read())
                except SyntaxError:
                    continue
            本文件缺口 = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    顶级 = node.module.split(".")[0]
                    if 顶级 not in 导出面:
                        continue
                    缺 = sorted(a.name for a in node.names
                                if a.name != "*" and a.name not in 导出面[顶级])
                    if 缺:
                        本文件缺口.setdefault(node.module, []).extend(缺)
            if 本文件缺口:
                # 相对 tests_dir（不是 _ROOT）：反跑会造一棵别的盘符上的临时树，
                # ntpath.relpath 跨盘符直接 ValueError（实踩）。
                缺口[os.path.relpath(path, tests_dir)] = {k: sorted(set(v))
                                                          for k, v in 本文件缺口.items()}
    return 缺口


# ---------------------------------------------------------------------------
# 层 3：已登记的能力边界（唯一维护点：补齐一条就删一条）
# ---------------------------------------------------------------------------
# 每条 `复验` 返回 True 表示「这条边界**仍然成立**」。返回 False = 能力已具备、
# 边界已消失 ⇒ `test_登记里不许残留已补齐项` 立即红，逼你删账。

def _原生腿跑(code):
    """用原生腿编译并运行；无 clang 时返回 None（调用方按 skip 处理）。"""
    import subprocess
    from llvm.compiler import compile_light_typed
    with tempfile.TemporaryDirectory(prefix="_r152_e1_") as d:
        src = os.path.join(d, "主.light")
        with io.open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, "产物"), optimize_level=0)
        r = subprocess.run([exe], capture_output=True, timeout=180)
        return r.returncode, r.stdout.decode("utf-8", errors="replace").replace("\r", "").strip()


_原生_默认字典 = '''从 集合工具 导入 默认字典
段落 主:
  设 d 为 默认字典(空)
  输出(转文本(字典获取(d, "不在的键", -1)))
'''


def _复验_原生腿默认字典不补值():
    """边界：原生腿 dict 读不回调 `__missing__`（Python `__missing__` 是 CPython 专属钩子）。"""
    rc, out = _原生腿跑(_原生_默认字典)
    # 仍成立 ⇔ 缺键读拿到的是默认值 -1，而不是工厂补出来的值。
    return rc == 0 and out == "-1"


_原生_命名元组 = '''从 集合工具 导入 命名元组
段落 主:
  设 名 为 命名元组("点", 列表("x", "y"))
  输出(转文本(长(名)))
'''


def _复验_原生腿命名元组工厂不可调用():
    """边界：原生腿无 `__call__`，`命名元组(...)` 只能是字段名列表（长=2），造不出实例。"""
    rc, out = _原生腿跑(_原生_命名元组)
    return rc == 0 and out == "2"


def _复验_默认字典无工厂降级运行时错误():
    """边界：无工厂时缺键读抛 运行时错误（非 键错误）——`键错误` 未在原生腿
    异常类白名单登记，直呼会让整个模块编译失败（R152-D1 实踩）。"""
    from 集合工具 import 默认字典
    d = 默认字典()
    try:
        d["肯定不存在的键"]
    except Exception as e:
        return type(e).__name__ == "RuntimeError"
    return False


# 清单长度 = 剩余边界债。补齐一条 ⇒ 删一条（门会逼你删，见 test_登记里不许残留已补齐项）。
已知边界 = {
    "默认字典_原生腿缺键读不调缺失": {
        "理由": "Python 的 __missing__ 是 CPython dict 专属钩子；原生腿 dict 读走 "
                "dv_dict_get，缺键直接返默认值，不回调。src 腿已实现类工厂补值。",
        "复验": _复验_原生腿默认字典不补值,
        "登记位置": "stdlib/集合工具.light 头部「原生腿能力边界」条目 1",
    },
    "命名元组_原生腿工厂不可调用": {
        "理由": "实例可调用依赖 __call__；原生腿无此 dunder 回调，命名元组在原生腿只能"
                "当字段名列表用（长(名)==字段数），造不出 p.x 那样的实例。",
        "复验": _复验_原生腿命名元组工厂不可调用,
        "登记位置": "stdlib/集合工具.light 头部「原生腿能力边界」条目 2",
    },
    "默认字典_无工厂时抛运行时错误而非键错误": {
        "理由": "原生腿 _gen_builtin_exception_classes 未登记 键错误，直呼会让整个"
                " 集合工具.light 编译失败；故无工厂缺键读降级为 运行时错误。",
        "复验": _复验_默认字典无工厂降级运行时错误,
        "登记位置": "stdlib/集合工具.light 默认字典类 段落 缺失 的注释",
    },
}


def _原生腿可用():
    return shutil.which("clang") is not None


# ---------------------------------------------------------------------------
# 层 1：静态
# ---------------------------------------------------------------------------
class Test静态_导出面缺口(unittest.TestCase):

    def test_测试导入名必须在该模块的导出面里(self):
        缺口 = 扫描导出缺口()
        self.assertEqual(缺口, {},
                         "下列测试从「魔数 only」模块导入的名字，在该模块的 "
                         "`导出` 清单 / 顶层段落 / 顶层类里都不存在——"
                         "这类模块没有同名 .py 兜底，R150 的门又扫不到，"
                         "缺失会静默活到权威门才爆：\n%s" % 缺口)


# ---------------------------------------------------------------------------
# 层 2：行为（把顶层 tests/ 的集合工具断言拉回本机门）
# ---------------------------------------------------------------------------
class Test行为_集合工具关键断言(unittest.TestCase):
    """`tests/test_stdlib_phase13.py::测试集合工具模块` 的单元化副本。

    R150 教训：顶层 `tests/` 长期不在本机判绿口径里。这里让同一批断言在
    `tests/unit/` 里也跑一遍，本机门对结构性缺陷不再无感。
    """

    def test_计数器(self):
        from 集合工具 import 计数器
        c = 计数器(['a', 'b', 'a', 'c', 'b', 'a'])
        self.assertEqual(c['a'], 3)
        self.assertEqual(c['b'], 2)
        self.assertEqual(c['c'], 1)

    def test_计数器最常见(self):
        from 集合工具 import 计数器
        c = 计数器(['a', 'b', 'a', 'c', 'b', 'a'])
        常见 = c.最常见(2)
        self.assertEqual(len(常见), 2)
        self.assertEqual(常见[0][0], 'a')

    def test_默认字典(self):
        from 集合工具 import 默认字典
        d = 默认字典(int)
        self.assertEqual(d['不存在的键'], 0)
        d['测试'] += 1
        self.assertEqual(d['测试'], 1)

    def test_默认字典列表(self):
        from 集合工具 import 默认字典
        d = 默认字典(list)
        d['键'].append(1)
        d['键'].append(2)
        self.assertEqual(d['键'], [1, 2])

    def test_有序字典(self):
        from 集合工具 import 有序字典
        d = 有序字典()
        d['b'] = 2
        d['a'] = 1
        d['c'] = 3
        self.assertEqual(list(d.keys()), ['b', 'a', 'c'])

    def test_双端队列(self):
        from 集合工具 import 双端队列
        dq = 双端队列([1, 2, 3])
        dq.右入队(4)
        self.assertEqual(dq.右出队(), 4)
        dq.左入队(0)
        self.assertEqual(dq.左出队(), 0)

    def test_命名元组(self):
        from 集合工具 import 命名元组
        点 = 命名元组('点', ['x', 'y'])
        p = 点(3, 4)
        self.assertEqual(p.x, 3)
        self.assertEqual(p.y, 4)

    def test_统计频率(self):
        from 集合工具 import 统计频率
        结果 = 统计频率(['a', 'b', 'a', 'c', 'b', 'a'])
        self.assertEqual(结果['a'], 3)


# ---------------------------------------------------------------------------
# 层 3：登记
# ---------------------------------------------------------------------------
class Test登记_能力边界(unittest.TestCase):

    def test_登记项都带理由与复验(self):
        for 名, 项 in 已知边界.items():
            self.assertIn("理由", 项)
            self.assertTrue(项["理由"].strip(), "%s 缺理由" % 名)
            self.assertTrue(callable(项.get("复验")), "%s 缺复验探针" % 名)
            self.assertIn("登记位置", 项)

    @unittest.skipUnless(_原生腿可用(), "本机无 clang，跳过原生腿复验")
    def test_登记里不许残留已补齐项(self):
        """边界一旦消失就必须删账 —— 防登记清单退化成永久白洗条。"""
        已补齐 = []
        for 名, 项 in sorted(已知边界.items()):
            try:
                仍成立 = 项["复验"]()
            except Exception as e:                      # 探针本身崩了也要暴露
                已补齐.append("%s（复验探针异常：%s: %s）" % (名, type(e).__name__, e))
                continue
            if not 仍成立:
                已补齐.append(名)
        self.assertEqual(已补齐, [],
                         "这些登记的边界其实已经消失了，请把它们从 `已知边界` 里删掉"
                         "（清单长度 = 剩余边界债，必须随补齐而缩短）：%s" % 已补齐)


# ---------------------------------------------------------------------------
# 反跑：证明这个门有牙
# ---------------------------------------------------------------------------
class Test反跑_门有牙(unittest.TestCase):
    """造临时 stdlib + 测试树，证明静态层会红、且不会误伤。"""

    def _造树(self, 魔数=True, light正文=None, 测试导入=None):
        d = tempfile.mkdtemp(prefix="_r152_e1_")
        sd = os.path.join(d, "stdlib")
        td = os.path.join(d, "tests")
        os.makedirs(sd)
        os.makedirs(td)
        名 = "某魔数模块"
        with io.open(os.path.join(sd, 名 + ".light"), "w", encoding="utf-8") as f:
            f.write(light正文 if light正文 is not None else "段落 甲():\n  返回 1\n")
            if 魔数:
                pass
        if 魔数 and light正文 is None:
            with io.open(os.path.join(sd, 名 + ".light"), "w", encoding="utf-8") as f:
                f.write("# 纯光明实现 —— 测试用\n段落 甲():\n  返回 1\n")
        with io.open(os.path.join(td, "test_某.py"), "w", encoding="utf-8") as f:
            f.write("def test_x():\n    from %s import %s\n" % (名, 测试导入 or "甲"))
        return d, sd, td, 名

    def test_导入了不存在的名字会被报出来(self):
        d, sd, td, 名 = self._造树(魔数=True, 测试导入="乙")
        try:
            缺口 = 扫描导出缺口(sd, td)
            self.assertTrue(any(名 in v for v in 缺口.values()),
                            "测试导入了 乙 但 .light 只导出 甲 —— 门必须报出来")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_导出清单里的名字不算缺口(self):
        d, sd, td, 名 = self._造树(
            魔数=True,
            light正文="# 纯光明实现 —— 测试用\n导出 乙。\n段落 乙():\n  返回 1\n",
            测试导入="乙")
        try:
            self.assertEqual(扫描导出缺口(sd, td), {},
                             "乙 在 `导出` 清单里，不该被判为缺口")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_无魔数模块不进扫描面(self):
        """反向：没有魔数（且没有同名 .py）的普通模块不在本门的管辖范围。"""
        d, sd, td, 名 = self._造树(魔数=False, 测试导入="乙")
        try:
            self.assertEqual(魔数only模块(sd), {}, "无魔数不该被当成魔数 only 模块")
            self.assertEqual(扫描导出缺口(sd, td), {})
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_有同名py的同魔数模块归属R150门(self):
        """带魔数 + 有同名 .py ⇒ 由 R150 门管，不进本门的魔数 only 集合。"""
        d, sd, td, 名 = self._造树(魔数=True)
        try:
            with io.open(os.path.join(sd, 名 + ".py"), "w", encoding="utf-8") as f:
                f.write("def 甲():\n    return 1\n")
            self.assertNotIn(名, 魔数only模块(sd))
            self.assertEqual(扫描导出缺口(sd, td), {})
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
