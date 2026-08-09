# 由光明编译器生成
# 源文件: 光明代码

# 导入光明标准库
import sys
import importlib.util
try:
    spec = importlib.util.spec_from_file_location('light_builtins', 'src/stdlib/builtins.py')
    _light_builtin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_light_builtin)
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

def 平方(数值):
    return (数值 * 数值)

def 求和(甲, 乙):
    return (甲 + 乙)

def 阶乘(数值):
    if (数值 <= 1):
        return 1
    return (数值 * 阶乘((数值 - 1)))

class 动物:
    def 叫声(self):
        print('动物叫声')

class 狗(动物):
    def __init__(self, 名称, 品种):
        self.名称 = 名称
        self.品种 = 品种
    def 叫声(self):
        print('汪汪汪')
    def 介绍(self):
        print('我是')
        print(self.名称)
        print('品种：')
        print(self.品种)

甲 = 10
乙 = 20
结果 = (甲 + 乙)
print(结果)
平方值 = 平方(5)
print(平方值)
和值 = 求和(10, 20)
print(和值)
分数 = 85
if (分数 > 60):
    print('及格')
else:
    print('不及格')
计数 = 0
while (计数 < 3):
    print(计数)
    计数 = (计数 + 1)
水果 = ['苹果', '香蕉', '橙子']
for 水果项 in 水果:
    print(水果项)
print(阶乘(5))
小狗 = 狗('旺财', '金毛')
小狗.叫声()
小狗.介绍()
print('所有测试完成！')