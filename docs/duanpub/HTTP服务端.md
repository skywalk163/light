# HTTP服务端

> 轻量HTTP服务器，路由、中间件、静态文件

## 包信息

| 属性 | 值 |
|------|-----|
| 版本 | 1.0.0 |
| 分类 | 网络通信 |
| 优先级 | 🔹 扩展包 |
| 公开函数 | 14 |
| FFI 声明 | 16 |

**关键词:** HTTP, 服务端, 路由, 中间件, 静态文件

**依赖包:** [Socket](Socket.md), [URL解析](URL解析.md)

## 导入方式

```duan
导入 HTTP服务端
```

或

```duan
导入 标准HTTP服务端
```

## 函数列表

共 14 个公开函数

> HTTP服务端 — duanpub 桥接模块
> 
> 基于 Python http.server 模块封装，提供中文名 API 用于创建 HTTP 服务端。
> 
> duanpub 原始包通过 C FFI 实现 HTTP 服务器，本桥接模块用 Python http.server 替代，
> 提供等价的 HTTP 服务端功能。函数签名与 duanpub 包保持一致。
> 
> 支持功能：
> - 路由注册（GET/POST/PUT/DELETE/PATCH）
> - 路径参数提取（如 /users/{id}）
> - 静态文件服务
> - CORS 中间件
> - 访问日志中间件
> - JSON/HTML/文本/文件响应
> - Cookie 设置
> - 重定向

### 创建HTTPServer(host,port):

*暂无详细文档*

### add_route(server,method,path,handler):

*暂无详细文档*

### add_static(server,url_prefix,dir_path):

*暂无详细文档*

### start_server(server):

*暂无详细文档*

### stop_server(server):

*暂无详细文档*

### response_write_text(response,status_code,text,content_type):

*暂无详细文档*

### response_write_json(response,status_code,json_str):

*暂无详细文档*

### response_write_html(response,status_code,html):

*暂无详细文档*

### response_write_file(response,file_path):

*暂无详细文档*

### response_redirect(response,location,status_code):

*暂无详细文档*

### response_set_header(response,name,value):

*暂无详细文档*

### response_set_cookie(response,cookie):

*暂无详细文档*

### responseNotFound(response):

*暂无详细文档*

### responseInternalError(response,err_msg):

*暂无详细文档*
