# 已知问题与技术债务清单

**版本**: v6.0.0  
**更新日期**: 2026-10-29  
**说明**: 本文档记录了光明 v6.0 中已知的问题、限制和技术债务，供开发者和用户参考。

---

## 一、严重问题

### P0 — 影响核心功能

- [ ] **[P0] 自举编译器覆盖范围**：当前自举编译器覆盖了大部分语法，但极边缘特性（如复杂嵌套泛型）尚未完全自举。
  - **影响**：少数边缘场景需要通过手动实现的编译器处理
  - **计划**：v6.1 中完成全覆盖

- [ ] **[P0] LLVM 后端标准库覆盖**：部分标准库函数在 LLVM 后端尚未完全实现，会回退到 Python 解释执行。
  - **影响**：使用 `--native` 编译时，部分标准库调用性能未达最优
  - **计划**：v6.1 中逐步补全

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

上游（v3 语句类节点共 27 个，其中 **10 个**没有适配层转换器）：
`AssertStmt`、`DecoratorDefinition`、`EmbedBlock`、`FFIFunctionDecl`、
`FFIVarArgsDecl`、`PassStmt`、`RunAsyncStmt`、`ScopeDeclStmt`、
`TypeCheckToggleStmt`、`YieldStmt`。

下游（`_gen_statement` 只有 **16** 条分支：`VariableDeclaration`、`Assignment`、
`SelfAssignment`、`CompoundAssignment`、`IfStatement`、`ForeachStatement`、
`WhileStatement`、`ReturnStatement`、`BreakStatement`、`ContinueStatement`、
`PrintStatement`、`TryStatement`、`ThrowStatement`、`ExpressionStatement`、
`ImportStatement`、`AsyncScope`）。适配层能产出、但这 16 条都不覆盖的 legacy
节点有 **28 种**，落链尾兜底，其中作为语句出现的主要是
`MatchStatement`、`WithStatement`、`DestructuringAssignment`、`SegmentDefinition`
（嵌套段落）、`InterfaceDefinition`、`MethodDefinition`、`AttributeDeclaration`。

**注意 `ImportStatement` 是 `pass`**：原生后端把导入语句**编成空操作**，既不报错
也不加载模块。它不在「会报错」清单里，属于另一类问题（静默无效），本轮未动。

### 9.3 实测分桶（24 条片段，`compile_source_typed` 直跑）

| 桶 | 条数 | 成员 |
|----|------|------|
| 能编 | 16 | 赋值/变量声明、`如果`、`遍历`、`当`、段落、`返回`、`跳出`、`继续`、`尝试`/`捕获`、`抛出`、`打印`、`引`（空操作）、类（非嵌套）、接口、`导出`、`延迟` |
| 明确拒绝 | 6 | `全局`(ScopeDeclStmt)、`外层`(先撞 SegmentDefinition)、`生成`(YieldStmt)、`断言`(AssertStmt)、类型别名(TypeAlias)、嵌套类(ClassDefinitionWithNested) |
| 更早的层拦下 | 2 | `匹配`（v3 解析器语法就没通）、`异步域`（同上） |

`外层` 报的是 `SegmentDefinition` 而不是 `ScopeDeclStmt`：`外层` 只能写在嵌套
段落里，而**嵌套段落本身原生就不支持**，所以先被它拦下。报真正拦下它的那一层，
不编造。

守卫在 `tests/unit/test_llvm_stmt_coverage.py`（正跑 6 条 + 反跑 5 条 + 2 条静态
断言，共 13 个用例）。

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

### 12.2 `cli/lightc.py` 对任何输入必崩

`SemanticAnalyzer()` 少传 `module` 参数 → `TypeError`。凡是文档/示例里写
`python cli/lightc.py <文件>` 的都会撞上（`examples/harness/M2_流式对话.light` 的使用说明
原先就是这么写的，已改为 `python cli/light.py run <文件>`）。
`tests/conftest.py` 的 `analyzer` fixture 是同一处签名不匹配，当前没有用例消费它，
所以门禁同样看不见。

### 12.3 codegen_typed 的包装段不建自己的槽位池

`_gen_typed_method` / `_gen_async_segment` 既不建自己的池、也不重置 `_temp_slot_index`，
会沿用上一个函数残留的池寄存器——跨函数引用寄存器，IR 本来就不合法。现有链路碰不到
（类/方法用例全绿），但这是潜伏项。

### 12.4 `_inline_small_functions_pass` 过度激进

会把「指令数 ≤5 且被调用 ≤1 次」的非 main 函数整段删掉，不看是否还有其它引用形式。

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

### 14.5 假测试门禁的覆盖缺口（合并期复核登记，待裁决后再动）

以下四条都不是「写错了」，是**覆盖范围**问题，动了会显著改变基线量级，
所以只登记不擅自扩：

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
4. **防造假形态零命中**：`assert_quality.py` 的两个预防性形态
   （`trivial-ge0` / `returncode-in`）与 `bootstrap_rate.py` 的自导入检查
   目前都是 0 命中。报文已显式标注「预防性、未拦任何存量」，不算假绿，
   但也要清楚它们当前不产生任何拦截力——真正在起作用的是 `decl >= 1`。

**第 1、2 条的裁决（2026-08-23，用户）：维持保守口径，不扩。** 理由是
「取保守口径、基线控制在 390 上下」这条既有裁决优先；两类全扩会把基线
从 474 再推到约 720，收益（多冻结一批存量）远小于口径反复的代价。
登记在此备查：将来若要扩，必须连同基线量级一起重新裁决，不许顺手扩。


