# 由光明编译器生成
# 源文件: 光明代码

import sys
import os

try:
    import importlib.util
except ImportError:
    importlib = None

try:
    _light_stdlib = os.path.join(os.path.dirname(__file__), 'stdlib')
except NameError:
    _light_stdlib = os.path.join(os.getcwd(), 'stdlib')
    if not os.path.isdir(_light_stdlib):
        # 尝试父目录（当从子目录运行时）
        parent_stdlib = os.path.normpath(os.path.join(os.getcwd(), '..', 'stdlib'))
        if os.path.isdir(parent_stdlib):
            _light_stdlib = parent_stdlib

if os.path.isdir(_light_stdlib) and _light_stdlib not in sys.path:
    sys.path.insert(0, _light_stdlib)

if importlib:
    try:
        _light_builtin_path = os.path.join(_light_stdlib, 'builtins.py')
        if os.path.isfile(_light_builtin_path):
            spec = importlib.util.spec_from_file_location('light_builtins', _light_builtin_path)
            _light_builtin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_light_builtin)
        else:
            raise ImportError()
    except:
        import types
        _light_builtin = types.ModuleType('_light_builtin')
        _light_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read()
        _light_builtin.写入文件 = lambda path, content: open(path, 'w', encoding='utf-8').write(content) or None
        _light_builtin.文件存在 = lambda path: __import__('os').path.isfile(path)
        _light_builtin.目录存在 = lambda path: __import__('os').path.isdir(path)
        _light_builtin.打印 = print
        _light_builtin.转字符串 = str
        _light_builtin.列表创建 = list
        _light_builtin.列表长度 = len
        _light_builtin.列 = lambda *args: list(args)
        _light_builtin.列表追加 = lambda lst, item: lst.append(item)
        _light_builtin.列表包含 = lambda lst, item: item in lst
        _light_builtin.字符串长度 = len
        _light_builtin.字典创建 = dict
        _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
        _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
        _light_builtin.字典键列表 = lambda d: list(d.keys())
except:
    import types
    _light_builtin = types.ModuleType('_light_builtin')
    _light_builtin.打印 = print
    _light_builtin.转字符串 = str
    _light_builtin.列表创建 = list
    _light_builtin.列表长度 = len
    _light_builtin.列 = lambda *args: list(args)
    _light_builtin.列表追加 = lambda lst, item: lst.append(item)
    _light_builtin.列表包含 = lambda lst, item: item in lst
    _light_builtin.字符串长度 = len
    _light_builtin.字典创建 = dict
    _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
    _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
    _light_builtin.字典键列表 = lambda d: list(d.keys())

print("你好，世界！")
甲 = 42
乙 = (甲 * 2)
print(乙)
def 求和(甲, 乙):
    return (甲 + 乙)

结果 = 求和(3, 5)
print(结果)