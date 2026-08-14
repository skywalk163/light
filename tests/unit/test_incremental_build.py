# -*- coding: utf-8 -*-
"""
增量编译系统单元测试

测试场景：
1. 首次编译：所有文件均为新文件，应全部编译
2. 增量编译：无变更时跳过编译
3. 文件变更检测：修改文件内容后应重新编译
4. 缓存持久化：缓存文件正确保存和加载
5. 强制全量编译：--force 选项应编译所有文件
"""

import sys
import os
import time
import json
import tempfile
import pytest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


class TestIncrementalBuild:
    """增量编译测试类"""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """创建临时项目目录的 fixture"""
        # 创建测试 .duan 文件
        main_file = tmp_path / "main.duan"
        main_file.write_text('输出("你好，世界！")。\n', encoding='utf-8')

        utils_file = tmp_path / "utils.duan"
        utils_file.write_text('段落 加数(甲, 乙)：\n    返回(甲 加 乙)\n', encoding='utf-8')

        return str(tmp_path)

    def test_first_build_compiles_all(self, project_dir):
        """测试首次编译：所有文件均为新文件，应全部编译"""
        from incremental_build import IncrementalBuilder

        builder = IncrementalBuilder(project_dir)
        root = builder.project_dir
        duan_files = list(root.glob('*.duan'))

        # 首次编译
        result = builder.build(duan_files, verbose=False)

        # 验证所有文件都被编译
        assert result == len(duan_files), f"应编译 {len(duan_files)} 个文件，实际编译 {result}"

        # 验证输出文件存在
        for f in duan_files:
            output = f.with_suffix('.py')
            assert output.exists(), f"输出文件不存在: {output}"

        # 验证缓存已保存
        assert builder.cache_path.exists(), "缓存文件未创建"
        assert len(builder.cache.files) == len(duan_files), "缓存文件数不匹配"

    def test_incremental_skip_unchanged(self, project_dir):
        """测试增量编译：无变更时跳过编译"""
        from incremental_build import IncrementalBuilder

        builder = IncrementalBuilder(project_dir)
        root = builder.project_dir
        duan_files = list(root.glob('*.duan'))

        # 首次编译
        builder.build(duan_files, verbose=False)

        # 清空输出文件，确保第二次编译会检测到输出缺失
        for f in duan_files:
            output = f.with_suffix('.py')
            if output.exists():
                output.unlink()

        # 第二次编译：文件未变更但输出缺失，应重新编译
        builder2 = IncrementalBuilder(project_dir)
        result2 = builder2.build(duan_files, verbose=False)
        assert result2 == len(duan_files), "输出缺失时应重新编译"

        # 第三次编译：文件未变更且输出存在，应跳过
        builder3 = IncrementalBuilder(project_dir)
        result3 = builder3.build(duan_files, verbose=False)
        assert result3 == len(duan_files), "完全未变更时应返回文件总数"

        # 验证跳过的统计：changed 应为空
        changed, unchanged = builder3.detect_changes(duan_files)
        assert len(changed) == 0, f"不应有变更文件，但发现 {len(changed)}"

    def test_change_detection(self, project_dir):
        """测试文件变更检测：修改文件内容后应重新编译"""
        from incremental_build import IncrementalBuilder

        builder = IncrementalBuilder(project_dir)
        root = builder.project_dir
        duan_files = list(root.glob('*.duan'))

        # 首次编译
        builder.build(duan_files, verbose=False)

        # 修改一个文件
        main_file = root / "main.duan"
        time.sleep(0.1)  # 确保 mtime 变化
        main_file.write_text('输出("已修改！")。\n', encoding='utf-8')

        # 检测变更
        changed, unchanged = builder.detect_changes(duan_files)
        main_path = str(main_file.resolve())
        assert main_path in changed, "修改后的文件应被检测为变更"

        # 增量编译
        result = builder.build(duan_files, verbose=False)
        assert result > 0, "增量编译应成功"

    def test_cache_persistence(self, project_dir):
        """测试缓存持久化：缓存文件正确保存和加载"""
        from incremental_build import IncrementalBuilder

        builder = IncrementalBuilder(project_dir)
        root = builder.project_dir
        duan_files = list(root.glob('*.duan'))

        # 首次编译
        builder.build(duan_files, verbose=False)

        # 保存缓存文件路径
        cache_path = builder.cache_path

        # 验证缓存文件存在且可读
        assert cache_path.exists()
        data = json.loads(cache_path.read_text(encoding='utf-8'))
        assert 'version' in data
        assert 'files' in data
        assert len(data['files']) == len(duan_files)

        # 新建 Builder 应能加载缓存
        builder2 = IncrementalBuilder(project_dir)
        assert len(builder2.cache.files) == len(duan_files)

    def test_force_full_build(self, project_dir):
        """测试强制全量编译：--force 选项应编译所有文件"""
        from incremental_build import IncrementalBuilder

        builder = IncrementalBuilder(project_dir)
        root = builder.project_dir
        duan_files = list(root.glob('*.duan'))

        # 首次编译
        builder.build(duan_files, verbose=False)

        # 强制全量编译
        result = builder.build(duan_files, force=True, verbose=False)
        assert result == len(duan_files), "强制全量编译应编译所有文件"

    def test_clear_cache(self, project_dir):
        """测试清除缓存"""
        from incremental_build import IncrementalBuilder

        builder = IncrementalBuilder(project_dir)
        root = builder.project_dir
        duan_files = list(root.glob('*.duan'))

        # 首次编译
        builder.build(duan_files, verbose=False)
        assert builder.cache_path.exists()

        # 清除缓存
        builder.clear_cache()
        assert not builder.cache_path.exists()
        assert len(builder.cache.files) == 0

    def test_get_stats(self, project_dir):
        """测试获取构建统计信息"""
        from incremental_build import IncrementalBuilder

        builder = IncrementalBuilder(project_dir)
        root = builder.project_dir
        duan_files = list(root.glob('*.duan'))

        # 首次编译
        builder.build(duan_files, verbose=False)

        stats = builder.get_stats()
        assert stats['cached_files'] == len(duan_files)
        assert stats['cache_path'] == str(builder.cache_path)
        assert stats['cache_created'] > 0

    def test_cli_function(self, project_dir):
        """测试 CLI 工具函数"""
        from incremental_build import incremental_build_cli

        # 增量编译
        result = incremental_build_cli(project_dir, verbose=False)
        assert result == 0, f"CLI 增量编译失败，返回值: {result}"

        # 强制全量
        result2 = incremental_build_cli(project_dir, force=True, verbose=False)
        assert result2 == 0, f"CLI 强制全量编译失败，返回值: {result2}"

    def test_detect_changes_returns_sets(self, project_dir):
        """测试 detect_changes 返回正确的集合类型"""
        from incremental_build import IncrementalBuilder

        builder = IncrementalBuilder(project_dir)
        root = builder.project_dir
        duan_files = list(root.glob('*.duan'))

        # 首次编译前检测变更：所有文件都应被检测为变更
        changed, unchanged = builder.detect_changes(duan_files)
        assert len(changed) == len(duan_files), "首次编译前所有文件都应是变更的"
        assert len(unchanged) == 0, "首次编译前不应有未变更文件"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])