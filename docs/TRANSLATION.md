# 文档翻译规范与进度（Translation Guide & Progress）

本文件记录光明（LightLang）文档的多语言（中文 → 英文）翻译规范与进度。

This file tracks the conventions and progress of translating LightLang documentation (Chinese → English).

---

## 🌐 语言切换 / Language Switch

- 中文首页：`docs/index.md`
- English home：`docs/en/index.md`
- 在 `docs/index.md` 顶部已加入切换横幅：`[🇺🇸 English](en/index.md) · [🇨🇳 中文](index.md)`

---

## 📐 翻译规范 / Conventions

1. **目录结构**：英文文档统一放在 `docs/en/` 下，文件名尽量与中文源文件保持一致（中文文件名保留原样，如 `docs/en/30分钟入门光明.md`）。
2. **代码块不变**：所有 ` ```light ` / ` ```bash ` / ` ```python ` 代码块保持原样，不翻译关键字、标识符、字符串字面量。
3. **术语对照**：
   | 中文 | English |
   |------|---------|
   | 光明 | LightLang |
   | 段落 | function / paragraph (代码注释中保留「段落」) |
   | 设 / 为 | `设 X 为 Y` → keep as-is in code; prose: "create variable X with value Y" |
   | 遍历 | for-loop / iterate |
   | 当 | while |
   | 类 / 继承 | class / inherit |
   | 己 | `self` / `this` (in prose) |
   | 尝试/捕获/抛出/最终 | try / catch / raise / finally |
   | 导入 / 导出 | import / export |
   | 标准库 | standard library |
   | 原生编译 / LLVM 后端 | native compilation / LLVM backend |
4. **链接**：中文文档内部相对链接（如 `docs/syntax.md`）在英文版中指向对应的 `en/` 版本；暂未翻译的文档保留指向中文源。
5. **版本号**：保持源文档中的版本号（v7.0 等）不变，不翻译。
6. **Markdown 结构**：标题层级、表格、列表与原文档一一对应。

---

## 📊 翻译进度 / Progress

| 英文文件 (docs/en/) | 中文源 (docs/) | 状态 | 说明 |
|---------------------|----------------|------|------|
| `README.md` | `README.md` (根) | ✅ 本批次翻译 | 核心章节全文翻译（特性/架构/快速开始/语法/CLI/标准库/项目结构/FAQ/许可） |
| `30分钟入门光明.md` | `docs/30分钟入门光明.md` | ✅ 本批次翻译 | 14 个部分全文翻译，代码块原样保留 |
| `index.md` | `docs/index.md` | ✅ 既有 | 文档站首页（导航/新特性/路线图） |
| `getting-started.md` | `docs/getting-started.md` | ✅ 既有 | 快速开始 |
| `syntax.md` | `docs/syntax.md` | ✅ 既有 | 语法手册 |
| `stdlib.md` | `docs/stdlib.md` | ✅ 既有 | 标准库速查 |
| `package-manager.md` | `docs/包管理器使用指南.md`（待确认） | ⚠️ 既有·待核对 | `docs/package-manager.md` 当前不存在，源文件疑似改名，需确认映射 |
| `web-framework.md` | 待确认（疑似 `docs/编译器内部设计.md` 或独立 Web 框架指南） | ⚠️ 既有·待核对 | `docs/web-framework.md` 当前不存在，需确认中文源 |

**汇总**：`docs/en/` 现含 **8** 个英文文档；其中本批次新增 `README.md` 与 `30分钟入门光明.md` 两份核心文档。

---

## 🗓️ 后续迭代计划 / Next Iterations

优先级按「用户价值」排序，未翻译文档可后续分批补：

1. **高优先**：核对 `package-manager.md` / `web-framework.md` 的中文源映射，补齐链接一致性。
2. **中优先**：`docs/五分钟入门光明.md`、`docs/端到端实战教程.md`、`docs/USER_MANUAL.md`、`docs/tools.md` 的英文版。
3. **低优先**：设计类文档（`architecture.md`、`ffi.md`、各类 `*_design.md` / `*_report.md`）按需翻译。

---

## ✅ 本批次验收（定向测试）

- [x] `docs/en/` 目录存在且至少含 `README.md`
- [x] `docs/index.md` 含语言切换链接（`[🇺🇸 English](en/index.md)`）
- [x] `docs/TRANSLATION.md` 已创建（进度表 + 规范）
- [x] 包注册表 `/health` 端点返回 200 + JSON（上一阶段已完成）
- [x] 备份脚本可执行并生成有效 JSON（上一阶段已完成）

---

> 翻译原则（来自项目身份 SOUL.md）：准确高于速度、不伪造历史。已知/待确认项如实标注，不臆造源文件映射。
