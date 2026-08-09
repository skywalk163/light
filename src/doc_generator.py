# -*- coding: utf-8 -*-
"""
光明（Light）文档生成器

功能：
  - 解析光明代码中的 # 注释
  - 提取段落（函数）文档
  - 生成 Markdown 和 HTML 格式文档

用法：
  light doc file.light           # 生成 Markdown 文档
  light doc file.light --html    # 生成 HTML 文档
  light doc .                   # 生成整个项目的文档
"""

import os
import sys
import re
from pathlib import Path


class DocParser:
    """文档解析器"""

    def __init__(self):
        self.paragraphs = []
        self.current_doc = []

    def parse_file(self, filepath: str) -> list:
        """解析单个文件"""
        self.paragraphs = []
        self.current_doc = []

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 处理注释行
            if stripped.startswith('#'):
                # 去除 # 和空格，但保留段落内的缩进
                comment = stripped[1:].strip() if len(stripped) > 1 else ''
                if comment:
                    self.current_doc.append(comment)
                continue

            # 处理段落定义（支持 '函数' 和 '段落' 两种关键字）
            if stripped.startswith('函数') or stripped.startswith('段落'):
                self._parse_paragraph(stripped, i + 1)
                continue

            # 处理类定义
            if stripped.startswith('类'):
                self._parse_class(stripped, i + 1)
                continue

            # 如果有文档但不是注释或段落，重置文档
            if self.current_doc and stripped:
                self.current_doc = []

        return self.paragraphs

    def _parse_paragraph(self, line: str, line_num: int):
        """解析段落定义"""
        # 格式：函数/段落 名称 接收 参数：
        # 或：函数/段落 名称：
        match = re.match(r'(?:函数|段落)\s+(\S+)(?:\s+接收\s+(.+?))?(?:：|:)', line)
        if match:
            name = match.group(1)
            params = match.group(2).strip() if match.group(2) else ''
            doc_text = '\n'.join(self.current_doc) if self.current_doc else ''

            self.paragraphs.append({
                'type': 'paragraph',
                'name': name,
                'params': params,
                'doc': doc_text,
                'line': line_num
            })

        self.current_doc = []

    def _parse_class(self, line: str, line_num: int):
        """解析类定义"""
        match = re.match(r'类\s+(\S+)', line)
        if match:
            name = match.group(1)
            doc_text = '\n'.join(self.current_doc) if self.current_doc else ''

            self.paragraphs.append({
                'type': 'class',
                'name': name,
                'params': '',
                'doc': doc_text,
                'line': line_num
            })

        self.current_doc = []


class DocGenerator:
    """文档生成器"""

    def __init__(self):
        self.parser = DocParser()

    def generate_markdown(self, filepath: str) -> str:
        """生成 Markdown 文档"""
        paragraphs = self.parser.parse_file(filepath)

        if not paragraphs:
            return "# 文档\n\n暂无文档"

        filename = os.path.basename(filepath)
        lines = [f"# {filename}", ""]

        for p in paragraphs:
            if p['type'] == 'class':
                lines.append(f"## 类 `{p['name']}`")
            else:
                params = f"({p['params']})" if p['params'] else "()"
                lines.append(f"## 段落 `{p['name']}{params}`")

            lines.append(f"**位置**: 第 {p['line']} 行")
            lines.append("")

            if p['doc']:
                lines.append(p['doc'])
                lines.append("")

            lines.append("---")
            lines.append("")

        return '\n'.join(lines)

    def generate_html(self, filepath: str) -> str:
        """生成 HTML 文档"""
        paragraphs = self.parser.parse_file(filepath)

        filename = os.path.basename(filepath)
        lines = [
            '<!DOCTYPE html>',
            '<html lang="zh-CN">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '    <title>光明文档 - ' + filename + '</title>',
            '    <style>',
            '        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 20px; background: #f8fafc; color: #1e293b; }',
            '        h1 { color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }',
            '        h2 { color: #1e293b; margin-top: 30px; }',
            '        .doc { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }',
            '        .meta { font-size: 14px; color: #64748b; margin-bottom: 10px; }',
            '        .doc-text { white-space: pre-wrap; line-height: 1.6; }',
            '        code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: "Fira Code", monospace; }',
            '    </style>',
            '</head>',
            '<body>',
            f'    <h1>{filename}</h1>',
            ''
        ]

        for p in paragraphs:
            if p['type'] == 'class':
                lines.append(f'    <div class="doc">')
                lines.append(f'        <h2>类 <code>{p["name"]}</code></h2>')
                lines.append(f'        <div class="meta">位置: 第 {p["line"]} 行</div>')
                if p['doc']:
                    lines.append(f'        <div class="doc-text">{p["doc"]}</div>')
                lines.append(f'    </div>')
            else:
                params = f"({p['params']})" if p['params'] else "()"
                lines.append(f'    <div class="doc">')
                lines.append(f'        <h2>段落 <code>{p["name"]}{params}</code></h2>')
                lines.append(f'        <div class="meta">位置: 第 {p["line"]} 行</div>')
                if p['doc']:
                    lines.append(f'        <div class="doc-text">{p["doc"]}</div>')
                lines.append(f'    </div>')

        lines.extend([
            '</body>',
            '</html>'
        ])

        return '\n'.join(lines)

    def generate_project_docs(self, directory: str, format: str = 'markdown') -> dict:
        """生成项目文档"""
        docs = {}
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for f in files:
                if f.endswith('.light'):
                    fpath = os.path.join(root, f)
                    rel_path = os.path.relpath(fpath, directory)
                    if format == 'html':
                        docs[rel_path] = self.generate_html(fpath)
                    else:
                        docs[rel_path] = self.generate_markdown(fpath)
        return docs


def run_doc(target: str, output_format: str = 'markdown', output_file: str = None):
    """运行文档生成器"""
    generator = DocGenerator()

    if os.path.isfile(target):
        if output_format == 'html':
            content = generator.generate_html(target)
            ext = '.html'
        else:
            content = generator.generate_markdown(target)
            ext = '.md'

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"文档已生成: {output_file}")
        else:
            print(content)

    elif os.path.isdir(target):
        docs = generator.generate_project_docs(target, output_format)

        if output_file:
            # 输出目录
            output_dir = output_file
            os.makedirs(output_dir, exist_ok=True)

            for rel_path, content in docs.items():
                out_path = os.path.join(output_dir, rel_path)
                out_path = out_path.replace('.light', '.' + output_format)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"文档已生成: {out_path}")

            # 创建索引页
            index_lines = ["# 项目文档", "", "## 文件列表", ""]
            for rel_path in sorted(docs.keys()):
                link = rel_path.replace('.light', '.' + output_format)
                index_lines.append(f"- [{rel_path}]({link})")

            with open(os.path.join(output_dir, 'index.md'), 'w', encoding='utf-8') as f:
                f.write('\n'.join(index_lines))
            print(f"索引页已生成: {output_dir}/index.md")

        else:
            for rel_path, content in docs.items():
                print(f"{'='*60}")
                print(f"文件: {rel_path}")
                print(f"{'='*60}")
                print(content)
                print()

    else:
        print(f"错误: 路径不存在: {target}", file=sys.stderr)
        sys.exit(1)