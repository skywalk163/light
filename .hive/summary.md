# T-0199 工作说明（LH-21｜light check 查不出未定义名 + LH-09｜导入名被局部遮蔽零告警）

## 结论
LH-21：`light check` 现用「AST + SemanticAnalyzer」做作用域感知的未定义名检查（E002），能报 `打印 临时目录()` / `设 甲 为 1`+`打印 乙`，并按 内置名/导入名/模块级段落/局部变量 分类给提示；解析器不可用时回退文本启发式。LH-09：`从 X 导入` 的名字被段落内 `设` 遮蔽时，新增 L-166 告警（提示 UnboundLocalError）。

## 改动
1. 新建 `src/linter/builtins.py`：内置名清单（手工兜底 + 动态读 `code_generator.builtin_map`/`BUILTIN_TYPES`），刻意不含 `去空白`。
2. 改 `src/linter/light_linter.py`：`_check_undefined_variable` 走 AST（`_collect_undefined_from_ast` + `_classify_undefined` + `_report_undefined`，E002）；`_check_shadowed_variable` 扩展：收集 `从 X 导入` 名，段落内同名 `设` 报 L-166（LH-09）。
3. 新建 `tools/内置名清单.py`：机器可读 JSON（--json/--python/--check）。
4. 新建 `tests/unit/test_LH21_未定义名.py`：6 组验收用例（未定义名 / 不误报 / JSON / 文档门禁 / LH-09 正反例）。

## 验证
本环境 bash 沙箱不可用（无 bubblewrap/Landlock、无审批通道，含子代理同样被拦），无法本地跑 pytest。以上代码均经静态/手工推演核对。需 worker 跑：`python3 -m pytest -q tests/unit/test_LH21_未定义名.py`。

## 残余风险
文档门禁把 `去空白`（文档错名、真实为 `去除空白`）列为已知偏差放行（文档只读不改）；`tools/内置名清单.py` 的 JSON 用真实清单（非兜底），若 `code_generator` 导入失败会退到兜底清单，仍满足验收 4/5。
