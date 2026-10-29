# -*- coding: utf-8 -*-
"""
LH-15（T-0202，P2）：socket 常量整组透出验收。

背景
----
旧版 ``stdlib/socket.light`` 只导出 6 个常量（AF_INET/AF_INET6/SOCK_STREAM/
SOCK_DGRAM/SOL_SOCKET/SO_REUSEADDR），``SO_REUSEPORT`` / ``TCP_NODELAY`` 拿不到。
本卡要求整组透出，并对平台差异诚实：

- 原生腿 ``stdlib/socket.light``：补导出 + 零参取值段（POSIX/Linux 规范字面量，
  门面语义；跨平台真值以 Python 腿为准）。
- Python 腿 ``stdlib/Socket.py``：用 ``getattr(socket, 名, None)`` 动态取真值，
  绝不写死数字；平台不存在的常量（Windows 的 SO_REUSEPORT）返回 ``空(None)``，
  绝不静默返回 0。

本文件四条验收（对齐任务卡）：
1. ``从 socket 导入 SO_REUSEPORT, TCP_NODELAY, IPPROTO_TCP`` 编译通过；
2. 取值与宿主 Python 对拍（不写死数字）；
3. SO_REUSEPORT 在支持平台上能真用（双绑同一端口，第二个绑定成功），
   不支持的平台 skip 并打印原因；
4. 取不到的常量返回 空/可读异常，而不是 0（负向用例）。
"""
import os
import re
import socket as _py_socket

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOCKET_LIGHT = os.path.abspath(os.path.join(_HERE, '..', '..', 'stdlib', 'socket.light'))
_SOCKET_PY = os.path.abspath(os.path.join(_HERE, '..', '..', 'stdlib', 'Socket.py'))

# 本卡要求整组透出的常量（原生腿 socket.light 导出行 + 零参取值段都必须有）
_REQUIRED_CONSTS = (
    'SOL_SOCKET', 'SO_REUSEADDR', 'SO_REUSEPORT', 'SO_KEEPALIVE', 'SO_BROADCAST',
    'TCP_NODELAY', 'IPPROTO_IP', 'IPPROTO_TCP', 'IPPROTO_UDP',
)


def _read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def test_light导入三常量_编译通过():
    """验收 1：`从 socket 导入 SO_REUSEPORT, TCP_NODELAY, IPPROTO_TCP` 编译不炸。"""
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    src = '从 socket 导入 SO_REUSEPORT, TCP_NODELAY, IPPROTO_TCP\n'
    ast = LightParser().parse(src)
    out = PythonCodeGenerator().generate(ast)
    # 编译产物里必须真的把三个名字带进导入语句（不是被悄悄丢弃）
    for name in ('SO_REUSEPORT', 'TCP_NODELAY', 'IPPROTO_TCP'):
        assert re.search(rf'\b{name}\b', out), f'编译产物未包含 {name}'


def test_socketlight_导出与零参段齐备():
    """验收 1 的原生腿面：socket.light 导出行点名 + 真有零参取值段。"""
    text = _read(_SOCKET_LIGHT)
    for name in _REQUIRED_CONSTS:
        # 导出行必须点名（出现 \b名字\b）
        assert re.search(rf'\b{re.escape(name)}\b', text), \
            f'stdlib/socket.light 未导出常量 {name}'
        # 必须真有 `段落 名字():` 定义（不是只写在注释里）
        assert re.search(rf'段落 {re.escape(name)}\s*\(', text), \
            f'stdlib/socket.light 缺少零参取值段 {name}'


def test_python腿常量_与宿主对拍():
    """验收 2：Python 腿 facade 的常量 == 宿主 socket 真值（不写死数字）。"""
    import Socket as _facade
    assert _facade.SO_REUSEADDR == _py_socket.SO_REUSEADDR
    assert _facade.TCP_NODELAY == _py_socket.TCP_NODELAY
    assert _facade.IPPROTO_TCP == _py_socket.IPPROTO_TCP
    assert _facade.IPPROTO_UDP == _py_socket.IPPROTO_UDP
    assert _facade.IPPROTO_IP == _py_socket.IPPROTO_IP
    assert _facade.SOL_SOCKET == _py_socket.SOL_SOCKET


def test_缺失常量_返回空而非0():
    """验收 4：平台不存在的常量必须是 空(None)，而不是误导性的 0。"""
    import Socket as _facade
    has_reuseport = hasattr(_py_socket, 'SO_REUSEPORT')
    if has_reuseport:
        # 支持平台：值等于真值，且绝不是 0
        assert _facade.SO_REUSEPORT == _py_socket.SO_REUSEPORT
        assert _facade.SO_REUSEPORT != 0
    else:
        # 不支持平台（如 Windows）：必须是 None（空），不是 0
        print(f'本平台({_py_socket.gethostname()})无 SO_REUSEPORT，facade 返回空(None)')
        assert _facade.SO_REUSEPORT is None


def test_soreuseport_双绑同一端口():
    """验收 3：SO_REUSEPORT 在支持平台上能真用——两个 socket 绑定同一端口，第二个成功。

    不支持的平台（Windows 无 SO_REUSEPORT）直接 skip 并打印原因。
    """
    val = getattr(_py_socket, 'SO_REUSEPORT', None)
    if val is None:
        pytest.skip('本平台无 SO_REUSEPORT（如 Windows），跳过双绑真用')

    s1 = _py_socket.socket(_py_socket.AF_INET, _py_socket.SOCK_STREAM)
    s2 = _py_socket.socket(_py_socket.AF_INET, _py_socket.SOCK_STREAM)
    try:
        s1.setsockopt(_py_socket.SOL_SOCKET, _py_socket.SO_REUSEPORT, 1)
        s2.setsockopt(_py_socket.SOL_SOCKET, _py_socket.SO_REUSEPORT, 1)
        s1.bind(('127.0.0.1', 0))
        chosen_port = s1.getsockname()[1]
        # 关键断言：第二个 socket 复用同一端口绑定成功
        s2.bind(('127.0.0.1', chosen_port))
    finally:
        s1.close()
        s2.close()


if __name__ == '__main__':
    import unittest
    unittest.main()
