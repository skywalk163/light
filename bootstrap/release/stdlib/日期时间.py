"""
日期时间模块 - 时间差、时区、格式解析

提供丰富的日期时间处理功能，包括：
- 日期时间对象创建与操作
- 时间差计算
- 时区转换
- 格式解析与格式化
- 日期运算与比较
"""
import time
import datetime
from datetime import datetime as _datetime, timedelta as _timedelta, timezone as _timezone
from typing import Tuple, Union, Optional


class 时间差:
    """时间差类"""
    
    def __init__(self, 天数: int = 0, 秒数: int = 0, **参数):
        self._时间差 = _timedelta(days=天数, seconds=秒数, **参数)
    
    def __add__(self, 其他: Union['日期时间', '时间差']) -> Union['日期时间', '时间差']:
        if isinstance(其他, 日期时间):
            return 日期时间._from_datetime(其他._日期时间 + self._时间差)
        return 时间差._from_timedelta(self._时间差 + 其他._时间差)
    
    def __sub__(self, 其他: '时间差') -> '时间差':
        return 时间差._from_timedelta(self._时间差 - 其他._时间差)
    
    def __neg__(self) -> '时间差':
        return 时间差._from_timedelta(-self._时间差)
    
    def __mul__(self, 标量: float) -> '时间差':
        return 时间差._from_timedelta(self._时间差 * 标量)
    
    def __truediv__(self, 其他: Union['时间差', float]) -> Union[float, '时间差']:
        if isinstance(其他, 时间差):
            return self._时间差 / 其他._时间差
        return 时间差._from_timedelta(self._时间差 / 其他)
    
    def __repr__(self) -> str:
        return f'时间差({self.天数()}天, {self.秒数()}秒)'
    
    @classmethod
    def _from_timedelta(cls, td: _timedelta) -> '时间差':
        实例 = cls.__new__(cls)
        实例._时间差 = td
        return 实例
    
    def 天数(self) -> float:
        """返回总天数"""
        return self._时间差.total_seconds() / (24 * 60 * 60)
    
    def 总秒数(self) -> float:
        """返回总秒数"""
        return self._时间差.total_seconds()
    
    def 秒数(self) -> int:
        """返回秒数部分"""
        return self._时间差.seconds % 60
    
    def 分钟数(self) -> int:
        """返回分钟数部分"""
        return (self._时间差.seconds // 60) % 60
    
    def 小时数(self) -> int:
        """返回小时数部分"""
        return self._时间差.seconds // (60 * 60)
    
    def 周数(self) -> float:
        """返回周数"""
        return self.天数() / 7


class 日期时间:
    """日期时间类"""
    
    def __init__(self, 年: int, 月: int, 日: int, 时: int = 0, 分: int = 0, 秒: int = 0, 微秒: int = 0, 时区: _timezone = None):
        self._日期时间 = _datetime(年, 月, 日, 时, 分, 秒, 微秒, tzinfo=时区)
    
    def __add__(self, 其他: 时间差) -> '日期时间':
        return 日期时间._from_datetime(self._日期时间 + 其他._时间差)
    
    def __sub__(self, 其他: Union['日期时间', 时间差]) -> Union['时间差', '日期时间']:
        if isinstance(其他, 日期时间):
            return 时间差._from_timedelta(self._日期时间 - 其他._日期时间)
        return 日期时间._from_datetime(self._日期时间 - 其他._时间差)
    
    def __lt__(self, 其他: '日期时间') -> bool:
        return self._日期时间 < 其他._日期时间
    
    def __le__(self, 其他: '日期时间') -> bool:
        return self._日期时间 <= 其他._日期时间
    
    def __gt__(self, 其他: '日期时间') -> bool:
        return self._日期时间 > 其他._日期时间
    
    def __ge__(self, 其他: '日期时间') -> bool:
        return self._日期时间 >= 其他._日期时间
    
    def __eq__(self, 其他: '日期时间') -> bool:
        return self._日期时间 == 其他._日期时间
    
    def __repr__(self) -> str:
        return f'日期时间({self.年()}, {self.月()}, {self.日()}, {self.时()}, {self.分()}, {self.秒()})'
    
    @classmethod
    def _from_datetime(cls, dt: _datetime) -> '日期时间':
        实例 = cls.__new__(cls)
        实例._日期时间 = dt
        return 实例
    
    def 年(self) -> int:
        return self._日期时间.year
    
    def 月(self) -> int:
        return self._日期时间.month
    
    def 日(self) -> int:
        return self._日期时间.day
    
    def 时(self) -> int:
        return self._日期时间.hour
    
    def 分(self) -> int:
        return self._日期时间.minute
    
    def 秒(self) -> int:
        return self._日期时间.second
    
    def 微秒(self) -> int:
        return self._日期时间.microsecond
    
    def 星期(self) -> int:
        """返回星期几（0=周一，6=周日）"""
        return self._日期时间.weekday()
    
    def 周几(self) -> str:
        """返回中文星期"""
        星期列表 = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        return 星期列表[self.星期()]
    
    def 季度(self) -> int:
        """返回季度"""
        return (self.月() - 1) // 3 + 1
    
    def 年中第几天(self) -> int:
        """返回年中第几天"""
        return self._日期时间.timetuple().tm_yday
    
    def 周中第几天(self) -> int:
        """返回周中第几天（1=周一，7=周日）"""
        return self._日期时间.isoweekday()
    
    def 转换时区(self, 目标时区: _timezone) -> '日期时间':
        """转换时区"""
        return 日期时间._from_datetime(self._日期时间.astimezone(目标时区))
    
    def 转为本地时间(self) -> '日期时间':
        """转为本地时间"""
        return 日期时间._from_datetime(self._日期时间.astimezone())
    
    def 转为UTC(self) -> '日期时间':
        """转为UTC时间"""
        return 日期时间._from_datetime(self._日期时间.astimezone(_timezone.utc))
    
    def 是否夏令时(self) -> bool:
        """是否为夏令时"""
        return self._日期时间.dst() is not None and self._日期时间.dst() > _timedelta(0)
    
    def 格式化(self, 格式字符串: str = '%Y-%m-%d %H:%M:%S') -> str:
        """格式化日期时间"""
        return self._日期时间.strftime(格式字符串)
    
    def 转为时间戳(self) -> float:
        """转为时间戳"""
        return self._日期时间.timestamp()
    
    def 是否工作日(self) -> bool:
        """是否为工作日"""
        return self.星期() < 5


def 当前时间() -> 日期时间:
    """返回当前日期时间（本地时区）"""
    return 日期时间._from_datetime(_datetime.now())


def 当前UTC时间() -> 日期时间:
    """返回当前UTC时间"""
    return 日期时间._from_datetime(_datetime.utcnow())


def 从时间戳(时间戳: float, 时区: _timezone = None) -> 日期时间:
    """从时间戳创建日期时间"""
    if 时区 is None:
        return 日期时间._from_datetime(_datetime.fromtimestamp(时间戳))
    return 日期时间._from_datetime(_datetime.fromtimestamp(时间戳, 时区))


def 从字符串(字符串: str, 格式字符串: str = '%Y-%m-%d %H:%M:%S') -> 日期时间:
    """从字符串解析日期时间"""
    return 日期时间._from_datetime(_datetime.strptime(字符串, 格式字符串))


def 创建时区(偏移秒数: int) -> _timezone:
    """创建时区"""
    return _timezone(_timedelta(seconds=偏移秒数))


def 北京时间() -> _timezone:
    """返回北京时间（UTC+8）"""
    return 创建时区(8 * 60 * 60)


def 纽约时间() -> _timezone:
    """返回纽约时间（UTC-5）"""
    return 创建时区(-5 * 60 * 60)


def 伦敦时间() -> _timezone:
    """返回伦敦时间（UTC+0）"""
    return 创建时区(0)


def 东京时间() -> _timezone:
    """返回东京时间（UTC+9）"""
    return 创建时区(9 * 60 * 60)


def 计算时间差(开始时间: 日期时间, 结束时间: 日期时间) -> 时间差:
    """计算两个日期时间之间的时间差"""
    return 结束时间 - 开始时间


def 日期加减(日期时间: 日期时间, 天数: int = 0, 小时: int = 0, 分钟: int = 0, 秒: int = 0) -> 日期时间:
    """日期加减"""
    return 日期时间 + 时间差(天数=天数) + 时间差(秒数=小时 * 3600 + 分钟 * 60 + 秒)


def 加天数(日期时间: 日期时间, 天数: int) -> 日期时间:
    """加天数"""
    return 日期时间 + 时间差(天数=天数)


def 减天数(日期时间: 日期时间, 天数: int) -> 日期时间:
    """减天数"""
    return 日期时间 - 时间差(天数=天数)


def 加小时(日期时间: 日期时间, 小时: int) -> 日期时间:
    """加小时"""
    return 日期时间 + 时间差(秒数=小时 * 3600)


def 减小时(日期时间: 日期时间, 小时: int) -> 日期时间:
    """减小时"""
    return 日期时间 - 时间差(秒数=小时 * 3600)


def 获取今天() -> 日期时间:
    """获取今天"""
    return 当前时间()


def 获取昨天() -> 日期时间:
    """获取昨天"""
    return 减天数(当前时间(), 1)


def 获取明天() -> 日期时间:
    """获取明天"""
    return 加天数(当前时间(), 1)


def 获取本周一() -> 日期时间:
    """获取本周一"""
    今天 = 当前时间()
    return 减天数(今天, 今天.星期())


def 获取本周末() -> 日期时间:
    """获取本周末（周日）"""
    今天 = 当前时间()
    return 加天数(今天, 6 - 今天.星期())


def 获取本月第一天() -> 日期时间:
    """获取本月第一天"""
    今天 = 当前时间()
    return 日期时间(今天.年(), 今天.月(), 1)


def 获取本月最后一天() -> 日期时间:
    """获取本月最后一天"""
    今天 = 当前时间()
    下个月 = 今天.月() + 1
    年 = 今天.年()
    if 下个月 > 12:
        下个月 = 1
        年 += 1
    return 减天数(日期时间(年, 下个月, 1), 1)


def 获取本年第一天() -> 日期时间:
    """获取本年第一天"""
    今天 = 当前时间()
    return 日期时间(今天.年(), 1, 1)


def 获取本年最后一天() -> 日期时间:
    """获取本年最后一天"""
    今天 = 当前时间()
    return 日期时间(今天.年(), 12, 31)


def 计算两个日期天数差(日期1: 日期时间, 日期2: 日期时间) -> int:
    """计算两个日期之间的天数差"""
    差值 = 日期2 - 日期1
    return int(差值.天数())


def 计算工作日天数(开始日期: 日期时间, 结束日期: 日期时间) -> int:
    """计算两个日期之间的工作日天数"""
    天数 = 0
    当前日期 = 开始日期
    while 当前日期 <= 结束日期:
        if 当前日期.是否工作日():
            天数 += 1
        当前日期 = 加天数(当前日期, 1)
    return 天数


def 判断闰年(年: int) -> bool:
    """判断是否为闰年"""
    return (年 % 4 == 0 and 年 % 100 != 0) or (年 % 400 == 0)


def 获取月份天数(年: int, 月: int) -> int:
    """获取月份天数"""
    月份天数 = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if 月 == 2 and 判断闰年(年):
        return 29
    return 月份天数[月 - 1]


def 格式化时间戳(时间戳: float, 格式字符串: str = '%Y-%m-%d %H:%M:%S') -> str:
    """格式化时间戳"""
    return 从时间戳(时间戳).格式化(格式字符串)


def 解析相对时间(相对时间: str) -> 日期时间:
    """解析相对时间（如 "1小时前", "2天后"）"""
    当前 = 当前时间()
    相对时间 = 相对时间.strip()
    
    if '前' in 相对时间:
        if '秒' in 相对时间:
            秒数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 当前 - 时间差(秒数=秒数)
        elif '分钟' in 相对时间:
            分钟 = int(''.join(filter(str.isdigit, 相对时间)))
            return 当前 - 时间差(秒数=分钟 * 60)
        elif '小时' in 相对时间:
            小时 = int(''.join(filter(str.isdigit, 相对时间)))
            return 当前 - 时间差(秒数=小时 * 3600)
        elif '天' in 相对时间:
            天数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 当前 - 时间差(天数=天数)
        elif '周' in 相对时间:
            周数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 当前 - 时间差(天数=周数 * 7)
        elif '月' in 相对时间:
            月数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 日期时间(当前.年(), 当前.月() - 月数, 当前.日())
        elif '年' in 相对时间:
            年数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 日期时间(当前.年() - 年数, 当前.月(), 当前.日())
    
    elif '后' in 相对时间 or '内' in 相对时间:
        if '秒' in 相对时间:
            秒数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 当前 + 时间差(秒数=秒数)
        elif '分钟' in 相对时间:
            分钟 = int(''.join(filter(str.isdigit, 相对时间)))
            return 当前 + 时间差(秒数=分钟 * 60)
        elif '小时' in 相对时间:
            小时 = int(''.join(filter(str.isdigit, 相对时间)))
            return 当前 + 时间差(秒数=小时 * 3600)
        elif '天' in 相对时间:
            天数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 当前 + 时间差(天数=天数)
        elif '周' in 相对时间:
            周数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 当前 + 时间差(天数=周数 * 7)
        elif '月' in 相对时间:
            月数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 日期时间(当前.年(), 当前.月() + 月数, 当前.日())
        elif '年' in 相对时间:
            年数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 日期时间(当前.年() + 年数, 当前.月(), 当前.日())
    
    return 当前


# =============================================================================
# 测试兼容 API（phase2 测试期望的函数名，兼容 Python datetime 和段言日期时间）
# =============================================================================

def 日期转时间戳(dt) -> float:
    """日期转时间戳（别名，对应 STDLIB_VERB_ARITY 注册）"""
    if isinstance(dt, 日期时间):
        return dt.转为时间戳()
    return dt.timestamp()


def 星期几(dt=None) -> int:
    """返回星期几（0=周一，6=周日）（别名，对应 STDLIB_VERB_ARITY 注册）"""
    if dt is None:
        dt = _datetime.now()
    elif isinstance(dt, 日期时间):
        return dt.星期()
    return dt.weekday()


def 星期名称(dt=None) -> str:
    """返回星期名称（别名，对应 STDLIB_VERB_ARITY 注册）"""
    if dt is None:
        dt = _datetime.now()
    return 获取星期几名称(dt)


def 是否工作日(dt=None) -> bool:
    """判断是否为工作日（别名，对应 STDLIB_VERB_ARITY 注册）"""
    if dt is None:
        dt = _datetime.now()
    if isinstance(dt, 日期时间):
        return dt.是否工作日()
    return dt.weekday() < 5


def 是否周末(dt=None) -> bool:
    """判断是否为周末（别名，对应 STDLIB_VERB_ARITY 注册）"""
    return not 是否工作日(dt)


def 当前日期() -> _datetime:
    """返回当前日期（不含时间部分）"""
    return _datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def 当前时间戳() -> float:
    """返回当前 Unix 时间戳（秒）"""
    return time.time()


def 当前时间戳毫秒() -> int:
    """返回当前 Unix 时间戳（毫秒）"""
    return int(time.time() * 1000)


def 时间戳转字符串(时间戳: float, 格式: str = '%Y-%m-%d %H:%M:%S') -> str:
    """时间戳转字符串"""
    return _datetime.fromtimestamp(时间戳).strftime(格式)


def 日期时间转字符串(dt, 格式: str = '%Y-%m-%d %H:%M:%S') -> str:
    """日期时间转字符串（兼容 Python datetime 和段言日期时间）"""
    if isinstance(dt, 日期时间):
        return dt.格式化(格式)
    return dt.strftime(格式)


def 字符串转日期时间(字符串: str, 格式: str = '%Y-%m-%d %H:%M:%S') -> _datetime:
    """字符串转日期时间"""
    return _datetime.strptime(字符串, 格式)


def 字符串转日期(字符串: str, 格式: str = '%Y-%m-%d') -> _datetime:
    """字符串转日期"""
    return _datetime.strptime(字符串, 格式)


def 字符串转时间(字符串: str, 格式: str = '%H:%M:%S') -> _datetime:
    """字符串转时间"""
    return _datetime.strptime(字符串, 格式)


def _get_dt_field(dt, py_attr: str, duan_method: str):
    """从 Python datetime 或段言日期时间获取字段"""
    if isinstance(dt, 日期时间):
        return getattr(dt, duan_method)()
    return getattr(dt, py_attr)


def 获取年份(dt) -> int:
    """获取年份"""
    return _get_dt_field(dt, 'year', '年')


def 获取月份(dt) -> int:
    """获取月份"""
    return _get_dt_field(dt, 'month', '月')


def 获取日(dt) -> int:
    """获取日"""
    return _get_dt_field(dt, 'day', '日')


def 获取星期几名称(dt) -> str:
    """获取星期几名称"""
    星期列表 = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    if isinstance(dt, 日期时间):
        return dt.周几()
    return 星期列表[dt.weekday()]


def 是否闰年(年) -> bool:
    """是否闰年"""
    if isinstance(年, (日期时间, _datetime)):
        年 = 年.year if not isinstance(年, 日期时间) else 年.年()
    return (年 % 4 == 0 and 年 % 100 != 0) or (年 % 400 == 0)


def 添加天数(dt, 天数: int):
    """添加天数（兼容 Python datetime 和段言日期时间）"""
    if isinstance(dt, 日期时间):
        return 加天数(dt, 天数)
    return dt + _timedelta(days=天数)


def 时间差天数(dt1, dt2) -> int:
    """计算两个日期的天数差"""
    if isinstance(dt1, 日期时间):
        d1 = dt1._日期时间
    else:
        d1 = dt1
    if isinstance(dt2, 日期时间):
        d2 = dt2._日期时间
    else:
        d2 = dt2
    return abs((d2 - d1).days)


def 日期比较(dt1, dt2) -> int:
    """日期比较（返回 -1/0/1）"""
    if isinstance(dt1, 日期时间):
        d1 = dt1._日期时间
    else:
        d1 = dt1
    if isinstance(dt2, 日期时间):
        d2 = dt2._日期时间
    else:
        d2 = dt2
    if d1 < d2:
        return -1
    elif d1 > d2:
        return 1
    return 0


def 获取相对时间描述(dt) -> str:
    """获取相对时间描述"""
    if isinstance(dt, 日期时间):
        d = dt._日期时间
    else:
        d = dt
    当前 = _datetime.now()
    差值 = 当前 - d
    总秒数 = 差值.total_seconds()

    if 总秒数 < 0:
        总秒数 = -总秒数
        前缀 = ''
    else:
        前缀 = '前'

    if 总秒数 < 60:
        return f'{int(总秒数)}秒{前缀}'
    elif 总秒数 < 3600:
        return f'{int(总秒数 / 60)}分钟{前缀}'
    elif 总秒数 < 86400:
        return f'{int(总秒数 / 3600)}小时{前缀}'
    elif 总秒数 < 604800:
        return f'{int(总秒数 / 86400)}天{前缀}'
    elif 总秒数 < 2592000:
        return f'{int(总秒数 / 604800)}周{前缀}'
    elif 总秒数 < 31536000:
        return f'{int(总秒数 / 2592000)}个月{前缀}'
    else:
        return f'{int(总秒数 / 31536000)}年{前缀}'