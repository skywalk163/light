"""给 bootstrap_level5.light 补充缺失的 `结束` 标记

基于缩进分析，为每个 段落/如果/当/遍历/尝试 块添加结束标记。
Level 5 源文件使用 2 空格缩进。

关键规则:
1. 当缩进减少时，关闭所有缩进 >= 当前行缩进的块
2. `否则` 不创建新块，但关闭所有缩进 > 否则缩进的块（否则内的块）
3. 已有的 `结束` 标记保留，关闭对应的块
4. 文件末尾关闭所有剩余块
"""
import re

# 读取源文件
with open('bootstrap/bootstrap_level5.light', 'r', encoding='utf-8') as f:
    text = f.read()
    lines = text.split('\n')

# 块开始关键字
BLOCK_KEYWORDS = {'段落', '段', '如果', '当', '遍历', '尝试'}

result = []
block_stack = []  # [(indent, keyword)]

for i, line in enumerate(lines):
    stripped = line.rstrip()
    if i == len(lines) - 1 and stripped == '':
        continue  # 跳过文件末尾空行
    
    # 空行或注释行 - 直接保留
    if stripped.strip() == '':
        result.append(line)
        continue
    if stripped.strip().startswith('#'):
        result.append(line)
        continue
    
    # 计算缩进
    indent = len(stripped) - len(stripped.lstrip(' '))
    content = stripped.strip()
    
    # 提取第一个词
    parts = content.split()
    first_word = parts[0].rstrip('：') if parts else ''
    is_else = content.startswith('否则')
    is_end = content.startswith('结束')
    
    # ===== 处理已存在的 "结束" =====
    if is_end:
        if block_stack:
            block_indent = block_stack[-1][0]
            result.append(line)
            block_stack.pop()
        else:
            result.append(line)
        continue
    
    # ===== 处理 "否则" =====
    if is_else:
        # 否则: 关闭所有缩进 > 否则缩进的块
        while block_stack:
            block_indent = block_stack[-1][0]
            if indent < block_indent:  # 严格小于: 否则内的块
                result.append(' ' * block_indent + '结束')
                block_stack.pop()
            else:
                break
        result.append(line)
        continue
    
    # ===== 普通行: 关闭所有缩进 >= 当前行缩进的块 =====
    while block_stack:
        block_indent = block_stack[-1][0]
        if indent <= block_indent:
            result.append(' ' * block_indent + '结束')
            block_stack.pop()
        else:
            break
    
    # ===== 检查当前行是否开始新块 =====
    if first_word in BLOCK_KEYWORDS:
        block_stack.append((indent, first_word))
    
    result.append(line)

# 关闭所有剩余的块
while block_stack:
    block_indent = block_stack.pop()[0]
    result.append(' ' * block_indent + '结束')

# 写入文件
output = '\n'.join(result) + '\n'
with open('bootstrap/bootstrap_level5.light', 'w', encoding='utf-8') as f:
    f.write(output)

# 统计
orig_lines = len(lines)
new_lines = len(result)
print(f"原文件: {orig_lines} 行")
print(f"新文件: {new_lines} 行")
print(f"新增行: {new_lines - orig_lines} 行")
print(f"结束标记总数: {output.count('结束')}")