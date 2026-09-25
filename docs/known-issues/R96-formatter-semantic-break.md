# R96-KI-01：`light fmt` 语义破坏缺陷

- 状态：**open**（锁定，默认关闭执行）
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

## 根因（初步）

`src/formatter/light_formatter.py` 的 `LightFormatter.format()` 在改写时：

1. 为不含冒号的语句**错误补冒号**（如 `返回 x + y` → `返回 x + y：`），违反光明语法（冒号只在复合语句首行末尾）；
2. **缩进层级被重排**（2 空格块 → 4/8 空格且不对应语句块结构），导致嵌套块错位。

二者叠加使产物无法被 lexer/parser 接受。

## 当前处置（R96）

- `cli/light.py` 的 `cmd_fmt` 已加 `--force` 安全闸门：`light fmt` 默认输出中文风险提示并 `exit(2)`，**不执行、不破坏文件**；
- 已知 `--check` 是安全的（只体检，不改写）；
- `src/formatter/__init__.py` 已导出 `run_formatter`，但入口默认关闭。

## 不在 R96 范围

- 不修复 formatter 本体（属 src 工具链，需独立回归，留给 R97 T9）；
- 不回退 `run_formatter` 导出（保留，便于 R97 直接修）。

## 验收（关闭标准）

- 对任意 `examples/` 与 `stdlib/` 下的 `.light`（`find` 全量）执行 `light fmt --force` 后，
  `light check` 的通过率与格式化前**完全一致**（允许空行/缩进规范化，禁止语义改变）；
- 新增回归测试 `tests/unit/test_formatter_safety.py`，含 `_test_nested_closure.light` 用例。
