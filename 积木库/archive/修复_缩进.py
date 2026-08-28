# -*- coding: utf-8 -*-
"""
修复光明积木 .light 源码中的缩进问题
=====================================
修复自动生成的积木模板中 while 循环体缺少缩进的问题。
"""

import os, re

_HERE = os.path.dirname(os.path.abspath(__file__))


def 修复_缩进(目录):
    """修复目录下所有 .light 文件中 while 循环体缺少缩进的问题
    
    模式: 当 ...：  (4 spaces)
          设 结果 为 ...  (4 spaces - WRONG, should be 8 spaces)
    → 修正为 8 spaces
    """
    计数 = 0
    for fname in os.listdir(目录):
        if not fname.endswith('.light'):
            continue
        路径 = os.path.join(目录, fname)
        with open(路径, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            # 检测 while 行：当 ...  (4 spaces indent)
            if stripped.startswith('当 ') and stripped.endswith('：'):
                new_lines.append(line)
                i += 1
                # 检查下一行是否是 while 体（应该比 while 多 4 spaces）
                if i < len(lines):
                    next_line = lines[i]
                    next_stripped = next_line.strip()
                    # 检查 while 体是否为空
                    if not next_stripped:
                        new_lines.append(next_line)
                        i += 1
                    else:
                        # 检查下一行的缩进
                        current_indent = len(line) - len(line.lstrip())
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent <= current_indent:
                            # 下一行缩进不足，增加 4 spaces
                            new_lines.append(' ' * (current_indent + 4) + next_stripped)
                            i += 1
                        else:
                            new_lines.append(next_line)
                            i += 1
            else:
                new_lines.append(line)
                i += 1
        
        new_content = '\n'.join(new_lines)
        if new_content != original:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  修复缩进: {fname}")
            计数 += 1
    return 计数


def main():
    print("=" * 50)
    print("开始修复缩进问题...")
    print("=" * 50)
    
    total = 0
    for 领域 in ['数据', '统计', '工具', '几何', '数学', '数组', '文本', '时间', '验证', '集合', '颜色', '逻辑', '财务', '密码']:
        目录 = os.path.join(_HERE, 领域)
        if os.path.isdir(目录):
            n = 修复_缩进(目录)
            if n:
                print(f"  [{领域}] 修复 {n} 个文件")
                total += n
    
    print(f"总共修复 {total} 个文件的缩进")
    print("=" * 50)


if __name__ == '__main__':
    main()