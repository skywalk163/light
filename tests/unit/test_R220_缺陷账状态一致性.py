# -*- coding: utf-8 -*-
"""T-0282 / R220：语言缺陷账 L-256~L-262 的「可执行判据 + 账实一致门禁」。

## 本文件承担两件事

1. **可执行判据**：每条缺陷至少一个 `subprocess` 真跑用例 ——
   `python -m cli.light run <探针>`，用本仓 `stdlib/`，不用下游项目的快照。
   原生腿差异额外跑 `run --backend native`。
2. **账实一致门禁**：账本 `docs/功能对标/语言缺陷账.md` 里 L-256~L-262 若标
   「✅ 已修复」/「🟡 部分修复（2026-11-07 复测）」，本文件就必须有同名
   `test_L2xx_*` 判据；历史 🔴 结论必须保留 —— 防止「只改账不改判据」。

## 取证纪律（账本 §二十七·四）

判断缺陷是否已修，必须用本仓 CLI + 本仓 stdlib 真跑；用下游项目的旧 stdlib
快照跑出来的结论测的是快照，不是语言。据此本文件的每个断言都看进程 rc 与 stdout。
"""

import ast
import importlib.util
import os
import re
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_账本路径 = os.path.join(_ROOT, "docs", "功能对标", "语言缺陷账.md")

_编号列表 = ["L-256", "L-257", "L-258", "L-259", "L-260", "L-261", "L-262"]

# 账本编号 → 本文件里必须存在的判据函数名（账上标已修却无判据 → 门禁红）
_判据名 = {
    "L-256": ("test_L256_中文关键字代表性调用", "test_L256_形参中英混杂已清零"),
    "L-257": ("test_L257_归约开箱可运行",),
    "L-258": ("test_L258_映射筛选返回列表",),
    "L-259": ("test_L259_解析时间ISO与失败抛错",),
    "L-260": ("test_L260_切片赋值成立",),
    "L-261": ("test_L261_伪名不在清单且真写法可用",),
    "L-262": ("test_L262_两腿参数列表一致",),
}


def _跑(源码, 实参=None, 后端=None, 超时=180):
    """真起 `python -m cli.light run` 子进程，返回 CompletedProcess。"""
    import tempfile

    d = tempfile.mkdtemp(prefix="r220_")
    入口 = os.path.join(d, "探针.light")
    with open(入口, "w", encoding="utf-8", newline="\n") as f:
        f.write(源码)
    命令 = [sys.executable, "-m", "cli.light", "run", 入口]
    if 后端:
        命令 += ["--backend", 后端]
    if 实参:
        命令 += ["--"] + list(实参)
    返回 = subprocess.run(
        命令, cwd=_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=超时,
    )
    返回.stdout = (返回.stdout or "").replace("\r\n", "\n")
    返回.stderr = (返回.stderr or "").replace("\r\n", "\n")
    return 返回


def _账本():
    with open(_账本路径, encoding="utf-8") as f:
        return f.read()


def _条目(账本, 编号):
    """切出 `#### L-xxx · …` 到下一个标题之间的完整条目（含历史状态与复测状态）。"""
    m = re.search(
        r"^#### %s ·.*?(?=^#### |^### |\Z)" % re.escape(编号),
        账本, re.S | re.M,
    )
    assert m, "账本里找不到条目 %s" % 编号
    return m.group(0)


# ---------------------------------------------------------------------------
# 账实一致门禁
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("编号", _编号列表)
def test_账本每条都保留历史结论且有2026_11_07复测状态(编号):
    """历史 🔴 不许删；复测结论与日期必须在条目内。"""
    段 = _条目(_账本(), 编号)
    assert "2026-10-30 实测" in 段, "%s 的历史结论被删了：账本不许只留新结论" % 编号
    assert "状态（2026-11-07 复测）" in 段, "%s 缺少 2026-11-07 复测状态行" % 编号
    assert "2026-11-07" in 段, "%s 缺复测日期" % 编号
    状态行 = re.search(r"\|\s*\*\*状态（2026-11-07 复测）\*\*\s*\|(.*?)\|", 段, re.S)
    assert 状态行, "%s 的复测状态行格式不对" % 编号
    文字 = 状态行.group(1)
    assert ("✅" in 文字) or ("🟡" in 文字), (
        "%s 复测结论既不是已修复也不是部分修复：%r" % (编号, 文字[:80])
    )


@pytest.mark.parametrize("编号", _编号列表)
def test_账上结论有本文件判据(编号):
    """「标已修/部分修」→ 本文件必须有对应 test_L2xx_* 判据。"""
    段 = _条目(_账本(), 编号)
    状态行 = re.search(r"\|\s*\*\*状态（2026-11-07 复测）\*\*\s*\|(.*?)\|", 段, re.S)
    assert 状态行, "%s 缺复测状态行" % 编号
    if ("✅" not in 状态行.group(1)) and ("🟡" not in 状态行.group(1)):
        return
    for 名 in _判据名[编号]:
        assert 名 in globals(), (
            "账本说 %s 已修/部分修，但 %s 里没有判据 %s" % (编号, os.path.basename(__file__), 名)
        )
        assert callable(globals()[名]), "%s 不是可调用判据" % 名


def test_汇总表覆盖七条且与条目一致():
    """二十七章的复测汇总表必须列全 7 条，且每条都指向 2026-11-07。"""
    账本 = _账本()
    汇总 = re.search(r"\*\*复测结论汇总（2026-11-07，T-0282）\*\*.*?(?=### 二十七·〇)", 账本, re.S)
    assert 汇总, "找不到 2026-11-07 复测汇总表"
    表 = 汇总.group(0)
    for 编号 in _编号列表:
        assert re.search(r"^\|\s*%s\s*\|" % re.escape(编号), 表, re.M), (
            "汇总表缺 %s" % 编号
        )
    assert 表.count("T-0282") >= 7, "汇总表的交付卡列没有逐条落到 T-0282"


def test_取证纪律条款在位():
    """任务卡目标 3：取证纪律必须是醒目条款，不能只散落在正文。"""
    账本 = _账本()
    assert "取证纪律（新增条款，后续每轮照做）" in 账本
    assert "测的是快照，不是语言" in 账本
    assert "python -m cli.light run" in 账本


# ---------------------------------------------------------------------------
# L-256 · 中文关键字（部分修复：形参已统一中文，直通 Python 内建仍收位置参数）
# ---------------------------------------------------------------------------

def test_L256_中文关键字代表性调用(tmp_path):
    """IO / 字符串 / JSON / 容器四类内置用中文关键字真跑。"""
    路径 = str(tmp_path / "数据.txt").replace("\\", "/")
    源 = (
        '设 路径 为 "%s"\n'
        '打印 转字符串(分割字符串("a,b", 分隔符=","))\n'
        '写入文件(路径, "你好", 编码="utf-8")\n'
        '打印 转字符串(读取文件(路径=路径, 编码="utf-8"))\n'
        '原子写入(路径, "内容", 编码="utf-8", 权限=空)\n'
        '打印 "原子写通"\n'
        '打印 转字符串(序列化JSON({"a": 1}, 缩进=2))\n'
        '打印 转字符串(字典获取({"a": 1}, "b", 默认值=5))\n'
        '打印 转字符串(排序列表([3, 1, 2], 键=接收 甲：返回 甲))\n'
        '设 表 为 [3, 1, 2]\n'
        '列表排序(表, 反向=真)\n'
        '打印 转字符串(表)\n'
    ) % 路径
    r = _跑(源)
    assert r.returncode == 0, "rc=%s stderr=%s" % (r.returncode, r.stderr[-800:])
    assert r.stdout.split("\n")[:9] == [
        '["a", "b"]', "你好", "原子写通", '{', '  "a": 1', '}', "5", "[1, 2, 3]", "[3, 2, 1]",
    ], r.stdout


def test_L256_形参中英混杂已清零():
    """结构根因：stdlib/builtins.py 顶层 def 的形参不再中英混杂。"""
    with open(os.path.join(_ROOT, "stdlib", "builtins.py"), encoding="utf-8") as f:
        树 = ast.parse(f.read())
    纯英文, 纯中文, 混杂 = 0, 0, 0
    for 节点 in 树.body:
        if not isinstance(节点, ast.FunctionDef):
            continue
        名 = [a.arg for a in 节点.args.args if a.arg not in ("self", "cls")]
        if not 名:
            continue
        有英 = any(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", x) for x in 名)
        有中 = any(re.search(r"[\u4e00-\u9fff]", x) for x in 名)
        if 有英 and 有中:
            混杂 += 1
        elif 有英:
            纯英文 += 1
        else:
            纯中文 += 1
    assert 混杂 == 0, "仍有 %d 个函数形参中英混杂" % 混杂
    assert 纯英文 == 0, "仍有 %d 个函数纯英文形参（旧账 70 个）" % 纯英文
    assert 纯中文 >= 160, "纯中文形参数异常：%d" % 纯中文


def test_L256_遗留_范围直通Python内建只收位置参数():
    """已知遗留：`范围` 映射到 range，关键字调用仍 TypeError；位置式可用。

    这条**明写为遗留**而不是假绿：将来 codegen 补了 `范围` 的别名翻译，
    本判据会转红，提醒同步改账本 §二十七·四。
    """
    关键字 = _跑('打印 转字符串(范围(起始=0, 结束=3))\n')
    assert 关键字.returncode != 0, "`范围` 已支持关键字？请同步刷新账本遗留段"
    assert "takes no keyword arguments" in 关键字.stderr, 关键字.stderr[-500:]
    位置 = _跑('打印 转字符串(范围(0, 3))\n')
    assert 位置.returncode == 0, 位置.stderr[-500:]
    assert 位置.stdout.strip() == "range(0, 3)", 位置.stdout


# ---------------------------------------------------------------------------
# L-257 · 归约开箱可运行
# ---------------------------------------------------------------------------

def test_L257_归约开箱可运行():
    """2 参 / 3 参都要真跑出结果（旧账：name 'functools' is not defined）。"""
    for 源, 期望 in [
        ('段落 求和(a, b):\n  返回 a + b\n打印 转字符串(归约([1, 2, 3], 求和, 0))\n', "6"),
        ('段落 求和(a, b):\n  返回 a + b\n打印 转字符串(归约([1, 2, 3], 求和))\n', "6"),
    ]:
        r = _跑(源)
        assert r.returncode == 0, "rc=%s stderr=%s" % (r.returncode, r.stderr[-800:])
        assert "functools" not in r.stderr, r.stderr[-500:]
        assert r.stdout.strip() == 期望, r.stdout


# ---------------------------------------------------------------------------
# L-258 · 映射 / 筛选 返回列表
# ---------------------------------------------------------------------------

def test_L258_映射筛选返回列表():
    r = _跑(
        '打印 转字符串(映射([1, 2], 接收 甲：返回 甲 乘 2))\n'
        '打印 转字符串(筛选([1, 2, 3], 接收 甲：返回 甲 大于 1))\n'
    )
    assert r.returncode == 0, "rc=%s stderr=%s" % (r.returncode, r.stderr[-800:])
    assert r.stdout.split("\n")[:2] == ["[2, 4]", "[2, 3]"], r.stdout
    assert "object at 0x" not in r.stdout, "仍泄漏 CPython 迭代器 repr：%r" % r.stdout


# ---------------------------------------------------------------------------
# L-259 · 解析时间 ISO / 失败抛错 / 试解析显式返回空
# ---------------------------------------------------------------------------

def test_L259_解析时间ISO与失败抛错():
    iso = _跑('从 时间管理 导入 解析时间\n打印 转字符串(解析时间("2026-10-30T15:00:00"))\n')
    assert iso.returncode == 0, iso.stderr[-800:]
    assert "tm_year=2026" in iso.stdout and "tm_hour=15" in iso.stdout, iso.stdout

    空格 = _跑('从 时间管理 导入 解析时间\n打印 转字符串(解析时间("2026-10-30 15:00:00"))\n')
    assert 空格.returncode == 0, 空格.stderr[-800:]
    assert "tm_year=2026" in 空格.stdout, 空格.stdout

    失败 = _跑('从 时间管理 导入 解析时间\n打印 转字符串(解析时间("不是时间"))\n')
    assert 失败.returncode != 0, "解析失败不许静默返回空"
    assert 失败.stdout.strip() == "", "失败路径不许产出值：%r" % 失败.stdout
    assert "值错误" in 失败.stderr and "解析时间失败" in 失败.stderr, 失败.stderr[-800:]

    试探 = _跑('从 时间管理 导入 试解析时间\n打印 转字符串(试解析时间("不是时间"))\n')
    assert 试探.returncode == 0, 试探.stderr[-800:]
    assert 试探.stdout.strip() == "空", 试探.stdout


# ---------------------------------------------------------------------------
# L-260 · 切片赋值
# ---------------------------------------------------------------------------

def test_L260_切片赋值成立():
    r = _跑("设 表 为 [1, 2, 3, 4]\n设 表[0:2] 为 [9, 9]\n打印 转字符串(表)\n")
    assert r.returncode == 0, "rc=%s stderr=%s" % (r.returncode, r.stderr[-800:])
    assert r.stdout.strip() == "[9, 9, 3, 4]", r.stdout
    读 = _跑("设 表 为 [1, 2, 3, 4]\n打印 转字符串(表[1:3])\n")
    assert 读.returncode == 0 and 读.stdout.strip() == "[2, 3]", 读.stdout


# ---------------------------------------------------------------------------
# L-261 · 伪名不在 linter 清单；真写法可用
# ---------------------------------------------------------------------------

def _装载_linter清单():
    路径 = os.path.join(_ROOT, "src", "linter", "builtins.py")
    spec = importlib.util.spec_from_file_location("_r220_linter_builtins", 路径)
    模块 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(模块)
    return 模块


def test_L261_伪名不在清单且真写法可用():
    模块 = _装载_linter清单()
    名单 = set(模块.get_builtin_names())
    assert "集合创建" not in 名单, "`集合创建` 已裁定为臆造名，清单不许登记"
    assert "字典设置默认值" not in 名单, "`字典设置默认值` 清单里有、实现里没有，属假绿"

    假名 = _跑('设 s 为 集合创建([1, 2, 2, 3])\n打印 转字符串(s)\n')
    assert 假名.returncode != 0, "`集合创建` 竟然能跑？须复核 T-0203 的裁定"
    assert ("name '集合创建' is not defined" in 假名.stderr
            or "NameError" in 假名.stderr), 假名.stderr[-500:]

    真名 = _跑('打印 转字符串(集合([1, 2, 2, 3]))\n')
    assert 真名.returncode == 0, 真名.stderr[-800:]
    assert 真名.stdout.strip() == "{1, 2, 3}", 真名.stdout


# ---------------------------------------------------------------------------
# L-262 · 两腿参数列表口径一致
# ---------------------------------------------------------------------------

def test_L262_两腿参数列表一致():
    源 = "打印 转字符串(参数列表())\n"
    转译 = _跑(源, 实参=["甲", "乙"])
    assert 转译.returncode == 0, 转译.stderr[-800:]
    assert 转译.stdout.strip() == '["甲", "乙"]', 转译.stdout

    原生 = _跑(源, 实参=["甲", "乙"], 后端="native", 超时=600)
    if 原生.returncode != 0 and ("原生编译失败" in 原生.stderr or "无法" in 原生.stderr):
        pytest.skip("本机原生腿不可用（非口径问题）：%s" % 原生.stderr[-200:])
    assert 原生.returncode == 0, 原生.stderr[-800:]
    assert 原生.stdout.strip() == 转译.stdout.strip(), (
        "两腿 `参数列表()` 口径仍不一致：转译=%r 原生=%r" % (转译.stdout, 原生.stdout)
    )