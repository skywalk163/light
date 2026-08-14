"""测试 LLVM 后端异步支持"""
import sys
import os
import tempfile
import subprocess
sys.path.insert(0, 'src')

from llvm.compiler import compile_source_typed, find_clang

def run_test(name, code):
    """运行一个测试"""
    print("=" * 60)
    print(f"测试: {name}")
    print("=" * 60)
    
    try:
        # 生成 IR
        ir = compile_source_typed(code, verbose=False)
        
        # 保存 IR
        ir_path = f'tests/_test_{name}.ll'
        with open(ir_path, 'w', encoding='utf-8') as f:
            f.write(ir)
        
        # 编译为可执行文件
        clang = find_clang()
        runtime_c = 'src/llvm/runtime_typed.c'
        exe_path = f'tests/_test_{name}.exe'
        
        result = subprocess.run(
            [clang, '-O2', '-o', exe_path, ir_path, runtime_c],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        
        if result.returncode != 0:
            print(f"编译失败!")
            print("stderr:", result.stderr[:3000])
            return False
        
        print(f"编译成功")
        
        # 运行
        run_result = subprocess.run(
            [exe_path],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=10
        )
        print(f"输出:\n{run_result.stdout}")
        if run_result.stderr:
            print(f"错误输出: {run_result.stderr}")
        print(f"返回码: {run_result.returncode}")
        
        return True
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"错误: {e}")
        return False

def test_async_simple():
    """测试简单的异步段落（仅创建，不执行）"""
    code = """
异步 段落 测试异步：
    输出("异步函数开始")
结束

输出("主程序开始")
x = 测试异步()
输出("主程序结束")
"""
    return run_test("async_simple", code)

def test_async_scope():
    """测试异步作用域（结构化并发）"""
    code = """
异步 段落 任务1：
    输出("任务1开始")
    返回(42)
结束

异步 段落 任务2：
    输出("任务2开始")
    返回("hello")
结束

输出("程序开始")

异步作用域：
    任务1()
    任务2()
结束

输出("程序结束")
"""
    return run_test("async_scope", code)

def test_async_await():
    """测试在异步作用域中使用 await"""
    code = """
异步 段落 任务1：
    输出("任务1开始")
    返回(42)
结束

异步 段落 主任务：
    输出("主任务开始")
    x = 等待 任务1()
    输出("等待结果:")
    输出(x)
    返回(x)
结束

输出("程序开始")

异步作用域：
    主任务()
结束

输出("程序结束")
"""
    return run_test("async_await", code)

def test_async_chain():
    """测试链式 await：一个协程 await 另一个协程"""
    code = """
异步 段落 计算：
    输出("计算开始")
    返回(100)
结束

异步 段落 累加器：
    输出("累加器开始")
    a = 等待 计算()
    输出("累加器得到:")
    输出(a)
    返回(a)
结束

输出("程序开始")

异步作用域：
    累加器()
结束

输出("程序结束")
"""
    return run_test("async_chain", code)

def test_async_multiple_await():
    """测试一个协程中多次 await"""
    code = """
异步 段落 任务甲：
    输出("任务甲")
    返回(10)
结束

异步 段落 任务乙：
    输出("任务乙")
    返回(20)
结束

异步 段落 主任务：
    输出("主任务开始")
    a = 等待 任务甲()
    b = 等待 任务乙()
    输出("结果:")
    输出(a)
    输出(b)
    返回(a)
结束

输出("程序开始")

异步作用域：
    主任务()
结束

输出("程序结束")
"""
    return run_test("async_multiple_await", code)


def test_async_with_params():
    """测试带参数的异步函数"""
    code = """
异步 段落 加法(甲, 乙)：
    输出("加法:")
    输出(甲)
    输出(乙)
    返回(甲 加上 乙)
结束

输出("程序开始")
异步作用域：
    加法(3, 4)
结束
输出("程序结束")
"""
    return run_test("async_params", code)


def test_async_with_condition():
    """测试异步函数中的条件分支"""
    code = """
异步 段落 判断(值)：
    如果 值 大于 0：
        输出("正数")
    否则：
        输出("非正数")
    结束
    返回(值)
结束

输出("程序开始")
异步作用域：
    判断(5)
    判断(-3)
结束
输出("程序结束")
"""
    return run_test("async_condition", code)


def test_async_scope_results():
    """测试异步作用域收集结果"""
    code = """
异步 段落 取数(值)：
    返回(值 乘以 2)
结束

输出("程序开始")
异步作用域 设为 甲, 乙：
    取数(10)
    取数(20)
结束
输出("甲:")
输出(甲)
输出("乙:")
输出(乙)
输出("程序结束")
"""
    return run_test("async_scope_results", code)


def test_async_with_string():
    """测试异步函数中的字符串操作"""
    code = """
异步 段落 问候(名)：
    输出("你好")
    输出(名)
    返回(名)
结束

输出("程序开始")
异步作用域：
    问候("世界")
结束
输出("程序结束")
"""
    return run_test("async_string", code)


def test_async_nested_scope():
    """测试嵌套异步作用域"""
    code = """
异步 段落 任务A：
    输出("A")
    返回(1)
结束

异步 段落 任务B：
    输出("B")
    返回(2)
结束

输出("开始")
异步作用域：
    任务A()
    任务B()
结束
输出("中间")
异步作用域：
    任务A()
    任务B()
结束
输出("结束")
"""
    return run_test("async_nested_scope", code)


def test_async_await_with_condition():
    """测试 await 结合条件判断"""
    code = """
异步 段落 获取值(标记)：
    如果 标记 等于 1：
        返回(100)
    结束
    返回(200)
结束

异步 段落 处理器(标记)：
    设 值 为 等待 获取值(标记)
    输出("得到:")
    输出(值)
    返回(值)
结束

输出("程序开始")
异步作用域：
    处理器(1)
    处理器(2)
结束
输出("程序结束")
"""
    return run_test("async_await_condition", code)


if __name__ == '__main__':
    tests = [
        ("简单异步", test_async_simple),
        ("异步作用域", test_async_scope),
        ("await 等待", test_async_await),
        ("链式 await", test_async_chain),
        ("多次 await", test_async_multiple_await),
        ("带参数异步", test_async_with_params),
        ("条件分支异步", test_async_with_condition),
        ("作用域结果", test_async_scope_results),
        ("字符串操作", test_async_with_string),
        ("嵌套作用域", test_async_nested_scope),
        ("await 加条件", test_async_await_with_condition),
    ]
    
    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            print()
            if test_fn():
                print(f"  [OK] {name}")
                passed += 1
            else:
                print(f"  [失败] {name}")
                failed += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  [错误] {name}: {e}")
            failed += 1
    
    print(f"\n总计: {len(tests)}  |  通过: {passed}  |  失败: {failed}")
    sys.exit(0 if failed == 0 else 1)
