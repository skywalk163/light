"""
段言（Duan）编程语言 - 中文单位语义内置解析

实现中文计量单位的原生解析支持，使段言源代码中的"数字+单位"表达式
能够被编译器自动识别并换算为标准单位值。

设计原则：
- 语义化：支持日常中文常用的各种单位表达
- 可换算：所有单位均可换算为对应的标准单位基准值
- 可扩展：单位映射表支持动态增删
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# =============================================================================
# 单位表达式数据类
# =============================================================================

@dataclass
class UnitExpression:
    """单位表达式

    表示源代码中的一个"数值+单位"表达式，包含原始文本、数值、
    单位字符串、所属类别以及换算为标准单位后的值。

    Attributes:
        value: 原始数值
        unit: 单位字符串（如"米"、"公斤"、"元"）
        category: 单位类别（货币/时间/距离/重量/容量/数据/速率）
        standard_value: 换算为标准单位的值
        original_text: 原始文本（如"5米"、"3公斤"）
    """
    value: float
    unit: str
    category: str
    standard_value: float
    original_text: str


# =============================================================================
# 单位信息数据类
# =============================================================================

@dataclass
class UnitInfo:
    """单位信息

    定义单个单位的元数据。

    Attributes:
        name: 单位名称
        category: 单位类别
        factor: 相对于标准单位的换算系数（标准单位值 = 数值 × factor）
        standard_unit: 对应的标准单位名称
        aliases: 同义词/别名列表
    """
    name: str
    category: str
    factor: float
    standard_unit: str
    aliases: List[str] = field(default_factory=list)


# =============================================================================
# 单位类别常量
# =============================================================================

CATEGORY_CURRENCY = "货币"
CATEGORY_TIME = "时间"
CATEGORY_DISTANCE = "距离"
CATEGORY_WEIGHT = "重量"
CATEGORY_VOLUME = "容量"
CATEGORY_DATA = "数据"
CATEGORY_SPEED = "速率"


# =============================================================================
# 单位定义映射表
# =============================================================================

# 单位定义映射，包含单位名、所属类别、换算系数（相对于标准单位）
# 标准单位：货币→元、时间→秒、距离→米、重量→千克、容量→升、数据→字节、速率→米/秒
UNIT_MAP: Dict[str, UnitInfo] = {
    # ========== 货币单位（标准单位：元） ==========
    "元": UnitInfo("元", CATEGORY_CURRENCY, 1.0, "元", ["块", "人民币"]),
    "角": UnitInfo("角", CATEGORY_CURRENCY, 0.1, "元", ["毛"]),
    "分": UnitInfo("分", CATEGORY_CURRENCY, 0.01, "元", []),
    "美元": UnitInfo("美元", CATEGORY_CURRENCY, 7.24, "元", ["美金", "刀", "美刀"]),
    "欧元": UnitInfo("欧元", CATEGORY_CURRENCY, 7.89, "元", []),
    "英镑": UnitInfo("英镑", CATEGORY_CURRENCY, 9.18, "元", []),

    # ========== 时间单位（标准单位：秒） ==========
    "秒": UnitInfo("秒", CATEGORY_TIME, 1.0, "秒", []),
    "分钟": UnitInfo("分钟", CATEGORY_TIME, 60.0, "秒", ["分", "分"]),
    "小时": UnitInfo("小时", CATEGORY_TIME, 3600.0, "秒", ["时", "钟头"]),
    "天": UnitInfo("天", CATEGORY_TIME, 86400.0, "秒", ["日", "昼夜"]),
    "周": UnitInfo("周", CATEGORY_TIME, 604800.0, "秒", ["星期", "礼拜"]),
    "月": UnitInfo("月", CATEGORY_TIME, 2592000.0, "秒", ["月份"]),  # 按30天计算
    "年": UnitInfo("年", CATEGORY_TIME, 31536000.0, "秒", ["岁", "年份"]),  # 按365天计算

    # ========== 距离单位（标准单位：米） ==========
    "厘米": UnitInfo("厘米", CATEGORY_DISTANCE, 0.01, "米", ["公分"]),
    "分米": UnitInfo("分米", CATEGORY_DISTANCE, 0.1, "米", []),
    "米": UnitInfo("米", CATEGORY_DISTANCE, 1.0, "米", ["公尺"]),
    "公里": UnitInfo("公里", CATEGORY_DISTANCE, 1000.0, "米", ["千米"]),
    "千米": UnitInfo("千米", CATEGORY_DISTANCE, 1000.0, "米", ["公里"]),
    "里": UnitInfo("里", CATEGORY_DISTANCE, 500.0, "米", ["华里", "市里"]),
    "英里": UnitInfo("英里", CATEGORY_DISTANCE, 1609.344, "米", ["迈"]),

    # ========== 重量单位（标准单位：千克） ==========
    "克": UnitInfo("克", CATEGORY_WEIGHT, 0.001, "千克", ["g"]),
    "千克": UnitInfo("千克", CATEGORY_WEIGHT, 1.0, "千克", ["公斤", "kg"]),
    "公斤": UnitInfo("公斤", CATEGORY_WEIGHT, 1.0, "千克", ["千克", "kg"]),
    "吨": UnitInfo("吨", CATEGORY_WEIGHT, 1000.0, "千克", []),
    "斤": UnitInfo("斤", CATEGORY_WEIGHT, 0.5, "千克", ["市斤"]),
    "两": UnitInfo("两", CATEGORY_WEIGHT, 0.05, "千克", []),

    # ========== 容量单位（标准单位：升） ==========
    "毫升": UnitInfo("毫升", CATEGORY_VOLUME, 0.001, "升", ["ml", "mL"]),
    "升": UnitInfo("升", CATEGORY_VOLUME, 1.0, "升", ["公升", "L", "l"]),

    # ========== 数据处理单位（标准单位：字节） ==========
    "字节": UnitInfo("字节", CATEGORY_DATA, 1.0, "字节", ["B", "byte"]),
    "KB": UnitInfo("KB", CATEGORY_DATA, 1024.0, "字节", ["K", "千字节", "KB"]),
    "MB": UnitInfo("MB", CATEGORY_DATA, 1048576.0, "字节", ["M", "兆字节", "MB"]),  # 1024^2
    "GB": UnitInfo("GB", CATEGORY_DATA, 1073741824.0, "字节", ["G", "吉字节", "GB"]),  # 1024^3
    "TB": UnitInfo("TB", CATEGORY_DATA, 1099511627776.0, "字节", ["T", "太字节", "TB"]),  # 1024^4

    # ========== 速率单位（标准单位：米/秒） ==========
    "米/秒": UnitInfo("米/秒", CATEGORY_SPEED, 1.0, "米/秒", ["m/s", "米每秒"]),
    "公里/小时": UnitInfo("公里/小时", CATEGORY_SPEED, 0.277778, "米/秒", ["千米/小时", "km/h", "km每小时"]),
    "字/分钟": UnitInfo("字/分钟", CATEGORY_SPEED, 1.0 / 60.0, "字/秒", ["字每分", "WPM"]),
}

# 单位别名到标准单位名的映射（用于查找）
UNIT_ALIAS_MAP: Dict[str, str] = {}
for unit_name, unit_info in UNIT_MAP.items():
    UNIT_ALIAS_MAP[unit_name] = unit_name
    for alias in unit_info.aliases:
        if alias not in UNIT_ALIAS_MAP:
            UNIT_ALIAS_MAP[alias] = unit_name


# =============================================================================
# 单位解析器
# =============================================================================

class ChineseUnitParser:
    """中文单位解析器

    从段言源代码中解析出所有"数字+单位"表达式，并提供单位换算功能。

    使用示例：
        >>> parser = ChineseUnitParser()
        >>> exprs = parser.parse_units("5米 3公斤 10秒")
        >>> for expr in exprs:
        ...     print(f"{expr.original_text} = {expr.standard_value} {expr.unit}")
    """

    # 数字模式：匹配整数和小数
    _NUMBER_PATTERN = re.compile(r'\d+(?:\.\d+)?')

    # 单位检测模式（按长度降序排列，确保长单位优先匹配）
    _UNIT_PATTERN_STR = '|'.join(
        sorted(
            (re.escape(name) for name in UNIT_MAP.keys()),
            key=len,
            reverse=True
        )
    )

    # "数字+单位"整体模式
    _UNIT_EXPRESSION_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*(' + _UNIT_PATTERN_STR + r')'
    )

    def __init__(self) -> None:
        """初始化单位解析器"""
        # 单位定义映射（拷贝以避免外部修改影响）
        self._unit_map: Dict[str, UnitInfo] = dict(UNIT_MAP)
        # 别名映射
        self._alias_map: Dict[str, str] = dict(UNIT_ALIAS_MAP)
        # 缓存编译后的正则表达式
        self._refresh_pattern()

    def _refresh_pattern(self) -> None:
        """刷新单位检测模式（当单位映射发生变化时调用）"""
        unit_pattern_str = '|'.join(
            sorted(
                (re.escape(name) for name in self._unit_map.keys()),
                key=len,
                reverse=True
            )
        )
        self._UNIT_EXPRESSION_PATTERN = re.compile(
            r'(\d+(?:\.\d+)?)\s*(' + unit_pattern_str + r')'
        )

    @property
    def unit_map(self) -> Dict[str, UnitInfo]:
        """单位定义映射

        Returns:
            单位名到 UnitInfo 的映射字典
        """
        return dict(self._unit_map)

    def parse_units(self, source: str) -> List[UnitExpression]:
        """从源代码中解析出所有单位表达式

        扫描源代码，找出所有"数字+单位"模式，并返回解析后的单位表达式列表。

        Args:
            source: 段言源代码字符串

        Returns:
            解析出的单位表达式列表，按在源代码中出现的顺序排列
        """
        if not source:
            return []

        expressions: List[UnitExpression] = []
        seen: set = set()  # 去重（避免同一位置重复匹配）

        for match in self._UNIT_EXPRESSION_PATTERN.finditer(source):
            start_pos = match.start()
            if start_pos in seen:
                continue
            seen.add(start_pos)

            value_str = match.group(1)
            unit_str = match.group(2)
            original_text = match.group(0)

            expr = self._build_expression(value_str, unit_str, original_text)
            if expr is not None:
                expressions.append(expr)

        return expressions

    def _build_expression(
        self,
        value_str: str,
        unit_str: str,
        original_text: str
    ) -> Optional[UnitExpression]:
        """构建单位表达式对象

        Args:
            value_str: 数值字符串（如"5"、"3.14"）
            unit_str: 单位字符串（如"米"、"公斤"）
            original_text: 原始匹配文本

        Returns:
            单位表达式对象，如果单位无效则返回 None
        """
        try:
            value = float(value_str)
        except ValueError:
            return None

        # 查找单位信息（支持别名查找）
        unit_info = self._unit_map.get(unit_str)
        if unit_info is None:
            # 尝试通过别名查找
            canonical_name = self._alias_map.get(unit_str)
            if canonical_name is not None:
                unit_info = self._unit_map.get(canonical_name)

        if unit_info is None:
            return None

        standard_value = value * unit_info.factor

        return UnitExpression(
            value=value,
            unit=unit_info.name,
            category=unit_info.category,
            standard_value=standard_value,
            original_text=original_text
        )

    def _detect_unit_pattern(self, source: str) -> List[Tuple[str, str, int]]:
        """检测源码中的"数字+单位"模式

        返回所有匹配到的（数值字符串, 单位字符串, 起始位置）三元组列表。

        Args:
            source: 待检测的源代码字符串

        Returns:
            (数值字符串, 单位字符串, 起始位置) 三元组列表
        """
        results: List[Tuple[str, str, int]] = []
        if not source:
            return results

        for match in self._UNIT_EXPRESSION_PATTERN.finditer(source):
            value_str = match.group(1)
            unit_str = match.group(2)
            start_pos = match.start()
            results.append((value_str, unit_str, start_pos))

        return results

    def convert_to_standard(self, value: float, unit: str) -> Optional[float]:
        """将指定单位的数值换算为标准单位值

        Args:
            value: 数值
            unit: 单位字符串

        Returns:
            换算后的标准单位值，如果单位未知则返回 None
        """
        unit_info = self._unit_map.get(unit)
        if unit_info is None:
            # 尝试通过别名查找
            canonical_name = self._alias_map.get(unit)
            if canonical_name is not None:
                unit_info = self._unit_map.get(canonical_name)
        if unit_info is None:
            return None
        return value * unit_info.factor

    def get_category(self, unit: str) -> Optional[str]:
        """获取单位所属类别

        Args:
            unit: 单位字符串

        Returns:
            单位类别名称，如果单位未知则返回 None
        """
        unit_info = self._unit_map.get(unit)
        if unit_info is None:
            canonical_name = self._alias_map.get(unit)
            if canonical_name is not None:
                unit_info = self._unit_map.get(canonical_name)
        return unit_info.category if unit_info is not None else None

    def add_unit(
        self,
        name: str,
        category: str,
        factor: float,
        standard_unit: str,
        aliases: Optional[List[str]] = None
    ) -> None:
        """动态添加单位定义

        Args:
            name: 单位名称
            category: 单位类别
            factor: 换算系数
            standard_unit: 标准单位名称
            aliases: 别名列表
        """
        info = UnitInfo(
            name=name,
            category=category,
            factor=factor,
            standard_unit=standard_unit,
            aliases=aliases or []
        )
        self._unit_map[name] = info
        # 更新别名映射
        self._alias_map[name] = name
        for alias in (aliases or []):
            if alias not in self._alias_map:
                self._alias_map[alias] = name
        # 刷新正则模式
        self._refresh_pattern()

    def remove_unit(self, name: str) -> bool:
        """移除单位定义

        Args:
            name: 单位名称

        Returns:
            是否成功移除
        """
        if name not in self._unit_map:
            return False
        unit_info = self._unit_map.pop(name)
        # 清理别名映射
        self._alias_map.pop(name, None)
        for alias in unit_info.aliases:
            self._alias_map.pop(alias, None)
        # 刷新正则模式
        self._refresh_pattern()
        return True


# =============================================================================
# 便捷函数
# =============================================================================

_default_parser: Optional[ChineseUnitParser] = None


def get_default_parser() -> ChineseUnitParser:
    """获取全局默认解析器实例

    Returns:
        默认的 ChineseUnitParser 实例
    """
    global _default_parser
    if _default_parser is None:
        _default_parser = ChineseUnitParser()
    return _default_parser


def parse_units(source: str) -> List[UnitExpression]:
    """便捷函数：从源代码中解析单位表达式

    使用全局默认解析器进行单位解析。

    Args:
        source: 段言源代码字符串

    Returns:
        单位表达式列表

    示例：
        >>> parse_units("5米 3公斤 10秒")
        [UnitExpression(value=5.0, unit='米', ...), ...]
    """
    return get_default_parser().parse_units(source)