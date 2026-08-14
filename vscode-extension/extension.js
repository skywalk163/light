// 光明 VSCode 扩展入口
const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

// =============================================================================
// 欢迎页 / 首次运行
// =============================================================================

const EXTENSION_VERSION = '7.0.0';
const WELCOME_SHOWN_KEY = 'light.welcomeShown';

function showWelcomePage(context) {
    const panel = vscode.window.createWebviewPanel(
        'lightWelcome',
        '欢迎使用光明编程语言',
        vscode.ViewColumn.One,
        { enableScripts: true }
    );

    panel.webview.html = getWelcomeHtml();
}

function getWelcomeHtml() {
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>欢迎使用光明</title>
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px 40px; max-width: 900px; margin: 0 auto; color: var(--vscode-editor-foreground); background: var(--vscode-editor-background); }
    h1 { font-size: 2.2em; border-bottom: 2px solid var(--vscode-textLink-foreground); padding-bottom: 10px; }
    h2 { font-size: 1.5em; margin-top: 30px; }
    .badge { display: inline-block; background: var(--vscode-textLink-foreground); color: #fff; padding: 2px 12px; border-radius: 12px; font-size: 0.9em; }
    .section { background: var(--vscode-sideBar-background); border-radius: 8px; padding: 16px 20px; margin: 12px 0; }
    code { background: var(--vscode-textCodeBlock-background); padding: 1px 6px; border-radius: 3px; font-size: 0.9em; }
    pre { background: var(--vscode-textCodeBlock-background); padding: 12px; border-radius: 6px; overflow-x: auto; }
    .steps { counter-reset: step; list-style: none; padding: 0; }
    .steps li { counter-increment: step; margin: 10px 0; padding: 10px 10px 10px 40px; position: relative; }
    .steps li::before { content: counter(step); position: absolute; left: 0; top: 10px; width: 26px; height: 26px; background: var(--vscode-textLink-foreground); color: #fff; border-radius: 50%; text-align: center; line-height: 26px; font-weight: bold; font-size: 0.9em; }
    .quick-links { display: flex; gap: 10px; flex-wrap: wrap; margin: 16px 0; }
    .quick-links a { flex: 1; min-width: 160px; text-align: center; padding: 12px; background: var(--vscode-button-background); color: var(--vscode-button-foreground); text-decoration: none; border-radius: 6px; font-weight: 500; }
    .quick-links a:hover { background: var(--vscode-button-hoverBackground); }
</style>
</head>
<body>
    <h1>欢迎使用光明 <span class="badge">v${EXTENSION_VERSION}</span></h1>
    <p>光明（LightLang）是一门面向中文母语者的编程语言，兼具 Python 的简洁与 Rust 的安全。</p>

    <div class="quick-links">
        <a href="#" onclick="vscode.postMessage({command:'newFile'})">📄 新建光明文件</a>
        <a href="#" onclick="vscode.postMessage({command:'openREPL'})">💻 打开 REPL</a>
        <a href="#" onclick="vscode.postMessage({command:'openHelp'})">📖 查看文档</a>
    </div>

    <h2>🚀 快速开始</h2>
    <ol class="steps">
        <li>新建一个 <code>.light</code> 文件，或打开已有的光明文件</li>
        <li>开始编写代码 —— 语法高亮、代码补全、实时诊断自动生效</li>
        <li>按 <code>Ctrl+Shift+R</code> 运行当前文件</li>
        <li>按 <code>Ctrl+Shift+B</code> 编译当前文件</li>
    </ol>

    <h2>📝 代码示例</h2>
    <pre>段落 主函数 接收 参数：
    打印("你好，光明！")
    定义 甲 等于 10
    定义 乙 等于 20
    设 结果 为 甲 加 乙
    打印("甲 + 乙 = " 加 结果)
结束。

主函数()</pre>

    <h2>✨ 核心特性</h2>
    <div class="section">
        <strong>🎨 中文关键字</strong> — 用中文编写代码，降低编程入门门槛
    </div>
    <div class="section">
        <strong>🔧 完整 IDE 支持</strong> — 语法高亮、自动补全、跳转定义、实时错误提示
    </div>
    <div class="section">
        <strong>⚡ 多后端编译</strong> — 支持 Python 解释执行和 LLVM 原生编译
    </div>
    <div class="section">
        <strong>🛡️ 类型系统</strong> — 可选静态类型检查，兼顾灵活与安全
    </div>

    <h2>📚 资源</h2>
    <ul>
        <li><a href="https://skywalk163.github.io/light">官方文档</a></li>
        <li><a href="https://github.com/skywalk163/light">GitHub 仓库</a></li>
        <li>在 VS Code 命令面板中搜索 <code>光明:</code> 查看所有可用命令</li>
    </ul>

    <p style="text-align:center; margin-top: 40px; opacity: 0.6;">光明 v${EXTENSION_VERSION} — 用中文，写世界</p>
</body>
</html>`;
}

function checkFirstRun(context) {
    const hasShown = context.globalState.get(WELCOME_SHOWN_KEY, false);
    if (!hasShown) {
        context.globalState.update(WELCOME_SHOWN_KEY, true);
        return true;
    }
    if (vscode.workspace.getConfiguration('light.welcome').get('alwaysShow', false)) {
        return true;
    }
    return false;
}

// =============================================================================
// 全局状态
// =============================================================================

/** @type {vscode.LanguageClient} */
let client = null;

/** @type {vscode.StatusBarItem} */
let statusBarItem = null;

/** @type {vscode.DiagnosticCollection} */
let diagnosticCollection = null;

/** @type {vscode.OutputChannel} */
let outputChannel = null;

// =============================================================================
// 工具函数
// =============================================================================

/**
 * 获取 Python 解释器路径
 */
function getPythonPath() {
    const configPath = vscode.workspace.getConfiguration('light').get('pythonPath');
    if (configPath && configPath.trim()) return configPath;
    return process.platform === 'win32' ? 'python' : 'python3';
}

/**
 * 获取项目根目录（light 源码目录）
 */
function getProjectRoot() {
    const extPath = vscode.extensions.getExtension('light-lang.light-language')?.extensionPath;
    if (extPath) {
        // 扩展目录在 vscode-extension/ 下，项目根目录是上一级
        const candidates = [
            path.join(extPath, '..'),
            path.join(extPath, '..', '..'),
        ];
        for (const p of candidates) {
            try {
                if (fs.existsSync(path.join(p, 'cli', 'light.py'))) {
                    return p;
                }
            } catch (_) {}
        }
    }
    // 默认：相对于工作区
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath;
    return workspaceRoot || '.';
}

/**
 * 在终端中执行光明 CLI 命令
 */
function runLightCommand(command, terminalName) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('没有打开的编辑器');
        return;
    }
    const filePath = editor.document.uri.fsPath;
    const projectRoot = getProjectRoot();
    const pythonCmd = getPythonPath();

    const terminal = vscode.window.createTerminal(terminalName || '光明');
    terminal.show();
    terminal.sendText(`cd "${projectRoot}" ; ${pythonCmd} -m cli.light ${command} "${filePath}"`);
}

/**
 * 获取当前光明文件路径
 */
function getActiveLightFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'light') {
        vscode.window.showInformationMessage('请打开一个光明 (.light) 文件');
        return null;
    }
    return editor.document.uri.fsPath;
}

/**
 * 格式化错误输出为 file:line:col: message 格式
 */
function formatErrorOutput(output) {
    const diagnostics = [];
    const lines = output.split('\n');
    for (const line of lines) {
        // 匹配常见错误格式: 文件:行:列: 消息
        const match = line.match(/^(.+?):(\d+):(\d+):\s*(.+)$/);
        if (match) {
            diagnostics.push({
                file: match[1],
                line: parseInt(match[2]) - 1,
                col: parseInt(match[3]) - 1,
                message: match[4]
            });
        }
    }
    return diagnostics;
}

// =============================================================================
// LSP 服务器管理
// =============================================================================

/**
 * 查找 LSP 服务器路径
 */
function findServerPath() {
    const configPath = vscode.workspace.getConfiguration('light').get('serverPath');
    if (configPath && configPath.trim()) return configPath;

    const projectRoot = getProjectRoot();
    const candidates = [
        path.join(projectRoot, 'lsp', 'light_lsp.py'),
        path.join(projectRoot, '..', 'lsp', 'light_lsp.py'),
    ];
    for (const p of candidates) {
        try {
            if (fs.existsSync(p)) return p;
        } catch (_) {}
    }
    return path.join(projectRoot, 'lsp', 'light_lsp.py');
}

/**
 * 启动 LSP 客户端
 */
function startLSP(context) {
    const serverPath = findServerPath();
    const pythonCmd = getPythonPath();

    outputChannel.appendLine(`[光明] 启动 LSP 服务器: ${pythonCmd} ${serverPath}`);

    const serverOptions = {
        command: pythonCmd,
        args: [serverPath],
        options: {
            cwd: path.dirname(serverPath),
        }
    };

    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'light' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.light')
        },
        outputChannel: outputChannel,
        traceOutputChannel: vscode.window.createOutputChannel('光明 LSP Trace'),
    };

    client = new vscode.LanguageClient(
        'light-lsp',
        '光明语言服务器',
        serverOptions,
        clientOptions
    );

    client.onDidChangeState(e => {
        if (e.newState === vscode.State.Running) {
            outputChannel.appendLine('[光明] LSP 服务器已启动');
            updateStatusBar('running');
        } else if (e.newState === vscode.State.Stopped) {
            outputChannel.appendLine('[光明] LSP 服务器已停止');
            updateStatusBar('offline');
        }
    });

    client.onReady().then(() => {
        updateStatusBar('running');
    }).catch(err => {
        outputChannel.appendLine(`[光明] LSP 启动失败: ${err.message}`);
        updateStatusBar('error');
    });

    context.subscriptions.push(client.start());
}

// =============================================================================
// 状态栏指示器
// =============================================================================

function createStatusBar(context) {
    statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.command = 'light.restartLSP';
    context.subscriptions.push(statusBarItem);
    updateStatusBar('offline');
}

function updateStatusBar(status) {
    if (!statusBarItem) return;
    switch (status) {
        case 'running':
            statusBarItem.text = `$(check) 光明 v${EXTENSION_VERSION}`;
            statusBarItem.tooltip = '光明语言服务运行中 - 点击重启';
            statusBarItem.backgroundColor = undefined;
            break;
        case 'error':
            statusBarItem.text = `$(error) 光明 v${EXTENSION_VERSION}`;
            statusBarItem.tooltip = '光明语言服务错误 - 点击重启';
            statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
            break;
        case 'offline':
        default:
            statusBarItem.text = `$(circle-slash) 光明 v${EXTENSION_VERSION}`;
            statusBarItem.tooltip = '光明语言服务离线 - 点击重启';
            statusBarItem.backgroundColor = undefined;
            break;
    }
    statusBarItem.show();
}

// =============================================================================
// 问题面板集成
// =============================================================================

function createDiagnosticCollection(context) {
    diagnosticCollection = vscode.languages.createDiagnosticCollection('light');
    context.subscriptions.push(diagnosticCollection);
}

/**
 * 运行 CLI 命令并将输出解析为诊断信息，输出到 Problems 面板
 */
function runCommandWithDiagnostics(command, args, sourceName) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    const filePath = editor.document.uri.fsPath;
    const projectRoot = getProjectRoot();
    const pythonCmd = getPythonPath();

    const fullArgs = ['-m', 'cli.light', command, filePath, ...args];
    const cwd = projectRoot;

    outputChannel.appendLine(`[光明] 执行: ${pythonCmd} ${fullArgs.join(' ')}`);

    exec(
        `"${pythonCmd}" ${fullArgs.map(a => `"${a}"`).join(' ')}`,
        { cwd, encoding: 'utf-8' },
        (error, stdout, stderr) => {
            const output = stderr || stdout || '';
            outputChannel.appendLine(`[光明] 输出: ${output.trim()}`);

            const uri = editor.document.uri;
            const diagnostics = [];

            // 解析错误输出
            const lines = output.split('\n');
            let currentLine = 0;
            let currentCol = 0;

            for (const line of lines) {
                // 格式: 文件:行:列: 消息
                const match = line.match(/^(.+?):(\d+):(\d+):\s*(.+)$/);
                if (match) {
                    const errLine = Math.max(0, parseInt(match[2]) - 1);
                    const errCol = Math.max(0, parseInt(match[3]) - 1);
                    diagnostics.push(new vscode.Diagnostic(
                        new vscode.Range(errLine, errCol, errLine, errCol + 1),
                        match[4],
                        vscode.DiagnosticSeverity.Error
                    ));
                }
                // 格式: 错误: 或 ❌ 开头的行
                else if (line.includes('错误') || line.includes('❌')) {
                    diagnostics.push(new vscode.Diagnostic(
                        new vscode.Range(currentLine, currentCol, currentLine, currentCol + 1),
                        line.trim(),
                        vscode.DiagnosticSeverity.Error
                    ));
                }
                // 格式: ⚠ 开头的行
                else if (line.includes('⚠') || line.includes('警告')) {
                    diagnostics.push(new vscode.Diagnostic(
                        new vscode.Range(currentLine, currentCol, currentLine, currentCol + 1),
                        line.trim(),
                        vscode.DiagnosticSeverity.Warning
                    ));
                }
            }

            diagnosticCollection.set(uri, diagnostics);

            if (diagnostics.length > 0) {
                outputChannel.appendLine(`[光明] ${sourceName}: 发现 ${diagnostics.length} 个问题`);
                outputChannel.show(true);
            } else if (!error) {
                vscode.window.showInformationMessage(`光明: ${sourceName}通过`);
            }
        }
    );
}

// =============================================================================
// Task Provider
// =============================================================================

class LightTaskProvider {
    constructor(projectRoot, pythonCmd) {
        this.projectRoot = projectRoot;
        this.pythonCmd = pythonCmd;
    }

    provideTasks() {
        const tasks = [];

        // 编译任务 (Ctrl+Shift+B)
        const compileTask = new vscode.Task(
            { type: 'light', task: 'compile' },
            vscode.TaskScope.Workspace,
            '光明: 编译当前文件',
            '光明',
            new vscode.ShellExecution(
                `"${this.pythonCmd}" -m cli.light compile "\${file}"`,
                { cwd: this.projectRoot }
            ),
            '$light'
        );
        compileTask.group = vscode.TaskGroup.Build;
        compileTask.problemMatchers = ['$light'];
        tasks.push(compileTask);

        // LLVM 编译任务
        const llvmTask = new vscode.Task(
            { type: 'light', task: 'compile-llvm' },
            vscode.TaskScope.Workspace,
            '光明: 编译当前文件 (LLVM-Typed)',
            '光明',
            new vscode.ShellExecution(
                `"${this.pythonCmd}" -m cli.light compile "\${file}" --backend llvm-typed`,
                { cwd: this.projectRoot }
            ),
            '$light'
        );
        llvmTask.group = vscode.TaskGroup.Build;
        llvmTask.problemMatchers = ['$light'];
        tasks.push(llvmTask);

        // 运行任务
        const runTask = new vscode.Task(
            { type: 'light', task: 'run' },
            vscode.TaskScope.Workspace,
            '光明: 运行当前文件',
            '光明',
            new vscode.ShellExecution(
                `"${this.pythonCmd}" -m cli.light run "\${file}"`,
                { cwd: this.projectRoot }
            ),
            '$light'
        );
        runTask.group = vscode.TaskGroup.Test;
        tasks.push(runTask);

        // 语法检查任务
        const checkTask = new vscode.Task(
            { type: 'light', task: 'check' },
            vscode.TaskScope.Workspace,
            '光明: 语法检查当前文件',
            '光明',
            new vscode.ShellExecution(
                `"${this.pythonCmd}" -m cli.light check "\${file}"`,
                { cwd: this.projectRoot }
            ),
            '$light'
        );
        checkTask.group = vscode.TaskGroup.Test;
        checkTask.problemMatchers = ['$light'];
        tasks.push(checkTask);

        return tasks;
    }

    resolveTask(task) {
        return task;
    }
}

// =============================================================================
// 补全提供器
// =============================================================================

class LightCompletionProvider {
    provideCompletionItems(document, position) {
        const items = [];

        // 关键字补全
        const keywords = [
            { label: '设', detail: '变量赋值', insertText: '设 ${1:变量名} 为 ${2:值}' },
            { label: '为', detail: '赋值关键字' },
            { label: '如果', detail: '条件判断', insertText: '如果 ${1:条件}：\n    ${2:代码}' },
            { label: '否则', detail: '否则分支', insertText: '否则：\n    ${1:代码}' },
            { label: '否则如果', detail: '否则如果分支', insertText: '否则如果 ${1:条件}：\n    ${2:代码}' },
            { label: '遍历', detail: '遍历循环', insertText: '遍历 ${1:项} 于 ${2:列表}：\n    ${3:代码}' },
            { label: '当', detail: '当循环', insertText: '当 ${1:条件}：\n    ${2:代码}' },
            { label: '段落', detail: '定义段落(函数)', insertText: '段落 ${1:名称} 接收 ${2:参数}：\n    ${3:代码}' },
            { label: '函数', detail: '定义函数', insertText: '函数 ${1:名称}(${2:参数})：\n    ${3:代码}' },
            { label: '返回', detail: '返回值', insertText: '返回 ${1:值}' },
            { label: '类', detail: '定义类', insertText: '类 ${1:名称}：\n    属性 ${2:属性名}\n\n    构造 接收 ${3:参数}：\n        己${2:属性名} 为 ${3:参数}\n\n    段落 ${4:方法名}()：\n        ${5:代码}' },
            { label: '继承', detail: '类继承' },
            { label: '属性', detail: '类属性声明' },
            { label: '构造', detail: '构造函数' },
            { label: '己', detail: '自身引用(self)' },
            { label: '父', detail: '父类引用(super)' },
            { label: '新建', detail: '创建对象实例', insertText: '新建 ${1:类名}(${2:参数})' },
            { label: '导入', detail: '导入模块', insertText: '导入《${1:模块名}》' },
            { label: '导出', detail: '导出符号', insertText: '导出 ${1:符号}' },
            { label: '从', detail: '从模块导入', insertText: '从《${1:模块名}》导入《${2:符号}》' },
            { label: '真', detail: '布尔值 true' },
            { label: '假', detail: '布尔值 false' },
            { label: '空', detail: '空值 None' },
            { label: '打印', detail: '输出到控制台', insertText: '打印(${1:值})' },
            { label: '尝试', detail: '异常捕获' },
            { label: '捕获', detail: '捕获异常' },
            { label: '抛出', detail: '抛出异常', insertText: '抛出 ${1:异常}' },
            { label: '跳出', detail: '跳出循环' },
            { label: '跳过', detail: '跳过当前迭代' },
            { label: '异步', detail: '异步函数' },
            { label: '等待', detail: 'await 表达式' },
            { label: '接口', detail: '定义接口' },
            { label: '实现', detail: '实现接口' },
            { label: '匹配', detail: '模式匹配', insertText: '匹配 ${1:值}：\n    情况 ${2:模式}：\n        ${3:代码}' },
            // 新增高优先级关键字
            { label: '使用', detail: '上下文管理器', insertText: '使用 ${1:表达式} 为 ${2:变量}：\n    ${3:代码}' },
            { label: '数据', detail: '定义数据/记录类型', insertText: '数据 ${1:名称}：\n    ${2:字段}: ${3:类型}' },
            { label: '枚举', detail: '定义枚举类型', insertText: '枚举 ${1:名称}：\n    ${2:变体}' },
            { label: '外部', detail: 'FFI 外部声明', insertText: '外部 段落 ${1:名称} 接收 ${2:参数} 返回 ${3:类型} 在 ${4:库}' },
            { label: '至', detail: '范围表达式（至）', insertText: '至 ${1:结束}' },
            { label: '到', detail: '范围表达式（到）', insertText: '到 ${1:结束}' },
            { label: '步', detail: '范围步长', insertText: '步 ${1:步长}' },
            { label: 'pass', detail: '空语句占位' },
            { label: '嵌入', detail: '嵌入代码块', insertText: '嵌入 Python：\n    ${1:代码}\n结束嵌入' },
            { label: '并', detail: '管道操作符', insertText: '并 ${1:段落}(${2:参数})' },
            { label: '标注', detail: '装饰器定义', insertText: '标注 ${1:段落名}\n段落 ${2:名称} 接收 ${3:参数}：\n    ${4:代码}' },
            // 新增中优先级关键字
            { label: '错误', detail: '定义错误类型', insertText: '错误 ${1:名称}：\n    ${2:字段}: ${3:类型}' },
            { label: 'trait', detail: '定义 Trait（接口集）', insertText: 'trait ${1:名称}：\n    ${2:方法}(${3:参数}) -> ${4:返回类型}' },
            { label: '类型别名', detail: '定义类型别名', insertText: '类型别名 ${1:名称} 为 ${2:目标类型}' },
            { label: '推迟', detail: '推迟执行（作用域退出时运行）', insertText: '推迟：\n    ${1:代码}' },
            { label: '并行', detail: '并行作用域（结构化并发）', insertText: '并行 {\n    ${1:任务1}\n    ${2:任务2}\n}' },
            { label: '开启类型检查', detail: '开启类型检查模式' },
            { label: '关闭类型检查', detail: '关闭类型检查模式' },
            // 新增低优先级 FFI 指针/内存操作关键字
            { label: '取地址', detail: 'FFI 取地址', insertText: '取地址(${1:变量})' },
            { label: '解引用', detail: 'FFI 解引用', insertText: '解引用(${1:指针})' },
            { label: '指针偏移', detail: 'FFI 指针偏移', insertText: '指针偏移(${1:指针}, ${2:偏移量})' },
            { label: '设置指针值', detail: 'FFI 通过指针写入值', insertText: '设置指针值(${1:指针}, ${2:值})' },
            { label: '分配内存', detail: 'FFI 分配内存', insertText: '分配内存(${1:大小})' },
            { label: '释放内存', detail: 'FFI 释放内存', insertText: '释放内存(${1:指针})' },
            { label: '创建数组', detail: 'FFI 创建数组', insertText: '创建数组 ${1:类型} [${2:大小}]' },
            { label: '设置数组', detail: 'FFI 设置数组元素', insertText: '设置数组(${1:数组}, ${2:索引}, ${3:值})' },
            { label: '获取FFI错误', detail: '获取最后的 FFI 错误' },
            { label: '获取系统错误码', detail: '获取系统错误码' },
        ];

        for (const kw of keywords) {
            const item = new vscode.CompletionItem(kw.label, vscode.CompletionItemKind.Keyword);
            item.detail = kw.detail;
            if (kw.insertText) {
                item.insertText = new vscode.SnippetString(kw.insertText);
            }
            item.range = document.getWordRangeAtPosition(position);
            items.push(item);
        }

        // 内置函数补全
        const builtins = [
            { label: '类型', detail: '获取值的类型', insertText: '类型(${1:值})' },
            { label: '长度', detail: '获取列表/字符串长度', insertText: '长度(${1:列表})' },
            { label: '转整数', detail: '转换为整数', insertText: '转整数(${1:值})' },
            { label: '转小数', detail: '转换为浮点数', insertText: '转小数(${1:值})' },
            { label: '转字符串', detail: '转换为字符串', insertText: '转字符串(${1:值})' },
            { label: '取整', detail: '向下取整', insertText: '取整(${1:值})' },
            { label: '绝对值', detail: '绝对值', insertText: '绝对值(${1:值})' },
            { label: '最大值', detail: '最大值', insertText: '最大值(${1:值}, ${2:值})' },
            { label: '最小值', detail: '最小值', insertText: '最小值(${1:值}, ${2:值})' },
            { label: '范围', detail: '生成范围', insertText: '范围(${1:开始}, ${2:结束})' },
            { label: '解析JSON', detail: '解析 JSON 字符串', insertText: '解析JSON(${1:字符串})' },
            { label: '序列化JSON', detail: '序列化为 JSON', insertText: '序列化JSON(${1:值})' },
            { label: '输入', detail: '读取用户输入', insertText: '输入(${1:提示})' },
        ];

        for (const fn of builtins) {
            const item = new vscode.CompletionItem(fn.label, vscode.CompletionItemKind.Function);
            item.detail = fn.detail;
            if (fn.insertText) {
                item.insertText = new vscode.SnippetString(fn.insertText);
            }
            items.push(item);
        }

        // 运算符补全
        const operators = [
            { label: '加', detail: '加法运算' },
            { label: '减', detail: '减法运算' },
            { label: '乘', detail: '乘法运算' },
            { label: '除', detail: '除法运算' },
            { label: '模', detail: '取模运算' },
            { label: '幂', detail: '幂运算' },
            { label: '大于', detail: '大于比较' },
            { label: '小于', detail: '小于比较' },
            { label: '等于', detail: '等于比较' },
            { label: '不等于', detail: '不等于比较' },
            { label: '大于等于', detail: '大于等于比较' },
            { label: '小于等于', detail: '小于等于比较' },
            { label: '且', detail: '逻辑与' },
            { label: '或', detail: '逻辑或' },
            { label: '非', detail: '逻辑非' },
            // 新增位运算符
            { label: '与', detail: '按位与运算' },
            { label: '异或', detail: '按位异或运算' },
            { label: '左移', detail: '按位左移' },
            { label: '右移', detail: '按位右移' },
            { label: '整除', detail: '整数除法' },
        ];

        for (const op of operators) {
            const item = new vscode.CompletionItem(op.label, vscode.CompletionItemKind.Operator);
            item.detail = op.detail;
            items.push(item);
        }

        return items;
    }
}

// =============================================================================
// 悬浮提示提供器
// =============================================================================

class LightHoverProvider {
    provideHover(document, position) {
        const wordRange = document.getWordRangeAtPosition(position);
        if (!wordRange) return null;

        const word = document.getText(wordRange);

        const hoverDocs = {
            '设': '### 设\n\n变量赋值语句。\n\n```\n设 变量名 为 值\n```\n\n示例：\n```\n设 甲 为 10\n设 姓名 为 "张三"\n```',
            '为': '### 为\n\n赋值关键字，与 `设` 配合使用。',
            '如果': '### 如果\n\n条件判断语句。\n\n```\n如果 条件：\n    代码\n否则如果 条件：\n    代码\n否则：\n    代码\n```',
            '否则': '### 否则\n\n条件判断的否则分支，与 `如果` 配合使用。',
            '否则如果': '### 否则如果\n\n多条件判断链，与 `如果` 配合使用。',
            '遍历': '### 遍历\n\n遍历循环，迭代列表中的每个元素。\n\n```\n遍历 项 于 列表：\n    代码\n```',
            '当': '### 当\n\n当循环，条件为真时重复执行。\n\n```\n当 条件：\n    代码\n```',
            '段落': '### 段落\n\n定义段落（函数）。\n\n```\n段落 名称 接收 参数：\n    代码\n    返回 值\n```',
            '函数': '### 函数\n\n定义函数（现代语法）。\n\n```\n函数 名称(参数)：\n    代码\n    返回 值\n```',
            '返回': '### 返回\n\n从段落（函数）中返回值。\n\n```\n返回 值\n```',
            '类': '### 类\n\n定义类。\n\n```\n类 类名：\n    属性 属性名\n    构造 接收 参数：\n        己属性名 为 参数\n    段落 方法名()：\n        代码\n```',
            '己': '### 己\n\n自身引用，等同于 Python 的 `self`。\n\n```\n己属性名\n己方法名()\n```',
            '父': '### 父\n\n父类引用，等同于 Python 的 `super()`。\n\n```\n父.构造(参数)\n```',
            '新建': '### 新建\n\n创建对象实例。\n\n```\n新建 类名(参数)\n```',
            '真': '### 真\n\n布尔值 `true`。',
            '假': '### 假\n\n布尔值 `false`。',
            '空': '### 空\n\n空值，等同于 Python 的 `None`。',
            '打印': '### 打印\n\n输出值到控制台。\n\n```\n打印("你好")\n打印(变量)\n打印("值：")打印(值)\n```',
            '导入': '### 导入\n\n导入模块。\n\n```\n导入《模块名》\n从《模块名》导入《符号》\n```',
            '导出': '### 导出\n\n声明模块的导出符号。\n\n```\n导出 符号一 符号二\n```',
            '跳出': '### 跳出\n\n跳出当前循环（等同于 Python 的 `break`）。',
            '跳过': '### 跳过\n\n跳过当前循环迭代（等同于 Python 的 `continue`）。',
            '尝试': '### 尝试\n\n异常捕获语句。\n\n```\n尝试：\n    代码\n捕获 异常变量：\n    处理代码\n```',
            '抛出': '### 抛出\n\n抛出异常。\n\n```\n抛出 异常值\n```',
            '匹配': '### 匹配\n\n模式匹配语句。\n\n```\n匹配 值：\n    情况 模式：\n        代码\n```',
            '异步': '### 异步\n\n声明异步函数。\n\n```\n异步 段落 名称 接收 参数：\n    await 操作\n```',
            '等待': '### 等待\n\n等待异步操作完成（等同于 Python 的 `await`）。',
            '长度': '### 长度\n\n获取列表或字符串的长度。\n\n```\n长度(列表)\n长度("字符串")\n```',
            '类型': '### 类型\n\n获取值的类型名称。\n\n```\n类型(值)\n```',
            '转整数': '### 转整数\n\n将值转换为整数。\n\n```\n转整数("42")  → 42\n```',
            '转小数': '### 转小数\n\n将值转换为浮点数。\n\n```\n转小数("3.14")  → 3.14\n```',
            '转字符串': '### 转字符串\n\n将值转换为字符串。\n\n```\n转字符串(42)  → "42"\n```',
            '范围': '### 范围\n\n生成整数范围。\n\n```\n范围(1, 10)  → [1, 2, ..., 10]\n```',
            '解析JSON': '### 解析JSON\n\n将 JSON 字符串解析为 Python 对象。',
            '序列化JSON': '### 序列化JSON\n\n将 Python 对象序列化为 JSON 字符串。',
            // 新增高优先级关键字
            '使用': '### 使用\n\n上下文管理器（使用 ... 为 ...）。\n\n```\n使用 表达式 为 变量：\n    代码\n```\n\n示例：\n```\n使用 打开("文件.txt") 为 文件：\n    打印(文件.读取())\n```',
            '数据': '### 数据\n\n定义数据/记录类型（类似于 Python 的 dataclass）。\n\n```\n数据 类型名：\n    字段名: 类型\n```\n\n示例：\n```\n数据 点：\n    x: 小数\n    y: 小数\n```',
            '枚举': '### 枚举\n\n定义枚举类型（代数数据类型）。\n\n```\n枚举 名称：\n    变体1\n    变体2(字段: 类型)\n```\n\n示例：\n```\n枚举 颜色：\n    红\n    绿\n    蓝\n```',
            '外部': '### 外部\n\nFFI 外部声明，用于调用 C 语言函数。\n\n```\n外部 段落 函数名 接收 参数 返回 类型 在 库别名\n```\n\n示例：\n```\n加载库 "libc.so.6" 为 libc\n外部 段落 malloc 接收 大小: 整数 返回 指针[空] 在 libc\n```',
            '至': '### 至\n\n范围表达式的结束关键字，配合起始值使用。\n\n```\n1 至 10    # 1 到 10（包含 10）\n```\n\n也支持 `到` 关键字。',
            '到': '### 到\n\n范围表达式的结束关键字，与 `至` 功能相同。\n\n```\n1 到 10    # 1 到 10（包含 10）\n```',
            '步': '### 步\n\n范围表达式的步长关键字。\n\n```\n1 至 10 步 2   # 1, 3, 5, 7, 9\n```',
            'pass': '### pass\n\n空语句占位符，用于需要语句但无操作的位置。\n\n```\n如果 条件：\n    pass    # 暂时空实现\n```',
            '嵌入': '### 嵌入\n\n嵌入代码块，可在光明代码中直接写 Python/C 等语言代码。\n\n```\n嵌入 Python：\n    print("Hello from Python")\n结束嵌入\n```',
            '并': '### 并\n\n管道操作符，将前一个表达式的结果传递给下一个函数。\n\n```\n数据 -> 并 处理() -> 并 输出()\n```',
            '标注': '### 标注\n\n装饰器定义，用于给段落/函数添加元数据或行为。\n\n```\n标注 装饰器名\n段落 被装饰函数 接收 参数：\n    代码\n```',
            // 新增中优先级关键字
            '错误': '### 错误\n\n定义错误类型，用于结构化错误处理。\n\n```\n错误 错误名：\n    字段1: 类型1\n    字段2: 类型2\n```\n\n示例：\n```\n错误 验证错误：\n    字段: 字符串\n    消息: 字符串\n```',
            'trait': '### trait\n\n定义 Trait（接口集），定义一组方法签名，供类型实现。\n\n```\ntrait 名称：\n    方法名(参数) -> 返回类型\n```\n\n示例：\n```\ntrait 可比较：\n    比较(其他) -> 整数\n```',
            '类型别名': '### 类型别名\n\n为已有类型定义别名。\n\n```\n类型别名 新名称 为 已有类型\n```\n\n示例：\n```\n类型别名 距离 为 小数\n```',
            '推迟': '### 推迟\n\n推迟执行，注册的代码块在作用域退出时自动执行（类似 Python 的 `finally` 或 Go 的 `defer`）。\n\n```\n推迟：\n    代码\n```\n\n示例：\n```\n设 文件 为 打开("data.txt")\n推迟：\n    文件.关闭()\n```',
            '并行': '### 并行\n\n并行作用域，结构化并发执行多个任务。\n\n```\n并行 {\n    任务1\n    任务2\n}\n```\n\n所有任务执行完毕后继续后续代码。',
            '开启类型检查': '### 开启类型检查\n\n在当前作用域内开启类型检查模式。\n\n```\n开启类型检查\n```\n\n之后的代码将进行严格的类型检查。',
            '关闭类型检查': '### 关闭类型检查\n\n在当前作用域内关闭类型检查模式。\n\n```\n关闭类型检查\n```\n\n之后的代码将跳过类型检查。',
            // 新增低优先级 FFI 关键字
            '取地址': '### 取地址\n\n获取变量的内存地址（FFI 指针操作）。\n\n```\n取地址(变量)\n```\n\n示例：\n```\n设 指针 为 取地址(甲)\n```',
            '解引用': '### 解引用\n\n通过指针访问其指向的值（FFI 指针操作）。\n\n```\n解引用(指针)\n```\n\n示例：\n```\n设 值 为 解引用(指针)\n```',
            '指针偏移': '### 指针偏移\n\n按偏移量移动指针位置（FFI 指针操作）。\n\n```\n指针偏移(指针, 偏移量)\n```',
            '设置指针值': '### 设置指针值\n\n通过指针向内存写入值（FFI 指针操作）。\n\n```\n设置指针值(指针, 值)\n```',
            '分配内存': '### 分配内存\n\n分配指定大小的内存（FFI 内存管理）。\n\n```\n分配内存(大小)\n```\n\n分配后应使用 `释放内存` 释放。',
            '释放内存': '### 释放内存\n\n释放之前分配的内存（FFI 内存管理）。\n\n```\n释放内存(指针)\n```',
            '创建数组': '### 创建数组\n\n创建 C 风格数组（FFI 数组操作）。\n\n```\n创建数组 类型 [大小]\n```\n\n示例：\n```\n设 数组 为 创建数组 整数 [5]\n```',
            '设置数组': '### 设置数组\n\n设置数组指定位置的元素（FFI 数组操作）。\n\n```\n设置数组(数组, 索引, 值)\n```',
            '获取FFI错误': '### 获取FFI错误\n\n获取最后一次 FFI 调用的错误信息。\n\n```\n获取FFI错误()\n```',
            '获取系统错误码': '### 获取系统错误码\n\n获取系统级错误码（errno）。\n\n```\n获取系统错误码()\n```',
        };

        if (hoverDocs[word]) {
            return new vscode.Hover(new vscode.MarkdownString(hoverDocs[word]));
        }

        return null;
    }
}

// =============================================================================
// 格式化提供器
// =============================================================================

class LightFormattingProvider {
    provideDocumentFormattingEdits(document) {
        const config = vscode.workspace.getConfiguration('light.format');
        const indentSize = config.get('indentSize', 4);
        const trimTrailing = config.get('trimTrailingWhitespace', true);
        const insertFinalNewline = config.get('insertFinalNewline', true);

        const edits = [];
        const lineCount = document.lineCount;
        if (lineCount === 0) return edits;

        const firstLine = document.lineAt(0);
        const lastLine = document.lineAt(lineCount - 1);
        const fullRange = new vscode.Range(
            firstLine.range.start,
            lastLine.range.end
        );

        const indentSpaces = ' '.repeat(indentSize);
        const lines = [];

        for (let i = 0; i < lineCount; i++) {
            let line = document.lineAt(i).text;

            // 将制表符转换为空格，确保缩进一致
            line = line.replace(/\t/g, indentSpaces);

            // 去除行尾空白
            if (trimTrailing) {
                line = line.replace(/[ \t]+$/, '');
            }

            lines.push(line);
        }

        let result = lines.join('\n');

        // 确保文件以换行符结尾
        if (insertFinalNewline && !result.endsWith('\n')) {
            result += '\n';
        }

        const originalText = document.getText();
        if (result === originalText) {
            return edits;
        }

        edits.push(vscode.TextEdit.replace(fullRange, result));
        return edits;
    }
}

// =============================================================================
// 命令注册
// =============================================================================

function registerCommands(context) {
    // --- 显示欢迎页 ---
    const welcomeCmd = vscode.commands.registerCommand('light.welcome', () => {
        showWelcomePage(context);
    });
    context.subscriptions.push(welcomeCmd);

    // --- 运行文件 ---
    const runCmd = vscode.commands.registerCommand('light.run', () => {
        const filePath = getActiveLightFile();
        if (!filePath) return;

        const terminal = vscode.window.createTerminal(`光明运行: ${path.basename(filePath)}`);
        terminal.show();
        const projectRoot = getProjectRoot();
        const pythonCmd = getPythonPath();
        terminal.sendText(`cd "${projectRoot}" ; ${pythonCmd} -m cli.light run "${filePath}"`);
    });

    // --- 构建文件 ---
    const buildCmd = vscode.commands.registerCommand('light.build', () => {
        const filePath = getActiveLightFile();
        if (!filePath) return;

        const terminal = vscode.window.createTerminal(`光明构建: ${path.basename(filePath)}`);
        terminal.show();
        const projectRoot = getProjectRoot();
        const pythonCmd = getPythonPath();
        const outPath = filePath.replace(/\.light$/, '');
        terminal.sendText(`cd "${projectRoot}" ; ${pythonCmd} -m cli.light compile "${filePath}" -o "${outPath}"`);
    });

    // --- 格式化文件 ---
    const formatCmd = vscode.commands.registerCommand('light.format', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'light') {
            vscode.window.showInformationMessage('请打开一个光明 (.light) 文件');
            return;
        }
        vscode.commands.executeCommand('editor.action.formatDocument');
    });

    // --- 语法检查 ---
    const checkCmd = vscode.commands.registerCommand('light.check', () => {
        const filePath = getActiveLightFile();
        if (!filePath) return;
        runCommandWithDiagnostics('check', [], '语法检查');
    });

    // --- 编译为 Python ---
    const compileCmd = vscode.commands.registerCommand('light.compile', () => {
        const filePath = getActiveLightFile();
        if (!filePath) return;

        const terminal = vscode.window.createTerminal(`光明编译: ${path.basename(filePath)}`);
        terminal.show();
        const projectRoot = getProjectRoot();
        const pythonCmd = getPythonPath();
        terminal.sendText(`cd "${projectRoot}" ; ${pythonCmd} -m cli.light compile "${filePath}"`);
    });

    // --- LLVM-Typed 编译 ---
    const compileLLVMCmd = vscode.commands.registerCommand('light.compileLLVM', () => {
        const filePath = getActiveLightFile();
        if (!filePath) return;

        const terminal = vscode.window.createTerminal(`光明 LLVM 编译: ${path.basename(filePath)}`);
        terminal.show();
        const projectRoot = getProjectRoot();
        const pythonCmd = getPythonPath();
        const outPath = filePath.replace(/\.light$/, '.exe');
        terminal.sendText(`cd "${projectRoot}" ; ${pythonCmd} -m cli.light compile "${filePath}" --backend llvm-typed -o "${outPath}"`);
    });

    // --- 类型检查 ---
    const typeCheckCmd = vscode.commands.registerCommand('light.typeCheck', () => {
        const filePath = getActiveLightFile();
        if (!filePath) return;
        runCommandWithDiagnostics('type-check', ['--level', '表达式'], '类型检查');
    });

    // --- REPL ---
    const replCmd = vscode.commands.registerCommand('light.repl', () => {
        const projectRoot = getProjectRoot();
        const pythonCmd = getPythonPath();
        const terminal = vscode.window.createTerminal('光明 REPL');
        terminal.show();
        terminal.sendText(`cd "${projectRoot}" ; ${pythonCmd} -m cli.light repl`);
    });

    // --- Python↔Light 双向翻译 ---
    const translateCmd = vscode.commands.registerCommand('light.translate', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showInformationMessage('请打开一个文件进行翻译');
            return;
        }
        const filePath = editor.document.uri.fsPath;
        const projectRoot = getProjectRoot();
        const pythonCmd = getPythonPath();
        const isLight = filePath.endsWith('.light');
        const direction = isLight ? '--to-python' : '--to-light';
        const terminal = vscode.window.createTerminal('光明翻译');
        terminal.show();
        terminal.sendText(`cd "${projectRoot}" ; ${pythonCmd} -m tools.ai_copilot.translator ${direction} "${filePath}"`);
    });

    // --- AI 辅助代码生成 ---
    const aiCmd = vscode.commands.registerCommand('light.ai', async () => {
        const query = await vscode.window.showInputBox({
            prompt: '请输入代码生成需求描述',
            placeHolder: '例如：写一个二分查找函数',
            ignoreFocusOut: true
        });
        if (!query) return;
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: '光明 AI 生成中...',
            cancellable: false
        }, async () => {
            try {
                const projectRoot = getProjectRoot();
                const pythonCmd = getPythonPath();
                const { execSync } = require('child_process');
                const result = execSync(
                    `"${pythonCmd}" -c "import sys; sys.path.insert(0, '${projectRoot.replace(/\\/g, '\\\\')}'); from tools.ai_copilot.offline_model import OfflineModel; m = OfflineModel(); print(m.generate('${query.replace(/'/g, "\\'")}'))"`,
                    { cwd: projectRoot, encoding: 'utf-8', timeout: 30000 }
                );
                const snippet = new vscode.SnippetString(result.trim());
                const editor = vscode.window.activeTextEditor;
                if (editor) {
                    editor.insertSnippet(snippet);
                    vscode.window.showInformationMessage('光明 AI 代码已插入');
                }
            } catch (e) {
                vscode.window.showErrorMessage(`AI 生成失败: ${e.message}`);
            }
        });
    });

    // --- 重启 LSP ---
    const restartCmd = vscode.commands.registerCommand('light.restartLSP', async () => {
        updateStatusBar('offline');
        if (client) {
            try {
                await client.stop();
            } catch (e) {
                outputChannel.appendLine(`[光明] 停止 LSP 失败: ${e.message}`);
            }
        }
        try {
            startLSP(context);
            vscode.window.showInformationMessage('光明 LSP 服务器已重启');
        } catch (e) {
            outputChannel.appendLine(`[光明] 启动 LSP 失败: ${e.message}`);
            updateStatusBar('error');
            vscode.window.showErrorMessage('光明 LSP 服务器重启失败');
        }
    });

    context.subscriptions.push(
        runCmd, buildCmd, formatCmd, checkCmd, compileCmd, compileLLVMCmd,
        typeCheckCmd, replCmd, restartCmd, translateCmd, aiCmd
    );
}

// =============================================================================
// 扩展激活 / 停用
// =============================================================================

function activate(context) {
    console.log('光明语言扩展已激活');

    // 输出通道
    outputChannel = vscode.window.createOutputChannel('光明');
    context.subscriptions.push(outputChannel);
    outputChannel.appendLine(`光明语言扩展 v${EXTENSION_VERSION} 已激活`);

    // 问题面板
    createDiagnosticCollection(context);

    // 状态栏
    createStatusBar(context);

    // 启动 LSP 语言服务器
    try {
        startLSP(context);
    } catch (e) {
        outputChannel.appendLine(`[光明] LSP 启动失败: ${e.message}`);
        updateStatusBar('error');
        vscode.window.showWarningMessage('光明 LSP 服务器启动失败，部分功能不可用');
    }

    // 注册命令
    registerCommands(context);

    // 注册 Task Provider
    const projectRoot = getProjectRoot();
    const pythonCmd = getPythonPath();
    const taskProvider = new LightTaskProvider(projectRoot, pythonCmd);
    context.subscriptions.push(
        vscode.tasks.registerTaskProvider('light', taskProvider)
    );

    // 注册补全提供器
    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(
            { scheme: 'file', language: 'light' },
            new LightCompletionProvider()
        )
    );

    // 注册悬浮提示提供器
    context.subscriptions.push(
        vscode.languages.registerHoverProvider(
            { scheme: 'file', language: 'light' },
            new LightHoverProvider()
        )
    );

    // 注册格式化提供器
    const formatEnabled = vscode.workspace.getConfiguration('light.format').get('enable', true);
    if (formatEnabled) {
        context.subscriptions.push(
            vscode.languages.registerDocumentFormattingEditProvider(
                { scheme: 'file', language: 'light' },
                new LightFormattingProvider()
            )
        );
        outputChannel.appendLine('[光明] 格式化提供器已注册');
    }

    outputChannel.appendLine('[光明] 扩展初始化完成');

    // 首次安装显示欢迎页
    if (checkFirstRun(context)) {
        setTimeout(() => {
            showWelcomePage(context);
        }, 500);
    }
}

function deactivate() {
    if (statusBarItem) {
        statusBarItem.dispose();
    }
    if (diagnosticCollection) {
        diagnosticCollection.clear();
    }
    if (outputChannel) {
        outputChannel.appendLine('[光明] 扩展已停用');
    }
    if (client) {
        return client.stop();
    }
    return undefined;
}

module.exports = { activate, deactivate };