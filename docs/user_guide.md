# 光明（LightLang）用户手册

**版本**: v6.0.0  
**日期**: 2026-10-29

---

## 一、快速入门

### 1.1 什么是光明？

光明（LightLang）是一门中文编程语言，核心设计理念是**像中文一样分层**。它借鉴中文"字→文体→领域→外语"的分层智慧，构建了从教学到商业的全场景覆盖语言体系。

### 1.2 你好，光明！

创建一个 `hello.light` 文件：

```python
印("你好，光明！")
```

运行：

```bash
light hello.light
```

### 1.3 五层架构概览

| 层级 | 名称 | 说明 |
|------|------|------|
| **L0** | 核心字集 | 30 个单字关键字，永远不变 |
| **L1** | 白话体 | 双字关键字，中文标点，适合教学 |
| **L2** | 文言体 | 单字关键字，英文标点，适合商业项目 |
| **L3** | 领域嵌入 | SQL/正则/数学公式直接嵌入光明代码 |
| **L4** | 外语引用 | 用 `引` 块引用 Python/C/Go/MoonBit 代码 |

---

## 二、安装

### 2.1 前提条件

- Python 3.10 或更高版本（推荐 Python 3.12）
- pip 包管理器

### 2.2 安装方式

**方式一：通过 PyPI 安装**

```bash
pip install light
```

**方式二：从源码安装**

```bash
git clone https://github.com/light-lang/light.git
cd light
pip install -e .
```

**方式三：使用独立可执行文件**

下载 `light7.exe`（Windows）或对应平台的可执行文件，无需 Python 环境即可运行。

### 2.3 验证安装

```bash
light --version
# 输出：光明 LightLang v6.0.0
```

---

## 三、基本用法

### 3.1 运行光明程序

```bash
# 直接运行
light 程序.light

# 生成 Python 代码但不执行
light 程序.light --emit-python

# 编译为可执行文件
light 程序.light --native
```

### 3.2 变量与类型

```python
# 基本变量定义
设 甲 为 10
设 乙 为 "hello"

# 类型注解（v5.1+）
设 丙 为 整数 = 20
设 丁 为 文本 = "world"

# 复合类型
设 列表 为 列表[整数] = [1, 2, 3]
设 映射 为 字典[文本, 整数] = {"a": 1}
```

### 3.3 条件判断

```python
若 甲 > 乙：
  印("甲更大")
否则 若 甲 == 乙：
  印("相等")
否则：
  印("乙更大")
```

### 3.4 循环

```python
# 遍循环（for-in）
遍 i 于 列(1, 2, 3, 4, 5)：
  印(i)

# 当循环（while）
设 计数 为 3
当 计数 > 0：
  印(计数)
  计数 = 计数 - 1
```

### 3.5 函数定义

```python
段 平方(x)：
  返回 x * x

# 带类型注解
段 加法(a: 整数, b: 整数) -> 整数：
  返回 a + b

印(平方(5))
```

### 3.6 类定义

```python
类 人：
  性 姓名
  性 年龄

  构(姓名, 年龄)：
    己.姓名 = 姓名
    己.年龄 = 年龄

  段 介绍()：
    印("我叫" + 己.姓名 + "，今年" + 己.年龄 + "岁")

设 张三 = 新 人("张三", 18)
张三.介绍()
```

### 3.7 异常处理

```python
尝试：
  设 结果 = 10 / 0
捕获 零除错误：
  印("不能除以零！")
最终：
  印("执行清理")
```

---

## 四、高级用法

### 4.1 泛型与联合类型

```python
# 泛型函数
段 首元素[T](列表: 列表[T]) -> T：
  返回 列表[0]

# 联合类型
段 处理(值: 整数 | 文本 | 空)：
  若 值 是 整数：
    印("整数")
  否则 若 值 是 文本：
    印("文本")
  否则：
    印("空")
```

### 4.2 模式匹配

```python
配 值：
  若 1:
    印("一")
  若 2:
    印("二")
  若 _:
    印("其他")
```

### 4.3 领域嵌入（L3）

```python
# SQL 嵌入
引 SQL:
  SELECT * FROM users WHERE age > 18

# 正则表达式
引 正则:
  ^\d{3}-\d{8}$

# 数学公式
引 数学:
  E = mc^2
```

### 4.4 外语引用（L4）

```python
# 引用 Python
引 Python:
  import numpy as np
  def 矩阵乘法(a, b):
    return np.dot(a, b)
出 矩阵乘法

# 引用 C 语言
引 C:
  int add(int a, int b) {
    return a + b;
  }
出 add
```

### 4.5 类型检查

```python
# 开启运行时类型检查
开启类型检查

# 类型不匹配时会抛出 TypeError
设 值 为 整数 = "文本"  # 错误！

# 关闭类型检查（恢复零开销）
关闭类型检查
```

---

## 五、工具链

### 5.1 CLI 命令行

```bash
# 查看帮助
light --help

# 编译运行
light 文件.light [参数...]

# 仅编译
light 文件.light --compile

# 编译为 C 代码
light 文件.light --c

# 编译为 LLVM IR
light 文件.light --llvm

# 编译为 WebAssembly
light 文件.light --wasm

# 生成可执行文件
light 文件.light --native

# 调试模式
light 文件.light --debug

# 性能分析
light 文件.light --profile
```

### 5.2 REPL 交互式环境

```bash
# 启动 REPL
light repl

# 在 REPL 中
>>> 印("你好，光明！")
你好，光明！
>>> 设 x 为 10
>>> x + 20
30
```

### 5.3 LSP 语言服务器

光明提供 LSP 语言服务器，支持：

- 代码自动补全
- 悬停类型提示
- 跳转到定义
- 代码格式化
- 错误诊断

在 VS Code 中安装光明扩展即可自动启用。

### 5.4 调试器

```bash
# 启动调试
light debug 文件.light

# 调试命令
- 断点设置/取消
- 单步执行
- 变量查看
- 调用栈追踪
```

### 5.5 代码格式化器

```bash
# 格式化文件
light fmt 文件.light

# 检查格式
light fmt --check 文件.light
```

### 5.6 代码检查器

```bash
# 运行 lint
light lint 文件.light

# 自动修复
light lint --fix 文件.light
```

### 5.7 包管理器

```bash
# 安装包
light install 包名

# 发布包
light publish

# 搜索包
light search 关键词

# 安装本地包
light install ./本地包路径
```

### 5.8 在线 Playground

访问 [https://light-lang.github.io/playground](https://light-lang.github.io/playground) 在线体验：

- 编写和运行光明代码
- 交互式教程（6 章 20 课）
- WebAssembly 执行模式
- 示例库浏览

### 5.9 VS Code 扩展

安装光明 VS Code 扩展后：

- L0-L4 完整语法高亮
- 代码片段（snippets）
- 调试适配器集成（断点/单步/变量查看）
- LSP 语言服务（自动补全/悬停提示/跳转定义）
- 编译/运行命令集成
- 编辑器标题栏运行按钮
- 右键菜单集成
- 状态栏文体模式显示

---

## 六、文体切换

光明支持两种文体风格，可在项目中混用：

### L1 白话体

```python
如果 x > 0：
  打印("正数")
否则：
  打印("非正数")
```

### L2 文言体

```python
若 x > 0:
  印("正数")
否则:
  印("非正数")
```

---

## 七、常见问题（FAQ）

### Q1: 光明和 Python 有什么关系？

光明编译器使用 Python 实现，编译后的代码生成 Python 字节码或 LLVM IR。光明代码可以直接调用 Python 库（通过 L4 引用层）。

### Q2: 光明的性能如何？

光明通过 LLVM 后端可以生成原生机器码，性能接近 C 语言。在 Python 后端模式下，性能与等效 Python 代码相当。

### Q3: 如何学习光明？

- 阅读本用户手册
- 参考 `docs/` 目录下的语言参考文档
- 浏览 `examples/` 目录的示例代码
- 使用在线 Playground 的交互式教程

### Q4: 光明支持哪些平台？

Windows、Linux、macOS 全平台支持。通过 CI 自动化测试验证。

### Q5: 光明与 Python 版本兼容性？

光明编译器需要 Python 3.10+。生成的代码兼容 Python 3.8+。

### Q6: 如何贡献代码？

请参考 `docs/contributing.md` 贡献指南。

### Q7: 光明有包管理机制吗？

有。光明提供内置的包管理器 `lightpkg`，支持本地安装和远程注册表发布/安装。

### Q8: 光明支持 WebAssembly 吗？

支持。通过 `--wasm` 选项可以将光明代码编译为 WebAssembly，在浏览器中运行。

### Q9: 如何报告 Bug？

请在 GitHub 仓库提交 Issue，包含完整的错误信息和复现步骤。

### Q10: 光明的开源协议是什么？

光明采用开源协议发布，详见项目根目录的 LICENSE 文件。