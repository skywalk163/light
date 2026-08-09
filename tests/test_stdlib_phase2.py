"""
光明标准库第二阶段测试用例

测试日期时间、随机、集合、迭代工具、数据结构模块
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'stdlib'))


class TestDateTime(unittest.TestCase):
    """测试日期时间模块"""

    def test_basic_functions(self):
        """测试基础函数"""
        from 日期时间 import 当前时间, 当前日期, 当前时间戳, 当前时间戳毫秒
        from 日期时间 import 时间戳转字符串, 日期时间转字符串
        
        dt = 当前时间()
        self.assertIsNotNone(dt)
        
        d = 当前日期()
        self.assertIsNotNone(d)
        
        ts = 当前时间戳()
        self.assertIsInstance(ts, float)
        
        ts_ms = 当前时间戳毫秒()
        self.assertIsInstance(ts_ms, int)
        
        s = 时间戳转字符串(ts)
        self.assertIsInstance(s, str)
        
        s2 = 日期时间转字符串(dt)
        self.assertIsInstance(s2, str)

    def test_parse_format(self):
        """测试解析和格式化"""
        from 日期时间 import 字符串转日期时间, 字符串转日期, 字符串转时间
        
        dt = 字符串转日期时间('2024-01-01 12:00:00')
        self.assertEqual(dt.year, 2024)
        
        d = 字符串转日期('2024-01-01')
        self.assertEqual(d.year, 2024)
        
        t = 字符串转时间('12:00:00')
        self.assertEqual(t.hour, 12)

    def test_date_components(self):
        """测试日期组件"""
        from 日期时间 import 获取年份, 获取月份, 获取日, 获取星期几名称
        
        from datetime import datetime
        dt = datetime(2024, 5, 20)
        
        self.assertEqual(获取年份(dt), 2024)
        self.assertEqual(获取月份(dt), 5)
        self.assertEqual(获取日(dt), 20)
        self.assertIn(获取星期几名称(dt), ['周一', '周二', '周三', '周四', '周五', '周六', '周日'])

    def test_leap_year(self):
        """测试闰年判断"""
        from 日期时间 import 是否闰年
        
        self.assertTrue(是否闰年(2024))
        self.assertFalse(是否闰年(2023))
        self.assertTrue(是否闰年(2000))
        self.assertFalse(是否闰年(1900))

    def test_date_arithmetic(self):
        """测试日期运算"""
        from 日期时间 import 添加天数, 时间差天数, 日期比较
        
        from datetime import datetime
        dt = datetime(2024, 1, 1)
        dt2 = 添加天数(dt, 1)
        
        self.assertEqual(dt2.day, 2)
        self.assertEqual(时间差天数(dt, dt2), 1)
        self.assertEqual(日期比较(dt, dt2), -1)

    def test_relative_time(self):
        """测试相对时间"""
        from 日期时间 import 获取相对时间描述
        
        from datetime import datetime, timedelta
        dt = datetime.now() - timedelta(minutes=30)
        desc = 获取相对时间描述(dt)
        self.assertIn('分钟前', desc)


class TestRandom(unittest.TestCase):
    """测试随机模块"""

    def test_basic_random(self):
        """测试基础随机函数"""
        from 随机 import 设置随机种子, 随机整数, 随机浮点数, 随机0到1, 随机布尔
        
        设置随机种子(42)
        
        n = 随机整数(1, 100)
        self.assertGreaterEqual(n, 1)
        self.assertLessEqual(n, 100)
        
        f = 随机浮点数(0, 1)
        self.assertGreaterEqual(f, 0)
        self.assertLess(f, 1)
        
        f2 = 随机0到1()
        self.assertGreaterEqual(f2, 0)
        self.assertLess(f2, 1)
        
        b = 随机布尔()
        self.assertIsInstance(b, bool)

    def test_random_choice(self):
        """测试随机选择"""
        from 随机 import 设置随机种子, 随机选择, 随机选择多个, 随机采样, 随机打乱, 随机打乱副本
        
        设置随机种子(42)
        
        lst = [1, 2, 3, 4, 5]
        
        item = 随机选择(lst)
        self.assertIn(item, lst)
        
        items = 随机选择多个(lst, 3)
        self.assertEqual(len(items), 3)
        
        sample = 随机采样(lst, 3)
        self.assertEqual(len(sample), 3)
        self.assertEqual(len(set(sample)), 3)
        
        shuffled = 随机打乱副本(lst)
        self.assertEqual(len(shuffled), len(lst))

    def test_random_strings(self):
        """测试随机字符串"""
        from 随机 import 设置随机种子, 随机字符串, 随机字母数字, 随机UUID
        
        设置随机种子(42)
        
        s = 随机字符串(10)
        self.assertEqual(len(s), 10)
        
        c = 随机字母数字()
        self.assertIsInstance(c, str)
        
        uid = 随机UUID()
        self.assertEqual(len(uid), 36)

    def test_weighted_choice(self):
        """测试权重选择"""
        from 随机 import 设置随机种子, 随机权重选择
        
        设置随机种子(42)
        
        items = ['a', 'b', 'c']
        weights = [1, 1, 1]
        
        result = 随机权重选择(items, weights)
        self.assertIn(result, items)


class TestSet(unittest.TestCase):
    """测试集合模块"""

    def test_set_operations(self):
        """测试集合运算"""
        from 集合 import 创建集合, 并集, 交集, 差集, 对称差
        
        s1 = 创建集合([1, 2, 3])
        s2 = 创建集合([3, 4, 5])
        
        self.assertEqual(并集(s1, s2), {1, 2, 3, 4, 5})
        self.assertEqual(交集(s1, s2), {3})
        self.assertEqual(差集(s1, s2), {1, 2})
        self.assertEqual(对称差(s1, s2), {1, 2, 4, 5})

    def test_set_relations(self):
        """测试集合关系"""
        from 集合 import 是否子集, 是否真子集, 是否不相交
        
        s1 = {1, 2}
        s2 = {1, 2, 3}
        s3 = {4, 5}
        
        self.assertTrue(是否子集(s1, s2))
        self.assertTrue(是否真子集(s1, s2))
        self.assertTrue(是否不相交(s1, s3))

    def test_set_operations_methods(self):
        """测试集合操作方法"""
        from 集合 import 创建集合, 添加元素, 移除元素, 集合长度, 集合包含
        
        s = 创建集合([1, 2, 3])
        
        添加元素(s, 4)
        self.assertEqual(集合长度(s), 4)
        
        self.assertTrue(集合包含(s, 4))
        
        移除元素(s, 4)
        self.assertEqual(集合长度(s), 3)

    def test_set_utilities(self):
        """测试集合工具函数"""
        from 集合 import 杰卡德相似度, 集合的唯一元素, 集合的重复元素
        
        s1 = {1, 2, 3}
        s2 = {2, 3, 4}
        
        sim = 杰卡德相似度(s1, s2)
        self.assertGreaterEqual(sim, 0)
        self.assertLessEqual(sim, 1)
        
        lst = [1, 2, 2, 3, 3, 3]
        unique = 集合的唯一元素(lst)
        self.assertEqual(unique, {1, 2, 3})
        
        duplicates = 集合的重复元素(lst)
        self.assertEqual(duplicates, {2, 3})


class TestIterTools(unittest.TestCase):
    """测试迭代工具模块"""

    def test_counter(self):
        """测试计数器"""
        from 迭代工具 import 计数器
        
        lst = ['a', 'b', 'a', 'c', 'b', 'a']
        cnt = 计数器(lst)
        
        self.assertEqual(cnt['a'], 3)
        self.assertEqual(cnt['b'], 2)

    def test_grouping(self):
        """测试分组"""
        from 迭代工具 import 分组
        
        lst = [1, 2, 3, 4, 5, 6]
        groups = 分组(lst, lambda x: x % 2)
        
        self.assertEqual(len(groups[0]), 3)
        self.assertEqual(len(groups[1]), 3)

    def test_permutations_combinations(self):
        """测试排列组合"""
        from 迭代工具 import 排列, 组合, 笛卡尔积
        
        lst = [1, 2, 3]
        
        perms = 排列(lst, 2)
        self.assertEqual(len(perms), 6)
        
        combs = 组合(lst, 2)
        self.assertEqual(len(combs), 3)
        
        prod = 笛卡尔积(lst, [4, 5])
        self.assertEqual(len(prod), 6)

    def test_accumulate(self):
        """测试累积计算"""
        from 迭代工具 import 累积和, 累积积
        
        lst = [1, 2, 3, 4]
        
        sums = 累积和(lst)
        self.assertEqual(sums, [1, 3, 6, 10])
        
        prods = 累积积(lst)
        self.assertEqual(prods, [1, 2, 6, 24])

    def test_sliding_window(self):
        """测试滑动窗口"""
        from 迭代工具 import 滑动窗口到列表
        
        lst = [1, 2, 3, 4, 5]
        
        windows = 滑动窗口到列表(lst, 3)
        self.assertEqual(len(windows), 3)


class TestDataStructures(unittest.TestCase):
    """测试数据结构模块"""

    def test_stack(self):
        """测试栈"""
        from 数据结构 import 栈
        
        s = 栈()
        s.压入(1)
        s.压入(2)
        s.压入(3)
        
        self.assertEqual(s.大小(), 3)
        self.assertEqual(s.弹出(), 3)
        self.assertEqual(s.顶部(), 2)
        self.assertEqual(s.大小(), 2)

    def test_queue(self):
        """测试队列"""
        from 数据结构 import 队列
        
        q = 队列()
        q.入队(1)
        q.入队(2)
        q.入队(3)
        
        self.assertEqual(q.大小(), 3)
        self.assertEqual(q.出队(), 1)
        self.assertEqual(q.队首(), 2)
        self.assertEqual(q.大小(), 2)

    def test_deque(self):
        """测试双端队列"""
        from 数据结构 import 双端队列
        
        dq = 双端队列()
        dq.左入队(1)
        dq.右入队(2)
        
        self.assertEqual(dq.大小(), 2)
        self.assertEqual(dq.左出队(), 1)
        self.assertEqual(dq.右出队(), 2)

    def test_priority_queue(self):
        """测试优先队列"""
        from 数据结构 import 优先队列
        
        pq = 优先队列()
        pq.入队(3, 'low')
        pq.入队(1, 'high')
        pq.入队(2, 'medium')
        
        self.assertEqual(pq.大小(), 3)
        self.assertEqual(pq.出队(), 'high')
        self.assertEqual(pq.出队(), 'medium')

    def test_linked_list(self):
        """测试单链表"""
        from 数据结构 import 单链表
        
        ll = 单链表()
        ll.尾部插入(1)
        ll.尾部插入(2)
        ll.头部插入(0)
        
        self.assertEqual(ll.大小(), 3)
        self.assertEqual(ll.获取(0), 0)
        self.assertEqual(ll.查找(2), 2)
        
        ll.删除指定值(1)
        self.assertEqual(ll.大小(), 2)

    def test_binary_search_tree(self):
        """测试二叉搜索树"""
        from 数据结构 import 二叉搜索树
        
        bst = 二叉搜索树()
        bst.插入(5)
        bst.插入(3)
        bst.插入(7)
        bst.插入(2)
        bst.插入(4)
        
        self.assertTrue(bst.查找(5))
        self.assertTrue(bst.查找(3))
        self.assertFalse(bst.查找(10))
        
        inorder = bst.中序遍历()
        self.assertEqual(inorder, [2, 3, 4, 5, 7])
        
        bst.删除(3)
        self.assertFalse(bst.查找(3))


if __name__ == '__main__':
    unittest.main(verbosity=2)