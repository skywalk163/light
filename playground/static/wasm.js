/**
 * 光明 (Light) WebAssembly 浏览器运行时 v4.1
 * 在 Playground 中提供客户端 WASM 执行模式
 */

let wasmRuntime = null;
let wasmMode = false;

// 检查是否启用 WASM 模式
const wasmEnabled = localStorage.getItem('light_wasm_mode') === 'true';

async function initWasmRuntime() {
    if (wasmRuntime) return wasmRuntime;

    const statusEl = document.getElementById('wasmStatus');
    if (statusEl) {
        statusEl.textContent = '⏳ 加载 Pyodide...';
        statusEl.className = 'wasm-status loading';
    }

    try {
        // 动态加载 Pyodide
        if (typeof loadPyodide === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js';
            document.head.appendChild(script);
            await new Promise((resolve, reject) => {
                script.onload = resolve;
                script.onerror = () => reject(new Error('Pyodide 脚本加载失败'));
            });
        }

        wasmRuntime = await loadPyodide({
            indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/'
        });

        if (statusEl) {
            statusEl.textContent = '✅ WASM 就绪';
            statusEl.className = 'wasm-status ready';
        }

        console.log('Light WASM runtime ready');
        return wasmRuntime;
    } catch (e) {
        if (statusEl) {
            statusEl.textContent = '❌ 加载失败';
            statusEl.className = 'wasm-status error';
        }
        console.error('Light WASM init failed:', e);
        throw e;
    }
}

async function runLightWasm(pythonCode) {
    if (!wasmRuntime) {
        await initWasmRuntime();
    }

    let output = '';
    wasmRuntime.setStdout({
        batched: (text) => { output += text + '\n'; }
    });
    wasmRuntime.setStderr({
        batched: (text) => { output += '⚠ ' + text + '\n'; }
    });

    try {
        await wasmRuntime.runPythonAsync(pythonCode);
        return { success: true, output: output.trim() };
    } catch (e) {
        return { success: false, error: e.message, output: output.trim() };
    }
}

async function executeWasm(source) {
    const outputEl = document.getElementById('outputPanel');
    if (outputEl) {
        outputEl.innerHTML = '<div class="output-loading">⏳ WASM 模式执行中...</div>';
    }

    try {
        // 先通过服务器编译光明代码为 Python
        const resp = await fetch(API_BASE + '/api/demos/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: source, target: 'python' })
        });
        const data = await resp.json();

        if (data.error) {
            if (outputEl) {
                outputEl.innerHTML = `<div class="output-error">
                    <div class="output-error-title">❌ 编译错误</div>
                    <pre>${escapeHtml(data.error)}</pre>
                </div>`;
            }
            return;
        }

        const pythonCode = data.python || '';
        const result = await runLightWasm(pythonCode);

        if (result.success) {
            if (outputEl) {
                outputEl.innerHTML = `<div class="output-success">
                    <div class="output-wasm-badge">⚡ WebAssembly</div>
                    <pre>${escapeHtml(result.output || '(无输出)')}</pre>
                </div>`;
            }
        } else {
            if (outputEl) {
                outputEl.innerHTML = `<div class="output-error">
                    <div class="output-error-title">❌ 运行时错误</div>
                    <pre>${escapeHtml(result.error || '未知错误')}</pre>
                    ${result.output ? `<pre class="output-stderr">${escapeHtml(result.output)}</pre>` : ''}
                </div>`;
            }
        }
    } catch (e) {
        if (outputEl) {
            outputEl.innerHTML = `<div class="output-error">
                <div class="output-error-title">❌ WASM 执行失败</div>
                <pre>${escapeHtml(e.message)}</pre>
            </div>`;
        }
    }
}

function toggleWasmMode() {
    wasmMode = !wasmMode;
    localStorage.setItem('light_wasm_mode', wasmMode ? 'true' : 'false');

    const btn = document.getElementById('wasmToggleBtn');
    const statusEl = document.getElementById('wasmStatus');

    if (wasmMode) {
        if (btn) btn.classList.add('active');
        if (statusEl) statusEl.style.display = 'inline';
        // 尝试初始化 WASM
        initWasmRuntime().catch(() => {});
        showToast('已切换到 WebAssembly 模式（浏览器端执行）', 'info');
    } else {
        if (btn) btn.classList.remove('active');
        if (statusEl) statusEl.style.display = 'none';
        showToast('已切换到服务器模式', 'info');
    }
}

// 页面加载时恢复 WASM 模式
if (wasmEnabled) {
    wasmMode = true;
    // 延迟初始化，等 DOM 加载完成
    setTimeout(() => {
        const btn = document.getElementById('wasmToggleBtn');
        if (btn) btn.classList.add('active');
        const statusEl = document.getElementById('wasmStatus');
        if (statusEl) statusEl.style.display = 'inline';
        initWasmRuntime().catch(() => {});
    }, 2000);
}