"""
段言（Duan）编程语言 - 口语化中文语法兼容层（弹性语法适配）

实现自然语言弹性语法适配，允许用户用更贴近日常中文表达的写法编写代码，
编译器自动完成语义适配，将口语化表达映射为标准段言关键字。

设计原则：
- 非侵入式：仅做文本级替换，不影响后续词法/语法分析流程
- 可扩展：弹性语法映射表可随时增补
- 安全替换：避免部分匹配导致误替换
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple, Optional


# =============================================================================
# 弹性语法映射表
# =============================================================================

# 口语化表达 → 标准段言关键字映射
# 映射规则：
# 1. 多字词优先匹配（如"如果...的话"优先于"如果"）
# 2. 替换后保持语义等价
# 3. 列表顺序决定匹配优先级（靠前的优先）
ELASTIC_SYNTAX_MAP: List[Tuple[str, str]] = [
    # ========== 条件判断 ==========
    ("如果...的话", "如果..."),       # 如果分数大于等于90的话 → 如果分数大于等于90
    ("要是", "如果"),                  # 要是 → 如果
    ("假如", "如果"),                  # 假如 → 如果
    ("假设", "如果"),                  # 假设 → 如果

    # ========== 循环 ==========
    ("每当", "当"),                    # 每当 → 当
    ("循环遍历", "遍历"),              # 循环遍历 → 遍历
    ("对于", "遍历"),                  # 对于 → 遍历
    ("逐项遍历", "遍历"),              # 逐项遍历 → 遍历
    ("从...到...遍历", "遍历 从 到"),  # 从1到10遍历 → 遍历 从 1 到 10

    # ========== 赋值 ==========
    ("把", "设"),                      # 把 甲 设 为 5 → 设 甲 为 5
    ("令", "设"),                      # 令 → 设
    ("让", "设"),                      # 让 → 设
    ("将", "设"),                      # 将 → 设

    # ========== 函数定义 ==========
    ("定义函数", "段落"),              # 定义函数 → 段落
    ("定义段落", "段落"),              # 定义段落 → 段落
    ("方法", "段落"),                  # 方法 → 段落
    ("过程", "段落"),                  # 过程 → 段落

    # ========== 返回 ==========
    ("返回结果", "返回"),              # 返回结果 → 返回
    ("输出结果", "返回"),              # 输出结果 → 返回
    ("给出", "返回"),                  # 给出 → 返回

    # ========== 比较 ==========
    ("等于", "等于"),                  # 等于（保持不变）
    ("不等于", "不等于"),              # 不等于（保持不变）
    ("大于", "大于"),                  # 大于（保持不变）
    ("小于", "小于"),                  # 小于（保持不变）
    ("大于等于", "大于等于"),          # 大于等于（保持不变）
    ("小于等于", "小于等于"),          # 小于等于（保持不变）
    ("不小于", "不小于"),              # 不小于（保持不变）
    ("不大于", "不大于"),              # 不大于（保持不变）

    # ========== 异常 ==========
    ("尝试运行", "尝试"),              # 尝试运行 → 尝试
    ("捕捉错误", "捕获"),              # 捕捉错误 → 捕获
    ("错误处理", "捕获"),              # 错误处理 → 捕获
    ("最终处理", "最终"),              # 最终处理 → 最终

    # ========== 类 ==========
    ("定义一个类", "类"),              # 定义一个类 → 类
    ("创建类", "类"),                  # 创建类 → 类

    # ========== 逻辑 ==========
    ("并且", "且"),                    # 并且 → 且
    ("或者", "或"),                    # 或者 → 或
    ("不是", "非"),                    # 不是 → 非
    ("不", "非"),                      # 不 → 非（注意：严格模式下行首"不"才替换）
]

# 句末"的话"后缀模式
# 如"如果分数大于等于90的话" → "如果分数大于等于90"
IF_SUFFIX_PATTERN = re.compile(r'的话\s*$')


# =============================================================================
# 弹性语法预处理器
# =============================================================================

class ElasticSyntaxPreprocessor:
    """口语化中文语法预处理器

    将段言源代码中的口语化表达自动替换为标准段言关键字，
    使编译器能够理解更贴近自然中文的代码写法。

    使用示例：
        >>> preprocessor = ElasticSyntaxPreprocessor()
        >>> result = preprocessor.preprocess("要是 分数 大于等于 90 的话")
        >>> print(result)
        "如果 分数 大于等于 90"
    """

    # 弹性语法映射表（按词长度降序排列，确保长词优先匹配）
    _sorted_map: List[Tuple[str, str]] = sorted(
        ELASTIC_SYNTAX_MAP,
        key=lambda x: len(x[0]),
        reverse=True
    )

    def preprocess(self, source: str) -> str:
        """预处理源代码，将口语化表达替换为标准段言语法

        Args:
            source: 原始段言源代码字符串

        Returns:
            经过弹性语法替换后的标准段言代码
        """
        if not source:
            return ""

        text = source
        text = self._handle_if_pattern(text)
        text = self._handle_if_suffix(text)
        text = self._apply_elastic_map(text)
        text = self._normalize_whitespace(text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符

        将连续的空白字符（空格、制表符等）统一为单个空格，
        去除行首尾空白，保留空行结构。

        Args:
            text: 待处理的文本

        Returns:
            空白规范化后的文本
        """
        lines = text.split('\n')
        normalized_lines: List[str] = []
        for line in lines:
            # 去除行首尾空白
            line = line.strip()
            # 将连续的空白字符替换为单个空格
            line = re.sub(r'\s+', ' ', line)
            normalized_lines.append(line)
        return '\n'.join(normalized_lines)

    def _handle_if_suffix(self, text: str) -> str:
        """处理句末的"的话"后缀

        将"如果...的话"模式中的"的话"去掉，因为段言中"如果"已包含条件语义。

        Args:
            text: 待处理的文本

        Returns:
            去掉"的话"后缀后的文本
        """
        lines = text.split('\n')
        processed_lines: List[str] = []
        for line in lines:
            # 每行独立处理"的话"后缀
            line = IF_SUFFIX_PATTERN.sub('', line)
            processed_lines.append(line)
        return '\n'.join(processed_lines)

    def _handle_if_pattern(self, text: str) -> str:
        """处理"如果...的话"中间省略模式

        将含有"如果"但没有直接跟"的话"在行尾的情况，
        如果行中存在"如果"且行尾是"的话"，则移除"的话"。

        Args:
            text: 待处理的文本

        Returns:
            处理后的文本
        """
        lines = text.split('\n')
        processed_lines: List[str] = []
        for line in lines:
            if '如果' in line:
                line = IF_SUFFIX_PATTERN.sub('', line)
            processed_lines.append(line)
        return '\n'.join(processed_lines)

    def _apply_elastic_map(self, text: str) -> str:
        """应用弹性语法映射表

        将文本中的口语化表达按映射表替换为标准段言关键字。
        使用词边界匹配，避免部分匹配（如"定义函数"不会匹配"定义函数指针"中的"函数"）。

        Args:
            text: 待处理的文本

        Returns:
            替换后的文本
        """
        result = text

        # 先处理带"..."通配符的模式（如"如果...的话"）
        for spoken, standard in self._sorted_map:
            if '...' in spoken:
                # 将"..."替换为正则通配符
                pattern_str = re.escape(spoken).replace(r'\.\.\.', r'(.+?)')
                pattern = re.compile(pattern_str)
                # 替换为对应的标准形式，保留捕获组内容
                standard_template = re.sub(r'\.\.\.', r'\\1', standard)
                result = pattern.sub(standard_template, result)
            else:
                # 普通词替换：使用词边界匹配
                pattern = re.compile(r'\b' + re.escape(spoken) + r'\b')
                result = pattern.sub(standard, result)

        return result

    def get_elastic_map(self) -> Dict[str, str]:
        """获取弹性语法映射表（字典形式）

        Returns:
            口语化表达到标准关键字的映射字典
        """
        return dict(ELASTIC_SYNTAX_MAP)

    def add_elastic_rule(self, spoken: str, standard: str) -> None:
        """动态添加弹性语法规则

        Args:
            spoken: 口语化表达
            standard: 对应的标准段言关键字
        """
        # 重新排序映射表
        self._sorted_map.append((spoken, standard))
        self._sorted_map.sort(key=lambda x: len(x[0]), reverse=True)

    def remove_elastic_rule(self, spoken: str) -> bool:
        """移除弹性语法规则

        Args:
            spoken: 要移除的口语化表达

        Returns:
            是否成功移除
        """
        for i, (s, _) in enumerate(self._sorted_map):
            if s == spoken:
                self._sorted_map.pop(i)
                return True
        return False

    def clear_elastic_rules(self) -> None:
        """清空所有弹性语法规则"""
        self._sorted_map.clear()

    def reset_elastic_rules(self) -> None:
        """重置弹性语法规则为默认映射表"""
        self._sorted_map = sorted(
            ELASTIC_SYNTAX_MAP,
            key=lambda x: len(x[0]),
            reverse=True
        )


# =============================================================================
# 便捷函数
# =============================================================================

_default_preprocessor: Optional[ElasticSyntaxPreprocessor] = None


def get_default_preprocessor() -> ElasticSyntaxPreprocessor:
    """获取全局默认预处理器实例

    Returns:
        默认的 ElasticSyntaxPreprocessor 实例
    """
    global _default_preprocessor
    if _default_preprocessor is None:
        _default_preprocessor = ElasticSyntaxPreprocessor()
    return _default_preprocessor


def preprocess(source: str) -> str:
    """便捷函数：预处理源代码

    使用全局默认预处理器对源代码进行弹性语法转换。

    Args:
        source: 原始段言源代码字符串

    Returns:
        经过弹性语法替换后的标准段言代码

    示例：
        >>> preprocess("要是 分数 大于等于 90 的话")
        "如果 分数 大于等于 90"
    """
    return get_default_preprocessor().preprocess(source)