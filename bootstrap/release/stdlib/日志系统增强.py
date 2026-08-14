"""
日志系统增强模块 - 分级、滚动、格式化

提供增强的日志功能，包括：
- 日志分级（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- 滚动日志（按大小、按时间）
- 多种输出格式
- 日志过滤
- 自定义处理器
"""
import logging
import logging.handlers
import sys
import os
import time as _time
from typing import Optional, Dict, Any, TextIO, Callable


class 日志级别:
    """日志级别常量"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    
    级别名称 = {
        DEBUG: 'DEBUG',
        INFO: 'INFO',
        WARNING: 'WARNING',
        ERROR: 'ERROR',
        CRITICAL: 'CRITICAL'
    }


class 日志格式化器:
    """日志格式化器"""
    
    @staticmethod
    def 创建标准格式(包含时间: bool = True, 包含级别: bool = True, 
                      包含模块: bool = True, 包含线程: bool = False) -> logging.Formatter:
        """创建标准日志格式"""
        格式部分 = []
        
        if 包含时间:
            格式部分.append('%(asctime)s')
        if 包含级别:
            格式部分.append('%(levelname)s')
        if 包含模块:
            格式部分.append('%(name)s')
        if 包含线程:
            格式部分.append('%(threadName)s')
        
        格式部分.append('%(message)s')
        
        return logging.Formatter(' | '.join(格式部分))
    
    @staticmethod
    def 创建JSON格式() -> logging.Formatter:
        """创建JSON格式"""
        return logging.Formatter(
            '{"时间":"%(asctime)s","级别":"%(levelname)s","模块":"%(name)s","消息":"%(message)s"}'
        )
    
    @staticmethod
    def 创建简洁格式() -> logging.Formatter:
        """创建简洁格式"""
        return logging.Formatter('%(levelname)s: %(message)s')
    
    @staticmethod
    def 创建详细格式() -> logging.Formatter:
        """创建详细格式"""
        return logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s'
        )


class 日志处理器:
    """日志处理器工厂"""
    
    @staticmethod
    def 创建控制台处理器(级别: int = logging.DEBUG, 
                           格式化器: logging.Formatter = None) -> logging.Handler:
        """创建控制台处理器"""
        处理器 = logging.StreamHandler(sys.stdout)
        处理器.setLevel(级别)
        
        if 格式化器:
            处理器.setFormatter(格式化器)
        
        return 处理器
    
    @staticmethod
    def 创建文件处理器(文件名: str, 级别: int = logging.DEBUG,
                        格式化器: logging.Formatter = None, 
                        编码: str = 'utf-8') -> logging.Handler:
        """创建文件处理器"""
        处理器 = logging.FileHandler(文件名, encoding=编码)
        处理器.setLevel(级别)
        
        if 格式化器:
            处理器.setFormatter(格式化器)
        
        return 处理器
    
    @staticmethod
    def 创建滚动文件处理器(文件名: str, 级别: int = logging.DEBUG,
                           格式化器: logging.Formatter = None,
                           最大大小: int = 1024 * 1024 * 10,
                           备份数量: int = 5,
                           编码: str = 'utf-8') -> logging.handlers.RotatingFileHandler:
        """创建按大小滚动的文件处理器"""
        处理器 = logging.handlers.RotatingFileHandler(
            文件名, maxBytes=最大大小, backupCount=备份数量, encoding=编码
        )
        处理器.setLevel(级别)
        
        if 格式化器:
            处理器.setFormatter(格式化器)
        
        return 处理器
    
    @staticmethod
    def 创建时间滚动处理器(文件名: str, 级别: int = logging.DEBUG,
                           格式化器: logging.Formatter = None,
                           间隔: str = 'D',
                           备份数量: int = 7,
                           编码: str = 'utf-8') -> logging.handlers.TimedRotatingFileHandler:
        """创建按时间滚动的文件处理器"""
        处理器 = logging.handlers.TimedRotatingFileHandler(
            文件名, when=间隔, backupCount=备份数量, encoding=编码
        )
        处理器.setLevel(级别)
        
        if 格式化器:
            处理器.setFormatter(格式化器)
        
        return 处理器


class 日志过滤器:
    """日志过滤器"""
    
    def __init__(self, 允许级别列表: list = None, 拒绝级别列表: list = None,
                 包含关键词: list = None, 排除关键词: list = None):
        self._允许级别列表 = 允许级别列表
        self._拒绝级别列表 = 拒绝级别列表
        self._包含关键词 = 包含关键词
        self._排除关键词 = 排除关键词
    
    def filter(self, 记录: logging.LogRecord) -> bool:
        """过滤日志记录"""
        if self._允许级别列表 and 记录.levelno not in self._允许级别列表:
            return False
        
        if self._拒绝级别列表 and 记录.levelno in self._拒绝级别列表:
            return False
        
        if self._包含关键词:
            包含 = any(关键词 in 记录.getMessage() for 关键词 in self._包含关键词)
            if not 包含:
                return False
        
        if self._排除关键词:
            for 关键词 in self._排除关键词:
                if 关键词 in 记录.getMessage():
                    return False
        
        return True


class 日志记录器:
    """增强的日志记录器"""
    
    def __init__(self, 名称: str = __name__, 级别: int = logging.DEBUG):
        self._记录器 = logging.getLogger(名称)
        self._记录器.setLevel(级别)
        self._记录器.propagate = False
    
    def 添加处理器(self, 处理器: logging.Handler):
        """添加处理器"""
        self._记录器.addHandler(处理器)
    
    def 添加过滤器(self, 过滤器: logging.Filter):
        """添加过滤器"""
        self._记录器.addFilter(过滤器)
    
    def 设置级别(self, 级别: int):
        """设置日志级别"""
        self._记录器.setLevel(级别)
    
    def 调试(self, 消息: str, **额外信息):
        """记录DEBUG级别日志"""
        self._记录器.debug(消息, extra=额外信息)
    
    def 信息(self, 消息: str, **额外信息):
        """记录INFO级别日志"""
        self._记录器.info(消息, extra=额外信息)
    
    def 警告(self, 消息: str, **额外信息):
        """记录WARNING级别日志"""
        self._记录器.warning(消息, extra=额外信息)
    
    def 错误(self, 消息: str, **额外信息):
        """记录ERROR级别日志"""
        self._记录器.error(消息, extra=额外信息)
    
    def 严重(self, 消息: str, **额外信息):
        """记录CRITICAL级别日志"""
        self._记录器.critical(消息, extra=额外信息)
    
    def 异常(self, 消息: str, **额外信息):
        """记录异常日志"""
        self._记录器.exception(消息, extra=额外信息)
    
    def 记录(self, 级别: int, 消息: str, **额外信息):
        """记录指定级别日志"""
        self._记录器.log(级别, 消息, extra=额外信息)
    
    def 获取记录器(self) -> logging.Logger:
        """获取原始记录器"""
        return self._记录器


class 日志管理器:
    """日志管理器"""
    
    def __init__(self):
        self._记录器映射: Dict[str, 日志记录器] = {}
        self._全局级别 = logging.DEBUG
    
    def 设置全局级别(self, 级别: int):
        """设置全局日志级别"""
        self._全局级别 = 级别
    
    def 获取记录器(self, 名称: str) -> 日志记录器:
        """获取或创建日志记录器"""
        if 名称 not in self._记录器映射:
            self._记录器映射[名称] = 日志记录器(名称, self._全局级别)
        return self._记录器映射[名称]
    
    def 配置控制台日志(self, 级别: int = logging.INFO,
                          格式化器: logging.Formatter = None):
        """配置控制台日志"""
        格式化器 = 格式化器 or 日志格式化器.创建标准格式()
        处理器 = 日志处理器.创建控制台处理器(级别, 格式化器)
        
        for 记录器 in self._记录器映射.values():
            记录器.添加处理器(处理器)
    
    def 配置文件日志(self, 文件名: str, 级别: int = logging.DEBUG,
                      格式化器: logging.Formatter = None,
                      滚动: bool = True, 最大大小: int = 1024 * 1024 * 10,
                      备份数量: int = 5):
        """配置文件日志"""
        格式化器 = 格式化器 or 日志格式化器.创建详细格式()
        
        if 滚动:
            处理器 = 日志处理器.创建滚动文件处理器(
                文件名, 级别, 格式化器, 最大大小, 备份数量
            )
        else:
            处理器 = 日志处理器.创建文件处理器(文件名, 级别, 格式化器)
        
        for 记录器 in self._记录器映射.values():
            记录器.添加处理器(处理器)
    
    def 配置时间滚动日志(self, 文件名: str, 级别: int = logging.DEBUG,
                          格式化器: logging.Formatter = None,
                          间隔: str = 'D', 备份数量: int = 7):
        """配置时间滚动日志"""
        格式化器 = 格式化器 or 日志格式化器.创建详细格式()
        处理器 = 日志处理器.创建时间滚动处理器(
            文件名, 级别, 格式化器, 间隔, 备份数量
        )
        
        for 记录器 in self._记录器映射.values():
            记录器.添加处理器(处理器)
    
    def 添加全局过滤器(self, 过滤器: logging.Filter):
        """添加全局过滤器"""
        for 记录器 in self._记录器映射.values():
            记录器.添加过滤器(过滤器)


# 便捷函数
def 获取日志记录器(名称: str = __name__) -> 日志记录器:
    """获取日志记录器"""
    return 日志记录器(名称)


def 创建日志记录器(名称: str = __name__, 级别: int = logging.DEBUG,
                    控制台输出: bool = True, 文件输出: bool = False,
                    文件名: str = 'app.log') -> 日志记录器:
    """创建配置好的日志记录器"""
    记录器 = 日志记录器(名称, 级别)
    
    if 控制台输出:
        格式化器 = 日志格式化器.创建标准格式()
        处理器 = 日志处理器.创建控制台处理器(级别, 格式化器)
        记录器.添加处理器(处理器)
    
    if 文件输出:
        格式化器 = 日志格式化器.创建详细格式()
        处理器 = 日志处理器.创建滚动文件处理器(文件名, 级别, 格式化器)
        记录器.添加处理器(处理器)
    
    return 记录器


def 快速配置(级别: int = logging.INFO, 控制台: bool = True, 
              文件: bool = False, 文件名: str = 'app.log'):
    """快速配置日志"""
    logging.basicConfig(
        level=级别,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        handlers=[]
    )
    
    处理器列表 = []
    
    if 控制台:
        处理器列表.append(logging.StreamHandler(sys.stdout))
    
    if 文件:
        处理器列表.append(logging.handlers.RotatingFileHandler(
            文件名, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        ))
    
    logging.getLogger().handlers = 处理器列表


class 日志上下文管理器:
    """日志上下文管理器"""
    
    def __init__(self, 记录器: 日志记录器, 消息: str, 级别: int = logging.INFO):
        self._记录器 = 记录器
        self._消息 = 消息
        self._级别 = 级别
    
    def __enter__(self):
        """进入上下文"""
        self._记录器.记录(self._级别, f'开始: {self._消息}')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if exc_type:
            self._记录器.错误(f'结束: {self._消息} - 异常: {exc_val}')
        else:
            self._记录器.记录(self._级别, f'完成: {self._消息}')


def 日志上下文(记录器: 日志记录器, 消息: str, 级别: int = logging.INFO) -> 日志上下文管理器:
    """创建日志上下文管理器"""
    return 日志上下文管理器(记录器, 消息, 级别)


class 结构化日志:
    """结构化日志工具"""
    
    @staticmethod
    def 创建结构化消息(事件: str, **数据) -> str:
        """创建结构化消息"""
        消息部分 = [f'事件={事件}']
        for 键, 值 in 数据.items():
            消息部分.append(f'{键}={值}')
        return ' '.join(消息部分)
    
    @staticmethod
    def 创建API日志(方法: str, 路径: str, 状态码: int, 耗时: float) -> str:
        """创建API日志"""
        return f'API {方法} {路径} {状态码} {耗时:.3f}秒'
    
    @staticmethod
    def 创建数据库日志(操作: str, 表名: str, 影响行数: int, 耗时: float) -> str:
        """创建数据库日志"""
        return f'DB {操作} {表名} 影响={影响行数} {耗时:.3f}秒'
    
    @staticmethod
    def 创建性能日志(操作: str, 耗时: float, 内存: float = None) -> str:
        """创建性能日志"""
        消息 = f'性能 {操作} 耗时={耗时:.3f}秒'
        if 内存:
            消息 += f' 内存={内存:.2f}MB'
        return 消息


# 全局日志管理器实例
_全局日志管理器 = 日志管理器()


def 获取全局日志管理器() -> 日志管理器:
    """获取全局日志管理器"""
    return _全局日志管理器


def 设置全局日志级别(级别: int):
    """设置全局日志级别"""
    _全局日志管理器.设置全局级别(级别)


def 配置全局日志(级别: int = logging.INFO, 控制台: bool = True,
                  文件: bool = False, 文件名: str = 'app.log'):
    """配置全局日志"""
    _全局日志管理器.设置全局级别(级别)
    
    if 控制台:
        _全局日志管理器.配置控制台日志(级别)
    
    if 文件:
        _全局日志管理器.配置文件日志(文件名, 级别)


# 合并自日志.py的独有函数

_LOG_LEVELS = {
    '调试': 10,
    '信息': 20,
    '警告': 30,
    '错误': 40,
    '致命': 50,
}

_LEVEL_NAMES = {v: k for k, v in _LOG_LEVELS.items()}

_current_level = 20
_format = '[{级别}] {时间} - {消息}'
_output_file: Optional[TextIO] = None
_enable_console = True
_log_formatters: Dict[str, Callable] = {}


def _输出(级别: str, 消息: str) -> None:
    级别值 = _LOG_LEVELS.get(级别, 0)
    if 级别值 < _current_level:
        return
    时间_str = _time.strftime('%Y-%m-%d %H:%M:%S', _time.localtime())
    行 = _format.format(级别=级别, 时间=时间_str, 消息=消息)
    if _enable_console:
        print(行, flush=True)
    if _output_file is not None:
        _output_file.write(行 + '\n')
        _output_file.flush()


def 调试(消息: str) -> None:
    """输出调试级别日志"""
    _输出('调试', 消息)


def 信息(消息: str) -> None:
    """输出信息级别日志"""
    _输出('信息', 消息)


def 警告(消息: str) -> None:
    """输出警告级别日志"""
    _输出('警告', 消息)


def 错误(消息: str) -> None:
    """输出错误级别日志"""
    _输出('错误', 消息)


def 致命(消息: str) -> None:
    """输出致命级别日志"""
    _输出('致命', 消息)


def 设置级别(级别: str) -> None:
    """
    设置日志级别

    参数:
        级别: '调试'、'信息'、'警告'、'错误'、'致命'
    """
    global _current_level
    if 级别 not in _LOG_LEVELS:
        raise RuntimeError(f"无效的日志级别: '{级别}'，可选：调试、信息、警告、错误、致命")
    _current_level = _LOG_LEVELS[级别]


def 获取级别() -> str:
    """获取当前日志级别"""
    return _LEVEL_NAMES.get(_current_level, '信息')


def 设置格式(格式字符串: str) -> None:
    """
    设置日志格式

    可用占位符:
        {级别} - 日志级别
        {时间} - 当前时间
        {消息} - 日志消息

    默认格式: '[{级别}] {时间} - {消息}'
    """
    global _format
    _format = 格式字符串


def 设置输出文件(文件路径: Optional[str] = None) -> None:
    """
    设置日志输出文件

    参数:
        文件路径: 输出文件路径，为空则关闭文件输出
    """
    global _output_file
    if _output_file is not None:
        _output_file.close()
        _output_file = None
    if 文件路径 is not None:
        _output_file = open(文件路径, 'a', encoding='utf-8')


def 启用控制台输出(启用: bool = True) -> None:
    """启用或禁用控制台输出"""
    global _enable_console
    _enable_console = 启用


def 禁用控制台输出() -> None:
    """禁用控制台输出"""
    启用控制台输出(False)


def 启用文件输出(文件路径: str) -> None:
    """启用文件输出"""
    设置输出文件(文件路径)


def 禁用文件输出() -> None:
    """禁用文件输出"""
    设置输出文件(None)


def 输出到标准错误() -> None:
    """将控制台输出重定向到标准错误"""
    global _output_file
    _output_file = sys.stderr


def 输出到标准输出() -> None:
    """将控制台输出重定向到标准输出"""
    global _output_file
    _output_file = sys.stdout


def 带上下文日志(级别: str, 消息: str, **上下文) -> None:
    """
    带上下文的日志输出

    参数:
        级别: 日志级别
        消息: 日志消息
        上下文: 额外的上下文信息
    """
    级别值 = _LOG_LEVELS.get(级别, 0)
    if 级别值 < _current_level:
        return
    时间_str = _time.strftime('%Y-%m-%d %H:%M:%S', _time.localtime())
    上下文_str = ' '.join(f'{k}={v}' for k, v in 上下文.items())
    if 上下文_str:
        消息 = f'{消息} [{上下文_str}]'
    行 = _format.format(级别=级别, 时间=时间_str, 消息=消息)
    if _enable_console:
        print(行, flush=True)
    if _output_file is not None:
        _output_file.write(行 + '\n')
        _output_file.flush()


def 调试上下文(消息: str, **上下文) -> None:
    """带上下文的调试日志"""
    带上下文日志('调试', 消息, **上下文)


def 信息上下文(消息: str, **上下文) -> None:
    """带上下文的信息日志"""
    带上下文日志('信息', 消息, **上下文)


def 警告上下文(消息: str, **上下文) -> None:
    """带上下文的警告日志"""
    带上下文日志('警告', 消息, **上下文)


def 错误上下文(消息: str, **上下文) -> None:
    """带上下文的错误日志"""
    带上下文日志('错误', 消息, **上下文)


def 致命上下文(消息: str, **上下文) -> None:
    """带上下文的致命日志"""
    带上下文日志('致命', 消息, **上下文)


def 日志异常(级别: str = '错误') -> None:
    """
    记录异常信息

    参数:
        级别: 日志级别，默认为'错误'
    """
    import traceback
    异常信息 = traceback.format_exc()
    带上下文日志(级别, f'异常发生:\n{异常信息}')


def 调试异常() -> None:
    """记录调试级别的异常信息"""
    日志异常('调试')


def 信息异常() -> None:
    """记录信息级别的异常信息"""
    日志异常('信息')


def 警告异常() -> None:
    """记录警告级别的异常信息"""
    日志异常('警告')


def 错误异常() -> None:
    """记录错误级别的异常信息"""
    日志异常('错误')


def 致命异常() -> None:
    """记录致命级别的异常信息"""
    日志异常('致命')


def 日志函数(级别: str) -> Callable:
    """
    获取指定级别的日志函数

    参数:
        级别: 日志级别

    返回:
        日志函数
    """
    函数映射 = {
        '调试': 调试,
        '信息': 信息,
        '警告': 警告,
        '错误': 错误,
        '致命': 致命,
    }
    return 函数映射.get(级别, 信息)


def 级别数值(级别: str) -> int:
    """获取级别的数值"""
    return _LOG_LEVELS.get(级别, 20)


def 级别名称(数值: int) -> str:
    """获取数值对应的级别名称"""
    return _LEVEL_NAMES.get(数值, '信息')


def 日志轮转(文件路径: str, 最大大小: int = 1024 * 1024, 备份数量: int = 5) -> None:
    """
    日志轮转

    参数:
        文件路径: 日志文件路径
        最大大小: 单个日志文件最大大小（字节），默认1MB
        备份数量: 保留的备份文件数量，默认5
    """
    if not os.path.exists(文件路径):
        return
    文件大小 = os.path.getsize(文件路径)
    if 文件大小 < 最大大小:
        return

    for i in range(备份数量 - 1, 0, -1):
        旧文件 = f'{文件路径}.{i}'
        新文件 = f'{文件路径}.{i + 1}'
        if os.path.exists(旧文件):
            if os.path.exists(新文件):
                os.remove(新文件)
            os.rename(旧文件, 新文件)

    if os.path.exists(f'{文件路径}.1'):
        os.remove(f'{文件路径}.1')
    os.rename(文件路径, f'{文件路径}.1')

    global _output_file
    if _output_file is not None:
        _output_file.close()
    _output_file = open(文件路径, 'w', encoding='utf-8')


def 设置日志轮转(文件路径: str, 最大大小: int = 1024 * 1024, 备份数量: int = 5) -> None:
    """
    设置日志轮转

    参数:
        文件路径: 日志文件路径
        最大大小: 单个日志文件最大大小（字节），默认1MB
        备份数量: 保留的备份文件数量，默认5
    """
    设置输出文件(文件路径)
    日志轮转(文件路径, 最大大小, 备份数量)


def 添加格式化器(名称: str, 格式化函数: Callable) -> None:
    """
    添加自定义格式化器

    参数:
        名称: 格式化器名称
        格式化函数: 格式化函数，接收(级别, 时间, 消息)参数
    """
    _log_formatters[名称] = 格式化函数


def 使用格式化器(名称: str) -> None:
    """
    使用指定的格式化器

    参数:
        名称: 格式化器名称
    """
    if 名称 not in _log_formatters:
        raise RuntimeError(f"格式化器 '{名称}' 不存在")
    格式化函数 = _log_formatters[名称]

    def _自定义输出(级别: str, 消息: str) -> None:
        级别值 = _LOG_LEVELS.get(级别, 0)
        if 级别值 < _current_level:
            return
        时间_str = _time.strftime('%Y-%m-%d %H:%M:%S', _time.localtime())
        行 = 格式化函数(级别, 时间_str, 消息)
        if _enable_console:
            print(行, flush=True)
        if _output_file is not None:
            _output_file.write(行 + '\n')
            _output_file.flush()

    global _输出
    _输出 = _自定义输出


def 创建简单格式化器(格式字符串: str) -> Callable:
    """
    创建简单格式化器

    参数:
        格式字符串: 格式字符串，支持{级别}、{时间}、{消息}占位符

    返回:
        格式化函数
    """
    def 格式化函数(级别: str, 时间: str, 消息: str) -> str:
        return 格式字符串.format(级别=级别, 时间=时间, 消息=消息)
    return 格式化函数


def 创建带颜色格式化器() -> Callable:
    """
    创建带颜色的格式化器

    返回:
        格式化函数
    """
    颜色映射 = {
        '调试': '\033[36m',
        '信息': '\033[32m',
        '警告': '\033[33m',
        '错误': '\033[31m',
        '致命': '\033[41m',
    }
    重置 = '\033[0m'

    def 格式化函数(级别: str, 时间: str, 消息: str) -> str:
        颜色 = 颜色映射.get(级别, '')
        return f'{颜色}[{级别}] {时间} - {消息}{重置}'
    return 格式化函数


def 创建JSON格式化器() -> Callable:
    """
    创建JSON格式化器

    返回:
        格式化函数
    """
    import json

    def 格式化函数(级别: str, 时间: str, 消息: str) -> str:
        return json.dumps({
            '级别': 级别,
            '时间': 时间,
            '消息': 消息,
        }, ensure_ascii=False)
    return 格式化函数


def 重置格式化器() -> None:
    """重置为默认格式化器"""
    global _输出
    _输出 = _输出


def 获取所有级别() -> list:
    """获取所有可用的日志级别"""
    return list(_LOG_LEVELS.keys())


def 获取格式化器列表() -> list:
    """获取所有已注册的格式化器"""
    return list(_log_formatters.keys())


def 打印日志配置() -> None:
    """打印当前日志配置"""
    配置 = {
        '当前级别': 获取级别(),
        '级别数值': _current_level,
        '输出格式': _format,
        '控制台输出': _enable_console,
        '文件输出': _output_file is not None,
        '格式化器': list(_log_formatters.keys()),
    }
    print(f'日志配置: {配置}')