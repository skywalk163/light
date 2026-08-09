"""测试光明版解释器执行光明代码"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source, LightValue


def test_light_interpreter():
    """测试光明版解释器"""
    print("=" * 70)
    print("测试：光明版解释器执行光明代码")
    print("=" * 70)
    print()
    
    # 加载所有组件
    print("加载光明自举组件...")
    
    # 1. 加载分词器
    print("  [1/4] tokenizer.light")
    with open(os.path.join(os.path.dirname(__file__), 'tokenizer.light'), 'r', encoding='utf-8') as f:
        tokenizer_code = f.read()
    
    # 2. 加载AST和解析器
    print("  [2/4] ast.light + parser.light")
    parser_code = ''
    for f in ['ast.light', 'parser.light']:
        with open(os.path.join(os.path.dirname(__file__), f), 'r', encoding='utf-8') as fp:
            parser_code += fp.read() + '\n\n'
    
    # 3. 加载解释器
    print("  [3/4] interpreter.light")
    with open(os.path.join(os.path.dirname(__file__), 'interpreter.light'), 'r', encoding='utf-8') as f:
        interpreter_code = f.read()
    
    # 合并代码
    all_code = tokenizer_code + '\n\n' + parser_code + '\n\n' + interpreter_code
    
    # 加载到Python解释器中
    print("  [4/4] 加载到Python解释器")
    interp = run_source(all_code)
    
    print()
    print("组件加载完成！")
    print()
    
    # 测试用例
    tests = [
        {
            'name': '算术运算',
            'code': '定义a等于10加20。定义b等于a乘3。打印(a)。打印(b)。',
            'expected': ['30', '90']
        },
        {
            'name': '条件语句',
            'code': '定义x等于100。如果x大于50那么：打印(大于50)。否则：打印(不大于50)。结束。',
            'expected': ['大于50']
        },
        {
            'name': '当循环',
            'code': '定义i等于0。定义sum等于0。当i小于5：sum等于sum加i。i等于i加1。结束。打印(sum)。',
            'expected': ['10']
        },
        {
            'name': '段落调用',
            'code': '《square》段(n): 返回n乘n。结束。打印(《square》(5))。',
            'expected': ['25']
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"测试: {test['name']}")
        print(f"代码: {test['code']}")
        
        try:
            # 使用光明版分词器分词
            tokenizer_func = interp.env.get('分词器').value
            tokens = interp._call_function(tokenizer_func, [LightValue(test['code'], '串')])
            
            # 使用光明版解析器解析
            parser_func = interp.env.get('解析').value
            parsed = interp._call_function(parser_func, [tokens])
            
            parsed_dict = parsed.value if hasattr(parsed, 'value') else {}
            
            if parsed_dict.get('_type') == 'Error':
                print(f"  [-] 解析失败: {parsed_dict.get('message')}")
                failed += 1
                continue
            
            # 使用光明版解释器执行
            run_func = interp.env.get('_run').value
            result = interp._call_function(run_func, [LightValue(parsed_dict.get('result'), '典')])
            
            # 获取输出
            output = interp.get_output().strip()
            interp.clear_output()
            
            # 验证结果
            success = True
            for expected in test['expected']:
                if expected not in output:
                    print(f"  [-] 期望 '{expected}' 未找到")
                    success = False
            
            if success:
                print(f"  [+] 通过")
                print(f"  输出: {output}")
                passed += 1
            else:
                print(f"  [-] 失败")
                print(f"  实际输出: {output}")
                failed += 1
                
        except Exception as e:
            print(f"  [-] 异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        
        print()
    
    print("=" * 70)
    print(f"结果: {passed}/{len(tests)} 通过")
    print("=" * 70)
    
    if failed == 0:
        print("\n🎉 光明版解释器测试全部通过！")
        return 0
    else:
        print("\n⚠️ 部分测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(test_light_interpreter())