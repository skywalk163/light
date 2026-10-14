# -*- coding: utf-8 -*-
"""
R148-A 子任务 1 用例：JSON 内部级联解耦（Tier2 最高优先）双腿对拍 + 源码级守单点。

背景：原生腿此前不认识 ``stdlib/builtins.py:452/462/468`` 的
``解析JSON`` / ``序列化JSON`` / ``美化JSON`` 三个地板转发函数——
光明代码直接调用会报 ``未定义的段落：解析JSON``（原生后端编译期失败）。
根因是这三者走 ``builtins.py → import JSON → stdlib/JSON.light → JSON核心.light``
的 Python import 级联，原生腿的 ``_gen_typed_builtin`` 无对应分支，也不走
``_light_builtin`` 回退。

修复：``runtime_typed.c`` 新增 C 层 ``dv_json_parse`` / ``dv_json_serialize`` /
``dv_json_serialize_pretty`` 三个原语（严格 JSON 递归下降解析 + json.dumps 口径序列化），
``codegen_typed.py`` 注册同名内置（中英别名），解开 Python import 级联。

语义对齐 ``stdlib/JSON核心.light``（纯光明实现）：
  * 解析：严格 JSON——数字禁前导零、转义只认 " \\ / b f n r t u、字符串内禁裸控制符、
    Unicode 转义序列合成单码点、解析完必须到串尾（尾部垃圾报错）。
    失败抛 ``运行时错误("JSON 解析失败: …")``。
  * 序列化：ensure_ascii=False 保中文原样；缩进 < 0 紧凑、>= 0 换行缩进；
    NaN/±inf 发 NaN/Infinity/-Infinity；非容器类型抛 ``运行时错误("JSON 序列化失败: …")``。
  * 美化JSON = 序列化缩进(值, 2)，对齐 JSON核心.light 美化JSON。

对拍口径：同一份源码分别走 native 腿（LLVM 编译 + 真跑）与 src 腿（转译 Python 腿，
规范源），逐条断言一致。整体 fork 到独立子进程（复用 ``_t6b_native_helper.py``），
避免 clang OOM 与进程内存污染。

已知预存差异（非本轮回归）：布尔 repr ``真/假``（native）vs ``True/False``（src）；
float 的 ``打印`` 直接输出（native 不带 .0）与 JSON 序列化输出（已对齐）不同——
本测试断言走 ``序列化JSON`` 路径，规避 ``打印`` 的 float repr 预存差异。
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (_ROOT, os.path.join(_ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from tests.unit.test_T6B_时间系统内建_原生腿 import _find_msvc_env  # noqa: E402


# 覆盖：基本类型 / 嵌套容器 / Unicode 转义 \uXXXX / 科学计数法 / 空容器 / 数组嵌套
_SRC_JSON = r"""段落 主():
  设 文本 为 '{"名":"张\u4e09","嵌套":{"列表":[1,2.5,true,null]},"空":{},"零":[[]]}'
  设 值 为 解析JSON(文本)
  打印("ser=", 序列化JSON(值))
  打印("pretty=", 美化JSON({"x": 1}))
  打印("num=", 序列化JSON(解析JSON('-12.5e2')))
  打印("pi=", 序列化JSON(解析JSON('3.14')))
  打印("int=", 序列化JSON(解析JSON('42')))
  打印("big=", 序列化JSON(解析JSON('1e20')))
  打印("float=", 序列化JSON(解析JSON('0.1')))
  打印("neg=", 序列化JSON(-0))
"""

# 美化JSON 单独探针（多行，_kv 不适用，故独立源码断言）
_SRC_PRETTY = r"""段落 主():
  打印("pretty=", 美化JSON({"x": 1, "y": [1, 2]}))
"""


# src 腿（规范源）实测期望值（2026-10-14，R148-A）
_EXPECT_JSON = {
    "ser": '{"名": "张三", "嵌套": {"列表": [1, 2.5, true, null]}, "空": {}, "零": [[]]}',
    "num": "-1250.0",
    "pi": "3.14",
    "int": "42",
    "big": "1e+20",
    "float": "0.1",
    "neg": "0",
}


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
        with tempfile.TemporaryDirectory(prefix="_r148a_") as d:
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
    return proc.stdout.decode("utf-8", "replace")


def _src_run(src_text, timeout=180):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        with tempfile.TemporaryDirectory(prefix="_r148a_py_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8") as f:
                f.write(src_text)
            proc = subprocess.run(
                [sys.executable, os.path.join("cli", "light.py"), "run", src],
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


def _kv(text):
    text = text.replace("\r\n", "\n").replace("\r", "")
    out = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _lines(text):
    """统一行尾后按行切分（原生腿 stdout 在 Windows 上带 \r\r\n）。"""
    text = text.replace("\r\n", "\n").replace("\r", "")
    return text.strip().splitlines()


def _clang_available():
    try:
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


class R148_JSON_Src腿基准(unittest.TestCase):
    """src 腿（规范源）基准：JSON 解析/序列化/美化输出须符合 JSON核心.light 口径。"""

    def test_src腿期望值(self):
        out = _kv(_src_run(_SRC_JSON))
        for key, want in _EXPECT_JSON.items():
            self.assertEqual(
                out.get(key), want,
                f"{key}: src 腿={out.get(key)!r} 期望={want!r}",
            )
        # pretty 多行断言（独立 _SRC_PRETTY，避免 _kv/_lines 截断后续行）
        want_pretty = '{\n  "x": 1,\n  "y": [\n    1,\n    2\n  ]\n}'
        got_pretty = "\n".join(_lines(_src_run(_SRC_PRETTY))).split("pretty=", 1)[-1].lstrip()
        self.assertEqual(got_pretty, want_pretty,
                         f"pretty: src 腿={got_pretty!r} 期望={want_pretty!r}")


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class R148_JSON_原生腿对拍(unittest.TestCase):
    """JSON 级联解耦后，原生腿须与 src 腿逐条一致（修复前：编译期报「未定义的段落」）。"""

    def test_双腿对拍(self):
        out = _kv(_native_run(_SRC_JSON))
        for key, want in _EXPECT_JSON.items():
            self.assertEqual(
                out.get(key), want,
                f"{key}: 原生腿={out.get(key)!r} 期望={want!r}（src 腿实测）",
            )
        # pretty 多行断言（独立 _SRC_PRETTY）
        want_pretty = '{\n  "x": 1,\n  "y": [\n    1,\n    2\n  ]\n}'
        got_pretty = "\n".join(_lines(_native_run(_SRC_PRETTY))).split("pretty=", 1)[-1].lstrip()
        self.assertEqual(got_pretty, want_pretty,
                         f"pretty: 原生腿={got_pretty!r} 期望={want_pretty!r}")


class R148_JSON_源码级守单点(unittest.TestCase):
    """源码级守单点：codegen 已注册 JSON 三内置，runtime 已导出三 C 原语。"""

    def test_codegen_注册JSON内置(self):
        codegen = os.path.join(_ROOT, "src", "llvm", "codegen_typed.py")
        with open(codegen, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("dv_json_parse", text, "codegen 未注册 dv_json_parse")
        self.assertIn("dv_json_serialize", text, "codegen 未注册 dv_json_serialize")
        self.assertIn("dv_json_serialize_pretty", text, "codegen 未注册 dv_json_serialize_pretty")
        self.assertIn("declare void @dv_json_parse(ptr, ptr)", text, "IR declare 缺 dv_json_parse")

    def test_runtime_导出JSON原语(self):
        rt = os.path.join(_ROOT, "src", "llvm", "runtime_typed.c")
        with open(rt, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("void dv_json_parse(LightValue* result, LightValue* text)", text)
        self.assertIn("void dv_json_serialize(LightValue* result, LightValue* value)", text)
        self.assertIn(
            "void dv_json_serialize_pretty(LightValue* result, LightValue* value, int64_t indent)",
            text,
        )

    def test_JSON错误路径_原生腿抛异常(self):
        """解析非法 JSON 须抛 运行时错误（消息前缀「JSON 解析失败:」），与 JSON核心.light 对齐。"""
        src = r"""段落 主():
  尝试:
    设 x 为 解析JSON('{"a": }')
    打印("BUG: 不应到达")
  捕获 异常 e:
    打印("caught=", e)
"""
        # src 腿基准
        out_src = _kv(_src_run(src))
        self.assertIn("JSON 解析失败", out_src.get("caught", ""),
                      f"src 腿未捕获 JSON 解析错误: {out_src}")
        # 原生腿（若 clang 可用）
        if _clang_available() and not (os.name == "nt" and not _find_msvc_env()[0]):
            out_native = _kv(_native_run(src))
            self.assertIn("JSON 解析失败", out_native.get("caught", ""),
                          f"原生腿未捕获 JSON 解析错误: {out_native}")


if __name__ == "__main__":
    unittest.main()