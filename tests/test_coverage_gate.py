# -*- coding: utf-8 -*-
"""T-0323 · CI 覆盖率门禁自身的判据测试。

全部用伪造的 coverage.json（coverage.py JSON format 3）做 fixture，
不依赖 coverage 是否安装、不跑全量测试、不联网。
边界按任务卡：69.9 红 / 70.0 绿、单文件缺失、未覆盖区间格式化、
rc 0/1/2 契约、--min 0 放行；另加防假绿与 CI 接线完整性。

环境说明：仓库根 pyproject.toml 的 addopts 带
``--timeout=60 -n 4 --dist=loadscope``，跑本文件需要既有的
pytest-xdist / pytest-timeout（CI 依赖步骤已装）。本卡不改 pyproject、
不引入 pytest-cov、不给这套 addopts 增加任何新依赖。
"""

from __future__ import annotations

import configparser
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_coverage.py"
CORE = (
    "src/lexer.py",
    "src/light_parser_v3.py",
    "src/compiler.py",
    "src/code_generator.py",
)


@pytest.fixture(scope="module")
def gate():
    """直接加载脚本模块，用于测纯函数（compress_ranges / compute_coverage）。"""
    spec = importlib.util.spec_from_file_location("check_coverage_under_test", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # dataclass 解析注解时会查 sys.modules[cls.__module__]，不注册会炸
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _entry(executed, missing, *, lying_pct=None):
    return {
        "executed_lines": list(executed),
        "missing_lines": list(missing),
        "excluded_lines": [],
        "summary": {
            "covered_lines": len(executed),
            "num_statements": len(executed) + len(missing),
            # 故意允许造假：门禁必须不采信这个字段
            "percent_covered": lying_pct if lying_pct is not None
            else 100.0 * len(executed) / max(1, len(executed) + len(missing)),
            "missing_lines": len(missing),
        },
    }


def _all_core(covered: int, total: int = 1000, *, key_style="posix"):
    """四个核心文件都是 covered/total，行号不重叠。"""
    files = {}
    for rel in CORE:
        key = rel.replace("/", "\\") if key_style == "windows" else rel
        files[key] = _entry(range(1, covered + 1), range(covered + 1, total + 1))
    return files


def _write_report(tmp_path: Path, files: dict, *, name="coverage.json") -> Path:
    payload = {
        "meta": {"format": 3, "version": "7.17.2", "branch_coverage": False},
        "files": files,
        "totals": {"covered_lines": 0, "num_statements": 0, "percent_covered": 0.0},
    }
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _run(path: Path, *extra: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--coverage-json", str(path), *extra],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )


# ── 阈值边界 ────────────────────────────────────────────────────────────────

def test_70_0_is_green(tmp_path):
    cp = _run(_write_report(tmp_path, _all_core(700)))
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert cp.stdout.count("[PASS]") == 4
    assert "70.00%" in cp.stdout


def test_69_9_is_red(tmp_path):
    cp = _run(_write_report(tmp_path, _all_core(699)))
    assert cp.returncode == 1, cp.stdout + cp.stderr
    assert "[FAIL]" in cp.stdout
    assert "69.90%" in cp.stdout
    assert "1 个文件不达标" not in cp.stdout  # 四个都 69.9，应报 4 个
    assert cp.stdout.count("[FAIL]") == 4


def test_exact_boundary_70_of_100_is_green(tmp_path):
    """70/100 = 70.0% 精确等于阈值，>= 判绿（不四舍五入、不 +epsilon）。"""
    cp = _run(_write_report(tmp_path, _all_core(70, 100)))
    assert cp.returncode == 0, cp.stdout + cp.stderr


def test_one_file_below_threshold_is_red_and_others_still_pass(tmp_path):
    files = _all_core(800)
    files["src/compiler.py"] = _entry(range(1, 500), range(500, 1001))
    cp = _run(_write_report(tmp_path, files))
    assert cp.returncode == 1
    assert cp.stdout.count("[PASS]") == 3
    assert cp.stdout.count("[FAIL]") == 1
    assert "49.90%" in cp.stdout


def test_custom_min(tmp_path):
    path = _write_report(tmp_path, _all_core(700))
    assert _run(path, "--min", "85").returncode == 1
    assert _run(path, "--min", "50").returncode == 0


def test_min_zero_allows_zero_coverage(tmp_path):
    """--min 0 只应急放行，不意味着可以删文件/改口径。"""
    cp = _run(_write_report(tmp_path, _all_core(0)), "--min", "0")
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert cp.stdout.count("[PASS]") == 4
    assert "0.00%" in cp.stdout


def test_invalid_min_is_rc2(tmp_path):
    path = _write_report(tmp_path, _all_core(700))
    assert _run(path, "--min", "-1").returncode == 2
    assert _run(path, "--min", "101").returncode == 2
    assert _run(path, "--min", "nan").returncode == 2


# ── 输入完整性与 rc 契约 ─────────────────────────────────────────────────────

def test_missing_one_core_file_is_red_not_skipped(tmp_path):
    files = _all_core(900)
    del files["src/light_parser_v3.py"]
    cp = _run(_write_report(tmp_path, files))
    assert cp.returncode == 1
    assert "src/light_parser_v3.py" in cp.stdout
    assert "未出现在覆盖统计中" in cp.stdout


def test_missing_input_is_rc2_with_generate_hint(tmp_path):
    cp = _run(tmp_path / "nope.json")
    assert cp.returncode == 2
    text = cp.stdout + cp.stderr
    assert "怎么生成" in text
    assert "coverage json" in text
    assert "scripts/check_coverage.py" in text


@pytest.mark.parametrize("payload", [
    "{not json",
    "[]",
    '{"meta": {}}',
    '{"files": []}',
    '{"files": {}}',
    '{"files": {"src/lexer.py": {"executed_lines": ["x"]}}}',
    '{"files": {"src/lexer.py": {"executed_lines": -3}}}',
])
def test_malformed_input_is_rc2(tmp_path, payload):
    path = tmp_path / "broken.json"
    path.write_text(payload, encoding="utf-8")
    cp = _run(path)
    assert cp.returncode == 2, cp.stdout + cp.stderr
    assert "怎么生成" in cp.stdout + cp.stderr


# ── 未覆盖行号区间与防假绿 ───────────────────────────────────────────────────

def test_missing_ranges_format(tmp_path):
    """12-18, 40, 55-57 三段必须出现在 FAIL 文件的报告里。"""
    files = _all_core(900)
    files["src/compiler.py"] = _entry(
        [1, 2, 3, 19, 20, 39, 41, 42, 54, 58, 59, 60],
        [12, 13, 14, 15, 16, 17, 18, 40, 55, 56, 57],
    )
    cp = _run(_write_report(tmp_path, files))
    assert cp.returncode == 1
    assert "12-18, 40, 55-57" in cp.stdout


def test_compress_ranges_pure_function(gate):
    assert gate.compress_ranges([]) == "（无）"
    assert gate.compress_ranges([5]) == "5"
    assert gate.compress_ranges([1, 2, 3, 7, 9, 10]) == "1-3, 7, 9-10"
    assert gate.compress_ranges([3, 1, 2, 2, 10, 9]) == "1-3, 9-10"  # 去重 + 排序
    assert gate.compress_ranges([12, 13, 14, 15, 16, 17, 18, 40, 55, 56, 57]) == "12-18, 40, 55-57"


def test_summary_percent_covered_is_not_trusted(tmp_path):
    """summary 写 99% 但行号数组是 0% → 必须红（防「改 summary 消红」）。"""
    files = _all_core(900)
    files["src/lexer.py"] = _entry([], range(1, 1001), lying_pct=99.0)
    cp = _run(_write_report(tmp_path, files))
    assert cp.returncode == 1
    assert "0.00%" in cp.stdout
    assert "1-1000" in cp.stdout


def test_windows_style_keys_are_normalized(tmp_path):
    cp = _run(_write_report(tmp_path, _all_core(800, key_style="windows")))
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert cp.stdout.count("[PASS]") == 4


def test_absolute_path_keys_are_normalized(tmp_path):
    files = _all_core(800)
    files = {"C:/work/light/" + k: v for k, v in files.items()}
    cp = _run(_write_report(tmp_path, files))
    assert cp.returncode == 0, cp.stdout + cp.stderr


def test_other_files_below_threshold_do_not_fail_the_gate(tmp_path):
    """不给全仓设门槛：非核心文件 0% 也不许影响判定。"""
    files = _all_core(900)
    files["src/totally_untouched.py"] = _entry([], range(1, 5001))
    files["tests/test_whatever.py"] = _entry([], range(1, 501))
    cp = _run(_write_report(tmp_path, files))
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert "仅 4 个核心文件" in cp.stdout


def test_empty_statement_file_is_not_fake_green(tmp_path):
    files = _all_core(900)
    files["src/lexer.py"] = _entry([], [])
    cp = _run(_write_report(tmp_path, files))
    assert cp.returncode == 1
    assert "0.00%" in cp.stdout


# ── CI / 配置接线完整性（防止「脚本写了但 CI 没挂」）─────────────────────────

def test_coveragerc_matches_contract():
    cfg = configparser.ConfigParser()
    assert cfg.read(REPO_ROOT / ".coveragerc", encoding="utf-8")
    run = cfg["run"]
    assert run["source"].strip() == "src"
    assert run.get("branch", "false").lower() == "false"
    for pattern in ("tests/*", "tools/*", "examples/*", "scripts/*"):
        assert pattern in run["omit"], f"omit 缺 {pattern}"


def test_gate_script_is_stdlib_only():
    import re
    source = SCRIPT.read_text(encoding="utf-8")
    # 不许 import coverage / pytest_cov（纯标准库是任务卡硬约束）
    assert not re.search(r"^\s*(import|from)\s+coverage\b", source, re.M)
    assert "pytest_cov" not in source
    assert "不装 pytest-cov" in source  # 口径注释要留着，防止后人装回来


def test_ci_step_is_wired_without_changing_existing_budget():
    text = (REPO_ROOT / ".gitea" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "coverage run -m pytest" in text
    assert "coverage json" in text
    assert "scripts/check_coverage.py" in text
    assert "--min 70" in text                 # 70% 硬门槛，CI 不许私自调低
    assert "覆盖统计的范围" in text           # 口径声明（任务卡硬性要求）
    assert "timeout-minutes: 3" in text      # 新增步骤自带 ≤180s 硬超时
    assert "BUDGET=3000" in text and "BUDGET=1800" in text   # 既有超时数值未改
    assert "tests/ci_baseline_failures.txt" in text           # 既有回归闸门未动
    # .github 是另一套流水线，本次不许碰（另开卡）
    github_ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/check_coverage.py" not in github_ci


def test_core_file_list_exactly_four(gate):
    assert gate.CORE_FILES == CORE
    assert len(gate.CORE_FILES) == 4
