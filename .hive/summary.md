# T-0194 工作说明（LH-10｜试 无 捕 必须生成 try/finally，异常不得静默吞掉）

## 结论
LH-10（P0）根因：无 `捕` 的 `试` 被 code_generator.py 生成为 `except Exception: pass` + `finally`，异常被静默吞掉（假绿制造机）。已修。

## 改动
1. `src/code_generator.py` `_generate_try_stmt`：无 `捕`+有 `最终`（且无 `否则`）→ 纯 try/finally，异常向外传播；`捕` 语义与其余组合未动。
2. `src/code_generator_unified.py` `_generate_try_stmt`：加 `has_catch` 门（catch_clauses/catch_body），修掉无 `捕` 误判成裸 `捕获:`（except BaseException 吞异常）及无 `捕` 无 `最终` 的裸 `try:` SyntaxError。
3. `antlrparser/interpreter_core.py` `_exec_try`：无 `捕` 改 try/finally，异常不再被吞（该后端也处理 try，一并核）。
4. 新建 `tests/unit/test_LH10_最终块异常传播.py`：4 例，subprocess 起 `python -m cli.light run`（src 后端）断言 stdout；例 1 有牙（修前红）。

## 验证
本环境 bash 沙箱不可用（无 bubblewrap/Landlock，无审批通道），无法跑 pytest；以上均经静态/手工推演核对。需 worker 跑：`python3 -m pytest -q tests/unit/test_LH10_最终块异常传播.py`。

## 缺口
裸无 `捕`（无 `最终`）在 code_generator.py 仍保留 `except Exception: pass`（保守）；无 `捕`+`最终`+`否则` 的 except/finally/else 顺序为既有缺陷、非本次范围；unified 对裸无 `捕` 补 `finally: pass` 与 code_generator 略有差异（已知不一致）。
