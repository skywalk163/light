# -*- coding: utf-8 -*-
"""
光明积木库综合修复脚本 v3.1
============================
系统性地修复预跑失败。

Fix6: 修复ParseError - 关键字参数名（仅修复已知有ParseError的文件）
Fix8: 修复ParseError - 如果-则-否则中数字无法识别
Fix9: 修复ParseError - 「真」是保留关键字
Fix12: 修复LexerError - 希腊字母

用法: python _综合修复_v3.py [--dry-run]
"""

import os, re, json, sys
from collections import defaultdict

_HERE = os.path.abspath(os.path.dirname(__file__))
BLOCKS_DIR = os.path.join(_HERE, 'blocks_v5')
RESULTS_PATH = os.path.join(_HERE, '_预跑结果.json')
DRY_RUN = '--dry-run' in sys.argv

# 希腊字母替换映射
GREEK_MAP = {
    'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta', 'Δ': 'Delta',
    'ε': 'epsilon', 'ζ': 'zeta', 'η': 'eta', 'θ': 'theta', 'Θ': 'Theta',
    'ι': 'iota', 'κ': 'kappa', 'λ': 'lambda', 'Λ': 'Lambda', 'μ': 'mu',
    'ν': 'nu', 'ξ': 'xi', 'Ξ': 'Xi', 'ο': 'omicron', 'π': 'pi', 'Π': 'Pi',
    'ρ': 'rho', 'σ': 'sigma', 'Σ': 'Sigma', 'τ': 'tau', 'υ': 'upsilon',
    'φ': 'phi', 'Φ': 'Phi', 'χ': 'chi', 'ψ': 'psi', 'Ψ': 'Psi', 'ω': 'omega', 'Ω': 'Omega',
}

# 已知导致ParseError的关键字（仅修复这些）
KNOWN_KEYWORD_PARAMS = {
    '配种母畜', '配种数', '配位数', '设施面积', '设备总值',
    '设备原值', '设备净值', '设备残值', '设备使用年限',
    '设备年使用费', '设备年平均成本', '设备年收益',
    '握手往返次数', 'ACL匹配',
}

# 中文数字参数（已知导致ParseError: CHINESE_NUM）
CHINESE_NUM_PARAMS = {
    '一', '二', '三', '四', '五', '六', '七', '八', '九', '零',
    '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖',
}

# 包含数字的参数名（已知导致ParseError: 期望冒号但得到数字）
NUMERIC_PARAMS = {
    '衰减1', '衰减2', 'i减1', 'i加1', 'i减2', 'i加2',
    '千粒重',
}


def fix_greek_letters(content):
    """Fix12: 修复希腊字母"""
    modified = False
    for greek, replacement in GREEK_MAP.items():
        if greek in content:
            content = content.replace(greek, replacement)
            modified = True
    return content, modified


def fix_if_then_else(content):
    """Fix8: 修复 如果-则-否则 表达式中的数字无法识别问题
    将 返回 如果 条件 则 值1 否则 值2 转换为 返回 选择(条件, 值1, 值2)
    """
    pattern = re.compile(
        r'返回\s+如果\s+(.+?)\s+则\s+(.+?)\s+否则\s+(.+?)$',
        re.DOTALL
    )
    new_content, count = pattern.subn(r'返回 选择(\1, \2, \3)', content)
    if count > 0:
        return new_content, True
    return content, False


def fix_keyword_true(content):
    """Fix9: 修复「真」是保留关键字问题"""
    modified = False
    # 替换 如果-则-否则 中的真/假
    new_content = re.sub(
        r'(返回\s+如果\s+.+?\s+则\s+)真(\s+否则\s+)假',
        r'\1True\2False',
        content
    )
    if new_content != content:
        modified = True
        content = new_content
    # 替换 如果 条件 则 假 否则 真
    new_content = re.sub(
        r'(返回\s+如果\s+.+?\s+则\s+)假(\s+否则\s+)真',
        r'\1False\2True',
        content
    )
    if new_content != content:
        modified = True
        content = new_content
    return content, modified


def fix_keyword_and_number_params(content):
    """Fix6+Fix7: 修复关键字和中文数字参数名"""
    lines = content.split('\n')
    modified = False
    param_rename = {}

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
            for p in params:
                rename_needed = False
                new_name = p

                # 检查是否在已知问题列表中
                if p in KNOWN_KEYWORD_PARAMS:
                    rename_needed = True
                elif p in CHINESE_NUM_PARAMS:
                    rename_needed = True
                elif p in NUMERIC_PARAMS:
                    rename_needed = True
                # 检查中文数字开头（如"千粒重"中的"千"）
                elif p and p[0] in '一二三四五六七八九十零百千万亿':
                    rename_needed = True
                
                if rename_needed:
                    new_name = 'p_' + p
                    param_rename[p] = new_name
                    new_params.append(new_name)
                    modified = True
                else:
                    new_params.append(p)

            if modified:
                new_line = f'{func_type} {func_name} 接收 {", ".join(new_params)}：'
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = indent + new_line

    # 更新体中所有使用旧参数名的地方
    if param_rename:
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            for old_name, new_name in param_rename.items():
                lines[i] = lines[i].replace(old_name, new_name)

    return '\n'.join(lines), modified


def fix_parse_error_syntax(content, filepath):
    """综合修复所有ParseError"""
    changes = []
    
    new_content, mod = fix_keyword_and_number_params(content)
    if mod:
        changes.append('Fix6/7:参数名')
        content = new_content
    
    new_content, mod = fix_if_then_else(content)
    if mod:
        changes.append('Fix8:如果-则-否则')
        content = new_content
    
    new_content, mod = fix_keyword_true(content)
    if mod:
        changes.append('Fix9:真/假')
        content = new_content
    
    new_content, mod = fix_greek_letters(content)
    if mod:
        changes.append('Fix12:希腊字母')
        content = new_content
    
    # 额外的Fix5: 无空格运算
    expr_fixes = [
        ('i加1', 'i 加 1'), ('i减1', 'i 减 1'),
        ('i加2', 'i 加 2'), ('i减2', 'i 减 2'),
        ('j加1', 'j 加 1'), ('j减1', 'j 减 1'),
        ('k加1', 'k 加 1'), ('k减1', 'k 减 1'),
        ('n加1', 'n 加 1'), ('n减1', 'n 减 1'),
        ('乘 乘', '乘'), ('除 除', '除'),
    ]
    for old, new in expr_fixes:
        if old in content:
            content = content.replace(old, new)
            if old not in ('乘 乘', '除 除') and 'Fix5' not in changes:
                changes.append('Fix5:无空格')
    
    return content, changes


def main():
    print('=' * 60)
    print(f'光明积木库综合修复 v3.1')
    print(f'模式: {"DRY RUN (仅预览)" if DRY_RUN else "实际写入"}')
    print('=' * 60)
    
    all_files = []
    for root, dirs, files in os.walk(BLOCKS_DIR):
        for f in files:
            if f.endswith('.light'):
                all_files.append(os.path.join(root, f))
    
    print(f'\n共找到 {len(all_files)} 个积木文件')
    
    print('\n--- 修复ParseError和LexerError ---')
    total_fixed = 0
    for filepath in all_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content, changes = fix_parse_error_syntax(content, filepath)
        
        if changes:
            if not DRY_RUN:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            relpath = os.path.relpath(filepath, BLOCKS_DIR)
            print(f'  [{",".join(changes)}] {relpath}')
            total_fixed += 1
    
    print(f'\n修复了 {total_fixed} 个文件')
    
    if DRY_RUN:
        print('\n这是DRY RUN，未写入任何文件。去掉 --dry-run 参数执行实际修复。')


if __name__ == '__main__':
    main()