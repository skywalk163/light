"""
日期时间 — lightpub 桥接模块

基于 Python datetime / time 库封装，函数名对齐上游 duanpub（段言时期）packages/时间日期/源.duan。

上游 duanpub 原始包通过 C FFI 调用系统时间 API，
本桥接模块用 Python datetime/time 模块替代，提供等价的时间日期功能。
"""

import datetime as _datetime
import time as _time


# =============================================================================
# 常量
# =============================================================================

星期名称 = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
月份名称 = ['一月', '二月', '三月', '四月', '五月', '六月',
          '七月', '八月', '九月', '十月', '十一月', '十二月']


# =============================================================================
# 数据结构
# =============================================================================

class 日期时间对象:
    """日期时间对象，封装 datetime.datetime"""
    def __init__(self, dt=None):
        self._dt = dt if dt is not None else _datetime.datetime.now()

    @property
    def 年(self):
        return self._dt.year

    @property
    def 月(self):
        return self._dt.month

    @property
    def 日(self):
        return self._dt.day

    @property
    def 时(self):
        return self._dt.hour

    @property
    def 分(self):
        return self._dt.minute

    @property
    def 秒(self):
        return self._dt.second


class 时间间隔:
    """时间间隔对象，封装 datetime.timedelta"""
    def __init__(self, td=None):
        self._td = td if td is not None else _datetime.timedelta()


# =============================================================================
# 时间戳函数
# =============================================================================

def 当前时间戳():
    """当前 Unix 时间戳（秒）"""
    return _time.time()


def 当前毫秒时间戳():
    """当前毫秒时间戳"""
    return int(_time.time() * 1000)


def 当前微秒时间戳():
    """当前微秒时间戳"""
    return int(_time.time() * 1000000)


def 当前时间():
    """当前本地时间，返回 日期时间对象"""
    return 日期时间对象(_datetime.datetime.now())


def 当前UTC时间():
    """当前 UTC 时间，返回 日期时间对象"""
    return 日期时间对象(_datetime.datetime.utcnow())


# =============================================================================
# 时间戳与日期转换
# =============================================================================

def 时间戳转日期时间(时间戳):
    """Unix 时间戳转 日期时间对象"""
    if 时间戳 is None:
        raise Exception("时间戳转日期时间失败: 时间戳为空")
    try:
        return 日期时间对象(_datetime.datetime.fromtimestamp(时间戳))
    except (ValueError, OSError, OverflowError) as e:
        raise Exception("时间戳转日期时间失败: " + str(e))


def 时间戳转UTC(时间戳):
    """Unix 时间戳转 UTC 日期时间对象"""
    if 时间戳 is None:
        raise Exception("时间戳转UTC失败: 时间戳为空")
    try:
        return 日期时间对象(_datetime.datetime.utcfromtimestamp(时间戳))
    except (ValueError, OSError, OverflowError) as e:
        raise Exception("时间戳转UTC失败: " + str(e))


def 日期时间转时间戳(dt):
    """日期时间对象转 Unix 时间戳"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("日期时间转时间戳失败: 无效的日期时间对象")
    try:
        return dt._dt.timestamp()
    except (ValueError, OSError) as e:
        raise Exception("日期时间转时间戳失败: " + str(e))


def 创建日期时间(年, 月, 日, 时=0, 分=0, 秒=0):
    """创建日期时间对象"""
    try:
        return 日期时间对象(_datetime.datetime(年, 月, 日, 时, 分, 秒))
    except ValueError as e:
        raise Exception("创建日期时间失败: " + str(e))


def 创建UTC日期时间(年, 月, 日, 时=0, 分=0, 秒=0):
    """创建 UTC 日期时间对象"""
    try:
        return 日期时间对象(_datetime.datetime(年, 月, 日, 时, 分, 秒, tzinfo=_datetime.timezone.utc))
    except ValueError as e:
        raise Exception("创建UTC日期时间失败: " + str(e))


# =============================================================================
# 格式化与解析
# =============================================================================

def 格式化时间(dt, 格式='%Y-%m-%d %H:%M:%S'):
    """格式化日期时间对象为字符串"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("格式化时间失败: 无效的日期时间对象")
    return dt._dt.strftime(格式)


def 格式化ISO8601(dt):
    """格式化为 ISO8601 字符串"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("格式化ISO8601失败: 无效的日期时间对象")
    return dt._dt.isoformat()


def 格式化RFC3339(dt):
    """格式化为 RFC3339 字符串"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("格式化RFC3339失败: 无效的日期时间对象")
    return dt._dt.strftime('%Y-%m-%dT%H:%M:%S%z')


def 格式化中文日期(dt):
    """格式化为中文日期字符串"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("格式化中文日期失败: 无效的日期时间对象")
    return dt._dt.strftime('%Y年%m月%d日 %H时%M分%S秒')


def 解析时间(文本, 格式='%Y-%m-%d %H:%M:%S'):
    """解析时间字符串为 日期时间对象"""
    if not 文本:
        raise Exception("解析时间失败: 文本为空")
    try:
        return 日期时间对象(_datetime.datetime.strptime(文本, 格式))
    except ValueError as e:
        raise Exception("解析时间失败: " + str(e))


# =============================================================================
# 日历计算
# =============================================================================

def 获取星期名称(dt):
    """获取星期名称（星期一~星期日）"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("获取星期名称失败: 无效的日期时间对象")
    return 星期名称[dt._dt.weekday()]


def 获取月份名称(月):
    """获取月份名称"""
    if 月 < 1 or 月 > 12:
        raise Exception("获取月份名称失败: 月份必须在1-12之间")
    return 月份名称[月 - 1]


def 获取月份天数(年, 月):
    """获取指定年月的天数"""
    if 月 < 1 or 月 > 12:
        raise Exception("获取月份天数失败: 月份必须在1-12之间")
    import calendar as _cal
    return _cal.monthrange(年, 月)[1]


def 是闰年(年):
    """判断是否为闰年"""
    return (年 % 4 == 0 and 年 % 100 != 0) or (年 % 400 == 0)


def 获取星期(dt):
    """获取星期几（0=星期一, 6=星期日）"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("获取星期失败: 无效的日期时间对象")
    return dt._dt.weekday()


def 获取年日(dt):
    """获取今天是当年第几天（1-366）"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("获取年日失败: 无效的日期时间对象")
    return dt._dt.timetuple().tm_yday


# =============================================================================
# 时间运算
# =============================================================================

def 时间相加(dt, 间隔):
    """时间加时间间隔，返回新 日期时间对象"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("时间相加失败: 无效的日期时间对象")
    if not 间隔 or not hasattr(间隔, '_td'):
        raise Exception("时间相加失败: 无效的时间间隔")
    return 日期时间对象(dt._dt + 间隔._td)


def 时间相减(dt1, dt2):
    """时间相减，返回 时间间隔"""
    if not dt1 or not hasattr(dt1, '_dt'):
        raise Exception("时间相减失败: 无效的第一个日期时间对象")
    if not dt2 or not hasattr(dt2, '_dt'):
        raise Exception("时间相减失败: 无效的第二个日期时间对象")
    return 时间间隔(dt1._dt - dt2._dt)


def 时间加天数(dt, 天数):
    """时间加天数，返回新 日期时间对象"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("时间加天数失败: 无效的日期时间对象")
    return 日期时间对象(dt._dt + _datetime.timedelta(days=天数))


def 时间加小时(dt, 小时):
    """时间加小时，返回新 日期时间对象"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("时间加小时失败: 无效的日期时间对象")
    return 日期时间对象(dt._dt + _datetime.timedelta(hours=小时))


def 时间加分钟(dt, 分钟):
    """时间加分钟，返回新 日期时间对象"""
    if not dt or not hasattr(dt, '_dt'):
        raise Exception("时间加分钟失败: 无效的日期时间对象")
    return 日期时间对象(dt._dt + _datetime.timedelta(minutes=分钟))


# =============================================================================
# 时间比较
# =============================================================================

def 时间比较(dt1, dt2):
    """比较两个时间，返回 -1/0/1（dt1早于/等于/晚于dt2）"""
    if not dt1 or not hasattr(dt1, '_dt') or not dt2 or not hasattr(dt2, '_dt'):
        raise Exception("时间比较失败: 无效的日期时间对象")
    if dt1._dt < dt2._dt:
        return -1
    elif dt1._dt > dt2._dt:
        return 1
    return 0


def 时间等于(dt1, dt2):
    """判断两个时间是否相等"""
    return 时间比较(dt1, dt2) == 0


def 时间早于(dt1, dt2):
    """判断 dt1 是否早于 dt2"""
    return 时间比较(dt1, dt2) < 0


# =============================================================================
# 时间间隔
# =============================================================================

def 创建时间间隔(天=0, 秒=0, 微秒=0, 毫秒=0, 分钟=0, 小时=0, 周=0):
    """创建时间间隔对象"""
    try:
        return 时间间隔(_datetime.timedelta(
            days=天, seconds=秒, microseconds=微秒,
            milliseconds=毫秒, minutes=分钟, hours=小时, weeks=周
        ))
    except (ValueError, TypeError) as e:
        raise Exception("创建时间间隔失败: " + str(e))


def 时间间隔总秒数(间隔):
    """获取时间间隔的总秒数"""
    if not 间隔 or not hasattr(间隔, '_td'):
        raise Exception("时间间隔总秒数失败: 无效的时间间隔")
    return 间隔._td.total_seconds()


def 时间间隔总毫秒数(间隔):
    """获取时间间隔的总毫秒数"""
    return 时间间隔总秒数(间隔) * 1000


def 时间间隔天数(间隔):
    """获取时间间隔的天数"""
    if not 间隔 or not hasattr(间隔, '_td'):
        raise Exception("时间间隔天数失败: 无效的时间间隔")
    return 间隔._td.days


def 时间间隔小时数(间隔):
    """获取时间间隔的总小时数"""
    return 时间间隔总秒数(间隔) / 3600


def 时间间隔分钟数(间隔):
    """获取时间间隔的总分钟数"""
    return 时间间隔总秒数(间隔) / 60


# =============================================================================
# 计时与休眠
# =============================================================================

def 开始计时():
    """开始计时，返回当前时间戳"""
    return _time.time()


def 结束计时(开始时间):
    """结束计时，返回耗时秒数"""
    if 开始时间 is None:
        raise Exception("结束计时失败: 开始时间为空")
    return _time.time() - 开始时间


def 休眠(秒):
    """休眠指定秒数"""
    if 秒 < 0:
        raise Exception("休眠失败: 秒数不能为负")
    _time.sleep(秒)


def 毫秒休眠(毫秒):
    """休眠指定毫秒数"""
    if 毫秒 < 0:
        raise Exception("毫秒休眠失败: 毫秒数不能为负")
    _time.sleep(毫秒 / 1000.0)
