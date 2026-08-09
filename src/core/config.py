# -*- coding: utf-8 -*-
"""
光明（Light）编译器配置管理
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class OutputFormat(Enum):
    """输出格式"""
    PYTHON = 'python'
    JAVASCRIPT = 'javascript'
    BYTECODE = 'bytecode'


class OptimizationLevel(Enum):
    """优化级别"""
    NONE = 0      # 不优化
    BASIC = 1     # 基本优化
    STANDARD = 2  # 标准优化
    AGGRESSIVE = 3  # 激进优化


class TypeCheckLevel(Enum):
    """类型检查级别"""
    NONE = 0      # 不检查（默认）
    SIGNATURE = 1  # 签名级：仅检查段落参数和返回值类型
    VARIABLE = 2   # 变量级：签名级 + 变量声明类型检查
    EXPRESSION = 3  # 表达式级：变量级 + 表达式运算类型检查


class SegmentTypeMode(Enum):
    """段落类型模式"""
    LOOSE = 'loose'    # 松散模式：无类型标注的段落不做类型检查
    STRICT = 'strict'  # 严格模式：段落强制类型检查


@dataclass
class LightConfig:
    """光明编译器配置"""
    
    # 语言选项
    language: str = 'zh'  # 默认中文
    
    # 输出选项
    output_format: OutputFormat = OutputFormat.PYTHON
    output_file: Optional[str] = None
    
    # 优化选项
    optimization_level: OptimizationLevel = OptimizationLevel.STANDARD
    enable_cache: bool = True
    
    # 调试选项
    debug_mode: bool = False
    verbose: bool = False
    show_ast: bool = False
    show_tokens: bool = False
    
    # 错误处理
    max_errors: int = 100
    warnings_as_errors: bool = False
    
    # 包含路径
    include_paths: List[str] = field(default_factory=list)
    
    # 预定义宏
    defines: Dict[str, Any] = field(default_factory=dict)
    
    # 目标平台
    target_platform: str = 'auto'  # auto, windows, linux, macos
    
    # 运行时选项
    runtime_checks: bool = True
    bounds_checking: bool = True

    # 类型系统选项
    type_check_level: TypeCheckLevel = TypeCheckLevel.NONE
    default_segment_mode: SegmentTypeMode = SegmentTypeMode.LOOSE
    type_inference_mode: str = '渐进'  # 渐进 / 全局 / 禁用
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LightConfig':
        """从字典创建配置"""
        config = cls()
        
        for key, value in config_dict.items():
            if hasattr(config, key):
                # 处理枚举类型
                if key == 'output_format' and isinstance(value, str):
                    value = OutputFormat(value)
                elif key == 'optimization_level' and isinstance(value, (int, str)):
                    if isinstance(value, str):
                        value = OptimizationLevel[value.upper()]
                    else:
                        value = OptimizationLevel(value)
                elif key == 'type_check_level' and isinstance(value, str):
                    value = TypeCheckLevel[value.upper()]
                elif key == 'default_segment_mode' and isinstance(value, str):
                    value = SegmentTypeMode(value)
                
                setattr(config, key, value)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, field):
                result[key] = []
            else:
                result[key] = value
        
        return result
    
    def validate(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        
        # 验证优化级别
        if not isinstance(self.optimization_level, OptimizationLevel):
            errors.append(f"无效的优化级别: {self.optimization_level}")
        
        # 验证输出格式
        if not isinstance(self.output_format, OutputFormat):
            errors.append(f"无效的输出格式: {self.output_format}")
        
        # 验证最大错误数
        if self.max_errors < 1:
            errors.append(f"最大错误数必须大于0: {self.max_errors}")
        
        return errors


# 全局默认配置
DEFAULT_CONFIG = LightConfig()


def get_default_config() -> LightConfig:
    """获取默认配置"""
    return DEFAULT_CONFIG


def set_default_config(config: LightConfig):
    """设置默认配置"""
    global DEFAULT_CONFIG
    DEFAULT_CONFIG = config
