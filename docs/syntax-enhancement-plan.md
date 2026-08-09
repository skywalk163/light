# 语法增强 — 迭代 1 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 subagent-driven-development（推荐）或 executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 增强光明 v3 解析器的异常处理（支持异常类型过滤）、完善 from...import...as 别名支持，并新增异常处理测试。

**架构：** 修改递归下降解析器 `DuanParser` 中的 TryStmt AST 节点和导入解析逻辑，同步更新 `PythonCodeGenerator` 中的代码生成逻辑。

**技术栈：** Python 3.10+，自定义递归下降解析器

---

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/light_parser_v3.py:222-233` | 修改 | TryStmt 增加 `catch_type` 字段 |
| `src/light_parser_v3.py:1257-1312` | 修改 | `_parse_try_stmt()` 支持读取异常类型 |
| `src/light_parser_v3.py:873-942` | 修改 | `_parse_from_import_stmt()` 支持 `为 别名` |
| `src/code_generator.py:408-438` | 修改 | `_generate_try_stmt()` 使用 `catch_type` 生成对应 except |
| `src/code_generator.py:787-805` | 修改 | `_generate_import_stmt()` 支持 `from X import Y as Z` |
| `tests/test_exception.py` | 创建 | 异常处理专项测试 |

---

### 任务 1：TryStmt 增加 catch_type 字段

**文件：**
- 修改：`src/light_parser_v3.py:222-233`

- [ ] **步骤 1：修改 TryStmt 类，增加 catch_type 字段**

将：

```python
class TryStmt(ASTNode):
    __slots__ = ('try_body', 'catch_var', 'catch_body', 'finally_body')
    """异常捕获语句"""
    def __init__(self, try_body: List[ASTNode], catch_var: str = None, 
                 catch_body: List[ASTNode] = None, finally_body: List[ASTNode] = None):
        self.try_body = try_body
        self.catch_var = catch_var  # 捕获的异常变量名
        self.catch_body = catch_body or []
        self.finally_body = finally_body or []
```

改为：

```python
class TryStmt(ASTNode):
    __slots__ = ('try_body', 'catch_type', 'catch_var', 'catch_body', 'finally_body')
    """异常捕获语句"""
    def __init__(self, try_body: List[ASTNode], catch_type: str = None, catch_var: str = None,
                 catch_body: List[ASTNode] = None, finally_body: List[ASTNode] = None):
        self.try_body = try_body
        self.catch_type = catch_type  # 捕获的异常类型（如'值错误'），None表示捕获所有异常
        self.catch_var = catch_var    # 捕获的异常变量名
        self.catch_body = catch_body or []
        self.finally_body = finally_body or []
```

- [ ] **步骤 2：同步更新 `_parse_try_stmt()` 中 TryStmt 构造调用**

在 `_parse_try_stmt()` 中返回 `TryStmt(try_body, catch_var, catch_body, finally_body)` 处，
检查并更新为 `TryStmt(try_body, catch_type, catch_var, catch_body, finally_body)`（此处在任务 2 中会整体重写，所以只需确认最终调用签名匹配即可）。

---

### 任务 2：_parse_try_stmt 支持异常类型过滤

**文件：**
- 修改：`src/light_parser_v3.py:1257-1312`

- [ ] **步骤 1：修改 `_parse_try_stmt()` 方法**

当前逻辑：
```
try -> try_body
if 捕获 -> consume '捕获' -> read IDENTIFIER as catch_var -> consume ':' -> catch_body
if 最终 -> consume '最终' -> consume ':' -> finally_body
```

改为：
```
try -> try_body
if 捕获 -> consume '捕获'
  # 先尝试读异常类型（关键字或标识符）
  if peek is IDENTIFIER/KEYWORD and not ':':
    # 检查下一个 token 决定是"类型"还是"类型+变量"还是"变量"
    if peek(1) is ':' : -> 只有标识符，视为变量名（向后兼容）
    elif peek(1) is IDENTIFIER/KEYWORD : -> 前一个为类型，后一个为变量
    else: -> 只有标识符，视为变量名（向后兼容）
  consume ':'
  catch_body
if 最终 -> consume '最终' -> consume ':' -> finally_body
```

具体实现替换：

当前代码：
```python
    def _parse_try_stmt(self) -> TryStmt:
        """解析异常捕获语句
        
        语法：
        尝试：
          语句...
        捕获 异常变量：
          语句...
        结束。
        
        或带最终块：
        尝试：
          语句...
        捕获 异常变量：
          语句...
        最终：
          语句...
        结束。
        """
        # 尝试
        self._consume(TokenType.KEYWORD, '尝试')
        
        # 冒号
        self._consume(TokenType.COLON)
        
        # try块
        try_body = self._parse_body()
        
        # 捕获（可选）
        catch_var = None
        catch_body = []
        if self._match(TokenType.KEYWORD, '捕获'):
            self._consume(TokenType.KEYWORD, '捕获')
            
            # 异常变量名（可选）
            if self._current() and self._current().type == TokenType.IDENTIFIER:
                catch_var = self._consume(TokenType.IDENTIFIER).value
            
            # 冒号
            self._consume(TokenType.COLON)
            
            # catch块
            catch_body = self._parse_body()
        
        # 最终（可选）
        finally_body = []
        if self._match(TokenType.KEYWORD, '最终'):
            self._consume(TokenType.KEYWORD, '最终')
            
            # 冒号
            self._consume(TokenType.COLON)
            
            # finally块
            finally_body = self._parse_body()
        
        return TryStmt(try_body, catch_var, catch_body, finally_body)
```

替换为：

```python
    def _parse_try_stmt(self) -> TryStmt:
        """解析异常捕获语句
        
        语法：
        尝试：
          语句...
        捕获 异常变量：
          语句...
        结束。
        
        或带类型过滤：
        尝试：
          语句...
        捕获 值错误：
          语句...
        结束。
        
        或带类型和变量：
        尝试：
          语句...
        捕获 值错误 异常变量：
          语句...
        结束。
        
        或带最终块：
        尝试：
          语句...
        捕获 异常变量：
          语句...
        最终：
          语句...
        结束。
        """
        # 尝试
        self._consume(TokenType.KEYWORD, '尝试')
        
        # 冒号
        self._consume(TokenType.COLON)
        
        # try块
        try_body = self._parse_body()
        
        # 捕获（可选）
        catch_type = None
        catch_var = None
        catch_body = []
        if self._match(TokenType.KEYWORD, '捕获'):
            self._consume(TokenType.KEYWORD, '捕获')
            
            # 读取类型/变量名
            # 可能的情况：
            # 1. 标识符 -> :           => 变量名（向后兼容）
            # 2. 标识符 -> 标识符 -> :  => 类型 + 变量名
            # 3. 关键字 -> :           => 类型
            # 4. 关键字 -> 标识符 -> :  => 类型 + 变量名
            tok = self._current()
            if tok and tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                # 先读取第一个标识符/关键字
                first = self._consume().value
                
                # 检查下一个 token
                next_tok = self._current()
                if next_tok and next_tok.type == TokenType.COLON:
                    # 情况1或3：只有一个标识符/关键字，后面是冒号
                    # 判断：如果是已知异常类型名？但由于我们无法预知所有类型，
                    # 统一视为变量名（向后兼容）
                    catch_var = first
                elif next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    # 情况2或4：有类型和变量名
                    catch_type = first
                    catch_var = self._consume().value
                else:
                    # 只有一个标识符，视为变量名
                    catch_var = first
            
            # 冒号
            self._consume(TokenType.COLON)
            
            # catch块
            catch_body = self._parse_body()
        
        # 最终（可选）
        finally_body = []
        if self._match(TokenType.KEYWORD, '最终'):
            self._consume(TokenType.KEYWORD, '最终')
            
            # 冒号
            self._consume(TokenType.COLON)
            
            # finally块
            finally_body = self._parse_body()
        
        return TryStmt(try_body, catch_type, catch_var, catch_body, finally_body)
```

---

### 任务 3：_generate_try_stmt 支持类型过滤

**文件：**
- 修改：`src/code_generator.py:408-438`

- [ ] **步骤 1：修改 `_generate_try_stmt()` 方法**

当前代码生成 `except Exception as var:`：

```python
    def _generate_try_stmt(self, stmt: TryStmt):
        """生成异常捕获语句"""
        # try块
        self._add_line("try:")
        self.indent_level += 1
        if stmt.try_body:
            for s in stmt.try_body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        
        # except块
        if stmt.catch_body:
            if stmt.catch_var:
                self._add_line(f"except Exception as {stmt.catch_var}:")
            else:
                self._add_line("except Exception:")
            
            self.indent_level += 1
            for s in stmt.catch_body:
                self._generate_statement(s)
            self.indent_level -= 1
```

替换为：

```python
    def _generate_try_stmt(self, stmt: TryStmt):
        """生成异常捕获语句"""
        # try块
        self._add_line("try:")
        self.indent_level += 1
        if stmt.try_body:
            for s in stmt.try_body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        
        # except块
        if stmt.catch_body:
            if stmt.catch_type and stmt.catch_var:
                # 捕获指定类型 + 变量：except 值错误 as 错误:
                self._add_line(f"except {stmt.catch_type} as {stmt.catch_var}:")
            elif stmt.catch_type:
                # 捕获指定类型无变量：except 值错误:
                self._add_line(f"except {stmt.catch_type}:")
            elif stmt.catch_var:
                # 无类型有变量（向后兼容）：except Exception as 错误:
                self._add_line(f"except Exception as {stmt.catch_var}:")
            else:
                # 无类型无变量：except Exception:
                self._add_line("except Exception:")
            
            self.indent_level += 1
            for s in stmt.catch_body:
                self._generate_statement(s)
            self.indent_level -= 1
        
        # finally块
        if stmt.finally_body:
            self._add_line("finally:")
            self.indent_level += 1
            for s in stmt.finally_body:
                self._generate_statement(s)
            self.indent_level -= 1
```

---

### 任务 4：from...import...as 别名支持

**文件：**
- 修改：`src/light_parser_v3.py:873-942`

- [ ] **步骤 1：修改 `_parse_from_import_stmt()` 方法**

在读取符号列表后，检查 `为` 关键字以设置别名。

在 `_parse_from_import_stmt()` 的末尾，`return ImportStmt(module_name, symbols=symbols)` 之前，插入别名检测：

```python
        # 别名（可选）：从 模块 导入 符号 为 别名
        alias = None
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '为':
            self._consume(TokenType.KEYWORD, '为')
            if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                alias = self._consume().value
            # 句号（可选）
            if self._current() and self._current().type == TokenType.DOT:
                self._consume(TokenType.DOT)
        
        return ImportStmt(module_name, symbols=symbols, alias=alias)
```

注意：需要在方法开头将 `alias` 初始值设为 `None`，并在函数返回前处理别名。

完整的修改后方法应将 `alias` 从 `_parse_import_stmt` 风格一样传递。当前方法签名中已有 `alias` 支持但未被使用，我们用 alias 参数构造 ImportStmt。

- [ ] **步骤 2：更新 code_generator 处理 from...import...as**

**文件：** `src/code_generator.py:787-805`

当前代码中 `_generate_import_stmt()` 处理 `from X import Y` 时不使用 `stmt.alias`。修改为：

当 `stmt.symbols` 不为空且 `stmt.alias` 不为空时：

```python
        if stmt.symbols:
            # 从...导入：from 数学 import 平方根 或 from 数学 import 平方根 as 开方
            symbols_str = ', '.join(stmt.symbols)
            if stmt.alias:
                self._add_line(f"from {module_name} import {symbols_str} as {stmt.alias}")
                self._imported_symbols.add(stmt.alias)
            else:
                self._add_line(f"from {module_name} import {symbols_str}")
                for symbol in stmt.symbols:
                    self._imported_symbols.add(symbol)
```

---

### 任务 5：异常处理测试

**文件：**
- 创建：`tests/test_exception.py`

- [ ] **步骤 1：创建异常处理测试文件**

创建 `tests/test_exception.py`：

```python
"""
光明异常处理功能测试
"""

import sys
import os
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import DuanParser
from code_generator import PythonCodeGenerator


def _compile_and_exec(light_code: str, global_vars: dict = None) -> dict:
    """编译并执行光明代码，返回执行后的全局变量"""
    parser = DuanParser()
    module = parser.parse(light_code)
    
    generator = PythonCodeGenerator()
    py_code = generator.generate(module)
    
    # 执行生成的 Python 代码
    namespace = {}
    if global_vars:
        namespace.update(global_vars)
    exec(py_code, namespace)
    return namespace


def test_try_catch_basic():
    """基本 try/catch"""
    code = """
设 结果 为 空。
尝试：
  设 结果 为 "尝试执行"。
捕获 错误：
  设 结果 为 "捕获到异常"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('结果') == "尝试执行", f"期望'尝试执行'，得到 {ns.get('结果')}"


def test_try_catch_exception_raised():
    """try/catch 捕获真实异常"""
    code = """
尝试：
  设 甲 为 1 除 0。
捕获 错误：
  设 甲 为 "除零错误"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('甲') == "除零错误", f"期望'除零错误'，得到 {ns.get('甲')}"


def test_try_catch_with_type():
    """按类型捕获异常（匹配时捕获）"""
    code = """
尝试：
  设 甲 为 1 除 0。
捕获 ZeroDivisionError：
  设 甲 为 "捕获除零"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('甲') == "捕获除零", f"期望'捕获除零'，得到 {ns.get('甲')}"


def test_try_catch_with_type_and_var():
    """按类型+变量捕获异常"""
    code = """
设 信息 为 空。
尝试：
  设 甲 为 1 除 0。
捕获 ZeroDivisionError 错误：
  设 信息 为 错误。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('信息') is not None, "异常对象不应为空"
    assert 'division by zero' in str(ns.get('信息')), f"期望包含'division by zero'，得到 {ns.get('信息')}"


def test_try_catch_wrong_type():
    """按类型捕获但异常类型不匹配（传播）"""
    code = """
尝试：
  设 甲 为 1 除 0。
捕获 ValueError：
  设 甲 为 "不会执行"。
结束。
"""
    ns = {}
    try:
        # 必须用 exec 手动执行以捕获异常传播
        parser = DuanParser()
        module = parser.parse(code)
        generator = PythonCodeGenerator()
        py_code = generator.generate(module)
        exec(py_code, ns)
        assert False, "应抛出 ZeroDivisionError 但未抛出"
    except ZeroDivisionError:
        pass  # 预期行为：类型不匹配，异常向上传播


def test_try_catch_finally():
    """try/catch/finally 完整组合"""
    code = """
设 最终结果 为 空。
尝试：
  设 甲 为 1 除 0。
捕获 错误：
  设 甲 为 "错误信息"。
最终：
  设 最终结果 为 "执行完成"。
结束。
"""
    ns = _compile_and_exec(code)
    assert ns.get('最终结果') == "执行完成", f"期望'执行完成'，得到 {ns.get('最终结果')}"
    assert ns.get('甲') == "错误信息", f"期望'错误信息'，得到 {ns.get('甲')}"


def test_throw_exception():
    """抛出异常"""
    code = """
尝试：
  抛出 "自定义错误"。
捕获 错误：
  设 甲 为 错误。
结束。
"""
    ns = _compile_and_exec(code)
    assert str(ns.get('甲')) == "自定义错误"


def test_throw_inside_function():
    """在函数内抛出异常"""
    code = """
段落 除 接收 甲, 乙：
  如果 乙 等于 0：
    抛出 "除数不能为零"。
  结束。
  返回 甲 除 乙。
结束。

设 结果 为 空。
尝试：
  设 结果 为 除(10, 0)。
捕获 错误：
  设 结果 为 错误。
结束。
"""
    ns = _compile_and_exec(code)
    assert str(ns.get('结果')) == "除数不能为零"


if __name__ == '__main__':
    tests = [
        ("基本 try/catch", test_try_catch_basic),
        ("捕获真实异常", test_try_catch_exception_raised),
        ("按类型捕获", test_try_catch_with_type),
        ("类型+变量", test_try_catch_with_type_and_var),
        ("类型不匹配传播", test_try_catch_wrong_type),
        ("try/catch/finally", test_try_catch_finally),
        ("抛出异常", test_throw_exception),
        ("函数内抛出", test_throw_inside_function),
    ]
    
    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [OK] {name}")
            passed += 1
        except Exception as e:
            print(f"  [失败] {name}: {e}")
            failed += 1
    
    print(f"\n总计: {len(tests)}  |  通过: {passed}  |  失败: {failed}")
    sys.exit(0 if failed == 0 else 1)
```

- [ ] **步骤 2：运行测试验证通过**

```bash
cd g:\dumategithub\light && python tests/test_exception.py
```

预期：全部 8 个测试通过。

---

### 任务 6：运行回归测试

**文件：**
- 运行：`antlrparser/test/test_dual_backend.py`

- [ ] **步骤 1：运行双后端测试确认无回归**

```bash
cd g:\dumategithub\light && python antlrparser/test/test_dual_backend.py
```

预期：26/26 测试全部通过。