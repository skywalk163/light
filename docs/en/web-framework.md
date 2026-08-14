# Web Framework

> **Version:** v6.0
> **Last updated:** 2026-08-07

Duan provides a powerful web development framework through the `HTTP服务端` (HTTP Server) standard library and the `Web框架` duanpub package. You can build web applications using Chinese keywords and natural syntax.

---

## Quick Start: Hello World Web Server

Create a simple HTTP server:

```段言
导入 HTTP服务端

段落 主页 接收 请求：
    返回 HTML响应("

# Hello, Duan Web!
")

HTTP服务端.路由("GET", "/", 主页)
HTTP服务端.启动("0.0.0.0", 8080)
打印("Server running at http://localhost:8080")
```

Run it:

```bash
duan run server.duan
```

## Key Components

### HTTP Server (`HTTP服务端`)

The HTTP server module provides:

| Function | Description |
|----------|-------------|
| `路由(方法, 路径, 处理函数)` | Register a route |
| `启动(主机, 端口)` | Start the server |
| `静态文件(目录)` | Serve static files |
| `请求(方法, URL, 参数)` | Make HTTP requests |

### Response Types

```段言
# HTML response
返回 HTML响应("<h1>Hello</h1>")

# JSON response
返回 JSON响应({"消息": "Hello"})

# Text response
返回 文本响应("Hello World")

# File response
返回 文件响应("path/to/file.pdf")

# Redirect
返回 重定向响应("/new-path")
```

## Building a Blog System

### Project Structure

```
blog_app/
├── package.toml
├── 主.duan          # Entry point
├── 路由.duan        # Route configuration
├── 模型.duan        # Data models
└── 页面.duan        # Page rendering
```

### Data Model (`模型.duan`)

```段言
类 博客：
    属性 标题, 内容, 作者, 时间, 标签

    构造 接收 标题, 内容, 作者, 标签 = []：
        己.标题 为 标题
        己.内容 为 内容
        己.作者 为 作者
        己.时间 为 当前时间()
        己.标签 为 标签

    段落 摘要 接收 字数 = 50：
        返回 己.内容[:字数] + "..."

导出 博客
```

### Route Configuration (`路由.duan`)

```段言
导入 HTTP服务端
导入 模型

段落 列表页 接收 请求：
    设 文章列表 为 读取文章列表()
    返回 HTML响应(渲染列表(文章列表))

段落 详情页 接收 请求, 文章ID：
    设 文章 为 获取文章(文章ID)
    如果 文章 是 空：
        返回 文本响应("404 Not Found", 404)
    返回 HTML响应(渲染详情(文章))

段落 发布页 接收 请求：
    如果 请求.方法 == "POST"：
        设 数据 为 请求.表单数据
        设 新文章 为 模型.博客(数据["标题"], 数据["内容"], 数据["作者"])
        保存文章(新文章)
        返回 重定向响应("/")
    返回 HTML响应(渲染表单())

# Register routes
HTTP服务端.路由("GET", "/", 列表页)
HTTP服务端.路由("GET", "/文章/{id}", 详情页)
HTTP服务端.路由("GET", "/发布", 发布页)
HTTP服务端.路由("POST", "/发布", 发布页)

导出 路由
```

### Entry Point (`主.duan`)

```段言
导入 HTTP服务端
导入 路由

# Configure static files
HTTP服务端.静态文件("静态")

# Start server
打印("博客系统启动于 http://localhost:8080")
HTTP服务端.启动("0.0.0.0", 8080)
```

## Middleware Support

Duan supports middleware for common web tasks:

```段言
# CORS middleware
使用 CORS中间件()：
    HTTP服务端.路由("GET", "/api", API处理)

# Logging middleware
使用 日志中间件()：
    HTTP服务端.路由("GET", "/", 主页)

# Rate limiting
使用 速率限制中间件(100, 60)：  # 100 requests per 60 seconds
    HTTP服务端.路由("POST", "/发布", 发布处理)
```

## RESTful API Development

Create a JSON API for your blog:

```段言
导入 HTTP服务端
导入 JSON

# GET /api/posts - List all posts
段落 获取文章列表 接收 请求：
    设 文章 为 读取所有文章()
    返回 JSON响应(文章)

# GET /api/posts/:id - Get single post
段落 获取文章详情 接收 请求, id：
    设 文章 为 获取文章(id)
    如果 文章 是 空：
        返回 JSON响应({"错误": "文章不存在"}, 404)
    返回 JSON响应(文章)

# POST /api/posts - Create post
段落 创建文章 接收 请求：
    设 数据 为 JSON.解析(请求.正文)
    设 新文章 为 保存文章(数据)
    返回 JSON响应(新文章, 201)

# Register API routes
HTTP服务端.路由("GET", "/api/posts", 获取文章列表)
HTTP服务端.路由("GET", "/api/posts/{id}", 获取文章详情)
HTTP服务端.路由("POST", "/api/posts", 创建文章)
```

## Session Management

```段言
# Start a session
设 会话 为 创建会话(请求)

# Store session data
会话["用户"] = "张三"

# Retrieve session data
设 用户 为 会话["用户"]

# Clear session
会话.清除()
```

## Static File Serving

```段言
# Serve static files from a directory
HTTP服务端.静态文件("public", "/static")

# Now files in public/ are accessible at /static/filename
# e.g., public/style.css → /static/style.css
```

## Deployment

### Running in Production

```bash
# Run with production settings
duan pkg -p blog_app run

# Native compilation with LLVM
duan pkg -p blog_app native -o blog_server.exe
./blog_server.exe
```

### Environment Configuration

```段言
导入 环境变量

设 端口 为 环境变量.获取("PORT", "8080")
设 主机 为 环境变量.获取("HOST", "0.0.0.0")

HTTP服务端.启动(主机, 转整数(端口))
```

## Complete Example

See the [blog tutorial](../blog/用段言构建Web应用.md) for a complete walkthrough of building a blog system with Duan's web framework.

## Related Resources

- 📖 [HTTP Server API](../api/HTTP服务端.md) — HTTP server module reference
- 📦 [Web Framework Package](../duanpub/Web框架.md) — duanpub web framework
- 🎬 [Video Tutorial](../video_scripts/段言Web开发实战.md) — 10-minute web development tutorial
- 📝 [Blog Tutorial](../blog/用段言构建Web应用.md) — Complete blog system tutorial