"""将 bootstrap_level5.light 从 Level 4/5 语法转换为 Level 6/7 语法

转换规则：
1. 移除 `结束` 关键词行（块结束标记）
2. 移除 `：`（块开始标记）
3. 移除 `。`（语句结束标记）
4. 2空格缩进 → 4空格缩进
"""
import re

with open('bootstrap/bootstrap_level5.light', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out_lines = []
removed_count = 0

for i, line in enumerate(lines):
    # 检查是否是纯 `结束` 行（含可选空格和注释）
    stripped = line.strip()
    if re.match(r'^结束\s*$', stripped):
        # 跳过 `结束` 行
        removed_count += 1
        continue

    # 移除行尾的 `：`（块开始标记）
    # 但保留非行尾的 `：`（如字符串内的 `：`）
    if line.rstrip().endswith('：'):
        # 找到最后一个 `：` 的位置
        # 只移除行尾的 `：`
        line = line.rstrip()[:-1] + '\n'

    # 移除 `。`（语句结束标记）
    # 注意：`。` 可能出现在行尾或作为分隔符
    # 只移除作为语句结束标记的 `。`
    # 检查行尾是否有 `。`
    if line.rstrip().endswith('。'):
        # 去掉行尾的 `。`
        line = line.rstrip()[:-1] + '\n'

    # 将 2空格缩进转换为 4空格缩进
    # 计算前导空格数（只统计空格和制表符，不统计换行符）
    leading_spaces = len(line) - len(line.lstrip(' \t'))
    if leading_spaces > 0:
        # 2空格 → 4空格
        line = ' ' * (leading_spaces * 2) + line.lstrip(' \t')

    out_lines.append(line)

# 写输出文件
output = ''.join(out_lines)
with open('bootstrap/bootstrap_level6.light', 'w', encoding='utf-8') as f:
    f.write(output)

# 添加头部注释
header = "# 光明自举编译器 - Level 6\n"
header += "# 无空格分词 + 纯缩进语法\n"
header += "# 从 bootstrap_level5.light 转换而来\n\n"
output = header + output.lstrip('\n')

with open('bootstrap/bootstrap_level6.light', 'w', encoding='utf-8') as f:
    f.write(output)

print(f"转换完成!")
print(f"  移除 {removed_count} 个 `结束` 行")
print(f"  输出: bootstrap/bootstrap_level6.light")
print(f"  行数: {len(out_lines)}")