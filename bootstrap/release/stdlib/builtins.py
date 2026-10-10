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
    """将值转换为字符串（L-072 方案A：光明相输出，容器发 JSON）

    口径与 stdlib/内置核心转换.light:29 的规范真身逐字一致：
      * True / False / None → "真" / "假" / "空"（不是 Python 的 True/False/None）
      * str → 原样返回，不加引号（日志与错误消息拼接依赖）
      * dict / list → JSON 文本（双引号、ensure_ascii=False 保中文、紧凑无缩进）
      * 其余 → str() 兜底
    bool 必须在 int 之前判——Python 里 bool 是 int 的子类。
    序列化失败退回 str()：转字符串 常在错误路径上，不许自己再抛错盖掉原故障。
    """
    if value is None:
        return "空"
    if value is True:
        return "真"
    if value is False:
        return "假"
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        try:
            return _duan_json_module.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
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
    """检查字符是否为数字。
    LP-D-019② 裁定（SRC 对齐文档）：是数字符 判单个字符，对齐 ANTLR 的 len==1 守卫。
    非单字符（如 "12"）一律判假。"""
    if len(char) != 1:
        return False
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


# ===== R114-S1 sync_builtins.py 自动生成段（勿手改；由 scripts/sync_builtins.py 重生成）=====

# --- 下列函数由 scripts/sync_builtins.py 从真源 stdlib/builtins.py 逐字补齐 ---
def 是文件(path: str) -> bool:
    """检查是否为文件"""
    return os.path.isfile(path)

def 列出文件(path: str = '.') -> List[str]:
    """
    列出目录中的文件（不包含子目录）
    
    参数:
        path: 目录路径（默认当前目录）
    
    返回:
        文件名列表（仅文件）
    """
    try:
        return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    except Exception as e:
        raise RuntimeError(f"列出文件失败 '{path}': {e}")

def 移动文件系统(source: str, target: str) -> None:
    """
    移动文件或目录
    
    参数:
        source: 源路径
        target: 目标路径
    """
    import shutil
    shutil.move(source, target)


# =============================================================================
# 标准输入输出（stdio）
# =============================================================================

def 切片下标检查(v):
    """L-080：切片下标必须是整数；非 int 给出明确中文错误（替代 Python 原生 slice indices 报错误导）"""
    if isinstance(v, bool) or isinstance(v, int):
        return v
    if isinstance(v, float):
        名 = '浮点数'
    elif v is None:
        名 = '空值'
    elif isinstance(v, str):
        名 = '文本'
    elif isinstance(v, list):
        名 = '列表'
    elif isinstance(v, dict):
        名 = '字典'
    else:
        名 = type(v).__name__
    raise TypeError('切片下标必须是整数，实际为' + 名 + ' ' + str(v) + '，请用 整数() 转换')

def 显示宽度(text) -> int:
    """
    返回字符串在等宽终端中的显示宽度。

    中文、日文、韩文及全角字符占 2 个单元格，ASCII 及半角字符占 1 个。
    用于终端边框、表格的对齐（用「显示宽度」替代「字符串长度」算填充）。

    示例:
        显示宽度("中文abc")  -> 7   (中=2, 文=2, a/b/c=1)
        显示宽度("hello")    -> 5
    """
    import unicodedata
    _WIDE_RANGES = (
        (0x1100, 0x115F),   # Hangul Jamo
        (0x2E80, 0xA4CF),   # CJK 部首补充 / 康熙部首 / 表意文字描述符 / 中日韩符号和标点
        (0xAC00, 0xD7A3),   # Hangul 音节
        (0xF900, 0xFAFF),   # CJK 兼容象形文字
        (0xFE30, 0xFE4F),   # CJK 兼容形式
        (0xFF00, 0xFF60),   # 全角 ASCII
        (0xFFE0, 0xFFE6),   # 全角符号
        (0x3000, 0x303F),   # CJK 符号和标点
        (0x3040, 0x30FF),   # 平假名 / 片假名
        (0x3400, 0x4DBF),   # CJK 扩展 A
        (0x4E00, 0x9FFF),   # CJK 统一表意文字
        (0x20000, 0x2FFFF), # CJK 扩展 B+
    )
    width = 0
    for ch in str(text):
        o = ord(ch)
        wide = any(lo <= o <= hi for lo, hi in _WIDE_RANGES)
        if not wide:
            try:
                wide = unicodedata.east_asian_width(ch) in ('W', 'F')
            except Exception:
                wide = False
        width += 2 if wide else 1
    return width

def 深拷贝(原):
    """深拷贝：递归复制所有嵌套字典/列表，结果与原对象完全脱钩（不共享子对象引用）。"""
    import copy as _拷贝模块
    return _拷贝模块.deepcopy(原)

def 冻结(原):
    """冻结（脱钩）：返回深拷贝，使调用方后续改动不影响已构造对象（深 freeze 语义）。"""
    import copy as _拷贝模块
    return _拷贝模块.deepcopy(原)

def 真实路径(路径: str) -> str:
    """解析符号链接 / junction / .. / 8.3 短名，返回规范化真实路径（os.path.realpath）"""
    return os.path.realpath(路径)

def 文件状态(路径):
    """按路径取文件元数据（os.stat）。取不到（不存在/无权限）返回空，不抛。

    状态对象即 Python 的 os.stat_result，透明暴露 硬链接数(st_nlink) /
    设备号(st_dev) / 节点号(st_ino) / 大小 / 是目录，供护栏 TOCTOU 身份比对。
    """
    try:
        return os.stat(路径)
    except Exception:
        return None

def 句柄状态(句柄):
    """按已打开的文件描述符取元数据（os.fstat）。取不到返回空，不抛。

    与 文件状态 的区别全在于「从已持有的句柄回查」，避免再开一个 TOCTOU 窗口。
    """
    try:
        return os.fstat(句柄)
    except Exception:
        return None

def 低级打开(路径: str, 标志位: int, 模式: int) -> int:
    """按标志位打开文件，返回整数文件描述符（os.open）。失败抛错。"""
    return os.open(路径, 标志位, 模式)

def 低级读(句柄: int, 字节数: int) -> bytes:
    """从描述符读至多 字节数 个字节，返回字节串（os.read）；读到末尾返回空字节串。"""
    return os.read(句柄, 字节数)

def 低级写(句柄: int, 字节) -> int:
    """向描述符写字节串，返回实际写入字节数（os.write）。"""
    return os.write(句柄, 字节)

def 低级关闭(句柄: int) -> None:
    """关闭描述符（os.close）。"""
    os.close(句柄)

def 随机字节(个数: int) -> bytes:
    """返回 个数 个密码学安全的随机字节（os.urandom）。"""
    return os.urandom(个数)

def 原子替换(源: str, 目标: str) -> None:
    """同卷内原子改名，目标已存在则原子覆盖（os.replace）。"""
    os.replace(源, 目标)

def 环境枚举():
    """列出当前进程全部环境变量，返回 [[名, 值], ...]（os.environ.items()）。"""
    return [[名, 值] for 名, 值 in os.environ.items()]

def 单调时钟() -> float:
    """返回只增不减、不受系统时钟调整影响的秒数（time.monotonic）。绝对值无意义，只用于求差。"""
    return _time_module.monotonic()

def 常量时间比较(甲, 乙) -> bool:
    """以不随输入内容变化的时间比较两个字符串/字节是否相等（hmac.compare_digest），防时序侧信道。"""
    import hmac
    return hmac.compare_digest(甲, 乙)


# ---- 8 个打开标志常量（跨平台，以零参函数形态落地） ----

def 只读() -> int:
    """打开标志：只读（os.O_RDONLY）。"""
    return os.O_RDONLY

def 只写() -> int:
    """打开标志：只写（os.O_WRONLY）。"""
    return os.O_WRONLY

def 新建() -> int:
    """打开标志：不存在则创建（os.O_CREAT）。"""
    return os.O_CREAT

def 截断() -> int:
    """打开标志：已存在则清空到零长度（os.O_TRUNC）。"""
    return os.O_TRUNC

def 追加() -> int:
    """打开标志：每次写都定位到文件末尾（os.O_APPEND）。"""
    return os.O_APPEND

def 独占() -> int:
    """打开标志：与 新建 合用时目标已存在则失败（os.O_EXCL）。"""
    return os.O_EXCL

def 二进制() -> int:
    """打开标志：字节透传不做换行转换。仅 Windows 存在（os.O_BINARY），POSIX 上无此概念、返回 0。"""
    return os.O_BINARY if hasattr(os, "O_BINARY") else 0

def 不跟随符号链接() -> int:
    """打开标志：末段是符号链接则直接失败。仅 POSIX 存在（os.O_NOFOLLOW），Windows 上返回 0。"""
    return os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0


# =============================================================================
# 导出所有函数
# =============================================================================

def container_get(d, key, default=None):
    """字典安全取值（惰性辅助，避免与内置 get 语义冲突）。"""
    try:
        return d.get(key, default)
    except Exception:
        return default

def 写入二进制文件(路径: str, 数据) -> None:
    """写入二进制文件：数据应为 bytes。"""
    import os
    d = os.path.dirname(路径)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    with open(路径, 'wb') as _f:
        _f.write(数据 if isinstance(数据, (bytes, bytearray)) else str(数据).encode('utf-8'))

def 读二进制文件(路径: str) -> bytes:
    """读取二进制文件，返回 bytes。"""
    with open(路径, 'rb') as _f:
        return _f.read()

def 创建临时目录(后缀=None, 前缀=None, 目录=None) -> str:
    """创建并返回一个新的临时目录路径。

    R128-A：原签名 0 参，但 lightharness 侧已按 3 参语义调用（对齐
    light-merge stdlib/临时文件.light 的 `创建临时目录(后缀, 前缀, 目录)`），
    旧签名会让 `创建临时目录("lh_sc_test")` 抛 TypeError。此处补齐为
    **向后兼容**的 3 参版本（全默认 → 行为与旧 0 参完全一致）。
    """
    import tempfile
    return tempfile.mkdtemp(suffix=后缀 or '', prefix=前缀 or '', dir=目录)

def 删目录树(路径: str) -> None:
    """递归删除目录树（含子目录与文件）。"""
    import shutil
    shutil.rmtree(路径, ignore_errors=False)

def 复制文件(源: str, 目标: str) -> None:
    """复制文件（保留元数据）。"""
    import shutil
    shutil.copy2(源, 目标)

def 复制目录(源: str, 目标: str) -> None:
    """递归复制目录。"""
    import shutil
    shutil.copytree(源, 目标)

def 重命名(源: str, 目标: str) -> None:
    """重命名/移动文件或目录。"""
    import os
    os.rename(源, 目标)

def 排序列表(序列, 反向: bool = False):
    """返回排序后的新列表（不原地修改）。"""
    return sorted(序列, reverse=bool(反向))


# 英文别名：code_generator 的 method_name_map 将光明方法名「排序」映射为 `sort`
# （`_light_builtin.排序(数据)` → `_light_builtin.sort(数据)`），且 stdlib/统计.light
# 百分位数/中位数依赖「排序后返回新列表」语义，故此处补 `sort` 指向 排序列表。

def 查找目录列表(路径: str = '.', 样式=None, 递归=False) -> list:
    """列出目录下的条目名（等价 列出目录）。

    R128-A：原签名只收 1 参，但 lightharness 侧已按 3 参语义调用
    （`src/文件.light:83` 的 `查找文件(目录, 样式, 递归)` 需要 glob 样式匹配 +
    递归开关），旧签名会让 3 参调用抛 TypeError。此处补齐为**向后兼容**的
    3 参版本：
      · 样式 为 None（默认）→ 行为与旧 1 参完全一致（返回条目名列表）；
      · 样式 非空 → 按 fnmatch 通配匹配文件名，返回**完整路径**列表；
        `递归=真` 时走 os.walk 遍历子目录，`假` 时只看顶层且只收文件。
    """
    import os
    if 样式 is None:
        return os.listdir(路径)
    import fnmatch
    结果 = []
    if 递归:
        for 根, _目录们, 文件们 in os.walk(路径):
            for 名 in 文件们:
                if fnmatch.fnmatch(名, 样式):
                    结果.append(os.path.join(根, 名))
    else:
        for 名 in os.listdir(路径):
            全路径 = os.path.join(路径, 名)
            if os.path.isfile(全路径) and fnmatch.fnmatch(名, 样式):
                结果.append(全路径)
    return 结果

def 取可选(容器, 键, 默认=None):
    """安全取字段：字典用 get，对象用 getattr，异常回落默认（空）。"""
    try:
        if isinstance(容器, dict):
            return container_get(容器, 键, 默认)
        return getattr(容器, 键, 默认)
    except Exception:
        return 默认

# --- 下列为 boot 自包含移植体（真源为地板转发式，release 环境无光导入钩子，语义对齐 内置核心*.light 真身）---
def 最后索引(text: str, substring: str) -> int:
    """查找子串最后出现位置，未找到返回 -1（R114-S1 boot 自包含移植：对齐 内置核心字符串.最后索引）"""
    return str.rfind(text, substring)

def 副本(原):
    """浅拷贝：字典浅拷贝键值对、列表浅拷贝元素、其他类型原样返回（R114-S1 boot 自包含移植：对齐 内置核心列表.副本）"""
    import copy as _拷贝模块
    return _拷贝模块.copy(原)

def 浅拷贝(原):
    """浅拷贝（R114-S1 boot 自包含移植：对齐 内置核心列表.浅拷贝）"""
    import copy as _拷贝模块
    return _拷贝模块.copy(原)

def 是字节(值) -> bool:
    """检查是否为字节串（bytes）。R114-S1 boot 自包含移植：对齐 内置核心判型.是字节。"""
    return isinstance(值, bytes)

def 是布尔(值) -> bool:
    """检查是否为布尔值。R114-S1 boot 自包含移植：对齐 内置核心判型.是布尔。"""
    return isinstance(值, bool)

def 是函数(值) -> bool:
    """检查是否为可调用对象（函数/方法/lambda）。R114-S1 boot 自包含移植：对齐 内置核心判型.是函数。"""
    return callable(值)

def 是数值(值) -> bool:
    """检查是否为数值类型（int/float，排除 bool）。R114-S1 boot 自包含移植：对齐 内置核心判型.是数值。"""
    if isinstance(值, bool):
        return False
    return isinstance(值, (int, float))

def 字符串全数字(串) -> bool:
    """检查整个字符串是否全由数字字符组成（空串/非 str 判假）。R114-S1 boot 自包含移植：对齐 内置核心判型.字符串全数字。"""
    if not isinstance(串, str):
        return False
    if len(串) == 0:
        return False
    return 串.isdigit()

def 是负零(值) -> bool:
    """检查 IEEE 754 负零（-0.0）；正零/整数 0/非零数均判假。R114-S1 boot 自包含移植：对齐 内置核心判型.是负零。"""
    if not isinstance(值, float):
        return False
    if 值 != 0.0:
        return False
    return str(值).startswith("-")

def 主目录() -> str:
    """获取当前用户主目录。R114-S1 boot 自包含移植：对齐 内置核心系统.主目录。"""
    return os.path.expanduser("~")

def 随机UUID() -> str:
    """生成随机 UUID v4 字符串。R114-S1 boot 自包含移植：对齐 内置核心系统.随机UUID。"""
    import uuid
    return str(uuid.uuid4())

# ===== R114-S1 sync_builtins.py 自动生成段结束 =====

__all__ = [
    '读取文件',
    '_读文件',
    '写入文件',
    '追加文件',
    '文件存在',
    '是文件',
    '目录存在',
    '路径存在',
    '创建目录',
    '删除文件',
    '删除目录',
    '列出目录',
    '列出文件',
    '文件大小',
    '绝对路径',
    '连接路径',
    '目录名',
    '文件名',
    '扩展名',
    '分割路径',
    '分割扩展名',
    '环境变量',
    '设置环境变量',
    '参数列表',
    '退出程序',
    '当前目录',
    '切换目录',
    '执行命令',
    '移动文件系统',
    '读取行',
    '读取N字节',
    '写入输出',
    '打印输出',
    '刷新输出',
    '写入错误',
    '打印错误',
    '解析JSON',
    '序列化JSON',
    '美化JSON',
    '转整数',
    '切片下标检查',
    '转浮点',
    '转字符串',
    '字符串长度',
    '显示宽度',
    '字符串获取',
    '截取',
    '分割字符串',
    '连接字符串',
    '替换字符串',
    '去除空白',
    '转大写',
    '转小写',
    '字符串包含',
    '开头',
    '结尾',
    '查找子串',
    '最后索引',
    '替换字符串次数',
    '截取到末尾',
    '字符串计数',
    '字符串重复',
    '字符串反转',
    '转标题',
    '去除左侧空白',
    '去除右侧空白',
    '字符串对齐居中',
    '字符串对齐左',
    '字符串对齐右',
    '列',
    '列表创建',
    '列表长度',
    '列表获取',
    '列表追加',
    '列表弹出',
    '列表插入',
    '列表排序',
    '列表反转',
    '列表包含',
    '副本',
    '浅拷贝',
    '深拷贝',
    '冻结',
    '字典创建',
    '字典设置',
    '字典删除',
    '字典键列表',
    '字典值列表',
    '字典项列表',
    '字典包含键',
    '字典获取',
    '是整数',
    '是浮点',
    '是字符串',
    '是列表',
    '是字典',
    '是字节',
    '是空',
    '是字母',
    '是数字',
    '是空白',
    '是布尔',
    '是函数',
    '是数值',
    '字符串全数字',
    '是负零',
    '时间戳',
    '格式化时间',
    '随机整数',
    '随机浮点',
    '随机选择',
    '阶乘',
    '平均数',
    '中位数',
    '众数',
    '方差',
    '标准差',
    '样本方差',
    '样本标准差',
    '求和',
    '累积和',
    '圆周率',
    '自然常数',
    '角度转弧度',
    '弧度转角度',
    '真实路径',
    '文件状态',
    '句柄状态',
    '低级打开',
    '低级读',
    '低级写',
    '低级关闭',
    '随机字节',
    '原子替换',
    '环境枚举',
    '单调时钟',
    '常量时间比较',
    '只读',
    '只写',
    '新建',
    '截断',
    '追加',
    '独占',
    '二进制',
    '不跟随符号链接',
    'container_get',
    '写入二进制文件',
    '读二进制文件',
    '创建临时目录',
    '删目录树',
    '复制文件',
    '复制目录',
    '重命名',
    '排序列表',
    '查找目录列表',
    '取可选',
    '主目录',
    '随机UUID',
]
