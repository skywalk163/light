# 快速开始

> **适用版本：** v6.0
> **最后更新：** 2026-08-07

## 安装

### 从 PyPI 安装（推荐）

```bash
pip install light
```

安装后即可使用 `light` 命令：
```bash
light --version
light --help
```

### 从源码安装

```bash
git clone https://github.com/skywalk163/light.git
cd light
pip install -e .
```

## 3 步跑起来

### 第1步：创建程序

创建文件 `hello.light`：

```光明
打印 "你好，光明！"
```

### 第2步：运行

```bash
light run hello.light
```

### 第3步：验证

```
你好，光明！
```

看到输出就说明安装成功！

## v6.0 语法示例

### 变量声明

```光明
设 姓名 为 "张三"
设 年龄 为 25
设 分数 为 95.5
设 列表 为 [1, 2, 3, 4, 5]
设 字典 为 {"名字": "张三", "年龄": 25}
```

### 段落（函数）

```光明
段落 加法 接收 甲, 乙：
    返回 甲 + 乙

设 结果 为 加法(3, 5)
打印 结果  # 输出：8
```

### 条件判断

```光明
设 分数 为 85

如果 分数 >= 90：
    打印 "优秀"
否则如果 分数 >= 60：
    打印 "及格"
否则：
    打印 "不及格"
```

### 循环

```光明
# 遍历范围
遍历 i 在 1 到 5：
    打印 i

# 遍历列表
设 水果 为 ["苹果", "香蕉", "橘子"]
遍历 水果 为 果：
    打印 果

# 当循环
设 计数 为 0
当 计数 < 5：
    打印 计数
    设 计数 为 计数 + 1
```

### 类与对象

```光明
类 动物：
    属性 名字

    构造 接收 名字：
        己.名字 为 名字

    段落 介绍 接收：
        打印(f"我叫{己.名字}")

设 小狗 为 动物("旺财")
小狗.介绍()
```

### 异常处理

```光明
尝试：
    设 结果 为 10 / 0
捕获 错误：
    打印("出错了：" + 转字符串(错误))
最终：
    打印("操作结束")
```

### 模块导入

```光明
导入 数学

设 结果 为 数学.平方根(16)
打印 结果  # 输出：4.0

# 从模块导入特定函数
从 数学 导入 阶乘
打印 阶乘(5)  # 输出：120
```

### 模式匹配

```光明
匹配 值：
    情况 1：
        打印("一")
    情况 2：
        打印("二")
    其他：
        打印("其他")
```

### 异步编程

```光明
异步 段落 获取数据 接收 url：
    返回 等待 请求(url)

# 异步入口也必须是一个 异步 段落
异步 段落 主流程()：
    设 数据 为 等待 获取数据("https://api.example.com")
    打印 数据
```

## CLI 命令

### 常用命令

```bash
light run hello.light         # 解释执行
light compile hello.light     # 编译为 Python
light ast hello.light         # 显示 AST
light tokens hello.light      # 显示 Token 流
light check hello.light       # 语法检查
light repl                   # 交互式编程环境
light tutorial               # 交互式教程
```

### 包管理命令

```bash
light pkg init myproject     # 初始化新项目
light pkg -p myproject build # 编译项目
light pkg -p myproject run   # 运行项目
light pkg -p myproject native -o output.exe  # LLVM 原生编译
```

### AI 辅助命令

```bash
light ai generate "写一个冒泡排序"  # AI 生成代码
light ai fix hello.light "第3行语法错误"  # 修复代码
light ai card  # 查看语法速查卡
light ai check hello.light  # 后端兼容性检测
```

### 后端选择

```bash
# SRC 后端（默认，无需额外依赖）
light run hello.light

# ANTLR 后端（兼容旧语法）
light run hello.light --backend antlr

# LLVM 后端（原生编译）
light compile hello.light --backend llvm-typed -o hello.exe
```

## 示例程序

项目包含多个示例程序：

```bash
# 运行示例
light run examples/hello.light
light run examples/basic.light
light run examples/class_example.light
```

示例列表：
- `examples/hello.light` - Hello World
- `examples/basic.light` - 基础语法
- `examples/class_example.light` - 类示例
- `examples/hanoi.light` - 汉诺塔算法
- `examples/calculator.light` - 计算器
- `examples/student_management.light` - 学生管理系统

## 更多资源

- 📖 [30 分钟入门光明](30分钟入门光明.md) — 零基础入门教程
- 📚 [语法规范](syntax.md) — 完整语法参考
- 🛠️ [工具链](tools.md) — CLI、LSP、调试器、AI Copilot
- 📦 [包管理器使用指南](包管理器使用指南.md) — lightpub 包管理
- 🌐 [API 文档](api/index.md) — 标准库参考
- 📋 [项目路线图](ROADMAP.md) — 版本规划与愿景