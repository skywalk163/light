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

from lexer import Lexer
from light_parser_v3 import LightParser
from keywords import ALL_KEYWORDS, VERB_ARITY


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
DUAN_ERROR_MESSAGES_ZH = {
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
    for eng, zh in DUAN_ERROR_MESSAGES_ZH.items():
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
            lexer = Lexer()
            tokens = lexer.tokenize(doc.text)

            parser = LightParser()
            ast = parser.parse_tokens(tokens)

            self.symbols[doc.uri] = self._extract_symbols(ast)
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

    def _extract_type_info(self, ast, inferencer) -> Dict:
        """提取变量/函数的类型信息"""
        info = {}

        def walk(node):
            if node is None:
                return
            node_type = type(node).__name__
            name = getattr(node, 'name', None)
            if name and node_type in ('VarDecl', 'VariableDeclaration', 'VarDef',
                                       'FuncDef', 'FunctionDef', 'SegmentDefinition',
                                       'Paragraph'):
                # 检查类型标注
                ta = getattr(node, 'type_annotation', None)
                if ta:
                    info[str(name)] = str(ta)
                else:
                    # 尝试从推断器获取
                    value = getattr(node, 'value', None)
                    if value and inferencer:
                        inferred = inferencer.type_cache.get(id(value))
                        if inferred:
                            info[str(name)] = str(inferred)

            for child_name in dir(node):
                if child_name.startswith('_'):
                    continue
                try:
                    child = getattr(node, child_name)
                    if isinstance(child, list):
                        for item in child:
                            if hasattr(item, '__class__') and hasattr(item, '__dict__'):
                                walk(item)
                    elif hasattr(child, '__class__') and hasattr(child, '__dict__') and hasattr(child, 'line'):
                        walk(child)
                except Exception:
                    pass

        walk(ast)
        return info
    
    def _extract_symbols(self, ast) -> List[Dict]:
        """提取文档符号"""
        symbols = []
        
        def walk(node):
            if node is None:
                return
                
            node_type = type(node).__name__
            
            line = getattr(node, 'line', 1) - 1
            col = getattr(node, 'col', 0)
            
            if node_type == 'FuncDef':
                name = getattr(node, 'name', '?')
                params = getattr(node, 'params', [])
                param_strs = []
                for p in params:
                    pname = getattr(p, 'name', '?') if hasattr(p, 'name') else str(p)
                    param_strs.append(pname)
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
            elif node_type == 'ClassDef':
                name = getattr(node, 'name', '?')
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
            elif node_type == 'VarDef':
                name = getattr(node, 'name', '?')
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
            
            for child_name in dir(node):
                if child_name.startswith('_'):
                    continue
                try:
                    child = getattr(node, child_name)
                    if isinstance(child, list):
                        for item in child:
                            if hasattr(item, '__class__') and hasattr(item, '__dict__'):
                                walk(item)
                    elif hasattr(child, '__class__') and hasattr(child, '__dict__') and hasattr(child, 'line'):
                        walk(child)
                except Exception:
                    pass

        walk(ast)
        return symbols
    
    def _extract_definitions(self, ast, doc) -> Dict:
        """提取定义"""
        definitions = {}
        
        def walk(node):
            if node is None:
                return
                
            node_type = type(node).__name__
            line = getattr(node, 'line', 1) - 1
            col = getattr(node, 'col', 0)
            
            if node_type in ('VarDef', 'FuncDef', 'ClassDef', 'MethodDef'):
                name = getattr(node, 'name', None)
                if name:
                    definitions[name] = {
                        'uri': doc.uri,
                        'range': {
                            'start': {'line': line, 'character': col},
                            'end': {'line': line, 'character': col + len(str(name))}
                        }
                    }
                    
                    # 额外保存节点信息用于悬停
                    if node_type == 'FuncDef':
                        params = getattr(node, 'params', [])
                        param_strs = []
                        for p in params:
                            pname = getattr(p, 'name', '?') if hasattr(p, 'name') else str(p)
                            param_strs.append(pname)
                        definitions[name + '__info'] = {
                            'type': '函数',
                            'params': param_strs,
                            'line': line,
                            'col': col
                        }
            
            for child_name in dir(node):
                if child_name.startswith('_'):
                    continue
                try:
                    child = getattr(node, child_name)
                    if isinstance(child, list):
                        for item in child:
                            if hasattr(item, '__class__') and hasattr(item, '__dict__'):
                                walk(item)
                    elif hasattr(child, '__class__') and hasattr(child, '__dict__') and hasattr(child, 'line'):
                        walk(child)
                except Exception:
                    pass

        walk(ast)
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
                    '若', '否', '试', '捕', '抛', '终', '配', '承', '自', '跳', '过', '并', '且', '或', '非', '空', '真', '假']
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
            'textDocument/hover': self._handle_hover,
            'textDocument/definition': self._handle_definition,
            'textDocument/references': self._handle_references,
            'textDocument/documentSymbol': self._handle_document_symbol,
            'textDocument/formatting': self._handle_formatting,
            'textDocument/rangeFormatting': self._handle_range_formatting,
            'textDocument/rename': self._handle_rename,
            'textDocument/signatureHelp': self._handle_signature_help,
            'textDocument/semanticTokens/full': self._handle_semantic_tokens,
            'textDocument/codeAction': self._handle_code_action,
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
        """处理代码补全"""
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
        
        completions = []
        
        # 关键字补全
        for kw in sorted(ALL_KEYWORDS):
            if not prefix or kw.startswith(prefix):
                # 关键字文档
                kw_docs = {
                    '定义': '定义变量：定义 变量名 等于 值。',
                    '设': '设变量为值：设 变量名 为 值。',
                    '如果': '条件语句：如果 条件 那么：...结束。',
                    '若': '条件语句（L0简写）：若 条件 则：...结束。',
                    '那么': '条件语句 then 分支',
                    '否则': '条件语句 else 分支',
                    '否': '条件语句 else 分支（L0简写）：否则/否 条件：...结束。',
                    '否则若': '条件语句 elif 分支',
                    '遍历': '遍历循环：遍历 变量 于 列表：...结束。',
                    '遍': '遍历循环（L0简写）：遍 变量 之 列表：...结束。',
                    '当': '条件循环：当 条件：...结束。',
                    '返回': '返回语句：返回 表达式。',
                    '返': '返回语句（L0简写）：返 表达式。',
                    '跳出': '跳出循环：跳出。',
                    '跳': '跳出循环（L0简写）：跳。',
                    '跳过': '跳过本次迭代：跳过。',
                    '过': '跳过本次迭代（L0简写）：过。',
                    '段落': '段落（函数）定义：段落 段名 接收 参数：...结束。',
                    '段': '段落（函数）定义（L0简写）：段 段名(参数)：...结束。',
                    '类': '类定义：类 类名：...结束。',
                    '承': '继承（L0简写）：类 子类 承 父类：...结束。',
                    '接口': '接口定义：接口 接口名：...结束。',
                    '接': '接口定义（L0简写）：接 接口名：...结束。',
                    '尝试': '异常处理：尝试：...捕获 异常：...结束。',
                    '试': '异常处理（L0简写）：试：...捕 异常：...结束。',
                    '捕获': '异常捕获：捕获 异常类型：...结束。',
                    '捕': '异常捕获（L0简写）：捕 异常类型：...结束。',
                    '抛出': '抛出异常：抛出 异常对象。',
                    '抛': '抛出异常（L0简写）：抛 异常对象。',
                    '最终': '最终执行块：最终：...结束。',
                    '终': '最终执行块（L0简写）：终：...结束。',
                    '导入': '导入模块：导入 模块名。',
                    '导': '导入模块（L0简写）：导 模块名。',
                    '导出': '导出模块：导出 模块名。',
                    '出': '导出模块（L0简写）：出 模块名。',
                    '匹配': '模式匹配：匹配 表达式：情况 模式：...结束。',
                    '配': '模式匹配（L0简写）：配 表达式：情况 模式：...结束。',
                    '异步': '异步函数定义：异步 段落 段名...',
                    '等待': '等待异步操作：等待 异步调用。',
                    '自': '自引用（L0）：自.属性 或 自.方法()，等价于 self。',
                    '之': '属性提取符（L0）：对象之属性，等价于 对象.属性。',
                    '并': '管道连接符（L0）：数据 并 处理1 并 处理2。',
                    '且': '逻辑与（L0）：条件1 且 条件2。',
                    '或': '逻辑或（L0）：条件1 或 条件2。',
                    '非': '逻辑非（L0）：非 条件。',
                    '真': '布尔值：真（True）。',
                    '假': '布尔值：假（False）。',
                    '空': '空值：空（None/null）。',
                    '是': '判断/相等（L0）：甲 是 乙 等价于 甲 == 乙。',
                    '从': '从...导入（L0）：从 模块 导入 名称。',
                }
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
        
        # 动词元数补全
        for verb, arity in sorted(VERB_ARITY.items()):
            if not prefix or verb.startswith(prefix):
                completions.append({
                    'label': verb,
                    'kind': 15,  # Snippet
                    'detail': f'动词 (元数: {arity})',
                    'sortText': f'2_{verb}',
                    'filterText': verb
                })
        
        # 本地变量/函数补全
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
                        'sortText': f'3_{name}',
                        'filterText': name
                    })
        
        return {
            'isIncomplete': False,
            'items': completions
        }
    
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

        # 检查是否是关键字或动词，显示详细中文文档
        if word in KW_HOVER_DOCS:
            contents.append(KW_HOVER_DOCS[word])
        elif word in ALL_KEYWORDS:
            contents.append(f"**关键字**: `{word}`\n\n光明编程语言关键字，用于控制程序结构和逻辑。")
        elif word in VERB_ARITY:
            contents.append(f"**动词**: `{word}` (元数: {VERB_ARITY[word]})\n\n光明内置动词，用于执行特定操作。")

        # 检查是否是本地定义
        if doc.uri in self.doc_manager.definitions:
            info = self.doc_manager.definitions[doc.uri].get(word + '__info')
            if info:
                if info['type'] == '函数':
                    params_str = ', '.join(info['params'])
                    contents.append(f"**函数**: `{word}({params_str})`")

            if word in self.doc_manager.definitions[doc.uri]:
                def_info = self.doc_manager.definitions[doc.uri][word]
                def_line = def_info['range']['start']['line'] + 1
                contents.append(f"定义于第 {def_line} 行")

        # 类型信息
        if doc.uri in self.doc_manager.type_info:
            t = self.doc_manager.type_info[doc.uri].get(word)
            if t:
                contents.append(f"**类型**: `{t}`")
        
        if not contents:
            return None
        
        return {
            'contents': {
                'kind': 'markdown',
                'value': '\n\n'.join(contents)
            },
            'range': {
                'start': {'line': line, 'character': start},
                'end': {'line': line, 'character': end}
            }
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
        
        # 查找定义
        if doc.uri in self.doc_manager.definitions:
            if word in self.doc_manager.definitions[doc.uri]:
                return self.doc_manager.definitions[doc.uri][word]
        
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
        """格式化文档内容"""
        indent = ' ' * tab_size if insert_spaces else '\t'
        lines = text.split('\n')
        total_lines = len(lines)

        if start_line is None:
            start_line = 0
        if end_line is None:
            end_line = total_lines - 1

        # 计算缩进级别
        formatted_lines = list(lines)
        indent_level = 0

        for i in range(start_line, end_line + 1):
            line = lines[i].strip()

            if not line:
                continue

            # 减少缩进：结束、否则/否、否则若/否若、捕获/捕、最终/终
            decrease_keywords = ['结束', '否则', '否', '否则若', '否若', '捕获', '捕', '最终', '终']
            for kw in decrease_keywords:
                if line.startswith(kw):
                    indent_level = max(0, indent_level - 1)
                    break

            # 应用缩进
            formatted_lines[i] = indent * indent_level + line

            # 增加缩进：如果/若、遍历/遍、当、段落/段、类、接口/接、尝试/试、匹配/配、否则/否、否则若/否若、捕获/捕
            if any(line.endswith(kw) for kw in ['：', ':']):
                if any(line.startswith(kw) for kw in
                       ['如果', '若', '遍历', '遍', '当', '段落', '段', '类', '接口', '接',
                        '尝试', '试', '匹配', '配', '否则', '否', '否则若', '否若', '捕获', '捕']):
                    indent_level += 1
                elif any(kw in line for kw in ['接收', '构造']):
                    indent_level += 1

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
        """处理代码操作请求（快速修复）"""
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


def create_language_server():
    """创建 LSP 服务器"""
    return LightLanguageServer()


# =============================================================================
# Stdio LSP 服务器入口
# =============================================================================

def run_stdio_server():
    """通过 stdio 运行 LSP 服务器"""
    import sys
    
    server = LightLanguageServer()
    request_id = None
    
    def send_message(message: Dict):
        """发送 LSP 消息"""
        content = json.dumps(message, ensure_ascii=False)
        content_bytes = content.encode('utf-8')
        sys.stdout.write(f'Content-Length: {len(content_bytes)}\r\n\r\n')
        sys.stdout.buffer.write(content_bytes)
        sys.stdout.flush()
    
    def read_message() -> Optional[Dict]:
        """读取 LSP 消息"""
        # 读取 headers
        headers = {}
        while True:
            line = sys.stdin.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        # 读取 content
        content_length = int(headers.get('content-length', '0'))
        if content_length <= 0:
            return None
        
        content = sys.stdin.buffer.read(content_length).decode('utf-8')
        return json.loads(content)
    
    while True:
        message = read_message()
        if message is None:
            break
        
        method = message.get('method')
        params = message.get('params', {})
        msg_id = message.get('id')
        
        if method == 'exit':
            break
        
        if method == 'shutdown':
            if msg_id is not None:
                send_message(lsp_response(msg_id, None))
            continue
        
        result = server.handle_request(method, params, msg_id)
        
        if result is not None and msg_id is not None:
            send_message(result)
        
        # 发送待处理的通知
        for notification in server.get_pending_notifications():
            send_message(notification)


if __name__ == '__main__':
    run_stdio_server()
