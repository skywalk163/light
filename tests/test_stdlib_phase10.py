"""
第十阶段测试用例 - 元编程与代码生成
"""
import sys
sys.path.insert(0, 'c:/dumatework/light/stdlib')
sys.path.insert(0, 'c:/dumatework/light/contrib')

import unittest


class 测试AST操作(unittest.TestCase):
    """测试AST操作模块"""
    
    def test_解析代码(self):
        from AST操作 import AST工具
        代码 = 'x = 1 + 2'
        树 = AST工具.解析代码(代码)
        self.assertIsNotNone(树)
    
    def test_生成代码(self):
        from AST操作 import AST工具
        代码 = 'x = 1 + 2'
        树 = AST工具.解析代码(代码)
        生成的代码 = AST工具.生成代码(树)
        self.assertIn('x', 生成的代码)
    
    def test_美化输出(self):
        from AST操作 import AST工具
        代码 = 'x = 1'
        树 = AST工具.解析代码(代码)
        输出 = AST工具.美化输出(树)
        self.assertIn('Module', 输出)
    
    def test_获取所有函数(self):
        from AST操作 import AST工具
        代码 = '''
def 函数1():
    pass

def 函数2():
    pass
'''
        树 = AST工具.解析代码(代码)
        函数列表 = AST工具.获取所有函数(树)
        self.assertEqual(len(函数列表), 2)
    
    def test_获取所有类(self):
        from AST操作 import AST工具
        代码 = '''
class 类1:
    pass

class 类2:
    pass
'''
        树 = AST工具.解析代码(代码)
        类列表 = AST工具.获取所有类(树)
        self.assertEqual(len(类列表), 2)
    
    def test_代码生成器_生成函数(self):
        from AST操作 import 代码生成器
        函数代码 = 代码生成器.生成函数('测试函数', ['x', 'y'], 'return x + y')
        self.assertIn('def 测试函数', 函数代码)
    
    def test_代码生成器_生成类(self):
        from AST操作 import 代码生成器
        类代码 = 代码生成器.生成类('测试类', 属性字典={'值': 42})
        self.assertIn('class 测试类', 类代码)
    
    def test_代码分析器(self):
        from AST操作 import 代码分析器
        代码 = '''
def 函数1():
    pass

class 类1:
    pass
'''
        分析器 = 代码分析器(代码)
        报告 = 分析器.生成报告()
        self.assertEqual(报告['函数数量'], 1)
        self.assertEqual(报告['类数量'], 1)
    
    def test_模式匹配器_查找空函数(self):
        from AST操作 import 模式匹配器, AST工具
        代码 = '''
def 空函数():
    pass

def 非空函数():
    x = 1
    return x
'''
        树 = AST工具.解析代码(代码)
        空函数 = 模式匹配器.查找空函数(树)
        self.assertEqual(len(空函数), 1)
    
    def test_便捷函数(self):
        from AST操作 import 解析代码, 生成代码, 分析代码
        代码 = 'x = 1'
        树 = 解析代码(代码)
        self.assertIsNotNone(树)
        生成的 = 生成代码(树)
        self.assertIn('x', 生成的)
        报告 = 分析代码(代码)
        self.assertIn('函数数量', 报告)


class 测试类型系统增强(unittest.TestCase):
    """测试类型系统增强模块"""
    
    def test_类型检查(self):
        from 类型系统增强 import 类型检查
        类型检查(1, int)
        类型检查('hello', str)
    
    def test_类型检查失败(self):
        from 类型系统增强 import 类型检查, 类型校验失败异常
        try:
            类型检查('hello', int, '参数')
            self.fail('应该抛出异常')
        except 类型校验失败异常:
            pass
    
    def test_类型校验装饰器(self):
        from 类型系统增强 import 类型校验
        
        @类型校验(int, int)
        def 加法(x, y):
            return x + y
        
        self.assertEqual(加法(1, 2), 3)
    
    def test_返回值类型检查(self):
        from 类型系统增强 import 返回值类型检查
        
        @返回值类型检查(int)
        def 返回整数():
            return 42
        
        self.assertEqual(返回整数(), 42)
    
    def test_泛型列表(self):
        from 类型系统增强 import 创建泛型列表
        
        列表 = 创建泛型列表(int)
        列表.添加(1)
        列表.添加(2)
        self.assertEqual(列表.长度(), 2)
        self.assertEqual(列表.获取(0), 1)
    
    def test_泛型列表类型错误(self):
        from 类型系统增强 import 创建泛型列表, 类型校验失败异常
        
        列表 = 创建泛型列表(int)
        try:
            列表.添加('hello')
            self.fail('应该抛出异常')
        except 类型校验失败异常:
            pass
    
    def test_泛型字典(self):
        from 类型系统增强 import 创建泛型字典
        
        字典 = 创建泛型字典(str, int)
        字典.设置('a', 1)
        字典.设置('b', 2)
        self.assertEqual(字典.获取('a'), 1)
        self.assertEqual(字典.长度(), 2)
    
    def test_可选类型(self):
        from 类型系统增强 import 可选类型
        
        可选 = 可选类型(int)
        self.assertTrue(可选.检查(42))
        self.assertTrue(可选.检查(None))
        self.assertFalse(可选.检查('hello'))
    
    def test_数据类(self):
        from 类型系统增强 import 数据类
        
        class 人(数据类):
            pass
        
        p = 人(姓名='张三', 年龄=25)
        self.assertEqual(p.姓名, '张三')
        self.assertEqual(p.年龄, 25)
        self.assertIn('张三', repr(p))
    
    def test_验证器(self):
        from 类型系统增强 import 验证器
        
        验证器.非空('hello', '名称')
        验证器.长度范围('hello', 3, 10, '名称')
        验证器.数值范围(5, 1, 10, '分数')
    
    def test_枚举(self):
        from 类型系统增强 import 枚举
        
        class 颜色(枚举):
            红 = 1
            绿 = 2
            蓝 = 3
        
        self.assertTrue(颜色.包含值(1))
        self.assertEqual(颜色.获取名称(1), '红')
        self.assertEqual(len(颜色.值列表()), 3)


class 测试对象池缓存(unittest.TestCase):
    """测试对象池缓存模块"""
    
    def test_对象池_获取释放(self):
        from 对象池缓存 import 对象池
        
        创建计数 = [0]
        
        def 创建对象():
            创建计数[0] += 1
            return {'id': 创建计数[0]}
        
        池 = 对象池(创建对象, 最大大小=5, 初始化数量=2)
        self.assertEqual(池.可用数量(), 2)
        
        对象1 = 池.获取()
        对象2 = 池.获取()
        self.assertEqual(池.已用数量(), 2)
        
        池.释放(对象1)
        self.assertEqual(池.可用数量(), 1)
    
    def test_对象池_上下文管理器(self):
        from 对象池缓存 import 对象池, 对象上下文管理器
        
        def 创建对象():
            return {'值': 42}
        
        with 对象池(创建对象, 最大大小=3) as 池:
            with 对象上下文管理器(池) as 对象:
                self.assertEqual(对象['值'], 42)
            self.assertEqual(池.可用数量(), 1)
    
    def test_LRU缓存_基本操作(self):
        from 对象池缓存 import LRU缓存
        
        缓存 = LRU缓存(最大容量=3)
        缓存.设置('a', 1)
        缓存.设置('b', 2)
        缓存.设置('c', 3)
        
        self.assertEqual(缓存.获取('a'), 1)
        self.assertEqual(缓存.大小(), 3)
    
    def test_LRU缓存_淘汰(self):
        from 对象池缓存 import LRU缓存
        
        缓存 = LRU缓存(最大容量=2)
        缓存.设置('a', 1)
        缓存.设置('b', 2)
        缓存.设置('c', 3)
        
        self.assertIsNone(缓存.获取('a'))
        self.assertEqual(缓存.获取('b'), 2)
        self.assertEqual(缓存.获取('c'), 3)
    
    def test_LRU缓存_命中率(self):
        from 对象池缓存 import LRU缓存
        
        缓存 = LRU缓存(最大容量=10)
        缓存.设置('a', 1)
        缓存.获取('a')
        缓存.获取('b')
        
        self.assertEqual(缓存.命中率(), 0.5)
    
    def test_简单缓存_过期(self):
        from 对象池缓存 import 简单缓存
        import time
        
        缓存 = 简单缓存(过期时间=0.1)
        缓存.设置('a', 1)
        self.assertEqual(缓存.获取('a'), 1)
        
        time.sleep(0.15)
        self.assertIsNone(缓存.获取('a'))
    
    def test_定时缓存(self):
        from 对象池缓存 import 定时缓存
        
        调用次数 = [0]
        
        def 获取数据():
            调用次数[0] += 1
            return 调用次数[0]
        
        缓存 = 定时缓存(获取数据, 刷新间隔=60)
        self.assertEqual(缓存.获取(), 1)
        self.assertEqual(缓存.获取(), 1)
        self.assertEqual(缓存.刷新(), 2)
    
    def test_缓存装饰器(self):
        from 对象池缓存 import 缓存装饰器
        
        调用次数 = [0]
        
        @缓存装饰器(最大容量=10)
        def 计算(n):
            调用次数[0] += 1
            return n * n
        
        self.assertEqual(计算(5), 25)
        self.assertEqual(计算(5), 25)
        self.assertEqual(调用次数[0], 1)
    
    def test_便捷函数(self):
        from 对象池缓存 import 创建LRU缓存, 创建简单缓存, 创建对象池
        
        缓存 = 创建LRU缓存(100)
        self.assertIsNotNone(缓存)
        
        缓存2 = 创建简单缓存()
        self.assertIsNotNone(缓存2)
        
        池 = 创建对象池(lambda: {}, 5)
        self.assertIsNotNone(池)


class 测试插件系统(unittest.TestCase):
    """测试插件系统模块"""
    
    def test_插件基类(self):
        from 插件系统 import 插件
        
        class 测试插件(插件):
            名称 = 'test'
        
        p = 测试插件()
        self.assertEqual(p.名称, 'test')
        self.assertFalse(p.已启用)
    
    def test_插件管理器_基本操作(self):
        from 插件系统 import 插件管理器, 插件
        
        class 测试插件(插件):
            名称 = 'test_plugin'
            
            def 初始化插件(self):
                self.初始化了 = True
        
        管理器 = 插件管理器()
        
        import sys
        模块名 = '测试插件模块'
        模块 = type(sys)(模块名)
        模块.测试插件 = 测试插件
        sys.modules[模块名] = 模块
        
        管理器.添加插件路径('.')
        
        self.assertFalse(管理器.已加载('不存在的插件'))
    
    def test_插件管理器_扩展点(self):
        from 插件系统 import 插件管理器
        
        管理器 = 插件管理器()
        结果列表 = []
        
        def 回调1(x):
            结果列表.append(f'回调1:{x}')
        
        def 回调2(x):
            结果列表.append(f'回调2:{x}')
        
        管理器.注册扩展点('测试点', 回调1)
        管理器.注册扩展点('测试点', 回调2)
        
        管理器.触发扩展点('测试点', 'hello')
        self.assertEqual(len(结果列表), 2)
    
    def test_动态模块加载器_从字符串(self):
        from 插件系统 import 动态模块加载器
        
        代码 = '''
def 测试函数():
    return 42

测试变量 = 'hello'
'''
        模块 = 动态模块加载器.从字符串加载(代码, '测试动态模块')
        self.assertEqual(模块.测试函数(), 42)
        self.assertEqual(模块.测试变量, 'hello')
    
    def test_便捷函数(self):
        from 插件系统 import 创建插件管理器, 动态加载代码
        
        管理器 = 创建插件管理器()
        self.assertIsNotNone(管理器)
        
        模块 = 动态加载代码('x = 1', '测试模块')
        self.assertEqual(模块.x, 1)


class 测试DSL支持(unittest.TestCase):
    """测试DSL支持模块"""
    
    def test_词法分析器(self):
        from DSL支持 import 词法分析器
        
        分析器 = 词法分析器.创建默认词法分析器()
        token列表 = 分析器.分词('1 + 2')
        
        self.assertTrue(len(token列表) > 0)
    
    def test_解释器_数字运算(self):
        from DSL支持 import 解释器
        
        解释器实例 = 解释器()
        结果 = 解释器实例.执行('2 + 3 * 4')
        self.assertEqual(结果, 14)
    
    def test_解释器_变量(self):
        from DSL支持 import 解释器
        
        解释器实例 = 解释器()
        解释器实例.设置变量('x', 10)
        结果 = 解释器实例.执行('x + 5')
        self.assertEqual(结果, 15)
    
    def test_解释器_函数调用(self):
        from DSL支持 import 解释器
        
        解释器实例 = 解释器()
        解释器实例.注册函数('double', lambda x: x * 2)
        结果 = 解释器实例.执行('double(5)')
        self.assertEqual(结果, 10)
    
    def test_表达式求值器(self):
        from DSL支持 import 表达式求值器
        
        求值器 = 表达式求值器()
        求值器.设置变量('a', 10)
        求值器.设置变量('b', 20)
        结果 = 求值器.求值('a + b')
        self.assertEqual(结果, 30)
    
    def test_模板引擎DSL(self):
        from DSL支持 import 模板引擎DSL
        
        引擎 = 模板引擎DSL()
        模板 = '你好, {{ name }}! 你有 {{ count }} 条消息。'
        结果 = 引擎.渲染(模板, {'name': '张三', 'count': 5})
        self.assertIn('张三', 结果)
        self.assertIn('5', 结果)
    
    def test_简单DSL(self):
        from DSL支持 import 简单DSL
        
        dsl = 简单DSL()
        dsl.设置变量('x', 10)
        结果 = dsl.执行('x + 5')
        self.assertEqual(结果, 15)
    
    def test_便捷函数(self):
        from DSL支持 import 求值表达式, 渲染模板, 创建DSL, 分词
        
        结果 = 求值表达式('2 + 3 * 4', {})
        self.assertEqual(结果, 14)
        
        模板结果 = 渲染模板('{{ x }}', {'x': 42})
        self.assertEqual(模板结果.strip(), '42')
        
        dsl = 创建DSL()
        self.assertIsNotNone(dsl)
        
        token列表 = 分词('1 + 2')
        self.assertTrue(len(token列表) > 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)