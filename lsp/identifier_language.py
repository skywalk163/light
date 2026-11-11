# -*- coding: utf-8 -*-
"""T-0325：LSP 层标识符语言一致性检查（中文 / 英文命名建议，**非强制**）。

背景
----
「对中国人友好」不等于全中文。标识符用中文还是英文应由**项目规范**决定，
而不是语言在语法层强制。L0 内核已冻结、L1/L2 双轨覆盖教学与工程，本模块只在
**LSP 层**给出命名风格的提示 / 警告，帮团队保持一致：

* 不做自动重命名、不提供 code action（不替用户改代码）；
* 任何情况下都不把命名风格升级成 error，也不会让编译 / 诊断失败；
* 纯标准库实现（lexer 复用既有 `src/lexer.py` 的 token 流，不自写正则硬啃源码）。

判定口径
--------
`check(text, mode="any") -> list[dict]`，元素::

    {name, line, column, kind, lang, severity, suggestion}

* `lang`：`zh`（含 CJK 且无拉丁字母）/ `en`（纯 ASCII 字母数字下划线）/
  `mixed`（CJK 与拉丁字母并存，如 `user名字`）。
* `mode`：
  - `"any"`：**默认不打扰**，直接返回 `[]`；
  - `"zh"`：英文名给 `info`，提示「本项目规范为中文命名」；
  - `"en"`：中文名给 `info`；
  - `mixed` 在 `zh` / `en` 任一开启模式下一律 `warning`，并给拆分建议。

坐标口径
--------
本模块对外返回的 `line` / `column` 沿用 lexer 的 **1-based**（给人看）；
转 LSP `Diagnostic.range` 时在 `lsp/diagnostic_extension.py` 统一 `-1` 换算成
0-based，与 `src/lsp_diagnostic.py` 的既有约定一致。

配置
----
读取 `light.toml` 的 `[lsp.identifier] mode = "zh"|"en"|"any"`，缺省 `any`。
配置缺失 / 非法值一律回落 `any`（默认不打扰）。
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Iterator, List, Optional

# 让 `src/` 在 path 上（与 lsp/diagnostic_extension.py 的做法一致）。
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _ROOT):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from lexer import Lexer, TokenType
except ImportError:  # pragma: no cover - lexer 缺失时降级为「不提示」
    Lexer = None  # type: ignore[assignment]
    TokenType = None  # type: ignore[assignment]

__all__ = [
    "SUPPORTED_MODES",
    "DEFAULT_MODE",
    "detect_lang",
    "iter_identifiers",
    "load_mode",
    "check",
    "check_from_config",
]

#: 支持的规范模式；其它值一律按 `any` 处理（不打扰）。
SUPPORTED_MODES = ("zh", "en", "any")

#: 缺省模式：默认不打扰。
DEFAULT_MODE = "any"

#: 声明类关键字（其后第一个标识符视为声明名）。
_DECL_KEYWORDS = frozenset({
    "设", "定义", "常量", "类型",
    "段", "段落", "函数",
    "类", "继承", "构造",
    "静态", "静态方法", "类方法", "特性", "属性",
})

#: 导入类关键字（其后第一个标识符视为导入的模块 / 符号名）。
_IMPORT_KEYWORDS = frozenset({"导入", "导", "从"})

#: 别名关键字：`导入 X 为 Y` 中的 `为`。
_ALIAS_KEYWORD = "为"


# --------------------------------------------------------------------------
# 语言判定
# --------------------------------------------------------------------------
def _is_cjk(ch: str) -> bool:
    """是否为 CJK 统一表意文字（基本区 + 扩展 A）。"""
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF) or (0x3400 <= o <= 0x4DBF)


def _is_latin(ch: str) -> bool:
    """是否为拉丁字母（A–Z / a–z）。"""
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z")


def detect_lang(name: str) -> str:
    """判定单个标识符的语言类别：`zh` / `en` / `mixed`。

    * 同时含 CJK 与拉丁字母 → `mixed`；
    * 只含 CJK（无拉丁字母）→ `zh`；
    * 其余（纯 ASCII 字母 / 数字 / 下划线等）→ `en`。
    """
    has_cjk = any(_is_cjk(ch) for ch in name)
    has_latin = any(_is_latin(ch) for ch in name)
    if has_cjk and has_latin:
        return "mixed"
    if has_cjk:
        return "zh"
    return "en"


# --------------------------------------------------------------------------
# 标识符抽取（复用既有 lexer token 流）
# --------------------------------------------------------------------------
def _classify_kind(prev: Any, prevprev: Any, paren_depth: int,
                   decl_paren_pending: bool) -> str:
    """根据上下文把一个 IDENTIFIER token 归类为粗粒度 kind。

    kind 仅作信息标注，不参与成败判定：

    * `decl`：声明名（紧跟 设/段/函数/类 等关键字）；
    * `param`：参数名（声明关键字后首个括号组内的标识符）；
    * `import`：导入的模块 / 符号名；
    * `import_alias`：导入别名（`导入 X 为 Y` 中的 Y）；
    * `ident`：其余普通标识符（变量引用等）。
    """
    def _value(tok: Any) -> Optional[str]:
        return getattr(tok, "value", None)

    def _is_keyword(tok: Any) -> bool:
        return TokenType is not None and getattr(tok, "type", None) is TokenType.KEYWORD

    if prev is not None and _is_keyword(prev):
        pv = _value(prev)
        if pv in _IMPORT_KEYWORDS:
            return "import"
        if pv == _ALIAS_KEYWORD and prevprev is not None \
                and getattr(prevprev, "type", None) is TokenType.IDENTIFIER:
            return "import_alias"
        if pv in _DECL_KEYWORDS:
            return "decl"
    if paren_depth > 0 and decl_paren_pending:
        return "param"
    return "ident"


def _lex_tokens(text: str) -> List[Any]:
    """跑既有 lexer 拿到 token 流；任何异常 / 空输入都返回空列表。"""
    if Lexer is None or not isinstance(text, str) or not text:
        return []
    try:
        return Lexer(text).tokenize()
    except Exception:
        return []


def _inspect(tokens: List[Any]) -> List[Dict[str, Any]]:
    """在已有的 token 流上抽取标识符（纯后置线性扫描，不再跑 lexer）。"""
    抽取: List[Dict[str, Any]] = []
    prev: Any = None
    prevprev: Any = None
    paren_depth = 0
    decl_paren_pending = False

    for tok in tokens:
        ttype = getattr(tok, "type", None)
        if ttype is TokenType.LPAREN:
            paren_depth += 1
        elif ttype is TokenType.RPAREN:
            paren_depth = max(0, paren_depth - 1)
            if paren_depth == 0:
                decl_paren_pending = False
        elif ttype is TokenType.IDENTIFIER:
            kind = _classify_kind(prev, prevprev, paren_depth,
                                   decl_paren_pending)
            if kind == "decl":
                decl_paren_pending = True
            抽取.append({
                "name": str(getattr(tok, "value", "") or ""),
                "line": int(getattr(tok, "line", 1) or 1),
                "column": int(getattr(tok, "col", 1) or 1),
                "kind": kind,
            })
        prevprev, prev = prev, tok
    return 抽取


def iter_identifiers(text: str) -> Iterator[Dict[str, Any]]:
    """从 token 流里抽取标识符，逐个产出 ``{name, line, column, kind}``。

    只保留 ``IDENTIFIER`` token：关键字（``如果`` / ``段落`` 等）、字符串字面量、
    注释（lexer 不发注释 token）、数字、运算符一律不进入结果。
    """
    yield from _inspect(_lex_tokens(text))


# --------------------------------------------------------------------------
# 配置读取
# --------------------------------------------------------------------------
def _normalize_mode(value: Any) -> str:
    """把配置值归一到受支持的模式；非法值回落 `any`。"""
    if isinstance(value, str):
        v = value.strip().lower()
        if v in SUPPORTED_MODES:
            return v
    return DEFAULT_MODE


def load_mode(toml_path: Optional[str] = None) -> str:
    """从 `light.toml` 读取 ``[lsp.identifier] mode``，缺省 / 非法回落 ``any``。

    读取失败（文件缺失、解析失败、字段缺失）一律返回 `any`，绝不抛异常。
    """
    path = toml_path or os.path.join(os.getcwd(), "light.toml")
    if not path or not os.path.isfile(path):
        return DEFAULT_MODE
    try:
        import tomllib  # Python 3.11+ 标准库
    except ImportError:  # pragma: no cover - 老版本 Python 兜底
        try:
            import toml as tomllib  # type: ignore
        except ImportError:
            return DEFAULT_MODE
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        section = data.get("lsp", {}) if isinstance(data, dict) else {}
        ident = section.get("identifier", {}) if isinstance(section, dict) else {}
        return _normalize_mode(ident.get("mode"))
    except Exception:
        return DEFAULT_MODE


# --------------------------------------------------------------------------
# 主入口
# --------------------------------------------------------------------------
def _suggestion(mode: str, lang: str, name: str) -> str:
    """按模式与语言类别生成建议文案（仅供提示，不替用户改名）。"""
    if lang == "mixed":
        return (f"标识符「{name}」中英文混排，建议拆分为纯中文或纯英文命名"
                "（去掉混排的另一方）。")
    if mode == "zh" and lang == "en":
        return f"本项目规范为中文命名，标识符「{name}」建议使用中文命名。"
    if mode == "en" and lang == "zh":
        return f"本项目规范为英文命名，标识符「{name}」建议使用英文命名。"
    return ""


def check(text: str, mode: str = DEFAULT_MODE) -> List[Dict[str, Any]]:
    """检查一段源码中的标识符命名风格，返回需提示的条目列表。

    参数:
        text: 源码文本。
        mode: 规范模式，``"zh"`` / ``"en"`` / ``"any"``；非法值按 ``any`` 处理。

    返回:
        条目列表，元素 ::

            {name, line, column, kind, lang, severity, suggestion}

        * ``severity``：``"info"``（风格与规范不符）或 ``"warning"``（混排）；
        * ``mode="any"`` 时直接返回空列表（默认不打扰）；
        * lexer 异常 / 空文本一律返回空列表，不让诊断通道崩掉。
    """
    mode = _normalize_mode(mode)
    if mode == DEFAULT_MODE:
        return []
    try:
        return _filter(_inspect(_lex_tokens(text)), mode)
    except Exception:
        return []


def _filter(idents: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
    """在已抽取的标识符列表上按模式过滤出需提示的条目（纯线性后置扫描）。"""
    结果: List[Dict[str, Any]] = []
    for ident in idents:
        name = ident["name"]
        if not name:
            continue
        # 只对定义位点（声明名 / 参数 / 导入名 / 别名）出诊断；普通引用（`ident`）
        # 不重复提示，避免同一名字在每次使用处都刷一条波浪线。
        if ident["kind"] == "ident":
            continue
        lang = detect_lang(name)
        severity: Optional[str] = None
        if lang == "mixed":
            severity = "warning"
        elif mode == "zh" and lang == "en":
            severity = "info"
        elif mode == "en" and lang == "zh":
            severity = "info"
        if severity is None:
            continue
        结果.append({
            "name": name,
            "line": ident["line"],
            "column": ident["column"],
            "kind": ident["kind"],
            "lang": lang,
            "severity": severity,
            "suggestion": _suggestion(mode, lang, name),
        })
    return 结果


def check_from_config(text: str, toml_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """按 `light.toml` 配置的模式执行 :func:`check`；未配置时等价 ``mode="any"``。"""
    return check(text, mode=load_mode(toml_path))
