# -*- coding: utf-8 -*-
"""
R131-C 定向用例：L-186 排序/反转写回 + L-187 异常对象转字符串（原生腿）。

L-186：runtime `dv_list_sort` / `dv_list_reverse` 都是「malloc 新列表并返回」，
       不原地改接收者。方法形态 `表.sort()` / `表.反转()` 作为独立语句时若不写回，
       调用方看到的仍是旧列表（实测 `[3,1,2]` 不变）。
       修复：把 排序/sort/反转/reverse 补进 mutating_methods（codegen 两份名单）。
       ⚠️ 裸函数式 `排序(表)` **刻意不修**——Python 腿（规范源）实测也不写回，
       修了会制造新的跨腿分叉。本用例把两侧形态都钉住，防"好心修过头"。

L-187：① 异常类名直呼构造 `抛出 运行时错误("…")` 此前**丢弃消息实参**，
       异常对象的「消息」字段是空的；② `转字符串` 对类实例直接吐
       `obj:__class__…` 裸结构（还带串台的栈追踪）。
       修复：构造后写「消息」字段 + dv_to_string 对对象串给友好形态。

双腿对拍：同一份源码分别走 Python 腿（规范源）与原生腿，逐条断言一致。
「编译 + 运行」整体 fork 到独立子进程（复用 _t6b_native_helper.py）。
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

_SRC = """段落 主():
  设 表 为 [3, 1, 2]
  表.sort()
  输出("排序写回=" 加上 转字符串(表))
  设 表2 为 [3, 1, 2]
  表2.反转()
  输出("反转写回=" 加上 转字符串(表2))
  设 表3 为 [3, 1, 2]
  排序(表3)
  输出("函数式排序=" 加上 转字符串(表3))
  设 表4 为 [3, 1, 2]
  反转(表4)
  输出("函数式反转=" 加上 转字符串(表4))
  尝试:
    抛出 运行时错误("故意的")
  捕获 异常 为 e:
    输出("异常串=" 加上 转字符串(e))
  返回 0
"""

# Python 腿（规范源）实测期望值（2026-10-09，R131-C）
_EXPECT = {
    "排序写回": "[1, 2, 3]",     # L-186 修复点：修复前原生腿 = [3, 1, 2]
    "反转写回": "[2, 1, 3]",     # L-186 修复点：修复前原生腿 = [3, 1, 2]
    "函数式排序": "[3, 1, 2]",   # 刻意与 Python 腿保持一致（不写回）
    "函数式反转": "[3, 1, 2]",   # 同上
    "异常串": "故意的",           # L-187 修复点：修复前是 obj:__class__… 裸串
}


def _native_run(src_text, timeout=240):
    """以内联 .light 源码走原生腿编译并运行，返回 {KEY: 值}。"""
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t6b_native_helper.py")
    env = dict(os.environ)
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    try:
        with tempfile.TemporaryDirectory(prefix="_r131c_") as d:
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
    return _parse(proc.stdout.decode("utf-8", "replace"))


def _python_run(src_text, timeout=120):
    """走转译腿（Python 腿，规范源）运行同一份源码，返回 {KEY: 值}。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        with tempfile.TemporaryDirectory(prefix="_r131c_py_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8") as f:
                f.write(src_text)
            proc = subprocess.run(
                [sys.executable, os.path.join("cli", "light.py"), "run", src],
                capture_output=True, timeout=timeout, env=env, cwd=_ROOT,
            )
    except subprocess.TimeoutExpired:
        raise AssertionError(f"Python 腿运行超时（>{timeout}s）")
    if proc.returncode != 0:
        raise AssertionError(
            f"Python 腿运行失败 rc={proc.returncode}\n"
            f"STDOUT:\n{proc.stdout.decode('utf-8', 'replace')}\n"
            f"STDERR:\n{proc.stderr.decode('utf-8', 'replace')[:2000]}"
        )
    return _parse(proc.stdout.decode("utf-8", "replace"))


def _parse(text):
    out = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _clang_available():
    try:
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


class R131Python腿对拍基准(unittest.TestCase):
    """Python 腿（规范源）基准：不依赖 clang，任何环境都要绿。"""

    def test_python腿期望值(self):
        out = _python_run(_SRC)
        for key, want in _EXPECT.items():
            self.assertEqual(out.get(key), want, f"{key}: Python 腿={out.get(key)!r} 期望={want!r}")


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class R131L186L187原生腿对拍(unittest.TestCase):
    """L-186 / L-187 修复后，原生腿须与 Python 腿逐条一致。"""

    def test_双腿对拍(self):
        out = _native_run(_SRC)
        for key, want in _EXPECT.items():
            self.assertEqual(
                out.get(key), want,
                f"{key}: 原生腿={out.get(key)!r} 期望={want!r}（Python 腿实测）",
            )


if __name__ == "__main__":
    unittest.main()
