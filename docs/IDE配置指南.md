# 段言（DuanLang）IDE 配置指南

## 目录

1. [VS Code 配置](#vs-code-配置)
2. [JetBrains IDEs 配置](#jetbrains-ides-配置)
3. [Neovim/Vim 配置](#neovimvim-配置)
4. [Emacs 配置](#emacs-配置)
5. [通用配置建议](#通用配置建议)
6. [故障排除](#故障排除)

---

## VS Code 配置

### 安装扩展

1. 打开 VS Code
2. 进入扩展市场（`Ctrl+Shift+X`）
3. 搜索 `段言` 或 `DuanLang`
4. 点击安装

### 手动安装（VSIX）

```bash
cd vscode-extension
npm install
npm run compile
npx vsce package
code --install-extension duan-language-*.vsix
```

### 功能特性

安装后自动获得以下功能，无需额外配置：

- **语法高亮** — 中文关键字、内置函数、类型、运算符、注释等
- **代码补全** — 关键字、动词、内置函数、变量名、代码片段
- **实时诊断** — 语法错误和类型检查，保存时自动更新
- **跳转定义** — 变量/函数/类定义跳转
- **悬停提示** — 关键字说明、函数签名、类型信息
- **代码格式化** — 全文/选区格式化
- **文档符号** — 大纲视图
- **状态栏指示器** — 显示 LSP 连接状态和版本号

### 快捷键

| 命令 | 快捷键 | 说明 |
|------|--------|------|
| 运行当前文件 | `Ctrl+Shift+R` | 解释执行当前段言文件 |
| 编译当前文件 | `Ctrl+Shift+B` | 编译为 Python 文件 |
| 语法检查 | `Ctrl+Shift+C` | 检查语法错误 |
| 编译（可选后端） | `Ctrl+Shift+E` | 编译当前文件 |
| 类型检查 | `Ctrl+Shift+T` | 类型检查 |
| 打开 REPL | `Ctrl+Shift+I` | 打开交互式解释器 |
| 格式化 | `Shift+Alt+F` | 格式化代码 |

### 推荐配置

在 `.vscode/settings.json` 中添加：

```json
{
    "files.associations": {
        "*.duan": "duan"
    },
    "[duan]": {
        "editor.tabSize": 4,
        "editor.insertSpaces": true,
        "editor.formatOnSave": true,
        "editor.suggest.snippetsPreventQuickSuggestions": false
    },
    "duan.trace.server": "off",
    "duan.format.enable": true,
    "duan.format.indentSize": 4,
    "duan.format.trimTrailingWhitespace": true,
    "duan.format.insertFinalNewline": true
}
```

### 调试配置

在 `.vscode/launch.json` 中添加：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "duan",
            "request": "launch",
            "name": "调试当前文件",
            "program": "${file}",
            "stopOnEntry": true
        }
    ]
}
```

---

## JetBrains IDEs 配置

JetBrains 全系 IDE（IntelliJ IDEA、PyCharm、GoLand 等）通过 **LSP 插件** 支持段言。

### 安装步骤

1. 打开 IDE，进入 `File → Settings → Plugins`
2. 搜索并安装 **LSP Support** 插件（作者: flaupretre, 市场搜索 "LSP"）
3. 安装完成后重启 IDE

### 配置 LSP 插件

1. 进入 `File → Settings → Tools → LSP Support`
2. 点击 **Server configurations** 下的 `+` 添加新服务器
3. 配置如下：

```
Name: 段言
Language ID: duan
File types: duan
Extension: duan
Server command: python
Arguments: <项目路径>/lsp/duan_lsp.py
Transport: stdio
```

### 文件关联

1. 进入 `File → Settings → Editor → File Types`
2. 在 Recognized File Types 中找到 `duan`（或新建）
3. 在 Registered Patterns 中添加 `*.duan`

### 推荐插件

- **LSP Support** — 核心 LSP 客户端
- **Rainbow Brackets** — 彩色括号配对
- **Indent Rainbow** — 缩进着色

---

## Neovim/Vim 配置

### 方式一：通过 coc.nvim（推荐）

#### 安装 coc.nvim

```vim
" 使用 vim-plug
Plug 'neoclide/coc.nvim', {'branch': 'release'}
```

#### 配置 LSP

在 `coc-settings.json` 中添加：

```json
{
    "languageserver": {
        "duan": {
            "command": "python",
            "args": ["<项目路径>/lsp/duan_lsp.py"],
            "filetypes": ["duan"],
            "rootPatterns": [".git", "package.toml"],
            "settings": {}
        }
    }
}
```

#### 文件类型检测

在 `~/.vimrc` 或 `~/.config/nvim/init.vim` 中添加：

```vim
" 文件类型检测
autocmd BufRead,BufNewFile *.duan set filetype=duan

" 语法高亮
syntax on

" 缩进设置
autocmd FileType duan setlocal tabstop=4 shiftwidth=4 expandtab
```

### 方式二：通过内置 LSP（Neovim 0.5+）

在 `~/.config/nvim/init.lua` 中添加：

```lua
vim.api.nvim_create_autocmd({ "BufRead", "BufNewFile" }, {
    pattern = "*.duan",
    callback = function()
        vim.bo.filetype = "duan"
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = "duan",
    callback = function()
        vim.bo.tabstop = 4
        vim.bo.shiftwidth = 4
        vim.bo.expandtab = true
    end,
})

-- LSP 配置
local lspconfig = require("lspconfig")
lspconfig.duan = {
    default_config = {
        cmd = { "python", "<项目路径>/lsp/duan_lsp.py" },
        filetypes = { "duan" },
        root_dir = lspconfig.util.find_git_ancestor,
        settings = {},
    },
}
lspconfig.duan.setup({})
```

### 语法高亮文件

创建 `~/.config/nvim/syntax/duan.vim`：

```vim
if exists("b:current_syntax")
  finish
endif

syntax keyword duanKeyword 设 为 定义 常量 如果 否则 否则若 若 那么 则 遍历 当 跳出 跳过 返回 结束 段落 函数 段 接收 类 继承 构造 属性 接口 实现 协议 导入 导出 从 尝试 捕获 抛出 最终 异步 等待 使用 匹配 情况 真 假 空 无 新建 己 父 抽象 静态 私有 公有 保护 嵌入 结束嵌入 标注 可空 断言 创建 加载 类型 对于 范围 输入 打印 求幂 整除 取余

syntax keyword duanType 整数 浮数 小数 字符串 文本 列表 字典 集合 布尔 任意 数 串 列 典 集 可空

syntax keyword duanBoolean 真 假
syntax keyword duanNull 空 无

syntax match duanComment "#.*$"
syntax region duanString start='"' end='"' contains=duanEscape
syntax region duanString start="'" end="'" contains=duanEscape
syntax region duanString start='`' end='`' contains=duanEscape
syntax region duanString start='「' end='」'
syntax match duanEscape "\\." contained

syntax match duanNumber "\v<\d+>"
syntax match duanNumber "\v<\d+\.\d+([eE][+-]?\d+)?>"
syntax match duanNumber "\v<0[xX][0-9a-fA-F]+>"
syntax match duanNumber "\v<0[bB][01]+>"

highlight link duanKeyword Keyword
highlight link duanType Type
highlight link duanBoolean Boolean
highlight link duanNull Constant
highlight link duanComment Comment
highlight link duanString String
highlight link duanNumber Number
highlight link duanEscape SpecialChar

let b:current_syntax = "duan"
```

---

## Emacs 配置

### 方式一：通过 lsp-mode

#### 安装依赖

```elisp
;; 确保已安装 lsp-mode
(use-package lsp-mode
  :ensure t
  :commands lsp)

;; 注册段言客户端
(require 'lsp-mode)
```

#### 配置 LSP 客户端

```elisp
(lsp-register-client
 (make-lsp-client
  :new-connection (lsp-stdio-connection
                   '("python" "<项目路径>/lsp/duan_lsp.py"))
  :activation-fn (lsp-activate-on "duan")
  :server-id 'duan-ls
  :multi-root t))

;; 文件类型关联
(add-to-list 'auto-mode-alist '("\\.duan\\'" . duan-mode))
```

#### 语法高亮

创建 `duan-mode.el`：

```elisp
(define-derived-mode duan-mode prog-mode "段言"
  "段言编程语言的主模式"
  (setq font-lock-defaults '(duan-font-lock-keywords))

  ;; 缩进设置
  (setq tab-width 4)
  (setq indent-tabs-mode nil)

  ;; 注释设置
  (setq comment-start "#")
  (setq comment-end ""))

(defvar duan-font-lock-keywords
  `((,(regexp-opt '("设" "为" "定义" "常量" "如果" "否则" "否则若"
                    "若" "那么" "则" "遍历" "当" "跳出" "跳过"
                    "返回" "结束" "段落" "函数" "段" "接收" "类"
                    "继承" "构造" "属性" "接口" "实现" "协议"
                    "导入" "导出" "从" "尝试" "捕获" "抛出" "最终"
                    "异步" "等待" "使用" "匹配" "情况" "真" "假"
                    "空" "无" "新建" "己" "父" "抽象" "静态"
                    "私有" "公有" "保护" "嵌入" "结束嵌入" "标注"
                    "可空" "断言" "创建" "加载" "类型" "对于"
                    "范围" "输入" "打印" "求幂" "整除" "取余")
                  'words)
     . font-lock-keyword-face)
    (,(regexp-opt '("整数" "浮数" "小数" "字符串" "文本" "列表"
                    "字典" "集合" "布尔" "任意" "数" "串" "列"
                    "典" "集" "可空")
                  'words)
     . font-lock-type-face)
    (,(regexp-opt '("打印" "输出" "读取" "输入" "长度" "类型"
                    "转整数" "转小数" "转字符串" "范围" "排序"
                    "反转" "求和" "筛选" "映射")
                  'words)
     . font-lock-builtin-face)
    ("#.*$" . font-lock-comment-face)
    ("\"\\([^\"]*\\)\"" . font-lock-string-face)
    ("'\\([^']*\\)'" . font-lock-string-face)
    ("`\\([^`]*\\)`" . font-lock-string-face)
    ("\\(\\d+\\)" . font-lock-constant-face)
    ("\\(0[xX][0-9a-fA-F]+\\)" . font-lock-constant-face)))

(provide 'duan-mode)
```

### 方式二：通过 eglot

```elisp
(use-package eglot
  :ensure t
  :config
  (add-to-list 'eglot-server-programs
               '(duan-mode . ("python" "<项目路径>/lsp/duan_lsp.py"))))

(add-to-list 'auto-mode-alist '("\\.duan\\'" . duan-mode))
```

---

## 通用配置建议

### 字符编码

所有段言源文件应使用 **UTF-8** 编码保存。建议在编辑器中设置：

```json
{ "files.encoding": "utf8" }
```

### 缩进风格

段言推荐使用 **4 空格缩进**（不使用制表符）：

```json
{ "editor.tabSize": 4, "editor.insertSpaces": true }
```

### 行尾序列

建议使用 **LF**（Unix 风格）行尾：

```json
{ "files.eol": "\n" }
```

### 建议安装的通用工具

- **EditorConfig** — 跨编辑器保持一致的编码风格（`.editorconfig` 文件）
- **GitLens** — Git 历史追溯
- **Error Lens** — 行内错误提示增强

---

## 故障排除

### LSP 服务器无法启动

**症状**：状态栏显示"离线"或"错误"。

**排查步骤**：

1. 检查 Python 是否可用：
   ```bash
   python --version
   # 或
   python3 --version
   ```

2. 检查 LSP 服务器路径是否正确：
   ```bash
   python <项目路径>/lsp/duan_lsp.py
   ```
   如果看到 `Content-Length: ...` 输出，说明服务器正常。

3. 检查 VS Code 输出日志：
   - 打开 `查看 → 输出`
   - 在下拉菜单中选择 `段言` 或 `段言 LSP Trace`

4. 重启 LSP 服务器：
   - 点击状态栏的段言图标
   - 或执行命令 `段言: 重启语言服务器`

### 语法高亮不生效

**症状**：.duan 文件没有颜色高亮。

**解决方案**：

1. 确保文件扩展名为 `.duan`
2. 手动设置语言模式：
   - VS Code: 右下角语言模式 → 选择 `段言`
   - 其他编辑器: 设置文件类型为 `duan`
3. 重新加载窗口

### 代码补全不工作

**症状**：输入代码时没有自动补全提示。

**解决方案**：

1. 确认 LSP 服务器已启动（状态栏显示 ✓）
2. 检查是否在 `.duan` 文件中编辑
3. 尝试手动触发补全：`Ctrl+Space`
4. 在 VS Code 设置中检查：
   ```json
   { "editor.quickSuggestions": { "other": true, "comments": false, "strings": false } }
   ```

### 格式化不生效

**症状**：`Shift+Alt+F` 没有格式化代码。

**解决方案**：

1. 确保设置中启用格式化：
   ```json
   { "duan.format.enable": true }
   ```
2. 确认文件语言为 `duan`

### 调试器无法启动

**症状**：F5 调试时没有反应或提示错误。

**解决方案**：

1. 确保已创建 `.vscode/launch.json` 调试配置
2. 检查调试适配器路径：
   - 默认路径：`<项目>/vscode-extension/debug-adapter/duan_debug_adapter.py`
   - 确保 Python 依赖已安装
3. 在 `.duan` 文件中设置断点后再启动调试

### 跨平台路径问题

**Windows 用户注意**：

- 确保 Python 在 PATH 环境变量中
- 如果使用 WSL，建议在 WSL 中安装 VS Code 和扩展
- 路径中的反斜杠 `\` 使用双反斜杠 `\\` 或正斜杠 `/`

---

*段言 v6.0.0 — 用中文，写世界*