# 交付报告_B9LLVM（第九轮 S2 · 清掉「CLI 路径表」llvm 行的告警）

- 分支：`task-B9LLVM`（基于 `main` 的 `38d5e270`）
- 提交：`ebb62d15` fix(round9-S2) + 本报告的 docs 提交
- 实测平台：**Windows 10 / CPython（本机）**。CI 的唯一 runner 是 **FreeBSD**，本报告
  凡未标注 FreeBSD 的实测结论都只代表 Windows 本机；跨平台判断见 §6。
- 结论一句话：这条告警是 **(b) 只缺登记（写得过期）**。源码侧 B9 S1 已经把死腿摘干净了，
  是清单没跟着改。已按 (b) 处置：补正登记 + 加两条真仓库断言，判据一个字没放宽。

---

## 1. 告警的确切来源

### 1.1 原文（真跑一次，未改动前）

```
> python tools/ci/native_product.py --root .
[原生产品门禁] 模块表：可编译 1 / 79 = 1.27%（未实测 0）
[原生产品门禁] CLI 路径表：共 10 条，其中坏 1 条；源码 --backend choices = antlr/llvm-typed/native/src
[原生产品门禁] 告警（不判红）：CLI路径表登记了源码里已无的后端取值：llvm（摘除死腿是许可处置，记得同步把表里那条改成 未实现 或删除）
[原生产品门禁] 平台矩阵：16 格，已实测通过 10 / 桩 2 / 未实测 4
[原生产品门禁] 通过：三张表合规、模块表与 stdlib 双向咬合、后端取值全登记、可编译比例未降、未实测与坏路径未增。
（rc=0）
```

### 1.2 产出这张表的脚本与判据位置

| 角色 | 位置（改动前行号） |
|---|---|
| 产出「CLI 路径表」那两三行输出的脚本 | `tools/ci/native_product.py:400-407` |
| 告警的 print 原文 | `tools/ci/native_product.py:405-407` |
| 告警的判据 | `tools/ci/native_product.py:302` → `已摘除 = sorted(表取值 - set(真取值))` |
| 「表取值」怎么来的 | `tools/ci/native_product.py:141-155`（`规范化`）从清单 `CLI路径状态表` 每条的 **`命令` 串**里用 `_RE_后端取值`（`:81`，`--backend\s+([\w\-/ ]+)`）抽出来，**与 `状态` 字段无关** |
| 「真取值」怎么来的 | `tools/ci/native_product.py:210-222`（`源码后端取值`）正则扫 `cli/light.py` 所有 `--backend ... choices=[...]` |
| 表数据（被告警的那一行，改动前） | `任务书/原生腿产品清单.json:401-407`，`"命令": "run/compile --backend llvm"`、`"状态": "坏"` |

### 1.3 为什么只 warn 不红

这是 G9 建门禁时的**明文裁决**，不是漏判：

- 口径写在 `tools/ci/native_product.py` docstring 第 2 条（改动前 `:38-43`）：正向（源码有、
  表里无）判红；反向（表里有、源码已无）只告警，因为「把死腿从 choices 里摘掉」是本轮
  许可处置（总纲 S1「修或删，二选一」），摘掉后 `坏` 计数下降是真进步，不该被拦。
- 这条裁决有测试钉着：`tests/unit/test_ci_gates_round9.py:369`
  `test_源码摘除后端取值只告警不判红`（断言 rc=0）。
- 代码路径上，`已摘除` 只进 `统计["backend_已摘除"]`（`:330`）供 print 用，**不进 `问题` 列表**，
  也不进基线比较，所以 rc 恒不受它影响。

---

## 2. 性质判定：(b) 只缺登记（写得过期）

### 2.1 排除 (a) 真缺功能

`--backend llvm` 是 string 腿，引用不存在的 `src/llvm/runtime.c`，B9 S1 2.1 已按「修或删」
选了删。**源码侧真的删干净了**，实测（Windows 本机）：

```
> python -m cli.light run --backend llvm nonexist.light; echo "rc=$LastExitCode"
usage: light run [-h] [--backend {antlr,src,native,llvm-typed}]
                 [--optimize {O0,O1,O2,O3,Os,Oz}] [--watch]
                 file
light run: error: argument --backend: invalid choice: 'llvm' (choose from 'antlr', 'src', 'native', 'llvm-typed')
rc=2
```

- `cli/light.py:1415`（run）与 `:1459`（compile）的 `choices` 都已无 `llvm`。
- 既有测试钉住了这条：`tests/test_native_cli.py:245` `test_死腿llvm被argparse拒绝`
  断言 `rc=2` 且 stderr 含 `invalid choice`。
- 替代路径真实存在且有真产物测试：`run/compile --backend native | llvm-typed` 走
  `compile_light_typed`（`cli/light.py:494-503`），`tests/test_native_cli.py:225-269`
  真编真跑（`skip_without_clang`）。
- 所以**没有功能缺口**：不存在「用户想干但现在干不了」的事。原 CLI 也从来没有
  「输出 LLVM IR」这个能力（`cli/light.py` 全无 `--emit-ir`，也没有 `build` 子命令）。

### 2.2 排除 (c) 判据误判

判据 `表取值 - 真取值` 问的是「清单是否登记了源码已不存在的后端取值」。事实是：清单里
确实有 `llvm`，源码里确实没有。**判据的回答是对的**，问题在被判对象（清单）过期：

- `坏` 这个状态词的语义是「路径存在但不可用」。这条路径现在连合法取值都不是，
  标 `坏` 是错的描述。
- 后果不只是刷一行字：它把 `cli_broken` 钉在 1，让「坏路径数只降不升」这条棘轮
  永远差一格，B9 S1 真做出来的进步（摘掉死腿）在指标上看不见。

### 2.3 顺带发现的一处**告警文案缺陷**（属 (c) 的边角，已修文案、未动判据）

原告警建议「把表里那条改成 未实现 或删除」。**「改成 未实现」根本消不掉这条告警**：
`后端取值` 是从 `命令` 串里抽的（`:145-146`），与 `状态` 无关，只要 `命令` 里还写着
`--backend llvm`，`已摘除` 就仍非空。这是一条会把人带进死循环的错指引，已改成实际
可行的处置。判据代码（`:308` 那一行集合差）**一个字符都没动**，warn 不判红的语义也没动。

---

## 3. 处置

| 文件 | 改了什么 | 为什么 |
|---|---|---|
| `任务书/原生腿产品清单.json` | 把 `run/compile --backend llvm` 那条从 `CLI路径状态表` 移出，整条挪进**新键 `已摘除CLI路径`**（`:423-431`），补上摘除轮次、rc=2 实测证据、以及「为什么不再算一条 CLI 路径」的理由；`说明` 数组补一条 S2 记账（`:469`） | 归档而不是删：历史账（曾有一条死腿、B9 摘掉了）必须留痕；留在活表里则是错误描述且让 `cli_broken` 虚高 |
| `tools/ci/native_product.py` | ① 告警文案改成可行处置（`:411-415`）；② docstring 第 2 条补「摘除后的收尾口径」（归档区、只改状态无效、归档不是豁免名单） | 判据未改、值域未改、warn 语义未改，只让指引与实现一致 |
| `tests/unit/test_ci_gates_round9.py` | `Test真清单在册` 加两条真仓库断言：`test_CLI路径表与源码后端取值双向咬合`（`:612`）、`test_已摘除归档不许藏活着的后端`（`:630`） | (b) 类处置必须配防腐烂断言，否则下一轮照样烂 |
| `docs/USER_MANUAL.md:531` | 表格里 `light compile file.light --backend llvm` → LLVM IR 这一行，改成 `--backend native` → 原生可执行文件 | 同一处过期登记的用户可见版本：照这行敲命令必然 `invalid choice`。这正是 B9 立项要治的「用户照文档敲一条命令必然失败」 |

**没有做的事**（免得被当成消警）：没有放宽任何判据、没有加豁免/白名单、没有改
`tools/ci/*_baseline.json`、没有把 warn 改成 red（那条 warn 是 G9 的明文裁决且有测试钉着）。

### 3.1 两条新断言各自钉的形状

1. `test_CLI路径表与源码后端取值双向咬合`：`统计["backend_已摘除"] == []`，且
   `表取值 集合 == cli/light.py choices 集合`。把门禁只肯 warn 的那件事，在**真仓库**上
   变成红；等号两边一起断，避免两个集合各自漂而门禁只喊一边。
2. `test_已摘除归档不许藏活着的后端`：归档区里抽出的后端取值 ∩ choices == 空，且
   `llvm` 必须在归档里。前半句堵「把一条活着的坏路径挪进归档来消 `坏` 计数」，
   后半句堵「把历史账悄悄删掉」。

---

## 4. 反跑证据（三条，每条都先把被测对象改坏再确认真变红）

变异探针脚本落在系统临时目录（`%TEMP%\_taskB9LLVM_变异探针.py`），跑完已删除；
每次探针后用 `git checkout -- 任务书/原生腿产品清单.json` 复原。

### 探针 A：把 llvm 那行退回 `CLI路径状态表`（即复原 S2 之前的腐烂状态）

门禁照旧只告警、rc=0（**证明「靠门禁跑一遍」抓不住这类腐烂**，也证明我没有偷偷把 warn 改成 red）：

```
[原生产品门禁] CLI 路径表：共 10 条，其中坏 1 条；源码 --backend choices = antlr/llvm-typed/native/src
[原生产品门禁] 告警（不判红）：CLI路径表登记了源码里已无的后端取值：llvm（摘除死腿是许可处置；把表里那条整条挪进清单的 `已摘除CLI路径` 归档区即可清掉本告警 —— 只改 `状态` 消不掉：`后端取值` 是从 `命令` 串里抽的，与状态词无关）
[原生产品门禁] 通过：...
gate_rc=0
```

新断言变红：

```
FAILED tests/unit/test_ci_gates_round9.py::Test真清单在册::test_CLI路径表与源码后端取值双向咬合
E   AssertionError: Lists differ: ['llvm'] != []
1 failed, 5 passed, 28 deselected
```

### 探针 B：把**仍在** choices 里的 `native` 塞进归档区（白名单式消警的手法）

```
[原生产品门禁] CLI 路径表：共 8 条，其中坏 0 条；源码 --backend choices = antlr/llvm-typed/native/src
[原生产品门禁] 通过：...
gate_rc=0
FAILED tests/unit/test_ci_gates_round9.py::Test真清单在册::test_已摘除归档不许藏活着的后端
E   AssertionError: Items in the first set but not the second:
E   'native'
1 failed, 5 passed, 28 deselected
```

**这条尤其值得记账**：门禁**没有**红。原因是门禁的正向检查是**按取值**记账的
（`native` 在另一条 `compile --backend native / llvm-typed` 里还有登记），所以「把某一条
路径藏进归档」逃得过门禁 —— 只被新断言抓住。也就是说归档这个新入口不是白送的口子，
它被单测堵住了。

### 探针 C：把 `llvm` 从归档区抹掉（历史账凭空消失）

```
FAILED tests/unit/test_ci_gates_round9.py::Test真清单在册::test_已摘除归档不许藏活着的后端
E   AssertionError: 'llvm' not found in set()
1 failed, 5 passed, 28 deselected
```

三条探针复原后 `git status --short` 干净。

---

## 5. 实测输出（改完之后）

### 5.1 原生产品门禁（告警已消失，rc=0）

```
> python tools/ci/native_product.py --root .
[原生产品门禁] 模块表：可编译 1 / 79 = 1.27%（未实测 0）
[原生产品门禁] CLI 路径表：共 9 条，其中坏 0 条；源码 --backend choices = antlr/llvm-typed/native/src
[原生产品门禁] 平台矩阵：16 格，已实测通过 10 / 桩 2 / 未实测 4
[原生产品门禁] CLI 坏路径数 下降 1 → 0（在合并点刷新基线）。
[原生产品门禁] 通过：三张表合规、模块表与 stdlib 双向咬合、后端取值全登记、可编译比例未降、未实测与坏路径未增。
rc=0
```

### 5.2 七道门禁全绿（逐条串跑，**没有与 pytest 并发**）

```
rc_assert_quality=0      [假测试门禁] 命中 469 条违规 → 无新增违规（存量冻结 469 未变）
rc_native_product=0      见 5.1
rc_bootstrap_rate=0      自举率 29/79=36.71% 持平；关键路径自举率 18/18=100% 持平
rc_floor_bootstrap=0     地板 0/80 持平；名单与 builtins.py 双向咬合
rc_dist_criteria=0       9 条能力 done 0 / partial 0 / none 9，持平
rc_python_direct_calls=0 248 行 ≤ 基线 248，无文件上升
rc_spec_coverage=0       对标清单 20 条 done 12 / partial 7 / none 1，持平
```

### 5.3 门禁单测（含两条新断言）

```
> python -m pytest tests/unit/test_ci_gates_round9.py -q
..................................
34 passed in 4.59s
```

（合并前是 32 条，S2 新增 2 条。）

### 5.4 全量（`pytest tests/ -x -q`，Windows 本机）

按要求先跑了带 `-x` 的那条，它在**一条与本改动无关的存量红**上停住：

```
> python -m pytest tests/ -x -q
1 failed, 142 passed, 24 skipped, 622 warnings in 321.55s (0:05:21)
FAILED tests/e2e/test_e2e_chain.py::test_duan_run[L4_python/all_in_one_demo.light]
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!
```

**这条红的根因（Windows 本机专属的假红，不是我造成的）**：
`tests/e2e/test_e2e_chain.py:137-141` 的 `_run_cli` 用 `capture_output=True, text=True`
**不带 `encoding=`**，父进程按本机 locale（cp936/GBK）解码；而同一处 `E2E_SUBPROC_ENV`
（`:28-32`）又给子进程强设了 `PYTHONUTF8=1 / PYTHONIOENCODING=utf-8`。**子进程按 UTF-8 写、
父进程按 GBK 读**，于是 `subprocess` 的 reader 线程抛 `UnicodeDecodeError`，
`out/err` 变成 `None`、`rc` 变 1，断言 `rc == 0` 失败：

```
UnicodeDecodeError: 'gbk' codec can't decode byte 0xa1 in position 5: illegal multibyte sequence
AssertionError: duan run 失败 (L4_python/all_in_one_demo.light):
  None
assert 1 == 0
```

FreeBSD 的 locale 编码是 UTF-8，两侧一致，这条不会触发 —— 与「PYTHONUTF8 自己也造假红」
是同一个坑的另一面。**本轮不动它**（不在本任务口径内，且属全仓 e2e 夹具，改它要单独立项）；
建议的一行修法记在 §7。

排除这一条后跑完整全量（不带 `-x`，仍未与门禁并发）：

```
> python -m pytest tests/ -q --deselect "tests/e2e/test_e2e_chain.py::test_duan_run[L4_python/all_in_one_demo.light]"
14 failed, 4610 passed, 86 skipped, 1 deselected, 1 xfailed, 6676 warnings, 237 subtests passed in 1523.14s (0:25:23)
```

14 条红逐条归因（**全部落在我一行都没碰的文件上**，见下面的 diff 范围）：

| 条数 | 用例 | 归因 |
|---|---|---|
| 3 | `tests/e2e/test_e2e_chain.py` 的 `L4_python/demo3_matplotlib_plot.light`（run + 产物）与 `L4_python/all_in_one_demo.light`（产物） | 同 §5.4 的 GBK/UTF-8 解码错配 + L4 示例依赖本机三方库 |
| 8 | `tests/test_datetime.py::test_{公历转农历,农历转公历,日期时间转农历,日期转农历,春节日期,中秋日期,端午日期,中国节假日}` | `RuntimeError: 农历转换需要 lunar…` —— 本机缺 `lunardate` 类库。按「本机装库转绿不算修好」的裁决，不装库、不改判据 |
| 2 | `tests/test_http_client.py::test_async_client{,_context_manager}` | `ModuleNotFoundError` —— 本机缺异步 HTTP 三方库 |
| 1 | `tests/test_stdlib_phase3.py::Test进程::test_进程类` | `RuntimeError: 进…` 进程类相关的本机环境依赖 |

本改动的全部范围（`git diff 38d5e270 --stat`），与上表任何文件零交集：

```
 docs/USER_MANUAL.md                |  2 +-
 tests/unit/test_ci_gates_round9.py | 39 ++++++++++++++++++++++++++++++++++++++
 tools/ci/native_product.py         | 10 +++++++++-
 任务书/原生腿产品清单.json         | 21 ++++++++++++--------
 4 files changed, 62 insertions(+), 10 deletions(-)
```

---

## 6. 平台归属与「关键路径自举率」核实

- 本报告所有实测都在 **Windows 10 本机**。涉及的改动是 JSON 记账 / 门禁 print 文案 /
  两条纯读文件的断言，**不含任何平台相关代码**：新断言只读 `任务书/*.json` 与
  `cli/light.py`，键一律走清单原文，**不生成任何带 `os.sep` 或行号的键**（两条血泪规程）。
  因此 FreeBSD 上的行为与 Windows 应当一致；但按规程声明：**FreeBSD 未实测**。
- 任务书线索里的「关键路径自举率是否与路径表有关」——**核实结论：无关**。
  `tools/ci/bootstrap_rate.py:322-333` 的 `读关键路径清单/scan_critical_path` 读的是
  `tools/ci/critical_path_modules.json`（**stdlib 模块名**清单，18 条，本次输出 18/18=100%），
  与 `原生腿产品清单.json` 的 `CLI路径表`（**CLI 命令路径**）既不共享数据文件也不共享分母。
  两者唯一交集是 `native_product.py` 借 `bootstrap_rate` 的 `iter_light_files` 枚举 stdlib
  （`:196-207`），那是模块表的分母，与 CLI 表无关。

---

## 7. 残留欠账（本轮没修，明确移交）

1. **基线待重建（给主线）**：`tools/ci/native_product_baseline.json` 仍写 `cli_broken: 1`、
   `cli_total: 10`，现值 `0 / 9`。`cli_broken` 走「只降不升」，下降只打印提示不判红；
   `cli_total` 没有判据。**所以现在不红，但基线数字是过期的**，请在 S2 合并点用
   `--write-baseline` 重建（红线：只在合并点）。
2. **文档里还有两处更深的 llvm 腐烂**，属设计文档级、不在本次口径内：
   - `docs/从光明到LLVM.md:1051/1111/1145/1171/1266`：`light build ... --backend llvm --emit-ir`。
     实测 `cli/light.py` **既没有 `build` 子命令**（只有 `pkg build`），**也没有 `--emit-ir`**，
     加上 `llvm` 已摘除，一条命令三处不成立。要么按现状改写，要么标注为设计稿。
   - `tools/packager/build_example.py:14/375` 与 `tools/packager/RELEASE_CHECKLIST.md:25`
     的 `--backend llvm`：那是 packager **自己的**参数（不是 `cli/light.py` 的 choices，
     门禁正则不扫它），需要单独核实它背后调的是哪条腿、是否也已死。
3. **`自测报告_任务G9_S1.md:123` 提到 `light run --backend llvm`**：历史报告，按「文档腐烂
   混合处置」不改写历史交付物，仅在此记账。
4. **归档区目前只有 llvm 一条**，`test_已摘除归档不许藏活着的后端` 里 `assertIn("llvm", 归档)`
   是刻意钉住的历史账。若未来真把 llvm 复活成可用后端，改的人必须同时动这条断言 ——
   这是设计意图（强制一次显式裁决），不是脆弱测试。
5. **e2e 夹具在 Windows 上会造假红**（本次撞上、未修）：`tests/e2e/test_e2e_chain.py:137-141`
   的 `subprocess.run(..., text=True)` 缺 `encoding='utf-8'`，与 `:28-32` 给子进程强设的
   `PYTHONUTF8/PYTHONIOENCODING=utf-8` 打架。**注意这不是「给测试套 UTF-8 包裹」那类禁忌**
   （禁的是 reconfigure 捕获流 / 给整场加 `PYTHONUTF8`），而是让**父进程的解码口径与它自己
   已经给子进程设定的口径对齐**，一处参数：`encoding='utf-8', errors='replace'`。
   它影响的是全仓 e2e 夹具、且只在非 UTF-8 locale 的机器上显形（FreeBSD CI 不显形），
   所以不在本任务里顺手改，建议单独立项并在 Windows + FreeBSD 双平台各跑一次。

---

## 8. 合并点须注意（给主线）

1. **必须重建 `tools/ci/native_product_baseline.json`**（`cli_broken` 1→0、`cli_total` 10→9）。
   不重建不红，但基线会一直骗人。
2. 清单新增了顶层键 `已摘除CLI路径`。门禁**不读**这个键（`规范化` 用 `dict(data)` 原样透传，
   `校验` 只看三张表），所以对指标零影响；`--sync-list` 也只动模块表，不会碰它。
   后续谁再摘除一条后端取值，收尾口径是「挪进这个归档区」，不是「改状态」也不是「直接删」。
3. 两条新断言在 `tests/unit/test_ci_gates_round9.py::Test真清单在册` 里，是**真仓库**断言：
   任何一路以后动 `cli/light.py` 的 `--backend choices` 而不同步清单，都会在这里红，
   而不再是一行可以视而不见的告警。
4. `assert_quality` 存量仍是 **469**（新加的测试没引入任何新违规形态）。
