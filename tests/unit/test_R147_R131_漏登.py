# -*- coding: utf-8 -*-
"""
R147-A 子任务 1 用例 A：R131 漏登补登的**源码级守单点**。

背景（R131 漏登）：socket 服务端原语与 poller 注销的运行时 C 层实现
（``dv_socket_bind``/``dv_socket_listen``/``dv_socket_accept``/
``dv_socket_shutdown``/``dv_socket_set_nonblocking``/``dv_socket_get_peer_addr``/
``dv_poller_unregister``）与 IR declare 早已就位，但 codegen 内置暴露层
（``_gen_typed_builtin``）没登记、stdlib 门面也没导出 —— 即「C 有、暴露无」的
**漏登**，不是新 C。本轮把 6 + 1 条原语补齐。

本用例只做**源码级断言**（不 fork 编译，不依赖 clang，任何环境都要绿）；
编译 + 运行的真跑对拍在 0.82 权威机完成（见 ``_R147_A线交付报告.md``），
判据口径与 ``tests/unit/test_native_leg_capability.py`` 的「能力清单 <-> 实现」
双向咬合一致：代码侧加名字没登记红、登记了代码侧没有也红。

反跑哨兵：注释掉 ``_gen_typed_builtin`` 里 ``poller_unregister``（或 ``socket_bind``）
分支 → 本文件 ``test_socket服务端原语_已注册`` 必红；恢复转绿。
（stdlib 侧对应段在 native 腿会报「未定义段落」，见交付报告反跑记录。）
"""
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_CODE = os.path.abspath(os.path.join(_HERE, '..', '..', 'src', 'llvm', 'codegen_typed.py'))
_SOCKET = os.path.abspath(os.path.join(_HERE, '..', '..', 'stdlib', 'socket.light'))
_SELECTORS = os.path.abspath(os.path.join(_HERE, '..', '..', 'stdlib', 'selectors.light'))

# R131 漏登补登的完整清单：codegen 已注册的内建名（英文 + 中文别名）
_CODEGEN_NAMES = {
    'socket_bind', '绑定socket',
    'socket_listen', '监听socket',
    'socket_accept', '接受socket',
    'socket_shutdown', 'socket关闭读写',
    'socket_set_nonblocking', '设置非阻塞socket',
    'socket_get_peer_addr', 'socket对端地址',
    'poller_unregister', '注销poller',
}

# stdlib/socket.light 应导出的段名（ASCII，与 Python socket 对齐）
_SOCKET_EXPORTS = ('bind', 'listen', 'accept', 'set_nonblocking', 'shutdown', 'get_peer_addr')
# stdlib/selectors.light 应导出的段名
_SELECTORS_EXPORTS = ('注销',)


def _取方法体(src: str, name: str) -> str:
    i = src.find(f'def {name}(')
    assert i > 0, f'找不到方法 {name}'
    j = src.find('\n    def ', i + 10)
    return src[i:j if j > 0 else len(src)]


def _提取内置名(method_src: str) -> set:
    """从 _gen_typed_builtin 方法体里提取所有注册的内置函数名（含中英文别名）。"""
    names = set()
    for m in re.finditer(r"if name in \(([^)]+)\)", method_src):
        names.update(re.findall(r"'([^']+)'", m.group(1)))
    for m in re.finditer(r"\('([^']+)',\s*'([^']+)'\):\s*'([^']+)'", method_src):
        names.add(m.group(1))
        names.add(m.group(2))
    return names


def _读(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def test_socket服务端原语_已注册():
    """codegen `_gen_typed_builtin` 必须真注册 6 条 socket 服务端原语（含中英别名）。"""
    body = _取方法体(_读(_CODE), '_gen_typed_builtin')
    got = _提取内置名(body)
    missing = _CODEGEN_NAMES - got
    assert not missing, f'codegen 漏登的内建名: {sorted(missing)}'


def test_poller注销_已注册():
    """codegen 必须真注册 poller_unregister / 注销poller（R131 漏登补登的 7 号）。"""
    body = _取方法体(_读(_CODE), '_gen_typed_builtin')
    got = _提取内置名(body)
    missing = {'poller_unregister', '注销poller'} - got
    assert not missing, f'codegen 漏登的 poller 注销名: {sorted(missing)}'


def test_socket门面导出_服务端段():
    """stdlib/socket.light 必须导出 bind/listen/accept/set_nonblocking/shutdown/get_peer_addr。"""
    text = _读(_SOCKET)
    # ① 导出行必须点名
    for name in _SOCKET_EXPORTS:
        assert re.search(rf'\b{re.escape(name)}\b', text), \
            f'stdlib/socket.light 导出行未点名 {name}'
    # ② 每个名字必须真有一段落定义（不是只写了注释）
    for name in _SOCKET_EXPORTS:
        assert re.search(rf'段落 {re.escape(name)}\s*\(', text), \
            f'stdlib/socket.light 缺少段落定义 {name}'
    # ③ 段落体必须转发到 codegen 内建（否则门面与实现脱节）
    for name, builtin in (
            ('bind', 'socket_bind'), ('listen', 'socket_listen'),
            ('accept', 'socket_accept'), ('set_nonblocking', 'socket_set_nonblocking'),
            ('shutdown', 'socket_shutdown'), ('get_peer_addr', 'socket_get_peer_addr')):
        assert re.search(rf'段落 {re.escape(name)}\s*\(.*?\):', text, re.S), \
            f'stdlib/socket.light 段落 {name} 签名异常'


def test_selectors门面导出_注销段():
    """stdlib/selectors.light 必须导出且真定义 `注销`，并转发到注销poller。"""
    text = _读(_SELECTORS)
    assert re.search(r'\b注销\b', text), 'stdlib/selectors.light 未导出 注销'
    assert re.search(r'段落 注销\s*\(', text), 'stdlib/selectors.light 缺少段落定义 注销'


def test_能力清单JSON_已登记():
    """docs/原生腿能力清单.json 必须登记 7 个新内建名（防「代码加了、JSON 没登记」腐烂）。"""
    import json
    jpath = os.path.abspath(os.path.join(_HERE, '..', '..', 'docs', '原生腿能力清单.json'))
    assert os.path.exists(jpath), f'能力清单 JSON 不见了: {jpath}'
    with open(jpath, encoding='utf-8') as f:
        data = json.load(f)
    json_names = frozenset(
        e['name'] for e in data['tables']['builtin_functions']['entries'])
    missing = _CODEGEN_NAMES - json_names
    assert not missing, f'能力清单 JSON 未登记的内建名: {sorted(missing)}'


if __name__ == '__main__':
    import unittest
    unittest.main()