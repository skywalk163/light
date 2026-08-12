# -*- coding: utf-8 -*-
"""批量修复第1批领域（数据/数学/统计/排序/搜索）的积木块问题。

修复类型：
  1. 三元表达式在 return 语句中：`返回 如果 条件 则 v1 否则 v2` → if/else + return
  2. .反转() 调用：`列表.反转()` → 循环反向遍历
  3. 三元表达式在赋值语句中（漏网之鱼）：`设 x 为 如果 条件 则 v1 否则 v2`
"""
import json
import os
import re
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, '..'))
V5_DIR = os.path.join(_HERE, 'blocks_v5')
LIGHT_CLI = os.path.join(_REPO, 'cli', 'light.py')

# 第1批修复领域
目标领域 = ['数据', '数学', '统计', '排序', '搜索']

# 模式：返回中的三元表达式 — 返回 如果 条件 则 v1 否则 v2
返回三元模式 = re.compile(
    r'^(?P<indent>\s*)返回\s+如果\s+(?P<cond>.+?)\s+则\s+(?P<val1>.+?)\s+否则\s+(?P<val2>.+?)$'
)

# 模式：赋值中的三元表达式
设三元模式 = re.compile(
    r'^(?P<indent>\s*)设\s+(?P<var>\S+)\s+为\s+'
    r'如果\s+(?P<cond>.+?)\s+则\s+(?P<val1>.+?)\s+否则\s+(?P<val2>.+?)$'
)

# 模式：.反转() 调用 — 列表.反转()
反转模式 = re.compile(r'(\w+)\.反转\(\)')

# 模式：追加(.反转()) — 结果.追加(列表.反转())
追加反转模式 = re.compile(r'(\w+)\.追加\((\w+)\.反转\(\)\)')


def 语法检查(路径):
    try:
        r = subprocess.run(
            [sys.executable, LIGHT_CLI, 'check', 路径],
            capture_output=True, text=True, timeout=10,
            cwd=_REPO
        )
        return r.returncode == 0, (r.stderr or r.stdout or '').strip()[:200]
    except subprocess.TimeoutExpired:
        return False, '超时 (10s)'
    except Exception as e:
        return False, str(e)


def 修复_返回三元表达式(内容):
    """修复返回中的三元表达式。
    
    输入：
        返回 如果 条件 则 v1 否则 v2
    输出：
        如果 条件：
            返回 v1
        否则：
            返回 v2
    """
    行们 = 内容.split('\n')
    新行们 = []
    修改 = False
    for 行 in 行们:
        m = 返回三元模式.match(行)
        if m:
            indent = m.group('indent')
            cond = m.group('cond').strip()
            val1 = m.group('val1').strip()
            val2 = m.group('val2').strip()
            新行们.append(f'{indent}如果 {cond}：')
            新行们.append(f'{indent}    返回 {val1}')
            新行们.append(f'{indent}否则：')
            新行们.append(f'{indent}    返回 {val2}')
            修改 = True
        else:
            新行们.append(行)
    return '\n'.join(新行们), 修改


def 修复_设三元表达式(内容):
    """修复赋值语句中的三元表达式（漏网之鱼）。
    
    输入：
        设 x 为 如果 条件 则 v1 否则 v2
    输出：
        如果 条件：
            设 x 为 v1
        否则：
            设 x 为 v2
    """
    行们 = 内容.split('\n')
    新行们 = []
    修改 = False
    for 行 in 行们:
        m = 设三元模式.match(行)
        if m:
            indent = m.group('indent')
            var = m.group('var')
            cond = m.group('cond').strip()
            val1 = m.group('val1').strip()
            val2 = m.group('val2').strip()
            新行们.append(f'{indent}如果 {cond}：')
            新行们.append(f'{indent}    设 {var} 为 {val1}')
            新行们.append(f'{indent}否则：')
            新行们.append(f'{indent}    设 {var} 为 {val2}')
            修改 = True
        else:
            新行们.append(行)
    return '\n'.join(新行们), 修改


def 修复_反转(内容):
    """修复 .反转() 调用。
    
    输入：
        结果.追加(列表.反转())  # 或 列表.反转()
    输出：
        # 循环反向遍历追加
        设 i 为 长度(列表) 减 1
        当 i 大于等于 0：
            结果.追加(列表[i])
            设 i 为 i 减 1
    """
    行们 = 内容.split('\n')
    新行们 = []
    修改 = False
    for 行 in 行们:
        m = 追加反转模式.search(行)
        if m:
            # 结果.追加(列表.反转()) → 循环反向遍历
            result_var = m.group(1)
            list_var = m.group(2)
            indent = '    '  # 假设缩进
            # 取行缩进
            leading = 行[:len(行) - len(行.lstrip())]
            新行们.append(f'{leading}# 修正：循环反向遍历')
            新行们.append(f'{leading}设 i 为 长度({list_var}) 减 1')
            新行们.append(f'{leading}当 i 大于等于 0：')
            新行们.append(f'{leading}    {result_var}.追加({list_var}[i])')
            新行们.append(f'{leading}    设 i 为 i 减 1')
            修改 = True
        else:
            m2 = 反转模式.search(行)
            if m2 and '.追加' not in 行:
                # 纯 列表.反转() 调用
                var = m2.group(1)
                leading = 行[:len(行) - len(行.lstrip())]
                新行们.append(f'{leading}# 修正：循环反向遍历')
                新行们.append(f'{leading}设 结果 为 []')
                新行们.append(f'{leading}设 i 为 长度({var}) 减 1')
                新行们.append(f'{leading}当 i 大于等于 0：')
                新行们.append(f'{leading}    结果.追加({var}[i])')
                新行们.append(f'{leading}    设 i 为 i 减 1')
                修改 = True
            else:
                新行们.append(行)
    return '\n'.join(新行们), 修改


def 修复文件(路径):
    """对单个文件应用所有修复。"""
    修改 = False
    with open(路径, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1) 修复返回中的三元表达式
    content, m1 = 修复_返回三元表达式(content)
    修改 = 修改 or m1

    # 2) 修复赋值中的三元表达式
    content, m2 = 修复_设三元表达式(content)
    修改 = 修改 or m2

    # 3) 修复 .反转()
    content, m3 = 修复_反转(content)
    修改 = 修改 or m3

    if 修改:
        with open(路径, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def 扫描领域(领域):
    """扫描指定领域的所有块，返回需要修复的文件列表。"""
    需修复 = []
    已修复 = []
    失败 = []
    跳过 = []
    
    领域目录 = os.path.join(V5_DIR, 领域)
    if not os.path.isdir(领域目录):
        return [], [], [], []
    
    for fname in sorted(os.listdir(领域目录)):
        if not fname.endswith('.light'):
            continue
        路径 = os.path.join(领域目录, fname)
        
        # 先检查当前语法
        ok, _ = 语法检查(路径)
        if ok:
            跳过.append(fname)
            continue
        
        需修复.append(fname)
    
    return 需修复, 已修复, 失败, 跳过


def 修复并验证(领域, fname):
    """修复单个文件并验证。"""
    路径 = os.path.join(V5_DIR, 领域, fname)
    
    # 备份
    backup = None
    with open(路径, 'r', encoding='utf-8') as f:
        backup = f.read()
    
    try:
        修改 = 修复文件(路径)
        if not 修改:
            return '无需修改', None
        
        # 语法检查
        ok, err = 语法检查(路径)
        if ok:
            return '修复成功', None
        else:
            # 恢复
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(backup)
            return '修复失败', err
    except Exception as e:
        # 恢复
        if backup:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(backup)
        return '异常', str(e)


def main():
    print('=== 批量修复第1批领域（数据/数学/统计/排序/搜索）===\n')
    
    总需修复 = 0
    总已修复 = 0
    总失败 = 0
    总跳过 = 0
    
    for 领域 in 目标领域:
        需修复, 已修复, 失败, 跳过 = 扫描领域(领域)
        total = len(需修复)
        print(f'[{领域}] {total} 个文件需要修复（{len(跳过)} 个已通过语法检查）')
        
        领域修复 = 0
        领域失败 = 0
        for fname in 需修复:
            status, detail = 修复并验证(领域, fname)
            if status == '修复成功':
                领域修复 += 1
                print(f'  ✅ {fname}')
            elif status == '无需修改':
                print(f'  ➖ {fname}（{status}）')
            else:
                领域失败 += 1
                print(f'  ❌ {fname}: {detail}')
        
        总需修复 += total
        总已修复 += 领域修复
        总失败 += 领域失败
        总跳过 += len(跳过)
        print(f'  → {领域修复} 修复成功, {领域失败} 失败\n')
    
    print(f'\n=== 汇总 ===')
    print(f'总计: {总需修复} 需修复, {总已修复} 成功, {总失败} 失败, {总跳过} 跳过')
    
    return 0 if 总失败 == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())