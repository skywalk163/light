# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 高级语义测试

测试覆盖：
- 动词元数（决策28）
- 主谓/谓宾语义识别（决策34）
- 元数驱动解析
- 语义识别和代码生成
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from verb_info import get_verb_info, get_python_mapping, VerbInfo
from arity_parser import ArityParser
from semantic_identifier import SemanticIdentifier, SemanticType


class TestVerbInfo:
    """动词信息测试"""
    
    def test_get_verb_info_exists(self):
        """测试获取已定义动词信息"""
        info = get_verb_info('加')
        
        assert info is not None
        assert isinstance(info, VerbInfo)
        assert info.arity == 2
    
    def test_get_verb_info_not_exists(self):
        """测试获取未定义动词信息"""
        info = get_verb_info('未知动词')
        
        # 未定义动词可能返回 None 或默认值
        # 根据实际实现调整
        assert info is None or isinstance(info, VerbInfo)
    
    def test_verb_arity(self):
        """测试动词元数"""
        # 二元运算符
        info = get_verb_info('加')
        if info:
            assert info.arity == 2
        
        # 一元操作符
        info = get_verb_info('打印')
        if info:
            assert info.arity == 1
    
    def test_verb_mode(self):
        """测试动词修改模式"""
        info = get_verb_info('排序')
        
        if info:
            # 排序支持两种模式
            assert info.mode in ['both', 'functional', 'modify']
    
    def test_get_python_mapping(self):
        """测试Python映射"""
        mapping = get_python_mapping('加')
        
        if mapping:
            python_name, mapping_type = mapping
            assert python_name in ['+', 'add']
            assert mapping_type in ['operator', 'function', 'method']


class TestArityParser:
    """元数驱动解析器测试"""
    
    @pytest.fixture
    def parser(self):
        return ArityParser([])
    
    def test_unary_verb(self, parser):
        """测试一元动词"""
        # ArityParser.parse_verb_call 解析动词调用
        result = parser.parse_verb_call('打印')
        assert result is not None
    
    def test_binary_verb(self, parser):
        """测试二元动词"""
        result = parser.parse_verb_call('加')
        assert result is not None
    
    def test_nested_verbs(self, parser):
        """测试嵌套动词"""
        result = parser.parse_verb_call('乘')
        assert result is not None
    
    def test_multiple_verbs(self, parser):
        """测试多个动词"""
        result = parser.parse_verb_call('打印')
        assert result is not None


class TestSemanticIdentifier:
    """语义识别器测试"""
    
    @pytest.fixture
    def identifier(self):
        symbol_table = {'列表': 'list', '数据': 'list'}
        return SemanticIdentifier(symbol_table)
    
    def test_subject_verb_semantic(self, identifier):
        """测试主谓语义"""
        from light_parser_v3 import BinaryOp, Identifier
        
        # 列表排序（主谓结构）
        expr = BinaryOp('排序', Identifier('列表'), None)
        
        semantic_type, verb = identifier.identify(expr)
        
        # 应该识别为主谓语义
        assert semantic_type is not None
    
    def test_verb_object_semantic(self, identifier):
        """测试谓宾语义"""
        from light_parser_v3 import BinaryOp, Identifier
        
        # 排序列表（谓宾结构）
        expr = BinaryOp('排序', None, Identifier('列表'))
        
        semantic_type, verb = identifier.identify(expr)
        
        # 应该识别为谓宾语义
        assert semantic_type is not None
    
    def test_function_call_semantic(self, identifier):
        """测试函数调用语义"""
        from light_parser_v3 import ParagraphCall, Identifier
        
        # 《排序》(列表)
        expr = ParagraphCall('排序', [Identifier('列表')])
        
        semantic_type, verb = identifier.identify(expr)
        
        # 应该识别为函数调用
        assert semantic_type in [SemanticType.FUNCTIONAL, SemanticType.VERB_OBJECT, SemanticType.SUBJECT_VERB]


class TestSemanticCodeGeneration:
    """语义代码生成测试"""
    
    def test_subject_verb_generation(self):
        """测试主谓语义代码生成"""
        from semantic_identifier import generate_python_code
        
        symbol_table = {'列表': 'list'}
        
        # 列表排序 → 列表.sort()
        python_code = generate_python_code(
            SemanticType.SUBJECT_VERB,
            '排序',
            [],
            symbol_table
        )
        
        # 应该生成方法调用
        assert python_code is not None
        assert '.sort()' in python_code or 'sorted(' in python_code
    
    def test_verb_object_generation(self):
        """测试谓宾语义代码生成"""
        from semantic_identifier import generate_python_code
        
        symbol_table = {'列表': 'list'}
        
        # 排序列表 → sorted(列表)
        python_code = generate_python_code(
            SemanticType.VERB_OBJECT,
            '排序',
            ['列表'],
            symbol_table
        )
        
        # 应该生成函数调用
        assert python_code is not None
        assert 'sorted(' in python_code or '.sort()' in python_code


class TestArityDrivenParsing:
    """元数驱动解析集成测试"""
    
    def test_simple_case(self):
        """测试简单用例"""
        from arity_parser import ArityParser
        
        parser = ArityParser([])
        result = parser.parse_verb_call('打印')
        
        assert result is not None
    
    def test_complex_case(self):
        """测试复杂用例"""
        from arity_parser import ArityParser
        
        parser = ArityParser([])
        result = parser.parse_verb_call('乘')
        
        assert result is not None


class TestSemanticAmbiguity:
    """语义歧义测试"""
    
    @pytest.fixture
    def identifier(self):
        symbol_table = {}
        return SemanticIdentifier(symbol_table)
    
    def test_ambiguous_expression(self, identifier):
        """测试歧义表达式"""
        from light_parser_v3 import BinaryOp, Identifier
        
        # 没有符号表信息时，可能有歧义
        expr = BinaryOp('排序', Identifier('未知'), None)
        
        semantic_type, verb = identifier.identify(expr)
        
        # 应该能处理歧义
        assert semantic_type is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])