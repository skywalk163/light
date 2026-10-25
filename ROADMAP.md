# 光明（Light）公开路线图

> 最后更新：2026-10-26（R166 全量门可重复性 + CI 真跑 + PY 腿对齐轮；判绿机 **0.88**（0.82 已关机）；干净树 `c33368c26` + R166 四线改动全量门 **9409 collected / 9268 passed / 128 skipped / 10 xfailed / 3 xpassed / 0 failed / 0 errors / new_reds=0**，E/F 两轮均绿（本轮主题即「可重复」）；R165 native 腿深水区（L-235 就地闭包 env、L-229b LIST 浅拷 UAF）+ 全量门基线 12→0 条；R166 修 **L-239**（`异步 运行 同步段落()` PY 腿 `asyncio.run(None)` 崩溃）+ E5 段② 翻转为默认真跑 + P4/P5 判据噪声容差化；以下 R147 段落为历史快照）
>
> 历史（2026-10-14，R147 收口：五线全闭环，0.82 权威全量门 **4807 passed/76 skipped/2 xfailed/0 failed/0 errors/new_reds=0**，errors 由 R146 的 7 → 0（补齐兄弟仓 lightharness）；A 线原生腿三处已修——**L-209 多参打印丢参**（`打印("x",5)` 只出 `x`，改逐参 `dv_print`+参间空格+末参 `dv_println` 对齐 src 腿 `print(*args)`）、**REF 不解引用**（dict 下标/属性返回 type-8 REF，标量读取内置误读垃圾字段致 `整数(dict字段)=0`/`格式化时间=1970`；新增 `_deref_value` 应用到 ~40 个只读内置，写回模型零改动）、**L-210 R131 漏登补登**（`socket_bind/listen/accept/shutdown/set_nonblocking/get_peer_addr`+`poller_unregister` 的 C 实现与 IR declare 早已就位，纯补 codegen 暴露 + `socket.light`/`selectors.light` 门面段，零新 C 代码）；⚠️ 同时更正 A 线一度误判的「多 dict 字面量 UAF」——实为多参打印 bug，dict 字面量 codegen 无改动；B 线 **L-207 已修**（`_light_import_hook.LightFinder.find_spec` 对子模块从父包 `__path__` 找 `.light`、仅含魔数才接管 + `stdlib/__init__.py` 在 star-import 前自动 install），`文件系统.py` 未达 115/115（96/116≈83%）**不删**、19 项缺口登记 R148，影子维持 34/123；C 线数学/JSON Tier1 经复核已在 `.light` 落地，补三腿对拍 17 例；D 线 **L-208 重定性**（28 个「定义数=0」`.light` = 标准双文件模块，非缺陷勿删；实证 `gen_native_capability_json.py` 从不扫 `.light`、`bootstrap_rate.py` 已按 decl≥1 口径处理 → 两脚本均无需改，**拒绝为不存在的「能力虚报」加死代码规则**）、`test_R145_文件系统补齐.py` 假绿断言硬化（变异验证 4/4 有牙）、`tests/ci_environment_reds.txt` 补 W-42~W-48；E 线历轮临时物 30 项处置（26 隔离 `_archive/r147_cleanup/`、10 清除、零误删）、**L-194 0.82 复测：`节点 --sample` RC=0/桶=可跑/SMOKE_OK、maxRSS 113 MB、RSS 曲线无线性增长 → R144 修点生效，~29MB/s→SIGSEGV 症状当前 HEAD 不可复现**（与 R145-B 一致，残余归 R119-B，本轮不新开 L 编号）；新增回归 `test_R147_R131_漏登.py`(5)/`test_R147_文件原语_deref打印.py`(4)/`test_R147_顶层hook.py`(6)/`test_R147_数学JSON补齐.py`(17) 共 32 例；双 gen + 能力门(11 passed) + assert_quality(零新增假绿) + bootstrap(影子 35→34、自举率 75.61%、关键路径 100%、逃逸 0) 全绿；五线交付报告 + 收口报告齐备；任务书归档 `_archive/task-books/R147_并行任务书.md`）
> + **R146 收口（2026-10-14）**：A 线原生腿 L-203(dict `.键` 属性访问恒空)/L-204(类字段嵌套 dict 读回内层键错乱)/L-206(self 接收者漏出 R125-A2 截胡保护) 三处已修，双腿对拍+反跑有牙+回归测试 7 passed，0.82 权威全量门 **4768 passed/75 skipped/2 xfailed/0 failed/new_reds=0**（仅 7 errors 为预存红 `test_builtins_drift` 环境性缺兄弟仓 lightharness，非回归）；B 线 `数据结构.py` 影子删除→影子数 35→34；D 线 L-205 hook 化 `tests/test_stdlib_phase2.py` 顶部挂 `_light_import_hook`，TestSet 4 红转绿；E 线 19 项隔离物清 18 留 2（防误删协议）；C 线 101 缺口分层 + 发现 28 个注释桩 `.light` 登记 L-208；五线交付报告齐备；任务书归档 `_archive/task-books/R146_并行任务书.md`。
> 详细技术路线见仓库内 [`docs/ROADMAP.md`](docs/ROADMAP.md)；本文件只保留**对外可承诺**的部分。

## 当前版本

- 语言本体：**v0.4.0**（稳定，2026-10-03 版本号统一发布）
  - ⚠️ **版本号口径铁规**（R139 起强制）：仓库内所有 `v5.x / v6.x / v7.x` 字样均为**历史阶段代号**，写于 2026-10-03 版本号体系统一之前，**不是**当前真实版本号。历史文档原样留档，但对外表述一律用「光明 / light · v0.4.0」。
- 复刻 harness：r95-dev（2026-09-25，R95 根因战场闭环）
- 积木库：独立仓 `lighting`（14222 积木 / 45 领域）

## 北极星（3 个月，到 R98）

> 一个新人在**零作者介入**下，能跑通：发现 → 安装 → Hello World → 复用一个第三方包 → 提交第一个 PR。

## 阶段

### ✅ R96（本轮 · 诚信与地基）
- CLI 命令可用性校正：`light fmt` 因语义破坏缺陷默认关闭并标注（R96-KI-01），其余命令实测可用；
- 三仓治理文件补齐（LICENSE / CONTRIBUTING / CODE_OF_CONDUCT / SECURITY / SUPPORT / CHANGELOG / ROADMAP / CONTRIBUTORS）；
- 生态地图 + `AWESOME-光明.md` + RFC 提案流程；
- 版本一致性校验脚本（`scripts/check_version_consistency.py`）。

### ✅ R97（工具兑现 · 已闭环）
- ✅ **T9 修复 R96-KI-01**：`src/formatter` 收敛为空白安全子集（R97 完成，R136 E 线复核：R96-KI-01 复现用例 3 次 RC=0，`test_formatter_safety.py` 6 passed）；
- ✅ **T10/T11** `light doc` / `light profile` 对真实工程可用（R136 D 线：lightharness 5 工程体端到端 RC=0，分阶段耗时 + 内存峰值输出）；
  - ⚠️ **R136 E 线登记**：D 线实现落在 `src/doc_generator.py` / `src/profiler.py`（HEAD 中本已存在，非 stub），未按任务书 §6.4「新建独立顶层文件」执行，见 `_R136_收口报告.md` §D 线红线登记；
- ✅ **T12** `light install/publish` + 共享 registry（R137 A 线：本地 git 模拟 registry 下 install/publish 全链路 RC=0，`contrib/registry_git_tmpl/registry.json` 为模板；**R144-E 默认远端已落地**：区域选择，国内默认 gitcode `https://gitcode.com/light-lang/registry/raw/main/registry.json`、国外默认 github `https://github.com/skywalk163/light/raw/main/registry/registry.json`，覆盖方式 `--registry-url` / `--registry-region` / 环境变量 `LIGHT_REGISTRY_REGION`，默认 domestic，不做 geo-IP 探测；`tests/unit/test_R137_install_publish.py` 17 例全绿（含区域解析优先级 + 本地文件桩「raw 落 200」离线断言）；真实 registry 仓库待用户侧建：gitcode `light-lang/registry` + github `skywalk163/registry`，待建清单见 `docs/包管理器使用指南.md`「默认远端与区域选择」）；
- ✅ **T13** 积木库 ↔ `light pkg` 打通（R137 B 线：`light pkg blocks list/install/publish` 落地，48 个领域可被安装进光明项目并 `light run` 跑通；发布方向降级为「反向导出候选」，见 `lighting_bridge.py` docstring）；
- ✅ **T14** LSP 诊断服务（R137 C 线：新增 `src/lsp_diagnostic.py` + `lsp/diagnostic_extension.py` + `lsp/diagnostic_server.py`，`--diagnostic` 默认 off，显式 `semantic` 开启；didOpen/didChange 叠加未定义符号等语义诊断，0-based range 正确）；
- ✅ **T15** CI badge 动态生成（R137 D 线：`tools/ci/gen_badge.py` 真跑测试生成 `docs/ci_badge.svg` + `docs/ci_badge.json`，README 徽章改指本地 SVG，不联网）。
- ✅ **T16** LSP 编辑体验补全（R140-B：对 `lsp/light_lsp.py` 的格式化 / 重命名 / 语义高亮 / 文档高亮·引用四项做真实验证并精确修补——缩进栈格式化 + rangeFormatting range 对齐、代码区掩码重命名 + 合法性/冲突校验、legend 对齐 + 严格 delta 编码、引用排除字符串与注释；新增 `tests/unit/test_R140_LSP_完整化.py`）。
- ✅ **T17** 原生腿语义正确性深挖（R140-A：修 **L-182 段参数遮蔽失效**（`codegen_typed.py::get_var/set_var` 前置形参旁路）与 **L-191 多模块顶层段名串作用域**（`codegen.py`/`compiler.py`/`codegen_typed.py` 逐语句模块切换）；`native_run_readiness` 基线刷新 **66→67 可跑、编不过 1→0、pair_rate 78.87%→79.17%**；0.82 全量 `tests/unit/` 4647 passed；**L-194 运行期线性内存泄漏**（~120 MB/s，`节点网络.light::收全部` socket 无限拼接 OOM）**已修（R144）**：`节点网络.light` 加 16 MiB 缓冲上限 + `客户端.请求` 校验 `连接socket`/`发送socket` 返回码 + `runtime_typed.c` `dv_socket_recv` 硬化 + 新增 `dv_socket_set_recv_timeout`/`SO_RCVTIMEO` + `codegen_typed.py` 分派 + `socket.light` 导出；0.82 实测 `客户端.请求` rc=0 干净错误、`节点网络.light --sample` rc=0 SMOKE_OK、全量门 0 failed；完整 `节点 --sample` 残余 ~29 MB/s 属 R119-B 原生腿异步 `等待` 局限（A 线 src/**，独立深水区））。
- ✅ **T18** `--target wasm` CLI 接通（R140-C：`cli/light_unified.py::compile_with_src` 补 `elif target=='wasm':` 分支，路由到 `src/wasm_target.py`；`--target wasm` 默认产出 `.html`（standalone/Pyodide），`-o xxx.json` 产出 Pyodide JSON，stderr 打印「经 Pyodide 执行的 Python」提示；顺手修 `wasm_target.py` docstring 过期函数名；`tests/test_R140_C_wasm_cli.py` 7 例全绿）。
- ✅ **T19** 文档债务清理（R140-D：`docs/blog/` 11 篇历史版本号口径统一（加「历史文档」注记，正文原样保留）；`docs/ROADMAP.md` 状态跟随 R139/R140（模式匹配五类 / 原生腿异步 runtime / L1 可跑率 67 / L4 语料 merge / LSP 完整化）；`docs/known_issues.md` §13.3 由「已核实未修」更新为「已接通（R140-C）」；根 `ROADMAP.md` 跟随）。

> **R97「工具兑现」已于 R137 对外声明闭环**（T9–T15 全部完成）。

### 🚀 R98（发行与增长）
- 官网门户（对标 go.dev 三栏）；
- 在线 Playground（WASM 后端）；
- 一键安装脚本；
- 3 个样板第三方包 + 发布教程；
- 展示墙 + 月度 Newsletter + 生态热度榜。

## 不在计划内（明确划界）

- 不改变核心编译器后端架构（LLVM/C/WASM 探索单列于 `docs/ROADMAP.md`）；
- 不做商业托管 / 云 IDE（社区开源优先）。

## 如何参与路线讨论

- 提案：见 [`docs/community/rfc流程.md`](docs/community/rfc流程.md)；
- 想法：GitHub Discussions → ideas 模板；
- 进度：各轮收口报告（如 `R95_收口报告.md`）与 `docs/known-issues/`。
