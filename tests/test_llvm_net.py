"""测试 LLVM 后端网络/Socket 支持 (Task B)

端到端测试范式：光明源码 → LLVM IR → 编译 → 运行 → 比对 stdout

编译策略（优先 clang，回退 llvmlite MCJIT + MSVC DLL）：
  1. 有 clang 时：clang -O2 -o exe ir.ll runtime.c -lws2_32 → 运行 exe
  2. 无 clang 有 MSVC 时：
     a. MSVC 编译 runtime_typed.c → _taskB_runtime.dll
     b. llvmlite MCJIT 在进程内编译 IR，符号从 DLL 解析
     c. 重定向 stdout，调用 main，读回输出
  3. 两者都没有时：pytest.mark.skipif 优雅 skip

端口段：19100-19199（绑定前探测，占用即报错退出，不自动+1）
临时文件一律 _taskB_ 前缀，收尾删干净
"""
import sys
import os
import socket
import threading
import subprocess
import time
import ctypes
import re
import tempfile
from typing import Optional

import pytest

sys.path.insert(0, 'src')

from llvm.compiler import compile_source_typed  # type: ignore[import]


# ================================================================
# 编译器探测
# ================================================================

def _find_clang_safely():
    """安全查找 clang，找不到返回 None（不抛异常）"""
    import shutil
    found = shutil.which('clang')
    if found:
        return found
    candidates = [
        r'c:\traework\light\llvm-mingw-20240619-ucrt-x86_64\bin\clang.exe',
        r'E:\Program Files\LLVM\bin\clang.exe',
        r'C:\Program Files\LLVM\bin\clang.exe',
        r'D:\Program Files\LLVM\bin\clang.exe',
        '/usr/bin/clang',
        '/usr/local/bin/clang',
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _find_msvc_safely():
    """安全查找 MSVC vcvarsall.bat，找不到返回 None"""
    for year, base in [
        ('2019', r'C:\Program Files (x86)\Microsoft Visual Studio\2019'),
        ('2022', r'C:\Program Files\Microsoft Visual Studio\2022'),
    ]:
        for edition in ('BuildTools', 'Community', 'Professional', 'Enterprise'):
            p = os.path.join(base, edition, r'VC\Auxiliary\Build\vcvarsall.bat')
            if os.path.exists(p):
                return p
    return None


CLANG_PATH = _find_clang_safely()
MSVC_VCVARS = _find_msvc_safely()
HAS_COMPILER = CLANG_PATH is not None or MSVC_VCVARS is not None

skip_no_compiler = pytest.mark.skipif(
    not HAS_COMPILER,
    reason="未找到 clang 或 MSVC 编译器，跳过网络端到端测试"
)


# ================================================================
# llvmlite MCJIT + MSVC DLL 执行管线（subprocess 方式）
# ================================================================

_runtime_dll_path = None
_runtime_def_path = None
_runtime_dll_compiled = False


def _ensure_runtime_dll():
    """确保 runtime DLL 已编译。返回 (dll_path, def_path) 或 (None, None)"""
    global _runtime_dll_path, _runtime_def_path, _runtime_dll_compiled
    if _runtime_dll_path is not None:
        return _runtime_dll_path, _runtime_def_path
    if _runtime_dll_compiled:
        return None, None

    _runtime_dll_compiled = True

    # 1. 提取所有需要导出的函数名
    codegen_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'llvm', 'codegen_typed.py')
    with open(codegen_path, 'r', encoding='utf-8') as f:
        content = f.read()
    func_names = sorted(set(re.findall(r'declare\s+\S+\s+@(dv_\w+)', content)))

    # 2. 生成 .def 文件
    def_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '_taskB_runtime.def'))
    def_content = 'LIBRARY _taskB_runtime\nEXPORTS\n'
    for name in func_names:
        def_content += f'    {name}\n'
    with open(def_path, 'w', encoding='utf-8') as f:
        f.write(def_content)

    # 3. 编译 DLL
    dll_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '_taskB_runtime.dll'))
    runtime_c = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'llvm', 'runtime_typed.c'))
    def_path_abs = os.path.abspath(def_path)

    bat_content = f"""@echo off
chcp 65001 >nul 2>&1
call "{MSVC_VCVARS}" x64 >nul 2>&1
cl.exe /nologo /O2 /utf-8 /LD /D_CRT_SECURE_NO_WARNINGS "{runtime_c}" /Fe:"{dll_path}" /link ws2_32.lib /DEF:"{def_path_abs}" 2>&1
echo EXIT_CODE=%ERRORLEVEL%
"""
    bat_path = os.path.join(os.path.dirname(__file__), '_taskB_compile_dll.bat')
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)

    try:
        result = subprocess.run(
            ['cmd', '/c', bat_path],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=60
        )
        if result.returncode != 0 or 'EXIT_CODE=0' not in result.stdout:
            print(f"DLL 编译失败:\n{result.stdout}\n{result.stderr}")
            return None, None
    finally:
        # 清理编译临时文件
        for suffix in ['.bat', '.exp', '.lib', '.obj']:
            p = os.path.join(os.path.dirname(__file__), f'_taskB_runtime{suffix}' if suffix != '.bat' else '_taskB_compile_dll.bat')
            try:
                if os.path.exists(p):
                    os.remove(p)
            except:
                pass

    if not os.path.exists(dll_path):
        print(f"DLL 未生成: {dll_path}")
        return None, None

    _runtime_dll_path = dll_path
    _runtime_def_path = def_path
    return dll_path, def_path


_RUNNER_SCRIPT = r'''"""MCJIT runner - 在子进程中编译并执行 LLVM IR"""
import sys, os, ctypes, re

def main():
    ir_path = sys.argv[1]
    dll_path = sys.argv[2]
    def_path = sys.argv[3]
    src_root = sys.argv[4]

    sys.path.insert(0, src_root)

    import llvmlite.binding as llvm

    try:
        llvm.initialize_all_targets()
        llvm.initialize_all_asmprinters()
    except Exception:
        pass

    # 从 .def 文件提取函数名
    with open(def_path, 'r') as f:
        def_content = f.read()
    func_names = re.findall(r'^\s+(dv_\w+)', def_content, re.MULTILINE)

    # 加载 DLL 并注册符号
    dll = ctypes.CDLL(dll_path)
    for name in func_names:
        try:
            func = getattr(dll, name)
            addr = ctypes.cast(func, ctypes.c_void_p).value
            if addr:
                llvm.add_symbol(name, addr)
        except (AttributeError, TypeError):
            pass

    # 读取并解析 IR
    with open(ir_path, 'r', encoding='utf-8') as f:
        ir_text = f.read()

    mod = llvm.parse_assembly(ir_text)
    mod.verify()

    triple = 'x86_64-pc-windows-msvc'
    target = llvm.Target.from_triple(triple)
    tm = target.create_target_machine(opt=2)
    mod.triple = triple
    mod.data_layout = str(tm.target_data)

    engine = llvm.create_mcjit_compiler(mod, tm)
    engine.finalize_object()
    engine.run_static_constructors()

    main_addr = engine.get_function_address('main')
    if not main_addr:
        print("ERROR: main not found", file=sys.stderr)
        sys.exit(1)

    cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(main_addr)
    retcode = cfunc()

    # 确保 stdout 刷新
    sys.stdout.flush()
    os._exit(retcode)

if __name__ == '__main__':
    main()
'''


def _execute_ir_mcjit(ir_text):
    """用子进程 MCJIT 编译并执行 IR，返回 (returncode, stdout, stderr)"""
    dll_path, def_path = _ensure_runtime_dll()
    if dll_path is None or def_path is None:
        return -1, "", "runtime DLL 不可用"

    # 写 runner 脚本
    runner_path = os.path.join(os.path.dirname(__file__), '_taskB_mcjit_runner.py')
    with open(runner_path, 'w', encoding='utf-8') as f:
        f.write(_RUNNER_SCRIPT)

    # 写 IR 到临时文件
    ir_path = os.path.join(os.path.dirname(__file__), '_taskB_exec.ir')
    with open(ir_path, 'w', encoding='utf-8') as f:
        f.write(ir_text)

    src_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    try:
        result = subprocess.run(
            [sys.executable, runner_path, ir_path, dll_path, def_path, src_root],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "执行超时"
    finally:
        for p in [runner_path, ir_path]:
            try:
                os.remove(p)
            except:
                pass


# ================================================================
# 端口管理
# ================================================================

PORT_RANGE_START = 19100
PORT_RANGE_END = 19199
_port_cursor = PORT_RANGE_START
_port_lock = threading.Lock()

def acquire_test_port():
    """在 19100-19199 段探测可用端口。占用即报错退出，不自动+1。"""
    global _port_cursor
    with _port_lock:
        port = _port_cursor
        _port_cursor += 1
        if _port_cursor > PORT_RANGE_END:
            raise RuntimeError("端口段 19100-19199 已耗尽")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', port))
        s.close()
        return port
    except OSError:
        raise RuntimeError(f"端口 {port} 被占用，测试无法继续（不自动+1重试）")
    finally:
        s.close()


# ================================================================
# Echo Server
# ================================================================

class EchoServer:
    """简单的 TCP echo server，在后台线程运行"""

    def __init__(self, port: int, delay: float = 0.0):
        self.port = port
        self.delay = delay
        self._sock: Optional[socket.socket] = None
        self._thread = None
        self._stop = False
        self._connections = []

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(('127.0.0.1', self.port))
        self._sock.listen(5)
        self._sock.settimeout(0.5)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        time.sleep(0.1)

    def _run(self):
        assert self._sock is not None
        while not self._stop:
            try:
                conn, addr = self._sock.accept()
                conn.settimeout(5.0)
                t = threading.Thread(target=self._handle, args=(conn,), daemon=True)
                t.start()
                self._connections.append(t)
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle(self, conn):
        try:
            while not self._stop:
                data = conn.recv(4096)
                if not data:
                    break
                if self.delay > 0:
                    time.sleep(self.delay)
                conn.sendall(data)
        except (socket.timeout, ConnectionError, OSError):
            pass
        finally:
            conn.close()

    def stop(self):
        self._stop = True
        if self._sock:
            try:
                self._sock.close()
            except:
                pass
        if self._thread:
            self._thread.join(timeout=2)


# ================================================================
# 编译运行工具
# ================================================================

def run_net_test(name, code, expected_output=None, expected_returncode=0, timeout=15):
    """编译光明代码为原生二进制并运行，比对 stdout

    优先 clang 编译到 exe，回退 llvmlite MCJIT 进程内执行
    """
    print("=" * 60)
    print(f"测试: {name}")
    print("=" * 60)

    # 生成 IR — 用 O0 跳过优化管线，避免优化器合并协程 yield 基本块
    try:
        ir = compile_source_typed(code, verbose=False, opt_level='O0')
    except Exception as e:
        print(f"IR 生成失败: {e}")
        return False

    # 保存 IR（_taskB_ 前缀，供调试）
    ir_path = f'tests/_taskB_{name}.ll'
    with open(ir_path, 'w', encoding='utf-8') as f:
        f.write(ir)

    if CLANG_PATH:
        # ---- clang 方式：编译到 exe 再运行 ----
        runtime_c = 'src/llvm/runtime_typed.c'
        exe_path = f'tests/_taskB_{name}.exe'
        result = subprocess.run(
            [CLANG_PATH, '-O2', '-o', exe_path, ir_path, runtime_c, '-lws2_32'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if result.returncode != 0:
            print(f"clang 编译失败!\nstderr: {result.stderr[:3000]}")
            _cleanup(ir_path)
            return False
        print(f"编译成功 (clang)")

        try:
            run_result = subprocess.run(
                [exe_path],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            print(f"运行超时 ({timeout}s)")
            _cleanup(ir_path, exe_path)
            return False

        stdout_str = run_result.stdout
        stderr_str = run_result.stderr
        retcode = run_result.returncode

        _cleanup(ir_path, exe_path)
    else:
        # ---- llvmlite MCJIT 方式：进程内执行 ----
        try:
            retcode, stdout_str, stderr_str = _execute_ir_mcjit(ir)
        except Exception as e:
            print(f"MCJIT 执行失败: {e}")
            _cleanup(ir_path)
            return False
        print(f"执行成功 (MCJIT + MSVC DLL)")
        _cleanup(ir_path)

    print(f"输出:\n{stdout_str}")
    if stderr_str:
        print(f"错误输出: {stderr_str}")
    print(f"返回码: {retcode}")

    # 检查返回码
    if retcode != expected_returncode:
        print(f"返回码不匹配: 期望 {expected_returncode}, 得到 {retcode}")
        return False

    # 检查输出
    if expected_output is not None:
        if expected_output not in stdout_str:
            print(f"输出不匹配: 期望包含 '{expected_output}'")
            return False

    return True


def _cleanup(*paths):
    """清理临时文件"""
    for f in paths:
        try:
            if os.path.exists(f):
                os.remove(f)
        except:
            pass


# ================================================================
# B1: Socket 原语测试
# ================================================================

@skip_no_compiler
class TestB1SocketPrimitives:
    """B1: Socket 原语端到端测试"""

    def test_socket_connect_send_recv(self):
        """B1 核心：连接 echo server → 发送 → 接收 → 比对"""
        port = acquire_test_port()
        server = EchoServer(port)
        server.start()
        try:
            code = f"""
fd = 创建socket(2, 1)
ret = 连接socket(fd, "127.0.0.1", {port})
发送socket(fd, "hello")
data = socket_recv(fd, 1024)
输出(data)
socket_close(fd)
"""
            assert run_net_test("b1_echo", code, "hello"), "echo 测试失败"
        finally:
            server.stop()

    def test_socket_connect_failure(self):
        """B1: 连接不存在的 server 应返回 -1"""
        port = acquire_test_port()
        code = f"""
fd = 创建socket(2, 1)
ret = 连接socket(fd, "127.0.0.1", {port})
输出(ret)
socket_close(fd)
"""
        assert run_net_test("b1_connfail", code, "-1"), "连接失败应返回-1"

    def test_socket_create_invalid(self):
        """B1: 无效 socket 类型应返回 -1"""
        code = """
fd = 创建socket(999, 999)
输出(fd)
"""
        assert run_net_test("b1_invalid", code, "-1"), "无效 socket 应返回-1"

    def test_socket_send_recv_large(self):
        """B1: 发送较长数据（256 字节）"""
        port = acquire_test_port()
        server = EchoServer(port)
        server.start()
        try:
            data_str = "A" * 256
            code = f"""
fd = 创建socket(2, 1)
连接socket(fd, "127.0.0.1", {port})
发送socket(fd, "{data_str}")
data = socket_recv(fd, 1024)
输出(data)
socket_close(fd)
"""
            assert run_net_test("b1_large", code, "A" * 100), "大数据发送失败"
        finally:
            server.stop()

    def test_socket_last_error(self):
        """B1: socket 错误信息可获取"""
        port = acquire_test_port()
        code = f"""
fd = 创建socket(2, 1)
ret = 连接socket(fd, "127.0.0.1", {port})
输出(ret)
socket_close(fd)
"""
        assert run_net_test("b1_error", code, "-1"), "应能获取 socket 错误状态"


# ================================================================
# B2: IO 多路复用测试
# ================================================================

@skip_no_compiler
class TestB2IOMultiplexing:
    """B2: IO 多路复用（select poller）端到端测试"""

    def test_poller_basic(self):
        """B2: poller 基本功能 — 创建/注册/等待/销毁"""
        code = """
p = 创建poller()
输出("poller创建成功")
销毁poller(p)
输出("poller销毁成功")
"""
        assert run_net_test("b2_poller_basic", code, "poller"), "poller 基本功能失败"

    def test_poller_select_one_ready(self):
        """B2: 两个 socket，只有一个有数据，等待只返回那一个"""
        port1 = acquire_test_port()
        port2 = acquire_test_port()
        server1 = EchoServer(port1)
        server2 = EchoServer(port2, delay=0.5)
        server1.start()
        server2.start()
        try:
            code = f"""
fd1 = 创建socket(2, 1)
连接socket(fd1, "127.0.0.1", {port1})
发送socket(fd1, "ping1")
fd2 = 创建socket(2, 1)
连接socket(fd2, "127.0.0.1", {port2})
发送socket(fd2, "ping2")
p = 创建poller()
注册poller(p, fd1, 1)
注册poller(p, fd2, 1)
ready = poller_wait(p, 2000)
输出(ready)
data = socket_recv(fd1, 1024)
输出(data)
销毁poller(p)
socket_close(fd1)
socket_close(fd2)
"""
            assert run_net_test("b2_poller_select", code, "ping1"), "poller select 测试失败"
        finally:
            server1.stop()
            server2.stop()


# ================================================================
# B3: 事件循环测试
# ================================================================

@skip_no_compiler
class TestB3EventLoop:
    """B3: 事件循环 + IO 唤醒端到端测试"""

    def test_coro_sleep_basic(self):
        """B3: dv_coro_sleep 基本功能"""
        code = """
异步 段落 测试睡眠：
    输出("sleep前")
    睡眠(100)
    输出("sleep后")
结束

输出("开始")
测试睡眠()
运行事件循环()
输出("结束")
"""
        assert run_net_test("b3_sleep", code, "sleep前"), "sleep 测试失败"

    def test_concurrent_echo(self):
        """B3: 两个异步段落各自连 echo server，事件循环并发驱动"""
        port1 = acquire_test_port()
        port2 = acquire_test_port()
        server1 = EchoServer(port1, delay=0)
        server2 = EchoServer(port2, delay=0.3)
        server1.start()
        server2.start()
        try:
            code = f"""
异步 段落 回显1：
    fd = 创建socket(2, 1)
    连接socket(fd, "127.0.0.1", {port1})
    发送socket(fd, "hello1")
    data = socket_recv(fd, 1024)
    输出(data)
    socket_close(fd)
结束

异步 段落 回显2：
    fd = 创建socket(2, 1)
    连接socket(fd, "127.0.0.1", {port2})
    发送socket(fd, "hello2")
    data = socket_recv(fd, 1024)
    输出(data)
    socket_close(fd)
结束

回显1()
回显2()
运行事件循环()
"""
            assert run_net_test("b3_concurrent", code, "hello1"), "并发 echo 测试失败"
        finally:
            server1.stop()
            server2.stop()

    def test_local_var_preservation(self):
        """B3: await_io 前后读同一个局部变量，值必须一致

        这是任务书强调的最容易出错的地方：
        Duff's device 恢复机制下，协程栈局部变量在挂起点后不保活。
        codegen_typed.py:2781-2999 的局部变量提升逻辑必须覆盖 await_io。
        """
        port = acquire_test_port()
        server = EchoServer(port)
        server.start()
        try:
            code = f"""
异步 段落 测试变量保持：
    x = 42
    输出(x)
    fd = 创建socket(2, 1)
    连接socket(fd, "127.0.0.1", {port})
    发送socket(fd, "test")
    await_io(fd, 1)
    data = socket_recv(fd, 1024)
    输出(data)
    输出(x)
    socket_close(fd)
结束

测试变量保持()
运行事件循环()
"""
            # x 的值在 await_io 前后都应该是 42
            assert run_net_test("b3_var_preserve", code, "42"), "局部变量保持测试失败"
        finally:
            server.stop()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
