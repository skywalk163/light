# -*- coding: utf-8 -*-
"""LH-41 / L-262：原生腿 `参数列表()` 比转译腿多返回 argv[0]（跨腿口径差 1）。

## 病灶

同一份源码、同一条 `light run <入口> -- 甲 乙`：

| 腿 | `参数列表()` |
|---|---|
| 转译腿（src / Python） | `['甲', '乙']` |
| 原生腿（native / LLVM） | `['<编译产物路径>', '甲', '乙']` ← 多一个 argv[0] |

转译腿的 `参数列表()` 读 CLI 注入的用户实参；原生腿走
`src/llvm/runtime_typed.c:dv_get_args`，从 `dv_init_args(argc, argv)` 的
**argv[0]** 开始返回 —— 原生产物是独立进程，argv[0] 是它自己的路径。
差 1 个元素不算崩，但凡有人写 `参数列表()[0]`，换后端就**静默**取到不同的东西。

## 修法（三处，见卡内说明）

1. `runtime_typed.c:dv_get_args` 从 `i = 1` 起（对齐 `sys.argv[1:]`）；
2. Windows 上 argv 是 CRT 按 ANSI/OEM 代码页解码来的（en-US runner 的 ACP=1252
   会把中文直接改写成 '?'），不是 UTF-8。T-0249 起 Windows 分支不再读 argc/argv，
   改走宽字符入口 `GetCommandLineW` + `CommandLineToArgvW`，逐格按 CP_UTF8
   窄化后重建 `_dv_argv`，与运行时「内部一律 UTF-8 字节流」的口径对齐；
3. `codegen_typed` 把 `用户参数` 一并登记（此前原生腿 `用户参数()` 是未定义名，
   同一条源码换后端就 NameError），与 `参数列表` 同走 `dv_get_args`；
4. `cli/light.py` 按 `--` 硬切并**真把实参传到产物命令行**
   （`subprocess.run([exe, *用户实参])`）；src 腿执行期把 `sys.argv` 设成这批实参，
   于是两条腿同源。

## 断言（任务卡验收 1、2）

1. 两腿 `参数列表()` **逐元素相等**（含长度），且都不含程序名/产物路径；
2. 两腿 `用户参数()` 同样相等；
3. 反跑有牙：把 runtime 的 `i = 1` 改回 `i = 0`、把 codegen 的 `用户参数`
   摘掉，源码级判据必须变红（证测试不是「怎么写都过」）。

无 clang 时原生腿部分跳过（不阻塞交付），但**会**在 summary 里写明「未能真跑」。
"""
import os
import subprocess
import sys
import tempfile
import unittest

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (_ROOT, os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tests.unit.test_T6B_时间系统内建_原生腿 import _find_msvc_env  # noqa: E402

# 原生腿每例真编译真跑（本机实测 ~4s/例），全量 xdist 并发时 clang 争抢会破全局
# --timeout=60（同 test_R130 的 R13C 加固口径）。
pytestmark = pytest.mark.timeout(300)
sys.dont_write_bytecode = True

# 探针：把两个内置都按元素打印出来，逐行对拍（不依赖 repr 口径）。
_探针 = '''导出 主。
段落 主:
  设 a 为 参数列表()
  设 u 为 用户参数()
  输出("AL=" 加上 转字符串(a.长度))
  设 i 为 0
  当 i 小于 a.长度:
    输出("A" 加上 转字符串(i) 加上 "=" 加上 a[i])
    设 i 为 i 加上 1
  输出("UL=" 加上 转字符串(u.长度))
  设 j 为 0
  当 j 小于 u.长度:
    输出("U" 加上 转字符串(j) 加上 "=" 加上 u[j])
    设 j 为 j 加上 1
'''


def _clang_available():
    try:
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


_需要原生腿 = unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿真跑")


def _env():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    return env


def _跑(源码, 实参, 后端=None, timeout=300):
    """真起进程跑 `python cli/light.py run <入口> [--backend native] -- <实参>`。

    返回 (rc, 非空 stdout 行, stderr 文本)。原生腿的实参必须真进产物命令行 ——
    这正是本卡要钉的那条链路，所以一律走 CLI、不走进程内直调。
    """
    with tempfile.TemporaryDirectory(prefix="_lh41_") as d:
        src = os.path.join(d, "main.light")
        with open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(源码)
        cmd = [sys.executable, os.path.join("cli", "light.py"), "run", src]
        if 后端:
            cmd += ["--backend", 后端, "--optimize", "O0"]
        got = subprocess.run(cmd + ["--", *实参], capture_output=True,
                             timeout=timeout, env=_env(), cwd=_ROOT)
    out = got.stdout.decode("utf-8", "replace").replace("\r", "")
    lines = [ln for ln in out.split("\n") if ln.strip()]
    return got.returncode, lines, got.stderr.decode("utf-8", "replace")


def _解析(lines):
    """把探针行解析成 {'参数列表': [...], '用户参数': [...]}，键只为逐元素对拍。"""
    got = {"参数列表": None, "用户参数": None}
    for line in lines:
        if line.startswith("AL="):
            got["参数列表"] = []
        elif line.startswith("UL="):
            got["用户参数"] = []
        elif line.startswith("A") and "=" in line and got["参数列表"] is not None:
            got["参数列表"].append(line.split("=", 1)[1])
        elif line.startswith("U") and "=" in line and got["用户参数"] is not None:
            got["用户参数"].append(line.split("=", 1)[1])
    return got


def _两腿(实参):
    """跑两腿，返回 (src 结果, native 结果, src 行, native 行)。"""
    src_rc, src_lines, src_err = _跑(_探针, 实参)
    nat_rc, nat_lines, nat_err = _跑(_探针, 实参, 后端="native")
    assert src_rc == 0, "转译腿 rc=%d\nstdout=%s\nstderr=%s" % (src_rc, src_lines, src_err[:2000])
    assert nat_rc == 0, "原生腿 rc=%d\nstdout=%s\nstderr=%s" % (nat_rc, nat_lines, nat_err[:3000])
    return _解析(src_lines), _解析(nat_lines), src_lines, nat_lines


# ── 一、验收 1：`参数列表()` 两腿逐元素相等 ────────────────────────────────────

class Test参数列表跨腿对拍(unittest.TestCase):
    """任务卡验收 1：两条腿的 `参数列表()` 逐元素相等（含长度）。"""

    def test_转译腿_恰为甲乙(self):
        src, _, src_lines, _ = _两腿(["甲", "乙"])
        self.assertEqual(src["参数列表"], ["甲", "乙"],
                         "转译腿口径变了：%s" % (src_lines,))

    @_需要原生腿
    def test_原生腿_恰为甲乙_不含argv0(self):
        _, nat, _, nat_lines = _两腿(["甲", "乙"])
        self.assertEqual(nat["参数列表"], ["甲", "乙"],
                         "原生腿仍多返回 argv[0]（L-262）：%s" % (nat_lines,))

    @_需要原生腿
    def test_两腿逐元素相等(self):
        """**本卡的主判据**：逐元素相等，长度也相等。"""
        src, nat, src_lines, nat_lines = _两腿(["甲", "乙"])
        self.assertEqual(nat["参数列表"], src["参数列表"],
                         "L-262 未销账：原生腿=%s 转译腿=%s"
                         % (nat_lines, src_lines))
        self.assertEqual(len(nat["参数列表"]), len(src["参数列表"]),
                         "两腿长度不等：原生 %d / 转译 %d"
                         % (len(nat["参数列表"]), len(src["参数列表"])))

    @_需要原生腿
    def test_原生腿长度不是三(self):
        """有牙齿的形状断言：`['产物路径','甲','乙']` 恰好是 3，不是 2。"""
        _, nat, _, _ = _两腿(["甲", "乙"])
        self.assertEqual(len(nat["参数列表"]), 2,
                         "原生腿长度 %d ≠ 2（多出的那一格就是 argv[0]）"
                         % len(nat["参数列表"]))


# ── 二、验收 2：`用户参数()` 两腿相等 ──────────────────────────────────────────

class Test用户参数跨腿对拍(unittest.TestCase):
    """`用户参数()` 是 `参数列表()` 的显式别名，原生腿此前根本没接线。"""

    def test_转译腿_用户参数(self):
        src, _, src_lines, _ = _两腿(["甲", "乙"])
        self.assertEqual(src["用户参数"], ["甲", "乙"],
                         "转译腿 用户参数 口径变了：%s" % (src_lines,))

    @_需要原生腿
    def test_原生腿_用户参数_不再未定义(self):
        """修前这条在原生腿直接 NameError（`用户参数` 没登记进 codegen）。"""
        _, nat, _, nat_lines = _两腿(["甲", "乙"])
        self.assertEqual(nat["用户参数"], ["甲", "乙"],
                         "原生腿 用户参数 口径错了：%s" % (nat_lines,))

    @_需要原生腿
    def test_两腿用户参数逐元素相等(self):
        src, nat, src_lines, nat_lines = _两腿(["甲", "乙"])
        self.assertEqual(nat["用户参数"], src["用户参数"],
                         "用户参数 两腿不一致：原生=%s 转译=%s"
                         % (nat_lines, src_lines))

    @_需要原生腿
    def test_用户参数与参数列表同源(self):
        """同一个程序里两个名字必须是同一批东西（不能一腿多一格）。"""
        src, nat, _, _ = _两腿(["甲", "乙"])
        self.assertEqual(src["用户参数"], src["参数列表"])
        self.assertEqual(nat["用户参数"], nat["参数列表"])


# ── 三、边界：空实参 / 空格中文引号 / 形如 CLI 选项的实参 ──────────────────────

class Test边界实参(unittest.TestCase):
    """`--` 之后什么都可能是数据（含空格、中文、引号、形如选项的串）。"""

    @_需要原生腿
    def test_双横线后为空_两腿都空(self):
        src, nat, _, _ = _两腿([])
        self.assertEqual(src["参数列表"], [])
        self.assertEqual(nat["参数列表"], [],
                         "空实参下原生腿仍返回了 %s" % (nat["参数列表"],))

    @_需要原生腿
    def test_空格中文引号原样到达(self):
        argv = ["a b", "中文", '带"引号"']
        src, nat, src_lines, nat_lines = _两腿(argv)
        self.assertEqual(src["参数列表"], argv)
        self.assertEqual(nat["参数列表"], argv,
                         "原生腿实参被改写：%s" % (nat_lines,))
        self.assertEqual(nat["参数列表"], src["参数列表"])

    @_需要原生腿
    def test_形如CLI选项的实参不被吞也两腿一致(self):
        """`--` 之后的 `--backend native` 只是脚本实参，两腿都必须原样接住。"""
        src, nat, _, nat_lines = _两腿(["--backend", "native"])
        self.assertEqual(src["参数列表"], ["--backend", "native"])
        self.assertEqual(nat["参数列表"], ["--backend", "native"],
                         "原生腿没接住形如选项的实参：%s" % (nat_lines,))


# ── 四、源码级守（行为之外钉住实现形态）──────────────────────────────────────

class Test源码级守(unittest.TestCase):
    """行为对拍挡不住「两边都错成同一形态」的退化，故补源码级判据。"""

    @staticmethod
    def _runtime():
        with open(os.path.join(_ROOT, "src", "llvm", "runtime_typed.c"),
                  encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _codegen():
        with open(os.path.join(_ROOT, "src", "llvm", "codegen_typed.py"),
                  encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _dv_get_args_body(text):
        """精确截取 dv_get_args 函数体（到首个 `\\n}` 为止）。"""
        i = text.find("void dv_get_args(LightValue* result) {")
        assert i > 0, "runtime 找不到 dv_get_args 定义"
        j = text.find("\n}", i)
        assert j > i, "dv_get_args 函数体未闭合"
        return text[i:j]

    def test_runtime_从下标1起(self):
        body = self._dv_get_args_body(self._runtime())
        self.assertIn("for (int i = 1; i < _dv_argc; i++)", body,
                      "dv_get_args 又从 argv[0] 开始了（L-262 回归）")
        self.assertNotIn("for (int i = 0; i < _dv_argc; i++)", body,
                         "dv_get_args 仍从 argv[0] 起 —— 跨腿口径又差 1")

    def test_runtime_Windows走宽字符入口(self):
        """T-0249：Windows 上必须从宽字符命令行取参，不能再按 ACP 猜编码。"""
        text = self._runtime()
        self.assertIn("_dv_arg_to_str", text, "找不到 argv→UTF-8 的转换入口")
        body = self._dv_get_args_body(text)
        self.assertIn("_dv_arg_to_str(&elem, _dv_argv[i])", body,
                      "dv_get_args 没走统一的 argv→UTF-8 转换")

        i = text.find("static char* _dv_wide_to_utf8")
        self.assertGreater(i, 0, "找不到宽字符→UTF-8 的转换入口")
        conv = text[i:]
        conv = conv[:conv.find("\n}\n") + 3]
        self.assertIn("CP_UTF8", conv, "宽字符没有按 UTF-8 窄化")

        j = text.find("static void _dv_init_args_win")
        self.assertGreater(j, 0, "找不到 Windows 宽字符取参入口")
        init = text[j:]
        init = init[:init.find("\n}\n") + 3]
        self.assertIn("GetCommandLineW", init,
                      "Windows 取参没走宽字符命令行（en-US runner 上中文会被改写成 '?'）")
        self.assertIn("CommandLineToArgvW", init,
                      "Windows 取参没走宽字符解析")

        # 有牙：旧的两跳 ACP 转码不能留在 argv 链路上（否则 en-US runner 必红）
        k = text.find("static void _dv_arg_to_str")
        self.assertGreater(k, 0, "找不到 _dv_arg_to_str")
        argconv = text[k:]
        argconv = argconv[:argconv.find("\n}\n") + 3]
        self.assertNotIn("CP_ACP", argconv,
                         "argv 仍在按 ACP 猜编码（L-262 在 en-US runner 上的病灶）")

    def test_codegen_用户参数已接线(self):
        src = self._codegen()
        i = src.find("if name in ('参数列表'")
        self.assertGreater(i, 0, "codegen 找不到 参数列表 分派分支")
        j = src.find("if name in ('整数'", i)
        self.assertGreater(j, i, "找不到 参数列表 分支的结束边界")
        body = src[i:j]
        self.assertIn("用户参数", body,
                      "原生腿仍不认 用户参数（同一条源码换后端就 NameError）")
        self.assertIn("dv_get_args", body, "用户参数 必须与 参数列表 同走 dv_get_args")

    def test_cli_实参真传到产物(self):
        with open(os.path.join(_ROOT, "cli", "light.py"), encoding="utf-8") as f:
            cli = f.read()
        i = cli.find("结果 = subprocess.run([exe")
        self.assertGreater(i, 0, "找不到 _run_native 起产物的那行")
        line = cli[i:cli.find("\n", i)]
        self.assertIn("用户实参", line,
                      "起产物时没把 `--` 后的实参传进去（原生腿会收到空 argv）")


# ── 五、反跑有牙 ─────────────────────────────────────────────────────────────

class Test反跑有牙(unittest.TestCase):
    """证明测试真能红：把修法变异回旧形态，同一判据必须失败。

    做法是把源码文本变异后再施加同一判据（与 R154 同款装置），
    原文件一个字节都不动 —— 这不是「改期望消红」。
    """

    @staticmethod
    def _runtime():
        with open(os.path.join(_ROOT, "src", "llvm", "runtime_typed.c"),
                  encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _codegen():
        with open(os.path.join(_ROOT, "src", "llvm", "codegen_typed.py"),
                  encoding="utf-8") as f:
            return f.read()

    def test_反跑_从argv0起会被抓住(self):
        real = self._runtime()
        i = real.find("void dv_get_args(LightValue* result) {")
        j = real.find("\n}", i)
        self.assertGreater(j, i)
        body = real[i:j]
        self.assertIn("for (int i = 1; i < _dv_argc; i++)", body,
                      "真实 runtime 里没有 i=1 的循环，本轮修复未落地")
        # 正形态变异：把循环头改回 `i = 0`（= R154 前的旧实现），
        # 再施加与 test_runtime_从下标1起 完全相同的判据 —— 必须变红。
        mutated = real[:i] + body.replace(
            "for (int i = 1; i < _dv_argc; i++)",
            "for (int i = 0; i < _dv_argc; i++)", 1) + real[j:]
        mi = mutated.find("void dv_get_args(LightValue* result) {")
        mbody = mutated[mi:mutated.find("\n}", mi)]
        self.assertIn("for (int i = 0; i < _dv_argc; i++)", mbody,
                      "反跑装置失效：变异体没变成从 argv[0] 起")
        self.assertNotIn("for (int i = 1; i < _dv_argc; i++)", mbody,
                         "反跑装置失效：变异体里仍留着 i=1 的循环")

    def test_反跑_摘掉用户参数会被抓住(self):
        real = self._codegen()
        i = real.find("if name in ('参数列表'")
        j = real.find("if name in ('整数'", i)
        self.assertGreater(j, i)
        mutated = real[:i] + "if name in ('参数列表', 'argv', 'args'):\n            return self._call_dv_func('dv_get_args'), 'dv'\n\n        " + real[j:]
        mi = mutated.find("if name in ('参数列表'")
        mj = mutated.find("if name in ('整数'", mi)
        self.assertNotIn("用户参数", mutated[mi:mj],
                         "反跑装置失效：变异体里仍有 用户参数")
        self.assertIn("用户参数", real[i:j],
                      "真实 codegen 里没登记 用户参数，本轮修复未落地")


if __name__ == "__main__":
    unittest.main()
