# C2｜积木库 blocks 版本目录裁决

> 工作包 C §4-C2。结论：**三套 blocks 版本均为活依赖，全部保留，不删除；归并收敛属 `src/` 所有权，延期由编译器组决策。**

## 1. 三版本规模（git ls-files 跟踪计数，稳定可复现）

| 版本目录 | 跟踪文件数 | 被 `src/` 编译器/测试引用位置 |
|---|---|---|
| `积木库/blocks/` | 14,222 | `src/lexer.py`（词法器加载积木数据） |
| `积木库/blocks_v4/` | 10,102 | `src/code_generator.py`、`tests/test_codegen.py` |
| `积木库/blocks_v5/` | 10,036 | `src/code_generator.py`、`src/parser_stmt.py`、`tests/test_feature_core_light.py`、`tests/unit/test_l0_char_aliases_paradigm_ac.py` |

- `blocks/` 文件数最多（14,222），是体积最大的批量导出。
- `blocks_v5/` 被引用处最多（9 处），且 `重建索引.py` 的 `路径` 解析**全部走 `blocks_v5/`** → `blocks_v5` 是索引重建的权威基底。

## 2. 索引契约与 blocks 的关系

- `积木库/索引.json`（v0.1.0，182 条契约）的 `路径` 字段解析分布（见 C3 校验）：**150 条命中顶层领域目录**（`数据/求和.light` 等），**29 条仅在 `blocks_v5/` 可解析**，**3 条仅在 `blocks_v4/` 可解析**，`blocks/` 命中 0。
- 即：契约**主体**消费顶层领域目录，但有 **32/182 条（≈17.6%）实际依赖 `blocks_v4/blocks_v5`**——删除这两套会直接令对应索引条目变孤儿。这与"三套均为活依赖、不可删"的结论一致且互相佐证。

## 3. 裁决结论与依据

总纲红线："不删被运行期/索引依赖的文件"；且 `src/**` 是 C 的**只读区**（所有权不相交）。实测三套 versions 均被 `src/` 编译器实时引用：

- 删 `blocks/` → 破坏 `src/lexer.py`（词法器数据缺失）。
- 删 `blocks_v4/` → 破坏 `src/code_generator.py` 与 `tests/test_codegen.py`。
- 删 `blocks_v5/` → 破坏 `src/code_generator.py` + `src/parser_stmt.py` + 多个测试，且 `重建索引.py` 无法解析路径。

**故三套均不可删。** 这与任务书"保留一个权威目录即可"的设想不同，但这是实测根因：压缩到一套需要改动 `src/` 的引用（属 A 包编译器所有权），非 C 可独立完成。

## 4. 建议（交付编译器组）

1. 以 `blocks/` 为合并目标（体积最大、领域最全），将 `blocks_v4/blocks_v5` 的差异块并入，并同步改 `src/` 三处引用。
2. 确认 `重建索引.py` 改指合并后的权威目录。
3. 完成后 `blocks_v4/blocks_v5` 方可归档（届时由 A 包或编译器组执行，C 不越界）。

## 5. 反跑判据与未实测项

- **反跑判据（C 视角）**：当前三套版本完整保留，`git grep` 显示 `src/` 三处引用仍可解析；契约 `索引.json` 与领域目录一一对应（见 C3 校验）。"删掉某版本立红"在 `src/` 侧可定位（即上述引用点），验证不删决策正确。
- **未实测**：`_冒烟工位.light` / `__组合测试.light` 冒烟佐证**未运行**——本 worktree 未 materialize `blocks*` 大目录（仅跟踪未检出），且运行 `.light` 需 Light 运行时 + harness。冒烟结论待编译器组在已检出环境/CI 复核。
- `_冒烟工位.light` 经排查**在本仓库从未被 git 跟踪**（任务书 §3.1 列为冒烟入口但快照中不存在），非 C 删除。
