"""
光明 API 参考文档自动生成器

功能：
  - 扫描 stdlib/ 目录下的 .light 文件，提取函数/类定义和注释
  - 扫描 src/ 目录下的 .py 文件，提取模块/类/函数文档
  - 生成 Markdown 格式的 API 参考文档
  - 输出到 docs/api/ 目录供 mkdocs 使用

用法：
  python playground/api_docs_generator.py
  python playground/api_docs_generator.py --output docs/api
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

        # 收集注释
        if stripped.startswith('#'):
            comment = stripped[1:].strip()
            if comment:
                current_comment.append(comment)
            continue

        # 匹配函数定义：段落/段/函数 名称
        func_match = re.match(r'(段落|段|函数)\s+(\S+)', stripped)
        if func_match:
            name = func_match.group(2)
            params = ''
            param_match = re.search(r'接收\s+(.+?)[：:]', stripped)
            if param_match:
                params = param_match.group(1)
            results.append({
                'type': 'function',
                'name': name,
                'params': params,
                'doc': '\n'.join(current_comment) if current_comment else '',
                'line': stripped[:80]
            })
            current_comment = []
            continue

        # 匹配类定义
        class_match = re.match(r'类\s+(\S+)', stripped)
        if class_match:
            results.append({
                'type': 'class',
                'name': class_match.group(1),
                'params': '',
                'doc': '\n'.join(current_comment) if current_comment else '',
                'line': stripped[:80]
            })
            current_comment = []
            continue

        # 非空行且非注释，重置当前注释
        if stripped:
            current_comment = []

    return results


def extract_py_api(filepath: str) -> list:
    """解析 .py 文件，提取模块/类/函数文档"""
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception:
        return results

    # 模块文档字符串
    module_doc = extract_py_docstring(source)
    if module_doc:
        results.append({
            'type': 'module',
            'name': os.path.basename(filepath),
            'doc': module_doc,
            'line': ''
        })

    lines = source.split('\n')
    i = 0
    current_comment = []

    while i < len(lines):
        stripped = lines[i].strip()

        # 收集注释
        if stripped.startswith('#'):
            comment = stripped[1:].strip()
            if comment:
                current_comment.append(comment)
            i += 1
            continue

        # 类定义
        class_match = re.match(r'class\s+(\w+)', stripped)
        if class_match:
            name = class_match.group(1)
            # 跳过类定义行，看下一行是否 docstring
            doc = ''
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                doc_match = re.match(r'"""(.*?)"""', next_line, re.DOTALL)
                if doc_match:
                    doc = doc_match.group(1).strip()
                elif next_line.startswith('"""') or next_line.startswith("'''"):
                    # 多行 docstring
                    end_char = '"""' if next_line.startswith('"""') else "'''"
                    doc_lines = [next_line[len(end_char):]]
                    j = i + 2
                    while j < len(lines):
                        if end_char in lines[j]:
                            doc_lines.append(lines[j][:lines[j].index(end_char)])
                            break
                        doc_lines.append(lines[j])
                        j += 1
                    doc = '\n'.join(doc_lines).strip()

            results.append({
                'type': 'class',
                'name': name,
                'doc': doc or '\n'.join(current_comment),
                'line': stripped[:80]
            })
            current_comment = []
            i += 1
            continue

        # 函数定义
        func_match = re.match(r'def\s+(\w+)\s*\(', stripped)
        if func_match and not stripped.startswith('def _'):
            name = func_match.group(1)
            # 提取参数
            params_match = re.search(r'\((.*?)\)', stripped)
            params = params_match.group(1) if params_match else ''

            doc = ''
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                doc_match = re.match(r'"""(.*?)"""', next_line, re.DOTALL)
                if doc_match:
                    doc = doc_match.group(1).strip()
                elif next_line.startswith('"""') or next_line.startswith("'''"):
                    end_char = '"""' if next_line.startswith('"""') else "'''"
                    doc_lines = [next_line[len(end_char):]]
                    j = i + 2
                    while j < len(lines):
                        if end_char in lines[j]:
                            doc_lines.append(lines[j][:lines[j].index(end_char)])
                            break
                        doc_lines.append(lines[j])
                        j += 1
                    doc = '\n'.join(doc_lines).strip()

            results.append({
                'type': 'function',
                'name': name,
                'params': params,
                'doc': doc or '\n'.join(current_comment),
                'line': stripped[:80]
            })
            current_comment = []
            i += 1
            continue

        if stripped:
            current_comment = []
        i += 1

    return results


def generate_markdown(output_dir: str):
    """生成 API 参考文档"""
    os.makedirs(output_dir, exist_ok=True)

    # 1. 扫描 stdlib/ 目录
    stdlib_docs = {}
    if os.path.isdir(_stdlib_dir):
        for fname in sorted(os.listdir(_stdlib_dir)):
            if fname.endswith('.light'):
                fpath = os.path.join(_stdlib_dir, fname)
                items = extract_light_docs(fpath)
                if items:
                    stdlib_docs[fname] = items

    # 2. 扫描 src/ 目录
    src_docs = {}
    if os.path.isdir(_src_dir):
        for fname in sorted(os.listdir(_src_dir)):
            if fname.endswith('.py') and not fname.startswith('_'):
                fpath = os.path.join(_src_dir, fname)
                items = extract_py_api(fpath)
                if items:
                    src_docs[fname] = items

    # 生成标准库 API 文档
    if stdlib_docs:
        content = ['# 标准库 API 参考', '', '> 自动生成 - 请勿手动编辑', '', '---', '']
        for fname, items in sorted(stdlib_docs.items()):
            mod_name = fname.replace('.light', '')
            content.append(f'## 模块: {mod_name}')
            content.append('')
            for item in items:
                if item['type'] == 'function':
                    params_str = f"({item['params']})" if item['params'] else '()'
                    content.append(f'### 函数 `{item["name"]}{params_str}`')
                    content.append('')
                    content.append(f'```light')
                    content.append(item['line'])
                    content.append('```')
                    content.append('')
                    if item['doc']:
                        content.append(item['doc'])
                        content.append('')
                elif item['type'] == 'class':
                    content.append(f'### 类 `{item["name"]}`')
                    content.append('')
                    if item['doc']:
                        content.append(item['doc'])
                        content.append('')
            content.append('---')
            content.append('')

        api_path = os.path.join(output_dir, 'stdlib.md')
        with open(api_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        print(f'  生成: {api_path}')

    # 生成编译器 API 文档
    if src_docs:
        content = ['# 编译器 API 参考', '', '> 自动生成 - 请勿手动编辑', '', '---', '']
        for fname, items in sorted(src_docs.items()):
            mod_name = fname.replace('.py', '')
            content.append(f'## 模块: {mod_name}')
            content.append('')
            for item in items:
                if item['type'] == 'module':
                    content.append(f'**模块说明**: {item["doc"]}')
                    content.append('')
                elif item['type'] == 'class':
                    content.append(f'### 类 `{item["name"]}`')
                    content.append('')
                    if item['doc']:
                        content.append(item['doc'])
                        content.append('')
                elif item['type'] == 'function':
                    content.append(f'### 函数 `{item["name"]}({item["params"]})`')
                    content.append('')
                    if item['doc']:
                        content.append(item['doc'])
                        content.append('')
            content.append('---')
            content.append('')

        api_path = os.path.join(output_dir, 'compiler.md')
        with open(api_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        print(f'  生成: {api_path}')

    # 生成索引页
    index_content = [
        '# API 参考文档',
        '',
        '> 自动生成 - 请勿手动编辑',
        '',
        '## 标准库 API',
        '',
        '- [标准库 API 参考](stdlib.md)',
        '',
        '## 编译器 API',
        '',
        '- [编译器 API 参考](compiler.md)',
        '',
        '---',
        '',
        f'*生成时间: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*',
    ]
    index_path = os.path.join(output_dir, 'index.md')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(index_content))
    print(f'  生成: {index_path}')

    return True


def main():
    parser = argparse.ArgumentParser(description='光明 API 参考文档自动生成器')
    parser.add_argument('--output', '-o', default=_default_output,
                        help=f'输出目录 (默认: {_default_output})')
    args = parser.parse_args()

    output_dir = args.output
    print(f'光明 API 参考文档自动生成器')
    print(f'=' * 50)
    print(f'标准库目录: {_stdlib_dir}')
    print(f'源码目录: {_src_dir}')
    print(f'输出目录: {output_dir}')
    print()

    success = generate_markdown(output_dir)

    if success:
        print(f'\n✅ API 参考文档已生成到: {output_dir}')
        print(f'   请在 mkdocs.yml 中添加以下导航项:')
        print(f'     - API 参考:')
        print(f'       - API 索引: api/index.md')
        print(f'       - 标准库 API: api/stdlib.md')
        print(f'       - 编译器 API: api/compiler.md')
    else:
        print(f'\n❌ 生成失败')
        sys.exit(1)


if __name__ == '__main__':
    main()