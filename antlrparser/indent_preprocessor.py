"""
v3 纯缩进语法预处理器

将 v3 纯缩进语法（类似 Python）转换为带"结束"标记的语法（ANTLR 后端需要）。

输入示例：
    段落 加法 接收 a, b：
        返回 a 加 b

输出示例：
    段落 加法 接收 a, b：
        返回 a 加 b
    结束

支持的块：
- 如果 / 否则如果 / 否则
- 当 / 遍历
- 段落 / 类 / 接口 / 构造
- 尝试 / 捕获 / 最终
- 匹配 / 用例
- 异步作用域 / 异步段落
"""

import re


def preprocess_v3_syntax(source: str) -> str:
    """
    将 v3 纯缩进语法转换为带"结束"标记的语法。

    规则：
    1. 跟踪缩进级别
    2. 每遇到一个块开始（以冒号结尾的行），压栈
    3. 当下一行缩进减少时，生成相应数量的"结束"
    4. 空行和注释行不影响缩进计算

    Args:
        source: v3 纯缩进语法源码

    Returns:
        带"结束"标记的源码（兼容 ANTLR 后端）
    """
    lines = source.split('\n')
    result = []
    indent_stack = [0]
    block_starts = []  # 每个缩进级别对应的"结束"关键字

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 空行或注释行：保持原样，不改变缩进栈
        if not stripped or stripped.startswith('#') or stripped.startswith('//'):
            result.append(line)
            i += 1
            continue

        # 计算当前行缩进（空格数）
        indent = _count_indent(line)

        # 处理缩进减少：生成"结束"
        while indent < indent_stack[-1]:
            indent_stack.pop()
            prev_indent = indent_stack[-1]
            # 用前一级缩进的空格数生成"结束"
            end_line = ' ' * prev_indent + '结束'
            result.append(end_line)
            if block_starts:
                block_starts.pop()

        # 处理缩进增加或同级
        if indent > indent_stack[-1]:
            indent_stack.append(indent)
        elif indent < indent_stack[-1]:
            # 不应该发生（上面的 while 已经处理了）
            indent_stack.append(indent)

        # 添加当前行
        result.append(line)

        # 检查是否是块开始行（以冒号结尾）
        if _is_block_start(stripped):
            # 块开始行后面会有 INDENT，但我们需要确保下一行缩进正确
            # 当下一行缩进减少时会生成"结束"
            pass

        i += 1

    # 文件末尾，生成所有剩余的"结束"
    while len(indent_stack) > 1:
        indent_stack.pop()
        prev_indent = indent_stack[-1]
        end_line = ' ' * prev_indent + '结束'
        result.append(end_line)

    return '\n'.join(result)


def _count_indent(line: str) -> int:
    """计算行首缩进空格数"""
    count = 0
    for ch in line:
        if ch == ' ':
            count += 1
        elif ch == '\t':
            count += 4  # 假设一个 tab 等于 4 个空格
        else:
            break
    return count


def _is_block_start(stripped_line: str) -> bool:
    """判断一行是否是块的开始（以冒号结尾）"""
    # 去掉行尾注释后再检查
    code_part = stripped_line
    for comment_prefix in ['#', '//']:
        idx = code_part.find(comment_prefix)
        if idx > 0:
            code_part = code_part[:idx].strip()
            break

    return code_part.endswith('：') or code_part.endswith(':')


# 测试用
if __name__ == '__main__':
    test_code = '''段落 加法 接收 a, b：
    返回 a 加 b

定义 x 等于 10

如果 x 大于 5：
    打印 "大"
否则：
    打印 "小"

当 x 大于 0：
    x 等于 x 减 1
    打印 x
'''
    print(preprocess_v3_syntax(test_code))
