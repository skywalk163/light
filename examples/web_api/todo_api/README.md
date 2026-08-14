# 待办事项 RESTful API

使用段言编程语言和内置 Web 框架实现的 RESTful API 服务，提供完整的待办事项 CRUD 操作，支持 JSON 数据格式和 CORS 跨域访问。

## 功能

- 获取所有待办事项（`GET /api/todos`）
- 获取单个待办事项（`GET /api/todos/:id`）
- 创建新待办事项（`POST /api/todos`）
- 更新待办事项（`PUT /api/todos/:id`）
- 删除待办事项（`DELETE /api/todos/:id`）
- 健康检查端点（`GET /api/health`）
- JSON 文件持久化存储
- CORS 跨域支持
- 输入验证和错误处理

## 用法

```bash
# 启动 API 服务器
duan run examples/web_api/todo_api/主.duan
```

服务器启动后，可以使用 `curl`、`Postman` 或浏览器访问 API。

### API 示例

```bash
# 获取所有待办事项
curl http://127.0.0.1:3000/api/todos

# 创建新待办事项
curl -X POST http://127.0.0.1:3000/api/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "学习段言编程", "completed": false}'

# 获取单个待办事项
curl http://127.0.0.1:3000/api/todos/1

# 更新待办事项
curl -X PUT http://127.0.0.1:3000/api/todos/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "学习段言编程", "completed": true}'

# 删除待办事项
curl -X DELETE http://127.0.0.1:3000/api/todos/1

# 健康检查
curl http://127.0.0.1:3000/api/health
```

## API 文档

### 获取所有待办事项

```
GET /api/todos
```

响应示例：
```json
[
  {
    "id": 1,
    "title": "学习段言编程",
    "completed": false,
    "created_at": "2024-01-01 12:00:00",
    "updated_at": "2024-01-01 12:00:00"
  }
]
```

### 创建待办事项

```
POST /api/todos
Content-Type: application/json

{
  "title": "新待办事项",
  "completed": false
}
```

### 更新待办事项

```
PUT /api/todos/:id
Content-Type: application/json

{
  "title": "更新后的标题",
  "completed": true
}
```

### 删除待办事项

```
DELETE /api/todos/:id
```

## 涉及的语言特性

- `段落` 函数定义与参数传递
- `设` 变量声明
- `如果`/`否则若`/`否则` 条件判断
- `遍历` 列表遍历循环
- `当` 条件循环
- `尝试`/`捕获` 异常处理
- `导入` 标准库模块（文件系统、JSON）
- 字典和列表操作
- JSON 解析与序列化
- 文件读写（持久化存储）
- `创建HTTP服务端` 创建 Web 服务器
- `服务器.注册路由()` 路由注册
- HTTP 请求/响应处理