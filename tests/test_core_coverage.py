# -*- coding: utf-8 -*-
"""
段言核心模块覆盖率补充测试

覆盖 parser_stmt / parser_expr / type_inferencer / code_generator 中
未被现有测试触达的语法分支，用于提升核心语言链路模块覆盖率（3.4.1）。

策略：对每个语法片段执行 词法→解析→适配→类型推断→代码生成 全链路，
断言流程不抛异常且生成代码非空。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from compiler import LightCompiler
from code_generator_unified import UnifiedCodeGenerator


def _compile_ok(source: str) -> str:
    """编译段言源码，返回生成的 Python 代码；流程异常则抛出"""
    compiler = LightCompiler()
    result = compiler.compile(source)
    assert result.get('ast') is not None, f"AST 生成失败: {source}\n{result.get('errors')}"
    codegen = UnifiedCodeGenerator()
    code = codegen.generate(result['ast'])
    assert isinstance(code, str) and len(code) > 0, f"代码生成失败: {source}"
    return code


# ---------------------------------------------------------------------------
# FFI 声明（解析 + 生成，不执行）
# ---------------------------------------------------------------------------

class TestFFICoverage:
    """FFI 各类声明编译覆盖"""

    def test_ffi_function_decl(self):
        _compile_ok('外部 函数 加法 接收 甲: 整数, 乙: 整数 返回 整数 在 libc。')

    def test_ffi_struct_def(self):
        _compile_ok('外部 结构体 点 { 甲: 整数, 乙: 整数 }。')

    def test_ffi_enum_def(self):
        _compile_ok('外部 枚举 颜色 { 红 = 1, 蓝 = 2 }。')

    def test_ffi_callback_def(self):
        _compile_ok('外部 回调 比较器 接收 甲, 乙 返回 整数。')

    def test_ffi_union_def(self):
        _compile_ok('外部 联合体 数据 { 甲: 整数, 乙: 小数 }。')

    def test_ffi_typedef_def(self):
        _compile_ok('外部 类型别名 长度 为 整数。')

    def test_ffi_bitfield_def(self):
        _compile_ok('外部 位域 标志 { 位一: 整数 }。')

    def test_ffi_varargs_decl(self):
        _compile_ok('外部 变长参数 函数 打印格式 接收 格式: 串 返回 整数 在 libc。')

    def test_ffi_debug_config(self):
        _compile_ok('外部 调试 级别 3。')

    def test_ffi_load_library(self):
        _compile_ok('加载库 "libm" 为 库。')

    def test_ffi_funcptr_def(self):
        _compile_ok('外部 函数指针 比较器 接收 甲 返回 整数。')

    def test_ffi_preprocessor_macro(self):
        _compile_ok('外部 宏 PI 为 3.14。')

    def test_ffi_struct_usage(self):
        _compile_ok('''外部 结构体 点 { 甲: 整数, 乙: 整数 }。
设 p 为 新建 点(1, 2)。
打印(p.甲)
''')


# ---------------------------------------------------------------------------
# 接口 / 类实现
# ---------------------------------------------------------------------------

class TestInterfaceCoverage:
    """接口定义与类实现编译覆盖"""

    def test_interface_definition(self):
        _compile_ok('接口 可打印：\n  段落 输出 返回 串。')

    def test_interface_inheritance(self):
        _compile_ok('接口 可保存 继承 可打印：\n  段落 保存(路径)。')

    def test_class_implements_interface(self):
        _compile_ok('''接口 可打印：
  段落 输出 返回 串。
类 文档 实现 可打印：
  段落 输出 返回 串：
    返回 "doc"
''')


# ---------------------------------------------------------------------------
# 控制流 / 语句
# ---------------------------------------------------------------------------

class TestStmtCoverage:
    """match / with / 装饰器 / 异步 / 嵌入 / 异常 语句编译覆盖"""

    def test_match_stmt(self):
        _compile_ok('''段落 评级 接收 分数：
  匹配 分数：
    情况 100：
      返回 "满分"
    情况 _：
      返回 "其他"
''' + '设 结果 为 评级(85)\n')

    def test_match_string_pattern(self):
        _compile_ok('''段落 判断 接收 颜色：
  匹配 颜色：
    情况 "红"：
      返回 1
    情况 _：
      返回 0
''' + '设 结果 为 判断("红")\n')

    def test_with_stmt(self):
        _compile_ok('''使用 文件 为 打开("a.txt")：
  打印(文件)
''')

    def test_decorator(self):
        _compile_ok('@抽象\n段落 方法：\n  返回 1\n')

    def test_async_paragraph(self):
        _compile_ok('''异步 段落 获取数据：
  返回 42
''')

    def test_embed_block(self):
        _compile_ok('''嵌入 Python:
  x = 1
结束嵌入
''')

    def test_try_catch(self):
        _compile_ok('''尝试：
  抛出 错误("x")
捕获 错误 为 e：
  打印(e)
''')

    def test_throw_from(self):
        _compile_ok('''段落 测试：
  抛出 错误() from 原因。
''')

    def test_foreach_range(self):
        _compile_ok('''遍历 i 在 1 到 10：
  打印(i)
''')

    def test_foreach_dict(self):
        _compile_ok('''设 表 为 {"甲": 1, "乙": 2}
遍历 键, 值 之 表：
  打印(键, 值)
''')

    def test_foreach_tuple_unpack(self):
        _compile_ok('''遍历 i, c 于 枚举([1, 2, 3])：
  打印(i, c)
''')

    def test_while_stmt(self):
        _compile_ok('''设 计数 为 0。
当 计数 小于 10：
  计数 为 计数 加 1
''')

    def test_slice_with_step(self):
        _compile_ok('''设 列表 为 [1, 2, 3, 4, 5]。
设 段 为 列表[1:4:2]。
''')

    def test_generic_decl(self):
        _compile_ok('设 表 为 字典<字符串, 列表<整数>> = {}。')

    def test_compound_assign(self):
        _compile_ok('''设 计数 为 0。
计数 为 计数 加 1。
''')

    def test_indexed_compound_assign(self):
        _compile_ok('''设 列表 为 [1, 2, 3]。
列表[0] 为 列表[0] 加 1。
''')

    def test_member_assign(self):
        _compile_ok('''类 盒子：
  属性 值。
  构造 接收 初值：
    己值 为 初值
设 盒子1 为 新建 盒子(1)
盒子1.值 为 5
''')

    def test_destructure_tuple(self):
        _compile_ok('''设 点 为 (1, 2)。
设（甲，乙）为 点。
''')

    def test_destructure_list(self):
        _compile_ok('''设 列表 为 [1, 2, 3]。
设 [首, 余] 为 列表。
''')


# ---------------------------------------------------------------------------
# 表达式
# ---------------------------------------------------------------------------

class TestExprCoverage:
    """lambda / 三元 / 解包 / 切片 / 推导 / 管道 表达式编译覆盖"""

    def test_lambda(self):
        _compile_ok('设 平方 为 接收 甲：返回 甲 乘 甲。')

    def test_conditional_expr(self):
        _compile_ok('设 结果 为 如果 甲 那么 1 否则 2。')

    def test_unwrap_expr(self):
        _compile_ok('设 值 为 5!。')

    def test_slice(self):
        _compile_ok('''设 列表 为 [1, 2, 3, 4, 5]。
设 前段 为 列表[1:3]。
''')

    def test_range_expr(self):
        _compile_ok('设 序列 为 范围(1, 10)。')

    def test_pipeline(self):
        _compile_ok('''段落 处理 接收 数据：
  返回 数据 加 1
设 结果 为 数据 -> 处理。
''')

    def test_dict_comprehension(self):
        _compile_ok('设 表 为 {甲: 甲乘甲 遍历 甲 之 [1,2,3]}。')

    def test_set_comprehension(self):
        _compile_ok('设 集 为 {甲 遍历 甲 之 [1,2,2,3]}。')

    def test_string_interpolation(self):
        _compile_ok('''设 名字 为 "世界"。
打印 "你好，{名字}"。
''')

    def test_tuple_literal(self):
        _compile_ok('设 点 为 (1, 2)。')


# ---------------------------------------------------------------------------
# 类型检查器（显式启用分级检查）
# ---------------------------------------------------------------------------

class TestTypeCheckerCoverage:
    """类型检查器文件指令 / 严格段落检查覆盖"""

    @staticmethod
    def _check(source, level='表达式'):
        from type_checker import TypeCheckerConfig, TypeChecker, TypeCheckLevel
        from type_inferencer import TypeInferencer
        c = LightCompiler()
        module = c.parse_raw(source)
        module = c.adapt(module)
        inf = TypeInferencer()
        inf.infer(module)
        level_map = {'签名': 1, '变量': 2, '表达式': 3}
        checker = TypeChecker(TypeCheckerConfig(
            check_level=TypeCheckLevel(level_map.get(level, 3))))
        results = checker.check(module, inf)
        return results

    def test_signature_level_check(self):
        """签名级别：段落参数与返回类型检查"""
        src = ('段落 加法 接收 a: 整数, b: 整数 返回 整数：\n'
               '  返回 a 加 b\n')
        results = self._check(src, '签名')
        assert results is not None

    def test_expression_level_check(self):
        """表达式级别检查"""
        src = ('段落 双倍 接收 n: 整数：\n'
               '  返回 n 乘 2\n')
        results = self._check(src, '表达式')
        assert results is not None

    def test_strict_segment(self):
        """严格 修饰段落：强制表达式级检查"""
        src = ('严格 段落 处理 接收 数据: 整数：\n'
               '  返回 数据 加 1\n')
        results = self._check(src, '签名')
        assert results is not None

    def test_file_directive(self):
        """文件级指令：类型检查级别 签名 / 类型模式 严格"""
        src = ('# 类型检查级别: 签名\n'
               '# 类型模式: 严格\n'
               '段落 处理 接收 数据: 整数 返回 整数：\n'
               '  返回 数据 加 1\n')
        from type_checker import TypeCheckerConfig, TypeChecker
        c = LightCompiler()
        module = c.parse_raw(src)
        module = c.adapt(module)
        from type_inferencer import TypeInferencer
        inf = TypeInferencer()
        inf.infer(module)
        config = TypeCheckerConfig()
        config = config.apply_file_directives(src)
        checker = TypeChecker(config)
        results = checker.check(module, inf)
        assert results is not None


# ---------------------------------------------------------------------------
# 高密度语法覆盖（赋值形式 / 类完整用法 / 运算符）
# ---------------------------------------------------------------------------

class TestDenseCoverage:
    """多种赋值形式与运算符的编译覆盖"""

    def test_assignment_forms(self):
        _compile_ok('''设 甲 为 1
甲 为 甲 加 1
甲 为 甲 减 1
甲 为 甲 乘 2
甲 为 甲 除 2
甲 为 甲 模 2
设 丙 为 甲 且 真
设 丁 为 甲 或 假
设 戊 为 非 甲
''')

    def test_class_full_usage(self):
        _compile_ok('''类 动物：
  静态 属性 种类 等于 "动物"
  属性 名称。
  构造 接收 名字：
    己名称 为 名字
  段落 叫声：
    返回 "..."
类 狗 继承 动物：
  段落 叫声：
    返回 "汪汪"
设 狗子 为 新建 狗("旺财")
打印(动物.种类)
打印(狗子.名称)
打印(狗子.叫声())
''')

    def test_arithmetic_operators(self):
        _compile_ok('''设 甲 为 10
设 乙 为 甲 加 5
设 丙 为 甲 减 5
设 丁 为 甲 乘 5
设 戊 为 甲 除 5
设 己 为 甲 模 3
设 庚 为 甲 整除 2
''')

    def test_comparison_operators(self):
        _compile_ok('''设 甲 为 10
设 乙 为 20
设 子 为 甲 大于 乙
设 丑 为 甲 小于 乙
设 寅 为 甲 等于 乙
设 卯 为 甲 不等于 乙
设 辰 为 甲 大于等于 乙
设 巳 为 甲 小于等于 乙
''')

    def test_logic_operators(self):
        _compile_ok('''设 甲 为 真
设 乙 为 假
设 丙 为 甲 且 乙
设 丁 为 甲 或 乙
设 戊 为 非 甲
''')

    def test_index_and_member(self):
        _compile_ok('''类 计数器：
  属性 当前。
  构造 接收 初值：
    己当前 为 初值
  段落 增加：
    己当前 为 己当前 加 1
设 计数 为 新建 计数器(0)
计数.增加()
设 列表 为 [1, 2, 3]
打印(列表[0])
设 表 为 {"键": 值}
打印(表["键"])
''')

    def test_nested_control_flow(self):
        _compile_ok('''设 总分 为 0
遍历 i 在 1 到 5：
  如果 i 模 2 等于 0：
    总分 为 总分 加 i
  否则：
    总分 为 总分 加 1
打印(总分)
''')

    def test_string_and_list_ops(self):
        _compile_ok('''设 文本 为 "你好，世界"
设 长度 为 文本长度(文本)
设 列表 为 [3, 1, 2]
列表 为 列表排序(列表)
设 拼接 为 "a" 加 "b"
打印(长度, 拼接)
''')
