# 07-track-b · MiniBridge（Track B 落地件）

对应任务卡 **T-0361**、设计依据 `../06-design/评测方案修订版.md` §3。
规格见 [规格.md](规格.md) —— **自包含**，只读它就能复现全部实现。

## 30 秒验收

```sh
cd benchmarks/light-lang-bench/07-track-b

sh build.sh                                                    # 幂等；连跑两次结果一致
sh run_b1.sh tests/case_basic.ndjson | diff - tests/expected_b1.txt   # 必须无差异
sh run_b2.sh tests/case_basic.ndjson | diff - tests/expected_b1.txt   # 必须与 B1 逐字节相同
```

无参数则从 stdin 读：`printf '{"service":"hash","message":"x"}\n' | sh run_b1.sh`

## 本机实测结果

| 项 | 结果 |
|----|------|
| `build.sh` | 通过；连跑两次 `run_b1.sh` 输出一致（幂等） |
| B1（进程编排） | 与 `tests/expected_b1.txt` **逐字节一致** |
| B2（C FFI） | 与 B1 **逐字节一致**；`B2_status=ok`（**真实 FFI**，非降级） |
| 边界：坏句柄名 | `broken<TAB>ERR`，其余行正常，**退出码 0** |
| 边界：非法 JSON | 跳过 + stderr `WARN invalid_json index=3` / `index=5`，退出码 0 |
| handler 四向对拍 | 6 组输入 × 4 个实现面全过（`tests/selfcheck_handlers.sh`） |
| 结构判据 | `引 C:` 块只出现在 `mb_cffi.light`，块内无路由决策 |

## 文件分工（为什么拆成这么多文件）

路由决策、调用方式、FFI 三件事必须能各自独立审阅 —— 这是本卡的核心考点：
「路由与外部调用是否结构分离」。

| 文件 | 职责 | 有没有 `引 ...:` 块 |
|------|------|----------------------|
| `minibridge.light` | 主流程：读输入、切行、编号、错误分流、输出 | 没有 |
| `mb_路由.light` | `route.conf` 解析 + 查表 + 默认分支（**路由决策全在这里**） | 没有 |
| `mb_进程.light` | B1：把一行交给外部进程，stderr/退出码 → `空`（下游映射成 `ERR`） | 没有 |
| `mb_cffi.light` | B2：C FFI 绑定 | **有，且只有这里有** |
| `mb_调度.light` | B1/B2 的唯一分叉点（只看模式，不看输入内容） | 没有 |

## B2 的形态：真实 FFI（不是降级）

本机 `cc` 与 `clang` 均存在（`gcc` 缺失，但光明 `引 C:` 的探测顺序是
`gcc → cc → clang`，命中 `cc`），因此 B2 走 **(a) 真实 FFI**：

```
mb_cffi.light 的 `引 C:` 块 → cc 编译 → .so → ctypes 直调 mb_fnv1a32
```

`B2_status=ok`，**未**使用 `blocked_no_c_compiler` 降级路径。

**用的哪一套 FFI 语法**（规格 §4.2 要求任务包指定一套，否则 Agent 会在两套之间反复试错）：
`引 C:` 块。另一套 `加载库 "x.so" 为 别名。外部 段落 ... 在 别名。` 在本地也实测可用
（记录见下），但本卡**刻意不用**，以消除「语法选择成本」污染 L4 引用成功率。

<details>
<summary>实测记录：另一套 `加载库` 语法也可用（仅供存档，本卡不用）</summary>

```
加载库 "handlers/libh_c_hash.so" 为 哈希库。
外部 段落 预编译哈希 为 "mb_fnv1a32" 接收 文本: 文本 返回 长整数 在 哈希库。
印(预编译哈希("abc".编码("utf-8")) 位与 4294967295)     # → 88168267
```

注意 `返回 长整数` 必须写 `长整数`：`整数` 映射到 ctypes `c_int`（32 位有符号），
会把 64 位返回值截断成负数。这是「ctypes 类型边界」问题的典型样例，
按修订版 §1.4 应单独分桶，不计入光明语言本身的失败。
</details>

## 一致性防线：为什么需要四向对拍

`引 C:` 块里的 C 文本与 `handlers/h_c_hash.c` 是**两个物理副本**，天然会漂移；
一旦漂移，「B1 与 B2 逐字节相同」就可能变成「两条一样错的结果」。

`tests/selfcheck_handlers.sh`（`build.sh` 自动调用，失败即红）把这些面全部拉齐：

1. `handlers/h_c_hash` —— C 可执行文件（B1 用）
2. `handlers/libh_c_hash.so` —— C 共享库
3. 从 `mb_cffi.light` **抽出 `引 C:` 块现场编译**的 .so（B2 用）
4. 一份**独立重写**的 Python 参照实现（防「三份错得一样」）

6 组输入覆盖：纯 ASCII / 中文（UTF-8 多字节）/ 长输入（跨 32 位符号位）/ 单字节。

## 无 C 编译器时的行为（规格 §4.2(b) 降级）

```sh
env PATH=<只有 python3/sh/go 的 PATH> sh build.sh    # → B2_status=blocked_no_c_compiler
env PATH=<同上> sh run_b2.sh tests/case_basic.ndjson
# SKIP: no C compiler
# B2_status=blocked_no_c_compiler   ← 退出码 0，不算失败
```

已实测：该降级路径退出码 0，且**不会**用 Python/Go 冒充 C（规格 §4.2 第 3 条）。
此时报告必须记 `environment_blocked`，B2 结论不计入 L4 引用成功率。

## 构建产物（不入库）

见 `.gitignore`：`.build/`、`handlers/h_c_hash`、`handlers/libh_c_hash.so`、
`handlers/h_go_len/h_go_len`、`out.log`。全部由 `build.sh` 生成，且只落在本目录内。

## 已知限制

1. **B2 结论只对 `light v0.4.2` + 本次 commit 成立**；`引 C:` 需现场编译，
   不同机器/编译器版本的结论不可外推。
2. `h_py_append` 的累计计数依赖当前工作目录下的 `out.log`；判据要求在
   `07-track-b` 下运行（`run_b1.sh` 已 `cd` 到脚本目录，不受调用方 cwd 影响）。
3. `h_go_len` 的字节数按 **UTF-8 字节**计（中文 3 字节），不是字符数 ——
   这是刻意选择，与 `h_c_hash` 的「按字节」口径保持一致。
4. C handler 单行上限 1 MiB（`MB_CLI_MAX`）；超出会截断。这是 CLI 形态的
   工程取舍，不影响 B2（B2 的 FFI 形态没有这个上限）。
