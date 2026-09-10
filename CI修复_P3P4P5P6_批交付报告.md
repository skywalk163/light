# P3/P4/P5/P6 四任务批交付报告

> 分支：`task-p3p6-杂项批`（已合并 task-5b-o0native数学 的 P5 成果）
> 日期：2026-09-10

## 总验收

| 任务 | 目标 | 结果 |
|---|---|---|
| **P3** 断言工具 7 失败 | test_stdlib_phase9::测试断言工具 全绿 | ✅ **16 passed**（本地实测） |
| **P4** 时间管理 8 失败 | test_stdlib_phase3::Test时间管理 全绿 | ✅ phase3 全文件 **37 passed** |
| **P5** O0 native 数学 10 失败 | 3 文件全绿 + 0.88 验证 | ✅ 本地 36/36；0.88 35 passed（1 例 `-n8` 并行偶发，单跑恒绿，失败例逐轮漂移证非改动引入）——详见 `CI修复_任务5_O0native数学_交付报告.md` |
| **P6** 杂项 5 项 | (a)(b)(c)(d)(e) 全绿 | ✅ 全目标项 passed（详见下） |

P3/P4 终态复核：`测试断言工具 + test_stdlib_phase3` → **53 passed**（commit 后复核）。

## P3 — 断言工具（零改动转绿）

`stdlib/断言工具.light` 导出行已含全部 7 组名（断言失败异常/字符串断言/对象断言/
异常断言/类型断言/自定义断言/链式断言所需 helper 均在 361-367 行导出），实测
`测试断言工具` 16 passed——**先前并行工作已修复**，本批零改动、实测复核确认。

## P4 — 时间管理（零改动转绿）

`tests/test_stdlib_phase3.py` 全文件 37 passed（含 Test时间管理 8 例）——睡眠的
time 导入、倒计时/定时器的线程回调等先前工作已修复，本批零改动、实测复核确认。

## P6 — 杂项（本批实际改动，commit `1952b820`）

| 项 | 根因 | 修法 | 结果 |
|---|---|---|---|
| (a) capture_encoding_guard + link_libs_guard | 3 个测试文件带 UTF-8 BOM（U+FEFF），ast 解析不了 → 护栏盲区 | 去 BOM：test_stdlib_phase13 / phase4 / unit/test_原生腿_R13C_对拍扩展 | **9 passed** |
| (b) e2e test_L073 | 示例设计即复现未捕获异常（文件头注释写明），rc=1 是正确行为；e2e 把 rc==0 当判据 | e2e 新增 `EXPECTED_FAILURE_EXAMPLES` + `test_duan_run_expected_failure`（验 rc!=0 且 stderr 带光明译文「缺少方法/属性」），常规链路排除 | **1 passed** |
| (c) test_division | `除`=Python `/` 真除（`7 除 2`→3.5 实测），`100/4` 应产 25.0；原期望 '25' 与真除语义相悖 | 测试期望 '25'→'25.0' 并注明口径（整数商用 整除//） | passed |
| (d) R13C test_URL编码解码 | ⚠️ 按更正口径只修对拍；该用例实测已绿 | 零改动，未重复链表查找改动 | passed |
| (e) R11A test_数据验证_对拍Python | 数据验证.light 用 `是整数/是浮点` 判型，native 派发缺 → NotImplementedError | codegen_typed 判型家族补 `是整数/is_int/is_integer`、`是浮点/是浮点数/is_float`（复用 P5 的 `_gen_type_predicate`） | **1 passed** |

## 已知噪音（非本批引入，stash 对照确认）

- `test_断言工具_对拍Python`：断言工具.light 含嵌入 C 块（EmbedBlock），native
  后端本不支持，基线上同样失败——移交后续 native 语句面扩容，不在 P6 (e) 范围。
- P5 的 0.88 `-n 8` 并行偶发 1 例（失败例漂移、单跑恒绿）——移交路 6 观察。

## 文件清单

- `src/llvm/codegen_typed.py`：判型家族补 是整数/是浮点（P6(e)）
- `tests/e2e/test_e2e_chain.py`：预期失败示例机制（P6(b)）
- `tests/unit/test_light_examples_run.py`：test_division 期望修正（P6(c)）
- `tests/test_stdlib_phase13.py` / `tests/test_stdlib_phase4.py` /
  `tests/unit/test_原生腿_R13C_对拍扩展.py`：去 BOM（P6(a)）
