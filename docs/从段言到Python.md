# 从段言到 Python —— 段言开发者迁移指南

> **版本：** v6.2  
> **更新日期：** 2026-08-07  
> **适用对象：** 已掌握段言、希望学习 Python 的开发者，以及已掌握 Python、希望快速上手段言的开发者

---

## 目录

1. [为什么要学 Python？——段言作为 Python 的"认知跳板"](#1-为什么要学-python段言作为-python-的认知跳板)
2. [语法对照速查表](#2-语法对照速查表)
3. [核心概念映射](#3-核心概念映射)
4. [标准库对照](#4-标准库对照)
5. [段言独特优势如何在 Python 中实现](#5-段言独特优势如何在-python-中实现)
6. [实战迁移示例](#6-实战迁移示例)
7. [学习路径建议](#7-学习路径建议)

---

## 1. 为什么要学 Python？——段言作为 Python 的"认知跳板"

### 1.1 Python 的生态优势

Python 拥有全球最大的编程语言生态系统之一，在以下领域占据主导地位：

| 领域 | 代表库/框架 | 说明 |
|------|------------|------|
| 数据科学 & 机器学习 | NumPy, Pandas, Scikit-learn, TensorFlow, PyTorch | 业界标准工具链 |
| Web 开发 | Django, Flask, FastAPI | 成熟的全栈框架 |
| 自动化运维 | Ansible, Fabric, SaltStack | 运维领域事实标准 |
| 人工智能 & NLP | Transformers, LangChain, OpenAI API | 大模型时代首选语言 |
| 科学计算 | SciPy, Matplotlib, SymPy | 学术研究标配 |
| 网络爬虫 | Scrapy, BeautifulSoup, Playwright | 数据采集首选 |

### 1.2 段言 → Python：一条平滑的迁移路径

段言的设计深受 Python 影响——两者共享相似的缩进风格、动态类型哲学和面向对象模型。段言的标准库本身就是 Python 和段言双语言实现的。这意味着：

- **段言开发者学习 Python 的成本极低**——语法结构高度相似，只是关键字从中文变为英文
- **Python 开发者学习段言几乎零门槛**——很多段言概念在 Python 中都有对应物
- **两者可以互补使用**——段言适合快速原型和中文场景，Python 适合深度生态依赖的项目

### 1.3 段言作为"认知跳板"的优势

段言的「词句段篇」层级和全中文关键字，让你在掌握编程逻辑的同时，已自然建立了对以下核心概念的理解：

| 段言概念 | Python 对应 | 认知迁移难度 |
|---------|------------|------------|
| 段落（函数） | `def` 函数 | 极低（只需记住英文关键字） |
| 如果/否则 | `if`/`else` | 极低 |
| 遍历/当 | `for`/`while` | 极低 |
| 类/构造/己 | `class`/`__init__`/`self` | 低 |
| 尝试/捕获 | `try`/`except` | 极低 |

**核心结论：** 如果你已经掌握了段言，你已经掌握了 80% 的 Python 编程思维。剩下的 20% 只是关键字和库的差异。

---

## 2. 语法对照速查表

### 2.1 变量与赋值

| 段言 | Python | 说明 |
|------|--------|------|
| `设 x 为 10` | `x = 10` | 基本变量赋值 |
| `设 x, y 为 10, 20` | `x, y = 10, 20` | 多重赋值 |
| `设 名字 为 "张三"` | `name = "张三"` | 字符串赋值 |
| `x = 10`（英文兼容） | `x = 10` | 段言兼容英文赋值写法 |
| `设 常量 为 100` | `CONSTANT = 100`（约定） | 常量（段言无const，Python靠命名约定） |

### 2.2 条件判断

| 段言 | Python | 说明 |
|------|--------|------|
| `如果 条件：` | `if 条件:` | 基本条件判断 |
| `否则：` | `else:` | 否则分支 |
| `否则如果 条件：` | `elif 条件:` | 多重条件 |
| `条件 且 条件2` | `条件 and 条件2` | 逻辑与 |
| `条件 或 条件2` | `条件 or 条件2` | 逻辑或 |
| `非 条件` | `not 条件` | 逻辑非 |
| `值 若 条件 否则 默认值` | `值 if 条件 else 默认值` | 三元表达式 |

### 2.3 循环

| 段言 | Python | 说明 |
|------|--------|------|
| `遍历 元素 于 列表：` | `for 元素 in 列表:` | for-each 循环 |
| `当 条件：` | `while 条件:` | while 循环 |
| `跳出` | `break` | 跳出循环 |
| `继续` | `continue` | 继续下一次循环 |
| `遍历 i, v 于 枚举(列表)：` | `for i, v in enumerate(列表):` | 带索引的遍历 |
| `遍历 键 于 字典：` | `for 键 in 字典:` | 遍历字典键 |
| `[x 遍历 x 于 列表 若 条件]` | `[x for x in 列表 if 条件]` | 列表推导式 |

### 2.4 函数定义

| 段言 | Python | 说明 |
|------|--------|------|
| `段落 函数名 接收 参数：` | `def 函数名(参数):` | 函数定义 |
| `段落 函数名 接收 a, b：` | `def 函数名(a, b):` | 多参数函数 |
| `返回 值` | `return 值` | 返回值 |
| `段落 函数名 接收 a = 10：` | `def 函数名(a=10):` | 默认参数 |
| `段落 函数名 接收 *参数：` | `def 函数名(*参数):` | 可变参数 |
| `段落 函数名 接收 **参数：` | `def 函数名(**参数):` | 关键字参数 |
| `段落 函数名 接收 a: 整数 返回 串：` | `def 函数名(a: int) -> str:` | 类型注解 |

### 2.5 类与对象

| 段言 | Python | 说明 |
|------|--------|------|
| `类 类名：` | `class 类名:` | 类定义 |
| `构造 接收 参数：` | `def __init__(self, 参数):` | 构造函数 |
| `己.属性` | `self.属性` | 实例属性访问 |
| `类 子类 继承 父类：` | `class 子类(父类):` | 继承 |
| `覆盖 段落 方法 接收 参数：` | `def 方法(self, 参数):`（自动覆盖） | 方法覆盖 |
| `类.静态方法()` | `@staticmethod` | 静态方法（段言暂未支持装饰器语法） |

### 2.6 异常处理

| 段言 | Python | 说明 |
|------|--------|------|
| `尝试：` | `try:` | 尝试执行 |
| `捕获 错误 为 e：` | `except 错误 as e:` | 捕获异常 |
| `捕获：` | `except:` | 捕获所有异常 |
| `最终：` | `finally:` | 最终执行 |
| `抛出 异常` | `raise 异常` | 抛出异常 |
| `抛出 "错误信息"` | `raise Exception("错误信息")` | 抛出异常信息 |

### 2.7 列表/字典操作

| 段言 | Python | 说明 |
|------|--------|------|
| `列表 = [1, 2, 3]` | `列表 = [1, 2, 3]` | 列表创建 |
| `字典 = {"键": "值"}` | `字典 = {"键": "值"}` | 字典创建 |
| `列表[0]` | `列表[0]` | 索引访问 |
| `列表[0 到 3]` | `列表[0:3]` | 切片 |
| `列表长度(列表)` | `len(列表)` | 获取长度 |
| `列表追加(列表, 元素)` | `列表.append(元素)` | 追加元素 |
| `列表删除(列表, 索引)` | `del 列表[索引]` | 删除元素 |
| `排序(列表, 倒序 为 真)` | `sorted(列表, reverse=True)` | 排序 |
| `字典["键"]` | `字典["键"]` | 字典访问 |
| `字典.获取("键", 默认值)` | `字典.get("键", 默认值)` | 安全获取 |

### 2.8 模块导入

| 段言 | Python | 说明 |
|------|--------|------|
| `从 模块 导入 函数` | `from 模块 import 函数` | 导入特定函数 |
| `导入 模块` | `import 模块` | 导入整个模块 |
| `从 模块 导入 a, b` | `from 模块 import a, b` | 导入多个 |
| `从 模块 导入 函数 为 别名` | `from 模块 import 函数 as 别名` | 别名导入 |
| `从 模块 导入 *` | `from 模块 import *` | 通配符导入 |

### 2.9 文件操作

| 段言 | Python | 说明 |
|------|--------|------|
| `读取文件(路径)` | `open(路径).read()` | 读取文件内容 |
| `写入文件(路径, 内容)` | `open(路径, 'w').write(内容)` | 写入文件 |
| `追加文件(路径, 内容)` | `open(路径, 'a').write(内容)` | 追加内容 |
| `文件存在(路径)` | `os.path.exists(路径)` | 检查文件存在 |
| `创建目录(路径)` | `os.makedirs(路径)` | 创建目录 |
| `列出目录(路径)` | `os.listdir(路径)` | 列出目录内容 |
| `删除文件(路径)` | `os.remove(路径)` | 删除文件 |

### 2.10 上下文管理器

| 段言 | Python | 说明 |
|------|--------|------|
| `使用 资源 为 r：` | `with 资源 as r:` | 基本上下文管理 |
| `使用 打开文件(路径) 为 f：` | `with open(路径) as f:` | 文件上下文管理 |
| `使用 临时文件() 为 f：` | `with tempfile.NamedTemporaryFile() as f:` | 临时文件 |
| `使用 更改目录(路径)：` | 手动 `os.chdir` | 临时更改目录 |

### 2.11 装饰器

| 段言 | Python | 说明 |
|------|--------|------|
| `@装饰器` | `@装饰器` | 装饰器语法（段言兼容） |
| `段落 装饰器 接收 函数：` | `def 装饰器(函数):` | 定义装饰器 |
| `段落 包装 接收 *参数, **关键字参数：` | `def 包装(*参数, **关键字参数):` | 装饰器包装函数 |
| `@缓存装饰器` | `@functools.lru_cache` | 缓存装饰器 |
| `@计时装饰器` | 自定义 `@计时` | 计时装饰器 |

### 2.12 异步编程

| 段言 | Python | 说明 |
|------|--------|------|
| `异步 段落 函数名 接收 参数：` | `async def 函数名(参数):` | 异步函数定义 |
| `等待 异步函数()` | `await 异步函数()` | 等待异步结果 |
| `异步 遍历 元素 于 异步生成器：` | `async for 元素 in 异步生成器:` | 异步遍历 |
| `异步 使用 资源：` | `async with 资源:` | 异步上下文管理器 |
| `运行(异步函数())` | `asyncio.run(异步函数())` | 运行异步函数 |

### 2.13 模式匹配（Python 3.10+）

| 段言 | Python | 说明 |
|------|--------|------|
| `匹配 值：` | `match 值:` | 模式匹配开始 |
| `情况 模式：` | `case 模式:` | 匹配单个模式 |
| `情况 模式 若 条件：` | `case 模式 if 条件：` | 带守卫的模式匹配 |
| `情况 _：` | `case _：` | 通配匹配 |
| `情况 [a, b, c]：` | `case [a, b, c]：` | 序列模式匹配 |
| `情况 {"键": 值}：` | `case {"键": 值}：` | 字典模式匹配 |

---

## 3. 核心概念映射

### 3.1 词句段篇 → Python 模块/函数/语句

段言的核心设计理念是「词句段篇」四层架构，在 Python 中每一层都有直接对应：

| 段言层级 | 含义 | Python 对应 | 说明 |
|---------|------|------------|------|
| **词** | 变量、操作符、关键字 | 标识符、运算符、关键字 | 完全相同，只是关键字从中文变为英文 |
| **句** | 一条完整的语句 | 语句（statement） | 段言用句号或换行结束，Python 用换行 |
| **段** | 函数/代码块 | 函数（function） | 段言用「段落」定义，Python 用 `def` |
| **篇** | 模块/程序 | 模块（module）/ 脚本 | 段言的 `.duan` 文件对应 Python 的 `.py` 文件 |

**迁移要点：**
- 段言的一篇（一个 `.duan` 文件）对应 Python 的一个 `.py` 文件
- 段言的段落（函数）对应 Python 的 `def` 函数
- 段言的词（变量名）在 Python 中可直接使用中文变量名（Python 3 支持 Unicode 标识符）

### 3.2 元数驱动 → Python 参数解析

段言的元数驱动解析器通过动词的参数数量判断语句结构，Python 虽然没有元数驱动的概念，但通过参数解析机制实现了类似的功能：

| 段言元数概念 | Python 对应 | 说明 |
|-------------|------------|------|
| 一元（`打印 内容`） | 单参数函数 | `print(内容)` |
| 二元（`设 甲 为 乙`） | 双参数赋值 | `甲 = 乙` |
| 三元（`从 模块 导入 函数`） | `from 模块 import 函数` | 固定语法结构 |
| 可变元数（`列表追加(列表, 元素)`） | `列表.append(元素)` | 方法调用 |
| 关键字参数 | `函数(参数名=值)` | 段言也支持 `函数(参数名=值)` |

**迁移要点：**
- 段言的元数驱动主要体现在语法解析层面，Python 的函数调用机制更灵活但更依赖符号
- 段言中 `从 列表 中 取 首个` 这样的三元结构，在 Python 中写为 `列表[0]`
- 命名参数在两种语言中都是推荐的做法

### 3.3 类型系统 → Python 类型注解

| 段言类型系统 | Python 对应 | 说明 |
|-------------|------------|------|
| `整数` | `int` | 整型 |
| `小数` | `float` | 浮点型 |
| `串` | `str` | 字符串 |
| `布尔` | `bool` | 布尔型 |
| `列/列表` | `list` | 列表 |
| `表/字典` | `dict` | 字典 |
| `空` | `None` | 空值 |
| `a: 整数`（类型注解） | `a: int`（类型注解） | 类型注解语法 |
| `段落 函数 接收 a: 整数 返回 串` | `def 函数(a: int) -> str:` | 函数签名类型注解 |
| HM 类型推断 | 鸭子类型 + 可选类型注解 | 段言编译时推断，Python 运行时确定 |

**迁移要点：**
- Python 3.5+ 支持类型注解，语法与段言类似
- Python 的类型注解是**可选的**，运行时不会强制执行（段言的三级类型检查则更严格）
- 段言的 HM 类型推断在编译时进行，Python 的类型检查需要借助 `mypy` 等外部工具

### 3.4 C FFI → Python ctypes

| 段言 C FFI | Python 对应 | 说明 |
|-----------|------------|------|
| `加载库 "lib.so" 为 math` | `ctypes.CDLL("lib.so")` | 加载动态库 |
| `外部 段落 函数 接收 参数 在 库` | 声明 `argtypes` 和 `restype` | 声明外部函数 |
| `结构体 定义` | `class 结构体(ctypes.Structure)` | 结构体定义 |
| 指针操作 | `ctypes.pointer()` | 指针操作 |
| 回调函数 | `ctypes.CFUNCTYPE` | 回调函数 |

**迁移要点：**
- Python 的 `ctypes` 标准库功能与段言 C FFI 类似，但语法更繁琐
- 对于更现代的 C 绑定，Python 还支持 `cffi` 和 `Cython` 等第三方方案
- 段言的 C FFI 设计更简洁，但 Python 的 ctypes 生态更成熟

---

## 4. 标准库对照

段言标准库提供了 60+ 个模块，以下是常用模块与 Python 标准库的对照表：

| 段言模块 | Python 标准库 | 说明 |
|---------|--------------|------|
| `数学` | `math` | 数学函数（三角函数、对数、阶乘等） |
| `字符串处理` | `str` 内置方法 / `string` | 字符串操作（分割、拼接、替换、查找） |
| `文件系统` | `os` / `pathlib` / `shutil` | 文件和目录操作 |
| `CSV` | `csv` | CSV 文件读写 |
| `JSON` | `json` | JSON 解析与序列化 |
| `HTTP客户端` | `urllib.request` / `requests`（第三方） | HTTP 请求 |
| `日期时间` | `datetime` | 日期时间处理 |
| `随机` | `random` | 随机数生成 |
| `正则表达式` | `re` | 正则匹配与替换 |
| `日志` | `logging` | 日志记录 |
| `集合` | `collections` | 集合操作与数据结构 |
| `加密` | `hashlib` / `cryptography` | 加密与哈希 |
| `网络套接字` | `socket` | TCP/UDP 网络通信 |
| `线程` | `threading` | 多线程编程 |
| `进程` | `multiprocessing` | 多进程编程 |
| `时间管理` | `time` | 时间工具（休眠、计时） |
| `编码解码` | `base64` / `urllib.parse` | 编码转换 |
| `统计函数` | `statistics` | 统计计算 |
| `矩阵运算` | `numpy`（第三方） | 矩阵运算 |
| `迭代工具` | `itertools` | 迭代器工具 |
| `模板引擎` | `string.Template` / `jinja2`（第三方） | 模板渲染 |
| `数据库` | `sqlite3` | SQLite 数据库 |
| `XML` | `xml.etree.ElementTree` | XML 解析 |
| `压缩` | `zipfile` / `gzip` / `tarfile` | 文件压缩与归档 |
| `系统信息` | `sys` / `platform` | 系统信息查询 |

**迁移要点：**
- 段言标准库的函数名是中文的，Python 标准库的函数名是英文的
- 段言标准库的 API 设计更「粗粒度」（一个函数完成多个步骤），Python 标准库更「细粒度」
- 例如：段言的 `解析CSV文件(路径)` 对应 Python 的 `open() + csv.DictReader()` 两步
- Python 的第三方库生态（PyPI 上 50 万+ 包）远超段言的 duanpub 注册中心

---

## 5. 段言独特优势如何在 Python 中实现

段言的一些独特设计在 Python 中没有原生支持，但可以通过编码实践来模拟。

### 5.1 词句段篇层级 → 良好的模块化设计

段言的「词句段篇」层级在 Python 中可以通过良好的代码组织来模拟：

```python
# 篇级：模块（.py 文件）
# 文件：data_processor.py

# 段级：函数（携带上下文）
import csv
import os

def process_scores(filepath):
    """句级：完整的函数逻辑"""
    # 词级：变量和操作
    data = []
    if not os.path.exists(filepath):
        return data
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    return data
```

**建议：** 将段言的「段级上下文继承」思想应用到 Python 中的嵌套函数和闭包。

### 5.2 元数驱动 → 类型重载 + 命名参数

段言的元数驱动解析在 Python 中可以通过函数重载和命名参数来模拟：

```python
# Python 中没有真正的函数重载，但可以用默认参数和类型判断模拟
from functools import singledispatch

@singledispatch
def 处理(数据):
    raise TypeError(f"不支持的类型：{type(数据)}")

@处理.register
def _(数据: str):
    return f"处理字符串：{数据}"

@处理.register
def _(数据: list):
    return f"处理列表：{len(数据)} 个元素"

# 更实用的方式：命名参数
def 查询(来源, 条件=None, 排序=None, 限制=None):
    """命名参数使调用语义自明"""
    pass

# 调用
查询(来源="数据库", 条件="年龄 > 18", 排序="年龄", 限制=10)
```

### 5.3 中文关键字 → 中文变量名 + 函数名

Python 3 支持 Unicode 标识符，可以在 Python 中使用中文命名：

```python
# Python 完全支持中文变量名和函数名
def 计算平均分(成绩列表):
    总分 = sum(成绩列表)
    人数 = len(成绩列表)
    return 总分 / 人数 if 人数 > 0 else 0

学生成绩 = [85, 92, 78, 95, 88]
平均分 = 计算平均分(学生成绩)
print(f"平均分：{平均分}")
```

**注意：** 虽然技术上可行，但在 Python 社区中混合中英文命名可能降低代码的可维护性。建议仅在团队内部或个人项目中使用。

### 5.4 上下文继承 → 闭包和类属性

段言的段落可以自动读取父作用域的变量（上下文继承），Python 中可以通过闭包或类属性来实现：

```python
# 闭包实现上下文继承
def 创建处理器(配置):
    阈值 = 配置["阈值"]
    模式 = 配置["模式"]
    
    def 处理数据(数据):
        # 自动继承外部变量：阈值、模式
        if 模式 == "严格":
            return [x for x in 数据 if x > 阈值]
        else:
            return [x for x in 数据 if x >= 阈值]
    
    return 处理数据

处理器 = 创建处理器({"阈值": 80, "模式": "严格"})
结果 = 处理器([75, 85, 95])  # [85, 95]
```

### 5.5 段言的三元表达式 → Python 的三元表达式

```python
# 段言：值 若 条件 否则 默认值
# Python：值 if 条件 else 默认值

# 段言风格
描述 = "优秀" if 分数 >= 90 else "普通"

# 嵌套三元
等级 = "优秀" if 分数 >= 90 else "良好" if 分数 >= 80 else "及格" if 分数 >= 60 else "不及格"
```

---

## 6. 实战迁移示例

### 6.1 案例一：CSV 数据处理

**场景：** 读取学生成绩 CSV 文件，计算各科平均分，筛选出总分排名前三的学生，将结果写入新文件。

#### 段言版本

```段言
从 CSV 导入 解析CSV文件, 序列化CSV文件, 转字典列表
从 文件系统 导入 文件存在

段落 分析成绩 接收 输入文件, 输出文件：
    如果 非 文件存在(输入文件)：
        打印("文件不存在：" + 输入文件)
        返回 空, []
    
    设 原始数据 为 解析CSV文件(输入文件)
    设 学生列表 为 转字典列表(原始数据)
    
    如果 列表长度(学生列表) 等于 0：
        返回 空, []
    
    # 计算各科平均分
    设 科目 为 ["语文", "数学", "英语"]
    设 平均分 为 {}
    遍历 科目 于 科目：
        设 分数列表 为 []
        遍历 学生 于 学生列表：
            列表追加(分数列表, 整数(学生[科目]))
        设 总分 为 0
        遍历 分数 于 分数列表：
            设 总分 为 总分 加 分数
        平均分[科目] 为 总分 除以 列表长度(分数列表)
    
    # 计算每个学生的总分
    遍历 学生 于 学生列表：
        设 学生总分 为 0
        遍历 科目 于 科目：
            设 学生总分 为 学生总分 加 整数(学生[科目])
        学生["总分"] 为 学生总分
    
    # 按总分排序取前3
    设 排序后 为 排序(学生列表, 依据 键 为 学生 => 学生["总分"], 倒序 为 真)
    设 前三名 为 排序后[0 到 3]
    
    # 写入结果
    设 输出数据 为 []
    设 序号 为 1
    遍历 学生 于 前三名：
        列表追加(输出数据, {
            "姓名": 学生["姓名"],
            "语文": 学生["语文"],
            "数学": 学生["数学"],
            "英语": 学生["英语"],
            "总分": 学生["总分"],
            "排名": 序号
        })
        设 序号 为 序号 加 1
    
    序列化CSV文件(输出文件, 输出数据)
    返回 平均分, 前三名

# 使用
设 平均分, 前三名 为 分析成绩("成绩.csv", "前三名.csv")
打印("平均分：" + 转字符串(平均分))
打印("前三名：")
遍历 学生 于 前三名：
    打印(学生["姓名"] + " - " + 转字符串(学生["总分"]))
```

#### Python 版本

```python
import csv
import os

def analyze_grades(input_file, output_file):
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"文件不存在：{input_file}")
        return None, []
    
    # 读取数据
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        students = list(reader)
    
    if not students:
        return None, []
    
    # 计算各科平均分
    subjects = ["语文", "数学", "英语"]
    averages = {}
    for subject in subjects:
        scores = [int(s[subject]) for s in students]
        averages[subject] = sum(scores) / len(scores)
    
    # 计算每个学生的总分
    for s in students:
        s["总分"] = sum(int(s[sub]) for sub in subjects)
    
    # 按总分排序取前3
    sorted_students = sorted(students, key=lambda s: s["总分"], reverse=True)
    top3 = sorted_students[:3]
    
    # 写入结果
    fieldnames = ["姓名"] + subjects + ["总分", "排名"]
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, s in enumerate(top3, 1):
            writer.writerow({
                "姓名": s["姓名"],
                "语文": s["语文"],
                "数学": s["数学"],
                "英语": s["英语"],
                "总分": s["总分"],
                "排名": i
            })
    
    return averages, top3

# 使用
averages, top3 = analyze_grades("成绩.csv", "前三名.csv")
print(f"平均分：{averages}")
print("前三名：")
for s in top3:
    print(f"{s['姓名']} - {s['总分']}")
```

#### 关键差异分析

| 维度 | 段言 | Python | 迁移建议 |
|------|------|--------|---------|
| 文件操作 | `文件存在()` 直接检查 | `os.path.exists()` 需导入 os 模块 | 记住 Python 需要显式导入模块 |
| CSV 读取 | `解析CSV文件(路径)` 一步完成 | `open() + csv.DictReader()` 两步 | Python 需要理解上下文管理器 `with` |
| 列表推导 | 显式 `遍历 + 列表追加` | 生成器表达式 `sum(int(s[sub]) for sub in subjects)` | Python 的生成器表达式更简洁，但需要适应 |
| 排序 | 命名参数 `依据 键 为 ..., 倒序 为 真` | `key=lambda, reverse=True` | 需要理解 lambda 表达式 |
| 字符串拼接 | `"文本" + 转字符串(值)` | f-string：`f"文本{值}"` | Python 的 f-string 更简洁 |
| CSV 写入 | `序列化CSV文件(路径, 数据)` 一步 | `DictWriter + writeheader + writerow` 三步 | Python 更细粒度，灵活性更高 |

#### 迁移建议

1. **最需要适应的变化：** Python 的上下文管理器（`with` 语句）和 lambda 表达式
2. **最享受的变化：** Python 的列表推导式和生成器表达式大幅减少代码量
3. **最容易忽略的细节：** Python 的 `open()` 需要显式指定编码和模式

---

### 6.2 案例二：Web 爬虫

**场景：** 抓取 GitHub 用户仓库列表，筛选星标数超过 100 的仓库，按星标数排序后输出关键信息。

#### 段言版本

```段言
从 HTTP客户端 导入 HTTP客户端
从 JSON 导入 解析JSON

段落 获取热门仓库 接收 用户名, 最少星标 = 100：
    设 客户端 为 HTTP客户端(超时=10)
    客户端.设置请求头("Accept", "application/vnd.github.v3+json")
    
    设 URL 为 "https://api.github.com/users/" + 用户名 + "/repos"
    
    尝试：
        设 响应 为 客户端.GET(URL)
        如果 响应.状态码 不等于 200：
            抛出 "请求失败：" + 转字符串(响应.状态码)
    捕获 错误 为 e：
        打印("请求失败：" + 转字符串(e))
        返回 []
    
    设 仓库列表 为 解析JSON(响应.正文)
    
    # 筛选星标超过阈值的仓库
    设 热门仓库 为 []
    遍历 仓库 于 仓库列表：
        如果 仓库["stargazers_count"] 大于等于 最少星标：
            列表追加(热门仓库, 仓库)
    
    # 按星标数排序（降序）
    设 排序后 为 排序(热门仓库, 依据 键 为 仓库 => 仓库["stargazers_count"], 倒序 为 真)
    
    # 提取关键信息
    设 结果 为 []
    遍历 仓库 于 排序后：
        设 描述 为 仓库["description"] 若 仓库["description"] 不等于 空 否则 ""
        列表追加(结果, {
            "名称": 仓库["name"],
            "星标": 仓库["stargazers_count"],
            "描述": 描述,
            "语言": 仓库["language"] 若 仓库["language"] 不等于 空 否则 "未知",
            "地址": 仓库["html_url"]
        })
    
    返回 结果

# 使用
设 仓库 为 获取热门仓库("skywalk163")
打印("找到 " + 转字符串(列表长度(仓库)) + " 个热门仓库：")
遍历 仓库 于 仓库：
    打印("⭐ " + 转字符串(仓库["星标"]) + " - " + 仓库["名称"] + " (" + 仓库["语言"] + ")")
    如果 仓库["描述"] 不等于 ""：
        打印("   " + 仓库["描述"])
```

#### Python 版本

```python
import requests

def get_popular_repos(username, min_stars=100):
    url = f"https://api.github.com/users/{username}/repos"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"请求失败：{e}")
        return []
    
    repos = resp.json()
    
    # 筛选星标超过阈值的仓库
    popular = [r for r in repos if r['stargazers_count'] >= min_stars]
    
    # 按星标数排序（降序）
    popular.sort(key=lambda r: r['stargazers_count'], reverse=True)
    
    # 提取关键信息
    result = []
    for r in popular:
        result.append({
            'name': r['name'],
            'stars': r['stargazers_count'],
            'description': r.get('description', ''),
            'language': r.get('language', 'Unknown'),
            'url': r['html_url']
        })
    
    return result

# 使用
repos = get_popular_repos("skywalk163")
print(f"找到 {len(repos)} 个热门仓库：")
for r in repos:
    print(f"⭐ {r['stars']} - {r['name']} ({r['language']})")
    if r['description']:
        print(f"   {r['description']}")
```

#### 关键差异分析

| 维度 | 段言 | Python | 迁移建议 |
|------|------|--------|---------|
| HTTP 客户端 | 创建 `HTTP客户端` 对象，手动设置请求头 | `requests.get(url, headers=...)` 一步完成 | Python 的 `requests` 库 API 更简洁 |
| 状态码检查 | 显式 `如果 响应.状态码 不等于 200` | `resp.raise_for_status()` 隐式检查 | Python 使用异常机制处理 HTTP 错误 |
| JSON 解析 | `解析JSON(响应.正文)` 显式函数调用 | `resp.json()` 响应对象原生方法 | Python 的响应对象直接提供 JSON 解析 |
| 条件筛选 | 显式 `遍历 + 如果 + 列表追加` | 列表推导式 `[r for r in repos if ...]` | Python 更简洁，但需要适应函数式思维 |
| 空值处理 | 三元表达式 `值 若 条件 否则 默认值` | 字典的 `get()` 方法 `r.get('key', default)` | Python 的 `get()` 方法是处理字典空值的标准方式 |
| 字典键名 | 可用中文键名 | 通常用英文键名 | 在 Python 中也可用中文键名，但建议遵循社区惯例 |

#### 迁移建议

1. **安装第三方库：** Python 的 `requests` 库需要额外安装（`pip install requests`），而段言的 HTTP 客户端是内置模块
2. **异常处理：** Python 使用 `requests.exceptions.RequestException` 捕获所有请求异常，段言使用更通用的 `捕获 错误`
3. **代码量：** Python 版本（约 30 行）比段言版本（约 40 行）更简洁，主要得益于列表推导式和方法链式调用

---

### 6.3 案例三：简单 CLI 工具

**场景：** 创建一个命令行工具，统计指定目录中各类型文件的数量和总大小，支持按扩展名过滤和排序。

#### 段言版本

```段言
从 文件系统 导入 列出目录, 文件存在, 文件信息
从 系统 导入 命令行参数

段落 统计文件 接收 目录路径, 扩展名过滤 = 空：
    如果 非 文件存在(目录路径)：
        打印("目录不存在：" + 目录路径)
        返回 {}
    
    设 文件列表 为 列出目录(目录路径)
    设 统计结果 为 {}
    设 总大小 为 0
    设 总文件数 为 0
    
    遍历 文件名 于 文件列表：
        设 完整路径 为 目录路径 + "/" + 文件名
        设 信息 为 文件信息(完整路径)
        
        如果 信息.是文件 为 假：
            继续
        
        # 提取扩展名
        设 扩展名 为 ""
        设 点位置 为 查找(文件名, ".")
        如果 点位置 大于 0：
            设 扩展名 为 截取(文件名, 点位置, 列表长度(文件名))
        否则：
            设 扩展名 为 "(无扩展名)"
        
        # 如果有过滤条件，跳过不匹配的文件
        如果 扩展名过滤 不等于 空 且 扩展名 不等于 扩展名过滤：
            继续
        
        # 统计
        如果 扩展名 不在 统计结果：
            统计结果[扩展名] 为 {"数量": 0, "大小": 0}
        
        统计结果[扩展名]["数量"] 为 统计结果[扩展名]["数量"] 加 1
        统计结果[扩展名]["大小"] 为 统计结果[扩展名]["大小"] 加 信息.大小
        设 总大小 为 总大小 加 信息.大小
        设 总文件数 为 总文件数 加 1
    
    返回 {"统计": 统计结果, "总大小": 总大小, "总文件数": 总文件数}

段落 主程序：
    设 参数 为 命令行参数()
    设 目录 为 参数[1] 若 列表长度(参数) 大于 1 否则 "."
    设 过滤 为 参数[2] 若 列表长度(参数) 大于 2 否则 空
    
    设 结果 为 统计文件(目录, 过滤)
    
    如果 结果 等于 {}：
        返回
    
    打印("=== 文件统计结果 ===")
    打印("扫描目录：" + 目录)
    打印("总文件数：" + 转字符串(结果["总文件数"]))
    打印("总大小：" + 转字符串(结果["总大小"]) + " 字节")
    打印("")
    打印("按扩展名统计：")
    
    # 排序输出
    设 扩展名列表 为 获取字典键(结果["统计"])
    设 排序后 为 排序(扩展名列表, 倒序 为 假)
    遍历 扩展名 于 排序后：
        设 项 为 结果["统计"][扩展名]
        打印("  " + 扩展名 + ": " + 转字符串(项["数量"]) + " 个文件, " + 转字符串(项["大小"]) + " 字节")

主程序()
```

#### Python 版本

```python
import os
import sys
from pathlib import Path

def count_files(directory, extension_filter=None):
    """统计目录中各类型文件的数量和总大小"""
    if not os.path.exists(directory):
        print(f"目录不存在：{directory}")
        return {}
    
    stats = {}
    total_size = 0
    total_count = 0
    
    for filename in os.listdir(directory):
        full_path = os.path.join(directory, filename)
        
        if not os.path.isfile(full_path):
            continue
        
        # 提取扩展名
        _, ext = os.path.splitext(filename)
        ext = ext if ext else "(无扩展名)"
        
        # 如果有过滤条件，跳过不匹配的文件
        if extension_filter and ext != extension_filter:
            continue
        
        # 获取文件大小
        file_size = os.path.getsize(full_path)
        
        # 统计
        if ext not in stats:
            stats[ext] = {"count": 0, "size": 0}
        
        stats[ext]["count"] += 1
        stats[ext]["size"] += file_size
        total_size += file_size
        total_count += 1
    
    return {"stats": stats, "total_size": total_size, "total_count": total_count}


def main():
    args = sys.argv
    directory = args[1] if len(args) > 1 else "."
    extension_filter = args[2] if len(args) > 2 else None
    
    result = count_files(directory, extension_filter)
    
    if not result:
        return
    
    print("=== 文件统计结果 ===")
    print(f"扫描目录：{directory}")
    print(f"总文件数：{result['total_count']}")
    print(f"总大小：{result['total_size']} 字节")
    print()
    print("按扩展名统计：")
    
    for ext in sorted(result["stats"].keys()):
        item = result["stats"][ext]
        print(f"  {ext}: {item['count']} 个文件, {item['size']} 字节")


if __name__ == "__main__":
    main()
```

#### 关键差异分析

| 维度 | 段言 | Python | 迁移建议 |
|------|------|--------|---------|
| 命令行参数 | `命令行参数()` 直接获取 | `sys.argv` 需要导入 sys 模块 | 两者功能相同，关键字不同 |
| 路径拼接 | 手动 `目录路径 + "/" + 文件名` | `os.path.join(directory, filename)` | Python 的 `os.path.join` 自动处理跨平台分隔符 |
| 文件类型判断 | `信息.是文件` | `os.path.isfile(full_path)` | 语义一致，API 不同 |
| 文件大小获取 | `信息.大小` | `os.path.getsize(full_path)` | 段言通过文件信息对象获取，Python 直接调用函数 |
| 扩展名提取 | 手动查找 `.` 位置 + 截取 | `os.path.splitext(filename)` | Python 的 `os.path.splitext` 更简洁 |
| 入口判断 | 直接调用 `主程序()` | `if __name__ == "__main__":` | Python 需要显式判断模块入口 |

#### 迁移建议

1. **跨平台路径：** Python 的 `os.path.join` 和 `pathlib.Path` 自动处理 Windows/Linux 路径差异，段言需要手动拼接
2. **模块入口：** Python 的 `if __name__ == "__main__":` 是标准实践，段言直接调用函数更简单
3. **路径处理：** Python 推荐使用 `pathlib` 模块（Python 3.4+），它提供了面向对象的路径操作 API

---

## 7. 学习路径建议

### 7.1 已经学会段言 → 如何快速上手 Python

如果你已经掌握了段言，你已经有 80% 的编程基础。建议按以下路径快速上手 Python：

#### 第一阶段：关键字映射（1-2 天）

将段言关键字映射到 Python 关键字：

| 段言 | Python | 记忆技巧 |
|------|--------|---------|
| `段落` | `def` | "define" 的缩写 |
| `如果/否则/否则如果` | `if/else/elif` | "else if" 的缩写 |
| `遍历` | `for` | 遍历所有元素 |
| `当` | `while` | 当条件成立时 |
| `返回` | `return` | 返回结果 |
| `类` | `class` | 类定义 |
| `构造` | `__init__` | 初始化方法 |
| `己` | `self` | 自己 |
| `尝试/捕获/最终` | `try/except/finally` | 异常处理 |
| `抛出` | `raise` | 抛出异常 |
| `从...导入` | `from...import` | 模块导入 |
| `真/假/空` | `True/False/None` | 布尔值/空值 |

#### 第二阶段：核心语法差异（3-5 天）

重点理解以下差异：

1. **列表推导式**：Python 的 `[x for x in list if cond]` 对应段言的 `[x 遍历 x 于 列表 若 条件]`
2. **生成器表达式**：Python 的 `(x for x in list)` 是惰性求值版本
3. **lambda 表达式**：Python 的 `lambda x: x + 1` 对应段言的 `参数 => 表达式`
4. **f-string**：Python 的 `f"值：{x}"` 比段言的 `"值：" + 转字符串(x)` 更简洁
5. **上下文管理器**：Python 的 `with open(...) as f:` 需要理解资源管理概念
6. **装饰器语法**：Python 的 `@decorator` 语法在段言中同样支持

#### 第三阶段：标准库迁移（1 周）

对照第 4 节的「标准库对照表」，逐一练习 Python 标准库的使用：

- 从 `文件系统` 模块 → 学习 `os` 和 `pathlib` 模块
- 从 `CSV` 模块 → 学习 `csv` 模块
- 从 `JSON` 模块 → 学习 `json` 模块
- 从 `HTTP客户端` 模块 → 学习 `requests` 库（第三方）
- 从 `数学` 模块 → 学习 `math` 模块

#### 第四阶段：生态探索（2-4 周）

根据你的兴趣方向，选择以下路径之一深入：

- **数据科学路线：** NumPy → Pandas → Matplotlib → Scikit-learn
- **Web 开发路线：** Flask → FastAPI → Django
- **自动化路线：** BeautifulSoup → Selenium → Playwright
- **AI 路线：** Transformers → LangChain → PyTorch

#### 推荐学习资源

- **官方教程：** [docs.python.org/zh-cn/3/tutorial/](https://docs.python.org/zh-cn/3/tutorial/)（中文版）
- **在线练习：** [leetcode.cn](https://leetcode.cn/)（中文界面）
- **速查手册：** Python 官方文档的「库参考」部分

---

### 7.2 已经会 Python → 如何快速上手段言（逆向使用）

如果你已经掌握了 Python，段言对你来说几乎是零门槛。建议按以下路径快速上手段言：

#### 第一阶段：关键字映射（半天）

将 Python 关键字映射到段言关键字：

| Python | 段言 | 记忆技巧 |
|--------|------|---------|
| `def` | `段落 ... 接收` | 「段落」是函数的自然中文名称 |
| `if/else/elif` | `如果/否则/否则如果` | 直接对应中文条件词 |
| `for` | `遍历 ... 于` | 「遍历」是 for 的中文含义 |
| `while` | `当` | 「当...时」是 while 的自然表达 |
| `return` | `返回` | 语义完全对应 |
| `class` | `类` | 类的中文名称 |
| `__init__` | `构造` | 构造函数 |
| `self` | `己` | 自己的简称 |
| `try/except/finally` | `尝试/捕获/最终` | 语义完全对应 |
| `raise` | `抛出` | 抛出异常 |
| `True/False/None` | `真/假/空` | 中文布尔值 |
| `and/or/not` | `且/或/非` | 中文逻辑词 |

#### 第二阶段：核心语法差异（1 天）

1. **列表推导式**：Python 的 `[x for x in list if cond]` → 段言 `[x 遍历 x 于 列表 若 条件]`
2. **lambda 表达式**：Python 的 `lambda x: x+1` → 段言 `参数 => 表达式`
3. **f-string**：Python 的 `f"值：{x}"` → 段言 `"值：" + 转字符串(x)` 或 `f"值：{x}"`
4. **切片**：Python 的 `list[0:3]` → 段言 `列表[0 到 3]`
5. **三元表达式**：Python 的 `a if cond else b` → 段言 `a 若 cond 否则 b`
6. **文件操作**：Python 的 `open() + with` → 段言 `读取文件(路径)` / `写入文件(路径, 内容)`

#### 第三阶段：段言特色功能（2-3 天）

1. **词句段篇层级**：理解段言如何将自然语言结构映射到代码
2. **元数驱动**：理解段言解析器如何利用动词元数判断语句结构
3. **三级类型检查**：从「签名级」到「表达式级」的渐进式类型检查
4. **上下文继承**：段言的段落自动继承父作用域上下文
5. **双后端**：开发阶段使用 SRC 后端（Python 解释执行），生产阶段使用 LLVM 原生编译

#### 第四阶段：段言标准库（1 周）

对照第 4 节的「标准库对照表」，熟悉段言的中文标准库 API：

- 所有函数名和参数名都是中文
- API 设计更粗粒度（一个函数封装多个步骤）
- 60+ 模块覆盖常见场景

#### 特别提示

- **段言兼容英文写法**：`打印` 和 `print` 等价，`如果` 和 `if` 等价，可以混合使用
- **Python 桥接**：段言可以直接导入 Python 库，`从 numpy 导入 数组` 这样的写法在你的 Python 知识下可以直接使用
- **C FFI**：段言的 C FFI 比 Python 的 `ctypes` 更简洁，如果你有 C 互操作需求，段言是更好的选择

---

## 附录：段言 ↔ Python 快速转换卡

### 常见代码模式转换

| 模式 | 段言 | Python |
|------|------|--------|
| Hello World | `打印 "你好"` | `print("你好")` |
| 变量赋值 | `设 x 为 10` | `x = 10` |
| 条件判断 | `如果 x > 0：` | `if x > 0:` |
| 循环遍历 | `遍历 i 于 列表：` | `for i in 列表:` |
| 函数定义 | `段落 函数 接收 p：` | `def 函数(p):` |
| 类定义 | `类 名称：` | `class 名称:` |
| 异常处理 | `尝试：... 捕获 e：` | `try:... except e:` |
| 文件读取 | `读取文件(路径)` | `open(路径).read()` |
| 列表推导 | `[x 遍历 x 于 L 若 条件]` | `[x for x in L if 条件]` |
| 字典访问 | `字典["键"]` | `字典["键"]` |
| 排序 | `排序(列表, 倒序 为 真)` | `sorted(列表, reverse=True)` |
| 模块导入 | `从 模块 导入 函数` | `from 模块 import 函数` |
| 异步函数 | `异步 段落 函数 接收 p：` | `async def 函数(p):` |
| 模式匹配 | `匹配 值：情况 模式：` | `match 值：case 模式：` |
| 三元表达式 | `a 若 条件 否则 b` | `a if 条件 else b` |
| 字符串拼接 | `"a" + "b"` | `"a" + "b"`（或 f-string） |
| 列表追加 | `列表追加(列表, 元素)` | `列表.append(元素)` |
| 获取长度 | `列表长度(列表)` | `len(列表)` |
| 类型注解 | `参数: 整数` | `参数: int` |
| 空值判断 | `值 等于 空` | `值 is None` |

---

> **项目地址：** [https://github.com/skywalk163/duan](https://github.com/skywalk163/duan)  
> **文档索引：** [docs/index.md](index.md)  
> **许可证：** MIT