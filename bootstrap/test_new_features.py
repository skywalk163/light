"""测试自举编译器新增功能"""
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from run_compiler import compile_bootstrap_dir, execute_generated_code

def run_bootstrap_compiler(code, filename='<test>'):
    """使用自举编译器编译段言代码"""
    tmp_dir = tempfile.mkdtemp()
    src_path = os.path.join(tmp_dir, 'test.duan')
    with open(src_path, 'w', encoding='utf-8') as f:
        f.write(code)
    result = compile_bootstrap_dir(src_path)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return result

def test_interface():
    """测试接口定义"""
    code = """
接口 可打印：
  段落 打印内容 返回 文本。
"""
    result = run_bootstrap_compiler(code, '<test>')
    print("=== 接口测试 ===")
    print(result)
    assert 'class 可打印(ABC):' in result, "接口应生成 ABC 类"
    assert '@abstractmethod' in result, "应包含 abstractmethod"
    assert 'def 打印内容(self' in result, "应包含方法定义"
    print("接口测试通过！\n")

def test_match():
    """测试匹配语句"""
    code = """
段落 测试匹配 接收 值：
  匹配 值：
    情况 1：
      打印("一")
    情况 2：
      打印("二")
    情况 _：
      打印("其他")
"""
    result = run_bootstrap_compiler(code, '<test>')
    print("=== 匹配测试 ===")
    print(result)
    assert 'match ' in result, "应生成 match 语句"
    assert 'case 1:' in result, "应包含 case 1"
    assert 'case _:' in result, "应包含通配符 case"
    print("匹配测试通过！\n")

def test_with():
    """测试使用语句"""
    code = """
段落 测试使用：
  使用 读取文件("test.txt") 为 f：
    打印(f)
"""
    result = run_bootstrap_compiler(code, '<test>')
    print("=== 使用测试 ===")
    print(result)
    assert 'with ' in result, "应生成 with 语句"
    assert 'as f' in result, "应包含 as 绑定"
    print("使用测试通过！\n")

def test_try():
    """测试尝试语句"""
    code = """
段落 测试尝试：
  尝试：
    打印("尝试块")
  捕获 错误：
    打印("出错")
  最终：
    打印("最终")
"""
    result = run_bootstrap_compiler(code, '<test>')
    print("=== 尝试测试 ===")
    print(result)
    assert 'try:' in result, "应生成 try 语句"
    assert 'except' in result, "应生成 except 语句"
    assert 'finally:' in result, "应生成 finally 语句"
    print("尝试测试通过！\n")

def test_throw():
    """测试抛出语句"""
    code = """
段落 测试抛出：
  抛出 "出错了"
"""
    result = run_bootstrap_compiler(code, '<test>')
    print("=== 抛出测试 ===")
    print(result)
    assert 'raise ' in result, "应生成 raise 语句"
    print("抛出测试通过！\n")

def test_interface_with_inheritance():
    """测试带继承的接口"""
    code = """
接口 高级接口 继承 基础接口：
  段落 新方法 接收 x 返回 整数。
"""
    result = run_bootstrap_compiler(code, '<test>')
    print("=== 继承接口测试 ===")
    print(result)
    assert 'class 高级接口(ABC, 基础接口):' in result, "应包含继承关系"
    print("继承接口测试通过！\n")

def test_match_with_guard():
    """测试带守卫条件的匹配"""
    code = """
段落 测试守卫 接收 值:
  匹配 值:
    情况 x 若 x 大于 5:
      打印("大")
    情况 _:
      打印("小")
"""
    result = run_bootstrap_compiler(code, '<test>')
    print("=== 带守卫匹配测试 ===")
    print(result)
    assert ' if ' in result, "应包含 if 守卫条件"
    print("带守卫匹配测试通过！\n")

if __name__ == '__main__':
    test_interface()
    test_match()
    test_with()
    test_try()
    test_throw()
    test_interface_with_inheritance()
    test_match_with_guard()
    print("\n所有新增功能测试通过！")