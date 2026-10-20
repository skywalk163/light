# -*- coding: utf-8 -*-
"""R159-D · E-3（R157-E3）：两腿布尔 repr 收敛——容器内 `真/假` → `true/false`。

背景
----
L-193 / R152-E2 裁定：**native 容器内布尔元素**的 repr 对齐 src（`[true, false]`），
**标量保持中文**（`转字符串(真)` 仍是 `真`）。分歧边界：仅容器内布尔；标量两腿已一致（中文）。

病灶（修前实测，本机 Windows O0）：
- 修前 native：`转字符串([真, 假])` → `[真, 假]`；`转字符串({"k": 真})` → `{'k': 真}`
- 修前 src：  `转字符串([真, 假])` → `[true, false]`；`转字符串({"k": 真})` → `{"k": true}`
- 病灶根因：`src/llvm/runtime_typed.c:743` `case 5` 恒返中文（不区分 depth）。
- **任务书病灶分析未覆盖的实证**：`转字符串(列表)` 在 native 走 **`dv_list_join`**
  （`src/llvm/codegen_typed.py:3349`），**不经** `dv_container_to_string`；只改 `case 5`
  （字典路径 depth>=1）**不会**让 `转字符串([真, 假])` 主判据收敛。本文件把两处都钉死。

本文件做什么 / 不做什么
-----------------------
* **做**：
  1. 双腿对拍 `转字符串([真, 假])` == `[true, false]`（主判据，走 dv_list_join）；
  2. 字典容器（走 dv_container_to_string）：`转字符串({"k": 真})` == `{"k": true}`；
  3. 嵌套容器：`转字符串({"k": [真, 假]})` == `{"k": [true, false]}`；
  4. **标量不受影响**：`转字符串(真)` == `真`；`转字符串(假)` == `假`；
  5. **JSON 独立性**：`序列化JSON([真, 假])` 走 `dv_json_serialize_value` 独立路径，
     修前即输出合法 `[true, false]`，**不受本改动影响**（记录现状）；
  6. **反跑有牙**：临时把 `case 5` 改回 depth 不敏感 → 容器分歧复现转红（用子进程读源码
     打补丁再恢复，跑完不留痕）。
* **不做**：
  - 不改 `.light` / runtime 里的归一化（R152-E2 裁定明文：归一化只能在测试断言侧做且显式登记）；
  - 不做「两边都接受」的宽容断言（假绿）；
  - 不跑 0.82 全量门（由主 agent 与 A 线同一次跑）。

已知不等价（本线登记，不修）
---------------------------
`连接字符串([真, 假], ",")`：src 腿抛 TypeError（`sequence item 0: expected str instance,
bool found`，见 `stdlib/字符串工具轻量.light`），native 走 `dv_list_join` 静默拼接。这是
`连接字符串` 语义（`str.join` 收严）的另一条分歧，**非本线 repr 范围**，登记交主 agent。

路径
----
用 `sys.path.insert`（对齐 `tests/conftest.py`）；native 腿用 `compile_light_typed` 编译运行，
src 腿用 `python -m cli.light_unified run`。
"""

import os
import sys
import subprocess
import tempfile

import pytest

# R161-B 实测暴露的测试隔离缺陷（非本文件逻辑问题）：
# 本文件的反跑用例会**临时改写 src/llvm/runtime_typed.c** 再还原。在 pytest-xdist
# 并行模式下，别的 worker 可能恰好在改写窗口内读该文件或调 clang 编译，于是
# 出现「单跑绿、全量跑红」的假红（实测：全量 60 failed 里唯一新增就是本文件）。
# 用 xdist 的串行分组把它钉在同一个 worker 上，避免与其它用例并发。
pytestmark = pytest.mark.xdist_group(name='mutates_runtime_typed')

# ── 路径常量 ──────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'src'))

PYTHON = sys.executable
SUBPROC_ENV = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}


# ── 双腿编译运行 ──────────────────────────────────────────────────────

def _native_run(code: str, optimize_level: int = 0) -> tuple:
    """原生腿：compile_light_typed 编译 + 运行，返回 (rc, stdout)。"""
    from llvm.compiler import compile_light_typed
    with tempfile.TemporaryDirectory(prefix='_r159d_') as d:
        src = os.path.join(d, '主.light')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, '产物'),
                                  optimize_level=optimize_level)
        r = subprocess.run([exe], capture_output=True, timeout=120)
        return r.returncode, r.stdout.decode('utf-8', errors='replace')


def _src_run(code: str) -> tuple:
    """src（转译）腿：python -m cli.light_unified run，返回 (rc, stdout)。"""
    with tempfile.TemporaryDirectory(prefix='_r159d_src_') as d:
        p = os.path.join(d, '主.light')
        with open(p, 'w', encoding='utf-8') as f:
            f.write(code)
        r = subprocess.run(
            [PYTHON, '-m', 'cli.light_unified', 'run', p],
            capture_output=True, timeout=120, cwd=_ROOT, env=SUBPROC_ENV)
        return r.returncode, r.stdout.decode('utf-8', errors='replace')


# 双腿共用的探针源码（只输出 `标记=值`，逐行可断言）
_PROBE = '''\
打印("L0=" 加上 转字符串(真))
打印("L1=" 加上 转字符串(假))
打印("LIST=" 加上 转字符串([真, 假]))
打印("LIST1=" 加上 转字符串([真]))
打印("DICT=" 加上 转字符串({"k": 真, "m": 假}))
打印("NEST=" 加上 转字符串({"k": [真, 假]}))
打印("NEST2=" 加上 转字符串([[真, 假], [假, 真]]))
打印("MIX=" 加上 转字符串([1, 真, "a"]))
打印("EMPTY=" 加上 转字符串([]))
打印("JSONL=" 加上 序列化JSON([真, 假]))
打印("JSOND=" 加上 序列化JSON({"k": 真}))
'''

# 两腿**应一致**的期望（R152-E2 裁定后的目标口径）。
# 注：容器内**字符串引号**两腿**既有分歧**（native 元素不带引号 / src 带双引号，L-072 遗留，
# 非本线范围，任务书明写「该腿既有格式」）；字典**键**引号同样（native 单引号 / src 双引号）。
# 本线只对**布尔 repr** 断言收敛；引号按各腿既有口径放行，不判为红，显式记录。
_EXPECTED_COMMON = {
    'L0': '真',
    'L1': '假',
    'LIST': '[true, false]',
    'LIST1': '[true]',
    'EMPTY': '[]',
    'NEST2': '[[true, false], [false, true]]',
    'JSONL': '[true, false]',
    'JSOND': '{"k": true}',
}
# 混合列表：布尔必须收敛，但字符串引号各腿既有形态（native 无引号 / src 双引号）
_EXPECTED_NATIVE_MIX = '[1, true, a]'
_EXPECTED_SRC_MIX = '[1, true, "a"]'
# 字典键引号各腿既有形态（native 单引号 / src 双引号）
_EXPECTED_NATIVE_DICT = "{'k': true, 'm': false}"
_EXPECTED_SRC_DICT = '{"k": true, "m": false}'
_EXPECTED_NATIVE_NEST = "{'k': [true, false]}"
_EXPECTED_SRC_NEST = '{"k": [true, false]}'


def _assert_bool_repr_converged(token: str, what: str):
    """断言容器内布尔 token 已收敛为 true/false（而非 真/假）。

    引号口径可能不同（既有分歧），但布尔 repr 必须收敛——这是本线判据核心。
    """
    assert 'true' in token or 'false' in token, \
        f"{what}: 容器内布尔未收敛到 true/false，实得 {token!r}"
    assert '真' not in token and '假' not in token, \
        f"{what}: 容器内布尔仍是中文，实得 {token!r}"


def _parse_output(out: str) -> dict:
    """把 `标记=值` 输出解析为 dict；未匹配行忽略。"""
    res = {}
    for line in out.replace('\r', '').split('\n'):
        if not line:
            continue
        if '=' in line:
            k, _, v = line.partition('=')
            res[k.strip()] = v
    return res


# ══════════════════════════════════════════════════════════════════════
# 1. 双腿对拍：修后两腿输出一致（R152-E2 收敛判据）
# ══════════════════════════════════════════════════════════════════════

def test_双腿对拍_容器内布尔repr收敛():
    """修后两腿容器内布尔 repr 收敛（R152-E2 判据核心）。

    引号口径两腿**既有分歧**（native 单引号 / src 双引号，L-072 遗留，任务书明写
    「该腿既有格式」），**非本线范围**。本线只判「容器内布尔是否 true/false」——
    这是 R152-E2 裁定收敛点；引号各自放行并显式记录。
    """
    rc_n, out_n = _native_run(_PROBE)
    assert rc_n == 0, f"native 腿 rc={rc_n}\n{out_n}"
    rc_s, out_s = _src_run(_PROBE)
    assert rc_s == 0, f"src 腿 rc={rc_s}\n{out_s}"

    got_n = _parse_output(out_n)
    got_s = _parse_output(out_s)

    # 1) 标量：两腿都应保持中文（R152-E2：标量中文）
    for k in ('L0', 'L1'):
        assert k in got_n, f"native 缺标记 {k}"
        assert k in got_s, f"src 缺标记 {k}"
        assert got_n[k] == _EXPECTED_COMMON[k], f"native {k}: {got_n[k]!r}"
        assert got_s[k] == _EXPECTED_COMMON[k], f"src {k}: {got_s[k]!r}"

    # 2) 列表容器内布尔：两腿都收敛到 true/false（主判据，纯布尔/空/嵌套列表）
    for k in ('LIST', 'LIST1', 'EMPTY', 'NEST2'):
        assert k in got_n, f"native 缺标记 {k}: {sorted(got_n)}"
        assert k in got_s, f"src 缺标记 {k}: {sorted(got_s)}"
        # native 收敛检查（真值）
        assert got_n[k] == _EXPECTED_COMMON[k], \
            f"native {k}: 期望 {_EXPECTED_COMMON[k]!r} 实得 {got_n[k]!r}"
        # src 收敛检查（真值）
        assert got_s[k] == _EXPECTED_COMMON[k], \
            f"src {k}: 期望 {_EXPECTED_COMMON[k]!r} 实得 {got_s[k]!r}"

    # 2b) 混合列表：布尔 repr 必须收敛（字符串引号各腿既有口径）
    for k, n_exp, s_exp in (('MIX', _EXPECTED_NATIVE_MIX, _EXPECTED_SRC_MIX),):
        assert k in got_n and k in got_s
        _assert_bool_repr_converged(got_n[k], f"native {k}")
        _assert_bool_repr_converged(got_s[k], f"src {k}")
        assert got_n[k] == n_exp, f"native {k}: {got_n[k]!r}"
        assert got_s[k] == s_exp, f"src {k}: {got_s[k]!r}"

    # 3) 字典容器：布尔 repr 必须收敛（引号按各腿既有口径）
    for k, n_exp, s_exp in (('DICT', _EXPECTED_NATIVE_DICT, _EXPECTED_SRC_DICT),
                            ('NEST', _EXPECTED_NATIVE_NEST, _EXPECTED_SRC_NEST)):
        assert k in got_n, f"native 缺标记 {k}"
        assert k in got_s, f"src 缺标记 {k}"
        _assert_bool_repr_converged(got_n[k], f"native {k}")
        _assert_bool_repr_converged(got_s[k], f"src {k}")
        # 引号口径记录（不判为红，仅断言存在并记录差异）
        assert got_n[k] in (n_exp,), f"native {k}: {got_n[k]!r}"
        assert got_s[k] in (s_exp,), f"src {k}: {got_s[k]!r}"

    # 4) JSON：独立路径，两腿都应合法
    for k in ('JSONL', 'JSOND'):
        assert k in got_n and k in got_s
        assert got_n[k] == _EXPECTED_COMMON[k], f"native {k}: {got_n[k]!r}"
        assert got_s[k] == _EXPECTED_COMMON[k], f"src {k}: {got_s[k]!r}"


def test_标量不受影响_转字符串布尔():
    """R152-E2 裁定：标量保持中文。"""
    rc, out = _native_run('''\
打印("A=" 加上 转字符串(真))
打印("B=" 加上 转字符串(假))
''')
    assert rc == 0, out
    got = _parse_output(out)
    assert got['A'] == '真', f"标量 真 应保持中文，实得 {got['A']!r}"
    assert got['B'] == '假', f"标量 假 应保持中文，实得 {got['B']!r}"


def test_json独立性_序列化JSON不受影响():
    """序列化JSON 走 dv_json_serialize_value 独立路径（case 5 直接 true/false），
    修前即输出合法 JSON，本改动不应改变它。"""
    rc, out = _native_run('''\
打印(序列化JSON([真, 假]))
打印(序列化JSON({"k": 真}))
''')
    assert rc == 0, out
    lines = [ln for ln in out.replace('\r', '').split('\n') if ln]
    assert lines[0] == '[true, false]', f"JSON 列表应 [true, false]，实得 {lines[0]!r}"
    assert lines[1] == '{"k": true}', f"JSON 字典应 {{\"k\": true}}，实得 {lines[1]!r}"


# ══════════════════════════════════════════════════════════════════════
# 2. 反跑有牙：临时改回 depth 不敏感 → 容器分歧复现转红
# ══════════════════════════════════════════════════════════════════════

_RT = os.path.join(_ROOT, 'src', 'llvm', 'runtime_typed.c')

# 锚点：改前（depth 不敏感，复现病灶）。带前导 8 空格 + CRLF
_BUG_LINE = (b'        case 5: return dv_strdup(v->boolean ? "\xe7\x9c\x9f" : "\xe5\x81\x87");\r\n')
# 锚点：改后（R152-E2 depth-aware）。带前导 8 空格 + CRLF，与真实文件逐字节一致
_FIX_LINE = (b'        case 5: return dv_strdup(v->boolean ? (depth > 0 ? "true" : "\xe7\x9c\x9f")\r\n'
             b'                                            : (depth > 0 ? "false" : "\xe5\x81\x87"));\r\n')


def _read_rt() -> bytes:
    with open(_RT, 'rb') as f:
        return f.read()


# R161-B 实测暴露的**跨模块并发**缺陷（不是本文件逻辑错）：
# 反跑用例临时改写 src/llvm/runtime_typed.c 再还原；pytest 默认 `-n 4
# --dist=loadscope` 只保证同模块用例同 worker，**不阻止别的模块的 worker** 在改写
# 窗口内读该文件 / 调 clang 编译，于是出现「单跑绿、全量跑红」的假红。
# 用跨进程文件锁把「改写 + 编译 + 还原」整段串行化。
# 锁文件放系统临时目录（**不落仓库**，避免污染 git status）。
import tempfile as _tempfile
_LOCK_PATH = os.path.join(_tempfile.gettempdir(), 'r159d_runtime_typed.mutex')


class _RTWriteLock:
    """跨进程互斥（Windows 用 msvcrt.locking，POSIX 用 fcntl.flock）。"""

    def __enter__(self):
        self._fh = open(_LOCK_PATH, 'a+b')
        for _ in range(600):          # 最多等 60s
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                import time
                time.sleep(0.1)
        return self                  # 超时也放行，避免死锁

    def __exit__(self, *exc):
        try:
            if os.name == 'nt':
                import msvcrt
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            self._fh.close()
        return False


def _write_rt(data: bytes):
    """写回 runtime_typed.c（原子替换 + 重试）。

    Windows 下文件可能带 A 属性或被 clang 编译进程短暂占用，`wb`/`truncate` 会
    报 [Errno 22]/[Errno 13]。改用「写临时文件 + os.replace 原子覆盖」，并做短重试。
    """
    import time
    tmp = _RT + '.r159d_patch.tmp'
    last_err = None
    for attempt in range(6):
        try:
            # 清除只读位（若被设置）
            if os.path.exists(_RT):
                os.chmod(_RT, os.stat(_RT).st_mode | 0o200)
            with open(tmp, 'wb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, _RT)
            return
        except (PermissionError, OSError) as e:
            last_err = e
            time.sleep(0.6)
    # 兜底：尝试就地截断写
    with open(_RT, 'r+b') as f:
        f.truncate(0)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    raise last_err


def test_反跑_改回depth不敏感_容器分歧复现():
    """把 case 5 临时改回 depth 不敏感 → 容器内布尔应回到中文（复现 L-193 分歧）→ 转红。

    跑完**必须恢复**（不留痕）。若源码已是修复态（本改动未落盘）则本测试**应红**——
    这是「反跑有牙」的咬合：本测试的存在本身证明深度感知是**必要的**。

    R161-B 实测结论：**本用例在 pytest-xdist 并行下不可安全运行**。它改写的是
    全仓共享的 `src/llvm/runtime_typed.c`，任何并发 worker 都可能：
      ① 在改写窗口内读该文件（源码锚点断言读到半改状态）；
      ② 在改写窗口内调 clang 编译（编译到 depth 不敏感版本）；
      ③ 若本 worker 中途被杀（xdist 超时/节点掉线），`finally` 不执行 ⇒
         源码**永久停在 bug 态**（实测发生过两次，全量运行后源码被改坏）。
    跨进程文件锁只能串行化「改写段」，挡不住 ①②③。故：**并行模式下跳过本用例**，
    由串行运行（`-p no:xdist` 或 `-n 0`）承担反跑验证。
    """
    if os.environ.get('PYTEST_XDIST_WORKER'):
        pytest.skip('改写共享源码的反跑用例在 xdist 并行下不安全（见 docstring）；'
                    '串行运行（-n 0）时执行')
    with _RTWriteLock():
        original = _read_rt()

        # 断言当前是修复态（否则本测试无意义）
        assert _FIX_LINE in original, \
            "前置：runtime_typed.c 应为 R159-D depth-aware 修复态（否则反跑无牙）"
        assert _BUG_LINE not in original

        # 打补丁：改成 depth 不敏感（复现病灶）
        patched = original.replace(_FIX_LINE, _BUG_LINE)
        assert patched != original, "补丁未生效：锚点不匹配"
        try:
            _write_rt(patched)
            # 现在容器内布尔应回中文（复现 L-193 分歧）
            rc, out = _native_run('''\
打印("LIST=" 加上 转字符串([真, 假]))
打印("DICT=" 加上 转字符串({"k": 真}))
打印("SCALAR=" 加上 转字符串(真))
''')
            assert rc == 0, f"打补丁后编译失败 rc={rc}\n{out}"
            got = _parse_output(out)
            # 复现病灶：容器内回中文
            assert got['LIST'] == '[真, 假]', \
                f"反跑未复现：LIST 应回 [真, 假]，实得 {got.get('LIST')!r}"
            assert got['DICT'] == "{'k': 真}", \
                f"反跑未复现：DICT 应回 {{'k': 真}}，实得 {got.get('DICT')!r}"
            # 标量仍应中文（原病灶即如此，标量路径 depth=0 不受影响）
            assert got['SCALAR'] == '真', f"标量应保持中文，实得 {got.get('SCALAR')!r}"
        finally:
            _write_rt(original)
            # 恢复后再确认修复态仍在
            restored = _read_rt()
            assert _FIX_LINE in restored, "恢复失败：修复态锚点丢失"
            assert _BUG_LINE not in restored


# ══════════════════════════════════════════════════════════════════════
# 3. 源码级守单点（防腐烂）
# ══════════════════════════════════════════════════════════════════════

def test_源码级_病灶depth感知锚点存在():
    """case 5 必须是 depth-aware 形态（防腐烂）；且 dv_list_join 两处也走 depth>=1。"""
    with open(_RT, 'rb') as f:
        txt = f.read()
    assert _FIX_LINE in txt, "case 5 缺失 depth-aware 形态"
    assert _BUG_LINE not in txt, "case 5 仍是 depth 不敏感（未修复）"
    # dv_list_join 两处（codegen_typed.py:3349 转字符串(列表) 主路径）
    assert txt.count(b'dv_to_string_depth(e, 1)') == 2, \
        f"dv_list_join 应有两处 depth>=1，实得 {txt.count(b'dv_to_string_depth(e, 1)')}"


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))