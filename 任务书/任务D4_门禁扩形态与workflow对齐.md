# 任务 D4：门禁扩形态与两份 workflow 对齐

> **前置必读**：`第四轮总纲.md`（尤其 §2.3 自举率防造假、§3 D4 的特殊授权与限制、§5.1 不许断字符串）
> **独占文件**：`tools/ci/**`、`.gitea/workflows/**`、`.github/workflows/**`、
> `docs/known_issues.md`、`docs/自举率报告.md`、`tests/unit/test_capture_encoding_guard.py`(若需新建)、
> 新建 `第四轮留档/**`
> **越界即停**：**不许改任何不属于自己的测试文件**。基线里属于 A4/B4/C4 文件的条目照原样进基线
> （存量冻结），要改的写进移交清单。
> **合并顺序**：你**最后合**。前三路都进 main 之后才重建基线、写最终数字。

---

## 0. 本轮你要拦住的两类真事故

**第一类：unittest 写法完全绕过了假测试门禁。**

现有门禁只扫 `assert '...' in py_code` 形态（101 条），
但 `self.assertIn('...', py_code)` 同口径实测 **114 处**——**比它拦住的还多**：

- `tests/test_ffi_stdlib_mock.py`：51 处
- `tests/unit/test_c_backend.py`：55 处
- `tests/_test_three_features.py`：8 处

放宽到「第一参数是字符串字面量」的全部 `assertIn` 是 **636 处**（52 个文件）；
`self.assertIn(` 总调用 **718 处**（57 个文件）。

**第二类：`.github/ci.yml` 有三个 `|| true` 没有 junit 兜底，一个用例没跑也算绿。**

`.github/workflows/ci.yml:88`、`:93`、`:104` 三处 `|| true` 后面**没有任何存在性检查**。
pytest collect error（import 失败、语法错误）→ 零用例执行 → 步骤绿。
对比 gitea 侧每个 `|| true` 后面都跟了 `test -f .ci/*.xml`（`:125`、`:138`、`:152`）。

---

## 1. D4-1：门禁扩三类形态（已裁决取保守口径）

**裁决：保守口径。** `assertIn` 沿用现有 `_STR_TARGETS` 产物变量白名单
（`py_code|pycode|ir|c_code|source|产物`），不扫任意字符串字面量。

要加的三个形态：

| 形态 | 实测处数 | 说明 |
|---|---|---|
| `self.assertIn('...', <产物变量>)` | 114 | 与现有 string-assert 同口径，只是 unittest 写法 |
| `assert len(x) >= N`（N>0） | 27 | 下界断言，集合非空即恒真 |
| `assert x is not None` | 153 | 只断「不是 None」，零信号 |

**`assert len(x) >= N` 的 27 处逐条**（复核实测，可直接用来验证你的正则命中数）：
`tests/test_linter.py`:106,118,130,148,161,177,204,250,260,337（10）；
`tests/test_llvm_net.py`:624,662,702（3）；`tests/test_parser.py`:184,220,249,262（4）；
`tests/test_migration.py`:185,282（2）；`tests/test_async.py`:390；
`tests/test_context_manager.py`:159；`tests/test_filesystem.py`:483；
`tests/test_iterator_protocol.py`:115；`tests/test_type_system_v4_2.py`:314；
`tests/test_llvm_optimization.py`:48；`tests/e2e/test_module_e2e.py`:116；
`tests/e2e/test_e2e_chain.py`:134（各 1）。

⚠️ **`tests/test_async.py:390` 与 `:659-660` 那批是 C4 本轮要改的**。
C4 先合、你后合，所以你重建基线时它们应该已经消失。**别把它们写进基线**，
基线要在 C4/A4/B4 都进 main 之后重建。

**顺手清掉两个空跑门禁**：`returncode-in`（`assert_quality.py:50`）与
`trivial-ge0`（`:48`）**全仓零命中**。要么删掉，要么在注释里写明「预防性形态，当前零命中」——
不许留着让人以为它在拦什么。

**判据 D4-1**：
1. 扩形态后基线重建，总数落在 **390–400**（保守口径预期值 103+114+27+153=397，
   减去 tokenize 豁免的 docstring 误命中）。**报告里贴实测总数与四类的分项计数。**
2. **每个新形态都要有反跑**：写一条该形态的探针进某个测试文件 → 门禁必须红并点名 →
   删掉探针 → 门禁恢复绿。三个形态三份输出。探针文件用 `_taskD4_` 前缀，**收尾删干净**。
3. **跨平台键归一必须保住**：基线键不许带 `os.sep`（第三轮 gitea run 71 就是这么红的）。
   验证方式：拿一份把 `/` 全换成 `\` 的基线副本再比一次，仍 rc=0。
4. 基线重建后 `assert_quality.py` 在本机 rc=0。

---

## 2. D4-2：自举率门禁加「防造假」维度

现状口径（`bootstrap_rate.py:43`、`:61-99`）：分母 = `stdlib/` 下所有 `.light`（69），
分子 = 至少有 1 行 `段落`/`类`/`函数` 的文件（17），17/69 = 24.64%。

**结构性事实（复核实测）**：52 个未算实现的文件**100% 是「纯 `导出` 声明 + 同名 `.py` 影子」**，
一个例外都没有；17 个有实现的里**只有 `列表工具` 有 `.py` 影子**。
也就是说「有 `.py` 影子」与「无实现」几乎是同一件事——**门禁完全没度量这个维度**。

按总纲 §2.3 追加的防造假口径，要做两件：

1. **新增度量维度**：报告「有同名 `.py` 影子的 `.light` 数」。这个数只许降不许升
   （新写的模块不该再造影子）。
2. **防造假检查**：若某个 `.light` 的实现体只是转手调用同名 `.py`（`导入 <自身模块名>`
   或再导出它的符号），**不许记为「有实现」**。
   判据可以粗一点（grep `导入 <自身模块名>`），但要明确写出误判/漏判边界。

**顺手修两处文档串与真值不符**（`bootstrap_rate.py:12`）：
- 写着「当前 16/68 ≈ 23.5%」，真值 **17/69 = 24.64%**
- 写着行维度「85.8%」，按脚本自己的口径实算是 decl 364 / code 4034 = **9.02%**

**判据 D4-2**：
1. 门禁输出里出现「影子数」这一项，且有基线
2. **反跑**：造一个 `stdlib/_taskD4_探针.light`，里面只写 `段落 X: 导入 _taskD4_探针`
   这类转手调用，门禁必须**不**把它记为有实现（或明确报违规）。探针收尾删干净。
3. 自举率数字不许因为你改口径而**虚涨**——若新口径把 `列表工具` 从 17 里剔出去变成 16/69，
   那就如实报 16/69 并在 `docs/自举率报告.md` 写明口径变更，**基线同步下调并说明原因**。
   （只许升不许降的规则针对「同口径」，口径变更要显式说明。）

---

## 3. D4-3：两份 workflow 判绿语义对齐

**复核出的不一致清单（7 条，逐条处理并在报告里逐条回答「怎么处理的」）**：

1. **回归闸门缺失**：gitea `:175-184` 的
   `check_regression.py --baseline tests/ci_baseline_failures.txt --soft-classname 'tests.test_*' 'tests._test_*'`
   在 github 侧**完全没有**。后果：github 的 unit/integration/e2e 是**裸硬判、无存量豁免**，
   gitea 是「软跑 + 基线对比」。**两边判绿语义相反。**
2. **lightpub 文档可导入性闸门**（gitea `:195-198`）github 无
3. **积木库门禁**（gitea `:205-210`）github 无（在独立的 `eval.yml`）
4. **崩溃兜底不对齐**：github 的 3 处 `|| true`（`:88`、`:93`、`:104`）**没有任何 junit 存在性兜底**
5. **并发不对齐**：gitea 探测 xdist 后 `-n auto`（`:106-107`、`:136`、`:146`）；github 完全串行、没装 xdist
6. **依赖不对齐**：github 装 `cryptography`（`:55`）；gitea 靠 `--system-site-packages`（`:78`）借宿主的包
7. **matrix 差异**：github PR 走 `ubuntu × (3.10,3.13)`，push main 走 3 os × 4 py，
   且 `continue-on-error: ${{ matrix.os != 'ubuntu-latest' }}`（`:25`）

**处理原则（不是全都要抹平）**：
- 第 4 条**必须修**：没有 junit 兜底的 `|| true` 是纯假绿，风险最高
- 第 1 条**必须有明确裁决**：要么 github 也接回归闸门，要么把 github 的软化步骤改成硬判并接受红。
  **不许维持「两边语义相反且没人知道」**
- 第 2、3、5、6、7 条：写清「保持差异」还是「对齐」，以及为什么。
  平台差异（FreeBSD vs ubuntu/windows/macos）导致的合理差异不必强行统一

**判据 D4-3**：
1. 每个 `|| true` 后面都有存在性/兜底检查（两份都过一遍）
2. **反跑**：故意让某个软化步骤 collect error（临时塞一个 import 不存在模块的探针测试文件），
   验证该步骤**不再显示为绿**。探针 `_taskD4_` 前缀，收尾删干净。
3. 7 条不一致逐条给出处理结论

---

## 4. D4-4：`time_budget.py --dry-run`

现状（`time_budget.py:99-119`）：打的是硬编码字面量，`:102-107` 还写着
「105 条违规」（真值 103）、「run #66 基线：492.6s」，**没有一次 `time.time()` 调用**，
`:104-105` 甚至自陈「需实测该 9+2 文件耗时」，**唯一出口是 `return 0`**。

它从未被任何 workflow 调用（CI 只用 `--mark` / `--check`），所以**实际风险 = 0**。
但它作为「确认新增没吃掉预算」的证据被引用过（`第三轮留档/D3交付报告.md:95,227`、
`合并报告_第三轮.md:191`）——**这才是问题**。

**二选一，在报告里说明选了哪个**：
- 改成真测量（真跑那几个脚本并计时）
- **删掉 `--dry-run` 这个开关**，并在引用过它的两份文档里加勘误说明

注意 `--check` 是真判定、会红（`:59-75`），**别把它一起删了**。

---

## 5. D4-5：Windows 捕获流护栏（查明它到底还在不在）

**这条要先查证再动手。** 第二轮有一批「给 `sys.stdout.reconfigure(` 补 `errors='replace'`
+ 挂 AST 级护栏 `tests/unit/test_capture_encoding_guard.py`」的止血修复，
在 2026-08-22 的 `reset` 里丢了（见 memory `project_第二轮回滚与取证`）。
第三轮总纲 §10 又说「`tests/conftest.py` 已修，别再改回去」。**两个说法冲突，以你实测为准。**

要查明并在报告里给出结论：

1. 全仓哪些文件调用了 `sys.stdout.reconfigure(` / `sys.stderr.reconfigure(`？各自有没有带 `errors='replace'`？
   （已知涉及过 `tests/test_summary.py`、`tests/test_class_definition.py`、`tests/test_comprehensive.py`）
2. `tests/unit/test_capture_encoding_guard.py` **存在吗**？不存在就明确说「不存在」
3. `tests/conftest.py` 里到底修了什么

**注意授权边界**：那三个 `test_*.py` **不在你的独占清单里**。
若它们确实缺 `errors='replace'`，**写进移交清单**，由主线在合并点处理。
你能做的是：**新建**（若不存在）`tests/unit/test_capture_encoding_guard.py` 这条 AST 级护栏
——这个文件在你的独占清单里。

**判据 D4-5**：
1. 护栏用例：AST 扫全仓 `.py`，任何 `reconfigure(` 调用若 `encoding` 参数存在而
   `errors` 参数缺失 → 红，报文点名文件行号
2. **反跑**：临时给某文件加一个不带 `errors` 的 `reconfigure` 探针 → 护栏必须红 → 删掉恢复绿
3. 若实测发现那三个文件已经带了 `errors='replace'`，护栏应当直接绿——
   **报告里贴实测输出证明「现状是绿的」而不是「我加了个永远绿的东西」**

---

## 6. D4-6：最终数字与留档

前三路都进 main 之后：

1. 重建假测试基线（D4-1），跑一次自举率（D4-2），把最终数字写进 `docs/自举率报告.md`
2. 本机定向回归 + 推远端等 CI 结论，把 **run 号 + status + 耗时**写进
   `第四轮留档/` 与合并报告——**不许人工拼数字，汇总行直抄**
3. `docs/known_issues.md` 补本轮的移交项与仍缺项

**CI 结论怎么拿**（第三轮踩过，直接用）：
- 状态：`http://192.168.1.5:3000/api/v1/repos/skywalk/light/actions/tasks?limit=10`
  （无 token，按 `head_sha` 精确匹配自己推的提交；`/actions/runs` 是 404）
- **失败要看是哪一步**：`curl.exe -s -o 文件 "http://192.168.1.5:3000/skywalk/light/actions/runs/<run_number>/jobs/0/logs"`
  → 200 全量文本，grep `Failure -` 定位失败步骤名。
  注意是 **web 路由 + `run_number`**；`/api/v1/.../actions/runs/<n>/jobs` → 404，
  `/api/v1/.../actions/jobs/<id>/logs` → 401
- 日志里非 ASCII 是 GBK 显示乱码，用 `errors='replace'` 读

---

## 7. 交付格式

按总纲 §9 六项。本任务特别要求：

- **反跑证明是本任务的核心交付物**（§9.3）。D4-1 三个形态、D4-2、D4-3、D4-5 各一份
  「造回退 → 变红 → 恢复 → 变绿」实测输出。第三轮的教训写在合并报告 §十二.3：
  **验收「门禁接入」的唯一方法是造一次回退看它红不红，不是 grep 到脚本存在。**
- **基线文件必须进仓**：`.gitignore` 的 `*.json` 曾把 `tools/ci/*_baseline.json` 吃掉，
  已加 `!tools/ci/*_baseline.json` 负规则。新增基线文件时**先 `git check-ignore -v` 验一遍**。
- 基线键**不许带平台分隔符**（第三轮 run 71 的根因）。新写任何基线都要过这一关。
- 移交清单要写清「哪些假绿在别人的文件里、建议怎么改」，**不许顺手改**。
- 临时探针文件全部 `_taskD4_` 前缀，**收尾删干净**（工作树必须干净）。
