# -*- coding: utf-8 -*-
"""
光明 v3.3 向后兼容性测试

验证 v4.0 编译器完整支持 v3.3 语法：
- 设变量（定义/赋值）
- 印输出（打印/输出）
- 若条件（如果/否则）
- 重复循环（当/遍历）
- 段函数（段落/函数定义）
- 模块导入
- 标准库函数
"""

import sys
import os
import io
import pytest

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# =============================================================================
# 辅助函数：执行 v3.3 代码并捕获输出
# =============================================================================

def _exec_v3_code(code: str) -> str:
    """执行 v3.3 光明代码，返回 stdout 输出"""
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    parser = LightParser()
    module = parser.parse(code)

    generator = PythonCodeGenerator()
    py_code = generator.generate(module)

    # 捕获输出
    old_stdout = sys.stdout
    captured = io.StringIO()
    sys.stdout = captured
    try:
        exec_globals = {}
        exec(py_code, exec_globals)
    finally:
        sys.stdout = old_stdout

    return captured.getvalue()


# =============================================================================
# 测试用例 1-10: v3.3 基本语法构造
# =============================================================================

def test_v33_设变量_整数():
    """测试 v3.3 '设' 变量定义（整数）"""
    code = """
设 甲 为 42。
输出 甲。
"""
    output = _exec_v3_code(code)
    assert "42" in output, f"期望输出包含 '42'，实际输出: {output}"


def test_v33_设变量_字符串():
    """测试 v3.3 '设' 变量定义（字符串）"""
    code = """
设 名称 为 "光明"。
输出 名称。
"""
    output = _exec_v3_code(code)
    assert "光明" in output, f"期望输出包含 '光明'，实际输出: {output}"


def test_v33_印输出_多参数():
    """测试 v3.3 '输出' 多参数打印"""
    code = """
输出 "答案:", 42。
"""
    output = _exec_v3_code(code)
    assert "答案" in output and "42" in output, f"期望输出包含 '答案' 和 '42'，实际输出: {output}"


def test_v33_若条件_真():
    """测试 v3.3 '如果' 条件判断（真分支）"""
    code = """
设 甲 为 10。
如果 甲 大于 5：
    输出 "甲大于5"。
否则：
    输出 "甲不大于5"。
"""
    output = _exec_v3_code(code)
    assert "甲大于5" in output, f"期望输出 '甲大于5'，实际输出: {output}"


def test_v33_若条件_假():
    """测试 v3.3 '如果' 条件判断（否则分支）"""
    code = """
设 甲 为 2。
如果 甲 大于 5：
    输出 "甲大于5"。
否则：
    输出 "甲不大于5"。
"""
    output = _exec_v3_code(code)
    assert "甲不大于5" in output, f"期望输出 '甲不大于5'，实际输出: {output}"


def test_v33_当循环():
    """测试 v3.3 '当' 循环"""
    code = """
设 计数 为 1。
设 总和 为 0。
当 计数 小于等于 5：
    总和 等于 总和 加 计数。
    计数 等于 计数 加 1。
输出 总和。
"""
    output = _exec_v3_code(code)
    assert "15" in output, f"1到5的和应为15，实际输出: {output}"


def test_v33_段函数_无参数():
    """测试 v3.3 '段落' 函数定义（无参数）"""
    code = """
段落 打招呼 接收：
    输出 "你好！"。
打招呼()。
"""
    output = _exec_v3_code(code)
    assert "你好" in output, f"期望输出 '你好'，实际输出: {output}"


def test_v33_段函数_带参数():
    """测试 v3.3 '段落' 函数定义（带参数）"""
    code = """
段落 加法 接收 a, b：
    返回 a 加 b。
输出 加法(3, 4)。
"""
    output = _exec_v3_code(code)
    assert "7" in output, f"3+4应为7，实际输出: {output}"


def test_v33_段函数_递归():
    """测试 v3.3 递归函数（阶乘）"""
    code = """
段落 阶乘 接收 n：
    如果 n 小于等于 1：
        返回 1。
    返回 n 乘 阶乘(n 减 1)。
输出 阶乘(5)。
"""
    output = _exec_v3_code(code)
    assert "120" in output, f"5!应为120，实际输出: {output}"


def test_v33_遍历循环():
    """测试 v3.3 '遍历' 循环"""
    code = """
设 结果 为 0。
遍历 i 于 1 至 5：
    结果 等于 结果 加 i。
输出 结果。
"""
    output = _exec_v3_code(code)
    assert "15" in output, f"1到5的和应为15，实际输出: {output}"


# =============================================================================
# 测试用例 11-14: v3.3 模块和标准库
# =============================================================================

def test_v33_数学运算_混合():
    """测试 v3.3 混合数学运算"""
    code = """
设 甲 为 10。
设 乙 为 3。
输出 甲 加 乙。
输出 甲 减 乙。
输出 甲 乘 乙。
输出 甲 除 乙。
"""
    output = _exec_v3_code(code)
    assert "13" in output, f"10+3应为13，实际输出: {output}"
    assert "7" in output, f"10-3应为7，实际输出: {output}"
    assert "30" in output, f"10*3应为30，实际输出: {output}"


def test_v33_字符串操作():
    """测试 v3.3 字符串连接和操作"""
    code = """
设 问候 为 "你好，" 加 "光明"。
输出 问候。
"""
    output = _exec_v3_code(code)
    assert "你好，光明" in output, f"期望 '你好，光明'，实际输出: {output}"


def test_v33_转串函数():
    """测试 v3.3 转串（类型转换）函数"""
    code = """
设 数字 为 42。
输出 "数字是" 加 转串(数字)。
"""
    output = _exec_v3_code(code)
    assert "数字是42" in output, f"期望 '数字是42'，实际输出: {output}"


def test_v33_嵌套条件():
    """测试 v3.3 嵌套条件判断"""
    code = """
设 分数 为 85。
如果 分数 大于等于 90：
    输出 "优秀"。
否则：
    如果 分数 大于等于 80：
        输出 "良好"。
    否则：
        输出 "继续努力"。
"""
    output = _exec_v3_code(code)
    assert "良好" in output, f"85分应输出'良好'，实际输出: {output}"


# =============================================================================
# 测试用例 15-16: v3.3 列表和字典
# =============================================================================

def test_v33_列表操作():
    """测试 v3.3 列表创建和操作"""
    code = """
设 列表 为 列(1, 2, 3, 4, 5)。
输出 列表长度(列表)。
输出 列表获取(列表, 0)。
"""
    output = _exec_v3_code(code)
    assert "5" in output, f"列表长度应为5，实际输出: {output}"
    assert "1" in output, f"列表第一个元素应为1，实际输出: {output}"


def test_v33_字典操作():
    """测试 v3.3 字典创建和操作"""
    code = """
设 字典 为 字典创建()。
字典设置(字典, "名称", "光明")。
字典设置(字典, "版本", "3.3")。
输出 字典获取(字典, "名称")。
输出 字典获取(字典, "版本")。
"""
    output = _exec_v3_code(code)
    assert "光明" in output, f"期望 '光明'，实际输出: {output}"
    assert "3.3" in output, f"期望 '3.3'，实际输出: {output}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])