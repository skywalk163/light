"""
段言标准库 - 农历工具模块

提供公历与农历之间的转换、农历节日查询、闰月判断等功能。

类：
    LunarCalendar: 农历工具类

用法:
    cal = LunarCalendar()
    info = cal.solar_to_lunar(2024, 1, 1)
    today = cal.get_lunar_date()
    festivals = cal.get_festivals(1, 1)
    is_leap = cal.is_leap_month(2024, 2)
"""

import datetime
from typing import Dict, List, Optional


# =============================================================================
# 2024-2030 年农历数据
# =============================================================================

# 农历月份天数表（大月30天，小月29天）
# 格式: [month1_days, month2_days, ..., month12_days, leap_month, leap_month_days]
# leap_month=0 表示没有闰月
_LUNAR_YEAR_DATA = {
    2024: [30, 29, 30, 29, 30, 29, 30, 29, 30, 29, 30, 29, 0, 0],
    2025: [29, 30, 29, 29, 30, 29, 30, 29, 30, 30, 30, 29, 6, 29],
    2026: [30, 29, 30, 29, 29, 30, 29, 29, 30, 30, 29, 30, 0, 0],
    2027: [29, 30, 29, 30, 29, 29, 30, 29, 30, 29, 30, 29, 5, 30],
    2028: [30, 29, 30, 29, 30, 29, 29, 30, 29, 30, 29, 30, 0, 0],
    2029: [29, 30, 30, 29, 30, 29, 29, 30, 29, 30, 29, 30, 0, 0],
    2030: [29, 30, 29, 30, 29, 30, 29, 29, 30, 29, 30, 29, 3, 30],
}

# 各年农历正月初一对应的公历日期
_LUNAR_NEW_YEAR = {
    2024: (2024, 2, 10),
    2025: (2025, 1, 29),
    2026: (2026, 2, 17),
    2027: (2027, 2, 6),
    2028: (2028, 1, 26),
    2029: (2029, 2, 13),
    2030: (2030, 2, 3),
}

# 农历月份名称
_LUNAR_MONTH_NAMES = [
    "正月", "二月", "三月", "四月", "五月", "六月",
    "七月", "八月", "九月", "十月", "冬月", "腊月",
]

# 农历日名称
_LUNAR_DAY_NAMES = [
    "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
]

# 天干地支
_HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
_EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
_ZODIAC_ANIMALS = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]


# =============================================================================
# 传统节日列表
# =============================================================================

_TRADITIONAL_FESTIVALS = {
    (1, 1): "春节",
    (1, 15): "元宵节",
    (2, 2): "龙抬头",
    (3, 3): "上巳节",
    (5, 5): "端午节",
    (6, 6): "天贶节",
    (7, 7): "七夕节",
    (7, 15): "中元节",
    (8, 15): "中秋节",
    (9, 9): "重阳节",
    (10, 1): "寒衣节",
    (10, 15): "下元节",
    (12, 8): "腊八节",
    (12, 23): "小年（北方）",
    (12, 24): "小年（南方）",
    (12, 30): "除夕",
}


# =============================================================================
# 农历工具类
# =============================================================================

class LunarCalendar:
    """农历工具类

    提供公历转农历、农历日期查询、传统节日查询、闰月判断等功能。
    内置 2024-2030 年的农历数据。

    用法:
        cal = LunarCalendar()
        lunar_info = cal.solar_to_lunar(2024, 10, 1)
        today = cal.get_lunar_date()
        festivals = cal.get_festivals(1, 1)
    """

    def __init__(self):
        """初始化农历工具"""
        self._year_data = _LUNAR_YEAR_DATA
        self._new_year = _LUNAR_NEW_YEAR
        self._festivals = _TRADITIONAL_FESTIVALS

    def solar_to_lunar(self, year: int, month: int, day: int) -> Dict[str, object]:
        """公历日期转农历日期

        Args:
            year: 公历年份
            month: 公历月份（1-12）
            day: 公历日期

        Returns:
            包含农历信息的字典:
            - lunar_year: 农历年
            - lunar_month: 农历月
            - lunar_day: 农历日
            - is_leap: 是否为闰月
            - month_name: 农历月名称（如"正月"）
            - day_name: 农历日名称（如"初一"）
            - ganzhi_year: 干支纪年
            - zodiac: 生肖
            - festivals: 当日节日列表
        """
        # 验证日期范围
        self._validate_date(year, month, day)

        # 检查是否在支持的数据范围内
        if year < min(self._year_data.keys()) or year > max(self._year_data.keys()):
            return self._calculate_lunar_fallback(year, month, day)

        # 查找该年农历新年日期
        if year not in self._new_year:
            return self._calculate_lunar_fallback(year, month, day)

        ny_year, ny_month, ny_day = self._new_year[year]

        # 计算与农历新年的天数差
        target_date = datetime.date(year, month, day)
        new_year_date = datetime.date(ny_year, ny_month, ny_day)

        if target_date < new_year_date:
            # 日期在上一年农历年内
            prev_year = year - 1
            if prev_year in self._new_year:
                pny_year, pny_month, pny_day = self._new_year[prev_year]
                prev_new_year = datetime.date(pny_year, pny_month, pny_day)
                diff = (target_date - prev_new_year).days
                return self._days_to_lunar(prev_year, diff)
            return self._calculate_lunar_fallback(year, month, day)

        diff = (target_date - new_year_date).days
        return self._days_to_lunar(year, diff)

    def _days_to_lunar(self, year: int, days: int) -> Dict[str, object]:
        """根据农历年正月初一之后的天数计算农历日期"""
        if year not in self._year_data:
            return self._make_simple_result(year, 1, 1, False)

        data = self._year_data[year]
        month_days = data[:12]
        leap_month = data[12]
        leap_days = data[13]

        current_days = 0
        lunar_month = 1
        lunar_day = 1
        is_leap = False

        # 遍历各月
        for m in range(12):
            month_size = month_days[m]
            if current_days + month_size > days:
                lunar_month = m + 1
                lunar_day = days - current_days + 1
                break
            current_days += month_size

            # 如果该月后有闰月
            if leap_month == m + 1:
                if current_days + leap_days > days:
                    lunar_month = m + 1
                    lunar_day = days - current_days + 1
                    is_leap = True
                    break
                current_days += leap_days
        else:
            # 超出已知月份范围
            lunar_month = 12
            lunar_day = min(30, days - current_days + 1)

        return self._make_result(year, lunar_month, lunar_day, is_leap)

    def _make_result(self, year: int, month: int, day: int, is_leap: bool) -> Dict[str, object]:
        """构建农历结果字典"""
        month_name = ("闰" if is_leap else "") + _LUNAR_MONTH_NAMES[month - 1]
        day_name = _LUNAR_DAY_NAMES[day - 1] if 1 <= day <= 30 else f"第{day}日"
        ganzhi = self._get_ganzhi_year(year)
        zodiac = self._get_zodiac(year)
        festivals = self.get_festivals(month, day)

        return {
            "lunar_year": year,
            "lunar_month": month,
            "lunar_day": day,
            "is_leap": is_leap,
            "month_name": month_name,
            "day_name": day_name,
            "ganzhi_year": ganzhi,
            "zodiac": zodiac,
            "festivals": festivals,
        }

    def _make_simple_result(self, year: int, month: int, day: int, is_leap: bool) -> Dict[str, object]:
        """构建简化农历结果（数据不足时使用）"""
        month_name = ("闰" if is_leap else "") + _LUNAR_MONTH_NAMES[month - 1] if 1 <= month <= 12 else f"第{month}月"
        day_name = _LUNAR_DAY_NAMES[day - 1] if 1 <= day <= 30 else f"第{day}日"
        ganzhi = self._get_ganzhi_year(year)
        zodiac = self._get_zodiac(year)
        festivals = self.get_festivals(month, day)

        return {
            "lunar_year": year,
            "lunar_month": month,
            "lunar_day": day,
            "is_leap": is_leap,
            "month_name": month_name,
            "day_name": day_name,
            "ganzhi_year": ganzhi,
            "zodiac": zodiac,
            "festivals": festivals,
        }

    def _calculate_lunar_fallback(self, year: int, month: int, day: int) -> Dict[str, object]:
        """数据范围外的公历转农历近似计算

        基于春节日期的大致估算（春节通常在1月21日至2月20日之间）。

        Args:
            year: 公历年份
            month: 公历月份
            day: 公历日期

        Returns:
            近似农历信息
        """
        # 简单估算：1月大概率在上一农历年，2月后在新农历年
        if month == 1 and day <= 20:
            # 可能在上一农历年
            lunar_year = year - 1
            lunar_month = 11  # 冬月或腊月
            lunar_day = day + 20  # 粗略估算
        elif month == 1:
            lunar_year = year
            lunar_month = 12
            lunar_day = day - 20
        elif month == 2 and day <= 19:
            lunar_year = year
            lunar_month = 1
            lunar_day = day + 10
        else:
            # 大致按公历月减1为农历月
            lunar_year = year
            lunar_month = max(1, month - 1)
            lunar_day = day

        # 确保日期的合理性
        lunar_day = max(1, min(30, lunar_day))

        return self._make_simple_result(lunar_year, lunar_month, lunar_day, False)

    def get_lunar_date(self) -> Dict[str, object]:
        """获取当前农历日期

        Returns:
            当前日期的农历信息字典
        """
        today = datetime.date.today()
        return self.solar_to_lunar(today.year, today.month, today.day)

    def get_festivals(self, lunar_month: int, lunar_day: int) -> List[str]:
        """获取农历指定日期对应的传统节日

        Args:
            lunar_month: 农历月份（1-12）
            lunar_day: 农历日期（1-30）

        Returns:
            节日名称列表，无节日时返回空列表
        """
        festivals = []
        key = (lunar_month, lunar_day)
        if key in self._festivals:
            festivals.append(self._festivals[key])
        return festivals

    def is_leap_month(self, year: int, month: int) -> bool:
        """判断指定年份的指定月份是否为闰月

        Args:
            year: 农历年份
            month: 农历月份（1-12）

        Returns:
            True 如果该月是闰月
        """
        if year not in self._year_data:
            return False
        data = self._year_data[year]
        leap_month = data[12]
        return leap_month == month

    def get_all_festivals(self) -> Dict[tuple, str]:
        """获取所有传统节日映射

        Returns:
            {(月, 日): "节日名"} 字典
        """
        return dict(self._festivals)

    def _get_ganzhi_year(self, year: int) -> str:
        """获取干支纪年

        Args:
            year: 公历年份

        Returns:
            干支字符串（如"甲辰"）
        """
        # 1984 年为甲子年
        offset = (year - 1984) % 60
        stem = _HEAVENLY_STEMS[offset % 10]
        branch = _EARTHLY_BRANCHES[offset % 12]
        return stem + branch

    def _get_zodiac(self, year: int) -> str:
        """获取生肖

        Args:
            year: 公历年份

        Returns:
            生肖字符（如"龙"）
        """
        # 2020 年为鼠年
        offset = (year - 2020) % 12
        return _ZODIAC_ANIMALS[offset]

    @staticmethod
    def _validate_date(year: int, month: int, day: int) -> None:
        """验证公历日期有效性

        Args:
            year: 年份
            month: 月份
            day: 日期

        Raises:
            ValueError: 日期无效时抛出
        """
        if not (1 <= month <= 12):
            raise ValueError(f"月份必须在 1-12 之间: {month}")
        if not (1 <= day <= 31):
            raise ValueError(f"日期必须在 1-31 之间: {day}")
        try:
            datetime.date(year, month, day)
        except ValueError as e:
            raise ValueError(f"无效的日期 {year}-{month:02d}-{day:02d}: {e}")


# =============================================================================
# 便捷函数
# =============================================================================

_default_calendar = LunarCalendar()


def 公历转农历(year: int, month: int, day: int) -> Dict[str, object]:
    """公历日期转农历日期

    Args:
        year: 公历年份
        month: 公历月份
        day: 公历日期

    Returns:
        农历信息字典
    """
    return _default_calendar.solar_to_lunar(year, month, day)


def 当前农历() -> Dict[str, object]:
    """获取当前农历日期

    Returns:
        当前农历信息字典
    """
    return _default_calendar.get_lunar_date()


def 查询节日(lunar_month: int, lunar_day: int) -> List[str]:
    """查询农历节日

    Args:
        lunar_month: 农历月份
        lunar_day: 农历日期

    Returns:
        节日名称列表
    """
    return _default_calendar.get_festivals(lunar_month, lunar_day)


def 判断闰月(year: int, month: int) -> bool:
    """判断是否为闰月

    Args:
        year: 农历年份
        month: 农历月份

    Returns:
        True 如果该月为闰月
    """
    return _default_calendar.is_leap_month(year, month)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'LunarCalendar',
    '公历转农历',
    '当前农历',
    '查询节日',
    '判断闰月',
]