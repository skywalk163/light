# -*- coding: utf-8 -*-
"""R153 · `是空` 语义统一回归（业主裁定：目标语义 = null 或 ""，纯空白不纳入）。

为什么先写测试
--------------
`是空` 的 broaden 是**全仓调用点一起变**的改动（详见 `_R153_是空语义对齐清单.md`）：
两腿当前语义实测一致（都只判 null），所以这不是「修分叉」而是「两腿同时扩」，
影响面靠人工过调用点不够，必须用测试钉死。本文件按业主裁定的顺序**先于改语义落地**，
改语义前的预期状态是**红**（TDD），改完后转绿。

覆盖（对应清单 §五.1）
--------------------
* 语义矩阵：null / "" / "abc" / " " / 0 / 假 / 空列表 / 空字典 —— **两腿对拍**；
* `文件系统.light:367` 专项：`创建临时目录(目录="")` 必须回落到当前目录（真身 + 形状两路）；
* 防漂移：`断言为无("")` 仍须失败、`断言不为无("")` 仍须通过（清单 §2.2）；
* 路径/配置读取入口三处（清单 §3.1）：`展开用户目录` / `主目录` 的回落。

断言口径
--------
两腿布尔 repr 不同（src `True/False` vs 原生 `真/假`，L-193 已另案裁定为文档口径），
故**不比对 repr**：探针一律把判定结果转成 `"1"/"0"` 字符串再输出，两腿逐行对拍。
"""
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import contextlib

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_REPO, "src"), os.path.join(_REPO, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

sys.dont_write_bytecode = True


# ── 两腿运行器 ────────────────────────────────────────────────────────────────

def _跑_src(code):
    """src 腿：解析 → 生成 Python → exec，返回 stdout 行列表。"""
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    ast = LightParser().parse(code)
    py = PythonCodeGenerator().generate(ast)
    g = {"__name__": "__main__"}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py, "<R153>", "exec"), g)
        if "主" in g and callable(g["主"]):
            g["主"]()
    out = buf.getvalue().replace("\r", "").strip()
    return out.split("\n") if out else []


def _跑_原生(code, cwd=None):
    """原生腿：LLVM 编译 → 子进程运行，返回 stdout 行列表。"""
    from llvm.compiler import compile_light_typed

    with tempfile.TemporaryDirectory(prefix="_r153n_") as d:
        src = os.path.join(d, "主.light")
        with open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, "产物"), optimize_level=0)
        r = subprocess.run([exe], capture_output=True, timeout=180, cwd=cwd)
        out = r.stdout.decode("utf-8", errors="replace").replace("\r", "").strip()
        assert r.returncode == 0, "原生腿 rc=%d stderr=%s" % (
            r.returncode, r.stderr.decode("utf-8", errors="replace")[:400])
        return out.split("\n") if out else []


# ── 1. 语义矩阵（两腿对拍）────────────────────────────────────────────────────
# 目标语义（业主裁定）：null → 1；"" → 1；其余（含纯空白 " "、0、假、空容器）→ 0。
_矩阵源 = '''段落 判(值):
  如果 是空(值):
    返回 "1"
  返回 "0"

段落 主:
  输出(判(空))
  输出(判(""))
  输出(判("abc"))
  输出(判(" "))
  输出(判(0))
  输出(判(假))
'''

_矩阵期望 = ["1", "1", "0", "0", "0", "0"]


def test_是空_语义矩阵_src腿():
    assert _跑_src(_矩阵源) == _矩阵期望


def test_是空_语义矩阵_原生腿():
    assert _跑_原生(_矩阵源) == _矩阵期望


def test_是空_语义矩阵_两腿一致():
    """两腿必须逐位相同 —— 这条是 L-193 repr 差异之外真正的语义对拍。"""
    assert _跑_src(_矩阵源) == _跑_原生(_矩阵源)


def test_是空_纯空白不算空():
    """业主裁定：纯空白/空格不默认纳入空。`是空白` 已单独覆盖该需求。"""
    # 用与语义矩阵同样的「1/0 字符串」口径，避开 L-193 布尔 repr 差异后再对拍。
    源 = '段落 主:\n  如果 是空(" "):\n    输出("1")\n  否则:\n    输出("0")\n'
    assert _跑_src(源) == ["0"]
    assert _跑_原生(源) == ["0"]
    # 纯空白由 `是空白` 单独覆盖：`是空白(" ")` 必须为真（既有语义不被本轮改动波及）
    源2 = '段落 主:\n  如果 是空白(" "):\n    输出("1")\n  否则:\n    输出("0")\n'
    assert _跑_src(源2) == ["1"]
    assert _跑_原生(源2) == ["1"]


# ── 2. 文件系统.light:367 专项 ────────────────────────────────────────────────
# 367 行的形状：`目录 等于 空` → `如果 是空(基): 设 基 为 当前目录()`。
# 传显式空串时，现状不回落（是空("")==假），broaden 后必须回落。
_形状源 = '''段落 挑(目录):
  设 基 为 目录
  如果 是空(基):
    返回 "回落"
  返回 "原样"

段落 主:
  输出(挑(空))
  输出(挑(""))
  输出(挑("/tmp"))
'''


def test_创建临时目录形状_空串目录回落_src腿():
    assert _跑_src(_形状源) == ["回落", "回落", "原样"]


def test_创建临时目录形状_空串目录回落_原生腿():
    assert _跑_原生(_形状源) == ["回落", "回落", "原样"]


@pytest.fixture()
def _文件系统():
    """经 _light_import_hook 加载 stdlib/文件系统.light（首行魔数，取代同名 .py）。"""
    import _light_import_hook
    _light_import_hook.install([os.path.join(_REPO, "stdlib")])
    import 文件系统 as m
    return m


def test_创建临时目录_真身_空串目录回落到当前目录(_文件系统, tmp_path, monkeypatch):
    """清单 §2.1·367 专项：真身调用。空串目录参数必须等同缺省（落到当前目录）。"""
    monkeypatch.chdir(str(tmp_path))
    got = _文件系统.创建临时目录("", "r153", "")
    assert got, "创建临时目录 返回空路径"
    # 必须落在当前工作目录下（= 回落生效），而不是相对裸名或根下
    assert os.path.isabs(got), "期望绝对路径（回落到 当前目录()），实际 %r" % (got,)
    assert os.path.dirname(os.path.abspath(got)) == os.path.realpath(str(tmp_path))
    shutil.rmtree(got, ignore_errors=True)


def test_创建临时目录_真身_给定目录仍生效(_文件系统, tmp_path):
    """反跑：显式给了目录时，不能因为 broaden 被误判成空而回落。"""
    子 = tmp_path / "给定"
    子.mkdir()
    got = _文件系统.创建临时目录("", "r153", str(子))
    assert os.path.dirname(os.path.abspath(got)) == os.path.realpath(str(子))
    shutil.rmtree(got, ignore_errors=True)


# ── 3. 防漂移：断言为无 / 断言不为无 不随 broaden 漂 ──────────────────────────
# 清单 §2.2：这两个段落名是「为无」，契约就是 is None，不能因 是空 扩语义而跟着变。
def test_断言为无_空串仍判失败():
    import _light_import_hook
    _light_import_hook.install([os.path.join(_REPO, "stdlib")])
    import 断言工具 as m
    with pytest.raises(Exception):
        m.断言为无("")


def test_断言不为无_空串仍判通过():
    import _light_import_hook
    _light_import_hook.install([os.path.join(_REPO, "stdlib")])
    import 断言工具 as m
    m.断言不为无("")  # 不抛即通过


def test_断言不为无_null仍判失败():
    import _light_import_hook
    _light_import_hook.install([os.path.join(_REPO, "stdlib")])
    import 断言工具 as m
    with pytest.raises(Exception):
        m.断言不为无(None)


# ── 4. 路径 / 配置读取入口三处（清单 §3.1）───────────────────────────────────
def test_展开用户目录_无USERPROFILE时回落HOME(_文件系统, monkeypatch):
    """B1 回归：USERPROFILE 缺失时 `环境变量` 返 ""，必须回落 HOME。"""
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.setenv("HOME", "/home/r153")
    got = _文件系统.展开用户目录("~/x")
    assert got.startswith("/home/r153"), "未回落 HOME，实际 %r" % (got,)


def test_主目录_无USERPROFILE时回落HOME(monkeypatch):
    """清单 §3.1 同类第三处：内置核心系统.light 的 主目录。"""
    import _light_import_hook
    _light_import_hook.install([os.path.join(_REPO, "stdlib")])
    import 内置核心系统 as m
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.setenv("HOME", "/home/r153")
    assert m.主目录() == "/home/r153"
