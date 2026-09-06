# -*- coding: utf-8 -*-
"""
R11B 反跑用例：中文工具族 7 模块 纯光明 .light 真实现（原生腿 O0）与 Python 参考对拍。

覆盖模块（均 O0 真编译真跑，与 stdlib/*.py 逐函数对拍）：
  1. 中文文本处理：统计中文字符/提取中文/去除标点/判断全中文/判断含中文/中文分句/中文分段/中文词频
  2. 中文数字转换：中文转阿拉伯数字/阿拉伯数字转中文/中文转浮点数/数字转大写金额
  3. 中文编码：检测编码/编码转换/判断GBK/判断UTF8/GBK转UTF8/UTF8转GBK/Unicode转义/Unicode反转义
     （光明原生腿无 bytes/codecs，输入输出统一用 hex 串口径；GBK/Big5 码表转换缺，见能力边界）
  4. 手机号校验：校验手机号/获取运营商/获取归属地（号段表/归属地表 .light 内嵌）
  5. 身份证校验：校验身份证/提取出生日期/提取性别/提取地区/计算校验码（地区码表 .light 内嵌）
  6. 中文分词：分词/添加自定义词/加载词典（正向最大匹配 + 653 词内嵌词典）
  7. 拼音转换：转拼音/拼音首字母（2808 常用字内嵌拼音表；源 .py 残缺无函数，以黄金对照对拍）

反跑判据：
  - 真实现 → 绿；改回 decl 0 空壳（仅导出语句）→ 原生腿编译导入即 NativeImportError 立红
    （空壳拦截已在各子代理交付时验证，本文件不再重复造壳）。

对拍口径说明：
  - 布尔输出用 if/else 打 1/0（光明 O0 下 整数(真)=0）。
  - 列表/字典输出用 长() + 逐元素/KV 展开（O0 下 输出(列表) 显示 []）。
  - 浮点经 转字符串（%g，6 位有效数字）打印，数值用 abs diff ≤1e-4。
  - 光明字符串字面量不处理 \\n/\\u 转义：需要真换行的输入用 字符自码位(10) 拼接构造；
    Unicode反转义 的输入 \\uXXXX 恰为字面反斜杠序列，直接写即可。

仅跑本文件；禁止全量。
"""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (_ROOT, os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_STDLIB = os.path.join(_ROOT, "stdlib")


# ── clang / MSVC 环境探测（参考 T6B 既有测试）────────────────────────────

def _find_msvc_env():
    """Windows 上定位 MSVC + Windows SDK 的 INCLUDE / LIB；其它平台返回 (None, None)。"""
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
    env = dict(os.environ)
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    return env


def _clang_available():
    try:
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


_MSVC_OK = (os.name != "nt") or bool(_find_msvc_env()[0])

pytestmark = [
    pytest.mark.skipif(not _clang_available(), reason="未找到 clang，跳过原生腿测试"),
    pytest.mark.skipif(os.name == "nt" and not _MSVC_OK, reason="未定位到 MSVC/Windows SDK 头，跳过"),
]


# ── 原生腿编译+运行（独立子进程，防 O0 内存累积；参考 T6B helper）──────────

_HELPER = r"""
import os, sys, subprocess
def main():
    root, src, exe = sys.argv[1], sys.argv[2], sys.argv[3]
    for p in (root, os.path.join(root, "src")):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        from llvm.compiler import compile_light_typed
        out = compile_light_typed(src, exe, optimize_level=0)
        if not out or not os.path.exists(out):
            sys.stderr.write("no exe: %r\n" % (out,))
            return 2
        r = subprocess.run([out], capture_output=True, timeout=240)
        sys.stdout.write(r.stdout.decode("utf-8", "replace"))
        sys.stderr.write(r.stderr.decode("utf-8", "replace"))
        return r.returncode
    except Exception:
        import traceback
        traceback.print_exc()
        return 1
sys.exit(main())
"""


def _native_run(src_text, timeout=300):
    """以内联 .light 源码走原生腿 O0 编译并运行，返回 {KEY: 值字符串}。

    编译 + 运行 fork 到全新 python 子进程（clang 拿到与单独运行相同的空闲 RAM，
    进程退出即释放），临时目录建在 worktree 根（模块解析稳定）。
    """
    env = _prepare_env()
    with tempfile.TemporaryDirectory(prefix="_taskR11B_test_", dir=_ROOT) as d:
        src = os.path.join(d, "main.light")
        with open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(src_text)
        exe = os.path.join(d, "main")
        try:
            proc = subprocess.run(
                [sys.executable, "-c", _HELPER, _ROOT, src, exe],
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


def _load_py(name, tag):
    """从文件动态加载 stdlib/<name>.py（每次独立模块名，保证全新实例）。"""
    spec = importlib.util.spec_from_file_location(tag, os.path.join(_STDLIB, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _collect_seq(out, prefix):
    """收集 out 里 prefix<i>=value 序列，返回按 i 排好序的值列表。"""
    items = {}
    for k, v in out.items():
        if k.startswith(prefix):
            items[int(k[len(prefix):])] = v
    return [items[i] for i in sorted(items)]


# ═══════════════════════════════════════════════════════════════════════
# 1. 中文文本处理
# ═══════════════════════════════════════════════════════════════════════

def test_中文文本处理_O0对拍():
    src = """从 中文文本处理 导入 统计中文字符 提取中文 去除标点 判断全中文 判断含中文 中文分句 中文分段 中文词频
段落 主:
  # 统计中文字符
  输出("N0=" 加上 转字符串(统计中文字符("Hello 你好世界！")))
  输出("N1=" 加上 转字符串(统计中文字符("《光明》编程语言。")))
  输出("N2=" 加上 转字符串(统计中文字符("abc")))
  输出("N3=" 加上 转字符串(统计中文字符("")))
  # 提取中文
  输出("E0=" 加上 提取中文("Hello 你好世界！"))
  输出("E1=" 加上 提取中文("《光明》编程语言。"))
  输出("E2=" 加上 提取中文("abc123"))
  输出("E3=" 加上 提取中文(""))
  # 去除标点
  输出("P0=" 加上 去除标点("你好，世界！"))
  输出("P1=" 加上 去除标点("《光明》编程语言。"))
  输出("P2=" 加上 去除标点("Hello, world!"))
  输出("P3=" 加上 去除标点(""))
  # 判断全中文
  设 a0 为 判断全中文("你好世界")
  如果 a0 == 真:
    输出("A0=1")
  否则:
    输出("A0=0")
  设 a1 为 判断全中文("你好，世界")
  如果 a1 == 真:
    输出("A1=1")
  否则:
    输出("A1=0")
  设 a2 为 判断全中文("")
  如果 a2 == 真:
    输出("A2=1")
  否则:
    输出("A2=0")
  # 判断含中文
  设 b0 为 判断含中文("Hello 你好")
  如果 b0 == 真:
    输出("B0=1")
  否则:
    输出("B0=0")
  设 b1 为 判断含中文("abc")
  如果 b1 == 真:
    输出("B1=1")
  否则:
    输出("B1=0")
  设 b2 为 判断含中文("")
  如果 b2 == 真:
    输出("B2=1")
  否则:
    输出("B2=0")
  # 中文分句（含真实换行用 字符自码位 构造）
  设 NL 为 字符自码位(10)
  设 s0 为 中文分句("你好。世界！今天" 加上 NL 加上 "怎么样？")
  输出("SC0=" 加上 转字符串(长(s0)))
  设 i0 为 0
  遍历 x 之 s0:
    输出("S0_" 加上 转字符串(i0) 加上 "=" 加上 x)
    设 i0 为 i0 加上 1
  设 s1 为 中文分句("只有一句")
  输出("SC1=" 加上 转字符串(长(s1)))
  设 i1 为 0
  遍历 y 之 s1:
    输出("S1_" 加上 转字符串(i1) 加上 "=" 加上 y)
    设 i1 为 i1 加上 1
  # 中文分段
  设 p0 为 中文分段("第一段。" 加上 NL 加上 NL 加上 "第二段来了")
  输出("PC0=" 加上 转字符串(长(p0)))
  设 j0 为 0
  遍历 z 之 p0:
    输出("P0_" 加上 转字符串(j0) 加上 "=" 加上 z)
    设 j0 为 j0 加上 1
  设 p1 为 中文分段("只有一段")
  输出("PC1=" 加上 转字符串(长(p1)))
  设 j1 为 0
  遍历 w 之 p1:
    输出("P1_" 加上 转字符串(j1) 加上 "=" 加上 w)
    设 j1 为 j1 加上 1
  # 中文词频
  设 f 为 中文词频("你好你好世界")
  设 ks 为 字典键列表(f)
  输出("FC=" 加上 转字符串(长(ks)))
  设 fi 为 0
  遍历 k 之 ks:
    输出("F" 加上 转字符串(fi) 加上 "=" 加上 k 加上 ":" 加上 转字符串(字典获取(f, k, -1)))
    设 fi 为 fi 加上 1
"""
    out = _native_run(src)
    ref = _load_py("中文文本处理", "_py_ref_wbcl")

    # 统计中文字符
    for i, s in enumerate(["Hello 你好世界！", "《光明》编程语言。", "abc", ""]):
        assert int(out[f"N{i}"]) == ref.统计中文字符(s), f"统计中文字符[{s}]"
    # 提取中文
    for i, s in enumerate(["Hello 你好世界！", "《光明》编程语言。", "abc123", ""]):
        assert out[f"E{i}"] == ref.提取中文(s), f"提取中文[{s}]"
    # 去除标点
    for i, s in enumerate(["你好，世界！", "《光明》编程语言。", "Hello, world!", ""]):
        assert out[f"P{i}"] == ref.去除标点(s), f"去除标点[{s}]"
    # 判断全中文 / 判断含中文
    for i, s in enumerate(["你好世界", "你好，世界", ""]):
        assert out[f"A{i}"] == ("1" if ref.判断全中文(s) else "0"), f"判断全中文[{s}]"
    for i, s in enumerate(["Hello 你好", "abc", ""]):
        assert out[f"B{i}"] == ("1" if ref.判断含中文(s) else "0"), f"判断含中文[{s}]"
    # 中文分句
    s0 = ref.中文分句("你好。世界！今天\n怎么样？")
    assert int(out["SC0"]) == len(s0)
    assert _collect_seq(out, "S0_") == list(s0), "中文分句[含换行]"
    s1 = ref.中文分句("只有一句")
    assert int(out["SC1"]) == len(s1)
    assert _collect_seq(out, "S1_") == list(s1), "中文分句[单句]"
    # 中文分段
    p0 = ref.中文分段("第一段。\n\n第二段来了")
    assert int(out["PC0"]) == len(p0)
    assert _collect_seq(out, "P0_") == list(p0), "中文分段[双段]"
    p1 = ref.中文分段("只有一段")
    assert int(out["PC1"]) == len(p1)
    assert _collect_seq(out, "P1_") == list(p1), "中文分段[单段]"
    # 中文词频（F<i>=字:数 展开组装 dict，键序无关比较）
    # 注意：_native_run 按首个 '=' 拆 key/value；key 带索引避免同键覆盖
    got = {}
    for k, v in out.items():
        if k.startswith("F") and len(k) > 1 and k[1:].isdigit():
            ck, cv = v.split(":", 1)
            got[ck] = int(cv)
    assert got == ref.中文词频("你好你好世界"), "中文词频"


# ═══════════════════════════════════════════════════════════════════════
# 2. 中文数字转换
# ═══════════════════════════════════════════════════════════════════════

def test_中文数字转换_O0对拍():
    src = """从 中文数字转换 导入 中文转阿拉伯数字 阿拉伯数字转中文 中文转浮点数 数字转大写金额
段落 主:
  输出("A0=" 加上 转字符串(中文转阿拉伯数字("一百二十三")))
  输出("A1=" 加上 转字符串(中文转阿拉伯数字("十二")))
  输出("A2=" 加上 转字符串(中文转阿拉伯数字("一万零五")))
  输出("A3=" 加上 转字符串(中文转阿拉伯数字("两")))
  输出("B0=" 加上 阿拉伯数字转中文(0))
  输出("B1=" 加上 阿拉伯数字转中文(11))
  输出("B2=" 加上 阿拉伯数字转中文(1010))
  输出("B3=" 加上 阿拉伯数字转中文(10005))
  输出("C0=" 加上 转字符串(中文转浮点数("三点一四")))
  输出("C1=" 加上 转字符串(中文转浮点数("十点五")))
  输出("C2=" 加上 转字符串(中文转浮点数("零点零零一")))
  输出("D0=" 加上 数字转大写金额(123.45))
  输出("D1=" 加上 数字转大写金额(0))
  输出("D2=" 加上 数字转大写金额(0.05))
  输出("D3=" 加上 数字转大写金额(1.00))
"""
    out = _native_run(src)
    ref = _load_py("中文数字转换", "_py_ref_szzh")

    for i, s in enumerate(["一百二十三", "十二", "一万零五", "两"]):
        assert int(out[f"A{i}"]) == ref.中文转阿拉伯数字(s), f"中文转阿拉伯数字[{s}]"
    for i, n in enumerate([0, 11, 1010, 10005]):
        assert out[f"B{i}"] == ref.阿拉伯数字转中文(n), f"阿拉伯数字转中文[{n}]"
    for i, s in enumerate(["三点一四", "十点五", "零点零零一"]):
        assert abs(float(out[f"C{i}"]) - ref.中文转浮点数(s)) <= 1e-4, f"中文转浮点数[{s}]"
    for i, n in enumerate([123.45, 0, 0.05, 1.00]):
        assert out[f"D{i}"] == ref.数字转大写金额(n), f"数字转大写金额[{n}]"


# ═══════════════════════════════════════════════════════════════════════
# 3. 中文编码（hex 串口径；能力边界：无 GBK/Big5 码表）
# ═══════════════════════════════════════════════════════════════════════

def test_中文编码_O0对拍():
    src = """从 中文编码 导入 判断UTF8 判断GBK 检测编码 Unicode转义 Unicode反转义 编码转换 UTF8转GBK GBK转UTF8
段落 主:
  设 u0 为 判断UTF8("e4bda0e5a5bd")
  如果 u0 == 真:
    输出("U0=1")
  否则:
    输出("U0=0")
  设 u1 为 判断UTF8("68656c6c6f")
  如果 u1 == 真:
    输出("U1=1")
  否则:
    输出("U1=0")
  设 u2 为 判断UTF8("baa3")
  如果 u2 == 真:
    输出("U2=1")
  否则:
    输出("U2=0")
  设 u3 为 判断UTF8("c0a0")
  如果 u3 == 真:
    输出("U3=1")
  否则:
    输出("U3=0")
  设 g0 为 判断GBK("baa3")
  如果 g0 == 真:
    输出("G0=1")
  否则:
    输出("G0=0")
  设 g1 为 判断GBK("e4bda0e5a5bd")
  如果 g1 == 真:
    输出("G1=1")
  否则:
    输出("G1=0")
  设 g2 为 判断GBK("68656c6c6f")
  如果 g2 == 真:
    输出("G2=1")
  否则:
    输出("G2=0")
  输出("D0=" 加上 检测编码("e4bda0e5a5bd"))
  输出("D1=" 加上 检测编码("baa3"))
  输出("D2=" 加上 检测编码("68656c6c6f"))
  输出("D3=" 加上 检测编码(""))
  输出("X0=" 加上 Unicode转义("你好"))
  输出("X1=" 加上 Unicode转义("hello"))
  输出("X2=" 加上 Unicode转义("😀"))
  设 BS 为 字符自码位(92)
  输出("Y0=" 加上 Unicode反转义(BS 加上 "u4f60" 加上 BS 加上 "u597d"))
  输出("Y1=" 加上 Unicode反转义(BS 加上 "u12gz"))
  输出("Y2=" 加上 Unicode反转义(BS 加上 "u123"))
  输出("Z0=" 加上 编码转换("", "gbk", "utf-8"))
  输出("Z1=" 加上 编码转换("68656c6c6f", "utf-8", "ascii"))
  输出("T0=" 加上 UTF8转GBK("hello"))
  输出("T1=" 加上 GBK转UTF8("68656c6c6f"))
"""
    out = _native_run(src)
    ref = _load_py("中文编码", "_py_ref_zmbm")

    def b(hexs):
        return bytes.fromhex(hexs) if hexs else b""

    for i, h in enumerate(["e4bda0e5a5bd", "68656c6c6f", "baa3", "c0a0"]):
        assert out[f"U{i}"] == ("1" if ref.判断UTF8(b(h)) else "0"), f"判断UTF8[{h}]"
    for i, h in enumerate(["baa3", "e4bda0e5a5bd", "68656c6c6f"]):
        assert out[f"G{i}"] == ("1" if ref.判断GBK(b(h)) else "0"), f"判断GBK[{h}]"
    for i, h in enumerate(["e4bda0e5a5bd", "baa3", "68656c6c6f", ""]):
        assert out[f"D{i}"] == ref.检测编码(b(h)), f"检测编码[{h}]"
    assert out["X0"] == ref.Unicode转义("你好"), "Unicode转义[中文]"
    assert out["X1"] == ref.Unicode转义("hello"), "Unicode转义[ASCII]"
    assert out["X2"] == ref.Unicode转义("😀"), "Unicode转义[扩展]"
    assert out["Y0"] == ref.Unicode反转义(r"\u4f60\u597d"), "Unicode反转义[合法]"
    assert out["Y1"] == ref.Unicode反转义(r"\u12gz"), "Unicode反转义[非法]"
    assert out["Y2"] == ref.Unicode反转义(r"\u123"), "Unicode反转义[不足4位]"
    # 编码转换 / UTF8转GBK / GBK转UTF8：仅测能力边界内的纯 ASCII / 空 / 同码通道
    assert out["Z0"] == ref.编码转换(b"", "gbk", "utf-8").hex(), "编码转换[空]"
    assert out["Z1"] == ref.编码转换(b"hello", "utf-8", "ascii").hex(), "编码转换[ASCII]"
    assert out["T0"] == ref.UTF8转GBK("hello").hex(), "UTF8转GBK[ASCII]"
    assert out["T1"] == ref.GBK转UTF8(b"hello"), "GBK转UTF8[ASCII]"


# ═══════════════════════════════════════════════════════════════════════
# 4. 手机号校验
# ═══════════════════════════════════════════════════════════════════════

def test_手机号校验_O0对拍():
    src = """从 手机号校验 导入 校验手机号 获取运营商 获取归属地
段落 主:
  设 p 为 ["13812345678", "19912345678", "17012345678", "110", "1381234567", "23812345678", "12345678901", "1234567890a"]
  设 k 为 0
  遍历 号 之 p:
    设 r 为 校验手机号(号)
    设 v 为 字典获取(r, "valid", 假)
    如果 v == 真:
      输出("V" 加上 转字符串(k) 加上 "=1")
    否则:
      输出("V" 加上 转字符串(k) 加上 "=0")
    输出("PH" 加上 转字符串(k) 加上 "=" 加上 字典获取(r, "phone", ""))
    输出("CA" 加上 转字符串(k) 加上 "=" 加上 字典获取(r, "carrier", ""))
    设 rg 为 字典获取(r, "region", "")
    如果 rg == 空:
      输出("RG" 加上 转字符串(k) 加上 "=NONE")
    否则:
      输出("RG" 加上 转字符串(k) 加上 "=" 加上 rg)
    设 es 为 字典获取(r, "errors", [])
    输出("EC" 加上 转字符串(k) 加上 "=" 加上 转字符串(长(es)))
    设 ei 为 0
    遍历 m 之 es:
      输出("E" 加上 转字符串(k) 加上 "_" 加上 转字符串(ei) 加上 "=" 加上 m)
      设 ei 为 ei 加上 1
    设 k 为 k 加上 1
  输出("OP0=" 加上 获取运营商("13812345678"))
  输出("OP1=" 加上 获取运营商("17012345678"))
  输出("OP2=" 加上 获取运营商("14012345678"))
  输出("OR0=" 加上 获取归属地("13800138000"))
  输出("OR1=" 加上 获取归属地("13431234567"))
  输出("OR2=" 加上 获取归属地("19912345678"))
"""
    out = _native_run(src)
    ref = _load_py("手机号校验", "_py_ref_sjhx")

    phones = ["13812345678", "19912345678", "17012345678", "110",
              "1381234567", "23812345678", "12345678901", "1234567890a"]
    for i, ph in enumerate(phones):
        d = ref.校验手机号(ph)
        assert out[f"V{i}"] == ("1" if d["valid"] else "0"), f"valid[{ph}]"
        assert out[f"PH{i}"] == str(d["phone"]), f"phone[{ph}]"
        assert out[f"CA{i}"] == str(d["carrier"]), f"carrier[{ph}]"
        exp_region = "NONE" if d["region"] is None else str(d["region"])
        assert out[f"RG{i}"] == exp_region, f"region[{ph}]"
        assert int(out[f"EC{i}"]) == len(d["errors"]), f"errors len[{ph}]"
        assert _collect_seq(out, f"E{i}_") or (int(out[f"EC{i}"]) == 0), f"errors[{ph}]"

    assert out["OP0"] == ref.获取运营商("13812345678")
    assert out["OP1"] == ref.获取运营商("17012345678")
    assert out["OP2"] == ref.获取运营商("14012345678")
    assert out["OR0"] == ref.获取归属地("13800138000")
    assert out["OR1"] == ref.获取归属地("13431234567")
    assert out["OR2"] == ref.获取归属地("19912345678")


# ═══════════════════════════════════════════════════════════════════════
# 5. 身份证校验
# ═══════════════════════════════════════════════════════════════════════

def test_身份证校验_O0对拍():
    ref = _load_py("身份证校验", "_py_ref_sfzh")

    def mk(前17):
        """按 .py 校验码算法反推合法 18 位号。"""
        return 前17 + ref.计算校验码(前17)

    num_ok = mk("11010119900101123")
    num_leap = mk("11010120000229001")
    num_baddate = mk("11010119900230001")
    num_badregion = mk("99999919900101123")
    num_wrong = "110101199001011236"  # 期望校验码 7，实际 6
    src = f"""从 身份证校验 导入 校验身份证 提取出生日期 提取性别 提取地区 计算校验码
段落 主:
  设 p 为 ["{num_ok}", "{num_leap}", "{num_baddate}", "{num_badregion}", "{num_wrong}", "1101011990010112", "1101011990010112377", "11010119900101123A"]
  设 k 为 0
  遍历 号 之 p:
    设 r 为 校验身份证(号)
    设 v 为 字典获取(r, "valid", 假)
    如果 v == 真:
      输出("V" 加上 转字符串(k) 加上 "=1")
    否则:
      输出("V" 加上 转字符串(k) 加上 "=0")
    输出("BD" 加上 转字符串(k) 加上 "=" 加上 字典获取(r, "birthday", ""))
    输出("GD" 加上 转字符串(k) 加上 "=" 加上 字典获取(r, "gender", ""))
    设 rg 为 字典获取(r, "region", "")
    如果 rg == 空:
      输出("RG" 加上 转字符串(k) 加上 "=NONE")
    否则:
      输出("RG" 加上 转字符串(k) 加上 "=" 加上 rg)
    设 es 为 字典获取(r, "errors", [])
    输出("EC" 加上 转字符串(k) 加上 "=" 加上 转字符串(长(es)))
    设 ei 为 0
    遍历 m 之 es:
      输出("E" 加上 转字符串(k) 加上 "_" 加上 转字符串(ei) 加上 "=" 加上 m)
      设 ei 为 ei 加上 1
    设 k 为 k 加上 1
  输出("B0=" 加上 提取出生日期("{num_ok}"))
  输出("B1=" 加上 提取出生日期("1101011990010112"))
  输出("G0=" 加上 提取性别("{num_ok}"))
  输出("G1=" 加上 提取性别("1101011990010112"))
  输出("R0=" 加上 提取地区("{num_ok}"))
  输出("R1=" 加上 提取地区("999999199001011230"))
  输出("C0=" 加上 计算校验码("11010119900101123"))
  输出("C1=" 加上 计算校验码("1101011990010112"))
"""
    out = _native_run(src)
    nums = [num_ok, num_leap, num_baddate, num_badregion, num_wrong,
            "1101011990010112", "1101011990010112377", "11010119900101123A"]
    for i, n in enumerate(nums):
        d = ref.校验身份证(n)
        assert out[f"V{i}"] == ("1" if d["valid"] else "0"), f"valid[{n}]"
        assert out[f"BD{i}"] == str(d["birthday"]), f"birthday[{n}]"
        assert out[f"GD{i}"] == str(d["gender"]), f"gender[{n}]"
        exp_region = "NONE" if d["region"] is None else str(d["region"])
        assert out[f"RG{i}"] == exp_region, f"region[{n}]"
        assert int(out[f"EC{i}"]) == len(d["errors"]), f"errors len[{n}]"
        assert _collect_seq(out, f"E{i}_") == list(d["errors"]), f"errors[{n}]"

    assert out["B0"] == ref.提取出生日期(num_ok)
    assert out["B1"] == ref.提取出生日期("1101011990010112")
    assert out["G0"] == ref.提取性别(num_ok)
    assert out["G1"] == ref.提取性别("1101011990010112")
    assert out["R0"] == ref.提取地区(num_ok)
    assert out["R1"] == ref.提取地区("999999199001011230")
    assert out["C0"] == ref.计算校验码("11010119900101123")
    assert out["C1"] == ref.计算校验码("1101011990010112")


# ═══════════════════════════════════════════════════════════════════════
# 6. 中文分词（正向最大匹配 + 653 词内嵌词典）
# ═══════════════════════════════════════════════════════════════════════

def test_中文分词_O0对拍():
    src = """从 中文分词 导入 分词 添加自定义词 加载词典
段落 主:
  设 r0 为 分词("今天天气真不错")
  输出("C0=" 加上 转字符串(长(r0)))
  设 i0 为 0
  遍历 t 之 r0:
    输出("T0_" 加上 转字符串(i0) 加上 "=" 加上 转字符串(长(t)) 加上 ":" 加上 t)
    设 i0 为 i0 加上 1
  设 r1 为 分词("你好世界人工智能")
  输出("C1=" 加上 转字符串(长(r1)))
  设 i1 为 0
  遍历 t 之 r1:
    输出("T1_" 加上 转字符串(i1) 加上 "=" 加上 转字符串(长(t)) 加上 ":" 加上 t)
    设 i1 为 i1 加上 1
  设 r2 为 分词("abcd")
  输出("C2=" 加上 转字符串(长(r2)))
  设 i2 为 0
  遍历 t 之 r2:
    输出("T2_" 加上 转字符串(i2) 加上 "=" 加上 转字符串(长(t)) 加上 ":" 加上 t)
    设 i2 为 i2 加上 1
  设 r3 为 分词("")
  输出("C3=" 加上 转字符串(长(r3)))
  设 r4 为 分词("我1995年在北京")
  输出("C4=" 加上 转字符串(长(r4)))
  设 i4 为 0
  遍历 t 之 r4:
    输出("T4_" 加上 转字符串(i4) 加上 "=" 加上 转字符串(长(t)) 加上 ":" 加上 t)
    设 i4 为 i4 加上 1
  添加自定义词("光明语言")
  设 r5 为 分词("光明语言很棒")
  输出("C5=" 加上 转字符串(长(r5)))
  设 i5 为 0
  遍历 t 之 r5:
    输出("T5_" 加上 转字符串(i5) 加上 "=" 加上 转字符串(长(t)) 加上 ":" 加上 t)
    设 i5 为 i5 加上 1
  加载词典(["深圳大学", "计算机科学"])
  设 r6 为 分词("深圳大学计算机科学专业")
  输出("C6=" 加上 转字符串(长(r6)))
  设 i6 为 0
  遍历 t 之 r6:
    输出("T6_" 加上 转字符串(i6) 加上 "=" 加上 转字符串(长(t)) 加上 ":" 加上 t)
    设 i6 为 i6 加上 1
"""
    out = _native_run(src)

    def seq(prefix, n):
        items = {}
        for k, v in out.items():
            if k.startswith(prefix):
                items[int(k[len(prefix):])] = v
        return [items[i] for i in range(n)]

    ref = _load_py("中文分词", "_py_ref_cfz0")
    for i, s in enumerate(["今天天气真不错", "你好世界人工智能", "abcd", "", "我1995年在北京"]):
        exp = ref.分词(s)
        assert int(out[f"C{i}"]) == len(exp), f"分词len[{s}]"
        got = seq(f"T{i}_", len(exp))
        exp_fmt = [f"{len(t)}:{t}" for t in exp]
        assert got == exp_fmt, f"分词[{s}]"

    # 添加自定义词（.py 独立全新实例，避免污染）
    ref2 = _load_py("中文分词", "_py_ref_cfz1")
    ref2.添加自定义词("光明语言")
    exp5 = ref2.分词("光明语言很棒")
    assert int(out["C5"]) == len(exp5)
    assert seq("T5_", len(exp5)) == [f"{len(t)}:{t}" for t in exp5], "分词[自定义词]"

    # 加载词典（.py 独立全新实例）
    ref3 = _load_py("中文分词", "_py_ref_cfz2")
    ref3.加载词典(["深圳大学", "计算机科学"])
    exp6 = ref3.分词("深圳大学计算机科学专业")
    assert int(out["C6"]) == len(exp6)
    assert seq("T6_", len(exp6)) == [f"{len(t)}:{t}" for t in exp6], "分词[加载词典]"


# ═══════════════════════════════════════════════════════════════════════
# 7. 拼音转换（源 .py 残缺无函数，以黄金对照对拍：解析 _PINYIN_MAP + 同款算法）
# ═══════════════════════════════════════════════════════════════════════

def _load_pinyin_map():
    """解析 stdlib/拼音转换.py 的 _PINYIN_MAP（按 Python dict 后值覆盖前值去重）。"""
    src = open(os.path.join(_STDLIB, "拼音转换.py"), encoding="utf-8").read()
    pairs = re.findall(r"'([^']+)'\s*:\s*'([^']*)'", src)
    m = {}
    for k, v in pairs:
        m[k] = v
    return m


def _gold_pinyin(m):
    def 转拼音(文本, 分隔符=" "):
        return 分隔符.join(m.get(c, c) for c in 文本)

    def 拼音首字母(文本):
        return "".join(m[c][0] if c in m else c for c in 文本)

    return 转拼音, 拼音首字母


def test_拼音转换_O0对拍():
    src = """从 拼音转换 导入 转拼音 拼音首字母
段落 主:
  输出("V0=" 加上 转拼音("你好世界"))
  输出("V1=" 加上 转拼音("中华人民共和国"))
  输出("V2=" 加上 转拼音("光明2a"))
  输出("V3=" 加上 转拼音("光明2a", ""))
  输出("V4=" 加上 转拼音("长重了着", " "))
  输出("V5=" 加上 转拼音("", " "))
  输出("V6=" 加上 转拼音("你好世界！Hello 123", " "))
  输出("I0=" 加上 拼音首字母("你好世界"))
  输出("I1=" 加上 拼音首字母("中华人民共和国"))
  输出("I2=" 加上 拼音首字母("光明2a"))
  输出("I3=" 加上 拼音首字母(""))
  输出("I4=" 加上 拼音首字母("好𠀀a"))
"""
    out = _native_run(src, timeout=360)
    m = _load_pinyin_map()
    assert len(m) >= 2500, f"拼音表去重后键数异常: {len(m)}"
    转拼音, 首字母 = _gold_pinyin(m)

    assert out["V0"] == 转拼音("你好世界")
    assert out["V1"] == 转拼音("中华人民共和国")
    assert out["V2"] == 转拼音("光明2a")
    assert out["V3"] == 转拼音("光明2a", "")
    assert out["V4"] == 转拼音("长重了着", " ")
    assert out["V5"] == 转拼音("", " ")
    assert out["V6"] == 转拼音("你好世界！Hello 123", " ")
    assert out["I0"] == 首字母("你好世界")
    assert out["I1"] == 首字母("中华人民共和国")
    assert out["I2"] == 首字母("光明2a")
    assert out["I3"] == 首字母("")
    assert out["I4"] == 首字母("好𠀀a")
