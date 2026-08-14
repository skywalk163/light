"""
lightpub P1 桥接模块测试 - HTTP客户端 + Socket + SQLite

验证 P1 包可通过 lightpub 加载器导入并使用。
"""
import sys
import os
import threading
import tempfile
import socket as _socket
import unittest
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'stdlib'))


def _has_network(timeout=2):
    """检查网络连接是否可用（尝试连接 httpbin.org）。

    仅当请求成功且返回 2xx/3xx 状态码时视为网络可用；
    超时、连接失败或 5xx 错误（如 503）均视为不可用，
    避免在代理/防火墙环境下因 httpbin 不可达而误判。
    """
    try:
        with urllib.request.urlopen('https://httpbin.org/get', timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except (urllib.error.URLError, OSError):
        return False


class TestHTTP客户端Bridge(unittest.TestCase):
    """测试 HTTP客户端 桥接模块"""

    @classmethod
    def setUpClass(cls):
        from lightpub import HTTP客户端
        cls.mod = HTTP客户端

    def test_导入(self):
        self.assertIsNotNone(self.mod)

    @unittest.skipIf(not _has_network(), "无网络连接")
    def test_HTTP获取(self):
        # skipIf 在模块加载时求值，运行时网络状态可能已变化，
        # 此处再次检查，网络不可用时优雅跳过而非失败
        if not _has_network():
            self.skipTest("网络不可用（httpbin.org 不可达）")
        resp = self.mod.HTTP获取('https://httpbin.org/get')
        self.assertEqual(resp.status, 200)
        self.assertTrue(len(resp.body) > 0)

    def test_URL编码解码(self):
        encoded = self.mod.URL编码('hello world')
        self.assertIn('hello', encoded)
        decoded = self.mod.URL解码(encoded)
        self.assertEqual(decoded, 'hello world')

    def test_拼接URL(self):
        url = self.mod.拼接URL('http://example.com', {'q': 'test', 'page': 1})
        self.assertIn('q=test', url)
        self.assertIn('page=1', url)

    @unittest.skipIf(not _has_network(), "无网络连接")
    def test_获取JSON(self):
        # skipIf 在模块加载时求值，运行时网络状态可能已变化
        if not _has_network():
            self.skipTest("网络不可用（httpbin.org 不可达）")
        data = self.mod.获取JSON('https://httpbin.org/get')
        self.assertIsNotNone(data)
        self.assertIn('url', data)

    @unittest.skipIf(not _has_network(), "无网络连接")
    def test_HTTP提交(self):
        resp = self.mod.发送JSON('https://httpbin.org/post', {'key': 'value'}, method='POST')
        self.assertEqual(resp.status, 200)
        self.assertIn('key', resp.body)


class TestSocketBridge(unittest.TestCase):
    """测试 Socket 桥接模块"""

    @classmethod
    def setUpClass(cls):
        from lightpub import Socket
        cls.mod = Socket

    def test_导入(self):
        self.assertIsNotNone(self.mod)

    def test_创建TCPSocket(self):
        s = self.mod.创建TCPSocket()
        self.assertIsNotNone(s)
        self.assertTrue(self.mod.sock有效(s))
        self.mod.关闭Socket(s)

    def test_创建UDPSocket(self):
        s = self.mod.创建UDPSocket()
        self.assertIsNotNone(s)
        self.assertTrue(self.mod.sock有效(s))
        self.mod.关闭Socket(s)

    def test_TCP_echo(self):
        """TCP 回显测试：服务端 + 客户端"""
        # 获取空闲端口
        s = _socket.socket(self.mod.AF_INET, self.mod.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        s.close()

        ready = threading.Event()
        results = []

        def server():
            ss = self.mod.创建TCPSocket()
            self.mod.绑定(ss, '127.0.0.1', port)
            self.mod.监听(ss, 1)
            ready.set()
            result = self.mod.接受(ss)
            self.assertTrue(result.成功)
            conn = result.连接
            data = self.mod.接收(conn, 1024)
            self.mod.发送(conn, 'ECHO:' + data)
            self.mod.关闭连接(conn)
            self.mod.关闭Socket(ss)

        t = threading.Thread(target=server)
        t.start()
        self.assertTrue(ready.wait(timeout=3))

        # 客户端
        conn = self.mod.连接TCP('127.0.0.1', port)
        self.mod.发送(conn, 'hello')
        resp = self.mod.接收(conn, 1024)
        self.assertEqual(resp, 'ECHO:hello')
        self.mod.关闭连接(conn)
        t.join()

    def test_常量(self):
        self.assertEqual(self.mod.AF_INET, _socket.AF_INET)
        self.assertEqual(self.mod.SOCK_STREAM, _socket.SOCK_STREAM)
        self.assertEqual(self.mod.SOCK_DGRAM, _socket.SOCK_DGRAM)

    def test_主机名转IP(self):
        ip = self.mod.将主机名转为IP('localhost')
        self.assertIsInstance(ip, str)
        self.assertTrue(len(ip) > 0)


class TestSQLiteBridge(unittest.TestCase):
    """测试 SQLite 桥接模块"""

    @classmethod
    def setUpClass(cls):
        from lightpub import SQLite
        cls.mod = SQLite

    def test_导入(self):
        self.assertIsNotNone(self.mod)

    def test_打开关闭数据库(self):
        tmp = tempfile.mktemp(suffix='.db')
        try:
            db = self.mod.打开数据库(tmp)
            self.assertTrue(db.opened)
            self.mod.关闭数据库(db)
            self.assertFalse(db.opened)
        finally:
            os.unlink(tmp)

    def test_创建表并插入(self):
        tmp = tempfile.mktemp(suffix='.db')
        try:
            db = self.mod.打开数据库(tmp)
            self.mod.执行SQL(db, 'CREATE TABLE test (id INT, name TEXT)')
            self.mod.执行SQL(db, 'INSERT INTO test VALUES (?, ?)', (1, 'hello'))
            self.mod.执行SQL(db, 'INSERT INTO test VALUES (?, ?)', (2, 'world'))
            self.mod.关闭数据库(db)
        finally:
            os.unlink(tmp)

    def test_查询(self):
        tmp = tempfile.mktemp(suffix='.db')
        try:
            db = self.mod.打开数据库(tmp)
            self.mod.执行SQL(db, 'CREATE TABLE test (id INT, name TEXT)')
            self.mod.执行SQL(db, 'INSERT INTO test VALUES (?, ?)', (1, 'hello'))
            self.mod.执行SQL(db, 'INSERT INTO test VALUES (?, ?)', (2, 'world'))

            result = self.mod.查询(db, 'SELECT * FROM test ORDER BY id')
            self.assertEqual(result.row_count, 2)
            self.assertEqual(result.col_names, ['id', 'name'])
            self.assertEqual(result.rows[0], [1, 'hello'])
            self.assertEqual(result.rows[1], [2, 'world'])

            row = self.mod.查询单条(db, 'SELECT * FROM test WHERE id=?', (1,))
            self.assertIsNotNone(row)
            self.assertEqual(row['name'], 'hello')

            rows = self.mod.查询所有(db, 'SELECT * FROM test')
            self.assertEqual(len(rows), 2)
            self.mod.关闭数据库(db)
        finally:
            os.unlink(tmp)

    def test_事务(self):
        tmp = tempfile.mktemp(suffix='.db')
        try:
            db = self.mod.打开数据库(tmp)
            self.mod.执行SQL(db, 'CREATE TABLE test (id INT)')
            self.mod.开始事务(db)
            self.mod.执行SQL(db, 'INSERT INTO test VALUES (1)')
            self.mod.提交事务(db)
            result = self.mod.查询(db, 'SELECT COUNT(*) as cnt FROM test')
            first_row = result.rows[0]
            cnt_idx = result.col_names.index('cnt') if 'cnt' in result.col_names else 0
            self.assertEqual(first_row[cnt_idx], 1)
            self.mod.关闭数据库(db)
        finally:
            os.unlink(tmp)

    def test_表是否存在(self):
        tmp = tempfile.mktemp(suffix='.db')
        try:
            db = self.mod.打开数据库(tmp)
            self.mod.执行SQL(db, 'CREATE TABLE mytable (id INT)')
            self.assertTrue(self.mod.表是否存在(db, 'mytable'))
            self.assertFalse(self.mod.表是否存在(db, 'nonexistent'))
            self.mod.关闭数据库(db)
        finally:
            os.unlink(tmp)

    def test_获取所有表(self):
        tmp = tempfile.mktemp(suffix='.db')
        try:
            db = self.mod.打开数据库(tmp)
            self.mod.执行SQL(db, 'CREATE TABLE t1 (id INT)')
            self.mod.执行SQL(db, 'CREATE TABLE t2 (id INT)')
            tables = self.mod.获取所有表(db)
            self.assertIn('t1', tables)
            self.assertIn('t2', tables)
            self.mod.关闭数据库(db)
        finally:
            os.unlink(tmp)

    def test_最后插入ID(self):
        tmp = tempfile.mktemp(suffix='.db')
        try:
            db = self.mod.打开数据库(tmp)
            self.mod.执行SQL(db, 'CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
            self.mod.执行SQL(db, 'INSERT INTO test (name) VALUES (?)', ('hello',))
            last_id = self.mod.最后插入ID(db)
            self.assertGreater(last_id, 0)
            self.mod.关闭数据库(db)
        finally:
            os.unlink(tmp)


if __name__ == '__main__':
    unittest.main(verbosity=2)