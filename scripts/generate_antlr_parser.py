#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 —— ANTLR4 生成产物一键重建脚本（R75-C）

背景（为什么需要这个脚本）
------------------------------------------------------------
`antlrparser/` 里原本只有两个 .g4 语法文件，**没有** ANTLR 生成的
`LightLangLexer.py` / `LightLangParser.py` / `LightLangParserVisitor.py`。
缺了它们，unified 腿（`cli/light_unified.py --backend antlr`）在导入阶段就
`ModuleNotFoundError: No module named 'LightLangLexer'`，本机与 0.82 都跑不了，
于是所有 unified 改动只能靠「手工构造 AST 节点」做等价验证 —— 这正是 R74 续
在 unified 上漏掉一处 `排序` 语义分叉的盲区成因。

旧脚本 `scripts/generate_parser.py` 不可用：它直接调裸命令 `antlr4`（依赖
`pip install antlr4-tools` 且要联网拉 JDK），并引用了一个不存在的
`LightLang.g4`。本脚本改为：**自己保证工具链**（本机 java → 否则自动下载
Temurin JRE + ANTLR complete jar）+ 只生成现存的两个 .g4。

工具链开销
------------------------------------------------------------
- 首选 PATH 上的 `java`（>= 11）。找不到才下载 Temurin JRE 17（约 43MB）。
- ANTLR jar 从 maven 镜像拉 `antlr-4.13.2-complete.jar`（约 2.1MB）。
  **版本必须与 `antlr4-python3-runtime` 一致**（本仓库 venv 里是 4.13.2），
  否则生成产物与运行时不兼容。
- 工具缓存目录（默认系统临时目录，可用环境变量覆盖）：
    ANTLR4_TOOLS_DIR=<dir>   # 默认 <temp>/light-antlr-tools
  缓存命中时不重复下载。

用法
------------------------------------------------------------
    # 建议用仓库自带解释器
    G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe \
        scripts/generate_antlr_parser.py

    python scripts/generate_antlr_parser.py --check     # 只体检工具链与产物
    python scripts/generate_antlr_parser.py --verify    # 生成后跑导入链自检

产物（全部落在 antlrparser/light_parser/，已由 .gitignore 开例外入库）
------------------------------------------------------------
    LightLangLexer.py / LightLangLexer.tokens / LightLangLexer.interp
    LightLangParser.py / LightLangParser.tokens / LightLangParser.interp
    LightLangParserVisitor.py
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------- 常量
ANTLR_VERSION = "4.13.2"  # 必须与 antlr4-python3-runtime 版本一致
ANTLR_JAR_NAME = f"antlr4-{ANTLR_VERSION}-complete.jar"
ANTLR_JAR_URLS = [
    # 国内镜像优先（repo1.maven.org 在部分网络下不可达）
    f"https://maven.aliyun.com/repository/public/org/antlr/antlr4/{ANTLR_VERSION}/{ANTLR_JAR_NAME}",
    f"https://mirrors.cloud.tencent.com/nexus/repository/maven-public/org/antlr/antlr4/{ANTLR_VERSION}/{ANTLR_JAR_NAME}",
    f"https://repo1.maven.org/maven2/org/antlr/antlr4/{ANTLR_VERSION}/{ANTLR_JAR_NAME}",
]
JRE_MAJOR = "17"
ADOPTIUM_URL = (
    "https://api.adoptium.net/v3/binary/latest/{maj}/ga/{os}/x64/jre/"
    "hotspot/normal/eclipse"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ANTLR_DIR = REPO_ROOT / "antlrparser"
OUT_DIR = ANTLR_DIR / "light_parser"  # 与 light_visitor.py 期望的路径一致

LEXER_G4 = "LightLangLexer.g4"
PARSER_G4 = "LightLangParser.g4"
EXPECTED_OUT = [
    "LightLangLexer.py",
    "LightLangLexer.tokens",
    "LightLangLexer.interp",
    "LightLangParser.py",
    "LightLangParser.tokens",
    "LightLangParser.interp",
    "LightLangParserVisitor.py",
]


# ---------------------------------------------------------------- 工具
def log(msg: str) -> None:
    print(msg, flush=True)


def tools_dir() -> Path:
    d = os.environ.get("ANTLR4_TOOLS_DIR") or os.path.join(
        tempfile.gettempdir(), "light-antlr-tools"
    )
    p = Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p


def download(url: str, dest: Path) -> None:
    log(f"  下载 {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "light-antlr-bootstrap"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as fh:
        shutil.copyfileobj(resp, fh)
    log(f"  已保存 {dest} ({dest.stat().st_size} 字节)")


def find_java() -> str | None:
    """优先 JAVA_HOME，其次 PATH 上的 java。"""
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        cand = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if cand.exists():
            return str(cand)
    exe = shutil.which("java")
    if exe:
        return exe
    return None


def ensure_java() -> str:
    """返回可用的 java 可执行文件路径；没有就下载一个便携 JRE。"""
    java = find_java()
    if java:
        try:
            out = subprocess.run(
                [java, "-version"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=60,
            )
            ver_line = (out.stderr or out.stdout).splitlines()[0] if (out.stderr or out.stdout) else ""
            log(f"✓ 使用系统 java: {java}")
            log(f"  {ver_line.strip()}")
            return java
        except Exception as exc:  # noqa: BLE001
            log(f"! 系统 java 不可用（{exc}），改用便携 JRE")

    cache = tools_dir() / f"jre{JRE_MAJOR}"
    exe = cache / ("bin/java.exe" if os.name == "nt" else "bin/java")
    if not exe.exists():
        sysname = {"nt": "windows", "posix": "linux"}.get(
            os.name, platform.system().lower()
        )
        if platform.system() == "Darwin":
            sysname = "mac"
        dest = tools_dir() / f"jre{JRE_MAJOR}.zip"
        download(ADOPTIUM_URL.format(maj=JRE_MAJOR, os=sysname), dest)
        log(f"  解压到 {cache}")
        cache.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest) as zf:
            zf.extractall(cache)
        # Adoptium 包内还有一层 jdk-x.y.z-jre/
        nested = [p for p in cache.iterdir() if p.is_dir()]
        if nested:
            src = nested[0]
            exe = src / ("bin/java.exe" if os.name == "nt" else "bin/java")
        if not exe.exists():
            raise SystemExit(f"[错误] 便携 JRE 解压后找不到 java: {exe}")
    log(f"✓ 使用便携 JRE: {exe}")
    return str(exe)


def ensure_jar() -> Path:
    jar = tools_dir() / ANTLR_JAR_NAME
    if jar.exists() and jar.stat().st_size > 1_000_000:
        log(f"✓ 使用缓存 jar: {jar}")
        return jar
    last_err = None
    for url in ANTLR_JAR_URLS:
        try:
            download(url, jar)
            if jar.stat().st_size > 1_000_000:
                return jar
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            log(f"  ! 该源失败: {exc}")
    raise SystemExit(f"[错误] ANTLR jar 全部下载源失败，最后一个错误: {last_err}")


def check_runtime_version() -> None:
    """提示生成版本与 antlr4-python3-runtime 版本必须一致。"""
    try:
        from antlr4 import __version__ as rt_ver  # type: ignore
    except Exception:  # noqa: BLE001
        rt_ver = None
    if rt_ver and not str(rt_ver).startswith(ANTLR_VERSION):
        log(f"⚠ 版本不匹配：生成用 ANTLR {ANTLR_VERSION}，"
            f"运行期 antlr4-python3-runtime {rt_ver}")
    elif rt_ver:
        log(f"✓ 运行期 antlr4-python3-runtime {rt_ver} 与生成版本一致")


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- 主流程
def run_antlr(java: str, jar: Path, g4: str, extra: list[str]) -> None:
    # ⚠️ -encoding UTF-8 必须显式指定：ANTLR 工具默认用 JVM 平台编码读 .g4，
    #    中文 Windows 上是 GBK，会把 UTF-8 的中文关键字读成乱码码点并烤进生成产物的
    #    literalNames（R76-A 根因①：错误消息出现 '缁撴潫' 即此成因）。
    cmd = [java, "-jar", str(jar), "-Dlanguage=Python3", "-visitor",
           "-no-listener", "-encoding", "UTF-8",
           "-o", OUT_DIR.name] + extra + [g4]
    log("  $ " + " ".join(cmd))
    # ⚠️ Java 的告警文本沿用平台编码（中文 Windows 上是 GBK），必须 errors="replace"，
    #    否则 subprocess 的读取线程会抛 UnicodeDecodeError 并污染输出。
    out = subprocess.run(cmd, cwd=str(ANTLR_DIR), capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    warnings = [ln for ln in (out.stderr or "").splitlines() if "warning(" in ln]
    if warnings:
        log(f"  ANTLR 告警 {len(warnings)} 条（语法层面的 token 不可达，历史遗留，不阻塞生成）")
    if out.returncode != 0:
        log(out.stdout or "")
        log(out.stderr or "")
        raise SystemExit(f"[错误] ANTLR 生成失败（{g4}），退出码 {out.returncode}")
    log(f"  ✓ {g4} 生成完成")


def generate() -> None:
    log(f"仓库根：{REPO_ROOT}")
    log(f"产物目录：{OUT_DIR}")
    check_runtime_version()
    java = ensure_java()
    jar = ensure_jar()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    log("\n[1/2] 生成词法分析器")
    run_antlr(java, jar, LEXER_G4, [])
    log("\n[2/2] 生成语法分析器（-lib 指向词法器产物所在目录，供 tokenVocab 使用）")
    run_antlr(java, jar, PARSER_G4, ["-lib", OUT_DIR.name])

    log("\n产物清单：")
    missing = []
    for name in EXPECTED_OUT:
        p = OUT_DIR / name
        if p.exists():
            log(f"  {md5(p)}  {name:<28} {p.stat().st_size:>8} 字节")
        else:
            missing.append(name)
            log(f"  [缺失] {name}")
    if missing:
        raise SystemExit(f"[错误] 产物不完整，缺: {missing}")
    log("\n✓ 生成完毕。可跑 --verify 做导入链自检。")


def verify() -> int:
    """导入链自检：模拟 cli/light_unified.py::_check_antlr 的导入顺序。"""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    sys.path.insert(0, str(ANTLR_DIR))
    sys.path.insert(0, str(OUT_DIR))
    try:
        from antlr4 import CommonTokenStream, InputStream  # noqa: F401
        from LightLangLexer import LightLangLexer  # noqa: F401
        from LightLangParser import LightLangParser  # noqa: F401
        from LightLangParserVisitor import LightLangParserVisitor  # noqa: F401
        from light_visitor import LightLangASTBuilder  # noqa: F401
        from code_generator_unified import UnifiedCodeGenerator  # noqa: F401
    except ImportError as exc:
        log(f"✗ 导入链自检失败: {exc}")
        return 1
    log("✓ 导入链自检通过（LightLangLexer/Parser/Visitor + light_visitor + unified codegen）")

    # 拿一段最小 v1 语法做真实解析（v3 缩进语法在本腿另有预处理缺口，不在此断言）
    from light_visitor import LightParser

    src = '设 甲 为 1。\n打印(甲)。\n'
    p = LightParser()
    mod = p.parse(src)
    if mod is None or p.errors:
        log("✗ 最小用例解析失败:")
        for e in list(p.errors)[:3]:
            log(f"    {e}")
        return 1
    log("✓ 最小用例 `设 甲 为 1。打印(甲)。` 解析通过")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="重建 antlrparser/light_parser 生成产物")
    ap.add_argument("--check", action="store_true", help="只体检：工具链 + 产物是否齐")
    ap.add_argument("--verify", action="store_true", help="生成后跑导入链自检")
    args = ap.parse_args()

    if args.check:
        log(f"java: {find_java() or '（未找到，需下载便携 JRE）'}")
        log(f"jar : {tools_dir() / ANTLR_JAR_NAME} "
            f"({'存在' if (tools_dir() / ANTLR_JAR_NAME).exists() else '缺失'})")
        miss = [n for n in EXPECTED_OUT if not (OUT_DIR / n).exists()]
        log(f"产物: {'齐全' if not miss else '缺 ' + str(miss)}")
        return 0 if not miss else 1

    generate()
    if args.verify:
        log("")
        return verify()
    return 0


if __name__ == "__main__":
    sys.exit(main())
