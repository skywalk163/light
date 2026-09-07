# CI 修复任务计划（R13-CI）

> 生成：2026-09-07。状态：**待执行**（两项任务并行中，暂不动代码）。
> 依据：GitHub Actions 两段红灯 —— `ci_eval` 闸门（冒烟 6 块失败）+ pytest（16 failed / 4012 passed）。
> 调查结论：已在本地复现并定位根因，失败分两类：**A 类 = 本地也红的真回归**；**B 类 = 本地单跑绿、CI 整进程红的顺序耦合**。

---

## 复现矩阵（调查阶段实测）

| 失败项 | 本地单跑 | 本地整跑（同 CI 进程） | 分类 |
|---|---|---|---|
| ci_eval 冒烟：提取邮箱 / Base64编码 / MD5 / SHA1 / SHA256 / SHA512 | ✗ 红 | 同 | A 真回归 |
| test_模块表与stdlib咬合 | ✗ 红 | 同 | A 真回归 |
| test_对象池缓存_冒烟_O0 | ✓ 绿 | 同 | A 真回归（任务 5 已修复） |
| test_lightpub_doc_importability（2 围栏） | 未单跑 | 与 re 解析同根因 | A（依赖任务 2） |
| TestMathStdlibEnglishAliases（3 条） | ✓ 绿 | 预计红（未整跑，见任务 4） | B 顺序耦合 |
| R11C 中国行政区划/农历/传统节日（9 条） | ✓ 绿 | 预计红 | B 顺序耦合 |

---

## 任务 1：运行期内建缺失 —— 冒烟 4 块（Base64编码 / MD5哈希 / SHA1 / SHA256 / SHA512）

**根因（已确认）**：`_b64_encode` / `_md5` / `_sha1` / `_sha256` / `_sha512` / `_hmac_sha256` 这批"runtime 内建"**只在 LLVM codegen 路径有实现**（`src/llvm/codegen_typed.py:2482` 起的 T5B 段落）。而 `Base64.light`、`哈希.light`、`编码.light`、`编码解码.light` 直接按函数名调用它们。冒烟走 `cli/light.py run` 的非 LLVM 执行路径时这些名字不存在 → `名称错误 name '_b64_encode' is not defined`。

**步骤**：
1. 确认冒烟执行链路（`积木库/评估/冒烟.py` → `cli/light.py run`）实际走哪条 backend，以及为何没命中 codegen_typed 的内建分发。
2. 在 Python 侧 runtime（`stdlib/builtins.py` 或解释器内建注册表）注册同名 Python 实现（`base64` / `hashlib` / `hmac` 包装），口径与 LLVM 的 `dv_*` 函数一致（字节级对拍）。
3. 补一条单测：非 LLVM 路径真跑 `Base64.light` / `哈希.light` 与 Python 对拍。

**验收**：ci_eval 冒烟 4 块绿；`tests/unit/test_T5B_编码哈希.py` 全绿。

**改动面**：runtime 注册处 + 新单测。主要冲突风险：无（不动 codegen_typed）。

---

## 任务 2：`re` 模块解析劫持 —— 冒烟「提取邮箱」+ lightpub 文档 2 条围栏

**根因（已确认）**：`stdlib/正则表达式.light` 开头 `从 re 导入 re_编译 …`。run 路径把它解析到了 **CPython 自带的 re**（错误信息：`cannot import name 're_编译' from 're' (…/Lib/re/__init__.py)`），而不是 `stdlib/re.light`（纯光明正则引擎，里面有 `re_编译`）。`_light_import_hook` 虽然挂在 `sys.meta_path[1]`，但 run 路径要么没装钩子、要么模块解析器（`src/module_resolver.py`）先命中了 Python 内建/标准库。

**步骤**：
1. 追 `从 re 导入 …` 在 run 路径的完整解析顺序（module_resolver + code_generator 生成物 + 钩子），找到 CPython re 抢先的准确位置。
2. 修复：让 stdlib 目录的 `re.light` 优先于 CPython 同名模块（或在钩子/解析器里对「stdlib 存在同名 .light」的名字做拦截）。
3. 修复后跑 `tests/unit/test_lightpub_doc_importability.py`；若围栏仍红，按测试提示重跑 `tools/gen_lightpub_docs.py` 降级。
4. 顺带检查同模式风险面：`sys` / `time` / `inspect` 等 Python 同名模块在 run 路径是否同样被劫持错（`stdlib/` 里有对应 .light）。

**验收**：冒烟「提取邮箱」绿；`test_lightpub_doc_importability` 绿。

**改动面**：module_resolver / _light_import_hook / 正则表达式相关生成物。与任务 1 均独立。

---

## 任务 3：能力清单咬合 —— 模块表缺 24 个模块

**根因（已确认，本地复现）**：`任务书/原生腿产品清单.json` 的模块表只有 89 条，而 `stdlib/` 实际枚举出 113 个 .light（`tools/ci/native_product.py:202 实际模块名`）。缺的 24 个：`re、sys、time、inspect、uuid工具、中国传统节日、中国行政区划、中文分词、中文数字转换、中文文本处理、中文编码、农历、图像处理基础、字符串工具、手机号校验、拼音转换、数据结构、数据验证、断言工具、缓存、网络请求、身份证校验、进度条、高级文件` —— 即 R11C/R12 两轮 .light 化（含改名，如 `拼音转换`）后清单没补齐，commit 250c04c8 重建时用了旧口径。

**步骤**：
1. 用 `native_product` 自带的"模块表补齐（只增不改）"逻辑重建清单（或其生成工具入口），新增条目按实际状态标 `可编译 / 不可编译 / 未实测` + 阻断原因。
2. 检查 `test_模块表与stdlib咬合` 外的另两张清单（地板清单 / 分布式判据）是否也需同步（本CI未见红，抽查即可）。

**验收**：`test_模块表与stdlib咬合` 绿。

**改动面**：仅 `任务书/原生腿产品清单.json`（数据文件）。最轻，可先做。

---

## 任务 4：纯光明 .light 与同名 .py 契约对齐 + 导入钩子进程泄漏 —— 数学 3 红 + R11C 9 红

**根因（已确认机制）**：
- `stdlib/数学.light`、`中国行政区划.light`、`农历.light`、`中国传统节日.light` 首行都带「纯光明实现」魔数 → 钩子（`stdlib/_light_import_hook.py:205`）会**优先加载 .light 并无视同名 .py**。
- 这些 .light 相对 .py 缺契约：数学.light 的 `四舍五入` 只收 1 参（.py 是 `(x, 小数位数=0)`）、没有 `pi/pow/sqrt/sin/cos/tan/random/floor/ceil/round` 英文别名；三个数据模块 .light 没有 `ChinaRegion / LunarCalendar / ChineseFestival` 类名导出（原生腿无类）。
- 本地单跑绿是因为进程里没装钩子、`import 数学` 落到 .py；CI 整进程跑时，更早的测试（生成代码内 `install()`，见 `src/code_generator.py:1025-1026`）把钩子装进 `sys.meta_path` 且**从不卸载** → 后续直 import 全部落到 .light。

**步骤**：
1. 整进程重跑 pytest 复现这 12 条红（按 CI 顺序），锁定是谁装的钩子（二分到具体测试文件）。
2. 给钩子加卸载/夹具隔离，或把 install 限定在生成代码自己的执行作用域 —— 防止测试间状态泄漏。
3. 给 .light 补齐 .py 已文档承诺的契约：
   - `数学.light`：`四舍五入(x, 小数位数=0)` 双参 + `pi` 常量 + 10 个英文别名；
   - `中国行政区划.light` / `农历.light` / `中国传统节日.light`：导出 `ChinaRegion / LunarCalendar / ChineseFestival`（原生腿无类，按对拍测试的用法以工厂段落/兼容对象实现）。
4. **决策点（执行前拍板）**：契约以 .py 为准（测试与文档按 .py 写，建议此口径），.light 对齐；而非反过来改测试去适配 .light 子集。

**验收**：整进程 pytest 下 `test_match_elif_import_aliases.py`、`test_原生腿_R11C_数据高级.py` 全绿。

**改动面**：4 个 stdlib .light + 钩子。与任务 5 同碰 stdlib .light，注意先后。

---

## 任务 5：对象池缓存 O0 codegen 回归 —— ✅ 已修复

**根因（已二分定位，非 R12C/合并引入）**：`test_对象池缓存_冒烟_O0` 期望 `对象池放入("a")/("b")` 后取回 `'b'/'a'`，实际取回 `'[]'/'空'`（槽默认值）——**放入的值没写进池槽**。`对象池缓存.light` 是 R12 期间 .light 化的；嫌疑原在 R12B「嵌套容器写回」或 R12C「槽位池」。

**二分定位结论**：引入 commit = **`39d22ab9`**（R12B「变量/容器/索引写回根因修复」，含 R11A-02），与嫌疑区间 R12B 一致；R12C `0c5c9eb7` 与其后提交均已在原始提交上单独测试排除，main 合流后无合并冲突引入。机制不是列表/字典写回本身，而是 R12B 附带的 **R11A-02「内建名遮蔽」短路**：`_gen_typed_function_call` 里该短路对**带实参的调用**也生效，把 `stdlib/对象池缓存.light` 内层 `列表(对象, 整数(时间戳()))`（构造列表条目）劫持成局部变量 `列表` 的引用返回 → 构造函数从未执行 → 池槽条目没建出来 → 取回槽默认值。

**修复**：`src/llvm/codegen_typed.py` `_gen_typed_function_call` 的 R11A-02 短路加 `not expr.arguments` 守卫 —— 仅对无参调用（歧义引用）按变量处理，带实参调用继续走正常派发（段函数 → builtin）。改动 8 行插入 / 4 行删除（< 50 行）。

**步骤**（已完成）：
1. ✅ 最小化复现：`创建对象池 → 对象池放入(池,"a") → 对象池获取(池)`，LLVM O0 编译 + dump IR 确认写入路径（列表条目构造被短路）。
2. ✅ 二分定位：`git log -S` + 手工切 R12B/R12C 原始提交分别测试，引入点 = `39d22ab9`（R12B）。
3. ✅ 修 codegen + 固化回归测试 `tests/unit/test_对象池缓存_冒烟_O0.py`（含最小复现用例 + 原冒烟用例）。

**验收**：✅ `test_对象池缓存_冒烟_O0.py` 绿（2/2）；✅ 最小复现 O0 编译运行输出正确（`2\nb\n1\na\n空`）；✅ 反跑：改回原 codegen → 最小复现立即立红（`2\n空\n1\n空\n空`）；✅ R12B 写回归 `tests/unit/test_codegen_container_writeback_O0.py` 14/14 绿，无回归。ci_eval 冒烟可运行率：本 worktree 无 ci_eval harness（gitea 闸门文件不存在），以 O0 定向测试等价验证，对象池缓存块全绿。

**改动面**：`src/llvm/codegen_typed.py`（R11A-02 短路段，8+/4-）、`tests/unit/test_对象池缓存_冒烟_O0.py`（回归测试）。

---

## 任务 6：收尾验证与提交

1. 本地**整进程**全量 pytest（模拟 CI 顺序）：0 failed。
2. `python 积木库/评估/ci_eval.py --并发 8`：全部闸门 ✓。
3. 提交拆分建议（各任务独立 commit，便于回滚）：
   - `fix(runtime): 非LLVM路径注册编码/哈希运行期内建`（任务 1）
   - `fix(import): stdlib .light 优先于 CPython 同名模块`（任务 2）
   - `chore(capability): 模块表补齐 R11C/R12 新增 24 模块`（任务 3）
   - `fix(stdlib): 纯光明模块补齐 .py 契约 + 导入钩子进程隔离`（任务 4）
   - `fix(codegen): 对象池写回 R12 回归修复`（任务 5）

**建议执行顺序**：3（10 分钟，纯数据）→ 1 → 2（1、2 解锁 ci_eval 全绿）→ 4 → 5（5 需要二分，耗时最不确定）→ 6。
**与并行任务的冲突点**：任务 1/5 碰 `src/llvm/codegen_typed.py`；任务 2 碰 `src/module_resolver.py` 与导入钩子；任务 4 碰 `stdlib/*.light`。开工前先 git pull 确认并行分支没在改同文件。
