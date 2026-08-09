# 光明语法的增强设计

**日期**：2026-06-15
**基于**：统一语法规范 v1.6

## 实施策略：三迭代混合推进

按使用频率确定优先级，每个迭代有独立的可交付成果。

---

## 迭代 1：异常增强 + 导入完善 + 测试

### 1.1 异常类型过滤

**现状**：`捕获 变量：` 只生成 `except Exception as 变量：`

**增强后语法**：

```
# 无类型（向后兼容）
捕获 错误：
  打印 错误。

# 按类型捕获
捕获 值错误：
  打印 "值错误"。

# 类型 + 变量
捕获 值错误 错误：
  打印 错误。
```

**改动文件**：
- `src/light_parser_v3.py`：TryStmt 增加 `catch_type` 字段；`_parse_try_stmt()` 先尝试读类型再读变量
- `src/code_generator.py`：`_generate_try_stmt()` 根据 `catch_type` 生成对应 Python 代码
- `src/ast_nodes.py`：同步更新 TryStmt（如有定义）

### 1.2 from...import...as 别名

**现状**：`从 模块 导入 符号` 后遇到 `为` 关键字直接退出，别名未处理。

**增强后语法**：

```
从 数学 导入 平方根 为 开方。
```

**改动文件**：
- `src/light_parser_v3.py`：`_parse_from_import_stmt()` 在符号列表后检测 `为` 关键字，设置 `ImportStmt.alias`
- `src/code_generator.py`：`_generate_import_stmt()` 处理 `from X import Y as Z` 输出

### 1.3 异常处理测试

新增测试，覆盖：
- 基本 try/catch（无类型）
- 按类型捕获
- 类型 + 变量名
- try/catch/finally 组合
- 抛出异常
- 异常传播（不捕获）

---

## 迭代 2：OOP 增强

### 2.1 super() 调用

**语法**：`父.方法名(参数)` 或 `父类.方法名(参数)`

**改动文件**：
- `src/light_parser_v3.py`：在表达式解析中识别 `父` 关键字
- `src/code_generator.py`：生成 `super().method(args)` 或 `super(ClassName, self).method(args)`

### 2.2 装饰器增强

**语法**：

```
@静态方法
段落 工具方法：
  ...

@类方法
段落 工厂方法：
  ...

@特性
段落 只读属性：
```

**改动文件**：
- `src/light_parser_v3.py`：`_parse_decorator()` 识别 `@静态方法`、`@类方法`、`@特性`
- `src/code_generator.py`：对应生成 `@staticmethod`、`@classmethod`、`@property`

---

## 迭代 3：访问修饰符 + 多继承

### 3.1 私有属性/方法

**语法**：以 `私` 前缀标记私有成员

```
类 示例：
  私属性 密码。
  私段落 内部逻辑：
    ...
```

**改动文件**：解析器、AST、代码生成器

### 3.2 多继承

**语法**：

```
类 狗 继承 动物, 宠物：
  ...

# 或使用「和」分隔
类 狗 继承 动物 和 宠物：
```

**改动文件**：解析器（`_parse_class_definition()`）、AST（`base_class` → `base_classes: List[str]`）、代码生成器