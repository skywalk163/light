# 已知问题与技术债务清单

**版本**: v6.0.0  
**更新日期**: 2026-10-29  
**说明**: 本文档记录了光明 v6.0 中已知的问题、限制和技术债务，供开发者和用户参考。

---

## 一、严重问题

### P0 — 影响核心功能

- [x] **[P0] 自举编译器覆盖范围**：~~当前自举编译器覆盖了大部分语法，但极边缘特性（如复杂嵌套泛型）尚未完全自举。~~
  **第十轮 R10-6 评估结论：原描述「复杂嵌套泛型未自举」不成立，大量特性已由 src/ 权威解析器覆盖；实际未自举的是 3 条 API/解析缺口，已逐条列路与排期。**

  **第九轮 A9/C9 已消除的差距**（实测 `src/light_parser_v3.py` 逐一验证通过）：
  - 泛型类（`类 栈[T]:`）✅
  - 泛型函数（`段落 测试[T] 接收 表: 列表<T>:`）✅
  - 嵌套泛型（`列表<字典<文本, 列表<T>>>`）✅
  - 类型别名（`类型 映射[K, V] = 字典[K, V]。`）✅
  - 异步段落在类体内（`异步 段落 请求(网址):`）✅
  - 符号运算符（`+ - * / % == != < > <= >=`）✅
  - 无空格分词（`设x为10`）✅
  - 关键字别名（`若`/`返`/`遍`/`于` 等）✅
  - 列表推导 / 字典推导 / 集合推导 ✅
  - 切片表达式 / 元组字面量 ✅
  - match 语句 / 装饰器 / 接口定义 ✅
  - 复合赋值（`x 加等 5`）✅
  - 字符串插值（`f"你好 {名}"`）✅
  - break/continue（`跳出`/`跳过`）✅
  - `捕获 类型 as 变量`（含中文变量名）✅
  - inline-if 单行赋值（`如果 (cond): X 为 Y`）✅

  **仍未自举的 3 条缺口**（逐条差距与路线）：

  | # | 缺口 | 差距 | 自举路线 | 排期 |
  |---|---|---|---|---|
  | G1 | SemanticAnalyzer 与 ast_nodes_v3.Module 不兼容 | `SemanticAnalyzer.__init__` 期望 `ast_unified.Module`（有 `add_scope` 等方法），但 `light_parser_v3` 产出 `ast_nodes_v3.Module`（无此方法）；`test_semantic.py` 整体 skip，`cli/lightc.py` 和 `light6.py` 均跳过语义分析 | 统一 Module 类型：要么让 `ast_nodes_v3.Module` 补齐 `add_scope` 等接口，要么让 `SemanticAnalyzer` 改为接受 v3 Module；属架构重构 | v7.0 |
  | G2 | lambda 表达式不支持 | `lambda x: x+1`、`匿名(x): x+1`、`x => x+1` 三种语法形式均 FAIL（解析器在 `:` 处报「无法识别的语法元素」） | 在 `parser_expr.py` 新增 lambda 解析分支：识别 `匿名`/`lambda` 关键字 → 解析参数列表 → 期望 `:` → 解析体表达式 | v6.1 |
  | G3 | with 语句不支持 | `与 open("f") 为 f:` 和 `用 文件("f") 为 f:` 均 FAIL（`与`被标记为保留关键字但无解析路径） | 在 `parser_stmt.py` 新增 with 语句解析：识别 `与`/`用` 关键字 → 解析上下文表达式 → `为` 变量名 → `:` → 缩进块 | v6.1 |

  **自举率门禁验证**（`tools/ci/bootstrap_rate.py`）：
  - 文件维度自举率：37/89 = 41.57%（基线 40.48%，未倒退）✅
  - 关键路径自举率：18/18 = 100%（持平）✅
  - 影子数：53（持平）✅
  - 引 Python 逃逸：0（守住）✅

  **bootstrap/ 自举编译器状态**：`bootstrap/test_level6_full.py`、`test_level7_bootstrap.py` 等因运行时漂移（`列表插入` 等内置函数未定义）大面积红——这是 bootstrap 自举编译器与 src/ 权威解析器分叉的**结构表征**，非本轮引入。`bootstrap/test_new_features.py`（7 passed）和 `bootstrap/test_compiler_simple.py` 仍绿。bootstrap/ 目录的收敛清理属结构债务（见 `docs/C6_bootstrap结构核对.md`），排期 v7.0。

- [ ] **[P0] LLVM 后端标准库覆盖**：部分标准库函数在 LLVM 后端尚未完全实现，会回退到 Python 解释执行。
  - **影响**：使用 `--native` 编译时，部分标准库调用性能未达最优
  - **计划**：v6.1 中逐步补全
  - **R10-7 评估结论（T9 核对，2026-09-04）**：以 `任务书/原生腿产品清单.json` 为基准，逐模块真编译复现（`compile_light_typed` 真出 exe；空壳 `.light` 实现在同名 `.py`、原生腿不加载 `.py`，不计为可编译）。
    - 原生可编译比例 = **5 / 89 = 5.62%**（产品语义口径：非空壳且含真实实现且真出 exe），**远未达 ≥60% 目标**。非空壳模块 41 个中仅 5 个可编译（12.20%）。
    - 未达标阻断原因分类（分母 89，复现归类）：同名 `.py` 影子/空壳 **48**、依赖 Python 标准库 **19**（sys/os/re/socket/time/codecs/ctypes/asyncio/selectors，含原清单「导入影子依赖」2 个实际 import 标准库）、代码生成不支持 **13**（缺 `长`/`类型`/`str`/`连接路径`/`替换字符串` 等注册点）、导入 `.py` 实现 `NativeImportError` **4**（分布式 `节点网络` 纯 `.py` 边界）。
    - 自 B9 快照（2026-08-24）以来变化：5 模块改善（JSON编解码/中文NLP/内置核心字符串/断言工具轻量/格式化 由不可编译→可编译）；1 模块倒退（列表工具 由可编译→不可编译，原生腿缺 `类型` 注册点——清单已过期，须 B9 重建基线时重填）。
    - 处置（评估后决定，**本轮不补实现**）：按阻断分类交办对应泳道——同名 `.py` 影子 → 各模块 owner 真 `.light` 化；依赖 Python 标准库 → 纯光明重写 Python 内建模块；代码生成不支持 → A10/B10 补原生 codegen 注册点；`NativeImportError` → 分布式 `节点网络` 纯 `.light` 重写。
    - 证据：`任务书/原生腿可编译核对_T9.json`（逐模块结果 + 计数，T9 核对落盘；判据可复现：重跑核对脚本即得同结论）。
  - **R10-8 攻坚第一批进展（原生腿覆盖，2026-09-04）**：对「代码生成不支持」13 个模块逐一生根，落地首批编译器修复后 **5/89 → 12/89（13.48%）**，新增 6 个可编译模块：内置核心判型、内置核心转换、内置核心字典、列表工具、路径运算、操作系统。
    - 落地修复（`src/llvm/codegen_typed.py` + `src/llvm/runtime_typed.c`）：内建名补齐（`类型`/`str`/`替换字符串`/`转大写`/`转小写`/`开头`/`字符串重复`/`字符串包含`/`连接路径`/`分割字符串`/`列表排序`/`目录存在`，runtime 新增 `dv_path_join`）；异常类名直呼构造（stdlib 写 `抛出 运行时错误("…")` 裸类名调用）；**变量名与内置判型名重名歧义兜底**（`设 是浮点 为 假` 后 `如果 是浮点 == 真`，v3 把变量引用解析成无参 ParagraphCall，原生腿在 `_gen_typed_function_call` 按「已声明局部变量且无参」降级为变量引用）。
    - 剩余 7 个「代码生成不支持」模块阻断根因（供下一批）：**KeywordArg ×3**（JSON/JSON核心/内置核心列表——`打开文件(路径, "w", encoding="utf-8")` 关键字参数 + `表.sort(reverse=反向)`，需关键字参数支持 + 文件句柄对象/方法分派）；**TupleLiteral**（内置核心路径——`返回 (头, 尾)` 元组字面量，需元组类型）；**列表弹出**（数据结构轻量——`列表弹出(己.数据)` 变异函数需属性写回）；**YieldStmt**（文件流——生成器）；**目录名**（文件系统——需 dirname + 文件句柄）。
    - 验证：codegen 定向回归全绿（test_llvm_stmt_coverage 13 + test_native_leg_capability 11 + test_llvm_c3_expr 56）；`docs/原生腿能力清单.json` 已同步（builtin 290 / runtime 216 全量行号重算，能力单点测试通过）。
  - **R10-9 攻坚第二批进展（原生腿覆盖，2026-09-05）**：完成「变异函数属性写回 + `dv_list_pop`」，**12/89 → 13/89（14.61%）**，解锁 数据结构轻量（编译 + 运行语义）。
    - 落地修复：runtime 新增 `dv_list_pop`（index<0 弹末尾，复用 `dv_list_remove`）；builtin 新增 `列表弹出`/`list_pop`（注意**不注册** `弹出`/`pop`——会劫持 `栈.弹出()` 类方法调用，已踩坑）；函数式变异调用写回（`_gen_typed_function_call` 对 `列表弹出(己.数据)`/`列表插入(己.数据,0,x)` 等 mutating builtin 返回新列表后写回第一参数，`_persist_to_receiver` 字段/变量均覆盖）；`_recv_is_field` 扩展为放行无点局部变量（此前方法调用 `栈.追加(元素)` 对局部变量接收者不写回，跨调用累积丢失）。
    - **运行语义验证（真跑 exe）**：数据结构轻量 4 个类全部正确——栈 `s.压入/弹出`（`20 1 10 0`）、队列 `q.入队/出队` 带索引弹出（`1 1 2 0`）、双端队列 左/右出队（`7 8`）、优先队列 按优先级出队（`甲 乙 丙`）。
    - **架构缺口（重要，需单独排期）**：原生腿**段参数传值**，列表作为参数跨段变异传递不生效（转译腿=Python 引用，原生腿=值拷贝+共享底层数组，realloc 后调用方悬垂）。数据结构轻量的辅助函数版本（`创建栈/入栈/出栈/栈大小` 以列表为参数）编译通过但运行语义受此限制；**类版本**（`己.数据` 字段 + self 对象共享）不受影响，故 4 个类全部正确。跨段引用语义是原生腿架构级缺口，影响所有「列表参数跨段变异」代码，需专项评估。
    - 验证：能力清单同步（builtin 293 / runtime 217）；codegen 定向回归 143 全绿（stmt_coverage 13 + capability 24 + c3_expr 56 + stdlib_phase2/13）。

  - **R10-10 攻坚第三批进展（原生腿覆盖，2026-09-05）**：完成「KeywordArg 展开 + 文件句柄链」，**13/89 → 16/89（17.98%）**，解锁 JSON / JSON核心 / 内置核心列表（编译 + 运行语义）。
    - 落地修复（codegen/compiler/runtime 三侧）：
      - **KeywordArg 展开**：`ast_nodes` 新增 `KeywordArg`（ID=102）；`compiler._convert_keyword_arg`；`codegen` 函数/方法调用参数展开时分离位置参数与关键字参数，`_merge_kwargs` 按 `_BUILTIN_KWARGS` 签名表（打开文件/排序 的 encoding/reverse）或光明段 `parameters` 参数名映射回位置（stdlib `打开文件(路径, "w", encoding=...)`、`表.sort(reverse=...)` 用）。
      - **文件句柄链**：runtime 新增 `LV_TYPE_FILE`（type=22）：`dv_open_file`/`dv_file_write`/`dv_file_close`（fclose 后置 NULL 防双关）；codegen builtin `打开文件`/`write`/`close` 分支接线。
      - **try/catch IR 非法修复**：`catch` 体与 `finally` 体若已以 terminator 结束不再多发 `br`（此前重复发 br 生成非法 IR）。
      - **dict 遍历 0 次根因**：`遍历 项 之 对象` 改用 `dv_len`（dict/list/str 统一取长）+ 新 runtime `dv_foreach_get`（开头 `v = dv_deref(v)` 处理 dict 内数组 REF）。
      - **段优先于 builtin**：`_gen_typed_function_call` 分派顺序调整为「本地段 > builtin > 导入段」，对齐转译腿 Python 语义（用户定义段覆盖同名内置，修复 JSON核心 `段落 连接` 被 `连接`(dv_concat) 劫持）。
      - **type 名对齐**：`dv_get_type_name` 返回英文名（NoneType/int/float/str/list/bool/dict），REF（type=8）解引用一层返回底层类型名。
      - **段默认参数丢失**：`compiler._convert_paragraph/_convert_parameter` 补 `default_value`（新增 `_convert_default_value` helper）；codegen 缺参分支应用默认值（stdlib `缩进 = 0`/`美化 = 假` 等），无默认值才用 null。
      - **dict 索引赋值**：`_gen_typed_assignment` 新增 IndexAccess 分支（`dv_dict_set` 原地设置 + 写回目标变量防 realloc 悬垂）；**并修复 `_convert_indexed_assignment`**——v3 的 `设 映射[键] 为 值` 在段落内 target 是已解析的 IndexAccess 节点，原实现 `Identifier(name=node.target)` 把节点塞进 name 导致 `'IndexAccess' object has no attribute 'encode'`（内置核心字典回归根因），现对非字符串 target 直接 `self.convert`。
      - **方法内调方法崩溃**：runtime 所有 `dv_call_method`/`dv_call_class_method`/`dv_call_static_method`/接口调用在 `method(result,...)` 前加 `dv_null(result)` 初始化结果槽。
      - **JSON 数组内 null 三处 REF 根因（本批关键调试成果）**：
        ① `dv_foreach_get` 不 deref REF——dict 内数组经 `dv_dict_get` 取值是 REF，`遍历 项 之 对象` 元素全 null（`{"b":[1,2,3]}` → `[null,null,null]`）；
        ② 索引 REF 字符串 type 判断——dict 内字符串经索引取值是 REF，codegen load type 后 `icmp eq 3`(str) 失败误走 list 分支取到垃圾 `\u0000`（`{"c":"x"}` → `\u0000`）；runtime 新增 `dv_deref_value`（解引用并复制实际值），codegen 索引访问 obj_slot 后先 deref；
        ③ `dv_eq` 不 deref REF——dict 内 bool/null 与 `空` 比较失败（`序列化({"t":真,...})` 崩），`dv_eq` 开头加 `dv_deref` 解引用。
    - **运行语义验证（真跑 exe）**：JSON round-trip **12/12 全过**（顶层数组/对象、对象内数组、嵌套、深层嵌套、空对象/数组、字符串转义、中文、浮点、多数组、布尔/null）；文件句柄 打开/写入/关闭 冒烟通过；13 模块编译核对 OK 10（本批新增 JSON / JSON核心 / 内置核心列表）。
    - **修复的本批回归**：内置核心字典（`_convert_indexed_assignment` 的 IndexAccess target 处理）——R10-8 解锁模块因本批新增 dict 索引赋值分支暴露的适配层 bug，已修并回归通过。
    - 验证：能力清单全量重建（builtin 299 / runtime 222，evidence 行号重算）；定向回归 `test_native_import.py` 5 + `test_native_leg_capability` 11 + `test_native_cli.py` 35 全绿；JSON round-trip 12/12。

    - 剩余 FAIL 2（下一批）：文件流（YieldStmt 生成器）、文件系统（目录名未定义段落）。

  - **R10-11a 攻坚第四批A进展（原生腿覆盖，2026-09-05）**：完成「元组字面量 + 元组索引」，**16/89 → 17/89（19.10%）**，解锁 内置核心路径（编译 + 分割路径/分割扩展名 真跑对拍 posixpath）。
    - **阻断根因**：`stdlib/内置核心路径.light` 的 `分割路径`/`分割扩展名` 用 `返回 (头, 尾)` 返回元组字面量（TupleLiteral），`扩展名` 用 `二元[1]` 元组索引——原生腿 AstAdapter 无 TupleLiteral 转换器（被包成 `<unknown:TupleLiteral>`），codegen 无元组表达式分支。
    - 落地修复（codegen/compiler/runtime/ast 四侧）：
      - **ast_nodes.py**：新增 `AST_TYPE_ID_TUPLE_LITERAL = 103`；新增 `TupleLiteral` dataclass（`elements: list`，镜像 `ListLiteral`）。
      - **compiler.py**：`_node_converters` 注册 `'TupleLiteral': self._convert_tuple_literal`；`_convert_tuple_literal` 镜像 `_convert_list_literal`（递归转换 elements）。
      - **codegen_typed.py**：4 条 declare（`dv_tuple_new`/`dv_tuple_append`/`dv_tuple_get`/`dv_tuple_len`）；`_gen_expression` 新增 `isinstance(expr, ast.TupleLiteral)` 分派 → `_gen_typed_tuple_literal`（逐元素 append）；`_gen_typed_index_access` 新增 `is_tuple = icmp eq i32 {type_reg}, 23` 分支 → `dv_tuple_get`。
      - **runtime_typed.c**：`#define LV_TYPE_TUPLE 23`（文件头部）；`dv_len` 新增 `type==23` 分支（调 `dv_tuple_len`）；文件末尾追加 `dv_tuple_new`/`dv_tuple_append`/`dv_tuple_get`/`dv_tuple_len`（含 REF deref、容量扩容、元素克隆，对齐 R10-10 的 dict/字符串 REF 教训）。
    - **运行语义验证（真跑对拍）**：`分割路径`/`分割扩展名` 与 `posixpath.split`/`posixpath.splitext` 逐字符等价（覆盖空串、纯斜杠、前导点、`.a/b.c/d`、中文路径等 32 样本，diff EXIT=0，见 `tests/unit/test_地板搬迁_路径_S2.py`）。
    - **反跑验证**：破坏 `_gen_expression` 的 TupleLiteral 分派（`if False and isinstance(...)`）→ 编译立即报 `暂不支持表达式「TupleLiteral」`；恢复后编译通过。
    - **R10-11a 增量修复（rfind/rstrip/ends_with/str_repeat，主控 agent 评审追加）**：
      - **阻断根因**：`分割路径` 用 `路径.rfind("/")`、`头.rstrip("/")`、`头 == "/" * 长(头)`；`分割扩展名` 用 `路径.rfind(".")`、`结果.结尾("/")`——codegen `_gen_typed_builtin` 无 `rfind`/`rstrip`/`结尾` 分支（走 `dv_call_method` 静默返回 null），`*` 运算符对 STRING×INT 走 `dv_mul`（数值乘法）而非 `dv_str_repeat`（字符串重复）。
      - **codegen_typed.py 修复**：
        - 新增 `declare i64 @dv_str_rfind(ptr, ptr)` 和 `declare void @dv_str_rstrip(ptr, ptr, ptr)`；
        - `rfind`/`右查找`/`str_rfind` 分支 → `call i64 @dv_str_rfind`；
        - `rstrip`/`右去除`/`str_rstrip` 分支 → `call void @dv_str_rstrip`（无 chars 参数时传 null 默认剥空白）；
        - `结尾`/`endswith`/`ends_with`/`后缀是`/`以结尾` 分支（复用已有 `dv_str_ends_with` runtime）；
        - `_gen_typed_binary_op` 的 `*`/`乘` 分支新增 STRING×INT / INT×STRING 分派 → `dv_str_repeat`（在 arith_ops 数值路径之后、cmp_ops 之前）。
      - **runtime_typed.c 修复**：
        - `dv_str_rfind`：**补 REF deref**（`str = dv_deref(str); sub = dv_deref(sub);`——对齐 R10-10 的 dict/字符串 REF 教训，缺则 REF 传入时 `type != 3` 直接返回 -1）；**字节偏移→字符偏移转换**（`dv_substr` 按字符位置切片，rfind 返回字节偏移会导致中文路径索引错位——用 `dv_utf8_seq_len` 逐字符累计转换为字符偏移）；空子串返回 `dv_utf8_char_count(s)`（对齐 Python `"".rfind("") == 0` 的字符语义）。
        - `dv_str_rstrip`：从右往左剥指定字符集或空白（`strchr` 匹配字符集，`isspace` 匹配空白）。
      - **对拍验证**：32 样本（含 `中文/目录/文件.txt`、`目录/中文名.文本` 等中文路径）与 `posixpath.split`/`posixpath.splitext` 逐字符等价，`diff EXIT=0`。
    - 验证：能力清单同步（builtin 310 / runtime 228，全量 evidence 行号重算）；定向回归 `test_地板搬迁_路径_S2.py` + `test_native_leg_capability.py` 共 478 全绿。
    - **R10-11a 打回修复·查收（2026-09-05，主控 agent 独立验证）**：上一轮打回（内置核心路径多段组合段错误）的修复提交 `f598a7b2`（分支 `task-T4aR`）已查收，**部分生效、核心判据未达验收 → 继续打回待 A2**：
      - **生效部分**：修复在 `_gen_typed_method_call` 的类方法检查之后、builtin 检查之前新增模块段分派（`obj_name in self._imported_modules and method_name in self._segments` → 直接 `_gen_typed_segment_call`，不走 `dv_call_method`）。查收实测：模块级导入（`导入 内置核心路径` → `内置核心路径.分割路径/分割扩展名/扩展名/目录名`）4 段全调用输出正确（`a|b.c`/`x.tar|.gz`/`.gz`/`/a//b`）。
      - **未达验收（打回主因）**：核心反跑判据（**O0** 下选择导入 `从 内置核心路径 导入 分割路径 分割扩展名 扩展名 目录名` 全调用）在 `task-T4aR` 上**仍段错误**（rc=3221225477，崩溃偏移 0x56530 = memcpy/memmove 内访问无效内存）。**执行者测试用默认 `optimize_level=2`（O2）通过，未覆盖 O0；O0 是 `compile_light_typed` 合法参数（optimize_level=0），同样崩**。
      - **精确触发条件（O0 特有，主控二分定位）**：单段/任意 2 段/全量 6 段导入全过；**含「扩展名 + 目录名 + 任意第三段」的 3/4 段选择导入崩**（`分割路径+扩展名+目录名`、`分割扩展名+扩展名+目录名`、`分割路径+分割扩展名+扩展名+目录名` 均复现）；2 段 `扩展名+目录名`、3 段无扩展名（`分割路径+分割扩展名+目录名`）或无目录名（`分割路径+分割扩展名+扩展名`）均过。
      - **根因方向**：选择导入（跳过 stdlib 部分段）时编译产物存在**未初始化读取**（O0 保留错误指针传给 memcpy → 段错误；O1+ 优化消除未初始化读取 → 通过）。O0 与 O1+ 的合并 IR 段调用编号均正确（主段 `_seg_f5` → `_seg_f9/f10/f11/f7`），崩溃在段函数内部执行路径。
      - **A2 修复要求**：O0 下任意导入组合（含上述 3/4 段）不崩且输出正确；**反跑用例必须显式传 `optimize_level=0`**（否则被 O2 掩盖）；保留已生效的模块级导入分派修复；单/2 段/全量 6 段 O0 与模块级导入不回归。
    - **R10-11a 打回 A2 修复（2026-09-05，分支 `task-T4aR2`）**：O0 多段组合段错误已修复，定向测试 482 全绿（原 480 + 新增 4 O0 反跑）。
      - **根因**：`_gen_typed_segment_call`（L3118）和 `_gen_imported_segment_call`（L1362）分配 `result_slot = self._new_dv_slot()` 后**未 `dv_null` 初始化**。`_new_dv_slot` 来自复用型临时槽位池（不零初始化，L594 注释明确），段函数返回路径 `_emit_return_with_self_writeback` 调 `dv_obj_release_slot(result_ptr)` 释放旧值——O0 下残留垃圾被误判为 REF 指针 → `memcpy` 非法地址 → 段错误（rc=3221225477）。O1+ 优化消除未初始化读取故不崩。与 `_call_dv_func`（L690-695）已有的同模式修复一致。
      - **修复**（`src/llvm/codegen_typed.py`，+19 行）：① `_gen_typed_segment_call` 的 `result_slot` 后补 `call void @dv_null(ptr {result_slot})`；② `_gen_imported_segment_call` 同理补 `dv_null`；③ `_gen_typed_method_call` 补回模块级导入分派（`obj_name in self._imported_modules and method_name in self._segments` → `_gen_typed_segment_call`，来自 f598a7b2 未合入 main 的修复，一并补回防止模块级导入回归）。
      - **验证**：O0 下 4 段选择导入（`分割路径+分割扩展名+扩展名+目录名`）rc=0 输出 `a|b.c`/`x.tar|.gz`/`.gz`/`/a//b`；3 段 A（`分割路径+扩展名+目录名`）、3 段 B（`分割扩展名+扩展名+目录名`）均 rc=0；单段/2 段/6 段全量/模块级导入 O0 均不回归；O2 对照正常。能力清单 JSON 328 条 evidence 行号全量重算。


  - **R10-11b 攻坚进展（原生腿覆盖，2026-09-05，第四批B）**：完成原生腿**生成器（`YieldStmt`）**——文件流 模块最后一块编译阻断解除。
    - 落地修复：
      - `ast_nodes.py` 新增一等节点 `YieldStatement`（`AST_TYPE_ID_YIELD_STATEMENT=103`，字段 `value`/`is_from`）；`compiler.py::AstAdapter` 增加 `_convert_yield_stmt`（`生成 全部 X` 保留 `is_from=True` 供 codegen 显式拒绝，不静默降级成 `生成 X`）。
      - `codegen_typed.py`：含 `生成` 的段落整段生成**生成器状态机函数** `_genf_<名>(ptr %gen)`——entry 块按预扫到的生成点数一次造齐 `switch` 恢复落点，局部变量全部落在堆上槽数组（`dv_gen_slot`，跨 `ret void` 存活），`生成 表达式` 发射 `dv_gen_yield` + `ret void` + 恢复标签；`_seg_<名>` 包装段 `dv_gen_create` + 实参/默认值抄槽 + `dv_gen_make` 包成 LightValue（type=24）返回。`遍历` 消费路径对迭代对象做 `dv_is_generator` 分派：生成器走 `dv_gen_resume/dv_gen_value` 逐条拉取，列表/字符串/字典走既有 `dv_len+dv_foreach_get`，两条取值路径写同一个循环变量槽、共用一个循环体。
      - **两处 IR 正确性修复（本批调试成果）**：① entry 回插指令必须用**符号名寄存器**（`%gs.N`/`%ga.N`）——正文生成与 entry 回插在时刻上交错，数字寄存器「文本序 ≠ 编号序」，LLVM 文本解析报 `expected to be numbered '%N' or greater`；② `遍历` 的 list 路径 `len` 改走**内存槽 store/load**——`list_loop` 有回边来自共用的循环步进块（生成器路径静态可达），SSA 值过不去支配校验，store/load 不适用支配规则。
      - `runtime_typed.c` 新增生成器运行时（10 符号，TLS 段之前）：`dv_gen_create/free/slot/state/yield/finish/make/resume/value` + `dv_is_generator`。
    - **运行语义验证（真跑 exe，zig cc 工具链）**：状态机用例全对（while 内 yield 逐条产出、if-else 分支挂起恢复、`跳过` 后恢复、`返回` 提前结束生成）；`逐行` 同构程序真跑**逐字节 MATCH** Python `readlines`（含行尾换行保留、末行无换行不补、空文件），遍历次数与行数一致（4/3/0）。`stdlib/文件流.light` 原生腿编译通过（IR 46884 字符）。
    - 能力清单同步：`statement_nodes` 16→17（+`YieldStatement`），`runtime_symbols` 222→232（+10 生成器符号）；重生成脚本顺带修复**跨行 `if name in (...)` 名单漏抓**（异常类内置名 22 个曾因逐行正则被静默丢掉，现整段扫描 + 按名字定位行号）。
    - 验证：定向回归 31 全绿（file_stream 7 + stmt_coverage 13 + capability 11）；§9 未支持语句清单同步（上游 10→9、下游 16→17、实测分桶 17/5/2）。


    - 剩余 FAIL 3（下一批）：内置核心路径（TupleLiteral 元组字面量）、文件流（YieldStmt 生成器）、文件系统（目录名未定义段落）。
  - **R10-11c 攻坚第四批C进展（原生腿覆盖，2026-09-05）**：完成「文件系统句柄链 + `_light_builtin` 模块点访问转发」，**16/89 → 18/89（20.22%）**，解锁 文件系统（编译 + 运行全链）与 文件流（编译放行）。
    - 落地修复（`src/llvm/codegen_typed.py` + `src/llvm/runtime_typed.c`）：
      - **目录名（dirname）**：选 runtime 内置方案（非 段落）——runtime 新增 `dv_path_dirname`（POSIX dirname 语义，对齐 转译腿 `_light_builtin.目录名` = `os.path.dirname`），codegen builtin 注册 `目录名`/`dirname`/`path_dirname`。**理由**：转译腿本就映射到 `os.path.dirname`；`内置核心路径` 的 `段落 目录名` 逐字实现依赖 `.rfind`/字符串切片/字符串乘法/`.rstrip` 等原生腿尚未支持的方法，逐字同构会级联新阻断点；且与 R10-8 `连接路径`→`dv_path_join` 的既有路径函数模式一致。
      - **f.read() 文件句柄读取**：runtime 新增 `dv_file_read`（对齐 `dv_file_write` 的 LightValue* 输出模式：从当前文件位置读到 EOF，str 字段持 malloc 内容，失败置 null；handle 生命周期由 `dv_file_close` 置 NULL 防双关），codegen 文件句柄方法 `read`/`读取` 接线（与已支持的 write/close 同链）。
      - **`_light_builtin.XXX` 点访问转发**：`_gen_typed_method_call` 对 `_light_builtin` 模块点访问按名转发内置（不把模块名当接收者传参——此前会把第一个参数取成字符串 "_light_builtin"，删除文件等调用全部错位），对齐转译腿 `_light_builtin.删除文件`→`删除文件` 语义；覆盖 删除文件/文件大小/创建目录/目录存在/删除目录/列出目录/绝对路径/时间戳 等。
      - **路径/目录系统调用边界内置补齐**：runtime 新增 `dv_path_basename`（`文件名`/`basename`/`path_basename`）、`dv_abspath`（`绝对路径`/`abspath`/`abs_path`，相对路径基于 cwd 拼接 + normpath 规范化，含 Windows 盘符前缀处理）、`dv_makedirs`（`创建目录`/`mkdir`/`make_dir`/`makedirs`，`os.makedirs(path, exist_ok=True)` 逐级建父目录）；`删除目录`/`rmdir` 接线既有 `dv_rmdir`。
      - **YieldStmt 编译放行（必要使能，非生成器实现）**：文件系统 依赖 文件流（`从 文件流 导入 行列表`），多模块编译会连同 文件流 的 `逐行`（`生成`/YieldStmt）编译；原生腿尚无生成器实现（归 T4a/T4b），codegen 对 `<unknown:YieldStmt>/<unknown:YieldFromStmt>` 按 no-op 跳过，使 文件系统 全链可编译可运行。**注意**：文件流 的 `逐行` 生成器语义仍为占位（返回空），真实生成器实现归 T4a/T4b。
      - **打开文件 失败抛异常（对齐转译腿 Python open）**：`dv_open_file` fopen 失败不再静默返回 null，而是创建并抛出 `IOException`（FileNotFoundError 语义，经 `dv_create_exception_with_cause` + `dv_throw_exception`，前向声明置于文件句柄段；调用点位于 文件句柄 段、新增函数追加在文件末尾非 TLS 区域，未动 TLS/元组/生成器区域）。效果：`文件系统.文件存在` 的 `尝试/捕获 异常` 能接住打开失败并返回 假（此前对不存在文件返回 真）；`读取文件` 等无 try 的调用打开不存在文件时按未捕获异常打印并退出（对齐 Python 未捕获 FileNotFoundError）；`写入文件`/`追加文件`/`JSON` dump 等所有 `打开文件` 消费方语义对齐转译腿。
    - **运行语义验证（真跑 exe）**：文件系统 写入→读取→追加→删除 全链真跑正确（写入文件自动建父目录、`encoding="utf-8"` 关键字参数、`f.read()`、`_light_builtin` 转发）；`文件存在` 在删除文件后返回 **假**（打开失败抛异常 → 尝试/捕获 接住，本次修复核心）；目录操作冒烟通过（创建目录/目录存在/删除目录/文件列表/文件大小/绝对路径/获取文件名）；`目录名`/`获取文件名` 边界语义与 `os.path.dirname/basename` 一致（`"a/b/c"`→`a/b`、`"/"`→`/`、`"a"`→空、`"a/b/"`→`a/b`）。
    - **反跑判据验证**：移除 `目录名` 接线 → 文件系统 编译立即立红（未定义的段落：目录名）；移除 `read`/`读取` 接线 → 文件系统 编译通过但运行链路破坏（`f.read()` 走 `dv_call_method` 兜底，读取结果为空，`READ1=空`），编译/运行二选一立红均满足。
    - **已解决（原记录限制）**：此前记录「`文件系统.文件存在` 对不存在文件仍返回 真」已通过「打开文件 失败抛异常」修复（见上）——`文件存在` 现对已删除文件返回 **假**，删除验证可用 `文件存在`=假 或 `文件大小`=0 双指标确认。
    - 验证：能力清单同步（builtin 317 / runtime 227，evidence 行号重算）；定向回归 `test_native_import.py` 5 + `test_native_leg_capability` 11 全绿。
    - 剩余 FAIL 2（下一批）：内置核心路径（TupleLiteral 元组字面量）、文件流 的 `逐行` 生成器语义（T4a/T4b 实现真实生成器后补齐）。



---

## 二、高优先级问题

### P1 — 影响使用体验

- [x] **[P1] 异常捕获语法增强**：`捕获 类型 as 变量` 语法**已支持**（D3 复核确认）。
  - **证据**：`bootstrap/test_level6_full.py:304` 实跑 `捕获 值错误 as e`；语言规格文档亦写明该形式。
  - **原文档（「尚未支持」）属过期条目，D3-2026-08-23 更正**。
  - **影响**：无（能力已具备，无需 v6.1 计划项）

- [ ] **[P1] 减法运算符歧义处理**：在 `a-1` 这样的表达式中，`-` 可能被识别为负号前缀而非减法运算符。
  - **影响**：需要用户在 `-` 前后加空格以避免歧义
  - **计划**：v6.1 中修复

- [ ] **[P1] 大项目编译性能**：万行级大项目的首次编译时间仍然较长（无缓存时）。
  - **影响**：影响大型项目的开发体验
  - **计划**：v6.2 中进一步优化

- [ ] **[P1] Windows 路径兼容性**：部分标准库函数在 Windows 平台上的路径处理存在已知的边缘问题。
  - **影响**：Windows 用户在使用文件路径时需注意转义
  - **计划**：v6.1 中修复

---

## 三、中等优先级问题

### P2 — 影响健壮性

- [ ] **[P2] 缩进规范增强**：纯缩进语法要求严格的缩进对齐，混合制表符和空格可能导致解析错误。
  - **影响**：编辑器设置不一致时可能引发解析错误
  - **计划**：v6.2 中增加检测和自动修复

- [ ] **[P2] 编译错误信息增强**：部分错误信息仍不够友好，缺少详细的修复建议。
  - **影响**：新手用户可能难以定位问题
  - **计划**：持续改进

- [ ] **[P2] 包注册表高可用性**：当前包注册表服务器为单节点部署，无高可用保障。
  - **影响**：注册表不可用时包安装会失败
  - **计划**：v6.2 中增加镜像和缓存机制

- [ ] **[P2] 文档站点多语言支持**：当前文档仅提供中文版本。
  - **影响**：非中文用户使用门槛较高
  - **计划**：v6.2 中增加英文文档

---

## 四、低优先级问题

### P3 — 增强功能

- [ ] **[P3] 在线 Playground 移动端适配**：Playground 在移动设备上的布局和交互体验有待优化。
  - **影响**：移动设备用户使用不便
  - **计划**：v6.2 中优化

- [ ] **[P3] 调试器远程调试**：当前调试器仅支持本地调试，不支持远程调试。
  - **影响**：无法调试远程服务器上的光明程序
  - **计划**：v6.3 中实现

- [ ] **[P3] 代码覆盖率工具**：缺少内置的代码覆盖率分析工具。
  - **影响**：开发者需要借助外部工具进行覆盖率分析
  - **计划**：v6.3 中增加

- [ ] **[P3] VS Code 扩展主题适配**：部分语法高亮在深色/浅色主题切换时颜色显示不准确。
  - **影响**：视觉效果一致性不足
  - **计划**：v6.2 中修复

---

## 五、技术债务

### 代码质量

| 项目 | 描述 | 优先级 | 计划版本 |
|------|------|--------|---------|
| 自举代码可读性 | 自举生成的代码缺少注释，可读性较差 | P2 | v6.2 |
| 测试覆盖率 | 部分模块测试覆盖率不足 80% | P2 | 持续改进 |
| 类型注解覆盖 | 部分内部模块缺少类型注解 | P3 | v6.2 |
| 代码重复 | 词法分析器和解析器中存在少量代码重复 | P3 | v6.2 |

### 架构

| 项目 | 描述 | 优先级 | 计划版本 |
|------|------|--------|---------|
| 编译器前端/后端分离 | 当前编译器前端和后端耦合较紧，不利于独立演进 | P2 | v7.0 |
| 插件系统 | 缺少官方插件系统，扩展功能需要通过修改核心代码 | P3 | v7.0 |
| 统一错误处理框架 | 错误处理分散在多个模块中，缺少统一框架 | P2 | v6.2 |

### 文档

| 项目 | 描述 | 优先级 | 计划版本 |
|------|------|--------|---------|
| API 参考文档自动化 | API 文档部分内容需要手动维护 | P2 | v6.2 |
| 教程覆盖面 | 交互式教程仅覆盖基础语法，缺少高级主题 | P2 | v6.2 |
| 最佳实践指南 | 缺少光明最佳实践和设计模式文档 | P3 | v6.3 |

### 测试

| 项目 | 描述 | 优先级 | 计划版本 |
|------|------|--------|---------|
| 模糊测试 | 缺少对词法分析器和解析器的模糊测试 | P2 | v6.2 |
| 基准测试自动化 | 性能基准测试需要手动执行，未集成到 CI | P2 | v6.2 |
| 跨平台测试覆盖 | 部分边缘场景缺少跨平台测试覆盖 | P2 | v6.2 |

---

## 六、已关闭的问题

以下问题已在 v6.0 中解决：

| 问题 | 状态 | 解决版本 |
|------|------|---------|
| 自举编辑器缺少类型注解支持 | ✅ 已解决 | v6.0.0 |
| 自举编辑器缺少 P3 特性支持 | ✅ 已解决 | v6.0.0 |
| LLVM 后端仅支持部分标准库函数 | ✅ 部分解决 | v6.0.0 |
| VSCode 扩展功能不完整 | ✅ 已解决 | v6.0.0 |
| 文档站点内容陈旧 | ✅ 已解决 | v6.0.0 |
| 部分模块缺少光明侧接口 | ✅ 已解决 | v6.0.0 |

---

## 七、反馈渠道

如果你发现了本文档未列出的问题，请通过以下方式反馈：

- [GitHub Issues](https://github.com/light-lang/light/issues)
- 文档站点反馈页面

---

## 八、更新日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-10-29 | v6.0.0 | 初始版本，基于 v6.0 发布时的已知问题 |
| 2026-08-22 | 任务 A2 第二轮 | 新增第九节（原生后端未支持语句清单）、第十节（语言层本轮口径变更） |

---

## 九、原生（LLVM）后端未支持的语句类型清单

**口径**：这里说的「未支持」= 用 `python -m cli.light_unified compile`（原生/LLVM
后端）会**明确报错**。同一份源码走转译后端（`python -m cli.light_unified run`）
大多是正常的——两个后端的能力面不一样，不要互相推断。

改动前这份清单不存在，因为**根本报不出来**：`TypedLLVMCodeGen._gen_statement` 的
`isinstance` 链没有 `else`，不认识的语句被静默丢弃，编译成功、IR 生成、程序少干
一件事而无任何提示。本轮补了链尾兜底，并拆掉了上游 `AstAdapter` 的一层伪装
（无转换器的 v3 节点被包成 `ExpressionStatement(Identifier("<unknown:XXX>"))`，
在后端看起来是一条合法表达式语句）。

### 9.1 两个漏点的位置

| 层 | 位置 | 原行为 | 现行为 |
|----|------|--------|--------|
| 上游 | `src/compiler.py::AstAdapter.convert` | 无转换器 → 包成 `<unknown:XXX>` | 后端识破并报出原 v3 类型名 |
| 下游 | `src/llvm/codegen_typed.py::_gen_statement` | 链尾无 `else`，静默丢弃 | `NotImplementedError`，文案含类型名 + 指向转译后端 |

### 9.2 静态清单

上游（v3 语句类节点共 27 个，其中 **9 个**没有适配层转换器）：
`AssertStmt`、`DecoratorDefinition`、`EmbedBlock`、`FFIFunctionDecl`、
`FFIVarArgsDecl`、`PassStmt`、`RunAsyncStmt`、`ScopeDeclStmt`、
`TypeCheckToggleStmt`。（`YieldStmt` 自 R10-11b 起有转换器——见下方 17 条分支。）

下游（`_gen_statement` 现有 **17** 条分支：`VariableDeclaration`、`Assignment`、
`SelfAssignment`、`CompoundAssignment`、`IfStatement`、`ForeachStatement`、
`WhileStatement`、`ReturnStatement`、`BreakStatement`、`ContinueStatement`、
`PrintStatement`、`TryStatement`、`ThrowStatement`、`ExpressionStatement`、
`ImportStatement`、`AsyncScope`、`YieldStatement`（生成器，R10-11b 新增））。
适配层能产出、但这 17 条都不覆盖的 legacy
节点有 **27 种**，落链尾兜底，其中作为语句出现的主要是
`MatchStatement`、`WithStatement`、`DestructuringAssignment`、`SegmentDefinition`
（嵌套段落）、`InterfaceDefinition`、`MethodDefinition`、`AttributeDeclaration`。

**`ImportStatement` 已从 no-op 变为真导入（B9 S1 2.3 / 2026-08-24）**：`compile_light_typed`
检测到模块级导入即委托 `compile_light_project` 多模块编译（`compiler.py:459/_module_has_imports`），
`_process_imports`（`codegen_typed.py:767`）登记符号、`_gen_exported_aliases` 做 `{模块名}_{段落名}`
名字修饰；同名 `.py` 影子 / 纯 Python 模块显式抛 `NativeImportError`（`compiler.py:42`），
绝不静默产出一个跑起来就崩的 exe。判据见 `tests/test_native_import.py`，边界见
`docs/原生腿能力边界.md` §9。`_gen_statement` 里 `ImportStatement` 的 `pass` 是
「模块级导入已在上游处理」的语义留白，不再是静默无效。

### 9.3 实测分桶（24 条片段，`compile_source_typed` 直跑）

| 桶 | 条数 | 成员 |
|----|------|------|
| 能编 | 17 | 赋值/变量声明、`如果`、`遍历`、`当`、段落、`返回`、`跳出`、`继续`、`尝试`/`捕获`、`抛出`、`打印`、`引`（B9 S1 起真导入，见上方说明）、类（非嵌套）、接口、`导出`、`延迟`、`生成`（生成器，R10-11b 新增） |
| 明确拒绝 | 5 | `全局`(ScopeDeclStmt)、`外层`(先撞 SegmentDefinition)、`断言`(AssertStmt)、类型别名(TypeAlias)、嵌套类(ClassDefinitionWithNested) |
| 更早的层拦下 | 2 | `匹配`（v3 解析器语法就没通）、`异步域`（同上） |

`外层` 报的是 `SegmentDefinition` 而不是 `ScopeDeclStmt`：`外层` 只能写在嵌套
段落里，而**嵌套段落本身原生就不支持**，所以先被它拦下。报真正拦下它的那一层，
不编造。

守卫在 `tests/unit/test_llvm_stmt_coverage.py`（正跑 5 条 + 反跑 6 条 + 2 条静态
断言，共 13 个用例；`生成` 自 R10-11b 起从正跑挪入反跑）。

### 9.4 已知缺口

- **拒绝文案里没有源码行号**。`AstAdapter` 转换时不带 `lineno`，后端拿不到行号，
  文案里如实写成「源码行 未知（适配层未保留行号）」。要真给行号得改
  `src/compiler.py`（本轮范围之外）。

---

## 十、语言层本轮口径变更（任务 A2 第二轮）

| 项 | 口径 |
|----|------|
| `外层` / `全局` | 词法器可能把它们与后面的名字切成多个 token，作用域声明的识别改为按 token 跨度判定，不再依赖「整体成一个词」 |
| 异步原语 | `异步睡眠`/`限时`/`创建任务`/`并发等待`/`首个完成` 映射到 `asyncio` 对应函数，按需插 `import asyncio` |
| `异步读取文件`/`异步写入文件`/`异步追加文件` | **只有词法保护、没有实现**：整体仍成一个词，调用时报 `NameError` 指向完整名字。实现需要动 `stdlib/`，不在本轮范围 |
| 泛型 | 类 / 段落 / 类型别名的 `generic_params` 现在会产出 `TypeVar` + `Generic[T]`；段落只登记 `TypeVar`（`def f[T]` 要 3.12+） |
| 嵌套类 | 类体内允许 `类`，转译后端可用；原生后端明确拒绝（见 9.3） |
| 段落体内的延迟导入 | 缩进行的导入**不计入模块级依赖**，可用来打破环；顶格写的导入照旧算模块级依赖、照旧拒绝成环，没有绕过开关 |
| `?` 可空后缀 | **永不支持**。写 `设 甲: 整数? 为 无。` 报错并指向 `可空 整数` |
| `异步` 在表达式位置 | 一律**编译期拒绝**。凡是以 `异步` 开头又不在词法复合词表里的名字（`异步读取二进制`、用户自造的 `异步取数` 等）会被切成 `异步` + 余下部分，改动前静默编成 `await 异步` 加一条结果被丢弃的调用；现在报「`异步` 是修饰符」。`异步 段落`/`异步 遍历`/`异步 运行` 走语句层，不受影响 |
| `等待 <名字>` | 判据是**源码是否相邻**：`等待价值`（两 token 首尾相接）仍当一个名字，`等待 任务甲`（中间有空白）编成 `await 任务甲`。改动前后者被静默拼成不存在的名字 `等待任务甲` |

---

## 十一、第二轮合并期修掉的缺陷（2026-08-22）

这一节记的是合并主线时发现并**已修**的缺陷，都带真跑判据，勿再当新问题重复排查。

### 11.1 pytest 捕获流被收紧成 strict，全量跑连锁报错

`tests/test_summary.py`、`test_class_definition.py`、`test_comprehensive.py` 在模块顶层
调 `sys.stdout.reconfigure(encoding='utf-8')`——只给 `encoding` 会把 `errors` 一并重置回
`strict`，而 pytest 的 fd 捕获流本来是 `errors='replace'`。收紧后只要后面有用例往捕获流写进
非法字节，每次 setup/teardown 的 snap() 都抛 `UnicodeDecodeError`：实测
`pytest tests --ignore=tests/e2e` 出约 3565 个 ERROR、约 1780 条用例根本没真跑，而单独跑
那几个文件全绿——典型的顺序相关、单跑看不见的门禁污染。`PYTHONUTF8=1` 挡不住，
因为 `reconfigure` 的 strict errors 覆盖它。

修法：补回 `errors='replace'`，并加 AST 级护栏
`tests/unit/test_capture_encoding_guard.py`（谁再写出不带 `errors=` 的 `reconfigure` 立刻红；
用 AST 而非正则，因为正则会把注释与文档字符串里的示例也算成调用）。

### 11.2 Windows 上「引 C」整条链是死的

L4「引 C」发射器只发一条 GNU 风格命令 `-shared -fPIC -O2 ... -lm`。Windows 上 clang 的默认
target 是 msvc，`-fPIC` 是硬错误（`unsupported option '-fPIC' for target
'x86_64-pc-windows-msvc'`），去掉后 `-lm` 又让 lld-link 去找不存在的 `m.lib`。

修法：签名提取上移到编译之前并派生导出符号表，编译改成两条命令按**返回码**逐条回退，
第二条是 `-shared -O2 -o LIB -Wl,/EXPORT:<每个符号> SRC`（不写 .def）。两条都失败才报错，
报错带两次完整命令行与 stderr。判据 `test_c_真编译真调用_取值正确`：真编译真经 ctypes 调用，
`fact(5)==120`、`tri(2.5)≈7.5`。

### 11.3 文本级 IR 优化删 `br` 留标签，产出非法 IR

`optimizer_pipeline.py` 的 `_peephole_pass` 有一条
`re.sub(r'br label %(\w+)\s*\n\s*\1:', r'\1:')`，把无条件跳转删掉只留目标标签，前驱块因此
没有终结指令；`_merge_blocks_pass` 也不看目标标签有几个前驱。clang 的报错形态是在标签行上
`expected instruction opcode`，落点全是 `endif_2:` / `while_cond_1:` / `param_end_3:` 这类行。
代价是 `tests/test_p3_comprehensive.py` 15 条红。

修法：删掉那条不安全规则；`_merge_blocks_pass` 改为先算本函数内的标签引用计数
（覆盖 `br label`、条件 `br` 两个分支、switch 的 default 与每个 case 的单行/多行两种发射形态、
phi 的来源块），只有单前驱才合并，且此时 `br` 与标签行一起删。判据 8 条含两条反跑。

### 11.4 每帧约 96KB 的临时槽位池

`codegen_typed.py` 的 `_temp_slot_pool_size = 2048` 在 emit 时就写死进 alloca，
`LIGHTVALUE_STRUCT` 对齐后 48 字节 × 2048 ≈ 96KB/帧，递归深一点直接爆栈。

修法：延迟填数（`_begin_temp_slot_pool()` 发占位行 → `_emit_temp_slot_pool()` 按真实
`_temp_slot_index` 回填），4 处 alloca 走同一条路径；2048 保留为上限，溢出仍硬报错。
反跑取证：同一份 IR 把元素数改回 2048 → `rc=0xC00000FD STATUS_STACK_OVERFLOW`、stdout 空；
按真实用量 → stdout `20100`。

### 11.5 纯光明 `.light` 完全遮蔽同名 `.py`，能力倒退

`stdlib/_light_import_hook.py:141,155` 的规则是：同名 `.py` 存在时，只要 `.light` 首行带
「纯光明实现」魔数就用 `.light` **完全取代** `.py`——不是兜底。断言工具 / 数据结构 /
字符串工具 / 日期时间 四份 `.light` 都带了魔数，把 77 / 29 / 81 / 100+ 个导出的 `.py`
换成 9 / 14 / 28 / 11 个导出的 `.light`，且命名不兼容。代价：`test_stdlib_phase2.py`
三条红、`test_stdlib_phase9.py` 一整批取不到符号、`test_datetime.py` 曾变成 collection error。

修法：加「轻量」后缀独立成名（同 JSON → JSON编解码 的既有处置），原模块名仍由 `.py` 提供。
`stdlib/列表工具.light` 保留原名——它与 `.py` 导出名完全一致（各 10 个），遮蔽不丢能力。

### 11.6 测试里的跨机绝对路径与子进程编码

`tests/test_stdlib_phase9~13.py` 各自 `sys.path.insert` 了 `'c:/traework/light/stdlib'` /
`'c:/dumatework/light/{stdlib,contrib}'`——两种前缀混杂，都是别的机器上的路径，本机不存在，
整文件 ImportError。路径统一收到 `tests/conftest.py` 按 `__file__` 推导。
`积木库/评估/冒烟.py` 的 subprocess 只在父侧写了 `encoding='utf-8'`（解码端），子进程无 env，
Windows 下按 GBK 输出会被当成乱码误判成冒烟不通过；现钉 `PYTHONIOENCODING=utf-8`。

---

## 十二、发现但**未修**的旧缺陷（移交，勿重复排查）

### 12.1 原生（LLVM）后端的类方法整条是坏的

两个缺陷，均已取证为 `pre-merge-abcd` 就存在、不是第二轮引入：

- 双 `ret void`：类方法产出两条终结指令
- 槽位池别名：`%1` 被别名到 `@.str.26`

`tests/` 目录里**没有任何**「原生腿 + 类方法」的组合覆盖，所以门禁看不见它。
现有的类/方法用例走的都是转译腿。

> **已解决（R9 待补 / 2026-08-27，commit `17c08c8b`）**：实测复现后修掉三处环环相扣的 bug——
> ① 方法体末尾无条件 `ret void` 造成双重终结符 → LLVM IR 验证红（终结符发射移入
> `if not _ends_with_terminator` 分支）；② 解析器把「己」归一成 `Identifier('self')`
> 而方法内槽位键是「己」，裸 `self` 落到字符串常量，`dv_class_get_member/set_member`
> 拿字符串当对象，属性读写 0xC0000005（补 `_gen_typed_identifier` 的 `己` 槽位映射 +
> `_gen_typed_assignment` 写回）；③ `己.方法名(...)` 被拍平成 `SegmentName('self.方法名')`
> 未路由 `dv_call_method`（补 `_gen_self_method_call`）。判据 `tests/test_native_cli.py`
> `Test原生类与方法代码生成` 六条真跑回归（普通/泛型类方法带参、构造+属性、方法内调方法、
> 方法内只写属性）。

### 12.2 `cli/lightc.py` 对任何输入必崩

`SemanticAnalyzer()` 少传 `module` 参数 → `TypeError`。凡是文档/示例里写
`python cli/lightc.py <文件>` 的都会撞上（`examples/harness/M2_流式对话.light` 的使用说明
原先就是这么写的，已改为 `python cli/light.py run <文件>`）。
`tests/conftest.py` 的 `analyzer` fixture 是同一处签名不匹配，当前没有用例消费它，
所以门禁同样看不见。

> **已修复（2026-09-04）**：`cli/lightc.py` `LightCompiler.__init__` 移除无参
> `SemanticAnalyzer()` 构造，`compile()` 方法与 `light6.py` `_src_compile` 一致
> 跳过语义分析（`SemanticAnalyzer` 与 `ast_nodes_v3.Module` 尚不兼容，
> `test_semantic.py` 整体 skip）。`tests/conftest.py` `analyzer` fixture 改为
> 返回 `None` 并注明不可用。新增 `tests/test_lightc_cli.py` 5 条真跑用例
> （编译 rc=0 / `--run` 输出正确 / 反跑判据：改回无参构造即 5 failed）。

### 12.3 codegen_typed 的包装段不建自己的槽位池

`_gen_typed_method` / `_gen_async_segment` 既不建自己的池、也不重置 `_temp_slot_index`，
会沿用上一个函数残留的池寄存器——跨函数引用寄存器，IR 本来就不合法。现有链路碰不到
（类/方法用例全绿），但这是潜伏项。

> **已解决（R9 待补 / 2026-08-27，commit `17c08c8b`）**：`_gen_typed_method`（
> `codegen_typed.py:4062/4147`）与 `_gen_async_segment`（`:3722/3791`）都补了
> `_begin_temp_slot_pool()` 开局占位 + `_emit_temp_slot_pool()` 按真实用量回填，
> 与 `_gen_typed_segment` 同一路径。槽位池别名（`%1` 被别名到 `@.str.26`）随之消失。

### 12.4 `_inline_small_functions_pass` 过度激进

会把「指令数 ≤5 且被调用 ≤1 次」的非 main 函数整段删掉，不看是否还有其它引用形式。

> **已解决（T3 / 2026-09-04）**：`SizeOptimizer._inline_small_functions`（
> `src/llvm/size_optimizer.py`）删除前改为统计**全部**引用形式（直接调用 / 地址
> 取用 / 间接调用 / 全局与外部引用），定义行自身不算引用，只要存在任一引用即
> 保留；`main` / `__light_init` 一律不删；函数体定位改用按行扫（不再用会被行内
> 结构体类型截断、或 DOTALL 从头吞到尾的 `define ... \{[^}]*\}` 正则）。新增反跑
> 用例 `Test小函数清理_统计全部引用形式`（tests/test_llvm_optimizer.py）：被地址
> 引用 / 间接调用 / 直接调用的 ≤5 指令小函数必须保留、零引用仍清理、保留后的 IR
> 经 clang 编译链接后经函数指针真跑出 42。pipeline 侧
> `_drop_unreferenced_functions` 本就按文本全量引用计数、已覆盖地址引用，无需改动。

### 12.5 `stdlib/lightpub/__init__.py:45` 路由到仓库外的绝对路径

指向 `C:\dumatework\lightpub`，跨机器就断。

### 12.6 50 个整文件注释的伪代码 stdlib 模块

整个文件被注释掉、只剩形状，`stdlib/日期时间.light` 是其中之一（正因为没有魔数所以无害）。
待定方案是缩成「导出清单 + 显式 NotImplemented」，会影响自举率口径，未决。

---

## 十三、仓库债务登记（D3 本轮明文标注，2026-08-23）

第三轮 D3 复核盘点出的结构性债务。**只标注、不代修**（多数属 A2/A3 基础设施范围）。
代修需走对应任务，勿在 D3 里为求门禁通过而放宽判据或顺手改。

### 13.1 `llvm_backend.py` 名不副实（根目录）

根目录 `llvm_backend.py`（6302 字节）并不生成 IR，只是 `clang` 的命令行包装
（把光明源码喂给 clang 做原生编译）。名字暗示"后端"，实际是"编译器驱动壳"。
**影响**：后来者按名索骥会误判它产出 LLVM IR。**处置**：重命名为
`llvm_driver.py` 或在文件头补一行职责说明（代修走 A2/A3）。

### 13.2 两条 LLVM 代码生成路径并存

- 新：`src/llvm/`（codegen_typed.py 等），由 `cli/light.py:342/366` 经
  `from src.llvm.compiler import compile_light[_typed]` 调用。
- 旧：`antlrparser/llvm_codegen.py`（`LLVMCodeGen`），由 `src/compiler.py:1523`
  `from llvm_codegen import LLVMCodeGen` 调用。
两条路径被不同 CLI 分别拉起，行为面与维护状态不一致，是回归的高危分叉点。
**处置**：统一到 `src/llvm/`，废弃 `antlrparser/llvm_codegen.py`（代修走 A2/A3）。

### 13.3 `--target wasm` 的实际去向（需核实）

`cli/light_unified.py:1056` 的 `--target` 含 `wasm` 选项，且仓库存在
`src/wasm_target.py`（`compile_to_wasm`，支持 `pyodide` / `standalone` 两种模式）。
D3-7 任务书原称"--target wasm 静默生成 .py"——**当前代码看并非如此**（已有独立
wasm 实现）。该声称可能已过期，标记**待核实**：确认 `--target wasm` 是否仍有一条
静默回退 `.py` 的支路，若有则修，若无则更新任务书措辞。

### 13.4 `stdlib/lightpub/__init__.py:45` 路由到仓库外绝对路径

见 §12.5（已记录）。指向 `C:\dumatework\lightpub`，跨机器即断；其 `__index__.py`
还声明了本仓库不存在的模块。本轮 JSON 已用换名 `JSON编解码` 规避，不依赖 lightpub，
但该项属长期一致性债务，记入此处汇总。



## 十四、第四轮移交与债务（D4 本轮，2026-08-23）

### 14.1 15 处 `sys.stdout/stderr.reconfigure` 缺 `errors='replace'`（D4-5 普查，移交）

全仓 AST 普查：`reconfigure` 缺 `errors=` 的调用共 **15 处**，全在 D4 独占清单之外
（护栏 `tests/unit/test_capture_encoding_guard.py` 只扫 pytest 收集面 test_*/_test_*/conftest，
这些文件不在收集面内，护栏管不到）。风险分级：

- **高（模块顶层，CI 直接调）**：
  - `积木库/评估/ci_eval.py:53` —— gitea 积木库门禁直接 `python 积木库/评估/ci_eval.py --并发 8`，顶层 try/except 包裹
  - `积木库/评估/跑分.py:36` —— 跑分脚本顶层 try/except 包裹
- **中（函数体内，CLI 路径）**：`cli/light.py:1080`（`_ensure_utf8()`，AI Copilot 子命令）
- **低（工具链脚本函数体内）**：`tools/ai_copilot/` 下 12 处（build_sft_dataset.py:2203、
  build_sft_dataset_v10.py:1591、cli.py:119、diagnose_loss.py:169、download_model.py:144、
  local_infer.py:573、merge_and_convert.py:349、pipeline.py:444、prompt_generator.py:180、
  snippets.py:231、train_cpu_lora.py:546、train_gpu_lora.py:1038）

修复动作统一为 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`。
**先修 1、2 号**（模块顶层 + CI 判绿路径）。修完复查：`git grep "reconfigure(encoding"`。

### 14.2 `stdlib/列表工具.light` 第 1 行注释与事实不符（D4-2 核验发现）

`stdlib/列表工具.light:1` 注释声称「无同名 .py 兜底，优先加载 .light」，但实测存在
`stdlib/列表工具.py`（1813 字节）。该 .light 是真实现（decl=10，有设/当/返回算法体），
不是转手调用，**不构成造假**，但注释撒谎。应改为如实说明「有同名 .py，但本文件是
自举实现，加载优先级见 module_resolver」。属轻量文档债务，交主线顺手修。

### 14.3 `tests/_test_*.py` 的 legacy 脚本直跑与 pytest 收集双轨（D4-3 核实）

`pyproject.toml:88` `python_files = ["test_*.py", "_test_*.py"]` 会让 `_test_*.py`
同时被 pytest 收集；github ci.yml 的 Legacy Feature Tests 步用 `python xxx.py` 直跑
同一批文件（本机实测 4 脚本全绿 rc=0）。两条轨覆盖相同文件、判据一致（新增失败即红），
但存在「改了 pytest 收集行为却没同步直跑脚本」的维护风险，登记备忘。

### 14.4 假测试基线在第四轮的三次变动（合并期已核，无需动作）


**(a) 存量清理：394 → 358。** C4 重写 `tests/test_async.py`（802 行变更）清掉了 37 条
存量违规（string-assert 36 + 其他 1）；B4 修掉 `test_agent_tools_light.py` 1 条。
与任务书 §D4-1 预估的 390-400 有偏差，偏差来源 = C4 实际清存量，**不是**门禁口径问题。

**(b) 合并期回补下界形态漏拼法：358 → 424。** D4-1 的下界形态只写了 `>=`，
`assert len(x) > 0`（与 `>= 1` 完全等价）整类溜过：全仓实测拦住 26 条、放过 67 条，
**放过的是拦住的 2.6 倍**——「换个符号就绕过门禁」正是门禁最该堵的洞。
放宽正则后基线重建为 **424 条**（string-assert 65 + assertin-string 113 +
upper-bound 2 + lower-bound 92 + not-none 152）。这 66 条增量全部是存量、
不是新写的假绿；口径仍是「存量冻结、新增即红」。
随后扫描根扩到全仓（见 14.5 第 3 条），基线终值 **474 条**。


**(c) `built_from_commit` 曾指向一个不可达提交。** D4-6 报告称基线已指向合并点
`b498142c`，实测两份基线里写的都是 `8c7d6292b066`——一个不在任何分支上的孤儿提交
（生成基线后又改写了提交，戳就悬空了）。这让「基线是否过期」这个自检字段失去意义。
合并期已重新生成两份基线，戳指向可达提交，并在基线 `note` 里写明该字段的语义
（= 生成基线时的 HEAD，即携带本基线那个提交的父提交）与「不可达即须重建」的判据。

### 14.5 假测试门禁的覆盖缺口（四条已全部裁决/处置）

以下四条都不是「写错了」，是**覆盖范围**问题，动了会显著改变基线量级，
所以当初只登记不擅自扩；第 1、2 条经用户裁决维持不扩，第 3、4 条已处置：

1. **`assertIsNotNone` 未覆盖**：形态 6 只认 `assert x is not None`，
   unittest 写法 `self.assertIsNotNone(x)` 实测 249 处全部在门禁外，
   而被拦的 `assert` 写法只有 152 处——与形态 4 当初的漏法同源。
2. **`assertGreaterEqual` / `assertLessEqual` 未覆盖**：实测 34 处，
   与形态 2/5 同源。
3. ~~**扫描根窄于形态的覆盖面**~~ **已处置（2026-08-23 用户裁决：扩到全仓）**：
   CI 原来只扫 `tests/`，同形态违规在 `tests/` 之外还有 50 条
   （`antlrparser/`、`tools/`、`examples/` 的自测脚本）。两个 workflow 的
   调用已改成 `--root .`，基线整份重生成为 **474 条**（424 在 `tests/` 内
   + 50 在外）。换根会让基线里所有 key 一起变（key 相对 `--root`），
   那次「全量新增」是换根造成的、不是回归。全仓实测 1.7s，仍在 <5s 承诺内。
4. ~~**防造假形态零命中**~~ **已处置（2026-08-23，非阻塞项-3）**：
   `assert_quality.py` 的两个预防性形态（`trivial-ge0` / `returncode-in`）
   与 `bootstrap_rate.py` 的自导入检查目前仍是 0 命中——这一点没变，也不该变
   （有命中才说明有人新写了假绿）。变的是**它们从此有证据**：
   `tests/unit/test_ci_gates.py`（12 条）钉住三处判据，每条都配了「几乎一样
   但不该命中」的反例（`>= 0` 拦 / `>= 1` 不拦；`in [...]` 拦 / `== 0` 不拦；
   `X.light` 里 `导入 X` 判假 / `导入 乙` 与 `导入 Python: X` 不判）。
   四发变异反跑（改 `>= 0` 成 `>= 987`、`in [` 成 `in (`、摘掉自导入判据、
   把 OSError 吞回去）各自 rc=1 判红，复位后 12 passed。
   遗留认知不变：真正在拦存量的仍是 `decl >= 1`，这三处只防新增。
   **副作用一并记下**：新文件的类 docstring 起初写成单行、里面带着
   `assert len(x) >= 0` 这个反面样例，直接被门禁点名（`_prose_lines()` 只豁免
   多行字符串）——反面教材必须放进多行块，这条已写进该文件的模块 docstring。


**第 1、2 条的裁决（2026-08-23，用户）：维持保守口径，不扩。** 理由是
「取保守口径、基线控制在 390 上下」这条既有裁决优先；两类全扩会把基线
从 474 再推到约 720，收益（多冻结一批存量）远小于口径反复的代价。
登记在此备查：将来若要扩，必须连同基线量级一起重新裁决，不许顺手扩。


### 14.6 `.github/` 整棵树当前不执行（2026-08-23 实测）

`git remote -v` 只有两个远端：gitea（内网 `192.168.1.5:3000`）与 gitcode
（`origin`）。**没有 GitHub 远端**，所以 `.github/workflows/` 下的 `ci.yml`
与 `quality-gate.yml` 一次都没跑过。这不是猜测，是查远端得到的事实。

由此重新定性两件事：

- **`quality-gate.yml` 不是「第三条判据路径」，是一份不判事的镜像。** 它与
  `ci.yml` 有三处口径差异（flake8 在它这里硬判红、多扫一个 `contrib`、
  用全量+覆盖率而不是基线差分），过去被当成潜在的口径分裂风险，实际风险为零
  ——因为它不执行。已在文件头把「不执行」与三处差异一并写明，免得将来有人
  接上 GitHub 远端后突然多出一条口径不同的红线还不知道来路。
  同时修掉它里面两处真问题：`覆盖率不低于 80%` 与实际 25% 的自相矛盾说明，
  以及覆盖率解析 `except Exception → sys.exit(0)`（报告读不出来就当通过，
  典型假绿）改为硬判红。
- **`ci.yml` 里的 flake8 缺陷（`bash -e` 下 `rc=$?` 不可达）之所以能长期活着，
  根因就是这条**：gitea 的 workflow 里根本没有 flake8 步骤，所以两边都不会红。
  修已在 `d9f445c7`，登记在此是为了记住「改 `.github/` 等于改文档，
  真正会执行的是 `.gitea/workflows/ci.yml`」。

顺带补齐的一个真缺口（非阻塞项-1）：`.ci/root_other.xml` 由非 Linux 那条
根目录测试步骤产出，但回归闸门是 `if: runner.os == 'Linux'`，**跨平台那一路
产了 junit 却没有任何东西看它**。现已补一条跨平台闸门，配专用的空基线
`tests/ci_baseline_failures_crossplat.txt`（该批全是 `tests.test_*`，按
`--soft-classname` 全部软化，所以基线本就该是空的；复用 Linux 那份 12 条基线
会打出 12 行「已不再打红、记得更新基线」的错误提示）。它只新增一种拦截：
**整批没跑起来**——collect error 的 junit 里 `classname` 是空串，`fnmatch('',
'tests.test_*')` 为假，软化豁免不了它，于是判红。已两向验证：坏 junit rc=1、
好 junit rc=0。该基线文件同样要在 `.gitignore` 里豁免 `*.txt`，否则 CI 上
`--baseline` 指向不存在的文件、闸门整条抬错。

## 十五、双后端分叉两条（第七轮 B7 双后端对照跑出来的，均未修）

### 15.1 `除以` 的算术语义 —— ✅ 已修（2026-09-04，裁决选 B）

**同一份 `.light`，两条后端算出不同答案**（修复前）：

- `打印 4 除以 3。`
  - 转译后端（光明 → Python）：`1.3333333333333333`（Python `/` 是真除法）
  - 原生腿（LLVM/C）：`1`（原生腿一切数字是 `i64`，`除以` 落到 C 的 `/`，整数截断）

**裁决（用户，主线）：选 B**——把 `除以` 明确定义为「整数相除得整数」（向零截断，
以原生腿 i64 `sdiv` 语义为基准）；需要真除法时用显式浮点字面量（任一操作数为浮点即
退化真除）。不走方案 A（补浮点类型）。

**修复方案**：
- `src/code_generator.py` 与 `src/code_generator_unified.py` 的二元运算 / 复合赋值发射点：
  遇到 `除以`/`整除`/`除`/`/`/`//` 一律改发 `_light_trunc_div(a, b)`。
- 生成头注入辅助函数 `_light_trunc_div`：`int/int` 走 `a // b if a*b>=0 else -((-a)//b)`
  （向零截断，与原生腿 `sdiv` 一致）；任一操作数为浮点则退化 `a / b` 真除法（与原生腿 `fdiv` 一致）。
  注意**不可用 Python `//`（floor）**——否则负数语义与原生腿分叉（`-7 // 2 = -4` vs `sdiv` 的 `-3`）。
- `src/optimizer/constant_fold.py` 的 `_apply_op`：`op in ('/', '//')` 原本折成 `left / right`
  （Python 真除），`cli.light run`（默认 O2）走此优化器会把 `7 除以 2` 折成浮点 `3.5`，
  与原生腿 `sdiv=3` 分叉。已改为与 `_light_trunc_div` 同口径（int/int 向零截断、含浮点真除），
  负数用例 `-7 除以 2` 折成 `-3`（非 floor 的 -4）。`cli.light_unified run` 路径无优化器，不受影响。

**证据（双后端实跑一致）**：
- `4 除以 3` → 两条腿均 `1`
- `-7 除以 2` → 两条腿均 `-3`（非 floor 的 `-4`）
- `-9 除以 2` → 两条腿均 `-4`
- `7.0 除以 2` → 两条腿均 `3.5`（浮点真除保留，未退化成整数）
- `tests/test_llvm_c3_expr.py::test_双后端一致_除法向零截断` 与 `test_双后端一致_基本算术`
  （已把 `乙 整除 甲` 换回 `乙 除以 甲`）锁死判据。

**裁决 B 落地后的 CI 对齐（2026-09-04，回归闸门修复）**：
- `examples/student_management.light` / `examples/module_demo.light` 平均值、
  `examples/bootstrap_eval.light` 求值器除法：整型 `除` 会向零截断，均值/计算器语境需真除，
  改为显式浮点操作数 `除 转浮点(长度/除数)`（§15.1「任一操作数为浮点即退化真除」的落法）。
- `stdlib/列表工具.light` 的 `平均值`：`总和 / 转浮点(长度值)` 保持与 CPython `sum()/len()` 逐位等价。
- `tests/unit/test_light_examples_run.py::test_division`：`100 除 4` 期望 `25`（整数截断，双后端一致）。
- `c_backend.py`：光明 `/` 在 Python 腿包 `_light_trunc_div`；C 的 `/` 对整数天然向零截断、
  浮点真除，即裁决 B 语义，`_translate_call` 把 `_light_trunc_div(a, b)` 调用映射回原生 C `/`。

**24 条 soft 打红全清（2026-09-04，回归闸门续）**：裁决 B 落地后，存量测试/示例对旧「除→浮点」语义的欠账逐条对齐。根因分组经 .86（Ubuntu 3.12）/ FreeBSD CI 主机（3.11，与 Gitea CI 同版本）四路实证，全部反跑判据（改回原语义立即立红）成立：
- `stdlib/度量.light`（纯光明实现，`转浮点` 为内置别名，不触发 python_direct_calls 棘轮）：
  - `分位` 的 `设 比例 为 ((n - 1) * 百分位) / 100` → `/ 100.0` → 清 metrics 分位 10 条（含反跑_线性插值非取整）。
  - `批量汇总` 的 `通过率 通过数 / 总数`、`平均耗时 总耗时 / 总数` → `转浮点(除数)`；`成本估算 (总词元 / 1000) * 单价` → `/ 1000.0` → 清 metrics 批量汇总 2 条 + harness 通过率/成本 3 条。
- `examples/harness/打分.light`：子集 `通过率 通过数 / 总条数` → `转浮点(总条数)` → 清 harness 整进程跑通里「子集精确通过率」断言（1/2 此前被打成 0）。
- 旧「除→浮点」期望对齐裁决 B（整型截断，反向判据：改回浮点期望立即立红）：
  - `test_edge_cases.py` 3 处（divide_assign/complex_arithmetic/multiple_params）：期望 5.0→5、17.0→17。注释已注明：v4.0 T01 审计锁定的「乘除优先级高于加减、左结合」结论不变，仅结果类型由浮点变整型，裁决 B 取代旧浮点除法假设。
  - `test_ternary.py` case_13：期望 `"1.0"`→`"1"`。
  - `test_self_host_bootstrap.py::test_binary_div`：`10 除 3` 期望 3.333…→`3`（对齐原生腿 i64 sdiv）。
- `test_exception.py` 2 处：`1//0` 的宿主消息 3.11/3.12 是 `integer division or modulo by zero`（不含 `division by zero`），3.14 才简化。断言 `'division by zero'` → `'by zero'`（版本容忍，CI 是 3.11）。
- `test_pure_light_hook.py` [求和]：`builtins.求和` 按 `sys.version_info` 传「启用补偿」（3.12+ 才走 Neumaier 补偿 → 1.0；3.11 朴素累加 → 0.0），期望改 `1.0 if sys.version_info >= (3, 12) else 0.0`（CI 3.11 取 0.0）。
- `test_async_io_light.py` TLS 异步读腿：并发门限 0.8→1.0，并补「并发 < 串行」关系断言。依据：FreeBSD 空闲实测并发 0.79~0.81s 正卡原 0.8 边缘、全核饱和 0.92s、CI 4 路 xdist 并行 1.78s；串行恒 ≥ 1.0s（2×延迟）仍在门限外，真正串行化（≈1.3s）依旧会被拦。判据本意断关系不断绝对值，绝对门限只做兜底。

**验证**：本机 3.14 + .86 3.12 + FreeBSD 3.11（与 CI 同版本）三路全绿；受影响文件整文件重跑通过（metrics/edge_cases/ternary/exception/harness 14/pure_light_hook/TLS）。e2e 基线 12 条为宿主机缺 numpy/pandas/matplotlib/sklearn 的环境欠账，代码层不可清，不在本次全清口径内。

**判据已就位**：原「止损」里的 6 例双后端一致性测试，其中 `test_双后端一致_基本算术`
已把 `整除` 换回 `除以` 作判据；并新增 `test_双后端一致_除法向零截断` 负数用例。
另注：双后端测试的转译腿走 `cli.light_unified run`（src 后端 `PythonCodeGenerator`，
无优化器），故 `7 除以 2` 不被常量折叠，直接发射 `_light_trunc_div(7,2)=3`，与原生腿一致。

### 15.2 stdout 的字节编码（Windows 上非 ASCII 输出不同字节）——已修复

同一句 `打印 "光明"。`，输出重定向进管道/文件时：

- 原生腿的 exe：吐 UTF-8 字节 `e5 85 89 e6 98 8e`
- 转译后端（`light run`，本质是个 Python 进程）：**修复前**吐平台 ANSI 代码页
  字节（中文 Windows 上是 cp936 的 `b9 e2 c3 f7`），**修复后**吐 UTF-8 字节
  `e5 85 89 e6 98 8e`，与原生腿一致。

**根因**：转译后端没有钉死自己的 `sys.stdout` 编码，跟随 `locale.getpreferredencoding()`；
原生腿写的是裸字节，源码是 UTF-8 就是 UTF-8。

**修复方案**：在 `src/code_generator.py` 生成头区块（`import sys` 之后、stdlib
路径探测之前）注入：

```python
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):
    pass
```

`errors='replace'` 是硬性要求——第四轮已踩过「reconfigure 默认收紧成 strict、
整场级联炸」的坑（见 §14.1），不加 `errors='replace'` 会把原本能输出的字符
变成 `UnicodeEncodeError`，比 cp936 丢字节更严重。

**反跑判据验证**：Windows 下 `打印 "光明"` 重定向进文件，修复前字节为 cp936
（`b9 e2 c3 f7`），修复后字节为 UTF-8（`e5 85 89 e6 98 8e`），实测通过。

**测试覆盖**：
- `tests/test_llvm_c3_expr.py::test_stdout_utf8_bytes`——新增字节断言用例，
  显式移除 `PYTHONIOENCODING` 和 `PYTHONUTF8`，重定向 stdout 进文件，断言
  UTF-8 字节存在且 cp936 字节不存在。该用例不依赖 `_run_transpiled` 的环境变量
  守卫，独立捕获 reconfigure 失效。
- `tests/test_llvm_c3_expr.py::_run_transpiled` 中原有的
  `PYTHONIOENCODING=utf-8` 保留为**回归守卫**——若生成头 reconfigure 被移除或
  破坏，此环境变量仍能拉平编码，使双后端字符级比对不因编码差异假红；但字节断言
  用例会独立捕获 reconfigure 失效。

**文件隔离**：本次只动 `code_generator.py` 生成头区块（~L962-968），未触碰
除以 op map（~L228）与复合赋值（~L2228）——归 T1。

## 十六、第七轮五路全合点的账（2026-08-24，合并期核验产出）

### 16.1 三份基线在全合点统一重建，重建理由逐条列明

在 `e99c63fd`（五路全合）之后一次性重建，**不是为了消红而重建**，每份都写明动因：

- **自举率**（`tools/ci/bootstrap_rate_baseline.json`）：29.73% → 31.58%（文件维度 24/76），
  关键路径子指标 77.78% → 88.89%（16/18）。都是**升**，重建只是把棘轮往上抬。
  影子数 53 持平，`stdlib/` 引 Python 逃逸仍是 0。
- **功能对标清单**（`tools/ci/spec_coverage_baseline.json`）：done 8 → 12。见 16.2。
- **Python 直调**（`tools/ci/python_direct_baseline.json`）：总数 308，per-file 有升有降。
  **升的两个文件必须记账**（这是唯一一份「有上升还重建」的基线）：
  - `examples/harness/LLM通道.light` 0 → 1：只剩 `:164 time.sleep(延迟秒)`。
    mock 通道的延迟注入点，在工作线程里同步睡。stdlib 无纯光明的睡眠原语，无可替代。
    （合并期已把同文件的 `json.dumps` 换成 `JSON核心.序列化`，那一条是真收口，不是豁免。）
  - `examples/harness/评测驱动.light` 12 → 16：`:141/:148 os.environ.get`（这两行**就是**
    `取环境/设环境` 光明包装器的实现体，os 是系统边界）、`:177/:181 time.time()`（计时，
    stdlib 无单调时钟原语）、`:180 asyncio.to_thread`（同步 agent 循环跨界到事件循环的
    唯一手段，见对标清单第 8 条）。
  - 同时两个文件是**降**的，抵掉了上面的升：`主程序.light` 21 → 15（切到
    `代理工具集.注册全部`）、`编排.light` 2 → 0（切到 `stdlib/并发`）。
  - 要真消掉那 5 行，得先在 stdlib 补「睡眠 / 单调时钟」两个纯光明原语，属后续轮次。

### 16.2 对标清单状态逐条核验（done 8 → 12）

先说一条**记账口径事故**：`第七轮C7_交付报告.md:177-188` 那张「功能对标清单推进」表的行号
（2/5/6/7/8/10/16/17）**不对应 `任务书/功能对标清单_harness.json` 的 `编号`**。
例：报告第 2 行写「JSONL 行流」，而清单 #2 是「并发调度」；报告第 16 行写「mock 造 tool_calls」，
而清单 #16 是「取消 / 超时」。两套编号撞车，谁照着报告的数字去改清单状态就会改错条目。
以后动状态只认清单 `编号` + `功能` 两个字段一起对上。

合并期按清单 `编号` 逐条核验（结构 + 实跑，不认注释与报告的自我声明）的结果：

- **升 done**：#8 多轮 agent loop —— `test_harness_agent_light.py:88` 断言 `完成轮数 >= 2`，
  轮数是 `代理循环.light:500` 在循环体内真加出来的，是真判据。
  （#13/#14/#15 的 done 是 D7 合入时兑现的 usage / 成本 / 分位，不在本节。）
- **升 partial（none → partial，但不到 done）**：
  - #5 错误分类与单条兜底：六类分类真的有，agent 路径有真判据；但分类器只有
    `评测驱动.light:193` 一个调用点，single 模式仍走 `编排.light:59` 只认两类异常。
  - #7 工具调用：mock 造 tool_calls、参数校验、工具真执行都成立；但「评测链请求体带 tools」
    只在 agent+real 这条**无测试**的路径成立，默认被测的 agent+mock 路径没有请求体这回事。
- **维持原状**：
  - #2 并发调度（partial）：实现真切到 `stdlib/并发` 信号量任务池、单实现无双写，
    但缺长尾判据 —— 分批 gather 同样能过现有全部测试。
  - #6 流式增量消费（partial）：消费方仍是 `设 累积 为 块["累积内容"]` 逐轮覆盖，
    `内容增量` 在 `examples/harness/` 消费侧零引用。本轮未推进。
  - #17 事件流可观测（partial）：「每实例一条总线」做到了；「汇聚到主协程再发」在代码里
    不存在（无队列 / 无 `call_soon_threadsafe`），实际是靠「工作线程干脆不发事件」达成。
- **降级 partial → none**：#16 取消 / 超时。评测链一行都没有；agent 侧取消令牌是死码 ——
  `代理循环.light:324` 构造里置空、全仓无赋值点，`是否已取消` 恒返回假。
  `stdlib/并发.light:76-78` 的 `超时运行` 现成没吃。
  > **第八轮订正（覆盖上面两行）**：#16 已升回 **partial**，且上面那句「全仓无赋值点」是错账。
  > - 错账：`tests/test_agent_loop_light.py:412-429` 有真赋值点，并断言 `轮次 == [0]`
  >   （令牌先置位则一轮都不跑）。准确说法是 **生产代码里没有赋值入口，只有测试在用**；
  >   `代理循环.light:324` 构造置空是「默认不可取消」，不是死码。
  > - 已补：第八轮把 `stdlib/并发.超时运行` 接进评测链 —— `评测驱动.light` 的
  >   `限时等待` + `HARNESS_TIMEOUT_SEC`，单模链与 agent 链各一处；超时落「超时」类失败、
  >   整场跑完、报告照样落盘。判据 `tests/test_harness_e2e_light.py::Test单条超时`、
  >   `tests/test_harness_agent_light.py::TestM18超时`（含反跑变异：把限时条件取反后
  >   两条「全条超时」用例立红，其余三条不动）。
  > - 仍然只是 partial：agent 模式被限时的对象是 `asyncio.to_thread(...)`，取消掉的是
  >   **等待**，掐不断已经起跑的 worker 线程；生产代码也依然没有给 取消令牌 赋值的入口。


### 16.3 合并期顺手修掉的三处（都不是 C7 报告里提的）

- `examples/harness/评测驱动.light`：C7 自带的 `求分位数` 用「取整下标」，与项目口径
  （`stdlib/统计.py` 的线性插值）不一致 —— 删掉本地版，改吃 `stdlib/度量.分位`。
  实测报告里的 p50/p95 与手算线性插值逐位相等。
- `examples/harness/行流.light`：`有键` 的 `返回 假` 误缩进在 `遍历` 体内，**只看第一个键**。
  当前调用点恰好总把 `坏` 排在首位（`stdlib/JSONL.light:43`），所以是潜伏而非现行故障。
  已把 `返回 假` 提到循环外；同文件删掉已成死码的 `导入 os/sys/json`。
- `examples/harness/评测驱动.light` 两处过期/失真注释：`TODO(移交:D7)` 说 p50/p95 用本地兜底
  （已不是）；`HARNESS_TOOLS` 文档说「agent 模式使用工具」，实际它**不 gate 任何工具注册**，
  `off` 也照样注册两个工具、照样发 tool_calls。后者是行为与文档不符，本轮先如实写清。

### 16.4 未修、明账移交

- **`用量`/`成本` 恒空字典**：不是在等 D7 —— `stdlib/度量.light:95-136` 的 `批量汇总` 已能算
  `总输入词元/总输出词元/成本估算/成本说明`。断点在 **`stdlib/代理循环.light:436`**：
  `单轮请求` 只从块里取 `完成原因/内容增量/工具调用增量`，块上的 `"用量"` 在那一行被丢掉，
  `代理循环` 也没有累积它的字段；第二道断点是 `评测驱动.light:145` 的返回字典不带用量。
  （留空是刻意的，**不许填 0** —— 「没配」和「真是 0」必须可区分。）
- **主流程无 try**：`评测驱动.light:344-418` 的 `主` 里 `写入JSON文件`/`写入文件` 前后无 `尝试`。
  「报告必须落盘」目前只对 agent 单条异常成立，对写盘/汇总/single 冒泡都不成立。
- **`错误分类.light:77-90 应重试` 与 `:101-107 状态码为整数` 全仓零调用点**：文件头声称接了
  重试决策，实际重试仍走 `编排.light:59` 那个只认两类异常的 `捕获`。
- **`主程序.light:43-61` 四个监听器仍往 stdout 写中文**：库侧已把发事件收敛到主线程，
  harness 侧这半个问题没处置。
- **判据缺口三条**：并发无长尾判据；`用量/成本/p50/p95` 在报告层无断言；事件总线无
  「两实例并发各自只收到自己的事件」用例。


---

## 十七、POSIX/Linux 实测账（2026-08-24，A7 交付的 Linux 实机验证）

来源：`docs/POSIX验证报告_Linux.md`（Ubuntu 22.04.5 + clang-18 + Python 3.12.13 实机跑，
非读代码推断）。同目录还有 `docs/POSIX验证报告.md`（Windows/沙箱版，早一轮）。
两份报告是**外部交付物存档**，不是本仓库的历史文档，引用时按 §号 定位。

已在本轮直接处置的：**#L3**（缺 cryptography 导致整轮 pytest collect abort）——
`tests/test_tls_light.py` 改成响亮降级（缺依赖时一条红代表全文件，只有显式
`LIGHT_ALLOW_SKIP_TLS_TEST=1` 才整文件 skip），并在 `.gitea/workflows/ci.yml`
装依赖那步补 `pip install cryptography || true`。**没有**按报告建议用
`pytest.importorskip` —— 那会让「纯离线、不许 skip」的文件在缺依赖时静默全绿。
**#L4** 无需动作（Windows 专属，Linux 侧 LTO 直接可用）。

### 17.1 #L1 [高·环境门槛] 原生腿要求 clang ≥ 18（已写进文档/CI）

- 现象：同一批 IR 在 clang-14 四档全红（`ptr type is only supported in -opaque-pointers
  mode … error: expected type`）、clang-15 也全红（O2/O3 另报
  `instruction expected to be numbered '%0'`）、clang-18 四档全绿（12 格矩阵 12/12）。
- 性质：**不是项目缺陷**，是工具链版本门槛（IR 走 opaque pointer 现代风格）。
  Ubuntu 22.04 自带的 clang-14 完全不可用。clang-16/17 未逐版实测。
- 处置：`docs/从光明到LLVM.md §1.0` 新增「工具链底线」小节 + §8.1 两条 Q；
  `.gitea/workflows/ci.yml` 新增「工具链盘点（clang 版本·只报告）」一步
  （**只报告不判绿**：缺 clang 时原生测试按设计 skip，不该因宿主 clang 旧就整轮红）。
- 未验证：~~FreeBSD runner 自带 clang 的版本~~ —— **gitea run 94（2026-08-24）已实测**：
  `FreeBSD clang version 19.1.7`，**≥18，满足底线**，新加那步没打警告。
  同一份日志还坐实了 #L3 的隐性依赖：`Requirement already satisfied: cryptography in
  /usr/local/lib/python3.11/site-packages (44.0.3)` —— 这台 runner 上新加的 pip 装依赖
  是空转，蹭的就是系统 site-packages 那份；换台干净 runner 才会真装。

### 17.2 #L2 [中] POSIX 侧原生 TLS 是 stub（有壳无实现）——已修复（Task T7：mbedTLS 后端）

- 原状：`runtime_typed.c` 旧 POSIX 分支 `backend=none`、`dv_tls_wrap` → NULL，
  任何握手调用立即失败；Windows 侧的 Schannel 后端是真的。缺的是**实现**，
  不是错误可见性（`dv_tls_last_error` 在 `#ifdef _WIN32` 之前无条件存在）。
- 修复（Task T7）：POSIX 分支补 **mbedTLS 客户端后端**（`runtime_typed.c:6147` 起，
  `#if defined(LIGHT_TLS_MBEDTLS)`），API 签名与行为对齐 Windows Schannel 分支：
  - 证书校验默认开启（`g_tls_verify_default=1`）；
  - `dv_tls_add_trusted_cert_file` 追加「独占根」信任锚（对应 Windows hExclusiveRoot、
    curl --cacert 语义：一旦设置只认显式给的这批根，比系统根更严）；
  - 握手可重入非阻塞（WANT_READ/WANT_WRITE 透传，喂 `dv_coro_await_io` 不阻塞事件循环）；
  - 发送走 out_pending 队列（半包写不完不阻塞）、`dv_tls_recv_status` 返回
    OK/WANT_READ/CLOSED/ERROR 与 Windows 一致；
  - `dv_tls_backend()` 返回 `"mbedTLS"`。
- 开/关：定义 `LIGHT_TLS_MBEDTLS` 启用真后端；未定义时保留原 stub（保证未装
  mbedTLS 的 POSIX 构建不破——「勿破坏原生腿其它部分」）。依赖 libmbedtls-dev
  （Ubuntu: `apt install libmbedtls-dev`），链接 `-lmbedtls -lmbedx509 -lmbedcrypto`。
- 验证（本机 Windows，POSIX 只做代码层对齐 + 编译检查）：
  - Windows Schannel 冒烟：`python -m pytest tests/test_llvm_tls.py -q` 正/负例
    **2 passed**（不破坏原生腿）；
  - POSIX mbedTLS 分支：对 Ubuntu 24 同款 **mbedTLS 2.28.8** 头与 3.5.2 头
    `-fsyntax-only` 全绿、2.28.8 完整 `-c` 编译通过（`_taskT7_posix_syntax.c` 独立 TU）。
  - **POSIX 真机实测通过**：目标机 192.168.0.86（Ubuntu 24.04 / clang 18.1.3 /
    libmbedtls-dev 2.28.8）上 `python3 -m pytest tests/test_llvm_tls.py -q` **2 passed**；
    C 二进制定向用例正例 `dv_tls_backend()=mbedTLS` + 握手/回显全 PASS、负例
    `X509 - Certificate verification failed (-0x2700)` 正确拒绝不受信证书。
    （首次交付时 .86 不可达曾标注「未在 POSIX 实测」，用户确认连通后补跑完成。）
- 定向测试：`tests/test_llvm_tls.py` 正/负例在双平台都跑真后端（已去掉 `仅Windows`
  跳过、删除 `仅POSIX` 桩反向钉住用例）；POSIX 编译由测试侧显式加
  `-DLIGHT_TLS_MBEDTLS -lmbedtls -lmbedx509 -lmbedcrypto`（生产 `get_link_libs()`
  的 POSIX 分支保持 `-lm` 不动，属 T9 范围）。
- 记账口径：启用 `LIGHT_TLS_MBEDTLS` 的 POSIX 构建上，「原生 TLS 可用」不再限
  Windows；未启用宏的构建仍为 stub。

### 17.3 #L5 [中] 溢出文件的**绝对路径**被拼进标准输出（跨平台真缺陷，Windows 是假绿）——已修复

报告把它记成「Linux 特有」，**本轮核查后改判：两个平台都漏，Windows 只是断言瞎了**。

- 真正的泄漏点：`stdlib/进程树.light:249` ——
  `设 标记 为 "...[已省略 N 字节，完整输出见 " + 己.溢出路径 + "]..."`，
  `己.溢出路径` 是 `os.path.join(己.目录, 名)` 的**绝对路径**，被 prepend 到
  `结果.标准输出` 的**开头**。合并期修 P0-1 时只把
  `stdlib/代理工具集.light:658` 那条尾部提示改成了 `os.path.basename`，
  上游这条省略标记漏了。
- 为什么 Windows 绿：`stdlib/路径护栏.light:105-112 规范路径` 在 Windows 上做
  `os.path.normcase`（全小写），沙箱根目录因此是小写，拼出来的路径也是小写；而
  `tests/test_agent_tools_light.py:666` 的 `str(tmp_path) not in 结果` 是**大小写敏感**的，
  于是漏检。本机实测（`_probeL5_` 探针）：输出头部确实带
  `c:\users\...\appdata\local\temp\_probel5_xxxx\_taskD2_spill_1_....bin`，
  同一断言判定 `NOLEAK`。Linux 上 normcase 是空操作，路径逐字相等 → 红。
- 为什么 `:665` 那条 `os.sep not in 尾段` 也没拦住：`尾段` 从 `"输出超限"` 起算，
  泄漏在它**前面**的正文里。
- 影响：给模型的输出里带宿主机目录结构（用户名、盘符、临时目录布局），
  而模型只能用沙箱内相对名（`read_file` 受 核准 管），绝对路径对它毫无用处。

**修复方案**：
1. `stdlib/进程树.light:249` 溢出标记改为回显 `os.path.basename(己.溢出路径)`，
   不再拼绝对路径。
2. `tests/test_process_tree_light.py:118-125` 新增路径泄露守卫：断言省略标记含
   `os.path.basename(结果.溢出文件)`、标记段不含 `os.sep` 和 `os.altsep`。
3. `tests/test_agent_tools_light.py:666-670` 原大小写敏感的
   `str(tmp_path) not in 结果` 改为 `str(tmp_path).lower() not in 结果.lower()`，
   并增加 `os.altsep` 断言。

**反跑判据验证**：修复前输出标记含完整绝对路径（盘符/用户目录）；
修复后只含文件名。若将 L249 改回拼接 `己.溢出路径`，上述新增断言立即立红。


## R10-12a T5A：数学/统计/排序 .light 化 — O0 codegen 缺陷与 workaround

### 概述

T5A 将 `stdlib/数学.light`、`stdlib/统计.light`、`stdlib/排序.light` 从空壳补为
纯光明真实现，在 O0（`optimize_level=0`）下真编译真跑，与 Python `math`/
`statistics` 对拍。过程中发现 6 个 O0 codegen 缺陷，均以纯光明 workaround 绕过，
不修改 codegen 核心（归后续 T7/T3）。

### 缺陷清单

#### T5A-01：跨段 float 返回值在算术中被零初始化

- **现象**：`设 m 为 均值(d); 设 v 为 m * 2` → `输出(m)` 显示正确值（如 `3`），
  但 `m * 2` 结果为 `0` 或垃圾值（如 `4.94e-324`）。
- **根因**：O0 下跨段函数返回的 float 值存入局部变量后，后续算术读取该变量时
  读到零初始化的 int slot 而非 float slot（类型标记丢失或 slot 复用错误）。
- **影响**：所有依赖其他段 float 返回值的函数（如 `方差` 调 `均值`、`标准差` 调
  `方差`、`常用对数` 调 `自然对数`、`相关系数` 调 `平方根`）均受影响。
- **Workaround**：将所有跨段 float 依赖改为**自包含内联计算**——每个函数独立
  计算 mean/variance/sqrt，不调用其他段的 float 返回值。例如 `方差` 内联重算
  mean，`标准差` 内联重算 variance，`常用对数`/`对数2`/`对数` 各自内联 ~20 行
  泰勒级数展开（而非调 `自然对数(x)` 后做除法），`相关系数`/`标准化` 内联牛顿法
  sqrt（20 次迭代 `(r + val/r) / 2.0`）。
- **归属**：codegen 类型推断/slot 管理，归 T7 修复。

#### T5A-02：int/int 除法结果在后续算术中被零初始化

- **现象**：`设 q 为 10 / 3; 输出(q)` 显示 `3`（正确），但 `q + 0.0` 结果为
  `4.94e-324`（垃圾值），`q * 2` 结果为 `0`。
- **根因**：int/int 除法在 O0 下返回的 dv 值虽然 `输出` 时能正确显示整数部分，
  但其内部类型标记为 int 而非 float；后续算术将其作为 int 读取后参与 float 运算，
  导致内存解释错误。
- **影响**：所有 `总计 / n` 形式的均值/方差/协方差计算。
- **Workaround**：统一使用 `(总计 + 0.0) / n` 模式——先将分子通过 `+ 0.0` 转为
  float dv，再做除法，确保结果为 float 类型标记。
- **归属**：codegen 除法类型推断，归 T7 修复。

#### T5A-03：`_light_builtin.平方根()` 返回值存入变量后在算术中被零初始化

- **现象**：`设 s 为 平方根(2.0); 输出(s)` 显示 `1.41421`（正确），但 `s * s`
  结果为 `0`。
- **根因**：与 T5A-01 同类——builtin 包装函数返回的 float 值存入局部变量后，
  类型标记丢失。
- **影响**：`相关系数`（需要 sqrt）、`标准化`（需要 sqrt）、`样本标准差`等。
- **Workaround**：在 `相关系数` 和 `标准化` 中用**内联牛顿法 sqrt** 替代
  `_light_builtin.平方根()` 调用：20 次迭代 `(r + val / r) / 2.0`，纯局部 float
  算术无函数调用。
- **归属**：codegen builtin 返回值 slot 管理，归 T7 修复。

#### T5A-04：float 字面量作为用户段函数参数时被零初始化

- **现象**：`设 r 为 百分位数(d, 75.0)` → 函数内 `百分位` 参数读为 `0`。
  但 `百分位数(d, 75)`（int 参数）正常；`向上取整(3.2)`（builtin 包装）也正常。
- **根因**：用户定义段的参数传递在 O0 下，float 字面量参数被写入 int slot。
- **影响**：`百分位数` 的 float 百分比参数。
- **Workaround**：`百分位数` 段改为接收 int 参数，内部 `设 p 为 百分位 + 0.0`
  转 float。`四分位数` 调用改为传 `25`/`50`/`75`（int）。
- **归属**：codegen 参数传递类型推断，归 T7 修复。

#### T5A-05：跨模块同名段导致 codegen 函数重定义

- **现象**：`数学.light` 和 `统计.light` 都有 `最小值`/`最大值` 段，联合编译时
  报 `invalid redefinition of function '_seg_f7'`。
- **根因**：`src/llvm/core.py` L116 `_safe_func_name` 使用全局 counter 映射段名到
  `f{counter}`，同名段在不同模块中映射到相同函数名。
- **影响**：任何跨模块同名段联合编译。
- **Workaround**：将 `统计.light` 的 `最小值`/`最大值` 重命名为
  `数据最小值`/`数据最大值`（导出和段定义同步修改）。
- **注意**：`统计.py` 仍导出 `最小值`/`最大值`；原生腿用 `.light`（导出
  `数据最小值`/`数据最大值`），解释腿用 `.py`（导出 `最小值`/`最大值`），
  两者导出名不同。混用场景暂不处理（T5A 仅验证原生腿）。
- **归属**：`_safe_func_name` 应按模块隔离 counter 或使用模块前缀，归 T3 修复。

#### T5A-06：`自然对数` float 参数被零初始化导致死循环

- **现象**：`自然对数(2.718...)` 超时——参数被零初始化后 `当 值 > 2.0` 条件
  恒为真（0 不大于 2.0 但泰勒展开对 0 无限循环），导致死循环。
- **根因**：与 T5A-04 同类——float 字面量作为函数参数被零初始化。
- **Workaround**：添加安全防护 `如果 值 <= 0.0: 返回 0.0`，避免死循环。
  实际调用时通过 int 参数或 `+ 0.0` 转换绕过。
- **归属**：同 T5A-04，归 T7 修复。

### 反跑判据验证

| 判据 | 真实现 | 空壳（恢复 decl 0） |
|------|--------|---------------------|
| 数学.light | ✅ 绿（5 测试） | ✅ 红（`NativeImportError: decl 0 空壳`） |
| 统计.light | ✅ 绿（5 测试） | ✅ 红 |
| 排序.light | ✅ 绿（2 测试） | ✅ 红 |
| 三模块联合 | ✅ 绿（1 测试） | — |
| 总计 | 16 passed | 3 passed（反向验证） |

### 临时文件

所有 `_taskT5a_*` 调试产物已清理。



## 十八、T5B 编码与哈希模块真 .light 化（2026-09-05）

本轮把 `Base64` / `编码` / `哈希` / `字符串常量` 四个「decl 0 空壳」模块改成
**纯光明真实现**（首行带「纯光明实现」魔数，旁路同名 `.py`），并在原生腿
（llvm typed，**optimize_level=0**）下与 Python `base64` / `hashlib` / `string`
逐项对拍通过。

### 18.1 本轮修掉的原生腿 builtin 接线缺陷（codegen_typed.py）

以下都是**既有代码的参数类型错误**，不是新增功能；`runtime_typed.c` 一行未改。

| 位置 | 症状 | 根因 | 修法 |
|---|---|---|---|
| `Base64编码/解码`、`MD5`、`SHA1`、`SHA256`（T5B 新增注册） | 返回空串 | `dv_str_len` 入参是 `LightValue*`，却先 `extractvalue …,3` 取了 `char*` | 先 `_store_dv(args[0])` 取槽指针再传 |
| `字符串包含`（`dv_str_contains`） | 恒假 | 同上，传了 `char*` | `_store_dv` 后再调 |
| `以开头`（`dv_str_starts_with`） | 恒假 | 同上 | 同上 |
| `以结尾`（`dv_str_ends_with`） | 恒假 | 同上 | 同上 |
| `反向查找`（`dv_str_rfind`） | 等价于 `查找` | 同上 | 同上 |
| `计数`（`dv_str_count`） | 恒 0 | 同上 | 同上 |
| `四舍五入`（`dv_round`） | IR 校验失败 `%N defined with type struct but expected ptr` | 第二参传了 struct 值 | `_store_dv(args[0])` 取指针 |

判定依据：`runtime_typed.c` 里 `dv_str_contains/starts_with/ends_with/count/rfind`
的签名均为 `(LightValue*, LightValue*)`，而 `dv_str_find` / `dv_base64_encode` /
`dv_md5` 等是 `(char*, …)` —— 两类混用是历史接线遗留。

### 18.2 本轮新增注册的 builtin（仅注册既有 runtime，未新增 C 函数）

- `Base64编码 / base64_encode / b64encode / _b64_encode` → `dv_base64_encode`
- `Base64解码 / base64_decode / b64decode / _b64_decode` → `dv_base64_decode`
- `MD5 / md5 / _md5` → `dv_md5`；`SHA1 / sha1 / _sha1` → `dv_sha1`；
  `SHA256 / sha256 / _sha256` → `dv_sha256`（三者均返回小写十六进制，与 `hexdigest()` 一致）
- `四舍五入 / round / _round` → `dv_round`
- `整除 / div` → `dv_div`（补齐：`取模/mod` 原本已有，两者成对）

> 命名约定：`.light` 模块暴露 runtime 时用 `_b64_encode` 这类**与公开中文名不同**
> 的内部别名。原因见下条。

### 18.3 #L-T5B-1 [中] 跨模块同名段落 → LLVM IR 重定义（未修，规避）

- 现象：`从 编码 导入 …`，而 `编码.light` 又 `从 Base64 导入 …` 时编译失败：
  `error: invalid redefinition of function '_seg_f15'`。
- 根因：`core.py:_safe_func_name()` 只按**段名**映射（`f{counter}`），不带模块前缀；
  多模块编译进同一个 codegen 时，`编码.Base64编码` 与 `Base64.Base64编码`
  被映射到同一个 LLVM 符号，于是 `define` 两次。
- 规避：**每个模块一个独立编译单元**。`编码.light` 因此自带一套
  UTF-8↔hex 实现，不从《Base64》导入；T5B 测试也对四个模块分别编译。
- 未修原因：改成模块前缀会牵动 `_gen_typed_segment_call` /
  `_gen_exported_aliases` 的调用侧命名约定，属独立改造项。

### 18.4 #L-T5B-2 [中] 高阶函数不支持（未修，语义变更 + 文档化）

- 现象：`段落 应用 接收 f, c: 返回 f(c)` → `未定义的段落：f`。
  原生后端只会把 `名字(...)` 解析成**段落调用**，没有函数值。
- 影响：`字符串常量.py` 的 `字符列表全部是(文本, 检测函数)` /
  `字符列表有一个是(文本, 检测函数)` 无法 1:1 复刻。
- 处理：`.light` 版第二参改为**分类名字符串**
  （`"字母"/"数字"/"字母数字"/"小写"/"大写"/"空白"/"可打印"/"标点"/"十六进制"/"八进制"`），
  未知分类名返回 `假`。**与 .py 签名不兼容**，已在模块头与本节登记。

### 18.5 #L-T5B-3 [中] SHA512 / HMAC_SHA256 能力边界（未实现，返回空串）

- `SHA512`（`编码.SHA512哈希`、`哈希.SHA512`）：原生腿无 `dv_sha512` runtime；
  且光明**缺位移与按位运算符**，无法在 `i64` 上可靠模拟 64 位无符号逻辑右移
  （`整除` 是向零取整，`2^63` 又超出 `i64` 上界）。故返回空串占位。
- `HMAC_SHA256`：`.py` 语义是 `pbkdf2_hmac('sha256', text, key, 1)`，其消息尾部含
  `b'\x00\x00\x00\x01'`，而 `dv_sha256` 以 `strlen` 取长度（**非二进制安全**），
  无法对拍。故返回空串占位。
- 解锁路径：runtime 增 `dv_sha512` / 二进制安全的 `dv_sha256_n(ptr, len)`，
  或语言层补位运算符 + 无符号 64 位移位。

### 18.6 #L-T5B-4 [低] `连接字符串` 对列表返空（未修，已在 .light 内规避）

`连接字符串` 用 `extractvalue …,3` 取列表指针，而列表指针不在 LightValue 的
索引 3 字段，故对列表恒返空。`字符串常量.light` 的 `连接` 改为纯光明索引循环实现。

### 18.7 字节口径结论（重要，后续模块照此办）

原生后端字符串索引按**字符**，而 Python `base64`/`hashlib` 按 **UTF-8 字节**。
纯光明实现统一以「十六进制串」作字节中间表示（`_编码UTF8` / `_解UTF8`），
已验证中文（`"Hello, 世界!"`）与 Python 逐字节一致。

### 18.8 反跑判据

- 测试：`tests/unit/test_T5B_编码哈希.py`（4 个用例，全部 `optimize_level=0`，
  各模块独立编译单元）。
- 真实现 → 4 项全绿；将四个 `.light` 改回「只有 `导出` 清单」的空壳 →
  4 项全部立红（`NativeImportError: … decl 0 空壳`）。
- 回归：`tests/test_native_import.py`、`tests/test_native_cli.py`、
  `tests/unit/test_地板搬迁_路径_S2.py`、`tests/e2e/test_llvm_pipeline.py`
  连同 T5B 共 **520 passed, 1 skipped, 0 failed**。

> 注：本机 clang 需要 `INCLUDE` / `LIB` 指向 MSVC + Windows SDK，否则
> `runtime_typed.c` 报 `'stdio.h' file not found`。T5B 测试会自动探测并补齐，
> 其它原生腿测试需自行在环境里准备。
## R10-12c T5C：集合/随机/对象池缓存 .light 化 — O0 codegen 缺陷与能力边界

### 概述

T5C 将 `stdlib/集合.light`、`stdlib/集合工具.light`、`stdlib/集合操作.light`、
`stdlib/随机.light`、`stdlib/对象池缓存.light` 五个「decl 0 空壳」补为纯光明
真实现，并在 `runtime_typed.c` 新增确定性随机数运行时（`dv_random` /
`dv_random_seed` / `dv_random_bits`），O0 下与 CPython `random.seed(同种子)`
逐位对拍（固定种子 42）。过程中发现的 O0 codegen 缺陷均以纯光明 workaround
绕过，不触碰 codegen 核心（归 T7）。

### 算法偏离（任务书 LCG → MT19937，已定案）

任务书要求 LCG，但对拍判据是「与 Python `random.seed(同种子)` 逐位一致」，
LCG 不可能对齐 CPython —— 实现改为 **MT19937**（`genrand_res53`），并对齐
CPython 3.14 的播种口径：整数种子一律走 `init_by_array`（小端 32 位字切分；
`|seed|` 取绝对值；`seed=0` 补单字 `[0]`）。`dv_random_bits(k)` 对齐
`getrandbits`「右移保留高 k 位」，**k ≤ 63**（k>63 截断、k≤0 返回 0，i64 上限）。

### 缺陷清单

#### T5C-01：builtin 浮点返回值参与算术时被误取 i64 槽（恒 0）

- **现象**：`随机数() 乘 9007199254740992.0`、`时间戳() 乘 1.0` 均为 `0`；
  与浮点字面量的比较路径同样错。
- **根因**：`_infer_expr_type(BinaryOp)` 把「未知类型操作数 + 浮点字面量」
  误判 FLOAT，`_gen_typed_binary_op` 快路径对未知侧执行 `extractvalue ..., 1`
  取 i64 槽（浮点 DV 的 i64 槽恒 0）。
- **修复**：codegen_typed.py 三处 —— ① 算术分支要求两侧均在
  ('FLOAT','INT') 才推断类型；② 算术 FLOAT 快路径加同条件；③ 比较 FLOAT
  快路径加同条件。任一侧未知时回退通用 `dv_*` 路径，由运行时标签决定。
- **归属**：本批已修（codegen 3 处），非 workaround。

#### T5C-02：`追加` 对函数参数（REF）无效，对字典读出句柄有效

- **现象**：函数内对**参数列表**调 `追加` 不生效（`唯一元素(列表(1,2,1,3,2))`
  得 0 元素）；对**本函数内新建**列表或**字典读出的列表**调 `追加` 生效。
- **根因**：O0 下参数经浅拷贝 REF 传递，列表扩容（realloc）后栈上壳指针
  未写回。
- **Workaround**：集合族所有变长构建改走「字典读出句柄」——
  `设 元素 为 集合_列表(集合)` 后再 `集合_加(元素, ...)`；或函数内自建
  局部列表直接构建。
- **归属**：codegen 参数/写回语义，归 T7。

#### T5C-03：`设 列表[i] 为 值` 索引赋值损坏 REF 列表

- **现象**：`设 结果[i] 为 值` 对函数参数不生效且把元素变「空」
  （`设 池[0] 为 池[2]` 得 `3,空,空`）。
- **Workaround**：全部改用 `设 空值 为 设置(结果, i, 值)`（`设置` builtin
  验证 OK）。随机.light 3 处、集合操作.light 2 处已替换。
- **归属**：codegen 索引赋值写回，归 T7。

#### T5C-04：字典新增键经函数参数（REF）写回丢失

- **现象**：函数内 `字典设置(缓存, "新键", 42)` 对**新增键**无效（主内读回
  空）；对**已有键更新**与**重建值列表 + 字典设置**生效。
- **根因**：新增键路径 `realloc` 重绑 list_data，栈上浅拷贝的 dict 壳指针
  没写回；替换路径不扩容、堆指针原地改。
- **Workaround**：`对象池缓存.light` 全模块改为「键/值/截止 并行列表」架构
  （`{"键":[], "值":[], "截止":[]}`），新增走「字典读出的列表句柄 +
  `追加`」、删除/清空走「重建新列表 + 字典设置（替换路径）」。
- **契约**：缓存值不可为 `空`（与缺失语义冲突）。
- **归属**：codegen 字典写回，归 T7。

#### T5C-05：变参 `接收 *x` 2 个以上实参不绑定

- **现象**：`合并(列表(1,2), 列表(3,4))` 把「列表们」绑成字符串 `"列表们"`。
- **Workaround**：集合操作/集合工具/集合 的变参函数全部改为固定双参
  （`合并(甲, 乙)`、`链字典(甲, 乙)`、`多个并集(甲, 乙)`、`多个交集(甲, 乙)`）。
- **归属**：codegen 变参，归 T7。

#### T5C-06：跨模块同名段 → codegen 函数重定义

- **现象**：同编译实例中 `集合.light` 与 `集合操作.light` 都有 `交集`/`差集`
  段 → `invalid redefinition of function '_seg_fN'`。
- **根因**：`src/llvm/core.py` `_safe_func_name` 按段名分配 fN。
- **Workaround**：`集合操作.light` 的 `随机下限` 改名 `打乱随机下限`；
  `交集`/`差集` 双模块共存不可改 → **同一程序内不得同时导入 集合 与 集合操作**
  （测试按程序分开导入）。
- **注意**：此限制对**所有** stdlib 双模块同名导出成立（T5A-05 同根因）。

### 能力边界（诚实声明）

- **安全随机类**（安全随机整数/令牌/URL令牌）：无 OS 级安全熵 —— 用
  `dv_random`（MT19937）加种子实现，**不具密码学安全性**，仅格式对齐。
- `随机字节` 返回十六进制字符串（原生腿无 bytes 类型），与 .py 的 bytes
  对象不等价；单字节内 nibble 序按小端字节取（`低` 在前），对拍 oracle 同步。
- `随机UUID` 为 v4 格式（第 13 位固定 4、第 17 位 `8+随机下限(4)`），
  31 次 4 位随机 + 1 次 2 位随机消耗。
- set 无原生类型：集合族用**列表模拟**（插入序），`弹出元素` 取列表首个 ——
  与 CPython set 哈希序不同（对拍 oracle 按插入序镜像）。
- `随机位` 上限 63 位（i64）；`随机0到1`/`正态分布` 等浮点语义与 CPython
  逐位一致（Box-Muller 同构 + 缓存第二个随机值）。
- 函数值/回调不可用（编译期「未定义的段落」）→ 对象池缓存的装饰器类返回
  `空`/池本身，仅标注能力边界。
- **POSIX 实测（2026-09-06，Ubuntu 24.04.4 / clang 18.1.3 / 3.9GB 空闲 / 4 核）**：
  `dv_random` 系列（MT19937 纯整数运算 + `dv_timestamp` 播种）经
  `test_随机_固定种子42逐位对拍_O0` **passed** 实测通过；但同轮全量原生腿回归中
  `test_集合_运算对拍_O0`（`移除元素`）暴露原生腿 `值错误` —— 属 T5C 集合族
  codegen 缺陷（T5C-01~06 同类），**非 T6B 引入**（T6B 的 codegen/runtime 改动
  仅涉 time/sys builtin 与 sys.stderr 链改写，git diff 已核零集合/移除相关代码）；
  T5C 此前「未在 POSIX 实测」，本次为首次 POSIX 暴露，建议归 T5C POSIX 验证单独立项。
  详见 R10-12d T6B POSIX 账。

## R10-12d T6B：时间/系统内建 time.light + sys.light 真 .light 化（2026-09-06）

### 概述
- 任务：建 `stdlib/time.light`、`stdlib/sys.light` 纯光明内建，解锁
  **日期时间轻量 / 时间管理 / 事件总线 / 插件** 四模块的原生腿（native/LLVM）编译。
- 约束：独立本地分支 `task-T6b`；`runtime_typed.c` 仅新增独立函数 `dv_sleep`/`dv_clock`，
  **严禁碰 TLS 段**（归 T7）；`codegen_typed.py` 注册 builtin。
- 反跑判据：`optimize_level=0` 真编译真跑；改回空壳→定向测试立红；时间戳对拍容差 ±2s
  （实际走整数毫秒口径比对，规避 `%g` 打印丢精度）。

### 解锁模块
- **日期时间轻量**：零文本改动解锁，原生 O0 字段/格式对拍 Python 绿。
- **时间管理**：32 导出全真实现（睡眠族/时间戳族/格式化耗时/本地时间/UTC时间/
  时区/计时器/秒表/创建秒表）。
- **事件总线 / 插件**：`sys.light`/`inspect.light` 依赖解锁 + 语法清理；python 腿
  保真绿（test_event_bus 13 passed、agent_loop 签名/stderr 5 passed、test_plugin 全绿）；
  原生全跑被「函数值动态调用」语言级缺口阻断（见 #L-T6B-3）。

### 运行时与 codegen 变更
- `runtime_typed.c`：新增独立函数（文件末尾，未碰 TLS 段）
  - `dv_sleep(double sec)`：Windows `Sleep(ms)` / POSIX `nanosleep`。
  - `dv_clock(void) -> double`：Windows `QueryPerformanceCounter` / POSIX
    `clock_gettime(CLOCK_MONOTONIC)`，返回单调高分辨率秒。
- `codegen_typed.py`：
  - 声明 `declare void @dv_sleep(double)` / `declare double @dv_clock()`。
  - 注册 builtin：`时间戳`/`_dv_timestamp`、`时间格式化`/`_strftime`、
    `睡眠秒`/`_sleep_sec`→`dv_sleep`、`时钟`/`性能计数器`/`单调时钟`/`_clock`→`dv_clock`。
  - `_gen_typed_method_call` 入口加 `sys.stderr.write(文本)`/`sys.stderr.flush()`
    链级改写（`write`→`dv_println` 落原生 stdout；`flush`→no-op），解决事件总线
    错误隔离路径 `sys.stderr` 无属性值表达的问题。

### 缺陷清单（T6B 特有）
- **#L-T6B-1 [中] 跨模块同名段 → codegen 重定义**（同 #L-T5B-1 根因）：
  `time.light` 对外只暴露 ASCII 段名；段内委托 builtin 用 `_dv_timestamp`/`_sleep_sec`/
  `_clock`/`_strftime` 下划线别名防自递归/被上层中文导出捕获（曾因 `时间戳()` 被
  `时间管理.时间戳` 捕获导致无限递归 0xC00000FD，已规避）。
- **#L-T6B-2 [中] 类构造期 `己.方法()` 字段写回丢失**（秒表/计时器后端缺陷）：
  `计时器.结束`/`秒表.停止` 浮点字段算术原生返回 0/负值 → 数值断言不覆盖，仅「不崩」冒烟。
- **#L-T6B-3 [高·语言级缺口] 函数值动态调用**：事件总线 `发布(事件名, 载荷)` 需把
  回调存进监听者表后动态调用 `处理器(事件名, 载荷)`；插件 `触发扩展点(载荷)` 同需
  `回调(载荷)`。原生 codegen 仅支持静态段/builtin 调用，无此 runtime 机制 →
  事件总线/插件原生全跑受阻。按边界交付（解锁 + 语法清理，python 腿保真绿）。
- **#L-T6B-4 [低] `time_ns` 毫秒口径**：秒×1e6 近似（无纳秒 runtime）→ 对拍用整数
  毫秒口径（`time_ns` 原值 vs `time()*1000`，容差 2000）。
- **#L-T6B-5 [低] `gmtime` 实为 `localtime`**：无 UTC 拆字段 runtime；`tm_isdst` 恒 -1；
  不提供 Python `struct_time` 索引/命名元组语义。
- **#L-T6B-6 [低] 字典成员判断**：原生不支持 `X 在/不在 Y`，改用 builtin `字典包含键`
  （事件总线 4 处 + 插件 14 处，共 18 处清理，语义中性）。

### 反跑判据验证
- O0 真编译真跑；改回空壳→定向测试立红；时间戳对拍容差 ±2s（整数毫秒口径）。
- T6B 反跑 **5 测试全绿（Windows 本机 MSVC + Ubuntu 24.04 clang 双平台）**。
- 本机（Windows）曾因空闲 RAM 仅 ~696MB 导致 clang 指令选择 OOM，已用
  `_t6b_native_helper.py` 把「编译+运行」fork 到独立子进程隔离（每次全新 Python，
  拿到与单独运行相同的空闲 RAM）。Ubuntu 3.9GB 空闲无此问题。

### POSIX 实测账（2026-09-06，Ubuntu 24.04.4 / clang 18.1.3 / 3.9GB 空闲 / 4 核）
- 连接 `192.168.0.86`（凭据在 `light-merge/.env` 的 `86SSH_HOST`/`SSH_USER_AI`/
  `SSH_PASS_AI`，**注意外层 `duan-light-merge/.env` 是另一套且 88 仅公钥**）。
- T6B 反跑 `tests/unit/test_T6B_时间系统内建_原生腿.py`：**5 passed / 12.57s**，无 OOM。
  `dv_sleep(nanosleep)` / `dv_clock(CLOCK_MONOTONIC)` 的 POSIX 路径**实测通过**，
  关闭了 T6B 新增项的「未在 POSIX 实测」缺口。
- 全量原生腿回归（T5A/T5B/T5C/T6B）：**33 passed / 1 failed**。
  - 失败：`test_原生腿_T5C_集合随机.py::test_集合_运算对拍_O0` —— `移除元素` 抛 `值错误`。
    **确认非 T6B 回归**：T6B 的 codegen/runtime 改动仅涉 time/sys builtin 与
    `sys.stderr` 链改写，git diff 已核零集合/移除相关代码；该缺陷属 T5C 集合族
    codegen（T5C-01~06 同类），且 T5C 此前「未在 POSIX 实测」，本次为首次 POSIX 暴露。
    建议归 T5C POSIX 验证单独立项（不在 T6B 交付范围）。
  - `dv_random` POSIX 路径随 `test_随机_固定种子42逐位对拍_O0` **passed** 实测通过。

### 能力边界（诚实声明）
- `time.light`：`localtime`/`gmtime` 返回 `本地时间对象`（字段对齐 `struct_time` 常用
  子集，经 `dv_format_time` 按 fmt 拆解）；`gmtime` 实为 `localtime`；`tm_isdst` 恒 -1；
  `time_ns` 毫秒级（无纳秒 runtime）。
- `sys.light`：导出零参取值段（`版本()`/`平台()`/`参数()`），**不导出属性值**；
  `平台()` 用路径分隔符反推（win32/posix 两档，同 `操作系统.本机平台`）；`退出(码)`
  委托 `退出程序`。Python 腿仍走真 CPython `sys`（双轨互不干扰）。
- `事件总线`/`插件`：函数值回调原生不可用（#L-T6B-3），python 腿保真。

### 文件清单
- 新增：`stdlib/time.light`、`stdlib/sys.light`、`stdlib/inspect.light`、
  `tests/unit/_t6b_native_helper.py`、`tests/unit/test_T6B_时间系统内建_原生腿.py`。
- 修改：`src/llvm/runtime_typed.c`（dv_sleep/dv_clock）、
  `src/llvm/codegen_typed.py`（builtin 注册 + stderr shim）、
  `stdlib/事件总线.light`、`stdlib/插件.light`、`stdlib/时间管理.light`。

### 临时文件
- `_taskT6b_*` 已清理（本任务会话的 `_probe_ubuntu.py`/`_run_ubuntu_*.py` 亦为临时探测脚本，不入库）。


## 十九、T6C：向量/复数/颜色/参数解析/编码解码真 .light 化（2026-09-05）

### 概述

5 个纯逻辑空壳模块真 .light 化：向量（22 导出）/ 复数（14）/ 颜色（14）/ 参数解析（11）/
编码解码（45），合计 106 导出。均为「.light 仅声明、同名 .py 有真实现、不依赖 Python 标准库
（只用 math/typing/纯算法）」模块，可直接真 .light 化。

**本批零 runtime / codegen 改动**：`src/llvm/runtime_typed.c`、`src/llvm/codegen_typed.py`
未触碰；未新增注册任何 builtin —— 只用既有 builtin（绝对值/幂/平方根/正弦/余弦/正切/向上取整/
向下取整/对数/时间/时间戳/Base64 编解码/MD5/SHA1/SHA256/替换/分割字符串 等）与纯光明算法：
colorsys（RGB↔HSV / RGB↔HSL）纯光明重写、hex 解析纯实现、url 编解码纯实现、
argparse 核心（参数解析器类/简单解析/快速获取，3 主导出 + 8 辅助导出）纯光明重写。

定向反跑测试 `tests/unit/test_原生腿_T6C_向量复数颜色参数编码.py`（23 用例，显式
optimize_level=0）全绿：18 功能对拍（与 Python math / colorsys / base64 / urllib.parse 手算
对拍一致，数值容差 1e-4）+ 5 反跑（空壳 → NativeImportError）。

### 缺陷清单

#### T6C-01：关键字参数（KeywordArg）对用户段调用不可靠（已规避）

- **现象**：`添加参数(p, "--输出", 短名称="-o", 值类型="整数", 默认值=1)` 中 `默认值`/`值类型`/
  `标志`/`计数` 绑定错位：IR 实证 `添加参数(q,"--a", 默认值=3)` 只推 3 个实参（q, 名, 3），
  `默认值` 绑到槽 2（`短名称`），`名称` 占了 `默认值` 槽；`标志=真` 推出 4 个实参（q,名,空,真）
  绑到槽 3（`值类型`）。
- **根因**：`_merge_kwargs` 尾递归兜底按「追加顺序」绑定参数槽，未按形参名匹配；隔离段落内
  偶发正确（探针 `试参数(1,2,d=9)` 输出 A/1/B/2/C/9/D/0），跨模块 / 长参表场景不可依赖。
- **规避**：模块内部与全部测试一律**全位置参数**调用；声明式形参默认值（`X = Y`）不受影响。

#### T6C-02：运行时 查找 返回字节偏移，与 截取/长 的字符语义不一致（已规避）

- **现象**：`查找("--输出=7", "=")` 返回 8（**字节**偏移），而 `截取`/`长` 按**字符**；
  多字节选项名（如 `--输出=7`）按 `查找`+`截取` 组合解析会错位/截到整串。
- **规避**：参数解析模块内逐字符扫描找 `=`（`如果 词[j] == "="`），不依赖 `查找` 的字节偏移。

#### T6C-03：REF 字符串（列表元素）上 截取/开头 失效（已规避）

- **现象**：`截取(列表[i], 0, 6)` / `开头(列表[i], "-")` 对 REF（列表元素引用）返回整串/不可靠。
- **规避**：解析循环先 `设 词 为 转字符串(列表[i])` 解引用后再做 开头/截取/字符扫描。

#### T6C-04：跨模块同名段落 → LLVM IR 重定义（同 T5C-06，未修，规避）

- 本批 5 模块间无同名导出（五模块联合导入测试通过）；该限制对 stdlib 双模块同名导出普遍成立
  （T5A-05 / T5C-06 同根因），合并期导入组合需注意。

#### T6C-05：GBK/GB2312/GB18030/BIG5 双向转换能力边界（8 导出返回空串）

- 原生腿无这些编码的码表（纯光明无 codecs）；`GBK转UTF8`/`UTF8转GBK`/`GB2312转UTF8`/
  `UTF8转GB2312`/`GB18030转UTF8`/`UTF8转GB18030`/`BIG5转UTF8`/`UTF8转BIG5` 8 个导出
  **返回空串 ""**（诚实边界）；ISO8859-1 双向按字节/码位实现（ASCII 域正确，超 255 返空）。
- `检测编码` 恒返回 `"utf-8"`（无启发式）；`字符集转换`/`字符集转字符串` 仅同编码直通
  （utf-8 直通时对 hex 串做 UTF-8 解码）。

#### T6C-06：类不可实例化、类方法整条不可用（12.1 既有）

- `向量.py`/`复数.py` 的 `类 向量/复数/矩阵` 以**构造函数形态**导出（向量/矩阵/复数/创建向量/
  创建复数/创建矩阵/极坐标转复数），类方法整条不可用；对拍按函数形态验证。

### 能力边界（诚实声明）

- **参数解析**：支持子集 = 位置参数 / 选项参数 / `--x=y` 形式 / 默认值 / 整数·浮点数·字符串
  类型转换 / 标志（布尔）/ 计数 / 子命令 / 帮助文本与用法文本；**不支持** argparse 的
  nargs 列表、choices 校验、互斥组、前缀缩写匹配等高级特性。
- **颜色**：RGB↔HSV / RGB↔HSL 按 colorsys 算法纯光明重写；`颜色混合`/`颜色亮度`/`颜色反转`/
  `颜色变亮`/`颜色变暗`/`颜色透明`/`获取颜色名称` 按 .py 常量表实现（名称映射仅内置常用色，
  未命中返回 `未知`）；hex 解析支持 `#RRGGBB`/`#RGB`/`rgb(r,g,b)`/`r,g,b` 四种形式。
- **向量/矩阵**：`矩阵行列式`/`矩阵逆矩阵` 为 2×2、3×3 通用实现；矩阵乘法要求左列数 == 右行数
  （不合规返回空列表）；`向量夹角` 对零向量返回 0。
- **编码解码**：Base64 / Base32 / Base16 / URL / Hex / Unicode 实体 / UTF-8·ISO8859-1 字符集
  全对拍；GBK 族见 T6C-05。
- **浮点输出**：原生腿 `输出` 用 %g（6 位有效数字）→ 数值对拍统一用 abs diff < 1e-4，
  不做字符串级比对。
- **O0 codegen 既有限制**（T5A 已记录）：负数字面量失效 → 一律 `0 - x`；`输出(列表)`/`输出(字典)`
  显示为 `[]`/`{}` → 逐项输出；含 `为` 关键字的函数名被词法切分（如 `字符集转换为字符串`）→
  编码解码导出以「字符集转字符串」命名提供。

### 反跑判据验证

- 23/23 绿（18 功能对拍 + 5 反跑），显式 `optimize_level=0`，O0 编译运行不崩。
- 反跑采用「OS 临时目录 decl-0 空壳 .light + 同名 .py 影子 + 导入方」编译断言
  `NativeImportError`（匹配 `decl 0 空壳`），并附加对仓库 stdlib 文件的**只读**非空壳检查
  （含段落/函数/类主体 + 导出清单含目标名）。本批环境对工作树写入受限，反跑不触碰
  stdlib 文件；改回空壳 → 编译即红（decl 0 空壳拦截，B9 S1 2.3 机制不变）。
- 五模块联合导入 O0 编译运行不崩（对拍 `5 / 5 / #FF0000 / 2 / aGk=`）。

### 临时文件

- 探针目录 `_taskT6c_probe/` 与探针源文件（编译产物与调试用例）→ **环境 G 盘写入恢复后删除**
  （本任务收尾时写入被平台沙箱拦截，见交付说明）。
