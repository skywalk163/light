# light-mcp：把光明接进任何支持 MCP 的宿主

一个文件、纯标准库、只走 stdio。宿主（Cursor / Claude Code / WorkBuddy / 自家
agent 框架）配好之后，就能直接调：

| 工具 | 入参 | 返回 |
|---|---|---|
| `light_check` | `path`, `strict?`, `run?` | `light ai check --json` 的原样 JSON + `exit_code` |
| `light_run` | `path`, `args?`, `timeout_s?` | `{ok, rc, stdout, stderr, timed_out, duration_ms}` |
| `light_patch` | `path`, `span: {line, column, end_column}`, `replacement` | `{ok, file, span, changed, new_text}`（**不写盘**） |

对 agent 来说省掉三件最容易翻车的事：自己拼 shell、自己解析 stdout、自己处理编码
（中文路径 / Windows 代码页 / 超时）。所有返回都是**结构化 JSON**，字段名与
`light ai check --json` 同一口径，两个入口可以复用同一套解析逻辑。

## 配置

把 `mcp.example.json` 里的 `C:/path/to/light` 全部换成你本机光明仓的绝对路径
（就是 `cli/light.py` 所在的那一层），然后按宿主的要求放到对应位置。

**通用 JSON（Cursor：`~/.cursor/mcp.json` 或项目 `.cursor/mcp.json`）**

```json
{
  "mcpServers": {
    "light": {
      "command": "python",
      "args": ["-X", "utf8", "C:/path/to/light/mcp/light_mcp.py"],
      "env": {"PYTHONIOENCODING": "utf-8", "LIGHT_ROOT": "C:/path/to/light"}
    }
  }
}
```

**Claude Code 一行版**

```bash
claude mcp add light -- python -X utf8 C:/path/to/light/mcp/light_mcp.py
```

**Windows 路径写法**：JSON 里用正斜杠最省事（`C:/path/to/light/mcp/light_mcp.py`）。
要用反斜杠必须写双反斜杠（`C:\\path\\to\\light\\mcp\\light_mcp.py`），单反斜杠会被
JSON 当成转义字符，配置直接解析失败。路径里有空格就原样放进字符串，不要自己加引号。

**Linux / macOS**

```json
{
  "mcpServers": {
    "light": {
      "command": "python3",
      "args": ["-X", "utf8", "/home/me/light/mcp/light_mcp.py"],
      "env": {"PYTHONIOENCODING": "utf-8", "LIGHT_ROOT": "/home/me/light"}
    }
  }
}
```

`LIGHT_ROOT` 可以不写（服务端按自己所在的 `mcp/` 上一级推导），但仓根和脚本不在同一
目录（比如把服务端软链到别处）时请显式给。

## 用法示例

改代码的标准闭环：先看诊断 → 按诊断改 → 拿新文本 → 再复验。

```json
// 1) 检查
{"name": "light_check", "arguments": {"path": "示例/你好.light", "run": true}}
// → {"ok": false, "stage": "语法", "diagnostics": [{"code": "L0000", "line": 3, "column": 10, "message": "期望 冒号「:」…", "fixes": [...]}], "exit_code": 1}

// 2) 局部改（行/列 1 起，end_column 不含）
{"name": "light_patch", "arguments": {"path": "示例/你好.light", "span": {"line": 3, "column": 10, "end_column": 11}, "replacement": ":"}}
// → {"ok": true, "changed": true, "new_text": "…整份新源码…"}   ← 记得自己写盘

// 3) 跑一下
{"name": "light_run", "arguments": {"path": "示例/你好.light", "args": ["甲", "乙"], "timeout_s": 30}}
// → {"ok": true, "rc": 0, "stdout": "你好，光明\n", "stderr": "", "duration_ms": 812}
```

`light_run` 的 `args` 会经 `--` 分隔符原样交给脚本（脚本侧用 `用户参数()` 取），
不会被当成 CLI 开关。

## 行为约定

- **永不崩**：工具内部失败一律走 `isError: true`，`content[0].text` 里仍是结构化
  JSON（`{"ok": false, "code": "L_MCP_*", "error": "…"}`），进程继续服务。
- **不写盘**：`light_patch` 只返回 `new_text`，落不落盘由调用方决定。
- **不判业务**：源码有错时 `light_check` 仍返回 `isError: false`，`ok: false` 是
  业务结果，不是工具故障；要不要修是调用方的事。
- **span 口径**：与 `light patch` 完全一致（行/列 1 起、端列不含、单行 span），
  底层复用 `src/patch_engine.py`，所以越界/交叠/不闭合的拒绝原因与 CLI 逐字相同。
- **超时**：`light_check` 内部上限 240s；`light_run` 默认 30s、上限 600s，超时返回
  `rc: null` + `timed_out: true`（不抛异常）。
- **`strict`**：只影响 stdout 的解析方式——`true` 要求整段 stdout 恰好是一个 JSON
  对象，`false`（默认）在夹带日志时仍尝试抽出 JSON。它不改变 `ok` 判定。

## 排错

| 现象 | 原因 / 处理 |
|---|---|
| 宿主里工具列表是空的 | `command` 写成了 `python` 但 PATH 里没有；换成 `python3` 或绝对路径的解释器 |
| 连上就退出 / `找不到光明仓根` | `mcp/light_mcp.py` 不在仓内，或仓根下没有 `cli/light.py`；补 `LIGHT_ROOT` 或用 `--root` |
| 中文路径报「文件不存在」 | 服务端会把相对路径按**宿主进程**的当前目录补成绝对路径；不确定就传绝对路径 |
| 输出里中文变 `???` | 宿主没按 UTF-8 读；配置里务必带 `PYTHONIOENCODING=utf-8`（服务端对子进程也强制了 UTF-8） |
| `light_check` 很慢（~2s） | 正常：每次都要拉起一次 `light` 解释器（含解析器导入）。批量检查请复用同一次 `run: true` |

## 自测

```bash
python -m pytest -q tests/test_T0461_mcp.py
```

只验证一件事：宿主视角下这套协议能跑通——`initialize` → `tools/list` → 三个工具
的真实调用（含坏文件诊断、`light_patch` 与 `light patch` 输出逐字一致、不存在的
路径返回 `isError` 且进程仍活着）。
