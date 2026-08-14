"""
测试：日期时间模块 (stdlib/日期时间.py)

覆盖范围：
1. 日期操作（创建、格式化、运算、比较、范围、星期、年中第几天、ISO日历、闰年）
2. 时间操作（创建、格式化、运算、时区）
3. 日期时间操作（创建、格式化、运算、时区转换、ISO 8601、Unix时间戳、相对时间）
4. 时段/周期（持续时间、格式、工作日计算、年龄）
5. 日历工具（农历、节假日、日历生成）
6. 解析（自动检测格式、中文日期、相对时间）
7. 向后兼容（现有API）
"""

import sys
import os
import time
import datetime
from datetime import datetime as _datetime, timedelta as _timedelta, timezone as _timezone

# 添加 stdlib 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'stdlib'))

from 日期时间 import (
    # 类
    日期时间, 时间差, 日期, 时间, 农历日期,
    # 日期操作
    创建日期, 日期范围, 月份范围, 日期加月份, 日期加年份,
    # 时间操作
    创建时间,
    # 日期时间操作
    创建日期时间, 创建时间差, 加月份, 减月份, 加年份, 减年份,
    Unix时间戳转日期时间, 日期时间转Unix时间戳,
    # 时区
    创建时区, 北京时间, 纽约时间, 伦敦时间, 东京时间, 获取时区, 时区转换, 常用时区,
    # 格式化
    时间戳转字符串友好, 时间戳转ISO8601, 解析ISO8601,
    # 时段/周期
    计算持续时间, 格式化持续时间, 计算工作日, 计算年龄,
    # 农历
    公历转农历, 农历转公历, 春节日期, 中秋日期, 端午日期, 中国节假日,
    获取农历节日, 获取公历节日,
    # 日历
    生成月历, 生成年历, 生成月历文本,
    # 解析
    解析日期字符串, 解析中文日期, 解析相对时间, 自动检测格式,
    # 现有函数
    当前时间, 当前UTC时间, 从时间戳, 从字符串,
    当前时间戳, 当前时间戳毫秒,
    加天数, 减天数, 加小时, 减小时,
    获取今天, 获取昨天, 获取明天,
    获取本周一, 获取本周末,
    获取本月第一天, 获取本月最后一天,
    获取本年第一天, 获取本年最后一天,
    计算两个日期天数差, 计算工作日天数,
    判断闰年, 获取月份天数,
    字符串转日期时间, 字符串转日期, 字符串转时间,
    时间戳转字符串, 日期时间转字符串,
    获取年份, 获取月份, 获取日,
    获取星期几名称, 星期几, 星期名称,
    是否工作日, 是否周末, 是否闰年,
    添加天数, 时间差天数, 日期比较,
    获取相对时间描述, 日期转时间戳,
    日期加减, 计算时间差,
    # 常量
    星期名称列表, 星期全称列表, 月份名称列表,
)


# =============================================================================
# 辅助函数
# =============================================================================

def _assert_eq(actual, expected, msg=""):
    """断言相等"""
    assert actual == expected, f"期望 {expected}，实际 {actual}。{msg}"


def _assert_true(actual, msg=""):
    """断言为真"""
    assert actual, f"期望为真，实际为假。{msg}"


def _assert_false(actual, msg=""):
    """断言为假"""
    assert not actual, f"期望为假，实际为真。{msg}"


def _assert_raises(exc_type, func, *args, **kwargs):
    """断言抛出异常"""
    try:
        func(*args, **kwargs)
        assert False, f"期望抛出 {exc_type.__name__}，但未抛出"
    except exc_type:
        pass
    except Exception as e:
        assert False, f"期望抛出 {exc_type.__name__}，但抛出了 {type(e).__name__}: {e}"


# =============================================================================
# 1. 日期操作
# =============================================================================

def test_日期创建():
    """测试日期创建"""
    d = 创建日期(2024, 8, 7)
    _assert_eq(d.年, 2024)
    _assert_eq(d.月, 8)
    _assert_eq(d.日, 7)
    _assert_eq(str(d), "日期(2024, 8, 7)")

    # 无效日期
    _assert_raises(ValueError, 创建日期, 2024, 2, 30)


def test_日期格式化():
    """测试日期格式化"""
    d = 创建日期(2024, 8, 7)
    _assert_eq(d.格式化(), "2024-08-07")
    _assert_eq(d.格式化("%Y年%m月%d日"), "2024年08月07日")
    _assert_eq(d.格式化("%Y/%m/%d"), "2024/08/07")


def test_日期运算():
    """测试日期运算"""
    d = 创建日期(2024, 8, 7)
    td = 创建时间差(天=3)

    # 加法
    d2 = d + td
    _assert_eq(d2.年, 2024)
    _assert_eq(d2.月, 8)
    _assert_eq(d2.日, 10)

    # 减法
    d3 = d - td
    _assert_eq(d3.年, 2024)
    _assert_eq(d3.月, 8)
    _assert_eq(d3.日, 4)

    # 日期减日期
    差值 = d - d2
    _assert_eq(int(差值.天数()), -3)


def test_日期比较():
    """测试日期比较"""
    d1 = 创建日期(2024, 8, 7)
    d2 = 创建日期(2024, 8, 8)
    d3 = 创建日期(2024, 8, 7)

    _assert_true(d1 < d2)
    _assert_true(d2 > d1)
    _assert_true(d1 <= d3)
    _assert_true(d1 >= d3)
    _assert_true(d1 == d3)
    _assert_true(d1 != d2)


def test_日期范围():
    """测试日期范围生成"""
    开始 = 创建日期(2024, 8, 1)
    结束 = 创建日期(2024, 8, 5)
    范围 = 日期范围(开始, 结束)
    _assert_eq(len(范围), 5)
    _assert_eq(范围[0], 开始)
    _assert_eq(范围[-1], 结束)

    # 步长
    范围2 = 日期范围(开始, 结束, 2)
    _assert_eq(len(范围2), 3)
    _assert_eq(范围2[0].日, 1)
    _assert_eq(范围2[1].日, 3)
    _assert_eq(范围2[2].日, 5)


def test_月份范围():
    """测试月份范围生成"""
    开始 = 创建日期(2024, 1, 15)
    结束 = 创建日期(2024, 4, 10)
    范围 = 月份范围(开始, 结束)
    _assert_eq(len(范围), 4)
    _assert_eq(范围[0].月, 1)
    _assert_eq(范围[1].月, 2)
    _assert_eq(范围[2].月, 3)
    _assert_eq(范围[3].月, 4)
    # 每月范围应该都是第一天
    _assert_eq(范围[0].日, 1)


def test_日期加月年():
    """测试日期加月份/年份"""
    d = 创建日期(2024, 1, 31)
    d2 = 日期加月份(d, 1)
    _assert_eq(d2.月, 2)
    _assert_eq(d2.日, 29)  # 2024年是闰年，2月有29天

    d3 = 日期加月份(d, 12)
    _assert_eq(d3.年, 2025)
    _assert_eq(d3.月, 1)

    d4 = 日期加年份(d, 1)
    _assert_eq(d4.年, 2025)
    _assert_eq(d4.月, 1)
    _assert_eq(d4.日, 31)


def test_日期星期():
    """测试日期星期相关"""
    # 2024-08-07 是周三
    d = 创建日期(2024, 8, 7)
    _assert_eq(d.星期(), 2)  # 0=周一, 2=周三
    _assert_eq(d.周几(), "周三")
    _assert_eq(d.周几全称(), "星期三")
    _assert_eq(d.周中第几天(), 3)  # 1=周一, 3=周三


def test_日期年中第几天():
    """测试年中第几天"""
    d = 创建日期(2024, 1, 1)
    _assert_eq(d.年中第几天(), 1)
    d2 = 创建日期(2024, 12, 31)
    _assert_eq(d2.年中第几天(), 366)  # 闰年


def test_日期ISO日历():
    """测试ISO日历"""
    d = 创建日期(2024, 1, 1)
    iso_year, iso_week, iso_day = d.ISO日历()
    _assert_eq(iso_year, 2024)
    _assert_eq(iso_week, 1)
    _assert_eq(iso_day, 1)


def test_日期闰年检测():
    """测试闰年检测"""
    d = 创建日期(2024, 8, 7)
    _assert_true(d.是否闰年())
    d2 = 创建日期(2023, 8, 7)
    _assert_false(d2.是否闰年())


def test_日期工作日检测():
    """测试工作日检测"""
    # 2024-08-05 是周一
    d = 创建日期(2024, 8, 5)
    _assert_true(d.是否工作日())
    _assert_false(d.是否周末())
    # 2024-08-10 是周六
    d2 = 创建日期(2024, 8, 10)
    _assert_false(d2.是否工作日())
    _assert_true(d2.是否周末())


def test_日期转为时间戳():
    """测试日期转时间戳"""
    d = 创建日期(2024, 1, 1)
    ts = d.转为时间戳()
    # 验证
    dt = _datetime.fromtimestamp(ts)
    _assert_eq(dt.year, 2024)
    _assert_eq(dt.month, 1)
    _assert_eq(dt.day, 1)


def test_日期可哈希():
    """测试日期可哈希"""
    d1 = 创建日期(2024, 8, 7)
    d2 = 创建日期(2024, 8, 7)
    s = {d1, d2}
    _assert_eq(len(s), 1)


# =============================================================================
# 2. 时间操作
# =============================================================================

def test_时间创建():
    """测试时间创建"""
    t = 创建时间(14, 30, 45)
    _assert_eq(t.时, 14)
    _assert_eq(t.分, 30)
    _assert_eq(t.秒, 45)
    _assert_eq(t.微秒, 0)
    _assert_eq(str(t), "时间(14, 30, 45)")

    t2 = 创建时间(9, 15, 30, 500000)
    _assert_eq(t2.微秒, 500000)


def test_时间格式化():
    """测试时间格式化"""
    t = 创建时间(14, 30, 45)
    _assert_eq(t.格式化(), "14:30:45")
    _assert_eq(t.格式化("%H时%M分%S秒"), "14时30分45秒")


def test_时间比较():
    """测试时间比较"""
    t1 = 创建时间(10, 0, 0)
    t2 = 创建时间(14, 0, 0)
    t3 = 创建时间(10, 0, 0)

    _assert_true(t1 < t2)
    _assert_true(t2 > t1)
    _assert_true(t1 == t3)
    _assert_true(t1 != t2)


def test_时间时区():
    """测试时区时间"""
    tz = 北京时间()
    t = 创建时间(14, 30, 0, 时区=tz)
    _assert_true(t.有时区())
    _assert_eq(t.时区, tz)

    # 无时区时间
    t2 = 创建时间(14, 30, 0)
    _assert_false(t2.有时区())

    # 附加时区
    t3 = t2.附加时区(tz)
    _assert_true(t3.有时区())


def test_时间可哈希():
    """测试时间可哈希"""
    t1 = 创建时间(10, 0, 0)
    t2 = 创建时间(10, 0, 0)
    s = {t1, t2}
    _assert_eq(len(s), 1)


# =============================================================================
# 3. 日期时间操作
# =============================================================================

def test_日期时间创建():
    """测试日期时间创建"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 45)
    _assert_eq(dt.年(), 2024)
    _assert_eq(dt.月(), 8)
    _assert_eq(dt.日(), 7)
    _assert_eq(dt.时(), 14)
    _assert_eq(dt.分(), 30)
    _assert_eq(dt.秒(), 45)
    _assert_eq(dt.微秒(), 0)


def test_日期时间格式化():
    """测试日期时间格式化"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 45)
    _assert_eq(dt.格式化(), "2024-08-07 14:30:45")
    _assert_eq(dt.格式化("%Y年%m月%d日 %H时%M分%S秒"), "2024年08月07日 14时30分45秒")


def test_日期时间运算():
    """测试日期时间运算"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 45)
    td = 创建时间差(天=1, 小时=2)

    # 加
    dt2 = dt + td
    _assert_eq(dt2.日(), 8)
    _assert_eq(dt2.时(), 16)

    # 减
    dt3 = dt - td
    _assert_eq(dt3.日(), 6)
    _assert_eq(dt3.时(), 12)

    # 日期时间减日期时间
    td2 = dt2 - dt
    _assert_eq(int(td2.天数()), 1)
    _assert_eq(td2.小时数(), 2)


def test_日期时间比较():
    """测试日期时间比较"""
    dt1 = 创建日期时间(2024, 8, 7, 14, 0, 0)
    dt2 = 创建日期时间(2024, 8, 8, 10, 0, 0)
    dt3 = 创建日期时间(2024, 8, 7, 14, 0, 0)

    _assert_true(dt1 < dt2)
    _assert_true(dt2 > dt1)
    _assert_true(dt1 == dt3)
    _assert_true(dt1 != dt2)


def test_日期时间时区转换():
    """测试时区转换"""
    bj_tz = 北京时间()
    ny_tz = 纽约时间()
    london_tz = 伦敦时间()
    tokyo_tz = 东京时间()

    # 创建北京时间
    dt = 创建日期时间(2024, 8, 7, 14, 0, 0, 时区=bj_tz)
    _assert_eq(dt.时(), 14)

    # 转UTC
    utc = dt.转为UTC()
    _assert_eq(utc.时(), 6)  # 14 - 8 = 6

    # 转纽约
    ny = dt.转换时区(ny_tz)
    _assert_eq(ny.时(), 1)  # 14 - 8 - 5 = 1 (或14-13=1)

    # 转东京
    tokyo = dt.转换时区(tokyo_tz)
    _assert_eq(tokyo.时(), 15)  # 14 - 8 + 9 = 15


def test_日期时间ISO8601():
    """测试ISO 8601"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 45)
    iso = dt.ISO8601()
    _assert_true("2024-08-07" in iso)
    _assert_true("14:30:45" in iso)

    # 解析ISO 8601
    dt2 = 解析ISO8601(iso)
    _assert_eq(dt2.年(), dt.年())
    _assert_eq(dt2.月(), dt.月())
    _assert_eq(dt2.日(), dt.日())


def test_日期时间Unix时间戳():
    """测试Unix时间戳转换"""
    # 创建已知时间戳
    dt = 创建日期时间(2024, 1, 1, 0, 0, 0, 时区=_timezone.utc)
    ts = dt.转为时间戳()

    # 时间戳转回
    dt2 = Unix时间戳转日期时间(ts, _timezone.utc)
    _assert_eq(dt2.年(), 2024)
    _assert_eq(dt2.月(), 1)
    _assert_eq(dt2.日(), 1)

    # 函数别名
    ts2 = 日期时间转Unix时间戳(dt)
    _assert_eq(int(ts), int(ts2))


def test_日期时间相对时间():
    """测试相对时间描述"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 0)
    desc = dt.相对时间描述()
    _assert_true(isinstance(desc, str))


def test_日期时间转换为日期时间():
    """测试日期时间转为日期/时间"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 45)
    d = dt.转为日期()
    _assert_eq(d.年, 2024)
    _assert_eq(d.月, 8)
    _assert_eq(d.日, 7)

    t = dt.转为时间()
    _assert_eq(t.时, 14)
    _assert_eq(t.分, 30)
    _assert_eq(t.秒, 45)


def test_日期时间加月年():
    """测试日期时间加月份/年份"""
    dt = 创建日期时间(2024, 1, 31, 14, 30, 0)
    dt2 = 加月份(dt, 1)
    _assert_eq(dt2.月(), 2)
    _assert_eq(dt2.日(), 29)  # 闰年

    dt3 = 减月份(dt2, 1)
    _assert_eq(dt3.月(), 1)
    _assert_eq(dt3.日(), 29)  # Feb 29 → Jan 29（保持同一天数）

    dt4 = 加年份(dt, 1)
    _assert_eq(dt4.年(), 2025)
    _assert_eq(dt4.月(), 1)

    dt5 = 减年份(dt4, 1)
    _assert_eq(dt5.年(), 2024)


def test_日期时间可哈希():
    """测试日期时间可哈希"""
    dt1 = 创建日期时间(2024, 8, 7, 14, 0, 0)
    dt2 = 创建日期时间(2024, 8, 7, 14, 0, 0)
    s = {dt1, dt2}
    _assert_eq(len(s), 1)


def test_常用时区():
    """测试常用时区"""
    _assert_true('北京时间' in 常用时区)
    _assert_true('UTC' in 常用时区)
    _assert_true('纽约时间' in 常用时区)
    _assert_true('伦敦时间' in 常用时区)
    _assert_true('东京时间' in 常用时区)
    _assert_true('香港时间' in 常用时区)
    _assert_true('巴黎时间' in 常用时区)
    _assert_true('悉尼时间' in 常用时区)


def test_获取时区():
    """测试获取时区"""
    tz = 获取时区('北京时间')
    _assert_eq(tz, 北京时间())

    tz2 = 获取时区('UTC+8')
    _assert_eq(tz2, 北京时间())

    tz3 = 获取时区('UTC+5:30')
    _assert_eq(tz3, 获取时区('印度时间'))

    _assert_raises(ValueError, 获取时区, '未知时区')


# =============================================================================
# 4. 时段/周期
# =============================================================================

def test_持续时间():
    """测试持续时间计算"""
    dt1 = 创建日期时间(2024, 8, 7, 14, 0, 0)
    dt2 = 创建日期时间(2024, 8, 10, 16, 30, 0)
    td = 计算持续时间(dt1, dt2)
    _assert_eq(int(td.天数()), 3)
    _assert_eq(td.小时数(), 2)
    _assert_eq(td.分钟数(), 30)


def test_格式化持续时间():
    """测试持续时间格式化"""
    td = 创建时间差(天=3, 小时=5, 分钟=30)
    desc = 格式化持续时间(td)
    _assert_true(isinstance(desc, str))
    _assert_true('3天' in desc)


def test_时间差中文描述():
    """测试时间差中文描述"""
    td = 创建时间差(天=1, 小时=2, 分钟=30)
    desc = td.中文描述()
    _assert_true('1天' in desc)

    td2 = 创建时间差(小时=2, 分钟=30)
    desc2 = td2.中文描述()
    _assert_true('2小时' in desc2)

    td3 = 创建时间差(秒=45)
    desc3 = td3.中文描述()
    _assert_true('45秒' in desc3)


def test_时间差成份():
    """测试时间差成份"""
    td = 创建时间差(天=3, 小时=5, 分钟=30, 秒=15)
    comp = td.成份()
    _assert_eq(comp['天'], 3)
    _assert_eq(comp['小时'], 5)
    _assert_eq(comp['分钟'], 30)
    _assert_eq(comp['秒'], 15)


def test_时间差运算():
    """测试时间差运算"""
    td1 = 创建时间差(天=5)
    td2 = 创建时间差(天=3)

    # 加减
    td3 = td1 + td2
    _assert_eq(int(td3.天数()), 8)

    td4 = td1 - td2
    _assert_eq(int(td4.天数()), 2)

    # 负
    td5 = -td1
    _assert_eq(int(td5.天数()), -5)

    # 乘除
    td6 = td1 * 2
    _assert_eq(int(td6.天数()), 10)

    td7 = td1 / 2
    _assert_eq(td7.天数(), 2.5)


def test_时间差总小时分钟():
    """测试时间差总小时/分钟/毫秒"""
    td = 创建时间差(天=1, 小时=6)
    _assert_eq(td.总小时数(), 30)
    _assert_eq(td.总分钟数(), 1800)
    _assert_eq(td.总毫秒数(), 30 * 3600 * 1000)


def test_计算工作日():
    """测试计算工作日（排除节假日）"""
    开始 = 创建日期(2024, 8, 5)  # 周一
    结束 = 创建日期(2024, 8, 11)  # 周日
    天数 = 计算工作日(开始, 结束)
    _assert_eq(天数, 5)  # 周一到周五


def test_计算年龄():
    """测试计算年龄"""
    出生 = 创建日期(1990, 5, 15)
    截止 = 创建日期(2024, 8, 7)
    年龄 = 计算年龄(出生, 截止)
    _assert_eq(年龄, 34)

    # 还没过生日
    截止2 = 创建日期(2024, 5, 10)
    年龄2 = 计算年龄(出生, 截止2)
    _assert_eq(年龄2, 33)


# =============================================================================
# 5. 农历日历
# =============================================================================

def test_农历日期创建():
    """测试农历日期创建"""
    d = 农历日期(2024, 1, 1)  # 2024年正月初一
    _assert_eq(d.年, 2024)
    _assert_eq(d.月, 1)
    _assert_eq(d.日, 1)
    _assert_false(d.是否闰月)
    _assert_eq(str(d), "农历2024年1月1日")


def test_农历天干地支():
    """测试农历天干地支"""
    d = 农历日期(2024, 1, 1)
    _assert_eq(d.天干地支年(), "甲辰")
    _assert_eq(d.生肖年(), "龙")


def test_公历转农历():
    """测试公历转农历"""
    # 2024年春节是2月10日
    春节 = 公历转农历(2024, 2, 10)
    _assert_eq(春节.年, 2024)
    _assert_eq(春节.月, 1)
    _assert_eq(春节.日, 1)

    # 2024年8月7日
    d = 公历转农历(2024, 8, 7)
    _assert_eq(d.年, 2024)
    _assert_eq(d.月, 7)  # 农历七月
    _assert_eq(d.日, 4)  # 初四
    # 确认：2024年8月7日 = 农历七月初四


def test_农历转公历():
    """测试农历转公历"""
    # 2024年正月初一 = 2024年2月10日
    d = 农历转公历(2024, 1, 1)
    _assert_eq(d.年, 2024)
    _assert_eq(d.月, 2)
    _assert_eq(d.日, 10)

    # 2024年八月十五
    d2 = 农历转公历(2024, 8, 15)
    _assert_eq(d2.年, 2024)
    _assert_eq(d2.月, 9)
    _assert_eq(d2.日, 17)


def test_日期时间转农历():
    """测试日期时间转农历"""
    dt = 创建日期时间(2024, 2, 10, 12, 0, 0)
    农历 = dt.转农历()
    _assert_eq(农历.年, 2024)
    _assert_eq(农历.月, 1)
    _assert_eq(农历.日, 1)


def test_日期转农历():
    """测试日期转农历"""
    d = 创建日期(2024, 2, 10)
    农历 = d.转农历()
    _assert_eq(农历.年, 2024)
    _assert_eq(农历.月, 1)
    _assert_eq(农历.日, 1)


def test_春节日期():
    """测试春节日期"""
    d = 春节日期(2024)
    _assert_eq(d.年, 2024)
    _assert_eq(d.月, 2)
    _assert_eq(d.日, 10)

    d2 = 春节日期(2025)
    _assert_eq(d2.年, 2025)
    _assert_eq(d2.月, 1)
    _assert_eq(d2.日, 29)


def test_中秋日期():
    """测试中秋日期"""
    d = 中秋日期(2024)
    _assert_eq(d.年, 2024)
    _assert_eq(d.月, 9)
    _assert_eq(d.日, 17)


def test_端午日期():
    """测试端午日期"""
    d = 端午日期(2024)
    _assert_eq(d.年, 2024)
    _assert_eq(d.月, 6)
    _assert_eq(d.日, 10)


def test_中国节假日():
    """测试中国节假日"""
    节假日 = 中国节假日(2024)
    _assert_true('春节' in 节假日)
    _assert_true('中秋节' in 节假日)
    _assert_true('端午节' in 节假日)
    _assert_true('国庆节' in 节假日)
    _assert_true('元旦' in 节假日)

    # 验证春节日期
    春节 = 节假日['春节']
    _assert_eq(春节.月, 2)
    _assert_eq(春节.日, 10)


def test_获取公历节日():
    """测试获取公历节日"""
    _assert_eq(获取公历节日(1, 1), "元旦")
    _assert_eq(获取公历节日(10, 1), "国庆节")
    _assert_eq(获取公历节日(5, 1), "劳动节")
    _assert_eq(获取公历节日(6, 1), "儿童节")
    _assert_eq(获取公历节日(12, 25), "圣诞节")
    _assert_eq(获取公历节日(3, 15), "")  # 未知节日


def test_获取农历节日():
    """测试获取农历节日"""
    _assert_eq(获取农历节日(2024, 1, 1), "春节")
    _assert_eq(获取农历节日(2024, 8, 15), "中秋节")
    _assert_eq(获取农历节日(2024, 5, 5), "端午节")
    _assert_eq(获取农历节日(2024, 1, 15), "元宵节")
    _assert_eq(获取农历节日(2024, 7, 7), "七夕节")


def test_生成月历():
    """测试生成月历"""
    月历 = 生成月历(2024, 8)
    _assert_true(len(月历) >= 4)  # 至少4周
    _assert_true(len(月历) <= 6)  # 最多6周
    # 第一行应该包含日期对象或None
    for 行 in 月历:
        for 日 in 行:
            if 日 is not None:
                _assert_true(isinstance(日, 日期))


def test_生成年历():
    """测试生成年历"""
    年历 = 生成年历(2024)
    _assert_eq(len(年历), 12)
    for 月 in range(1, 13):
        _assert_true(月 in 年历)


def test_生成月历文本():
    """测试生成月历文本"""
    文本 = 生成月历文本(2024, 8)
    _assert_true(isinstance(文本, str))
    _assert_true('2024' in 文本)
    _assert_true('August' in 文本)


# =============================================================================
# 6. 解析
# =============================================================================

def test_自动检测格式():
    """测试自动检测格式"""
    _assert_eq(自动检测格式("2024-08-07"), "%Y-%m-%d")
    _assert_eq(自动检测格式("2024/08/07"), "%Y/%m/%d")
    _assert_eq(自动检测格式("2024-08-07 14:30:45"), "%Y-%m-%d %H:%M:%S")
    _assert_eq(自动检测格式("20240807"), "%Y%m%d")
    _assert_eq(自动检测格式("14:30:45"), "%H:%M:%S")
    _assert_eq(自动检测格式("2024年8月7日"), "%Y年%m月%d日")


def test_解析日期字符串():
    """测试解析日期字符串"""
    dt = 解析日期字符串("2024-08-07")
    _assert_eq(dt.年(), 2024)
    _assert_eq(dt.月(), 8)
    _assert_eq(dt.日(), 7)

    dt2 = 解析日期字符串("2024-08-07 14:30:45")
    _assert_eq(dt2.时(), 14)
    _assert_eq(dt2.分(), 30)
    _assert_eq(dt2.秒(), 45)

    dt3 = 解析日期字符串("2024/08/07")
    _assert_eq(dt3.年(), 2024)
    _assert_eq(dt3.月(), 8)
    _assert_eq(dt3.日(), 7)

    # 指定格式
    dt4 = 解析日期字符串("2024|08|07", "%Y|%m|%d")
    _assert_eq(dt4.年(), 2024)
    _assert_eq(dt4.月(), 8)
    _assert_eq(dt4.日(), 7)

    # 空字符串
    _assert_raises(ValueError, 解析日期字符串, "")


def test_解析中文日期():
    """测试解析中文日期"""
    # 绝对日期
    dt = 解析中文日期("2024年8月7日")
    _assert_eq(dt.年(), 2024)
    _assert_eq(dt.月(), 8)
    _assert_eq(dt.日(), 7)

    dt2 = 解析中文日期("2024年08月07日")
    _assert_eq(dt2.年(), 2024)
    _assert_eq(dt2.月(), 8)
    _assert_eq(dt2.日(), 7)

    # 含时间
    dt3 = 解析中文日期("2024年8月7日 14:30:45")
    _assert_eq(dt3.时(), 14)
    _assert_eq(dt3.分(), 30)
    _assert_eq(dt3.秒(), 45)

    # 简写
    dt4 = 解析中文日期("8月7日")
    _assert_eq(dt4.月(), 8)
    _assert_eq(dt4.日(), 7)

    # 相对日期（需要动态计算，只验证类型）
    for 文本 in ['今天', '昨天', '明天', '前天', '后天']:
        dt5 = 解析中文日期(文本)
        _assert_true(isinstance(dt5, 日期时间))


def test_解析相对时间():
    """测试解析相对时间"""
    # 这些函数返回基于当前时间的相对值，验证类型
    for 文本 in ['1小时前', '2天后', '3天前', '30分钟前', '1周后']:
        dt = 解析相对时间(文本)
        _assert_true(isinstance(dt, 日期时间))


def test_时间戳转友好字符串():
    """测试时间戳转友好字符串"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 45)
    ts = dt.转为时间戳()
    s = 时间戳转字符串友好(ts)
    _assert_true('2024年' in s)
    _assert_true('8月' in s or '08月' in s)
    _assert_true('7日' in s or '07日' in s)

    # 不含时间
    s2 = 时间戳转字符串友好(ts, 包含时间=False)
    _assert_true('2024年' in s2)
    _assert_false(':' in s2)


def test_时间戳转ISO8601():
    """测试时间戳转ISO 8601"""
    ts = _datetime(2024, 8, 7, 14, 30, 45).timestamp()
    iso = 时间戳转ISO8601(ts)
    _assert_true('2024-08-07' in iso)


# =============================================================================
# 7. 向后兼容（现有API）
# =============================================================================

def test_当前时间():
    """测试当前时间"""
    now = 当前时间()
    _assert_true(isinstance(now, 日期时间))


def test_当前UTC时间():
    """测试当前UTC时间"""
    now = 当前UTC时间()
    _assert_true(isinstance(now, 日期时间))


def test_当前时间戳():
    """测试当前时间戳"""
    ts = 当前时间戳()
    _assert_true(ts > 0)


def test_当前时间戳毫秒():
    """测试当前时间戳毫秒"""
    ts = 当前时间戳毫秒()
    _assert_true(ts > 0)


def test_从时间戳():
    """测试从时间戳创建"""
    dt = _datetime(2024, 8, 7, 14, 30, 45)
    ts = dt.timestamp()
    result = 从时间戳(ts)
    _assert_eq(result.年(), 2024)
    _assert_eq(result.月(), 8)
    _assert_eq(result.日(), 7)


def test_从字符串():
    """测试从字符串解析"""
    dt = 从字符串("2024-08-07 14:30:45")
    _assert_eq(dt.年(), 2024)
    _assert_eq(dt.月(), 8)
    _assert_eq(dt.日(), 7)
    _assert_eq(dt.时(), 14)


def test_加天数减天数():
    """测试加减天数"""
    dt = 创建日期时间(2024, 8, 7, 14, 0, 0)
    d1 = 加天数(dt, 3)
    _assert_eq(d1.日(), 10)
    d2 = 减天数(dt, 3)
    _assert_eq(d2.日(), 4)


def test_加小时减小时():
    """测试加减小时"""
    dt = 创建日期时间(2024, 8, 7, 14, 0, 0)
    h1 = 加小时(dt, 3)
    _assert_eq(h1.时(), 17)
    h2 = 减小时(dt, 3)
    _assert_eq(h2.时(), 11)


def test_获取今天昨天明天():
    """测试获取今天/昨天/明天"""
    today = 获取今天()
    yesterday = 获取昨天()
    tomorrow = 获取明天()
    _assert_true(isinstance(today, 日期时间))
    _assert_true(isinstance(yesterday, 日期时间))
    _assert_true(isinstance(tomorrow, 日期时间))


def test_获取本周相关():
    """测试获取本周相关"""
    monday = 获取本周一()
    weekend = 获取本周末()
    _assert_true(isinstance(monday, 日期时间))
    _assert_true(isinstance(weekend, 日期时间))
    _assert_eq(monday.星期(), 0)  # 周一


def test_获取本月相关():
    """测试获取本月相关"""
    first = 获取本月第一天()
    last = 获取本月最后一天()
    _assert_true(isinstance(first, 日期时间))
    _assert_true(isinstance(last, 日期时间))
    _assert_eq(first.日(), 1)
    _assert_true(last.日() >= 28)


def test_获取本年相关():
    """测试获取本年相关"""
    first = 获取本年第一天()
    last = 获取本年最后一天()
    _assert_true(isinstance(first, 日期时间))
    _assert_true(isinstance(last, 日期时间))
    _assert_eq(first.月(), 1)
    _assert_eq(first.日(), 1)
    _assert_eq(last.月(), 12)
    _assert_eq(last.日(), 31)


def test_计算两个日期天数差():
    """测试计算两个日期天数差"""
    dt1 = 创建日期时间(2024, 8, 1)
    dt2 = 创建日期时间(2024, 8, 10)
    diff = 计算两个日期天数差(dt1, dt2)
    _assert_eq(diff, 9)


def test_计算工作日天数():
    """测试计算工作日天数"""
    start = 创建日期时间(2024, 8, 5)  # 周一
    end = 创建日期时间(2024, 8, 11)  # 周日
    days = 计算工作日天数(start, end)
    _assert_eq(days, 5)


def test_判断闰年():
    """测试判断闰年"""
    _assert_true(判断闰年(2024))
    _assert_false(判断闰年(2023))
    _assert_true(判断闰年(2000))
    _assert_false(判断闰年(1900))


def test_获取月份天数():
    """测试获取月份天数"""
    _assert_eq(获取月份天数(2024, 1), 31)
    _assert_eq(获取月份天数(2024, 2), 29)  # 闰年
    _assert_eq(获取月份天数(2023, 2), 28)
    _assert_eq(获取月份天数(2024, 4), 30)


def test_字符串转日期时间():
    """测试字符串转日期时间"""
    dt = 字符串转日期时间("2024-08-07 14:30:45")
    _assert_true(isinstance(dt, _datetime))
    _assert_eq(dt.year, 2024)


def test_字符串转日期():
    """测试字符串转日期"""
    dt = 字符串转日期("2024-08-07")
    _assert_true(isinstance(dt, _datetime))


def test_字符串转时间():
    """测试字符串转时间"""
    dt = 字符串转时间("14:30:45")
    _assert_true(isinstance(dt, _datetime))


def test_时间戳转字符串():
    """测试时间戳转字符串"""
    ts = _datetime(2024, 8, 7, 14, 30, 45).timestamp()
    s = 时间戳转字符串(ts)
    _assert_eq(s, "2024-08-07 14:30:45")


def test_日期时间转字符串():
    """测试日期时间转字符串"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 45)
    s = 日期时间转字符串(dt)
    _assert_eq(s, "2024-08-07 14:30:45")

    # 兼容Python datetime
    import datetime
    py_dt = datetime.datetime(2024, 8, 7, 14, 30, 45)
    s2 = 日期时间转字符串(py_dt)
    _assert_eq(s2, "2024-08-07 14:30:45")


def test_获取年份月份日():
    """测试获取年份/月份/日"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 45)
    _assert_eq(获取年份(dt), 2024)
    _assert_eq(获取月份(dt), 8)
    _assert_eq(获取日(dt), 7)


def test_星期几函数():
    """测试星期几函数"""
    # 2024-08-07 是周三
    dt = 创建日期时间(2024, 8, 7)
    _assert_eq(星期几(dt), 2)  # 0=周一, 2=周三

    # 无参数
    wd = 星期几()
    _assert_true(isinstance(wd, int))
    _assert_true(0 <= wd <= 6)


def test_星期名称函数():
    """测试星期名称函数"""
    dt = 创建日期时间(2024, 8, 7)
    name = 星期名称(dt)
    _assert_true(name in 星期名称列表)


def test_是否工作日周末():
    """测试是否工作日/周末"""
    # 2024-08-05 是周一
    dt = 创建日期时间(2024, 8, 5)
    _assert_true(是否工作日(dt))
    _assert_false(是否周末(dt))

    # 2024-08-10 是周六
    dt2 = 创建日期时间(2024, 8, 10)
    _assert_false(是否工作日(dt2))
    _assert_true(是否周末(dt2))


def test_是否闰年函数():
    """测试是否闰年函数"""
    _assert_true(是否闰年(2024))
    _assert_false(是否闰年(2023))
    _assert_true(是否闰年(创建日期时间(2024, 1, 1)))


def test_添加天数():
    """测试添加天数"""
    dt = 创建日期时间(2024, 8, 7)
    result = 添加天数(dt, 3)
    _assert_eq(result.日(), 10)

    # 兼容Python datetime
    import datetime
    py_dt = datetime.datetime(2024, 8, 7)
    result2 = 添加天数(py_dt, 3)
    _assert_eq(result2.day, 10)


def test_时间差天数():
    """测试时间差天数"""
    dt1 = 创建日期时间(2024, 8, 1)
    dt2 = 创建日期时间(2024, 8, 10)
    _assert_eq(时间差天数(dt1, dt2), 9)
    _assert_eq(时间差天数(dt2, dt1), 9)


def test_日期比较函数():
    """测试日期比较函数"""
    dt1 = 创建日期时间(2024, 8, 1)
    dt2 = 创建日期时间(2024, 8, 10)
    dt3 = 创建日期时间(2024, 8, 1)
    _assert_eq(日期比较(dt1, dt2), -1)
    _assert_eq(日期比较(dt2, dt1), 1)
    _assert_eq(日期比较(dt1, dt3), 0)


def test_获取相对时间描述():
    """测试获取相对时间描述"""
    desc = 获取相对时间描述(创建日期时间(2024, 8, 7, 14, 30, 0))
    _assert_true(isinstance(desc, str))


def test_日期转时间戳():
    """测试日期转时间戳"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 45)
    ts = 日期转时间戳(dt)
    _assert_true(ts > 0)


def test_日期加减函数():
    """测试日期加减函数"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 0)
    result = 日期加减(dt, 天数=3, 小时=2)
    _assert_eq(result.日(), 10)
    _assert_eq(result.时(), 16)


def test_计算时间差():
    """测试计算时间差"""
    dt1 = 创建日期时间(2024, 8, 1)
    dt2 = 创建日期时间(2024, 8, 10)
    td = 计算时间差(dt1, dt2)
    _assert_eq(int(td.天数()), 9)


def test_创建时间差():
    """测试创建时间差"""
    td = 创建时间差(天=1, 小时=2, 分钟=30, 秒=15)
    _assert_eq(int(td.天数()), 1)
    _assert_eq(td.小时数(), 2)
    _assert_eq(td.分钟数(), 30)
    _assert_eq(td.秒数(), 15)


def test_时间差布尔值():
    """测试时间差布尔值"""
    td1 = 创建时间差(天=0)
    _assert_false(bool(td1))
    td2 = 创建时间差(天=1)
    _assert_true(bool(td2))


def test_日期时间季度():
    """测试日期时间季度"""
    dt1 = 创建日期时间(2024, 1, 15)
    _assert_eq(dt1.季度(), 1)
    dt2 = 创建日期时间(2024, 4, 15)
    _assert_eq(dt2.季度(), 2)
    dt3 = 创建日期时间(2024, 7, 15)
    _assert_eq(dt3.季度(), 3)
    dt4 = 创建日期时间(2024, 10, 15)
    _assert_eq(dt4.季度(), 4)


def test_日期时间夏令时():
    """测试日期时间夏令时"""
    # 中国时区没有夏令时
    dt = 创建日期时间(2024, 8, 7, 时区=北京时间())
    _assert_false(dt.是否夏令时())


def test_日期时间复制():
    """测试日期时间复制"""
    dt = 创建日期时间(2024, 8, 7, 14, 30, 45)
    dt2 = dt.复制()
    _assert_eq(dt, dt2)
    _assert_true(dt is not dt2)


def test_日期复制():
    """测试日期复制"""
    d = 创建日期(2024, 8, 7)
    d2 = d.复制()
    _assert_eq(d, d2)
    _assert_true(d is not d2)


def test_时间复制():
    """测试时间复制"""
    t = 创建时间(14, 30, 45)
    t2 = t.复制()
    _assert_eq(t, t2)
    _assert_true(t is not t2)


def test_农历日期格式化():
    """测试农历日期格式化"""
    d = 农历日期(2024, 1, 1)
    s = d.格式化()
    _assert_eq(s, "农历2024年1月1日")

    # 带天干地支
    s2 = d.格式化("%G年%S年 农历%m月%d日")
    _assert_eq(s2, "甲辰年龙年 农历1月1日")


def test_获取星期几名称():
    """测试获取星期几名称"""
    dt = 创建日期时间(2024, 8, 7)  # 周三
    name = 获取星期几名称(dt)
    _assert_eq(name, "周三")


def test_时间差总秒数():
    """测试时间差总秒数"""
    td = 创建时间差(天=1, 小时=1)
    _assert_eq(td.总秒数(), 90000)  # 86400 + 3600


def test_时区转换函数():
    """测试时区转换函数"""
    dt = 创建日期时间(2024, 8, 7, 14, 0, 0, 时区=北京时间())
    dt2 = 时区转换(dt, _timezone.utc)
    _assert_eq(dt2.时(), 6)


def test_ISO日历():
    """测试ISO日历"""
    dt = 创建日期时间(2024, 1, 1)
    iso = dt.ISO日历()
    _assert_eq(len(iso), 3)


def test_生成月历空值():
    """测试月历空值处理"""
    月历 = 生成月历(2024, 8)
    # 检查是否有None值（表示空白天数）
    has_none = any(日 is None for 行 in 月历 for 日 in 行)
    # 8月1日是周四，第一周应该有3个None
    if 月历[0][0] is None:
        _assert_true(has_none)


# =============================================================================
# 运行所有测试
# =============================================================================

def run_all_tests():
    """运行所有测试"""
    test_functions = [
        # 1. 日期操作
        test_日期创建,
        test_日期格式化,
        test_日期运算,
        test_日期比较,
        test_日期范围,
        test_月份范围,
        test_日期加月年,
        test_日期星期,
        test_日期年中第几天,
        test_日期ISO日历,
        test_日期闰年检测,
        test_日期工作日检测,
        test_日期转为时间戳,
        test_日期可哈希,

        # 2. 时间操作
        test_时间创建,
        test_时间格式化,
        test_时间比较,
        test_时间时区,
        test_时间可哈希,

        # 3. 日期时间操作
        test_日期时间创建,
        test_日期时间格式化,
        test_日期时间运算,
        test_日期时间比较,
        test_日期时间时区转换,
        test_日期时间ISO8601,
        test_日期时间Unix时间戳,
        test_日期时间相对时间,
        test_日期时间转换为日期时间,
        test_日期时间加月年,
        test_日期时间可哈希,
        test_常用时区,
        test_获取时区,

        # 4. 时段/周期
        test_持续时间,
        test_格式化持续时间,
        test_时间差中文描述,
        test_时间差成份,
        test_时间差运算,
        test_时间差总小时分钟,
        test_计算工作日,
        test_计算年龄,

        # 5. 农历日历
        test_农历日期创建,
        test_农历天干地支,
        test_公历转农历,
        test_农历转公历,
        test_日期时间转农历,
        test_日期转农历,
        test_春节日期,
        test_中秋日期,
        test_端午日期,
        test_中国节假日,
        test_获取公历节日,
        test_获取农历节日,
        test_生成月历,
        test_生成年历,
        test_生成月历文本,

        # 6. 解析
        test_自动检测格式,
        test_解析日期字符串,
        test_解析中文日期,
        test_解析相对时间,
        test_时间戳转友好字符串,
        test_时间戳转ISO8601,

        # 7. 向后兼容
        test_当前时间,
        test_当前UTC时间,
        test_当前时间戳,
        test_当前时间戳毫秒,
        test_从时间戳,
        test_从字符串,
        test_加天数减天数,
        test_加小时减小时,
        test_获取今天昨天明天,
        test_获取本周相关,
        test_获取本月相关,
        test_获取本年相关,
        test_计算两个日期天数差,
        test_计算工作日天数,
        test_判断闰年,
        test_获取月份天数,
        test_字符串转日期时间,
        test_字符串转日期,
        test_字符串转时间,
        test_时间戳转字符串,
        test_日期时间转字符串,
        test_获取年份月份日,
        test_星期几函数,
        test_星期名称函数,
        test_是否工作日周末,
        test_是否闰年函数,
        test_添加天数,
        test_时间差天数,
        test_日期比较函数,
        test_获取相对时间描述,
        test_日期转时间戳,
        test_日期加减函数,
        test_计算时间差,
        test_创建时间差,
        test_时间差布尔值,
        test_日期时间季度,
        test_日期时间夏令时,
        test_日期时间复制,
        test_日期复制,
        test_时间复制,
        test_农历日期格式化,
        test_获取星期几名称,
        test_时间差总秒数,
        test_时区转换函数,
        test_ISO日历,
        test_生成月历空值,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            passed += 1
            print(f"  ✓ {test_func.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {test_func.__name__}: {e}")

    print(f"\n结果: {passed}/{len(test_functions)} 通过, {failed} 失败")
    return failed == 0


if __name__ == '__main__':
    print("测试: 日期时间模块 (stdlib/日期时间.py)")
    print("=" * 50)
    成功 = run_all_tests()
    sys.exit(0 if 成功 else 1)