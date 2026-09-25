# 光明生态地图

> 一句话定位：光明生态由**语言本体**、**运行时包（lightpub）**、**积木库（lighting）**、**复刻 harness（lightharness）** 四块组成。新人先看懂下面两张表，再决定「我该去哪找轮子」。

## 一、四个仓库 / 资产的边界

| 资产 | 仓库 / 位置 | 是什么 | 怎么用 | 适合谁 |
|---|---|---|---|---|
| **语言本体** | `light-merge`（本仓） | 编译器 + CLI + `src/stdlib/` | `pip install light` 后写 `.light` | 所有使用者 |
| **运行时包 lightpub** | `light-merge/stdlib/lightpub/` | 可 `导入` 的 Python 桥接运行时包（56 模块 + 元数据） | `导入 HTTP客户端` 等，随语言分发 | 需要 IO / 网络 / 加密的开发者 |
| **积木库 lighting** | 独立仓 `lighting`（14222 积木 / 45 领域） | 领域能力单元（积木），靠索引 + 选块器消费，**非 import 式** | `索引.json` + `选块.py` 检索 → 落地为代码 | 想复用「领域积木」的开发者 |
| **复刻 harness** | 独立仓 `lightharness` | 用光明 1:1 复刻的 agent harness（889 个 `.light`） | 跑 LLM agent 评测 / 二次开发 | 研究 / 复刻派 |

## 二、lightpub（运行时包）vs lighting（积木库）—— 选型表

**常见误区：以为 lightpub 和 lighting 是同一套东西。** 它们互补，**互相不可替代**。

| 维度 | lightpub（运行时包） | lighting（积木库） |
|---|---|---|
| 消费方式 | `导入 X`（运行时 import） | 选块器检索 → 落地为代码片段 |
| 存放 | 跟随语言本体分发（`stdlib/lightpub/`） | 独立仓库，自带 `索引.json` |
| 形态 | 完整 Python 桥接模块（类 / 函数） | 细粒度「积木」（更小、更专） |
| 适用 | 程序运行期调用（HTTP/Socket/DB/加密） | 编写期「拖一个能力过来」 |
| 典型 | `导入 HTTP客户端` 发请求 | 选「个税计算」积木生成函数 |
| 文档 | `docs/lightpub/`（110 页） | `lighting/docs_site/`（静态站） |

**决策树：**
- 我要「运行期调一个现成能力（网络/IO/加密）」→ **lightpub**（`light doc` 看 API）。
- 我要「写代码时复用一个领域功能单元」→ **lighting**（跑 `选块.py` 选一块）。
- 两者都满足不了 → 自己写，并考虑**反哺**（`light pkg publish` 或向 lighting 提 PR）。

## 三、上手顺序（推荐）

1. `docs/30分钟入门光明.md` → 写第一个 `.light`；
2. `light check 你的文件` 体检（安全）；
3. 需要网络/IO → 查 `docs/lightpub/`；
4. 需要领域积木 → clone `lighting`，跑 `选块.py`；
5. 想做 agent → 看 `lightharness`。

## 四、相关入口

- 第三方索引：[`AWESOME-光明.md`](../../AWESOME-光明.md)
- 公开路线：[`ROADMAP.md`](../../ROADMAP.md)
- 提案流程：[`docs/community/rfc流程.md`](rfc流程.md)
