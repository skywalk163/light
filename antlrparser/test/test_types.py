"""
光明 - 数据类型与运算测试

验证所有运算符、字符串、列表等数据类型的解析和 AST 结构
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_ast import (
    Module, VariableDeclaration, NumberLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, ListLiteral,
    BinaryOp, UnaryOp, Identifier,
    PrintStatement, IfStatement, ForeachStatement,
    WhileStatement, BreakStatement, ContinueStatement,
    ReturnStatement, SegmentName, SegmentDefinition
)
from light_visitor import LightParser


def test_arithmetic_operators():
    """测试算术运算符：加/减/乘/除(×/÷)/模/幂"""
    print("=" * 60)
    print("算术运算符测试")
    print("=" * 60)
    
    test_cases = [
        ("10加5", "BinaryOp", "加"),
        ("10减5", "BinaryOp", "减"),
        ("10乘5", "BinaryOp", "乘"),
        ("10×5", "BinaryOp", "乘"),
        ("10除5", "BinaryOp", "除"),
        ("10÷5", "BinaryOp", "除"),
        ("10模3", "BinaryOp", "模"),
        ("2幂3", "BinaryOp", "幂"),
    ]
    
    for expr, expected_type, expected_op in test_cases:
        source = f"定义结果等于{expr}。"
        parser = LightParser()
        module = parser.parse(source)
        assert module is not None, f"解析失败: {source}"
        
        decl = module.statements[0]
        assert hasattr(decl, 'value'), f"缺少 value 属性: {source}"
        
        value = decl.value
        value_type = type(value).__name__
        assert value_type == expected_type, f"期望 {expected_type}, 实际 {value_type}: {source}"
        
        if expected_type == "BinaryOp":
            assert value.operator == expected_op, f"期望运算符 '{expected_op}', 实际 '{value.operator}': {source}"
        
        print(f"  [+] {source:<30s} -> {value_type}({expected_op if expected_type=='BinaryOp' else ''})")
    
    return True


def test_comparison_operators():
    """测试比较运算符"""
    print("\n" + "=" * 60)
    print("比较运算符测试")
    print("=" * 60)
    
    operators = [
        ("大于", "大于"),
        ("小于", "小于"),
        ("等于", "等于"),
        ("不等于", "不等于"),
        ("大于等于", "大于等于"),
        ("小于等于", "小于等于"),
    ]
    
    for op_text, expected_op in operators:
        source = f"定义_结果等于10{op_text}5。"
        parser = LightParser()
        module = parser.parse(source)
        assert module is not None, f"解析失败: {source}"
        
        decl = module.statements[0]
        assert type(decl.value).__name__ == 'BinaryOp', f"期望 BinaryOp, 实际 {type(decl.value).__name__}: {source}"
        assert decl.value.operator == expected_op, f"期望 '{expected_op}', 实际 '{decl.value.operator}': {source}"
        
        print(f"  [+] {source:<35s} -> BinaryOp({expected_op})")
    
    return True


def test_logical_operators():
    """测试逻辑运算符：且/或/非"""
    print("\n" + "=" * 60)
    print("逻辑运算符测试")
    print("=" * 60)
    
    # 且/或
    op_cases = [
        ("真且假", "BinaryOp", "且"),
        ("真或假", "BinaryOp", "或"),
    ]
    for expr, expected_type, expected_op in op_cases:
        source = f"定义_结果等于{expr}。"
        parser = LightParser()
        module = parser.parse(source)
        assert module is not None, f"解析失败: {source}"
        value = module.statements[0].value
        assert type(value).__name__ == expected_type, f"期望 {expected_type}: {source}"
        if expected_type == "BinaryOp":
            assert value.operator == expected_op
        print(f"  [+] {source:<35s} -> {expected_type}({expected_op})")
    
    # 非（一元运算）
    source = "定义_结果等于非真。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 非真"
    value = module.statements[0].value
    assert type(value).__name__ == "UnaryOp", f"期望 UnaryOp, 实际 {type(value).__name__}"
    assert value.operator == "非", f"期望 '非', 实际 '{value.operator}'"
    print(f"  [+] {'定义_结果等于非真。':<35s} -> UnaryOp(非)")
    
    return True


def test_parentheses_priority():
    """测试括号改变优先级"""
    print("\n" + "=" * 60)
    print("括号/优先级测试")
    print("=" * 60)
    
    # (3+5)*2  vs  3+5*2
    cases = [
        ("(3加5)乘2", "BinaryOp", "乘"),  # 先加后乘
        ("3加5乘2", "BinaryOp", "加"),  # 乘优先，加在外面
    ]
    
    for expr, expected_type, expected_op in cases:
        source = f"定义_结果等于{expr}。"
        parser = LightParser()
        module = parser.parse(source)
        assert module is not None, f"解析失败: {source}"
        value = module.statements[0].value
        assert type(value).__name__ == expected_type, f"期望 {expected_type}: {source}"
        if expected_type == "BinaryOp":
            assert value.operator == expected_op, f"期望顶层运算符 '{expected_op}': {source}"
        print(f"  [+] {source:<35s} -> {expected_type}({expected_op})")
    
    return True


def test_string_literals():
    """测试字符串字面量"""
    print("\n" + "=" * 60)
    print("字符串测试")
    print("=" * 60)
    
    # 双引号字符串
    source = '定义_问候等于"你好世界"。'
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 双引号字符串"
    value = module.statements[0].value
    assert type(value).__name__ == 'StringLiteral', f"期望 StringLiteral: {type(value).__name__}"
    assert value.value == "你好世界", f"期望 '你好世界', 实际 '{value.value}'"
    print(f"  [+] 双引号: \"你好世界\" -> '{value.value}'")
    
    # 单引号字符串
    source = "定义_英文等于'hello'。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 单引号字符串"
    value = module.statements[0].value
    assert type(value).__name__ == 'StringLiteral'
    assert value.value == "hello", f"期望 'hello', 实际 '{value.value}'"
    print(f"  [+] 单引号: 'hello' -> '{value.value}'")
    
    return True


def test_list_literals():
    """测试列表字面量"""
    print("\n" + "=" * 60)
    print("列表测试")
    print("=" * 60)
    
    # 数字列表
    source = "定义_数字列等于【1, 2, 3】。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 列表"
    value = module.statements[0].value
    assert type(value).__name__ == 'ListLiteral', f"期望 ListLiteral: {type(value).__name__}"
    assert len(value.elements) == 3, f"期望 3 个元素, 实际 {len(value.elements)}"
    print(f"  [+] 数字列表: 【1, 2, 3】 -> {len(value.elements)} 个元素")
    
    # 混合类型列表
    source = '定义_混合列等于【1, "你好", 真, 空】。'
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 混合列表"
    value = module.statements[0].value
    assert type(value).__name__ == 'ListLiteral'
    assert len(value.elements) == 4, f"期望 4 个元素, 实际 {len(value.elements)}"
    
    elem_types = [type(e).__name__ for e in value.elements]
    print(f"  [+] 混合列表: 【1, \"你好\", 真, 空】 -> 元素类型: {elem_types}")
    
    # 空列表
    source = "定义_空列等于【】。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 空列表"
    value = module.statements[0].value
    assert type(value).__name__ == 'ListLiteral'
    assert len(value.elements) == 0, f"期望 0 个元素, 实际 {len(value.elements)}"
    print(f"  [+] 空列表: 【】 -> 0 个元素")
    
    return True


def test_boolean_null_literals():
    """测试布尔值和空值"""
    print("\n" + "=" * 60)
    print("布尔/空值测试")
    print("=" * 60)
    
    literals = [
        ("真", "BooleanLiteral", True),
        ("假", "BooleanLiteral", False),
        ("空", "NullLiteral", None),
    ]
    
    for lit, expected_type, expected_value in literals:
        source = f"定义_结果等于{lit}。"
        parser = LightParser()
        module = parser.parse(source)
        assert module is not None, f"解析失败: {source}"
        value = module.statements[0].value
        assert type(value).__name__ == expected_type, f"期望 {expected_type}: {source}"
        print(f"  [+] {lit:<8s} -> {expected_type}")
    
    return True


def test_complex_expressions():
    """测试复杂混合表达式"""
    print("\n" + "=" * 60)
    print("复杂表达式测试")
    print("=" * 60)
    
    cases = [
        ("(10加5)乘(20减15)除2", "运算链"),
        ("(10大于5)且(20小于30)", "逻辑+比较"),
        ("(3加(4乘5))减2", "嵌套括号"),
    ]
    
    for expr, desc in cases:
        source = f"定义_复合等于{expr}。"
        parser = LightParser()
        module = parser.parse(source)
        assert module is not None, f"解析失败: {source}"
        value = module.statements[0].value
        assert value is not None, f"表达式为 None: {source}"
        print(f"  [+] {desc:<15s}: {expr}")
    
    return True


def test_string_operations():
    """测试字符串运算：拼接、转义"""
    print("\n" + "=" * 60)
    print("字符串运算测试")
    print("=" * 60)
    
    # 字符串拼接
    source = '定义_结果等于"hello"加"world"。'
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 字符串拼接"
    value = module.statements[0].value
    assert type(value).__name__ == 'BinaryOp', f"期望 BinaryOp: {type(value).__name__}"
    assert value.operator == '加', f"期望运算符 '加': {value.operator}"
    assert value.left.value == 'hello', f"左值错误: {value.left.value}"
    assert value.right.value == 'world', f"右值错误: {value.right.value}"
    print(f"  [+] 字符串拼接: 'hello'加'world' -> BinaryOp(加)")
    
    # 转义序列 \n
    source = '定义_结果等于"第一行\\n第二行"。'
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 转义 \\n"
    value = module.statements[0].value
    assert value.value == "第一行\n第二行", f"\\n 转义错误: {repr(value.value)}"
    print(f"  [+] 转义 \\n: 正确解析为换行符")
    
    # 转义序列 \t
    source = '定义_结果等于"列1\\t列2"。'
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 转义 \\t"
    value = module.statements[0].value
    assert value.value == "列1\t列2", f"\\t 转义错误: {repr(value.value)}"
    print(f"  [+] 转义 \\t: 正确解析为制表符")
    
    # 转义序列 \\ (反斜杠)
    source = '定义_x等于"反斜杠\\\\符号"。'
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 转义 \\\\"
    value = module.statements[0].value
    assert value.value == '反斜杠\\符号', f"\\\\ 转义错误: {repr(value.value)}"
    print(f"  [+] 转义 \\\\: 正确解析为单反斜杠")
    
    # 转义序列 \" (引号)
    source = '定义_x等于"带\\"引号"。'
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 转义 \\\""
    value = module.statements[0].value
    assert value.value == '带"引号', f"\\\" 转义错误: {repr(value.value)}"
    print(f"  [+] 转义 \\\": 正确解析为双引号")
    
    # 变量与字符串拼接
    source = '定义_问候等于"你好"。定义_结果等于_问候加"，世界"。'
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 变量+字符串拼接"
    value = module.statements[1].value
    assert type(value).__name__ == 'BinaryOp'
    assert value.operator == '加', f"期望 '加': {value.operator}"
    print(f"  [+] 变量与字符串拼接: 变量加\",世界\" -> BinaryOp(加)")
    
    return True


def test_list_operations():
    """测试列表运算：索引访问、属性访问"""
    print("\n" + "=" * 60)
    print("列表运算测试")
    print("=" * 60)
    
    # 列表索引访问 [index]
    source = "定义_列等于【10, 20, 30】。定义_结果等于_列[0]。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 列表索引"
    value = module.statements[1].value
    assert type(value).__name__ == 'IndexAccess', f"期望 IndexAccess: {type(value).__name__}"
    assert type(value.obj).__name__ == 'Identifier', f"期望 Identifier: {type(value.obj).__name__}"
    assert type(value.index).__name__ == 'NumberLiteral', f"期望 NumberLiteral: {type(value.index).__name__}"
    assert value.index.value == 0, f"索引值错误: {value.index.value}"
    print(f"  [+] 列表索引: 列[0] -> IndexAccess(obj=Identifier, index=NumberLiteral(0))")
    
    # 另一种语法：对象之属性
    source = "定义_列等于【10, 20, 30】。定义_结果等于_列之长度。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 属性访问"
    value = module.statements[1].value
    assert type(value).__name__ == 'PropertyAccess', f"期望 PropertyAccess: {type(value).__name__}"
    assert value.property_name == '长度', f"属性名错误: {value.property_name}"
    print(f"  [+] 属性访问: 列之长度 -> PropertyAccess(prop=长度)")
    
    # 索引表达式（变量作为索引）
    source = "定义_列等于【10, 20, 30】。定义_索引等于1。定义_结果等于_列[_索引]。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 变量索引"
    value = module.statements[2].value
    assert type(value).__name__ == 'IndexAccess'
    assert type(value.index).__name__ == 'Identifier'
    print(f"  [+] 变量索引: 列[_索引] -> IndexAccess(index=Identifier)")
    
    # 空列表
    source = "定义_空列等于【】。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 空列表"
    value = module.statements[0].value
    assert type(value).__name__ == 'ListLiteral'
    assert len(value.elements) == 0, f"空列表元素数错误: {len(value.elements)}"
    print(f"  [+] 空列表: 【】 -> 0 个元素")
    
    return True


def test_unary_operations():
    """测试一元运算：负号"""
    print("\n" + "=" * 60)
    print("一元运算测试（负号）")
    print("=" * 60)
    
    # 负号 -5
    source = "定义_结果等于-5。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: -5"
    value = module.statements[0].value
    assert type(value).__name__ == 'UnaryOp', f"期望 UnaryOp: {type(value).__name__}"
    assert value.operator == '-', f"期望 '-': {value.operator}"
    print(f"  [+] 负数: -5 -> UnaryOp(op=-)")
    
    # 双重否定 --5 (= +5)
    source = "定义_结果等于--5。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: --5"
    value = module.statements[0].value
    assert type(value).__name__ == 'UnaryOp'
    # 外层是第一个 -
    inner = value.operand
    assert type(inner).__name__ == 'UnaryOp', f"内层期望 UnaryOp: {type(inner).__name__}"
    assert inner.operator == '-'
    print(f"  [+] 双重否定: --5 -> UnaryOp(-, UnaryOp(-, 5))")
    
    # 负号在表达式中
    source = "定义_结果等于-3加5。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: -3加5"
    value = module.statements[0].value
    assert type(value).__name__ == 'BinaryOp', f"期望 BinaryOp: {type(value).__name__}"
    assert value.operator == '加'
    assert type(value.left).__name__ == 'UnaryOp', f"左值期望 UnaryOp: {type(value.left).__name__}"
    print(f"  [+] 表达式负号: -3加5 -> BinaryOp(加, UnaryOp(-, 3), 5)")
    
    return True


def test_mixed_type_expressions():
    """测试混合类型表达式"""
    print("\n" + "=" * 60)
    print("混合类型表达式测试")
    print("=" * 60)
    
    # 比较+逻辑
    source = "定义_结果等于(10大于5)且(20小于30)。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 比较+逻辑"
    value = module.statements[0].value
    assert type(value).__name__ == 'BinaryOp'
    assert value.operator == '且'
    print(f"  [+] 比较+逻辑: (10>5)且(20<30) -> BinaryOp(且)")
    
    # 嵌套索引
    source = "定义_矩阵等于【【1, 2】, 【3, 4】】。定义_结果等于_矩阵[0][1]。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 嵌套索引"
    # 第一个语句应是 ListLiteral 嵌套
    v0 = module.statements[0].value
    assert type(v0).__name__ == 'ListLiteral', f"期望 ListLiteral: {type(v0).__name__}"
    assert len(v0.elements) == 2
    assert type(v0.elements[0]).__name__ == 'ListLiteral', f"嵌套期望 ListLiteral: {type(v0.elements[0]).__name__}"
    print(f"  [+] 嵌套列表: 【【1, 2】, 【3, 4】】 -> 2x2 矩阵")
    
    # 第二个语句：矩阵[0][1] 
    v1 = module.statements[1].value
    assert type(v1).__name__ == 'IndexAccess', f"外层 IndexAccess: {type(v1).__name__}"
    inner = v1.index
    assert type(inner).__name__ == 'NumberLiteral', f"期望 NumberLiteral: {type(inner).__name__}"  
    print(f"  [+] 链式索引: 矩阵[0][1] -> IndexAccess(IndexAccess(...))")
    
    # 多个混合运算符
    source = "定义_结果等于(3乘(4加5))大于(20减10)且非假。"
    parser = LightParser()
    module = parser.parse(source)
    assert module is not None, "解析失败: 混合运算符链"
    value = module.statements[0].value
    assert value is not None
    print(f"  [+] 混合运算符: (3*(4+5))>(20-10)且非假")
    
    return True


if __name__ == '__main__':
    print("=== 光明数据类型与运算测试 ===\n")
    
    tests = [
        ("算术运算符", test_arithmetic_operators),
        ("比较运算符", test_comparison_operators),
        ("逻辑运算符", test_logical_operators),
        ("括号/优先级", test_parentheses_priority),
        ("字符串", test_string_literals),
        ("字符串运算", test_string_operations),
        ("列表", test_list_literals),
        ("列表运算", test_list_operations),
        ("布尔/空值", test_boolean_null_literals),
        ("一元运算", test_unary_operations),
        ("混合类型", test_mixed_type_expressions),
        ("复杂表达式", test_complex_expressions),
    ]
    
    all_passed = True
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            if fn():
                pass
            print(f"  [+] 通过")
        except Exception as e:
            print(f"  [FAIL] 失败: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("全部数据类型与运算测试通过")
    else:
        print("部分测试失败")
    
    sys.exit(0 if all_passed else 1)