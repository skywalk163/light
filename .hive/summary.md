# T-0251 交付说明：light 正则引擎 / codegen 写回回归

## 结论先行

卡面列的四条（A/B/C/D）在**本机 Windows 上只有 A 重现**，且 A 的真身与卡面猜的
「T6A-11 堆损坏复发」**不是一回事**；B 在本机其实是**判据口径漂移**（环境变量缺
失导致 UTF-8 输出被二次编码），C/D 在本机**已全绿/skip**（见第三节逐条取证）。

修掉两处根因后，两条 verify 命令**在本机 Windows 上连续绿**：

| 命令 | 结果 |
|---|---|
| `pytest -q test_relight_engine_O0.py test_codegen_ref_dict_O0.py test_R140_L182_L191_原生腿.py --timeout=300` | **20 passed, 1 skipped** |
| `pytest -q test_codegen_ref_dict_O0.py test_R140_L182_L191_原生腿.py` | **13 passed, 1 skipped** |
| 附带：`pytest -q test_T6a_正则文本模块_原生腿.py --timeout=300` | **17 passed** |

另跑了 CI 同环境 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` 一遍，同样 20 passed / 13 passed，两个口径一致。

---

## 一、A 条：Windows 进程级崩溃 = **栈溢出**，不是堆损坏复发

### 取证（把「断言全错」与「进程崩溃」分开，卡面要求）

- 本机 Windows 11 / Python 3.14 / clang 22.1.8，`TestT6A11_MemorySafety::test_20次连续验证调用_不崩且正确`
  → `rc=3221225725`，**stdout 全空、stderr 全空**。这是**进程级**退出，不是断言失败。
- `3221225725 = 0xC00000FD = STATUS_STACK_OVERFLOW`（不是 T9B 修掉的 `0xC0000374` HEAP_CORRUPTION）。
- 最小化：**只调用一次 `验证IPv6地址` 就崩**，不用 20 次。模式
  `^([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}$` 在 Windows 默认栈上单次就吃穿。
  （插曲：源里 `{1,4}` 的 `{`/`,` 是方言保留字，只能用 `re_花括号(1,4)` 运行期拼；
  拼出来的模式本身没问题，问题在深度。）
- 决定性实验：同一份 IR 手工链接，只改栈尺寸——

  | 栈尺寸 | 结果 |
  |---|---|
  | 1MB（MSVC 默认） | `0xC00000FD` |
  | 2 / 3 / 4 / 6 / 8 / 64MB | **全绿，输出全对** |

  栈一抬就好 ⇒ 根因是**栈深度**，与堆、与列表生命周期都无关。

### 根因

re.light 的回溯 VM（`stdlib/re.light` `re_内部_跑`）是**真递归**：`支`、`循支`、
`{n}` 展开每层回溯都再进一层递归。O0 下 `_seg_fN` 帧里还压着一整套 LightValue
临时槽（IR 实测单帧 41 个 alloca / 328 字节，加对齐与调用窥孔远大于此）。
Windows 的 PE 默认栈是 **1MB**，Linux/FreeBSD 默认是 **8MB** —— 这就是
「mac/POSIX 不崩、Windows ×4 必崩」的全部原因。

### 修复

`src/llvm/runtime_typed.c` 的 Windows 段加一条：

```c
#pragma comment(linker, "/STACK:8388608")
```

把它放在**运行时库**而不是 `compiler.py` 的 `link_args`，因为运行时库被三个链接点
（`compile_light_typed` / `compile_light_project` / `c_backend`）共同链接，一处声明
覆盖全部产物；`/STACK` 走 COFF `.drectve` 节，lld-link 与 MSVC link 都认
（`llvm-readobj --coff-directives` 实测可见 `/STACK:8388608`）。非 Windows 段不编译，
Linux/FreeBSD/macOS 不受影响。

**没有**动 re.light 的算法（把递归改成显式回点栈 = VM 重写，超出本卡）。

### 反跑（有牙，两个方向都实测）

- 摘掉 pragma → `test_20次连续验证调用` 立刻 `rc=3221225725` 变红；
  `test_T6a_正则文本模块_原生腿.py` 的 `test_正则_验证函数_完整20次` +
  `test_正则_验证函数_2_URL_IP` 同时变红。
- 装回 → 全绿。

> 注意：**POSIX 上摘 pragma 无变化**（那边默认就是 8MB）。这条反跑只能在 Windows 上做。

---

## 二、B 条：本机是**判据口径漂移**，不是正则引擎回归（已一并治掉）

卡面 B 说「win + mac 都错、形态是正例判假」。本机实测**不是**：

- 同一模式 `re_完全匹配` 单跑 → 真；IPv4 四条用例单文件跑 → **4 passed**；
  连编 20 次同一源 → **产物稳定，只有一组结果**。没有「第三分支没走到」。
- 真正让本机变红的是**输出解码**：`_t6a_native_helper.py` 把被测程序的 UTF-8 字节
  `decode` 成 str 再 `sys.stdout.write`，而 helper 进程 stdout 在 Windows 默认是
  **代码页 936(GBK)** → 二次编码。父进程按 UTF-8 解码只剩 `\ufffd\ufffd`：

  ```
  继承 locale : raw = b'\xd5\xe6\r\r\n'     → utf8 解码 = \ufffd\ufffd
  强制 utf-8  : raw = b'\xe7\x9c\x9f\r\r\n' → utf8 解码 = 真     （正确）
  ```

  于是 `真/假` 全丢 → 四条 IPv4 用例「实际=['假','假','假','假']」——**形状与卡面
  描述一模一样，但成因完全不同**：卡面是引擎少走分支，本机是转发层丢字节。
- 为什么 CI 看不到：`.github/workflows/ci.yml` 第 56~58 行设了
  `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`，恰好把这个坑盖住了。所以这不是
  「本机 vs CI 产物不同」，是**判据两侧口径不一致**。

### 修复（控制在 paths 内）

`_t6a_native_helper.py` **不在**本卡 paths，所以没有改它（先改过、验证有效，随后
按红线回退）。改为在**允许的测试文件**里把 helper 的编码环境显式对齐 CI：

- `tests/unit/test_relight_engine_O0.py`
- `tests/unit/test_T6a_正则文本模块_原生腿.py`

两处都是 `_subproc.run(..., env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8'))`，
并写了注释说明「不这么做，本机会把环境变量缺失误判成产物回归」。

### 反跑（有牙）

- `git stash` 掉 test_relight_engine_O0.py 的 env 改动 → **7 failed**（IPv4 四条 + T6A11 三条）。
- 装回 → 7 passed。
- 顺带证明：**A 与 B 是两条独立缺陷**——只修栈不修编码，IPv4 仍红；只修编码不修栈，
  T6A11 仍崩。两者都修才全绿。

---

## 三、C / D 条：本机全绿，未改代码（如实说明）

| 条目 | 本机 Windows 实测 | 处置 |
|---|---|---|
| C `test_回溯递归_参数写回不污染_O0` | **passed**（无 `RETRY=1/CLASS=1/MAIL=0` 污染） | 不改；失败签名只在 mac ×2 出现（CI job 125731686508 / 125731686598），本机无法取证 |
| D `test_L182_写JSON形参不被同名全局遮蔽` | **skipped**（该用例既有 `@pytest.mark.skipif(sys.platform=='win32')`，理由「本机禁止实跑 A 线原生腿」） | 不改；失败签名只在 mac ×2 出现 |

> 这两条我没有「改弱断言 / 进基线豁免」来转绿 —— 它们本来就没红。C/D 的结论是：
> **本机不可取证，红只出现在 mac ×2**，需要 mac 侧环境或 GitHub 终审才有证据；
> 不该由本卡在 Windows 上硬判。

---

## 四、GitHub 终审（判据 4）—— 未取得，如实说明

按卡面，终审合格线是「A~D 六个 nodeid 在 windows ×4 的 step 级失败清单里消失」。
我拉了 **run 41579793947**（2026-11-03，卡面引用的原始 run）的 step 级清单：

- windows ×4（3.10/3.11/3.12/3.13）的 `Unit Tests` **全部 failure**，失败清单里含：
  `test_relight_engine_O0.py::TestT6A11_MemorySafety::test_20次连续验证调用_不崩且正确`
  （`rc=3221225725` / `rc=4294967295`）、`test_T6a_正则文本模块_原生腿.py::test_正则_验证函数_完整20次`、
  `test_正则_验证函数_2_URL_IP`。→ 与本机定因的 A 条**完全同签名**。
- mac ×2 的 `Unit Tests` failure 里有 B/C/D 六条 nodeid（IPv4 三条 + 回溯写回 + L182 写JSON），
  形态全是**结果错**（无崩溃）。→ 与卡面说法一致，但**那是 mac、不是 win**。
- ubuntu ×4 全绿。

**本卡提交时 main 上还没有含本次修复的 run**（卡面明说「worker 提交时 main 还没这轮
run，塞进 verify 必红」），所以「终审六条消失」这条**必须由主控 land 后重跑 CI 才能验**，
我这边无法自证。**能自证的是：本机 Windows 上六条 nodeid 对应的用例全部绿，且两条反跑都有牙。**

---

## 五、假绿条件（卡面要求逐条写进说明）

- **ubuntu 上绿推不出 Windows 上不崩**：A 条只在 Windows 崩（PE 默认栈 1MB vs POSIX 8MB）。
  本卡所有反跑都在 Windows 上做，POSIX 上摘 pragma 无变化。
- **`continue-on-error` 会把 job 报成 success，真实信号在 step 级**：我拉的是 `steps[]`，
  windows ×4 的 `Unit Tests`(step 7) 是 `failure`，整 job 也报 `failure`，一致，无掩盖。
- **`gh run list` 不带 `-w CI` 会取到别的 workflow**：我直接用 `gh run view --job <id>` 拉指定 job，
  没有走 `run list`，不存在取错 workflow。
- **本机绿不能当判据**：卡面说本机（FreeBSD）本来就绿、A/B/C/D 在 Linux/FreeBSD 不重现。
  **这条与实测不符**——本机是 **Windows 11**，A 条在本机 100% 重现（`0xC00000FD`），
  所以本机（Windows）反而是 A 条的有效取证环境。C/D 在本机绿 / skip，已在第三节说明。
- **没有把任何用例改成 `pytest.skip`**：一条都没改（D 的 skipif 是既有代码，不是我加的）。
- **没有把这 4 条并进 `tests/ci_baseline_failures.txt`**：未触碰该文件。

---

## 六、改动清单（全部在 paths 内）

| 文件 | 改动 | 为什么 |
|---|---|---|
| `src/llvm/runtime_typed.c` | +17 行：Windows 段 `#pragma comment(linker, "/STACK:8388608")` + 根因注释 | A 条根因（栈溢出） |
| `tests/unit/test_relight_engine_O0.py` | `_编译并运行` 传 `env=`（PYTHONUTF8/PYTHONIOENCODING 对齐 CI） | B 条判据口径 |
| `tests/unit/test_T6a_正则文本模块_原生腿.py` | 同上 | 同上（该文件也在 paths，CI 上同样红） |
| `docs/known_issues.md` | 新增 `T6A-11b` 条目 | 把「0xC00000FD 栈溢出 ≠ T6A-11 的 0xC0000374 堆损坏」钉在文档里，免得下次又被当成堆损坏复发 |

**未触碰**：`stdlib/re.light`、`stdlib/模板.light`、`codegen_typed.py`、
`test_codegen_ref_dict_O0.py`、`test_R140_L182_L191_原生腿.py`（本机已绿，无改动必要）；
`_t6a_native_helper.py`（不在 paths，改过验证有效后已回退）。
未写任何 token / 密钥 / IP 到源码或本文档。

---

## 七、遗留（本卡不做，建议另立卡）

1. **re.light 回溯 VM 仍是真递归**，深度随模式长度线性增长。8MB 只是把 Windows 拉到
   POSIX 口径，**极端长模式仍会吃穿**。根治 = 把 `re_内部_跑` 的递归回溯改成显式
   回点栈（VM 重写），量级与本卡不匹配。
2. **C / D 的真红只在 mac ×2**，需要 mac 侧环境取证（本机 Windows 无法复现）。
3. `test_正则_提取与替换` / `test_正则_标志_忽略大小写_多行_点号` 等 mac 侧失败属
   **编码族**（卡面已划给 T-0250），本机 17 passed 全绿，未碰。

---

## 八、耗时与状态

- 约 2h，超过卡面 60min 软要求——主要花在「把 0xC00000FD 与 0xC0000374 分开取证」
  和「B 到底是引擎错还是解码错」的二分上。两条根因都拿到了决定性实验
  （栈尺寸扫描 / 字节级对比），不是猜的。
- 状态：**两条 verify 在本机 Windows 全绿；GitHub 终审待主控 land 后重跑**。
