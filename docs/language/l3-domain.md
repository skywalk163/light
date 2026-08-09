# L3 领域嵌入

L3 层直接在光明代码中嵌入 SQL、正则表达式、数学公式，无需特殊标记。

## SQL 嵌入

```python
设 DB = ":memory:"
l3_sql_exec(DB, "CREATE TABLE t (id INTEGER, name TEXT)")
l3_sql_exec(DB, "INSERT INTO t VALUES (1, '张三')")
设 结果 = l3_sql_query(DB, "SELECT * FROM t")
印(结果)
```

## 正则表达式嵌入

```python
设 邮箱正则 = "[a-zA-Z]+@[a-zA-Z]+\\.[a-zA-Z]+"
l3_re_match(邮箱正则, "test@light-lang.org")
```

## 数学公式嵌入

```python
l3_math_solve_quadratic(2, 5, -3)  # 解方程 2x²+5x-3=0
```

## 内置 L3 函数

| 函数 | 说明 |
|------|------|
| `l3_sql_exec(db, sql)` | 执行 SQL 语句 |
| `l3_sql_query(db, sql)` | 查询 SQL 并返回结果 |
| `l3_re_match(pattern, text)` | 正则匹配 |
| `l3_re_findall(pattern, text)` | 查找所有匹配 |
| `l3_math_solve_quadratic(a, b, c)` | 解二次方程 |
| `l3_math_solve_linear(a, b)` | 解线性方程 |