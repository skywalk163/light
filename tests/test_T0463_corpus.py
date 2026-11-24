# -*- coding: utf-8 -*-
"""T-0463 契约测试：stdlib + spec →（中文需求, 光明代码）配对语料。

覆盖完成标准：
    * 两次运行 light_sft.jsonl 逐字节一致；
    * 条数 ≥ 500；
    * 字段齐全，prompt 不含 code 中的光明关键字与 ASCII 标识符（全量检查）；
    * 抽样 runnable:true 的代码交 light check（本机无 light 时 skip，不造假绿）；
    * manifest.json 可解析且分布总和等于条数；
    * 单样本不超过 60 行，来源只能来自 stdlib/ 与 spec/。
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "tools" / "gen_ai_corpus.py"
SPEC_PATH = REPO_ROOT / "spec" / "light.spec.json"
STDLIB_DIR = REPO_ROOT / "stdlib"
JSONL_NAME = "light_sft.jsonl"
MANIFEST_NAME = "manifest.json"
MIN_COUNT = 500
MAX_LINES = 60
LEVELS = {"L1", "L2", "L3", "L4"}
STRUCTURAL_SINGLE_KEYWORDS = ("设", "若", "且", "与", "为", "从", "在", "的", "是", "空", "长")
RE_ASCII_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_generator(out_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        str(GENERATOR),
        "--out",
        str(out_dir),
        "--min",
        str(MIN_COUNT),
        *extra,
    ]
    return subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )


@pytest.fixture(scope="module")
def spec_keywords() -> list[str]:
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    return [str(item["字"]) for item in raw["keywords"] if item.get("字")]


@pytest.fixture(scope="module")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> dict:
    first = tmp_path_factory.mktemp("corpus_run1")
    second = tmp_path_factory.mktemp("corpus_run2")
    results = {}
    for tag, out_dir in (("first", first), ("second", second)):
        proc = run_generator(out_dir)
        assert proc.returncode == 0, f"生成器退出码 {proc.returncode}：{proc.stderr}"
        results[tag] = {
            "dir": out_dir,
            "jsonl": (out_dir / JSONL_NAME).read_bytes(),
            "manifest": json.loads((out_dir / MANIFEST_NAME).read_text(encoding="utf-8")),
        }
    records = [
        json.loads(line)
        for line in results["first"]["jsonl"].decode("utf-8").splitlines()
        if line.strip()
    ]
    return {
        "first": results["first"],
        "second": results["second"],
        "records": records,
    }


def test_two_runs_are_byte_identical(corpus: dict) -> None:
    first, second = corpus["first"], corpus["second"]
    assert sha256_bytes(first["jsonl"]) == sha256_bytes(second["jsonl"])
    assert first["manifest"] == second["manifest"]
    assert first["manifest"]["jsonl_sha256"] == sha256_bytes(first["jsonl"])


def test_count_ids_and_schema(corpus: dict) -> None:
    records = corpus["records"]
    assert len(records) >= MIN_COUNT, f"条数不足：{len(records)}"
    required = {"id", "prompt", "code", "level", "source", "runnable", "sha256"}
    ids = [record["id"] for record in records]
    assert len(ids) == len(set(ids)), "id 出现重复"
    for index, record in enumerate(records, start=1):
        assert required <= set(record), f"{record.get('id')} 字段缺失"
        assert record["id"] == f"L-{index:04d}"
        assert record["level"] in LEVELS
        assert record["source"].startswith("stdlib/")
        assert (REPO_ROOT / record["source"]).is_file()
        assert isinstance(record["runnable"], bool)
        assert record["sha256"] == sha256_bytes(record["code"].encode("utf-8"))


def test_every_sample_within_line_budget(corpus: dict) -> None:
    for record in corpus["records"]:
        lines = record["code"].splitlines()
        assert lines, f"{record['id']} 代码为空"
        assert len(lines) <= MAX_LINES, f"{record['id']} 共 {len(lines)} 行，超过上限"


def test_prompt_never_leaks_code_tokens(corpus: dict, spec_keywords: list[str]) -> None:
    multi_keywords = [keyword for keyword in spec_keywords if len(keyword) >= 2]
    leaked = []
    sampled = random.Random(463).sample(corpus["records"], min(50, len(corpus["records"])))
    for record in corpus["records"]:
        prompt, code = record["prompt"], record["code"]
        banned = {keyword for keyword in multi_keywords if keyword in code}
        banned.update(RE_ASCII_IDENT.findall(code))
        banned.update(single for single in STRUCTURAL_SINGLE_KEYWORDS if single in code)
        hits = sorted(token for token in banned if token in prompt)
        if hits or RE_ASCII_IDENT.search(prompt):
            leaked.append((record["id"], hits))
    assert not leaked, f"需求侧泄题：{leaked[:5]}"
    assert sampled, "抽样列表为空"


def test_prompts_are_unique_and_human_readable(corpus: dict) -> None:
    records = corpus["records"]
    prompts = [record["prompt"] for record in records]
    assert len(set(prompts)) >= MIN_COUNT, "需求文本重复过多"
    for prompt in prompts:
        assert 8 <= len(prompt) <= 200, prompt
        assert "段落" not in prompt and "返回" not in prompt


def test_manifest_matches_records(corpus: dict) -> None:
    manifest = corpus["first"]["manifest"]
    records = corpus["records"]
    assert manifest["count"] == len(records)
    assert manifest["generator"].endswith("gen_ai_corpus.py")
    assert manifest["max_lines"] == MAX_LINES
    assert sum(manifest["by_level"].values()) == len(records)
    assert sum(manifest["by_source_class"].values()) == len(records)
    matrix_total = sum(
        count
        for level in LEVELS
        for count in manifest["matrix"][level].values()
    )
    assert matrix_total == len(records)
    assert manifest["runnable"] == sum(1 for record in records if record["runnable"])


def test_runnable_samples_pass_light_check(corpus: dict, tmp_path: Path) -> None:
    light = shutil.which("light")
    if not light:
        pytest.skip("本机没有 light 命令，跳过可运行性抽检")

    pool = [record for record in corpus["records"] if record["runnable"]]
    assert len(pool) >= 5, f"可运行样本不足：{len(pool)}"
    picked = random.Random(20261124).sample(pool, 5)
    for record in picked:
        target = tmp_path / f"{record['id']}.light"
        target.write_text(record["code"] + "\n", encoding="utf-8")
        proc = subprocess.run(
            [light, "check", str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        assert proc.returncode == 0, (
            f"{record['id']} 未通过 light check：{proc.stdout}\n{proc.stderr}"
        )