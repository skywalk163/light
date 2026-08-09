# 光明编程语言 - 示例

本目录包含光明（Light）编程语言的示例代码，按学习路径和后端兼容性分类。

---

## 学习示例（按难度排序）

| 文件 | 难度 | 演示内容 | 后端 |
|------|------|----------|------|
| [hello.light](hello.light) | ⭐ | 基础输出 | ANTLR |
| [basic.light](basic.light) | ⭐ | 变量、算术、条件、函数、递归、循环 | SRC |
| [advanced.light](advanced.light) | ⭐⭐ | 列表、斐波那契、高阶函数、条件嵌套 | SRC |
| [class_example.light](class_example.light) | ⭐⭐ | 类定义、属性、构造、方法 | SRC |
| [calculator.light](calculator.light) | ⭐⭐⭐ | 类、方法、条件判断 | SRC |
| [module_demo.light](module_demo.light) | ⭐⭐⭐ | 模块函数、列表操作 | SRC |
| [student_management.light](student_management.light) | ⭐⭐⭐ | 类、列表、循环、多对象管理 | SRC |
| [hanoi.light](hanoi.light) | ⭐⭐⭐ | 汉诺塔递归算法 | SRC |

## 测试/参考示例

这些文件主要用于后端开发和回归测试，更复杂的程序供参考：

| 文件 | 说明 | 语法版本 |
|------|------|----------|
| [test_fib.light](test_fib.light) | 斐波那契数列 · 递归 | 旧式 |
| [test_fib_src.light](test_fib_src.light) | 同上（src 后端） | 旧式 |
| [test_bubble.light](test_bubble.light) | 冒泡排序 · 数组操作 | 旧式 |
| [test_hello.light](test_hello.light) | Hello + 函数求和 | 旧式 |
| [test_hello_src.light](test_hello_src.light) | 同上（src 后端） | 旧式 |
| [test_para.light](test_para.light) | 无括号隐式函数调用 | 旧式 |
| [test_stdio.light](test_stdio.light) | I/O 输入输出测试 | 旧式 |
| [test_turing.light](test_turing.light) | **图灵机模拟**（最复杂的示例） | 旧式 |

---

## 语法说明

### 新旧语法对照

光明目前存在两种语法风格：

```光明
# ── 旧式语法（《段名》段模式，兼容 SRC 后端）──
《求和》段(甲, 乙)：
  返回 甲 加 乙。
结束。

# ── 新式语法（段落 段名 接收 模式，ANTLR 规范）──
段落 求和 接收 甲, 乙：
  返回 甲 加 乙。
结束。
```

### 核心差异

| 方面 | 旧式 | 新式 |
|------|------|------|
| 段落声明 | `《段名》段(参数)` | `段落 段名 接收 参数` |
| 函数调用 | `《求和》(三, 五)` | `求和(3, 5)` |
| 类声明 | `《学生》类:` | `类 学生：` |
| 条件语句 | `如果 条件 那么 动作。` / `如果 条件 那么：` | `如果 条件：` |
| 条件否则 | `否则 动作。` / `否则：` | `否则：` |
| 循环 | `当 条件：` / `当条件：` | `当 条件：` |
| 结束 | `结束。`（句号可选） | `结束。` |
| 数字 | 中文数字作变量名 (`三`) | 仅 ASCII 数字 (`3`) |
| 注释 | `# 注释` | `# 注释` |

### 兼容性

- **hello.light** 兼容两种后端
- **class_example.light** 使用新式 ANTLR 语法（SRC 后端同样支持）
- 其余示例使用旧式《段名》段语法，SRC 后端均可正常运行
- 旧式格式在 ANTLR 后端中可能报错（如 `那么`、`参数` 等关键字差异）
- 所有 16 个示例均至少在一个后端上通过测试

---

## 运行方式

### 前提条件

```bash
# 安装依赖
pip install antlr4-tools antlr4-python3-runtime
```

### 使用 ANTLR 解释器（推荐）

```bash
# 进入项目根目录
cd g:\dumategithub\light

# 运行 Hello World
python -c "
from antlrparser.light_interpreter import run_source
run_source(open('examples/hello.light', encoding='utf-8').read())
"

# 运行汉诺塔
python -c "
from antlrparser.light_interpreter import run_source
run_source(open('examples/hanoi.light', encoding='utf-8').read())
"
```

### 使用 CLI 工具运行

```bash
# 使用 SRC 后端（推荐，兼容所有示例）
python cli/light.py run examples/basic.light --backend src
python cli/light.py run examples/advanced.light --backend src
python cli/light.py run examples/test_turing.light --backend src

# 使用 ANTLR 后端（仅兼容 hello.light）
python cli/light.py run examples/hello.light --backend antlr
python cli/light.py run examples/class_example.light --backend antlr
```

> **提示**：hello.light 两种后端均可运行；其余旧式语法示例建议使用 `--backend src`。

### 使用 REPL

```bash
# 启动交互式环境
python cli/light_repl.py

# 在 REPL 中：
光明> 打印("你好，世界！")。
光明> 设 甲 为 42。
光明> 打印(甲)。
```

---

## 示例详解

### 1. Hello World — [hello.light](hello.light)

最简单的光明程序：

```光明
打印("你好，世界！")。
```

### 2. 基础语法 — [basic.light](basic.light)

演示变量声明、算术运算、条件语句、函数定义、递归（阶乘）、while 循环。

关键语法：
```光明
# 变量声明
定义甲等于123。

# 函数定义（旧式）
《加法》段(甲, 乙)：
  返回甲加乙。
结束。

# 函数调用（旧式）
定义和等于《加法》(三, 五)。

# 递归
《阶乘》段(数)：
  如果数小于等于一那么返回一。
  返回数乘《阶乘》(数减一)。
结束。

# While 循环
定义计数等于一。
当 计数 小于等于 五：
  打印(计数)。
  定义计数等于计数加一。
结束。
```

### 3. 高级功能 — [advanced.light](advanced.light)

演示列表字面量、斐波那契数列、高阶函数（函数作为参数）、多级条件判断。

```光明
# 列表字面量
定义列表等于[1, 2, 3, 4, 5]。

# 斐波那契数列（递归）
《斐波那契》段(数)：
  如果数小于等于二那么返回一。
  返回《斐波那契》(数减一)加《斐波那契》(数减二)。
结束。

# 高阶函数：函数作为参数
《计算器》段(操作符, 甲, 乙)：
  如果操作符等于"加"那么返回甲加乙。
  如果操作符等于"乘"那么返回甲乘乙。
结束。

打印("函数参数：")。
打印(《计算器》("加", 三, 五))。
打印(《计算器》("乘", 三, 五))。
```

### 4. 类定义 — [class_example.light](class_example.light)

示范新式 ANTLR 类语法：

```光明
类 学生：
  属性 姓名
  属性 年龄
  
  构造(姓名, 年龄)：
    定义己姓名等于姓名。
    定义己年龄等于年龄。
  
  介绍：
    打印"我叫"加己姓名加"，今年"加己年龄加"岁。"。

# 使用类
定义学生等于创建学生参数"张三"，20。
学生.介绍。
```

### 5. 计算器 — [calculator.light](calculator.light)

演示旧式类语法、方法定义、条件判断：

```光明
《计算器》类:
    定义 结果 等于 0。
    
    《加》方法(x):
        结果 等于 结果 加 x。
    
    《除》方法(x):
        如果 x 不等于 0 那么:
            结果 等于 结果 除 x。
        否则:
            打印("错误: 除数不能为零")。

定义 计算器1 等于 新建 计算器()。
计算器1之加(10)。
计算器1之乘(2)。
```

### 6. 学生管理系统 — [student_management.light](student_management.light)

使用旧式类语法实现完整的学生管理，包含列表操作、循环遍历：

```光明
《学生》类:
    定义 成绩 等于 []。
    
    《添加成绩》方法(分数):
        列表追加(成绩, 分数)。
    
    《平均成绩》方法():
        定义 总分 等于 0。
        定义 i 等于 0。
        当 i 小于 列表长度(成绩):
            总分 等于 总分 加 成绩[i]。
            i 等于 i 加 1。
        返回 总分 除 列表长度(成绩)。

定义 学生1 等于 新建 学生("张三", 18)。
学生1之添加成绩(85)。
```

### 7. 汉诺塔 — [hanoi.light](hanoi.light)

经典递归算法演示：

```光明
《汉诺塔》段(层数, 源柱, 目标柱, 辅助柱):
  如果 层数 等于 一 那么:
    打印("移动盘子 1 从 " + 源柱 + " 到 " + 目标柱)。
  否则:
    汉诺塔(层数 减 一, 源柱, 辅助柱, 目标柱)。
    打印("移动盘子 " + 转字符串(层数) + " 从 " + 源柱 + " 到 " + 目标柱)。
    汉诺塔(层数 减 一, 辅助柱, 目标柱, 源柱)。
  结束。
结束。
```

### 8. 图灵机模拟 — [test_turing.light](test_turing.light)

最复杂的示例，用光明实现二进制加一器。演示字典操作、状态机、循环控制：

```光明
设纸带为 ["1", "0", "1", "1", " "]。
设指针为零。

# 状态转移表
设状态表为 字典()。
字典设置(状态表, "S0 0", ["S1", "1", "0"])。
字典设置(状态表, "S0 1", ["S0", "0", "-1"])。

# 执行
当 当前状态 不等于 "停机"：
  如果 字典包含键(状态表, 键) 那么：
    设转移为 字典获取(状态表, 键)。
```

### 使用批量测试脚本

```bash
# 运行所有示例的自动测试
python examples/test_all_examples.py
```

---

## 测试结果

所有 16 个示例通过批量测试（`test_all_examples.py`）：

| 后端 | 通过数 | 失败数 |
|------|--------|--------|
| ANTLR | 1 (hello.light) | 0 |
| SRC   | 15 | 0 |
| **总计** | **16** | **0** |

> 旧式语法示例主要兼容 SRC 后端；hello.light 使用最简语法，兼容两种后端。
> 批量测试脚本会自动尝试 ANTLR 后端，失败后回退到 SRC 后端。

---

## 注意事项

1. **后端选择**：旧式语法示例（basic, advanced, calculator 等）在 ANTLR 后端可能报 `参数` 非关键字错误，请使用 `--backend src`
2. **中文数字**：旧式示例中使用 `三`、`五` 等中文数字作为标识符或变量名，**不是数字字面量**；新语法只支持 ASCII 数字
3. **文件编码**：所有 `.light` 文件使用 **UTF-8** 编码
4. **语句结束**：新规范要求语句以 `。` 结尾；旧式示例中 `结束` 可能不带句号

---

## 编写新示例

推荐使用新式 ANTLR 规范语法：

```光明
# 新示例模板
段落 函数名 接收 参数1, 参数2：
  设 结果 为 参数1 加 参数2。
  返回 结果。
结束。

打印(函数名(3, 5))。
```

将文件保存为 `.light`，用 ANTLR 后端运行：

```bash
python cli/light.py run examples/你的文件.light --backend antlr
```