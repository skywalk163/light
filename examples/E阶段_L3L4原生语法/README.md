# v4.0 E 阶段 — L3 领域原生语法 + L4 作用域隔离 说明

E 阶段实现了两大能力：
1. **L3 领域原生语法**：`引 SQL` / `引 模式` / `引 公式` 三种前缀，直接写原生 SQL / 正则 / 数学公式，不用包一层 Python 函数。
2. **L4 作用域隔离**：所有 `引 Python` 内部的中间变量（`import numpy as np`、`_tmp`、内部类…）现在都在独立的命名空间里执行，不会污染光明主作用域，只导出公共函数/数据。

> **向后兼容 100%**：C 阶段用 `引 Python: def l3_sql_exec(...)` 这种老写法**依旧可用**，只是 E 阶段多了 3 种原生写法、少写了很多样板代码。

---

## 1. 引 SQL：原生参数化（防注入）

```light
引 SQL 成绩:
    CREATE TABLE students(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, age INTEGER, score REAL);
    INSERT INTO students(name, age, score) VALUES (?, ?, ?);
    SELECT name, age, score FROM students WHERE score > ? ORDER BY score DESC;
结束引
```

**code_generator 自动生成 3 个光明函数**（`CREATE/INSERT` 走 DML，`SELECT` 走查询）：

| 函数名 | 返回 | 说明 |
|--------|------|------|
| `l3_sql_成绩_e0()` | 影响行数（CREATE TABLE 常为 -1） | 建表 |
| `l3_sql_成绩_e1([张三, 22, 88.5])` | 影响行数（通常为 1） | 参数化插入，防注入 |
| `l3_sql_成绩_q2([85])` | `list[dict]` | 查询分数 > 85 的学生 |

- 每个 `引 SQL 标签` 独立持有一个 sqlite3 连接（默认 `:memory:`；标签≠`default` 会创建 `标签.db` 文件）
- 用户写的 SQL 里 `?` 占位符会被 `sqlite3.execute(sql, tuple(params))` 绑定，**天然防注入**
- 未来（v4.1 E+）：加 `引 PG 业务库 / 引 MySQL 主库` 路由到 asyncpg / pymysql，光明调用侧写法不变

demo：[E1_L3_SQL原生.light](./E1_L3_SQL原生.light)

---

## 2. 引 模式：命名捕获组 → 点成员访问

```light
引 模式 日期:
    # 第一行写正则，其他行写注释
    (?P<年>\d{4})-(?P<月>\d{2})-(?P<日>\d{2})
结束引
```

**code_generator 自动生成 1 个类**（类名 = 模式标签），支持 3 个中文类方法：

| 中文类方法 | 等价 Python 行为 |
|-----------|----------------|
| `日期.匹配(文本)` | `re.fullmatch(...)` 全串匹配 |
| `日期.搜索(文本)` | `re.search(...)` 找第一个 |
| `日期.查找全部(文本)` | `re.finditer(...)` 找全部，返回 list |

**返回值的点成员访问**（E 阶段的核心价值！）：
```light
设 d = 日期.匹配("2026-08-04")
打印 d.年   # → "2026"
打印 d.月   # → "08"
打印 d.日   # → "04"
打印 d.hit  # → 真
打印 d      # → 日期<年=2026,月=08,日=04>
若 d: 打印 "命中了！"
```

也就是你不用再写 `d["年"]` 这种「字典写法」，直接 `.年` 就是**光明 L0 风格的成员访问**。

demo：[E2_L3_模式正则原生.light](./E2_L3_模式正则原生.light)

---

## 3. 引 公式：5 种数学公式格式 → 可调用函数

```light
引 公式 例1:
    # 形式1：解代数方程（支持 = 分左右）
    解 2x^2+5x-3=0

    # 形式2：求导
    d/dx (x**3 + 2*x**2)

    # 形式3a：中文写法（积分 sinx 从 0 到 π）
    积分 sin(x) 从 0 到 3.141592653589793
    # 形式3b：符号写法
    ∫(0→3.141592653589793) sin(x) dx

    # 形式4：矩阵乘法
    矩阵乘 [[1,2],[3,4]] * [[5,6],[7,8]]

    # 形式5：默认化简
    (x+1)*(x-1) + (x-2)**2
结束引
```

code_generator 按行解析，每行生成一个光明函数。未安装 `sympy` 时**会在调用时抛出友好异常**（`sympy未装: ...`），不会在加载时崩溃。

demo：[E3_L3_公式数学原生.light](./E3_L3_公式数学原生.light)

---

## 4. L4 作用域隔离：引 Python 不再"污染"光明变量

**之前（v4.0 D 及更早）**：引 Python 里写的代码和光明生成的代码共享同一个 Python 模块命名空间。
```python
# 引 Python:
import numpy as np
_tmp = 9999
def f(x): return x*x
```
→ 光明里你会有一个叫 `np` 的变量、一个叫 `_tmp` 的变量。万一你自己也想叫 `np` 就重名了；更糟的是内部类、密码、配置也会泄漏。

**现在（v4.0 E）**：引 Python 里的代码都在一个独立的 `types.ModuleType("_LIGHT_L4_NS")` 里执行，然后按**三条导出规则**决定哪些名字暴露给光明：

| 你写的引 Python 代码 | 导出？ | 原因 |
|-------------------|--------|------|
| `def l3_solve(...): ...` | ✅ | 以 `l3_` 开头，强制导出 |
| `def l4_add(...): ...` | ✅ | 以 `l4_` 开头，强制导出 |
| `def 公共函数(n): return n*n` | ✅ | 不以 `_` 开头 **且 callable** |
| `L4_PI = 3.14159` | ✅ | 不以 `_` 开头 **且** 在基本数据白名单（int/float/str/list/dict/tuple/bool/None） |
| `某Dict = {"a":1}` | ✅ | dict 属于基本数据白名单 |
| `import numpy as np` | ❌ | `np` 是 module，不在白名单（保护光明侧） |
| `_tmp = 9999` | ❌ | 以 `_` 开头（内部变量） |
| `_PASSWORD = "s3cret"` | ❌ | 以 `_` 开头（敏感数据） |
| `class 内部类: pass` | ❌ | `type` 对象不在白名单（不在 callable+基本数据 → 白名单仅额外加 callable，类确实是 callable，**但 E4 版本会在 C/D 阶段的「贡献/模块」里控制是否导出类，当前版本为了保持最小破坏先 export 类**。如需严格隔离请 `class _内部类:` 加下划线） |

demo：[E4_L4_沙箱隔离验证.light](./E4_L4_沙箱隔离验证.light)

---

## 5. 对 C 阶段（v4.0 C 效果演示）的兼容性

C 阶段用的写法（`引 Python: 里面自己 def l3_sql_exec()`）**100% 依旧可用**：
- L4 作用域隔离的导出规则 `以 l3_/l4_ 开头强制导出` 就是为了兼容 C 阶段用户已经写的 l3_*/l4_* 函数。
- 旧 demo (`examples/L3_domain/`、`examples/L4_python/`) 继续运行，不需要改。

**新代码推荐用 E 阶段的 3 种原生写法**——少写样板，可读性更强。
