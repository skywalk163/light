"""
日期时间模块 - 时间差、时区、格式解析

提供丰富的日期时间处理功能，包括：
- 日期时间对象创建与操作
- 时间差计算
- 时区转换
- 格式解析与格式化
- 日期运算与比较
- 农历日期与节假日
- 日历生成
- 灵活的中文日期解析
"""
import time
import datetime
import calendar as _calendar
import re
from datetime import datetime as _datetime, timedelta as _timedelta, timezone as _timezone, date as _date, time as _time
from typing import Tuple, Union, Optional, List, Dict

try:
    from lunardate import LunarDate as _LunarDate
    _HAS_LUNAR = True
except ImportError:
    _HAS_LUNAR = False

# =============================================================================
# 常量
# =============================================================================

星期名称列表 = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
星期全称列表 = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
月份名称列表 = ['一月', '二月', '三月', '四月', '五月', '六月',
               '七月', '八月', '九月', '十月', '十一月', '十二月']

# 常用时区偏移（秒）
_UTC8 = _timedelta(hours=8)
_UTC9 = _timedelta(hours=9)
_UTC0 = _timedelta(hours=0)
_UTC5 = _timedelta(hours=-5)
_UTC4 = _timedelta(hours=-4)

# =============================================================================
# 农历数据表（1900-2100年）
# 编码方式：每个整数表示一年的农历信息
#   - Bits 0-3: 闰月(0=无闰月, 1-12=闰月月份)
#   - Bit 4: 闰月天数(0=29, 1=30)
#   - Bits 5-16: 12位表示1-12月大小月(1=30天, 0=29天)
# =============================================================================

_LUNAR_YEAR_INFO = (
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,  # 1900-1909
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,  # 1910-1919
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,  # 1920-1929
    0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,  # 1930-1939
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,  # 1940-1949
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0,  # 1950-1959
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,  # 1960-1969
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,  # 1970-1979
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,  # 1980-1989
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0,  # 1990-1999
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,  # 2000-2009
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,  # 2010-2019
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,  # 2020-2029
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,  # 2030-2039
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,  # 2040-2049
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06aa0, 0x1a6c4, 0x0aae0,  # 2050-2059
    0x092e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,  # 2060-2069
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,  # 2070-2079
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,  # 2080-2089
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a4d0, 0x0d150, 0x0f252,  # 2090-2099
    0x0d520,  # 2100
)

# 天干地支
天干 = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
地支 = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
生肖 = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']


# =============================================================================
# 辅助函数
# =============================================================================

def _农历年份信息(农历年: int) -> int:
    """获取农历年份的编码信息"""
    idx = 农历年 - 1900
    if 0 <= idx < len(_LUNAR_YEAR_INFO):
        return _LUNAR_YEAR_INFO[idx]
    raise ValueError(f"农历数据不支持 {农历年} 年（仅支持1900-2100年）")


def _农历闰月(农历年: int) -> int:
    """返回农历年的闰月月份（0=无闰月）"""
    return _农历年份信息(农历年) & 0xf


def _农历闰月天数(农历年: int) -> int:
    """返回农历年闰月的天数"""
    if _农历闰月(农历年) == 0:
        return 0
    return 30 if (_农历年份信息(农历年) & 0x10) else 29


def _农历月天数(农历年: int, 农历月: int) -> int:
    """返回农历年指定月的天数"""
    if _农历年份信息(农历年) & (0x10000 >> (12 - 农历月)):
        return 30
    return 29


def _农历年总天数(农历年: int) -> int:
    """返回农历年总天数"""
    total = 0
    for m in range(1, 13):
        total += _农历月天数(农历年, m)
    闰月 = _农历闰月(农历年)
    if 闰月 > 0:
        total += _农历闰月天数(农历年)
    return total


# =============================================================================
# 农历日期类
# =============================================================================

class 农历日期:
    """农历日期类"""

    def __init__(self, 年: int, 月: int, 日: int, 是否闰月: bool = False):
        self.年 = 年
        self.月 = 月
        self.日 = 日
        self.是否闰月 = 是否闰月
        self._验证()

    def _验证(self):
        if not (1900 <= self.年 <= 2100):
            raise ValueError(f"农历年份超出范围(1900-2100): {self.年}")
        if not (1 <= self.月 <= 12):
            raise ValueError(f"农历月份超出范围(1-12): {self.月}")
        if _HAS_LUNAR:
            try:
                _LunarDate(self.年, self.月, self.日, self.是否闰月)
            except ValueError as e:
                raise ValueError(f"无效的农历日期: {e}")
        else:
            # 降级使用内置数据表
            最大天数 = _农历月天数(self.年, self.月)
            if not (1 <= self.日 <= 最大天数):
                raise ValueError(f"农历{self.年}年{self.月}月天数范围为1-{最大天数}，当前: {self.日}")
            if self.是否闰月:
                闰月 = _农历闰月(self.年)
                if 闰月 != self.月:
                    raise ValueError(f"{self.年}年的闰月是{闰月}月，不是{self.月}月")

    def 天干地支年(self) -> str:
        """返回天干地支纪年"""
        年偏移 = (self.年 - 4) % 60
        return 天干[年偏移 % 10] + 地支[年偏移 % 12]

    def 生肖年(self) -> str:
        """返回生肖"""
        return 生肖[(self.年 - 4) % 12]

    def 格式化(self, 格式: str = '农历%Y年%m月%d日') -> str:
        """格式化农历日期"""
        result = 格式.replace('%Y', str(self.年))
        result = result.replace('%m', str(self.月))
        result = result.replace('%d', str(self.日))
        result = result.replace('%G', self.天干地支年())
        result = result.replace('%S', self.生肖年())
        if self.是否闰月:
            result = result.replace('%L', '闰')
        else:
            result = result.replace('%L', '')
        return result

    def __repr__(self) -> str:
        前缀 = '闰' if self.是否闰月 else ''
        return f'农历{self.年}年{前缀}{self.月}月{self.日}日'

    def __eq__(self, 其他) -> bool:
        if not isinstance(其他, 农历日期):
            return False
        return (self.年 == 其他.年 and self.月 == 其他.月
                and self.日 == 其他.日 and self.是否闰月 == 其他.是否闰月)


# =============================================================================
# 现有类：时间差
# =============================================================================

class 时间差:
    """时间差类"""

    def __init__(self, 天数: int = 0, 秒数: int = 0, **参数):
        # 处理中文参数名 → Python参数名
        if '毫秒' in 参数:
            参数['milliseconds'] = 参数.pop('毫秒')
        if '微秒' in 参数:
            参数['microseconds'] = 参数.pop('微秒')
        if '分钟' in 参数:
            参数['minutes'] = 参数.pop('分钟')
        if '小时' in 参数:
            参数['hours'] = 参数.pop('小时')
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

    def __bool__(self) -> bool:
        return bool(self._时间差)

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

    def 总小时数(self) -> float:
        """返回总小时数"""
        return self._时间差.total_seconds() / 3600

    def 总分钟数(self) -> float:
        """返回总分钟数"""
        return self._时间差.total_seconds() / 60

    def 总毫秒数(self) -> float:
        """返回总毫秒数"""
        return self._时间差.total_seconds() * 1000

    def 中文描述(self) -> str:
        """返回人类可读的中文描述"""
        总秒 = abs(int(self._时间差.total_seconds()))
        负号 = '前' if self._时间差.total_seconds() < 0 else ''

        if 总秒 < 60:
            return f'{总秒}秒{负号}'
        elif 总秒 < 3600:
            return f'{总秒 // 60}分钟{负号}'
        elif 总秒 < 86400:
            小时 = 总秒 // 3600
            分钟 = (总秒 % 3600) // 60
            if 分钟:
                return f'{小时}小时{分钟}分钟{负号}'
            return f'{小时}小时{负号}'
        elif 总秒 < 604800:
            天 = 总秒 // 86400
            return f'{天}天{负号}'
        elif 总秒 < 2592000:
            周 = 总秒 // 604800
            return f'{周}周{负号}'
        elif 总秒 < 31536000:
            月 = 总秒 // 2592000
            return f'{月}个月{负号}'
        else:
            年 = 总秒 // 31536000
            return f'{年}年{负号}'

    def 成份(self) -> dict:
        """返回时间差的各成分（天、小时、分钟、秒）"""
        总秒 = int(self._时间差.total_seconds())
        天, 余 = divmod(abs(总秒), 86400)
        时, 余 = divmod(余, 3600)
        分, 秒 = divmod(余, 60)
        符号 = -1 if 总秒 < 0 else 1
        return {'天': 符号 * 天, '小时': 时, '分钟': 分, '秒': 秒}


# =============================================================================
# 现有类：日期时间（增强）
# =============================================================================

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

    def __hash__(self) -> int:
        return hash(self._日期时间)

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
        return 星期名称列表[self.星期()]

    def 周几全称(self) -> str:
        """返回中文星期全称"""
        return 星期全称列表[self.星期()]

    def 季度(self) -> int:
        """返回季度"""
        return (self.月() - 1) // 3 + 1

    def 年中第几天(self) -> int:
        """返回年中第几天"""
        return self._日期时间.timetuple().tm_yday

    def 周中第几天(self) -> int:
        """返回周中第几天（1=周一，7=周日）"""
        return self._日期时间.isoweekday()

    def ISO日历(self) -> tuple:
        """返回ISO日历 (ISO年, ISO周, ISO周中第几天)"""
        return self._日期时间.isocalendar()

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

    def 转为日期(self) -> '日期':
        """转为日期对象"""
        return 日期._from_date(self._日期时间.date())

    def 转为时间(self) -> '时间':
        """转为时间对象"""
        return 时间._from_time(self._日期时间.timetz() if self._日期时间.tzinfo else self._日期时间.time())

    def 转农历(self) -> 农历日期:
        """公历日期转农历日期"""
        return 公历转农历(self.年(), self.月(), self.日())

    def 相对时间描述(self) -> str:
        """返回相对于现在的描述"""
        return 获取相对时间描述(self)

    def ISO8601(self) -> str:
        """返回ISO 8601格式字符串"""
        return self._日期时间.isoformat()

    def 复制(self) -> '日期时间':
        """复制日期时间对象"""
        return 日期时间._from_datetime(self._日期时间.replace())


# =============================================================================
# 新增：日期类（纯日期，不含时间）
# =============================================================================

class 日期:
    """日期类（纯日期，不含时间）"""

    def __init__(self, 年: int, 月: int, 日: int):
        self._日期 = _date(年, 月, 日)

    def __add__(self, 其他: 时间差) -> '日期':
        return 日期._from_date(self._日期 + 其他._时间差)

    def __sub__(self, 其他: Union['日期', 时间差]) -> Union['时间差', '日期']:
        if isinstance(其他, 日期):
            return 时间差._from_timedelta(self._日期 - 其他._日期)
        return 日期._from_date(self._日期 - 其他._时间差)

    def __lt__(self, 其他: '日期') -> bool:
        return self._日期 < 其他._日期

    def __le__(self, 其他: '日期') -> bool:
        return self._日期 <= 其他._日期

    def __gt__(self, 其他: '日期') -> bool:
        return self._日期 > 其他._日期

    def __ge__(self, 其他: '日期') -> bool:
        return self._日期 >= 其他._日期

    def __eq__(self, 其他: '日期') -> bool:
        return self._日期 == 其他._日期

    def __repr__(self) -> str:
        return f'日期({self.年}, {self.月}, {self.日})'

    def __hash__(self) -> int:
        return hash(self._日期)

    @classmethod
    def _from_date(cls, d: _date) -> '日期':
        实例 = cls.__new__(cls)
        实例._日期 = d
        return 实例

    @property
    def 年(self) -> int:
        return self._日期.year

    @property
    def 月(self) -> int:
        return self._日期.month

    @property
    def 日(self) -> int:
        return self._日期.day

    def 星期(self) -> int:
        """返回星期几（0=周一，6=周日）"""
        return self._日期.weekday()

    def 周几(self) -> str:
        """返回中文星期"""
        return 星期名称列表[self.星期()]

    def 周几全称(self) -> str:
        """返回中文星期全称"""
        return 星期全称列表[self.星期()]

    def 周中第几天(self) -> int:
        """返回周中第几天（1=周一，7=周日）"""
        return self._日期.isoweekday()

    def ISO日历(self) -> tuple:
        """返回ISO日历 (ISO年, ISO周, ISO周中第几天)"""
        return self._日期.isocalendar()

    def 年中第几天(self) -> int:
        """返回年中第几天"""
        return self._日期.timetuple().tm_yday

    def 季度(self) -> int:
        """返回季度"""
        return (self.月 - 1) // 3 + 1

    def 是否闰年(self) -> bool:
        """是否为闰年"""
        return 判断闰年(self.年)

    def 是否工作日(self) -> bool:
        """是否为工作日"""
        return self.星期() < 5

    def 是否周末(self) -> bool:
        """是否为周末"""
        return self.星期() >= 5

    def 格式化(self, 格式字符串: str = '%Y-%m-%d') -> str:
        """格式化日期"""
        return self._日期.strftime(格式字符串)

    def 转为时间戳(self) -> float:
        """转为时间戳（当天00:00:00）"""
        return _datetime.combine(self._日期, _time()).timestamp()

    def 转农历(self) -> 农历日期:
        """公历日期转农历日期"""
        return 公历转农历(self.年, self.月, self.日)

    def 复制(self) -> '日期':
        """复制日期对象"""
        return 日期._from_date(self._日期)


# =============================================================================
# 新增：时间类（纯时间，不含日期）
# =============================================================================

class 时间:
    """时间类（纯时间，不含日期）"""

    def __init__(self, 时: int = 0, 分: int = 0, 秒: int = 0, 微秒: int = 0, 时区: _timezone = None):
        self._时间 = _time(时, 分, 秒, 微秒, tzinfo=时区)

    def __repr__(self) -> str:
        return f'时间({self.时}, {self.分}, {self.秒})'

    def __eq__(self, 其他: '时间') -> bool:
        return self._时间 == 其他._时间

    def __lt__(self, 其他: '时间') -> bool:
        return self._时间 < 其他._时间

    def __le__(self, 其他: '时间') -> bool:
        return self._时间 <= 其他._时间

    def __gt__(self, 其他: '时间') -> bool:
        return self._时间 > 其他._时间

    def __ge__(self, 其他: '时间') -> bool:
        return self._时间 >= 其他._时间

    def __hash__(self) -> int:
        return hash(self._时间)

    @classmethod
    def _from_time(cls, t: _time) -> '时间':
        实例 = cls.__new__(cls)
        实例._时间 = t
        return 实例

    @property
    def 时(self) -> int:
        return self._时间.hour

    @property
    def 分(self) -> int:
        return self._时间.minute

    @property
    def 秒(self) -> int:
        return self._时间.second

    @property
    def 微秒(self) -> int:
        return self._时间.microsecond

    @property
    def 时区(self) -> _timezone:
        return self._时间.tzinfo

    def 有时区(self) -> bool:
        """是否有时区信息"""
        return self._时间.tzinfo is not None

    def 格式化(self, 格式字符串: str = '%H:%M:%S') -> str:
        """格式化时间"""
        return self._时间.strftime(格式字符串)

    def 转换时区(self, 目标时区: _timezone) -> '时间':
        """转换时区"""
        if not self.有时区():
            raise ValueError("无时区信息的时间无法转换时区，请先附加时区")
        # 通过 datetime 中转
        dt = _datetime.combine(_date.today(), self._时间)
        dt = dt.astimezone(目标时区)
        return 时间._from_time(dt.timetz())

    def 附加时区(self, 时区: _timezone) -> '时间':
        """附加时区信息"""
        return 时间._from_time(self._时间.replace(tzinfo=时区))

    def 复制(self) -> '时间':
        """复制时间对象"""
        return 时间._from_time(self._时间)


# =============================================================================
# 新增：日期范围生成
# =============================================================================

def 日期范围(开始日期: '日期', 结束日期: '日期', 步长: int = 1) -> list:
    """生成日期范围列表"""
    结果 = []
    当前 = 开始日期
    while 当前 <= 结束日期:
        结果.append(当前)
        当前 = 日期._from_date(当前._日期 + _timedelta(days=步长))
    return 结果


def 月份范围(开始日期: '日期', 结束日期: '日期') -> list:
    """生成月份范围列表（每月第一天）"""
    结果 = []
    当前年, 当前月 = 开始日期.年, 开始日期.月
    结束年, 结束月 = 结束日期.年, 结束日期.月
    while (当前年 < 结束年) or (当前年 == 结束年 and 当前月 <= 结束月):
        结果.append(日期(当前年, 当前月, 1))
        当前月 += 1
        if 当前月 > 12:
            当前月 = 1
            当前年 += 1
    return 结果


# =============================================================================
# 新增：日期加减（月、年）
# =============================================================================

def 加月份(日期时间对象: '日期时间', 月数: int) -> '日期时间':
    """加月份（自动处理月末边界）"""
    年 = 日期时间对象.年() + (日期时间对象.月() + 月数 - 1) // 12
    月 = (日期时间对象.月() + 月数 - 1) % 12 + 1
    日 = min(日期时间对象.日(), _calendar.monthrange(年, 月)[1])
    return 日期时间(年, 月, 日, 日期时间对象.时(), 日期时间对象.分(), 日期时间对象.秒(), 日期时间对象.微秒(), 日期时间对象._日期时间.tzinfo)


def 减月份(日期时间对象: '日期时间', 月数: int) -> '日期时间':
    """减月份"""
    return 加月份(日期时间对象, -月数)


def 加年份(日期时间对象: '日期时间', 年数: int) -> '日期时间':
    """加年份"""
    return 加月份(日期时间对象, 年数 * 12)


def 减年份(日期时间对象: '日期时间', 年数: int) -> '日期时间':
    """减年份"""
    return 加月份(日期时间对象, -年数 * 12)


def 日期加月份(日期对象: '日期', 月数: int) -> '日期':
    """日期加月份"""
    年 = 日期对象.年 + (日期对象.月 + 月数 - 1) // 12
    月 = (日期对象.月 + 月数 - 1) % 12 + 1
    日 = min(日期对象.日, _calendar.monthrange(年, 月)[1])
    return 日期(年, 月, 日)


def 日期加年份(日期对象: '日期', 年数: int) -> '日期':
    """日期加年份"""
    return 日期加月份(日期对象, 年数 * 12)


# =============================================================================
# 农历公历互转
# =============================================================================

def 公历转农历(年: int, 月: int, 日: int) -> 农历日期:
    """公历转农历"""
    if not _HAS_LUNAR:
        raise RuntimeError("农历转换需要 lunardate 库，请执行: pip install lunardate")
    lunar = _LunarDate.from_solar_date(年, 月, 日)
    return 农历日期(lunar.year, lunar.month, lunar.day, lunar.isLeapMonth)


def 农历转公历(农历年: int, 农历月: int, 农历日: int, 是否闰月: bool = False) -> 日期:
    """农历转公历"""
    if not _HAS_LUNAR:
        raise RuntimeError("农历转换需要 lunardate 库，请执行: pip install lunardate")
    lunar = _LunarDate(农历年, 农历月, 农历日, 是否闰月)
    solar = lunar.to_solar_date()
    return 日期(solar.year, solar.month, solar.day)


# =============================================================================
# 中国节假日
# =============================================================================

# 固定公历节日
_固定公历节日 = {
    (1, 1): '元旦',
    (2, 14): '情人节',
    (3, 8): '妇女节',
    (3, 12): '植树节',
    (4, 1): '愚人节',
    (5, 1): '劳动节',
    (5, 4): '青年节',
    (6, 1): '儿童节',
    (7, 1): '建党节',
    (8, 1): '建军节',
    (9, 10): '教师节',
    (10, 1): '国庆节',
    (12, 25): '圣诞节',
}

# 农历节日（月, 日）
_农历节日 = {
    (1, 1): '春节',
    (1, 15): '元宵节',
    (5, 5): '端午节',
    (7, 7): '七夕节',
    (7, 15): '中元节',
    (8, 15): '中秋节',
    (9, 9): '重阳节',
    (12, 8): '腊八节',
    (12, 30): '除夕',  # 可能是29或30
}


def 获取公历节日(月: int, 日: int) -> str:
    """获取公历节日名称"""
    return _固定公历节日.get((月, 日), '')


def 获取农历节日(农历年: int, 农历月: int, 农历日: int) -> str:
    """获取农历节日名称"""
    # 特殊处理除夕（腊月最后一天）
    if 农历月 == 12:
        if _HAS_LUNAR:
            try:
                _LunarDate(农历年, 12, 30)
                腊月天数 = 30
            except ValueError:
                腊月天数 = 29
        else:
            腊月天数 = _农历月天数(农历年, 12)
        if 农历日 == 腊月天数:
            return '除夕'
    return _农历节日.get((农历月, 农历日), '')


def 中国节假日(年: int) -> dict:
    """返回指定年份的所有中国节假日"""
    节假日 = {}

    # 公历节日
    for (月, 日), 名称 in _固定公历节日.items():
        try:
            d = 日期(年, 月, 日)
            节假日[名称] = d
        except ValueError:
            pass

    # 农历节日
    for (农历月, 农历日), 名称 in _农历节日.items():
        try:
            if 名称 == '除夕':
                # 除夕是腊月最后一天
                if _HAS_LUNAR:
                    try:
                        _LunarDate(年, 12, 30)
                        腊月天数 = 30
                    except ValueError:
                        腊月天数 = 29
                else:
                    腊月天数 = _农历月天数(年, 12)
                d = 农历转公历(年, 12, 腊月天数)
            else:
                d = 农历转公历(年, 农历月, 农历日)
            节假日[名称] = d
        except (ValueError, IndexError):
            pass

    return 节假日


def 春节日期(年: int) -> 日期:
    """返回指定年份春节（农历正月初一）的公历日期"""
    return 农历转公历(年, 1, 1)


def 中秋日期(年: int) -> 日期:
    """返回指定年份中秋节（农历八月十五）的公历日期"""
    return 农历转公历(年, 8, 15)


def 端午日期(年: int) -> 日期:
    """返回指定年份端午节（农历五月初五）的公历日期"""
    return 农历转公历(年, 5, 5)


# =============================================================================
# 日历生成
# =============================================================================

def 生成月历(年: int, 月: int) -> list:
    """生成月历（按周分组）"""
    cal = _calendar.monthcalendar(年, 月)
    结果 = []
    for 周 in cal:
        周行 = []
        for 日 in 周:
            if 日 == 0:
                周行.append(None)
            else:
                周行.append(日期(年, 月, 日))
        结果.append(周行)
    return 结果


def 生成年历(年: int) -> dict:
    """生成年历"""
    return {m: 生成月历(年, m) for m in range(1, 13)}


def 生成月历文本(年: int, 月: int) -> str:
    """生成月历文本"""
    cal = _calendar.TextCalendar()
    return cal.formatmonth(年, 月)


# =============================================================================
# 灵活日期解析
# =============================================================================

# 常见日期格式
_常见日期格式 = [
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
    '%Y/%m/%d %H:%M:%S',
    '%Y/%m/%d %H:%M',
    '%Y/%m/%d',
    '%Y年%m月%d日 %H:%M:%S',
    '%Y年%m月%d日 %H:%M',
    '%Y年%m月%d日',
    '%Y.%m.%d',
    '%Y%m%d',
    '%Y%m%d%H%M%S',
    '%m-%d-%Y',
    '%m/%d/%Y',
    '%d-%m-%Y',
    '%d/%m/%Y',
    '%H:%M:%S',
    '%H:%M',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M:%S%z',
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%dT%H:%M:%S.%f%z',
]

# 中文相对时间模式
_相对时间模式 = re.compile(r'^([上下]个?)?(\d+)?\s*(秒|分钟|小时|时|天|日|周|星期|个月|月|年)\s*(前|后|内|之[前后])?$')


def 自动检测格式(日期字符串: str) -> str:
    """自动检测日期字符串的格式"""
    日期字符串 = 日期字符串.strip()

    # 尝试逐个格式匹配
    for 格式 in _常见日期格式:
        try:
            _datetime.strptime(日期字符串, 格式)
            return 格式
        except ValueError:
            continue

    # 尝试ISO 8601解析
    try:
        from datetime import fromisoformat
        fromisoformat(日期字符串)
        return 'ISO8601'
    except (ValueError, ImportError):
        pass

    return ''


def 解析日期字符串(字符串: str, 格式: str = '') -> 日期时间:
    """解析日期字符串，支持多种格式"""
    字符串 = 字符串.strip()

    if not 字符串:
        raise ValueError("日期字符串不能为空")

    # 如果指定了格式，直接使用
    if 格式:
        if 格式 == 'ISO8601':
            try:
                from datetime import fromisoformat
                return 日期时间._from_datetime(fromisoformat(字符串))
            except (ValueError, ImportError):
                pass
        return 日期时间._from_datetime(_datetime.strptime(字符串, 格式))

    # 自动检测格式
    检测到的格式 = 自动检测格式(字符串)
    if 检测到的格式:
        if 检测到的格式 == 'ISO8601':
            from datetime import fromisoformat
            return 日期时间._from_datetime(fromisoformat(字符串))
        return 日期时间._from_datetime(_datetime.strptime(字符串, 检测到的格式))

    # 尝试解析中文日期
    try:
        return 解析中文日期(字符串)
    except ValueError:
        pass

    # 尝试解析相对时间
    try:
        return 解析相对时间(字符串)
    except ValueError:
        pass

    raise ValueError(f"无法解析日期字符串: {字符串}")


def 解析中文日期(字符串: str) -> 日期时间:
    """解析中文日期字符串"""
    字符串 = 字符串.strip()

    # "昨天"、"今天"、"明天"
    if 字符串 == '今天':
        return 当前时间()
    elif 字符串 == '昨天':
        return 获取昨天()
    elif 字符串 == '明天':
        return 获取明天()
    elif 字符串 == '前天':
        return 减天数(当前时间(), 2)
    elif 字符串 == '后天':
        return 加天数(当前时间(), 2)

    # "上个月"、"下个月"
    if 字符串 == '上个月' or 字符串 == '上月':
        return 减月份(当前时间(), 1)
    elif 字符串 == '下个月' or 字符串 == '下月':
        return 加月份(当前时间(), 1)
    elif 字符串 == '上周' or 字符串 == '上个星期' or 字符串 == '上星期':
        return 减天数(当前时间(), 7)
    elif 字符串 == '下周' or 字符串 == '下个星期' or 字符串 == '下星期':
        return 加天数(当前时间(), 7)

    # "上周一"、"下周五"
    周匹配 = re.match(r'^([上下]个?)?(周|星期)([一二三四五六日天])$', 字符串)
    if 周匹配:
        方向 = 周匹配.group(1) or ''
        周名 = 周匹配.group(3)
        周映射 = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6}
        目标周几 = 周映射.get(周名, 0)
        今天 = 当前时间()
        当前周几 = 今天.星期()
        偏移 = 目标周几 - 当前周几
        if '上' in 方向:
            偏移 -= 7
        elif '下' in 方向:
            偏移 += 7
        return 加天数(今天, 偏移)

    # "2024年8月7日"、"2024年08月07日"
    中文日期匹配 = re.match(r'^(\d{1,4})年(\d{1,2})月(\d{1,2})日?\s*(\d{1,2})?[:：]?(\d{1,2})?[:：]?(\d{1,2})?$', 字符串)
    if 中文日期匹配:
        年 = int(中文日期匹配.group(1))
        月 = int(中文日期匹配.group(2))
        日 = int(中文日期匹配.group(3))
        时 = int(中文日期匹配.group(4) or 0)
        分 = int(中文日期匹配.group(5) or 0)
        秒 = int(中文日期匹配.group(6) or 0)
        return 日期时间(年, 月, 日, 时, 分, 秒)

    # "8月7日"
    简写日期匹配 = re.match(r'^(\d{1,2})月(\d{1,2})日?$', 字符串)
    if 简写日期匹配:
        今天 = 当前时间()
        月 = int(简写日期匹配.group(1))
        日 = int(简写日期匹配.group(2))
        return 日期时间(今天.年(), 月, 日)

    raise ValueError(f"无法解析中文日期: {字符串}")


# =============================================================================
# 时间格式转换
# =============================================================================

def 时间戳转字符串友好(时间戳: float, 包含时间: bool = True) -> str:
    """时间戳转友好字符串"""
    dt = _datetime.fromtimestamp(时间戳)
    if 包含时间:
        return dt.strftime('%Y年%m月%d日 %H:%M:%S')
    return dt.strftime('%Y年%m月%d日')


def 时间戳转ISO8601(时间戳: float) -> str:
    """时间戳转ISO 8601字符串"""
    return _datetime.fromtimestamp(时间戳).isoformat()


def 解析ISO8601(字符串: str) -> 日期时间:
    """解析ISO 8601字符串"""
    try:
        from datetime import fromisoformat
        return 日期时间._from_datetime(fromisoformat(字符串))
    except (ValueError, ImportError):
        pass
    # 手动解析常见ISO 8601格式
    # 处理带Z的UTC时间
    s = 字符串.replace('Z', '+00:00')
    try:
        return 日期时间._from_datetime(_datetime.strptime(s, '%Y-%m-%dT%H:%M:%S%z'))
    except ValueError:
        pass
    # 尝试无时区格式
    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
        try:
            return 日期时间._from_datetime(_datetime.strptime(字符串, fmt))
        except ValueError:
            continue
    raise ValueError(f"无法解析ISO 8601字符串: {字符串}")


# =============================================================================
# 时间段/持续时间
# =============================================================================

def 计算持续时间(开始: 日期时间, 结束: 日期时间) -> 时间差:
    """计算两个日期时间之间的持续时间"""
    return 结束 - 开始


def 格式化持续时间(时间差对象: 时间差, 详细: bool = False) -> str:
    """格式化持续时间，返回人类可读字符串"""
    return 时间差对象.中文描述()


def 计算工作日(开始日期: 日期, 结束日期: 日期, 节假日列表: list = None) -> int:
    """计算两个日期之间的工作日天数（排除节假日）"""
    天数 = 0
    当前 = 开始日期
    while 当前 <= 结束日期:
        if 当前.是否工作日():
            if 节假日列表 and 当前 in 节假日列表:
                pass  # 跳过节假日
            else:
                天数 += 1
        当前 = 日期._from_date(当前._日期 + _timedelta(days=1))
    return 天数


def 计算年龄(出生日期: 日期, 截止日期: 日期 = None) -> int:
    """计算年龄"""
    if 截止日期 is None:
        截止日期 = 日期._from_date(_date.today())
    年龄 = 截止日期.年 - 出生日期.年
    # 调整：如果还没过生日
    if (截止日期.月, 截止日期.日) < (出生日期.月, 出生日期.日):
        年龄 -= 1
    return 年龄


# =============================================================================
# 现有函数（保持向后兼容）
# =============================================================================

def 当前时间() -> 日期时间:
    """返回当前日期时间（本地时区）"""
    return 日期时间._from_datetime(_datetime.now())


def 当前UTC时间() -> 日期时间:
    """返回当前UTC时间"""
    return 日期时间._from_datetime(_datetime.now(_timezone.utc))


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
    """返回纽约时间（UTC-5，标准时间）"""
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
            return 减月份(当前, 月数)
        elif '年' in 相对时间:
            年数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 加年份(当前, -年数)

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
            return 加月份(当前, 月数)
        elif '年' in 相对时间:
            年数 = int(''.join(filter(str.isdigit, 相对时间)))
            return 加年份(当前, 年数)

    return 当前


# =============================================================================
# 新增：时区转换快捷函数
# =============================================================================

常用时区 = {
    '北京时间': _timezone(_timedelta(hours=8)),
    'UTC': _timezone.utc,
    '纽约时间': _timezone(_timedelta(hours=-5)),
    '伦敦时间': _timezone(_timedelta(hours=0)),
    '东京时间': _timezone(_timedelta(hours=9)),
    '香港时间': _timezone(_timedelta(hours=8)),
    '巴黎时间': _timezone(_timedelta(hours=1)),
    '悉尼时间': _timezone(_timedelta(hours=11)),
    '洛杉矶时间': _timezone(_timedelta(hours=-8)),
    '新加坡时间': _timezone(_timedelta(hours=8)),
    '印度时间': _timezone(_timedelta(hours=5, minutes=30)),
}


def 获取时区(时区名称: str) -> _timezone:
    """通过名称获取时区对象"""
    时区名称 = 时区名称.strip()
    if 时区名称 in 常用时区:
        return 常用时区[时区名称]
    # 尝试解析UTC偏移
    m = re.match(r'^UTC([+-])(\d{1,2})(?::?(\d{2}))?$', 时区名称)
    if m:
        符号 = 1 if m.group(1) == '+' else -1
        小时 = int(m.group(2))
        分钟 = int(m.group(3) or 0)
        return _timezone(_timedelta(hours=符号 * 小时, minutes=符号 * 分钟))
    raise ValueError(f"未知时区名称: {时区名称}")


def 时区转换(日期时间对象: 日期时间, 目标时区: _timezone) -> 日期时间:
    """时区转换"""
    return 日期时间对象.转换时区(目标时区)


# =============================================================================
# 新增：创建快捷函数
# =============================================================================

def 创建日期(年: int, 月: int, 日: int) -> 日期:
    """创建日期对象"""
    return 日期(年, 月, 日)


def 创建时间(时: int = 0, 分: int = 0, 秒: int = 0, 微秒: int = 0, 时区: _timezone = None) -> 时间:
    """创建时间对象"""
    return 时间(时, 分, 秒, 微秒, 时区)


def 创建日期时间(年: int, 月: int, 日: int, 时: int = 0, 分: int = 0, 秒: int = 0, 微秒: int = 0, 时区: _timezone = None) -> 日期时间:
    """创建日期时间对象"""
    return 日期时间(年, 月, 日, 时, 分, 秒, 微秒, 时区)


def 创建时间差(天: int = 0, 小时: int = 0, 分钟: int = 0, 秒: int = 0, 毫秒: int = 0) -> 时间差:
    """创建时间差对象"""
    return 时间差(天数=天, 秒数=秒 + 分钟 * 60 + 小时 * 3600, 毫秒=毫秒)


# =============================================================================
# 新增：Unix时间戳转换
# =============================================================================

def Unix时间戳转日期时间(时间戳: float, 时区: _timezone = None) -> 日期时间:
    """Unix时间戳转日期时间"""
    return 从时间戳(时间戳, 时区)


def 日期时间转Unix时间戳(dt: Union[日期时间, _datetime]) -> float:
    """日期时间转Unix时间戳"""
    if isinstance(dt, 日期时间):
        return dt.转为时间戳()
    return dt.timestamp()


# =============================================================================
# 测试兼容 API（phase2 测试期望的函数名，兼容 Python datetime 和光明日期时间）
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
    """日期时间转字符串（兼容 Python datetime 和光明日期时间）"""
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


def _get_dt_field(dt, py_attr: str, light_method: str):
    """从 Python datetime 或光明日期时间获取字段"""
    if isinstance(dt, 日期时间):
        return getattr(dt, light_method)()
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
    if isinstance(dt, 日期时间):
        return dt.周几()
    if isinstance(dt, 日期):
        return dt.周几()
    return 星期名称列表[dt.weekday()]


def 是否闰年(年) -> bool:
    """是否闰年"""
    if isinstance(年, (日期时间, _datetime)):
        年 = 年.year if not isinstance(年, 日期时间) else 年.年()
    return (年 % 4 == 0 and 年 % 100 != 0) or (年 % 400 == 0)


def 添加天数(dt, 天数: int):
    """添加天数（兼容 Python datetime 和光明日期时间）"""
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