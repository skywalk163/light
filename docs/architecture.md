# 光明编译器架构设计

> **版本：** v7.0.0（`src/version.py`）
> **最后校对：** 2026-08-29（对照源码逐段核实 + 实测）
>
> ⚠️ **本文件于 2026-08-29 整体重写。** 旧版本描述的是一套**并不存在**的编译器
> （`src/ir.py` / `src/codegen_x64.py` / `src/linker.py` 三文件在仓库中从未存在），
> 且被 mkdocs 导航与 `docs/index.md` 收录，属对外公开的错误信息。重写以源码为准。

---

## 0. 先厘清一个高频误读：L0–L7 是「语法层级」，不是编译器分层

外部常把光明的 `L1` / `L2` / `L3` 读成「词法层 / 语法层 / 编译层」。**这是错的。**

`src/version.py`：

```python
SUPPORTED_LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"]
```

这 8 级指的是**同一种语言的不同文体与方言层级**，跟编译器内部阶段毫无关系：

| 层级 | 含义 | 例子 |
|---|---|---|
| **L0** | 核心字集（30 字冻结，永不更改） | `若 设 返 段 试 捕 抛 终 自 承 接 配 导 出` / `类 空 真 跳 遍 当 为 否` |
| **L1** | 白话体（青少年 / 教学） | `加上`/`减去`/`乘以`/`除以` 作 `+ - * /` 的别名 |
| **L2** | 文言体（商用工程，强类型） | 显式类型标注、英文标点 |
| **L3** | 领域嵌入 | 内嵌 SQL（sqlite3 参数化）/ 正则 / 数学（sympy） |
| **L4** | 外语引用 | 内嵌 Python / C / Go / MoonBit，沙箱隔离 |

**编译器分层请看下节**，与 L0–L7 完全是两套坐标系。

---

## 1. 总览：5 段前端 + 代码生成 + 三后端

```
                        .light 源文件
                             │
    ═══════════════ 编译前端（LightCompiler.compile()）═══════════════
                             │
    ┌────────────────────────▼────────────────────────┐
    │ 1. 词法分析      Lexer          → Token 流       │  src/lexer.py
    ├─────────────────────────────────────────────────┤
    │ 2. 语法解析      LightParser    → v3 AST        │  src/parser_stmt.py
    │                                                 │  src/parser_expr.py
    │                                                 │  src/parser_core.py
    ├─────────────────────────────────────────────────┤
    │ 3. AST 适配      AstAdapter     → 统一 AST      │  src/compiler.py:217
    │                  (v3 AST → ast_nodes)           │  src/ast_nodes.py
    ├─────────────────────────────────────────────────┤
    │ 4. AST 优化      OPTIMIZERS     → 优化后 AST    │  src/optimizer/
    ├─────────────────────────────────────────────────┤
    │ 5. 类型检查      TypeInferencer → 类型标注 AST  │  src/type_inferencer.py
    │                  TypeChecker                    │  src/type_checker.py
    └────────────────────────┬────────────────────────┘
    ═════════════════════════╪══════════════════════════════════════
                             │  三级缓存（进程内）：Token / AST / Codegen
                             ▼
                        代码生成 + 后端分叉
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
  ┌───────────┐      ┌─────────────┐      ┌──────────────┐
  │ SRC 后端  │      │ ANTLR 后端  │      │ 原生腿 LLVM  │
  │ （默认）  │      │             │      │              │
  │ → Python  │      │ ANTLR4 解析 │      │ → LLVM IR    │
  │   后 exec │      │ + 解释      │      │ → clang      │
  │           │      │             │      │ → 原生 exe   │
  └───────────┘      └─────────────┘      └──────────────┘
```

### 权威判据

前端 5 段是源码注释里写死的，见 `src/compiler.py:990` `LightCompiler.compile()`：

```python
# 1) 词法分析（使用缓存）        tokens  = self.tokenize(source)
# 2) 语法解析（原始 v3 AST）     raw_ast = self.parse_raw(source)
# 3) AST 适配                   our_ast = self.adapt(raw_ast)
# 4) 优化（默认开启）            our_ast = self.optimize_ast(our_ast)
# 5) 类型检查                   self.type_check(our_ast, source)
```

---

## 2. 各阶段详解

### 2.1 词法分析（Lexer）

**文件**：`src/lexer.py`（167 KB，全仓最大单文件）

三层分词机制（决策 29）：

- **类型切换自动分词**：`甲加1` → `[甲] [加] [1]`
- **双字关键词优先匹配**：`定义甲` → `[定义] [甲]`
- **元数驱动参数收集**：`打印 甲`（元数=1）→ `[打印] [甲]`

Token 类型定义见 `src/tokens.py`。

> ⚠️ 词法器的贪心切分是本项目最多的坑源（方法名以关键字开头被切开、
> 属性名以作用域内用户定义名开头导致静默错编成 `==`）。
> 详见 [光明语言排错手册](../.workbuddy/) 与 `docs/known_issues.md`。

### 2.2 语法解析（Parser）

**文件**：`src/light_parser_v3.py`（驱动）+ `parser_stmt.py`（328 KB）/ `parser_expr.py`（163 KB）/ `parser_core.py`（27 KB）

递归下降解析器，输出 **v3 AST**（`src/ast_nodes_v3.py`，51 KB）。

同时支持缩进语法与花括号语法。关键字表见 `src/keywords.py`（23 KB，含 L0 核心字冻结表）。

### 2.3 AST 适配（AstAdapter）

**文件**：`src/compiler.py:217`

把 v3 解析器产出的 AST 转换为编译器内部统一的 `ast_nodes.Module`（40 KB）。
这是一层显式适配，不是可省略的胶水——两套 AST 的节点模型不同
（例如 v3 的切片表达式 `SliceExpr` 在统一 AST 里被降级成 `FunctionCall`）。

### 2.4 AST 优化

**文件**：`src/optimizer/`

⚠️ **注意：目录里有 6 个 pass 实现，但只有 3 个接进了管线。**

`src/compiler.py:41`：

```python
OPTIMIZERS = [
    DeadCodeEliminationOptimizer,   # 死代码消除
    ConstantFoldingOptimizer,       # 常量折叠
    LoopInvariantOptimizer,         # 循环不变量外提
]
```

| Pass | 实现文件 | 是否接入 |
|---|---|---|
| 死代码消除 | `src/optimizer/dead_code.py` | ✅ |
| 常量折叠 | `src/optimizer/constant_fold.py` | ✅ |
| 循环不变量外提 | `src/optimizer/loop_invariant.py` | ✅ |
| 公共子表达式消除 | `src/optimizer/cse.py` | ❌ 已实现未接入 |
| 函数内联 | `src/optimizer/inline.py` | ❌ 已实现未接入 |
| 窥孔优化 | `src/optimizer/peephole.py` | ❌ 已实现未接入 |

### 2.5 类型检查

**文件**：`src/type_inferencer.py`（111 KB）/ `src/type_checker.py`（61 KB）/ `src/type_system.py`（66 KB）

- `TypeInferencer` 做 HM 全局类型推断，产出符号表与类型标注
- `TypeChecker` 做校验，错误进统一收集器 `CompilerErrorCollector`
- 编译器实例上可用 `CompilerQuery` 查询推断结果（`src/compiler.py:1621`）

标准库符号由 `ModuleResolver.preload_builtins()` 预加载后注入符号表
（`src/compiler.py:966` `_inject_stdlib_symbols`）。

### 2.6 代码生成与后端

| 后端 | CLI 取值 | 实现 | 产物 | 状态 |
|---|---|---|---|---|
| **SRC**（默认） | `src` | `src/code_generator.py`（268 KB）<br>`src/code_generator_unified.py`（80 KB） | Python 源码 → `exec` | 主力，生产可用 |
| **ANTLR** | `antlr` | `antlrparser/` | ANTLR4 解析 + 解释 | 兼容旧语法 |
| **原生腿** | `native` / `llvm-typed` | `src/llvm/codegen_typed.py`（213 KB）<br>`src/llvm/compiler.py`（54 KB）<br>`src/llvm/runtime_typed.c`（192 KB） | LLVM IR → clang → 原生 exe | 生产可用，**覆盖有限** |

> `native` 与 `llvm-typed` 是**同一个东西**（`native` 是一等别名，B9 S1 2.2）。
> 旧的 `--backend llvm`（string 死腿，引用不存在的 `runtime.c`）已在 B9 移除，CLI 不再接受该值。

另有 `c_backend.py`（仓库根）、`llvm_backend.py`（仓库根）、`src/wasm_target.py` 三个**独立实验性后端**，
不通过上述 CLI 的 `--backend` 分派，与 `src/version.py` 里
`COMPILER_BACKENDS = ["python", "llvm", "c", "wasm"]` 的声明对应——
该声明是**能力清单**，不是 CLI 可选项列表，两者不要混为一谈。

原生腿的能力边界以 `docs/原生腿能力边界.md` 为准，
并由 `tests/unit/test_native_leg_capability.py` 做源码级守单。

---

## 3. 模块系统

**文件**：`src/module_resolver.py`（50 KB）

搜索顺序（`find_module`，`:263`）：

1. `from_dir`（导入方所在目录）
2. `self.search_paths`
3. 环境变量 `LIGHT_PATH`（`os.pathsep` 分隔）

模块文件优先 `.light`，其次 `.py`。未找到抛 `ModuleNotFoundError` 并列出全部搜索路径。

> ⚠️ **已知缺口**：项目自身的 `stdlib/` 目录默认不在 `search_paths` 里，
> 跨目录引用 stdlib 模块需显式设置 `LIGHT_PATH`。详见 `docs/原生腿能力边界.md` §10。

---

## 4. 性能特征（2026-08-29 实测）

环境：Windows / CPython 3.13.14 / clang 22.1.8。
基准：斐波那契(26) 递归 + 300 万次循环累加，取 3 次最小值。

| 路径 | 耗时 | 相对手写 Python |
|---|---|---|
| 手写 Python（基线） | 0.947 s | 1.00x |
| SRC 后端**转译产物** | 0.983 s | **1.03x** |
| `light run` 全链路 | 1.874 s | 1.98x |
| 原生腿**执行**（不含编译） | 0.215 s | **0.23x（快 4.4 倍）** |

### 关键结论

1. **运行时几乎零开销。** 转译产物与手写 Python 同速（1.03x）。
   生成的 Python 无包装层，例：

   ```python
   def 斐波(n):
       if (n < 2):
           return n
       return (斐波((n - 1)) + 斐波((n - 2)))
   ```

2. **慢的是启动，不是运行。** `light run` 的 1.874 s 拆解：

   | 阶段 | 耗时 |
   |---|---|
   | CPython 启动 + site/sitecustomize | ~0.34 s |
   | 导入编译器（925 KB 源码；lexer 94ms / parser_expr 101ms / ast_nodes 99ms） | 0.239 s |
   | **`compile()` 前端 5 段**（15 行源文件） | **0.059 s** |
   | 代码生成 + 写文件 + 执行 | 其余 |

3. **前端本身就很快**（59 ms）。瓶颈是每次 `light run` 都要重新导入编译器。
   `CompilerCache`（`src/compiler.py:69`）**只在进程内有效**，跨进程不复用。

4. **原生腿执行真快，但编译一次要 ~5 s**（clang 编译 192 KB 的 `runtime_typed.c`）。
   适合「编译一次、跑很多次」，不适合短任务。

> ⚠️ `docs/性能基准_vs_Python_v2.md`（v5.5，2026-08-07）中 LLVM 相对 SRC
> 的 40x–1600x 数字**已过期**，本次实测仅 8.7x。该文件已加过期标注。

---

## 5. 三套并行实现

| 实现 | 位置 | 用途 |
|---|---|---|
| 手写 | `src/` | 主力，`--backend src` |
| ANTLR4 | `antlrparser/` | 兼容旧语法，`--backend antlr` |
| 自举 | `bootstrap/` | 用光明写的光明编译器（Level 3–7） |

`src/version.py` 自述：「三套并行实现：手写 src/、ANTLR4 antlrparser/、自举 bootstrap/（Level 3–7）」。

---

## 6. 扩展计划

### 近期（按优先级）

- [ ] **原生腿：识别并跳过 Python 生态模块**（`导入 asyncio` / `codecs` 当前被当 `.light` 找文件，
      导致任何依赖 Python 生态的项目必然编译失败）—— 当前 P0 阻塞项
- [ ] **原生腿：把项目 `stdlib/` 自动纳入 `search_paths`**（现需手设 `LIGHT_PATH`）
- [ ] **跨进程编译缓存**（现每次 `light run` 重付 ~1 s 启动税）
- [ ] 接入已实现未上线的 3 个优化 pass（CSE / 内联 / 窥孔）

### 远期

- [ ] 完善标准库实现
- [ ] 支持 ARM64 原生后端
- [ ] 完整的调试器与性能分析工具
- [ ] 自举率继续提升（见 `docs/自举率报告.md`）

---

## 参考资料

- [编译器内部设计](编译器内部设计.md) — 各阶段的深入说明
- [原生腿能力边界](原生腿能力边界.md) — LLVM 后端支持/不支持的源码级清单
- [从光明到 LLVM](从光明到LLVM.md) — 原生腿设计
- [从光明到 Python](从光明到Python.md) — SRC 后端设计
- [模块系统设计](module_system_design.md)
