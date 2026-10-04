# -*- coding: utf-8 -*-
"""
R114 S1 · stdlib/builtins.py 三副本 drift 门禁。

与 scripts/sync_builtins.py 共用同一份豁免常量（BOOT_JSON_EXEMPT / LH_ONLY /
BOOT_PORTED / BOOT_KEEP_HEADER）——单一权威，防两处漂移。

断言分级：
1. boot 副本（bootstrap/release/stdlib/builtins.py，自举打包用）：
   - 函数名集合 == 真源（R114 前缺 49 个：判型族/文件族/二进制族/系统原语）；
   - BOOT_KEEP_HEADER（import json as _duan_json_module）必须保留；
   - BOOT_JSON_EXEMPT 三函数取 boot 直用 json 版（不得误入真源的惰性 import JSON 版）；
   - 全文件不得出现可执行的光转发式 import（boot 发布环境实测无光导入钩子、
     内置核心*.light 全部缺失，任何 `import 内置核心*`/`import JSON` 都会运行期炸）；
   - BOOT_PORTED 移植体函数必须存在；
   - boot 运行冒烟兜底（importlib 实调判型族/JSON/container_get）。
2. LH 副本（lightharness/stdlib/builtins.py）：
   - 函数名集合 diff == LH_ONLY（== {整数}）；
   - 公共函数体规范化哈希与真源一致（防 LP-D-019② 那种函数体级语义分叉）。

说明（计划砍线条款落地）：boot 现有 109 个自包含公共函数体为发布期保留体——
真源对应函数是"地板转发"（惰性 import 内置核心*），boot 环境无法托管，故不参与
哈希比对；参与哈希比对的 LH 公共函数体与逐字补齐的 boot 函数已在 sync 自检中覆盖。
"""

import os
import re
import sys
import importlib.util

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scripts.sync_builtins import (  # noqa: E402
    BOOT_JSON_EXEMPT,
    LH_ONLY,
    BOOT_PORTED,
    BOOT_KEEP_HEADER,
    MAIN_PATH,
    BOOT_PATH,
    LH_PATH,
    parse_functions,
    block_hash,
)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def copies():
    main_f, _ = parse_functions(_read(MAIN_PATH))
    boot_f, _ = parse_functions(_read(BOOT_PATH))
    lh_f, _ = parse_functions(_read(LH_PATH))
    return main_f, boot_f, lh_f


# ---------------------------------------------------------------------------
# boot 副本
# ---------------------------------------------------------------------------
def test_boot_name_set_equals_main(copies):
    main_f, boot_f, _ = copies
    assert set(boot_f) == set(main_f), (
        f"boot 缺: {sorted(set(main_f) - set(boot_f))};"
        f"boot 多出: {sorted(set(boot_f) - set(main_f))}"
    )


def test_boot_keep_header_present(copies):
    text = _read(BOOT_PATH)
    exec_lines = [
        l.strip() for l in text.split("\n")
        if l.strip() and not l.strip().startswith("#")
    ]
    assert BOOT_KEEP_HEADER in exec_lines, "boot 顶层保留行丢失"


def test_boot_json_exempt_pinned(copies):
    _, boot_f, _ = copies
    for n in sorted(BOOT_JSON_EXEMPT):
        assert n in boot_f
        block = boot_f[n]
        assert not re.search(r"^\s*import\s+JSON\s*$", block, re.M), (
            f"boot 豁免函数 {n} 误入了真源的惰性 import JSON 版"
        )
    assert "_duan_json_module" in boot_f["解析JSON"]
    assert "_duan_json_module" in boot_f["序列化JSON"]
    assert "序列化JSON" in boot_f["美化JSON"]


def test_boot_no_light_forward_leak(copies):
    text = _read(BOOT_PATH)
    exec_lines = [
        l.strip() for l in text.split("\n")
        if l.strip() and not l.strip().startswith("#")
    ]
    bad = [
        l for l in exec_lines
        if re.match(r"^\s*import\s+(内置核心\w*|字符串工具轻量|JSON|JSON核心)\s*$", l)
        or re.match(r"^\s*from\s+(内置核心\w*|字符串工具轻量|JSON)\b", l)
    ]
    assert bad == [], f"boot 出现光转发式 import（运行期必炸）: {bad}"


def test_boot_ported_present(copies):
    _, boot_f, _ = copies
    missing = [n for n in BOOT_PORTED if n not in boot_f]
    assert missing == [], f"boot 缺少自包含移植体: {missing}"


# ---------------------------------------------------------------------------
# LH 副本
# ---------------------------------------------------------------------------
def test_lh_name_diff_only_lh_only(copies):
    main_f, _, lh_f = copies
    assert set(lh_f) - set(main_f) == LH_ONLY
    assert set(main_f) - set(lh_f) == set()


def test_lh_public_body_hash_equals_main(copies):
    main_f, _, lh_f = copies
    drifted = [
        n for n in main_f
        if n not in LH_ONLY and block_hash(lh_f[n]) != block_hash(main_f[n])
    ]
    assert drifted == [], f"LH 公共函数体与真源漂移: {drifted}"


# ---------------------------------------------------------------------------
# boot 运行冒烟兜底
# ---------------------------------------------------------------------------
def test_boot_runtime_smoke():
    stdlib_dir = os.path.dirname(BOOT_PATH)
    sys.path.insert(0, stdlib_dir)
    try:
        spec = importlib.util.spec_from_file_location(
            "drift_smoke_builtins", os.path.join(stdlib_dir, "builtins.py")
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        # 判型族（本轮新增的核心）
        assert m.是数值(3) is True
        assert m.是数值(3.5) is True
        assert m.是数值(True) is False
        assert m.是数值("7") is False
        assert m.是数字("7") is True
        assert m.是数字("12") is False          # LP-D-019② 单字符守卫
        assert m.是布尔(True) is True
        assert m.是布尔(1) is False
        assert m.字符串全数字("123") is True
        assert m.字符串全数字("") is False
        assert m.是负零(-0.0) is True
        assert m.是负零(0.0) is False

        # JSON 三豁免（boot 直用 _duan_json_module）
        assert m.解析JSON('{"a":1}') == {"a": 1}
        assert m.序列化JSON({"a": 1}) == '{"a": 1}'

        # 本轮新增公共函数代表
        assert m.container_get({"a": 1}, "a", 9) == 1
        assert m.取可选({"a": 1}, "a", 9) == 1
        assert m.排序列表([3, 1, 2]) == [1, 2, 3]
    finally:
        sys.path.remove(stdlib_dir)
