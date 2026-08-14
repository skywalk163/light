# URL解析 API

> 模块路径：`stdlib/URL解析.py`
> 导入方式：`从 URL解析 导入 函数名` 或 `导入 URL解析`

---

## 函数列表

| 函数 | 说明 |
|------|------|
| `解析URL(url)` | 解析 URL 字符串，返回 ParsedURL 对象。 |
| `构建URL(scheme, hostname, port, path, params, query, fragment, username, password)` | 构建 URL 字符串 |
| `编码查询参数(params, doseq)` | 将字典编码为查询参数字符串 |
| `解析查询参数(query_string, keep_blank_values)` | 解析查询参数字符串为字典 |
| `URL拼接(base)` | 拼接 URL 路径 |
| `获取URL参数(url, param_name, default)` | 从 URL 中获取指定查询参数的值 |
| `添加URL参数(url)` | 向 URL 添加查询参数 |
| `__init__(self, scheme, netloc, path, params, query, fragment, hostname, port, username, password)` |  |

---

## 函数详情

### `解析URL(url)`

解析 URL 字符串，返回 ParsedURL 对象。
包含 scheme, netloc, path, params, query, fragment, hostname, port, username, password

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |

---

### `构建URL(scheme = '', hostname = '', port = None, path = '', params = '', query = '', fragment = '', username = '', password = '')`

构建 URL 字符串

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `scheme` | `None` | （默认：''） |
| `hostname` | `None` | （默认：''） |
| `port` | `None` | （默认：None） |
| `path` | `None` | （默认：''） |
| `params` | `None` | （默认：''） |
| `query` | `None` | （默认：''） |
| `fragment` | `None` | （默认：''） |
| `username` | `None` | （默认：''） |
| `password` | `None` | （默认：''） |

---

### `编码查询参数(params, doseq = False)`

将字典编码为查询参数字符串

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `params` | `None` |  |
| `doseq` | `None` | （默认：False） |

---

### `解析查询参数(query_string, keep_blank_values = False)`

解析查询参数字符串为字典

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `query_string` | `None` |  |
| `keep_blank_values` | `None` | （默认：False） |

---

### `URL拼接(base)`

拼接 URL 路径

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `base` | `None` |  |

---

### `获取URL参数(url, param_name, default = None)`

从 URL 中获取指定查询参数的值

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |
| `param_name` | `None` |  |
| `default` | `None` | （默认：None） |

---

### `添加URL参数(url)`

向 URL 添加查询参数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `url` | `None` |  |

---

### `__init__(self, scheme = '', netloc = '', path = '', params = '', query = '', fragment = '', hostname = '', port = None, username = '', password = '')`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `scheme` | `None` | （默认：''） |
| `netloc` | `None` | （默认：''） |
| `path` | `None` | （默认：''） |
| `params` | `None` | （默认：''） |
| `query` | `None` | （默认：''） |
| `fragment` | `None` | （默认：''） |
| `hostname` | `None` | （默认：''） |
| `port` | `None` | （默认：None） |
| `username` | `None` | （默认：''） |
| `password` | `None` | （默认：''） |

---

## 常量

| 常量名 | 值 |
|--------|-----|
| `parsed` | `解析URL(url)` |
| `params` | `解析查询参数(parsed.query)` |
| `parsed` | `_urlparse.urlparse(url)` |
| `netloc` | `hostname` |
| `result` | `_urlparse.urlunparse((scheme, netloc, path, params, query, fragment))` |
| `parsed` | `_urlparse.parse_qs(query_string, keep_blank_values=keep_blank_values)` |
| `existing_params` | `解析查询参数(existing_query)` |
| `netloc` | `f'{hostname}:{port}'` |
