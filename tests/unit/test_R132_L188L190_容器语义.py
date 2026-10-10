# -*- coding: utf-8 -*-
"""
R132-B 定向用例：L-188 嵌套下标读-改-写回 / L-189 列表别名赋值 / L-190 带参 .弹出(i)。

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

# L-188：嵌套下标读-改-写回（native 修复前 `嵌套[0]=[1]`）
# L-189：列表别名赋值（native 修复前 源=[1,2] 副=[1,2,3]，Python 腿 源=[1,2,3]）
# L-190：带参 .弹出(i)（native 修复前 弹出返回=空 表=[1,2,3]）
_SRC = """段落 主():
  设 嵌套 为 [[1], [2]]
  嵌套[0].追加(9)
  输出("L188_嵌套0=" 加上 转字符串(嵌套[0]))
  输出("L188_嵌套=" 加上 转字符串(嵌套))
  设 源 为 [1, 2]
  设 副 为 源
  副.追加(3)
  输出("L189_源=" 加上 转字符串(源))
  输出("L189_副=" 加上 转字符串(副))
  设 表 为 [1, 2, 3]
  设 弹 为 表.弹出(0)
  输出("L190_弹出返回=" 加上 转字符串(弹))
  输出("L190_表=" 加上 转字符串(表))
  设 表2 为 [1, 2, 3]
  设 弹2 为 表2.弹栈()
  输出("L190_弹栈返回=" 加上 转字符串(弹2))
  输出("L190_表2=" 加上 转字符串(表2))
  返回 0
"""

_EXPECT = {
    "L188_嵌套0": "[1, 9]",
    "L188_嵌套": "[[1, 9], [2]]",
    "L190_弹出返回": "1",
    "L190_表": "[2, 3]",
    "L190_弹栈返回": "3",
    "L190_表2": "[1, 2]",
}

# L-189（R132-B 裁定：不做，登记为已知跨腿分叉）
#   两条腿语义不同：Python 腿 `设 副 为 源` 是引用别名（源=[1,2,3]），
#   原生腿当前是值语义（dv_clone 深拷贝，源=[1,2] 副=[1,2,3]）。
#   修复需架构级引用模型改造（REF 是单向指针，无法联动多个别名），
#   爆炸半径远超判据阈值 ⇒ 本轮不修，只在原生腿断言当前真实行为。
_L189_NATIVE_EXPECT = {"L189_源": "[1, 2]", "L189_副": "[1, 2, 3]"}
_L189_PYTHON_EXPECT = {"L189_源": "[1, 2, 3]", "L189_副": "[1, 2, 3]"}


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
        with tempfile.TemporaryDirectory(prefix="_r132b_") as d:
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
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        with tempfile.TemporaryDirectory(prefix="_r132b_py_") as d:
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


class R132Python腿对拍基准(unittest.TestCase):
    """Python 腿（规范源）基准：不依赖 clang，任何环境都要绿。

    只对 L-188 / L-190 做双腿一致性断言（这是本轮修的两条）。
    L-189 单独断言 Python 腿规范值，不做双腿比对（见 _EXPECT 注释）。
    """

    def test_python腿期望值(self):
        out = _python_run(_SRC)
        for key in ("L188_嵌套0", "L188_嵌套", "L190_弹出返回",
                    "L190_表", "L190_弹栈返回", "L190_表2"):
            want = _EXPECT[key]
            self.assertEqual(out.get(key), want, f"{key}: Python 腿={out.get(key)!r} 期望={want!r}")

    def test_python腿L189值语义(self):
        """Python 腿（规范源）的 L-189 基准：`设 副 为 源` 是引用别名。"""
        out = _python_run(_SRC)
        for key, want in _L189_PYTHON_EXPECT.items():
            self.assertEqual(out.get(key), want, f"{key}: Python 腿={out.get(key)!r} 期望={want!r}")


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class R132L188L190容器语义对拍(unittest.TestCase):
    """L-188 / L-190 修复后，原生腿须与 Python 腿逐条一致。"""

    def test_双腿对拍(self):
        out = _native_run(_SRC)
        for key, want in _EXPECT.items():
            self.assertEqual(
                out.get(key), want,
                f"{key}: 原生腿={out.get(key)!r} 期望={want!r}（Python 腿实测）",
            )
        # L-189：本轮**不做**（跨腿分叉），只钉住原生腿当前真实行为，
        # 防止后续改动不小心把这条也改了却不自知。
        for key, want in _L189_NATIVE_EXPECT.items():
            self.assertEqual(
                out.get(key), want,
                f"{key}: 原生腿={out.get(key)!r} 期望={want!r}（L-189 登记差异）",
            )


if __name__ == "__main__":
    unittest.main()