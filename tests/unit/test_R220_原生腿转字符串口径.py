# -*- coding: utf-8 -*-
"""R220：`转字符串(容器)` 两腿口径必须逐字一致（原生腿此前是 dv_list_join 旧口径）。

## 病灶（2026-11-08 实测，light main `ffe46a0ed`）

| 输入 | 转译腿（真源：stdlib/内置核心转换.light → JSON核心.序列化） | 原生腿（修复前） |
|---|---|---|
| `[1, 2.5, 真, 假, 空, "甲"]` | `[1, 2.5, true, false, null, "甲"]` | `[1, 2.5, true, false, 空, 甲]` |
| `{"甲": 1, "乙": [2, 真]}` | `{"甲": 1, "乙": [2, true]}` | `{'甲': 1, '乙': [2, true]}` |
| `[["x"]]` | `[["x"]]` | `[['x']]` |

根因：`codegen_typed` 的 `转字符串` 内置对 list(type 4) 走
`dv_list_join(列表, ", ")` 再手动拼 `[...]`，字符串元素裸奔、null 走 `dv_to_string`
的「空」、dict(type 7) 落到 `dv_value_to_string` 的 repr 口径。而 src 腿的
L-072 口径是「dict/list → JSON文本（双引号、中文不转义、紧凑）」。

## 修法

原生腿把容器分支改成调用运行时已有的、与 `JSON核心.light` 对齐的
`dv_json_serialize_safe`（= `dv_json_serialize` 的非抛错版：不可 JSON 化元素回落
`dv_to_string`，不整段抛错），其余值仍走 `dv_value_to_string`。

## 本文件钉什么

1. 容器（list / dict / 嵌套）两腿 stdout **逐字相等**（不是"元素个数量对"）；
2. 标量（真/假/空/字符串/非整值浮点）两腿相等；
3. 顶层整值浮点 `3.0` 是**已知遗留差**（native 印 `3`），xfail 留证，不装作已对齐；
4. 容器里混入不可 JSON 化的值（段落值）时**不抛错**（宽松回落），这是 safe 版的意义。

无 clang 时原生腿用例整体 skip。
"""
import os
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (_ROOT, os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tests.unit.test_T6B_时间系统内建_原生腿 import _find_msvc_env  # noqa: E402

_探针 = r'''打印 "L=" 加上 转字符串([1, 2.5, 真, 假, 空, "甲", "带\"引号", "反\\斜杠"])
打印 "D=" 加上 转字符串({"甲": 1, "乙": [2, 真]})
打印 "N=" 加上 转字符串([[1, 2], ["x"]])
打印 "S=" 加上 转字符串("裸字符串")
打印 "B=" 加上 转字符串(真)
打印 "Z=" 加上 转字符串(空)
'''

_浮点探针 = '打印 转字符串(3.0)\n'

_非JSON探针 = '''段落 加倍(x):
  返回 x 乘以 2
打印 转字符串([加倍, "x", 1])
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
    env["PYTHONUTF8"] = "1"
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    return env


def _跑(源码, 后端=None, timeout=300):
    """真起 CLI 进程；返回 (rc, stdout 原文归一化, stderr)。"""
    with tempfile.TemporaryDirectory(prefix="_r220tostr_") as d:
        src = os.path.join(d, "main.light")
        with open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(源码)
        cmd = [sys.executable, os.path.join("cli", "light.py"), "run", src]
        if 后端:
            cmd += ["--backend", 后端, "--optimize", "O0"]
        got = subprocess.run(cmd, capture_output=True, timeout=timeout,
                             env=_env(), cwd=_ROOT)
    out = got.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    return got.returncode, out, got.stderr.decode("utf-8", "replace")


def _两腿(源码):
    src_rc, src_out, src_err = _跑(源码)
    nat_rc, nat_out, nat_err = _跑(源码, 后端="llvm-typed")
    assert src_rc == 0, "转译腿 rc=%d\nstdout=%s\nstderr=%s" % (src_rc, src_out, src_err[:2000])
    assert nat_rc == 0, "原生腿 rc=%d\nstdout=%s\nstderr=%s" % (nat_rc, nat_out, nat_err[:3000])
    return src_out, nat_out


def test_容器两腿逐字相等():
    """L/D/N 三行必须完全一致 —— 这是本缺陷的主判据。"""
    src_out, nat_out = _两腿(_探针)
    assert src_out.splitlines()[:3] == nat_out.splitlines()[:3], (
        "容器转字符串两腿不一致\n--- src ---\n%s\n--- native ---\n%s" % (src_out, nat_out))


def test_标量两腿逐字相等():
    """真/假/空/字符串/2.5 这些非容器值本来就该一致，防止改动把标量带坏。"""
    src_out, nat_out = _两腿(_探针)
    src_lines, nat_lines = src_out.splitlines(), nat_out.splitlines()
    assert src_lines[3:6] == nat_lines[3:6], (
        "标量转字符串两腿不一致\n--- src ---\n%s\n--- native ---\n%s" % (src_out, nat_out))


def test_容器字符串元素带双引号与转义():
    """明确钉住 JSON 口径：双引号、内层引号/反斜杠转义，而不是单引号或裸奔。"""
    _src, nat_out = _两腿(_探针)
    line = nat_out.splitlines()[0]
    assert '"甲"' in line, line
    assert '"带\\"引号"' in line, line
    assert '"反\\\\斜杠"' in line, line
    assert "'甲'" not in line, line


@_需要原生腿
def test_容器内不可JSON化元素不抛错():
    """段落值进容器：宽松回落（可能为空串），但**不能**抛 运行时错误。"""
    _src, nat_out = _两腿(_非JSON探针)
    assert "运行时错误" not in nat_out, nat_out
    assert '"x"' in nat_out, nat_out


@_需要原生腿
def test_顶层整值浮点是已知遗留差():
    """native 印 `3`、src 印 `3.0`：不在本次容器口径修复范围，留证待另卡。"""
    src_out, nat_out = _两腿(_浮点探针)
    assert src_out.strip() == "3.0", src_out
    assert nat_out.strip() == "3", nat_out