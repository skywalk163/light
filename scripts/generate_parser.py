#!/usr/bin/env python3
"""
光明（Light）编程语言 - ANTLR4解析器代码生成脚本

使用方法：
  python scripts/generate_parser.py

依赖：
  pip install antlr4-tools
"""

import os
import subprocess
import sys
from pathlib import Path

def check_antlr():
    """检查ANTLR4是否安装"""
    try:
        result = subprocess.run(['antlr4', '-version'], capture_output=True, text=True)
        print(f"✓ ANTLR4已安装: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("✗ ANTLR4未安装")
        print("\n安装方法：")
        print("  pip install antlr4-tools")
        print("\n或手动安装：")
        print("  1. 下载ANTLR4 jar: https://www.antlr.org/download/antlr-4.13.1-complete.jar")
        print("  2. 创建别名: alias antlr4='java -jar antlr-4.13.1-complete.jar'")
        return False

def generate_parser():
    """生成解析器代码"""
    antlr_dir = Path(__file__).parent.parent / 'antlrparser'
    
    print("\n生成词法分析器...")
    lexer_cmd = [
        'antlr4',
        '-Dlanguage=Python3',
        '-visitor',
        '-no-listener',
        str(antlr_dir / 'LightLangLexer.g4')
    ]
    
    result = subprocess.run(lexer_cmd, cwd=antlr_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"✗ 词法分析器生成失败:\n{result.stderr}")
        return False
    print("✓ 词法分析器生成成功")
    
    print("\n生成语法分析器...")
    parser_cmd = [
        'antlr4',
        '-Dlanguage=Python3',
        '-visitor',
        '-no-listener',
        str(antlr_dir / 'LightLangParser.g4')
    ]
    
    result = subprocess.run(parser_cmd, cwd=antlr_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"✗ 语法分析器生成失败:\n{result.stderr}")
        return False
    print("✓ 语法分析器生成成功")
    
    # 生成完整语法（合并Lexer和Parser）
    print("\n生成完整语法...")
    full_cmd = [
        'antlr4',
        '-Dlanguage=Python3',
        '-visitor',
        '-no-listener',
        str(antlr_dir / 'LightLang.g4')
    ]
    
    result = subprocess.run(full_cmd, cwd=antlr_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"✗ 完整语法生成失败:\n{result.stderr}")
        return False
    print("✓ 完整语法生成成功")
    
    print("\n所有解析器代码生成完成！")
    return True

def main():
    print("光明编程语言 - ANTLR4解析器代码生成")
    print("=" * 60)
    
    if not check_antlr():
        sys.exit(1)
    
    if not generate_parser():
        sys.exit(1)
    
    print("\n下一步：")
    print("  1. 运行测试: python -m pytest antlrparser/test/")
    print("  2. 编译示例: python light_compile.py test_import.light")

if __name__ == '__main__':
    main()
