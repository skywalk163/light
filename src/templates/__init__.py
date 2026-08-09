# -*- coding: utf-8 -*-
"""
光明项目模板包

提供开箱即用的项目模板：
- student_management: 学生管理系统
- web_service: Web 服务
- data_analysis: 数据分析
"""

import os
import shutil
from pathlib import Path

TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__))


def list_templates() -> list:
    """列出所有可用模板"""
    templates = []
    for item in sorted(os.listdir(TEMPLATES_DIR)):
        item_path = os.path.join(TEMPLATES_DIR, item)
        if os.path.isdir(item_path) and not item.startswith('_') and not item.startswith('.'):
            pkg_toml = os.path.join(item_path, 'package.toml')
            description = ""
            if os.path.exists(pkg_toml):
                with open(pkg_toml, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('description'):
                            description = line.split('=')[1].strip().strip('"').strip("'")
                            break
            templates.append({
                'name': item,
                'description': description,
                'path': item_path,
            })
    return templates


def copy_template(template_name: str, target_dir: str) -> bool:
    """复制模板到目标目录"""
    template_path = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.isdir(template_path):
        print(f"错误: 未找到模板 '{template_name}'")
        print(f"可用模板: {', '.join(t['name'] for t in list_templates())}")
        return False

    target_path = Path(target_dir)
    if target_path.exists():
        print(f"错误: 目标目录 '{target_dir}' 已存在")
        return False

    shutil.copytree(template_path, target_path)
    print(f"已从模板 '{template_name}' 创建项目: {target_dir}")
    return True