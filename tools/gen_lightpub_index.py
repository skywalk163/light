#!/usr/bin/env python3
"""
lightpub 包索引生成器

扫描 lightpub/packages/ 下所有包，提取元数据，生成结构化索引文件 __index__.py。
可复用：lightpub 包增删后重新运行此脚本即可更新索引。

用法:
    python tools/gen_lightpub_index.py [--lightpub-path PATH] [--output PATH]

默认:
    --lightpub-path: C:/dumatework/lightpub
    --output:       stdlib/lightpub/__index__.py
"""

import os
import re
import sys
import argparse
from pathlib import Path


def parse_toml_simple(toml_path: str) -> dict:
    """简易 TOML 解析器，仅支持段件.toml 使用的格式（key = value, list, no nested tables beyond [段件]）"""
    result = {}
    with open(toml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配 key = "value"
    for m in re.finditer(r'^(\w+)\s*=\s*"([^"]*)"', content, re.MULTILINE):
        result[m.group(1)] = m.group(2)

    # 匹配 key = ["a", "b"]
    for m in re.finditer(r'^(\w+)\s*=\s*\[([^\]]*)\]', content, re.MULTILINE):
        items_str = m.group(2)
        items = [s.strip().strip('"').strip("'") for s in items_str.split(',') if s.strip()]
        result[m.group(1)] = items

    return result


def extract_functions(light_path: str) -> list:
    """从源.light 中提取公开函数名（跳过 _内部 函数）"""
    funcs = []
    if not os.path.exists(light_path):
        return funcs
    with open(light_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 匹配: 函数 函数名 接收 ...：  或  函数 函数名：
            m = re.match(r'^函数\s+(\S+)(?:\s+接收)?', line)
            if m:
                name = m.group(1)
                if not name.startswith('_'):
                    funcs.append(name)
    return funcs


def extract_ffi_count(light_path: str) -> int:
    """统计 FFI 外部函数声明数量"""
    if not os.path.exists(light_path):
        return 0
    count = 0
    with open(light_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('外部 段落'):
                count += 1
    return count


# 10 个高频包与现有 stdlib 的对应关系
PRIORITY_MAP = {
    '文件系统':   {'priority': 'P0', 'stdlib_equivalent': '文件系统', 'note': '已有 Python 实现，桥接到 stdlib'},
    'JSON':       {'priority': 'P0', 'stdlib_equivalent': 'JSON',     'note': '已有 Python 实现，桥接到 stdlib'},
    'CSV':        {'priority': 'P0', 'stdlib_equivalent': 'CSV读写器', 'note': '已有 Python 实现，桥接到 stdlib'},
    '正则表达式': {'priority': 'P0', 'stdlib_equivalent': '正则表达式', 'note': '已有 Python 实现，桥接到 stdlib'},
    '日期时间':   {'priority': 'P0', 'stdlib_equivalent': '历法',     'note': '已有 Python 实现，桥接到 stdlib'},
    '数学运算':   {'priority': 'P0', 'stdlib_equivalent': '数学',     'note': '已有 Python 实现，桥接到 stdlib'},
    '加密':       {'priority': 'P1', 'stdlib_equivalent': '加密',     'note': '已有 Python 实现，桥接到 stdlib'},
    'HTTP客户端': {'priority': 'P1', 'stdlib_equivalent': None,       'note': '需新建，基于 requests'},
    'Socket':     {'priority': 'P1', 'stdlib_equivalent': None,       'note': '需新建，基于 socket'},
    'SQLite':     {'priority': 'P1', 'stdlib_equivalent': None,       'note': '需新建，基于 sqlite3'},
}


def scan_packages(lightpub_root: str) -> list:
    """扫描所有包，返回结构化元数据列表"""
    packages_dir = Path(lightpub_root) / 'packages'
    if not packages_dir.exists():
        print(f"ERROR: packages directory not found: {packages_dir}", file=sys.stderr)
        return []

    results = []
    for pkg_dir in sorted(packages_dir.iterdir()):
        if not pkg_dir.is_dir():
            continue

        pkg_name = pkg_dir.name
        toml_path = pkg_dir / '段件.toml'
        src_path = pkg_dir / '源.light'

        # 解析段件.toml
        meta = parse_toml_simple(str(toml_path)) if toml_path.exists() else {}

        # 提取函数和 FFI 信息
        functions = extract_functions(str(src_path)) if src_path.exists() else []
        ffi_count = extract_ffi_count(str(src_path)) if src_path.exists() else 0

        # 优先级标注
        priority_info = PRIORITY_MAP.get(pkg_name, {'priority': 'P2', 'stdlib_equivalent': None, 'note': ''})

        pkg_info = {
            'name': pkg_name,
            'version': meta.get('版本', '0.0.0'),
            'description': meta.get('描述', ''),
            'author': meta.get('作者', ''),
            'namespace': meta.get('命名空间', 'std'),
            'category': meta.get('分类', ''),
            'keywords': meta.get('关键词', []),
            'dependencies': meta.get('依赖', []),
            'functions': functions,
            'function_count': len(functions),
            'ffi_count': ffi_count,
            'has_source': src_path.exists(),
            'priority': priority_info['priority'],
            'stdlib_equivalent': priority_info['stdlib_equivalent'],
            'note': priority_info['note'],
            'path': f'packages/{pkg_name}',
        }
        results.append(pkg_info)

    return results


def generate_index(packages: list, lightpub_root: str) -> str:
    """生成 __index__.py 内容"""
    lines = [
        '"""',
        'lightpub 包索引 (自动生成)',
        '',
        f'包总数: {len(packages)}',
        f'数据源: {lightpub_root}/packages/',
        f'生成工具: tools/gen_lightpub_index.py',
        '',
        '此文件由脚本自动生成，请勿手动编辑。',
        '如需更新索引，运行: python tools/gen_lightpub_index.py',
        '"""',
        '',
        '# 每个包的元数据',
        'PACKAGES = {',
    ]

    for pkg in packages:
        lines.append(f'    {repr(pkg["name"])}: {{')
        lines.append(f'        "version": {repr(pkg["version"])},')
        lines.append(f'        "description": {repr(pkg["description"])},')
        lines.append(f'        "category": {repr(pkg["category"])},')
        lines.append(f'        "keywords": {repr(pkg["keywords"])},')
        lines.append(f'        "dependencies": {repr(pkg["dependencies"])},')
        lines.append(f'        "functions": {repr(pkg["functions"])},')
        lines.append(f'        "function_count": {pkg["function_count"]},')
        lines.append(f'        "ffi_count": {pkg["ffi_count"]},')
        lines.append(f'        "has_source": {repr(pkg["has_source"])},')
        lines.append(f'        "priority": {repr(pkg["priority"])},')
        lines.append(f'        "stdlib_equivalent": {repr(pkg["stdlib_equivalent"])},')
        lines.append(f'        "note": {repr(pkg["note"])},')
        lines.append(f'        "path": {repr(pkg["path"])},')
        lines.append('    },')

    lines.append('}')
    lines.append('')

    # 分类索引
    lines.append('# 按分类分组')
    lines.append('CATEGORIES = {')
    cat_map = {}
    for pkg in packages:
        cat = pkg['category'] or 'other'
        cat_map.setdefault(cat, []).append(pkg['name'])
    for cat in sorted(cat_map.keys()):
        lines.append(f'    {repr(cat)}: {repr(sorted(cat_map[cat]))},')
    lines.append('}')
    lines.append('')

    # 优先级索引
    lines.append('# 按优先级分组 (P0=高频已有stdlib/P1=高频需新建/P2=其他)')
    lines.append('PRIORITY = {')
    pri_map = {}
    for pkg in packages:
        pri_map.setdefault(pkg['priority'], []).append(pkg['name'])
    for pri in sorted(pri_map.keys()):
        lines.append(f'    {repr(pri)}: {repr(sorted(pri_map[pri]))},')
    lines.append('}')
    lines.append('')

    # 导入名映射（去重处理：与 stdlib 同名的包加"标准"前缀可选）
    lines.append('# 导入名 -> lightpub 包名映射')
    lines.append('# 光明代码可用 "导入 标准文件系统" 或 "导入 文件系统" 访问')
    lines.append('IMPORT_MAP = {')
    for pkg in packages:
        name = pkg['name']
        lines.append(f'    {repr(name)}: {repr(name)},  # 直接名')
        lines.append(f'    {repr("标准" + name)}: {repr(name)},  # 标准前缀')
    lines.append('}')
    lines.append('')

    # 统计摘要
    total_funcs = sum(p['function_count'] for p in packages)
    total_ffis = sum(p['ffi_count'] for p in packages)
    lines.append(f'# 统计: {len(packages)} 包, {total_funcs} 公开函数, {total_ffis} FFI 声明')
    lines.append(f'TOTAL_PACKAGES = {len(packages)}')
    lines.append(f'TOTAL_FUNCTIONS = {total_funcs}')
    lines.append(f'TOTAL_FFI = {total_ffis}')

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='lightpub 包索引生成器')
    parser.add_argument('--lightpub-path', default='C:/dumatework/lightpub',
                        help='lightpub 根目录路径')
    parser.add_argument('--output', default=None,
                        help='输出文件路径 (默认: stdlib/lightpub/__index__.py)')
    args = parser.parse_args()

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        # 相对当前工作目录
        output_path = Path('stdlib/lightpub/__index__.py')

    print(f"扫描 lightpub 包: {args.lightpub_path}/packages/")
    packages = scan_packages(args.lightpub_path)

    if not packages:
        print("ERROR: 未找到任何包", file=sys.stderr)
        sys.exit(1)

    print(f"发现 {len(packages)} 个包")

    # 打印统计
    p0 = [p for p in packages if p['priority'] == 'P0']
    p1 = [p for p in packages if p['priority'] == 'P1']
    p2 = [p for p in packages if p['priority'] == 'P2']
    print(f"  P0 (高频,已有stdlib): {len(p0)} 包")
    print(f"  P1 (高频,需新建):     {len(p1)} 包")
    print(f"  P2 (其他):            {len(p2)} 包")
    print(f"  总函数数: {sum(p['function_count'] for p in packages)}")
    print(f"  总FFI数:  {sum(p['ffi_count'] for p in packages)}")

    # 生成索引
    content = generate_index(packages, args.lightpub_path)

    # 写入文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding='utf-8')
    print(f"\n索引已写入: {output_path}")
    print(f"文件大小: {output_path.stat().st_size} bytes")


if __name__ == '__main__':
    main()
