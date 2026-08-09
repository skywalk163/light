/**
 * 光明调试配置提供者
 */

import * as vscode from 'vscode';
import * as path from 'path';

export class LightDebugConfigurationProvider implements vscode.DebugConfigurationProvider {
    
    /**
     * 提供调试配置
     */
    async provideDebugConfigurations(
        folder: vscode.WorkspaceFolder | undefined
    ): Promise<vscode.DebugConfiguration[]> {
        const configurations: vscode.DebugConfiguration[] = [
            {
                name: '调试当前文件',
                type: 'light',
                request: 'launch',
                program: '${file}',
                stopOnEntry: true,
                console: {
                    integrated: {
                        internalConsoleOptions: 'neverOpen'
                    }
                }
            },
            {
                name: '调试程序',
                type: 'light',
                request: 'launch',
                program: '',
                stopOnEntry: true,
                console: {
                    integrated: {
                        internalConsoleOptions: 'neverOpen'
                    }
                }
            },
            {
                name: '附加到调试器',
                type: 'light',
                request: 'attach',
                port: 8765,
                host: 'localhost'
            }
        ];
        
        return configurations;
    }
    
    /**
     * 解析调试配置
     */
    async resolveDebugConfiguration(
        folder: vscode.WorkspaceFolder | undefined,
        config: vscode.DebugConfiguration,
        token?: vscode.CancellationToken
    ): Promise<vscode.DebugConfiguration | undefined> {
        // 如果没有配置，提供默认值
        if (!config.type && !config.request && !config.name) {
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document.languageId === 'light') {
                config = {
                    type: 'light',
                    name: '调试当前文件',
                    request: 'launch',
                    program: editor.document.uri.fsPath,
                    stopOnEntry: true
                };
            }
        }
        
        // 验证程序文件
        if (config.program) {
            const programPath = config.program.replace('${file}', '');
            if (programPath && !path.existsSync(programPath)) {
                vscode.window.showErrorMessage(`程序文件不存在: ${programPath}`);
                return undefined;
            }
        }
        
        return config;
    }
}
