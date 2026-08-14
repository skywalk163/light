# -*- coding: utf-8 -*-
"""
颜色转换和处理工具

提供 RGB、HEX、HSL、HSV、CMYK 等颜色格式之间的相互转换。

用法:
    from 标准库.颜色处理 import RGB转十六进制, 十六进制转RGB, HSL转RGB, 混合颜色

示例:
    设 红色 = RGB转十六进制(255, 0, 0)
    打印(红色)  # "#FF0000"
"""

import re as _re
from typing import Tuple, Optional


def RGB转十六进制(r: int, g: int, b: int) -> str:
    """将 RGB 颜色值转换为十六进制字符串

    Args:
        r: 红色分量，范围 0-255
        g: 绿色分量，范围 0-255
        b: 蓝色分量，范围 0-255

    Returns:
        十六进制颜色字符串，如 "#FF0000"

    Raises:
        ValueError: 如果 RGB 值超出范围
    """
    for 名称, 值 in [("R", r), ("G", g), ("B", b)]:
        if not 0 <= 值 <= 255:
            raise ValueError(f"{名称}值 {值} 超出范围 (0-255)")
    return f"#{r:02X}{g:02X}{b:02X}"


def 十六进制转RGB(十六进制: str) -> Tuple[int, int, int]:
    """将十六进制颜色字符串转换为 RGB 元组

    Args:
        十六进制: 十六进制颜色字符串，支持 "#RGB"、"#RRGGBB" 或 "RRGGBB" 格式

    Returns:
        (R, G, B) 元组，每个分量范围 0-255

    Raises:
        ValueError: 如果十六进制字符串格式无效
    """
    十六进制 = 十六进制.lstrip("#").strip()
    if len(十六进制) == 3:
        十六进制 = "".join(c * 2 for c in 十六进制)
    if len(十六进制) != 6:
        raise ValueError(f"无效的十六进制颜色值: #{十六进制}")

    try:
        r = int(十六进制[0:2], 16)
        g = int(十六进制[2:4], 16)
        b = int(十六进制[4:6], 16)
        return (r, g, b)
    except ValueError as e:
        raise ValueError(f"十六进制格式无效: {e}")


def RGB转HSL(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """将 RGB 颜色值转换为 HSL 颜色值

    Args:
        r: 红色分量，范围 0-255
        g: 绿色分量，范围 0-255
        b: 蓝色分量，范围 0-255

    Returns:
        (H, S, L) 元组，H 范围 0-360，S 和 L 范围 0-100
    """
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    最大值 = max(r_norm, g_norm, b_norm)
    最小值 = min(r_norm, g_norm, b_norm)
    差值 = 最大值 - 最小值

    # 计算色相 H
    if 差值 == 0:
        h = 0
    elif 最大值 == r_norm:
        h = 60 * (((g_norm - b_norm) / 差值) % 6)
    elif 最大值 == g_norm:
        h = 60 * (((b_norm - r_norm) / 差值) + 2)
    else:
        h = 60 * (((r_norm - g_norm) / 差值) + 4)

    # 计算亮度 L
    l = (最大值 + 最小值) / 2

    # 计算饱和度 S
    if 差值 == 0:
        s = 0
    else:
        s = 差值 / (1 - abs(2 * l - 1))

    return (round(h % 360, 1), round(s * 100, 1), round(l * 100, 1))


def HSL转RGB(h: float, s: float, l: float) -> Tuple[int, int, int]:
    """将 HSL 颜色值转换为 RGB 颜色值

    Args:
        h: 色相，范围 0-360
        s: 饱和度，范围 0-100
        l: 亮度，范围 0-100

    Returns:
        (R, G, B) 元组，每个分量范围 0-255
    """
    s_norm = s / 100.0
    l_norm = l / 100.0

    c = (1 - abs(2 * l_norm - 1)) * s_norm
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l_norm - c / 2

    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    return (round((r + m) * 255), round((g + m) * 255), round((b + m) * 255))


def RGB转HSV(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """将 RGB 颜色值转换为 HSV 颜色值

    Args:
        r: 红色分量，范围 0-255
        g: 绿色分量，范围 0-255
        b: 蓝色分量，范围 0-255

    Returns:
        (H, S, V) 元组，H 范围 0-360，S 和 V 范围 0-100
    """
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    最大值 = max(r_norm, g_norm, b_norm)
    最小值 = min(r_norm, g_norm, b_norm)
    差值 = 最大值 - 最小值

    if 差值 == 0:
        h = 0
    elif 最大值 == r_norm:
        h = 60 * (((g_norm - b_norm) / 差值) % 6)
    elif 最大值 == g_norm:
        h = 60 * (((b_norm - r_norm) / 差值) + 2)
    else:
        h = 60 * (((r_norm - g_norm) / 差值) + 4)

    s = 0 if 最大值 == 0 else (差值 / 最大值) * 100
    v = 最大值 * 100

    return (round(h % 360, 1), round(s, 1), round(v, 1))


def HSV转RGB(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """将 HSV 颜色值转换为 RGB 颜色值

    Args:
        h: 色相，范围 0-360
        s: 饱和度，范围 0-100
        v: 明度，范围 0-100

    Returns:
        (R, G, B) 元组，每个分量范围 0-255
    """
    s_norm = s / 100.0
    v_norm = v / 100.0

    c = v_norm * s_norm
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v_norm - c

    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    return (round((r + m) * 255), round((g + m) * 255), round((b + m) * 255))


def RGB转CMYK(r: int, g: int, b: int) -> Tuple[float, float, float, float]:
    """将 RGB 颜色值转换为 CMYK 颜色值

    Args:
        r: 红色分量，范围 0-255
        g: 绿色分量，范围 0-255
        b: 蓝色分量，范围 0-255

    Returns:
        (C, M, Y, K) 元组，每个分量范围 0-100
    """
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    k = 1 - max(r_norm, g_norm, b_norm)
    if k == 1:
        return (0, 0, 0, 100)

    c = (1 - r_norm - k) / (1 - k) * 100
    m = (1 - g_norm - k) / (1 - k) * 100
    y = (1 - b_norm - k) / (1 - k) * 100

    return (round(c, 1), round(m, 1), round(y, 1), round(k * 100, 1))


def CMYK转RGB(c: float, m: float, y: float, k: float) -> Tuple[int, int, int]:
    """将 CMYK 颜色值转换为 RGB 颜色值

    Args:
        c: 青色，范围 0-100
        m: 品红，范围 0-100
        y: 黄色，范围 0-100
        k: 黑色，范围 0-100

    Returns:
        (R, G, B) 元组，每个分量范围 0-255
    """
    c_norm = c / 100.0
    m_norm = m / 100.0
    y_norm = y / 100.0
    k_norm = k / 100.0

    r = round(255 * (1 - c_norm) * (1 - k_norm))
    g = round(255 * (1 - m_norm) * (1 - k_norm))
    b = round(255 * (1 - y_norm) * (1 - k_norm))

    return (r, g, b)


def 混合颜色(颜色1: str, 颜色2: str, 比例: float = 0.5) -> str:
    """混合两种十六进制颜色

    Args:
        颜色1: 第一种颜色，十六进制字符串
        颜色2: 第二种颜色，十六进制字符串
        比例: 混合比例，0 表示纯色1，1 表示纯色2，默认 0.5

    Returns:
        混合后的十六进制颜色字符串
    """
    if not 0 <= 比例 <= 1:
        raise ValueError(f"混合比例 {比例} 超出范围 (0-1)")

    r1, g1, b1 = 十六进制转RGB(颜色1)
    r2, g2, b2 = 十六进制转RGB(颜色2)

    r = round(r1 * (1 - 比例) + r2 * 比例)
    g = round(g1 * (1 - 比例) + g2 * 比例)
    b = round(b1 * (1 - 比例) + b2 * 比例)

    return RGB转十六进制(r, g, b)


def 亮度调整(十六进制: str, 百分比: float) -> str:
    """调整颜色的亮度

    Args:
        十六进制: 十六进制颜色字符串
        百分比: 亮度调整百分比，正数变亮，负数变暗，范围 -100 到 100

    Returns:
        调整后的十六进制颜色字符串
    """
    r, g, b = 十六进制转RGB(十六进制)
    比例 = 百分比 / 100.0

    if 比例 >= 0:
        r = round(r + (255 - r) * 比例)
        g = round(g + (255 - g) * 比例)
        b = round(b + (255 - b) * 比例)
    else:
        r = round(r * (1 + 比例))
        g = round(g * (1 + 比例))
        b = round(b * (1 + 比例))

    return RGB转十六进制(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def 随机颜色() -> str:
    """生成随机颜色

    Returns:
        随机十六进制颜色字符串
    """
    import random
    return RGB转十六进制(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def 获取颜色名称(十六进制: str) -> Optional[str]:
    """获取常见颜色的中文名称

    Args:
        十六进制: 十六进制颜色字符串

    Returns:
        颜色名称，如果未找到匹配则返回 None
    """
    常用颜色 = {
        "#FF0000": "红色", "#00FF00": "绿色", "#0000FF": "蓝色",
        "#FFFF00": "黄色", "#FF00FF": "品红", "#00FFFF": "青色",
        "#000000": "黑色", "#FFFFFF": "白色", "#808080": "灰色",
        "#FFC0CB": "粉色", "#FFA500": "橙色", "#800080": "紫色",
        "#A52A2A": "棕色", "#00FF7F": "春绿", "#FF4500": "橙红",
        "#708090": "石板灰", "#2E8B57": "海洋绿", "#DAA520": "金色",
        "#8B4513": "马鞍棕", "#6A5ACD": "板岩蓝", "#FFD700": "金色",
        "#C0C0C0": "银色", "#F5F5DC": "米色", "#FFE4E1": "薄雾玫瑰",
    }
    upper = 十六进制.upper()
    if upper in 常用颜色:
        return 常用颜色[upper]
    return None


def 生成渐变色(起始颜色: str, 结束颜色: str, 步数: int = 10) -> list:
    """生成两种颜色之间的渐变色列表

    Args:
        起始颜色: 起始十六进制颜色
        结束颜色: 结束十六进制颜色
        步数: 渐变步数，默认为 10

    Returns:
        渐变色十六进制字符串列表
    """
    if 步数 < 2:
        raise ValueError("步数必须大于等于 2")

    return [混合颜色(起始颜色, 结束颜色, i / (步数 - 1)) for i in range(步数)]