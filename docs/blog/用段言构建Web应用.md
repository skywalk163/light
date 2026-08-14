# 用段言构建 Web 应用——从零到一的实战指南

> **发布日期：** 2026-08-07
> **适用版本：** v6.0.0
> **作者：** 段言开发团队

---

## 引言

Web 开发是最常见的编程需求之一。无论你是想搭建个人博客、企业内部工具，还是 SaaS 产品，Web 技术都是不可或缺的。

段言 v6.0 提供了强大的 Web 开发能力——通过 `HTTP服务端` 标准库和 `Web框架` duanpub 包，你可以用中文自然语言快速构建 Web 应用。

在本教程中，我们将从零开始，用段言构建一个完整的**博客系统**。这个系统将包含：

- 文章列表首页（按时间倒序排列）
- 文章详情页
- 发布新文章功能
- 标签分类
- 数据持久化（JSON 文件存储）

## 准备工作

### 安装段言 v6.0

确保已安装段言 v6.0：

```bash
pip install duan --upgrade
duan --version
# 输出：Duan v6.0.0
```

### 创建项目

```bash
mkdir 段言博客
cd 段言博客
```

## 第一步：Hello World 版 Web 服务器

先从一个最简单的 Web 服务器开始，确保环境正常。

创建 `服务器.duan`：

```段言
导入 HTTP服务端。

段落 处理请求 接收 请求, 响应：
    响应.设置HTML("
        <html>
        <body>
            <h1>你好，段言！</h1>
            <p>这是我的第一个段言 Web 应用</p>
        </body>
        </html>
    ")

设 服务器 为 创建HTTP服务端("127.0.0.1", 8080)
服务器.注册路由("/", 处理请求, "GET")
打印("服务器启动在 http://127.0.0.1:8080")
服务器.启动(真)
```

运行：

```bash
duan run 服务器.duan
```

打开浏览器访问 `http://127.0.0.1:8080`，你应该能看到页面上显示"你好，段言！"。

**架构说明**：段言的 `HTTP服务端` 模块基于 Python 的 `http.server` 封装，提供了简洁的路由注册和请求/响应处理接口。`处理请求` 段落接收两个参数——`请求` 对象（包含请求方法、路径、表单数据等）和 `响应` 对象（用于设置状态码、响应头和响应体）。

## 第二步：设计数据模型

博客系统需要存储文章数据。我们使用 JSON 文件作为持久化存储，方便查看和调试。

创建 `数据层.duan`：

```段言
导入 文件系统。
导入 JSON。

设 数据文件 为 "posts.json"

段落 加载文章列表：
    如果 文件存在(数据文件)：
        设 内容 为 读取文件(数据文件)
        设 数据 为 解析JSON(内容)
        返回 数据
    否则：
        返回 []

段落 保存文章列表 接收 列表：
    设 数据 为 序列化JSON(列表, 2)
    写入文件(数据文件, 数据)

段落 生成文章ID 接收 列表：
    设 最大ID 为 0
    遍历 文章 于 列表：
        如果 文章["id"] 大于 最大ID：
            最大ID 为 文章["id"]
    返回 最大ID + 1
```

**关键点**：
- `加载文章列表()` 检查文件是否存在，不存在则返回空列表
- `保存文章列表()` 将数据序列化为格式化 JSON 写入文件
- `生成文章ID()` 自动递增 ID，避免 ID 冲突

## 第三步：设计 HTML 模板

段言使用字符串模板来渲染 HTML。我们将模板定义为常量，通过 `替换字符串` 函数注入动态数据。

创建 `模板.duan`：

```段言
设 页面模板 为 "<!DOCTYPE html>
<html lang='zh-CN'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>{标题}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; background: #f0f2f5; color: #333; }
    .container { max-width: 860px; margin: 0 auto; padding: 20px; }
    header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 0; text-align: center; margin-bottom: 30px; }
    header h1 { font-size: 32px; }
    header h1 a { color: white; text-decoration: none; }
    .post { background: white; border-radius: 10px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .post h2 { color: #333; margin-bottom: 10px; }
    .post h2 a { color: #333; text-decoration: none; }
    .post .meta { color: #999; font-size: 13px; margin-bottom: 12px; }
    .post .content { line-height: 1.9; color: #555; }
    .btn { display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 10px 24px; border-radius: 6px; text-decoration: none; }
    .btn:hover { opacity: 0.9; }
    form { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    form label { display: block; margin-bottom: 6px; font-weight: bold; color: #555; }
    form input, form textarea { width: 100%; padding: 12px; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 6px; }
    form textarea { height: 300px; resize: vertical; }
    .nav { text-align: center; margin: 24px 0; }
    .footer { text-align: center; color: #aaa; padding: 30px; }
  </style>
</head>
<body>
  <header>
    <div class='container'>
      <a href='/'><h1>段言博客</h1></a>
      <p>用段言编程语言构建的博客系统</p>
    </div>
  </header>
  <div class='container'>
    {内容}
    <div class='footer'>
      <p>段言博客 - 基于段言 v6.0 构建</p>
    </div>
  </div>
</body>
</html>"

设 首页模板 为 "<div class='nav'><a href='/new' class='btn'>✏ 写新文章</a></div>
{文章列表}"

设 文章卡片模板 为 "<div class='post'>
  <h2><a href='/post/{id}'>{标题}</a></h2>
  <div class='meta'>📅 {时间} &nbsp;|&nbsp; 🏷 {标签}</div>
  <div class='content'>{摘要}...</div>
  <div style='margin-top:16px;'><a href='/post/{id}' class='btn'>阅读全文</a></div>
</div>"

设 文章详情模板 为 "<div class='post'>
  <h2>{标题}</h2>
  <div class='meta'>📅 {时间} &nbsp;|&nbsp; 🏷 {标签}</div>
  <div class='content'>{正文}</div>
  <div class='nav'>
    <a href='/' class='btn'>返回首页</a>
    <a href='/new' class='btn'>写新文章</a>
  </div>
</div>"

设 新建文章模板 为 "<h2 style='margin-bottom:24px;'>✏ 写新文章</h2>
<form method='POST' action='/new'>
  <label>文章标题</label>
  <input type='text' name='title' placeholder='请输入文章标题' required>

  <label>标签（用逗号分隔）</label>
  <input type='text' name='tags' placeholder='例如: 段言, 教程, 编程'>

  <label>文章内容</label>
  <textarea name='content' placeholder='请输入文章内容...' required></textarea>

  <button type='submit' class='btn'>发布文章</button>
  <a href='/' class='btn' style='background:#6c757d;'>取消</a>
</form>"

设 模板404 为 "<div class='post' style='text-align:center;'>
  <h2 style='font-size:48px;color:#ddd;'>404</h2>
  <p style='color:#999;'>您请求的页面不存在。</p>
  <div class='nav'><a href='/' class='btn'>返回首页</a></div>
</div>"
```

**设计思路**：模板使用 `{变量名}` 占位符，后续通过 `替换字符串` 函数注入实际数据。这种模板方案简单直接，无需额外依赖，适合小型应用。

## 第四步：实现路由处理

现在来实现核心的路由逻辑。创建 `路由.duan`：

```段言
导入 数据层。
导入 模板。

段落 渲染页面 接收 标题, 内容：
    设 页面 为 模板.页面模板
    页面 为 替换字符串(页面, "{标题}", 标题)
    页面 为 替换字符串(页面, "{内容}", 内容)
    返回 页面

段落 替换模板 接收 模板, 变量名, 值：
    返回 替换字符串(模板, "{" + 变量名 + "}", 值)

段落 获取当前时间字符串：
    返回 时间戳()

段落 处理首页 接收 请求, 响应：
    设 文章列表 为 数据层.加载文章列表()

    如果 列表长度(文章列表) 等于 0：
        设 空状态 为 "<div class='empty-state' style='text-align:center;padding:60px 20px;color:#999;'>
            <p>📝 还没有任何文章</p>
            <a href='/new' class='btn'>发布第一篇文章</a>
        </div>"
        设 首页内容 为 替换模板(模板.首页模板, "文章列表", 空状态)
        设 HTML 为 渲染页面("段言博客 - 首页", 首页内容)
        响应.设置HTML(HTML)
        返回

    # 按时间倒序排列（后添加的在前面）
    设 序号 为 列表长度(文章列表) - 1
    设 文章卡片列表 为 ""

    当 序号 大于等于 0：
        设 文章 为 文章列表[序号]
        设 卡片 为 模板.文章卡片模板
        卡片 为 替换模板(卡片, "id", 转字符串(文章["id"]))
        卡片 为 替换模板(卡片, "标题", 文章["title"])
        卡片 为 替换模板(卡片, "时间", 文章["created_at"])

        设 标签文本 为 字典获取(文章, "tags", "未分类")
        卡片 为 替换模板(卡片, "标签", 标签文本)

        设 摘要 为 文章["content"]
        如果 字符串长度(摘要) 大于 120：
            摘要 为 字符串获取(摘要, 0, 120)
        卡片 为 替换模板(卡片, "摘要", 摘要)
        文章卡片列表 为 文章卡片列表 + 卡片
        序号 为 序号 - 1

    设 首页内容 为 替换模板(模板.首页模板, "文章列表", 文章卡片列表)
    设 HTML 为 渲染页面("段言博客 - 首页", 首页内容)
    响应.设置HTML(HTML)

段落 处理文章详情 接收 请求, 响应, 文章编号：
    设 文章列表 为 数据层.加载文章列表()
    设 找到 为 假

    遍历 文章 于 文章列表：
        如果 文章["id"] 等于 文章编号：
            找到 为 真
            设 文章内容 为 模板.文章详情模板
            文章内容 为 替换模板(文章内容, "标题", 文章["title"])
            文章内容 为 替换模板(文章内容, "时间", 文章["created_at"])
            文章内容 为 替换模板(文章内容, "标签", 字典获取(文章, "tags", "未分类"))

            设 正文 为 替换字符串(文章["content"], "\n", "<br>")
            文章内容 为 替换模板(文章内容, "正文", 正文)
            设 HTML 为 渲染页面(文章["title"] + " - 段言博客", 文章内容)
            响应.设置HTML(HTML)
            跳出

    如果 找到 等于 假：
        设 HTML 为 渲染页面("404 - 页面未找到", 模板.模板404)
        响应.设置状态码(404)
        响应.设置HTML(HTML)

段落 处理新建页面 接收 请求, 响应：
    设 HTML 为 渲染页面("写新文章 - 段言博客", 模板.新建文章模板)
    响应.设置HTML(HTML)

段落 处理创建文章 接收 请求, 响应：
    设 文章列表 为 数据层.加载文章列表()
    设 表单 为 请求.获取表单数据()

    设 标题 为 字典获取(表单, "title", "无标题")
    设 内容 为 字典获取(表单, "content", "")
    设 标签 为 字典获取(表单, "tags", "")

    设 新文章 为 {
        "id": 数据层.生成文章ID(文章列表),
        "title": 标题,
        "content": 内容,
        "tags": 标签,
        "created_at": 获取当前时间字符串()
    }
    列表追加(文章列表, 新文章)
    数据层.保存文章列表(文章列表)

    打印("新文章发布: " + 标题)
    响应.重定向("/")

段落 解析文章ID 接收 路径：
    设 部分 为 分割字符串(路径, "/")
    如果 列表长度(部分) 大于等于 3：
        返回 转整数(部分[2])
    返回 0

段落 处理请求 接收 请求, 响应：
    设 路径 为 请求.获取路径()
    设 方法 为 请求.获取方法()

    如果 路径 等于 "/" 且 方法 等于 "GET"：
        处理首页(请求, 响应)
    否则若 路径 等于 "/new" 且 方法 等于 "GET"：
        处理新建页面(请求, 响应)
    否则若 路径 等于 "/new" 且 方法 等于 "POST"：
        处理创建文章(请求, 响应)
    否则若 开头(路径, "/post/") 且 方法 等于 "GET"：
        设 文章编号 为 解析文章ID(路径)
        处理文章详情(请求, 响应, 文章编号)
    否则：
        响应.设置状态码(404)
        设 HTML 为 渲染页面("404 - 页面未找到", 模板.模板404)
        响应.设置HTML(HTML)
```

**路由设计说明**：

段言的路由系统采用 `路径 + 请求方法` 匹配模式。`处理请求` 是统一入口，根据路径和方法分发到不同处理函数：

- `GET /` → 首页，展示文章列表
- `GET /new` → 新建文章页面（表单）
- `POST /new` → 处理文章创建
- `GET /post/{id}` → 文章详情页
- 其他路径 → 404 页面

注意这里使用了 `模块化` 设计，将数据层、模板、路由拆分为不同文件，通过 `导入` 关键字引用。这是段言推荐的项目组织方式。

## 第五步：组装主程序

最后，创建 `主.duan` 作为入口：

```段言
导入 路由。
导入 HTTP服务端。

段落 主程序：
    打印("======================================")
    打印("  段言博客系统 v1.0")
    打印("======================================")
    打印("  服务器地址: http://127.0.0.1:8080")
    打印("  数据存储: posts.json")
    打印("======================================")

    设 服务器 为 创建HTTP服务端("127.0.0.1", 8080)
    服务器.注册路由("/", 路由.处理请求, "GET")
    服务器.注册路由("/new", 路由.处理请求, "GET")
    服务器.注册路由("/new", 路由.处理请求, "POST")
    服务器.注册路由("/post/{id}", 路由.处理请求, "GET")

    打印("博客系统启动在 http://127.0.0.1:8080")
    打印("按 Ctrl+C 停止服务器")
    服务器.启动(真)

主程序()
```

## 第六步：运行和测试

### 启动服务器

```bash
duan run 主.duan
```

你应该看到以下输出：

```
======================================
  段言博客系统 v1.0
======================================
  服务器地址: http://127.0.0.1:8080
  数据存储: posts.json
======================================
博客系统启动在 http://127.0.0.1:8080
按 Ctrl+C 停止服务器
```

### 功能测试

1. **首页**：访问 `http://127.0.0.1:8080`，显示空状态页面，提示"还没有任何文章"
2. **发布文章**：点击"写新文章"，填写标题、标签和内容，点击"发布文章"
3. **查看文章**：发布后自动跳转首页，显示文章卡片
4. **文章详情**：点击"阅读全文"进入文章详情页
5. **404 页面**：访问不存在的路径，显示 404 页面

### 运行截图

启动后，你应该能看到类似这样的页面：

```
┌──────────────────────────────────────────────┐
│          段言博客                             │
│   用段言编程语言构建的博客系统                │
├──────────────────────────────────────────────┤
│                                              │
│  [✏ 写新文章]                               │
│                                              │
│  ┌──────────────────────────────────────────┐│
│  │ 段言 v6.0 正式发布！                     ││
│  │ 📅 2026-08-07  |  🏷 段言, 发布, v6.0   ││
│  │ 我们很高兴地宣布段言 v6.0 正式发布...    ││
│  │ [阅读全文]                               ││
│  └──────────────────────────────────────────┘│
│                                              │
│  ┌──────────────────────────────────────────┐│
│  │ 用段言构建 Web 应用                      ││
│  │ 📅 2026-08-07  |  🏷 教程, Web           ││
│  │ 从零开始，用段言构建一个完整的博客...    ││
│  │ [阅读全文]                               ││
│  └──────────────────────────────────────────┘│
│                                              │
│  段言博客 - 基于段言 v6.0 构建              │
└──────────────────────────────────────────────┘
```

## 进阶：使用 Web 框架

如果你需要更复杂的 Web 功能（中间件、Session、文件上传等），可以使用 duanpub 的 `Web框架` 包：

```bash
duan pkg install Web框架
```

```段言
导入 段言博客框架。

设 应用 为 创建应用()

# 添加中间件
应用.使用(日志中间件())
应用.使用(CORS中间件())

# 定义路由
应用.路由("GET", "/api/posts", 段落 接收 请求, 响应：
    设 文章列表 为 加载文章列表()
    响应.JSON(文章列表)
)

应用.路由("POST", "/api/posts", 段落 接收 请求, 响应：
    设 数据 为 请求.获取JSON数据()
    设 新文章 为 创建文章(数据)
    响应.JSON(新文章, 201)
)

应用.启动("127.0.0.1", 8080)
```

## 完整项目结构

最终的项目结构如下：

```
段言博客/
├── 主.duan          # 入口文件，启动服务器
├── 数据层.duan      # 数据存储层，JSON 文件读写
├── 模板.duan        # HTML 模板定义
├── 路由.duan        # 请求路由和处理逻辑
└── posts.json       # 自动生成的文章数据
```

## 总结

通过这个教程，我们从零开始用段言构建了一个完整的博客系统。你学到了：

1. **HTTP 服务端**：使用 `HTTP服务端` 模块创建 Web 服务器
2. **路由系统**：通过 `注册路由` 注册不同路径的处理函数
3. **请求处理**：解析请求路径、方法和表单数据
4. **响应生成**：设置 HTML 响应、状态码和重定向
5. **模板渲染**：使用字符串模板加变量替换渲染页面
6. **数据持久化**：使用 JSON 文件存储和读取数据
7. **模块化**：将代码拆分为多个文件，通过 `导入` 组织

段言的 Web 开发能力虽然年轻，但已经足够支撑中小型 Web 应用的开发需求。随着 v6.0 的发布和社区生态的完善，我们期待看到更多基于段言的 Web 应用涌现。

---

> 项目地址：[https://github.com/skywalk163/duan](https://github.com/skywalk163/duan)
> 示例代码：[examples/blog_system/](https://github.com/skywalk163/duan/tree/main/examples/blog_system)
> 许可证：MIT