#!/usr/bin/env python3
"""SSH 到 88 用 python3.11 检查 GGUF"""
import paramiko
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ssh_config import SSH_HOST, SSH_USER_DUMATE, SSH_PASS_DUMATE2

HOST = SSH_HOST
USER = SSH_USER_DUMATE
PASS = SSH_PASS_DUMATE2
GGUF = "/home/skywalk/Downloads/kaggle/working/light/tools/ai_copilot/output/light_translator_merged_3.5_2b/light_translator_q4_k_m.gguf"

def run(ssh, cmd, timeout=60):
    print(f"\n$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        print(out[:8000])
    if err:
        print(f"[stderr] {err[:3000]}")
    return out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

# 用 python3.11 全路径
run(ssh, "/usr/local/bin/python3.11 --version")

script = r'''
import struct, sys
f = open(sys.argv[1], "rb")
magic = struct.unpack("<I", f.read(4))[0]
print(f"Magic: 0x{magic:08x} GGUF={magic == 0x46554747}")
version = struct.unpack("<I", f.read(4))[0]
tc = struct.unpack("<Q", f.read(8))[0]
mc = struct.unpack("<Q", f.read(8))[0]
print(f"Version: {version} Tensors: {tc} MetaKVs: {mc}")

def rs(f):
    n = struct.unpack("<Q", f.read(8))[0]
    return f.read(n).decode("utf-8","replace")
def rv(f, t):
    if t==0: return struct.unpack("<B",f.read(1))[0]
    elif t==1: return struct.unpack("<b",f.read(1))[0]
    elif t==2: return struct.unpack("<H",f.read(2))[0]
    elif t==3: return struct.unpack("<h",f.read(2))[0]
    elif t==4: return struct.unpack("<I",f.read(4))[0]
    elif t==5: return struct.unpack("<i",f.read(4))[0]
    elif t==6: return struct.unpack("<f",f.read(4))[0]
    elif t==7: return struct.unpack("<B",f.read(1))[0]!=0
    elif t==8: return rs(f)
    elif t==9:
        et=struct.unpack("<I",f.read(4))[0]; ec=struct.unpack("<Q",f.read(8))[0]
        return [rv(f,et) for _ in range(min(ec,50))]
    elif t==10: return struct.unpack("<Q",f.read(8))[0]
    elif t==11: return struct.unpack("<q",f.read(8))[0]
    elif t==12: return struct.unpack("<d",f.read(8))[0]
    else: return f"<type{t}>"

for i in range(mc):
    k=rs(f); vt=struct.unpack("<I",f.read(4))[0]; v=rv(f,vt)
    if isinstance(v,str) and len(v)>150: v=v[:150]+"..."
    print(f"  {k} = {v}")

print(f"\n--- Tensors ({tc}) ---")
tn=[]
for i in range(tc):
    n=rs(f); nd=struct.unpack("<I",f.read(4))[0]
    dims=[struct.unpack("<I",f.read(4))[0] for _ in range(nd)]
    dt=struct.unpack("<I",f.read(4))[0]; off=struct.unpack("<Q",f.read(8))[0]
    tn.append(n)

for i,n in enumerate(tn):
    print(f"  [{i:3d}] {n}")

print(f"\n--- Block analysis ---")
bn=set()
for n in tn:
    if n.startswith("blk."):
        p=n.split(".")
        if len(p)>=2:
            try: bn.add(int(p[1]))
            except: pass
if bn:
    print(f"  Blocks: {min(bn)}-{max(bn)} ({len(bn)} blocks)")
    for b in sorted(bn):
        bt=[n for n in tn if n.startswith(f"blk.{b}.")]
        an=any("attn_norm" in n for n in bt)
        fn=any("ffn_norm" in n for n in bt)
        print(f"  blk.{b}: {len(bt)}tensors attn_norm={an} ffn_norm={fn}")
        if not an:
            print(f"    MISSING attn_norm! tensors: {bt}")
f.close()
'''

run(ssh, f"/usr/local/bin/python3.11 /tmp/gguf_check.py '{GGUF}' 2>&1", timeout=30)

ssh.close()
print("\n[done]")
