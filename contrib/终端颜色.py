"""
光明标准库 - 终端颜色模块

提供 ANSI 转义序列颜色输出功能
"""

# ANSI 转义序列前缀
ANSI_PREFIX = "\033["
ANSI_SUFFIX = "m"

# 重置代码
RESET = "0"

# 前景色代码
FOREGROUND_COLORS = {
    "黑色": "30",
    "红色": "31",
    "绿色": "32",
    "黄色": "33",
    "蓝色": "34",
    "洋红": "35",
    "青色": "36",
    "白色": "37",
}

# 背景色代码
BACKGROUND_COLORS = {
    "黑色": "40",
    "红色": "41",
    "绿色": "42",
    "黄色": "43",
    "蓝色": "44",
    "洋红": "45",
    "青色": "46",
    "白色": "47",
}

# 样式代码
STYLE_CODES = {
    "高亮": "1",
    "暗色": "2",
    "下划线": "4",
    "闪烁": "5",
}


def _wrap(text: str, *codes: str) -> str:
    """将文本包装为 ANSI 转义序列"""
    code_str = ";".join(codes)
    return f"{ANSI_PREFIX}{code_str}{ANSI_SUFFIX}{text}{ANSI_PREFIX}{RESET}{ANSI_SUFFIX}"


def 红色(文本: str) -> str:
    """红色前景色"""
    return _wrap(文本, FOREGROUND_COLORS["红色"])


def 绿色(文本: str) -> str:
    """绿色前景色"""
    return _wrap(文本, FOREGROUND_COLORS["绿色"])


def 蓝色(文本: str) -> str:
    """蓝色前景色"""
    return _wrap(文本, FOREGROUND_COLORS["蓝色"])


def 黄色(文本: str) -> str:
    """黄色前景色"""
    return _wrap(文本, FOREGROUND_COLORS["黄色"])


def 青色(文本: str) -> str:
    """青色前景色"""
    return _wrap(文本, FOREGROUND_COLORS["青色"])


def 洋红(文本: str) -> str:
    """洋红前景色"""
    return _wrap(文本, FOREGROUND_COLORS["洋红"])


def 白色(文本: str) -> str:
    """白色前景色"""
    return _wrap(文本, FOREGROUND_COLORS["白色"])


def 黑色(文本: str) -> str:
    """黑色前景色"""
    return _wrap(文本, FOREGROUND_COLORS["黑色"])


def 高亮(文本: str) -> str:
    """高亮样式"""
    return _wrap(文本, STYLE_CODES["高亮"])


def 暗色(文本: str) -> str:
    """暗色样式"""
    return _wrap(文本, STYLE_CODES["暗色"])


def 下划线(文本: str) -> str:
    """下划线样式"""
    return _wrap(文本, STYLE_CODES["下划线"])


def 闪烁(文本: str) -> str:
    """闪烁样式"""
    return _wrap(文本, STYLE_CODES["闪烁"])


def 重置() -> str:
    """重置所有格式"""
    return f"{ANSI_PREFIX}{RESET}{ANSI_SUFFIX}"


def 样式(文本: str, 代码: str) -> str:
    """自定义样式代码"""
    return _wrap(文本, 代码)


def 前景色(文本: str, 颜色名: str) -> str:
    """指定前景色"""
    if 颜色名 not in FOREGROUND_COLORS:
        raise ValueError(f"未知的前景色: {颜色名}")
    return _wrap(文本, FOREGROUND_COLORS[颜色名])


def 背景色(文本: str, 颜色名: str) -> str:
    """指定背景色"""
    if 颜色名 not in BACKGROUND_COLORS:
        raise ValueError(f"未知的背景色: {颜色名}")
    return _wrap(文本, BACKGROUND_COLORS[颜色名])


__all__ = [
    "红色", "绿色", "蓝色", "黄色", "青色", "洋红", "白色", "黑色",
    "高亮", "暗色", "下划线", "闪烁", "重置",
    "样式", "前景色", "背景色",
]
