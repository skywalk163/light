# -*- coding: utf-8 -*-
"""
编译器缓存功能单元测试

测试增量编译缓存的正确性：
- 缓存命中时返回相同结果
- use_cache=False 时每次重新编译
"""

import sys
import os
import tempfile
import time
import pytest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


class TestCompilerCache:
    """编译器缓存测试类"""

    @pytest.fixture
    def temp_source_file(self, tmp_path):
        """创建临时源文件的 fixture"""
        # 清空缓存，确保测试独立性
        from compiler import _compile_cache
        _compile_cache.clear()

        source_file = tmp_path / "test_cache.light"
        source_file.write_text('设 x 为 123。', encoding='utf-8')
        return str(source_file)

    def test_cache_hit_returns_same_result(self, temp_source_file):
        """测试缓存命中：两次编译同一文件结果相同"""
        from compiler import compile_file, _compile_cache, _normalize_cache_path

        # 第一次编译
        result1 = compile_file(temp_source_file)
        assert result1 is not None
        assert 'ast' in result1

        # 验证缓存已存储（使用规范化路径作为 key）
        cache_key = _normalize_cache_path(temp_source_file)
        assert cache_key in _compile_cache

        # 第二次编译（应该命中缓存）
        result2 = compile_file(temp_source_file)

        # 验证返回的是同一个对象（缓存命中）
        assert result1 is result2

    def test_no_cache_option(self, temp_source_file):
        """测试 use_cache=False 时每次重新编译"""
        from compiler import compile_file, _compile_cache

        # 第一次编译（不使用缓存）
        result1 = compile_file(temp_source_file, use_cache=False)
        assert result1 is not None

        # 验证没有存入缓存
        abs_path = os.path.abspath(temp_source_file)
        assert abs_path not in _compile_cache

        # 第二次编译（不使用缓存）
        result2 = compile_file(temp_source_file, use_cache=False)

        # 验证返回的是不同对象（每次重新编译）
        assert result1 is not result2
        # 但内容应该相同
        assert result1['source'] == result2['source']

    def test_cache_invalidation_on_file_change(self, temp_source_file):
        """测试文件修改后缓存失效：重新编译"""
        from compiler import compile_file, _compile_cache

        # 第一次编译
        result1 = compile_file(temp_source_file)
        assert result1 is not None

        # 修改文件内容
        time.sleep(0.1)  # 确保 mtime 有变化
        with open(temp_source_file, 'w', encoding='utf-8') as f:
            f.write('设 y 为 456。')

        # 第二次编译（应该重新编译）
        result2 = compile_file(temp_source_file)

        # 验证返回的是不同对象（文件已修改）
        assert result1 is not result2
        assert result2['source'] == '设 y 为 456。'

    def test_cache_uses_absolute_path(self, tmp_path):
        """测试缓存使用绝对路径作为 key"""
        from compiler import compile_file, _compile_cache, _normalize_cache_path

        # 清空缓存
        _compile_cache.clear()

        source_file = tmp_path / "test_abs.light"
        source_file.write_text('打印 "你好"。', encoding='utf-8')

        abs_path = os.path.abspath(str(source_file))

        # 检查是否在同一盘符（Windows 跨盘符无法使用相对路径）
        try:
            rel_path = os.path.relpath(abs_path)
            # 使用相对路径编译
            result1 = compile_file(rel_path)
            # 使用绝对路径编译
            result2 = compile_file(abs_path)
            # 应该命中缓存（使用规范化路径作为 key）
            assert result1 is result2
        except ValueError:
            # 跨盘符时跳过相对路径测试，直接验证是否缓存
            cache_key = _normalize_cache_path(abs_path)
            result1 = compile_file(abs_path)
            assert cache_key in _compile_cache
            result2 = compile_file(abs_path)
            assert result1 is result2
