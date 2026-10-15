# -*- coding: utf-8 -*-
"""R150-A：文件系统建议锁（文件锁定 / 文件解锁）—— 双腿对拍 + 源码级守单点 + 参考实现对拍。

背景（L-212）：`stdlib/文件系统.light` 首行含魔数「纯光明实现」→ `_light_import_hook`
在运行期用它接管同名 `.py`。但它只有 129 段、`.py` 有 115 个函数，其中缺的
`文件锁定/文件解锁` 直接导致 `tests/test_filesystem.py::Test文件锁定` 4 条红
（`AttributeError: module 'stdlib.文件系统' has no attribute '文件锁定'`）。
该缺口**在本机 Windows 上就能复现**，不是 FreeBSD 平台差异。

修复走 R149-A 实证的「四处齐全」铁律（缺一处就报误导性错误）：
  1. `src/llvm/runtime_typed.c`：C 原语 `dv_fs_lock` / `dv_fs_unlock`
     （POSIX flock / Windows LockFileEx，进程内 static 锁表 path→fd）；
  2. `src/llvm/codegen_typed.py`：`declare` + `_gen_typed_builtin` 分派（含中英别名）；
  3. `src/code_generator.py`：`builtin_map` 裸名条目（缺了会报「变量必须先定义后使用」）；
  4. `stdlib/builtins.py`：src 腿地板实体（缺了 `_light_builtin` 代理 AttributeError）。

语义（与 `stdlib/文件系统.py` 逐条对齐，测试即判据）：
  * 锁定不存在的路径 → O_CREAT 自动建出来，返回 真；
  * 重复锁定 → 复用既有 fd，仍返回 真（不泄漏句柄）；
  * 解锁 → 关 fd、撤登记，返回 真；
  * **重复解锁 → 返回 假**（未登记路径解锁为假）。
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


def _fwd(p):
    return p.replace("\\", "/")


# 已知两腿 repr 分歧（R148 已登记候选，非本轮回归）：打印标量布尔时
# native 输出「真/假」、src 输出「True/False」。对拍前归一化。
_BOOL_REPR = {"真": "True", "假": "False"}


def _kv(out):
    d = {}
    for ln in out.splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            v = v.strip()
            d[k.strip()] = _BOOL_REPR.get(v, v)
    return d


def _build_src(目标路径):
    """只调**已注册内置**（文件锁定/文件解锁/文件存在）。

    ⚠️ 三个坑都要避开（R149-A 实证）：
      1. 不能用 创建临时目录/写文件（原生腿无地板原语）→ 测试侧用 Python 建 dir；
      2. 不能嵌套调用（原生腿解析器会把内层名当未定义变量）；
      3. 不能调 stdlib 门面段（原生腿不做模块解析）。
    """
    return (
        "段落 主():\n"
        "  打印(\"create=\", 文件存在('%s'))\n"
        "  打印(\"lock1=\", 文件锁定('%s'))\n"
        "  打印(\"lock2=\", 文件锁定('%s'))\n"
        "  打印(\"created=\", 文件存在('%s'))\n"
        "  打印(\"unlock1=\", 文件解锁('%s'))\n"
        "  打印(\"unlock2=\", 文件解锁('%s'))\n"
    ) % ((目标路径,) * 6)


def _native_run(src_text, timeout=300):
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t6b_native_helper.py")
    env = dict(os.environ)
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    try:
        with tempfile.TemporaryDirectory(prefix="_r150a_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8") as f:
                f.write(src_text)
            exe = os.path.join(d, "main")
            proc = subprocess.run(
                [sys.executable, helper, src, exe],
                capture_output=True, timeout=timeout + 60, env=env, cwd=_ROOT,
            )
    except subprocess.TimeoutExpired:
        raise AssertionError("原生腿编译/运行超时（>%ss）" % timeout)
    if proc.returncode != 0:
        raise AssertionError(
            "原生腿编译/运行失败 rc=%d\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (proc.returncode, proc.stdout.decode("utf-8", "replace"),
               proc.stderr.decode("utf-8", "replace")[:3000])
        )
    return proc.stdout.decode("utf-8", "replace")


def _src_run(src_text, timeout=180):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    with tempfile.TemporaryDirectory(prefix="_r150a_py_") as d:
        src = os.path.join(d, "main.light")
        with open(src, "w", encoding="utf-8") as f:
            f.write(src_text)
        proc = subprocess.run(
            [sys.executable, os.path.join("cli", "light.py"), "run", src],
            capture_output=True, timeout=timeout, env=env, cwd=_ROOT,
        )
    if proc.returncode != 0:
        raise AssertionError(
            "src 腿运行失败 rc=%d\nSTDERR:\n%s"
            % (proc.returncode, proc.stderr.decode("utf-8", "replace")[:2000])
        )
    return proc.stdout.decode("utf-8", "replace")


class R150_文件锁_源码级守单点(unittest.TestCase):
    """守单点：新增内置必须「四处齐全」，缺一处就报误导性错误（R149-A 实证）。"""

    def test_codegen_注册两个内置(self):
        p = os.path.join(_ROOT, "src", "llvm", "codegen_typed.py")
        s = open(p, encoding="utf-8").read()
        for fn in ("dv_fs_lock", "dv_fs_unlock"):
            self.assertIn("declare void @%s" % fn, s, "codegen 缺 declare: %s" % fn)
        for nm in ("文件锁定", "文件解锁"):
            self.assertIn("'%s'" % nm, s, "codegen 缺内置分派名: %s" % nm)

    def test_runtime_导出两个C符号(self):
        p = os.path.join(_ROOT, "src", "llvm", "runtime_typed.c")
        s = open(p, encoding="utf-8").read()
        for fn in ("dv_fs_lock", "dv_fs_unlock"):
            self.assertIn("void %s(" % fn, s, "runtime 缺 C 定义: %s" % fn)
        # 锁表是「解锁时能按路径查回 fd」的前提，必须存在
        self.assertIn("_dv_lock_find", s, "runtime 缺锁表查找：_dv_lock_find")
        # POSIX flock 常量在 sys/file.h（glibc 不一定经 fcntl.h 带出）
        self.assertIn("#include <sys/file.h>", s, "runtime 缺 #include <sys/file.h>")

    def test_builtin_map_补裸名条目(self):
        """缺了这一处，原生腿会报「变量必须先定义后使用」这种误导性错误。"""
        p = os.path.join(_ROOT, "src", "code_generator.py")
        s = open(p, encoding="utf-8").read()
        for nm in ("文件锁定", "文件解锁"):
            self.assertIn("'%s': '_light_builtin.%s'" % (nm, nm), s,
                          "builtin_map 缺条目: %s" % nm)

    def test_builtins_补src腿地板实体(self):
        p = os.path.join(_ROOT, "stdlib", "builtins.py")
        s = open(p, encoding="utf-8").read()
        for nm in ("文件锁定", "文件解锁"):
            self.assertIn("def %s(" % nm, s, "builtins.py 缺地板实体: %s" % nm)

    def test_light门面段已补(self):
        p = os.path.join(_ROOT, "stdlib", "文件系统.light")
        s = open(p, encoding="utf-8").read()
        for nm in ("文件锁定", "文件解锁"):
            self.assertIn("段落 %s(" % nm, s, "文件系统.light 缺门面段: %s" % nm)
            self.assertIn(nm, s.split("导出")[-1][:600],
                          "文件系统.light 导出清单缺: %s" % nm)


class R150_文件锁_参考实现对拍(unittest.TestCase):
    """以 `stdlib/文件系统.py` 为黄金 oracle，验证 src 腿语义逐条对齐。"""

    def test_语义四条性质(self):
        sys.path.insert(0, _ROOT)
        try:
            import stdlib.文件系统 as fs
        finally:
            sys.path.remove(_ROOT)
        with tempfile.TemporaryDirectory(prefix="_r150a_fs_") as td:
            # 1) 不存在的路径会被自动创建
            目标 = os.path.join(td, "不该存在.lock")
            self.assertFalse(os.path.exists(目标), "前置：目标文件应不存在")
            self.assertTrue(fs.文件锁定(目标), "锁定不存在的路径应自动创建并返回真")
            self.assertTrue(os.path.exists(目标), "锁定后文件应被建出来")
            # 2) 重复锁定仍为真
            self.assertTrue(fs.文件锁定(目标), "重复锁定应复用 fd 并返回真")
            # 3) 解锁返回真
            self.assertTrue(fs.文件解锁(目标), "首次解锁应返回真")
            # 4) 重复解锁返回假
            self.assertFalse(fs.文件解锁(目标), "重复解锁应返回假")

    def test_共享锁(self):
        sys.path.insert(0, _ROOT)
        try:
            import stdlib.文件系统 as fs
        finally:
            sys.path.remove(_ROOT)
        with tempfile.TemporaryDirectory(prefix="_r150a_sh_") as td:
            目标 = os.path.join(td, "shared.lock")
            self.assertTrue(fs.文件锁定(目标, 共享=True), "共享锁应返回真")
            self.assertTrue(fs.文件解锁(目标), "共享锁解锁应返回真")


@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0],
                 "未定位到 MSVC/Windows SDK 头，跳过原生腿")
class R150_文件锁_双腿对拍(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory(prefix="_r150a_run_")
        # ⚠️ 两条腿**必须各用一份目标路径**：文件锁定会 O_CREAT 把文件建出来，
        # 共用一条路径的话先跑的那条腿会把后跑的那条的「前置：文件不存在」变成假，
        # 得到「两腿分歧 create：native=False src=True」这种纯测试装置的假红。
        # ⚠️ 父目录必须真的存在：文件锁定要对「不存在的文件」O_CREAT，
        # 但不会递归建父目录。忘了 mkdir 会让两条腿**一起返回假**，
        # 于是「两腿一致」这种断言反而假绿——真正的语义断言才把它抓出来。
        目录_native = os.path.join(self._td.name, "native")
        目录_src = os.path.join(self._td.name, "src")
        os.makedirs(目录_native, exist_ok=True)
        os.makedirs(目录_src, exist_ok=True)
        self._src_native = _build_src(_fwd(os.path.join(目录_native, "target.lock")))
        self._src_src = _build_src(_fwd(os.path.join(目录_src, "target.lock")))

    def tearDown(self):
        self._td.cleanup()

    def test_双腿逐项一致(self):
        n = _kv(_native_run(self._src_native))
        s = _kv(_src_run(self._src_src))
        for k in ("create", "lock1", "lock2", "created", "unlock1", "unlock2"):
            self.assertIn(k, n, "原生腿缺输出项 %s：%s" % (k, n))
            self.assertIn(k, s, "src 腿缺输出项 %s：%s" % (k, s))
            self.assertEqual(n[k], s[k],
                             "两腿分歧 %s：native=%s src=%s" % (k, n[k], s[k]))

    def test_语义四条性质在原生腿同样成立(self):
        d = _kv(_native_run(self._src_native))
        self.assertEqual(d["create"], "False", "前置：目标文件应不存在")
        self.assertEqual(d["lock1"], "True", "锁定不存在的路径应自动创建并返回真")
        self.assertEqual(d["created"], "True", "锁定后文件应被建出来")
        self.assertEqual(d["lock2"], "True", "重复锁定应返回真")
        self.assertEqual(d["unlock1"], "True", "首次解锁应返回真")
        self.assertEqual(d["unlock2"], "False", "重复解锁应返回假")


if __name__ == "__main__":
    unittest.main()
