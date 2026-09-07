# -*- coding: utf-8 -*-
"""CI-A 子任务 1：非 LLVM 路径（cli/light.py run）真跑 Base64.light / 哈希.light，
与 Python base64 / hashlib 对拍。

## 为什么这条测试存在

`stdlib/Base64.light` / `stdlib/哈希.light` 按函数名调用 `_b64_encode` / `_md5` /
`_sha1` / `_sha256` / `_sha512` / `_hmac_sha256` 这批 runtime 内建。LLVM 原生腿在
`src/llvm/codegen_typed.py:2482+` 有同名派发；解释器执行路径（`cli/light.py run`）
此前没有 —— 冒烟 Base64/哈希 四块 `name '_md5' is not defined`（CI-A A 类回归）。

修复 = codegen `builtin_map` 把别名接到 `_light_builtin.*`（stdlib/builtins.py
经 stdlib/_t5b_runtime.py 提供同名 Python 实现，口径与 C dv_* 字节级一致）。

本测试走与冒烟相同的子进程链路（`python cli/light.py run`），判据 = 输出逐行等于
Python base64/hashlib/pbkdf2_hmac 的期望值。覆盖：Base64 编解码、MD5/SHA1/SHA256/
SHA512 空串+非空串（含中文）、HMAC_SHA256 基本用例。
"""
import base64
import hashlib
import os
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 样本刻意避开双引号与反斜杠：光明字符串字面量用双引号，转义只覆盖这两种。
样本 = ["", "abc", "你好光明", "Hello, World 2026"]
HMAC样本 = [
    ("", ""),
    ("密钥", "待签文本"),
    ("secret-key-中文", "hello hmac 2026"),
]


def _光串(s: str) -> str:
    assert '"' not in s and "\\" not in s, "样本含需转义字符：%r" % s
    return '"%s"' % s


def _期望值():
    out = []
    for s in 样本:
        out.append(base64.b64encode(s.encode("utf-8")).decode("ascii"))
    for s in 样本:
        b64 = base64.b64encode(s.encode("utf-8")).decode("ascii")
        out.append(base64.b64decode(b64).decode("utf-8"))
    for s in 样本:
        out.append(hashlib.md5(s.encode("utf-8")).hexdigest())
    for s in 样本:
        out.append(hashlib.sha1(s.encode("utf-8")).hexdigest())
    for s in 样本:
        out.append(hashlib.sha256(s.encode("utf-8")).hexdigest())
    for s in 样本:
        out.append(hashlib.sha512(s.encode("utf-8")).hexdigest())
    for 密钥, 文本 in HMAC样本:
        out.append(hashlib.pbkdf2_hmac(
            "sha256", 文本.encode("utf-8"), 密钥.encode("utf-8"), 1).hex())
    return out


def _程序文本():
    lines = [
        "从《Base64》导入《Base64编码》",
        "从《Base64》导入《Base64解码》",
        "从《哈希》导入《MD5》",
        "从《哈希》导入《SHA1》",
        "从《哈希》导入《SHA256》",
        "从《哈希》导入《SHA512》",
        "从《哈希》导入《HMAC_SHA256》",
    ]
    for s in 样本:
        lines.append("打印 Base64编码(%s)" % _光串(s))
    for s in 样本:
        b64 = base64.b64encode(s.encode("utf-8")).decode("ascii")
        lines.append("打印 Base64解码(%s)" % _光串(b64))
    for s in 样本:
        lines.append("打印 MD5(%s)" % _光串(s))
    for s in 样本:
        lines.append("打印 SHA1(%s)" % _光串(s))
    for s in 样本:
        lines.append("打印 SHA256(%s)" % _光串(s))
    for s in 样本:
        lines.append("打印 SHA512(%s)" % _光串(s))
    for 密钥, 文本 in HMAC样本:
        lines.append("打印 HMAC_SHA256(%s, %s)" % (_光串(密钥), _光串(文本)))
    return "\n".join(lines) + "\n"


def _跑_非LLVM(程序文本, 超时=240):
    """子进程走 cli/light.py run（src 后端 = 非 LLVM 解释执行链路）。"""
    源码路径 = None
    try:
        with tempfile.NamedTemporaryFile(
                "w", suffix=".light", dir=_ROOT, encoding="utf-8",
                delete=False, newline="\n") as fh:
            fh.write(程序文本)
            源码路径 = fh.name
        结果 = subprocess.run(
            [sys.executable, "cli/light.py", "run", os.path.basename(源码路径)],
            cwd=_ROOT, capture_output=True, text=True, timeout=超时)
        return 结果.returncode, 结果.stdout, 结果.stderr
    finally:
        if 源码路径 and os.path.isfile(源码路径):
            try:
                os.remove(源码路径)
            except OSError:
                pass


def test_非LLVM路径编码哈希与Python对拍():
    rc, out, err = _跑_非LLVM(_程序文本())
    assert rc == 0, "cli/light.py run 失败 rc=%d\nstderr:\n%s\nstdout:\n%s" % (
        rc, err, out)
    期望 = _期望值()
    # splitlines 保留首尾空行（空串样本的 Base64 编码/解码会打印空行），
    # 不能用 strip() —— 那会吞掉行首空行导致行数错位。
    实际 = out.splitlines()
    assert len(实际) == len(期望), (
        "输出行数不符：期望 %d 行、实际 %d 行\n期望:\n%s\n实际:\n%s"
        % (len(期望), len(实际), "\n".join(期望), out))
    for i, (got, want) in enumerate(zip(实际, 期望)):
        assert got == want, "第 %d 行对拍失败：期望 %s、实际 %s" % (i, want, got)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
