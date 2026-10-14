#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R148-D 凭证防泄露扫描器（仓内 tracked 工具，CI / pre-push / 各线自查复用）。

来源：把 R147 在 _r140b_remote82.py 做好的「打包前哨兵」提升为独立、可复用的 tracked 工具。
R147 收口时主 agent 实测发现：`.env`（含 GITHUB_TOKEN / SSH_PASS_* / TWINE_PASSWORD）虽被
.gitignore 覆盖、从未进 commit，但曾随全树上传落入 0.82 远端树——根因是上传包排除清单漏了 `.env`。
本工具把「命中即中止（绝不回显密钥本体）」的纪律固化为可被多处调用的真门。

支持四种扫描模式（互斥，默认 --root 当前目录）：
  --root DIR      扫描目录树（打包前 / 本地仓库全树核查）
  --staged        扫描 git 暂存区（pre-commit 用）
  --history       扫描 git 全历史（已推送面核查）
  --pre-push      读 pre-push 标准输入，扫描本次推送的提交范围（真门，推荐接 pre-push hook）

命中任一密钥形态即退出码 1 并报告（只报 文件:行:形态名，**绝不回显密钥本体**）。
私钥块标题在源文件里可能是占位符（如 stdlib/lightpub/证书.py 的假证书）：要求伴随
≥60 字符 base64 连续行才判真密钥，避免占位 PEM 误伤。

安全纪律（最高优先级）：报告 / 日志 / 测试输出一律不出现凭证值；确需证明只写键名 + 长度。
"""
import os
import re
import sys
import subprocess

# ── 密钥形态清单（name 仅用于报告，绝不回显匹配到的密钥本体）──
# req_b64=True 表示：除标题外还需同文件出现 ≥60 字符 base64 连续行才判真密钥。
SECRET_PATTERNS = [
    ("GITHUB_TOKEN(ghp_)", re.compile(r"ghp_[A-Za-z0-9]{20,}"), False),
    ("GITHUB_PAT", re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), False),
    ("GITHUB_OAUTH(gho_)", re.compile(r"gho_[A-Za-z0-9]{20,}"), False),
    ("OPENAI_SK", re.compile(r"sk-[A-Za-z0-9]{24,}"), False),
    ("AWS_ACCESS_KEY_ID(AKIA)", re.compile(r"AKIA[0-9A-Z]{16}"), False),
    ("PRIVATE_KEY_BLOCK", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), True),
]
LONG_B64 = re.compile(r"^[A-Za-z0-9+/]{60,}={0,2}$")

# 与 _r140b_remote82.py 保持一致的排除口径（凭证文件 / 二进制 / 体积 / 敏感目录）。
EXC_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".light_cache",
    ".pytest_basetemp", "_archive", "node_modules", "dist",
    ".mypy_cache", ".ruff_cache", ".workbuddy", ".vscode",
    ".scratch", ".box-agent", ".box-agent-scratch", ".dumate", ".opencode",
    "demo_video", "第三轮留档", "第四轮留档", "vscode-light-archive",
    "_venv_ciperf", "logs", "r127a_logs", "P0-2_verify",
}
EXC_FILES = {
    ".coverage", "pip-wheel-metadata",
    ".env", ".env.local", ".env.*.local",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    ".netrc", ".pgpass", ".htpasswd",
}
EXC_FILE_SUFFIXES = (".key", ".pem", ".p12", ".pfx", ".jks", ".keystore")
EXC_EXTS = (
    ".exe", ".o", ".obj", ".pdb", ".dll", ".so", ".a", ".lib",
    ".mp4", ".zip", ".whl", ".tgz", ".gz", ".png", ".jpg", ".jpeg",
    ".ico", ".pdf", ".pyc", ".log",
)
MAX_FILE_BYTES = 2 * 1024 * 1024


def _excluded_by_path(path):
    """路径级排除：敏感文件名 / 后缀 / 任一目录分量在排除清单内。"""
    norm = path.replace("\\", "/")
    parts = norm.split("/")
    base = parts[-1]
    if base in EXC_FILES or base.lower() in EXC_FILES:
        return True
    if base.lower().endswith(EXC_FILE_SUFFIXES):
        return True
    if any(p in EXC_DIRS for p in parts):
        return True
    return False


def scan_text(text):
    """对单段文本做精确扫描，返回命中形态名列表（不含密钥本体）。

    私钥块形态在源文件可能是占位符：要求同文本出现 ≥60 字符 base64 连续行才判真密钥。
    """
    hits = []
    for name, pat, req_b64 in SECRET_PATTERNS:
        if pat.search(text):
            if req_b64 and not any(LONG_B64.match(ln) for ln in text.splitlines()):
                continue
            hits.append(name)
    return hits


def _find_lineno(text, pat):
    """定位首个命中行号（只为报告，不返回该行内容）。"""
    for i, ln in enumerate(text.splitlines(), 1):
        if pat.search(ln):
            return i
    return 0


def _scan_file_content(path):
    """读文件（≤2MiB、UTF-8 文本）做扫描，路径被排除或不可读则返回空。"""
    if _excluded_by_path(path):
        return []
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return []
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return []
    return scan_text(text)


def scan_root(root):
    """--root 模式：遍历目录树扫描文本文件。"""
    hits = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXC_DIRS]
        for fn in files:
            p = os.path.join(dirpath, fn)
            for name in _scan_file_content(p):
                rel = os.path.relpath(p, root)
                hits.append((rel, _find_lineno(_read_text(p), SECRET_PATTERNS_DICT().get(name) or _any_pat()), name))
    return hits


def _read_text(path):
    try:
        with open(path, "rb") as fh:
            return fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _any_pat():
    return SECRET_PATTERNS[0][1]


def SECRET_PATTERNS_DICT():
    return {name: pat for name, pat, _ in SECRET_PATTERNS}


def _git(repo, args, text=True):
    try:
        return subprocess.run(["git", "-C", repo] + args,
                               capture_output=True, text=text)
    except (OSError, subprocess.SubprocessError):
        return None


def scan_staged(repo):
    """--staged 模式：扫描 git 暂存区（index）文件内容。"""
    hits = []
    res = _git(repo, ["diff", "--cached", "--name-only"])
    if not res or res.returncode != 0:
        return hits
    for path in res.stdout.splitlines():
        if _excluded_by_path(path):
            continue
        blob = _git(repo, ["show", ":" + path])
        if not blob or blob.returncode != 0:
            continue
        for name in scan_text(blob.stdout):
            hits.append((path, _find_lineno(blob.stdout, SECRET_PATTERNS_DICT()[name]), name))
    return hits


def scan_history(repo):
    """--history 模式：扫描 git 全历史（所有可达 commit 的 blob）。"""
    hits = []
    revs = _git(repo, ["rev-list", "--all"])
    if not revs or revs.returncode != 0 or not revs.stdout.strip():
        return hits
    refspec = revs.stdout.split()
    for name, pat, _ in SECRET_PATTERNS:
        gres = _git(repo, ["grep", "-I", "-n", "-E", pat.pattern] + refspec)
        if not gres or gres.returncode != 0:
            continue
        for line in gres.stdout.splitlines():
            parts = line.split(":", 3)
            if len(parts) < 2:
                continue
            commit, path = parts[0], parts[1]
            if _excluded_by_path(path):
                continue
            show = _git(repo, ["show", "%s:%s" % (commit, path)])
            if not show or show.returncode != 0:
                continue
            # 用精确扫描复核（应用 long_b64 规则、且不回显内容）
            sub = scan_text(show.stdout)
            if name in sub:
                hits.append(("%s:%s" % (commit, path),
                             _find_lineno(show.stdout, pat), name))
    return hits


def scan_pre_push(repo):
    """--pre-push 模式：读 pre-push 标准输入，扫描本次推送的提交范围。

    git 每行给：<local-ref> <local-oid> <remote-ref> <remote-oid>。
    对每对，取 local_oid 与 remote_oid 之差的文件清单，扫描其 blob 内容。
    """
    hits = []
    # git 空树 oid：新建分支（remote_oid 全 0）时，以此为基线才能列出本次提交的全部文件。
    EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    for raw in sys.stdin:
        parts = raw.split()
        if len(parts) < 4:
            continue
        local_oid, remote_oid = parts[1], parts[3]
        base = remote_oid if set(remote_oid) != {"0"} else EMPTY_TREE
        cmd = ["diff", "--name-only", base, local_oid]
        res = _git(repo, cmd)
        if not res or res.returncode != 0:
            continue
        for path in res.stdout.splitlines():
            if _excluded_by_path(path):
                continue
            show = _git(repo, ["show", "%s:%s" % (local_oid, path)])
            if not show or show.returncode != 0:
                continue
            for name in scan_text(show.stdout):
                hits.append((path, _find_lineno(show.stdout, SECRET_PATTERNS_DICT()[name]), name))
    return hits


def _report(hits, mode):
    if not hits:
        print("[secret_prescan] 模式=%s 干净：未检出密钥形态。" % mode)
        return 0
    print("[secret_prescan] 模式=%s 检出 %d 处密钥形态（密钥本体已脱敏，只报 文件:行:形态）："
          % (mode, len(hits)))
    for loc, lineno, name in hits[:50]:
        print("  %s:%d [%s]" % (loc, lineno, name))
    if len(hits) > 50:
        print("  ... 其余 %d 处省略" % (len(hits) - 50))
    print("[secret_prescan] 处置：从待提交/待推送内容移除真实凭证"
          "（改用 .env + gitignore，.env 已被排除清单覆盖），再重试。")
    return 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = "."
    mode = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--root":
            mode = "root"
            repo = argv[i + 1] if i + 1 < len(argv) else "."
            i += 2
        elif a == "--staged":
            mode = "staged"
            i += 1
        elif a == "--history":
            mode = "history"
            i += 1
        elif a == "--pre-push":
            mode = "pre-push"
            i += 1
        elif a in ("-C", "--repo"):
            repo = argv[i + 1]
            i += 2
        else:
            i += 1
    if mode is None:
        mode = "root"
    if mode == "root":
        hits = scan_root(repo)
    elif mode == "staged":
        hits = scan_staged(repo)
    elif mode == "history":
        hits = scan_history(repo)
    elif mode == "pre-push":
        hits = scan_pre_push(repo)
    else:
        print("未知模式: %s" % mode, file=sys.stderr)
        return 2
    return _report(hits, mode)


if __name__ == "__main__":
    raise SystemExit(main())
