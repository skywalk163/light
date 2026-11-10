# -*- coding: utf-8 -*-
"""吃狗粮场景回归（T-0322）。

两个层次，别混为一谈：
  1) check 层：`python -m cli.light check` 抽 20 个工程体模块，验「语法/类型能不能过」；
     失败集合必须 ⊆ baseline.json，新增失败即红，已有欠账以 xfail 记账。
  2) 场景层：`python -m cli.light run` 真跑 5 个用户目标，rc=0 之外还要看到 stdout 里
     的业务收尾标志；跑不动的场景用 xfail(strict=True) 挂账，原因见 docs/吃狗粮回归.md。

lightharness 全程只读；light 本体缺陷只记录、不修、不开绿灯。
"""
from __future__ import annotations

import json

import pytest

from _dogfood import (
    BASELINE_PATH, LIGHTHARNESS_DIR, REPO_ROOT, SAMPLE, SCENES, SKIP_TEXT,
    merged_results, record, run_cli,
)

_BASELINE_DATA = (
    json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    if BASELINE_PATH.is_file() else {}
)
BASELINE = set(_BASELINE_DATA.get("failed_modules", {}))
# 首次落地清单：failed_modules 只能删、不能加，防止「把新失败塞进基线」消红。
INITIAL_BASELINE = set(_BASELINE_DATA.get("initial_failed_modules", BASELINE))

SCENE_PARAMS = [
    pytest.param(
        scene,
        id=scene["id"],
        marks=pytest.mark.xfail(strict=True, reason=scene["xfail"]) if scene["xfail"] else (),
    )
    for scene in SCENES
]


def test_环境预检():
    """缺 lightharness 时由 conftest 统一 skip；这里是「跑起来」的前置条件。"""
    assert LIGHTHARNESS_DIR.is_dir(), SKIP_TEXT
    assert (REPO_ROOT / "cli" / "light.py").is_file(), "light 仓根缺 cli/light.py，无法跑 CLI 判据"
    assert BASELINE_PATH.is_file(), "缺 tests/dogfood/baseline.json，拒绝无基线运行"
    assert SAMPLE, "lightharness 的 src/ + stdlib/ 下没有发现任何 .light 工程体模块"


@pytest.mark.parametrize("rel", SAMPLE, ids=lambda rel: rel)
def test_check_模块语法与类型(rel):
    """确定化抽样：按相对路径排序前 N，禁止随机。"""
    result = run_cli("check", rel)
    record("check", rel, result)

    if result["rc"] != 0:
        if rel in BASELINE:
            pytest.xfail(
                f"基线欠账 {rel}: rc={result['rc']} | {result['error_first']} | "
                f"{result['detail_first']} | stderr首行={result['stderr_first']!r}"
            )
        pytest.fail(
            f"新增失败（不在 baseline.json）：{rel} rc={result['rc']} | "
            f"{result['error_first']} | {result['detail_first']} | "
            f"stderr首行={result['stderr_first']!r}\n"
            "禁止把基线调大来消红：按 docs/吃狗粮回归.md 定位 light 缺陷并开卡。"
        )
    assert result["rc"] == 0, f"{rel} 的 check 返回码非零"


@pytest.mark.parametrize("scene", SCENE_PARAMS)
def test_场景级_真跑入口(scene):
    """场景 = 一个用户目标被完整跑通，不是「模块存在」。"""
    result = run_cli("run", scene["entry"])
    record("scene", scene["id"], result)

    assert result["rc"] == 0, (
        f"场景「{scene['id']}」未跑通：entry={scene['entry']} rc={result['rc']} | "
        f"stderr首行={result['stderr_first']!r} | {result['error_first']} | "
        f"耗时={result['elapsed_sec']}s"
    )
    if scene["expect"]:
        assert scene["expect"] in result["stdout_excerpt"], (
            f"场景「{scene['id']}」rc=0 但没看到业务收尾标志 {scene['expect']!r}；"
            f"stdout 末行={result['stdout_last']!r} —— 空跑不算跑通"
        )


def test_基线集合未扩大_并提示可缩减项():
    """集合级断言：本次失败集合 ⊆ 基线集合；基线里已通过的条目提示可从文件删除。"""
    checks = merged_results()["check"]
    failed = {m for m, r in checks.items() if r["rc"] != 0}
    new_failures = sorted(failed - BASELINE)
    assert not new_failures, f"失败集合超出基线（新增失败）：{new_failures}"

    # 基线只能缩小：新增条目必须同步改 initial_failed_modules 并在文档登记理由
    added_to_baseline = sorted(BASELINE - INITIAL_BASELINE)
    assert not added_to_baseline, (
        f"基线被调大了（出现首次清单之外的条目）：{added_to_baseline}。"
        "上调需按 docs/吃狗粮回归.md 写明理由并附 light 缺陷卡号，禁止为消红而调大。"
    )

    removable = sorted(m for m in BASELINE if m in checks and checks[m]["rc"] == 0)
    if removable:
        print("\n[dogfood] 基线可缩小 —— 以下条目本次 check 已通过，可从 "
              "tests/dogfood/baseline.json 删除：")
        for m in removable:
            print(f"  - {m}")

    out_of_sample = sorted(m for m in BASELINE if m not in SAMPLE)
    if out_of_sample:
        print("[dogfood] 以下基线条目本次未抽样，保留观察（不自动提示删除）：")
        for m in out_of_sample:
            print(f"  - {m}")

    print(f"[dogfood] 抽样 {len(SAMPLE)} / 已记录 {len(checks)} / 失败 {len(failed)} "
          f"/ 基线欠账 {len(BASELINE)} / 新增失败 {len(new_failures)}")
