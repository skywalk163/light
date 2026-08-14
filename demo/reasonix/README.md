# Reasonix 推理引擎

> 段言 (Duan) 编程语言能力演示 — 基于 Chain-of-Thought 的多步推理引擎

## 概述

Reasonix 是一个交互式推理引擎 demo，展示段言编程语言在复杂推理任务中的应用能力。它通过 **4 阶段 Chain-of-Thought** 推理流程，对用户提出的问题进行分析和解答。

支持两种运行模式：

- **AI 模式** — 调用 OpenAI 兼容 API（如 DeepSeek、OpenAI、通义千问等）进行真实推理
- **模拟模式** — 使用内置模拟内容演示推理流程（无需 API 密钥）

## 快速开始

### 1. 安装依赖

确保已安装 `requests` 库：

```bash
pip install requests
```

### 2. 配置 API 密钥（可选）

复制配置文件模板并填入你的 API 信息：

```bash
cp demo/reasonix/.env.example demo/reasonix/.env
```

编辑 `demo/reasonix/.env`，设置以下参数：

| 参数 | 说明 | 示例值 |
|------|------|--------|
| `REASONIX_API_KEY` | API 密钥（必填） | `sk-xxxxxxxxxxxxxxxx` |
| `REASONIX_API_BASE_URL` | API 基础地址 | `https://api.deepseek.com/v1` |
| `REASONIX_MODEL` | 模型名称 | `deepseek-chat` 或 `gpt-4o-mini` |
| `REASONIX_MAX_TOKENS` | 最大 Token 数 | `2000` |
| `REASONIX_TEMPERATURE` | 生成温度（0.0-2.0） | `0.7` |

> 未配置 API 密钥时，demo 自动以模拟模式运行，无需任何配置即可体验。

### 3. 运行 Demo

在项目根目录执行：

```bash
python -m cli.duan run demo/reasonix/主.duan --backend src
```

或者使用 `duan` 命令（如果已安装）：

```bash
duan run demo/reasonix/主.duan --backend src
```

### 4. 使用

启动后进入交互式界面，支持以下命令：

| 命令 | 说明 |
|------|------|
| `你的问题` | 直接输入问题，引擎将进行 4 阶段推理 |
| `帮助` | 显示帮助信息 |
| `历史` | 查看推理历史记录 |
| `清屏` | 清空屏幕 |
| `退出` | 退出程序 |

#### 示例问题

```
天空为什么是蓝色的？
什么是黑洞？
请用 Python 写一个快速排序算法。
解释一下量子纠缠。
```

## 推理流程

引擎使用 **4 阶段 Chain-of-Thought** 推理：

### 阶段 1：理解问题
分析问题的核心内容，识别问题类型和关键信息。

### 阶段 2：信息提取
提取关键数据和实体，识别已知条件和约束。

### 阶段 3：逻辑推理
基于已知信息进行逻辑推理和计算，构建推理链条。

### 阶段 4：验证答案
验证推理结论的正确性和完整性。

## 架构说明

```
demo/reasonix/
├── .env.example      # API 配置模板（已提交到仓库）
├── .env              # API 配置（已加入 .gitignore，不提交）
├── ai_api_helper.py  # Python 辅助模块，封装 AI API HTTP 调用
├── 主.duan           # 主入口，交互式 CLI 界面
├── 引擎.duan         # 核心引擎，管理推理流程
├── 思考链.duan       # 思考链数据结构，记录推理过程
├── 提示词.duan       # AI 提示词模板，生成阶段提示
├── 工具.duan         # 工具函数，格式化输出、UI 显示
└── README.md         # 本文件
```

### 模块依赖关系

```
主.duan
  ├── 引擎.duan
  │     ├── 思考链.duan
  │     ├── 提示词.duan
  │     ├── 工具.duan
  │     └── ai_api_helper.py (Python)
  └── 工具.duan
```

## AI 模式 vs 模拟模式

| 特性 | AI 模式 | 模拟模式 |
|------|---------|----------|
| API 密钥 | 需要配置 | 不需要 |
| 推理质量 | 真实 AI 推理 | 固定模拟内容 |
| 响应速度 | 依赖 API 响应 | 即时 |
| 使用场景 | 实际使用 | 演示和测试 |

## 常见问题

### Q: 启动时提示 `module 'ai_api_helper' has no attribute 'xxx'`

确保已安装 `requests` 库：`pip install requests`

### Q: AI 模式返回超时

检查网络连接，或增大 `.env` 中的 `REASONIX_MAX_TOKENS` 值。某些模型处理长上下文可能需要更长时间。

### Q: 如何切换不同的 AI 模型？

修改 `.env` 文件中的 `REASONIX_API_BASE_URL` 和 `REASONIX_MODEL`：

- **DeepSeek**: `https://api.deepseek.com` + `deepseek-chat`
- **OpenAI**: `https://api.openai.com/v1` + `gpt-4o-mini`
- **通义千问**: `https://dashscope.aliyuncs.com/compatible-mode/v1` + `qwen-plus`

### Q: 如何重置历史记录？

重启程序即可清空历史记录。