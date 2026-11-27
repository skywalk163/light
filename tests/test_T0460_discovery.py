# -*- coding: utf-8 -*-
"""T-0460 零配置发现：AGENTS.md / llms.txt / skills/light/SKILL.md 三入口。

判据来自任务卡「完成标准」：
  1. 三个文件存在；总字节 ≤12000；单文件 ≥500（防空文件过关）
  2. AGENTS.md 含 `light ai check --json`、`读取文件`、`打印`
  3. llms.txt 首行以 `# ` 开头且含 `## ` 分节
  4. SKILL.md frontmatter 有 name 与 description
  5. 正文反引号里的相对路径全部真实存在（至少覆盖 docs/、spec/、stdlib/）
  6. 事实与 spec/light.spec.json 一致：L0 字数、≥5 关键字、≥5 stdlib 函数名

第 5、6 条是防文档腐烂的关键：路径写错、函数名写错，测试立刻红。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
LLMS = ROOT / "llms.txt"
SKILL = ROOT / "skills" / "light" / "SKILL.md"
SPEC = ROOT / "spec" / "light.spec.json"

ENTRIES = (AGENTS, LLMS, SKILL)
TOTAL_MAX_BYTES = 12000
SINGLE_MIN_BYTES = 500
SINGLE_MAX_BYTES = 6000

BACKTICK_RE = re.compile(r"`([^`\n]+)`")
MD_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
DOC_SUFFIX_RE = re.compile(r"\.(md|json|py|light|toml|yml|yaml|txt)$")

# 反引号里可能出现的“非路径”内容：运算符、通配、标点、纯占位
NON_PATH_CHARS = set("()[]{}<>,;:\"'：，。、“”‘’*|=&+")
URL_PREFIXES = ("http://", "https://", "#", "mailto:")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def looks_like_relative_path(token: str) -> bool:
    """只把形如 `docs/xxx.md`、`stdlib/文件系统.light` 的反引号内容当路径。

    排除：带空格的命令（`light ai card`）、函数调用（`读取文件(路径)`）、
    选项（`--full`）、运算符（`&&`）、纯占位（`变量-整数`）。
    """
    token = token.strip()
    if not token or " " in token or "\t" in token:
        return False
    if any(ch in NON_PATH_CHARS for ch in token):
        return False
    if token.startswith(URL_PREFIXES):
        return False
    if "\\" in token:  # Windows 绝对路径不在本文档约定里
        return False
    if "/" not in token and not DOC_SUFFIX_RE.search(token):
        return False
    return bool(re.search(r"[A-Za-z\u4e00-\u9fff]", token))


def resolve_exists(token: str) -> bool:
    rel = token.strip().rstrip("/")
    return (ROOT / rel).exists()


def test_entry_files_exist_and_budgeted():
    for p in ENTRIES:
        assert p.is_file(), f"缺少入口文件：{p.relative_to(ROOT)}"
    sizes = {p.name: len(read(p).encode("utf-8")) for p in ENTRIES}
    assert all(s >= SINGLE_MIN_BYTES for s in sizes.values()), f"文件太小像空壳：{sizes}"
    assert all(s <= SINGLE_MAX_BYTES for s in sizes.values()), f"单文件超 6KB：{sizes}"
    assert sum(sizes.values()) <= TOTAL_MAX_BYTES, f"三入口合计超 12000 字节：{sizes}"


def test_agents_md_has_required_markers():
    text = read(AGENTS)
    # 卡面点名要有的三样
    assert "light ai check --json" in text
    assert "读取文件" in text
    assert "打印" in text
    # 六条硬规则的关键事实
    for marker in ("中文关键字", "冒号", "stdin", "缩进"):
        assert marker in text, f"AGENTS.md 缺少硬规则事实：{marker}"
    # 常用命令小表四件套
    for cmd in ("light ai card", "light ai snippets", "light 运行"):
        assert cmd in text, f"AGENTS.md 缺少命令：{cmd}"


def test_llms_txt_format():
    text = read(LLMS)
    first_line = text.splitlines()[0]
    assert first_line.startswith("# "), f"llms.txt 首行必须是以 '# ' 开头的标题：{first_line!r}"
    assert "\n## " in text, "llms.txt 必须含 '## ' 分节"

    links = MD_LINK_RE.findall(text)
    assert links, "llms.txt 的「## 链接」里至少要有一个链接"
    for target in links:
        if target.startswith(URL_PREFIXES):
            continue
        assert (ROOT / target).exists(), f"llms.txt 链接指向不存在的路径：{target}"


def test_skill_frontmatter_has_name_and_description():
    text = read(SKILL)
    assert text.startswith("---\n"), "SKILL.md 必须以 frontmatter 开头"
    end = text.find("\n---", 4)
    assert end > 0, "SKILL.md frontmatter 没有闭合的 ---"
    front = text[4:end]

    fields = {}
    for line in front.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()

    assert fields.get("name") == "light", f"frontmatter name 必须是 light：{fields.get('name')!r}"
    description = fields.get("description", "")
    assert len(description) >= 20, "description 要写清什么时候该用它，不能只有一句空话"
    assert "when_to_use" in fields, "frontmatter 缺少 when_to_use"


def test_all_backticked_paths_exist():
    missing = []
    covered = {"docs/": 0, "spec/": 0, "stdlib/": 0}
    for p in ENTRIES:
        for token in BACKTICK_RE.findall(read(p)):
            if not looks_like_relative_path(token):
                continue
            if not resolve_exists(token):
                missing.append(f"{p.relative_to(ROOT)} -> {token}")
            for prefix in covered:
                if token.strip().rstrip("/").startswith(prefix):
                    covered[prefix] += 1

    assert not missing, "文档里的相对路径并不存在：\n" + "\n".join(missing)
    for prefix, count in covered.items():
        assert count > 0, f"三入口没有引用 {prefix} 下的真实路径，覆盖不足"


def test_facts_match_spec():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    texts = {p.name: read(p) for p in ENTRIES}

    l0_count = spec["l0_core"]["实际字数"]
    assert any(str(l0_count) in t for t in texts.values()), (
        f"三入口都没写与 spec 一致的 L0 字数 {l0_count}")

    keyword_names = [item["字"] for item in spec["keywords"]]
    found_kw = [k for k in keyword_names if any(k in t for t in texts.values())]
    assert len(found_kw) >= 5, f"与 spec 对上的关键字不足 5 个：{found_kw}"

    stdlib_names = []
    for module in spec["stdlib"]["模块"]:
        stdlib_names.extend(entry["名字"] for entry in module["导出"])
    found_stdlib = sorted({n for n in stdlib_names if any(n in t for t in texts.values())})
    assert len(found_stdlib) >= 5, f"与 spec 对上的 stdlib 函数名不足 5 个：{found_stdlib}"

    # 反向抽查：写进去的 stdlib 名必须是 spec 里真实存在的导出
    for name in ("读取文件", "写入文件", "文件存在", "分割", "拼接"):
        assert name in stdlib_names, f"spec 里没有这个导出：{name}"
