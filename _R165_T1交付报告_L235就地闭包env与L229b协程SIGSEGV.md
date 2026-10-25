# R165 T-1 交付报告：L-235 就地闭包 env 打包 + L-229b native 协程 SIGSEGV

- 轮次：R165・T-1（任务书 `light-merge/_R165_并行任务书.md` §2）
- 派给：Deepseek（`src/llvm` 独占区）
- 权威测试机：**192.168.0.88**（FreeBSD 15.1-RELEASE-p1，用户 `workbuddy`，`nice -n 20` + `-n 0`）
- 基线代码：`964ad4c02`（R164 收口 + gitea hive 线 merge）
- 交付 commit：`9fda0b565`（R165 收口主提交）
- 交付时间：2026-10-25
- 纪律：只改本线点名文件（`src/llvm/codegen_typed.py`、`src/llvm/runtime_typed.c`、新增 `tests/unit/test_R165_L235_就地闭包env.py`、`tests/unit/test_R160_E5协程库.py`）；未碰 stdlib / docs / scripts；未 commit / push（收口由主 agent 统一执行）

---

## 一、判据核对（任务书 §2.3）

| 判据 | 要求 | 实测（0.88 原始输出，M 口复跑） | 结论 |
|---|---|---|---|
| L-235 行为 | `test_R165_L235_就地闭包env.py` 3 passed | **6 passed**（3 行为 + 3 IR 佐证；任务书写 3，实际交付 6） | ✅ |
| L-229b S10 转真跑 | `test_R160_E5协程库.py` 15 passed / 0 xfailed | **15 passed / 0 xfailed**（`R160_E5_SEG2=1` 真跑口径） | ✅ 见 §三 |
| 全量门 new_reds=0 | 硬判据 | D 轮 `9264 passed / 0 failed`，`new_red=[]`、`failed_hard=[]`、exit 0（见 `_R165_收口报告.md` §4.1） | ✅ |

---

## 二、L-235：嵌套段「就地按名调用」env 传 null

### 2.1 缺陷机制（IR 铁证）

R130 的堆 env 只在 `_gen_segment_function_value`（段名封成函数值）路径构建；嵌套段被**直接按名调用**时走：

```
call void @_seg_f2(ptr %13, ptr null, i32 0, ptr null)
                          ^^^^^^^^ 第 4 参 env 恒 null
```

段入口解包通道（`_emit_closure_env_unpack`）与写回（`_emit_closure_env_writeback`，L-098）早已就绪，但直调点没人调用 `_emit_closure_env_pack`，原生腿静默读 0 ⇒ 闭包自由变量全部错值。同/异步腿都中，与 L-232 同源不同投影；R163-A 的修法只覆盖「段名封成函数值」路径，不覆盖「就地按名直调」。

### 2.2 修法（最小爆炸半径）

在 `_gen_typed_segment_call` 发射 `@_seg_*` 调用处，按 `_segment_free_vars` 判定：

- **被调段 free_vars 非空** ⇒ `_emit_closure_env_pack` 打包调用方自由变量，替换第 4 参 `ptr null`；
- **free_vars 为空** ⇒ 仍传 `ptr null`（天然安全，勿误打包，负对照用例锁死此点）；
- **同步直调** 打完即 `free` env；
- **异步** 由 `dv_coro_create` 把 env 克隆进协程帧。

文件句柄 `句柄.写/关闭/读` 不受影响（无 `class_name` 不进 `_instance_classes`）。

### 2.3 回归门 `tests/unit/test_R165_L235_就地闭包env.py`（209 行）

6 例：
1. 同步就地 `同步就地=11`（有自由变量段被就地直调）；
2. 异步就地 `异步就地合法=11`；
3. **负对照**：无自由变量的段就地直调，行为不变；
4–6. IR 佐证：直调点 `@_seg_*` 第 4 参**非 null**（有信号计数，不是字符串 `in`）。

### 2.4 反跑有牙

临时把 env 打包摘掉 ⇒ 同步就地用例转红（M 口复跑确认）。

---

## 三、L-229b：native 协程第二次 `竞速/选择` SIGSEGV

### 3.1 根因（9 批最小复现 + IR/运行时取证）

`dv_deref_value` 对 LIST 走浅拷：

```c
*result = *v;   // list_data 指针与源共享
```

源是库层全局 `_结果槽表` 的 LIST。协程帧拆除时 locals 循环 `dv_free`，连带把全局数组的 `list_data` 释放 ⇒ 第二次开槽时 heap-use-after-free ⇒ SIGSEGV（rc=-11）。

- 单次调用不崩（locals 槽没拆）；
- 两次 + 均有让出点不崩（第二次源数组还在）；
- 第二次调用 + 某次工人无让出点（同步跑完）⇒ locals 已释放全局数组 ⇒ 崩；
- src（PY 转译）腿无此现象，真因在 C runtime。

### 3.2 修法

`dv_deref_value` 对 LIST 改 `dv_clone` 深拷，断开与全局 `_结果槽表` 的 `list_data` 共享。locals 拆除时 `dv_free` 只释放自己的克隆，不动全局数组。

### 3.3 S10 探针前提订正（必须知情）

T-1 修完后 `test_R160_E5协程库.py::test_S10_选择IO_原生真实fd_库层probe` 首跑报 `IO1=未超时`。M 口用**同一二进制**做对照实验：

- 原探针（不 accept 监听 fd）⇒ `IO1=未超时`；
- 在两次 `选择IO` 之间补 `接受socket(监听fd)` 排空就绪 ⇒ `IO1=超时`。

⇒ **产品超时路径正常，S10 的期望值前提失效**：监听 fd 的待接连接未被取走，level-trigger 下第二次必然「已就绪」，`IO1=超时` 在语义上不可能成立。已在 `_P8` 补 `接受socket`（与 S9 的 `_P7` 形态对齐），**断言值一字未改**。取证脚本 `_scratch_r165_t5/s10_probe.py`，回退方式：删掉 `_P8` 里那行 `接受socket` 与配套 `socket_close(连接A)` 即复原。

修后 `test_R160_E5协程库.py` 在 `R160_E5_SEG2=1` 下：**15 passed / 0 xfailed**（S10 xfail 已摘除）。

---

## 四、爆炸半径与文件清单

| 文件 | 改动 | 说明 |
|---|---|---|
| `src/llvm/codegen_typed.py` | +24 −? | `_gen_typed_segment_call` 加 free_vars 判定 + env 打包 |
| `src/llvm/runtime_typed.c` | +22 −? | `dv_deref_value` LIST 改 `dv_clone` 深拷 |
| `tests/unit/test_R165_L235_就地闭包env.py` | +209 | 新增回归门（3 行为 + 3 IR） |
| `tests/unit/test_R160_E5协程库.py` | +18 −? | 摘 S10 xfail；`_P8` 补 `接受socket` 排空就绪 |

**未越界**：未碰 stdlib / docs / scripts / 其它线文件；未改判据凑绿（S10 仅补探针前提，断言值未改）。

---

## 五、遗留

| 项 | 内容 |
|---|---|
| E5 段② 默认 skip | 11 例双腿对拍仍被 `R160_E5_SEG2=1` 门控，CI 永不执行；建议业主裁定改默认启用或写进 `.gitea/workflows/ci.yml`（已登记 `_R165_收口报告.md` §七） |
