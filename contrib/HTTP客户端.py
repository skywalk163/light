"""
HTTP客户端模块 - GET/POST、Cookie、重定向

提供HTTP请求功能，包括：
- GET/POST请求
- Cookie管理
- 重定向处理
- 超时控制
- 文件上传下载
"""
import urllib.request
import urllib.parse
import http.cookiejar
import json
from typing import Dict, Any, Optional, Tuple, List
import socket


class HTTP客户端:
    """HTTP客户端类"""
    
    def __init__(self, 超时: int = 30, 最大重定向: int = 5):
        self._超时 = 超时
        self._最大重定向 = 最大重定向
        self._cookie_jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookie_jar),
            urllib.request.HTTPRedirectHandler
        )
        self._headers = {
            'User-Agent': 'LightLang/1.0',
            'Accept': '*/*',
        }
    
    def 设置超时(self, 秒数: int):
        """设置超时时间"""
        self._超时 = 秒数
    
    def 设置用户代理(self, UA: str):
        """设置User-Agent"""
        self._headers['User-Agent'] = UA
    
    def 设置请求头(self, 名称: str, 值: str):
        """设置请求头"""
        self._headers[名称] = 值
    
    def 设置多个请求头(self, headers: Dict[str, str]):
        """设置多个请求头"""
        self._headers.update(headers)
    
    def GET(self, URL: str, 参数: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """发送GET请求"""
        完整URL = self._构建URL(URL, 参数)
        请求 = urllib.request.Request(完整URL, method='GET')
        self._添加请求头(请求, headers)
        
        try:
            响应 = self._opener.open(请求, timeout=self._超时)
            return self._解析响应(响应)
        except urllib.error.URLError as e:
            return {'成功': False, '错误': str(e), '状态码': None}
        except socket.timeout:
            return {'成功': False, '错误': '请求超时', '状态码': None}
    
    def POST(self, URL: str, 数据: Dict[str, Any] = None, 
             JSON数据: Any = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """发送POST请求"""
        请求 = urllib.request.Request(URL, method='POST')
        self._添加请求头(请求, headers)
        
        if JSON数据:
            请求.add_header('Content-Type', 'application/json')
            请求数据 = json.dumps(JSON数据).encode('utf-8')
        elif 数据:
            请求数据 = urllib.parse.urlencode(数据).encode('utf-8')
        else:
            请求数据 = b''
        
        try:
            响应 = self._opener.open(请求, 请求数据, timeout=self._超时)
            return self._解析响应(响应)
        except urllib.error.URLError as e:
            return {'成功': False, '错误': str(e), '状态码': None}
        except socket.timeout:
            return {'成功': False, '错误': '请求超时', '状态码': None}
    
    def PUT(self, URL: str, 数据: Any = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """发送PUT请求"""
        请求 = urllib.request.Request(URL, method='PUT')
        self._添加请求头(请求, headers)
        
        if 数据:
            if isinstance(数据, (dict, list)):
                请求.add_header('Content-Type', 'application/json')
                请求数据 = json.dumps(数据).encode('utf-8')
            else:
                请求数据 = str(数据).encode('utf-8')
        else:
            请求数据 = b''
        
        try:
            响应 = self._opener.open(请求, 请求数据, timeout=self._超时)
            return self._解析响应(响应)
        except urllib.error.URLError as e:
            return {'成功': False, '错误': str(e), '状态码': None}
    
    def DELETE(self, URL: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """发送DELETE请求"""
        请求 = urllib.request.Request(URL, method='DELETE')
        self._添加请求头(请求, headers)
        
        try:
            响应 = self._opener.open(请求, timeout=self._超时)
            return self._解析响应(响应)
        except urllib.error.URLError as e:
            return {'成功': False, '错误': str(e), '状态码': None}
    
    def 上传文件(self, URL: str, 文件路径: str, 字段名: str = 'file',
                  其他数据: Dict[str, str] = None) -> Dict[str, Any]:
        """上传文件"""
        with open(文件路径, 'rb') as f:
            文件内容 = f.read()
        
        文件名 = 文件路径.split('/')[-1].split('\\')[-1]
        
        boundary = '----LightLangFormBoundary' + str(hash(文件名) % 10000)
        
        body_parts = []
        if 其他数据:
            for key, value in 其他数据.items():
                body_parts.append(f'--{boundary}\r\n')
                body_parts.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n')
                body_parts.append(f'{value}\r\n')
        
        body_parts.append(f'--{boundary}\r\n')
        body_parts.append(f'Content-Disposition: form-data; name="{字段名}"; filename="{文件名}"\r\n')
        body_parts.append(f'Content-Type: application/octet-stream\r\n\r\n')
        body_parts.append(文件内容)
        body_parts.append(f'\r\n--{boundary}--\r\n')
        
        body = b''.join([p.encode('utf-8') if isinstance(p, str) else p for p in body_parts])
        
        请求 = urllib.request.Request(URL, data=body, method='POST')
        请求.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        self._添加请求头(请求)
        
        try:
            响应 = self._opener.open(请求, timeout=self._超时)
            return self._解析响应(响应)
        except urllib.error.URLError as e:
            return {'成功': False, '错误': str(e), '状态码': None}
    
    def 下载文件(self, URL: str, 保存路径: str) -> Dict[str, Any]:
        """下载文件"""
        请求 = urllib.request.Request(URL)
        self._添加请求头(请求)
        
        try:
            响应 = self._opener.open(请求, timeout=self._超时)
            内容 = 响应.read()
            
            with open(保存路径, 'wb') as f:
                f.write(内容)
            
            return {
                '成功': True,
                '状态码': 响应.getcode(),
                '文件大小': len(内容),
                '保存路径': 保存路径
            }
        except urllib.error.URLError as e:
            return {'成功': False, '错误': str(e), '状态码': None}
        except IOError as e:
            return {'成功': False, '错误': f'文件保存失败: {e}', '状态码': None}
    
    def 获取Cookies(self) -> List[Dict[str, str]]:
        """获取所有Cookie"""
        cookies = []
        for cookie in self._cookie_jar:
            cookies.append({
                '名称': cookie.name,
                '值': cookie.value,
                '域名': cookie.domain,
                '路径': cookie.path,
            })
        return cookies
    
    def 清除Cookies(self):
        """清除所有Cookie"""
        self._cookie_jar.clear()
    
    def _构建URL(self, URL: str, 参数: Dict[str, Any] = None) -> str:
        """构建完整URL"""
        if 参数:
            查询字符串 = urllib.parse.urlencode(参数)
            if '?' in URL:
                return URL + '&' + 查询字符串
            else:
                return URL + '?' + 查询字符串
        return URL
    
    def _添加请求头(self, 请求: urllib.request.Request, 额外headers: Dict[str, str] = None):
        """添加请求头"""
        for 名称, 值 in self._headers.items():
            请求.add_header(名称, 值)
        if 额外headers:
            for 名称, 值 in 额外headers.items():
                请求.add_header(名称, 值)
    
    def _解析响应(self, 响应) -> Dict[str, Any]:
        """解析响应"""
        内容 = 响应.read()
        编码 = 响应.headers.get_content_charset() or 'utf-8'
        
        try:
            文本内容 = 内容.decode(编码)
            try:
                JSON数据 = json.loads(文本内容)
                return {
                    '成功': True,
                    '状态码': 响应.getcode(),
                    '内容': JSON数据,
                    '文本': 文本内容,
                    '响应头': dict(响应.headers),
                    'URL': 响应.url,
                }
            except json.JSONDecodeError:
                return {
                    '成功': True,
                    '状态码': 响应.getcode(),
                    '内容': None,
                    '文本': 文本内容,
                    '响应头': dict(响应.headers),
                    'URL': 响应.url,
                }
        except UnicodeDecodeError:
            return {
                '成功': True,
                '状态码': 响应.getcode(),
                '内容': None,
                '二进制': 内容,
                '响应头': dict(响应.headers),
                'URL': 响应.url,
            }


def HTTPGET(URL: str, 参数: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """发送GET请求"""
    客户端 = HTTP客户端()
    return 客户端.GET(URL, 参数, headers)


def HTTPPOST(URL: str, 数据: Dict[str, Any] = None, JSON数据: Any = None) -> Dict[str, Any]:
    """发送POST请求"""
    客户端 = HTTP客户端()
    return 客户端.POST(URL, 数据, JSON数据)


def HTTPPUT(URL: str, 数据: Any = None) -> Dict[str, Any]:
    """发送PUT请求"""
    客户端 = HTTP客户端()
    return 客户端.PUT(URL, 数据)


def HTTPDELETE(URL: str) -> Dict[str, Any]:
    """发送DELETE请求"""
    客户端 = HTTP客户端()
    return 客户端.DELETE(URL)


def 上传文件(URL: str, 文件路径: str, 字段名: str = 'file') -> Dict[str, Any]:
    """上传文件"""
    客户端 = HTTP客户端()
    return 客户端.上传文件(URL, 文件路径, 字段名)


def 下载文件(URL: str, 保存路径: str) -> Dict[str, Any]:
    """下载文件"""
    客户端 = HTTP客户端()
    return 客户端.下载文件(URL, 保存路径)


def 创建HTTP客户端(超时: int = 30) -> HTTP客户端:
    """创建HTTP客户端实例"""
    return HTTP客户端(超时)


def 获取网页内容(URL: str) -> str:
    """获取网页内容"""
    结果 = HTTPGET(URL)
    return 结果.get('文本', '') if 结果['成功'] else ''


def 获取JSON数据(URL: str) -> Any:
    """获取JSON数据"""
    客户端 = HTTP客户端()
    客户端.设置请求头('Accept', 'application/json')
    结果 = 客户端.GET(URL)
    return 结果.get('内容') if 结果['成功'] else None


def 发送表单数据(URL: str, 数据: Dict[str, Any]) -> Dict[str, Any]:
    """发送表单数据"""
    return HTTPPOST(URL, 数据=数据)


def 发送JSON数据(URL: str, 数据: Any) -> Dict[str, Any]:
    """发送JSON数据"""
    return HTTPPOST(URL, JSON数据=数据)


def 检查URL可达(URL: str, 超时: int = 5) -> bool:
    """检查URL是否可达"""
    try:
        客户端 = HTTP客户端(超时=超时)
        结果 = 客户端.GET(URL)
        return 结果['成功'] and 结果['状态码'] < 400
    except:
        return False


def 获取URL状态码(URL: str) -> Optional[int]:
    """获取URL状态码"""
    客户端 = HTTP客户端()
    结果 = 客户端.GET(URL)
    return 结果.get('状态码')


def 批量GET请求(URL列表: List[str], 并发数: int = 5) -> List[Dict[str, Any]]:
    """批量GET请求"""
    import concurrent.futures
    
    客户端 = HTTP客户端()
    结果列表 = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=并发数) as executor:
        futures = {executor.submit(客户端.GET, URL): URL for URL in URL列表}
        for future in concurrent.futures.as_completed(futures):
            结果列表.append(future.result())
    
    return 结果列表


def 解析响应JSON(响应数据: Dict[str, Any]) -> Any:
    """解析响应中的JSON"""
    return 响应数据.get('内容')


def 获取响应头(响应数据: Dict[str, Any], 名称: str) -> Optional[str]:
    """获取响应头"""
    响应头 = 响应数据.get('响应头', {})
    return 响应头.get(名称)


def 设置基础认证(用户名: str, 密码: str) -> Dict[str, str]:
    """设置基础认证请求头"""
    import base64
    认证字符串 = base64.b64encode(f'{用户名}:{密码}'.encode()).decode()
    return {'Authorization': f'Basic {认证字符串}'}


def 设置Bearer认证(token: str) -> Dict[str, str]:
    """设置Bearer认证请求头"""
    return {'Authorization': f'Bearer {token}'}


def 流式下载(URL: str, 保存路径: str, 进度回调: callable = None) -> Dict[str, Any]:
    """流式下载文件"""
    请求 = urllib.request.Request(URL)
    
    try:
        响应 = urllib.request.urlopen(请求, timeout=30)
        文件大小 = int(响应.headers.get('Content-Length', 0))
        已下载 = 0
        
        with open(保存路径, 'wb') as f:
            while True:
                块 = 响应.read(8192)
                if not 块:
                    break
                f.write(块)
                已下载 += len(块)
                if 进度回调 and 文件大小 > 0:
                    进度 = 已下载 / 文件大小 * 100
                    进度回调(进度, 已下载, 文件大小)
        
        return {
            '成功': True,
            '文件大小': 文件大小,
            '保存路径': 保存路径
        }
    except Exception as e:
        return {'成功': False, '错误': str(e)}