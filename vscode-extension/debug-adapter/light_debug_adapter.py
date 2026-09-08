# -*- coding: utf-8 -*-
"""
光明调试适配器 (Debug Adapter Protocol) — VS Code 扩展版本

实现 VS Code 调试协议，允许在 VS Code 中调试光明程序。
"""

import sys
import os
import json
import socket
import argparse
import threading
import traceback
from typing import Dict, List, Any, Optional

# 路径设置：从 vscode-extension/debug-adapter/ 导航到项目根目录
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_dir = os.path.dirname(os.path.dirname(_script_dir))

sys.path.insert(0, os.path.join(_project_dir, 'src'))
sys.path.insert(0, os.path.join(_project_dir, 'tools'))
sys.path.insert(0, _project_dir)

from light_debug import LightDebugger, DebuggerContext, StackFrame


# =============================================================================
# DAP 传输层（Transport）
#
# DAP（Debug Adapter Protocol）消息为「头部 + 体」结构：
#   Content-Length: <字节数>\r\n\r\n<JSON 体>
# 原实现只支持 stdio（VS Code 进程内通信）。下面抽象出 Transport，
# 新增 TcpTransport 支持 DAP over TCP，使调试器可被远程机器上的
# IDE 通过 host/port 连接，实现「远程调试」。
# =============================================================================

class StdioTransport:
    """标准输入/输出传输（默认，VS Code 本地调试使用）。"""

    def read_message(self) -> Optional[Dict]:
        return _read_stdin_message()

    def write_message(self, message: Dict):
        _write_stdout_message(message)

    def close(self):
        pass


class TcpTransport:
    """TCP 传输：适配器作为服务端监听 host:port，远程 DAP 客户端连接。

    典型远程调试场景：在目标机器上运行
        python light_debug_adapter.py --host 0.0.0.0 --port 5678
    本地 VS Code / DAP 客户端连接该地址即可调试远端光明程序。
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((host, port))
        self._server.listen(1)
        self._conn: Optional[socket.socket] = None
        self._buf = b''

    def _ensure_connected(self):
        if self._conn is None:
            sys.stderr.write(f'[光明调试] 监听 DAP TCP {self.host}:{self.port} ...\n')
            sys.stderr.flush()
            conn, addr = self._server.accept()
            self._conn = conn
            sys.stderr.write(f'[光明调试] DAP 客户端已连接: {addr}\n')
            sys.stderr.flush()

    def read_message(self) -> Optional[Dict]:
        self._ensure_connected()
        headers = {}
        while True:
            line = self._read_line()
            if line is None:
                return None
            line = line.strip()
            if not line:
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        content_length = int(headers.get('content-length', '0'))
        if content_length <= 0:
            return None
        body = self._read_exact(content_length)
        if body is None:
            return None
        return json.loads(body.decode('utf-8'))

    def _read_line(self) -> Optional[str]:
        while b'\n' not in self._buf:
            chunk = self._conn.recv(4096)
            if not chunk:
                return None
            self._buf += chunk
        idx = self._buf.index(b'\n')
        line = self._buf[:idx]
        self._buf = self._buf[idx + 1:]
        if line.endswith(b'\r'):
            line = line[:-1]
        return line.decode('utf-8', errors='replace')

    def _read_exact(self, n: int) -> Optional[bytes]:
        while len(self._buf) < n:
            chunk = self._conn.recv(4096)
            if not chunk:
                return None
            self._buf += chunk
        data = self._buf[:n]
        self._buf = self._buf[n:]
        return data

    def write_message(self, message: Dict):
        content = json.dumps(message, ensure_ascii=False).encode('utf-8')
        self._conn.sendall(f'Content-Length: {len(content)}\r\n\r\n'.encode('utf-8'))
        self._conn.sendall(content)

    def close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
        try:
            self._server.close()
        except Exception:
            pass


_stdin_buf = b''


def _read_stdin_message() -> Optional[Dict]:
    """从 stdin（二进制缓冲）按 DAP 帧读取一条消息。

    注意：必须全程从 sys.stdin.buffer 读取，不能混用文本模式
    sys.stdin.readline()，否则 TextIOWrapper 的预读会导致
    buffer.read() 读到空、JSON 解析失败。
    """
    global _stdin_buf
    while b'\r\n\r\n' not in _stdin_buf:
        # read1 返回「当前可用」字节，不会为凑满 4096 而阻塞；
        # 普通 read(4096) 在管道上会一直等到 4096 字节或 EOF，导致卡死。
        chunk = sys.stdin.buffer.read1(4096)
        if not chunk:
            return None
        _stdin_buf += chunk
    sep = _stdin_buf.index(b'\r\n\r\n')
    header_block = _stdin_buf[:sep]
    _stdin_buf = _stdin_buf[sep + 4:]

    headers = {}
    for line in header_block.split(b'\r\n'):
        if b':' in line:
            key, value = line.split(b':', 1)
            headers[key.strip().lower()] = value.strip()
    content_length = int(headers.get(b'content-length', b'0'))
    if content_length <= 0:
        return None

    while len(_stdin_buf) < content_length:
        chunk = sys.stdin.buffer.read1(4096)
        if not chunk:
            return None
        _stdin_buf += chunk
    body = _stdin_buf[:content_length]
    _stdin_buf = _stdin_buf[content_length:]
    return json.loads(body.decode('utf-8'))


# DAP 输出目标。必须在程序运行前捕获真实 stdout，因为 _run_program
# 会把 sys.stdout 替换为 LightOutputCapture 来捕获程序输出；若 DAP
# 消息仍写 sys.stdout，会被误当成程序输出造成递归/损坏。
_DAP_OUT = None


def _set_dap_out(stream):
    global _DAP_OUT
    _DAP_OUT = stream


def _write_stdout_message(message: Dict):
    content = json.dumps(message, ensure_ascii=False).encode('utf-8')
    # 整帧以字节写出，绕过 TextIOWrapper 的换行翻译（Windows 下 \n→\r\n
    # 会把 \r\n\r\n 变成 \r\r\n\r\r\n，破坏 DAP 帧边界）。
    frame = b'Content-Length: ' + str(len(content)).encode('utf-8') + b'\r\n\r\n' + content
    out = _DAP_OUT if _DAP_OUT is not None else sys.stdout
    buf = getattr(out, 'buffer', out)
    buf.write(frame)
    buf.flush()


def create_transport() -> 'StdioTransport | TcpTransport':
    """根据命令行参数 / 环境变量构建传输层。

    配置优先级：显式 --mode/--port/--host > 环境变量 LIGHT_DEBUG_* > 默认值。
    - 未指定端口（默认 0）且 mode=auto → stdio
    - 指定 --port N（N>0）或 --mode tcp → TCP 服务端（监听 host:port）
    """
    parser = argparse.ArgumentParser(description='光明调试适配器 (DAP)')
    parser.add_argument('--host', default=os.environ.get('LIGHT_DEBUG_HOST', '127.0.0.1'),
                        help='TCP 监听地址（默认 127.0.0.1；远程调试用 0.0.0.0）')
    parser.add_argument('--port', type=int, default=int(os.environ.get('LIGHT_DEBUG_PORT', '0')),
                        help='TCP 监听端口（>0 时启用 TCP 模式；默认 0=stdio）')
    parser.add_argument('--mode', default='auto', choices=['stdio', 'tcp', 'auto'],
                        help='传输模式：stdio / tcp / auto（默认 auto，按端口自动判定）')
    args, _ = parser.parse_known_args()

    if args.mode == 'stdio':
        return StdioTransport()
    if args.mode == 'tcp' or (args.mode == 'auto' and args.port > 0):
        return TcpTransport(args.host, args.port)
    return StdioTransport()


class DebugAdapter:
    """调试适配器"""

    def __init__(self, transport=None):
        self.transport = transport if transport is not None else StdioTransport()
        self.seq = 0
        self.running = False
        self.breakpoints: Dict[str, List[int]] = {}
        self.variables: Dict[str, Any] = {}
        self.current_line = 0
        self.call_stack: List[Dict] = []
        self.debugger = LightDebugger()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._program_thread: Optional[threading.Thread] = None
        self._current_frame = None
        self._source_code = ''
        self._program_path = ''

    def send_response(self, request_seq: int, success: bool, body: Dict = None, command: str = '', message: str = ''):
        response = {
            'type': 'response',
            'request_seq': request_seq,
            'success': success,
            'command': command
        }
        if body:
            response['body'] = body
        if not success:
            response['message'] = message
        self._send_message(response)

    def send_event(self, event: str, body: Dict = None):
        event_msg = {
            'type': 'event',
            'event': event
        }
        if body:
            event_msg['body'] = body
        self._send_message(event_msg)

    def _send_message(self, message: Dict):
        # 委托给传输层：stdio → sys.stdout；tcp → socket
        self.transport.write_message(message)

    def handle_message(self, message: Dict):
        if message.get('type') == 'request':
            self._handle_request(message)

    def _handle_request(self, request: Dict):
        command = request.get('command', '')
        request_seq = request.get('seq', 0)

        handlers = {
            'initialize': self._handle_initialize,
            'launch': self._handle_launch,
            'setBreakpoints': self._handle_set_breakpoints,
            'configurationDone': self._handle_configuration_done,
            'threads': self._handle_threads,
            'stackTrace': self._handle_stack_trace,
            'scopes': self._handle_scopes,
            'variables': self._handle_variables,
            'pause': self._handle_pause,
            'continue': self._handle_continue,
            'next': self._handle_next,
            'stepIn': self._handle_step_in,
            'stepOut': self._handle_step_out,
            'disconnect': self._handle_disconnect,
            'evaluate': self._handle_evaluate,
        }

        handler = handlers.get(command)
        if handler:
            try:
                result = handler(request.get('arguments', {}))
                self.send_response(request_seq, True, result, command)
            except Exception as e:
                self.send_response(request_seq, False, command=command, message=str(e))
                self.send_event('output', {
                    'category': 'stderr',
                    'output': f'调试器错误: {e}\n{traceback.format_exc()}'
                })
        else:
            self.send_response(request_seq, False, command=command, message=f'未实现的命令: {command}')

    def _handle_initialize(self, args: Dict) -> Dict:
        self.send_event('initialized')
        return {
            'supportsConfigurationDoneRequest': True,
            'supportsStepBack': False,
            'supportsRestartFrame': False,
            'supportsCompletionsRequest': True,
            'supportsExceptionInfoRequest': True,
            'supportsFunctionBreakpoints': False,
            'supportsConditionalBreakpoints': True,
            'supportsEvaluateForHovers': True,
            'supportsLoadedSourcesRequest': False,
            'supportsProgressReporting': False,
            'supportsReadMemoryRequest': False,
            'supportsRestartRequest': True,
            'supportsSetVariable': True,
            'supportsStepInTargetsRequest': False,
            'supportsTerminateRequest': True,
            'supportsTerminateThreadsRequest': False,
            'supportsModulesRequest': False,
            'additionalModuleColumns': [],
            'supportedChecksumKinds': [],
            'supportsExceptionOptions': True,
            'supportsExceptionDetailsRequest': True,
            'exceptionBreakpointFilters': [
                {'filter': 'all', 'label': '所有异常', 'default': False},
                {'filter': 'uncaught', 'label': '未捕获的异常', 'default': True}
            ]
        }

    def _handle_launch(self, args: Dict) -> Dict:
        self.running = True
        program = args.get('program', '')
        if program:
            self._run_program(program)
        return {}

    def _handle_set_breakpoints(self, args: Dict) -> Dict:
        source = args.get('source', {})
        source_path = source.get('path', '')
        breakpoints = args.get('breakpoints', [])

        # 清空旧断点
        if source_path in self.breakpoints:
            for line in self.breakpoints[source_path]:
                self.debugger.clear_breakpoint(source_path, line)
        self.breakpoints[source_path] = []

        actual_breakpoints = []
        for bp in breakpoints:
            line = bp.get('line', 1)
            condition = bp.get('condition', None)
            self.breakpoints[source_path].append(line)
            self.debugger.set_breakpoint(source_path, line, condition)
            actual_breakpoints.append({
                'id': len(actual_breakpoints) + 1,
                'verified': True,
                'line': line,
                'source': source
            })

        return {'breakpoints': actual_breakpoints}

    def _handle_configuration_done(self, args: Dict) -> Dict:
        return {}

    def _handle_threads(self, args: Dict) -> Dict:
        return {
            'threads': [
                {'id': 1, 'name': '主线程'}
            ]
        }

    def _handle_stack_trace(self, args: Dict) -> Dict:
        stack_frames = []
        for i, frame in enumerate(self.call_stack[-20:]):
            stack_frames.append({
                'id': i + 1,
                'name': frame.get('name', 'Frame'),
                'source': {
                    'path': frame.get('file', ''),
                    'name': os.path.basename(frame.get('file', ''))
                },
                'line': frame.get('line', 1),
                'column': frame.get('col', 1)
            })

        return {
            'stackFrames': stack_frames,
            'totalFrames': len(stack_frames)
        }

    def _handle_scopes(self, args: Dict) -> Dict:
        return {
            'scopes': [
                {
                    'name': '局部变量',
                    'variablesReference': 1,
                    'expensive': False
                },
                {
                    'name': '全局变量',
                    'variablesReference': 2,
                    'expensive': False
                }
            ]
        }

    def _handle_variables(self, args: Dict) -> Dict:
        ref = args.get('variablesReference', 0)
        variables = []

        if ref == 1:
            for name, value in sorted(self.variables.items()):
                if name.startswith('_'):
                    continue
                var_ref = self._get_variable_ref(value)
                variables.append({
                    'name': name,
                    'value': self._format_value(value),
                    'type': type(value).__name__,
                    'variablesReference': var_ref
                })
        elif ref == 2:
            variables.append({
                'name': '__name__',
                'value': '__main__',
                'type': 'str',
                'variablesReference': 0
            })

        return {'variables': variables}

    def _handle_pause(self, args: Dict) -> Dict:
        self.debugger.set_step(LightDebugger.STEP_OVER)
        return {}

    def _handle_continue(self, args: Dict) -> Dict:
        self.debugger.set_step(LightDebugger.STEP_NONE)
        self.debugger.start()
        self._pause_event.set()
        return {'allThreadsContinued': True}

    def _handle_next(self, args: Dict) -> Dict:
        self.debugger.set_step(LightDebugger.STEP_OVER)
        self.debugger.start()
        self._pause_event.set()
        return {}

    def _handle_step_in(self, args: Dict) -> Dict:
        self.debugger.set_step(LightDebugger.STEP_INTO)
        self.debugger.start()
        self._pause_event.set()
        return {}

    def _handle_step_out(self, args: Dict) -> Dict:
        self.debugger.set_step(LightDebugger.STEP_OUT)
        self.debugger.start()
        self._pause_event.set()
        return {}

    def _handle_disconnect(self, args: Dict) -> Dict:
        self.running = False
        self.debugger.stop()
        self._pause_event.set()
        return {}

    def _handle_evaluate(self, args: Dict) -> Dict:
        expression = args.get('expression', '')
        frame_id = args.get('frameId', None)
        try:
            result = eval(expression, {'__builtins__': {}}, self.variables)
            return {
                'result': self._format_value(result),
                'variablesReference': self._get_variable_ref(result)
            }
        except Exception as e:
            return {
                'result': f'<错误: {e}>',
                'variablesReference': 0
            }

    def _get_variable_ref(self, value: Any) -> int:
        if isinstance(value, (list, tuple)) and len(value) > 0:
            return 100
        if isinstance(value, dict) and len(value) > 0:
            return 101
        return 0

    def _run_program(self, program_path: str):
        if not os.path.exists(program_path):
            self.send_event('output', {
                'category': 'stderr',
                'output': f'错误: 文件不存在: {program_path}\n'
            })
            self.send_event('terminated')
            return

        self._program_path = program_path
        try:
            with open(program_path, 'r', encoding='utf-8') as f:
                source = f.read()
            self._source_code = source

            # 编译光明代码
            from light_parser_v3 import LightParser
            from code_generator import PythonCodeGenerator

            parser = LightParser()
            module = parser.parse(source)
            generator = PythonCodeGenerator()
            python_code = generator.generate(module)
            python_code = self._inject_line_mapping(source, python_code)

            # 同步断点到调试器
            for file_path, lines in self.breakpoints.items():
                for line in lines:
                    self.debugger.set_breakpoint(file_path, line)

            # 设置回调：命中断点或单步停止时发送 stopped 事件
            def on_stop(file, line, frame):
                self._current_frame = frame
                self.current_line = line
                self.variables = dict(frame.f_locals) if frame else {}
                self.call_stack = [
                    {'name': f.f_code.co_name, 'file': f.f_code.co_filename, 'line': f.f_lineno}
                    for f in self._get_frames(frame)
                ]
                reason = 'breakpoint' if self.debugger.check_breakpoint(file, line) else 'step'
                self.send_event('stopped', {
                    'reason': reason,
                    'threadId': 1,
                    'allThreadsStopped': True
                })
                self._pause_event.clear()
                self._pause_event.wait()

            self.debugger.frame_callback = on_stop

            # 在线程中运行程序
            def run_thread():
                old_stdout = sys.stdout
                sys.stdout = LightOutputCapture(self)
                try:
                    self.debugger.start()
                    with DebuggerContext(self.debugger):
                        compiled = compile(python_code, program_path, 'exec')
                        exec_globals = {'__name__': '__main__', '__file__': program_path}
                        exec(compiled, exec_globals)
                except Exception as e:
                    light_error = self._format_light_error(e, source, python_code)
                    self.send_event('output', {
                        'category': 'stderr',
                        'output': light_error
                    })
                finally:
                    sys.stdout = old_stdout
                    self.send_event('terminated')

            self._program_thread = threading.Thread(target=run_thread, daemon=True)
            self._program_thread.start()

        except Exception as e:
            self.send_event('output', {
                'category': 'stderr',
                'output': f'编译错误: {e}\n{traceback.format_exc()}'
            })
            self.send_event('terminated')

    @staticmethod
    def _get_frames(frame):
        frames = []
        f = frame
        while f is not None:
            frames.append(f)
            f = f.f_back
        return frames

    def _inject_line_mapping(self, source: str, python_code: str) -> str:
        source_lines = source.split('\n')
        mapping_lines = []
        for i, line in enumerate(source_lines, 1):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                mapping_lines.append(f"# LIGHT_SRC:{i}:{stripped[:40]}")
        mapping_header = '\n'.join(mapping_lines)
        return f"# -*- coding: utf-8 -*-\n# 光明源码行号映射\n{mapping_header}\n\n{python_code}"

    def _format_light_error(self, e: Exception, source: str, python_code: str) -> str:
        lines = []
        lines.append(f"运行时错误: {e}")
        lines.append("")

        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_tb:
            for frame, lineno in traceback.walk_tb(exc_tb):
                filename = frame.f_code.co_filename
                func_name = frame.f_code.co_name
                if filename.endswith('.light'):
                    source_lines = source.split('\n')
                    if 1 <= lineno <= len(source_lines):
                        src_line = source_lines[lineno - 1].strip()
                        lines.append(f"  文件 \"{filename}\", 行 {lineno}, 在 {func_name} 中")
                        lines.append(f"    {src_line}")
                    else:
                        lines.append(f"  文件 \"{filename}\", 行 {lineno}, 在 {func_name} 中")
        lines.append("")
        return '\n'.join(lines)

    def _format_value(self, value: Any) -> str:
        if value is None:
            return '空'
        if isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        if isinstance(value, bool):
            return '真' if value else '假'
        if isinstance(value, list):
            if len(value) > 10:
                return f'列表[{len(value)}]({value[:3]}...)'
            return f'列表[{len(value)}]({value})'
        if isinstance(value, dict):
            if len(value) > 5:
                keys = list(value.keys())[:3]
                return f'字典[{len(value)}]({keys}...)'
            return f'字典({value})'
        return repr(value)


class LightOutputCapture:
    """捕获输出并发送到调试器"""

    def __init__(self, adapter: DebugAdapter):
        self.adapter = adapter
        self.buffer = ''

    def write(self, text: str):
        self.buffer += text
        if '\n' in self.buffer:
            lines = self.buffer.split('\n')
            self.buffer = lines[-1]
            for line in lines[:-1]:
                if line.strip():
                    self.adapter.send_event('output', {
                        'category': 'stdout',
                        'output': line + '\n'
                    })

    def flush(self):
        if self.buffer.strip():
            self.adapter.send_event('output', {
                'category': 'stdout',
                'output': self.buffer
            })
            self.buffer = ''


def run_debug_adapter():
    """运行调试适配器。传输方式由 --host/--port/--mode 或环境变量决定。"""
    # 捕获真实 stdout 作为 DAP 输出通道（必须在 _run_program 替换 sys.stdout 之前）。
    _set_dap_out(sys.stdout)

    transport = create_transport()
    mode = 'tcp' if isinstance(transport, TcpTransport) else 'stdio'
    sys.stderr.write(f'[光明调试] 启动 DAP 适配器（传输模式: {mode}）\n')
    sys.stderr.flush()

    adapter = DebugAdapter(transport=transport)

    while True:
        message = transport.read_message()
        if message is None:
            break
        adapter.handle_message(message)

    transport.close()


if __name__ == '__main__':
    run_debug_adapter()