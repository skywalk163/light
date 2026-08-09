# -*- coding: utf-8 -*-
"""
光明调试引擎

支持：
- 单步执行（step into/over/out）
- 断点管理（设置/清除/列出）
- 变量查看
- 调用栈跟踪
"""

from typing import Dict, List, Tuple, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class StepMode(Enum):
    """单步执行模式"""
    NONE = 'none'       # 正常执行
    INTO = 'into'       # 单步进入
    OVER = 'over'       # 单步跳过
    OUT = 'out'         # 单步跳出


@dataclass
class Frame:
    """调用帧"""
    func_name: str
    file_path: str
    line: int
    local_vars: Dict[str, Any]
    func_id: str = ''


class DebugEngine:
    """光明调试引擎
    
    支持：
    - 单步执行（step into/over/out）
    - 断点管理（设置/清除/列出）
    - 变量查看
    - 调用栈跟踪
    """
    
    def __init__(self):
        self.breakpoints: Dict[str, List[int]] = {}   # 文件 -> 行号列表
        self.watch_vars: List[str] = []                # 监视变量列表
        self.call_stack: List[Frame] = []              # 调用栈
        self.local_vars: Dict[str, Any] = {}           # 当前局部变量
        self.step_mode: StepMode = StepMode.NONE       # 单步模式
        self.paused = False                            # 是否暂停
        self.current_line = 0                          # 当前行号
        self.current_file = ''                         # 当前文件
        self._breakpoint_hit_callback: Optional[Callable] = None
        self._step_hit_callback: Optional[Callable] = None
    
    # ------------------------------------------------------------------
    # 断点管理
    # ------------------------------------------------------------------
    
    def set_breakpoint(self, file_path: str, line: int) -> bool:
        """设置断点
        
        Args:
            file_path: 文件路径
            line: 行号
            
        Returns:
            是否成功（True=新增, False=已存在）
        """
        if file_path not in self.breakpoints:
            self.breakpoints[file_path] = []
        
        if line not in self.breakpoints[file_path]:
            self.breakpoints[file_path].append(line)
            self.breakpoints[file_path].sort()
            return True
        return False
    
    def clear_breakpoint(self, file_path: str, line: int) -> bool:
        """清除断点
        
        Args:
            file_path: 文件路径
            line: 行号
            
        Returns:
            是否成功（True=已清除, False=不存在）
        """
        if file_path in self.breakpoints and line in self.breakpoints[file_path]:
            self.breakpoints[file_path].remove(line)
            if not self.breakpoints[file_path]:
                del self.breakpoints[file_path]
            return True
        return False
    
    def clear_all_breakpoints(self) -> None:
        """清除所有断点"""
        self.breakpoints.clear()
    
    def list_breakpoints(self) -> List[Tuple[str, int]]:
        """列出所有断点
        
        Returns:
            断点列表，每个元素为 (文件路径, 行号)
        """
        result = []
        for file_path, lines in self.breakpoints.items():
            for line in lines:
                result.append((file_path, line))
        return result
    
    # ------------------------------------------------------------------
    # 单步执行
    # ------------------------------------------------------------------
    
    def step_into(self) -> bool:
        """单步进入
        
        设置单步模式为 INTO，下一次执行到任何行时暂停。
        
        Returns:
            是否成功
        """
        self.step_mode = StepMode.INTO
        self.paused = True
        return True
    
    def step_over(self) -> bool:
        """单步跳过
        
        设置单步模式为 OVER，在同一层级执行到下一行时暂停。
        
        Returns:
            是否成功
        """
        self.step_mode = StepMode.OVER
        self.paused = True
        return True
    
    def step_out(self) -> bool:
        """单步跳出
        
        设置单步模式为 OUT，执行到当前函数返回时暂停。
        
        Returns:
            是否成功
        """
        self.step_mode = StepMode.OUT
        self.paused = True
        return True
    
    # ------------------------------------------------------------------
    # 执行控制
    # ------------------------------------------------------------------
    
    def continue_execution(self) -> bool:
        """继续执行
        
        取消暂停状态，恢复正常执行。
        
        Returns:
            是否成功
        """
        self.paused = False
        self.step_mode = StepMode.NONE
        return True
    
    def pause(self) -> bool:
        """暂停执行
        
        Returns:
            是否成功
        """
        self.paused = True
        return True
    
    # ------------------------------------------------------------------
    # 断点/步骤检查
    # ------------------------------------------------------------------
    
    def should_break(self, file_path: str, line: int) -> bool:
        """检查当前行是否应该暂停
        
        检查顺序：
        1. 是否有断点命中
        2. 单步模式是否匹配
        
        Args:
            file_path: 当前文件路径
            line: 当前行号
            
        Returns:
            是否应该暂停
        """
        self.current_file = file_path
        self.current_line = line
        
        # 1. 断点检查
        if file_path in self.breakpoints and line in self.breakpoints[file_path]:
            self.paused = True
            if self._breakpoint_hit_callback:
                self._breakpoint_hit_callback(file_path, line)
            return True
        
        # 2. 单步模式检查
        if self.step_mode == StepMode.INTO:
            # 单步进入：任何行都暂停
            self.paused = True
            if self._step_hit_callback:
                self._step_hit_callback(self.step_mode, file_path, line)
            return True
        
        if self.step_mode == StepMode.OVER:
            # 单步跳过：只在当前层级暂停
            if self.call_stack:
                current_depth = len(self.call_stack)
                # 只在顶层暂停
                if current_depth <= 1:
                    self.paused = True
                    if self._step_hit_callback:
                        self._step_hit_callback(self.step_mode, file_path, line)
                    return True
            else:
                self.paused = True
                if self._step_hit_callback:
                    self._step_hit_callback(self.step_mode, file_path, line)
                return True
        
        if self.step_mode == StepMode.OUT:
            # 单步跳出：当调用栈深度减少时暂停
            if self.call_stack:
                current_depth = len(self.call_stack)
                if current_depth < self._saved_stack_depth:
                    self.paused = True
                    if self._step_hit_callback:
                        self._step_hit_callback(self.step_mode, file_path, line)
                    return True
        
        return False
    
    # ------------------------------------------------------------------
    # 变量查看
    # ------------------------------------------------------------------
    
    def get_variables(self) -> Dict[str, Any]:
        """获取当前变量
        
        Returns:
            当前局部变量字典
        """
        return dict(self.local_vars)
    
    def get_watch_values(self) -> Dict[str, Any]:
        """获取监视变量的值
        
        Returns:
            监视变量名 -> 值的字典
        """
        result = {}
        for var_name in self.watch_vars:
            if var_name in self.local_vars:
                result[var_name] = self.local_vars[var_name]
            else:
                # 检查调用栈中的变量
                for frame in reversed(self.call_stack):
                    if var_name in frame.local_vars:
                        result[var_name] = frame.local_vars[var_name]
                        break
                else:
                    result[var_name] = '<未定义>'
        return result
    
    def add_watch(self, var_name: str) -> bool:
        """添加监视变量
        
        Args:
            var_name: 变量名
            
        Returns:
            是否成功
        """
        if var_name not in self.watch_vars:
            self.watch_vars.append(var_name)
            return True
        return False
    
    def remove_watch(self, var_name: str) -> bool:
        """移除监视变量
        
        Args:
            var_name: 变量名
            
        Returns:
            是否成功
        """
        if var_name in self.watch_vars:
            self.watch_vars.remove(var_name)
            return True
        return False
    
    # ------------------------------------------------------------------
    # 调用栈管理
    # ------------------------------------------------------------------
    
    def get_call_stack(self) -> List[Dict]:
        """获取调用栈
        
        Returns:
            调用帧字典列表，每个元素包含 func_name, file_path, line, local_vars
        """
        return [
            {
                'func_name': frame.func_name,
                'file_path': frame.file_path,
                'line': frame.line,
                'local_vars': dict(frame.local_vars),
            }
            for frame in self.call_stack
        ]
    
    def push_frame(self, func_name: str, file_path: str, line: int, 
                   vars: Dict[str, Any] = None) -> None:
        """压入调用帧
        
        Args:
            func_name: 函数名
            file_path: 文件路径
            line: 行号
            vars: 局部变量
        """
        frame = Frame(
            func_name=func_name,
            file_path=file_path,
            line=line,
            local_vars=vars or {},
            func_id=f"{file_path}:{func_name}"
        )
        self.call_stack.append(frame)
        self.local_vars = dict(frame.local_vars)
    
    def pop_frame(self) -> Optional[Dict]:
        """弹出调用帧
        
        Returns:
            被弹出的调用帧，如果调用栈为空则返回 None
        """
        if not self.call_stack:
            return None
        
        frame = self.call_stack.pop()
        
        # 更新当前局部变量
        if self.call_stack:
            self.local_vars = dict(self.call_stack[-1].local_vars)
        else:
            self.local_vars = {}
        
        return {
            'func_name': frame.func_name,
            'file_path': frame.file_path,
            'line': frame.line,
            'local_vars': dict(frame.local_vars),
        }
    
    def update_local_vars(self, vars: Dict[str, Any]) -> None:
        """更新当前局部变量
        
        Args:
            vars: 新的局部变量字典
        """
        self.local_vars.update(vars)
        if self.call_stack:
            self.call_stack[-1].local_vars.update(vars)
    
    def update_current_line(self, line: int) -> None:
        """更新当前行号
        
        Args:
            line: 新的行号
        """
        self.current_line = line
        if self.call_stack:
            self.call_stack[-1].line = line
    
    # ------------------------------------------------------------------
    # 回调设置
    # ------------------------------------------------------------------
    
    def on_breakpoint_hit(self, callback: Callable[[str, int], None]) -> None:
        """设置断点命中回调
        
        Args:
            callback: 回调函数，接收 (file_path, line)
        """
        self._breakpoint_hit_callback = callback
    
    def on_step_hit(self, callback: Callable[[StepMode, str, int], None]) -> None:
        """设置单步命中回调
        
        Args:
            callback: 回调函数，接收 (step_mode, file_path, line)
        """
        self._step_hit_callback = callback
    
    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------
    
    def get_status(self) -> Dict[str, Any]:
        """获取调试引擎状态
        
        Returns:
            状态字典
        """
        return {
            'paused': self.paused,
            'step_mode': self.step_mode.value,
            'current_file': self.current_file,
            'current_line': self.current_line,
            'breakpoint_count': len(self.list_breakpoints()),
            'stack_depth': len(self.call_stack),
            'watch_var_count': len(self.watch_vars),
            'local_var_count': len(self.local_vars),
        }
    
    def reset(self) -> None:
        """重置调试引擎"""
        self.breakpoints.clear()
        self.watch_vars.clear()
        self.call_stack.clear()
        self.local_vars.clear()
        self.step_mode = StepMode.NONE
        self.paused = False
        self.current_line = 0
        self.current_file = ''