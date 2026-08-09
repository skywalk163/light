# -*- coding: utf-8 -*-
"""
光明文档站化工具

功能：
1. 验证文档链接完整性
2. 生成文档索引
3. 检查文档格式
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple


DOCS_DIR = Path(__file__).parent.parent / 'docs'


def check_broken_links(verbose: bool = True) -> List[Tuple[str, str]]:
    """检查文档中的死链接"""
    broken_links = []
    
    if not DOCS_DIR.exists():
        return broken_links
    
    md_files = list(DOCS_DIR.glob('**/*.md'))
    
    # 收集所有可用的 markdown 文件
    available_files = {f.stem for f in md_files}
    
    for md_file in md_files:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配 markdown 链接 [text](file.md) 和 [text](file.md#anchor)
        for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', content):
            link = m.group(2)
            
            # 跳过外部链接
            if link.startswith(('http://', 'https://', 'mailto:')):
                continue
            
            # 移除锚点
            if '#' in link:
                link = link.split('#')[0]
            
            # 跳过空链接
            if not link or link == '#':
                continue
            
            # 检查本地文件
            if link.endswith('.md'):
                link_stem = Path(link).stem
                if link_stem not in available_files:
                    broken_links.append((str(md_file.relative_to(DOCS_DIR)), link))
                    if verbose:
                        print(f"❌ 死链接: {md_file.relative_to(DOCS_DIR)}: {m.group(1)} -> {link}")
    
    return broken_links


def check_unused_files(nav_files: List[str]) -> List[str]:
    """检查 nav 中未引用但存在的文件"""
    available = {f.stem for f in DOCS_DIR.glob('*.md')}
    nav_stems = {Path(f).stem for f in nav_files}
    unused = available - nav_stems
    return sorted(unused)


def check_toc_structure() -> Dict:
    """检查文档目录结构"""
    result = {
        'total': 0,
        'with_title': 0,
        'with_toc': 0,
        'by_category': {},
    }
    
    for md_file in DOCS_DIR.glob('*.md'):
        result['total'] += 1
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if re.search(r'^# .+', content, re.MULTILINE):
            result['with_title'] += 1
        
        if '## 目录' in content or '## 概览' in content or '## ' in content:
            result['with_toc'] += 1
    
    return result


def check_code_examples() -> Dict:
    """检查文档中的代码示例"""
    result = {
        'total_blocks': 0,
        'light_blocks': 0,
        'python_blocks': 0,
        'other_blocks': 0,
    }
    
    for md_file in DOCS_DIR.glob('*.md'):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配代码块
        for m in re.finditer(r'```(\w+)?\n(.*?)```', content, re.DOTALL):
            result['total_blocks'] += 1
            lang = m.group(1) or 'text'
            if lang in ('光明', 'light'):
                result['light_blocks'] += 1
            elif lang in ('python', 'py'):
                result['python_blocks'] += 1
            else:
                result['other_blocks'] += 1
    
    return result


def generate_index_report() -> str:
    """生成文档索引报告"""
    lines = []
    lines.append("# 光明文档索引")
    lines.append("")
    
    if not DOCS_DIR.exists():
        lines.append("⚠️  docs 目录不存在")
        return "\n".join(lines)
    
    md_files = sorted(DOCS_DIR.glob('*.md'))
    lines.append(f"**文档总数**: {len(md_files)}")
    lines.append("")
    
    # 按类别分组
    categories = {
        '入门': ['index', 'getting-started', 'quickstart'],
        '语言': ['syntax', 'USER_MANUAL', '光明-完整规范文档', 'LANGUAGE_EXTENSIONS'],
        '设计': ['class_system_design', 'llvm_backend_design', 'module_system_design',
                'architecture', '可空类型', 'HM', 'interface'],
        '工具': ['tools', 'REPL', 'BOOTSTRAP', 'lsp'],
        '标准库': ['stdlib', 'API_REFERENCE'],
        '报告': ['PROGRESS_REPORT', 'OPTIMIZATION', 'PERFORMANCE', 'FILE_IO', 'MODULE_SYSTEM',
                'RELEASE_CHECKLIST', 'FINAL_SUMMARY'],
    }
    
    files_by_stem = {f.stem: f for f in md_files}
    
    used = set()
    for cat, stems in categories.items():
        cat_files = [files_by_stem[s] for s in stems if s in files_by_stem]
        if cat_files:
            lines.append(f"## {cat}")
            lines.append("")
            for f in cat_files:
                used.add(f.stem)
                title = _extract_title(f) or f.stem
                lines.append(f"- [{title}]({f.name})")
            lines.append("")
    
    # 其他文档
    other = [f for f in md_files if f.stem not in used]
    if other:
        lines.append("## 其他")
        lines.append("")
        for f in other:
            title = _extract_title(f) or f.stem
            lines.append(f"- [{title}]({f.name})")
        lines.append("")
    
    return "\n".join(lines)


def _extract_title(md_file: Path) -> str:
    """提取 markdown 文件的第一个标题"""
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        m = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        return m.group(1).strip() if m else md_file.stem
    except Exception:
        return md_file.stem


def main():
    """主入口"""
    import argparse
    parser = argparse.ArgumentParser(description='光明文档站化工具')
    parser.add_argument('--check-links', action='store_true', help='检查死链接')
    parser.add_argument('--check-toc', action='store_true', help='检查文档结构')
    parser.add_argument('--check-code', action='store_true', help='检查代码示例')
    parser.add_argument('--gen-index', action='store_true', help='生成索引')
    parser.add_argument('--output', '-o', help='输出报告到文件')
    args = parser.parse_args()
    
    print("=" * 60)
    print("光明文档站化工具")
    print("=" * 60)
    
    if not DOCS_DIR.exists():
        print(f"⚠️  文档目录不存在: {DOCS_DIR}")
        return
    
    md_files = list(DOCS_DIR.glob('*.md'))
    print(f"📚 发现 {len(md_files)} 个 markdown 文件")
    print()
    
    if args.check_links or not any([args.check_toc, args.check_code, args.gen_index]):
        print("🔗 检查死链接...")
        broken = check_broken_links(verbose=True)
        if broken:
            print(f"\n❌ 发现 {len(broken)} 个死链接")
        else:
            print("✅ 没有发现死链接")
        print()
    
    if args.check_toc:
        print("📑 检查文档结构...")
        toc = check_toc_structure()
        print(f"  总数: {toc['total']}")
        print(f"  有标题: {toc['with_title']}")
        print(f"  有目录: {toc['with_toc']}")
        print()
    
    if args.check_code:
        print("💻 检查代码示例...")
        code = check_code_examples()
        print(f"  总代码块: {code['total_blocks']}")
        print(f"  光明代码: {code['light_blocks']}")
        print(f"  Python 代码: {code['python_blocks']}")
        print(f"  其他: {code['other_blocks']}")
        print()
    
    if args.gen_index:
        print("📖 生成文档索引...")
        report = generate_index_report()
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"  已保存到: {args.output}")
        else:
            print(report)
        print()
    
    print("=" * 60)
    print("✅ 文档检查完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
