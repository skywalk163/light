# T-0212 光明P1：写侧比读侧窄 —— 切片赋值不成立、dict 索引赋值不成立 [L-260/L-255]

## 做了什么

### 1. `src/parser_stmt.py`：赋值左值下标位置支持切片 + 容器 hop 构造成与读侧相同的 MemberAccess 链

- 新增 `_parse_index_or_slice_suffix()`：与读侧 parser_expr 的切片文法逐条对称
  （[起:止:步] / [起:止] / [起:] / [:止]，缺省起补 NumberLiteral(0)，A9-S2 口径）。
  接入五处赋值左值下标位置：`_parse_self_assignment` 索引后缀、
  `_parse_assignment_stmt` 成员链索引后缀、裸下标分支（含链式）、
  `_parse_set_stmt` 属性+索引分支、`_parse_set_stmt` 裸索引分支。
- L-255：`设 包.列[0] 为 5` 的容器 hop（包.列）原先被烤进单个 Identifier
  （`full_name = name + '.' + attr`），写侧照名字发裸 `包.列[0] = 值`，dict 上
  AttributeError。现构造成与读侧完全相同的 MemberAccess 链。
- 同族顺手修：`设` 路径属性名收集支持多级点链（`设 包.内.列[0] 为 5` 原先撞「.」
  报「期望'为'或'等于'」）；`设 包.列 为 [9]`（无索引属性写）原先返回
  `VarDecl("包.列")` 同样发裸赋值，现返回 MemberAccess 目标的 Assignment
  （codegen 落 `_light_attr_set`，与裸赋值路径既有行为对齐）。

### 2. `src/code_generator.py`：补写侧对称 helper `_light_index_set` / `_light_slice_set`

- 产物头部新增两个 helper（紧挨 `_light_attr_set`）：
  `_light_index_set(对象, 键, 索引, 值)` 与 `_light_slice_set(对象, 键, 起, 止, 步, 值)`。
  容器 hop 走读侧同一把 `_light_attr_get`（dict → 键访问、类实例 → 原生属性），
  末跳在容器上做原生下标/切片赋值 —— dict / list / 类实例行为一致。
- 新增 `_try_emit_container_index_write()`：容器 hop 为属性（X.Y[...]）时发 helper；
  裸名/键下标（表[0]、包["键"][0]）走原有原生形态，产物逐字不变。
  切片界与读侧 L-080 用同一把 `_light_builtin.切片下标检查`（非整数明确中文报错）。
- `Assignment` 分支与 `_generate_indexed_assignment` 各挂一处调用，天然覆盖
  设/裸赋值/自赋值三条解析路径。

### 3. 新增 `tests/unit/test_LH38_下标与切片写.py`（34 用例）

- 验收矩阵（light run 真跑，走 `cli.light._run_src` 完整入口含 stdlib 地板）：
  list 单下标/切片、dict 键下标/点属性下标/点属性切片、类实例属性下标（存量不回退）、
  段落体内写 —— 全部断言输出值。
- 读-写对拍：先读后写再读，断言读写路径拿到同一处（dict/list/类实例三容器）。
- 解析层：切片左值不报语法错（参数化 7 形态）；发射形态静态锚点（发
  `_light_index_set`/`_light_slice_set`、不发裸 `包.列[0] = 5`、产物含对称
  helper 定义、裸名下标产物不变）；读侧既有行为边界（切片读、属性读、增量赋值、
  方法调用语句不回退）。

## 验证（全部实跑，不是推演）

| 命令 | 结果 |
| --- | --- |
| `python3 -m pytest -q tests/unit/test_LH38_下标与切片写.py`（卡面验收命令） | **34 passed** |
| 修复前复现（stash 后基线）：`设 表[0:2] 为 [9,9]` → ParseError「期望 右方括号，但得到 冒号」、`设 包.列[0] 为 5` → AttributeError | 症状确认 |
| 定向回归：test_codegen_container_writeback_O0 / test_codegen_ref_dict_O0 / test_v34_syntax_sugar / test_v35_chained_call | **91 passed** |
| 核心链路：tests/test_codegen.py + test_A9_language.py + test_parser.py | **61 passed** |
| 全量 tests/unit（-n 0） | 78 failed / 5506 passed —— **78 红全部为既有基线**（stash 后基线复跑门禁批 14/14、原生腿批 44/44 与带改动完全同名同数；本机无 LLVM 工具链、Windows 无 grep 等环境因素） |

## 风险 / 边界（诚实声明）

1. `设 包["列"][0] 加为 1`（设 路径下标 + 增量动词）改前改后都报「期望'为'或'等于'」
   —— 该形态在存量里本就不支持（裸赋值路径 `包["列"][0] 加为 1` 一直通），
   不属于本卡范围，未顺手扩。
2. `_light_slice_set` 的步长分支带步切片语义与 Python 一致（`表[0:4:2] = [7,8]`
   → `[7,2,8,4]`），只加了长度不变的守门测试，非常规步长的替换语义未逐一钉。
3. 全量 78 红为既有基线（对比方法与逐条同名清单见上表），但**修复基线账本**
   `tests/ci_baseline_failures.txt` 不在本卡允许路径内，未动。
4. unified 后端（code_generator_unified.py）不在卡面允许路径内，未动；
   本卡语义落在 src 后端（卡面验收命令即跑 src 后端）。
