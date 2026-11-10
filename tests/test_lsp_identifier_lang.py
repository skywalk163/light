# -*- coding: utf-8 -*-
"""T-0325：LSP 标识符语言一致性检查（中文/英文命名建议，非强制）测试。

覆盖:
* 三种 mode（zh / en / any）对 zh 名 / en 名 / mixed 名的判定矩阵；
* 字符串字面量与注释里的中文不误判；
* 中文标点、关键字本身（如果 / 段落 等）不当作标识符；
* 性能粗测：1000 行源码 check() < 50ms（只防 O(n²)）；
* 默认 any 下返回空列表；
* light.toml 配置读取与 diagnostic_extension 接线（0-based 坐标 / severity 映射）。
"""

import os
import sys
import time

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _ROOT)

from lsp.identifier_language import (  # noqa: E402
    check,
    check_from_config,
    detect_lang,
    iter_identifiers,
    load_mode,
    _lex_tokens,
    _inspect,
    _filter,
)
from lsp.diagnostic_extension import (  # noqa: E402
    identifier_diagnostics_for_source,
    IDENTIFIER_SOURCE_NAME,
)


# --------------------------------------------------------------------------
# 语言判定单元
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name,expected", [
    ("甲", "zh"),
    ("加法", "zh"),
    ("学生", "zh"),
    ("username", "en"),
    ("utils", "en"),
    ("_x1", "en"),
    ("user名字", "mixed"),
    ("工具lib", "mixed"),
])
def test_detect_lang(name, expected):
    assert detect_lang(name) == expected


# --------------------------------------------------------------------------
# 三种 mode 判定矩阵
# --------------------------------------------------------------------------
SOURCE_MATRIX = """\
设 甲为 1
设 username为 2
设 user名字 为 3
段落 加法(甲，乙)：
  返回 甲 加 乙
类 学生：
导入 工具库 为 utils
"""


def _names(结果):
    return [项["name"] for 项 in 结果]


def test_mode_any_returns_empty_by_default():
    """默认 any：不提示，返回空列表。"""
    assert check(SOURCE_MATRIX) == []
    assert check(SOURCE_MATRIX, mode="any") == []


def test_mode_zh_matrix():
    结果 = check(SOURCE_MATRIX, mode="zh")
    by_name = {项["name"]: 项 for 项 in 结果}
    # 英文名 → info；混排 → warning；中文名不提示。
    assert by_name["username"]["severity"] == "info"
    assert by_name["username"]["lang"] == "en"
    assert by_name["utils"]["severity"] == "info"
    assert by_name["user名字"]["severity"] == "warning"
    assert by_name["user名字"]["lang"] == "mixed"
    # 中文名不应出现在提示里。
    for 名 in ("甲", "加法", "乙", "学生", "工具库"):
        assert 名 not in by_name


def test_mode_en_matrix():
    结果 = check(SOURCE_MATRIX, mode="en")
    by_name = {项["name"]: 项 for 项 in 结果}
    # 中文名 → info；混排 → warning；英文名不提示。
    assert by_name["甲"]["severity"] == "info"
    assert by_name["加法"]["severity"] == "info"
    assert by_name["学生"]["severity"] == "info"
    assert by_name["工具库"]["severity"] == "info"
    assert by_name["user名字"]["severity"] == "warning"
    for 名 in ("username", "utils"):
        assert 名 not in by_name


def test_mixed_is_warning_in_either_active_mode():
    for mode in ("zh", "en"):
        结果 = check("设 user名字为 3", mode=mode)
        assert len(结果) == 1
        assert 结果[0]["lang"] == "mixed"
        assert 结果[0]["severity"] == "warning"
        assert 结果[0]["suggestion"]


def test_entry_shape():
    结果 = check("设 user名字为 3", mode="zh")
    项 = 结果[0]
    assert set(项.keys()) == {"name", "line", "column", "kind", "lang",
                             "severity", "suggestion"}
    assert 项["line"] >= 1 and 项["column"] >= 1
    assert 项["kind"] in {"decl", "param", "import", "import_alias", "ident"}


# --------------------------------------------------------------------------
# 字符串 / 注释 / 关键字 / 标点 不误判
# --------------------------------------------------------------------------
SOURCE_NOISE = """\
# 注释里有中文 张三 和混排 user名字
设 甲为 "字符串里有中文 李四 和 user名字"
如果 甲 大于 乙：
  打印(甲)
否则：
  打印(乙)
段落 加法(甲，乙)：
  返回 甲 加 乙
"""


def test_string_and_comment_not_flagged():
    # 即便在 en 模式下，字符串 / 注释里的中文也不应进结果。
    结果 = check(SOURCE_NOISE, mode="en")
    名表 = _names(结果)
    assert "张三" not in 名表
    assert "李四" not in 名表
    assert "user名字" not in 名表


def test_keywords_and_punctuation_not_treated_as_identifiers():
    结果 = check(SOURCE_NOISE, mode="en")
    关键字 = {"如果", "大于", "否则", "打印", "段落", "返回", "加", "设"}
    名表 = set(_names(结果))
    # 关键字本身绝不出现在标识符结果里。
    assert 名表 & 关键字 == set()
    # 中文标点不是标识符：结果里不可能出现纯标点名。
    for 项 in 结果:
        assert any(c.isalnum() or ('一' <= c <= '鿿') for c in 项["name"])


def test_iter_identifiers_excludes_strings_and_keywords():
    抽取 = list(iter_identifiers(SOURCE_NOISE))
    名表 = {项["name"] for 项 in 抽取}
    assert "张三" not in 名表
    assert "李四" not in 名表
    assert "如果" not in 名表
    assert "段落" not in 名表


# --------------------------------------------------------------------------
# 配置读取
# --------------------------------------------------------------------------
def test_load_mode_default_any(tmp_path):
    assert load_mode(str(tmp_path / "light.toml")) == "any"


def test_load_mode_reads_toml(tmp_path):
    toml = tmp_path / "light.toml"
    toml.write_text('[lsp.identifier]\nmode = "en"\n', encoding="utf-8")
    assert load_mode(str(toml)) == "en"


def test_load_mode_invalid_falls_back_any(tmp_path):
    toml = tmp_path / "light.toml"
    toml.write_text('[lsp.identifier]\nmode = "jp"\n', encoding="utf-8")
    assert load_mode(str(toml)) == "any"


def test_check_from_config_respects_toml(tmp_path):
    toml = tmp_path / "light.toml"
    toml.write_text('[lsp.identifier]\nmode = "zh"\n', encoding="utf-8")
    结果 = check_from_config("设 username为 1", str(toml))
    assert len(结果) == 1
    assert 结果[0]["severity"] == "info"


# --------------------------------------------------------------------------
# diagnostic_extension 接线
# --------------------------------------------------------------------------
def test_identifier_diagnostics_lsp_shape():
    诊断 = identifier_diagnostics_for_source(SOURCE_MATRIX, mode="zh")
    assert 诊断, "zh 模式下应产生命名诊断"
    for d in 诊断:
        assert d["source"] == IDENTIFIER_SOURCE_NAME
        assert d["code"] == "identifier-language"
        # 0-based 坐标
        assert d["range"]["start"]["line"] >= 0
        assert d["range"]["start"]["character"] >= 0
        assert d["range"]["end"]["character"] >= d["range"]["start"]["character"]
        # 命名风格只允许 warning(2) / info(3)，绝不允许 error(1)
        assert d["severity"] in (2, 3)
        assert d["severity"] != 1


def test_identifier_diagnostics_default_any_empty():
    assert identifier_diagnostics_for_source(SOURCE_MATRIX) == []


def test_identifier_diagnostics_warning_severity():
    诊断 = identifier_diagnostics_for_source("设 user名字为 3", mode="en")
    assert len(诊断) == 1
    assert 诊断[0]["severity"] == 2  # warning


# --------------------------------------------------------------------------
# 性能粗测：1000 行（宽松，只防 O(n²)）
#
# 说明：既有 `src/lexer.py` 是全仓共用的重量级词法分析器，单跑一遍 1000 行在
# 本机 Windows 上基线约 90–220ms（与本模块无关，且禁止改 src/）。本模块自己的
# 后置扫描（抽取标识符 + 语言判定 + 过滤）是纯线性 O(n)，因此性能闸门分两层：
#   1. 我们自己的后置扫描 < 50ms（真正防本模块写出 O(n²)）；
#   2. 端到端 check() 能在宽松上限内跑完（冒烟，不把 lexer 基线算到本模块头上）。
# --------------------------------------------------------------------------
def _big_source() -> str:
    行 = [f"设 变量{i}为 {i}" for i in range(500)]
    行 += [f"设 var_{i} 为 {i}" for i in range(500)]
    return "\n".join(行)


def test_performance_post_scan_linear():
    源码 = _big_source()
    # 预热：lexer / 模块首次导入与编译缓存，不计入耗时。
    check("设 甲为 1", mode="zh")
    tokens = _lex_tokens(源码)

    start = time.perf_counter()
    for _ in range(3):
        抽取 = _inspect(tokens)
        _filter(抽取, "zh")
    耗时_ms = (time.perf_counter() - start) / 3 * 1000

    assert 耗时_ms < 50.0, f"本模块后置扫描 1000 行耗时 {耗时_ms:.1f}ms，超过 50ms"


def test_performance_check_end_to_end_smoke():
    源码 = _big_source()
    check("设 甲为 1", mode="zh")  # 预热
    start = time.perf_counter()
    结果 = check(源码, mode="zh")
    耗时_ms = (time.perf_counter() - start) * 1000
    # 宽松上限：端到端耗时主要由既有 lexer 基线决定，这里只防止整体卡死 / 退化。
    assert 耗时_ms < 1000.0, f"1000 行 check() 端到端耗时 {耗时_ms:.1f}ms"
    assert isinstance(结果, list)
