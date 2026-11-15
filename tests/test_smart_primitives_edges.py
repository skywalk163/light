# -*- coding: utf-8 -*-
"""智能原语弹性层 —— 边界与回归测试。

这些用例是首轮 33 项测试**没有覆盖**的缺口，由独立评审实测暴露后补齐：
保护区（中文引号 / 三引号跨行 / L4 四种写法 / 缩进回归）、字节级格式保持、
配置通道与坏映射表降级、诊断语义、轨迹误报、CLI 默认路径的 import 开销。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from smart_primitives import (  # noqa: E402
    ENV_CONFLICT, ENV_ENABLED, ENV_MAP,
    SmartConfig, apply_smart_elastic, compile_rules, load_map,
    preprocess, resolve_config,
)

STD = ("观察", "规划", "决策", "执行", "记忆")


def _cfg(**kw):
    params = dict(enabled=True, trace=True, primitives=load_map()["primitives"],
                  map_path=str(SRC / "smart_primitives_map.json"))
    params.update(kw)
    return SmartConfig(**params)


def _pp(source, **kw):
    return preprocess(source, config=_cfg(**kw))


def _cli(args, env_extra=None):
    env = dict(os.environ)
    for k in (ENV_ENABLED, ENV_MAP, ENV_CONFLICT):
        env.pop(k, None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, "-m", "cli.light"] + args,
                          cwd=str(ROOT), env=env, capture_output=True,
                          text=True, encoding="utf-8", timeout=60)


# ── 保护区：中文引号 / 三引号跨行 / 多行字符串 ─────────────────────────

@pytest.mark.parametrize("src,expect", [
    ("打印(「计划」)\n安排()\n", "打印(「计划」)\n规划()\n"),
    ("打印(『计划』)\n安排()\n", "打印(『计划』)\n规划()\n"),
    ('打印("计划")\n安排()\n', '打印("计划")\n规划()\n'),
])
def test_中文与英文引号内的变体不被替换(src, expect):
    assert _pp(src).source == expect


def test_三引号跨行字符串内容不被替换():
    src = '设 文案 为 """\n计划：文案里的安排\n"""\n安排()\n'
    out = _pp(src).source
    assert "计划：文案里的安排" in out      # 字符串内容原样
    assert out.endswith("规划()\n")          # 字符串外的调用照常归一


def test_普通字符串含换行时内容不被替换():
    src = '打印("计划\n安排")\n安排()\n'
    out = _pp(src).source
    assert '"计划\n安排"' in out
    assert out.endswith("规划()\n")


def test_转义引号不打断字符串边界():
    src = '打印("他说\\"计划\\"")\n安排()\n'
    out = _pp(src).source
    assert '"他说\\"计划\\""' in out
    assert out.endswith("规划()\n")


# ── 保护区：L4 嵌入块的四种写法 + 缩进回归 + EOF ───────────────────────

@pytest.mark.parametrize("open_line,close_line", [
    ("引 Python:", "结束引"),
    ("引 Python:", "结束嵌入"),
    ("嵌入 Python:", "结束引"),
    ("嵌入 Python:", "结束嵌入"),
])
def test_L4四种起止写法块内都不替换(open_line, close_line):
    src = f"{open_line}\n    计划 = 1\n{close_line}\n段 主():\n    返回 计划(1)\n"
    out = _pp(src).source
    assert "    计划 = 1" in out        # 外语代码零改动
    assert "规划(1)" in out             # 块外照常归一


def test_L4缩进回归自动闭合():
    """官方允许省略结束标记，靠缩进回到开启行来闭合（lexer.py:2142-2165）。"""
    src = ("段 主():\n"
           "    引 Python:\n"
           "        计划 = 1\n"
           "    返回 计划(1)\n")
    out = _pp(src).source
    assert "        计划 = 1" in out
    assert "返回 规划(1)" in out


def test_L4文件以缩进块体结尾时EOF闭合():
    src = "段 主():\n    引 Python:\n        计划 = 1\n"
    out = _pp(src).source
    assert out == src                    # 全部在块内，一个字符都不动


# ── 字节级格式保持 ─────────────────────────────────────────────────────

def test_CRLF逐字节保持():
    src = "段 计划():\r\n    安排()\r\n"
    out = _pp(src).source
    assert out == "段 规划():\r\n    规划()\r\n"
    assert "\n" not in out.replace("\r\n", "")   # 没有裸 LF


def test_Tab与混合缩进保持():
    src = "段 计划():\n\t安排()\n"
    assert _pp(src).source == "段 规划():\n\t规划()\n"


def test_末尾无换行时不被补换行():
    src = "段 计划():\n    安排()"
    out = _pp(src).source
    assert not out.endswith("\n")
    assert out.endswith("规划()")


def test_空行与BOM保持():
    src = "\ufeff段 计划():\n\n    安排()\n\n"
    out = _pp(src).source
    assert out.startswith("\ufeff")
    assert "\n\n" in out


# ── 配置通道 / 坏映射表降级 ────────────────────────────────────────────

def test_仅设MAP时映射表enabled_true可独立开启(tmp_path):
    p = tmp_path / "on.json"
    p.write_text(json.dumps({
        "schema": "light.smart-elastic-map/v1", "version": 1,
        "enabled": True, "scope": "identifier",
        "primitives": {"规划": {"kind": "plan", "variants": ["计划"]}},
    }, ensure_ascii=False), encoding="utf-8")
    src = "段 主():\n    返回 计划(1)\n"
    # apply_smart_elastic 读 os.environ，这里用 resolve_config 覆盖同一逻辑
    cfg, diags = resolve_config(src, env={ENV_MAP: str(p)})
    assert cfg.enabled is True and diags == []
    assert "规划(1)" in preprocess(src, config=cfg).source
    # CLI 全链路同样生效
    f = tmp_path / "t.light"
    f.write_text(src, encoding="utf-8")
    r = _cli(["compile", str(f), "-o", str(tmp_path / "t.py")], {ENV_MAP: str(p)})
    assert r.returncode == 0, r.stderr
    assert "规划" in (tmp_path / "t.py").read_text(encoding="utf-8")


def test_坏spec不再令CLI崩溃且给出004(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"schema":"light.smart-elastic-map/v1","version":1,'
                 '"enabled":true,"scope":"identifier",'
                 '"primitives":{"规划":"计划"}}', encoding="utf-8")
    f = tmp_path / "t.light"
    f.write_text("段 主():\n    返回 计划(1)\n", encoding="utf-8")
    r = _cli(["ast", str(f)], {ENV_ENABLED: "1", ENV_MAP: str(p)})
    assert r.returncode == 0, r.stderr
    assert "L-SMART-004" in r.stderr
    assert "Traceback" not in r.stderr


def test_schema不匹配时降级并给004(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('{"schema":"WRONG/v9","version":1,"enabled":true,'
                 '"scope":"identifier","primitives":{"规划":{"variants":["计划"]}}}',
                 encoding="utf-8")
    cfg, diags = resolve_config("设 甲 为 1", env={ENV_MAP: str(p)})
    assert any(d.code == "L-SMART-004" and d.severity == "error" for d in diags)
    assert cfg.primitives          # 回退兜底表，不崩


def test_keep不吞配置类诊断(tmp_path):
    r = preprocess("段 规划():\n    规划()\n", env={
        ENV_ENABLED: "1", ENV_MAP: str(tmp_path / "nope.json"), ENV_CONFLICT: "keep"})
    assert [d.code for d in r.diagnostics] == ["L-SMART-004"]


def test_BOM与行尾注释都可识别文件头指令():
    for src in ("\ufeff# @智能弹性 开\n段 主():\n    计划(1)\n",
                "# @智能弹性 开  # 说明\n段 主():\n    计划(1)\n"):
        cfg, _ = resolve_config(src, env={})
        assert cfg.enabled is True and cfg.directive == "on"


def test_文件头关优先级高于环境变量开():
    src = "# @智能弹性 关\n设 甲 为 计划(1)\n"
    cfg, _ = resolve_config(src, env={ENV_ENABLED: "1"})
    assert cfg.enabled is False
    assert apply_smart_elastic(src, file_path=None) is src


# ── 轨迹：不误报、模式判定 ─────────────────────────────────────────────

def test_轨迹不把字符串与注释里的调用记成事件():
    src = ('段 主():\n'
           '    打印("规划(测试)")\n'
           '    观察(1)  # 规划(2)\n'
           '    当 轮 < 3:\n'
           '        执行(1)\n')
    t = _pp(src).trace
    calls = [(e["line"], e["primitive"]) for e in t["events"] if e["type"] == "tool_call"]
    assert calls == [(3, "观察"), (5, "执行")]


def test_乱序三连且无循环不算惯用模式():
    t = _pp("观察(1)\n执行(2)\n规划(3)\n").trace
    assert t["pattern"] == "custom"


def test_完整三段式带循环才算惯用模式():
    src = ("段 主():\n"
           "    当 轮 < 3:\n"
           "        观察(1)\n"
           "        规划(2)\n"
           "        执行(3)\n")
    assert _pp(src).trace["pattern"] == "observe_plan_act"


def test_规则缓存不污染诊断对象():
    p = load_map()["primitives"]
    _, d1 = compile_rules(p)
    _, d2 = compile_rules(p)
    d1.append("污染")
    _, d3 = compile_rules(p)
    assert len(d3) == len(d2) and all(hasattr(d, "code") for d in d3)


# ── CLI 默认路径的开销与健壮性 ─────────────────────────────────────────

def test_默认关闭时不加载弹性层模块():
    code = (
        "import sys\n"
        f"sys.path[:0] = [{str(ROOT)!r}, {str(SRC)!r}]\n"
        "from cli.light import _read_source\n"
        "import pathlib, tempfile\n"
        "p = pathlib.Path(tempfile.mkdtemp()) / 'a.light'\n"
        "p.write_text('段 主():\\n    打印(1)\\n', encoding='utf-8')\n"
        "_read_source(str(p))\n"
        "print('LOADED' if 'smart_primitives' in sys.modules else 'NOT_LOADED')\n"
    )
    env = dict(os.environ)
    for k in (ENV_ENABLED, ENV_MAP):
        env.pop(k, None)
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    assert "NOT_LOADED" in r.stdout


def test_未开启时普通文件行为与直接读文件一致(tmp_path):
    f = tmp_path / "plain.light"
    src = "段 主():\n    设 甲 为 1\n    打印(甲)\n"
    f.write_text(src, encoding="utf-8")
    r = _cli(["run", str(f)])
    assert r.returncode == 0, r.stderr
    assert "1" in r.stdout
