# -*- coding: utf-8 -*-
"""L4 发布管线 · 本地就绪核查（只读，不发布）

检查「发布 lightgm 到 PyPI / 发布 VS Code 扩展到 Marketplace」在**本地仓库侧**的就绪项，
输出就绪清单（✅/❌/⚠️）。GitHub 侧密钥（PYPI_API_TOKEN / VSCE_PAT）需用户在 GH UI 配置，
本脚本无法读取，列为「需人工确认」项。

用法：
    python scripts/release_preflight.py
    python scripts/release_preflight.py --json      # 机器可读

不依赖任何第三方库（仅标准库）。绝不执行任何 push / publish。
"""
import os
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # light-merge/


def _read(path, mode="r", enc="utf-8"):
    try:
        with open(path, mode, encoding=enc, errors="replace") as f:
            return f.read()
    except Exception:
        return None


def _exists(p):
    return os.path.exists(p)


def _norm_ver(v):
    """归一化版本号为可比较的 PEP 440 规范形。

    PyPI 用 PEP 440（0.4.0rc1，无连字符），VS Code Marketplace 用 SemVer
   （0.4.0-rc1，有连字符）——二者是同一发版的两种强制格式，必须归一后比较，
    否则 rc 发版会被误判为「版本不一致」。
    v0.4.0-rc1 → 0.4.0rc1；0.4.0a1 → 0.4.0a1；0.4.0b2 → 0.4.0b2。
    """
    if not v:
        return ""
    s = v.strip().lower()
    if s.startswith("v"):
        s = s[1:]
    s = s.replace("-rc", "rc").replace("-alpha", "a").replace("-beta", "b").replace("-pre", "rc")
    return s


def _toml_simple(path):
    """极简读取 pyproject [project] name/version（不引第三方 toml 解析）"""
    txt = _read(path)
    if txt is None:
        return None, None
    name = version = None
    in_project = False
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith("[project]"):
            in_project = True
            continue
        if s.startswith("[") and not s.startswith("[project]"):
            in_project = False
            continue
        if in_project:
            if s.startswith("name") and "=" in s and name is None:
                name = s.split("=", 1)[1].strip().strip('"').strip("'")
            if s.startswith("version") and "=" in s and version is None:
                version = s.split("=", 1)[1].strip().strip('"').strip("'")
    return name, version


def _pkg_json(path):
    import re
    txt = _read(path)
    if txt is None:
        return None
    out = {}
    for key in ("name", "version", "publisher", "displayName"):
        m = re.search(r'"%s"\s*:\s*"([^"]+)"' % key, txt)
        if m:
            out[key] = m.group(1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    checks = []  # (level, item, ok, detail)

    def add(level, item, ok, detail=""):
        checks.append((level, item, ok, detail))

    # --- 1. PyPI 包 manifest ---
    pname, pver = _toml_simple(os.path.join(ROOT, "pyproject.toml"))
    add("PyPI", "pyproject.toml 存在且 name=lightgm", pname == "lightgm",
        f"name={pname} version={pver}")
    # --- 2. VS Code 扩展 manifest ---
    pkg = _pkg_json(os.path.join(ROOT, "vscode-extension", "package.json"))
    ext_ok = bool(pkg and pkg.get("name"))
    add("VSCE", "vscode-extension/package.json 存在", ext_ok,
        f"name={pkg.get('name')} version={pkg.get('version')} publisher={pkg.get('publisher')}" if pkg else "缺失")

    # --- 3. 构建/发布脚本 ---
    add("通用", "build_exe.py 存在", _exists(os.path.join(ROOT, "build_exe.py")))
    add("PyPI", "scripts/build_release.py 存在", _exists(os.path.join(ROOT, "scripts", "build_release.py")))
    add("PyPI", "scripts/publish_pypi.py 存在（含 --check-only/--test）",
        _exists(os.path.join(ROOT, "scripts", "publish_pypi.py")))

    # --- 4. 工作流 ---
    add("PyPI", ".github/workflows/release.yml 存在",
        _exists(os.path.join(ROOT, ".github", "workflows", "release.yml")))
    add("VSCE", ".github/workflows/vsce-publish.yml 存在",
        _exists(os.path.join(ROOT, ".github", "workflows", "vsce-publish.yml")))

    # --- 5. 发布产物（需先 build）---
    dist = os.path.join(ROOT, "dist")
    if _exists(dist):
        arts = [f for f in os.listdir(dist) if f.endswith((".tar.gz", ".whl"))]
        add("PyPI", "dist/ 构建产物已生成", len(arts) > 0, f"{len(arts)} 个 (.whl/.tar.gz)")
    else:
        add("PyPI", "dist/ 构建产物已生成", False, "dist/ 不存在 → 需先 python scripts/build_release.py")

    # --- 6. CHANGELOG（release.yml 用它生成 Release 说明）---
    add("通用", "CHANGELOG.md 存在（Release 说明来源）", _exists(os.path.join(ROOT, "CHANGELOG.md")),
        "缺失则 Release 说明退化为单行")

    # --- 7. 版本对齐（关键）---
    if pver and pkg and pkg.get("version"):
        # 归一化比较：PyPI(PEP440, 0.4.0rc1) 与 VS Code(SemVer, 0.4.0-rc1)
        # 是同一发版的两种强制格式，须归一后判等，否则 rc 发版误报不一致。
        aligned = (_norm_ver(pver) == _norm_ver(pkg["version"]))
        add("关键", "pyproject 版本 == package.json 版本（归一后）", aligned,
            f"pyproject={pver} package.json={pkg['version']}（规范形均为 {_norm_ver(pver)}）")
        # 与 day2 锚点 v0.4.0-rc1 的关系（归一化判定）
        if _norm_ver(pver) != "0.4.0rc1":
            add("关键", "发布版本号已对齐 day2 锚点 v0.4.0-rc1（或已决定新号）", False,
                f"当前 pyproject={pver}；day2 锚点 v0.4.0-rc1 → 若直接推 v0.4.0-rc1，"
                "PyPI/VSCE 将用 pyproject 的 {pver}（疑似已发）→ 撞版本被拒。发布前必须统一版本号。".format(pver=pver))

    # --- 8. 工作流 action 版本钉死（关键）---
    rel = _read(os.path.join(ROOT, ".github", "workflows", "release.yml"))
    if rel:
        v7 = rel.count("@v7")
        add("关键", "release.yml 未钉死不存在的 actions/@v7", v7 == 0,
            f"检出 {v7} 处 @v7（checkout/upload-artifact/download-artifact/setup-python@v7 当前主流为 @v4）→ "
            "若 @v7 未发布，workflow 会失败。发布前需确认或改钉 @v4")

    # --- 9. GitHub 侧密钥（无法本地读，提示人工确认）---
    add("PyPI", "[人工] GH Environment `pypi` 已配 `PYPI_API_TOKEN`（或 lightgm 登记 trusted publisher）",
        None, "需在 GitHub 仓库 Settings → Environments → pypi → Secrets 配置")
    add("VSCE", "[人工] GH Repo Secrets 已配 `VSCE_PAT`", None,
        "Settings → Secrets and variables → Actions → VSCE_PAT（可选 OVSX_PAT）")
    add("通用", "[人工] 已决定并打发布 tag（vX.Y.Z，触发 release.yml + vsce-publish.yml）", None,
        "建议先发 TestPyPI / prerelease 验证链路，再正式发版")

    # --- 输出 ---
    levels = {"PyPI": "PyPI(lightgm)", "VSCE": "VSCE(扩展)", "通用": "通用", "关键": "关键"}
    order = ["关键", "PyPI", "VSCE", "通用"]
    checks.sort(key=lambda c: order.index(c[0]) if c[0] in order else 99)
    sym = {True: "✅", False: "❌", None: "⚠️"}
    if args.json:
        out = [{"area": levels.get(c[0], c[0]), "item": c[1], "state": c[2], "detail": c[3]} for c in checks]
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("=" * 72)
        print("  L4 发布管线 · 本地就绪核查（只读，不发布）")
        print("=" * 72)
        cur = None
        for lvl, item, ok, detail in checks:
            area = levels.get(lvl, lvl)
            if area != cur:
                cur = area
                print(f"\n## {area}")
            print(f"  {sym[ok]} {item}")
            if detail:
                print(f"        ↳ {detail}")
        print("\n" + "=" * 72)
        n_ok = sum(1 for c in checks if c[2] is True)
        n_no = sum(1 for c in checks if c[2] is False)
        n_manual = sum(1 for c in checks if c[2] is None)
        print(f"  本地可核查: ✅{n_ok} ❌{n_no} ｜ 需人工确认(GH侧): ⚠️{n_manual}")
        print("  下一步：补齐 ❌ 项 + 在 GH UI 配置 ⚠️ 项后，按 Day11_发布管线.md 执行发布。")
        print("=" * 72)


if __name__ == "__main__":
    main()
