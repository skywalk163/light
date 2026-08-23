# 任务 C｜SSE 流式解析 + LLM 客户端 + JSON Schema 校验（全部用光明写）

> **任务编号**：C　**优先级**：P1（M1 里程碑的全部内容）　**依赖**：弱依赖任务 A 的异步启动入口——**可以先写同步生成器版，不必等 A**
> **仓库**：`g:\dswork\duan-light-merge\light-merge`，主分支 `main`
> **⚠️ 开工前必读 `任务书/协作规程.md`**——四路 agent 同机并行，你必须在自己的 git worktree（`../wt-C`，分支 `task-C`）里作业，且**不许跑全量测试**。你的 fake server 端口段是 **19200–19299**。规程优先于本文任何冲突表述。
> **背景**：我们要用「光明（Light）」这门中文编程语言复刻一个 agent 框架。第一个真实里程碑是「向 DeepSeek 发一次流式 chat 请求，逐 token 打印」。光明目前**没有任何 SSE 解析能力**，JSON Schema 校验只是个四关键字玩具。你来补这两块——**并且必须用光明语言本身写**。

---

## 0. 本任务最重要的一条约束：必须用 `.light` 写，不许留 `.py` 影子

光明的标准库现在有一个尴尬事实：**运行期真正由光明代码提供的模块数是 0/134 = 0%**。

- `stdlib/` 下 56 个 `.light` 文件里，55 个只是导出清单，没有一行可执行光明代码。见 `stdlib/文件系统.light:1-7` 自述："本模块实现见同名 .py 文件，本 .duan 仅作导出清单。"
- 唯一有真实现的 `stdlib/列表工具.light`（129 行，自称"既是可用的工具库，也是「段言能自举写库」的示例"）**已经被后来添加的 `stdlib/列表工具.py` 完全遮蔽**。
- 遮蔽原因在导入钩子 `stdlib/_light_import_hook.py:140-142`：
  ```python
  # 同名 .py 存在 => 源文件只是清单，让标准机制加载 .py
  if os.path.isfile(os.path.join(base, fullname + '.py')):
      return None
  ```
  `.py` **绝对优先**。全仓 `PURE_LIGHT_ONLY = 0`，也就是说这个钩子的 `.light` 加载分支在 stdlib 范围内是**死代码**。

**所以：你写的每个新模块只能有 `.light`，绝对不许建同名 `.py`。** 这不是代码风格洁癖——这是"这门语言到底能不能写自己的库"的唯一检验，也是你这个任务对整个项目最大的价值。你会是第一个真正激活那条 `.light` 加载路径的人。

**同理，不许用 `引 Python` 绕过语言缺陷。** 绕不过就登记为语言缺陷交回主线（任务 A 负责修）。掩盖缺陷等于把整个项目的意义废掉。

---

## 1. 你可以依赖的语言能力（已实测确认可用）

避免你在不确定中试错，这些是核实过能用的：

- **生成器**：`生成 X。` → `yield X`；裸 `生成。` → `yield`；`遍历 项 之 生成器()` 正常。端到端跑通
- **异常**：try/catch/finally/else、多 catch 子句、`捕获 类型 as 变量`、自定义异常继承链、裸 `抛出`（重抛）、`抛出 X 从 Y`。全部实测通过（注意 `docs/known_issues.md:27` 说不支持 `as 变量` —— **那份文档过期了**）
- **类**：继承、多继承（**只能写 `继承 甲, 乙`，不能写 `类 甲(乙, 丙)：`**）、`己`/`父`、构造、接口/协议→ABC、`@静态方法/@类方法/@特性/@抽象`、私有名改写、迭代器协议 `__迭代__`/`__下一项__`/`迭代停止`
- **闭包与高阶函数**：端到端跑通，lambda 写作 `接收 甲：返回 甲 乘 甲`，可多参，可作实参，可放进字典
- **字节与字符串**：`b"..."` 字面量、`.编码("utf-8")`/`.解码("utf-8")`、f-string 插值含表达式
- **数据结构**：`[1,2,3]` 列表、**`["键": 值]` 方括号就是字典**、`(1,2)` 元组、`{1,2}` 集合、解构 `设（甲，乙）为 (1,2)。`、列表/字典/集合推导式、切片 `列[0:2]`
- **装饰器**（含链式与带参）、**上下文管理器** `使用 X 为 v：`（多上下文 `使用 A 为 甲, B 为 乙：` 也行）
- **定义侧可变参数** `段落 处理 接收 *其余, **关键：`（**注意：括号形式 `段落 处理(*其余)` 不支持**）
- **模块**：`导入 X。`、`从 X 导入 Y。`、`导出 X。`

## 2. 你会踩到的坑（已知，绕开或上报）

| 坑 | 现象 | 怎么办 |
|----|------|--------|
| **`yield from` 静默错编** | `生成 从 乙()。` → `yield 从` + `乙()`（两条语句）；`生成 全部 乙()。` → `yield all(乙)()`。编译期零提示 | **任务 A 正在修**。你先手写 `遍历 项 之 内层(): 生成 项。` 代替，并在代码里留 `# 待 A 修复 yield from 后简化` |
| **`映射`/`筛选` 参数序反了** | `映射([1,2], 函数)` → `map([1,2], lambda)` → `TypeError` | **任务 A 正在修**。你改用推导式 `[函数(项) 遍历 项 之 列]`，别用这两个动词 |
| **调用侧关键字实参不支持** | `打印(甲 = 1)` → `意外的标记: 「=」` | **任务 A 正在修**。你先用位置参数，并把"需要 kwargs 的 API"列进移交清单 |
| **无 `global`/`nonlocal`** | 函数内 `设 计 为 计 加上 1` → `UnboundLocalError` | 用类属性或可变容器兜。这也是为什么建议把解析器写成**类**而不是一堆自由函数 |
| **顶层异步无启动入口** | 顶层 `等待 主()。` → `SyntaxError: 'await' outside function` | **任务 A 正在修**。所以你**先写同步生成器版**（`生成` 逐帧产出），异步入口就绪后再加异步变体 |
| **类属性默认值只认 `等于`** | `属性 计数 为 0。` 报错，必须写 `属性 计数 等于 0。` | 照 `等于` 写。A6 在修 |
| **推导式介词** | 只认 `之`/`在`，不认 `于` | 用 `之` |
| **循环依赖被硬拒绝** | `src/module_resolver.py` 抛 `CircularDependencyError` | 模块依赖图必须是 DAG。按 `SSE → 流式 → 大模型客户端` 单向分层设计 |

---

## 3. 任务分解

### C1 SSE 帧解析器 → `stdlib/SSE.light`（新建）

**为什么从零写**：全仓 stdlib/contrib 内 `event-stream | EventSource | SSE | chunked` **零命中**。`stdlib/lightpub/HTTP客户端.py:110-114` 只有一个 `iter_content` 转发，**连 `iter_lines` 都没有**。顶层 `stdlib/HTTP.py` 的 14 个函数全基于 urllib 且**无 stream 参数**。

**要实现的**（按 W3C Server-Sent Events 规范）
- 字节流 → 行切分：正确处理 `\n` / `\r\n` / `\r` 三种行尾，且**必须能处理跨 chunk 断行**（一个字段被切成两半是常态）
- 行 → 字段：`data:` / `event:` / `id:` / `retry:` / 注释行（以 `:` 开头）/ 未知字段忽略
- 字段值前导单空格要剥掉（`data: x` 的值是 `x` 不是 ` x`）
- 空行 = 帧边界 → 产出一个事件；多个 `data:` 行用 `\n` 拼接
- 增量式接口：`喂入(字节块)` + `生成` 逐个吐出完整事件。**这是关键设计点**——不许要求调用方先把整个响应读完
- UTF-8 多字节字符跨 chunk 边界被切断的情况要正确处理（**不许 `.解码()` 直接炸**）

**测试**：`tests/test_sse_light.py`（新建）。必须覆盖：正常多帧、跨 chunk 断行、跨 chunk 断 UTF-8、只有注释、`data` 多行、空 `data`、`[DONE]` 哨兵、流中途断开（不完整帧不该被当成完整帧吐出）。

---

### C2 流式 HTTP → `stdlib/流式.light`（新建）

**要实现的**
- 流式 GET/POST，逐块产出响应体（`生成` 字节块）
- `按行读取` 生成器（SSE 之下的通用层）
- chunked transfer-encoding 解码（如果底层已经处理就跳过，但要**验证**过而不是假设）
- 超时（连接超时 / 读超时分开）、状态码与响应头访问
- 断连时抛明确的光明异常，不许静默返回空

**底层怎么接**：这里有个现实取舍。原生 socket 是任务 B 在做，还没有。所以：
1. **本阶段允许**通过 `导入` 现有的 `stdlib/网络.py`（socket 薄封装）或 `stdlib/lightpub/HTTP客户端.py`（有 `iter_content`）作为传输层——**注意 `导入 X` 是普通 import，不算 `引 Python` 逃逸**，这是可接受的
2. **但传输层之上的一切（分块、行切分、SSE 分帧、解码）必须是光明代码**。这才是被压力测试的部分
3. 传输层接口要抽成一个薄的**协议/接口**（用 `接口` 关键字），这样任务 B 的原生 socket 就绪后可以直接换实现，上层不动

---

### C3 LLM 客户端 → `stdlib/大模型客户端.light`（新建）

**要实现的**（对齐 OpenAI 兼容的 `/chat/completions`，DeepSeek 走这个协议）
- 非流式 `对话(消息列表, 模型, ...)` 与流式 `流式对话(...)`（`生成` 逐个增量块）
- 增量块组装：把 `choices[0].delta` 的 `content` / `tool_calls` 累积成完整消息。**tool_calls 的增量拼接是最容易写错的地方**——`index` 分组、`function.name` 只在第一个增量里出现、`arguments` 是逐字符流式拼接的 JSON 字符串
- `finish_reason` 处理：`stop` / `length` / `tool_calls`
- `data: [DONE]` 哨兵终止
- 错误响应（4xx/5xx 的 JSON error body）转成光明异常
- API key 从环境变量读，**绝不硬编码，也不许打印出来**
- base_url 可配置（DeepSeek / 本地 vLLM / 其它兼容端点）

**测试**：`tests/test_llm_client_light.py`（新建）。**默认必须离线可跑**——用一个本地 fake server（测试里用 Python 起一个 HTTP server 回放录制好的 SSE 字节流）。真实 API 调用另开一个 `pytest.mark.skipif(无 API key)` 的用例，**不许让 CI 依赖外网或 API key**。

---

### C4 JSON Schema 校验器 → `stdlib/模式校验.light`（新建）

**现状**：`stdlib/JSON.py:777-795` 有个 `JSONSchema验证`，实现在 `:798-829`，**只认 `type` / `properties` / `required` / `items` 四个关键字**，返回裸 `bool` **不产出错误路径**，且 `:794` 一个裸 `except:` 会把实现 bug 一并吞成"校验失败"。全仓无 `jsonschema` 第三方依赖。

**要实现的**（Draft 2020-12 的常用子集，tool 参数校验够用）
- 类型：`type`（含数组形式 `["string","null"]`）、`enum`、`const`
- 数值：`minimum` / `maximum` / `exclusiveMinimum` / `exclusiveMaximum` / `multipleOf`
- 字符串：`minLength` / `maxLength` / `pattern`
- 数组：`items` / `prefixItems` / `minItems` / `maxItems` / `uniqueItems`
- 对象：`properties` / `required` / `additionalProperties` / `propertyNames` / `minProperties` / `maxProperties`
- 组合：`oneOf` / `anyOf` / `allOf` / `not`
- 引用：`$ref` + `$defs`（**至少支持同文档内 `#/$defs/X`**，远程引用不做）
- **返回结构化结果，不是裸 bool**：`{ 通过: 真/假, 错误: [{ 路径: "#/参数/超时", 关键字: "type", 消息: "期望 整数，得到 文本" }] }`。路径用 JSON Pointer。**这是 LLM tool-call 场景的刚需**——校验失败要把可读原因喂回模型让它重试
- **不许用裸 `捕获：`吞异常**。实现 bug 必须炸出来，不能伪装成"校验失败"

**测试**：`tests/test_schema_light.py`（新建）。每个关键字至少一正一负；错误路径要断言到具体 pointer 字符串。

**注意**：`stdlib/JSON.py` 里那个旧的 `JSONSchema验证` **不要删也不要改**（它有现存调用方与测试 `tests/test_stdlib_complete.py:248-253`）。你的是新模块。是否废弃旧的由主线裁定。

---

## 4. 交付要求

1. **只建/改这些文件**：
   - 新建：`stdlib/SSE.light`、`stdlib/流式.light`、`stdlib/大模型客户端.light`、`stdlib/模式校验.light`
   - 新建：`tests/test_sse_light.py`、`tests/test_llm_client_light.py`、`tests/test_schema_light.py`
   - **绝对不许**建 `stdlib/SSE.py`、`stdlib/流式.py`、`stdlib/大模型客户端.py`、`stdlib/模式校验.py` —— 会被 `_light_import_hook.py:140-142` 遮蔽，你的光明代码将永远不被执行
   - **不许动**：`src/` 下任何文件（任务 A/B 的地盘）、`stdlib/JSON.py`、`stdlib/进程*.light`（任务 D 的地盘）
2. **`引 Python` 出现次数必须为 0**。`导入 现有模块` 可以（那是普通 import），`引 Python：<裸 Python 代码>` 不行。
3. **每个模块要有真跑测试**，离线可跑，不依赖外网与 API key。
4. **回归验证：只跑定向测试，不跑全量**（详见 `协作规程.md` §2）。
   - 老协议「`git stash push` 跑两遍全量」**已作废，不要执行**——四个 agent 同机作业时 stash 栈是共享的，会互相摧毁
   - 你要跑的：你新建的 `tests/test_sse_light.py`、`tests/test_llm_client_light.py`、`tests/test_schema_light.py`，加 `tests/test_stdlib_complete.py`
   - **全量回归由主线在独占机器时统一跑**并出「红转绿 / 新增打红」两份名单。别抢这个活
   - **fake server 端口写死在 19200–19299 段**。绑定前先探测可用，占用则报错退出，**不许自动往上加一个端口重试**（会漂到任务 B 的段里）
   - 临时文件一律加 `_taskC_` 前缀，收尾删干净
   - **任务 D 也在 `stdlib/` 下建新文件**（`进程树/事件总线/插件.light`）。文件不重名，但别去碰它们
5. **本机装第三方库导致的转绿不算修好。**
6. **PowerShell**：中文输出落盘再读（直读乱码，乱码只在显示层）；不支持 `&&` 与 heredoc。
7. **安全**：API key 只从环境变量读；日志里不许出现 key 或完整 Authorization 头；写文件时注意不要把请求体明文落盘。

## 5. 移交清单（发现即登记，不要自己绕）

每当你**因为语言缺陷而不得不写出丑陋代码**，就在这里记一条——格式：`光明写不出什么 → 你的临时绕法 → 期望的语言能力`。这份清单是本任务最有价值的产出之一，它直接决定任务 A 下一批修什么。

已知会命中的（帮你开个头）：
- `yield from` 静默错编 → 手写 `遍历…生成` → 期望 `生成 全部 X。`
- 调用侧 kwargs 不支持 → 长位置参数列表 → 期望 `函数(超时 = 30)`
- 顶层异步无入口 → 只能写同步生成器版 → 期望 `运行 异步 主()。`
- 类属性默认值只认 `等于` → 照写 → 期望与 `设…为` 一致
