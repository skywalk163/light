# CI修复_网络请求native_交付报告（task-net-native）

- **分支**：`task-net-native`（自 main@424e99a6 切出）
- **修复提交**：`525124ab` fix(stdlib): 网络请求.light 函数级导入提为模块级，修复 native 整模块编译失败
- **验证机**：192.168.0.88（FreeBSD clang 19.1.7，真门禁）
- **交付日期**：2026-09-11

---

## 一、任务与验收标准

补全 `stdlib/网络请求.light`（及依赖的 native builtin/runtime 函数）在 O0 native（LLVM）后端的支持，使网络请求相关测试在 native 下可用。

1. native 对拍失败数显著下降（目标归零，至少 `Test网络请求` 整组全绿）；
2. 0.88 全量 `pytest tests/ -n 8` 无新回归；
3. 确属 native 能力边界的标 xfail/skip 并记缺陷账（L-07x），严禁假过。

## 二、修复内容（提交 525124ab）

**根因**：`响应.JSON` 方法体内「从 JSON核心 导入 解析」是全 stdlib 唯一的函数级导入；native 后端 `_gen_statement` 对方法内 `ImportStatement` 不绑定名字（`codegen_typed.py` 直接 pass），调用 `解析` 时按未定义段落拒绝。codegen 按整模块生成，故任何 `import 网络请求` 的 native 编译都会在此挂掉——R11C `Test网络请求` 5 例、R13B `Test网络请求扩展` 3 例对拍全红的根因；「字典 NameError」为同一次编译失败的连带症状。

**修复**：把导入提到模块顶层（与 `JSON.light`/`uuid工具.light` 等一致的既有跨模块导入路径），方法体内仅保留调用。`.py` 后端口径不变。

## 三、本轮（验证轮）工作

### 3.1 0.88 测试树修复

排查发现 `/home/workbuddy/light_verify` 此前按裁剪清单同步，缺失根目录文件（`llvm_backend.py`、`c_backend.py`、`CHANGELOG.md`、`antlrparser/`、`lsp/` 等），导致 e2e 文件存在性检查 ×4、`test_c_backend.py`/`test_lsp.py` collection ERROR 等 ~19 例**环境性假失败**。本轮按 `git ls-files` 全量同步（39222 个跟踪文件，tar 11.4MB）后这些失败全部消失。

同步核验：src/tests/stdlib 共 663 个 `.py`/`.light` 文件 md5 与 worktree HEAD 逐一一致（中文文件名按八进制转义解码后比对）。

### 3.2 定向门禁（88 实测）

```
pytest "tests/test_stdlib_phase3.py::Test网络请求"
       "tests/unit/test_原生腿_R11C_数据高级.py::Test网络请求"
       "tests/unit/原生腿_R13B_能力扩展.py::Test网络请求扩展"
→ 15 passed, 1 skipped（skip 为需真实外网的 HTTPS 用例，与本改动无关）
```

本地（worktree，py3.10 + 真 clang O0）：R11C/R13B/R13C 全量 73 passed / 2 skipped / 2 xfailed（基线 8 failed → 0）。

### 3.3 全量门禁 + A/B 对照

在 88 上做严格 A/B：仅切换 `stdlib/网络请求.light` 为 main 版（基线 B，md5 `d01d5ef6…`）与修复版（md5 `36adea2f…`），其余完全一致，各跑全量 `tests/ -n 8`：

| 轮次 | 网络请求.light | failed | passed | 失败构成 |
|---|---|---|---|---|
| 基线 B | main 版 | 44 | 7921 | 恒定 35 + 网络 native 8 + `distributed_eval` 偶发 1 |
| 修复 run1 | 修复版 | 36 | 7929 | 恒定 35 + `行政区划` 偶发 1 |
| 修复 final | 修复版 | 37 | 7928 | 恒定 35 + `distributed_eval`、`http_client` 偶发 2 |

- **三轮恒定失败集 35 例逐项一致**（`final ∩ run1 ∩ baseB`）；
- 修复净消除**恰为 8 例**网络请求 native 对拍（R11C 5 + R13B 3），与基线 diff 严格吻合；
- 轮换偶发 3 例，均与本改动无因果：
  - `Test行政区划扩展::test_O0_行政区划代码_对拍与扩展`：改动前 l076 基线（12:52）即失败；定向复跑出现 0.12s 秒挂 1 次、5.5s 正常通过 4 次（3 连跑全过）→ 记缺陷账 **L-079**；
  - `test_distributed_eval_light.py::test_重派与心跳_杀节点后重派且无静默丢条`：基线 B（main）中失败、修复版定向单跑通过，分布式时序敏感；
  - `test_http_client.py::test_concurrent_requests`（assert 9 == 10）：纯 Python 并发时序偶发。

### 3.4 恒定 35 例构成（全部为改动前既有）

| 组 | 数量 | 归属 |
|---|---|---|
| `测试断言工具` | 16 | L-076 遮蔽债 |
| `Test时间管理` | 9 | L-076 遮蔽债（`from 时间管理 import 倒计时` 解析到 `.light` 残缺版，日志实证） |
| `Test网络请求`（stdlib 层） | 5 | L-076 遮蔽债（定向单跑 7/7 全绿；全量下被 `.light` 版遮蔽） |
| `R13C::test_URL编码解码` | 1 | L-076 同族（定向单跑 88 实证通过，仅全量下失败） |
| `test_native_leg_capability` | 3 | 既有能力清单漂移 |
| `test_cross_platform` | 1 | 既有 |

其中 L-076 相关 ~31 例：双后端同模块名 + xdist worker 污染（`sys.modules` 遮蔽），属既有架构债，已有专项根治规划（Prompt ②），非本任务单模块可解；且四组定向单跑在 88 上全部复证通过。

## 四、验收对照

| # | 标准 | 结果 |
|---|---|---|
| 1 | native 对拍失败显著下降（目标归零，Test网络请求 整组全绿） | ✅ 88 实测 8 → 0；R11C `Test网络请求` 5/5、R13B `Test网络请求扩展` 3/3、stdlib `Test网络请求` 定向 7/7 全绿 |
| 2 | 0.88 全量 `-n 8` 无新回归 | ✅ A/B 恒定失败集 35 例逐项一致，修复净消除 8 例、零新增；差异仅为 3 例与改动无因果的轮换偶发 |
| 3 | 严禁假过 | ✅ 未改任何测试、未加 xfail/skip；修复为 stdlib 源码级真修复；0.88 真 clang（19.1.7）native 验证 |

## 五、缺陷账

- **新增 L-079**：`R13B 行政区划 O0 对拍` 在 0.88 全量门禁下偶发失败（含秒挂形态），定向复跑多数通过；根因待查（疑似编译缓存/并发资源竞争）。编号跳过 L-077/L-078（已被路5语法债在 `test_L075_L077.py` 语境使用）。
- **重申 L-076**（待修复）：全量并行下 stdlib `.light` 残缺版遮蔽 `.py` 完备版，波及 `断言工具`/`时间管理`/`网络请求` stdlib 层与 `R13C test_URL编码解码`，约 31 例；按既有规划由专项根治，本任务不越权处理。

## 六、88 现场终态

- `/home/workbuddy/light_verify` = `task-net-native` HEAD（`525124ab`）全量同步；
- 最终日志：`/home/workbuddy/pytest_fullgate_88_final.log`（37 failed / 7928 passed / 97 skipped / 13 xfailed）；
- A/B 日志留存：`pytest_fullgate_88_baseB.log`（main 版基线）、`pytest_fullgate_88.log`（修复 run1）。

## 七、交付物清单

| 文件 | 说明 | 提交 |
|---|---|---|
| `stdlib/网络请求.light` | 函数级导入提为模块级（native 编译根因修复） | `525124ab` |
| `CI修复_网络请求native_交付报告.md` | 本报告 | 本轮 |
| `docs/功能对标/语言缺陷账.md` | 新增 L-079 | 本轮 |
