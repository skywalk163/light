# T-0209 光明P1：归约 一调就崩 + 映射/筛选 返回迭代器 [L-257/L-258]

## 做了什么
- `src/code_generator.py`（legacy 后端；`cli.light run` 与 `cli.light_unified run` 默认都走此腿）：
  1. 产物序言补 `import functools`——原缺失，`归约` 一调即 `NameError: name 'functools'
     is not defined`；unified 序言 L518 早已有无条件 import，本次对齐。
  2. `_DATA_FIRST_BUILTINS` 增补 `归约/折叠 → functools.reduce`；`_reorder_data_first_args`
     放开 reduce 的 3 参形态（`归约(数据, 函数, 初值)`，初值保持末位），
     换序返回 `[args[1], args[0]] + list(args[2:])`。
  3. `映射/筛选`（2 参）与 `枚举`（1~2 参）在发射点外层包 `list(...)`，返回**列表**
     而非惰性迭代器（不再打 `<map object at 0x…>`，`长()`/下标/`转字符串` 可用）。
- `src/code_generator_unified.py`（unified 后端）：镜像上述三点——新增 `_looks_data_arg`
  /`_looks_callable_arg`/`_reorder_data_first_args` 与 `list()` 包裹（判不定不换序，不抛错）。
- 新建 `tests/unit/test_LH35_归约与高阶内置.py`：`python -m cli.light run` **真跑**，
  一份源码 7 行 stdout 覆盖任务卡四条验收（归约=12 / 映射=[2,4,6] 且长=3 /
  筛选=[2,4] 且长=2 / 枚举长=3）加映射结果下标可用。

## 验证
- 契约命令 `python3 -m pytest -q tests/unit/test_LH35_归约与高阶内置.py` → **5 passed**。
- 回归 `python3 -m pytest -q tests/test_frontend_blockers_run.py -k a3` → **6 passed**（A3 语序护栏未破）。
- `tests/unit/test_R158_地板证据窗口漂移.py` 在基线 36d2b5429 与本改动后**同为 6 failed / 4 passed**
  （stash 对比实测确认）：pre-existing 失败，与 T-0209 无关；本次未改 `stdlib/builtins.py`。
- 语序裁定：卡面 `归约([1,2,3], 加倍, 0) → 12` 未给 `加倍` 定义，依 `docs/语义密度示例集.md:350`
  `归约(组.值, 段(a, b) 返 a + b["金额"], 0)` 判定 `归约` 为**二元折叠**，故测试用
  `加倍(累积, 项) 返回 累积 + 项 * 2`（0+2+4+6=12）。

## 没做 / 风险（诚实声明）
- **unified 后端改动无运行时验证**：本机 `light_visitor`/antlr4 缺失
  （`LightUnifiedCLI().antlr_available == False`），仅 `py_compile` 通过；`cli.light_unified`
  的 `run` 与默认 `compile` 都回落到 legacy `PythonCodeGenerator`，故契约用例与 A3 回归
  实际覆盖的只是 legacy 腿。若 CI 具备 antlr 环境，请以 unified 腿复跑本文件。
- unified 侧 `_reorder_data_first_args` 对「lambda 在前」**不抛 CodeGenError**（src 侧会抛），
  有意不追求完全 parity 以降风险。
- 未改 `stdlib/builtins.py`（地板自举率门禁禁区）、未动其它任务卡与 agents 配置、未写任何 token/密钥。