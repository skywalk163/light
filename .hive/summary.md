# T-0249 · light 跨平台原生腿 argv 编码：Windows ×4 统一口径

**结论：Windows 原生腿已改走宽字符入口（GetCommandLineW + CommandLineToArgvW），argv 以 UTF-8 直出；定向测试本机 17 passed，反跑（i=1 → i=0）10 failed / 7 passed，有牙。**

## 改动（仅 3 个 paths 内文件）

1. `src/llvm/runtime_typed.c`
   - Windows 分支不再使用 CRT 的 `argc/argv`：`dv_init_args` 调 `_dv_init_args_win()`，
     用 `GetCommandLineW()` + `CommandLineToArgvW()` 取参数，逐格经
     `_dv_wide_to_utf8()`（`WideCharToMultiByte(CP_UTF8)`）重建 `_dv_argv`；
   - `_dv_arg_to_str` 只做 `dv_str`（输入已是 UTF-8），删掉旧的两跳
     `MultiByteToWideChar(CP_ACP)` → `WideCharToMultiByte(CP_UTF8)`；
   - `dv_get_args` 的 `i = 1` 口径未动；**非 Windows 分支一字未改**；
   - 补 `#include <shellapi.h>` 与 `#pragma comment(lib, "shell32.lib")`。
2. `src/llvm/compiler.py`
   - `get_link_libs()` 的 win32 分支追加 `-lshell32`（`CommandLineToArgvW` 所在库）；
     测试侧 `tests/llvm运行时.py` 本来就转调该函数，故单点生效。
3. `tests/unit/test_LH41_原生腿参数口径.py`
   - 文件头「修法」第 2 条改成宽字符入口口径；
   - `test_runtime_Windows按UTF8取出` 改为 `test_runtime_Windows走宽字符入口`：
     断言 `GetCommandLineW` / `CommandLineToArgvW` / `_dv_wide_to_utf8` 含 `CP_UTF8`，
     并断言 `_dv_arg_to_str` 函数体不含 `CP_ACP`（有牙，防回退）；
   - 用例总数仍为 17，没有新增 skip、没有放宽断言。

`src/llvm/codegen_typed.py`（`用户参数` 已登记）与 `cli/light.py`（`结果 = subprocess.run([exe] + _当前用户实参())`）
经复核已满足本卡要求，未改动。

## 验证证据

| 项 | 命令 | 结果 |
|---|---|---|
| 定向测试（修前基线，本机 zh-CN） | `python -m pytest -q tests/unit/test_LH41_原生腿参数口径.py --timeout=300` | 17 passed in 235.63s |
| 定向测试（修后） | 同上 | **17 passed in 64.40s** |
| 反跑有牙（`i = 1` 改回 `i = 0`） | 同上 | **10 failed, 7 passed**（原生腿多出 argv[0]，如 `AL=3` / `A0=<产物路径>`），复原后复测 17 passed |
| 卡面 verify#2 | `python -c "... sys.exit(0 if ('CP_ACP' in s) else 1)"` | exit 0 |
| 改动边界 | `git status --porcelain` | 仅上述 3 个 paths 内文件 |

反跑那一轮的失败输出同时证明宽字符链路真的在工作：把 `i` 改成 0 后，中文实参仍然原样
（`A1=a b`、`A2=中文`、`A3=带"引号"`），红的是「多一格 argv[0]」，不是编码。

## 说明与风险

- **本机无法复现 runner 的 ACP=1252 红**：本机 ACP=936，修复前就是 17 passed。
  因此「en-US runner 转绿」不能由本机直接证明；本机证明的是：① 新入口真编译真跑、中文原样；
  ② 源码级守钉住 `GetCommandLineW`/`CommandLineToArgvW`/`CP_UTF8` 且禁止 `CP_ACP` 回到 argv 链路。
  GitHub 侧 4 条 Windows job 的终审（卡 §5.3）仍需主控在 land 前跑。
- 卡面 verify#2 断言的是文件里仍有 `CP_ACP` 字样。实际代码已不再用 `CP_ACP`，该字样只保留在
  说明「旧两跳转码已删除、是病灶」的注释里；若主控认为该 verify 已过期，建议改判据。
- 流程偏差（非代码）：本机 hived 的 store 只在启动时从 Git 摄入任务卡，16:54 创建的 T-0249 不在 store，
  `hive claim` 报 `T-0249 store 领取失败：没有任务 T-0249`。本次用
  `HIVE_CLAIM_BACKEND=git take/submit` 走 Git 租约（`claim/T-0249` → `task/T-0249`），
  未修改任何 hive 配置或任务卡正文。
- 未写任何 token / 密钥 / IP；未用 `--no-verify`，未改 hooks/hooksPath。
