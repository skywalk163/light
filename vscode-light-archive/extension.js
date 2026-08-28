/**
 * 光明 (Light) VS Code 扩展 v5.0
 * 提供运行、解析、编译、格式化、调试命令及 LSP 语言服务
 */
const vscode = require('vscode');
const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * 激活扩展
 */
function activate(context) {
    console.log('光明 v5.0 扩展已激活');

    // 注册 LSP 客户端
    const lspClient = startLSPClient(context);

    // 注册调试适配器工厂
    const debugAdapterFactory = createDebugAdapterFactory();
    context.subscriptions.push(
        vscode.debug.registerDebugAdapterDescriptorFactory('light', debugAdapterFactory)
    );

    // 运行当前文件
    const runCmd = vscode.commands.registerCommand('light.runFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('请先打开一个 .light 文件');
            return;
        }

        const filePath = editor.document.uri.fsPath;
        const pythonPath = vscode.workspace.getConfiguration('light').get('pythonPath', 'python');

        // 保存文件
        await editor.document.save();

        // 创建输出通道
        const outputChannel = vscode.window.createOutputChannel('光明 运行');
        outputChannel.show(true);
        const startTime = Date.now();
        outputChannel.appendLine(`=== 运行: ${path.basename(filePath)} ===\n`);

        try {
            const projectRoot = findProjectRoot(filePath);
            const cmd = `"${pythonPath}" -c "
import sys
sys.path.insert(0, r'${projectRoot}')
sys.path.insert(0, r'${path.join(projectRoot, 'src')}')
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

with open(r'${filePath}', 'r', encoding='utf-8') as f:
    code = f.read()

parser = LightParser()
ast = parser.parse(code)
if ast is None:
    print('解析错误:', parser.errors)
    sys.exit(1)

gen = PythonCodeGenerator()
py_code = gen.generate(ast)
exec(py_code, {'__name__': '__main__'})
"`;

            const result = execSync(cmd, {
                cwd: projectRoot,
                encoding: 'utf-8',
                timeout: 30000,
                maxBuffer: 10 * 1024 * 1024
            });

            const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
            outputChannel.appendLine(result || '(无输出)');
            outputChannel.appendLine(`\n=== 运行完成 (${elapsed}s) ===`);
        } catch (error) {
            outputChannel.appendLine(`错误: ${error.stderr || error.message}`);
            outputChannel.appendLine('\n=== 运行失败 ===');
        }
    });

    // 解析当前文件 (AST)
    const parseCmd = vscode.commands.registerCommand('light.parseFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('请先打开一个 .light 文件');
            return;
        }

        const filePath = editor.document.uri.fsPath;
        const pythonPath = vscode.workspace.getConfiguration('light').get('pythonPath', 'python');

        await editor.document.save();

        const outputChannel = vscode.window.createOutputChannel('光明 AST');
        outputChannel.show(true);
        outputChannel.appendLine(`=== AST 解析: ${path.basename(filePath)} ===\n`);

        try {
            const projectRoot = findProjectRoot(filePath);
            const cmd = `"${pythonPath}" -c "
import sys, json
sys.path.insert(0, r'${projectRoot}')
sys.path.insert(0, r'${path.join(projectRoot, 'src')}')
from light_parser_v3 import LightParser

with open(r'${filePath}', 'r', encoding='utf-8') as f:
    code = f.read()

parser = LightParser()
ast = parser.parse(code)
if ast is None:
    print('解析错误:')
    for e in parser.errors:
        print(f'  {e}')
else:
    node_count = count_nodes(ast)
    print(f'语句数: {len(ast.statements)}')
    print(f'节点总数: {node_count}')
    print()
    for i, stmt in enumerate(ast.statements):
        print(f'[{i}] {type(stmt).__name__}')
        for attr in dir(stmt):
            if not attr.startswith('_'):
                try:
                    val = getattr(stmt, attr)
                    if not callable(val) and val is not None:
                        print(f'    {attr}: {val}')
                except:
                    pass

def count_nodes(node):
    count = 1
    for attr in dir(node):
        if not attr.startswith('_'):
            try:
                val = getattr(node, attr)
                if isinstance(val, list):
                    for item in val:
                        if hasattr(item, '__class__') and hasattr(item, '__dict__'):
                            count += count_nodes(item)
                elif hasattr(val, '__class__') and hasattr(val, '__dict__'):
                    count += count_nodes(val)
            except:
                pass
    return count
"`;

            const result = execSync(cmd, {
                cwd: projectRoot,
                encoding: 'utf-8',
                timeout: 10000,
                maxBuffer: 10 * 1024 * 1024
            });

            outputChannel.appendLine(result);
            outputChannel.appendLine('\n=== 解析完成 ===');
        } catch (error) {
            outputChannel.appendLine(`错误: ${error.stderr || error.message}`);
        }
    });

    // 编译当前文件
    const compileCmd = vscode.commands.registerCommand('light.compileFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('请先打开一个 .light 文件');
            return;
        }

        const filePath = editor.document.uri.fsPath;
        const pythonPath = vscode.workspace.getConfiguration('light').get('pythonPath', 'python');

        await editor.document.save();

        const outputChannel = vscode.window.createOutputChannel('光明 编译');
        outputChannel.show(true);
        outputChannel.appendLine(`=== 编译: ${path.basename(filePath)} ===\n`);

        try {
            const projectRoot = findProjectRoot(filePath);
            const cmd = `"${pythonPath}" -c "
import sys
sys.path.insert(0, r'${projectRoot}')
sys.path.insert(0, r'${path.join(projectRoot, 'src')}')
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

with open(r'${filePath}', 'r', encoding='utf-8') as f:
    code = f.read()

parser = LightParser()
ast = parser.parse(code)
if ast is None:
    print('解析错误:', parser.errors)
    sys.exit(1)

gen = PythonCodeGenerator()
py_code = gen.generate(ast)
print(py_code)
"`;

            const result = execSync(cmd, {
                cwd: projectRoot,
                encoding: 'utf-8',
                timeout: 15000,
                maxBuffer: 10 * 1024 * 1024
            });

            outputChannel.appendLine(result);
            outputChannel.appendLine('\n=== 编译完成 ===');
        } catch (error) {
            outputChannel.appendLine(`错误: ${error.stderr || error.message}`);
            outputChannel.appendLine('\n=== 编译失败 ===');
        }
    });

    // 编译为原生可执行文件
    const compileNativeCmd = vscode.commands.registerCommand('light.compileNative', async () => {
        vscode.window.showInformationMessage('原生编译需要 LLVM 工具链支持，请先安装 LLVM');
    });

    // 构建整个项目
    const buildProjectCmd = vscode.commands.registerCommand('light.buildProject', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('请先打开项目中的 .light 文件');
            return;
        }

        const filePath = editor.document.uri.fsPath;
        const projectRoot = findProjectRoot(filePath);
        const pythonPath = vscode.workspace.getConfiguration('light').get('pythonPath', 'python');

        const outputChannel = vscode.window.createOutputChannel('光明 构建');
        outputChannel.show(true);
        outputChannel.appendLine(`=== 构建项目: ${path.basename(projectRoot)} ===\n`);

        try {
            // 读取 package.toml
            const pkgPath = path.join(projectRoot, 'package.toml');
            if (fs.existsSync(pkgPath)) {
                outputChannel.appendLine(`项目配置: ${fs.readFileSync(pkgPath, 'utf-8')}`);
            }

            // 收集所有 .light 文件
            const lightFiles = findLightFiles(projectRoot);
            outputChannel.appendLine(`找到 ${lightFiles.length} 个 .light 文件\n`);

            for (const lightFile of lightFiles) {
                const relPath = path.relative(projectRoot, lightFile);
                outputChannel.appendLine(`[编译] ${relPath}...`);

                const cmd = `"${pythonPath}" -c "
import sys
sys.path.insert(0, r'${projectRoot}')
sys.path.insert(0, r'${path.join(projectRoot, 'src')}')
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

with open(r'${lightFile}', 'r', encoding='utf-8') as f:
    code = f.read()

parser = LightParser()
ast = parser.parse(code)
if ast is None:
    print('解析错误:', parser.errors)
    sys.exit(1)

gen = PythonCodeGenerator()
py_code = gen.generate(ast)
output_path = r'${lightFile}' + '.py'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(py_code)
print(f'生成: {output_path}')
"`;

                execSync(cmd, {
                    cwd: projectRoot,
                    encoding: 'utf-8',
                    timeout: 15000,
                    maxBuffer: 10 * 1024 * 1024
                });
            }

            outputChannel.appendLine('\n=== 构建完成 ===');
        } catch (error) {
            outputChannel.appendLine(`错误: ${error.stderr || error.message}`);
            outputChannel.appendLine('\n=== 构建失败 ===');
        }
    });

    // 格式化当前文件
    const formatCmd = vscode.commands.registerCommand('light.formatFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('请先打开一个 .light 文件');
            return;
        }

        const document = editor.document;
        const text = document.getText();
        const tabSize = editor.options.tabSize || 4;
        const insertSpaces = editor.options.insertSpaces !== false;

        const indent = insertSpaces ? ' '.repeat(tabSize) : '\t';
        const lines = text.split('\n');
        let indentLevel = 0;
        const formattedLines = [];

        for (const line of lines) {
            const trimmed = line.trim();
            let lineText = trimmed;

            // 减少缩进关键字
            const decreaseKeywords = ['结束', '结束引', '否则', '否', '否则若', '否若', '捕获', '捕', '最终', '终'];
            for (const kw of decreaseKeywords) {
                if (trimmed.startsWith(kw)) {
                    indentLevel = Math.max(0, indentLevel - 1);
                    break;
                }
            }

            // 应用缩进
            if (trimmed) {
                formattedLines.push(indent.repeat(indentLevel) + trimmed);
            } else {
                formattedLines.push('');
            }

            // 增加缩进
            if (trimmed.endsWith('：') || trimmed.endsWith(':')) {
                const increaseKeywords = ['若', '如果', '当', '历', '遍历', '函', '段落', '类', '接口', '试', '尝试', '匹', '匹配', '否则', '否', '捕获', '捕'];
                for (const kw of increaseKeywords) {
                    if (trimmed.startsWith(kw)) {
                        indentLevel += 1;
                        break;
                    }
                }
            }
        }

        const formatted = formattedLines.join('\n');
        if (formatted !== text) {
            const fullRange = new vscode.Range(
                document.positionAt(0),
                document.positionAt(text.length)
            );
            editor.edit(editBuilder => {
                editBuilder.replace(fullRange, formatted);
            });
            vscode.window.showInformationMessage('光明文件已格式化');
        }
    });

    // 显示版本信息
    const versionCmd = vscode.commands.registerCommand('light.showVersion', () => {
        const outputChannel = vscode.window.createOutputChannel('光明 版本信息');
        outputChannel.show(true);
        outputChannel.appendLine('=== 光明 (Light) 语言 ===');
        outputChannel.appendLine('版本: 5.0.0');
        outputChannel.appendLine('VSCode 扩展版本: 5.0.0');
        outputChannel.appendLine('文体模式: L1 白话 (19字) / L2 文言 (30字)');
        outputChannel.appendLine('层级: L0 基础 / L1 白话 / L2 文言 / L3 格律 / L4 嵌入');
        outputChannel.appendLine('');
        outputChannel.appendLine('项目仓库: https://github.com/light-lang/light');
        outputChannel.appendLine('文档: https://github.com/light-lang/light/blob/main/docs/');
    });

    // 状态栏：显示文体模式
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(symbol-namespace) 光明 L2';
    statusBarItem.tooltip = '光明文体模式 (L1 白话 / L2 文言)';
    statusBarItem.command = 'light.showVersion';
    statusBarItem.show();

    // 更新状态栏基于配置
    function updateStatusBar() {
        const style = vscode.workspace.getConfiguration('light').get('style', 'L2');
        statusBarItem.text = `$(symbol-namespace) 光明 ${style}`;
    }
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('light.style')) {
                updateStatusBar();
            }
        })
    );

    context.subscriptions.push(
        runCmd, parseCmd, compileCmd, compileNativeCmd,
        buildProjectCmd, formatCmd, versionCmd, statusBarItem
    );
}

/**
 * 创建并启动 LSP 客户端
 */
function startLSPClient(context) {
    try {
        const pythonPath = vscode.workspace.getConfiguration('light').get('pythonPath', 'python');
        const lspScript = path.join(context.extensionPath, '..', 'lsp', 'light_lsp_main.py');

        if (!fs.existsSync(lspScript)) {
            console.log('光明 LSP 脚本未找到，跳过 LSP 客户端启动');
            return null;
        }

        const serverOptions = {
            command: pythonPath,
            args: [lspScript, '--stdio'],
            options: {
                env: { ...process.env }
            }
        };

        const clientOptions = {
            documentSelector: [{ scheme: 'file', language: 'light' }],
            synchronize: {
                configurationSection: 'light'
            }
        };

        const client = new (require('vscode-languageclient/node').LanguageClient)(
            'light-lsp',
            '光明语言服务器',
            serverOptions,
            clientOptions
        );

        context.subscriptions.push(client.start());
        console.log('光明 LSP 客户端已启动');
        return client;
    } catch (e) {
        console.log('光明 LSP 客户端启动失败（可选功能）:', e.message);
        return null;
    }
}

/**
 * 创建调试适配器工厂
 */
function createDebugAdapterFactory() {
    const factory = {
        createDebugAdapterDescriptor(session) {
            const pythonPath = vscode.workspace.getConfiguration('light').get('pythonPath', 'python');
            const debugScript = path.join(__dirname, 'debug-adapter', 'light_debug.py');

            if (fs.existsSync(debugScript)) {
                return new vscode.DebugAdapterExecutable(
                    pythonPath,
                    [debugScript],
                    { env: { ...process.env } }
                );
            }
            return null;
        }
    };
    return factory;
}

/**
 * 查找项目根目录（包含 src/ 目录的父目录）
 */
function findProjectRoot(filePath) {
    let dir = path.dirname(filePath);
    while (dir !== path.dirname(dir)) {
        if (fs.existsSync(path.join(dir, 'src', 'light_parser_v3.py'))) {
            return dir;
        }
        dir = path.dirname(dir);
    }
    return path.dirname(filePath);
}

/**
 * 查找所有 .light 文件
 */
function findLightFiles(rootDir) {
    const results = [];
    function walk(dir) {
        try {
            const entries = fs.readdirSync(dir, { withFileTypes: true });
            for (const entry of entries) {
                const fullPath = path.join(dir, entry.name);
                if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
                    walk(fullPath);
                } else if (entry.isFile() && entry.name.endsWith('.light')) {
                    results.push(fullPath);
                }
            }
        } catch (e) {
            // 忽略无权访问的目录
        }
    }
    walk(rootDir);
    return results;
}

function deactivate() {}

module.exports = { activate, deactivate };