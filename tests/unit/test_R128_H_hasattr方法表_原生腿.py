# -*- coding: utf-8 -*-
"""
R128-H 定向用例：dv_has_attr 假阴性修复——类方法表查找路径。

背景：dv_has_attr 此前只搜实例字段 blob（dv_r117_obj_has_member），
类方法注册在 LightClassInfo 方法表里、不在实例字段串中 →
hasattr(实例, "方法名") 原生腿恒假（Python 腿为真），跨腿分叉。
已翻面的 断言工具.断言属性存在 对方法名误报失败。

修复：dv_has_attr 在字段 blob 未命中时，若对象是类实例（OBJ_PREFIX），
再取类名、沿继承链查 dv_find_method。

与 Python 腿 stdlib/builtins.py 同输入对拍，逐条一致。
「编译 + 运行」整体 fork 到独立子进程（复用 _t6b_native_helper.py）。
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

类 甲:
  段 初始化():
    己.名称 为 "甲实例"
  段 标记():
    返回 "标记了"

段 主:
  设 实例 为 新建 甲()
  输出("字段名称=" 加上 转字符串(hasattr(实例, "名称")))
  输出("方法标记=" 加上 转字符串(hasattr(实例, "标记")))
  输出("方法初始化=" 加上 转字符串(hasattr(实例, "初始化")))
  输出("不存在=" 加上 转字符串(hasattr(实例, "没有的属性")))
  输出("字典名称=" 加上 转字符串(hasattr({"a": 1}, "名称")))
  输出("列表追加=" 加上 转字符串(hasattr([1,2,3], "追加")))
  输出("整数名称=" 加上 转字符串(hasattr(123, "名称")))
  输出("字符串名称=" 加上 转字符串(hasattr("串", "名称")))
"""

# 与 Python 腿同输入实测对拍（来源：本机 python 腿跑 p1_hasattr.light）
_EXPECT = {
    "字段名称": "真",
    "方法标记": "真",   # 修复前原生腿 = 假（假阴性）；修复后 = 真
    "方法初始化": "真", # 构造方法是否注册在方法表里（待实测）
    "不存在": "假",
    "字典名称": "假",
    "列表追加": "假",
    "整数名称": "假",
    "字符串名称": "假",
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
    try:
        with tempfile.TemporaryDirectory(prefix="_r128h_") as d:
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
class R128HHasattr方法表反跑(unittest.TestCase):
    """dv_has_attr 类方法表查找路径——原生腿 O0 定向反跑（R128-H）。"""

    def test_hasattr_双腿对拍(self):
        out = _native_run(_SRC)
        for key, want in _EXPECT.items():
            got = out.get(key)
            self.assertEqual(
                got, want,
                f"{key}: 原生腿={got!r} 期望={want!r}（Python 腿实测）",
            )


if __name__ == "__main__":
    unittest.main()
