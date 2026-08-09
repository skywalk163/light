"""测试光明高级特性"""
import sys
sys.path.insert(0, 'g:/dumategithub/light/antlrparser')

from light_visitor import parse_source

# 测试代码
code = '''
【测试模块】

// 接口定义
《可打印》接口:
  《输出》方法 -> 串。
结束。

// 类定义
《动物》类:
  定义名称等于""。
  
  《说话》方法 -> 串:
    返回"动物叫"。
  结束。
结束。

《主段》段():
  打印("测试完成")。
结束。
'''

try:
    module = parse_source(code)
    print('解析成功!')
    print(f'模块名: {module.name}')
    print(f'接口数: {len(module.interfaces)}')
    print(f'类数: {len(module.classes)}')
    print(f'段数: {len(module.segments)}')
    
    if module.interfaces:
        print('\n接口:')
        for iface in module.interfaces:
            print(f'  - {iface.name}')
            for method in iface.methods:
                print(f'    方法: {method.name} -> {method.return_type}')
    
    if module.classes:
        print('\n类:')
        for cls in module.classes:
            print(f'  - {cls.name}')
            print(f'    字段数: {len(cls.fields)}')
            print(f'    方法数: {len(cls.methods)}')
            for method in cls.methods:
                print(f'      方法: {method.name} -> {method.return_type}')
    
except Exception as e:
    print(f'解析失败: {e}')
    import traceback
    traceback.print_exc()