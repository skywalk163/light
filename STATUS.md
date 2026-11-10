# 光明（Light）当前状态

> 单一入口：本页只写可核验的当前状态，数据均注明口径与出处；历史细节见 CHANGELOG.md。
> 本页不承诺日期，不列路线图时间点。

## 版本与定位

- 版本：**0.4.1**（唯一真源为 [pyproject.toml](pyproject.toml) 的 `project.version`，`src/version.py` 同步）。
- 定位：中文关键字编程语言，L0–L7 分层语法，转译腿（Python）与原生腿（C runtime）双后端，CLI 入口 `light` / `lightc`。

## 已稳定

- 全量门禁：9421 collected / 9323 passed / 88 skipped / 10 xfailed / 0 failed / 0 errors，`new_reds=0`（最近一次全量：2026-10-26，R167，0.88 全量门 `-n 0` 连跑两轮；快照见 [tests/ci_baseline_failures.txt](tests/ci_baseline_failures.txt)）。
- 用例数口径：junit `<skipped>` 记 98 = 88 skipped + 10 xfailed；`failed` / `errors` 按 pytest 汇总行，不按 junit 元素数（口径写在基线文件头）。
- 标准库：`stdlib/*.light` 顶层模块 **119 个**（口径 `ls stdlib/*.light | wc -l`；本页数值为 2026-11-10 在本分支实算，子目录模块不计入）。
- 版本号单一真源：`tests/unit/test_version_single_source.py` 覆盖 `pyproject.toml` / `src/version.py` / CLI 兜底串（T-0228，2026-11-02 恢复全绿）。
- 后端与工具链：转译腿、原生腿、C 后端代码生成，CLI / LSP / 包管理见 [docs/API_REFERENCE.md](docs/API_REFERENCE.md)；验证方式为各模块定向 pytest，阶段记录见 `docs/ROADMAP.md`。

## 实验性

- **不保证 API 稳定**：下列能力处于实验态，接口、内置名与行为可能随轮次调整。
- L3–L7 语法层级（SQL/正则/数学 DSL、L4 外部语言引用、L5 异常与模块、L6 无空格分词、L7 类型注解）：规格见 `docs/level5_spec.md`、`docs/level7_spec.md`，可用层级以 `src/version.py` 的 `SUPPORTED_LEVELS` 为准。
- 原生腿与转译腿仍有语义分歧：边界与未覆盖形态见 [docs/原生腿能力边界.md](docs/原生腿能力边界.md)；R163-B 实测「原生腿经模块限定名调用 .py 侧函数返回空」仍登记为语言级限制。
- WASM（Pyodide）后端、`light fmt` 空白安全子集：默认关闭或需显式启用，见 `ROADMAP.md` 与 [docs/known-issues/README.md](docs/known-issues/README.md)。
- 平台边界：Windows 本机 `tests/unit` 全量在 xdist 高负载下有 node down 风险，判绿以 0.82 / 0.88 门禁为准（见上条 known-issues 看板）。

## 最小可用面

> 五个方向各一行，边界文档为 [docs/MVP_SURFACE.md](docs/MVP_SURFACE.md)（尚未合并，合并后以该文件为准）。

- 语言内核：L0–L2 中文关键字与分层语法，规格 [docs/L1_白话体语法规范_v4.0.md](docs/L1_白话体语法规范_v4.0.md)。
- 标准库：`stdlib/*.light` 顶层 119 模块，索引 [docs/STDLIB_REFERENCE.md](docs/STDLIB_REFERENCE.md)。
- 运行后端：转译腿 `light run`、原生腿 `--target native`，边界 [docs/原生腿能力边界.md](docs/原生腿能力边界.md)。
- 工具链：CLI `light` / `lightc`、包管理 `light install` / `light publish`，用法 [docs/API_REFERENCE.md](docs/API_REFERENCE.md)。
- 上手路径：[docs/getting-started.md](docs/getting-started.md) 与 `docs/AI编程指南.md`（语法坑位以该指南为准，本页不复制）。

## 最近一轮变更

- [0.4.1] 2026-11-02：T-0228 发布，版本号单一真源推进到 0.4.1，无功能变更。
- [LH-3] 2026-10-29：lighthive 第三轮复测，4 条误记 + 4 条已修（编译缓存 key 加 stdlib 指纹、`可重入锁()`、三级属性赋值）。
- [T-0197] 2026-10-29：内置层对拍七条（LH-02/03/04/07/08/11/14）。
- [R167] 2026-10-26：门禁假绿清零轮，全量门 9421 collected / 0 failed（`docs/ROADMAP.md` 头部）。
- [R160] 2026-10-18：协程运行时就绪轮（L-219 已修、E-5 src 腿、L-217 立项）。

## 已知欠账

- CI 存量基线：[tests/ci_baseline_failures.txt](tests/ci_baseline_failures.txt)（9421 collected、0 failed / 0 errors；88 skipped / 10 xfailed 口径见文件头）。
- 语言缺陷账：[docs/功能对标/语言缺陷账.md](docs/功能对标/语言缺陷账.md)（L-xxx 编号，含未修项与判定证据）。
- 语言本体已知问题：[docs/known_issues.md](docs/known_issues.md)；工程侧 CI / 门禁类：[docs/known-issues/README.md](docs/known-issues/README.md)（KI-Rxx 看板）。
- 原生腿未覆盖形态：[docs/原生腿就绪度指标.md](docs/原生腿就绪度指标.md)（分母与逐项登记，不做清零表述）。
- 轮次归档在 `docs/归档/轮次报告/`；本页只链真实文件，不代销账、不粉饰。
