"""
段言模式匹配增强测试

测试内容：
1. 守卫条件：情况 模式 若 条件
2. 嵌套模式：列表嵌套、模式组合
3. 绑定变量：模式中捕获变量
4. 解构赋值：设 a, b = [1, 2]
5. 空列表/空值模式
6. 多值匹配场景
"""

import sys
import os
import io
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def run_light(code: str) -> str:
    """使用 src 后端解析并执行段言代码，返回输出"""
    parser = LightParser()
    module = parser.parse(code)
    generator = PythonCodeGenerator()
    py_code = generator.generate(module)
    
    # 执行生成的 Python 代码，捕获输出
    output = io.StringIO()
    local_vars = {}
    try:
        with redirect_stdout(output):
            exec(py_code, {}, local_vars)
    except SystemExit:
        pass
    result = output.getvalue().strip()
    return result


def _compile(duan_code: str) -> str:
    """编译段言代码，返回Python源码"""
    parser = LightParser()
    module = parser.parse(duan_code)
    generator = PythonCodeGenerator()
    return generator.generate(module)


def test_guard_condition():
    """守卫条件：情况 模式 若 条件"""
    result = run_light('''
设 分数 为 85。
匹配 分数：
  情况 100：
    打印 "满分"。
  情况 分数 若 分数 大于 80：
    打印 "优秀"。
  情况 _：
    打印 "加油"。
结束。
''')
    assert result == "优秀", f"Expected '优秀', got '{result}'"


def test_guard_condition_false():
    """守卫条件失败时走通配符"""
    result = run_light('''
设 分数 为 60。
匹配 分数：
  情况 100：
    打印 "满分"。
  情况 分数 若 分数 大于 80：
    打印 "优秀"。
  情况 _：
    打印 "加油"。
结束。
''')
    assert result == "加油", f"Expected '加油', got '{result}'"


def test_guard_with_multiple_conditions():
    """守卫条件中使用且/或"""
    result = run_light('''
设 年龄 为 25。
匹配 年龄：
  情况 年龄 若 年龄 大于 0 且 年龄 小于 18：
    打印 "未成年"。
  情况 年龄 若 年龄 大于 等于 18 且 年龄 小于 60：
    打印 "成年"。
  情况 _：
    打印 "老年"。
结束。
''')
    assert result == "成年", f"Expected '成年', got '{result}'"


def test_list_pattern():
    """列表模式匹配"""
    result = run_light('''
设 列表 为 [1, 2, 3]。
匹配 列表：
  情况 [1, 2, 3]：
    打印 "一二三"。
  情况 _：
    打印 "其他"。
结束。
''')
    assert result == "一二三", f"Expected '一二三', got '{result}'"


def test_list_pattern_wildcard():
    """列表通配符模式"""
    result = run_light('''
设 列表 为 [1, 2, 3]。
匹配 列表：
  情况 [1, _]：
    打印 "两个元素"。
  情况 [1, _, _]：
    打印 "三个元素"。
  情况 _：
    打印 "其他"。
结束。
''')
    assert result == "三个元素", f"Expected '三个元素', got '{result}'"


def test_variable_binding():
    """变量绑定模式"""
    result = run_light('''
设 数值 为 42。
匹配 数值：
  情况 甲：
    打印 "绑定了" + 转字符串(甲)。
结束。
''')
    assert "绑定了42" in result, f"Expected '绑定了42', got '{result}'"


def test_type_check_pattern():
    """类型检查模式：类型 变量名"""
    result = run_light('''
设 值 为 "你好"。
匹配 值：
  情况 整数 甲：
    打印 "整数：" + 转字符串(甲)。
  情况 文本 甲：
    打印 "文本：" + 甲。
结束。
''')
    assert "文本：你好" in result, f"Expected '文本：你好', got '{result}'"


def test_boolean_pattern():
    """布尔模式匹配"""
    result = run_light('''
设 标志 为 真。
匹配 标志：
  情况 真：
    打印 "开启"。
  情况 假：
    打印 "关闭"。
结束。
''')
    assert result == "开启", f"Expected '开启', got '{result}'"


def test_nested_pattern():
    """嵌套列表模式"""
    result = run_light('''
设 数据 为 [[1, 2], [3, 4]]。
匹配 数据：
  情况 [[1, 2], [3, 4]]：
    打印 "匹配二维"。
  情况 _：
    打印 "不匹配"。
结束。
''')
    assert result == "匹配二维", f"Expected '匹配二维', got '{result}'"


def test_combined_guard_and_binding():
    """守卫条件与变量绑定组合"""
    result = run_light('''
设 值 为 7。
匹配 值：
  情况 甲 若 甲 大于 5：
    打印 "大于5：" + 转字符串(甲)。
  情况 _：
    打印 "不大于5"。
结束。
''')
    assert "大于5：7" in result, f"Expected '大于5：7', got '{result}'"


def test_empty_list_pattern():
    """空列表模式"""
    result = run_light('''
设 列表 为 []。
匹配 列表：
  情况 []：
    打印 "空列表"。
  情况 _：
    打印 "非空"。
结束。
''')
    assert result == "空列表", f"Expected '空列表', got '{result}'"


def test_string_pattern():
    """字符串模式匹配"""
    result = run_light('''
设 名称 为 "admin"。
匹配 名称：
  情况 "admin"：
    打印 "管理员"。
  情况 "user"：
    打印 "用户"。
  情况 _：
    打印 "未知"。
结束。
''')
    assert result == "管理员", f"Expected '管理员', got '{result}'"


def test_null_pattern():
    """空值模式匹配"""
    result = run_light('''
设 值 为 空。
匹配 值：
  情况 空：
    打印 "空值"。
  情况 _：
    打印 "非空"。
结束。
''')
    assert result == "空值", f"Expected '空值', got '{result}'"


def test_nested_match():
    """嵌套匹配语句"""
    result = run_light('''
设 值 为 2。
匹配 值：
  情况 1：
    打印 "一"。
  情况 2：
    打印 "二"。
  情况 _：
    打印 "其他"。
结束。
''')
    assert result == "二", f"Expected '二', got '{result}'"


def test_destructuring_tuple():
    """元组解构赋值：设 a, b = 列表"""
    result = run_light('''
设 数据 为 [10, 20]。
设 甲, 乙 为 数据。
打印 转字符串(甲) + "," + 转字符串(乙)。
''')
    assert result == "10,20", f"Expected '10,20', got '{result}'"


def test_destructuring_list():
    """列表解构赋值：设 [甲, 乙] 为 列表"""
    result = run_light('''
设 数据 为 [1, 2]。
设 [甲, 乙] 为 数据。
打印 转字符串(甲) + "," + 转字符串(乙)。
''')
    assert result == "1,2", f"Expected '1,2', got '{result}'"


def test_destructuring_with_function():
    """解构赋值与函数返回值"""
    result = run_light('''
段落 获取坐标：
  返回 [3, 4]。
结束。

设 甲, 乙 为 获取坐标()。
打印 转字符串(甲) + "," + 转字符串(乙)。
''')
    assert result == "3,4", f"Expected '3,4', got '{result}'"


def test_match_with_expression_guard():
    """使用 如果 关键字作为守卫条件"""
    result = run_light('''
设 值 为 15。
匹配 值：
  情况 甲 如果 甲 大于 10：
    打印 "大于10"。
  情况 _：
    打印 "不大于10"。
结束。
''')
    assert result == "大于10", f"Expected '大于10', got '{result}'"


def test_multi_value_match():
    """多值匹配场景"""
    result = run_light('''
设 状态码 为 404。
匹配 状态码：
  情况 200：
    打印 "成功"。
  情况 301：
    打印 "重定向"。
  情况 302：
    打印 "重定向"。
  情况 404：
    打印 "未找到"。
  情况 500：
    打印 "服务器错误"。
  情况 _：
    打印 "未知状态"。
结束。
''')
    assert result == "未找到", f"Expected '未找到', got '{result}'"


def test_match_with_guard_and_type():
    """守卫条件与类型检查组合"""
    result = run_light('''
设 值 为 "hello"。
匹配 值：
  情况 文本 甲 若 长度(甲) 大于 5：
    打印 "长文本"。
  情况 文本 甲：
    打印 "短文本：" + 甲。
  情况 _：
    打印 "非文本"。
结束。
''')
    assert "短文本" in result, f"Expected '短文本', got '{result}'"


def test_wildcard_fallback():
    """通配符兜底"""
    result = run_light('''
设 值 为 99。
匹配 值：
  情况 1：
    打印 "一"。
  情况 2：
    打印 "二"。
  情况 _：
    打印 "其他"。
结束。
''')
    assert result == "其他", f"Expected '其他', got '{result}'"


if __name__ == '__main__':
    tests = [
        ("守卫条件", test_guard_condition),
        ("守卫条件失败", test_guard_condition_false),
        ("守卫条件多条件", test_guard_with_multiple_conditions),
        ("列表模式", test_list_pattern),
        ("列表通配符", test_list_pattern_wildcard),
        ("变量绑定", test_variable_binding),
        ("类型检查模式", test_type_check_pattern),
        ("布尔模式", test_boolean_pattern),
        ("嵌套模式", test_nested_pattern),
        ("守卫+绑定组合", test_combined_guard_and_binding),
        ("空列表模式", test_empty_list_pattern),
        ("字符串模式", test_string_pattern),
        ("空值模式", test_null_pattern),
        ("嵌套匹配", test_nested_match),
        ("元组解构", test_destructuring_tuple),
        ("列表解构", test_destructuring_list),
        ("函数返回值解构", test_destructuring_with_function),
        ("表达式守卫", test_match_with_expression_guard),
        ("多值匹配", test_multi_value_match),
        ("守卫+类型组合", test_match_with_guard_and_type),
        ("通配符兜底", test_wildcard_fallback),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  [OK] {name}")
            passed += 1
        except Exception as e:
            import traceback
            print(f"  [失败] {name}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n总计: {len(tests)}  |  通过: {passed}  |  失败: {failed}")
    sys.exit(0 if failed == 0 else 1)