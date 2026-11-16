#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MiniBridge · h_py_append（B1 handler，Python）

契约（见 ../规格.md §3.1）：
  输入：stdin 一行 JSON 记录（UTF-8，行尾 `\n`）。
  行为：把该行**原样**追加到 out.log（追加写，每个记录后必有 `\n`）。
  输出：stdout 单行 `OK <累计行数>\\n`；累计行数是 out.log 中当前的记录条数。
  失败：任何异常 → stderr 一行 `ERR <原因>`，退出码 1（不写 out.log）。

设计约束（规格 §3.4）：
  - 不解析 JSON：handler 只做「有状态、落盘」，不做业务计算，避免把 JSON
    解析能力混进「进程编排」的度量里。
  - 计数以 out.log 的真实行数为准，而不是内存计数器：这样进程每次重启
    （B1 每条记录都起一个新进程）也能得到正确的累计值。
"""

import os
import sys

OUT_NAME = "out.log"


def main() -> int:
    raw = sys.stdin.buffer.read()
    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
    if not line.strip():
        sys.stderr.write("ERR empty_input\n")
        return 1

    path = os.path.join(os.getcwd(), OUT_NAME)
    try:
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            count = sum(1 for _ in f)
    except OSError as exc:
        sys.stderr.write(f"ERR io: {exc}\n")
        return 1

    sys.stdout.write(f"OK {count}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
