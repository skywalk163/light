"""测试三元条件表达式（ANTLR 后端）"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'antlrparser'))

try:
    from light_visitor import LightParser
    from code_generator_unified import UnifiedCodeGenerator
except ImportError:
    import pytest
    pytest.skip("ANTLR parser not available (missing generated LightLangParser module)", allow_module_level=True)


def run_light(code):
    """使用 ANTLR 后端解析并执行光明代码"""
    parser = LightParser()
    module = parser.parse(code)
    if parser.errors:
        return f"解析错误: {'; '.join(parser.errors)}"
    gen = UnifiedCodeGenerator()
    py_code = gen.generate(module)
    import io
    from contextlib import redirect_stdout
    f = io.StringIO()
    with redirect_stdout(f):
        exec(py_code)
    return f.getvalue().strip()


tests = [
    ("设 甲 为 如果 1 小于 2 那么 10 否则 20。打印 甲。", "10"),
    ("设 甲 为 如果 1 大于 2 那么 10 否则 20。打印 甲。", "20"),
    ('打印 如果 真 那么 "是" 否则 "否"。', "是"),
    ('打印 如果 假 那么 "是" 否则 "否"。', "否"),
    ("设 甲 为 10。打印 如果 甲 大于 5 那么 30 否则 40。", "30"),
    ("设 甲 为 2。打印 如果 甲 大于 5 那么 30 否则 40。", "40"),
    ("打印 如果 3 大于 1 那么 100 否则 200。", "100"),
    ("设 结果 为 如果 1 等于 1 那么 42 否则 0。打印 结果。", "42"),
    # 没有否则分支（应返回空值）
    ('打印 如果 假 那么 "条件成立"。', "None"),
    # 三元表达式作为函数参数
    ("打印 如果 5 大于 3 那么 1 否则 2。", "1"),
    # 嵌套三元表达式
    ("设 甲 为 5。打印 如果 甲 大于 10 那么 100 否则 如果 甲 大于 0 那么 50 否则 0。", "50"),
    ("设 甲 为 -1。打印 如果 甲 大于 10 那么 100 否则 如果 甲 大于 0 那么 50 否则 0。", "0"),
    # 更复杂的三元表达式（包含运算）
    ("设 甲 为 6。打印 如果 甲 大于 5 那么 甲 乘 2 否则 甲 除 2。", "12"),
    ("设 甲 为 2。打印 如果 甲 大于 5 那么 甲 乘 2 否则 甲 除 2。", "1.0"),
]

passed = 0
failed = 0
for code, expected in tests:
    try:
        result = run_light(code)
        if result == str(expected):
            passed += 1
            print(f"[PASS] {code[:60]}")
        else:
            failed += 1
            print(f"[FAIL] {code[:60]}")
            print(f"       期望: {expected}, 实际: {result}")
    except Exception as e:
        failed += 1
        print(f"[FAIL] {code[:60]}")
        print(f"       错误: {type(e).__name__}: {e}")

print(f"\n总计: {passed + failed}, 通过: {passed}, 失败: {failed}")