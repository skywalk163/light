/**
 * 光明 (Light) Web Playground - 前端逻辑 v4.0
 */

let editor = null;
let currentExampleId = null;
let isSidebarOpen = false;
let currentFontSize = 14;
let autoSaveTimer = null;
let currentProjectName = '';
let currentStyle = 'L2'; // 默认 L2 文言模式

const API_BASE = '';
const STORAGE_KEY = 'light_playground_code';
const PROJECT_KEY = 'light_playground_project';
const THEME_KEY = 'light_playground_theme';
const FONT_KEY = 'light_playground_font';
const STYLE_KEY = 'light_playground_style';

loadExamples();

const params = new URLSearchParams(window.location.search);
const shareId = params.get('share');
if (shareId) {
    loadSharedCode(shareId);
}

const savedTheme = localStorage.getItem(THEME_KEY) || 'dark';
applyTheme(savedTheme);

const savedFont = parseInt(localStorage.getItem(FONT_KEY)) || 14;
currentFontSize = savedFont;

const savedStyle = localStorage.getItem(STYLE_KEY) || 'L2';
currentStyle = savedStyle;
applyStyle(currentStyle);

require.config({
    paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }
});

require(['vs/editor/editor.main'], function () {
    monaco.languages.register({ id: 'light' });

    monaco.languages.setMonarchTokensProvider('light', {
        defaultToken: '',
        tokenPostfix: '.light',

        keywords: [
            // v4.0 L0 核心关键字（单字主形式）
            '设', '为', '等于',
            '若', '则', '否', '或若',
            '遍', '于', '当', '断', '跃',
            '段', '返',
            '类', '承', '性', '构', '己', '父', '新',
            '约', '现',
            '引', '出', '自',
            '且', '或', '非',
            '真', '假', '空',
            '印', '写',
            '试', '捕', '掷',
            '匹', '例',
            '异', '等',
            '常',
            '护', '私', '公', '静',
            '是',
            // v3.3 兼容别名（双字形式）
            '如果', '那么', '否则', '否则如果',
            '遍历', '段落', '接收', '返回',
            '继承', '属性', '构造', '新建',
            '接口', '实现',
            '导入', '导出', '从',
            '打印', '输出',
            '尝试', '捕获', '抛出',
            '匹配', '情况',
            '异步', '等待',
            '常量',
            '保护', '私有', '公共', '静态',
            '跳出', '跳过'
        ],

        typeKeywords: [
            '数', '整数', '浮数', '串', '列', '典', '集', '布尔', '空类型', '任意'
        ],

        operators: [
            // v4.0 符号运算符（主形式）
            '+', '-', '*', '/', '%', '**', '//',
            '>', '<', '>=', '<=', '==', '!=',
            '+=', '-=', '*=', '/=',
            // v3.3 中文运算符（别名）
            '加', '减', '乘', '除', '模', '幂',
            '大于', '小于', '等于', '不等于', '大于等于', '小于等于',
            '加上', '减去', '乘以', '除以'
        ],

        tokenizer: {
            root: [
                [/#.*$/, 'comment'],

                [/"[^"]*"/, 'string'],
                [/'[^']*'/, 'string'],

                [/\d+\.\d+/, 'number.float'],
                [/\d+/, 'number'],

                [
                    /[^\s\[\]\(\)（）,，。.：:；;{}"']+/,
                    {
                        cases: {
                            '@keywords': 'keyword',
                            '@typeKeywords': 'type',
                            '@operators': 'operator',
                            '@default': 'identifier'
                        }
                    }
                ],

                [/[。.]/, 'delimiter'],
                [/[，,]/, 'delimiter'],
                [/[：:]/, 'delimiter'],
                [/[；;]/, 'delimiter'],
                [/[\[\]\(\)（）{}]/, '@brackets'],
            ]
        }
    });

    const savedCode = getSavedCode();
    const defaultCode = savedCode || getDefaultCode();

    const theme = localStorage.getItem(THEME_KEY) || 'dark';
    const monacoTheme = theme === 'dark' ? 'vs-dark' : 'vs';

    editor = monaco.editor.create(document.getElementById('editor'), {
        value: defaultCode,
        language: 'light',
        theme: monacoTheme,
        fontSize: currentFontSize,
        lineHeight: currentFontSize + 8,
        fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', Consolas, 'Microsoft YaHei', monospace",
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        padding: { top: 12, bottom: 12 },
        automaticLayout: true,
        tabSize: 4,
        insertSpaces: true,
        wordWrap: 'on',
        renderWhitespace: 'selection',
        bracketPairColorization: { enabled: true },
        lineNumbersMinChars: 3,
        glyphMargin: false,
        folding: true,
        smoothScrolling: true,
        cursorSmoothCaretAnimation: 'on',
        suggest: {
            showKeywords: true,
            showTypes: true,
            snippetsPreventQuickSuggestions: false
        }
    });

    editor.onDidChangeModelContent(function () {
        scheduleAutoSave();
        updateAutoSaveLabel('正在保存...');
        // 标记当前文件为脏
        if (activeFile && openFiles[activeFile]) {
            openFiles[activeFile].dirty = true;
        }
    });

    document.getElementById('fontSizeLabel').textContent = currentFontSize + 'px';

    // 恢复保存的项目名称
    try {
        const savedProject = localStorage.getItem(PROJECT_KEY);
        if (savedProject) {
            currentProjectName = savedProject;
            updateProjectNameDisplay();
        }
    } catch(e) {}

    window._monacoReady = true;
});

setTimeout(function() {
    if (!window._monacoReady) {
        const container = document.getElementById('editor');
        if (container && !container.querySelector('textarea')) {
            const fallback = document.createElement('textarea');
            fallback.className = 'fallback-editor';
            fallback.value = getDefaultCode();
            fallback.style.cssText = 'width:100%;height:100%;background:#1e1e1e;color:#d4d4d4;border:none;padding:16px;font-family:Consolas,monospace;font-size:14px;line-height:1.6;resize:none;outline:none;tab-size:4';
            container.appendChild(fallback);

            editor = {
                getValue: function() { return fallback.value; },
                setValue: function(v) { fallback.value = v; },
                updateOptions: function() {}
            };

            fallback.addEventListener('input', function() {
                scheduleAutoSave();
                updateAutoSaveLabel('正在保存...');
            });
        }
    }
}, 5000);

function getDefaultCode() {
    return `# 欢迎使用光明 v4.0 Playground！
# 试试运行这段代码 👇
# 快捷键：Ctrl+Enter 运行
# 文体切换：点击工具栏「文」按钮切换 L1白话 / L2文言

印("你好，光明 v4.0！")

设 甲 为 10
设 乙 为 20

印("甲 = ")
印(甲)
印("乙 = ")
印(乙)

若 甲 > 乙：
  印("甲更大")
否则：
  印("乙更大")

# v4.0 函数定义（单字关键字）
段 平方(x)：
  返回 x * x

印("5 的平方 = ")
印(平方(5))

# v4.0 循环
设 总和 为 0
遍 i 于 列(1, 2, 3, 4, 5)：
  设 总和 为 总和 + i
印("1-5 总和 = ")
印(总和)
`;
}

function getSavedCode() {
    try {
        return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
        return null;
    }
}

function saveCode() {
    try {
        if (editor && editor.getValue) {
            localStorage.setItem(STORAGE_KEY, editor.getValue());
            updateAutoSaveLabel('已自动保存');
        }
    } catch (e) {}
}

function scheduleAutoSave() {
    if (autoSaveTimer) clearTimeout(autoSaveTimer);
    autoSaveTimer = setTimeout(saveCode, 1000);
}

function updateAutoSaveLabel(text) {
    const el = document.getElementById('autoSaveLabel');
    if (el) el.textContent = text;
}

function runCode() {
    // 多文件项目：使用项目运行 API
    if (currentProjectName && projectFiles.length > 0) {
        runProject();
        return;
    }

    const code = editor.getValue();
    if (!code.trim()) {
        showToast('请输入代码', 'warning');
        return;
    }

    const runBtn = document.getElementById('runBtn');
    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="spinner"></span> 运行中...';

    ['outputPanel', 'astPanel', 'tokensPanel', 'pythonPanel', 'llvmPanel'].forEach(function(id) {
        document.getElementById(id).innerHTML = '';
    });

    const requests = [
        fetch(API_BASE + '/api/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        }).then(r => r.json()),
        fetch(API_BASE + '/api/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        }).then(r => r.json()),
        fetch(API_BASE + '/api/tokenize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        }).then(r => r.json())
    ];

    Promise.all(requests).then(function(results) {
        renderOutput(results[0]);
        renderAST(results[1]);
        renderTokens(results[2]);

        if (results[0].success && results[0].python_code) {
            renderPythonCode(results[0].python_code);
        }
    }).catch(function(err) {
        document.getElementById('outputPanel').innerHTML =
            '<div class="output-line error">网络错误: ' + escapeHtml(err.message) + '</div>';
    }).finally(function() {
        runBtn.disabled = false;
        runBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M4 2.5v11l9-5.5-9-5.5z"/>
            </svg>
            运行
        `;
    });

    fetch(API_BASE + '/api/llvm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
    }).then(r => r.json()).then(function(result) {
        renderLLVM(result);
    }).catch(function() {});
}

function runProject() {
    // 先保存当前文件
    if (editor && activeFile && openFiles[activeFile]) {
        openFiles[activeFile].content = editor.getValue();
    }

    const runBtn = document.getElementById('runBtn');
    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="spinner"></span> 运行中...';

    ['outputPanel', 'astPanel', 'tokensPanel', 'pythonPanel', 'llvmPanel'].forEach(function(id) {
        document.getElementById(id).innerHTML = '';
    });

    // 先保存项目
    var files = [];
    Object.keys(openFiles).forEach(function(fname) {
        files.push({ name: fname, content: openFiles[fname].content });
    });

    fetch(API_BASE + '/api/projects/' + encodeURIComponent(currentProjectName), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: files })
    })
    .then(function() {
        return fetch(API_BASE + '/api/projects/' + encodeURIComponent(currentProjectName) + '/run', {
            method: 'POST'
        });
    })
    .then(function(r) { return r.json(); })
    .then(function(result) {
        document.getElementById('outputPanel').innerHTML = '';
        renderProjectOutput(result);
        renderProjectAST(result);
        renderProjectTokens(result);
        renderProjectLLVM(result);
    })
    .catch(function(err) {
        document.getElementById('outputPanel').innerHTML =
            '<div class="output-line error">网络错误: ' + escapeHtml(err.message) + '</div>';
    })
    .finally(function() {
        runBtn.disabled = false;
        runBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M4 2.5v11l9-5.5-9-5.5z"/>
            </svg>
            运行
        `;
    });
}

function renderProjectOutput(result) {
    const panel = document.getElementById('outputPanel');
    if (result.success) {
        var html = '';
        if (result.execution_time !== undefined) {
            html += '<div class="output-meta">执行时间: ' + result.execution_time + ' ms</div>';
        }
        var lines = (result.output || '').split('\n');
        html += lines.map(function(line) {
            var cls = (line.indexOf('错误') !== -1 || line.indexOf('Error') !== -1) ? 'error'
                     : (line.indexOf('成功') !== -1) ? 'success'
                     : '';
            return '<div class="output-line ' + cls + '">' + escapeHtml(line) + '</div>';
        }).join('');
        panel.innerHTML = html;
    } else {
        var html = '<div class="output-line error">' + escapeHtml(result.error || '') + '</div>';
        if (result.traceback) {
            html += '<pre class="code-block">' + escapeHtml(result.traceback) + '</pre>';
        }
        if (result.output) {
            html += '<div class="output-line">' + escapeHtml(result.output) + '</div>';
        }
        panel.innerHTML = html;
    }
    switchTab('output');
}

function renderProjectAST(result) {
    document.getElementById('astPanel').innerHTML =
        '<div class="output-placeholder">多文件项目请使用「解析」面板查看单个文件 AST</div>';
}

function renderProjectTokens(result) {
    document.getElementById('tokensPanel').innerHTML =
        '<div class="output-placeholder">多文件项目请使用「Token 分析」面板查看单个文件</div>';
}

function renderProjectLLVM(result) {
    document.getElementById('llvmPanel').innerHTML =
        '<div class="output-placeholder">多文件项目暂不支持 LLVM IR 生成</div>';
}

function renderOutput(result) {
    const panel = document.getElementById('outputPanel');

    if (result.success) {
        let html = '';
        if (result.execution_time !== undefined) {
            html += '<div class="output-meta">执行时间: ' + result.execution_time + ' ms</div>';
        }
        const lines = result.output.split('\n');
        html += lines.map(function(line) {
            const cls = (line.indexOf('错误') !== -1 || line.indexOf('Error') !== -1) ? 'error'
                     : (line.indexOf('成功') !== -1) ? 'success'
                     : '';
            return '<div class="output-line ' + cls + '">' + escapeHtml(line) + '</div>';
        }).join('');
        panel.innerHTML = html;
    } else {
        panel.innerHTML = '<div class="output-line error">' + escapeHtml(result.error) + '</div>';
    }

    switchTab('output');
}

function renderAST(result) {
    const panel = document.getElementById('astPanel');

    if (!result.success) {
        panel.innerHTML = '<div class="output-line error">' + escapeHtml(result.error) + '</div>';
        return;
    }

    let html = '';

    if (result.segments && result.segments.length > 0) {
        html += '<h4 class="panel-subtitle">段落（函数）</h4>';
        html += '<table class="ast-table"><thead><tr><th>名称</th><th>参数</th></tr></thead><tbody>';
        result.segments.forEach(function(seg) {
            const params = seg.parameters.join(', ') || '(无)';
            html += '<tr><td class="ast-segment">' + escapeHtml(seg.name) + '</td><td>' + escapeHtml(params) + '</td></tr>';
        });
        html += '</tbody></table>';
    }

    if (result.classes && result.classes.length > 0) {
        html += '<h4 class="panel-subtitle">类</h4>';
        html += '<table class="ast-table"><thead><tr><th>类名</th><th>父类</th><th>方法</th></tr></thead><tbody>';
        result.classes.forEach(function(cls) {
            const methods = cls.methods ? cls.methods.join(', ') : '(无)';
            const parent = cls.parent || '-';
            html += '<tr><td class="ast-class">' + escapeHtml(cls.name) + '</td><td>' + escapeHtml(parent) + '</td><td>' + escapeHtml(methods) + '</td></tr>';
        });
        html += '</tbody></table>';
    }

    html += '<div class="ast-stats">';
    html += '语句: ' + (result.statement_count || 0) + ' &nbsp;|&nbsp; ';
    html += '段落: ' + (result.segments ? result.segments.length : 0) + ' &nbsp;|&nbsp; ';
    html += '类: ' + (result.classes ? result.classes.length : 0);
    html += '</div>';

    panel.innerHTML = html;
}

function renderTokens(result) {
    const panel = document.getElementById('tokensPanel');

    if (!result.success) {
        panel.innerHTML = '<div class="output-line error">' + escapeHtml(result.error) + '</div>';
        return;
    }

    if (result.errors && result.errors.length > 0) {
        panel.innerHTML = result.errors.map(function(e) {
            return '<div class="output-line error">' + escapeHtml(e) + '</div>';
        }).join('') + '<br>';
    }

    let html = '<div class="token-count">共 ' + result.token_count + ' 个 Token</div>';
    html += '<table class="token-table"><thead><tr><th>类型</th><th>文本</th><th>位置</th></tr></thead><tbody>';

    result.tokens.forEach(function(t) {
        html += '<tr><td class="token-type">' + escapeHtml(t.type) + '</td><td class="token-text">' + escapeHtml(t.text) + '</td><td class="token-loc">' + t.line + ':' + t.column + '</td></tr>';
    });

    html += '</tbody></table>';
    panel.innerHTML = html;
}

function renderPythonCode(code) {
    const panel = document.getElementById('pythonPanel');
    panel.innerHTML = '<pre class="code-block">' + escapeHtml(code) + '</pre>';
}

function renderLLVM(result) {
    const panel = document.getElementById('llvmPanel');
    if (result.success) {
        panel.innerHTML = '<pre class="code-block">' + escapeHtml(result.ir_code) + '</pre>';
    } else {
        panel.innerHTML = '<div class="output-placeholder">' + escapeHtml(result.error) + '</div>';
    }
}

function loadExamples() {
    fetch(API_BASE + '/api/examples')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const list = document.getElementById('exampleList');
            let html = '';

            if (data.categories) {
                data.categories.forEach(function(cat) {
                    html += '<div class="example-category">';
                    html += '<div class="example-cat-title">' + escapeHtml(cat.category) + '</div>';
                    cat.examples.forEach(function(ex) {
                        html += '<div class="example-item" data-id="' + ex.id + '" onclick="loadExample(\'' + ex.id + '\')">';
                        html += '<div class="example-item-title">' + escapeHtml(ex.title) + '</div>';
                        html += '<div class="example-item-desc">' + escapeHtml(ex.description) + '</div>';
                        html += '</div>';
                    });
                    html += '</div>';
                });
            }

            list.innerHTML = html;
        })
        .catch(function(err) {
            document.getElementById('exampleList').innerHTML =
                '<div class="example-loading">加载失败: ' + escapeHtml(err.message) + '</div>';
        });
}

function loadExample(exampleId) {
    fetch(API_BASE + '/api/examples/' + exampleId)
        .then(function(r) { return r.json(); })
        .then(function(ex) {
            if (ex.error) {
                showToast(ex.error, 'error');
                return;
            }
            editor.setValue(ex.code);
            currentExampleId = exampleId;

            document.querySelectorAll('.example-item').forEach(function(el) {
                el.classList.toggle('active', el.dataset.id === exampleId);
            });

            if (window.innerWidth <= 768) {
                toggleSidebar();
            }

            showToast('已加载示例: ' + ex.title, 'success');
        })
        .catch(function() { showToast('加载示例失败', 'error'); });
}

function toggleSidebar() {
    isSidebarOpen = !isSidebarOpen;
    document.getElementById('sidebar').classList.toggle('closed', !isSidebarOpen);
}

let _grammarLoaded = false;

function openGrammarModal() {
    document.getElementById('grammarOverlay').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    loadGrammar();
}

function closeGrammarModal() {
    document.getElementById('grammarOverlay').classList.add('hidden');
    document.body.style.overflow = '';
}

let _stdlibLoaded = false;

function openStdlibModal() {
    document.getElementById('stdlibOverlay').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    loadStdlib();
}

function closeStdlibModal() {
    document.getElementById('stdlibOverlay').classList.add('hidden');
    document.body.style.overflow = '';
}

function loadGrammar() {
    if (_grammarLoaded) return;
    _grammarLoaded = true;

    const panel = document.getElementById('grammarModalBody');
    panel.innerHTML = '<div class="grammar-loading">📖 加载语法参考中...</div>';

    fetch(API_BASE + '/api/grammar')
        .then(function(r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(data) {
            renderGrammar(data.categories);
        })
        .catch(function(err) {
            panel.innerHTML = '<div class="output-line error">加载失败: ' + escapeHtml(err.message) + '</div>';
            _grammarLoaded = false;
        });
}

function loadStdlib() {
    if (_stdlibLoaded) return;
    _stdlibLoaded = true;

    const panel = document.getElementById('stdlibModalBody');
    panel.innerHTML = '<div class="grammar-loading">📚 加载标准库参考中...</div>';

    fetch(API_BASE + '/api/stdlib')
        .then(function(r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(data) {
            renderStdlib(data.categories);
        })
        .catch(function(err) {
            panel.innerHTML = '<div class="output-line error">加载失败: ' + escapeHtml(err.message) + '</div>';
            _stdlibLoaded = false;
        });
}

function renderGrammar(categories) {
    const panel = document.getElementById('grammarModalBody');

    let html = '<div class="grammar-intro"><p>快速入门光明 v4.0 分层语法。L0 核心字（30个）稳定不变，L1 白话子集（19字）适合教学，L2 文言全集（30字）适合商业项目。点击「示例」可加载对应代码体验。</p></div>';

    categories.forEach(function(cat) {
        html += '<div class="grammar-category">';
        html += '<h4 class="grammar-cat-title">' + escapeHtml(cat.category) + '</h4>';
        html += '<div class="grammar-items">';

        cat.items.forEach(function(item) {
            html += '<div class="grammar-item">';
            const syntaxLines = item.syntax.split('\n');
            html += '<div class="grammar-syntax">';
            syntaxLines.forEach(function(line) {
                html += '<code>' + escapeHtml(line) + '</code>';
            });
            html += '</div>';
            if (item.description) {
                html += '<div class="grammar-desc">' + escapeHtml(item.description) + '</div>';
            }
            if (item.example) {
                html += '<div class="grammar-example">例: ' + escapeHtml(item.example) + '</div>';
            }
            html += '</div>';
        });

        html += '</div></div>';
    });

    panel.innerHTML = html;
}

function renderStdlib(categories) {
    const panel = document.getElementById('stdlibModalBody');

    let html = '<div class="grammar-intro"><p>光明标准库提供了丰富的功能模块，点击查看各模块的使用方法。</p></div>';

    categories.forEach(function(cat) {
        html += '<div class="grammar-category">';
        html += '<h4 class="grammar-cat-title" style="color: var(--accent-purple);">' + escapeHtml(cat.category) + '</h4>';
        html += '<div class="grammar-items">';

        cat.items.forEach(function(item) {
            html += '<div class="grammar-item">';
            html += '<div class="grammar-syntax"><code>' + escapeHtml(item.name) + '</code></div>';
            if (item.desc) {
                html += '<div class="grammar-desc">' + escapeHtml(item.desc) + '</div>';
            }
            html += '</div>';
        });

        html += '</div></div>';
    });

    panel.innerHTML = html;
}

function closeModals() {
    closeShareModal();
    closeGrammarModal();
    closeStdlibModal();
    closeProjectsModal();
    closeCreateFileModal();
    closeDeleteFileModal();
}

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('.output-panel').forEach(function(p) { p.classList.add('hidden'); });

    const tabEl = document.querySelector('.tab[data-tab="' + tabName + '"]');
    if (tabEl) tabEl.classList.add('active');
    const panel = document.getElementById(tabName + 'Panel');
    if (panel) panel.classList.remove('hidden');
}

function clearOutput() {
    ['outputPanel', 'astPanel', 'tokensPanel', 'pythonPanel', 'llvmPanel'].forEach(function(id) {
        document.getElementById(id).innerHTML = '<div class="output-placeholder">输出已清除</div>';
    });
    showToast('输出已清除', 'info');
}

function resetCode() {
    if (confirm('确定要重置为默认代码吗？当前代码将丢失。')) {
        editor.setValue(getDefaultCode());
        showToast('已重置为默认代码', 'info');
    }
}

function copyCode() {
    const code = editor.getValue();
    navigator.clipboard.writeText(code).then(function() {
        showToast('代码已复制到剪贴板', 'success');
    }).catch(function() {
        showToast('复制失败', 'error');
    });
}

function shareCode() {
    const code = editor.getValue();
    if (!code.trim()) {
        showToast('没有可分享的代码', 'warning');
        return;
    }

    const shareBtn = document.getElementById('shareBtn');
    shareBtn.disabled = true;

    fetch(API_BASE + '/api/share', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            const url = window.location.origin + window.location.pathname + '?share=' + data.share_id;
            document.getElementById('shareUrlInput').value = url;
            document.getElementById('shareModal').classList.remove('hidden');
            document.getElementById('overlay').classList.remove('hidden');
        } else {
            showToast(data.error || '分享失败', 'error');
        }
    })
    .catch(function(err) { showToast('网络错误: ' + err.message, 'error'); })
    .finally(function() {
        shareBtn.disabled = false;
    });
}

function closeShareModal() {
    document.getElementById('shareModal').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');
}

function copyShareUrl() {
    const input = document.getElementById('shareUrlInput');
    input.select();
    navigator.clipboard.writeText(input.value).then(function() {
        showToast('链接已复制到剪贴板', 'success');
    }).catch(function() {
        document.execCommand('copy');
        showToast('链接已复制', 'success');
    });
}

function loadSharedCode(shareId) {
    fetch(API_BASE + '/api/share/' + shareId)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }
            if (editor && editor.setValue) {
                editor.setValue(data.code);
            }
            showToast('已加载分享的代码', 'success');
        })
        .catch(function() { showToast('加载分享代码失败', 'error'); });
}

function increaseFontSize() {
    if (currentFontSize < 24) {
        currentFontSize += 2;
        updateFontSize();
    }
}

function decreaseFontSize() {
    if (currentFontSize > 10) {
        currentFontSize -= 2;
        updateFontSize();
    }
}

function updateFontSize() {
    if (editor && editor.updateOptions) {
        editor.updateOptions({
            fontSize: currentFontSize,
            lineHeight: currentFontSize + 8
        });
    }
    document.getElementById('fontSizeLabel').textContent = currentFontSize + 'px';
    try {
        localStorage.setItem(FONT_KEY, currentFontSize);
    } catch (e) {}
}

function toggleTheme() {
    const current = document.body.dataset.theme;
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    try {
        localStorage.setItem(THEME_KEY, next);
    } catch (e) {}
}

function toggleStyle() {
    const next = currentStyle === 'L2' ? 'L1' : 'L2';
    currentStyle = next;
    applyStyle(next);
    try {
        localStorage.setItem(STYLE_KEY, next);
    } catch (e) {}
    const label = next === 'L1' ? '白话' : '文言';
    showToast('已切换到 L' + (next === 'L1' ? '1' : '2') + ' ' + label + '模式', 'info');
}

function applyStyle(style) {
    document.body.dataset.style = style;
    const btn = document.getElementById('styleBtn');
    if (btn) {
        btn.title = style === 'L1' ? '当前：L1 白话模式（19字子集）' : '当前：L2 文言模式（30字全集）';
        btn.style.color = style === 'L1' ? 'var(--accent-orange)' : 'var(--accent-purple)';
    }
}

// ==================== 多文件项目管理 ====================

var openFiles = {};           // {filename: {content, dirty}}
var activeFile = 'main.light'; // 当前编辑的文件
var projectFiles = [];        // 项目文件列表
var fileToDelete = null;     // 待删除的文件名

function switchSidebarTab(tab) {
    document.querySelectorAll('.sidebar-tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('.sidebar-panel').forEach(function(p) { p.classList.add('hidden'); });

    var tabEl = document.querySelector('.sidebar-tab[data-panel="' + tab + '"]');
    if (tabEl) tabEl.classList.add('active');

    if (tab === 'examples') {
        document.getElementById('sidebarExamples').classList.remove('hidden');
        document.getElementById('sidebarFiles').classList.add('hidden');
    } else {
        document.getElementById('sidebarExamples').classList.add('hidden');
        document.getElementById('sidebarFiles').classList.remove('hidden');
    }
}

function renderFileTree() {
    var tree = document.getElementById('fileTree');
    if (!currentProjectName) {
        tree.innerHTML = '<div class="projects-empty">加载项目后可查看文件</div>';
        return;
    }

    document.getElementById('fileTreeProjectName').textContent = currentProjectName;

    if (projectFiles.length === 0) {
        tree.innerHTML = '<div class="projects-empty">暂无文件，点击 + 新建</div>';
        return;
    }

    var html = '';
    projectFiles.forEach(function(f) {
        var isActive = f.name === activeFile;
        html += '<div class="file-tree-item' + (isActive ? ' active' : '') + '" onclick="openFileInEditor(\'' + escapeHtmlAttr(f.name) + '\')">';
        html += '<span class="file-tree-icon">📄</span>';
        html += '<span class="file-tree-name">' + escapeHtml(f.name) + '</span>';
        html += '<span class="file-tree-actions">';
        html += '<button class="btn btn-icon btn-small" onclick="event.stopPropagation();deleteFilePrompt(\'' + escapeHtmlAttr(f.name) + '\')" title="删除">🗑</button>';
        html += '</span>';
        html += '</div>';
    });
    tree.innerHTML = html;
}

function renderEditorTabs() {
    var tabs = document.getElementById('editorTabs');
    var filenames = Object.keys(openFiles);
    if (filenames.length === 0) {
        tabs.innerHTML = '';
        return;
    }

    var html = '';
    filenames.forEach(function(fname) {
        var isActive = fname === activeFile;
        html += '<div class="editor-tab' + (isActive ? ' active' : '') + '" data-file="' + escapeHtmlAttr(fname) + '" onclick="switchEditorTab(\'' + escapeHtmlAttr(fname) + '\')">';
        html += '<span class="editor-tab-name">' + escapeHtml(fname) + '</span>';
        html += '<span class="editor-tab-close" onclick="closeEditorTab(event,\'' + escapeHtmlAttr(fname) + '\')">×</span>';
        html += '</div>';
    });
    tabs.innerHTML = html;
}

function openFileInEditor(filename) {
    if (activeFile === filename) return;

    // 保存当前文件内容
    if (editor && activeFile && openFiles[activeFile]) {
        openFiles[activeFile].content = editor.getValue();
    }

    // 加载目标文件
    if (openFiles[filename]) {
        activeFile = filename;
        if (editor) editor.setValue(openFiles[filename].content);
        renderFileTree();
        renderEditorTabs();
    }
}

function switchEditorTab(filename) {
    openFileInEditor(filename);
}

function closeEditorTab(event, filename) {
    event.stopPropagation();

    // 检查是否有未保存内容
    if (openFiles[filename] && openFiles[filename].dirty) {
        if (!confirm('文件「' + filename + '」有未保存的更改，确定关闭？')) return;
    }

    delete openFiles[filename];

    if (activeFile === filename) {
        var remaining = Object.keys(openFiles);
        if (remaining.length > 0) {
            activeFile = remaining[0];
            if (editor) editor.setValue(openFiles[activeFile].content);
        } else {
            activeFile = '';
            if (editor) editor.setValue('');
        }
    }

    renderFileTree();
    renderEditorTabs();
}

function createNewFile() {
    if (!currentProjectName) {
        showToast('请先加载或创建项目', 'warning');
        return;
    }
    document.getElementById('createFileModal').classList.remove('hidden');
    document.getElementById('overlay').classList.remove('hidden');
    document.getElementById('newFileNameInput').value = '';
    setTimeout(function() {
        document.getElementById('newFileNameInput').focus();
    }, 100);
}

function closeCreateFileModal() {
    document.getElementById('createFileModal').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');
}

function confirmCreateFile() {
    var input = document.getElementById('newFileNameInput');
    var name = (input.value || '').trim();
    if (!name) {
        showToast('请输入文件名', 'warning');
        return;
    }

    fetch(API_BASE + '/api/projects/' + encodeURIComponent(currentProjectName) + '/files', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, content: '' })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        closeCreateFileModal();
        // 重新加载项目文件列表
        refreshProjectFiles();
        showToast('文件 ' + data.name + ' 已创建', 'success');
    })
    .catch(function() { showToast('创建失败', 'error'); });
}

function deleteFilePrompt(filename) {
    fileToDelete = filename;
    document.getElementById('deleteFileName').textContent = filename;
    document.getElementById('deleteFileModal').classList.remove('hidden');
    document.getElementById('overlay').classList.remove('hidden');
}

function closeDeleteFileModal() {
    document.getElementById('deleteFileModal').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');
    fileToDelete = null;
}

function confirmDeleteFile() {
    if (!fileToDelete) return;

    fetch(API_BASE + '/api/projects/' + encodeURIComponent(currentProjectName) + '/files/' + encodeURIComponent(fileToDelete), {
        method: 'DELETE'
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        closeDeleteFileModal();
        // 从本地状态中移除
        delete openFiles[fileToDelete];
        if (activeFile === fileToDelete) {
            var remaining = Object.keys(openFiles);
            activeFile = remaining.length > 0 ? remaining[0] : '';
            if (activeFile && editor) editor.setValue(openFiles[activeFile].content);
            else if (editor) editor.setValue('');
        }
        refreshProjectFiles();
        showToast('文件已删除', 'success');
    })
    .catch(function() { showToast('删除失败', 'error'); });
}

function refreshProjectFiles() {
    if (!currentProjectName) return;

    fetch(API_BASE + '/api/projects/' + encodeURIComponent(currentProjectName))
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) return;
        projectFiles = data.files || [];
        // 更新 openFiles，保留已在内存中的内容
        projectFiles.forEach(function(f) {
            if (!openFiles[f.name]) {
                openFiles[f.name] = { content: f.content, dirty: false };
            }
        });
        // 如果当前没有活跃文件，默认打开第一个
        if (!activeFile && projectFiles.length > 0) {
            activeFile = projectFiles[0].name;
            if (editor) editor.setValue(openFiles[activeFile].content);
        }
        renderFileTree();
        renderEditorTabs();
    })
    .catch(function() {});
}

// ==================== 项目管理（重写） ====================

function saveCurrentProject() {
    if (!currentProjectName) {
        var name = prompt('请输入项目名称：','');
        if (!name) return;
        currentProjectName = name;
        updateProjectNameDisplay();
        try { localStorage.setItem(PROJECT_KEY, name); } catch(e) {}
    }

    // 保存当前编辑的文件内容
    if (editor && activeFile && openFiles[activeFile]) {
        openFiles[activeFile].content = editor.getValue();
        openFiles[activeFile].dirty = false;
    }

    // 收集所有文件
    var files = [];
    Object.keys(openFiles).forEach(function(fname) {
        files.push({ name: fname, content: openFiles[fname].content });
    });

    fetch(API_BASE + '/api/projects/' + encodeURIComponent(currentProjectName), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: files })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            showToast('项目「' + currentProjectName + '」已保存', 'success');
            updateAutoSaveLabel('已保存');
        } else {
            showToast('保存失败', 'error');
        }
    })
    .catch(function() {
        showToast('保存失败，请检查服务器', 'error');
    });
}

function openProjectsModal() {
    document.getElementById('projectsModal').classList.remove('hidden');
    document.getElementById('overlay').classList.remove('hidden');
    loadProjectList();
}

function closeProjectsModal() {
    document.getElementById('projectsModal').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');
}

function loadProjectList() {
    fetch(API_BASE + '/api/projects')
    .then(function(r) { return r.json(); })
    .then(function(data) {
        var list = document.getElementById('projectsList');
        var projects = data.projects || [];
        if (projects.length === 0) {
            list.innerHTML = '<div class="projects-empty">暂无项目。点击"新建项目"开始！</div>';
            return;
        }
        var html = '';
        projects.forEach(function(p) {
            var date = new Date(p.updated_at * 1000);
            var timeStr = date.toLocaleString('zh-CN');
            html += '<div class="project-item">';
            html += '<div class="project-item-info">';
            html += '<span class="project-item-name">' + escapeHtml(p.name) + '</span>';
            html += '<span class="project-item-time">' + timeStr + ' · ' + (p.file_count || 0) + ' 个文件</span>';
            html += '</div>';
            html += '<div class="project-item-actions">';
            html += '<button class="btn btn-small" onclick="loadProject(\'' + escapeHtmlAttr(p.name) + '\')">打开</button>';
            html += '<button class="btn btn-small btn-danger" onclick="deleteProject(\'' + escapeHtmlAttr(p.name) + '\')">删除</button>';
            html += '</div>';
            html += '</div>';
        });
        list.innerHTML = html;
    })
    .catch(function() {
        document.getElementById('projectsList').innerHTML = '<div class="projects-empty">加载失败，请检查服务器</div>';
    });
}

function newProject() {
    if (!confirm('新建项目将关闭当前项目，是否继续？')) return;

    currentProjectName = '';
    openFiles = {};
    activeFile = 'main.light';
    projectFiles = [];
    updateProjectNameDisplay();
    try { localStorage.removeItem(PROJECT_KEY); } catch(e) {}

    // 创建默认 main.light
    openFiles['main.light'] = { content: getDefaultCode(), dirty: false };
    if (editor) editor.setValue(getDefaultCode());
    renderFileTree();
    renderEditorTabs();
    closeProjectsModal();
    showToast('已创建新项目', 'info');
}

function loadProject(name) {
    fetch(API_BASE + '/api/projects/' + encodeURIComponent(name))
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            showToast('加载失败: ' + data.error, 'error');
            return;
        }

        currentProjectName = name;
        updateProjectNameDisplay();
        try { localStorage.setItem(PROJECT_KEY, name); } catch(e) {}

        projectFiles = data.files || [];
        openFiles = {};

        // 加载所有文件
        projectFiles.forEach(function(f) {
            openFiles[f.name] = { content: f.content, dirty: false };
        });

        // 打开入口文件
        if (projectFiles.length > 0) {
            activeFile = data.entry || projectFiles[0].name;
            if (openFiles[activeFile]) {
                if (editor) editor.setValue(openFiles[activeFile].content);
            }
        } else {
            activeFile = 'main.light';
            openFiles['main.light'] = { content: getDefaultCode(), dirty: false };
            if (editor) editor.setValue(getDefaultCode());
        }

        renderFileTree();
        renderEditorTabs();
        closeProjectsModal();
        // 切换到文件侧边栏
        switchSidebarTab('files');
        showToast('已加载项目「' + name + '」（' + projectFiles.length + ' 个文件）', 'success');
    })
    .catch(function() {
        showToast('加载失败，请检查服务器', 'error');
    });
}

function deleteProject(name) {
    if (!confirm('确定要删除项目「' + name + '」吗？此操作不可恢复。')) return;
    fetch(API_BASE + '/api/projects/' + encodeURIComponent(name), {
        method: 'DELETE'
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            if (currentProjectName === name) {
                currentProjectName = '';
                openFiles = {};
                activeFile = 'main.light';
                projectFiles = [];
                updateProjectNameDisplay();
                renderFileTree();
                renderEditorTabs();
                try { localStorage.removeItem(PROJECT_KEY); } catch(e) {}
            }
            showToast('项目「' + name + '」已删除', 'success');
            loadProjectList();
        }
    })
    .catch(function() {
        showToast('删除失败', 'error');
    });
}

function updateProjectNameDisplay() {
    var el = document.getElementById('projectNameDisplay');
    if (!el) return;
    if (currentProjectName) {
        el.textContent = currentProjectName;
        el.style.color = 'var(--accent-green)';
        el.title = '已保存项目';
    } else {
        el.textContent = '未命名项目';
        el.style.color = 'var(--text-muted)';
        el.title = '点击保存按钮命名项目';
    }
}

// ==================== 本地文件导入/导出 ====================

function downloadCode() {
    var code = '';
    if (editor && activeFile && openFiles[activeFile]) {
        code = editor.getValue();
    }
    var filename = activeFile || 'light_code.light';
    var blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('已下载 ' + filename, 'success');
}

function uploadCode() {
    document.getElementById('fileInput').click();
}

document.addEventListener('DOMContentLoaded', function() {
    var fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            var file = e.target.files[0];
            if (!file) return;
            var reader = new FileReader();
            reader.onload = function(ev) {
                var name = file.name.replace(/\.light$/,'').replace(/\.txt$/,'').replace(/\.text$/,'');
                var content = ev.target.result;
                // 如果已有项目，添加为项目文件
                if (currentProjectName) {
                    openFiles[file.name] = { content: content, dirty: true };
                    activeFile = file.name;
                    if (editor) editor.setValue(content);
                    renderFileTree();
                    renderEditorTabs();
                    // 保存到服务器
                    saveCurrentProject();
                } else {
                    currentProjectName = name;
                    openFiles = {};
                    openFiles[file.name] = { content: content, dirty: false };
                    activeFile = file.name;
                    projectFiles = [{ name: file.name, content: content }];
                    if (editor) editor.setValue(content);
                    updateProjectNameDisplay();
                    try { localStorage.setItem(PROJECT_KEY, name); } catch(e) {}
                    renderFileTree();
                    renderEditorTabs();
                    switchSidebarTab('files');
                }
                showToast('已打开文件: ' + file.name, 'success');
            };
            reader.readAsText(file, 'utf-8');
            fileInput.value = '';
        });
    }
});

// ==================== 主题 ====================

function applyTheme(theme) {
    document.body.dataset.theme = theme;
    if (editor && monaco && monaco.editor) {
        monaco.editor.setTheme(theme === 'dark' ? 'vs-dark' : 'vs');
    }
}

document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runCode();
    }

    if (e.key === 'Escape') {
        closeShareModal();
        closeGrammarModal();
        closeStdlibModal();
        closeProjectsModal();
        closeCreateFileModal();
        closeDeleteFileModal();
    }

    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        if (currentProjectName) {
            saveCurrentProject();
        } else {
            saveCode();
            showToast('代码已保存到浏览器', 'success');
        }
    }
});

function showToast(message, type) {
    type = type || 'info';
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(function() { toast.remove(); }, 300);
    }, 2500);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeHtmlAttr(text) {
    return text.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
