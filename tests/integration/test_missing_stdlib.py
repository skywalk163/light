# -*- coding: utf-8 -*-
"""
段言「stdlib 缺失」场景的回归测试

背景
----
曾有一类失败（对外表现为「2/10 fail」）只在「抽取/部署环境只带了 src、没带 stdlib」
时出现：
  - lists 失败：AttributeError: module '_light_builtin' has no attribute '列表排序'
    —— 运行时解析不到 stdlib/builtins.py，退回到代码生成器的内联 lambda fallback，
       fallback 漏掉了 列表排序/列表反转/追加文件 等 builtin。
  - files 失败：ModuleNotFoundError: No module named '文件系统'
    —— 段言程序首行 `导入 文件系统。`，但 stdlib 不在 sys.path 上，import 找不到模块。

修复（src/code_generator.py、src/code_generator_unified.py 的 _light_builtin 定义之后）
在 stdlib 物理缺失时才补齐常用 builtin，并注册一个合成的 `文件系统` 模块，使上述代码
即便在没有 stdlib 的运行环境中也能跑通。

本测试模拟该场景：
  1) 进程内（unified 后端）—— chdir 到一个不含 stdlib 的临时目录，使生成的代码
     通过 getcwd() 解析不到 stdlib，从而触发 fallback + 兜底补齐逻辑。
  2) 端到端（src 后端，`duan run`）—— 把 cli/ 与 src/ 拷进一个临时根目录（不含
     stdlib），像「只抽取 src」那样运行原 two 个失败用例，断言 rc==0 且输出正确。

两类测试都在「stdlib 缺失」前提下断言原先会崩的行为现在可用，从而固守修复。
"""

import os
import sys
import io
import shutil
import tempfile
import contextlib
import unittest
import subprocess

# 项目路径：tests/integration/test_missing_stdlib.py -> 上溯三级
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC_DIR = os.path.join(_PROJECT_ROOT, 'src')
sys.path.insert(0, _SRC_DIR)


def _require_compiler():
    """返回 (Compiler, UnifiedCodeGenerator)；不可用时抛 SkipTest。"""
    try:
        from compiler import LightCompiler
        from code_generator_unified import UnifiedCodeGenerator
        return LightCompiler, UnifiedCodeGenerator
    except ImportError as e:
        raise unittest.SkipTest(f"编译器模块不可用: {e}")


def _run_unified(code):
    """用 unified 后端编译并执行段言代码，返回标准输出（去尾随空白）。"""
    Compiler, UnifiedCodeGenerator = _require_compiler()
    res = Compiler().compile(code)
    module = res.get('ast') if isinstance(res, dict) else res
    py_code = UnifiedCodeGenerator().generate(module)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(py_code, {})
    return buf.getvalue().strip()


class TestMissingStdlibUnified(unittest.TestCase):
    """进程内统一后端：cwd 不含 stdlib 时，fallback 仍应补齐 builtin 与 文件系统。"""

    @classmethod
    def setUpClass(cls):
        _require_compiler()

    def setUp(self):
        # 切到一个不含 stdlib 的临时目录，模拟「抽取器只 copy 了 src」的运行环境
        self._saved_cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp(prefix='duan_missing_stdlib_')
        os.chdir(self._tmp)
        # 清掉可能残留的 文件系统 stub，确保每次都从兜底逻辑重新注册。
        # 注意：这里会把真实的 stdlib/文件系统 也从 sys.modules 摘掉，兜底逻辑随后会
        # setdefault 一个只有少数函数的合成 stub。若不在 tearDown 里还原，后续用例
        # （如 tests/test_stdlib_complete.py::TestFileSystem）再 `from 文件系统 import`
        # 就会拿到这个残留 stub 并报
        # `ImportError: cannot import name '文件大小' from '文件系统' (unknown location)`。
        self._saved_fs_module = sys.modules.pop('文件系统', None)

    def tearDown(self):
        os.chdir(self._saved_cwd)
        shutil.rmtree(self._tmp, ignore_errors=True)
        # 还原 sys.modules['文件系统']，避免把兜底 stub 泄漏给后续用例
        sys.modules.pop('文件系统', None)
        if self._saved_fs_module is not None:
            sys.modules['文件系统'] = self._saved_fs_module

    def test_list_sort_missing_stdlib(self):
        """列表排序 在 stdlib 缺失时不应再抛 AttributeError。"""
        out = _run_unified("设 数据 为 [3, 1, 2, 5, 4]。\n列表排序(数据)。\n打印 数据。")
        self.assertEqual(out, '[1, 2, 3, 4, 5]')

    def test_list_reverse_missing_stdlib(self):
        """列表反转 在 stdlib 缺失时也应可用（原先 fallback 也漏了它）。"""
        out = _run_unified("设 数据 为 [1, 2, 3]。\n列表反转(数据)。\n打印 数据。")
        self.assertEqual(out, '[3, 2, 1]')

    def test_import_filesystem_missing_stdlib(self):
        """`导入 文件系统。` 在 stdlib 缺失时不应抛 ModuleNotFoundError。"""
        out = _run_unified(
            '导入 文件系统。\n'
            '写入文件("o.txt", "hi")。\n'
            '设 内容 为 读取文件("o.txt")。\n'
            '打印 内容。'
        )
        self.assertEqual(out, 'hi')

    def test_append_file_missing_stdlib(self):
        """追加文件 在 stdlib 缺失时应可用（原先 fallback 漏了它）。"""
        out = _run_unified(
            '写入文件("a.txt", "A")。\n'
            '追加文件("a.txt", "B")。\n'
            '打印 读取文件("a.txt")。'
        )
        self.assertEqual(out, 'AB')

    def test_list_length_missing_stdlib(self):
        """补齐项中的 列表长度 在 stdlib 缺失时也应可用。"""
        out = _run_unified(
            "设 数据 为 [1, 2, 3]。\n"
            "打印 列表长度(数据)。"
        )
        self.assertEqual(out, '3')


class TestMissingStdlibSrcBackendE2E(unittest.TestCase):
    """端到端：只抽取 cli/ + src/（无 stdlib），用 `duan run` 跑原两个失败用例。"""

    @classmethod
    def setUpClass(cls):
        # 确认 duan CLI 与 src 存在，否则跳过
        cls._cli = os.path.join(_PROJECT_ROOT, 'cli', 'duan.py')
        cls._src = os.path.join(_PROJECT_ROOT, 'src')
        if not (os.path.isfile(cls._cli) and os.path.isdir(cls._src)):
            raise unittest.SkipTest("cli/duan.py 或 src/ 不存在，跳过端到端测试")

    def _build_extraction(self):
        """构造一个只含 cli/ + src/、不含 stdlib 的临时运行根目录。"""
        root = tempfile.mkdtemp(prefix='duan_extract_')
        shutil.copytree(os.path.join(_PROJECT_ROOT, 'cli'), os.path.join(root, 'cli'))
        shutil.copytree(os.path.join(_PROJECT_ROOT, 'src'), os.path.join(root, 'src'))
        return root

    def _run_light(self, root, source):
        """在 root 内写一个 .light 源并运行 `duan run`，返回 (rc, stdout, stderr)。"""
        src_path = os.path.join(root, '_case.light')
        with open(src_path, 'w', encoding='utf-8') as f:
            f.write(source)
        env = dict(os.environ)
        env.setdefault('PYTHONIOENCODING', 'utf-8')
        env['PYTHONUTF8'] = '1'
        proc = subprocess.run(
            [sys.executable, os.path.join(root, 'cli', 'duan.py'), 'run', src_path],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            cwd=root, env=env,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

    def test_lists_exercise_runs_without_stdlib(self):
        """原 lists 失败用例在 stdlib 缺失的抽取环境中应跑通。"""
        root = self._build_extraction()
        try:
            rc, out, err = self._run_light(
                root,
                "设 数据 为 [3, 1, 2, 5, 4]。\n列表排序(数据)。\n打印 数据。",
            )
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(rc, 0, msg=f"退出码非0；stderr={err}")
        self.assertEqual(out, '[1, 2, 3, 4, 5]')

    def test_files_exercise_runs_without_stdlib(self):
        """原 files 失败用例（`导入 文件系统。`）在 stdlib 缺失的抽取环境中应跑通。"""
        root = self._build_extraction()
        try:
            rc, out, err = self._run_light(
                root,
                '导入 文件系统。\n'
                '写入文件("out.txt", "hello")。\n'
                '设 内容 为 读取文件("out.txt")。\n'
                '打印 内容。',
            )
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(rc, 0, msg=f"退出码非0；stderr={err}")
        self.assertEqual(out, 'hello')


if __name__ == '__main__':
    unittest.main()
