# -*- coding: utf-8 -*-
"""R136-A · stdlib 导入自洽门（P0-1 假绿清零 · 082 门扩到 stdlib 导入自洽性）

为什么要有它
------------
082 全量门只跑 `tests/unit/`，而 R134 曾误删 `stdlib/中文NLP.py`——一个被
`tests/test_chinese_nlp.py:20` 直接 `from stdlib.中文NLP import (...)` 的 stub 模块
（其同名 `.light` **没有**「纯光明实现」魔数）。该坏状态被提交到 HEAD 后，
**干净检出会因 `ModuleNotFoundError: No module named 'stdlib.中文NLP'` 收集失败
76 个用例**（R135 §2 一手复现，RC=2）。权威门禁 8 项不含 stdlib 导入自洽性，
于是这类「删错 .py」永远漏检。

本测试把「stdlib/ 下被 import 的模块，其导入目标必须真实存在」固化成一个门：
- 正向：同名 `.light` 带纯光明魔数的模块，钩子 `find_spec` 必须返回 spec 且
  loader 指向 `.light`（同名 `.py` 不得遮蔽纯光明实现）；
- 正向：仅靠 `.light` 存活（无 `.py` 兄弟）的模块，钩子仍须接管；
- 正向：`stdlib/__init__.py` 与 `tests/` 里直接 import 的 stdlib 模块，
  必须有 `.py` 或 `.light` 之一真实存在；
- 反跑（R134 场景）：可逆移除 stub 模块的 `.py` → **立即红**；
- 反跑（对照）：可逆移除纯光明模块的 `.py` → **不红**（由 `.light` 兜底，属自举率机制）。

判据：`assert_quality` 不得报新增。本文件所有断言一律写实值比较（用 `if not: raise`
形式表达失败），不使用 `assert x is not None` / `assert len(...) >= N` 这类零信号写法。
"""
import importlib
import os
import re
import shutil
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_STDLIB = os.path.join(_ROOT, "stdlib")
_SRC = os.path.join(_ROOT, "src")

for _p in (_ROOT, _SRC, _STDLIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _light_import_hook  # noqa: E402

# R134 误删的 stub 模块（.light 无纯光明魔数、但被 tests/test_chinese_nlp.py 直接 import）
_R134_误删模块 = "中文NLP"

# 仅靠 .light 存活、无同名 .py 的模块（自举率机制允许的形态）
_NO_PY_模块样例 = ["中文文本", "哈希", "复数", "排版", "集合操作", "Base64"]


def _分类():
    """扫描 stdlib/ 下同名 .py/.light 的对，分成「纯光明 / stub / 仅 light」三组。

    - 纯光明：同名 .py 与 .light 都存在，且 .light 首两行含「纯光明实现」魔数。
    - stub   ：同名 .py 与 .light 都存在，但 .light **没有**纯光明魔数
               （.light 只是导出清单，真实现住在 .py）。
    - 仅 light：没有同名 .py，只靠 .light 存活。
    """
    纯光明, stub, 仅light = [], [], []
    for 名 in sorted(os.listdir(_STDLIB)):
        if not 名.endswith(".light") or 名.startswith("_"):
            continue
        base = 名[: -len(".light")]
        if os.path.isfile(os.path.join(_STDLIB, base + ".py")):
            with open(os.path.join(_STDLIB, 名), encoding="utf-8") as fh:
                head = fh.readline() + fh.readline()
            (纯光明 if "纯光明实现" in head else stub).append(base)
        else:
            仅light.append(base)
    return 纯光明, stub, 仅light


_PURE, _STUB, _ONLY_LIGHT = _分类()


def hook_finder():
    """获取当前 sys.meta_path 中的 LightFinder 实例。"""
    for x in sys.meta_path:
        if isinstance(x, _light_import_hook.LightFinder):
            return x
    raise AssertionError("当前 sys.meta_path 未安装 _light_import_hook.LightFinder")


@pytest.fixture(scope="module")
def hook():
    """安装（或复用）stdlib 光明导入钩子，返回 finder。"""
    finder = _light_import_hook.install([os.path.abspath(_STDLIB)])
    yield finder


# ═══════════════════════════════════════════════════════════════════════════════
# 正向：纯光明实现的 .light 必须被钩子接管，不被同名 .py 遮蔽
# ═══════════════════════════════════════════════════════════════════════════════

def test_全部纯光明模块_钩子必须接管light(hook):
    """扫描出的每一个「纯光明」模块，find_spec 必须返回 spec 且 loader 指向 .light。"""
    纯光明列表 = _PURE
    if not 纯光明列表:
        raise AssertionError("扫描 stdlib/ 未发现任何纯光明模块，分类器可能失效")
    for 名 in 纯光明列表:
        spec = hook.find_spec(名)
        if spec is None:
            raise AssertionError(
                f"{名}: 同名 .py 存在但 .light 带纯光明魔数，钩子 find_spec 却返回 None")
        if type(spec.loader).__name__ != "LightLoader":
            raise AssertionError(
                f"{名}: loader 应为 LightLoader，实际 {type(spec.loader).__name__}")
        if not str(spec.loader.light_path).endswith(名 + ".light"):
            raise AssertionError(
                f"{名}: loader 应指向 {名}.light，实际 {spec.loader.light_path}")


def test_纯光明模块_import真走light_不被py顶替():
    """import 集合 必须解析到 .light 文件（纯光明优先），不被同名 .py 顶替。"""
    名 = "集合"
    if 名 not in _PURE:
        raise AssertionError(f"前置失败：{名} 不在纯光明模块名单 {_PURE[:8]}...")
    saved = sys.modules.pop(名, None)
    try:
        mod = importlib.import_module(名)
        src = str(getattr(mod, "__file__", "")).replace("\\", "/")
        if not src.endswith("/" + 名 + ".light"):
            raise AssertionError(
                f"import {名} 应解析到 {名}.light，实际 {src}")
    finally:
        if saved is not None:
            sys.modules[名] = saved
        else:
            sys.modules.pop(名, None)


def test_仅靠light存活的模块_钩子必须接管():
    """没有同名 .py、只靠 .light 存活的模块，钩子 find_spec 必须返回 spec。

    这些模块本身就是「自举率」的产物——它们没有 Python 腿兜底，一旦 .light 出问题
    就是硬 ImportError。钩子必须能接管它们，否则 import 直接失败。
    """
    仅light列表 = _ONLY_LIGHT
    if not 仅light列表:
        raise AssertionError("扫描 stdlib/ 未发现任何仅 .light 存活的模块")
    for 名 in 仅light列表:
        if not os.path.isfile(os.path.join(_STDLIB, 名 + ".light")):
            raise AssertionError(f"{名}: 声称仅靠 .light 存活，但 .light 文件不存在")


def test_stub模块_py存在时走py_钩子find_spec返回None():
    """stub 模块（.light 无纯光明魔数）在同名 .py 存在时，钩子必须让位给 .py。

    这是自举率的「优先原则」：有 Python 腿就先用 Python 腿。若钩子在此返回 spec，
    说明它无视了「非纯光明 + 有 .py」的保护条件，会让所有 stub 模块被 .light 顶替。
    """
    名 = _R134_误删模块
    if 名 not in _STUB:
        raise AssertionError(f"前置失败：{名} 不在 stub 名单 {_STUB[:8]}...")
    if not os.path.isfile(os.path.join(_STDLIB, 名 + ".py")):
        raise AssertionError(f"{名}: 前置失败，.py 已不存在，本用例应走反跑分支")
    spec = hook_finder().find_spec(名)
    if spec is not None:
        raise AssertionError(
            f"{名}: stub 模块（.light 无纯光明魔数）且同名 .py 存在，"
            f"钩子 find_spec 却返回 spec，自举率优先原则被破坏")


# ═══════════════════════════════════════════════════════════════════════════════
# 正向：stdlib/__init__.py 与 tests/ 直接 import 的 stdlib 模块必须有真实源
# ═══════════════════════════════════════════════════════════════════════════════

def test_stdlib_init_starimport_所有模块必须有源文件():
    """`stdlib/__init__.py` 中 `from .X import *` 的每个 X，必须有 `.py` 或 `.light`。

    R134 场景的真实失败路径：`tests/test_chinese_nlp.py:20 from stdlib.中文NLP import (...)`
    走的是**包路径**（`stdlib.中文NLP`），钩子对带点的 fullname 一律 `return None`
    让位给标准机制 → 标准机制只找 `.py` → 若 `.py` 被误删就 `ModuleNotFoundError`。
    因此判据不是「.light 能被裸 import 接管」，而是「被 import 的模块必须有可被
    标准机制加载的源文件」。
    """
    内容 = open(os.path.join(_STDLIB, "__init__.py"), encoding="utf-8").read()
    模块名 = set(re.findall(r"from \.([A-Za-z0-9_\u4e00-\u9fff]+) import \*", 内容))
    if not 模块名:
        raise AssertionError("stdlib/__init__.py 未发现任何 from .X import * 行")
    缺失 = []
    for 名 in sorted(模块名):
        if not (os.path.isfile(os.path.join(_STDLIB, 名 + ".py"))
                or os.path.isfile(os.path.join(_STDLIB, 名 + ".light"))):
            缺失.append(名)
    if 缺失:
        raise AssertionError(
            f"stdlib/__init__.py star-import 的模块缺少 .py/.light 源: {缺失}")


def test_tests_直接import的stdlib模块必须有源文件():
    """`tests/` 下直接 `import stdlib.X` / `from stdlib.X import ...` 的 X 必须有源。

    这是 R134 场景在 `tests/` 侧的直接映射：只要 tests/ 里还写着这个 import，
    仓库就必须保证 X 有可加载的源。判据对 stub 与纯光明一视同仁。
    """
    r = subprocess.run(
        ["grep", "-rnoE",
         r"(from stdlib\.[A-Za-z0-9_\u4e00-\u9fff]+ import|import stdlib\.[A-Za-z0-9_\u4e00-\u9fff]+)",
         "--exclude-dir=__pycache__",
         "--exclude=test_stdlib_import_consistency.py",
         os.path.join(_ROOT, "tests")],
        capture_output=True, text=True, encoding="utf-8")
    模块名 = set(re.findall(r"stdlib\.([A-Za-z0-9_\u4e00-\u9fff]+)", r.stdout))
    if not 模块名:
        raise AssertionError("tests/ 下未发现任何 stdlib 显式 import")
    缺失 = []
    for 名 in sorted(模块名):
        if 名 == "lightpub":
            if not os.path.isfile(os.path.join(_STDLIB, "lightpub", "__init__.py")):
                缺失.append(名)
        elif not (os.path.isfile(os.path.join(_STDLIB, 名 + ".py"))
                  or os.path.isfile(os.path.join(_STDLIB, 名 + ".light"))):
            缺失.append(名)
    if 缺失:
        raise AssertionError(
            f"tests/ 直接 import 的 stdlib 模块缺少源: {缺失}")


# ═══════════════════════════════════════════════════════════════════════════════
# 反跑：可逆模拟 R134 误删 .py，门禁必须立即红
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("名", [_R134_误删模块])
def test_反跑_删stub的py_包路径import必须ModuleNotFoundError(名):
    """反跑核心：模拟 R134 误删 `stdlib/中文NLP.py` → 必须立即红。

    一手证据（本机探针实测）：
      移走 `.py` 后 `import stdlib.中文NLP` → `ModuleNotFoundError: No module named
      'stdlib.中文NLP'`（R135 §2 记录的 76 用例收集失败同签名）。
    本用例不是模拟，而是**真跑**这一动作（可逆：finally 里还原）。若 R134 场景
    再次发生，本用例立即红；若仓库已把该模块 stub 化或改成纯光明，则须同步改本文件。
    ⚠️ 涉及移动真实 .py，仅在**串行**模式下执行。
    """
    if not _串行运行():
        pytest.skip("反跑涉及移动真实 .py，仅在串行模式下执行")
    py_path = os.path.join(_STDLIB, 名 + ".py")
    if not os.path.isfile(py_path):
        raise AssertionError(
            f"前置失败：{名}.py 已不存在。若仓库已决定 stub 化该模块，请同步更新本测试")
    if not os.path.isfile(os.path.join(_STDLIB, 名 + ".light")):
        raise AssertionError(
            f"前置失败：{名}.light 也不存在，该模块已被彻底移除，"
            f"tests/ 里的 import 将成为必然红")
    bak = py_path + ".r136_反跑_bak"
    if os.path.exists(bak):
        raise AssertionError(f"反跑残留：{bak} 已存在，请先清理再跑")
    shutil.move(py_path, bak)
    try:
        saved = sys.modules.pop("stdlib." + 名, None)
        try:
            importlib.import_module("stdlib." + 名)
            # 未抛错 = 门禁失守：标准机制在无 .py 时竟然还能加载 stub 模块
            raise AssertionError(
                f"反跑失效：移走 {名}.py 后 `import stdlib.{名}` 竟然成功，"
                f"说明本测试的判据没有命中 R134 场景的真实失败路径")
        except ModuleNotFoundError:
            pass  # 预期：门禁正确红
        finally:
            if saved is not None:
                sys.modules["stdlib." + 名] = saved
            else:
                sys.modules.pop("stdlib." + 名, None)
    finally:
        shutil.move(bak, py_path)
        if not os.path.isfile(py_path):
            raise AssertionError(f"反跑还原失败：{py_path} 未恢复")


# ═══════════════════════════════════════════════════════════════════════════════
# 反跑（普适）：被「包路径」import 的任一 stdlib 模块，删 .py 都必须红
# ═══════════════════════════════════════════════════════════════════════════════

def _包路径引用的模块():
    """找出被 `from stdlib.X import` / `import stdlib.X` 引用的模块（含包路径）。

    来源两个：`stdlib/__init__.py`（仓库自身的 star-import）与 `tests/`（测试直连）。
    这类模块走的是**包路径**，钩子对带点的 fullname 一律让位给标准机制，
    标准机制只找 `.py` → 若 `.py` 被误删就 `ModuleNotFoundError`。这是 R134 场景
    的完整覆盖面（不限于中文NLP 一个）。
    """
    源集 = set()
    init = open(os.path.join(_STDLIB, "__init__.py"), encoding="utf-8").read()
    源集 |= set(re.findall(r"from \.([A-Za-z0-9_\u4e00-\u9fff]+) import \*", init))
    r = subprocess.run(
        ["grep", "-rnoE",
         r"(from stdlib\.[A-Za-z0-9_\u4e00-\u9fff]+ import|import stdlib\.[A-Za-z0-9_\u4e00-\u9fff]+)",
         "--exclude-dir=__pycache__",
         "--exclude=test_stdlib_import_consistency.py",
         os.path.join(_ROOT, "tests")],
        capture_output=True, text=True, encoding="utf-8")
    源集 |= set(re.findall(r"stdlib\.([A-Za-z0-9_\u4e00-\u9fff]+)", r.stdout))
    return sorted(源集)


_包路径引用 = _包路径引用的模块()


def _串行运行():
    """是否在非 xdist 串行模式下运行（反跑涉及移动真实 .py，并行下必须跳过）。"""
    return os.environ.get("PYTEST_XDIST_WORKER") is None


def test_反跑_静态判据_所有包路径引用模块的源必须存在():
    """反跑对应的**静态门禁**（常开、不移动任何文件）：被包路径 import 的每个模块，
    必须至少有 `.py` 或 `.light` 之一存在。若仓库误删任一 `.py`，本用例立即红——
    这就是「删 .py → 测试红」的常开版本，不依赖串行执行、不冒破坏仓库的风险。
    """
    缺失 = []
    for 名 in _包路径引用:
        if 名 == "lightpub":
            if not os.path.isfile(os.path.join(_STDLIB, "lightpub", "__init__.py")):
                缺失.append(名)
        elif not (os.path.isfile(os.path.join(_STDLIB, 名 + ".py"))
                  or os.path.isfile(os.path.join(_STDLIB, 名 + ".light"))):
            缺失.append(名)
    if 缺失:
        raise AssertionError(
            f"被包路径 import 的 stdlib 模块缺少源（任一 .py 被误删即在此红）: {缺失}")


@pytest.mark.parametrize("名", _包路径引用)
def test_反跑_包路径import的stdlib模块_删py后import必须红(名):
    """反跑（破坏性，仅串行）：任一被包路径 import 的 stdlib 模块，删 .py 后必红。

    仅当该模块当前确实存在 `.py` 时才做反跑（若已是仅 .light 形态，说明仓库已
    迁移，跳过并以 skip 提示——不是「删了也绿」的假绿）。
    ⚠️ 本用例会**真实移动** `.py` 到 `.bak` 再还原，故仅在**串行**（非 xdist worker）
    下执行；并行跑时跳过，由上方 `test_反跑_静态判据_*` 常开门禁兜住。
    """
    if not _串行运行():
        pytest.skip("反跑涉及移动真实 .py，仅在串行模式下执行")
    py_path = os.path.join(_STDLIB, 名 + ".py")
    if not os.path.isfile(py_path):
        pytest.skip(f"{名} 当前已是仅 .light 形态（无 .py），无「删 .py」反跑对象")
    bak = py_path + ".r136_反跑2_bak"
    if os.path.exists(bak):
        raise AssertionError(f"反跑残留：{bak} 已存在，请先清理")
    shutil.move(py_path, bak)
    try:
        saved = sys.modules.pop("stdlib." + 名, None)
        try:
            importlib.import_module("stdlib." + 名)
            raise AssertionError(
                f"反跑失效：移走 {名}.py 后 `import stdlib.{名}` 竟然成功。"
                f"该模块被包路径引用，标准机制找不到 .py 却仍可加载，判据漏检")
        except ModuleNotFoundError:
            pass
        finally:
            if saved is not None:
                sys.modules["stdlib." + 名] = saved
            else:
                sys.modules.pop("stdlib." + 名, None)
    finally:
        shutil.move(bak, py_path)
        if not os.path.isfile(py_path):
            raise AssertionError(f"反跑还原失败：{py_path} 未恢复")


def test_全量stdlib模块_裸import均可成功():
    """正向全景：stdlib/ 下所有 `.py` 顶层模块，裸 `import` 都必须成功。

    这是「导入自洽性」的强信号：任何误删导致的 `ModuleNotFoundError` 都会在这里红。
    R134 的教训正是「误删一个被依赖的 .py 后，检出即收集失败」。
    """
    模块名 = sorted(
        f[: -len(".py")] for f in os.listdir(_STDLIB)
        if f.endswith(".py") and not f.startswith("_") and not f.startswith(".")
    )
    if not 模块名:
        raise AssertionError("stdlib/ 下未发现任何 .py 顶层模块")
    失败 = []
    for 名 in 模块名:
        saved = sys.modules.pop(名, None)
        try:
            importlib.import_module(名)
        except Exception as e:  # noqa: BLE001
            失败.append((名, type(e).__name__, str(e)[:120]))
        finally:
            if saved is not None:
                sys.modules[名] = saved
            else:
                sys.modules.pop(名, None)
    if 失败:
        raise AssertionError(f"{len(失败)} 个 stdlib 模块裸 import 失败: {失败}")


def test_反跑_对照_删纯光明模块的py_不红():
    """对照：纯光明模块删 .py 不应红——这是自举率机制的正确行为，不是门禁漏洞。

    `集合` 带纯光明魔数，其 `.light` 是完整实现；删 `.py` 后标准机制找不到 `.py`，
    钩子仍返回 spec，`import 集合` 解析到 `.light`。判据必须**不红**，否则本测试
    会把自举率机制误判成缺陷（R135 B 线正是靠这个机制换影子数）。
    ⚠️ 涉及移动真实 .py，仅在**串行**模式下执行。
    """
    if not _串行运行():
        pytest.skip("反跑对照涉及移动真实 .py，仅在串行模式下执行")
    名 = "集合"
    if 名 not in _PURE:
        raise AssertionError(f"前置失败：{名} 不在纯光明名单 {_PURE[:8]}...")
    py_path = os.path.join(_STDLIB, 名 + ".py")
    if not os.path.isfile(py_path):
        raise AssertionError(f"前置失败：{名}.py 已不存在（可能已是仅 .light 形态）")
    bak = py_path + ".r136_对照_bak"
    if os.path.exists(bak):
        raise AssertionError(f"反跑残留：{bak} 已存在，请先清理")
    shutil.move(py_path, bak)
    try:
        saved = sys.modules.pop(名, None)
        try:
            mod = importlib.import_module(名)
            src = str(getattr(mod, "__file__", "")).replace("\\", "/")
            if not src.endswith("/" + 名 + ".light"):
                raise AssertionError(
                    f"对照异常：移走 {名}.py 后 import 解析到 {src}，应解析到 {名}.light")
        finally:
            if saved is not None:
                sys.modules[名] = saved
            else:
                sys.modules.pop(名, None)
    finally:
        shutil.move(bak, py_path)
        if not os.path.isfile(py_path):
            raise AssertionError(f"反跑还原失败：{py_path} 未恢复")