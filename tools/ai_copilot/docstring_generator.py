"""
光明（Light）编程语言 - 文档注释生成器

功能：
  读取一个 .duan 文件，使用 lexer + parser 解析，
  为每个段落（函数）定义自动生成中文文档注释。
  注释包含：功能描述模板、参数说明、返回值说明。

用法：
  python tools/ai_copilot/docstring_generator.py <file.duan>
  python tools/ai_copilot/docstring_generator.py <file.duan> --stdout   # 输出到标准输出
"""

import sys
import os
from typing import List, Optional, Dict

# 添加 src 到路径
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, '..', '..'))
_SRC_DIR = os.path.join(_PROJECT_DIR, 'src')
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from light_parser_v3 import LightParser, ParseError
from ast_nodes_v3 import (
    ASTNode, Module, Paragraph, VarDecl, IfStmt, ForeachStmt, WhileStmt,
    ReturnStmt, BreakStmt, ContinueStmt, BinaryOp, UnaryOp, NumberLiteral,
    StringLiteral, Identifier, ParagraphCall, FunctionCallExpr, ClassDefinition,
    MethodDefinition, TryStmt, ThrowStmt, ImportStmt, ExportStmt,
    WithStmt, MatchStmt, MatchCase, InterfaceDefinition,
)


# =============================================================================
# AST 遍历
# =============================================================================

def find_paragraphs(node: ASTNode) -> List[Paragraph]:
    """递归遍历 AST，收集所有 Paragraph 定义"""
    paragraphs = []

    def _walk(n):
        if n is None:
            return
        if isinstance(n, Paragraph):
            paragraphs.append(n)
        elif isinstance(n, Module):
            for stmt in getattr(n, 'statements', []) or []:
                _walk(stmt)
        elif isinstance(n, ClassDefinition):
            for stmt in getattr(n, 'body', []) or []:
                _walk(stmt)
            for stmt in getattr(n, 'methods', []) or []:
                _walk(stmt)
        elif isinstance(n, IfStmt):
            for stmt in getattr(n, 'then_body', []) or []:
                _walk(stmt)
            for stmt in getattr(n, 'else_body', []) or []:
                _walk(stmt)
        elif isinstance(n, TryStmt):
            for stmt in getattr(n, 'body', []) or []:
                _walk(stmt)
            for handler in getattr(n, 'handlers', []) or []:
                for stmt in getattr(handler, 'body', []) or []:
                    _walk(stmt)
            for stmt in getattr(n, 'final_body', []) or []:
                _walk(stmt)
        elif isinstance(n, (ForeachStmt, WhileStmt, WithStmt)):
            for stmt in getattr(n, 'body', []) or []:
                _walk(stmt)
        elif isinstance(n, MatchStmt):
            for case in getattr(n, 'cases', []) or []:
                for stmt in getattr(case, 'body', []) or []:
                    _walk(stmt)
        elif isinstance(n, MatchCase):
            for stmt in getattr(n, 'body', []) or []:
                _walk(stmt)
        elif isinstance(n, InterfaceDefinition):
            for stmt in getattr(n, 'methods', []) or []:
                _walk(stmt)
        elif isinstance(n, MethodDefinition):
            for stmt in getattr(n, 'body', []) or []:
                _walk(stmt)

    _walk(node)
    return paragraphs


# =============================================================================
# 文档注释生成
# =============================================================================

def _ast_node_to_text(node: ASTNode) -> str:
    """将 AST 节点转换为简短的文本描述"""
    if node is None:
        return ''
    if isinstance(node, NumberLiteral):
        return str(node.value)
    if isinstance(node, StringLiteral):
        return f'"{node.value}"'
    if isinstance(node, Identifier):
        return node.name
    if isinstance(node, BinaryOp):
        return f'{_ast_node_to_text(node.left)} {node.operator} {_ast_node_to_text(node.right)}'
    if isinstance(node, UnaryOp):
        return f'{node.operator}{_ast_node_to_text(node.operand)}'
    if isinstance(node, ParagraphCall):
        return f'{node.name}(...)'
    if isinstance(node, FunctionCallExpr):
        return f'{node.name}(...)'
    if isinstance(node, ReturnStmt):
        return f'返回 {_ast_node_to_text(node.value)}'
    if isinstance(node, VarDecl):
        return f'{node.name} = {_ast_node_to_text(node.value)}'
    return type(node).__name__


def _infer_return_description(para: Paragraph) -> str:
    """根据函数体推断返回值描述"""
    has_return = False
    return_values = set()

    def _walk(n):
        nonlocal has_return
        if n is None:
            return
        if isinstance(n, ReturnStmt):
            has_return = True
            if n.value is not None:
                text = _ast_node_to_text(n.value)
                if text:
                    return_values.add(text)
        elif isinstance(n, (IfStmt, ForeachStmt, WhileStmt, TryStmt, WithStmt, MatchStmt)):
            for child in getattr(n, 'body', []) or []:
                _walk(child)
            for child in getattr(n, 'else_body', []) or []:
                _walk(child)
            if isinstance(n, TryStmt):
                for handler in getattr(n, 'handlers', []) or []:
                    for child in getattr(handler, 'body', []) or []:
                        _walk(child)
                for child in getattr(n, 'final_body', []) or []:
                    _walk(child)

    for stmt in para.body:
        _walk(stmt)

    if not has_return:
        return '无返回值'
    if para.return_type:
        return f'返回 {para.return_type} 类型的结果'
    return '返回计算结果'


def generate_docstring(para: Paragraph, lines: List[str]) -> List[str]:
    """
    为段落生成文档注释。

    返回注释行列表（不含 # 前缀，调用方负责添加）。
    """
    doc_lines = []

    # 函数描述
    doc_lines.append(f'{para.name} - 功能描述')

    # 参数描述
    if para.params:
        doc_lines.append('')
        doc_lines.append('参数：')
        for p in para.params:
            param_name = p.get('name', '?') if isinstance(p, dict) else str(p)
            param_type = p.get('type', '任意') if isinstance(p, dict) and p.get('type') else '任意'
            doc_lines.append(f'  {param_name} ({param_type}): 参数描述')
    else:
        doc_lines.append('')
        doc_lines.append('参数：无')

    # 返回值描述
    doc_lines.append('')
    doc_lines.append(f'返回：{_infer_return_description(para)}')

    return doc_lines


def format_docstring_comment(doc_lines: List[str], indent: str = '') -> str:
    """将文档注释行格式化为带 # 前缀的注释块"""
    if not doc_lines:
        return ''
    comment_lines = []
    comment_lines.append(f'{indent}# {doc_lines[0]}')
    for line in doc_lines[1:]:
        if line.strip():
            comment_lines.append(f'{indent}# {line}')
        else:
            comment_lines.append(f'{indent}#')
    return '\n'.join(comment_lines)


# =============================================================================
# 主流程
# =============================================================================

def process_file(filepath: str, to_stdout: bool = False) -> Optional[str]:
    """处理单个 .duan 文件，生成带文档注释的版本"""
    if not os.path.exists(filepath):
        print(f"错误: 文件不存在: {filepath}", file=sys.stderr)
        return None

    # 读取源文件
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    lines = source.split('\n')

    # 解析（parser.parse 内部会调用 lexer 进行词法分析）
    parser = LightParser()
    try:
        ast = parser.parse(source)
    except Exception as e:
        print(f"解析错误: {e}", file=sys.stderr)
        return None

    # 收集所有段落
    paragraphs = find_paragraphs(ast)
    if not paragraphs:
        print("警告: 未找到任何段落定义", file=sys.stderr)

    if to_stdout:
        # 输出到 stdout
        return _insert_docstrings(source, lines, paragraphs)

    # 写入回原文件
    new_source = _insert_docstrings(source, lines, paragraphs)
    if new_source == source:
        print("未检测到需要插入文档注释的段落。")
        return None

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_source)
    print(f"已更新: {filepath}")
    return new_source


def _find_para_line(lines: List[str], para_name: str) -> Optional[int]:
    """在源文件中查找段落定义所在的行号（0-based）"""
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 匹配: 段落 名称 或 函数 名称 或 异步 段落 名称
        if stripped.startswith(('段落', '函数')):
            # 跳过 "段落" 或 "函数" 关键字，检查名称
            rest = stripped[2:].strip()
            # 如果 rest 以 para_name 开头
            if rest.startswith(para_name):
                # 确保后面是 接收、：、: 或空格
                after = rest[len(para_name):].strip()
                if after.startswith(('接收', '：', ':', '参数')):
                    return i
        # 匹配: 异步 段落 名称
        elif stripped.startswith('异步'):
            rest = stripped[2:].strip()
            if rest.startswith(('段落', '函数')):
                rest2 = rest[2:].strip()
                if rest2.startswith(para_name):
                    after = rest2[len(para_name):].strip()
                    if after.startswith(('接收', '：', ':', '参数')):
                        return i
    return None


def _insert_docstrings(source: str, lines: List[str], paragraphs: List[Paragraph]) -> str:
    """在源文件中插入文档注释"""
    if not paragraphs:
        return source

    # 收集每个段落及其行号，按行号从大到小排序
    para_line_pairs = []  # List of (line_0based, Paragraph)
    for para in paragraphs:
        line_no = _find_para_line(lines, para.name)
        if line_no is not None:
            para_line_pairs.append((line_no, para))

    # 按行号从大到小排序，这样从后往前插入不会破坏行号
    para_line_pairs.sort(key=lambda x: x[0], reverse=True)

    result_lines = list(lines)  # 复制一份

    for para_line_0based, para in para_line_pairs:
        # 计算缩进
        line_text = result_lines[para_line_0based] if para_line_0based < len(result_lines) else ''
        indent = ''
        for ch in line_text:
            if ch in ' \t':
                indent += ch
            else:
                break

        # 检查该行前面是否已有文档注释
        has_existing_doc = False
        check_line = para_line_0based - 1
        while check_line >= 0:
            prev_line = result_lines[check_line].strip()
            if prev_line == '':
                check_line -= 1
                continue
            if prev_line.startswith('#'):
                has_existing_doc = True
            break

        if has_existing_doc:
            continue  # 已有注释，跳过

        # 生成文档注释
        doc_lines = generate_docstring(para, lines)
        comment_block = format_docstring_comment(doc_lines, indent)

        # 插入注释（在段落定义行之前插入空行 + 注释）
        insertion = comment_block + '\n'
        result_lines.insert(para_line_0based, insertion)

    return '\n'.join(result_lines)


# =============================================================================
# 命令行入口
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        print(f"用法: python {os.path.basename(__file__)} <file.duan> [--stdout]", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    to_stdout = '--stdout' in sys.argv

    if not os.path.exists(filepath):
        print(f"错误: 文件不存在: {filepath}", file=sys.stderr)
        sys.exit(1)

    if not filepath.endswith(('.light', '.duan')):
        print(f"警告: 文件后缀不是 .light/.duan，仍将继续处理: {filepath}", file=sys.stderr)

    result = process_file(filepath, to_stdout=to_stdout)
    if result is None:
        sys.exit(1)

    if to_stdout:
        print(result)


if __name__ == '__main__':
    main()