# -*- coding: utf-8 -*-
"""
光明 LSP 服务器入口点

支持 --stdio 模式，通过标准输入输出进行 LSP 通信。
"""

import sys
import os
import argparse

# 将项目 src 目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_lsp import run_stdio_server, create_language_server


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description='光明 LSP 服务器')
    parser.add_argument('--stdio', action='store_true', help='通过 stdio 通信')
    parser.add_argument('--version', action='store_true', help='显示版本信息')

    args = parser.parse_args()

    if args.version:
        print('光明 LSP 服务器 v5.0.0')
        return

    if args.stdio:
        # 标准输入输出 LSP 通信模式
        run_stdio_server()
    else:
        # 默认使用 stdio 模式
        run_stdio_server()


if __name__ == '__main__':
    main()