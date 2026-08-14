# -*- coding: utf-8 -*-
"""
光明积木库综合修复脚本 v4.0
============================
系统性地修复预跑失败。

修复策略：
  FixA: 修复Fix6/7的双重重命名bug（p_p_问题）和遗漏的关键字参数
  FixB: 修复SyntaxError - 函数参数名「函数」是关键字
  FixC: 修复LexerError - 希腊字母（扩展Fix12）
  FixD: 修复"int is not callable" - 参数名与函数调用冲突
  FixE: 修复ParseError - 扩展关键字参数检测

用法: python _综合修复_v4.py [--dry-run]
"""

import os, re, sys
from collections import defaultdict

_HERE = os.path.abspath(os.path.dirname(__file__))
BLOCKS_DIR = os.path.join(_HERE, 'blocks_v5')
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

# 光明语言关键字集合（从keywords.py提取）
# 这些字/词在光明解析器中作为关键字处理，不能用作参数名
LIGHT_KEYWORDS = {
    # L0核心字
    '若', '否', '当', '遍', '跳', '过', '返',
    '设', '段', '类', '承', '接', '配',
    '试', '捕', '抛', '终',
    '自', '之', '并', '从', '是',
    '且', '或', '非', '真', '假', '空',
    '导', '出',
    # 双字关键字
    '定义', '常量', '类型', '导入', '导出', '为',
    '如果', '那么', '否则', '否则若', '则',
    '遍历', '跳出', '跳过', '在', '对', '中的', '于',
    '函数', '段落', '接收', '返回',
    '严格', '松散',
    '尝试', '捕获', '抛出', '最终',
    '继承', '属性', '构造', '新建',
    '接口', '实现',
    '私有', '公有', '保护',
    '静态', '静态方法', '类方法', '特性',
    '模块', '标准库',
    '异步', '等待', '作用域',
    '匹配', '情况',
    '使用', '标注',
    '嵌入', '结束嵌入',
    '引', '结束引',
    '外部', '加载库', '结构体', '回调',
    '捕获', '外部错误',
    '枚举', '联合体', '变长参数',
    '类型别名', '位域', '函数指针', '宏', '调试',
    '抽象',
    '私属性', '私段落',
    '开启', '关闭',
    '与', '并且',
}

# 中文数字集合（单个字，这些作为参数名会引发ParseError: CHINESE_NUM）
CHINESE_NUM_SINGLE = {
    '零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
    '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖', '拾',
    '百', '千', '万', '亿',
}

# 数字结尾的参数名（这些会被词法分析器误识别为数字字面量）
NUMERIC_ENDING_PARAMS = {
    '衰减1', '衰减2', 'i减1', 'i加1', 'i减2', 'i加2',
    '千粒重',
}

# 中文数字开头的参数名（如"千粒重"中的"千"）
CHINESE_NUM_START_CHARS = set('一二三四五六七八九十零百千万亿')


def is_keyword_param(param_name):
    """检查参数名是否需要重命名（是关键字或中文数字）"""
    # 已经重命名过的跳过
    if param_name.startswith('p_'):
        return False
    if param_name.startswith('p_p_'):
        return False
    # 单字中文数字
    if param_name in CHINESE_NUM_SINGLE:
        return True
    # 光明语言关键字
    if param_name in LIGHT_KEYWORDS:
        return True
    # 数字结尾
    if param_name in NUMERIC_ENDING_PARAMS:
        return True
    # 中文数字开头
    if param_name and param_name[0] in CHINESE_NUM_START_CHARS:
        return True
    return False


def fix_double_rename(content):
    """FixA: 修复双重重命名bug（p_p_ → p_）"""
    if 'p_p_' not in content:
        return content, False, None
    
    modified = False
    lines = content.split('\n')
    has_changes = False
    
    # 修复p_p_前缀的引用
    for i, line in enumerate(lines):
        # 修复参数行中的p_p_
        stripped = line.strip()
        m = re.match(r'(段落|函数|段)\s+(\S+)\s+接收\s+(.+)', stripped)
        if m:
            params_str = m.group(3).strip()
            params_str = re.sub(r'[：:]$', '', params_str)
            params = [p.strip() for p in params_str.split(',')]
            new_params = []
            changed = False
            for p in params:
                if p.startswith('p_p_'):
                    # 检查对应的p_版本是否在body中使用
                    p_single = 'p_' + p[4:]  # p_p_衰减1 → p_衰减1
                    new_params.append(p_single)
                    changed = True
                else:
                    new_params.append(p)
            if changed:
                new_line = f'{m.group(1)} {m.group(2)} 接收 {", ".join(new_params)}：'
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = indent + new_line
                has_changes = True
        else:
            # 修复body中的p_p_引用
            if 'p_p_' in line and not line.strip().startswith('#'):
                # 替换 p_p_X → p_X
                old_line = line
                lines[i] = re.sub(r'p_p_(\w+)', r'p_\1', line)
                if lines[i] != old_line:
                    has_changes = True
    
    if has_changes:
        modified = True
    return '\n'.join(lines), modified, 'FixA:双重重命名'


def fix_keyword_params(content):
    """FixB+E: 修复关键字参数名和中文数字参数名"""
    lines = content.split('\n')
    modified = False
    param_rename = {}
    fix_names = []

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
            local_rename = {}
            for p in params:
                if is_keyword_param(p):
                    new_name = 'p_' + p
                    local_rename[p] = new_name
                    new_params.append(new_name)
                    modified = True
                else:
                    new_params.append(p)

            if local_rename:
                new_line = f'{func_type} {func_name} 接收 {", ".join(new_params)}：'
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = indent + new_line
                param_rename.update(local_rename)
                fix_names.append('FixE:关键字参数')

    # 更新body中所有使用旧参数名的地方
    if param_rename:
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            for old_name, new_name in param_rename.items():
                # 注意：替换时要避免部分匹配
                # 例如 "壹" 被替换成 "p_壹"，但不要影响 "壹" 在其他词中的部分
                # 使用单词边界匹配
                if old_name in lines[i]:
                    # 安全替换：只替换完整的标识符
                    pattern = re.compile(r'(?<=[\s,()+\-*/])' + re.escape(old_name) + r'(?=[\s,()+\-*/]|$)')
                    lines[i] = pattern.sub(new_name, lines[i])
                    # 也处理行首或行尾的情况
                    if lines[i].strip().startswith(old_name) or lines[i].strip().endswith(old_name):
                        lines[i] = lines[i].replace(old_name, new_name)
                    # 处理字符串中的引用
                    lines[i] = lines[i].replace(f"'{old_name}'", f"'{new_name}'")
                    lines[i] = lines[i].replace(f'"{old_name}"', f'"{new_name}"')

    return '\n'.join(lines), modified, fix_names[0] if fix_names else None


def fix_func_param(content):
    """FixB: 修复函数参数名「函数」是关键字问题"""
    if '函数' not in content:
        return content, False, None
    
    lines = content.split('\n')
    modified = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = re.match(r'(段落|函数|段)\s+(\S+)\s+接收\s+(.+)', stripped)
        if m:
            func_type = m.group(1)
            func_name = m.group(2)
            params_str = m.group(3).strip()
            params_str = re.sub(r'[：:]$', '', params_str)
            params = [p.strip() for p in params_str.split(',')]
            
            # 检查是否有「函数」作为参数名
            if '函数' not in params:
                continue
            
            new_params = []
            has_func_param = False
            for p in params:
                if p == '函数':
                    new_params.append('p_函数')
                    has_func_param = True
                    modified = True
                else:
                    new_params.append(p)
            
            if has_func_param:
                new_line = f'{func_type} {func_name} 接收 {", ".join(new_params)}：'
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = indent + new_line
    
    # 更新body中的函数调用
    if modified:
        for i, line in enumerate(lines):
            if not line.strip().startswith('#'):
                # 替换函数(param) → p_函数(param)
                # 使用正则匹配：函数( 作为函数调用
                lines[i] = re.sub(r'(?<![a-zA-Z_])函数\(', 'p_函数(', lines[i])
    
    return '\n'.join(lines), modified, 'FixB:函数参数'


def fix_greek_letters(content):
    """FixC: 修复希腊字母"""
    modified = False
    for greek, replacement in GREEK_MAP.items():
        if greek in content:
            content = content.replace(greek, replacement)
            modified = True
    return content, modified, 'FixC:希腊字母' if modified else None


def fix_if_then_else(content):
    """修复 如果-则-否则 表达式"""
    pattern = re.compile(
        r'返回\s+如果\s+(.+?)\s+则\s+(.+?)\s+否则\s+(.+?)$',
        re.DOTALL
    )
    new_content, count = pattern.subn(r'返回 选择(\1, \2, \3)', content)
    if count > 0:
        return new_content, True, 'Fix8:如果-则-否则'
    return content, False, None


def fix_keyword_true(content):
    """修复「真」是保留关键字"""
    modified = False
    new_content = re.sub(
        r'(返回\s+如果\s+.+?\s+则\s+)真(\s+否则\s+)假',
        r'\1True\2False',
        content
    )
    if new_content != content:
        modified = True
        content = new_content
    new_content = re.sub(
        r'(返回\s+如果\s+.+?\s+则\s+)假(\s+否则\s+)真',
        r'\1False\2True',
        content
    )
    if new_content != content:
        modified = True
        content = new_content
    return content, modified, 'Fix9:真/假' if modified else None


def fix_no_space_ops(content):
    """修复无空格运算"""
    modified = False
    fixes = [
        ('i加1', 'i 加 1'), ('i减1', 'i 减 1'),
        ('i加2', 'i 加 2'), ('i减2', 'i 减 2'),
        ('j加1', 'j 加 1'), ('j减1', 'j 减 1'),
        ('k加1', 'k 加 1'), ('k减1', 'k 减 1'),
        ('n加1', 'n 加 1'), ('n减1', 'n 减 1'),
        ('乘 乘', '乘'), ('除 除', '除'),
    ]
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            modified = True
    return content, modified, 'Fix5:无空格' if modified else None


def fix_param_as_call(content):
    """FixD: 修复参数名被当作函数调用的问题（int is not callable）
    
    检测模式：参数名在body中以 param(args) 形式出现
    解决方案：检查参数名是否在body中被用作函数调用（后面跟着括号参数）
    """
    lines = content.split('\n')
    modified = False
    
    # 提取参数名
    params = []
    for line in lines:
        stripped = line.strip()
        m = re.match(r'(段落|函数|段)\s+(\S+)\s+接收\s+(.+)', stripped)
        if m:
            params_str = m.group(3).strip()
            params_str = re.sub(r'[：:]$', '', params_str)
            params = [p.strip() for p in params_str.split(',')]
            break
    
    if not params:
        return content, False, None
    
    # 检查每个参数名在body中是否被用作函数调用
    # 模式：param( 或 param( 之前是空格或行首
    param_as_call = {}
    body = '\n'.join(lines)
    
    for p in params:
        # 跳过已重命名的参数
        if p.startswith('p_'):
            continue
        # 跳过关键字参数（这些已经由FixB/FixE处理）
        if p in LIGHT_KEYWORDS or p in CHINESE_NUM_SINGLE:
            continue
        
        # 检查 p( 模式（参数被用作函数调用）
        pattern = re.compile(r'(?<![a-zA-Z_\u4e00-\u9fff])' + re.escape(p) + r'\s*\(')
        if pattern.search(body):
            param_as_call[p] = True
    
    if not param_as_call:
        return content, False, None
    
    # 重命名这些参数
    rename_map = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = re.match(r'(段落|函数|段)\s+(\S+)\s+接收\s+(.+)', stripped)
        if m:
            params_str = m.group(3).strip()
            params_str = re.sub(r'[：:]$', '', params_str)
            existing_params = [p.strip() for p in params_str.split(',')]
            
            new_params = []
            for p in existing_params:
                if p in param_as_call:
                    new_name = 'cb_' + p  # cb = callback
                    rename_map[p] = new_name
                    new_params.append(new_name)
                    modified = True
                else:
                    new_params.append(p)
            
            if rename_map:
                func_type = m.group(1)
                func_name = m.group(2)
                new_line = f'{func_type} {func_name} 接收 {", ".join(new_params)}：'
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = indent + new_line
    
    # 更新body中所有使用旧参数名的地方
    if rename_map:
        for i, line in enumerate(lines):
            if not line.strip().startswith('#'):
                for old_name, new_name in rename_map.items():
                    if old_name in line:
                        lines[i] = line.replace(old_name, new_name)
    
    return '\n'.join(lines), modified, 'FixD:参数作函数'


def fix_await_outside_async(content):
    """修复'await' outside async function问题"""
    if '等待' not in content:
        return content, False, None
    
    # 将 等待(x) 替换为 同步等待(x) 或直接调用
    modified = False
    new_content = content.replace('等待(', '同步等待(')
    if new_content != content:
        modified = True
    return new_content, modified, 'Fix:等待同步' if modified else None


def main():
    print('=' * 60)
    print(f'光明积木库综合修复 v4.0')
    print(f'模式: {"DRY RUN (仅预览)" if DRY_RUN else "实际写入"}')
    print('=' * 60)
    
    all_files = []
    for root, dirs, files in os.walk(BLOCKS_DIR):
        for f in files:
            if f.endswith('.light'):
                all_files.append(os.path.join(root, f))
    
    print(f'\n共找到 {len(all_files)} 个积木文件')
    
    # 统计
    stats = defaultdict(int)
    file_fixes = {}
    
    print('\n--- 修复ParseError, LexerError, SyntaxError ---')
    for filepath in all_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # FixA: 双重重命名
        content, mod, name = fix_double_rename(content)
        if mod: changes.append(name)
        
        # FixB: 函数参数名
        content, mod, name = fix_func_param(content)
        if mod: changes.append(name)
        
        # FixE: 关键字参数名
        content, mod, name = fix_keyword_params(content)
        if mod: changes.append(name)
        
        # FixC: 希腊字母
        content, mod, name = fix_greek_letters(content)
        if mod: changes.append(name)
        
        # Fix8: 如果-则-否则
        content, mod, name = fix_if_then_else(content)
        if mod: changes.append(name)
        
        # Fix9: 真/假
        content, mod, name = fix_keyword_true(content)
        if mod: changes.append(name)
        
        # Fix5: 无空格
        content, mod, name = fix_no_space_ops(content)
        if mod: changes.append(name)
        
        # FixD: 参数作函数调用
        content, mod, name = fix_param_as_call(content)
        if mod: changes.append(name)
        
        # Fix: 等待同步
        content, mod, name = fix_await_outside_async(content)
        if mod: changes.append(name)
        
        if changes:
            if not DRY_RUN:
                with open(filepath, 'w', encoding='utf-8') as f:
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