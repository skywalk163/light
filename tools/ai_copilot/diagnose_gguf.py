#!/usr/bin/env python3
"""SSH 到 192.168.0.88 诊断 GGUF 模型问题"""
import paramiko
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ssh_config import SSH_HOST, SSH_USER_DUMATE, SSH_PASS_DUMATE2

HOST = SSH_HOST
USER = SSH_USER_DUMATE
PASS = SSH_PASS_DUMATE2
MODEL_DIR = "/home/skywalk/Downloads/kaggle/working/light/tools/ai_copilot/output/light_translator_merged_3.5_2b"

def run(ssh, cmd, timeout=60):
    print(f"\n$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    if out:
        print(out[:3000])
    if err:
        print(f"[stderr] {err[:2000]}")
    return code, out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print(f"连接 {USER}@{HOST}...")
ssh.connect(HOST, username=USER, password=PASS, timeout=10)
print("[OK] SSH 连接成功")

# 1. 查看 GGUF 文件信息
run(ssh, f"ls -lh {MODEL_DIR}/light_translator_q4_k_m.gguf")

# 2. 查看 ollama 版本
run(ssh, "ollama --version")

# 3. 查看 llama.cpp 版本（如果有）
run(ssh, "llama-server --version 2>&1 || llama-cli --version 2>&1 || echo 'no llama.cpp binary'")

# 4. 检查 GGUF 文件头和 metadata
# 用 python 读 GGUF header
gguf_inspect = """
import struct, sys, json

f = open(sys.argv[1], "rb")

# GGUF magic
magic = struct.unpack("<I", f.read(4))[0]
print(f"Magic: 0x{magic:08x} (GGUF={magic == 0x46554747})")

version = struct.unpack("<I", f.read(4))[0]
print(f"Version: {version}")

tensor_count = struct.unpack("<Q", f.read(8))[0]
metadata_kv_count = struct.unpack("<Q", f.read(8))[0]
print(f"Tensor count: {tensor_count}")
print(f"Metadata KV count: {metadata_kv_count}")

# 读 metadata
def read_string(f):
    n = struct.unpack("<Q", f.read(8))[0]
    return f.read(n).decode("utf-8", errors="replace")

def read_value(f, t):
    if t == 0:  # UINT8
        return struct.unpack("<B", f.read(1))[0]
    elif t == 1:  # INT8
        return struct.unpack("<b", f.read(1))[0]
    elif t == 2:  # UINT16
        return struct.unpack("<H", f.read(2))[0]
    elif t == 3:  # INT16
        return struct.unpack("<h", f.read(2))[0]
    elif t == 4:  # UINT32
        return struct.unpack("<I", f.read(4))[0]
    elif t == 5:  # INT32
        return struct.unpack("<i", f.read(4))[0]
    elif t == 6:  # FLOAT32
        return struct.unpack("<f", f.read(4))[0]
    elif t == 7:  # BOOL
        return struct.unpack("<B", f.read(1))[0] != 0
    elif t == 8:  # STRING
        return read_string(f)
    elif t == 9:  # ARRAY
        elem_type = struct.unpack("<I", f.read(4))[0]
        elem_count = struct.unpack("<Q", f.read(8))[0]
        return [read_value(f, elem_type) for _ in range(min(elem_count, 20))]
    elif t == 10:  # UINT64
        return struct.unpack("<Q", f.read(8))[0]
    elif t == 11:  # INT64
        return struct.unpack("<q", f.read(8))[0]
    elif t == 12:  # FLOAT64
        return struct.unpack("<d", f.read(8))[0]
    else:
        return f"<unknown type {t}>"

metadata = {}
for i in range(metadata_kv_count):
    key = read_string(f)
    val_type = struct.unpack("<I", f.read(4))[0]
    val = read_value(f, val_type)
    metadata[key] = val
    if isinstance(val, str) and len(val) > 100:
        val = val[:100] + "..."
    print(f"  {key} = {val}")

# 读 tensor names
print(f"\\nTensors (first 50 and last 20 of {tensor_count}):")
tensor_names = []
for i in range(tensor_count):
    name = read_string(f)
    n_dims = struct.unpack("<I", f.read(4))[0]
    dims = [struct.unpack("<I", f.read(4))[0] for _ in range(n_dims)]
    dtype = struct.unpack("<I", f.read(4))[0]
    offset = struct.unpack("<Q", f.read(8))[0]
    tensor_names.append(name)
    if i < 50 or i >= tensor_count - 20:
        print(f"  [{i}] {name} dims={dims} dtype={dtype} offset={offset}")
    elif i == 50:
        print(f"  ... (skipping middle tensors) ...")

# 检查缺失的 tensor
print(f"\\nChecking for missing attn_norm tensors:")
found_attn_norms = [n for n in tensor_names if "attn_norm" in n]
print(f"  Found attn_norm tensors: {found_attn_norms}")

# 检查 block 数量
blk_nums = set()
for n in tensor_names:
    if n.startswith("blk."):
        try:
            num = int(n.split(".")[1])
            blk_nums.add(num)
        except:
            pass
if blk_nums:
    print(f"  Block numbers: {min(blk_nums)} to {max(blk_nums)} (total {len(blk_nums)})")
    # 检查哪些 block 缺 attn_norm
    for num in sorted(blk_nums):
        has_attn_norm = any(f"blk.{num}.attn_norm" in n for n in tensor_names)
        if not has_attn_norm:
            print(f"  [MISSING] blk.{num}.attn_norm.weight")

f.close()
"""

run(ssh, f"python3 -c '{gguf_inspect}' {MODEL_DIR}/light_translator_q4_k_m.gguf 2>&1", timeout=30)

# 5. 检查原始合并模型（safetensors）的 tensor 列表
run(ssh, f"ls -lh {MODEL_DIR}/*.safetensors 2>/dev/null || echo 'no safetensors'")

# 6. 检查是否有 f16 版本
run(ssh, f"ls -lh {MODEL_DIR}/*.gguf 2>/dev/null")

# 7. 查看 ollama 已有模型
run(ssh, "ollama list 2>&1")

# 8. 查看 Modelfile 内容
run(ssh, f"cat {MODEL_DIR}/Modelfile 2>/dev/null")

ssh.close()
print("\n[完成] 诊断完毕")
