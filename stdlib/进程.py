# -*- coding: utf-8 -*-
"""
光明标准库 - 进程管理模块

提供进程启动、停止、等待等管理功能。
"""

import subprocess
import os
import signal
import sys
from typing import Optional, List, Tuple


def 进程启动(命令: List[str], 等待: bool = True, 超时: int = None,
              捕获输出: bool = False, 工作目录: str = None,
              环境变量: dict = None) -> subprocess.Popen:
    """
    启动一个新进程

    参数:
        命令: 命令列表（如 ['python', 'script.py']）
        等待: 是否等待进程结束
        超时: 等待超时秒数（默认不超时）
        捕获输出: 是否捕获标准输出和错误
        工作目录: 进程工作目录
        环境变量: 进程环境变量字典

    返回:
        subprocess.Popen 对象
    """
    try:
        if 捕获输出:
            proc = subprocess.Popen(
                命令, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=工作目录, env=环境变量
            )
        else:
            proc = subprocess.Popen(
                命令, cwd=工作目录, env=环境变量
            )

        if 等待:
            proc.wait(timeout=超时)

        return proc
    except FileNotFoundError:
        raise RuntimeError(f"命令未找到: '{命令[0]}'")
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError(f"进程执行超时（{超时}秒）")
    except Exception as e:
        raise RuntimeError(f"进程启动失败: {e}")


def 进程运行(命令: List[str], 输入: str = None, 超时: int = None,
              工作目录: str = None, 环境变量: dict = None) -> dict:
    """
    运行命令并捕获输出

    参数:
        命令: 命令列表
        输入: 标准输入内容
        超时: 超时秒数
        工作目录: 工作目录
        环境变量: 环境变量字典

    返回:
        包含 '返回码', '标准输出', '标准错误' 的字典
    """
    try:
        result = subprocess.run(
            命令, input=输入, capture_output=True, text=True,
            timeout=超时, cwd=工作目录, env=环境变量
        )
        return {
            '返回码': result.returncode,
            '标准输出': result.stdout,
            '标准错误': result.stderr,
        }
    except FileNotFoundError:
        raise RuntimeError(f"命令未找到: '{命令[0]}'")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"进程执行超时（{超时}秒）")
    except Exception as e:
        raise RuntimeError(f"进程运行失败: {e}")


def 进程停止(进程: subprocess.Popen, 强制: bool = False):
    """
    停止进程

    参数:
        进程: 进程对象
        强制: 是否强制终止（SIGKILL 而非 SIGTERM）
    """
    if 进程.poll() is not None:
        return  # 进程已结束

    try:
        if 强制:
            进程.kill()
        else:
            进程.terminate()

        # 等待进程结束
        try:
            进程.wait(timeout=5)
        except subprocess.TimeoutExpired:
            进程.kill()
            进程.wait()
    except Exception as e:
        raise RuntimeError(f"进程停止失败: {e}")


def 进程等待(进程: subprocess.Popen, 超时: int = None) -> int:
    """
    等待进程结束

    参数:
        进程: 进程对象
        超时: 超时秒数

    返回:
        进程返回码
    """
    try:
        return 进程.wait(timeout=超时)
    except subprocess.TimeoutExpired:
        raise RuntimeError("进程等待超时")


def 进程是否运行(进程: subprocess.Popen) -> bool:
    """
    检查进程是否正在运行

    参数:
        进程: 进程对象

    返回:
        是否正在运行
    """
    return 进程.poll() is None


def 进程返回码(进程: subprocess.Popen) -> Optional[int]:
    """
    获取进程返回码

    参数:
        进程: 进程对象

    返回:
        返回码，未结束时返回 None
    """
    return 进程.poll()


def 进程PID(进程: subprocess.Popen) -> int:
    """
    获取进程 PID

    参数:
        进程: 进程对象

    返回:
        进程 PID
    """
    return 进程.pid


def 当前进程PID() -> int:
    """获取当前进程 PID"""
    return os.getpid()


def 父进程PID() -> int:
    """获取父进程 PID"""
    return os.getppid()


def 进程列表() -> List[int]:
    """
    获取当前进程的 PID 列表

    返回:
        PID 列表
    """
    if sys.platform == 'win32':
        # Windows 上使用 tasklist
        try:
            result = subprocess.run(['tasklist', '/FO', 'CSV'],
                                     capture_output=True, text=True)
            pids = []
            for line in result.stdout.strip().split('\n')[1:]:
                if line.strip():
                    parts = line.strip().split(',')
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1].strip('"'))
                            pids.append(pid)
                        except ValueError:
                            pass
            return pids
        except Exception:
            return [os.getpid()]
    else:
        # Unix 上使用 ps
        try:
            result = subprocess.run(['ps', '-eo', 'pid'],
                                     capture_output=True, text=True)
            pids = []
            for line in result.stdout.strip().split('\n')[1:]:
                if line.strip():
                    try:
                        pids.append(int(line.strip()))
                    except ValueError:
                        pass
            return pids
        except Exception:
            return [os.getpid()]


def 进程发送信号(进程: subprocess.Popen, 信号值: int):
    """
    向进程发送信号

    参数:
        进程: 进程对象
        信号值: 信号值（如 signal.SIGTERM）
    """
    try:
        if sys.platform == 'win32' and 信号值 == signal.SIGTERM:
            进程.terminate()
        else:
            os.kill(进程.pid, 信号值)
    except Exception as e:
        raise RuntimeError(f"发送信号失败: {e}")


# ===== 测试期望的附加 API =====

def 当前进程标识() -> int:
    """获取当前进程标识符"""
    return os.getpid()


def 父进程标识() -> int:
    """获取父进程标识符"""
    return os.getppid()


def CPU核心数() -> int:
    """获取 CPU 核心数"""
    return os.cpu_count() or 1


def 执行系统命令(命令字符串: str, 超时: int = None) -> dict:
    """
    执行系统命令

    参数:
        命令字符串: 要执行的命令
        超时: 超时秒数

    返回:
        包含 '返回码', '超时', '标准输出' 的字典
    """
    try:
        result = subprocess.run(
            命令字符串, shell=True, capture_output=True, text=True, timeout=超时
        )
        return {
            '返回码': result.returncode,
            '超时': False,
            '标准输出': result.stdout,
            '标准错误': result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            '返回码': -1,
            '超时': True,
            '标准输出': '',
            '标准错误': '超时',
        }


def _进程包装(队列, 函数, 参数):
    """进程内部包装函数（模块级别，可被 pickle）"""
    try:
        结果 = 函数(*参数)
        队列.put(('成功', 结果))
    except Exception as e:
        队列.put(('失败', e))


class 进程:
    """进程类"""

    def __init__(self, 函数, *参数):
        """
        创建进程

        参数:
            函数: 进程执行的目标函数
        """
        import multiprocessing
        self._函数 = 函数
        self._参数 = 参数
        self._进程 = None
        self._队列 = multiprocessing.Queue()

    def 开始(self):
        """启动进程"""
        import multiprocessing
        self._进程 = multiprocessing.Process(
            target=_进程包装, args=(self._队列, self._函数, self._参数)
        )
        self._进程.start()

    def 获取结果(self, 超时: float = None):
        """
        获取进程执行结果

        参数:
            超时: 等待超时秒数

        返回:
            进程执行结果
        """
        if self._进程:
            self._进程.join(timeout=超时)
        if self._进程 and self._进程.is_alive():
            raise RuntimeError("进程执行超时")
        状态, 值 = self._队列.get()
        if 状态 == '失败':
            raise 值
        return 值


class 进程队列:
    """进程安全队列"""

    def __init__(self, 最大大小: int = 0):
        import multiprocessing
        self._队列 = multiprocessing.Queue(maxsize=最大大小)

    def 空(self) -> bool:
        """检查队列是否为空"""
        return self._队列.empty()

    def 入队(self, 项目):
        """入队"""
        self._队列.put(项目)

    def 出队(self):
        """出队"""
        return self._队列.get()


class 共享值:
    """共享值"""

    def __init__(self, 类型码: str, 初始值):
        import multiprocessing
        self._值 = multiprocessing.Value(类型码, 初始值)

    def 获取(self):
        """获取共享值"""
        return self._值.value

    def 设置(self, 值):
        """设置共享值"""
        self._值.value = 值


class 共享数组:
    """共享数组"""

    def __init__(self, 类型码: str, 长度: int):
        import multiprocessing
        self._数组 = multiprocessing.Array(类型码, 长度)

    def 长度(self) -> int:
        """获取数组长度"""
        return len(self._数组)

    def 获取(self, 索引: int):
        """获取指定索引的值"""
        return self._数组[索引]

    def 设置(self, 索引: int, 值):
        """设置指定索引的值"""
        self._数组[索引] = 值


class 进程锁:
    """进程锁"""

    def __init__(self):
        import multiprocessing
        self._锁 = multiprocessing.Lock()

    def __enter__(self):
        self._锁.acquire()
        return self

    def __exit__(self, *args):
        self._锁.release()


class 管道:
    """进程管道"""

    def __init__(self):
        import multiprocessing
        self._父端, self._子端 = multiprocessing.Pipe(duplex=True)
        self._是本端父端 = None

    def 标记父端(self):
        """标记当前进程端为父端"""
        self._是本端父端 = True

    def 关闭本端(self):
        """关闭当前进程端的管道"""
        if self._是本端父端:
            self._父端.close()
        else:
            self._子端.close()

    def 关闭对端(self):
        """关闭对端管道"""
        if self._是本端父端:
            self._子端.close()
        else:
            self._父端.close()


__all__ = [
    '进程启动', '进程运行', '进程停止', '进程等待',
    '进程是否运行', '进程返回码', '进程PID',
    '当前进程PID', '父进程PID', '进程列表',
    '进程发送信号',
    # 附加 API
    '当前进程标识', '父进程标识', 'CPU核心数',
    '执行系统命令', '进程', '进程队列',
    '共享值', '共享数组', '进程锁', '管道',
]