#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明 AI Copilot — 命令行入口

集成到 light CLI 的子命令，提供算力不足场景下的光明代码生成辅助。

用法：
    # 生成 prompt（粘贴给任意 AI 使用）
    light ai prompt "写一个二分查找函数"
    light ai prompt --mode translate "def add(a, b): return a + b"
    light ai prompt --mode paragraph "写一个阶乘段落"

    # 输出语法速查卡（精简版/完整版）
    light ai card
    light ai card --full

    # 列出代码片段库
    light ai snippets

    # Python→光明对照示例
    light ai examples

    # 校验光明代码（语法检查 + 运行）
    light ai check hello.light

    # 交互式代码生成（多轮对话）
    light ai interactive
    light ai interactive --model "Qwen/Qwen2.5-0.5B-Instruct"

    # 基于上下文的错误修复
    light ai fix hello.light
    light ai fix hello.light --error "语法错误: 缺少冒号"
    light ai fix hello.light --apply

    # Python↔光明双向翻译
    light ai translate --to-light hello.py
    light ai translate --to-python hello.light
    light ai translate --interactive
"""

import argparse
import os
import sys
import subprocess
import json
from typing import List, Dict, Optional
from datetime import datetime

# 路径设置
_TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_TOOL_DIR))
sys.path.insert(0, _TOOL_DIR)
sys.path.insert(0, os.path.join(_PROJECT_DIR, 'src'))


# ═══════════════════════════════════════════════════════════════════
# 对话历史管理
# ═══════════════════════════════════════════════════════════════════

class Conversation:
    """多轮对话历史管理"""

    def __init__(self, max_turns: int = 20):
        self.history: List[Dict[str, str]] = []
        self.max_turns = max_turns

    def add_turn(self, role: str, content: str):
        """添加一轮对话"""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        # 超出最大轮数时裁掉最早的轮次
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-(self.max_turns * 2):]

    def get_context(self, max_chars: int = 4000) -> str:
        """获取对话历史上下文（用于 prompt 拼接）"""
        lines = []
        total = 0
        for turn in self.history[-10:]:  # 只取最近10轮
            role_label = "用户" if turn["role"] == "user" else "助手"
            entry = f"{role_label}: {turn['content']}"
            total += len(entry)
            if total > max_chars:
                break
            lines.append(entry)
        return "\n".join(lines)

    def get_last_code(self) -> Optional[str]:
        """获取最近一次助手生成的代码"""
        for turn in reversed(self.history):
            if turn["role"] == "assistant" and turn["content"].strip():
                return turn["content"]
        return None

    def show_history(self) -> str:
        """显示完整对话历史"""
        if not self.history:
            return "（暂无对话历史）"
        lines = []
        for i, turn in enumerate(self.history, 1):
            role_label = "用户" if turn["role"] == "user" else "助手"
            lines.append(f"[{i}] {role_label} ({turn['timestamp'][:19]}):")
            lines.append(turn["content"])
            lines.append("---")
        return "\n".join(lines)

    def clear(self):
        """清空历史"""
        self.history = []


def _ensure_utf8():
    """确保 stdout 使用 UTF-8 编码"""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')


def cmd_prompt(args):
    """生成 prompt"""
    _ensure_utf8()
    from prompt_generator import generate_prompt

    mode = args.mode or "auto"
    compact = not args.full
    user_input = args.input

    # 如果输入是文件路径，读取文件内容
    if os.path.isfile(user_input):
        with open(user_input, encoding='utf-8') as f:
            user_input = f.read()

    prompt = generate_prompt(user_input, mode=mode, compact=compact)
    print(prompt)


def cmd_card(args):
    """输出语法速查卡"""
    _ensure_utf8()
    from syntax_card import generate_syntax_card

    compact = not args.full
    card = generate_syntax_card(compact=compact, include_verbs=args.verbs)
    print(card)


def cmd_snippets(args):
    """列出代码片段库"""
    _ensure_utf8()
    from snippets import list_snippets, get_snippet

    if args.name:
        snippet = get_snippet(args.name)
        if not snippet:
            print(f"片段不存在: {args.name}")
            sys.exit(1)
        print(f"名称：{args.name}")
        print(f"用途：{snippet['desc']}")
        print(f"模板：\n{snippet['code']}")
        if 'example' in snippet:
            print(f"示例：\n{snippet['example']}")
    else:
        print(list_snippets())


def cmd_examples(args):
    """输出 Python→光明对照示例"""
    _ensure_utf8()
    from syntax_card import generate_example_pairs
    print(generate_example_pairs())


def cmd_check(args):
    """校验光明代码文件"""
    _ensure_utf8()
    filepath = args.file

    if not os.path.isfile(filepath):
        print(f"文件不存在: {filepath}")
        sys.exit(1)

    # Step 1: 语法检查
    print(f"[1/2] 语法检查: {filepath}")
    result = subprocess.run(
        [sys.executable, '-m', 'cli.light', 'check', filepath],
        capture_output=True, text=True, encoding='utf-8',
        cwd=_PROJECT_DIR,
    )
    if result.returncode != 0:
        print(f"  ✗ 语法检查失败:")
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return
    print(f"  ✓ 语法检查通过")

    # Step 2: 运行检查
    if args.run:
        print(f"[2/2] 运行测试: {filepath}")
        result = subprocess.run(
            [sys.executable, '-m', 'cli.light', 'run', filepath],
            capture_output=True, text=True, encoding='utf-8',
            cwd=_PROJECT_DIR,
            timeout=args.timeout,
        )
        if result.returncode != 0:
            print(f"  ✗ 运行失败:")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        else:
            print(f"  ✓ 运行成功")
            if result.stdout.strip():
                print(f"  输出:")
                for line in result.stdout.strip().split('\n'):
                    print(f"    {line}")
    else:
        print("[2/2] 跳过运行检查（使用 --run 启用）")


# ═══════════════════════════════════════════════════════════════════
# D24: 交互式代码生成（多轮对话）
# ═══════════════════════════════════════════════════════════════════

def cmd_interactive(args):
    """交互式代码生成模式 - 支持多轮对话"""
    _ensure_utf8()

    # 尝试加载离线模型
    offline_model = None
    if args.model:
        try:
            from offline_model import OfflineModel
            offline_model = OfflineModel(model_name=args.model)
            print(f"离线模型已加载: {args.model}")
        except Exception as e:
            print(f"离线模型加载失败: {e}")
            print("将使用规则引擎回退模式")

    conversation = Conversation(max_turns=args.max_turns)

    print("=" * 50)
    print("光明 AI Copilot — 交互式代码生成")
    print("=" * 50)
    print("输入自然语言描述来生成光明代码")
    print("特殊命令:")
    print("  exit/quit    — 退出")
    print("  history      — 查看对话历史")
    print("  clear        — 清空对话历史")
    print("  save <file>  — 将最后生成的代码保存到文件")
    print("  show         — 显示最后生成的代码")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n再见！")
            break

        if not user_input:
            continue

        # 处理特殊命令
        if user_input.lower() in ('exit', 'quit'):
            print("再见！")
            break

        if user_input.lower() == 'history':
            print(conversation.show_history())
            continue

        if user_input.lower() == 'clear':
            conversation.clear()
            print("对话历史已清空")
            continue

        if user_input.lower() == 'show':
            last_code = conversation.get_last_code()
            if last_code:
                print(f"\n最后生成的代码:\n{last_code}")
            else:
                print("（暂无生成的代码）")
            continue

        if user_input.lower().startswith('save '):
            filename = user_input[5:].strip()
            last_code = conversation.get_last_code()
            if last_code:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(last_code)
                print(f"代码已保存到: {os.path.abspath(filename)}")
            else:
                print("（暂无代码可保存）")
            continue

        # 记录用户输入
        conversation.add_turn("user", user_input)

        # 尝试生成代码
        if offline_model and offline_model.model_available:
            # 使用离线模型
            context = conversation.get_context()
            prompt = f"对话历史:\n{context}\n\n请生成光明代码: {user_input}"
            response = offline_model.generate(prompt)
        else:
            # 使用规则引擎
            response = _rule_based_generate(user_input, conversation)

        print(f"\n助手 > {response}")
        conversation.add_turn("assistant", response)


def _rule_based_generate(user_input: str, conversation: Conversation) -> str:
    """基于规则的代码生成"""
    from prompt_generator import generate_prompt

    last_code = conversation.get_last_code()

    # 检测是否为修改请求
    refinement_keywords = ['修改', '调整', '完善', '加上', '添加', '加', '改', '修复', '优化']
    is_refinement = any(kw in user_input for kw in refinement_keywords)

    if is_refinement and last_code:
        # 这是对已有代码的修改请求
        prompt = f"当前代码:\n{last_code}\n\n修改需求: {user_input}\n\n请输出修改后的完整光明代码:"
        mode = "paragraph"
    else:
        # 这是新代码生成请求
        prompt = generate_prompt(user_input, mode="auto", compact=True)

    return prompt


# ═══════════════════════════════════════════════════════════════════
# D24: 基于上下文的错误修复
# ═══════════════════════════════════════════════════════════════════

def cmd_fix_context(args):
    """基于文件上下文的代码修复"""
    _ensure_utf8()
    filepath = args.file

    if not os.path.isfile(filepath):
        print(f"文件不存在: {filepath}")
        sys.exit(1)

    # 读取文件内容
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"文件: {filepath} ({len(content)} 字符)")
    print(f"错误描述: {args.error or '（自动检测）'}")
    print()

    # Step 1: 尝试语法检查以获取错误信息
    errors = _detect_syntax_errors(content)
    if errors:
        print(f"发现 {len(errors)} 个语法问题:")
        for err in errors:
            print(f"  ✗ {err}")
    else:
        print("✓ 未检测到明显语法问题")

    print()

    # Step 2: 生成修复建议
    fixes = _generate_fixes(content, errors, args.error)
    if fixes:
        print("=" * 50)
        print("修复建议:")
        print("=" * 50)
        for i, fix in enumerate(fixes, 1):
            print(f"\n--- 修复方案 {i} ---")
            print(f"{fix['description']}")
            print(f"代码:\n{fix['code']}")
    else:
        print("暂无法自动生成修复建议")

    # Step 3: 如果 --apply，直接应用修复
    if args.apply and fixes:
        best_fix = fixes[0]
        output_path = args.output or filepath
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(best_fix['code'])
        print(f"\n修复已应用到: {output_path}")


def _detect_syntax_errors(content: str) -> List[str]:
    """检测光明代码中的常见语法错误"""
    errors = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # 检查缩进一致性
        if i > 1 and stripped and not stripped.startswith('#'):
            prev_line = lines[i - 2].rstrip() if i >= 2 else ''
            if prev_line.endswith('：') and not line.startswith('    '):
                errors.append(f"行 {i}: 冒号后缺少缩进")

        # 检查常见关键字拼写
        keyword_map = {
            '函数': '段落',
            'def ': '段落 ',
            'print(': '打印(',
            'return ': '返回 ',
            'class ': '类 ',
            'if ': '如果 ',
            'else:': '否则：',
            'elif ': '否则若 ',
            'for ': '遍历 ',
            'while ': '当 ',
            'try:': '尝试：',
            'except': '捕获',
            'finally:': '最终：',
            'with ': '使用 ',
            'async ': '异步 ',
            'await ': '等待 ',
            'import ': '导入 ',
            'from ': '从 ',
            'True': '真',
            'False': '假',
            'None': '空',
            'and': '且',
            'or': '或',
            'not': '非',
        }
        for py_kw, light_kw in keyword_map.items():
            if py_kw in stripped and light_kw not in stripped:
                # 避免误报：如果已经在使用光明关键字则跳过
                if not any(light_kw in stripped for light_kw in ['段落', '打印', '返回', '类', '如果', '否则', '遍历', '当', '尝试', '捕获', '使用', '异步', '等待', '导入', '从', '真', '假', '空', '且', '或', '非']):
                    pass  # 可能含 Python 关键字，但需要更精确的判断

    return errors


def _generate_fixes(content: str, errors: List[str], user_error: Optional[str]) -> List[Dict]:
    """生成代码修复建议"""
    fixes = []

    # 尝试使用离线模型
    try:
        from offline_model import OfflineModel
        model = OfflineModel()
        if model.model_available:
            error_context = user_error or '\n'.join(errors) if errors else '未知错误'
            prompt = f"修复以下光明代码中的错误:\n\n代码:\n{content}\n\n错误:\n{error_context}\n\n请输出修复后的完整光明代码:"
            fix_code = model.fix_syntax(prompt)
            if fix_code and fix_code != content:
                fixes.append({
                    "description": "基于离线模型的修复建议",
                    "code": fix_code,
                })
                return fixes
    except Exception:
        pass

    # 回退到规则修复
    fix_code = _rule_based_fix(content, errors, user_error)
    if fix_code and fix_code != content:
        fixes.append({
            "description": "基于规则的修复建议",
            "code": fix_code,
        })

    # 提供原始代码 + 错误提示
    if user_error:
        fixes.append({
            "description": f"原始代码（请根据错误描述手动修正: {user_error}）",
            "code": content,
        })
    elif errors:
        fixes.append({
            "description": "原始代码（请根据以上错误提示手动修正）",
            "code": content,
        })

    return fixes


def _rule_based_fix(content: str, errors: List[str], user_error: Optional[str]) -> Optional[str]:
    """基于规则的代码修复"""
    lines = content.split('\n')
    fixed_lines = []
    changed = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            fixed_lines.append(line)
            continue

        new_line = line

        # 修复: 函数定义缺少冒号
        if stripped.startswith('段落 ') and not stripped.endswith('：') and not stripped.endswith(':'):
            # 检查是否以参数结尾
            if '接收' in stripped:
                new_line = line + '：'
                changed = True

        # 修复: 如果/否则若/否则 缺少冒号
        for kw in ['如果 ', '否则若 ', '当 ', '遍历 ', '匹配 ']:
            if stripped.startswith(kw) and not stripped.endswith('：') and not stripped.endswith(':'):
                new_line = line + '：'
                changed = True
                break

        # 修复: 尝试/捕获/最终 缺少冒号
        for kw in ['尝试', '捕获', '最终']:
            if stripped.startswith(kw) and not stripped.endswith('：') and not stripped.endswith(':'):
                # 检查是否后面有参数（如 捕获 异常 e）
                if stripped == kw or stripped.startswith(kw + ' '):
                    new_line = line + '：'
                    changed = True
                    break

        # 修复: 使用 ... 为 缺少冒号
        if stripped.startswith('使用 ') and ' 为 ' in stripped and not stripped.endswith('：') and not stripped.endswith(':'):
            new_line = line + '：'
            changed = True

        # 修复: 缩进问题（冒号后下一行应缩进）
        if i > 0:
            prev_stripped = lines[i - 1].strip()
            if prev_stripped.endswith('：') or prev_stripped.endswith(':'):
                current_indent = len(line) - len(line.lstrip())
                prev_indent = len(lines[i - 1]) - len(lines[i - 1].lstrip())
                if current_indent <= prev_indent and stripped:
                    # 自动添加缩进
                    new_line = '    ' + line
                    changed = True

        fixed_lines.append(new_line)

    if changed:
        return '\n'.join(fixed_lines)
    return None


# ═══════════════════════════════════════════════════════════════════
# Python ↔ 光明 双向翻译
# ═══════════════════════════════════════════════════════════════════

def cmd_translate(args):
    """Python ↔ 光明 双向翻译"""
    _ensure_utf8()

    from translator import PythonToLightTranslator, LightToPythonTranslator

    if args.to_light:
        # Python → 光明
        file_path = args.to_light
        if not os.path.isfile(file_path):
            print(f"文件不存在: {file_path}")
            sys.exit(1)
        try:
            translator = PythonToLightTranslator()
            result = translator.translate_file(file_path)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"翻译完成，输出到: {args.output}")
            else:
                print(result)
        except SyntaxError as e:
            print(f"Python 语法错误: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"翻译错误: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.to_python:
        # 光明 → Python
        file_path = args.to_python
        if not os.path.isfile(file_path):
            print(f"文件不存在: {file_path}")
            sys.exit(1)
        try:
            translator = LightToPythonTranslator()
            result = translator.translate_file(file_path)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"翻译完成，输出到: {args.output}")
            else:
                print(result)
        except ValueError as e:
            print(f"光明语法错误: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"翻译错误: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.interactive:
        # 交互式翻译模式
        print("=" * 50)
        print("光明 ↔ Python 双向翻译 — 交互模式")
        print("=" * 50)
        print("输入 Python 代码翻译为光明，或输入光明代码翻译为 Python")
        print("特殊命令: exit/quit — 退出, mode py — 切到 Python→光明模式")
        print("         mode light — 切到 光明→Python 模式")
        print("=" * 50)

        mode = "py_to_light"  # 默认 Python→光明
        py_translator = PythonToLightTranslator()
        light_translator = LightToPythonTranslator()

        while True:
            try:
                user_input = input(f"\n[{ 'Python→光明' if mode == 'py_to_light' else '光明→Python' }] > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n再见！")
                break

            if not user_input:
                continue

            if user_input.lower() in ('exit', 'quit'):
                print("再见！")
                break

            if user_input.lower() == 'mode py':
                mode = "py_to_light"
                print("切换到 Python→光明 模式")
                continue

            if user_input.lower() == 'mode light':
                mode = "light_to_py"
                print("切换到 光明→Python 模式")
                continue

            try:
                if mode == "py_to_light":
                    result = py_translator.translate(user_input)
                    print(f"\n→ 光明:\n{result}")
                else:
                    result = light_translator.translate(user_input)
                    print(f"\n→ Python:\n{result}")
            except (SyntaxError, ValueError) as e:
                print(f"  ✗ 翻译错误: {e}")
            except Exception as e:
                print(f"  ✗ 错误: {e}")


# ═══════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog='light ai',
        description='光明 AI Copilot — 算力不足场景下的光明代码生成辅助工具',
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # prompt 子命令
    p_prompt = subparsers.add_parser('prompt', help='生成让 AI 写光明代码的 prompt')
    p_prompt.add_argument('input', help='需求描述或 Python 代码（也支持文件路径）')
    p_prompt.add_argument('--mode', choices=['auto', 'translate', 'create', 'paragraph'],
                         default='auto', help='生成模式（默认 auto 自动检测）')
    p_prompt.add_argument('--full', action='store_true', help='使用完整语法卡（默认精简卡）')
    p_prompt.set_defaults(func=cmd_prompt)

    # card 子命令
    p_card = subparsers.add_parser('card', help='输出光明语法速查卡')
    p_card.add_argument('--full', action='store_true', help='完整版（默认精简版）')
    p_card.add_argument('--verbs', action='store_true', help='包含动词参数参照表')
    p_card.set_defaults(func=cmd_card)

    # snippets 子命令
    p_snippets = subparsers.add_parser('snippets', help='列出代码片段库')
    p_snippets.add_argument('name', nargs='?', help='查看指定片段详情')
    p_snippets.set_defaults(func=cmd_snippets)

    # examples 子命令
    p_examples = subparsers.add_parser('examples', help='Python→光明对照示例')
    p_examples.set_defaults(func=cmd_examples)

    # check 子命令
    p_check = subparsers.add_parser('check', help='校验光明代码（语法+运行）')
    p_check.add_argument('file', help='光明代码文件路径')
    p_check.add_argument('--run', action='store_true', help='同时运行测试')
    p_check.add_argument('--timeout', type=int, default=10, help='运行超时秒数（默认10）')
    p_check.set_defaults(func=cmd_check)

    # interactive 子命令 (D24: 多轮对话)
    p_interactive = subparsers.add_parser('interactive', help='交互式代码生成（多轮对话）')
    p_interactive.add_argument('--model', default=None, help='指定离线模型名称（如 Qwen/Qwen2.5-0.5B-Instruct）')
    p_interactive.add_argument('--max-turns', type=int, default=20, help='最大对话轮数（默认20）')
    p_interactive.set_defaults(func=cmd_interactive)

    # fix 子命令 (D24: 基于上下文的修复)
    p_fix = subparsers.add_parser('fix', help='基于文件上下文的代码修复')
    p_fix.add_argument('file', help='光明代码文件路径')
    p_fix.add_argument('--error', '-e', default=None, help='错误描述（可选，默认自动检测）')
    p_fix.add_argument('--apply', '-a', action='store_true', help='直接应用修复到文件')
    p_fix.add_argument('--output', '-o', default=None, help='输出文件路径（默认覆盖原文件）')
    p_fix.set_defaults(func=cmd_fix_context)

    # translate 子命令 (D25: Python↔光明双向翻译)
    p_translate = subparsers.add_parser('translate', help='Python ↔ 光明 双向翻译')
    translate_group = p_translate.add_mutually_exclusive_group()
    translate_group.add_argument('--to-light', metavar='FILE',
                                 help='将 Python 文件翻译为光明')
    translate_group.add_argument('--to-python', metavar='FILE',
                                 help='将光明文件翻译为 Python')
    translate_group.add_argument('--interactive', action='store_true',
                                 help='交互式翻译模式')
    p_translate.add_argument('--output', '-o', metavar='FILE',
                             help='输出到文件（默认输出到终端）')
    p_translate.set_defaults(func=cmd_translate)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == '__main__':
    main()