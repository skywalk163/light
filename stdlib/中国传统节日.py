"""
段言标准库 - 中国传统节日查询模块

提供中国传统节日的查询功能，包括公历和农历节日的日期查询、
节日判断、倒计时计算等。

类：
    ChineseFestival: 中国传统节日查询器

用法:
    festival = ChineseFestival()
    festivals = festival.get_festivals(2026)
    date = festival.get_festival_date("春节", 2026)
    name = festival.is_festival("2026-01-01")
    month_festivals = festival.get_festivals_in_month(2026, 1)
    countdown = festival.get_festival_countdown("春节")
"""

import datetime
from typing import Dict, List, Optional


# =============================================================================
# 节日数据
# =============================================================================

# 春节日期（农历正月初一对应的公历日期，2024-2030年）
_SPRING_FESTIVAL_DATES = {
    2024: datetime.date(2024, 2, 10),
    2025: datetime.date(2025, 1, 29),
    2026: datetime.date(2026, 2, 17),
    2027: datetime.date(2027, 2, 6),
    2028: datetime.date(2028, 1, 26),
    2029: datetime.date(2029, 2, 13),
    2030: datetime.date(2030, 2, 3),
}

# 农历节日列表（月份, 日期, 名称, 说明）
_LUNAR_FESTIVALS = [
    (1, 1, "春节", "农历正月初一，中国传统新年"),
    (1, 15, "元宵节", "农历正月十五，又称上元节"),
    (5, 5, "端午节", "农历五月初五，纪念屈原"),
    (7, 7, "七夕节", "农历七月初七，中国传统情人节"),
    (8, 15, "中秋节", "农历八月十五，团圆节"),
    (9, 9, "重阳节", "农历九月初九，敬老节"),
    (12, 8, "腊八节", "农历十二月初八，喝腊八粥"),
    (12, 30, "除夕", "农历腊月三十（或廿九），除夕夜"),
]

# 公历节日列表
_SOLAR_FESTIVALS = [
    (1, 1, "元旦", "公历1月1日，新年伊始"),
    (4, 5, "清明节", "公历4月5日左右，扫墓祭祖"),
    (5, 1, "劳动节", "公历5月1日，国际劳动节"),
    (10, 1, "国庆节", "公历10月1日，中华人民共和国成立纪念日"),
]

# 月份天数
_MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


class ChineseFestival:
    """中国传统节日查询器

    提供中国传统节日的查询、日期获取、节日判断、月度节日列表和倒计时功能。
    内置春节、元宵节、端午节、七夕节、中秋节、重阳节、腊八节、除夕、
    元旦、清明节、劳动节、国庆节等节日数据。

    用法:
        festival = ChineseFestival()
        festivals = festival.get_festivals(2026)
        date = festival.get_festival_date("春节", 2026)
        name = festival.is_festival("2026-01-01")
        countdown = festival.get_festival_countdown("春节")
    """

    def __init__(self) -> None:
        """初始化节日查询器"""
        self._lunar_festivals = _LUNAR_FESTIVALS
        self._solar_festivals = _SOLAR_FESTIVALS
        self._spring_festival_dates = _SPRING_FESTIVAL_DATES

    def _get_lunar_festival_date(self, month: int, day: int, year: int) -> Optional[datetime.date]:
        """根据农历月日计算公历日期

        基于春节日期推算农历节日的公历日期。
        注意：此方法为简化实现，仅适用于已知春节日期的年份。

        Args:
            month: 农历月份（1-12）
            day: 农历日期（1-30）
            year: 公历年份

        Returns:
            对应的公历日期，无法计算时返回 None
        """
        if year not in self._spring_festival_dates:
            return None

        spring = self._spring_festival_dates[year]

        # 计算从春节（正月初一）到目标日期的天数偏移
        # 简化：假设正月30天，其他月交替29/30天
        days_offset = 0

        # 计算月份偏移
        for m in range(1, month):
            if m == 1:
                # 正月按30天计算
                days_offset += 30
            else:
                # 其他月交替29/30天
                days_offset += 29 if m % 2 == 0 else 30

        # 加上日期偏移（初一是第0天）
        days_offset += day - 1

        try:
            return spring + datetime.timedelta(days=days_offset)
        except (OverflowError, ValueError):
            return None

    def _get_festival_date_internal(self, name: str, year: int) -> Optional[Dict]:
        """获取指定节日的日期信息

        Args:
            name: 节日名称
            year: 年份

        Returns:
            节日日期信息字典，未找到返回 None
        """
        name = name.strip()

        # 先查农历节日
        for month, day, f_name, desc in self._lunar_festivals:
            if f_name == name:
                if name == "春节":
                    date = self._spring_festival_dates.get(year)
                else:
                    date = self._get_lunar_festival_date(month, day, year)
                if date:
                    return {
                        "name": f_name,
                        "date": date,
                        "date_str": date.strftime("%Y-%m-%d"),
                        "type": "农历",
                        "description": desc,
                        "lunar_month": month,
                        "lunar_day": day,
                    }
                return None

        # 再查公历节日
        for month, day, f_name, desc in self._solar_festivals:
            if f_name == name:
                # 清明节特殊处理：可能有浮动
                if name == "清明节":
                    # 4月5日左右
                    date = self._get_qingming_date(year)
                else:
                    try:
                        date = datetime.date(year, month, day)
                    except ValueError:
                        return None
                return {
                    "name": f_name,
                    "date": date,
                    "date_str": date.strftime("%Y-%m-%d"),
                    "type": "公历",
                    "description": desc,
                }

        return None

    @staticmethod
    def _get_qingming_date(year: int) -> datetime.date:
        """获取清明节日期（4月4日或5日）

        Args:
            year: 年份

        Returns:
            清明节日期
        """
        # 清明节通常在4月4日或5日，简化处理
        # 闰年多为4月4日
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        day = 4 if is_leap else 5
        return datetime.date(year, 4, day)

    def get_festivals(self, year: int) -> List[Dict]:
        """获取指定年份的所有传统节日列表

        Args:
            year: 年份

        Returns:
            节日列表，每个元素为包含节日信息的字典
        """
        results: List[Dict] = []

        # 添加农历节日
        for month, day, f_name, desc in self._lunar_festivals:
            if f_name == "春节":
                date = self._spring_festival_dates.get(year)
            elif f_name == "除夕":
                # 除夕：腊月最后一天，简化处理为腊月三十
                date = self._get_lunar_festival_date(12, 30, year)
                if date is None:
                    date = self._get_lunar_festival_date(12, 29, year)
            else:
                date = self._get_lunar_festival_date(month, day, year)

            if date:
                results.append({
                    "name": f_name,
                    "date": date,
                    "date_str": date.strftime("%Y-%m-%d"),
                    "type": "农历",
                    "description": desc,
                    "lunar_month": month,
                    "lunar_day": day,
                })

        # 添加公历节日
        for month, day, f_name, desc in self._solar_festivals:
            if f_name == "清明节":
                date = self._get_qingming_date(year)
            else:
                try:
                    date = datetime.date(year, month, day)
                except ValueError:
                    continue

            results.append({
                "name": f_name,
                "date": date,
                "date_str": date.strftime("%Y-%m-%d"),
                "type": "公历",
                "description": desc,
            })

        # 按日期排序
        results.sort(key=lambda x: x["date"])
        return results

    def get_festival_date(self, name: str, year: int) -> Optional[Dict]:
        """获取特定节日的日期信息

        Args:
            name: 节日名称（如"春节"、"中秋节"、"元旦"）
            year: 年份

        Returns:
            节日日期信息字典，包含名称、日期、类型等。
            节日不存在时返回 None。
        """
        return self._get_festival_date_internal(name, year)

    def is_festival(self, date_str: str) -> Optional[str]:
        """判断指定日期是否是传统节日

        返回匹配的节日名称。如果当天是多个节日，返回第一个匹配的。

        Args:
            date_str: 日期字符串，格式为 "YYYY-MM-DD" 或 "YYYYMMDD"

        Returns:
            节日名称，非节日返回 None
        """
        # 解析日期
        date_str = date_str.strip().replace("-", "").replace("/", "").replace("年", "").replace("月", "").replace("日", "")
        if len(date_str) == 8:
            try:
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                target_date = datetime.date(year, month, day)
            except (ValueError, IndexError):
                return None
        else:
            return None

        # 检查所有节日
        festivals = self.get_festivals(year)
        for festival in festivals:
            if festival["date"] == target_date:
                return festival["name"]

        return None

    def get_festivals_in_month(self, year: int, month: int) -> List[Dict]:
        """获取指定月份的所有传统节日

        Args:
            year: 年份
            month: 月份（1-12）

        Returns:
            该月内的节日列表
        """
        festivals = self.get_festivals(year)
        return [f for f in festivals if f["date"].month == month]

    def get_festival_countdown(self, name: str) -> int:
        """计算距离指定节日还有多少天

        Args:
            name: 节日名称

        Returns:
            距离节日的天数（正数表示未来，负数表示已过去，0表示今天）
        """
        today = datetime.date.today()
        year = today.year

        # 尝试当年
        festival = self.get_festival_date(name, year)
        if festival:
            diff = (festival["date"] - today).days
            if diff >= 0:
                return diff

        # 尝试下一年
        festival = self.get_festival_date(name, year + 1)
        if festival:
            diff = (festival["date"] - today).days
            return diff

        return -1  # 未找到节日


# =============================================================================
# 便捷函数
# =============================================================================

_default_festival = ChineseFestival()


def 获取节日列表(year: int) -> List[Dict]:
    """获取指定年份的所有传统节日

    Args:
        year: 年份

    Returns:
        节日列表
    """
    return _default_festival.get_festivals(year)


def 获取节日日期(name: str, year: int) -> Optional[Dict]:
    """获取特定节日的日期信息

    Args:
        name: 节日名称
        year: 年份

    Returns:
        节日日期信息字典
    """
    return _default_festival.get_festival_date(name, year)


def 判断节日(date_str: str) -> Optional[str]:
    """判断某天是否是节日

    Args:
        date_str: 日期字符串 "YYYY-MM-DD"

    Returns:
        节日名称，非节日返回 None
    """
    return _default_festival.is_festival(date_str)


def 获取月份节日(year: int, month: int) -> List[Dict]:
    """获取某月的节日列表

    Args:
        year: 年份
        month: 月份

    Returns:
        节日列表
    """
    return _default_festival.get_festivals_in_month(year, month)


def 节日倒计时(name: str) -> int:
    """距离某节日还有多少天

    Args:
        name: 节日名称

    Returns:
        天数
    """
    return _default_festival.get_festival_countdown(name)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'ChineseFestival',
    '获取节日列表',
    '获取节日日期',
    '判断节日',
    '获取月份节日',
    '节日倒计时',
]