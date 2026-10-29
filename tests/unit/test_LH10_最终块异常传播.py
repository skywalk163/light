# -*- coding: utf-8 -*-
"""LH-10（光明P0）：`试` 无 `捕` 必须生成 try/finally，异常不得被静默吞掉。

背景（lighthive/docs/光明语言问题记录.md LH-10，P0）：
  `试: … 最终: …`（没有 `捕`）时，code_generator.py 旧逻辑把无 `捕` 的 `试`
  生成为 `except Exception: pass` + `finally`——异常被完全吞掉，且异常点之后、
  同一段落内的代码继续执行，外层 `捕` 收不到（假绿制造机：程序不崩但结果错了）。

  正确语义：无 `捕` 时异常应向外传播（Python 的 try/finally 不拦截异常）。

本文件用 subprocess 起 `python -m cli.light run <临时.light>`（默认 src 后端，
即 code_generator.PythonCodeGenerator——缺陷的表现层），断言 stdout，而非 import
内部函数：这个缺陷的表现就是「程序没崩但结果错了」，只看生成代码结构会漏掉。

用例（任务卡要求至少 4 例）：
  1. 无捕 + 最终：异常穿透到外层 `捕`；「不该出现」那行没有输出  ← 有牙（修前红）
  2. 有捕（无最终）：本层 `捕` 吃掉，执行继续                ← 回归护栏
  3. 捕 + 最终 同时存在：先 `捕` 再 `最终`，顺序正确           ← 回归护栏
  4. 返回 在 试 内 + 最终（无捕）：return 路径也走 finally，返回值不被覆盖 ← 回归护栏
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SUBPROC_ENV = {
    **os.environ,
    'PYTHONUTF8': '1',
    'PYTHONIOENCODING': 'utf-8',
}


def _run_light(src: str) -> tuple[int, str, str]:
    """起 `python -m cli.light run <临时.light>`，返回 (rc, stdout, stderr)。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'probe.light'
        path.write_text(src, encoding='utf-8')
        r = subprocess.run(
            [sys.executable, '-m', 'cli.light', 'run', str(path)],
            capture_output=True, text=True, encoding='utf-8',
            cwd=str(REPO_ROOT), timeout=120, env=SUBPROC_ENV,
        )
    return r.returncode, r.stdout, r.stderr


# ── 用例 1：无捕 + 最终，异常必须穿透到外层 捕（LH-10 复现） ──
_CASE1 = '''\
段落 冒炮():
  抛出 "我是一个异常"

段落 探():
  试:
    冒炮()
    打印 "抛出之后（不该出现）"
  最终:
    打印 "最终块执行"
  打印 "异常之后仍然继续执行了"

段落 主():
  试:
    探()
    打印 "外层: 没抛"
  捕 错误 为 e2:
    打印 "外层捕获到"
'''


def test_01_无捕_最终_异常穿透到外层捕():
    rc, out, err = _run_light(_CASE1)
    assert rc == 0, f"[无捕+最终] 退出码 {rc}:\n{err}\n{out}"
    # stdout 全等：最终块先执行，随后异常向外传播进入外层 捕。
    # 修前（旧 `except Exception: pass` 吞异常）会额外打出
    # 「异常之后仍然继续执行了」+「外层: 没抛」，故本断言有牙（修前红）。
    assert out.strip().split('\n') == ["最终块执行", "外层捕获到"], \
        f"stdout 不匹配:\n{out!r}"
    # 「不该出现」那行没有输出（异常点之后、同一段落内的代码不得继续执行）
    assert "抛出之后（不该出现）" not in out, f"异常点之后的代码竟继续执行:\n{out}"
    assert "异常之后仍然继续执行了" not in out, f"无捕 try 之后代码竟继续执行:\n{out}"
    assert "外层: 没抛" not in out, f"外层捕未生效（还打印了没抛）:\n{out}"


# ── 用例 2：有捕（无最终），本层捕吃掉，执行继续 ──
_CASE2 = '''\
段落 主():
  试:
    抛出 "boom"
    打印 "抛出之后（不该出现）"
  捕 错误 为 e:
    打印 "捕获到"
  打印 "捕之后继续"
'''


def test_02_有捕_无最终_本层捕吃掉():
    rc, out, err = _run_light(_CASE2)
    assert rc == 0, f"[有捕] 退出码 {rc}:\n{err}\n{out}"
    assert "捕获到" in out, f"捕 未执行:\n{out}"
    assert "捕之后继续" in out, f"捕 后代码未继续:\n{out}"
    assert "抛出之后（不该出现）" not in out, f"异常点之后的代码竟执行:\n{out}"


# ── 用例 3：捕 + 最终 同时存在，顺序：先捕再最终 ──
_CASE3 = '''\
段落 主():
  试:
    抛出 "boom"
  捕 错误 为 e:
    打印 "捕获到"
  最终:
    打印 "最终块"
  打印 "之后继续"
'''


def test_03_捕_最终_顺序正确():
    rc, out, err = _run_light(_CASE3)
    assert rc == 0, f"[捕+最终] 退出码 {rc}:\n{err}\n{out}"
    lines = [ln for ln in out.split('\n') if ln.strip()]
    # 先 捕 再 最终
    assert lines[0] == "捕获到", f"捕 应最先执行:\n{out}"
    assert "最终块" in lines[1], f"最终 应在 捕 之后:\n{out}"
    assert "之后继续" in lines[2], f"捕+最终 之后应继续:\n{out}"


# ── 用例 4：返回 在 试 内 + 最终（无捕），return 路径也走 finally ──
_CASE4 = '''\
设 日志 为 []

段落 测试():
  试:
    日志.追加("try")
    返回 "result"
  最终:
    日志.追加("finally")
  返回 "end"

段落 主():
  设 结果 为 测试()
  打印 结果
  打印 日志
'''


def test_04_返回_在试内_最终_走finally():
    rc, out, err = _run_light(_CASE4)
    assert rc == 0, f"[返回+最终] 退出码 {rc}:\n{err}\n{out}"
    lines = [ln for ln in out.split('\n') if ln.strip()]
    # 返回值不被 finally 覆盖（应为 "result"，而非 "end"）
    assert lines[0] == "result", f"返回值被覆盖:\n{out}"
    # finally 在 return 路径上确实执行
    assert "try" in lines[1], f"try 未执行:\n{out}"
    assert "finally" in lines[1], f"finally 未在 return 路径执行:\n{out}"
    # 返回 "end" 不应被走到（try 内 return 已提前返回）
    assert "end" not in lines[1], f"return 之后的代码竟执行:\n{out}"
