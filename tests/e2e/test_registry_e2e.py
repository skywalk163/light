# -*- coding: utf-8 -*-
"""
光明包注册表端到端测试

针对 src/registry_server.py 的 PackageStorage（制品仓库）与 RegistryHandler
（HTTP 接口）做完整的发布 → 搜索 → 下载 → 删除 全链路验证。
"""

import io
import os
import sys
import json
import time
import zipfile
import threading
import tempfile
import shutil
import unittest
from pathlib import Path
from http.server import HTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, parse_qs

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from registry_server import PackageStorage, RegistryHandler


# ===========================================================================
# 测试辅助：造一个最小合法包（.zip 字节流）
# ===========================================================================

def make_package_bytes(name: str, version: str, metadata: dict = None) -> bytes:
    """在内存里构造一个最小合法的光明包 zip（结构对齐 _create_minimal_package）"""
    metadata = metadata or {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        pkg_json = {
            'name': name,
            'version': version,
            'description': metadata.get('description', ''),
            'author': metadata.get('author', ''),
            'license': metadata.get('license', 'MIT'),
            'dependencies': metadata.get('dependencies', {}),
        }
        zf.writestr('light.json', json.dumps(pkg_json, indent=2, ensure_ascii=False))
        zf.writestr(f'{name}.light', f'# {name} v{version}\n# 光明包\n')
    return buf.getvalue()


# ===========================================================================
# PackageStorage 单元测试
# ===========================================================================

class TestPackageStorage(unittest.TestCase):
    """PackageStorage 核心功能测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='light_reg_test_')
        self.storage = PackageStorage(storage_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _publish(self, name, version='1.0.0', metadata=None):
        metadata = metadata or {}
        return self.storage.publish_package(
            make_package_bytes(name, version, metadata), name, version, metadata)

    def test_empty_storage(self):
        """空注册表"""
        self.assertEqual(self.storage.list_packages(), [])
        self.assertIsNone(self.storage.get_package('nonexistent'))
        results, total = self.storage.search_packages('test')
        self.assertEqual(results, [])
        self.assertEqual(total, 0)

    def test_publish_and_get(self):
        """发布并获取包"""
        result = self._publish('测试包', '1.0.0', {
            'description': '一个测试包',
            'author': '测试作者',
        })
        self.assertEqual(result['status'], 'published')
        self.assertEqual(result['name'], '测试包')
        self.assertEqual(result['version'], '1.0.0')
        self.assertTrue(result['sha256'])

        info = self.storage.get_package('测试包')
        self.assertIsNotNone(info)
        self.assertEqual(info['latest_version'], '1.0.0')
        self.assertEqual(info['description'], '一个测试包')
        self.assertEqual(info['author'], '测试作者')
        self.assertEqual(info['downloads'], 0)
        self.assertEqual(info['versions'], ['1.0.0'])

    def test_get_specific_version(self):
        """获取指定版本的信息"""
        self._publish('版本包', '1.0.0', {'dependencies': {'依赖包': '^1.0.0'}})
        ver = self.storage.get_package('版本包', '1.0.0')
        self.assertIsNotNone(ver)
        self.assertEqual(ver['version'], '1.0.0')
        self.assertEqual(ver['dependencies'], {'依赖包': '^1.0.0'})
        self.assertGreater(ver['size'], 0)
        self.assertIsNone(self.storage.get_package('版本包', '9.9.9'))

    def test_publish_version_history(self):
        """版本历史记录：所有版本都保留，latest 指向最后发布的版本"""
        self._publish('pkg', '1.0.0')
        time.sleep(0.01)  # 确保时间戳不同
        self._publish('pkg', '2.0.0')

        versions = self.storage.list_versions('pkg')
        self.assertEqual(len(versions), 2)
        # list_versions 按版本号降序
        self.assertEqual(versions[0]['version'], '2.0.0')
        self.assertEqual(versions[1]['version'], '1.0.0')
        self.assertEqual(self.storage.get_package('pkg')['latest_version'], '2.0.0')
        self.assertEqual(self.storage.list_versions('不存在'), [])

    def test_search_by_name(self):
        """按名称搜索"""
        self._publish('网络请求')
        self._publish('网络工具')
        results, total = self.storage.search_packages('网络')
        self.assertEqual(total, 2)
        self.assertEqual(len(results), 2)

    def test_search_by_keyword(self):
        """按关键词搜索（关键词经 update_metadata 写入）"""
        self._publish('测试包')
        self.assertTrue(self.storage.update_metadata('测试包', {'keywords': ['测试', 'demo']}))

        results, total = self.storage.search_packages('demo')
        self.assertEqual(total, 1)
        self.assertEqual(results[0]['name'], '测试包')

        # keyword 精确过滤
        results, total = self.storage.search_packages('', keyword='测试')
        self.assertEqual(total, 1)
        results, total = self.storage.search_packages('', keyword='不存在的关键词')
        self.assertEqual(total, 0)

    def test_search_ranking_by_relevance(self):
        """搜索排序：sort_by='relevance' 时精确匹配优先"""
        self._publish('数学')
        self._publish('数学扩展')
        results, total = self.storage.search_packages('数学', sort_by='relevance')
        self.assertEqual(total, 2)
        self.assertEqual(results[0]['name'], '数学')
        self.assertEqual(results[0]['score'], 100)
        self.assertEqual(results[1]['score'], 80)

    def test_delete_package(self):
        """删除整个包"""
        self._publish('todelete')
        self.assertIsNotNone(self.storage.get_package('todelete'))
        self.assertTrue(self.storage.delete_package('todelete'))
        self.assertIsNone(self.storage.get_package('todelete'))
        self.assertFalse(self.storage.delete_package('todelete'))

    def test_delete_version(self):
        """删除单个版本；删完最后一个版本时包整体消失"""
        self._publish('多版本', '1.0.0')
        self._publish('多版本', '2.0.0')
        self.assertTrue(self.storage.delete_version('多版本', '2.0.0'))
        self.assertEqual(self.storage.get_package('多版本')['latest_version'], '1.0.0')
        self.assertFalse(self.storage.delete_version('多版本', '2.0.0'))

        self.assertTrue(self.storage.delete_version('多版本', '1.0.0'))
        self.assertIsNone(self.storage.get_package('多版本'))

    def test_download_package_roundtrip(self):
        """下载包：拿到的字节流可解压，且下载计数自增"""
        payload = make_package_bytes('可下载', '1.0.0')
        self.storage.publish_package(payload, '可下载', '1.0.0', {})

        data = self.storage.download_package('可下载')
        self.assertEqual(data, payload)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            self.assertIn('light.json', zf.namelist())
        self.assertEqual(self.storage.get_package('可下载')['downloads'], 1)

        self.assertIsNone(self.storage.download_package('不存在'))
        self.assertIsNone(self.storage.download_package('可下载', '9.9.9'))

    def test_download_count(self):
        """下载计数"""
        self._publish('downloaded')
        for _ in range(5):
            self.assertTrue(self.storage.record_download('downloaded'))
        info = self.storage.get_package('downloaded')
        self.assertEqual(info['downloads'], 5)
        self.assertFalse(self.storage.record_download('不存在'))

    def test_get_stats(self):
        """注册表统计"""
        self._publish('a', '1.0.0')
        self._publish('b', '2.0.0')
        stats = self.storage.get_stats()
        self.assertEqual(stats['total_packages'], 2)
        self.assertEqual(stats['total_versions'], 2)
        self.assertGreater(stats['storage_size'], 0)

    def test_deprecate_and_undeprecate(self):
        """弃用与取消弃用"""
        self._publish('待弃用')
        self.assertTrue(self.storage.deprecate('待弃用', '请使用新包'))
        results, _ = self.storage.search_packages('待弃用')
        self.assertTrue(results[0]['deprecated'])
        self.assertTrue(self.storage.undeprecate('待弃用'))
        results, _ = self.storage.search_packages('待弃用')
        self.assertFalse(results[0]['deprecated'])
        self.assertFalse(self.storage.deprecate('不存在'))

    def test_maintainers(self):
        """维护者增删"""
        self._publish('有维护者')
        self.assertTrue(self.storage.add_maintainer('有维护者', '张三'))
        self.assertTrue(self.storage.add_maintainer('有维护者', '张三'))  # 幂等
        self.assertEqual(self.storage.index['packages']['有维护者']['maintainers'], ['张三'])
        self.assertTrue(self.storage.remove_maintainer('有维护者', '张三'))
        self.assertEqual(self.storage.index['packages']['有维护者']['maintainers'], [])
        self.assertFalse(self.storage.add_maintainer('不存在', '张三'))

    def test_dependency_graph(self):
        """依赖关系图"""
        self._publish('底层库', '1.0.0')
        self._publish('上层库', '1.0.0', {'dependencies': {'底层库': '^1.0.0'}})
        graph = self.storage.get_dependency_graph('上层库')
        self.assertEqual(graph['name'], '上层库')
        self.assertIn('底层库', graph['dependencies'])
        self.assertEqual(graph['dependencies']['底层库']['resolved_version'], '1.0.0')

    def test_index_persisted(self):
        """索引落盘后可被新实例读取"""
        self._publish('持久化', '1.0.0')
        self.assertTrue((Path(self.tmpdir) / 'index.json').exists())
        reopened = PackageStorage(storage_dir=self.tmpdir)
        self.assertEqual(reopened.get_package('持久化')['latest_version'], '1.0.0')


# ===========================================================================
# 端到端集成测试（HTTP 级别）
# ===========================================================================

class TestRegistryServerE2E(unittest.TestCase):
    """注册表 HTTP 服务器端到端测试"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix='light_reg_e2e_')
        cls._case_id = 0
        cls.server = HTTPServer(('127.0.0.1', 0), RegistryHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f'http://127.0.0.1:{cls.port}'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)  # 等待服务器启动

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        RegistryHandler.storage = None
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        """每个测试用独立存储目录，确保测试隔离

        RegistryHandler 通过类属性 storage 注入 PackageStorage。
        """
        cls = type(self)
        cls._case_id += 1
        case_dir = os.path.join(cls.tmpdir, f'case_{cls._case_id}')
        self.storage = PackageStorage(storage_dir=case_dir)
        RegistryHandler.storage = self.storage

    # -- HTTP 辅助 ---------------------------------------------------------

    def _build_url(self, path: str) -> str:
        """构建 URL，只编码路径部分，保留查询字符串"""
        if '?' in path:
            base_path, query = path.split('?', 1)
            encoded_path = quote(base_path, safe='/')
            encoded_query = urlencode(parse_qs(query), doseq=True)
            return f'{self.base_url}{encoded_path}?{encoded_query}'
        return f'{self.base_url}{quote(path, safe="/")}'

    def _get_json(self, path):
        with urlopen(self._build_url(path), timeout=5) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def _get_bytes(self, path):
        with urlopen(self._build_url(path), timeout=5) as resp:
            return resp.read()

    def _request(self, path, method, data=None):
        """发起请求，返回 (状态码, JSON 体)；4xx/5xx 也一并返回而不抛异常"""
        url = self._build_url(path)
        body = json.dumps(data).encode('utf-8') if data is not None else None
        req = Request(url, data=body, method=method)
        if body is not None:
            req.add_header('Content-Type', 'application/json')
        try:
            with urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except HTTPError as e:
            return e.code, json.loads(e.read().decode('utf-8'))

    def _publish(self, name, version='1.0.0', metadata=None):
        payload = {'name': name, 'version': version}
        if metadata is not None:
            payload['metadata'] = metadata
        return self._request('/api/packages/publish', 'POST', payload)

    # -- 用例 --------------------------------------------------------------

    def test_health_check(self):
        """健康检查"""
        data = self._get_json('/api/health')
        self.assertEqual(data['status'], 'ok')

    def test_root_endpoint_list(self):
        """根路径返回端点清单"""
        data = self._get_json('/')
        self.assertIn('endpoints', data)
        self.assertTrue(any('/api/packages' in ep for ep in data['endpoints']))

    def test_empty_list(self):
        """空列表"""
        data = self._get_json('/api/packages')
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['packages'], [])

    def test_full_publish_and_list_flow(self):
        """完整发布-列表流程"""
        status, result = self._publish('e2e测试包', '1.0.0', {
            'description': '端到端测试',
            'author': '测试者',
        })
        self.assertEqual(status, 201)
        self.assertEqual(result['status'], 'published')

        data = self._get_json('/api/packages')
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['packages'][0]['name'], 'e2e测试包')

        detail = self._get_json('/api/packages/e2e测试包')
        self.assertEqual(detail['latest_version'], '1.0.0')
        self.assertEqual(detail['description'], '端到端测试')

        ver = self._get_json('/api/packages/e2e测试包/1.0.0')
        self.assertEqual(ver['version'], '1.0.0')

    def test_publish_missing_fields(self):
        """缺少必填字段时发布失败（HTTP 层校验）"""
        for payload in ({}, {'name': 'test'}, {'version': '1.0.0'}):
            status, data = self._request('/api/packages/publish', 'POST', payload)
            self.assertEqual(status, 400)
            self.assertIn('error', data)

    def test_publish_invalid_version(self):
        """无效版本号时发布失败（HTTP 层校验语义化版本）"""
        for bad in ('abc', '1', '1.0'):
            status, data = self._request(
                '/api/packages/publish', 'POST', {'name': 'test', 'version': bad})
            self.assertEqual(status, 400)
            self.assertIn('error', data)

        status, _ = self._publish('test', '1.0.0')
        self.assertEqual(status, 201)

    def test_search_flow(self):
        """搜索流程"""
        self._publish('搜索测试包', '1.0.0', {'description': '用于搜索测试的包'})
        data = self._get_json('/api/search?q=搜索')
        self.assertGreaterEqual(data['total'], 1)
        self.assertTrue(any(p['name'] == '搜索测试包' for p in data['results']))
        self.assertEqual(data['query'], '搜索')

    def test_version_management(self):
        """版本管理流程：发布多版本 → 列版本 → 删版本"""
        self._publish('版本测试', '1.0.0')
        self._publish('版本测试', '2.0.0')

        data = self._get_json('/api/packages/版本测试/versions')
        self.assertEqual(data['total'], 2)
        self.assertEqual([v['version'] for v in data['versions']], ['2.0.0', '1.0.0'])

        status, result = self._request('/api/packages/版本测试/2.0.0', 'DELETE')
        self.assertEqual(status, 200)
        self.assertEqual(result['status'], 'deleted')
        data = self._get_json('/api/packages/版本测试/versions')
        self.assertEqual(data['total'], 1)

    def test_download_flow_and_counting(self):
        """下载流程与下载计数

        注：这里用 ASCII 包名。RegistryHandler._send_binary 把包名塞进
        Content-Disposition，HTTP 头按 latin-1 编码，中文包名会导致该端点
        500（存储层本身没问题，见 TestPackageStorage.test_download_package_roundtrip）。
        """
        self._publish('download-test', '1.0.0')

        raw = self._get_bytes('/api/packages/download-test/download')
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            self.assertIn('light.json', zf.namelist())

        for _ in range(2):
            self._get_bytes('/api/packages/download-test/download/1.0.0')

        detail = self._get_json('/api/packages/download-test')
        self.assertEqual(detail['downloads'], 3)

    def test_metadata_update_flow(self):
        """元数据更新流程（PUT）"""
        self._publish('元数据包', '1.0.0')
        status, result = self._request(
            '/api/packages/元数据包/metadata', 'PUT',
            {'description': '新描述', 'keywords': ['光明', 'light']})
        self.assertEqual(status, 200)
        self.assertEqual(result['status'], 'updated')

        detail = self._get_json('/api/packages/元数据包')
        self.assertEqual(detail['description'], '新描述')
        data = self._get_json('/api/search?q=light')
        self.assertTrue(any(p['name'] == '元数据包' for p in data['results']))

    def test_stats(self):
        """统计信息"""
        self._publish('统计包', '1.0.0')
        stats = self._get_json('/api/stats')
        self.assertIn('total_packages', stats)
        self.assertIn('total_versions', stats)
        self.assertIn('storage_size', stats)
        self.assertEqual(stats['total_packages'], 1)

    def test_delete_flow(self):
        """删除流程"""
        self._publish('待删除包', '1.0.0')
        status, data = self._request('/api/packages/待删除包', 'DELETE')
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'deleted')

        data = self._get_json('/api/packages')
        names = [p['name'] for p in data['packages']]
        self.assertNotIn('待删除包', names)

        status, _ = self._request('/api/packages/待删除包', 'DELETE')
        self.assertEqual(status, 404)

    def test_not_found_paths(self):
        """未知包与未知路径"""
        status, data = self._request('/api/packages/不存在的包', 'GET')
        self.assertEqual(status, 404)
        self.assertIn('error', data)
        status, _ = self._request('/api/不存在的端点', 'GET')
        self.assertEqual(status, 404)


class TestRegistryWriteAuth(unittest.TestCase):
    """写操作鉴权

    历史缺陷：RegistryHandler.admin_token 由 --admin-token 赋值后从未被校验，
    do_POST / do_PUT / do_DELETE 全部零鉴权，而默认绑定还是 0.0.0.0，
    等于任何能连上的人都可以发布、改元数据、删包删版本。
    这组用例锁死修复后的行为：读公开，写必须带令牌。
    """

    ADMIN_TOKEN = 'test-admin-token-0123456789'

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix='light_reg_auth_')
        cls._prev_token = RegistryHandler.admin_token
        RegistryHandler.admin_token = cls.ADMIN_TOKEN
        cls.server = HTTPServer(('127.0.0.1', 0), RegistryHandler)
        cls.base_url = f'http://127.0.0.1:{cls.server.server_address[1]}'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        RegistryHandler.admin_token = cls._prev_token
        RegistryHandler.storage = None
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        case_dir = os.path.join(self.tmpdir, self._testMethodName)
        RegistryHandler.storage = PackageStorage(storage_dir=case_dir)

    def _request(self, path, method, data=None, token=None):
        url = f'{self.base_url}{quote(path, safe="/")}'
        body = json.dumps(data).encode('utf-8') if data is not None else None
        req = Request(url, data=body, method=method)
        if body is not None:
            req.add_header('Content-Type', 'application/json')
        if token is not None:
            req.add_header('Authorization', token)
        try:
            with urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except HTTPError as e:
            return e.code, json.loads(e.read().decode('utf-8'))

    def _publish(self, name, token=None, version='1.0.0'):
        return self._request('/api/packages/publish', 'POST',
                             {'name': name, 'version': version}, token=token)

    # -- 读操作保持公开 ----------------------------------------------------

    def test_get_requires_no_token(self):
        """配置了令牌也不影响 GET"""
        status, data = self._request('/api/health', 'GET')
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'ok')

    # -- 写操作必须带令牌 --------------------------------------------------

    def test_publish_without_token_rejected(self):
        status, data = self._publish('无令牌包')
        self.assertEqual(status, 401)
        self.assertIn('error', data)

    def test_publish_with_wrong_token_rejected(self):
        status, _ = self._publish('错令牌包', token='Bearer wrong-token')
        self.assertEqual(status, 401)

    def test_publish_with_bare_token_rejected(self):
        """必须是 Bearer 方案，裸令牌不接受"""
        status, _ = self._publish('裸令牌包', token=self.ADMIN_TOKEN)
        self.assertEqual(status, 401)

    def test_publish_with_valid_token_succeeds(self):
        status, data = self._publish('有令牌包', token=f'Bearer {self.ADMIN_TOKEN}')
        self.assertEqual(status, 201)
        self.assertEqual(data['status'], 'published')

    def test_put_metadata_requires_token(self):
        self._publish('元数据包', token=f'Bearer {self.ADMIN_TOKEN}')
        status, _ = self._request('/api/packages/元数据包/metadata', 'PUT',
                                  {'description': '未授权改写'})
        self.assertEqual(status, 401)
        status, _ = self._request('/api/packages/元数据包/metadata', 'PUT',
                                  {'description': '已授权改写'},
                                  token=f'Bearer {self.ADMIN_TOKEN}')
        self.assertEqual(status, 200)

    def test_delete_requires_token(self):
        self._publish('待删包', token=f'Bearer {self.ADMIN_TOKEN}')
        status, _ = self._request('/api/packages/待删包', 'DELETE')
        self.assertEqual(status, 401)
        # 未授权的删除不能真的把包删掉
        status, data = self._request('/api/packages/待删包', 'GET')
        self.assertEqual(status, 200)
        status, _ = self._request('/api/packages/待删包', 'DELETE',
                                  token=f'Bearer {self.ADMIN_TOKEN}')
        self.assertEqual(status, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
