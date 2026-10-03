# 光明（Light）中文编程语言 · 宣传文档

> 版本：**v0.4.0-rc2** ｜ 状态：预发布候选（稳定版槽位 `0.4.0` 已预留）
> 更新日期：2026-10-03 ｜ 语言本体仓库：`light-merge`
> 一句话定位：**一门让中国人用母语思维编程、并能被自己复刻的语言。**

---

## 一、它是什么

「光明」（Light，英文包名 `light`，CLI 入口 `light` / `lightc`）是一门**全中文关键字**的编程语言。

它不追求把中文"翻译成"代码，而是让关键字本身就是中文：

```light
设 数字列表 为 [1, 2, 3, 4, 5]
遍历 数字列表 之 值：
    若 值 % 2 == 0：
        打印(值)
```

- **L0 核心字（30 个，永久冻结）**：控制流、类型定义、异常、逻辑值、自指连接、组织 —— 全部高层语法都由这 30 字组合而来，永不改动。
- **L1 白话体**：19 个 L0 子集 + 中文标点 + 自动类型推断，青少年零门槛入门。
- **L2 文言体**：全部 30 个 L0 + 英文标点 + 显式类型 `: 整`，面向商用大项目、多人协作。
- **L3 领域嵌入层**：SQL / 正则 / 数学公式原生写成语法，参数化，防注入。
- **L4 外语引用层**：直接 `引 C:` / `引 Go:` / `引 MoonBit:` / `引 Python:`，复用全球生态并沙箱隔离。

> 术语澄清：L0–L7 是**语法层级（文体与方言）**，不是编译器内部分层。编译器是 5 段前端 + 代码生成 + 三后端（SRC 默认 / ANTLR 兼容 / LLVM 原生）。

---

## 二、核心亮点（为什么值得关注）

| 亮点 | 事实 |
|---|---|
| 🀄 **中文语法** | 30 个 L0 核心字稳定内核，L1/L2 双轨并行，符合中文思维习惯 |
| 🚀 **自举编译** | 编译器本身用光明编写（`bootstrap_v3.light`，95 个段落），可自举编译 |
| ⚡ **LLVM 原生编译** | 编译为原生 EXE，无需 Python 运行时；runtime C 层内置 TLS / SHA512 / HMAC / PBKDF2 / UUID / Base64 / 容器序列化等 |
| 📦 **三后端架构** | SRC 自研解析器（默认）· ANTLR 兼容旧语法 · native/llvm-typed 原生编译，`--backend` 灵活切换 |
| 🔧 **丰富标准库** | **109 个 `.light` 模块**，覆盖数学/字符串/数据结构/日期/农历/编码/哈希/加密/网络/大模型客户端/Agent 循环/系统/进程/线程/并发/事件总线/测试/中文分词/身份证校验/FFI/图像处理等 |
| 🔗 **原生腿能力** | 合计 **711 项**（builtin 411 + runtime 262），与 CPython 标准库字节级对拍 |
| 🏗️ **分层语法体系** | L0–L7 七层架构，教学与工程共用一套内核，零破坏兼容 v3.3 |
| 🌐 **生态打通** | CLI / LSP / 调试器 / AI Copilot / VS Code 扩展 / lightpub 运行时包 / lighting 积木库 |

---

## 三、近期开发回顾（2026-09 下旬 → 10-03）

### 3.1 版本线

| 版本 | 时间 | 关键动作 |
|---|---|---|
| 7.0.0 家族 | — | 双线（原光明 × 光明）合并，`CHANGELOG.md` 按版本取并集统一 |
| **0.4.0** | 2026-10-02 | **版本号家族统一**：全仓对外可见版本统一到 0.4.0，单一真源 `src/version.py`（`VERSION = "0.4.0"`）；`pyproject.toml = 0.4.0rc2`（PEP 440），`vscode-extension = 0.4.0-rc2`（SemVer） |
| **v0.4.0-rc2 tag** | 2026-10-02 凌晨 | 修正「rc2 的 tag 编出 rc1 的包号」漂移，四处版本串归位到 rc2；`release_preflight.py` 改为读本地最新 `v*` tag（按创建时间倒序），以后每个 rc 无需手改脚本 |
| 后续 | 10-03 | R110 收口后**版本维持 v0.4.0-rc2**，CHANGELOG 登记「已对齐上游 0.2.0-rc.2」 |

### 3.2 工程面硬成果

- **原生腿能力扩展**（R10–R13 四批 + CI 修复批）：builtin ~350 / runtime ~200 → **builtin 411 / runtime 262 / 合计 711**。
- **runtime C 层补齐 POSIX**：mbedTLS 后端（TLS_POSIX_MBEDTLS 宏）与 Windows Schannel 对齐；修复 `bio_send/bio_recv` 握手自锁，POSIX 下 HTTPS 从"永远阻塞"到可用。
- **密码学原生实现**：`dv_sha512` / `dv_pbkdf2_hmac_sha256_1` / `dv_uuid5` / `dv_uuid3`，与 CPython `uuid.uuid5()` / `uuid.uuid3()` 逐字符一致。
- **stdlib 从 60+ 扩展到 109 个 `.light` 模块**：新增网络请求（HTTPS/重定向/chunked）、农历（1900–2098 精确数据表）、中国行政区划（34 省级 + 445 地级市，GB/T 2260）等。
- **CI 红灯全清**：`ci_eval` 冒烟 6 块 + pytest 16 failed 全部修复。
- **能力清单自动重建**：`scripts/gen_native_capability_json.py` + `tests/unit/test_native_leg_capability.py`（11 用例校验）。

### 3.3 门禁与回归（硬基线）

| 项 | 值 |
|---|---|
| 门禁机 | 0.82 FreeBSD 15.1（家庭实验室 `192.168.1.5`） |
| 门禁基线 | 本机 Windows 全量 **8489 用例**，其中 **passed 8352 / failed 0 / skipped 126**（2026-10-01 19:30，mode=full） |
| CI 徽章快照 | **7912 passed / 0 failed / 新增红 0**（README 徽章） |
| R110 收口验证 | Windows 全量 **8489 用例 / 0 new_red**；R55 时代 5 个已知红全清；唯一 failed 为已知 flaky（`test_进程类`，单跑复绿） |

> 门禁纪律：`.gitea/workflows/ci.yml` 为**权威**（0.82 自托管实时跑）；`.github/workflows/ci.yml` 为对齐镜像，**未启用**，请勿据此判断实时状态。

---

## 四、R109 / R110 两轮收口亮点

### R109（2026-10-01）：债清收口轮

- 闭合 **4 条历史账**：R99③ `_light_re` import hook 缺陷（LH 最大红源，0 改动销账）/ R103 挂载集对话内切换接入总入口 / R99 临时脚本清理（早已出清，no-op）/ R107-G 地板清单门禁接 CI（`.gitea`+`.github` 双树）。
- 全量回归：**1171 passed / 1 skipped / EXITCODE=0**，引入 0 红。
- 地板门禁脚本 `assert_floor_manifest.py` 本地实跑通过（158 条，分类 62/15/68/13/0）。

### R110（2026-10-03）：上游 0.2.0-rc.2 增量对齐

- 对齐 deepseek-harness 上游 `dsh-v0.2.0-rc.2`（`639ed01539`）相对 rc.1 的**187 commits / 1022 真增量文件 / +33253 / -6141**（三点基准 `rc.1...rc.2`，merge-base `4878cdabd8`）。
- 逐包甄别 → **纯逻辑面待移植 4 组**（schedule framing / user-questions 状态机 / tool-ask-user timed / shell 提示词文案），其余全登记为宿主面。
- 本轮回基线修正：分发书原 `e5b5ccbfcb..rc.2` 两点口径有误，已纠正为三点基准（`e5b5ccbfcb` 是 fork 合流提交，会冒 freebsd 假删除）。
- **版本维持 v0.4.0-rc2 不动**（纯逻辑面 = 0 文件 < 10，按判据维持）。

---

## 五、生态与配套

| 配套 | 说明 |
|---|---|
| `lightpub` 运行时包 | light-merge 生态包分发 |
| `lighting` 积木库 | 积木式组件库（`light-merge/lighting`） |
| VS Code 扩展 | 语言支持（`vscode-extension/`） |
| LSP / Debug Adapter | `lsp/`、`debug-adapter/` |
| AI Copilot | LoRA 7B / ERNIE SFT 微调指南 |
| `AWESOME-光明.md` | 第三方生态索引 |
| `docs/ecosystem/README.md` | 生态地图 |

**相关仓库（三远端布局：内网 gitea 192.168.1.5 + GitHub + GitCode）**

- 语言本体（本仓）：`github.com/skywalk163/light`
- 复刻 harness（lightharness）：`github.com/skywalk163/lightharness`
- 积木库（lighting）：`github.com/skywalk163/lighting`

---

## 六、当前状态与下一步

- **当前**：v0.4.0-rc2（预发布候选），正式 `0.4.0` 槽位已预留。
- **已验证**：Windows / FreeBSD 0.82 / Linux 0.86 三平台门禁；LLVM 原生 EXE 编译；自举编译。
- **待办**（部分来自 R110 遗留）：
  1. 0.86 Linux / 0.82 FreeBSD 基线 JSON 补生成（逻辑上无新红风险）。
  2. 纯逻辑面 4 组候选移植项：lightharness 无对应纯逻辑层承载，已按"暂缓"登记，待 lightharness 侧模块补齐后回移植。
  3. 稳定版 `0.4.0` 出口：待 rc2 稳定观察期结束后 bump。

---

## 七、数据真实性声明

本文所有数字（版本号、用例数、模块数、原生腿能力数、commit/文件数）均取自本仓库内权威文档：

- `light-merge/README.md`、`light-merge/CHANGELOG.md`
- `lightharness/CHANGELOG.md`（含 R109 / R110 收口记录）
- `lightharness/docs/功能对标/R110_交付报告.md`
- `lightharness/docs/国庆7天/Day15_总结.md`
- `lightharness/reports/R110_lm_windows_latest.json`

未引用任何联网推测；如与本仓最新 `git log` / `reports/` 基线 JSON 不一致，以仓内数据为准。