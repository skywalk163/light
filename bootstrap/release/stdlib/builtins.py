"""
段言标准库 - 内置函数实现

提供文件I/O、路径操作、系统函数等核心功能
"""

import os
import sys
import math
import random
import statistics
import time as _time_module
from datetime import datetime as _datetime_class
from pathlib import Path
from typing import List, Optional, Union


# =============================================================================
# 文件I/O函数
# =============================================================================

def 读取文件(path: str, encoding: str = 'utf-8') -> str:
    """
    读取文件内容
    
    参数:
        path: 文件路径
        encoding: 编码（默认utf-8）
    
    返回:
        文件内容
    
    异常:
        RuntimeError: 文件读取失败
    """
    try:
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        raise RuntimeError(f"文件不存在: '{path}'")
    except PermissionError:
        raise RuntimeError(f"无权限读取文件: '{path}'")
    except Exception as e:
        raise RuntimeError(f"读取文件失败 '{path}': {e}")


def _读文件(path: str) -> str:
    """内部用：读取文件内容（简化版）"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def 写入文件(path: str, content: str, encoding: str = 'utf-8') -> None:
    """
    写入文件内容
    
    参数:
        path: 文件路径
        content: 文件内容
        encoding: 编码（默认utf-8）
    
    异常:
        RuntimeError: 文件写入失败
    """
    try:
        # 确保目录存在
        dir_path = os.path.dirname(path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
    except PermissionError:
        raise RuntimeError(f"无权限写入文件: '{path}'")
    except Exception as e:
        raise RuntimeError(f"写入文件失败 '{path}': {e}")


def 追加文件(path: str, content: str, encoding: str = 'utf-8') -> None:
    """
    追加内容到文件
    
    参数:
        path: 文件路径
        content: 追加内容
        encoding: 编码（默认utf-8）
    """
    try:
        with open(path, 'a', encoding=encoding) as f:
            f.write(content)
    except Exception as e:
        raise RuntimeError(f"追加文件失败 '{path}': {e}")


def 文件存在(path: str) -> bool:
    """检查文件是否存在"""
    return os.path.isfile(path)


def 目录存在(path: str) -> bool:
    """检查目录是否存在"""
    return os.path.isdir(path)


def 路径存在(path: str) -> bool:
    """检查路径是否存在（文件或目录）"""
    return os.path.exists(path)


def 创建目录(path: str) -> None:
    """
    创建目录
    
    参数:
        path: 目录路径
    
    说明:
        自动创建所有父目录
    """
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"创建目录失败 '{path}': {e}")


def 删除文件(path: str) -> None:
    """删除文件"""
    try:
        os.remove(path)
    except FileNotFoundError:
        raise RuntimeError(f"文件不存在: '{path}'")
    except Exception as e:
        raise RuntimeError(f"删除文件失败 '{path}': {e}")


def 删除目录(path: str) -> None:
    """删除空目录"""
    try:
        os.rmdir(path)
    except Exception as e:
        raise RuntimeError(f"删除目录失败 '{path}': {e}")


def 列出目录(path: str = '.') -> List[str]:
    """
    列出目录内容
    
    参数:
        path: 目录路径（默认当前目录）
    
    返回:
        文件名列表
    """
    try:
        return os.listdir(path)
    except Exception as e:
        raise RuntimeError(f"列出目录失败 '{path}': {e}")


def 文件大小(path: str) -> int:
    """
    获取文件大小（字节）
    
    参数:
        path: 文件路径
    
    返回:
        文件大小（字节）
    """
    try:
        return os.path.getsize(path)
    except Exception as e:
        raise RuntimeError(f"获取文件大小失败 '{path}': {e}")


# =============================================================================
# 路径操作函数
# =============================================================================

def 绝对路径(path: str) -> str:
    """获取绝对路径"""
    return os.path.abspath(path)


def 连接路径(*paths: str) -> str:
    """连接多个路径"""
    return os.path.join(*paths)


def 目录名(path: str) -> str:
    """获取路径的目录部分"""
    return os.path.dirname(path)


def 文件名(path: str) -> str:
    """获取路径的文件名部分"""
    return os.path.basename(path)


def 扩展名(path: str) -> str:
    """获取文件扩展名"""
    _, ext = os.path.splitext(path)
    return ext


def 分割路径(path: str) -> tuple:
    """分割路径为(目录, 文件名)"""
    return os.path.split(path)


def 分割扩展名(path: str) -> tuple:
    """分割路径为(主名, 扩展名)"""
    return os.path.splitext(path)


# =============================================================================
# 系统函数
# =============================================================================

def 环境变量(name: str, default: str = None) -> Optional[str]:
    """
    获取环境变量
    
    参数:
        name: 环境变量名
        default: 默认值
    
    返回:
        环境变量值或默认值
    """
    return os.environ.get(name, default)


def 设置环境变量(name: str, value: str) -> None:
    """设置环境变量"""
    os.environ[name] = value


def 参数列表() -> List[str]:
    """获取命令行参数列表"""
    return sys.argv


def 退出程序(code: int = 0) -> None:
    """退出程序"""
    sys.exit(code)


def 当前目录() -> str:
    """获取当前工作目录"""
    return os.getcwd()


def 切换目录(path: str) -> None:
    """切换工作目录"""
    try:
        os.chdir(path)
    except Exception as e:
        raise RuntimeError(f"切换目录失败 '{path}': {e}")


def 执行命令(command: str) -> int:
    """
    执行系统命令
    
    参数:
        command: 命令字符串
    
    返回:
        退出码
    """
    return os.system(command)


# =============================================================================
# 标准输入输出（stdio）
# =============================================================================

def 读取行() -> str:
    """
    从标准输入读取一行

    返回:
        读取的字符串（不含换行符）
    """
    # 注意：Windows subprocess 在 text 模式下会将 \r\n 转换为 \r\r\n
    # 因此需要同时去除 \r 和 \n
    return sys.stdin.readline().rstrip('\r\n')


def 读取N字节(字节数: int) -> str:
    """
    从标准输入读取指定数量的字节
    
    参数:
        字节数: 要读取的字节数
    
    返回:
        读取的字符串
    """
    return sys.stdin.read(字节数)


def 写入输出(text: str) -> None:
    """
    向标准输出写入文本（不含换行）
    
    参数:
        text: 要写入的文本
    """
    sys.stdout.write(text)
    sys.stdout.flush()


def 打印输出(text: str) -> None:
    """
    向标准输出打印文本并换行
    
    参数:
        text: 要打印的文本
    """
    print(text, flush=True)


def 刷新输出() -> None:
    """强制刷新标准输出缓冲区"""
    sys.stdout.flush()


def 写入错误(text: str) -> None:
    """向标准错误写入文本"""
    sys.stderr.write(text)
    sys.stderr.flush()


def 打印错误(text: str) -> None:
    """向标准错误打印文本并换行"""
    print(text, file=sys.stderr, flush=True)


# =============================================================================
# JSON 处理
# =============================================================================

import json as _duan_json_module

def 解析JSON(text: str) -> object:
    """解析 JSON 字符串为段言值"""
    try:
        return _duan_json_module.loads(text)
    except _duan_json_module.JSONDecodeError as e:
        raise RuntimeError(f"JSON 解析失败: {e}")


def 序列化JSON(value: object, 缩进: Optional[int] = None) -> str:
    """将段言值序列化为 JSON 字符串"""
    try:
        if 缩进 is not None:
            return _duan_json_module.dumps(value, ensure_ascii=False, indent=缩进)
        return _duan_json_module.dumps(value, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"JSON 序列化失败: {e}")


def 美化JSON(value: object) -> str:
    """美化 JSON 输出（带缩进）"""
    return 序列化JSON(value, 缩进=2)


# =============================================================================
# 字符串工具函数
# =============================================================================

def 转整数(text: str) -> int:
    """将字符串转换为整数"""
    try:
        return int(text)
    except ValueError:
        raise RuntimeError(f"无法将 '{text}' 转换为整数")


def 转浮点(text: str) -> float:
    """将字符串转换为浮点数"""
    try:
        return float(text)
    except ValueError:
        raise RuntimeError(f"无法将 '{text}' 转换为浮点数")


def 转字符串(value) -> str:
    """将值转换为字符串"""
    return str(value)


def 字符串长度(text: str) -> int:
    """获取字符串长度"""
    return len(text)


def 字符串获取(text: str, index: int) -> str:
    """获取字符串中指定位置的字符"""
    return text[index]


def 截取(text: str, start: int, end: int) -> str:
    """截取字符串的一部分"""
    return text[start:end]


def 分割字符串(text: str, separator: str = None) -> List[str]:
    """分割字符串"""
    return text.split(separator)


def 连接字符串(parts: List[str], separator: str = '') -> str:
    """连接字符串列表"""
    return separator.join(parts)


def 替换字符串(text: str, old: str, new: str) -> str:
    """替换字符串"""
    return text.replace(old, new)


def 去除空白(text: str) -> str:
    """去除首尾空白"""
    return text.strip()


def 转大写(text: str) -> str:
    """转换为大写"""
    return text.upper()


def 转小写(text: str) -> str:
    """转换为小写"""
    return text.lower()


def 字符串包含(text: str, substring: str) -> bool:
    """检查字符串是否包含子串"""
    return substring in text


def 开头(text: str, prefix: str) -> bool:
    """检查字符串是否以指定前缀开头"""
    return text.startswith(prefix)


def 结尾(text: str, suffix: str) -> bool:
    """检查字符串是否以指定后缀结尾"""
    return text.endswith(suffix)


def 查找子串(text: str, substring: str) -> int:
    """查找子串位置，未找到返回-1"""
    return text.find(substring)


def 替换字符串次数(text: str, old: str, new: str, count: int = -1) -> str:
    """替换字符串，指定替换次数"""
    if count < 0:
        return text.replace(old, new)
    return text.replace(old, new, count)


def 截取到末尾(text: str, start: int) -> str:
    """从指定位置截取到字符串末尾"""
    return text[start:]


def 字符串计数(text: str, substring: str) -> int:
    """统计子串出现次数"""
    return text.count(substring)


def 字符串重复(text: str, times: int) -> str:
    """重复字符串指定次数"""
    return text * times


def 字符串反转(text: str) -> str:
    """反转字符串"""
    return text[::-1]


def 转标题(text: str) -> str:
    """转换为标题格式（首字母大写）"""
    return text.title()


def 去除左侧空白(text: str) -> str:
    """去除左侧空白"""
    return text.lstrip()


def 去除右侧空白(text: str) -> str:
    """去除右侧空白"""
    return text.rstrip()


def 字符串对齐居中(text: str, width: int, fillchar: str = ' ') -> str:
    """居中对齐字符串"""
    return text.center(width, fillchar)


def 字符串对齐左(text: str, width: int, fillchar: str = ' ') -> str:
    """左对齐字符串"""
    return text.ljust(width, fillchar)


def 字符串对齐右(text: str, width: int, fillchar: str = ' ') -> str:
    """右对齐字符串"""
    return text.rjust(width, fillchar)


# =============================================================================
# 列表工具函数
# =============================================================================

def 列(*args) -> list:
    """创建包含指定元素的列表"""
    return list(args)


def 列表创建() -> list:
    """创建空列表"""
    return []


def 列表长度(列表) -> int:
    """获取列表长度"""
    return len(列表)


def 列表获取(列表, 索引):
    """获取列表中指定索引的元素"""
    return 列表[索引]


def 列表追加(列表, 元素) -> None:
    """向列表追加元素"""
    列表.append(元素)


def 列表弹出(列表, 索引: int = -1):
    """从列表弹出元素"""
    return 列表.pop(索引)


def 列表插入(列表, 索引, 元素) -> None:
    """在指定索引处插入元素"""
    列表.insert(索引, 元素)


def 列表排序(列表, 反向: bool = False) -> None:
    """排序列表（原地修改）"""
    列表.sort(reverse=反向)


def 列表反转(列表) -> None:
    """反转列表（原地修改）"""
    列表.reverse()


def 列表包含(列表, 元素) -> bool:
    """检查列表是否包含元素"""
    return 元素 in 列表


# =============================================================================
# 字典工具函数
# =============================================================================

def 字典创建() -> dict:
    """创建空字典"""
    return {}


def 字典设置(字典, 键, 值) -> None:
    """设置字典键值"""
    字典[键] = 值


def 字典删除(字典, 键) -> None:
    """删除字典键值"""
    if 键 in 字典:
        del 字典[键]


def 字典键列表(字典) -> list:
    """获取字典的所有键"""
    return list(字典.keys())


def 字典值列表(字典) -> list:
    """获取字典的所有值"""
    return list(字典.values())


def 字典项列表(字典) -> list:
    """获取字典的所有键值对"""
    return list(字典.items())


def 字典包含键(字典, 键) -> bool:
    """检查字典是否包含键"""
    return 键 in 字典


def 字典获取(字典, 键, 默认值=None):
    """从字典获取值，不存在则返回默认值"""
    return 字典.get(键, 默认值)


# =============================================================================
# 类型检查函数
# =============================================================================

def 是整数(值) -> bool:
    """检查是否为整数"""
    return isinstance(值, int) and not isinstance(值, bool)


def 是浮点(值) -> bool:
    """检查是否为浮点数"""
    return isinstance(值, float)


def 是字符串(值) -> bool:
    """检查是否为字符串"""
    return isinstance(值, str)


def 是列表(值) -> bool:
    """检查是否为列表"""
    return isinstance(值, list)


def 是字典(值) -> bool:
    """检查是否为字典"""
    return isinstance(值, dict)


def 是空(值) -> bool:
    """检查是否为空值"""
    return 值 is None


def 是字母(char: str) -> bool:
    """检查字符是否为字母"""
    return str.isalpha(char)


def 是数字(char: str) -> bool:
    """检查字符是否为数字"""
    return str.isdigit(char)


def 是空白(char: str) -> bool:
    """检查字符是否为空格或空白字符"""
    return str.isspace(char)


# =============================================================================
# 日期时间函数
# =============================================================================

def 时间戳() -> float:
    """
    获取当前 Unix 时间戳（秒）
    
    返回:
        浮点数时间戳
    """
    return _time_module.time()


def 格式化时间(时间对象: Union[str, float], 格式: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    将时间戳或时间字符串格式化为指定格式
    
    参数:
        时间对象: Unix 时间戳（浮点数）或 'YYYY-MM-DD HH:MM:SS' 格式字符串
        格式: 目标格式模板
    
    返回:
        格式化后的时间字符串
    """
    if isinstance(时间对象, (int, float)):
        dt = _datetime_class.fromtimestamp(时间对象)
    else:
        # 尝试多种格式解析
        for fmt in [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d',
        ]:
            try:
                dt = _datetime_class.strptime(时间对象, fmt)
                break
            except ValueError:
                continue
        else:
            raise RuntimeError(f"无法解析时间字符串: '{时间对象}'")
    
    return dt.strftime(格式)


# =============================================================================
# 数学/统计/随机函数
# =============================================================================

def 随机整数(最小: int, 最大: int) -> int:
    """
    生成范围内的随机整数
    
    参数:
        最小: 最小值（包含）
        最大: 最大值（包含）
    
    返回:
        随机整数
    """
    return random.randint(最小, 最大)


def 随机浮点() -> float:
    """
    生成 [0.0, 1.0) 范围内的随机浮点数
    
    返回:
        随机浮点数
    """
    return random.random()


def 随机选择(列表) -> Optional[object]:
    """
    从列表中随机选择一个元素
    
    参数:
        列表: 源列表
    
    返回:
        随机选中的元素，列表为空返回空
    """
    if not 列表:
        return None
    return random.choice(列表)


def 阶乘(n: int) -> int:
    """
    计算 n 的阶乘
    
    参数:
        n: 非负整数
    
    返回:
        n!
    """
    if n < 0:
        raise RuntimeError("阶乘参数不能为负数")
    return math.factorial(n)


def 平均数(数据: list) -> float:
    """
    计算列表的平均值
    
    参数:
        数据: 数值列表
    
    返回:
        平均值
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    return statistics.mean(数据)


def 中位数(数据: list) -> float:
    """
    计算列表的中位数
    
    参数:
        数据: 数值列表
    
    返回:
        中位数
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    return statistics.median(数据)


def 众数(数据: list):
    """
    计算列表的众数（出现次数最多的值）
    
    参数:
        数据: 数值列表
    
    返回:
        众数
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    try:
        return statistics.mode(数据)
    except statistics.StatisticsError:
        raise RuntimeError("无法确定众数（多个值出现次数相同）")


def 方差(数据: list) -> float:
    """
    计算总体方差
    
    参数:
        数据: 数值列表
    
    返回:
        方差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.pvariance(数据)


def 标准差(数据: list) -> float:
    """
    计算总体标准差
    
    参数:
        数据: 数值列表
    
    返回:
        标准差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.pstdev(数据)


def 样本方差(数据: list) -> float:
    """
    计算样本方差（分母 n-1）
    
    参数:
        数据: 数值列表
    
    返回:
        样本方差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.variance(数据)


def 样本标准差(数据: list) -> float:
    """
    计算样本标准差（分母 n-1）
    
    参数:
        数据: 数值列表
    
    返回:
        样本标准差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.stdev(数据)


def 求和(数据: list) -> float:
    """
    计算列表中所有数值的和
    
    参数:
        数据: 数值列表
    
    返回:
        总和
    """
    return sum(数据)


def 累积和(数据: list) -> list:
    """
    计算列表的累积和
    
    参数:
        数据: 数值列表
    
    返回:
        累积和列表
    
    示例:
        累积和([1, 2, 3, 4])  # [1, 3, 6, 10]
    """
    result = []
    total = 0
    for v in 数据:
        total += v
        result.append(total)
    return result


def 圆周率() -> float:
    """返回圆周率 π 的近似值"""
    return math.pi


def 自然常数() -> float:
    """返回自然常数 e 的近似值"""
    return math.e


def 角度转弧度(角度: float) -> float:
    """角度转弧度"""
    return math.radians(角度)


def 弧度转角度(弧度: float) -> float:
    """弧度转角度"""
    return math.degrees(弧度)


# =============================================================================
# 导出所有函数
# =============================================================================

__all__ = [
    # 文件I/O
    '读取文件', '写入文件', '追加文件',
    '文件存在', '目录存在', '路径存在',
    '创建目录', '删除文件', '删除目录',
    '列出目录', '文件大小',
    
    # 路径操作
    '绝对路径', '连接路径', '目录名', '文件名',
    '扩展名', '分割路径', '分割扩展名',
    
    # 系统函数
    '环境变量', '设置环境变量', '参数列表',
    '退出程序', '当前目录', '切换目录', '执行命令',

    # 标准输入输出
    '读取行', '读取N字节', '写入输出',
    '打印输出', '刷新输出', '写入错误', '打印错误',

    # JSON 处理
    '解析JSON', '序列化JSON', '美化JSON',

    # 字符串工具

    # 字符串工具
    '转整数', '转浮点', '转字符串',
    '字符串长度', '字符串获取', '分割字符串', '连接字符串',
    '替换字符串', '去除空白',
    '字符串包含', '开头', '结尾', '查找子串',
    '替换字符串次数', '截取到末尾', '字符串计数',
    '字符串重复', '字符串反转', '转标题',
    '去除左侧空白', '去除右侧空白',
    '字符串对齐居中', '字符串对齐左', '字符串对齐右',
    
    # 列表工具
    '列', '列表长度', '列表追加', '列表弹出', '列表插入',
    '列表排序', '列表反转', '列表包含',
    
    # 字典工具
    '字典创建', '字典设置', '字典删除',
    '字典键列表', '字典值列表', '字典项列表',
    '字典包含键', '字典获取',
    
    # 类型检查
    '是整数', '是浮点', '是字符串',
    '是列表', '是字典', '是空',
    '是字母', '是数字', '是空白',
    
    # 数学/统计/随机
    '随机整数', '随机浮点', '随机选择',
    '阶乘', '平均数', '中位数', '众数',
    '方差', '标准差', '样本方差', '样本标准差',
    '求和', '累积和',
    '圆周率', '自然常数',
    '角度转弧度', '弧度转角度',
]
