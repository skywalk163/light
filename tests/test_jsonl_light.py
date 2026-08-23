# -*- coding: utf-8 -*-
"""
test_jsonl_light.py —— JSONL 行流读写行为判据（C5，M13）

覆盖：
- `写JSONL文件` → `读JSONL文件` round-trip：数据逐条一致（含中文、嵌套结构）
- `逐行读JSONL`：懒惰流式，逐条返回且顺序正确
- 坏行 / 空行策略：空行跳过、坏行不丢而以「坏」标记给出，不静默丢数据
- 空文件 → 空列表

反跑改坏点贴在对应用例 docstring；临时文件前缀统一 `_taskC5_`，收尾删干净。
"""
import json
import os
import sys
import tempfile

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from JSONL import 读JSONL文件, 逐行读JSONL, 写JSONL文件


@pytest.fixture
def c5tmp():
    """收尾自动清理的 `_taskC5_` 临时目录。"""
    d = tempfile.mkdtemp(prefix="_taskC5_")
    yield d
    for name in os.listdir(d):
        try:
            os.remove(os.path.join(d, name))
        except OSError:
            pass
    os.rmdir(d)


class TestRoundTrip:
    def test_write_then_read_roundtrip(self, c5tmp):
        path = os.path.join(c5tmp, "data.jsonl")
        原数据 = [
            {"序号": 1, "标签": ["A", "B"], "说明": "中文内容"},
            {"序号": 2, "嵌套": {"键": "值"}, "通过": True},
        ]
        写JSONL文件(path, 原数据)
        读回 = 读JSONL文件(path)
        assert 读回 == 原数据, "round-trip 后数据应逐条一致（含中文、嵌套、布尔）"

    def test_utf8_chinese_survives(self, c5tmp):
        # 反跑改坏点：写入时 ensure_ascii=True → 读回仍值一致，但保证中文可直接读可另验；这里验值
        path = os.path.join(c5tmp, "cn.jsonl")
        写JSONL文件(path, [{"话": "你好，世界"}])
        assert 读JSONL文件(path)[0]["话"] == "你好，世界"


class TestStream:
    def test_逐行_reads_in_order(self, c5tmp):
        path = os.path.join(c5tmp, "s.jsonl")
        写JSONL文件(path, [{"i": 1}, {"i": 2}, {"i": 3}])
        序号们 = [r["i"] for r in 逐行读JSONL(path)]
        assert 序号们 == [1, 2, 3]

    def test_逐行_matches_bulk_read(self, c5tmp):
        path = os.path.join(c5tmp, "m.jsonl")
        写JSONL文件(path, [{"a": 1}, {"a": 2}])
        assert list(逐行读JSONL(path)) == 读JSONL文件(path)


class TestBadLineStrategy:
    def test_bad_line_marked_not_dropped(self, c5tmp):
        # 反跑改坏点：坏行被跳过丢弃 → 记录数从 3 变 2 → 红
        path = os.path.join(c5tmp, "bad.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"ok": 1}\n')
            fh.write("这是一行不是 JSON 的坏行\n")
            fh.write('{"ok": 2}\n')
        记录们 = 读JSONL文件(path)
        assert len(记录们) == 3
        assert 记录们[0]["ok"] == 1
        assert 记录们[2]["ok"] == 2
        assert 记录们[1]["坏"] is True
        assert 记录们[1]["行内容"] == "这是一行不是 JSON 的坏行"

    def test_blank_lines_skipped(self, c5tmp):
        path = os.path.join(c5tmp, "blank.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"a": 1}\n\n\n{"a": 2}\n')
        记录们 = 读JSONL文件(path)
        assert [r["a"] for r in 记录们] == [1, 2]

    def test_stream_bad_line_strategy(self, c5tmp):
        # 逐行流式对坏行的处理与整读一致：不丢，带「坏」标记
        path = os.path.join(c5tmp, "sbad.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"ok": 1}\nBADLINE\n')
        流 = list(逐行读JSONL(path))
        assert len(流) == 2
        assert 流[0]["ok"] == 1
        assert 流[1]["坏"] is True


class TestEmpty:
    def test_empty_file_returns_empty_list(self, c5tmp):
        path = os.path.join(c5tmp, "empty.jsonl")
        with open(path, "w", encoding="utf-8"):
            pass
        assert 读JSONL文件(path) == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))