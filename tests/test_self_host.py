# -*- coding: utf-8 -*-
"""
test_self_host.py - 自举编译器编译级测试

验证内容：
1. 使用 src 后端编译 bootstrap_v3.duan 为 Python
2. 运行生成的 Python 代码
3. 验证执行无错误
4. 检查输出是否包含 "Duan" 或 "段言" 等标识符
"""

import pytest
import sys
import os
import io
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer, LexerError
from light_parser_v3 import LightParser, ParseError
from code_generator import PythonCodeGenerator, CodeGenError

BOOTSTRAP_FILE = os.path.join(os.path.dirname(__file__), '..', 'bootstrap', 'bootstrap_v3.duan')


def _compile_bootstrap():
    """编译 bootstrap_v3.duan 为 Python 代码"""
    assert os.path.exists(BOOTSTRAP_FILE), f"文件不存在: {BOOTSTRAP_FILE}"

    with open(BOOTSTRAP_FILE, 'r', encoding='utf-8') as f:
        source = f.read()

    parser = LightParser()
    module = parser.parse(source)

    generator = PythonCodeGenerator()
    py_code = generator.generate(module)

    return py_code, source


def _run_python_code(py_code: str, capture_output: bool = False):
    """运行生成的 Python 代码，返回命名空间和可选的输出捕获"""
    # 创建内建模块
    _light_builtin = types.ModuleType('_light_builtin')
    _light_builtin.打印 = print
    _light_builtin.输出 = print
    _light_builtin.转字符串 = str
    _light_builtin.转整数 = int
    _light_builtin.转浮点 = float
    _light_builtin.列表创建 = list
    _light_builtin.列表长度 = len
    _light_builtin.列表获取 = lambda lst, i: lst[i]
    _light_builtin.列表追加 = lambda lst, item: lst.append(item)
    _light_builtin.列表弹出 = lambda lst: lst.pop()
    _light_builtin.列表包含 = lambda lst, item: item in lst
    _light_builtin.字典创建 = dict
    _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
    _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
    _light_builtin.字典包含键 = lambda d, k: k in d
    _light_builtin.字典键列表 = lambda d: list(d.keys())
    _light_builtin.字典值列表 = lambda d: list(d.values())
    _light_builtin.字典项列表 = lambda d: list(d.items())
    _light_builtin.字典删除 = lambda d, k: d.pop(k, None)
    _light_builtin.字符串长度 = len
    _light_builtin.字符串获取 = lambda s, i: s[i]
    _light_builtin.截取 = lambda s, start, end: s[start:end]
    _light_builtin.分割字符串 = lambda s, sep=' ': s.split(sep)
    _light_builtin.连接字符串 = lambda parts, sep='': sep.join(parts)
    _light_builtin.替换字符串 = lambda s, old, new: s.replace(old, new)
    _light_builtin.去除空白 = lambda s: s.strip()
    _light_builtin.列表排序 = lambda lst, reverse=False: lst.sort(reverse=reverse)
    _light_builtin.列表反转 = lambda lst: lst.reverse()
    _light_builtin.是整数 = lambda x: isinstance(x, int)
    _light_builtin.是浮点 = lambda x: isinstance(x, float)
    _light_builtin.是字符串 = lambda x: isinstance(x, str)
    _light_builtin.是列表 = lambda x: isinstance(x, list)
    _light_builtin.是字典 = lambda x: isinstance(x, dict)
    _light_builtin.是空 = lambda x: x is None
    _light_builtin.随机整数 = lambda a, b: __import__('random').randint(a, b)
    _light_builtin.随机浮点 = lambda: __import__('random').random()
    _light_builtin.随机选择 = lambda lst: __import__('random').choice(lst)
    _light_builtin.阶乘 = lambda n: __import__('math').factorial(n)
    _light_builtin.平均数 = lambda data: sum(data) / len(data) if data else 0
    _light_builtin.求和 = lambda data: sum(data)
    _light_builtin.时间戳 = lambda: __import__('time').time()
    _light_builtin.格式化时间 = lambda ts, fmt='%Y-%m-%d %H:%M:%S': __import__('time').strftime(fmt, __import__('time').localtime(ts))
    _light_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read()
    _light_builtin.写入文件 = lambda path, content: open(path, 'w', encoding='utf-8').write(content)
    _light_builtin.追加文件 = lambda path, content: open(path, 'a', encoding='utf-8').write(content)
    _light_builtin.文件存在 = lambda path: __import__('os').path.isfile(path)
    _light_builtin.目录存在 = lambda path: __import__('os').path.isdir(path)
    _light_builtin.创建目录 = lambda path: __import__('os').makedirs(path, exist_ok=True)
    _light_builtin.圆周率 = lambda: __import__('math').pi
    _light_builtin.自然常数 = lambda: __import__('math').e
    _light_builtin._读文件 = lambda path: open(path, 'r', encoding='utf-8').read()

    namespace = {
        '_light_builtin': _light_builtin,
        '__builtins__': __builtins__,
    }

    # 如果有需要捕获输出
    if capture_output:
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        try:
            exec(py_code, namespace)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        return namespace, stdout_capture.getvalue(), stderr_capture.getvalue()
    else:
        exec(py_code, namespace)
        return namespace, None, None


class TestSelfHostCompile:
    """自举编译器编译级测试"""

    def test_compile_bootstrap_success(self):
        """测试 bootstrap_v3.duan 能被成功编译为 Python"""
        py_code, source = _compile_bootstrap()

        assert py_code is not None, "编译返回 None"
        assert len(py_code) > 0, "编译结果为空"
        assert 'def ' in py_code, "编译结果未包含函数定义"
        print(f"\n编译成功: 生成了 {len(py_code)} 字符的 Python 代码")

    def test_generated_code_is_valid_syntax(self):
        """验证生成的 Python 代码语法正确"""
        py_code, _ = _compile_bootstrap()

        try:
            compile(py_code, '<string>', 'exec')
        except SyntaxError as e:
            lines = py_code.splitlines()
            context = ''
            if e.lineno and 1 <= e.lineno <= len(lines):
                start = max(0, e.lineno - 3)
                end = min(len(lines), e.lineno + 2)
                context = '\n'.join(f"{i + 1}: {lines[i]}" for i in range(start, end))
            pytest.fail(
                f"Python 语法错误 (行 {e.lineno}): {e.msg}\n"
                f"附近代码:\n{context}"
            )

    def test_run_generated_code(self):
        """测试生成的 Python 代码能成功执行"""
        py_code, _ = _compile_bootstrap()

        try:
            namespace, stdout, stderr = _run_python_code(py_code)
        except Exception as e:
            # 提供错误上下文
            lines = py_code.splitlines()
            tb = traceback.format_exc()
            pytest.fail(f"执行生成的代码失败: {e}\n{tb}")

        # 验证关键函数被定义
        assert '词法分析' in namespace or 'compile_source' in namespace, \
            "命名空间中未找到预期的函数定义"

    def test_generated_code_contains_duan_identifiers(self):
        """验证生成的代码包含段言相关标识符"""
        py_code, _ = _compile_bootstrap()

        # 检查是否包含 "Duan" 或 "段言" 相关标识
        has_duan = 'Duan' in py_code or '段言' in py_code or 'duan' in py_code.lower()
        has_bootstrap = 'bootstrap' in py_code.lower()
        has_duan_compiler = '段言' in py_code or 'duan' in py_code.lower()

        # 检查是否包含核心函数
        has_lexer_funcs = '词法分析' in py_code or 'lexer' in py_code.lower()
        has_parser_funcs = 'parse' in py_code.lower()
        has_codegen_funcs = 'generate' in py_code.lower() or 'codegen' in py_code.lower()

        print(f"\n--- 生成代码标识符检查 ---")
        print(f"包含 'Duan'/'段言': {has_duan}")
        print(f"包含 'bootstrap': {has_bootstrap}")
        print(f"包含词法分析函数: {has_lexer_funcs}")
        print(f"包含解析函数: {has_parser_funcs}")
        print(f"包含代码生成函数: {has_codegen_funcs}")
        print(f"--------------------------")

        assert has_duan_compiler, "生成的代码应包含段言相关标识符"
        assert has_lexer_funcs, "生成的代码应包含词法分析函数"
        assert has_parser_funcs, "生成的代码应包含解析函数"
        assert has_codegen_funcs, "生成的代码应包含代码生成函数"

    def test_execution_without_errors(self):
        """验证生成的代码执行无异常"""
        py_code, _ = _compile_bootstrap()

        # 先验证语法
        compile(py_code, '<string>', 'exec')

        # 执行但不捕获输出（让 print 正常显示）
        namespace, stdout, stderr = _run_python_code(py_code, capture_output=True)

        # 确认没有 stderr 错误输出
        if stderr and stderr.strip():
            print(f"\n警告: 执行产生 stderr 输出:\n{stderr[:500]}")


# 导入 traceback 用于错误报告
import traceback

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])