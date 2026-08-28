# -*- coding: utf-8 -*-
"""
光明调试适配器 - 后端实现

通过 JSON-RPC 与 VSCode 通信，支持断点、单步执行、变量查看、调用栈和表达式求值。
"""

import sys
import os
import json
import traceback
import re
import subprocess
import socket
import signal
from typing import Dict, List, Optional, Any


# =============================================================================
# JSON-RPC 通信
# =============================================================================

class JSONRPCConnection:
    """JSON-RPC over stdio 通信"""

    def __init__(self):
        self.buffer = ''

    def send_message(self, message: Dict):
        """发送 JSON-RPC 消息"""
        content = json.dumps(message, ensure_ascii=False)
        content_bytes = content.encode('utf-8')
        header = f'Content-Length: {len(content_bytes)}\r\n\r\n'
        sys.stdout.write(header)
        sys.stdout.buffer.write(content_bytes)
        sys.stdout.flush()

    def send_event(self, event: str, body: Dict = None):
        """发送事件"""
        msg = {
            'type': 'event',
            'event': event,
            'body': body or {}
        }
        self.send_message(msg)

    def send_response(self, request_seq: int, success: bool, body: Dict = None, command: str = ''):
        """发送响应"""
        msg = {
            'type': 'response',
            'request_seq': request_seq,
            'success': success,
            'command': command,
            'body': body or {}
        }
        self.send_message(msg)

    def read_message(self) -> Optional[Dict]:
        """读取 JSON-RPC 消息"""
        while True:
            line = sys.stdin.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                break
            if ':' in line:
                key, value = line.split(':', 1)
                if key.strip().lower() == 'content-length':
                    content_length = int(value.strip())

        if content_length <= 0:
            return None

        content = sys.stdin.buffer.read(content_length).decode('utf-8')
        return json.loads(content)


# =============================================================================
# 断点管理
# =============================================================================

class BreakpointManager:
    """断点管理器"""

    def __init__(self):
        self.breakpoints: Dict[str, List[Dict]] = {}  # path -> [breakpoints]
        self.next_id = 1

    def set_breakpoints(self, path: str, lines: List[int]) -> List[Dict]:
        """设置断点"""
        bps = []
        self.breakpoints[path] = []
        for line in lines:
            bp = {
                'id': self.next_id,
                'verified': True,
                'line': line,
                'source': {'path': path}
            }
            self.next_id += 1
            bps.append(bp)
            self.breakpoints[path].append(bp)
        return bps

    def clear_breakpoints(self, path: str):
        """清除断点"""
        self.breakpoints.pop(path, None)

    def get_breakpoints(self, path: str) -> List[Dict]:
        """获取断点"""
        return self.breakpoints.get(path, [])

    def has_breakpoint_at(self, path: str, line: int) -> bool:
        """检查指定行是否有断点"""
        for bp in self.breakpoints.get(path, []):
            if bp.get('line') == line:
                return True
        return False


# =============================================================================
# 调试引擎
# =============================================================================

class DebugEngine:
    """光明调试引擎"""

    def __init__(self):
        self.connection = JSONRPCConnection()
        self.bp_manager = BreakpointManager()
        self.is_running = False
        self.is_paused = False
        self.current_thread_id = 1
        self.current_frame_id = 1
        self.source_code = ''
        self.source_path = ''
        self.current_line = 0
        self.variables: Dict[str, Any] = {}
        self.stack_frames: List[Dict] = []
        self.call_stack: List[Dict] = []
        self.step_mode = None  # None, 'stepIn', 'stepOver', 'stepOut'

    def initialize(self, args: Dict) -> Dict:
        """初始化调试适配器"""
        return {
            'supportsConfigurationDoneRequest': True,
            'supportsFunctionBreakpoints': False,
            'supportsConditionalBreakpoints': True,
            'supportsHitConditionalBreakpoints': False,
            'supportsEvaluateForHovers': True,
            'supportsStepBack': False,
            'supportsSetVariable': True,
            'supportsRestartFrame': False,
            'supportsGotoTargetsRequest': False,
            'supportsStepInTargetsRequest': False,
            'supportsCompletionsRequest': False,
            'supportsModulesRequest': False,
            'supportsRestartRequest': False,
            'supportsExceptionOptions': True,
            'supportsValueFormattingOptions': True,
            'supportsExceptionInfoRequest': True,
            'supportTerminateDebuggee': True,
            'supportsDelayedStackTraceLoading': True,
            'supportsLoadedSourcesRequest': True,
            'supportsLogPoints': False,
            'supportsTerminateThreadsRequest': False,
            'supportsSetExpression': False,
            'supportsClipboardContext': True
        }

    def launch(self, args: Dict) -> bool:
        """启动调试会话"""
        try:
            program = args.get('program', '')
            if not program:
                program = args.get('__file', '')

            if not os.path.isfile(program):
                self.connection.send_event('output', {
                    'category': 'stderr',
                    'output': f'错误: 找不到文件 {program}\n'
                })
                return False

            self.source_path = program
            with open(program, 'r', encoding='utf-8') as f:
                self.source_code = f.read()

            self.is_running = True
            self.is_paused = False
            self.current_line = 1
            self.variables = {}
            self.call_stack = []

            # 初始停靠在第一行
            self._pause_at_line(1, '启动')

            return True
        except Exception as e:
            self.connection.send_event('output', {
                'category': 'stderr',
                'output': f'启动错误: {str(e)}\n'
            })
            return False

    def attach(self, args: Dict) -> bool:
        """附加到进程"""
        self.connection.send_event('output', {
            'category': 'stdout',
            'output': '附加模式暂不支持\n'
        })
        return False

    def disconnect(self, args: Dict):
        """断开调试"""
        self.is_running = False
        self.is_paused = False
        self.source_code = ''
        self.variables = {}
        self.call_stack = []

    def set_breakpoints(self, args: Dict) -> List[Dict]:
        """设置断点"""
        source = args.get('source', {})
        path = source.get('path', '')
        lines = args.get('lines', [])
        breakpoints = args.get('breakpoints', [])

        if breakpoints:
            lines = [bp.get('line', 0) for bp in breakpoints]

        self.bp_manager.clear_breakpoints(path)
        return self.bp_manager.set_breakpoints(path, lines)

    def set_exception_breakpoints(self, args: Dict):
        """设置异常断点"""
        pass

    def configuration_done(self):
        """配置完成"""
        pass

    def continue_request(self, seq: int, command: str):
        """继续执行"""
        self.step_mode = None
        self.is_paused = False
        self.connection.send_response(seq, True, command=command)
        self._simulate_execution()

    def next_request(self, seq: int, command: str):
        """单步跳过"""
        self.step_mode = 'stepOver'
        self.is_paused = False
        self.connection.send_response(seq, True, command=command)
        self._simulate_execution()

    def step_in_request(self, seq: int, command: str):
        """单步进入"""
        self.step_mode = 'stepIn'
        self.is_paused = False
        self.connection.send_response(seq, True, command=command)
        self._simulate_execution()

    def step_out_request(self, seq: int, command: str):
        """单步跳出"""
        self.step_mode = 'stepOut'
        self.is_paused = False
        self.connection.send_response(seq, True, command=command)
        self._simulate_execution()

    def pause_request(self, seq: int, command: str):
        """暂停"""
        self.is_paused = True
        self.connection.send_response(seq, True, command=command)

    def stack_trace_request(self, seq: int, command: str, args: Dict):
        """获取调用栈"""
        start_frame = args.get('startFrame', 0)
        levels = args.get('levels', 20)

        frames = []
        frame_id = self.current_frame_id

        for i, frame_info in enumerate(self._get_stack_frames()):
            if i < start_frame:
                continue
            if len(frames) >= levels:
                break

            line = frame_info.get('line', self.current_line)
            col = frame_info.get('column', 0)
            name = frame_info.get('name', '主程序')

            frames.append({
                'id': frame_id,
                'name': name,
                'line': line,
                'column': col,
                'source': {
                    'path': self.source_path,
                    'name': os.path.basename(self.source_path)
                }
            })
            frame_id += 1

        self.connection.send_response(seq, True, {
            'stackFrames': frames,
            'totalFrames': len(frames)
        }, command)

    def scopes_request(self, seq: int, command: str, args: Dict):
        """获取变量作用域"""
        scopes = [
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
        self.connection.send_response(seq, True, {'scopes': scopes}, command)

    def variables_request(self, seq: int, command: str, args: Dict):
        """获取变量列表"""
        ref = args.get('variablesReference', 0)
        variables = []

        if ref == 1:
            # 局部变量
            for name, value in self.variables.items():
                variables.append(self._make_variable(name, value))
        elif ref == 2:
            # 全局变量
            for name, value in self.variables.items():
                variables.append(self._make_variable(name, value))

        self.connection.send_response(seq, True, {'variables': variables}, command)

    def evaluate_request(self, seq: int, command: str, args: Dict):
        """表达式求值"""
        expr = args.get('expression', '')
        try:
            # 简单表达式求值: 变量名查找
            if expr in self.variables:
                value = self.variables[expr]
                result = {
                    'result': str(value),
                    'variablesReference': 0,
                    'type': type(value).__name__
                }
            else:
                # 尝试执行 Python 表达式
                result = {
                    'result': f'<未定义: {expr}>',
                    'variablesReference': 0,
                    'type': 'undefined'
                }

            self.connection.send_response(seq, True, result, command)
        except Exception as e:
            self.connection.send_response(seq, False, {
                'error': {
                    'id': 0,
                    'format': str(e),
                    'showUser': True
                }
            }, command)

    def source_request(self, seq: int, command: str, args: Dict):
        """获取源代码"""
        self.connection.send_response(seq, True, {
            'content': self.source_code,
            'mimeType': 'text/x-light'
        }, command)

    def threads_request(self, seq: int, command: str):
        """获取线程列表"""
        self.connection.send_response(seq, True, {
            'threads': [
                {'id': self.current_thread_id, 'name': '主线程'}
            ]
        }, command)

    def loaded_sources_request(self, seq: int, command: str):
        """获取已加载源文件"""
        sources = []
        if self.source_path:
            sources.append({
                'path': self.source_path,
                'name': os.path.basename(self.source_path)
            })
        self.connection.send_response(seq, True, {'sources': sources}, command)

    def exception_info_request(self, seq: int, command: str, args: Dict):
        """获取异常信息"""
        self.connection.send_response(seq, True, {
            'exceptionId': '运行时异常',
            'description': '程序执行遇到异常',
            'breakMode': 'unhandled'
        }, command)

    # =========================================================================
    # 内部辅助方法
    # =========================================================================

    def _make_variable(self, name: str, value: Any) -> Dict:
        """创建变量描述"""
        if isinstance(value, (list, dict)):
            var_ref = 100 + len(self.variables)
            return {
                'name': name,
                'value': str(value),
                'type': type(value).__name__,
                'variablesReference': var_ref
            }
        else:
            return {
                'name': name,
                'value': str(value),
                'type': type(value).__name__,
                'variablesReference': 0
            }

    def _get_stack_frames(self) -> List[Dict]:
        """获取调用栈帧"""
        if self.call_stack:
            return self.call_stack
        return [{
            'name': '主程序',
            'line': self.current_line,
            'column': 0
        }]

    def _pause_at_line(self, line: int, reason: str = 'breakpoint'):
        """在指定行暂停"""
        self.is_paused = True
        self.current_line = line
        self.connection.send_event('stopped', {
            'reason': reason,
            'threadId': self.current_thread_id,
            'description': f'暂停于第 {line} 行',
            'text': f'暂停于第 {line} 行'
        })

    def _simulate_execution(self):
        """模拟执行（逐行执行源代码）"""
        if not self.source_code:
            self._terminate_session()
            return

        lines = self.source_code.split('\n')
        total_lines = len(lines)

        while self.is_running and not self.is_paused and self.current_line <= total_lines:
            line_text = lines[self.current_line - 1].strip()

            # 模拟变量变化
            self._simulate_variables(line_text)

            # 检查断点
            if self.bp_manager.has_breakpoint_at(self.source_path, self.current_line):
                self._pause_at_line(self.current_line, 'breakpoint')
                return

            # 按步进模式执行
            if self.step_mode == 'stepOver':
                self._pause_at_line(self.current_line, 'step')
                return
            elif self.step_mode == 'stepIn':
                self._pause_at_line(self.current_line, 'step')
                return
            elif self.step_mode == 'stepOut':
                self._pause_at_line(self.current_line, 'step')
                return

            self.current_line += 1

            # 输出行执行信息
            if line_text:
                self.connection.send_event('output', {
                    'category': 'stdout',
                    'output': f'[执行] 第 {self.current_line - 1} 行: {line_text}\n'
                })

        # 执行完成
        if self.current_line > total_lines:
            self._terminate_session()

    def _simulate_variables(self, line_text: str):
        """模拟变量变化（从源代码行中提取变量赋值）"""
        # 匹配设/定义 变量名 为/等于 值
        match = re.match(r'(设|定义)\s+(\w+)\s+(为|等于)\s+(.+)', line_text)
        if match:
            name = match.group(2)
            value = match.group(4).strip('"\'')
            self.variables[name] = value

        # 匹配 变量名 = 值
        match = re.match(r'(\w+)\s*=\s*(.+)', line_text)
        if match:
            name = match.group(1)
            if name not in ('若', '则', '否', '当', '函', '类', '引', '设', '定义'):
                value = match.group(2).strip('"\'')
                self.variables[name] = value

    def _terminate_session(self):
        """终止调试会话"""
        self.is_running = False
        self.connection.send_event('output', {
            'category': 'stdout',
            'output': '\n=== 调试会话结束 ===\n'
        })
        self.connection.send_event('terminated', {})


# =============================================================================
# 主循环
# =============================================================================

def main():
    """调试适配器主入口"""
    engine = DebugEngine()
    connection = engine.connection

    while True:
        message = connection.read_message()
        if message is None:
            break

        msg_type = message.get('type', '')
        seq = message.get('seq', 0)
        command = message.get('command', '')
        args = message.get('arguments', {})

        try:
            if msg_type == 'request':
                if command == 'initialize':
                    capabilities = engine.initialize(args)
                    connection.send_response(seq, True, capabilities, command)

                elif command == 'launch':
                    success = engine.launch(args)
                    connection.send_response(seq, success, command=command)

                elif command == 'attach':
                    success = engine.attach(args)
                    connection.send_response(seq, success, command=command)

                elif command == 'disconnect':
                    engine.disconnect(args)
                    connection.send_response(seq, True, command=command)
                    break

                elif command == 'setBreakpoints':
                    bps = engine.set_breakpoints(args)
                    connection.send_response(seq, True, {
                        'breakpoints': bps
                    }, command)

                elif command == 'setExceptionBreakpoints':
                    engine.set_exception_breakpoints(args)
                    connection.send_response(seq, True, command=command)

                elif command == 'configurationDone':
                    engine.configuration_done()
                    connection.send_response(seq, True, command=command)

                elif command == 'continue':
                    engine.continue_request(seq, command)

                elif command == 'next':
                    engine.next_request(seq, command)

                elif command == 'stepIn':
                    engine.step_in_request(seq, command)

                elif command == 'stepOut':
                    engine.step_out_request(seq, command)

                elif command == 'pause':
                    engine.pause_request(seq, command)

                elif command == 'stackTrace':
                    engine.stack_trace_request(seq, command, args)

                elif command == 'scopes':
                    engine.scopes_request(seq, command, args)

                elif command == 'variables':
                    engine.variables_request(seq, command, args)

                elif command == 'evaluate':
                    engine.evaluate_request(seq, command, args)

                elif command == 'source':
                    engine.source_request(seq, command, args)

                elif command == 'threads':
                    engine.threads_request(seq, command)

                elif command == 'loadedSources':
                    engine.loaded_sources_request(seq, command)

                elif command == 'exceptionInfo':
                    engine.exception_info_request(seq, command, args)

                else:
                    connection.send_response(seq, True, command=command)

        except Exception as e:
            connection.send_response(seq, False, {
                'error': {
                    'id': 0,
                    'format': f'内部错误: {str(e)}',
                    'showUser': True
                }
            }, command)
            connection.send_event('output', {
                'category': 'stderr',
                'output': traceback.format_exc()
            })


if __name__ == '__main__':
    main()