"""
日期时间增强模块 - 扩展 stdlib/日期时间.light 的 Python 后端
新增能力：
1. 自然语言相对时间解析（"3天前"/"下个月1号"/"上周六"/"今天"/"明天"/"下周周一"）
2. 起止时间（月初/月末/季度初/季度末/年初/年末/周一/周日）
3. 日期范围生成器（按日/周/月步长，返回 日期时间 列表）
"""
from __future__ import annotations
import re as _re
from datetime import datetime, timedelta, date
from calendar import monthrange, isleap
from typing import List, Optional, Tuple

# 复用 stdlib 日期时间.light 的底层工厂（如果存在则热插拔）
try:
    from stdlib.日期时间 import _创建日期时间, _创建时间差  # type: ignore
except Exception:  # 独立运行 fallback
    def _创建日期时间(y, mo, d, h=0, mi=0, s=0, ms=0, tz=None):  # type: ignore[misc]
        from datetime import timezone
        tzinfo = tz if tz is not None else timezone(timedelta(hours=8))
        return datetime(y, mo, d, h, mi, s, ms, tzinfo=tzinfo)

    def _创建时间差(天=0, 秒=0, **kw):  # type: ignore[misc]
        return timedelta(days=天, seconds=秒,
                         minutes=kw.get('分钟数', 0),
                         hours=kw.get('小时数', 0),
                         weeks=kw.get('周数', 0))

# ==========================================================
# 1. 自然语言相对时间解析
# ==========================================================

_HANZI_NUM = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
              '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
_WEEKDAY_ZH = {'周一': 0, '周二': 1, '周三': 2, '周四': 3, '周五': 4, '周六': 5, '周日': 6, '周天': 6, '星期天': 6}


def _parse_han_int(text: str) -> Optional[int]:
    """把「三/二十三/两/十」这类中文数字转成 int"""
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if text in _HANZI_NUM:
        return _HANZI_NUM[text]
    # 组合：二十三 = 10 + 3，十三 = 10 + 3，二十 = 20
    total = 0
    cur = 0
    for ch in text:
        if ch not in _HANZI_NUM:
            return None
        v = _HANZI_NUM[ch]
        if v == 10:
            if cur == 0:
                cur = 1
            total += cur * 10
            cur = 0
        else:
            cur = cur * 10 + v if cur == 1 and v < 10 else cur + v  # fallback
    return total + cur


def 解析相对时间(描述: str, 基准: Optional[datetime] = None) -> datetime:
    """把中文自然语言描述解析成 datetime（带 Asia/Shanghai 偏移的 tzinfo）

    支持句式：
      今天 / 今 / 此刻 / 现在
      明天 / 明日 / 后天 / 大后天 / 昨天 / 昨日 / 前天 / 大前天
      N天前 / N天後 / N天后 / N天後 / N日之前 / N日之后
      N小时前 / N小时后 / N分钟前 / N分钟后 / N秒前 / N秒后
      N周前 / N周后 / N个月前 / N个月后 / N年前 / N年后
      本周一 / 下周一 / 下下周一 / 上周六 / 本周日
      今天起N天 / N个月后的第K日
      下个月1号 / 本月15号 / 今年3月8号 / 明年1月1日
    """
    now = 基准 or _创建日期时间(*_today_ymd())  # noqa: F821
    now = now.replace(microsecond=0)
    desc = 描述.strip()
    if not desc:
        return now

    # 0. 立刻匹配的固定短语（含"今天"基）
    if desc in ('今天', '今', '今日', '此刻', '现在', '当前'):
        return now
    delta_days = {'明天': 1, '明日': 1, '后天': 2, '大后天': 3,
                  '昨天': -1, '昨日': -1, '前天': -2, '大前天': -3,
                  '上周': -7, '下周': 7, '本月': 0}
    if desc in delta_days:
        return _add_days(now, delta_days[desc])

    # 1. N天前 / N天后 / N日之前 / N日之后 / N小时前/后 / N分钟前/后 / N秒前/后 / N周前/后
    m = _re.match(r'^(.+?)\s*(天|日|小时|时|分钟|分|秒|周|个月|月|年)\s*(前|之前|以前|后|之后|以后|後)$', desc)
    if m:
        n = _parse_han_int(m.group(1))
        if n is None:
            raise ValueError(f"无法识别数字: {m.group(1)!r}")
        unit = m.group(2)
        sign = -1 if m.group(3) in ('前', '之前', '以前') else 1
        return _shift(now, unit, sign * n)

    # 2. 本周一/下周一/下下周一/上周六/本周日
    m = _re.match(r'^(本|下|上上|上|下下)?\s*周\s*([一二三四五六日天])\s*$', desc)
    if m:
        prefix = m.group(1) or '本'
        target_wd = _WEEKDAY_ZH['周' + m.group(2)]
        current_wd = now.weekday()
        diff_days = target_wd - current_wd
        if prefix == '本':
            pass  # diff_days stay as-is, negative means earlier this week
        elif prefix == '上' or prefix == '上上':
            diff_days -= 7 if prefix == '上' else 14
            if diff_days > 0:
                diff_days -= 7
        else:  # 下 / 下下
            add = 7 if prefix == '下' else 14
            if diff_days <= 0:
                diff_days += add
            else:
                diff_days += (add - 7)
        return _add_days(now, diff_days)

    # 3. 下个月1号 / 本月15号 / 今年3月8号 / 明年1月1日
    m = _re.match(r'^(本|下|上|明|去)?\s*(月|年|个月)\s*(\d{1,2})\s*(?:月)?\s*(\d{1,2})\s*[号日]?$', desc)
    if not m:
        m = _re.match(r'^(本|下|上|明|去)(月|年|个月)\s*(第)?\s*(\d{1,2})\s*[号日]$', desc)
    if m:
        prefix = m.group(1) or '本'
        span = m.group(2)
        groups = m.groups()
        if span in ('月', '个月'):
            y, mo = now.year, now.month
            if prefix == '下':
                mo += 1
            elif prefix == '上':
                mo -= 1
            if mo > 12:
                y += 1
                mo -= 12
            elif mo < 1:
                y -= 1
                mo += 12
            # 解析日
            day_match = _re.search(r'(\d{1,2})\s*[号日]$', desc)
            if day_match:
                d = int(day_match.group(1))
            else:
                m2 = _re.match(r'^.*?(\d{1,2})\s*月\s*(\d{1,2})\s*[号日]?$', desc)
                if m2:
                    mo = int(m2.group(1)); d = int(m2.group(2))
                else:
                    d = 1
        else:  # 年
            y = now.year + (1 if prefix == '明' else -1 if prefix == '去' else 0)
            mo_d = _re.findall(r'(\d{1,2})\s*月\s*(\d{1,2})\s*[号日]?|(\d{1,2})\s*[号日]', desc)
            try:
                flat = [x for t in mo_d for x in t if x]
                if len(flat) >= 2:
                    mo, d = int(flat[0]), int(flat[1])
                elif len(flat) == 1:
                    mo, d = now.month, int(flat[0])
                else:
                    mo, d = 1, 1
            except Exception:
                mo, d = 1, 1
        last_day = monthrange(y, mo)[1]
        d = min(max(d, 1), last_day)
        return _创建日期时间(y, mo, d, now.hour, now.minute, now.second)

    raise ValueError(f"无法解析相对时间描述: {描述!r}")


def _today_ymd() -> Tuple[int, int, int]:
    t = datetime.now()
    return t.year, t.month, t.day


def _add_days(dt: datetime, n: int) -> datetime:
    return _创建日期时间(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second) + _创建时间差(天=n)


def _shift(dt: datetime, unit: str, n: int) -> datetime:
    if unit in ('天', '日'):
        return _add_days(dt, n)
    if unit in ('小时', '时'):
        return dt + _创建时间差(小时数=n)
    if unit in ('分钟', '分'):
        return dt + _创建时间差(分钟数=n)
    if unit == '秒':
        return dt + _创建时间差(秒数=n)
    if unit == '周':
        return _add_days(dt, 7 * n)
    if unit in ('个月', '月'):
        y, mo, d = dt.year, dt.month, dt.day
        total = y * 12 + (mo - 1) + n
        y2, mo2 = divmod(total, 12)
        mo2 += 1
        last = monthrange(y2, mo2)[1]
        d2 = min(d, last)
        return _创建日期时间(y2, mo2, d2, dt.hour, dt.minute, dt.second)
    if unit == '年':
        y2 = dt.year + n
        mo, d = dt.month, dt.day
        if mo == 2 and d == 29 and not isleap(y2):
            d = 28
        return _创建日期时间(y2, mo, d, dt.hour, dt.minute, dt.second)
    raise ValueError(f"未知单位: {unit}")


# ==========================================================
# 2. 起止时间
# ==========================================================

def 月初(dt: Optional[datetime] = None) -> datetime:
    t = dt or _创建日期时间(*_today_ymd())
    return _创建日期时间(t.year, t.month, 1)


def 月末(dt: Optional[datetime] = None) -> datetime:
    t = dt or _创建日期时间(*_today_ymd())
    last_day = monthrange(t.year, t.month)[1]
    return _创建日期时间(t.year, t.month, last_day, 23, 59, 59)


def 季度初(dt: Optional[datetime] = None) -> datetime:
    t = dt or _创建日期时间(*_today_ymd())
    q = (t.month - 1) // 3
    return _创建日期时间(t.year, q * 3 + 1, 1)


def 季度末(dt: Optional[datetime] = None) -> datetime:
    t = dt or _创建日期时间(*_today_ymd())
    q = (t.month - 1) // 3
    last_mo = q * 3 + 3
    last_day = monthrange(t.year, last_mo)[1]
    return _创建日期时间(t.year, last_mo, last_day, 23, 59, 59)


def 年初(dt: Optional[datetime] = None) -> datetime:
    t = dt or _创建日期时间(*_today_ymd())
    return _创建日期时间(t.year, 1, 1)


def 年末(dt: Optional[datetime] = None) -> datetime:
    t = dt or _创建日期时间(*_today_ymd())
    return _创建日期时间(t.year, 12, 31, 23, 59, 59)


def 周初(dt: Optional[datetime] = None) -> datetime:
    t = dt or _创建日期时间(*_today_ymd())
    return _add_days(t, -t.weekday())


def 周末(dt: Optional[datetime] = None) -> datetime:
    t = dt or _创建日期时间(*_today_ymd())
    sun = _add_days(t, 6 - t.weekday())
    return _创建日期时间(sun.year, sun.month, sun.day, 23, 59, 59)


# ==========================================================
# 3. 日期范围生成器
# ==========================================================

def 日期范围(开始: datetime, 结束: datetime, 步长天: int = 1, 步长周: int = 0, 步长月: int = 0) -> List[datetime]:
    """返回 [开始, 结束] 闭区间内按步长生成的日期时间列表。
    步长优先级：步长月 > 步长周 > 步长天"""
    if 开始 > 结束:
        raise ValueError("开始必须 <= 结束")
    res: List[datetime] = []
    cur = 开始
    i = 0
    while cur <= 结束:
        res.append(_创建日期时间(cur.year, cur.month, cur.day, cur.hour, cur.minute, cur.second))
        i += 1
        if 步长月 != 0:
            cur = _shift(cur, '月', 步长月)
        elif 步长周 != 0:
            cur = _add_days(cur, 7 * 步长周)
        else:
            cur = _add_days(cur, 步长天 or 1)
        if i > 100000:
            raise RuntimeError("日期范围过大，超过10万条中止")
    return res
