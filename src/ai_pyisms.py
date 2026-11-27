# -*- coding: utf-8 -*-
"""AI 惯性诊断：把「Python 习惯写法」在动语法分析器之前就认出来（D1xx）。

为什么需要这个模块
------------------
``light ai check --json`` 拿到 ``def 问候():`` 时，词法器把 ``def`` 当普通标识符，
真报错落在 ``':'`` 上（``无法识别的语法元素：':'。``），于是
``src/diagnostics/registry.py`` 的自由文本正则归因不上，CLI 只能落 ``L0000``
占位码——agent 回头去改冒号，白烧 3–4 轮。本模块在**源码**上做一次静态扫描，
按 token 序列认出「哪一行、第几列、错了什么、整行该换成什么」，供
``registry`` 归成 D1xx 真码。

设计红线
--------
* 纯标准库；**只读** lexer 的 token，不改 lexer / parser / keywords 的任何行为。
* 按 token 序列匹配，**不拿正则扫全文**：字符串字面量与注释在交给判定逻辑之前
  就被逐字符替换成空格（等长，列号不变），所以注释里的 ``if``、字符串里的
  ``'def'`` 不会误报（``docs/AI编程指南.md`` 六、错误 1 的正例文本里，
  ``'def'`` 就是一个字符串 token，本模块对它一律无感）。
* 每条 ``replacement`` 要么是**能直接替换的整行文本**，要么留空串并在
  ``message`` 里给正确写法；**绝不编一个错的替换**。同一行上的机械写法
  （``&&`` / ``True`` / ``print`` / 单引号 …）会一次性全部换掉，所以照任意一条
  的 ``replacement`` 贴回去，整行都是对的。
* 不升级 severity：指南里写「部分版本不支持 / 静默不生效 / 不要混用」的坑用
  ``warning``，真编译不过或运行必炸的用 ``error``（口径见各条 ``docs`` 出处）。

对外接口
--------
::

    from src.ai_pyisms import scan
    for f in scan(source):
        print(f.line, f.column, f.code, f.message, f.replacement)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "Finding",
    "CodeInfo",
    "PYISM_SEGMENT",
    "PYISM_CODE_PATTERN",
    "PYISM_CODES",
    "code_info",
    "all_codes",
    "scan",
]

#: 码段：D1xx = 「AI 把 Python 习惯写进了光明源码」。与 L1–L5 编译器码段并列，
#: 由 ``src/diagnostics/registry.py`` 的 ``PYISM_DIAGNOSTICS`` 收编。
PYISM_SEGMENT = "D1"

#: ``D1xx``：段位 D1 + 两位序号（D101–D199），与 L 码的 ``L[1-5]NNN`` 互不重叠。
PYISM_CODE_PATTERN = re.compile(r"D1\d{2}")

_GUIDE = "docs/AI编程指南.md"


@dataclass(frozen=True)
class CodeInfo:
    """一条 D1xx 的元数据（码表事实源，``registry`` 据此建 ``DiagnosticSpec``）。

    ``Finding`` 只带任务卡规定的 8 个字段，severity / 出处在这里查，
    保证「一条码一个 severity」，不会同一个码既 warning 又 error。
    """

    code: str
    name: str
    title: str
    hint: str
    severity: str
    docs: str


# ---------------------------------------------------------------------------
# 码表：14 条高频错误全覆盖（docs/AI编程指南.md §六）+ 必要的细项拆分
# ---------------------------------------------------------------------------
PYISM_CODES: Tuple[CodeInfo, ...] = (
    CodeInfo(
        code="D101", name="PY_DEF",
        title="用 def / function 定义函数",
        hint="光明用「段落」定义函数：段落 名 接收 参数：",
        severity="error", docs=_GUIDE + ":621-632（六、错误 1）",
    ),
    CodeInfo(
        code="D102", name="PY_IF",
        title="用 if 写条件",
        hint="条件判断用「如果 条件：」",
        severity="error", docs=_GUIDE + ":634-645（六、错误 2）",
    ),
    CodeInfo(
        code="D103", name="PY_ELIF",
        title="用 elif 写多分支",
        hint="多分支用「否则如果」（别名「否则若」）",
        severity="error", docs=_GUIDE + ":634-645（六、错误 2）",
    ),
    CodeInfo(
        code="D104", name="PY_ELSE",
        title="用 else 写兜底分支",
        hint="兜底分支用「否则：」",
        severity="error", docs=_GUIDE + ":634-645（六、错误 2）",
    ),
    CodeInfo(
        code="D105", name="PY_FOR",
        title="用 for … in … 写遍历",
        hint="遍历用「遍历 元素 于 序列：」，介词用 于",
        severity="error", docs=_GUIDE + ":634-645（六、错误 2）",
    ),
    CodeInfo(
        code="D106", name="PY_WHILE",
        title="用 while 写循环",
        hint="条件循环用「当 条件：」",
        severity="error", docs=_GUIDE + ":634-645（六、错误 2）",
    ),
    CodeInfo(
        code="D107", name="PY_RETURN",
        title="用 return 返回值",
        hint="返回值用「返回 表达式」",
        severity="error", docs=_GUIDE + ":621-632（六、错误 1）、§2.4",
    ),
    CodeInfo(
        code="D108", name="PY_BOOL",
        title="布尔/空值写成 True / False / None",
        hint="字面量是 真 / 假 / 空（可作值，不可作变量名）",
        severity="warning", docs=_GUIDE + ":647-658（六、错误 3）",
    ),
    CodeInfo(
        code="D109", name="PY_LOGIC",
        title="逻辑运算符写成 && / || / !",
        hint="逻辑运算用「且」「或」「非」；!= / >= / <= 是合法比较符，不动",
        severity="error", docs=_GUIDE + ":660-669（六、错误 4）、§2.2",
    ),
    CodeInfo(
        code="D110", name="PY_LOGIC_WORD",
        title="逻辑运算符写成 and / or / not",
        hint="and→且、or→或、not→非、not in→不在",
        severity="error", docs=_GUIDE + ":660-669（六、错误 4）、§2.2",
    ),
    CodeInfo(
        code="D111", name="PY_COLLECTION",
        title="用 新建列表() / 新建字典() 创建空容器",
        hint="空列表写 列表创建() 或 []，空字典写 字典创建() 或 {}",
        severity="warning", docs=_GUIDE + ":671-679（六、错误 5）、§2.1",
    ),
    CodeInfo(
        code="D112", name="PY_COLLECTION_PY",
        title="用 Python 的 list() / dict() 创建容器",
        hint="列表用 列表创建() 或 []，字典用 字典创建() 或 {}",
        severity="error", docs=_GUIDE + ":671-679（六、错误 5）、§2.1",
    ),
    CodeInfo(
        code="D113", name="PY_APPEND",
        title="列表追加写成函数调用 追加(列表, 项)",
        hint="追加是方法调用：列表.追加(项)",
        severity="warning", docs=_GUIDE + ":681-688（六、错误 6）",
    ),
    CodeInfo(
        code="D114", name="PY_FOR_PREP",
        title="遍历语句里用了推导式介词 之",
        hint="遍历语句用「于」，推导式才用「之 / 在」",
        severity="warning", docs=_GUIDE + ":690-699（六、错误 7）、§2.3",
    ),
    CodeInfo(
        code="D115", name="PY_STRING",
        title="字符串用单引号",
        hint="字符串字面量统一用双引号",
        severity="warning", docs=_GUIDE + ":701-708（六、错误 8）、:924-925",
    ),
    CodeInfo(
        code="D116", name="PY_INIT",
        title="构造函数写成 __init__",
        hint="构造函数名是「初始化」：段落 初始化 接收 参数：",
        severity="warning", docs=_GUIDE + ":710-720（六、错误 9）",
    ),
    CodeInfo(
        code="D117", name="PY_SELF",
        title="实例属性没写 己.",
        hint="实例属性写成 设 己.属性 为 值；只写 名字 是局部变量",
        severity="warning", docs=_GUIDE + ":722-733（六、错误 10）",
    ),
    CodeInfo(
        code="D118", name="PY_IMPORT",
        title="导入用英文模块名",
        hint="模块名是中文：从 数学 导入 平方根",
        severity="error", docs=_GUIDE + ":735-742（六、错误 11）、§2.6",
    ),
    CodeInfo(
        code="D119", name="PY_PRINT",
        title="输出用 print 而不是 打印",
        hint="输出用「打印(...)」",
        severity="error", docs=_GUIDE + ":744-751（六、错误 12）",
    ),
    CodeInfo(
        code="D120", name="PY_LAMBDA",
        title="用 lambda 写匿名函数",
        hint="lambda 不支持：先写命名段落，再把段名当值传",
        severity="error", docs=_GUIDE + ":753-768（六、错误 13）",
    ),
    CodeInfo(
        code="D121", name="PY_WITH",
        title="用 with 管理资源",
        hint="with 不支持：用 尝试 / 最终 手写清理",
        severity="error", docs=_GUIDE + ":770-786（六、错误 14）",
    ),
)

_BY_CODE: Dict[str, CodeInfo] = {info.code: info for info in PYISM_CODES}


def code_info(code: str) -> CodeInfo:
    """按码查元数据；未登记抛 ``KeyError``（不返回空，免得下游写出假码）。"""
    try:
        return _BY_CODE[code]
    except KeyError:
        raise KeyError(f"未登记的 D1xx 码：{code!r}") from None


def all_codes() -> Tuple[str, ...]:
    """按码表顺序返回全部 D1xx 码。"""
    return tuple(info.code for info in PYISM_CODES)


# ---------------------------------------------------------------------------
# Finding：任务卡固定的 8 个字段
# ---------------------------------------------------------------------------
@dataclass
class Finding:
    """一条「这里写成了 Python」的发现。

    字段口径（与任务卡 T-0457 一致）：

    * ``line`` / ``column`` / ``end_column``：1-based **字符**列。``column`` 是
      第一个错误元素的起始列，``end_column`` 是它的**开区间**结束列
      （即 ``column + len(wrong)``）。
    * ``wrong`` / ``right``：第一个错误元素及其正确写法（给人看）。
    * ``message``：一句中文，说清「这行要改成什么」。
    * ``replacement``：**整行级**替换后的文本（含原缩进，可原样套 ``light patch``）；
      整行无法安全重写时为空串，此时 ``message`` 必须给出正确写法。
    """

    line: int
    column: int
    end_column: int
    code: str
    wrong: str
    right: str
    message: str
    replacement: str


# ---------------------------------------------------------------------------
# 行级预处理：把字符串字面量与注释抹成空格（等长，列号不变）
# ---------------------------------------------------------------------------
@dataclass
class _LineState:
    """跨行状态：只跟踪未闭合的三引号。"""

    triple: str = ""


def _mask_line(raw: str, state: _LineState) -> Tuple[str, str, List[Tuple[int, int]]]:
    """返回 ``(可见代码, 注释, 单引号字面量区间)``。

    ``可见代码`` 与 ``raw`` **等长**：字符串字面量与注释的每个字符都换成空格，
    因此 token 的列号可以直接对回原文。「单引号字面量区间」是含引号的
    ``[start, end)`` 半开区间，供单引号规则改写用。
    """
    n = len(raw)
    visible = list(raw)
    singles: List[Tuple[int, int]] = []
    i = 0
    while i < n:
        if state.triple:
            close = raw.find(state.triple, i)
            if close < 0:
                for k in range(i, n):
                    visible[k] = " "
                return "".join(visible), "", singles
            for k in range(i, close + 3):
                visible[k] = " "
            state.triple = ""
            i = close + 3
            continue
        ch = raw[i]
        if ch == "#":
            for k in range(i, n):
                visible[k] = " "
            return "".join(visible), raw[i:], singles
        if ch in "\"'":
            triple = ch * 3
            if raw.startswith(triple, i):
                close = raw.find(triple, i + 3)
                if close < 0:
                    state.triple = triple
                    for k in range(i, n):
                        visible[k] = " "
                    return "".join(visible), "", singles
                for k in range(i, close + 3):
                    visible[k] = " "
                i = close + 3
                continue
            j = i + 1
            while j < n:
                if raw[j] == "\\":
                    j += 2
                    continue
                if raw[j] == ch:
                    break
                j += 1
            end = min(j + 1, n)
            if ch == "'":
                singles.append((i, end))
            for k in range(i, end):
                visible[k] = " "
            i = end
            continue
        i += 1
    return "".join(visible), "", singles


_LEXER = None

#: 词法器不认识的字符（``&`` / ``|``）会让整行 tokenize 抛错；为了让同行里的
#: ``if`` / ``print`` 仍然能被认出，这里做一次**等长**归一化后再试一次。
_LEN_SAFE = (("&&", "且 "), ("||", "或 "), ("!", "非"))


def _lexer():
    """惰性取 ``Lexer``，兼容 ``src.ai_pyisms`` / ``ai_pyisms`` 两种导入方式。

    ``src/lexer.py`` 内部是 ``from tokens import ...``（绝对导入），因此它要求
    ``src/`` 在 ``sys.path`` 上；以仓库根为工作目录直跑时未必满足，这里兜一次
    **只加自己的目录**，不改别人的路径顺序、也不改 lexer 一行代码。
    """
    global _LEXER
    if _LEXER is not None:
        return _LEXER
    try:
        from .lexer import Lexer
    except ImportError:  # 以 src/ 为 sys.path 根，或 src 还不在 sys.path 上
        import os
        import sys

        src_dir = os.path.dirname(os.path.abspath(__file__))
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from lexer import Lexer  # type: ignore[no-redef]

    _LEXER = Lexer()
    return _LEXER


def _tokens(visible: str):
    """一行可见代码 → token 列表；连归一化都失败时返回 ``None``。"""
    if not visible.strip():
        return []
    lexer = _lexer()
    try:
        return lexer.tokenize(visible)
    except Exception:
        pass
    patched = visible
    for src, dst in _LEN_SAFE:
        patched = patched.replace(src, dst)
    try:
        return lexer.tokenize(patched)
    except Exception:
        return None


_SKIP_TYPES = frozenset({"NEWLINE", "INDENT", "DEDENT", "EOF"})


def _significants(tokens) -> List:
    """去掉 NEWLINE / INDENT / DEDENT / EOF，留下真正有内容的 token。"""
    return [t for t in tokens if t.type.name not in _SKIP_TYPES]


def _text(tok) -> str:
    """token 的源码文本（``value`` 非 str 时按字面量取串）。"""
    value = tok.value
    return value if isinstance(value, str) else str(value)


def _span(tok) -> Tuple[int, int]:
    """token 在行内的 ``[start, end)`` 下标（0-based）。"""
    start = tok.col - 1
    return start, start + len(_text(tok))


def _indent_of(raw: str) -> int:
    """行首缩进的字符数。"""
    return len(raw) - len(raw.lstrip(" \t"))


def _trim(text: str) -> str:
    """去首尾空白。"""
    return text.strip()


def _fullwidth_colon(text: str) -> str:
    """行尾 ASCII 冒号换全角（光明两种都收，文档主形式是全角）。"""
    body = text.rstrip()
    if body.endswith(":"):
        return body[:-1] + "："
    return body


def _assemble(body: str, comment: str) -> str:
    """正文（**已含缩进**）+ 注释，拼回一整行。"""
    line = body.rstrip()
    if not comment:
        return line
    return line + " " + comment


# ---------------------------------------------------------------------------
# 机械替换：一整行上的「就地换字」，一次做完，幂等
# ---------------------------------------------------------------------------
_PY_BOOLS = {"True": "真", "False": "假", "None": "空"}
_PY_LOGIC_WORDS = {"and": "且", "or": "或", "not": "非"}
_LOGIC_CHAR = {"&&": "且", "||": "或", "!": "非"}
_PY_COLLECTION_ALIAS = {"新建列表": "列表创建", "新建字典": "字典创建"}
_PY_COLLECTION_BUILTIN = {"list": "列表创建", "dict": "字典创建"}


def _find_logic(visible: str) -> List[Tuple[int, int, str]]:
    """在可见代码里找 ``&&`` / ``||`` / 单目 ``!``，返回 ``(start, end, 原文)``。"""
    hits: List[Tuple[int, int, str]] = []
    i, n = 0, len(visible)
    while i < n:
        two = visible[i:i + 2]
        if two in ("&&", "||"):
            hits.append((i, i + 2, two))
            i += 2
            continue
        if visible[i] == "!":
            prev = visible[i - 1] if i else ""
            nxt = visible[i + 1] if i + 1 < n else ""
            if nxt != "=" and prev not in "!<>=":
                hits.append((i, i + 1, "!"))
            i += 1
            continue
        i += 1
    return hits


def _edits(visible: str, toks, singles: Sequence[Tuple[int, int]]) -> List[Tuple[int, int, str]]:
    """汇总一行上的全部机械替换 ``(start, end, 新文本)``。"""
    out: List[Tuple[int, int, str]] = []

    for start, end, wrong in _find_logic(visible):
        repl = _LOGIC_CHAR[wrong]
        # 中文关键词和相邻标识符之间补空格：``!c`` → ``非 c``、``a&&b`` → ``a 且 b``
        if start > 0 and not visible[start - 1].isspace():
            repl = " " + repl
        if end < len(visible) and not visible[end].isspace():
            repl = repl + " "
        out.append((start, end, repl))

    for tok in toks:
        word = _text(tok)
        if word in _PY_BOOLS:
            s, e = _span(tok)
            out.append((s, e, _PY_BOOLS[word]))
        elif word in _PY_LOGIC_WORDS:
            s, e = _span(tok)
            if word == "not":
                tail = visible[e:].lstrip()
                if tail.startswith("in") and (len(tail) == 2 or not tail[2].isalnum()):
                    gap = len(visible[e:]) - len(visible[e:].lstrip())
                    out.append((s, e + gap + 2, "不在"))
                    continue
            out.append((s, e, _PY_LOGIC_WORDS[word]))
        elif word == "print" and _followed_by_paren(toks, tok):
            s, e = _span(tok)
            out.append((s, e, "打印"))
        elif word in _PY_COLLECTION_ALIAS:
            if _empty_call_at(toks, tok):
                s, e = _span(tok)
                out.append((s, e, _PY_COLLECTION_ALIAS[word]))
        elif word in _PY_COLLECTION_BUILTIN:
            if _empty_call_at(toks, tok):
                s, e = _span(tok)
                out.append((s, e, _PY_COLLECTION_BUILTIN[word]))

    for start, end in singles:
        # 单引号 → 双引号：只改两端的引号字符，内容原样保留。
        # 内容本身含双引号的跳过——换过去要转义，反而不如原样。
        if '"' in visible[start:end]:
            continue
        out.append((start, start + 1, '"'))
        out.append((end - 1, end, '"'))

    append_edit = _append_edit(toks)
    if append_edit is not None:
        # 结构改写（追加(列表, 项) → 列表.追加(项)）优先级最高：它包住的就地替换
        # 让位给它，改完由 _mechanical 再跑一轮把里面的字面量补掉。
        start, end, _repl = append_edit
        out = [x for x in out if not (start <= x[0] and x[1] <= end)]
        out.append(append_edit)
    return out


def _apply(raw: str, edits: Sequence[Tuple[int, int, str]]) -> str:
    """从后往前套替换；重叠的编辑只保留靠前的一条。"""
    out = raw
    last_start = len(raw) + 1
    for start, end, repl in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        if end > last_start:
            continue
        out = out[:start] + repl + out[end:]
        last_start = start
    return out


def _mechanical(raw: str, _redo: bool = True) -> str:
    """对一整行（不含注释）做全部机械替换，返回修好的行。

    幂等：换出来的形态（``且`` / ``真`` / ``打印`` / ``"..."``）不会再被匹配。
    唯一需要第二轮的是 ``追加(列表, 项)`` 这种**结构改写**：第一轮换成
    ``列表.追加(项)`` 后，项里若还有 ``True`` 之类，第二轮才看得见它。
    """
    state = _LineState()
    visible, _comment, singles = _mask_line(raw, state)
    tokens = _tokens(visible)
    toks = _significants(tokens) if tokens is not None else []
    out = _apply(raw, _edits(visible, toks, singles))
    if _redo and out != raw and _append_edit(toks) is not None:
        return _mechanical(out, _redo=False)
    return out


def _followed_by_paren(toks, tok) -> bool:
    idx = _index_of(toks, tok)
    return idx is not None and idx + 1 < len(toks) and toks[idx + 1].type.name == "LPAREN"


def _empty_call_at(toks, tok) -> bool:
    idx = _index_of(toks, tok)
    return (idx is not None and idx + 2 < len(toks)
            and toks[idx + 1].type.name == "LPAREN"
            and toks[idx + 2].type.name == "RPAREN")


def _index_of(toks, tok) -> Optional[int]:
    for idx, item in enumerate(toks):
        if item is tok:
            return idx
    return None


def _append_edit(toks) -> Optional[Tuple[int, int, str]]:
    """``追加(列表, 项)`` 整段换成 ``列表.追加(项)`` 的编辑；形状不对返回 None。"""
    if len(toks) != 6 or _text(toks[0]) != "追加":
        return None
    kinds = [t.type.name for t in toks]
    if kinds[1] != "LPAREN" or kinds[3] != "COMMA" or kinds[5] != "RPAREN":
        return None
    start = _span(toks[0])[0]
    end = _span(toks[5])[1]
    return start, end, "%s.追加(%s)" % (_text(toks[2]), _text(toks[4]))


# ---------------------------------------------------------------------------
# 作用域栈（只为了「实例属性没写 己.」这一条）
# ---------------------------------------------------------------------------
@dataclass
class _Block:
    """行级作用域栈的一帧：缩进 + 是否「初始化」+ 参数名。"""

    indent: int
    is_init: bool
    params: Tuple[str, ...]


def _split_params(text: str) -> Tuple[str, ...]:
    """``甲, 乙 = 1`` → ``('甲', '乙')``；只取名字，去掉默认值与类型标注。"""
    out: List[str] = []
    for raw in re.split(r"[,，]", text):
        name = re.split(r"[=:：]", raw, maxsplit=1)[0].strip()
        if name:
            out.append(name)
    return tuple(out)


def _push_block(stack: List[_Block], indent: int, toks, code: str) -> None:
    """段落头入栈：记下缩进、是否「初始化」、参数名清单。"""
    name = _text(toks[1]) if len(toks) > 1 else ""
    params: Tuple[str, ...] = ()
    for tok in toks:
        if _text(tok) == "接收":
            params = _split_params(code[_span(tok)[1]:].rstrip("：: \t"))
            break
    stack.append(_Block(indent=indent, is_init=(name == "初始化"), params=params))


# ---------------------------------------------------------------------------
# 行扫描
# ---------------------------------------------------------------------------
def _scan_line(number: int, raw: str, state: _LineState, stack: List[_Block]) -> List[Finding]:
    """扫一行，返回这一行上的全部发现（同一码同一行只报一次）。"""
    visible, comment, singles = _mask_line(raw, state)
    code = raw if not comment else raw[:len(raw) - len(comment)]
    tokens = _tokens(visible)
    if tokens is None:
        # 连等长归一化都过不了：只保留能靠纯字符判定的 && / || / !。
        return _logic_only(number, raw, visible, comment)

    toks = _significants(tokens)
    if not toks:
        return []

    indent = _indent_of(raw)
    # 整行的「完整修复」：头部关键字规则命中时用它自己产出的行（里面还会再跑一次
    # 机械替换），否则只做机械替换。同一行上所有发现共用这同一份 replacement，
    # 所以 agent 照任意一条贴回去都不会留下半截 Python 写法。
    # 惰性求值：绝大多数行没有发现，不该为它们多跑一次分词。
    head_fix: Optional[str] = None
    cached_fix: List[str] = []
    findings: List[Finding] = []

    def line_fix() -> str:
        if head_fix is not None:
            return head_fix
        if not cached_fix:
            cached_fix.append(_mechanical(code))
        return cached_fix[0]

    def emit(code_: str, start: int, end: int, wrong: str, right: str,
             message: str, replacement: Optional[str] = None) -> None:
        if any(f.code == code_ for f in findings):
            return
        text = line_fix() if replacement is None else replacement
        findings.append(Finding(
            line=number, column=start + 1, end_column=end + 1, code=code_,
            wrong=wrong, right=right, message=message,
            replacement=_assemble(text, comment) if text else "",
        ))

    head = toks[0]
    head_text = _text(head)

    # ---- 段落 / 类：作用域栈 + __init__ --------------------------------
    if head_text in ("段落", "函数", "段") and len(toks) >= 2:
        name_tok = toks[1]
        if _text(name_tok) == "__init__":
            rest = _trim(code[_span(name_tok)[1]:])
            body = "段落 初始化" + (" " + rest if rest else "")
            fix = _mechanical(" " * indent + _fullwidth_colon(body))
            head_fix = fix
            s, e = _span(name_tok)
            emit("D116", s, e, "__init__", "初始化",
                 "构造函数名是「初始化」：`段落 初始化 接收 参数：`；写 __init__ 不会被当成构造函数。",
                 fix)
        _push_block(stack, indent, toks, code)

    # ---- def / function -----------------------------------------------
    elif head_text in ("def", "function") and len(toks) >= 2:
        fix = _def_replacement(code, toks, indent)
        head_fix = fix or None
        emit("D101", *_span(head), head_text, "段落",
             "函数定义用「段落 名 接收 参数：」；`def` 不是光明关键字，"
             "报错常常落在行尾的 `:` 上，别去修冒号。", fix)

    # ---- if / elif / else ---------------------------------------------
    elif head_text == "if":
        fix = _cond_replacement(code, toks, indent, "如果")
        head_fix = fix or None
        emit("D102", *_span(head), "if", "如果",
             "条件判断用「如果 条件：」，光明没有 if。", fix)
    elif head_text == "elif":
        fix = _cond_replacement(code, toks, indent, "否则如果")
        head_fix = fix or None
        emit("D103", *_span(head), "elif", "否则如果",
             "多分支用「否则如果 条件：」（别名「否则若」）。", fix)
    elif head_text == "else":
        fix = _mechanical(" " * indent + "否则：")
        head_fix = fix
        emit("D104", *_span(head), "else", "否则",
             "兜底分支用「否则：」。", fix)

    # ---- for … in … ----------------------------------------------------
    elif head_text == "for":
        fix = _for_replacement(code, toks, indent)
        head_fix = fix or None
        emit("D105", *_span(head), "for", "遍历",
             ("遍历写「遍历 元素 于 序列：」；range 这类英文函数名也要换成中文（范围）。"
              if any(_text(t) == "in" for t in toks)
              else "遍历写「遍历 元素 于 序列：」，Python 的 for … in … 不成立。"), fix)

    # ---- while ---------------------------------------------------------
    elif head_text == "while":
        fix = _cond_replacement(code, toks, indent, "当")
        head_fix = fix or None
        emit("D106", *_span(head), "while", "当",
             "条件循环用「当 条件：」。", fix)

    # ---- return --------------------------------------------------------
    elif head_text == "return":
        rest = _trim(code[_span(head)[1]:])
        fix = _mechanical(" " * indent + "返回" + (" " + rest if rest else ""))
        head_fix = fix
        emit("D107", *_span(head), "return", "返回",
             "返回值用「返回 表达式」，不是 return。", fix)

    # ---- with ----------------------------------------------------------
    elif head_text == "with":
        emit("D121", *_span(head), "with", "尝试 / 最终",
             "with 不支持：用 `尝试:` 打开、`最终:` 里关闭；简单读写直接用 读取文件() / 写入文件()。",
             "")

    # ---- 从 <英文模块> 导入 --------------------------------------------
    if head_text == "从" and len(toks) >= 3 and _text(toks[2]) == "导入":
        module = _text(toks[1])
        if module.isascii() and module not in _known_ascii_modules():
            cn = _EN_MODULE_MAP.get(module, "")
            s, e = _span(toks[1])
            emit("D118", s, e, module, cn or "中文模块名",
                 "标准库模块名是中文"
                 + ("（`%s` → `%s`）" % (module, cn) if cn
                    else "，`%s` 不在模块清单里；对照 docs/STDLIB_REFERENCE.md 查中文名" % module),
                 _mechanical(code[:s] + (cn or module) + code[e:]) if cn else "")

    # ---- print( --------------------------------------------------------
    for tok in toks:
        if _text(tok) == "print" and _followed_by_paren(toks, tok):
            s, e = _span(tok)
            emit("D119", s, e, "print", "打印",
                 "输出用「打印(...)」，光明没有 print。")

    # ---- lambda --------------------------------------------------------
    for tok in toks:
        if _text(tok) == "lambda":
            s, e = _span(tok)
            emit("D120", s, e, "lambda", "命名段落",
                 "lambda 不支持：先写 `段落 名 接收 参数：`，再把段名当值传（排序 key 也一样）。",
                 "")

    # ---- True / False / None -------------------------------------------
    for tok in toks:
        if _text(tok) in _PY_BOOLS:
            s, e = _span(tok)
            emit("D108", s, e, _text(tok), _PY_BOOLS[_text(tok)],
                 "布尔/空值是 真 / 假 / 空 三个字面量（True / False / None 不是字面量）。")

    # ---- && || ! -------------------------------------------------------
    for start, end, wrong in _find_logic(visible):
        emit("D109", start, end, wrong, _LOGIC_CHAR[wrong],
             "逻辑运算用「且」「或」「非」；光明没有 && / || / !（!= 是合法比较符）。")

    # ---- and / or / not ------------------------------------------------
    for tok in toks:
        if _text(tok) in _PY_LOGIC_WORDS:
            s, e = _span(tok)
            emit("D110", s, e, _text(tok), _PY_LOGIC_WORDS[_text(tok)],
                 "逻辑运算用「且」「或」「非」（Python 的 and / or / not 不是关键字）。")

    # ---- 新建列表() / 新建字典() / list() / dict() ---------------------
    for tok in toks:
        word = _text(tok)
        if word in _PY_COLLECTION_ALIAS and _empty_call_at(toks, tok):
            s, e = _span(tok)
            emit("D111", s, e, word, _PY_COLLECTION_ALIAS[word],
                 "指南里 `新建列表()/新建字典()` 是反例：空列表写 `列表创建()` 或 `[]`，"
                 "空字典写 `字典创建()` 或 `{}`。")
        elif word in _PY_COLLECTION_BUILTIN and _empty_call_at(toks, tok):
            s, e = _span(tok)
            emit("D112", s, e, word, _PY_COLLECTION_BUILTIN[word],
                 "`%s()` 是 Python 写法：空列表写 `列表创建()` 或 `[]`，"
                 "空字典写 `字典创建()` 或 `{}`。" % word)

    # ---- 追加(列表, 项) -------------------------------------------------
    append_edit = _append_edit(toks)
    if append_edit is not None:
        target, item = _text(toks[2]), _text(toks[4])
        s, e = _span(toks[0])
        emit("D113", s, e, "追加", target + ".追加",
             "追加是方法调用：`%s.追加(%s)`；`追加(列表, 项)` 会被误映射到文件模式常量。"
             % (target, item))

    # ---- 遍历 之 -------------------------------------------------------
    if head_text == "遍历":
        for tok in toks:
            if _text(tok) == "之":
                s, e = _span(tok)
                emit("D114", s, e, "之", "于",
                     "遍历语句的介词用「于」；「之 / 在」是推导式用的，混用会踩坑。",
                     _mechanical(code[:s] + "于" + code[e:]))

    # ---- 单引号字符串 ---------------------------------------------------
    for start, end in singles:
        text = raw[start:end]
        if '"' in text[1:-1]:
            # 内容就是双引号本身（「判断这个字符是不是引号」那类写法）：换双引号要
            # 转义、更难读，不算 Python 惯性，不报也不改。
            continue
        emit("D115", start, end, text, _double_quote(text),
             "字符串统一用双引号（单引号部分版本解析不出来）。")

    # ---- 实例属性没写 己. -----------------------------------------------
    block = stack[-1] if stack else None
    if block is not None and block.is_init and len(toks) == 4:
        if _text(toks[0]) == "设" and _text(toks[2]) == "为":
            lhs, rhs = _text(toks[1]), _text(toks[3])
            if lhs == rhs and lhs in block.params:
                s, e = _span(toks[1])
                emit("D117", s, e, lhs, "己." + lhs,
                     "`设 %s 为 %s` 只是给局部变量赋值；实例属性要写 `设 己.%s 为 %s`。"
                     % (lhs, lhs, lhs, lhs),
                     _assemble(code[:s] + "己." + code[s:], "").rstrip())

    return findings


def _logic_only(number: int, raw: str, visible: str, comment: str) -> List[Finding]:
    """token 化彻底失败的行：只交 ``&& / || / !`` 这一种能纯字符判定的发现。"""
    hits = _find_logic(visible)
    if not hits:
        return []
    start, end, wrong = hits[0]
    return [Finding(
        line=number, column=start + 1, end_column=end + 1, code="D109",
        wrong=wrong, right=_LOGIC_CHAR[wrong],
        message="逻辑运算用「且」「或」「非」；光明没有 && / || / !（!= 是合法比较符）。",
        replacement=_assemble(_mechanical(raw), comment),
    )]


def _def_replacement(code: str, toks, indent: int) -> str:
    """``def 名(参数):`` → ``段落 名 接收 参数：``；形状不认识时留空串。"""
    if len(toks) < 2 or toks[-1].type.name != "COLON":
        return ""
    name = _text(toks[1])
    open_idx = next((i for i, t in enumerate(toks) if t.type.name == "LPAREN"), None)
    if open_idx is None:
        return ""
    depth, close_idx = 0, None
    for i in range(open_idx, len(toks)):
        kind = toks[i].type.name
        if kind == "LPAREN":
            depth += 1
        elif kind == "RPAREN":
            depth -= 1
            if depth == 0:
                close_idx = i
                break
    if close_idx is None:
        return ""
    params = _trim(code[_span(toks[open_idx])[1]:_span(toks[close_idx])[0]])
    body = "段落 " + name + (" 接收 " + params if params else "") + "："
    return _mechanical(" " * indent + body)


def _cond_replacement(code: str, toks, indent: int, keyword: str) -> str:
    """``if cond:`` / ``while cond:`` → ``如果 cond：`` / ``当 cond：``。"""
    if len(toks) < 2 or toks[-1].type.name != "COLON":
        return ""
    cond = _trim(code[_span(toks[1])[0]:])
    if not cond:
        return ""
    return _mechanical(" " * indent + keyword + " " + _fullwidth_colon(cond))


def _for_replacement(code: str, toks, indent: int) -> str:
    """``for x in xs:`` → ``遍历 x 于 xs：``。"""
    in_idx = next((i for i, t in enumerate(toks) if _text(t) == "in"), None)
    if in_idx is None or not (0 < in_idx < len(toks) - 1) or toks[-1].type.name != "COLON":
        return ""
    target = _trim(code[_span(toks[0])[1]:_span(toks[in_idx])[0]])
    seq = _trim(code[_span(toks[in_idx])[1]:])
    if not target or not seq:
        return ""
    return _mechanical(" " * indent + "遍历 " + target + " 于 " + _fullwidth_colon(seq))


def _double_quote(text: str) -> str:
    """``'a'`` → ``"a"``。"""
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return '"' + text[1:-1] + '"'
    return text


# ---------------------------------------------------------------------------
# 英文模块名（只认能复核的映射，绝不猜）
# ---------------------------------------------------------------------------
def _stdlib_stems() -> set:
    """仓库自带模块的文件名（``stdlib/*.light`` / ``stdlib/*.py`` …）。

    光明的模块名可以全是 ASCII（``从 JSONL 导入 逐行读JSONL`` 就是合法写法），
    所以「英文模块名」不能只看 ``NAME_TO_MODULE`` 的导出表：模块存在但一个名字
    都没导出时，那张表里查不到它。这里直接数目录，避免把真模块判死。
    """
    import os

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = set()
    for sub in ("stdlib", os.path.join("src", "stdlib")):
        try:
            names = os.listdir(os.path.join(root, sub))
        except OSError:
            continue
        for name in names:
            stem, ext = os.path.splitext(name)
            if ext in (".light", ".py") and stem.isascii():
                out.add(stem)
    return out


def _known_ascii_modules() -> set:
    """光明里真实存在的 ASCII 模块名（导出表 ∪ stdlib 文件名）。

    来源：``src/stdlib_name_map.py`` 的 ``NAME_TO_MODULE`` 值域（自动生成，
    不手抄）+ 模块目录自身，避免把 ``从 os 导入`` / ``从 JSONL 导入`` 这类合法
    写法判死。
    """
    global _KNOWN_MODULES
    if _KNOWN_MODULES is None:
        known = _stdlib_stems()
        try:
            try:
                from .stdlib_name_map import NAME_TO_MODULE
            except ImportError:
                from stdlib_name_map import NAME_TO_MODULE  # type: ignore[no-redef]

            known |= {m for m in NAME_TO_MODULE.values() if m.isascii()}
        except Exception:
            # 拿不到映射表就只补指南点过名的 math，绝不凭空判死其它模块名。
            known.add("math")
        _KNOWN_MODULES = known
    return _KNOWN_MODULES


_KNOWN_MODULES = None

#: 有中文正名、且文档点过名的英文模块（不猜，只收能复核的）。
_EN_MODULE_MAP: Dict[str, str] = {
    "math": "数学",
}


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
#: 嵌入块 / L4 外语引用块的开头（``引 Python:`` / ``嵌入 C:``）。块里的代码**本来
#: 就是**外语，扫它等于把 C 的 ``for (int i...)`` 当 Python 惯性报，必须整块跳过。
#: 口径与 ``lexer._tokenize_embed_block`` 一致：找不到 ``结束引``/``结束嵌入`` 时，
#: 块一直吃到文件末尾（词法器也是这么切的）。
_EMBED_OPEN = re.compile(r"^\s*(?:嵌入|引)\s*[A-Za-z][A-Za-z0-9_+#.]*\s*[:：]\s*$")
_EMBED_CLOSE = re.compile(r"^\s*结束(?:嵌入|引)\s*$")


def scan(source: str) -> List[Finding]:
    """扫一份源码，按 ``(行, 列)`` 顺序返回全部 D1xx 发现。

    * 只读：不改源码、不改 lexer / parser 行为。
    * 嵌入块（``引 Python:`` … ``结束引``）整块跳过——里面本来就是外语代码。
    * 同一行同一码最多一条（重复踩同一个坑不重复刷屏）。
    * 没有发现就返回空列表——**不造兜底发现**。
    """
    if not isinstance(source, str):
        raise TypeError(f"scan() 需要 str 源码，收到 {type(source).__name__}")

    state = _LineState()
    stack: List[_Block] = []
    findings: List[Finding] = []
    in_embed = False
    for number, raw in enumerate(source.splitlines(), 1):
        if in_embed:
            if _EMBED_CLOSE.match(raw):
                in_embed = False
            continue
        if _EMBED_OPEN.match(raw):
            in_embed = True
            continue
        if not raw.strip():
            continue
        indent = _indent_of(raw)
        while stack and indent <= stack[-1].indent:
            stack.pop()
        findings.extend(_scan_line(number, raw, state, stack))
    findings.sort(key=lambda f: (f.line, f.column, f.code))
    return findings
