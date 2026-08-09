"""
光明（Light）编程语言 - ANTLR 解析器包

本包提供基于 ANTLR4 的解析器和编译器实现：
- light_lexer.py / light_tokenizer.py: 词法分析器
- light_parser.py / LightLangParser.py: ANTLR 生成的语法分析器
- light_visitor.py / light_ast.py: AST 节点定义和访问器
- llvm_codegen.py / llvm_core.py: LLVM IR 代码生成
- light_llvm.py: LLVM 编译流程入口
- cli.py / light_cli.py: 命令行工具

支持语法版本：1.x（需结束关键字）、2.x（混合语法）、3.x（纯缩进语法）

确保包内模块间的扁平导入（from light_ast import xxx）在作为 pip 包安装后也能正常工作。
"""
import sys
import os

# 将包目录加入 sys.path，使 flat imports 在包内有效
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)