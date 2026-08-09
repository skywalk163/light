/**
 * 光明 (Light) Web Playground - 前端逻辑
 */

// =============================================================================
// 状态
// =============================================================================

let editor = null;
let currentExampleId = null;
let isSidebarOpen = false;

// API 基础路径
const API_BASE = '';

// =============================================================================
// 示例库 — 独立加载，不依赖 Monaco
// =============================================================================

// 立即加载示例
loadExamples();

// 检查是否有分享 ID
const params = new URLSearchParams(window.location.search);
const shareId = params.get('share');
if (shareId) {
    loadSharedCode(shareId);
}

// =============================================================================
// Monaco Editor 初始化（使用 jsdelivr CDN，国内可访问）
// =============================================================================

require.config({
    paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }
});

require(['vs/editor/editor.main'], function () {
    // 定义光明语法的基本高亮
    monaco.languages.register({ id: 'light' });

    monaco.languages.setMonarchTokensProvider('light', {
        defaultToken: '',
        tokenPostfix: '.light',

        keywords: [
            '定义', '常量', '等于',
            '如果', '那么', '否则', '否则若',
            '遍历', '当', '跳出', '跳过',
            '段', '返回', '结束',
            '导入', '导出', '从',
            '且', '或', '非',
            '真', '假', '空',
            '打印', '输出'
        ],

        typeKeywords: [
            '数', '整数', '浮数', '串', '列', '典', '集', '布尔', '空', '任意'
        ],

        operators: [
            '加', '减', '乘', '除', '模', '幂',
            '大于', '小于', '不等于', '大于等于', '小于等于'
        ],

        tokenizer: {
            root: [
                // 注释
                [/```注释[\s\S]*?```/, 'comment'],
                [/#.*$/, 'comment'],

                // 字符串
                [/"[^"]*"/, 'string'],
                [/'[^']*'/, 'string'],
                [/「[^」]*」/, 'string'],

                // 书名号（段落名）
                [/《[^》]*》/, { token: 'custom-function', bracket: '@open' }],

                // 方括号（篇名/列表）
                [/【[^】]*】/, 'type'],
                [/[【】\[\]]/, '@brackets'],

                // 数字
                [/\d+\.\d+/, 'number.float'],
                [/\d+/, 'number'],

                // 关键字
                [
                    /[^\s《》【】\(\)（）,，。.：:；;]+/,
                    {
                        cases: {
                            '@keywords': 'keyword',
                            '@typeKeywords': 'type',
                            '@operators': 'operator',
                            '@default': 'identifier'
                        }
                    }
                ],

                // 标点
                [/[。.]/, 'delimiter'],
                [/[，,]/, 'delimiter'],
                [/[：:]/, 'delimiter'],
                [/[；;]/, 'delimiter'],
                [/[\(\)（）]/, '@brackets'],
            ]
        }
    });

    // 创建编辑器
    editor = monaco.editor.create(document.getElementById('editor'), {
        value: getDefaultCode(),
        language: 'light',
        theme: 'vs-dark',
        fontSize: 14,
        lineHeight: 22,
        fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', Consolas, monospace",
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        padding: { top: 12, bottom: 12 },
        automaticLayout: true,
        tabSize: 2,
        insertSpaces: true,
        wordWrap: 'on',
        renderWhitespace: 'selection',
        bracketPairColorization: { enabled: true },
        lineNumbersMinChars: 3,
        glyphMargin: false,
        folding: true,
        suggest: {
            showKeywords: true,
            showTypes: true
        }
    });

    // Mark Monaco as loaded
    window._monacoReady = true;
});

// Monaco 加载超时回退（5秒后如果 Monaco 未就绪，使用 textarea）
setTimeout(function() {
    if (!window._monacoReady) {
        const container = document.getElementById('editor');
        if (container && !container.querySelector('textarea')) {
            const fallback = document.createElement('textarea');
            fallback.className = 'fallback-editor';
            fallback.value = getDefaultCode();
            fallback.style.cssText = 'width:100%;height:100%;background:#1e1e1e;color:#d4d4d4;border:none;padding:16px;font-family:Consolas,monospace;font-size:14px;line-height:1.6;resize:none;outline:none;tab-size:2';
            container.appendChild(fallback);

            // 提供 getValue / setValue 接口兼容
            editor = {
                getValue: function() { return fallback.value; },
                setValue: function(v) { fallback.value = v; }
            };
        }
    }
}, 5000);

// =============================================================================
// 获取默认代码
// =============================================================================

function getDefaultCode() {
    return `# 欢迎使用光明 (Light) Playground！
# 试试运行这段代码 👇

定义甲等于10。
定义乙等于20。

打印("甲 + 乙 = "加甲加乙)。

如果甲大于乙那么:
  打印("甲更大")。
否则:
  打印("乙更大")。
结束。

# 定义段落
《平方》段(数值):
  返回数值乘数值。
结束。

打印("5 的平方 = "加《平方》(5))。
`;
}

// =============================================================================
// 运行代码
// =============================================================================

function runCode() {
    const code = editor.getValue();
    if (!code.trim()) {
        showToast('请输入代码', 'warning');
        return;
    }

    const runBtn = document.getElementById('runBtn');
    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="spinner"></span> 运行中...';

    document.getElementById('outputPanel').innerHTML = '';
    document.getElementById('astPanel').innerHTML = '';
    document.getElementById('tokensPanel').innerHTML = '';

    // 同时执行、解析、词法分析
    Promise.all([
        fetch(`${API_BASE}/api/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        }).then(r => r.json()),
        fetch(`${API_BASE}/api/parse`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        }).then(r => r.json()),
        fetch(`${API_BASE}/api/tokenize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        }).then(r => r.json())
    ]).then(([execResult, parseResult, tokenResult]) => {
        // 输出面板
        renderOutput(execResult);

        // AST 面板
        renderAST(parseResult);

        // Token 面板
        renderTokens(tokenResult);
    }).catch(err => {
        document.getElementById('outputPanel').innerHTML =
            `<div class="output-line error">网络错误: ${err.message}</div>`;
    }).finally(() => {
        runBtn.disabled = false;
        runBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M4 2.5v11l9-5.5-9-5.5z"/>
            </svg>
            运行
        `;
    });
}

// =============================================================================
// 渲染输出
// =============================================================================

function renderOutput(result) {
    const panel = document.getElementById('outputPanel');

    if (result.success) {
        const lines = result.output.split('\n');
        panel.innerHTML = lines.map(line => {
            const cls = line.startsWith('错误') || line.startsWith('Error') ? 'error'
                     : line.startsWith('成功') ? 'success'
                     : '';
            return `<div class="output-line ${cls}">${escapeHtml(line)}</div>`;
        }).join('');
    } else {
        panel.innerHTML = `<div class="output-line error">${escapeHtml(result.error)}</div>`;
    }

    switchTab('output');
}

// =============================================================================
// 渲染 AST
// =============================================================================

function renderAST(result) {
    const panel = document.getElementById('astPanel');

    if (!result.success) {
        panel.innerHTML = `<div class="output-line error">${escapeHtml(result.error)}</div>`;
        return;
    }

    let html = '<table class="ast-table"><thead><tr><th>段落</th><th>参数</th><th>返回类型</th></tr></thead><tbody>';

    if (result.segments && result.segments.length > 0) {
        result.segments.forEach(seg => {
            const params = seg.parameters.join(', ') || '(无)';
            const ret = seg.return_type || '-';
            html += `<tr>
                <td class="ast-segment">《${escapeHtml(seg.name)}》</td>
                <td>${escapeHtml(params)}</td>
                <td>${escapeHtml(ret)}</td>
            </tr>`;
        });
    } else {
        html += '<tr><td colspan="3" style="color: var(--text-muted)">(未定义段落)</td></tr>';
    }

    html += `</tbody></table>
             <div style="margin-top: 8px; font-size: 12px; color: var(--text-muted);">
                 语句: ${result.statement_count} &nbsp;|&nbsp; 导入: ${result.import_count} &nbsp;|&nbsp; 导出: ${result.export_count}
             </div>`;

    panel.innerHTML = html;
}

// =============================================================================
// 渲染 Token
// =============================================================================

function renderTokens(result) {
    const panel = document.getElementById('tokensPanel');

    if (!result.success) {
        panel.innerHTML = `<div class="output-line error">${escapeHtml(result.error)}</div>`;
        return;
    }

    if (result.errors && result.errors.length > 0) {
        panel.innerHTML = result.errors.map(e =>
            `<div class="output-line error">${escapeHtml(e)}</div>`
        ).join('') + '<br>';
    }

    let html = `<div style="margin-bottom: 8px; font-size: 12px; color: var(--text-muted);">
        共 ${result.token_count} 个 Token
    </div>`;

    html += '<table class="token-table"><thead><tr><th>类型</th><th>文本</th><th>位置</th></tr></thead><tbody>';

    result.tokens.forEach(t => {
        html += `<tr>
            <td class="token-type">${escapeHtml(t.type)}</td>
            <td class="token-text">${escapeHtml(t.text)}</td>
            <td class="token-loc">${t.line}:${t.column}</td>
        </tr>`;
    });

    html += '</tbody></table>';
    panel.innerHTML = html;
}

// =============================================================================
// 示例管理
// =============================================================================

function loadExamples() {
    fetch(`${API_BASE}/api/examples`)
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('exampleList');
            list.innerHTML = data.examples.map(ex => `
                <div class="example-item" data-id="${ex.id}" onclick="loadExample('${ex.id}')">
                    <div class="example-item-title">${escapeHtml(ex.title)}</div>
                    <div class="example-item-desc">${escapeHtml(ex.description)}</div>
                </div>
            `).join('');
        })
        .catch(err => {
            document.getElementById('exampleList').innerHTML =
                `<div class="example-loading">加载失败: ${err.message}</div>`;
        });
}

function loadExample(exampleId) {
    fetch(`${API_BASE}/api/examples/${exampleId}`)
        .then(r => r.json())
        .then(ex => {
            if (ex.error) {
                showToast(ex.error, 'error');
                return;
            }
            editor.setValue(ex.code);
            currentExampleId = exampleId;

            // 高亮当前示例
            document.querySelectorAll('.example-item').forEach(el => {
                el.classList.toggle('active', el.dataset.id === exampleId);
            });

            // 移动端自动关闭侧边栏
            if (window.innerWidth <= 768) {
                toggleExamples();
            }
        })
        .catch(err => showToast('加载示例失败', 'error'));
}

// =============================================================================
// 侧边栏切换
// =============================================================================

function toggleExamples() {
    isSidebarOpen = !isSidebarOpen;
    document.getElementById('sidebar').classList.toggle('closed', !isSidebarOpen);
}

// =============================================================================
// 语法参考（全页弹窗）
// =============================================================================

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

function closeModals() {
    closeShareModal();
    closeGrammarModal();
}

function loadGrammar() {
    if (_grammarLoaded) return;
    _grammarLoaded = true;

    const panel = document.getElementById('grammarModalBody');
    panel.innerHTML = '<div class="grammar-loading">📖 加载语法参考中...</div>';

    fetch(API_BASE + '/api/grammar')
        .then(r => {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(data => {
            renderGrammar(data.categories);
        })
        .catch(err => {
            panel.innerHTML = `<div class="output-line error">加载失败: ${err.message}</div>`;
            _grammarLoaded = false;
        });
}

function renderGrammar(categories) {
    const panel = document.getElementById('grammarModalBody');

    let html = `
        <div class="grammar-intro">
            <p>快速入门光明编程语言的语法，适合新手查阅。点击「示例」可加载对应代码体验。</p>
        </div>
    `;

    categories.forEach(cat => {
        html += `<div class="grammar-category">`;
        html += `<h4 class="grammar-cat-title">${cat.category}</h4>`;
        html += `<div class="grammar-items">`;

        cat.items.forEach(item => {
            html += `<div class="grammar-item">`;
            // 处理多行语法
            const syntaxLines = item.syntax.split('\n');
            html += `<div class="grammar-syntax">`;
            syntaxLines.forEach(line => {
                html += `<code>${escapeHtml(line)}</code>`;
            });
            html += `</div>`;
            if (item.description) {
                html += `<div class="grammar-desc">${item.description}</div>`;
            }
            if (item.example) {
                html += `<div class="grammar-example">例: ${escapeHtml(item.example)}</div>`;
            }
            html += `</div>`;
        });

        html += `</div></div>`;
    });

    panel.innerHTML = html;
}

// =============================================================================
// Tab 切换
// =============================================================================

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.output-panel').forEach(p => p.classList.add('hidden'));

    const tabEl = document.querySelector(`.tab[data-tab="${tabName}"]`);
    if (tabEl) tabEl.classList.add('active');
    document.getElementById(`${tabName}Panel`).classList.remove('hidden');
}

// =============================================================================
// 清除输出
// =============================================================================

function clearOutput() {
    document.getElementById('outputPanel').innerHTML =
        `<div class="output-placeholder">输出已清除</div>`;
    document.getElementById('astPanel').innerHTML =
        `<div class="output-placeholder">输出已清除</div>`;
    document.getElementById('tokensPanel').innerHTML =
        `<div class="output-placeholder">输出已清除</div>`;
    showToast('输出已清除', 'info');
}

// =============================================================================
// 分享功能
// =============================================================================

function shareCode() {
    const code = editor.getValue();
    if (!code.trim()) {
        showToast('没有可分享的代码', 'warning');
        return;
    }

    const shareBtn = document.getElementById('shareBtn');
    shareBtn.disabled = true;

    fetch(`${API_BASE}/api/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const url = `${window.location.origin}${window.location.pathname}?share=${data.share_id}`;
            document.getElementById('shareUrlInput').value = url;
            document.getElementById('shareModal').classList.remove('hidden');
            document.getElementById('overlay').classList.remove('hidden');
        } else {
            showToast(data.error || '分享失败', 'error');
        }
    })
    .catch(err => showToast('网络错误: ' + err.message, 'error'))
    .finally(() => {
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
    navigator.clipboard.writeText(input.value).then(() => {
        showToast('链接已复制到剪贴板', 'success');
    }).catch(() => {
        document.execCommand('copy');
        showToast('链接已复制', 'success');
    });
}

function loadSharedCode(shareId) {
    fetch(`${API_BASE}/api/share/${shareId}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }
            editor.setValue(data.code);
            showToast('已加载分享的代码', 'success');
        })
        .catch(err => showToast('加载分享代码失败', 'error'));
}

// =============================================================================
// 键盘快捷键
// =============================================================================

document.addEventListener('keydown', function(e) {
    // Ctrl+Enter / Cmd+Enter 运行
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runCode();
    }

    // Escape 关闭弹窗
    if (e.key === 'Escape') {
        closeShareModal();
        closeGrammarModal();
    }
});

// =============================================================================
// Toast 通知
// =============================================================================

function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// =============================================================================
// 工具函数
// =============================================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}