# -*- coding: utf-8 -*-
"""
错误处理模块测试
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from errors import format_exception, format_source_context, LightError, LexerError, SemanticError


class TestErrorFormatting:
    """测试错误格式化"""
    
    def test_light_error(self):
        """测试 LightError"""
        err = LightError("测试错误", line=5, col=10)
        assert "测试错误" in str(err)
        assert err.line == 5
        assert err.col == 10
    
    def test_lexer_error(self):
        """测试 LexerError"""
        err = LexerError("词法错误", line=1, col=1)
        assert "词法分析错误" in str(err)
    
    def test_semantic_error(self):
        """测试 SemanticError"""
        err = SemanticError("语义错误", line=10, col=5)
        assert "语义错误" in str(err)
    
    def test_light_error_with_hint(self):
        """测试带提示的错误"""
        err = LightError("错误", hint="试试这个")
        assert "提示" in str(err)
        assert "试试这个" in str(err)
    
    def test_format_source_context(self):
        """测试源代码上下文格式化"""
        source = "第一行\n第二行\n第三行\n第四行\n第五行"
        result = format_source_context(source, 3, 2)
        assert "第二行" in result
        assert "第三行" in result
        assert "第四行" in result
    
    def test_format_exception_name_error(self):
        """测试格式化 NameError"""
        try:
            x = undefined_variable  # noqa
        except Exception as e:
            result = format_exception(type(e), e, e.__traceback__)
            assert "名称错误" in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
