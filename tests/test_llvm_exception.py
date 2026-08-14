"""测试 LLVM 后端异常处理支持"""
import sys
import os
import subprocess
import tempfile
sys.path.insert(0, 'src')

from llvm.compiler import compile_source_typed, find_clang


def run_llvm_test(name, code, expected_output=None, expected_returncode=0):
    """运行一个 LLVM 后端异常处理测试"""
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
        
        # 检查返回码
        if run_result.returncode != expected_returncode:
            print(f"返回码不匹配: 期望 {expected_returncode}, 得到 {run_result.returncode}")
            return False
        
        # 检查输出
        if expected_output is not None:
            if expected_output not in run_result.stdout:
                print(f"输出不匹配: 期望包含 '{expected_output}'")
                return False
        
        return True
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"错误: {e}")
        return False


def test_try_catch_basic():
    """基本 try/catch：捕获异常"""
    code = """
输出("开始")
尝试：
    输出("尝试块")
捕获 错误：
    输出("捕获块")
结束
输出("结束")
"""
    return run_llvm_test("exc_basic", code, "尝试块")


def test_try_catch_exception():
    """try/catch 捕获真实异常（除零）"""
    code = """
输出("开始")
尝试：
    设 x 为 1 除 0
    输出("不会执行")
捕获 错误：
    输出("捕获到除零异常")
结束
输出("结束")
"""
    return run_llvm_test("exc_divzero", code, "捕获到除零异常")


def test_try_catch_with_type():
    """按类型捕获异常（类型匹配时捕获）"""
    code = """
输出("开始")
尝试：
    设 x 为 1 除 0
    输出("不会执行")
捕获 ZeroDivisionError：
    输出("捕获到 ZeroDivisionError")
结束
输出("结束")
"""
    return run_llvm_test("exc_type_match", code, "捕获到 ZeroDivisionError")


def test_try_catch_wrong_type():
    """按类型捕获但类型不匹配（异常传播导致崩溃）"""
    code = """
输出("开始")
尝试：
    设 x 为 1 除 0
    输出("不会执行")
捕获 ValueError：
    输出("不会执行")
结束
输出("不会执行")
"""
    return run_llvm_test("exc_type_mismatch", code, expected_returncode=0)


def test_try_catch_finally():
    """try/catch/finally 完整组合"""
    code = """
输出("开始")
尝试：
    输出("尝试块")
捕获 错误：
    输出("捕获块")
最终：
    输出("最终块")
结束
输出("结束")
"""
    return run_llvm_test("exc_try_catch_finally", code, "最终块")


def test_try_finally():
    """try/finally（无 catch）"""
    code = """
输出("开始")
尝试：
    输出("尝试块")
最终：
    输出("最终块")
结束
输出("结束")
"""
    return run_llvm_test("exc_try_finally", code, "最终块")


def test_try_finally_exception():
    """try/finally 在异常时仍执行 finally"""
    code = """
输出("开始")
尝试：
    输出("尝试块")
    设 x 为 1 除 0
    输出("不会执行")
最终：
    输出("最终块")
结束
输出("不会执行")
"""
    return run_llvm_test("exc_finally_always", code, "最终块")


def test_throw_basic():
    """抛出基本异常"""
    code = """
输出("开始")
尝试：
    输出("尝试块")
    抛出("自定义错误")
    输出("不会执行")
捕获 错误：
    输出("捕获到自定义错误")
结束
输出("结束")
"""
    return run_llvm_test("exc_throw_basic", code, "捕获到自定义错误")


def test_throw_in_function():
    """在函数内抛出异常"""
    code = """
段落 除法(甲, 乙)：
    如果 乙 等于 0：
        抛出("除数不能为零")
    结束
    返回 甲 除 乙
结束

输出("开始")
尝试：
    设 结果 为 除法(10, 0)
    输出("不会执行")
捕获 错误：
    输出("捕获到函数内异常")
结束
输出("结束")
"""
    return run_llvm_test("exc_throw_in_func", code, "捕获到函数内异常")


def test_throw_string():
    """抛出字符串异常"""
    code = """
输出("开始")
尝试：
    抛出("这是一个错误消息")
捕获 错误：
    输出("捕获到异常")
结束
输出("结束")
"""
    return run_llvm_test("exc_throw_string", code, "捕获到异常")


def test_nested_try():
    """嵌套 try/catch"""
    code = """
输出("开始")
尝试：
    输出("外层尝试")
    尝试：
        输出("内层尝试")
        抛出("内层错误")
        输出("不会执行")
    捕获 错误：
        输出("内层捕获")
    结束
    输出("外层继续")
捕获 错误：
    输出("外层捕获")
结束
输出("结束")
"""
    return run_llvm_test("exc_nested", code, "内层捕获")


def test_multi_catch():
    """多 catch 子句"""
    code = """
段落 触发错误(类型)：
    如果 类型 等于 1：
        抛出("类型一错误")
    结束
    如果 类型 等于 2：
        抛出("类型二错误")
    结束
    抛出("未知错误")
结束

输出("开始")
尝试：
    触发错误(1)
捕获 错误：
    输出("通用捕获")
结束
输出("结束")
"""
    return run_llvm_test("exc_multi_catch", code, "通用捕获")


def test_exception_in_loop():
    """循环中的异常处理"""
    code = """
遍历 设 i 为 0 到 2：
    输出("循环:")
    输出(i)
    尝试：
        如果 i 等于 1：
            抛出("中间错误")
        结束
        输出("正常")
    捕获 错误：
        输出("捕获")
    结束
结束
输出("完成")
"""
    return run_llvm_test("exc_in_loop", code, "完成")


if __name__ == '__main__':
    tests = [
        ("基本 try/catch", test_try_catch_basic),
        ("捕获真实异常", test_try_catch_exception),
        ("按类型捕获", test_try_catch_with_type),
        ("类型不匹配", test_try_catch_wrong_type),
        ("try/catch/finally", test_try_catch_finally),
        ("try/finally", test_try_finally),
        ("异常时 finally", test_try_finally_exception),
        ("抛出基本异常", test_throw_basic),
        ("函数内抛出", test_throw_in_function),
        ("抛出字符串", test_throw_string),
        ("嵌套 try/catch", test_nested_try),
        ("多 catch 子句", test_multi_catch),
        ("循环中异常", test_exception_in_loop),
    ]
    
    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
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