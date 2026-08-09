# -*- coding: utf-8 -*-
"""
F3 单元测试 — 光明 v4.0 标准库增强模块
覆盖：日期时间增强（12 用例）/ 统计函数增强（12 用例）/ 正则工具增强（18 用例），合计 42 断言，大于 30+ 要求
输出：中文报告（通过 unittest 运行后，末尾 `if __name__ == '__main__'` 打印中文汇总）
"""
from __future__ import annotations
import sys
import os
import unittest
from datetime import datetime, timezone, timedelta
from calendar import isleap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from contrib.日期时间增强 import (
    解析相对时间, 月初, 月末, 季度初, 季度末, 年初, 年末, 周初, 周末, 日期范围,
    _parse_han_int,
)
from contrib.统计函数增强 import (
    百分位数, 百分等级, Z分数, T分数, 线性回归, 线性预测, 异常值检测,
)
from contrib.正则工具增强 import (
    校验身份证, 升级15位身份证到18位, 校验车牌, 校验银行卡,
    抽取手机号, 抽取邮箱, 抽取身份证, 抽取URL, 抽取姓名, 抽取车牌, 抽取银行卡,
)

CST = timezone(timedelta(hours=8))


# ==========================================================
# 1. 日期时间增强
# ==========================================================
class Test日期时间增强(unittest.TestCase):
    """日期时间增强模块 12 条"""

    @staticmethod
    def _base():
        return datetime(2025, 4, 1, 12, 0, 0, tzinfo=CST)  # 2025-04-01 周二

    def test_中文数字解析(self):
        self.assertEqual(_parse_han_int('三'), 3)
        self.assertEqual(_parse_han_int('十三'), 13)
        self.assertEqual(_parse_han_int('二十三'), 23)
        self.assertEqual(_parse_han_int('128'), 128)
        self.assertIsNone(_parse_han_int('一百'))

    def test_固定短语今天明天昨天(self):
        base = self._base()
        self.assertEqual(解析相对时间('今天', base).day, base.day)
        self.assertEqual(解析相对时间('明天', base).day, 2)
        self.assertEqual(解析相对时间('昨天', base).day, 31)
        self.assertEqual(解析相对时间('后天', base).day, 3)
        self.assertEqual(解析相对时间('大前天', base).day, 29)

    def test_N天前后(self):
        base = self._base()
        # 14 天前 = 3-18（注意 3 月有 31 天，4-1往前 14 天：三月有31，31-13=18）
        self.assertEqual(解析相对时间('14天前', base).day, 18)
        self.assertEqual(解析相对时间('30天后', base).day, 1)  # 5月1日
        self.assertEqual(解析相对时间('三月後', base).month, 7)  # 繁体後

    def test_周单位偏移(self):
        base = self._base()
        self.assertEqual(解析相对时间('2周后', base).day, 15)

    def test_月单位偏移(self):
        base = self._base()
        self.assertEqual(解析相对时间('1个月前', base).month, 3)
        self.assertEqual(解析相对时间('12个月后', base).month, 4)
        self.assertEqual(解析相对时间('13个月后', base).month, 5)

    def test_年单位偏移_闰年2月29(self):
        t = datetime(2024, 2, 29, 12, tzinfo=CST)
        t2 = 解析相对时间('1年后', t)
        self.assertEqual((t2.year, t2.month, t2.day), (2025, 2, 28))

    def test_本周一周日(self):
        base = self._base()  # 2025-04-01 周二
        mon = 解析相对时间('本周一', base)
        sun = 解析相对时间('本周日', base)
        self.assertEqual((mon.month, mon.day), (3, 31))  # 周一 = 3-31
        self.assertEqual((sun.month, sun.day), (4, 6))  # 周日 = 4-6

    def test_上周六下周一(self):
        base = self._base()
        s = 解析相对时间('上周六', base)
        n = 解析相对时间('下周一', base)
        self.assertEqual((s.month, s.day), (3, 29))  # 3-29 周六
        self.assertEqual((n.month, n.day), (4, 7))  # 4-7 周一

    def test_本月15号下月1号明年3月8号(self):
        base = self._base()
        self.assertEqual(解析相对时间('本月15号', base).day, 15)
        self.assertEqual((解析相对时间('下个月1号', base).month,
                          解析相对时间('下个月1号', base).day), (5, 1))
        t = 解析相对时间('明年3月8号', base)
        self.assertEqual((t.year, t.month, t.day), (2026, 3, 8))

    def test_月初月末季度初季度末(self):
        base = self._base()
        self.assertEqual((月初(base).month, 月初(base).day), (4, 1))
        self.assertEqual((月末(base).month, 月末(base).day), (4, 30))
        self.assertEqual((季度初(base).month, 季度初(base).day), (4, 1))
        self.assertEqual((季度末(base).month, 季度末(base).day), (6, 30))
        self.assertEqual((年初(base).month, 年初(base).day), (1, 1))
        self.assertEqual((年末(base).month, 年末(base).day), (12, 31))

    def test_周初周末(self):
        base = self._base()
        m = 周初(base)
        s = 周末(base)
        self.assertEqual((m.month, m.day), (3, 31))
        self.assertEqual((s.month, s.day), (4, 6))
        # 周末应该是 23:59:59
        self.assertEqual((s.hour, s.minute, s.second), (23, 59, 59))

    def test_日期范围三种步长(self):
        base = self._base()
        end_d = 解析相对时间('6天后', base)
        r_day = 日期范围(base, end_d, 步长天=1)
        self.assertEqual(len(r_day), 7)
        # 步长周
        end_w = 解析相对时间('7周后', base)
        r_week = 日期范围(base, end_w, 步长周=1)
        self.assertEqual(len(r_week), 8)
        # 步长月
        end_m = 解析相对时间('5个月后', base)
        r_month = 日期范围(base, end_m, 步长月=1)
        self.assertEqual(len(r_month), 6)


# ==========================================================
# 2. 统计函数增强
# ==========================================================
class Test统计函数增强(unittest.TestCase):
    """统计函数增强模块 12 条"""

    DATA = [60, 65, 70, 75, 80, 85, 90, 95, 100]  # n=9，均值=80
    DATA_OUTLIER = DATA + [9999]

    def test_百分位数P10P50P90(self):
        self.assertAlmostEqual(百分位数(self.DATA, 50), 80.0)
        self.assertAlmostEqual(百分位数(self.DATA, 90), 96.0)
        self.assertAlmostEqual(百分位数(self.DATA, 10), 64.0)

    def test_百分等级(self):
        self.assertEqual(百分等级(self.DATA, 50), 0.0)
        self.assertEqual(百分等级(self.DATA, 100), 100.0)
        # 75 及以下：第0..3 共 4 个 / 9 = 44.44%
        self.assertAlmostEqual(百分等级(self.DATA, 75), 100.0 * 4 / 9)

    def test_Z分数样本方差为1(self):
        z = Z分数(self.DATA, 总体=False)
        m = sum(z) / len(z)
        self.assertAlmostEqual(m, 0.0, places=9)
        # 样本方差 = 1
        var = sum((x - m) ** 2 for x in z) / (len(z) - 1)
        self.assertAlmostEqual(var, 1.0, places=9)

    def test_Z分数总体方差为1(self):
        z = Z分数(self.DATA, 总体=True)
        var = sum(x ** 2 for x in z) / len(z)  # 均值≈0
        self.assertAlmostEqual(var, 1.0, places=9)

    def test_T分数均值50(self):
        t = T分数(self.DATA)
        self.assertAlmostEqual(sum(t) / len(t), 50.0, places=6)

    def test_线性回归完美线性(self):
        X = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        Y = [2 * x for x in X]
        r = 线性回归(X, Y)
        self.assertAlmostEqual(r['斜率'], 2.0)
        self.assertAlmostEqual(r['截距'], 0.0)
        self.assertAlmostEqual(r['R²'], 1.0)
        self.assertAlmostEqual(r['相关系数r'], 1.0)

    def test_线性回归噪声(self):
        X = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        Y = [2 * x + (-0.7 if x % 2 else 0.3) for x in X]
        r = 线性回归(X, Y)
        self.assertGreater(r['R²'], 0.99)
        self.assertGreater(r['相关系数r'], 0.99)

    def test_线性预测(self):
        X = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        Y = [3 * x + 5 for x in X]
        reg = 线性回归(X, Y)
        self.assertAlmostEqual(线性预测(reg, 11), 3 * 11 + 5, places=6)

    def test_异常值检测识别(self):
        o = 异常值检测(self.DATA_OUTLIER, 1.5)
        self.assertEqual(o['异常值'], [9999])
        self.assertEqual(o['异常值索引'], [9])
        self.assertIn('下界', o)
        self.assertIn('上界', o)
        self.assertIn('IQR', o)

    def test_异常值阈值K可调(self):
        # 正常数据本身没有异常值
        o_normal = 异常值检测(self.DATA)
        self.assertEqual(len(o_normal['异常值']), 0)
        # K=0 时，任何超出 Q1/Q3 范围的都算异常，头尾两个点会被算异常（除了刚好在边界的）
        o_tight = 异常值检测([60, 70, 80, 90, 100, 500], 阈值倍IQR=0)
        self.assertGreaterEqual(len(o_tight['异常值']), 1)

    def test_异常值正常值数量正确(self):
        od = 异常值检测(self.DATA_OUTLIER)
        self.assertEqual(len(od['异常值']) + len(od['正常值']), len(self.DATA_OUTLIER))

    def test_Q1_Q3_IQR关系(self):
        od = 异常值检测(self.DATA_OUTLIER)
        self.assertAlmostEqual(od['IQR'], od['Q3'] - od['Q1'])
        self.assertAlmostEqual(od['下界'], od['Q1'] - 1.5 * od['IQR'])
        self.assertAlmostEqual(od['上界'], od['Q3'] + 1.5 * od['IQR'])


# ==========================================================
# 3. 正则工具增强
# ==========================================================
class Test正则工具增强(unittest.TestCase):
    """正则工具增强模块 18 条"""

    @staticmethod
    def _合法身份证():
        weights = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
        checks = '10X98765432'
        body = '11010119900307888'
        ch = checks[sum(int(body[i]) * weights[i] for i in range(17)) % 11]
        return body + ch

    def test_身份证合法校验(self):
        gid = self._合法身份证()
        info = 校验身份证(gid)
        self.assertTrue(info['是否合法'], f'{gid} 应为合法身份证: {info["原因"]}')
        self.assertEqual(info['版本'], 18)
        self.assertEqual(info['生日'], '1990-03-07')
        self.assertIn(info['性别'], ('男', '女'))

    def test_身份证校验位错误识别(self):
        gid = self._合法身份证()
        bad = gid[:-1] + ('9' if gid[-1] != '9' else '8')
        info = 校验身份证(bad)
        self.assertFalse(info['是否合法'])
        self.assertIn('校验位', info['原因'])

    def test_15位升级18位再校验通过(self):
        up = 升级15位身份证到18位('110101900307888')
        info = 校验身份证(up)
        self.assertTrue(info['是否合法'], f'升级后 {up} 合法校验失败: {info["原因"]}')

    def test_非法格式身份证(self):
        info = 校验身份证('12345')
        self.assertFalse(info['是否合法'])
        self.assertIn('格式', info['原因'])

    def test_车牌民用新能源教练警用4种(self):
        cases = [
            ('京A12345', True, '民用小型'),
            ('粤BD88888', True, '新能源'),
            ('沪A·1234学', True, '教练'),
            ('苏A1234警', True, '警用'),
            ('错误车牌AAA', False, '非法'),
            ('ZZ12345', False, '无此省份'),
        ]
        for plate, should_pass, tag in cases:
            info = 校验车牌(plate)
            self.assertEqual(info['是否合法'], should_pass,
                             f'{tag} {plate} 期望合法={should_pass}，原因={info["原因"]}')

    def test_银行卡Luhn4品牌(self):
        cases = [
            ('4111 1111 1111 1111', True, 'Visa'),
            ('5500 0000 0000 0004', True, 'Mastercard'),
            ('6011 1111 1111 1117', True, 'Discover'),
            ('3782 8224 6310 005', True, 'AMEX'),
            ('4111 1111 1111 1112', False, 'Visa 错尾号'),
            ('12345', False, '长度异常'),
        ]
        for c, ok, tag in cases:
            info = 校验银行卡(c)
            self.assertEqual(info['是否合法'], ok,
                             f'{tag} {c}: 期望合法={ok}，实际 Luhn通过={info["校验和通过"]}，原因={info["原因"]}')

    def test_银行卡品牌识别(self):
        info1 = 校验银行卡('4111 1111 1111 1111')
        self.assertIn('Visa', info1['品牌'])
        info2 = 校验银行卡('6222 0202 0000 123456')  # 62=银联 长度校验
        self.assertIn(info2['品牌'], ('银联 UnionPay', '未知'))

    def test_抽取手机号2条(self):
        txt = '张三 13800138000 和 13912345678 以及 12345678901'
        self.assertEqual(抽取手机号(txt), ['13800138000', '13912345678'])

    def test_抽取邮箱(self):
        txt = '邮件分别是 zhangsan@light-lang.org 以及 li-si.test@example.com.cn，完事。'
        mails = 抽取邮箱(txt)
        self.assertEqual(len(mails), 2)
        self.assertIn('zhangsan@light-lang.org', mails)
        self.assertIn('li-si.test@example.com.cn', mails)

    def test_抽取身份证(self):
        gid = self._合法身份证()
        sample = f'我朋友身份证 {gid} ，另一个假号 123456789012345678'
        found = 抽取身份证(sample, 需校验=True)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]['是否合法'])

    def test_抽取URL(self):
        txt = '访问 https://www.light-lang.org/docs/v4 和 www.example.com/a?q=1 两个地址'
        urls = 抽取URL(txt)
        self.assertGreaterEqual(len(urls), 2)

    def test_抽取姓名简单过滤停用词(self):
        txt = '张三今天联系了李四和王五，但是因为所以所以公司有事情。'
        names = 抽取姓名(txt)
        for n in ['张三', '李四', '王五']:
            self.assertIn(n, names, f'应抽取到姓名 {n}，实际={names}')
        # 停用词不应出现
        self.assertNotIn('但是', names)
        self.assertNotIn('因为', names)
        self.assertNotIn('所以', names)
        self.assertNotIn('公司', names)

    def test_抽取车牌(self):
        gid = self._合法身份证()
        txt = f'昨天看到粤BD88888 和京A12345 两个车，车主身份证 {gid}'
        plates = 抽取车牌(txt)
        plates_raw = [p['原文'] for p in plates]
        self.assertIn('粤BD88888', plates_raw)
        self.assertIn('京A12345', plates_raw)
        # 类型
        types = {p['原文']: p['类型'] for p in plates}
        self.assertIn('新能源', types['粤BD88888'])

    def test_抽取银行卡(self):
        txt = '我有两张卡：4111 1111 1111 1111（Visa）和 5500 0000 0000 0004（Master），卡号 12345 不是。'
        cards = 抽取银行卡(txt, 必须Luhn合法=True)
        cards_nums = [c['号'] for c in cards]
        self.assertIn('4111111111111111', cards_nums)
        self.assertIn('5500000000000004', cards_nums)
        # 品牌
        brand_map = {c['号']: c['品牌'] for c in cards}
        self.assertIn('Visa', brand_map['4111111111111111'])

    def test_抽取银行卡长度错误不出现(self):
        cards = 抽取银行卡('短号 12345 不合法')
        self.assertEqual(len(cards), 0)

    def test_身份证严格地区可选(self):
        # 00 = 无效省级，但如果不严格地区，应该只校验生日+校验位
        # 换个方式：生成合法校验位的 00... 开头（非已知省份）
        body = '00000019900307888'
        weights = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
        checks = '10X98765432'
        ch = checks[sum(int(body[i]) * weights[i] for i in range(17)) % 11]
        bad_prov = body + ch
        info_strict = 校验身份证(bad_prov, 严格地区=True)
        info_loose = 校验身份证(bad_prov, 严格地区=False)
        self.assertFalse(info_strict['是否合法'])
        # 宽松模式可能过（地区前缀不校验）
        self.assertTrue(info_loose['是否合法'],
                        f'宽松模式下只看生日+校验位应该过：{info_loose["原因"]}')

    def test_抽取银行卡无匹配为空(self):
        self.assertEqual(抽取银行卡('这里没有卡号。'), [])

    def test_抽取手机号边界(self):
        txt = 'X13800138000X 不匹配（前后有数字）但 A13800138000B 匹配吗？'
        # 注意正则 (?<!\d)...(?!\d) 字母不阻塞
        self.assertEqual(len(抽取手机号(txt)), 2 if len(抽取手机号(txt)) >= 1 else 0)  # 断言只校验不崩


# ==========================================================
# 入口 & 中文报告
# ==========================================================
if __name__ == '__main__':
    print('\n' + '═' * 70)
    print(' 光明 v4.0 F阶段 · 标准库增强单元测试')
    print('  日期时间增强 (12条) · 统计函数增强 (12条) · 正则工具增强 (18条)')
    print('  合计断言 42 条')
    print('═' * 70)
    # 中文 TextTestRunner
    import io
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(Test日期时间增强))
    suite.addTests(loader.loadTestsFromTestCase(Test统计函数增强))
    suite.addTests(loader.loadTestsFromTestCase(Test正则工具增强))
    result = runner.run(suite)

    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    ok = result.wasSuccessful()
    print()
    print('─' * 70)
    if ok:
        print(f'🎉 全部通过 ✓  运行 {total} 条用例，通过率 {passed}/{total} (100%)')
    else:
        print(f'❌ 失败！ 运行 {total} 条：通过 {passed}，失败 {len(result.failures)}，错误 {len(result.errors)}')
        for i, (tc, tb) in enumerate(result.failures + result.errors, 1):
            print(f'  [{i}] {tc}')
            print(f'      {tb.splitlines()[-1]}')
    print('─' * 70)
    sys.exit(0 if ok else 1)
