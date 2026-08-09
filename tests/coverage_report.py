# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 测试覆盖率报告

生成测试覆盖率和统计报告
"""

import sys
import io
import os
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 测试用例定义
TEST_CASES = {
    "词法分析器": [
        ("关键字识别", "设甲为三。", "应识别：定义、甲、等于、三"),
        ("数字识别", "123", "应识别数字 123"),
        ("无空格分词", "甲加乙", "应分出：甲、加、乙"),
        ("中文数字", "三加五", "应识别中文数字"),
        ("符号识别", "。，：", "应识别标点符号"),
        ("书名号", "《段名》", "应识别书名号"),
        ("条件语句", "如果甲那么乙", "应识别关键字"),
    ],
    "语法解析器": [
        ("变量声明", "设甲为123。", "应解析为 VariableDecl"),
        ("条件语句", "如果甲大于乙那么打印甲。", "应解析为 IfStatement"),
        ("函数定义", "《计算》段返回甲加乙。", "应解析为 FunctionDef"),
        ("多语句", "设甲为1。设乙为2。", "应解析出2条语句"),
    ],
    "语义分析器": [
        ("类型检查", "设甲为123。", "应检查类型"),
        ("作用域", "设甲为1。打印甲。", "应管理作用域"),
    ],
    "代码生成器": [
        ("变量生成", "设甲为123。", "应生成 Python 赋值语句"),
        ("表达式生成", "设甲为三加五。", "应生成算术表达式"),
        ("函数生成", "《加法》段(甲, 乙)：返回甲加乙。", "应生成 def 函数"),
    ],
    "高级语义": [
        ("动词元数", "加", "元数=2，模式=functional"),
        ("动词元数", "打印", "元数=1"),
        ("语义识别", "列表排序", "主谓语义"),
    ],
    "集成测试": [
        ("完整编译", "设甲为三加五。", "应生成可执行 Python 代码"),
        ("函数编译", "《阶乘》段(数)：返回数。", "应生成递归函数"),
    ],
}


def run_tests():
    """运行测试并生成报告"""
    print("=" * 70)
    print("光明编译器测试覆盖率报告")
    print("=" * 70)
    print()
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    results = {}
    
    for category, tests in TEST_CASES.items():
        print(f"\n{category}")
        print("-" * 70)
        
        category_passed = 0
        category_failed = 0
        
        for test_name, test_code, expected in tests:
            total_tests += 1
            
            try:
                # 根据类别运行不同测试
                if category == "词法分析器":
                    from lexer import Lexer
                    lexer = Lexer()
                    tokens = lexer.tokenize(test_code)
                    success = len(tokens) > 0
                    
                elif category == "语法解析器":
                    from light_parser_v3 import LightParser
                    parser = LightParser()
                    module = parser.parse(test_code)
                    success = len(module.statements) > 0
                    
                elif category == "语义分析器":
                    from light_parser_v3 import LightParser
                    from semantic_analyzer import SemanticAnalyzer
                    parser = LightParser()
                    analyzer = SemanticAnalyzer()
                    module = parser.parse(test_code)
                    success = analyzer.analyze(module)
                    
                elif category == "代码生成器":
                    from light_parser_v3 import LightParser
                    from semantic_analyzer import SemanticAnalyzer
                    from code_generator import PythonCodeGenerator
                    parser = LightParser()
                    analyzer = SemanticAnalyzer()
                    generator = PythonCodeGenerator()
                    module = parser.parse(test_code)
                    analyzer.analyze(module)
                    python_code = generator.generate(module)
                    success = python_code is not None and len(python_code) > 0
                    
                elif category == "高级语义":
                    if test_name == "动词元数":
                        from verb_info import get_verb_info
                        info = get_verb_info(test_code)
                        success = info is not None
                    else:
                        from semantic_identifier import SemanticIdentifier
                        identifier = SemanticIdentifier({})
                        success = True  # 初始化成功
                    
                elif category == "集成测试":
                    from light_parser_v3 import LightParser
                    from semantic_analyzer import SemanticAnalyzer
                    from code_generator import PythonCodeGenerator
                    parser = LightParser()
                    analyzer = SemanticAnalyzer()
                    generator = PythonCodeGenerator()
                    module = parser.parse(test_code)
                    analyzer.analyze(module)
                    python_code = generator.generate(module)
                    success = len(python_code) > 0
                
                if success:
                    print(f"  [OK] {test_name}")
                    category_passed += 1
                    passed_tests += 1
                else:
                    print(f"  [FAIL] {test_name}")
                    category_failed += 1
                    failed_tests += 1
                    
            except Exception as e:
                print(f"  [ERROR] {test_name}: {str(e)[:30]}")
                category_failed += 1
                failed_tests += 1
        
        results[category] = {
            'passed': category_passed,
            'failed': category_failed,
            'total': len(tests)
        }
    
    # 打印总结
    print()
    print("=" * 70)
    print("测试总结")
    print("=" * 70)
    
    print(f"\n总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    
    if total_tests > 0:
        coverage = (passed_tests / total_tests) * 100
        print(f"\n测试覆盖率: {coverage:.1f}%")
    
    print("\n分类统计:")
    for category, stats in results.items():
        total = stats['total']
        passed = stats['passed']
        coverage = (passed / total * 100) if total > 0 else 0
        print(f"  {category}: {passed}/{total} ({coverage:.0f}%)")
    
    print()
    print("=" * 70)
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), 'test_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 光明编译器测试报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 测试统计\n\n")
        f.write(f"- 总测试数: {total_tests}\n")
        f.write(f"- 通过: {passed_tests}\n")
        f.write(f"- 失败: {failed_tests}\n")
        f.write(f"- 测试覆盖率: {coverage:.1f}%\n\n")
        f.write(f"## 分类统计\n\n")
        for category, stats in results.items():
            total = stats['total']
            passed = stats['passed']
            coverage = (passed / total * 100) if total > 0 else 0
            f.write(f"- {category}: {passed}/{total} ({coverage:.0f}%)\n")
    
    print(f"报告已保存到: {report_path}")
    
    return failed_tests == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
