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
| 能编 | 16 | 赋值/变量声明、`如果`、`遍历`、`当`、段落、`返回`、`跳出`、`继续`、`尝试`/`捕获`、`抛出`、`打印`、`引`（B9 S1 起真导入，见上方说明）、类（非嵌套）、接口、`导出`、`延迟` |
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

### 15.1 `除以` 的算术语义

**同一份 `.light`，两条后端算出不同答案**：

- `打印 4 除以 3。`
  - 转译后端（光明 → Python）：`1.3333333333333333`（Python `/` 是真除法）
  - 原生腿（LLVM/C）：`1`（原生腿一切数字是 `i64`，`除以` 落到 C 的 `/`，整数截断）

**为什么现在不修**：修法有两条且都动语义面，需要裁决而不是顺手改——
(a) 原生腿补浮点类型，让 `除以` 在两条腿上都是浮点除法；
(b) 把 `除以` 明确定成「整数相除得整数」，靠 `整除` / 显式浮点字面量区分。
`docs/光明-完整规范文档.md` 现在把 `除以` 写作 `/`、`整除` 写作 `//`，按文档口径应当走 (a)。

**当前的止损**：`tests/test_llvm_c3_expr.py` 的双后端一致性 6 例全部用 `整除`
绕开这一处，并在用例里写明缘由——**不是躲过去了，是把它圈出来了**。谁修完这条，
把那 6 例里的 `整除` 换回 `除以`，那组用例即刻变成这条修复的判据。

### 15.2 stdout 的字节编码（Windows 上非 ASCII 输出不同字节）

同一句 `打印 "光明"。`，输出重定向进管道/文件时：

- 原生腿的 exe：吐 UTF-8 字节 `e5 85 89 e6 98 8e`
- 转译后端（`light run`，本质是个 Python 进程）：吐**平台 ANSI 代码页**字节，
  中文 Windows 上是 cp936 的 `b9 e2 c3 f7`

即「同一个程序，两条腿产出的文件编码不同」。ANSI 那边还会在无法映射的字符上
直接抛 `UnicodeEncodeError`。

**根因**：转译后端没有钉死自己的 `sys.stdout` 编码，跟随 `locale.getpreferredencoding()`；
原生腿写的是裸字节，源码是 UTF-8 就是 UTF-8。

**未修的原因**：改法（在 CLI 入口 `reconfigure(encoding='utf-8')`）动的是所有
转译后端用户的既有输出行为，且第四轮已经踩过「reconfigure 顺手把 errors 改成
strict、整场级联炸」的坑（见十四节），要单独一轮带反跑地做。

**当前的止损**：`tests/test_llvm_c3_expr.py::_run_transpiled` 给子进程钉
`PYTHONIOENCODING=utf-8`，把两边拉到同一编码再比字符。B7 原稿没钉，所以那 6 例
在外部已设 `PYTHONUTF8` 的机器上绿、在没设的机器上红（合并期实测 2 红），
是「本机绿 CI 红」的又一例。

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

### 17.2 #L2 [中] POSIX 侧原生 TLS 是 stub（有壳无实现）

- 证据：`runtime_typed.c:5747-5778`，POSIX 分支 `backend=none`、`dv_tls_wrap` → NULL，
  任何握手调用立即失败。Windows 侧的 Schannel 后端是真的。
- 口径纠正：`docs/POSIX验证报告_Linux.md` 已把「`dv_tls_last_error()` POSIX 未导出」
  的怀疑证伪——它定义在 `runtime_typed.c:5107`、在 `#ifdef _WIN32` 之前无条件存在，
  POSIX 上返回可读错误 `本平台未实现原生 TLS：当前只有 Windows Schannel 后端（POSIX 待补 mbedTLS）`。
  所以缺的是**实现**，不是错误可见性。
- 排期：第九轮 M23（原生腿）候选。补 mbedTLS/OpenSSL 后端属新增能力，不在本轮范围。
- 记账口径：凡文档/清单写「原生 TLS 可用」的地方，必须标 **Windows-only**。

### 17.3 #L5 [中] 溢出文件的**绝对路径**被拼进标准输出（跨平台真缺陷，Windows 是假绿）

报告把它记成「Linux 特有」，**本轮核查后改判：两个平台都漏，Windows 只是断言瞎了**。

- 真正的泄漏点：`stdlib/进程树.light:248` ——
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
- 修法（未做，排期第九轮）：`进程树.light:248` 改成回显 `os.path.basename(己.溢出路径)`
  —— 但 `进程树` 是通用库、调用方不一定有沙箱，得先定「相对谁」的口径；
  同时把 `:666` 的断言改成大小写不敏感（否则 Windows 上继续假绿，改完也测不出）。


