# Light 生态最小可用面（MVP Surface）

> 结论先行：生态冷启动不看「有多少」（109 个 stdlib 模块、711 项原生能力），
> 只看**一个真实项目用到的 20% 是否打磨到无摩擦**。本文把这 20% 收敛成 5 个方向，
> 每个方向配一个 `git clone` 后就能直接跑的完整示例，并由
> `tests/scenarios/test_mvp_surface.py` 真跑兜底。
>
> 最近验证：2026-11-10 · macOS 12.7.6 / Python 3.12.9 · 后端 `src`（`light run` 默认）
> 验证命令：`python -m pytest -q tests/scenarios/`

## 判定口径

| 状态 | 含义 |
| --- | --- |
| 稳定 | 示例里真跑通过，退出码 0，输出有明确标记；可直接写进真实项目 |
| 实验 | 能跑通但存在语义/跨后端/跨平台注意事项，真实项目需自行兜底 |
| 缺失 | 当前跑不通，示例不得使用；已记录现象与替代路线 |

## 五方向总表

| 方向 | 状态 | 示例 | 一句话结论 |
| --- | --- | --- | --- |
| 文件读写 | 稳定 | [01_file_io.light](../examples/mvp/01_file_io.light) | 写、读、逐行统计、临时目录清理全通 |
| 网络请求 + JSON | 稳定 | [02_http_json.light](../examples/mvp/02_http_json.light) | 本机 HTTP → JSON → 取字段全通，但取函数必须用 `从 … 导入` |
| 进程管理 | 稳定 | [03_process.light](../examples/mvp/03_process.light) | 子进程 stdout/stderr/非零退出码全通 |
| 测试框架 | 稳定 | [04_test_framework.light](../examples/mvp/04_test_framework.light) | `断言工具` + `尝试/捕获` 可用，预期失败可演示 |
| 包与模块引用 | 稳定（导入）<br>缺失（`pkg run`） | [05_pkg_module.light](../examples/mvp/05_pkg_module.light) | `从 模块 导入` 可用；`light pkg run` 跨模块失败 |

---

## 1. 文件读写

示例：[examples/mvp/01_file_io.light](../examples/mvp/01_file_io.light)
运行：`python -m cli.light run examples/mvp/01_file_io.light`

| 能力 | 状态 | 入口 API（真实函数名） | 已知坑 | 示例路径 | 最近验证 |
| --- | --- | --- | --- | --- | --- |
| 写文本文件 | 稳定 | `文件系统.写入文件(路径, 内容)` | 只验证 UTF-8 文本；二进制能力未进入 MVP 面 | `examples/mvp/01_file_io.light` | 2026-11-10 |
| 读文本文件 | 稳定 | `文件系统.读取文件(路径)` | 返回整串，不自动去尾部换行 | `examples/mvp/01_file_io.light` | 2026-11-10 |
| 逐行读取 | 稳定 | `文件系统.文件行列表(路径)` | **必须写全限定名**：`导入 文件系统。` 后直接写 `文件行列表(...)` 会「名称未定义」；行尾换行会保留 | `examples/mvp/01_file_io.light` | 2026-11-10 |
| 存在性判断 | 稳定 | `文件系统.文件存在(路径)` | 只判断文件，不判断目录（目录用 `目录存在`） | `examples/mvp/01_file_io.light` | 2026-11-10 |
| 文件大小 | 稳定 | `文件系统.文件大小(路径)` | 返回字节数，不是字符数；UTF-8 中文会大于 `字符串长度` | `examples/mvp/01_file_io.light` | 2026-11-10 |
| 删除文件 | 稳定 | `文件系统.删除文件(路径)` | 文件不存在时行为未在示例中覆盖 | `examples/mvp/01_file_io.light` | 2026-11-10 |
| 临时目录 | 稳定 | `临时文件.创建临时目录()` + `文件系统.删除目录(目录)` | 删除目录要求目录为空，先删文件；不写用户目录，测试结束后清理 | `examples/mvp/01_file_io.light` | 2026-11-10 |
| 路径拼接 | 稳定 | `文件系统.路径连接(目录, 文件名)` | 示例只用两段拼接 | `examples/mvp/01_file_io.light` | 2026-11-10 |

## 2. 网络请求 + JSON

示例：[examples/mvp/02_http_json.light](../examples/mvp/02_http_json.light)
运行：`python -m cli.light run examples/mvp/02_http_json.light -- http://127.0.0.1:8765/mvp`

| 能力 | 状态 | 入口 API（真实函数名） | 已知坑 | 示例路径 | 最近验证 |
| --- | --- | --- | --- | --- | --- |
| HTTP GET | 稳定 | `从 网络请求 导入 获取` → `获取(url)` | **模块点访问不可用**：`导入 网络请求。` 后写 `网络请求.获取(url)` 会报 `'module' object is not subscriptable`；必须 `从 网络请求 导入 获取` | `examples/mvp/02_http_json.light` | 2026-11-10 |
| 状态码 | 稳定 | `响应.状态码` | 是属性不是方法，不要加括号 | `examples/mvp/02_http_json.light` | 2026-11-10 |
| 响应文本 | 稳定 | `响应.文本()` | 是方法，必须加括号；编码按响应头/UTF-8 | `examples/mvp/02_http_json.light` | 2026-11-10 |
| 成功判断 | 稳定 | `响应.成功()` | 没有 `响应.是否成功` 属性，写错会「属性错误」 | `examples/mvp/02_http_json.light` | 2026-11-10 |
| JSON 解析 | 稳定 | `JSON.解析JSON(文本)` | 也支持裸 `解析JSON(...)`；非 JSON 文本的报错未进入示例 | `examples/mvp/02_http_json.light` | 2026-11-10 |
| 本机服务联调 | 稳定 | 测试内 `http.server` 随机端口 | 示例只访问 `127.0.0.1`，不依赖外网；HTTPS/公网未验证 | `tests/scenarios/test_mvp_surface.py` | 2026-11-10 |
| 请求头 / POST / 超时 | 实验 | `获取(url, 头部, 超时)`、`发送(...)` | 未进入 MVP 示例，参数顺序以 `stdlib/网络请求.py` 为准 | — | 2026-11-10 |

## 3. 进程管理

示例：[examples/mvp/03_process.light](../examples/mvp/03_process.light)
运行：`python -m cli.light run examples/mvp/03_process.light`

| 能力 | 状态 | 入口 API（真实函数名） | 已知坑 | 示例路径 | 最近验证 |
| --- | --- | --- | --- | --- | --- |
| 运行并等待子进程 | 稳定 | `进程.进程运行(命令列表, 输入, 超时, 工作目录, 环境变量)` | 命令必须是**列表**，不是 shell 字符串；不走 shell，天然避开 `head/grep/awk/!` 这类 POSIX 写法 | `examples/mvp/03_process.light` | 2026-11-10 |
| 退出码 | 稳定 | `结果["返回码"]` | 非零退出不抛异常，正常返回；要自己判 0 | `examples/mvp/03_process.light` | 2026-11-10 |
| stdout | 稳定 | `结果["标准输出"]` | 原样带回尾部换行，展示前建议 `去除空白` | `examples/mvp/03_process.light` | 2026-11-10 |
| stderr | 稳定 | `结果["标准错误"]` | 与 stdout 分开；失败路径要同时看两个字段 | `examples/mvp/03_process.light` | 2026-11-10 |
| 跨平台可执行文件 | 稳定（Python 后端） | `sys.executable` | `light run` 的 Python 后端里 `sys` 是真 Python sys；原生后端 `stdlib/sys.light` 不提供 `executable`，示例跨后端会失效 | `examples/mvp/03_process.light` | 2026-11-10 |
| 管道会话 / 后台进程 | 实验 | `进程会话启动`、`后台执行` | 未进入 MVP 示例；`外部命令.light` 只有导出声明，实现腿待确认 | — | 2026-11-10 |

## 4. 测试框架

示例：[examples/mvp/04_test_framework.light](../examples/mvp/04_test_framework.light)
运行：`python -m cli.light run examples/mvp/04_test_framework.light`
或：`python -m cli.light test examples/mvp/04_test_framework.light`

| 能力 | 状态 | 入口 API（真实函数名） | 已知坑 | 示例路径 | 最近验证 |
| --- | --- | --- | --- | --- | --- |
| 相等断言 | 稳定 | `断言工具.断言相等(实际值, 期望值, 消息)` | 失败抛 `断言失败异常`，不是返回布尔 | `examples/mvp/04_test_framework.light` | 2026-11-10 |
| 真值断言 | 稳定 | `断言工具.断言为真(条件, 消息)` | 同左 | `examples/mvp/04_test_framework.light` | 2026-11-10 |
| 子串断言 | 稳定 | `断言工具.断言包含子串(文本, 子串, 消息)` | 同左 | `examples/mvp/04_test_framework.light` | 2026-11-10 |
| 预期失败演示 | 稳定 | `尝试:` / `捕获 e:` | 必须自己捕获；未捕获会让整文件失败——这正是 `light test` 的判据 | `examples/mvp/04_test_framework.light` | 2026-11-10 |
| 文件级测试入口 | 稳定 | `light test <文件.light>` | 只按**文件**判通过/失败（无异常=通过），没有函数级用例发现与逐条报告 | `examples/mvp/04_test_framework.light` | 2026-11-10 |
| xfail / skip | 缺失 | — | 语言测试运行器无 xfail/skip 语义；pytest 侧的 `pytest.xfail(strict=True)` 只能包在 Python 场景测试里 | `tests/scenarios/test_mvp_surface.py` | 2026-11-10 |
| 自动发现 | 实验 | `light test`（不带文件） | 会递归执行 `tests/` 下所有 `.light`，包括辅助模块；辅助文件不要用 `.light` 放在 `tests/` | — | 2026-11-10 |

## 5. 包与模块引用

示例：[examples/mvp/05_pkg_module.light](../examples/mvp/05_pkg_module.light)
被引用模块：[examples/mvp/统计工具.light](../examples/mvp/统计工具.light)
运行：`python -m cli.light run examples/mvp/05_pkg_module.light`

| 能力 | 状态 | 入口 API（真实函数名） | 已知坑 | 示例路径 | 最近验证 |
| --- | --- | --- | --- | --- | --- |
| 同目录模块导入 | 稳定 | `从 统计工具 导入 求和, 平均值, 最大值` | 模块文件需与被运行入口同目录；导出名要与 `导出` 列表一致 | `examples/mvp/05_pkg_module.light` | 2026-11-10 |
| 子目录模块导入 | 稳定 | `从 工具包.统计 导入 求和` | 目录不需要 `__init__.light`；点号路径映射到 `<目录>/<模块>.light` | 已用最小工程验证 | 2026-11-10 |
| 模块导出 | 稳定 | `导出 求和, 平均值, 最大值。` | 不写 `导出` 的名字不会跨模块可见 | `examples/mvp/统计工具.light` | 2026-11-10 |
| `light pkg run` 跨模块 | 缺失 | `light pkg --project <目录> run` | 生成代码执行时报 `No module named '<模块>'`（退出码 3）；且会把整份生成 Python 打到 stdout，难以做脚本化判据 | 最小 `package.toml` 工程复现 | 2026-11-10 |
| `package.toml` 入口 | 实验 | `[package] entry = "主.light"` | 单文件入口可被 `pkg run` 找到；一旦入口 `从 … 导入` 就落入上面的缺失项 | 最小 `package.toml` 工程 | 2026-11-10 |

---

## 真实场景输出（2026-11-10）

`python scripts/run_scenarios.py` 的实际输出：

| 场景 | 结果 | 耗时(ms) |
| --- | --- | ---: |
| 文件读写 | 通过 | 12559.4 |
| 网络请求+JSON | 通过 | 6815.7 |
| 进程管理 | 通过 | 5837.3 |
| 测试框架 | 通过 | 5083.3 |
| 包与模块引用 | 通过 | 6009.6 |

耗时主要是每次 `light run` 的 CLI 冷启动（约 5~12 秒），不是示例逻辑本身。

## 跨平台与判据

- 五个示例只用语言自带能力（文件、网络、进程、断言、模块），**不调用 shell**，
  因此不含 `head/grep/awk`、`!`、`$()` 这类 Windows 不可用写法。
- 进程示例统一用 `sys.executable` 起 Python 子进程，避免依赖 `python`/`python3` 名字差异。
- 若某台机器上 POSIX 判据本身不可用，会出现**判据 exit 255 的假失败**；
  这不是产物坏了。按任务约定可换 FreeBSD 15.1 机器复跑：
  `ssh workbuddy@192.168.0.88`（密码取 `.env` 的 `SSH_PASS_WORKBUDDY`，注意尾部空格需 strip）。

## 发现但不在本卡修的坑（建议另开卡）

1. **`网络请求` 模块点访问失效**：`导入 网络请求。` + `网络请求.获取(...)` 报
   `'module' object is not subscriptable`。替代路线是 `从 网络请求 导入 获取`。
   建议修 codegen 的模块成员访问，别让新人第一步就踩。
2. **`light pkg run` 不把项目目录加入模块搜索路径**：入口一旦 `从 … 导入` 就
   `No module named`；同时它把生成 Python 全量打印到 stdout，建议默认静默、`-v` 再打。
3. **`导入 文件系统。` 的导出绑定不一致**：`读取文件/写入文件/文件存在/文件大小`
   可裸用，`文件行列表` 必须写全限定名。建议统一为「导入即全部绑定」。
4. **`外部命令.light` 只有导出声明没有实现体**，真实行为取决于同名 `.py` 或内置，
   新人容易误判为纯光明实现。建议在模块头明确标注实现腿。

以上均未修改 `stdlib/` 实现；本卡只记录现象与可用替代路线。
