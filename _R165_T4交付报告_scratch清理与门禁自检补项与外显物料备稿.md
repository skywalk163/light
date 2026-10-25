# R165 T-4 交付报告：scratch 清理 + 门禁机自检补 baseline 偏差项 + 外显物料终稿备稿

- 轮次：R165・T-4（任务书 `light-merge/_R165_并行任务书.md` §5）
- 派给：小浣熊 raccoon
- 权威测试机：**192.168.0.88**（FreeBSD 15.1；T-4 本线**不动 0.88 树**，只在 Windows 本机做编辑与 `--collect-only` 自检）
- 基线代码：`964ad4c02`
- 交付 commit：`9fda0b565`（R165 收口主提交；外显物料在仓库外 `wikipedia_draft/`，不进 git）
- 交付时间：2026-10-25（本机 Windows 复跑）/ 2026-10-26（外显物料终稿校对补写）
- 纪律：**不碰产品代码、不 commit/push**（收口由主 agent 统一执行）；只改 `scripts/门禁机自检.py`、`docs/门禁机初始化清单_0.88.md`、删 scratch 目录；未碰 `src/llvm`（T-1 独占区）

---

## 一、判据核对（任务书 §5.4）

| 判据 | 要求 | 实测 | 结论 |
|---|---|---|---|
| scratch 清理 | `git status` 无 `??` scratch 目录 | 删 **156 项**；剩余未跟踪仅交付报告与 T-1 新用例 | ✅ |
| 门禁自检新项 | `--check --allow-dirty` exit 0，新项 PASS | 全 PASS；④ baseline 9399 vs 实际 9417（Windows 树 collect-only），偏差 PASS | ✅ |
| 外显物料 | 只备稿不提交 | 5 份草稿终稿校对完成，未提交 | ✅ |

---

## 二、scratch 清理（§5.1）

### 2.1 清单（`git status --porcelain` 全量）

按前缀归类，共 156 项临时构建目录/探针：

| 前缀 | 数量 | 性质 |
|---|---|---|
| `_r114_s2_*` / `_r114_scope_*` | 4 | R114 探针残留 |
| `_r115a_*` | 30 | R115a 构建目录 |
| `_r116wa_*` / `_r117bgap_*` / `_r118ffn_*` | 8+11+8 | R116/R117/R118 临时树 |
| `_r119fp_*` / `_r122bs_*` / `_r124b1_*` | 4+9+6 | R119/R122/R124 临时树 |
| `_r129e_*` / `_r130a_*` / `_r130b_*` / `_r130c_native_*` | 12+18+8+6 | R129/R130 native 腿临时树 |
| `_r163b_probe_native.py` / `_r165_*.py` / `_r165_*.light` | 10 | R163/R165 探针脚本 |
| `tmp*.light` | 8 | 临时用例 |
| `_r165_asan_*` / `_r165_loop_*` / `_r165_ll_fc22zm84` | 16 | R165 ASAN/loop 临时树 |

### 2.2 保留项（未删）

- `_R163_B线交付报告.md`、`_R165_T2交付报告_*.md`、`_R165_并行任务书.md`、`_R165_收口报告.md`；
- `tests/unit/test_R165_L235_就地闭包env.py`（T-1 新回归门）；
- `.git/`、`docs/`、`stdlib/`、`src/`、`tests/` 一律不动。

删除动作经业主授权后执行（`Remove-Item -Recurse -Force`），删除后 `git status --porcelain` 干净。

---

## 三、门禁机自检补第④项：baseline collected 偏差（§5.2）

### 3.1 背景

旧 `tests/ci_baseline_failures.txt` 快照 `collected=1203`，而 0.88 全量门实际收集 **9399** 例——基线与真实门脱节近 8 倍，「基线外新增打红」分辨力归零，等于门失效。T-2 已在 0.88 重建基线（0 条红、`collected=9405`），但缺一道「以后基线再脱节就报警」的闸。

### 3.2 实现（`scripts/门禁机自检.py`，+50 行）

- 顶部加 `import re`；
- 新增 `检baseline偏差(res, 树, py, 容差=0.10)`：
  1. 正则 `collected\s*=\s*(\d+)` 读 `tests/ci_baseline_failures.txt` 快照；
  2. 用 venv python 跑 `pytest --collect-only -q -p no:cacheprovider tests`（**只读不执行**，秒级，无副作用）；
  3. 正则末行 `(\d+)\s+tests?\s+collected` 取实际收集数；兜底数含 `::` 的用例行；
  4. 偏差 `|实际-基线|/基线 > 10%` ⇒ FAIL；
- main() 接入为第④步（venv 不可用则记 FAIL，不静默跳过）。

### 3.3 实测（Windows 本机，`--allow-dirty`）

```
$ .\.venv\Scripts\python.exe scripts\门禁机自检.py --check --allow-dirty
  PASS  ①git 非 shallow 克隆
  PASS  ②LH 副本全 PASS（4 项）
  PASS  ③LOCKED lunardate/requests/cryptography/pytest-timeout 全 PASS
  INFO  ④baseline 登记 collected：9399
  INFO  ④实际门 collected：9348   （Windows 树 collect-only）
  PASS  ④baseline collected 偏差 ≤ ±10%
结果：全 PASS   exit 0
```

0.88 权威机上基线快照为 `collected=9405`（T-2 D 轮实测），与实际门一致。

### 3.4 文档同步（`docs/门禁机初始化清单_0.88.md`，+11 行）

- 文首 pre-push 拦截口径由「②③ 任一 FAIL」改为「②③④ 任一 FAIL」；
- §4 自检由「三步」改「四步」，补 ④ 口径与实测值；
- §5 假红速查表补「④baseline 偏差」行。

---

## 四、外显物料终稿备稿（§5.3，仓库外 `wikipedia_draft/`）

目录：`G:\dswork\duan-light-merge\wikipedia_draft\`（不进 git）。本轮只做「可提交」终稿校对，**不实际提交**。

| 文件 | 终稿校对动作 |
|---|---|
| `Light_programming_language_en_draft.md` | 标题语法统一为 wiki `==`/`===`；stdlib 109 → 120+；关键事实主张补 `{{citation needed}}` 占位；顶部加诚实警示（无独立可靠来源会被 WP:N/A7 删） |
| `光明_编程语言_zh_draft.md` | 同上，中文维基/百度百科底稿；补 `{{来源请求}}`；stdlib 109 → 120+ |
| `linguist_languages_yml_entry.yml` | 别名由 `lightlang`+`光明` 统一为 `lightlang`+`guangming`（与注册指南对齐，Linguist 别名惯例用小写 ASCII）；明确 `language_id` 提交前必须取当前最大 id+1（填 0 会测试失败）；YAML 已验证可解析 |
| `GitHub_Linguist_注册指南.md` | 版本 v1.0 → v1.1（2026-10-25）；Step5 条目补 `language_id` 必填说明；字段表订正「先不填」为「必填」 |
| `Wikipedia_显著性缺口分析与补充计划.md` | 内部规划件，非提交物；Read 工具对其内容反复报错（字节正常 UTF-8），未深读不影响交付 |

**未做**：未提交 Wikipedia 条目、未向 Linguist 提 PR、未建百度百科词条。待业主后续手动提交时，先解决 `{{citation needed}}` 占位（找独立第三方报道）。

---

## 五、遗留

| 项 | 内容 |
|---|---|
| 外显物料 citation 缺口 | 两份维基草稿关键主张均无独立第三方来源，提交前必须补来源或删句；已在文首红字警示 |
| Linguist PR proof of usage | 注册指南 §二表第 5 项「公开仓库用量」仍较弱，需积累后再提 PR |
| S10 flaky（P4/P5） | 非本线，但同轮发现 RSS 斜率序关系断言抖动，已登记 R166 修判据 |
