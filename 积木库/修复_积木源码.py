# -*- coding: utf-8 -*-
"""
修复光明积木 .light 源码中的语法缺陷
=====================================
修复自动生成的积木模板中的各种语法错误。
"""

import os, re

_HERE = os.path.dirname(os.path.abspath(__file__))


def 修复_文件(路径, 替换规则):
    """读取文件，执行替换规则，写回"""
    with open(路径, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content
    for 旧, 新 in 替换规则:
        if 旧 in content:
            content = content.replace(旧, 新)
    if content != original:
        with open(路径, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def 修复_数据领域():
    """修复 数据/ 目录下的缺失运算符问题
    
    模式: 设 结果 为 结果 列表[i] 加 列表[i]
    → 设 结果 为 结果 加 列表[i]
    """
    目录 = os.path.join(_HERE, '数据')
    计数 = 0
    for fname in os.listdir(目录):
        if not fname.endswith('.light'):
            continue
        路径 = os.path.join(目录, fname)
        with open(路径, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        changed = False
        for line in lines:
            # 修复: 结果 列表[i] OP 列表[i] → 结果 OP 列表[i]
            # 先处理复杂的模式：结果 列表[i] 乘 列表[i] 加 列表[i] → 结果 加 列表[i] 乘 列表[i]
            # 再处理简单模式：结果 列表[i] 加 列表[i] → 结果 加 列表[i]
            new_line = line
            # 模式1: 结果 列表[i] 乘 列表[i] 乘 列表[i] 加 列表[i] → 结果 加 列表[i] 乘 列表[i] 乘 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+列表\[i\]\s+(乘\s+列表\[i\](\s+乘\s+列表\[i\])*)\s+加\s+列表\[i\]',
                r'设 结果 为 结果 加 列表[i] \1',
                new_line
            )
            # 模式2: 结果 列表[i] 乘 列表[i] 加 列表[i] → 结果 加 列表[i] 乘 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+列表\[i\]\s+乘\s+列表\[i\]\s+加\s+列表\[i\]',
                r'设 结果 为 结果 加 列表[i] 乘 列表[i]',
                new_line
            )
            # 模式3: 结果 列表[i] 乘 列表[i] → 结果 乘 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+列表\[i\]\s+乘\s+列表\[i\]',
                r'设 结果 为 结果 乘 列表[i]',
                new_line
            )
            # 模式4: 结果 列表[i] 加 列表[i] → 结果 加 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+列表\[i\]\s+加\s+列表\[i\]',
                r'设 结果 为 结果 加 列表[i]',
                new_line
            )
            # 模式5: 结果 1 除 列表[i] 加 列表[i] → 结果 加 1/列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+1\s+除\s+列表\[i\]\s+加\s+列表\[i\]',
                r'设 结果 为 结果 加 1 除 列表[i]',
                new_line
            )
            # 模式6: 结果 列表[i] 列表[i]（无运算符）→ 结果 乘 列表[i]（累积积）
            m = re.match(r'^\s*设\s+结果\s+为\s+结果\s+列表\[i\]\s+列表\[i\]\s*$', new_line)
            if m:
                # 判断上下文：看文件名包含"累积"还是"累积差"
                base = os.path.splitext(fname)[0]
                if '差' in base:
                    new_line = '    设 结果 为 结果 减 列表[i]\n'
                elif '积' in base:
                    new_line = '    设 结果 为 结果 乘 列表[i]\n'
                else:
                    new_line = '    设 结果 为 结果 加 列表[i]\n'
            
            # 模式7: 结果 列表[i] 数 列表[i] → 结果 数 列表[i]
            m = re.match(r'^\s*设\s+结果\s+为\s+结果\s+(\w+)\s+列表\[i\]\s*$', new_line)
            if m:
                op = m.group(1)
                # 需要根据文件名判断正确操作
                base = os.path.splitext(fname)[0]
                if '最大值' in base or '最大' in base:
                    # 求最大值索引的特殊处理
                    pass  # 走三元表达式逻辑
                else:
                    new_line = f'    设 结果 为 结果 {op} 列表[i]\n'

            # 模式8: 结果 结果.追加(0) 列表[i] → 结果.追加(列表[i])
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+结果\.追加\(0\)\s+列表\[i\]',
                r'结果.追加(列表[i])',
                new_line
            )
            
            # 模式9: 结果 数 列表[i] → 结果 加 列表[i]（求绝对值特殊）
            if re.match(r'^\s*设\s+结果\s+为\s+结果\s+数\s+列表\[i\]\s*$', new_line):
                new_line = '    设 结果 为 结果 加 列表[i]\n'

            # 模式10: 求绝对值.light 的初始值错误
            # 设 结果 为 如果 列表[i] 大于 0 则 列表[i] 否则 (0 减 列表[i])
            m = re.match(r'^\s*设\s+结果\s+为\s+如果\s+.+?大于\s+0\s+则\s+.+?否则\s+.+', new_line)
            if m:
                new_line = '    设 结果 为 []\n'

            # 模式11: 求最大值索引/求最小值索引 中的三元表达式错误
            # 结果 如果 列表[i] 大于 列表[结果] 则 i 否则 结果 列表[i]
            # → 如果 列表[i] 大于 列表[结果] 则 i 否则 结果
            m = re.match(
                r'^\s*设\s+结果\s+为\s+结果\s+如果\s+(列表\[i\]\s+大于\s+列表\[结果\])\s+则\s+(\w+)\s+否则\s+结果\s+列表\[i\]\s*$',
                new_line
            )
            if m:
                new_line = f'    设 结果 为 如果 {m.group(1)} 则 {m.group(2)} 否则 结果\n'
            m = re.match(
                r'^\s*设\s+结果\s+为\s+结果\s+如果\s+(列表\[i\]\s+小于\s+列表\[结果\])\s+则\s+(\w+)\s+否则\s+结果\s+列表\[i\]\s*$',
                new_line
            )
            if m:
                new_line = f'    设 结果 为 如果 {m.group(1)} 则 {m.group(2)} 否则 结果\n'

            # 模式12: 求前缀和/求后缀和: 设 结果 为 结果 结果.追加(0) 列表[i] → 结果.追加(列表[i])
            m = re.match(
                r'^\s*设\s+结果\s+为\s+结果\s+结果\.追加\(0\)\s+列表\[i\]\s*$',
                new_line
            )
            if m:
                new_line = '    结果.追加(列表[i])\n'

            if new_line != line:
                changed = True
            new_lines.append(new_line)
        
        if changed:
            with open(路径, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"  修复: {fname}")
            计数 += 1
    return 计数


def 修复_统计领域():
    """修复 统计/ 目录下的缺失运算符问题"""
    目录 = os.path.join(_HERE, '统计')
    计数 = 0
    for fname in os.listdir(目录):
        if not fname.endswith('.light'):
            continue
        路径 = os.path.join(目录, fname)
        with open(路径, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        changed = False
        for line in lines:
            new_line = line
            
            # 模式: 结果 列表[i] 乘 列表[i] 乘 列表[i] 乘 列表[i] 加 列表[i]
            # → 结果 加 列表[i] 乘 列表[i] 乘 列表[i] 乘 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+列表\[i\]\s+(乘\s+列表\[i\](\s+乘\s+列表\[i\])*)\s+加\s+列表\[i\]',
                r'设 结果 为 结果 加 列表[i] \1',
                new_line
            )
            # 模式: 结果 列表[i] 乘 列表2[i] 加 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+列表\[i\]\s+乘\s+列表2\[i\]\s+加\s+列表\[i\]',
                r'设 结果 为 结果 加 列表[i] 乘 列表2[i]',
                new_line
            )
            # 模式: 结果 (列表[i] 减 均值) 乘 (列表2[i] 减 均值2) 加 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+\((列表\[i\]\s+减\s+均值)\)\s+乘\s+\((列表2\[i\]\s+减\s+均值2)\)\s+加\s+列表\[i\]',
                r'设 结果 为 结果 加 (\1) 乘 (\2)',
                new_line
            )
            # 模式: 结果 列表[i] 乘 列表[i] 加 列表[i] → 结果 加 列表[i] 乘 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+列表\[i\]\s+乘\s+列表\[i\]\s+加\s+列表\[i\]',
                r'设 结果 为 结果 加 列表[i] 乘 列表[i]',
                new_line
            )
            # 模式: 结果 列表[i] 乘 列表[i] → 结果 乘 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+列表\[i\]\s+乘\s+列表\[i\]',
                r'设 结果 为 结果 乘 列表[i]',
                new_line
            )
            # 模式: 结果 列表[i] 加 列表[i] → 结果 加 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+列表\[i\]\s+加\s+列表\[i\]',
                r'设 结果 为 结果 加 列表[i]',
                new_line
            )
            # 模式: 结果 长度(列表) 减 1 列表[i] → 结果 加 (长度(列表) 减 1)
            m = re.match(
                r'^\s*设\s+结果\s+为\s+结果\s+长度\(列表\)\s+减\s+1\s+列表\[i\]\s*$',
                new_line
            )
            if m:
                new_line = '    设 结果 为 结果 加 (长度(列表) 减 1)\n'
            
            # 模式: 结果 如果 列表[i] 大于 0 且 列表[i] 小于 100 则 1 加 0 否则 0 加 列表[i]
            # → 如果 列表[i] 大于 0 且 列表[i] 小于 100 则 结果 加 1 否则 结果
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+如果\s+(.+?)\s+则\s+1\s+加\s+0\s+否则\s+0\s+加\s+列表\[i\]',
                r'如果 \1 则 结果 加 1 否则 结果',
                new_line
            )
            # 模式: 结果 如果 列表[i] 小于 1 则 1 加 0 否则 0 加 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+如果\s+(.+?)\s+则\s+1\s+加\s+0\s+否则\s+0\s+加\s+列表\[i\]',
                r'如果 \1 则 结果 加 1 否则 结果',
                new_line
            )
            # 模式: 结果 如果 列表[i] 不为 0 则 1 加 0 否则 0 加 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+如果\s+(.+?)\s+则\s+1\s+加\s+0\s+否则\s+0\s+加\s+列表\[i\]',
                r'如果 \1 则 结果 加 1 否则 结果',
                new_line
            )
            # 模式: 结果 如果 列表[i] 等于 0 则 1 加 0 否则 0 加 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+如果\s+(.+?)\s+则\s+1\s+加\s+0\s+否则\s+0\s+加\s+列表\[i\]',
                r'如果 \1 则 结果 加 1 否则 结果',
                new_line
            )
            # 模式: 结果 如果 列表[i] 模 2 等于 0 则 1 加 0 否则 0 加 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+如果\s+(.+?)\s+则\s+1\s+加\s+0\s+否则\s+0\s+加\s+列表\[i\]',
                r'如果 \1 则 结果 加 1 否则 结果',
                new_line
            )
            # 模式: 结果 如果 列表[i] 模 2 不等于 0 则 1 加 0 否则 0 加 列表[i]
            new_line = re.sub(
                r'设\s+结果\s+为\s+结果\s+如果\s+(.+?)\s+则\s+1\s+加\s+0\s+否则\s+0\s+加\s+列表\[i\]',
                r'如果 \1 则 结果 加 1 否则 结果',
                new_line
            )
            
            if new_line != line:
                changed = True
            new_lines.append(new_line)
        
        if changed:
            with open(路径, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"  修复: {fname}")
            计数 += 1
    return 计数


def 修复_逻辑领域():
    """修复 逻辑/ 目录下的重复变量问题
    
    模式: 返回 甲 甲 且 乙 乙 → 返回 甲 且 乙
    """
    目录 = os.path.join(_HERE, '逻辑')
    计数 = 0
    for fname in os.listdir(目录):
        if not fname.endswith('.light'):
            continue
        路径 = os.path.join(目录, fname)
        with open(路径, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        # 修复: 返回 甲 甲 且 乙 乙 → 返回 甲 且 乙
        content = re.sub(r'返回\s+(\w+)\s+\1\s+(且|或|非|等于|不等于|大于|小于|大于等于|小于等于)\s+(\w+)\s+\3', r'返回 \1 \2 \3', content)
        # 修复: 返回 甲 非 甲 乙 → 返回 非 甲
        content = re.sub(r'返回\s+(\w+)\s+非\s+\1\s+(\w+)', r'返回 非 \1', content)
        
        if content != original:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  修复: {fname}")
            计数 += 1
    return 计数


def 修复_数组领域():
    """修复 数组/ 目录下的三元表达式问题
    
    模式: 结果.追加(表甲[i] 如果 大于 表乙[i])
    → 结果.追加(如果 表甲[i] 大于 表乙[i] 则 表甲[i] 否则 表乙[i])
    """
    目录 = os.path.join(_HERE, '数组')
    计数 = 0
    for fname in os.listdir(目录):
        if not fname.endswith('.light'):
            continue
        路径 = os.path.join(目录, fname)
        with open(路径, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        # 修复: 结果.追加(表甲[i] 如果 大于 表乙[i])
        # → 结果.追加(如果 表甲[i] 大于 表乙[i] 则 表甲[i] 否则 表乙[i])
        content = re.sub(
            r'结果\.追加\((\w+)\[i\]\s+如果\s+大于\s+(\w+)\[i\]\)',
            r'结果.追加(如果 \1[i] 大于 \2[i] 则 \1[i] 否则 \2[i])',
            content
        )
        content = re.sub(
            r'结果\.追加\((\w+)\[i\]\s+如果\s+小于\s+(\w+)\[i\]\)',
            r'结果.追加(如果 \1[i] 小于 \2[i] 则 \1[i] 否则 \2[i])',
            content
        )
        
        if content != original:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  修复: {fname}")
            计数 += 1
    return 计数


def 修复_文本领域():
    """修复 文本/ 目录下的参数名错误
    
    模式: 文本.切分(模式) → 输入.切分(模式)
    模式: 文本.切分(' ') → 输入.切分(' ')
    """
    目录 = os.path.join(_HERE, '文本')
    计数 = 0
    for fname in ['文本_按正则切分.light', '文本_单词统计.light']:
        路径 = os.path.join(目录, fname)
        if not os.path.isfile(路径):
            continue
        with open(路径, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        # 修复: 文本.切分 → 输入.切分
        content = content.replace('文本.切分', '输入.切分')
        # 修复: 文本.长度() → 输入.长度()（虽然会被翻译器处理，但保持语义一致）
        content = content.replace('文本.长度()', '输入.长度()')
        
        if content != original:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  修复: {fname}")
            计数 += 1
    return 计数


def 修复_聚合_工具():
    """修复 工具/聚合_工具_3项.light 中的参数缺失问题"""
    路径 = os.path.join(_HERE, '工具', '聚合_工具_3项.light')
    if not os.path.isfile(路径):
        return 0
    
    with open(路径, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    # 修复: 分页(总数) → 分页(总数, 10)（默认每页10条）
    content = content.replace('分页(总数)', '分页(总数, 10)')
    # 修复: 余(总数) → 余(总数, 2)（默认模2）
    content = content.replace('余(总数)', '余(总数, 2)')
    # 修复: 乘方(总数) → 乘方(总数, 2)（默认平方）
    content = content.replace('乘方(总数)', '乘方(总数, 2)')
    
    if content != original:
        with open(路径, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  修复: 聚合_工具_3项.light")
        return 1
    return 0


def 修复_集合领域():
    """修复 集合/ 目录下的空格分隔运算符问题
    
    模式: 大于 等于 → 大于等于
    """
    目录 = os.path.join(_HERE, '集合')
    计数 = 0
    for fname in os.listdir(目录):
        if not fname.endswith('.light'):
            continue
        路径 = os.path.join(目录, fname)
        with open(路径, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        content = content.replace('大于 等于', '大于等于')
        content = content.replace('小于 等于', '小于等于')
        
        if content != original:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  修复: {fname}")
            计数 += 1
    return 计数


def 修复_验证领域():
    """修复 验证/ 目录下的空格分隔运算符问题"""
    目录 = os.path.join(_HERE, '验证')
    计数 = 0
    for fname in os.listdir(目录):
        if not fname.endswith('.light'):
            continue
        路径 = os.path.join(目录, fname)
        with open(路径, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        content = content.replace('大于 等于', '大于等于')
        content = content.replace('小于 等于', '小于等于')
        
        if content != original:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  修复: {fname}")
            计数 += 1
    return 计数


def main():
    print("=" * 50)
    print("开始修复光明积木 .light 源码...")
    print("=" * 50)
    
    n = 修复_数据领域()
    print(f"[数据] 修复 {n} 个文件")
    
    n = 修复_统计领域()
    print(f"[统计] 修复 {n} 个文件")
    
    n = 修复_逻辑领域()
    print(f"[逻辑] 修复 {n} 个文件")
    
    n = 修复_数组领域()
    print(f"[数组] 修复 {n} 个文件")
    
    n = 修复_文本领域()
    print(f"[文本] 修复 {n} 个文件")
    
    n = 修复_聚合_工具()
    print(f"[工具] 修复 {n} 个文件")
    
    n = 修复_集合领域()
    print(f"[集合] 修复 {n} 个文件")
    
    n = 修复_验证领域()
    print(f"[验证] 修复 {n} 个文件")
    
    print("=" * 50)
    print("源码修复完成!")


if __name__ == '__main__':
    main()