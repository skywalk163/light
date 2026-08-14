# 段言（Duan）紧凑写法与相关 Bug 修复记录

> 本文档记录了段言编译器中与「紧凑写法」（无空格省略写法）相关的词法分析器、解析器及代码生成器的 Bug 修复，包括根因分析、修复方案及对应源码位置。

---

## 目录

1. [Bug 1：ASCII 标识符后汉字序列中的运算符动词未被识别](#bug-1ascii-标识符后汉字序列中的运算符动词未被识别)
2. [Bug 2：三引号字符串被拆分成三个 token](#bug-2三引号字符串被拆分成三个-token)
3. [Bug 3：裸字符串语句（docstring）无解析分支](#bug-3裸字符串语句docstring无解析分支)
4. [Bug 4：函数名含运算符动词的合并未校验用户定义](#bug-4函数名含运算符动词的合并未校验用户定义)
5. [Bug 5：IDENTIFIER 合并无相邻性检查](#bug-5identifier-合并无相邻性检查)
6. [Bug 6：属性声明中「等于/为」被吞掉](#bug-6属性声明中等于为被吞掉)
7. [Bug 7：StringLiteral 无语句级代码生成分支](#bug-7stringliteral-无语句级代码生成分支)
8. [Bug 8：f-string 内嵌表达式引号转义错误](#bug-8f-string-内嵌表达式引号转义错误)
9. [附：三层分词机制说明](#附三层分词机制说明)

---

## Bug 1：ASCII 标识符后汉字序列中的运算符动词未被识别

### 现象

紧凑写法 `n减1`、`left至右`、`n乘阶乘` 等表达式被错误地合并为单个标识符（如 `n减`、`left至`），运行时抛出 `NameError`。

### 根因

段言语言允许无空格分词，ASCII 标识符（如 `n`、`left`）后紧跟汉字时，词法分析器需要决定是否将汉字作为标识符后缀合并还是作为独立关键字/标识符处理。

**源码位置：** [src/lexer.py:1047-1055](file:///c:/dumatework/duan/src/lexer.py#L1047-L1055)

原实现中，ASCII 标识符后紧跟汉字时的合并逻辑为：

```python
# 原逻辑（简化）：
while j < n and _is_han(source[j]):
    # 只检查汉字序列开头是否命中 ALL_KEYWORDS
    if source[j:j+2] in ALL_KEYWORDS:
        break
    j += 1
```

这里只检查了 `ALL_KEYWORDS` 集合，但运算符动词（如 `减`、`乘`、`除`、`至`、`等于` 等）存放在 **`VERB_ARITY`** 字典中，**不在** `ALL_KEYWORDS` 集合里。因此汉字序列 `减1` 中的 `减` 未被识别为关键字，整个汉字序列被整体并入 ASCII 标识符，形成 `n减` 这个不存在的标识符。

### 修复方案

**源码位置：** [src/lexer.py:1056-1064](file:///c:/dumatework/duan/src/lexer.py#L1056-L1064)

改用 `_match_keyword()` 方法做最长关键字匹配，该方法同时覆盖 `ALL_KEYWORDS` 和 `VERB_ARITY` 中的关键字：

```python
while j < n and _is_han(source[j]):
    # 从 j 处做最长关键字匹配（_match_keyword 覆盖 VERB_ARITY 中的动词）
    han_kw, _ = self._match_keyword(source, j)
    if han_kw:
        break       # 命中关键字，停止合并
    k = j
    while k < n and _is_han(source[k]):
        k += 1
    j = k           # 未命中关键字的纯汉字后缀仍合并
```

效果：
- `n减1` → 正确切分为 `标识符 n` + `关键字 减` + `数字 1`
- `evennum集` → 仍保持为单个标识符（`集` 不是关键字）

---

## Bug 2：三引号字符串被拆分成三个 token

### 现象

`bootstrap_eval.duan`、`bootstrap_lexer.duan` 等示例中函数体首行的 `"""文档字符串"""` 无法解析，报错 `无法识别的语法元素：''`。

### 根因

**源码位置：** [src/lexer.py:713-726](file:///c:/dumatework/duan/src/lexer.py#L713-L726)

原实现只按成对单引号/双引号处理，`"""..."""` 被拆成三个独立的 `STRING` token：

```
""     → 空字符串 token
"内容" → 内容 token
""     → 空字符串 token
```

作为独立语句时，首 token 为空字符串 `''`，解析器不认识这个空字符串，直接报错。

### 修复方案

**源码位置：** [src/lexer.py:719-726](file:///c:/dumatework/duan/src/lexer.py#L719-L726)

在 `_tokenize_string` 方法中，检测连续三个相同引号，将整个三引号块作为单个 `STRING` token 消费：

```python
if i + 2 < len(source) and source[i] == source[i + 1] == source[i + 2]:
    triple = quote_char * 3
    close_idx = source.find(triple, i + 3)
    if close_idx == -1:
        raise LexerError(f"字符串未闭合: 三引号 '{triple}' 缺少匹配的结束符", line, start_col)
    value = source[i + 3:close_idx]
    return Token(TokenType.STRING, value, line, start_col), close_idx + 3 - i
```

内容为三引号之间的原文（支持跨行），供裸字符串语句（docstring）解析使用。

---

## Bug 3：裸字符串语句（docstring）无解析分支

### 现象

配合 Bug 2 修复后，词法分析器能正确输出单个 `STRING` token，但解析器仍然报错，表现为 `无法识别的语法元素`。

### 根因

**源码位置：** [src/parser_stmt.py:321-335](file:///c:/dumatework/duan/src/parser_stmt.py#L321-L335)

`_parse_statement` 方法原先没有任何 `STRING` 类型的分支。裸字符串作为独立语句时，直接落入方法末尾的 `无法识别的语法元素` 报错分支。

### 修复方案

**源码位置：** [src/parser_stmt.py:334-335](file:///c:/dumatework/duan/src/parser_stmt.py#L334-L335)

将 `STRING` 作为表达式语句解析：

```python
if tok.type == TokenType.STRING:
    return self._parse_expr_stmt()
```

对应代码生成器中的 `StringLiteral` 分支（见 Bug 7）。

---

## Bug 4：函数名含运算符动词的合并未校验用户定义

### 现象

紧凑写法 `n乘阶乘(n-1)` 被解析为函数调用 `n乘阶乘(...)`，而不是乘法表达式 `n * 阶乘(n-1)`，运行时抛出 `NameError`。

### 根因

**源码位置（三处）：**

- [src/parser_expr.py:822-838](file:///c:/dumatework/duan/src/parser_expr.py#L822-L838) — `_collect_primary_arg`
- [src/parser_expr.py:1033-1051](file:///c:/dumatework/duan/src/parser_expr.py#L1033-L1051) — `_parse_primary`
- [src/parser_expr.py:1003-1008](file:///c:/dumatework/duan/src/parser_expr.py#L1003-L1008) — `_collect_single_arg`

词法分析器把 `n乘阶乘(` 拆成 `标识符 n` + `动词 乘` + `标识符 阶乘` + `(`。解析器原先无条件将相邻令牌合并成函数名 `n乘阶乘`，使本应是乘法表达式 `n * 阶乘(n-1)` 的紧凑写法被误当成函数调用。

### 修复方案

词法分析器在 `_tokenize` 方法中增加预扫描阶段，收集用户定义的标识符：

**源码位置：** [src/lexer.py:284-291](file:///c:/dumatework/duan/src/lexer.py#L284-L291)

```python
user_definitions = self._scan_user_definitions(source)
# 暴露给解析器：parser_expr 需要区分「含运算符动词的函数名」（如 添加任务，
# 用户确实定义了该段落）与「紧凑二元表达式」（如 n乘阶乘 中 乘 是运算符，
# n乘 并不是用户定义）。
self.user_definitions = user_definitions
```

解析器三处合并逻辑统一增加校验：合并结果必须是 `lexer.user_definitions` 中的已有定义才生效，否则回退令牌位置，交由二元运算符解析机制处理：

```python
_user_defs = getattr(self.lexer, 'user_definitions', None) or set()
if _fn_candidate in _user_defs:
    name = _fn_candidate
else:
    self.pos = _fn_saved_pos  # 回退，走二元运算符解析
```

---

## Bug 5：IDENTIFIER 合并无相邻性检查

### 现象

`转字符串 x`（带空格）被错误合并为 `转字符串x`，导致 `转字符串` 作为一个整体函数名被调用，而 `x` 丢失了参数身份。

### 根因

**源码位置：** [src/parser_expr.py:983-1001](file:///c:/dumatework/duan/src/parser_expr.py#L983-L1001)

`_collect_single_arg` 方法中合并连续的 `IDENTIFIER` 令牌时，原实现只检查类型，**不检查令牌在源码中是否相邻**（无空格）。因此 `转字符串 x`（`转字符串` 与 `x` 之间有空格）被错误合并成 `转字符串x`。

### 修复方案

**源码位置：** [src/parser_expr.py:992-1001](file:///c:/dumatework/duan/src/parser_expr.py#L992-L1001)

用列号追踪相邻性——仅当后一个 `IDENTIFIER` 的起始列恰好等于前一个令牌的结束列（`col + len(value)`）时才合并：

```python
_prev_col = tok.col + len(tok.value)
while self._current() and self._current().type == TokenType.IDENTIFIER \
        and self._current().value not in self.ADD_OP_MAP \
        and self._current().value not in self.MUL_OP_MAP \
        and self._current().value != '不':
    _cur = self._current()
    if _cur.col != _prev_col:
        break
    name += self._consume().value
    _prev_col = _cur.col + len(_cur.value)
```

带空格的 `转字符串 x` 保持为两个独立标识符（`转字符串` 为函数调用，`x` 为参数）。

---

## Bug 6：属性声明中「等于/为」被吞掉

### 现象

`class_complete.duan` 中的 `属性 品种 等于 "金毛"` 解析失败，级联产生大量 `无法识别的语法元素` 错误。

### 根因

**源码位置：** [src/parser_stmt.py:3223-3233](file:///c:/dumatework/duan/src/parser_stmt.py#L3223-L3233)

`_parse_attribute_declaration` 方法中，属性名收集循环原先只处理 `PERIOD`、`NEWLINE`、`COLON` 三种分隔符，会把 `等于/为` 当作属性名的一部分吞掉。导致 `属性 品种 等于 "金毛"` 中 `品种` 之后的所有内容（包括 `等于 "金毛"`）都被当作属性名吃掉。

### 修复方案

**源码位置：** [src/parser_stmt.py:3232-3233](file:///c:/dumatework/duan/src/parser_stmt.py#L3232-L3233)

遇到 `等于/为` 立即停止收集属性名，交由下方「默认值（可选）」逻辑继续解析：

```python
if self._current().value in ('等于', '为'):
    break
```

---

## Bug 7：StringLiteral 无语句级代码生成分支

### 现象

修复 Bug 2 和 Bug 3 后，AST 中出现了 `StringLiteral` 类型的语句节点，但代码生成器没有对应的处理分支，抛出 `CodeGenError: 未知语句类型`。

### 根因

**源码位置：** [src/code_generator.py:741-748](file:///c:/dumatework/duan/src/code_generator.py#L741-L748)

`_generate_statement` 方法中的分支覆盖了表达式语句、赋值语句、循环语句等，但缺少 `StringLiteral` 类型。修复前该节点没有语句级分支，直接落入 `else` 抛出异常。

### 修复方案

**源码位置：** [src/code_generator.py:741-748](file:///c:/dumatework/duan/src/code_generator.py#L741-L748)

添加 `StringLiteral` 分支，输出 Python 字符串表达式语句：

```python
elif isinstance(stmt, StringLiteral):
    # 裸字符串语句（docstring）生成：配合 lexer/parser 的三引号 docstring 修复
    # Python 会把函数/类/模块体首行的字符串视为 docstring，
    # 其余位置的裸字符串为无操作表达式（与 Python 语义一致）。
    self._add_line(self._generate_expr(stmt))
```

---

## Bug 8：f-string 内嵌表达式引号转义错误

### 现象

当 f-string 的花括号内表达式包含字符串参数时，如 `{处理数据("hello")}`，生成的 Python 代码中 `"hello"` 被错误转义为 `\"hello\"`，触发 `unexpected character after line continuation character` 语法错误。

### 根因

**源码位置：** [src/code_generator.py:1793-1804](file:///c:/dumatework/duan/src/code_generator.py#L1793-L1804)

原实现先拼接整个 f-string，再用 `fstr.replace('"', '\\"')` 全局转义双引号。若花括号内表达式含字符串（如 `{处理数据("hello")}`），表达式里的 `"` 会被转成 `\"`——在 f-string 花括号内属于无效转义。

### 修复方案

**源码位置：** [src/code_generator.py:1805-1814](file:///c:/dumatework/duan/src/code_generator.py#L1805-L1814)

1. **表达式部分**由 `_generate_expr` 生成（字符串统一用双引号），因此只要表达式含 `"`，外层引号就必须选单引号 `'`（花括号内出现 `"` 合法）；
2. **外层引号**只出现在字面量部分，若字面量含同种引号则仅在该处转义（花括号外的 `\'` 或 `\"` 是合法转义）。

```python
if any('"' in p for p in expr_parts):
    outer = "'"
elif any("'" in p for p in parts if isinstance(p, str)):
    outer = '"'
else:
    outer = '"'
# 仅转义字面量部分中的外层引号
```

---

## 附：三层分词机制说明

段言语言的核心分词机制（决策 29）分为三层：

1. **类型切换自动分词**：遇到汉字/字母切换时自动拆分（如 `n减1` 中的 `n` → `减` → `1`）
2. **双字关键词优先匹配**：优先匹配 `ALL_KEYWORDS` 中的双字及以上关键字
3. **元数驱动参数收集**：通过 `VERB_ARITY` 中关键字的预期元数决定后续分词行为

### 关键数据结构

| 数据结构 | 用途 | 示例 |
|---------|------|------|
| `ALL_KEYWORDS` | 所有关键字集合 | `设`、`为`、`如果`、`打印` |
| `VERB_ARITY` | 运算符动词及其元数 | `加`→2, `减`→2, `乘`→2, `至`→2 |
| `IDENTIFIER_SAFE_KEYWORDS` | 常作复合标识符后缀的关键字 | `函数`、`段落`、`输出`、`返回` |
| `user_definitions` | lexer 预扫描出的用户定义标识符 | 段落名、方法名、变量名 |

### 修复涉及的源码文件

| 文件 | 修复内容 |
|------|---------|
| [src/lexer.py](file:///c:/dumatework/duan/src/lexer.py) | Bug 1（ASCII+汉字动词识别）、Bug 2（三引号字符串）、预扫描 `user_definitions` |
| [src/parser_expr.py](file:///c:/dumatework/duan/src/parser_expr.py) | Bug 4（三处动词函数名校验）、Bug 5（IDENTIFIER 相邻性检查） |
| [src/parser_stmt.py](file:///c:/dumatework/duan/src/parser_stmt.py) | Bug 3（裸字符串语句解析）、Bug 6（属性声明默认值） |
| [src/code_generator.py](file:///c:/dumatework/duan/src/code_generator.py) | Bug 7（StringLiteral 语句分支）、Bug 8（f-string 引号转义） |