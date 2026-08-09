"""
光明标准库 - 枚举模块

封装 enum 模块，提供枚举类型定义功能。
"""

import enum
from typing import Any, List, Dict, Optional, Type


class 枚举(enum.Enum):
    """
    枚举基类
    
    用法：
        class 颜色(枚举):
            红色 = 1
            绿色 = 2
            蓝色 = 3
    """
    
    @classmethod
    def 所有成员(cls) -> list:
        """获取所有成员列表"""
        return list(cls)
    
    @classmethod
    def 所有名称(cls) -> List[str]:
        """获取所有成员名称列表"""
        return [成员.name for 成员 in cls]
    
    @classmethod
    def 所有值(cls) -> List[Any]:
        """获取所有成员值列表"""
        return [成员.value for 成员 in cls]
    
    @classmethod
    def 从名称获取(cls, 名称: str) -> Optional['枚举']:
        """根据名称获取枚举成员"""
        try:
            return cls[名称]
        except KeyError:
            return None
    
    @classmethod
    def 从值获取(cls, 值: Any) -> Optional['枚举']:
        """根据值获取枚举成员"""
        try:
            return cls(值)
        except ValueError:
            return None
    
    @classmethod
    def 包含名称(cls, 名称: str) -> bool:
        """检查是否包含指定名称的成员"""
        return 名称 in cls.__members__
    
    @classmethod
    def 包含值(cls, 值: Any) -> bool:
        """检查是否包含指定值的成员"""
        try:
            cls(值)
            return True
        except ValueError:
            return False
    
    @classmethod
    def 成员数量(cls) -> int:
        """获取成员数量"""
        return len(cls)
    
    @classmethod
    def 到字典(cls) -> Dict[str, Any]:
        """转换为字典"""
        return {成员.name: 成员.value for 成员 in cls}
    
    @property
    def 名称(self) -> str:
        """获取成员名称"""
        return self.name
    
    @property
    def 值(self) -> Any:
        """获取成员值"""
        return self.value
    
    def 下一个(self) -> Optional['枚举']:
        """获取下一个成员"""
        成员列表 = list(type(self))
        索引 = 成员列表.index(self)
        if 索引 + 1 < len(成员列表):
            return 成员列表[索引 + 1]
        return None
    
    def 上一个(self) -> Optional['枚举']:
        """获取上一个成员"""
        成员列表 = list(type(self))
        索引 = 成员列表.index(self)
        if 索引 > 0:
            return 成员列表[索引 - 1]
        return None


def 创建枚举(名称: str, 成员: Dict[str, Any]) -> Type[枚举]:
    """
    动态创建枚举类
    
    参数:
        名称: 枚举类名
        成员: {成员名: 值} 字典
    
    返回:
        枚举类
    """
    return enum.Enum(名称, 成员, type=枚举)


def 创建整数枚举(名称: str, 成员列表: List[str], 起始值: int = 1) -> Type[枚举]:
    """
    快速创建整数枚举
    
    参数:
        名称: 枚举类名
        成员列表: 成员名称列表
        起始值: 起始整数值
    
    返回:
        枚举类
    """
    成员字典 = {名称: 起始值 + i for i, 名称 in enumerate(成员列表)}
    return 创建枚举(名称, 成员字典)


class 标志枚举(enum.Flag):
    """标志枚举基类（支持按位运算）"""
    
    @classmethod
    def 所有成员(cls) -> list:
        return list(cls)
    
    @classmethod
    def 从值获取(cls, 值: int) -> '标志枚举':
        return cls(值)
    
    @property
    def 名称(self) -> str:
        return self.name
    
    @property
    def 值(self) -> int:
        return self.value
    
    def 包含(self, 标志: '标志枚举') -> bool:
        """检查是否包含指定标志"""
        return (self.value & 标志.value) == 标志.value
    
    def 添加(self, 标志: '标志枚举') -> '标志枚举':
        """添加标志"""
        return type(self)(self.value | 标志.value)
    
    def 移除(self, 标志: '标志枚举') -> '标志枚举':
        """移除标志"""
        return type(self)(self.value & ~标志.value)


__all__ = [
    '枚举',
    '创建枚举',
    '创建整数枚举',
    '标志枚举',
]
