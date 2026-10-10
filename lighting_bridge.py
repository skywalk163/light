# -*- coding: utf-8 -*-
"""积木库（lighting 仓库）↔ 光明项目 的桥接模块（R137 B 线）。

定位
----
`lighting`（积木库）**永远是只读的数据源**：本模块只读它，从不写入。
本模块负责把积木库里的 `.light` 积木「装」进一个光明项目，使该项目能用

    从 <包名>.<领域>.<积木名> 导入 <导出名>

真实调用到积木实现。

积木库真实结构（2026-10 实测，与早期任务书描述不同）
------------------------------------------------
`lighting` 根下**同时存在两棵积木树**，两者是不同的两代实现，同名文件内容也不同：

* `<root>/blocks/<领域>/*.light` —— 自动生成的全量树，45 个领域 / 14222 个文件。
* `<root>/<领域>/*.light`       —— 较早的 L0 手写树，36 个领域 / 2474 个文件，
  `索引.json` 的 `路径` 字段**以它为基准**（182 条契约全部命中这棵树）。

因此本模块把「来源」做成一等概念（`来源` 参数：`'blocks'` / `'根'` / None）：

* `list_domains()`：None → **两树并集（48 个）**；`'blocks'` → 45 个；`'根'` → 36 个。
* `list_blocks() / install_from_blocks()`：None → 该领域在全量树里有就整域取全量树，
  否则退回首尾完整的根树（不混装两代，避免同一包里出现两种代码风格/两套命名）。

设计约束
--------
* 纯标准库，不引新依赖。
* 积木库路径**不硬编码**：优先 `root` 参数 → 环境变量 `LIGHTING_ROOT` →
  模块同级/父级自动探测。默认常量只作为「探测不到」时的兜底，可被环境变量覆盖。
* 绝不写 lighting：所有写操作都在用户指定的目标目录；`publish_to_blocks`
  显式拒绝任何落在 lighting 内的输出目录。

公开接口
--------
    has_lighting()              —— 积木库是否可用
    list_domains()              —— 领域清单
    list_blocks()               —— 某领域积木清单（含导出名/描述/契约）
    get_block()                 —— 单个积木
    install_from_blocks()       —— 把某领域积木装进目标光明项目（核心）
    publish_to_blocks()         —— 反向导出（降级：只产出计划与暂存区文件）
    safe_module_name()          —— 文件名 → 合法光明模块名
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "LIGHTING_ROOT_ENV",
    "BlocksRootMissing",
    "has_lighting",
    "resolve_root",
    "list_domains",
    "list_blocks",
    "get_block",
    "install_from_blocks",
    "publish_to_blocks",
    "safe_module_name",
    "read_exports",
    "INDEX_FILE",
    "BLOCKS_DIR_NAME",
]

# ---------------------------------------------------------------------------
# 常量与路径解析（全部可配置，不把绝对路径写进逻辑）
# ---------------------------------------------------------------------------

#: 覆盖默认积木库根的环境变量
LIGHTING_ROOT_ENV = "LIGHTING_ROOT"

#: 契约索引文件名（协议 v1.0）
INDEX_FILE = "索引.json"

#: 全量积木树所在子目录名
BLOCKS_DIR_NAME = "blocks"

#: 「根树」来源标签 / 「全量树」来源标签
SRC_ROOT = "根"
SRC_BLOCKS = "blocks"

#: 默认 package.toml 里的登记表节名（也是默认包名）
DEFAULT_PACKAGE_NAME = "积木库"

#: 安装清单文件名（写进**目标目录**侧，不写 lighting）
MANIFEST_FILE = "_积木清单.json"

#: 兜底默认根（仅当环境变量与自动探测全部失效时使用；不是硬编码依赖，
#: 正常使用路径由 _候选根() 推导）
_FALLBACK_ROOT = Path(__file__).resolve().parent.parent / "lighting"

_EXPORTS_RE = re.compile(r"^[ \t]*导出[ \t]+(.+?)[ \t]*$", re.M)
_HEADER_积木_RE = re.compile(r"^#[ \t]*积木[：:][ \t]*(.+?)[ \t]*$", re.M)
_HEADER_契约_RE = re.compile(r"^#[ \t]*契约[：:][ \t]*(.+?)[ \t]*$", re.M)
_段落_RE = re.compile(r"^([ \t]*)段落[ \t]+(\S+)[ \t]*(?:接收|\()(.+?)[ \t]*(?:）|\)|:|：)?[ \t]*$")


class BlocksRootMissing(FileNotFoundError):
    """积木库根目录不存在（安装/ubuntu CI 等机器上普遍如此）。"""


def _候选根() -> List[Path]:
    """推导积木库根的候选位置（按优先级）。"""
    here = Path(__file__).resolve().parent
    cands: List[Path] = []
    env = os.environ.get(LIGHTING_ROOT_ENV, "").strip()
    if env:
        cands.append(Path(env))
    cands.extend([
        here.parent / "lighting",      # light-merge/ 与 lighting/ 平级（本机实测布局）
        here / "lighting",
        Path.cwd() / "lighting",
        Path.cwd().parent / "lighting",
        _FALLBACK_ROOT,
    ])
    seen = set()
    out = []
    for c in cands:
        try:
            key = str(c)
        except Exception:  # pragma: no cover - 防御
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _is_blocks_root(p: Path) -> bool:
    """判定一个目录是否为积木库根：含 blocks/ 子目录或 索引.json。"""
    try:
        return (p / BLOCKS_DIR_NAME).is_dir() or (p / INDEX_FILE).is_file()
    except OSError:
        return False


def resolve_root(root: Optional[os.PathLike | str] = None) -> Path:
    """解析积木库根目录。

    Args:
        root: 显式指定；None 时按 `LIGHTING_ROOT` 环境变量 → 自动探测。

    Raises:
        BlocksRootMissing: 显式指定却不存在，或自动探测全部落空。
    """
    if root is not None:
        p = Path(root).expanduser()
        if not _is_blocks_root(p):
            raise BlocksRootMissing(f"积木库根目录不可用: {p}")
        return p.resolve()
    for cand in _候选根():
        if _is_blocks_root(cand):
            return cand.resolve()
    raise BlocksRootMissing(
        "未找到积木库（lighting）。请显式传 root，或设置环境变量 "
        f"{LIGHTING_ROOT_ENV} 指向积木库根。"
    )


def has_lighting(root: Optional[os.PathLike | str] = None) -> bool:
    """积木库是否可用（不可用时返回 False，不抛异常）。供上层 skip 判断。"""
    try:
        resolve_root(root)
        return True
    except BlocksRootMissing:
        return False


# ---------------------------------------------------------------------------
# 文本工具：导出名 / 契约注释 / 模块名清洗
# ---------------------------------------------------------------------------

def _split_exports(raw: str) -> List[str]:
    """把 `导出 甲, 乙。` 解析成 ['甲','乙']（兼容中英文逗号与句号）。"""
    raw = raw.strip()
    for tail in ("。", "；", ";", "，", ","):
        if raw.endswith(tail):
            raw = raw[: -len(tail)].strip()
    parts = re.split(r"[，,、;；]", raw)
    return [p.strip() for p in parts if p.strip()]


def read_exports(text: str) -> List[str]:
    """从积木源码文本里读出全部导出名（实测每个积木恰好 1 个）。"""
    out: List[str] = []
    for m in _EXPORTS_RE.finditer(text):
        out.extend(_split_exports(m.group(1)))
    # 去重保序
    seen = set()
    uniq = []
    for n in out:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def read_contract(text: str) -> Dict[str, str]:
    """读 `# 积木：` / `# 契约：` 两行注释，作为无索引时的元数据兜底。"""
    head = "\n".join(text.splitlines()[:6])
    m1 = _HEADER_积木_RE.search(head)
    m2 = _HEADER_契约_RE.search(head)
    desc = ""
    if m2:
        desc = m2.group(1).strip()
    elif m1:
        desc = m1.group(1).strip()
    return {
        "描述": desc,
        "名称注释": m1.group(1).strip() if m1 else "",
        "契约": m2.group(1).strip() if m2 else "",
    }


def safe_module_name(name: str) -> str:
    """把积木文件名/积木名洗成「能被光明语法解析」的模块名。

    必要性（实测）：14222 个积木里有 3313 个文件名含小数点（如
    `各乘0.01中文.light`）。光明词法会把 `0.01` 切成数字字面量，
    `从 各乘0.01中文 导入 ...` 直接 `语法错误 ... 无法识别的语法元素：'0.01'`。
    因此安装时必须把 `.` 洗成 `_`，并把其它非标识符字符一并替换。
    """
    out = []
    for ch in name:
        if ch.isalnum() or ch == "_" or ord(ch) >= 0x2000:
            out.append(ch)
        else:
            out.append("_")
    s = "".join(out).strip("_")
    if not s:
        s = "积木"
    # 纯数字开头的模块名在部分后端里容易被当成字面量，加前缀规避
    if s[0].isdigit():
        s = "m" + s
    return s


# ---------------------------------------------------------------------------
# 索引.json
# ---------------------------------------------------------------------------

def _load_index(root: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """读契约索引，键为 (领域, 路径)。索引不存在/损坏时返回空表（不致命）。"""
    path = root / INDEX_FILE
    idx: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not path.is_file():
        return idx
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return idx
    for b in data.get("块", []) or []:
        if not isinstance(b, dict):
            continue
        key = (str(b.get("领域", "")), str(b.get("路径", "")).replace("\\", "/"))
        if key[1]:
            idx[key] = b
    return idx


# ---------------------------------------------------------------------------
# 来源（两棵树）遍历
# ---------------------------------------------------------------------------

def _sources(root: Path, 来源: Optional[str] = None) -> List[Tuple[str, Path]]:
    """返回 [(来源标签, 树基目录)]，顺序即优先级。

    来源取值：None/'全部' → blocks 优先再根树；'blocks' → 仅全量树；'根'/'索引' → 仅根树。
    """
    all_src = [(SRC_BLOCKS, root / BLOCKS_DIR_NAME), (SRC_ROOT, root)]
    if 来源 is None or 来源 in ("全部", "all"):
        return [(t, d) for t, d in all_src if d.is_dir()]
    if 来源 in (SRC_BLOCKS, "blocks"):
        return [(t, d) for t, d in all_src if t == SRC_BLOCKS and d.is_dir()]
    if 来源 in (SRC_ROOT, "根", "索引"):
        return [(t, d) for t, d in all_src if t == SRC_ROOT and d.is_dir()]
    raise ValueError(f"未知来源筛选: {来源!r}（可选 None / 'blocks' / '根'）")


def _walk_lights(base: Path) -> List[str]:
    """列出 base 下全部 .light 的相对路径（posix 形式，已排序）。"""
    if not base.is_dir():
        return []
    rels = []
    for dp, _dn, fn in os.walk(base):
        rel_dir = os.path.relpath(dp, base)
        if rel_dir == ".":
            rel_dir = ""
        for f in fn:
            if f.endswith(".light"):
                rels.append(f"{rel_dir}/{f}" if rel_dir else f)
    return sorted(rels)


def list_domains(root: Optional[os.PathLike | str] = None,
                 来源: Optional[str] = None) -> List[str]:
    """列出积木库全部领域名（去重、排序）。

    Args:
        root: 积木库根，None 走自动解析。
        来源: None → 两棵树并集；'blocks' → 仅全量树；'根' → 仅根树。
    """
    base = resolve_root(root)
    names = set()
    for tag, tree in _sources(base, 来源):
        try:
            entries = os.listdir(tree)
        except OSError:
            continue
        for e in entries:
            if e.startswith(".") or e == "__pycache__":
                continue
            p = tree / e
            if not p.is_dir() or e == BLOCKS_DIR_NAME:
                continue
            # blocks_v4 / blocks_v5 是历史版本快照目录，不是领域
            if e.startswith("blocks"):
                continue
            # 根树下混着 demo / docs_site / archive 等非领域目录
            if tag == SRC_ROOT and e in ("demo", "docs_site", "archive", "tools", "scripts"):
                continue
            if _walk_lights(p):
                names.add(e)
    return sorted(names)


def _默认来源(base: Path, 领域: str, 来源: Optional[str]) -> Optional[str]:
    """单个领域的默认取树策略：全量树有该领域就用全量树，否则退回根树。

    理由：两棵树是**不同代实现**（实测同名文件内容完全不同），混装会把两种
    代码风格/两套导出命名塞进同一个包，调用方难以预期。默认整域取同一代。
    """
    if 来源 is not None:
        return 来源
    if (base / BLOCKS_DIR_NAME / 领域).is_dir():
        return SRC_BLOCKS
    return SRC_ROOT


def _build_block_entry(tree: Path, tag: str, rel: str, 领域: str,
                       index: Dict[Tuple[str, str], Dict[str, Any]]) -> Dict[str, Any]:
    """组装单个积木的描述字典。"""
    src = tree / rel
    try:
        text = src.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    exports = read_exports(text)
    contract = read_contract(text)
    name_only = Path(rel).name[: -len(".light")]
    名称 = name_only
    # 相对积木库**根**的路径：根树是 `<领域>/xxx.light`，全量树是 `blocks/<领域>/xxx.light`。
    # 契约索引的 `路径` 字段以根为基准且从不含 `blocks/` 前缀 ⇒ 用它做 key 才能
    # 保证「索引元数据只贴到它真正描述的那份文件上」。
    根相对路径 = f"{领域}/{rel}" if tag == SRC_ROOT else f"{BLOCKS_DIR_NAME}/{领域}/{rel}"

    entry: Dict[str, Any] = {
        "名称": 名称,
        "领域": 领域,
        "路径": 根相对路径,
        "相对路径": rel,
        "绝对路径": str(src),
        "来源": tag,
        "导出名": exports,
        "导出名主": exports[0] if exports else name_only,
        "模块名": safe_module_name(名称),
        "描述": contract["描述"],
        "契约": contract["契约"],
        "已索引": False,
        "输入": [],
        "输出": None,
        "稳定性": "",
    }
    key = (领域, 根相对路径)
    if key in index:
        b = index[key]
        entry["已索引"] = True
        entry["描述"] = b.get("描述") or entry["描述"]
        entry["输入"] = b.get("输入") or []
        entry["输出"] = b.get("输出")
        entry["稳定性"] = b.get("稳定性", "")
        entry["索引名称"] = b.get("名称", "")
        entry["索引导出名"] = b.get("导出名", "")
    return entry


def list_blocks(领域: str, root: Optional[os.PathLike | str] = None,
                来源: Optional[str] = None) -> List[Dict[str, Any]]:
    """列出某领域的全部积木。

    同名（相对路径相同）积木在两棵树并存时，按 `来源` 优先级取其一，
    优先级的第一个胜出，另一份丢弃（两者是不同代实现，用一个即可）。

    Returns:
        [{名称, 领域, 路径, 相对路径, 绝对路径, 来源, 导出名, 模块名,
          描述, 契约, 已索引, 输入, 输出, 稳定性}, ...]
    """
    base = resolve_root(root)
    index = _load_index(base)
    picked: Dict[str, Dict[str, Any]] = {}
    for tag, tree in _sources(base, _默认来源(base, 领域, 来源)):
        domain_dir = tree / 领域
        if not domain_dir.is_dir():
            continue
        for rel in _walk_lights(domain_dir):
            if rel in picked:
                continue
            picked[rel] = _build_block_entry(domain_dir, tag, rel, 领域, index)
    return [picked[k] for k in sorted(picked)]


def get_block(领域: str, 名称: str, root: Optional[os.PathLike | str] = None,
              来源: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """按名称（文件名/积木名/模块名任一）取单个积木，取不到返回 None。"""
    target = str(名称)
    target_safe = safe_module_name(target)
    for b in list_blocks(领域, root=root, 来源=来源):
        if target in (b["名称"], b["导出名主"], b["模块名"]) or target_safe == b["模块名"]:
            return b
    return None


# ---------------------------------------------------------------------------
# package.toml 读写（极简，按光明 project 的 mini-TOML 子集）
# ---------------------------------------------------------------------------

def _ensure_package_toml(toml_path: Path, 包名: str,
                         registrations: Sequence[Tuple[str, str]]) -> bool:
    """确保 `package.toml` 存在且含 `[<包名>]` 登记表。返回是否发生写入。

    对既有文件只做**追加式**修改：没有对应节就整节追加；有则替换同名键的行，
    其余内容原样保留（不重写整个文件，避免破坏用户手写配置）。
    """
    new_lines = [f'"{领域}" = "{rel}"' for 领域, rel in registrations]
    section = f"[{包名}]"

    if not toml_path.exists():
        text = (
            "# 光明项目配置（由 lighting_bridge.install_from_blocks 生成）\n"
            "[package]\n"
            f'name = "{toml_path.parent.name}"\n'
            'version = "0.1.0"\n'
            'entry = "主.light"\n'
            'description = ""\n'
            "\n"
            "[dependencies]\n"
            "\n"
            f"{section}\n"
            + "".join(l + "\n" for l in new_lines)
        )
        toml_path.write_text(text, encoding="utf-8")
        return True

    raw = toml_path.read_text(encoding="utf-8", errors="replace")
    out: List[str] = raw.splitlines()
    changed = False

    # 定位既有节
    sec_start = None
    for i, line in enumerate(out):
        if line.strip() == section:
            sec_start = i
            break

    if sec_start is None:
        if out and out[-1].strip():
            out.append("")
        out.append(section)
        out.extend(new_lines)
        changed = True
    else:
        sec_end = len(out)
        for j in range(sec_start + 1, len(out)):
            if out[j].strip().startswith("["):
                sec_end = j
                break
        body = out[sec_start + 1: sec_end]
        want = dict(registrations)
        kept: List[str] = []
        for line in body:
            key = line.split("=", 1)[0].strip().strip('"').strip("'")
            if key in want:
                # 值变了就换新行
                if f'"{key}" = "{want[key]}"' != line.strip():
                    kept.append(f'"{key}" = "{want[key]}"')
                    changed = True
                else:
                    kept.append(line)
                del want[key]
            else:
                kept.append(line)
        for k, v in want.items():
            kept.append(f'"{k}" = "{v}"')
            changed = True
        out[sec_start + 1: sec_end] = kept

    if changed:
        toml_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


# ---------------------------------------------------------------------------
# 安装：积木库 → 光明项目（核心）
# ---------------------------------------------------------------------------

def install_from_blocks(领域: str,
                        目标目录: os.PathLike | str,
                        blocks: Optional[Iterable[str]] = None,
                        root: Optional[os.PathLike | str] = None,
                        包名: Optional[str] = DEFAULT_PACKAGE_NAME,
                        覆盖: bool = True,
                        来源: Optional[str] = None,
                        限制: Optional[int] = None,
                        改写非法导出名: bool = True) -> Dict[str, Any]:
    """把一个领域的积木装进目标光明项目，使其可被 `从 ... 导入 ...` 调用。

    产物布局（`包名` 非 None 时）：

        <目标目录>/package.toml            ← 新建或追加 [积木库] 登记
        <目标目录>/<包名>/<领域>/xxx.light ← 积木副本（文件名已洗成合法模块名）
        <目标目录>/<包名>/<领域>/_积木清单.json

    目标项目里即可：

        从 积木库.数学.乘法 导入 乘法
        打印(乘法(6, 7))     # 42

    `包名=None` 时退化为「平铺」：积木直接落在 `<目标目录>/` 下，导入写
    `从 乘法 导入 乘法`（多领域混装会重名，谨慎使用）。

    Args:
        领域: 领域名，如 "数学"。
        目标目录: 光明项目根目录。
        blocks: 只要这几个积木（名称/导出名/模块名任一匹配）；None 表示全部。
        root: 积木库根。
        包名: 安装根包名；None 表示平铺安装。
        覆盖: 目标已存在同名文件时是否覆盖。
        来源: 树筛选，同 list_blocks。
        限制: 最多装多少个（调试用）。
        改写非法导出名: 把含小数点等非法标识符的**导出符号名**一并改写成
            合法名（`各乘0.01中文` → `各乘0_01中文`）。实测 14222 个积木里有
            3313 个是这种名字：原文件连 `导出 各乘0.01中文` 这一行都解析不过，
            属于死数据；改写后首次可用。只改**副本**，不动积木库源文件。

    Returns:
        dict：领域 / 包名 / 导入前缀 / 包目录 / 已装数量 / 文件列表 /
        模块名映射 / package.toml 路径 / 清单路径 / 跳过 / 导入示例。
    """
    base = resolve_root(root)
    dest_root = Path(目标目录)
    dest_root.mkdir(parents=True, exist_ok=True)

    wanted = None
    if blocks is not None:
        wanted = set()
        for b in blocks:
            s = str(b)
            wanted.add(s)
            wanted.add(safe_module_name(s))

    all_blocks = list_blocks(领域, root=base, 来源=来源)
    if not all_blocks:
        raise FileNotFoundError(f"积木库里没有领域「{领域}」（root={base}）")

    selected: List[Dict[str, Any]] = []
    for b in all_blocks:
        if wanted is not None:
            hit = ({b["名称"], b["导出名主"], b["模块名"]} & wanted)
            if not hit:
                continue
        selected.append(b)
    if 限制 is not None:
        selected = selected[: int(限制)]

    if 包名:
        dest_dir = dest_root / 包名 / 领域
        导入前缀 = f"{包名}.{领域}"
    else:
        dest_dir = dest_root
        导入前缀 = ""
    dest_dir.mkdir(parents=True, exist_ok=True)

    已装: List[Dict[str, str]] = []
    跳过: List[Dict[str, str]] = []
    已用名: Dict[str, int] = {}

    for b in selected:
        # 领域树基本是平铺：目录段保留原文，只有最后一段（文件名）清洗改名
        rel_parts = Path(b["相对路径"]).parts
        dir_parts = list(rel_parts[:-1])
        stem = Path(rel_parts[-1]).stem
        安装名 = safe_module_name(stem)
        if 安装名 in 已用名:
            已用名[安装名] += 1
            安装名 = f"{安装名}_{已用名[安装名]}"
        else:
            已用名[安装名] = 0

        rel_out = "/".join([*dir_parts, 安装名 + ".light"])
        target = dest_dir / rel_out
        if target.exists() and not 覆盖:
            跳过.append({"名称": b["名称"], "目标": str(target), "原因": "已存在且覆盖=False"})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(b["绝对路径"], target)
        except OSError as e:
            跳过.append({"名称": b["名称"], "目标": str(target), "原因": f"复制失败: {e}"})
            continue

        改写映射 = {e: safe_module_name(e) for e in b["导出名"] if safe_module_name(e) != e}
        if 改写非法导出名 and 改写映射:
            # 只改副本：把非法符号名整体换成合法名，使这类积木首次可被引擎解析
            try:
                text = target.read_text(encoding="utf-8", errors="replace")
                for old, new in 改写映射.items():
                    text = text.replace(old, new)
                target.write_text(text, encoding="utf-8")
            except OSError as e:
                跳过.append({"名称": b["名称"], "目标": str(target),
                             "原因": f"改写导出名失败: {e}"})
                continue

        实际导出名 = [改写映射.get(e, e) for e in b["导出名"]]
        导入名 = f"{导入前缀}.{安装名}" if 导入前缀 else 安装名
        已装.append({
            "名称": b["名称"],
            "安装名": 安装名,
            "导入名": 导入名,
            "导出名": ",".join(实际导出名),
            "原始导出名": ",".join(b["导出名"]),
            "已改写导出名": bool(改写非法导出名 and 改写映射),
            "来源": b["来源"],
            "文件": str(target),
        })

    # package.toml 登记
    toml_path = dest_root / "package.toml"
    包相对路径 = os.path.relpath(dest_dir, dest_root).replace("\\", "/")
    _ensure_package_toml(toml_path, 包名 or DEFAULT_PACKAGE_NAME,
                         [(领域, 包相对路径)])

    # 安装清单（写在目标侧，绝不写回积木库）
    manifest = {
        "积木库根": str(base),
        "领域": 领域,
        "包名": 包名,
        "导入前缀": 导入前缀,
        "已装数量": len(已装),
        "跳过数量": len(跳过),
        "积木": 已装,
        "跳过": 跳过,
    }
    manifest_path = dest_dir / MANIFEST_FILE
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    示例导出 = 已装[0]["导出名"].split(",")[0] if 已装 else "X"
    示例导入 = 已装[0]["导入名"] if 已装 else f"{导入前缀}.<积木名>"
    导入示例 = f"从 {示例导入} 导入 {示例导出}。"

    return {
        "领域": 领域,
        "积木库根": str(base),
        "目标目录": str(dest_root),
        "包名": 包名,
        "导入前缀": 导入前缀,
        "包目录": str(dest_dir),
        "已装数量": len(已装),
        "跳过数量": len(跳过),
        "文件列表": 已装,
        "跳过": 跳过,
        "模块名映射": {b["名称"]: b["安装名"] for b in 已装},
        "package_toml": str(toml_path),
        "清单": str(manifest_path),
        "导入示例": 导入示例,
    }


# ---------------------------------------------------------------------------
# 反向：光明项目 → 积木候选（降级实现，不写回积木库）
# ---------------------------------------------------------------------------

def _已知积木名(base: Path) -> set:
    """廉价收集积木库里已有积木的名字骨骼（只列目录，不读文件内容）。

    publish 只用它做「重名冲突」提示，因此文件名级别足够；逐文件读 14222 份
    源码去抽导出名会让一次 publish 慢到几十秒，不值当。
    """
    names = set()
    for _tag, tree in [(SRC_BLOCKS, base / BLOCKS_DIR_NAME), (SRC_ROOT, base)]:
        if not tree.is_dir():
            continue
        try:
            domains = os.listdir(tree)
        except OSError:
            continue
        for d in domains:
            if d.startswith(".") or d.startswith("blocks") or d == "__pycache__":
                continue
            dd = tree / d
            if not dd.is_dir():
                continue
            try:
                for f in os.listdir(dd):
                    if f.endswith(".light"):
                        names.add(f[: -len(".light")])
                        names.add(safe_module_name(f[: -len(".light")]))
            except OSError:
                continue
    return names


def _extract_paragraph(text: str, name: str) -> Optional[str]:
    """抽取 `段落 <name> ...` 起至该段落结束（含缩进还原）的源码。"""
    lines = text.splitlines()
    start = None
    indent = 0
    pat = re.compile(rf"^([ \t]*)段落[ \t]+{re.escape(name)}[ \t]*(?:接收|\()")
    for i, line in enumerate(lines):
        m = pat.match(line)
        if m:
            start = i
            indent = len(m.group(1).expandtabs(4))
            break
    if start is None:
        pat2 = re.compile(rf"^([ \t]*)(?:段落|段)?[ \t]*{re.escape(name)}[ \t]*[（(]")
        for i, line in enumerate(lines):
            m = pat2.match(line)
            if m:
                start = i
                indent = len(m.group(1).expandtabs(4))
                break
    if start is None:
        return None

    body = [lines[start]]
    for line in lines[start + 1:]:
        if line.strip():
            cur = len(line) - len(line.lstrip(" \t"))
            cur = len(line[:cur].expandtabs(4))
            if cur <= indent:
                break
        body.append(line)
    # 缩进统一到 4 空格
    first_body_indent = None
    for line in body[1:]:
        if line.strip():
            lead = len(line) - len(line.lstrip(" \t"))
            first_body_indent = len(line[:lead].expandtabs(4))
            break
    if first_body_indent is None or first_body_indent < 4:
        shift = 4 - (first_body_indent or 0)
        norm = [body[0]]
        for line in body[1:]:
            norm.append((" " * shift + line) if shift > 0 and line.strip() else line)
        body = norm
    return "\n".join(body)


def publish_to_blocks(项目路径: os.PathLike | str,
                      积木名: Optional[str | Iterable[str]] = None,
                      目标目录: Optional[os.PathLike | str] = None,
                      落地: bool = False,
                      root: Optional[os.PathLike | str] = None) -> Dict[str, Any]:
    """把光明项目里的段落导出成「积木候选」（反向通道，**降级实现**）。

    降级说明（R137 B 线如实登记）：
      积木库仓库在本轮是**只读**资产，且其归档格式由积木库 owner 定，
      因此本函数**不写回 lighting**。它做的是：
        1) 扫描项目里的导出段落，产出符合积木头文件约定的候选内容；
        2) 与现有积木比对，标出重名冲突；
        3) `落地=True` 时把候选写到**项目自己**的输出目录（默认 `<项目>/导出积木/`），
           供人工/流水线 review 后再由 owner 合入积木库。
      若显式要求输出到积木库根之内，一律拒绝并给出原因，绝不静默写入。

    Args:
        项目路径: 光明项目根目录。
        积木名: 只导出这些名字；None 表示全部。
        目标目录: 输出目录；None → `<项目路径>/导出积木`。
        落地: 默认 False（先出计划，人工确认后再置 True 落盘）。

    Returns:
        dict：状态 / 原因 / 项目路径 / 输出目录 / 候选列表 / 文件列表 / 备注。
    """
    project = Path(项目路径)
    if not project.is_dir():
        raise FileNotFoundError(f"项目路径不存在: {project}")

    want = None
    if 积木名 is not None:
        want = {积木名} if isinstance(积木名, str) else set(map(str, 积木名))

    out_dir = Path(目标目录) if 目标目录 else project / "导出积木"

    # 红线：拒绝写进积木库
    lighting_root = None
    try:
        lighting_root = resolve_root(root)
    except BlocksRootMissing:
        lighting_root = None
    if lighting_root is not None:
        lp = os.path.normcase(os.path.realpath(str(lighting_root)))
        op = os.path.normcase(os.path.realpath(str(out_dir)))
        if op == lp or op.startswith(lp + os.sep):
            return {
                "状态": "拒绝",
                "原因": f"输出目录位于只读的积木库之内（{lighting_root}），拒绝写入。"
                        f"请把 目标目录 指到项目自己的目录，再人工合入积木库。",
                "项目路径": str(project),
                "输出目录": str(out_dir),
                "候选": [],
                "文件": [],
                "备注": "publish_to_blocks 降级：本轮不自动写回积木库。",
            }

    已有 = _已知积木名(lighting_root) if lighting_root is not None else set()

    候选: List[Dict[str, Any]] = []
    for src in sorted(project.rglob("*.light")):
        try:
            rel_in_proj = os.path.relpath(src, project)
            if rel_in_proj.startswith("导出积木") or rel_in_proj.startswith(".."):
                continue
            text = src.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for exp in read_exports(text):
            if want is not None and exp not in want:
                continue
            body = _extract_paragraph(text, exp)
            if not body:
                continue
            候选.append({
                "名称": exp,
                "模块名": safe_module_name(exp),
                "来源文件": str(src),
                "相对项目": rel_in_proj.replace("\\", "/"),
                "重名冲突": exp in 已有,
                "正文": body,
            })

    文件: List[str] = []
    if 落地 and 候选:
        out_dir.mkdir(parents=True, exist_ok=True)
        for c in 候选:
            target = out_dir / (c["模块名"] + ".light")
            content = (
                f"# 积木：{c['名称']}（自项目反向导出，待 review）\n"
                f"# 契约：由 {c['相对项目']} 导出，输入/输出契约待人工补全\n"
                f"导出 {c['名称']}\n"
                f"{c['正文']}\n"
            )
            target.write_text(content, encoding="utf-8")
            文件.append(str(target))

    return {
        "状态": "已落地" if (落地 and 候选) else ("dry-run" if 候选 else "无候选"),
        "原因": "",
        "项目路径": str(project),
        "输出目录": str(out_dir),
        "候选": 候选,
        "文件": 文件,
        "备注": "publish_to_blocks 降级：本轮不自动写回积木库，只产出候选与暂存文件。",
    }
