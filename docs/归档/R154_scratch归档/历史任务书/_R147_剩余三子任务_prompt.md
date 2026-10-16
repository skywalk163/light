# R147 剩余任务 · 三子任务分派 prompt（主 agent 收拢，2026-10-14）

> 用法：三条 prompt 各自独立、可直接粘贴派给一个执行代理。派完由主 agent 收口（0.82 终检 + commit/push + `_R147_收口报告.md` + 记忆）。
> 根目录一律 `G:\dswork\duan-light-merge\light-merge`（下称 LM）。cwd 必须在 `light-merge/` 内。

## 状态速览（本轮已完成，勿重做）

**A 线 src/ 改动已由主 agent 完成并验证**：
- `src/llvm/codegen_typed.py`：`_deref_value` 已应用到 ~40 个「标量读取/只读」内置（REF 解引用，修 `整数(dict字段)=0`/`格式化时间=1970`）。
- 多参 `打印` 已修：原实现只发 `args[0]`、`args[1:]` 静默丢弃；改为逐参 `dv_print` + 参间 `dv_print(" ")` + 末参 `dv_println`，与 src 腿 `print(*args)` 一致。
- dict 字面量「UAF」**经复核为误判**（原代码正确，症状实为多参打印 bug），已回滚改写。
- R131 补登：codegen 新增内置 `socket_bind/listen/accept/shutdown/set_nonblocking/get_peer_addr` + `poller_unregister`（C 层与 IR declare 早已就位，纯暴露）；`stdlib/socket.light` 新增段 `bind/listen/accept/set_nonblocking/shutdown/get_peer_addr`，`stdlib/selectors.light` 新增段 `注销`。native 探针全绿。
- 双 gen 已刷新且 `--check` 通过；`tests/unit/test_native_leg_capability.py` 11 passed。
- 本机定向已验：多参打印、REF 解引用、两腿一致（仅布尔 repr `真/假` vs `True/False` 为预存差异）。

---

## §通用纪律（三条 prompt 共用，必读）

1. 单写者：本轮**只有 A 线可动 `src/**`**；B/C/D/E 零 `src/` 改动。动手前整篇读 `docs/工程纪律_TRUNK_BRIDGE_APP.md` 并按 §〇 贴标签、过防误删协议。
2. 汇报须含**真实命令 + 退出码**；判据与题面冲突以实测为准并写明。子代理不许谎报，主 agent 会亲自复验。
3. git：`git add <显式文件>`，**绝不 `git add .`**；**不 commit / 不 push**（交主 agent）；scratch `_r147X_scratch/` 保持未跟踪不进仓；新文件 `bareLF=0`。
4. 0.82 权威机：`ssh ai@192.168.0.82 'bash -c "..."'`（默认 sh 不支持数组）；跑前过 `scripts/跑前CPU门禁.py`（≥80%→INVALID）；大跑批必加 `ulimit -v <KB>`。0.82 pytest 用系统 python3.12 全局 pytest，`-o addopts=""` 中和 pyproject timeout 依赖（或 `--timeout=120`）。**0.82 同时只允许一条线跑 `-n 4` 全量门**（定向单测 `-n 1/2` 可并行）。
5. 本机 LM 全量：`CODEBUDDY_SAFE_DELETE_ENABLED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -n 4 --dist loadscope -q -p no:cacheprovider`（注意：本机 xdist 偶发 `node down` 属资源型 infra，非回归；**权威判据以 0.82 为准**）。
6. **全程禁跑 `pull_stdlib_from_light.py`**。
7. 改 codegen/适配层后必跑双 gen（`scripts/gen_llvm_capability_matrix.py` + `scripts/gen_native_capability_json.py --check`）+ `tests/unit/test_native_leg_capability.py`。
8. 版本口径：一律 R 轮次 + v0.4.x，**禁 v7.0/v6.x**；`src/version.py` 保持 `VERSION="0.4.0"`。
9. 权威判据：**`0 failed` / `new_reds=0`**（预存红 3 条 `test_builtins_drift` 系列属环境性缺兄弟仓，见子任务 3 台账）。

---

## 子任务 1 — A 线收尾（🔴 TRUNK · 唯一可动 src/）

**背景**：A 线 src/ 改动已完成并验证（见上方「状态速览」）。本子任务**只补测试 + 反跑哨兵 + 缺陷账 + 交付报告**，默认**不再改 src/**（除非发现真 bug，届时你是唯一 src/ 写者）。

**要做**：
1. 新增 `tests/unit/test_R147_R131_漏登.py`：源码级断言 `src/llvm/codegen_typed.py` 的 `_gen_typed_builtin` 中已注册 `socket_bind/socket_listen/socket_accept/socket_shutdown/socket_set_nonblocking/socket_get_peer_addr/poller_unregister`（及对应中文别名）；断言 `stdlib/socket.light` 导出 `bind/listen/accept/set_nonblocking/shutdown/get_peer_addr`、`stdlib/selectors.light` 导出 `注销`。可复用 `tests/unit/test_native_leg_capability.py` 的核验套路（真实 fork 编译 + 运行需在 0.82）。
2. 新增 `tests/unit/test_R147_文件原语_deref打印.py`（文件名自定但须 `test_R147_*`）：覆盖 ① REF 解引用——dict 字段（属性 + 下标两种）喂 `整数/取模/整除/四舍五入/格式化时间` 结果正确；② 多参 `打印` 两腿一致（`打印("x", 5)` 输出 `x 5`）。两腿对拍用 `cli/light.py run --backend src|native`。
3. **反跑哨兵**：注释掉 `_gen_typed_builtin` 里 `poller_unregister`（或 `socket_bind`）分支 → `stdlib/selectors.light`（或 socket.light）对应段在 native 腿报「未定义段落」→ 恢复转绿；把两条命令 + 结果写进交付报告。
4. 更新 `docs/功能对标/语言缺陷账.md`：
   - 新增一条 **L-2xx 候选（多参打印丢参，已修）**：根因（`_gen_typed_builtin` 里 `if name in ('输出','打印')` 只发 `args[0]`）、修复、证据（探针 + 两腿一致）。
   - 记录 **R131 漏登补登**（socket 服务端 6 + poller_unregister 1，纯暴露，非新 C）。
   - **更正**：此前「多 dict 字面量 UAF」为误判（原 dict 字面量代码正确），如实写明，不给 dict codegen 记假修复。
5. 写 `_R147_A线交付报告.md`（结构：根因/做了什么/证据命令+退出码/影响面/回滚方案/未竟项）。
6. **验证**：双 gen `--check` 绿 + `test_native_leg_capability.py` 全绿 + 新增 `test_R147_*` 本机绿 + **0.82 全量门 `0 failed`/`new_reds=0`**（0.82 重建见 MEMORY §3）。

**交付物**：`tests/unit/test_R147_*` 两个 + 缺陷账更新 + `_R147_A线交付报告.md`。
**验收（主 agent 0.82 复验）**：双 gen rc=0；`test_native_leg_capability.py` 全绿；新增测试绿；0.82 全量 `0 failed`/`new_reds=0`。

---

## 子任务 2 — B 线 + C 线（🟡 BRIDGE · 零 src/）

**背景**：B 线（顶层 import hook 治 L-207 + 文件系统.py 删除 + 影子再降）与 C 线（数学/JSON Tier1 落地）本轮**均未开工**（无 scratch）。两者都属 stdlib 纯光明层，纠在一起做。当前影子 **34/123**（R146-B 后）。

**B 线要做**（详见 `_R147_并行任务书.md` §B）：
1. **顶层 import hook 通用化（治 L-207）**：现状 `stdlib/__init__.py` 57 处相对 star-import 只认 `.py`；R146-D 只在 `tests/test_stdlib_phase2.py` 顶部局部挂了 `_light_import_hook`。在 `stdlib/__init__.py`（或 `cli/light.py` 引导处）引入通用钩子——同名 `.light` 含「纯光明实现」魔数且 `.py` 为影子时，import 走 `.light`；无 `.light` 时回退 `.py`。验收：最小探针 `import 数据结构; import 集合` 行为等价直接跑 `.light`；新增回归 `tests/unit/test_R147_顶层hook.py`。
2. **文件系统.py 删除评估**：前置 = `文件系统.light` 达 115/115 + 三腿对拍一致 + 通用 hook 接住顶层 import。满足则 `git rm stdlib/文件系统.py` + 三断点复核（`stdlib/__init__.py` 命名空间 / 显式加载 helper / 同源重复断言）+ `scripts/bootstrap_rate.py` 确认 shadow 34→**33**；**不满足则登记剩余清单留 R148，不删、不计失败**。
3. **影子再降冲刺（≤30）**：复扫其余 33 个 `.py` 影子中「`.light` 含魔数且对拍一致」者，逐模块走七步（读证据→hook 接住→三腿对拍→oracle 按口径改造→`git rm .py`→三断点复核→bootstrap_rate 复核）。**oracle 改造两种口径**：原生腿 vs oracle 改 `_light_import_hook` 加载 `.light`；src 腿 vs oracle **必须改内联期望值**（再指 `.light` 即恒真）。**护栏 `test_stdlib_import_consistency.py` 放宽为 `_PURE or _ONLY_LIGHT`**。

**C 线要做**（详见 `_R147_并行任务书.md` §C）：
1. **Tier 1 纯 `.light` 落地**：数学基础族（取整/绝对值/幂/对数/三角基础/随机封装）、JSON 序列化/反序列化（纯字符串拼装 + dict/list 构造）；只动 `stdlib/数学.light` / `stdlib/JSON核心.light`（或新建 `.light`），与 `.py` 参考实现**三腿对拍**（native/src/参考）。分歧不强行合并，登记待修。
2. **Tier 2 只登记不越权**：`builtins.py:452/462/468` 内部级联（JSON 深层解析依赖的内部 builtin 解耦）、数学高精度/复数等需 native 绑定项 → 登记回 A 线 stretch，**不动 `src/`**。
3. 对拍记录进 `_r147c_scratch/`（不进仓）。

**验证**：`scripts/bootstrap_rate.py` shadow 只降不升（≤33，力争 ≤30）、file-rate/关键路径/逃逸不倒退；**0.82 全量门 `0 failed`/`new_reds=0`**。
**交付物**：通用 hook 改动 + `tests/unit/test_R147_顶层hook.py` + `文件系统.light` 删除或剩余登记 + 数学/JSON Tier1 实现 + `_R147_B线交付报告.md`（含 C 线段落）。
**注意**：`bootstrap_rate_baseline.json` 只由 **A 线独占刷新**；B 线只跑 `bootstrap_rate.py` 验证。

---

## 子任务 3 — D 线 + E 线收尾（🟢 APP · 零 src/）

**背景**：D 线已有 scratch（`_r147d_scratch/`：L-208 扫描 `defs_scan.json`、假绿探针 `probe_dup.py`、`test_R145_hardened.py`）；E 线已有 scratch（`_r147e_scratch/`：`引用复核_29项.log`、refaudit*.sh）。本子任务**把两线收到终态**。**注意**：`_R147_并行任务书.md` 里 D 线的「L-208 删空 `.light`」默认动作已被主 agent **重定性推翻**（见下），以本 prompt 为准。

**D 线要做**：
1. **L-208 重定性（重要，覆盖任务书默认）**：28 个「定义数=0」的 `.light` 经复核**不是缺陷**——它们是**标准双文件模块**（`.py` 真身 + 同名 `.light` 是待迁移占位/门面），**不得删**（保持 28 文件为一条纪律，**不要批量删 `.light`**，也不要删 `.py`）。正确动作：① 在 `docs/功能对标/语言缺陷账.md` 把 L-208 置为「重定性：非缺陷·标准双文件模块，勿删」并写明判据；② 若确要根治「能力虚报」，只在 `scripts/gen_native_capability_json.py` 加「定义数=0 的 `.light` 不计入能力清单」规则（**不删文件**），并 `--check` 复核。
3. **假绿断言硬化**：`tests/unit/test_R145_文件系统补齐.py:135` 的 `assert len(dup) >= 1`（恒真下界）改为有信号断言（如 `assert len(dup) == 1 and dup[0].endswith("a.txt")`）；跑 `tools/ci/assert_quality.py --root .` 确认不再报该条；顺扫 `tests/unit/` 其它「非空/下界断言式」逐个硬化或说明。
4. **预存红台账固化**：把 3 条 `test_builtins_drift` 系列预存红（缺兄弟仓 lightharness，环境性非回归）写入 `tests/ci_environment_reds.txt`，含复现命令 + 净舱实证结论，供权威门 `new_reds=0` 口径比对。

**E 线要做**：
1. **历史临时物大清理（防误删协议最高优先级）**：对每个 `_rXXX_scratch/`（`_r131/_r137/_r138/_r140b/_r142/_r143/_r144/_r145*/_r146*/_r147a` 等）+ 探针 + `_r127_082_*.sh`/`_push_via_api.py` 全仓 `grep -rn "<对象名>" --include=*.md --include=*.py --include=*.light . | grep -v "_rXXX_scratch"` 确认无引用；**前置 = 无引用 + 结论已被测试/缺陷账固化**；满足才用**显式路径** `rm`/`git clean -f <path>`（**禁 `git clean -f` 无参数**，先 `git clean -ndx <path>` 预演）。台账更新 `_R147_临时物清理评审.md`（对象|动作|引用复核|日期）。`_R127_LH21红_立单.md` 评估 LH 仓是否闭环，无用于 LM 则按协议处理。
2. **L-194 深水区复测登记**：在 0.82 用 `_r143_remote82.py`（若保留）或新建最小复测脚本，重跑 `节点 --sample` 全量，记录内存曲线（MB/s 起始→SIGSEGV 点）+ 退出码；判定 R144 修点是否已止血「坏套接字无限拼接」（应不再 OOM 暴冲，仅剩异步 `等待` 局限 SIGSEGV）。产出 `_R147_L194_复测报告.md`，残余归 R119-B → 登记「L-2xx 候选」交主 agent，**本轮不强行修 src**。

**纪律**：不碰 `_r147a_scratch/`（A 线证据链，保留）；不删业务代码；清理只动未跟踪项 + 新建报告。
**交付物**：`tests/unit/test_R145_文件系统补齐.py`（硬化）+ `tests/ci_environment_reds.txt` + `_R147_临时物清理评审.md` + `_R147_L194_复测报告.md` + 缺陷账 L-208 重定性。
**验收**：`assert_quality.py` 零新增假绿；`test_R145_文件系统补齐.py` 全绿且断言有信号；临时物每项有结论、工作区 `git status --short` 仅余显式保留项；`0 failed`/`new_reds=0`。

---

## 收口（主 agent 亲做，不在三子任务内）

三线回传后：五线复验 → 0.82 全量终检 `0 failed`/`new_reds=0` → 缺陷账（L-207/L-208/R131/多参打印 L-2xx 统一编号）+ `ROADMAP.md`「最后更新」行 → `git add <显式文件>` + commit + push 三远端 → `_R147_收口报告.md` → 任务书归档 `_archive/task-books/` → 更新 `.workbuddy/memory/`。
