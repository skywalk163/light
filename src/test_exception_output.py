# 由光明编译器生成
# 源文件: 光明代码

# 导入光明标准库
import sys
import importlib.util
try:
    # 尝试从src/stdlib导入
    spec = importlib.util.spec_from_file_location('light_builtins', 'stdlib/builtins.py')
    _light_builtin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_light_builtin)
except:
    # 如果无法导入，使用内置函数占位
    import types
    _light_builtin = types.ModuleType('_light_builtin')
    _light_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read()
    _light_builtin.写入文件 = lambda path, content: open(path, 'w', encoding='utf-8').write(content) or None
    _light_builtin.文件存在 = lambda path: __import__('os').path.isfile(path)
    _light_builtin.目录存在 = lambda path: __import__('os').path.isdir(path)
    _light_builtin.打印 = print
    _light_builtin.列表创建 = list
    _light_builtin.列表追加 = lambda lst, item: lst.append(item)
    _light_builtin.列表包含 = lambda lst, item: item in lst
    _light_builtin.字符串长度 = len
    _light_builtin.字典创建 = dict
    _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
    _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)

def 测试基本异常():
    try:
        print("尝试执行")
    except Exception as 错误:
        print(错误)
    return 0

def 测试抛出异常():
    try:
        print("开始")
        raise 异常("测试错误")
        print("不会执行")
    except Exception as 错误:
        print("捕获到异常")
    return 0

def 测试最终块():
    try:
        print("尝试块")
    except Exception as 错误:
        print(错误)
    finally:
        print("最终块")
    return 0

class 异常:
    def __init__(self, 消息):
        self.消息 = 消息


def 主():
    print("=== 测试基本异常 ===")
    测试基本异常
    print("")
    print("=== 测试抛出异常 ===")
    测试抛出异常
    print("")
    print("=== 测试最终块 ===")
    测试最终块
    return 0
