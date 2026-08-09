"""
光明（Light）编程语言 - 手写递归下降解析器实现

本包提供纯 Python 实现的手写编译器后端：
- parser_stmt.py: 语句解析器（递归下降）
- lexer.py: 词法分析器
- ast_nodes.py: AST 节点定义
- compiler.py: 编译器主体（包含 AST 适配器）
- codegen.py: Python 代码生成

支持语法版本：3.x（纯缩进语法，无结束关键字）

特点：轻量级、无外部依赖（仅需 antlr4-runtime 用于共享 AST 类型）
"""

__version__ = "6.0.0"
