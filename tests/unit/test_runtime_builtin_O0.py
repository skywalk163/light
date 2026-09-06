# -*- coding: utf-8 -*-
"""
T7D 定向测试：runtime builtin 签名/实现根因修复反跑判据。

覆盖缺陷（docs/known_issues.md）：
  1. T6A-04 builtin 连接字符串(列表, 分隔) 恒返空串 —— runtime dv_str_join 是
     legacy "list:..." 序列化解析器、codegen 又取 str 字段（列表为 NULL）。
     T7D 新增 dv_list_join(原生 LightValue 列表, 分隔) 并重接 codegen。
  2. T6A-05 builtin 字典获取 第 3 参（默认值）被丢弃 —— codegen 只传 2 参。
     T7D 新增 dv_dict_get_def（键缺失返回默认值）。
  3. T6A-06 builtin 替换 特定形态返回「旧串」 —— 本批实测当前已绿
     （此前批次 codegen 顺带修复），此处用连续替换链钉死，防回归。
  4. T5B-3 SHA512 / HMAC_SHA256 返回空串占位 —— T7D 新增 runtime dv_sha512
     （C 层 64 位字）与 dv_pbkdf2_hmac_sha256_1（二进制安全 HMAC，对齐 .py 的
     pbkdf2_hmac('sha256', text, key, 1)）；stdlib 编码/哈希 改调 runtime。
  5. 顺带修复：sha256 长度编码 latent bug（多块输入摘要错误，HMAC 触发暴露）——
     final 原把 count[1](块数)/count[0](残余位) 当两半 32 位大端拼，仅 <64B 对；
     改为总位数 = count[1]*512+count[0]。此用例以 ≥64B 输入锁定。

反跑判据：O0 真编译真跑，输出与 Python oracle（hashlib / str.join / dict.get /
str.replace）逐项对拍。

隔离约定：
  编码 与 哈希 均导出 Base64编码/Base64解码（_safe_func_name 仅按段名映射，
  跨模块同名段会 IR 重定义），两模块相关用例**分别编译**。

环境：仅在能定位 clang 且（Windows 下）能定位 MSVC/Windows SDK 时执行，否则 skip。
"""

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for p in (_ROOT, os.path.join(_ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)


def _find_msvc_env():
    if os.name != "nt":
        return None, None
    vs_base = r"C:\Program Files (x86)\Microsoft Visual Studio"
    kits_base = r"C:\Program Files (x86)\Windows Kits\10"
    msvc_inc = msvc_lib = None
    if os.path.isdir(vs_base):
        for year in sorted(os.listdir(vs_base), reverse=True):
            for edition in ("BuildTools", "Community", "Professional", "Enterprise"):
                inc_root = os.path.join(vs_base, year, edition, "VC", "Tools", "MSVC")
                if not os.path.isdir(inc_root):
                    continue
                for ver in sorted(os.listdir(inc_root), reverse=True):
                    cand_inc = os.path.join(inc_root, ver, "include")
                    cand_lib = os.path.join(inc_root, ver, "lib", "x64")
                    if os.path.isdir(cand_inc) and os.path.isdir(cand_lib):
                        msvc_inc, msvc_lib = cand_inc, cand_lib
                        break
                if msvc_inc:
                    break
            if msvc_inc:
                break
    sdk_inc = sdk_lib = None
    if os.path.isdir(kits_base):
        inc_root = os.path.join(kits_base, "Include")
        if os.path.isdir(inc_root):
            for ver in sorted(os.listdir(inc_root), reverse=True):
                parts = [os.path.join(inc_root, ver, x) for x in ("ucrt", "shared", "um")]
                if all(os.path.isdir(p) for p in parts):
                    sdk_inc = parts
                    sdk_lib = [os.path.join(kits_base, "Lib", ver, x, "x64")
                               for x in ("ucrt", "um")]
                    break
    include = ";".join([msvc_inc] + sdk_inc) if (msvc_inc and sdk_inc) else None
    lib = ";".join([msvc_lib] + sdk_lib) if (msvc_lib and sdk_lib) else None
    return include, lib


def _prepare_env():
    env = dict(os.environ)
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    return env


def _native_run(src_text, timeout=180):
    """内联 .light 源码走原生腿 O0 编译并运行，返回 {KEY: 值字符串}。"""
    from llvm.compiler import compile_light_typed

    env = _prepare_env()
    old_env = {k: os.environ.get(k) for k in ("INCLUDE", "LIB")}
    os.environ.update({k: v for k, v in env.items() if k in ("INCLUDE", "LIB")})
    try:
        with tempfile.TemporaryDirectory(prefix="_t7d_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8") as f:
                f.write(src_text)
            exe = os.path.join(d, "main")
            out_exe = compile_light_typed(src, exe, optimize_level=0)
            if not out_exe or not os.path.exists(out_exe):
                raise AssertionError(f"原生腿编译未产出可执行文件: {out_exe!r}")
            proc = subprocess.run([out_exe], capture_output=True, timeout=timeout, env=env)
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    if proc.returncode != 0:
        raise AssertionError(
            f"运行失败 rc={proc.returncode}\n"
            f"STDOUT:\n{proc.stdout.decode('utf-8', 'replace')}\n"
            f"STDERR:\n{proc.stderr.decode('utf-8', 'replace')[:2000]}"
        )
    out = {}
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v
    return out


def _clang_available():
    try:
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class T7DruntimeBuiltin反跑(unittest.TestCase):
    """T6A-04/05/06 + T5B-3(SHA512/HMAC) 最小复现 + 对拍。"""

    # ── T6A-04：连接字符串 ──
    def test_连接字符串_对拍Python(self):
        src = """段落 主:
  设 们 为 列表("a", "b")
  输出("J2=" 加上 连接字符串(们, "-"))
  输出("J1=" 加上 连接字符串(列表("x", "y", "z")))
  输出("J0=" 加上 连接字符串(列表(), ","))
  输出("JCH=" 加上 连接字符串(列表("表格", "行"), "|"))
"""
        got = _native_run(src)
        self.assertEqual(got["J2"], "-".join(["a", "b"]))
        self.assertEqual(got["J1"], "".join(["x", "y", "z"]))
        self.assertEqual(got["J0"], "".join([]))
        self.assertEqual(got["JCH"], "|".join(["表格", "行"]))

    # ── T6A-05：字典获取 3 参（默认值）──
    def test_字典获取3参_对拍Python(self):
        src = """段落 主:
  设 d 为 {}
  设 d["有"] 为 "V"
  设 d["数"] 为 42
  输出("HIT=" 加上 转文本(字典获取(d, "有", "默认")))
  输出("MISS=" 加上 转文本(字典获取(d, "缺", "默认")))
  输出("MISSE=" 加上 转文本(字典获取(d, "缺2", "")))
  输出("NUM=" 加上 转文本(字典获取(d, "数", 0)))
  输出("MISSN=" 加上 转文本(字典获取(d, "缺3", 空)))
"""
        got = _native_run(src)
        self.assertEqual(got["HIT"], "V")
        self.assertEqual(got["MISS"], "默认")
        self.assertEqual(got["MISSE"], "")
        self.assertEqual(got["NUM"], "42")
        # 默认值为 空 → 转文本后为 空
        self.assertEqual(got["MISSN"], "空")

    # ── T6A-06：替换（连续替换链钉死；当前已绿，防回归）──
    def test_替换链_对拍Python(self):
        src = """段落 主:
  设 s 为 "${a}${b}"
  设 s 为 替换(s, "${a}", "1")
  设 s 为 替换(s, "${b}", "2")
  输出("R2=" 加上 s)
  设 s2 为 "aaa"
  设 s2 为 替换(s2, "a", "bb")
  输出("R3=" 加上 s2)
  输出("R1=" 加上 替换("hello world", "world", "光明"))
  输出("R0=" 加上 替换("无此模式", "xyz", "X"))
"""
        got = _native_run(src)
        self.assertEqual(got["R2"], "${a}${b}".replace("${a}", "1").replace("${b}", "2"))
        self.assertEqual(got["R3"], "aaa".replace("a", "bb"))
        self.assertEqual(got["R1"], "hello world".replace("world", "光明"))
        self.assertEqual(got["R0"], "无此模式")

    # ── T5B-3：SHA512（编码 + 哈希 分别编译）──
    def test_SHA512_编码模块_对拍Python(self):
        long_txt = "光明语言原生腿SHA512多块输入测试" * 8  # >128B，跨多个 128B 块
        src = """从 编码 导入 SHA512哈希
段落 主:
  设 s 为 "%s"
  设 长 为 "%s"
  输出("S=" 加上 SHA512哈希("abc"))
  输出("E=" 加上 SHA512哈希(""))
  输出("L=" 加上 SHA512哈希(长))
""" % ("abc", long_txt)
        got = _native_run(src)
        self.assertEqual(got["S"], hashlib.sha512(b"abc").hexdigest())
        self.assertEqual(got["E"], hashlib.sha512(b"").hexdigest())
        self.assertEqual(got["L"], hashlib.sha512(long_txt.encode()).hexdigest())

    def test_SHA512_HMAC_哈希模块_对拍Python(self):
        long_key = "密钥key" * 30  # >64B，触发 HMAC key 压缩路径
        long_txt = "msg文本" * 25
        src = """从 哈希 导入 SHA512 HMAC_SHA256
段落 主:
  输出("S=" 加上 SHA512("abc"))
  输出("H1=" 加上 HMAC_SHA256("密钥key", "msg文本"))
  输出("HL=" 加上 HMAC_SHA256("%s", "%s"))
  输出("HE=" 加上 HMAC_SHA256("", ""))
""" % (long_key, long_txt)
        got = _native_run(src)
        self.assertEqual(got["S"], hashlib.sha512(b"abc").hexdigest())
        self.assertEqual(got["H1"],
                         hashlib.pbkdf2_hmac("sha256", "msg文本".encode(), "密钥key".encode(), 1).hex())
        self.assertEqual(got["HL"],
                         hashlib.pbkdf2_hmac("sha256", long_txt.encode(), long_key.encode(), 1).hex())
        self.assertEqual(got["HE"],
                         hashlib.pbkdf2_hmac("sha256", b"", b"", 1).hex())

    # ── latent fix：sha256 长度编码（≥64B 多块输入，T7D 定界暴露）──
    def test_SHA256_多块输入_回归(self):
        long_txt = "abcdefghijklmnopqrstuvwxyz" * 4  # 104B，跨块
        src = """从 编码 导入 SHA256哈希
段落 主:
  设 长 为 "%s"
  输出("L=" 加上 SHA256哈希(长))
""" % long_txt
        got = _native_run(src)
        self.assertEqual(got["L"], hashlib.sha256(long_txt.encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
