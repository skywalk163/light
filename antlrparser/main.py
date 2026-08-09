"""
光明（Light）编程语言 - ANTLR 解析器入口

使用方法：
    python main.py <file.light>      # 解析文件
    python main.py -t <file.light>   # 仅词法分析，显示 Token 序列
    python main.py -                # 从标准输入读取
"""

import sys
import os
import json

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from light_parser.LightLangLexer import LightLangLexer
    from light_parser.LightLangParser import LightLangParser
    from light_parser.LightLangParserVisitor import LightLangParserVisitor
except ImportError:
    print("[错误] 无法导入 ANTLR 生成的解析器。")
    print("[提示] 请先运行: cd antlrparser && scripts\\generate.ps1")
    sys.exit(1)

from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener

from light_visitor import LightLangASTBuilder, LightLangErrorListener, parse_source, parse_file

from light_tokenizer import LightLangTokenizer


def tokenize_only(source: str):
    """仅进行词法分析，输出 Token 序列（使用自定义中文分词器）"""
    tokenizer = LightLangTokenizer()
    tokens = tokenizer.tokenize(source)

    print(f"{'类型':<25} {'文本':<15} {'行':<5} {'列':<5}")
    print("-" * 50)

    for token in tokens:
        if token.type_name == 'EOF':
            continue
        print(f"{token.type_name:<25} {token.text:<15} {token.line:<5} {token.column:<5}")

    if tokenizer.errors:
        print("\n[词法错误]:")
        for err in tokenizer.errors:
            print(f"  {err}")
        return False
    return True


def print_ast(node, indent: int = 0):
    """打印 AST（调试用）"""
    prefix = "  " * indent
    if hasattr(node, '__dataclass_fields__'):
        node_type = node.__class__.__name__
        fields = {}
        for field_name in node.__dataclass_fields__:
            value = getattr(node, field_name)
            if value is None or (isinstance(value, list) and len(value) == 0):
                continue
            if isinstance(value, (int, float, str, bool)):
                fields[field_name] = value
        if fields:
            print(f"{prefix}{node_type}: {fields}")
        else:
            print(f"{prefix}{node_type}")
        
        for field_name in node.__dataclass_fields__:
            value = getattr(node, field_name)
            if isinstance(value, list):
                for item in value:
                    if hasattr(item, '__dataclass_fields__'):
                        print_ast(item, indent + 1)
            elif hasattr(value, '__dataclass_fields__'):
                print_ast(value, indent + 1)
    else:
        print(f"{prefix}{node}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n示例:")
        print("  python main.py test/sample_quicksort.light")
        print("  python main.py -t test/sample_basic.light")
        sys.exit(1)

    mode = 'parse'
    source_file = None

    args = sys.argv[1:]
    if args[0] == '-t':
        mode = 'tokenize'
        args = args[1:]
    elif args[0] == '-a':
        mode = 'ast'
        args = args[1:]

    if args[0] == '-':
        source = sys.stdin.read()
        source_file = "<stdin>"
    else:
        source_file = args[0]
        if not os.path.exists(source_file):
            print(f"[错误] 文件不存在: {source_file}")
            sys.exit(1)
        with open(source_file, 'r', encoding='utf-8') as f:
            source = f.read()

    print(f"=== 光明 ANTLR 解析器 ===")
    print(f"文件: {source_file}")
    print(f"大小: {len(source)} 字符\n")

    if mode == 'tokenize':
        success = tokenize_only(source)
        sys.exit(0 if success else 1)

    # 解析并构建 AST
    module = parse_source(source)

    if module is None:
        print("[错误] 解析失败")
        sys.exit(1)

    if mode == 'ast':
        print("=== AST ===")
        print_ast(module)
    else:
        print(f"解析成功！")
        print(f"  段落数: {len(module.segments)}")
        print(f"  语句数: {len(module.statements)}")
        print(f"  导入数: {len(module.imports)}")
        print(f"  导出数: {len(module.exports)}")

        if module.name:
            print(f"  模块名: {module.name}")

        if module.segments:
            print(f"\n段落列表:")
            for seg in module.segments:
                params = ", ".join(p.name for p in seg.parameters)
                ret = f" -> {seg.return_type}" if seg.return_type else ""
                print(f"  - 《{seg.name}》段({params}){ret}")

    print("\n完成。")


if __name__ == '__main__':
    main()