"""
段言标准库 - 外部命令模块

封装 subprocess 模块，提供执行外部命令的便捷接口。
"""

import subprocess
import sys
import os
from typing import List, Dict, Optional, Union, Tuple


class 命令结果:
    """命令执行结果"""
    
    def __init__(self, 返回码: int, 标准输出: str = "", 标准错误: str = ""):
        self.返回码 = 返回码
        self.标准输出 = 标准输出
        self.标准错误 = 标准错误
    
    @property
    def 是否成功(self) -> bool:
        """是否执行成功（返回码为0）"""
        return self.返回码 == 0
    
    def __bool__(self) -> bool:
        return self.是否成功
    
    def __repr__(self) -> str:
        return f"命令结果(返回码={self.返回码}, 成功={self.是否成功})"


def 执行命令(
    命令: Union[str, List[str]],
    捕获输出: bool = True,
    工作目录: str = None,
    环境变量: Dict[str, str] = None,
    超时: float = None,
    编码: str = "utf-8",
) -> 命令结果:
    """
    执行外部命令
    
    参数:
        命令: 命令字符串或命令列表
        捕获输出: 是否捕获标准输出和标准错误
        工作目录: 工作目录
        环境变量: 环境变量字典（会合并到当前环境）
        超时: 超时时间（秒）
        编码: 输出编码
    
    返回:
        命令结果对象
    """
    命令列表 = 命令 if isinstance(命令, list) else 命令
    shell = isinstance(命令, str)
    
    环境 = None
    if 环境变量:
        环境 = dict(os.environ)
        环境.update(环境变量)
    
    try:
        if 捕获输出:
            结果 = subprocess.run(
                命令列表,
                shell=shell,
                capture_output=True,
                text=True,
                encoding=编码,
                cwd=工作目录,
                env=环境,
                timeout=超时,
            )
            return 命令结果(
                返回码=结果.returncode,
                标准输出=结果.stdout or "",
                标准错误=结果.stderr or "",
            )
        else:
            结果 = subprocess.run(
                命令列表,
                shell=shell,
                cwd=工作目录,
                env=环境,
                timeout=超时,
            )
            return 命令结果(返回码=结果.returncode)
    except subprocess.TimeoutExpired as e:
        return 命令结果(
            返回码=-1,
            标准输出=e.stdout.decode(编码, errors='replace') if e.stdout and isinstance(e.stdout, bytes) else (e.stdout or ""),
            标准错误=f"命令超时（{超时}秒）",
        )
    except FileNotFoundError:
        return 命令结果(
            返回码=-1,
            标准错误="命令未找到",
        )
    except Exception as e:
        return 命令结果(
            返回码=-1,
            标准错误=str(e),
        )


def 执行命令并获取输出(
    命令: Union[str, List[str]],
    工作目录: str = None,
    环境变量: Dict[str, str] = None,
    超时: float = None,
    编码: str = "utf-8",
) -> str:
    """
    执行命令并返回标准输出
    
    参数:
        命令: 命令字符串或列表
        工作目录: 工作目录
        环境变量: 环境变量
        超时: 超时时间
        编码: 输出编码
    
    返回:
        标准输出字符串
    """
    结果 = 执行命令(命令, 捕获输出=True, 工作目录=工作目录, 环境变量=环境变量, 超时=超时, 编码=编码)
    return 结果.标准输出.strip()


def 命令是否成功(
    命令: Union[str, List[str]],
    工作目录: str = None,
    超时: float = None,
) -> bool:
    """
    检查命令是否执行成功
    
    参数:
        命令: 命令字符串或列表
        工作目录: 工作目录
        超时: 超时时间
    
    返回:
        是否成功
    """
    结果 = 执行命令(命令, 捕获输出=False, 工作目录=工作目录, 超时=超时)
    return 结果.是否成功


def 管道执行(
    命令列表: List[Union[str, List[str]]],
    捕获输出: bool = True,
    工作目录: str = None,
    编码: str = "utf-8",
) -> 命令结果:
    """
    管道执行多个命令（前一个的输出是后一个的输入）
    
    参数:
        命令列表: 命令列表
        捕获输出: 是否捕获输出
        工作目录: 工作目录
        编码: 输出编码
    
    返回:
        最后一个命令的结果
    """
    if not 命令列表:
        return 命令结果(返回码=-1, 标准错误="命令列表为空")
    
    上一个输出 = None
    最后结果 = 命令结果(返回码=0)
    
    for i, 命令 in enumerate(命令列表):
        cmd = 命令 if isinstance(命令, list) else 命令
        shell = isinstance(命令, str)
        
        输入数据 = 上一个输出.encode(编码) if 上一个输出 is not None else None
        
        try:
            结果 = subprocess.run(
                cmd,
                shell=shell,
                input=输入数据,
                capture_output=捕获输出,
                cwd=工作目录,
            )
            
            if 捕获输出:
                上一个输出 = 结果.stdout.decode(编码, errors='replace') if isinstance(结果.stdout, bytes) else 结果.stdout
                最后结果 = 命令结果(
                    返回码=结果.returncode,
                    标准输出=上一个输出 or "",
                    标准错误=结果.stderr.decode(编码, errors='replace') if isinstance(结果.stderr, bytes) else (结果.stderr or ""),
                )
            else:
                最后结果 = 命令结果(返回码=结果.returncode)
            
            if 结果.returncode != 0:
                break
        except Exception as e:
            最后结果 = 命令结果(返回码=-1, 标准错误=str(e))
            break
    
    return 最后结果


def 后台执行(
    命令: Union[str, List[str]],
    工作目录: str = None,
    环境变量: Dict[str, str] = None,
) -> subprocess.Popen:
    """
    后台执行命令（不等待完成）
    
    参数:
        命令: 命令字符串或列表
        工作目录: 工作目录
        环境变量: 环境变量
    
    返回:
        Popen对象
    """
    cmd = 命令 if isinstance(命令, list) else 命令
    shell = isinstance(命令, str)
    
    环境 = None
    if 环境变量:
        环境 = dict(os.environ)
        环境.update(环境变量)
    
    return subprocess.Popen(
        cmd,
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=工作目录,
        env=环境,
    )


def 等待进程(进程: subprocess.Popen, 超时: float = None) -> 命令结果:
    """
    等待后台进程完成
    
    参数:
        进程: Popen对象
        超时: 超时时间
    
    返回:
        命令结果
    """
    try:
        标准输出, 标准错误 = 进程.沟通(timeout=超时)
        return 命令结果(
            返回码=进程.returncode,
            标准输出=标准输出.decode('utf-8', errors='replace') if isinstance(标准输出, bytes) else (标准输出 or ""),
            标准错误=标准错误.decode('utf-8', errors='replace') if isinstance(标准错误, bytes) else (标准错误 or ""),
        )
    except subprocess.TimeoutExpired:
        进程.kill()
        return 命令结果(返回码=-1, 标准错误=f"进程超时（{超时}秒）")


def 命令存在(命令名: str) -> bool:
    """
    检查命令是否存在（在PATH中可找到）
    
    参数:
        命令名: 命令名称
    
    返回:
        是否存在
    """
    if os.name == 'nt':
        命令 = f"where {命令名}"
    else:
        命令 = f"which {命令名}"
    
    return 命令是否成功(命令)


__all__ = [
    '命令结果',
    '执行命令',
    '执行命令并获取输出',
    '命令是否成功',
    '管道执行',
    '后台执行',
    '等待进程',
    '命令存在',
]
