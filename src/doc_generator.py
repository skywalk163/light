# -*- coding: utf-8 -*-
"""
光明（Light）文档生成器 — R136 D线 T10

从 .light 源文件 AST 抽取段落 / 类 / 全局变量 / 导入导出清单，
渲染为 Markdown（默认）或 HTML。

由 cli/light.py 的 `light doc` 子命令通过
`_导入能力('doc_generator', 'doc', 'run_doc')` 延迟加载。

R136 改造：原实现用正则 `函数 X 接收 Y：` 匹配，对 lightharness
实际语法 `《段名》段(参数):` 抽不到任何符号。现改用 light_parser_v3
AST 抽取，覆盖 Paragraph / ClassDefinition / VarDecl / ImportStmt / ExportStmt。

用法：
  light doc file.light           # Markdown 文档
  light doc file.light --html    # HTML
  light doc dir/ -o out/          # 批量
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from light_parser_v3 import LightParser, ParseError  # noqa: E402
from ast_nodes_v3 import (  # noqa: E402
    Module, Paragraph, ClassDefinition, VarDecl,
    ImportStmt, ExportStmt, MethodDefinition, AttributeDeclaration,
)


# ─────────────────────────────────────────────────────────────────────
# AST 抽取
# ─────────────────────────────────────────────────────────────────────

def _fmt_param(p: Dict[str, Any]) -> str:
    """Paragraph.params 的 dict 渲染成 `名字: 型 = 默认`。"""
    name = p.get('name', '?')
    type_ann = p.get('type')
    default = p.get('default', None)
    s = str(name)
    if type_ann:
        s += f': {type_ann}'
    if default is not None:
        s += f' = {default}'
    return s


def _extract(module: Module, source_path: str) -> Dict[str, Any]:
    paragraphs: List[Dict[str, Any]] = []
    classes: List[Dict[str, Any]] = []
    globals_: List[Dict[str, Any]] = []
    imports_: List[Dict[str, Any]] = []
    exports: List[str] = []

    for stmt in module.statements:
        if isinstance(stmt, Paragraph):
            paragraphs.append({
                'name': stmt.name,
                'params': [_fmt_param(p) for p in (stmt.params or [])],
                'return_type': stmt.return_type,
                'line': getattr(stmt, 'line', 0),
            })
        elif isinstance(stmt, ClassDefinition):
            methods = []
            for m in (stmt.methods or []):
                if not isinstance(m, MethodDefinition):
                    continue
                params = []
                for prm in (m.parameters or []):
                    if hasattr(prm, 'name'):
                        s = str(prm.name)
                        if getattr(prm, 'type_annotation', None):
                            s += f': {prm.type_annotation}'
                        params.append(s)
                    else:
                        params.append(str(prm))
                methods.append({
                    'name': m.name,
                    'params': params,
                    'return_type': m.return_type,
                    'is_constructor': bool(getattr(m, 'is_constructor', False)),
                    'access': getattr(m, 'access_modifier', 'public'),
                })
            attrs = []
            for a in (stmt.attributes or []):
                if isinstance(a, AttributeDeclaration):
                    attrs.append({
                        'name': a.name,
                        'type': a.type_annotation,
                        'access': a.access_modifier,
                    })
            classes.append({
                'name': stmt.name,
                'base_classes': stmt.base_classes or [],
                'attributes': attrs,
                'methods': methods,
                'line': getattr(stmt, 'line', 0),
            })
        elif isinstance(stmt, VarDecl):
            globals_.append({
                'name': stmt.name,
                'type': stmt.type_annotation,
                'line': getattr(stmt, 'line', 0),
            })
        elif isinstance(stmt, ImportStmt):
            imports_.append({
                'module': stmt.module_name,
                'symbols': stmt.symbols or [],
                'alias': stmt.alias,
                'language': stmt.language,
            })
        elif isinstance(stmt, ExportStmt):
            exports.extend(stmt.symbols or [])

    return {
        'source_path': source_path,
        'paragraphs': paragraphs,
        'classes': classes,
        'globals': globals_,
        'imports': imports_,
        'exports': exports,
        'stats': {
            'paragraph_count': len(paragraphs),
            'class_count': len(classes),
            'global_count': len(globals_),
            'import_count': len(imports_),
            'export_count': len(exports),
        },
    }


# ─────────────────────────────────────────────────────────────────────
# Markdown 渲染
# ─────────────────────────────────────────────────────────────────────

def _render_markdown(info: Dict[str, Any]) -> str:
    name = os.path.basename(info['source_path'])
    L: List[str] = []
    L.append(f'# API 文档：{name}')
    L.append('')
    L.append(f'> 由 `light doc` 自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    L.append(f'> 源文件：`{info["source_path"]}`')
    L.append('')

    s = info['stats']
    L.append('## 概览')
    L.append('')
    L.append(f'- 段落（函数）：**{s["paragraph_count"]}**')
    L.append(f'- 类：**{s["class_count"]}**')
    L.append(f'- 全局变量：**{s["global_count"]}**')
    L.append(f'- 导入：**{s["import_count"]}**')
    L.append(f'- 导出符号：**{s["export_count"]}**')
    L.append('')

    if info['imports']:
        L.append('## 导入')
        L.append('')
        for imp in info['imports']:
            lang = f' [{imp["language"]}]' if imp['language'] else ''
            syms = f'（符号: {", ".join(imp["symbols"])}）' if imp['symbols'] else ''
            alias = f' as {imp["alias"]}' if imp['alias'] else ''
            L.append(f'- `{imp["module"]}`{lang}{syms}{alias}')
        L.append('')

    if info['paragraphs']:
        L.append('## 段落（函数）')
        L.append('')
        for p in info['paragraphs']:
            sig = f'{p["name"]}({", ".join(p["params"])})'
            if p['return_type']:
                sig += f' -> {p["return_type"]}'
            L.append(f'### {p["name"]}')
            L.append('')
            L.append('```text')
            L.append(sig)
            L.append('```')
            L.append('')

    if info['classes']:
        L.append('## 类')
        L.append('')
        for c in info['classes']:
            head = f'### 类 `{c["name"]}`'
            if c['base_classes']:
                head += f'（继承：{", ".join(c["base_classes"])}）'
            L.append(head)
            L.append('')
            if c['attributes']:
                L.append('字段：')
                L.append('')
                for a in c['attributes']:
                    t = f': {a["type"]}' if a['type'] else ''
                    L.append(f'- `{a["name"]}`{t}  _{a["access"]}_')
                L.append('')
            if c['methods']:
                L.append('方法：')
                L.append('')
                for m in c['methods']:
                    tag = '构造' if m['is_constructor'] else m['access']
                    ret = f' -> {m["return_type"]}' if m['return_type'] else ''
                    L.append(f'- `{m["name"]}({", ".join(m["params"])})`{ret}  _{tag}_')
                L.append('')

    if info['globals']:
        L.append('## 全局变量')
        L.append('')
        for g in info['globals']:
            t = f': {g["type"]}' if g['type'] else ''
            L.append(f'- `{g["name"]}`{t}')
        L.append('')

    if info['exports']:
        L.append('## 导出符号')
        L.append('')
        for sym in info['exports']:
            L.append(f'- `{sym}`')
        L.append('')

    return '\n'.join(L)


# ─────────────────────────────────────────────────────────────────────
# HTML 渲染
# ─────────────────────────────────────────────────────────────────────

def _esc(s: Any) -> str:
    import html as _html
    return _html.escape(str(s), quote=True)


def _render_html(info: Dict[str, Any]) -> str:
    name = _esc(os.path.basename(info['source_path']))
    P: List[str] = []
    P.append('<!DOCTYPE html>')
    P.append('<html lang="zh-CN"><head><meta charset="utf-8">')
    P.append(f'<title>API 文档：{name}</title>')
    P.append('<style>body{font-family:sans-serif;max-width:960px;margin:2em auto;padding:0 1em;}'
             'code{background:#f4f4f4;padding:2px 4px;}'
             'pre{background:#f4f4f4;padding:1em;overflow:auto;}'
             'h1{border-bottom:2px solid #ccc;}h2{margin-top:2em;border-bottom:1px solid #ddd;}</style>')
    P.append('</head><body>')
    P.append(f'<h1>API 文档：{name}</h1>')
    s = info['stats']
    P.append('<h2>概览</h2><ul>')
    P.append(f'<li>段落：<b>{s["paragraph_count"]}</b></li>')
    P.append(f'<li>类：<b>{s["class_count"]}</b></li>')
    P.append(f'<li>全局变量：<b>{s["global_count"]}</b></li>')
    P.append(f'<li>导出符号：<b>{s["export_count"]}</b></li>')
    P.append('</ul>')

    if info['paragraphs']:
        P.append('<h2>段落</h2>')
        for p in info['paragraphs']:
            sig = f'{p["name"]}({", ".join(p["params"])})'
            if p['return_type']:
                sig += f' -> {p["return_type"]}'
            P.append(f'<h3>{_esc(p["name"])}</h3><pre>{_esc(sig)}</pre>')

    if info['classes']:
        P.append('<h2>类</h2>')
        for c in info['classes']:
            P.append(f'<h3>类 {_esc(c["name"])}</h3><ul>')
            for m in c['methods']:
                P.append(f'<li><code>{_esc(m["name"])}({_esc(", ".join(m["params"]))})</code></li>')
            P.append('</ul>')

    P.append('</body></html>')
    return '\n'.join(P)


# ─────────────────────────────────────────────────────────────────────
# 兼容外壳（保留 R136 前的 DocGenerator / run_doc 签名）
# ─────────────────────────────────────────────────────────────────────

class DocGenerator:
    """文档生成器（AST 后端）。"""

    def generate_markdown(self, filepath: str) -> str:
        with open(filepath, 'r', encoding='utf-8') as f:
            src = f.read()
        module = LightParser().parse(src)
        return _render_markdown(_extract(module, filepath))

    def generate_html(self, filepath: str) -> str:
        with open(filepath, 'r', encoding='utf-8') as f:
            src = f.read()
        module = LightParser().parse(src)
        return _render_html(_extract(module, filepath))

    def generate_project_docs(self, directory: str, format: str = 'markdown') -> dict:
        docs = {}
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for f in files:
                if f.endswith('.light'):
                    fpath = os.path.join(root, f)
                    rel = os.path.relpath(fpath, directory)
                    try:
                        docs[rel] = (self.generate_html(fpath) if format == 'html'
                                     else self.generate_markdown(fpath))
                    except Exception as e:  # noqa: BLE001
                        docs[rel] = f'# 解析失败\n\n`{e}`'
        return docs


def run_doc(target: str, output_format: str = 'markdown', output_file: Optional[str] = None):
    """`light doc` 主入口（与 cli/light.py:1441 调用签名对齐）。"""
    if not os.path.exists(target):
        print(f'⚠️  路径不存在：{target}', file=sys.stderr)
        sys.exit(2)

    gen = DocGenerator()

    if os.path.isfile(target):
        try:
            content = (gen.generate_html(target) if output_format == 'html'
                        else gen.generate_markdown(target))
        except ParseError as e:
            print(f'⚠️  解析失败 {target}: {e}', file=sys.stderr)
            sys.exit(1)
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'✓ 文档已生成: {output_file}')
        else:
            print(content)
        return

    if os.path.isdir(target):
        docs = gen.generate_project_docs(target, output_format)
        if output_file:
            os.makedirs(output_file, exist_ok=True)
            for rel_path, content in docs.items():
                out_path = os.path.join(output_file, rel_path.replace('.light', '.' + output_format))
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            # 索引
            idx = ['# 项目文档', '', '## 文件列表', '']
            for rel in sorted(docs.keys()):
                link = rel.replace('.light', '.' + output_format)
                idx.append(f'- [{rel}]({link})')
            with open(os.path.join(output_file, 'index.md'), 'w', encoding='utf-8') as f:
                f.write('\n'.join(idx))
            print(f'✓ 批量文档已生成: {output_file}')
        else:
            for rel, content in docs.items():
                print('=' * 60)
                print(f'文件: {rel}')
                print('=' * 60)
                print(content)
        return

    print(f'错误: 路径不存在: {target}', file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='光明文档生成器')
    ap.add_argument('target')
    ap.add_argument('--html', action='store_true')
    ap.add_argument('-o', '--output')
    a = ap.parse_args()
    run_doc(a.target, output_format='html' if a.html else 'markdown', output_file=a.output)
