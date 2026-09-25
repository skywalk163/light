# R96-KI-01：`light fmt` 语义破坏缺陷

- 状态：**resolved (R97)**（R97 T9 已修复，验收通过）
- 引入轮次：固有缺陷（R96 首次接通 `fmt` 入口时暴露）
- 严重度：高（会静默破坏合法源文件）
- 修复轮次：计划 **R97（T9）**

## 现象

`light fmt <文件>` 会把**语法合法的 `.light` 代码**改写成无法解析的形式。

复现步骤（2026-09-25 实测）：

```bash
cd light-merge
cp examples/_test_nested_closure.light /tmp/t.light
light check /tmp/t.light      # ✅ rc=0 类型检查通过
light fmt /tmp/t.light        # 提示"已格式化"
light check /tmp/t.light      # ❌ rc=1 解析错误
```

## 根因（确认）

`src/formatter/light_formatter.py` **与**顶层 `src/formatter.py`（`cli/light_unified.py` 经 `from formatter import run_formatter` 引用）的 `format()` 用「基于行首前缀猜测」的 regex 启发式改写，在 光明 这种**缩进敏感**且关键字多为中文的语言上必然出错：

1. **错误补冒号**：`NEEDS_COLON` 含单字关键字 `返/跳/过/抛/终`，`返回 x` 被前缀匹配到 `返` → 追加 `：`（`返回 x + y：`），违反语法；
2. **缩进被整体重排**为 4 空格且不对应真实块结构（光明块结构由缩进决定），导致嵌套块错位。

二者叠加使 `light fmt` 把**合法代码**改写成无法解析的形式。

## 修复（R97 T9，已落地）

将两份 formatter 实现**收敛为「空白安全子集」**，只做绝不改变语义的变换：

- 统一换行符为 `\n`（CRLF 由 `run_formatter` 还原）；
- 去除每行行尾空白；
- 折叠 3+ 连续空行为 2 个；
- 去除文件首尾多余空行；
- 确保文件以单个换行结尾。

**安全性证明**：光明块结构完全由「每行缩进 + 行内 token」决定；安全子集对二者**逐行精确保留**（仅 `rstrip` 行尾空白，不碰行首缩进、不增删 token），因此产物解析结果与输入**必然一致**——从根本上消除 R96-KI-01。

**配套动作**：
- `cli/light.py` 的 `cmd_fmt` 移除 `--force` 默认关闭闸门（`light fmt` 自 R97 起默认开放且安全；`--force` 保留为兼容无操作项）；
- `tests/test_formatter.py` 重写为安全子集契约；新增 `tests/unit/test_formatter_safety.py` 回归测试（含 `_test_nested_closure.light` 复现 + `examples/` 全量 + `stdlib/` 抽样的不变量断言）。

> 后续若需"缩进规范化 / 冒号对齐 / 导入排序"等增强，**必须接入真实解析器**（复用 `src/` 的 lexer/parser），切勿退回到行前缀猜测启发式。

## 验收（已通过）

- 对任意 `examples/` 与 `stdlib/` 下的 `.light` 执行 `light fmt` 后，`light check` 的通过率与格式化前**完全一致**（解析保留不变量已纳入回归测试逐文件断言）；
- 新增回归测试 `tests/unit/test_formatter_safety.py`，含 `_test_nested_closure.light` 用例 + 全量/抽样不变量断言 + 幂等性 + 冒号防护；
- 端到端验证：`light fmt`（默认开放）对复现用例改写后 `light check` 仍 rc=0。
