# R159-D 任务文本 —— E-3（R157-E3）：两腿布尔 repr 收敛（容器内 `真/假` → `true/false`）

> 全文与「铁律」以 `_R159_并行任务书.md` 为权威（**先 Read 整篇**）。本文件是被派单代理读的那一份，自包含。
> 工作目录：`G:\dswork\duan-light-merge\light-merge`。**不 commit / 不 push / 不做任何 git 写操作。**

## 你的任务

实施 R152-E2 裁定：**native 容器内布尔元素**的 repr 对齐 src（`[true, false]`），**标量保持中文**
（`转字符串(真)` 仍是 `真`）。分歧边界：仅容器内布尔；标量两腿已一致（中文）。
**断言扫描清单必须先报主 agent 确认，再改**（E-3 原文「爆炸半径不可控」）。

## 先读（必须读完再动手）

1. `_R159_并行任务书.md`（整篇；重点 §一1.4、§四 D 线、§五 独占矩阵、§六 铁律）
2. `src/llvm/runtime_typed.c:595-660`（`dv_to_string_depth` 前向声明 + `dv_elem_to_string`）
3. `src/llvm/runtime_typed.c:728-752`（`dv_to_string_depth` 的 case 5 病灶）
4. `docs/功能对标/语言缺陷账.md` §十五（R152-E2 裁定三条：规范 A/B/C）
5. `ROADMAP.md` R157 段「两腿 repr 分歧裁定」行

## 现状要点（起草时已核实，请亲自复核）

- 病灶：`runtime_typed.c:743`：
  ```c
  case 5: return dv_strdup(v->boolean ? "真" : "假");
  ```
- `depth` 天然区分标量/容器元素：顶层 `dv_to_string` = `dv_to_string_depth(v, 0)`（`:750-751`）；
  容器内 `dv_elem_to_string`（`:600` 附近）以 `depth + 1` 调用 ⇒ **容器元素 depth ≥ 1**。
- 爆炸半径（起草时核对）：`dv_to_string` 其余调用点（拼接 `:776-777`、比较 `:1281/:1326/:2160`、
  列表连接 `:3836/:3854`、异常消息 `:4054/:4126/:4144/:4200`）**全部 depth=0**（标量路径），不受影响；
  仅 `dv_container_to_string`（`:612`）经 `dv_elem_to_string` 走 depth≥1。
  **真正要扫的是断言**：`tests/unit/test_原生腿_*` 中断言 `[真, 假]` 容器形态的用例。
- 行尾：`runtime_typed.c` 实测 **CRLF（11591 crlf / 0 bare LF）**。

## 做法要点

1. **改前先扫爆炸半径**：
   - `grep -rn "\[真\|真, 假\|假, 真" tests/unit/test_原生腿_*`（以及 `grep -rn "真" tests/` 里
     断言字符串容器的用例）；
   - 产出**受影响断言清单**（文件:行:原文摘录）→ **报主 agent 确认后再改**。
2. **修**：`:743` 改 depth-aware：
   ```c
   case 5: return dv_strdup(v->boolean ? (depth > 0 ? "true" : "真")
                                       : (depth > 0 ? "false" : "假"));
   ```
   加注释「R152-E2 裁定：标量中文 / 容器内对齐 src」。
3. **断言同步**：清单内断言改为 `[true, false]` 形态。**禁止**在 `.light`/runtime 里加归一化
   （裁定明文：归一化只能在测试断言侧做且必须显式登记）。
4. **新增回归门** `tests/unit/test_R159_E3_容器布尔repr.py`：
   - 双腿对拍 `转字符串([真, 假])` == `[true, false]`；
   - 嵌套（`{"k": [真]}` → `{'k': [true]}` 或该腿既有格式）；
   - **标量不受影响**（`转字符串(真)` == `真`）；
   - 反跑（改回 depth 不敏感 → 容器分歧复现，转红）。
5. **JSON 独立性验证**：`序列化JSON([真, 假])` 走 `dv_json_serialize` 独立路径——
   确认输出仍为合法 JSON（`[true, false]`），记录现状（不受本改动影响或本来就该如此）。

## 必跑

L0 本机（双腿对拍 + 双 gen `--check` + 波及面 `test_原生腿_*`）→ L2 0.86 平台批。
**收口 L1 全量门由主 agent 与 A 线一起跑（你不许自行触发 0.82 全量门）。**

## 禁令

- 不许动 `dv_elem_to_string` 的字符串引号逻辑（`'x'` 是另一套口径，非本线）。
- 不许把标量也改成 `true/false`（裁定明确标量中文）。
- 不许在测试侧做「两边都接受」的宽容断言（假绿）。
- 不许动 `src/llvm/compiler.py`/`codegen_typed.py`（A 线文件）、`stdlib/**`。
- 行尾：`runtime_typed.c` 改动必须保持 CRLF（bareLF=0 自检）。

## 交付

写 `_R159_D线交付报告.md`：断言扫描清单（报主 agent 的原文）/ 修改 diff / 双腿对拍输出 /
反跑证据 / JSON 独立性记录 / 0.86 平台证据 / 新发现问题（需立号从 L-219 起，先 grep 确认未用）。
**完成后用 SendMessage 给 main 发结构化汇报（含真实命令与退出码）。**
