# -*- coding: utf-8 -*-
"""
光明运行时错误信息友好化模块

将 Python 运行时的异常 traceback 转换为光明源码行号和友好的中文错误信息。
"""

import sys
import re
import traceback
from typing import List, Tuple, Optional, Set


def _levenshtein_distance(s1: str, s2: str) -> int:
    """计算 Levenshtein 编辑距离"""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def _find_similar_names(name: str, candidates: Set[str], max_distance: int = 3, max_results: int = 3) -> List[str]:
    """查找相似名称"""
    scored = []
    for candidate in candidates:
        dist = _levenshtein_distance(name, candidate)
        if dist <= max_distance:
            scored.append((dist, candidate))
    scored.sort(key=lambda x: (x[0], len(x[1])))
    return [c for _, c in scored[:max_results]]


# 常见变量/函数名建议列表
COMMON_LIGHT_NAMES = {
    '打印', '长度', '输入', '整数', '文本', '浮点数', '布尔',
    '列表', '字典', '元组', '集合', '范围', '枚举',
    '转字符串', '转整数', '转浮点数', '转布尔',
    '追加', '弹出', '插入', '排序', '反转', '清除', '复制',
    '包含', '获取', '设置', '删除', '更新', '合并',
    '打开', '读取', '写入', '关闭',
    '真', '假', '空', '无',
    '数学', '随机', '时间', '文件', '系统', 'JSON',
    '序列化', '解析', '创建', '格式化',
    '替换', '分割', '连接', '查找', '统计',
    '最大值', '最小值', '求和', '平均值', '绝对值',
    '类型', '实例', '属性', '方法', '类',
    '主', '入口', '初始化', '运行', '测试',
    '读取文件', '写入文件', '文件存在', '目录存在',
    '解析JSON', '序列化JSON', '美化JSON',
    '列表长度', '列表追加', '列表弹出', '列表插入', '列表排序', '列表包含',
    '字符串长度', '字符串替换', '字符串分割', '字符串包含',
    '字典包含键', '字典获取', '字典键列表', '字典值列表',
    '平方根', '阶乘', '幂', '绝对值', '取整', '随机数',
}


class LightErrorFormatter:
    """光明错误信息格式化器"""

    def __init__(self, source: str = '', source_name: str = '<光明代码>'):
        self.source = source
        self.source_name = source_name
        self.source_lines = source.split('\n') if source else []
        self._known_names: Set[str] = set()  # 已知变量/函数名，用于相似名建议

    def parse_line_mapping(self, python_code: str) -> dict:
        """从生成的 Python 代码中解析 LIGHT_SRC 行号映射表

        Returns:
            dict: {python_line: (light_line, code_snippet)}
        """
        mapping = {}
        for line in python_code.split('\n'):
            m = re.match(r'#\s*LIGHT_SRC:(\d+):(.*)', line)
            if m:
                light_line = int(m.group(1))
                snippet = m.group(2)
                mapping[line] = (light_line, snippet)
        return mapping

    def build_full_mapping(self, python_code: str) -> dict:
        """构建完整的 Python 行号 -> 光明行号映射

        思路：
        1. 先找 LIGHT_SRC 注释对应的 Python 行号
        2. 假设两个相邻映射点之间是连续的（简单的近似）
        """
        lines = python_code.split('\n')
        anchors = []  # (py_line, light_line)

        for i, line in enumerate(lines):
            m = re.match(r'#\s*LIGHT_SRC:(\d+):', line)
            if m:
                anchors.append((i, int(m.group(1))))

        if not anchors:
            return {}

        mapping = {}
        for idx, (py_line, light_line) in enumerate(anchors):
            if idx + 1 < len(anchors):
                next_py, next_light = anchors[idx + 1]
                py_end = next_py
            else:
                py_end = len(lines)

            for p in range(py_line, py_end):
                if mapping.get(p) is None:
                    mapping[p] = light_line

        return mapping

    def format_exception(self, exc_type=None, exc_value=None, exc_tb=None) -> str:
        """格式化异常为光明友好的错误信息

        Args:
            exc_type: 异常类型
            exc_value: 异常值
            exc_tb: traceback 对象

        Returns:
            格式化后的错误信息字符串
        """
        if exc_type is None:
            exc_type, exc_value, exc_tb = sys.exc_info()

        if exc_type is None:
            return "未知错误"

        result = []
        result.append("=" * 60)
        result.append(f"❌ 光明运行时错误: {exc_type.__name__}")
        result.append("=" * 60)
        result.append("")

        result.append(f"📋 错误类型: {self._chinese_exc_name(exc_type.__name__)}")
        result.append(f"💬 错误信息: {exc_value}")
        result.append("")

        if exc_tb:
            result.append("📍 错误位置：")
            result.append("-" * 60)
            tb_lines = traceback.format_tb(exc_tb)
            for tb_line in tb_lines:
                result.append(tb_line.rstrip())

            result.append("")

        if self.source_lines:
            result.append(self._format_source_context(exc_tb))

        result.extend(self._suggest_fix(exc_type.__name__, str(exc_value)))

        return "\n".join(result)

    def format_traceback_string(self, tb_text: str) -> str:
        """格式化 traceback 字符串为光明友好版本"""
        result = []
        result.append("=" * 60)
        result.append("❌ 光明运行时错误")
        result.append("=" * 60)
        result.append("")
        result.append(tb_text)
        return "\n".join(result)

    def _chinese_exc_name(self, en_name: str) -> str:
        """将英文异常名转为中文（D05: 全量映射，与 LIGHT_EXCEPTION_MAP 保持一致）"""
        mapping = {
            'SyntaxError': '语法解析错误',
            'TypeError': '类型错误',
            'ValueError': '值错误',
            'NameError': '名称错误',
            'IndexError': '索引错误',
            'KeyError': '键错误',
            'AttributeError': '属性错误',
            'ImportError': '导入错误',
            'RuntimeError': '运行时错误',
            'ZeroDivisionError': '除零错误',
            'FileNotFoundError': '文件未找到',
            'IOError': '输入输出错误',
            'MemoryError': '内存错误',
            'RecursionError': '递归错误',
            'StopIteration': '迭代停止',
            'AssertionError': '断言错误',
            'NotImplementedError': '未实现错误',
            'OverflowError': '溢出错误',
            'ArithmeticError': '算术错误',
            'LookupError': '查找错误',
            # 额外常见异常
            'IndentationError': '缩进错误',
            'TabError': '制表符错误',
            'UnicodeError': 'Unicode 错误',
            'EOFError': '输入结束错误',
            'KeyboardInterrupt': '用户中断',
            'SystemExit': '系统退出',
            'ConnectionError': '连接错误',
            'TimeoutError': '超时错误',
            'OSError': '系统错误',
            'ModuleNotFoundError': '模块未找到',
            'PermissionError': '权限不足',
            'UnicodeDecodeError': 'Unicode解码错误',
            'UnicodeEncodeError': 'Unicode编码错误',
            'FloatingPointError': '浮点运算错误',
            'ReferenceError': '引用错误',
            'SystemError': '系统内部错误',
        }
        return mapping.get(en_name, en_name)

    def _format_source_context(self, exc_tb, context_lines: int = 2) -> str:
        """格式化错误位置的源码上下文"""
        result = []
        result.append("📄 源码上下文：")
        result.append("-" * 60)

        last_line = None
        for tb_frame, lineno in self._walk_tb(exc_tb):
            last_line = lineno
            break

        if last_line is None:
            result.append("（无法定位源码位置）")
            return "\n".join(result)

        start = max(0, last_line - context_lines - 1)
        end = min(len(self.source_lines), last_line + context_lines)

        for i in range(start, end):
            line_num = i + 1
            line_content = self.source_lines[i] if i < len(self.source_lines) else ''

            if line_num == last_line:
                result.append(f"  → {line_num:4d} | {line_content}  ◀━━ 错误位置")
            else:
                result.append(f"    {line_num:4d} | {line_content}")

        return "\n".join(result)

    def _walk_tb(self, exc_tb):
        """遍历 traceback"""
        while exc_tb:
            yield exc_tb.tb_frame, exc_tb.tb_lineno
            exc_tb = exc_tb.tb_next

    def _extract_name_from_msg(self, exc_name: str, exc_msg: str) -> Optional[str]:
        """从错误消息中提取名称"""
        # NameError: name 'xxx' is not defined
        m = re.search(r"name\s+'([^']+)'", exc_msg)
        if m:
            return m.group(1)
        # KeyError: 'xxx'
        m = re.search(r"'([^']+)'", exc_msg)
        if m:
            return m.group(1)
        return None

    def _get_similar_name_suggestions(self, name: str) -> List[str]:
        """获取相似名称建议"""
        candidates = COMMON_LIGHT_NAMES | self._known_names
        # 从源码中提取变量名
        if self.source_lines:
            for line in self.source_lines:
                # 匹配 设 X 为 ...
                for m in re.finditer(r'设\s+(\w+)\s+为', line):
                    candidates.add(m.group(1))
                # 匹配 段落 X 接收
                for m in re.finditer(r'段落\s+(\w+)\s+接收', line):
                    candidates.add(m.group(1))
                # 匹配 类 X
                for m in re.finditer(r'类\s+(\w+)', line):
                    candidates.add(m.group(1))
                # 匹配 导入 X
                for m in re.finditer(r'从\s+(\w+)\s+导入', line):
                    candidates.add(m.group(1))
        return _find_similar_names(name, candidates)

    def _suggest_fix(self, exc_name: str, exc_msg: str) -> List[str]:
        """根据异常类型给出修复建议"""
        suggestions = []
        suggestions.append("")
        suggestions.append("💡 修复建议：")
        suggestions.append("-" * 60)

        # D06: 添加通用中文修改指引
        _chinese_hints = {
            'SyntaxError': '请检查代码语法是否正确，确保所有括号、引号、冒号等符号已正确配对。',
            'TypeError': '请检查操作数类型是否匹配，光明中文本和数字不能直接进行运算。',
            'ValueError': '请检查传入的值是否在有效范围内，可能需要先进行类型转换。',
            'NameError': '请检查变量名是否拼写正确，使用前需先通过「设」关键字定义变量。',
            'IndexError': '请检查索引是否在有效范围内，光明列表索引从 0 开始。',
            'KeyError': '请检查字典键是否存在，可以使用「字典包含键」方法先判断。',
            'AttributeError': '请检查对象是否拥有该属性或方法，需确认类定义中已声明。',
            'ImportError': '请检查模块名是否拼写正确，确认模块已安装或在标准库路径中。',
            'RuntimeError': '程序运行时出现异常，请根据具体错误信息排查。',
            'ZeroDivisionError': '除数不能为零，请在除法前添加条件判断。',
            'FileNotFoundError': '请检查文件路径是否正确，确认文件是否存在。',
            'IOError': '输入输出操作失败，请检查文件状态和权限。',
            'MemoryError': '内存不足，请尝试优化代码或增加系统内存。',
            'RecursionError': '递归过深，请检查函数是否存在无限递归，增加递归终止条件。',
            'StopIteration': '迭代器已无更多元素，请检查循环逻辑或使用默认值。',
            'AssertionError': '断言条件不满足，请检查断言表达式是否正确。',
            'NotImplementedError': '该方法尚未实现，请补充实现代码。',
            'OverflowError': '数值运算结果超出范围，请使用更大的数据类型。',
            'ArithmeticError': '算术运算出错，请检查操作数和运算符是否正确。',
            'LookupError': '查找操作失败，请检查索引或键是否存在。',
        }
        _general_hint = _chinese_hints.get(exc_name)
        if _general_hint:
            suggestions.append(f"📌 {_general_hint}")
            suggestions.append("")

        if exc_name == 'NameError':
            suggestions.append("• 检查变量名是否拼写正确")
            suggestions.append("• 确认变量在使用前已经通过'设 ... 为'声明")
            suggestions.append("• 检查变量是否在正确的作用域内（如在段落内部定义的变量不能在外部使用）")
            # 相似名称建议
            name = self._extract_name_from_msg(exc_name, exc_msg)
            if name:
                similar = self._get_similar_name_suggestions(name)
                if similar:
                    suggestions.append(f"• 您是不是想找: {', '.join(similar)}？")
                else:
                    suggestions.append(f"  未找到与 '{name}' 相似的名称，请检查拼写")
            suggestions.append(f"  错误信息: {exc_msg}")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 x 为 10")
            suggestions.append("          打印(x)")
            suggestions.append("")
            suggestions.append("    错误: 打印(x)")
            suggestions.append("          设 x 为 10")
        elif exc_name == 'TypeError':
            suggestions.append("• 检查操作数类型是否正确（如不能对文本进行乘法运算）")
            suggestions.append("• 确认函数调用时参数类型与声明一致")
            suggestions.append("• 如果使用了类型注解，请检查实际传值是否符合类型要求")
            # 提取类型信息
            type_m = re.search(r"unsupported operand type\(s\) for [^:]+: '([^']+)' and '([^']+)'", exc_msg)
            if type_m:
                suggestions.append(f"• 操作类型不匹配: '{type_m.group(1)}' 和 '{type_m.group(2)}' 不能进行该操作")
            suggestions.append(f"  错误信息: {exc_msg}")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 x 为 整数 = 10")
            suggestions.append("          设 y 为 整数 = 20")
            suggestions.append("          打印(x 加 y)")
            suggestions.append("")
            suggestions.append("    错误: 设 x 为 文本 = \"hello\"")
            suggestions.append("          打印(x 乘 2)")
        elif exc_name == 'IndexError':
            suggestions.append("• 检查列表索引是否在有效范围内（索引从0开始，长度为N的列表最大索引为N-1）")
            suggestions.append("• 可以先用 列表长度() 获取列表长度后再访问")
            suggestions.append("• 使用 列表包含() 方法判断索引是否有效")
            # 提取索引信息
            idx_m = re.search(r"list index out of range", exc_msg)
            if idx_m:
                suggestions.append("• 列表索引超出范围，请检查索引值是否小于列表长度")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 lst 为 [1, 2, 3]")
            suggestions.append("          如 索引 < 列表长度(lst)：")
            suggestions.append("              打印(lst[索引])")
            suggestions.append("          否则：")
            suggestions.append("              打印(\"索引越界\")")
        elif exc_name == 'KeyError':
            suggestions.append("• 检查字典键是否存在")
            suggestions.append("• 可以用 字典包含键() 方法先判断键是否存在")
            suggestions.append("• 使用 字典获取() 方法提供默认值")
            # 提取键名
            key_m = re.search(r"'([^']+)'", exc_msg)
            if key_m:
                key_name = key_m.group(1)
                suggestions.append(f"• 键 '{key_name}' 不存在")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 d 为 {'名字': '张三'}")
            suggestions.append("          如 字典包含键(d, '年龄')：")
            suggestions.append("              打印(d['年龄'])")
            suggestions.append("          否则：")
            suggestions.append("              打印(字典获取(d, '年龄', 0))")
        elif exc_name == 'AttributeError':
            suggestions.append("• 检查对象是否拥有该属性或方法")
            suggestions.append("• 确认类名/对象名拼写正确")
            suggestions.append("• 检查是否混淆了属性和方法（方法需要加括号调用）")
            # 提取属性名
            attr_m = re.search(r"'([^']+)' object has no attribute '([^']+)'", exc_msg)
            if attr_m:
                obj_type = attr_m.group(1)
                attr_name = attr_m.group(2)
                suggestions.append(f"• 对象类型 '{obj_type}' 没有属性 '{attr_name}'")
                # 常见属性建议
                common_attrs = {
                    'str': ['长度', '替换', '分割', '连接', '查找', '格式化'],
                    'list': ['追加', '弹出', '插入', '排序', '反转', '长度'],
                    'dict': ['获取', '键列表', '值列表', '包含键', '更新'],
                    'int': ['转字符串', '转浮点数'],
                    'float': ['转整数', '转字符串'],
                }
                if obj_type in common_attrs:
                    suggestions.append(f"• '{obj_type}' 的常用属性: {', '.join(common_attrs[obj_type])}")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 s 为 \"hello\"")
            suggestions.append("          打印(字符串长度(s))")
            suggestions.append("")
            suggestions.append("    错误: 设 s 为 \"hello\"")
            suggestions.append("          打印(s.长度)")
        elif exc_name == 'ZeroDivisionError':
            suggestions.append("• 检查除数是否为零")
            suggestions.append("• 在除法前添加条件判断")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 除数 为 0")
            suggestions.append("          如 除数 != 0：")
            suggestions.append("              打印(10 / 除数)")
            suggestions.append("          否则：")
            suggestions.append("              打印(\"除数不能为零\")")
        elif exc_name == 'SyntaxError' or exc_name == 'IndentationError':
            if exc_name == 'SyntaxError':
                suggestions.append("• 检查代码语法是否正确")
                suggestions.append("• 确保所有括号（(), [], {}）匹配")
                suggestions.append("• 确保字符串引号闭合")
                suggestions.append("• 检查冒号是否在条件/循环/函数定义后正确使用")
                # 提取语法错误位置
                syn_m = re.search(r"line\s+(\d+)", exc_msg)
                if syn_m:
                    suggestions.append(f"• 语法错误在第 {syn_m.group(1)} 行附近")
                suggestions.append("")
                suggestions.append("  常见错误：")
                suggestions.append("    1. 段落定义后缺少冒号")
                suggestions.append("       ✓ 正确: 段落 测试 接收：")
                suggestions.append("       ✗ 错误: 段落 测试 接收")
                suggestions.append("    2. 条件语句后缺少冒号")
                suggestions.append("       ✓ 正确: 如果 x > 0：")
                suggestions.append("       ✗ 错误: 如果 x > 0")
                suggestions.append("    3. 字符串引号未闭合")
                suggestions.append("       ✓ 正确: 打印(\"hello\")")
                suggestions.append("       ✗ 错误: 打印(\"hello)")
            else:
                suggestions.append("• 检查缩进是否一致（光明使用 4 空格缩进）")
                suggestions.append("• 不要混用 Tab 和空格")
                suggestions.append("• 确保所有同级语句缩进级别相同")
                suggestions.append("")
                suggestions.append("  示例：")
                suggestions.append("    正确: 段落 测试：")
                suggestions.append("              打印(\"第一行\")")
                suggestions.append("              打印(\"第二行\")")
                suggestions.append("")
                suggestions.append("    错误: 段落 测试：")
                suggestions.append("              打印(\"第一行\")")
                suggestions.append("            打印(\"缩进不一致\")")
        elif exc_name == 'FileNotFoundError':
            suggestions.append("• 检查文件路径是否正确")
            suggestions.append("• 使用绝对路径或相对于当前目录的路径")
            suggestions.append("• 确认文件确实存在")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 内容 为 读取文件(\"data/文件.txt\")")
            suggestions.append("")
            suggestions.append("    错误: 设 内容 为 读取文件(\"不存在的文件.txt\")")
        elif exc_name == 'RecursionError':
            suggestions.append("• 检查函数是否存在无限递归")
            suggestions.append("• 增加递归终止条件")
            suggestions.append("• 考虑使用循环替代递归")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 段落 递归(n):")
            suggestions.append("              如 n <= 0:")
            suggestions.append("                  返回 0")
            suggestions.append("              返回 n 加 递归(n - 1)")
            suggestions.append("")
            suggestions.append("    错误: 段落 无限递归():")
            suggestions.append("              返回 无限递归()")
        elif exc_name == 'AssertionError':
            suggestions.append("• 检查断言条件是否正确")
            suggestions.append("• 确认前置条件满足")
            suggestions.append("• 如果断言总是失败，请修改条件或移除断言")
        elif exc_name == 'UnicodeDecodeError':
            suggestions.append("• 检查文件编码是否正确")
            suggestions.append("• 尝试指定编码格式（如 UTF-8）")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 内容 为 读取文件(\"文件.txt\", 编码=\"utf-8\")")
        elif exc_name == 'ImportError' or exc_name == 'ModuleNotFoundError':
            suggestions.append("• 检查模块名是否拼写正确")
            suggestions.append("• 确认模块已安装或在标准库路径中")
            suggestions.append("• 使用 导入 语句而不是直接使用模块名")
            # 提取模块名
            mod_m = re.search(r"(\w+)'?\s*(?:is not|No module named)", exc_msg)
            if mod_m:
                mod_name = mod_m.group(1)
                suggestions.append(f"• 模块 '{mod_name}' 未找到")
                similar = _find_similar_names(mod_name, {'数学', '随机', '时间', '文件', '系统', 'JSON', '字符串', '列表', '字典', 'os', 'sys', 'json', 'math', 'random', 'time', 'datetime', 're', 'pathlib'})
                if similar:
                    suggestions.append(f"• 您是不是想导入: {', '.join(similar)}？")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 导入 数学")
            suggestions.append("          打印(数学.平方根(16))")
            suggestions.append("")
            suggestions.append("    正确: 从 数学 导入 阶乘")
            suggestions.append("          打印(阶乘(5))")
        elif exc_name == 'PermissionError':
            suggestions.append("• 检查文件或目录的访问权限")
            suggestions.append("• 以管理员/超级用户身份运行程序")
            suggestions.append("• 确认目标路径有写入权限")
        elif exc_name == 'TimeoutError':
            suggestions.append("• 检查网络连接是否正常")
            suggestions.append("• 增加超时时间")
            suggestions.append("• 检查目标服务器是否可达")
        else:
            suggestions.append(f"• 详细错误信息: {exc_msg}")
            suggestions.append("• 可以查阅光明文档: docs/")
            suggestions.append("• 访问光明官网获取更多帮助")

        suggestions.append("")
        suggestions.append("📖 更多帮助：")
        suggestions.append("• 光明文档: https://docs.light-lang.org")
        suggestions.append("• 示例代码: examples/")
        suggestions.append("• 常见问题: docs/FAQ.md")

        suggestions.append("")
        return suggestions


def run_with_friendly_error(code: str, source: str = '', source_name: str = '<光明代码>') -> int:
    """执行代码并以友好的方式报告错误

    Args:
        code: 要执行的 Python 代码
        source: 光明源代码（用于上下文显示）
        source_name: 源代码名称

    Returns:
        退出码 (0=正常, 1=错误)
    """
    formatter = LightErrorFormatter(source, source_name)
    try:
        exec(code, {'__name__': '__main__', '__file__': source_name})
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    except Exception:
        exc_type, exc_value, exc_tb = sys.exc_info()
        print(formatter.format_exception(exc_type, exc_value, exc_tb),
              file=sys.stderr, flush=True)
        return 1


def format_runtime_error(source: str, exc_type=None, exc_value=None, exc_tb=None) -> str:
    """便捷函数：格式化运行时错误

    Args:
        source: 光明源代码
        exc_type, exc_value, exc_tb: 异常信息，默认为 sys.exc_info()
    """
    formatter = LightErrorFormatter(source)
    return formatter.format_exception(exc_type, exc_value, exc_tb)


# 中文异常类型映射（供 raise 用）
LIGHT_EXCEPTION_MAP = {
    'NameError': '变量未定义错误',
    'TypeError': '类型错误',
    'ValueError': '值错误',
    'IndexError': '索引越界错误',
    'KeyError': '键不存在错误',
    'AttributeError': '属性不存在错误',
    'ZeroDivisionError': '除零错误',
    'IOError': '输入输出错误',
    'FileNotFoundError': '文件未找到错误',
    'RuntimeError': '运行时错误',
}


if __name__ == '__main__':
    # 测试
    source = '''设 x 为 10
设 y 为 0
设 z 为 x / y
打印 z
'''
    try:
        exec("x = 10\ny = 0\nz = x / y\nprint(z)")
    except Exception:
        print(format_runtime_error(source))
