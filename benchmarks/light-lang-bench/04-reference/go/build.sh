#!/bin/sh
# MiniLog Go 参考实现构建脚本（幂等，可重复执行）。
# 用法：在 benchmarks/light-lang-bench 目录下执行 `sh 04-reference/go/build.sh`，
# 也可直接 `sh build.sh`；产物为同目录下的可执行文件 `minilog`。
cd "$(dirname "$0")" || exit 1
go build -o minilog minilog.go
