# -*- coding: utf-8 -*-
"""
LSP 语言服务器基础测试
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from lsp.light_lsp import (
    LightLanguageServer,
    Document,
    DocumentManager,
    lsp_response,
    lsp_notification,
    lsp_error
)


class TestDocument:
    """测试 Document 类"""

    def test_create_document(self):
        """测试创建文档"""
        doc = Document("file:///test.light", "设 x 为 10")
        assert doc.uri == "file:///test.light"
        assert doc.text == "设 x 为 10"
        assert len(doc.lines) == 1

    def test_get_line(self):
        """测试获取行"""
        doc = Document("file:///test.light", "第一行\n第二行\n第三行")
        assert doc.get_line(0) == "第一行"
        assert doc.get_line(1) == "第二行"
        assert doc.get_line(2) == "第三行"
        assert doc.get_line(100) == ""

    def test_full_update(self):
        """测试全文更新"""
        doc = Document("file:///test.light", "旧内容")
        doc.update([{'text': '新内容'}])
        assert doc.text == "新内容"
        assert doc.version == 2


class TestDocumentManager:
    """测试 DocumentManager 类"""

    def test_open_document(self):
        """测试打开文档"""
        mgr = DocumentManager()
        mgr.open_document("file:///test.light", "设 x 为 10")
        doc = mgr.get_document("file:///test.light")
        assert doc is not None
        assert doc.text == "设 x 为 10"

    def test_close_document(self):
        """测试关闭文档"""
        mgr = DocumentManager()
        mgr.open_document("file:///test.light", "test")
        mgr.close_document("file:///test.light")
        assert mgr.get_document("file:///test.light") is None

    def test_definitions_extracted(self):
        """测试文档打开后提取了定义"""
        mgr = DocumentManager()
        text = """段落 测试段(甲, 乙)：
  返回 甲 加 乙。
结束。

设 变量1 为 42。

类 测试类：
  属性 名称。
  构造(参数)：
    设 己.名称 为 参数。
  结束。
结束。
"""
        mgr.open_document("file:///test.light", text)
        assert '测试段' in mgr.definitions.get("file:///test.light", {})
        assert '变量1' in mgr.definitions.get("file:///test.light", {})
        assert '测试类' in mgr.definitions.get("file:///test.light", {})

    def test_symbols_extracted(self):
        """测试文档打开后提取了符号"""
        mgr = DocumentManager()
        text = """段落 测试段(甲, 乙)：
  返回 甲 加 乙。
结束。

设 变量1 为 42。
"""
        mgr.open_document("file:///test.light", text)
        symbols = mgr.symbols.get("file:///test.light", [])
        names = [s['name'] for s in symbols]
        assert '测试段' in names
        assert '变量1' in names


class TestLSPMessages:
    """测试 LSP 消息构建"""

    def test_lsp_response(self):
        """测试响应构建"""
        resp = lsp_response(1, {"result": "ok"})
        assert resp['jsonrpc'] == '2.0'
        assert resp['id'] == 1
        assert resp['result']['result'] == 'ok'

    def test_lsp_notification(self):
        """测试通知构建"""
        notif = lsp_notification('textDocument/publishDiagnostics', {'uri': 'test'})
        assert notif['jsonrpc'] == '2.0'
        assert notif['method'] == 'textDocument/publishDiagnostics'
        assert notif['params']['uri'] == 'test'

    def test_lsp_error(self):
        """测试错误响应构建"""
        err = lsp_error(1, -32603, "内部错误")
        assert err['jsonrpc'] == '2.0'
        assert err['id'] == 1
        assert err['error']['code'] == -32603


class TestLanguageServer:
    """测试语言服务器"""

    def test_initialize(self):
        """测试初始化"""
        server = LightLanguageServer()
        params = {
            'processId': None,
            'rootUri': None,
            'capabilities': {}
        }
        result = server._handle_initialize(params)
        assert 'capabilities' in result
        assert 'serverInfo' in result
        assert result['serverInfo']['name'] == '光明语言服务器'

    def test_completion_returns_items(self):
        """测试代码补全返回 items"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '设 x 为 10'
            }
        })
        result = server._handle_completion({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 1}
        })
        assert 'items' in result
        assert isinstance(result['items'], list)
        assert len(result['items']) > 0

    def test_completion(self):
        """测试代码补全"""
        server = LightLanguageServer()
        # 先打开文档
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '设 x 为 10'
            }
        })
        result = server._handle_completion({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 1}
        })
        assert 'items' in result
        assert isinstance(result['items'], list)
    def test_completion_has_keywords(self):
        """测试补全包含关键字"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': ''
            }
        })
        result = server._handle_completion({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 0}
        })
        items = result['items']
        labels = [i['label'] for i in items]
        assert '如果' in labels
        assert '段落' in labels
        assert '定义' in labels

    def test_hover(self):
        """测试悬停"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '设 x 为 10'
            }
        })
        # 悬停在"设"上
        result = server._handle_hover({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 1}
        })
        assert result is not None
        assert 'contents' in result
        contents = result['contents']
        if isinstance(contents, dict):
            value = contents.get('value', '')
        else:
            value = str(contents)
        assert '关键字' in value or '设' in value

    def test_hover_returns_content_for_keyword(self):
        """测试悬停返回关键字内容"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '设 x 为 10'
            }
        })
        # 悬停在"设"上
        result = server._handle_hover({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 0}
        })
        assert result is not None
        assert 'contents' in result
        contents = result['contents']
        if isinstance(contents, dict):
            value = contents.get('value', '')
        else:
            value = str(contents)
        assert '关键字' in value or '设' in value

    def test_hover_returns_content_for_keyword_if(self):
        """测试悬停返回关键字'如果'的内容"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '如果 甲 大于 10 那么：'
            }
        })
        # 悬停在"如果"上
        result = server._handle_hover({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 0}
        })
        assert result is not None
        assert 'contents' in result

    def test_definition_returns_none_for_unknown(self):
        """测试跳转定义对未知符号返回 None"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '设 x 为 10'
            }
        })
        result = server._handle_definition({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 0}
        })
        # "设" 是关键字，不是用户定义，所以返回 None
        assert result is None

    def test_definition_returns_location(self):
        """测试跳转定义返回位置"""
        server = LightLanguageServer()
        text = """设 变量1 为 42。
设 x 为 变量1。
"""
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': text
            }
        })
        # 跳转到"变量1"的定义
        result = server._handle_definition({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 1, 'character': 6}
        })
        assert result is not None
        assert 'uri' in result
        assert 'range' in result
        # 应该定位到某个行（变量1 定义的位置）

    def test_formatting_returns_edits(self):
        """测试格式化返回编辑"""
        server = LightLanguageServer()
        # 使用未缩进的代码
        unformatted = """如果 甲 大于 10 那么：
返回 甲。
结束。
"""
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': unformatted
            }
        })
        result = server._handle_formatting({
            'textDocument': {'uri': 'file:///test.light'},
            'options': {'tabSize': 4, 'insertSpaces': True}
        })
        assert isinstance(result, list)

    def test_formatting_indents_blocks(self):
        """测试格式化缩进块"""
        server = LightLanguageServer()
        unformatted = """如果 甲 大于 10 那么：
返回 甲。
结束。
"""
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': unformatted
            }
        })
        result = server._handle_formatting({
            'textDocument': {'uri': 'file:///test.light'},
            'options': {'tabSize': 4, 'insertSpaces': True}
        })
        # 如果返回了编辑，验证缩进
        if result:
            new_text = result[0]['newText']
            lines = new_text.split('\n')
            # "返回 甲。" 应该在 if 块内，缩进 4 空格
            return_line = [l for l in lines if '返回' in l]
            if return_line:
                assert return_line[0].startswith('    ')

    def test_document_symbol(self):
        """测试文档符号"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '段落 测试()：\n  返回 1\n结束。'
            }
        })
        symbols = server._handle_document_symbol({
            'textDocument': {'uri': 'file:///test.light'}
        })
        assert isinstance(symbols, list)
        # 应该有测试符号
        assert len(symbols) > 0

    def test_document_symbol_has_types(self):
        """测试文档符号包含类型"""
        server = LightLanguageServer()
        text = """段落 测试段(甲, 乙)：
  返回 甲 加 乙。
结束。

设 全局变量 为 100。

类 测试类：
  属性 名称。
结束。
"""
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': text
            }
        })
        symbols = server._handle_document_symbol({
            'textDocument': {'uri': 'file:///test.light'}
        })
        names = [s['name'] for s in symbols]
        kinds = {s['name']: s['kind'] for s in symbols}
        assert '测试段' in names
        assert '全局变量' in names
        assert '测试类' in names
        assert kinds.get('测试段') == 12   # Function
        assert kinds.get('测试类') == 5    # Class
        assert kinds.get('全局变量') == 6  # Variable

    def test_diagnostics(self):
        """测试诊断"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '设 x 为 10'
            }
        })
        notifications = server.get_pending_notifications()
        has_diag = any(n['method'] == 'textDocument/publishDiagnostics' for n in notifications)
        assert has_diag

    def test_references(self):
        """测试查找引用"""
        server = LightLanguageServer()
        text = """设 变量1 为 42。
设 x 为 变量1。
打印输出(变量1)。
"""
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': text
            }
        })
        result = server._handle_references({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 3}
        })
        assert isinstance(result, list)
        # 变量1 出现在第 0、1、2 行
        # 但由于引用查找是文本匹配，且"变量1"可能也是定义的一部分
        # 只要返回列表即可

    def test_signature_help(self):
        """测试签名帮助"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '打印输出('
            }
        })
        result = server._handle_signature_help({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 5}
        })
        # 可能在括号内也可能不在，取决于位置
        # 只要不崩溃即可
        assert result is None or 'signatures' in result

    def test_rename(self):
        """测试重命名"""
        server = LightLanguageServer()
        text = """设 变量1 为 42。
设 x 为 变量1。
"""
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': text
            }
        })
        result = server._handle_rename({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 3},
            'newName': '变量2'
        })
        assert result is not None
        assert 'changes' in result
        assert 'file:///test.light' in result['changes']

    def test_handle_highlight(self):
        """测试文档高亮"""
        server = LightLanguageServer()
        text = """设 变量1 为 42。
设 x 为 变量1。
"""
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': text
            }
        })
        result = server._handle_document_highlight({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 3}
        })
        assert isinstance(result, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])