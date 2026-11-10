"""STATUS.md 结构回归：确定性校验，纯 Python / 跨平台（不用 head、grep、awk、$()）。"""
from __future__ import annotations

import re
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "STATUS.md"
README = ROOT / "README.md"
PYPROJECT = ROOT / "pyproject.toml"
SECTIONS = ["## 版本与定位", "## 已稳定", "## 实验性",
            "## 最小可用面", "## 最近一轮变更", "## 已知欠账"]
OPTIONAL = {"docs/MVP_SURFACE.md"}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _version() -> str:
    try:
        import tomllib
        return tomllib.loads(_text(PYPROJECT))["project"]["version"]
    except (ImportError, KeyError, ValueError):
        m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', _text(PYPROJECT))
        assert m, "pyproject.toml 缺 version"
        return m.group(1)


def _section(text: str, title: str) -> str:
    assert title in text, f"缺小节 {title}"
    rest = text[text.index(title) + len(title):]
    nxt = re.search(r"(?m)^## ", rest)
    return rest[:nxt.start()] if nxt else rest


def test_status_exists_and_at_most_100_lines():
    assert STATUS.is_file(), "仓库根目录缺 STATUS.md"
    n = len(_text(STATUS).splitlines())
    assert 1 <= n <= 100, f"STATUS.md 行数 {n} 超出 100"


def test_six_sections_in_fixed_order():
    heads = re.findall(r"(?m)^## .+$", _text(STATUS))
    assert heads == SECTIONS, f"二级标题或顺序不符：{heads}"


def test_version_matches_pyproject():
    ver = _version()
    seg = _section(_text(STATUS), SECTIONS[0])
    assert re.search(r"\b" + re.escape(ver) + r"\b", seg), f"未写入版本 {ver}"


def test_experimental_disclaimer():
    assert "不保证 API 稳定" in _section(_text(STATUS), SECTIONS[2])


def test_five_directions_one_line_each():
    seg = _section(_text(STATUS), SECTIONS[3])
    items = [ln for ln in seg.splitlines() if ln.startswith("- ")]
    assert len(items) == 5, f"最小可用面应有五方向各一行，实得 {len(items)}"


def test_recent_changes_at_most_five():
    seg = _section(_text(STATUS), SECTIONS[4])
    items = [ln for ln in seg.splitlines() if ln.startswith("- ")]
    assert 1 <= len(items) <= 5, f"最近一轮变更 {len(items)} 条，超过 5 条"


def test_relative_links_resolve():
    bad = []
    for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", _text(STATUS)):
        target = link.split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if (ROOT / target).exists():
            continue
        if target in OPTIONAL:
            warnings.warn(f"{target} 尚未合并，跳过该链接存在性检查", UserWarning)
            continue
        bad.append(target)
    assert not bad, f"STATUS.md 相对链接目标不存在：{bad}"


def test_module_count_matches_declared():
    text = _text(STATUS)
    assert "ls stdlib/*.light | wc -l" in text, "未写明模块数统计口径"
    actual = len(list((ROOT / "stdlib").glob("*.light")))
    m = re.search(r"顶层模块\s*\*{0,2}(\d+)\s*个", text)
    assert m and int(m.group(1)) == actual, f"声明模块数与实算 {actual} 不一致"


def test_readme_points_to_status_in_top_30_lines():
    needle = "当前状态与最小可用面见 [STATUS.md](STATUS.md)"
    assert any(needle in ln for ln in _text(README).splitlines()[:30])
