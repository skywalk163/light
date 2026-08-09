# 光明 (Light) VS Code 扩展

## 功能特性

### 语言服务 (LSP)
- 代码补全 — 关键字、动词、本地变量/函数智能补全
- 悬停提示 — 关键字说明、动词元数、函数签名、类型信息
- 跳转定义 — 变量/函数/类定义跳转
- 引用查找 — 跨文件查找引用
- 文档符号 — 大纲视图（函数/类/变量）
- 代码格式化 — 全文/选区格式化
- 重命名 — 跨文件重命名
- 代码操作 — 快速修复建议
- 实时诊断 — 语法错误 + 类型检查，保存时自动更新

### 编译 & 运行
- 运行当前文件（`Ctrl+Shift+R`）
- 编译为 Python 文件
- LLVM-Typed 原生编译为 EXE
- 语法检查（输出到 Problems 面板，支持点击跳转）
- 类型检查（三级：签名/变量/表达式）

### 交互式开发
- REPL 交互式解释器
- 代码片段 — 快速生成函数/条件/循环/类模板

### 调试支持
- 断点设置、单步执行、变量查看、调用栈显示

### 构建系统
- Task Provider — 支持 `Ctrl+Shift+B` 构建
- 4 个预置任务：编译 / LLVM编译 / 运行 / 语法检查
- 错误自动解析到 Problems 面板

### 状态栏
- 右下角语言服务状态指示器（运行中 / 错误 / 离线）
- 点击状态栏图标可重启 LSP

## 安装

### 方法 1: 从 VSIX 安装

```bash
cd vscode-extension
npm install
npm run compile
vsce package
code --install-extension light-language.vsix
```

### 方法 2: 开发模式

```bash
cd vscode-extension
npm install
npm run watch
# 按 F5 在新的 VS Code 窗口中打开
```

## 配置

```json
{
  "light.serverPath": "path/to/lsp/server.py",
  "light.pythonPath": "python",
  "light.trace.server": "off"
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `light.serverPath` | LSP 服务器路径 | 自动查找 |
| `light.pythonPath` | Python 解释器路径 | python / python3 |
| `light.trace.server` | LSP 通信日志级别 | off |

## 快捷键

| 命令 | 快捷键 | 说明 |
|------|--------|------|
| 运行当前文件 | `Ctrl+Shift+R` | 解释执行当前光明文件 |
| 编译当前文件 | `Ctrl+Shift+B` | 编译为 Python 文件 |

## 命令面板

| 命令 | 说明 |
|------|------|
| `光明: 运行当前文件` | 解释执行当前文件 |
| `光明: 检查语法` | 语法检查，结果输出到 Problems 面板 |
| `光明: 编译当前文件` | 编译为 Python 文件 |
| `光明: 编译当前文件 (LLVM-Typed 原生)` | LLVM 原生编译为 EXE |
| `光明: 类型检查当前文件` | 类型检查，结果输出到 Problems 面板 |
| `光明: 打开 REPL` | 打开光明交互式解释器 |
| `光明: 重启语言服务器` | 重启 LSP 服务器 |

## 调试

### 启动调试

1. 打开要调试的 `.light` 文件
2. 按 `F9` 设置断点
3. 按 `F5` 开始调试
4. 使用调试工具栏进行单步执行

### 调试配置

```json
{
  "type": "light",
  "request": "launch",
  "program": "${file}",
  "stopOnEntry": true
}
```

## 文件关联

扩展会自动关联 `.light` 文件：

```json
{
  "files.associations": {
    "*.light": "light"
  }
}
```

## 问题反馈

如遇到问题，请提交 Issue：
https://github.com/light-lang/light/issues

## 许可证

MIT License