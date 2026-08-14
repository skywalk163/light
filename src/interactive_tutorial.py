#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段言（DuanLang）交互式教程引擎

提供逐步引导的编程练习，每个步骤包含：
- 知识点讲解
- 编程任务
- 代码验证
- 进度追踪

支持多教程选择、分类练习、进度追踪和断点续学。
"""

import sys
import os
import json
import re
import argparse
from typing import List, Dict, Optional, Callable, Any, Tuple

# 颜色支持
try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init(autoreset=True)
    C = {
        'title': Fore.CYAN + Style.BRIGHT,
        'section': Fore.YELLOW + Style.BRIGHT,
        'code': Fore.GREEN,
        'output': Fore.WHITE,
        'tip': Fore.MAGENTA,
        'prompt': Fore.CYAN,
        'success': Fore.GREEN + Style.BRIGHT,
        'error': Fore.RED + Style.BRIGHT,
        'highlight': Fore.YELLOW,
        'dim': Fore.LIGHTBLACK_EX,
        'reset': Style.RESET_ALL,
        'box': Fore.CYAN,
        'label': Fore.BLUE + Style.BRIGHT,
        'demo': Fore.GREEN,
        'star': Fore.YELLOW + Style.BRIGHT,
        'info': Fore.BLUE,
        'category': Fore.GREEN + Style.BRIGHT,
    }
except ImportError:
    C = {k: '' for k in ['title', 'section', 'code', 'output', 'tip', 'prompt',
                          'success', 'error', 'highlight', 'dim', 'reset',
                          'box', 'label', 'demo', 'star', 'info', 'category']}


# =============================================================================
# 教程步骤定义
# =============================================================================

class TutorialStep:
    """单个教程步骤"""

    def __init__(
        self,
        step_id: int,
        title: str,
        explanation: str,
        task: str,
        hint: str,
        demo_code: str,
        category: str = "basic",
        validator: Optional[Callable[[str, Dict], bool]] = None,
        expected_output: Optional[str] = None,
        expected_lines: Optional[List[str]] = None,
    ):
        self.step_id = step_id
        self.title = title
        self.explanation = explanation
        self.task = task
        self.hint = hint
        self.demo_code = demo_code
        self.category = category  # 'basic', 'intermediate', 'advanced'
        self.validator = validator
        self.expected_output = expected_output
        self.expected_lines = expected_lines

    def validate(self, output: str, namespace: Dict) -> Tuple[bool, str]:
        """验证用户代码输出是否正确

        Returns:
            (是否通过, 反馈消息)
        """
        if self.validator:
            return self.validator(output, namespace)

        if self.expected_output is not None:
            if output.strip() == self.expected_output.strip():
                return True, "输出完全正确！"
            return False, f"期望输出: {self.expected_output!r}"

        if self.expected_lines is not None:
            output_lines = [l.strip() for l in output.strip().split('\n')]
            for expected in self.expected_lines:
                if expected.strip() not in output_lines:
                    return False, f"未找到期望的输出行: {expected}"
            return True, "所有期望输出行都已找到！"

        # 默认：只要没有错误就通过
        return True, "执行成功！"


# =============================================================================
# 教程定义
# =============================================================================

class TutorialDefinition:
    """一个完整的教程定义"""

    def __init__(self, tutorial_id: str, name: str, description: str,
                 category: str, steps: List[TutorialStep],
                 prerequisites: str = "无"):
        self.tutorial_id = tutorial_id
        self.name = name
        self.description = description
        self.category = category  # 'beginner', 'intermediate', 'advanced'
        self.steps = steps
        self.prerequisites = prerequisites

    @property
    def total_steps(self) -> int:
        return len(self.steps)


# =============================================================================
# 所有教程定义
# =============================================================================

def create_all_tutorials() -> Dict[str, TutorialDefinition]:
    """创建所有可用的教程"""

    # ─── 基础入门教程（5步） ─────────────────────────────────
    beginner_steps = [
        TutorialStep(
            step_id=0,
            title="Hello World",
            category="basic",
            explanation=(
                "段言（DuanLang）是一门用中文自然语言编程的语言。\n"
                "让我们从经典的 Hello World 开始！\n\n"
                "在段言中，使用「打印」来输出内容到屏幕，\n"
                "字符串用双引号包裹。"
            ),
            task='请输出 "你好，世界！"',
            hint='打印 "你好，世界！"',
            demo_code='打印 "你好，世界！"',
            expected_output="你好，世界！",
        ),
        TutorialStep(
            step_id=1,
            title="变量与赋值",
            category="basic",
            explanation=(
                "在段言中，使用「设」关键字来声明变量。\n\n"
                "语法：设 变量名 为 值\n\n"
                "变量名可以用中文，赋值后即可使用。\n"
                "让我们创建一个变量并打印它。"
            ),
            task='创建一个变量「甲」赋值为 5，然后打印它',
            hint='设 甲 为 5\n打印(甲)',
            demo_code='设 甲 为 5\n打印(甲)',
            expected_output="5",
        ),
        TutorialStep(
            step_id=2,
            title="定义函数（段落）",
            category="basic",
            explanation=(
                "在段言中，函数叫做「段落」。\n\n"
                "语法：段落 函数名 接收 参数1, 参数2：\n"
                "    返回 表达式\n\n"
                "用「段落」关键字定义，用「接收」列出参数，\n"
                "用「返回」返回结果。\n\n"
                "让我们定义一个加法函数。"
            ),
            task='定义一个名为「加法」的段落，接收两个参数 甲, 乙，返回它们的和，然后调用它',
            hint='段落 加法 接收 甲, 乙：\n    返回 甲 + 乙\n\n打印(加法(3, 5))',
            demo_code='段落 加法 接收 甲, 乙：\n    返回 甲 + 乙\n\n打印(加法(3, 5))',
            expected_output="8",
        ),
        TutorialStep(
            step_id=3,
            title="循环遍历",
            category="basic",
            explanation=(
                "段言使用「遍历」关键字进行循环。\n\n"
                "语法：遍历 变量 在 范围(结束值)：\n"
                "    循环体\n\n"
                "「范围(n)」生成从 0 到 n-1 的数字序列。\n"
                "让我们遍历 0 到 4 并打印每个数字。"
            ),
            task='使用「遍历」循环打印 0 到 4 的每个数字',
            hint='遍历 甲 在 范围(5)：\n    打印(甲)',
            demo_code='遍历 甲 在 范围(5)：\n    打印(甲)',
            expected_lines=['0', '1', '2', '3', '4'],
        ),
        TutorialStep(
            step_id=4,
            title="获取帮助",
            category="basic",
            explanation=(
                "恭喜你完成了基础练习！🎉\n\n"
                "段言提供了丰富的命令行帮助：\n"
                "  • duan --help      — 查看所有命令\n"
                "  • duan repl        — 进入交互式编程环境\n"
                "  • duan tutorial    — 完整教程\n\n"
                "在 REPL 中，输入 :help 或 :帮助 查看内置命令。\n\n"
                "这个练习很简单——只需输入任意代码（或直接回车跳过）。"
            ),
            task='（可选）输入任意段言代码，或直接回车完成教程',
            hint='打印 "段言，你好！"',
            demo_code='打印 "段言，你好！"',
            expected_output=None,  # 任何输出都通过
        ),
    ]

    # ─── 进阶练习（5步） ─────────────────────────────────
    intermediate_steps = [
        TutorialStep(
            step_id=0,
            title="条件判断",
            category="intermediate",
            explanation=(
                "段言使用「如果/否则如果/否则」进行条件判断。\n\n"
                "语法：\n"
                "  如果 条件：\n"
                "      代码块\n"
                "  否则如果 条件：\n"
                "      代码块\n"
                "  否则：\n"
                "      代码块\n\n"
                "条件判断是程序做决策的基础。"
            ),
            task='设变量 分数 为 85，如果分数 >= 90 打印"优秀"，否则如果 >= 60 打印"及格"，否则打印"不及格"',
            hint='设 分数 为 85\n如果 分数 >= 90：\n    打印 "优秀"\n否则如果 分数 >= 60：\n    打印 "及格"\n否则：\n    打印 "不及格"',
            demo_code='设 分数 为 85\n如果 分数 >= 90：\n    打印 "优秀"\n否则如果 分数 >= 60：\n    打印 "及格"\n否则：\n    打印 "不及格"',
            expected_output="及格",
        ),
        TutorialStep(
            step_id=1,
            title="列表操作",
            category="intermediate",
            explanation=(
                "列表是段言中存储多个数据的基本结构。\n\n"
                "创建列表：设 列表 为 [元素1, 元素2, ...]\n"
                "访问元素：列表[索引]（索引从 0 开始）\n"
                "追加元素：列表.追加(新元素)\n"
                "获取长度：长度(列表)\n\n"
                "创建一个水果列表，追加一个水果，然后打印整个列表。"
            ),
            task='创建一个名为「水果」的列表，包含"苹果"和"香蕉"，然后追加"橘子"，最后打印列表',
            hint='设 水果 为 ["苹果", "香蕉"]\n水果.追加("橘子")\n打印(水果)',
            demo_code='设 水果 为 ["苹果", "香蕉"]\n水果.追加("橘子")\n打印(水果)',
            expected_output="['苹果', '香蕉', '橘子']",
        ),
        TutorialStep(
            step_id=2,
            title="字典操作",
            category="intermediate",
            explanation=(
                "字典用键值对存储数据，类似于查字典。\n\n"
                "创建：设 字典 为 {键: 值, 键: 值}\n"
                "访问：字典[键]\n"
                "修改：字典[键] = 新值\n\n"
                "创建一个学生字典，包含姓名、年龄和成绩。"
            ),
            task='创建一个字典「学生」，包含姓名"张三"、年龄18、成绩95，然后打印姓名',
            hint='设 学生 为 {"姓名": "张三", "年龄": 18, "成绩": 95}\n打印(学生["姓名"])',
            demo_code='设 学生 为 {"姓名": "张三", "年龄": 18, "成绩": 95}\n打印(学生["姓名"])',
            expected_output="张三",
        ),
        TutorialStep(
            step_id=3,
            title="字符串操作",
            category="intermediate",
            explanation=(
                "段言支持丰富的字符串操作。\n\n"
                "拼接：字符串1 + 字符串2\n"
                "长度：长度(字符串)\n"
                "格式化：f\"{变量}\"（f-string）\n"
                "替换：字符串.替换(旧, 新)\n\n"
                "尝试使用 f-string 格式化输出。"
            ),
            task='设变量 名字 为"段言"，版本 为 6，使用 f-string 输出"语言：段言，版本：6"',
            hint='设 名字 为 "段言"\n设 版本 为 6\n打印(f"语言：{名字}，版本：{版本}")',
            demo_code='设 名字 为 "段言"\n设 版本 为 6\n打印(f"语言：{名字}，版本：{版本}")',
            expected_output="语言：段言，版本：6",
        ),
        TutorialStep(
            step_id=4,
            title="列表推导式",
            category="intermediate",
            explanation=(
                "列表推导式用一行代码生成列表，非常简洁。\n\n"
                "语法：[表达式 遍历 变量 之 范围]\n"
                "例如：[x * x 遍历 x 之 范围(1, 6)] 生成 [1, 4, 9, 16, 25]\n\n"
                "试一下这个示例！"
            ),
            task='使用列表推导式生成 1 到 5 的平方数列表，并打印',
            hint='设 平方数 为 [x * x 遍历 x 之 范围(1, 6)]\n打印(平方数)',
            demo_code='设 平方数 为 [x * x 遍历 x 之 范围(1, 6)]\n打印(平方数)',
            expected_output="[1, 4, 9, 16, 25]",
        ),
    ]

    # ─── 高级练习（5步） ─────────────────────────────────
    advanced_steps = [
        TutorialStep(
            step_id=0,
            title="类和对象",
            category="advanced",
            explanation=(
                "段言支持面向对象编程。\n\n"
                "定义类：\n"
                "  类 类名：\n"
                "      属性 属性1, 属性2\n"
                "      构造 接收 参数1, 参数2：\n"
                "          己.属性1 为 参数1\n\n"
                "「己」相当于其他语言的 this 或 self。\n"
                "定义一个简单的「狗」类。"
            ),
            task='定义一个「狗」类，有属性「名字」，构造方法接收名字，有方法「叫」打印"汪汪！"。创建对象并调用叫方法。',
            hint='类 狗：\n    属性 名字\n    构造 接收 名字：\n        己.名字 为 名字\n    段落 叫 接收：\n        打印 "汪汪！"\n\n设 我的狗 为 狗("旺财")\n我的狗.叫()',
            demo_code='类 狗：\n    属性 名字\n    构造 接收 名字：\n        己.名字 为 名字\n    段落 叫 接收：\n        打印 "汪汪！"\n\n设 我的狗 为 狗("旺财")\n我的狗.叫()',
            expected_output="汪汪！",
        ),
        TutorialStep(
            step_id=1,
            title="继承",
            category="advanced",
            explanation=(
                "继承让一个类自动获得另一个类的属性和方法。\n\n"
                "语法：类 子类 继承 父类：\n\n"
                "子类可以重写（覆盖）父类的方法，\n"
                "也可以调用父类的方法。\n\n"
                "定义一个动物类和继承它的猫类。"
            ),
            task='定义一个「动物」类（有名字属性和介绍方法），然后定义「猫」类继承动物，重写介绍方法输出"喵喵"',
            hint='类 动物：\n    属性 名字\n    构造 接收 名字：\n        己.名字 为 名字\n    段落 介绍 接收：\n        打印 "我是动物"\n\n类 猫 继承 动物：\n    段落 介绍 接收：\n        打印 己.名字 + "：喵喵~"\n\n设 猫猫 为 猫("小花")\n猫猫.介绍()',
            demo_code='类 动物：\n    属性 名字\n    构造 接收 名字：\n        己.名字 为 名字\n    段落 介绍 接收：\n        打印 "我是动物"\n\n类 猫 继承 动物：\n    段落 介绍 接收：\n        打印 己.名字 + "：喵喵~"\n\n设 猫猫 为 猫("小花")\n猫猫.介绍()',
            expected_output="小花：喵喵~",
        ),
        TutorialStep(
            step_id=2,
            title="异常处理",
            category="advanced",
            explanation=(
                "异常处理让程序在出错时不会崩溃。\n\n"
                "语法：\n"
                "  尝试：\n"
                "      可能出错的代码\n"
                "  捕获 错误：\n"
                "      出错时执行的代码\n"
                "  最终：\n"
                "      无论是否出错都会执行的代码\n\n"
                "尝试捕获一个除零错误。"
            ),
            task='使用尝试/捕获处理 10/0 的除零错误，打印友好的错误信息',
            hint='尝试：\n    设 结果 为 10 / 0\n    打印 结果\n捕获 错误：\n    打印 "除数不能为零！"\n最终：\n    打印 "程序执行完毕"',
            demo_code='尝试：\n    设 结果 为 10 / 0\n    打印 结果\n捕获 错误：\n    打印 "除数不能为零！"\n最终：\n    打印 "程序执行完毕"',
            expected_lines=["除数不能为零！", "程序执行完毕"],
        ),
        TutorialStep(
            step_id=3,
            title="模块导入",
            category="advanced",
            explanation=(
                "段言支持模块化编程。\n\n"
                "导入语法：\n"
                "  导入 模块名\n"
                "  从 模块名 导入 函数1, 函数2\n\n"
                "段言内置了数学、JSON、文件系统等标准库模块。\n"
                "导入数学模块并使用平方根函数。"
            ),
            task='从「数学」模块导入「平方根」函数，计算 16 的平方根并打印',
            hint='从 数学 导入 平方根\n设 结果 为 平方根(16)\n打印(结果)',
            demo_code='从 数学 导入 平方根\n设 结果 为 平方根(16)\n打印(结果)',
            expected_output="4.0",
        ),
        TutorialStep(
            step_id=4,
            title="综合应用：斐波那契",
            category="advanced",
            explanation=(
                "综合运用所学知识！\n\n"
                "斐波那契数列：每个数等于前两个数之和。\n"
                "1, 1, 2, 3, 5, 8, 13, 21, ...\n\n"
                "用递归函数实现斐波那契数列计算。\n"
                "递归函数需要有一个终止条件。"
            ),
            task='定义递归函数「斐波那契」接收 n，当 n<=2 返回 1，否则返回 斐波那契(n-1) + 斐波那契(n-2)，然后计算并打印第 6 项',
            hint='段落 斐波那契 接收 n：\n    如果 n <= 2：\n        返回 1\n    返回 斐波那契(n - 1) + 斐波那契(n - 2)\n\n打印(斐波那契(6))',
            demo_code='段落 斐波那契 接收 n：\n    如果 n <= 2：\n        返回 1\n    返回 斐波那契(n - 1) + 斐波那契(n - 2)\n\n打印(斐波那契(6))',
            expected_output="8",
        ),
    ]

    # 组装成教程定义
    return {
        "beginner": TutorialDefinition(
            tutorial_id="beginner",
            name="基础入门",
            description="从零开始学习段言基础语法，适合编程初学者。",
            category="beginner",
            steps=beginner_steps,
            prerequisites="无",
        ),
        "intermediate": TutorialDefinition(
            tutorial_id="intermediate",
            name="进阶练习",
            description="掌握条件判断、列表、字典、字符串等核心数据结构。",
            category="intermediate",
            steps=intermediate_steps,
            prerequisites="基础入门 或 有基础编程知识",
        ),
        "advanced": TutorialDefinition(
            tutorial_id="advanced",
            name="高级编程",
            description="学习类、继承、异常处理、模块导入等高级特性。",
            category="advanced",
            steps=advanced_steps,
            prerequisites="进阶练习",
        ),
    }


# =============================================================================
# 教程引擎
# =============================================================================

class TutorialEngine:
    """交互式教程引擎"""

    PROGRESS_DIR = os.path.join(os.path.expanduser("~"), ".light")
    PROGRESS_FILE = os.path.join(PROGRESS_DIR, "tutorial_progress.json")

    def __init__(self, tutorial: TutorialDefinition):
        self.tutorial = tutorial
        self.current_step = 0
        self.completed: set = set()
        self.namespace: Dict = {}
        self._load_progress()

    # ------------------------------------------------------------------
    # 进度管理
    # ------------------------------------------------------------------

    def _progress_path(self) -> str:
        os.makedirs(os.path.dirname(self.PROGRESS_FILE), exist_ok=True)
        return self.PROGRESS_FILE

    def _load_progress(self):
        """从文件加载进度"""
        try:
            if os.path.exists(self.PROGRESS_FILE):
                with open(self.PROGRESS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                tutorial_data = data.get(self.tutorial.tutorial_id, {})
                self.current_step = tutorial_data.get('current', 0)
                self.completed = set(tutorial_data.get('completed', []))
        except Exception:
            pass

    def _save_progress(self):
        """保存进度到文件"""
        try:
            # 先读取现有数据
            all_progress = {}
            if os.path.exists(self.PROGRESS_FILE):
                try:
                    with open(self.PROGRESS_FILE, 'r', encoding='utf-8') as f:
                        all_progress = json.load(f)
                except Exception:
                    pass

            # 更新当前教程进度
            all_progress[self.tutorial.tutorial_id] = {
                'current': self.current_step,
                'completed': list(self.completed),
                'name': self.tutorial.name,
            }

            with open(self._progress_path(), 'w', encoding='utf-8') as f:
                json.dump(all_progress, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def clear_progress(self):
        """清除当前教程的进度"""
        self.current_step = 0
        self.completed = set()
        self.namespace = {}
        try:
            all_progress = {}
            if os.path.exists(self.PROGRESS_FILE):
                with open(self.PROGRESS_FILE, 'r', encoding='utf-8') as f:
                    all_progress = json.load(f)
            if self.tutorial.tutorial_id in all_progress:
                del all_progress[self.tutorial.tutorial_id]
                with open(self.PROGRESS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(all_progress, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @property
    def total_steps(self) -> int:
        return len(self.tutorial.steps)

    @property
    def progress_text(self) -> str:
        return f"{len(self.completed)}/{self.total_steps}"

    @property
    def is_all_completed(self) -> bool:
        return len(self.completed) >= self.total_steps

    @property
    def category_counts(self) -> Dict[str, int]:
        """统计各类别练习的完成情况"""
        counts = {"basic": 0, "intermediate": 0, "advanced": 0}
        for step in self.tutorial.steps:
            if step.step_id in self.completed:
                cat = step.category
                if cat in counts:
                    counts[cat] = counts[cat] + 1
        return counts

    @property
    def category_totals(self) -> Dict[str, int]:
        totals = {"basic": 0, "intermediate": 0, "advanced": 0}
        for step in self.tutorial.steps:
            cat = step.category
            if cat in totals:
                totals[cat] = totals[cat] + 1
        return totals

    # ------------------------------------------------------------------
    # 代码编译与执行
    # ------------------------------------------------------------------

    def _compile_duan(self, source: str) -> str:
        """编译段言代码为 Python"""
        try:
            from duan_parser_v3 import DuanParser
            from code_generator import PythonCodeGenerator
            parser = DuanParser()
            module = parser.parse(source)
            if module is None:
                raise RuntimeError("解析失败")
            generator = PythonCodeGenerator()
            return generator.generate(module)
        except ImportError:
            raise RuntimeError("无法导入段言编译器模块")

    def _run_duan(self, source: str) -> str:
        """执行段言代码，返回输出"""
        py_code = self._compile_duan(source)
        output_lines = []

        def _capture_print(*args, **kwargs):
            line = ' '.join(str(a) for a in args)
            output_lines.append(line)

        namespace = dict(self.namespace)
        namespace['print'] = _capture_print
        namespace.setdefault('__name__', '__main__')

        exec(py_code, namespace)
        # 更新持久化的命名空间（保留用户定义的变量）
        for k, v in namespace.items():
            if not k.startswith('_') and k not in ('print', '__name__', '__builtins__'):
                self.namespace[k] = v
        return '\n'.join(output_lines)

    # ------------------------------------------------------------------
    # 步骤显示与交互
    # ------------------------------------------------------------------

    def _get_category_label(self, category: str) -> str:
        labels = {
            "basic": f"{C['category']}[基础]{C['reset']}",
            "intermediate": f"{C['highlight']}[进阶]{C['reset']}",
            "advanced": f"{C['star']}[高级]{C['reset']}",
        }
        return labels.get(category, "")

    def _render_step(self, step: TutorialStep):
        """显示当前步骤的说明"""
        done_mark = f" {C['success']}✓{C['reset']}" if step.step_id in self.completed else ""
        cat_label = self._get_category_label(step.category)
        print(f"\n{C['section']}━━━ {cat_label} {step.title} (第 {step.step_id + 1}/{self.total_steps} 步){done_mark} ━━━{C['reset']}")
        print()
        print(f"{C['info']}{step.explanation}{C['reset']}")
        print()
        print(f"  {C['highlight']}🎯 任务：{C['reset']}{step.task}")
        print()
        print(f"  {C['tip']}💡 提示：{C['reset']}")
        for line in step.hint.split('\n'):
            print(f"  {C['tip']}{line}{C['reset']}")
        print(f"  {C['dim']}──────────────────────────────────────────────{C['reset']}")

    def _get_user_input(self) -> str:
        """获取用户输入的多行代码"""
        lines = []
        print(f"  {C['prompt']}请输入段言代码（空行执行，输入 'skip' 跳过）：{C['reset']}")
        while True:
            try:
                line = input(f"  {C['prompt']}段言> {C['reset']}")
            except (EOFError, KeyboardInterrupt):
                print()
                return ""

            if line.strip() == '':
                break
            if line.strip().lower() == 'skip':
                return 'skip'
            lines.append(line)
        return '\n'.join(lines)

    def _show_demo(self, step: TutorialStep):
        """显示参考答案"""
        print(f"\n  {C['demo']}📖 参考答案：{C['reset']}")
        for line in step.demo_code.split('\n'):
            print(f"  {C['demo']}  {line}{C['reset']}")
        print()

    def _friendly_error(self, e: Exception) -> str:
        """将 Python 异常转换为中文友好的提示"""
        msg = str(e)

        if 'is not defined' in msg:
            m = re.search(r"name '(.+?)' is not defined", msg)
            if m:
                name = m.group(1)
                return f"未定义的变量「{name}」—— 请先用「设 {name} 为 ...」声明"
        if 'invalid syntax' in msg.lower():
            return "语法错误——请检查关键字拼写、冒号、缩进是否正确"
        if 'unexpected indent' in msg.lower():
            return "缩进错误——段言用 4 个空格缩进，请检查代码块缩进是否一致"
        if 'unexpected EOF' in msg.lower() or 'EOF while' in msg.lower():
            return "代码不完整——可能是缺少冒号或缩进块不完整"
        if isinstance(e, TypeError):
            return f"类型错误：{msg}"
        if isinstance(e, NameError):
            return f"名称错误：{msg}——请检查变量名是否正确拼写"
        if isinstance(e, ZeroDivisionError):
            return "除数不能为零！"
        if isinstance(e, IndexError):
            return "索引越界——请检查列表索引是否在有效范围内"
        if isinstance(e, KeyError):
            return "键不存在——请检查字典键名是否正确"
        return f"出错啦：{msg}"

    # ------------------------------------------------------------------
    # 主运行循环
    # ------------------------------------------------------------------

    def run(self, start_from: Optional[int] = None) -> bool:
        """运行教程

        Args:
            start_from: 可选的起始步骤索引

        Returns:
            是否完成所有步骤
        """
        if start_from is not None:
            self.current_step = start_from

        # 显示进度概览
        self._show_progress_overview()

        while self.current_step < self.total_steps:
            step = self.tutorial.steps[self.current_step]

            # 如果已跳过，则继续
            if step.step_id in self.completed and self.current_step < self.total_steps - 1:
                self.current_step += 1
                continue

            self._render_step(step)

            # 获取用户输入
            user_code = self._get_user_input()

            if user_code == 'skip':
                print(f"  {C['dim']}已跳过「{step.title}」{C['reset']}")
                self.completed.add(step.step_id)
                self._save_progress()
                self.current_step += 1
                continue

            if not user_code.strip():
                # 空输入：询问是否查看 demo
                print(f"  {C['tip']}输入 demo 查看参考答案，或输入代码开始练习{C['reset']}")
                continue

            # 处理特殊命令
            cmd = user_code.strip().lower()
            if cmd == 'demo':
                self._show_demo(step)
                continue
            if cmd == 'exit' or cmd == 'quit':
                print(f"\n  {C['success']}教程已暂停，下次继续！{C['reset']}")
                self._save_progress()
                return False
            if cmd == 'progress':
                self._show_progress_overview()
                continue

            # 执行用户代码
            try:
                output = self._run_duan(user_code)
                if output:
                    print(f"\n  {C['output']}{output}{C['reset']}")

                passed, feedback = step.validate(output, self.namespace)
                if passed:
                    print(f"\n  {C['success']}🎉 {feedback}{C['reset']}")
                    self.completed.add(step.step_id)
                    self._save_progress()
                    self.current_step += 1
                else:
                    print(f"\n  {C['error']}✗ {feedback}{C['reset']}")
                    print(f"  {C['tip']}💡 试试输入 demo 查看参考答案，或修改代码重试{C['reset']}")

            except Exception as e:
                print(f"\n  {C['error']}✗ {self._friendly_error(e)}{C['reset']}")

        # 完成所有步骤
        if self.is_all_completed:
            self._show_completion_message()
            return True

        return False

    def _show_progress_overview(self):
        """显示进度概览"""
        print(f"\n{C['title']}╔══════════════════════════════════════════════════════════╗")
        print(f"║         🀄  段言交互式教程  🀄                              ║")
        print(f"║         {self.tutorial.name}                                  ║")
        print(f"╚══════════════════════════════════════════════════════════╝{C['reset']}")
        print()
        print(f"  {C['highlight']}教程：{C['reset']}{self.tutorial.name}")
        print(f"  {C['highlight']}说明：{C['reset']}{self.tutorial.description}")
        print(f"  {C['highlight']}前置要求：{C['reset']}{self.tutorial.prerequisites}")
        print()

        # 进度条
        done = len(self.completed)
        total = self.total_steps
        pct = done * 100 // total if total > 0 else 0
        bar_len = 30
        filled = done * bar_len // total if total > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"  {C['label']}进度：{C['reset']}{bar} {pct}% ({done}/{total})")
        print()

        # 分类统计
        cat_labels = {"basic": "基础", "intermediate": "进阶", "advanced": "高级"}
        for cat, label in cat_labels.items():
            d = self.category_counts.get(cat, 0)
            t = self.category_totals.get(cat, 0)
            if t > 0:
                print(f"    {label}练习：{C['success']}{d}{C['reset']}/{t} 已完成")
        print()

        print(f"  {C['dim']}怎么玩？{C['reset']}")
        print(f"  {C['dim']}  • 直接输入段言代码，按 Enter 执行{C['reset']}")
        print(f"  {C['dim']}  • 输入 demo 查看参考答案{C['reset']}")
        print(f"  {C['dim']}  • 输入 skip 跳过当前步骤{C['reset']}")
        print(f"  {C['dim']}  • 输入 progress 查看进度{C['reset']}")
        print(f"  {C['dim']}  • 输入 quit 退出教程{C['reset']}")

    def _show_completion_message(self):
        """显示完成消息"""
        # 统计各类别完成情况
        cat_counts = self.category_counts
        cat_totals = self.category_totals

        print(f"\n{C['title']}╔══════════════════════════════════════════════════════════╗")
        print(f"║       🎉 恭喜！你完成了全部 {self.total_steps} 个练习！🎉        ║")
        print(f"╚══════════════════════════════════════════════════════════╝{C['reset']}")
        print()
        print(f"  {C['success']}你已经完成了「{self.tutorial.name}」教程！{C['reset']}")
        print()

        # 完成统计
        print(f"  {C['label']}完成统计：{C['reset']}")
        cat_labels = {"basic": "基础", "intermediate": "进阶", "advanced": "高级"}
        for cat, label in cat_labels.items():
            d = cat_counts.get(cat, 0)
            t = cat_totals.get(cat, 0)
            if t > 0:
                status = f"{C['success']}✓{C['reset']}" if d >= t else f"{C['error']}✗{C['reset']}"
                print(f"    {status} {label}练习：{d}/{t}")

        print()

        # 下一步建议
        tutorial_id = self.tutorial.tutorial_id
        next_steps = {
            "beginner": "intermediate",
            "intermediate": "advanced",
            "advanced": None,
        }
        next_id = next_steps.get(tutorial_id)
        if next_id:
            all_tutorials = create_all_tutorials()
            if next_id in all_tutorials:
                next_tut = all_tutorials[next_id]
                print(f"  {C['highlight']}下一步：{C['reset']}你可以开始学习「{next_tut.name}」教程")
                print(f"  {C['dim']} 运行：python src/interactive_tutorial.py --tutorial {next_id}{C['reset']}")
        else:
            print(f"  {C['highlight']}你已经完成了所有教程！{C['reset']}")
            print(f"  {C['dim']}  • 运行 duan repl 进入交互式解释器，自由探索{C['reset']}")
            print(f"  {C['dim']}  • 运行 duan --help 查看所有命令选项{C['reset']}")
            print(f"  {C['dim']}  • 查看 docs/tutorials/ 目录下的教程文档继续学习{C['reset']}")

        print()


# =============================================================================
# 命令行接口
# =============================================================================

def list_tutorials():
    """列出所有可用的教程"""
    all_tutorials = create_all_tutorials()

    print(f"\n{C['title']}╔══════════════════════════════════════════════════════════╗")
    print(f"║         📚 段言交互式教程列表  📚                         ║")
    print(f"╚══════════════════════════════════════════════════════════╝{C['reset']}")
    print()

    cat_labels = {"beginner": "🟢 入门", "intermediate": "🟡 进阶", "advanced": "🔴 高级"}

    for tid, tut in all_tutorials.items():
        label = cat_labels.get(tut.category, "⚪ 其他")
        print(f"  {C['section']}{label}：{C['reset']}{C['title']}{tut.name}{C['reset']}")
        print(f"    教程ID：{C['code']}{tid}{C['reset']}")
        print(f"    说明：{tut.description}")
        print(f"    练习数：{C['highlight']}{tut.total_steps} 个步骤{C['reset']}")
        print(f"    前置要求：{tut.prerequisites}")
        print()

    print(f"  {C['tip']}使用方法：{C['reset']}")
    print(f"  python src/interactive_tutorial.py --tutorial beginner")
    print(f"  python src/interactive_tutorial.py --tutorial intermediate")
    print(f"  python src/interactive_tutorial.py --tutorial advanced")
    print(f"  python src/interactive_tutorial.py --resume")
    print()


def show_progress_summary():
    """显示所有教程的进度摘要"""
    all_tutorials = create_all_tutorials()
    progress_file = os.path.join(
        os.path.expanduser("~"), ".light", "tutorial_progress.json"
    )

    print(f"\n{C['title']}╔══════════════════════════════════════════════════════════╗")
    print(f"║         📊 学习进度总览  📊                              ║")
    print(f"╚══════════════════════════════════════════════════════════╝{C['reset']}")
    print()

    if not os.path.exists(progress_file):
        print(f"  {C['dim']}暂无学习记录，开始你的第一个教程吧！{C['reset']}")
        print()
        return

    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            all_progress = json.load(f)
    except Exception:
        print(f"  {C['error']}无法读取进度文件{C['reset']}")
        return

    for tid, tut in all_tutorials.items():
        progress = all_progress.get(tid, {})
        completed = set(progress.get('completed', []))
        total = tut.total_steps
        done = len(completed)
        pct = done * 100 // total if total > 0 else 0

        bar_len = 20
        filled = done * bar_len // total if total > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)

        status = f"{C['success']}✓{C['reset']}" if done >= total else f"{C['highlight']}→{C['reset']}"
        print(f"  {status} {C['title']}{tut.name}{C['reset']}")
        print(f"    {bar} {pct}% ({done}/{total})")
        print()

    print()


# =============================================================================
# 便捷入口
# =============================================================================

def run_tutorial(tutorial_id: str, resume: bool = False):
    """运行指定教程"""
    all_tutorials = create_all_tutorials()

    if tutorial_id not in all_tutorials:
        print(f"{C['error']}错误：未找到教程「{tutorial_id}」{C['reset']}")
        print(f"可用教程：{', '.join(all_tutorials.keys())}")
        return

    tutorial = all_tutorials[tutorial_id]
    engine = TutorialEngine(tutorial)

    if not resume:
        engine.clear_progress()

    engine.run()


def create_first_run_tutorial() -> TutorialEngine:
    """创建首次入门教程引擎（用于测试）"""
    all_tutorials = create_all_tutorials()
    tutorial = all_tutorials["beginner"]
    return TutorialEngine(tutorial)


def run_first_run_tutorial() -> bool:
    """运行首次入门教程（兼容旧版入口）"""
    engine = create_first_run_tutorial()
    return engine.run()


# =============================================================================
# 主入口
# =============================================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="段言交互式教程 - 边学边练！",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python src/interactive_tutorial.py              # 运行默认教程（基础入门）
  python src/interactive_tutorial.py --tutorial beginner   # 基础入门
  python src/interactive_tutorial.py --tutorial intermediate # 进阶练习
  python src/interactive_tutorial.py --tutorial advanced    # 高级编程
  python src/interactive_tutorial.py --list-tutorials       # 查看所有教程
  python src/interactive_tutorial.py --resume               # 继续上次学习
  python src/interactive_tutorial.py --progress             # 查看学习进度
        """
    )
    parser.add_argument(
        '--tutorial', type=str, default=None,
        help='选择要运行的教程 (beginner, intermediate, advanced)'
    )
    parser.add_argument(
        '--list-tutorials', action='store_true',
        help='列出所有可用的教程'
    )
    parser.add_argument(
        '--resume', action='store_true',
        help='继续上次的教程学习'
    )
    parser.add_argument(
        '--progress', action='store_true',
        help='查看所有教程的学习进度'
    )

    args = parser.parse_args()

    # 处理 --list-tutorials
    if args.list_tutorials:
        list_tutorials()
        return

    # 处理 --progress
    if args.progress:
        show_progress_summary()
        return

    # 处理 --resume
    if args.resume:
        # 查找上次学习的教程
        progress_file = os.path.join(
            os.path.expanduser("~"), ".light", "tutorial_progress.json"
        )
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    all_progress = json.load(f)
                # 找到有进度的教程
                for tid in ["beginner", "intermediate", "advanced"]:
                    if tid in all_progress and all_progress[tid].get('completed', []):
                        print(f"{C['success']}找到上次学习进度，继续「{all_progress[tid].get('name', tid)}」教程{C['reset']}")
                        run_tutorial(tid, resume=True)
                        return
                print(f"{C['dim']}未找到学习进度，开始基础入门教程{C['reset']}")
            except Exception:
                pass
        run_tutorial("beginner")
        return

    # 处理 --tutorial
    if args.tutorial:
        run_tutorial(args.tutorial)
        return

    # 默认运行基础入门
    run_tutorial("beginner")


if __name__ == '__main__':
    main()