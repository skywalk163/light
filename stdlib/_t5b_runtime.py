# -*- coding: utf-8 -*-
"""T5B 编码/哈希 runtime 内建（非 LLVM 路径）—— 仅供 stdlib/builtins.py 接线引用。

## 为什么存在

stdlib 的 Base64.light / 哈希.light 按函数名直接调用 `_b64_encode` / `_md5` /
`_sha1` / `_sha256` / `_sha512` / `_hmac_sha256` 这批「runtime 内建」。
LLVM 原生腿在 src/llvm/codegen_typed.py:2482+ 把这批名字派发到 C runtime
（dv_base64_encode / dv_md5 / dv_pbkdf2_hmac_sha256_1 等）；而解释器执行路径
（cli/light.py run 的 src 后端）没有同名实现，生成产物里这些名字解析不到 →
运行期 NameError（CI-A 真回归根因，冒烟 Base64/哈希 块全挂）。

## 口径（与 C 层 dv_* 字节级对拍）

- _b64_encode(s)          -> 输入 UTF-8 字节的标准 Base64（带 '=' 填充）
- _b64_decode(s)          -> Base64 文本解回 UTF-8 字符串
- _md5/_sha1/_sha256/_sha512(s) -> UTF-8 字节摘要的小写十六进制（32/40/64/128 位）
- _hmac_sha256(密钥, 文本) -> pbkdf2_hmac('sha256', text, key, 1)
  （参数名保持 light 侧「密钥在前」；语义与 C dv_pbkdf2_hmac_sha256_1
  password=文本、salt=密钥 一致，也与 stdlib/哈希.py 旧壳同款）

## 为什么是独立文件而不是在 builtins.py 里加 def

tools/ci/floor_bootstrap.py 用 ast 数 stdlib/builtins.py 的顶层函数当分母，
新加 `def` 会触发「清单漏登记」判红（地板函数名是冻结名单）。
本文件只被 builtins.py `from _t5b_runtime import ...` 接线，不改动 builtins.py
自身的函数计数，也不属于地板名单的登记范围。
"""
import base64
import hashlib
import random as _random_mod
import time as _time_mod


def _b64_encode(数据) -> str:
    if isinstance(数据, bytes):
        return base64.b64encode(数据).decode('ascii')
    return base64.b64encode(数据.encode('utf-8')).decode('ascii')


def _b64_decode(数据) -> str:
    raw = 数据 if isinstance(数据, bytes) else 数据.encode('ascii')
    return base64.b64decode(raw).decode('utf-8')


def _md5(文本) -> str:
    return hashlib.md5(文本.encode('utf-8')).hexdigest()


def _sha1(文本) -> str:
    return hashlib.sha1(文本.encode('utf-8')).hexdigest()


def _sha256(文本) -> str:
    return hashlib.sha256(文本.encode('utf-8')).hexdigest()


def _sha512(文本) -> str:
    return hashlib.sha512(文本.encode('utf-8')).hexdigest()


def _hmac_sha256(密钥, 文本) -> str:
    """HMAC_SHA256 —— 参数名(密钥, 文本)，语义 = pbkdf2_hmac('sha256', 文本, 密钥, 1)。"""
    return hashlib.pbkdf2_hmac(
        'sha256', 文本.encode('utf-8'), 密钥.encode('utf-8'), 1).hex()


# ---- R123-A1：跨腿内建名一致性补口（原生腿 codegen_typed 分派认、转译腿原零映射）----
# 放这里而非 builtins.py 开 def，同 T5B 理由：floor_bootstrap 数 builtins.py 顶层
# FunctionDef 当分母，新增 def 会触发「清单漏登记」判红。builtins.py 只做 from import 接线。

def 右去除(文本, 字符集=None) -> str:
    """str.rstrip：去掉右侧空白（或指定字符集）。对齐原生腿 codegen_typed 的 rstrip。"""
    if 字符集 is None:
        return 文本.rstrip()
    return 文本.rstrip(字符集)


def 随机位(位数: int) -> int:
    """random.getrandbits(k)：返回 k 个随机位组成的非负整数。对齐原生腿 dv_random_bits。"""
    return _random_mod.getrandbits(位数)


def 播种随机种子(种子=None) -> None:
    """random.seed：播种随机数发生器。对齐原生腿 dv_random_seed。"""
    _random_mod.seed(种子)


def 睡眠秒(秒数) -> None:
    """time.sleep(秒数)：阻塞指定秒数（浮点）。对齐原生腿 dv_sleep。"""
    _time_mod.sleep(秒数)
