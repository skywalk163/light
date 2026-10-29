# T-0198 工作说明（LH-22 / LH-18b / LH-12）

## 结论
三条都在 HEAD 上复现并已修：括号外行首运算符续行现在**能跑**（不再误报「缩进不正确」）；
`\` 续行支持；运行期跨模块报错带「抛出点 → 调用点」异常链。存量 309 个 `.light` 解析结果逐字不变。

## 做了什么
1. **LH-22（取卡面期望方案 1，自动续行）**：`src/lexer.py` 在语句层 NEWLINE 处新增
   「行首二元运算符续行」分支，三个条件缺一不可：上一行末尾是完整表达式（字面量/标识符/
   闭括号/`真假空无` 白名单，块头「：」天然排除）、本行首个词是二元运算符关键字、
   本行缩进**严格深于**语句行。续行行前导缩进不进缩进栈（沿用 L-023 原理）。
2. **LH-22 方案 2 兜底**：`src/parser_stmt.py`（**卡面 paths 未列，见下「越界说明」**）
   在「缩进不正确」「保留关键字不能作为语句开头」两处文案后追加
   `（疑似续行：本行以运算符「X」开头…）`——续行前提不成立时不再把人往缩进上引。
3. **LH-18b**：`src/lexer.py` 支持 `\` + 行尾空白 + 换行续行；`\` 只在字符串外、
   且其后到行尾全空白时才算续行符（字符串转义与注释内 `\` 一字未动）。
4. **LH-22 验收④**：`src/parser_core.py` 聚合报错新增 `_decascade_order`——「缩进不正确」
   若其**上一行另有一条非回声错误**，则渲染时排到最后，保证「错误 1/N」恒指真因；
   `all_errors` 保持原始顺序（工具链口径不变）。
5. **LH-12**：`src/enhanced_errors.py` 把 L-061/L-093 的行号归因拆成可复用方法
   （`_map_frames` / `_try_frame_location` / `_resolve_mapping`，行为不变），在其上新增
   `_format_exception_chain`：≥2 跳可归因时输出 `异常链（抛出点 → 调用点）: 依赖.light:2 → 主.light:2`；
   单帧报错一字不加，跳数 >4 只保留两端。
6. `docs/T-0198_续行规则.md`：本卡自己的续行文档段落（三种合法续行、边界、报错口径、验证命令）。
7. `tests/unit/test_LH22_续行.py`：22 条用例（卡面 4 项验收 + 回归护栏）。

## 验证
- 卡面验收：`python3 -m pytest -q tests/unit/test_LH22_续行.py` → **22 passed**。
- **反跑（有牙）**：`git checkout --` 4 个 src 文件（保留用例）复跑 → **12 failed / 10 passed**；
  红的正好是三条缺陷的用例，绿的正好是回归护栏（括号内、字符串转义、注释 `\`、单行、同级缩进、
  独立缩进错误、单帧异常）。恢复修复后回到 22 passed。
- 存量边界：`tests/test_c3_parser_codegen.py`（**卡面写的 `tests/unit/test_c3_parser_codegen.py`
  不存在，真文件在 `tests/` 根**）+ `tests/test_codegen.py` + `test_lpd_006_行尾续行.py`
  + `tests/unit/test_L0*.py` + `test_R142_L074_是字母是空白.py` + `tests/test_R75/R76_syntax_gaps.py`
  → **148 passed**。
- 语料对拍：309 个 `.light`（tests/examples/demos/stdlib/lighttests/demo/edu/playground/project/templates，
  排除 archive）改前/改后 parse 结果（OK/ERR + 错误指纹）**逐字相同**，diff 为空。
- CRLF 源另测：行首续行 / `\` 续行 / 空行+续行 三种形态均通过（`\r` 只跳过不计缩进）。

## 越界说明（卡面 paths 之外，各一行理由）
- `src/parser_stmt.py`：卡面落点写「报错文案在解析失败路径（parser_core）」，但
  「缩进不正确」与「保留关键字不能作为语句开头」两处文案**实际在 parser_stmt.py:810-825**；
  不改这里就无法落实卡面「期望 2（至少换一条报错）」。改动仅为追加提示后缀，且只在命中
  二元运算符关键字时追加，其余文案一字不动。
- `docs/T-0198_续行规则.md`：卡面正文明确「语法文档如要补说明，写在 docs/ 下本卡自己的段落里」。
- `tests/unit/test_LH22_续行.py`：卡面指定路径，已在 paths 内。

## 遗留 / 风险
- **同级缩进的行首运算符形态仍报错**：`打印 "a"` + 同级 `加上 "b"` 不并入（不加缩进看不出意图），
  报「意外的标记: 换行」——比原来的「缩进不正确」准，但不如「疑似续行」直白；
  给「保留关键字不能作为语句开头」补提示覆盖不到这条路径（它走的是表达式解析）。
  要彻底覆盖需在 parser_expr 的「意外的标记」处也加判据，本卡未做（超出卡面四项验收）。
- `tests/unit` 全量在**本机跑不出结论**（如实记录，不标绿）：
  - 基线（暂存 4 个 src 改动后跑）**52 failed / 3738 passed**，跑到 73% 时 xdist
    `node down` ×2 → `INTERNALERROR KeyError: <WorkerController gw5>` 中断，`-rf` 清单未打印；
  - 修复后同参数一轮 **40 failed / 3884 passed**，跑到 ~99% 时
    `OSError: [WinError 1450] 系统资源不足` 中断，同样无清单。
  - 两轮都被原生腿（`_t6b_native_helper.py` 子进程挂死，12 分钟零 CPU 增长）与
    本机资源耗尽打断，**红数修复后不高于基线**，但**不能**据此宣称全量绿；
    机器上同时有别的 agent 在跑（另见 doubao-win 的 submit/门禁自检进程）。
  - 结论：全量门未作为本卡判据，改用「语料逐字对拍 + 解析/词法/生成子集 148 passed」
    作为存量护栏。

