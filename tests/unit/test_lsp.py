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
        # 请求补全
        result = server._handle_completion({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 1}
        })
        assert 'items' in result
        assert isinstance(result['items'], list)
    
    def test_hover(self):
        """测试悬停"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '设 x 为 10'
            }
        })
        result = server._handle_hover({
            'textDocument': {'uri': 'file:///test.light'},
            'position': {'line': 0, 'character': 1}
        })
        # 悬停可能返回 None 或有内容
        assert result is None or 'contents' in result
    
    def test_document_symbol(self):
        """测试文档符号"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '段落 测试：\n  返回 1'
            }
        })
        symbols = server._handle_document_symbol({
            'textDocument': {'uri': 'file:///test.light'}
        })
        assert isinstance(symbols, list)
    
    def test_diagnostics(self):
        """测试诊断"""
        server = LightLanguageServer()
        server._handle_did_open({
            'textDocument': {
                'uri': 'file:///test.light',
                'text': '设 x 为 10'
            }
        })
        # 检查是否有待发送的通知
        notifications = server.get_pending_notifications()
        # 应该有 publishDiagnostics 通知
        has_diag = any(n['method'] == 'textDocument/publishDiagnostics' for n in notifications)
        assert has_diag


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
