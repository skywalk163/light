# -*- coding: utf-8 -*-
"""
光明积木库综合修复脚本 v5.1
============================
系统性地修复预跑失败。

修复策略：
  FixA: p_函数 → cb_func（参数名含关键字'函数'导致ParseError）
  FixB: p_衰减1/p_衰减2 → p_衰减一/p_衰减二（数字结尾+下划线导致ParseError）
  FixC: 两点距离、斜率计算的参数名含运算符（甲减乙→甲,乙分开）
  FixD: 正多边形面积 - 方法调用转函数调用
  FixE: 移除未使用的p_i减1/p_i加1参数（滤波函数）
  FixF: 修复函数合成/组合中body未更新cb_前缀
  FixG: 修复函数泰勒二阶中的p_前缀
  FixH: 转换CRLF为LF（修复新行解析错误）

用法: python _修复v5.py [--dry-run]
"""

import os, re, sys
from collections import defaultdict

_HERE = os.path.abspath(os.path.dirname(__file__))
BLOCKS_DIR = os.path.join(_HERE, 'blocks_v5')
DRY_RUN = '--dry-run' in sys.argv


def fix_p_func(content):
    """FixA: p_函数 → cb_func（参数名含关键字'函数'）"""
    if 'p_函数' not in content:
        return content, False, None
    new_content = content.replace('p_函数', 'cb_func')
    modified = new_content != content
    return new_content, modified, 'FixA:函数参数' if modified else None


def fix_p_digit(content):
    """FixB: p_衰减_一/p_衰减_二 → p_衰减一/p_衰减二（去掉下划线）"""
    fixes = {
        'p_衰减_一': 'p_衰减一',
        'p_衰减_二': 'p_衰减二',
    }
    modified = False
    for old, new in fixes.items():
        if old in content:
            content = content.replace(old, new)
            modified = True
    return content, modified, 'FixB:数字参数' if modified else None


def fix_distance_params(content):
    """FixC: 修复天干地支组合的表达式参数名"""
    lines = content.split('\n')
    modified = False
    STEM_BRANCH = set('甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥')
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = re.match(r'(段落|函数|段)\s+(\S+)\s+接收\s+(.+)', stripped)
        if m:
            func_type = m.group(1)
            func_name = m.group(2)
            params_str = m.group(3).strip()
            params_str = re.sub(r'[：:]$', '', params_str)
            params = [p.strip() for p in params_str.split(',')]
            new_params = []
            renamed = {}
            for p in params:
                m2 = re.match(r'^([甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥])([加减乘除])([甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥])$', p)
                if m2:
                    a, op, b = m2.groups()
                    renamed[p] = (a, b, op)
                    new_params.extend([a, b])
                    modified = True
                else:
                    new_params.append(p)
            if renamed:
                new_line = f'{func_type} {func_name} 接收 {", ".join(new_params)}：'
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = indent + new_line
                for j, body_line in enumerate(lines):
                    if j != i and not body_line.strip().startswith('#'):
                        updated = body_line
                        for old_name, (a, b, op) in renamed.items():
                            if old_name in updated:
                                updated = updated.replace(old_name, f'({a} {op} {b})')
                        if updated != body_line:
                            lines[j] = updated
    return '\n'.join(lines), modified, 'FixC:距离参数' if modified else None


def fix_tangent_method(content):
    """FixD: (expr).正切() → 正切(expr)"""
    if '.正切()' not in content:
        return content, False, None
    pattern = re.compile(r'\(([^)]+)\)\.正切\(\)')
    new_content = pattern.sub(r'正切(\1)', content)
    return new_content, new_content != content, 'FixD:正切方法' if new_content != content else None


def fix_filter_params(content):
    """FixE: 移除未使用的 p_i减1/p_i加1 参数（滤波函数）
    
    这些参数名包含运算符和数字，导致ParseError。
    且这些参数在函数体中未被使用，可以直接移除。
    """
    if 'p_i 减 1' not in content and 'p_i 加 1' not in content:
        return content, False, None
    
    lines = content.split('\n')
    modified = False
    
    UNUSED_PARAMS = {'p_i 减 1', 'p_i 加 1'}
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = re.match(r'(段落|函数|段)\s+(\S+)\s+接收\s+(.+)', stripped)
        if m:
            func_type = m.group(1)
            func_name = m.group(2)
            params_str = m.group(3).strip()
            params_str = re.sub(r'[：:]$', '', params_str)
            params = [p.strip() for p in params_str.split(',')]
            
            new_params = [p for p in params if p not in UNUSED_PARAMS]
            if len(new_params) != len(params):
                new_line = f'{func_type} {func_name} 接收 {", ".join(new_params)}：'
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = indent + new_line
                modified = True
    
    return '\n'.join(lines), modified, 'FixE:滤波参数' if modified else None


def fix_cb_body(content):
    """FixF: 修复函数体中 cb_ 前缀未更新的问题
    
    当参数是 cb_X 但体中使用 X 时，更新体中的引用
    """
    lines = content.split('\n')
    modified = False
    cb_params = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = re.match(r'(段落|函数|段)\s+(\S+)\s+接收\s+(.+)', stripped)
        if m:
            params_str = m.group(3).strip()
            params_str = re.sub(r'[：:]$', '', params_str)
            params = [p.strip() for p in params_str.split(',')]
            cb_params = [p for p in params if p.startswith('cb_')]
            break
    
    if not cb_params:
        return content, False, None
    
    for i, line in enumerate(lines):
        if not line.strip().startswith('#') and not line.strip().startswith('段落') and not line.strip().startswith('函数') and not line.strip().startswith('段'):
            for cb_p in cb_params:
                base_name = cb_p[3:]  # 去掉 cb_ 前缀
                if base_name in line:
                    # 检查是否在行中以独立标识符出现（不在cb_前缀中）
                    pattern = re.compile(r'(?<![a-zA-Z_\u4e00-\u9fff])' + re.escape(base_name) + r'(?![a-zA-Z_\u4e00-\u9fff])')
                    new_line = pattern.sub(cb_p, lines[i])
                    if new_line != lines[i]:
                        lines[i] = new_line
                        modified = True
    
    return '\n'.join(lines), modified, 'FixF:cb体更新' if modified else None


def fix_p_func_name(content):
    """FixG: 修复函数名中的 p_ 前缀（如 函数泰勒p_二阶 → 函数泰勒二阶）"""
    lines = content.split('\n')
    modified = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 修复导出行和段落行中的函数名
        m = re.match(r'(导出|段落|函数|段)\s+(\S+)(.*)', stripped)
        if m:
            keyword = m.group(1)
            name = m.group(2)
            rest = m.group(3)
            if 'p_' in name:
                # 去掉 p_ 前缀
                new_name = name.replace('p_', '')
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = f'{indent}{keyword} {new_name}{rest}'
                modified = True
                
                # 同时更新参数行中的同名参数
                if keyword in ('段落', '函数', '段'):
                    params_str = rest.strip()
                    if '接收' in params_str:
                        # 在参数列表中也去除 p_ 前缀
                        _, params_part = params_str.split('接收', 1)
                        params_part = params_part.strip()
                        params_part = re.sub(r'[：:]$', '', params_part)
                        param_list = [p.strip() for p in params_part.split(',')]
                        new_param_list = [p.replace('p_', '') if p.startswith('p_') else p for p in param_list]
                        if new_param_list != param_list:
                            new_line = f'{indent}{keyword} {new_name} 接收 {", ".join(new_param_list)}：'
                            lines[i] = new_line
                            modified = True
    
    return '\n'.join(lines), modified, 'FixG:函数名p_' if modified else None


def fix_crlf(content):
    """FixH: 转换CRLF为LF"""
    if '\r\n' in content:
        return content.replace('\r\n', '\n'), True, 'FixH:CRLF转LF'
    return content, False, None


def main():
    print('=' * 60)
    print(f'光明积木库综合修复 v5.1')
    print(f'模式: {"DRY RUN (仅预览)" if DRY_RUN else "实际写入"}')
    print('=' * 60)
    
    all_files = []
    for root, dirs, files in os.walk(BLOCKS_DIR):
        for f in files:
            if f.endswith('.light'):
                all_files.append(os.path.join(root, f))
    
    print(f'\n共找到 {len(all_files)} 个积木文件')
    
    stats = defaultdict(int)
    file_fixes = {}
    
    print('\n--- 修复ParseError ---')
    for filepath in all_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # FixA: p_函数 → cb_func
        content, mod, name = fix_p_func(content)
        if mod: changes.append(name)
        
        # FixB: p_衰减_一 → p_衰减一
        content, mod, name = fix_p_digit(content)
        if mod: changes.append(name)
        
        # FixC: 距离参数
        content, mod, name = fix_distance_params(content)
        if mod: changes.append(name)
        
        # FixD: 正切方法
        content, mod, name = fix_tangent_method(content)
        if mod: changes.append(name)
        
        # FixE: 移除滤波参数
        content, mod, name = fix_filter_params(content)
        if mod: changes.append(name)
        
        # FixF: cb_体更新
        content, mod, name = fix_cb_body(content)
        if mod: changes.append(name)
        
        # FixG: 函数名p_
        content, mod, name = fix_p_func_name(content)
        if mod: changes.append(name)
        
        # FixH: CRLF转LF
        content, mod, name = fix_crlf(content)
        if mod: changes.append(name)
        
        if changes:
            if not DRY_RUN:
                with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(content)
            relpath = os.path.relpath(filepath, BLOCKS_DIR)
            print(f'  [{",".join(changes)}] {relpath}')
            for c in changes:
                stats[c] += 1
            file_fixes[relpath] = changes
    
    print(f'\n修复统计:')
    for fix_name, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f'  {fix_name}: {count} 个文件')
    print(f'\n共修复 {len(file_fixes)} 个文件')
    
    if DRY_RUN:
        print('\n这是DRY RUN，未写入任何文件。去掉 --dry-run 参数执行实际修复。')


if __name__ == '__main__':
    main()