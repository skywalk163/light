# -*- coding: utf-8 -*-
"""链接库参数护栏：测试里不许自己硬编码平台相关的 `-l` 库。

## 这条护栏钉的是什么

gitea runner 是 FreeBSD 14 + clang。run #63/#64 上整条 clang 腿全红，两层原因：

1. `tests/test_llvm_net.py` / `test_llvm_c_unit.py` / `test_llvm_tls.py` 无条件塞
   `-lws2_32 -lsecur32 -lcrypt32` → FreeBSD 上 `unable to find library -lws2_32`。
2. `tests/test_llvm_optimizer.py` / `test_p3_comprehensive.py` / `test_llvm_async.py`
   / `test_llvm_exception.py` 什么库都不加 → 非 Windows 上 libm 不自动链，
   `undefined symbol: sin/cos/pow/floor/ceil/fmod/tan`。

而**生产代码一直是对的**（`src/llvm/compiler.py` 的 `get_link_libs()` 有平台分支）。
也就是说这批红不是能力缺失，纯粹是测试各自抄了一份判据、抄错了。这些用例又都命中
`--soft-classname` 只报不拦，所以在闸门上一直是「非阻塞」，谁也没去看。

修法是让判据只有一处：测试统一调 `tests/llvm运行时.py` 的 `取链接库参数()`，
它直接转调生产的 `get_link_libs()`。这条护栏保证以后没人再抄第二份。

## 为什么用源码级断言而不是真跑

「Windows 上全绿、FreeBSD 上全红」这种红，在本机无论怎么跑都复现不出来——只有
推上 CI 才看得见，一个来回 8 分钟。所以改成源码级断言守单点：谁再在测试里写
`'-lws2_32'` 或 `'-lm'` 字面量，本机立刻红。

用 AST 取字符串字面量而不是正则搜文本，是因为注释和文档字符串里合法地写着这些
库名（本文件自己就是），正则会当场自我误报。
"""

import ast
import sys
from pathlib import Path

_仓根 = Path(__file__).resolve().parents[2]
_测试根 = _仓根 / 'tests'
_本文件 = Path(__file__).resolve()

# 收集面与 test_capture_encoding_guard.py 一致：对齐 pyproject 的 pytest 配置。
_排除目录 = {'archive', '__pycache__'}

# 平台相关的链接库字面量。只管 `-l<lib>` 形式：
# MSVC 分支里的 'ws2_32.lib'（写在 .bat 内容的 f-string 里）不在此列——那条腿由
# `HAS_MSVC` 守着，本身就只可能在 Windows 上执行，不存在跨平台误用。
_禁止字面量 = {'-lws2_32', '-lsecur32', '-lcrypt32', '-lm'}


def _收集():
    出 = set()
    for 模式 in ('test_*.py', '_test_*.py', 'conftest.py', 'llvm运行时.py'):
        for p in _测试根.rglob(模式):
            if _排除目录 & set(p.relative_to(_测试根).parts[:-1]):
                continue
            if p.resolve() == _本文件:
                # 本文件自己必须写出这些字面量：既要在 _禁止字面量 里声明判据，
                # 也要在反跑用例里造反例。第一版没排掉自己，跑起来当场自我误报。
                continue
            出.add(p)
    return sorted(出)


_被收集 = _收集()


def _查违规(源码: str):
    """返回 [(行号, 字面量)]：源码里出现的平台相关 -l 库字符串字面量。"""
    结果 = []
    树 = ast.parse(源码)
    for 节点 in ast.walk(树):
        if isinstance(节点, ast.Constant) and isinstance(节点.value, str):
            if 节点.value in _禁止字面量:
                结果.append((节点.lineno, 节点.value))
    return sorted(结果)


def test_测试里不许硬编码平台链接库():
    违规 = []
    读不了 = []
    for p in _被收集:
        名 = p.relative_to(_仓根).as_posix()
        try:
            命中 = _查违规(p.read_text(encoding='utf-8', errors='replace'))
        except SyntaxError as e:
            读不了.append(f'{名}:{e.lineno} {e.msg}')
            continue
        for 行号, 字面量 in 命中:
            违规.append(f'{名}:{行号} {字面量}')
    assert not 读不了, (
        '这些被收集的模块 ast 解析不了，护栏看不见它们：\n  ' + '\n  '.join(读不了))
    assert not 违规, (
        '这些地方自己硬编码了平台相关的链接库，换平台必红；'
        '请改调 tests/llvm运行时.py 的 取链接库参数()：\n  ' + '\n  '.join(违规))


def test_取链接库参数就是生产的判据():
    """测试用的 helper 必须与生产 compiler.py 返回同一份结果，不许是平行实现。"""
    sys.path.insert(0, str(_测试根))
    from llvm运行时 import 取链接库参数
    from llvm.compiler import get_link_libs
    assert 取链接库参数() == list(get_link_libs())


def test_两个平台的库清单都不为空():
    """反跑：任何平台都得给出非空清单，别退化成「什么都不加」——那正是缺 -lm 那批红。"""
    from llvm.compiler import get_link_libs
    库 = get_link_libs()
    assert 库, '当前平台拿到空的链接库清单'
    assert all(x.startswith('-l') for x in 库), 库
    if sys.platform == 'win32':
        assert '-lws2_32' in 库, 库
    else:
        assert '-lm' in 库, 库


def test_护栏能抓到反例():
    """反跑：确认上面那条不是永真断言。"""
    坏 = "cmd = [clang, '-o', exe, src, '-lws2_32', '-lm']\n"
    好 = "cmd = [clang, '-o', exe, src, *取链接库参数()]\n"
    注释里出现 = "# 历史上这里写的是 -lws2_32 -lm\ncmd = [clang]\n"
    assert _查违规(坏) == [(1, '-lm'), (1, '-lws2_32')], _查违规(坏)
    assert _查违规(好) == []
    assert _查违规(注释里出现) == [], '把注释里的库名也算成了调用'


def test_收集面不为空():
    assert len(_被收集) > 50, f'只找到 {len(_被收集)} 个被收集模块，路径大概率错了'
