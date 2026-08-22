#!/usr/bin/env bash
# ============================================================
# 任务 D2-2：POSIX 分支可复现脚本（进程树）
#
# 目的：`stdlib/进程树.light` 的 POSIX 分支（os.setsid / os.killpg /
# SIGTERM→SIGKILL 升级链）在 Windows 上从未实测。本机（2026-08-22 实探）
# 无 WSL 发行版、无 Docker（`wsl -l -q` rc=1、`docker` 不可执行），
# 系统级工具被安全策略禁用，无法就地实测。
#
# 本脚本**未在本机运行过**，请在有 Linux 环境的一侧执行：
#     bash tools/taskD2_posix_repro.sh          # 或 chmod +x 后直接 ./运行
# 脚本自包含：唯一外部依赖是 python3（标准库即可，不需要 pytest、psutil）。
#
# 逐项验证：
#   [1] setsid 后 killpg 杀整个进程组能带走孙子进程
#   [2] SIGTERM 宽限期内正常退出的路径（不需要 SIGKILL）
#   [3] 宽限超时后 SIGKILL 生效
#   [4] 孤儿进程不残留（跑完 ps 确认，只按唯一标记匹配，绝不按进程名乱杀）
#
# 输出：每项 PASS/FAIL，末尾汇总；任意 FAIL 时脚本以非零码退出。
# ============================================================
set -u

# 定位仓库根目录（本脚本在 tools/ 下）
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_REPO_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"
_PYTHON="${PYTHON:-python3}"

echo "=== taskD2_posix_repro：进程树 POSIX 分支验证 ==="
echo "repo root: $_REPO_ROOT"
echo "python   : $("$_PYTHON" --version 2>&1)"
echo "本机未实测声明：本脚本由 Windows 侧产出，未在 Linux 上实际执行过；"
echo "以下结果以当前（Linux）机器为准。"
echo

"$_PYTHON" - "$_REPO_ROOT" <<'PY'
import os
import sys
import time
import signal
import subprocess

REPO_ROOT = sys.argv[1] if len(sys.argv) > 1 else None

# ---- 结果汇总 ----
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


# ---- 通用工具（只按 PID/进程组，绝不按进程名杀） ----
def 活(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ProcessLookupError):
        return False
    except Exception:
        return False


def 孙脚本(marker, 秒=60):
    return (
        "import time, sys\n"
        "time.sleep(%d)\n"
        "open(sys.argv[1], 'w').write('x')\n" % 秒
    )


def 父脚本(孙路径, 标记路径):
    return (
        "import subprocess, sys, time\n"
        "gc = subprocess.Popen([sys.executable, '-u', %r, %r])\n"
        "print(gc.pid, flush=True)\n"
        "time.sleep(60)\n" % (孙路径, 标记路径)
    )


def ps_残留(标记):
    """用 ps 查唯一标记，返回残留进程 (pid, ppid, pgid, args) 列表。"""
    try:
        out = subprocess.run(
            ["ps", "-eo", "pid,ppid,pgid,args"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception as e:
        return [("?", "?", "?", f"ps 失败: {e}")]
    rows = []
    for line in out.splitlines()[1:]:
        parts = line.split(None, 3)
        if len(parts) >= 4 and 标记 in parts[3]:
            rows.append(tuple(parts[:4]))
    return rows


# ============================================================
# A. 语义自检（纯 Python，独立于 .light 编译器，任何 Linux 可跑）
# ============================================================
print("---- A. 纯 Python 语义自检（OS 级） ----")


def A_杀组带孙():
    """[1] setsid 后 killpg 杀组带走孙子。"""
    d = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/tmp"
    import tempfile
    tmp = tempfile.mkdtemp(prefix="_taskD2_")
    mark = os.path.join(tmp, "孙标记.txt")
    gc = os.path.join(tmp, "孙.py")
    pr = os.path.join(tmp, "父.py")
    with open(gc, "w", encoding="utf-8") as f:
        f.write(孙脚本(mark))
    with open(pr, "w", encoding="utf-8") as f:
        f.write(父脚本(gc, mark))
    # setsid 建立新会话（进程组组长 = pid）
    p = subprocess.Popen(
        [sys.executable, "-u", pr], preexec_fn=os.setsid,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        line = p.stdout.readline().strip()
        if not line.isdigit():
            return False, f"未读到孙子 pid: {line!r}"
        gcpid = int(line)
        time.sleep(0.5)
        if not 活(gcpid):
            return False, f"孙子未存活: {gcpid}"
        # 杀整个进程组（组长即 p.pid）
        os.killpg(p.pid, signal.SIGTERM)
        time.sleep(0.3)
        if 活(p.pid):
            os.killpg(p.pid, signal.SIGKILL)
        time.sleep(0.5)
        if 活(p.pid):
            return False, "父进程仍存活"
        if 活(gcpid):
            return False, "孙子进程仍存活（未随组被杀）"
        if os.path.exists(mark):
            return False, "孙子写下了标记（说明没死透）"
        return True, f"父 {p.pid} / 孙 {gcpid} 均已死"
    finally:
        try:
            p.kill()
        except Exception:
            pass
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            pass
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


ok, d = A_杀组带孙()
check("A1 setsid 后 killpg 杀组带走孙子进程", ok, d)


def A_宽限正常退出():
    """[2] SIGTERM 宽限期内正常退出，不需要 SIGKILL。"""
    code = (
        "import signal, time, sys\n"
        "def h(sig, frm):\n"
        "    print('TERM', flush=True)\n"
        "    sys.exit(0)\n"
        "signal.signal(signal.SIGTERM, h)\n"
        "time.sleep(60)\n"
    )
    p = subprocess.Popen(
        [sys.executable, "-c", code], preexec_fn=os.setsid,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        time.sleep(0.5)
        os.killpg(p.pid, signal.SIGTERM)
        # 宽限 5s 内应正常退出（退出码 0，说明是 handler 自己退的，不是被 SIGKILL）
        rc = p.wait(timeout=5)
        if rc != 0:
            return False, f"退出码 {rc}（期望 0，可能被 SIGKILL）"
        return True, f"宽限内正常退出，退出码 {rc}"
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            pass
        return False, "5s 宽限内未退出（SIGTERM 路径失效）"


ok, d = A_宽限正常退出()
check("A2 SIGTERM 宽限期内正常退出（无需 SIGKILL）", ok, d)


def A_宽限超时强杀():
    """[3] 宽限超时后 SIGKILL 生效。"""
    code = (
        "import signal, time\n"
        "def h(sig, frm):\n"
        "    pass  # 忽略 SIGTERM\n"
        "signal.signal(signal.SIGTERM, h)\n"
        "time.sleep(60)\n"
    )
    p = subprocess.Popen(
        [sys.executable, "-c", code], preexec_fn=os.setsid,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        time.sleep(0.5)
        os.killpg(p.pid, signal.SIGTERM)
        time.sleep(0.4)  # 宽限期
        if not 活(p.pid):
            return False, "SIGTERM 后进程反而退了（期望它忽略）"
        os.killpg(p.pid, signal.SIGKILL)
        rc = p.wait(timeout=3)
        return True, f"SIGKILL 后退出，退出码 {rc}（-9 即被强杀）"
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            pass
        return False, "SIGKILL 后 3s 未退出"


ok, d = A_宽限超时强杀()
check("A3 宽限超时后 SIGKILL 生效", ok, d)


def A_孤儿不残留():
    """[4] 跑完 ps 确认没有带任务标记的残留进程。"""
    标记 = "_taskD2_孤儿探针_"
    code = f"import time\ntime.sleep(60)\n# {标记}\n"
    p = subprocess.Popen(
        [sys.executable, "-c", code], preexec_fn=os.setsid,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.5)
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except Exception:
        pass
    try:
        p.wait(timeout=3)
    except subprocess.TimeoutExpired:
        p.kill()
    time.sleep(0.3)
    rows = ps_残留(标记)
    if rows:
        return False, f"残留: {rows}"
    return True, "ps 未发现带标记的残留进程"


ok, d = A_孤儿不残留()
check("A4 孤儿进程不残留（ps 确认）", ok, d)

# ============================================================
# B. 真模块自检（能加载 stdlib/进程树.light 就跑真实 POSIX 分支）
# ============================================================
print("---- B. 真实 stdlib/进程树.light POSIX 分支 ----")
try:
    sys.path.insert(0, REPO_ROOT)
    sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
    sys.path.insert(0, os.path.join(REPO_ROOT, "stdlib"))
    import _light_import_hook
    _light_import_hook.install([os.path.join(REPO_ROOT, "stdlib"), REPO_ROOT])
    from 进程树 import 进程树
    MODULE_OK = True
except Exception as e:
    MODULE_OK = False
    print(f"（无法加载 stdlib/进程树.light：{type(e).__name__}: {e} → B 部分跳过）")

if MODULE_OK:
    import tempfile

    def B_跑(命令, 配置, 超时):
        树干 = 进程树(命令, 配置)
        if not 树干.启动():
            return None, None
        return 树干, 树干.等待(超时)

    def B_杀组带孙():
        import shutil
        tmp = tempfile.mkdtemp(prefix="_taskD2_")
        mark = os.path.join(tmp, "孙标记.txt")
        gc = os.path.join(tmp, "孙.py")
        pr = os.path.join(tmp, "父.py")
        try:
            with open(gc, "w", encoding="utf-8") as f:
                f.write(孙脚本(mark))
            with open(pr, "w", encoding="utf-8") as f:
                f.write(父脚本(gc, mark))
            树干, 结果 = B_跑(
                [sys.executable, "-u", pr],
                {"宽限期毫秒": 400}, 超时=1200,
            )
            if 树干 is None:
                return False, "启动失败"
            是否超时 = 结果.是否超时
            line = 结果.标准输出.strip()
            if not line.isdigit():
                return False, f"未读到孙子 pid: {line!r}"
            gcpid = int(line)
            time.sleep(0.5)
            if 活(gcpid):
                return False, "孙子进程仍存活（杀树没带走进程组）"
            if 树干.是否存活():
                return False, "直接子进程仍存活"
            if os.path.exists(mark):
                return False, "孙子写下了标记"
            return True, f"超时={是否超时}，父/孙均已死"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    ok, d = B_杀组带孙()
    check("B1 真实模块：setsid 杀组带走孙子", ok, d)

    def B_宽限正常退出():
        code = (
            "import signal, time, sys\n"
            "def h(sig, frm):\n"
            "    sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, h)\n"
            "time.sleep(60)\n"
        )
        树干 = 进程树([sys.executable, "-u", "-c", code], {"宽限期毫秒": 4000})
        if not 树干.启动():
            return False, "启动失败"
        结果 = 树干.等待(1500)  # 1.5s 触发总超时 → 杀树(SIGTERM) → 宽限 4s
        if 树干.是否存活():
            return False, "进程未在宽限内退出（可能被 SIGKILL）"
        if 结果.退出码 != 0:
            return False, f"退出码 {结果.退出码}（期望 0，可能被强杀）"
        return True, f"宽限内正常退出，退出码 {结果.退出码}"

    ok, d = B_宽限正常退出()
    check("B2 真实模块：SIGTERM 宽限内正常退出", ok, d)

    def B_宽限超时强杀():
        code = (
            "import signal, time\n"
            "def h(sig, frm):\n"
            "    pass\n"
            "signal.signal(signal.SIGTERM, h)\n"
            "time.sleep(60)\n"
        )
        树干 = 进程树([sys.executable, "-u", "-c", code], {"宽限期毫秒": 300})
        if not 树干.启动():
            return False, "启动失败"
        结果 = 树干.等待(1500)
        if 树干.是否存活():
            return False, "进程未被 SIGKILL 杀掉"
        return True, "忽略 SIGTERM 后超时被 SIGKILL"

    ok, d = B_宽限超时强杀()
    check("B3 真实模块：宽限超时后 SIGKILL 生效", ok, d)

    def B_孤儿不残留():
        标记 = "_taskD2_孤儿探针B_"
        code = f"import time\ntime.sleep(60)\n# {标记}\n"
        树干 = 进程树([sys.executable, "-u", "-c", code], {"宽限期毫秒": 300})
        if not 树干.启动():
            return False, "启动失败"
        树干.等待(1200)
        time.sleep(0.3)
        rows = ps_残留(标记)
        if rows:
            return False, f"残留: {rows}"
        return True, "ps 未发现残留"

    ok, d = B_孤儿不残留()
    check("B4 真实模块：孤儿进程不残留", ok, d)
else:
    print("（B 部分未运行——不影响 A 部分结论）")

# ============================================================
print()
总计 = len(RESULTS)
通过 = sum(1 for _, ok, _ in RESULTS if ok)
print(f"=== 汇总：{通过}/{总计} PASS ===")
for 名, ok, _ in RESULTS:
    print(f"  [{'PASS' if ok else 'FAIL'}] {名}")
if 通过 != 总计:
    print("存在 FAIL，请把本脚本输出连同平台信息（uname -a）交回主线。")
    sys.exit(1)
print("全部通过。")
sys.exit(0)
PY
