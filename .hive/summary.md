# T-0203 交付摘要（workbuddyai-win）

**卡**：光明P2：22 条问题并入缺陷账 + 文档口径对齐 + 内置名存在性门禁 [台账]
**基点**：light `e1332f188`（= 三远端 main 之上已合入 T-0197/T-0198/T-0199 的树）
**验收**：`python3 -m pytest -q tests/unit/test_文档内置名存在性.py` → **13 passed**

## 交付物

| 文件 | 变更 |
|---|---|
| `docs/功能对标/语言缺陷账.md` | +210 行：新增 §二十五（22 条并入 + 复测总表 + 12 条六段式 + 10 条已验证修复 + 顺带发现 + 交接） |
| `docs/AI编程指南.md` | 判空三口径划清（`是空`/`皆空`/`长(x)==0`/`如果 x:`）；订正 6 处伪名/伪返回值 |
| `docs/空值语义规范.md` | §1 速查卡 + §2.1 矩阵加 `皆空` 列（实测值） |
| `docs/编号登记表.md` | 新增 §3.6 LH 族（22 token）+ §二总览一行 + 变更记录 |
| `src/compiler_cache.py` | 只加注释 + `缓存已禁用()`（`NO_CACHE`/`LIGHT_NO_CACHE`）+ 2 处 guard；**不改缓存逻辑** |
| `tests/unit/test_文档内置名存在性.py` | **新建**，13 例双层门禁（登记 + 运行时可达）+ 3 条反跑 |
| `tests/unit/test_LH21_未定义名.py` | `KNOWN_DOC_ERRORS` 清空（伪名已从文档删除），三条断言全部保留 |
| `_R168_T-0203交付报告.md` | 新建，含逐条实测原始输出与 A/B 取证 |

## 22 条实测（`e1332f188`，逐条真跑 CLI）

**已修 10**（LH-02/03/04/07/08/12/14/16/18/22）｜**部分 4**（LH-01/09/11/21）｜
**未修 7**（LH-05/06/10/15/17/19/20）｜**待观察 1**（LH-13）= 22

编号：活着的 12 条取 `L-240`~`L-251`；已修 10 条不占号（进「已验证修复」）。

## 关键发现（已写进账）

1. **假绿**：T-0194/T-0195/T-0200 在 hive 记「完成关闭」并写了 land commit（`7fac8d1`），
   但该 commit 在三个远端和本仓**都不存在**，`LH-06/10/17/19/20` 五条症状**逐条实测仍复现**。
   ⇒ 本账按实测登记为未修。
2. **能力在但用户摸不到**：`LH-09`/`LH-21` 的检查能力（E016/W016）已实现，但只在
   `python -m src.linter.cli --check-names` 里生效，`light check` 完全没接线 ⇒ 部分修复。
3. **登记表口径太宽**：`builtin_names()` 约 2900 条里约 2591 条是 lightpub **模块函数**（非地板内置名）。
   `临时目录` 是真实函数（须 `从 系统接口 导入`），裸调用 `NameError`，但登记表有意放宽 ⇒ E016 漏报。
   所以门禁用「登记 + 运行时可达」双闸，单闸都会被骗过（Python 内置名泄漏 / 登记表过宽）。
4. **既有红（非本卡）**：`test_doc_examples_gate::test_噪声类总数不许涨` 19 vs 18，
   已 A/B 实证（把本卡 4 个 doc 全回滚后单跑同一条，失败逐字相同）。

## 回归

- 新门禁 + `test_LH21_未定义名.py`：**31 passed**
- `test_LH08` + `test_LH22` + 新门禁：**59 passed**
- `test_compiler_cache` / `test_spec_docs_sync` / `test_R136_doc_profile` / `test_doc_examples_gate`：30 passed / 1 failed（既有红）
- `tests/test_缺陷账_L162_L169.py` + `test_R140_L182_L191_原生腿.py`：17 passed / 1 skipped

## 边界遵守

只改文档 + 测试；`src/` 仅 `compiler_cache.py` 加注释与开关（卡明确允许）。
未碰 `code_generator.py` / `parser_core.py` / `module_resolver.py`（后者需独立卡，已在 TODO 里点名）。
