# -*- coding: utf-8 -*-
"""
光明（Light）WebAssembly 编译目标 v4.1

将光明代码编译为可在浏览器中通过 Pyodide（Python → WebAssembly）执行的格式。
支持两种模式：
  1. Pyodide 模式：编译为 Python 代码，在浏览器 Pyodide 运行时中执行
  2. 独立模式：生成包含 Python 代码和 Pyodide 引导的独立 HTML 页面

用法：
  from wasm_target import compile_to_wasm
  result = compile_to_wasm(source, mode='pyodide')
  # 或生成独立 HTML
  html = compile_to_wasm(source, mode='standalone')
"""

import os
import sys
import json
import base64
from pathlib import Path
from typing import Dict, Optional, Tuple

# 确保能导入项目模块
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_dir = os.path.dirname(_script_dir)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)


# =============================================================================
# Pyodide 引导代码
# =============================================================================

PYODIDE_LOADER_JS = """
// Pyodide 加载器 - 在浏览器中运行光明代码
let pyodideReady = null;

async function loadPyodide() {
    if (pyodideReady) return pyodideReady;
    
    pyodideReady = (async () => {
        if (typeof loadPyodide === 'undefined') {
            // 动态加载 Pyodide
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js';
            document.head.appendChild(script);
            await new Promise((resolve, reject) => {
                script.onload = resolve;
                script.onerror = reject;
            });
        }
        const pyodide = await loadPyodide({
            indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/'
        });
        return pyodide;
    })();
    
    return pyodideReady;
}

async function runLightWasm(pythonCode) {
    const pyodide = await loadPyodide();
    
    // 捕获输出
    let output = '';
    pyodide.setStdout({
        batched: (text) => { output += text + '\\n'; }
    });
    pyodide.setStderr({
        batched: (text) => { output += '[ERR] ' + text + '\\n'; }
    });
    
    try {
        await pyodide.runPythonAsync(pythonCode);
        return { success: true, output: output.trim() };
    } catch (e) {
        return { success: false, error: e.message, output: output.trim() };
    }
}
"""

# =============================================================================
# 独立 HTML 模板
# =============================================================================

STANDALONE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>光明 (Light) WebAssembly 应用</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: #0d1117;
            color: #e6edf3;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 800px;
            width: 100%;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            overflow: hidden;
        }}
        .header {{
            background: #21262d;
            padding: 16px 24px;
            border-bottom: 1px solid #30363d;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .header h1 {{
            font-size: 18px;
            font-weight: 600;
            color: #3fb950;
        }}
        .header .badge {{
            font-size: 11px;
            padding: 2px 8px;
            background: #3fb95022;
            color: #3fb950;
            border: 1px solid #3fb95044;
            border-radius: 4px;
        }}
        .source {{
            padding: 16px 24px;
            border-bottom: 1px solid #30363d;
        }}
        .source h2 {{
            font-size: 14px;
            color: #8b949e;
            margin-bottom: 8px;
        }}
        .source pre {{
            font-family: 'Cascadia Code', 'Fira Code', Consolas, 'Microsoft YaHei', monospace;
            font-size: 13px;
            color: #58a6ff;
            background: #0d1117;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        .output {{
            padding: 16px 24px;
            min-height: 100px;
        }}
        .output h2 {{
            font-size: 14px;
            color: #8b949e;
            margin-bottom: 8px;
        }}
        .output-content {{
            font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace;
            font-size: 13px;
            background: #0d1117;
            padding: 12px;
            border-radius: 6px;
            min-height: 40px;
            white-space: pre-wrap;
            color: #e6edf3;
        }}
        .output-content.error {{
            color: #f85149;
        }}
        .output-content.loading {{
            color: #d29922;
        }}
        .controls {{
            padding: 12px 24px;
            border-top: 1px solid #30363d;
            display: flex;
            gap: 10px;
        }}
        button {{
            padding: 8px 16px;
            border: 1px solid #30363d;
            border-radius: 6px;
            background: #21262d;
            color: #e6edf3;
            cursor: pointer;
            font-size: 13px;
            font-family: inherit;
            transition: all 0.15s;
        }}
        button:hover {{
            background: #30363d;
        }}
        button.primary {{
            background: #238636;
            border-color: #238636;
            color: #fff;
        }}
        button.primary:hover {{
            background: #2ea043;
        }}
        .footer {{
            text-align: center;
            padding: 16px;
            color: #484f58;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>光明</h1>
            <span class="badge">WebAssembly</span>
            <span style="font-size:12px;color:#8b949e;margin-left:auto">{title}</span>
        </div>
        <div class="source">
            <h2>光明源代码</h2>
            <pre>{source_escaped}</pre>
        </div>
        <div class="output">
            <h2>运行结果</h2>
            <div class="output-content loading" id="output">⏳ 正在加载 Pyodide 运行时...</div>
        </div>
        <div class="controls">
            <button class="primary" onclick="run()">▶ 运行</button>
            <button onclick="location.reload()">↺ 重置</button>
        </div>
    </div>
    <div class="footer">
        由光明 v4.1 编译器生成 · 基于 Pyodide (Python → WebAssembly)
    </div>

    <script src="https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js"></script>
    <script>
        let pyodide = null;
        let isReady = false;

        async function init() {{
            document.getElementById('output').textContent = '⏳ 正在加载 Pyodide 运行时（约 10MB，首次较慢）...';
            try {{
                pyodide = await loadPyodide({{
                    indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/'
                }});
                isReady = true;
                document.getElementById('output').textContent = '✅ Pyodide 已就绪，点击「运行」执行代码';
                document.getElementById('output').classList.remove('loading');
            }} catch (e) {{
                document.getElementById('output').textContent = '❌ Pyodide 加载失败: ' + e.message;
                document.getElementById('output').classList.add('error');
            }}
        }}

        async function run() {{
            if (!isReady) {{
                document.getElementById('output').textContent = '⏳ Pyodide 尚未加载完成，请稍候...';
                return;
            }}

            const outputEl = document.getElementById('output');
            outputEl.textContent = '⏳ 正在执行...';
            outputEl.classList.remove('error');

            let output = '';
            pyodide.setStdout({{
                batched: (text) => {{ output += text + '\\n'; }}
            }});
            pyodide.setStderr({{
                batched: (text) => {{ output += '[ERR] ' + text + '\\n'; }}
            }});

            try {{
                await pyodide.runPythonAsync(`{python_code_escaped}`);
                outputEl.textContent = output.trim() || '(无输出)';
            }} catch (e) {{
                outputEl.textContent = output.trim() + '\\n\\n❌ 错误: ' + e.message;
                outputEl.classList.add('error');
            }}
        }}

        init();
    </script>
</body>
</html>
"""


# =============================================================================
# 编译函数
# =============================================================================

def compile_light_to_python(source: str) -> Tuple[str, Optional[str]]:
    """将光明代码编译为 Python 代码"""
    try:
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator

        parser = LightParser()
        module = parser.parse(source)

        generator = PythonCodeGenerator()
        py_code = generator.generate(module)

        return py_code, None
    except Exception as e:
        return "", str(e)


def compile_to_pyodide(source: str) -> Dict:
    """
    编译光明代码为 Pyodide 可执行格式

    Returns:
        {
            'python_code': str,      # 编译后的 Python 代码
            'loader_js': str,         # Pyodide 加载器 JS 代码
            'error': str or None,     # 编译错误
        }
    """
    py_code, error = compile_light_to_python(source)
    if error:
        return {
            'python_code': '',
            'loader_js': PYODIDE_LOADER_JS,
            'error': error,
        }
    return {
        'python_code': py_code,
        'loader_js': PYODIDE_LOADER_JS,
        'error': None,
    }


def compile_to_standalone_html(source: str, title: str = "光明程序") -> str:
    """
    编译光明代码为独立 HTML 页面（内嵌 Pyodide 运行时）

    Args:
        source: 光明源代码
        title: 页面标题

    Returns:
        完整的 HTML 字符串
    """
    py_code, error = compile_light_to_python(source)
    if error:
        py_code = f"# 编译错误: {error}"

    # 转义特殊字符以嵌入 HTML/JS
    source_escaped = _escape_html(source.strip())
    python_code_escaped = _escape_js_string(py_code.strip())

    return STANDALONE_HTML_TEMPLATE.format(
        title=title,
        source_escaped=source_escaped,
        python_code_escaped=python_code_escaped,
    )


def compile_to_wasm_json(source: str) -> str:
    """
    编译为 JSON 格式的 WASM 包（包含 Python 代码和元数据）

    Returns:
        JSON 字符串
    """
    result = compile_to_pyodide(source)
    return json.dumps(result, ensure_ascii=False, indent=2)


def _escape_html(text: str) -> str:
    """转义 HTML 特殊字符"""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def _escape_js_string(text: str) -> str:
    """转义 JS 字符串中的特殊字符"""
    return (text
            .replace('\\', '\\\\')
            .replace('`', '\\`')
            .replace('$', '\\$')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t'))


# =============================================================================
# Pyodide 标准库预加载
# =============================================================================

PYODIDE_PACKAGES = [
    'numpy',
    'pandas',
    'matplotlib',
    'Pillow',
    'requests',
    'regex',
    'sqlite3',
]

PYODIDE_PRELOAD_JS = f"""
// 预加载 Pyodide 科学计算包
async function loadPyodideWithPackages() {{
    const pyodide = await loadPyodide({{
        indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/'
    }});
    // 预加载常用包
    await pyodide.loadPackage([{', '.join(f"'{p}'" for p in PYODIDE_PACKAGES)}]);
    return pyodide;
}}
"""


# =============================================================================
# 浏览器端光明运行时
# =============================================================================

LIGHT_WASM_RUNTIME_JS = """
/**
 * 光明 (Light) WebAssembly 浏览器运行时 v4.1
 *
 * 在浏览器中通过 Pyodide 运行光明代码，无需服务器。
 * 用法：
 *   const light = new LightWasmRuntime();
 *   await light.init();
 *   const result = await light.run(source);
 */

class LightWasmRuntime {
    constructor(options = {}) {
        this.pyodide = null;
        this.ready = false;
        this.options = {
            pyodideUrl: 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js',
            pyodideIndex: 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/',
            preloadPackages: [],
            ...options
        };
    }

    async init() {
        if (this.ready) return;

        // 加载 Pyodide
        if (typeof loadPyodide === 'undefined') {
            await this._loadScript(this.options.pyodideUrl);
        }

        this.pyodide = await loadPyodide({
            indexURL: this.options.pyodideIndex
        });

        // 预加载包
        if (this.options.preloadPackages.length > 0) {
            await this.pyodide.loadPackage(this.options.preloadPackages);
        }

        this.ready = true;
    }

    async run(source, options = {}) {
        if (!this.ready) {
            await this.init();
        }

        // 编译光明代码为 Python
        const resp = await fetch('/api/demos/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source: source,
                target: 'python',
                wasm: true
            })
        });
        const data = await resp.json();

        if (data.error) {
            return { success: false, error: data.error, output: '' };
        }

        const pythonCode = data.python || data.output || '';

        // 在 Pyodide 中执行
        let output = '';
        this.pyodide.setStdout({
            batched: (text) => { output += text + '\\n'; }
        });
        this.pyodide.setStderr({
            batched: (text) => { output += '[ERR] ' + text + '\\n'; }
        });

        try {
            await this.pyodide.runPythonAsync(pythonCode);
            return { success: true, output: output.trim(), python: pythonCode };
        } catch (e) {
            return { success: false, error: e.message, output: output.trim(), python: pythonCode };
        }
    }

    async _loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`Failed to load: ${src}`));
            document.head.appendChild(script);
        });
    }

    destroy() {
        this.pyodide = null;
        this.ready = false;
    }
}
"""


# =============================================================================
# CLI 入口
# =============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='光明 WebAssembly 编译器')
    parser.add_argument('source', nargs='?', help='源文件 (.light)')
    parser.add_argument('--mode', choices=['pyodide', 'standalone', 'json'],
                       default='standalone', help='输出模式')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--title', default='光明程序', help='HTML 页面标题')

    args = parser.parse_args()

    if args.source:
        with open(args.source, 'r', encoding='utf-8') as f:
            source = f.read()
    else:
        source = sys.stdin.read()

    if args.mode == 'standalone':
        html = compile_to_standalone_html(source, title=args.title)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"已生成独立 HTML: {args.output}")
        else:
            print(html)

    elif args.mode == 'pyodide':
        result = compile_to_pyodide(source)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"已生成 Pyodide 包: {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.mode == 'json':
        result = compile_to_wasm_json(source)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"已生成 JSON 包: {args.output}")
        else:
            print(result)