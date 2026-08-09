"""测试Python版解释器执行光明代码"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source


def test_simple_code():
    """测试简单的光明代码"""
    print("=" * 60)
    print("测试：Python版解释器执行光明代码")
    print("=" * 60)
    
    # 测试代码列表
    tests = [
        {
            'name': '算术运算',
            'code': '定义a等于10加20。定义b等于a乘3。打印(a)。打印(b)。',
            'expected': ['30', '90']
        },
        {
            'name': '条件语句',
            'code': '定义x等于100。如果x大于50那么：打印("大于50")。否则：打印("不大于50")。结束。',
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
        },
        {
            'name': '列表操作',
            'code': '定义arr等于【1,2,3,4,5】。打印(arr之长度)。打印(arr[0])。',
            'expected': ['5', '1']
        },
        {
            'name': '字符串操作',
            'code': '定义s等于"Hello"加" "加"World"。打印(s)。打印(s之长度)。',
            'expected': ['Hello World', '11']
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n测试: {test['name']}")
        print(f"代码: {test['code']}")
        
        try:
            interp = run_source(test['code'])
            output = interp.get_output().strip()
            
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
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"结果: {passed}/{len(tests)} 通过")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(test_simple_code())