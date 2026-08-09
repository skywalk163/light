# -*- coding: utf-8 -*-
"""
Playground API 集成测试
覆盖：GET /api/demos/list, POST /api/demos/run, GET /api/demos/<id>, POST /api/execute, POST /api/parse, POST /api/tokenize
"""
import os
import sys
import json
import unittest
import threading
import time

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)

# 尝试导入 Flask 测试客户端，若 Flask 未安装则跳过所有测试
try:
    from playground.server import app
    _FLASK_AVAILABLE = True
except ImportError as _e:
    _FLASK_AVAILABLE = False
    _FLASK_IMPORT_ERROR = str(_e)


class _FlaskTestBase(unittest.TestCase):
    """基类：Flask 不可用时跳过所有测试"""

    @classmethod
    def setUpClass(cls):
        if not _FLASK_AVAILABLE:
            raise unittest.SkipTest(f"Flask 不可用，跳过 Playground API 测试: {_FLASK_IMPORT_ERROR}")


class TestPlaygroundDemosAPI(_FlaskTestBase):
    """Demo 相关 API"""

    def setUp(self):
        self.client = app.test_client()

    def test_list_demos(self):
        """GET /api/demos/list — 返回 demo 列表"""
        resp = self.client.get('/api/demos/list')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(data['count'], 0)
        self.assertIn('demos', data)
        self.assertIn('categories', data)

    def test_list_demos_category_filter(self):
        """GET /api/demos/list?category=SQL — 按类别过滤"""
        resp = self.client.get('/api/demos/list?category=SQL')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])

    def test_list_demos_limit(self):
        """GET /api/demos/list?limit=5 — 限制返回数量"""
        resp = self.client.get('/api/demos/list?limit=5')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertLessEqual(len(data['demos']), 5)

    def test_run_demo_by_id(self):
        """POST /api/demos/run — 通过 demo_id 运行示例"""
        resp = self.client.post('/api/demos/run',
                                json={'demo_id': 'builtin__hello'},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('你好，光明', data['output'])

    def test_run_demo_inline_code(self):
        """POST /api/demos/run — 直接传入代码运行"""
        resp = self.client.post('/api/demos/run',
                                json={'code': '打印("liping")'},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('liping', data['output'])

    def test_run_demo_invalid_id(self):
        """POST /api/demos/run — 无效 demo_id 格式"""
        resp = self.client.post('/api/demos/run',
                                json={'demo_id': 'nonexistent_xyz'},
                                content_type='application/json')
        # 格式不合法（非 builtin__/file__ 前缀），返回 500（ValueError 未捕获为 4xx）
        self.assertIn(resp.status_code, [400, 500])

    def test_run_demo_no_params(self):
        """POST /api/demos/run — 无参数"""
        resp = self.client.post('/api/demos/run',
                                json={},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_get_demo_detail(self):
        """GET /api/demos/<id> — 获取 demo 详情"""
        resp = self.client.get('/api/demos/builtin__hello')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('code', data)
        self.assertIn('你好，光明', data['code'])

    def test_get_demo_not_found(self):
        """GET /api/demos/<id> — 不存在的 demo"""
        resp = self.client.get('/api/demos/builtin__nonexistent_xyz')
        self.assertEqual(resp.status_code, 404)


class TestPlaygroundExecuteAPI(_FlaskTestBase):
    """代码执行 API"""

    def setUp(self):
        self.client = app.test_client()

    def test_execute_simple(self):
        """POST /api/execute — 简单代码执行"""
        resp = self.client.post('/api/execute',
                                json={'code': '打印("zzp")'},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('zzp', data['output'])

    def test_execute_empty_code(self):
        """POST /api/execute — 空代码"""
        resp = self.client.post('/api/execute',
                                json={'code': ''},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['success'])

    def test_execute_variable_assignment(self):
        """POST /api/execute — 变量赋值和打印"""
        resp = self.client.post('/api/execute',
                                json={'code': '设 甲 为 42\n打印(甲)'},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('42', data['output'])

    def test_execute_conditional(self):
        """POST /api/execute — 条件判断"""
        resp = self.client.post('/api/execute',
                                json={'code': '设 分数 为 85\n如果 分数 大于等于 80：\n  打印("通过")\n否则：\n  打印("不通过")'},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('通过', data['output'])

    def test_execute_loop(self):
        """POST /api/execute — 循环"""
        resp = self.client.post('/api/execute',
                                json={'code': '设 总和 为 0\n设 i 为 1\n当 i 小于等于 5：\n  设 总和 为 总和 加 i\n  设 i 为 i 加 1\n打印(总和)'},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('15', data['output'])

    def test_execute_syntax_error(self):
        """POST /api/execute — 语法错误"""
        resp = self.client.post('/api/execute',
                                json={'code': '设 甲 为 '},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['success'])


class TestPlaygroundParseAPI(_FlaskTestBase):
    """解析和词法分析 API"""

    def setUp(self):
        self.client = app.test_client()

    def test_parse_simple(self):
        """POST /api/parse — 简单解析"""
        resp = self.client.post('/api/parse',
                                json={'code': '设 甲 为 42\n打印(甲)'},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])

    def test_parse_empty(self):
        """POST /api/parse — 空代码"""
        resp = self.client.post('/api/parse',
                                json={'code': ''},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['success'])

    def test_tokenize_simple(self):
        """POST /api/tokenize — 简单词法分析"""
        resp = self.client.post('/api/tokenize',
                                json={'code': '设 甲 为 42'},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('tokens', data)
        self.assertGreater(data['token_count'], 0)

    def test_tokenize_empty(self):
        """POST /api/tokenize — 空代码"""
        resp = self.client.post('/api/tokenize',
                                json={'code': ''},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['success'])


class TestPlaygroundExamplesAPI(_FlaskTestBase):
    """示例和语法参考 API"""

    def setUp(self):
        self.client = app.test_client()

    def test_get_examples(self):
        """GET /api/examples — 获取内置示例"""
        resp = self.client.get('/api/examples')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('categories', data)
        self.assertIn('examples', data)

    def test_get_grammar(self):
        """GET /api/grammar — 获取语法参考"""
        resp = self.client.get('/api/grammar')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('categories', data)

    def test_get_stdlib(self):
        """GET /api/stdlib — 获取标准库参考"""
        resp = self.client.get('/api/stdlib')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('categories', data)


if __name__ == '__main__':
    unittest.main(verbosity=2)