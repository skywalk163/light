# -*- coding: utf-8 -*-
"""智能原语与中文语法兼容层 —— 最小原型测试。

覆盖四类验收项：
  A 词法/语法（归一化后仍走原有分析流程，缩进/字符串/注释/L4 块不受破坏）
  B 映射表与配置（可配置、可关闭、冲突有清晰诊断）
  C 可观测性（结构化轨迹字段）
  D/E 向后兼容回归 + 最小示例编译运行
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from smart_primitives import (  # noqa: E402
    ENV_ENABLED, ENV_MAP, ENV_TRACE, ENV_CONFLICT,
    SmartConfig, apply_smart_elastic, compile_rules, load_map,
    preprocess, resolve_config, validate_map,
)
from keywords import ALL_KEYWORDS  # noqa: E402

EXAMPLE_DIR = ROOT / "examples" / "智能原语"
STD_EXAMPLE = EXAMPLE_DIR / "观察_规划_执行.light"
SPOKEN_EXAMPLE = EXAMPLE_DIR / "观察_规划_执行_口语变体.light"
STANDARDS = ("观察", "规划", "决策", "执行", "记忆")


def _cfg(primitives=None, **kw):
    prim = load_map()["primitives"] if primitives is None else primitives
    params = dict(enabled=True, trace=True, primitives=prim,
                  map_path=str(SRC / "smart_primitives_map.json"))
    params.update(kw)
    return SmartConfig(**params)


def _pp(source, **kw):
    return preprocess(source, config=_cfg(**kw))


def _run_cli(script: Path, extra_env=None):
    env = dict(os.environ)
    env.pop(ENV_ENABLED, None)
    env.pop(ENV_MAP, None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "cli.light", "run", str(script)],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
        encoding="utf-8", timeout=30,
    )


def _indents(text: str):
    return [len(line) - len(line.lstrip(" ")) for line in text.splitlines()]


def _defs(text: str):
    return set(re.findall(r"^段\s+([^\s(（]+)\s*\(", text, re.M))


# ── A. 映射表与词法/语法安全 ────────────────────────────────────────────

def test_默认映射表结构与双字单义():
    raw = load_map()
    assert raw["schema"] == "light.smart-elastic-map/v1"
    assert raw["scope"] == "identifier"
    assert raw["enabled"] is False          # 默认关闭是兼容性的硬保证
    assert set(raw["primitives"]) == set(STANDARDS)
    for name, spec in raw["primitives"].items():
        assert len(name) == 2, f"标准形式必须是双字: {name}"
        assert spec["variants"] and spec["kind"]


def test_L0冻结未被触碰_标准词都不是关键字():
    for word in STANDARDS:
        assert word not in ALL_KEYWORDS, f"{word} 不该进关键字表"
    # 变体也都不是关键字（弹性层只做标识符重命名，不碰词法）
    for spec in load_map()["primitives"].values():
        for v in spec["variants"]:
            assert v not in ALL_KEYWORDS, f"变体 {v} 撞关键字"


def test_计划_安排_筹谋_归一到_规划():
    src = "设 甲 为 计划(1)\n设 乙 为 安排(2)\n设 丙 为 筹谋(3)\n"
    r = _pp(src)
    assert r.source.count("规划(") == 3
    assert "计划(" not in r.source
    assert {(w["from"], w["to"]) for w in r.rewrites} == {
        ("计划", "规划"), ("安排", "规划"), ("筹谋", "规划")}


def test_五原语口语变体全覆盖():
    src = "看看(1) 计划(2) 拍板(3) 动手(4) 记下(5)\n"
    r = _pp(src)
    for std in STANDARDS:
        assert std + "(" in r.source


def test_中文词边界_长词不误替换():
    # 旧 elastic_syntax.py 用 \b，对中文失效；这里验证「计划书 / 计划表」不被切
    src = "段 计划书():\n    返回 1\n设 甲 为 计划表\n"
    r = _pp(src)
    assert "段 计划书():" in r.source
    assert "计划表" in r.source
    assert r.rewrites == []


def test_字符串与注释受保护():
    src = '# 计划：这段注释里也提到计划\n打印("计划已定")\n设 甲 为 计划(1)\n'
    r = _pp(src)
    assert "# 计划：这段注释里也提到计划" in r.source
    assert '"计划已定"' in r.source
    assert "为 规划(1)" in r.source


def test_缩进与行结构逐字符保留():
    src = ("段 主():\n"
           "    设 甲 为 计划(1)\n"
           "        若 甲:\n"
           "            打印(甲)\n")
    r = _pp(src)
    assert _indents(r.source) == _indents(src)
    assert len(r.source.splitlines()) == len(src.splitlines())


def test_L4嵌入块原样透传():
    src = ("引 Python:\n"
           "    计划 = 1\n"
           "结束引\n"
           "段 主():\n"
           "    返回 计划(1)\n")
    r = _pp(src)
    assert "    计划 = 1" in r.source       # 嵌入块内不替换
    assert "规划(1)" in r.source            # 块外照常归一化


def test_长变体优先():
    prim = {"规划": {"variants": ["计划"]}, "记忆": {"variants": ["计划书"]}}
    src = "设 甲 为 计划书\n设 乙 为 计划\n"
    r = _pp(src, primitives=prim)
    assert "为 记忆" in r.source
    assert "为 规划" in r.source


def test_归一化源码可通过原有词法与语法():
    from cli.light import _compile_src
    r = _pp(SPOKEN_EXAMPLE.read_text(encoding="utf-8"))
    py_code = _compile_src(r.source)
    assert isinstance(py_code, str) and py_code.strip()
    compile(py_code, "<smart-elastic>", "exec")   # 生成产物语法有效


# ── B. 配置 / 关闭 / 诊断 ───────────────────────────────────────────────

def test_默认关闭_源码逐字节不变():
    src = STD_EXAMPLE.read_text(encoding="utf-8")   # 不含文件头指令
    r = preprocess(src, env={})
    assert r.enabled is False
    assert r.source is src


def test_文件头开指令覆盖环境变量关闭():
    src = SPOKEN_EXAMPLE.read_text(encoding="utf-8")   # 含「# @智能弹性 开」
    r = preprocess(src, env={ENV_ENABLED: "0"})
    assert r.enabled is True and "段 观察(" in r.source


def test_环境变量开启():
    cfg, _ = resolve_config("设 甲 为 计划(1)", env={ENV_ENABLED: "1"})
    assert cfg.enabled is True
    assert cfg.trace is True


def test_文件头指令优先级_开():
    src = "# @智能弹性 开\n设 甲 为 计划(1)\n"
    cfg, _ = resolve_config(src, env={ENV_ENABLED: "0"})
    assert cfg.enabled is True and cfg.directive == "on"


def test_文件头指令优先级_关():
    src = "# @智能弹性 关\n设 甲 为 计划(1)\n"
    cfg, _ = resolve_config(src, env={ENV_ENABLED: "1"})
    assert cfg.enabled is False and cfg.directive == "off"


def test_自定义映射表生效(tmp_path):
    p = tmp_path / "custom.json"
    p.write_text(json.dumps({
        "schema": "light.smart-elastic-map/v1", "version": 1,
        "enabled": True, "scope": "identifier", "on_conflict": "diagnose",
        "primitives": {"规划": {"kind": "plan", "variants": ["打算盘"]}},
    }, ensure_ascii=False), encoding="utf-8")
    src = "设 甲 为 打算盘(1)\n"
    cfg, diags = resolve_config(src, env={ENV_MAP: str(p), ENV_ENABLED: "1"})
    assert cfg.enabled is True and diags == []
    r = preprocess(src, config=cfg)
    assert "规划(1)" in r.source


def test_自定义映射表损坏时诊断(tmp_path):
    cfg, diags = resolve_config(
        "设 甲 为 1", env={ENV_MAP: str(tmp_path / "missing.json"), ENV_ENABLED: "1"})
    assert any(d.code == "L-SMART-004" for d in diags)
    assert cfg.primitives                     # 回退到兜底表，不崩


def test_冲突_撞关键字_L_SMART_001():
    prim = {"规划": {"variants": ["如果", "计划"]}}
    diags = validate_map(prim)
    hit = [d for d in diags if d.code == "L-SMART-001" and d.source == "如果"]
    assert hit and hit[0].severity == "error"
    rules, _ = compile_rules(prim)
    assert all(variant != "如果" for variant, _, _ in rules)   # 该规则被丢弃


def test_冲突_重复变体_L_SMART_003():
    prim = {"规划": {"variants": ["计划"]}, "记忆": {"variants": ["计划"]}}
    diags = validate_map(prim)
    assert any(d.code == "L-SMART-003" and "同时映射" in d.message for d in diags)


def test_冲突_混用_L_SMART_002():
    src = "段 规划():\n    返回 1\n段 计划():\n    返回 2\n"
    r = _pp(src)
    hit = [d for d in r.diagnostics if d.code == "L-SMART-002"]
    assert hit and hit[0].line > 0 and hit[0].column > 0


def test_on_conflict_keep_与_warn():
    prim = {"规划": {"variants": ["如果"]}}
    r_keep = preprocess("设 甲 为 1", config=_cfg(primitives=prim, on_conflict="keep"))
    assert r_keep.diagnostics == []
    r_warn = preprocess("设 甲 为 1", config=_cfg(primitives=prim, on_conflict="warn"))
    assert r_warn.diagnostics
    assert all(d.severity == "warning" for d in r_warn.diagnostics)


def test_轨迹可独立关闭():
    r = _pp("设 甲 为 计划(1)\n", trace=False)
    assert r.enabled is True and r.trace == {}


def test_关闭时CLI零副作用(monkeypatch):
    monkeypatch.delenv(ENV_ENABLED, raising=False)
    src = "段 主():\n    打印(计划)\n"
    assert apply_smart_elastic(src, file_path=None) is src


# ── C. 可观测性 ─────────────────────────────────────────────────────────

def test_轨迹字段齐全():
    r = _pp(SPOKEN_EXAMPLE.read_text(encoding="utf-8"))
    t = r.trace
    assert t["schema"] == "light.smart-trace/v1"
    assert t["pattern"] == "observe_plan_act"
    assert t["duration_ms"] >= 0
    assert t["rewrites"]
    assert set(t["primitives"]) == set(STANDARDS)
    types = {e["type"] for e in t["events"]}
    assert {"tool_call", "decision_point", "side_effect", "duration"} <= types
    for e in t["events"]:
        assert "line" in e and "type" in e


def test_轨迹sidecar写入(tmp_path):
    p = tmp_path / "口语.light"
    p.write_text(SPOKEN_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    out = apply_smart_elastic(p.read_text(encoding="utf-8"), file_path=str(p))
    assert "段 观察(" in out
    trace_file = Path(str(p) + ".smart-trace.json")
    assert trace_file.exists()
    doc = json.loads(trace_file.read_text(encoding="utf-8"))
    assert doc["pattern"] == "observe_plan_act"
    assert any(e["type"] == "tool_call" for e in doc["events"])


# ── D. 向后兼容回归 ─────────────────────────────────────────────────────

def test_旧elastic_syntax行为未变():
    from elastic_syntax import ElasticSyntaxPreprocessor
    out = ElasticSyntaxPreprocessor().preprocess("要是 甲 大于 1")
    assert "如果" in out


def test_普通代码开启弹性层后逐字节不变():
    src = ("# 文体: 文言\n段 主():\n    设 分数 为 85\n"
           "    若 分数 >= 60:\n        打印(\"及格\")\n    返回 分数\n主()\n")
    r = _pp(src)
    assert r.source == src
    assert r.rewrites == []


def test_标准双字写法本身就是规范代码():
    src = STD_EXAMPLE.read_text(encoding="utf-8")
    r = _pp(src)
    assert r.source == src                  # 不需任何前端改写就能编译
    assert r.rewrites == []


# ── E. 最小示例编译运行 ─────────────────────────────────────────────────

def test_标准示例直接运行():
    r = _run_cli(STD_EXAMPLE, {ENV_ENABLED: "0"})
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("执行动作: 走") == 3
    assert "完成" in r.stdout


def test_口语变体示例运行并保留字符串原文(tmp_path):
    p = tmp_path / "口语.light"
    p.write_text(SPOKEN_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    r = _run_cli(p)
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("计划已定: 走") == 3   # 字符串里的「计划」未被改写
    assert r.stdout.count("记下: 走") == 3
    assert "完成" in r.stdout


def test_归一化后与标准写法段落名一致():
    spoken = _pp(SPOKEN_EXAMPLE.read_text(encoding="utf-8")).source
    std = STD_EXAMPLE.read_text(encoding="utf-8")
    assert _defs(spoken) == _defs(std)
    assert "设 动作 为 规划(" in spoken         # 口语词「计划」被归一成标准形式


def test_口语示例在弹性层关闭时仍可独立运行(tmp_path):
    """设计约束：弹性层只做风格归一化，绝不是代码能跑的前提。"""
    src = SPOKEN_EXAMPLE.read_text(encoding="utf-8").replace(
        "# @智能弹性 开", "# @智能弹性 关", 1)
    p = tmp_path / "口语_关闭.light"
    p.write_text(src, encoding="utf-8")
    r = _run_cli(p, {ENV_ENABLED: "0"})
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("计划已定: 走") == 3


def test_混写口语变体时弹性层使其自洽(tmp_path):
    """定义写「计划」、调用写「安排」，只有开启弹性层才合一。"""
    src = SPOKEN_EXAMPLE.read_text(encoding="utf-8").replace(
        "设 动作 为 计划(信号, 轮)", "设 动作 为 安排(信号, 轮)")
    p = tmp_path / "口语_混写.light"
    p.write_text(src, encoding="utf-8")
    r = _run_cli(p)                              # 文件头「开」→ 弹性层生效
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("计划已定: 走") == 3
