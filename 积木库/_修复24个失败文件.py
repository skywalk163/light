# -*- coding: utf-8 -*-
"""修复第2批修复失败的24个文件。

Failure categories:
  1. 数字在标识符中: 3倍数, 5倍数, 过滤模10零集合, 过滤模2零集合
  2. 如果...则...否则... → 如果...：\n    ...\n否则：\n    ...
  3. 且 关键字 → 多层嵌套如果
  4. 后N个 → 后个数
"""

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, '..'))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, 'src'))

from light_parser_v3 import LightParser, ParseError

V5_DIR = os.path.join(_HERE, 'blocks_v5')


def 语法检查(路径):
    try:
        with open(路径, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        return False, f'读取失败: {e}'
    parser = LightParser()
    try:
        module = parser.parse(source)
        if module is None:
            return False, '解析失败：返回空模块'
        return True, ''
    except ParseError as e:
        return False, str(e)[:200]
    except Exception as e:
        return False, f'{type(e).__name__}: {e}'


def 修复_数字标识符(内容, 数字映射):
    """修复 Group 1: 数字在标识符中"""
    修改 = False
    for 数字, 中文 in 数字映射.items():
        if 数字 in 内容:
            内容 = 内容.replace(数字, 中文)
            修改 = True
    return 内容, 修改


def 解析_如果则否则(行):
    """解析一行中的 if-then-else 表达式，返回 (cond, then_val, else_val) 或 None"""
    m = re.match(r'(\s*)返回\s+如果\s+(.+?)\s+则\s+(.+?)\s+否则\s+(.+?)$', 行)
    if m:
        indent = m.group(1)
        cond = m.group(2).strip()
        then_val = m.group(3).strip()
        else_val = m.group(4).strip()
        return indent, cond, then_val, else_val
    return None


def 修复_如果则否则(内容):
    """修复 Group 2: 如果...则...否则... → 如果...：\n    ...\n否则：\n    ..."""
    行们 = 内容.split('\n')
    新行们 = []
    修改 = False
    for 行 in 行们:
        r = 解析_如果则否则(行)
        if r:
            indent, cond, then_val, else_val = r
            # 检查 else_val 中是否包含嵌套的 如果...则...否则...
            if '如果' in else_val and '则' in else_val and '否则' in else_val:
                # 嵌套 case: 提取嵌套的 if-then-else
                nm = re.match(r'\(?\s*如果\s+(.+?)\s+则\s+(.+?)\s+否则\s+(.+?)\s*\)?', else_val)
                if nm:
                    nested_cond = nm.group(1).strip()
                    nested_then = nm.group(2).strip()
                    nested_else = nm.group(3).strip()
                    新行们.append(f'{indent}如果 {cond}：')
                    新行们.append(f'{indent}    返回 {then_val}')
                    新行们.append(f'{indent}否则：')
                    新行们.append(f'{indent}    如果 {nested_cond}：')
                    新行们.append(f'{indent}        返回 {nested_then}')
                    新行们.append(f'{indent}    否则：')
                    新行们.append(f'{indent}        返回 {nested_else}')
                    修改 = True
                    continue
            新行们.append(f'{indent}如果 {cond}：')
            新行们.append(f'{indent}    返回 {then_val}')
            新行们.append(f'{indent}否则：')
            新行们.append(f'{indent}    返回 {else_val}')
            修改 = True
        else:
            新行们.append(行)
    return '\n'.join(新行们), 修改


def 修复_且条件(内容):
    """修复 Group 3: 如果 A 且 B → 嵌套如果"""
    行们 = 内容.split('\n')
    新行们 = []
    修改 = False
    for 行 in 行们:
        s = 行.strip()
        if '如果' in s and '且' in s and '：' in s:
            m = re.match(r'(\s*)如果\s+(.+?)\s+且\s+(.+?)\s*[：:]', 行)
            if m:
                indent = m.group(1)
                cond1 = m.group(2).strip()
                cond2 = m.group(3).strip()
                # 找到该行后面的内容（缩进更大的行）
                新行们.append(f'{indent}如果 {cond1}：')
                新行们.append(f'{indent}    如果 {cond2}：')
                # 将该行后续内容缩进增加
                修改 = True
                continue
        新行们.append(行)
    return '\n'.join(新行们), 修改


def 修复_后N个(内容):
    """修复 Group 4: 后N个 → 后个数, N → 个数"""
    修改 = False
    if '后N个' in 内容:
        内容 = 内容.replace('后N个', '后个数')
        修改 = True
    if ' N ' in 内容 or ' N：' in 内容 or ' N\n' in 内容 or 'N' in 内容.split('\n')[-1] if 内容.split('\n') else False:
        # 在非注释行中替换 N 为 个数
        行们 = 内容.split('\n')
        新行们 = []
        for 行 in 行们:
            s = 行.strip()
            if s.startswith('#') or s.startswith('导出') or re.match(r'^(段落|函数|段)\s+', s):
                新行们.append(行)
            else:
                # 替换独立的 N 为 个数
                行 = re.sub(r'(?<!\w)N(?!\w)', '个数', 行)
                新行们.append(行)
        内容 = '\n'.join(新行们)
        修改 = True
    return 内容, 修改


def 修复文件(路径, 文件名):
    """修复单个文件，返回 (成功?, 错误信息?)"""
    备份 = None
    try:
        with open(路径, 'r', encoding='utf-8') as f:
            content = f.read()
        备份 = content
    except Exception as e:
        return False, f'读取失败: {e}'
    
    修改 = False
    
    # Group 1: 数字标识符
    数字映射 = {}
    if '3倍数' in 文件名 or '3倍数' in content:
        数字映射['3倍数'] = '三倍数'
        数字映射['3'] = '三'
    if '5倍数' in 文件名 or '5倍数' in content:
        数字映射['5倍数'] = '五倍数'
        数字映射['5'] = '五'
    if '过滤模10零' in 文件名:
        数字映射['过滤模10零'] = '过滤模十零'
        数字映射['10'] = '十'
    if '过滤模2零' in 文件名:
        数字映射['过滤模2零'] = '过滤模二零'
        数字映射['2'] = '二'
    
    if 数字映射:
        content, m1 = 修复_数字标识符(content, 数字映射)
        if m1:
            修改 = True
    
    # Group 2: 如果...则...否则...
    if '则' in content and '否则' in content:
        content, m2 = 修复_如果则否则(content)
        if m2:
            修改 = True
    
    # Group 3: 且
    if '且' in content:
        content, m3 = 修复_且条件(content)
        if m3:
            修改 = True
    
    # Group 4: 后N个
    if '后N个' in content or ' N ' in content:
        content, m4 = 修复_后N个(content)
        if m4:
            修改 = True
    
    # 额外的数字替换：在非注释/导出/段落行中将 0/1/2/5 替换为中文
    if not 修改:
        行们 = content.split('\n')
        新行们 = []
        数字映射2 = {'0': '零', '1': '一', '2': '二', '5': '五'}
        for 行 in 行们:
            s = 行.strip()
            if s.startswith('#') or s.startswith('导出') or re.match(r'^(段落|函数|段)\s+', s):
                新行们.append(行)
            else:
                原行 = 行
                for 数字, 中文 in 数字映射2.items():
                    行 = re.sub(r'(?<!\w)' + 数字 + r'(?!\w)', 中文, 行)
                if 行 != 原行:
                    修改 = True
                新行们.append(行)
        content = '\n'.join(新行们)
    
    if not 修改:
        return False, None  # 无需修改
    
    # 写入验证
    try:
        # 写前先语法检查
        ok_before, _ = 语法检查_文本(content)
        if ok_before:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, None
        
        with open(路径, 'w', encoding='utf-8') as f:
            f.write(content)
        ok, verr = 语法检查(路径)
        if ok:
            return True, None
        else:
            if 备份:
                with open(路径, 'w', encoding='utf-8') as f:
                    f.write(备份)
            return False, f'修复后语法检查失败: {verr[:100]}'
    except Exception as e:
        if 备份:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(备份)
        return False, str(e)


def 语法检查_文本(source):
    parser = LightParser()
    try:
        module = parser.parse(source)
        if module is None:
            return False, '解析失败：返回空模块'
        return True, ''
    except ParseError as e:
        return False, str(e)[:200]
    except Exception as e:
        return False, f'{type(e).__name__}: {e}'


def main():
    # 24个失败文件列表
    失败文件 = [
        ('集合', '3倍数.light'),
        ('集合', '5倍数.light'),
        ('集合', '中间段.light'),
        ('集合', '后N个.light'),
        ('集合', '过滤模10零集合.light'),
        ('集合', '过滤模2零集合.light'),
        ('随机', '伯努利.light'),
        ('随机', '随机Cox过程.light'),
        ('随机', '随机信用.light'),
        ('随机', '随机再生.light'),
        ('随机', '随机分支.light'),
        ('随机', '随机反射.light'),
        ('随机', '随机复合泊松.light'),
        ('随机', '随机多inomial.light'),
        ('随机', '随机多项式.light'),
        ('随机', '随机操作.light'),
        ('随机', '随机破产.light'),
        ('随机', '随机泊松过程.light'),
        ('随机', '随机流动.light'),
        ('随机', '随机符号.light'),
        ('随机', '随机类别.light'),
        ('随机', '随机粒子.light'),
        ('随机', '随机跳跃.light'),
        ('随机', '随机排队.light'),
    ]
    
    成功 = 0
    失败 = 0
    
    for 领域, 文件名 in 失败文件:
        路径 = os.path.join(V5_DIR, 领域, 文件名)
        if not os.path.exists(路径):
            print(f'  ⚠ 文件不存在: {领域}/{文件名}')
            continue
        
        ok, err = 修复文件(路径, 文件名)
        if ok:
            print(f'  ✅ {领域}/{文件名}')
            成功 += 1
        elif err:
            print(f'  ❌ {领域}/{文件名}: {err}')
            失败 += 1
        else:
            print(f'  ➖ {领域}/{文件名}（无需修改）')
    
    print(f'\n结果: 成功 {成功}, 失败 {失败}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())