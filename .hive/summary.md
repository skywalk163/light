# T-0241 · light 治 GitHub CI（sibling 缺失 9 条 + 真红约 10 条）

## 环境（本机复跑口径）

- worktree：`C:\Users\skywalk\.hive\wt\trae-win\T-0241`（base main @ 15c5f3d60，含 4be264311）
- 解释器：`g:\dswork\duan-light-merge\light-merge\.venv\Scripts\python.exe`（Python 3.13.14，
  已有 pytest 9.1.1 / xdist 3.8.0 / timeout 2.4.0 / lunardate / requests / cryptography / flask）
- sibling：`C:\Users\skywalk\.hive\wt\trae-win\lightharness` → 目录联接指向
  `g:\dswork\duan-light-merge\lightharness`（**仓外环境物，不进本仓改动**）
- 口径：`PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`、`--timeout=60/120`
- **平台差异警示**：上述全部是 Windows 结论。CI 的 Unit Tests 在 ubuntu 上跑；native 腿
  （R11C / llvm_stdlib_readiness）与 clang 相关的结论在 Windows 只算参考。

## 逐条定因（CI run 41289797116：12 failed + 7 errors = 19）

| # | nodeid | 签名 | 分类 | 依据（本机实测） | 处置 |
|---|---|---|---|---|---|
| 1-3 | `test_地板搬迁_判型_S2.py::test_字符判型对非字符串入参抛同型异常[是数字-*]` ×3 | DID NOT RAISE TypeError | **门禁漂移** | 真源/`内置核心判型.light` 的 `是数字` 自 T-0197（LH-08）改收任意值（int/float 判真、bool 判假、str 才走单字符 isdigit）；用例仍拿 `str.isdigit` 当 oracle，两条口径互斥 | 改用例（见下） |
| 4 | `test_native_leg_capability.py::test_内置函数清单与代码一致` | JSON 清单 vs `_gen_typed_builtin` 注册名不一致 | **门禁基线漂移（越界）** | `python scripts/gen_native_capability_json.py --check` rc=1：`builtin_functions.count` 落盘 594 vs 现算 595、缺条目 `用户参数`（另有 runtime_symbols note/category 22 处） | **越界**：需重生 `docs/原生腿能力清单.json`，paths 外 |
| 5 | `test_doc_examples_gate.py::test_噪声类总数不许涨` | 19 > 18 | **门禁基线漂移** | 新增噪声唯一条目 = `docs/T-0198_续行规则.md` hash `9bff193ddc56`（ANNOTATED）：那是**故意的反例块**（`设 甲 为\n 加上 "b"`，行尾带 `# 上一行没写完…` 注解），扫面本身没问题 | 刷新基线（生成器重生成，与手改逐字一致） |
| 6 | `test_link_libs_guard.py::test_测试里不许硬编码平台链接库` | `tests/unit/test_R13B_TLS_POSIX握手.py:200 -lm` | **真回归（测试侧）** | 护栏要求链接库判据只许一处（`tests/llvm运行时.取链接库参数()`）；该文件自己写死 `-lm`/`-lpthread` | 改测试（见下） |
| 7-8 | `test_LH01_时间算术.py::Test解析时间容错::{无效字符串返回空, 无效字符串指定格式返回空}` | ValueError | **门禁漂移** | `stdlib/时间管理.py:434-474` 已裁决：`解析时间` 失败**抛 ValueError**（不静默返回空），容错语义搬到新函数 `试解析时间`；用例断言的是旧口径 | 改用例（见下） |
| 9-15 | `test_builtins_drift.py` 7 条 | `FileNotFoundError: .../lightharness/stdlib/builtins.py` | **环境缺件** | 本机补 sibling 后 **7 条全绿**（boot 副本判据本不需要 sibling，是被 module 级 fixture 连坐成 ERROR） | 显式 skip（见下） |
| 16-17 | `test_LH34_中文关键字参数.py::{test_副本形参名全中文[lh], test_LH形参名与真源逐字相同}` | 同上 FileNotFoundError | **环境缺件** | 同上；补 sibling 后本机 2 条全绿 | 显式 skip（见下） |
| 18 | `test_原生腿_R11C_数据高级.py::Test高级文件::test_O0_复制文件_对拍` | `NotImplementedError: 未定义的模块点访问：原子写入` | **真回归（跨文件，越界）** | 本机独立复现（serial 371s，`1 failed, 28 passed`）。`stdlib/文件系统.light:137` 的 `原子写入` 体转发 `_light_builtin.原子写入`，原生后端不认这个模块点 → 整个 `文件系统` 模块被拒 → 任何从它导入的用例连坐 | **越界**：需改 `stdlib/文件系统.light` 或原生能力表，paths 外 |
| 19 | `test_llvm_stdlib_readiness.py::Test真编译下界::test_下界模块当场编过` | `SUBFAILED(模块="文件系统")`：桶=明确拒绝 | **真回归（跨文件，越界）** | 同上，同一条根因（本机 1366s 复现 `2 failed, 35 passed`） | 同上，越界 |

补充：**跨仓漂移（LH34 2 条）在本机补 sibling 后已消失**——主控此前环境里补完 sibling 后
仍红的 `test_builtins_drift` + `test_LH34` 3 条，在本机对当前 main @ 15c5f3d60 + sibling
（`2a94cf6` merge）全绿；结论按本机口径为准：**sibling 齐全时无跨仓 drift**。

无法归因：主控环境 40 failed 中另外 21 条签名未拿到，本机复现不出，**不猜**。

## 改动清单

1. `.github/workflows/ci.yml`
   - 新增步 `sibling lightharness 可用性（缺失则相关用例显式 skip）`：只检测
     `../lightharness/stdlib/builtins.py` 并把结论打进日志（缺失时发 `::notice`），**不 checkout sibling**。
   - 文件头「本项目当前没有 GitHub 远端、这棵树一次都没跑过」更正为真实事实（run 41289797116）。
2. `tests/unit/lightharness_sibling.py`（新增，92 行内）——`缺失原因()/缺失则skip()`：
   skip 的 reason 会出现在 SKIPPED 汇总与 CI 日志里（可见、非静默、非 collect error）。
3. `tests/unit/test_builtins_drift.py`——`copies` fixture 在 sibling 缺失时把 `lh_f` 置 None（原来直接
   `_read(LH_PATH)`，一处缺件连坐 boot 的 5 条判据成 ERROR）；`test_lh_*` 两条调 `缺失则skip`。
4. `tests/unit/test_LH34_中文关键字参数.py`——`test_副本形参名全中文[lh]` 与 `test_LH形参名与真源逐字相同`
   调 `缺失则skip`；boot 侧判据不受影响。
5. `tests/unit/test_地板搬迁_判型_S2.py`——`_oracle_是数字` 改为 T-0197 口径（bool 假 / int,float 真 /
   str 单字符 isdigit / 其余假）；`test_字符判型对非字符串入参抛同型异常` 收窄到 `严格字符串段落 =
   ("是字母","是空白")`，并写明为什么 `是数字` 不能在这条名单里。
6. `tests/unit/test_LH01_时间算术.py`——`解析时间` 失败改为断言 `pytest.raises(ValueError)`；新增
   `试解析时间` 两条（失败返回 None / 有效正常返回），容错语义仍有哨兵。
7. `tests/unit/test_R13B_TLS_POSIX握手.py`——探针编译参数里去掉硬编码 `-lm`/`-lpthread`，改
   `*取链接库参数()`（转调生产 `get_link_libs()`）；mbedTLS 三个库保留（探针独有）。
8. `tests/unit/doc_examples_baseline.json`——用生成器重生成（`tools/ci/run_with_memory_cap.py
   tools/ci/gen_doc_examples_baseline.py`，peak 8.5MB）：scanned 1041 / failing 20，仅新增上述反例块一条，
   无条目下线，噪声基线 18 → 19。

## 自检记录（分块复跑，PYTHONUTF8=1 / --timeout=60~120 / xdist 默认）

| 块 | 命令范围 | 结果 | 耗时 |
|---|---|---|---|
| A 修前基线 | 判型 + native_leg_capability + doc_gate + link_libs + LH01 + builtins_drift + LH34 | `8 failed, 804 passed` | 121s |
| B 修后定向 | 上表 1/5/6/7 的 7 个文件（含 R13B）+ builtins_drift + LH34 | `801 passed, 1 skipped`（skip = R13B 平台门） | 121s |
| C sibling 缺失模拟 | 临时删掉目录联接，只跑 builtins_drift + LH34 | `397 passed, 4 skipped`，SKIPPED reason 全文可见，**0 error** | 55s |
| D sibling 还原 | 同 C | `401 passed` | 55s |
| E 原生腿（越界项取证） | `test_原生腿_R11C_数据高级.py -n0`（`tests/unit` 全量在该文件上串行） | `1 failed, 28 passed`，371s；根因即 `原子写入` | 371s |
| F 原生腿 + LLVM 就绪 | 两文件同跑（`-n0`） | `2 failed, 35 passed, 8 subtests`；与 E 同一根因 | 1366s |

- 未做：`tests/unit/` 全量一次性跑（本机 xdist `loadscope` 在若干模块上会 fatal
  “Known limitations” 调度错误，改为 `--dist loadfile -n8` 后单次 >9.5 分钟被推到后台，
  未拿到干净汇总）。**E/F 已把剩余两条真红全覆盖**，A–D 覆盖了全部本次改动面。
- YAML 解析：`yaml.safe_load` 通过，jobs = test / lint / build / exe。
- `python scripts/gen_native_capability_json.py --check`：rc=1（见上表 #4，越界项取证）。


## 未完成 / 越界（需另开卡）

1. `docs/原生腿能力清单.json` 重生成（`scripts/gen_native_capability_json.py`），修
   `test_native_leg_capability.py::test_内置函数清单与代码一致`。
2. `stdlib/文件系统.light:137` 的 `原子写入` 原生口径（转发 `_light_builtin.原子写入` → 模块点访问失败），
   一处根因同时钉红 `test_原生腿_R11C_数据高级.py::Test高级文件::test_O0_复制文件_对拍` 与
   `test_llvm_stdlib_readiness.py::Test真编译下界::test_下界模块当场编过`。
3. `docs/T-0198_续行规则.md` 的 `9bff193ddc56` 块建议改标 ```text（已先以基线登记止血；
   文档体裁仍应由 docs 侧收拾）。
4. 主控 40 failed 里另外 21 条签名未提供，本机无法归因。

## `.gitea/workflows/ci.yml` 的 `|| true` 裁决建议

**先不收紧。** gitea 侧那条 `|| true` 不是判绿点，只是「崩溃也要把 junit 吐出来」的兜底，
真正的判据在随后的 `check_regression.py`，且 `tests/ci_baseline_failures.txt` 当前是
**0 条**（R165 重建后的既定状态）——即 unit 失败一律阻断，语义已经是硬判。此刻去动 shell 语义，
会在「同一份代码两种结论」的风险上白付一次改动。建议改为在 gitea 侧加一条**基线必须为空**的
守卫（0 条即等价硬判，不需要动 `|| true`），等 GitHub 侧这 3 条越界红清完后再评估是否同步。
