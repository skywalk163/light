# -*- coding: utf-8 -*-
"""LH-35（光明P1）：归约 一调就崩 + 映射/筛选 返回迭代器 [L-257/L-258]。

背景（lighthive 任务卡 T-0209）：
  · L-257：`归约(列表, 段落, 初值)` 一调就崩——code_generator 把 `归约` 直译为
    `functools.reduce`，但产物序言没有 `import functools`，真跑报
    `名称错误 / name 'functools' is not defined`。
  · L-258：`映射`/`筛选` 直译成内建 `map`/`filter`，返回惰性迭代器对象，
    打印出来是 `<map object at 0x…>`，不能 `长()`、不能下标、不能 `转字符串`。

  期望：`归约` 走「数据在前」语序可正常真跑；`映射`/`筛选` 返回**列表**
  （与 `反转`/`范围`/`枚举` 同口径），可 `长()`、可下标、可 `转字符串`。

为什么用真跑：这两个缺陷的表现层都在**产物执行**（NameError / 返回类型），
只看生成代码字符串会漏。故本文件起 `python -m cli.light run <临时.light>`
（默认 src 后端 = code_generator.PythonCodeGenerator），断言 stdout。

语序裁定（重要）：任务卡只写 `归约([1,2,3], 加倍, 0) → 12`，未给 `加倍` 定义。
  依项目权威用法 `docs/语义密度示例集.md:350`
  `归约(组.值, 段(a, b) 返 a + b["金额"], 0)`，`归约` 是**二元折叠**
  （对应 `functools.reduce(func, iterable, initial)`）。要让上式得 12，
  `加倍` 必须是二元归约函数：0 + 1*2 + 2*2 + 3*2 = 12。

用例（覆盖任务卡四条验收 + 下标可用性）：
  ① 归约([1,2,3], 加倍, 0) → 12
  ② 转字符串(映射([1,2,3], 双倍)) 含 [2, 4, 6]；长(映射(...)) → 3
  ③ 长(筛选([1,2,3,4], 判偶)) → 2；转字符串(筛选(...)) 含 [2, 4]
  ④ 长(枚举([1,2,3])) → 3（顺手收 L-245 的 `枚举` 尾巴）
  ⑤ 映射结果可下标：转字符串(映射(...)[1]) → 4
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# 子进程强制 UTF-8：Windows 控制台默认 cp936，中文输出会抛 UnicodeEncodeError，
# 与被测语义无关（与 tests/unit/test_LH10_最终块异常传播.py 同一口径）。
SUBPROC_ENV = {
    **os.environ,
    'PYTHONUTF8': '1',
    'PYTHONIOENCODING': 'utf-8',
}


def _run_light(src: str) -> tuple:
    """起 `python -m cli.light run <临时.light>`，返回 (rc, stdout, stderr)。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'probe_lh35.light'
        path.write_text(src, encoding='utf-8')
        r = subprocess.run(
            [sys.executable, '-m', 'cli.light', 'run', str(path)],
            capture_output=True, text=True, encoding='utf-8',
            cwd=str(REPO_ROOT), timeout=120, env=SUBPROC_ENV,
        )
    return r.returncode, r.stdout, r.stderr


# 一份源码跑一次：七行输出覆盖全部验收点（子进程开销大，避免重复起进程）。
_SOURCE = '''\
段落 加倍(累积, 项):
  返回 累积 + 项 * 2

段落 双倍(数):
  返回 数 * 2

段落 判偶(数):
  返回 数 % 2 == 0

打印 转字符串(归约([1,2,3], 加倍, 0))
打印 转字符串(映射([1,2,3], 双倍))
打印 长(映射([1,2,3], 双倍))
打印 长(筛选([1,2,3,4], 判偶))
打印 转字符串(筛选([1,2,3,4], 判偶))
打印 长(枚举([1,2,3]))
打印 转字符串(映射([1,2,3], 双倍)[1])
'''


@pytest.fixture(scope='module')
def lines() -> list:
    """真跑一次，返回去空行后的 stdout 行列表。"""
    rc, out, err = _run_light(_SOURCE)
    assert rc == 0, f'真跑失败 rc={rc}\nstdout={out!r}\nstderr={err!r}'
    result = [ln.strip() for ln in out.splitlines() if ln.strip()]
    assert len(result) == 7, f'预期 7 行输出，实际 {len(result)} 行：{result!r}'
    return result


# ── ① 归约：数据在前语序必须能真跑（修前抛 functools NameError） ──
def test_归约_数据在前_真跑得12(lines):
    assert lines[0] == '12', f'归约期望 12，实际 {lines[0]!r}'


# ── ② 映射：返回列表（非迭代器），可 转字符串 / 长 ──
def test_映射_返回列表_可转字符串(lines):
    assert lines[1] == '[2, 4, 6]', f'映射期望 [2, 4, 6]，实际 {lines[1]!r}'
    assert 'map object' not in lines[1]
    assert lines[2] == '3', f'长(映射) 期望 3，实际 {lines[2]!r}'


# ── ③ 筛选：返回列表，可 长 / 转字符串 ──
def test_筛选_返回列表_可长可转字符串(lines):
    assert lines[3] == '2', f'长(筛选) 期望 2，实际 {lines[3]!r}'
    assert lines[4] == '[2, 4]', f'筛选期望 [2, 4]，实际 {lines[4]!r}'
    assert 'filter object' not in lines[4]


# ── ④ 枚举：包 list 后 长 可用（L-245 尾巴） ──
def test_枚举_返回列表_可长(lines):
    assert lines[5] == '3', f'长(枚举) 期望 3，实际 {lines[5]!r}'


# ── ⑤ 映射结果可下标（列表语义的旁证） ──
def test_映射结果_可下标(lines):
    assert lines[6] == '4', f'映射[1] 期望 4，实际 {lines[6]!r}'