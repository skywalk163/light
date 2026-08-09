"""
光明 - 解释执行测试

验证解释器能正确执行光明程序并产生预期结果
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import (
    Interpreter, LightValue, LightFunction, Environment,
    ReturnSignal, BreakSignal, ContinueSignal, LightError,
    run_source, run_file
)


# =============================================================================
# 辅助函数
# =============================================================================

def run(source: str) -> Interpreter:
    """解析并执行光明代码，返回解释器实例"""
    return run_source(source)


def get_var(interp: Interpreter, name: str) -> LightValue:
    """获取变量值"""
    return interp.env.get(name)


def assert_var(interp: Interpreter, name: str, expected):
    """断言变量值等于预期值"""
    actual = get_var(interp, name)
    assert actual.value == expected, (
        f"变量 '{name}' 期望 {repr(expected)}, 实际 {repr(actual.value)}"
    )


# =============================================================================
# 测试用例
# =============================================================================

def test_arithmetic():
    """测试算术运算"""
    print("=" * 60)
    print("算术运算执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_a等于10加5。
        定义_b等于10减5。
        定义_c等于10乘5。
        定义_d等于10除5。
        定义_e等于10模3。
        定义_f等于2幂3。
    """)
    
    assert_var(interp, '_a', 15)
    assert_var(interp, '_b', 5)
    assert_var(interp, '_c', 50)
    assert_var(interp, '_d', 2.0)
    assert_var(interp, '_e', 1)
    assert_var(interp, '_f', 8)
    print("  [+] 算术运算全部正确")
    return True


def test_comparison():
    """测试比较运算"""
    print("\n" + "=" * 60)
    print("比较运算执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_a等于10大于5。
        定义_b等于10小于5。
        定义_c等于10等于10。
        定义_d等于10不等于5。
        定义_e等于10大于等于5。
        定义_f等于10小于等于10。
        定义_g等于10大于10。
    """)
    
    assert_var(interp, '_a', True)
    assert_var(interp, '_b', False)
    assert_var(interp, '_c', True)
    assert_var(interp, '_d', True)
    assert_var(interp, '_e', True)
    assert_var(interp, '_f', True)
    assert_var(interp, '_g', False)
    print("  [+] 比较运算全部正确")
    return True


def test_logical():
    """测试逻辑运算"""
    print("\n" + "=" * 60)
    print("逻辑运算执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_a等于真且真。
        定义_b等于真且假。
        定义_c等于真或假。
        定义_d等于假或假。
        定义_e等于非真。
        定义_f等于非假。
    """)
    
    assert_var(interp, '_a', True)
    assert_var(interp, '_b', False)
    assert_var(interp, '_c', True)
    assert_var(interp, '_d', False)
    assert_var(interp, '_e', False)
    assert_var(interp, '_f', True)
    print("  [+] 逻辑运算全部正确")
    return True


def test_negative():
    """测试负数"""
    print("\n" + "=" * 60)
    print("负数执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_a等于-5。
        定义_b等于-3加5。
        定义_c等于-3减-2。
    """)
    
    assert_var(interp, '_a', -5)
    assert_var(interp, '_b', 2)  # -3 + 5 = 2
    assert_var(interp, '_c', -1)  # -3 - (-2) = -1
    print("  [+] 负数运算全部正确")
    return True


def test_string():
    """测试字符串操作"""
    print("\n" + "=" * 60)
    print("字符串执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_a等于"hello"加"world"。
        定义_b等于"你好"加"，世界"。
        定义_c等于"值："加123。
    """)
    
    var_a = get_var(interp, '_a')
    assert var_a.type_name == '串', f"期望 '串', 实际 '{var_a.type_name}'"
    assert var_a.value == 'helloworld', f"期望 'helloworld', 实际 '{var_a.value}'"
    
    var_b = get_var(interp, '_b')
    assert var_b.value == '你好，世界', f"期望 '你好，世界', 实际 '{var_b.value}'"
    
    var_c = get_var(interp, '_c')
    assert var_c.value == '值：123', f"期望 '值：123', 实际 '{var_c.value}'"
    
    print("  [+] 字符串操作全部正确")
    return True


def test_list():
    """测试列表操作"""
    print("\n" + "=" * 60)
    print("列表执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_数列等于【1, 2, 3, 4, 5】。
        定义_a等于_数列[0]。
        定义_b等于_数列[4]。
        定义_c等于_数列之长度。
    """)
    
    assert_var(interp, '_a', 1)
    assert_var(interp, '_b', 5)
    assert_var(interp, '_c', 5)
    
    # 列表类型验证
    lst = get_var(interp, '_数列')
    assert lst.type_name == '列', f"期望 '列', 实际 '{lst.type_name}'"
    assert len(lst.value) == 5, f"期望长度 5, 实际 {len(lst.value)}"
    
    print("  [+] 列表操作全部正确")
    return True


def test_nested_list():
    """测试嵌套列表"""
    print("\n" + "=" * 60)
    print("嵌套列表执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_矩阵等于【【1, 2】, 【3, 4】】。
        定义_a等于_矩阵[0][0]。
        定义_b等于_矩阵[1][1]。
        定义_r等于_矩阵之长度。
    """)
    
    assert_var(interp, '_a', 1)
    assert_var(interp, '_b', 4)
    assert_var(interp, '_r', 2)
    
    print("  [+] 嵌套列表全部正确")
    return True


def test_boolean_and_null():
    """测试布尔值和空值"""
    print("\n" + "=" * 60)
    print("布尔/空值执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_a等于真。
        定义_b等于假。
        定义_c等于空。
    """)
    
    assert_var(interp, '_a', True)
    assert_var(interp, '_b', False)
    
    var_c = get_var(interp, '_c')
    assert var_c.value is None, f"期望 None, 实际 {var_c.value}"
    assert var_c.type_name == '空', f"期望 '空', 实际 '{var_c.type_name}'"
    
    print("  [+] 布尔/空值全部正确")
    return True


def test_assignment():
    """测试变量赋值和修改"""
    print("\n" + "=" * 60)
    print("赋值执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_x等于10。
        _x等于20。
        定义_y等于_x加5。
    """)
    
    assert_var(interp, '_x', 20)
    assert_var(interp, '_y', 25)
    
    print("  [+] 赋值操作全部正确")
    return True


def test_complex_expression():
    """测试复杂表达式"""
    print("\n" + "=" * 60)
    print("复杂表达式执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_a等于(10加5)乘(20减15)除2。  # (15 * 5) / 2 = 37.5
        定义_b等于(10大于5)且(20小于30)。  # True and True = True
        定义_c等于(3加(4乘5))减2。          # (3 + 20) - 2 = 21
    """)
    
    assert_var(interp, '_a', 37.5)
    assert_var(interp, '_b', True)
    assert_var(interp, '_c', 21)
    
    print("  [+] 复杂表达式全部正确")
    return True


def test_if_statement():
    """测试条件语句"""
    print("\n" + "=" * 60)
    print("条件语句执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_分数等于85。
        定义_等级等于"未知"。
        如果_分数大于等于90那么：
          定义_等级等于"A"。
        否则若_分数大于等于80那么：
          定义_等级等于"B"。
        否则若_分数大于等于60那么：
          定义_等级等于"C"。
        否则：
          定义_等级等于"D"。
        结束。
    """)
    
    assert_var(interp, '_等级', 'B')
    print("  [+] if/elif/else 正确 (85 -> B)")
    
    # 测试无 else
    interp2 = run("""
        定义_甲等于真。
        定义_结果等于空。
        如果_甲那么：
          定义_结果等于"成立"。
        结束。
    """)
    assert_var(interp2, '_结果', '成立')
    print("  [+] if 无 else 正确")
    
    # 测试 else
    interp3 = run("""
        定义_甲等于假。
        定义_结果等于空。
        如果_甲那么：
          定义_结果等于"成立"。
        否则：
          定义_结果等于"不成立"。
        结束。
    """)
    assert_var(interp3, '_结果', '不成立')
    print("  [+] if/else 正确")
    
    return True


def test_while_loop():
    """测试当循环"""
    print("\n" + "=" * 60)
    print("当循环执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_计数等于3。
        定义_和等于0。
        当_计数大于0：
          定义_和等于_和加_计数。
          定义_计数等于_计数减1。
        结束。
    """)
    
    assert_var(interp, '_和', 6)  # 3 + 2 + 1 = 6
    assert_var(interp, '_计数', 0)
    print("  [+] 当循环 3+2+1=6 正确")
    
    return True


def test_foreach_loop():
    """测试遍历循环"""
    print("\n" + "=" * 60)
    print("遍历循环执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_列表等于【1, 2, 3, 4, 5】。
        定义_和等于0。
        遍历 项 _列表：
          定义_和等于_和加项。
        结束。
    """)
    
    assert_var(interp, '_和', 15)  # 1+2+3+4+5 = 15
    print("  [+] 遍历循环 1+2+3+4+5=15 正确")
    
    return True


def test_break_continue():
    """测试跳出和跳过"""
    print("\n" + "=" * 60)
    print("跳出/跳过执行测试")
    print("=" * 60)
    
    interp = run("""
        定义_和等于0。
        定义_索引等于1。
        当_索引小于10：
          如果_索引等于5那么：
            定义_索引等于_索引加1。
            跳过。
          结束。
          如果_索引等于8那么：
            跳出。
          结束。
          定义_和等于_和加_索引。
          定义_索引等于_索引加1。
        结束。
    """)
    
    # 1+2+3+4 + 6+7 = 23 (跳过5，8时跳出)
    assert_var(interp, '_和', 23)
    print("  [+] 跳出/跳过 (1+2+3+4+6+7=23) 正确")
    
    return True


def test_print_output():
    """测试打印输出"""
    print("\n" + "=" * 60)
    print("打印输出测试")
    print("=" * 60)
    
    interp = run("""
        打印"你好世界"。
        输出100。
    """)
    
    output = interp.get_output()
    lines = output.split('\n')
    assert len(lines) == 2, f"期望 2 行输出, 实际 {len(lines)}"
    assert lines[0] == '你好世界', f"第一行期望 '你好世界', 实际 '{lines[0]}'"
    assert lines[1] == '100', f"第二行期望 '100', 实际 '{lines[1]}'"
    print("  [+] 打印输出正确")
    
    return True


def test_segment_definition_and_call():
    """测试段落定义和调用"""
    print("\n" + "=" * 60)
    print("段落定义与调用测试")
    print("=" * 60)
    
    # 使用英文段名避免中文关键字冲突
    interp = run("""
        《add》段(_甲, _乙):
          返回_甲加_乙。
        结束。
        
        定义_结果等于《add》(3, 4)。
    """)
    
    assert_var(interp, '_结果', 7)
    print("  [+] 段落定义与调用正确 (add: 3+4=7)")
    
    # 测试无参数段落
    interp2 = run("""
        《val》段():
          返回42。
        结束。
        
        定义_结果等于《val》()。
    """)
    assert_var(interp2, '_结果', 42)
    print("  [+] 无参段落正确")
    
    # 测试段落嵌套调用
    interp3 = run("""
        《sq》段(_n):
          返回_n乘_n。
        结束。
        
        《sum_sq》段(_甲, _乙):
          定义_a等于《sq》(_甲)。
          定义_b等于《sq》(_乙)。
          返回_a加_b。
        结束。
        
        定义_结果等于《sum_sq》(3, 4)。
    """)
    assert_var(interp3, '_结果', 25)  # 3^2 + 4^2 = 25
    print("  [+] 段落嵌套调用正确 (3^2+4^2=25)")
    
    return True


def test_segment_return():
    """测试段落返回值"""
    print("\n" + "=" * 60)
    print("段落返回值测试")
    print("=" * 60)
    
    interp = run("""
        《fact》段(_n):
          如果_n小于等于1那么：
            返回1。
          结束。
          返回_n乘《fact》(_n减1)。
        结束。
        
        定义_结果等于《fact》(5)。
    """)
    
    assert_var(interp, '_结果', 120)  # 5! = 120
    print("  [+] 递归段落正确 (5! = 120)")
    
    return True


def test_mixed_program():
    """测试完整混合程序"""
    print("\n" + "=" * 60)
    print("完整混合程序测试")
    print("=" * 60)
    
    # 计算 1 到 10 之间所有偶数的平方和
    interp = run("""
        定义_和等于0。
        定义_索引等于1。
        当_索引小于等于10：
          定义_余数等于_索引模2。
          如果_余数等于0那么：
            定义_平方等于_索引乘_索引。
            定义_和等于_和加_平方。
          结束。
          定义_索引等于_索引加1。
        结束。
    """)
    
    # 2^2 + 4^2 + 6^2 + 8^2 + 10^2 = 4 + 16 + 36 + 64 + 100 = 220
    assert_var(interp, '_和', 220)
    print("  [+] 混合程序: 1~10 偶数平方和 = 220 正确")
    
    return True


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("错误处理测试")
    print("=" * 60)
    
    interp = run("""
        尝试：
          抛出"出错了"。
        捕获 _err：
          定义_信息等于_err。
        结束。
    """)
    
    info = get_var(interp, '_信息')
    assert info.value is not None, f"期望错误信息, 实际 {info}"
    print(f"  [+] 捕获异常正确: {info}")
    
    return True


# =============================================================================
# 主入口
# =============================================================================

if __name__ == '__main__':
    print("=== 光明解释执行测试 ===\n")
    
    tests = [
        ("算术运算", test_arithmetic),
        ("比较运算", test_comparison),
        ("逻辑运算", test_logical),
        ("负数", test_negative),
        ("字符串", test_string),
        ("列表", test_list),
        ("嵌套列表", test_nested_list),
        ("布尔/空值", test_boolean_and_null),
        ("赋值", test_assignment),
        ("复杂表达式", test_complex_expression),
        ("条件语句", test_if_statement),
        ("当循环", test_while_loop),
        ("遍历循环", test_foreach_loop),
        ("跳出/跳过", test_break_continue),
        ("打印输出", test_print_output),
        ("段落定义/调用", test_segment_definition_and_call),
        ("段落返回值", test_segment_return),
        ("混合程序", test_mixed_program),
        ("错误处理", test_error_handling),
    ]
    
    all_passed = True
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            fn()
            print(f"  [+] 通过")
        except Exception as e:
            print(f"  [FAIL] 失败: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("全部解释执行测试通过")
    else:
        print("部分测试失败")
    
    sys.exit(0 if all_passed else 1)