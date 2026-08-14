# SQLite API

> 模块路径：`stdlib/SQLite.py`
> 导入方式：`从 SQLite 导入 函数名` 或 `导入 SQLite`

---

## 函数列表

| 函数 | 说明 |
|------|------|
| `打开数据库(路径)` | 打开/创建 SQLite 数据库，返回 DBConn |
| `关闭数据库(db)` | 关闭数据库连接 |
| `_dbconn_replace_conn(self, conn)` |  |
| `执行SQL(db, sql, params)` | 执行 SQL 语句（INSERT/UPDATE/DELETE/DDL），返回受影响行数 |
| `批量执行(db, sql, params_list)` | 批量执行 SQL（参数化），返回受影响行数 |
| `查询(db, sql, params)` | 执行查询 SQL，返回 QueryResult |
| `查询单条(db, sql, params)` | 查询单条记录，返回 dict 或 None |
| `查询所有(db, sql, params)` | 查询所有记录，返回 list[dict] |
| `开始事务(db)` | 开始事务 |
| `提交事务(db)` | 提交事务 |
| `回滚事务(db)` | 回滚事务 |
| `最后插入ID(db)` | 获取最后插入的行 ID |
| `受影响行数(db)` | 获取上次操作受影响行数 |
| `表是否存在(db, 表名)` | 检查表是否存在 |
| `获取所有表(db)` | 获取所有表名列表 |
| `获取表结构(db, 表名)` | 获取表的列信息 |
| `准备语句(db, sql)` | 准备 SQL 语句，返回 Stmt |
| `绑定文本(stmt, index, value)` | 绑定文本参数 |
| `绑定整数(stmt, index, value)` | 绑定整数参数 |
| `绑定浮点(stmt, index, value)` | 绑定浮点参数 |
| `绑定空值(stmt, index)` | 绑定 NULL 参数 |
| `执行语句(stmt)` | 执行预处理语句 |
| `重置语句(stmt)` | 重置预处理语句 |
| `释放语句(stmt)` | 释放预处理语句 |
| `创建查询(table)` | 创建查询构建器 |
| `查询构建器_select(qb)` | 设置查询列 |
| `查询构建器_where(qb, condition)` | 添加 WHERE 条件 |
| `查询构建器_order(qb)` | 添加 ORDER BY |
| `查询构建器_limit(qb, limit, offset)` | 设置 LIMIT |
| `查询构建器执行(db, qb)` | 执行查询构建器，返回 QueryResult |
| `__init__(self, path, opened)` |  |
| `__init__(self, col_names, rows, row_count, col_count)` |  |
| `__init__(self, sql, db)` |  |
| `__init__(self, table)` |  |
| `__init__(self, version, desc, up_sql, down_sql)` |  |

---

## 函数详情

### `打开数据库(路径)`

打开/创建 SQLite 数据库，返回 DBConn

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `路径` | `None` |  |

---

### `关闭数据库(db)`

关闭数据库连接

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |

---

### `_dbconn_replace_conn(self, conn)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `conn` | `None` |  |

---

### `执行SQL(db, sql, params = None)`

执行 SQL 语句（INSERT/UPDATE/DELETE/DDL），返回受影响行数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |
| `sql` | `None` |  |
| `params` | `None` | （默认：None） |

---

### `批量执行(db, sql, params_list)`

批量执行 SQL（参数化），返回受影响行数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |
| `sql` | `None` |  |
| `params_list` | `None` |  |

---

### `查询(db, sql, params = None)`

执行查询 SQL，返回 QueryResult

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |
| `sql` | `None` |  |
| `params` | `None` | （默认：None） |

---

### `查询单条(db, sql, params = None)`

查询单条记录，返回 dict 或 None

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |
| `sql` | `None` |  |
| `params` | `None` | （默认：None） |

---

### `查询所有(db, sql, params = None)`

查询所有记录，返回 list[dict]

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |
| `sql` | `None` |  |
| `params` | `None` | （默认：None） |

---

### `开始事务(db)`

开始事务

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |

---

### `提交事务(db)`

提交事务

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |

---

### `回滚事务(db)`

回滚事务

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |

---

### `最后插入ID(db)`

获取最后插入的行 ID

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |

---

### `受影响行数(db)`

获取上次操作受影响行数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |

---

### `表是否存在(db, 表名)`

检查表是否存在

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |
| `表名` | `None` |  |

---

### `获取所有表(db)`

获取所有表名列表

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |

---

### `获取表结构(db, 表名)`

获取表的列信息

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |
| `表名` | `None` |  |

---

### `准备语句(db, sql)`

准备 SQL 语句，返回 Stmt

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |
| `sql` | `None` |  |

---

### `绑定文本(stmt, index, value)`

绑定文本参数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `stmt` | `None` |  |
| `index` | `None` |  |
| `value` | `None` |  |

---

### `绑定整数(stmt, index, value)`

绑定整数参数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `stmt` | `None` |  |
| `index` | `None` |  |
| `value` | `None` |  |

---

### `绑定浮点(stmt, index, value)`

绑定浮点参数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `stmt` | `None` |  |
| `index` | `None` |  |
| `value` | `None` |  |

---

### `绑定空值(stmt, index)`

绑定 NULL 参数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `stmt` | `None` |  |
| `index` | `None` |  |

---

### `执行语句(stmt)`

执行预处理语句

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `stmt` | `None` |  |

---

### `重置语句(stmt)`

重置预处理语句

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `stmt` | `None` |  |

---

### `释放语句(stmt)`

释放预处理语句

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `stmt` | `None` |  |

---

### `创建查询(table)`

创建查询构建器

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `table` | `None` |  |

---

### `查询构建器_select(qb)`

设置查询列

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `qb` | `None` |  |

---

### `查询构建器_where(qb, condition)`

添加 WHERE 条件

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `qb` | `None` |  |
| `condition` | `None` |  |

---

### `查询构建器_order(qb)`

添加 ORDER BY

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `qb` | `None` |  |

---

### `查询构建器_limit(qb, limit, offset = None)`

设置 LIMIT

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `qb` | `None` |  |
| `limit` | `None` |  |
| `offset` | `None` | （默认：None） |

---

### `查询构建器执行(db, qb)`

执行查询构建器，返回 QueryResult

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `db` | `None` |  |
| `qb` | `None` |  |

---

### `__init__(self, path = '', opened = False)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `path` | `None` | （默认：''） |
| `opened` | `None` | （默认：False） |

---

### `__init__(self, col_names = None, rows = None, row_count = 0, col_count = 0)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `col_names` | `None` | （默认：None） |
| `rows` | `None` | （默认：None） |
| `row_count` | `None` | （默认：0） |
| `col_count` | `None` | （默认：0） |

---

### `__init__(self, sql = '', db = None)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `sql` | `None` | （默认：''） |
| `db` | `None` | （默认：None） |

---

### `__init__(self, table = '')`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `table` | `None` | （默认：''） |

---

### `__init__(self, version = 0, desc = '', up_sql = '', down_sql = '')`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `version` | `None` | （默认：0） |
| `desc` | `None` | （默认：''） |
| `up_sql` | `None` | （默认：''） |
| `down_sql` | `None` | （默认：''） |

---

## 常量

| 常量名 | 值 |
|--------|-----|
| `result` | `查询(db, sql, params)` |
| `row` | `result.rows[0]` |
| `result` | `查询(db, sql, params)` |
| `result` | `查询单条(db, "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (表名,))` |
| `result` | `查询(db, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")` |
| `result` | `查询(db, 'PRAGMA table_info(' + 表名 + ')')` |
| `columns` | `[]` |
| `sql` | `'SELECT '` |
| `params` | `[]` |
| `conn` | `_sqlite3.connect(路径)` |
| `cursor` | `db._conn.cursor()` |
| `cursor` | `db._conn.cursor()` |
| `cursor` | `db._conn.cursor()` |
| `rows` | `cursor.fetchall()` |
| `col_names` | `[desc[0] for desc in cursor.description] if cursor.description else []` |
| `row_list` | `[]` |
| `stmt` | `Stmt(sql=sql, db=db)` |
| `params` | `qb.cond_params` |
