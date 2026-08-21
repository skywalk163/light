"""
日期序列 — lightpub 桥接模块

基于 Python datetime / time / calendar 库封装，
函数名对齐上游 duanpub（段言时期）packages/日期序列/源.duan。

上游 duanpub 原始包通过 C FFI 实现日期序列功能，
本桥接模块用 Python 标准库替代，提供等价的日期序列处理功能。
"""

import datetime as _datetime
import time as _time
import calendar as _calendar
import math as _math


# =============================================================================
# 时间戳
# =============================================================================

class _TimeStamp:
    """时间戳对象"""
    def __init__(self, dt=None):
        self._dt = dt if dt is not None else _datetime.datetime.now()

    def to_datetime(self):
        return self._dt


def 创建时间戳(年, 月, 日, 时=0, 分=0, 秒=0, 微秒=0, 时区=None):
    """创建时间戳"""
    try:
        dt = _datetime.datetime(年, 月, 日, 时, 分, 秒, 微秒)
        if 时区:
            dt = dt.replace(tzinfo=时区)
        return _TimeStamp(dt)
    except Exception as e:
        raise Exception("创建时间戳失败: " + str(e))


def 创建时间戳从毫秒(毫秒):
    """从毫秒时间戳创建"""
    try:
        dt = _datetime.datetime.fromtimestamp(毫秒 / 1000.0)
        return _TimeStamp(dt)
    except Exception as e:
        raise Exception("创建时间戳从毫秒失败: " + str(e))


def 创建时间戳从字符串(字符串, 格式='%Y-%m-%d %H:%M:%S'):
    """从字符串解析创建时间戳"""
    try:
        dt = _datetime.datetime.strptime(字符串, 格式)
        return _TimeStamp(dt)
    except Exception as e:
        raise Exception("创建时间戳从字符串失败: " + str(e))


def 创建时间戳当前():
    """创建当前时间的时间戳"""
    return _TimeStamp(_datetime.datetime.now())


def 创建时间戳今天():
    """创建今天零点的时间戳"""
    now = _datetime.datetime.now()
    return _TimeStamp(now.replace(hour=0, minute=0, second=0, microsecond=0))


# =============================================================================
# 时间戳格式化
# =============================================================================

def ts格式化(ts, 格式='%Y-%m-%d %H:%M:%S'):
    """格式化时间戳"""
    if not isinstance(ts, _TimeStamp):
        raise Exception("ts格式化失败: 不是时间戳对象")
    try:
        return ts._dt.strftime(格式)
    except Exception as e:
        raise Exception("ts格式化失败: " + str(e))


def tsToISO8601(ts):
    """转为 ISO 8601 格式"""
    return ts格式化(ts, '%Y-%m-%dT%H:%M:%S')


def tsToUnix(ts):
    """转为 Unix 时间戳（秒）"""
    return ts._dt.timestamp()


def tsToMs(ts):
    """转为 Unix 时间戳（毫秒）"""
    return int(ts._dt.timestamp() * 1000)


# =============================================================================
# 时间戳运算
# =============================================================================

def ts添加(ts, 持续时间):
    """时间戳加法"""
    if not isinstance(ts, _TimeStamp):
        raise Exception("ts添加失败: 不是时间戳对象")
    if isinstance(持续时间, _Duration):
        delta = _datetime.timedelta(seconds=持续时间._total_seconds)
    elif isinstance(持续时间, (int, float)):
        delta = _datetime.timedelta(seconds=持续时间)
    else:
        raise Exception("ts添加失败: 不支持的持续时间类型")
    return _TimeStamp(ts._dt + delta)


def ts减去(ts, 持续时间):
    """时间戳减法"""
    if not isinstance(ts, _TimeStamp):
        raise Exception("ts减去失败: 不是时间戳对象")
    if isinstance(持续时间, _Duration):
        delta = _datetime.timedelta(seconds=持续时间._total_seconds)
    elif isinstance(持续时间, (int, float)):
        delta = _datetime.timedelta(seconds=持续时间)
    else:
        raise Exception("ts减去失败: 不支持的持续时间类型")
    return _TimeStamp(ts._dt - delta)


def ts差值(ts1, ts2):
    """计算两个时间戳的差值，返回 Duration"""
    if not isinstance(ts1, _TimeStamp) or not isinstance(ts2, _TimeStamp):
        raise Exception("ts差值失败: 不是时间戳对象")
    delta = ts1._dt - ts2._dt
    return _Duration(delta.total_seconds())


# =============================================================================
# 时间戳比较
# =============================================================================

def tsIsBefore(ts1, ts2):
    """判断是否早于"""
    return ts1._dt < ts2._dt


def tsIsAfter(ts1, ts2):
    """判断是否晚于"""
    return ts1._dt > ts2._dt


def tsIsEqual(ts1, ts2):
    """判断是否相等"""
    return ts1._dt == ts2._dt


# =============================================================================
# 时间戳信息
# =============================================================================

def ts获取星期(ts):
    """获取星期（1-7，1=星期一）"""
    weekday = ts._dt.weekday()  # 0=Monday
    return weekday + 1


def ts获取星期名称(ts):
    """获取星期名称（中文）"""
    名称 = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    return 名称[ts._dt.weekday()]


def ts获取月份名称(ts):
    """获取月份名称（中文）"""
    名称 = ['一月', '二月', '三月', '四月', '五月', '六月',
            '七月', '八月', '九月', '十月', '十一月', '十二月']
    return 名称[ts._dt.month - 1]


def ts获取月份天数(ts):
    """获取月份的天数"""
    return _calendar.monthrange(ts._dt.year, ts._dt.month)[1]


def ts是否闰年(ts):
    """判断是否闰年"""
    return _calendar.isleap(ts._dt.year)


def tsIsWorkday(ts):
    """判断是否为工作日"""
    return ts._dt.weekday() < 5


def ts获取季度(ts):
    """获取季度（1-4）"""
    return (ts._dt.month - 1) // 3 + 1


def ts获取周数(ts):
    """获取周数（ISO 周数）"""
    return ts._dt.isocalendar()[1]


# =============================================================================
# 时间戳复制与转换
# =============================================================================

def ts复制(ts):
    """复制时间戳"""
    return _TimeStamp(ts._dt)


def ts设置时区(ts, 时区):
    """设置时区"""
    new_ts = ts复制(ts)
    new_ts._dt = new_ts._dt.replace(tzinfo=时区)
    return new_ts


def ts转为UTC(ts):
    """转为 UTC 时间"""
    new_ts = ts复制(ts)
    if new_ts._dt.tzinfo:
        new_ts._dt = new_ts._dt.astimezone(_datetime.timezone.utc)
    else:
        new_ts._dt = new_ts._dt.replace(tzinfo=_datetime.timezone.utc)
    return new_ts


# =============================================================================
# 时间戳增减
# =============================================================================

def ts添加天数(ts, 天数):
    return _TimeStamp(ts._dt + _datetime.timedelta(days=天数))


def ts添加小时(ts, 小时):
    return _TimeStamp(ts._dt + _datetime.timedelta(hours=小时))


def ts添加分钟(ts, 分钟):
    return _TimeStamp(ts._dt + _datetime.timedelta(minutes=分钟))


def ts添加秒(ts, 秒):
    return _TimeStamp(ts._dt + _datetime.timedelta(seconds=秒))


def ts添加月数(ts, 月数):
    """添加月数"""
    total_months = ts._dt.year * 12 + (ts._dt.month - 1) + 月数
    year = total_months // 12
    month = total_months % 12 + 1
    day = min(ts._dt.day, _calendar.monthrange(year, month)[1])
    return _TimeStamp(ts._dt.replace(year=year, month=month, day=day,
                                      hour=ts._dt.hour, minute=ts._dt.minute,
                                      second=ts._dt.second))


def ts添加年数(ts, 年数):
    return ts添加月数(ts, 年数 * 12)


# =============================================================================
# 日期范围
# =============================================================================

class _DateRange:
    """日期范围"""
    def __init__(self, start, end):
        self._start = start
        self._end = end

    def start(self):
        return self._start

    def end(self):
        return self._end


def 创建日期范围(开始, 结束):
    """创建日期范围"""
    return _DateRange(开始, 结束)


def 创建日期范围从数量(开始, 数量, 单位='days', 步长=1):
    """从开始时间和数量创建日期范围"""
    if 单位 == 'days':
        delta = _datetime.timedelta(days=步长 * (数量 - 1))
    elif 单位 == 'hours':
        delta = _datetime.timedelta(hours=步长 * (数量 - 1))
    elif 单位 == 'weeks':
        delta = _datetime.timedelta(weeks=步长 * (数量 - 1))
    else:
        delta = _datetime.timedelta(days=步长 * (数量 - 1))
    end_dt = 开始._dt + delta
    return _DateRange(开始, _TimeStamp(end_dt))


def 创建工作日范围(开始, 结束):
    """创建工作日范围（仅包含工作日）"""
    timestamps = []
    current = 开始._dt
    end_dt = 结束._dt
    while current <= end_dt:
        if current.weekday() < 5:
            timestamps.append(_TimeStamp(current))
        current += _datetime.timedelta(days=1)
    return timestamps


# =============================================================================
# 日期范围操作
# =============================================================================

def dr获取时间戳列表(dr):
    """获取日期范围内所有时间戳列表"""
    if not isinstance(dr, _DateRange):
        raise Exception("dr获取时间戳列表失败: 不是日期范围对象")
    timestamps = []
    current = dr._start._dt
    end_dt = dr._end._dt
    while current <= end_dt:
        timestamps.append(_TimeStamp(current))
        current += _datetime.timedelta(days=1)
    return timestamps


def dr长度(dr):
    """获取日期范围天数"""
    if not isinstance(dr, _DateRange):
        raise Exception("dr长度失败: 不是日期范围对象")
    delta = dr._end._dt - dr._start._dt
    return delta.days + 1


def dr包含(dr, ts):
    """判断日期范围是否包含指定时间戳"""
    if not isinstance(dr, _DateRange):
        raise Exception("dr包含失败: 不是日期范围对象")
    return dr._start._dt <= ts._dt <= dr._end._dt


# =============================================================================
# 持续时间
# =============================================================================

class _Duration:
    """持续时间"""
    def __init__(self, seconds=0):
        self._total_seconds = seconds

    def _to_timedelta(self):
        return _datetime.timedelta(seconds=self._total_seconds)


def 创建持续时间(秒=0, 分钟=0, 小时=0, 天数=0):
    """创建持续时间"""
    total = 秒 + 分钟 * 60 + 小时 * 3600 + 天数 * 86400
    return _Duration(total)


def durToMs(dur):
    """持续时间转为毫秒"""
    return int(dur._total_seconds * 1000)


def dur总秒数(dur):
    """获取总秒数"""
    return dur._total_seconds


def dur总分钟数(dur):
    """获取总分钟数"""
    return dur._total_seconds / 60.0


def dur总小时数(dur):
    """获取总小时数"""
    return dur._total_seconds / 3600.0


def dur总天数(dur):
    """获取总天数"""
    return dur._total_seconds / 86400.0


def dur格式化(dur, 格式='%H:%M:%S'):
    """格式化持续时间"""
    total_sec = int(dur._total_seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    if 格式 == '%H:%M:%S':
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{hours}h{minutes}m{seconds}s"


# =============================================================================
# 时区
# =============================================================================

class _TimeZone:
    """时区对象"""
    def __init__(self, tz):
        self._tz = tz


def 创建时区(偏移小时, 偏移分钟=0):
    """创建时区"""
    offset = _datetime.timedelta(hours=偏移小时, minutes=偏移分钟)
    return _TimeZone(_datetime.timezone(offset))


def tz获取当前偏移(tz):
    """获取当前时区偏移（小时）"""
    offset = tz._tz.utcoffset(None)
    if offset is None:
        return 0
    return offset.total_seconds() / 3600


def tzIsDST(tz):
    """判断是否为夏令时"""
    # Python 的 timezone 对象不支持 DST 判断
    return False


# =============================================================================
# 日期偏移
# =============================================================================

class _DateOffset:
    """日期偏移"""
    def __init__(self, years=0, months=0, days=0):
        self.years = years
        self.months = months
        self.days = days


def 创建日期偏移(年=0, 月=0, 日=0):
    """创建日期偏移"""
    return _DateOffset(年, 月, 日)


def do应用(offset, ts):
    """应用日期偏移到时间戳"""
    if not isinstance(offset, _DateOffset):
        raise Exception("do应用失败: 不是日期偏移对象")
    return ts添加月数(ts添加天数(ts, offset.days), offset.months + offset.years * 12)


# =============================================================================
# 重采样器
# =============================================================================

class _Resampler:
    """重采样器"""
    def __init__(self, 数据, 频率):
        self._数据 = 数据
        self._频率 = 频率


def 创建重采样器(数据, 频率):
    """创建重采样器"""
    return _Resampler(数据, 频率)


def rs求和(rs):
    """重采样求和"""
    return _resample_apply(rs, sum)


def rs平均值(rs):
    """重采样平均值"""
    return _resample_apply(rs, lambda x: sum(x) / len(x) if x else 0)


def rs最小值(rs):
    """重采样最小值"""
    return _resample_apply(rs, min)


def rs最大值(rs):
    """重采样最大值"""
    return _resample_apply(rs, max)


def rs首值(rs):
    """重采样首值"""
    return _resample_apply(rs, lambda x: x[0] if x else None)


def rs末值(rs):
    """重采样末值"""
    return _resample_apply(rs, lambda x: x[-1] if x else None)


def rs计数(rs):
    """重采样计数"""
    return _resample_apply(rs, len)


def rs标准差(rs):
    """重采样标准差"""
    return _resample_apply(rs, _std_dev)


def rs前向填充(rs):
    """重采样前向填充"""
    result = []
    last_val = None
    for group in _resample_groups(rs):
        if group:
            last_val = group[-1]
            result.append(last_val)
        else:
            result.append(last_val)
    return result


def rs后向填充(rs):
    """重采样后向填充"""
    # 简单实现：后向填充
    groups = list(_resample_groups(rs))
    result = []
    next_val = None
    for i in range(len(groups) - 1, -1, -1):
        if groups[i]:
            next_val = groups[i][0]
        result.append(next_val)
    result.reverse()
    return result


def rs线性插值(rs):
    """重采样线性插值"""
    groups = list(_resample_groups(rs))
    result = []
    # 找到有值的索引
    valid_indices = [i for i, g in enumerate(groups) if g]
    if not valid_indices:
        return [None] * len(groups)

    for i in range(len(groups)):
        if groups[i]:
            result.append(groups[i][-1])
        else:
            # 找到前后的有效值进行线性插值
            before = [v for v in valid_indices if v < i]
            after = [v for v in valid_indices if v > i]
            if before and after:
                b_idx = before[-1]
                a_idx = after[0]
                b_val = groups[b_idx][-1]
                a_val = groups[a_idx][0]
                ratio = (i - b_idx) / (a_idx - b_idx)
                result.append(b_val + (a_val - b_val) * ratio)
            elif before:
                result.append(groups[before[-1]][-1])
            elif after:
                result.append(groups[after[0]][0])
            else:
                result.append(None)
    return result


def rs应用(rs, 函数):
    """重采样应用自定义函数"""
    return _resample_apply(rs, 函数)


# =============================================================================
# 重采样内部函数
# =============================================================================

def _resample_groups(rs):
    """将数据按频率分组"""
    data = rs._数据
    freq = rs._频率
    if not data:
        return []
    # 简单按频率分块
    n = max(1, int(freq))
    groups = [data[i:i + n] for i in range(0, len(data), n)]
    return groups


def _resample_apply(rs, func):
    """对重采样组应用函数"""
    return [func(g) for g in _resample_groups(rs)]


def _std_dev(values):
    """计算标准差"""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return _math.sqrt(variance)