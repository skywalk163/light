"""运行光明自举测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_bootstrap_test():
    """运行完整的光明自举测试"""
    print("=" * 70)
    print("光明自举测试 - 将所有组件合并执行")
    print("=" * 70)
    print()
    
    # 合并所有组件
    print("合并组件代码...")
    combined_code = ''
    
    # 1. tokenizer
    print("  [1/5] tokenizer.light")
    with open(os.path.join(BASE_DIR, 'tokenizer.light'), 'r', encoding='utf-8') as f:
        combined_code += f.read() + '\n\n'
    
    # 2. ast
    print("  [2/5] ast.light")
    with open(os.path.join(BASE_DIR, 'ast.light'), 'r', encoding='utf-8') as f:
        combined_code += f.read() + '\n\n'
    
    # 3. parser
    print("  [3/5] parser.light")
    with open(os.path.join(BASE_DIR, 'parser.light'), 'r', encoding='utf-8') as f:
        combined_code += f.read() + '\n\n'
    
    # 4. interpreter
    print("  [4/5] interpreter.light")
    with open(os.path.join(BASE_DIR, 'interpreter.light'), 'r', encoding='utf-8') as f:
        combined_code += f.read() + '\n\n'
    
    # 5. 简化的测试代码
    print("  [5/5] 测试代码")
    test_code = '''
《执行代码》段(_code):
  _tokens等于《分词器》(_code)。
  _result等于《解析》(_tokens)。
  如果_result["_type"]等于"Error"那么：
    打印("解析失败: "加_result["message"])。
    返回。
  结束。
  《_run》(_result["result"])。
返回。

# 测试1: 简单算术
打印("测试1: 算术运算")。
《执行代码》("定义a等于10加20。定义b等于a乘3。打印(a)。打印(b)。")。
打印()。

# 测试2: 条件语句
打印("测试2: 条件语句")。
《执行代码》("定义x等于100。如果x大于50那么：打印(\"大于50\")。否则：打印(\"不大于50\")。结束。")。
打印()。

# 测试3: 循环
打印("测试3: 当循环")。
《执行代码》("定义i等于0。定义sum等于0。当i小于5：sum等于sum加i。i等于i加1。结束。打印(sum)。")。
打印()。

# 测试4: 段落调用
打印("测试4: 段落调用")。
《执行代码》("《平方》段(n): 返回n乘n。结束。打印(《平方》(5))。")。
打印()。

print("所有测试完成!")。
'''
    combined_code += test_code
    
    print(f"\n总代码长度: {len(combined_code)} 字符")
    print()
    
    # 执行测试
    print("执行合并代码...")
    print("=" * 70)
    
    try:
        interp = run_source(combined_code)
        output = interp.get_output()
        print(output)
        print("=" * 70)
        print("执行完成！")
        return 0
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(run_bootstrap_test())