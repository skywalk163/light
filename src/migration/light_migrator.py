# -*- coding: utf-8 -*-
"""
光明代码迁移工具 (Light Migrator) v1.1

统一的代码迁移入口，支持 v3.3 → v4.0 → v5.x 的语法转换。

用法:
    from migration.light_migrator import LightMigrator

    migrator = LightMigrator()
    # 自动检测并迁移
    result = migrator.migrate(source_code)
    # 或指定迁移路径
    result = migrator.migrate_v33_to_v40(source_code)
    result = migrator.migrate_v40_to_v50(source_code)

命令行:
    python -m src.migration.light_migrator detect file.light     # 检测语法版本
    python -m src.migration.light_migrator v33-v40 file.light    # v3.3 → v4.0
    python -m src.migration.light_migrator v40-v50 file.light    # v4.0 → v5.x
    python -m src.migration.light_migrator auto file.light       # 自动检测并迁移
    python -m src.migration.light_migrator auto --preview file.light  # 预览
"""

import re
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.migration.v33_to_v40 import MigrationV33ToV40
from src.migration.v40_to_v50 import MigrationV40ToV50


# =============================================================================
# 版本检测器
# =============================================================================

class VersionDetector:
    """检测光明代码的语法版本"""

    # v3.3 特有语法特征
    V33_PATTERNS = [
        r'定义\s+\S+\s+等于',      # 定义 x 等于 y
        r'(?:段落|段|函数)\s+\S+\s+接收',  # 段 名 接收 参数
        r'[\u4e00-\u9fff\w]之[\u4e00-\u9fff\w]',  # 对象之属性
        r'\b打印\b',               # 打印
        r'\b输出\b',               # 输出
    ]

    # v4.0 特有语法特征
    V40_PATTERNS = [
        r'(?:设|定义)\s+\S+\s+为\s+',  # 设 x 为 y
        r'(?:段|函)\s+\S+\s*\(',       # 段 名(
        r'\b印\b',                     # 印
        r'\b引\b',                     # 引
    ]

    # v5.x 特有语法特征
    V50_PATTERNS = [
        r'->\s*\w+',                        # 返回类型注解
        r'→\s*\w+',                         # 中文返回类型注解
        r'引\s+\S+\s+为\s+\S+',             # 引 x 为 y
        r'引\s+\S+\s+中\s+\S+',             # 引 x 中 y
        r'\b异步\b',                         # 异步
        r'\b等待\b',                         # 等待
        r'\b泛型\b',                         # 泛型
        r'列表<\w+>',                        # 列表<类型>
        r'映射<\w+,\s*\w+>',                # 映射<类型, 类型>
    ]

    @classmethod
    def detect(cls, source: str) -> str:
        """
        检测代码语法版本

        Returns:
            'v33', 'v40', 'v50', 或 'unknown'
        """
        v33_score = 0
        v40_score = 0
        v50_score = 0

        for pattern in cls.V33_PATTERNS:
            if re.search(pattern, source):
                v33_score += 1

        for pattern in cls.V40_PATTERNS:
            if re.search(pattern, source):
                v40_score += 1

        for pattern in cls.V50_PATTERNS:
            if re.search(pattern, source):
                v50_score += 1

        # 判定：优先匹配最高版本
        if v50_score >= 2:
            return 'v50'
        if v40_score >= 3 and v33_score == 0:
            return 'v40'
        if v33_score >= 2:
            return 'v33'
        if v40_score > 0:
            return 'v40'
        if v33_score > 0:
            return 'v33'

        return 'unknown'


# =============================================================================
# 统一迁移器
# =============================================================================

class LightMigrator:
    """
    光明代码迁移器（统一入口）

    支持自动检测版本并执行 v3.3 → v4.0 → v5.x 的递进迁移。
    """

    def __init__(self):
        self.migrator_v33 = MigrationV33ToV40()
        self.migrator_v40 = MigrationV40ToV50()
        self.detector = VersionDetector()

    def migrate(self, source: str) -> Tuple[str, List[str]]:
        """
        自动检测版本并迁移到最新语法

        Args:
            source: 源代码

        Returns:
            (迁移后的代码, 迁移日志)
        """
        version = self.detector.detect(source)
        logs = [f"检测到语法版本: {version}"]

        if version == 'v33':
            logs.append("执行 v3.3 → v4.0 迁移...")
            v40_source = self.migrator_v33.migrate(source)
            logs.append("v3.3 → v4.0 迁移完成")
            logs.append("执行 v4.0 → v5.x 迁移...")
            v50_source = self.migrator_v40.migrate(v40_source)
            logs.append("v4.0 → v5.x 迁移完成")
            return v50_source, logs

        elif version == 'v40':
            logs.append("执行 v4.0 → v5.x 迁移...")
            result = self.migrator_v40.migrate(source)
            logs.append("v4.0 → v5.x 迁移完成")
            return result, logs

        elif version == 'v50':
            logs.append("代码已是最新 v5.x 语法，无需迁移")
            return source, logs

        else:
            logs.append("无法确定语法版本，代码保持原样")
            return source, logs

    def migrate_v33_to_v40(self, source: str) -> str:
        """执行 v3.3 → v4.0 迁移"""
        return self.migrator_v33.migrate(source)

    def migrate_v40_to_v50(self, source: str) -> str:
        """执行 v4.0 → v5.x 迁移"""
        return self.migrator_v40.migrate(source)

    def migrate_file(self, file_path: str) -> Tuple[str, List[str]]:
        """
        自动检测并迁移文件

        Args:
            file_path: 文件路径

        Returns:
            (迁移后的代码, 迁移日志)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        result, logs = self.migrate(source)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(result)

        logs.append(f"已写入文件: {file_path}")
        return result, logs

    def migrate_directory(self, dir_path: str) -> Dict[str, Tuple[str, List[str]]]:
        """
        迁移目录中的所有 .light 文件

        Args:
            dir_path: 目录路径

        Returns:
            {文件路径: (迁移后代码, 迁移日志)}
        """
        results = {}
        base = Path(dir_path)
        for f in base.rglob('*.light'):
            try:
                result, logs = self.migrate_file(str(f))
                results[str(f)] = (result, logs)
            except Exception as e:
                results[str(f)] = ('', [f'错误: {e}'])
        return results

    def preview(self, source: str) -> Dict[str, List[Dict]]:
        """
        预览迁移变更

        Args:
            source: 源代码

        Returns:
            {'v33_to_v40': [...], 'v40_to_v50': [...]}
        """
        version = self.detector.detect(source)
        result = {}

        if version in ('v33', 'unknown'):
            changes = self.migrator_v33.preview_changes(source)
            if changes:
                result['v33_to_v40'] = changes

        if version in ('v33', 'v40', 'unknown'):
            changes = self.migrator_v40.preview_changes(source)
            if changes:
                result['v40_to_v50'] = changes

        return result


# =============================================================================
# 命令行界面
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog='light-migrator',
        description='光明代码迁移工具 - 统一入口'
    )
    parser.add_argument('command', choices=['detect', 'v33-v40', 'v40-v50', 'auto'],
                        help='操作: detect(检测版本), v33-v40(迁移), v40-v50(迁移), auto(自动)')
    parser.add_argument('target', help='文件或目录路径')
    parser.add_argument('--preview', action='store_true', help='预览模式，不修改文件')
    parser.add_argument('--report', action='store_true', help='生成迁移报告')

    args = parser.parse_args()
    migrator = LightMigrator()
    target_path = args.target

    if args.command == 'detect':
        if os.path.isfile(target_path):
            with open(target_path, 'r', encoding='utf-8') as f:
                source = f.read()
            version = VersionDetector.detect(source)
            print(f"文件: {target_path}")
            print(f"语法版本: {version}")
        elif os.path.isdir(target_path):
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                for f in files:
                    if f.endswith('.light'):
                        fp = os.path.join(root, f)
                        with open(fp, 'r', encoding='utf-8') as sf:
                            source = sf.read()
                        version = VersionDetector.detect(source)
                        print(f"  {fp}: {version}")
        else:
            print(f"错误: 路径不存在: {target_path}")
            return 1
        return 0

    if args.preview:
        if os.path.isfile(target_path):
            with open(target_path, 'r', encoding='utf-8') as f:
                source = f.read()
            changes = migrator.preview(source)
            if not changes:
                print("无需修改")
            else:
                for step, step_changes in changes.items():
                    migrator_obj = migrator.migrator_v33 if step == 'v33_to_v40' else migrator.migrator_v40
                    print(migrator_obj.report(step_changes))
        elif os.path.isdir(target_path):
            all_changes = {'v33_to_v40': [], 'v40_to_v50': []}
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                for f in files:
                    if f.endswith('.light'):
                        fp = os.path.join(root, f)
                        with open(fp, 'r', encoding='utf-8') as sf:
                            source = sf.read()
                        changes = migrator.preview(source)
                        for step, step_changes in changes.items():
                            all_changes.setdefault(step, []).extend(step_changes)
            for step, step_changes in all_changes.items():
                if step_changes:
                    migrator_obj = migrator.migrator_v33 if step == 'v33_to_v40' else migrator.migrator_v40
                    print(migrator_obj.report(step_changes))
        else:
            print(f"错误: 路径不存在: {target_path}")
            return 1
        return 0

    # 执行迁移
    if args.command == 'v33-v40':
        migrator_impl = migrator.migrator_v33
    elif args.command == 'v40-v50':
        migrator_impl = migrator.migrator_v40
    elif args.command == 'auto':
        if os.path.isfile(target_path):
            result, logs = migrator.migrate_file(target_path)
            for log in logs:
                print(f"  {log}")
            return 0
        elif os.path.isdir(target_path):
            results = migrator.migrate_directory(target_path)
            success = sum(1 for v in results.values() if not v[1][-1].startswith('错误'))
            failed = sum(1 for v in results.values() if v[1][-1].startswith('错误'))
            print(f"已完成: {success} 个文件, 失败: {failed} 个")
            return 0
        else:
            print(f"错误: 路径不存在: {target_path}")
            return 1

    # 非 auto 模式的迁移执行
    if os.path.isfile(target_path):
        if target_path.endswith('.light'):
            print(f"迁移: {target_path}")
            if args.command == 'v33-v40':
                result = migrator_impl.migrate_file(target_path)
            else:
                result = migrator_impl.migrate_file(target_path)
            print(f"  ✓ 已完成")
        else:
            print(f"错误: 仅支持 .light 文件: {target_path}")
            return 1
    elif os.path.isdir(target_path):
        print(f"迁移目录: {target_path}")
        results = migrator_impl.migrate_directory(target_path)
        success = sum(1 for v in results.values() if not v.startswith('错误'))
        failed = sum(1 for v in results.values() if v.startswith('错误'))
        print(f"  ✓ {success} 个文件完成")
        if failed:
            print(f"  ✗ {failed} 个文件失败")
    else:
        print(f"错误: 路径不存在: {target_path}")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())