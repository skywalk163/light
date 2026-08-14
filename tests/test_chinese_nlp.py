"""
中文 NLP 模块测试用例

测试 中文NLP 模块的六大功能：
1. 分词
2. 拼音转换
3. 简繁转换
4. 文本统计
5. 数字与金额转换
6. 文本处理工具

注意：本模块无外部依赖时也能运行，部分功能使用内置回退实现。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from stdlib.中文NLP import (
    # 分词
    分词精确模式, 分词全模式, 分词搜索引擎模式,
    词性标注, 提取关键词TFIDF, 提取关键词TextRank,
    分词带位置, 添加自定义词语, 删除自定义词语,
    # 拼音
    转拼音, 转拼音带声调, 转拼音声调数字,
    转拼音首字母, 转拼音列表, 转拼音姓氏,
    # 简繁
    简转繁, 繁转简, 简转繁台湾, 简转繁香港,
    # 文本统计
    统计字符, 统计词频, 统计句子数, 统计段落数,
    可读性评分, 语言检测,
    # 数字与金额
    数字转中文, 中文转数字, 金额转大写,
    百分比转中文, 中文转百分比,
    # 文本处理工具
    去除空白, 去除标点, 提取汉字, 提取英文, 提取数字,
    判断中英混合,
    文本相似度Jaccard, 文本相似度余弦,
    敏感词过滤器,
)


class 测试分词模块(unittest.TestCase):
    """测试分词功能"""

    def test_分词精确模式_中文(self):
        """测试中文精确模式分词"""
        result = 分词精确模式('我爱北京天安门')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_分词精确模式_空文本(self):
        """测试空文本"""
        self.assertEqual(分词精确模式(''), [])

    def test_分词精确模式_混合文本(self):
        """测试中英文混合文本"""
        result = 分词精确模式('hello世界')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_分词全模式(self):
        """测试全模式分词"""
        result = 分词全模式('中华人民共和国')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_分词搜索引擎模式(self):
        """测试搜索引擎模式分词"""
        result = 分词搜索引擎模式('北京天安门')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_词性标注(self):
        """测试词性标注"""
        result = 词性标注('我爱北京')
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_提取关键词TFIDF(self):
        """测试 TF-IDF 关键词提取"""
        text = '北京是中国的首都，北京有故宫和天安门。'
        result = 提取关键词TFIDF(text, 数量=3)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) <= 3)

    def test_提取关键词TextRank(self):
        """测试 TextRank 关键词提取"""
        text = '自然语言处理是人工智能的一个重要方向。'
        result = 提取关键词TextRank(text, 数量=3)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) <= 3)

    def test_分词带位置(self):
        """测试分词带位置信息"""
        text = '我爱北京天安门'
        result = 分词带位置(text)
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 3)
            # 验证位置信息
            word, start, end = item
            self.assertEqual(text[start:end], word)

    def test_添加删除自定义词语(self):
        """测试添加和删除自定义词语"""
        添加自定义词语('测试段言', 词频=100, 词性='n')
        # 删除自定义词语
        删除自定义词语('测试段言')

    def test_分词精确模式_英文(self):
        """测试英文文本"""
        result = 分词精确模式('hello world')
        self.assertIsInstance(result, list)


class 测试拼音模块(unittest.TestCase):
    """测试拼音转换功能"""

    def test_转拼音_中文(self):
        """测试中文转拼音"""
        result = 转拼音('中国')
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_转拼音_空文本(self):
        """测试空文本"""
        self.assertEqual(转拼音(''), '')

    def test_转拼音带声调(self):
        """测试带声调拼音"""
        result = 转拼音带声调('你好')
        self.assertIsInstance(result, str)

    def test_转拼音声调数字(self):
        """测试声调数字拼音"""
        result = 转拼音声调数字('你好')
        self.assertIsInstance(result, str)

    def test_转拼音首字母(self):
        """测试拼音首字母"""
        result = 转拼音首字母('中国')
        self.assertIsInstance(result, str)

    def test_转拼音列表(self):
        """测试拼音列表"""
        result = 转拼音列表('中国')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_转拼音列表_带声调(self):
        """测试带声调拼音列表"""
        result = 转拼音列表('中国', 带声调=True)
        self.assertIsInstance(result, list)

    def test_转拼音姓氏(self):
        """测试姓氏拼音"""
        result = 转拼音姓氏('张三')
        self.assertIsInstance(result, str)

    def test_转拼音_分隔符(self):
        """测试自定义分隔符"""
        result = 转拼音('中国', 分隔符='-')
        self.assertIsInstance(result, str)

    def test_转拼音_首字母模式(self):
        """测试首字母模式"""
        result = 转拼音('中国', 首字母=True)
        self.assertIsInstance(result, str)


class 测试简繁转换模块(unittest.TestCase):
    """测试简繁转换功能"""

    def test_简转繁(self):
        """测试简体转繁体"""
        result = 简转繁('中国')
        self.assertIsInstance(result, str)
        # 简体 '国' 转繁体 '國'
        self.assertIn('國', result)

    def test_繁转简(self):
        """测试繁体转简体"""
        result = 繁转简('中國')
        self.assertIsInstance(result, str)
        self.assertIn('国', result)

    def test_简转繁_空文本(self):
        """测试空文本"""
        self.assertEqual(简转繁(''), '')

    def test_繁转简_空文本(self):
        """测试空文本"""
        self.assertEqual(繁转简(''), '')

    def test_简转繁_循环(self):
        """测试简繁互转一致性"""
        simplified = '中华人民共和国'
        traditional = 简转繁(simplified)
        back = 繁转简(traditional)
        self.assertEqual(simplified, back)

    def test_简转繁台湾(self):
        """测试简体转台湾繁体"""
        result = 简转繁台湾('中国')
        self.assertIsInstance(result, str)

    def test_简转繁香港(self):
        """测试简体转香港繁体"""
        result = 简转繁香港('中国')
        self.assertIsInstance(result, str)


class 测试文本统计模块(unittest.TestCase):
    """测试文本统计功能"""

    def test_统计字符(self):
        """测试字符统计"""
        result = 统计字符('Hello 世界！123')
        self.assertIsInstance(result, dict)
        self.assertIn('总字符数', result)
        self.assertIn('汉字数', result)
        self.assertIn('英文字母数', result)
        self.assertIn('数字数', result)
        self.assertEqual(result['汉字数'], 2)
        self.assertEqual(result['英文字母数'], 5)
        self.assertEqual(result['数字数'], 3)

    def test_统计字符_空文本(self):
        """测试空文本"""
        result = 统计字符('')
        self.assertEqual(result['总字符数'], 0)

    def test_统计词频(self):
        """测试词频统计"""
        result = 统计词频('中国中国北京', 数量=2)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) <= 2)

    def test_统计词频_过滤停用词(self):
        """测试过滤停用词"""
        result = 统计词频('的的的北京', 数量=5, 过滤停用词=True)
        self.assertIsInstance(result, list)

    def test_统计句子数(self):
        """测试句子数统计"""
        self.assertEqual(统计句子数('你好。世界！'), 2)
        self.assertEqual(统计句子数(''), 0)

    def test_统计段落数(self):
        """测试段落数统计"""
        self.assertEqual(统计段落数('第一段\n第二段\n第三段'), 3)
        self.assertEqual(统计段落数(''), 0)

    def test_可读性评分(self):
        """测试可读性评分"""
        score = 可读性评分('今天天气很好。我们一起去公园玩。')
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_可读性评分_空文本(self):
        """测试空文本"""
        self.assertEqual(可读性评分(''), 0.0)

    def test_语言检测_中文(self):
        """测试中文检测"""
        self.assertEqual(语言检测('你好世界'), '中文')

    def test_语言检测_英文(self):
        """测试英文检测"""
        self.assertEqual(语言检测('Hello World'), '英文')

    def test_语言检测_混合(self):
        """测试中英混合检测"""
        result = 语言检测('Hello 世界')
        self.assertIn(result, ['中英混合', '中文', '英文'])

    def test_语言检测_空文本(self):
        """测试空文本"""
        self.assertEqual(语言检测(''), '其他')


class 测试数字金额模块(unittest.TestCase):
    """测试数字与金额转换功能"""

    def test_数字转中文_整数(self):
        """测试整数转中文"""
        self.assertEqual(数字转中文(123), '一百二十三')
        self.assertEqual(数字转中文(0), '零')
        self.assertEqual(数字转中文(10), '十')

    def test_数字转中文_大写(self):
        """测试大写数字"""
        result = 数字转中文(123, 大写=True)
        self.assertIn('壹', result)
        self.assertIn('贰', result)
        self.assertIn('叁', result)

    def test_数字转中文_负数(self):
        """测试负数"""
        result = 数字转中文(-5)
        self.assertTrue(result.startswith('负'))

    def test_数字转中文_浮点数(self):
        """测试浮点数"""
        result = 数字转中文(3.14)
        self.assertIsInstance(result, str)
        self.assertIn('点', result)

    def test_中文转数字(self):
        """测试中文转数字"""
        self.assertEqual(中文转数字('一百二十三'), 123)
        self.assertEqual(中文转数字('十'), 10)
        self.assertEqual(中文转数字('零'), 0)

    def test_中文转数字_负数(self):
        """测试负数的中文转数字"""
        self.assertEqual(中文转数字('负五'), -5)

    def test_金额转大写(self):
        """测试金额转大写"""
        result = 金额转大写(1234.56)
        self.assertIsInstance(result, str)
        self.assertIn('壹仟', result)
        self.assertIn('元', result)
        self.assertIn('角', result)
        self.assertIn('分', result)

    def test_金额转大写_整数(self):
        """测试整数金额"""
        result = 金额转大写(100)
        self.assertIn('整', result)

    def test_金额转大写_零(self):
        """测试零金额"""
        self.assertEqual(金额转大写(0), '零元整')

    def test_金额转大写_负数(self):
        """测试负金额"""
        result = 金额转大写(-100)
        self.assertTrue(result.startswith('负'))

    def test_百分比转中文(self):
        """测试百分比转中文"""
        result = 百分比转中文(0.1234)
        self.assertIn('%', result)

    def test_中文转百分比_百分号(self):
        """测试百分号格式"""
        self.assertAlmostEqual(中文转百分比('12.34%'), 0.1234)

    def test_中文转百分比_中文格式(self):
        """测试中文百分比格式"""
        result = 中文转百分比('百分之十二')
        self.assertAlmostEqual(result, 0.12)


class 测试文本处理工具模块(unittest.TestCase):
    """测试文本处理工具功能"""

    def test_去除空白(self):
        """测试去除空白"""
        self.assertEqual(去除空白(' 你 好 '), '你好')

    def test_去除标点(self):
        """测试去除标点"""
        result = 去除标点('你好，世界！')
        self.assertIn('你好', result)
        self.assertIn('世界', result)

    def test_提取汉字(self):
        """测试提取汉字"""
        self.assertEqual(提取汉字('Hello 世界！'), '世界')

    def test_提取汉字_空文本(self):
        """测试空文本"""
        self.assertEqual(提取汉字(''), '')

    def test_提取英文(self):
        """测试提取英文"""
        self.assertEqual(提取英文('Hello 世界'), 'Hello')

    def test_提取数字(self):
        """测试提取数字"""
        self.assertEqual(提取数字('abc123def456'), '123456')

    def test_判断中英混合_混合(self):
        """测试中英混合判断"""
        self.assertTrue(判断中英混合('Hello 世界'))

    def test_判断中英混合_纯中文(self):
        """测试纯中文"""
        self.assertFalse(判断中英混合('你好世界'))

    def test_判断中英混合_纯英文(self):
        """测试纯英文"""
        self.assertFalse(判断中英混合('Hello'))

    def test_判断中英混合_空文本(self):
        """测试空文本"""
        self.assertFalse(判断中英混合(''))

    def test_文本相似度Jaccard_相同(self):
        """测试完全相同文本"""
        self.assertEqual(文本相似度Jaccard('你好', '你好'), 1.0)

    def test_文本相似度Jaccard_不同(self):
        """测试完全不同文本"""
        self.assertEqual(文本相似度Jaccard('你好', '再见'), 0.0)

    def test_文本相似度Jaccard_部分(self):
        """测试部分相似"""
        sim = 文本相似度Jaccard('你好', '你好吗')
        self.assertGreater(sim, 0)
        self.assertLess(sim, 1.0)

    def test_文本相似度Jaccard_空文本(self):
        """测试空文本"""
        self.assertEqual(文本相似度Jaccard('', ''), 1.0)

    def test_文本相似度余弦_相同(self):
        """测试完全相同文本"""
        self.assertAlmostEqual(文本相似度余弦('你好世界', '你好世界'), 1.0)

    def test_文本相似度余弦_不同(self):
        """测试完全不同文本"""
        sim = 文本相似度余弦('你好', '再见')
        self.assertGreaterEqual(sim, 0)


class 测试敏感词过滤器(unittest.TestCase):
    """测试敏感词过滤器"""

    def setUp(self):
        self.filter = 敏感词过滤器()

    def test_添加敏感词_单个(self):
        """测试添加单个敏感词"""
        self.filter.添加敏感词('敏感词')
        result = self.filter.检测('文本包含敏感词')
        self.assertEqual(result, ['敏感词'])

    def test_添加敏感词_列表(self):
        """测试添加多个敏感词"""
        self.filter.添加敏感词(['词1', '词2'])
        result = self.filter.检测('包含词1和词2')
        self.assertIn('词1', result)
        self.assertIn('词2', result)

    def test_过滤(self):
        """测试过滤功能"""
        self.filter.添加敏感词('敏感词')
        result = self.filter.过滤('文本包含敏感词')
        self.assertNotIn('敏感词', result)
        self.assertIn('***', result)

    def test_过滤_自定义替换字符(self):
        """测试自定义替换字符"""
        self.filter.添加敏感词('敏感词')
        result = self.filter.过滤('文本包含敏感词', 替换字符='X')
        self.assertIn('XXX', result)

    def test_检测_无敏感词(self):
        """测试检测无敏感词"""
        self.filter.添加敏感词('敏感词')
        result = self.filter.检测('安全文本')
        self.assertEqual(result, [])

    def test_清空(self):
        """测试清空敏感词"""
        self.filter.添加敏感词('敏感词')
        self.filter.清空()
        result = self.filter.检测('包含敏感词')
        self.assertEqual(result, [])

    def test_多次过滤(self):
        """测试多次过滤"""
        self.filter.添加敏感词(['敏感词1', '敏感词2'])
        text = '包含敏感词1和敏感词2'
        result = self.filter.过滤(text)
        self.assertNotIn('敏感词1', result)
        self.assertNotIn('敏感词2', result)


if __name__ == '__main__':
    unittest.main(verbosity=2)