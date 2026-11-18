# -*- coding: utf-8 -*-
"""spec/light.spec.json 与仓内真实来源的 lockstep 门禁。

这张表的价值全在「每一行都能回溯」。所以本文件不做文案检查，只做三类硬断言：

1. **可重建**：内存重算一遍必须与仓内 JSON 逐字节相同（等价于
   ``python -m spec.build_spec --check``）。
2. **stdlib 锁步**：每个条目都必须出现在它所属的 ``stdlib/<模块>.light``
   导出清单里；非空 ``参数个数`` 必须能在它标注的来源行/函数上数出来。
3. **关键字/运算符锁步**：关键字集合等于 lexer 真正会发 KEYWORD 的集合，
   ``是否可作标识符`` 由词法实测决定；运算符 canonical 唯一，别名必须可词法化。

第 4 类是等价写法的**编译实测**：canonical 与 accepted 必须生成同一段代码。
注意：这不是「文档抄写」测试——``docs/分层语法设计_v4.0.md`` 里 8 类等价写法
有两类（中英标点全等价、主谓/谓宾）已被实测证伪，表里按实测登记，不按文档。
"""
import ast
import json
import os
import re
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "src"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from spec import build_spec  # noqa: E402
from lexer import Lexer  # noqa: E402
from tokens import TokenType  # noqa: E402
from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402
import keywords as kw  # noqa: E402

_SPEC_PATH = os.path.join(_ROOT, "spec", "light.spec.json")
_SKIP_TYPES = {TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT, TokenType.EOF}


def _load():
    with open(_SPEC_PATH, encoding="utf-8") as f:
        return json.load(f)


def _token_types(source):
    lexer = Lexer(source)
    return [t.type.name for t in lexer.tokenize() if t.type not in _SKIP_TYPES]


def _first_token(word):
    # 单字符书名号/引号不构成完整记号，词法器会报「未闭合」；
    # 它们的 TokenType 由 lexer 的符号映射确定。
    override = {'"': "STRING", "'": "STRING", "《": "LBOOK", "》": "RBOOK", "\\": "COMMA"}
    if word in override:
        return override[word], word
    try:
        for t in Lexer(word).tokenize():
            if t.type not in _SKIP_TYPES:
                return t.type.name, t.value
    except Exception:
        return "ERROR", None
    return "EOF", None


def _gen(source):
    tree = LightParser().parse(source)
    return PythonCodeGenerator().generate(tree)


def _body_only(code):
    idx = code.find("# LIGHT_SRC:1")
    return code[idx:] if idx >= 0 else code


# =============================================================================
# 1. 可重建
# =============================================================================

def test_spec_file_exists_and_is_valid_json():
    assert os.path.isfile(_SPEC_PATH), "spec/light.spec.json 不存在"
    data = _load()
    assert isinstance(data, dict)


def test_spec_is_rebuildable_byte_for_byte():
    """等价于 `python -m spec.build_spec --check`：源不变则表必须逐字节一致。

    行尾先归一为 LF：仓库 core.autocrlf=true，Windows 检出会把该 JSON 落成
    CRLF，不归一会让每条 Windows 上的 lockstep 都假红（内容其实没变）。
    """
    rebuilt = build_spec.render(build_spec.build())
    with open(_SPEC_PATH, encoding="utf-8") as f:
        current = f.read().replace("\r\n", "\n")
    assert current == rebuilt, (
        "spec/light.spec.json 与仓内现状不一致；"
        "请跑 PYTHONPATH=src python3 -m spec.build_spec 重新生成"
    )


def test_stdlib_digest_ignores_line_endings(tmp_path, monkeypatch):
    """反证（T-0388）：stdlib 指纹不许随检出形态（CRLF/LF）变化。

    同一份提交在 Windows（``core.autocrlf=true`` → CRLF 检出）与 0.88（LF 检出）
    必须算出同一个 ``stdlib_汇总``。做法是把仓内 stdlib 原样拷进临时树，算出
    指纹后把每个文件整体翻成另一种行尾形态，再算一次——两次必须逐字相同。
    """
    src_dir = os.path.join(_ROOT, "stdlib")
    dst_dir = tmp_path / "stdlib"
    dst_dir.mkdir()
    for name in sorted(os.listdir(src_dir)):
        if not name.endswith((".light", ".py")):
            continue
        (dst_dir / name).write_bytes(open(os.path.join(src_dir, name), "rb").read())

    monkeypatch.setattr(build_spec, "ROOT", tmp_path)
    digest_before = build_spec._stdlib_digest()

    for p in dst_dir.iterdir():
        data = p.read_bytes()
        # LF → CRLF（若原本已是 CRLF，先归一再加回，结果等价于「另一种形态」）
        data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        p.write_bytes(data)
    assert build_spec._stdlib_digest() == digest_before, (
        "stdlib 指纹随行尾形态变化；非 Windows 检出会与 Windows 算出不同值"
    )


def test_required_sections_present():
    data = _load()
    for key in ("version", "generated_from", "keywords", "operators",
                "stdlib", "syntax_forms", "diagnostics"):
        assert key in data, f"缺少顶层字段 {key}"


# =============================================================================
# 2. L0 与关键字锁步
# =============================================================================

def _parse_l0_doc():
    path = os.path.join(_ROOT, "docs", "language", "l0-core.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    chars, section = set(), None
    for line in text.splitlines():
        hm = re.match(r"^## (.+)（(\d+)字）\s*$", line)
        if hm:
            section = hm.group(1)
            continue
        rm = re.match(r"^\| `(.)` \| (.+?) \|\s*$", line)
        if rm and section:
            chars.add(rm.group(1))
    return chars


def test_l0_core_is_44_and_matches_doc():
    data = _load()
    doc_chars = _parse_l0_doc()
    spec_chars = {item["字"] for item in data["keywords"] if item.get("层级") == "L0"}
    assert len(doc_chars) == 44, f"l0-core.md 实际 {len(doc_chars)} 字"
    assert spec_chars == doc_chars, (
        f"只在表里: {''.join(sorted(spec_chars - doc_chars))}；"
        f"只在文档: {''.join(sorted(doc_chars - spec_chars))}"
    )
    assert data["l0_core"]["声明总数"] == 44
    assert data["l0_core"]["实际字数"] == 44
    assert sum(s["字数"] for s in data["l0_core"]["章节"]) == 44


def test_keywords_equal_lexer_keyword_surface():
    """keywords 段必须正好覆盖 lexer 会发 KEYWORD 的名字 ∪ L0 文档承诺字。

    lexer 的关键字面是 ``ALL_KEYWORDS | VERB_ARITY``（见 lexer.py 的
    ``_ALL_KEYWORDS_WITH_VERBS``）；L0 里范式 A/C 的字不在这个面里，但也是
    语言承诺的规范条目，必须留在表里。
    """
    data = _load()
    expected = set(kw.ALL_KEYWORDS) | set(kw.VERB_ARITY) | _parse_l0_doc()
    # 文档登记、但已降级为上下文关键字的别名（当前只有 `属性`）也必须在表里
    expected |= {a for als in build_spec.parse_keyword_aliases().values() for a in als
                 if _first_token(a)[0] != "ERROR"}
    actual = {item["字"] for item in data["keywords"]}
    assert actual == expected, (
        f"表里多: {''.join(sorted(actual - expected))}；"
        f"表里少: {''.join(sorted(expected - actual))}"
    )


def test_keyword_identifier_flag_matches_lexer():
    """`是否可作标识符` 不许手写：逐个用词法器实测。

    真关键字（lexer 发 KEYWORD）不可作标识符；范式 A/C 的字在词法层是
    IDENTIFIER，可作标识符（A 只在特定语法位置才当关键字）。
    """
    data = _load()
    bad = []
    for item in data["keywords"]:
        kind, _value = _first_token(item["字"])
        lexer_says_keyword = kind == "KEYWORD"
        if item["是否可作标识符"] == lexer_says_keyword:
            bad.append(f"{item['字']}(表={item['是否可作标识符']}, 词法KEYWORD={lexer_says_keyword})")
    assert not bad, "标识符标志与词法实测不符：" + "、".join(bad)


def test_landing_paradigm_consistent_with_keywords():
    """L0 的范式 B 必须在 ALL_KEYWORDS，范式 A 必须不在（口径 16 的反向守卫）。"""
    data = _load()
    problems = []
    for item in data["keywords"]:
        if item.get("层级") != "L0":
            continue
        word, paradigm = item["字"], item.get("范式")
        if paradigm == "B" and word not in kw.ALL_KEYWORDS:
            problems.append(f"{word} 登记 B 但不在 ALL_KEYWORDS")
        if paradigm == "A" and word in kw.ALL_KEYWORDS:
            problems.append(f"{word} 登记 A 却漏进了 ALL_KEYWORDS")
        if paradigm not in ("A", "B", "C"):
            problems.append(f"{word} 范式非法: {paradigm}")
    assert not problems, "；".join(problems)


# =============================================================================
# 3. 运算符
# =============================================================================

def test_operator_canonical_is_unique():
    data = _load()
    canonicals = [op["canonical"] for op in data["operators"]]
    dup = sorted({c for c in canonicals if canonicals.count(c) > 1})
    assert not dup, "同一语义出现多个 canonical：" + "、".join(dup)


def test_operator_forms_are_lexable():
    """canonical 与别名都必须是词法层真能切出来的形态，不许登记不存在的写法。"""
    data = _load()
    bad = []
    for op in data["operators"]:
        if op["状态"] == "不可用":
            continue  # 表里明确登记为不可用的形态（^ / | / -> / :=）不要求可词法化
        forms = [op["canonical"]] + list(op.get("别名", []))
        for form in forms:
            kind, _value = _first_token(form)
            if kind == "ERROR":
                bad.append(f"{op['canonical']} 的形态 {form!r} 词法拒绝")
    assert not bad, "；".join(bad)


def test_operator_symbol_token_names_match_lexer():
    """登记为符号（记号不是 KEYWORD）的 canonical，词法记号必须对得上。"""
    data = _load()
    bad = []
    for op in data["operators"]:
        token = op["记号"]
        canonical = op["canonical"]
        if token in ("KEYWORD", "语句级（不是表达式运算符）", "STRING"):
            continue
        if token == "ERROR":
            kind, _ = _first_token(canonical)
            if kind != "ERROR":
                bad.append(f"{canonical} 登记为 ERROR，实际词法为 {kind}")
            continue
        kind, _ = _first_token(canonical)
        if kind != token:
            bad.append(f"{canonical} 登记 {token}，实际词法 {kind}")
    assert not bad, "；".join(bad)


def test_compound_assignment_is_not_symbol_form():
    """`+=` 之类符号作源码写法时必须报错——表里不能把它们写成可用。"""
    from light_parser_v3 import LightParser  # noqa: F401  （保持导入路径单一）
    with pytest.raises(Exception):
        LightParser().parse("设 甲 为 1。\n甲 += 2。")
    # 对应的中文形态必须能编
    assert "甲 += 2" in _body_only(_gen("设 甲 为 1。\n甲 加上 2。"))


# =============================================================================
# 4. stdlib 锁步
# =============================================================================

def _stdlib_exports(module):
    path = os.path.join(_ROOT, "stdlib", module + ".light")
    names = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("导出"):
                continue
            m = re.match(r"^导出\s+(.+?)[。；]?\s*$", line)
            if not m:
                continue
            for n in m.group(1).split():
                n = n.strip().rstrip("。；，,")
                if n and n not in names:
                    names.append(n)
    return names


def test_stdlib_entries_all_exist_in_stdlib_dir():
    data = _load()
    bad = []
    for mod in data["stdlib"]["模块"]:
        module = mod["模块"]
        path = os.path.join(_ROOT, "stdlib", module + ".light")
        if not os.path.isfile(path):
            bad.append(f"模块 {module} 没有 .light 文件")
            continue
        exports = set(_stdlib_exports(module))
        for entry in mod["导出"]:
            if entry["名字"] not in exports:
                bad.append(f"{module}.{entry['名字']} 不在导出清单")
        if len(mod["导出"]) != len(exports):
            bad.append(f"{module} 条目数 {len(mod['导出'])} ≠ 导出清单 {len(exports)}")
    assert not bad, "stdlib 锁步失败：\n" + "\n".join(bad)


_LINE_CACHE = {}
_AST_CACHE = {}


def _file_lines(rel):
    if rel not in _LINE_CACHE:
        with open(os.path.join(_ROOT, rel), encoding="utf-8") as f:
            _LINE_CACHE[rel] = f.read().splitlines()
    return _LINE_CACHE[rel]


def _file_ast(rel):
    if rel not in _AST_CACHE:
        with open(os.path.join(_ROOT, rel), encoding="utf-8") as f:
            _AST_CACHE[rel] = ast.parse(f.read())
    return _AST_CACHE[rel]


def test_stdlib_arity_is_backed_by_source():
    """非空 `参数个数` 必须在来源处数得出来——不许用默认值凑。"""
    from keywords import STDLIB_VERB_ARITY

    data = _load()
    bad = []
    for mod in data["stdlib"]["模块"]:
        for entry in mod["导出"]:
            n = entry["参数个数"]
            src = entry["来源"]
            if n is None:
                continue
            if src is None:
                bad.append(f"{mod['模块']}.{entry['名字']} 有参数个数却没有来源")
                continue
            if src.startswith("src/keywords.py:STDLIB_VERB_ARITY"):
                v = STDLIB_VERB_ARITY.get(entry["名字"])
                if v is None or (v >= 0 and v != n):
                    bad.append(f"{mod['模块']}.{entry['名字']} 的 verb-arity={v} 与表 {n} 不符")
                continue

            rel, _, lineno = src.rpartition(":")
            if not rel.endswith((".light", ".py")):
                bad.append(f"{mod['模块']}.{entry['名字']} 来源无法识别: {src}")
                continue
            lineno = int(lineno)
            if rel.endswith(".light"):
                line = _file_lines(rel)[lineno - 1]
                m = re.match(r"^(?:段落|函数|段)\s+[^\s(（]+\s*(?:[（(](.*?)[）)]|接收\s+(.*?))?\s*[:：]?\s*$",
                             line.strip())
                if not m:
                    bad.append(f"{src} 不是函数定义行: {line.strip()}")
                    continue
                params = [p for p in re.split(r"[,，、]", (m.group(1) or m.group(2) or "").strip()) if p.strip()]
                if len(params) != n:
                    bad.append(f"{src} 数出 {len(params)} 个参数，表里是 {n}")
            else:
                tree = _file_ast(rel)
                fn = None
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno == lineno:
                        fn = node
                        break
                if fn is None:
                    bad.append(f"{src} 找不到对应的顶层函数")
                    continue
                total = len(fn.args.posonlyargs) + len(fn.args.args)
                if total != n:
                    bad.append(f"{src} 数出 {total} 个参数，表里是 {n}")
    assert not bad, "参数个数无来源：\n" + "\n".join(bad[:20])


def test_stdlib_return_flag_is_boolean_or_null():
    data = _load()
    for mod in data["stdlib"]["模块"]:
        for entry in mod["导出"]:
            assert entry["是否返回"] in (True, False, None), entry


# =============================================================================
# 5. 等价写法族（编译实测）
# =============================================================================

def test_syntax_forms_are_eight_classes():
    data = _load()
    assert len(data["syntax_forms"]) == 8
    assert len({f["id"] for f in data["syntax_forms"]}) == 8
    for f in data["syntax_forms"]:
        assert isinstance(f["已实测"], bool)
        if f["已实测"]:
            assert f["canonical"] and f["canonical_example"]
            assert f["accepted"] and f["accepted_examples"]
        else:
            # 未实现的写法族不许登记 accepted——否则等于教 Agent 写错
            assert f["accepted"] == []
            assert "未实现" in f["说明"]


@pytest.mark.parametrize("canonical,variant", [
    ("设 甲 为 10。\n印(甲)", "设甲为10。\n印(甲)"),
    ("设 甲 为 1。\n印(甲)", "设 甲 为 1 结束。\n印(甲)"),
    ("设 列表 为 [3,1,2]。\n排序(列表)", "设 列表 为 [3,1,2]。\n排序 列表"),
    ("设 列表 为 [3,1,2]。\n排序(列表)", "设 列表 为 [3,1,2]。\n《排序》(列表)"),
    ("设 甲 为 1。\n打印(甲)", "设 甲 为 1。\n打印 甲"),
    ("段 加法(甲,乙):\n  返 甲 加 乙。\n印(加法(1,2))",
     "段落 加法 接收 甲, 乙：\n  返回 甲 + 乙\n打印(加法(1,2))"),
    ("设 甲 为 1 + 2。", "设 甲 为 1 加 2。"),
    ("设 甲 为 8 模 3。", "设 甲 为 8 % 3。"),
])
def test_accepted_variant_compiles_to_same_code(canonical, variant):
    a = _body_only(_gen(canonical))
    b = _body_only(_gen(variant))
    assert a == b, f"等价写法生成代码不同：\ncanonical:\n{a}\nvariant:\n{b}"


def test_sentence_period_is_not_dot():
    """半角 . 不是语句结束符：`1.` 会被读成浮点 1.0，必须能被这条门禁抓住。"""
    assert _token_types("设 甲 为 1。") == ["KEYWORD", "IDENTIFIER", "KEYWORD", "NUMBER", "PERIOD"]
    dot = _token_types("设 甲 为 1.")
    assert "PERIOD" not in dot
    assert dot[-1] == "NUMBER"


def test_cn_punctuation_token_types_match_ascii():
    pairs = [
        ("设 甲 为 1，2。", "设 甲 为 1, 2。"),
        ("设 甲 为 1；印(甲)", "设 甲 为 1;印(甲)"),
        ("设 甲 为【1,2】。", "设 甲 为 [1,2]。"),
        ("设 甲 为 ｛1:2｝。", "设 甲 为 {1:2}。"),
        ("设 甲 为 『abc』。", "设 甲 为 'abc'。"),
        ("设 甲 为 「abc」。", '设 甲 为 "abc"。'),
        ("印(1、2)", "印(1\\2)"),
        ("设 甲 为 1。\n印（甲）", "设 甲 为 1。\n印(甲)"),
        ("若 甲 > 0 ： 印(甲)。", "若 甲 > 0 : 印(甲)。"),
    ]
    for cn, en in pairs:
        assert _token_types(cn) == _token_types(en), f"{cn!r} 与 {en!r} 记号序列不同"


# =============================================================================
# 6. 诊断码 / 版本
# =============================================================================

def test_diagnostics_match_registry():
    data = _load()
    codes = [d["code"] for d in data["diagnostics"]]
    registry_path = os.path.join(_ROOT, "src", "diagnostics", "registry.py")
    if not os.path.isfile(registry_path):
        assert codes == []
        return
    from diagnostics import registry
    assert set(codes) == set(registry.all_codes())
    assert len(codes) == len(set(codes)), "诊断码重复"


def test_version_matches_source():
    data = _load()
    with open(os.path.join(_ROOT, "src", "version.py"), encoding="utf-8") as f:
        text = f.read()
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m and data["version"] == m.group(1)


def test_generated_from_covers_all_declared_sources():
    data = _load()
    files = data["generated_from"]["文件"]
    for rel in files:
        assert os.path.isfile(os.path.join(_ROOT, rel)), f"指纹来源 {rel} 不存在"
    assert "stdlib_汇总" in data["generated_from"]
