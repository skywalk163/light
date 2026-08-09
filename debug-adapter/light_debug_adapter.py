# -*- coding: utf-8 -*-
"""
光明调试适配器 (Debug Adapter Protocol)

实现 VS Code 调试协议，允许在 VS Code 中调试光明程序。
"""

import sys
import os
import json
import threading
import traceback
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

from compiler import LightCompiler
from code_generator_unified import UnifiedCodeGenerator
from errors import format_exception
from light_debug import LightDebugger, DebuggerContext, StackFrame


class DebugAdapter:
    """调试适配器基类"""

    def __init__(self):
        self.seq = 0
        self.running = False
        self.breakpoints: Dict[str, List[int]] = {}
        self.variables: Dict[str, Any] = {}
        self.current_line = 0
        self.call_stack: List[Dict] = []
        self.debugger = LightDebugger()
        self._pause_event = threading.Event()
        self._pause_event.set()  # 初始为可运行
        self._program_thread: Optional[threading.Thread] = None
        self._current_frame = None
        self._source_code = ''
        self._program_path = ''
        
    def send_response(self, request_seq: int, success: bool, body: Dict = None, command: str = '', message: str = ''):
        """发送响应"""
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
        """发送事件"""
        event_msg = {
            'type': 'event',
            'event': event
        }
        if body:
            event_msg['body'] = body
        self._send_message(event_msg)
    
    def _send_message(self, message: Dict):
        """发送消息到调试器客户端"""
        content = json.dumps(message, ensure_ascii=False)
        content_bytes = content.encode('utf-8')
        sys.stdout.write(f'Content-Length: {len(content_bytes)}\r\n\r\n')
        sys.stdout.buffer.write(content_bytes)
        sys.stdout.flush()
    
    def handle_message(self, message: Dict):
        """处理调试器消息"""
        if message.get('type') == 'request':
            self._handle_request(message)
    
    def _handle_request(self, request: Dict):
        """处理请求"""
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
                    'output': format_exception(type(e), e, e.__traceback__)
                })
        else:
            self.send_response(request_seq, False, command=command, message=f'未实现的命令: {command}')
    
    def _handle_initialize(self, args: Dict) -> Dict:
        """处理初始化请求"""
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
            'exceptionBreakpointFilters': [
                {
                    'filter': 'all',
                    'label': '所有异常',
                    'default': False
                },
                {
                    'filter': 'uncaught',
                    'label': '未捕获的异常',
                    'default': True
                }
            ],
            'supportsTerminateThreadsRequest': False,
            'supportsModulesRequest': False,
            'additionalModuleColumns': [],
            'supportedChecksumKinds': [],
            'supportsExceptionOptions': True,
            'supportsExceptionDetailsRequest': True
        }
    
    def _handle_launch(self, args: Dict) -> Dict:
        """处理启动请求"""
        self.running = True
        program = args.get('program', '')
        if program:
            self._run_program(program)
        return {}
    
    def _handle_set_breakpoints(self, args: Dict) -> Dict:
        """处理设置断点请求"""
        source = args.get('source', {})
        source_path = source.get('path', '')
        breakpoints = args.get('breakpoints', [])
        
        self.breakpoints[source_path] = [bp.get('line', 1) for bp in breakpoints]
        
        # 返回实际设置的断点
        actual_breakpoints = []
        for bp in breakpoints:
            line = bp.get('line', 1)
            actual_breakpoints.append({
                'id': len(actual_breakpoints) + 1,
                'verified': True,
                'line': line,
                'source': source
            })
        
        return {'breakpoints': actual_breakpoints}
    
    def _handle_configuration_done(self, args: Dict) -> Dict:
        """处理配置完成请求"""
        self.send_event('continued', {
            'allThreadsContinued': True
        })
        return {}
    
    def _handle_threads(self, args: Dict) -> Dict:
        """处理线程列表请求"""
        return {
            'threads': [
                {
                    'id': 1,
                    'name': '主线程'
                }
            ]
        }
    
    def _handle_stack_trace(self, args: Dict) -> Dict:
        """处理堆栈跟踪请求"""
        stack_frames = []
        for i, frame in enumerate(self.call_stack[-10:]):  # 最多显示10帧
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
        """处理作用域请求"""
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
        """处理变量请求"""
        ref = args.get('variablesReference', 0)
        variables = []
        
        if ref == 1:  # 局部变量
            for name, value in self.variables.items():
                variables.append({
                    'name': name,
                    'value': self._format_value(value),
                    'type': type(value).__name__,
                    'variablesReference': 0
                })
        elif ref == 2:  # 全局变量
            variables.append({
                'name': '全局作用域',
                'value': '<global>',
                'type': 'module',
                'variablesReference': 0
            })
        
        return {'variables': variables}
    
    def _handle_pause(self, args: Dict) -> Dict:
        """处理暂停请求"""
        self.debugger.set_step(LightDebugger.STEP_OVER)
        return {}

    def _handle_continue(self, args: Dict) -> Dict:
        """处理继续请求"""
        self.debugger.set_step(LightDebugger.STEP_NONE)
        self.debugger.start()
        self._pause_event.set()
        return {
            'allThreadsContinued': True
        }

    def _handle_next(self, args: Dict) -> Dict:
        """处理单步跳过请求"""
        self.debugger.set_step(LightDebugger.STEP_OVER)
        self.debugger.start()
        self._pause_event.set()
        return {}

    def _handle_step_in(self, args: Dict) -> Dict:
        """处理步入请求"""
        self.debugger.set_step(LightDebugger.STEP_INTO)
        self.debugger.start()
        self._pause_event.set()
        return {}

    def _handle_step_out(self, args: Dict) -> Dict:
        """处理步出请求"""
        self.debugger.set_step(LightDebugger.STEP_OUT)
        self.debugger.start()
        self._pause_event.set()
        return {}

    def _handle_disconnect(self, args: Dict) -> Dict:
        """处理断开连接请求"""
        self.running = False
        self.debugger.stop()
        self._pause_event.set()
        return {}
    
    def _run_program(self, program_path: str):
        """运行程序（在线程中，带调试跟踪）"""
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

            compiler = LightCompiler()
            result = compiler.compile(source)

            if result['errors']:
                for error in result['errors']:
                    self.send_event('output', {
                        'category': 'stderr',
                        'output': f'编译错误: {error}\n'
                    })
                self.send_event('terminated')
                return

            codegen = UnifiedCodeGenerator()
            python_code = codegen.generate(result['ast'])
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
                self.send_event('stopped', {
                    'reason': 'breakpoint' if self.debugger.check_breakpoint(file, line) else 'step',
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
                'output': format_exception(type(e), e, e.__traceback__)
            })
            self.send_event('terminated')

    @staticmethod
    def _get_frames(frame):
        """从当前帧向上遍历调用栈"""
        frames = []
        f = frame
        while f is not None:
            frames.append(f)
            f = f.f_back
        return frames

    def _inject_line_mapping(self, source: str, python_code: str) -> str:
        """在生成代码前注入源码行号映射表"""
        source_lines = source.split('\n')
        mapping_lines = []
        for i, line in enumerate(source_lines, 1):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                mapping_lines.append(f"# LIGHT_SRC:{i}:{stripped[:40]}")
        mapping_header = '\n'.join(mapping_lines)
        return f"# -*- coding: utf-8 -*-\n# 光明源码行号映射\n{mapping_header}\n\n{python_code}"

    def _format_light_error(self, e: Exception, source: str, python_code: str) -> str:
        """将 Python 异常转换为带光明源码行号的错误信息"""
        import traceback as tb
        lines = []
        lines.append(f"运行时错误: {e}")
        lines.append("")

        # 提取 traceback
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_tb:
            for frame, lineno in tb.walk_tb(exc_tb):
                filename = frame.f_code.co_filename
                func_name = frame.f_code.co_name
                if filename.endswith('.light'):
                    # 获取对应源码行
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
        """格式化变量值"""
        if value is None:
            return '空'
        if isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
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
        """写入输出"""
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
        """刷新缓冲区"""
        if self.buffer.strip():
            self.adapter.send_event('output', {
                'category': 'stdout',
                'output': self.buffer
            })
            self.buffer = ''


def run_debug_adapter():
    """运行调试适配器"""
    adapter = DebugAdapter()
    
    def read_message() -> Optional[Dict]:
        """读取消息"""
        headers = {}
        while True:
            line = sys.stdin.readline()
            if not line:
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
        
        content = sys.stdin.buffer.read(content_length).decode('utf-8')
        return json.loads(content)
    
    # 主循环
    while True:
        message = read_message()
        if message is None:
            break
        
        adapter.handle_message(message)


if __name__ == '__main__':
    run_debug_adapter()
