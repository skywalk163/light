"""
光明标准库 - 参数解析模块

封装 argparse 模块，提供命令行参数解析功能。
"""

import argparse
import sys
from typing import List, Dict, Optional, Any, Tuple


class 参数解析器:
    """命令行参数解析器"""
    
    def __init__(self, 程序名: str = None, 描述: str = "", 版本: str = None):
        """
        初始化参数解析器
        
        参数:
            程序名: 程序名称
            描述: 程序描述
            版本: 版本号
        """
        self._解析器 = argparse.ArgumentParser(
            prog=程序名,
            description=描述,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        self._参数 = {}
        self._已解析 = False
        self._解析结果 = None
        
        if 版本:
            self._解析器.add_argument('--version', action='version', version=版本)
    
    def 添加参数(
        self,
        名称: str,
        短名称: str = None,
        类型: type = str,
        默认值: Any = None,
        描述: str = "",
        必需: bool = False,
        取值列表: List[Any] = None,
        多值: bool = False,
        标志: bool = False,
        计数: bool = False,
    ) -> None:
        """
        添加命令行参数
        
        参数:
            名称: 参数名称（长选项）
            短名称: 短选项名称
            类型: 参数类型
            默认值: 默认值
            描述: 参数描述
            必需: 是否必需
            取值列表: 允许的取值列表
            多值: 是否接受多个值
            标志: 是否为布尔标志
            计数: 是否为计数参数（如 -vvv）
        """
        参数列表 = []
        是否位置参数 = False
        
        if 短名称:
            if not 短名称.startswith('-'):
                参数列表.append(f"-{短名称}")
            else:
                参数列表.append(短名称)
        
        if 名称.startswith('--'):
            参数列表.append(名称)
            目标名 = 名称.lstrip('--').replace('-', '_')
        elif 名称.startswith('-'):
            参数列表.append(名称)
            目标名 = 名称.lstrip('-').replace('-', '_')
        else:
            # 位置参数
            参数列表.append(名称)
            目标名 = 名称.replace('-', '_')
            是否位置参数 = True
        
        kwargs = {'help': 描述}
        if not 是否位置参数:
            kwargs['dest'] = 目标名
        
        if 标志:
            kwargs['action'] = 'store_true'
        elif 计数:
            kwargs['action'] = 'count'
            kwargs['default'] = 0
        else:
            kwargs['type'] = 类型
            if 默认值 is not None:
                kwargs['default'] = 默认值
            if 取值列表:
                kwargs['choices'] = 取值列表
            if 多值:
                kwargs['nargs'] = '+' if 必需 else '*'
            if 必需 and len(参数列表) > 0 and 参数列表[0].startswith('-'):
                kwargs['required'] = True
        
        self._参数[目标名] = {'类型': 类型, '默认值': 默认值}
        self._解析器.add_argument(*参数列表, **kwargs)
    
    def 添加位置参数(
        self,
        名称: str,
        类型: type = str,
        默认值: Any = None,
        描述: str = "",
        可选: bool = False,
        多值: bool = False,
    ) -> None:
        """
        添加位置参数
        
        参数:
            名称: 参数名称
            类型: 参数类型
            默认值: 默认值
            描述: 参数描述
            可选: 是否可选
            多值: 是否接受多个值
        """
        kwargs = {'help': 描述, 'type': 类型}
        if 可选:
            kwargs['nargs'] = '?'
            kwargs['default'] = 默认值
        if 多值:
            kwargs['nargs'] = '*'
        
        self._解析器.add_argument(名称, **kwargs)
    
    def 添加子命令(self, 名称: str, 描述: str = "") -> '参数解析器':
        """
        添加子命令
        
        参数:
            名称: 子命令名称
            描述: 子命令描述
        
        返回:
            子命令的参数解析器
        """
        if not hasattr(self, '_子解析器'):
            self._子解析器 = self._解析器.add_subparsers(dest='子命令')
        
        子解析器 = self._子解析器.add_parser(名称, help=描述)
        子封装 = 参数解析器.__new__(参数解析器)
        子封装._解析器 = 子解析器
        子封装._参数 = {}
        子封装._已解析 = False
        子封装._解析结果 = None
        return 子封装
    
    def 解析(self, 参数列表: List[str] = None) -> Dict[str, Any]:
        """
        解析命令行参数
        
        参数:
            参数列表: 参数列表，默认为sys.argv[1:]
        
        返回:
            参数字典
        """
        args = self._解析器.parse_args(参数列表)
        self._解析结果 = args
        self._已解析 = True
        return vars(args)
    
    def 获取(self, 参数名: str, 默认值: Any = None) -> Any:
        """
        获取解析后的参数值
        
        参数:
            参数名: 参数名称
            默认值: 不存在时的默认值
        
        返回:
            参数值
        """
        if not self._已解析:
            self.解析()
        return getattr(self._解析结果, 参数名.replace('-', '_'), 默认值)
    
    def 打印帮助(self) -> None:
        """打印帮助信息"""
        self._解析器.print_help()
    
    def 帮助文本(self) -> str:
        """获取帮助文本"""
        return self._解析器.format_help()
    
    def 用法文本(self) -> str:
        """获取用法文本"""
        return self._解析器.format_usage()


def 简单解析(参数定义: List[Dict[str, Any]], 参数列表: List[str] = None) -> Dict[str, Any]:
    """
    简单参数解析（便捷函数）
    
    参数:
        参数定义: 参数定义列表，每个元素是字典
        参数列表: 要解析的参数列表
    
    返回:
        参数字典
    
    示例:
        参数定义 = [
            {'名称': '文件', '描述': '输入文件'},
            {'名称': '--输出', '短名称': '-o', '描述': '输出文件'},
            {'名称': '-- verbose', '短名称': '-v', '标志': True, '描述': '详细输出'},
        ]
    """
    解析器 = 参数解析器()
    for 定义 in 参数定义:
        解析器.添加参数(**定义)
    return 解析器.解析(参数列表)


def 快速获取(参数名: str, 默认值: Any = None, 参数列表: List[str] = None) -> Any:
    """
    快速获取单个参数值
    
    参数:
        参数名: 参数名（如 '--output' 或 'filename'）
        默认值: 默认值
        参数列表: 参数列表
    
    返回:
        参数值
    """
    解析器 = 参数解析器()
    if 参数名.startswith('--'):
        解析器.添加参数(参数名, 默认值=默认值)
    else:
        解析器.添加位置参数(参数名, 默认值=默认值, 可选=True)
    结果 = 解析器.解析(参数列表)
    return 结果.get(参数名.lstrip('--').replace('-', '_'), 默认值)


__all__ = [
    '参数解析器',
    '简单解析',
    '快速获取',
]
