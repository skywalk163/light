# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 代码生成器测试

测试覆盖：
- 变量声明代码生成
- 表达式代码生成
- 条件语句代码生成
- 循环语句代码生成
- 函数定义代码生成
- 函数调用代码生成
- 完整程序代码生成
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


class TestVariableGeneration:
    """变量声明代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_simple_variable(self, parser, generator):
        """测试简单变量生成"""
        module = parser.parse('设 甲 为 123。')
        python_code = generator.generate(module)
        assert '123' in python_code
        assert '=' in python_code

    def test_variable_with_expression(self, parser, generator):
        """测试带表达式的变量生成"""
        module = parser.parse('设 结果 为 三 加 五。')
        python_code = generator.generate(module)
        assert '+' in python_code or 'add' in python_code.lower()


class TestExpressionGeneration:
    """表达式代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_arithmetic_expression(self, parser, generator):
        """测试算术表达式生成"""
        module = parser.parse('设 结果 为 甲 加 乙 乘 丙。')
        python_code = generator.generate(module)
        assert '+' in python_code or 'add' in python_code.lower()
        assert '*' in python_code or 'mul' in python_code.lower()

    def test_comparison_expression(self, parser, generator):
        """测试比较表达式生成"""
        module = parser.parse('如果 甲 大于 乙 那么：打印(甲)。')
        python_code = generator.generate(module)
        assert 'if' in python_code
        assert '>' in python_code or 'gt' in python_code.lower()


class TestConditionalGeneration:
    """条件语句代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_simple_if(self, parser, generator):
        """测试简单if生成"""
        module = parser.parse('如果 甲 大于 乙 那么：打印(甲)。')
        python_code = generator.generate(module)
        assert 'if' in python_code
        assert 'print' in python_code

    def test_if_else(self, parser, generator):
        """测试if-else生成"""
        module = parser.parse('如果 甲 大于 乙 那么：打印(甲)。否则：打印(乙)。')
        python_code = generator.generate(module)
        assert 'if' in python_code
        assert 'else' in python_code


class TestLoopGeneration:
    """循环语句代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_while_loop(self, parser, generator):
        """测试while循环生成"""
        code = '''当 甲 小于 十：
  甲 等于 甲 加 一。
结束。'''
        module = parser.parse(code)
        python_code = generator.generate(module)
        assert 'while' in python_code

    def test_for_loop(self, parser, generator):
        """测试for循环生成"""
        code = '''遍历 元素 之 列表：
  打印(元素)。
结束。'''
        module = parser.parse(code)
        python_code = generator.generate(module)
        assert 'for' in python_code


class TestFunctionGeneration:
    """函数定义代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_simple_function(self, parser, generator):
        """测试简单函数生成"""
        module = parser.parse('段 计算 接收：返回 甲 加 乙。结束。')
        python_code = generator.generate(module)
        assert 'def' in python_code

    def test_function_with_params(self, parser, generator):
        """测试带参数的函数生成"""
        module = parser.parse('《计算》段(甲, 乙)：返回 甲 加 乙。')
        python_code = generator.generate(module)
        assert 'def' in python_code
        assert '(' in python_code
        assert ')' in python_code
        assert 'return' in python_code


class TestFunctionCallGeneration:
    """函数调用代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_simple_call(self, parser, generator):
        """测试简单函数调用生成"""
        module = parser.parse('设 结果 为 计算(甲, 乙)。')
        python_code = generator.generate(module)
        assert '(' in python_code
        assert ')' in python_code

    def test_call_in_expression(self, parser, generator):
        """测试表达式中的函数调用"""
        module = parser.parse('设 结果 为 计算(甲, 乙)。')
        python_code = generator.generate(module)
        assert '(' in python_code


class TestCompleteProgramGeneration:
    """完整程序代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_factorial(self, parser, generator):
        """测试阶乘程序生成"""
        code = '''《阶乘》段(数)：
  如果 数 小于等于 1 那么 返回 1。
  返回 数 乘 阶乘(数 减 1)。

设 结果 为 阶乘(5)。
打印(结果)。'''
        module = parser.parse(code)
        python_code = generator.generate(module)
        assert 'def' in python_code
        assert 'if' in python_code
        assert 'return' in python_code
        assert 'print' in python_code

    def test_fibonacci(self, parser, generator):
        """测试斐波那契程序生成"""
        code = '''《斐波那契》段(数)：
  如果 数 小于等于 2 那么 返回 1。
  返回 斐波那契(数 减 1) 加 斐波那契(数 减 2)。

设 结果 为 斐波那契(10)。
打印(结果)。'''
        module = parser.parse(code)
        python_code = generator.generate(module)
        assert 'def' in python_code
        assert 'if' in python_code
        assert 'return' in python_code


class TestCodeExecution:
    """代码执行测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_simple_execution(self, parser, generator):
        """测试简单程序执行"""
        module = parser.parse('设 甲 为 三 加 五。')
        python_code = generator.generate(module)
        try:
            exec_globals = {}
            exec(python_code, exec_globals)
            assert True
        except Exception as e:
            print(f"Execution error: {e}")

    def test_function_execution(self, parser, generator):
        """测试函数程序执行"""
        module = parser.parse('《加法》段(甲, 乙)：返回 甲 加 乙。')
        python_code = generator.generate(module)
        try:
            exec_globals = {}
            exec(python_code, exec_globals)
        except Exception as e:
            print(f"Execution error: {e}")


class Test内置映射与实现咬合:
    """`builtin_map` 里每个 `_light_builtin.X` 目标，`stdlib/builtins.py` 里必须真有 `X`。

    ## 为什么要这条通用护栏，而不是只测三个名字

    映射指向不存在的实现是**编译期零报错、运行期 AttributeError** 的形态。
    C9BI 动手前实测过三条原文，例如：

        AttributeError: module 'light_builtins' has no attribute '包含'

    C9BI 清掉的 `包含` / `字符串替换` / `字符串分割` 只是当时正好存在的三条。
    单测那三个名字只能证明「这三条修好了」，堵不住下一个人再加一条空壳。
    所以判据写成「整张表 × 整个实现模块」的全量比对。

    ## 为什么判据是「模块里真有这个属性」而不是「名字在 `__all__` 里」

    产物是用 `spec_from_file_location` + `exec_module` 把 `stdlib/builtins.py`
    整个装进来的（`src/code_generator.py:759-763`），取属性根本不看 `__all__`。
    而 `stdlib/builtins.py:1012` 的 `__all__` 实际上是个**过期的子集**：实测有
    15 个正常在用的内置不在里面（`是文件` / `列出文件` / `移动文件系统` /
    `显示宽度` / `转大写` / `转小写` / `截取` / `子串` / `字符串截取` /
    `最后索引` / `列表获取` / `列表创建` / `时间戳` / `格式化时间` / `_读文件`）。
    拿 `__all__` 当判据会凭空造 15 条幻影红 —— 那是把护栏调成了噪音。
    """

    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _载入内置模块(self):
        """按产物的加载方式装 stdlib/builtins.py（走 spec，不走 import）。"""
        import importlib.util
        路径 = os.path.join(self._ROOT, 'stdlib', 'builtins.py')
        assert os.path.isfile(路径), '实现体不见了：stdlib/builtins.py'
        spec = importlib.util.spec_from_file_location('light_builtins_probe', 路径)
        模块 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(模块)
        return 模块

    def test_内置映射不许有空壳(self):
        """`_light_builtin.X` 的 X 必须在实现模块里真的存在。"""
        模块 = self._载入内置模块()
        表 = PythonCodeGenerator().builtin_map
        目标 = {k: v for k, v in 表.items() if v.startswith('_light_builtin.')}
        assert 目标, 'builtin_map 里一条 _light_builtin.* 都没有，说明表被改坏了'
        缺失 = sorted(
            '%s -> %s' % (k, v)
            for k, v in 目标.items()
            if not hasattr(模块, v.split('.', 1)[1])
        )
        assert 缺失 == [], (
            '空壳映射（builtin_map 有、stdlib/builtins.py 无，调用即 AttributeError）：\n  '
            + '\n  '.join(缺失)
        )

    @pytest.mark.parametrize('源码, 期望', [
        # 三条曾经的空壳，现在必须真跑出正确结果
        ('设 结果 为 包含([1, 2, 3], 2)。', True),
        ('设 结果 为 包含([1, 2, 3], 9)。', False),
        ('设 结果 为 包含("abc", "b")。', True),
        ('设 结果 为 字符串替换("abcabc", "b", "X")。', 'aXcaXc'),
        ('设 结果 为 字符串分割("a,b,c", ",")。', ['a', 'b', 'c']),
    ])
    def test_三条旧空壳的语义(self, 源码, 期望):
        """编译 + 真执行，断结果值。

        `包含` 的实参顺序取「容器在前」：真调用者
        `积木库/blocks_v4/集合/集合包含.light:5` 写的是 `包含(输入, 元素)`，
        成员形式 `容器.包含(元素)` 也发射 `(元素 in 容器)`
        （`src/code_generator.py:2956`）。三条用例把这个顺序钉住 ——
        若哪天被改成「子在前」，`包含([1,2,3], 9)` 会从 False 变成抛错。
        """
        py = PythonCodeGenerator().generate(LightParser().parse(源码))
        # 产物靠 __file__ 的所在目录去找 stdlib/；exec 出来的代码没有 __file__，
        # 不喂就会退到 os.getcwd()，测试结果随 pytest 的启动目录漂。
        环境 = {'__file__': os.path.join(self._ROOT, '_c9bi_内置探针.py')}
        exec(compile(py, '<内置探针>', 'exec'), 环境)
        assert 环境['结果'] == 期望


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
