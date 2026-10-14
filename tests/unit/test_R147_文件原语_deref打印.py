# -*- coding: utf-8 -*-
"""
R147-A 子任务 1 用例 B：REF 解引用 + 多参打印 双腿对拍。

两个 A 线修复的守单点：
 ① REF 解引用（``_deref_value`` 应用到标量读取/只读内置）——
    dict 字段读取返回 REF（type 8，指向内部值），直接喂 整数/取模/整除/四舍五入/
    格式化时间 会误读 LightValue 结构体的垃圾字段（`整数(dict字段)=0`、
    `格式化时间=1970` 等）。修复：读 REF 实参前先 ``dv_deref_value``。
    覆盖两条取值路径：属性访问（``表.a``）与下标访问（``表["a"]``）。
 ② 多参打印——原实现只发 ``args[0]``，``args[1:]`` 静默丢弃（``打印("x", 5)`` 只出
    ``x``）。修复：逐参 ``dv_print`` + 参间 ``dv_print(" ")`` + 末参 ``dv_println``。

对拍口径：同一份源码分别走 native 腿（LLVM 编译 + 真跑）与 src 腿
（转译 Python 腿，规范源），逐条断言一致。整体 fork 到独立子进程
（复用 ``_t6b_native_helper.py``），避免 clang OOM 与进程内存污染。

已知预存差异（非本轮回归）：布尔 repr ``真/假``（native）vs ``True/False``（src）。
"""
import os
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (_ROOT, os.path.join(_ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from tests.unit.test_T6B_时间系统内建_原生腿 import _find_msvc_env  # noqa: E402


# 只读标量族：REF 解引用覆盖（属性 + 下标两条取值路径）
_SRC_DEREF = """段落 主():
  设 表 为 {"a": 17, "b": 5, "pi": 3.14159, "ts": 86400.0}
  打印("int_attr=", 整数(表.a))
  打印("int_sub=", 整数(表["a"]))
  打印("mod_attr=", 取模(表.a, 表.b))
  打印("mod_sub=", 取模(表["a"], 表["b"]))
  打印("div_attr=", 整除(表.a, 表.b))
  打印("div_sub=", 整除(表["a"], 表["b"]))
  打印("round_attr=", 四舍五入(表.pi))
  打印("round_sub=", 四舍五入(表["pi"]))
  打印("ftime_attr=", 格式化时间(表.ts))
  打印("ftime_sub=", 格式化时间(表["ts"]))
"""

# 多参打印：逐参空格连接 + 换行（对齐 src 腿 print(*args)）
_SRC_MULTI = """段落 主():
  打印("x", 5)
  打印("a", "b", "c")
  打印("单参")
  打印("v=", 42, "end")
"""

# Python 腿（规范源）实测期望值（2026-10-14，R147-A）
# 注意：格式化时间按**本地时区**换算（src 腿 datetime.fromtimestamp 语义）。
# 期望值动态算，避免 0.82（Linux UTC）与本机（Windows CST）时区差导致假红。
import datetime as _dt  # noqa: E402

_FTIME_WANT = _dt.datetime.fromtimestamp(86400.0).strftime("%Y-%m-%d %H:%M:%S")

_EXPECT_DEREF = {
    "int_attr": "17",
    "int_sub": "17",
    "mod_attr": "2",
    "mod_sub": "2",
    "div_attr": "3",
    "div_sub": "3",
    "round_attr": "3",
    "round_sub": "3",
    "ftime_attr": _FTIME_WANT,
    "ftime_sub": _FTIME_WANT,
}

# 多参打印期望（不含收尾标记；`打印()` 空参在两腿 repr 分叉——native 输出 `空`、
# src 输出空串，属预存差异，不纳入本轮对拍）
_EXPECT_MULTI = [
    "x 5",
    "a b c",
    "单参",
    "v= 42 end",
]


def _native_run(src_text, timeout=240):
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t6b_native_helper.py")
    env = dict(os.environ)
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    try:
        with tempfile.TemporaryDirectory(prefix="_r147a_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8") as f:
                f.write(src_text)
            exe = os.path.join(d, "main")
            proc = subprocess.run(
                [sys.executable, helper, src, exe],
                capture_output=True, timeout=timeout + 60, env=env, cwd=_ROOT,
            )
    except subprocess.TimeoutExpired:
        raise AssertionError(f"原生腿编译/运行超时（>{timeout}s）")
    if proc.returncode != 0:
        raise AssertionError(
            f"原生腿编译/运行失败 rc={proc.returncode}\n"
            f"STDOUT:\n{proc.stdout.decode('utf-8', 'replace')}\n"
            f"STDERR:\n{proc.stderr.decode('utf-8', 'replace')[:3000]}"
        )
    return proc.stdout.decode("utf-8", "replace")


def _src_run(src_text, timeout=120):
    """走 src 腿（转译 Python 腿，规范源）运行同一份源码，返回原始 stdout。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        with tempfile.TemporaryDirectory(prefix="_r147a_py_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8") as f:
                f.write(src_text)
            proc = subprocess.run(
                [sys.executable, os.path.join("cli", "light.py"), "run", src],
                capture_output=True, timeout=timeout, env=env, cwd=_ROOT,
            )
    except subprocess.TimeoutExpired:
        raise AssertionError(f"src 腿运行超时（>{timeout}s）")
    if proc.returncode != 0:
        raise AssertionError(
            f"src 腿运行失败 rc={proc.returncode}\n"
            f"STDOUT:\n{proc.stdout.decode('utf-8', 'replace')}\n"
            f"STDERR:\n{proc.stderr.decode('utf-8', 'replace')[:2000]}"
        )
    return proc.stdout.decode("utf-8", "replace")


def _kv(text):
    text = text.replace("\r\n", "\n").replace("\r", "")
    out = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _lines(text):
    """统一行尾后按行切分（原生腿 stdout 在 Windows 上带 \r\r\n）。"""
    text = text.replace("\r\n", "\n").replace("\r", "")
    return text.strip().splitlines()


def _clang_available():
    try:
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


class R147_Deref解引用_Src腿基准(unittest.TestCase):
    """src 腿（规范源）基准：REF 读取的 dict 字段须被正确解引用。"""

    def test_src腿期望值(self):
        out = _kv(_src_run(_SRC_DEREF))
        for key, want in _EXPECT_DEREF.items():
            self.assertEqual(
                out.get(key), want,
                f"{key}: src 腿={out.get(key)!r} 期望={want!r}",
            )


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class R147_Deref解引用_原生腿对拍(unittest.TestCase):
    """REF 解引用后，原生腿须与 src 腿逐条一致（修复前：整数(表.a)=0、格式化时间=1970）。"""

    def test_双腿对拍(self):
        out = _kv(_native_run(_SRC_DEREF))
        for key, want in _EXPECT_DEREF.items():
            self.assertEqual(
                out.get(key), want,
                f"{key}: 原生腿={out.get(key)!r} 期望={want!r}（src 腿实测）",
            )


class R147_多参打印_Src腿基准(unittest.TestCase):
    """src 腿（规范源）基准：`打印(*args)` 空格连接 + 换行。"""

    def test_src腿期望值(self):
        lines = _lines(_src_run(_SRC_MULTI))
        self.assertEqual(lines, _EXPECT_MULTI, f"src 腿多参打印输出不一致: {lines}")


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class R147_多参打印_原生腿对拍(unittest.TestCase):
    """多参打印修复后，原生腿须与 src 腿逐条一致（修复前：`打印("x", 5)` 只出 `x`）。"""

    def test_双腿对拍(self):
        lines = _lines(_native_run(_SRC_MULTI))
        self.assertEqual(lines, _EXPECT_MULTI, f"原生腿多参打印输出不一致: {lines}")


if __name__ == "__main__":
    unittest.main()