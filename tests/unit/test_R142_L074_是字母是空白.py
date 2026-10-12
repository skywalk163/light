# -*- coding: utf-8 -*-
"""
R142-C 定向用例：L-074 补齐转译腿 builtin_map 的 是字母/是空白（src 后端）。

背景：`src/code_generator.py::builtin_map` 的类型检查段此前只登记到 是数字符，
      缺 `是字母`/`是空白`。unified 腿（code_generator_unified.py:297/299）与
      原生腿（codegen_typed.py _gen_typed_builtin，R127-C 已支持）都有，唯独
      转译腿用这两名报「未定义的段落 / NameError」。本用例把补上的两条映射钉住。

修复：builtin_map 补
        '是字母': '_light_builtin.是字母',
        '是空白': '_light_builtin.是空白',
      并同步 fallback 映射表（stdlib 加载失败时兜底）补
        ('是字母', lambda v: isinstance(v, str) and v.isalpha()),
        ('是空白', lambda v: isinstance(v, str) and v.isspace()),
      与 stdlib/内置核心判型.light:55/67 的 str.isalpha/str.isspace 整串语义对齐。

双腿对拍：同一份源码分别走 src（转译腿）与原生腿，逐条断言一致（ASCII 边界值）。
⚠️ 原生腿 dv_str_isalpha/dv_str_isspace 是 ASCII 判定（R127-C 已登记 Unicode 砍线），
      故用例只覆盖 ASCII 字符；`是字母("中")` 这类 Unicode 属已登记砍线，不在此断言。
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

_SRC = """导出 主。
段落 主:
  输出("字母a=" 加上 转字符串(是字母("a")))
  输出("字母Z=" 加上 转字符串(是字母("Z")))
  输出("字母1=" 加上 转字符串(是字母("1")))
  输出("字母空=" 加上 转字符串(是字母("")))
  输出("字母ab=" 加上 转字符串(是字母("ab")))
  输出("空白空格=" 加上 转字符串(是空白(" ")))
  输出("空白制表=" 加上 转字符串(是空白("\\t")))
  输出("空白换行=" 加上 转字符串(是空白("\\n")))
  输出("空白x=" 加上 转字符串(是空白("x")))
  输出("空白空=" 加上 转字符串(是空白("")))
  输出("空白两空格=" 加上 转字符串(是空白("  ")))
"""

# 与 stdlib/内置核心判型.light:55/67 同输入实测对拍（真/假 逐条一致）
_EXPECT = {
    "字母a": "真", "字母Z": "真", "字母1": "假", "字母空": "假", "字母ab": "真",
    "空白空格": "真", "空白制表": "真", "空白换行": "真", "空白x": "假",
    "空白空": "假", "空白两空格": "真",
}


def _src_run(src_text, timeout=120):
    """以内联 .light 源码走转译腿（src 后端）运行，返回原始 stdout 文本。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        with tempfile.TemporaryDirectory(prefix="_r142_l074_") as d:
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
    """把 `KEY=VALUE` 行解析成 {KEY: VALUE}。"""
    out = {}
    for ln in raw.splitlines():
        if "=" in ln:
            k, _, v = ln.strip().partition("=")
            out[k.strip()] = v.strip()
    return out


class R142L074转译腿是字母是空白(unittest.TestCase):
    """L-074：转译腿补 是字母/是空白 后，逐条与显式期望一致。"""

    def test_src腿逐条与显式期望一致(self):
        out = _keyvals(_src_run(_SRC))
        for key, want in _EXPECT.items():
            self.assertEqual(
                out.get(key), want,
                f"{key}: src 腿={out.get(key)!r} 期望={want!r}\n原始输出:\n{out}",
            )
        # 确保探针真的跑到了全部 11 个键（防断言静默跳过）
        self.assertEqual(
            set(out.keys()), set(_EXPECT.keys()),
            f"src 腿输出键集合与期望不一致：{set(out.keys())} vs {set(_EXPECT.keys())}",
        )

    @unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿对拍")
    @unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
    def test_双腿对拍ASCII边界一致(self):
        out_s = _keyvals(_src_run(_SRC))
        out_n = _keyvals(_native_raw(_SRC))
        for key in _EXPECT:
            self.assertEqual(
                out_s.get(key), out_n.get(key),
                f"{key}: src={out_s.get(key)!r} native={out_n.get(key)!r}",
            )


if __name__ == "__main__":
    unittest.main()