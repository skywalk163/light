# -*- coding: utf-8 -*-
"""报错数据集（tools/ai_copilot/error_corpus.py）的单元测试。

只依赖标准库 + pytest，全部读写落在 tmp 目录。
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "ai_copilot"))

import error_corpus as ec  # noqa: E402


DIAGNOSTIC = {
    "code": "E1001",
    "message": "未知关键字 'models'",
    "hint": "Light 用 define 声明变量",
    "fixes": ["把 models 改成 define models"],
    "line": 3,
}

SOURCE = "\n".join(
    [
        "define main() {",
        '    print("hello")',
        "    models x = 1",
        "    print(x)",
        "}",
    ]
)


@pytest.fixture()
def corpus(tmp_path):
    return tmp_path / "corpus"


def _jsonl_rows(root):
    rows = []
    for path in sorted(Path(root).glob("*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                rows.append(json.loads(raw))
    return rows


def test_record_writes_valid_jsonl(corpus):
    saved = ec.record(
        DIAGNOSTIC,
        SOURCE,
        context={"backend": "src", "lang_level": "v3", "light_version": "3.2"},
        root=corpus,
    )

    assert saved["hits"] == 1
    files = sorted(Path(corpus).glob("*.jsonl"))
    assert len(files) == 1
    assert files[0].name.endswith(".jsonl")

    rows = _jsonl_rows(corpus)
    assert len(rows) == 1
    row = rows[0]
    for field in (
        "ts",
        "code",
        "message",
        "hint",
        "fixes",
        "source_snippet",
        "source_hash",
        "lang_level",
        "backend",
        "light_version",
        "hits",
    ):
        assert field in row, field
    assert row["code"] == "E1001"
    assert len(row["source_hash"]) == 16
    assert "models x = 1" in row["source_snippet"]
    assert "define main() {" in row["source_snippet"]  # 出错行 ±2 行


def test_dedup_keeps_single_line_and_counts_hits(corpus):
    for _ in range(3):
        saved = ec.record(DIAGNOSTIC, SOURCE, root=corpus)

    assert saved["hits"] == 3
    assert len(_jsonl_rows(corpus)) == 1

    index = json.loads((Path(corpus) / "index.json").read_text(encoding="utf-8"))
    assert len(index["entries"]) == 1
    entry = next(iter(index["entries"].values()))
    assert entry["hits"] == 3

    # 不同错误码应当换一行。
    ec.record(dict(DIAGNOSTIC, code="E2002"), SOURCE, root=corpus)
    assert len(_jsonl_rows(corpus)) == 2


def test_snippet_is_redacted(corpus):
    token = "abcdefghijklmnopqrstuvwxyz012345"
    source = "\n".join(
        [
            "define main() {",
            '    token = "{}"'.format(token),
            '    path = "/Users/alice/secret/project/main.light"',
            "}",
        ]
    )
    diagnostic = {
        "code": "E3003",
        "message": '打开 /Users/alice/secret/project/main.light 失败，token={}'.format(token),
        "hint": "检查 /home/alice/project/conf.light",
        "fixes": ["把 /Users/alice/secret/project/main.light 移到项目目录"],
        "line": 3,
    }

    saved = ec.record(diagnostic, source, root=corpus)

    blob = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(Path(corpus).iterdir())
        if path.is_file()
    )
    assert "alice" not in blob
    assert "/Users/" not in blob
    assert "/home/" not in blob
    assert token not in blob
    assert "main.light" in blob  # 只保留 basename
    assert token not in saved["message"]


def test_export_pairs_structure_and_min_hits(corpus):
    ec.record(DIAGNOSTIC, SOURCE, root=corpus)
    ec.record(DIAGNOSTIC, SOURCE, root=corpus)
    ec.record(
        {"code": "E5005", "message": "类型不匹配", "fixes": ["显式转换类型"], "line": 1},
        "define y = 1\n",
        root=corpus,
    )

    pairs = ec.export_pairs(root=corpus)
    assert len(pairs) == 2
    assert all(set(pair) == {"prompt", "completion"} for pair in pairs)
    assert "E1001" in pairs[0]["prompt"]
    assert "models x = 1" in pairs[0]["prompt"]
    assert "修复步骤" in pairs[0]["completion"]
    assert "define models" in pairs[0]["completion"]

    only_hot = ec.export_pairs(min_hits=2, root=corpus)
    assert len(only_hot) == 1
    assert "E1001" in only_hot[0]["prompt"]


def test_summary_sorted_and_windowed(corpus):
    for _ in range(3):
        ec.record(DIAGNOSTIC, SOURCE, root=corpus)
    ec.record(
        {"code": "E2002", "message": "缩进错误", "fixes": [], "line": 1},
        "define z = 2\n",
        root=corpus,
    )

    rows = ec.summary(window_days=30, root=corpus)
    assert [row["code"] for row in rows] == ["E1001", "E2002"]
    assert rows[0]["hits"] == 3
    assert rows[1]["hits"] == 1
    assert all(set(row) == {"code", "hits", "last_seen"} for row in rows)

    assert len(ec.summary(window_days=30, top=1, root=corpus)) == 1
    # 窗口为 0 时，已经落盘的记录都算过期。
    assert ec.summary(window_days=0, root=corpus) == []


def test_purge_dry_run_then_remove(corpus):
    ec.record(DIAGNOSTIC, SOURCE, root=corpus)
    ec.record(
        {"code": "E2002", "message": "缩进错误", "fixes": [], "line": 1},
        "define z = 2\n",
        root=corpus,
    )

    index_path = Path(corpus) / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    for entry in index["entries"].values():
        if entry["code"] == "E1001":
            entry["last_seen"] = "2020-01-01T00:00:00+08:00"
    index_path.write_text(json.dumps(index), encoding="utf-8")

    dry = ec.purge(before="2021-01-01T00:00:00+08:00", root=corpus)
    assert dry["dry_run"] is True
    assert dry["removed_count"] == 1
    assert dry["removed"][0]["code"] == "E1001"
    assert len(_jsonl_rows(corpus)) == 2  # dry-run 不落盘

    real = ec.purge(before="2021-01-01T00:00:00+08:00", dry_run=False, root=corpus)
    assert real["removed_count"] == 1
    assert real["files_rewritten"] == 1
    remaining = _jsonl_rows(corpus)
    assert [row["code"] for row in remaining] == ["E2002"]
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(index["entries"]) == 1


def test_concurrent_appends_never_write_half_line(corpus):
    def work(i):
        return ec.record(
            {"code": "E9000", "message": "并发错误 {}".format(i), "fixes": []},
            "define value{} = {}\nprint(value{})\n".format(i, i, i),
            root=corpus,
        )

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(work, range(100)))

    assert all(item["hits"] == 1 for item in results)
    rows = _jsonl_rows(corpus)
    assert len(rows) == 100
    for row in rows:
        assert row["code"] == "E9000"

    index = json.loads((Path(corpus) / "index.json").read_text(encoding="utf-8"))
    assert len(index["entries"]) == 100


def test_default_root_can_be_overridden_by_env(tmp_path, monkeypatch):
    target = tmp_path / "env_corpus"
    monkeypatch.setenv("LIGHT_ERROR_CORPUS_DIR", str(target))

    ec.record(DIAGNOSTIC, SOURCE)

    assert list(target.glob("*.jsonl"))
