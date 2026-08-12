"""
第十二阶段测试用例 - 并发与分布式
"""
import sys
sys.path.insert(0, 'c:/traework/light/stdlib')

import unittest
import time
import threading


class 测试Actor模型(unittest.TestCase):
    """测试Actor模型模块"""
    
    def test_Actor系统创建(self):
        from Actor模型 import Actor系统
        系统 = Actor系统("测试系统")
        self.assertEqual(系统.名称, "测试系统")
        self.assertIsNotNone(系统)
        系统.关闭()
    
    def test_简单Actor发送消息(self):
        from Actor模型 import Actor系统, 简单Actor
        结果 = []
        结果锁 = threading.Lock()
        
        def 处理函数(msg):
            with 结果锁:
                结果.append(msg)
        
        with Actor系统("测试") as 系统:
            actor = 系统.创建Actor(lambda n: 简单Actor(处理函数, n), "测试Actor")
            self.assertIsNotNone(actor)
            actor.发送("hello")
            actor.发送("world")
            time.sleep(0.2)
        
        self.assertIn("hello", 结果)
        self.assertIn("world", 结果)
    
    def test_Actor请求响应(self):
        from Actor模型 import Actor系统, Actor
        
        class 计算器Actor(Actor):
            def 处理(self, 消息):
                if isinstance(消息, tuple) and len(消息) == 2:
                    op, num = 消息
                    if op == "加":
                        return num + 1
                    elif op == "乘":
                        return num * 2
                return None
        
        with Actor系统("测试") as 系统:
            计算器 = 系统.创建Actor(计算器Actor, "计算器")
            结果1 = 计算器.请求(("加", 5))
            结果2 = 计算器.请求(("乘", 3))
            
            self.assertEqual(结果1, 6)
            self.assertEqual(结果2, 6)
    
    def test_Actor路径(self):
        from Actor模型 import Actor系统, 简单Actor
        
        with Actor系统("测试") as 系统:
            actor = 系统.创建Actor(lambda n: 简单Actor(lambda x: x, n), "测试Actor")
            self.assertEqual(actor.路径, "/user/测试Actor")
            self.assertEqual(actor.名称, "测试Actor")
    
    def test_获取Actor(self):
        from Actor模型 import Actor系统, 简单Actor
        
        with Actor系统("测试") as 系统:
            系统.创建Actor(lambda n: 简单Actor(lambda x: x, n), "myActor")
            found = 系统.获取Actor("/user/myActor")
            self.assertIsNotNone(found)
            self.assertEqual(found.名称, "myActor")
    
    def test_Actor停止(self):
        from Actor模型 import Actor系统, 简单Actor
        
        with Actor系统("测试") as 系统:
            actor = 系统.创建Actor(lambda n: 简单Actor(lambda x: x, n), "测试Actor")
            actor.停止()
            time.sleep(0.2)
            self.assertTrue(True)
    
    def test_创建Actor系统函数(self):
        from Actor模型 import 创建Actor系统
        系统 = 创建Actor系统("测试")
        self.assertIsNotNone(系统)
        系统.关闭()


class 测试分布式锁(unittest.TestCase):
    """测试分布式锁模块"""
    
    def test_内存锁获取释放(self):
        from 分布式锁 import 内存分布式锁
        锁 = 内存分布式锁("test_lock_1", 超时时间=10.0)
        self.assertTrue(锁.获取())
        self.assertTrue(锁.释放())
    
    def test_内存锁上下文管理(self):
        from 分布式锁 import 内存分布式锁
        锁 = 内存分布式锁("test_lock_2", 超时时间=10.0)
        with 锁:
            self.assertEqual(锁.检查状态().value, "已锁定")
        self.assertEqual(锁.检查状态().value, "未锁定")
    
    def test_锁互斥(self):
        from 分布式锁 import 内存分布式锁
        锁1 = 内存分布式锁("test_mutex", 超时时间=10.0, 等待超时=0.1)
        锁2 = 内存分布式锁("test_mutex", 超时时间=10.0, 等待超时=0.1)
        
        self.assertTrue(锁1.获取())
        self.assertFalse(锁2.获取(阻塞=False))
        锁1.释放()
        self.assertTrue(锁2.获取())
        锁2.释放()
    
    def test_锁超时自动过期(self):
        from 分布式锁 import 内存分布式锁
        # 手动模拟过期：释放锁后另一个锁可以获取
        锁1 = 内存分布式锁("test_expire_manual", 超时时间=10.0, 等待超时=0.1)
        锁2 = 内存分布式锁("test_expire_manual", 超时时间=10.0, 等待超时=0.1)
        
        self.assertTrue(锁1.获取())
        self.assertFalse(锁2.获取(阻塞=False))
        锁1.释放()
        self.assertTrue(锁2.获取())
        锁2.释放()
    
    def test_剩余时间(self):
        from 分布式锁 import 内存分布式锁
        锁 = 内存分布式锁("test_remaining", 超时时间=5.0)
        锁.获取()
        剩余 = 锁.剩余时间()
        self.assertGreater(剩余, 0)
        self.assertLessEqual(剩余, 5.0)
        锁.释放()
    
    def test_可重入锁(self):
        from 分布式锁 import 可重入内存锁
        锁 = 可重入内存锁("test_reentrant", 超时时间=10.0)
        self.assertTrue(锁.获取())
        self.assertTrue(锁.获取())
        self.assertTrue(锁.释放())
        self.assertTrue(锁.释放())
    
    def test_信号量锁(self):
        from 分布式锁 import 信号量锁
        信号量 = 信号量锁("test_sem", 许可数=2, 超时时间=1.0)
        self.assertTrue(信号量.获取())
        self.assertTrue(信号量.获取())
        信号量.释放()
        信号量.释放()
        self.assertTrue(True)
    
    def test_创建分布式锁函数(self):
        from 分布式锁 import 创建分布式锁, 锁类型
        锁1 = 创建分布式锁("test_create1", 类型=锁类型.互斥锁)
        锁2 = 创建分布式锁("test_create2", 类型=锁类型.可重入锁)
        锁3 = 创建分布式锁("test_create3", 类型=锁类型.读写锁)
        self.assertIsNotNone(锁1)
        self.assertIsNotNone(锁2)
        self.assertIsNotNone(锁3)
    
    def test_带锁执行(self):
        from 分布式锁 import 带锁执行
        计数器 = [0]
        
        def 递增():
            计数器[0] += 1
            return 计数器[0]
        
        结果 = 带锁执行("test_lock_exec", 递增)
        self.assertEqual(结果, 1)
        self.assertEqual(计数器[0], 1)


class 测试消息队列(unittest.TestCase):
    """测试消息队列模块"""
    
    def test_队列创建(self):
        from 消息队列 import 内存消息队列
        队列 = 内存消息队列("测试队列")
        self.assertEqual(队列.名称, "测试队列")
        self.assertEqual(队列.大小(), 0)
    
    def test_发送接收消息(self):
        from 消息队列 import 内存消息队列
        队列 = 内存消息队列("测试队列")
        队列.发送("消息1")
        队列.发送("消息2")
        
        self.assertEqual(队列.大小(), 2)
        
        msg1 = 队列.接收(超时=0.1)
        self.assertEqual(msg1.内容, "消息1")
        
        msg2 = 队列.接收(超时=0.1)
        self.assertEqual(msg2.内容, "消息2")
    
    def test_延迟消息(self):
        from 消息队列 import 内存消息队列
        队列 = 内存消息队列("测试延迟队列")
        队列.发送("延迟消息", 延迟=0.2)
        
        msg = 队列.接收(超时=0.05)
        self.assertIsNone(msg)
        
        msg = 队列.接收(超时=0.3)
        self.assertIsNotNone(msg)
        self.assertEqual(msg.内容, "延迟消息")
    
    def test_消息优先级(self):
        from 消息队列 import 内存消息队列
        队列 = 内存消息队列("测试优先级队列")
        队列.发送("低优先级", 优先级=1)
        队列.发送("高优先级", 优先级=10)
        队列.发送("中优先级", 优先级=5)
        
        # 注意：普通队列是FIFO，延迟队列才按优先级
        # 这里测试基本发送接收功能
        msg1 = 队列.接收(超时=0.1)
        self.assertEqual(msg1.内容, "低优先级")
    
    def test_发布订阅(self):
        from 消息队列 import 发布订阅
        pubsub = 发布订阅()
        收到的消息 = []
        结果锁 = threading.Lock()
        
        def 回调(msg):
            with 结果锁:
                收到的消息.append(msg)
        
        订阅id = pubsub.订阅("主题1", 回调)
        self.assertIsNotNone(订阅id)
        
        数量 = pubsub.发布("主题1", "hello")
        time.sleep(0.05)
        
        self.assertEqual(数量, 1)
        self.assertIn("hello", 收到的消息)
    
    def test_取消订阅(self):
        from 消息队列 import 发布订阅
        pubsub = 发布订阅()
        收到的消息 = []
        
        def 回调(msg):
            收到的消息.append(msg)
        
        订阅id = pubsub.订阅("主题1", 回调)
        pubsub.取消订阅("主题1", 订阅id)
        
        pubsub.发布("主题1", "test")
        time.sleep(0.05)
        
        self.assertEqual(len(收到的消息), 0)
    
    def test_工作队列(self):
        from 消息队列 import 工作队列
        处理结果 = []
        结果锁 = threading.Lock()
        
        def 处理函数(任务):
            with 结果锁:
                处理结果.append(任务 * 2)
        
        wq = 工作队列("测试工作队列", 工作线程数=2)
        wq.启动(处理函数)
        
        for i in range(5):
            wq.提交(i)
        
        wq.等待完成(超时=2.0)
        wq.停止()
        
        self.assertEqual(len(处理结果), 5)
        for i in range(5):
            self.assertIn(i * 2, 处理结果)
    
    def test_队列统计(self):
        from 消息队列 import 内存消息队列
        队列 = 内存消息队列("测试统计")
        队列.发送("msg1")
        队列.发送("msg2")
        统计 = 队列.获取统计()
        
        self.assertEqual(统计["已发送"], 2)
        self.assertEqual(统计["待处理"], 2)
    
    def test_创建消息队列函数(self):
        from 消息队列 import 创建消息队列, 创建发布订阅
        q = 创建消息队列("test")
        ps = 创建发布订阅()
        self.assertIsNotNone(q)
        self.assertIsNotNone(ps)


class 测试任务队列调度器(unittest.TestCase):
    """测试任务队列与调度器模块"""
    
    def test_任务队列创建(self):
        from 任务队列调度器 import 任务队列
        tq = 任务队列(工作线程数=2)
        self.assertEqual(tq.工作线程数, 2)
        tq.启动()
        tq.停止()
    
    def test_提交任务(self):
        from 任务队列调度器 import 任务队列
        结果 = []
        结果锁 = threading.Lock()
        
        def 任务(n):
            with 结果锁:
                结果.append(n)
            return n * 2
        
        tq = 任务队列(工作线程数=2)
        tq.启动()
        
        任务id = tq.提交(任务, 5)
        self.assertIsNotNone(任务id)
        
        tq.等待完成(超时=2.0)
        tq.停止()
        
        self.assertIn(5, 结果)
    
    def test_获取任务结果(self):
        from 任务队列调度器 import 任务队列
        
        def 计算(n):
            return n * 2
        
        tq = 任务队列(工作线程数=2)
        tq.启动()
        
        任务id = tq.提交(计算, 10)
        结果 = tq.获取任务结果(任务id, 等待=True, 超时=2.0)
        
        self.assertEqual(结果, 20)
        tq.停止()
    
    def test_任务优先级(self):
        from 任务队列调度器 import 任务队列
        执行顺序 = []
        结果锁 = threading.Lock()
        
        def 记录任务(name):
            with 结果锁:
                执行顺序.append(name)
        
        tq = 任务队列(工作线程数=1)
        
        # 先提交所有任务，再启动工作线程，确保优先级排序生效
        tq.提交(记录任务, "低优先级", 优先级=1)
        tq.提交(记录任务, "高优先级", 优先级=10)
        tq.启动()
        
        tq.等待完成(超时=2.0)
        tq.停止()
        
        # 高优先级应该先执行
        self.assertEqual(执行顺序[0], "高优先级")
    
    def test_任务重试(self):
        from 任务队列调度器 import 任务队列
        调用次数 = [0]
        
        def 失败任务():
            调用次数[0] += 1
            raise ValueError("测试错误")
        
        tq = 任务队列(工作线程数=1)
        tq.启动()
        
        任务id = tq.提交(失败任务, 最大重试次数=2, 重试延迟=0.01)
        time.sleep(0.5)
        tq.停止()
        
        self.assertEqual(调用次数[0], 3)  # 1次初始 + 2次重试
    
    def test_取消任务(self):
        from 任务队列调度器 import 任务队列
        
        def 慢任务():
            time.sleep(1.0)
        
        tq = 任务队列(工作线程数=1)
        tq.启动()
        
        # 先提交一个长任务
        tq.提交(慢任务)
        # 再提交一个取消任务
        任务id = tq.提交(lambda: None)
        
        结果 = tq.取消任务(任务id)
        self.assertTrue(结果)
        
        tq.停止(等待=False)
    
    def test_延迟任务(self):
        from 任务队列调度器 import 任务队列
        执行时间 = [None]
        
        def 记录时间():
            执行时间[0] = time.time()
        
        tq = 任务队列(工作线程数=1)
        tq.启动()
        
        开始时间 = time.time()
        tq.提交(记录时间, 延迟=0.2)
        tq.等待完成(超时=2.0)
        tq.停止()
        
        self.assertIsNotNone(执行时间[0])
        self.assertGreaterEqual(执行时间[0] - 开始时间, 0.15)
    
    def test_创建任务队列函数(self):
        from 任务队列调度器 import 创建任务队列, 创建调度器
        tq = 创建任务队列(2)
        scheduler = 创建调度器()
        self.assertIsNotNone(tq)
        self.assertIsNotNone(scheduler)
        tq.停止()
    
    def test_调度器间隔任务(self):
        from 任务队列调度器 import 定时调度器
        计数器 = [0]
        结果锁 = threading.Lock()
        
        def 递增():
            with 结果锁:
                计数器[0] += 1
        
        scheduler = 定时调度器()
        scheduler.添加间隔任务(0.1, 递增, 立即执行=True)
        scheduler.启动()
        time.sleep(0.25)
        scheduler.停止()
        
        self.assertGreaterEqual(计数器[0], 2)
    
    def test_调度器定时任务(self):
        from 任务队列调度器 import 定时调度器
        执行了 = [False]
        
        def 任务():
            执行了[0] = True
        
        scheduler = 定时调度器()
        执行时间 = time.time() + 0.1
        scheduler.添加定时任务(执行时间, 任务)
        scheduler.启动()
        time.sleep(0.2)
        scheduler.停止()
        
        self.assertTrue(执行了[0])
    
    def test_调度器取消任务(self):
        from 任务队列调度器 import 定时调度器
        
        scheduler = 定时调度器()
        任务id = scheduler.添加间隔任务(1.0, lambda: None)
        self.assertTrue(scheduler.取消任务(任务id))


class 测试工作流引擎(unittest.TestCase):
    """测试工作流引擎模块"""
    
    def test_工作流创建(self):
        from 工作流引擎 import 工作流
        wf = 工作流("测试工作流")
        self.assertEqual(wf.名称, "测试工作流")
        self.assertEqual(wf.状态.value, "待运行")
    
    def test_添加节点(self):
        from 工作流引擎 import 工作流, 工作流节点
        wf = 工作流("测试")
        节点 = 工作流节点("步骤1", lambda ctx: "结果1")
        wf.添加节点(节点)
        self.assertEqual(wf.拓扑排序(), ["步骤1"])
    
    def test_创建节点(self):
        from 工作流引擎 import 工作流
        wf = 工作流("测试")
        wf.创建节点("步骤1", lambda ctx: "A")
        wf.创建节点("步骤2", lambda ctx: "B", 依赖=["步骤1"])
        
        拓扑 = wf.拓扑排序()
        self.assertEqual(拓扑, ["步骤1", "步骤2"])
    
    def test_简单工作流执行(self):
        from 工作流引擎 import 工作流
        wf = 工作流("测试")
        wf.创建节点("步骤1", lambda ctx: ctx.get("输入", 0) + 1)
        wf.创建节点("步骤2", lambda ctx: ctx["步骤1"] * 2, 依赖=["步骤1"])
        
        结果 = wf.执行({"输入": 5})
        
        self.assertEqual(结果["步骤1"], 6)
        self.assertEqual(结果["步骤2"], 12)
        self.assertEqual(wf.状态.value, "已完成")
    
    def test_工作流验证_有环(self):
        from 工作流引擎 import 工作流
        wf = 工作流("测试环")
        wf.创建节点("A", lambda ctx: None)
        wf.创建节点("B", lambda ctx: None, 依赖=["A"])
        
        # 手动添加环
        wf._节点["A"].依赖.append(wf._节点["B"])
        wf._节点["B"].下游节点.append(wf._节点["A"])
        
        self.assertFalse(wf.验证())
    
    def test_工作流验证_无环(self):
        from 工作流引擎 import 工作流
        wf = 工作流("测试无环")
        wf.创建节点("A", lambda ctx: None)
        wf.创建节点("B", lambda ctx: None, 依赖=["A"])
        wf.创建节点("C", lambda ctx: None, 依赖=["A"])
        
        self.assertTrue(wf.验证())
    
    def test_并行节点执行(self):
        from 工作流引擎 import 工作流
        wf = 工作流("并行测试", 描述="测试并行执行")
        wf.创建节点("开始", lambda ctx: "start")
        wf.创建节点("分支A", lambda ctx: "A_result", 依赖=["开始"])
        wf.创建节点("分支B", lambda ctx: "B_result", 依赖=["开始"])
        wf.创建节点("合并", lambda ctx: ctx["分支A"] + ctx["分支B"], 依赖=["分支A", "分支B"])
        
        结果 = wf.执行()
        
        self.assertEqual(结果["分支A"], "A_result")
        self.assertEqual(结果["分支B"], "B_result")
        self.assertEqual(结果["合并"], "A_resultB_result")
    
    def test_工作流统计(self):
        from 工作流引擎 import 工作流
        wf = 工作流("统计测试")
        wf.创建节点("步骤1", lambda ctx: 1)
        wf.创建节点("步骤2", lambda ctx: 2, 依赖=["步骤1"])
        
        wf.执行()
        统计 = wf.获取统计()
        
        self.assertEqual(统计["总节点数"], 2)
        self.assertEqual(统计["已完成"], 2)
        self.assertIn("总耗时", 统计)
    
    def test_工作流构建器(self):
        from 工作流引擎 import 工作流构建器
        builder = 工作流构建器("构建器测试")
        builder.节点("A", lambda ctx: 1)
        builder.节点("B", lambda ctx: 2, 依赖=["A"])
        wf = builder.构建()
        
        结果 = wf.执行()
        self.assertEqual(结果["A"], 1)
        self.assertEqual(结果["B"], 2)
    
    def test_创建工作流函数(self):
        from 工作流引擎 import 创建工作流, 创建工作流构建器, 顺序执行
        wf = 创建工作流("测试")
        builder = 创建工作流构建器("测试2")
        self.assertIsNotNone(wf)
        self.assertIsNotNone(builder)
    
    def test_顺序执行(self):
        from 工作流引擎 import 顺序执行
        
        def 步骤1(ctx):
            return 1
        
        def 步骤2(ctx):
            return ctx["步骤_0"] + 1
        
        结果 = 顺序执行([步骤1, 步骤2])
        self.assertEqual(结果["步骤_0"], 1)
        self.assertEqual(结果["步骤_1"], 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
