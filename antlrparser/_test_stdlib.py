"""
光明标准库扩展测试 - ANTLR 后端

测试新增的各个模块功能：
- 日期时间模块
- JSON 模块
- 哈希模块
- 正则表达式模块
- 数学/统计/随机函数
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_visitor import parse_source
from light_interpreter import Interpreter


def run_test(name, source, expected_contains=None):
    """运行单测"""
    print(f"\n=== {name} ===")
    module = parse_source(source)
    if module is None:
        print(f"  ✗ 解析失败")
        return False
    
    interp = Interpreter()
    try:
        result = interp.interpret(module)
        output = '\n'.join(interp.output_lines)
        print(f"  输出: {output}")
        
        if expected_contains:
            for exp in expected_contains:
                if exp in output:
                    print(f"  ✓ 包含期望输出: '{exp}'")
                else:
                    print(f"  ✗ 缺失期望输出: '{exp}'")
                    return False
        
        # 解释完成即认为成功
        print(f"  ✓ 通过")
        return True
    except Exception as e:
        print(f"  ✗ 执行错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_direct_test(name, func, args, expected_check=None):
    """通过直接调用内置函数测试"""
    print(f"\n=== {name} ===")
    try:
        interp = Interpreter()
        # 将 Python 值包装为 LightValue
        from light_interpreter import LightValue
        
        light_args = []
        for a in args:
            if isinstance(a, bool):
                light_args.append(LightValue(a, '布尔'))
            elif isinstance(a, int):
                light_args.append(LightValue(a, '数'))
            elif isinstance(a, float):
                light_args.append(LightValue(a, '数'))
            elif isinstance(a, str):
                light_args.append(LightValue(a, '串'))
            elif isinstance(a, list):
                light_args.append(LightValue(a, '列'))
            elif isinstance(a, dict):
                light_args.append(LightValue(a, '典'))
            elif a is None:
                light_args.append(LightValue(None, '空'))
            else:
                light_args.append(LightValue(a))
        
        result = func(light_args)
        print(f"  结果: {result.value} (类型: {result.type_name})")
        
        if expected_check and not expected_check(result):
            print(f"  ✗ 类型断言失败")
            return False
        
        print(f"  ✓ 通过")
        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all():
    """运行所有测试"""
    passed = 0
    failed = 0
    
    print("=" * 60)
    print("光明标准库扩展测试")
    print("=" * 60)
    
    # ========== 测试1: 随机整数 ==========
    def check_random_int(r):
        return isinstance(r.value, int) and 1 <= r.value <= 100
    if run_direct_test('随机整数', Interpreter()._builtin_random_int, [1, 100], check_random_int):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试2: 随机浮点 ==========
    def check_random_float(r):
        return isinstance(r.value, float) and 0 <= r.value < 1
    if run_direct_test('随机浮点', Interpreter()._builtin_random_float, [], check_random_float):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试3: 阶乘 ==========
    def check_factorial(r):
        return r.value == 120
    if run_direct_test('阶乘(5)', Interpreter()._builtin_factorial, [5], check_factorial):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试4: 平均数 ==========
    def check_mean(r):
        return r.value == 3.0
    if run_direct_test('平均数([1,2,3,4,5])', Interpreter()._builtin_mean, [[1, 2, 3, 4, 5]], check_mean):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试5: 中位数 ==========
    def check_median(r):
        return r.value == 3.0
    if run_direct_test('中位数([1,2,3,4,5])', Interpreter()._builtin_median, [[1, 2, 3, 4, 5]], check_median):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试6: 求和 ==========
    if run_direct_test('求和([10,20,30])', Interpreter()._builtin_sum, [[10, 20, 30]]):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试7: 圆周率 ==========
    def check_pi(r):
        return r.type_name == '数' and r.value > 3.14
    if run_direct_test('圆周率', Interpreter()._builtin_pi, [], check_pi):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试8: 自然常数 ==========
    def check_e(r):
        return r.type_name == '数' and r.value > 2.7
    if run_direct_test('自然常数', Interpreter()._builtin_e, [], check_e):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试9: JSON 解析 ==========
    def check_parse_json(r):
        return r.type_name == '典' and r.value.get('name') == '光明'
    if run_direct_test('解析JSON', Interpreter()._builtin_parse_json, ['{"name": "光明", "version": 1}'], check_parse_json):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试10: JSON 序列化 ==========
    def check_stringify_json(r):
        return isinstance(r.value, str) and '光明' in r.value
    if run_direct_test('序列化JSON', Interpreter()._builtin_stringify_json, [{'name': '光明'}], check_stringify_json):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试11: 当前时间 ==========
    def check_current_time(r):
        return isinstance(r.value, str) and len(r.value) > 10
    if run_direct_test('当前时间', Interpreter()._builtin_current_time, [], check_current_time):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试12: 当前日期 ==========
    def check_current_date(r):
        return isinstance(r.value, str) and '-' in r.value
    if run_direct_test('当前日期', Interpreter()._builtin_current_date, [], check_current_date):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试13: 时间戳 ==========
    def check_timestamp(r):
        return isinstance(r.value, (int, float)) and r.value > 1e9
    if run_direct_test('时间戳', Interpreter()._builtin_timestamp, [], check_timestamp):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试14: 日期差 ==========
    def check_date_diff(r):
        return r.value == 2
    if run_direct_test('日期差(2026-06-14, 2026-06-16)', Interpreter()._builtin_date_diff, ['2026-06-14', '2026-06-16'], check_date_diff):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试15: MD5 ==========
    def check_md5(r):
        return isinstance(r.value, str) and len(r.value) == 32
    if run_direct_test('MD5("光明")', Interpreter()._builtin_md5, ['光明'], check_md5):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试16: SHA256 ==========
    def check_sha256(r):
        return isinstance(r.value, str) and len(r.value) == 64
    if run_direct_test('SHA256("光明")', Interpreter()._builtin_sha256, ['光明'], check_sha256):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试17: Base64 编解码 ==========
    if run_direct_test('Base64编码("光明")', Interpreter()._builtin_base64_encode, ['光明']):
        passed += 1
    else:
        failed += 1
    
    def check_b64_decode(r):
        return r.value == '光明'
    if run_direct_test('Base64解码(编码结果)', Interpreter()._builtin_base64_decode, ['5q616KiA'], check_b64_decode):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试18: 正则匹配 ==========
    def check_regex_match(r):
        return r.value is not None and '光明' in str(r.value)
    if run_direct_test('正则匹配("段\\\\w+", "光明语言")', Interpreter()._builtin_regex_match, [r'段\w+', '光明语言'], check_regex_match):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试19: 正则搜索 ==========
    def check_regex_search(r):
        return r.value is not None
    if run_direct_test('正则搜索("\\\\d+", "abc123def456")', Interpreter()._builtin_regex_search, [r'\d+', 'abc123def456'], check_regex_search):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试20: 正则查找所有 ==========
    def check_regex_find_all(r):
        return isinstance(r.value, list) and len(r.value) == 3
    if run_direct_test('正则查找所有("\\\\d+", "a1b2c3")', Interpreter()._builtin_regex_find_all, [r'\d+', 'a1b2c3'], check_regex_find_all):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试21: 正则替换 ==========
    def check_regex_replace(r):
        return r.value == 'hello-world-2026'
    if run_direct_test('正则替换("[\\\\s]+", "-", "hello world 2026")', Interpreter()._builtin_regex_replace, [r'\s+', '-', 'hello world 2026'], check_regex_replace):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试22: 正则分割 ==========
    def check_regex_split(r):
        return isinstance(r.value, list) and len(r.value) == 3
    if run_direct_test('正则分割("[,\\\\s]+", "a, b, c")', Interpreter()._builtin_regex_split, [r'[,\s]+', 'a, b, c'], check_regex_split):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试23: 光明源码执行 - 随机整数 ==========
    source1 = """设 结果 为 随机整数(1, 100)。
打印(结果)。
"""
    if run_test('源码:随机整数', source1):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试24: 光明源码执行 - JSON ==========
    source2 = """设 数据 为 parseJSON('{"name": "光明", "year": 2026}')。
打印(数据)。
"""
    if run_test('源码:解析JSON', source2):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试25: 光明源码执行 - 日期时间 ==========
    source3 = """设 现在 为 当前时间()。
打印(现在)。
设 今日 为 当前日期()。
打印(今日)。
设 时间 为 时间戳()。
打印(时间)。
"""
    if run_test('源码:日期时间', source3):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试26: 光明源码执行 - 正则 ==========
    source4 = """设 结果 为 查找所有('\\\\d+', 'a1b2c3')。
打印(结果)。
设 替换后 为 替换('世界', '光明', '你好世界')。
打印(替换后)。
"""
    if run_test('源码:正则', source4):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试27: 光明源码执行 - 哈希 ==========
    source5 = """设 md5值 为 MD5('光明')。
打印(md5值)。
设 b64 为 Base64编码('光明')。
打印(b64)。
"""
    if run_test('源码:哈希', source5):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试28: 光明源码执行 - 数学统计 ==========
    source6 = """设 阶乘结果 为 阶乘(5)。
打印(阶乘结果)。
设 和数据 为 [1, 2, 3, 4, 5]。
设 平均值 为 平均数(和数据)。
打印(平均值)。
"""
    if run_test('源码:数学统计', source6):
        passed += 1
    else:
        failed += 1
    
    # ========== 测试29: formatTime 格式化时间 ==========
    def check_format_time(r):
        return r.value == '2026年06月16日'
    if run_direct_test('格式化时间', Interpreter()._builtin_format_time, ['2026-06-16 10:30:00', '%Y年%m月%d日'], check_format_time):
        passed += 1
    else:
        failed += 1
    
    # ========== 汇总 ==========
    print("\n" + "=" * 60)
    print(f"  通过: {passed}, 失败: {failed}, 总计: {passed + failed}")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = test_all()
    sys.exit(0 if success else 1)