# 光明（Light）CLI 工具包
"""
本包提供光明语言的命令行工具：
- light.py: 主命令行入口
- light_unified.py: 统一编译器 CLI（支持 antlr/src 双后端）
- lightc.py: 编译运行工具

用法：
    python -m cli.light_unified <源文件> [--target antlr|src] [--output <输出>]
    python cli/lightc.py <源文件> --run
"""