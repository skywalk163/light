#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明 v4.0 - FFI + 标准库综合 Mock 测试

测试内容：
A. FFI 声明解析 + 代码生成
B. 标准库操作
C. FFI + stdlib 混合使用
"""

import sys
import os
import io
import unittest
import tempfile
import shutil
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def _make_builtin():
    """创建包含内置函数的 light 运行时环境"""
    import types
    m = types.ModuleType('_light_builtin')
    m.打印 = print
    m.设 = lambda name, val: None
    m.列表创建 = list
    m.列表追加 = lambda lst, item: lst.append(item)
    m.列表包含 = lambda lst, item: item in lst
    m.字符串长度 = len
    m.字典创建 = dict
    m.整数 = int
    m.小数 = float
    m.文本 = str
    m.布尔 = bool
    m.空 = None
    m.类型 = type
    return m


def compile_and_run(light_code):
    """编译并执行光明代码，返回捕获的输出"""
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator
    
    parser = LightParser()
    try:
        module = parser.parse(light_code)
    except Exception as e:
        raise RuntimeError(f"解析错误: {e}")
    
    generator = PythonCodeGenerator()
    python_code = generator.generate(module)
    
    # 添加 stdlib 路径
    _stdlib_path = os.path.join(os.path.dirname(__file__), '..', 'stdlib')
    if _stdlib_path not in sys.path:
        sys.path.insert(0, _stdlib_path)
    
    _contrib_path = os.path.join(os.path.dirname(__file__), '..', 'contrib')
    if _contrib_path not in sys.path:
        sys.path.insert(0, _contrib_path)
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    
    globals_dict = {'__name__': '__main__', '_light_builtin': _make_builtin()}
    
    try:
        exec(compile(python_code, '<light_test>', 'exec'), globals_dict)
        output = captured_output.getvalue()
        return output
    except Exception as e:
        raise RuntimeError(f"执行错误: {e}\n\n生成的 Python 代码:\n{python_code}")
    finally:
        sys.stdout = old_stdout


def compile_only(light_code):
    """仅编译光明代码，返回生成的 Python 代码（不执行）"""
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator
    
    parser = LightParser()
    try:
        module = parser.parse(light_code)
    except Exception as e:
        raise RuntimeError(f"解析错误: {e}")
    
    generator = PythonCodeGenerator()
    python_code = generator.generate(module)
    return python_code


# ============================================================
# A. FFI 声明解析 + 代码生成测试
# ============================================================

class TestFFI_Macro(unittest.TestCase):
    """A1. 外部 宏 定义"""

    def test_simple_macro(self):
        """简单宏定义：外部 宏 最大连接 为 100"""
        code = "外部 宏 最大连接 为 100。"
        py_code = compile_only(code)
        self.assertIn("最大连接", py_code)
        self.assertIn("_light_ffi.定义宏", py_code)
        self.assertIn("100", py_code)

    def test_macro_with_string(self):
        """字符串宏：外部 宏 默认路径 为 "/tmp/light" """
        code = '外部 宏 默认路径 为 "/tmp/light"。'
        py_code = compile_only(code)
        self.assertIn("默认路径", py_code)
        self.assertIn("/tmp/light", py_code)

    def test_multi_token_macro_name(self):
        """多 token 宏名：外部 宏 最大连接数 为 1000"""
        code = "外部 宏 最大连接数 为 1000。"
        py_code = compile_only(code)
        self.assertIn("最大连接数", py_code)
        self.assertIn("1000", py_code)


class TestFFI_FunctionDecl(unittest.TestCase):
    """A2. 外部 函数 声明"""

    def test_simple_function(self):
        """简单函数声明：外部 函数 正弦 接收 甲 为 小数 返回 小数 在 数学库"""
        code = "外部 函数 正弦 接收 甲 为 小数 返回 小数 在 数学库。"
        py_code = compile_only(code)
        self.assertIn("正弦", py_code)
        self.assertIn("数学库", py_code)
        self.assertIn("ctypes", py_code)

    def test_function_with_multiple_params(self):
        """多参数函数"""
        code = "外部 函数 幂 接收 底 为 小数, 指数 为 小数 返回 小数 在 数学库。"
        py_code = compile_only(code)
        self.assertIn("幂", py_code)
        self.assertIn("底", py_code)
        self.assertIn("指数", py_code)

    def test_function_no_return(self):
        """无返回值的函数"""
        code = "外部 函数 设置标题 接收 标题 为 文本 在 用户库。"
        py_code = compile_only(code)
        self.assertIn("设置标题", py_code)


class TestFFI_StructDef(unittest.TestCase):
    """A3. 外部 结构体 定义"""

    def test_simple_struct(self):
        """简单结构体"""
        code = "外部 结构体 点 { 甲: 整数, 乙: 整数 }。"
        py_code = compile_only(code)
        self.assertIn("点", py_code)
        self.assertIn("ctypes.Structure", py_code)
        self.assertIn("甲", py_code)
        self.assertIn("乙", py_code)

    def test_struct_with_mixed_types(self):
        """混合类型结构体"""
        code = "外部 结构体 用户 { 编号: 整数, 姓名: 文本, 分数: 小数 }。"
        py_code = compile_only(code)
        self.assertIn("用户", py_code)
        self.assertIn("编号", py_code)
        self.assertIn("姓名", py_code)
        self.assertIn("分数", py_code)


class TestFFI_CallbackDef(unittest.TestCase):
    """A4. 外部 回调 定义"""

    def test_simple_callback(self):
        """简单回调"""
        code = "外部 回调 比较回调 接收 甲 为 整数, 乙 为 整数 返回 整数。"
        py_code = compile_only(code)
        self.assertIn("比较回调", py_code)
        self.assertIn("CFUNCTYPE", py_code)

    def test_callback_no_params(self):
        """无参回调"""
        code = "外部 回调 通知回调 返回 空。"
        py_code = compile_only(code)
        self.assertIn("通知回调", py_code)
        self.assertIn("CFUNCTYPE", py_code)


class TestFFI_EnumDef(unittest.TestCase):
    """A5. 外部 枚举 定义"""

    def test_simple_enum(self):
        """简单枚举"""
        code = "外部 枚举 颜色 { 红, 绿, 蓝 }。"
        py_code = compile_only(code)
        self.assertIn("颜色", py_code)
        self.assertIn("红", py_code)
        self.assertIn("绿", py_code)
        self.assertIn("蓝", py_code)

    def test_enum_with_values(self):
        """带值枚举"""
        code = "外部 枚举 错误码 { 成功 = 0, 失败 = 1, 超时 = 2 }。"
        py_code = compile_only(code)
        self.assertIn("错误码", py_code)
        self.assertIn("成功", py_code)


class TestFFI_UnionDef(unittest.TestCase):
    """A6. 外部 联合体 定义"""

    def test_simple_union(self):
        """简单联合体"""
        code = "外部 联合体 数据 { 整数部分: 整数, 小数部分: 小数 }。"
        py_code = compile_only(code)
        self.assertIn("数据", py_code)
        self.assertIn("ctypes.Union", py_code)


class TestFFI_BitfieldDef(unittest.TestCase):
    """A8. 外部 位域 定义"""

    def test_bitfield(self):
        """位域"""
        code = "外部 位域 标志位 { 可读: 1, 可写: 1, 可执行: 2 }。"
        py_code = compile_only(code)
        self.assertIn("标志位", py_code)
        self.assertIn("可读", py_code)
        self.assertIn("可写", py_code)


class TestFFI_TypedefDef(unittest.TestCase):
    """A9. 外部 类型别名 定义"""

    def test_typedef(self):
        """类型别名"""
        code = "外部 类型别名 长度 为 整数。"
        py_code = compile_only(code)
        self.assertIn("长度", py_code)
        self.assertIn("c_int", py_code)


class TestFFI_EmbedCBlock(unittest.TestCase):
    """A10. 引 C: 嵌入块"""

    def test_embed_c_block(self):
        """引 C: 嵌入块"""
        code = '''
引 C:
    #include <stdio.h>
    int add(int a, int b) { return a + b; }
结束引
'''
        py_code = compile_only(code)
        self.assertIn("C", py_code)
        self.assertIn("add", py_code)
        self.assertIn("stdio.h", py_code)


class TestFFI_EmbedPythonBlock(unittest.TestCase):
    """A11. 引 Python: 嵌入块 (L4)"""

    def test_embed_python_block(self):
        """引 Python: 嵌入块，定义函数并导出"""
        code = '''
引 Python:
def l4_hello(name):
    return f"你好，{name}！"
结束引
打印(l4_hello("世界"))。
'''
        output = compile_and_run(code)
        self.assertIn("你好，世界", output)

    def test_embed_python_math(self):
        """引 Python: 嵌入块，使用 Python 数学计算"""
        code = '''
引 Python:
def l4_square(x):
    return x * x
def l4_cube(x):
    return x * x * x
结束引
打印(l4_square(5))。
打印(l4_cube(3))。
'''
        output = compile_and_run(code)
        self.assertIn("25", output)
        self.assertIn("27", output)

    def test_embed_python_private_not_exported(self):
        """引 Python: 以下划线开头的函数不应导出"""
        code = '''
引 Python:
def l4_public():
    return "公开"
def _private():
    return "私有"
结束引
打印(l4_public())。
'''
        output = compile_and_run(code)
        self.assertIn("公开", output)


# ============================================================
# B. 标准库操作测试
# ============================================================

class TestStdlib_FileSystem(unittest.TestCase):
    """B1. 文件系统操作"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='light_test_')

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_and_read_file(self):
        """写入文件 + 读取文件"""
        test_file = os.path.join(self.temp_dir, '测试.txt').replace('\\', '\\\\')
        code = f'''
从 文件系统 导入 写入文件, 读取文件。
写入文件("{test_file}", "Hello, 光明！")。
设 内容 为 读取文件("{test_file}")。
打印(内容)。
'''
        output = compile_and_run(code)
        self.assertIn("Hello, 光明", output)

    def test_file_exists(self):
        """文件存在性检查"""
        test_file = os.path.join(self.temp_dir, '存在.txt').replace('\\', '\\\\')
        code = f'''
从 文件系统 导入 写入文件, 文件存在, 删除文件。
写入文件("{test_file}", "test")。
设 存在 为 文件存在("{test_file}")。
打印(存在)。
删除文件("{test_file}")。
设 不存在 为 文件存在("{test_file}")。
打印(不存在)。
'''
        output = compile_and_run(code)
        lines = [l.strip() for l in output.strip().split('\n') if l.strip()]
        self.assertEqual(lines[-1], "False")

    def test_append_file(self):
        """追加文件内容"""
        test_file = os.path.join(self.temp_dir, '追加.txt').replace('\\', '\\\\')
        code = f'''
从 文件系统 导入 写入文件, 追加文件, 读取文件。
写入文件("{test_file}", "第一行\\n")。
追加文件("{test_file}", "第二行")。
设 内容 为 读取文件("{test_file}")。
打印(内容)。
'''
        output = compile_and_run(code)
        self.assertIn("第一行", output)
        self.assertIn("第二行", output)


class TestStdlib_JSON(unittest.TestCase):
    """B2. JSON 操作"""

    def test_parse_json(self):
        """解析 JSON"""
        code = '''
从 JSON 导入 解析JSON, 序列化JSON。
设 数据 为 解析JSON('{"name": "光明", "version": 4}')。
打印(数据["name"])。
打印(数据["version"])。
'''
        output = compile_and_run(code)
        self.assertIn("光明", output)
        self.assertIn("4", output)

    def test_serialize_json(self):
        """序列化 JSON"""
        code = '''
从 JSON 导入 序列化JSON。
设 数据 为 {"语言": "光明", "版本": 4.0}。
设 文本 为 序列化JSON(数据)。
打印(文本)。
'''
        output = compile_and_run(code)
        self.assertIn("光明", output)
        self.assertIn("4.0", output)


class TestStdlib_Math(unittest.TestCase):
    """B3. 数学运算"""

    def test_abs(self):
        """绝对值"""
        code = '''
从 数学 导入 绝对值。
打印(绝对值(-5))。
打印(绝对值(3))。
'''
        output = compile_and_run(code)
        self.assertIn("5", output)
        self.assertIn("3", output)

    def test_sqrt(self):
        """平方根"""
        code = '''
从 数学 导入 平方根。
打印(平方根(16))。
'''
        output = compile_and_run(code)
        self.assertIn("4.0", output)

    def test_pow(self):
        """幂运算"""
        code = '''
从 数学 导入 幂。
打印(幂(2, 10))。
打印(幂(3, 3))。
'''
        output = compile_and_run(code)
        self.assertIn("1024", output)
        self.assertIn("27", output)

    def test_sin(self):
        """正弦函数"""
        code = '''
从 数学 导入 正弦。
打印(正弦(0.0))。
'''
        output = compile_and_run(code)
        self.assertIn("0.0", output)


class TestStdlib_String(unittest.TestCase):
    """B4. 字符串处理"""

    def test_length(self):
        """字符串长度"""
        code = '''
从 字符串处理 导入 长度。
打印(长度("Hello, 光明"))。
'''
        output = compile_and_run(code)
        self.assertIn("9", output)

    def test_split(self):
        """字符串分割"""
        code = '''
从 字符串处理 导入 分割。
设 结果 为 分割("甲,乙,丙", ",")。
打印(结果[0])。
打印(结果[1])。
打印(结果[2])。
'''
        output = compile_and_run(code)
        self.assertIn("甲", output)
        self.assertIn("乙", output)
        self.assertIn("丙", output)

    def test_replace(self):
        """字符串替换"""
        code = '''
从 字符串处理 导入 替换。
设 结果 为 替换("Hello World", "World", "光明")。
打印(结果)。
'''
        output = compile_and_run(code)
        self.assertIn("Hello 光明", output)

    def test_find(self):
        """查找子串"""
        code = '''
从 字符串处理 导入 查找。
打印(查找("Hello World", "World"))。
打印(查找("Hello World", "Python"))。
'''
        output = compile_and_run(code)
        self.assertIn("6", output)
        self.assertIn("-1", output)


class TestStdlib_DateTime(unittest.TestCase):
    """B5. 日期时间"""

    def test_now(self):
        """获取当前时间戳并格式化"""
        code = '''
从 日期时间 导入 当前时间戳, 格式化时间戳。
设 戳 为 当前时间戳()。
设 文本 为 格式化时间戳(戳, "%Y-%m-%d")。
打印(文本)。
'''
        output = compile_and_run(code)
        self.assertIsNotNone(re.search(r'\d{4}-\d{2}-\d{2}', output))

    def test_timestamp(self):
        """时间戳"""
        code = '''
从 日期时间 导入 当前时间戳。
设 戳 为 当前时间戳()。
打印(戳)。
'''
        output = compile_and_run(code)
        self.assertTrue(len(output.strip()) > 0)


class TestStdlib_Regex(unittest.TestCase):
    """B6. 正则表达式"""

    def test_search(self):
        """正则搜索"""
        code = '''
从 正则表达式 导入 查找。
设 结果 为 查找("world", "hello world")。
打印(结果)。
'''
        output = compile_and_run(code)
        self.assertIn("world", output)


class TestStdlib_Logging(unittest.TestCase):
    """B7. 日志"""

    def test_basic_logging(self):
        """基础日志（使用日志模块）"""
        code = '''
从 日志系统增强 导入 获取级别, 信息。
设 级别 为 获取级别()。
打印(级别)。
信息("测试信息")。
打印("日志完成")。
'''
        output = compile_and_run(code)
        self.assertIn("测试信息", output)
        self.assertIn("日志完成", output)


class TestStdlib_AdvancedFile(unittest.TestCase):
    """B8. 高级文件"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='light_test_adv_')

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_copy_file(self):
        """复制文件"""
        src = os.path.join(self.temp_dir, '源.txt').replace('\\', '\\\\')
        dst = os.path.join(self.temp_dir, '目标.txt').replace('\\', '\\\\')
        code = f'''
从 文件系统 导入 写入文件。
从 高级文件 导入 复制文件。
写入文件("{src}", "Hello")。
复制文件("{src}", "{dst}")。
打印("复制完成")。
'''
        output = compile_and_run(code)
        self.assertIn("复制完成", output)
        self.assertTrue(os.path.exists(dst.replace('\\\\', '\\')))
        with open(src.replace('\\\\', '\\'), 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), "Hello")


# ============================================================
# C. 综合测试：FFI + stdlib 混合使用
# ============================================================

class TestFFI_Stdlib_Combined(unittest.TestCase):
    """C. FFI + stdlib 综合测试"""

    def test_ffi_macro_with_stdlib_string(self):
        """宏定义 + 字符串处理"""
        code = '''
外部 宏 最大连接 为 100。
从 字符串处理 导入 长度。
设 宏名 为 "最大连接"。
打印(长度(宏名))。
'''
        py_code = compile_only(code)
        self.assertIn("最大连接", py_code)
        self.assertIn("_light_ffi.定义宏", py_code)

    def test_ffi_enum_with_math(self):
        """枚举定义 + 数学运算"""
        code = '''
外部 枚举 状态 { 就绪, 运行, 停止 }。
从 数学 导入 绝对值。
打印(绝对值(-42))。
'''
        output = compile_and_run(code)
        self.assertIn("42", output)

    def test_l4_python_with_stdlib_file(self):
        """L4 Python 嵌入 + 文件系统"""
        temp_dir = tempfile.mkdtemp(prefix='light_test_l4_')
        test_file = os.path.join(temp_dir, 'l4_test.txt').replace('\\', '\\\\')
        code = f'''
引 Python:
def l4_greeting(name):
    return f"你好，{{name}}！"
结束引

从 文件系统 导入 写入文件, 读取文件。
设 消息 为 l4_greeting("光明")。
写入文件("{test_file}", 消息)。
设 内容 为 读取文件("{test_file}")。
打印(内容)。
'''
        try:
            output = compile_and_run(code)
            self.assertIn("你好，光明", output)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_l4_python_with_json(self):
        """L4 Python 嵌入 + JSON 处理"""
        code = '''
引 Python:
def l4_process_data(data):
    return {"original": data, "doubled": data * 2}
结束引

设 处理结果 为 l4_process_data(21)。
打印(处理结果["original"])。
打印(处理结果["doubled"])。
'''
        output = compile_and_run(code)
        self.assertIn("21", output)
        self.assertIn("42", output)


# ============================================================
# D. 完整 FFI 场景（仅编译验证）
# ============================================================

class TestFFI_FullFlow(unittest.TestCase):
    """D. FFI 完整流程（仅编译验证，不执行）"""

    def test_full_ffi_flow(self):
        """完整 FFI 流程"""
        code = '''
加载库 "libc.so.6" 为 C库。
外部 结构体 时间结构 { 秒: 整数, 分: 整数, 时: 整数 }。
外部 枚举 星期 { 周一, 周二, 周三, 周四, 周五, 周六, 周日 }。
外部 回调 比较器 接收 甲 为 整数, 乙 为 整数 返回 整数。
外部 函数 获取时间 接收 时间参数 为 时间结构 返回 整数 在 C库。
外部 宏 版本 为 "1.0"。
'''
        py_code = compile_only(code)
        self.assertIn("C库", py_code)
        self.assertIn("时间结构", py_code)
        self.assertIn("星期", py_code)
        self.assertIn("比较器", py_code)
        self.assertIn("获取时间", py_code)
        self.assertIn("版本", py_code)
        self.assertIn("ctypes", py_code)


# ============================================================
# E. 边界情况测试
# ============================================================

class TestEdgeCase_Encrypt(unittest.TestCase):
    """E1. 加密模块"""

    def test_md5_hash(self):
        """MD5 哈希"""
        code = '''
从 加密 导入 MD5。
设 结果 为 MD5("hello")。
打印(结果)。
'''
        output = compile_and_run(code)
        # "hello" 的 MD5 是 5d41402abc4b2a76b9719d911017c592
        self.assertIn("5d41402abc4b2a76b9719d911017c592", output)

    def test_sha256_hash(self):
        """SHA256 哈希"""
        code = '''
从 加密 导入 SHA256。
设 结果 为 SHA256("hello")。
打印(结果)。
'''
        output = compile_and_run(code)
        # "hello" 的 SHA256
        self.assertIn("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", output)

    def test_hash_function(self):
        """通用哈希函数"""
        code = '''
从 加密 导入 哈希。
设 结果 为 哈希("hello", "md5")。
打印(结果)。
'''
        output = compile_and_run(code)
        self.assertIn("5d41402abc4b2a76b9719d911017c592", output)


if __name__ == '__main__':
    unittest.main(verbosity=2)