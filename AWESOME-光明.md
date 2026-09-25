# Awesome 光明（Light）

> 一份社区维护的光明语言资源索引。对标 awesome-go。
> 收录标准：公开可访问、与光明直接相关、对社区有明确价值。**欢迎 PR 补充**（见底部「贡献条目」）。

## 目录

- [官方资源](#官方资源)
- [入门与教程](#入门与教程)
- [示例项目](#示例项目)
- [工具链](#工具链)
- [标准库与生态包（lightpub）](#标准库与生态包lightpub)
- [积木库（lighting）](#积木库lighting)
- [文档与文章](#文档与文章)
- [视频与讲演](#视频与讲演)
- [社区](#社区)
- [编辑器支持](#编辑器支持)

---

## 官方资源

- 语言本体仓库：<https://github.com/skywalk163/light>
- 文档站点（mkdocs / GitHub Pages 自动部署）
- 复刻 harness（lightharness）：<https://github.com/skywalk163/lightharness>
- 积木库（lighting）：<https://github.com/skywalk163/lighting>

## 入门与教程

- `docs/30分钟入门光明.md` — 30 分钟上手
- `docs/五分钟入门光明.md` — 极速体验
- `cli/tutorial.py` — 交互式 30 分钟教程（运行 `light tutorial`）
- 英文入门：`docs/en/30分钟入门光明.md` / `docs/en/getting-started.md`

## 示例项目

> 下面的 `examples/` 目录包含大量可运行 `.light` 示例，是学习首选。
- `examples/` — 语言本体内置示例集合
- lightharness 的 `examples/` — 用光明复刻的 agent harness 用法

## 工具链

- 编译器 / CLI：`light`（run / compile / check / type-check / ast / tokens / init / pkg / test / harness / py2light / repl / tutorial）
- 代码体检：`light check`（语法 + 类型检查，安全不改写文件）
- 文档生成：`light doc`（R97 验收中）
- 性能分析：`light profile`（R97 验收中）
- 格式化：`light fmt`（⚠️ R96-KI-01 语义破坏缺陷，默认关闭，需 `--force`）
- 包管理：`light pkg`（init / build / run / native / search / info / list / update / publish）
- VS Code 扩展：`vscode-extension/`（语法高亮 + snippets + 2 套主题）

## 标准库与生态包（lightpub）

- 运行时包目录：`stdlib/lightpub/`（56 个桥接模块 + `__index__.py` 元数据）
- 包 API 文档：`docs/lightpub/`（110 页自动生成）
- 代表性能力：HTTP 客户端 / 服务端、Socket、SQLite、JSON、CSV、加密、URL 解析、事件驱动、任务队列、Web 框架

## 积木库（lighting）

- 仓库：<https://github.com/skywalk163/lighting>
- 规模：**14222 个积木文件 / 45 个领域**（排序 / 数据 / 类型 / 系统 / 统计 / 数学 / 密码 / 网络 等）
- 索引：`索引.json`；选型器：`选块.py` / `语义选块.py` / `embedding选块.py` / `混合选块.py`
- 静态文档站：`docs_site/`（build_docs.py 构建）

## 文档与文章

- `docs/blog/中文编程的生态建设之路.md`
- `docs/blog/中文编程的语义密度优势.md`
- `docs/blog/中文编程语言的未来.md`（⚠️ 部分历史文章仍沿用旧品牌「段言」，正在统一）

## 视频与讲演

- `光明之路_讲演稿.md` / `光明之路.pptx`（社区分享材料）
- `光明×LightHarness_宣传海报`（品牌物料）

## 社区

- GitHub Issues / Discussions（bug_report / feature_request / ideas / help / showcase 模板齐备）
- RFC 提案流程：`docs/community/rfc流程.md`
- 行为准则：`CODE_OF_CONDUCT.md`
- 安全政策：`SECURITY.md`
- 支持渠道：`SUPPORT.md`

## 编辑器支持

- VS Code：`vscode-extension/`（高亮 + snippets + 主题；R97 计划升级为 LSP 诊断）

---

## 贡献条目

在 **Pull Request** 中按以下格式补充（标题 `docs: add awesome entry <名称>`）：

```markdown
- [条目名](链接) — 一句话说明（作者 / 维护者）
```

收录规则：链接须公开、与光明直接相关、非商业推广。失效链接会在季度清理时移除。
