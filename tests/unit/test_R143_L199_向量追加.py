# -*- coding: utf-8 -*-
"""
R143-B 定向用例：L-199 向量 `追加` 2 参函数式调用在 src 腿被截胡为 0 参 `builtins.追加`。

背景：`src/code_generator.py::builtin_map` 把关键字 `追加` 映射为 `'_light_builtin.追加'`
      （:559）；而 `stdlib/builtins.py:1391` 的 `追加` 是
      `def 追加() -> int: return os.O_APPEND`（0 参文件打开标志）。`向量.light` 等
      20+ 个 stdlib `.light` 用函数式 2 参 `追加(结果, x)`，被截胡成 0 参实现 →
      `TypeError: 追加() takes 0 positional arguments but 2 were given`。

根因：builtin_map 是「单一名字 → 单一目标」的映射，无法表达同名不同 arity 的双重身份。
      原生腿 `src/llvm/codegen_typed.py:2606-2613` 早已按 arity 派发（2 参走
      `dv_list_append`、0 参返回 0 作文件标志），唯独 Python 转译腿缺这一步。

修复：`src/code_generator.py` ParagraphCall 分支补 arity 感知派发——
      裸函数式 `追加(a, b)`（≥2 参）→ `_light_builtin.列表追加`（list.append 语义）；
      0 参 `追加()` 保留原映射 `_light_builtin.追加`（文件标志，路径护栏.light:420 依赖）。
      ⚠️ 仅作用于**裸函数式调用**；`表.追加(x)` 方法形态走 method_name_map 的
      '追加'→'append'，不受影响；类方法体内的裸 `追加()`（如路径护栏.追加标志）
      也保留文件标志语义。

双腿对拍：同一份源码分别走 src（转译腿）与原生腿，逐条断言一致。
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
from tests.unit.test_R131_L186L187_原生腿 import _native_raw, _clang_available  # noqa: E402

# A1：2 参函数式 `追加(结果, 9)` —— 修复前 TypeError，修复后 [9]
A1 = """段落 主():
  设 结果 为 新建列表()
  追加(结果, 9)
  输出("追加2参=" 加上 转字符串(结果))
"""

# A2：0 参 `追加()` 文件标志 —— 修复后仍走 builtins.追加（O_APPEND），
#     必须保留（路径护栏.light:420 依赖它拼 open 标志位）
A2 = """段落 主():
  输出("追加0参=" 加上 转字符串(追加()))
"""

# A3：方法形态 `表.追加(x)` —— 走 method_name_map '追加'→'append'，不受 L-199 修复影响
A3 = """段落 主():
  设 表 为 []
  表.追加(5)
  输出("方法追加=" 加上 转字符串(表))
"""

# A4：2 参 `追加(结果, x)` 与原生腿返回新列表（原生 dv_list_append 原地 append 并返回列表），
#     src 腿 `_light_builtin.列表追加` 返回 None；两腿结果值一致但**返回值分歧**已登记，
#     此处只断言结果列表内容一致（返回值语义不在 L-199 收口范围）
A4 = """段落 主():
  设 结果 为 新建列表()
  追加(结果, 1.5)
  追加(结果, 2.5)
  输出("多次追加=" 加上 转字符串(结果))
"""

# A5：混合场景 —— 文件标志常量 与 列表追加 在同一模块内共存
A5 = """类 标志机:
  段落 追加标志:
    返回 追加()
段落 主():
  设 m 为 新建 标志机()
  输出("类内0参=" 加上 转字符串(m.追加标志()))
  设 结果 为 新建列表()
  追加(结果, 7)
  输出("模块2参=" 加上 转字符串(结果))
"""

_EXPECT = {
    "追加2参": "[9]",
    "方法追加": "[5]",
    "多次追加": "[1.5, 2.5]",
    "模块2参": "[7]",
}


def _src_run(src_text, timeout=120):
    """以内联 .light 源码走转译腿（src 后端）运行，返回原始 stdout 文本。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        with tempfile.TemporaryDirectory(prefix="_r143_l199_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8") as f:
                f.write(src_text)
            proc = subprocess.run(
                [sys.executable, os.path.join("cli", "light.py"), "run", src, "--backend", "src"],
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


def _keyvals(raw):
    out = {}
    for ln in raw.splitlines():
        if "=" in ln:
            k, _, v = ln.strip().partition("=")
            out[k.strip()] = v.strip()
    return out


class R143L199向量追加(unittest.TestCase):
    """L-199：src 腿 `追加` 按 arity 派发，2 参不再被截胡成 0 参文件标志。"""

    def test_A1_2参追加不再TypeError(self):
        out = _keyvals(_src_run(A1))
        self.assertEqual(out.get("追加2参"), "[9]",
                         f"追加2参：src 腿={out.get('追加2参')!r} 期望=[9]")

    def test_A2_0参追加保留文件标志(self):
        out = _keyvals(_src_run(A2))
        self.assertIn("追加0参", out,
                      "0 参 `追加()` 必须保留文件标志语义（路径护栏.light:420 依赖）")
        # 平台相关的 O_APPEND：Windows=8, POSIX=1024
        self.assertIn(out["追加0参"], ("8", "1024"),
                      f"追加0参应返回 O_APPEND 值，实际={out['追加0参']!r}")

    def test_A3_方法形态不受影响(self):
        out = _keyvals(_src_run(A3))
        self.assertEqual(out.get("方法追加"), "[5]")

    def test_A4_多次追加(self):
        out = _keyvals(_src_run(A4))
        self.assertEqual(out.get("多次追加"), "[1.5, 2.5]")

    def test_A5_类内0参与模块2参共存(self):
        out = _keyvals(_src_run(A5))
        self.assertIn("类内0参", out)
        self.assertIn(out["类内0参"], ("8", "1024"),
                      f"类方法内裸 追加() 应保留文件标志语义，实际={out['类内0参']!r}")
        self.assertEqual(out.get("模块2参"), "[7]")

    def test_向量light_src腿可运行(self):
        """生产用例：`零向量(3)` 走 src 腿不再 TypeError（L-199 原始现象）。"""
        src = """从 向量 导入 零向量。
段落 主():
  设 v 为 零向量(3)
  输出("向量=" 加上 转字符串(v))
"""
        out = _keyvals(_src_run(src))
        self.assertEqual(out.get("向量"), "[0.0, 0.0, 0.0]",
                         f"向量.light src 腿应能跑通，实际={out.get('向量')!r}")

    @unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿对拍")
    @unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
    def test_双腿对拍2参追加一致(self):
        """2 参 `追加` 双腿结果一致（A1/A4）。返回值语义分歧已登记，不在本用例断言。"""
        for name, src_text in (("A1", A1), ("A4", A4)):
            out_s = _keyvals(_src_run(src_text))
            out_n = _keyvals(_native_raw(src_text))
            for key, want in _EXPECT.items():
                if key not in out_s:
                    continue
                if key not in out_n:
                    continue
                self.assertEqual(
                    out_s.get(key), out_n.get(key),
                    f"{name} {key}: src={out_s.get(key)!r} native={out_n.get(key)!r}",
                )


if __name__ == "__main__":
    unittest.main()