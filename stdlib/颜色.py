# -*- coding: utf-8 -*-
"""
光明标准库 - 颜色处理模块

提供 RGB/HSL/十六进制颜色转换和处理功能。
"""

import colorsys
import re
from typing import Tuple, Optional


def RGB解析(文本: str) -> Tuple[int, int, int]:
    """
    解析颜色字符串为 RGB 元组

    支持格式：
    - #RRGGBB
    - #RGB
    - rgb(r, g, b)
    - r, g, b

    参数:
        文本: 颜色字符串

    返回:
        (R, G, B) 元组，每个分量 0-255

    示例:
        RGB解析('#FF0000')  # (255, 0, 0)
        RGB解析('rgb(255, 0, 0)')  # (255, 0, 0)
    """
    if not 文本:
        raise ValueError("颜色字符串不能为空")

    文本 = 文本.strip()

    # #RRGGBB
    m = re.match(r'^#?([0-9a-fA-F]{6})$', 文本)
    if m:
        十六进制 = m.group(1)
        return (int(十六进制[0:2], 16), int(十六进制[2:4], 16), int(十六进制[4:6], 16))

    # #RGB
    m = re.match(r'^#?([0-9a-fA-F]{3})$', 文本)
    if m:
        十六进制 = m.group(1)
        return (int(十六进制[0] * 2, 16), int(十六进制[1] * 2, 16), int(十六进制[2] * 2, 16))

    # rgb(r, g, b)
    m = re.match(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', 文本)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # r, g, b
    m = re.match(r'(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', 文本)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    raise ValueError(f"无法解析颜色字符串: '{文本}'")


def RGB转十六进制(r: int, g: int, b: int) -> str:
    """
    RGB 转十六进制颜色字符串

    参数:
        r: 红色分量 (0-255)
        g: 绿色分量 (0-255)
        b: 蓝色分量 (0-255)

    返回:
        十六进制颜色字符串，如 '#FF0000'
    """
    _验证RGB(r, g, b)
    return f'#{r:02X}{g:02X}{b:02X}'


def 十六进制转RGB(十六进制: str) -> Tuple[int, int, int]:
    """
    十六进制颜色字符串转 RGB 元组

    参数:
        十六进制: 十六进制颜色字符串（如 '#FF0000'）

    返回:
        (R, G, B) 元组
    """
    return RGB解析(十六进制)


def RGB转HSL(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    RGB 转 HSL

    参数:
        r: 红色分量 (0-255)
        g: 绿色分量 (0-255)
        b: 蓝色分量 (0-255)

    返回:
        (H, S, L) 元组，H: 0-360, S: 0-100, L: 0-100
    """
    _验证RGB(r, g, b)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return (h * 360, s * 100, l * 100)


def HSL转RGB(h: float, s: float, l: float) -> Tuple[int, int, int]:
    """
    HSL 转 RGB

    参数:
        h: 色相 (0-360)
        s: 饱和度 (0-100)
        l: 亮度 (0-100)

    返回:
        (R, G, B) 元组，每个分量 0-255
    """
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return (int(r * 255), int(g * 255), int(b * 255))


def RGB转HSV(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    RGB 转 HSV

    参数:
        r: 红色分量 (0-255)
        g: 绿色分量 (0-255)
        b: 蓝色分量 (0-255)

    返回:
        (H, S, V) 元组，H: 0-360, S: 0-100, V: 0-100
    """
    _验证RGB(r, g, b)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return (h * 360, s * 100, v * 100)


def HSV转RGB(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """
    HSV 转 RGB

    参数:
        h: 色相 (0-360)
        s: 饱和度 (0-100)
        v: 明度 (0-100)

    返回:
        (R, G, B) 元组
    """
    r, g, b = colorsys.hsv_to_rgb(h / 360, s / 100, v / 100)
    return (int(r * 255), int(g * 255), int(b * 255))


def 颜色混合(颜色1: str, 颜色2: str, 比例: float = 0.5) -> str:
    """
    混合两种颜色

    参数:
        颜色1: 第一种颜色（十六进制）
        颜色2: 第二种颜色（十六进制）
        比例: 混合比例 (0-1)，0 为颜色1，1 为颜色2

    返回:
        混合后的颜色十六进制字符串
    """
    r1, g1, b1 = RGB解析(颜色1)
    r2, g2, b2 = RGB解析(颜色2)
    r = int(r1 + (r2 - r1) * 比例)
    g = int(g1 + (g2 - g1) * 比例)
    b = int(b1 + (b2 - b1) * 比例)
    return RGB转十六进制(r, g, b)


def 颜色亮度(颜色: str) -> float:
    """
    计算颜色的感知亮度 (0-1)

    参数:
        颜色: 十六进制颜色字符串

    返回:
        亮度值，0为最暗，1为最亮
    """
    r, g, b = RGB解析(颜色)
    # 使用相对亮度公式
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def 颜色反转(颜色: str) -> str:
    """
    反转颜色

    参数:
        颜色: 十六进制颜色字符串

    返回:
        反转后的颜色十六进制字符串
    """
    r, g, b = RGB解析(颜色)
    return RGB转十六进制(255 - r, 255 - g, 255 - b)


def 颜色变亮(颜色: str, 比例: float = 0.2) -> str:
    """
    将颜色变亮

    参数:
        颜色: 十六进制颜色字符串
        比例: 变亮比例 (0-1)

    返回:
        变亮后的颜色十六进制字符串
    """
    r, g, b = RGB解析(颜色)
    r = int(min(255, r + (255 - r) * 比例))
    g = int(min(255, g + (255 - g) * 比例))
    b = int(min(255, b + (255 - b) * 比例))
    return RGB转十六进制(r, g, b)


def 颜色变暗(颜色: str, 比例: float = 0.2) -> str:
    """
    将颜色变暗

    参数:
        颜色: 十六进制颜色字符串
        比例: 变暗比例 (0-1)

    返回:
        变暗后的颜色十六进制字符串
    """
    r, g, b = RGB解析(颜色)
    r = int(max(0, r * (1 - 比例)))
    g = int(max(0, g * (1 - 比例)))
    b = int(max(0, b * (1 - 比例)))
    return RGB转十六进制(r, g, b)


def 颜色透明(颜色: str, 透明度: float) -> str:
    """
    为颜色添加透明度（RGBA 格式）

    参数:
        颜色: 十六进制颜色字符串
        透明度: 透明度值 (0-1)

    返回:
        rgba(r, g, b, a) 格式字符串
    """
    r, g, b = RGB解析(颜色)
    return f'rgba({r}, {g}, {b}, {透明度})'


def 获取颜色名称(颜色: str) -> str:
    """
    获取常见颜色的中文名称

    参数:
        颜色: 十六进制颜色字符串

    返回:
        颜色名称，未知返回 '未知'
    """
    颜色映射 = {
        '#FF0000': '红色', '#00FF00': '绿色', '#0000FF': '蓝色',
        '#FFFFFF': '白色', '#000000': '黑色', '#FFFF00': '黄色',
        '#FF00FF': '品红', '#00FFFF': '青色', '#C0C0C0': '银色',
        '#808080': '灰色', '#800000': '栗色', '#808000': '橄榄色',
        '#008000': '深绿', '#800080': '紫色', '#008080': '青色',
        '#000080': '深蓝', '#FFA500': '橙色', '#FFC0CB': '粉色',
        '#A52A2A': '棕色', '#FFD700': '金色', '#F0F8FF': '爱丽丝蓝',
        '#FAEBD7': '古董白', '#7FFFD4': '碧绿', '#F0FFFF': '天蓝',
        '#F5F5DC': '米色', '#FFE4C4': '饼干色', '#FF7F50': '珊瑚色',
        '#6495ED': '矢车菊蓝', '#DC143C': '绯红', '#00BFFF': '深天蓝',
        '#696969': '暗灰', '#FF1493': '深粉', '#FF4500': '橙红',
        '#2E8B57': '海绿', '#F0E68C': '卡其', '#FFFACD': '柠檬绸',
        '#E6E6FA': '薰衣草', '#FFE4E1': '薄雾玫瑰', '#FFE4B5': '鹿皮色',
        '#FFDAB9': '桃色', '#FFA07A': '亮鲑鱼', '#87CEEB': '天蓝',
        '#DDA0DD': '李色', '#F08080': '亮珊瑚', '#FA8072': '鲑鱼',
        '#F4A460': '沙色', '#D2B48C': '黄褐', '#FF6347': '番茄',
        '#EE82EE': '紫罗兰', '#F5DEB3': '小麦色',
    }
    return 颜色映射.get(颜色.upper(), '未知')


def _验证RGB(r: int, g: int, b: int):
    """验证 RGB 分量值范围"""
    for 名称, 值 in [('R', r), ('G', g), ('B', b)]:
        if not isinstance(值, int) or 值 < 0 or 值 > 255:
            raise ValueError(f"RGB 分量 {名称} 值 {值} 超出范围 (0-255)")


__all__ = [
    'RGB解析', 'RGB转十六进制', '十六进制转RGB',
    'RGB转HSL', 'HSL转RGB',
    'RGB转HSV', 'HSV转RGB',
    '颜色混合', '颜色亮度', '颜色反转',
    '颜色变亮', '颜色变暗', '颜色透明',
    '获取颜色名称',
]