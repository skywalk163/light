# HTTP客户端 API

> 模块路径：`stdlib/HTTP客户端.py`
> 导入方式：`从 HTTP客户端 导入 函数名` 或 `导入 HTTP客户端`

---

## 函数列表

| 函数 | 说明 |
|------|------|
| `HTTP获取(url, headers, timeout)` | HTTP GET 请求，返回 HTTPResponse |
| `HTTP提交(url, body, headers, timeout, content_type)` | HTTP POST 请求，返回 HTTPResponse |
| `HTTP更新(url, body, headers, timeout, content_type)` | HTTP PUT 请求，返回 HTTPResponse |
| `HTTP删除(url, headers, timeout)` | HTTP DELETE 请求，返回 HTTPResponse |
| `HTTP修补(url, body, headers, timeout, content_type)` | HTTP PATCH 请求，返回 HTTPResponse |
| `HTTP头部(url, headers, timeout)` | HTTP HEAD 请求，返回 HTTPResponse |
| `获取JSON(url, headers, timeout)` | GET 请求并解析 JSON 响应，返回 dict/list |
| `发送JSON(url, data, method, headers, timeout)` | 发送 JSON 数据并返回 HTTPResponse |
| `下载文件(url, 文件路径, headers, timeout)` | 下载文件到指定路径，返回 True/False |
| `URL编码(字符串)` | URL 编码 |
| `URL解码(字符串)` | URL 解码 |
| `拼接URL(base_url, params)` | 拼接 URL 和查询参数 |
| `_build_request(method, url, body, headers)` | 构建 urllib Request 对象 |
| `_do_request(method, url, body, headers, timeout)` | 执行 HTTP 请求，返回 HTTPResponse |
| `__init__(self, method, url, headers, body, query, follow_redirect, timeout)` |  |
| `__init__(self, status, status_msg, headers, body, final_url, cookies)` |  |

---

## 函数详情

### `HTTP获取(url, headers = None, timeout = 30)`

HTTP GET 请求，返回 HTTPResponse

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |
| `headers` | `None` | （默认：None） |
| `timeout` | `None` | （默认：30） |

---

### `HTTP提交(url, body = None, headers = None, timeout = 30, content_type = 'application/json')`

HTTP POST 请求，返回 HTTPResponse

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |
| `body` | `None` | （默认：None） |
| `headers` | `None` | （默认：None） |
| `timeout` | `None` | （默认：30） |
| `content_type` | `None` | （默认：'application/json'） |

---

### `HTTP更新(url, body = None, headers = None, timeout = 30, content_type = 'application/json')`

HTTP PUT 请求，返回 HTTPResponse

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |
| `body` | `None` | （默认：None） |
| `headers` | `None` | （默认：None） |
| `timeout` | `None` | （默认：30） |
| `content_type` | `None` | （默认：'application/json'） |

---

### `HTTP删除(url, headers = None, timeout = 30)`

HTTP DELETE 请求，返回 HTTPResponse

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |
| `headers` | `None` | （默认：None） |
| `timeout` | `None` | （默认：30） |

---

### `HTTP修补(url, body = None, headers = None, timeout = 30, content_type = 'application/json')`

HTTP PATCH 请求，返回 HTTPResponse

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |
| `body` | `None` | （默认：None） |
| `headers` | `None` | （默认：None） |
| `timeout` | `None` | （默认：30） |
| `content_type` | `None` | （默认：'application/json'） |

---

### `HTTP头部(url, headers = None, timeout = 30)`

HTTP HEAD 请求，返回 HTTPResponse

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |
| `headers` | `None` | （默认：None） |
| `timeout` | `None` | （默认：30） |

---

### `获取JSON(url, headers = None, timeout = 30)`

GET 请求并解析 JSON 响应，返回 dict/list

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |
| `headers` | `None` | （默认：None） |
| `timeout` | `None` | （默认：30） |

---

### `发送JSON(url, data, method = 'POST', headers = None, timeout = 30)`

发送 JSON 数据并返回 HTTPResponse

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |
| `data` | `None` |  |
| `method` | `None` | （默认：'POST'） |
| `headers` | `None` | （默认：None） |
| `timeout` | `None` | （默认：30） |

---

### `下载文件(url, 文件路径, headers = None, timeout = 300)`

下载文件到指定路径，返回 True/False

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |
| `文件路径` | `None` |  |
| `headers` | `None` | （默认：None） |
| `timeout` | `None` | （默认：300） |

---

### `URL编码(字符串)`

URL 编码

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `字符串` | `None` |  |

---

### `URL解码(字符串)`

URL 解码

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `字符串` | `None` |  |

---

### `拼接URL(base_url, params = None)`

拼接 URL 和查询参数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `base_url` | `None` |  |
| `params` | `None` | （默认：None） |

---

### `_build_request(method, url, body = None, headers = None)`

构建 urllib Request 对象

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `method` | `None` |  |
| `url` | `None` |  |
| `body` | `None` | （默认：None） |
| `headers` | `None` | （默认：None） |

---

### `_do_request(method, url, body = None, headers = None, timeout = 30)`

执行 HTTP 请求，返回 HTTPResponse

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `method` | `None` |  |
| `url` | `None` |  |
| `body` | `None` | （默认：None） |
| `headers` | `None` | （默认：None） |
| `timeout` | `None` | （默认：30） |

---

### `__init__(self, method = 'GET', url = '', headers = None, body = None, query = None, follow_redirect = True, timeout = 30)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `method` | `None` | （默认：'GET'） |
| `url` | `None` | （默认：''） |
| `headers` | `None` | （默认：None） |
| `body` | `None` | （默认：None） |
| `query` | `None` | （默认：None） |
| `follow_redirect` | `None` | （默认：True） |
| `timeout` | `None` | （默认：30） |

---

### `__init__(self, status = 0, status_msg = '', headers = None, body = '', final_url = '', cookies = None)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `status` | `None` | （默认：0） |
| `status_msg` | `None` | （默认：''） |
| `headers` | `None` | （默认：None） |
| `body` | `None` | （默认：''） |
| `final_url` | `None` | （默认：''） |
| `cookies` | `None` | （默认：None） |

---

## 常量

| 常量名 | 值 |
|--------|-----|
| `resp` | `HTTP获取(url, headers=headers, timeout=timeout)` |
| `body` | `_json.dumps(data, ensure_ascii=False)` |
| `query_str` | `urllib.parse.urlencode(params)` |
| `separator` | `'&' if '?' in base_url else '?'` |
| `headers` | `{}` |
| `headers` | `{}` |
| `headers` | `{}` |
| `headers` | `{}` |
| `req` | `_build_request('GET', url, headers=headers)` |
| `ctx` | `_ssl.create_default_context()` |
| `headers` | `{}` |
| `body` | `body.encode('utf-8')` |
| `req` | `_build_request(method, url, body=body, headers=headers)` |
| `ctx` | `_ssl.create_default_context()` |
| `resp_body` | `resp.read()` |
| `resp_headers` | `dict(resp.headers)` |
| `resp_body` | `''` |
| `resp_body` | `e.read().decode('utf-8')` |
| `chunk` | `resp.read(8192)` |
| `resp_body` | `resp_body.decode('utf-8')` |
| `resp_body` | `resp_body.decode('latin-1')` |
