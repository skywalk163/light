# VS Code 配置

## 安装扩展

1. 下载 `vscode-light` 扩展：
   ```bash
   git clone https://github.com/light-lang/light.git
   cd light/vscode-light
   code --install-extension light-lang.vsix
   ```

2. 或在 VS Code 扩展商店搜索 "Light"

## 功能特性

- **语法高亮**：L0 关键字、L3/L4 嵌入块
- **代码片段**：`设` `若` `段` `类` 等
- **Ctrl+Shift+R**：运行当前文件
- **解析 AST**：查看代码解析树
- **调试支持**：断点调试、变量查看

## 配置建议

在 `.vscode/settings.json` 中添加：

```json
{
    "light.enableLinting": true,
    "light.pythonPath": "python",
    "light.formatOnSave": true,
    "files.associations": {
        "*.light": "light"
    }
}
```