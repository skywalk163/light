# Trae 任务规格书 v3.5

**项目**: 光明（Light）编程语言
**基线**: commit `1df69fc`（v3.4 — 链式调用修复、运算符双轨制、模块路径系统）
**环境**: Windows, Python 3.13, git-bash, 工作目录 `C:\dumatework\light`
**约束**: 零回归（现有 1142 passed / 14 pre-existing failed 不可增加失败数）

---

## 任务 T1: 深层链式赋值修复

### 背景
v3.4 修复了 `己.history.append(内容)` 的链式方法调用，但深层链式赋值仍然不可用：

```python
# Python 原始代码
self.data.value = 10
```

当前光明语法 `己.data.value = 10` 会报错 `无法识别的语法元素：'='`。

### 根因
`_parse_self_assignment`（`src/parser_stmt.py` 约 400-470 行）在检测到 `己.属性名` 后只解析了第一层成员访问，就检查是否跟赋值运算符。如果跟的是另一个 `.`（如 `己.data.value`），它不知道如何处理。

### 目标
让 `己.属性名.子属性名 = 值` 正确解析为 `self.属性名.子属性名 = 值`。

### 涉及文件
- `src/parser_stmt.py` — `_parse_self_assignment` 方法（约 390-500 行）

### 实现方案
在 `_parse_self_assignment` 中，解析完 `己.属性名` 后，如果遇到 `.` 而非赋值运算符，继续循环解析后续的 `.子属性名` 链，构建嵌套的 `MemberAccess(MemberAccess(Identifier("self"), "data"), "value")`，直到遇到赋值运算符。

### 验收标准
```python
# 以下代码必须正确解析和生成
函数 测试():
    己.data.value = 10。        # → self.data.value = 10
    己.config.timeout = 30。    # → self.config.timeout = 30
    己.cache["key"] = "val"。   # → self.cache["key"] = "val" (索引赋值也支持)
```

### 测试
```bash
cd C:\dumatework\light
python -m pytest tests/test_edge_cases.py tests/test_class_definition.py tests/test_class_advanced.py -x -q --tb=short
```
确保零新增失败。

---

## 任务 T2: 转译器增加 match-case 和 async/await 支持

### 背景
`tools/ai_copilot/py2duan_transpiler.py` 是 Python→光明 单文件转译器。当前有以下 Python 语法无法转译，会直接跳过或报错：

1. `match/case` 语句 → 应转译为光明的 `匹配/情况` 语法
2. `async def` / `await` → 应转译为光明的 `异步 函数` / `等待`
3. 函数参数默认值 `def f(x, y=10):` → 光明已支持 `函数 f(x, y=10):`

### 涉及文件
- `tools/ai_copilot/py2duan_transpiler.py` — `Py2DuanTranspiler` 类

### 目标

#### 2.1 match-case 转译
```python
# Python
match status:
    case 200:
        print("OK")
    case 404:
        print("Not Found")
    case _:
        print("Unknown")
```
转译为：
```
匹配 status:
    情况 200:
        打印("OK")。
    情况 404:
        打印("Not Found")。
    默认:
        打印("Unknown")。
结束匹配。
```

#### 2.2 async/await 转译
```python
# Python
async def fetch_data(url):
    response = await get(url)
    return response
```
转译为：
```
异步 函数 fetch_data(url):
    设 response 为 等待 get(url)。
    返回 response。
```

#### 2.3 函数默认参数
```python
# Python
def greet(name, greeting="Hello", times=1):
    for i in range(times):
        print(f"{greeting}, {name}!")
```
转译为：
```
函数 greet(name, greeting="Hello", times=1):
    遍历 i 于 范围(times):
        打印(f"{greeting}, {name}!")。
```

### 验收标准
写一个测试脚本 `tools/ai_copilot/test_transpiler_v2.py`，包含以上三种语法的 Python 代码，转译后输出正确的光明代码，且光明代码能被 `DuanParser` 正确解析。

### 测试
```bash
cd C:\dumatework\light
python tools/ai_copilot/test_transpiler_v2.py
python -m pytest tests/ -q --tb=no -k "not antlr" --ignore=tests/test_module_system.py --ignore=tests/test_comprehensive.py --ignore=tests/test_ffi.py --ignore=tests/test_ffi_at_c.py --ignore=tests/test_ffi_phase2.py --ignore=tests/test_ffi_phase3.py --ignore=tests/test_ffi_phase4.py --ignore=tests/test_llvm_async.py --ignore=tests/test_lsp_protocol.py --ignore=tests/test_lsp_protocol_full.py --ignore=tests/test_module_resolver.py --ignore=tests/test_advanced_semantic.py --ignore=tests/test_modern_features.py --ignore=tests/test_async.py --ignore=tests/test_ternary_antlr.py --ignore=tests/test_light_stdlib.py --ignore=tests/test_light_stdlib2.py --ignore=tests/test_json_import.py --ignore=tests/test_interface.py
```

---

## 任务 T3: 装饰器转译增强

### 背景
当前转译器无法正确处理 Python 装饰器：
- `@staticmethod` → 光明有 `静态` 关键字
- `@classmethod` → 光明有 `类方法` 关键字  
- `@property` → 光明有 `特性` 关键字
- 自定义装饰器 `@my_decorator` → 光明有 `标注` 语法

### 涉及文件
- `tools/ai_copilot/py2duan_transpiler.py`

### 目标
```python
# Python
class MyClass:
    @staticmethod
    def helper():
        return 42
    
    @property
    def count(self):
        return len(self.items)
    
    @my_decorator
    def process(self):
        pass
```
转译为：
```
类 MyClass:
    静态 函数 helper():
        返回 42。
    
    特性 函数 count():
        返回 己.items.长度()。
    
    标注 my_decorator
    函数 process():
        过去。
```

### 验收标准
在 `test_transpiler_v2.py` 中增加装饰器测试用例，转译后光明代码能被 `DuanParser` 正确解析。

---

## 任务 T4: TokenType.DOT 拆分（成员访问统一前置工作）

### 背景
当前 `TokenType.DOT` 同时承担两个语义：
1. 中文句号 `。`（语句结束符）
2. 英文点号 `.`（成员访问符）

这导致成员访问统一（`的` vs `.`）无法实施。需要将 `TokenType.DOT` 拆分为：
- `TokenType.PERIOD` — 中文句号 `。`（语句结束）
- `TokenType.DOT` — 英文点号 `.`（成员访问）

### 涉及文件
- `src/tokens.py` — 新增 `PERIOD` token 类型
- `src/lexer.py` — `。` 映射到 `PERIOD`，`.` 保持 `DOT`
- `src/parser_stmt.py` — 所有消耗句号的地方从 `TokenType.DOT` 改为 `TokenType.PERIOD`
- `src/parser_expr.py` — 成员访问的 `.` 保持 `TokenType.DOT` 不变

### 验收标准
1. 所有现有测试通过（零回归）
2. `。` 和 `.` 在 lexer 层面被正确区分为不同的 token 类型
3. 成员访问 `.` 仍正常工作
4. 语句结束 `。` 仍正常工作

### 注意事项
- 这是一个**重构性变更**，影响面广（parser_stmt.py 中大量 `TokenType.DOT` 引用需要改为 `TokenType.PERIOD`）
- 建议用全局搜索替换 + 逐一审查的方式
- 先用 `grep -c "TokenType.DOT" src/parser_stmt.py src/parser_expr.py` 统计影响范围
- `src/parser_expr.py` 中的 `TokenType.DOT` 引用**不需要改**（那些都是成员访问的 `.`）

### 测试
```bash
cd C:\dumatework\light
python -m pytest tests/ -q --tb=short -k "not antlr" --ignore=tests/test_module_system.py --ignore=tests/test_comprehensive.py --ignore=tests/test_ffi.py --ignore=tests/test_ffi_at_c.py --ignore=tests/test_ffi_phase2.py --ignore=tests/test_ffi_phase3.py --ignore=tests/test_ffi_phase4.py --ignore=tests/test_llvm_async.py --ignore=tests/test_lsp_protocol.py --ignore=tests/test_lsp_protocol_full.py --ignore=tests/test_module_resolver.py --ignore=tests/test_advanced_semantic.py --ignore=tests/test_modern_features.py --ignore=tests/test_async.py --ignore=tests/test_ternary_antlr.py --ignore=tests/test_light_stdlib.py --ignore=tests/test_light_stdlib2.py --ignore=tests/test_json_import.py --ignore=tests/test_interface.py
```

---

## 通用约束

1. **不要修改以下文件**（DuMate 正在并行使用）：
   - `src/parser_core.py` — DuMate 正在改善错误提示
   - `src/keywords.py` — DuMate 正在分析关键词精简
   - `stdlib/` 目录 — DuMate 正在设计 lightpub 集成

2. **编码规范**：
   - 代码正文用 ASCII 半角标点
   - Python 文件写 `encoding="utf-8"`
   - `.sh` 文件用 LF 行尾
   - 全角字符（中文标点）不要嵌入源代码字符串之外

3. **提交规范**：
   - 每个 task 独立 commit
   - commit message 格式：`fix: T1 深层链式赋值修复` / `feat: T2 转译器 match-case/async 支持` 等
   - 不要 push，只 commit 到本地

4. **测试规范**：
   - 每完成一个 task 跑一次测试套件
   - 确保零新增失败
   - 如果修复了 pre-existing 失败，在 commit message 中说明
