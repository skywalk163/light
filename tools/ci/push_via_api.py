# -*- coding: utf-8 -*-
"""github.com git 协议被本地代理拦截、但 api.github.com 可达时的应急推送。

## 场景（R99 §4.4 实锤并验证有效）

- 本机 `git push github` 常被本地代理拦截（`CONNECT tunnel 502` / `Empty reply` /
  schannel 握手失败），但 `api.github.com` 恒通。
- 本脚本用 GitHub **Git Data API** 把本地提交原样复刻到远端 `main`：以远端 `main`
  的 tree 为基准重建 tree/commit，规避本地 CRLF blob 与远端 LF blob 造成的 SHA 分叉。
  等价于快进，但**不强推、不 `merge -s ours`**。
- 之后远端 SHA 可能与本地不同（CRLF 平行历史），但内容等价。核验请走
  `git ls-remote <r> refs/heads/main`，**不要**信 `git push` 的退出码（tail 管道会吞码）。

## 用法

    python tools/ci/push_via_api.py <本地commit> [tag名]

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

# tools/ci/push_via_api.py -> tools -> 仓库根（light-merge 自身即 git 仓库）
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
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  HTTPError {e.code} {method} {path}: {e.read()[:300]!r}")
        raise


def iso_from_git_ts(ts: str) -> str:
    """git 原始 '1758800000 +0800' → ISO 8601"""
    unix, off = ts.split()
    sign = 1 if off.startswith("+") else -1
    hh, mm = int(off[1:3]), int(off[3:5])
    tz = timezone(sign * timedelta(hours=hh, minutes=mm))
    return datetime.fromtimestamp(int(unix), tz).isoformat()


commit = sys.argv[1]
tag = sys.argv[2] if len(sys.argv) > 2 else None

full_commit = git("rev-parse", commit)
parent = git("rev-parse", commit + "^")
tree_expect = git("rev-parse", commit + "^{tree}")
base_tree = git("rev-parse", parent + "^{tree}")
an, ae, ad, cn, ce, cd = git("show", "-s", "--format=%an%n%ae%n%aI%n%cn%n%ce%n%cI", commit).splitlines()
msg = git("show", "-s", "--format=%B", commit)
files = git("diff", "--name-only", parent, commit).split()

print(f"[1] 本地提交 {full_commit[:8]}  parent={parent[:8]}  改动文件={files}")

entries = []
for f in files:
    ls = git("ls-tree", commit, "--", f)
    mode = ls.split()[0]
    content = git("cat-file", "blob", f"{commit}:{f}")
    entries.append({"path": f, "mode": mode, "type": "blob", "content": content})
    print(f"    {f} mode={mode} bytes={len(content)}")

remote_main = api("GET", f"/repos/{REPO}/git/ref/heads/main")["object"]["sha"]
print(f"[2] 远端 main = {remote_main[:8]}（本地 parent {parent[:8]}）")
if remote_main != parent:
    print("    ⚠️ 与本地 parent 不同（CRLF 导致 SHA 分叉）→ base_tree 改用**远端** main 的 tree")
# 以远端 main 的 tree 为基准，避免本地 CRLF blob 与远端 LF blob 混用导致 tree 漂移
base_tree = api("GET", f"/repos/{REPO}/git/commits/{remote_main}")["tree"]["sha"]
print(f"    base_tree = {base_tree[:8]}（远端）")

res = api("POST", f"/repos/{REPO}/git/trees", {"base_tree": base_tree, "tree": entries})
new_tree = res["sha"]
print(f"[3] tree 远端={new_tree[:8]} 本地={tree_expect[:8]}  {'✅ 一致' if new_tree == tree_expect else '⚠️ 不一致'}")

res = api("POST", f"/repos/{REPO}/git/commits", {
    "tree": new_tree, "parents": [remote_main], "message": msg,
    "author": {"name": an, "email": ae, "date": ad},
    "committer": {"name": cn, "email": ce, "date": cd},
})
new_commit = res["sha"]
print(f"[4] commit 远端={new_commit[:8]} 本地={full_commit[:8]}  {'✅ SHA 一致' if new_commit == full_commit else '⚠️ SHA 不一致'}")

api("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": new_commit})
print(f"[5] main ref 已更新 → {new_commit[:8]}")

if tag:
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
    print(f"[6] 重建 tag {tag} → object={new_commit[:8]} tagger={tname_}")
    try:
        api("DELETE", f"/repos/{REPO}/git/refs/tags/{tag}")
        print("    旧 tag ref 已删")
    except Exception as e:
        print("    删旧 tag 失败（可能不存在）：", type(e).__name__)
    tres = api("POST", f"/repos/{REPO}/git/tags", {
        "tag": tname, "message": tmsg, "object": new_commit, "type": "commit",
        "tagger": {"name": tname_, "email": tmail, "date": iso_from_git_ts(ts)},
    })
    api("POST", f"/repos/{REPO}/git/refs", {"ref": f"refs/tags/{tag}", "sha": tres["sha"]})
    print(f"[7] tag {tag} 已建 → {tres['sha'][:8]}")

print("[8] 远端核验：")
for ref in ("heads/main", f"tags/{tag}" if tag else "heads/main"):
    try:
        r = api("GET", f"/repos/{REPO}/git/ref/{ref}")
        print(f"    {ref} = {r['object']['sha'][:8]}")
    except Exception as e:
        print(f"    {ref} 查询失败 {type(e).__name__}")
