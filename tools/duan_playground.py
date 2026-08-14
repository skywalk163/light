#!/usr/bin/env python3
"""
段言多文件 Playground - Web 编辑器

提供基于浏览器的段言编辑环境，支持多文件编辑、编译运行、错误提示。

用法:
    python tools/duan_playground.py [--port 8080] [--host 127.0.0.1]
"""

import sys
import os
import json
import io
import contextlib
import traceback
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# 项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 添加 src 和 stdlib 到路径
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))
sys.path.insert(0, str(_PROJECT_ROOT / 'stdlib'))

# 尝试导入编译器组件
COMPILER_AVAILABLE = False
try:
    from lexer import Lexer, LexerError
    from duan_parser_v3 import DuanParser, ParseError
    from code_generator import PythonCodeGenerator
    from tokens import Token, TokenType
    COMPILER_AVAILABLE = True
except ImportError as e:
    _import_error = str(e)

# 标准库路径
_STDLIB_PATH = str(_PROJECT_ROOT / 'stdlib')


class PlaygroundHandler(BaseHTTPRequestHandler):
    """Playground HTTP 请求处理器"""

    # 文件系统 - 存储用户代码（内存中）
    files = {
        'main.duan': '打印("你好，世界！")\n',
        'lib.duan': '# 在此编写工具函数\n段落 加 接收 a, b:\n    返回 a + b\n',
    }
    current_file = 'main.duan'

    # ---------- HTTP 方法 ----------

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/' or path == '/index.html':
            self._serve_html()
        elif path == '/api/files':
            self._handle_list_files()
        elif path == '/api/current-file':
            self._send_json({'file': self.current_file})
        elif path.startswith('/api/files/'):
            filename = path[len('/api/files/'):]
            if filename in self.files:
                self._send_json({'name': filename, 'content': self.files[filename]})
            else:
                self._send_error(404, '文件不存在')
        else:
            self._send_error(404, 'Not Found')

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/compile':
            self._handle_compile()
        elif path == '/api/run':
            self._handle_run()
        elif path == '/api/files/save':
            self._handle_save_file()
        elif path == '/api/files/create':
            self._handle_create_file()
        elif path == '/api/files/delete':
            self._handle_delete_file()
        elif path == '/api/files/current':
            self._handle_set_current()
        else:
            self._send_error(404, 'Not Found')

    # ---------- API Handlers ----------

    def _handle_list_files(self):
        files_list = []
        for name in sorted(self.files.keys()):
            files_list.append({
                'name': name,
                'isCurrent': name == self.current_file,
            })
        self._send_json({'files': files_list})

    def _handle_save_file(self):
        data = self._read_json()
        name = data.get('name', '')
        content = data.get('content', '')
        if not name:
            self._send_error(400, '文件名不能为空')
            return
        self.files[name] = content
        self._send_json({'success': True})

    def _handle_create_file(self):
        data = self._read_json()
        name = data.get('name', '')
        if not name:
            self._send_error(400, '文件名不能为空')
            return
        if not name.endswith('.duan'):
            self._send_error(400, '文件名必须以 .duan 结尾')
            return
        if name in self.files:
            self._send_error(400, '文件已存在')
            return
        self.files[name] = ''
        self._send_json({'success': True, 'name': name})

    def _handle_delete_file(self):
        data = self._read_json()
        name = data.get('name', '')
        if name not in self.files:
            self._send_error(404, '文件不存在')
            return
        del self.files[name]
        if self.current_file == name:
            self.current_file = next(iter(self.files.keys()), '')
        self._send_json({'success': True})

    def _handle_set_current(self):
        data = self._read_json()
        name = data.get('name', '')
        if name not in self.files:
            self._send_error(404, '文件不存在')
            return
        self.current_file = name
        self._send_json({'success': True})

    def _handle_compile(self):
        """编译段言代码：词法分析 + 语法分析，返回 tokens 和 AST 摘要"""
        if not COMPILER_AVAILABLE:
            self._send_json({
                'success': False,
                'errors': [{'message': '编译器模块未加载', 'line': 1, 'col': 0}],
                'tokens': [],
                'ast': ''
            })
            return

        data = self._read_json()
        code = data.get('code', '')
        errors = []

        # 1. 词法分析
        tokens = []
        try:
            lexer = Lexer()
            tokens = lexer.tokenize(code)
            token_strs = [str(t) for t in tokens[:80]]
        except Exception as e:
            errors.append({'message': f'词法错误: {e}', 'line': 1, 'col': 0})
            self._send_json({'success': False, 'errors': errors, 'tokens': [], 'ast': ''})
            return

        # 2. 语法分析
        ast_summary = ''
        parse_ok = True
        try:
            parser = DuanParser()
            module = parser.parse(code)
            ast_summary = self._ast_summary(module)
        except ParseError as e:
            errors.append({'message': f'语法错误: {e}', 'line': 1, 'col': 0})
            parse_ok = False
        except Exception as e:
            errors.append({'message': f'解析错误: {e}', 'line': 1, 'col': 0})
            parse_ok = False

        self._send_json({
            'success': parse_ok and len(errors) == 0,
            'errors': errors,
            'tokens': token_strs,
            'ast': ast_summary,
        })

    def _handle_run(self):
        """编译并运行段言代码"""
        if not COMPILER_AVAILABLE:
            self._send_json({
                'success': False,
                'output': '',
                'errors': ['编译器模块未加载']
            })
            return

        data = self._read_json()
        code = data.get('code', '')
        filename = data.get('filename', 'main.duan')

        # 先解析
        try:
            parser = DuanParser()
            module = parser.parse(code)
        except Exception as e:
            self._send_json({
                'success': False,
                'output': '',
                'errors': [f'语法错误: {e}']
            })
            return

        # 生成 Python 代码
        try:
            generator = PythonCodeGenerator()
            py_code = generator.generate(module)
        except Exception as e:
            self._send_json({
                'success': False,
                'output': '',
                'errors': [f'代码生成错误: {e}']
            })
            return

        # 执行生成的 Python 代码
        output = io.StringIO()
        errors = []
        try:
            exec_globals = {
                '__name__': '__main__',
                '__file__': filename,
            }
            # 使用自定义 print 捕获输出
            custom_print = lambda *args, **kwargs: print(
                *args, **kwargs, file=output
            )
            exec_globals['打印'] = custom_print
            exec_globals['print'] = custom_print

            with contextlib.redirect_stdout(output):
                exec(py_code, exec_globals)

            self._send_json({
                'success': True,
                'output': output.getvalue(),
                'errors': [],
            })
        except Exception as e:
            errors.append(f'{type(e).__name__}: {e}')
            errors.append(traceback.format_exc())
            self._send_json({
                'success': False,
                'output': output.getvalue(),
                'errors': errors,
            })

    # ---------- 辅助方法 ----------

    def _ast_summary(self, node, indent=0):
        """生成 AST 的文本摘要"""
        if node is None:
            return ''
        name = type(node).__name__
        prefix = '  ' * indent

        # 收集基本属性
        attrs = {}
        for attr in dir(node):
            if attr.startswith('_') or attr in ('statements', 'body', 'segments', 'classes', 'methods', 'params', 'parameters', 'args', 'elements'):
                continue
            val = getattr(node, attr, None)
            if val is not None and not callable(val):
                if isinstance(val, (str, int, float, bool)):
                    attrs[attr] = val

        result = f'{prefix}{name}'
        for k, v in sorted(attrs.items()):
            result += f' {k}={v}'
        result += '\n'

        # 递归处理子节点
        for child_attr in ('statements', 'body', 'segments', 'classes', 'methods', 'params', 'parameters', 'args', 'elements'):
            children = getattr(node, child_attr, None) or []
            if isinstance(children, list):
                for child in children:
                    if hasattr(child, '__class__') and hasattr(child, '__dict__'):
                        result += self._ast_summary(child, indent + 1)

        return result

    # ---------- HTTP Helpers ----------

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_error(self, status, message):
        self._send_json({'error': message}, status)

    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode('utf-8'))

    def _serve_html(self):
        """服务 HTML 页面 - 所有前端代码内嵌"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_TEMPLATE.encode('utf-8'))


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>段言 Playground</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #1e1e1e; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; }
        .toolbar { background: #2d2d2d; padding: 8px 16px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #3c3c3c; flex-shrink: 0; }
        .toolbar h1 { font-size: 14px; font-weight: 600; margin-right: 16px; }
        .toolbar button { padding: 6px 14px; border: 1px solid #555; border-radius: 4px; background: #3c3c3c; color: #d4d4d4; cursor: pointer; font-size: 12px; }
        .toolbar button:hover { background: #505050; }
        .toolbar button.primary { background: #0e639c; border-color: #0e639c; }
        .toolbar button.primary:hover { background: #1177bb; }
        .toolbar button.danger { background: #5c2d2d; border-color: #5c2d2d; }
        .toolbar button.danger:hover { background: #7a3a3a; }
        .main { display: flex; flex: 1; overflow: hidden; }
        .file-panel { width: 200px; background: #252526; border-right: 1px solid #3c3c3c; display: flex; flex-direction: column; flex-shrink: 0; }
        .file-panel .header { padding: 8px 12px; font-size: 11px; text-transform: uppercase; color: #888; border-bottom: 1px solid #3c3c3c; }
        .file-list { flex: 1; overflow-y: auto; }
        .file-item { padding: 6px 12px; cursor: pointer; font-size: 13px; display: flex; justify-content: space-between; align-items: center; }
        .file-item:hover { background: #2a2d2e; }
        .file-item.active { background: #37373d; }
        .file-item .close { color: #888; cursor: pointer; padding: 0 4px; font-size: 14px; }
        .file-item .close:hover { color: #e06c75; }
        .file-panel .new-file { padding: 8px 12px; }
        .file-panel .new-file input { width: 100%; padding: 4px 8px; background: #3c3c3c; border: 1px solid #555; color: #d4d4d4; border-radius: 3px; font-size: 12px; outline: none; }
        .file-panel .new-file input:focus { border-color: #0e639c; }
        .editor-panel { flex: 1; display: flex; flex-direction: column; min-width: 0; }
        .editor-panel .tab-bar { display: flex; background: #252526; border-bottom: 1px solid #3c3c3c; flex-shrink: 0; }
        .tab-item { padding: 6px 16px; font-size: 13px; cursor: pointer; color: #888; border-right: 1px solid #3c3c3c; }
        .tab-item.active { color: #fff; background: #1e1e1e; border-bottom: 1px solid #1e1e1e; }
        .tab-item .dirty { color: #e06c75; margin-left: 4px; }
        textarea { flex: 1; background: #1e1e1e; color: #d4d4d4; border: none; outline: none; padding: 16px; font-family: "Cascadia Code", "Fira Code", "Consolas", monospace; font-size: 14px; line-height: 1.5; resize: none; tab-size: 4; }
        .bottom-panel { height: 250px; background: #1e1e1e; border-top: 1px solid #3c3c3c; display: flex; flex-direction: column; flex-shrink: 0; }
        .bottom-panel .tabs { display: flex; background: #252526; border-bottom: 1px solid #3c3c3c; flex-shrink: 0; }
        .bottom-panel .tab { padding: 4px 16px; font-size: 12px; cursor: pointer; color: #888; }
        .bottom-panel .tab.active { color: #fff; }
        .bottom-panel .tab .badge { background: #e06c75; color: #fff; border-radius: 8px; padding: 0 6px; font-size: 10px; margin-left: 4px; }
        .output-content { flex: 1; overflow-y: auto; padding: 8px 16px; font-family: "Cascadia Code", "Fira Code", "Consolas", monospace; font-size: 13px; white-space: pre-wrap; }
        .output-content.error { color: #e06c75; }
        .output-content.success { color: #98c379; }
        .error-panel { border-top: 1px solid #3c3c3c; max-height: 150px; overflow-y: auto; background: #2d2d2d; }
        .error-item { padding: 4px 12px; font-size: 12px; color: #e06c75; border-bottom: 1px solid #3c3c3c; cursor: pointer; }
        .error-item:hover { background: #3a3a3a; }
        .error-item .line { color: #888; margin-right: 8px; }
        .statusbar { background: #007acc; padding: 2px 12px; font-size: 12px; color: #fff; flex-shrink: 0; }
        .resize-handle { height: 4px; background: #3c3c3c; cursor: ns-resize; flex-shrink: 0; }
        .resize-handle:hover { background: #007acc; }
    </style>
</head>
<body>
    <div class="toolbar">
        <h1>段言 Playground</h1>
        <button class="primary" onclick="runCode()">▶ 运行</button>
        <button onclick="compileCode()">⚙ 编译</button>
        <span style="flex:1"></span>
        <span id="status" style="font-size:12px;color:#888">就绪</span>
    </div>
    <div class="main">
        <div class="file-panel">
            <div class="header">文件</div>
            <div class="file-list" id="fileList"></div>
            <div class="new-file">
                <input type="text" placeholder="新建文件.duan" id="newFileName" onkeydown="if(event.key==='Enter')createFile()">
            </div>
        </div>
        <div class="editor-panel">
            <div class="tab-bar" id="tabBar">
                <div class="tab-item active" id="currentTab">无文件</div>
            </div>
            <textarea id="editor" spellcheck="false" oninput="onEditorChange()"></textarea>
        </div>
    </div>
    <div class="resize-handle" id="resizeHandle"></div>
    <div class="bottom-panel" id="bottomPanel">
        <div class="tabs">
            <div class="tab active" id="outputTab" onclick="switchOutputTab('output')">输出</div>
            <div class="tab" id="astTab" onclick="switchOutputTab('ast')">AST</div>
            <div class="tab" id="tokensTab" onclick="switchOutputTab('tokens')">Token</div>
        </div>
        <div class="output-content" id="output"></div>
    </div>
    <div class="error-panel" id="errorPanel" style="display:none"></div>
    <div class="statusbar" id="statusBar">就绪</div>
    <script>
        let currentFile = '';
        let files = {};
        let dirty = false;
        let outputTab = 'output';
        let autoSaveTimer = null;

        function loadFiles() {
            fetch('/api/files')
                .then(r => r.json())
                .then(data => {
                    const fileList = document.getElementById('fileList');
                    fileList.innerHTML = '';
                    data.files.forEach(f => {
                        const div = document.createElement('div');
                        div.className = 'file-item' + (f.isCurrent ? ' active' : '');
                        div.innerHTML = '<span>' + escapeHtml(f.name) + '</span><span class="close" onclick="event.stopPropagation();deleteFile(\\'' + escapeJs(f.name) + '\\')">×</span>';
                        div.onclick = () => openFile(f.name);
                        fileList.appendChild(div);
                    });
                    if (!currentFile && data.files.length > 0) {
                        openFile(data.files[0].name);
                    }
                });
        }

        function openFile(name) {
            fetch('/api/files/' + encodeURIComponent(name))
                .then(r => r.json())
                .then(data => {
                    currentFile = data.name;
                    document.getElementById('editor').value = data.content;
                    dirty = false;
                    updateUI();
                    loadFiles();
                    document.getElementById('output').textContent = '';
                    document.getElementById('output').className = 'output-content';
                });
        }

        function saveCurrentFile() {
            if (!currentFile) return;
            const code = document.getElementById('editor').value;
            fetch('/api/files/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: currentFile, content: code})
            });
            dirty = false;
            updateUI();
        }

        function onEditorChange() {
            if (!dirty) {
                dirty = true;
                updateUI();
            }
            if (autoSaveTimer) clearTimeout(autoSaveTimer);
            autoSaveTimer = setTimeout(saveCurrentFile, 2000);
        }

        function runCode() {
            const code = document.getElementById('editor').value;
            if (!currentFile) { setStatus('请先选择文件'); return; }
            setStatus('运行中...');
            clearErrors();
            saveCurrentFile();

            fetch('/api/run', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: code, filename: currentFile || 'main.duan'})
            })
            .then(r => r.json())
            .then(data => {
                const output = document.getElementById('output');
                output.className = 'output-content';
                if (data.success) {
                    output.textContent = data.output || '(无输出)';
                    output.className += ' success';
                } else {
                    output.textContent = '错误:\\n' + (data.errors || []).join('\\n');
                    output.className += ' error';
                }
                switchOutputTab('output');
                setStatus('就绪');
            })
            .catch(err => {
                setStatus('网络错误');
                document.getElementById('output').textContent = '请求失败: ' + err;
            });
        }

        function compileCode() {
            const code = document.getElementById('editor').value;
            if (!currentFile) { setStatus('请先选择文件'); return; }
            setStatus('编译中...');
            clearErrors();

            fetch('/api/compile', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: code, filename: currentFile || 'main.duan'})
            })
            .then(r => r.json())
            .then(data => {
                const output = document.getElementById('output');
                if (data.errors && data.errors.length > 0) {
                    showErrors(data.errors);
                    output.textContent = '编译失败: ' + data.errors.length + ' 个错误';
                    output.className = 'output-content error';
                } else {
                    output.textContent = '编译通过!';
                    output.className = 'output-content success';
                }
                setStatus('就绪');
            })
            .catch(err => {
                setStatus('网络错误');
            });
        }

        function updateUI() {
            const tabBar = document.getElementById('tabBar');
            tabBar.innerHTML = '<div class="tab-item active">' + escapeHtml(currentFile || '无文件') + (dirty ? '<span class="dirty"> ●</span>' : '') + '</div>';
        }

        function createFile() {
            const input = document.getElementById('newFileName');
            const name = input.value.trim();
            if (!name) return;
            if (!name.endsWith('.duan')) {
                setStatus('文件名必须以 .duan 结尾');
                return;
            }
            fetch('/api/files/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    input.value = '';
                    openFile(name);
                } else {
                    setStatus('创建失败: ' + (data.error || ''));
                }
            });
        }

        function deleteFile(name) {
            if (!confirm('删除 ' + name + '?')) return;
            fetch('/api/files/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    loadFiles();
                }
            });
        }

        function showErrors(errors) {
            const panel = document.getElementById('errorPanel');
            panel.innerHTML = '';
            errors.forEach(e => {
                const div = document.createElement('div');
                div.className = 'error-item';
                div.innerHTML = '<span class="line">[' + (e.line || 1) + ':' + (e.col || 0) + ']</span>' + escapeHtml(e.message);
                panel.appendChild(div);
            });
            panel.style.display = errors.length > 0 ? 'block' : 'none';
        }

        function clearErrors() {
            document.getElementById('errorPanel').style.display = 'none';
            document.getElementById('errorPanel').innerHTML = '';
        }

        function switchOutputTab(tab) {
            outputTab = tab;
            document.querySelectorAll('.bottom-panel .tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tab + 'Tab').classList.add('active');
        }

        function setStatus(msg) {
            document.getElementById('status').textContent = msg;
            document.getElementById('statusBar').textContent = msg;
        }

        function escapeHtml(str) {
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function escapeJs(str) {
            return String(str).replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'");
        }

        // 底部面板拖拽调整大小
        (function() {
            const handle = document.getElementById('resizeHandle');
            const panel = document.getElementById('bottomPanel');
            let startY, startH;
            handle.addEventListener('mousedown', function(e) {
                startY = e.clientY;
                startH = panel.offsetHeight;
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
            function onMouseMove(e) {
                const delta = startY - e.clientY;
                const newH = Math.max(100, Math.min(500, startH + delta));
                panel.style.height = newH + 'px';
            }
            function onMouseUp() {
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            }
        })();

        // 自动保存每3秒
        setInterval(() => {
            if (dirty && currentFile) {
                saveCurrentFile();
            }
        }, 3000);

        // 初始化
        loadFiles();
    </script>
</body>
</html>'''


def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description='段言 Playground - Web 编辑器')
    parser.add_argument('--port', type=int, default=8080, help='监听端口 (默认: 8080)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='监听地址 (默认: 127.0.0.1)')
    return parser.parse_args()


def run_server(host='127.0.0.1', port=8080):
    """启动 HTTP 服务器"""
    server = HTTPServer((host, port), PlaygroundHandler)
    print(f"段言 Playground 已启动!")
    print(f"  访问地址: http://{host}:{port}")
    print(f"  编译器: {'可用' if COMPILER_AVAILABLE else '不可用 (请检查 src/ 目录)'}")
    print(f"  按 Ctrl+C 停止服务器")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        server.server_close()
        print("服务器已停止。")


if __name__ == '__main__':
    args = parse_args()
    run_server(host=args.host, port=args.port)