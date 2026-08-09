# 接口与抽象类 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 subagent-driven-development（推荐）或 executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在光明 v3 解析器中添加接口定义、类实现接口、@抽象 装饰器。

**架构：** 在递归下降解析器中添加 InterfaceDefinition AST 节点和对应解析方法；修改类定义解析支持 `实现` 子句；代码生成器使用 Python `abc.ABC` + `@abstractmethod`。

**技术栈：** Python 3.10+，自定义递归下降解析器

---

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/keywords.py` | 修改 | 新增 `接口`、`实现`、`抽象` 关键字 |
| `src/light_parser_v3.py` | 修改 | 新增 InterfaceDefinition/MethodSignature AST；接口解析；类定义支持 `实现`；`@抽象` 装饰器 |
| `src/code_generator.py` | 修改 | 接口生成 + ABC 导入；抽象方法生成 |

---

### 任务 1：添加关键字

**文件：** `src/keywords.py`

- [ ] **步骤 1：添加 `接口`、`实现` 到 KEYWORDS_CLASS，`抽象` 到新 KEYWORDS_DECORATOR**

```python
# 类与对象（新增）
KEYWORDS_CLASS = {
    '类', '继承', '属性', '构造', '新建',
    '接口', '实现',
}
```

在 `KEYWORDS_CONTEXT` 之后新增装饰器关键字集合：

```python
# 装饰器关键字（新增）
KEYWORDS_DECORATOR = {
    '抽象',  # @抽象 → @abstractmethod
}

# 所有双字关键字
KEYWORDS_DOUBLE = (
    KEYWORDS_DEFINE |
    KEYWORDS_CONDITION |
    KEYWORDS_LOOP |
    KEYWORDS_FUNCTION |
    KEYWORDS_EXCEPTION |
    KEYWORDS_CLASS |
    KEYWORDS_MODULE |
    KEYWORDS_MATCH |
    KEYWORDS_CONTEXT |
    KEYWORDS_DECORATOR
)
```

---

### 任务 2：InterfaceDefinition AST 节点

**文件：** `src/light_parser_v3.py`

- [ ] **步骤 1：新增 InterfaceDefinition 和 MethodSignature AST 类**

在 `DecoratorDefinition` 类之后（约第 492 行）添加：

```python
class MethodSignature(ASTNode):
    __slots__ = ('name', 'parameters', 'return_type')
    """接口方法签名"""
    def __init__(self, name: str, parameters: List[Parameter] = None, return_type: str = None):
        self.name = name
        self.parameters = parameters or []
        self.return_type = return_type
    
    def __repr__(self):
        return f"MethodSignature({self.name})"


class InterfaceDefinition(ASTNode):
    __slots__ = ('name', 'methods', 'properties', 'super_interfaces')
    """接口定义"""
    def __init__(self, name: str, methods: List[MethodSignature], 
                 properties: List[AttributeDeclaration] = None,
                 super_interfaces: List[str] = None):
        self.name = name
        self.methods = methods        # List[MethodSignature]
        self.properties = properties or []
        self.super_interfaces = super_interfaces or []
    
    def __repr__(self):
        return f"InterfaceDefinition({self.name})"
```

---

### 任务 3：接口解析方法

**文件：** `src/light_parser_v3.py`

- [ ] **步骤 1：在 `_parse_statement` 中添加接口分支**

在 `_parse_statement` 中（约第 633 行），在检查 `类` 关键字后添加 `接口` 检查：

```python
        # 接口定义
        if tok.type == TokenType.KEYWORD and tok.value == '接口':
            return self._parse_interface_definition()
```

- [ ] **步骤 2：实现 `_parse_interface_definition` 方法**

```python
    def _parse_interface_definition(self) -> InterfaceDefinition:
        """解析接口定义
        
        语法：
        接口 名称：
          段落 方法名 参数... 返回 类型。
          段落 方法名(参数) 返回 类型。
        结束。
        
        或带继承：
        接口 名称 继承 父接口1, 父接口2：
          ...
        结束。
        """
        # 接口
        self._consume(TokenType.KEYWORD, '接口')
        
        # 接口名
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            raise ParseError(f"期望接口名，但得到 {name_tok.type if name_tok else '输入结束'}")
        
        # 继承（可选）
        super_interfaces = []
        if self._match(TokenType.KEYWORD, '继承'):
            self._consume(TokenType.KEYWORD, '继承')
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                super_interfaces.append(self._consume().value)
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                else:
                    break
        
        # 冒号或句号
        if self._match(TokenType.COLON):
            self._consume(TokenType.COLON)
        elif self._match(TokenType.DOT):
            self._consume(TokenType.DOT)
        
        # 接口体
        methods = []
        properties = []
        while self._current():
            tok = self._current()
            
            # 结束
            if tok.type == TokenType.KEYWORD and tok.value == '结束':
                self._consume(TokenType.KEYWORD, '结束')
                if self._current() and self._current().type == TokenType.DOT:
                    self._consume(TokenType.DOT)
                break
            
            # 方法签名：段落 方法名 参数 参数名 返回 类型
            if tok.type == TokenType.KEYWORD and tok.value == '段落':
                sig = self._parse_method_signature()
                methods.append(sig)
            
            # 属性声明：属性 名称（可选类型）
            elif tok.type == TokenType.KEYWORD and tok.value == '属性':
                attr = self._parse_attribute_declaration()
                properties.append(attr)
            
            else:
                # 跳过无法识别的 token
                if tok.type == TokenType.DOT:
                    self._consume(TokenType.DOT)
                else:
                    break
        
        return InterfaceDefinition(name, methods, properties, super_interfaces)
    
    def _parse_method_signature(self) -> MethodSignature:
        """解析接口方法签名
        
        语法：
        段落 方法名 参数 参数名 返回 类型。
        段落 方法名(参数) 返回 类型。
        段落 方法名 返回 类型。
        段落 方法名。
        """
        self._consume(TokenType.KEYWORD, '段落')
        
        # 方法名
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            raise ParseError(f"期望方法名")
        
        # 参数
        params = []
        
        # 括号参数：(参数1, 参数2, ...)
        if self._match(TokenType.LPAREN):
            self._consume(TokenType.LPAREN)
            while self._current() and self._current().type != TokenType.RPAREN:
                if self._current().type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                    continue
                param_tok = self._current()
                if param_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    param_name = self._consume().value
                    # 可选类型注解
                    param_type = None
                    if self._match(TokenType.COLON):
                        self._consume(TokenType.COLON)
                        if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            param_type = self._consume().value
                    params.append(Parameter(param_name, param_type))
                else:
                    break
            self._consume(TokenType.RPAREN)
        
        # 无括号参数：参数 参数名（段落风格）
        elif self._match(TokenType.KEYWORD, '参数'):
            self._consume(TokenType.KEYWORD, '参数')
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                param_name = self._consume().value
                params.append(Parameter(param_name))
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                else:
                    break
        
        # 返回类型（可选）
        return_type = None
        if self._match(TokenType.KEYWORD, '返回'):
            self._consume(TokenType.KEYWORD, '返回')
            if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                return_type = self._consume().value
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.DOT:
            self._consume(TokenType.DOT)
        
        return MethodSignature(name, params, return_type)
```

---

### 任务 4：类定义支持 `实现` 子句

**文件：** `src/light_parser_v3.py`（`_parse_class_definition` 方法，约第 2568 行）

- [ ] **步骤 1：在 `继承` 子句之后添加 `实现` 子句支持**

在现有继承解析代码之后（`base_class` → `base_classes` 已在上次迭代中改为列表），读取 `实现` 关键字并收集接口名：

将当前继承后的代码：

```python
        # 句号或冒号
        if self._current() and self._current().type == TokenType.DOT:
            self._consume(TokenType.DOT)
        elif self._current() and self._current().type == TokenType.COLON:
            self._consume(TokenType.COLON)
```

之前插入：

```python
        # 实现接口（可选）
        if self._match(TokenType.KEYWORD, '实现'):
            self._consume(TokenType.KEYWORD, '实现')
            impl_interfaces = []
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                impl_interfaces.append(self._consume().value)
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                else:
                    break
            # 合并到 base_classes
            if not base_classes:
                base_classes = []
            base_classes.extend(impl_interfaces)
```

注意：需要改方法签名，在 `继承` 代码之前声明 `base_classes = []` 而不是 `base_class = None`（已在迭代 3 中完成）。

---

### 任务 5：`@抽象` 装饰器支持

**文件：** `src/light_parser_v3.py`

- [ ] **步骤 1：在 `_parse_decorator` 中处理 `抽象`**

在 `_parse_decorator` 方法中（约第 2844 行），将 `'静态方法', '类方法', '特性'` 列表扩展为包含 `'抽象'`：

```python
        if decorator_name in ('静态方法', '类方法', '特性', '抽象'):
```

---

### 任务 6：代码生成器

**文件：** `src/code_generator.py`

- [ ] **步骤 1：添加 ABC/abstractmethod 导入跟踪**

在 `PythonCodeGenerator.__init__` 中（约第 38 行），添加标志：

```python
class PythonCodeGenerator:
    """光明到Python代码生成器"""
    
    def __init__(self):
        self.indent_level = 0
        self.indent_str = "    "
        self.output_lines: List[str] = []
        self._imported_symbols: set = set()
        self._needs_abc = False  # 是否需要 from abc import ABC, abstractmethod
```

- [ ] **步骤 2：生成接口定义**

在 `_generate_class_definition` 之后添加接口生成方法：

```python
    def _generate_interface_definition(self, stmt: InterfaceDefinition):
        """生成接口定义"""
        self._needs_abc = True
        class_name = self._sanitize_name(stmt.name)
        
        # 基类
        bases = ['ABC']
        for sup in stmt.super_interfaces:
            bases.append(self._sanitize_name(sup))
        bases_str = ', '.join(bases)
        
        self._add_line(f"class {class_name}({bases_str}):")
        self.indent_level += 1
        
        # 生成抽象方法
        for method in stmt.methods:
            self._generate_abstract_method(method)
        
        # 如果没有方法，添加 pass
        if not stmt.methods:
            self._add_line("pass")
        
        self.indent_level -= 1
        self._add_line("")
    
    def _generate_abstract_method(self, method: MethodSignature):
        """生成抽象方法"""
        self._needs_abc = True
        method_name = self._sanitize_name(method.name)
        
        # 参数列表
        params = ['self']
        for param in method.parameters:
            param_name = self._sanitize_name(param.name)
            params.append(param_name)
        
        params_str = ', '.join(params)
        
        self._add_line("@abstractmethod")
        if method.return_type:
            ret_type = self._sanitize_name(method.return_type)
            self._add_line(f"def {method_name}({params_str}) -> {ret_type}:")
        else:
            self._add_line(f"def {method_name}({params_str}):")
        self.indent_level += 1
        self._add_line("pass")
        self.indent_level -= 1
```

- [ ] **步骤 3：在 `_generate_statement` 中添加接口分支**

```python
        elif isinstance(stmt, InterfaceDefinition):
            self._generate_interface_definition(stmt)
```

- [ ] **步骤 4：`generate()` 方法在输出开始时添加 ABC 导入**

在 `generate()` 方法中（约第 162 行），在生成模块头部后添加：

```python
        # 如果需要 ABC，添加导入
        if self._needs_abc:
            self._add_line("from abc import ABC, abstractmethod")
            self._add_line("")
```

- [ ] **步骤 5：处理 @抽象 装饰器生成**

在 `_generate_decorator_definition` 方法中，将 `'抽象'` 加入映射：

```python
        builtin_decorators = {
            '静态方法': '@staticmethod',
            '类方法': '@classmethod',
            '特性': '@property',
            '抽象': '@abstractmethod',
        }
```

并在遇到 `抽象` 装饰器时设置 `self._needs_abc = True`。

---

### 任务 7：验证测试

- [ ] **步骤 1：创建一个简单的接口测试用例**

创建 `g:\dumategithub\light\tests\test_interface.py`：

```python
"""
光明接口与抽象类功能测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _compile(light_code: str) -> str:
    """编译光明代码，返回Python源码"""
    parser = LightParser()
    module = parser.parse(light_code)
    generator = PythonCodeGenerator()
    return generator.generate(module)


def test_interface_definition():
    """接口定义"""
    code = """
接口 可打印：
  段落 输出 返回 串。
结束。
"""
    py_code = _compile(code)
    assert 'from abc import ABC, abstractmethod' in py_code
    assert 'class 可打印(ABC):' in py_code
    assert '@abstractmethod' in py_code
    assert 'def 输出(self) -> str:' in py_code or 'def 输出(self) -> 串:' in py_code


def test_interface_inheritance():
    """接口继承"""
    code = """
接口 可保存 继承 可打印：
  段落 保存(路径)。
结束。
"""
    py_code = _compile(code)
    assert 'class 可保存(可打印):' in py_code


def test_class_implements():
    """类实现接口"""
    code = """
接口 可打印：
  段落 输出 返回 串。
结束。

类 文档 实现 可打印：
  段落 输出 返回 串：
    返回 "文档内容"。
  结束。
结束。
"""
    py_code = _compile(code)
    assert 'class 文档(可打印):' in py_code


def test_abstract_decorator():
    """@抽象 装饰器"""
    code = """
类 形状：
  @抽象
  段落 面积 返回 数：
    结束。
结束。
"""
    py_code = _compile(code)
    assert '@abstractmethod' in py_code


if __name__ == '__main__':
    tests = [
        ("接口定义", test_interface_definition),
        ("接口继承", test_interface_inheritance),
        ("类实现接口", test_class_implements),
        ("@抽象装饰器", test_abstract_decorator),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  [OK] {name}")
            passed += 1
        except Exception as e:
            print(f"  [失败] {name}: {e}")
            failed += 1
    print(f"\n总计: {len(tests)}  |  通过: {passed}  |  失败: {failed}")
    sys.exit(0 if failed == 0 else 1)
```

- [ ] **步骤 2：运行全部测试**

```bash
cd g:\dumategithub\light && python tests\test_interface.py
cd g:\dumategithub\light && python antlrparser\test\test_dual_backend.py
cd g:\dumategithub\light && python tests\test_exception.py
cd g:\dumategithub\light && python tests\test_class_definition.py
```