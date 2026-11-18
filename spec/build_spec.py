# -*- coding: utf-8 -*-
"""抽取并生成 ``spec/light.spec.json``（光明语言的机器可读权威表）。

用法::

    PYTHONPATH=src python3 -m spec.build_spec           # 写入 spec/light.spec.json
    PYTHONPATH=src python3 -m spec.build_spec --check   # 与仓内现状比对，不一致 rc=1

设计口径
--------
* **只从仓里抽事实**：L0 字表读 ``docs/language/l0-core.md``（44 字权威），
  关键字读 ``src/keywords.py`` 的真实集合，运算符读 ``src/code_generator.py``
  的 ``operator_map`` / 语句级 ``py_ops`` 与词法层的实测记号，stdlib 读
  ``stdlib/*.light`` 的「导出」清单并用同名 ``.py`` / ``.light`` 的函数签名
  补参数信息，diagnostics 读 ``src/diagnostics/registry.py``。
* **不知道就写 null**：抽不到的 arity / 返回值一律 ``null``，绝不用默认值凑数。
* **确定性**：输出只依赖仓内文件内容（``generated_from`` 存内容指纹，不存
  commit），同一份源必生成逐字节相同的 JSON，``--check`` 才有意义。
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SPEC_PATH = Path(__file__).resolve().parent / "light.spec.json"
SPEC_VERSION = 1

# 参与指纹的来源文件（相对仓根）。stdlib 目录单独做汇总指纹。
FINGERPRINT_FILES = (
    "src/keywords.py",
    "src/lexer.py",
    "src/code_generator.py",
    "src/version.py",
    "src/diagnostics/registry.py",
    "docs/language/l0-core.md",
    "docs/language/keywords.md",
    "docs/language/l1-l2-style.md",
    "docs/language/operators.md",
    "docs/分层语法设计_v4.0.md",
    "tests/unit/test_spec_docs_sync.py",
)


def _ensure_src_on_path() -> None:
    p = str(SRC)
    if p not in sys.path:
        sys.path.insert(0, p)


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_normalized(path: Path) -> str:
    """按「行尾归一为 LF」后的内容取 sha256（指纹专用）。

    仓库 ``core.autocrlf=true`` 时，Windows 检出把文本落成 CRLF，而 git blob 是
    LF；若指纹直接取磁盘原始字节，**同一份提交**在 Windows 与 Linux/FreeBSD
    上会算出不同的值，``--check`` 就在非 Windows 检出上假红（T-0388）。

    归一的是**输入文件**，不是输出 JSON：输出侧本来就只有 LF。
    """
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# =============================================================================
# 文档解析
# =============================================================================

_L0_SECTION_RE = re.compile(r"^## (.+)（(\d+)字）\s*$")
_L0_ROW_RE = re.compile(r"^\| `(.)` \| (.+?) \|\s*$")


def parse_l0_core() -> dict:
    """解析 docs/language/l0-core.md，返回 {字: {语义, 章节}} 与声明总数。"""
    text = _read(ROOT / "docs/language/l0-core.md")
    declared = None
    m = re.search(r"包含 (\d+) 个单字关键字", text)
    if m:
        declared = int(m.group(1))

    chars: dict[str, dict] = {}
    section = None
    for line in text.splitlines():
        hm = _L0_SECTION_RE.match(line)
        if hm:
            section = hm.group(1)
            continue
        rm = _L0_ROW_RE.match(line)
        if rm and section:
            ch, semantic = rm.group(1), rm.group(2).strip()
            # 同一字重复出现时保留首次（文档是逐章节的唯一权威）
            chars.setdefault(ch, {"语义": semantic, "章节": section})
    return {"声明总数": declared, "字": chars}


_LANDING_RE = re.compile(r"^_落地范式\s*(?::.*)?=\s*\{", re.MULTILINE)


def parse_landing_paradigm() -> dict[str, str]:
    """从 tests/unit/test_spec_docs_sync.py 读 ``_落地范式`` 登记表。

    这张表是「文档承诺字 ↔ 代码落地位置」的唯一连接，A/B/C 范式由它定义；
    直接 AST 取字面量，避免 import 测试文件。
    """
    path = ROOT / "tests" / "unit" / "test_spec_docs_sync.py"
    tree = ast.parse(_read(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == "_落地范式":
                return ast.literal_eval(node.value)
    raise RuntimeError("test_spec_docs_sync.py 里找不到 _落地范式 登记表")


_ALIAS_ROW_RE = re.compile(r"^\| `(.+?)` \| (.+?) \|\s*$")


def parse_keyword_aliases() -> dict[str, list[str]]:
    """从两份文档抽「主形式 → 别名」：

    * ``docs/language/l1-l2-style.md`` 的 L0/L1 对照表（严格一对一）；
    * ``docs/language/keywords.md`` 的 v3.3 兼容别名表（只取别名数与目标数相等的行，
      3:2 这类有歧义的行跳过，不猜配对）。
    """
    alias_to_main: dict[str, str] = {}

    def _absorb(main_col: str, alias_col: str) -> None:
        mains = re.findall(r"`(.+?)`", main_col)
        aliases = re.findall(r"`(.+?)`", alias_col)
        if len(mains) == 1:
            for a in aliases:
                alias_to_main.setdefault(a, mains[0])
        elif len(mains) == len(aliases) and len(mains) > 1:
            for a, mn in zip(aliases, mains):
                alias_to_main.setdefault(a, mn)
        # 其余形态（如 3 别名 → 2 主形式）不配对，跳过

    style = _read(ROOT / "docs/language/l1-l2-style.md")
    in_table = False
    for line in style.splitlines():
        if line.startswith("| L0 单字 | L1 双字别名 |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0] not in ("L0 单字",) and not cells[0].startswith("---"):
                _absorb(cells[0], cells[1])

    kw = _read(ROOT / "docs/language/keywords.md")
    in_table = False
    for line in kw.splitlines():
        if line.startswith("| 别名 | 对应 v4.0 |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0] not in ("别名",) and not cells[0].startswith("---"):
                _absorb(cells[1], cells[0])

    out: dict[str, list[str]] = {}
    for alias, main in alias_to_main.items():
        out.setdefault(main, []).append(alias)
    return {k: sorted(v) for k, v in sorted(out.items())}


# =============================================================================
# 关键字
# =============================================================================

_KEYWORD_TABLES = (
    ("KEYWORDS_DEFINE", "定义声明"),
    ("KEYWORDS_CONDITION", "条件判断"),
    ("KEYWORDS_LOOP", "循环控制"),
    ("KEYWORDS_FUNCTION", "函数定义"),
    ("KEYWORDS_TYPE", "类型修饰"),
    ("KEYWORDS_EXCEPTION", "异常处理"),
    ("KEYWORDS_CLASS", "类与对象"),
    ("KEYWORDS_MODULE", "模块系统"),
    ("KEYWORDS_ASYNC", "异步/并发"),
    ("KEYWORDS_GENERATOR", "生成器"),
    ("KEYWORDS_MATCH", "模式匹配"),
    ("KEYWORDS_CONTEXT", "上下文管理器"),
    ("KEYWORDS_EMBED", "嵌入块"),
    ("KEYWORDS_DECORATOR", "装饰器"),
    ("KEYWORDS_FFI", "C FFI"),
    ("KEYWORDS_LOGIC", "逻辑运算"),
    ("KEYWORDS_SPECIAL", "特殊值"),
    ("KEYWORDS_RESERVED", "保留字"),
)


# 书名号/引号单独一个字符不构成完整记号（词法器会报未闭合），
# 但它们的 TokenType 是确定的；单独查询时直接给出映射，不做「装进样例再取」。
_SINGLE_TOKEN_OVERRIDE = {'"': "STRING", "'": "STRING", "《": "LBOOK", "》": "RBOOK", "\\": "COMMA"}


def _lex_first_token(word: str) -> tuple[str, object]:
    """返回 word 单独词法化后的第一个有效 token 的 (类型名, 值)。"""
    if word in _SINGLE_TOKEN_OVERRIDE:
        return _SINGLE_TOKEN_OVERRIDE[word], word
    _ensure_src_on_path()
    from lexer import Lexer
    from tokens import TokenType

    skip = {TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT, TokenType.EOF}
    try:
        for tok in Lexer(word).tokenize():
            if tok.type in skip:
                continue
            return tok.type.name, tok.value
    except Exception:  # 词法拒绝（例如裸 ^）→ 按非关键字处理
        return "ERROR", None
    return "EOF", None


def _is_keyword_token(word: str) -> bool:
    # 只看「词法层是否把它当 KEYWORD」。个别别名会在 tokenize 末尾重映射
    # （lexer._BREAK_ALIAS: 退出循环 → 跳出），值变了但仍是关键字，不能因此
    # 判成「可作标识符」。
    kind, _value = _lex_first_token(word)
    return kind == "KEYWORD"


def build_keywords() -> list[dict]:
    _ensure_src_on_path()
    import keywords as kw

    l0 = parse_l0_core()
    landing = parse_landing_paradigm()
    aliases = parse_keyword_aliases()

    role_sets: dict[str, list[str]] = {}
    for table, role in _KEYWORD_TABLES:
        for word in getattr(kw, table):
            role_sets.setdefault(word, [])
            if role not in role_sets[word]:
                role_sets[word].append(role)
    for word in kw.VERB_ARITY:
        role_sets.setdefault(word, [])
        if "运算符动词" not in role_sets[word]:
            role_sets[word].append("运算符动词")

    all_words = set(kw.ALL_KEYWORDS) | set(kw.VERB_ARITY) | set(l0["字"])

    # 文档登记、但已从关键字表降级为「上下文关键字」的别名（当前只有 `属性`：
    # L-021 把它移出 KEYWORDS_CLASS，改由 parser 在类体位置识别 IDENTIFIER）。
    # 这些词仍是语言承诺的保留写法，不能因为不在 ALL_KEYWORDS 就从权威表里消失。
    for alias in (a for als in aliases.values() for a in als):
        kind, _value = _lex_first_token(alias)
        if kind != "ERROR":
            all_words.add(alias)

    alias_of: dict[str, str] = {}
    for main, als in aliases.items():
        for a in als:
            alias_of.setdefault(a, main)

    items = []
    for word in sorted(all_words, key=lambda w: (len(w), w)):
        doc = l0["字"].get(word)
        main = alias_of.get(word)
        if doc:
            semantic = doc["语义"]
        elif role_sets.get(word):
            semantic = "、".join(role_sets[word])
        elif main and main in l0["字"]:
            semantic = l0["字"][main]["语义"]
        else:
            semantic = "别名"
        src = []
        if doc:
            src.append("docs/language/l0-core.md")
        for table, role in _KEYWORD_TABLES:
            if word in getattr(kw, table):
                src.append(f"src/keywords.py:{table}")
        if word in kw.VERB_ARITY:
            src.append("src/keywords.py:VERB_ARITY")
        if not src and main:
            src.append("docs/language/keywords.md / docs/language/l1-l2-style.md")

        category = "、".join(role_sets.get(word, []))
        if not category:
            category = "L0 规范条目" if word in l0["字"] else ("文档登记别名（上下文）" if main else "")

        item = {
            "字": word,
            "作用": semantic,
            "类别": category,
            "是否可作标识符": not _is_keyword_token(word),
            "来源": "；".join(src) if src else "src/keywords.py",
        }
        if not doc and not role_sets.get(word) and main:
            item["备注"] = (
                f"词法层是 IDENTIFIER；文档登记为「{main}」的别名，"
                "parser 只在特定位置把它当关键字（上下文关键字）"
            )
        if word in l0["字"]:
            item["层级"] = "L0"
            item["范式"] = landing.get(word)
            if item["范式"] == "A":
                item["备注"] = "范式 A：词法层发 IDENTIFIER，只在类体/接口体等特定位置当关键字"
            elif item["范式"] == "C":
                item["备注"] = "范式 C：词法层发 IDENTIFIER，调用点由 code_generator.builtin_map 映射"
        if word in alias_of:
            item["主形式"] = alias_of[word]
        elif aliases.get(word):
            item["别名"] = aliases[word]
        items.append(item)
    return items


# =============================================================================
# 运算符
# =============================================================================

# 目标（Python 侧符号）→ (名称, 类别, canonical 光明形态)
_OP_TARGET_META = {
    "+": ("加法", "算术", "+"),
    "-": ("减法", "算术", "-"),
    "*": ("乘法", "算术", "*"),
    "/": ("除法", "算术", "/"),
    "//": ("整除", "算术", "整除"),
    "%": ("取模", "算术", "模"),
    "**": ("幂", "算术", "幂"),
    ">": ("大于", "比较", ">"),
    "<": ("小于", "比较", "<"),
    "==": ("等于", "比较", "=="),
    "!=": ("不等于", "比较", "!="),
    ">=": ("大于等于", "比较", ">="),
    "<=": ("小于等于", "比较", "<="),
    "and": ("逻辑与", "逻辑", "且"),
    "or": ("逻辑或", "逻辑", "或"),
    "not": ("逻辑非", "逻辑", "非"),
    "&": ("位与", "位运算", "位与"),
    "|": ("位或", "位运算", "位或"),
    "^": ("位异或", "位运算", "位异或"),
    "<<": ("左移", "位运算", "左移"),
    ">>": ("右移", "位运算", "右移"),
    "~": ("位非", "位运算", "位非"),
}

# 标点/结构记号：canonical, 名称, 类别, 全角写法, 状态, 说明
_PUNCTUATION = (
    ("。", "语句结束符", "语句", [], "可用", "唯一的语句结束符；半角 . 不等价（`1.` 会被读成浮点 1.0）"),
    (".", "成员访问/小数点", "结构", [], "可用", "只作成员访问或小数点，不能当语句结束符"),
    (",", "逗号", "分隔", ["，"], "可用", "表达式/参数分隔；不是管道（语句位置落成调用嵌套）"),
    ("\\", "参数分隔（顿号）", "分隔", ["、"], "可用", "等价于逗号，用于并列参数"),
    (";", "语句分隔", "分隔", ["；"], "可用", "同一行内分隔两条语句"),
    (":", "块起始/键值分隔", "结构", ["："], "可用", "若/段/类等块头与字典键值都用它"),
    ("(", "左圆括号", "结构", ["（"], "可用", ""),
    (")", "右圆括号", "结构", ["）"], "可用", ""),
    ("[", "左方括号", "结构", ["【"], "可用", ""),
    ("]", "右方括号", "结构", ["】"], "可用", ""),
    ("{", "左花括号", "结构", ["｛"], "可用", ""),
    ("}", "右花括号", "结构", ["｝"], "可用", ""),
    ("《", "左书名号", "结构", [], "可用", "书名号调用必须带括号：`《排序》(列表)`；`《排序》列表` 不成立"),
    ("》", "右书名号", "结构", [], "可用", ""),
    ('"', "字符串引号（双）", "字面量", ["「", "」"], "可用", "「…」与 \"…\" 等价"),
    ("'", "字符串引号（单）", "字面量", ["『", "』"], "可用", "『…』与 '…' 等价"),
    ("=", "赋值（符号形式）", "赋值", [], "可用", "`设 甲 = 1。` 与 `设 甲 为 1。` 都成立；首选 `为`"),
    ("@", "装饰器标记", "结构", [], "可用", ""),
    ("!", "可空解包", "一元", ["！"], "可用", "`甲!` 生成 _light_unwrap(甲)"),
    ("->", "箭头", "管道", [], "不可用", "解析器报「意外的标记 ->」；不要当管道用"),
    (":=", "海象运算符", "赋值", [], "不可用", "词法识别为 WALRUS，但解析器不支持"),
    ("|", "竖线", "结构", [], "不可用", "表达式位置报语法错误"),
    ("^", "脱字符", "结构", [], "不可用", "词法器「未知字符」；幂运算用 `幂`"),
)

# 语句级复合赋值：canonical, 名称, 别名, 是否实测
_COMPOUND_ASSIGN = (
    ("+=", "加后赋值", ["加上"], True),
    ("-=", "减后赋值", ["减去"], True),
    ("*=", "乘后赋值", ["乘以"], True),
    ("/=", "除后赋值", ["除以"], True),
)


def parse_codegen_operator_maps() -> tuple[dict, dict]:
    """AST 读取 code_generator.py 的 operator_map 与语句级 py_ops（不 import）。"""
    tree = ast.parse(_read(ROOT / "src/code_generator.py"))
    operator_map = None
    py_ops = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Attribute) and t.attr == "operator_map":
                operator_map = ast.literal_eval(node.value)
            if isinstance(t, ast.Name) and t.id == "py_ops" and py_ops is None:
                py_ops = ast.literal_eval(node.value)
    if operator_map is None:
        raise RuntimeError("code_generator.py 里找不到 self.operator_map")
    return operator_map, py_ops or {}


def _token_of(symbol: str) -> str:
    return _lex_first_token(symbol)[0]


# operator_map 里存在、但词法/语法层并不接受的符号别名：不写进「别名」，
# 否则等于告诉 Agent 一个会报错的写法是合法的。
_UNAVAILABLE_ALIASES = frozenset({"^", "|", "&", "~", "<<", ">>", "**", "//", "+=", "-=", "*=", "/="})

# 标点/结构记号的 TokenType（直接读 lexer 的映射表，字符串引号单独标注）
_PUNCT_TOKEN = {
    "。": "PERIOD", ".": "DOT", ",": "COMMA", "\\": "COMMA", ";": "SEMICOLON",
    ":": "COLON", "(": "LPAREN", ")": "RPAREN", "[": "LBRACKET", "]": "RBRACKET",
    "{": "LBRACE", "}": "RBRACE", "《": "LBOOK", "》": "RBOOK",
    '"': "STRING", "'": "STRING", "=": "EQUALS", "@": "AT", "!": "BANG",
    "->": "ARROW", ":=": "WALRUS", "|": "PIPE", "^": "ERROR",
}


def _alias_is_usable(alias: str) -> bool:
    if alias in _UNAVAILABLE_ALIASES:
        return False
    kind, _value = _lex_first_token(alias)
    return kind != "ERROR"


def _op_token(canonical: str) -> str:
    if canonical in _PUNCT_TOKEN:
        return _PUNCT_TOKEN[canonical]
    if all(ord(c) < 128 for c in canonical) and len(canonical) <= 2:
        return _token_of(canonical)
    return "KEYWORD"


def build_operators() -> list[dict]:
    operator_map, _py_ops = parse_codegen_operator_maps()

    grouped: dict[str, list[str]] = {}
    for alias, target in operator_map.items():
        grouped.setdefault(target, []).append(alias)

    items = []
    for target, aliases in sorted(grouped.items(), key=lambda kv: kv[0]):
        if target not in _OP_TARGET_META:
            continue
        name, kind, canonical = _OP_TARGET_META[target]
        alias_list = sorted(a for a in aliases if a != canonical and _alias_is_usable(a))
        item = {
            "canonical": canonical,
            "名称": name,
            "类别": kind,
            "语义": target,
            "别名": alias_list,
            "全角": [],
            "半角": [canonical] if all(ord(c) < 128 for c in canonical) else [],
            "记号": _op_token(canonical),
            "状态": "可用",
            "来源": "src/code_generator.py:operator_map",
        }
        if canonical == "整除":
            item["说明"] = "源码里 `//` 是注释，整除只能写「整除」"
        if canonical == "幂":
            item["说明"] = "源码里没有 `**` 记号（词法切成两个 STAR），幂只能写「幂」"
        items.append(item)

    # 包含关系（parser 用 @@contains@@ 中缀识别，不在 operator_map 里）
    items.append({
        "canonical": "包含",
        "名称": "包含关系",
        "类别": "比较",
        "语义": "in",
        "别名": ["在"],
        "全角": [],
        "半角": [],
        "记号": "KEYWORD",
        "状态": "可用",
        "来源": "src/parser_expr.py:@@contains@@（实测 `包含`/`在` 生成 in）",
    })

    for canonical, name, aliases, verified in _COMPOUND_ASSIGN:
        items.append({
            "canonical": canonical,
            "名称": name,
            "类别": "复合赋值",
            "语义": canonical,
            "别名": aliases,
            "全角": [],
            "半角": [canonical],
            "记号": "语句级（不是表达式运算符）",
            "状态": "可用",
            "已实测": verified,
            "来源": "src/code_generator.py:py_ops（语句级）",
            "说明": "`甲 加上 1。` 生成 `甲 += 1`；符号 `+=` 本身不被源码接受"
                    if canonical == "+=" else "",
        })

    for canonical, name, kind, fullwidth, status, note in _PUNCTUATION:
        items.append({
            "canonical": canonical,
            "名称": name,
            "类别": kind,
            "别名": [],
            "全角": fullwidth,
            "半角": [canonical] if all(ord(c) < 128 for c in canonical) else [],
            "记号": _PUNCT_TOKEN[canonical],
            "状态": status,
            "来源": "src/lexer.py:_SYMBOL_TOKEN_MAP / SYMBOL_MAP（T-0377 实测）",
            "说明": note,
        })

    # 字段裁剪：空字符串/空列表保留（schema 稳定），但"说明"为空时删掉
    for it in items:
        if not it.get("说明"):
            it.pop("说明", None)
        if not it.get("已实测"):
            it.pop("已实测", None)
    return items


# =============================================================================
# stdlib
# =============================================================================

_EXPORT_RE = re.compile(r"^导出\s+(.+?)[。；]?\s*$")
_LIGHT_DEF_PAREN_RE = re.compile(r"^(?:段落|函数|段)\s+([^\s(（]+)\s*[（(](.*?)[）)]\s*[:：]?\s*$")
_LIGHT_DEF_RECEIVE_RE = re.compile(r"^(?:段落|函数|段)\s+([^\s(（]+)\s+接收\s+(.*?)\s*[:：]\s*$")
_LIGHT_RETURN_RE = re.compile(r"^\s*(?:返回|返)\s+(.+?)\s*$")


def _split_params(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    # 参数分隔只用逗号/顿号；字符串里的逗号不常见，若出现会多算一个参数，
    # 但这类签名在仓里不存在（生成物会随之变化，--check 会报出来）。
    parts = re.split(r"[,，、]", text)
    return [p.strip() for p in parts if p.strip()]


def _param_stats(params: list[str]) -> tuple[int, int, bool]:
    """返回 (参数个数, 必填参数, 可变参数)。"""
    variadic = False
    required = 0
    for p in params:
        p = p.strip()
        if p.startswith("*") or p.startswith("…") or p.startswith("..."):
            variadic = True
            continue
        has_default = ("=" in p) or bool(re.search(r"\s(?:等于|为)\s", p))
        if not has_default:
            required += 1
    return len(params), required, variadic


def _light_defs(path: Path) -> dict[str, dict]:
    """解析 .light 里的函数定义（段落/函数/段），返回 {名字: 签名信息}。"""
    lines = _read(path).splitlines()
    defs: dict[str, dict] = {}
    for idx, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        m = _LIGHT_DEF_PAREN_RE.match(line) or _LIGHT_DEF_RECEIVE_RE.match(line)
        if not m:
            continue
        name, params_text = m.group(1), m.group(2)
        params = _split_params(params_text)
        total, required, variadic = _param_stats(params)
        base_indent = len(raw) - len(raw.lstrip())
        returns: bool | None = False
        for nxt in lines[idx + 1:]:
            if not nxt.strip():
                continue
            indent = len(nxt) - len(nxt.lstrip())
            if indent <= base_indent:
                break
            rm = _LIGHT_RETURN_RE.match(nxt.strip())
            if rm:
                rest = rm.group(1).strip().rstrip("。.")
                if rest:
                    returns = True
        defs.setdefault(name, {
            "参数个数": total,
            "必填参数": required,
            "可变参数": variadic,
            "是否返回": returns,
            "来源": f"{_rel(path)}:{idx + 1}",
        })
    return defs


def _py_defs(path: Path) -> dict[str, dict]:
    """解析 .py 的顶层函数定义（AST），返回 {名字: 签名信息}。"""
    try:
        tree = ast.parse(_read(path))
    except SyntaxError:
        return {}

    def _has_value_return(fn: ast.AST) -> bool:
        stack = list(getattr(fn, "body", []))
        while stack:
            node = stack.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue  # 嵌套函数的 return 不算外层
            if isinstance(node, ast.Return) and node.value is not None:
                return True
            stack.extend(ast.iter_child_nodes(node))
        return False

    defs: dict[str, dict] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        a = node.args
        total = len(a.posonlyargs) + len(a.args)
        required = total - len(a.defaults)
        variadic = bool(a.vararg or a.kwarg)
        defs.setdefault(node.name, {
            "参数个数": total,
            "必填参数": required,
            "可变参数": variadic,
            "是否返回": _has_value_return(node),
            "来源": f"{_rel(path)}:{node.lineno}",
        })
    return defs


def build_stdlib() -> dict:
    _ensure_src_on_path()
    from keywords import STDLIB_VERB_ARITY

    stdlib = ROOT / "stdlib"
    modules = []
    for light_path in sorted(stdlib.glob("*.light")):
        module = light_path.name[:-len(".light")]
        lines = _read(light_path).splitlines()
        names: list[str] = []
        for line in lines:
            s = line.strip()
            if not s.startswith("导出"):
                continue
            m = _EXPORT_RE.match(s)
            if not m:
                continue
            for n in m.group(1).split():
                n = n.strip().rstrip("。；，,")
                if n and n not in names:
                    names.append(n)
        if not names:
            continue

        ldefs = _light_defs(light_path)
        py_path = light_path.with_suffix(".py")
        pdefs = _py_defs(py_path) if py_path.is_file() else {}

        entries = []
        for name in names:
            obs = []
            if name in ldefs:
                obs.append(("light-def", ldefs[name]))
            if name in pdefs:
                obs.append(("py-def", pdefs[name]))
            if name in STDLIB_VERB_ARITY:
                v = STDLIB_VERB_ARITY[name]
                obs.append(("verb-arity", {
                    "参数个数": None if v < 0 else v,
                    "必填参数": None if v < 0 else v,
                    "可变参数": v < 0,
                    "是否返回": None,
                    "来源": f"src/keywords.py:STDLIB_VERB_ARITY[{name!r}]",
                }))

            if not obs:
                entry = {
                    "名字": name,
                    "参数个数": None,
                    "必填参数": None,
                    "可变参数": None,
                    "是否返回": None,
                    "来源": None,
                }
            else:
                chosen = obs[0][1]
                entry = {
                    "名字": name,
                    "参数个数": chosen["参数个数"],
                    "必填参数": chosen["必填参数"],
                    "可变参数": chosen["可变参数"],
                    "是否返回": chosen["是否返回"],
                    "来源": chosen["来源"],
                }
                # 两个来源都给出了非空参数个数、且对不上时，把观测全部摊开，
                # 暴露「双轨签名」而不是替它选一个。只有一个来源有数时不摊开，
                # 避免把「另一个来源没这个字段」误读成冲突。
                arities = [(o[1]["参数个数"], o[1]["必填参数"]) for o in obs
                           if o[1]["参数个数"] is not None]
                if len(obs) > 1 and len(set(arities)) > 1:
                    entry["观测"] = [
                        {
                            "种类": kind,
                            "参数个数": info["参数个数"],
                            "必填参数": info["必填参数"],
                            "可变参数": info["可变参数"],
                            "是否返回": info["是否返回"],
                            "来源": info["来源"],
                        }
                        for kind, info in obs
                    ]
            entries.append(entry)

        modules.append({"模块": module, "导出": entries})

    total_exports = sum(len(m["导出"]) for m in modules)
    with_arity = sum(1 for m in modules for e in m["导出"] if e["参数个数"] is not None)
    with_return = sum(1 for m in modules for e in m["导出"] if e["是否返回"] is not None)
    return {
        "模块数": len(modules),
        "导出条目数": total_exports,
        "有参数个数": with_arity,
        "有返回信息": with_return,
        "模块": modules,
    }


# =============================================================================
# 等价写法族（8 类）
# =============================================================================

def build_syntax_forms() -> list[dict]:
    """8 类等价写法族：canonical 形态 + 已实测接受的变体。

    每一条的「已实测」都对应 tests/test_spec_lockstep.py 里一次真实的
    词法/编译对比，而不是照抄设计文档。
    """
    return [
        {
            "id": "cn_en_punctuation",
            "名称": "中英文标点",
            "canonical": "。",
            "accepted": ["，", "：", "（", "）", "【", "】", "｛", "｝", "「", "」", "『", "』", "、", "；"],
            "canonical_example": "设 甲 为 1。",
            "accepted_examples": ["设 甲 为 1；印(甲)", "设 甲 为【1,2】。", "设 甲 为 ｛1:2｝。"],
            "已实测": True,
            "反例": {
                "写法": "设 甲 为 1.",
                "原因": "半角 . 会被读成小数点，`1.` 变成浮点 1.0；句号必须用「。」",
            },
            "来源": "docs/分层语法设计_v4.0.md §1.2 第 1 类；lexer SYMBOL_MAP + T-0377 实测",
            "说明": "除句号外，中文标点与对应半角标点在词法层归一到同一记号。",
        },
        {
            "id": "space_optional",
            "名称": "有空格/无空格",
            "canonical": "设 甲 为 10。",
            "accepted": ["设甲为10。"],
            "canonical_example": "设 甲 为 10。\n印(甲)",
            "accepted_examples": ["设甲为10。\n印(甲)"],
            "已实测": True,
            "来源": "docs/分层语法设计_v4.0.md §1.2 第 2 类；T-0377 实测生成代码逐字相同",
        },
        {
            "id": "explicit_end",
            "名称": "显式结束/缩进",
            "canonical": "设 甲 为 1。",
            "accepted": ["设 甲 为 1 结束。"],
            "canonical_example": "设 甲 为 1。\n印(甲)",
            "accepted_examples": ["设 甲 为 1 结束。\n印(甲)"],
            "已实测": True,
            "来源": "docs/分层语法设计_v4.0.md §1.2 第 3 类；T-0377 实测生成代码逐字相同",
            "说明": "「结束。」是可选冗余标记，块边界仍由缩进决定。",
        },
        {
            "id": "book_brackets",
            "名称": "有括号/无括号",
            "canonical": "排序(列表)",
            "accepted": ["《排序》(列表)", "排序 列表"],
            "canonical_example": "设 列表 为 [3,1,2]。\n排序(列表)",
            "accepted_examples": ["设 列表 为 [3,1,2]。\n《排序》(列表)", "设 列表 为 [3,1,2]。\n排序 列表"],
            "已实测": True,
            "反例": {
                "写法": "《排序》列表",
                "原因": "书名号形式必须带圆括号；不带括号会生成字符串 \"排序\" 与 列表() 两个表达式",
            },
            "来源": "docs/分层语法设计_v4.0.md §1.2 第 4 类；T-0377 实测",
        },
        {
            "id": "function_keyword",
            "名称": "段落/函数/段",
            "canonical": "段 加法(甲,乙):",
            "accepted": ["段落 加法(甲,乙):", "函数 加法(甲,乙):", "段落 加法 接收 甲, 乙："],
            "canonical_example": "段 加法(甲,乙):\n  返 甲 加 乙。\n印(加法(1,2))",
            "accepted_examples": ["段落 加法 接收 甲, 乙：\n  返回 甲 + 乙\n打印(加法(1,2))"],
            "已实测": True,
            "来源": "docs/分层语法设计_v4.0.md §1.2 第 5 类；src/keywords.py:KEYWORDS_FUNCTION；T-0377 实测生成代码逐字相同",
            "说明": "段（L0 主形式）/段落/函数三者等价；「接收」是参数表连接词，"
                    "但 parser 已对该写法发 DeprecationWarning，规范写法用括号参数表。",
        },
        {
            "id": "cn_operator",
            "名称": "中文运算符/符号",
            "canonical": "+",
            "accepted": ["加", "且", "或", "非", "大于", "小于", "等于", "不等于", "大于等于", "小于等于", "不小于", "不大于", "整除", "模", "幂", "位与", "位或", "位异或", "左移", "右移", "位非"],
            "canonical_example": "设 甲 为 1 + 2。",
            "accepted_examples": ["设 甲 为 1 加 2。", "若 甲 等于 1 则 印(1)。", "设 甲 为 8 整除 3。"],
            "已实测": True,
            "来源": "docs/分层语法设计_v4.0.md §1.2 第 6 类；src/code_generator.py:operator_map；T-0377 实测",
            "说明": "复合赋值是另一族：`甲 加上 1。`≡`甲 += 1`，符号 `+=` 不作源码写法。",
        },
        {
            "id": "subject_object",
            "名称": "主谓/谓宾",
            "canonical": None,
            "accepted": [],
            "canonical_example": None,
            "accepted_examples": [],
            "已实测": False,
            "来源": "docs/分层语法设计_v4.0.md §1.2 第 7 类",
            "说明": "未实现：`列表排序(甲)` 与 `排序列表(甲)` 被词法层当两个不同标识符，"
                    "生成 _light_builtin.列表排序 / _light_builtin.排序列表，不存在语法层归一。"
                    "表里不登记任何 accepted，避免把不存在的写法写成合法。",
        },
        {
            "id": "arity_calls",
            "名称": "显式模式/简洁模式（元数驱动双调用）",
            "canonical": "打印(甲)",
            "accepted": ["打印 甲"],
            "canonical_example": "设 甲 为 1。\n打印(甲)",
            "accepted_examples": ["设 甲 为 1。\n打印 甲"],
            "已实测": True,
            "来源": "docs/分层语法设计_v4.0.md §1.2 第 8 类；src/keywords.py:VERB_ARITY；T-0377 实测生成代码逐字相同",
            "说明": "只有登记在 VERB_ARITY / STDLIB_VERB_ARITY 的动词才允许省略括号。",
        },
    ]


# =============================================================================
# 诊断码
# =============================================================================

def build_diagnostics() -> list[dict]:
    """registry.py 存在就抽真实码表，不存在就空数组（不造码）。"""
    registry_path = SRC / "diagnostics" / "registry.py"
    if not registry_path.is_file():
        return []
    _ensure_src_on_path()
    from diagnostics import registry

    out = []
    for rule in registry.RULES:
        out.append({
            "code": rule.code,
            "title": rule.title,
            "stage": rule.stage,
            "severity": rule.severity,
            "provisional": rule.provisional,
            "source": rule.source,
        })
    return out


# =============================================================================
# 汇总
# =============================================================================

def _stdlib_digest() -> str:
    h = hashlib.sha256()
    for p in sorted(list((ROOT / "stdlib").glob("*.light")) + list((ROOT / "stdlib").glob("*.py"))):
        h.update(_rel(p).encode("utf-8"))
        h.update(b"\0")
        h.update(_sha256_normalized(p).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def build() -> dict:
    _ensure_src_on_path()
    version_src = _read(SRC / "version.py")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', version_src, re.MULTILINE)
    version = m.group(1) if m else None

    l0 = parse_l0_core()
    diagnostics = build_diagnostics()

    data = {
        "spec": "light.spec.json",
        "schema_version": SPEC_VERSION,
        "version": version,
        "generated_by": "spec/build_spec.py",
        "generated_from": {
            "说明": "按文件内容取 sha256[:16]；不存 commit，合并后内容不变则 --check 仍绿",
            "文件": {rel: _sha256_normalized(ROOT / rel)[:16] for rel in FINGERPRINT_FILES},
            "stdlib_汇总": _stdlib_digest()[:16],
        },
        "l0_core": {
            "声明总数": l0["声明总数"],
            "实际字数": len(l0["字"]),
            "章节": [],
        },
        "keywords": build_keywords(),
        "operators": build_operators(),
        "stdlib": build_stdlib(),
        "syntax_forms": build_syntax_forms(),
        "diagnostics": diagnostics,
    }

    # 章节统计（来自文档，不改写文档）
    text = _read(ROOT / "docs/language/l0-core.md")
    section = None
    counts: dict[str, int] = {}
    for line in text.splitlines():
        hm = _L0_SECTION_RE.match(line)
        if hm:
            section = hm.group(1)
            counts[section] = 0
            continue
        if section and _L0_ROW_RE.match(line):
            counts[section] += 1
    data["l0_core"]["章节"] = [{"章节": k, "字数": v} for k, v in counts.items()]
    return data


def render(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成/校验 spec/light.spec.json")
    ap.add_argument("--check", action="store_true", help="只比对，不写文件；不一致 rc=1")
    args = ap.parse_args(argv)

    text = render(build())
    if args.check:
        if not SPEC_PATH.is_file():
            print(f"缺少 {_rel(SPEC_PATH)}；先跑 python -m spec.build_spec", file=sys.stderr)
            return 1
        # 行尾按 LF 归一：仓库 core.autocrlf=true 时，checkout 会把这个 JSON
        # 落成 CRLF；若不归一，任何 Windows 检出都会假报陈旧（内容其实没变）。
        current = _read(SPEC_PATH).replace("\r\n", "\n")
        if current == text:
            print(f"OK: {_rel(SPEC_PATH)} 与仓内现状一致")
            return 0
        cur_lines = current.splitlines()
        new_lines = text.splitlines()
        for i, (a, b) in enumerate(zip(cur_lines, new_lines), 1):
            if a != b:
                # a = 仓内文件现状，b = 本次重建结果；文案别写反，否则排查时会
                # 把「文件里的旧值」当成「重建出来的新值」（T-0383 踩过一次）。
                print(f"不一致：第 {i} 行\n  文件: {a[:160]}\n  重建: {b[:160]}",
                      file=sys.stderr)
                break
        else:
            print(f"不一致：行数 {len(cur_lines)} → {len(new_lines)}", file=sys.stderr)
        print(f"请重新生成：PYTHONPATH=src python3 -m spec.build_spec", file=sys.stderr)
        return 1

    SPEC_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"写入 {_rel(SPEC_PATH)}（{len(text)} 字符）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
