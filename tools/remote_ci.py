#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 192.168.0.88（FreeBSD 15.1）上排队跑任意仓库的 pytest。

为什么需要「排队」：所有 agent 的机器都不一样（Windows 老机 / 云沙箱 / FreeBSD），
本地跑一次全量要几分钟到几小时，结论还不可比。统一到 0.88 跑之后，新的问题变成
「多个 agent 同时压同一台 12 核机器」——各自 `-n 6` 会互相抢核，跑出来的耗时没有
意义，重活还会把别人挤到超时。

于是这里做三件事：

1. **槽位（slot）**：远端用 `mkdir` 的原子性做信号量，默认 2 个槽 × `-n 6` = 12 线程，
   正好吃满 12 vCPU；槽满就排队等，等到空位再上传、再跑。
2. **现场隔离**：每个 run 一个目录 `/tmp/lp-ci/run-<时间戳>-<tag>/`，互不覆盖；
   跑完只删自己那份 tar，不动别人目录、不动远端任何既有仓库。
3. **台账**：`/tmp/lp-ci/queue.log` 记录谁在什么时候占了哪个槽、什么时候结束、rc 多少，
   `--list` 一眼看到现在谁在跑。

此外（T-0390）：**起跑前看一眼远端 load**。槽位只管「我们自己人」不互相抢，管不住
别的进程；0.88 只有 12 vCPU，被挤到 load≈15 时，一批实测 52–61s 的用例就会在
`--timeout=60` 边界上随机翻红——同一份提交两轮全量的失败集合对不上（T-0383 实测：
三轮 21/19/14，来回翻 11 条）。所以占槽之后先读一次 1 分钟负载：

* 超过 `--max-load`（默认 1.0 × vCPU）→ 在 `[3/4]` 行明确打警告，说明本轮失败集合
  不可复现；
* 加 `--wait-load` 则改成排队等待，等到负载降下来再跑（仍受 `--queue-timeout` 约束）。

凭据：默认读 `duan-light-merge/.env` 的 `SSH_USER_WORKBUDDY` / `SSH_PASS_WORKBUDDY`。

用法::

    python _tools/remote_ci.py --list                       # 看当前排队/占用情况
    python _tools/remote_ci.py --repo light-merge --tag A线   # 排队跑全量
    python _tools/remote_ci.py --repo light-merge --tag B线 -- -q -k linter
    python _tools/remote_ci.py --repo lightprism --tag M线 --jobs 6
    python _tools/remote_ci.py --repo light-merge --tag A线 --wait-load   # 负载高就等

`--` 之后的参数原样透传给 pytest。
"""

from __future__ import annotations

import argparse
import io
import os
import shlex
import sys
import tarfile
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

BASE = Path(__file__).resolve().parent.parent          # duan-light-merge/
DEFAULT_HOST = "192.168.0.88"
DEFAULT_ROOT = "/tmp/lp-ci"
DEFAULT_SLOTS = 2
STALE_MIN = 240          # 槽位锁超过 4 小时视为死锁，自动清理
POLL_SEC = 5


def env_candidates() -> list[Path]:
    """凭据文件候选路径。

    这个脚本会被复制进各仓（`_tools/` 与 `<repo>/tools/`），目录层级不一样，
    所以不写死一个路径，按顺序找第一个存在的。
    """
    out = []
    if os.environ.get("LP_ENV_FILE"):
        out.append(Path(os.environ["LP_ENV_FILE"]))
    out += [
        BASE / ".env",                       # duan-light-merge/.env
        BASE.parent / ".env",                # 上一级
        BASE / "duan-light-merge" / ".env",  # 脚本被放在别的仓里时
        BASE.parent / "duan-light-merge" / ".env",
        Path.home() / ".lp_ci_env",
    ]
    return out


def resolve_env_file(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    for p in env_candidates():
        if p.is_file():
            return p
    return None

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".pytest_basetemp",
    ".mypy_cache", ".ruff_cache", ".tox", "node_modules", "build", "dist",
    "outputs", "checkpoints", ".worktrees", "_venv_ciperf",
}
SKIP_SUFFIX = (".pyc", ".pyo", ".o", ".so", ".a", ".dylib", ".exe", ".pyd")


def load_env(path: Path) -> dict:
    env = {}
    if not path.is_file():
        return env
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def build_tar(repo: Path, dest: Path) -> tuple[int, int]:
    """打快照。返回 (文件数, 字节数)。

    `*.sh` 在**包内**转 LF：Windows 检出的 CRLF 会让 FreeBSD bash 报
    `$'\\r': command not found`。不动本机工作树里的原文件。
    tar 条目一律 POSIX 分隔符，否则 Windows 的 `str(Path)` 会把反斜杠写进文件名。
    """
    count = 0
    with tarfile.open(dest, "w:gz") as tar:
        for dirpath, dirnames, filenames in os.walk(repo):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            rel_dir = Path(dirpath).relative_to(repo)
            for name in filenames:
                if name.endswith(SKIP_SUFFIX):
                    continue
                p = Path(dirpath) / name
                arc = (rel_dir / name).as_posix()
                try:
                    if name.endswith(".sh"):
                        data = p.read_bytes().replace(b"\r\n", b"\n")
                        info = tarfile.TarInfo(arc)
                        info.size = len(data)
                        info.mtime = int(p.stat().st_mtime)
                        info.mode = 0o755
                        tar.addfile(info, io.BytesIO(data))
                    else:
                        tar.add(p, arcname=arc)
                    count += 1
                except OSError as exc:
                    print(f"[warn] 跳过 {p}: {exc}", file=sys.stderr)
    return count, dest.stat().st_size


def acquire_script(root: str, slots: int, tag: str, wait_sec: int) -> str:
    """远端占槽脚本：原子 mkdir + 陈旧锁清理 + 排队等待，占到位就 echo SLOT=<n>。"""
    return f"""
Q={root}
mkdir -p "$Q/slots"
SLOT=""
ELAPSED=0
while :; do
  i=1
  while [ $i -le {slots} ]; do
    d="$Q/slots/slot-$i"
    if [ -d "$d" ]; then
      if [ -z "$(find "$d" -prune -mmin -{STALE_MIN} 2>/dev/null)" ]; then
        echo "[queue] slot-$i 陈旧（超过 {STALE_MIN} 分钟未更新），回收" >&2
        rm -rf "$d"
      fi
    fi
    if mkdir "$d" 2>/dev/null; then
      echo $$ > "$d/pid"
      printf '%s' {shlex.quote(tag)} > "$d/owner"
      date '+%Y-%m-%d %H:%M:%S' > "$d/start"
      SLOT=$i
      break
    fi
    i=$((i+1))
  done
  if [ -n "$SLOT" ]; then break; fi
  if [ $ELAPSED -ge {wait_sec} ]; then echo "QUEUE_TIMEOUT"; exit 75; fi
  if [ $ELAPSED -eq 0 ]; then
    echo "[queue] 槽位全满，排队等待（可用 --slots 调整；占用情况见 --list）" >&2
    ls "$Q/slots" 2>/dev/null | sed 's/^/[queue]   占用: /' >&2
  fi
  sleep {POLL_SEC}
  ELAPSED=$((ELAPSED+{POLL_SEC}))
done
echo "$(date '+%Y-%m-%d %H:%M:%S') TAG={shlex.quote(tag)} SLOT=$SLOT START" >> "$Q/queue.log"
echo "SLOT=$SLOT"
"""


def load_probe_script(root: str, max_load: float, wait: bool, wait_sec: int) -> str:
    """远端负载探针：读 1 分钟 load 与 vCPU 数，给出「这一轮可不可复现」的判定。

    为什么这个判定重要（T-0390）：pytest 的每用例上限 `--timeout=60` 是硬的，而一批
    用例在本机负载正常时就要 52–61s。槽位保证了我们自己的两条线不会互相挤，但管不住
    别人的进程；一旦 load 超过 vCPU 数，这些踩线用例就会在 59–61s 之间随机翻红，
    于是「同一份提交跑两遍，失败集合不一样」。与其事后猜哪条是假红，不如起跑前就说清楚。

    输出（stdout，最后一行是结论，调用方按前缀解析）：
      LOAD=<1分钟负载> NCPU=<核数> MAXLOAD=<阈值> VERDICT=OK|HIGH
      HIGH 且 --wait-load 时循环等到低于阈值（或超时后给出 WAIT_TIMEOUT）
    """
    poll = 15
    return f"""
Q={root}
NCPU=$(sysctl -n hw.ncpu 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || nproc 2>/dev/null || echo 1)
MAX={max_load}
WAITED=0
while :; do
  LOAD=$(sysctl -n vm.loadavg 2>/dev/null | tr -d '{{}}' | awk '{{print $1}}')
  if [ -z "$LOAD" ]; then
    LOAD=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\\1/' 2>/dev/null)
  fi
  if [ -z "$LOAD" ]; then LOAD=0; fi
  VERDICT=$(awk -v l="$LOAD" -v m="$MAX" 'BEGIN{{print (l+0 > m+0) ? "HIGH" : "OK"}}')
  echo "LOAD=$LOAD NCPU=$NCPU MAXLOAD=$MAX VERDICT=$VERDICT"
  if [ "$VERDICT" = "OK" ]; then exit 0; fi
  if [ "{1 if wait else 0}" = "0" ]; then exit 0; fi
  if [ $WAITED -ge {wait_sec} ]; then echo "WAIT_TIMEOUT waited=$WAITED"; exit 0; fi
  if [ $WAITED -eq 0 ]; then
    echo "[load] 1 分钟 load 高于阈值 $MAX（$LOAD/$NCPU），等负载降下来再跑（--wait-load）" >&2
  fi
  sleep {poll}
  WAITED=$((WAITED+{poll}))
done
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="0.88 排队跑 pytest")
    ap.add_argument("--repo", default=str(BASE / "light-merge"),
                    help="要跑的仓库目录（默认 duan-light-merge/light-merge）")
    ap.add_argument("--tag", default=f"{os.environ.get('USERNAME', 'anon')}-{os.getpid()}",
                    help="排队台账里的标识，建议用线路名，例如 A线 / B线 / M线")
    ap.add_argument("--host", default=os.environ.get("LP_CI_HOST", DEFAULT_HOST))
    ap.add_argument("--remote-root", default=os.environ.get("LP_CI_ROOT", DEFAULT_ROOT))
    ap.add_argument("--env-file", default=os.environ.get("LP_ENV_FILE"),
                    help="凭据文件（默认自动找 .env：本仓 / 上二级 / duan-light-merge/.env）")
    ap.add_argument("--python", default=os.environ.get("LP_CI_PYTHON", "python3"))
    ap.add_argument("--slots", type=int, default=DEFAULT_SLOTS,
                    help=f"并发槽位数（默认 {DEFAULT_SLOTS}；每槽用 -n jobs 个 worker）")
    ap.add_argument("--jobs", type=int, default=6, help="pytest-xdist -n（0=串行）")
    ap.add_argument("--queue-timeout", type=int, default=3600, help="等槽位的最长秒数")
    ap.add_argument("--timeout", type=float, default=5400.0, help="远端命令超时秒数")
    ap.add_argument("--max-load", type=float, default=0.0,
                    help="起跑前允许的 1 分钟负载上限（默认 0 = 自动取 1.0×vCPU；"
                         "超过就在 [3/4] 行打警告，说明本轮失败集合不可复现）")
    ap.add_argument("--wait-load", action="store_true",
                    help="负载超过 --max-load 时排队等它降下来再跑，而不是只警告")
    ap.add_argument("--list", action="store_true", help="只看排队/占用情况，不跑测试")
    ap.add_argument("--no-clean", action="store_true", help="保留本次 tar（排障用）")
    ap.add_argument("--no-addopts", action="store_true",
                    help="用 -o addopts= 清空仓库 addopts（仓库 addopts 硬依赖某个插件而远端没装时用）")
    args, extra = ap.parse_known_args()
    # parse_known_args 会把分隔符 "--" 本身留在 extra 里，透传给 pytest 就成了
    # `pytest -- -k xxx`，症状是「no tests ran」且看不出原因
    if extra and extra[0] == "--":
        extra = extra[1:]

    try:
        import paramiko
    except ModuleNotFoundError:
        print("缺少 paramiko：pip install paramiko（只在跑远端时需要）", file=sys.stderr)
        return 2

    env_path = resolve_env_file(args.env_file)
    if env_path is None:
        print("没有凭据文件：找过 " + "、".join(str(p) for p in env_candidates()) +
              "；可用 --env-file 或 LP_ENV_FILE 指定", file=sys.stderr)
        return 2
    env = load_env(env_path)
    user = os.environ.get("SSH_USER_WORKBUDDY") or env.get("SSH_USER_WORKBUDDY")
    pw = os.environ.get("SSH_PASS_WORKBUDDY") or env.get("SSH_PASS_WORKBUDDY")
    if not user or not pw:
        print(f"没有凭据：{env_path} 需含 SSH_USER_WORKBUDDY / SSH_PASS_WORKBUDDY",
              file=sys.stderr)
        return 2

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(args.host, username=user, password=pw, timeout=20,
                    allow_agent=False, look_for_keys=False)
    except Exception as exc:  # noqa: BLE001
        print(f"[error] 连不上 {args.host}：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    try:
        if args.list:
            q = args.remote_root
            script = (
                f'Q={q}; mkdir -p "$Q/slots" "$Q/runs"; '
                f'echo "--- 槽位占用 ---"; '
                f'for d in "$Q"/slots/slot-*; do '
                f'[ -d "$d" ] || continue; '
                f'printf "%-8s owner=%s start=%s\\n" "$(basename "$d")" '
                f'"$(cat "$d/owner" 2>/dev/null)" "$(cat "$d/start" 2>/dev/null)"; done; '
                f'[ -n "$(ls "$Q"/slots 2>/dev/null)" ] || echo "(空，可立即上跑)"; '
                f'echo "--- 最近台账 ---"; tail -n 20 "$Q/queue.log" 2>/dev/null || echo "(无)"; '
                f'echo "--- 最近现场 ---"; ls -1dt "$Q"/run-* 2>/dev/null | head -5'
            )
            _i, out, err = cli.exec_command(script, timeout=60)
            for line in out:
                print(line, end="")
            print((err.read() or b"").decode("utf-8", "replace").rstrip())
            return 0

        repo = Path(args.repo).resolve()
        if not repo.is_dir():
            print(f"[error] 仓库不存在：{repo}", file=sys.stderr)
            return 2

        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe_tag = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.tag)
        run_name = f"run-{stamp}-{safe_tag}"
        local_tar = Path(os.environ.get("TEMP", "/tmp")) / f"{run_name}.tgz"
        n, size = build_tar(repo, local_tar)
        print(f"[1/4] 快照 {repo.name}：{n} 个文件，{size / 1048576:.1f} MB → {local_tar.name}")

        sftp = cli.open_sftp()
        remote_tar = f"{args.remote_root}/{run_name}.tgz"
        run_dir = f"{args.remote_root}/{run_name}"
        cli.exec_command(f'mkdir -p {args.remote_root}/slots {args.remote_root}/runs',
                         timeout=30)[1].read()
        sftp.put(str(local_tar), remote_tar)
        sftp.close()
        print(f"[2/4] 已上传 → {args.host}:{remote_tar}")

        # 占槽（占不到就排队等，绝不抢跑）
        acq = acquire_script(args.remote_root, max(1, args.slots), args.tag, args.queue_timeout)
        _i, aout, aerr = cli.exec_command(acq, timeout=args.queue_timeout + 120)
        acq_text = aout.read().decode("utf-8", "replace")
        acq_err = aerr.read().decode("utf-8", "replace")
        acq_rc = aout.channel.recv_exit_status()
        if acq_err.strip():
            print(acq_err.rstrip())
        if acq_rc != 0 or "SLOT=" not in acq_text:
            print(f"[error] 没占到槽位（rc={acq_rc}），本次不跑。稍后用 --list 看占用情况。",
                  file=sys.stderr)
            try:
                cli.exec_command(f"rm -f {remote_tar}", timeout=30)[1].read()
            except Exception:  # noqa: BLE001
                pass
            return 75
        slot = acq_text.strip().splitlines()[-1].split("=")[1]
        print(f"[3/4] 已占槽 slot-{slot}（tag={args.tag}），开始跑")

        # 负载闸门（T-0390）：踩线用例在 load > vCPU 时会随机翻红，先在 [3/4] 行说清楚。
        # 阈值默认 1.0×vCPU（远端自己数核数，脚本里 awk 比较，避免本地猜）。
        probe_l = load_probe_script(args.remote_root, args.max_load,
                                    args.wait_load, max(60, args.queue_timeout // 2))
        _i, lout, _lerr = cli.exec_command(probe_l, timeout=max(120, args.queue_timeout // 2 + 120))
        load_lines = [ln.strip() for ln in lout.read().decode("utf-8", "replace").splitlines() if ln.strip()]
        load_stat = {}
        for ln in load_lines:
            if ln.startswith("LOAD="):
                load_stat = dict(kv.split("=", 1) for kv in ln.split() if "=" in kv)
        if load_stat:
            try:
                ncpu = float(load_stat.get("NCPU", "1") or 1)
                cur = float(load_stat.get("LOAD", "0") or 0)
                limit = float(load_stat.get("MAXLOAD", "0") or 0)
            except ValueError:
                ncpu, cur, limit = 1.0, 0.0, 0.0
            if limit <= 0:
                limit = ncpu  # 默认阈值 = 1.0 × vCPU
            over = cur > limit
            print(f"[3/4] 远端负载 {cur:.2f} / {ncpu:.0f} vCPU（阈值 {limit:.2f}）"
                  + ("　⚠️ 超阈值：本轮慢用例可能在 --timeout=60 边界随机翻红，"
                     "失败集合不可复现" if over else "　✅ 在可复现区间"))
            if load_lines and load_lines[-1].startswith("WAIT_TIMEOUT"):
                print("[3/4] ⚠️ --wait-load 等到超时，负载仍高，按当前状态继续跑", file=sys.stderr)

        # xdist 是否存在先探一次，避免把并行参数拼进 shell 变量（拼错过一次，症状是
        # pytest 一句 "no tests ran" 就退出，极难定位）
        probe = f"{args.python} -c 'import xdist' >/dev/null 2>&1 && echo yes || echo no"
        has_xdist = cli.exec_command(probe, timeout=60)[1].read().decode().strip() == "yes"
        pytest_args = shlex.join(extra)
        if args.no_addopts:
            pytest_args = ("-o addopts= " + pytest_args).strip()
        job_arg = ""
        if args.jobs > 0:
            if has_xdist:
                job_arg = f"-n {args.jobs}"
            else:
                print("[note] 远端没有 pytest-xdist，本次串行（会慢，且排队读数不可比）",
                      file=sys.stderr)
        cleanup = "echo '[cleanup] 保留 tar'" if args.no_clean else f"rm -f {remote_tar}"
        script = " ".join([
            f"Q={args.remote_root}; SLOT={slot}; TAG={shlex.quote(args.tag)};",
            """trap 'rm -rf "$Q/slots/slot-$SLOT"' EXIT INT TERM HUP;""",
            f"mkdir -p {run_dir}; cd {run_dir} && tar -xzf {remote_tar};",
            f"echo '--- env ---'; {args.python} -V; uname -srm;",
            "echo '--- pytest ---';",
            f"START=$(date +%s); PYTHONPATH=src {args.python} -m pytest -q {job_arg} {pytest_args}; RC=$?;",
            'END=$(date +%s); echo "--- 耗时 $((END-START))s rc=$RC ---";',
            'echo "$(date \'+%Y-%m-%d %H:%M:%S\') TAG=$TAG SLOT=$SLOT END rc=$RC dur=$((END-START))s"',
            '>> "$Q/queue.log";',
            cleanup + ";",
            "echo DONE; exit $RC",
        ])
        _in, out, err = cli.exec_command(script, timeout=args.timeout)
        if os.environ.get("LP_CI_DEBUG"):
            print("[debug] remote script:", script, file=sys.stderr)
        for line in out:
            print(line, end="")
        err_text = (err.read() or b"").decode("utf-8", "replace")
        if err_text.strip():
            print("[stderr]", err_text.rstrip())
        rc = out.channel.recv_exit_status()
        print(f"[4/4] rc={rc} ｜ 现场：{args.host}:{run_dir} ｜ 槽位 slot-{slot} 已释放")
        return 0 if rc == 0 else 1
    except Exception as exc:  # noqa: BLE001 - 远端任何失败都原样报出
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        cli.close()
        try:
            Path(os.environ.get("TEMP", "/tmp"), f"{run_name}.tgz").unlink()
        except (OSError, NameError):
            pass


if __name__ == "__main__":
    raise SystemExit(main())
