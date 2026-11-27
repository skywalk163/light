# -*- coding: utf-8 -*-
"""strict 检测器：把「同一语义有多种合法写法」收敛成可判定的一条（纯模块，只读）。

职责边界（T-0458）
------------------
* 只做检测：给定源码，返回非规范写法的结构化清单，以及该处**可机械套用**的替换文本；
* 不写盘、不接 CLI、不改 parser、不登记诊断码（那些是 T-0457 / T-0464 的地盘）；
* 规则表的唯一真相是 ``spec/light.spec.json``（``keywords`` / ``operators`` /
  ``syntax_forms``）。本模块**不手写第二份关键字表**：spec 没登记的关系一律
  跳过，记进 ``StrictReport.skipped_spec``，绝不靠猜补齐。

三类规则
--------
``ALIAS``
    别名 → 单字主形式。关系全部来自 spec 的 ``keywords[].主形式`` 与
    ``keywords[].别名``（链式别名解析到终点）。
``PUNCT``
    中文标点 → 英文标点。单字符映射来自 spec ``operators[].全角`` → ``canonical``；
    中文引号（``「」`` / ``『』``）按**整条字符串 token** 一次性给替换。
    句号 ``。`` 不在表内：spec 明确它是唯一的语句结束符、半角 ``.`` 不等价
    （``syntax_forms`` 里 ``cn_en_punctuation`` 的反例），换成 ``.`` 会产出非法代码。
``TYPE``
    L2 要求显式类型标注，``设 甲 为 10。`` 这类无标注的声明只报不给 replacement——
    类型得靠人 / agent 判断，不编。

位置口径
--------
``line`` / ``column`` 与 ``src/lexer.py`` 的 token 位置完全一致（行、列都从 1 起，
列按 Unicode 码点计，一个汉字算 1 列）。``end_column`` 是**开区间右端**：
``行[column-1:end_column-1]`` 正好是 ``actual``。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "KINDS",
    "DEFAULT_SPEC_PATH",
    "SUPPORTED_CANONICAL",
    "StrictError",
    "StrictSpecError",
    "StrictFinding",
    "SkippedRule",
    "StrictReport",
    "load_spec",
    "check",
    "check_report",
]


KINDS = ("ALIAS", "PUNCT", "TYPE")

#: 仓库内 spec 的默认位置（``src/ai_strict.py`` 的上两级 + ``spec/light.spec.json``）。
DEFAULT_SPEC_PATH = Path(__file__).resolve().parent.parent / "spec" / "light.spec.json"

#: 目前支持的目标文体。L1 是「被归一」的那一侧，不是 canonical。
SUPPORTED_CANONICAL = ("L2",)

#: 语句边界 token：出现在 ``设`` 之前仍算「语句起始」。
_STMT_BOUNDARY_TYPES = frozenset({"NEWLINE", "INDENT", "DEDENT", "SEMICOLON", "PERIOD"})

#: 含换行的判断用码点，写成函数是为了避免源码里出现裸换行字面量。
_NL = chr(10)
_CR = chr(13)


class StrictError(Exception):
    """检测器自身的错误（源码无法分词等）。"""


class StrictSpecError(StrictError):
    """spec 读不到 / 结构不对。**绝不**静默返回空列表。"""


@dataclass(frozen=True)
class StrictFinding:
    """一处非规范写法。"""

    line: int
    column: int
    end_column: int
    kind: str
    actual: str
    expected: str
    replacement: str
    message: str

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"未知 kind: {self.kind!r}（只允许 {KINDS}）")
        if self.line < 1 or self.column < 1:
            raise ValueError("位置从 1 起：line / column 必须 >= 1")
        if self.end_column < self.column:
            raise ValueError("end_column 是开区间右端，必须 >= column")
        if self.kind != "TYPE" and not self.replacement:
            raise ValueError(f"{self.kind} 必须给出机械可套用的 replacement")

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "column": self.column,
            "end_column": self.end_column,
            "kind": self.kind,
            "actual": self.actual,
            "expected": self.expected,
            "replacement": self.replacement,
            "message": self.message,
        }


@dataclass(frozen=True)
class SkippedRule:
    """一条「本该归一、但没做」的记录（只报告，不猜）。"""

    rule: str
    word: str
    reason: str

    def to_dict(self) -> dict:
        return {"rule": self.rule, "word": self.word, "reason": self.reason}


@dataclass(frozen=True)
class StrictReport:
    """``check_report`` 的返回值：命中项 + 两类跳过项。"""

    findings: List[StrictFinding] = field(default_factory=list)
    #: 静态跳过：由 spec 结构决定，与源码无关。
    skipped_spec: List[SkippedRule] = field(default_factory=list)
    #: 动态跳过：本次源码里遇到、但替换无法保证安全的位置。
    skipped_source: List[SkippedRule] = field(default_factory=list)
    spec_path: str = ""

    def to_dict(self) -> dict:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "skipped_spec": [s.to_dict() for s in self.skipped_spec],
            "skipped_source": [s.to_dict() for s in self.skipped_source],
            "spec_path": self.spec_path,
        }


# --------------------------------------------------------------------------- #
# spec 读取与规则表推导
# --------------------------------------------------------------------------- #


def load_spec(spec_path: Optional[os.PathLike | str] = None) -> dict:
    """读 ``spec/light.spec.json``。

    读不到 / 不是 JSON 对象 / 缺关键字段 → :class:`StrictSpecError`。
    调用方拿到的永远是一份完整 spec，不存在「空表当没规则」的静默降级。
    """
    path = Path(spec_path) if spec_path is not None else DEFAULT_SPEC_PATH
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StrictSpecError(f"spec 不存在：{path}（strict 规则表的唯一真相）") from exc
    except OSError as exc:
        raise StrictSpecError(f"spec 读取失败：{path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise StrictSpecError(f"spec 不是合法 JSON：{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StrictSpecError(f"spec 顶层必须是对象：{path}")
    for key in ("keywords", "operators"):
        if not isinstance(data.get(key), list):
            raise StrictSpecError(f"spec 缺 {key!r} 段或类型不对：{path}")
    return data


def _is_symbol_char(ch: str) -> bool:
    """ASCII 标点/符号（spec ``operators[].canonical`` 用来表示「符号形态」）。"""
    return len(ch) == 1 and ch.isascii() and not ch.isalnum() and not ch.isspace()


def _resolve_chains(alias_to_main: Dict[str, str]) -> Dict[str, str]:
    """别名指向的若本身也是别名，解析到终点（防环）。"""
    out: Dict[str, str] = {}
    for alias in alias_to_main:
        seen = {alias}
        current = alias_to_main[alias]
        while current in alias_to_main and current not in seen:
            seen.add(current)
            current = alias_to_main[current]
        if current != alias and current not in seen:
            out[alias] = current
    return out


@dataclass(frozen=True)
class _Tables:
    """从 spec 推导出的规则表（唯一真相是 spec，本类不引入任何人工词表）。"""

    alias_to_main: Dict[str, str]
    punct_to_ascii: Dict[str, str]
    quote_pairs: Dict[str, Tuple[str, str]]
    decl_words: frozenset
    decl_modifier_words: frozenset
    assign_words: frozenset
    skipped_spec: List[SkippedRule]
    spec_path: str


def _build_tables(spec: dict, spec_path: str) -> _Tables:
    keywords = [k for k in spec.get("keywords") or [] if isinstance(k, dict)]
    operators = [o for o in spec.get("operators") or [] if isinstance(o, dict)]
    syntax_forms = [s for s in spec.get("syntax_forms") or [] if isinstance(s, dict)]

    # ── 关键字类：别名轴 + 声明/修饰/赋值角色 ──────────────────────────────
    mains: set = set()
    alias_to_main: Dict[str, str] = {}
    decl_words, modifier_words, assign_words = set(), set(), set()
    for item in keywords:
        word = item.get("字")
        if not isinstance(word, str) or not word:
            continue
        role = item.get("作用")
        if role == "变量声明":
            decl_words.add(word)
        elif role == "常量修饰符":
            modifier_words.add(word)
        elif role == "赋值":
            assign_words.add(word)
        main = item.get("主形式")
        if isinstance(main, str) and main and main != word:
            alias_to_main.setdefault(word, main)
            mains.add(main)
        for alias in item.get("别名") or []:
            if isinstance(alias, str) and alias and alias != word:
                alias_to_main.setdefault(alias, word)
                mains.add(word)

    # ── 标点类：全角 → canonical ──────────────────────────────────────────
    punct_to_ascii: Dict[str, str] = {}
    quote_pairs: Dict[str, Tuple[str, str]] = {}
    for op in operators:
        canon = op.get("canonical")
        if not isinstance(canon, str) or not _is_symbol_char(canon):
            continue
        fullwidth = [c for c in (op.get("全角") or []) if isinstance(c, str) and len(c) == 1]
        if not fullwidth:
            continue
        if canon in ('"', "'"):
            # 中文引号成对出现：按整条字符串 token 替换，不拆成两个单字符标点。
            if len(fullwidth) == 2:
                quote_pairs.setdefault(fullwidth[0], (fullwidth[1], canon))
            continue
        for ch in fullwidth:
            if not ch.isascii():
                punct_to_ascii.setdefault(ch, canon)

    skipped: List[SkippedRule] = _spec_gaps(keywords, alias_to_main, mains, syntax_forms)

    return _Tables(
        alias_to_main=_resolve_chains(alias_to_main),
        punct_to_ascii=punct_to_ascii,
        quote_pairs=quote_pairs,
        decl_words=frozenset(decl_words),
        decl_modifier_words=frozenset(modifier_words),
        assign_words=frozenset(assign_words),
        skipped_spec=skipped,
        spec_path=spec_path,
    )


def _spec_gaps(keywords: List[dict], alias_to_main: Dict[str, str], mains: set,
               syntax_forms: List[dict]) -> List[SkippedRule]:
    """把「本该归一、但 spec 没给够信息」的条目列出来（不猜，只报告）。

    判据是纯结构的：某个**类别**里已经出现过 L0 单字规范条目，或已登记过别名关系
    —— 说明这个类别确实有「多字 ⇄ 单字」这根轴。于是该类别里既无「主形式」、
    也没有任何词以它为别名的多字词，就是 spec 缺信息：它的规范形是谁，spec 没说。
    """
    by_word = {item["字"]: item for item in keywords if isinstance(item.get("字"), str)}
    l0_categories = {
        item.get("类别") for item in keywords
        if isinstance(item.get("字"), str) and len(item["字"]) == 1
        and item.get("层级") == "L0"
    }
    alias_axis_categories = l0_categories | {
        by_word[alias].get("类别")
        for alias, main in alias_to_main.items()
        if alias in by_word and main in by_word
        and by_word[alias].get("类别") == by_word[main].get("类别")
    }

    skipped: List[SkippedRule] = []
    for item in keywords:
        word = item.get("字")
        if not isinstance(word, str) or len(word) < 2:
            continue
        if word in alias_to_main or word in mains or item.get("别名"):
            continue
        category = item.get("类别")
        if category not in alias_axis_categories:
            continue
        skipped.append(SkippedRule(
            rule="ALIAS",
            word=word,
            reason=(f"spec.keywords 的「{category}」类别已登记别名轴，但「{word}」既无"
                    "「主形式」也无反向「别名」登记：规范单字待 spec 补齐，本模块不猜"),
        ))
    for form in syntax_forms:
        if form.get("已实测") is False:
            skipped.append(SkippedRule(
                rule="PUNCT",
                word=str(form.get("id") or form.get("名称") or "?"),
                reason="spec.syntax_forms 标记「未实测」，不作为可归一的写法",
            ))
    return skipped


# --------------------------------------------------------------------------- #
# 源码侧工具
# --------------------------------------------------------------------------- #


def _import_lexer():
    """按仓库既有约定取 lexer（``tests/conftest.py`` 把 ``src`` 放进了 sys.path）。"""
    try:
        from lexer import Lexer, LexerError, TokenType  # noqa: WPS433
        return Lexer, LexerError, TokenType
    except ImportError:  # pragma: no cover - 只在 src 不在 sys.path 时走到
        try:
            from src.lexer import Lexer, LexerError, TokenType  # noqa: WPS433
            return Lexer, LexerError, TokenType
        except ImportError as exc:
            raise StrictError(
                "找不到 src/lexer.py：strict 检测器的分词依赖它，"
                "请把仓库 src/ 放进 sys.path（仓库测试由 tests/conftest.py 负责）"
            ) from exc


def _line_starts(source: str) -> List[int]:
    starts = [0]
    for index, ch in enumerate(source):
        if ch == _NL:
            starts.append(index + 1)
    return starts


def _text_at(source: str, starts: Sequence[int], line: int, column: int, length: int) -> str:
    """取源码里 (line, column) 起、长 ``length`` 的原文（越界返回空串）。"""
    if not (1 <= line <= len(starts)):
        return ""
    base = starts[line - 1] + column - 1
    return source[base:base + length]


def _type_name(token) -> str:
    return getattr(getattr(token, "type", None), "name", "")


def _token_text(token) -> str:
    return token.value if isinstance(token.value, str) else ""


# --------------------------------------------------------------------------- #
# 三类规则
# --------------------------------------------------------------------------- #


def _alias_findings(tokens, source, starts, tables: _Tables,
                    skipped: List[SkippedRule]) -> List[StrictFinding]:
    out: List[StrictFinding] = []
    for token in tokens:
        kind = _type_name(token)
        value = _token_text(token)
        if value not in tables.alias_to_main:
            continue
        if kind == "IDENTIFIER":
            # spec 把这些词登记成「文档登记别名（上下文）」——词法层按标识符发，
            # 是不是关键字取决于 parser 位置（例如 `属性`）。检测器不做语法分析，
            # 无法区分「上下文关键字」和「真的叫这个名字的标识符」，因此不报，
            # 只记一条待 spec/parser 给判据。
            skipped.append(SkippedRule(
                rule="ALIAS",
                word=value,
                reason=(f"spec 登记「{value}」是「{tables.alias_to_main[value]}」的别名，"
                        "但词法层把它发成 IDENTIFIER（上下文关键字）：没有 parser 位置语义，"
                        "无法与同名标识符区分，不猜"),
            ))
            continue
        if kind != "KEYWORD":
            continue
        actual = _text_at(source, starts, token.line, token.col, len(value))
        if actual != value:
            # 词法层重映射过（如 `退出循环` → KEYWORD('跳出')）：原文与 token 值不一致，
            # 拿 token 值去切原文会错位，这里只报告、不猜位置。
            skipped.append(SkippedRule(
                rule="ALIAS",
                word=actual or value,
                reason=f"词法层把该词重映射成了 {value!r}，原文与 token 值不一致，无法定位",
            ))
            continue
        main = tables.alias_to_main[value]
        out.append(StrictFinding(
            line=token.line,
            column=token.col,
            end_column=token.col + len(actual),
            kind="ALIAS",
            actual=actual,
            expected=main,
            replacement=main,
            message=f"别名「{actual}」→ 规范单字「{main}」（spec 登记的主形式）",
        ))
    return out


def _punct_findings(tokens, source, starts, tables: _Tables,
                    skipped: List[SkippedRule]) -> List[StrictFinding]:
    """单字符中文标点 → 英文标点（symbol 级）。"""
    out: List[StrictFinding] = []
    for token in tokens:
        value = _token_text(token)
        if len(value) != 1:
            continue
        ascii_form = tables.punct_to_ascii.get(value)
        if ascii_form is None:
            continue
        actual = _text_at(source, starts, token.line, token.col, 1)
        if actual != value:
            continue
        out.append(StrictFinding(
            line=token.line,
            column=token.col,
            end_column=token.col + 1,
            kind="PUNCT",
            actual=actual,
            expected=ascii_form,
            replacement=ascii_form,
            message=f"中文标点「{actual}」→ 英文标点「{ascii_form}」",
        ))
    return out


def _quote_findings(tokens, source, starts, tables: _Tables,
                    skipped: List[SkippedRule]) -> List[StrictFinding]:
    """``「…」`` / ``『…』`` 字符串按**整条 token** 归一成 ASCII 引号。

    中文引号在词法层走 ``_QUOTE_MAP``（不像 ``，`` 走 ``SYMBOL_MAP``），所以这里
    不能只看单字符 token：必须整条字符串一起换，才拿到语义等价的代码。

    三条保守边界（都记进 ``skipped_source``，不硬给替换）：
    * 字符串体与 token 值不一致（含转义）—— 原文定位不可靠；
    * 字符串体含目标 ASCII 引号或反斜杠 —— 直接换会改变字符串内容；
    * 跨行字符串 —— ``end_column`` 是同一行的列，跨行没有单行区间可表达。
    """
    out: List[StrictFinding] = []
    for token in tokens:
        if _type_name(token) not in ("STRING", "FSTRING", "BYTES"):
            continue
        body = _token_text(token)
        if not (1 <= token.line <= len(starts)):
            continue
        base = starts[token.line - 1] + token.col - 1
        if base >= len(source) or source[base] not in tables.quote_pairs:
            continue
        opener = source[base]
        closer, ascii_form = tables.quote_pairs[opener]
        if source[base + 1:base + 1 + len(body)] != body:
            skipped.append(SkippedRule(
                rule="PUNCT",
                word=source[base:base + 12],
                reason="字符串体与 token 值不一致（含转义），原文定位不可靠，跳过",
            ))
            continue
        close_at = base + 1 + len(body)
        if close_at >= len(source) or source[close_at] != closer:
            skipped.append(SkippedRule(
                rule="PUNCT",
                word=source[base:base + 12],
                reason=f"找不到配对的中文右引号 {closer}，跳过",
            ))
            continue
        actual = source[base:close_at + 1]
        if _NL in actual or _CR in actual:
            skipped.append(SkippedRule(
                rule="PUNCT",
                word=actual[:8],
                reason="跨行字符串：单行内没有可表达的 end_column 区间，跳过",
            ))
            continue
        if ascii_form in body or "\\" in body:
            skipped.append(SkippedRule(
                rule="PUNCT",
                word=actual[:8],
                reason=(f"字符串体含 {ascii_form!r} 或反斜杠，直接换 ASCII 引号会改变字符串内容，"
                        "需人工加转义"),
            ))
            continue
        out.append(StrictFinding(
            line=token.line,
            column=token.col,
            end_column=token.col + len(actual),
            kind="PUNCT",
            actual=actual,
            expected=f"{ascii_form}{body}{ascii_form}",
            replacement=f"{ascii_form}{body}{ascii_form}",
            message=f"中文引号 {opener}{closer} → ASCII 引号 {ascii_form}（整条字符串替换）",
        ))
    return out


def _is_decl_start(tokens: Sequence, index: int, tables: _Tables) -> bool:
    """``tokens[index]`` 是否处在语句起始位置（前面只有边界或修饰符）。"""
    if index == 0:
        return True
    previous = tokens[index - 1]
    if _type_name(previous) in _STMT_BOUNDARY_TYPES:
        return True
    return (_type_name(previous) == "KEYWORD"
            and _token_text(previous) in tables.decl_modifier_words)


def _type_findings(tokens, source, starts, tables: _Tables,
                   skipped: List[SkippedRule]) -> List[StrictFinding]:
    """无显式类型标注的变量声明：只报，不给 replacement。"""
    out: List[StrictFinding] = []
    if not tables.decl_words:
        return out
    for index, token in enumerate(tokens):
        if _type_name(token) != "KEYWORD" or _token_text(token) not in tables.decl_words:
            continue
        if not _is_decl_start(tokens, index, tables):
            continue
        if index + 1 >= len(tokens):
            continue
        name_token = tokens[index + 1]
        if _type_name(name_token) != "IDENTIFIER":
            continue
        name = _text_at(source, starts, name_token.line, name_token.col,
                        len(_token_text(name_token)))
        if not name:
            continue
        next_token = tokens[index + 2] if index + 2 < len(tokens) else None
        next_type = _type_name(next_token) if next_token is not None else ""
        if next_type == "COLON":
            continue  # 已有显式类型标注
        is_assign = (next_type == "EQUALS"
                     or (next_type == "KEYWORD" and _token_text(next_token) in tables.assign_words))
        if not is_assign:
            if next_type in ("COMMA", "LPAREN"):
                skipped.append(SkippedRule(
                    rule="TYPE",
                    word=name,
                    reason="多目标 / 解构式声明，类型标注形态无法机械判定，跳过",
                ))
            continue
        end_column = name_token.col + len(name)
        if name_token.line != token.line:
            continue  # 跨行的声明头不在同一行内，没有单行区间可表达
        actual = _text_at(source, starts, token.line, token.col, end_column - token.col)
        decl = _token_text(token)
        out.append(StrictFinding(
            line=token.line,
            column=token.col,
            end_column=end_column,
            kind="TYPE",
            actual=actual,
            expected=f"{decl} {name}: <类型>",
            replacement="",
            message=(f"变量声明「{name}」缺少 L2 显式类型标注；规范写作 "
                     f"`{decl} {name}: <类型> = …`（类型靠人判断，不代猜）"),
        ))
    return out


# --------------------------------------------------------------------------- #
# 对外入口
# --------------------------------------------------------------------------- #


def _check(source: str, canonical: str, spec_path) -> StrictReport:
    if canonical not in SUPPORTED_CANONICAL:
        raise ValueError(f"暂只支持 canonical={SUPPORTED_CANONICAL}，收到 {canonical!r}")
    if not isinstance(source, str):
        raise TypeError("source 必须是 str")

    resolved = Path(spec_path) if spec_path is not None else DEFAULT_SPEC_PATH
    spec = load_spec(resolved)
    tables = _build_tables(spec, str(resolved))

    Lexer, LexerError, _unused = _import_lexer()
    try:
        tokens = Lexer().tokenize(source)
    except LexerError as exc:
        raise StrictError(
            f"源码无法分词（行{getattr(exc, 'line', '?')} 列{getattr(exc, 'col', '?')}）：{exc}"
        ) from exc

    starts = _line_starts(source)
    skipped_source: List[SkippedRule] = []
    findings: List[StrictFinding] = []
    findings += _alias_findings(tokens, source, starts, tables, skipped_source)
    findings += _punct_findings(tokens, source, starts, tables, skipped_source)
    findings += _quote_findings(tokens, source, starts, tables, skipped_source)
    findings += _type_findings(tokens, source, starts, tables, skipped_source)

    findings.sort(key=lambda f: (f.line, f.column, KINDS.index(f.kind)))
    return StrictReport(
        findings=findings,
        skipped_spec=list(tables.skipped_spec),
        skipped_source=skipped_source,
        spec_path=tables.spec_path,
    )


def check(source: str, *, canonical: str = "L2", spec_path=None) -> List[StrictFinding]:
    """检测 ``source`` 里的非规范写法，按 (行, 列, kind) 升序返回。

    :param canonical: 目标文体，目前只支持 ``"L2"``（单字关键字 + 英文标点 + 显式类型）。
    :param spec_path: 覆盖 spec 路径（测试用），默认仓库内 ``spec/light.spec.json``。
    :raises StrictSpecError: spec 读不到或结构不对（**绝不**静默返回空列表）。
    :raises StrictError: 源码无法分词。
    """
    return _check(source, canonical, spec_path).findings


def check_report(source: str, *, canonical: str = "L2", spec_path=None) -> StrictReport:
    """同 :func:`check`，额外带回「spec 缺信息而跳过」与「替换不安全而跳过」两清单。"""
    return _check(source, canonical, spec_path)