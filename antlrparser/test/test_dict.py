"""
光明 - 典类型与内置函数测试

测试：
1. _典 函数创建字典
2. 典索引访问和赋值
3. 典属性（长度、键列、值列）
4. 遍历典
5. 类型转换（_串化、_数化）
6. 字符分类（_是中文、_是字母、_是数字）
7. 文件IO（_读文件、_写文件）
8. DictLiteral AST节点（如语法支持后）
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source, LightValue


def run(source: str):
    """解析并执行光明代码，返回执行器"""
    return run_source(source)


def assert_var(interp, name, expected, msg=None):
    """断言变量值"""
    val = interp.env.get(name)
    actual = val.value
    assert actual == expected, f"{msg or f'变量 {name}'}: 期望 {expected!r}, 实际 {actual!r}"


def assert_type(interp, name, expected_type, msg=None):
    """断言变量类型"""
    val = interp.env.get(name)
    assert val.type_name == expected_type, f"{msg or f'变量 {name} 类型'}: 期望 {expected_type}, 实际 {val.type_name}"


def assert_dict_value(interp, name, expected: dict, msg=None):
    """断言典内容"""
    val = interp.env.get(name)
    assert val.type_name == '典', f"{msg or f'变量 {name}'}: 期望类型 典, 实际 {val.type_name}"
    d = val.value
    # 解包 LightValue 值
    actual = {k: v.value if isinstance(v, LightValue) else v for k, v in d.items()}
    assert actual == expected, f"{msg or f'典 {name}'}: 期望 {expected!r}, 实际 {actual!r}"


# =============================================================================
# 测试用例
# =============================================================================

def test_dict_create():
    """测试创建典"""
    print("\n" + "=" * 60)
    print("测试: 创建典")
    print("=" * 60)

    interp = run("""
        定义_映射等于_典("甲", 1, "乙", 2, "丙", 3)。
    """)

    assert_type(interp, '_映射', '典', "类型应为典")
    assert_dict_value(interp, '_映射', {"甲": 1, "乙": 2, "丙": 3}, "典内容")
    print("  [+] 创建典正确")
    return True


def test_dict_access():
    """测试典索引访问和赋值"""
    print("\n" + "=" * 60)
    print("测试: 典索引访问与赋值")
    print("=" * 60)

    interp = run("""
        定义_映射等于_典("甲", 1, "乙", 2)。
        定义_甲值等于_映射["甲"]。
        _映射之丙等于3。
        定义_丙值等于_映射["丙"]。
    """)

    assert_var(interp, '_甲值', 1, "访问['甲']")
    assert_var(interp, '_丙值', 3, "赋值后访问['丙']")
    assert_dict_value(interp, '_映射', {"甲": 1, "乙": 2, "丙": 3}, "典内容")
    print("  [+] 典索引访问与赋值正确")
    return True


def test_dict_properties():
    """测试典属性"""
    print("\n" + "=" * 60)
    print("测试: 典属性")
    print("=" * 60)

    interp = run("""
        定义_映射等于_典("甲", 1, "乙", 2, "丙", 3)。
        定义_长度等于_映射之长度。
        定义_键列等于_映射之键列。
        定义_值列等于_映射之值列。
    """)

    assert_var(interp, '_长度', 3, "典长度应为3")
    keys = interp.env.get('_键列').value
    key_set = set(k.value for k in keys)
    assert key_set == {"甲", "乙", "丙"}, f"键列不正确: {keys}"
    vals = interp.env.get('_值列').value
    assert sorted([v.value for v in vals]) == [1, 2, 3], f"值列不正确: {vals}"
    print("  [+] 典属性正确")
    return True


def test_dict_foreach():
    """测试遍历典"""
    print("\n" + "=" * 60)
    print("测试: 遍历典")
    print("=" * 60)

    interp = run("""
        定义_映射等于_典("甲", 1, "乙", 2, "丙", 3)。
        定义_和等于0。
        遍历_key _映射：
          定义_和等于_和加_映射[_key]。
        结束。
    """)

    assert_var(interp, '_和', 6, "典遍历求和应为6")
    print("  [+] 遍历典正确")
    return True


def test_builtin_to_string():
    """测试_串化转换"""
    print("\n" + "=" * 60)
    print("测试: _串化")
    print("=" * 60)

    interp = run("""
        定义_文本等于_串化(123)。
        定义_文本2等于_串化(真)。
        定义_文本3等于_串化(空)。
    """)

    assert_var(interp, '_文本', "123", "数→串")
    assert_var(interp, '_文本2', "真", "布尔→串")
    assert_var(interp, '_文本3', "空", "空→串")
    assert_type(interp, '_文本', '串', "类型应为串")
    print("  [+] _串化 正确")
    return True


def test_builtin_to_number():
    """测试_数化转换"""
    print("\n" + "=" * 60)
    print("测试: _数化")
    print("=" * 60)

    interp = run("""
        定义_数等于_数化("123")。
        定义_数2等于_数化("3.14")。
        定义_数3等于_数化(真)。
    """)

    assert_var(interp, '_数', 123, "串→数")
    assert_var(interp, '_数2', 3.14, "串→浮数")
    assert_var(interp, '_数3', 1, "真→数")
    print("  [+] _数化 正确")
    return True


def test_builtin_char_classify():
    """测试字符分类函数"""
    print("\n" + "=" * 60)
    print("测试: 字符分类")
    print("=" * 60)

    interp = run("""
        定义_r1等于_是中文("中")。
        定义_r2等于_是字母("a")。
        定义_r3等于_是数字("5")。
        定义_r4等于_是字母("_")。
        定义_r5等于_是中文("ab")。
    """)

    assert_var(interp, '_r1', True, "是中文")
    assert_var(interp, '_r2', True, "是字母")
    assert_var(interp, '_r3', True, "是数字")
    assert_var(interp, '_r4', True, "下划线是字母")
    assert_var(interp, '_r5', False, "多字符不是中文")
    print("  [+] 字符分类正确")
    return True


def test_builtin_file_io():
    """测试文件读写"""
    print("\n" + "=" * 60)
    print("测试: 文件读写")
    print("=" * 60)

    # 使用临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("光明测试内容")
        tmp_path = f.name.replace('\\', '/')

    try:
        interp = run(f"""
            _写文件("{tmp_path}", "新写入内容")。
            定义_内容等于_读文件("{tmp_path}")。
        """)

        assert_var(interp, '_内容', "新写入内容", "文件读写")
        # 验证文件确实被写入
        with open(tmp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "新写入内容", f"文件内容不正确: {content}"

        print("  [+] 文件读写正确")
        return True
    finally:
        os.unlink(tmp_path)


def test_empty_dict():
    """测试空典"""
    print("\n" + "=" * 60)
    print("测试: 空典")
    print("=" * 60)

    interp = run("""
        定义_空典等于_典()。
        定义_长度等于_空典之长度。
    """)

    assert_var(interp, '_长度', 0, "空典长度应为0")
    d = interp.env.get('_空典').value
    assert d == {}, f"空典应为空字典: {d}"
    assert_type(interp, '_空典', '典', "类型应为典")
    print("  [+] 空典正确")
    return True


def test_dict_number_key():
    """测试数字键典"""
    print("\n" + "=" * 60)
    print("测试: 数字键典")
    print("=" * 60)

    interp = run("""
        定义_映射等于_典(1, "一", 2, "二", 3, "三")。
        定义_v1等于_映射[1]。
        定义_v3等于_映射[3]。
    """)

    assert_var(interp, '_v1', "一", "索引数字键1")
    assert_var(interp, '_v3', "三", "索引数字键3")
    print("  [+] 数字键典正确")
    return True


def test_dict_truthy():
    """测试典的真值"""
    print("\n" + "=" * 60)
    print("测试: 典真值")
    print("=" * 60)

    interp = run("""
        定义_空典等于_典()。
        定义_满典等于_典("a", 1)。
        定义_r1等于_空典且真。
        定义_r2等于_满典且真。
    """)

    # 空典为假，满典为真
    assert_var(interp, '_r1', False, "空典应为假")
    assert_var(interp, '_r2', True, "满典应为真")
    print("  [+] 典真值正确")
    return True


# =============================================================================
# 主入口
# =============================================================================

if __name__ == '__main__':
    tests = [
        ("创建典", test_dict_create),
        ("典索引访问与赋值", test_dict_access),
        ("典属性", test_dict_properties),
        ("遍历典", test_dict_foreach),
        ("空典", test_empty_dict),
        ("数字键典", test_dict_number_key),
        ("典真值", test_dict_truthy),
        ("_串化", test_builtin_to_string),
        ("_数化", test_builtin_to_number),
        ("字符分类", test_builtin_char_classify),
        ("文件读写", test_builtin_file_io),
    ]

    passed = 0
    failed = 0

    for name, func in tests:
        try:
            func()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n总计: {passed} 通过, {failed} 失败")