# -*- coding: utf-8 -*-
"""R157 A 线 · 0.82 上 verbose 编译现场采集（抓秒挂根因线索）。"""
from __future__ import annotations
import io, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIGHTHARNESS = ROOT / "lightharness"
REMOTE_PTR = LIGHTHARNESS / "reports" / "同步0.82_远程目录.txt"
HOST = "192.168.0.82"
PORT = 22
PY = "/usr/local/bin/python3.12"


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


def run_remote(cli, cmd, timeout=1200):
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
            raise TimeoutError("timeout")
        time.sleep(0.1)
    rc = chan.recv_exit_status()
    chan.close()
    return rc, buf.getvalue()


# 独立小脚本：直接用 compile_light_typed 的 verbose 模式跑一次
PROBE_PY = r"""
import sys, time, os, tempfile
_here = os.getcwd()
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(_here, 'src'))
sys.path.insert(0, os.path.join(_here, 'stdlib'))
from llvm.compiler import compile_light_typed, find_clang
from 中国行政区划 import ChinaRegion
r = ChinaRegion()
code = ['从 中国行政区划 导入 获取行政区划代码', '段落 主:']
for 名称, 代码 in r._region_code_map.items():
    code.append('  输出(获取行政区划代码("%s"))' % 名称)
for 名称, 代码 in [("湛江市","440800"),("中山市","442000"),("东莞市","441900"),("金华市","330700")]:
    code.append('  输出(获取行政区划代码("%s"))' % 名称)
src = '\n'.join(code)
print('clang =', find_clang())
t0 = time.time()
with tempfile.TemporaryDirectory(prefix='_r157v_') as d:
    sp = os.path.join(d, '主.light')
    open(sp,'w',encoding='utf-8').write(src)
    t1 = time.time()
    exe = compile_light_typed(sp, os.path.join(d, '产物'), optimize_level=0, verbose=True)
    t2 = time.time()
    import subprocess
    r2 = subprocess.run([exe], capture_output=True, timeout=300, cwd=d)
    t3 = time.time()
    print('TIMING read=%.2f compile=%.2f run=%.2f total=%.2f' % (t1-t0, t2-t1, t3-t2, t3-t0))
    print('RUNRC=%d' % r2.returncode)
    print('OUTLINES=%d' % len(r2.stdout.decode('utf-8','replace').strip().split(chr(10))))
"""


def main():
    remote_dir = REMOTE_PTR.read_text(encoding="utf-8").strip()
    cwd = f"{remote_dir}/light-merge"
    cli = connect()
    try:
        print(f"[采集] {cwd}")
        probe_path = "/tmp/r157_probe.py"
        sftp = cli.open_sftp()
        with sftp.open(probe_path, "w") as f:
            f.write(PROBE_PY)
        sftp.close()
        cmd = (
            f"cd {cwd} && export PYTHONIOENCODING=utf-8 && "
            f"export PATH=/tmp/r44-shim:$PATH && "
            f"{PY} {probe_path}"
        )
        rc, out = run_remote(cli, cmd, timeout=1200)
        print(f"rc={rc}")
        print(out[-4000:])
    finally:
        cli.close()


if __name__ == "__main__":
    main()