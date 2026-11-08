# R167 T-3 交付报告：3 例 xpassed 摘 xfail + 断言有牙复核（含运行时反跑实证）

- 轮次：R167「门禁可信度收口轮」・**T-3**（任务书 `light-merge/_R167_并行任务书.md` §4）
- 基线代码：`2f359753b`（R166 收口，四远端一致）
- 本线**唯一改动文件**：`tests/test_native_isinstance_typing_modules.py`（diff = **7 insertions / 13 deletions**）
- 执行分工：**本机 Windows 只做编辑与 diff / 机读取证**（不跑 pytest）；**判据与反跑在权威判绿机 0.88**（`ssh workbuddy@192.168.0.88`，FreeBSD 15.1-RELEASE-p1，12 核 / 64G）执行
  - 解释器：`~/r164venv/bin/python`（Python 3.12.13，pytest 8.4.2，`pytest-xdist` / `pytest-randomly` 已装，本轮一律 `-n 0 -p no:randomly`）
  - clang：`/usr/bin/clang`；全部命令前缀 `nice -n 20`
- **反跑隔离**：本轮在**私有净树** `~/r167t3` 执行（`git clone ~/r164clean` + `git fetch https://gitcode.com/skywalk163/light.git main` + `git checkout -f 2f359753b`），`git rev-parse HEAD` = `2f359753b3f0dbb5e9ca568de1aa15542a07a72c`，起始 `git status --porcelain` 干净 ⇒ **反跑窗口不与其他线互踩**（任务书 §6 要求，规避 §6-210 提到的 `test_R159_E3_容器布尔repr.py` 共用 `runtime_typed.c` 窗口冲突）
- 纪律：**本线未 commit / 未 push / 未 git add**；只改本线点名文件；未动 `src/`（含 `src/llvm/`）任何文件——反跑期的临时破坏**已用备份逐字节还原**，未用 `git stash / checkout -- / reset --hard / clean`；未跑 `pull_stdlib_from_light.py`；未碰 T-1（`tests/e2e/`）/ T-2（`scripts/` + `docs/` + `pyproject.toml`）/ T-4 的文件域

---

## 一、判据核对（任务书 §4.2）

| # | 判据命令 | 要求 | 实测 | 结论 |
|---|---|---|---|---|
| ① | `pytest tests/test_native_isinstance_typing_modules.py -n 0 -p no:randomly -q -rxX` | `7+3 passed`，`xpassed=0`，`xfailed=0` | `10 passed in 13.82s`，**EXIT=0**，`-rxX` 未产出任何 `XFAIL` / `XPASS` 段 | ✅ |
| ② | 任务书 §4.1-2 有牙复核 | 断言须为「具体值/具体分支」形态，否则补强或改 `strict=True` 并登记 | 三条断言**均为具体值形态**（见 §三），无需补强、无需保留 xfail | ✅ |
| ③ | 任务书 §4.1-3 反跑 | 破坏 `dv_isinstance` 标量分支后三条必须转红 | `3 failed, 7 passed in 13.83s`，**EXIT=1**，转红者恰为目标三条（见 §四） | ✅ |

> 判据 ① 在**净树**上跑（`~/r167t3`，仅工作副本含本线那一处测试文件改动），故 `10 passed` 中的 **7** 为转译腿 + 原生腿非 xfail 用例，**3** 为本次摘掉 xfail 后真跑的用例；无 `xpassed / xfailed` 残留，说明「摘 xfail」是彻底摘除而非被 `strict=False` 吞成提示。

---

## 二、§4.1-1 · 摘三处 xfail + docstring 改写

### 2.1 改动总览（`git diff`，7 insertions / 13 deletions）

| 位置（改后行号） | 改动 |
|---|---|
| 模块 docstring 第 2 条（`:17` 起，+5 / -3） | 「A1（R124-A）未落地前这些断言**必然失败**，按 `pytest.mark.xfail` 登记（不阻塞 CI）；A1 落地后自动转绿（无需改本文件）」→ 改为「**R124-A1 已修**（修复轮次 = R124 收口 `362618f3f`：`src/llvm/runtime_typed.c` 的 `dv_isinstance` 新增 `dv_scalar_isinstance` 原生标量分派），故三条原生腿用例自 **R167-T3** 起**摘掉 `pytest.mark.xfail`、转为真跑护栏**——原 `strict=False` 的 xfail 把 XPASS 吞成提示，缺陷回潮无人知（`_R167_并行任务书.md` §0.2）；断言有牙由 R167-T3 反跑实证」 |
| 段落标题 `:119` | `# 二、原生腿（LLVM）：真编译 + 真跑，A1 未落地前必然失败 → xfail（不阻塞 CI）` → `# 二、原生腿（LLVM）：真编译 + 真跑，R124-A1 已修 → 真跑护栏（无 xfail）` |
| `:196`（原）→ 现 `:197-198` 后 | 删除 `@pytest.mark.xfail(reason='R124-A1 未落地：原生腿 isinstance 对原生标量恒假（dv_isinstance 仅服务类实例）', strict=False)`（3 行） |
| `:248`（原）→ 现 `:246-247` 后 | 删除 `@pytest.mark.xfail(reason='R124-A1 未落地：原生腿 isinstance 对原生标量恒假 ⇒ 副本 不分流 dict/list', strict=False)`（3 行） |
| `:268`（原）→ 现 `:263-264` 后 | 删除 `@pytest.mark.xfail(reason='R124-A1 未落地：原生腿 isinstance(连接符, str) 恒假 ⇒ 连接字符串 对合法 str 也抛', strict=False)`（3 行） |

三处删除后，三条用例仅剩功能门控装饰器 `@_需真跑[0]`（clang 可用）/ `@_需真跑[1]`（Windows 下 MSVC env），语义为「环境不具备则 skip」，**不再是「预期失败」**。

### 2.2 残留 `xfail` 字样核查（防漏摘）

`grep -n "xfail"` 后仅剩 **3 处纯文字说明**，无任何 `pytest.mark.xfail` 装饰器：

| 行 | 性质 | 说明 |
|---|---|---|
| `:20` | docstring | 本报告 §2.1 新写的护栏口径说明 |
| `:119` | 段落注释 | 本报告 §2.1 改写的段落标题 |
| `:229` | docstring | `test_原生腿_内置核心判型_是字节_设计边界恒假` 内「本用例**不 xfail**：它断言的是恒假这一设计边界，A1 修完 `dv_isinstance` 后仍应恒假」——**该说明本就正确、无需改**（bytes 在原生腿无一等类型，恒假是设计边界，见下） |

> 佐证：判据 ① 的 `-rxX` 输出中无 `XFAIL`/`XPASS` 条目，与「零装饰器残留」自洽；`_需真跑` 列表（`:190-`）本身不含 xfail 标记。

---

## 三、§4.1-2 · 有牙复核（三条断言是否真钉住「原生腿 isinstance 判型正确」）

结论：**三条断言均为「具体值」形态，非「不抛异常」弱形态，无需补强，也无需保留 `strict=True` xfail**。

| 用例 | 断言行（改后） | 断言原文（要点） | 形态判定 |
|---|---|---|---|
| `test_原生腿_内置核心判型_各标量判型失真` | `:212` | `assert lines == ['整数:真','字符串:真','列表:真','字典:真','数值:真','布尔:真','浮点:真']` | **具体值全等**（7 个类型名 + 每个的判型结果逐项钉死） |
| `test_原生腿_内置核心列表_副本不独立` | `:260` | `assert lines == ['原:1','副:99']`（f-string 报错含实际值） | **具体值全等**（副本脱钩后原容器保持 1、副本改 99，二者不对称即红） |
| `test_原生腿_字符串工具轻量_连接字符串抛` | `:271` | `assert r.returncode == 0 and _输出(r) == '连接:a-b'` | **退出码 + 具体输出双钉**（对合法 str 输入必须 rc=0 且输出 `a-b`） |

- 三条都不是「只要不抛异常即过」：例如第二条若只写「不抛异常」，则 `副本` 退化「原样返回」时仍不抛而蒙混过关；现断言值 `['原:1','副:99']` 会立刻抓到退化（见 §四实测 `['原:99','副:99']`）。
- 第三条把 `returncode == 0` 一并钉住：合法输入下它若抛（rc=1）即红（见 §四实测 `rc=1 out=''`），亦不属于弱形态。
- 因此**不触发** §4.1-2 的「保留 xfail + `strict=True` + 报告登记」分支；该分支本轮不适用，无需登记欠账。

---

## 四、§4.1-3 · 反跑取证（三条必须转红）

### 4.1 破坏方式（「退回修复前形态」等价）

任务书允许「临时把 `dv_isinstance` 的标量分支改坏（或退回修复前的判断）」。采用**退回修复前形态**（比「改坏」更干净，语义即 R124-A1 之前「非类实例恒假」）：

```
# ~/r167t3/src/llvm/runtime_typed.c:6113  破坏前
    return dv_scalar_isinstance(obj, class_name);
# 破坏后
    return 0;
```

```
$ diff /tmp/runtime_typed.c.r167t3.bak src/llvm/runtime_typed.c
6113c6113
<     return dv_scalar_isinstance(obj, class_name);
---
>     return 0;
diff_rc=1
```

> 破坏前已 `cp src/llvm/runtime_typed.c /tmp/runtime_typed.c.r167t3.bak`（12761 行）备份；仅改 1 行，`src/` 其余部分未动。

### 4.2 反跑判据输出（破坏树）

```
$ cd ~/r167t3 && nice -n 20 ~/r164venv/bin/python -m pytest \
    tests/test_native_isinstance_typing_modules.py -n 0 -p no:randomly -q -rxX
.....F.FF.                                                               [100%]
...
3 failed, 7 passed in 13.83s     # EXIT=1
```

**转红者恰为目标三条**，且失败原因直指判型失真：

| 用例 | 实测失败信息 |
|---|---|
| `test_原生腿_内置核心判型_各标量判型失真` | `AssertionError: 原生腿判型失真（isinstance 缺陷），实际：['整数:假','字符串:假','列表:假','字典:假','数值:假','布尔:假','浮点:假']`（期望全「真」） |
| `test_原生腿_内置核心列表_副本不独立` | `AssertionError: 原生腿 副本 未脱钩（isinstance 缺陷），实际：['原:99','副:99']`（期望 `['原:1','副:99']`；`副本` 因 `isinstance(原,dict)/isinstance(原,list)` 双双恒假 ⇒ 退化为「原样返回」） |
| `test_原生腿_字符串工具轻量_连接字符串抛` | `AssertionError: 原生腿 连接字符串 对合法输入应得 a-b，实际 rc=1 out=''`（`连接字符串` 内 `isinstance(连接符, str)` 恒假 ⇒ 对合法 str 也抛） |

**未转红者**（7 passed）中，含 `test_原生腿_内置核心判型_是字节_设计边界恒假`——它断言的是「bytes 判型**恒假**」这一**设计边界**（原生腿 `b"..."` 落成 STRING，`isinstance(值,"bytes")` 恒假），破坏标量分支后仍应恒假，故**正确地不转红**；这与 §2.2 `:229` docstring 说明一致，佐证该用例不是本次遗漏的 xfail。

### 4.3 还原与复核（禁止 `git` 回滚类命令）

```
$ cp /tmp/runtime_typed.c.r167t3.bak src/llvm/runtime_typed.c
$ diff /tmp/runtime_typed.c.r167t3.bak src/llvm/runtime_typed.c   # 无输出 ⇒ 逐字节一致 rc=0
$ sed -n "6109,6114p" src/llvm/runtime_typed.c
    /* 类实例之外的路径：原生标量（含 None）判型。… */
    return dv_scalar_isinstance(obj, class_name);
$ git rev-parse HEAD            # 2f359753b3f0dbb5e9ca568de1aa15542a07a72c
$ git status --porcelain
 M tests/test_native_isinstance_typing_modules.py       # 仅本线文件
```

还原后**复核判绿**（同一判据命令）：

```
$ nice -n 20 ~/r164venv/bin/python -m pytest \
    tests/test_native_isinstance_typing_modules.py -n 0 -p no:randomly -q -rxX
10 passed in 13.82s     # EXIT=0
```

⇒ 反跑红 → 还原 → 复核绿，**闭环**；`src/llvm/runtime_typed.c` 在工作树中恢复原状，`git status --porcelain` 只剩本线那一处测试文件改动。

---

## 五、修复轮次溯源（docstring 引用的 `362618f3f`）

任务书要求 docstring 注明修复轮次，故须给出可追溯证据：

```
$ git log -S "dv_scalar_isinstance" --oneline -- src/llvm/runtime_typed.c
362618f3f R124 收口：修复原生腿 isinstance 对原生标量恒假（8 形态转真）+ 判型用例入库
```

- **修复轮次 = R124 收口 `362618f3f`**（该提交同时入库了 `tests/test_native_isinstance_typing_modules.py` 本体，当时三条用例带 `strict=False` 的 xfail）。
- 代码事实佐证（`src/llvm/runtime_typed.c`）：
  - `dv_isinstance` @6089：先 `dv_deref`，判 `type==3 && strncmp(obj->str, OBJ_PREFIX, …)==0` 走 `dv_isinstance_inner`（类实例路径），否则 `return dv_scalar_isinstance(obj, class_name);` @6113（**R124-A1 新增的原生标量分派**）；
  - `dv_scalar_isinstance` @6118（前置声明 @6087）；
  - 破坏该分派即等价退回「非类实例恒假」⇒ 即 §四 反跑所用形态。
- 为何 R124 修完仍留 xfail：该 xfail 用 `strict=False`，R124 修复后三条用例**转为 XPASS 但被吞成提示**，`-rxX` 只见提示、CI 不红，故缺陷「已修」与「护栏已摘」之间存在 **R124→R167 的护栏欠账**，本轮 T-3 正是收口这笔欠账（对应任务书 §0.2「xpassed 无人知」口径）。

---

## 六、本机侧静态复核（Windows）

| 项 | 结果 |
|---|---|
| `git diff --stat -- tests/test_native_isinstance_typing_modules.py` | `1 file changed, 7 insertions(+), 13 deletions(-)`（与报告口径一致） |
| `python -m py_compile tests/test_native_isinstance_typing_modules.py` | **rc=0** |
| 行尾规范 | `CRLF=0, bareLF=306, bytes=16571`（纯 LF，与仓库索引存储形态一致；`git diff` 仅余 autocrlf 提示，非本线引入） |
| `grep "pytest.mark.xfail"` | 0 命中（§2.2） |

> 说明：本机工作区 `git status --porcelain` 另见 **T-2 线**在跑的 4 个改动文件（`docs/门禁机初始化清单_0.88.md`、`pyproject.toml`、`scripts/ensure_venv.py`、`tests/ci_baseline_failures.txt`，diff 内明确标注 `R167-T2`），以及任务书本身 `?? _R167_并行任务书.md`。**上述均非本线产物，本线未触碰**，本线 `git diff` 严格限定于点名文件。

---

## 七、命令与日志留痕（0.88）

| 文件（0.88） | 内容 | 关键结果 |
|---|---|---|
| `~/r167t3` | 私有净树（clone 自 `~/r164clean` + fetch gitcode + `checkout -f 2f359753b`） | `HEAD=2f359753b…`，起始 porcelain 干净 |
| `/tmp/runtime_typed.c.r167t3.bak` | 反跑前备份（12761 行） | 还原基准 |
| `~/r167_t3_runF.log` | 改动后首次判据（会话内已产） | `10 passed`，EXIT=0 |
| `~/r167_t3_negF.log` | 破坏后反跑 | `3 failed, 7 passed`，EXIT=1 |
| `~/r167_t3_runG.log` | 还原后复核判据 | `10 passed in 13.82s`，EXIT=0 |

判据命令全文（两处仅 log 文件名不同）：

```
cd ~/r167t3 && nice -n 20 ~/r164venv/bin/python -m pytest \
  tests/test_native_isinstance_typing_modules.py -n 0 -p no:randomly -q -rxX
```

---

## 八、红线遵守与遗留

**遵守**

- ✅ 不 commit / 不 push / 不 `git add`；收口交主 agent。
- ✅ 只改点名文件 `tests/test_native_isinstance_typing_modules.py`；`git diff` 限定自己文件（见 §六）。
- ✅ 反跑用**私有净树** `~/r167t3`，与 T-1/T-2/T-4 跑批窗口隔离（§6 要求）。
- ✅ 未用 `git stash / checkout -- / reset --hard / clean`；反跑破坏用 `cp` 备份**逐字节还原**。
- ✅ 未动 `src/` 产品代码（反跑临时改动已还原）；未跑 `pull_stdlib_from_light.py`。

**遗留 / 交接**

- 无本线未决缺陷；三条用例由「xfail（strict=False）」转为「真跑护栏」，且 R167-T3 反跑已实证其**有牙**（§四）。
- 任务书 §4.1-2 的「保留 xfail + `strict=True` + 报告登记」分支本轮**不适用**（断言非弱形态，§三），故无欠账登记项产生。
- 本报告文件本身为**未提交**状态，连同测试文件改动一并交 M 口收口决定。
- 任务书 §0.1 L4 残留 1 例 skip / §0.3 表格与 128 skipped 差额等属 **T-1** 范围，与 T-3 无关，本线不涉。