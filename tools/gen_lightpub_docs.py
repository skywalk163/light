#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lightpub 包文档自动生成工具

从 stdlib/lightpub/__index__.py 读取包元数据，
遍历 stdlib/lightpub/ 目录下的桥接模块源码，
提取函数签名、参数、文档字符串，
为每个包生成标准格式的 Markdown API 文档。

用法:
    python tools/gen_lightpub_docs.py

输出:
    docs/lightpub/ 目录下每个包一个 .md 文件
    docs/lightpub/README.md 分类索引
"""

import os
import sys
import ast
import re
from pathlib import Path
from datetime import datetime

# ── 路径设置 ──────────────────────────────────────────────────────
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_TOOLS_DIR)
sys.path.insert(0, _PROJECT_DIR)

LIGHTPUB_DIR = os.path.join(_PROJECT_DIR, 'stdlib', 'lightpub')
DOCS_DIR = os.path.join(_PROJECT_DIR, 'docs', 'lightpub')

# 进度输出里有 ✓ / ✅，在 GBK 控制台（或被重定向成 GBK 管道）上会
# UnicodeEncodeError，而且崩点在 f.write(doc) 之后——生成会停在半路，
# 留下一个只改了几篇的 docs/lightpub/。只放宽编码错误处理，不改成 UTF-8：
# 包名是中文，GBK 本身放得下，换编码反而会让重定向出来的文件变成混合编码。
try:
    sys.stdout.reconfigure(errors='replace')
except (AttributeError, ValueError):
    pass

# 加载包索引
sys.path.insert(0, os.path.dirname(LIGHTPUB_DIR))
from lightpub.__index__ import PACKAGES, CATEGORIES, PRIORITY, TOTAL_PACKAGES

# 导入方式代码块的围栏标签，按「这条导入语句在本仓库到底跑不跑得通」逐块判定
from lightpub_importability import 判定

# 分类中文名映射
CATEGORY_NAMES = {
    'dev': '开发工具',
    'net': '网络通信',
    'database': '数据库',
    'security': '安全加密',
    'language': '语言特性',
    'media': '多媒体',
    'graphics': '图形渲染',
    'infrastructure': '基础设施',
    'output': '输出生成',
}

# 优先级标签
PRIORITY_LABELS = {
    'P0': '⭐ 核心包（已有 stdlib 桥接）',
    'P1': '🔶 高频包（需新建桥接）',
    'P2': '🔹 扩展包',
}


def extract_python_docstrings(filepath: str) -> dict:
    """从 Python 源码中提取函数签名和文档字符串"""
    result = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
    except (SyntaxError, FileNotFoundError):
        return result

    # 提取模块文档字符串
    module_doc = ast.get_docstring(tree) or ''

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            doc = ast.get_docstring(node) or ''

            # 提取参数
            params = []
            for arg in node.args.args:
                arg_name = arg.arg
                if arg_name == 'self':
                    continue
                params.append(arg_name)

            # 提取返回值注解
            returns = None
            if node.returns:
                if isinstance(node.returns, ast.Name):
                    returns = node.returns.id
                elif isinstance(node.returns, ast.Constant):
                    returns = str(node.returns.value)

            result[func_name] = {
                'name': func_name,
                'params': params,
                'returns': returns,
                'doc': doc.strip() if doc else '',
            }

    return result, module_doc


def generate_package_doc(pkg_name: str, pkg_info: dict) -> str:
    """为单个包生成 Markdown 文档"""
    lines = []
    cat_name = CATEGORY_NAMES.get(pkg_info.get('category', ''), pkg_info.get('category', '未分类'))
    priority_label = PRIORITY_LABELS.get(pkg_info.get('priority', ''), '')

    # 标题
    lines.append(f'# {pkg_name}')
    lines.append('')
    lines.append(f'> {pkg_info.get("description", "")}')
    lines.append('')

    # 元数据
    lines.append('## 包信息')
    lines.append('')
    lines.append('| 属性 | 值 |')
    lines.append('|------|-----|')
    lines.append(f'| 版本 | {pkg_info.get("version", "-")} |')
    lines.append(f'| 分类 | {cat_name} |')
    lines.append(f'| 优先级 | {priority_label} |')
    lines.append(f'| 公开函数 | {pkg_info.get("function_count", 0)} |')
    lines.append(f'| FFI 声明 | {pkg_info.get("ffi_count", 0)} |')

    stdlib_eq = pkg_info.get('stdlib_equivalent')
    if stdlib_eq:
        lines.append(f'| stdlib 对应 | {stdlib_eq} |')
    note = pkg_info.get('note', '')
    if note:
        lines.append(f'| 备注 | {note} |')
    lines.append('')

    # 关键词
    keywords = pkg_info.get('keywords', [])
    if keywords:
        lines.append('**关键词:** ' + ', '.join(keywords))
        lines.append('')

    # 依赖
    deps = pkg_info.get('dependencies', [])
    if deps:
        lines.append('**依赖包:** ' + ', '.join(f'[{d}]({d}.md)' for d in deps))
        lines.append('')

    # 导入方式
    #
    # 2026-08-21：这里原本无条件写死 ```duan 两个块，等于对每个包都承诺
    # 「这样写就能用」。实测 109 篇 × 2 块 = 218 块里只有 98 块真跑得通，
    # 其余 120 块要么本仓没实现、要么包名过不了词法。文档示例扫描面只验证
    # 「能否编译」，`导入 GUI框架` 编译得过、运行才 ModuleNotFoundError，
    # 它一个都抓不到。所以围栏标签改成按真实可导入性逐块判定：
    # 跑得通才给光明围栏，跑不通降 ```text 并写清跑不通的原因。
    # 判定不在这里复刻 P0/P1/P2 分支——tools/lightpub_importability.py
    # 直接调真正的代码生成器，让判据和编译器物理上不可能漂移。
    lines.append('## 导入方式')
    lines.append('')
    语句表 = [f'导入 {pkg_name}', f'导入 标准{pkg_name}']
    for 序号, 语句 in enumerate(语句表):
        if 序号:
            lines.append('或')
            lines.append('')
        结论 = 判定(语句)
        if 结论.可用:
            lines.append('```light')
            lines.append(语句)
            lines.append('```')
        else:
            lines.append(f'> ⚠️ 这种写法在本仓库跑不通：{结论.说明}')
            lines.append('>')
            lines.append('> 代码块因此标为 `text` 而非光明围栏，不参与文档示例编译扫描——'
                         '免得它冒充一个能用的示例。')
            lines.append('')
            lines.append('```text')
            lines.append(语句)
            lines.append('```')
        lines.append('')


    # 函数列表
    functions = pkg_info.get('functions', [])
    if functions:
        lines.append('## 函数列表')
        lines.append('')
        lines.append(f'共 {len(functions)} 个公开函数')
        lines.append('')

        # 尝试从桥接模块提取详细信息
        bridge_file = os.path.join(LIGHTPUB_DIR, f'{pkg_name}.py')
        extracted_funcs = {}
        module_doc = ''
        if os.path.exists(bridge_file):
            extracted_funcs, module_doc = extract_python_docstrings(bridge_file)

        if module_doc:
            lines.append('> ' + module_doc.replace('\n', '\n> '))
            lines.append('')

        for func_name in functions:
            lines.append(f'### {func_name}')
            lines.append('')

            # 如果有提取的详细信息
            if func_name in extracted_funcs:
                info = extracted_funcs[func_name]
                if info['params']:
                    lines.append(f'**参数:** `{", ".join(info["params"])}`')
                    lines.append('')
                if info['returns']:
                    lines.append(f'**返回:** `{info["returns"]}`')
                    lines.append('')
                if info['doc']:
                    lines.append(info['doc'])
                    lines.append('')
            else:
                lines.append('*暂无详细文档*')
                lines.append('')

    return '\n'.join(lines)


def generate_category_index() -> str:
    """生成分类索引页面"""
    lines = []
    lines.append('# lightpub 包文档索引')
    lines.append('')
    lines.append(f'> 共 {TOTAL_PACKAGES} 个包，{sum(p.get("function_count", 0) for p in PACKAGES.values())} 个公开函数')
    lines.append('')
    lines.append('## 按分类浏览')
    lines.append('')

    for cat_key, cat_name in sorted(CATEGORY_NAMES.items()):
        pkg_list = CATEGORIES.get(cat_key, [])
        if not pkg_list:
            continue
        lines.append(f'### {cat_name}')
        lines.append('')
        lines.append(f'共 {len(pkg_list)} 个包')
        lines.append('')
        lines.append('| 包名 | 描述 | 优先级 | 函数数 |')
        lines.append('|------|------|--------|--------|')
        for pkg_name in sorted(pkg_list):
            info = PACKAGES.get(pkg_name, {})
            desc = info.get('description', '')
            priority = info.get('priority', '')
            func_count = info.get('function_count', 0)
            lines.append(f'| [{pkg_name}]({pkg_name}.md) | {desc} | {priority} | {func_count} |')
        lines.append('')

    # 按优先级浏览
    lines.append('## 按优先级浏览')
    lines.append('')
    for pri_key in ['P0', 'P1', 'P2']:
        pkg_list = PRIORITY.get(pri_key, [])
        if not pkg_list:
            continue
        label = PRIORITY_LABELS.get(pri_key, pri_key)
        lines.append(f'### {label}')
        lines.append('')
        lines.append(f'共 {len(pkg_list)} 个包')
        lines.append('')
        for pkg_name in sorted(pkg_list):
            info = PACKAGES.get(pkg_name, {})
            desc = info.get('description', '')
            lines.append(f'- [{pkg_name}]({pkg_name}.md) — {desc}')
        lines.append('')

    # 统计信息
    lines.append('## 统计信息')
    lines.append('')
    lines.append(f'- **总包数:** {TOTAL_PACKAGES}')
    lines.append(f'- **总函数数:** {sum(p.get("function_count", 0) for p in PACKAGES.values())}')
    lines.append(f'- **总 FFI 声明数:** {sum(p.get("ffi_count", 0) for p in PACKAGES.values())}')
    lines.append(f'- **P0 (已有桥接):** {len(PRIORITY.get("P0", []))} 包')
    lines.append(f'- **P1 (需新建):** {len(PRIORITY.get("P1", []))} 包')
    lines.append(f'- **P2 (扩展):** {len(PRIORITY.get("P2", []))} 包')
    lines.append('')
    lines.append(f'*文档生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*')
    lines.append('')

    return '\n'.join(lines)


def ensure_docs_dir():
    """确保 docs/lightpub/ 目录存在"""
    os.makedirs(DOCS_DIR, exist_ok=True)


def main():
    print(f"lightpub 包文档生成工具")
    print(f"=" * 40)
    print(f"总包数: {TOTAL_PACKAGES}")
    print()

    ensure_docs_dir()

    # 1. 生成每个包的文档
    success_count = 0
    for pkg_name, pkg_info in sorted(PACKAGES.items()):
        doc = generate_package_doc(pkg_name, pkg_info)
        output_path = os.path.join(DOCS_DIR, f'{pkg_name}.md')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(doc)
        success_count += 1
        print(f"  ✓ {pkg_name} ({pkg_info.get('function_count', 0)} 函数)")

    # 2. 生成分类索引
    index = generate_category_index()
    index_path = os.path.join(DOCS_DIR, 'README.md')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index)
    print(f"\n  ✓ 分类索引 (README.md)")

    print(f"\n✅ 完成! 共生成 {success_count} 个包文档 + 1 个分类索引")
    print(f"   输出目录: {DOCS_DIR}")


if __name__ == '__main__':
    main()