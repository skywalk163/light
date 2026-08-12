# 由光明编译器生成
# 源文件: 光明代码

# 导入光明标准库
import sys
import os
import asyncio

try:
    import importlib.util
except ImportError:
    importlib = None

try:
    _light_stdlib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stdlib')
except NameError:
    _light_stdlib = os.path.join(os.getcwd(), 'stdlib')
    if not os.path.isdir(_light_stdlib):
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
        _light_builtin.列表创建 = list
        _light_builtin.列表追加 = lambda lst, item: lst.append(item)
        _light_builtin.列表包含 = lambda lst, item: item in lst
        _light_builtin.字符串长度 = len
        _light_builtin.字典创建 = dict
        _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
        _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
        _light_builtin.转整数 = lambda text: int(text)
        _light_builtin.转浮点 = lambda text: float(text)
        _light_builtin.时间戳 = lambda: int(__import__('time').time())
        _light_builtin.格式化时间 = lambda ts, fmt: __import__('time').strftime(fmt, __import__('time').localtime(ts))
        _light_builtin.JSON序列化 = lambda obj, indent=2: json.dumps(obj, ensure_ascii=False, indent=indent)
else:
    import types
    _light_builtin = types.ModuleType('_light_builtin')
    _light_builtin.打印 = print
    _light_builtin.转整数 = lambda text: int(text)
    _light_builtin.转浮点 = lambda text: float(text)
    _light_builtin.时间戳 = lambda: int(__import__('time').time())
    _light_builtin.格式化时间 = lambda ts, fmt: __import__('time').strftime(fmt, __import__('time').localtime(ts))
    _light_builtin.JSON序列化 = lambda obj, indent=2: json.dumps(obj, ensure_ascii=False, indent=indent)

def 解析CSV行(行):
    结果 = []
    当前 = ''
    在引号中 = 0
    i = 0
    while (i < len(行)):
        字符 = 行[i]
        if (字符 == '"'):
            if (在引号中 == 1):
                在引号中 = 0
            else:
                在引号中 = 1
        elif (字符 == ','):
            if (在引号中 == 0):
                结果 = (结果 + [当前])
                当前 = ''
            else:
                当前 = (当前 + 字符)
        else:
            当前 = (当前 + 字符)
        i = (i + 1)
    结果 = (结果 + [当前])
    return 结果

def 解析CSV(文本):
    行列表 = 分割(文本, '\n')
    结果 = []
    表头 = 解析CSV行(行列表[0])
    i = 1
    while (i < len(行列表)):
        if (行列表[i] != ''):
            行数据 = 解析CSV行(行列表[i])
            行记录 = {}
            j = 0
            while ((j < len(表头)) and (j < len(行数据))):
                行记录[表头[j]] = 行数据[j]
                j = (j + 1)
            结果 = (结果 + [行记录])
        i = (i + 1)
    return 结果

def 分割(文本, 分隔符):
    结果 = []
    当前 = ''
    分隔长度 = len(分隔符)
    i = 0
    while (i < len(文本)):
        if (文本[slice(i, (i + 分隔长度))] == 分隔符):
            结果 = (结果 + [当前])
            当前 = ''
            i = (i + 分隔长度)
        else:
            当前 = (当前 + 文本[i])
            i = (i + 1)
    结果 = (结果 + [当前])
    return 结果

def 求和(列表):
    总和 = 0
    for 项 in 列表:
        总和 = (总和 + 项)
    return 总和

def 平均数(列表):
    长度 = len(列表)
    if (长度 == 0):
        return 0
    return (求和(列表) / 长度)

def 求最大(列表):
    最大值 = 列表[0]
    for 项 in 列表:
        if (项 > 最大值):
            最大值 = 项
    return 最大值

def 求最小(列表):
    最小值 = 列表[0]
    for 项 in 列表:
        if (项 < 最小值):
            最小值 = 项
    return 最小值

def 转数值(文本):
    return _light_builtin.转整数(文本)

def 统计摘要(数值列表):
    if (len(数值列表) == 0):
        return {}
    摘要 = {}
    摘要['计数'] = len(数值列表)
    摘要['求和'] = 求和(数值列表)
    摘要['平均数'] = 平均数(数值列表)
    摘要['最大值'] = 求最大(数值列表)
    摘要['最小值'] = 求最小(数值列表)
    return 摘要

def 分组聚合(记录列表, 分组键, 聚合键):
    分组 = {}
    for 记录 in 记录列表:
        键 = 记录[分组键]
        if (键 in 分组):
            分组[键] = (分组[键] + [转数值(记录[聚合键])])
        else:
            分组[键] = [转数值(记录[聚合键])]
    结果 = {}
    for 键 in 分组:
        结果[键] = 统计摘要(分组[键])
    return 结果

print('=== 数据处理演示 ===')
print('')
csv数据 = '姓名,年龄,城市,分数\n张三,25,北京,85\n李四,30,上海,92\n王五,22,广州,78\n赵六,28,北京,95\n陈七,35,上海,88'
print('原始 CSV 数据：')
print(csv数据)
print('')
记录列表 = 解析CSV(csv数据)
print('解析后记录数：')
print(len(记录列表))
print('')
print('逐条记录：')
for 记录 in 记录列表:
    print(记录)
print('')
分数列表 = []
for 记录 in 记录列表:
    分数列表 = (分数列表 + [转数值(记录['分数'])])
print('分数统计摘要：')
摘要 = 统计摘要(分数列表)
print(摘要)
print('')
print('按城市分组聚合（分数）：')
聚合结果 = 分组聚合(记录列表, '城市', '分数')
for 城市 in 聚合结果:
    print(城市)
    print(聚合结果[城市])
print('')
print('前三名（高分）：')
排序分数 = []
for 分数 in 分数列表:
    排序分数 = (排序分数 + [分数])
排序完成 = False
i = 0
while (not 排序完成):
    排序完成 = True
    while (i < (len(排序分数) - 1)):
        if (排序分数[i] < 排序分数[(i + 1)]):
            临时 = 排序分数[i]
            排序分数[i] = 排序分数[(i + 1)]
            排序分数[(i + 1)] = 临时
            排序完成 = False
        i = (i + 1)
print(排序分数[slice(0, 3)])
print('')
print('=== 数据处理完成 ===')