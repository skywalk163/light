# 语法增强 — 迭代 2 实现计划

> **面向 AI 代理的工作者：** 步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 添加 super() 调用和内置装饰器（@staticmethod/@classmethod/@property）支持。

**架构：** 扩展递归下降解析器和代码生成器，复用已有的后缀解析（`.方法()`）和装饰器机制。

---

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/keywords.py` | 修改 | 将 `父` 加入 KEYWORDS_RESERVED |
| `src/light_parser_v3.py` | 修改 | `_parse_primary` 中处理 `父` 关键字；`_parse_decorator` 识别特殊装饰器 |
| `src/code_generator.py` | 修改 | `_generate_decorator_definition` 映射特殊装饰器 |

---

### 任务 1：添加 `父` 关键字

**文件：** `src/keywords.py:87-92`

- [ ] **步骤 1：将 `父` 加入保留字集合**

在 `KEYWORDS_RESERVED` 中添加 `'父'`：

```python
KEYWORDS_RESERVED = {
    '并',
    '之',
    '的',
    '己',
    '父',  # super() 调用
}
```

---

### 任务 2：解析器支持 `父.方法名()` 语法

**文件：** `src/light_parser_v3.py:1823-1835`

- [ ] **步骤 1：在 `_parse_primary` 中处理 `父` 关键字**

在 `己` 处理代码（约第1823行）之后、`raise ParseError` 之前，添加：

```python
        # Super引用：父.方法名()
        if tok.type == TokenType.KEYWORD and tok.value == '父':
            self._consume()
            expr = Identifier("super()")
            return self._parse_postfix(expr)
```

这个方式利用已有的 `_parse_postfix` 机制：
- `父.方法名()` → `super().方法名()` — 后缀 `.方法名()` 由 _parse_postfix 处理
- `父.属性名` → `super().属性名` — 后缀 `.属性名` 由 _parse_postfix 处理为 PropertyAccess

---

### 任务 3：解析器支持 `@静态方法`/`@类方法`/`@特性`

**文件：** `src/light_parser_v3.py:2838-2875`

- [ ] **步骤 1：在 `_parse_decorator` 中检测特殊装饰器**

修改 `_parse_decorator` 方法，在读取装饰器名后，如果是 `静态方法`/`类方法`/`特性`，则不要求后跟段落定义（直接解析后续段落作为被装饰对象）。

将方法体扩展为：读取装饰器名后，如果是特殊装饰器则直接返回，让主解析流程继续处理后续段落/方法定义。

修改后的 `_parse_decorator`：

```python
    def _parse_decorator(self) -> DecoratorDefinition:
        """解析装饰器定义
        语法：@段落名 标注 段落 ...
              @静态方法 / @类方法 / @特性（内置装饰器，后跟段落/构造定义）
        """
        # @
        self._consume(TokenType.AT)
        
        # 装饰器名
        decorator_name = None
        tok = self._current()
        if tok and tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            decorator_name = self._consume().value
        else:
            raise ParseError(f"期望装饰器名，但得到 {tok.type if tok else '输入结束'}")
        
        # 标注（可选关键字）
        if self._match(TokenType.KEYWORD, '标注'):
            self._consume(TokenType.KEYWORD, '标注')
        
        # 内置装饰器（静态方法、类方法、特性）不跟标注关键字
        if decorator_name in ('静态方法', '类方法', '特性'):
            # 后跟段落定义或构造定义，由主解析流程处理
            paragraph = None
            if self._match(TokenType.LBOOK):
                paragraph = self._parse_paragraph()
            elif self._match(TokenType.KEYWORD, '段落'):
                paragraph = self._parse_paragraph_v2()
            elif self._match(TokenType.KEYWORD, '构造'):
                paragraph = self._parse_method_definition(is_constructor=True)
            else:
                raise ParseError("装饰器后必须跟段落定义或构造定义")
            return DecoratorDefinition(decorator_name, paragraph)
        
        # 标注（可选关键字）— 仅自定义装饰器支持
        if self._match(TokenType.KEYWORD, '标注'):
            self._consume(TokenType.KEYWORD, '标注')
        
        # 解析被装饰的段落
        paragraph = None
        if self._match(TokenType.LBOOK):
            paragraph = self._parse_paragraph()
        elif self._match(TokenType.KEYWORD, '段落'):
            paragraph = self._parse_paragraph_v2()
        else:
            raise ParseError("装饰器后必须跟段落定义（'《段名》段' 或 '段落 段名'）")
        
        return DecoratorDefinition(decorator_name, paragraph)
```

---

### 任务 4：代码生成器映射内置装饰器

**文件：** `src/code_generator.py:570-577`

- [ ] **步骤 1：修改 `_generate_decorator_definition`**

```python
    def _generate_decorator_definition(self, stmt: DecoratorDefinition):
        """生成装饰器定义"""
        decorator_name = stmt.decorator_name
        
        # 内置装饰器映射
        builtin_decorators = {
            '静态方法': '@staticmethod',
            '类方法': '@classmethod',
            '特性': '@property',
        }
        
        if decorator_name in builtin_decorators:
            self._add_line(builtin_decorators[decorator_name])
        else:
            # 自定义装饰器
            self._add_line(f"@{decorator_name}")
        
        if isinstance(stmt.paragraph, Paragraph):
            self._generate_paragraph(stmt.paragraph)
        else:
            raise CodeGenError("装饰器后必须是段落定义", type(stmt.paragraph).__name__)
```