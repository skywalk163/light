# A9-S1 语言层实现报告

## S1.1 类体接受 `异步 段落`

### 问题
类体内 `异步 段落 名字():` 在 parser 的类体循环中无 `异步` 关键字分支，直接落到 else 报错「类体内不支持的成员声明：'异步'」。stdlib/流式.light 的四个异步读腿只能甩到模块级。

### 根因
- `parser_stmt.py` 类体循环（:4274-4493）只处理 `段落`/`函数`/`段` 关键字，没有 `异步`/`异` 分支。
- `code_generator.py` `_generate_method`（:2512）始终发 `def`，无 `async def` 分支。
- `MethodDefinition` 的 `__slots__` 没有 `modifiers` 字段，但 `_parse_async_paragraph` 返回的是 `Paragraph` 节点（有 `modifiers` slot），所以可以直接复用。

### 修改
1. **`src/parser_stmt.py`** — 类体循环中 `_is_paragraph_kw` 分支之前，新增 `异步`/`异` 关键字分支：
   - 调用 `_parse_async_paragraph()`（返回 `Paragraph` 节点，`modifiers` 含 `'异步'`）
   - 设置 `access_modifier`、`is_static`、`is_classmethod`
   - 追加到 `methods` 列表

2. **`src/code_generator.py`** — `_generate_method` 中 `def` 行之前，新增异步检测：
   ```python
   is_async = '异步' in (getattr(method, 'modifiers', []) or [])
   def_prefix = "async def" if is_async else "def"
   ```
   - `getattr(method, 'modifiers', [])` 对 `MethodDefinition`（无 modifiers slot）返回 `[]`，不影响同步方法
   - 对 `Paragraph`（有 modifiers slot）正确检测 `'异步'`

### 验证
- `async def 读取(self, 路径):` 正确生成
- 同步方法仍生成 `def`（不受影响）
- `异` 单字别名也正确工作
- async 方法内可使用 `等待`（await）
- 类中混合同步/异步方法正确

---

## S1.2 真 `最终`(finally) 语义 + 捕获折叠 bug 修复

### 问题
`_parse_catch_clause` 中 catch 块体使用裸 `_parse_body()` 解析。`_parse_body` 的契约是「调用者已消耗当前块的 INDENT」，直接调用而不先消耗 INDENT 时，本块自己的 INDENT 被当成嵌套记进 depth（0→1），块结束的 DEDENT 只把 depth 减回 0 而不停止循环。当 catch 是最后一个子句（后面是普通兄弟语句），没有任何关键字 break 条件，后续语句被静默吞入 except 块。

### 根因
- `_parse_clause_body`（:2851-2887）的 docstring 已精确描述了这个 bug 模式。
- `最终` 块已在 :3067 使用 `_parse_clause_body()`（此前已修），但 `捕获` 块仍在 :2982 用裸 `_parse_body()`。
- `try` 块也在 :3031 用裸 `_parse_body()`，虽然「碰巧」能停住（后面紧跟 `捕获`/`最终`/`结束` 关键字触发 break），但 DEDENT 消耗路径不规范。

### 修改
1. **`src/parser_stmt.py` `_parse_catch_clause`** — catch 块体从 `_parse_body()` 改为 `_parse_clause_body()`：
   ```python
   # 修改前
   catch_body = self._parse_body()
   # 修改后
   catch_body = self._parse_clause_body()
   ```

2. **`src/parser_stmt.py` `_parse_try_stmt`** — try 块体从 `_parse_body()` 改为 `_parse_clause_body()`：
   ```python
   # 修改前
   try_body = self._parse_body()
   # 修改后
   try_body = self._parse_clause_body()
   ```

### 验证
- **catch 折叠修复**：`try/catch` 后的同级 `输出("after")` 正确生成在 `except` 块外（与 `try` 同缩进）
- **正常路径**：try 无异常 → after 执行（catch 不执行）
- **异常路径**：try 有异常 → catch 执行 → after 执行
- **finally 正常路径**：try → finally → after
- **finally 异常路径**：try → catch → finally → after
- **finally + return**：return 时 finally 仍执行，return 后的语句不执行
- **多 catch 块**：按类型匹配正确捕获
- **try/finally 无 catch**：正确解析
- **嵌套 try/catch/finally**：内外层都正确

---

## 改动文件清单

| 文件 | 改动 |
|------|------|
| `src/parser_stmt.py` | 类体循环加 `异步`/`异` 分支；catch/try 块体改用 `_parse_clause_body()` |
| `src/code_generator.py` | `_generate_method` 加 `async def` 检测分支 |
| `tests/test_A9_language.py` | 新增 16 个测试用例（S1.1 × 6，S1.2 × 10） |

## 测试结果

```
302 passed, 1 skipped, 0 failed
```
（含 16 个 A9 新测试 + 286 个已有测试，全部通过）
