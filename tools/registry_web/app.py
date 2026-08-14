# -*- coding: utf-8 -*-
"""
段言（Duan）包注册中心 Web 界面

提供友好的 Web 界面用于浏览、搜索和查看段言包信息。

用法：
    python tools/registry_web/app.py              # 默认端口 5000
    python tools/registry_web/app.py --port 8080  # 自定义端口
    python tools/registry_web/app.py --registry-url http://localhost:8000  # 指定注册中心 API
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote, quote


# =============================================================================
# 注册中心 API 客户端
# =============================================================================

class RegistryAPIClient:
    """连接注册中心 API 的客户端"""

    def __init__(self, registry_url: str = "http://localhost:8000"):
        self.registry_url = registry_url.rstrip('/')

    def _request(self, path: str) -> Optional[Dict]:
        """发送 API 请求"""
        url = f"{self.registry_url}{path}"
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'duan-registry-web/1.0',
                'Accept': 'application/json'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
            return None

    def list_packages(self) -> List[Dict]:
        """列出所有包"""
        data = self._request('/api/v1/packages')
        if data and 'packages' in data:
            return data['packages']
        return []

    def get_package(self, name: str) -> Optional[Dict]:
        """获取包详情"""
        return self._request(f'/api/v1/packages/{quote(name)}')

    def search(self, query: str) -> List[Dict]:
        """搜索包"""
        data = self._request(f'/api/v1/search?q={quote(query)}')
        if data and 'results' in data:
            return data['results']
        return []

    def get_stats(self) -> Dict[str, Any]:
        """获取注册中心统计"""
        data = self._request('/api/v1/stats')
        return data or {'total_packages': 0, 'total_downloads': 0}

    def is_connected(self) -> bool:
        """检查是否连接到注册中心"""
        data = self._request('/api/v1/stats')
        return data is not None


# =============================================================================
# 内置静态注册表数据（当注册中心不可用时回退）
# =============================================================================

BUILTIN_PACKAGES = {
    "标准数学扩展": {
        "name": "标准数学扩展",
        "version": "1.0.0",
        "description": "扩展数学函数库：矩阵运算、复数、统计函数",
        "author": "段言团队",
        "keywords": ["数学", "矩阵", "统计"],
        "dependencies": [],
        "repository": "https://gitcode.com/duan-lang/duan-math-ext.git",
    },
    "网络请求": {
        "name": "网络请求",
        "version": "1.0.0",
        "description": "HTTP 客户端库：GET/POST 请求、JSON 解析",
        "author": "段言团队",
        "keywords": ["网络", "HTTP", "API"],
        "dependencies": [],
        "repository": "https://gitcode.com/duan-lang/duan-http.git",
    },
    "命令行工具": {
        "name": "命令行工具",
        "version": "1.0.0",
        "description": "CLI 开发工具：参数解析、进度条、颜色输出",
        "author": "段言团队",
        "keywords": ["CLI", "命令行", "终端"],
        "dependencies": [],
        "repository": "https://gitcode.com/duan-lang/duan-cli-utils.git",
    },
    "测试框架": {
        "name": "测试框架",
        "version": "1.0.0",
        "description": "单元测试框架：断言、测试套件、覆盖率",
        "author": "段言团队",
        "keywords": ["测试", "单元测试", "断言"],
        "dependencies": [],
        "repository": "https://gitcode.com/duan-lang/duan-test.git",
    },
    "数据库": {
        "name": "数据库",
        "version": "1.0.0",
        "description": "数据库操作库：SQL 查询、连接池、ORM",
        "author": "段言团队",
        "keywords": ["数据库", "SQL", "ORM"],
        "dependencies": [],
        "repository": "https://gitcode.com/duan-lang/duan-db.git",
    },
    "模板引擎": {
        "name": "模板引擎",
        "version": "1.0.0",
        "description": "文本模板引擎：变量替换、循环、条件渲染",
        "author": "段言团队",
        "keywords": ["模板", "渲染", "HTML"],
        "dependencies": [],
        "repository": "https://gitcode.com/duan-lang/duan-template.git",
    },
    "日志": {
        "name": "日志",
        "version": "1.0.0",
        "description": "日志记录库：分级日志、文件输出、格式化",
        "author": "段言团队",
        "keywords": ["日志", "调试", "记录"],
        "dependencies": [],
        "repository": "https://gitcode.com/duan-lang/duan-log.git",
    },
    "配置管理": {
        "name": "配置管理",
        "version": "1.0.0",
        "description": "配置文件管理：TOML/JSON/YAML 读写",
        "author": "段言团队",
        "keywords": ["配置", "TOML", "JSON"],
        "dependencies": [],
        "repository": "https://gitcode.com/duan-lang/duan-config.git",
    },
    "加密": {
        "name": "加密",
        "version": "1.0.0",
        "description": "加密工具库：哈希、对称加密、Base64",
        "author": "段言团队",
        "keywords": ["加密", "哈希", "安全"],
        "dependencies": [],
        "repository": "https://gitcode.com/duan-lang/duan-crypto.git",
    },
    "图像处理": {
        "name": "图像处理",
        "version": "1.0.0",
        "description": "图像处理库：缩放、裁剪、滤镜",
        "author": "段言团队",
        "keywords": ["图像", "图片", "处理"],
        "dependencies": [],
        "repository": "https://gitcode.com/duan-lang/duan-image.git",
    },
}


# =============================================================================
# HTTP 处理器
# =============================================================================

class RegistryWebHandler(BaseHTTPRequestHandler):
    """Web 界面 HTTP 请求处理器"""

    # 静态模板文件路径
    _templates_dir = Path(__file__).resolve().parent / 'templates'
    _static_dir = Path(__file__).resolve().parent / 'static'

    def __init__(self, *args, **kwargs):
        # 注册中心客户端（在 main 中设置）
        self.client = getattr(self.__class__, 'api_client', RegistryAPIClient())
        super().__init__(*args, **kwargs)

    def _read_template(self, name: str) -> str:
        """读取模板文件"""
        path = self._templates_dir / name
        if path.exists():
            return path.read_text(encoding='utf-8')
        return f"<h1>模板 {name} 未找到</h1>"

    def _read_static(self, name: str) -> Optional[bytes]:
        """读取静态文件"""
        path = self._static_dir / name
        if path.exists():
            return path.read_bytes()
        return None

    def _send_html(self, html: str, status=200):
        """发送 HTML 响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _send_static(self, content: bytes, content_type: str):
        """发送静态文件响应"""
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'max-age=3600')
        self.end_headers()
        self.wfile.write(content)

    def _render(self, template: str, **kwargs) -> str:
        """渲染模板（简单字符串替换）"""
        html = self._read_template(template)
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"
            html = html.replace(placeholder, str(value))
        return html

    def _render_package_list(self, packages: List[Dict]) -> str:
        """渲染包列表 HTML"""
        rows = []
        for pkg in packages:
            name = pkg.get('name', '?')
            version = pkg.get('version', '?')
            desc = pkg.get('description', '')
            keywords = pkg.get('keywords', [])
            downloads = pkg.get('download_count', 0)
            author = pkg.get('author', pkg.get('authors', ['?']))
            if isinstance(author, list):
                author = ', '.join(author)
            kw_tags = ''.join(f'<span class="tag">{k}</span>' for k in keywords[:3])
            rows.append(f'''
            <div class="package-card">
                <div class="package-header">
                    <a href="/package/{quote(name)}" class="package-name">{name}</a>
                    <span class="package-version">v{version}</span>
                </div>
                <div class="package-desc">{desc}</div>
                <div class="package-meta">
                    <span class="meta-item">👤 {author}</span>
                    <span class="meta-item">⬇️ {downloads}</span>
                    {kw_tags}
                </div>
                <div class="package-install">
                    <code>duan pkg install {name}</code>
                </div>
            </div>
            ''')
        return ''.join(rows)

    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        query = parse_qs(parsed.query)

        # 静态文件
        if path.startswith('/static/'):
            filename = path[8:]
            static_data = self._read_static(filename)
            if static_data is not None:
                if filename.endswith('.css'):
                    self._send_static(static_data, 'text/css; charset=utf-8')
                elif filename.endswith('.js'):
                    self._send_static(static_data, 'application/javascript; charset=utf-8')
                elif filename.endswith('.png'):
                    self._send_static(static_data, 'image/png')
                else:
                    self._send_static(static_data, 'application/octet-stream')
                return
            self._send_html('<h1>404 - 文件未找到</h1>', 404)
            return

        # 首页
        if path == '/' or path == '/index':
            packages = self.client.list_packages() if self.client.is_connected() else list(BUILTIN_PACKAGES.values())
            stats = self.client.get_stats() if self.client.is_connected() else {'total_packages': len(BUILTIN_PACKAGES), 'total_downloads': 0}
            if not packages:
                packages = list(BUILTIN_PACKAGES.values())
            package_list_html = self._render_package_list(packages)
            html = self._render(
                'index.html',
                package_list=package_list_html,
                total_packages=stats.get('total_packages', len(packages)),
                total_downloads=stats.get('total_downloads', 0),
                registry_url=self.client.registry_url,
                search_query='',
            )
            self._send_html(html)
            return

        # 搜索
        if path == '/search':
            q = query.get('q', [''])[0]
            if not q:
                # 重定向到首页
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return

            if self.client.is_connected():
                results = self.client.search(q)
            else:
                # 本地搜索
                q_lower = q.lower()
                results = []
                for pkg in BUILTIN_PACKAGES.values():
                    if (q_lower in pkg.get('name', '').lower() or
                        q_lower in pkg.get('description', '').lower() or
                        any(q_lower in kw.lower() for kw in pkg.get('keywords', []))):
                        results.append(pkg)

            if not results:
                package_list_html = '<div class="no-results">未找到匹配的包。</div>'
            else:
                package_list_html = self._render_package_list(results)

            html = self._render(
                'search.html',
                package_list=package_list_html,
                search_query=q,
                result_count=len(results),
                registry_url=self.client.registry_url,
            )
            self._send_html(html)
            return

        # 包详情
        if path.startswith('/package/'):
            name = unquote(path[9:])
            if self.client.is_connected():
                pkg = self.client.get_package(name)
            else:
                pkg = BUILTIN_PACKAGES.get(name)

            if not pkg:
                self._send_html(self._render('package.html',
                    package_name=name,
                    package_version='?',
                    package_description='未找到该包',
                    package_author='?',
                    package_keywords='',
                    package_dependencies='无',
                    package_repository='#',
                    package_downloads='0',
                    install_command=f'duan pkg install {name}',
                    registry_url=self.client.registry_url,
                    search_query='',
                ), 404)
                return

            author = pkg.get('author', pkg.get('authors', ['?']))
            if isinstance(author, list):
                author = ', '.join(author)
            keywords = pkg.get('keywords', [])
            kw_tags = ', '.join(keywords) if keywords else '无'
            deps = pkg.get('dependencies', [])
            if isinstance(deps, dict):
                deps = list(deps.keys())
            deps_str = ', '.join(deps) if deps else '无'
            repo = pkg.get('repository', pkg.get('git', '#'))
            downloads = pkg.get('download_count', 0)

            html = self._render(
                'package.html',
                package_name=pkg.get('name', name),
                package_version=pkg.get('version', '?'),
                package_description=pkg.get('description', ''),
                package_author=author,
                package_keywords=kw_tags,
                package_dependencies=deps_str,
                package_repository=repo,
                package_downloads=str(downloads),
                install_command=f'duan pkg install {pkg.get("name", name)}',
                registry_url=self.client.registry_url,
                search_query='',
            )
            self._send_html(html)
            return

        # 404
        self._send_html('<h1>404 - 页面未找到</h1>', 404)

    def log_message(self, format, *args):
        """自定义日志格式"""
        sys.stderr.write(f"[RegistryWeb] {args[0]} {args[1]} {args[2]}\n")


# =============================================================================
# 启动
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='段言包注册中心 Web 界面')
    parser.add_argument('--port', '-p', type=int, default=5000, help='监听端口（默认: 5000）')
    parser.add_argument('--host', default='127.0.0.1', help='监听地址（默认: 127.0.0.1）')
    parser.add_argument('--registry-url', default='http://localhost:8000',
                        help='注册中心 API 地址（默认: http://localhost:8000）')
    parser.add_argument('--open-browser', action='store_true', help='自动打开浏览器')
    args = parser.parse_args()

    # 设置 API 客户端
    RegistryWebHandler.api_client = RegistryAPIClient(args.registry_url)

    # 检查注册中心连接
    if RegistryWebHandler.api_client.is_connected():
        print(f"✅ 已连接到注册中心: {args.registry_url}")
    else:
        print(f"⚠️  无法连接到注册中心 {args.registry_url}")
        print(f"   使用内置包数据（仅显示预置包）")
        print(f"   提示: 先运行注册中心服务器: python src/registry_server.py")

    server = HTTPServer((args.host, args.port), RegistryWebHandler)
    url = f"http://{args.host}:{args.port}"

    print(f"\n📦 段言包注册中心 Web 界面")
    print(f"=" * 40)
    print(f"   地址: {url}")
    print(f"   API:  {args.registry_url}")
    print(f"   端口: {args.port}")
    print(f"=" * 40)
    print(f"\n按 Ctrl+C 停止服务器\n")

    if args.open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.server_close()


if __name__ == '__main__':
    main()