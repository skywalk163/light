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


# ===== LH-20：管道式交互子进程（新能力，不改既有 API） =====
# 提供「拿到子进程句柄 → 写一行 → 读一行 → 再写」的长连接接口，
# 是 MCP stdio / LSP / JSON-RPC over pipe / 交互式 CLI 驱动（ssh/gdb/psql/fdisk）
# 的地基。此前 进程启动 是一次性的、进程运行 无 stdin、进程启动(捕获输出)
# 只有 PIPE stdout 无 stdin=PIPE，导致所有 stdin/stdout 长连接协议做不了。

# 读端 EOF 哨兵（读线程读到管道关闭时入队，读一行 据此返回 空）
_进程会话_EOF = object()


class 进程会话:
    """管道式交互子进程句柄（LH-20）。

    设计要点（对应 LH-20 期望）：
      1. stdin=PIPE、stdout=PIPE、bufsize=1（行缓冲，text 模式）；
         由调用方以「写一行 → 读一行 → 再写」的循环驱动。
      2. 读一行(超时=) 用「后台读线程 + 队列」实现可靠超时——读端绝不永久阻塞
         （这是本缺陷最容易写出的翻版：裸 readline() 无超时直接挂死）。
      3. 输出原样保留：不做行内重排、不吞空行；读一行只剥行终结符（\\n / \\r\\n），
         其余内容原样返回。空行返回空字符串（不吞）。
      4. stderr 默认并入 DEVNULL——绝不接 PIPE 又不读（会把子进程写死）。
         调用方如确需收集 stderr，请自行把子进程 stderr 重定向到文件/临时文件，
         而非 PIPE。
      5. 跨平台：FreeBSD/Linux 必过。Windows 上 bufsize=1 文本行缓冲与 POSIX
         存在差异，但本类读端用 `for line in stdout`（TextIOWrapper 自实现行切分）
         而非依赖系统行缓冲、写端每次 flush——正确性不依赖平台缓冲语义，无需
         额外降级。若未来确需二进制原样透传，可改用自实现行切分。
    """

    def __init__(self, 命令, 工作目录=None, 环境变量=None):
        import threading
        import queue
        self._进程 = subprocess.Popen(
            命令,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,   # 点4：stderr 不接 PIPE，防写死
            bufsize=1,                   # 点1：行缓冲
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=工作目录,
            env=环境变量,
        )
        self._读队列 = queue.Queue()
        self._已EOF = False
        self._读线程 = threading.Thread(target=self._读循环, daemon=True)
        self._读线程.start()

    def _读循环(self):
        """后台持续读 stdout 的每一行入队；读到管道关闭（EOF）时放哨兵。"""
        try:
            for 行 in self._进程.stdout:
                if 行.endswith('\r\n'):
                    行 = 行[:-2]
                elif 行.endswith('\n'):
                    行 = 行[:-1]
                self._读队列.put(行)
        except Exception:
            pass
        finally:
            self._读队列.put(_进程会话_EOF)

    def 写一行(self, 内容):
        """向子进程 stdin 写一行（自动补 '\\n' 并 flush）。"""
        try:
            self._进程.stdin.write(str(内容) + '\n')
            self._进程.stdin.flush()
        except (BrokenPipeError, ValueError, OSError) as e:
            raise RuntimeError(f"向进程会话写入失败（进程可能已退出）: {e}")

    def 读一行(self, 超时=None):
        """从子进程 stdout 读一行；超时（秒）返回 空（None），不抛。

        超时返回 None 而非抛异常（LH-20 点2）。超时=None 时阻塞直至读到一行、
        管道关闭（EOF）或进程结束。
        """
        import queue
        if self._已EOF:
            return None
        try:
            item = self._读队列.get(timeout=超时)
        except queue.Empty:
            return None
        if item is _进程会话_EOF:
            self._已EOF = True
            return None
        return item

    def 是否存活(self):
        """子进程是否仍在运行。"""
        return self._进程.poll() is None

    def 进程PID(self):
        """子进程 PID。"""
        return self._进程.pid

    def 返回码(self):
        """子进程返回码；未结束时为 None。"""
        return self._进程.poll()

    def 终止(self):
        """终止子进程并等待回收（无僵尸）。

        POSIX 发送 SIGTERM；超时未退则 SIGKILL。wait() 确保进程被收割。
        """
        if self._进程.poll() is None:
            self._进程.terminate()
        try:
            self._进程.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._进程.kill()
            self._进程.wait()
        # 关闭管道，避免句柄泄漏
        for 流 in (self._进程.stdin, self._进程.stdout):
            try:
                流.close()
            except Exception:
                pass
        if self._读线程.is_alive():
            self._读线程.join(timeout=2)


def 进程会话启动(命令, 工作目录=None, 环境变量=None):
    """启动管道式交互子进程（LH-20）。

    参数:
        命令: 命令列表（如 ['python3', 'mcp_server.py']）
        工作目录: 子进程工作目录
        环境变量: 子进程环境变量字典

    返回:
        进程会话 句柄（写一行 / 读一行(超时=) / 是否存活 / 终止）
    """
    return 进程会话(命令, 工作目录=工作目录, 环境变量=环境变量)


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
    # LH-20 管道式交互子进程
    '进程会话', '进程会话启动',
]