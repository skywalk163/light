# -*- coding: utf-8 -*-
"""R137 B 线：积木库（lighting）↔ 光明项目 桥接模块 lighting_bridge 的单元测试。

稳健性约定：积木库是**外部只读仓库**，CI/他人机器上大概率不存在。
因此凡依赖积木库的用例统一 `skipif(not has_lighting())`，缺积木库时**跳过而不是红**；
积木库存在时则真跑、真断言（含 subprocess 跑 `light run` 校验返回值）。

不依赖积木库的用例（模块名清洗、索引缺失兜底、publish 干跑等）始终执行。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import lighting_bridge as lb

ROOT = Path(__file__).resolve().parents[2]          # light-merge/
HAS_LIGHTING = lb.has_lighting()

needs_lighting = pytest.mark.skipif(
    not HAS_LIGHTING,
    reason="本机没有积木库（lighting），跳过依赖积木库的用例",
)


@pytest.fixture
def 临时目录():
    """自建临时目录，替代 pytest 的 `tmp_path`。

    实测（本机，2026-10-11）：`tmp_path` 首次使用要 ~11.7s（pytest basetemp
    创建/清理这段在本仓环境下异常慢），同样场景换 `TemporaryDirectory` 只需
    ~1.4s。为了不把本机 pytest 的这一开销算到本模块头上，这里自己管目录。
    """
    import tempfile
    with tempfile.TemporaryDirectory(prefix="r137_lb_") as d:
        yield Path(d)


# ---------------------------------------------------------------------------
# 纯逻辑用例（不依赖积木库）
# ---------------------------------------------------------------------------

def test_safe_module_name_清洗非法字符():
    """含小数点的积木名必须洗掉点号——原样写进 `从 X 导入` 会触发词法错误。"""
    assert lb.safe_module_name("各乘0.01中文") == "各乘0_01中文"
    assert lb.safe_module_name("乘法") == "乘法"
    assert lb.safe_module_name("10的幂") == "m10的幂"
    assert lb.safe_module_name("A/B*C") == "A_B_C"
    # 清洗结果必须不含小数点，且非空
    for raw in ("各乘0.01中文", "0.5倍", "a.b.c"):
        assert "." not in lb.safe_module_name(raw)
    assert lb.safe_module_name("...") != ""


def test_read_exports_兼容中英文逗号与句号():
    assert lb.read_exports("导出 甲。\n") == ["甲"]
    assert lb.read_exports("导出 甲, 乙。\n") == ["甲", "乙"]
    assert lb.read_exports("导出 甲，乙、丙\n") == ["甲", "乙", "丙"]
    assert lb.read_exports("# 没有导出行\n设 x 为 1。\n") == []


def test_read_contract_从注释兜底描述():
    text = "# 积木：乘法（数学领域，自动生成）\n# 契约：输入 [数, 数] → 输出 数（两个数相乘）\n导出 乘法\n"
    c = lb.read_contract(text)
    assert "两个数相乘" in c["描述"]
    assert c["契约"]


def test_resolve_root_非法根目录时抛异常():
    with pytest.raises(lb.BlocksRootMissing):
        lb.resolve_root(ROOT / "不存在的一个目录名")
    # 可读性：异常消息要带上路径，方便用户定位
    try:
        lb.resolve_root(ROOT / "不存在的一个目录名")
    except lb.BlocksRootMissing as e:
        assert "不存在的一个目录名" in str(e)


def test_ensure_package_toml_追加式修改不破坏既有内容(临时目录):
    toml = 临时目录 / "package.toml"
    toml.write_text(
        "[package]\nname = \"旧项目\"\n自定义键 = \"请保留\"\n\n[dependencies]\n\n",
        encoding="utf-8",
    )
    lb._ensure_package_toml(toml, "积木库", [("数学", "积木库/数学")])
    text = toml.read_text(encoding="utf-8")

    assert "自定义键" in text            # 既有内容不被抹掉
    assert 'name = "旧项目"' in text
    assert '[积木库]' in text
    assert '"数学" = "积木库/数学"' in text

    # 再装一个领域：同节增量追加，且不重复同一键
    lb._ensure_package_toml(toml, "积木库", [("数学", "积木库/数学"), ("文本", "积木库/文本")])
    text2 = toml.read_text(encoding="utf-8")
    assert text2.count('"数学" =') == 1
    assert '"文本" = "积木库/文本"' in text2


def test_publish_to_blocks_默认干跑且能识别导出段落(临时目录):
    """publish 方向不依赖积木库也能跑：默认只出计划，不落盘。"""
    proj = 临时目录 / "proj"
    proj.mkdir()
    (proj / "工具箱.light").write_text(
        "导出 双倍, 三连。\n\n"
        "段落 双倍(甲):\n"
        "    返回 甲 乘 2\n\n"
        "段落 三连 接收 文本：\n"
        "    返回 文本 加 文本 加 文本\n",
        encoding="utf-8",
    )
    r = lb.publish_to_blocks(proj)
    assert r["状态"] == "dry-run"
    assert {c["名称"] for c in r["候选"]} == {"双倍", "三连"}
    assert r["文件"] == []              # 干跑不落盘
    for c in r["候选"]:
        assert c["正文"].startswith("段落")
        assert "返回" in c["正文"]


def test_publish_to_blocks_落地到项目自己的目录(临时目录):
    proj = 临时目录 / "proj2"
    proj.mkdir()
    (proj / "源.light").write_text(
        "导出 加倍。\n段落 加倍(甲):\n    返回 甲 加 甲\n",
        encoding="utf-8",
    )
    r = lb.publish_to_blocks(proj, 落地=True)
    assert r["状态"] == "已落地"
    assert len(r["文件"]) == 1
    out = Path(r["文件"][0])
    assert out.is_file() and out.read_text(encoding="utf-8").startswith("# 积木：")


# ---------------------------------------------------------------------------
# 依赖积木库的用例（缺积木库时跳过）
# ---------------------------------------------------------------------------

@needs_lighting
def test_list_domains_覆盖全量树四十五领域():
    domains = lb.list_domains()
    blocks_domains = lb.list_domains(来源="blocks")
    assert len(blocks_domains) == 45
    # 「完整 45 个领域」判据：全量树的 45 个域必须全部出现在默认清单里
    assert set(blocks_domains) <= set(domains)
    assert "数学" in domains and "数据" in domains and "文本" in domains
    assert domains == sorted(domains)          # 稳定排序，便于 CLI 展示
    # 历史版本快照目录不能被当成领域
    assert "blocks" not in domains and "blocks_v4" not in domains


@needs_lighting
def test_list_blocks_元数据与字段完整性():
    blocks = lb.list_blocks("数学")
    assert blocks, "数学领域不应为空"
    b = next(x for x in blocks if x["名称"] == "乘法")
    assert b["导出名"] == ["乘法"]
    assert b["领域"] == "数学"
    assert b["模块名"] == "乘法"
    assert b["描述"], "没有索引时也要从文件头注释兜底出描述"
    assert Path(b["绝对路径"]).is_file()

    # 全量树里的积木，不应被贴到「只描述根树」的索引元数据上
    assert b["已索引"] is False
    root_version = lb.get_block("数学", "乘法", 来源="根")
    if root_version is not None:
        assert root_version["路径"].startswith("数学/")


@needs_lighting
def test_install_from_blocks_产物齐全(临时目录):
    res = lb.install_from_blocks("数学", 临时目录, blocks=["乘法"])
    assert res["已装数量"] == 1
    pkg_dir = Path(res["包目录"])
    assert (pkg_dir / "乘法.light").is_file()
    assert Path(res["package_toml"]).is_file()
    assert Path(res["清单"]).is_file()

    toml_text = Path(res["package_toml"]).read_text(encoding="utf-8")
    assert "[积木库]" in toml_text and '"数学" = "积木库/数学"' in toml_text
    assert res["导入示例"] == "从 积木库.数学.乘法 导入 乘法。"

    # 同一目标再装一次：幂等，不重复、不报错
    res2 = lb.install_from_blocks("数学", 临时目录, blocks=["乘法"])
    assert res2["已装数量"] == 1
    assert Path(res2["package_toml"]).read_text(encoding="utf-8").count('"数学" =') == 1


@needs_lighting
def test_install_from_blocks_改写非法导出名(临时目录):
    """文件名/导出名含小数点的积木，安装后必须变成合法可调用的形态。"""
    res = lb.install_from_blocks("中文", 临时目录, blocks=["各乘0.01中文"])
    assert res["已装数量"] == 1
    item = res["文件列表"][0]
    assert item["安装名"] == "各乘0_01中文"
    assert item["原始导出名"] == "各乘0.01中文"
    assert item["已改写导出名"] is True

    text = Path(item["文件"]).read_text(encoding="utf-8")
    assert "各乘0.01中文" not in text
    assert "各乘0_01中文" in text


@needs_lighting
def test_install_后_light_run_真实跑通且值正确(临时目录):
    """核心判据：装完能被 `从 ... 导入` 真实调用，输出**值正确**（不是不报错就行）。"""
    res = lb.install_from_blocks("数学", 临时目录, blocks=["乘法"])
    driver = Path(res["目标目录"]) / "驱动.light"
    driver.write_text("从 积木库.数学.乘法 导入 乘法。\n打印(乘法(6, 7))。\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "cli.light", "run", str(driver)],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    assert proc.stdout.strip() == "42"


@needs_lighting
def test_install_清洗名后_light_run_也跑得通(临时目录):
    """被改写的积木（原文件连解析都过不了）安装后同样要能真跑。"""
    res = lb.install_from_blocks("中文", 临时目录, blocks=["各乘0.01中文"])
    driver = Path(res["目标目录"]) / "驱动.light"
    driver.write_text(
        "从 积木库.中文.各乘0_01中文 导入 各乘0_01中文。\n"
        "打印(各乘0_01中文([100, 200]))。\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "-m", "cli.light", "run", str(driver)],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    assert proc.stdout.strip().replace(" ", "") in ("[1.0,2.0]", "[1,2]")


@needs_lighting
def test_publish_to_blocks_拒绝写进只读积木库(临时目录):
    """红线：任何指向积木库内的输出都必须被拒绝，而不是静默写入。"""
    proj = 临时目录 / "proj3"
    proj.mkdir()
    (proj / "源.light").write_text("导出 某块。\n段落 某块(甲):\n    返回 甲\n", encoding="utf-8")

    lighting_root = lb.resolve_root()
    r = lb.publish_to_blocks(proj, 目标目录=str(lighting_root / "blocks" / "数学"))
    assert r["状态"] == "拒绝"
    assert "只读" in r["原因"]
    assert r["文件"] == []
    # 拒绝时必须一个文件都没多出来
    assert not (lighting_root / "blocks" / "数学" / "某块.light").exists()


@needs_lighting
def test_积木库只读本次不写入():
    """保险栓：本模块对外不应提供写回积木库的入口——只读资产。"""
    root = lb.resolve_root()
    before = sorted(os.listdir(root))
    lb.list_domains()
    lb.list_blocks("数学")
    lb.list_domains(来源="根")
    assert sorted(os.listdir(root)) == before
