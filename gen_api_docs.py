"""
光明 API 参考文档自动生成脚本

从源码中提取 API 文档，生成 Markdown 格式的 API 参考文档。
输出到 docs/api/ 目录供 mkdocs 使用。

用法：
  python docs/gen_api_docs.py
  python docs/gen_api_docs.py --output docs/api
"""

import os
import sys
import re
import argparse
from pathlib import Path


_project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_stdlib_dir = os.path.join(_project_dir, 'stdlib')
_src_dir = os.path.join(_project_dir, 'src')
_default_output = os.path.join(_project_dir, 'docs', 'api')


def extract_py_docstring(source: str) -> str:
    """提取 Python 文件的文档字符串"""
    match = re.match(r'^"""(.+?)"""', source, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.match(r"^'''(.+?)'''", source, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ''


def extract_light_docs(filepath: str) -> list:
    """解析 .light 文件，提取函数/类定义和注释"""
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return results

    current_comment = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            current_comment.append(stripped.lstrip('#/ '))
        elif '段落' in stripped or '段 ' in stripped or '类 ' in stripped or 'class ' in stripped:
            entry = {
                'line': stripped,
                'comment': ' '.join(current_comment) if current_comment else '',
                'line_num': lines.index(line) + 1
            }
            results.append(entry)
            current_comment = []
        else:
            current_comment = []
    return results


def gen_stdlib_api_docs() -> str:
    """生成标准库 API 文档"""
    lines = [
        '# 标准库 API 参考\n',
        '> 自动生成 - 请勿手动编辑\n',
        '---\n',
    ]

    if not os.path.isdir(_stdlib_dir):
        lines.append('\n标准库目录不存在。\n')
        return '\n'.join(lines)

    for fname in sorted(os.listdir(_stdlib_dir)):
        if not fname.endswith('.light'):
            continue
        fpath = os.path.join(_stdlib_dir, fname)
        mod_name = fname.replace('.light', '')
        lines.append(f'\n## 模块: {mod_name}\n')

        doc = extract_light_docs(fpath)
        if doc:
            for entry in doc:
                lines.append(f'### {entry["line"]}\n')
                if entry['comment']:
                    lines.append(f'\n{entry["comment"]}\n')
                lines.append(f'\n```light\n{entry["line"]}\n```\n')
        else:
            lines.append('\n（该模块包含实用函数和工具）\n')

    return '\n'.join(lines)


def gen_compiler_api_docs() -> str:
    """生成编译器 API 文档（从 src/ 提取）"""
    lines = [
        '# 编译器 API 参考\n',
        '> 自动生成 - 请勿手动编辑\n',
        '---\n',
    ]

    if not os.path.isdir(_src_dir):
        lines.append('\n编译器源码目录不存在。\n')
        return '\n'.join(lines)

    for fname in sorted(os.listdir(_src_dir)):
        if not fname.endswith('.py') or fname.startswith('_'):
            continue
        fpath = os.path.join(_src_dir, fname)
        mod_name = fname.replace('.py', '')

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue

        docstring = extract_py_docstring(content)
        lines.append(f'\n## 模块: {mod_name}\n')
        if docstring:
            lines.append(f'\n**模块说明**: {docstring}\n')

        # 提取类定义
        class_pattern = re.compile(r'^class\s+(\w+)(?:\(.*?\))?:', re.MULTILINE)
        for match in class_pattern.finditer(content):
            class_name = match.group(1)
            lines.append(f'\n### 类 `{class_name}`\n')

        # 提取函数定义
        func_pattern = re.compile(r'^def\s+(\w+)\s*\(', re.MULTILINE)
        for match in func_pattern.finditer(content):
            func_name = match.group(1)
            if func_name.startswith('_'):
                continue
            lines.append(f'\n### 函数 `{func_name}`\n')

    return '\n'.join(lines)


def gen_api_index() -> str:
    """生成 API 索引页面"""
    return f"""# API 参考文档

> 自动生成 - 请勿手动编辑

## 标准库 API

- [标准库 API 参考](stdlib.md)

## 编译器 API

- [编译器 API 参考](compiler.md)

---

*生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""


def main():
    parser = argparse.ArgumentParser(description='光明 API 文档生成器')
    parser.add_argument('--output', '-o', default=_default_output,
                        help=f'输出目录（默认: {_default_output}）')
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成标准库 API
    stdlib_content = gen_stdlib_api_docs()
    stdlib_path = output_dir / 'stdlib.md'
    stdlib_path.write_text(stdlib_content, encoding='utf-8')
    print(f'[✓] 标准库 API 文档 -> {stdlib_path}')

    # 生成编译器 API
    compiler_content = gen_compiler_api_docs()
    compiler_path = output_dir / 'compiler.md'
    compiler_path.write_text(compiler_content, encoding='utf-8')
    print(f'[✓] 编译器 API 文档 -> {compiler_path}')

    # 生成索引
    index_path = output_dir / 'index.md'
    index_path.write_text(gen_api_index(), encoding='utf-8')
    print(f'[✓] API 索引 -> {index_path}')

    print(f'\nAPI 文档生成完成！输出目录: {output_dir}')


if __name__ == '__main__':
    main()