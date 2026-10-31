# T-0210 光明P1：内置形参名中英混杂，中文关键字参数调不通 [L-256]

## 做了什么

### 1. `stdlib/builtins.py`：形参名全量归一为中文（token 级重命名，不动语义）

190 个顶层函数里，改前 **73 个纯英文形参 / 2 个中英混杂**（`序列化JSON(value, 缩进)`、
`设置文件所有者(路径, uid, gid)`）/ 92 个纯中文。改后 **纯英文 0、混杂 0、纯中文 167**
（余下 23 个无参）。共动 **75 个函数、241 处 token**。

改法不是手敲：用 `ast` 取每个顶层函数的行区间 + `tokenize` 逐 token 换名，显式跳过
三类不该动的东西 —— 属性名（`os.path` 里的 `path`）、关键字实参标签
（`open(encoding=...)` 里的 `encoding`）、字符串/注释里的同名字样。
`git diff --stat` 是 **180 插入 / 180 删除、文件行数 2125 不变**，纯一对一换名，
顶层 `def` 数量 190 不变（`tests/unit/test_R158_地板证据窗口漂移.py` 的地板分母不受影响）。

命名取自三处权威，不自己发明：`stdlib/*.light` 门面的段落签名
（`段落 读取文件(路径)`、`段落 字典获取(映射, 键, 默认值)`）、
`docs/stdlib.md`（`设置环境变量(名称, 值)`）、
以及 `src/enhanced_errors.py` 给用户看的报错示范
（`读取文件(路径, 编码="utf-8")`）。

主要映射：`path→路径`、`encoding→编码`、`content→内容`、`text→文本`、`value→值`、
`separator→分隔符`、`default→默认值`、`substring→子串`、`width→宽度`、
`fillchar→填充字符`、`start/end→起始/结束`、`old/new→旧串/新串`、`count/times→次数`、
`uid/gid→用户ID/组ID`、`a/b→甲/乙`、`n→数`、`d/key→字典/键`、`*paths→*路径们`。

### 2. `scripts/sync_builtins.py`：把「形参名归一」变成可复现的同步步骤

boot 副本有 109 个「自包含保留体」不走逐字同步（模块 docstring 里写明的原因：真源对应
函数是地板转发体，release 环境没有光导入钩子）。所以只改真源 + 跑 sync，boot 那 109 个
函数的英文签名**修不掉**。因此：

- 新增 `PARAM_RENAME`（与真源同一张表）与 `normalize_param_names()`，
  `sync_boot()` 写完 boot 后按同一张表把 boot 全文件的英文形参名改成中文；
  幂等 —— 已是中文的不产生改动（连跑两次 md5 相同，第二次不再打印「形参名归一」）。
- `self_checks()` 新增一条：**真源 / boot / lh 三份副本都不得留英文形参名**，
  留一个就 exit 非 0。这是「防再犯」的机器判据，不靠人记。

### 3. 顺手修掉一处既有红：boot 的 `皆空` 是转发体

`bootstrap/release/stdlib/builtins.py` 里 `皆空` 原本是逐字搬自真源的
`import 内置核心判型` 转发体 —— release 环境没有光导入钩子，运行期必
`ModuleNotFoundError`。这本来就是 `test_boot_no_light_forward_leak` 的既有红
（**基线实证**：主仓 `36d2b5429` 未改动时跑 `tests/unit/test_builtins_drift.py`
是 `1 failed, 7 passed`，红的正是这一条）。

本卡把它补进 `BOOT_PORTED`，按 `stdlib/内置核心判型.light:55-70` 逐条落成自包含实现
（null / `""` / 空 list / 空 dict 为真；纯空白串、`0`、空 bytes 不算空）。
现在该文件 **8 passed**，基线那 1 红清零。这条是「改形参名会动 boot」时的附带收获，
不是本卡的主线；如果不修，本卡的 verify 第 3 条会一直红着，卡根本 land 不了。

### 4. 新增 `tests/unit/test_LH34_中文关键字参数.py`（391 用例）

四组断言：

1. **代表函数中文关键字真调**：`读取文件 / 写入文件 / 分割字符串 / 字典获取 / 原子写入`
   五个，断言返回值（不是「没抛异常」就算过）。`原子写入` 是
   `stdlib/路径护栏.light` 的段落，它的形参本来就是中文，这里钉住别被改回去。
2. **形参名全中文**（参数化到每个公开顶层函数）：失败信息直接列出函数名 + 英文形参名。
3. **中文名可作关键字**：每个公开函数的每个中文形参名都能
   `inspect.signature(...).bind(**{中文名: None})` 成功；并做**反向自证** ——
   把中文名换成 `path`/`text` 必须 `TypeError`，否则这条门禁是空的。
4. **三份副本一致**：boot / LH 副本形参名全中文；LH 与真源逐字相同；
   boot 与真源的差异只允许 `{是数字: (['值'], ['字符'])}` 这一条已知保留体差异
   （boot 的是旧版单字符判型，两者都中文、语义等价，不强行拉平）。

另加 `test_boot副本中文关键字可调` 与 `test_boot副本皆空是自包含实现`，
把「boot 不只是静态改了名、运行期真能中文关键字调」钉住。

**为什么第 3 组用 `bind()` 而不是真调用**：`删除文件` / `退出程序` / `执行命令`
这类函数真调会删文件、退出进程、跑 shell，门禁不能拿它们做实验。`bind()` 成功已经
足以证明「`编码=` 这种写法不会再 `TypeError: unexpected keyword argument`」。
真实调用留给第 1 组和第 5 组（5 个代表 + boot 3 个），都是无破坏性的。

## 验证（全部实跑，不是推演）

| 命令 | 结果 |
| --- | --- |
| `python3 -m pytest -q tests/unit/test_LH34_中文关键字参数.py` | **391 passed** |
| `python3 scripts/sync_builtins.py` | **exit 0**，自检全部通过，连跑两次幂等（md5 相同） |
| `python3 -m pytest -q tests/unit/test_builtins_drift.py` | **8 passed**（基线 `1 failed, 7 passed`，那 1 红被本卡修掉） |

邻接回归（确认换名没打断调用方）：

| 命令 | 本卡 | 基线 `36d2b5429` |
| --- | --- | --- |
| `tests/unit/test_R158_地板证据窗口漂移.py` | 4 passed / 6 failed | **同样 4 passed / 6 failed（同名同数）** |
| `tests/test_codegen.py` | 22 passed | — |
| `tests/test_path_guard_light.py` + `tests/unit/test_bootstrap_compiler.py` | 全绿 | — |

`test_R158_地板证据窗口漂移.py` 那 6 红是**既有红**：主仓 `36d2b5429` 未改动时逐条同名
同数复现，与本卡无关（本卡没增删顶层 `def`，地板分母 190 不变）。

### 换名的破面排查（先扫后改，不是改完再撞）

改前扫了全仓 `.py`（`src/ stdlib/ tests/ tools/ bootstrap/`）里对这 75 个函数名的
**关键字调用**，只有 7 处命中，逐条核实后**全部是别的模块的同名函数**：

- `stdlib/外部命令.py` 的 `执行命令(捕获输出=…, 工作目录=…)` → 该文件 `:40` 自己定义了
  `执行命令`（5 参），不是地板的 `执行命令(命令)`。
- `tests/test_new_modules.py:445` / `tests/test_stdlib_phase13.py:226` 的
  `美化JSON(数据, 缩进=2)` → 调的是 `美化输出`/`JSON` 模块的 `美化JSON`，不是地板那个。

`.light` 门面调地板一律按位置传参，不受影响。

## 没做 / 风险（诚实声明）

1. **`lightharness` 独立仓没有提交**。本卡工作区里的 LH 副本
   （`<worktree>/../lightharness/stdlib/builtins.py`）是由 `scripts/sync_builtins.py`
   生成的、与真源逐字一致（`test_LH形参名与真源逐字相同` 钉住），但**真正的
   `G:/dswork/duan-light-merge/lightharness` 仓我没动**：它当前是
   `## main...myrepo/main [ahead 7, behind 1]` 且 `stdlib/builtins.py` /
   `stdlib/内置核心判型.light` 已有**上一轮遗留的未提交改动**，
   直接覆盖会吞掉别人的工作。LH 仓的落地需要单独一张卡（或由该仓 owner 跑一次
   `scripts/sync_builtins.py` 后提交）。本卡的 3 条 verify 都不依赖 LH 仓的 git 状态。
2. **`原子写入` 不在 `stdlib/builtins.py` 里**，它是 `stdlib/路径护栏.light:296` 的段落
   （`段落 原子写入(路径, 内容)`，形参本来就是中文）。卡面把它列进代表函数，
   我按「它已经是中文、别改回去」来钉，没有改 `.light`（`.light` 不在本卡允许路径内）。
   卡面说的「原子写入内部 encoding + 权限 混着」在当前 `main` 上已不复现。
3. **`阶乘(数)` / `十进制加(甲, 乙)` 与 `.light` 门面的 `阶乘(n)` / `十进制加(a, b)`
   不同名**。门面是独立实现（不在本卡允许路径内），地板这侧按「形参必须全中文」的
   要求改成了中文名；两边都能用位置参数互调，但关键字名不一致这一点如实记在这里。
4. **`dir_path` 这类函数内局部变量仍是英文**，本卡只管形参（门禁也只判形参）。
5. 没有跑 LH 全量（2100+ 用例，本机 ~53 分钟）—— 本卡只动形参名、不动语义，
   已用上面 4 组邻接回归 + 全仓关键字调用扫描覆盖破面。若需要全量对拍，建议送 0.88。
