# -*- coding: utf-8 -*-
"""R220 · 「移植实测 7 条语言坑」的可执行判据（只新增测试，不改编译器）。

## 取证环境

- 入口：本仓 `python -m cli.light run <入口>`（默认 `--backend src`，即 CLI 与 `src/` 同仓）。
- 标准库：本仓 `stdlib/`，**不用**下游 stdlib 快照 / lightharness 副本。
- 临时文件：全部走 pytest `tmp_path`，不写死 `/tmp/xxx`，Windows / Linux 同跑。
- 结论日期：**2026-11-07**（light HEAD `8567a6588` 复测 T-0258 原表）；
  本文件为可执行固化，日期晚于复测不改变结论口径。

## 纪律

**结论与缺陷账 / 任务卡冲突时，以本文件实测为准。** 老结论过期就改判据、点名过期，
不要为了「守住旧结论」去改编译器；反过来，判据红了也不要静默放宽断言。

## 三态结论（每条至少 1 个 subprocess 真跑用例）

| # | T-0258 原结论 | 本文件实测结论 | 态 |
|---|---|---|---|
| 1 | `导出 a b c` 行末不要加句号 | 多名导出 + 行末句号均 rc=0，三个符号都能被导入 | **已修**（原结论过期） |
| 2 | 字符串不解释 `\\uXXXX`，要写真实 UTF-8 | 单个反斜杠的 `\\u4f60` 已输出「你」；写 `\\\\u4f60` 才是字面反斜杠+u | **已修**（原结论过期） |
| 3 | 不支持匿名函数 `段落() 返回 x` | 仍不支持，但抛可读「名称错误」；`接收 x：返回 …` 可用 | **设计约束** |
| 4 | `设 f(x) 为 v` 非法 | 仍非法，parser 报「期望'为'或'等于'」 | **设计约束** |
| 5 | 变量名避开关键字尾巴 | `设 等待 为 1` 仍解析失败 | **仍红**（保留复现 + 建议换名） |
| 6 | `写` 只吃单个字面量或已赋值变量 | `写 转字符串(甲 + 1)` 已输出 `2`（不换行） | **已修**（原结论过期） |
| 7 | `捕获` 必须紧跟 `尝试:`，跨模块会错位 | 常规 `尝试/捕获`（含 `试/捕` 别名）rc=0 | **已修**（基本形态已绿） |

## 已绿能力的回归（≥ 12 例总数的一部分）

`light run … -- 甲 乙` + `用户参数()`；`分割字符串(分隔符=)`；`读取文件(路径=)` /
`写入文件(编码=)`；`映射` / `筛选` 返回列表；列表切片读与切片赋值。

## 一条实测风险（不写成断言）

`导出` 目前**未做白名单门禁**：模块里未 `导出` 的名字也能被 `从 模块 导入 …` 拿到
（负控 rc=0）。这更像缺陷而非设计，故不把该行为锁进断言，只在此点名，避免用测试
固化错误语义。
"""

import os
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _跑(入口, 实参=None):
    """真起 `python -m cli.light run` 子进程（默认 src 后端），返回 CompletedProcess。"""
    return subprocess.run(
        [sys.executable, "-m", "cli.light", "run", str(入口)] + list(实参 or []),
        cwd=_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )


def _写(tmp_path, 名, 源码):
    p = tmp_path / 名
    p.write_text(源码, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 坑 1：`导出` 行末句号 —— 原结论已过期
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("带句号", [False, True], ids=["行末无句号", "行末带句号"])
def test_坑一_导出多名行末句号均不报错且全部可导入(tmp_path, 带句号):
    """原结论「行末不要加句号」在 2026-11-07 实测已不成立：两种写法都通。"""
    尾 = "。" if 带句号 else ""
    _写(tmp_path, "库.light",
        "设 甲 为 1\n设 乙 为 2\n设 丙 为 3\n导出 甲 乙 丙%s\n" % 尾)
    入口 = _写(tmp_path, "主.light", "从 库 导入 甲 乙 丙\n打印 甲\n打印 乙\n打印 丙\n")
    r = _跑(入口)
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.split() == ["1", "2", "3"], r.stdout


# ---------------------------------------------------------------------------
# 坑 2：字符串 `\uXXXX` —— 原结论「不解释」已过期
# ---------------------------------------------------------------------------

def test_坑二_单个反斜杠u序列被解释为对应字符(tmp_path):
    """2026-11-07 实测：源里写单个反斜杠 `\\u4f60` 会输出「你」。"""
    r = _跑(_写(tmp_path, "探针.light", r'打印("\u4f60好")' + "\n"))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "你好", r.stdout


def test_坑二_双反斜杠才保留字面序列(tmp_path):
    """写 `\\\\u4f60`（源码里两个反斜杠）才得到字面 `\\u4f60`，即普通转义语义。"""
    r = _跑(_写(tmp_path, "探针.light", r'打印("\\u4f60好")' + "\n"))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == r"\u4f60好", r.stdout


def test_坑二_真实UTF8字符正常输出(tmp_path):
    r = _跑(_写(tmp_path, "探针.light", '打印("你好")\n'))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "你好", r.stdout


# ---------------------------------------------------------------------------
# 坑 3：不支持 `段落() 返回 x`；`接收 x：返回 …` 是替代写法
# ---------------------------------------------------------------------------

def test_坑三_段落匿名函数仍不支持但报错可读(tmp_path):
    r = _跑(_写(tmp_path, "探针.light", "设 f 为 段落() 返回 1\n打印(f())\n"))
    assert r.returncode != 0, "不支持的写法必须非零退出，不许静默"
    assert r.stdout.strip() == "", f"不应产出错值：{r.stdout!r}"
    assert "名称错误" in r.stderr, r.stderr
    assert "段落" in r.stderr, "报错应点名出问题的关键字"


def test_坑三_接收形式的匿名函数可用(tmp_path):
    r = _跑(_写(tmp_path, "探针.light",
              "设 f 为 接收 甲：返回 甲 乘 2\n打印(f(3))\n"))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "6", r.stdout


# ---------------------------------------------------------------------------
# 坑 4：`设 f(x) 为 v` 非法 —— 设计约束（`设` 只认变量名）
# ---------------------------------------------------------------------------

def test_坑四_设不接受函数签名(tmp_path):
    r = _跑(_写(tmp_path, "探针.light", "设 f(3) 为 5\n打印(f(3))\n"))
    assert r.returncode != 0, "`设 f(x) 为 v` 不该被接受"
    assert "解析错误" in r.stderr, r.stderr
    assert "为" in r.stderr and "等于" in r.stderr, "报错应提示期望『为/等于』"


# ---------------------------------------------------------------------------
# 坑 5：关键字尾巴作变量名 —— 仍红（复现 + 建议）
# ---------------------------------------------------------------------------

def test_坑五_变量名等待仍解析失败(tmp_path):
    """仍红：`等待` 是 `当…` 语句的关键字尾巴（词法最大匹配）。
    建议：变量改名（如 `等待时长`），不要拿语句关键字当变量名。
    """
    r = _跑(_写(tmp_path, "探针.light", "设 等待 为 1\n打印(等待)\n"))
    assert r.returncode != 0, "按 T-0258 结论此时应仍红；变绿则说明已修，需更新本判据"
    assert "解析错误" in r.stderr, r.stderr


def test_坑五_对照_跳过作变量名可解析(tmp_path):
    """对照：并非所有关键字尾巴都红（`跳过` 在表达式位置被允许），
    所以建议是「避开只作语句关键字的词」，不是「所有关键字都不能用」。"""
    r = _跑(_写(tmp_path, "探针.light", "设 跳过 为 1\n打印(跳过)\n"))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "1", r.stdout


# ---------------------------------------------------------------------------
# 坑 6：`写` 已支持表达式 —— 原结论已过期
# ---------------------------------------------------------------------------

def test_坑六_写可吃表达式调用结果(tmp_path):
    r = _跑(_写(tmp_path, "探针.light", "设 甲 为 1\n写 转字符串(甲 + 1)\n"))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout == "2", f"`写` 语义是不换行 write：{r.stdout!r}"


def test_坑六_写字面量与已赋值变量仍通(tmp_path):
    r = _跑(_写(tmp_path, "探针.light", '设 乙 为 "已赋值"\n写 乙\n写 "字面量"\n'))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout == "已赋值字面量", f"两段 write 应拼接且无换行：{r.stdout!r}"


# ---------------------------------------------------------------------------
# 坑 7：`尝试/捕获` 常规形态 —— 已修（基本形态已绿）
# ---------------------------------------------------------------------------

def test_坑七_尝试捕获常规形态(tmp_path):
    r = _跑(_写(tmp_path, "探针.light",
              '尝试:\n  抛出 "炸了"\n捕获:\n  打印("捕到了")\n'))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "捕到了", r.stdout


def test_坑七_单字别名试捕同样有效(tmp_path):
    r = _跑(_写(tmp_path, "探针.light",
              '试:\n  抛 "炸了"\n捕:\n  打印("捕到了")\n'))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "捕到了", r.stdout


# ---------------------------------------------------------------------------
# 今天已绿能力的回归
# ---------------------------------------------------------------------------

def test_绿_用户参数经双横线原样到达(tmp_path):
    r = _跑(_写(tmp_path, "探针.light", "打印 转字符串(用户参数())\n"),
             ["--", "甲", "乙"])
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == '["甲", "乙"]', r.stdout


def test_绿_分割字符串支持中文关键字参数(tmp_path):
    r = _跑(_写(tmp_path, "探针.light",
              '打印 转字符串(分割字符串("a,b", 分隔符=","))\n'))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == '["a", "b"]', r.stdout


def test_绿_读取文件与写入文件支持中文关键字参数(tmp_path):
    路径 = (tmp_path / "数据.txt").as_posix()
    r = _跑(_写(tmp_path, "探针.light",
              f'设 路径 为 "{路径}"\n'
              '写入文件(路径, "你好", 编码="utf-8")\n'
              '打印 转字符串(读取文件(路径, 编码="utf-8"))\n'))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "你好", r.stdout


def test_绿_映射返回列表(tmp_path):
    r = _跑(_写(tmp_path, "探针.light",
              "打印 转字符串(映射([1, 2], 接收 甲：返回 甲 乘 2))\n"))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "[2, 4]", r.stdout


def test_绿_筛选返回列表(tmp_path):
    r = _跑(_写(tmp_path, "探针.light",
              "打印 转字符串(筛选([1, 2, 3], 接收 甲：返回 甲 大于 1))\n"))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "[2, 3]", r.stdout


def test_绿_列表切片赋值成立(tmp_path):
    r = _跑(_写(tmp_path, "探针.light",
              "设 表 为 [1, 2, 3, 4]\n设 表[0:2] 为 [9, 9]\n打印 转字符串(表)\n"))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "[9, 9, 3, 4]", r.stdout


def test_绿_列表切片读与写侧对称(tmp_path):
    r = _跑(_写(tmp_path, "探针.light",
              "设 表 为 [1, 2, 3, 4]\n打印 转字符串(表[1:3])\n"))
    assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
    assert r.stdout.strip() == "[2, 3]", r.stdout
