"""
光明（Light）编程语言 - 第三批现代语言特性测试

测试内容：
1. 字符串插值 — "你好，{名字}"
2. 列表推导 — [表达式 遍历 变量 之 列表]
3. 匿名函数 — 接收 甲：返回 甲 乘 甲。
4. 模式匹配 — 匹配 值：情况 ... 结束。
"""

import sys
import os
import io
from contextlib import redirect_stdout

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'antlrparser'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'antlrparser', 'light_parser'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from light_visitor import LightParser
    from code_generator_unified import UnifiedCodeGenerator
except ImportError:
    import pytest
    pytest.skip("ANTLR parser not available (missing generated LightLangParser module)", allow_module_level=True)


def run_light(code: str) -> str:
    """解析并执行光明代码，返回输出"""
    parser = LightParser()
    module = parser.parse(code)
    if not module:
        raise AssertionError(f"Parse failed: {parser.errors}")
    
    gen = UnifiedCodeGenerator()
    py_code = gen.generate(module)
    
    f = io.StringIO()
    with redirect_stdout(f):
        exec(py_code, {'__name__': '__main__', '__file__': 'test.light'})
    return f.getvalue().strip()


class TestStringInterpolation:
    """字符串插值测试"""
    
    def test_simple_variable(self):
        """简单变量插值"""
        result = run_light('设 名字 为 "世界"。打印 "你好，{名字}"。')
        assert result == "你好，世界", f"Expected '你好，世界', got '{result}'"
    
    def test_expression_in_interpolation(self):
        """插值中包含表达式"""
        result = run_light('设 甲 为 10。打印 "值={甲}，平方={甲 乘 甲}"。')
        assert result == "值=10，平方=100", f"Expected '值=10，平方=100', got '{result}'"
    
    def test_multiple_interpolations(self):
        """多个插值表达式"""
        result = run_light('设 甲 为 3。设 乙 为 4。打印 "{甲}加{乙}等于{甲 加 乙}"。')
        assert result == "3加4等于7", f"Expected '3加4等于7', got '{result}'"
    
    def test_plain_string_no_interpolation(self):
        """普通字符串（无插值）"""
        result = run_light('打印 "你好世界"。')
        assert result == "你好世界", f"Expected '你好世界', got '{result}'"


class TestListComprehension:
    """列表推导测试"""
    
    def test_simple_comprehension(self):
        """简单列表推导"""
        result = run_light('设 列表 为 [甲 乘 甲 遍历 甲 之 [1, 2, 3]]。打印 列表。')
        assert result == "[1, 4, 9]", f"Expected '[1, 4, 9]', got '{result}'"
    
    def test_comprehension_with_filter(self):
        """带过滤条件的列表推导"""
        result = run_light('设 偶数 为 [甲 遍历 甲 之 [1, 2, 3, 4, 5, 6] 如果 甲 模 2 等于 0]。打印 偶数。')
        assert result == "[2, 4, 6]", f"Expected '[2, 4, 6]', got '{result}'"
    
    def test_comprehension_transform(self):
        """列表推导中的变换"""
        result = run_light('设 倍数 为 [甲 乘 2 遍历 甲 之 [1, 2, 3]]。打印 倍数。')
        assert result == "[2, 4, 6]", f"Expected '[2, 4, 6]', got '{result}'"


class TestLambdaExpression:
    """匿名函数测试"""
    
    def test_simple_lambda(self):
        """简单匿名函数"""
        result = run_light('设 平方 为 接收 甲：返回 甲 乘 甲。打印 平方(5)。')
        assert result == "25", f"Expected '25', got '{result}'"
    
    def test_lambda_multiple_params(self):
        """多参数匿名函数"""
        result = run_light('设 加法 为 接收 甲, 乙：返回 甲 加 乙。打印 加法(3, 7)。')
        assert result == "10", f"Expected '10', got '{result}'"
    
    def test_lambda_in_expression(self):
        """匿名函数在表达式中使用"""
        result = run_light('设 乘以二 为 接收 甲：返回 甲 乘 2。打印 乘以二(8)。')
        assert result == "16", f"Expected '16', got '{result}'"


class TestMatchStatement:
    """模式匹配测试"""
    
    def test_simple_match(self):
        """简单模式匹配"""
        result = run_light('''设 等级 为 2。
匹配 等级：
情况 1：
  打印 "低"。
情况 2：
  打印 "中"。
情况 3：
  打印 "高"。
结束。''')
        assert result == "中", f"Expected '中', got '{result}'"
    
    def test_match_with_wildcard(self):
        """带通配符的模式匹配"""
        result = run_light('''设 分数 为 85。
匹配 分数：
情况 100：
  打印 "满分"。
情况 _：
  打印 "未满分"。
结束。''')
        assert result == "未满分", f"Expected '未满分', got '{result}'"
    
    def test_match_string(self):
        """字符串模式匹配"""
        result = run_light('''设 颜色 为 "红"。
匹配 颜色：
情况 "红"：
  打印 "停止"。
情况 "绿"：
  打印 "通行"。
情况 _：
  打印 "注意"。
结束。''')
        assert result == "停止", f"Expected '停止', got '{result}'"


class TestCombinedFeatures:
    """组合特性测试"""
    
    def test_lambda_with_list_comprehension(self):
        """匿名函数与列表推导组合"""
        result = run_light('''设 加一 为 接收 甲：返回 甲 加 1。
设 结果 为 [加一(甲) 遍历 甲 之 [1, 2, 3]]。
打印 结果。''')
        assert result == "[2, 3, 4]", f"Expected '[2, 3, 4]', got '{result}'"
    
    def test_interpolation_with_comprehension_result(self):
        """字符串插值显示列表推导结果"""
        result = run_light('''设 平方 为 [甲 乘 甲 遍历 甲 之 [1, 2, 3]]。
打印 "平方列表：{平方}"。''')
        assert result == "平方列表：[1, 4, 9]", f"Expected '平方列表：[1, 4, 9]', got '{result}'"


# 运行所有测试
if __name__ == '__main__':
    test_classes = [
        TestStringInterpolation,
        TestListComprehension,
        TestLambdaExpression,
        TestMatchStatement,
        TestCombinedFeatures,
    ]
    
    total = 0
    passed = 0
    failed = 0
    
    for test_class in test_classes:
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                total += 1
                try:
                    getattr(instance, method_name)()
                    passed += 1
                    print(f'[PASS] {test_class.__name__}.{method_name}')
                except Exception as e:
                    failed += 1
                    print(f'[FAIL] {test_class.__name__}.{method_name}: {e}')
    
    print(f'\nTotal: {total}, Passed: {passed}, Failed: {failed}')
    if failed == 0:
        print('All tests passed!')
