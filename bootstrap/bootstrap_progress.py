# -*- coding: utf-8 -*-
"""
段言（Duan）编程语言 - 自举编译器进度检查工具

评估 bootstrap_level4.duan 和 bootstrap_level5.duan 中每个层级的功能完成度，
生成进度报告，列出尚未自举的功能。

用法：
    from bootstrap_progress import BootstrapProgressChecker
    checker = BootstrapProgressChecker()
    report = checker.generate_report()
    print(report)
"""

import os
import re
from typing import Dict, List, Set, Tuple, Optional


class BootstrapProgressChecker:
    """自举编译器进度检查器

    分析 bootstrap_level4.duan 和 bootstrap_level5.duan 的源代码，
    评估每个层级的功能完成度，并生成进度报告。
    """

    # 功能检查清单：每个层级预期包含的功能
    LEVEL_CHECKLIST: Dict[int, Dict[str, List[str]]] = {
        1: {
            "数字字面量": ["数字", "NUM"],
            "字符串字面量": ["字符串", "STR"],
            "布尔值": ["真", "假"],
            "变量引用": ["ID"],
            "二元运算": ["加", "减", "乘", "除", "取模"],
            "括号分组": ["LPAREN", "RPAREN"],
        },
        2: {
            "if语句": ["如果"],
            "if-else语句": ["否则"],
            "比较运算": ["等于", "小于", "大于", "小于等于", "大于等于", "不等于"],
            "逻辑运算": ["且", "或", "非"],
        },
        3: {
            "函数定义": ["段落", "段"],
            "函数调用": ["LPAREN"],
            "参数传递": ["接收"],
            "return语句": ["返回"],
            "while循环": ["当"],
            "变量赋值": ["设", "为"],
        },
        4: {
            "列表字面量": ["列表创建"],
            "字典字面量": ["字典创建"],
            "索引访问": ["列表获取", "字典获取"],
            "模块导入/导出": ["导入", "导出"],
            "for循环": ["遍历", "在"],
            "类定义": ["类"],
            "属性访问": ["DOT", "属性"],
            "方法定义": ["己"],
            "继承": ["父", "继承"],
        },
        5: {
            "try/except/finally": ["尝试", "捕获", "最终"],
            "raise语句": ["抛出"],
            "class定义": ["类"],
            "装饰器": ["装饰器"],
            "类型标注": ["类型"],
            "match/case": ["匹配", "情形"],
            "async/await": ["异步", "等待"],
            "with语句": ["使用"],
        },
    }

    # 中文关键字到 Python 关键字的映射，用于检测已实现的功能
    KEYWORD_MAP: Dict[str, str] = {
        "设": "=",
        "如果": "if",
        "否则": "else",
        "当": "while",
        "遍历": "for",
        "在": "in",
        "返回": "return",
        "段落": "def",
        "段": "def",
        "类": "class",
        "尝试": "try",
        "捕获": "except",
        "最终": "finally",
        "抛出": "raise",
        "导入": "import",
        "导出": "export",
        "真": "True",
        "假": "False",
        "加": "+",
        "减": "-",
        "乘": "*",
        "除": "//",
        "取模": "%",
        "等于": "==",
        "小于": "<",
        "大于": ">",
        "小于等于": "<=",
        "大于等于": ">=",
        "不等于": "!=",
        "且": "and",
        "或": "or",
        "非": "not",
        "己": "self",
        "父": "super",
        "属性": "attribute",
        "接收": "接收",
        "结束": "结束",
        "为": "=",
        "匹配": "match",
        "情形": "case",
        "异步": "async",
        "等待": "await",
        "使用": "with",
        "装饰器": "decorator",
        "类型": "type",
        "继承": "继承",
    }

    def __init__(self, bootstrap_dir: Optional[str] = None) -> None:
        """初始化进度检查器

        Args:
            bootstrap_dir: 自举编译器目录，默认为本文件所在目录
        """
        if bootstrap_dir is None:
            bootstrap_dir = os.path.dirname(os.path.abspath(__file__))
        self.bootstrap_dir = bootstrap_dir
        self.level4_source: str = ""
        self.level5_source: str = ""
        self._load_sources()

    def _load_sources(self) -> None:
        """加载自举编译器源码"""
        level4_path = os.path.join(self.bootstrap_dir, "bootstrap_level4.duan")
        level5_path = os.path.join(self.bootstrap_dir, "bootstrap_level5.duan")

        if os.path.exists(level4_path):
            with open(level4_path, "r", encoding="utf-8") as f:
                self.level4_source = f.read()
        if os.path.exists(level5_path):
            with open(level5_path, "r", encoding="utf-8") as f:
                self.level5_source = f.read()

    def check_progress(self) -> Dict[str, Dict[str, bool]]:
        """检查每个层级的功能完成度

        Returns:
            嵌套字典，结构为 {level: {feature: completed}}
        """
        combined_source = self.level4_source + "\n" + self.level5_source
        result: Dict[str, Dict[str, bool]] = {}

        for level, features in self.LEVEL_CHECKLIST.items():
            level_key = f"Level {level}"
            result[level_key] = {}
            for feature_name, keywords in features.items():
                completed = self._check_feature(combined_source, keywords, level)
                result[level_key][feature_name] = completed

        return result

    def _check_feature(self, source: str, keywords: List[str], level: int) -> bool:
        """检查单个功能是否已实现

        Args:
            source: 自举编译器源码
            keywords: 该功能对应的关键字列表
            level: 层级编号

        Returns:
            该功能是否已完成
        """
        if level <= 4:
            check_source = self.level4_source
        else:
            check_source = self.level5_source

        # Level 5 的功能需要同时在 level5 中检查，有些可能也在 level4 中
        # 特殊处理：level5 包含 level4 的全部功能
        if level == 5:
            check_source = self.level5_source

        # 检查是否所有关键字都在源码中出现
        found = 0
        for kw in keywords:
            if kw in check_source:
                found += 1

        # 如果关键字在源码的函数定义或注释中出现，认为已实现
        # 对于有多个关键字的特征，至少需要 50% 的关键字出现
        threshold = max(1, len(keywords) // 2)
        return found >= threshold

    def _get_level_source(self, level: int) -> str:
        """获取指定层级的源码

        Args:
            level: 层级编号 (1-5)

        Returns:
            该层级的源码字符串
        """
        if level <= 4:
            return self.level4_source
        return self.level5_source

    def get_remaining_features(self) -> List[str]:
        """列出尚未自举的功能

        Returns:
            未完成的功能描述列表
        """
        progress = self.check_progress()
        remaining: List[str] = []

        for level_key, features in progress.items():
            incomplete = [name for name, done in features.items() if not done]
            for feature in incomplete:
                remaining.append(f"{level_key}: {feature}")

        return remaining

    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息

        Returns:
            包含总功能数、已完成数、未完成数等统计信息
        """
        progress = self.check_progress()
        total = 0
        completed = 0

        for features in progress.values():
            for done in features.values():
                total += 1
                if done:
                    completed += 1

        return {
            "total_features": total,
            "completed": completed,
            "remaining": total - completed,
            "completion_percentage": round(completed / total * 100, 1) if total > 0 else 0,
        }

    def generate_report(self) -> str:
        """生成进度报告

        Returns:
            格式化的进度报告字符串
        """
        progress = self.check_progress()
        stats = self.get_statistics()
        remaining = self.get_remaining_features()

        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("  段言（Duan）自举编译器进度报告")
        lines.append("=" * 60)
        lines.append("")

        # 总体进度
        lines.append(f"  总体进度: {stats['completed']}/{stats['total_features']} "
                      f"({stats['completion_percentage']}%)")
        bar_len = 40
        filled = int(bar_len * stats['completion_percentage'] / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"  [{bar}]")
        lines.append("")

        # 各层级详情
        for level_key in sorted(progress.keys(), key=lambda x: int(x.split()[-1])):
            features = progress[level_key]
            level_num = int(level_key.split()[-1])
            completed = sum(1 for v in features.values() if v)
            total = len(features)
            pct = round(completed / total * 100, 1) if total > 0 else 0

            level_name = {
                1: "基础表达式",
                2: "条件判断",
                3: "函数与循环",
                4: "列表、字典、模块、类",
                5: "异常处理、高级特性",
            }.get(level_num, level_key)

            lines.append(f"  {level_key} - {level_name}")
            lines.append(f"  {'─' * 50}")
            lines.append(f"    完成度: {completed}/{total} ({pct}%)")

            for feature_name, done in features.items():
                icon = "✅" if done else "❌"
                lines.append(f"    {icon} {feature_name}")

            lines.append("")

        # 尚未自举的功能
        if remaining:
            lines.append(f"  尚未自举的功能 ({len(remaining)}):")
            lines.append(f"  {'─' * 50}")
            for item in remaining:
                lines.append(f"    ❌ {item}")
            lines.append("")

        # 源码统计
        lines.append("  源码统计:")
        lines.append(f"  {'─' * 50}")
        lines.append(f"    Level 4 源码行数: {len(self.level4_source.splitlines())}")
        lines.append(f"    Level 5 源码行数: {len(self.level5_source.splitlines())}")
        lines.append(f"    Level 4 函数数量: {self.level4_source.count('段落 ')}")
        lines.append(f"    Level 5 函数数量: {self.level5_source.count('段落 ')}")
        lines.append("")

        # 时间戳
        from datetime import datetime
        lines.append(f"  报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)

        return "\n".join(lines)


def main() -> None:
    """主函数：运行进度检查并输出报告"""
    checker = BootstrapProgressChecker()
    report = checker.generate_report()
    print(report)


if __name__ == "__main__":
    main()