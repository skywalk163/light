# T-0215 · 光明P2：原生腿 `参数列表()` 比转译腿多返回 argv[0]（跨腿口径差 1）[L-262]

**结论：口径已销账 —— 两条腿的 `参数列表()` / `用户参数()` 逐元素相等，都不含程序名。**

## 做了什么（四处，都在卡面 paths 内）

1. `src/llvm/runtime_typed.c:dv_get_args`：循环从 `i = 1` 起，跳过 argv[0]
   （对齐 `sys.argv[1:]` 口径）。原生产物是独立进程，argv[0] 是它自己的路径。
2. 同文件新增 `_dv_arg_to_str`：**Windows 上 argv 不是 UTF-8** —— CRT 按 ANSI
   代码页（本机 936/GBK）解码，同一批中文实参原生腿拿到 GBK 双字节，打印乱码、
   逐元素对拍必红。改为 CP_ACP 宽化 → CP_UTF8 窄化，与运行时「内部一律 UTF-8
   字节流」口径对齐；非 Windows 原样使用。
3. `src/llvm/codegen_typed.py:3416`：`用户参数` 并入 `参数列表`/`argv`/`args`
   分派（此前原生腿 `用户参数()` 是未定义名，换后端就 NameError），同走 `dv_get_args`。
4. `cli/light.py`：main() 在 argparse **之前**按第一个裸 `--` 硬切（只对 `run` 生效），
   实参挂 `args.用户实参`；`_run_native` 起产物时真传（`subprocess.run([exe, *用户实参])`）；
   `_run_src` 在执行期内把 `sys.argv` 设成这批实参、并补 `用户参数` 别名，跑完（含异常
   路径）还原。不写 `--` 时口径逐字不变。
5. `tests/unit/test_T6B_时间系统内建_原生腿.py:207`：`assertGreaterEqual(N, 1)` →
   `assertEqual(N, 0)`。**理由（卡面要求写明）**：该断言旧口径 `>= 1` 恰恰是靠
   「多算一格 argv[0]」才成立的，正是 L-262 病灶本身；该用例跑产物时不带任何用户
   实参，跳过 argv[0] 后长度**必须恰为 0**。改成「恰为 0」比卡面允许的 `>= 0`
   **更严**，不是放宽：它直接钉死「返回值不含程序名」，argv[0] 一回来长度立刻变 1 转红。

## 新增 `tests/unit/test_LH41_原生腿参数口径.py`（17 例）

验收 1：两腿 `参数列表()` 逐元素相等（含长度）+ 长度恰为 2（不是 3）；
验收 2：两腿 `用户参数()` 相等、且与本腿 `参数列表()` 同源；
边界：`--` 后为空 → 两腿都空；空格/中文/引号原样到达；`--backend native` 当数据不被吞；
源码级守：runtime 必须 `i = 1`、必须走 UTF-8 转换、codegen 必须登记 `用户参数`、
cli 起产物必须带实参；
反跑有牙：把循环改回 `i = 0`、把 `用户参数` 摘掉，同一判据变红（原文件一字未动）。

## 验证（全部本机实跑，含真编译真跑）

| 命令 | 结果 |
|---|---|
| `python3 -m pytest -q tests/unit/test_LH41_原生腿参数口径.py`（**卡面验收**） | **17 passed** |
| `tests/unit/test_T6B_时间系统内建_原生腿.py`（被改断言的那个套件） | **5 passed** |
| `tests/test_native_cli.py`（原生腿 CLI 贴边回归） | **35 passed**（与改动前基线同） |
| `test_R154_L213_环境变量口径.py` + `test_R130_对象池缓存_原生腿.py` | **18 passed** |
| `test_R131_L186L187_原生腿.py` + `test_LH38_下标与切片写.py` | **40 passed** |
| `test_entry_function.py` + `test_L093_L094_diagnostics.py`（`_run_src` 调用方） | **17 passed** |
| `flake8 cli/light.py src/llvm/codegen_typed.py <两个测试文件> --max-line-length=120` | rc=0 |

手工端到端（真编译真跑，`light run <入口> [--backend native --optimize O0] -- <实参>`）：
`甲 乙` → 两腿均 `参数列表=['甲','乙']`、`用户参数=['甲','乙']`；`--` 后为空 → 两腿均空；
`a b`/`中文`/`带"引号"` → 两腿字节级一致；`--backend native` 作为数据 → 两腿均原样接住。

## 诚实披露：本卡前提与 main 不一致

- 卡面根因写「转译腿读 CLI 注入的 `LIGHT_USER_ARGS`」。**main 与全部远端分支上都没有
  这个注入点**：LH-05（T-0196）的落地只在分支 `task/T-0196`（未合入 main），其 summary
  自己记着「原生腿的用户实参透传没接 ⇒ 建议另立卡」。故本卡是在 **T-0196 未入 main
  的前提下**做的：口径仍按卡面要求（两条腿都不含程序名、`--` 之后原样到达），
  但转译腿的实现落点是 `_run_src` 里设 `sys.argv` + 命名空间内 `用户参数` 别名
  （不是读环境变量），这些改动都在本卡允许的 `cli/light.py` 内，未碰 `stdlib/builtins.py`。
  若日后 T-0196 合入 main（`参数列表()` 改读注入点），本卡的 `_run_src` 设 `sys.argv`
  那段仍成立（两者同源），只需复核 gate；**合卡时请留意这处重叠**。
- `用户参数` 在地板 `stdlib/builtins.py` 里同样不存在（同属 T-0196 未落地）；本卡
  在 `cli/light.py` 的命名空间与 `codegen_typed.py` 各补一处，**未改地板文件**
  （不在允许 paths 内，地板名单冻结也不允许新增顶层 def）。
- 未跑全量 `tests/unit`（全量在本机 ~1.5–2.5 小时，且 78 条既有红与本卡无关）；
  已跑上表六个套件、共 132 例全绿。

## 遗留风险

1. `参数列表()` 无参时的口径现在是「空表」（原为「含产物路径」）。这是**有意的语义
   修正**（对齐 `sys.argv[1:]`），但对存量里「拿 argv[0] 当程序名」的原生腿脚本是
   **行为变化**：仓内 `stdlib/参数解析.light`、`stdlib/sys.light` 只读长度/遍历，
   实测不受影响；仓外脚本无法排查，已在卡内如实记录。
2. Windows 上 argv 的 CP_ACP→UTF-8 转换按「CRT 走 ANSI 代码页」的实现假设；
   若日后改用 `wmain`/`-municode` 或 manifest 声明 UTF-8，这段会变成 no-op 直通
   （仍是正确结果），不会反向破坏。
3. 无 clang 的 CI 上，本文件 12 例原生腿会 skip（`skipUnless`），仅 5 例（转译腿 +
   源码级守 + 反跑）真跑 —— **本机有 clang，全部 17 例都是真编译真跑过的**，
   skip 分支只是给无工具链机器留的退路。
