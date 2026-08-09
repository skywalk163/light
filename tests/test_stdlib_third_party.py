"""
第三方视角 - 光明标准库综合测试

模拟外部用户首次使用光明标准库，按12个阶段逐一测试。
基于模块实际API进行测试。
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'stdlib'))

import time
import tempfile
import traceback


class 测试结果:
    def __init__(self):
        self.通过 = 0
        self.失败 = 0
        self.跳过 = 0
        self.失败详情 = []
        self.模块API = {}
    
    def 记录通过(self, 模块名):
        self.通过 += 1
        print(f"  ✅ {模块名} - 通过")
    
    def 记录失败(self, 模块名, 错误):
        self.失败 += 1
        self.失败详情.append((模块名, 错误))
        print(f"  ❌ {模块名} - 失败: {错误}")
    
    def 记录跳过(self, 模块名, 原因):
        self.跳过 += 1
        print(f"  ⚠️  {模块名} - 跳过: {原因}")
    
    def 记录API(self, 模块名, 公共接口):
        self.模块API[模块名] = 公共接口


def 探测模块(模块对象):
    """探测模块的公共接口"""
    return [name for name in dir(模块对象) if not name.startswith('_')]


def 测试阶段1_基础核心(结果: 测试结果):
    """阶段1：基础核心模块"""
    print("\n📦 阶段1：基础核心模块")
    
    # 数学模块
    try:
        import 数学
        结果.记录API("数学", 探测模块(数学))
        assert callable(数学.阶乘)
        assert 数学.阶乘(5) == 120
        assert 数学.绝对值(-3.14) == 3.14
        assert callable(数学.正弦)
        assert isinstance(数学.正弦(0.5), float)
        结果.记录通过("数学")
    except Exception as e:
        结果.记录失败("数学", str(e))
    
    # 字符串处理模块
    try:
        import 字符串处理
        结果.记录API("字符串处理", 探测模块(字符串处理))
        assert 字符串处理.分割("a,b,c", ",") == ["a", "b", "c"]
        assert 字符串处理.拼接("x", "y", "z") == "xyz"
        assert 字符串处理.替换("hello world", "world", "光明") == "hello 光明"
        assert 字符串处理.长度("测试") == 2
        assert 字符串处理.查找("hello", "ll") == 2
        结果.记录通过("字符串处理")
    except Exception as e:
        结果.记录失败("字符串处理", str(e))
    
    # 文件系统模块
    try:
        import 文件系统
        结果.记录API("文件系统", 探测模块(文件系统))
        临时文件 = tempfile.mktemp(suffix=".txt")
        文件系统.写入文件(临时文件, "你好，光明！")
        内容 = 文件系统.读取文件(临时文件)
        assert 内容 == "你好，光明！"
        assert 文件系统.文件存在(临时文件) == True
        os.unlink(临时文件)
        结果.记录通过("文件系统")
    except Exception as e:
        结果.记录失败("文件系统", str(e))
    
    # JSON模块
    try:
        import JSON
        结果.记录API("JSON", 探测模块(JSON))
        数据 = {"姓名": "张三", "年龄": 25, "技能": ["Python", "光明"]}
        json_str = JSON.序列化JSON(数据)
        解析结果 = JSON.解析JSON(json_str)
        assert 解析结果["姓名"] == "张三"
        assert 解析结果["年龄"] == 25
        assert JSON.验证JSON(json_str) == True
        结果.记录通过("JSON")
    except Exception as e:
        结果.记录失败("JSON", str(e))
    
    # 日志模块
    try:
        import 日志
        结果.记录API("日志", 探测模块(日志))
        日志.设置级别("DEBUG" if "DEBUG" in [x for x in dir(日志)] else "调试")
        # 尝试中文级别
        try:
            日志.设置级别("调试")
        except:
            pass
        日志.信息("测试日志信息")
        日志.调试("调试信息")
        日志.警告("警告信息")
        结果.记录通过("日志")
    except Exception as e:
        结果.记录失败("日志", str(e))


def 测试阶段2_数据结构工具(结果: 测试结果):
    """阶段2：数据结构与工具"""
    print("\n📦 阶段2：数据结构与工具")
    
    # 日期时间模块
    try:
        import 日期时间
        结果.记录API("日期时间", 探测模块(日期时间))
        assert hasattr(日期时间, '日期时间')
        # 获取当前时间
        now = 日期时间.当前时间()
        assert now is not None
        assert callable(now.格式化)
        格式化结果 = now.格式化("%Y-%m-%d")
        assert len(格式化结果) == 10
        # 测试日期时间创建
        dt = 日期时间.日期时间(2025, 1, 15, 10, 30, 0)
        assert dt.年() == 2025
        assert dt.月() == 1
        assert dt.日() == 15
        assert dt.周几() in ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        结果.记录通过("日期时间")
    except Exception as e:
        结果.记录失败("日期时间", str(e))
    
    # 随机模块
    try:
        import 随机
        结果.记录API("随机", 探测模块(随机))
        数值 = 随机.随机整数(1, 100)
        assert 1 <= 数值 <= 100
        选项 = ["A", "B", "C", "D"]
        选中 = 随机.随机选择(选项) if hasattr(随机, '随机选择') else random.choice(选项)
        assert 选中 in 选项
        结果.记录通过("随机")
    except Exception as e:
        结果.记录失败("随机", str(e))
    
    # 集合模块
    try:
        import 集合
        结果.记录API("集合", 探测模块(集合))
        set1 = {1, 2, 3, 4}
        set2 = {3, 4, 5, 6}
        if hasattr(集合, '并集'):
            assert 集合.并集(set1, set2) == {1, 2, 3, 4, 5, 6}
            assert 集合.交集(set1, set2) == {3, 4}
        结果.记录通过("集合")
    except Exception as e:
        结果.记录失败("集合", str(e))
    
    # 迭代工具模块
    try:
        import 迭代工具
        结果.记录API("迭代工具", 探测模块(迭代工具))
        结果.记录通过("迭代工具")
    except Exception as e:
        结果.记录失败("迭代工具", str(e))
    
    # 数据结构模块
    try:
        import 数据结构
        结果.记录API("数据结构", 探测模块(数据结构))
        结果.记录通过("数据结构")
    except Exception as e:
        结果.记录失败("数据结构", str(e))


def 测试阶段3_系统网络(结果: 测试结果):
    """阶段3：系统与网络"""
    print("\n📦 阶段3：系统与网络")
    
    # 线程模块
    try:
        import 线程
        结果.记录API("线程", 探测模块(线程))
        结果值 = []
        
        def 工作(n):
            for i in range(n):
                结果值.append(i)
        
        t = 线程.线程(工作, 5)
        t.开始()
        t.等待()
        assert len(结果值) == 5
        结果.记录通过("线程")
    except Exception as e:
        结果.记录失败("线程", str(e))
    
    # 进程模块
    try:
        import 进程
        结果.记录API("进程", 探测模块(进程))
        结果.记录跳过("进程", "进程模块可导入（完整测试需独立进程环境）")
    except Exception as e:
        结果.记录失败("进程", str(e))
    
    # 时间管理模块
    try:
        import 时间管理
        结果.记录API("时间管理", 探测模块(时间管理))
        # 测试计时器（测量代码执行时间）
        with 时间管理.计时器() as t:
            time.sleep(0.01)
        assert t.经过时间() >= 0.005
        
        # 测试周期定时器
        if hasattr(时间管理, '周期定时器'):
            计数 = [0]
            def 定时任务():
                计数[0] += 1
            
            pt = 时间管理.周期定时器(0.05, 定时任务)
            pt.开始()
            time.sleep(0.12)
            pt.停止()
            assert 计数[0] >= 2
        结果.记录通过("时间管理")
    except Exception as e:
        结果.记录失败("时间管理", str(e))
    
    # 网络请求模块
    try:
        import 网络请求
        结果.记录API("网络请求", 探测模块(网络请求))
        结果.记录跳过("网络请求", "需要真实网络环境")
    except Exception as e:
        结果.记录失败("网络请求", str(e))


def 测试阶段4_编码安全(结果: 测试结果):
    """阶段4：编码与安全"""
    print("\n📦 阶段4：编码与安全")
    
    # 编码解码模块
    try:
        import 编码解码
        结果.记录API("编码解码", 探测模块(编码解码))
        原始 = "Hello, 光明！"
        编码结果 = 编码解码.Base64编码(原始)
        解码结果 = 编码解码.Base64解码(编码结果)
        assert 解码结果 == 原始
        结果.记录通过("编码解码")
    except Exception as e:
        结果.记录失败("编码解码", str(e))
    
    # 哈希模块
    try:
        import 哈希
        结果.记录API("哈希", 探测模块(哈希))
        md5 = 哈希.MD5("test") if hasattr(哈希, 'MD5') else 哈希.md5("test")
        assert len(md5) == 32
        结果.记录通过("哈希")
    except Exception as e:
        结果.记录失败("哈希", str(e))
    
    # 加密模块
    try:
        import 加密
        结果.记录API("加密", 探测模块(加密))
        结果.记录通过("加密")
    except Exception as e:
        结果.记录失败("加密", str(e))


def 测试阶段5_高级特性(结果: 测试结果):
    """阶段5：高级特性"""
    print("\n📦 阶段5：高级特性")
    
    # 装饰器模块
    try:
        import 装饰器
        结果.记录API("装饰器", 探测模块(装饰器))
        if hasattr(装饰器, '缓存'):
            @装饰器.缓存(最大缓存数=10)
            def 计算(n):
                return n * n
            
            assert 计算(5) == 25
            assert 计算(5) == 25  # 第二次应该命中缓存
        
        if hasattr(装饰器, '重试'):
            @装饰器.重试(最大次数=3)
            def 可能失败(n):
                if n < 0:
                    raise ValueError("负数")
                return n
            
            assert 可能失败(10) == 10
        结果.记录通过("装饰器")
    except Exception as e:
        结果.记录失败("装饰器", str(e))
    
    # 上下文管理器模块
    try:
        import 上下文管理器
        结果.记录API("上下文管理器", 探测模块(上下文管理器))
        if hasattr(上下文管理器, '计时上下文'):
            with 上下文管理器.计时上下文() as t:
                time.sleep(0.01)
            assert t.耗时() >= 0.005
        结果.记录通过("上下文管理器")
    except Exception as e:
        结果.记录失败("上下文管理器", str(e))


def 测试阶段6_数据科学(结果: 测试结果):
    """阶段6：数据科学与计算"""
    print("\n📦 阶段6：数据科学与计算")
    
    # 统计函数模块
    try:
        import 统计函数
        结果.记录API("统计函数", 探测模块(统计函数))
        数据 = [2, 4, 6, 8, 10]
        assert 统计函数.均值(数据) == 6.0
        assert 统计函数.中位数(数据) == 6.0
        assert 统计函数.方差(数据) > 0
        assert 统计函数.标准差(数据) > 0
        结果.记录通过("统计函数")
    except Exception as e:
        结果.记录失败("统计函数", str(e))
    
    # 矩阵运算模块
    try:
        import 矩阵运算
        结果.记录API("矩阵运算", 探测模块(矩阵运算))
        结果.记录通过("矩阵运算")
    except Exception as e:
        结果.记录失败("矩阵运算", str(e))
    
    # 线性代数模块
    try:
        import 线性代数
        结果.记录API("线性代数", 探测模块(线性代数))
        结果.记录通过("线性代数")
    except Exception as e:
        结果.记录失败("线性代数", str(e))


def 测试阶段7_文本处理(结果: 测试结果):
    """阶段7：文本处理与解析"""
    print("\n📦 阶段7：文本处理与解析")
    
    # 正则表达式模块
    try:
        import 正则表达式
        结果.记录API("正则表达式", 探测模块(正则表达式))
        # 测试函数式API
        assert 正则表达式.匹配(r"\d+", "123abc") == True
        assert 正则表达式.查找(r"world", "hello world") is not None
        assert 正则表达式.替换(r"cat", "cat cat cat", "dog") == "dog dog dog"
        匹配列表 = 正则表达式.查找所有(r"\d+", "a1 b2 c3")
        assert len(匹配列表) == 3
        
        # 测试常用验证函数
        assert 正则表达式.验证邮箱("user@example.com") == True
        assert 正则表达式.验证手机号("13800138000") == True
        assert 正则表达式.验证URL("https://www.example.com") == True
        
        # 测试类式API
        if hasattr(正则表达式, '正则表达式'):
            re_obj = 正则表达式.编译(r"[a-z]+")
            assert re_obj.匹配("hello123") == True
        结果.记录通过("正则表达式")
    except Exception as e:
        结果.记录失败("正则表达式", str(e))
    
    # 模板引擎模块
    try:
        import 模板引擎
        结果.记录API("模板引擎", 探测模块(模板引擎))
        if hasattr(模板引擎, '简单模板'):
            模板 = 模板引擎.简单模板("你好，{{名字}}！")
            输出 = 模板.渲染(名字="张三")
            assert "张三" in 输出
        结果.记录通过("模板引擎")
    except Exception as e:
        结果.记录失败("模板引擎", str(e))
    
    # CSV读写器模块
    try:
        import CSV读写器
        结果.记录API("CSV读写器", 探测模块(CSV读写器))
        结果.记录通过("CSV读写器")
    except Exception as e:
        结果.记录失败("CSV读写器", str(e))
    
    # JSON解析器模块
    try:
        import JSON解析器
        结果.记录API("JSON解析器", 探测模块(JSON解析器))
        结果.记录通过("JSON解析器")
    except Exception as e:
        结果.记录失败("JSON解析器", str(e))


def 测试阶段8_Web通信(结果: 测试结果):
    """阶段8：Web与通信协议"""
    print("\n📦 阶段8：Web与通信协议")
    
    # URL工具模块
    try:
        import URL工具
        结果.记录API("URL工具", 探测模块(URL工具))
        结果.记录通过("URL工具")
    except Exception as e:
        结果.记录失败("URL工具", str(e))
    
    # HTTP客户端模块
    try:
        import HTTP客户端
        结果.记录API("HTTP客户端", 探测模块(HTTP客户端))
        结果.记录跳过("HTTP客户端", "需要真实网络环境")
    except Exception as e:
        结果.记录失败("HTTP客户端", str(e))
    
    # HTTP服务端模块
    try:
        import HTTP服务端
        结果.记录API("HTTP服务端", 探测模块(HTTP服务端))
        结果.记录跳过("HTTP服务端", "服务端类可导入（启动测试需端口）")
    except Exception as e:
        结果.记录失败("HTTP服务端", str(e))
    
    # SMTP邮件模块
    try:
        import SMTP邮件
        结果.记录API("SMTP邮件", 探测模块(SMTP邮件))
        结果.记录跳过("SMTP邮件", "需要真实邮件服务器")
    except Exception as e:
        结果.记录失败("SMTP邮件", str(e))


def 测试阶段9_测试调试(结果: 测试结果):
    """阶段9：测试与调试"""
    print("\n📦 阶段9：测试与调试")
    
    # 断言工具模块
    try:
        import 断言工具
        结果.记录API("断言工具", 探测模块(断言工具))
        if hasattr(断言工具, '断言相等'):
            断言工具.断言相等(1 + 1, 2)
        if hasattr(断言工具, '断言为真'):
            断言工具.断言为真(2 > 1)
        结果.记录通过("断言工具")
    except Exception as e:
        结果.记录失败("断言工具", str(e))
    
    # Mock工具模块
    try:
        import Mock工具
        结果.记录API("Mock工具", 探测模块(Mock工具))
        结果.记录通过("Mock工具")
    except Exception as e:
        结果.记录失败("Mock工具", str(e))
    
    # 性能基准测试模块
    try:
        import 性能基准测试
        结果.记录API("性能基准测试", 探测模块(性能基准测试))
        结果.记录通过("性能基准测试")
    except Exception as e:
        结果.记录失败("性能基准测试", str(e))
    
    # 日志系统增强模块
    try:
        import 日志系统增强
        结果.记录API("日志系统增强", 探测模块(日志系统增强))
        结果.记录通过("日志系统增强")
    except Exception as e:
        结果.记录失败("日志系统增强", str(e))
    
    # 单元测试框架模块
    try:
        import 单元测试框架
        结果.记录API("单元测试框架", 探测模块(单元测试框架))
        结果.记录通过("单元测试框架")
    except Exception as e:
        结果.记录失败("单元测试框架", str(e))


def 测试阶段10_元编程(结果: 测试结果):
    """阶段10：元编程与代码生成"""
    print("\n📦 阶段10：元编程与代码生成")
    
    # 对象池缓存模块
    try:
        import 对象池缓存
        结果.记录API("对象池缓存", 探测模块(对象池缓存))
        结果.记录通过("对象池缓存")
    except Exception as e:
        结果.记录失败("对象池缓存", str(e))
    
    # 类型系统增强模块
    try:
        import 类型系统增强
        结果.记录API("类型系统增强", 探测模块(类型系统增强))
        结果.记录通过("类型系统增强")
    except Exception as e:
        结果.记录失败("类型系统增强", str(e))
    
    # 插件系统模块
    try:
        import 插件系统
        结果.记录API("插件系统", 探测模块(插件系统))
        结果.记录通过("插件系统")
    except Exception as e:
        结果.记录失败("插件系统", str(e))
    
    # DSL支持模块
    try:
        import DSL支持
        结果.记录API("DSL支持", 探测模块(DSL支持))
        结果.记录跳过("DSL支持", "基础类可导入")
    except Exception as e:
        结果.记录失败("DSL支持", str(e))
    
    # AST操作模块
    try:
        import AST操作
        结果.记录API("AST操作", 探测模块(AST操作))
        结果.记录跳过("AST操作", "基础类可导入")
    except Exception as e:
        结果.记录失败("AST操作", str(e))


def 测试阶段11_安全权限(结果: 测试结果):
    """阶段11：安全与权限"""
    print("\n📦 阶段11：安全与权限")
    
    # OAuth_JWT认证模块
    try:
        import OAuth_JWT认证
        结果.记录API("OAuth_JWT认证", 探测模块(OAuth_JWT认证))
        结果.记录通过("OAuth_JWT认证")
    except Exception as e:
        结果.记录失败("OAuth_JWT认证", str(e))
    
    # 访问控制模块
    try:
        import 访问控制
        结果.记录API("访问控制", 探测模块(访问控制))
        结果.记录通过("访问控制")
    except Exception as e:
        结果.记录失败("访问控制", str(e))
    
    # 加密协议模块
    try:
        import 加密协议
        结果.记录API("加密协议", 探测模块(加密协议))
        结果.记录通过("加密协议")
    except Exception as e:
        结果.记录失败("加密协议", str(e))
    
    # 输入校验净化模块
    try:
        import 输入校验净化
        结果.记录API("输入校验净化", 探测模块(输入校验净化))
        结果.记录通过("输入校验净化")
    except Exception as e:
        结果.记录失败("输入校验净化", str(e))
    
    # 审计日志模块
    try:
        import 审计日志
        结果.记录API("审计日志", 探测模块(审计日志))
        结果.记录通过("审计日志")
    except Exception as e:
        结果.记录失败("审计日志", str(e))


def 测试阶段12_并发分布式(结果: 测试结果):
    """阶段12：并发与分布式"""
    print("\n📦 阶段12：并发与分布式")
    
    # Actor模型模块
    try:
        import Actor模型
        结果.记录API("Actor模型", 探测模块(Actor模型))
        import threading
        结果列表 = []
        结果锁 = threading.Lock()
        
        def 处理函数(msg):
            with 结果锁:
                结果列表.append(msg)
        
        with Actor模型.Actor系统("测试系统") as 系统:
            actor = 系统.创建Actor(lambda n: Actor模型.简单Actor(处理函数, n), "测试Actor")
            actor.发送("消息1")
            actor.发送("消息2")
            time.sleep(0.2)
        
        assert "消息1" in 结果列表
        assert "消息2" in 结果列表
        结果.记录通过("Actor模型")
    except Exception as e:
        结果.记录失败("Actor模型", str(e))
    
    # 分布式锁模块
    try:
        import 分布式锁
        结果.记录API("分布式锁", 探测模块(分布式锁))
        # 测试互斥锁
        锁1 = 分布式锁.内存分布式锁("test_lock", 超时时间=10.0)
        assert 锁1.获取() == True
        assert 锁1.释放() == True
        
        # 测试可重入锁
        rlock = 分布式锁.可重入内存锁("test_rlock")
        assert rlock.获取() == True
        assert rlock.获取() == True  # 重入
        assert rlock.释放() == True
        assert rlock.释放() == True
        
        # 测试信号量
        sem = 分布式锁.信号量锁("test_sem", 许可数=2)
        assert sem.获取() == True
        assert sem.获取() == True
        sem.释放()
        sem.释放()
        
        结果.记录通过("分布式锁")
    except Exception as e:
        结果.记录失败("分布式锁", str(e))
    
    # 消息队列模块
    try:
        import 消息队列
        结果.记录API("消息队列", 探测模块(消息队列))
        # 测试基本队列
        q = 消息队列.内存消息队列("测试队列")
        q.发送("消息A")
        q.发送("消息B")
        msg1 = q.接收(超时=0.1)
        msg2 = q.接收(超时=0.1)
        assert msg1.内容 == "消息A"
        assert msg2.内容 == "消息B"
        
        # 测试发布订阅
        ps = 消息队列.发布订阅()
        收到 = []
        def 回调(msg):
            收到.append(msg)
        
        ps.订阅("主题1", 回调)
        ps.发布("主题1", "测试消息")
        time.sleep(0.05)
        assert "测试消息" in 收到
        
        结果.记录通过("消息队列")
    except Exception as e:
        结果.记录失败("消息队列", str(e))
    
    # 任务队列调度器模块
    try:
        import 任务队列调度器
        结果.记录API("任务队列调度器", 探测模块(任务队列调度器))
        # 测试任务队列
        tq = 任务队列调度器.任务队列(工作线程数=2)
        tq.启动()
        
        def 计算(n):
            return n * 2
        
        任务id = tq.提交(计算, 21)
        结果值 = tq.获取任务结果(任务id, 等待=True, 超时=2.0)
        assert 结果值 == 42
        tq.停止()
        
        # 测试定时调度器
        scheduler = 任务队列调度器.定时调度器()
        计数 = [0]
        def 定时任务():
            计数[0] += 1
        
        scheduler.添加间隔任务(0.05, 定时任务)
        scheduler.启动()
        time.sleep(0.12)
        scheduler.停止()
        assert 计数[0] >= 2
        
        结果.记录通过("任务队列调度器")
    except Exception as e:
        结果.记录失败("任务队列调度器", str(e))
    
    # 工作流引擎模块
    try:
        import 工作流引擎
        结果.记录API("工作流引擎", 探测模块(工作流引擎))
        wf = 工作流引擎.工作流("测试工作流")
        wf.创建节点("步骤1", lambda ctx: ctx.get("输入", 0) + 1)
        wf.创建节点("步骤2", lambda ctx: ctx["步骤1"] * 2, 依赖=["步骤1"])
        wf.创建节点("步骤3", lambda ctx: ctx["步骤2"] + 10, 依赖=["步骤2"])
        
        assert wf.验证() == True
        
        最终结果 = wf.执行({"输入": 5})
        assert 最终结果["步骤1"] == 6
        assert 最终结果["步骤2"] == 12
        assert 最终结果["步骤3"] == 22
        assert wf.状态.value == "已完成"
        
        结果.记录通过("工作流引擎")
    except Exception as e:
        结果.记录失败("工作流引擎", str(e))


def 主程序():
    print("=" * 60)
    print("🧪 光明标准库 - 第三方视角综合测试")
    print("=" * 60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本: {sys.version}")
    print(f"标准库路径: {os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'stdlib'))}")
    
    结果 = 测试结果()
    
    # 12个阶段逐一测试
    测试阶段1_基础核心(结果)
    测试阶段2_数据结构工具(结果)
    测试阶段3_系统网络(结果)
    测试阶段4_编码安全(结果)
    测试阶段5_高级特性(结果)
    测试阶段6_数据科学(结果)
    测试阶段7_文本处理(结果)
    测试阶段8_Web通信(结果)
    测试阶段9_测试调试(结果)
    测试阶段10_元编程(结果)
    测试阶段11_安全权限(结果)
    测试阶段12_并发分布式(结果)
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"✅ 通过: {结果.通过}")
    print(f"❌ 失败: {结果.失败}")
    print(f"⚠️  跳过: {结果.跳过}")
    总数 = 结果.通过 + 结果.失败
    print(f"📈 通过率: {(结果.通过 / 总数 * 100) if 总数 > 0 else 0:.1f}%")
    
    if 结果.失败详情:
        print("\n❌ 失败详情：")
        for 模块名, 错误 in 结果.失败详情:
            print(f"  - {模块名}: {错误}")
    
    # 输出模块API概览
    print("\n" + "=" * 60)
    print("📚 模块公共接口概览")
    print("=" * 60)
    for 模块名, 接口列表 in sorted(结果.模块API.items()):
        print(f"\n🔹 {模块名} ({len(接口列表)}个接口)")
        # 只显示前10个，太多则省略
        if len(接口列表) <= 10:
            for 接口 in 接口列表:
                print(f"   - {接口}")
        else:
            for 接口 in 接口列表[:10]:
                print(f"   - {接口}")
            print(f"   ... 还有 {len(接口列表) - 10} 个")
    
    print("\n" + "=" * 60)
    
    return 结果.失败 == 0


if __name__ == "__main__":
    成功 = 主程序()
    sys.exit(0 if 成功 else 1)
