"""
进程管理 — lightpub 桥接模块

基于 Python subprocess/os 库封装，函数名对齐上游 duanpub（段言时期）packages/进程管理/源.duan。

上游 duanpub 原始包通过 C FFI 直接调用操作系统进程 API，
本桥接模块用 Python subprocess/os 模块替代，提供等价的进程管理功能。
"""

import subprocess as _subprocess
import os as _os
import time as _time
import signal as _signal


# =============================================================================
# 数据结构
# =============================================================================

class 进程对象:
    """进程对象包装"""
    def __init__(self, 进程=None, 命令='', 进程ID=0):
        self.进程 = 进程
        self.命令 = 命令
        self.进程ID = 进程ID
        self.标准输出 = ''
        self.标准错误 = ''
        self.退出码 = None


# =============================================================================
# 进程管理
# =============================================================================

def 启动进程(命令, 参数=None, 工作目录='', 环境变量=None):
    """启动一个新进程，返回进程对象"""
    if 参数 is None:
        参数 = []
    try:
        cmd = [命令] + 参数
        进程 = _subprocess.Popen(
            cmd, cwd=工作目录 or None, env=环境变量,
            stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
            stdin=_subprocess.PIPE, text=True
        )
        return 进程对象(进程, 命令, 进程.pid)
    except Exception as e:
        raise Exception("启动进程失败: " + str(e))


def 等待进程(进程):
    """等待进程结束，返回退出码"""
    if not 进程 or not 进程.进程:
        raise Exception("等待进程失败: 进程为空")
    try:
        进程.退出码 = 进程.进程.wait()
        进程.标准输出, 进程.标准错误 = 进程.进程.communicate()
        return 进程.退出码
    except Exception as e:
        raise Exception("等待进程失败: " + str(e))


def 终止进程(进程):
    """终止进程"""
    if not 进程 or not 进程.进程:
        raise Exception("终止进程失败: 进程为空")
    try:
        进程.进程.terminate()
        return True
    except Exception as e:
        raise Exception("终止进程失败: " + str(e))


def 进程是否运行中(进程):
    """检查进程是否仍在运行"""
    if not 进程 or not 进程.进程:
        return False
    try:
        进程.进程.poll()
        return 进程.进程.returncode is None
    except Exception:
        return False


def 获取进程退出码(进程):
    """获取进程的退出码"""
    if not 进程:
        raise Exception("获取进程退出码失败: 进程为空")
    if 进程.退出码 is not None:
        return 进程.退出码
    if 进程.进程:
        进程.进程.poll()
        return 进程.进程.returncode
    return -1


def 获取进程ID(进程):
    """获取进程的ID"""
    if not 进程:
        return 0
    return 进程.进程ID or (进程.进程.pid if 进程.进程 else 0)


def 获取标准输出(进程):
    """获取进程的标准输出"""
    if not 进程:
        return ''
    return 进程.标准输出 or ''


def 获取标准错误(进程):
    """获取进程的标准错误"""
    if not 进程:
        return ''
    return 进程.标准错误 or ''


def 写入标准输入(进程, 文本):
    """向进程的标准输入写入数据"""
    if not 进程 or not 进程.进程:
        raise Exception("写入标准输入失败: 进程为空")
    try:
        进程.进程.stdin.write(文本)
        进程.进程.stdin.flush()
        return True
    except Exception as e:
        raise Exception("写入标准输入失败: " + str(e))


def 关闭标准输入(进程):
    """关闭进程的标准输入"""
    if not 进程 or not 进程.进程:
        return
    try:
        进程.进程.stdin.close()
    except Exception:
        pass


def 执行命令(命令, 参数=None, 工作目录=''):
    """执行命令，返回(退出码, 标准输出, 标准错误)"""
    if 参数 is None:
        参数 = []
    try:
        cmd = [命令] + 参数
        结果 = _subprocess.run(
            cmd, cwd=工作目录 or None,
            capture_output=True, text=True
        )
        return (结果.returncode, 结果.stdout, 结果.stderr)
    except Exception as e:
        raise Exception("执行命令失败: " + str(e))


def 执行命令并获取输出(命令, 参数=None, 工作目录=''):
    """执行命令并获取标准输出，失败抛出异常"""
    if 参数 is None:
        参数 = []
    try:
        cmd = [命令] + 参数
        结果 = _subprocess.run(
            cmd, cwd=工作目录 or None,
            capture_output=True, text=True, check=True
        )
        return 结果.stdout
    except _subprocess.CalledProcessError as e:
        raise Exception("执行命令并获取输出失败: " + str(e))
    except Exception as e:
        raise Exception("执行命令并获取输出失败: " + str(e))


def 执行命令并检查(命令, 参数=None, 工作目录=''):
    """执行命令并检查返回码，成功返回True，失败抛出异常"""
    if 参数 is None:
        参数 = []
    try:
        cmd = [命令] + 参数
        _subprocess.run(cmd, cwd=工作目录 or None, check=True)
        return True
    except _subprocess.CalledProcessError as e:
        raise Exception("执行命令失败: 退出码 " + str(e.returncode))
    except Exception as e:
        raise Exception("执行命令失败: " + str(e))


def 获取当前进程ID():
    """获取当前进程的ID"""
    return _os.getpid()


def 列出子进程():
    """列出当前进程的子进程ID列表（简化实现，返回空列表）"""
    子进程列表 = []
    try:
        current_pid = _os.getpid()
        import psutil as _psutil
        current = _psutil.Process(current_pid)
        子进程列表 = [p.info['pid'] for p in current.children(recursive=True)]
    except ImportError:
        pass
    except Exception:
        pass
    return 子进程列表


def 系统休眠(秒数):
    """系统休眠指定秒数"""
    _time.sleep(秒数)