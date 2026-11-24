"""T-0444：中文标识符含关键字（如「定义」）被词法截断的边界回归。

## 缺陷

中文标识符中间夹着关键字（本卡用 `定义`）时，同一串字符在**不同上下文**被切成
不同 token 序列：

    · 声明处 `设 未定义甲 为 9` → 预扫描整体登记，IDENTIFIER('未定义甲')；
    · 使用处 `打印(未定义甲)`   → IDENTIFIER('未') + KEYWORD('定义') + IDENTIFIER('甲')。

于是「能定义、不能用」，运行期报 `name '未' is not defined`（名字被截断），而
`light check` 照报「语法检查通过」——check 绿 / run 红，且报错名与源码对不上，
排查方向被带偏。

## 本卡采用的设计（方案 1：整体识别）

标识符优先整体成词：汉字游程里的 `定义` 处于词中/词尾时并入标识符，只有**独立
出现**（词首且后不接汉字，或两侧有空白）时才是关键字。实现上把 `定义` 从后缀位置
排除集 `_P0A_SUFFIX_SPLIT_KW` 中移出，与该规则下其余多字非运算符关键字同口径。
依据：`定义` 作语句头（`定义 宏 X 为 ...`）恒在语句起始位置（scan_pos==0），由第一层
最长匹配直接发 KEYWORD，词中/词尾不存在真语句头，故原排除项没有保护任何合法语法。

未采用方案 2（词法期报「标识符不得包含关键字」）：那会把 `参数定义`、`未定义甲` 这类
自然中文名字连同**已声明**的合法用法（判据 3）一起判死，并需改语法文档口径。

## 判据对应与判别力（反证实测）

把 `定义` 加回 `_P0A_SUFFIX_SPLIT_KW`（回到「关键字优先切分」）后本文件实测：
第 1、2、4 条与 token 断言 **3 红**，第 3 条仍绿。

第 3 条（声明后使用 → 9）在修前也成立，原因是 `_scan_user_definitions` 会把
`设 X` 声明的名字整体登记进白名单，声明与使用都能整体成词；它守的是「声明/使用
一致性」不被后续改动打破，不是本次截断的判别器。卡面「反证：第 3 条必须真红」
与实测不符，此处按实测记录，不用假断言凑（见 .hive/summary.md）。

第 4 条按「check 与 run 必须看到同一个完整标识符」落地：check 是静态语法/类型
检查、不做名字解析（linter 不在本卡允许路径内），所以「未声明名字 check 绿 / run 红」
是语言现状、不是本卡的截断缺陷；本卡要保证的是 check 的通过结论**不是建立在被截断
的 token 上**——run 报出的名字必须与 check 词法所见标识符同为源码里的完整串。
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from lexer import Lexer  # noqa: E402

CLI = os.path.join(ROOT, "cli", "light.py")


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #

def _tokens(source: str):
    """词法结果（去掉 NEWLINE/EOF），用 (类型名, 值) 便于断言。"""
    return [(t.type.name, t.value) for t in Lexer(source).tokenize()
            if t.type.name not in ("NEWLINE", "EOF")]


def _run_cli(tmp_path, action: str, source: str, name: str = "probe.light"):
    """在仓根跑 `python cli/light.py <action> <file>`，返回 CompletedProcess。

    不用 shell / head / grep：Windows 上那些 POSIX 判据会直接 exit 255 假失败。
    """
    path = os.path.join(str(tmp_path), name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(source)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, CLI, action, path],
        cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=600, env=env,
    )


def _output(proc) -> str:
    return (proc.stdout or "") + (proc.stderr or "")


def _program(body: str) -> str:
    """包一层最小可运行程序（段落 主 + 调用）。"""
    return "段落 主():\n" + body + "  返回 0\n主()\n"


# --------------------------------------------------------------------------- #
# 判据 1：`甲定义乙` 未声明 → 报错名字必须完整
# --------------------------------------------------------------------------- #

def test_甲定义乙_未声明_报错名完整(tmp_path):
    proc = _run_cli(tmp_path, "run", _program("  打印(甲定义乙)\n"), "k.light")
    out = _output(proc)

    assert proc.returncode != 0, f"未声明标识符必须运行失败，实际 rc=0，输出：{out}"
    assert "name '甲' is not defined" not in out, (
        f"标识符仍被截断成 甲（关键字优先切分未修），实际输出：{out}")
    assert "name '甲定义乙' is not defined" in out, f"报错名不是完整标识符，实际输出：{out}"


# --------------------------------------------------------------------------- #
# 判据 2：`未定义甲` 未声明 → 报错名字必须完整
# --------------------------------------------------------------------------- #

def test_未定义甲_未声明_报错名完整(tmp_path):
    proc = _run_cli(tmp_path, "run", _program("  打印(未定义甲)\n"), "kk.light")
    out = _output(proc)

    assert proc.returncode != 0, f"未声明标识符必须运行失败，实际 rc=0，输出：{out}"
    assert "name '未' is not defined" not in out, (
        f"标识符仍被截断成 未（关键字优先切分未修），实际输出：{out}")
    assert "name '未定义甲' is not defined" in out, f"报错名不是完整标识符，实际输出：{out}"


# --------------------------------------------------------------------------- #
# 判据 3：声明后使用必须一致（`设 未定义甲 为 9` + `打印(未定义甲)` → 9）
# --------------------------------------------------------------------------- #

def test_声明后使用一致_未定义甲(tmp_path):
    src = _program("  设 未定义甲 为 9\n  打印(未定义甲)\n")
    run = _run_cli(tmp_path, "run", src, "s.light")
    check = _run_cli(tmp_path, "check", src, "s_check.light")

    assert run.returncode == 0, (
        f"声明后使用必须能跑：check 看到整体名、run 却按关键字切分。输出：{_output(run)}")
    assert run.stdout.strip() == "9", f"应只打印 9，实际 stdout：{run.stdout!r}"
    assert check.returncode == 0, f"同一份源码 check 应通过，实际：{_output(check)}"
    # 声明处与使用处必须是同一个整体标识符
    values = [v for t, v in _tokens("设 未定义甲 为 9\n打印(未定义甲)") if t == "IDENTIFIER"]
    assert values == ["未定义甲", "未定义甲"], f"声明/使用切分不一致：{values}"


# --------------------------------------------------------------------------- #
# 判据 4：check→run 同源 —— run 报的名字必须与 check 看到的标识符同为完整串
# --------------------------------------------------------------------------- #

def test_check与run同源_同名且完整(tmp_path):
    """check 的「通过」不得建立在被截断的 token 上。

    修前：check 的标识符是 `甲`（被 `定义` 切断），run 报 `name '甲' is not defined`
    ——两边一起错，报错名与源码 `甲定义乙` 对不上 ⇒ 本条真红。
    修后：check 与 run 都看到 `甲定义乙`，check 仍绿（未声明是运行期问题），
    run 报的名字等于源码里的完整串 ⇒ 同源成立。
    """
    src = _program("  打印(甲定义乙)\n")
    check = _run_cli(tmp_path, "check", src, "d_check.light")
    run = _run_cli(tmp_path, "run", src, "d.light")

    ids = [v for t, v in _tokens(src) if t == "IDENTIFIER"]
    assert "甲定义乙" in ids, f"check 词法看到的标识符被截断：{ids}"
    assert "甲" not in ids, f"check 词法里仍有截断前缀 `甲`：{ids}"

    assert check.returncode == 0, f"语法层面应通过（未声明是运行期问题）：{_output(check)}"
    assert "name '甲定义乙' is not defined" in _output(run), (
        f"run 报的名字必须与 check 所见标识符一致，实际：{_output(run)}")


# --------------------------------------------------------------------------- #
# token 级断言：同一串字符在任何上下文都切成同一个标识符
# --------------------------------------------------------------------------- #

def test_token_级_词中词尾整体成词():
    assert _tokens("打印(甲定义乙)") == [
        ("KEYWORD", "打印"), ("LPAREN", "("),
        ("IDENTIFIER", "甲定义乙"), ("RPAREN", ")"),
    ]
    assert _tokens("甲定义乙") == [("IDENTIFIER", "甲定义乙")]
    assert _tokens("设 未定义甲 为 9") == [
        ("KEYWORD", "设"), ("IDENTIFIER", "未定义甲"),
        ("KEYWORD", "为"), ("NUMBER", 9),
    ]


def test_token_级_独立出现仍是关键字():
    """整体识别不等于取消关键字：空格分隔 / 词首独立出现时 定义 仍是 KEYWORD。"""
    assert _tokens("定义 甲") == [("KEYWORD", "定义"), ("IDENTIFIER", "甲")]
    assert _tokens("甲 定义 乙") == [
        ("IDENTIFIER", "甲"), ("KEYWORD", "定义"), ("IDENTIFIER", "乙"),
    ]
    # 定义 语句头（原文写法）依旧走关键字路径
    assert _tokens("定义 宏 加法 接收 甲，乙：")[0] == ("KEYWORD", "定义")


# --------------------------------------------------------------------------- #
# 回归：ASCII 标识符 / 无空格分词（compact notation）不得回退
# --------------------------------------------------------------------------- #

def test_回归_无空格分词与ASCII标识符():
    assert _tokens("设x为10") == [
        ("KEYWORD", "设"), ("IDENTIFIER", "x"), ("KEYWORD", "为"), ("NUMBER", 10),
    ]
    assert _tokens("甲加乙") == [
        ("IDENTIFIER", "甲"), ("KEYWORD", "加"), ("IDENTIFIER", "乙"),
    ]
    assert _tokens("total加1") == [
        ("IDENTIFIER", "total"), ("KEYWORD", "加"), ("NUMBER", 1),
    ]
    assert _tokens("abc_1") == [("IDENTIFIER", "abc_1")]
