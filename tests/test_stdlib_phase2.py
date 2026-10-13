"""
光明标准库第二阶段测试用例

测试日期时间、随机、集合、迭代工具、数据结构模块

R146-D 线（v0.4.x）：本文件对「纯光明实现」模块（`集合` / `数据结构`）统一经
`stdlib/_light_import_hook.py` 加载同名 `.light`，不再依赖同名 `.py` 兜底。

背景（缺陷账 L-205）：R144 删 `stdlib/集合.py` 影子后仅存 `集合.light`，而本文件
原先只做 `sys.path.insert` + 裸 `from 集合 import ...`，CPython 不解析 `.light`
→ 4 条 TestSet 报 `ModuleNotFoundError`（先于 R145 存在的预存红，已用 HEAD 净舱
worktree 复跑实证，见 `_R146_D线交付报告.md`）。

口径同 `tests/test_agent_loop_light.py` / `tests/test_async_io_light.py`：
先挂 `_light_import_hook`，再由钩子按「`.light` 首两行含「纯光明实现」魔数」
规则决定遮蔽同名 `.py`。本文件涉及的 5 个模块中，只有 `集合`、`数据结构`
带该魔数会被钩子接管；`日期时间` / `随机`（无魔数，有 `.py`）、`迭代工具`
（无同名 `.light`）仍走标准机制，行为不变。
"""

import os
import sys
import unittest

# 用绝对路径（而非 '../stdlib'）：pytest 的工作目录不保证是 tests/，
# 相对路径在不同 rootdir 下会指错地方。
_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'stdlib')
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)

# 挂上光明导入钩子：让 `import 集合` / `import 数据结构` 能解析到同名 `.light`。
import _light_import_hook  # noqa: E402
_light_import_hook.install([_STDLIB])


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
    """测试集合模块

    R146-D 线（v0.4.x）口径变更说明
    ------------------------------
    本组用例原先直接拿 Python 原生 `set` 当集合值（`s1 = {1, 2}`），并断言
    `并集(s1, s2) == {1,2,3,4,5}`。那是 **R144 删掉的 `stdlib/集合.py`** 的语义。

    现真身是 `stdlib/集合.light`（首两行带「纯光明实现」魔数，经本文件顶部的
    `_light_import_hook` 加载）。它为了照顾「原生腿无 set 类型」，内部用
    **「字典 + 列表」表示集合**：`创建集合([1,2,3])` → `{'元素': [1, 2, 3]}`。
    因此：

    - 集合值**必须经 `创建集合(...)` 构造**，不能塞 Python 原生 `set`
      （`集合_列表` 会去 `字典获取(集合, "元素")`，原生 set 会抛 TypeError）；
    - 运算结果**经 `集合转列表` 取内容**再与期望列表比（这是真身的公开 API，
      不是自比自：`集合转列表` 只做读取，元素内容由 `并集/交集/...` 决定）；
    - `杰卡德相似度` 返回**整数指纹（值 × 2^53）**而非 [0,1] 浮点——口径与
      `tests/unit/test_原生腿_T5C_集合随机.py` 的「已知边界」一致；
    - `集合的唯一元素` / `集合的重复元素` 收列表、返回**去重后的列表**
      （旧 `.py` 返回 Python `set`）。

    该表示差异已作为独立候选缺陷登记（见 `tests/ci_environment_reds.txt`），
    交主 agent 统一编号；本文件只负责让测试如实钉住**当前真身**的行为。
    """

    def test_set_operations(self):
        """测试集合运算"""
        from 集合 import 创建集合, 并集, 交集, 差集, 对称差, 集合转列表

        s1 = 创建集合([1, 2, 3])
        s2 = 创建集合([3, 4, 5])

        self.assertEqual(sorted(集合转列表(并集(s1, s2))), [1, 2, 3, 4, 5])
        self.assertEqual(sorted(集合转列表(交集(s1, s2))), [3])
        self.assertEqual(sorted(集合转列表(差集(s1, s2))), [1, 2])
        self.assertEqual(sorted(集合转列表(对称差(s1, s2))), [1, 2, 4, 5])

    def test_set_relations(self):
        """测试集合关系"""
        from 集合 import 创建集合, 是否子集, 是否真子集, 是否不相交

        s1 = 创建集合([1, 2])
        s2 = 创建集合([1, 2, 3])
        s3 = 创建集合([4, 5])

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
        from 集合 import 创建集合, 杰卡德相似度, 集合的唯一元素, 集合的重复元素

        s1 = 创建集合([1, 2, 3])
        s2 = 创建集合([2, 3, 4])

        # 杰卡德相似度 = |交| / |并| = 2/4 = 0.5；真身以「值 × 2^53」整数指纹返回。
        sim = 杰卡德相似度(s1, s2) / (2 ** 53)
        self.assertAlmostEqual(sim, 0.5, places=9)
        self.assertGreaterEqual(sim, 0)
        self.assertLessEqual(sim, 1)

        lst = [1, 2, 2, 3, 3, 3]
        # 真身返回去重后的列表（旧 .py 返回 Python set）。
        self.assertEqual(sorted(集合的唯一元素(lst)), [1, 2, 3])
        self.assertEqual(sorted(集合的重复元素(lst)), [2, 3])


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
        """测试栈（函数式 API）"""
        from 数据结构 import 创建栈, 压入, 弹出元素, 顶部, 栈大小
        
        s = 创建栈()
        压入(s, 1)
        压入(s, 2)
        压入(s, 3)
        
        self.assertEqual(栈大小(s), 3)
        self.assertEqual(弹出元素(s), 3)
        self.assertEqual(顶部(s), 2)
        self.assertEqual(栈大小(s), 2)

    def test_queue(self):
        """测试队列（函数式 API）"""
        from 数据结构 import 创建队列, 入队, 出队元素, 队首, 队列大小
        
        q = 创建队列()
        入队(q, 1)
        入队(q, 2)
        入队(q, 3)
        
        self.assertEqual(队列大小(q), 3)
        self.assertEqual(出队元素(q), 1)
        self.assertEqual(队首(q), 2)
        self.assertEqual(队列大小(q), 2)

    def test_deque(self):
        """测试双端队列（函数式 API）"""
        from 数据结构 import 创建双端队列, 左入队, 右入队, 左出队元素, 右出队元素, 双端队列大小
        
        dq = 创建双端队列()
        dq = 左入队(dq, 1)
        dq = 右入队(dq, 2)
        
        self.assertEqual(双端队列大小(dq), 2)
        self.assertEqual(左出队元素(dq), 1)
        self.assertEqual(右出队元素(dq), 2)

    def test_priority_queue(self):
        """测试优先队列（函数式 API）"""
        from 数据结构 import 创建优先队列, 优先入队, 优先出队元素, 优先队列大小
        
        pq = 创建优先队列()
        优先入队(pq, 'low', 3)
        优先入队(pq, 'high', 1)
        优先入队(pq, 'medium', 2)
        
        self.assertEqual(优先队列大小(pq), 3)
        self.assertEqual(优先出队元素(pq), 'high')
        self.assertEqual(优先出队元素(pq), 'medium')

    def test_linked_list(self):
        """测试单链表（函数式 API）"""
        from 数据结构 import 创建链表, 尾部插入, 头部插入, 链表大小, 链表获取, 链表查找, 删除指定值
        
        ll = 创建链表()
        ll = 尾部插入(ll, 1)
        ll = 尾部插入(ll, 2)
        ll = 头部插入(ll, 0)
        
        self.assertEqual(链表大小(ll), 3)
        self.assertEqual(链表获取(ll, 0), 0)
        self.assertEqual(链表查找(ll, 2), 2)
        
        ll = 删除指定值(ll, 1)
        self.assertEqual(链表大小(ll), 2)

    def test_binary_search_tree(self):
        """测试二叉搜索树（函数式 API）"""
        from 数据结构 import 创建二叉搜索树, 二叉插入, 二叉查找, 二叉中序遍历, 二叉删除
        
        bst = 创建二叉搜索树()
        二叉插入(bst, 5)
        二叉插入(bst, 3)
        二叉插入(bst, 7)
        二叉插入(bst, 2)
        二叉插入(bst, 4)
        
        self.assertTrue(二叉查找(bst, 5))
        self.assertTrue(二叉查找(bst, 3))
        self.assertFalse(二叉查找(bst, 10))
        
        inorder = 二叉中序遍历(bst)
        self.assertEqual(inorder, [2, 3, 4, 5, 7])
        
        二叉删除(bst, 3)
        self.assertFalse(二叉查找(bst, 3))


class TestLightImportHook(unittest.TestCase):
    """R146-D：钉住「纯光明模块经 `_light_import_hook` 加载同名 `.light`」。

    `__light_source__` 由 `stdlib/_light_import_hook.py` 的 `LightLoader` 写入，
    只有真正走了 `.light` 才存在。B 线删掉 `stdlib/数据结构.py` 之后，本条能立刻
    发现「钩子没接住 → 掉回 `.py` 或直接 `ModuleNotFoundError`」，
    是 L-205 类断点的回归哨。
    """

    def test_纯光明真身经钩子加载(self):
        import 集合
        import 数据结构
        for 模块 in (集合, 数据结构):
            self.assertTrue(
                str(getattr(模块, '__light_source__', '')).endswith('.light'),
                '{} 未走 .light 真身（__file__={}）'.format(
                    模块.__name__, getattr(模块, '__file__', None)
                ),
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)