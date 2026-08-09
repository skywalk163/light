"""光明 REPL 命令处理器"""

from typing import Any, Dict, List, Optional
import os


class CommandHandler:
    """光明 REPL 命令处理器"""

    # 命令映射（主命令 -> 中文别名）
    COMMANDS = {
        'help': ['帮助', 'h'],
        'exit': ['退出', 'quit', 'q'],
        'clear': ['清除', 'cls'],
        'reset': ['重置'],
        'vars': ['变量', 'var'],
        'funcs': ['函数', '段落', 'func', 'functions'],
        'classes': ['类', 'class'],
        'history': ['历史'],
        'load': ['加载'],
        'save': ['保存'],
        'debug': ['调试'],
        'step': ['单步'],
        'continue': ['继续', 'cont', 'c'],
        'break': ['断点', 'bp'],
        'stack': ['栈', '调用栈', 'callstack'],
        'watch': ['监视'],
    }

    def __init__(self, env: Dict = None, executor=None):
        """初始化命令处理器

        Args:
            env: 环境变量字典
            executor: 执行器实例
        """
        self.env = env if env is not None else {}
        self.executor = executor
        self._history: List[str] = []
        self._debug_enabled = False
        self._debug_engine = None  # 延迟导入 DebugEngine

    def _get_debug_engine(self):
        """获取调试引擎实例（延迟初始化）"""
        if self._debug_engine is None:
            try:
                from debug_engine import DebugEngine
                self._debug_engine = DebugEngine()
            except ImportError:
                return None
        return self._debug_engine

    def handle(self, input: str) -> Any:
        """处理命令输入

        Args:
            input: 命令字符串（已去除前导冒号）

        Returns:
            'EXIT' - 退出REPL
            'CLEAR' - 清屏
            'RESET' - 重置环境
            其他字符串 - 显示给用户
        """
        input = input.strip()
        if not input:
            return ''

        # 去除前导冒号
        if input.startswith(':'):
            input = input[1:]

        # 解析命令和参数
        parts = input.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ''

        # 查找命令（支持别名）
        actual_cmd = self._resolve_command(cmd)
        if actual_cmd is None:
            return f"未知命令: {cmd}"

        return self._execute(actual_cmd, args)

    def _resolve_command(self, cmd: str) -> Optional[str]:
        """解析命令，支持别名

        Args:
            cmd: 命令或别名

        Returns:
            主命令名称，如果未找到返回None
        """
        # 先检查是否已经是主命令
        if cmd in self.COMMANDS:
            return cmd

        # 搜索别名
        for main_cmd, aliases in self.COMMANDS.items():
            if cmd in aliases:
                return main_cmd

        return None

    def _execute(self, cmd: str, args: str) -> Any:
        """执行命令

        Args:
            cmd: 命令名称
            args: 命令参数

        Returns:
            命令执行结果
        """
        handlers = {
            'help': self._help,
            'exit': lambda: 'EXIT',
            'clear': lambda: 'CLEAR',
            'reset': lambda: 'RESET',
            'vars': lambda: self._show_vars(),
            'funcs': lambda: self._show_funcs(),
            'classes': lambda: self._show_classes(),
            'history': lambda: self._show_history(),
            'load': lambda: self._load_file(args),
            'save': lambda: self._save_session(args),
            'debug': lambda: self._toggle_debug(args),
            'step': lambda: self._do_step(args),
            'continue': lambda: self._do_continue(args),
            'break': lambda: self._do_break(args),
            'stack': lambda: self._show_stack(),
            'watch': lambda: self._do_watch(args),
        }

        handler = handlers.get(cmd)
        if handler:
            return handler()

        return f"未知命令: {cmd}"

    def _help(self) -> str:
        """显示帮助信息"""
        return """光明 REPL 帮助

命令:
  :help / :帮助     - 显示此帮助
  :exit / :退出     - 退出 REPL
  :clear / :清除    - 清屏
  :reset / :重置    - 重置环境
  :vars / :变量     - 显示所有变量
  :funcs / :段落    - 显示所有段落
  :classes / :类    - 显示所有类
  :history / :历史  - 显示命令历史
  :load <file>      - 加载文件
  :save <file>      - 保存会话

调试命令:
  :debug on/off     - 开启/关闭调试模式
  :step             - 单步执行
  :continue / :继续 - 继续执行
  :break <文件> <行> - 设置断点（如 :break test.light 10）
  :break list       - 列出所有断点
  :break clear      - 清除所有断点
  :stack / :调用栈  - 显示调用栈
  :watch <变量>     - 添加监视变量（如 :watch 甲）
  :watch list       - 列出所有监视变量
  :watch remove <名> - 移除监视变量"""

    # ------------------------------------------------------------------
    # 变量/函数/类显示
    # ------------------------------------------------------------------

    def _show_vars(self) -> str:
        """显示所有变量（增强格式）"""
        if not self.env:
            return "无变量"

        lines = []
        lines.append("变量列表:")
        lines.append("─" * 50)

        if not self.env:
            return "无变量"

        # 按类型分组显示
        for name, value in self.env.items():
            var_type = type(value).__name__
            type_icon = {
                'str': '📝',
                'int': '🔢',
                'float': '🔢',
                'list': '📋',
                'dict': '📖',
                'bool': '✅',
                'NoneType': '⬜',
                'function': '🔧',
            }.get(var_type, '❓')
            lines.append(f"  {type_icon} {name} = {repr(value)}  ({var_type})")

        return "\n".join(lines)

    def _show_funcs(self) -> str:
        """显示所有段落（函数）"""
        if not self.executor:
            return "无段落"

        funcs = getattr(self.executor, 'funcs', {})
        if not funcs:
            # 尝试从环境获取
            if hasattr(self.executor, 'env') and hasattr(self.executor.env, 'functions'):
                funcs = self.executor.env.functions
            else:
                return "无段落"

        if not funcs:
            return "无段落"

        lines = []
        lines.append("段落列表:")
        lines.append("─" * 50)
        for name in funcs:
            lines.append(f"  📌 {name}")
        return "\n".join(lines)

    def _show_classes(self) -> str:
        """显示所有类"""
        if not self.executor:
            return "无类"

        classes = getattr(self.executor, 'classes', {})
        if not classes:
            return "无类"

        lines = []
        lines.append("类列表:")
        lines.append("─" * 50)
        for name in classes:
            lines.append(f"  📦 {name}")
        return "\n".join(lines)

    def _show_history(self) -> str:
        """显示命令历史"""
        if not self._history:
            return "无历史"

        lines = []
        lines.append("历史记录:")
        lines.append("─" * 50)
        for i, cmd in enumerate(self._history, 1):
            lines.append(f"  {i:3d}. {cmd}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 文件操作
    # ------------------------------------------------------------------

    def _load_file(self, filename: str) -> str:
        """加载文件"""
        if not filename:
            return "请指定文件名: :load <file>"

        if not os.path.exists(filename):
            return f"文件不存在: {filename}"

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                code = f.read()

            if self.executor:
                self.executor.execute(code)
                return f"已加载文件: {filename}"
            else:
                return f"加载文件: {filename}"
        except Exception as e:
            return f"加载失败: {e}"

    def _save_session(self, filename: str) -> str:
        """保存会话"""
        if not filename:
            return "请指定文件名: :save <file>"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for item in self._history:
                    f.write(item + '\n')
            return f"会话已保存: {filename}"
        except Exception as e:
            return f"保存失败: {e}"

    # ------------------------------------------------------------------
    # 调试命令
    # ------------------------------------------------------------------

    def _toggle_debug(self, args: str) -> str:
        """切换调试模式"""
        args = args.strip().lower()

        if args == 'on':
            self._debug_enabled = True
            engine = self._get_debug_engine()
            if engine is None:
                return "调试引擎不可用（debug_engine 模块未找到）"
            return "调试模式已开启"
        elif args == 'off':
            self._debug_enabled = False
            if self._debug_engine:
                self._debug_engine.reset()
            return "调试模式已关闭"
        else:
            return "用法: :debug on/off"

    def _do_break(self, args: str) -> str:
        """处理断点命令"""
        if not self._debug_enabled:
            return "请先开启调试模式: :debug on"

        engine = self._get_debug_engine()
        if engine is None:
            return "调试引擎不可用"

        args = args.strip()
        if not args:
            return "用法: :break <文件> <行号> 或 :break list 或 :break clear"

        if args == 'list':
            breakpoints = engine.list_breakpoints()
            if not breakpoints:
                return "无断点"
            lines = ["断点列表:", "─" * 50]
            for file_path, line in breakpoints:
                lines.append(f"  📍 {file_path}:{line}")
            return "\n".join(lines)

        if args == 'clear':
            engine.clear_all_breakpoints()
            return "所有断点已清除"

        # 解析 :break <文件> <行号>
        parts = args.split()
        if len(parts) >= 2:
            file_path = parts[0]
            try:
                line = int(parts[1])
                if engine.set_breakpoint(file_path, line):
                    return f"断点已设置: {file_path}:{line}"
                else:
                    return f"断点已存在: {file_path}:{line}"
            except ValueError:
                return f"行号无效: {parts[1]}"
        else:
            return "用法: :break <文件> <行号>"

    def _do_step(self, args: str) -> str:
        """单步执行"""
        if not self._debug_enabled:
            return "请先开启调试模式: :debug on"

        engine = self._get_debug_engine()
        if engine is None:
            return "调试引擎不可用"

        mode = args.strip().lower()
        if mode == 'into' or mode == 'i':
            engine.step_into()
            return "单步进入模式已激活"
        elif mode == 'over' or mode == 'o' or not mode:
            engine.step_over()
            return "单步跳过模式已激活"
        elif mode == 'out' or mode == 'u':
            engine.step_out()
            return "单步跳出模式已激活"
        else:
            return "用法: :step [into|over|out]"

    def _do_continue(self, args: str) -> str:
        """继续执行"""
        if not self._debug_enabled:
            return "请先开启调试模式: :debug on"

        engine = self._get_debug_engine()
        if engine is None:
            return "调试引擎不可用"

        engine.continue_execution()
        return "继续执行"

    def _show_stack(self) -> str:
        """显示调用栈"""
        if not self._debug_enabled:
            return "请先开启调试模式: :debug on"

        engine = self._get_debug_engine()
        if engine is None:
            return "调试引擎不可用"

        stack = engine.get_call_stack()
        if not stack:
            return "调用栈为空"

        lines = []
        lines.append("调用栈:")
        lines.append("─" * 60)
        for i, frame in enumerate(stack):
            lines.append(
                f"  #{i} {frame['func_name']} "
                f"at {frame['file_path']}:{frame['line']}"
            )
            if frame['local_vars']:
                var_str = ", ".join(
                    f"{k}={v}" for k, v in frame['local_vars'].items()
                )
                lines.append(f"     vars: {var_str}")
        lines.append("─" * 60)

        # 附加调试引擎状态
        status = engine.get_status()
        lines.append(f"当前状态: {'暂停中' if status['paused'] else '运行中'}")
        lines.append(f"单步模式: {status['step_mode']}")
        if status['current_file']:
            lines.append(f"当前位置: {status['current_file']}:{status['current_line']}")

        return "\n".join(lines)

    def _do_watch(self, args: str) -> str:
        """处理监视变量命令"""
        if not self._debug_enabled:
            return "请先开启调试模式: :debug on"

        engine = self._get_debug_engine()
        if engine is None:
            return "调试引擎不可用"

        args = args.strip()
        if not args:
            return "用法: :watch <变量名> 或 :watch list 或 :watch remove <变量名>"

        if args == 'list':
            watch_values = engine.get_watch_values()
            if not watch_values:
                return "无监视变量"
            lines = ["监视变量:", "─" * 50]
            for name, value in watch_values.items():
                lines.append(f"  👁 {name} = {repr(value)}")
            return "\n".join(lines)

        if args.startswith('remove '):
            var_name = args[7:].strip()
            if engine.remove_watch(var_name):
                return f"已移除监视变量: {var_name}"
            else:
                return f"监视变量不存在: {var_name}"

        if engine.add_watch(args):
            return f"已添加监视变量: {args}"
        else:
            return f"监视变量已存在: {args}"

    # ------------------------------------------------------------------
    # 历史记录
    # ------------------------------------------------------------------

    def add_history(self, cmd: str) -> None:
        """添加命令到历史记录

        Args:
            cmd: 命令字符串
        """
        self._history.append(cmd)