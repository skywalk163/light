#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
光明 REPL 语法高亮

提供关键字、动词、字符串等的高亮显示。
"""

from typing import List, Tuple

# ANSI颜色代码
COLORS = {
    'keyword': '\033[34m',     # 蓝色
    'verb': '\033[32m',        # 绿色
    'string': '\033[33m',      # 黄色
    'number': '\033[35m',      # 紫色
    'comment': '\033[90m',     # 灰色
    'error': '\033[31m',       # 红色
    'reset': '\033[0m',        # 重置
}

# 关键字集合
KEYWORDS_SET = set([
    '设', '为', '函数', '段落', '接收', '返回', '类', '继承', '实现',
    '属性', '构造', '新建', '己', '如果', '那么', '否则', '结束',
    '遍历', '当', '跳出', '跳过', '尝试', '捕获', '抛出',
    '导入', '导出', '从', '真', '假', '空',
])

# 动词集合
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
    from keywords import VERB_ARITY
    VERBS_SET = set(VERB_ARITY.keys())
except Exception:
    VERBS_SET = set([
        '打印', '长', '首', '末', '排序', '反转', '求和',
        '求最大', '求最小', '去重', '筛选', '映射',
        '转整数', '转浮点', '转字符串', '字符串长度',
        '分割字符串', '连接字符串', '替换字符串', '去除空白',
        '读取文件', '写入文件', '文件存在', '目录存在',
    ])


class LightHighlighter:
    """光明语法高亮器"""
    
    def __init__(self, use_color: bool = True):
        """初始化
        
        Args:
            use_color: 是否使用颜色
        """
        self.use_color = use_color
    
    def highlight(self, text: str) -> str:
        """高亮文本
        
        Args:
            text: 输入文本
            
        Returns:
            高亮后的文本
        """
        if not self.use_color:
            return text
        
        result = []
        i = 0
        
        while i < len(text):
            # 注释
            if text[i] == '#':
                end = text.find('\n', i)
                if end == -1:
                    end = len(text)
                result.append(self._color('comment', text[i:end]))
                i = end
                continue
            
            # 字符串
            if text[i] in '"\'':
                quote = text[i]
                result.append(self._color('string', quote))
                i += 1
                while i < len(text) and text[i] != quote:
                    if text[i] == '\\' and i + 1 < len(text):
                        result.append(text[i:i+2])
                        i += 2
                    else:
                        result.append(text[i])
                        i += 1
                if i < len(text):
                    result.append(self._color('string', text[i]))
                    i += 1
                continue
            
            # 数字
            if text[i].isdigit():
                j = i
                while j < len(text) and (text[j].isdigit() or text[j] == '.'):
                    j += 1
                result.append(self._color('number', text[i:j]))
                i = j
                continue
            
            # 中文关键字/动词
            if self._is_chinese(text[i]):
                word = self._extract_chinese_word(text, i)
                
                if word in KEYWORDS_SET:
                    result.append(self._color('keyword', word))
                elif word in VERBS_SET:
                    result.append(self._color('verb', word))
                else:
                    result.append(word)
                
                i += len(word)
                continue
            
            # 其他字符
            result.append(text[i])
            i += 1
        
        return ''.join(result)
    
    def _color(self, color_type: str, text: str) -> str:
        """添加颜色"""
        if not self.use_color or color_type not in COLORS:
            return text
        return f"{COLORS[color_type]}{text}{COLORS['reset']}"
    
    def _is_chinese(self, ch: str) -> bool:
        """判断是否是中文"""
        return '\u4e00' <= ch <= '\u9fff'
    
    def _extract_chinese_word(self, text: str, start: int) -> str:
        """提取中文词"""
        end = start
        while end < len(text) and self._is_chinese(text[end]):
            end += 1
        return text[start:end]


# prompt_toolkit 高亮器（可选）
try:
    from prompt_toolkit.lexers import Lexer
    
    class PromptToolkitLexer(Lexer):
        """prompt_toolkit 词法分析器"""
        
        def __init__(self, highlighter: LightHighlighter):
            self.highlighter = highlighter
        
        def lex_document(self, document):
            def get_line(lineno):
                line = document.lines[lineno]
                # 返回高亮后的文本
                highlighted = self.highlighter.highlight(line)
                return [(highlighted, '')]
            return get_line
    
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False
    PromptToolkitLexer = None


# 命令行高亮测试
if __name__ == '__main__':
    h = LightHighlighter()
    
    test_cases = [
        "# 这是注释",
        '"字符串"',
        "12345",
        "设 甲 为 3。",
        "打印(甲)。",
    ]
    
    print("=== 语法高亮测试 ===\n")
    for case in test_cases:
        print(f"原文: {case}")
        print(f"高亮: {h.highlight(case)}")
        print()