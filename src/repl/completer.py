#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
光明 REPL 自动补全

提供关键字、动词、变量名补全以及上下文感知补全。
"""

from typing import List, Dict, Optional, Set
import os
import re

# 关键字列表
KEYWORDS_LIST = [
    '设', '为', '函数', '段落', '接收', '返回', '类', '继承', '实现',
    '属性', '构造', '新建', '己', '如果', '那么', '否则', '结束',
    '遍历', '当', '跳出', '跳过', '尝试', '捕获', '抛出',
    '导入', '导出', '从', '真', '假', '空',
]

# 动词白名单
try:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
    from keywords import VERB_ARITY
    VERBS_LIST = list(VERB_ARITY.keys())
except Exception:
    VERBS_LIST = [
        '打印', '长', '首', '末', '排序', '反转', '求和',
        '求最大', '求最小', '去重', '筛选', '映射',
        '转整数', '转浮点', '转字符串', '字符串长度',
        '分割字符串', '连接字符串', '替换字符串', '去除空白',
        '读取文件', '写入文件', '文件存在', '目录存在',
    ]

# 内置类型
TYPES_LIST = ['数', '串', '列', '典', '布尔', '任意', '整数', '浮数']

# 语句开始关键字
STATEMENT_STARTERS = [
    '设', '如果', '遍历', '当', '函数', '段落', '类', '接口',
    '导入', '从', '尝试', '返回', '打印',
]

# 导入语句补全
IMPORT_KEYWORDS = ['导入', '从']

# 条件语句补全
CONDITIONAL_KEYWORDS = ['如果', '那么', '否则', '当']

# 循环语句补全
LOOP_KEYWORDS = ['遍历', '当']

# 块语句结束关键字
BLOCK_END_KEYWORDS = ['结束', '否则']


class LightCompleter:
    """光明自动补全器（增强版）

    支持：
    - 语法关键字上下文补全
    - 导入语句补全
    - 模块路径补全
    - 点号访问补全
    - 变量类型推断补全
    - 函数参数补全
    """

    def __init__(self, env: Dict = None):
        """初始化

        Args:
            env: 当前环境变量字典
        """
        self.env = env or {}
        self._stdlib_paths: List[str] = []
        self._contrib_paths: List[str] = []
        self._module_cache: Set[str] = set()
        self._scan_stdlib()

    def _scan_stdlib(self) -> None:
        """扫描标准库和 contrib 目录获取模块名"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # stdlib 目录
        stdlib_dir = os.path.join(base_dir, 'stdlib')
        if os.path.isdir(stdlib_dir):
            self._stdlib_paths = self._scan_directory(stdlib_dir)

        # contrib 目录
        contrib_dir = os.path.join(base_dir, 'contrib')
        if os.path.isdir(contrib_dir):
            self._contrib_paths = self._scan_directory(contrib_dir)

        # 缓存模块名
        for path in self._stdlib_paths + self._contrib_paths:
            name = os.path.splitext(os.path.basename(path))[0]
            self._module_cache.add(name)

    def _scan_directory(self, directory: str) -> List[str]:
        """扫描目录下的 .light 文件

        Args:
            directory: 目录路径

        Returns:
            文件路径列表
        """
        paths = []
        try:
            for f in os.listdir(directory):
                if f.endswith('.light') or f.endswith('.py'):
                    paths.append(os.path.join(directory, f))
                elif os.path.isdir(os.path.join(directory, f)):
                    # 子目录中的模块
                    sub_path = os.path.join(directory, f, '__init__.light')
                    if os.path.exists(sub_path):
                        paths.append(sub_path)
        except Exception:
            pass
        return paths

    def get_completions(self, text: str, cursor_pos: int = None) -> List[str]:
        """获取补全建议（上下文感知）

        Args:
            text: 当前输入文本
            cursor_pos: 光标位置（可选）

        Returns:
            补全建议列表
        """
        if cursor_pos is None:
            cursor_pos = len(text)

        text_before_cursor = text[:cursor_pos]

        # 判断上下文类型
        context = self._detect_context(text_before_cursor)

        # 根据上下文调用对应的补全方法
        if context == 'import':
            return self._complete_import(text_before_cursor)
        elif context == 'module_path':
            return self._complete_module_path(text_before_cursor)
        elif context == 'dot_access':
            return self._complete_dot_access(text_before_cursor)
        elif context == 'function_args':
            return self._complete_function_args(text_before_cursor)
        elif context == 'statement_start':
            return self._complete_statement_start(text_before_cursor)
        elif context == 'after_keyword':
            return self._complete_after_keyword(text_before_cursor)
        else:
            return self._complete_general(text_before_cursor)

    def _detect_context(self, text: str) -> str:
        """检测当前输入上下文

        Args:
            text: 光标前的文本

        Returns:
            上下文类型: 'import', 'module_path', 'dot_access', 'function_args',
                        'statement_start', 'after_keyword', 'general'
        """
        text = text.strip()

        if not text:
            return 'statement_start'

        # 导入语句
        if text == '导入' or text.endswith('导入'):
            return 'import'
        if text.startswith('从 ') or text.startswith('从'):
            return 'module_path'
        if '导入' in text and text.count('导入') == text.count('从') + 1:
            # 从 ... 导入 ...
            if '导入' in text:
                parts = text.split('导入', 1)
                if len(parts) > 1 and parts[1].strip():
                    return 'import'
                return 'module_path'

        # 点号访问
        if '.' in text:
            # 检查是否以变量名. 结尾
            last_dot = text.rfind('.')
            if last_dot > 0:
                prefix = text[:last_dot].strip()
                if prefix and not prefix[-1].isspace():
                    return 'dot_access'

        # 函数调用（参数补全）
        if '(' in text and ')' not in text[text.rfind('('):]:
            return 'function_args'

        # 关键字后补全
        words = text.split()
        last_word = words[-1] if words else ''
        if last_word in ['设', '从', '导入', '返回', '遍历', '继承']:
            return 'after_keyword'
        # 设 <变量名> 后补全 "为"
        if len(words) >= 2 and words[-2] == '设':
            return 'after_keyword'

        return 'general'

    # ------------------------------------------------------------------
    # 导入语句补全
    # ------------------------------------------------------------------

    def _complete_import(self, text: str) -> List[str]:
        """导入语句补全

        Args:
            text: 当前输入文本

        Returns:
            补全建议列表
        """
        words = text.split()
        last_word = words[-1] if words else ''

        candidates = []

        # 模块名补全
        module_names = sorted(self._module_cache)
        if last_word and last_word != '导入':
            candidates.extend(self._match(last_word, module_names))
        else:
            candidates.extend(list(self._module_cache)[:10])

        # 如果已经输入了模块名，提示 "从" 或 "导入"
        if last_word in self._module_cache:
            candidates.extend(['导入', '从'])

        return candidates[:20]

    def _complete_module_path(self, text: str) -> List[str]:
        """模块路径补全

        Args:
            text: 当前输入文本

        Returns:
            补全建议列表
        """
        # 提取路径部分
        # 从 <路径> 导入 <模块>
        import_match = re.match(r'从\s+(.*?)\s*导入\s*', text)
        if import_match:
            # 导入后的模块名补全
            after_import = import_match.group(1)
            words = text.split()
            last_word = words[-1] if words else ''
            return self._match(last_word, sorted(self._module_cache))[:10]

        # 路径补全
        path_match = re.match(r'从\s+(.*)', text)
        if path_match:
            path_part = path_match.group(1).strip()
            # 搜索路径中的模块
            return self._match(path_part, sorted(self._module_cache))[:10]

        return sorted(self._module_cache)[:10]

    # ------------------------------------------------------------------
    # 点号访问补全
    # ------------------------------------------------------------------

    def _complete_dot_access(self, text: str) -> List[str]:
        """点号访问补全

        Args:
            text: 当前输入文本

        Returns:
            补全建议列表
        """
        last_dot = text.rfind('.')
        if last_dot < 0:
            return []

        obj_name = text[:last_dot].strip()
        prefix = text[last_dot + 1:]

        # 从环境变量中获取对象
        obj = self.env.get(obj_name) if obj_name in self.env else None
        if obj is None:
            return []

        # 获取对象的属性和方法
        try:
            members = [m for m in dir(obj) if not m.startswith('_')]
            return self._match(prefix, members)[:20]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # 函数参数补全
    # ------------------------------------------------------------------

    def _complete_function_args(self, text: str) -> List[str]:
        """函数参数补全

        Args:
            text: 当前输入文本

        Returns:
            补全建议列表
        """
        # 提取函数名
        func_match = re.search(r'(\w+)\([^)]*$', text)
        if not func_match:
            # 尝试匹配中文函数名
            func_match = re.search(r'([\u4e00-\u9fff\w]+)\([^)]*$', text)

        if not func_match:
            return self._complete_general(text)

        func_name = func_match.group(1)

        # 从环境变量中查找函数
        if func_name in self.env:
            func = self.env[func_name]
            if callable(func):
                try:
                    import inspect
                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    if params:
                        return [f"{p}=" for p in params]
                except Exception:
                    pass

        # 从关键字中获取常见函数参数
        if func_name in VERBS_LIST:
            return ['值', '索引', '列表', '字符串', '数字']

        return []

    # ------------------------------------------------------------------
    # 语句开始补全
    # ------------------------------------------------------------------

    def _complete_statement_start(self, text: str) -> List[str]:
        """语句开始补全

        Args:
            text: 当前输入文本

        Returns:
            补全建议列表
        """
        words = text.split()
        if not words:
            return STATEMENT_STARTERS[:10]

        last_word = words[-1]
        return self._match(last_word, STATEMENT_STARTERS)[:10]

    def _complete_after_keyword(self, text: str) -> List[str]:
        """关键字后补全

        Args:
            text: 当前输入文本

        Returns:
            补全建议列表
        """
        words = text.split()
        if not words:
            return []

        last_word = words[-1]

        # 检查是否在 "设 <变量名>" 上下文中，提示 "为"
        if len(words) >= 2 and words[-2] == '设' and last_word != '设':
            return ['为']

        # 不同关键字后的补全
        after_map = {
            '设': self._complete_after_set(text),
            '从': sorted(self._module_cache),
            '导入': sorted(self._module_cache),
            '返回': self._get_all_names(),
            '遍历': ['列', '典', '范围'],
            '继承': ['类', '接口'],
        }

        return after_map.get(last_word, [])[:10]

    def _complete_after_set(self, text: str) -> List[str]:
        """'设' 关键字后的补全

        Args:
            text: 当前输入文本

        Returns:
            补全建议列表
        """
        # 设 <变量名> 为 <值>
        words = text.split()
        if len(words) >= 2:
            # 已经有变量名，提示 "为"
            return ['为']
        else:
            # 提示变量名（从环境中已有的变量名）
            return list(self.env.keys())[:10]

    # ------------------------------------------------------------------
    # 通用补全
    # ------------------------------------------------------------------

    def _complete_general(self, text: str) -> List[str]:
        """通用补全

        Args:
            text: 当前输入文本

        Returns:
            补全建议列表
        """
        words = text.split()
        if not words:
            return KEYWORDS_LIST[:10]

        last_word = words[-1]

        candidates = []

        # 关键字
        candidates.extend(self._match(last_word, KEYWORDS_LIST))

        # 动词
        candidates.extend(self._match(last_word, VERBS_LIST))

        # 类型
        candidates.extend(self._match(last_word, TYPES_LIST))

        # 环境变量
        if self.env:
            candidates.extend(self._match(last_word, list(self.env.keys())))

        # 模块名
        candidates.extend(self._match(last_word, sorted(self._module_cache)))

        # 内置函数
        builtins = sorted(self._module_cache)
        candidates.extend(self._match(last_word, builtins))

        return candidates[:20]

    def _get_all_names(self) -> List[str]:
        """获取所有可用名称（变量 + 关键字 + 动词）"""
        names = set()
        names.update(self.env.keys())
        names.update(KEYWORDS_LIST)
        names.update(VERBS_LIST)
        names.update(TYPES_LIST)
        names.update(self._module_cache)
        return sorted(names)

    def _match(self, prefix: str, candidates: List[str]) -> List[str]:
        """匹配前缀

        Args:
            prefix: 前缀字符串
            candidates: 候选列表

        Returns:
            匹配的候选列表
        """
        if not prefix:
            return candidates[:10]
        return [c for c in candidates if c.startswith(prefix)]

    def update_env(self, env: Dict):
        """更新环境

        Args:
            env: 新的环境变量字典
        """
        self.env = env


# prompt_toolkit 补全器（可选）
try:
    from prompt_toolkit.completion import Completer, Completion

    class PromptToolkitCompleter(Completer):
        """prompt_toolkit 补全器"""

        def __init__(self, light_completer: LightCompleter):
            self.completer = light_completer

        def get_completions(self, document, complete_event):
            text = document.text
            cursor_pos = document.cursor_position

            completions = self.completer.get_completions(text, cursor_pos)

            for c in completions:
                # 计算起始位置（替换最后一个词）
                words = text[:cursor_pos].split()
                if words:
                    start_pos = cursor_pos - len(words[-1])
                else:
                    start_pos = cursor_pos

                yield Completion(c, start_position=-len(words[-1]) if words else 0)

    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False
    PromptToolkitCompleter = None