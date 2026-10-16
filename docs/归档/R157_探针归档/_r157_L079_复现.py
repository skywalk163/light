# -*- coding: utf-8 -*-
"""R157 A 线 · L-079 复现脚本 v3：多文件并发原生编译压力复现。

模拟 L-079 原始观测条件：0.88 全量门禁 `-n 8` 下，多个文件里的原生腿编译用例
被不同 worker 并发执行，竞争 clang/磁盘/资源。

用法：python _r157_L079_复现.py <轮次> <n> [mode]
  mode:
    combo   多个原生编译文件一起跑（--dist=loadfile，真并发）—— 默认
    case    单用例（基线）
    file    单文件
"""
from __future__ import annotations
import io, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIGHTHARNESS = ROOT / "lightharness"
REMOTE_PTR = LIGHTHARNESS / "reports" / "同步0.82_远程目录.txt"
HOST = "192.168.0.82"
PORT = 22
PY = "/usr/local/bin/python3.12"

CASE = ("tests/unit/test_原生腿_R13B_能力扩展.py"
        "::Test行政区划扩展::test_O0_行政区划代码_对拍与扩展")
FILE = "tests/unit/test_原生腿_R13B_能力扩展.py"
# 与 R13B 同属「原生腿 O0 编译」的相邻测试文件（真实并发 clang 编译场景）
COMBO_FILES = [
    "tests/unit/test_原生腿_R13B_能力扩展.py",
    "tests/unit/test_codegen_unary_bool_O0.py",
    "tests/unit/test_codegen_container_writeback_O0.py",
    "tests/unit/test_codegen_controlflow_O0.py",
    "tests/unit/test_codegen_method_syntax_O0.py",
    "tests/unit/test_codegen_float_slot_O0.py",
    "tests/unit/test_codegen_ref_dict_O0.py",
    "tests/unit/test_codegen_safename_multimodule_O0.py",
]


def load_env():
    data = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data.get("SSH_USER_AI", ""), data.get("SSH_PASS_AI", "")


def connect():
    import paramiko
    user, pwd = load_env()
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, port=PORT, username=user, password=pwd, timeout=30,
                allow_agent=False, look_for_keys=False)
    return cli


def run_remote(cli, cmd, timeout=2400):
    chan = cli.get_transport().open_session()
    chan.settimeout(timeout)
    chan.exec_command(cmd)
    buf = io.StringIO()
    t0 = time.time()
    while True:
        if chan.recv_ready():
            buf.write(chan.recv(65536).decode("utf-8", "replace"))
        if chan.exit_status_ready():
            while chan.recv_ready():
                buf.write(chan.recv(65536).decode("utf-8", "replace"))
            break
        if time.time() - t0 > timeout:
            chan.close()
            raise TimeoutError(f"远端命令超时: {cmd[:80]}")
        time.sleep(0.1)
    rc = chan.recv_exit_status()
    chan.close()
    return rc, buf.getvalue()


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    n = sys.argv[2] if len(sys.argv) > 2 else "8"
    mode = sys.argv[3] if len(sys.argv) > 3 else "combo"
    remote_dir = REMOTE_PTR.read_text(encoding="utf-8").strip()
    cwd = f"{remote_dir}/light-merge"

    if mode == "combo":
        sel = " ".join(COMBO_FILES)
        dist = "--dist=loadfile "
    elif mode == "file":
        sel = FILE
        dist = ""
    else:
        sel = CASE
        dist = ""

    node = ""
    if n != "1":
        node = f"-n {n} {dist}"
    else:
        node = "-p no:xdist "

    cli = connect()
    try:
        print(f"[复现v3] {remote_dir}  轮次={rounds}  n={n}  mode={mode}  PY={PY}")
        print(f"  选择: {sel}")
        for i in range(1, rounds + 1):
            t0 = time.time()
            cmd = (
                f"cd {cwd} && export PYTHONIOENCODING=utf-8 && "
                f"export PATH=/tmp/r44-shim:$PATH && "
                f"{PY} -m pytest {sel} {node}-o addopts= --timeout=300 --tb=short -q "
                f"-rfE --durations=5 2>&1 | tail -50"
            )
            try:
                rc, out = run_remote(cli, cmd, timeout=2400)
            except TimeoutError as e:
                print(f"[轮 {i:02d}] 超时 {e}")
                continue
            dur = time.time() - t0
            summary = [l for l in out.splitlines()
                       if "passed" in l or "failed" in l or "error" in l]
            print(f"[轮 {i:02d}] wall={dur:.2f}s  pytest_rc={rc}  {' | '.join(summary)}")
            if rc != 0:
                print(f"  --- 现场 ---\n{out[-3000:]}")
    finally:
        cli.close()


if __name__ == "__main__":
    main()