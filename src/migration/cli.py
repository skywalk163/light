# -*- coding: utf-8 -*-
"""
光明代码迁移工具 - 命令行界面

用法:
    python -m src.migration.cli v33-v40 file.light     # 迁移单个文件
    python -m src.migration.cli v33-v40 .              # 迁移目录
    python -m src.migration.cli v33-v40 --preview file.light  # 预览变更
    python -m src.migration.cli v40-v50 file.light     # v4.0 → v5.x 迁移
    python -m src.migration.cli --list                 # 列出可用迁移
"""

import os
import sys
import argparse
from pathlib import Path

from src.migration.v33_to_v40 import MigrationV33ToV40
from src.migration.v40_to_v50 import MigrationV40ToV50


def list_migrations():
    """列出可用迁移"""
    print("可用迁移:")
    print("  v33-v40    v3.3 → v4.0 代码迁移")
    print("  v40-v50    v4.0 → v5.x 代码迁移")
    print()
    print("用法:")
    print("  python -m src.migration.cli <迁移> <文件或目录> [选项]")


def main():
    parser = argparse.ArgumentParser(
        prog='light-migrate',
        description='光明代码迁移工具'
    )
    parser.add_argument('migration', nargs='?', help='迁移类型: v33-v40, v40-v50')
    parser.add_argument('target', nargs='?', help='文件或目录路径')
    parser.add_argument('--preview', action='store_true', help='预览模式，不修改文件')
    parser.add_argument('--report', action='store_true', help='生成迁移报告')
    parser.add_argument('--list', action='store_true', help='列出可用迁移')
    args = parser.parse_args()

    if args.list:
        list_migrations()
        return 0

    if not args.migration or not args.target:
        parser.print_help()
        return 1

    if args.migration == 'v33-v40':
        migrator = MigrationV33ToV40()
    elif args.migration == 'v40-v50':
        migrator = MigrationV40ToV50()
    else:
        print(f"错误: 未知的迁移类型: {args.migration}")
        print("可用迁移: v33-v40, v40-v50")
        return 1

    target_path = args.target

    if args.preview:
        # 预览模式
        if os.path.isfile(target_path):
            with open(target_path, 'r', encoding='utf-8') as f:
                source = f.read()
            changes = migrator.preview_changes(source)
            print(migrator.report(changes))
        elif os.path.isdir(target_path):
            all_changes = []
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                for f in files:
                    if f.endswith('.light'):
                        fp = os.path.join(root, f)
                        with open(fp, 'r', encoding='utf-8') as sf:
                            source = sf.read()
                        changes = migrator.preview_changes(source)
                        all_changes.extend(changes)
            print(migrator.report(all_changes))
        else:
            print(f"错误: 路径不存在: {target_path}")
            return 1
        return 0

    if args.report:
        # 报告模式
        if os.path.isfile(target_path):
            with open(target_path, 'r', encoding='utf-8') as f:
                source = f.read()
            changes = migrator.preview_changes(source)
            print(migrator.report(changes))
        elif os.path.isdir(target_path):
            all_changes = []
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                for f in files:
                    if f.endswith('.light'):
                        fp = os.path.join(root, f)
                        with open(fp, 'r', encoding='utf-8') as sf:
                            source = sf.read()
                        changes = migrator.preview_changes(source)
                        all_changes.extend(changes)
            print(migrator.report(all_changes))
        else:
            print(f"错误: 路径不存在: {target_path}")
            return 1
        return 0

    # 执行迁移
    if os.path.isfile(target_path):
        if target_path.endswith('.light'):
            print(f"迁移: {target_path}")
            result = migrator.migrate_file(target_path)
            print(f"  ✓ 已完成")
        else:
            print(f"错误: 仅支持 .light 文件: {target_path}")
            return 1
    elif os.path.isdir(target_path):
        print(f"迁移目录: {target_path}")
        results = migrator.migrate_directory(target_path)
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