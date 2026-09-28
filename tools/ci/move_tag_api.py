# -*- coding: utf-8 -*-
"""github.com git 协议被代理拦截时，用 GitHub API 把本地 tag 原样搬到远端（只动 ref，不造提交）。

## 场景（R99 §4.4 实锤并验证有效）

- 与 `push_via_api.py` 同一类兜底：本机 `git push --tags` 推 github.com 被本地代理拦截，
  但 `api.github.com` 恒通。
- 本脚本用 Git Data API **只重建 tag ref**，不改动任何提交；远端 tag 指向的 commit 对象
  须已存在于远端（通常先用 `push_via_api.py` 把 commit 推上去）。

## 用法

    python tools/ci/move_tag_api.py <tag名>

## 路径约定

脚本随仓库走，靠文件位置向上定位仓库根与本仓 `.env`，**不写死任何本机用户名绝对路径**
（R100 路A 提升进 `tools/ci/` 时清掉）。要推其它仓，改 `REPO` 常量即可。
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# tools/ci/move_tag_api.py -> tools -> 仓库根（light-merge 自身即 git 仓库）
_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parent.parent
LM = REPO_ROOT
API = "https://api.github.com"
REPO = "skywalk163/light"  # 本脚本随 light-merge 仓走；推其它仓改这里即可


def load_token() -> str:
    """优先取环境变量 GITHUB_TOKEN，否则从仓库根向上的 .env 里找 GITHUB_TOKEN。"""
    env_tok = os.environ.get("GITHUB_TOKEN")
    if env_tok:
        return env_tok
    d = _HERE
    for _ in range(4):
        cand = d / ".env"
        if cand.is_file():
            for ln in cand.read_text(encoding="utf-8", errors="ignore").splitlines():
                if ln.startswith("GITHUB_TOKEN"):
                    return ln.split("=", 1)[1].strip().strip('"').strip("'")
        d = d.parent
    raise SystemExit("未找到 GITHUB_TOKEN（请在环境变量或仓库根向上的 .env 中提供）")


TOKEN = load_token()


def git(*args):
    return subprocess.run(["git", *args], cwd=str(LM), capture_output=True,
                          text=True, encoding="utf-8", errors="ignore").stdout.strip()


def api(method, path, data=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Authorization", "token " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, body) as r:
            txt = r.read().decode("utf-8")
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        print(f"  HTTPError {e.code} {method} {path}: {e.read()[:200]!r}")
        raise


def iso_from_git_ts(ts: str) -> str:
    unix, off = ts.split()
    sign = 1 if off.startswith("+") else -1
    tz = timezone(sign * timedelta(hours=int(off[1:3]), minutes=int(off[3:5])))
    return datetime.fromtimestamp(int(unix), tz).isoformat()


tag = sys.argv[1]
raw = git("cat-file", "-p", tag)
lines = raw.splitlines()
obj = lines[0].split()[1]
tname = lines[2].split(" ", 1)[1]
tagger_line = next(l for l in lines if l.startswith("tagger "))
rest = tagger_line[len("tagger "):]
tmail = rest[rest.index("<") + 1:rest.index(">")]
tname_ = rest[:rest.index("<")].strip()
ts = rest[rest.index(">") + 1:].strip()
tmsg = raw.split("\n\n", 1)[1] if "\n\n" in raw else ""

print(f"[1] 本地 tag {tag}: object={obj[:8]} tagger={tname_} <{tmail}> {ts}")

remote_main = api("GET", f"/repos/{REPO}/git/ref/heads/main")["object"]["sha"]
print(f"[2] 远端 main = {remote_main[:8]}（本地 tag 目标 {obj[:8]}）{'✅一致' if remote_main == obj else '⚠️不一致'}")

try:
    old = api("GET", f"/repos/{REPO}/git/ref/tags/{tag}")
    print(f"[3] 远端旧 tag → {old['object']['sha'][:8]}")
    api("DELETE", f"/repos/{REPO}/git/refs/tags/{tag}")
    print("    已删除旧 tag ref")
except Exception as e:
    print(f"    旧 tag 不存在或删除失败：{type(e).__name__}")

tres = api("POST", f"/repos/{REPO}/git/tags", {
    "tag": tname, "message": tmsg, "object": obj, "type": "commit",
    "tagger": {"name": tname_, "email": tmail, "date": iso_from_git_ts(ts)},
})
print(f"[4] 建 tag 对象 → {tres['sha'][:8]}")
api("POST", f"/repos/{REPO}/git/refs", {"ref": f"refs/tags/{tag}", "sha": tres["sha"]})
print(f"[5] tag ref 已建：refs/tags/{tag}")

r = api("GET", f"/repos/{REPO}/git/ref/tags/{tag}")
print(f"[6] 核验：{tag} → {r['object']['sha'][:8]} (type={r['object']['type']})")
