# 光明（Light）中文编程语言 · 宣传文档

> 版本：**v0.4.2「智能原语版」** ｜ 状态：**正式版，已发布到 PyPI**（`pip install guangming==0.4.2`）
> 发布/更新日期：2026-11-15 ｜ 三远端：内网 Gitea `192.168.1.5/skywalk/light` · GitHub `skywalk163/light` · GitCode `skywalk163/light`
> 一句话定位：**一门让中国人用母语思维编程、并能被自己复刻的语言。**

---

## 一、它是什么

「光明」（Light，PyPI 包名 `guangming`，CLI 入口 `light` / `lightc`）是一门**全中文关键字**的编程语言。
它不把中文"翻译成"代码，而是让关键字本身就是中文：

```light
设 数字列表 为 [1, 2, 3, 4, 5]
遍历 值 于 数字列表：
    若 值 % 2 == 0：
        打印(值)
```

- **L0 核心字（永久冻结）**：控制流、类型定义、异常、逻辑值、自指连接、组织——高层语法全部由这批单字组合而来，**永不改动、永不新增**。
- **L1 白话体**：L0 子集 + 中文标点 + 自动类型推断，青少年零门槛入门（无文件头声明时默认文体）。
- **L2 文言体**：L0 全集 + 英文标点 + 显式类型（`: 整`），面向商用工程与多人协作。
- **L3 领域嵌入层**：SQL / 正则 / 数学公式原生写成语法，参数化，防注入。
- **L4 外语引用层**：`引 C:` / `引 Go:` / `引 MoonBit:` / `引 Python:`，复用全球生态并沙箱隔离。

> 术语澄清：L0–L7 是**语法层级（文体与方言）**，不是编译器内部分层。编译器是 5 段前端 + 代码生成 + 三后端（SRC 默认 / ANTLR 兼容 / LLVM 原生）。
> `v0.4.2` 是**编译器版本号**；`v4.0/v7.0` 是语法架构与旧产品线的历史里程碑，两者不是同一序列。

---

## 二、本版主角：智能原语，与中文语法**不打架**

### 2.1 先说结论：智能原语不是关键字

这几年 AI 编程最火的概念——观察、规划、执行、记忆——如果直接塞进关键字池，中文编程语言就死了：
日常词一旦变成保留字，用户连变量名都不能用；而且今天是「规划」，明天社区就会要求「筹谋」「盘算」。

光明的做法是**三层叠加，一层都不碰内核**：

| 层 | 做什么 | 成本 |
|---|---|---|
| L1 双字标准形式 | `观察 / 规划 / 决策 / 执行 / 记忆` 五个**普通标识符**（用户自己起的段落名） | 零语法改动 |
| L0 组合惯用法 | 用冻结的 `段 / 设 / 当 / 若 / 断 / 返回` 拼出「观察→规划→决策→执行→记忆」循环 | 零新关键字 |
| 前端弹性映射（可选） | 把「计划/安排/筹谋」这类口语变体**文本级**归一成「规划」 | 默认关闭，可逐文件开关 |

实测确认：这五个词**都不在** `keywords.ALL_KEYWORDS`（123 个）里。
`段落 规划` 与 `段落 算分` 在语法上完全同构——**智能是"形状"，不是"特权"**。

### 2.2 标准写法：L0 组合惯用法（本版新增可运行示例）

```light
段 观察(环境):
    返回 环境["信号"]

段 规划(信号, 轮):
    若 轮 >= 3:
        返回 "停"
    返回 信号

段 决策(动作):
    若 动作 == "停":
        返回 假
    返回 真

段 执行(动作):
    打印("执行动作: " + 动作)
    返回 动作

段 主():
    设 环境 为 ["信号": "走"]
    设 轮 为 0
    当 轮 < 4:
        设 信号 为 观察(环境)
        设 动作 为 规划(信号, 轮)
        若 决策(动作) == 假:
            断
        执行(动作)
        设 轮 为 轮 + 1
```

一眼可辨：这份"AI Agent 循环"里**没有一个新关键字**，全是 L0 冻结字。

### 2.3 口语写法：同义变体由前端吸收（默认关闭）

```light
# @智能弹性 开
段 看看(环境):
    返回 环境["信号"]

段 计划(信号, 轮):
    若 轮 >= 3:
        返回 "停"
    返回 信号

段 动手(动作):
    打印("计划已定: " + 动作)

段 主():
    设 环境 为 ["信号": "走"]
    设 动作 为 计划(看看(环境), 0)
    动手(动作)
```

映射表默认吸收这些变体：`看看/瞧瞧/感知→观察`、`计划/安排/筹谋/盘算/打算→规划`、
`拍板/定夺/拿主意→决策`、`动手/实施/落实→执行`、`记下/记住/存档→记忆`
（5 个标准词 / **23 条变体**）。要点三条：

1. **默认关闭**。不写文件头、不设环境变量，口语词就只是口语词，代码照常跑。
2. **保护区严格**。字符串（含中文引号 `「」『』`、三引号跨行）、`#` 注释、L3/L4 嵌入块
   整块透传——`打印("计划已定")` 输出仍是「计划已定」，文案不会被"优化"掉。
3. **关掉也合法**。弹性层是**风格归一化**，不是运行前提：把文件头改成「关」，
   口语版示例仍是一份合法的纯 Light 程序（e2e 已按这条验收）。

### 2.4 附带可观测性：编译期结构化轨迹

开启弹性层后，编译期顺带产出 `<文件名>.smart-trace.json`（零运行时开销，不注入任何代码）：

```json
{
  "pattern": "observe_plan_act",
  "events": [
    {"type": "tool_call",      "line": 49, "primitive": "观察", "callee": "观察", "scope": "主流程"},
    {"type": "decision_point", "line": 27, "primitive": "规划", "condition": "轮 >= 3", "l0_form": "若"},
    {"type": "side_effect",    "line": 37, "primitive": "执行", "kind": "print"},
    {"type": "duration",       "line": 48, "primitive": "主流程", "metric": "iterations", "static_bound": 4}
  ]
}
```

（摘自 `examples/智能原语/观察_规划_执行_口语变体.light` 的真实 sidecar，已删减到 4 条。）

`pattern` 判为 `observe_plan_act` 需要**同时**满足「三段都在」+「有 `当` 循环」，
三个散点调用不会误报。诚实标注：`duration` 是**循环静态上界**，不是真实运行耗时。

### 2.5 L0 零改动是可验证的，不是口号

```bash
git diff --numstat -- src/keywords.py src/lexer.py src/parser_stmt.py \
    src/code_generator.py docs/language/l0-core.md
# 输出为空 = 逐字节零改动
```

对**语言内核**相关的既有文件只动了两处：`cli/light.py::_read_source()` 加一个**默认关闭**的钩子、
`.gitignore` 忽略轨迹产物。（其余改动都是新增文件，外加打包配置与文档。）

> 一句话记住这套设计：**冻结的是骨架，生长的是说法，可观测的是形状。**

---

## 三、核心亮点

| 亮点 | 事实（可验证） |
|---|---|
| 🀄 **中文语法** | L0 核心字冻结，L1/L2 双轨并行，符合中文思维习惯 |
| 🧠 **智能原语（0.4.2 新增）** | 5 个双字标识符 + 23 条口语变体 + 编译期轨迹，**零新关键字、L0 零改动** |
| 🚀 **自举编译** | 编译器用光明自己写：`bootstrap/bootstrap_v3.light`，3014 行 / **115 个段落** |
| ⚡ **LLVM 原生编译** | 可编译为原生 EXE，不依赖 Python 运行时；runtime C 层含 TLS / SHA512 / HMAC / PBKDF2 / UUID / Base64 |
| 📦 **三后端** | SRC 自研解析器（默认）· ANTLR 兼容 · native/llvm-typed，`--backend` 切换 |
| 🔧 **标准库** | `stdlib/` 下 **119 个 `.light` 模块**（数学/字符串/日期/农历/编码/哈希/加密/网络/大模型客户端/Agent 循环/并发/事件总线/中文分词/身份证校验/FFI/图像处理…） |
| 🔗 **原生腿能力** | 声明 **711 项**（builtin 411 + runtime 262），与 CPython 标准库字节级对拍 |
| 🏗️ **分层语法体系** | L0–L7 七层，教学与工程共用一套内核 |
| 🌐 **生态打通** | PyPI 包 / CLI / LSP / 调试器 / VS Code 扩展 / lightpub / lighting 积木库 |

---

## 四、0.4.2 工程面：交付了什么

### 4.1 代码

| 文件 | 作用 |
|---|---|
| `src/smart_primitives.py` | 弹性映射 + 冲突诊断 + 编译期轨迹扫描（纯标准库，无第三方依赖） |
| `src/smart_primitives_map.json` | 5 个标准双字形式 / 23 条口语变体 |
| `cli/light.py` | `_read_source()` 增加默认关闭的可选钩子（**+37/−2 行**，含零依赖快判，未开启时不 import 模块） |
| `examples/智能原语/*.light` | 标准版 + 口语变体版，两个都可直接 `run` |
| `tests/test_smart_primitives*.py` | **61 项**：词法/语法、映射表与配置、四类冲突诊断、轨迹字段、向后兼容、示例运行 |

### 4.2 测试与回归

| 项 | 结果 |
|---|---|
| 智能原语单测 | **61 passed** |
| e2e 全链路（新示例 compile + 产物运行） | **4 passed** |
| 全量回归（改动前基线） | 278 failed / 9482 passed / 1 error |
| 全量回归（改动后） | **278 failed / 9547 passed / 1 error** |
| 失败集合逐条比对 | **新增红 0 / 消失红 0 / ERROR 与 SUBFAIL 完全一致** |

**诚实说明**：`278 failed` 是 main 上**既有**的环境/平台类红（原生腿 `test_原生腿_R13B`、
`test_R149/R150` 文件系统、LLVM 具名冲突、LLVM stdlib 就绪度），与本版改动无关，
也没被"顺手修绿"。本版验收口径是**失败集合不新增**，而不是"全绿"。

### 4.3 发布

- **PyPI**：`guangming 0.4.2`（wheel 2.2 MB + sdist 2.5 MB，`twine check` PASSED）。
  干净虚拟环境实测：`pip install guangming==0.4.2` → `light --version` 输出 `光明编译器 v0.4.2`，
  口语变体示例直接跑通。
- **修掉一个会坏在用户机器上的坑**：`pyproject.toml` 的 `package-data` 原本只收 `*.light`/`*.toml`，
  JSON **不进 wheel**——本地跑得好好的映射表，用户 `pip install` 后会丢，弹性层直接退化成
  3 条兜底原语。已补 `"src" = ["*.json"]`，并在装好的包里核到 **5 原语 / 23 变体**在位。
- **三远端**：`main` + `v0.4.2` tag 全部推送，三处 HEAD 一致，未使用 force。
- **文档**：`docs/AI编程指南.md` 新增「智能原语与中文口语变体」整节（AI 侧唯一真源）；
  `docs/syntax.md`、L1 规范、`CHANGELOG.md`、`mkdocs.yml` 同步；全库文档头版本对齐 0.4.2（35 个文件）。

### 4.4 诊断与开关

| 手段 | 效果 |
|---|---|
| 什么都不做 | 默认关闭 |
| 文件头 `# @智能弹性 开` / `关` | 逐文件开关（优先级最高） |
| `LIGHT_SMART_ELASTIC=1/0` | 本次运行开关 |
| `LIGHT_SMART_ELASTIC_TRACE=0` | 只关轨迹，归一化仍生效 |
| `LIGHT_SMART_ELASTIC_MAP=<json>` | 换自定义映射表 |

诊断码 `L-SMART-000..005`：变体撞关键字/内置名、同文件口语与标准形式混用、
一个变体映射到多个标准词、映射表加载失败（自动回退兜底表）、`on_conflict` 取值非法。

---

## 五、快速开始

```bash
# 1) 从 PyPI 安装
pip install guangming==0.4.2
light --version            # 光明编译器 v0.4.2

# 2) 跑一个智能原语示例
light run examples/智能原语/观察_规划_执行.light
light run examples/智能原语/观察_规划_执行_口语变体.light   # 文件头自带「开」

# 3) 从仓库跑（开发态）
python3 -m cli.light run examples/智能原语/观察_规划_执行.light
python3 -m pytest tests/test_smart_primitives.py tests/test_smart_primitives_edges.py -q -n 0
```

---

## 六、生态与配套

| 配套 | 说明 |
|---|---|
| PyPI 包 | `guangming`（本语言本体，`light` / `lightc` 入口） |
| `lightpub` 运行时包 | 生态包分发 |
| `lighting` 积木库 | 积木式组件库 |
| VS Code 扩展 | 语言支持（`vscode-extension/`） |
| LSP / Debug Adapter | `lsp/`、`debug-adapter/` |
| AI 编程指南 | `docs/AI编程指南.md`（AI 写光明代码的唯一真源，含机器可读诊断 `light ai check --json`） |
| `AWESOME-光明.md` | 第三方生态索引 |

**相关仓库**

- 语言本体（本仓）：`github.com/skywalk163/light`（内网 Gitea 为主，GitHub / GitCode 镜像）
- 复刻 harness（lightharness）：`github.com/skywalk163/lightharness`
- 积木库（lighting）：`github.com/skywalk163/lighting`

---

## 七、当前状态与下一步

- **当前**：v0.4.2 正式版，PyPI 已发布，三远端 tag 已打。
- **本版实测**：Linux 沙箱全量回归（9547 passed / 新增红 0）；PyPI 干净 venv 安装后
  `light --version` 输出与口语示例均通过；三远端 `main` HEAD 一致。
- **沿用既有基线、本轮未重测**：Windows / FreeBSD 门禁机基线、LLVM 原生 EXE 编译、自举编译
  —— 这三项是 0.4.0 基线能力，本版无相关改动（本版改动面 = 新增前端模块 + CLI 一个默认关闭的钩子）。
- **已知边界（不藏着）**：
  1. **文本级替换的天花板**：用户原有标识符恰好叫「计划」、且文件里没有「规划」时，
     无法与口语用法区分，会被静默改名。缓解：默认关闭 + 轨迹 `rewrites[]` 可人工核对。
  2. **部分子命令绕过钩子**：`ai check` / `ai prompt` / `py2light` 直读文件，不受弹性层影响。
     建议口语写法只用于主链路文件，或先 `compile` 归一化。
  3. **`read_text` 通用换行**：CLI 读文件会把 CRLF→LF（改动前即如此，非本层引入）。
  4. **既有 278 条红**：环境/原生腿/LLVM 类，独立工单，非本版引入。
- **下一步**：
  1. 把智能原语惯用法沉淀进 stdlib 示例集（事件总线 / 工作流 DAG 两条骨架已盘点完）。
  2. `duration` 从静态上界升级为可选运行时采样（需语言层钩子，属独立设计）。
  3. 清理既有 278 条环境类红，恢复"全绿"口径。

---

## 八、数据真实性声明与口径说明

本文所有数字均可在仓库内一条命令复核：

| 数字 | 复核方式 |
|---|---|
| 版本 0.4.2 | `python3 -c "import sys;sys.path.insert(0,'src');import version;print(version.VERSION)"` |
| 5 个标准词不在关键字表 | `PYTHONPATH=src python3 -c "import keywords;print([w for w in ['观察','规划','决策','执行','记忆'] if w in keywords.ALL_KEYWORDS])"` → `[]` |
| 23 条变体 | `python3 -c "import json;d=json.load(open('src/smart_primitives_map.json'));print(sum(len(v['variants']) for v in d['primitives'].values()))"` |
| 119 个 stdlib 模块 | `ls stdlib/*.light | wc -l` |
| 自举 115 段 / 3014 行 | `grep -c '^段落 ' bootstrap/bootstrap_v3.light`（=115）；`wc -l`（=3014） |
| 61 项新测 | `python3 -m pytest tests/test_smart_primitives*.py -q -n 0` |
| 回归数字 | `python3 -m pytest -q --tb=no`（本机实测 278 failed / 9547 passed / 1 error） |

**两处口径需要说明，避免误读**：

1. **L0 字表数量**：规范文案（`docs/language/levels.md`、`docs/syntax.md`）写「30 字永久冻结」，
   而 `docs/language/l0-core.md` 实列 44 字。代码里已**没有**第二份字表（旧的
   `KEYWORDS_L0_CORE` frozenset 于 2026-08-20 因"零消费者 + 第二事实源"删除）。
   本版**没有改动这个数字**，只在设计文档风险清单 R1 登记漂移，待专单收口。
2. **标准库模块数**：对外文档长期写「109 个」，本版实测 `stdlib/*.light` 为 **119 个**。
   本文用实测值 119，并已把 `docs/stdlib.md` 的表述改为「119 个模块 + 速查表只收录常用部分」
   （该页表格本身尚未补齐全部模块，属文档待办，不影响可用性）。

未引用任何联网推测；如与仓内最新 `git log` / `reports/` 基线不一致，以仓内数据为准。

---

> **最后一句**：一门语言的成长，不是把流行概念一个个塞进关键字池，
> 而是让**内核足够小、表达足够活**——小到可以永久冻结，活到容得下每个人自己的说法。
