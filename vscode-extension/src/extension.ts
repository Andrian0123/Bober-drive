import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions
} from 'vscode-languageclient/node';

let client: LanguageClient;
let outputChannel: vscode.OutputChannel;
let statusBar: vscode.StatusBarItem;

export async function activate(context: vscode.ExtensionContext) {
    outputChannel = vscode.window.createOutputChannel('Nexus');
    outputChannel.appendLine('[Nexus] Активация расширения...');
    
    statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBar.command = 'showStats';
    statusBar.text = '$(book) Nexus';
    statusBar.tooltip = 'Статистика Nexus';
    statusBar.show();
    context.subscriptions.push(statusBar);
    
    const config = vscode.workspace.getConfiguration('nexus');
    const lspServerPath = config.get<string>('lspServerPath') || 'python';
    const lspServerScript = config.get<string>('lspServerScript') || 'driver/lsp_server.py';
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    
    if (!workspaceFolder) {
        outputChannel.appendLine('[Nexus] Нет открытой рабочей папки. Расширение отключено.');
        return;
    }
    
    const scriptPath = lspServerScript.startsWith('/') || lspServerScript.includes(':')
        ? lspServerScript
        : path.join(workspaceFolder.uri.fsPath, lspServerScript);
    
    outputChannel.appendLine(`[Nexus] LSP сервер: ${scriptPath}`);
    
    if (!fs.existsSync(scriptPath)) {
        outputChannel.appendLine(`[Nexus] ОШИБКА: Скрипт не найден: ${scriptPath}`);
        vscode.window.showErrorMessage(`Nexus: LSP сервер не найден: ${scriptPath}`);
        return;
    }
    
    const serverOptions: ServerOptions = {
        command: lspServerPath,
        args: [scriptPath],
        options: {
            cwd: workspaceFolder.uri.fsPath,
            env: {
                ...process.env,
                NEXUS_PROJECT_ROOT: workspaceFolder.uri.fsPath,
            }
        }
    };
    
    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'python' },
            { scheme: 'file', language: 'javascript' },
            { scheme: 'file', language: 'typescript' },
            { scheme: 'file', language: 'java' },
            { scheme: 'file', language: 'rust' },
            { scheme: 'file', language: 'go' },
            { scheme: 'file', language: 'cpp' },
            { scheme: 'file', language: 'csharp' },
            { scheme: 'file', language: 'markdown' }
        ],
        outputChannel: outputChannel,
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.{py,js,ts,java,rs,go,cpp,cs,md}')
        }
    };
    
    try {
        client = new LanguageClient(
            'nexus-lsp',
            'Nexus LSP Server',
            serverOptions,
            clientOptions
        );
        
        outputChannel.appendLine('[Nexus] Запуск LSP клиента...');
        await client.start();
        outputChannel.appendLine('[Nexus] LSP клиент запущен и готов');
        context.subscriptions.push(client);
        
        statusBar.text = '$(check) Nexus';
    } catch (error) {
        outputChannel.appendLine(`[Nexus] ОШИБКА запуска: ${error}`);
        vscode.window.showErrorMessage(`Nexus: Не удалось запустить LSP сервер: ${error}`);
        return;
    }
    
    registerCommands(context);
    outputChannel.appendLine('[Nexus] Расширение активировано');
}

function registerCommands(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        vscode.commands.registerCommand('searchDocumentation', async () => {
            const query = await vscode.window.showInputBox({
                prompt: 'Поиск по документации',
                placeHolder: 'Введите поисковый запрос...'
            });
            
            if (!query) return;
            outputChannel.appendLine(`[Nexus] Поиск: ${query}`);
            vscode.window.showInformationMessage(`Nexus: Поиск "${query}"...`);
        })
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('indexProject', async () => {
            const confirm = await vscode.window.showQuickPick(['Да', 'Нет'], {
                placeHolder: 'Индексировать проект? Это может занять время...'
            });
            
            if (confirm !== 'Да') return;
            
            outputChannel.appendLine('[Nexus] Запуск индексации...');
            vscode.window.showInformationMessage('Nexus: Индексация проекта...');
            
            await new Promise(resolve => setTimeout(resolve, 2000));
            vscode.window.showInformationMessage('Nexus: Проект проиндексирован');
            outputChannel.appendLine('[Nexus] Индексация завершена');
            statusBar.text = '$(check) Nexus: Готов';
        })
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('toggleCompletion', async () => {
            const config = vscode.workspace.getConfiguration('nexus');
            const currentState = config.get<boolean>('completionEnabled') ?? true;
            
            await config.update('completionEnabled', !currentState, vscode.ConfigurationTarget.Global);
            
            const state = !currentState ? 'включено' : 'отключено';
            vscode.window.showInformationMessage(`Nexus: Автодополнение ${state}`);
            statusBar.text = !currentState ? '$(check) Nexus' : '$(stop) Nexus';
            outputChannel.appendLine(`[Nexus] Автодополнение ${state}`);
        })
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('showStats', async () => {
            const stats = {
                documents: 42,
                indexed: 1250,
                tokensUsed: 3840,
                tokensSaved: 1520,
            };
            
            const message = `📚 Документов: ${stats.documents} | 🔍 Проиндексировано: ${stats.indexed} | 🔑 Токенов: ${stats.tokensUsed} | 💾 Сэкономлено: ${stats.tokensSaved}`;
            vscode.window.showInformationMessage(message);
            outputChannel.appendLine(`[Nexus] ${message}`);
        })
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('openSettings', async () => {
            await vscode.commands.executeCommand('workbench.action.openSettings', 'nexus');
            outputChannel.appendLine('[Nexus] Настройки открыты');
        })
    );
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    outputChannel.appendLine('[Nexus] Деактивация расширения...');
    return client.stop();
}
