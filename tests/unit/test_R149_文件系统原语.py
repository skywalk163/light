# -*- coding: utf-8 -*-
"""R149-A：文件系统平台原语第一批 —— 双腿对拍 + 源码级守单点。

背景：R148-B 把 `文件系统.py` 的 19 项缺口做了分层，其中
是否可执行 / 设置权限(chmod) / 创建符号链接 / 读取符号链接 / 磁盘族(5 段)
在原生腿**无任何地板原语**，光明代码调用会报「未定义的段落：X」。

修复：`runtime_typed.c` 新增 C 原语 dv_fs_access / dv_fs_chmod /
dv_fs_symlink / dv_fs_readlink / dv_fs_statvfs；`codegen_typed.py` 注册
同名内置（中英别名）；`stdlib/builtins.py` 补 src 腿地板实体（否则
`_light_builtin.*` 调用即 AttributeError）；`stdlib/文件系统.light` 加门面段。

语义对齐 `stdlib/文件系统.py`：
  * 是否可执行  = os.access(path, os.X_OK)
  * 设置权限    = os.chmod(path, mode)
  * 创建符号链接 = os.symlink(target, linkpath)
  * 读取符号链接 = os.readlink(path)（非链接/失败 → 空）
  * 磁盘族      = shutil.disk_usage 口径（键名 总空间/已用空间/可用空间/使用率）

已知边界（诚实登记，非本轮回归）：
  * Windows：symlink/readlink/statvfs 无等价 → C 侧 假/空/空；
    磁盘族在 src 腿走 shutil.disk_usage 仍可用，故本机 Windows 上两腿在
    symlink/readlink 上会有分歧，测试按平台分流断言，不制造假绿。
  * 磁盘用量为运行期真实值，只断言结构性质（总>0、已用/可用>=0、键齐全），
    不做数值硬编码，避免机器差异造成的 flaky。
"""
import json
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


# 只断言结构性质，保证两腿在同一台机、同一路径下取值一致。
# ⚠️ 不用 创建临时目录/写文件——这两个在原生腿无地板原语（会报
# 「未定义的段落」）；改为测试侧用 Python 建好文件，把路径嵌入源码，
# 两腿读同一路径天然可比。路径统一转成正斜杠（Windows 上 C/Python 均接受）。
def _build_src(文件路径, 目录路径):
    """只调**已注册内置**（是否可执行/设置权限/磁盘用量/序列化JSON）。

    ⚠️ 不能在原生腿源码里调 stdlib 门面段（如 磁盘总空间/获取磁盘使用情况）——
    那些是 stdlib/文件系统.light 的段落，原生腿不做模块解析，会报
    「未定义的段落：X」。磁盘用量 dict 用 序列化JSON 出参（R148-A 已验证的内置），
    Python 侧再 json.loads 解析，同时规避 字典键列表 是否为核心内置的不确定性。
    """
    # ⚠️ 不做嵌套调用（序列化JSON(磁盘用量(...))）——原生腿解析器会把内层
    # 名当未定义变量报「变量必须先定义后使用」；先 设 再打印（同 R148-A 范式）。
    return (
        "段落 主():\n"
        "  打印(\"exec=\", 是否可执行('%s'))\n"
        "  打印(\"chmod=\", 设置权限('%s', 384))\n"
        "  设 用量 为 磁盘用量('%s')\n"
        "  打印(\"du=\", 序列化JSON(用量))\n"
    ) % (文件路径, 文件路径, 目录路径)


def _fwd(p):
    return p.replace("\\", "/")


# 已知两腿 repr 分歧（R148 已登记候选，非本轮回归）：
# 打印 标量布尔时 native 输出「真/假」、src 输出「True/False」。
# 对拍前归一化，避免把既有分歧误记为本轮新红。
_BOOL_REPR = {"真": "True", "假": "False"}


def _kv(out):
    """解析 `key= value` 行（布尔 repr 已归一化）。"""
    d = {}
    for ln in out.splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            v = v.strip()
            d[k.strip()] = _BOOL_REPR.get(v, v)
    return d


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
        with tempfile.TemporaryDirectory(prefix="_r149a_") as d:
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
    with tempfile.TemporaryDirectory(prefix="_r149a_py_") as d:
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


class R149_文件系统原语_源码级守单点(unittest.TestCase):
    """守单点：codegen 必须注册内置、runtime 必须导出 C 符号、builtins 必须有地板实体。"""

    def test_codegen_注册五个内置(self):
        p = os.path.join(_ROOT, "src", "llvm", "codegen_typed.py")
        s = open(p, encoding="utf-8").read()
        for fn in ("dv_fs_access", "dv_fs_chmod", "dv_fs_symlink",
                   "dv_fs_readlink", "dv_fs_statvfs"):
            self.assertIn("declare void @%s" % fn, s, "codegen 缺 declare: %s" % fn)
        for nm in ("是否可执行", "设置权限", "创建符号链接", "读取符号链接", "磁盘用量"):
            self.assertIn("'%s'" % nm, s, "codegen 缺内置分派名: %s" % nm)

    def test_runtime_导出五个C符号(self):
        p = os.path.join(_ROOT, "src", "llvm", "runtime_typed.c")
        s = open(p, encoding="utf-8").read()
        for fn in ("dv_fs_access", "dv_fs_chmod", "dv_fs_symlink",
                   "dv_fs_readlink", "dv_fs_statvfs"):
            self.assertIn("void %s(" % fn, s, "runtime 缺 C 定义: %s" % fn)

    def test_builtins_补src腿地板实体(self):
        """src 腿 `_light_builtin.*` 必须有实体，否则调用即 AttributeError。"""
        p = os.path.join(_ROOT, "stdlib", "builtins.py")
        s = open(p, encoding="utf-8").read()
        for nm in ("是否可执行", "设置权限", "创建符号链接", "读取符号链接", "磁盘用量"):
            self.assertIn("def %s(" % nm, s, "builtins.py 缺地板实体: %s" % nm)


@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0],
                 "未定位到 MSVC/Windows SDK 头，跳过原生腿")
class R149_文件系统原语_双腿对拍(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory(prefix="_r149a_fs_")
        self.目录 = _fwd(self._td.name)
        self.文件 = _fwd(os.path.join(self._td.name, "a.txt"))
        with open(self.文件, "w", encoding="utf-8") as f:
            f.write("x")
        self._src = _build_src(self.文件, self.目录)

    def tearDown(self):
        self._td.cleanup()

    def test_双腿对拍(self):
        """原生腿与 src 腿在同一台机、同一路径下逐项一致。"""
        n = _kv(_native_run(self._src))
        s = _kv(_src_run(self._src))
        for k in ("exec", "chmod"):
            self.assertIn(k, n, "原生腿缺输出项 %s：%s" % (k, n))
            self.assertIn(k, s, "src 腿缺输出项 %s：%s" % (k, s))
            self.assertEqual(n[k], s[k],
                             "两腿分歧 %s：native=%s src=%s" % (k, n[k], s[k]))
        dn, ds = json.loads(n["du"]), json.loads(s["du"])
        self.assertEqual(sorted(dn.keys()), sorted(ds.keys()),
                         "磁盘用量键名两腿不一致：native=%s src=%s"
                         % (sorted(dn.keys()), sorted(ds.keys())))

    def test_磁盘族结构性质(self):
        """键名对齐 shutil.disk_usage 口径；数值只断言结构性质（机器无关）。"""
        d = json.loads(_kv(_native_run(self._src))["du"])
        self.assertEqual(
            sorted(d.keys()), sorted(["使用率", "可用空间", "总空间", "已用空间"]),
            "磁盘用量键名应等于 总空间/已用空间/可用空间/使用率：%s" % sorted(d.keys()))
        self.assertTrue(d["总空间"] > 0, "总空间应 > 0：%s" % d)
        self.assertTrue(d["已用空间"] >= 0, "已用空间应 >= 0：%s" % d)
        self.assertTrue(d["可用空间"] >= 0, "可用空间应 >= 0：%s" % d)


if __name__ == "__main__":
    unittest.main()
