# -*- coding: utf-8 -*-
"""
光明调试器核心模块

提供断点管理、单步执行、变量监视等调试功能。
"""

import sys
import os
import traceback
import ast
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@dataclass
class Breakpoint:
    """断点"""
    id: int
    line: int
    condition: Optional[str] = None
    enabled: bool = True
    hit_count: int = 0
    hit_condition: Optional[str] = None  # '>', '>=', '==', '<', '<=', '%'

    def should_stop(self, current_hit_count: int) -> bool:
        """检查是否应该停止"""
        if not self.enabled:
            return False
        
        if self.hit_condition is None:
            return True
        
        if self.hit_condition == '>':
            return current_hit_count > int(self.hit_count)
        elif self.hit_condition == '>=':
            return current_hit_count >= int(self.hit_count)
        elif self.hit_condition == '==':
            return current_hit_count == int(self.hit_count)
        elif self.hit_condition == '<':
            return current_hit_count < int(self.hit_count)
        elif self.hit_condition == '<=':
            return current_hit_count <= int(self.hit_count)
        elif self.hit_condition == '%':
            return current_hit_count % int(self.hit_count) == 0
        
        return True


@dataclass
class StackFrame:
    """调用栈帧"""
    name: str
    filename: str
    lineno: int
    locals: Dict[str, Any] = field(default_factory=dict)
    globals: Dict[str, Any] = field(default_factory=dict)


class LightDebugger:
    """光明调试器"""
    
    STEP_NONE = 0
    STEP_OVER = 1  # 单步跳过
    STEP_INTO = 2  # 单步进入
    STEP_OUT = 3   # 单步跳出
    
    def __init__(self):
        self.breakpoints: Dict[str, Dict[int, Breakpoint]] = {}  # file -> line -> Breakpoint
        self.breakpoint_id_counter = 1
        
        # 调试状态
        self.step_mode = self.STEP_NONE
        self.stop_on_entry = True
        self.running = False
        self.quitting = False
        
        # 调试钩子
        self.frame_callback: Optional[Callable] = None
        
        # 调用栈
        self.call_stack: List[StackFrame] = []
        
        # 执行状态
        self.current_line = 0
        self.current_file = '<repl>'
        
        # 捕获的异常
        self.last_exception: Optional[Exception] = None
        
    def set_breakpoint(self, file: str, line: int, condition: str = None) -> Breakpoint:
        """设置断点"""
        if file not in self.breakpoints:
            self.breakpoints[file] = {}
        
        if line in self.breakpoints[file]:
            bp = self.breakpoints[file][line]
            bp.enabled = True
            if condition:
                bp.condition = condition
        else:
            bp = Breakpoint(
                id=self.breakpoint_id_counter,
                line=line,
                condition=condition
            )
            self.breakpoint_id_counter += 1
            self.breakpoints[file][line] = bp
        
        return bp
    
    def clear_breakpoint(self, file: str, line: int) -> bool:
        """清除断点"""
        if file in self.breakpoints and line in self.breakpoints[file]:
            del self.breakpoints[file][line]
            return True
        return False
    
    def get_breakpoint(self, file: str, line: int) -> Optional[Breakpoint]:
        """获取断点"""
        return self.breakpoints.get(file, {}).get(line)
    
    def list_breakpoints(self, file: str = None) -> List[Breakpoint]:
        """列出所有断点"""
        result = []
        files = [file] if file else self.breakpoints.keys()
        for f in files:
            if f in self.breakpoints:
                result.extend(self.breakpoints[f].values())
        return sorted(result, key=lambda bp: bp.id)
    
    def check_breakpoint(self, file: str, line: int) -> Optional[Breakpoint]:
        """检查是否应该在此行停止"""
        if file not in self.breakpoints:
            return None
        
        bp = self.breakpoints[file].get(line)
        if bp and bp.should_stop(bp.hit_count):
            bp.hit_count += 1
            return bp
        return None
    
    def set_step(self, mode: int):
        """设置单步模式"""
        self.step_mode = mode
    
    def should_stop_here(self, file: str, line: int) -> bool:
        """检查是否应该在此处停止"""
        # 检查断点
        bp = self.check_breakpoint(file, line)
        if bp:
            return True
        
        # 检查单步模式
        if self.step_mode == self.STEP_INTO:
            return True
        
        if self.step_mode == self.STEP_OVER:
            return True
        
        return False
    
    def on_line_change(self, file: str, line: int, frame=None):
        """行变化回调"""
        self.current_line = line
        self.current_file = file
        
        if self.should_stop_here(file, line):
            self.running = False
            if self.frame_callback:
                self.frame_callback(file, line, frame)
        
        # 重置单步模式
        if self.step_mode != self.STEP_NONE:
            self.step_mode = self.STEP_NONE
    
    def start(self):
        """开始调试"""
        self.running = True
    
    def stop(self):
        """停止调试"""
        self.running = False
        self.quitting = True
    
    def get_stack_trace(self) -> List[StackFrame]:
        """获取调用栈"""
        return list(self.call_stack)
    
    def format_stack_trace(self) -> str:
        """格式化调用栈"""
        lines = []
        lines.append("╔══════════════════════════════════════════════════════════╗")
        lines.append("║                        调用栈                            ║")
        lines.append("╠══════════════════════════════════════════════════════════╣")
        
        if not self.call_stack:
            lines.append("║  (空调用栈)                                           ║")
        else:
            for i, frame in enumerate(reversed(self.call_stack[-10:])):
                filename = os.path.basename(frame.filename)
                lines.append(f"║  {i:2d} {filename:<20} 行 {frame.lineno:<6} {frame.name:<15}║")
        
        lines.append("╚══════════════════════════════════════════════════════════╝")
        return '\n'.join(lines)
    
    def format_variables(self, frame=None) -> str:
        """格式化变量"""
        lines = []
        lines.append("╔══════════════════════════════════════════════════════════╗")
        lines.append("║                        局部变量                           ║")
        lines.append("╠══════════════════════════════════════════════════════════╣")
        
        vars_list = []
        if frame:
            # 从 frame 获取局部变量
            try:
                vars_list = list(frame.f_locals.items())
            except:
                pass
        
        # 合并调试器的变量
        for name, value in sorted(self.globals.items()) if hasattr(self, 'globals') else []:
            vars_list.append((name, value))
        
        if not vars_list:
            lines.append("║  (无局部变量)                                         ║")
        else:
            for name, value in vars_list[:20]:  # 最多显示20个
                if name.startswith('_'):
                    continue
                value_str = self._format_value(value)
                if len(value_str) > 40:
                    value_str = value_str[:37] + "..."
                lines.append(f"║  {name:<20} = {value_str:<30}║")
        
        lines.append("╚══════════════════════════════════════════════════════════╝")
        return '\n'.join(lines)
    
    def _format_value(self, value: Any) -> str:
        """格式化值"""
        if value is None:
            return '空'
        if isinstance(value, str):
            if len(value) > 30:
                return f'"{value[:27]}..."'
            return f'"{value}"'
        if isinstance(value, bool):
            return '真' if value else '假'
        if isinstance(value, (list, tuple)):
            if len(value) > 10:
                return f'{type(value).__name__}[{len(value)}]'
            return f'{type(value).__name__}({value})'
        if isinstance(value, dict):
            if len(value) > 5:
                return f'字典[{len(value)}]'
            return f'字典({value})'
        if isinstance(value, (int, float)):
            return str(value)
        if callable(value):
            return f'<函数 {value.__name__}>'
        return f'<{type(value).__name__}>'


class DebuggerContext:
    """调试上下文管理器"""
    
    def __init__(self, debugger: LightDebugger):
        self.debugger = debugger
        self.old_trace = None
        
    def __enter__(self):
        """进入调试上下文"""
        self.old_trace = sys.gettrace()
        sys.settrace(self._trace_func)
        return self.debugger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出调试上下文"""
        sys.settrace(self.old_trace)
        return False
    
    def _trace_func(self, frame, event, arg):
        """跟踪函数"""
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno

        if event == 'line':
            self.debugger.on_line_change(filename, lineno, frame)

            # 如果调试器停止，等待恢复
            if not self.debugger.running:
                return None

        elif event == 'call':
            self.debugger.call_stack.append(StackFrame(
                name=frame.f_code.co_name,
                filename=filename,
                lineno=lineno,
                locals=dict(frame.f_locals),
                globals=dict(frame.f_globals)
            ))

        elif event == 'return' and self.debugger.call_stack:
            self.debugger.call_stack.pop()

        elif event == 'exception':
            self.debugger.last_exception = arg[1]

        return self._trace_func


def create_debugger() -> LightDebugger:
    """创建调试器实例"""
    return LightDebugger()
