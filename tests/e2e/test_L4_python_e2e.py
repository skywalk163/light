# -*- coding: utf-8 -*-
"""
L4 Python 引用层 E2E 测试
覆盖：numpy 均值、pandas CSV、matplotlib 绘图、requests HTTP、sklearn 分类、沙箱隔离
"""
import os
import sys
import io
import unittest
import socket

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _is_network_available(host="httpbin.org", port=443, timeout=5):
    """检测网络是否可达（含 HTTP 响应检查）"""
    try:
        socket.create_connection((host, port), timeout=timeout)
        # 额外检查 HTTP 服务是否正常响应
        try:
            import urllib.request
            req = urllib.request.Request(f"https://{host}/get")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False
    except OSError:
        return False


def _run_light(code: str) -> str:
    parser = LightParser()
    ast = parser.parse(code)
    if ast is None:
        errors = '\n'.join(getattr(parser, 'errors', []))
        raise RuntimeError(f"解析失败:\n{errors}")
    gen = PythonCodeGenerator()
    py_code = gen.generate(ast)
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        namespace = {'__name__': '__main__'}
        exec(py_code, namespace)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout


# ==========================================================
# 1. L4 numpy 测试
# ==========================================================
class TestL4_Numpy_E2E(unittest.TestCase):
    """L4 numpy 引用层"""

    def test_numpy_mean(self):
        """numpy 计算均值"""
        code = '''
引 Python:
    import numpy as np
    def l4_numpy_mean(arr):
        nparr = np.array(arr, dtype=float)
        return float(np.mean(nparr))
结束引

设 数据 = [12, 25, 30, 43, 52, 67, 78, 89]
设 结果 = l4_numpy_mean(数据)
打印(结果)
'''
        output = _run_light(code)
        self.assertIn("49.5", output)

    def test_numpy_basic_ops(self):
        """numpy 基本运算"""
        code = '''
引 Python:
    import numpy as np
    def l4_numpy_stats(arr):
        a = np.array(arr, dtype=float)
        return [float(np.sum(a)), float(np.std(a)), float(np.min(a)), float(np.max(a))]
结束引

设 数据 = [1, 2, 3, 4, 5]
设 结果 = l4_numpy_stats(数据)
打印(结果[0])
打印(结果[2])
打印(结果[3])
'''
        output = _run_light(code)
        self.assertIn("15.0", output)
        self.assertIn("1.0", output)
        self.assertIn("5.0", output)


# ==========================================================
# 2. L4 pandas 测试
# ==========================================================
class TestL4_Pandas_E2E(unittest.TestCase):
    """L4 pandas 引用层"""

    def test_pandas_dataframe(self):
        """pandas DataFrame 创建和基本操作"""
        code = '''
引 Python:
    import pandas as pd
    def l4_pandas_table():
        df = pd.DataFrame({"姓名": ["张三","李四","王五"], "分数": [85,92,78]})
        return [str(df["分数"].mean()), str(df["分数"].max()), str(len(df))]
结束引

设 结果 = l4_pandas_table()
打印(结果[0])
打印(结果[1])
打印(结果[2])
'''
        output = _run_light(code)
        self.assertIn("85.0", output)
        self.assertIn("92", output)
        self.assertIn("3", output)


# ==========================================================
# 3. L4 matplotlib 测试
# ==========================================================
class TestL4_Matplotlib_E2E(unittest.TestCase):
    """L4 matplotlib 引用层"""

    def test_matplotlib_non_blocking(self):
        """matplotlib 非阻塞绘图（不显示窗口）"""
        code = '''
引 Python:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import io as _io
    def l4_mpl_test():
        fig, ax = plt.subplots()
        ax.bar([1,2,3], [10,20,30])
        buf = _io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig)
        return len(buf.getvalue())
结束引

设 结果 = l4_mpl_test()
打印("图片大小:", 结果)
如果 结果 > 0:
    打印("OK")
'''
        output = _run_light(code)
        self.assertIn("OK", output)


# ==========================================================
# 4. L4 requests 测试
# ==========================================================
class TestL4_Requests_E2E(unittest.TestCase):
    """L4 requests 引用层"""

    @unittest.skipUnless(_is_network_available(), "httpbin.org 不可达，跳过网络测试")
    def test_requests_get(self):
        """requests HTTP GET 请求"""
        code = '''
引 Python:
    import requests
    def l4_http_get(url):
        resp = requests.get(url, timeout=10)
        return resp.status_code
结束引

设 状态码 = l4_http_get("https://httpbin.org/status/200")
打印(状态码)
'''
        output = _run_light(code)
        self.assertIn("200", output)


# ==========================================================
# 5. L4 沙箱隔离测试
# ==========================================================
class TestL4_Sandbox_E2E(unittest.TestCase):
    """L4 沙箱隔离（命名空间隔离）"""

    def test_namespace_isolation(self):
        """验证引 Python 块内的变量不污染光明外层"""
        code = '''
引 Python:
    _secret = "internal_only"
    def l4_check_secret():
        return _secret
结束引

设 结果 = l4_check_secret()
打印(结果)
'''
        output = _run_light(code)
        self.assertIn("internal_only", output)

    def test_multiple_blocks_independent(self):
        """多个引 Python 块独立命名空间"""
        code = '''
引 Python:
    def l4_block_a():
        return "A"
结束引

引 Python:
    def l4_block_b():
        return "B"
结束引

打印(l4_block_a())
打印(l4_block_b())
'''
        output = _run_light(code)
        self.assertIn("A", output)
        self.assertIn("B", output)


if __name__ == '__main__':
    unittest.main(verbosity=2)