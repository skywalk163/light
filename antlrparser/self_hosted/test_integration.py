"""完整集成测试：验证光明版解释器执行光明代码"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source, LightValue, LightFunction


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def unwrap_value(v):
    """递归解包 LightValue"""
    if isinstance(v, LightValue):
        return unwrap_value(v.value)
    if isinstance(v, dict):
        return {k: unwrap_value(v) for k, v in v.items()}
    if isinstance(v, list):
        return [unwrap_value(x) for x in v]
    return v


def load_all_components():
    """加载所有自举组件"""
    print("加载自举组件...")
    
    # 1. 加载分词器
    print("  [1/4] 加载分词器...")
    with open(os.path.join(BASE_DIR, 'tokenizer.light'), 'r', encoding='utf-8') as f:
        tokenizer_code = f.read()
    tok_interp = run_source(tokenizer_code)
    tok_func = tok_interp.env.get('分词器').value
    
    # 2. 加载解析器 (ast + parser)
    print("  [2/4] 加载解析器...")
    parser_code = ''
    for name in ['ast.light', 'parser.light']:
        with open(os.path.join(BASE_DIR, name), 'r', encoding='utf-8') as f:
            parser_code += f.read() + '\n'
    parse_interp = run_source(parser_code)
    parse_func = parse_interp.env.get('解析').value
    
    # 3. 加载解释器
    print("  [3/4] 加载解释器...")
    with open(os.path.join(BASE_DIR, 'interpreter.light'), 'r', encoding='utf-8') as f:
        interp_code = f.read()
    interp = run_source(interp_code)
    run_func = interp.env.get('_run').value
    
    # 4. 加载LLVM代码生成器
    print("  [4/4] 加载LLVM代码生成器...")
    with open(os.path.join(BASE_DIR, 'llvm_codegen.light'), 'r', encoding='utf-8') as f:
        llvm_code = f.read()
    llvm_interp = run_source(llvm_code)
    compile_func = llvm_interp.env.get('编译').value
    
    print("  所有组件加载完成！")
    return tok_interp, tok_func, parse_interp, parse_func, interp, run_func, llvm_interp, compile_func


def get_tokens(code, tok_interp, tok_func):
    """用光明版分词器获取Token"""
    result = tok_interp._call_function(tok_func, [LightValue(code, '串')])
    raw_tokens = unwrap_value(result)
    wrapped = []
    for t in raw_tokens:
        wrapped.append(LightValue({
            'type': LightValue(t['type'], '串'),
            'text': LightValue(t['text'], '串'),
            'line': LightValue(t['line'], '数'),
            'col': LightValue(t['col'], '数'),
        }, '典'))
    return LightValue(wrapped, '列')


def parse_code(tokens, parse_interp, parse_func):
    """用光明版解析器解析Token"""
    result = parse_interp._call_function(parse_func, [tokens])
    parsed = unwrap_value(result)
    if parsed.get('_type') == 'Error':
        return None, parsed.get('message')
    return parsed.get('result'), None


def execute_code(ast_dict, interp, run_func):
    """用光明版解释器执行AST"""
    ast_value = LightValue(ast_dict, '典')
    interp._call_function(run_func, [ast_value])
    output = interp.get_output()
    interp.clear_output()
    return output


def test_arithmetic():
    """测试基本算术运算"""
    print("=" * 60)
    print("测试：基本算术运算")
    print("=" * 60)
    
    code = """
定义a等于10加20。
定义b等于a乘3。
定义c等于b减10。
定义d等于c除5。
打印("a = "加a)。
打印("b = "加b)。
打印("c = "加c)。
打印("d = "加d)。
"""
    
    return {
        'code': code.strip(),
        'expected': ['a = 30', 'b = 90', 'c = 80', 'd = 16'],
        'name': '算术运算'
    }


def test_condition():
    """测试条件语句"""
    print("=" * 60)
    print("测试：条件语句")
    print("=" * 60)
    
    code = """
定义x等于100。
如果x大于50那么：
  打印("x大于50")。
否则：
  打印("x不大于50")。
结束。

定义y等于20。
如果y大于50那么：
  打印("y大于50")。
否则：
  打印("y不大于50")。
结束。
"""
    
    return {
        'code': code.strip(),
        'expected': ['x大于50', 'y不大于50'],
        'name': '条件语句'
    }


def test_while_loop():
    """测试当循环"""
    print("=" * 60)
    print("测试：当循环")
    print("=" * 60)
    
    code = """
定义i等于0。
定义sum等于0。
当i小于5：
  sum等于sum加i。
  i等于i加1。
结束。
打印("sum = "加sum)。
"""
    
    return {
        'code': code.strip(),
        'expected': ['sum = 10'],
        'name': '当循环'
    }


def test_for_loop():
    """测试遍历循环"""
    print("=" * 60)
    print("测试：遍历循环")
    print("=" * 60)
    
    code = """
定义arr等于【10, 20, 30, 40】。
定义total等于0。
遍历x arr：
  total等于total加x。
结束。
打印("total = "加total)。
"""
    
    return {
        'code': code.strip(),
        'expected': ['total = 100'],
        'name': '遍历循环'
    }


def test_segment():
    """测试段落定义和调用"""
    print("=" * 60)
    print("测试：段落定义和调用")
    print("=" * 60)
    
    code = """
《平方》段(n):
  返回n乘n。
结束。

《阶乘》段(n):
  如果n小于等于1那么：
    返回1。
  结束。
  返回n乘《阶乘》(n减1)。
结束。

打印("平方(5) = "加《平方》(5))。
打印("阶乘(5) = "加《阶乘》(5))。
"""
    
    return {
        'code': code.strip(),
        'expected': ['平方(5) = 25', '阶乘(5) = 120'],
        'name': '段落定义和调用'
    }


def test_list_and_dict():
    """测试列表和典操作"""
    print("=" * 60)
    print("测试：列表和典操作")
    print("=" * 60)
    
    code = """
定义list1等于【1, 2, 3, 4, 5】。
打印("列表长度: "加list1之长度)。
打印("第一个元素: "加list1[0])。
打印("最后一个元素: "加list1[4])。

定义map1等于_典("姓名", "张三", "年龄", 18)。
打印("姓名: "加map1["姓名"])。
打印("年龄: "加map1["年龄"])。
"""
    
    return {
        'code': code.strip(),
        'expected': ['列表长度: 5', '第一个元素: 1', '最后一个元素: 5', '姓名: 张三', '年龄: 18'],
        'name': '列表和典操作'
    }


def test_string_operations():
    """测试字符串操作"""
    print("=" * 60)
    print("测试：字符串操作")
    print("=" * 60)
    
    code = """
定义s1等于"Hello"。
定义s2等于"World"。
定义s3等于s1加" "加s2。
打印("拼接: "加s3)。
打印("长度: "加s3之长度)。
"""
    
    return {
        'code': code.strip(),
        'expected': ['拼接: Hello World', '长度: 11'],
        'name': '字符串操作'
    }


def test_comprehensive():
    """综合测试"""
    print("=" * 60)
    print("测试：综合示例")
    print("=" * 60)
    
    code = """
《斐波那契》段(n):
  如果n等于0那么：返回0。结束。
  如果n等于1那么：返回1。结束。
  返回《斐波那契》(n减1)加《斐波那契》(n减2)。
结束。

打印("斐波那契数列前10项:")。
定义i等于0。
当i小于10：
  打印("F("加i加") = "加《斐波那契》(i))。
  i等于i加1。
结束。
"""
    
    return {
        'code': code.strip(),
        'expected': [
            '斐波那契数列前10项:',
            'F(0) = 0', 'F(1) = 1', 'F(2) = 1', 'F(3) = 2', 'F(4) = 3',
            'F(5) = 5', 'F(6) = 8', 'F(7) = 13', 'F(8) = 21', 'F(9) = 34'
        ],
        'name': '综合示例'
    }


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("光明自举解释器 - 完整集成测试")
    print("=" * 70)
    print()
    
    # 加载组件
    tok_interp, tok_func, parse_interp, parse_func, interp, run_func, llvm_interp, compile_func = load_all_components()
    print()
    
    # 测试用例
    tests = [
        test_arithmetic(),
        test_condition(),
        test_while_loop(),
        test_for_loop(),
        test_segment(),
        test_list_and_dict(),
        test_string_operations(),
        test_comprehensive()
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"测试: {test['name']}")
        print(f"代码:\n{test['code']}\n")
        
        try:
            # 分词
            tokens = get_tokens(test['code'], tok_interp, tok_func)
            print(f"  [+] 分词完成: {len(unwrap_value(tokens))} 个Token")
            
            # 解析
            ast, err = parse_code(tokens, parse_interp, parse_func)
            if err:
                print(f"  [-] 解析失败: {err}")
                failed += 1
                print()
                continue
            print(f"  [+] 解析成功")
            
            # 执行
            output = execute_code(ast, interp, run_func)
            output_lines = [line.strip() for line in output.strip().split('\n') if line.strip()]
            
            # 验证结果
            success = True
            for expected in test['expected']:
                if expected not in output:
                    print(f"  [-] 期望输出 '{expected}' 未找到")
                    success = False
            
            if success:
                print(f"  [+] 所有期望输出均已找到")
                print(f"  [+] 实际输出:")
                for line in output_lines:
                    print(f"      {line}")
                passed += 1
            else:
                print(f"  [-] 输出不匹配")
                print(f"  [-] 实际输出:")
                for line in output_lines:
                    print(f"      {line}")
                failed += 1
                
        except Exception as e:
            print(f"  [-] 测试异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        
        print()
    
    # 汇总
    print("=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    print(f"  通过: {passed}/{len(tests)}")
    print(f"  失败: {failed}/{len(tests)}")
    print()
    
    if failed == 0:
        print("🎉 所有测试通过！光明自举解释器工作正常！")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())