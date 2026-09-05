# -*- coding: utf-8 -*-
"""
T5B 定向测试：编码与哈希模块（Base64 / 编码 / 哈希 / 字符串常量）真 .light 化反跑判据。

判据：
  1. 原生腿（llvm typed）以 **optimize_level=0** 编译 stdlib 的真 .light 实现并运行，
     输出与 Python（base64 / hashlib / string，同输入）逐项对拍一致。
  2. 若把对应 .light 改回空壳（仅有 导出 清单、无 段落），本测试立即失败 —— 即「反跑立红」。

隔离约定：
  每个模块单独一个编译单元（不可在同一 .light 里同时 从 Base64 导入 与 从 编码 导入）。
  原因见 docs/known_issues.md —— 原生后端 _safe_func_name 仅按段名映射 LLVM 符号，
  跨模块同名段落会触发 invalid redefinition of function。

环境：
  仅在能定位到 clang 且（Windows 下）能定位到 MSVC/Windows SDK 头与库时执行，否则 skip。
"""

import base64
import hashlib
import os
import string
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
    """在 Windows 上定位 MSVC + Windows SDK 的 INCLUDE / LIB；其它平台返回 (None, None)。"""
    if os.name != "nt":
        return None, None
    vs_base = r"C:\Program Files (x86)\Microsoft Visual Studio"
    kits_base = r"C:\Program Files (x86)\Windows Kits\10"

    msvc_inc = msvc_lib = None
    if os.path.isdir(vs_base):
        for year in sorted(os.listdir(vs_base), reverse=True):
            tools = os.path.join(vs_base, year)
            for edition in ("BuildTools", "Community", "Professional", "Enterprise"):
                inc_root = os.path.join(tools, edition, "VC", "Tools", "MSVC")
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
    """返回可直接传给 subprocess 的环境；Windows 下补齐 MSVC/SDK 头与库路径。"""
    env = dict(os.environ)
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    return env


def _native_run(src_text, timeout=180):
    """以内联 .light 源码走原生腿 O0 编译并运行，返回 {KEY: 值字符串}。

    源码约定：模块内 `段落 主` 中用 `输出("KEY=" 加上 ...)` 逐行打印。
    """
    from llvm.compiler import compile_light_typed

    env = _prepare_env()
    old_env = {k: os.environ.get(k) for k in ("INCLUDE", "LIB")}
    os.environ.update({k: v for k, v in env.items() if k in ("INCLUDE", "LIB")})
    try:
        with tempfile.TemporaryDirectory(prefix="_t5b_") as d:
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
        sys.path.insert(0, os.path.join(_ROOT, "src"))
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class T5B编码哈希反跑(unittest.TestCase):
    """每个模块一个独立编译单元，逐项与 Python oracle 对拍。"""

    # ── Base64 ──
    def test_Base64_编解码_对拍Python(self):
        src = """从 Base64 导入 Base64编码 Base64解码 Base64URL编码 Base64URL解码 Base16编码 Base16解码 Base32编码 Base32解码 Base64验证
段落 主:
  设 s 为 "Hello, 世界!"
  输出("B64=" 加上 Base64编码(s))
  输出("B64D=" 加上 Base64解码(Base64编码(s)))
  输出("U64=" 加上 Base64URL编码(s))
  输出("U64D=" 加上 Base64URL解码(Base64URL编码(s)))
  输出("B16=" 加上 Base16编码(s))
  输出("B16D=" 加上 Base16解码(Base16编码(s)))
  输出("B32=" 加上 Base32编码(s))
  输出("B32D=" 加上 Base32解码(Base32编码(s)))
  输出("VOK=" 加上 转字符串(Base64验证(Base64编码(s))))
  输出("VBAD=" 加上 转字符串(Base64验证("!!!no b64!!!")))
  输出("B32_1=" 加上 Base32编码("A"))
  输出("B32_2=" 加上 Base32编码("AB"))
  输出("B32_3=" 加上 Base32编码("ABC"))
  输出("B32_4=" 加上 Base32编码("ABCD"))
"""
        got = _native_run(src)
        s = "Hello, 世界!"
        self.assertEqual(got["B64"], base64.b64encode(s.encode()).decode())
        self.assertEqual(got["B64D"], s)
        self.assertEqual(got["U64"], base64.urlsafe_b64encode(s.encode()).decode())
        self.assertEqual(got["U64D"], s)
        self.assertEqual(got["B16"], base64.b16encode(s.encode()).decode())
        self.assertEqual(got["B16D"], s)
        self.assertEqual(got["B32"], base64.b32encode(s.encode()).decode())
        self.assertEqual(got["B32D"], s)
        self.assertEqual(got["VOK"], "真")
        self.assertEqual(got["VBAD"], "假")
        for raw in ("A", "AB", "ABC", "ABCD"):
            self.assertEqual(got[f"B32_{len(raw)}"], base64.b32encode(raw.encode()).decode(), raw)

    # ── 编码 ──
    def test_编码_哈希_对拍Python(self):
        src = """从 编码 导入 Base64编码 Base64解码 Hex编码 Hex解码 MD5哈希 SHA1哈希 SHA256哈希 字符串转字节 字节转字符串 字节长度
段落 主:
  设 s 为 "Hello, 世界!"
  输出("B64=" 加上 Base64编码(s))
  输出("B64D=" 加上 Base64解码(Base64编码(s)))
  输出("HEX=" 加上 Hex编码(s))
  输出("HEXD=" 加上 Hex解码(Hex编码(s)))
  输出("MD5=" 加上 MD5哈希("hello"))
  输出("S1=" 加上 SHA1哈希("hello"))
  输出("S256=" 加上 SHA256哈希("hello"))
  输出("B=" 加上 字符串转字节("Hi"))
  输出("BS=" 加上 字节转字符串(字符串转字节("Hi")))
  输出("BL=" 加上 转字符串(字节长度(字符串转字节("Hi"))))
"""
        got = _native_run(src)
        s = "Hello, 世界!"
        self.assertEqual(got["B64"], base64.b64encode(s.encode()).decode())
        self.assertEqual(got["B64D"], s)
        self.assertEqual(got["HEX"], s.encode().hex())
        self.assertEqual(got["HEXD"], s)
        self.assertEqual(got["MD5"], hashlib.md5(b"hello").hexdigest())
        self.assertEqual(got["S1"], hashlib.sha1(b"hello").hexdigest())
        self.assertEqual(got["S256"], hashlib.sha256(b"hello").hexdigest())
        self.assertEqual(got["B"], "Hi".encode().hex())
        self.assertEqual(got["BS"], "Hi")
        self.assertEqual(got["BL"], "2")

    # ── 哈希 ──
    def test_哈希_对拍Python(self):
        src = """从 哈希 导入 MD5 SHA1 SHA256 Base64编码 Base64解码 Base64URL编码 Base64URL解码
段落 主:
  输出("MD5=" 加上 MD5("hello"))
  输出("S1=" 加上 SHA1("hello"))
  输出("S256=" 加上 SHA256("hello"))
  设 s 为 "Hello, 世界!"
  输出("B64=" 加上 Base64编码(s))
  输出("B64D=" 加上 Base64解码(Base64编码(s)))
  输出("U64=" 加上 Base64URL编码(s))
  输出("U64D=" 加上 Base64URL解码(Base64URL编码(s)))
  设 t 为 "ab?>"
  输出("U64B=" 加上 Base64URL编码(t))
  输出("U64BD=" 加上 Base64URL解码(Base64URL编码(t)))
"""
        got = _native_run(src)
        s, t = "Hello, 世界!", "ab?>"
        self.assertEqual(got["MD5"], hashlib.md5(b"hello").hexdigest())
        self.assertEqual(got["S1"], hashlib.sha1(b"hello").hexdigest())
        self.assertEqual(got["S256"], hashlib.sha256(b"hello").hexdigest())
        self.assertEqual(got["B64"], base64.b64encode(s.encode()).decode())
        self.assertEqual(got["B64D"], s)
        self.assertEqual(got["U64"], base64.urlsafe_b64encode(s.encode()).decode().rstrip("="))
        self.assertEqual(got["U64D"], s)
        self.assertEqual(got["U64B"], base64.urlsafe_b64encode(t.encode()).decode().rstrip("="))
        self.assertEqual(got["U64BD"], t)

    # ── 字符串常量 ──
    def test_字符串常量_对拍Python(self):
        src = """从 字符串常量 导入 小写字母 大写字母 数字 十六进制数字 八进制数字 标点符号 可打印字符 空白字符 换行符
从 字符串常量 导入 是字母 是数字 是小写 是大写 是标点 是十六进制 是八进制
从 字符串常量 导入 全大写 全小写 首字母大写 交换大小写 标题大小写
从 字符串常量 导入 去除两端空白 去除左端空白 去除右端空白 居中填充 左对齐 右对齐 补零
从 字符串常量 导入 连接 分割 替换 包含 以开头 以结尾 查找 反向查找 计数
从 字符串常量 导入 字符列表全部是 字符列表有一个是
段落 主:
  输出("LOW=" 加上 小写字母)
  输出("UP=" 加上 大写字母)
  输出("DIG=" 加上 数字)
  输出("HEXD=" 加上 十六进制数字)
  输出("OCT=" 加上 八进制数字)
  输出("PUNC=" 加上 标点符号)
  输出("WSLEN=" 加上 转字符串(长(空白字符)))
  输出("PRINTLEN=" 加上 转字符串(长(可打印字符)))
  输出("NLLEN=" 加上 转字符串(长(换行符)))
  输出("ISL=" 加上 转字符串(是小写("a")))
  输出("ISU=" 加上 转字符串(是大写("A")))
  输出("ISD=" 加上 转字符串(是数字("7")))
  输出("ISA=" 加上 转字符串(是字母("Z")))
  输出("ISP=" 加上 转字符串(是标点("#")))
  输出("ISH=" 加上 转字符串(是十六进制("f")))
  输出("ISO=" 加上 转字符串(是八进制("7")))
  输出("UP2=" 加上 全大写("abC"))
  输出("LOW2=" 加上 全小写("abC"))
  输出("CAP=" 加上 首字母大写("hELLO"))
  输出("SWAP=" 加上 交换大小写("aBc1"))
  输出("TITLE=" 加上 标题大小写("hello world"))
  输出("TRIM=[" 加上 去除两端空白("  hi  ") 加上 "]")
  输出("LTRIM=[" 加上 去除左端空白("  hi  ") 加上 "]")
  输出("RTRIM=[" 加上 去除右端空白("  hi  ") 加上 "]")
  输出("CENTER=[" 加上 居中填充("ab", 6, "-") 加上 "]")
  输出("LJ=[" 加上 左对齐("ab", 5, "-") 加上 "]")
  输出("RJ=[" 加上 右对齐("ab", 5, "-") 加上 "]")
  输出("ZF=[" 加上 补零("42", 5) 加上 "]")
  设 parts 为 分割("a,b,c", ",")
  输出("JOIN=" 加上 连接("-", parts))
  输出("REPL=" 加上 替换("aaa", "a", "b"))
  输出("CT=" 加上 转字符串(包含("hello", "ell")))
  输出("SW=" 加上 转字符串(以开头("hello", "he")))
  输出("EW=" 加上 转字符串(以结尾("hello", "lo")))
  输出("FIND=" 加上 转字符串(查找("hello", "ll")))
  输出("RFIND=" 加上 转字符串(反向查找("banana", "an")))
  输出("CNT=" 加上 转字符串(计数("banana", "an")))
  输出("ALLD=" 加上 转字符串(字符列表全部是("123", "数字")))
  输出("ALLDX=" 加上 转字符串(字符列表全部是("12a", "数字")))
  输出("ANYD=" 加上 转字符串(字符列表有一个是("ab1", "数字")))
"""
        got = _native_run(src)
        self.assertEqual(got["LOW"], string.ascii_lowercase)
        self.assertEqual(got["UP"], string.ascii_uppercase)
        self.assertEqual(got["DIG"], string.digits)
        self.assertEqual(got["HEXD"], string.hexdigits)
        self.assertEqual(got["OCT"], string.octdigits)
        self.assertEqual(got["PUNC"], string.punctuation)
        self.assertEqual(got["WSLEN"], str(len(string.whitespace)))
        self.assertEqual(got["PRINTLEN"], str(len(string.printable)))
        self.assertEqual(got["NLLEN"], "1")
        self.assertEqual(got["ISL"], "真")
        self.assertEqual(got["ISU"], "真")
        self.assertEqual(got["ISD"], "真")
        self.assertEqual(got["ISA"], "真")
        self.assertEqual(got["ISP"], "真")
        self.assertEqual(got["ISH"], "真")
        self.assertEqual(got["ISO"], "真")
        self.assertEqual(got["UP2"], "abC".upper())
        self.assertEqual(got["LOW2"], "abC".lower())
        self.assertEqual(got["CAP"], "hELLO".capitalize())
        self.assertEqual(got["SWAP"], "aBc1".swapcase())
        self.assertEqual(got["TITLE"], "hello world".title())
        self.assertEqual(got["TRIM"], "[" + "  hi  ".strip() + "]")
        self.assertEqual(got["LTRIM"], "[" + "  hi  ".lstrip() + "]")
        self.assertEqual(got["RTRIM"], "[" + "  hi  ".rstrip() + "]")
        self.assertEqual(got["CENTER"], "[" + "ab".center(6, "-") + "]")
        self.assertEqual(got["LJ"], "[" + "ab".ljust(5, "-") + "]")
        self.assertEqual(got["RJ"], "[" + "ab".rjust(5, "-") + "]")
        self.assertEqual(got["ZF"], "[" + "42".zfill(5) + "]")
        self.assertEqual(got["JOIN"], "-".join(["a", "b", "c"]))
        self.assertEqual(got["REPL"], "aaa".replace("a", "b"))
        self.assertEqual(got["CT"], "真")
        self.assertEqual(got["SW"], "真")
        self.assertEqual(got["EW"], "真")
        self.assertEqual(got["FIND"], str("hello".find("ll")))
        self.assertEqual(got["RFIND"], str("banana".rfind("an")))
        self.assertEqual(got["CNT"], str("banana".count("an")))
        self.assertEqual(got["ALLD"], "真")
        self.assertEqual(got["ALLDX"], "假")
        self.assertEqual(got["ANYD"], "真")


if __name__ == "__main__":
    unittest.main(verbosity=2)
