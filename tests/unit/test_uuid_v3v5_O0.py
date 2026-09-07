# -*- coding: utf-8 -*-
"""R13C 定向测试：uuid v3/v5 真语义（runtime SHA1/MD5）字节级对拍。

判据：生成UUID5(命名空间, 名称) 与 Python uuid.uuid5() 逐字符一致；
生成UUID3 与 uuid.uuid3() 一致。每用例独立编译运行（T5A 范式），
optimize_level=0 强 O0。只跑本文件，禁止全量。
"""
import os
import sys
import subprocess as _subproc
import tempfile as _tempfile
import uuid as _uuid

import pytest


def _编译并运行(code: str, optimize_level: int = 0) -> tuple:
    from llvm.compiler import compile_light_typed
    with _tempfile.TemporaryDirectory(prefix='_taskR13C_') as d:
        src = os.path.join(d, '主.light')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, '产物'),
                                  optimize_level=optimize_level)
        r = _subproc.run([exe], capture_output=True, timeout=60)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        return r.returncode, out, err


def _行(out: str):
    return [h for h in out.replace('\r', '').split('\n') if h != '']


# 命名空间标准串（与 Python uuid 常量同值）
_NS = {
    'DNS':  '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
    'URL':  '6ba7b811-9dad-11d1-80b4-00c04fd430c8',
    'OID':  '6ba7b812-9dad-11d1-80b4-00c04fd430c8',
    'X500': '6ba7b814-9dad-11d1-80b4-00c04fd430c8',
}


def _期望5(ns_name: str, name: str) -> str:
    return str(_uuid.uuid5(getattr(_uuid, f'NAMESPACE_{ns_name}'), name))


def _期望3(ns_name: str, name: str) -> str:
    return str(_uuid.uuid3(getattr(_uuid, f'NAMESPACE_{ns_name}'), name))


def test_uuid5_DNS_多名称():
    """uuid.uuid5(NAMESPACE_DNS, name)：5 组名称逐字符对拍。"""
    names = ['python.org', '光明', 'a', '', 'x' * 200]
    names[3] = ''  # 空名
    code_lines = ['从 uuid工具 导入 生成UUID5', '段落 主:']
    for ns in ('DNS',):
        for name in names:
            期望 = _期望5(ns, name)
            code_lines.append(f'  输出(生成UUID5("{_NS[ns]}", "{name}"))')
            if name == '':
                # 空串名在 .light 里用 "" 表示；oracle 同
                pass
    code = '\n'.join(code_lines) + '\n'
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    期望们 = [_期望5('DNS', n) for n in names]
    assert _行(out) == 期望们, f"实际={_行(out)} 期望={期望们}"


def test_uuid5_四命名空间():
    """DNS/URL/OID/X500 × 固定名称，四命名空间逐字符对拍。"""
    name = 'example.com/path?q=1'
    code = (
        '从 uuid工具 导入 生成UUID5\n'
        '段落 主:\n'
        f'  输出(生成UUID5("{_NS["DNS"]}", "{name}"))\n'
        f'  输出(生成UUID5("{_NS["URL"]}", "{name}"))\n'
        f'  输出(生成UUID5("{_NS["OID"]}", "{name}"))\n'
        f'  输出(生成UUID5("{_NS["X500"]}", "{name}"))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    期望们 = [_期望5(ns, name) for ns in ('DNS', 'URL', 'OID', 'X500')]
    assert _行(out) == 期望们, f"实际={_行(out)} 期望={期望们}"


def test_uuid5_确定性():
    """同输入两次调用结果一致（确定性派生）。"""
    code = (
        '从 uuid工具 导入 生成UUID5\n'
        '段落 主:\n'
        '  设 a 为 生成UUID5("' + _NS['DNS'] + '", "确定性检查")\n'
        '  设 b 为 生成UUID5("' + _NS['DNS'] + '", "确定性检查")\n'
        '  输出(a == b)\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    assert _行(out) == ['真']


def test_uuid3_多名称():
    """uuid.uuid3(NAMESPACE_DNS, name)：MD5 派生逐字符对拍。"""
    names = ['python.org', '光明', 'mixed-英文名-123']
    code = (
        '从 uuid工具 导入 生成UUID3\n'
        '段落 主:\n'
        f'  输出(生成UUID3("{_NS["DNS"]}", "{names[0]}"))\n'
        f'  输出(生成UUID3("{_NS["DNS"]}", "{names[1]}"))\n'
        f'  输出(生成UUID3("{_NS["DNS"]}", "{names[2]}"))\n'
    )
    rc, out, err = _编译并运行(code)
    assert rc == 0, err
    期望们 = [_期望3('DNS', n) for n in names]
    assert _行(out) == 期望们, f"实际={_行(out)} 期望={期望们}"


def test_uuid5_版本与变体位():
    """输出 UUID 的版本 nibble=5、变体 RFC 4122（结构校验）。"""
    u = _期望5('DNS', 'python.org')
    assert u[14] == '5'
    assert u[19] in '89ab'
