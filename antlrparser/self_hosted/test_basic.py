"""基础测试：验证光明版解释器和LLVM代码生成器能被正确解析和加载"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_interpreter import run_source
from light_visitor import parse_source


def test_interpreter_load():
    """测试解释器源码能被正确解析和加载"""
    print("=" * 60)
    print("测试：光明版解释器加载")
    print("=" * 60)
    
    interp_code = open("interpreter.light", encoding="utf-8").read()
    
    # 解析验证
    ast = parse_source(interp_code)
    if ast is None:
        print("  ✗ 解析失败")
        return False
    
    print(f"  [+] 解析成功")
    print(f"  [+] 段落定义数: {len(ast.segments)}")
    print(f"  [+] 语句数: {len(ast.statements)}")
    
    # 执行加载
    try:
        interp = run_source(interp_code)
        print(f"  [+] 加载成功")
        
        # 检查关键函数是否存在
        funcs = ['_run', '_eval', '_execStmt', '_newEnv', '_findVar']
        for func_name in funcs:
            if interp.env.get(func_name):
                print(f"  [+] 函数 《{func_name}》已注册")
            else:
                print(f"  [-] 函数 《{func_name}》未找到")
        
        return True
    except Exception as e:
        print(f"  ✗ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llvm_codegen_load():
    """测试LLVM代码生成器能被正确解析和加载"""
    print("=" * 60)
    print("测试：光明版LLVM代码生成器加载")
    print("=" * 60)
    
    llvm_code = open("llvm_codegen.light", encoding="utf-8").read()
    
    # 解析验证
    ast = parse_source(llvm_code)
    if ast is None:
        print("  ✗ 解析失败")
        return False
    
    print(f"  [+] 解析成功")
    print(f"  [+] 段落定义数: {len(ast.segments)}")
    print(f"  [+] 语句数: {len(ast.statements)}")
    
    # 执行加载
    try:
        interp = run_source(llvm_code)
        print(f"  [+] 加载成功")
        
        # 检查关键函数是否存在
        funcs = ['编译', '生成模块', '生成表达式', '生成语句']
        for func_name in funcs:
            if interp.env.get(func_name):
                print(f"  [+] 函数 《{func_name}》已注册")
            else:
                print(f"  [-] 函数 《{func_name}》未找到")
        
        return True
    except Exception as e:
        print(f"  ✗ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tokenizer_load():
    """测试分词器能被正确解析和加载"""
    print("=" * 60)
    print("测试：光明版分词器加载")
    print("=" * 60)
    
    tokenizer_code = open("tokenizer.light", encoding="utf-8").read()
    
    # 解析验证
    ast = parse_source(tokenizer_code)
    if ast is None:
        print("  ✗ 解析失败")
        return False
    
    print(f"  [+] 解析成功")
    print(f"  [+] 段落定义数: {len(ast.segments)}")
    
    # 执行加载
    try:
        interp = run_source(tokenizer_code)
        print(f"  [+] 加载成功")
        
        if interp.env.get('分词器'):
            print(f"  [+] 函数 《分词器》已注册")
        else:
            print(f"  [-] 函数 《分词器》未找到")
        
        return True
    except Exception as e:
        print(f"  ✗ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parser_load():
    """测试解析器能被正确解析和加载"""
    print("=" * 60)
    print("测试：光明版解析器加载")
    print("=" * 60)
    
    # 合并 ast.light 和 parser.light
    combined = ''
    for name in ['ast.light', 'parser.light']:
        with open(name, 'r', encoding='utf-8') as f:
            combined += f.read() + '\n'
    
    # 解析验证
    ast = parse_source(combined)
    if ast is None:
        print("  ✗ 解析失败")
        return False
    
    print(f"  [+] 解析成功")
    print(f"  [+] 段落定义数: {len(ast.segments)}")
    
    # 执行加载
    try:
        interp = run_source(combined)
        print(f"  [+] 加载成功")
        
        funcs = ['解析', '解析表达式', '解析语句', '创建模块']
        for func_name in funcs:
            if interp.env.get(func_name):
                print(f"  [+] 函数 《{func_name}》已注册")
            else:
                print(f"  [-] 函数 《{func_name}》未找到")
        
        return True
    except Exception as e:
        print(f"  ✗ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("开始测试光明自举组件加载...")
    print()
    
    results = []
    
    results.append(("分词器", test_tokenizer_load()))
    print()
    
    results.append(("解析器", test_parser_load()))
    print()
    
    results.append(("解释器", test_interpreter_load()))
    print()
    
    results.append(("LLVM代码生成器", test_llvm_codegen_load()))
    print()
    
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(p for _, p in results)
    print()
    if all_passed:
        print("所有组件加载成功！")
        print()
        print("光明自举系统包含以下组件：")
        print("  - tokenizer.light     : 光明版分词器")
        print("  - ast.light           : AST节点定义")
        print("  - parser.light        : 光明版解析器")
        print("  - interpreter.light   : 光明版解释器")
        print("  - llvm_codegen.light  : 光明版LLVM代码生成器")
        sys.exit(0)
    else:
        print("部分组件加载失败！")
        sys.exit(1)