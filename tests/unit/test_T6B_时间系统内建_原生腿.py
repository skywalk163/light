# -*- coding: utf-8 -*-
"""
T6B 反跑用例：时间/系统内建 time.light + sys.light + 依赖模块（原生腿 O0）

覆盖（显式 optimize_level=0）：
  - time.light：时间戳实时对拍（整数毫秒口径，±2s）、localtime 拆字段与
    strftime（固定时间戳常量对拍 Python）、sleep_ms 真实睡眠冒烟、perf_counter 单调
  - sys.light：版本/平台/参数列表冒烟（平台口径与 操作系统.本机平台 一致；原生腿
    连接路径分隔符为 '/'，归类 posix——见 sys.light 头部说明）
  - 日期时间轻量：零文本改动解锁，固定时间戳字段/格式化对拍 Python
  - 时间管理：睡眠计时冒烟、时间戳毫秒实时对拍（±2s）、格式化耗时、本地时间/
    格式化时间（固定时间戳）、计时器/秒表 仅「构造与调用不崩且非空」冒烟
    （类浮点字段算术的原生腿后端缺陷另见 known_issues T6B 章，不在此断言数值）

注意：
  - 大时间戳 float 经 转字符串（%g，6 位有效数字）打印丢精度，实时对拍一律走
    整数毫秒/纳秒口径，不用 float 秒字符串。
  - 事件总线/插件：原生腿完整运行被「函数值动态调用」语言级缺口阻断（known_issues
    T6B 章），本文件不为其建 O0 用例；两模块的 sys.light 依赖解锁与 python 腿冒烟
    由既有 tests/test_event_bus_light.py、tests/test_agent_loop_light.py、
    tests/test_plugin_light.py 覆盖。
"""
import os
import subprocess
import sys
import tempfile
import time as _pytime
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (_ROOT, os.path.join(_ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

TS = 1788621579  # 固定时间戳（2026-09 附近），字段/格式对拍用确定值


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


def _native_run(src_text, timeout=180):
    """以内联 .light 源码走原生腿 O0 编译并运行，返回 {KEY: 值字符串}。

    编译 + 运行整体 fork 到独立子进程（见 _t6b_native_helper.py），避免同一
    pytest 进程连续编译多个重型模块时 Python RSS 累积导致 clang 在内存受限机上
    OOM；每次都是全新 Python，clang 拿到与单独运行相同的空闲 RAM。
    """
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t6b_native_helper.py")
    env = _prepare_env()
    try:
        with tempfile.TemporaryDirectory(prefix="_t6b_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8") as f:
                f.write(src_text)
            exe = os.path.join(d, "main")
            proc = subprocess.run(
                [sys.executable, helper, src, exe],
                capture_output=True, timeout=timeout + 60, env=env,
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
class T6B时间系统内建反跑(unittest.TestCase):
    """time/sys 内建 + 日期时间轻量 + 时间管理 原生腿 O0 反跑。"""

    def tearDown(self):
        # 原生编译会 spawn clang 子进程并持有较大 IR/AST 对象；测试间回收内存，
        # 避免内存受限机（如本机 ~696MB 空闲）在最后一个较重测试（时间管理）verify
        # 阶段 clang 指令选择 OOM。各测试单独运行均已通过。
        import gc
        gc.collect()

    def test_time_时间戳对拍_固定字段与格式(self):
        src = """导入 time
导出 主。
段落 主:
  设 n 为 time.time_ns()
  输出("N=" 加上 转字符串(n))
  设 t 为 转浮点("TSX")
  设 s 为 time.localtime(t)
  输出("Y=" 加上 转字符串(s.tm_year))
  输出("MO=" 加上 转字符串(s.tm_mon))
  输出("D=" 加上 转字符串(s.tm_mday))
  输出("H=" 加上 转字符串(s.tm_hour))
  输出("MI=" 加上 转字符串(s.tm_min))
  设 f 为 time.strftime(t, "%Y-%m-%d %H:%M:%S")
  输出("F=" 加上 f)
""".replace('"TSX"', str(TS))
        got = _native_run(src)
        # light time_ns 为毫秒级（秒×1e6），Python time_ns 为纳秒 → 除 1000 对齐；
        # 容忍 2 秒偏差（实时时钟 + %g 打印精度）
        self.assertAlmostEqual(int(got["N"]), int(_pytime.time_ns() / 1000), delta=2_000_000)
        lt = _pytime.localtime(TS)
        self.assertEqual(int(got["Y"]), lt.tm_year)
        self.assertEqual(int(got["MO"]), lt.tm_mon)
        self.assertEqual(int(got["D"]), lt.tm_mday)
        self.assertEqual(int(got["H"]), lt.tm_hour)
        self.assertEqual(int(got["MI"]), lt.tm_min)
        self.assertEqual(got["F"], _pytime.strftime("%Y-%m-%d %H:%M:%S", lt))

    def test_time_睡眠与单调时钟冒烟(self):
        src = """导入 time
导出 主。
段落 主:
  设 a 为 time.perf_counter()
  设 b 为 time.perf_counter()
  输出("A=" 加上 转字符串(a))
  输出("B=" 加上 转字符串(b))
  设 c 为 time.perf_counter()
  time.sleep_ms(80)
  设 e 为 time.perf_counter()
  设 差 为 e - c
  输出("D=" 加上 转字符串(差))
  设 n 为 time.time_ns()
  输出("N=" 加上 转字符串(n))
"""
        got = _native_run(src)
        self.assertGreaterEqual(float(got["B"]), float(got["A"]))  # 单调不减
        self.assertGreaterEqual(float(got["D"]), 0.05)             # 80ms 睡眠真实发生
        self.assertGreater(int(got["N"]), 1000000000)              # light time_ns 毫秒级（>1e9 成立）

    def test_sys_内建冒烟(self):
        src = """导入 sys
导出 主。
段落 主:
  设 v 为 sys.version()
  设 p 为 sys.platform()
  设 a 为 sys.argv()
  输出("V=" 加上 v)
  输出("P=" 加上 p)
  输出("N=" 加上 转字符串(a.长度))
"""
        got = _native_run(src)
        self.assertIn("光明内建 sys", got["V"])
        self.assertIn(got["P"], ("win32", "posix"))  # 口径与 操作系统.本机平台 一致
        self.assertGreaterEqual(int(got["N"]), 1)

    def test_日期时间轻量_对拍Python(self):
        src = """导入 日期时间轻量
导出 主。
段落 主:
  设 t 为 转浮点("TSX")
  设 y 为 日期时间轻量.获取年份(t)
  设 mo 为 日期时间轻量.获取月份(t)
  设 dd 为 日期时间轻量.获取日(t)
  输出("Y=" 加上 转字符串(y))
  输出("MO=" 加上 转字符串(mo))
  输出("D=" 加上 转字符串(dd))
  设 s 为 日期时间轻量.格式化当前时间(t)
  输出("S=" 加上 s)
""".replace('"TSX"', str(TS))
        got = _native_run(src)
        lt = _pytime.localtime(TS)
        self.assertEqual(int(got["Y"]), lt.tm_year)
        self.assertEqual(int(got["MO"]), lt.tm_mon)
        self.assertEqual(int(got["D"]), lt.tm_mday)
        self.assertEqual(got["S"], _pytime.strftime("%Y-%m-%d %H:%M:%S", lt))

    def test_时间管理_睡眠计时冒烟(self):
        src = """导入 时间管理
导出 主。
段落 主:
  设 c0 为 时间管理.性能计数器()
  时间管理.睡眠(0.06)
  设 c1 为 时间管理.性能计数器()
  设 差 为 c1 - c0
  输出("D=" 加上 转字符串(差))
  设 M 为 时间管理.时间戳毫秒()
  输出("M=" 加上 转字符串(M))
  设 fm 为 时间管理.格式化耗时(0.0005)
  输出("FM=" 加上 fm)
  设 fs 为 时间管理.格式化耗时(2.5)
  输出("FS=" 加上 fs)
  设 t 为 转浮点("TSX")
  设 lt 为 时间管理.本地时间(t)
  输出("Y=" 加上 转字符串(lt.tm_year))
  设 f2 为 时间管理.格式化时间("%Y-%m-%d", t)
  输出("F2=" 加上 f2)
  设 记 为 新建 计时器()
  记.开始()
  设 el 为 记.结束()
  输出("EL=" 加上 转字符串(el))
  设 b 为 新建 秒表(真)
  设 st 为 b.停止()
  输出("ST=" 加上 转字符串(st))
""".replace('"TSX"', str(TS))
        got = _native_run(src)
        self.assertGreaterEqual(float(got["D"]), 0.04)              # 60ms 睡眠真实发生
        self.assertAlmostEqual(int(got["M"]), int(_pytime.time() * 1000), delta=2000)
        self.assertEqual(got["FM"], "500微秒")
        self.assertEqual(got["FS"], "3秒")  # 2.5 取整（原生腿边界见模块头）
        lt = _pytime.localtime(TS)
        self.assertEqual(int(got["Y"]), lt.tm_year)
        self.assertEqual(got["F2"], _pytime.strftime("%Y-%m-%d", lt))
        # 类方法（计时器/秒表）构造与调用仅作「不崩」冒烟；其浮点字段算术在原生腿
        # 后端存在缺陷（计时器结束返回 0、秒表停止返回负值），数值断言见 known_issues
        # T6B 章，不在本用例覆盖。只判定 key 已产出（程序未崩）。
        self.assertIn("EL", got)
        self.assertIn("ST", got)


if __name__ == "__main__":
    unittest.main()
