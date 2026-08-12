#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
光明 REPL 增强模式

使用 prompt_toolkit 提供：
- 语法高亮输入
- Tab 补全
- 历史导航（上下箭头）
- 多行编辑支持
"""

import sys
import os
from typing import Optional, List, Dict

# 尝试导入 prompt_toolkit
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.key_binding import KeyBindings

    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False


class EnhancedREPL:
    """增强版 REPL（prompt_toolkit 驱动）

    提供：
    - 语法高亮
    - Tab 补全
    - 历史记录导航
    - 多行编辑
    """

    def __init__(self, parent_repl):
        """初始化增强 REPL

        Args:
            parent_repl: LightREPL 实例
        """
        self.parent = parent_repl
        self._session = None
        self._key_bindings = None

        if not HAS_PROMPT_TOOLKIT:
            return

        self._setup_key_bindings()
        self._setup_session()

    def _setup_key_bindings(self) -> None:
        """设置快捷键绑定"""
        kb = KeyBindings()

        @kb.add('c-d')
        def _(event):
            """Ctrl+D 退出"""
            event.app.exit(result=None)

        @kb.add('c-c')
        def _(event):
            """Ctrl+C 中断"""
            event.app.exit(result='')

        self._key_bindings = kb

    def _setup_session(self) -> None:
        """设置 prompt_toolkit 会话"""
        if not HAS_PROMPT_TOOLKIT:
            return

        # 历史记录文件
        history_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '.repl_history'
        )

        # 语法高亮器
        from .highlighter import PromptToolkitLexer, LightHighlighter
        highlighter = LightHighlighter(use_color=True)
        lexer = PromptToolkitLexer(highlighter)

        # 补全器
        from .completer import PromptToolkitCompleter, LightCompleter
        completer = PromptToolkitCompleter(self.parent.completer)

        self._session = PromptSession(
            history=FileHistory(history_path),
            auto_suggest=AutoSuggestFromHistory(),
            enable_history_search=True,
            key_bindings=self._key_bindings,
            lexer=lexer,
            completer=completer,
            complete_while_typing=True,
            multiline=False,
            reserve_space_for_menu=4,
        )

    def read_input(self, prompt: str) -> Optional[str]:
        """读取用户输入（增强版）

        Args:
            prompt: 提示符

        Returns:
            用户输入，EOF 时返回 None
        """
        if not HAS_PROMPT_TOOLKIT or self._session is None:
            return self._fallback_read(prompt)

        try:
            return self._session.prompt(prompt)
        except (EOFError, KeyboardInterrupt):
            return None

    def _fallback_read(self, prompt: str) -> Optional[str]:
        """回退到标准输入"""
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return None

    def update_env(self, env: Dict) -> None:
        """更新环境变量（用于补全器同步）"""
        self.parent.completer.update_env(env)