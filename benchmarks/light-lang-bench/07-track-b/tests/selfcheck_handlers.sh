#!/bin/sh
# MiniBridge · handler 交叉对拍（build.sh 调用；也可单独跑）
#
# 为什么需要它：C handler 有三份"实现面"，若它们对同一输入的哈希不一致，
# 「B1 与 B2 逐字节相同」（规格 §4.3）就是假绿：
#
#   1. handlers/h_c_hash           C → 可执行文件（B1 进程编排用）
#   2. handlers/libh_c_hash.so     C → 共享库（参考绑定用）
#   3. mb_cffi.light 里的 `引 C:` 块  C → 光明侧现场编译（B2 真实 FFI 用）
#
# 第 3 份是 `.light` 文件里的内联 C 文本，与 h_c_hash.c 是**两个物理副本**——
# 这正是最容易随时间漂移的地方。所以本脚本把 `引 C:` 块从 mb_cffi.light 里
# 抽出来、现场编译成 .so，与 1、2 和一份**独立写的 Python 参照实现**四向对拍。
# 任何一处漂移都会让 build.sh 直接失败，而不是静默给出两条一样错的结果。
#
# 覆盖：ASCII / 中文（UTF-8 多字节）/ 长输入（跨 32 位符号位）/ 单字节。

set -u

HERE=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$HERE" || exit 1

CLI=handlers/h_c_hash
SO=handlers/libh_c_hash.so
CFFI=mb_cffi.light
[ -x "$CLI" ] || { echo "缺少 $CLI（先跑 build.sh）" >&2; exit 1; }
[ -f "$SO" ] || { echo "缺少 $SO（先跑 build.sh）" >&2; exit 1; }
[ -f "$CFFI" ] || { echo "缺少 $CFFI" >&2; exit 1; }

CC_BIN=""
for cand in cc gcc clang; do
    if command -v "$cand" >/dev/null 2>&1; then CC_BIN=$cand; break; fi
done

TMPDIR_MB=$(mktemp -d 2>/dev/null || echo /tmp/mb_selfcheck.$$)
mkdir -p "$TMPDIR_MB"
trap 'rm -rf "$TMPDIR_MB"' EXIT INT TERM

# ---- 从 mb_cffi.light 抽取 `引 C:` 块，编成独立 .so ------------------------ #
EXTRACTED_SO=""
if [ -n "$CC_BIN" ]; then
    python3 - "$CFFI" "$TMPDIR_MB/inline.c" <<'PY'
import re
import sys

src = open(sys.argv[1], encoding="utf-8").read().split("\n")
out, inblock, base = [], False, 0
for line in src:
    m = re.match(r"^(\s*)引\s+C\s*[:：]\s*$", line)
    if m:
        inblock, base = True, len(m.group(1))
        continue
    if inblock:
        if line.strip() == "":
            continue
        ind = len(line) - len(line.lstrip())
        if ind <= base:
            inblock = False
            continue
        out.append(line[base:])
if not out:
    sys.exit("mb_cffi.light 里找不到 引 C: 块")
body = "\n".join(out) + "\n"
if "mb_fnv1a32" not in body:
    sys.exit("引 C: 块里没有 mb_fnv1a32")
open(sys.argv[2], "w", encoding="utf-8").write(body)
PY
    if [ "$?" -eq 0 ] && "$CC_BIN" -shared -fPIC -O2 -o "$TMPDIR_MB/inline.so" \
            "$TMPDIR_MB/inline.c" >"$TMPDIR_MB/inline.log" 2>&1; then
        EXTRACTED_SO="$TMPDIR_MB/inline.so"
    else
        echo "从 mb_cffi.light 抽取的 引 C: 块编译失败，日志：" >&2
        cat "$TMPDIR_MB/inline.log" >&2 2>/dev/null
        exit 1
    fi
else
    echo "没有 C 编译器，跳过 引 C: 块对拍" >&2
fi

# ---- 四向对拍 ------------------------------------------------------------- #
python3 - "$CLI" "$SO" "$EXTRACTED_SO" <<'PY'
import ctypes
import pathlib
import subprocess
import sys

cli, so, inline_so = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ""

MASK64 = (1 << 64) - 1


def fnv1a32(data: bytes) -> int:
    """FNV-1a 64 位取低 32 位。独立写的规范实现，不复用仓库内任何一份代码，
    防止「三份错得一样」的假绿。"""
    h = 14695981039346656037
    for b in data:
        h ^= b
        h = (h * 1099511628211) & MASK64
    return h & 0xFFFFFFFF


def bind(path):
    """绑定 mb_fnv1a32；mb_fnv1a32_n 是**可选**符号——mb_cffi.light 的 引 C: 块
    只内联了主函数（B2 用不到定长版），缺它不算错，返回 None 表示「没这个符号」。"""
    lib = ctypes.CDLL(path)
    lib.mb_fnv1a32.restype = ctypes.c_longlong
    lib.mb_fnv1a32.argtypes = [ctypes.c_char_p]
    try:
        lib.mb_fnv1a32_n.restype = ctypes.c_longlong
        lib.mb_fnv1a32_n.argtypes = [ctypes.c_char_p, ctypes.c_longlong]
    except AttributeError:
        lib.mb_fnv1a32_n = None
    return lib


lib_so = bind(so)
lib_inline = bind(inline_so) if inline_so else None

CASES = [
    b"hello",
    "你好".encode("utf-8"),
    b'{"service":"hash","message":"hello"}',
    b"a" * 1000,
    ("汉" * 300).encode("utf-8"),
    b"x",
]

fails = 0
for case in CASES:
    want = fnv1a32(case)

    r = subprocess.run([cli], input=case + b"\n", capture_output=True)
    got_cli = None
    if r.returncode == 0:
        parts = r.stdout.split()
        if len(parts) == 2 and parts[0] == b"HASH":
            got_cli = int(parts[1])

    got_so = lib_so.mb_fnv1a32(case) & 0xFFFFFFFF
    got_so_n = (lib_so.mb_fnv1a32_n(case, len(case)) & 0xFFFFFFFF)
    got_inline_n = (lib_inline.mb_fnv1a32_n(case, len(case)) & 0xFFFFFFFF
                    if lib_inline and lib_inline.mb_fnv1a32_n else want)
    got_inline = (lib_inline.mb_fnv1a32(case) & 0xFFFFFFFF) if lib_inline else want

    ok = (got_cli == want and got_so == want and got_so_n == want
          and got_inline == want and got_inline_n == want)
    fails += 0 if ok else 1
    print(
        f"{'OK  ' if ok else 'FAIL'} len={len(case):4d} want={want:10d} "
        f"cli={got_cli} so={got_so} so_n={got_so_n} "
        f"inline={got_inline} inline_n={got_inline_n}"
    )

# 另外两个 handler 的独立抽查（不参与 B2，但同属 B1 契约）
r = subprocess.run(["./handlers/h_go_len/h_go_len"],
                   input=b'{"service":"measure"}\n', capture_output=True)
want_len = len(b'{"service":"measure"}')
got = r.stdout.decode().strip()
ok = (r.returncode == 0 and got == f"LEN {want_len}")
fails += 0 if ok else 1
print(f"{'OK  ' if ok else 'FAIL'} h_go_len want=LEN {want_len} got={got}")

# h_py_append 是**有状态**的（写 out.log），必须在独立临时目录里跑：
# 否则本脚本会给仓库根留下 out.log，下次 build 时计数从 OK 2 起，幂等性判据假红。
# 这正是「自测不得污染被测目录」的通用教训。
import tempfile

with tempfile.TemporaryDirectory(prefix="mb_h_py_append_") as tmp:
    script = str(pathlib.Path("handlers/h_py_append.py").resolve())
    r = subprocess.run([sys.executable, script],
                       input=b'{"service":"notes"}\n', capture_output=True, cwd=tmp)
    ok = r.returncode == 0 and r.stdout.strip() == b"OK 1"
    # 再跑一次，确认「落盘计数」语义：第二次应是 OK 2
    r2 = subprocess.run([sys.executable, script],
                        input=b'{"service":"notes"}\n', capture_output=True, cwd=tmp)
    ok = ok and r2.returncode == 0 and r2.stdout.strip() == b"OK 2"
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} h_py_append want=OK 1 then OK 2 "
          f"got={r.stdout.strip()!r} {r2.stdout.strip()!r}")

if fails:
    print(f"\n{fails} 组对拍失败", file=sys.stderr)
    sys.exit(1)
print("\n全部对拍通过")
PY
