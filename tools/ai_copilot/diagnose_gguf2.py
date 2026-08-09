#!/usr/bin/env python3
"""SSH 到 192.168.0.88 检查 GGUF tensor 详情"""
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
        print(out[:5000])
    if err:
        print(f"[stderr] {err[:3000]}")
    return out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)
print("[OK] SSH connected")

# 检查 python 可用性
run(ssh, "which python python3 python3.11 python3.10 2>/dev/null; python --version 2>&1")

# 用 python 检查 GGUF
script = r'''
import struct, sys

f = open(sys.argv[1], "rb")
magic = struct.unpack("<I", f.read(4))[0]
print(f"Magic: 0x{magic:08x} (GGUF={magic == 0x46554747})")
version = struct.unpack("<I", f.read(4))[0]
tensor_count = struct.unpack("<Q", f.read(8))[0]
metadata_kv_count = struct.unpack("<Q", f.read(8))[0]
print(f"Version: {version}, Tensors: {tensor_count}, Metadata KVs: {metadata_kv_count}")

def read_string(f):
    n = struct.unpack("<Q", f.read(8))[0]
    return f.read(n).decode("utf-8", errors="replace")

def read_value(f, t):
    if t == 0: return struct.unpack("<B", f.read(1))[0]
    elif t == 1: return struct.unpack("<b", f.read(1))[0]
    elif t == 2: return struct.unpack("<H", f.read(2))[0]
    elif t == 3: return struct.unpack("<h", f.read(2))[0]
    elif t == 4: return struct.unpack("<I", f.read(4))[0]
    elif t == 5: return struct.unpack("<i", f.read(4))[0]
    elif t == 6: return struct.unpack("<f", f.read(4))[0]
    elif t == 7: return struct.unpack("<B", f.read(1))[0] != 0
    elif t == 8: return read_string(f)
    elif t == 9:
        et = struct.unpack("<I", f.read(4))[0]
        ec = struct.unpack("<Q", f.read(8))[0]
        return [read_value(f, et) for _ in range(min(ec, 50))]
    elif t == 10: return struct.unpack("<Q", f.read(8))[0]
    elif t == 11: return struct.unpack("<q", f.read(8))[0]
    elif t == 12: return struct.unpack("<d", f.read(8))[0]
    else: return f"<type {t}>"

for i in range(metadata_kv_count):
    key = read_string(f)
    vt = struct.unpack("<I", f.read(4))[0]
    val = read_value(f, vt)
    if isinstance(val, str) and len(val) > 120:
        val = val[:120] + "..."
    print(f"  {key} = {val}")

print(f"\n--- Tensors ({tensor_count}) ---")
tnames = []
for i in range(tensor_count):
    name = read_string(f)
    nd = struct.unpack("<I", f.read(4))[0]
    dims = [struct.unpack("<I", f.read(4))[0] for _ in range(nd)]
    dt = struct.unpack("<I", f.read(4))[0]
    off = struct.unpack("<Q", f.read(8))[0]
    tnames.append(name)

# 打印所有 tensor 名
for i, n in enumerate(tnames):
    print(f"  [{i:3d}] {n}")

# 分析 block 结构
print(f"\n--- Block analysis ---")
blk_nums = set()
for n in tnames:
    if n.startswith("blk."):
        parts = n.split(".")
        if len(parts) >= 2:
            try: blk_nums.add(int(parts[1]))
            except: pass
if blk_nums:
    print(f"  Blocks: {min(blk_nums)}-{max(blk_nums)} ({len(blk_nums)} blocks)")
    # 检查每个 block 的 tensor
    for bnum in sorted(blk_nums):
        blk_tensors = [n for n in tnames if n.startswith(f"blk.{bnum}.")]
        has_attn_norm = any("attn_norm" in n for n in blk_tensors)
        has_ffn_norm = any("ffn_norm" in n for n in blk_tensors)
        has_attn_q = any("attn_q" in n or "q_proj" in n for n in blk_tensors)
        print(f"  blk.{bnum}: {len(blk_tensors)} tensors, attn_norm={has_attn_norm}, ffn_norm={has_ffn_norm}, attn_q={has_attn_q}")
        if not has_attn_norm:
            print(f"    -> tensors: {blk_tensors}")

f.close()
'''

# 写脚本到远程并执行
run(ssh, f"cat > /tmp/gguf_check.py << 'PYEOF'\n{script}\nPYEOF")
run(ssh, f"python /tmp/gguf_check.py '{GGUF}' 2>&1", timeout=30)

# 检查 ollama 是否有 show 命令可以看模型信息
run(ssh, "ollama show light-translator 2>&1 || true")

ssh.close()
print("\n[done]")
