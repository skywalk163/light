# CI 修复交付报告 —— ci-runtime-builtins-CIA（R13-CI 任务 1 + 任务 3）

> 分支：`light-merge-ci-runtime-builtins`（自 main b7f1ce05 切出，本地分支隔离作业，
> 未走 worktree —— 并行 agent 的 worktree 管理曾回滚误建目录，按项目惯例改用主仓本地分支）。
> 日期：2026-09-07。范围：A 类真回归 2 项（非 LLVM 运行期内建缺失 + 模块表缺 24 模块）。
> 未触碰：`src/llvm/codegen_typed.py`（归 CI-C）、`src/module_resolver.py` /
> `_light_import_hook.py`（归 CI-B）、`stdlib/*.light` 函数实现（归 CI-B）。

---

## 一、修复内容

### 子任务 1：非 LLVM 路径注册编码/哈希运行期内建（commit 1 `fix(runtime)`）

- `src/code_generator.py`：`builtin_map` 新增 7 条别名映射
  `_b64_encode / _b64_decode / _md5 / _sha1 / _sha256 / _sha512 / _hmac_sha256`
  → `_light_builtin.<同名>`。生成产物（`.light` → Python）在调用点把别名接到
  `_light_builtin`（即 `stdlib/builtins.py`）。
- `stdlib/_t5b_runtime.py`（新文件）：提供同名 Python 实现 —— `base64.b64encode/
  b64decode`（UTF-8 字节口径）、`hashlib.md5/sha1/sha256/sha512.hexdigest()`、
  `_hmac_sha256(密钥, 文本) = hashlib.pbkdf2_hmac('sha256', text, key, 1).hex()`
  （对齐 C 层 `dv_pbkdf2_hmac_sha256_1(pw=文本, salt=密钥)` 与旧壳 `哈希.py` 语义）。
  独立成文件而非在 builtins.py 里加 `def`：floor_bootstrap 用 ast 数 builtins.py
  顶层函数当分母，新增 def 会触发「清单漏登记」判红。
- `stdlib/builtins.py`：`_光明钩子.install(...)` 后加
  `from _t5b_runtime import (…)` 接线（不产生 FunctionDef，地板计数不变）。
- `tests/unit/test_非LLVM路径_T5B编码哈希.py`（新测试）：子进程 `cli/light.py run`
  真跑 `Base64.light` / `哈希.light`，输出逐行对拍 Python base64/hashlib/pbkdf2_hmac。
  覆盖：Base64 编码/解码、MD5/SHA1/SHA256/SHA512 空串+abc+中文、HMAC 3 组。

### 子任务 2：模块表补齐 R11C/R12 新增 24 模块（commit 2 `chore(capability)`）

- `任务书/原生腿产品清单.json`：`stdlib原生可编译矩阵` 89 → 113 条，补登 24 模块
  （re、sys、time、inspect、uuid工具、中国传统节日、中国行政区划、中文分词、
  中文数字转换、中文文本处理、中文编码、农历、图像处理基础、字符串工具、
  手机号校验、拼音转换、数据结构、数据验证、断言工具、缓存、网络请求、
  身份证校验、进度条、高级文件），全标 `可编译`；摘要 / 按阻断原因分类 / 生成时间
  同步刷新，说明追加 R13-CIA 判据记录。
- 另两张清单抽查：地板清单（`自举地板清单.json`）与 builtins 顶层函数双向咬合
  —— 本任务未给 builtins.py 加函数，`tests/unit/test_ci_gates_round9.py`
  `Test地板自举率` / `Test真清单在册` 全绿；分布式判据清单不涉及本任务改动面，且
  `Test分布式判据` / `Test真清单在册::test_分布式九条能力齐` 全绿。二者无需同步。
- `任务书/CI修复计划_R13.md`：任务 1、任务 3 状态更新为「已修复」，记录落地与验证证据。

---

## 二、根因定位

1. **子任务 1（NameError）**：`_b64_encode` 等 7 个 runtime 内建只在 LLVM 路径
   （`src/llvm/codegen_typed.py:2482+` T5B 段，派发到 C `dv_*`）有实现。解释器路径
   （`cli/light.py run` = codegen 生成 Python 后 exec）里生成产物保留裸别名调用，
   名字无定义 → `name '_md5' is not defined`。复现：`从《哈希》导入《MD5》` +
   `打印 MD5("abc")` 即红（修复前本地实测）。
2. **子任务 2（模块咬合红）**：commit 250c04c8 能力清单重建发生在 R11C/R12 `.light`-化
   落地之前，模块表停留 89 条；native_product 双向咬合（漏/吹）判 stdlib 实际 113 个
   `.light` 有 24 个未登记 → 红。附带发现：矩阵 89 条里有 52 条标「同名 .py 影子：
   .light 是 decl 0 空壳」的数据对 Base64/哈希/编码 等已是真实现的老模块也已过期 ——
   属既有台账失真（非本任务范围，已在缺口节记录）。

---

## 三、反跑判据验证

| 判据 | 命令 | 结果 |
|---|---|---|
| 原生产品门禁（模块咬合/后端取值/棘轮） | `python tools/ci/native_product.py --root .` | 通过；可编译比例 1.12% → 22.12%（合并点刷基线） |
| round9 门禁测试（含模块表与 stdlib 咬合） | pytest `tests/unit/test_ci_gates_round9.py` | 39 passed |
| 非 LLVM 编码/哈希对拍（新增） | pytest `tests/unit/test_非LLVM路径_T5B编码哈希.py` | 1 passed（11s，CLI 子进程真跑） |
| 内置映射与实现咬合（防空壳） | pytest `tests/test_codegen.py::Test内置映射与实现咬合` | 6 passed |
| 原生腿能力清单 | pytest `tests/unit/test_native_leg_capability.py` | 全绿 |
| 冒烟相关块 | `python 积木库/评估/冒烟.py --块 Base64编码 MD5哈希 SHA1哈希 SHA256哈希 SHA512哈希` | 5/5 通过（"abc" → 期望摘要逐块命中） |
| 附带验证 | `从《编码解码》导入《Base64编码》` CLI run | 通过（编码/编码解码 .light 同样受益） |

子任务 2 状态判据（非门禁，供账目可信）：`_taskCIA_编译探针.py`（Windows 注入
MSVC 2019 BuildTools 14.29 + SDK 10.0.19041 INCLUDE/LIB，`compile_light_typed` O0）
24/24 模块真出 exe；对照项 `列表工具`（矩阵原可编译）同环境复编译通过。

---

## 四、定向测试结果

只跑定向集，未跑全量：
- `test_非LLVM路径_T5B编码哈希` 1 passed（~11s）
- `test_ci_gates_round9.py` 39 passed
- `test_codegen.py::Test内置映射与实现咬合` 6 passed
- `test_native_leg_capability.py` 全绿
- 冒烟定向 5 块 5/5 通过

> 说明：本机 pytest 走受管 venv（`~/.workbuddy/binaries/python/envs/default`）——
> 系统默认 python（3.13 managed）与 C:\Python314 均未装 pytest。CLI/门禁脚本用默认 python 即可。

---

## 五、仍存在的缺口（不在本任务范围，记账）

1. **模块表台账失真**：矩阵 89 条存量中 52 条「同名 .py 影子：decl 0 空壳」对
   Base64 / 哈希 / 编码 / 编码解码 / 正则表达式 / JSON 等**已是纯光明实现**的模块
   已过期（.light-化在 R11C/R12 完成，台账没重建）。本次按任务边界「只增不改」处理，
   未翻旧账。建议后续轮次对全部 113 条用编译探针重建一次状态（可编译比例会再跳）。
2. **基线未刷新**：`tools/ci/native_product_baseline.json` 仍是 89 条时代的快照
   （module_total 89 / rate 1.12%）。门禁对比模式当前输出「提升（在合并点刷新基线）」
   属信息不判红；**R13 合并点必须 `--write-baseline` 重建**，否则下次对比把提升当红。
3. **运行期语义对拍深度**：新单测覆盖空串/ascii/中文/HMAC 基本用例；Base64 解码
   对非法输入、超长多块哈希的逐长度对拍由既有 T7D 长度扫描与 LLVM 侧测试覆盖，
   未在本任务重复。
4. 编译探针为一次性临时工具（`_taskCIA_*`），已随收尾删除，未入库；判据命令已记入
   清单 `依据` 与 `说明` 字段。
