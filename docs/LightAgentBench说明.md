# Light Agent Benchmark 说明（可离线判定的 AI 编程能力任务集）

> 位置：`benchmarks/light_agent/`　｜　测试：`tests/test_light_agent_bench.py`
>
> 一句话：给同一个 Agent 同一句 prompt，看它**一次能不能写对**。
> 本目录只提供**判定骨架**，不接任何真实模型。

## 1. 为什么要有它

「光明语言对 AI 好不好写」过去全靠体感：谁改了一个关键字，谁也说不清是变好写了还是变难写了。
改成可测只需要三件确定的东西：

| 指标 | 定义 | 现在从哪来 |
|---|---|---|
| 一次通过率 | 第一次尝试就通过的任务占比 | `summary.pass_rate` |
| 平均 retry | 每条任务「失败了几次才通过」（一次通过记 0） | `summary.avg_retries` |
| 错误码分布 | 每次**失败尝试**命中的诊断码计数 | `summary.error_codes` |

有了这三项，「把 `读取` 和 `读取文件` 归一」这类改动就能拿数字说话，而不是拿感觉说话。

**不做什么**（红线，和任务卡一致）：

- 不接真实模型 API，不引入网络依赖。模型接入是后续卡的事。
- 不用 LLM 打分、不用模糊匹配、不用「看起来差不多」——判据只有返回码和文件内容断言。
- 不动 `benchmarks/` 下已有的 9 个性能类脚本（编译/运行时/热区/内存），它们是另一条线。
- 不把 `tests/` 里既有用例挪进来：这里放的是「给 Agent 的题目」，不是仓的单元测试。

## 2. 目录

```
benchmarks/light_agent/
├── tasks.jsonl                    # 120 条任务，一行一条
├── fixtures/                      # 修改/修复/重构类任务的起始件（坏的、旧的、啰嗦的）
├── stub_answers/<任务 id>/attempt-N/   # 记录好的补丁文件（整文件快照）
└── run_benchmarks_agent.py        # 判定器：铺补丁 → 跑命令 → 断言 → 出 JSON
```

`--model stub` 把 `stub_answers/` 当成「Agent 的产物」重放：第 N 次尝试用 `attempt-N/`
里的文件铺进临时工作区，跑判定；不通过就换下一次尝试，直到通过或用完。
这样 CI 能**离线验证 harness 本身**：断言写错了、fixture 坏了，测试立刻红。

`fixtures/` 里除 `.light` 之外还可能有**数据起始件**（例如 LA-006 要读的 `数据.txt`）。
仓根 `.gitignore` 有一条全局 `*.txt`（那是给门禁基线留的），会把这类的起始件也一起吃掉：
T-0381 首版提交就漏了 `fixtures/数据.txt`，本地因为文件还在磁盘上所以测试照常绿，一合入/换机就
`LA_E_FIXTURE`。本目录的 `.gitignore` 用 `!fixtures/*.txt` 把起始件捞回来，提交前仍请用
`git status --ignored` 确认没有 `!!` 残留；`tests/test_light_agent_bench.py` 也会断言
`setup.from` 指向的起始件**确实被 git 跟踪**。

## 3. `tasks.jsonl` 字段

```json
{"id":"LA-001",
 "prompt":"在 问候.light 里写一个小程序：用「当」循环把「你好，光明」打印三次，每次一行。",
 "entry":"问候.light",
 "paths":["问候.light"],
 "expected":{"kind":"可运行","cmd":"light run {entry} --stdlib-dir {stdlib}",
             "files":[{"path":"问候.light","contains":["当 ","打印"]}],
             "stdout_count":{"你好，光明":3}},
 "difficulty":"L1",
 "category":"新建",
 "setup":[],
 "stub":{"attempts":[{"files":{"问候.light":"stub_answers/LA-001/attempt-1/问候.light"}}]}}
```

| 字段 | 含义 |
|---|---|
| `id` | `LA-NNN`，唯一；错误码/报告按它定位 |
| `prompt` | 给 Agent 的中文需求（不含答案；别把要改的每一行都写出来） |
| `entry` | Agent 要交付/要改的那个文件（相对工作区） |
| `paths` | 允许触碰的文件集合，`entry` 必须在里面 |
| `expected.kind` | `可运行` / `可编译` / `可检查`，决定主命令是什么 |
| `expected.cmd` | 主判定命令；以 `light` 开头会被翻成 `python -m cli.light` |
| `expected.post_cmd` | 可选，主命令通过后再跑（如 `可编译` 跑生成的 `.py`、`可检查` 跑一遍行为） |
| `expected.files` | 文件断言列表：`path` + `contains` / `not_contains` / `equals` |
| `expected.rc` | 期望返回码，默认 0 |
| `expected.stdout_*` | `stdout_contains` / `stdout_not_contains` / `stdout_count` / `stdout_equals` |
| `difficulty` | `L1` / `L2` / `L3`（单文件小脚本 → 多概念 → 归一/重构） |
| `category` | `新建` / `修改` / `修复` / `重构`（题目形态，与 `error_class` 正交） |
| `error_class` | `新建` / `pyism` / `alias` / `stdlib`（**Agent 为什么会错**，口径见 §3.1） |
| `setup` | 起始件：`{"from":"fixtures/x.light","to":"x.light"}` |
| `stub.attempts[]` | 记录好的补丁：`{"files":{"工作区路径":"stub_answers/…"}}`，第 1 条是第一次尝试 |

命令模板里的占位符都是**整 token**替换，路径带空格也不会被拆开：

- `{entry}` 交付文件；`{stdlib}` 仓里的 `stdlib/`；`{out}` `<entry 去后缀>.py`；`{workspace}` 工作区。

起始配额（2026-11 基线）：新建 6 / 修改 5 / 修复 5 / 重构 4 = 20 条。
T-0462 扩到 120 条后，category 不再按固定比例卡（现为 新建 99 / 修改 10 / 重构 6 / 修复 5），
真正卡配额的是 §3.1 的四类 `error_class` 与 L1/L2/L3 难度——它们才是「能力维度」。
新增任务按比例扩，别把某一类塞爆——四类考的是不同能力（从零写、读别人的代码、定位错误、消除冗长）。

### 3.1 `error_class` 四类判据口径

`category` 说的是**题目长什么样**（要新建还是要修），`error_class` 说的是**Agent 会栽在哪**。
两个维度正交：同一道「新建」题，可以考 Python 惯性，也可以考 stdlib 名字。

| error_class | 含义 | 判据（写题与打标时按这条对） | 题量下限 |
|---|---|---|---|
| `新建` | 从零写一个能跑的程序 | 题面只给需求、不给骨架；`expected.files` 只断言正确产物里必然出现的结构片段 | ≥40 |
| `pyism` | 题面诱导 Python 惯性 | prompt 里出现 Python 词汇（写个函数 / for 循环 / range / len / sum / str / % / // / sorted / def），产物必须换成光明写法，并在 `not_contains` 里禁掉这些 Python 记号 | ≥30 |
| `alias` | 同一语义的别名 / 双字体诱惑 | 题面用别名词（遍历 … 从 … 到 / 输出 / 若…则 / 重复 N 次 / 直到 / == / and）或全角符号；产物要落到光明关键字，`not_contains` 禁别名与全角符号 | ≥20 |
| `stdlib` | 必须用对 stdlib 函数名 | 题干只描述「读文件 / 写文件 / JSON / 切分 / 排序 / 求极值」，不点函数名；`contains` 断言正确的调用名（读取文件、写入文件、转整数、解析JSON、排序列表……） | ≥30 |

难度配额（2026-11 基线）：`L1` ≥60 / `L2` ≥40 / `L3` ≥20。
重试卡要求：至少 30 条卡带 `attempt-2`（第一次错、第二次对），用来验证 harness 真能区分
「一次通过」与「重试通过」；错误码分布才不会退化成一条直线。


## 4. 判据为什么必须是确定的

一条任务的判定只做三件事：

1. 跑 `expected.cmd`（可选再跑 `post_cmd`），**返回码必须等于 `expected.rc`**；
2. 对 `expected.files` 里的每个文件做**精确子串/全文断言**（`contains` 是字面包含，不是正则、不是相似度）；
3. 对标准输出做精确断言（`stdout_equals` 逐字符比较，`stdout_count` 数出现次数）。

失败时给一个**确定性**错误码：

- 优先用语言自己的诊断码：`light ai check --json` 的 `diagnostics[].code`；拿不到就在 stdout/stderr 里找 `L\d{4}`；
- 都拿不到才落骨架码：`LA_E_RC_<rc>` / `LA_E_TIMEOUT` / `LA_E_FILE_CONTAINS` / `LA_E_STDOUT` / …

> 当前 `L0000` 是占位码（`src/diagnostics/` 码表由 B 线落地）。**这不是缺陷**：骨架只认「码的形状」，
> 等 `L1xxx–L5xxx` 注册表合入，同一套判据会自动开始产出细粒度分布，不需要改 benchmark。

**为什么不用 LLM 打分**：

- 不可复现：同一份产物两次打分可能不同，回归就失去意义；
- 不可定位：分数掉了 5 分，说不出是哪条任务、哪个阶段、哪个错误码；
- 会漂移：打分模型一升级，历史基线全部作废；
- 成本与依赖：为一条本来就确定的断言引入网络和凭据，违背本卡的离线要求。

一句话：能用 `rc` 和字符串断言说清的事，不要交给模型去「感觉」。

## 5. `--model stub` 与「未接线」

```bash
python benchmarks/light_agent/run_benchmarks_agent.py --model stub                 # 人读
python benchmarks/light_agent/run_benchmarks_agent.py --model stub --json          # 机读
python benchmarks/light_agent/run_benchmarks_agent.py --model stub --task LA-006   # 单条
python benchmarks/light_agent/run_benchmarks_agent.py --list                       # 只列题
```

`--jobs N` 并行判定（默认 `min(4, CPU 数)`，任务间无共享状态，`threading` 之外没有别的并发假设）；
`--workspace DIR` 指定临时工作区根，`--keep` 保留工作区便于排查失败。

`--model <其它名字>` 现在**明确报错退出（rc=2）**，并提示「未接线」。这是故意的：
宁可当场红，也不要假装跑出一个通过率。

`--json` 输出：

```json
{"bench":"light_agent","model":"stub","repo":"…",
 "tasks":[{"id":"LA-002","ok":true,"stage":"ok","error_code":"LA_E_STDOUT",
           "error_class":"新建","retries":1,"elapsed":8.02,
           "attempts":[{"n":1,"ok":false,"stage":"assert","error_code":"LA_E_STDOUT"},
                       {"n":2,"ok":true,"stage":"ok","error_code":""}]}],
 "summary":{"total":120,"passed":120,"failed":0,"pass_rate":1.0,
            "retries_total":30,"avg_retries":0.25,
            "error_codes":{"L0000":9,"LA_E_FILE_CONTAINS":12,"LA_E_STDOUT":9},
            "by_error_class":{"新建":{"total":40,"passed":40,"failed":0,"pass_rate":1.0},
                              "pyism":{…},"alias":{…},"stdlib":{…}}}}
```

口径细节：

- `retries` = 通过之前失败了几次（一次通过 = 0）；全部尝试都失败时 = 尝试总数。
- `error_code` = **最后一次失败阶段**的码（一次通过则为空串）——它才是这次 retry 的成因。
- `error_class` = 该卡的四类打标；`summary.by_error_class` 按它分组给 `pass_rate`，
  「修 `读取` 有没有用」就看这一组的数字，而不是看总分。
- `summary.error_codes` 按**尝试**统计：重试前的失败也算一次真实报错，这才是「错误码分布」。
- `stage`：`ok` / `setup` / `command` / `assert`。`setup` 说明是 benchmark 自己的问题（找不到 fixture），不是语言的问题。

## 6. 怎么加一条任务

1. **写题**：在 `tasks.jsonl` 末尾加一行，`id` 顺延，`prompt` 用人话描述需求（不泄露答案），
   `error_class` 按 §3.1 的口径打标（不是按 category 抄）。
2. **备起始件**：`新建` 不用；其余把「坏/旧/啰嗦」的 `.light` 放进 `fixtures/`，在 `setup` 里铺到工作区。
   需要非 `.light` 的输入数据（如 `数据.txt`）也放 `fixtures/`——注意仓根 `*.txt` 忽略规则，见 §2 的说明。
3. **备补丁**：把「正确产物」整文件写进 `stub_answers/<id>/attempt-1/`。
   想模拟「第一次写错、第二次才对」，就再放 `attempt-2/`——`retries` 会自然变成 1。
4. **写断言**：能断言行为就断言行为（`stdout_equals`），再补一条结构断言（`contains`/`not_contains`）防止「碰巧输出对」。
   `pyism` / `alias` 两类必须带 `not_contains`（禁 Python 记号 / 别名与全角符号），否则打标就成了空话。
5. **自检**：`--task <新 id> --json` 必须 `ok=true`；再把补丁故意改坏一次，确认能判失败。
6. **全量**：`--model stub --json` 必须 `failed=0`，并核对 `summary.by_error_class` 四组都在。

## 7. 跑法（平台差异）

POSIX（0.88 / FreeBSD、Linux）：

```bash
PYTHONPATH=src python3 -m pytest -q -o addopts= tests/test_light_agent_bench.py
PYTHONPATH=src python3 benchmarks/light_agent/run_benchmarks_agent.py --model stub --json
```

Windows（PowerShell；`VAR=x cmd` 这种写法不可用，用 `$env:`）：

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q -o addopts= tests/test_light_agent_bench.py
python benchmarks\light_agent\run_benchmarks_agent.py --model stub --json
```

判定器自己会给子进程补 `PYTHONPATH`（仓根 + `src`）和 `PYTHONUTF8=1`，所以从任意目录调用都不会因为
找不到 `cli` / `src` 或中文乱码而假失败。单条命令默认超时 30s（`--timeout` 可调）。

> 注意：跑本模块**要指定文件**（`tests/test_light_agent_bench.py`），别用 `-k light_agent_bench` 扫全仓。
> `tests/dogfood/conftest.py` 的 `pytest_collection_modifyitems` 是 session 级 hook：当 `lightharness`
> 不在位时，它会给**整场所有用例**打 skip（远端 CI 常见）。那种 skip 是「跳过」不是「通过」，
> 别当成绿。


## 8. 维护约定

- 改判据只改 `expected`，不要改「任务本身」的 prompt；prompt 变了基线就不可比。
- 补丁是**整文件快照**，不是行级 diff：不依赖 `git apply` / `patch`，Windows 和 FreeBSD 行为一致。
  改一处就重写整个文件，别指望「打个 hunk」。
- 新增/删除任务必须同步改 `tests/test_light_agent_bench.py` 里的配额断言
  （≥120 条、四类 error_class 下限、L1/L2/L3 下限、重试卡 ≥30）。
- 新增起始件后提交前跑一次 `git status --ignored -- benchmarks/light_agent`：出现 `!!` 就是被忽略规则
  吃掉了（仓根 `*.txt`／`*.json` 都会命中）。要么 `git add -f`，要么在本目录 `.gitignore` 里加负向规则。
- 报告里的「新增红」只认 `--model stub` 的 `failed` 条数；`LA_E_*` 是骨架故障，`L####` 是语言问题，分开看。
