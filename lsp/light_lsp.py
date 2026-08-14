# -*- coding: utf-8 -*-
"""
光明编程语言 - Language Server Protocol (LSP) 实现

提供 VS Code 等编辑器的智能提示支持。
"""

import sys
import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer, LexerError
from light_parser_v3 import LightParser, ParseError, ASTNode
from keywords import ALL_KEYWORDS, VERB_ARITY, STDLIB_VERB_ARITY, BUILTIN_TYPES

# 尝试导入 lightpub 包索引
_LIGHTPUB_PACKAGES = []
try:
    from stdlib.lightpub.__index__ import PACKAGES as _LIGHTPUB_PKG_MAP
    _LIGHTPUB_PACKAGES = sorted(_LIGHTPUB_PKG_MAP.keys())
except ImportError:
    pass


# =============================================================================
# LSP 常量
# =============================================================================

LSP_METHODS = {
    # 初始化
    'initialize': 'initialize',
    'initialized': 'initialized',
    'shutdown': 'shutdown',
    'exit': 'exit',
    
    # 文本文档
    'textDocument/didOpen': 'textDocument/didOpen',
    'textDocument/didChange': 'textDocument/didChange',
    'textDocument/didClose': 'textDocument/didClose',
    'textDocument/didSave': 'textDocument/didSave',
    
    # 诊断
    'textDocument/publishDiagnostics': 'textDocument/publishDiagnostics',
    
    # 代码补全
    'textDocument/completion': 'textDocument/completion',
    'completionItem/resolve': 'completionItem/resolve',
    
    # 悬停
    'textDocument/hover': 'textDocument/hover',
    
    # 跳转定义
    'textDocument/definition': 'textDocument/definition',
    'textDocument/typeDefinition': 'textDocument/typeDefinition',
    'textDocument/declaration': 'textDocument/declaration',
    
    # 查找引用
    'textDocument/references': 'textDocument/references',
    
    # 文档符号
    'textDocument/documentSymbol': 'textDocument/documentSymbol',
    
    # 格式化
    'textDocument/formatting': 'textDocument/formatting',
    'textDocument/rangeFormatting': 'textDocument/rangeFormatting',
    
    # 光标位置
    'textDocument/documentHighlight': 'textDocument/documentHighlight',
    
    # 语义令牌
    'textDocument/semanticTokens/full': 'textDocument/semanticTokens/full',
    
    # LSP 3.17+ 拉取式诊断
    'textDocument/diagnostic': 'textDocument/diagnostic',
}


# =============================================================================
# 中文友好错误消息
# =============================================================================

# 常见 LSP 错误码及其中文翻译
LSP_ERROR_MESSAGES_ZH = {
    -32700: "解析错误: JSON 格式无效，请检查语法",
    -32600: "请求无效: 消息结构不正确",
    -32601: "方法未找到: 不支持该操作",
    -32602: "参数无效: 函数参数不匹配",
    -32603: "内部错误: 服务器处理请求时发生异常",
    -32000: "请求已取消",
    -32001: "内容已修改",
    -32002: "请求已过期",
}

# 光明语法错误中文翻译
LIGHT_ERROR_MESSAGES_ZH = {
    "unexpected token": "意外的标记，请检查语法",
    "unexpected indent": "缩进不正确，请检查对齐",
    "unexpected dedent": "缩进减少不正确",
    "invalid syntax": "语法无效",
    "name not defined": "名称未定义，请先使用「设」或「定义」声明变量",
    "undefined variable": "变量未定义，请先声明",
    "expected expression": "需要表达式",
    "expected statement": "需要语句",
    "expected identifier": "需要标识符（变量名或函数名）",
    "expected keyword": "需要关键字",
    "keyword expected": "需要关键字",
    "missing colon": "缺少冒号「：」，条件/循环/函数定义后需要冒号",
    "missing period": "缺少句号「。」，语句结束需要句号",
    "unclosed string": "字符串未闭合，缺少引号",
    "invalid character": "无效字符",
    "division by zero": "除数不能为零",
    "type mismatch": "类型不匹配",
    "argument mismatch": "参数数量不匹配",
    "too many arguments": "参数过多",
    "too few arguments": "参数过少",
    "function not defined": "函数未定义",
    "module not found": "模块未找到，请检查导入路径",
    "import error": "导入错误，请检查模块名是否正确",
    "recursion depth exceeded": "递归深度超过限制",
    "index out of range": "索引超出范围",
    "key not found": "键不存在于字典中",
    "attribute not found": "属性不存在",
}


def translate_error_message(msg: str) -> str:
    """将英文错误消息翻译为中文"""
    # 完全匹配
    lower_msg = msg.lower()
    for eng, zh in LIGHT_ERROR_MESSAGES_ZH.items():
        if eng in lower_msg:
            return zh

    # 部分匹配 - 常见错误模式
    patterns = [
        ("未定义", "未定义"),
        ("没有定义", "未定义"),
        ("is not defined", "未定义"),
        ("cannot import", "无法导入"),
        ("no module", "模块不存在"),
        ("module", "模块"),
        ("syntax", "语法"),
        ("indent", "缩进"),
        ("colon", "缺少冒号"),
        ("period", "缺少句号"),
        ("string", "字符串"),
        ("type", "类型"),
    ]
    for eng, zh in patterns:
        if eng in lower_msg:
            return f"{zh}: {msg}"

    return msg


def format_lsp_error_zh(code: int) -> str:
    """获取 LSP 错误码的中文描述"""
    return LSP_ERROR_MESSAGES_ZH.get(code, f"未知错误 (代码: {code})")


# =============================================================================
# LSP 响应构建器
# =============================================================================

def lsp_response(id: Any, result: Any) -> Dict:
    """构建 LSP 响应"""
    return {
        'jsonrpc': '2.0',
        'id': id,
        'result': result
    }


def lsp_error(id: Any, code: int, message: str) -> Dict:
    """构建 LSP 错误响应（中文友好）"""
    # 翻译错误消息
    zh_msg = translate_error_message(message)
    # 如果原始消息不是中文，添加中文翻译
    if zh_msg == message:
        zh_from_code = format_lsp_error_zh(code)
        if zh_from_code and "未知错误" not in zh_from_code:
            zh_msg = f"{zh_from_code}: {message}"

    return {
        'jsonrpc': '2.0',
        'id': id,
        'error': {
            'code': code,
            'message': zh_msg
        }
    }


def lsp_notification(method: str, params: Dict) -> Dict:
    """构建 LSP 通知"""
    return {
        'jsonrpc': '2.0',
        'method': method,
        'params': params
    }


# =============================================================================
# 文档管理器
# =============================================================================

class Document:
    """LSP 文档"""
    def __init__(self, uri: str, text: str):
        self.uri = uri
        self.text = text
        self.lines = text.split('\n')
        self.version = 1
        
    def update(self, changes: List[Dict]):
        """更新文档内容"""
        for change in changes:
            range_info = change.get('range')
            if range_info:
                start_line = range_info['start']['line']
                start_char = range_info['start']['character']
                end_line = range_info['end']['line']
                end_char = range_info['end']['character']
                
                # 应用更改
                start_offset = sum(len(self.lines[i]) + 1 for i in range(start_line)) + start_char
                end_offset = sum(len(self.lines[i]) + 1 for i in range(end_line)) + end_char
                
                self.text = self.text[:start_offset] + change['text'] + self.text[end_offset:]
            else:
                # 整个文档替换
                self.text = change.get('text', '')
            
            self.lines = self.text.split('\n')
            self.version += 1
    
    def get_line(self, line: int) -> str:
        """获取指定行"""
        if 0 <= line < len(self.lines):
            return self.lines[line]
        return ''
    
    def get_position(self, line: int, character: int) -> int:
        """将 (line, character) 转换为字符偏移"""
        offset = 0
        for i in range(min(line, len(self.lines))):
            offset += len(self.lines[i]) + 1
        return offset + min(character, len(self.lines[line]) if line < len(self.lines) else 0)


class DocumentManager:
    """文档管理器"""
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.symbols: Dict[str, List] = {}  # uri -> symbols
        self.definitions: Dict[str, Dict] = {}  # uri -> {name: location}
        self.type_info: Dict[str, Dict] = {}  # uri -> {name: type_str}

    def open_document(self, uri: str, text: str):
        """打开文档"""
        doc = Document(uri, text)
        self.documents[uri] = doc
        self._analyze_document(doc)

    def update_document(self, uri: str, changes: List[Dict]):
        """更新文档"""
        if uri in self.documents:
            self.documents[uri].update(changes)
            self._analyze_document(self.documents[uri])

    def close_document(self, uri: str):
        """关闭文档"""
        self.documents.pop(uri, None)
        self.symbols.pop(uri, None)
        self.definitions.pop(uri, None)
        self.type_info.pop(uri, None)
    
    def get_document(self, uri: str) -> Optional[Document]:
        """获取文档"""
        return self.documents.get(uri)
    
    def _analyze_document(self, doc: Document):
        """分析文档，提取符号、定义和类型信息"""
        try:
            parser = LightParser()
            ast = parser.parse(doc.text)

            self.symbols[doc.uri] = self._extract_symbols(ast, doc)
            self.definitions[doc.uri] = self._extract_definitions(ast, doc)

            # 类型推断
            try:
                from type_inferencer import TypeInferencer
                inferencer = TypeInferencer()
                inferencer.infer(ast)
                self.type_info[doc.uri] = self._extract_type_info(ast, inferencer)
            except Exception:
                self.type_info[doc.uri] = {}

        except Exception:
            pass

    # ------------------------------------------------------------------
    # AST 遍历辅助
    # ------------------------------------------------------------------

    _AST_CHILD_ATTRS = {
        'Module':      ('statements',),
        'VarDecl':     ('value',),
        'IfStmt':      ('condition', 'then_body', 'else_body'),
        'ForeachStmt': ('iterable', 'body'),
        'WhileStmt':   ('condition', 'body'),
        'Paragraph':   ('body',),
        'ReturnStmt':  ('value',),
        'ThrowStmt':   ('value',),
        'BinaryOp':    ('left', 'right'),
        'UnaryOp':     ('operand',),
        'Pipeline':    ('stages',),
        'ClassDefinition': ('attributes', 'methods'),
        'MethodDefinition': ('body',),
        'TryStmt':     ('try_body', 'catch_clauses', 'catch_body', 'finally_body'),
        'MatchStmt':   ('subject', 'cases'),
        'MatchCase':   ('body',),
        'WithStmt':    ('context_expr', 'body'),
        'LambdaExpression': ('body',),
        'DestructuringAssignment': ('value',),
        'CompoundAssignment': ('value',),
        'IndexedAssignment': ('index', 'value'),
        'SelfAssignment': ('value',),
        'ConditionalExpression': ('condition', 'then_expr', 'else_expr'),
        'MemberAccess': ('obj',),
        'IndexAccess':  ('obj', 'index'),
        'ListLiteral':  ('elements',),
        'TupleLiteral': ('elements',),
        'DictLiteral':  ('entries',),
        'ListComprehension': ('iterable', 'expression', 'condition'),
        'SetComprehension':  ('iterable', 'expression', 'condition'),
        'DictComprehension': ('iterable', 'key_expr', 'value_expr', 'condition'),
        'ClassInstantiation': ('args',),
        'FunctionCallExpr': ('callee', 'args'),
        'ParagraphCall': ('args',),
        'DecoratorDefinition': ('paragraph',),
    }

    def _walk_ast(self, node, callback):
        """遍历 AST 节点树，对每个节点调用 callback(node)"""
        if node is None:
            return
        callback(node)
        node_type = type(node).__name__
        for attr_name in self._AST_CHILD_ATTRS.get(node_type, ()):
            try:
                child = getattr(node, attr_name, None)
                if child is None:
                    continue
                if isinstance(child, list):
                    for item in child:
                        if isinstance(item, ASTNode):
                            self._walk_ast(item, callback)
                elif isinstance(child, ASTNode):
                    self._walk_ast(child, callback)
            except Exception:
                pass

    def _extract_type_info(self, ast, inferencer) -> Dict:
        """提取变量/函数的类型信息"""
        info = {}

        def collect(node):
            node_type = type(node).__name__
            name = getattr(node, 'name', None)
            if name and node_type in ('VarDecl', 'Paragraph', 'ClassDefinition', 'MethodDefinition',
                                       'AttributeDeclaration'):
                ta = getattr(node, 'type_annotation', None)
                if ta:
                    info[str(name)] = str(ta)
                else:
                    if node_type == 'VarDecl':
                        value = getattr(node, 'value', None)
                        if value and inferencer:
                            inferred = inferencer.type_cache.get(id(value))
                            if inferred:
                                info[str(name)] = str(inferred)

        self._walk_ast(ast, collect)
        return info

    def _extract_symbols(self, ast, doc) -> List[Dict]:
        """提取文档符号"""
        symbols = []

        def collect(node):
            node_type = type(node).__name__
            if node_type not in ('Paragraph', 'ClassDefinition', 'MethodDefinition', 'VarDecl',
                                  'AttributeDeclaration', 'InterfaceDefinition'):
                return

            line = getattr(node, 'line', 1) - 1
            name = getattr(node, 'name', '?')
            col = getattr(node, 'col', 0)

            if node_type == 'Paragraph':
                params = getattr(node, 'params', [])
                param_strs = []
                for p in params:
                    if isinstance(p, dict):
                        param_strs.append(p.get('name', '?'))
                    elif hasattr(p, 'name'):
                        param_strs.append(p.name)
                    else:
                        param_strs.append(str(p))
                detail = f"({', '.join(param_strs)})"
                symbols.append({
                    'name': name,
                    'kind': 12,  # Function
                    'detail': detail,
                    'range': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    },
                    'selectionRange': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    }
                })
            elif node_type == 'ClassDefinition':
                symbols.append({
                    'name': name,
                    'kind': 5,  # Class
                    'detail': '类',
                    'range': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    },
                    'selectionRange': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    }
                })
            elif node_type == 'MethodDefinition':
                params = getattr(node, 'parameters', [])
                param_strs = [p.name if hasattr(p, 'name') else str(p) for p in params]
                detail = f"({', '.join(param_strs)})"
                symbols.append({
                    'name': name,
                    'kind': 12,  # Function
                    'detail': detail,
                    'range': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    },
                    'selectionRange': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    }
                })
            elif node_type == 'VarDecl':
                symbols.append({
                    'name': name,
                    'kind': 6,  # Variable
                    'detail': '变量',
                    'range': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    },
                    'selectionRange': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    }
                })
            elif node_type == 'AttributeDeclaration':
                symbols.append({
                    'name': name,
                    'kind': 6,  # Variable
                    'detail': '属性',
                    'range': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    },
                    'selectionRange': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    }
                })
            elif node_type == 'InterfaceDefinition':
                symbols.append({
                    'name': name,
                    'kind': 5,  # Class
                    'detail': '接口',
                    'range': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    },
                    'selectionRange': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': col + len(name)}
                    }
                })

        self._walk_ast(ast, collect)
        return symbols

    def _extract_definitions(self, ast, doc) -> Dict:
        """提取定义位置，供跳转定义使用"""
        definitions = {}

        def collect(node):
            node_type = type(node).__name__
            if node_type not in ('Paragraph', 'ClassDefinition', 'MethodDefinition', 'VarDecl',
                                  'AttributeDeclaration', 'InterfaceDefinition'):
                return

            line = getattr(node, 'line', 1) - 1
            col = getattr(node, 'col', 0)
            name = getattr(node, 'name', None)
            if not name:
                return

            definitions[name] = {
                'uri': doc.uri,
                'range': {
                    'start': {'line': line, 'character': col},
                    'end': {'line': line, 'character': col + len(str(name))}
                }
            }

            # 额外保存节点信息用于悬停
            if node_type == 'Paragraph':
                params = getattr(node, 'params', [])
                param_strs = []
                for p in params:
                    if isinstance(p, dict):
                        param_strs.append(p.get('name', '?'))
                    elif hasattr(p, 'name'):
                        param_strs.append(p.name)
                    else:
                        param_strs.append(str(p))
                definitions[name + '__info'] = {
                    'type': '函数',
                    'params': param_strs,
                    'line': line,
                    'col': col
                }
            elif node_type == 'MethodDefinition':
                params = getattr(node, 'parameters', [])
                param_strs = [p.name if hasattr(p, 'name') else str(p) for p in params]
                definitions[name + '__info'] = {
                    'type': '函数',
                    'params': param_strs,
                    'line': line,
                    'col': col
                }
            elif node_type == 'ClassDefinition':
                definitions[name + '__info'] = {
                    'type': '类',
                    'params': [],
                    'line': line,
                    'col': col
                }
            elif node_type == 'VarDecl':
                definitions[name + '__info'] = {
                    'type': '变量',
                    'params': [],
                    'line': line,
                    'col': col
                }

        self._walk_ast(ast, collect)
        return definitions


# =============================================================================
# LSP 服务器
# =============================================================================

class LightLanguageServer:
    """光明 LSP 服务器"""
    
    def __init__(self):
        self.doc_manager = DocumentManager()
        self.capabilities = {
            'textDocumentSync': 1,  # Full sync
            'completionProvider': {
                'resolveProvider': True,
                'triggerCharacters': [' ', '设', '定', '打', '定', '导', '类', '接', '返', '当', '遍', '如',
                    # L0 单字关键字触发补全（v4.1）
                    '若', '否', '试', '捕', '抛', '终', '配', '承', '自', '跳', '过', '并', '且', '或', '非', '空', '真', '假',
                    # 标点触发补全
                    '（', '(', '。', '.', '，', ',', '：', ':']
            },
            'hoverProvider': True,
            'definitionProvider': True,
            'referencesProvider': True,
            'documentSymbolProvider': True,
            'documentFormattingProvider': True,
            'documentRangeFormattingProvider': True,
            'renameProvider': True,
            'signatureHelpProvider': {
                'triggerCharacters': ['(', '（', ',']
            },
            'semanticTokensProvider': {
                'legend': {
                    'tokenTypes': ['keyword', 'function', 'variable', 'string', 'number', 'operator', 'comment', 'type'],
                    'tokenModifiers': ['declaration', 'definition', 'readonly', 'static']
                },
                'full': True,
                'range': False
            },
            'codeActionProvider': {
                'codeActionKinds': ['quickfix', 'refactor']
            },
            'diagnosticProvider': {
                'interFileDependencies': False,
                'workspaceDiagnostics': False
            },
            'documentHighlightProvider': True,
            'signatureHelpProvider': {
                'triggerCharacters': ['（', '(', '，', ',']
            },
            'semanticTokensProvider': {
                'legend': {
                    'tokenTypes': ['namespace', 'type', 'class', 'enum', 'interface',
                                   'function', 'variable', 'property', 'parameter', 'keyword',
                                   'method', 'string', 'number', 'operator', 'comment'],
                    'tokenModifiers': ['declaration', 'definition', 'readonly', 'static',
                                       'deprecated', 'abstract', 'async', 'modification', 'documentation']
                },
                'range': False,
                'full': {
                    'delta': False
                }
            }
        }
        
    def handle_request(self, method: str, params: Dict, id: Any) -> Optional[Dict]:
        """处理请求"""
        handlers = {
            'initialize': self._handle_initialize,
            'textDocument/didOpen': self._handle_did_open,
            'textDocument/didChange': self._handle_did_change,
            'textDocument/didClose': self._handle_did_close,
            'textDocument/didSave': self._handle_did_save,
            'textDocument/completion': self._handle_completion,
            'completionItem/resolve': self._handle_completion_resolve,
            'textDocument/hover': self._handle_hover,
            'textDocument/definition': self._handle_definition,
            'textDocument/goToDefinition': self._handle_definition,
            'textDocument/references': self._handle_references,
            'textDocument/documentSymbol': self._handle_document_symbol,
            'textDocument/formatting': self._handle_formatting,
            'textDocument/rangeFormatting': self._handle_range_formatting,
            'textDocument/rename': self._handle_rename,
            'textDocument/signatureHelp': self._handle_signature_help,
            'textDocument/semanticTokens/full': self._handle_semantic_tokens,
            'textDocument/codeAction': self._handle_code_action,
            'textDocument/documentHighlight': self._handle_document_highlight,
            'textDocument/signatureHelp': self._handle_signature_help,
            'textDocument/semanticTokens/full': self._handle_semantic_tokens_full,
            'textDocument/diagnostic': self._handle_document_diagnostic,
        }
        
        handler = handlers.get(method)
        if handler:
            try:
                return lsp_response(id, handler(params))
            except Exception as e:
                return lsp_error(id, -32603, str(e))
        
        return None
    
    def _handle_initialize(self, params: Dict) -> Dict:
        """处理初始化请求"""
        return {
            'capabilities': self.capabilities,
            'serverInfo': {
                'name': '光明语言服务器',
                'version': '4.1.0'
            }
        }
    
    def _handle_did_close(self, params: Dict):
        """处理文档关闭"""
        text_doc = params.get('textDocument', {})
        uri = text_doc.get('uri')
        self.doc_manager.close_document(uri)
        return None

    def _handle_did_save(self, params: Dict):
        """处理文档保存"""
        text_doc = params.get('textDocument', {})
        uri = text_doc.get('uri')
        # 重新分析文档并发布诊断
        if uri in self.doc_manager.documents:
            doc = self.doc_manager.documents[uri]
            self.doc_manager._analyze_document(doc)
            self._publish_diagnostics(uri)
        return None

    def _handle_completion(self, params: Dict) -> Dict:
        """处理代码补全 - 智能上下文感知补全"""
        doc = self.doc_manager.get_document(params.get('textDocument', {}).get('uri', ''))
        if not doc:
            return {'isIncomplete': False, 'items': []}
        
        position = params.get('position', {})
        line = position.get('line', 0)
        character = position.get('character', 0)
        
        # 获取当前行的前缀
        line_text = doc.get_line(line)
        # 找到当前词的起始位置
        start = character
        while start > 0:
            ch = line_text[start - 1]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                start -= 1
            else:
                break
        prefix = line_text[start:character]
        
        # 获取光标前的上下文文本（用于上下文感知）
        before_cursor = line_text[:start].strip()
        # 判断上下文类型
        context_type = 'normal'
        if before_cursor.endswith('设') or before_cursor.endswith('设 '):
            context_type = 'after_set'
        elif before_cursor.endswith('定义') or before_cursor.endswith('定义 '):
            context_type = 'after_define'
        elif before_cursor.endswith('导入') or before_cursor.endswith('导入 '):
            context_type = 'after_import'
        elif before_cursor.endswith('返回') or before_cursor.endswith('返回 '):
            context_type = 'after_return'
        elif before_cursor.endswith('等待') or before_cursor.endswith('等待 '):
            context_type = 'after_await'
        elif before_cursor.endswith('新建') or before_cursor.endswith('新建 '):
            context_type = 'after_new'
        elif before_cursor.endswith('抛出') or before_cursor.endswith('抛出 '):
            context_type = 'after_throw'
        elif before_cursor.endswith('类') or before_cursor.endswith('类 '):
            context_type = 'after_class'
        elif before_cursor.endswith('段落') or before_cursor.endswith('段落 '):
            context_type = 'after_paragraph'
        elif before_cursor.endswith('从') or before_cursor.endswith('从 '):
            context_type = 'after_from'
        elif before_cursor.endswith('使用') or before_cursor.endswith('使用 '):
            context_type = 'after_with'
        elif before_cursor.endswith('捕获') or before_cursor.endswith('捕获 '):
            context_type = 'after_catch'
        elif before_cursor.endswith('匹配') or before_cursor.endswith('匹配 '):
            context_type = 'after_match'
        
        completions = []
        
        # ====== 上下文感知补全 ======
        if context_type == 'after_import':
            # 导入上下文：建议模块名和 lightpub 包名
            modules = ['标准库', '文件系统', 'JSON', 'CSV', 'HTTP', 'Socket', '数学', '正则表达式',
                       '字符串处理', '日期时间', '线程', '系统信息', '日志系统', '配置管理']
            for mod_name in sorted(modules):
                if not prefix or mod_name.startswith(prefix):
                    completions.append({
                        'label': mod_name,
                        'kind': 9,  # Module
                        'detail': '模块',
                        'sortText': f'1_{mod_name}',
                        'filterText': mod_name,
                    })
            # lightpub 包名
            for pkg_name in _LIGHTPUB_PACKAGES:
                if not prefix or pkg_name.startswith(prefix):
                    completions.append({
                        'label': pkg_name,
                        'kind': 9,
                        'detail': 'lightpub 包',
                        'sortText': f'1_{pkg_name}',
                        'filterText': pkg_name,
                    })
            return {'isIncomplete': False, 'items': completions}
        
        elif context_type == 'after_set':
            # 设 上下文：建议变量名
            if doc.uri in self.doc_manager.definitions:
                for name in sorted(self.doc_manager.definitions[doc.uri].keys()):
                    if name.endswith('__info'):
                        continue
                    if not prefix or name.startswith(prefix):
                        completions.append({
                            'label': name,
                            'kind': 6,
                            'detail': '变量',
                            'sortText': f'1_{name}',
                            'filterText': name,
                        })
            return {'isIncomplete': False, 'items': completions}
        
        elif context_type == 'after_return':
            # 返回上下文：建议表达式
            completions.append({
                'label': '真', 'kind': 14, 'detail': '布尔值', 'sortText': '1_真', 'filterText': '真'
            })
            completions.append({
                'label': '假', 'kind': 14, 'detail': '布尔值', 'sortText': '1_假', 'filterText': '假'
            })
            completions.append({
                'label': '空', 'kind': 14, 'detail': '空值', 'sortText': '1_空', 'filterText': '空'
            })
            return {'isIncomplete': False, 'items': completions}
        
        elif context_type == 'after_class':
            # 类上下文：建议继承关键字和类模板
            completions.append({
                'label': '继承', 'kind': 14, 'detail': '类继承', 'sortText': '1_继承', 'filterText': '继承'
            })
            completions.append({
                'label': '实现', 'kind': 14, 'detail': '实现接口', 'sortText': '1_实现', 'filterText': '实现'
            })
            return {'isIncomplete': False, 'items': completions}

        elif context_type == 'after_paragraph':
            # 段落上下文：建议函数名和接收关键字
            completions.append({
                'label': '接收', 'kind': 14, 'detail': '段落参数', 'sortText': '1_接收', 'filterText': '接收'
            })
            return {'isIncomplete': False, 'items': completions}

        elif context_type == 'after_from':
            # 从...导入上下文：建议模块名
            modules = ['标准库', 'JSON', 'CSV', 'HTTP', '正则表达式', '日期时间', '数学', '线程', '系统信息', '字符串处理']
            for mod_name in sorted(modules):
                if not prefix or mod_name.startswith(prefix):
                    completions.append({
                        'label': mod_name,
                        'kind': 9,  # Module
                        'detail': '模块',
                        'sortText': f'1_{mod_name}',
                        'filterText': mod_name,
                    })
            return {'isIncomplete': False, 'items': completions}

        elif context_type == 'after_with':
            # 使用上下文：建议资源管理
            completions.append({
                'label': '为', 'kind': 14, 'detail': '使用...为 语法', 'sortText': '1_为', 'filterText': '为'
            })
            return {'isIncomplete': False, 'items': completions}

        elif context_type == 'after_catch':
            # 捕获上下文：建议异常类型
            exceptions = ['值错误', '类型错误', '键错误', '索引错误', '属性错误',
                          '文件未找到', '导入错误', '运行时错误', '零除错误', '异常']
            for exc_name in sorted(exceptions):
                if not prefix or exc_name.startswith(prefix):
                    completions.append({
                        'label': exc_name,
                        'kind': 14,  # Keyword
                        'detail': '异常类型',
                        'sortText': f'1_{exc_name}',
                        'filterText': exc_name,
                    })
            return {'isIncomplete': False, 'items': completions}

        elif context_type == 'after_match':
            # 匹配上下文：建议情况关键字
            completions.append({
                'label': '情况', 'kind': 14, 'detail': '匹配分支', 'sortText': '1_情况', 'filterText': '情况'
            })
            return {'isIncomplete': False, 'items': completions}
        
        # ====== 关键字补全（从 ALL_KEYWORDS 中获取）======
        kw_docs = {
            '定义': '定义变量：定义 变量名 等于 值。',
            '设': '设变量为值：设 变量名 为 值。',
            '如果': '条件语句：如果 条件 那么：...结束。',
            '若': '条件语句（简写）：若 条件 则：...结束。',
            '那么': '条件语句 then 分支',
            '否则': '条件语句 else 分支',
            '否则若': '条件语句 elif 分支',
            '遍历': '遍历循环：遍历 变量 于 列表：...结束。',
            '当': '条件循环：当 条件：...结束。',
            '返回': '返回语句：返回 表达式。',
            '跳出': '跳出循环：跳出。',
            '跳过': '跳过本次迭代：跳过。',
            '段落': '段落（函数）定义：段落 段名 接收 参数：...结束。',
            '函数': '函数定义：函数 函数名 接收 参数：...结束。',
            '类': '类定义：类 类名：...结束。',
            '接口': '接口定义：接口 接口名：...结束。',
            '尝试': '异常处理：尝试：...捕获 异常：...结束。',
            '捕获': '捕获异常：捕获 异常类型 为 变量：...',
            '最终': '最终执行块：最终：...',
            '抛出': '抛出异常：抛出 异常对象。',
            '导入': '导入模块：导入 模块名。',
            '匹配': '模式匹配：匹配 表达式：情况 模式：...结束。',
            '情况': '匹配分支：情况 模式：...',
            '异步': '异步函数定义：异步 段落 段名...',
            '等待': '等待异步操作：等待 异步调用。',
            '使用': '上下文管理器：使用 资源 为 变量：...',
            '从': '从模块导入：从 模块名 导入 名称。',
            '导出': '导出语句：导出 名称。',
            '属性': '类属性声明：属性 名称。',
            '构造': '构造函数：构造 参数：...结束。',
            '继承': '类继承：类 类名 继承 父类：...',
            '实现': '实现接口：类 类名 实现 接口名：...',
            '协议': '协议定义：协议 协议名：...结束。',
            '私属性': '私有属性声明。',
            '私段落': '私有方法声明。',
            '私有': '访问控制：私有成员。',
            '公有': '访问控制：公有成员。',
            '保护': '访问控制：保护成员。',
            '静态': '静态方法修饰符。',
            '抽象': '抽象方法修饰符。',
            '真': '布尔值：真 (True)',
            '假': '布尔值：假 (False)',
            '空': '空值：空 (None)',
            '新建': '创建对象实例：新建 类名(参数)。',
            '己': '自身引用 self。',
            '父': '父类引用 super。',
            '嵌入': '嵌入代码块：嵌入 Python：...结束嵌入。',
            '加载': '动态加载模块：加载 "模块名"。',
            '可空': '可空类型标记：字符串? 或 可空(字符串)。',
            '断言': '断言检查：断言 条件 等于 真。',
            '创建': '创建集合/列表：创建 列表。',
            '无': '空值（与 空 同义）。',
            '加载库': '加载动态链接库：加载库 "libc.so.6" 为 libc。',
            '外部': 'FFI 外部函数声明。',
            '结构体': 'FFI 结构体定义。',
            '枚举': '枚举类型定义。',
            '类型别名': '类型别名定义。',
            '标注': '装饰器/标注定义。',
            '特性': '类特性/属性定义。',
            '生成': '生成器定义。',
            '作用域': '作用域控制。',
            '模块': '模块声明。',
            '标准库': '标准库引用。',
            '开启': '开启类型检查。',
            '关闭': '关闭类型检查。',
            '嵌入': '嵌入代码块。',
            '结束嵌入': '结束嵌入代码块。',
            '并': '管道操作符/并行。',
            '之': '属性提取符。',
            '的': '定语标记。',
            '至': '范围结束符（1 至 10）。',
            '到': '范围结束符（1 到 10）。',
            '步': '范围步长（1 至 10 步 2）。',
            '且': '逻辑与。',
            '或': '逻辑或。',
            '非': '逻辑非。',
            '与': '按位与。',
            # ===== L0 单字简写关键字（v4.1）=====
            '否': '条件语句 else 分支（L0简写）：否则/否 条件：...结束。',
            '遍': '遍历循环（L0简写）：遍 变量 之 列表：...结束。',
            '返': '返回语句（L0简写）：返 表达式。',
            '跳': '跳出循环（L0简写）：跳。',
            '过': '跳过本次迭代（L0简写）：过。',
            '段': '段落（函数）定义（L0简写）：段 段名(参数)：...结束。',
            '承': '继承（L0简写）：类 子类 承 父类：...结束。',
            '接': '接口定义（L0简写）：接 接口名：...结束。',
            '试': '异常处理（L0简写）：试：...捕 异常：...结束。',
            '捕': '异常捕获（L0简写）：捕 异常类型：...结束。',
            '抛': '抛出异常（L0简写）：抛 异常对象。',
            '终': '最终执行块（L0简写）：终：...结束。',
            '导': '导入模块（L0简写）：导 模块名。',
            '出': '导出模块（L0简写）：出 模块名。',
            '配': '模式匹配（L0简写）：配 表达式：情况 模式：...结束。',
            '自': '自引用（L0）：自.属性 或 自.方法()，等价于 self。',
            '是': '判断/相等（L0）：甲 是 乙 等价于 甲 == 乙。',
        }

        for kw in sorted(ALL_KEYWORDS):
            if not prefix or kw.startswith(prefix):
                item = {
                    'label': kw,
                    'kind': 14,  # Keyword
                    'detail': '关键字',
                    'sortText': f'1_{kw}',
                    'filterText': kw,
                    'insertText': kw[len(prefix):] if prefix and kw.startswith(prefix) else kw
                }
                if kw in kw_docs:
                    item['documentation'] = {'kind': 'markdown', 'value': kw_docs[kw]}
                completions.append(item)

        # 补充不在 ALL_KEYWORDS 中的常用中文关键词
        extra_keywords = {
            '加载': '动态加载模块或库。',
            '可空': '可空类型标记：类型? 表示可空。',
            '断言': '断言检查：断言 条件。',
            '创建': '创建新对象：创建 列表 / 创建 字典。',
            '输入': '读取用户输入：输入("提示")。',
            '类型': '获取值的类型：类型(值)。',
            '对于': '对于循环（同遍历）：对于 变量 于 列表。',
            '范围': '生成范围：范围(开始, 结束)。',
            '无': '空值标记（同 空）。',
            '打印': '输出到控制台：打印(值)。',
            '求幂': '幂运算：求幂(底数, 指数)。',
            '整除': '整数除法：整除(被除数, 除数)。',
            '取余': '取余运算：取余(被除数, 除数)。',
        }
        for kw, kw_doc in sorted(extra_keywords.items()):
            if not prefix or kw.startswith(prefix):
                completions.append({
                    'label': kw,
                    'kind': 14,  # Keyword
                    'detail': '中文关键字',
                    'sortText': f'1_{kw}',
                    'filterText': kw,
                    'insertText': kw[len(prefix):] if prefix and kw.startswith(prefix) else kw,
                    'documentation': {'kind': 'markdown', 'value': kw_doc}
                })
        
        # ====== 动词元数补全 ======
        for verb, arity in sorted(VERB_ARITY.items()):
            if not prefix or verb.startswith(prefix):
                detail = f'动词 (元数: {arity})'
                params_str = ''
                if arity > 0:
                    params_str = ' '.join(['参数' + str(i+1) for i in range(arity)])
                elif arity < 0:
                    params_str = '参数...'
                completions.append({
                    'label': verb,
                    'kind': 15,  # Snippet
                    'detail': detail,
                    'sortText': f'2_{verb}',
                    'filterText': verb,
                    'insertText': f'{verb} $0' if arity == 0 else verb,
                    'data': {
                        'type': 'verb',
                        'name': verb,
                        'arity': arity,
                        'params': params_str
                    }
                })
        
        # ====== Stdlib 函数补全 ======
        for func_name, arity in sorted(STDLIB_VERB_ARITY.items()):
            if not prefix or func_name.startswith(prefix):
                arity_str = f'元数: {arity}' if arity >= 0 else '可变参数'
                completions.append({
                    'label': func_name,
                    'kind': 3,  # Function
                    'detail': f'内置函数 ({arity_str})',
                    'sortText': f'4_{func_name}',
                    'filterText': func_name,
                    'data': {
                        'type': 'stdlib',
                        'name': func_name,
                        'arity': arity
                    }
                })

        # ====== 常用内置函数补全（不在 STDLIB_VERB_ARITY 中的）======
        extra_builtins = {
            '打印': '打印内容到控制台',
            '读取行': '从标准输入读取一行',
            '写入输出': '向标准输出写入文本',
            '打印输出': '打印文本并换行',
            '类型': '获取值的类型',
            '长': '获取列表/字符串长度',
            '长度': '获取列表/字符串长度',
            '转字符串': '将值转换为字符串',
            '转整数': '将值转换为整数',
            '转浮点': '将值转换为浮点数',
            '范围': '生成整数范围',
            '字符串长度': '获取字符串长度',
            '分割字符串': '分割字符串为列表',
            '连接字符串': '连接字符串列表',
            '替换字符串': '替换字符串中的子串',
            '去除空白': '去除字符串首尾空白',
            '解析JSON': '解析 JSON 字符串为光明值',
            '序列化JSON': '将光明值序列化为 JSON 字符串',
            '文件存在': '检查文件是否存在',
            '目录存在': '检查目录是否存在',
            '读取文件': '读取文件全部内容',
            '写入文件': '写入内容到文件',
            '追加文件': '追加内容到文件',
            '删除文件': '删除文件',
            '创建目录': '创建目录',
            '列出目录': '列出目录内容',
            '执行命令': '执行系统命令',
            '当前目录': '获取当前工作目录',
            '切换目录': '切换工作目录',
            '环境变量': '获取环境变量值',
            '退出程序': '退出程序',
            '随机整数': '生成随机整数',
            '随机浮点': '生成随机浮点数',
            '随机选择': '从列表中随机选择',
            '求和': '计算列表数值之和',
            '平均数': '计算列表数值平均值',
            '中位数': '计算列表数值中位数',
            '阶乘': '计算阶乘',
            '圆周率': '返回圆周率 π',
            '自然常数': '返回自然常数 e',
        }
        for func_name, func_desc in sorted(extra_builtins.items()):
            if func_name in STDLIB_VERB_ARITY:
                continue  # 跳过已在 stdlib 列表中的
            if not prefix or func_name.startswith(prefix):
                completions.append({
                    'label': func_name,
                    'kind': 3,  # Function
                    'detail': func_desc,
                    'sortText': f'4_{func_name}',
                    'filterText': func_name,
                })
        
        # ====== 内置类型补全 ======
        for t in sorted(BUILTIN_TYPES):
            if not prefix or t.startswith(prefix):
                completions.append({
                    'label': t,
                    'kind': 22,  # TypeParameter
                    'detail': '内置类型',
                    'sortText': f'5_{t}',
                    'filterText': t
                })
        
        # ====== 本地变量/函数补全 ======
        if doc.uri in self.doc_manager.definitions:
            for name in sorted(self.doc_manager.definitions[doc.uri].keys()):
                if name.endswith('__info'):
                    continue
                if not prefix or name.startswith(prefix):
                    info = self.doc_manager.definitions[doc.uri].get(name + '__info', {})
                    kind = 6  # Variable
                    detail = '变量'
                    if info.get('type') == '函数':
                        kind = 12  # Function
                        detail = f"函数({', '.join(info.get('params', []))})"
                    
                    completions.append({
                        'label': name,
                        'kind': kind,
                        'detail': detail,
                        'sortText': f'6_{name}',
                        'filterText': name
                    })
        
        # ====== lightpub 包名补全 ======
        for pkg_name in _LIGHTPUB_PACKAGES:
            if not prefix or pkg_name.startswith(prefix):
                completions.append({
                    'label': pkg_name,
                    'kind': 9,  # Module
                    'detail': 'lightpub 包',
                    'sortText': f'7_{pkg_name}',
                    'filterText': pkg_name,
                    'data': {
                        'type': 'lightpub',
                        'name': pkg_name,
                    }
                })
        
        # ====== Snippet 补全（常用模式，sortText 为 3_ 排在关键字和动词之后）======
        snippets = [
            {
                'label': '段落模板',
                'kind': 15,  # Snippet
                'detail': '段落定义模板',
                'sortText': '3_段落模板',
                'insertText': '段落 ${1:段名} 接收 ${2:参数}：\n\t$0\n结束。',
                'insertTextFormat': 2,  # SnippetTextFormat
            },
            {
                'label': '如果模板',
                'kind': 15,
                'detail': '如果条件语句模板',
                'sortText': '3_如果模板',
                'insertText': '如果 ${1:条件} 那么：\n\t$0\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '如果否则模板',
                'kind': 15,
                'detail': '如果-否则条件语句模板',
                'sortText': '3_如果否则模板',
                'insertText': '如果 ${1:条件} 那么：\n\t${2:代码}\n否则：\n\t${3:代码}\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '遍历模板',
                'kind': 15,
                'detail': '遍历循环模板',
                'sortText': '3_遍历模板',
                'insertText': '遍历 ${1:变量} 于 ${2:列表}：\n\t$0\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '当模板',
                'kind': 15,
                'detail': '当循环模板',
                'sortText': '3_当模板',
                'insertText': '当 ${1:条件}：\n\t$0\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '类模板',
                'kind': 15,
                'detail': '类定义模板',
                'sortText': '3_类模板',
                'insertText': '类 ${1:类名}：\n\t属性 ${2:属性名}。\n\t构造 ${3:参数}：\n\t\t$0\n\t结束。\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '函数模板',
                'kind': 15,
                'detail': '函数定义模板',
                'sortText': '3_函数模板',
                'insertText': '函数 ${1:函数名} 接收 ${2:参数}：\n\t$0\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '尝试模板',
                'kind': 15,
                'detail': '异常处理模板',
                'sortText': '3_尝试模板',
                'insertText': '尝试：\n\t$0\n捕获 ${1:异常}：\n\t\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '尝试最终模板',
                'kind': 15,
                'detail': '异常处理模板（含 finally）',
                'sortText': '3_尝试最终模板',
                'insertText': '尝试：\n\t$0\n捕获 ${1:异常}：\n\t\n最终：\n\t\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '匹配模板',
                'kind': 15,
                'detail': '模式匹配模板',
                'sortText': '3_匹配模板',
                'insertText': '匹配 ${1:表达式}：\n情况 ${2:模式}：\n\t$0\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '定义变量',
                'kind': 15,
                'detail': '定义变量模板',
                'sortText': '3_定义变量',
                'insertText': '定义 ${1:变量名} 等于 ${2:值}。',
                'insertTextFormat': 2,
            },
            {
                'label': '异步段落模板',
                'kind': 15,
                'detail': '异步段落定义模板',
                'sortText': '3_异步段落模板',
                'insertText': '异步 段落 ${1:段名} 接收 ${2:参数}：\n\t$0\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '使用模板',
                'kind': 15,
                'detail': '上下文管理器模板',
                'sortText': '3_使用模板',
                'insertText': '使用 ${1:资源} 为 ${2:变量}：\n\t$0\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '接口模板',
                'kind': 15,
                'detail': '接口定义模板',
                'sortText': '3_接口模板',
                'insertText': '接口 ${1:接口名}：\n\t段落 ${2:方法名} 接收 ${3:参数}。\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '遍历范围模板',
                'kind': 15,
                'detail': '遍历范围循环模板',
                'sortText': '3_遍历范围模板',
                'insertText': '遍历 ${1:变量} 于 ${2:起始} 至 ${3:结束}：\n\t$0\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '设变量模板',
                'kind': 15,
                'detail': '设变量赋值模板',
                'sortText': '3_设变量模板',
                'insertText': '设 ${1:变量名} 为 ${2:值}。',
                'insertTextFormat': 2,
            },
            {
                'label': '返回模板',
                'kind': 15,
                'detail': '返回值模板',
                'sortText': '3_返回模板',
                'insertText': '返回 ${1:值}。',
                'insertTextFormat': 2,
            },
            {
                'label': '抛出模板',
                'kind': 15,
                'detail': '抛出异常模板',
                'sortText': '3_抛出模板',
                'insertText': '抛出 ${1:异常}。',
                'insertTextFormat': 2,
            },
            {
                'label': '导入模板',
                'kind': 15,
                'detail': '导入模块模板',
                'sortText': '3_导入模板',
                'insertText': '导入 ${1:模块名}。',
                'insertTextFormat': 2,
            },
            {
                'label': '从导入模板',
                'kind': 15,
                'detail': '从模块导入符号模板',
                'sortText': '3_从导入模板',
                'insertText': '从 ${1:模块名} 导入 ${2:符号}。',
                'insertTextFormat': 2,
            },
            {
                'label': '导出模板',
                'kind': 15,
                'detail': '导出符号模板',
                'sortText': '3_导出模板',
                'insertText': '导出 ${1:符号}。',
                'insertTextFormat': 2,
            },
            {
                'label': '等待模板',
                'kind': 15,
                'detail': '等待异步操作模板',
                'sortText': '3_等待模板',
                'insertText': '等待 ${1:异步调用}。',
                'insertTextFormat': 2,
            },
            {
                'label': '断言模板',
                'kind': 15,
                'detail': '断言检查模板',
                'sortText': '3_断言模板',
                'insertText': '断言 ${1:条件} 等于 ${2:真}。',
                'insertTextFormat': 2,
            },
            {
                'label': '打印模板',
                'kind': 15,
                'detail': '打印输出模板',
                'sortText': '3_打印模板',
                'insertText': '打印(${1:值})',
                'insertTextFormat': 2,
            },
            {
                'label': '输入模板',
                'kind': 15,
                'detail': '读取用户输入模板',
                'sortText': '3_输入模板',
                'insertText': '输入("${1:提示}")',
                'insertTextFormat': 2,
            },
            {
                'label': '加载模板',
                'kind': 15,
                'detail': '动态加载模块模板',
                'sortText': '3_加载模板',
                'insertText': '加载 "${1:模块名}"。',
                'insertTextFormat': 2,
            },
            {
                'label': '创建模板',
                'kind': 15,
                'detail': '创建列表/字典模板',
                'sortText': '3_创建模板',
                'insertText': '创建 ${1:列表}(${2:元素})',
                'insertTextFormat': 2,
            },
            {
                'label': '类型模板',
                'kind': 15,
                'detail': '获取类型模板',
                'sortText': '3_类型模板',
                'insertText': '类型(${1:值})',
                'insertTextFormat': 2,
            },
            {
                'label': '范围模板',
                'kind': 15,
                'detail': '范围生成模板',
                'sortText': '3_范围模板',
                'insertText': '范围(${1:起始}, ${2:结束})',
                'insertTextFormat': 2,
            },
            {
                'label': '静态段落模板',
                'kind': 15,
                'detail': '静态段落定义模板',
                'sortText': '3_静态段落模板',
                'insertText': '静态 段落 ${1:方法名} 接收 ${2:参数}：\n\t$0\n结束。',
                'insertTextFormat': 2,
            },
            {
                'label': '抽象段落模板',
                'kind': 15,
                'detail': '抽象段落定义模板',
                'sortText': '3_抽象段落模板',
                'insertText': '抽象 段落 ${1:方法名} 接收 ${2:参数}。',
                'insertTextFormat': 2,
            },
            {
                'label': '可空类型模板',
                'kind': 15,
                'detail': '可空类型声明模板',
                'sortText': '3_可空类型模板',
                'insertText': '可空(${1:类型})',
                'insertTextFormat': 2,
            },
        ]
        completions.extend(snippets)
        
        return {
            'isIncomplete': False,
            'items': completions
        }
    
    def _handle_completion_resolve(self, params: Dict) -> Dict:
        """处理补全项解析（返回参数详细信息）"""
        item = params
        data = item.get('data', {})
        item_type = data.get('type', '')
        name = data.get('name', '')
        
        if item_type == 'verb':
            arity = data.get('arity', 0)
            if arity > 0:
                params_detail = ' '.join([f'参数{i+1}' for i in range(arity)])
                item['detail'] = f'动词: {name} ({params_detail})'
            elif arity < 0:
                item['detail'] = f'动词: {name} (可变参数)'
            else:
                item['detail'] = f'动词: {name} (无参数)'
        elif item_type == 'stdlib':
            arity = data.get('arity', 0)
            # 为 stdlib 函数提供更详细的文档
            stdlib_docs = {
                '读取文件': '读取文件内容\n\n参数: path (文件路径)\n返回: 文件内容字符串',
                '写入文件': '写入文件内容\n\n参数: path (文件路径), content (内容)',
                '追加文件': '追加内容到文件\n\n参数: path (文件路径), content (追加内容)',
                '文件存在': '检查文件是否存在\n\n参数: path (文件路径)\n返回: 布尔值',
                '目录存在': '检查目录是否存在\n\n参数: path (目录路径)\n返回: 布尔值',
                '路径存在': '检查路径是否存在\n\n参数: path (路径)\n返回: 布尔值',
                '创建目录': '创建目录\n\n参数: path (目录路径)',
                '删除文件': '删除文件\n\n参数: path (文件路径)',
                '删除目录': '删除空目录\n\n参数: path (目录路径)',
                '列出目录': '列出目录内容\n\n参数: path (目录路径)\n返回: 文件名列表',
                '绝对路径': '获取绝对路径\n\n参数: path (路径)\n返回: 绝对路径字符串',
                '连接路径': '连接多个路径\n\n参数: *paths (路径片段)\n返回: 连接后的路径',
                '环境变量': '获取环境变量\n\n参数: name (变量名), default (默认值)\n返回: 变量值或默认值',
                '退出程序': '退出程序\n\n参数: code (退出码，默认0)',
                '当前目录': '获取当前工作目录\n\n返回: 路径字符串',
                '切换目录': '切换工作目录\n\n参数: path (目录路径)',
                '执行命令': '执行系统命令\n\n参数: command (命令字符串)\n返回: 退出码',
                '读取行': '从标准输入读取一行\n\n返回: 读取的字符串',
                '写入输出': '向标准输出写入文本\n\n参数: text (要写入的文本)',
                '打印输出': '向标准输出打印文本并换行\n\n参数: text (要打印的文本)',
                '解析JSON': '解析 JSON 字符串\n\n参数: text (JSON 字符串)\n返回: 光明值',
                '序列化JSON': '将值序列化为 JSON 字符串\n\n参数: value (值), 缩进 (可选)',
                '转整数': '将字符串转换为整数\n\n参数: text (字符串)\n返回: 整数',
                '转浮点': '将字符串转换为浮点数\n\n参数: text (字符串)\n返回: 浮点数',
                '转字符串': '将值转换为字符串\n\n参数: value (任意值)\n返回: 字符串',
                '字符串长度': '获取字符串长度\n\n参数: text (字符串)\n返回: 整数',
                '分割字符串': '分割字符串\n\n参数: text (字符串), separator (分隔符)',
                '连接字符串': '连接字符串列表\n\n参数: parts (列表), separator (分隔符)',
                '替换字符串': '替换字符串\n\n参数: text (原串), old (旧串), new (新串)',
                '去除空白': '去除首尾空白\n\n参数: text (字符串)\n返回: 处理后的字符串',
                '随机整数': '生成随机整数\n\n参数: 最小 (包含), 最大 (包含)\n返回: 随机整数',
                '随机浮点': '生成 [0.0, 1.0) 随机浮点数\n\n返回: 随机浮点数',
                '随机选择': '从列表中随机选择元素\n\n参数: 列表\n返回: 选中的元素',
                '阶乘': '计算 n 的阶乘\n\n参数: n (非负整数)\n返回: n!',
                '平均数': '计算列表平均值\n\n参数: 数据 (数值列表)\n返回: 平均值',
                '中位数': '计算列表中位数\n\n参数: 数据 (数值列表)\n返回: 中位数',
                '求和': '计算列表和\n\n参数: 数据 (数值列表)\n返回: 总和',
                '圆周率': '返回圆周率 π\n\n返回: 3.14159...',
                '自然常数': '返回自然常数 e\n\n返回: 2.71828...',
            }
            if name in stdlib_docs:
                item['documentation'] = {'kind': 'markdown', 'value': f'**{name}**\n\n{stdlib_docs[name]}'}
            else:
                item['detail'] = f'内置函数: {name}'
        elif item_type == 'keyword':
            kw_docs = {
                '定义': '定义变量：定义 变量名 等于 值。',
                '如果': '条件语句：如果 条件 那么：...结束。',
                '遍历': '遍历循环：遍历 变量 于 列表：...结束。',
                '返回': '返回语句：返回 表达式。',
                '段落': '段落（函数）定义：段落 段名 接收 参数：...结束。',
            }
            if name in kw_docs:
                item['documentation'] = {'kind': 'markdown', 'value': kw_docs[name]}
        
        return item
    
    def _handle_hover(self, params: Dict) -> Optional[Dict]:
        """处理悬停请求"""
        doc = self.doc_manager.get_document(params.get('textDocument', {}).get('uri', ''))
        if not doc:
            return None
        
        position = params.get('position', {})
        line = position.get('line', 0)
        character = position.get('character', 0)
        
        # 获取当前位置的词
        line_text = doc.get_line(line)
        start = character
        end = character
        
        while start > 0:
            ch = line_text[start - 1]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                start -= 1
            else:
                break
        while end < len(line_text):
            ch = line_text[end]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                end += 1
            else:
                break
        
        word = line_text[start:end]
        if not word:
            return None
        
        # 构造悬停内容
        contents = []

        # 中文关键字详细文档
        KW_HOVER_DOCS = {
            '定义': '**关键字**: `定义`\n\n**用法**: `定义 变量名 等于 值。`\n\n**说明**: 用于声明变量并赋值。v4.0 推荐使用 L0 单字「设」替代。\n\n**示例**:\n```\n定义 甲 等于 42。\n定义 名称 等于 "光明"。\n```',
            '设': '**关键字**: `设` (L0 核心字)\n\n**用法**: `设 变量名 = 值。`\n\n**说明**: L0 单字关键字，用于声明变量并赋值。是 v4.0 推荐的主形式。\n\n**示例**:\n```\n设 甲 = 42\n设 名称 = "光明"\n```',
            '如果': '**关键字**: `如果`\n\n**用法**: `如果 条件：\\n    代码块\\n否则：\\n    代码块`\n\n**说明**: 条件判断语句。v4.0 推荐使用 L0 单字「若」替代。\n\n**示例**:\n```\n如果 分数 >= 60：\n    打印 "及格"\n否则：\n    打印 "不及格"\n```',
            '若': '**关键字**: `若` (L0 核心字)\n\n**用法**: `若 条件 则：\\n    代码块\\n否：\\n    代码块`\n\n**说明**: L0 单字条件判断关键字，v4.0 推荐的主形式。\n\n**示例**:\n```\n若 甲 > 乙：\n    打印 "甲大"\n否：\n    打印 "乙大"\n```',
            '否则': '**关键字**: `否则`\n\n**用法**: `否则：\\n    代码块`\n\n**说明**: 条件判断的 else 分支。v4.0 推荐使用 L0 单字「否」替代。',
            '否': '**关键字**: `否` (L0 核心字)\n\n**用法**: `否：\\n    代码块`\n\n**说明**: L0 单字，条件判断的 else 分支，v4.0 推荐的主形式。',
            '否则若': '**关键字**: `否则若`\n\n**用法**: `否则若 条件：\\n    代码块`\n\n**说明**: 多条件判断的 elif 分支。',
            '遍历': '**关键字**: `遍历`\n\n**用法**: `遍历 变量 于 列表：\\n    代码块`\n\n**说明**: 遍历循环，用于迭代列表或范围。v4.0 推荐使用 L0 单字「遍」替代。\n\n**示例**:\n```\n遍历 i 于 1 至 5：\n    打印 i\n```',
            '遍': '**关键字**: `遍` (L0 核心字)\n\n**用法**: `遍 变量 之 列表：\\n    代码块`\n\n**说明**: L0 单字遍历循环关键字，v4.0 推荐的主形式。',
            '当': '**关键字**: `当` (L0 核心字)\n\n**用法**: `当 条件：\\n    代码块`\n\n**说明**: 条件循环，当条件为真时重复执行代码块。\n\n**示例**:\n```\n当 计数 <= 5：\n    打印 计数\n    计数 = 计数 + 1\n```',
            '返回': '**关键字**: `返回`\n\n**用法**: `返回 表达式。`\n\n**说明**: 从函数中返回一个值。v4.0 推荐使用 L0 单字「返」替代。',
            '返': '**关键字**: `返` (L0 核心字)\n\n**用法**: `返 表达式。`\n\n**说明**: L0 单字返回关键字，v4.0 推荐的主形式。',
            '段落': '**关键字**: `段落`\n\n**用法**: `段落 函数名 接收 参数：\\n    代码块`\n\n**说明**: 定义函数（段落）。v4.0 推荐使用 L0 单字「段」替代。\n\n**示例**:\n```\n段落 阶乘 接收 n：\\n    若 n <= 1：返 1\\n    返 n * 阶乘(n-1)\n```',
            '段': '**关键字**: `段` (L0 核心字)\n\n**用法**: `段 函数名(参数)：\\n    代码块`\n\n**说明**: L0 单字函数定义关键字，v4.0 推荐的主形式。',
            '类': '**关键字**: `类` (L0 核心字)\n\n**用法**: `类 类名：\\n    属性\\n    段落 方法名(参数)：\\n        代码块`\n\n**说明**: 定义类（面向对象编程）。',
            '承': '**关键字**: `承` (L0 核心字)\n\n**用法**: `类 子类 承 父类：\\n    代码块`\n\n**说明**: L0 单字，表示类继承。',
            '接口': '**关键字**: `接口`\n\n**用法**: `接口 接口名：\\n    段落 方法名(参数)：\\n        代码块`\n\n**说明**: 定义接口（抽象方法集合）。v4.0 推荐使用 L0 单字「接」替代。',
            '接': '**关键字**: `接` (L0 核心字)\n\n**用法**: `接 接口名：\\n    代码块`\n\n**说明**: L0 单字接口定义关键字，v4.0 推荐的主形式。',
            '匹配': '**关键字**: `匹配`\n\n**用法**: `匹配 表达式：\\n    情况 模式：\\n        代码块`\n\n**说明**: 模式匹配。v4.0 推荐使用 L0 单字「配」替代。',
            '配': '**关键字**: `配` (L0 核心字)\n\n**用法**: `配 表达式：\\n    情况 模式：\\n        代码块`\n\n**说明**: L0 单字模式匹配关键字。',
            '尝试': '**关键字**: `尝试`\n\n**用法**: `尝试：\\n    代码块\\n捕获 异常：\\n    代码块\\n最终：\\n    代码块`\n\n**说明**: 异常处理。v4.0 推荐使用 L0 单字「试」替代。',
            '试': '**关键字**: `试` (L0 核心字)\n\n**用法**: `试：\\n    代码块\\n捕 异常：\\n    代码块\\n终：\\n    代码块`\n\n**说明**: L0 单字异常处理关键字。',
            '捕获': '**关键字**: `捕获`\n\n**用法**: `捕获 异常类型：\\n    代码块`\n\n**说明**: 捕获异常。v4.0 推荐使用 L0 单字「捕」替代。',
            '捕': '**关键字**: `捕` (L0 核心字)\n\n**用法**: `捕 异常类型：\\n    代码块`\n\n**说明**: L0 单字异常捕获关键字。',
            '抛出': '**关键字**: `抛出`\n\n**用法**: `抛出 异常对象。`\n\n**说明**: 主动抛出异常。v4.0 推荐使用 L0 单字「抛」替代。',
            '抛': '**关键字**: `抛` (L0 核心字)\n\n**用法**: `抛 异常对象。`\n\n**说明**: L0 单字抛出异常关键字。',
            '最终': '**关键字**: `最终`\n\n**用法**: `最终：\\n    代码块`\n\n**说明**: 异常处理的 finally 块，无论是否发生异常都会执行。v4.0 推荐使用 L0 单字「终」替代。',
            '终': '**关键字**: `终` (L0 核心字)\n\n**用法**: `终：\\n    代码块`\n\n**说明**: L0 单字最终执行块关键字。',
            '导入': '**关键字**: `导入`\n\n**用法**: `导入 模块名。`\n\n**说明**: 导入模块。v4.0 推荐使用 L0 单字「导」替代。',
            '导': '**关键字**: `导` (L0 核心字)\n\n**用法**: `导 模块名。`\n\n**说明**: L0 单字导入关键字。',
            '导出': '**关键字**: `导出`\n\n**用法**: `导出 模块名。`\n\n**说明**: 导出模块。v4.0 推荐使用 L0 单字「出」替代。',
            '出': '**关键字**: `出` (L0 核心字)\n\n**用法**: `出 模块名。`\n\n**说明**: L0 单字导出关键字。',
            '从': '**关键字**: `从`\n\n**用法**: `从 模块 导入 名称。`\n\n**说明**: 从指定模块导入特定名称。',
            '跳出': '**关键字**: `跳出`\n\n**用法**: `跳出。`\n\n**说明**: 跳出当前循环。v4.0 推荐使用 L0 单字「跳」替代。',
            '跳': '**关键字**: `跳` (L0 核心字)\n\n**用法**: `跳。`\n\n**说明**: L0 单字跳出循环关键字。',
            '跳过': '**关键字**: `跳过`\n\n**用法**: `跳过。`\n\n**说明**: 跳过当前循环迭代，继续下一次。v4.0 推荐使用 L0 单字「过」替代。',
            '过': '**关键字**: `过` (L0 核心字)\n\n**用法**: `过。`\n\n**说明**: L0 单字跳过循环迭代关键字。',
            '真': '**关键字**: `真` (L0 核心字)\n\n**说明**: 布尔值真（True）。',
            '假': '**关键字**: `假` (L0 核心字)\n\n**说明**: 布尔值假（False）。',
            '空': '**关键字**: `空` (L0 核心字)\n\n**说明**: 空值（None/null）。',
            '且': '**关键字**: `且` (L0 核心字)\n\n**用法**: `条件1 且 条件2`\n\n**说明**: 逻辑与（AND）运算符。',
            '或': '**关键字**: `或` (L0 核心字)\n\n**用法**: `条件1 或 条件2`\n\n**说明**: 逻辑或（OR）运算符。',
            '非': '**关键字**: `非` (L0 核心字)\n\n**用法**: `非 条件`\n\n**说明**: 逻辑非（NOT）运算符。',
            '自': '**关键字**: `自` (L0 核心字)\n\n**用法**: `自.属性` 或 `自.方法()`\n\n**说明**: 自引用，等价于其他语言中的 self 或 this。',
            '之': '**关键字**: `之` (L0 核心字)\n\n**用法**: `对象之属性`\n\n**说明**: 属性提取符，等价于 `对象.属性`。',
            '并': '**关键字**: `并` (L0 核心字)\n\n**用法**: `数据 并 处理函数`\n\n**说明**: 管道连接符，将数据传递给处理函数。',
            '是': '**关键字**: `是` (L0 核心字)\n\n**用法**: `甲 是 乙`\n\n**说明**: 判断相等或类型判断，等价于 `==` 或 `isinstance`。',
            '异步': '**关键字**: `异步`\n\n**用法**: `异步 段落 函数名：\\n    代码块`\n\n**说明**: 定义异步函数。',
            '等待': '**关键字**: `等待`\n\n**用法**: `等待 异步调用`\n\n**说明**: 等待异步操作完成。',
            '新建': '**关键字**: `新建`\n\n**用法**: `新建 类名(参数...)`\n\n**说明**: 创建类实例。',
            '嵌入': '**关键字**: `嵌入`\n\n**用法**: `嵌入 语言：\\n    代码块\\n结束嵌入`\n\n**说明**: 嵌入其他语言代码块（如 Python）。v4.0 推荐使用 L0 单字「引」替代。',
            '引': '**关键字**: `引` (L0 核心字)\n\n**用法**: `引 语言：\\n    代码块\\n结束引`\n\n**说明**: L0 单字，嵌入其他语言代码块。',
            '打印': '**动词**: `打印`\n\n**用法**: `打印 值1, 值2, ...`\n\n**说明**: 向控制台输出内容。支持多个参数。',
            '输出': '**动词**: `输出`\n\n**用法**: `输出 值1, 值2, ...`\n\n**说明**: 向控制台输出内容，等价于「打印」。',
            '加': '**动词**: `加`\n\n**用法**: `甲 加 乙`\n\n**说明**: 加法运算，也用于字符串连接。',
            '减': '**动词**: `减`\n\n**用法**: `甲 减 乙`\n\n**说明**: 减法运算。',
            '乘': '**动词**: `乘`\n\n**用法**: `甲 乘 乙`\n\n**说明**: 乘法运算。',
            '除': '**动词**: `除`\n\n**用法**: `甲 除 乙`\n\n**说明**: 除法运算。',
            '等于': '**动词**: `等于`\n\n**用法**: `变量 等于 值。`\n\n**说明**: 赋值运算。',
            '大于': '**动词**: `大于`\n\n**用法**: `甲 大于 乙`\n\n**说明**: 大于比较。',
            '小于': '**动词**: `小于`\n\n**用法**: `甲 小于 乙`\n\n**说明**: 小于比较。',
            '转串': '**动词**: `转串`\n\n**用法**: `转串(值)`\n\n**说明**: 将值转换为字符串。',
            '转整数': '**动词**: `转整数`\n\n**用法**: `转整数(字符串)`\n\n**说明**: 将字符串转换为整数。',
            '转浮点': '**动词**: `转浮点`\n\n**用法**: `转浮点(字符串)`\n\n**说明**: 将字符串转换为浮点数。',
        }

        # 关键字用法提示（KW_HOVER_DOCS 未覆盖时的补充示例）
        kw_hints = {
            '定义': '`定义` 用于声明变量：\n\n```光明\n定义 变量名 等于 值。\n```',
            '设': '`设` 用于变量赋值：\n\n```光明\n设 变量名 为 值。\n```',
            '如果': '`如果` 用于条件判断：\n\n```光明\n如果 条件 那么：\n    代码\n结束。\n```',
            '若': '`若` 是 `如果` 的简写：\n\n```光明\n若 条件 则：\n    代码\n结束。\n```',
            '那么': '`那么` 是 `if` 语句的 then 分支标记，与 `如果` 搭配使用。',
            '否则': '`否则` 是条件语句的 else 分支，与 `如果` 搭配使用。',
            '否则若': '`否则若` 是条件语句的 elif 分支，用于多条件判断。',
            '遍历': '`遍历` 用于循环迭代：\n\n```光明\n遍历 变量 于 列表：\n    代码\n结束。\n```',
            '当': '`当` 用于条件循环：\n\n```光明\n当 条件：\n    代码\n结束。\n```',
            '返回': '`返回` 用于从函数中返回值：\n\n```光明\n返回 表达式。\n```',
            '跳出': '`跳出` 用于跳出当前循环。',
            '跳过': '`跳过` 用于跳过本次循环迭代，继续下一次。',
            '段落': '`段落` 用于定义函数：\n\n```光明\n段落 段名 接收 参数：\n    代码\n结束。\n```',
            '函数': '`函数` 用于定义函数（与 `段落` 同义）：\n\n```光明\n函数 函数名 接收 参数：\n    代码\n结束。\n```',
            '类': '`类` 用于定义类：\n\n```光明\n类 类名：\n    属性 变量。\n    构造 参数：\n        代码\n    结束。\n结束。\n```',
            '接口': '`接口` 用于定义接口：\n\n```光明\n接口 接口名：\n    ...\n结束。\n```',
            '尝试': '`尝试` 用于异常处理：\n\n```光明\n尝试：\n    代码\n捕获 异常：\n    处理\n结束。\n```',
            '抛出': '`抛出` 用于抛出异常：\n\n```光明\n抛出 异常对象。\n```',
            '导入': '`导入` 用于导入模块：\n\n```光明\n导入 模块名。\n```',
            '匹配': '`匹配` 用于模式匹配：\n\n```光明\n匹配 表达式：\n情况 模式：\n    代码\n结束。\n```',
            '异步': '`异步` 用于定义异步函数：\n\n```光明\n异步 段落 段名 接收 参数：\n    ...\n结束。\n```',
            '等待': '`等待` 用于等待异步操作完成：\n\n```光明\n等待 异步调用。\n```',
            '真': '布尔值 `真`（True）。',
            '假': '布尔值 `假`（False）。',
            '空': '空值 `空`（None）。',
        }
        
        # 检查是否是关键字（优先详细文档，其次用法提示）
        if word in KW_HOVER_DOCS:
            contents.append(KW_HOVER_DOCS[word])
        elif word in ALL_KEYWORDS:
            if word in kw_hints:
                contents.append(f"**关键字**: `{word}`\n\n{kw_hints[word]}")
            else:
                contents.append(f"**关键字**: `{word}`\n\n光明编程语言关键字，用于控制程序结构和逻辑。")
        
        # 检查是否是动词（KW_HOVER_DOCS 已覆盖的不重复输出）
        if word in VERB_ARITY and word not in KW_HOVER_DOCS:
            arity = VERB_ARITY[word]
            arity_desc = '无参数' if arity == 0 else f'{arity} 个参数' if arity > 0 else '可变参数'
            contents.append(f"**动词**: `{word}` (元数: {arity}, {arity_desc})")
        
        # 检查是否是 stdlib 函数
        if word in STDLIB_VERB_ARITY:
            stdlib_docs = {
                '读取文件': '读取文件内容\n\n参数: `path` (文件路径)\n返回: 文件内容字符串\n\n**示例**:\n```光明\n内容 = 读取文件("test.txt")\n```',
                '写入文件': '写入文件内容\n\n参数: `path` (文件路径), `content` (内容)\n\n**示例**:\n```光明\n写入文件("test.txt", "你好")\n```',
                '文件存在': '检查文件是否存在\n\n参数: `path` (文件路径)\n返回: 布尔值',
                '目录存在': '检查目录是否存在\n\n参数: `path` (目录路径)\n返回: 布尔值',
                '路径存在': '检查路径是否存在\n\n参数: `path` (路径)\n返回: 布尔值',
                '创建目录': '创建目录（自动创建父目录）\n\n参数: `path` (目录路径)',
                '删除文件': '删除文件\n\n参数: `path` (文件路径)',
                '列出目录': '列出目录内容\n\n参数: `path` (目录路径, 默认当前目录)\n返回: 文件名列表',
                '绝对路径': '获取绝对路径\n\n参数: `path` (路径)\n返回: 绝对路径字符串',
                '连接路径': '连接多个路径\n\n参数: `*paths` (路径片段)\n返回: 连接后的路径',
                '环境变量': '获取环境变量\n\n参数: `name` (变量名), `default` (默认值)\n返回: 变量值或默认值',
                '退出程序': '退出程序\n\n参数: `code` (退出码, 默认0)',
                '当前目录': '获取当前工作目录\n\n返回: 路径字符串',
                '切换目录': '切换工作目录\n\n参数: `path` (目录路径)',
                '执行命令': '执行系统命令\n\n参数: `command` (命令字符串)\n返回: 退出码',
                '读取行': '从标准输入读取一行\n\n返回: 读取的字符串（不含换行符）',
                '打印输出': '向标准输出打印文本并换行\n\n参数: `text` (要打印的文本)',
                '解析JSON': '解析 JSON 字符串\n\n参数: `text` (JSON 字符串)\n返回: 光明值',
                '序列化JSON': '将值序列化为 JSON 字符串\n\n参数: `value` (值), `缩进` (可选)\n返回: JSON 字符串',
                '转整数': '将字符串转换为整数\n\n参数: `text` (字符串)\n返回: 整数',
                '转浮点': '将字符串转换为浮点数\n\n参数: `text` (字符串)\n返回: 浮点数',
                '转字符串': '将值转换为字符串\n\n参数: `value` (任意值)\n返回: 字符串',
                '字符串长度': '获取字符串长度\n\n参数: `text` (字符串)\n返回: 整数',
                '分割字符串': '分割字符串\n\n参数: `text` (字符串), `separator` (分隔符, 可选)',
                '连接字符串': '连接字符串列表\n\n参数: `parts` (列表), `separator` (分隔符, 默认空串)',
                '替换字符串': '替换字符串\n\n参数: `text` (原串), `old` (旧串), `new` (新串)',
                '去除空白': '去除首尾空白\n\n参数: `text` (字符串)\n返回: 处理后的字符串',
                '随机整数': '生成范围内的随机整数\n\n参数: `最小` (包含), `最大` (包含)\n返回: 随机整数',
                '随机浮点': '生成 [0.0, 1.0) 范围内的随机浮点数\n\n返回: 随机浮点数',
                '随机选择': '从列表中随机选择一个元素\n\n参数: `列表` (源列表)\n返回: 选中的元素，空列表返回空',
                '阶乘': '计算 n 的阶乘\n\n参数: `n` (非负整数)\n返回: n!',
                '平均数': '计算列表的平均值\n\n参数: `数据` (数值列表)\n返回: 平均值',
                '中位数': '计算列表的中位数\n\n参数: `数据` (数值列表)\n返回: 中位数',
                '求和': '计算列表中所有数值的和\n\n参数: `数据` (数值列表)\n返回: 总和',
                '圆周率': '返回圆周率 π 的近似值\n\n返回: 3.141592653589793',
                '自然常数': '返回自然常数 e 的近似值\n\n返回: 2.718281828459045',
            }
            arity = STDLIB_VERB_ARITY[word]
            arity_desc = '无参数' if arity == 0 else f'{arity} 个参数' if arity > 0 else '可变参数'
            doc_text = stdlib_docs.get(word, '标准库函数')
            contents.append(f"**内置函数**: `{word}`\n\n{arity_desc}\n\n{doc_text}")
        
        # 检查是否是本地定义
        if doc.uri in self.doc_manager.definitions:
            info = self.doc_manager.definitions[doc.uri].get(word + '__info')
            if info:
                if info['type'] == '函数':
                    params_str = ', '.join(info['params'])
                    # 获取参数类型信息
                    typed_params = []
                    for p in info['params']:
                        ptype = '任意'
                        if doc.uri in self.doc_manager.type_info:
                            ptype = self.doc_manager.type_info[doc.uri].get(p, '任意')
                        typed_params.append(f"{p}: {ptype}")
                    typed_params_str = ', '.join(typed_params)
                    contents.append(f"**函数**: `{word}({typed_params_str})`\n\n定义于第 {info['line'] + 1} 行")

            if word in self.doc_manager.definitions[doc.uri]:
                def_info = self.doc_manager.definitions[doc.uri][word]
                def_line = def_info['range']['start']['line'] + 1
                # 检查是否是变量定义
                is_var = word not in {k.replace('__info', '') for k in self.doc_manager.definitions[doc.uri] if k.endswith('__info')}
                if is_var and word not in ALL_KEYWORDS and word not in VERB_ARITY:
                    if not info:  # 不是函数时
                        contents.append(f"定义于第 {def_line} 行")

        # 类型信息（从缓存获取）
        type_str = None
        if doc.uri in self.doc_manager.type_info:
            type_str = self.doc_manager.type_info[doc.uri].get(word)

        # 如果缓存中没有类型信息，尝试从 AST 解析
        if type_str is None:
            try:
                parser = LightParser()
                ast = parser.parse(doc.text)
                
                def find_type(node):
                    nonlocal type_str
                    if type_str:
                        return
                    node_type = type(node).__name__
                    name = getattr(node, 'name', None)
                    if name == word:
                        if node_type == 'VarDecl':
                            ta = getattr(node, 'type_annotation', None)
                            if ta:
                                type_str = str(ta)
                        elif node_type == 'Paragraph':
                            return_type = getattr(node, 'return_type', None)
                            params = getattr(node, 'params', [])
                            if return_type or params:
                                type_str = '函数'
                        elif node_type == 'ClassDefinition':
                            type_str = '类'
                
                self.doc_manager._walk_ast(ast, find_type)
            except Exception:
                pass

        if type_str:
            has_type = any('类型' in c for c in contents)
            if not has_type:
                contents.append(f"**类型**: `{type_str}`")
        
        # 内置类型提示
        if word in BUILTIN_TYPES:
            type_docs = {
                '数': '通用数值类型，包含整数和浮点数。',
                '整数': '整数类型，如 1, 42, -3。',
                '浮数': '浮点数类型，如 3.14, -0.5。',
                '小数': '浮点数类型的别名。',
                '串': '字符串类型的别名。',
                '文本': '字符串类型，如 "你好", \'光明\'。',
                '列': '列表类型的别名。',
                '列表': '列表类型，有序集合，如 [1, 2, 3]。',
                '典': '字典类型的别名。',
                '字典': '字典类型，键值对集合，如 {"a": 1}。',
                '布尔': '布尔值类型，取值为真或假。',
                '空': '空类型，表示没有值。',
                '任意': '任意类型，可接受任何值。',
            }
            if word in type_docs:
                contents.append(f"**内置类型**: `{word}`\n\n{type_docs[word]}")
        
        if not contents:
            return None
        
        return {
            'contents': {
                'kind': 'markdown',
                'value': '\n\n---\n\n'.join(contents)
            },
            'range': {
                'start': {'line': line, 'character': start},
                'end': {'line': line, 'character': end}
            }
        }
    
    def _handle_document_highlight(self, params: Dict) -> List[Dict]:
        """处理文档高亮请求，高亮光标位置处符号的所有出现"""
        doc = self.doc_manager.get_document(params.get('textDocument', {}).get('uri', ''))
        if not doc:
            return []
        
        position = params.get('position', {})
        line = position.get('line', 0)
        character = position.get('character', 0)
        
        # 获取光标位置的词
        line_text = doc.get_line(line)
        start = character
        end = character
        
        while start > 0:
            ch = line_text[start - 1]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                start -= 1
            else:
                break
        while end < len(line_text):
            ch = line_text[end]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                end += 1
            else:
                break
        
        word = line_text[start:end]
        if not word:
            return []
        
        # 查找所有出现
        highlights = []
        for i, ln in enumerate(doc.lines):
            pos = 0
            while True:
                idx = ln.find(word, pos)
                if idx == -1:
                    break
                # 检查是否是完整词
                before_ok = idx == 0 or not (
                    ln[idx - 1].isalnum() or '\u4e00' <= ln[idx - 1] <= '\u9fff'
                )
                after_ok = idx + len(word) >= len(ln) or not (
                    ln[idx + len(word)].isalnum() or
                    '\u4e00' <= ln[idx + len(word)] <= '\u9fff'
                )
                if before_ok and after_ok:
                    highlights.append({
                        'range': {
                            'start': {'line': i, 'character': idx},
                            'end': {'line': i, 'character': idx + len(word)}
                        }
                    })
                pos = idx + len(word)
        
        return highlights
    
    def _handle_signature_help(self, params: Dict) -> Optional[Dict]:
        """处理签名帮助请求，显示函数调用时的参数信息"""
        doc = self.doc_manager.get_document(params.get('textDocument', {}).get('uri', ''))
        if not doc:
            return None
        
        position = params.get('position', {})
        line = position.get('line', 0)
        character = position.get('character', 0)
        
        # 获取当前行文本
        line_text = doc.get_line(line)
        
        # 向前查找函数调用括号
        # 找到光标前的 '(' 或 '（' 位置
        paren_pos = -1
        depth = 0
        for i in range(character - 1, -1, -1):
            ch = line_text[i]
            if ch in ('(', '（'):
                if depth == 0:
                    paren_pos = i
                    break
                depth += 1
            elif ch in (')', '）'):
                depth -= 1
        
        if paren_pos == -1:
            return None
        
        # 从括号位置向前提取函数名
        func_start = paren_pos - 1
        while func_start >= 0:
            ch = line_text[func_start]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                func_start -= 1
            else:
                break
        func_name = line_text[func_start + 1:paren_pos]
        
        if not func_name:
            return None
        
        # 计算当前参数索引（按逗号分割）
        arg_text = line_text[paren_pos + 1:character]
        arg_index = 0
        if arg_text.strip():
            arg_index = 1  # 至少有一个参数开始输入
            for ch in arg_text:
                if ch in ('，', ','):
                    arg_index += 1
        # 如果光标在逗号后面，参数索引加1
        if arg_index > 0 and character > 0 and line_text[character - 1] in ('，', ','):
            arg_index += 1
        if arg_index > 0:
            arg_index -= 1  # 转为0-based
        
        signatures = []
        active_parameter = 0
        
        # 检查是否是 stdlib 函数
        if func_name in STDLIB_VERB_ARITY:
            arity = STDLIB_VERB_ARITY[func_name]
            if arity >= 0:
                params_list = []
                for i in range(arity):
                    params_list.append(f'参数{i+1}')
                params_str = ', '.join(params_list)
                signatures.append({
                    'label': f'{func_name}({params_str})',
                    'parameters': [{'label': p} for p in params_list]
                })
                active_parameter = min(arg_index, arity - 1) if arity > 0 else 0
        
        # 检查是否是动词
        if func_name in VERB_ARITY:
            arity = VERB_ARITY[func_name]
            if arity >= 0:
                params_list = []
                for i in range(arity):
                    params_list.append(f'参数{i+1}')
                params_str = ', '.join(params_list)
                signatures.append({
                    'label': f'{func_name}({params_str})',
                    'parameters': [{'label': p} for p in params_list]
                })
                active_parameter = min(arg_index, arity - 1) if arity > 0 else 0
        
        # 检查是否是本地定义的函数
        if doc.uri in self.doc_manager.definitions:
            info = self.doc_manager.definitions[doc.uri].get(func_name + '__info')
            if info and info.get('type') == '函数':
                params_list = info.get('params', [])
                params_str = ', '.join(params_list)
                signatures.append({
                    'label': f'{func_name}({params_str})',
                    'parameters': [{'label': p} for p in params_list]
                })
                active_parameter = min(arg_index, len(params_list) - 1) if params_list else 0
        
        if not signatures:
            return None
        
        return {
            'signatures': signatures,
            'activeSignature': 0,
            'activeParameter': active_parameter
        }
    
    def _handle_definition(self, params: Dict) -> Optional[Dict]:
        """处理跳转定义请求"""
        doc = self.doc_manager.get_document(params.get('textDocument', {}).get('uri', ''))
        if not doc:
            return None
        
        position = params.get('position', {})
        line = position.get('line', 0)
        character = position.get('character', 0)
        
        # 获取当前位置的词
        line_text = doc.get_line(line)
        start = character
        end = character
        
        while start > 0:
            ch = line_text[start - 1]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                start -= 1
            else:
                break
        while end < len(line_text):
            ch = line_text[end]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                end += 1
            else:
                break
        
        word = line_text[start:end]
        if not word:
            return None
        
        # 1. 优先从已缓存的 definitions 中查找（当前文档）
        if doc.uri in self.doc_manager.definitions:
            if word in self.doc_manager.definitions[doc.uri]:
                return self.doc_manager.definitions[doc.uri][word]

        # 2. 跨文档查找定义（遍历所有已打开文档）
        for other_uri, defs in self.doc_manager.definitions.items():
            if other_uri == doc.uri:
                continue
            if word in defs:
                return defs[word]

        # 3. 尝试解析 AST 作为 fallback 查找定义
        try:
            parser = LightParser()
            ast = parser.parse(doc.text)
            found = None

            def search(node):
                nonlocal found
                if found:
                    return
                node_type = type(node).__name__
                name = getattr(node, 'name', None)
                if name == word and node_type in ('VarDecl', 'Paragraph', 'ClassDefinition',
                                                   'MethodDefinition', 'AttributeDeclaration',
                                                   'InterfaceDefinition'):
                    lineno = getattr(node, 'line', 1) - 1
                    col = getattr(node, 'col', 0)
                    found = {
                        'uri': doc.uri,
                        'range': {
                            'start': {'line': lineno, 'character': col},
                            'end': {'line': lineno, 'character': col + len(str(name))}
                        }
                    }
                    return

            self.doc_manager._walk_ast(ast, search)
            if found:
                return found
        except Exception:
            pass

        # 4. 跨文档 AST 查找（遍历所有已打开文档的 AST）
        for other_uri, other_doc in self.doc_manager.documents.items():
            if other_uri == doc.uri:
                continue
            try:
                other_parser = LightParser()
                other_ast = other_parser.parse(other_doc.text)
                other_found = None

                def other_search(node):
                    nonlocal other_found
                    if other_found:
                        return
                    node_type = type(node).__name__
                    name = getattr(node, 'name', None)
                    if name == word and node_type in ('VarDecl', 'Paragraph', 'ClassDefinition',
                                                       'MethodDefinition', 'AttributeDeclaration',
                                                       'InterfaceDefinition'):
                        lineno = getattr(node, 'line', 1) - 1
                        col = getattr(node, 'col', 0)
                        other_found = {
                            'uri': other_uri,
                            'range': {
                                'start': {'line': lineno, 'character': col},
                                'end': {'line': lineno, 'character': col + len(str(name))}
                            }
                        }
                        return

                self.doc_manager._walk_ast(other_ast, other_search)
                if other_found:
                    return other_found
            except Exception:
                continue

        return None
    
    def _handle_document_symbol(self, params: Dict) -> List[Dict]:
        """处理文档符号请求"""
        uri = params.get('textDocument', {}).get('uri', '')
        return self.doc_manager.symbols.get(uri, [])
    
    def _handle_references(self, params: Dict) -> List[Dict]:
        """处理查找引用请求"""
        doc = self.doc_manager.get_document(params.get('textDocument', {}).get('uri', ''))
        if not doc:
            return []

        position = params.get('position', {})
        line = position.get('line', 0)
        character = position.get('character', 0)

        line_text = doc.get_line(line)
        start = character
        end = character
        while start > 0:
            ch = line_text[start - 1]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                start -= 1
            else:
                break
        while end < len(line_text):
            ch = line_text[end]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                end += 1
            else:
                break

        word = line_text[start:end]
        if not word:
            return []

        references = []
        for uri, doc_obj in self.doc_manager.documents.items():
            for i, line_text in enumerate(doc_obj.lines):
                pos = 0
                while True:
                    idx = line_text.find(word, pos)
                    if idx == -1:
                        break
                    references.append({
                        'uri': uri,
                        'range': {
                            'start': {'line': i, 'character': idx},
                            'end': {'line': i, 'character': idx + len(word)}
                        }
                    })
                    pos = idx + len(word)

        return references

    def _handle_formatting(self, params: Dict) -> List[Dict]:
        """处理文档格式化请求"""
        uri = params.get('textDocument', {}).get('uri', '')
        doc = self.doc_manager.get_document(uri)
        if not doc:
            return []

        options = params.get('options', {})
        tab_size = options.get('tabSize', 4)
        insert_spaces = options.get('insertSpaces', True)

        edits = self._format_document(doc.text, tab_size, insert_spaces)
        return edits

    def _handle_range_formatting(self, params: Dict) -> List[Dict]:
        """处理范围格式化请求"""
        uri = params.get('textDocument', {}).get('uri', '')
        doc = self.doc_manager.get_document(uri)
        if not doc:
            return []

        range_info = params.get('range', {})
        options = params.get('options', {})
        tab_size = options.get('tabSize', 4)
        insert_spaces = options.get('insertSpaces', True)

        # 提取范围内的文本
        start_line = range_info.get('start', {}).get('line', 0)
        end_line = range_info.get('end', {}).get('line', 0)
        lines = doc.text.split('\n')
        range_text = '\n'.join(lines[start_line:end_line + 1])

        edits = self._format_document(
            doc.text, tab_size, insert_spaces,
            start_line=start_line, end_line=end_line
        )
        return edits

    def _format_document(self, text: str, tab_size: int, insert_spaces: bool,
                         start_line: int = None, end_line: int = None) -> List[Dict]:
        """格式化文档内容 — AST 结构感知格式化"""
        indent = ' ' * tab_size if insert_spaces else '\t'
        lines = text.split('\n')
        total_lines = len(lines)

        if start_line is None:
            start_line = 0
        if end_line is None:
            end_line = total_lines - 1

        # 1. 先尝试用 AST 计算每行的缩进级别
        indent_map = self._compute_indent_from_ast(text, lines)

        # 2. 逐行格式化
        formatted_lines = list(lines)
        for i in range(start_line, end_line + 1):
            raw = lines[i]
            stripped = raw.strip()

            if not stripped:
                # 保留空行
                continue

            # 注释行：保留原有缩进
            if stripped.startswith('#'):
                # 保持注释在所在缩进位置
                existing_indent = len(raw) - len(raw.lstrip())
                formatted_lines[i] = indent * (existing_indent // tab_size) + stripped
                continue

            # 使用 AST 计算的缩进级别，如果不可用则回退到启发式
            level = indent_map.get(i)
            if level is None:
                level = self._heuristic_indent_level(stripped, lines, i)

            formatted_lines[i] = indent * level + stripped

        # 3. 在操作符周围添加空格（仅对非注释、非空行）
        for i in range(start_line, end_line + 1):
            raw = formatted_lines[i]
            stripped = raw.strip()
            if not stripped or stripped.startswith('#'):
                continue
            # 去掉缩进再处理，然后重新加回缩进
            indent_str = raw[:len(raw) - len(raw.lstrip())]
            cleaned = self._add_operator_spacing(stripped)
            if cleaned != stripped:
                formatted_lines[i] = indent_str + cleaned

        new_text = '\n'.join(formatted_lines)

        if new_text == text:
            return []

        return [{
            'range': {
                'start': {'line': start_line, 'character': 0},
                'end': {'line': end_line, 'character': len(lines[end_line])}
            },
            'newText': '\n'.join(formatted_lines[start_line:end_line + 1])
        }]

    def _compute_indent_from_ast(self, text: str, lines: list) -> Dict[int, int]:
        """通过 AST 计算每行应有的缩进级别"""
        indent_map = {}
        try:
            parser = LightParser()
            ast = parser.parse(text)

            def visit(node, parent_indent=0):
                node_type = type(node).__name__
                lineno = getattr(node, 'line', 1) - 1
                if lineno < 0 or lineno >= len(lines):
                    return

                # 块级节点，其子节点应缩进
                if node_type in ('Module', 'IfStmt', 'ForeachStmt', 'WhileStmt',
                                  'Paragraph', 'ClassDefinition', 'MethodDefinition',
                                  'TryStmt', 'MatchStmt', 'MatchCase', 'WithStmt',
                                  'ElseBody', 'CatchBody', 'FinallyBody'):
                    indent_map[lineno] = parent_indent

                    # 获取子节点列表
                    body_attrs = []
                    if node_type == 'Module':
                        body_attrs = [('statements', 0)]
                    elif node_type == 'Paragraph':
                        body_attrs = [('body', parent_indent + 1)]
                    elif node_type == 'ClassDefinition':
                        body_attrs = [('attributes', parent_indent + 1), ('methods', parent_indent + 1)]
                    elif node_type == 'MethodDefinition':
                        body_attrs = [('body', parent_indent + 1)]
                    elif node_type == 'IfStmt':
                        body_attrs = [('then_body', parent_indent + 1), ('else_body', parent_indent + 1)]
                    elif node_type == 'ForeachStmt':
                        body_attrs = [('body', parent_indent + 1)]
                    elif node_type == 'WhileStmt':
                        body_attrs = [('body', parent_indent + 1)]
                    elif node_type == 'TryStmt':
                        body_attrs = [('try_body', parent_indent + 1), ('catch_body', parent_indent + 1),
                                       ('finally_body', parent_indent + 1)]
                    elif node_type == 'MatchStmt':
                        body_attrs = [('cases', parent_indent + 1)]
                    elif node_type == 'MatchCase':
                        body_attrs = [('body', parent_indent + 1)]
                    elif node_type == 'WithStmt':
                        body_attrs = [('body', parent_indent + 1)]

                    for attr_name, child_indent in body_attrs:
                        children = getattr(node, attr_name, None)
                        if children is None:
                            continue
                        if not isinstance(children, list):
                            children = [children]
                        for child in children:
                            if isinstance(child, ASTNode):
                                visit(child, child_indent)
                else:
                    indent_map[lineno] = parent_indent

            visit(ast, 0)
        except Exception:
            pass
        return indent_map

    def _heuristic_indent_level(self, stripped: str, lines: list, idx: int) -> int:
        """启发式计算缩进级别（AST 不可用时回退）"""
        level = 0
        for j in range(idx):
            prev = lines[j].strip()
            if not prev:
                continue
            # 减少缩进关键字（含 L0 单字简写）
            if any(prev.startswith(kw) for kw in ['结束', '否则若', '否若', '否则', '否', '捕获', '捕',
                                                     '最终', '终', '情况', '结束嵌入']):
                level = max(0, level - 1)
            # 增加缩进（含 L0 单字简写）
            if any(prev.endswith(kw) for kw in ['：', ':']):
                if any(prev.startswith(kw) for kw in
                       ['如果', '若', '遍历', '遍', '当', '段落', '段', '函数', '类', '接口', '接',
                        '尝试', '试', '匹配', '配', '否则若', '否若', '否则', '否', '捕获', '捕', '使用']):
                    level += 1
                elif any(kw in prev for kw in ['接收', '构造']):
                    level += 1
        return level

    def _add_operator_spacing(self, line: str) -> str:
        """在操作符周围添加一致的空格"""
        # 跳过字符串字面量
        in_string = False
        string_char = None
        result = []
        i = 0
        while i < len(line):
            ch = line[i]
            # 处理字符串
            if ch in ('"', "'", '「'):
                if not in_string:
                    in_string = True
                    string_char = ch
                elif ch == string_char:
                    in_string = False
                result.append(ch)
                i += 1
                continue
            if in_string:
                result.append(ch)
                i += 1
                continue

            # 处理中文引号
            if ch in ('"', '」'):
                result.append(ch)
                i += 1
                continue

            # 运算符
            if ch in ('=', '＋', '－', '×', '÷', '＋', '－', '×', '÷'):
                # 跳过已经有一侧空格的
                if i > 0 and line[i - 1].isspace() and i + 1 < len(line) and line[i + 1].isspace():
                    result.append(ch)
                else:
                    result.append(f' {ch} ')
                i += 1
                continue

            # 逗号后加空格
            if ch in ('，', ',', '、'):
                result.append(ch)
                if i + 1 < len(line) and not line[i + 1].isspace() and line[i + 1] not in ('）', ')', '】'):
                    result.append(' ')
                i += 1
                continue

            result.append(ch)
            i += 1

        return ''.join(result)

    def _handle_rename(self, params: Dict) -> Optional[Dict]:
        """处理重命名请求"""
        uri = params.get('textDocument', {}).get('uri', '')
        doc = self.doc_manager.get_document(uri)
        if not doc:
            return None

        position = params.get('position', {})
        new_name = params.get('newName', '')
        line = position.get('line', 0)
        character = position.get('character', 0)

        # 获取当前光标处的词
        line_text = doc.get_line(line)
        start = character
        end = character
        while start > 0:
            ch = line_text[start - 1]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                start -= 1
            else:
                break
        while end < len(line_text):
            ch = line_text[end]
            if ch.isalnum() or '\u4e00' <= ch <= '\u9fff':
                end += 1
            else:
                break
        old_name = line_text[start:end]

        if not old_name or not new_name:
            return None

        # 查找所有引用
        changes = {}
        for doc_uri, doc_obj in self.doc_manager.documents.items():
            doc_edits = []
            for i, doc_line in enumerate(doc_obj.lines):
                pos = 0
                while True:
                    idx = doc_line.find(old_name, pos)
                    if idx == -1:
                        break
                    # 检查是否是完整词（前后不是中文字符或字母数字）
                    before_ok = idx == 0 or not (
                        doc_line[idx - 1].isalnum() or '\u4e00' <= doc_line[idx - 1] <= '\u9fff'
                    )
                    after_ok = idx + len(old_name) >= len(doc_line) or not (
                        doc_line[idx + len(old_name)].isalnum() or
                        '\u4e00' <= doc_line[idx + len(old_name)] <= '\u9fff'
                    )
                    if before_ok and after_ok:
                        doc_edits.append({
                            'range': {
                                'start': {'line': i, 'character': idx},
                                'end': {'line': i, 'character': idx + len(old_name)}
                            },
                            'newText': new_name
                        })
                    pos = idx + len(old_name)

            if doc_edits:
                changes[doc_uri] = doc_edits

        if not changes:
            return None

        return {'changes': changes}

    def _handle_code_action(self, params: Dict) -> List[Dict]:
        """处理代码操作请求（快速修复 + 重构）"""
        uri = params.get('textDocument', {}).get('uri', '')
        doc = self.doc_manager.get_document(uri)
        if not doc:
            return []

        context = params.get('context', {})
        diagnostics = context.get('diagnostics', [])
        code_actions = []

        for diag in diagnostics:
            msg = diag.get('message', '')
            d_range = diag.get('range', {})

            # 语法错误快速修复建议
            if '意外的标记' in msg:
                code_actions.append({
                    'title': '查看光明语法文档',
                    'kind': 'quickfix',
                    'diagnostics': [diag],
                    'command': {
                        'title': '打开语法文档',
                        'command': 'vscode.open',
                        'arguments': ['https://github.com/light-lang/light/blob/main/docs/syntax.md']
                    }
                })
            elif '名称未定义' in msg or '未定义' in msg:
                var_name = msg.split("'")[1] if "'" in msg else "变量"
                code_actions.append({
                    'title': '添加变量定义',
                    'kind': 'quickfix',
                    'diagnostics': [diag],
                    'edit': {
                        'changes': {
                            uri: [{
                                'range': d_range,
                                'newText': f'定义 {var_name} 等于 空。\n'
                            }]
                        }
                    }
                })

        # 获取选中范围 (用于重构)
        range_info = params.get('range', {})
        if range_info and range_info.get('start') and range_info.get('end'):
            start_line = range_info['start'].get('line', 0)
            end_line = range_info['end'].get('line', 0)
            start_char = range_info['start'].get('character', 0)
            end_char = range_info['end'].get('character', 0)

            # 提取函数重构
            if start_line < end_line or (start_line == end_line and end_char - start_char > 5):
                selected_text = ''
                if start_line == end_line:
                    selected_text = doc.get_line(start_line)[start_char:end_char]
                else:
                    lines = []
                    for ln in range(start_line, end_line + 1):
                        ln_text = doc.get_line(ln)
                        if ln == start_line:
                            lines.append(ln_text[start_char:])
                        elif ln == end_line:
                            lines.append(ln_text[:end_char])
                        else:
                            lines.append(ln_text)
                    selected_text = '\n'.join(lines)

                if selected_text.strip():
                    code_actions.append({
                        'title': '提取函数 (将选中代码提取为新函数)',
                        'kind': 'refactor.extract.function',
                        'diagnostics': [],
                        'command': {
                            'title': '提取函数',
                            'command': 'light.extractFunction',
                            'arguments': [uri, start_line, end_line, selected_text]
                        }
                    })

            # 内联变量重构（选中单个变量引用时）
            if start_line == end_line and end_char - start_char > 0:
                word = doc.get_line(start_line)[start_char:end_char]
                if word and word.isidentifier():
                    code_actions.append({
                        'title': f"内联变量 '{word}' (将变量替换为其值)",
                        'kind': 'refactor.inline',
                        'diagnostics': [],
                        'command': {
                            'title': '内联变量',
                            'command': 'light.inlineVariable',
                            'arguments': [uri, word, start_line, start_char]
                        }
                    })

        return code_actions

    def _handle_signature_help(self, params: Dict) -> Optional[Dict]:
        """处理函数签名帮助请求"""
        doc = self.doc_manager.get_document(params.get('textDocument', {}).get('uri', ''))
        if not doc:
            return None

        position = params.get('position', {})
        line = position.get('line', 0)
        character = position.get('character', 0)
        line_text = doc.get_line(line)

        # 查找当前正在调用的函数名
        # 从光标位置向左搜索，找到函数调用开始处
        func_name = ''
        paren_depth = 0
        for i in range(character - 1, -1, -1):
            ch = line_text[i]
            if ch == ')' or ch == '）':
                paren_depth += 1
            elif ch == '(' or ch == '（':
                if paren_depth > 0:
                    paren_depth -= 1
                else:
                    # 找到函数参数开始，向左找函数名
                    j = i - 1
                    while j >= 0 and (line_text[j].isalnum() or '\u4e00' <= line_text[j] <= '\u9fff' or line_text[j] == '_'):
                        j -= 1
                    func_name = line_text[j + 1:i]
                    break

        if not func_name:
            return {'signatures': [], 'activeSignature': 0, 'activeParameter': 0}

        # 计算当前参数索引
        active_param = 0
        depth = 0
        for i in range(character - 1, 0, -1):
            ch = line_text[i]
            if ch == ')' or ch == '）':
                depth += 1
            elif ch == '(' or ch == '（':
                if depth > 0:
                    depth -= 1
                else:
                    break
            elif ch == ',' or ch == '，':
                if depth == 0:
                    active_param += 1

        # 查找函数签名
        signatures = []
        if doc.uri in self.doc_manager.definitions:
            info = self.doc_manager.definitions[doc.uri].get(func_name + '__info')
            if info and info.get('type') == '函数':
                params_list = info.get('params', [])
                label = f"{func_name}({', '.join(params_list)})"
                signatures.append({
                    'label': label,
                    'documentation': {'kind': 'markdown', 'value': f'**函数**: `{func_name}`\n\n参数: {", ".join(params_list)}'},
                    'parameters': [{'label': p} for p in params_list]
                })

        # 检查是否是内置动词
        if not signatures and func_name in VERB_ARITY:
            arity = VERB_ARITY[func_name]
            if arity == -1:
                label = f"{func_name}(参数...)"
                params = [{'label': f'参数{i+1}'} for i in range(3)]
            elif arity == 0:
                label = f"{func_name}()"
                params = []
            else:
                params = [{'label': f'参数{i+1}'} for i in range(arity)]
                label = f"{func_name}({', '.join(p['label'] for p in params)})"
            signatures.append({
                'label': label,
                'documentation': {'kind': 'markdown', 'value': f'**动词**: `{func_name}` (元数: {arity})'},
                'parameters': params
            })

        if not signatures:
            return {'signatures': [], 'activeSignature': 0, 'activeParameter': 0}

        return {
            'signatures': signatures,
            'activeSignature': 0,
            'activeParameter': min(active_param, len(signatures[0].get('parameters', [])) - 1) if signatures[0].get('parameters') else 0
        }

    def _handle_semantic_tokens(self, params: Dict) -> Dict:
        """处理语义令牌请求（语法高亮增强）"""
        doc = self.doc_manager.get_document(params.get('textDocument', {}).get('uri', ''))
        if not doc:
            return {'data': []}

        try:
            from lexer import Lexer
            from tokens import TokenType as TT

            lexer = Lexer()
            tokens = lexer.tokenize(doc.text)

            # Token type mapping
            token_type_map = {
                TT.KEYWORD: 0,      # keyword
                TT.IDENTIFIER: 1,   # function (temporary, will be refined)
                TT.STRING: 3,       # string
                TT.NUMBER: 4,       # number
                TT.OPERATOR: 5,     # operator
                TT.COMMENT: 6,      # comment
            }

            # L0/L1 keyword modifier mapping
            l0_keywords = {'若', '否', '当', '遍', '跳', '过', '返', '设', '段', '类', '承', '接', '配',
                          '试', '捕', '抛', '终', '自', '之', '并', '从', '是', '且', '或', '非', '真', '假', '空',
                          '导', '出'}

            data = []
            prev_line = 0
            prev_col = 0

            for tok in tokens:
                if tok.type == TT.EOF or tok.type == TT.NEWLINE:
                    continue

                tt = token_type_map.get(tok.type)
                if tt is None:
                    continue

                line = tok.line - 1
                col = tok.col - 1
                length = len(tok.value)

                # Delta encoding
                if prev_line == line and prev_col == col:
                    delta_line = 0
                    delta_col = 0
                elif prev_line == line:
                    delta_line = 0
                    delta_col = col - prev_col
                else:
                    delta_line = line - prev_line
                    delta_col = col

                prev_line = line
                prev_col = col

                # Modifier: 0 = none
                modifier = 0
                if tok.type == TT.KEYWORD and tok.value in l0_keywords:
                    modifier = 0  # Could use bit flags for L0 keyword modifier

                data.extend([delta_line, delta_col, length, tt, modifier])

            return {'data': data}
        except Exception:
            return {'data': []}

    def _handle_semantic_tokens_full(self, params: Dict) -> Dict:
        """处理语义令牌全量请求

        基于文本分析生成语义令牌，分类为：
        - keyword: 光明关键字（设/返回/如果/遍历/当/类/段落等）
        - function: 函数名
        - variable: 变量名
        - class: 类名
        - parameter: 参数名
        - property: 属性名
        - number: 数字字面量
        - string: 字符串字面量
        - operator: 运算符
        - comment: 注释
        """
        uri = params.get('textDocument', {}).get('uri', '')
        doc = self.doc_manager.get_document(uri)
        if not doc:
            return {'data': []}

        data = []
        for line_idx, line_text in enumerate(doc.lines):
            # 令牌编码: line, start_char, length, token_type, token_modifiers
            i = 0
            line_len = len(line_text)
            while i < line_len:
                ch = line_text[i]

                # 跳过空白
                if ch in (' ', '\t'):
                    i += 1
                    continue

                # 注释：以 # 开头
                if ch == '#':
                    comment_end = line_len
                    data.extend([line_idx, i, comment_end - i, 14, 0])  # comment type = 14
                    break

                # 字符串字面量
                if ch in ('"', "'"):
                    str_start = i
                    i += 1
                    while i < line_len and line_text[i] != ch:
                        if line_text[i] == '\\':
                            i += 1  # 跳过转义
                        i += 1
                    if i < line_len:
                        i += 1  # 跳过结束引号
                    data.extend([line_idx, str_start, i - str_start, 11, 0])  # string type = 11
                    continue

                # 数字字面量
                if ch.isdigit() or (ch == '.' and i + 1 < line_len and line_text[i + 1].isdigit()):
                    num_start = i
                    while i < line_len and (line_text[i].isdigit() or line_text[i] == '.'):
                        i += 1
                    data.extend([line_idx, num_start, i - num_start, 12, 0])  # number type = 12
                    continue

                # 中文/字母标识符
                if ch.isalpha() or '\u4e00' <= ch <= '\u9fff':
                    word_start = i
                    while i < line_len and (line_text[i].isalnum() or '\u4e00' <= line_text[i] <= '\u9fff' or line_text[i] == '_'):
                        i += 1
                    word = line_text[word_start:i]

                    # 判断 token 类型
                    keywords = {'设', '为', '如果', '否则', '遍历', '于', '当', '返回', '类',
                                '段落', '协议', '构造', '属性', '己', '父', '真', '假', '空',
                                '尝试', '捕获', '最终', '抛出', '使用', '导入', '从', '匹配',
                                '若', '跳出', '跳过', '删除', '静态', '特性', '类方法', '异步',
                                '等待', '全局', '非局部', '产出', '断言', '空操作', '继承', '实现'}
                    if word in keywords:
                        data.extend([line_idx, word_start, i - word_start, 9, 0])  # keyword type = 9
                    elif word[0].isupper() if word[0].isascii() else False:
                        # 大写开头的英文词 → class/type
                        data.extend([line_idx, word_start, i - word_start, 2, 0])  # class type = 2
                    else:
                        # 默认作为 variable
                        data.extend([line_idx, word_start, i - word_start, 6, 0])  # variable type = 6
                    continue

                # 运算符
                operators = {'+', '-', '*', '/', '%', '=', '>', '<', '!', '&', '|', '^', '~'}
                if ch in operators:
                    op_start = i
                    while i < line_len and line_text[i] in operators:
                        i += 1
                    data.extend([line_idx, op_start, i - op_start, 13, 0])  # operator type = 13
                    continue

                # 其他字符（标点等）
                i += 1

        return {'data': data}

    def _handle_document_diagnostic(self, params: Dict) -> Dict:
        """处理 LSP 3.17+ 拉取式诊断请求 (textDocument/diagnostic)

        返回文档的完整诊断结果，包括语法错误、类型错误等。
        """
        uri = params.get('textDocument', {}).get('uri', '')
        doc = self.doc_manager.get_document(uri)
        if not doc:
            return {'kind': 'full', 'items': []}

        diagnostics = self.get_diagnostics(uri)
        return {
            'kind': 'full',
            'items': diagnostics
        }

    def _handle_did_open(self, params: Dict):
        """处理文档打开"""
        text_doc = params.get('textDocument', {})
        uri = text_doc.get('uri')
        text = text_doc.get('text', '')
        self.doc_manager.open_document(uri, text)
        # 发布初始诊断
        self._publish_diagnostics(uri)
    
    def _handle_did_change(self, params: Dict):
        """处理文档更改"""
        text_doc = params.get('textDocument', {})
        uri = text_doc.get('uri')
        changes = params.get('contentChanges', [])
        self.doc_manager.update_document(uri, changes)
        # 重新发布诊断
        self._publish_diagnostics(uri)
    
    def _publish_diagnostics(self, uri: str):
        """发布诊断信息"""
        diagnostics = self.get_diagnostics(uri)
        notification = lsp_notification('textDocument/publishDiagnostics', {
            'uri': uri,
            'diagnostics': diagnostics
        })
        # 存储待发送的通知
        if not hasattr(self, '_pending_notifications'):
            self._pending_notifications = []
        self._pending_notifications.append(notification)
    
    def get_pending_notifications(self) -> List[Dict]:
        """获取待发送的通知"""
        if not hasattr(self, '_pending_notifications'):
            return []
        notifications = self._pending_notifications
        self._pending_notifications = []
        return notifications
    
    def get_diagnostics(self, uri: str) -> List[Dict]:
        """获取文档诊断信息（语法错误 + 类型错误）"""
        doc = self.doc_manager.get_document(uri)
        if not doc:
            return []

        diagnostics = []

        # 语法分析错误
        try:
            parser = LightParser()
            ast = parser.parse(doc.text)
        except Exception as e:
            if hasattr(e, 'line') and hasattr(e, 'col'):
                line = max(0, e.line - 1)
                col = max(0, e.col - 1)
                # 尝试获取错误 token 的长度，用于精确高亮
                end_col = col + 1
                if hasattr(e, 'token_value') and e.token_value:
                    end_col = col + len(str(e.token_value))
                # 使用中文错误消息
                err_msg = str(e.message) if hasattr(e, 'message') else str(e)
                zh_msg = translate_error_message(err_msg)
                diagnostics.append({
                    'severity': 1,
                    'range': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': end_col}
                    },
                    'message': zh_msg,
                    'source': '光明'
                })
            else:
                err_msg = str(e)
                zh_msg = translate_error_message(err_msg)
                diagnostics.append({
                    'severity': 1,
                    'range': {
                        'start': {'line': 0, 'character': 0},
                        'end': {'line': 0, 'character': 0}
                    },
                    'message': f'错误: {zh_msg}',
                    'source': '光明'
                })
            return diagnostics

        # 类型检查诊断
        try:
            from type_inferencer import TypeInferencer
            from type_checker import create_checker_from_source

            inferencer = TypeInferencer()
            inferencer.infer(ast)

            for err in getattr(inferencer, 'errors', []):
                err_line = getattr(err, 'line', 0)
                err_col = getattr(err, 'col', 0)
                diagnostics.append({
                    'severity': 1,
                    'range': {
                        'start': {'line': max(0, err_line - 1), 'character': max(0, err_col - 1)},
                        'end': {'line': max(0, err_line - 1), 'character': max(0, err_col)}
                    },
                    'message': str(err),
                    'source': '光明类型'
                })

            checker = create_checker_from_source(doc.text)
            if checker.config.check_level.value > 0:
                check_results = checker.check(ast, inferencer)
                for r in check_results:
                    severity = 1 if r.is_error() else 2
                    r_line = max(0, getattr(r, 'line', 0) - 1)
                    r_col = max(0, getattr(r, 'col', 0))
                    diagnostics.append({
                        'severity': severity,
                        'range': {
                            'start': {'line': r_line, 'character': r_col},
                            'end': {'line': r_line, 'character': max(r_col, 1)}
                        },
                        'message': getattr(r, 'message', str(r)),
                        'source': '光明类型'
                    })
        except Exception:
            pass

        return diagnostics

    def _diagnose(self, uri: str, text: str) -> List[Dict]:
        """诊断文档，使用 Lexer + Parser 收集语法错误，返回诊断列表"""
        diagnostics = []
        try:
            lexer = Lexer()
            try:
                tokens = lexer.tokenize(text)
            except LexerError as e:
                diagnostics.append({
                    'range': {
                        'start': {'line': max(0, e.line - 1), 'character': max(0, e.col - 1)},
                        'end': {'line': max(0, e.line - 1), 'character': max(0, e.col)},
                    },
                    'severity': 1,
                    'source': 'light',
                    'message': f'词法错误: {e.message if hasattr(e, "message") else str(e)}',
                })
                return diagnostics
            except Exception as e:
                diagnostics.append({
                    'range': {
                        'start': {'line': 0, 'character': 0},
                        'end': {'line': 0, 'character': 1},
                    },
                    'severity': 1,
                    'source': 'light',
                    'message': f'词法分析错误: {str(e)}',
                })
                return diagnostics

            parser = LightParser()
            try:
                ast = parser.parse(text)
            except ParseError as e:
                line = max(0, e.line - 1)
                col = max(0, e.col - 1)
                end_col = col + 1
                if e.token_value:
                    end_col = col + len(str(e.token_value))
                diagnostics.append({
                    'range': {
                        'start': {'line': line, 'character': col},
                        'end': {'line': line, 'character': end_col},
                    },
                    'severity': 1,
                    'source': 'light',
                    'message': e.message if hasattr(e, 'message') else str(e),
                })
            except Exception as e:
                diagnostics.append({
                    'range': {
                        'start': {'line': 0, 'character': 0},
                        'end': {'line': 0, 'character': 1},
                    },
                    'severity': 1,
                    'source': 'light',
                    'message': f'解析错误: {str(e)}',
                })
        except Exception as e:
            diagnostics.append({
                'range': {
                    'start': {'line': 0, 'character': 0},
                    'end': {'line': 0, 'character': 1},
                },
                'severity': 1,
                'source': 'light',
                'message': f'诊断错误: {str(e)}',
            })
        return diagnostics

    def _publish_diagnostics_with_lexer_parser(self, uri: str, text: str):
        """使用 Lexer + Parser 诊断并发布通知"""
        diagnostics = self._diagnose(uri, text)
        notification = lsp_notification('textDocument/publishDiagnostics', {
            'uri': uri,
            'diagnostics': diagnostics
        })
        if not hasattr(self, '_pending_notifications'):
            self._pending_notifications = []
        self._pending_notifications.append(notification)


def create_language_server():
    """创建 LSP 服务器"""
    return LightLanguageServer()


# =============================================================================
# Stdio LSP 服务器入口
# =============================================================================

def main():
    """启动 LSP 服务器（独立入口）"""
    server = LightLanguageServer()
    buffer = ''
    content_length = 0
    
    while True:
        # Read headers
        while '\r\n\r\n' not in buffer:
            chunk = sys.stdin.buffer.read(4096)
            if not chunk:
                return
            buffer += chunk.decode('utf-8', errors='replace')
        
        # Parse Content-Length
        header, _, buffer = buffer.partition('\r\n\r\n')
        for line in header.split('\r\n'):
            if line.lower().startswith('content-length:'):
                content_length = int(line.split(':')[1].strip())
        
        # Read content
        while len(buffer) < content_length:
            chunk = sys.stdin.buffer.read(4096)
            if not chunk:
                return
            buffer += chunk.decode('utf-8', errors='replace')
        
        content = buffer[:content_length]
        buffer = buffer[content_length:]
        
        try:
            message = json.loads(content)
            method = message.get('method')
            params = message.get('params')
            msg_id = message.get('id')
            
            if method == 'exit':
                return
            
            if method == 'shutdown':
                if msg_id is not None:
                    response = json.dumps({'jsonrpc': '2.0', 'id': msg_id, 'result': None}, ensure_ascii=False)
                    response_bytes = response.encode('utf-8')
                    sys.stdout.write(f'Content-Length: {len(response_bytes)}\r\n\r\n')
                    sys.stdout.buffer.write(response_bytes)
                    sys.stdout.flush()
                continue
            
            if method:
                result = server.handle_request(method, params, msg_id)
                if result is not None:
                    response = json.dumps({'jsonrpc': '2.0', 'id': msg_id, 'result': result}, ensure_ascii=False)
                    response_bytes = response.encode('utf-8')
                    sys.stdout.write(f'Content-Length: {len(response_bytes)}\r\n\r\n')
                    sys.stdout.buffer.write(response_bytes)
                    sys.stdout.flush()
            
            # Send pending notifications
            for notification in server.get_pending_notifications():
                notification_json = json.dumps(notification, ensure_ascii=False)
                notification_bytes = notification_json.encode('utf-8')
                sys.stdout.write(f'Content-Length: {len(notification_bytes)}\r\n\r\n')
                sys.stdout.buffer.write(notification_bytes)
                sys.stdout.flush()
        except Exception as e:
            error_response = json.dumps({
                'jsonrpc': '2.0',
                'id': msg_id if 'msg_id' in locals() else None,
                'error': {'code': -32603, 'message': str(e)}
            }, ensure_ascii=False)
            error_bytes = error_response.encode('utf-8')
            sys.stdout.write(f'Content-Length: {len(error_bytes)}\r\n\r\n')
            sys.stdout.buffer.write(error_bytes)
            sys.stdout.flush()


# =============================================================================
# Stdio LSP 服务器入口
# =============================================================================

def run_stdio_server():
    """通过 stdio 运行 LSP 服务器（兼容别名）"""
    main()


if __name__ == '__main__':
    main()
