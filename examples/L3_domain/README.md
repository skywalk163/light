# 光明 v4.0 — L3 领域嵌入层（SQL / 正则 / 数学公式）演示

光明 v4.0 分层架构的 **L3 领域嵌入层** 原型：
`引 X:` 语法块把成熟的领域语言直接**融入**光明代码，不需要再翻译成光明函数。

## 3 大领域

| 文件 | 领域 | 功能演示 | 底层库（阶段 B/C） |
|------|------|---------|-------------------|
| `demo1_sql.light` | SQL | 建表 / 批量插入 / 参数化查询 / 聚合统计（AVG/MAX/MIN/COUNT） | Python 标准库 `sqlite3` |
| `demo2_regex.light` | 正则 | 邮箱验证 / 手机号提取 / 命名捕获组（年月日） / 替换 | Python 标准库 `re` |
| `demo3_math.light` | 数学公式 | 解一元二次方程 / 求导 / 定积分 / 矩阵乘法 / 代数化简 | `sympy`（需 pip 安装） |
| `all_in_one_L3_demo.light` | **三合一** | 一个文件同时展示 3 大领域（sympy 未装时自动跳过数学） | sqlite3 + re + sympy |

## 快速开始

```bash
# 1. 装依赖（SQL/正则已经在 Python 标准库里，只有数学需要）
pip install -r examples/L3_domain/requirements_L3.txt
#    ↳ 等价于：pip install sympy

# 2. 跑统一 demo（推荐）
python -m cli.light run examples/L3_domain/all_in_one_L3_demo.light

# 3. 跑单独 demo
python -m cli.light run examples/L3_domain/demo1_sql.light
python -m cli.light run examples/L3_domain/demo2_regex.light
python -m cli.light run examples/L3_domain/demo3_math.light
```

## 阶段 B/C 原型 vs 未来原生（阶段 D 规划）

当前（v4.0 B/C 阶段）：**效果演示优先**——用 `引 Python:` 包一层对应 Python 库来「模拟」领域嵌入效果。
用户先**获得价值**（SQL/正则/数学真的能跑）。

未来（v4.0 D 阶段）：**原生语法落地**——在解析器层识别下列原生前缀，生成安全的参数化代码：

```light
# 未来原生写法（规划中，当前阶段B/C先不写死，避免反复改关键字）
引 SQL: SELECT name,score FROM students WHERE score>:min
    :min = 85
→ 最终生成参数化 SQL（避免注入）

引 模式: 日期 = (?<年>\d{4})-(?<月>\d{2})-(?<日>\d{2})
→ 光明侧获得 日期.年 / 日期.月 / 日期.日 的成员访问

引 公式: 解 2x^2+5x-3=0
→ 光明侧直接返回 list[数]
```

当前「引 Python: 包一层」写法 → 未来「引 SQL/模式/公式:」原生写法**调用侧代码不改变**（只需改引块内部实现，光明调用的 l3_* 函数名/参数不变）。
