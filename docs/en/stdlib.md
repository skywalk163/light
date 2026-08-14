# Standard Library

> **Version:** v6.0
> **Last updated:** 2026-08-07

Duan provides a rich standard library with **60+ modules** organized in **13 phases**, located in the `stdlib/` directory. Each module has both Python (`.py`) and Duan (`.duan`) implementations.

---

## Phase 1: Core Modules

### builtins
Built-in functions providing basic operations:
- `打印(值)` — Print value to console
- `长度(集合)` — Get length of a collection
- `转字符串(值)` — Convert to string
- `类型(值)` — Get type of a value
- `范围(开始, 结束)` — Create a range

### 数学 (Math)
Mathematical functions:
- `绝对值(x)` — Absolute value
- `正弦(x)` / `余弦(x)` / `正切(x)` — Trigonometric functions
- `指数(x)` — Exponential
- `对数(x)` — Natural logarithm
- `阶乘(n)` — Factorial
- `平方根(x)` — Square root
- `平均数(列表)` — Mean average
- `最大值(列表)` / `最小值(列表)` — Max/Min

### 字符串处理 (String Processing)
String operations:
- `分割(字符串, 分隔符)` — Split string
- `拼接(列表)` — Join string list
- `替换(字符串, 旧, 新)` — Replace substring
- `查找(字符串, 子串)` — Find substring position
- `截取(字符串, 开始, 结束)` — Slice string

### 文件系统 (File System)
File and directory operations:
- `读取(路径)` — Read file content
- `写入(路径, 内容)` — Write to file
- `追加(路径, 内容)` — Append to file
- `存在(路径)` — Check if path exists
- `创建目录(路径)` — Create directory
- `列出目录(路径)` — List directory contents

### 日志 (Logging)
Logging utilities:
- `记录(消息)` — Log a message
- `调试(消息)` — Debug level
- `信息(消息)` — Info level
- `警告(消息)` — Warning level
- `错误(消息)` — Error level

### JSON
JSON parsing and serialization:
- `解析(字符串)` — Parse JSON string
- `序列化(对象)` — Serialize to JSON string

## Phase 2: Data Structures & Tools

### 日期时间 (Date & Time)
Date/time handling:
- `解析(字符串, 格式)` — Parse date string
- `格式化(日期, 格式)` — Format date
- `当前时间()` — Get current timestamp
- `时间戳转日期(时间戳)` — Convert timestamp to date

### 随机数 (Random)
Random number generation:
- `整数(最小值, 最大值)` — Random integer
- `浮点数()` — Random float
- `选择(列表)` — Random choice
- `打乱(列表)` — Shuffle list
- `UUID()` — Generate UUID

### 集合 (Set)
Set operations:
- `并集(集合1, 集合2)` — Union
- `交集(集合1, 集合2)` — Intersection
- `差集(集合1, 集合2)` — Difference
- `对称差集(集合1, 集合2)` — Symmetric difference

### 数据结构 (Data Structures)
Common data structures:
- `栈()` — Stack
- `队列()` — Queue
- `二叉搜索树()` — Binary search tree

## Phase 3: System & Network

### 网络请求 (HTTP Requests)
HTTP client:
- `GET(URL)` — GET request
- `POST(URL, 数据)` — POST request
- `请求(URL, 方法, 数据)` — Generic request

### 进程 (Process)
Process management:
- `启动进程(命令, 参数)` — Start a process
- `等待进程(进程)` — Wait for process completion

### 线程 (Thread)
Thread management:
- `创建线程(函数, 参数)` — Create thread
- `互斥锁()` — Mutex lock
- `信号量(初始值)` — Semaphore

### 时间管理 (Time Management)
Time utilities:
- `计时器(间隔, 函数)` — Timer
- `休眠(秒)` — Sleep

## Phase 4: Encoding & Security

### 编码解码 (Encoding)
Encoding conversion:
- `Base64编码(字符串)` — Base64 encode
- `Base64解码(字符串)` — Base64 decode
- `URL编码(字符串)` — URL encode
- `URL解码(字符串)` — URL decode

### 加密 (Encryption)
Encryption tools:
- `AES加密(数据, 密钥)` — AES encrypt
- `AES解密(数据, 密钥)` — AES decrypt
- `RSA加密(数据, 公钥)` — RSA encrypt
- `RSA解密(数据, 私钥)` — RSA decrypt

### 哈希 (Hash)
Hash functions:
- `MD5(字符串)` — MD5 hash
- `SHA256(字符串)` — SHA256 hash
- `SHA512(字符串)` — SHA512 hash

## Phase 5: Advanced Features

### 装饰器 (Decorators)
Decorator utilities (11 types):
- `缓存装饰器` — Cache function results
- `重试装饰器(次数)` — Auto-retry
- `计时装饰器` — Execution timing
- `日志装饰器` — Logging
- `类型检查装饰器` — Parameter type checking

### 上下文管理器 (Context Managers)
Context managers (13 types):
- `临时文件()` — Temporary file
- `临时目录()` — Temporary directory
- `更改目录(路径)` — Change directory temporarily
- `设置环境变量(变量, 值)` — Set env var temporarily

## Phase 6: Data Science & Computing

### 统计函数 (Statistics)
Statistical calculations:
- `平均数(列表)` — Mean
- `中位数(列表)` — Median
- `标准差(列表)` — Standard deviation
- `协方差(列表1, 列表2)` — Covariance
- `相关系数(列表1, 列表2)` — Correlation coefficient

### 矩阵运算 (Matrix Operations)
Matrix operations:
- `矩阵(列表)` — Create matrix
- `矩阵加法(矩阵1, 矩阵2)` — Matrix addition
- `矩阵乘法(矩阵1, 矩阵2)` — Matrix multiplication
- `行列式(矩阵)` — Determinant

### 线性代数 (Linear Algebra)
Linear algebra tools:
- `向量(列表)` — Create vector
- `向量点积(向量1, 向量2)` — Dot product
- `向量叉积(向量1, 向量2)` — Cross product

## Phase 7: Text Processing & Parsing

### 正则表达式 (Regular Expressions)
Regex operations:
- `匹配(模式, 字符串)` — Match
- `搜索(模式, 字符串)` — Search
- `替换(模式, 替换, 字符串)` — Replace
- `分割(模式, 字符串)` — Split
- `查找所有(模式, 字符串)` — Find all

### 模板引擎 (Template Engine)
Template rendering:
- `简单模板(模板字符串)` — Create template
- `渲染(变量)` — Render template

### CSV读写器 (CSV Reader/Writer)
CSV file operations:
- `读取CSV(路径)` — Read CSV
- `写入CSV(路径, 数据)` — Write CSV

## Phase 8: Web & Communication

### HTTP客户端 (HTTP Client)
HTTP client library:
- `请求(URL, 方法, 参数, 头信息)` — HTTP request
- `GET(URL, 参数, 头信息)` — GET request
- `POST(URL, 数据, 头信息)` — POST request
- `会话()` — Persistent session

### HTTP服务端 (HTTP Server)
HTTP server:
- `路由(路径, 方法, 处理函数)` — Route registration
- `启动(主机, 端口)` — Start server
- `静态文件(目录)` — Static file serving

### WebSocket支持 (WebSocket)
WebSocket support:
- `WebSocket客户端(URL)` — Client
- `WebSocket服务端(主机, 端口)` — Server
- `发送(消息)` — Send message
- `接收()` — Receive message

### SMTP邮件 (SMTP Email)
Email sending:
- `SMTP客户端(服务器, 端口)` — Create client
- `登录(用户名, 密码)` — Login
- `发送邮件(发件人, 收件人, 主题, 内容)` — Send email

## Phase 9: Testing & Debugging

### 单元测试框架 (Unit Testing)
Test framework:
- `测试用例()` — Test case class
- `断言相等(实际, 预期)` — Assert equal
- `断言为真(表达式)` — Assert true
- `测试套件()` — Test suite
- `运行测试()` — Run tests

### 性能基准测试 (Performance Benchmarking)
Performance testing:
- `计时(函数, 参数)` — Time execution
- `内存测量(函数, 参数)` — Memory measurement
- `基准测试(函数, 次数)` — Benchmark

## Phase 10: Metaprogramming

### AST操作 (AST Operations)
AST processing:
- `解析代码(代码)` — Parse code to AST
- `生成代码(节点)` — Generate code from AST
- `遍历AST(节点, 访问者)` — Traverse AST

### 插件系统 (Plugin System)
Plugin management:
- `插件管理器()` — Plugin manager
- `加载插件(路径)` — Load plugin
- `获取插件(名称)` — Get plugin
- `卸载插件(名称)` — Uninstall plugin

## Phase 11: Security & Authentication

### OAuth_JWT认证 (Authentication)
Authentication tools:
- `密码工具.哈希密码(密码)` — Hash password
- `密码工具.验证密码(密码, 哈希)` — Verify password
- `JWT令牌(密钥, 过期时间)` — JWT token
- `生成令牌(载荷)` — Generate token
- `验证令牌(令牌)` — Verify token

### 访问控制 (Access Control)
Permission management:
- `RBAC系统()` — RBAC system
- `添加角色(名称)` — Add role
- `添加权限(名称)` — Add permission
- `授予权限(角色, 权限)` — Grant permission
- `检查权限(用户, 权限)` — Check permission

## Phase 12: Concurrency & Distributed

### Actor模型 (Actor Model)
Concurrent programming:
- `Actor系统(名称)` — Create actor system
- `创建Actor(类, 名称)` — Create actor
- `Actor引用.发送(消息)` — Send message
- `Actor引用.请求(消息, 超时)` — Request-reply

### 消息队列 (Message Queue)
Message queuing:
- `内存消息队列(名称)` — In-memory queue
- `发送(内容, 优先级, 延迟)` — Send message
- `接收(超时)` — Receive message
- `发布订阅()` — Pub/sub pattern

### 任务队列调度器 (Task Queue Scheduler)
Task scheduling:
- `任务队列(线程数)` — Task queue
- `提交(函数, 参数)` — Submit task
- `定时调度器()` — Scheduled scheduler
- `添加间隔任务(间隔, 函数)` — Interval task

## Phase 13: System Utilities

### 系统接口 (System Interface)
System interfaces:
- `获取环境变量(名称, 默认值)` — Get env var
- `设置环境变量(名称, 值)` — Set env var
- `获取命令行参数()` — Get CLI args
- `退出(状态码)` — Exit program
- `进程ID()` — Get process ID
- `当前工作目录()` — Get CWD
- `操作系统()` — Get OS name
- `CPU核心数()` — CPU core count

### 外部命令 (External Commands)
External command execution:
- `执行命令(命令, 捕获输出, 超时)` — Execute command
- `管道执行(命令列表)` — Pipeline execution
- `命令存在(命令名)` — Check if command exists

### 参数解析 (Argument Parsing)
CLI argument parsing:
- `参数解析器(程序名, 描述)` — Create parser
- `解析器.添加参数(名称, 短名称, 类型, 默认值, 描述)` — Add argument
- `解析器.解析(参数列表)` — Parse arguments
- `解析器.显示帮助()` — Show help

## Usage Example

```段言
# Import modules
导入 数学
导入 文件系统

# Use functions
设 结果 为 数学.阶乘(10)
打印 结果  # Output: 3628800

# Import specific functions
从 字符串处理 导入 分割
设 列表 为 分割("a,b,c", ",")
打印 列表  # Output: ["a", "b", "c"]
```

## Standard Library Structure

```
stdlib/
├── builtins.py              # Built-in functions
├── 数学.py / 数学.duan       # Math utilities
├── 字符串处理.py / .duan     # String processing
├── 文件系统.py / .duan       # File system
├── JSON.py / .duan           # JSON handling
├── ...                       # 60+ modules
└── __init__.py               # Package init
```