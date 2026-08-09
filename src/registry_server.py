# -*- coding: utf-8 -*-
"""
光明在线包注册表服务器 (Light Package Registry)

提供 HTTP API 用于包的发布、搜索、安装和版本管理。

API 端点:
  GET  /api/packages                   列出所有包
  GET  /api/packages/<name>            获取包信息
  GET  /api/packages/<name>/<version>  获取指定版本
  GET  /api/packages/<name>/download   下载包（最新版本）
  POST /api/packages/publish           发布包
  GET  /api/search?q=<query>           搜索包
  GET  /api/stats                      注册表统计

用法:
  python registry_server.py                    # 启动服务器（默认端口 8080）
  python registry_server.py --port 9000        # 指定端口
  python registry_server.py --dir ./registry   # 指定存储目录
"""

import os
import sys
import json
import hashlib
import argparse
import tempfile
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, List, Tuple


# =============================================================================
# 包存储
# =============================================================================

class PackageStorage:
    """包存储管理器"""

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.packages_dir = self.storage_dir / 'packages'
        self.index_file = self.storage_dir / 'index.json'
        self._ensure_dirs()
        self.index = self._load_index()

    def _ensure_dirs(self):
        """确保目录存在"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.packages_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> Dict:
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'packages': {}, 'updated': str(datetime.now()), 'stats': {'total_packages': 0, 'total_versions': 0}}

    def _save_index(self):
        """保存索引"""
        self.index['updated'] = str(datetime.now())
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def list_packages(self) -> List[Dict]:
        """列出所有包"""
        pkgs = []
        for name, info in self.index['packages'].items():
            pkg = {
                'name': name,
                'latest_version': info.get('latest_version', '0.0.0'),
                'description': info.get('description', ''),
                'author': info.get('author', ''),
                'versions': list(info.get('versions', {}).keys()),
                'downloads': info.get('downloads', 0),
                'updated': info.get('updated', ''),
            }
            pkgs.append(pkg)
        return pkgs

    def get_package(self, name: str, version: str = None) -> Optional[Dict]:
        """获取包信息"""
        info = self.index['packages'].get(name)
        if not info:
            return None

        if version:
            ver_info = info.get('versions', {}).get(version)
            if not ver_info:
                return None
            return {
                'name': name,
                'version': version,
                'description': info.get('description', ''),
                'author': info.get('author', ''),
                'license': info.get('license', ''),
                'dependencies': ver_info.get('dependencies', {}),
                'published': ver_info.get('published', ''),
                'size': ver_info.get('size', 0),
                'sha256': ver_info.get('sha256', ''),
            }

        return {
            'name': name,
            'latest_version': info.get('latest_version', '0.0.0'),
            'description': info.get('description', ''),
            'author': info.get('author', ''),
            'license': info.get('license', ''),
            'versions': list(info.get('versions', {}).keys()),
            'downloads': info.get('downloads', 0),
            'updated': info.get('updated', ''),
        }

    def publish_package(self, pkg_data: bytes, pkg_name: str, version: str,
                        metadata: Dict) -> Dict:
        """发布包"""
        # 更新索引
        if pkg_name not in self.index['packages']:
            self.index['packages'][pkg_name] = {
                'latest_version': version,
                'description': metadata.get('description', ''),
                'author': metadata.get('author', ''),
                'license': metadata.get('license', ''),
                'versions': {},
                'downloads': 0,
                'updated': str(datetime.now()),
            }
            self.index['stats']['total_packages'] += 1
        else:
            self.index['packages'][pkg_name]['latest_version'] = version
            self.index['packages'][pkg_name]['description'] = metadata.get('description', '')
            self.index['packages'][pkg_name]['author'] = metadata.get('author', '')
            self.index['packages'][pkg_name]['updated'] = str(datetime.now())

        # 保存包文件
        sha256 = hashlib.sha256(pkg_data).hexdigest()
        pkg_dir = self.packages_dir / pkg_name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        pkg_file = pkg_dir / f'{version}.zip'
        with open(pkg_file, 'wb') as f:
            f.write(pkg_data)

        # 更新版本信息
        self.index['packages'][pkg_name]['versions'][version] = {
            'published': str(datetime.now()),
            'size': len(pkg_data),
            'sha256': sha256,
            'dependencies': metadata.get('dependencies', {}),
        }
        self.index['stats']['total_versions'] += 1

        self._save_index()
        return {'status': 'published', 'name': pkg_name, 'version': version, 'sha256': sha256}

    def download_package(self, name: str, version: str = None) -> Optional[bytes]:
        """下载包"""
        info = self.index['packages'].get(name)
        if not info:
            return None

        if version is None:
            version = info.get('latest_version', '0.0.0')

        pkg_file = self.packages_dir / name / f'{version}.zip'
        if not pkg_file.exists():
            return None

        # 更新下载计数
        info['downloads'] = info.get('downloads', 0) + 1
        self._save_index()

        with open(pkg_file, 'rb') as f:
            return f.read()

    def search_packages(self, query: str, sort_by: str = 'downloads',
                         order: str = 'desc', page: int = 1, page_size: int = 20,
                         author: str = '', keyword: str = '') -> Tuple[List[Dict], int]:
        """搜索包，支持排序、分页、过滤"""
        results = []
        q = query.lower().strip() if query else ''

        for name, info in self.index['packages'].items():
            # 全文搜索
            if q:
                search_text = f"{name} {info.get('description', '')} {info.get('author', '')} {' '.join(info.get('keywords', []))}".lower()
                if q not in search_text:
                    continue

            # 作者过滤
            if author and author.lower() not in info.get('author', '').lower():
                continue

            # 关键字过滤
            if keyword:
                pkg_keywords = [kw.lower() for kw in info.get('keywords', [])]
                if keyword.lower() not in pkg_keywords:
                    continue

            results.append({
                'name': name,
                'latest_version': info.get('latest_version', '0.0.0'),
                'description': info.get('description', ''),
                'author': info.get('author', ''),
                'downloads': info.get('downloads', 0),
                'updated': info.get('updated', ''),
                'keywords': info.get('keywords', []),
                'deprecated': info.get('deprecated', False),
            })

        # 排序
        reverse = order.lower() != 'asc'
        if sort_by == 'name':
            results.sort(key=lambda x: x['name'], reverse=reverse)
        elif sort_by == 'updated':
            results.sort(key=lambda x: x.get('updated', ''), reverse=reverse)
        elif sort_by == 'downloads':
            results.sort(key=lambda x: x.get('downloads', 0), reverse=reverse)
        else:
            results.sort(key=lambda x: x.get('downloads', 0), reverse=True)

        # 分页
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size

        return results[start:end], total

    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = self.index.get('stats', {})
        stats['storage_size'] = sum(
            f.stat().st_size for f in self.packages_dir.rglob('*.zip')
        )
        return stats

    # ------------------------------------------------------------------
    # 增强功能：元数据管理、版本管理、弃用标记等
    # ------------------------------------------------------------------

    def list_versions(self, name: str) -> List[Dict]:
        """列出包的所有版本"""
        info = self.index['packages'].get(name)
        if not info:
            return []
        versions = []
        for ver, ver_info in info.get('versions', {}).items():
            versions.append({
                'version': ver,
                'published': ver_info.get('published', ''),
                'size': ver_info.get('size', 0),
                'sha256': ver_info.get('sha256', ''),
                'dependencies': ver_info.get('dependencies', {}),
            })
        versions.sort(key=lambda x: x['version'], reverse=True)
        return versions

    def delete_version(self, name: str, version: str) -> bool:
        """删除特定版本"""
        import shutil
        info = self.index['packages'].get(name)
        if not info:
            return False
        versions = info.get('versions', {})
        if version not in versions:
            return False

        # 删除包文件
        pkg_file = self.packages_dir / name / f'{version}.zip'
        if pkg_file.exists():
            pkg_file.unlink()

        # 从索引中删除
        del versions[version]
        info['versions'] = versions
        self.index['stats']['total_versions'] = max(0, self.index['stats']['total_versions'] - 1)

        # 如果还有版本，更新 latest_version
        if versions:
            sorted_versions = sorted(versions.keys(), reverse=True)
            info['latest_version'] = sorted_versions[0]
        else:
            # 没有版本了，删除包
            del self.index['packages'][name]
            self.index['stats']['total_packages'] = max(0, self.index['stats']['total_packages'] - 1)
            pkg_dir = self.packages_dir / name
            if pkg_dir.exists():
                shutil.rmtree(pkg_dir)

        self._save_index()
        return True

    def update_metadata(self, name: str, metadata: Dict) -> bool:
        """更新包元数据"""
        info = self.index['packages'].get(name)
        if not info:
            return False
        if 'description' in metadata:
            info['description'] = metadata['description']
        if 'author' in metadata:
            info['author'] = metadata['author']
        if 'license' in metadata:
            info['license'] = metadata['license']
        if 'keywords' in metadata:
            info['keywords'] = metadata['keywords']
        info['updated'] = str(datetime.now())
        self._save_index()
        return True

    def add_maintainer(self, name: str, maintainer: str, role: str = 'maintainer') -> bool:
        """添加维护者"""
        info = self.index['packages'].get(name)
        if not info:
            return False
        maintainers = info.setdefault('maintainers', [])
        if maintainer not in maintainers:
            maintainers.append(maintainer)
        self._save_index()
        return True

    def remove_maintainer(self, name: str, maintainer: str) -> bool:
        """移除维护者"""
        info = self.index['packages'].get(name)
        if not info:
            return False
        maintainers = info.get('maintainers', [])
        if maintainer in maintainers:
            maintainers.remove(maintainer)
        self._save_index()
        return True

    def deprecate(self, name: str, message: str = '') -> bool:
        """标记包为已弃用"""
        info = self.index['packages'].get(name)
        if not info:
            return False
        info['deprecated'] = True
        info['deprecation_message'] = message
        info['updated'] = str(datetime.now())
        self._save_index()
        return True

    def undeprecate(self, name: str) -> bool:
        """取消弃用标记"""
        info = self.index['packages'].get(name)
        if not info:
            return False
        info['deprecated'] = False
        info['deprecation_message'] = ''
        info['updated'] = str(datetime.now())
        self._save_index()
        return True

    def get_dependency_graph(self, name: str) -> Dict:
        """获取依赖关系图"""
        graph = {'name': name, 'dependencies': {}}
        visited = set()

        def _resolve(pkg_name: str, depth: int = 0):
            if pkg_name in visited or depth > 10:
                return {}
            visited.add(pkg_name)
            info = self.index['packages'].get(pkg_name)
            if not info:
                return {}
            result = {}
            latest = info.get('latest_version', '0.0.0')
            ver_info = info.get('versions', {}).get(latest, {})
            deps = ver_info.get('dependencies', {})
            for dep_name, dep_version in deps.items():
                result[dep_name] = {
                    'version_constraint': dep_version,
                    'resolved_version': self.index['packages'].get(dep_name, {}).get('latest_version', 'unknown'),
                    'dependencies': _resolve(dep_name, depth + 1),
                }
            return result

        graph['dependencies'] = _resolve(name)
        return graph


# =============================================================================
# HTTP 服务器
# =============================================================================

class RegistryHandler(BaseHTTPRequestHandler):
    """注册表 HTTP 处理器"""

    storage: PackageStorage = None  # 由外部设置
    admin_token: str = ''           # 管理员令牌（可选）

    def log_message(self, format, *args):
        """自定义日志"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

    def _send_json(self, data: Any, status: int = 200):
        """发送 JSON 响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_error(self, message: str, status: int = 400):
        """发送错误响应"""
        self._send_json({'error': message}, status)

    def _send_binary(self, data: bytes, filename: str = 'package.zip'):
        """发送二进制响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/zip')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def _parse_path_parts(self) -> tuple:
        """解析路径为结构化部分"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        params = parse_qs(parsed.query)
        parts = [p for p in path.split('/') if p]
        return path, parts, params

    def do_GET(self):
        """处理 GET 请求"""
        try:
            path, parts, params = self._parse_path_parts()

            # GET /api/health - 健康检查
            if path == '/api/health':
                self._send_json({
                    'status': 'ok',
                    'timestamp': str(datetime.now()),
                    'version': '1.0.0',
                    'registry': '光明包注册表',
                })

            # GET /api/packages - 列出所有包
            elif path == '/api/packages':
                pkgs = self.storage.list_packages()
                self._send_json({
                    'packages': pkgs,
                    'total': len(pkgs),
                    'registry': '光明包注册表',
                    'version': '1.0.0',
                })

            # GET /api/search?q=<query> - 搜索包（增强版）
            elif path == '/api/search':
                query = params.get('q', [''])[0]
                sort_by = params.get('sort', ['downloads'])[0]
                order = params.get('order', ['desc'])[0]
                page = int(params.get('page', ['1'])[0])
                page_size = int(params.get('page_size', ['20'])[0])
                author = params.get('author', [''])[0]
                keyword = params.get('keyword', [''])[0]

                results, total = self.storage.search_packages(
                    query, sort_by=sort_by, order=order,
                    page=page, page_size=page_size,
                    author=author, keyword=keyword,
                )
                self._send_json({
                    'results': results,
                    'query': query,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size if page_size > 0 else 0,
                })

            # GET /api/stats
            elif path == '/api/stats':
                stats = self.storage.get_stats()
                self._send_json(stats)

            # GET /api/packages/<name>/download/<version>
            elif len(parts) >= 5 and parts[3] == 'download' and parts[1] == 'packages':
                pkg_name = parts[2]
                version = parts[4]
                data = self.storage.download_package(pkg_name, version)
                if data:
                    self._send_binary(data, f'{pkg_name}-{version}.zip')
                else:
                    self._send_error(f'包 {pkg_name} v{version} 未找到', 404)

            # GET /api/packages/<name>/download
            elif len(parts) >= 4 and parts[3] == 'download' and parts[1] == 'packages':
                pkg_name = parts[2]
                version = params.get('version', [None])[0]
                data = self.storage.download_package(pkg_name, version)
                if data:
                    self._send_binary(data, f'{pkg_name}.zip')
                else:
                    self._send_error(f'包 {pkg_name} 未找到', 404)

            # GET /api/packages/<name>/versions
            elif len(parts) >= 4 and parts[3] == 'versions' and parts[1] == 'packages':
                pkg_name = parts[2]
                versions = self.storage.list_versions(pkg_name)
                self._send_json({
                    'name': pkg_name,
                    'versions': versions,
                    'total': len(versions),
                })

            # GET /api/packages/<name>/dependencies
            elif len(parts) >= 4 and parts[3] == 'dependencies' and parts[1] == 'packages':
                pkg_name = parts[2]
                graph = self.storage.get_dependency_graph(pkg_name)
                self._send_json(graph)

            # GET /api/packages/<name>/<version>
            elif len(parts) >= 4 and parts[1] == 'packages':
                pkg_name = parts[2]
                version = parts[3]
                pkg = self.storage.get_package(pkg_name, version)
                if pkg:
                    self._send_json(pkg)
                else:
                    self._send_error(f'包 {pkg_name} v{version} 未找到', 404)

            # GET /api/packages/<name>
            elif len(parts) == 3 and parts[1] == 'packages':
                pkg_name = parts[2]
                pkg = self.storage.get_package(pkg_name)
                if pkg:
                    self._send_json(pkg)
                else:
                    self._send_error(f'包 {pkg_name} 未找到', 404)

            # 根路径
            elif path == '' or path == '/':
                self._send_json({
                    'name': '光明包注册表',
                    'version': '1.0.0',
                    'endpoints': [
                        'GET  /api/health',
                        'GET  /api/packages',
                        'GET  /api/packages/{name}',
                        'GET  /api/packages/{name}/{version}',
                        'POST /api/packages/publish',
                        'GET  /api/packages/{name}/download',
                        'GET  /api/packages/{name}/download/{version}',
                        'GET  /api/search?q={query}',
                        'GET  /api/packages/{name}/versions',
                        'GET  /api/packages/{name}/dependencies',
                        'DELETE /api/packages/{name}/{version}',
                        'PUT  /api/packages/{name}/metadata',
                        'POST /api/packages/{name}/maintainers',
                        'DELETE /api/packages/{name}/maintainers/{user}',
                        'POST /api/packages/{name}/deprecate',
                        'POST /api/packages/{name}/undeprecate',
                        'GET  /api/stats',
                    ],
                })

            else:
                self._send_error('Not Found', 404)

        except Exception as e:
            self._send_error(f'Internal error: {str(e)}', 500)

    def do_POST(self):
        """处理 POST 请求"""
        try:
            path, parts, params = self._parse_path_parts()

            # POST /api/packages/publish - 发布包
            if path == '/api/packages/publish':
                content_length = int(self.headers.get('Content-Length', 0))
                content_type = self.headers.get('Content-Type', '')

                if 'multipart/form-data' in content_type:
                    self._send_error('multipart upload not yet supported', 400)
                    return

                body = self.rfile.read(content_length)
                try:
                    data = json.loads(body)
                    pkg_name = data.get('name')
                    version = data.get('version')
                    metadata = data.get('metadata', {})

                    if not pkg_name or not version:
                        self._send_error('Missing required fields: name, version', 400)
                        return

                    pkg_content = data.get('content')
                    if pkg_content:
                        import base64
                        pkg_data = base64.b64decode(pkg_content)
                    else:
                        pkg_data = self._create_minimal_package(pkg_name, version, metadata)

                    result = self.storage.publish_package(pkg_data, pkg_name, version, metadata)
                    self._send_json(result, 201)

                except json.JSONDecodeError:
                    self._send_error('Invalid JSON', 400)
                except Exception as e:
                    self._send_error(f'Publish failed: {str(e)}', 500)

            # POST /api/packages/<name>/maintainers - 添加维护者
            elif len(parts) >= 5 and parts[3] == 'maintainers' and parts[1] == 'packages':
                pkg_name = parts[2]
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                try:
                    data = json.loads(body)
                    maintainer = data.get('maintainer', '')
                    role = data.get('role', 'maintainer')
                    if not maintainer:
                        self._send_error('Missing maintainer field', 400)
                        return
                    if self.storage.add_maintainer(pkg_name, maintainer, role):
                        self._send_json({'status': 'ok', 'maintainer': maintainer, 'role': role})
                    else:
                        self._send_error(f'包 {pkg_name} 未找到', 404)
                except json.JSONDecodeError:
                    self._send_error('Invalid JSON', 400)

            # POST /api/packages/<name>/deprecate - 标记弃用
            elif len(parts) >= 4 and parts[3] == 'deprecate' and parts[1] == 'packages':
                pkg_name = parts[2]
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                try:
                    data = json.loads(body) if body.strip() else {}
                    message = data.get('message', '')
                    if self.storage.deprecate(pkg_name, message):
                        self._send_json({'status': 'deprecated', 'name': pkg_name, 'message': message})
                    else:
                        self._send_error(f'包 {pkg_name} 未找到', 404)
                except json.JSONDecodeError:
                    self._send_error('Invalid JSON', 400)

            # POST /api/packages/<name>/undeprecate - 取消弃用
            elif len(parts) >= 4 and parts[3] == 'undeprecate' and parts[1] == 'packages':
                pkg_name = parts[2]
                if self.storage.undeprecate(pkg_name):
                    self._send_json({'status': 'undeprecated', 'name': pkg_name})
                else:
                    self._send_error(f'包 {pkg_name} 未找到', 404)

            else:
                self._send_error('Not Found', 404)

        except Exception as e:
            self._send_error(f'Internal error: {str(e)}', 500)

    def do_PUT(self):
        """处理 PUT 请求"""
        try:
            path, parts, params = self._parse_path_parts()

            # PUT /api/packages/<name>/metadata - 更新元数据
            if len(parts) >= 4 and parts[3] == 'metadata' and parts[1] == 'packages':
                pkg_name = parts[2]
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                try:
                    metadata = json.loads(body)
                    if self.storage.update_metadata(pkg_name, metadata):
                        self._send_json({'status': 'updated', 'name': pkg_name})
                    else:
                        self._send_error(f'包 {pkg_name} 未找到', 404)
                except json.JSONDecodeError:
                    self._send_error('Invalid JSON', 400)
            else:
                self._send_error('Not Found', 404)

        except Exception as e:
            self._send_error(f'Internal error: {str(e)}', 500)

    def do_DELETE(self):
        """处理 DELETE 请求"""
        try:
            path, parts, params = self._parse_path_parts()

            # DELETE /api/packages/<name>/<version> - 删除版本
            if len(parts) >= 4 and parts[1] == 'packages':
                pkg_name = parts[2]
                version = parts[3]
                if self.storage.delete_version(pkg_name, version):
                    self._send_json({'status': 'deleted', 'name': pkg_name, 'version': version})
                else:
                    self._send_error(f'版本 {pkg_name} v{version} 未找到', 404)

            # DELETE /api/packages/<name>/maintainers/<user> - 移除维护者
            elif len(parts) >= 5 and parts[3] == 'maintainers' and parts[1] == 'packages':
                pkg_name = parts[2]
                maintainer = parts[4]
                if self.storage.remove_maintainer(pkg_name, maintainer):
                    self._send_json({'status': 'removed', 'maintainer': maintainer})
                else:
                    self._send_error(f'包 {pkg_name} 未找到', 404)

            else:
                self._send_error('Not Found', 404)

        except Exception as e:
            self._send_error(f'Internal error: {str(e)}', 500)

    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def _create_minimal_package(self, name: str, version: str, metadata: Dict) -> bytes:
        """创建最小包 zip 文件"""
        import io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            # light.json
            pkg_json = {
                'name': name,
                'version': version,
                'description': metadata.get('description', ''),
                'author': metadata.get('author', ''),
                'license': metadata.get('license', 'MIT'),
                'dependencies': metadata.get('dependencies', {}),
            }
            zf.writestr('light.json', json.dumps(pkg_json, indent=2, ensure_ascii=False))
            # 主模块文件
            zf.writestr(f'{name}.light', f'# {name} v{version}\n# 光明包\n\n段 主函数()：\n  打印 "Hello from {name}!"。\n')
        return buf.getvalue()


# =============================================================================
# 入口
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='光明在线包注册表服务器')
    parser.add_argument('--port', type=int, default=8080, help='服务器端口（默认 8080）')
    parser.add_argument('--dir', type=str, default='./registry_data', help='存储目录（默认 ./registry_data）')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='绑定地址（默认 0.0.0.0）')
    parser.add_argument('--admin-token', type=str, default='', help='管理员令牌（可选）')
    args = parser.parse_args()

    # 初始化存储
    storage = PackageStorage(args.dir)
    RegistryHandler.storage = storage
    RegistryHandler.admin_token = args.admin_token

    # 启动服务器
    server = HTTPServer((args.host, args.port), RegistryHandler)
    print(f'╔══════════════════════════════════════════╗')
    print(f'║     光明包注册表服务器已启动             ║')
    print(f'╠══════════════════════════════════════════╣')
    print(f'║  地址: http://{args.host}:{args.port}')
    print(f'║  存储: {os.path.abspath(args.dir)}')
    print(f'║  包数: {storage.index["stats"]["total_packages"]}')
    print(f'║  健康检查: http://{args.host}:{args.port}/api/health')
    if args.admin_token:
        print(f'║  管理员模式: 已启用')
    print(f'║  按 Ctrl+C 停止服务器')
    print(f'╚══════════════════════════════════════════╝')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务器已停止')
        server.shutdown()


if __name__ == '__main__':
    main()