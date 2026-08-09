# LSP 集成

光明 LSP (Language Server Protocol) 提供 IDE 智能支持。

## 启动 LSP 服务器

```bash
python lsp/light_lsp_main.py
```

## 功能

- **语法错误检查**：实时显示语法错误
- **自动补全**：关键字、函数名、变量名补全
- **悬停信息**：显示变量类型和文档
- **跳转定义**：跳转到变量/函数定义位置
- **代码大纲**：显示文件结构
- **诊断信息**：错误和警告

## 编辑器集成

### VS Code

在 `settings.json` 中配置：

```json
{
    "light.lsp.enabled": true,
    "light.lsp.serverPath": "python lsp/light_lsp_main.py"
}
```

### Neovim

```lua
require('lspconfig').light.setup({
    cmd = {"python", "lsp/light_lsp_main.py"},
})
```