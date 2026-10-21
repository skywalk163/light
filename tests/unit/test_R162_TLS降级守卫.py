# -*- coding: utf-8 -*-
"""test_R162_TLS降级守卫.py —— 让「缺 cryptography 必须响亮降级」这条契约**常驻可跑**（L-234）

背景（L-234 立项依据）
--------------------
`tests/test_tls_light.py` 头注写明：缺 `cryptography` 时不许静默转绿，只留一条
`test_缺cryptography必须响亮降级` 打红代表整文件。但那条用例的定义包在
`if _缺cryptography is not None:` 里 —— **装上 cryptography 之后它就不存在了**
（`--collect-only` 只剩 3 条真 TLS 用例）。R161-E 在 0.82 装了 `cryptography 50.0.2`
之后实测确认：这条守卫**永久不跑**，契约没人守。

本文件用**子进程 + 依赖屏蔽**把「缺包」这件事模拟出来：临时目录放一个
`sitecustomize.py`，往 `sys.meta_path` 头部插一个 finder，凡 `cryptography*`
一律抛 `ImportError`，再用 `PYTHONPATH` 注入给子进程。于是**装了包的机器上**
也能真跑这条降级路径。

四条断言
--------
1. 屏蔽 + 无开关 ⇒ 子进程**恰好一条失败**，且名字 = `test_缺cryptography必须响亮降级`
   （是「响亮降级」，不是静默 skip、也不是收集错误）。
2. 屏蔽 + `LIGHT_ALLOW_SKIP_TLS_TEST=1` ⇒ 整文件 skip，**不红**（逃生口仍在）。
3. 不屏蔽 ⇒ 该文件正常收集 3 条 TLS 用例（证明「屏蔽」没把文件搞坏，
   也证明 1/2 的红/skip 真来自缺包，而非别的环境破坏）。
4. 有牙反跑：把 `test_tls_light.py` 里那条 `pytest.fail` 改成 `pass` ⇒
   断言 1 必须转红（否则本文件自己就是假门）。反跑由维护者手工执行，
   见文件末尾 `_反跑说明`。

不改动 `tests/test_tls_light.py`（B 线红线）。
"""

import os
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TLS文件 = os.path.join(_ROOT, 'tests', 'test_tls_light.py')
_红用例名 = "test_缺cryptography必须响亮降级"

_子进程环境 = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}

_SITECUSTOMIZE = '''# R162 B 线：模拟「本机缺 cryptography」——屏蔽 cryptography* 的一切导入。
import sys


class _屏蔽cryptography:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'cryptography' or fullname.startswith('cryptography.'):
            raise ImportError('R162 守卫模拟：cryptography 被屏蔽（%s）' % fullname)
        return None


sys.meta_path.insert(0, _屏蔽cryptography())
'''


def _屏蔽目录():
    """生成一个含 sitecustomize.py 的临时目录（调用方负责清理）。"""
    d = tempfile.mkdtemp(prefix='_r162_shield_')
    with open(os.path.join(d, 'sitecustomize.py'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(_SITECUSTOMIZE)
    return d


def _跑pytest(参数, 屏蔽=False, 额外环境=None, 超时=180):
    """子进程跑一次 pytest，返回 (rc, stdout)。"""
    env = dict(_子进程环境)
    if 屏蔽:
        d = _屏蔽目录()
        env['PYTHONPATH'] = d + os.pathsep + env.get('PYTHONPATH', '')
    else:
        d = None
        env.pop('LIGHT_ALLOW_SKIP_TLS_TEST', None)
    if 额外环境:
        env.update(额外环境)
    try:
        r = subprocess.run(
            [sys.executable, '-m', 'pytest', *参数],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=超时, cwd=_ROOT, env=env,
        )
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    finally:
        if d:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


def _失败行(out):
    return [l.strip() for l in out.splitlines() if l.strip().startswith('FAILED ')]


def _失败用例名(失败行):
    """`FAILED tests/x.py::用例名 - Failed: 摘要` → 用例名（去掉 `- 摘要` 尾巴）。"""
    尾 = 失败行.split('::')[-1]
    return 尾.split(' - ')[0].strip()


# ═══════════════════════════════════════════════════════════════════════════
# 1 · 缺包 → 恰好一条响亮红
# ═══════════════════════════════════════════════════════════════════════════

def test_缺cryptography时_恰好一条响亮降级红():
    """屏蔽 cryptography ⇒ 子进程恰好 1 failed，且就是 `test_缺cryptography必须响亮降级`。

    这条是 L-234 的本体：装了 cryptography 的机器上，原文件里那条守卫**不存在**，
    靠本文件把契约重新跑起来。
    """
    rc, out = _跑pytest([os.path.relpath(_TLS文件, _ROOT), '-q', '--tb=no',
                         '-p', 'no:cacheprovider', '-p', 'no:randomly'],
                        屏蔽=True)
    失败 = _失败行(out)
    assert len(失败) == 1, (
        f"缺 cryptography 时应恰好一条红（响亮降级），实得 {len(失败)} 条：{失败}\n"
        f"--- 子进程输出 ---\n{out[-1500:]}")
    assert _失败用例名(失败[0]) == _红用例名, (
        f"红的必须是 {_红用例名}，实得 {失败[0]}")
    assert rc != 0, "缺依赖时应是非零退出码（进 junit、被回归闸门拦下）"


# ═══════════════════════════════════════════════════════════════════════════
# 2 · 逃生口：显式开关 ⇒ 整文件 skip，不红
# ═══════════════════════════════════════════════════════════════════════════

def test_缺cryptography且显式放行时_整文件skip不红():
    """屏蔽 + `LIGHT_ALLOW_SKIP_TLS_TEST=1` ⇒ 整文件 skip（人为放行），不得红、不得 error。"""
    rc, out = _跑pytest([os.path.relpath(_TLS文件, _ROOT), '-q', '--tb=no', '-rs',
                         '-p', 'no:cacheprovider', '-p', 'no:randomly'],
                        屏蔽=True,
                        额外环境={'LIGHT_ALLOW_SKIP_TLS_TEST': '1'})
    # 整文件 skip ⇒ pytest 一条都没跑 ⇒ EXIT_NOTESTS(5)；某些版本给 0。两者都不是红，
    # 而 1(failed)/2(interrupted)/3(internal)/4(usage) 才是要拦的形态。
    assert rc in (0, 5), (
        f"显式放行后应是 skip（5=EXIT_NOTESTS 或 0），不得是失败/中断码，实得 rc={rc}\n"
        f"--- 输出 ---\n{out[-1500:]}")
    assert not _失败行(out), f"显式放行后不应有 FAILED：{_失败行(out)}"
    # 放行理由必须出现在 skip 原因里（防「静默 skip 而没写理由」）
    assert 'LIGHT_ALLOW_SKIP_TLS_TEST' in out, (
        "整文件 skip 的理由里必须写明是显式放行（LIGHT_ALLOW_SKIP_TLS_TEST），"
        f"实得输出尾部：\n{out[-800:]}")


# ═══════════════════════════════════════════════════════════════════════════
# 3 · 反向对照：不屏蔽时文件正常收集
# ═══════════════════════════════════════════════════════════════════════════

def test_不屏蔽时_文件正常收集三条TLS用例():
    """对照：不屏蔽 cryptography ⇒ 该文件正常收集 3 条 TLS 用例。

    证明「屏蔽」只挡了 cryptography，没把文件搞坏 —— 于是 1/2 的红/skip
    确实归因于缺包。
    """
    try:
        import cryptography  # noqa: F401
    except ImportError:
        pytest.skip('本机本就缺 cryptography：反向对照（装包态）在此机器上无意义，'
                    '此时 test_tls_light.py 的降级路径本就在跑')
    rc, out = _跑pytest([os.path.relpath(_TLS文件, _ROOT), '--collect-only', '-q',
                         '-p', 'no:cacheprovider', '-p', 'no:randomly'],
                        屏蔽=False, 超时=120)
    assert rc == 0, f"不屏蔽时应能正常收集，rc={rc}\n--- 输出 ---\n{out[-1200:]}"
    收集 = [l for l in out.splitlines() if '::' in l]
    assert len(收集) == 3, f"装包态应收集 3 条 TLS 用例，实得 {len(收集)} 条：{收集}"
    assert all(_红用例名 not in l for l in 收集), (
        f"装包态不应出现降级用例（它只在缺包时定义），实得：{收集}")


# ═══════════════════════════════════════════════════════════════════════════
# 反跑说明（手工执行，不写成没跑过的断言）
# ═══════════════════════════════════════════════════════════════════════════

_反跑说明 = """
反跑锚点（证明本文件自身不是假门）：

1. 把 `tests/test_tls_light.py` 里 `test_缺cryptography必须响亮降级` 的
   `pytest.fail(...)` 改成 `pass` ⇒ `test_缺cryptography时_恰好一条响亮降级红`
   必须转红（子进程 0 failed，断言 `len(失败) == 1` 不成立）。改回即复原。
2. 把 `tests/test_tls_light.py` 头注的逃生口判断
   `os.environ.get("LIGHT_ALLOW_SKIP_TLS_TEST") == "1"` 改成恒假 ⇒
   `test_缺cryptography且显式放行时_整文件skip不红` 必须转红（放行失效 ⇒ 仍红）。
3. 屏蔽范围写窄（只挡 `cryptography` 不挡 `cryptography.*`）⇒ 三条真 TLS 用例
   会以别的形态失败，第 1 条断言的「恰好一条红」会转红。
"""
