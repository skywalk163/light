# -*- coding: utf-8 -*-
"""
L4 C/Go/MoonBit 编译封装 E2E 测试
覆盖：C 编译求和、Go 编译斐波那契、MoonBit 编译排序、工具链缺失优雅降级
"""
import os
import sys
import io
import unittest

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _run_light(code: str) -> str:
    return _run_light_ns(code)[0]


def _run_light_ns(code: str):
    """执行光明代码，返回 (stdout, 执行后的命名空间)。

    返回命名空间是为了让测试能直接拿到 L4 绑定进去的 ctypes 函数对象，
    做「真调用取返回值」的断言，而不是只对生成代码做字符串匹配。
    """
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
        return sys.stdout.getvalue(), namespace
    finally:
        sys.stdout = old_stdout


def _find_c_compiler():
    """按 L4 发射器的候选顺序探测真实可执行的 C 编译器，返回 (名字, 绝对路径) 或 None。"""
    import shutil
    for _cand in ['gcc', 'cc', 'clang']:
        _p = shutil.which(_cand)
        if _p:
            return _cand, _p
    return None



def _has_toolchain(tool: str) -> bool:
    """检查工具链是否可用"""
    import subprocess
    try:
        subprocess.run([tool, '--version'], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


# ==========================================================
# 1. L4 C 编译测试
# ==========================================================
class TestL4_C_Compile_E2E(unittest.TestCase):
    """L4 C 编译封装"""

    def test_c_compilation_preserves_code(self):
        """验证引 C 块被正确解析（不要求实际编译）"""
        code = '''
引 C:
    int add(int a, int b) {
        return a + b;
    }
结束引

打印("C 块解析成功")
'''
        output = _run_light(code)
        self.assertIn("C 块解析成功", output)

    def test_c_compilation_fallback(self):
        """C 编译失败时优雅降级"""
        # 这个测试验证代码生成器能处理 C 块，即使没有 gcc
        code = '''
引 C:
    double quick_sum(double* arr, int n) {
        double s = 0.0;
        for (int i = 0; i < n; i++) s += arr[i];
        return s;
    }
结束引

打印("C 编译块已生成")
'''
        output = _run_light(code)
        self.assertIn("C 编译块已生成", output)

    def test_c_真编译真调用_取值正确(self):
        """引 C：真编译成动态库、真通过 ctypes 调用、断言返回值。

        覆盖 int 与 double 两种返回类型（restype/argtypes 绑定的两条分支），
        并顺带守住 Windows 回退路径——本机只有 clang/MSVC target 时，
        GNU 风格那条命令必然失败（-fPIC 非法），能取到值就说明回退真的生效了。
        """
        _cc = _find_c_compiler()
        if _cc is None:
            self.skipTest(
                "本机 PATH 上 shutil.which 找不到 gcc / cc / clang 中的任何一个，"
                "无 C 编译器可用，无法真编译"
            )
        code = '''
引 C:
    int fact(int n) {
        int r = 1;
        for (int i = 2; i <= n; i++) r *= i;
        return r;
    }

    double tri(double h) {
        return 6.0 * h / 2.0;
    }
结束引

打印("C 已就绪")
'''
        output, ns = _run_light_ns(code)
        self.assertIn("C 已就绪", output)

        # 必须真的绑上了名字（否则下面取不到函数对象）
        for _name in ('fact', 'tri'):
            self.assertIn(_name, ns, f"{_name} 未被绑定到命名空间")

        fact = ns['fact']
        tri = ns['tri']

        # 真调用，拿真返回值
        got_fact = fact(5)
        got_tri = tri(2.5)

        self.assertNotIsInstance(
            got_fact, str,
            f"fact 返回了占位字符串（说明编译/加载失败被降级吞掉）: {got_fact!r}"
        )
        self.assertNotIsInstance(
            got_tri, str,
            f"tri 返回了占位字符串（说明编译/加载失败被降级吞掉）: {got_tri!r}"
        )
        self.assertEqual(120, got_fact, f"fact(5) 应为 120，实得 {got_fact!r}（编译器: {_cc[1]}）")
        self.assertAlmostEqual(7.5, got_tri, places=9,
                               msg=f"tri(2.5) 应为 7.5，实得 {got_tri!r}（编译器: {_cc[1]}）")



# ==========================================================
# 2. L4 Go 编译测试
# ==========================================================
class TestL4_Go_Compile_E2E(unittest.TestCase):
    """L4 Go 编译封装"""

    def test_go_compilation_preserves_code(self):
        """验证引 Go 块被正确解析"""
        code = '''
引 Go:
    func fib(n int) int {
        if n <= 1 {
            return n
        }
        return fib(n-1) + fib(n-2)
    }
结束引

打印("Go 块解析成功")
'''
        output = _run_light(code)
        self.assertIn("Go 块解析成功", output)


# ==========================================================
# 3. L4 MoonBit 编译测试
# ==========================================================
class TestL4_MoonBit_Compile_E2E(unittest.TestCase):
    """L4 MoonBit 编译封装"""

    def test_moonbit_compilation_preserves_code(self):
        """验证引 MoonBit 块被正确解析"""
        code = '''
引 MoonBit:
    fn quicksort(arr: Array[Int], low: Int, high: Int) -> Unit {
        if low < high {
            let pi = partition(arr, low, high)
            quicksort(arr, low, pi - 1)
            quicksort(arr, pi + 1, high)
        }
    }
结束引

打印("MoonBit 块解析成功")
'''
        output = _run_light(code)
        self.assertIn("MoonBit 块解析成功", output)


# ==========================================================
# 4. 多语言混合测试
# ==========================================================
class TestL4_MultiLang_E2E(unittest.TestCase):
    """L4 多语言混合"""

    def test_mixed_python_c_blocks(self):
        """Python 和 C 块混合使用"""
        code = '''
引 Python:
    def l4_py_hello():
        return "Hello from Python"
结束引

引 C:
    int c_answer() {
        return 42;
    }
结束引

打印(l4_py_hello())
打印("C 块已定义")
'''
        output = _run_light(code)
        self.assertIn("Hello from Python", output)
        self.assertIn("C 块已定义", output)

    def test_mixed_python_go_blocks(self):
        """Python 和 Go 块混合使用"""
        code = '''
引 Python:
    def l4_py_version():
        return "Python 3.x"
结束引

引 Go:
    func go_version() string {
        return "Go 1.x"
    }
结束引

打印(l4_py_version())
打印("Go 块已定义")
'''
        output = _run_light(code)
        self.assertIn("Python 3.x", output)
        self.assertIn("Go 块已定义", output)


if __name__ == '__main__':
    unittest.main(verbosity=2)