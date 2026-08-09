/**
 * 光明 (Light) VS Code 扩展
 * 
 * 提供：
 * - LSP 客户端连接
 * - 调试适配器集成
 * - 命令注册
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { LanguageClient, LanguageClientOptions, ServerOptions, TransportKind } from 'vscode-languageclient/node';
import { LightDebugConfigurationProvider } from './debugConfiguration';

// 全局变量
let client: LanguageClient | undefined;

/**
 * 获取 LSP 服务器路径
 */
function getServerPath(): string {
    const config = vscode.workspace.getConfiguration('light');
    const customPath = config.get<string>('serverPath');
    
    if (customPath && customPath.trim()) {
        return customPath;
    }
    
    // 默认使用相对于扩展目录的路径
    const extensionPath = __dirname;
    const projectRoot = path.dirname(path.dirname(extensionPath));
    return path.join(projectRoot, 'lsp', 'light_lsp.py');
}

/**
 * 激活扩展
 */
export function activate(context: vscode.ExtensionContext) {
    console.log('光明扩展已激活');
    
    // 注册调试配置提供者
    context.subscriptions.push(
        vscode.debug.registerDebugConfigurationProvider('light', new LightDebugConfigurationProvider())
    );
    
    // 启动 LSP 服务器
    startLanguageServer(context);
    
    // 注册命令
    registerCommands(context);
}

/**
 * 启动语言服务器
 */
async function startLanguageServer(context: vscode.ExtensionContext) {
    const serverPath = getServerPath();
    const debugPort = vscode.workspace.getConfiguration('light').get<number>('debugPort', 8765);
    
    // 服务器选项
    const serverOptions: ServerOptions = {
        run: {
            command: 'python',
            args: [serverPath],
            transport: TransportKind.stdio
        },
        debug: {
            command: 'python',
            args: ['-m', 'debugpy', '--listen', `localhost:${debugPort}`, '--wait-for-client', serverPath],
            transport: TransportKind.stdio
        }
    };
    
    // 客户端选项
    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ language: 'light' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.light')
        },
        middleware: {
            provideHover: async (document, position, token, next) => {
                // 可以在这里添加自定义的悬停处理
                return next(document, position, token);
            },
            provideCompletionItem: async (document, position, context, token, next) => {
                // 可以在这里添加自定义的补全处理
                return next(document, position, context, token);
            }
        }
    };
    
    // 创建客户端
    client = new LanguageClient('lightLanguageServer', '光明语言服务器', serverOptions, clientOptions);
    
    // 启动客户端
    try {
        await client.start();
        console.log('LSP 服务器已启动');
    } catch (error) {
        vscode.window.showErrorMessage(`无法启动 LSP 服务器: ${error}`);
        console.error('LSP 服务器启动失败:', error);
    }
    
    // 清理
    context.subscriptions.push({
        dispose: () => {
            client?.stop();
        }
    });
}

/**
 * 注册命令
 */
function registerCommands(context: vscode.ExtensionContext) {
    // 运行文件
    context.subscriptions.push(
        vscode.commands.registerCommand('light.runFile', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor || editor.document.languageId !== 'light') {
                vscode.window.showInformationMessage('请打开一个光明文件');
                return;
            }
            
            const filePath = editor.document.uri.fsPath;
            const terminal = vscode.window.createTerminal(`光明运行: ${path.basename(filePath)}`);
            terminal.sendText(`python "${filePath}"`);
            terminal.show();
        })
    );
    
    // 打开 REPL
    context.subscriptions.push(
        vscode.commands.registerCommand('light.showREPL', async () => {
            const projectRoot = path.dirname(path.dirname(__dirname));
            const terminal = vscode.window.createTerminal('光明 REPL');
            terminal.sendText(`python "${path.join(projectRoot, 'tools', 'repl.py')}"`);
            terminal.show();
        })
    );
    
    // 重启服务器
    context.subscriptions.push(
        vscode.commands.registerCommand('light.restartServer', async () => {
            if (client) {
                await client.stop();
                await client.start();
                vscode.window.showInformationMessage('LSP 服务器已重启');
            }
        })
    );
}

/**
 * 停用扩展
 */
export function deactivate(): Thenable<void> | undefined {
    if (client) {
        return client.stop();
    }
    return undefined;
}
