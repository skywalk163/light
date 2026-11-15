# -*- coding: utf-8 -*-
"""
光明（Light）智能原语弹性适配层 —— L1 前端，非侵入、可配置、可关闭、可诊断。

设计立场
--------
智能原语**不是关键字**，而是「L1 双字标准形式（普通标识符） + L0 组合惯用法」：

    口语「计划 / 安排 / 筹谋」
      ↓ 本层：文本级标识符归一化（可整体关闭）
    标准双字标识符「观察 / 规划 / 执行 / 记忆 / 决策」
      ↓ 冻结的 L0 核心字：段 / 设 / 当 / 若 / 返回 / 断 …（零改动）
    原有词法、语法、代码生成流程

本层只做三件事，全部在源码进入 lexer **之前**完成：
1. 把口语变体按映射表归一化成标准双字标识符；
2. 对映射表与源码做冲突诊断（不阻断编译）；
3. 只读扫描 L0 组合惯用模式，产出结构化轨迹（sidecar JSON）。

明确不做：不改 ``src/keywords.py``、不改 L0 冻结字表、不改 lexer/parser/codegen、
不新增关键字、不修改 AST、不改变生成代码、不 strip 缩进、不替换字符串与注释内容。

保护区口径（与 ``src/lexer.py`` 对齐，勿凭直觉简化）
----------------------------------------------------
- 英文引号 ``"…"`` / ``'…'``，支持反斜杠转义；
- 三引号 ``\"\"\"…\"\"\"`` / ``'''…'''``，**支持跨行**（lexer.py:1875 起）；
- 中文引号 ``「…」`` / ``『…』``（lexer.py:469-472 的字符串定界符），
  无转义语义，同样支持跨行；
- ``#`` 行注释（含行尾注释）；
- L4 嵌入块：前缀 ``嵌入`` / ``引``（lexer.py:2044 起），结束标记
  ``结束嵌入`` / ``结束引``（可容错混用），并支持**缩进回归闭合**与 EOF 闭合；
  块内是外语代码，一个字符都不能改。

与 ``src/elastic_syntax.py`` 的关系：那是「口语 -> 关键字」的旧先例，未接入主管线且
存在中文 ``\\b`` 边界失效、strip 缩进等缺陷。本模块是独立的新层，**不修改也不复用**
那份实现，避免引入回归。

开关与环境
----------
默认关闭（关闭时源码对象原样返回，零文件 IO、零新增正则）。
- ``LIGHT_SMART_ELASTIC=1|0``            总开关
- ``LIGHT_SMART_ELASTIC_MAP=<json路径>``  自定义映射表（其内 ``enabled`` 可独立开启）
- ``LIGHT_SMART_ELASTIC_TRACE=1|0``       轨迹输出（默认跟随总开关）
- ``LIGHT_SMART_ELASTIC_ON_CONFLICT=diagnose|warn|keep``  冲突处置
- 文件头 ``# @智能弹性 开`` / ``# @智能弹性 关``  逐文件覆盖（优先级最高）
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Tuple

__all__ = [
    "SCHEMA_MAP", "SCHEMA_TRACE",
    "Diagnostic", "SmartConfig", "SmartResult",
    "load_map", "validate_map", "compile_rules", "resolve_config",
    "preprocess", "apply_smart_elastic",
    "ENV_ENABLED", "ENV_MAP", "ENV_TRACE", "ENV_CONFLICT",
]

SCHEMA_MAP = "light.smart-elastic-map/v1"
SCHEMA_TRACE = "light.smart-trace/v1"

ENV_ENABLED = "LIGHT_SMART_ELASTIC"
ENV_MAP = "LIGHT_SMART_ELASTIC_MAP"
ENV_TRACE = "LIGHT_SMART_ELASTIC_TRACE"
ENV_CONFLICT = "LIGHT_SMART_ELASTIC_ON_CONFLICT"

DEFAULT_MAP_PATH = Path(__file__).with_name("smart_primitives_map.json")

# 文件头指令；允许 BOM 前缀与行尾注释（``# @智能弹性 开  # 说明``）
DIRECTIVE_RE = re.compile(
    r"^[ \t]*#[ \t]*@智能弹性[ \t]*(开|关|on|off)[ \t]*(?:#.*)?$", re.IGNORECASE)

# L4 嵌入块：前缀「嵌入」或「引」，语言名到冒号；结束标记两种写法都认。
# 依据 src/lexer.py:2044-2184（含缩进回归闭合），此处只做行级近似，
# 但必须覆盖双前缀 / 双结束标记，否则块内语言代码会被误改。
EMBED_START_RE = re.compile(r"^[ \t]*(?:嵌入|引)[ \t]+([^:：\n]+?)[ \t]*[:：][^\n]*$")
EMBED_END_RE = re.compile(r"^[ \t]*(?:结束嵌入|结束引)[ \t]*。?[ \t]*$")

# 「段/段落/函数/定义 <名字>(」—— L0/L1 既有的定义字，本层不新增
DEFINE_RE = re.compile(r"^[ \t]*(段|段落|函数|定义)[ \t]+([^\s(（]+)[ \t]*\(")
IF_RE = re.compile(r"^[ \t]*(?:若|如果|要是|假如)[ \t]*(.+?)[ \t]*[:：][ \t]*$")
WHILE_RE = re.compile(r"^[ \t]*(?:当|每当)[ \t]*(.+?)[ \t]*[:：][ \t]*$")
PRINT_RE = re.compile(r"(?<!\w)(?:打印|印|写)[ \t]*\(")
STATIC_BOUND_RE = re.compile(r"<[ \t]*(\d+)")

# 字符串定界符：开 -> 闭；只有英文引号有反斜杠转义
_QUOTE_CLOSE = {'"': '"', "'": "'", '「': '」', '『': '』'}
_ESCAPABLE = frozenset({'"', "'"})

_TRUTHY = {"1", "on", "true", "yes", "开", "启用"}
_FALSY = {"0", "off", "false", "no", "关", "禁用"}
_CONFLICT_MODES = {"diagnose", "warn", "keep"}

# JSON 缺失时的最小兜底（不是第二事实源；权威表是 smart_primitives_map.json）
_FALLBACK_PRIMITIVES: Dict[str, Dict[str, Any]] = {
    "观察": {"kind": "observe", "variants": ["看看", "感知"]},
    "规划": {"kind": "plan", "variants": ["计划", "安排", "筹谋"]},
    "执行": {"kind": "act", "variants": ["动手", "落实"]},
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Diagnostic:
    """一条结构化诊断。line=0 表示配置级（不指向源码行）。"""
    code: str
    severity: str            # error | warning
    message: str
    source: str = ""         # 触发词（口语变体）
    target: str = ""         # 目标标准词
    line: int = 0
    column: int = 0
    origin: str = ""         # 规则来源

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code, "severity": self.severity, "message": self.message,
            "source": self.source, "target": self.target,
            "line": self.line, "column": self.column, "origin": self.origin,
        }


@dataclass
class SmartConfig:
    enabled: bool = False
    trace: bool = False
    on_conflict: str = "diagnose"
    primitives: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    map_path: Optional[str] = None
    directive: Optional[str] = None       # 命中的文件头指令

    @property
    def effective(self) -> bool:
        return self.enabled and bool(self.primitives)


@dataclass
class SmartResult:
    source: str
    enabled: bool = False
    diagnostics: List[Diagnostic] = field(default_factory=list)
    trace: Dict[str, Any] = field(default_factory=dict)
    rewrites: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 映射表：加载 / 校验 / 编译
# ---------------------------------------------------------------------------

def load_map(path: Optional[str] = None) -> Dict[str, Any]:
    """加载映射表 JSON。path 为 None 时用内置默认表。

    schema / version / primitives 结构不合法时抛 ``ValueError``，
    由 ``resolve_config`` 统一降级为 L-SMART-004（不阻断编译）。
    """
    p = Path(path) if path else DEFAULT_MAP_PATH
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"映射表根节点必须是对象: {p}")
    schema = raw.get("schema")
    if schema is not None and schema != SCHEMA_MAP:
        raise ValueError(f"映射表 schema 不匹配（期望 {SCHEMA_MAP}，实际 {schema!r}）: {p}")
    version = raw.get("version", 1)
    if not isinstance(version, int) or version < 1:
        raise ValueError(f"映射表 version 非法（应为正整数，实际 {version!r}）: {p}")
    prim = raw.get("primitives")
    if not isinstance(prim, dict):
        raise ValueError(f"映射表结构非法（缺 primitives 对象）: {p}")
    scope = raw.get("scope")
    if scope is not None and scope != "identifier":
        raise ValueError(f"映射表 scope 仅支持 identifier（实际 {scope!r}）: {p}")
    return raw


def _reserved_words() -> Tuple[set, List[Diagnostic]]:
    """从 keywords.ALL_KEYWORDS 动态取保留字，避免再造一份「第二事实源」字表。"""
    diags: List[Diagnostic] = []
    try:
        from keywords import ALL_KEYWORDS          # src/ 在 sys.path 时
    except ImportError:
        try:
            from src.keywords import ALL_KEYWORDS  # 项目根在 sys.path 时
        except ImportError:
            ALL_KEYWORDS = ()
            diags.append(Diagnostic(
                code="L-SMART-000", severity="warning",
                message="未能加载 keywords.ALL_KEYWORDS，保留字冲突检查降级（不影响替换）",
            ))
    words = set(ALL_KEYWORDS or ())
    # 高频内置名补充：这些不是关键字，但被占用时同样会造成歧义
    words.update({"打印", "长", "返回", "输入", "读取", "写入", "类型", "范围"})
    return words, diags


_IDENT_RE = re.compile(r"[^\W\d_][\w]*", re.UNICODE)


def validate_map(primitives: Dict[str, Dict[str, Any]],
                 origin: str = "default") -> List[Diagnostic]:
    """映射表级冲突诊断：L-SMART-001 / L-SMART-003 / L-SMART-004。

    返回 error 级诊断时，对应规则在 compile_rules 里会被丢弃（不阻断编译）。
    """
    diags: List[Diagnostic] = []
    reserved, load_diags = _reserved_words()
    diags.extend(load_diags)

    standard_names = set(primitives.keys())
    seen_variant: Dict[str, str] = {}

    for standard, spec in primitives.items():
        if not isinstance(spec, dict):
            diags.append(Diagnostic(
                "L-SMART-004", "error",
                f"标准形式「{standard}」的规则必须是对象，实际是 "
                f"{type(spec).__name__}，该条已跳过",
                source=standard, target=standard, origin=origin))
            continue
        variants = spec.get("variants", [])
        if not isinstance(variants, list):
            diags.append(Diagnostic(
                "L-SMART-004", "error",
                f"标准形式「{standard}」的 variants 必须是列表，实际是 "
                f"{type(variants).__name__}，该条已跳过",
                source=standard, target=standard, origin=origin))
            continue
        if not _IDENT_RE.fullmatch(standard):
            diags.append(Diagnostic(
                "L-SMART-003", "error", f"标准形式「{standard}」不是合法标识符",
                source=standard, target=standard, origin=origin))
        if standard in reserved:
            diags.append(Diagnostic(
                "L-SMART-001", "error",
                f"标准形式「{standard}」撞已有关键字/内置名，禁止作为智能原语",
                source=standard, target=standard, origin=origin))

        for v in variants:
            if not isinstance(v, str) or not _IDENT_RE.fullmatch(v):
                diags.append(Diagnostic(
                    "L-SMART-003", "error",
                    f"变体「{v}」不是合法标识符（不能含空格/标点/数字开头）",
                    source=v, target=standard, origin=origin))
                continue
            if v in reserved:
                diags.append(Diagnostic(
                    "L-SMART-001", "error",
                    f"变体「{v}」撞已有关键字/内置名「{v}」，该规则已跳过",
                    source=v, target=standard, origin=origin))
            if v in seen_variant and seen_variant[v] != standard:
                diags.append(Diagnostic(
                    "L-SMART-003", "error",
                    f"变体「{v}」同时映射到「{seen_variant[v]}」和「{standard}」",
                    source=v, target=standard, origin=origin))
            seen_variant[v] = standard
            if v in standard_names and v != standard:
                diags.append(Diagnostic(
                    "L-SMART-003", "error",
                    f"变体「{v}」同时是另一条规则的标准形式，会产生链式替换",
                    source=v, target=standard, origin=origin))
            if v == standard:
                diags.append(Diagnostic(
                    "L-SMART-003", "error", f"变体「{v}」与标准形式同名，规则无意义",
                    source=v, target=standard, origin=origin))
    return diags


_RULE_CACHE: Dict[Tuple[str, str], Tuple[List[Tuple[str, str, Pattern[str]]],
                                         List[Diagnostic]]] = {}


def compile_rules(primitives: Dict[str, Dict[str, Any]], origin: str = "default"
                  ) -> Tuple[List[Tuple[str, str, Pattern[str]]], List[Diagnostic]]:
    """把映射表编译成 (变体, 标准词, 正则) 列表，按变体长度降序（长词优先）。

    中文边界用「前后不得是标识符字符」而非 ``\\b``：Python 的 ``\\b`` 对汉字
    全部是 ``\\w``，``\\b计划\\b`` 在中文上下文基本匹配不上（旧弹性层的坑）。
    结果按映射表内容缓存；返回副本，调用方可安全修改。
    """
    try:
        key = (origin, json.dumps(primitives, sort_keys=True, ensure_ascii=False))
        cached = _RULE_CACHE.get(key)
    except (TypeError, ValueError):
        key, cached = None, None
    if cached is not None:
        return list(cached[0]), [Diagnostic(**d.to_dict()) for d in cached[1]]

    diags = validate_map(primitives, origin=origin)
    bad_source = {d.source for d in diags if d.severity == "error"}
    rules: List[Tuple[str, str, Pattern[str]]] = []
    for standard, spec in primitives.items():
        if standard in bad_source or not isinstance(spec, dict):
            continue
        variants = spec.get("variants", [])
        if not isinstance(variants, list):
            continue
        for v in variants:
            if not isinstance(v, str) or v in bad_source:
                continue
            rules.append((v, standard, re.compile(r"(?<!\w)" + re.escape(v) + r"(?!\w)")))
    rules.sort(key=lambda r: len(r[0]), reverse=True)
    if key is not None:
        _RULE_CACHE[key] = (list(rules), [Diagnostic(**d.to_dict()) for d in diags])
    return rules, diags


# ---------------------------------------------------------------------------
# 配置解析
# ---------------------------------------------------------------------------

def _env_bool(name: str, default: Optional[bool] = None,
              env: Optional[Dict[str, str]] = None) -> Optional[bool]:
    raw = (os.environ if env is None else env).get(name)
    if raw is None:
        return default
    v = raw.strip().lower()
    if v in _TRUTHY:
        return True
    if v in _FALSY:
        return False
    return default


def _source_directive(source: str) -> Optional[str]:
    """扫描文件头 30 行里的 ``# @智能弹性 开|关`` 指令（容忍 BOM 与行尾注释）。"""
    for line in source.splitlines()[:30]:
        m = DIRECTIVE_RE.match(line.lstrip("\ufeff"))
        if m:
            return "on" if m.group(1).lower() in ("开", "on") else "off"
    return None


def resolve_config(source: str, file_path: Optional[str] = None,
                   env: Optional[Dict[str, str]] = None) -> Tuple[SmartConfig, List[Diagnostic]]:
    """解析生效配置。优先级：文件头指令 > 环境变量 > 映射表 > 默认关闭。"""
    diags: List[Diagnostic] = []
    env = os.environ if env is None else env

    map_path = env.get(ENV_MAP)
    origin_label = str(map_path or DEFAULT_MAP_PATH)
    try:
        raw = load_map(map_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        diags.append(Diagnostic(
            code="L-SMART-004", severity="error",
            message=f"映射表加载失败（{exc}），回退内置默认表",
            origin=origin_label))
        raw = {
            "schema": SCHEMA_MAP, "version": 1, "enabled": False,
            "scope": "identifier", "on_conflict": "diagnose",
            "primitives": _FALLBACK_PRIMITIVES,
        }
        origin_label = "内置兜底表"

    primitives = raw.get("primitives", {})
    origin = origin_label

    directive = _source_directive(source)
    if directive == "on":
        enabled = True
    elif directive == "off":
        enabled = False
    else:
        enabled = _env_bool(ENV_ENABLED, default=bool(raw.get("enabled", False)), env=env)

    trace = _env_bool(ENV_TRACE, default=enabled, env=env)
    on_conflict = str(env.get(ENV_CONFLICT, raw.get("on_conflict", "diagnose"))).lower()
    if on_conflict not in _CONFLICT_MODES:
        diags.append(Diagnostic(
            "L-SMART-005", "warning",
            f"未知 on_conflict「{on_conflict}」，按 diagnose 处理", origin=origin))
        on_conflict = "diagnose"

    cfg = SmartConfig(
        enabled=bool(enabled), trace=bool(trace), on_conflict=on_conflict,
        primitives=primitives, map_path=origin, directive=directive,
    )
    return cfg, diags


# ---------------------------------------------------------------------------
# 源码保护：字符串（英文/中文/三引号跨行） / 注释 / L4 嵌入块
# ---------------------------------------------------------------------------

def _indent_width(line: str) -> int:
    """按 lexer 口径计算前导缩进（\\t 记 4 列）。"""
    w = 0
    for c in line:
        if c == "\t":
            w += 4
        elif c == " ":
            w += 1
        else:
            break
    return w


def _embed_mask(lines: List[str]) -> List[bool]:
    """标记哪些行属于 L4 嵌入块（块内一个字符都不许改）。

    闭合方式与 lexer 对齐：``结束嵌入``/``结束引``、缩进回归、EOF。
    """
    mask = [False] * len(lines)
    i, n = 0, len(lines)
    while i < n:
        if not EMBED_START_RE.match(lines[i]):
            i += 1
            continue
        mask[i] = True
        open_indent = _indent_width(lines[i])
        body_indent: Optional[int] = None
        j = i + 1
        closed = False
        while j < n:
            cur = lines[j]
            if EMBED_END_RE.match(cur):
                mask[j] = True
                closed = True
                j += 1
                break
            if cur.strip() and open_indent >= 0:
                cur_indent = _indent_width(cur)
                if body_indent is None:
                    body_indent = cur_indent
                elif body_indent > open_indent and cur_indent <= open_indent:
                    closed = True          # 本行已回到外层，不属块
                    break
            mask[j] = True
            j += 1
        i = j if closed else n
    return mask


def _protect(lines: List[str], embed: Optional[List[bool]] = None) -> List[List[bool]]:
    """返回逐行逐字符的「可编辑」掩码；跨行维护字符串状态。

    覆盖：英文引号（含转义）、三引号跨行、中文引号「」『』、``#`` 注释。
    嵌入块整行不可编辑。
    """
    if embed is None:
        embed = _embed_mask(lines)
    out: List[List[bool]] = []
    triple: Optional[str] = None          # 当前三引号定界符
    quote: Optional[Tuple[str, bool]] = None   # (闭合符, 是否支持反斜杠转义)

    for idx, line in enumerate(lines):
        if embed[idx]:
            out.append([False] * len(line))
            continue
        flags = [True] * len(line)
        i, n = 0, len(line)
        while i < n:
            if triple is not None:
                k = line.find(triple, i)
                if k < 0:
                    for x in range(i, n):
                        flags[x] = False
                    i = n
                    break                     # 三引号未闭合，状态延续到下一行
                for x in range(i, k + 3):
                    flags[x] = False
                triple = None
                i = k + 3
                continue
            if quote is not None:
                closing, escapable = quote
                flags[i] = False
                c = line[i]
                if escapable and c == "\\" and i + 1 < n:
                    flags[i + 1] = False
                    i += 2
                    continue
                if c == closing:
                    quote = None
                i += 1
                continue
            c = line[i]
            if c == "#":
                for x in range(i, n):
                    flags[x] = False
                break
            if c in _QUOTE_CLOSE:
                if c in _ESCAPABLE and line[i:i + 3] == c * 3:
                    flags[i] = flags[i + 1] = flags[i + 2] = False
                    triple = c * 3
                    i += 3
                    continue
                flags[i] = False
                quote = (_QUOTE_CLOSE[c], c in _ESCAPABLE)
                i += 1
                continue
            i += 1
        out.append(flags)
    return out


def _protected_flags(line: str) -> List[bool]:
    """单行便捷入口（不感知跨行状态，仅供外部/调试使用）。"""
    return _protect([line])[0]


def _replace_in_line(line: str, flags: List[bool],
                     rules: List[Tuple[str, str, Pattern[str]]],
                     line_no: int, rewrites: List[Dict[str, Any]]) -> str:
    """在可编辑片段内应用规则；缩进、字符串、注释逐字符保留。"""
    out: List[str] = []
    i, n = 0, len(line)
    while i < n:
        editable = flags[i] if i < len(flags) else True
        j = i
        while j < n and (flags[j] if j < len(flags) else True) == editable:
            j += 1
        frag = line[i:j]
        if editable and frag:
            # 加空格哨兵，让 lookaround 在片段两端也正确判定中文词边界
            padded = " " + frag + " "
            for variant, standard, pattern in rules:
                def _sub(m: re.Match, _v=variant, _s=standard, _off=i) -> str:
                    rewrites.append({
                        "line": line_no, "from": _v, "to": _s,
                        "column": max(0, _off + m.start() - 1),
                    })
                    return _s
                padded, _ = pattern.subn(_sub, padded)
            frag = padded[1:-1]
        out.append(frag)
        i = j
    return "".join(out)


def _masked_text(lines: List[str], flags_all: List[List[bool]],
                 embed: List[bool]) -> List[str]:
    """把字符串/注释/嵌入块内容替换成等长空格，保持列号不变。"""
    out: List[str] = []
    for idx, line in enumerate(lines):
        if embed[idx]:
            out.append(" " * len(line))
            continue
        flags = flags_all[idx]
        out.append("".join(ch if ok else " " for ch, ok in zip(line, flags)))
    return out


def _editable_text(source: str) -> str:
    """用于混用检测的纯代码文本（字符串/注释/嵌入块以空格占位）。"""
    lines = source.splitlines()
    embed = _embed_mask(lines)
    flags_all = _protect(lines, embed)
    return "\n".join(_masked_text(lines, flags_all, embed))


def _detect_mixed_usage(source: str, rules: List[Tuple[str, str, Pattern[str]]],
                        map_path: str) -> List[Diagnostic]:
    """L-SMART-002：同一源码里口语变体与标准双字形式混用，替换后可能合并两个名字。

    注意边界：本诊断只覆盖「变体与标准词在同一文件同现」。若用户原本就有个标识符
    恰好叫「计划」而文件里没有「规划」，文本级替换会把它改名且**无法与口语用法区分**
    （见设计文档 R13），此时请用 ``on_conflict=keep`` 或关闭弹性层。
    """
    code = _editable_text(source)
    standards = {target for _, target, _ in rules}
    diags: List[Diagnostic] = []
    for standard in sorted(standards):
        std_pat = re.compile(r"(?<!\w)" + re.escape(standard) + r"(?!\w)")
        if not std_pat.search(code):
            continue
        for variant, target, pattern in rules:
            if target != standard:
                continue
            m = pattern.search(code)
            if not m:
                continue
            line_no = code[:m.start()].count("\n") + 1
            col = m.start() - (code.rfind("\n", 0, m.start()) + 1) + 1
            diags.append(Diagnostic(
                "L-SMART-002", "warning",
                f"「{variant}」与标准形式「{standard}」在同一文件混用；"
                f"归一化后两者会指向同一标识符，请确认这是预期",
                source=variant, target=standard, line=line_no, column=col,
                origin=map_path))
    return diags


# ---------------------------------------------------------------------------
# 可观测性：编译期只读扫描 L0 组合惯用模式
# ---------------------------------------------------------------------------

def _kind_of(primitives: Dict[str, Any], name: str) -> str:
    """容错取 kind：映射表里某条 spec 可能不是对象（坏表），不能让它抛异常。"""
    spec = primitives.get(name)
    if isinstance(spec, dict):
        kind = spec.get("kind")
        if isinstance(kind, str) and kind:
            return kind
    return "custom"


def build_trace(source: str, primitives: Dict[str, Dict[str, Any]],
                rewrites: List[Dict[str, Any]], duration_ms: float,
                file_path: Optional[str] = None) -> Dict[str, Any]:
    """产出结构化轨迹。只读扫描，不改 AST、不改生成代码。

    events[].type ∈ {tool_call, decision_point, side_effect, duration, primitive_def}
    扫描前先做保护掩码，字符串/注释里的示例词不会产生假事件。
    """
    lines = source.splitlines()
    embed = _embed_mask(lines)
    flags_all = _protect(lines, embed)
    masked = _masked_text(lines, flags_all, embed)

    names = list(primitives.keys())
    call_re = (re.compile(r"(?<!\w)(" + "|".join(re.escape(n) for n in names) + r")[ \t]*\(")
               if names else None)
    events: List[Dict[str, Any]] = []
    current_primitive: Optional[str] = None
    seen: set = set()

    for line_no, line in enumerate(masked, 1):
        if not line.strip():
            continue                      # 空行 / 整行注释 / 嵌入块
        m = DEFINE_RE.match(line)
        if m:
            name = m.group(2)
            current_primitive = name if name in primitives else None
            if current_primitive:
                seen.add(name)
                events.append({
                    "type": "primitive_def", "line": line_no,
                    "primitive": name,
                    "kind": _kind_of(primitives, name),
                    "l0_form": m.group(1),
                })
            continue

        if call_re:
            for cm in call_re.finditer(line):
                name = cm.group(1)
                seen.add(name)
                events.append({
                    "type": "tool_call", "line": line_no,
                    "primitive": name,
                    "kind": _kind_of(primitives, name),
                    "callee": name,
                    "scope": current_primitive or "主流程",
                })

        im = IF_RE.match(line)
        if im:
            events.append({
                "type": "decision_point", "line": line_no,
                "primitive": current_primitive or "主流程",
                "condition": " ".join(im.group(1).split()),
                "l0_form": "若",
            })

        if PRINT_RE.search(line):
            events.append({
                "type": "side_effect", "line": line_no,
                "primitive": current_primitive or "主流程",
                "kind": "print",
            })

        wm = WHILE_RE.match(line)
        if wm:
            cond = " ".join(wm.group(1).split())
            bound = STATIC_BOUND_RE.search(cond)
            events.append({
                "type": "duration", "line": line_no,
                "primitive": current_primitive or "主流程",
                "phase": "loop", "metric": "iterations",
                "static_bound": int(bound.group(1)) if bound else None,
                "condition": cond, "l0_form": "当",
            })

    # 惯用模式 = 双字标准原语的三段调用 + 至少一处 L0 循环骨架。
    # 只有调用、没有循环的散点不算模式（避免乱序三连被误报）。
    has_loop = any(e["type"] == "duration" for e in events)
    pattern = ("observe_plan_act"
               if {"观察", "规划", "执行"}.issubset(seen) and has_loop else "custom")
    return {
        "schema": SCHEMA_TRACE,
        "file": str(file_path) if file_path else None,
        "pattern": pattern,
        "primitives": {n: _kind_of(primitives, n) for n in names},
        "duration_ms": round(duration_ms, 3),
        "rewrites": rewrites,
        "events": events,
    }


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def preprocess(source: str, config: Optional[SmartConfig] = None,
               file_path: Optional[str] = None,
               env: Optional[Dict[str, str]] = None) -> SmartResult:
    """纯函数式预处理：返回归一化源码 + 诊断 + 轨迹，不产生任何外部副作用。

    ``enabled=False`` 时返回原始 ``source`` 对象，保证逐字节不变。
    """
    t0 = time.perf_counter()
    if config is None:
        config, config_diags = resolve_config(source, file_path=file_path, env=env)
    else:
        config_diags = []

    if not config.effective:
        return SmartResult(source=source, enabled=False, diagnostics=config_diags)

    rules, rule_diags = compile_rules(config.primitives, origin=config.map_path or "default")

    # 冲突类诊断（001/002/003）受 on_conflict 控制；配置类（004/005）永不被吞，
    # 否则用户会误以为自己配置的映射表生效了。
    conflict = list(rule_diags)
    conflict.extend(_detect_mixed_usage(source, rules, config.map_path or "default"))
    if config.on_conflict == "keep":
        conflict = []
    elif config.on_conflict == "warn":
        conflict = [Diagnostic(**{**d.to_dict(), "severity": "warning"}) for d in conflict]
    diags = list(config_diags) + conflict

    lines = source.splitlines(keepends=True)
    stripped = [ln.rstrip("\r\n") for ln in lines]
    endings = [ln[len(s):] for ln, s in zip(lines, stripped)]
    embed = _embed_mask(stripped)
    flags_all = _protect(stripped, embed)

    new_lines: List[str] = []
    rewrites: List[Dict[str, Any]] = []
    for line_no, (raw, newline, flags, in_embed) in enumerate(
            zip(stripped, endings, flags_all, embed), 1):
        if in_embed:
            new_lines.append(raw + newline)       # L4 嵌入块整行原样透传
            continue
        new_lines.append(_replace_in_line(raw, flags, rules, line_no, rewrites) + newline)

    new_source = "".join(new_lines)
    duration_ms = (time.perf_counter() - t0) * 1000
    trace: Dict[str, Any] = {}
    if config.trace:
        trace = build_trace(new_source, config.primitives, rewrites,
                            duration_ms, file_path=file_path)
        trace["diagnostics"] = [d.to_dict() for d in diags]
    return SmartResult(
        source=new_source, enabled=True, diagnostics=diags,
        trace=trace, rewrites=rewrites,
    )


def apply_smart_elastic(source: str, file_path: Optional[str] = None) -> str:
    """CLI 便捷入口：默认关闭；开启时输出诊断并写 sidecar 轨迹文件。

    关闭路径只做一次文件头正则 + 环境变量字典查询，**不 import 本模块之外的东西、
    不读映射表**，源码对象原样返回 —— 现有测试行为完全不变。
    """
    directive = _source_directive(source)
    if directive == "off":
        return source
    if directive != "on":
        env = os.environ
        if ENV_ENABLED in env:
            if not _env_bool(ENV_ENABLED, default=False):
                return source
        elif ENV_MAP not in env:
            # 无文件头指令、无环境变量：默认关闭。
            # 自定义映射表的 enabled 字段需要读表才知道，因此上面 ENV_MAP 分支放行。
            return source

    result = preprocess(source, file_path=file_path)
    if not result.enabled:
        return source
    for d in result.diagnostics:
        loc = f"第 {d.line} 行" if d.line else "配置"
        print(f"[智能弹性·{d.severity}] {d.code} {loc}: {d.message}", file=sys.stderr)
    if result.trace and file_path:
        out = Path(str(file_path) + ".smart-trace.json")
        try:
            out.write_text(json.dumps(result.trace, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        except OSError as exc:
            print(f"[智能弹性·warning] 轨迹写入失败: {exc}", file=sys.stderr)
    return result.source
