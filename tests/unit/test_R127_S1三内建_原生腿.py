# -*- coding: utf-8 -*-
"""
R127-C 定向用例：S1 三内建 是字母/是空白/是文件 原生腿 O0 反跑。

背景：R114 曾登记「S1 降级桩未覆盖三内建」。R127-C 核实——原生腿此前对这三名
裸调用直接报「未定义的段落」（响亮拒绝，非静默），本次在 _gen_typed_builtin
判型族区补齐派发：
  - 是字母/是空白 → runtime 新增 dv_str_isalpha / dv_str_isspace
    （对齐 Python str.isalpha/str.isspace 整串语义：非空且每字符通过；
    ASCII 判定，Unicode 砍线见 runtime_typed.c 注释）
  - 是文件 → 复用 runtime 既有 dv_is_file（os.path.isfile 语义，
    与 文件存在 的 access(F_OK) 口径区分：目录判假）

与 Python 腿 stdlib/builtins.py（是文件:155 / 是字母:917 / 是空白:933）同输入
对拍，11/11 逐条一致（见测试内预期值，来源：stdlib 直调实测）。

「编译 + 运行」整体 fork 到独立子进程（复用 _t6b_native_helper.py，见其头部
说明：内存受限机防 clang OOM）。
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

_SRC = """导出 主。
段落 主:
  输出("字母a=" 加上 转字符串(是字母("a")))
  输出("字母Z=" 加上 转字符串(是字母("Z")))
  输出("字母1=" 加上 转字符串(是字母("1")))
  输出("字母空=" 加上 转字符串(是字母("")))
  输出("空白空格=" 加上 转字符串(是空白(" ")))
  输出("空白制表=" 加上 转字符串(是空白("\\t")))
  输出("空白x=" 加上 转字符串(是空白("x")))
  输出("空白空=" 加上 转字符串(是空白("")))
  输出("文件有=" 加上 转字符串(是文件("stdlib/builtins.py")))
  输出("文件目录=" 加上 转字符串(是文件("stdlib")))
  输出("文件无=" 加上 转字符串(是文件("stdlib/不存在_R127.light")))
"""

# 与 Python 腿 stdlib/builtins.py 同输入实测对拍（真/假 逐条一致）
_EXPECT = {
    "字母a": "真", "字母Z": "真", "字母1": "假", "字母空": "假",
    "空白空格": "真", "空白制表": "真", "空白x": "假", "空白空": "假",
    "文件有": "真", "文件目录": "假", "文件无": "假",
}


def _native_run(src_text, timeout=240):
    """以内联 .light 源码走原生腿 O0 编译并运行，返回 {KEY: 值}。"""
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t6b_native_helper.py")
    env = dict(os.environ)
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    # 是文件 需要相对 stdlib 路径：子进程 cwd 固定到仓库根
    try:
        with tempfile.TemporaryDirectory(prefix="_r127c_") as d:
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
    out = {}
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
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


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class R127S1三内建反跑(unittest.TestCase):
    """是字母/是空白/是文件 原生腿 O0 定向反跑（R127-C）。"""

    def test_三内建_双腿对拍(self):
        out = _native_run(_SRC)
        for key, want in _EXPECT.items():
            got = out.get(key)
            self.assertEqual(
                got, want,
                f"{key}: 原生腿={got!r} 期望={want!r}（Python 腿 stdlib 实测）",
            )


if __name__ == "__main__":
    unittest.main()
