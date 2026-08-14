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
        # 异常断点配置
        self._exception_breakpoint_filters: Dict[str, bool] = {}
        self._last_exception_info: Optional[Dict] = None
        # 数据断点
        self._data_breakpoints: Dict[str, Dict] = {}
        self._data_breakpoint_id_counter = 1
        # 变量引用系统（用于嵌套展开）
        self._variable_reference_counter = 2
        self._variable_references: Dict[int, tuple] = {}
        
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
            'setExceptionBreakpoints': self._handle_set_exception_breakpoints,
            'setDataBreakpoints': self._handle_set_data_breakpoints,
            'configurationDone': self._handle_configuration_done,
            'threads': self._handle_threads,
            'stackTrace': self._handle_stack_trace,
            'scopes': self._handle_scopes,
            'variables': self._handle_variables,
            'setVariable': self._handle_set_variable,
            'evaluate': self._handle_evaluate,
            'exceptionInfo': self._handle_exception_info,
            'completions': self._handle_completions,
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
            'supportsConditionalBreakpoints': True,
            'supportsDataBreakpoints': True,
            'supportsEvaluateForHovers': True,
            'supportsExceptionInfoRequest': True,
            'supportsExceptionOptions': True,
            'supportsFunctionBreakpoints': False,
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
            'supportedChecksumKinds': []
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
    
    def _handle_set_exception_breakpoints(self, args: Dict) -> Dict:
        """处理异常断点设置请求"""
        filters = args.get('filters', [])
        filter_options = args.get('filterOptions', [])
        
        # 存储异常断点过滤器配置
        self._exception_breakpoint_filters = {}
        for f in filters:
            self._exception_breakpoint_filters[f] = True
        
        # 处理详细的 filterOptions
        for opt in filter_options:
            filter_id = opt.get('filterId', '')
            self._exception_breakpoint_filters[filter_id] = opt.get('default', True)
        
        return {}
    
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
        """处理变量请求（支持嵌套展开）"""
        ref = args.get('variablesReference', 0)
        variables = []
        
        if ref == 1:  # 局部变量
            for name, value in self.variables.items():
                var_ref = self._get_variable_reference(name, value)
                variables.append({
                    'name': name,
                    'value': self._format_value(value),
                    'type': type(value).__name__,
                    'variablesReference': var_ref
                })
        elif ref == 2:  # 全局变量
            if self._current_frame:
                for name, value in self._current_frame.f_globals.items():
                    if not name.startswith('_'):
                        var_ref = self._get_variable_reference(name, value)
                        variables.append({
                            'name': name,
                            'value': self._format_value(value),
                            'type': type(value).__name__,
                            'variablesReference': var_ref
                        })
        else:
            # 嵌套变量展开
            container = self._variable_references.get(ref)
            if container:
                name, obj, type_name = container
                variables = self._get_child_variables(obj)
        
        return {'variables': variables}
    
    def _handle_set_variable(self, args: Dict) -> Dict:
        """处理设置变量请求"""
        name = args.get('name', '')
        value_str = args.get('value', '')
        ref = args.get('variablesReference', 0)
        
        # 解析字符串值为实际类型
        try:
            converted_value = self._parse_value(value_str)
        except Exception:
            converted_value = value_str
        
        # 根据引用ID确定变量作用域
        if ref == 1:  # 局部变量
            self.variables[name] = converted_value
            if self._current_frame:
                try:
                    self._current_frame.f_locals[name] = converted_value
                except Exception:
                    pass
        elif ref == 2:  # 全局变量
            if self._current_frame:
                try:
                    self._current_frame.f_globals[name] = converted_value
                except Exception:
                    pass
        else:
            # 嵌套容器中的变量
            container = self._variable_references.get(ref)
            if container:
                _, obj, _ = container
                if isinstance(obj, dict):
                    obj[name] = converted_value
                elif isinstance(obj, (list, tuple)):
                    try:
                        idx = int(name)
                        obj[idx] = converted_value
                    except (ValueError, IndexError):
                        pass
                elif hasattr(obj, '__dict__'):
                    setattr(obj, name, converted_value)
        
        var_ref = self._get_variable_reference(name, converted_value)
        return {
            'value': self._format_value(converted_value),
            'type': type(converted_value).__name__,
            'variablesReference': var_ref
        }
    
    def _get_variable_reference(self, name: str, value: Any) -> int:
        """获取变量的引用ID（用于嵌套展开）"""
        if value is None:
            return 0
        if isinstance(value, (bool, int, float, str, bytes, bytearray)):
            return 0
        if callable(value):
            return 0
        # 列表、字典、元组、集合、自定义对象都可展开
        if isinstance(value, (list, tuple, dict, set)):
            self._variable_reference_counter += 1
            ref = self._variable_reference_counter
            self._variable_references[ref] = (name, value, type(value).__name__)
            return ref
        # 有 __dict__ 的对象
        if hasattr(value, '__dict__'):
            self._variable_reference_counter += 1
            ref = self._variable_reference_counter
            self._variable_references[ref] = (name, value, type(value).__name__)
            return ref
        return 0
    
    def _get_child_variables(self, obj: Any) -> List[Dict]:
        """获取容器对象的子变量"""
        variables = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                var_ref = self._get_variable_reference(str(key), value)
                variables.append({
                    'name': str(key),
                    'value': self._format_value(value),
                    'type': type(value).__name__,
                    'variablesReference': var_ref
                })
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                var_ref = self._get_variable_reference(str(i), item)
                variables.append({
                    'name': str(i),
                    'value': self._format_value(item),
                    'type': type(item).__name__,
                    'variablesReference': var_ref,
                    'indexedVariables': len(obj)
                })
        elif isinstance(obj, set):
            for i, item in enumerate(sorted(obj, key=str)):
                var_ref = self._get_variable_reference(str(i), item)
                variables.append({
                    'name': str(i),
                    'value': self._format_value(item),
                    'type': type(item).__name__,
                    'variablesReference': var_ref
                })
        elif hasattr(obj, '__dict__'):
            for attr_name, attr_value in obj.__dict__.items():
                if not attr_name.startswith('_'):
                    var_ref = self._get_variable_reference(attr_name, attr_value)
                    variables.append({
                        'name': attr_name,
                        'value': self._format_value(attr_value),
                        'type': type(attr_value).__name__,
                        'variablesReference': var_ref
                    })
        return variables
    
    def _parse_value(self, value_str: str) -> Any:
        """解析字符串值为Python值"""
        if value_str in ('空', 'None', 'null'):
            return None
        if value_str in ('真', 'True', 'true'):
            return True
        if value_str in ('假', 'False', 'false'):
            return False
        # 带引号的字符串
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]
        # 数字
        try:
            return int(value_str)
        except ValueError:
            pass
        try:
            return float(value_str)
        except ValueError:
            pass
        return value_str
    
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

    def _handle_evaluate(self, args: Dict) -> Dict:
        """处理表达式求值请求（支持悬停求值、监视、调试控制台）"""
        expression = args.get('expression', '')
        frame_id = args.get('frameId', None)
        context = args.get('context', '')  # 'watch', 'repl', 'hover', 'clipboard'

        try:
            result = None
            if self._current_frame:
                # 尝试在当前帧上下文中求值
                try:
                    result = eval(expression, self._current_frame.f_globals, self._current_frame.f_locals)
                except Exception:
                    # 尝试仅作为变量名查找
                    if expression in self._current_frame.f_locals:
                        result = self._current_frame.f_locals[expression]
                    elif expression in self._current_frame.f_globals:
                        result = self._current_frame.f_globals[expression]
                    else:
                        raise NameError(f"未定义的变量: {expression}")
            else:
                # 在变量字典中查找
                if expression in self.variables:
                    result = self.variables[expression]
                else:
                    raise NameError(f"未定义的变量: {expression}")

            var_ref = self._get_variable_reference(expression, result)
            indexed = 0
            named = 0
            if isinstance(result, (list, tuple)):
                indexed = len(result)
            if isinstance(result, dict):
                named = len(result)

            return {
                'result': self._format_value(result),
                'type': type(result).__name__,
                'variablesReference': var_ref,
                'indexedVariables': indexed,
                'namedVariables': named
            }
        except Exception as e:
            return {
                'result': f"错误: {e}",
                'type': 'error',
                'variablesReference': 0
            }

    def _handle_set_data_breakpoints(self, args: Dict) -> Dict:
        """处理数据断点设置请求"""
        breakpoints = args.get('breakpoints', [])
        data_breakpoints = []

        self._data_breakpoints.clear()
        for bp in breakpoints:
            name = bp.get('name', '')
            data_bp_id = self._data_breakpoint_id_counter
            self._data_breakpoint_id_counter += 1

            # 获取当前值作为基准
            current_value = self._get_data_breakpoint_value(name)
            self._data_breakpoints[name] = {
                'id': data_bp_id,
                'previous_value': current_value
            }

            data_breakpoints.append({
                'id': data_bp_id,
                'verified': True,
                'description': f'监视变量 "{name}"'
            })

        return {'breakpoints': data_breakpoints}

    def _get_data_breakpoint_value(self, name: str) -> Any:
        """获取数据断点监视的变量值"""
        if name in self.variables:
            return self.variables[name]
        if self._current_frame:
            if name in self._current_frame.f_locals:
                return self._current_frame.f_locals[name]
            if name in self._current_frame.f_globals:
                return self._current_frame.f_globals[name]
        return None

    def _check_data_breakpoints(self) -> bool:
        """检查数据断点是否命中"""
        if not self._data_breakpoints:
            return False
        for name, info in list(self._data_breakpoints.items()):
            current_value = self._get_data_breakpoint_value(name)
            if current_value != info['previous_value']:
                info['previous_value'] = current_value
                self.send_event('stopped', {
                    'reason': 'data breakpoint',
                    'description': f'变量 "{name}" 的值已改变',
                    'text': f'"{name}" 从 {info["previous_value"]} 变为 {current_value}',
                    'threadId': 1,
                    'allThreadsStopped': True,
                    'hitBreakpointIds': [info['id']]
                })
                return True
        return False

    def _handle_exception_info(self, args: Dict) -> Dict:
        """处理异常信息请求"""
        thread_id = args.get('threadId', 1)

        # 优先使用缓存的最新异常信息
        if self._last_exception_info:
            return self._last_exception_info

        # 从调试器获取异常信息
        if self.debugger.last_exception:
            exc = self.debugger.last_exception
            exc_type = type(exc)
            tb_str = ''.join(traceback.format_exception_only(exc_type, exc)).strip()
            return {
                'exceptionId': exc_type.__name__,
                'description': str(exc),
                'breakMode': 'always',
                'details': {
                    'message': str(exc),
                    'typeName': exc_type.__name__,
                    'stackTrace': tb_str
                }
            }

        return {
            'exceptionId': 'unknown',
            'description': '无异常信息',
            'breakMode': 'unhandled'
        }

    def _handle_completions(self, args: Dict) -> Dict:
        """处理调试控制台自动补全请求"""
        text = args.get('text', '')
        column = args.get('column', len(text))
        line = args.get('line', 0)

        # 提取当前输入的前缀
        prefix = text[:column].split()[-1] if text[:column].strip() else ''

        targets = []
        seen = set()

        # 添加关键字
        keywords = [
            'if', 'else', 'elif', 'while', 'for', 'in', 'break', 'continue',
            'return', 'def', 'class', 'import', 'from', 'as', 'pass', 'del',
            'True', 'False', 'None', 'and', 'or', 'not', 'is', 'try',
            'except', 'finally', 'raise', 'with', 'yield', 'lambda',
            'print', 'len', 'range', 'type', 'int', 'str', 'float',
            'list', 'dict', 'set', 'tuple', 'bool', 'repr', 'str',
            'min', 'max', 'sum', 'abs', 'sorted', 'reversed', 'enumerate',
            'zip', 'map', 'filter', 'any', 'all', 'isinstance', 'hasattr',
            'getattr', 'setattr', 'dir', 'vars', 'locals', 'globals'
        ]

        for kw in keywords:
            if kw.startswith(prefix) and kw not in seen:
                targets.append({
                    'label': kw,
                    'type': 'keyword'
                })
                seen.add(kw)

        # 添加变量名
        for name in self.variables:
            if name.startswith(prefix) and name not in seen:
                targets.append({
                    'label': name,
                    'type': 'variable',
                    'text': name
                })
                seen.add(name)

        # 添加当前帧中的局部变量和全局变量
        if self._current_frame:
            for name in self._current_frame.f_locals:
                if name.startswith(prefix) and name not in seen:
                    targets.append({
                        'label': name,
                        'type': 'variable',
                        'text': name
                    })
                    seen.add(name)
            for name in self._current_frame.f_globals:
                if name.startswith(prefix) and not name.startswith('_') and name not in seen:
                    targets.append({
                        'label': name,
                        'type': 'variable',
                        'text': name
                    })
                    seen.add(name)

        return {'targets': targets[:100]}

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

                # 检查数据断点
                if self._check_data_breakpoints():
                    self._pause_event.clear()
                    self._pause_event.wait()
                    return

                # 检查是否因异常停止
                reason = 'breakpoint'
                if self.debugger.check_breakpoint(file, line):
                    reason = 'breakpoint'
                elif self.debugger.step_mode != LightDebugger.STEP_NONE:
                    reason = 'step'

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
                    # 捕获异常信息供后续查询
                    self._last_exception_info = {
                        'exceptionId': type(e).__name__,
                        'description': str(e),
                        'breakMode': 'always',
                        'details': {
                            'message': str(e),
                            'typeName': type(e).__name__,
                            'stackTrace': traceback.format_exc()
                        }
                    }
                    light_error = self._format_light_error(e, source, python_code)
                    self.send_event('output', {
                        'category': 'stderr',
                        'output': light_error
                    })
                    self.send_event('stopped', {
                        'reason': 'exception',
                        'description': str(e),
                        'text': type(e).__name__,
                        'threadId': 1,
                        'allThreadsStopped': True
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


def main():
    """启动调试适配器"""
    adapter = DebugAdapter()
    
    while True:
        try:
            # Read Content-Length header
            header = ''
            while True:
                line = sys.stdin.readline()
                if not line:
                    return
                header += line
                if line == '\r\n' or line == '\n':
                    break
            
            # Parse Content-Length
            match = __import__('re').search(r'Content-Length:\s*(\d+)', header)
            if not match:
                continue
            
            content_length = int(match.group(1))
            
            # Read the JSON content
            content = sys.stdin.read(content_length)
            if not content:
                continue
            
            message = json.loads(content)
            adapter.handle_message(message)
            
        except Exception as e:
            adapter.send_event('output', {
                'category': 'stderr',
                'output': f'适配器错误: {e}\n'
            })


if __name__ == '__main__':
    main()
