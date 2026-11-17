# -*- coding: utf-8 -*-
"""R222-D / T-0380：归一（canonical）通道。

「工程体」过去只是若干规则名的集合，同一种语义有 8 类等价写法都被接受，
Agent 每次都要选一次。本模块把其中**确定性、无风险**的几类收敛到单一权威形态：

- L5001 标点：全角/中文标点统一为半角（字符串、注释内部一律不动）。
- L5002 运算符：`加/加上` 等中文别名统一为 ASCII 符号（`等于` 有歧义，跳过）。
- L5003 段落关键字：`段落` / `函数` / `段` 收敛为 style 对应的 canonical 形态。
- L5004 空白：行尾空白与行内多余的连续空格。

约定：
- 有歧义、不敢自动改的位置写入 ``skipped``，交给 Agent 判断，**不猜**。
- ``canonicalize`` 幂等：``canonicalize(canonicalize(src)[0])[0] ==
  canonicalize(src)[0]``。
- 不改变字符串字面量与注释的内容；不改写任何解析器语义。

为什么不把 `。` 换成 `.`：
    词法器把 `。` 映射成 ``PERIOD``，把 `.` 映射成 ``DOT``。`甲。长度` 解析失败，
    而 `甲.长度` 是成员访问；`段落 f():\n  返回 甲。` 若改成 `返回 甲.` 会立即报
    「期望成员名」。因此 `。` 只能按**语句分隔**语义归一为 `;`（实测 `返回 甲;` /
    `设 甲 为 1;` / `如果…。` 的 AST 与原文一致）。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Tuple

__all__ = [
    'CanonicalEdit',
    'SkippedEdit',
    'canonicalize',
    'edits_as_dicts',
]


# =============================================================================
# 常量
# =============================================================================

# 全角/中文标点 -> 半角。`《》`、`「」`、`『』` 不动：
# 前者是书名号专用 token，后者是字符串定界符。
PUNCT_MAP = {
    '。': ';',
    '，': ',',
    '、': ',',
    '；': ';',
    '：': ':',
    '（': '(',
    '）': ')',
    '【': '[',
    '】': ']',
    '｛': '{',
    '｝': '}',
    '！': '!',
}

# 中文运算符别名 -> ASCII 符号。按长度降序匹配，保证 `大于等于` 不被拆成 `大于`+`等于`。
OPERATOR_ALIASES = (
    ('大于等于', '>='),
    ('小于等于', '<='),
    ('不等于', '!='),
    ('不小于', '>='),
    ('不大于', '<='),
    ('加上', '+'),
    ('减去', '-'),
    ('乘以', '*'),
    ('除以', '/'),
    ('大于', '>'),
    ('小于', '<'),
    ('加', '+'),
    ('减', '-'),
    ('乘', '*'),
    ('除', '/'),
)

# 有歧义、只报告不改写的运算符词。
# `等于` 既可能是赋值（`设 甲 等于 1`）也可能是比较（`如果 甲 等于 乙`），
# 词法层无法区分，交给 Agent。
AMBIGUOUS_OPERATOR_WORDS = ('等于',)

FUNCTION_KEYWORDS = ('段落', '函数', '段')
FUNCTION_CANONICAL = {
    '工程体': '段落',
    '教学体': '段',
}
DEFAULT_STYLE = '工程体'

CODE_PUNCT = 'L5001'
CODE_OPERATOR = 'L5002'
CODE_FUNCTION = 'L5003'
CODE_WHITESPACE = 'L5004'

_STATE_CODE = 0
_STATE_STRING = 1
_STATE_COMMENT = 2


# =============================================================================
# 结果类型
# =============================================================================

@dataclass(frozen=True)
class CanonicalEdit:
    """一处可自动修复的归一。"""

    code: str
    line: int
    col: int
    before: str
    after: str
    reason: str


@dataclass(frozen=True)
class SkippedEdit:
    """一处有歧义、刻意跳过的归一。"""

    code: str
    line: int
    col: int
    text: str
    reason: str


def edits_as_dicts(edits) -> List[dict]:
    """把编辑/跳过记录转成可 JSON 序列化的 dict 列表。"""
    return [asdict(e) for e in edits]


# =============================================================================
# 字符工具
# =============================================================================

def _is_han(ch: str) -> bool:
    return '\u4e00' <= ch <= '\u9fff'


def _is_ident_char(ch: str) -> bool:
    """标识符字符：ASCII 字母数字、下划线、汉字。"""
    if _is_han(ch):
        return True
    return ch.isascii() and (ch.isalnum() or ch == '_')


def _is_sep(text: str, idx: int) -> bool:
    """idx 位置是否为「词边界」（越界或非标识符字符）。

    归一只在两侧都是显式边界时进行：`相加`、`函数1`、`模块` 这类词内出现
    的别名一律不碰（宁可漏归一，也不猜）。
    """
    if idx < 0 or idx >= len(text):
        return True
    return not _is_ident_char(text[idx])


def _is_operator_bound(text: str, idx: int) -> bool:
    """运算符归一要求两侧是空白/行边界。

    单字运算符（`加`/`减`…）与用户定义名同形（例如 `段落 加(a, b)`），
    只要不满足「两侧空白」就一律不碰。
    """
    if idx == 0:
        return True
    return text[idx - 1] in ' \t\n'


def _is_operator_bound_right(text: str, idx: int) -> bool:
    if idx >= len(text):
        return True
    return text[idx] in ' \t\n'


def _string_end(text: str, start: int) -> int:
    """返回从 start 开始的字符串字面量的结束位置（不含）。"""
    n = len(text)
    quote = text[start]

    # 中文引号字符串
    if quote in ('「', '『'):
        close = '」' if quote == '「' else '』'
        idx = text.find(close, start + 1)
        return n if idx < 0 else idx + 1

    # 三引号字符串（可跨行）
    triple = quote * 3
    if text.startswith(triple, start):
        idx = text.find(triple, start + 3)
        return n if idx < 0 else idx + 3

    idx = start + 1
    while idx < n:
        ch = text[idx]
        if ch == '\\' and idx + 1 < n:
            idx += 2
            continue
        if ch == quote:
            return idx + 1
        if ch == '\n':
            # 未闭合单行字符串：停在行尾，交给词法器报错，本模块不猜。
            return idx
        idx += 1
    return n


def _is_line_comment(text: str, idx: int) -> bool:
    """`//` 是注释还是整除运算符（与词法器同口径）。"""
    back = idx - 1
    while back >= 0 and text[back] in ' \t':
        back -= 1
    if back < 0:
        return True
    prev = text[back]
    # 前一个 token 是数字/标识符/)/]/字符串时是整除运算符。
    return not (_is_ident_char(prev) or prev in ')]"\'」』')


# =============================================================================
# 主流程
# =============================================================================

def canonicalize(source: str, style: str = DEFAULT_STYLE
                 ) -> Tuple[str, List[CanonicalEdit], List[SkippedEdit]]:
    """把 source 归一化。

    Args:
        source: 光明源码。
        style: ``工程体`` / ``教学体``，决定 `段落`/`函数`/`段` 的 canonical 形态。

    Returns:
        ``(new_source, edits, skipped)``。``edits`` 是已改写的记录，
        ``skipped`` 是有歧义、未改写的记录。
    """
    if style not in FUNCTION_CANONICAL:
        style = DEFAULT_STYLE
    func_canonical = FUNCTION_CANONICAL[style]

    n = len(source)
    out: List[str] = []
    states: List[int] = []
    edits: List[CanonicalEdit] = []
    skipped: List[SkippedEdit] = []

    line = 1
    col = 1

    def emit(chunk: str, state: int) -> None:
        if not chunk:
            return
        out.append(chunk)
        states.extend([state] * len(chunk))

    def advance(chunk: str) -> None:
        nonlocal line, col
        newlines = chunk.count('\n')
        if newlines:
            line += newlines
            col = len(chunk) - chunk.rfind('\n')
        else:
            col += len(chunk)

    def take(chunk: str, state: int) -> None:
        """输出 chunk（同时更新源码坐标）。"""
        emit(chunk, state)
        advance(chunk)

    i = 0
    while i < n:
        ch = source[i]

        # 注释：`#` 恒为注释；`//` 按词法器的前 token 规则判断。
        if ch == '#':
            end = source.find('\n', i)
            if end < 0:
                end = n
            take(source[i:end], _STATE_COMMENT)
            i = end
            continue
        if source.startswith('//', i) and _is_line_comment(source, i):
            end = source.find('\n', i)
            if end < 0:
                end = n
            take(source[i:end], _STATE_COMMENT)
            i = end
            continue

        # 字符串字面量：原样保留。
        if ch in ('"', "'", '「', '『'):
            end = _string_end(source, i)
            take(source[i:end], _STATE_STRING)
            i = end
            continue

        # 全角/中文标点 -> 半角。
        if ch in PUNCT_MAP:
            after = PUNCT_MAP[ch]
            edits.append(CanonicalEdit(
                CODE_PUNCT, line, col, ch, after,
                '全角/中文标点统一为半角',
            ))
            take(after, _STATE_CODE)
            i += 1
            continue

        # 中文运算符别名 -> ASCII 符号。
        matched = None
        for word, symbol in OPERATOR_ALIASES:
            end = i + len(word)
            if (source.startswith(word, i)
                    and _is_operator_bound(source, i)
                    and _is_operator_bound_right(source, end)):
                matched = (word, symbol, end)
                break
        if matched:
            word, symbol, end = matched
            if source[i:end] == symbol:
                take(source[i:end], _STATE_CODE)
            else:
                edits.append(CanonicalEdit(
                    CODE_OPERATOR, line, col, word, symbol,
                    '运算符中英文别名归一为 ASCII',
                ))
                take(symbol, _STATE_CODE)
            i = end
            continue

        # 有歧义：`等于` 可能是赋值也可能是比较，只报告。
        ambiguous = None
        for word in AMBIGUOUS_OPERATOR_WORDS:
            end = i + len(word)
            if (source.startswith(word, i)
                    and _is_sep(source, i - 1)
                    and _is_sep(source, end)):
                ambiguous = (word, end)
                break
        if ambiguous:
            word, end = ambiguous
            line_start = source.rfind('\n', 0, i) + 1
            prefix = source[line_start:i].strip()
            # `设 甲 等于 1` / `常 设 甲 等于 1` 是赋值，语义明确，不用提示。
            is_assignment = prefix.startswith('设') or prefix.startswith('常')
            if not is_assignment:
                skipped.append(SkippedEdit(
                    CODE_OPERATOR, line, col, word,
                    '「等于」既可能是赋值也可能是比较，不自动改写',
                ))
            take(word, _STATE_CODE)
            i = end
            continue

        # `段落` / `函数` / `段`：收敛为 style 对应的 canonical 形态。
        func_word = None
        for word in FUNCTION_KEYWORDS:
            end = i + len(word)
            if (source.startswith(word, i)
                    and _is_sep(source, i - 1)
                    and _is_sep(source, end)):
                func_word = (word, end)
                break
        if func_word:
            word, end = func_word
            if word == func_canonical:
                take(word, _STATE_CODE)
            else:
                edits.append(CanonicalEdit(
                    CODE_FUNCTION, line, col, word, func_canonical,
                    '段落/函数/段 归一为「%s」' % func_canonical,
                ))
                take(func_canonical, _STATE_CODE)
            i = end
            continue

        take(ch, _STATE_CODE)
        i += 1

    text = ''.join(out)
    text, ws_edits = _normalize_whitespace(text, states)
    edits.extend(ws_edits)
    edits.sort(key=lambda e: (e.line, e.col))
    skipped.sort(key=lambda s: (s.line, s.col))
    return text, edits, skipped


def _normalize_whitespace(text: str, states: List[int]
                          ) -> Tuple[str, List[CanonicalEdit]]:
    """行尾空白 + 行内多余连续空格。字符串/注释内部不动。"""
    edits: List[CanonicalEdit] = []
    if not text:
        return text, edits

    lines = text.split('\n')
    result: List[str] = []
    offset = 0

    for line_no, raw in enumerate(lines, start=1):
        # 行尾空白：字符串内部的尾部空白保留（多行字符串会改变值）。
        end = len(raw)
        while end > 0 and raw[end - 1] in ' \t' and states[offset + end - 1] != _STATE_STRING:
            end -= 1
        if end != len(raw):
            edits.append(CanonicalEdit(
                CODE_WHITESPACE, line_no, end + 1, raw[end:], '',
                '行尾空白归一',
            ))

        # 行内连续空格（缩进不算，字符串/注释内部不算）。
        chars: List[str] = []
        k = 0
        while k < end:
            if raw[k] == ' ':
                run_end = k
                while run_end < end and raw[run_end] == ' ':
                    run_end += 1
                leading = all(c in ' \t' for c in raw[:k])
                all_code = all(
                    states[offset + pos] == _STATE_CODE
                    for pos in range(k, run_end)
                )
                if (not leading) and (run_end - k) >= 2 and all_code:
                    edits.append(CanonicalEdit(
                        CODE_WHITESPACE, line_no, k + 1,
                        raw[k:run_end], ' ', '多余空格归一为单空格',
                    ))
                    chars.append(' ')
                else:
                    chars.append(raw[k:run_end])
                k = run_end
            else:
                chars.append(raw[k])
                k += 1

        result.append(''.join(chars))
        offset += len(raw) + 1

    return '\n'.join(result), edits
