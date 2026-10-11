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

    def test_python腿规范值_写回与不写回二分(self):
        """R138-A 流X：把 L-186 的「规范值二分」显式钉在 Python 腿（规范源）上。

        标记形态 `表.sort()` / `表.反转()` **必须写回**；
        裸函数式 `排序(表)` / `反转(表)` **必须不写回**（与 Python 腿实测一致，
        修了会制造新的跨腿分叉）。上面 `test_python腿期望值` 已逐条覆盖，
        本用例把这条契约单独拎出来，防后续「好心修过头」时被顺手改掉。
        """
        out = _python_run(_SRC)
        self.assertEqual(out.get("排序写回"), "[1, 2, 3]", "方法形态 表.sort() 必须写回")
        self.assertEqual(out.get("反转写回"), "[2, 1, 3]", "方法形态 表.反转() 必须写回")
        self.assertEqual(out.get("函数式排序"), "[3, 1, 2]", "裸函数式 排序(表) 必须不写回")
        self.assertEqual(out.get("函数式反转"), "[3, 1, 2]", "裸函数式 反转(表) 必须不写回")


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


# ---------------------------------------------------------------------------
# R138-A 流X：L-187 残余「栈深度累积」定向用例
#
# 根因：`runtime_typed.c` 的调用栈是全局数组（`__dv_call_stack` /
#       `__dv_call_stack_size`）。`dv_throw_exception` 用 longjmp 跳回 setjmp 点，
#       longjmp 跨过的那些帧永不 `dv_stack_pop`；`dv_try_pop` 原先只回退
#       `__dv_try_level`，不回收 `__dv_call_stack_size`。
#       ⇒ 异常对象「栈追踪」字段会带上前序调用的残留帧，且**逐次累积**。
#
# 修法：`dv_try_push` 保存进入 try 前的栈深度到 `__dv_try_saved_stack_size[level]`，
#       `dv_try_pop` 弹出该级别时把 `__dv_call_stack_size` 截断回快照值。
#
# 断言口径：连续三次抛出/捕获，异常对象「栈追踪」的**帧数必须恒等**，
#       且每次只含「抛出点 + 捕获点」这两个与本次抛出真正相关的帧。
#       修复前实测：2 → 3 → 4（单调累积）。
# ---------------------------------------------------------------------------

_SRC_L187_栈深度 = """段落 路径甲():
  抛出 运行时错误("甲")

段落 路径乙():
  抛出 运行时错误("乙")

段落 路径丙():
  抛出 运行时错误("丙")

段落 捕获第(编号):
  尝试:
    如果 编号 等于 1:
      路径甲()
    否则如果 编号 等于 2:
      路径乙()
    否则:
      路径丙()
  捕获 异常 为 e:
    返回 e.栈追踪
  返回 "未捕获"

设 t1 为 捕获第(1)
输出("T1B")
输出(t1)
输出("T1E")
设 t2 为 捕获第(2)
输出("T2B")
输出(t2)
输出("T2E")
设 t3 为 捕获第(3)
输出("T3B")
输出(t3)
输出("T3E")
"""


def _block(text, name):
    """取 `输出("<NAME>B")` … `输出("<NAME>E")` 之间的多行原文。"""
    begin, end = f"{name}B", f"{name}E"
    lines = text.splitlines()
    out, cap = [], False
    for ln in lines:
        s = ln.strip()
        if s == begin:
            cap = True
            continue
        if s == end:
            break
        if cap:
            out.append(ln)
    return "\n".join(out)


def _frames(block_text):
    """把栈追踪文本切成帧名列表（`    at 名字` 形态）。"""
    names = []
    for ln in block_text.splitlines():
        s = ln.strip()
        if s.startswith("at "):
            names.append(s[3:].strip())
    return names


def _python_raw(src_text, timeout=120):
    """与 _python_run 同路径，但返回原始 stdout 文本（保留多行结构）。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        with tempfile.TemporaryDirectory(prefix="_r138x_py_") as d:
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
    return proc.stdout.decode("utf-8", "replace")


def _native_raw(src_text, timeout=240):
    """与 _native_run 同路径，但返回原始 stdout 文本（保留多行结构）。"""
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t6b_native_helper.py")
    env = dict(os.environ)
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    try:
        with tempfile.TemporaryDirectory(prefix="_r138x_") as d:
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


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class R138X_L187栈深度残余(unittest.TestCase):
    """L-187 残余：捕获后异常对象「栈追踪」不得含 longjmp 残留帧，且不随次数累积。"""

    def test_栈追踪帧数不随捕获次数累积(self):
        raw = _native_raw(_SRC_L187_栈深度)
        counts, names = [], []
        for tag in ("T1", "T2", "T3"):
            fr = _frames(_block(raw, tag))
            counts.append(len(fr))
            names.append(fr)

        # 关键断言：三次捕获的帧数必须完全相等（修复前为 2/3/4 单调累积）
        self.assertEqual(
            len(set(counts)), 1,
            f"栈追踪帧数随捕获次数累积（L-187 残余复现）：{counts}\n"
            f"帧明细={names}\n原始输出:\n{raw}",
        )
        # 且深度须为「抛出点 + 捕获点」两层，不得带上更早的无关帧
        self.assertEqual(
            counts[0], 2,
            f"栈追踪应为 2 帧（抛出点 + 捕获点），实为 {counts[0]}：{names[0]}\n原始输出:\n{raw}",
        )
        # 且每次的抛出点须对应当次真正抛出的段
        for idx, (fr, want_throw) in enumerate(
                zip(names, ("路径甲", "路径乙", "路径丙"))):
            self.assertIn(
                want_throw, fr,
                f"第 {idx + 1} 次捕获的栈追踪未含本次抛出点 {want_throw}：{fr}",
            )

    def test_栈追踪不含前序调用残留帧(self):
        """第一次捕获后，第二次捕获不得带出第一次的抛出点帧。"""
        raw = _native_raw(_SRC_L187_栈深度)
        f1 = _frames(_block(raw, "T1"))
        f2 = _frames(_block(raw, "T2"))
        f3 = _frames(_block(raw, "T3"))
        self.assertNotIn("路径甲", f2, f"第二次捕获带出第一次的残留帧：{f2}")
        self.assertNotIn("路径甲", f3, f"第三次捕获带出第一次的残留帧：{f3}")
        self.assertNotIn("路径乙", f3, f"第三次捕获带出第二次的残留帧：{f3}")
        self.assertEqual(f1, ["路径甲", "捕获第"], f"首次栈追踪帧序异常：{f1}")
        self.assertEqual(f2, ["路径乙", "捕获第"], f"第二次栈追踪帧序异常：{f2}")
        self.assertEqual(f3, ["路径丙", "捕获第"], f"第三次栈追踪帧序异常：{f3}")


class R138X_L187栈深度残余_Python腿(unittest.TestCase):
    """Python 腿（规范源）侧：`traceback` 在 except 块内应只含本次调用链。

    ⚠️ 字段名已实测确认（0.88，2026-10-11）：原生腿异常对象有「栈追踪」字段，
        Python 腿的 `RuntimeError` **没有**该属性（`e.栈追踪` 报属性错误）。
        故跨腿规范值对齐不落在字段名上，而落在「本次调用链、无前序残留」这一契约上：
        原生腿读 `e.栈追踪`，Python 腿读 `traceback.format_exc()`。
    """

    _SRC_PY = """导入 traceback

段落 路径甲():
  抛出 运行时错误("甲")

段落 路径乙():
  抛出 运行时错误("乙")

段落 路径丙():
  抛出 运行时错误("丙")

段落 捕获第(编号):
  尝试:
    如果 编号 等于 1:
      路径甲()
    否则如果 编号 等于 2:
      路径乙()
    否则:
      路径丙()
  捕获 异常 为 e:
    返回 traceback.format_exc()
  返回 "未捕获"

设 t1 为 捕获第(1)
输出("T1B")
输出(t1)
输出("T1E")
设 t2 为 捕获第(2)
输出("T2B")
输出(t2)
输出("T2E")
设 t3 为 捕获第(3)
输出("T3B")
输出(t3)
输出("T3E")
"""

    def test_python腿栈追踪只含本次调用链(self):
        raw = _python_raw(self._SRC_PY)
        t1 = _block(raw, "T1")
        t2 = _block(raw, "T2")
        t3 = _block(raw, "T3")
        for tag, txt, want in (("T1", t1, "路径甲"), ("T2", t2, "路径乙"), ("T3", t3, "路径丙")):
            self.assertIn(want, txt, f"{tag} traceback 未含本次抛出点 {want}：{txt!r}\n原始输出:\n{raw}")
        self.assertNotIn("路径甲", t2, f"T2 traceback 带出前序帧：{t2!r}")
        self.assertNotIn("路径甲", t3, f"T3 traceback 带出前序帧：{t3!r}")
        self.assertNotIn("路径乙", t3, f"T3 traceback 带出前序帧：{t3!r}")


if __name__ == "__main__":
    unittest.main()
